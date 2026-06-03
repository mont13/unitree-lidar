#!/usr/bin/env python3
"""Interaktivni 3D prohlizec zachyceneho mracna (.pcd). Otaceni mysi, kolecko=zoom, Q=konec.
Pouziti: python3 view_pcd.py [cesta.pcd]"""
import os
import sys
import numpy as np
import open3d as o3d
import matplotlib.cm as cm

# koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "lidar_cloud.pcd")
pcd = o3d.io.read_point_cloud(path)
pts = np.asarray(pcd.points)
if len(pts) == 0:
    print("Prazdne mracno:", path); sys.exit(1)

z = pts[:, 2]
zz = (z - z.min()) / (np.ptp(z) + 1e-6)
pcd.colors = o3d.utility.Vector3dVector(cm.turbo(zz)[:, :3])

print(f"{len(pts)} bodu. Otaceni levym tlacitkem mysi, kolecko = zoom, Q/Esc = konec.")
o3d.visualization.draw_geometries(
    [pcd, o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5)],
    window_name="Unitree L2 - zachycene mracno", width=1280, height=800)
