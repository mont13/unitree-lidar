#!/usr/bin/env python3
"""Jednoduche slozeni pohybove sekvence bez Open3D/KISS-ICP.

Pracovni fallback pro continuous_movement, kdyz neni nainstalovane .venv.
Pouziva jen numpy + scipy + matplotlib. Registruje kratke PCD framy postupne
2D point-to-point ICP do lokalni mapy v pudorysu XY a ulozi PCD + PNG.

Neni to plnohodnotny SLAM: nema deskew, IMU ani loop closure. Slouzi jako rychly
nahled, jestli pohybova sekvence dava smysl.
"""
from __future__ import annotations

import argparse
import math
import os
import tempfile
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from merge_scans_simple import read_pcd_xyzi, voxel_downsample_keep_first, write_pcd_xyzi

HERE = Path(__file__).resolve().parent
DEFAULT_SEQ = HERE / "measurements" / "continuous_movement" / "scans" / "latest_sequence"
DEFAULT_RESULTS = HERE / "measurements" / "continuous_movement" / "results"


def transform_xy(xy: np.ndarray, pose: np.ndarray) -> np.ndarray:
    return xy @ pose[:2, :2].T + pose[:2, 2]


def transform_points(points: np.ndarray, pose: np.ndarray) -> np.ndarray:
    out = points.copy()
    out[:, :2] = transform_xy(points[:, :2], pose)
    return out


def yaw_from_pose(pose: np.ndarray) -> float:
    return math.degrees(math.atan2(float(pose[1, 0]), float(pose[0, 0])))


def select_registration_xy(points: np.ndarray, *, max_points: int, seed: int) -> np.ndarray:
    xyz = points[:, :3]
    mask = np.isfinite(xyz).all(axis=1)
    r = np.linalg.norm(xyz[:, :2], axis=1)
    mask &= (r >= 0.20) & (r <= 8.0)
    if np.any(mask):
        z = xyz[mask, 2]
        lo, hi = np.quantile(z, [0.03, 0.97])
        mask &= (xyz[:, 2] >= lo) & (xyz[:, 2] <= hi)
    xy = xyz[mask, :2]
    if len(xy) > max_points:
        rng = np.random.default_rng(seed)
        xy = xy[rng.choice(len(xy), size=max_points, replace=False)]
    return np.asarray(xy, dtype=np.float64)


def rigid_delta_2d(src_world: np.ndarray, dst_world: np.ndarray) -> np.ndarray:
    src_c = src_world.mean(axis=0)
    dst_c = dst_world.mean(axis=0)
    a = src_world - src_c
    b = dst_world - dst_c
    h = a.T @ b
    u, _, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0:
        vt[-1, :] *= -1
        r = vt.T @ u.T
    t = dst_c - r @ src_c
    delta = np.eye(3, dtype=np.float64)
    delta[:2, :2] = r
    delta[:2, 2] = t
    return delta


def icp_to_map(
    src_xy_local: np.ndarray,
    map_xy: np.ndarray,
    init_pose: np.ndarray,
    *,
    max_corr: float,
    iterations: int,
    trim_quantile: float,
) -> tuple[np.ndarray, float, int]:
    if len(src_xy_local) < 20 or len(map_xy) < 20:
        return init_pose.copy(), float("nan"), 0

    tree = cKDTree(map_xy)
    pose = init_pose.copy()
    last_rmse = float("inf")
    used = 0
    for _ in range(iterations):
        src_world = transform_xy(src_xy_local, pose)
        dist, idx = tree.query(src_world, k=1, distance_upper_bound=max_corr)
        valid = np.isfinite(dist) & (idx < len(map_xy))
        if int(valid.sum()) < 30:
            break
        valid_idx = np.flatnonzero(valid)
        if trim_quantile < 1.0 and len(valid_idx) > 50:
            cutoff = np.quantile(dist[valid_idx], trim_quantile)
            valid_idx = valid_idx[dist[valid_idx] <= cutoff]
        if len(valid_idx) < 30:
            break
        src_sel = src_world[valid_idx]
        dst_sel = map_xy[idx[valid_idx]]
        delta = rigid_delta_2d(src_sel, dst_sel)
        pose = delta @ pose
        rmse = float(np.sqrt(np.mean(np.sum((transform_xy(src_xy_local, pose)[valid_idx] - dst_sel) ** 2, axis=1))))
        used = len(valid_idx)
        if abs(last_rmse - rmse) < 1e-4:
            last_rmse = rmse
            break
        last_rmse = rmse
    return pose, last_rmse, used


def setup_matplotlib() -> None:
    os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mpl-lidar-"))
    import matplotlib
    matplotlib.use("Agg")


