#!/usr/bin/env python3
import subprocess
import numpy as np
import sys
import os

# Config micro
CARD = 2
DEVICE = 0
RATE = 48000
CHANNELS = 2
FORMAT = "S32_LE"
CHUNK = 1024

BAR_WIDTH = 40

def rms(data):
    samples = np.frombuffer(data, dtype=np.int32).astype(np.float32)
    samples = samples[1::2]  # canal droit (INMP441 I2S)
    if len(samples) == 0:
        return 0
    return np.sqrt(np.mean(samples**2))

def draw_bar(level, max_level=200_000_000):
    ratio = min(level / max_level, 1.0)
    filled = int(ratio * BAR_WIDTH)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    db = 20 * np.log10(level + 1)

    if ratio < 0.3:
        color = "\033[32m"   # vert
    elif ratio < 0.7:
        color = "\033[33m"   # jaune
    else:
        color = "\033[31m"   # rouge

    reset = "\033[0m"
    return f"{color}[{bar}]{reset} {level:6.0f} RMS  {db:5.1f} dB"

def main():
    print(f"\033[2J\033[H", end="")  # clear screen
    print("🎙️  Détection micro INMP441 — Pi3")
    print(f"   Card {CARD}, Device {DEVICE} | {RATE} Hz | {FORMAT}")
    print("   Ctrl+C pour quitter\n")

    cmd = [
        "arecord",
        f"--device=hw:{CARD},{DEVICE}",
        f"--rate={RATE}",
        f"--channels={CHANNELS}",
        f"--format={FORMAT}",
        "--quiet",
        "-"
    ]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("❌ 'arecord' introuvable. Installe alsa-utils : sudo apt install alsa-utils")
        sys.exit(1)

    # Vérifie que arecord démarre correctement (attend 0.3s)
    import time, select
    time.sleep(0.3)
    if proc.poll() is not None:
        err = proc.stderr.read().decode()
        print(f"❌ arecord a échoué (code {proc.returncode}) :\n{err}")
        sys.exit(1)

    peak = 0
    frame = 0
    try:
        while True:
            data = proc.stdout.read(CHUNK * 4 * 2)  # 4 bytes x 2 canaux
            if not data:
                err = proc.stderr.read().decode()
                print(f"\n❌ Stream terminé prématurément.\n{err}")
                break

            samples = np.frombuffer(data, dtype=np.int32).astype(np.float32)
            left  = samples[::2]
            right = samples[1::2]

            rms_left  = np.sqrt(np.mean(left**2))
            rms_right = np.sqrt(np.mean(right**2))

            frame += 1
            if frame % 5 == 0:  # affiche toutes les 5 frames
                print(f"\r  L: {rms_left:12.0f}  R: {rms_right:12.0f}  "
                      f"| raw L[0]={int(left[0])}  raw R[0]={int(right[0])}   ", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\n✅ Arrêté.")
    finally:
        proc.terminate()

if __name__ == "__main__":
    main()
