#!/usr/bin/env python3
"""Jednoduche spojeni dvou statickych Unitree L2 PCD skenu.

Bez Open3D: pouziva jen numpy + matplotlib. Druhy scan se hrube zaregistruje do
souradnic prvniho scanu pres 2D occupancy-grid korelaci v pudorysu, pak se aplikuje
odhad vyskového posunu a vysledek se ulozi jako PCD + PNG.

Typicke pouziti pro aktualni dva skeny:
  ./merge_scans_simple.py scans/latest_usb_scan.pcd scans/latest_usb_scan_pos2.pcd \
      --max-sensor-move 1.2 --out scans/room_merged_$(date +%Y%m%d_%H%M%S).pcd

Poznamka: je to prvni/pracovni merge. Pro presnejsi mapu pouzij Open3D ICP nebo
LiDAR-inertial SLAM, az budou k dispozici dalsi zavislosti/senzory.
"""
from __future__ import annotations

import argparse
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Iterable

import numpy as np


XYZI_DTYPE = np.dtype("<f4")


def normalize_angle_deg(angle: float) -> float:
    """Return angle in (-180, 180]."""
    out = (angle + 180.0) % 360.0 - 180.0
    if out <= -180.0:
        out += 360.0
    return out


def read_pcd_xyzi(path: Path) -> np.ndarray:
    """Read simple binary PCD and return Nx4 float32 [x,y,z,intensity].

    Supports PCD files with FIELDS containing x/y/z and optional intensity, where all
    fields are 4-byte floats with COUNT 1. This matches scan_serial_direct.py output.
    """
    header: dict[str, str] = {}
    header_bytes = 0
    with path.open("rb") as f:
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f"{path}: chybi DATA radek v PCD hlavicce")
            header_bytes += len(line)
            text = line.decode("ascii", errors="replace").strip()
            if text.startswith("#") or not text:
                continue
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                header[parts[0].upper()] = parts[1]
            if parts and parts[0].upper() == "DATA":
                break

        data_kind = header.get("DATA", "").lower()
        if data_kind != "binary":
            raise ValueError(f"{path}: podporuji jen DATA binary, ne {data_kind!r}")

        fields = header.get("FIELDS", "").split()
        sizes = [int(x) for x in header.get("SIZE", "").split()]
        types = header.get("TYPE", "").split()
        counts = [int(x) for x in header.get("COUNT", "").split()]
        points = int(header.get("POINTS", header.get("WIDTH", "0").split()[0]))
        if not fields or len(fields) != len(sizes) or len(fields) != len(types) or len(fields) != len(counts):
            raise ValueError(f"{path}: neocekavana PCD hlavicka")
        if any(size != 4 for size in sizes) or any(t.upper() != "F" for t in types) or any(c != 1 for c in counts):
            raise ValueError(f"{path}: podporuji jen 4B float fields s COUNT 1")
        for required in ("x", "y", "z"):
            if required not in fields:
                raise ValueError(f"{path}: chybi field {required!r}")

        raw = f.read(points * len(fields) * 4)
        expected = points * len(fields) * 4
        if len(raw) != expected:
            raise ValueError(f"{path}: cekal jsem {expected} B dat, prislo {len(raw)} B")

    arr = np.frombuffer(raw, dtype="<f4").reshape(points, len(fields))
    out = np.zeros((points, 4), dtype=np.float32)
    out[:, 0] = arr[:, fields.index("x")]
    out[:, 1] = arr[:, fields.index("y")]
    out[:, 2] = arr[:, fields.index("z")]
    if "intensity" in fields:
        out[:, 3] = arr[:, fields.index("intensity")]
    del header_bytes
    return out


