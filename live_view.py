#!/usr/bin/env python3
"""Zivy 3D prohlizec mracna. Cte snimky ze stdin (z programu stream_cloud) a
prubezne aktualizuje Open3D okno. Barva = vyska Z.
Pouziti:  stream_cloud serial | python3 live_view.py
          stream_cloud udp    | python3 live_view.py
V okne: leve tlacitko mysi = otaceni, kolecko = zoom, Q/Esc = konec."""
import sys
import numpy as np
import open3d as o3d
import matplotlib.cm as cm


def read_frame(f):
    while True:
        line = f.readline()
        if not line:
            return None
        if line[:1] == 'F':
            try:
                n = int(line.split()[1])
            except (IndexError, ValueError):
                continue
            rows = []
            while len(rows) < n:
                parts = f.readline().split()
                if len(parts) >= 3:
                    rows.append(parts[:4])
            return np.array(rows, dtype=float)


vis = o3d.visualization.Visualizer()
vis.create_window("Unitree L2 - ZIVE (Q=konec)", 1280, 800)
opt = vis.get_render_option()
opt.point_size = 1.5
opt.background_color = np.array([0.05, 0.05, 0.08])
pcd = o3d.geometry.PointCloud()
added = False
print("Zivy nahled bezi. V okne: mys = otaceni, kolecko = zoom, Q = konec.")

while True:
    d = read_frame(sys.stdin)
    if d is None:
        break
    pts = d[:, :3]
    z = pts[:, 2]
    zz = (z - z.min()) / (np.ptp(z) + 1e-6)
    pcd.points = o3d.utility.Vector3dVector(pts)
    pcd.colors = o3d.utility.Vector3dVector(cm.turbo(zz)[:, :3])
    if not added:
        vis.add_geometry(pcd)
        added = True
    else:
        vis.update_geometry(pcd)
    if not vis.poll_events():
        break
    vis.update_renderer()

vis.destroy_window()
