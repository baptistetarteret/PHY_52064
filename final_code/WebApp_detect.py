#!/usr/bin/env python3
import subprocess
import numpy as np
import time
import socket
import json
import threading
import requests
from datetime import datetime, timezone
from collections import deque

# --- CONFIG ---
RATE             = 48000
CHUNK            = 48
CHANNELS         = 2
CARD             = "hw:2,0"
THRESHOLD_FACTOR = 5.0
AMBIENT_WINDOW   = 1000
COOLDOWN_MS      = 200
LOG_FILE         = "/home/phypi30/detections.log"

MASTER_IP           = "192.168.137.10"
MASTER_HTTP_PORT    = 5000
TIME_BROADCAST_PORT = 5001

# --- SYNCHRONISATION TEMPS ---
time_offset      = 0.0
time_offset_lock = threading.Lock()

def time_sync_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", TIME_BROADCAST_PORT))
    while True:
        try:
            data, _  = sock.recvfrom(256)
            t_local  = time.time()
            t_master = json.loads(data.decode())["utc"]
            with time_offset_lock:
                time_offset = t_master - t_local
        except Exception:
            pass

threading.Thread(target=time_sync_listener, daemon=True).start()

def corrected_time_ns():
    return time.time_ns()

# --- ENVOI AU SERVEUR ---

def send_timestamp(ts_s):
    try:
        requests.post(
            f"http://{MASTER_IP}:{MASTER_HTTP_PORT}/timestamp",
            json={"timestamp": ts_s},
            timeout=0.5,
        )
    except Exception as e:
        print(f"  [envoi] erreur : {e}")

# --- DETECTION ---

cmd = [
    "arecord",
    f"--device={CARD}",
    f"--rate={RATE}",
    f"--channels={CHANNELS}",
    "--format=S32_LE",
    "--quiet", "-"
]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

bytes_per_chunk   = CHUNK * CHANNELS * 4
ambient_buf       = deque(maxlen=AMBIENT_WINDOW)
last_detection_ns = 0

print(f"Ecoute — chunk={CHUNK} samples = {1000*CHUNK/RATE:.2f} ms")
print(f"Maitre : {MASTER_IP}:{MASTER_HTTP_PORT}")
print("Ctrl+C pour arreter\n")

with open(LOG_FILE, "a") as log:
    log.write(f"\n--- Session {datetime.now(timezone.utc).isoformat()} ---\n")

try:
    while True:
        raw = proc.stdout.read(bytes_per_chunk)
        if not raw or len(raw) < bytes_per_chunk:
            continue

        ts_ns = corrected_time_ns()

        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64)
        audio   = samples[1::2]

        rms = np.sqrt(np.mean(audio ** 2))
        ambient_buf.append(rms)

        if len(ambient_buf) < 10:
            continue

        ambient   = float(np.median(ambient_buf))
        threshold = ambient * THRESHOLD_FACTOR

        if rms > threshold and rms > 1e6:
            if ts_ns - last_detection_ns > COOLDOWN_MS * 1_000_000:
                last_detection_ns = ts_ns

                ts_s    = ts_ns / 1e9
                unix_ms = ts_ns / 1_000_000
                snr     = 20 * np.log10(rms / (ambient + 1e-12))

                with time_offset_lock:
                    offset_ms = time_offset * 1000

                dt  = datetime.fromtimestamp(ts_s, tz=timezone.utc)
                iso = dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}ms"

                line = (f"[{iso}]  unix={unix_ms:.3f} ms  "
                        f"RMS={rms:.0f}  SNR=+{snr:.1f}dB  "
                        f"offset={offset_ms:+.3f}ms")
                print(line)

                with open(LOG_FILE, "a") as log:
                    log.write(line + "\n")

                threading.Thread(target=send_timestamp, args=(ts_s,), daemon=True).start()

except KeyboardInterrupt:
    print("\nArrete.")
finally:
    proc.terminate()