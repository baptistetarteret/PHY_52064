#!/usr/bin/env python3
"""
Détection sonore avec timestamp UTC précis à la milliseconde
INMP441 — Pi3 — synchronisé chrony
"""
import subprocess
import numpy as np
import time
from datetime import datetime, timezone
from collections import deque

# --- CONFIG ---
RATE         = 48000
CHUNK        = 48        # 1 ms par buffer (48 samples @ 48kHz)
CHANNELS     = 2
CARD         = "hw:2,0"

# Seuil de détection
THRESHOLD_FACTOR = 5.0   # détecte si RMS > THRESHOLD_FACTOR * bruit_ambiant
AMBIENT_WINDOW   = 1000   # nombre de buffers pour estimer le bruit ambiant (~200ms)
COOLDOWN_MS      = 200   # ms minimum entre deux détections

LOG_FILE = "/home/phypi30/detections.log"

# --- LANCEMENT ARECORD ---
cmd = [
    "arecord",
    f"--device={CARD}",
    f"--rate={RATE}",
    f"--channels={CHANNELS}",
    "--format=S32_LE",
    "--quiet", "-"
]
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

bytes_per_chunk = CHUNK * CHANNELS * 4  # S32 = 4 bytes
ambient_buf = deque(maxlen=AMBIENT_WINDOW)
last_detection_ns = 0

print(f"Écoute en cours — chunk={CHUNK} samples = {1000*CHUNK/RATE:.2f} ms")
print(f"Seuil : x{THRESHOLD_FACTOR} le bruit ambiant")
print(f"Log   : {LOG_FILE}")
print("Ctrl+C pour arrêter\n")

with open(LOG_FILE, "a") as log:
    log.write(f"\n--- Session démarrée {datetime.now(timezone.utc).isoformat()} ---\n")

try:
    while True:
        raw = proc.stdout.read(bytes_per_chunk)
        if not raw or len(raw) < bytes_per_chunk:
            continue

        # ⚡ Timestamp capturé IMMÉDIATEMENT après la lecture
        ts_ns = time.time_ns()

        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64)
        audio   = samples[1::2]  # canal droit (INMP441)

        rms = np.sqrt(np.mean(audio ** 2))
        ambient_buf.append(rms)

        # Bruit ambiant = médiane des derniers buffers
        if len(ambient_buf) < 10:
            continue
        ambient = float(np.median(ambient_buf))
        threshold = ambient * THRESHOLD_FACTOR

        # Détection
        if rms > threshold and rms > 1e6:  # garde-fou anti-silence total
            cooldown_ns = COOLDOWN_MS * 1_000_000
            if ts_ns - last_detection_ns > cooldown_ns:
                last_detection_ns = ts_ns

                # Timestamp précis
                dt = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)
                iso = dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}ms"
                unix_ms = ts_ns / 1_000_000

                # Niveau relatif au bruit
                snr = 20 * np.log10(rms / (ambient + 1e-12))

                line = f"[{iso}]  unix={unix_ms:.3f} ms  RMS={rms:.0f}  SNR=+{snr:.1f}dB  ambiant={ambient:.0f}"
                print(line)

                with open(LOG_FILE, "a") as log:
                    log.write(line + "\n")

except KeyboardInterrupt:
    print("\nArrêté.")
finally:
    proc.terminate()