def render_png(path: Path, points: np.ndarray, trajectory: np.ndarray, *, max_points: int = 300_000) -> None:
    if len(points) == 0:
        return
    setup_matplotlib()
    import matplotlib.pyplot as plt

    pts = points
    if len(pts) > max_points:
        rng = np.random.default_rng(42)
        pts = pts[rng.choice(len(pts), size=max_points, replace=False)]
    z = pts[:, 2]

    fig = plt.figure(figsize=(18, 8))
    ax = fig.add_subplot(1, 2, 1)
    sc = ax.scatter(pts[:, 0], pts[:, 1], c=z, s=0.25, cmap="turbo", linewidths=0)
    if len(trajectory):
        ax.plot(trajectory[:, 0], trajectory[:, 1], c="white", lw=2.0, alpha=0.9, label="odhad trajektorie")
        ax.scatter(trajectory[:1, 0], trajectory[:1, 1], c="lime", marker="o", s=80, label="start")
        ax.scatter(trajectory[-1:, 0], trajectory[-1:, 1], c="red", marker="x", s=100, label="konec")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right")
    ax.set_title(f"Continuous movement fallback mapa ({len(points)} bodu), barva=Z")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    plt.colorbar(sc, ax=ax, label="Z [m]", shrink=0.8)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=z, s=0.25, cmap="turbo", linewidths=0)
    ax2.set_title("3D nahled")
    ax2.set_xlabel("X [m]")
    ax2.set_ylabel("Y [m]")
    ax2.set_zlabel("Z [m]")
    try:
        ax2.set_box_aspect((np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), np.ptp(pts[:, 2])))
    except Exception:
        pass
    ax2.view_init(elev=20, azim=-60)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=110)
    plt.close(fig)


def update_symlink(target: Path, link: Path) -> None:
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(os.path.relpath(target, start=link.parent))


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    ap = argparse.ArgumentParser(description="Fallback continuous movement map bez Open3D/KISS-ICP")
    ap.add_argument("sequence", nargs="?", type=Path, default=DEFAULT_SEQ)
    ap.add_argument("out", nargs="?", type=Path, default=DEFAULT_RESULTS / f"continuous_map_simple_{stamp}.pcd")
    ap.add_argument("--voxel", type=float, default=0.03)
    ap.add_argument("--reg-voxel", type=float, default=0.05)
    ap.add_argument("--max-reg-points", type=int, default=3500)
    ap.add_argument("--map-reg-points", type=int, default=50000)
    ap.add_argument("--max-corr", type=float, default=0.30)
    ap.add_argument("--iterations", type=int, default=12)
    ap.add_argument("--trim-quantile", type=float, default=0.80)
    ap.add_argument("--max-frames", type=int, default=0, help="0 = vsechny")
    args = ap.parse_args()

    seq = args.sequence.resolve()
    files = sorted(seq.glob("*.pcd"))
    if args.max_frames > 0:
        files = files[: args.max_frames]
    if not files:
        print(f"CHYBA: zadne PCD framy v {seq}")
        return 1

    print(f"[simple-map] sekvence: {seq}")
    print(f"[simple-map] framu: {len(files)}")

    frames = [read_pcd_xyzi(fp) for fp in files]
    pose = np.eye(3, dtype=np.float64)
    poses = [pose.copy()]
    transformed_frames: list[np.ndarray] = [transform_points(frames[0], pose)]
    map_points = voxel_downsample_keep_first(transformed_frames[0], args.reg_voxel)
    map_xy = select_registration_xy(map_points, max_points=args.map_reg_points, seed=100)
    report_lines = ["frame,points,used_corr,rmse,yaw_deg,x,y"]
    report_lines.append(f"0,{len(frames[0])},0,nan,0.000,0.000,0.000")

    for i, pts in enumerate(frames[1:], start=1):
        src_xy = select_registration_xy(pts, max_points=args.max_reg_points, seed=i)
        new_pose, rmse, used = icp_to_map(
            src_xy,
            map_xy,
            pose,
            max_corr=args.max_corr,
            iterations=args.iterations,
            trim_quantile=args.trim_quantile,
        )
        if used < 30 or not np.isfinite(rmse):
            # Kdyz registrace selze, nechame posledni pozu; lepsi nez nahodny skok.
            new_pose = pose.copy()
        pose = new_pose
        poses.append(pose.copy())
        world = transform_points(pts, pose)
        transformed_frames.append(world)
        map_points = voxel_downsample_keep_first(np.vstack((map_points, world)), args.reg_voxel)
        map_xy = select_registration_xy(map_points, max_points=args.map_reg_points, seed=100 + i)
        report_lines.append(f"{i},{len(pts)},{used},{rmse:.5f},{yaw_from_pose(pose):.3f},{pose[0,2]:.4f},{pose[1,2]:.4f}")
        if i % 10 == 0 or i == len(frames) - 1:
            print(f"  {i+1}/{len(frames)} frame, mapa_reg={len(map_points)} bodu, rmse={rmse:.3f}, used={used}")

    merged_raw = np.vstack(transformed_frames).astype(np.float32, copy=False)
    merged = voxel_downsample_keep_first(merged_raw, args.voxel)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    png = args.out.with_suffix(".png")
    report = args.out.with_suffix(".report.csv")
    write_pcd_xyzi(args.out, merged)
    traj = np.array([[p[0, 2], p[1, 2]] for p in poses], dtype=np.float64)
    render_png(png, merged, traj)
    report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    update_symlink(args.out, args.out.parent / "latest_map_simple.pcd")
    update_symlink(png, png.parent / "latest_map_simple.png")
    update_symlink(report, report.parent / "latest_map_simple.report.csv")
    update_symlink(args.out, args.out.parent / "latest_map.pcd")
    update_symlink(png, png.parent / "latest_map.png")

    ext = np.ptp(merged[:, :3], axis=0)
    print("-" * 60)
    print(f"MAPA SIMPLE: {len(merged)} bodu, rozmer X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")
    print(f"PCD: {args.out} ({args.out.stat().st_size/1e6:.1f} MB)")
    print(f"PNG: {png} ({png.stat().st_size/1e6:.1f} MB)")
    print(f"REPORT: {report}")
    print("poznamka: fallback bez IMU/KISS; ber jako rychly nahled, ne finalni SLAM")
    print("-" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
