#!/usr/bin/env python3
"""SLAM: slepi sekvenci snimku (slozka *.pcd z record_seq) do jedne 3D mapy
pomoci KISS-ICP. Mapu prubezne voxel-downsampluje (uspora pameti/disku),
ulozi komprimovany PCD, vypise rozmery a vyrenderuje obrazek.
Pouziti: slam_map.py [slozka_se_snimky] [vystup.pcd] [voxel_m]"""
import sys
import os
import glob
import numpy as np
import open3d as o3d

# koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

SEQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "seq")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "room_map.pcd")
# PNG odvozen z vystupni cesty OUT (ne hardcoded)
PNG = os.path.splitext(OUT)[0] + ".png"
VOX = float(sys.argv[3]) if len(sys.argv) > 3 else 0.03

files = sorted(glob.glob(os.path.join(SEQ, "*.pcd")))
if not files:
    print("Zadne snimky v", SEQ); sys.exit(1)
print(f"{len(files)} snimku ze {SEQ}, spoustim KISS-ICP ...")

from kiss_icp.kiss_icp import KissICP
from kiss_icp.config import KISSConfig
cfg = KISSConfig()
cfg.data.max_range = 30.0
cfg.data.min_range = 0.3
cfg.data.deskew = False          # nemame per-point casy -> deskew off
cfg.mapping.voxel_size = 0.3     # interni mapovaci voxel KISS-ICP (~max_range/100)
odom = KissICP(cfg)

mapc = o3d.geometry.PointCloud()
last_pose = np.eye(4)
n_ok = 0
for i, fp in enumerate(files):
    pts = np.asarray(o3d.io.read_point_cloud(fp).points)
    if len(pts) == 0:
        continue
    ts = np.zeros(len(pts), dtype=np.float64)
    try:
        odom.register_frame(pts, ts)
        last_pose = np.asarray(odom.last_pose)   # 4x4 poza v 1.3.0
        n_ok += 1
    except Exception as e:
        print(f"  pozor: frame {i} register chyba: {e}")
    h = np.c_[pts, np.ones(len(pts))]
    world = (h @ last_pose.T)[:, :3]
    fr = o3d.geometry.PointCloud()
    fr.points = o3d.utility.Vector3dVector(world)
    mapc += fr
    if i % 20 == 19:
        mapc = mapc.voxel_down_sample(VOX)
    if i % 25 == 0:
        print(f"  {i+1}/{len(files)}  mapa ~{len(mapc.points)} bodu")

mapc = mapc.voxel_down_sample(VOX)
if len(mapc.points) > 100:
    mapc, _ = mapc.remove_statistical_outlier(nb_neighbors=15, std_ratio=2.5)
# zajisti existenci vystupniho adresare pred zapisem
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
o3d.io.write_point_cloud(OUT, mapc, write_ascii=False, compressed=True)

pts = np.asarray(mapc.points)
ext = mapc.get_axis_aligned_bounding_box().get_extent()
print("-" * 60)
print(f"MAPA: {len(pts)} bodu, {os.path.getsize(OUT)/1e6:.2f} MB  (zaregistrovano {n_ok}/{len(files)} snimku)")
print(f"rozmer  X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")
print("-" * 60)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
z = pts[:, 2]
fig = plt.figure(figsize=(18, 8))
ax = fig.add_subplot(1, 2, 1)
sc = ax.scatter(pts[:, 0], pts[:, 1], c=z, s=0.3, cmap="turbo", linewidths=0)
ax.set_aspect("equal"); ax.grid(alpha=.2)
ax.set_title(f"Mapa - pudorys ({len(pts)} bodu)"); ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
plt.colorbar(sc, ax=ax, label="Z [m]", shrink=.8)
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=z, s=0.3, cmap="turbo", linewidths=0)
ax2.set_title("3D mapa")
try:
    ax2.set_box_aspect((np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), np.ptp(pts[:, 2])))
except Exception:
    pass
ax2.view_init(elev=20, azim=-60)
plt.tight_layout(); plt.savefig(PNG, dpi=110)
print("obrazek:", PNG)