def write_pcd_xyzi(path: Path, points: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pts = np.asarray(points, dtype="<f4")
    with path.open("wb") as f:
        header = (
            "# .PCD v0.7\n"
            "VERSION 0.7\n"
            "FIELDS x y z intensity\n"
            "SIZE 4 4 4 4\n"
            "TYPE F F F F\n"
            "COUNT 1 1 1 1\n"
            f"WIDTH {len(pts)}\n"
            "HEIGHT 1\n"
            "VIEWPOINT 0 0 0 1 0 0 0\n"
            f"POINTS {len(pts)}\n"
            "DATA binary\n"
        )
        f.write(header.encode("ascii"))
        f.write(pts.tobytes(order="C"))


def point_stats(points: np.ndarray) -> str:
    xyz = points[:, :3]
    ext = np.ptp(xyz, axis=0)
    return f"{len(points)} bodu, rozmer X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m"


def rotation_matrix_2d(yaw_deg: float) -> np.ndarray:
    a = math.radians(yaw_deg)
    c = math.cos(a)
    s = math.sin(a)
    return np.array([[c, -s], [s, c]], dtype=np.float32)


def sample_xy_for_registration(
    points: np.ndarray,
    *,
    max_points: int,
    seed: int,
    min_radius: float,
    max_radius: float,
    z_trim: float,
) -> np.ndarray:
    xyz = points[:, :3]
    mask = np.isfinite(xyz).all(axis=1)
    radius = np.linalg.norm(xyz[:, :2], axis=1)
    mask &= (radius >= min_radius) & (radius <= max_radius)
    if not np.any(mask):
        raise ValueError("po filtru nezbyly zadne body pro registraci")

    if z_trim > 0:
        z = xyz[:, 2]
        low, high = np.quantile(z[mask], [z_trim, 1.0 - z_trim])
        mask &= (z >= low) & (z <= high)

    xy = xyz[mask, :2]
    if len(xy) > max_points:
        rng = np.random.default_rng(seed)
        xy = xy[rng.choice(len(xy), size=max_points, replace=False)]
    return np.asarray(xy, dtype=np.float32)


def dilate_grid(grid: np.ndarray, iterations: int = 1) -> np.ndarray:
    out = grid.astype(bool, copy=False)
    for _ in range(iterations):
        b = out
        n = b.copy()
        n[1:, :] |= b[:-1, :]
        n[:-1, :] |= b[1:, :]
        n[:, 1:] |= b[:, :-1]
        n[:, :-1] |= b[:, 1:]
        n[1:, 1:] |= b[:-1, :-1]
        n[:-1, :-1] |= b[1:, 1:]
        n[1:, :-1] |= b[:-1, 1:]
        n[:-1, 1:] |= b[1:, :-1]
        out = n
    return out.astype(np.float32)


def occupancy_grid(centered_xy: np.ndarray, *, res: float, half_extent: float, size: int, dilation: int) -> np.ndarray:
    ij = np.floor((centered_xy + half_extent) / res).astype(np.int32)
    valid = (ij[:, 0] >= 0) & (ij[:, 0] < size) & (ij[:, 1] >= 0) & (ij[:, 1] < size)
    grid = np.zeros((size, size), dtype=np.float32)
    if np.any(valid):
        np.add.at(grid, (ij[valid, 1], ij[valid, 0]), 1.0)
    grid = (grid > 0).astype(np.float32)
    if dilation > 0:
        grid = dilate_grid(grid, iterations=dilation)
    return grid


def fft_xcorr_shift(target: np.ndarray, source: np.ndarray) -> tuple[np.ndarray, float]:
    """Return shift in grid cells that best moves source onto target."""
    h, w = target.shape
    shape = (2 * h, 2 * w)
    corr = np.fft.irfft2(np.fft.rfft2(target, shape) * np.conj(np.fft.rfft2(source, shape)), shape)
    y, x = np.unravel_index(int(np.argmax(corr)), corr.shape)
    score = float(corr[y, x])
    if y > h:
        y -= shape[0]
    if x > w:
        x -= shape[1]
    return np.array([x, y], dtype=np.float32), score


def select_candidate(
    candidates: list[dict[str, object]],
    *,
    max_sensor_move: float,
    min_prior_score_ratio: float,
) -> tuple[dict[str, object], str | None]:
    candidates = sorted(candidates, key=lambda item: float(item["norm_score"]), reverse=True)
    best = candidates[0]
    if max_sensor_move <= 0:
        return best, None

    min_score = float(best["norm_score"]) * min_prior_score_ratio
    close = [
        item
        for item in candidates
        if float(item["sensor_distance_m"]) <= max_sensor_move and float(item["norm_score"]) >= min_score
    ]
    if close:
        chosen = close[0]
        if chosen is not best:
            msg = (
                "vybral jsem kandidata podle prioru pohybu senzoru; absolutne nejlepsi "
                f"mel senzor {float(best['sensor_distance_m']):.2f} m od scan_1"
            )
            return chosen, msg
        return chosen, None

    return best, (
        "zadny kandidat nesplnil --max-sensor-move s dostatecnym score; "
        "beru absolutne nejlepsi registraci"
    )


def evaluate_angles(
    *,
    angles_deg: Iterable[float],
    ref_centered: np.ndarray,
    src_centered: np.ndarray,
    ref_center: np.ndarray,
    src_center: np.ndarray,
    res: float,
    half_extent: float,
    dilation: int,
    max_sensor_move: float,
    min_prior_score_ratio: float,
) -> tuple[dict[str, object], list[dict[str, object]], str | None]:
    size = int(math.ceil((2.0 * half_extent) / res)) + 1
    target_grid = occupancy_grid(ref_centered, res=res, half_extent=half_extent, size=size, dilation=dilation)
    target_cells = float(target_grid.sum())
    candidates: list[dict[str, object]] = []

    for angle in angles_deg:
        yaw = normalize_angle_deg(float(angle))
        rot = rotation_matrix_2d(yaw)
        src_rot = src_centered @ rot.T
        source_grid = occupancy_grid(src_rot, res=res, half_extent=half_extent, size=size, dilation=dilation)
        source_cells = float(source_grid.sum())
        if source_cells <= 0 or target_cells <= 0:
            continue
        shift_cells, raw_score = fft_xcorr_shift(target_grid, source_grid)
        shift_xy = shift_cells * res
        norm_score = raw_score / (math.sqrt(target_cells * source_cells) + 1e-9)
        sensor_xy = (np.array([0.0, 0.0], dtype=np.float32) - src_center) @ rot.T + ref_center + shift_xy
        candidates.append(
            {
                "yaw_deg": yaw,
                "shift_xy": shift_xy.astype(np.float32),
                "sensor_xy": sensor_xy.astype(np.float32),
                "sensor_distance_m": float(np.linalg.norm(sensor_xy)),
                "norm_score": float(norm_score),
                "raw_score": float(raw_score),
                "res": float(res),
                "target_cells": target_cells,
                "source_cells": source_cells,
                "grid_size": size,
            }
        )

    if not candidates:
        raise ValueError("registrace nenasla zadne kandidaty")
    chosen, warning = select_candidate(
        candidates,
        max_sensor_move=max_sensor_move,
        min_prior_score_ratio=min_prior_score_ratio,
    )
    return chosen, sorted(candidates, key=lambda item: float(item["norm_score"]), reverse=True), warning


def register_2d(
    ref_points: np.ndarray,
    src_points: np.ndarray,
    *,
    max_points: int,
    min_radius: float,
    max_radius: float,
    z_trim: float,
    coarse_res: float,
    fine_res: float,
    coarse_yaw_step: float,
    refine_window: float,
    refine_yaw_step: float,
    dilation: int,
    max_sensor_move: float,
    min_prior_score_ratio: float,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[str]]:
    ref_xy = sample_xy_for_registration(
        ref_points,
        max_points=max_points,
        seed=1,
        min_radius=min_radius,
        max_radius=max_radius,
        z_trim=z_trim,
    )
    src_xy = sample_xy_for_registration(
        src_points,
        max_points=max_points,
        seed=2,
        min_radius=min_radius,
        max_radius=max_radius,
        z_trim=z_trim,
    )

    # Median je stabilnejsi nez mean, protoze skeny maji hodne stropu/sten a occlusions.
    ref_center = np.median(ref_xy, axis=0).astype(np.float32)
    src_center = np.median(src_xy, axis=0).astype(np.float32)
    ref_centered = ref_xy - ref_center
    src_centered = src_xy - src_center

    q = np.quantile(np.vstack((ref_centered, src_centered)), [0.002, 0.998], axis=0)
    half_extent = float(max(np.abs(q).max() + 1.5, 4.0))

    warnings: list[str] = []
    coarse_angles = np.arange(-180.0, 180.0 + 0.5 * coarse_yaw_step, coarse_yaw_step)
    coarse, coarse_candidates, coarse_warning = evaluate_angles(
        angles_deg=coarse_angles,
        ref_centered=ref_centered,
        src_centered=src_centered,
        ref_center=ref_center,
        src_center=src_center,
        res=coarse_res,
        half_extent=half_extent,
        dilation=dilation,
        max_sensor_move=max_sensor_move,
        min_prior_score_ratio=min_prior_score_ratio,
    )
    if coarse_warning:
        warnings.append("coarse: " + coarse_warning)

    center_yaw = float(coarse["yaw_deg"])
    fine_angles = np.arange(center_yaw - refine_window, center_yaw + refine_window + 0.5 * refine_yaw_step, refine_yaw_step)
    fine, fine_candidates, fine_warning = evaluate_angles(
        angles_deg=fine_angles,
        ref_centered=ref_centered,
        src_centered=src_centered,
        ref_center=ref_center,
        src_center=src_center,
        res=fine_res,
        half_extent=half_extent,
        dilation=dilation,
        max_sensor_move=max_sensor_move,
        min_prior_score_ratio=min_prior_score_ratio,
    )
    if fine_warning:
        warnings.append("fine: " + fine_warning)

    fine["ref_center"] = ref_center
    fine["src_center"] = src_center
    fine["half_extent"] = half_extent
    fine["registration_ref_points"] = len(ref_xy)
    fine["registration_src_points"] = len(src_xy)
    return fine, coarse_candidates, fine_candidates, warnings


def estimate_z_shift(ref_points: np.ndarray, src_points: np.ndarray, *, mode: str, upper_quantile: float) -> tuple[float, str]:
    if mode == "none":
        return 0.0, "bez vyskového zarovnani"
    if mode == "median":
        return float(np.median(ref_points[:, 2]) - np.median(src_points[:, 2])), "median Z"
    if mode == "lower":
        q = 1.0 - upper_quantile
        return float(np.quantile(ref_points[:, 2], q) - np.quantile(src_points[:, 2], q)), f"dolni kvantil Z q={q:.2f}"
    if mode == "upper":
        q = upper_quantile
        return float(np.quantile(ref_points[:, 2], q) - np.quantile(src_points[:, 2], q)), f"horni kvantil Z q={q:.2f}"
    raise ValueError(f"neznamy z-align mode {mode!r}")


def transform_src_points(src_points: np.ndarray, transform: dict[str, object], dz: float) -> tuple[np.ndarray, np.ndarray]:
    yaw = float(transform["yaw_deg"])
    rot = rotation_matrix_2d(yaw)
    ref_center = np.asarray(transform["ref_center"], dtype=np.float32)
    src_center = np.asarray(transform["src_center"], dtype=np.float32)
    shift_xy = np.asarray(transform["shift_xy"], dtype=np.float32)

    out = src_points.copy()
    out[:, :2] = (src_points[:, :2] - src_center) @ rot.T + ref_center + shift_xy
    out[:, 2] = src_points[:, 2] + dz

    matrix = np.eye(4, dtype=np.float64)
    matrix[:2, :2] = rot.astype(np.float64)
    matrix[:2, 3] = (ref_center + shift_xy - rot @ src_center).astype(np.float64)
    matrix[2, 3] = float(dz)
    return out, matrix


def voxel_downsample_keep_first(points: np.ndarray, voxel: float) -> np.ndarray:
    if voxel <= 0 or len(points) == 0:
        return points
    keys = np.floor(points[:, :3] / voxel).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    return points[np.sort(idx)]


def setup_matplotlib() -> None:
    os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mpl-lidar-"))
    import matplotlib

    matplotlib.use("Agg")


def render_png(path: Path, points: np.ndarray, *, sensor2_xy: np.ndarray, max_points: int = 300_000) -> None:
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
    ax.scatter([0], [0], c="red", marker="x", s=130, label="LiDAR scan_1")
    ax.scatter([sensor2_xy[0]], [sensor2_xy[1]], c="lime", marker="x", s=130, label="LiDAR scan_2")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right")
    ax.set_title(f"Slouceny pudorys X-Y ({len(points)} bodu), barva=Z")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    plt.colorbar(sc, ax=ax, label="Z [m]", shrink=0.8)

    ax2 = fig.add_subplot(1, 2, 2, projection="3d")
    ax2.scatter(pts[:, 0], pts[:, 1], pts[:, 2], c=z, s=0.25, cmap="turbo", linewidths=0)
    ax2.set_title("3D nahled slouceneho mračna")
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


def render_overlay_png(
    path: Path,
    ref_points: np.ndarray,
    src_transformed: np.ndarray,
    *,
    sensor2_xy: np.ndarray,
    max_points_each: int = 180_000,
) -> None:
    setup_matplotlib()
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(7)
    ref = ref_points
    src = src_transformed
    if len(ref) > max_points_each:
        ref = ref[rng.choice(len(ref), size=max_points_each, replace=False)]
    if len(src) > max_points_each:
        src = src[rng.choice(len(src), size=max_points_each, replace=False)]

    fig, ax = plt.subplots(figsize=(10, 9))
    ax.scatter(ref[:, 0], ref[:, 1], s=0.25, c="tab:blue", alpha=0.45, linewidths=0, label="scan_1 reference")
    ax.scatter(src[:, 0], src[:, 1], s=0.25, c="tab:orange", alpha=0.45, linewidths=0, label="scan_2 transformovany")
    ax.scatter([0], [0], c="red", marker="x", s=140, label="LiDAR scan_1")
    ax.scatter([sensor2_xy[0]], [sensor2_xy[1]], c="lime", marker="x", s=140, label="LiDAR scan_2")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", markerscale=4)
    ax.set_title("Kontrola zarovnani: modra=scan_1, oranzova=scan_2")
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=130)
    plt.close(fig)


