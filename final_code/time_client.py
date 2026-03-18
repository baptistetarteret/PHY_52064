#!/usr/bin/env python3
"""
Client de synchronisation temps — a lancer sur les Pi esclaves (137.11, 137.12)
Ecoute les broadcasts UDP du Pi maitre (137.10) et calcule le decalage local.

Note : ce script ne modifie pas l'horloge systeme.
       Il calcule le decalage pour corriger les timestamps dans detect_precise.py.
       La synchronisation reelle doit passer par chrony (NTP).
"""
import socket
import json
import time

LISTEN_PORT  = 5001
MASTER_IP    = "192.168.137.10"

print(f"Ecoute broadcast temps depuis {MASTER_IP} sur UDP:{LISTEN_PORT}")
print("Ctrl+C pour arreter\n")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("", LISTEN_PORT))

offsets = []

try:
    while True:
        data, addr = sock.recvfrom(256)
        t_local = time.time()

        msg = json.loads(data.decode())
        t_master = msg["utc"]
        chrony_offset = msg.get("offset")

        # Decalage entre l'horloge locale et le maitre
        diff_ms = (t_local - t_master) * 1000
        offsets.append(diff_ms)
        if len(offsets) > 60:
            offsets.pop(0)

        avg_ms  = sum(offsets) / len(offsets)
        print(f"  maitre={t_master:.6f}  local={t_local:.6f}  "
              f"decalage={diff_ms:+.3f} ms  moy={avg_ms:+.3f} ms  "
              f"(chrony offset maitre={chrony_offset} s)")

except KeyboardInterrupt:
    print("\nArrete.")
finally:
    sock.close()