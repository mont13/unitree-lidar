#!/usr/bin/env python3
"""Prohlizec mracna pres Rerun - plynula navigace (orbit + first-person prolet).
Pouziti: rerun_view.py [mracno.pcd]
V okne: drag = orbit, ctrl+scroll = zoom; v nastaveni 3D pohledu prepni na
first-person pro 'prolet' prostorem."""
import os
import sys
import numpy as np
import open3d as o3d
import rerun as rr
import matplotlib.cm as cm

# koren odvozen ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

PCD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "room_map_full.pcd")

pcd = o3d.io.read_point_cloud(PCD)
pts = np.asarray(pcd.points)
if len(pts) == 0:
    print("Prazdne mracno:", PCD); sys.exit(1)

z = pts[:, 2]
zz = (z - z.min()) / (np.ptp(z) + 1e-6)
colors = (cm.turbo(zz)[:, :3] * 255).astype(np.uint8)

rr.init("unitree_l2_mapa", spawn=True)
rr.log("mapa", rr.Points3D(pts, colors=colors, radii=0.015))
print(f"Rerun: nahrano {len(pts)} bodu z {PCD}")
print("Okno: drag=orbit, ctrl+scroll=zoom; prepni na first-person pro prolet prostorem.")
