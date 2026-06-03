#!/usr/bin/env python3
"""Vykresli zachycene mracno bodu (CSV z dump_cloud) do PNG: pohled shora + 3D."""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

csv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "lidar_cloud.csv")
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "lidar_view.png")

d = np.loadtxt(csv, delimiter=",", skiprows=1)
x, y, z = d[:, 0], d[:, 1], d[:, 2]
r = np.sqrt(x * x + y * y + z * z)
m = (r > 0.05) & (r < 30)
x, y, z = x[m], y[m], z[m]
print(f"bodu k vykresleni: {len(x)}")

fig = plt.figure(figsize=(18, 8))

# 1) pohled shora (mapa okoli)
ax1 = fig.add_subplot(1, 2, 1)
sc = ax1.scatter(x, y, c=z, s=0.4, cmap="turbo", linewidths=0)
ax1.scatter([0], [0], c="red", marker="x", s=140, label="LiDAR (0,0)")
ax1.set_aspect("equal")
ax1.set_xlabel("X [m]"); ax1.set_ylabel("Y [m]")
ax1.set_title(f"Pohled shora (X-Y) — {len(x)} bodu, barva = vyska Z")
ax1.legend(loc="upper right"); ax1.grid(alpha=0.2)
plt.colorbar(sc, ax=ax1, label="Z [m]", shrink=0.8)

# 2) 3D perspektiva
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.scatter(x, y, z, c=z, s=0.3, cmap="turbo", linewidths=0)
ax2.set_xlabel("X [m]"); ax2.set_ylabel("Y [m]"); ax2.set_zlabel("Z [m]")
ax2.set_title("3D mracno bodu")
try:
    ax2.set_box_aspect((np.ptp(x), np.ptp(y), np.ptp(z)))
except Exception:
    pass
ax2.view_init(elev=22, azim=-60)

plt.tight_layout()
plt.savefig(out, dpi=110)
print("ulozeno:", out)
