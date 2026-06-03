#!/usr/bin/env python3
"""Geometricka 'detekce objektu' z mracna (bez AI):
  - RANSAC roviny (podlaha/steny/strop) -> sede
  - DBSCAN shluky zbytku (objekty) -> barevne + bounding boxy + rozmery
Render do PNG + vypis objektu. Pouziti: segment.py [mracno.pcd] [vystup.png]"""
import os
import sys
import numpy as np
import open3d as o3d
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

PCD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "room_map_full.pcd")
# vystupni PNG: argv prepis zachovan, jinak odvozeno z cesty vstupniho PCD
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.abspath(PCD))[0] + "_segmented.png"

pcd = o3d.io.read_point_cloud(PCD).voxel_down_sample(0.05)
print(f"{len(pcd.points)} bodu (po 5cm downsample)")

# 1) iterativni RANSAC roviny (podlaha, strop, steny)
rest = pcd
planes = []
for _ in range(6):
    if len(rest.points) < 600:
        break
    model, inliers = rest.segment_plane(distance_threshold=0.06, ransac_n=3, num_iterations=1000)
    if len(inliers) < 1000:
        break
    planes.append(rest.select_by_index(inliers))
    rest = rest.select_by_index(inliers, invert=True)

# 2) DBSCAN na zbytku -> objekty
labels = np.array(rest.cluster_dbscan(eps=0.15, min_points=30)) if len(rest.points) else np.array([])
nlab = (labels.max() + 1) if labels.size and labels.max() >= 0 else 0
rpts = np.asarray(rest.points)
objects = []
for k in range(nlab):
    op = rpts[labels == k]
    if len(op) < 40:
        continue
    size = op.max(0) - op.min(0)
    if max(size) > 5.0:        # vyrad zbytky sten
        continue
    objects.append((op, size, op.min(0), op.max(0)))
objects.sort(key=lambda o: -len(o[0]))
print(f"roviny (podlaha/steny/strop): {len(planes)}   objekty (shluky): {len(objects)}")

# render
fig = plt.figure(figsize=(18, 9))
cmap = plt.cm.tab20
ax = fig.add_subplot(1, 2, 1)
for pl in planes:
    p = np.asarray(pl.points); ax.scatter(p[:, 0], p[:, 1], s=0.3, c="lightgray", linewidths=0)
for j, (op, size, mn, mx) in enumerate(objects):
    c = cmap(j % 20)
    ax.scatter(op[:, 0], op[:, 1], s=1.2, color=c, linewidths=0)
    ax.plot([mn[0], mx[0], mx[0], mn[0], mn[0]], [mn[1], mn[1], mx[1], mx[1], mn[1]], color=c, lw=1.2)
    ax.text(mn[0], mx[1], str(j), color=c, fontsize=9, weight="bold")
ax.set_aspect("equal"); ax.grid(alpha=.2)
ax.set_title(f"Pohled shora: {len(planes)} rovin (sede) + {len(objects)} objektu (barevne)")
ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
ax2 = fig.add_subplot(1, 2, 2, projection="3d")
for pl in planes:
    p = np.asarray(pl.points); ax2.scatter(p[:, 0], p[:, 1], p[:, 2], s=0.3, c="lightgray", linewidths=0)
for j, (op, size, mn, mx) in enumerate(objects):
    ax2.scatter(op[:, 0], op[:, 1], op[:, 2], s=1.2, color=cmap(j % 20), linewidths=0)
ax2.set_title("3D: roviny + objekty")
plt.tight_layout(); plt.savefig(OUT, dpi=110)
print("obrazek:", OUT)
print("--- detekovane objekty (rozmery v metrech) ---")
for j, (op, size, mn, mx) in enumerate(objects[:15]):
    print(f"  objekt {j}: {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} m  ({len(op)} bodu)")
