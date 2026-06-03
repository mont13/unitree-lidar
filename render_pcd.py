#!/usr/bin/env python3
"""Bezdisplejovy render libovolneho .pcd do PNG (pudorys + 3D) pres matplotlib/Agg.
Pouziti: render_pcd.py <vstup.pcd> [vystup.png]"""
import sys
import os
import numpy as np
import open3d as o3d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PCD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "room_map.pcd")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(PCD))[0] + ".png"

pts = np.asarray(o3d.io.read_point_cloud(PCD).points)
if len(pts) == 0:
    print("Prazdne mracno:", PCD); sys.exit(1)
ext = pts.max(0) - pts.min(0)
print(f"{PCD}: {len(pts)} bodu, rozmer X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")

z = pts[:, 2]
fig = plt.figure(figsize=(18, 8))
ax = fig.add_subplot(1, 2, 1)
sc = ax.scatter(pts[:, 0], pts[:, 1], c=z, s=0.3, cmap="turbo", linewidths=0)
ax.set_aspect("equal"); ax.grid(alpha=.2)
ax.set_title(f"Pudorys ({len(pts)} bodu)"); ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
plt.colorbar(sc, ax=ax, label="Z [m]", shrink=.8)
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=z, s=0.3, cmap="turbo", linewidths=0)
ax2.set_title("3D mapa")
try:
    ax2.set_box_aspect((np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), np.ptp(pts[:, 2])))
except Exception:
    pass
ax2.view_init(elev=20, azim=-60)
plt.tight_layout(); plt.savefig(OUT, dpi=110)
print("obrazek:", OUT)
