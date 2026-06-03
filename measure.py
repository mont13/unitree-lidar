#!/usr/bin/env python3
"""Interaktivni mereni REALNYCH vzdalenosti z mracna (jednotky = metry).
Ovladani: nadrzet SHIFT + leve tlacitko mysi = oznac bod (oznac vic bodu),
pak okno zavri (Q). Vypisu vzdalenost kazdeho bodu od LiDARu i mezi body.
Pouziti: measure.py [mracno.pcd]"""
import os
import sys
import numpy as np
import open3d as o3d
import matplotlib.cm as cm

# koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

# default mracno vedle skriptu; argv prepis zachovan
PCD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "room_scan.pcd")
pcd = o3d.io.read_point_cloud(PCD)
pts = np.asarray(pcd.points)
if len(pts) == 0:
    print("Prazdne mracno:", PCD); sys.exit(1)
z = pts[:, 2]
zz = (z - z.min()) / (np.ptp(z) + 1e-6)
pcd.colors = o3d.utility.Vector3dVector(cm.turbo(zz)[:, :3])

print("SHIFT + leve tlacitko = oznac bod. Oznac napr. 2 body, pak Q = vypis vzdalenosti.")
vis = o3d.visualization.VisualizerWithEditing()
vis.create_window("Mereni vzdalenosti - shift+klik, pak Q", 1280, 800)
vis.add_geometry(pcd)
vis.run()
vis.destroy_window()

idx = vis.get_picked_points()
if not idx:
    print("Nebyl oznacen zadny bod."); sys.exit(0)
P = pts[idx]
print("-" * 50)
for i, p in enumerate(P):
    print(f"bod {i}: ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}) m   vzdalenost od LiDARu = {np.linalg.norm(p):.3f} m")
for i in range(len(P) - 1):
    dd = np.linalg.norm(P[i + 1] - P[i])
    print(f"vzdalenost bod{i} -> bod{i+1} = {dd:.3f} m")
print("-" * 50)
