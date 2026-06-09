#!/usr/bin/env python3
"""Primy USB/serial scan pro Unitree L2 bez C++ SDK parseru.

Pouziti:
  ./scan_serial_direct.py --packets 2000 --out scans/scan_1.pcd

Ctou se syrove Unitree framy z /dev/ttyACM0 @ 4 000 000 baud:
  packet_type 102 = point data, packet_type 104 = IMU.
Point data se prevadi na XYZ stejnymi vzorci jako Unitree SDK header
unitree_lidar_utilities.h a uklada se jako binarni PCD.
"""
from __future__ import annotations

import argparse
import binascii
import glob
import math
import os
import select
import struct
import sys
import tempfile
import termios
import time
from pathlib import Path

import numpy as np


HEADER = b"\x55\xAA\x05\x0A"
TAIL = b"\x00\xFF"

LIDAR_USER_CMD_PACKET_TYPE = 100
LIDAR_ACK_DATA_PACKET_TYPE = 101
LIDAR_POINT_DATA_PACKET_TYPE = 102
LIDAR_IMU_DATA_PACKET_TYPE = 104

USER_CMD_STANDBY_TYPE = 2  # value 0=start, 1=standby


def choose_default_port() -> str:
    for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return "/dev/ttyACM0"


def crc32_unitree(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def make_packet(packet_type: int, payload: bytes, msg_type_check: int = 0) -> bytes:
    packet_size = 12 + len(payload) + 12
    head_and_payload = HEADER + struct.pack("<II", packet_type, packet_size) + payload
    crc = crc32_unitree(payload)
    return head_and_payload + struct.pack("<II2s2s", crc, msg_type_check, b"\x00\x00", TAIL)


def make_start_packet() -> bytes:
    return make_packet(LIDAR_USER_CMD_PACKET_TYPE, struct.pack("<II", USER_CMD_STANDBY_TYPE, 0))


def set_serial_raw_4m(fd: int, baud: int) -> None:
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
    attrs[3] = 0
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1
    speed_const = getattr(termios, f"B{baud}", None)
    if speed_const is None:
        raise RuntimeError(f"Python/termios nezna B{baud}")
    attrs[4] = speed_const
    attrs[5] = speed_const
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


def read_available(fd: int, seconds: float) -> bytes:
    end = time.monotonic() + seconds
    out = bytearray()
    while time.monotonic() < end:
        timeout = max(0.0, min(0.05, end - time.monotonic()))
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            continue
        try:
            chunk = os.read(fd, 65536)
        except BlockingIOError:
            continue
        if not chunk:
            break
        out.extend(chunk)
    return bytes(out)


def iter_frames_from_buffer(buf: bytearray):
    """Yield kompletni Unitree framy a z bufferu zahod zpracovana data."""
    pos = 0
    while True:
        start = buf.find(HEADER, pos)
        if start < 0:
            # Nech max 3 bajty pro pripad, ze zacina splitnuty HEADER.
            if len(buf) > 3:
                del buf[:-3]
            return
        if start > 0:
            del buf[:start]
            start = 0
        if len(buf) < 24:
            return
        packet_type, packet_size = struct.unpack_from("<II", buf, 4)
        if packet_size < 24 or packet_size > 65536:
            del buf[0]
            continue
        if len(buf) < packet_size:
            return
        frame = bytes(buf[:packet_size])
        del buf[:packet_size]
        if frame[-2:] == TAIL:
            yield packet_type, frame


def parse_point_frame(frame: bytes, range_min_user: float, range_max_user: float) -> np.ndarray:
    """Return Nx4 float32 array [x,y,z,intensity] from Unitree packet_type 102."""
    data = memoryview(frame)[12:-12]
    if len(data) < 1020:
        return np.empty((0, 4), dtype=np.float32)

    # Offsets podle unitree_lidar_protocol.h:
    # DataInfo 16 B, LidarInsideState 36 B, LidarCalibParam 32 B.
    calib_off = 16 + 36
    line_off = calib_off + 32
    (
        a_axis_dist,
        b_axis_dist,
        theta_angle_bias,
        alpha_angle_bias,
        beta_angle,
        xi_angle,
        range_bias,
        range_scale,
    ) = struct.unpack_from("<8f", data, calib_off)

    (
        com_horizontal_angle_start,
        com_horizontal_angle_step,
        scan_period,
        range_min_packet,
        range_max_packet,
        angle_min,
        angle_increment,
        time_increment,
        point_num,
    ) = struct.unpack_from("<8fI", data, line_off)
    del scan_period, time_increment

    n = max(0, min(int(point_num), 300))
    if n == 0:
        return np.empty((0, 4), dtype=np.float32)

    ranges_off = line_off + 8 * 4 + 4
    intens_off = ranges_off + 300 * 2
    ranges = np.frombuffer(data[ranges_off : ranges_off + 300 * 2], dtype="<u2", count=300)[:n]
    intensities = np.frombuffer(data[intens_off : intens_off + 300], dtype=np.uint8, count=300)[:n]

    r = range_scale * (ranges.astype(np.float32) + range_bias)
    valid = (
        (ranges >= 1)
        & (r >= range_min_packet)
        & (r <= range_max_packet)
        & (r >= range_min_user)
        & (r <= range_max_user)
    )
    if not np.any(valid):
        return np.empty((0, 4), dtype=np.float32)

    idx = np.arange(n, dtype=np.float32)
    alpha = angle_min + alpha_angle_bias + idx * angle_increment
    theta = com_horizontal_angle_start + theta_angle_bias + idx * com_horizontal_angle_step

    r = r[valid]
    alpha = alpha[valid]
    theta = theta[valid]
    inten = intensities.astype(np.float32)[valid]

    sin_beta = math.sin(beta_angle)
    cos_beta = math.cos(beta_angle)
    sin_xi = math.sin(xi_angle)
    cos_xi = math.cos(xi_angle)
    cos_beta_sin_xi = cos_beta * sin_xi
    sin_beta_cos_xi = sin_beta * cos_xi
    sin_beta_sin_xi = sin_beta * sin_xi
    cos_beta_cos_xi = cos_beta * cos_xi

    sin_alpha = np.sin(alpha)
    cos_alpha = np.cos(alpha)
    sin_theta = np.sin(theta)
    cos_theta = np.cos(theta)

    a = (-cos_beta_sin_xi + sin_beta_cos_xi * sin_alpha) * r + b_axis_dist
    b = cos_alpha * cos_xi * r
    c = (sin_beta_sin_xi + cos_beta_cos_xi * sin_alpha) * r

    x = cos_theta * a - sin_theta * b
    y = sin_theta * a + cos_theta * b
    z = c + a_axis_dist

    return np.column_stack((x, y, z, inten)).astype(np.float32, copy=False)


def write_pcd(path: Path, points_xyzi: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    points_xyzi = np.asarray(points_xyzi, dtype="<f4")
    with path.open("wb") as f:
        header = (
            "# .PCD v0.7\n"
            "VERSION 0.7\n"
            "FIELDS x y z intensity\n"
            "SIZE 4 4 4 4\n"
            "TYPE F F F F\n"
            "COUNT 1 1 1 1\n"
            f"WIDTH {len(points_xyzi)}\n"
            "HEIGHT 1\n"
            "VIEWPOINT 0 0 0 1 0 0 0\n"
            f"POINTS {len(points_xyzi)}\n"
            "DATA binary\n"
        )
        f.write(header.encode("ascii"))
        f.write(points_xyzi.tobytes(order="C"))


def render_png(path: Path, points_xyzi: np.ndarray, max_points: int = 250_000) -> None:
    if len(points_xyzi) == 0:
        return
    os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mpl-lidar-"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pts = points_xyzi
    if len(pts) > max_points:
        rng = np.random.default_rng(42)
        pts = pts[rng.choice(len(pts), size=max_points, replace=False)]
    z = pts[:, 2]

    fig = plt.figure(figsize=(18, 8))
    ax = fig.add_subplot(1, 2, 1)
    sc = ax.scatter(pts[:, 0], pts[:, 1], c=z, s=0.25, cmap="turbo", linewidths=0)
    ax.scatter([0], [0], c="red", marker="x", s=120, label="LiDAR")
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right")
    ax.set_title(f"Pudorys X-Y ({len(points_xyzi)} bodu)")
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


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(description="Primy Unitree L2 USB/serial scan do PCD + PNG")
    parser.add_argument("--port", default=choose_default_port())
    parser.add_argument("--baud", type=int, default=4_000_000)
    parser.add_argument("--packets", type=int, default=2000, help="pocet point-data packetu 102")
    parser.add_argument("--seconds", type=float, default=20.0, help="max delka zaznamu")
    parser.add_argument("--out", default=f"scans/serial_scan_{stamp}.pcd")
    parser.add_argument("--png", default=None, help="default: stejna cesta jako --out, ale .png")
    parser.add_argument("--range-min", type=float, default=0.05)
    parser.add_argument("--range-max", type=float, default=30.0)
    parser.add_argument("--no-start", action="store_true", help="neposilat start command pred ctenim")
    args = parser.parse_args()

    out = Path(args.out)
    png = Path(args.png) if args.png else out.with_suffix(".png")

    fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    chunks: list[np.ndarray] = []
    buf = bytearray()
    point_packets = 0
    imu_packets = 0
    ack_packets = 0
    bytes_read = 0
    started = time.monotonic()
    last_report = started
    try:
        set_serial_raw_4m(fd, args.baud)
        read_available(fd, 0.2)  # drain
        if not args.no_start:
            pkt = make_start_packet()
            for _ in range(3):
                os.write(fd, pkt)
                termios.tcdrain(fd)
                time.sleep(0.12)

        deadline = started + args.seconds
        print(
            f"[scan-serial-direct] ctu {args.port} @ {args.baud}, "
            f"cil {args.packets} packetu / max {args.seconds:.1f}s"
        )
        while point_packets < args.packets and time.monotonic() < deadline:
            data = read_available(fd, 0.15)
            if data:
                bytes_read += len(data)
                buf.extend(data)
                for packet_type, frame in iter_frames_from_buffer(buf):
                    if packet_type == LIDAR_POINT_DATA_PACKET_TYPE:
                        pts = parse_point_frame(frame, args.range_min, args.range_max)
                        if len(pts):
                            chunks.append(pts)
                        point_packets += 1
                    elif packet_type == LIDAR_IMU_DATA_PACKET_TYPE:
                        imu_packets += 1
                    elif packet_type == LIDAR_ACK_DATA_PACKET_TYPE:
                        ack_packets += 1

            now = time.monotonic()
            if now - last_report >= 2.0:
                npts = sum(len(c) for c in chunks)
                print(
                    f"  {point_packets}/{args.packets} point packetu, "
                    f"{imu_packets} IMU, {npts} bodu, {bytes_read/1e6:.1f} MB"
                )
                last_report = now
    finally:
        os.close(fd)

    if chunks:
        points = np.concatenate(chunks, axis=0)
    else:
        points = np.empty((0, 4), dtype=np.float32)

    if len(points) == 0:
        print("CHYBA: neprisel zadny platny point cloud bod.", file=sys.stderr)
        return 1

    ext = points[:, :3].max(axis=0) - points[:, :3].min(axis=0)
    write_pcd(out, points)
    render_png(png, points)
    print("-" * 60)
    print(f"point packety: {point_packets}, IMU packety: {imu_packets}, ACK: {ack_packets}")
    print(f"body: {len(points)}")
    print(f"rozmer X x Y x Z = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} m")
    print(f"ulozeno PCD: {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"ulozeno PNG: {png} ({png.stat().st_size / 1e6:.1f} MB)")
    print("-" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
