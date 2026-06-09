#!/usr/bin/env python3
"""Slouceni tri existujicich statickych scanu podle ulozenych transformaci.

Pouziti pro aktualni data:
  ./merge_three_known_poses.py \
    --scan1 scans/latest_usb_scan.pcd \
    --scan2 scans/latest_usb_scan_pos2.pcd \
    --scan3 scans/latest_usb_scan_pos3.pcd \
    --t2 scans/latest_room_merged.transform.txt \
    --t3 scans/latest_room_merged_pos3.transform.txt \
    --out scans/room_merged_3poses_$(date +%Y%m%d_%H%M%S).pcd

Rozdil proti merge_scans_simple.py:
- tady explicitne pracujeme se 3 raw scany,
- vykreslujeme 3 pozice LiDARu,
- nemenime puvodni merge vystupy.
"""
from __future__ import annotations

import argparse
import os
import tempfile
import time
from pathlib import Path

import numpy as np

from merge_scans_simple import read_pcd_xyzi, write_pcd_xyzi, voxel_downsample_keep_first


def parse_matrix_from_report(path: Path) -> np.ndarray:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## 4x4 matice":
            start = i
            break
    if start is None:
        raise ValueError(f"{path}: nenalezen blok '## 4x4 matice'")

    rows: list[list[float]] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## ") and rows:
            break
        parts = stripped.split()
        if len(parts) != 4:
            continue
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            continue
        if len(rows) == 4:
            break
    if len(rows) != 4:
        raise ValueError(f"{path}: neumim precist 4 radky matice")
    return np.array(rows, dtype=np.float64)


def apply_transform(points_xyzi: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    out = points_xyzi.copy()
    xyz = points_xyzi[:, :3].astype(np.float64, copy=False)
    out[:, :3] = (xyz @ matrix[:3, :3].T + matrix[:3, 3]).astype(np.float32)
    return out


def setup_matplotlib() -> None:
    os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mpl-lidar-"))
    import matplotlib

    matplotlib.use("Agg")


def render_merged_png(path: Path, points: np.ndarray, poses: list[tuple[str, np.ndarray]], max_points: int = 350_000) -> None:
    setup_matplotlib()
    import matplotlib.pyplot as plt

    pts = points
    if len(pts) > max_points:
        rng = np.random.default_rng(42)
        pts = pts[rng.choice(len(pts), size=max_points, replace=False)]
    z = pts[:, 2]

    colors = ["red", "lime", "magenta", "cyan", "yellow"]
    fig = plt.figure(figsize=(18, 8))

    ax = fig.add_subplot(1, 2, 1)
    sc = ax.scatter(pts[:, 0], pts[:, 1], c=z, s=0.22, cmap="turbo", linewidths=0)
    for idx, (label, pose) in enumerate(poses):
        ax.scatter([pose[0]], [pose[1]], c=colors[idx % len(colors)], marker="x", s=150, label=label)
        ax.text(pose[0], pose[1], f"  {idx + 1}", color=colors[idx % len(colors)], fontsize=11, weight="bold")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right")
    ax.set_title(f"Slouceny pudorys X-Y ze 3 pozic ({len(points)} bodu), barva=Z")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    plt.colorbar(sc, ax=ax, label="Z [m]", shrink=0.8)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=z, s=0.22, cmap="turbo", linewidths=0)
    for idx, (label, pose) in enumerate(poses):
        ax2.scatter([pose[0]], [pose[1]], [pose[2]], c=colors[idx % len(colors)], marker="x", s=90, label=label)
    ax2.set_title("3D nahled slouceneho mracna + 3 pozice LiDARu")
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


def render_sources_overlay(path: Path, clouds: list[tuple[str, np.ndarray]], poses: list[tuple[str, np.ndarray]], max_points_each: int = 150_000) -> None:
    setup_matplotlib()
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(7)
    colors = ["tab:blue", "tab:orange", "tab:purple"]
    marker_colors = ["red", "lime", "magenta"]

    fig, ax = plt.subplots(figsize=(10, 9))
    for idx, (label, cloud) in enumerate(clouds):
        pts = cloud
        if len(pts) > max_points_each:
            pts = pts[rng.choice(len(pts), size=max_points_each, replace=False)]
        ax.scatter(pts[:, 0], pts[:, 1], s=0.22, c=colors[idx % len(colors)], alpha=0.42, linewidths=0, label=label)
    for idx, (label, pose) in enumerate(poses):
        ax.scatter([pose[0]], [pose[1]], c=marker_colors[idx % len(marker_colors)], marker="x", s=160, label=label)
        ax.text(pose[0], pose[1], f"  {idx + 1}", color=marker_colors[idx % len(marker_colors)], fontsize=12, weight="bold")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", markerscale=4)
    ax.set_title("Kontrola zarovnani: scan_1 + scan_2 + scan_3")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=130)
    plt.close(fig)


def update_symlink(target: Path, link: Path) -> None:
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(os.path.relpath(target, start=link.parent))


def stats(points: np.ndarray) -> str:
    ext = np.ptp(points[:, :3], axis=0)
    return f"{len(points)} bodu, rozmer X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m"


