#!/usr/bin/env python3
"""Zpracuje syrovy sken (room_raw.pcd): voxel downsampling + odstraneni sumu
-> kompaktni komprimovany PCD. Vypise rozmery prostoru a vzdalenosti, vyrenderuje
obrazek a SYROVY soubor SMAZE (uspora mista).
Pouziti: process_scan.py [raw.pcd] [out.pcd] [voxel_m]"""
import sys
import os
import numpy as np
import open3d as o3d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "room_raw.pcd")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "room_scan.pcd")
# BUG fix: PNG odvozeny z vystupni cesty, ne hardcoded
PNG = os.path.splitext(OUT)[0] + ".png"
VOX = float(sys.argv[3]) if len(sys.argv) > 3 else 0.02  # 2 cm

pcd = o3d.io.read_point_cloud(RAW)
n0 = len(pcd.points)
if n0 == 0:
    print("Prazdny sken:", RAW); sys.exit(1)

pcd = pcd.voxel_down_sample(VOX)
pcd, _ = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
n1 = len(pcd.points)
o3d.io.write_point_cloud(OUT, pcd, write_ascii=False, compressed=True)

pts = np.asarray(pcd.points)
dist = np.linalg.norm(pts, axis=1)
ext = pcd.get_axis_aligned_bounding_box().get_extent()
sz_raw = os.path.getsize(RAW) / 1e6
sz_out = os.path.getsize(OUT) / 1e6

print("-" * 60)
print(f"syrovy : {n0:>9d} bodu  ({sz_raw:6.1f} MB)")
print(f"kompakt: {n1:>9d} bodu  ({sz_out:6.2f} MB)  @ voxel {VOX*100:.0f} cm")
print(f"rozmer prostoru  X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")
print(f"vzdalenost od LiDARu: nejblizsi {dist.min():.2f} m | median {np.median(dist):.2f} m | nejdal {dist.max():.2f} m")
print("-" * 60)

# obrazek: pudorys + 3D
z = pts[:, 2]
fig = plt.figure(figsize=(18, 8))
ax = fig.add_subplot(1, 2, 1)
sc = ax.scatter(pts[:, 0], pts[:, 1], c=z, s=0.5, cmap="turbo", linewidths=0)
ax.scatter([0], [0], c="red", marker="x", s=140, label="LiDAR")
ax.set_aspect("equal"); ax.grid(alpha=.2); ax.legend(loc="upper right")
ax.set_title(f"Pudorys (X-Y) — {n1} bodu, barva=vyska"); ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
plt.colorbar(sc, ax=ax, label="Z [m]", shrink=.8)
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=z, s=0.4, cmap="turbo", linewidths=0)
ax2.set_title("3D sken"); ax2.set_xlabel("X"); ax2.set_ylabel("Y"); ax2.set_zlabel("Z")
try:
    ax2.set_box_aspect((np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), np.ptp(pts[:, 2])))
except Exception:
    pass
ax2.view_init(elev=20, azim=-60)
plt.tight_layout(); plt.savefig(PNG, dpi=110)
print("obrazek:", PNG)

# syrovy soubor smaz JEN pokud neni totozny s vystupem (jinak bychom prisli o vysledek)
if os.path.abspath(RAW) != os.path.abspath(OUT):
    os.remove(RAW)
    print("syrovy soubor smazan (uspora mista). Vysledek:", OUT)
else:
    print("syrovy a vystupni soubor jsou totozne - nemazu. Vysledek:", OUT)
