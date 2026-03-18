#!/usr/bin/env python3
"""
Usage:
  python3 triangulation.py          # serveur Flask + broadcast temps
  python3 triangulation.py --demo   # demonstrateur

Chaque Pi envoie son timestamp via POST /timestamp :
  curl -X POST http://192.168.137.10:5000/timestamp \
       -H "Content-Type: application/json" \
       -d '{"timestamp": 1741862551.847}'

Le serveur broadcast son temps UTC en UDP sur le port 5001
toutes les secondes vers les autres Pis.
"""
import sys
import threading
import time
import socket
import json
import subprocess
import numpy as np
from scipy.optimize import minimize

SPEED_OF_SOUND = 343.0

KNOWN_IPS = [
    "192.168.137.10",
    "192.168.137.11",
    "192.168.137.12",
    "172.20.10.3"
]

MIC_POSITIONS = np.array([
    [0.0,  0.0],
    [1.0,  0.0],
    [0.5,  0.866],
])

TIME_BROADCAST_PORT     = 5001
TIME_BROADCAST_INTERVAL = 1.0  # secondes

MAX_PROPAGATION = max(
    np.linalg.norm(MIC_POSITIONS[i] - MIC_POSITIONS[j])
    for i in range(len(MIC_POSITIONS))
    for j in range(len(MIC_POSITIONS))
) / SPEED_OF_SOUND

WINDOW = MAX_PROPAGATION * 500

pending      = {}
window_start = None
lock         = threading.Lock()
timer        = None


# --- chrony ---