def write_report(
    path: Path,
    *,
    out: Path,
    scans: list[Path],
    transforms: list[np.ndarray],
    poses: list[tuple[str, np.ndarray]],
    counts: dict[str, int],
    voxel: float,
) -> None:
    lines: list[str] = []
    lines.append("# Merge 3 raw scanu podle znamych transformaci")
    lines.append("")
    lines.append(f"cas: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"vystup: {out}")
    lines.append(f"voxel_downsample_m: {voxel:.3f}")
    lines.append("")
    lines.append("## Vstupni scany")
    for idx, scan in enumerate(scans, start=1):
        lines.append(f"- scan_{idx}: {scan}")
    lines.append("")
    lines.append("## Pozice LiDARu v souradnicich scan_1")
    for label, pose in poses:
        lines.append(f"- {label}: x={pose[0]:.3f}, y={pose[1]:.3f}, z={pose[2]:.3f} m")
    lines.append("")
    lines.append("## Pocty bodu")
    for key, value in counts.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    for idx, matrix in enumerate(transforms, start=1):
        lines.append(f"## Matice scan_{idx} -> scan_1")
        for row in matrix:
            lines.append(" ".join(f"{v: .9f}" for v in row))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(description="Slouci 3 raw PCD scany a ukaze 3 pozice LiDARu")
    parser.add_argument("--scan1", type=Path, default=Path("scans/latest_usb_scan.pcd"))
    parser.add_argument("--scan2", type=Path, default=Path("scans/latest_usb_scan_pos2.pcd"))
    parser.add_argument("--scan3", type=Path, default=Path("scans/latest_usb_scan_pos3.pcd"))
    parser.add_argument("--t2", type=Path, default=Path("scans/latest_room_merged.transform.txt"), help="transform report scan_2 -> scan_1")
    parser.add_argument("--t3", type=Path, default=Path("scans/latest_room_merged_pos3.transform.txt"), help="transform report scan_3 -> scan_1/mapa")
    parser.add_argument("--out", type=Path, default=Path(f"scans/room_merged_3poses_{stamp}.pcd"))
    parser.add_argument("--voxel", type=float, default=0.03)
    parser.add_argument("--no-latest", action="store_true")
    args = parser.parse_args()

    print("[3poses] nacitam raw scany")
    scan1 = read_pcd_xyzi(args.scan1)
    scan2 = read_pcd_xyzi(args.scan2)
    scan3 = read_pcd_xyzi(args.scan3)
    print(f"  scan_1: {stats(scan1)}")
    print(f"  scan_2: {stats(scan2)}")
    print(f"  scan_3: {stats(scan3)}")

    t1 = np.eye(4, dtype=np.float64)
    t2 = parse_matrix_from_report(args.t2)
    t3 = parse_matrix_from_report(args.t3)

    scan2_t = apply_transform(scan2, t2)
    scan3_t = apply_transform(scan3, t3)
    raw = np.vstack((scan1, scan2_t, scan3_t)).astype(np.float32, copy=False)
    merged = voxel_downsample_keep_first(raw, args.voxel)

    poses = [
        ("LiDAR scan_1", t1[:3, 3].copy()),
        ("LiDAR scan_2", t2[:3, 3].copy()),
        ("LiDAR scan_3", t3[:3, 3].copy()),
    ]

    png = args.out.with_suffix(".png")
    overlay = args.out.with_suffix(".overlay.png")
    report = args.out.with_suffix(".report.txt")

    write_pcd_xyzi(args.out, merged)
    render_merged_png(png, merged, poses)
    render_sources_overlay(overlay, [("scan_1", scan1), ("scan_2", scan2_t), ("scan_3", scan3_t)], poses)
    write_report(
        report,
        out=args.out,
        scans=[args.scan1, args.scan2, args.scan3],
        transforms=[t1, t2, t3],
        poses=poses,
        counts={
            "scan_1_raw": len(scan1),
            "scan_2_raw": len(scan2),
            "scan_3_raw": len(scan3),
            "pred_downsample": len(raw),
            "po_downsample": len(merged),
        },
        voxel=args.voxel,
    )

    if not args.no_latest:
        update_symlink(args.out, args.out.parent / "latest_room_merged_3poses.pcd")
        update_symlink(png, png.parent / "latest_room_merged_3poses.png")
        update_symlink(overlay, overlay.parent / "latest_room_merged_3poses.overlay.png")
        update_symlink(report, report.parent / "latest_room_merged_3poses.report.txt")

    print(f"[3poses] raw body: {len(raw)} -> po voxel {args.voxel:.3f} m: {len(merged)}")
    for label, pose in poses:
        print(f"[3poses] {label}: x={pose[0]:.3f}, y={pose[1]:.3f}, z={pose[2]:.3f} m")
    print(f"[3poses] ulozeno PCD:     {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    print(f"[3poses] ulozeno PNG:     {png} ({png.stat().st_size / 1e6:.1f} MB)")
    print(f"[3poses] ulozen overlay:  {overlay} ({overlay.stat().st_size / 1e6:.1f} MB)")
    print(f"[3poses] ulozen report:   {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
