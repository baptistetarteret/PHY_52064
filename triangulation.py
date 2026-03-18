#!/usr/bin/env python3
import numpy as np
from scipy.optimize import minimize

SPEED_OF_SOUND = 343.0

MIC_POSITIONS = np.array([
    [0.0,  0.0],
    [10.0,  0.0],
    [0.0,  10],
])

SOURCE_POS   = [10, 7]
T_EMISSION   = 0.0
NOISE_STD_MS = 0.5  # ecart-type du bruit en millisecondes


def compute_timestamps(source_pos, mic_pos, t_emission, c=SPEED_OF_SOUND):
    distances  = np.array([np.linalg.norm(np.array(source_pos) - mic) for mic in mic_pos])
    delays     = distances / c
    return t_emission + delays, distances, delays


def tdoa_triangulate(mic_pos, timestamps, c=SPEED_OF_SOUND):
    ref     = np.argmin(timestamps)
    delta_d = c * (timestamps - timestamps[ref])

    def cost(source):
        d_ref = np.linalg.norm(source - mic_pos[ref])
        return sum((np.linalg.norm(source - mic_pos[i]) - d_ref - delta_d[i]) ** 2
                   for i in range(len(mic_pos)))

    result = minimize(cost, np.mean(mic_pos, axis=0), method="Nelder-Mead",
                      options={"xatol": 1e-6, "fatol": 1e-12, "maxiter": 100000})
    return result.x, result.fun


timestamps, distances, delays = compute_timestamps(SOURCE_POS, MIC_POSITIONS, T_EMISSION)
noise      = np.abs(np.random.normal(0, NOISE_STD_MS / 1000, size=len(MIC_POSITIONS)))
timestamps_noisy = timestamps + noise
source, residual = tdoa_triangulate(MIC_POSITIONS, timestamps_noisy)

print("=" * 55)
print(f"  Source reelle    : ({SOURCE_POS[0]:.4f}, {SOURCE_POS[1]:.4f}) m")
print(f"  Source estimee   : ({source[0]:.4f}, {source[1]:.4f}) m")
err = np.linalg.norm(source - np.array(SOURCE_POS))
print(f"  Erreur           : {err*1000:.4f} mm")
print(f"  Residu           : {residual:.2e}")
print("=" * 55)

for i in range(len(MIC_POSITIONS)):
    print(f"  Micro {i+1} : t_reel={timestamps[i]*1000:.4f} ms  bruit={noise[i]*1000:+.4f} ms  t_mesure={timestamps_noisy[i]*1000:.4f} ms")