def get_chrony_offset():
    try:
        out = subprocess.check_output(["chronyc", "tracking"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if "System time" in line:
                parts = line.split()
                return float(parts[3])
    except Exception:
        pass
    return None


# --- broadcast temps ---

def time_broadcast_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    targets = [ip for ip in KNOWN_IPS if ip != "192.168.137.10"]

    while True:
        ts      = time.time()
        offset  = get_chrony_offset()
        payload = json.dumps({
            "utc":    ts,
            "offset": offset,
        }).encode()

        for ip in targets:
            try:
                sock.sendto(payload, (ip, TIME_BROADCAST_PORT))
            except Exception as e:
                print(f"  [broadcast] erreur vers {ip} : {e}")

        time.sleep(TIME_BROADCAST_INTERVAL)


# --- etat global ---

def reset():
    global pending, window_start, timer
    pending      = {}
    window_start = None
    if timer is not None:
        timer.cancel()
        timer = None
    print("  [reset] buffer vide")


def on_timeout():
    with lock:
        missing = [ip for ip in KNOWN_IPS if ip not in pending]
        print(f"  [timeout] {len(pending)}/3 recus — manquants : {missing} — reset")
        reset()


def try_triangulate():
    global timer
    timestamps = np.array([pending[ip] for ip in KNOWN_IPS])
    if timer:
        timer.cancel()
        timer = None
    saved = dict(pending)
    reset()
    return tdoa_triangulate(MIC_POSITIONS, timestamps), saved


# --- maths ---

def compute_timestamps(source_pos, mic_pos, t_emission, c=SPEED_OF_SOUND):
    distances = np.array([np.linalg.norm(np.array(source_pos) - mic) for mic in mic_pos])
    delays    = distances / c
    return t_emission + delays, distances, delays


def tdoa_triangulate(mic_pos, timestamps, c=SPEED_OF_SOUND, n_starts=50):
    ref     = np.argmin(timestamps)
    delta_d = c * (timestamps - timestamps[ref])

    def cost(source):
        d_ref = np.linalg.norm(source - mic_pos[ref])
        return sum((np.linalg.norm(source - mic_pos[i]) - d_ref - delta_d[i]) ** 2
                   for i in range(len(mic_pos)))

    max_range = max(c * (timestamps.max() - timestamps.min()) * 20, 20.0)
    best = None
    for _ in range(n_starts):
        x0  = np.random.uniform(-max_range, max_range, size=2)
        res = minimize(cost, x0, method="Nelder-Mead",
                       options={"xatol": 1e-8, "fatol": 1e-16, "maxiter": 100000})
        if best is None or res.fun < best.fun:
            best = res
    return best.x, best.fun


# --- demo ---

def run_demo():
    SOURCE_POS   = [10.0, 7.0]
    T_EMISSION   = 0.0
    NOISE_STD_MS = 0.5

    timestamps, distances, delays = compute_timestamps(SOURCE_POS, MIC_POSITIONS, T_EMISSION)
    noise            = np.abs(np.random.normal(0, NOISE_STD_MS / 1000, size=len(MIC_POSITIONS)))
    timestamps_noisy = timestamps + noise

    source, residual = tdoa_triangulate(MIC_POSITIONS, timestamps_noisy)
    err = np.linalg.norm(source - np.array(SOURCE_POS))

    print("=" * 55)
    print(f"  Source reelle  : ({SOURCE_POS[0]:.4f}, {SOURCE_POS[1]:.4f}) m")
    print(f"  Source estimee : ({source[0]:.4f}, {source[1]:.4f}) m")
    print(f"  Erreur         : {err*1000:.1f} mm")
    print(f"  Residu         : {residual:.2e}")
    print("=" * 55)
    for i in range(len(MIC_POSITIONS)):
        print(f"  Micro {i+1} : t_reel={timestamps[i]*1000:.4f} ms  "
              f"bruit={noise[i]*1000:+.4f} ms  "
              f"t_mesure={timestamps_noisy[i]*1000:.4f} ms")


# --- serveur ---

def run_server():
    from flask import Flask, request, jsonify
    global pending, window_start, timer

    # Demarre le broadcast en arriere-plan
    t = threading.Thread(target=time_broadcast_loop, daemon=True)
    t.start()
    print(f"  Broadcast temps UTC -> {[ip for ip in KNOWN_IPS if ip != '192.168.137.10']} "
          f"(UDP:{TIME_BROADCAST_PORT}) toutes les {TIME_BROADCAST_INTERVAL}s")

    app = Flask(__name__)

    @app.route("/timestamp", methods=["POST"])
    def receive_timestamp():
        global window_start, timer

        src_ip = request.remote_addr
        if src_ip not in KNOWN_IPS:
            return jsonify({"error": f"IP inconnue : {src_ip}"}), 403

        data = request.get_json()
        if not data or "timestamp" not in data:
            return jsonify({"error": "champ 'timestamp' manquant"}), 400

        ts = float(data["timestamp"])

        with lock:
            if src_ip in pending:
                return jsonify({"status": "deja recu", "ip": src_ip}), 409

            pending[src_ip] = ts
            n = len(pending)
            print(f"  [{src_ip}] timestamp recu : {ts:.6f} s  ({n}/3)")

            if n == 1:
                window_start = time.monotonic()
                timer = threading.Timer(WINDOW, on_timeout)
                timer.start()
                print(f"  [fenetre] ouverte pour {WINDOW*1000:.2f} ms")

            if n == 3:
                (source, residual), saved = try_triangulate()
                result = {
                    "x":         round(float(source[0]), 4),
                    "y":         round(float(source[1]), 4),
                    "residual":  float(residual),
                    "timestamps": {ip: saved[ip] for ip in KNOWN_IPS},
                }
                print(f"  [triangulation] x={result['x']} m  y={result['y']} m  residu={residual:.2e}")
                return jsonify(result), 200

        elapsed = (time.monotonic() - window_start) * 1000 if window_start else 0
        return jsonify({"status": "en attente", "received": n, "elapsed_ms": round(elapsed, 2)}), 202

    @app.route("/time", methods=["GET"])
    def get_time():
        ts     = time.time()
        offset = get_chrony_offset()
        return jsonify({"utc": ts, "offset": offset})

    @app.route("/status", methods=["GET"])
    def status():
        with lock:
            n       = len(pending)
            elapsed = (time.monotonic() - window_start) * 1000 if window_start else 0
        return jsonify({
            "received":       n,
            "missing_ips":    [ip for ip in KNOWN_IPS if ip not in pending],
            "elapsed_ms":     round(elapsed, 2),
            "window_ms":      round(WINDOW * 1000, 2),
            "mics":           MIC_POSITIONS.tolist(),
            "speed_of_sound": SPEED_OF_SOUND,
        })

    @app.route("/reset", methods=["POST"])
    def manual_reset():
        with lock:
            reset()
        return jsonify({"status": "reset ok"})

    print("Serveur triangulation sur http://0.0.0.0:5000")
    print(f"  IPs autorisees : {KNOWN_IPS}")
    print(f"  Fenetre d'attente : {WINDOW*1000:.2f} ms")
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_server()