def write_transform_report(
    path: Path,
    *,
    ref_path: Path,
    src_path: Path,
    out_path: Path,
    transform: dict[str, object],
    matrix: np.ndarray,
    dz: float,
    z_note: str,
    raw_count: int,
    downsampled_count: int,
    voxel: float,
    warnings: list[str],
    coarse_candidates: list[dict[str, object]],
    fine_candidates: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Transformace scan_2 -> scan_1")
    lines.append("")
    lines.append(f"cas: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"reference scan_1: {ref_path}")
    lines.append(f"source scan_2:    {src_path}")
    lines.append(f"vystup:           {out_path}")
    lines.append("")
    lines.append(f"yaw_z_deg: {float(transform['yaw_deg']):.3f}")
    sensor_xy = np.asarray(transform["sensor_xy"], dtype=float)
    shift_xy = np.asarray(transform["shift_xy"], dtype=float)
    lines.append(f"grid_shift_xy_m: [{shift_xy[0]:.3f}, {shift_xy[1]:.3f}]")
    lines.append(f"pozice LiDARu scan_2 ve scan_1: [{sensor_xy[0]:.3f}, {sensor_xy[1]:.3f}, {dz:.3f}] m")
    lines.append(f"sensor_distance_xy_m: {float(transform['sensor_distance_m']):.3f}")
    lines.append(f"z_shift_m: {dz:.3f} ({z_note})")
    lines.append(f"norm_score: {float(transform['norm_score']):.6f}")
    lines.append(f"raw_score: {float(transform['raw_score']):.1f}")
    lines.append(f"voxel_downsample_m: {voxel:.3f}")
    lines.append(f"body pred downsample: {raw_count}")
    lines.append(f"body po downsample:   {downsampled_count}")
    lines.append("")
    if warnings:
        lines.append("## Varovani / poznamky")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.append("## 4x4 matice")
    lines.append("Mapuje sloupcovy vektor [x, y, z, 1]^T ze scan_2 do scan_1.")
    lines.append("")
    for row in matrix:
        lines.append(" ".join(f"{v: .9f}" for v in row))
    lines.append("")
    lines.append("## Top coarse kandidati")
    for item in coarse_candidates[:8]:
        lines.append(
            f"- yaw={float(item['yaw_deg']):7.2f} deg, "
            f"score={float(item['norm_score']):.6f}, "
            f"sensor_xy={np.asarray(item['sensor_xy'])[0]: .3f},{np.asarray(item['sensor_xy'])[1]: .3f}, "
            f"dist={float(item['sensor_distance_m']):.3f} m"
        )
    lines.append("")
    lines.append("## Top fine kandidati")
    for item in fine_candidates[:8]:
        lines.append(
            f"- yaw={float(item['yaw_deg']):7.2f} deg, "
            f"score={float(item['norm_score']):.6f}, "
            f"sensor_xy={np.asarray(item['sensor_xy'])[0]: .3f},{np.asarray(item['sensor_xy'])[1]: .3f}, "
            f"dist={float(item['sensor_distance_m']):.3f} m"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_latest_symlink(target: Path, link: Path) -> None:
    try:
        if link.exists() or link.is_symlink():
            link.unlink()
        rel = os.path.relpath(target, start=link.parent)
        link.symlink_to(rel)
    except OSError as exc:
        print(f"[warn] neumim vytvorit symlink {link}: {exc}")


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(description="Spoji dva staticke PCD skeny bez Open3D")
    parser.add_argument("ref_pcd", type=Path, help="referencni scan_1 PCD")
    parser.add_argument("src_pcd", type=Path, help="scan_2, ktery se transformuje do scan_1")
    parser.add_argument("--out", type=Path, default=Path(f"scans/room_merged_{stamp}.pcd"))
    parser.add_argument("--png", type=Path, default=None, help="default: stejny basename jako --out, .png")
    parser.add_argument("--overlay-png", type=Path, default=None, help="default: stejny basename jako --out, .overlay.png")
    parser.add_argument("--voxel", type=float, default=0.03, help="voxel downsample v metrech; 0 = vypnout")
    parser.add_argument("--max-sensor-move", type=float, default=0.0, help="prior: max XY vzdalenost druhe pozice LiDARu od prvni; 0=vypnuto")
    parser.add_argument("--min-prior-score-ratio", type=float, default=0.92, help="kandidat v prioru musi mit aspon tuto cast top score")
    parser.add_argument("--z-align", choices=("upper", "lower", "median", "none"), default="upper")
    parser.add_argument("--z-upper-quantile", type=float, default=0.95, help="pro --z-align upper; lower pouzije 1-q")
    parser.add_argument("--registration-max-points", type=int, default=250_000)
    parser.add_argument("--registration-min-radius", type=float, default=0.15)
    parser.add_argument("--registration-max-radius", type=float, default=8.0)
    parser.add_argument("--registration-z-trim", type=float, default=0.01, help="oriznout spodni/horni Z okraje pro 2D registraci")
    parser.add_argument("--coarse-res", type=float, default=0.10)
    parser.add_argument("--fine-res", type=float, default=0.05)
    parser.add_argument("--coarse-yaw-step", type=float, default=5.0)
    parser.add_argument("--refine-window", type=float, default=8.0)
    parser.add_argument("--refine-yaw-step", type=float, default=0.5)
    parser.add_argument("--dilation", type=int, default=1, help="dilatace occupancy gridu v bunkach")
    parser.add_argument("--no-latest", action="store_true", help="nevytvaret latest_room_merged symlinky")
    args = parser.parse_args()

    png = args.png if args.png is not None else args.out.with_suffix(".png")
    overlay_png = args.overlay_png if args.overlay_png is not None else args.out.with_suffix(".overlay.png")
    transform_txt = args.out.with_suffix(".transform.txt")

    print(f"[merge] nacitam scan_1: {args.ref_pcd}")
    ref_points = read_pcd_xyzi(args.ref_pcd)
    print(f"        {point_stats(ref_points)}")
    print(f"[merge] nacitam scan_2: {args.src_pcd}")
    src_points = read_pcd_xyzi(args.src_pcd)
    print(f"        {point_stats(src_points)}")

    print("[merge] registrace v pudorysu XY ...")
    transform, coarse_candidates, fine_candidates, warnings = register_2d(
        ref_points,
        src_points,
        max_points=args.registration_max_points,
        min_radius=args.registration_min_radius,
        max_radius=args.registration_max_radius,
        z_trim=args.registration_z_trim,
        coarse_res=args.coarse_res,
        fine_res=args.fine_res,
        coarse_yaw_step=args.coarse_yaw_step,
        refine_window=args.refine_window,
        refine_yaw_step=args.refine_yaw_step,
        dilation=args.dilation,
        max_sensor_move=args.max_sensor_move,
        min_prior_score_ratio=args.min_prior_score_ratio,
    )
    for warning in warnings:
        print(f"[merge][poznamka] {warning}")

    dz, z_note = estimate_z_shift(ref_points, src_points, mode=args.z_align, upper_quantile=args.z_upper_quantile)
    src_transformed, matrix = transform_src_points(src_points, transform, dz)
    sensor_xy = np.asarray(transform["sensor_xy"], dtype=np.float32)

    raw_merged = np.vstack((ref_points, src_transformed)).astype(np.float32, copy=False)
    merged = voxel_downsample_keep_first(raw_merged, args.voxel)

    print("[merge] vysledek transformace scan_2 -> scan_1")
    print(f"        yaw Z: {float(transform['yaw_deg']):.2f} deg")
    print(f"        pozice LiDARu scan_2 v scan_1: x={sensor_xy[0]:.2f}, y={sensor_xy[1]:.2f}, z={dz:.2f} m")
    print(f"        score: {float(transform['norm_score']):.6f}")
    print(f"        Z posun: {dz:.2f} m ({z_note})")
    print(f"        body sloucene: {len(raw_merged)} -> {len(merged)} po voxel {args.voxel:.3f} m")

    write_pcd_xyzi(args.out, merged)
    render_png(png, merged, sensor2_xy=sensor_xy)
    render_overlay_png(overlay_png, ref_points, src_transformed, sensor2_xy=sensor_xy)
    write_transform_report(
        transform_txt,
        ref_path=args.ref_pcd,
        src_path=args.src_pcd,
        out_path=args.out,
        transform=transform,
        matrix=matrix,
        dz=dz,
        z_note=z_note,
        raw_count=len(raw_merged),
        downsampled_count=len(merged),
        voxel=args.voxel,
        warnings=warnings,
        coarse_candidates=coarse_candidates,
        fine_candidates=fine_candidates,
    )

    if not args.no_latest:
        update_latest_symlink(args.out, args.out.parent / "latest_room_merged.pcd")
        update_latest_symlink(png, png.parent / "latest_room_merged.png")
        update_latest_symlink(overlay_png, overlay_png.parent / "latest_room_merged.overlay.png")
        update_latest_symlink(transform_txt, transform_txt.parent / "latest_room_merged.transform.txt")

    print(f"[merge] ulozeno PCD:        {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    print(f"[merge] ulozeno PNG:        {png} ({png.stat().st_size / 1e6:.1f} MB)")
    print(f"[merge] ulozen overlay PNG: {overlay_png} ({overlay_png.stat().st_size / 1e6:.1f} MB)")
    print(f"[merge] ulozen transform:   {transform_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
