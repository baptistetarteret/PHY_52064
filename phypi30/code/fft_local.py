#!/usr/bin/env python3
"""
FFT temps réel dans le terminal — INMP441 Pi3
Dépendances : numpy (déjà installé), arecord (alsa-utils)
"""
import curses
import numpy as np
import subprocess

# --- CONFIG ---
RATE            = 48000
CHUNK           = 4096
CARD            = "hw:2,0"
CHANNELS        = 2
SENSITIVITY_REF = 2**23

BANDS       = [63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
BAND_LABELS = ["63", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]

blackman_win = np.blackman(CHUNK)
freqs        = np.fft.rfftfreq(CHUNK, 1 / RATE)

def get_band_db(fft_db, f_low, f_high):
    mask = (freqs >= f_low) & (freqs < f_high)
    if not np.any(mask):
        return -100.0
    return float(np.max(fft_db[mask]))

def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,  -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_RED,    -1)
    curses.init_pair(4, curses.COLOR_CYAN,   -1)
    stdscr.nodelay(True)

    cmd = [
        "arecord",
        f"--device={CARD}",
        f"--rate={RATE}",
        f"--channels={CHANNELS}",
        "--format=S32_LE",
        "--quiet", "-"
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    peak_hold = [-100.0] * len(BANDS)

    try:
        while True:
            key = stdscr.getch()
            if key == ord('q'):
                break

            # CHUNK samples x 2 canaux x 4 bytes (S32)
            raw = proc.stdout.read(CHUNK * CHANNELS * 4)
            if not raw:
                break

            samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32)
            audio   = samples[::2]  # canal gauche

            windowed = audio * blackman_win
            fft_mag  = np.abs(np.fft.rfft(windowed))
            fft_db   = 20 * np.log10((fft_mag / (SENSITIVITY_REF * (CHUNK / 2))) + 1e-12)
            fft_db   = np.clip(fft_db, -100, 0)

            h, w  = stdscr.getmaxyx()
            bar_h = h - 6

            stdscr.erase()
            stdscr.addstr(0, 2, "FFT INMP441 — Pi3  |  q pour quitter",
                          curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(1, 2, f"Résolution : {RATE/CHUNK:.1f} Hz/pt  |  CHUNK={CHUNK}  |  {RATE} Hz",
                          curses.color_pair(4))

            band_w = max(4, (w - 4) // len(BANDS))

            for i, (label, f) in enumerate(zip(BAND_LABELS, BANDS)):
                f_next = BANDS[i + 1] if i + 1 < len(BANDS) else RATE // 2
                db     = get_band_db(fft_db, f, f_next)

                peak_hold[i] = db if db > peak_hold[i] else max(peak_hold[i] - 0.5, db)

                ratio  = (db + 100) / 100.0
                filled = max(0, min(int(ratio * bar_h), bar_h))
                x      = 2 + i * band_w

                for row in range(bar_h):
                    y = h - 3 - row
                    if y < 2 or x >= w - 1:
                        continue
                    try:
                        if row < filled:
                            color = curses.color_pair(3 if ratio > 0.75 else 2 if ratio > 0.45 else 1)
                            stdscr.addstr(y, x, "█" * min(band_w - 1, w - x - 1), color)
                        else:
                            stdscr.addstr(y, x, "░" * min(band_w - 1, w - x - 1), curses.color_pair(1))
                    except curses.error:
                        pass

                try:
                    stdscr.addstr(h - 2, x, label[:band_w - 1],        curses.color_pair(4))
                    stdscr.addstr(h - 1, x, f"{db:+.0f}"[:band_w - 1], curses.color_pair(4))
                except curses.error:
                    pass

            stdscr.refresh()

    finally:
        proc.terminate()

curses.wrapper(main)
