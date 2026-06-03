#!/usr/bin/env python3
"""Offscreen render zachyceneho mracna pres Open3D do PNG (hezci nez matplotlib).
Pouziti: .venv/bin/python3 render_o3d.py [PCD] [OUT]"""
import os
import sys
import numpy as np
import open3d as o3d
import matplotlib.cm as cm

# koren odvozeny ze samotneho skriptu (zadne hardcoded cesty)
HERE = os.path.dirname(os.path.abspath(__file__))

# arg-driven: prvni argv = vstupni PCD, druhy argv = vystupni PNG; jinak defaulty
PCD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "lidar_cloud.pcd")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "lidar_view3d.png")

pcd = o3d.io.read_point_cloud(PCD)
pts = np.asarray(pcd.points)
z = pts[:, 2]
zz = (z - z.min()) / (np.ptp(z) + 1e-6)
pcd.colors = o3d.utility.Vector3dVector(cm.turbo(zz)[:, :3])
center = pcd.get_axis_aligned_bounding_box().get_center()


def try_offscreen():
    r = o3d.visualization.rendering.OffscreenRenderer(1400, 900)
    m = o3d.visualization.rendering.MaterialRecord()
    m.shader = "defaultUnlit"
    m.point_size = 2.0
    r.scene.add_geometry("pc", pcd, m)
    r.scene.set_background([0.04, 0.04, 0.07, 1.0])
    eye = center + np.array([-9.0, -9.0, 7.0])
    r.setup_camera(60.0, center, eye, [0, 0, 1])
    o3d.io.write_image(OUT, r.render_to_image())


def try_vis():
    v = o3d.visualization.Visualizer()
    v.create_window(visible=False, width=1400, height=900)
    v.add_geometry(pcd)
    o = v.get_render_option()
    o.point_size = 2.0
    o.background_color = np.array([0.04, 0.04, 0.07])
    vc = v.get_view_control()
    vc.set_up([0, 0, 1]); vc.set_front([-0.6, -0.6, 0.5]); vc.set_zoom(0.45)
    for _ in range(6):
        v.poll_events(); v.update_renderer()
    v.capture_screen_image(OUT, do_render=True)
    v.destroy_window()


try:
    try_offscreen(); print("offscreen OK ->", OUT)
except Exception as e:
    print("offscreen failed:", e)
    try:
        try_vis(); print("visualizer OK ->", OUT)
    except Exception as e2:
        print("visualizer failed:", e2); sys.exit(2)
