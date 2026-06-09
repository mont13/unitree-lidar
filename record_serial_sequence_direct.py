#!/usr/bin/env python3
"""Primy USB/serial recorder kratkych PCD framu pro lidar-only SLAM.

Navazuje na scan_serial_direct.py, ale misto jednoho dlouheho statickeho PCD
uklada sekvenci kratkych framu:

  measurements/continuous_movement/scans/seq_YYYYMMDD_HHMMSS/000000.pcd
  measurements/continuous_movement/scans/seq_YYYYMMDD_HHMMSS/000001.pcd
  ...

Tyto framy pak umi zpracovat slam_map.py pres KISS-ICP.
"""
from __future__ import annotations

import argparse
import os
import sys
import termios
import time
from pathlib import Path

import numpy as np

from scan_serial_direct import (
    LIDAR_ACK_DATA_PACKET_TYPE,
    LIDAR_IMU_DATA_PACKET_TYPE,
    LIDAR_POINT_DATA_PACKET_TYPE,
    choose_default_port,
    iter_frames_from_buffer,
    make_start_packet,
    parse_point_frame,
    read_available,
    set_serial_raw_4m,
    write_pcd,
)

HERE = Path(__file__).resolve().parent
DEFAULT_SCAN_BASE = HERE / "measurements" / "continuous_movement" / "scans"


def positive_int(value: str) -> int:
    out = int(value)
    if out <= 0:
        raise argparse.ArgumentTypeError("musi byt kladne cislo")
    return out


def make_relative_symlink(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        link.unlink()
    rel = os.path.relpath(target.resolve(), link.parent.resolve())
    link.symlink_to(rel, target_is_directory=target.is_dir())


def main() -> int:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser(
        description="Primy Unitree L2 USB/serial recorder sekvence framu pro KISS-ICP",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--port", default=choose_default_port())
    parser.add_argument("--baud", type=int, default=4_000_000)
    parser.add_argument("--frames", type=positive_int, default=150, help="kolik kratkych PCD framu ulozit")
    parser.add_argument("--seconds", type=float, default=30.0, help="maximalni delka zaznamu")
    parser.add_argument(
        "--packets-per-frame",
        type=positive_int,
        default=20,
        help="kolik point packetu 102 seskupit do jednoho framu",
    )
    parser.add_argument("--min-points-per-frame", type=positive_int, default=1000)
    parser.add_argument("--out-dir", default=str(DEFAULT_SCAN_BASE / f"seq_{stamp}"))
    parser.add_argument("--range-min", type=float, default=0.05)
    parser.add_argument("--range-max", type=float, default=30.0)
    parser.add_argument("--no-start", action="store_true", help="neposilat start command pred ctenim")
    parser.add_argument(
        "--drop-partial-final",
        action="store_true",
        help="na konci nezapisovat nedokonceny frame",
    )
    parser.add_argument(
        "--latest-link",
        default=None,
        help="symlink na posledni sekvenci; default: <out-dir>/../latest_sequence",
    )
    parser.add_argument("--no-latest", action="store_true", help="nevytvaret latest_sequence symlink")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.csv"
    meta_path = out_dir / "meta.txt"

    fd = -1
    buf = bytearray()
    current_chunks: list[np.ndarray] = []
    current_packet_count = 0
    written_frames = 0
    total_point_packets = 0
    total_imu_packets = 0
    total_ack_packets = 0
    total_bytes = 0
    total_points = 0
    started = time.monotonic()
    last_report = started

    def flush_frame(partial: bool = False) -> None:
        nonlocal current_chunks, current_packet_count, written_frames, total_points
        if not current_chunks:
            current_packet_count = 0
            return
        points = np.concatenate(current_chunks, axis=0)
        packet_count = current_packet_count
        current_chunks = []
        current_packet_count = 0
        if len(points) < args.min_points_per_frame:
            print(
                f"  preskakuju {'posledni ' if partial else ''}frame: "
                f"jen {len(points)} bodu < {args.min_points_per_frame}",
                file=sys.stderr,
            )
            return
        frame_path = out_dir / f"{written_frames:06d}.pcd"
        write_pcd(frame_path, points)
        rel_t = time.monotonic() - started
        with index_path.open("a", encoding="utf-8") as idx:
            idx.write(f"{written_frames},{rel_t:.6f},{packet_count},{len(points)},{frame_path.name}\n")
        written_frames += 1
        total_points += len(points)

    try:
        fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        set_serial_raw_4m(fd, args.baud)
        read_available(fd, 0.2)  # drain stareho bufferu
        if not args.no_start:
            pkt = make_start_packet()
            for _ in range(3):
                os.write(fd, pkt)
                termios.tcdrain(fd)
                time.sleep(0.12)

        index_path.write_text("frame,timestamp_rel_s,point_packets,points,file\n", encoding="utf-8")
        deadline = started + args.seconds
        print(
            f"[record-seq-direct] ctu {args.port} @ {args.baud}, "
            f"cil {args.frames} framu / max {args.seconds:.1f}s, "
            f"{args.packets_per_frame} point packetu na frame"
        )
        print(f"[record-seq-direct] vystup: {out_dir}")

        while written_frames < args.frames and time.monotonic() < deadline:
            data = read_available(fd, 0.15)
            if data:
                total_bytes += len(data)
                buf.extend(data)
                for packet_type, frame in iter_frames_from_buffer(buf):
                    if packet_type == LIDAR_POINT_DATA_PACKET_TYPE:
                        pts = parse_point_frame(frame, args.range_min, args.range_max)
                        if len(pts):
                            current_chunks.append(pts)
                        current_packet_count += 1
                        total_point_packets += 1
                        if current_packet_count >= args.packets_per_frame:
                            flush_frame()
                            if written_frames >= args.frames:
                                break
                    elif packet_type == LIDAR_IMU_DATA_PACKET_TYPE:
                        total_imu_packets += 1
                    elif packet_type == LIDAR_ACK_DATA_PACKET_TYPE:
                        total_ack_packets += 1

            now = time.monotonic()
            if now - last_report >= 2.0:
                print(
                    f"  {written_frames}/{args.frames} framu, "
                    f"{total_point_packets} point packetu, {total_imu_packets} IMU, "
                    f"{total_bytes/1e6:.1f} MB"
                )
                last_report = now

        if current_chunks and not args.drop_partial_final and written_frames < args.frames:
            flush_frame(partial=True)

    except PermissionError as e:
        print(f"CHYBA: nemam prava k {args.port}: {e}", file=sys.stderr)
        print("Tip: sudo usermod -aG dialout $USER  # potom odhlasit/prihlasit", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"CHYBA: port {args.port} neexistuje (USB/DC napajeni LiDARu?)", file=sys.stderr)
        return 1
    finally:
        if fd >= 0:
            os.close(fd)

    elapsed = time.monotonic() - started
    meta = (
        "continuous_movement direct sequence\n"
        f"created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"port: {args.port}\n"
        f"baud: {args.baud}\n"
        f"frames_written: {written_frames}\n"
        f"target_frames: {args.frames}\n"
        f"seconds_limit: {args.seconds}\n"
        f"elapsed_s: {elapsed:.3f}\n"
        f"packets_per_frame: {args.packets_per_frame}\n"
        f"min_points_per_frame: {args.min_points_per_frame}\n"
        f"point_packets: {total_point_packets}\n"
        f"imu_packets: {total_imu_packets}\n"
        f"ack_packets: {total_ack_packets}\n"
        f"total_points_written: {total_points}\n"
        f"bytes_read: {total_bytes}\n"
        f"range_min: {args.range_min}\n"
        f"range_max: {args.range_max}\n"
    )
    meta_path.write_text(meta, encoding="utf-8")

    if written_frames == 0:
        print("CHYBA: neulozil se zadny frame.", file=sys.stderr)
        print(f"meta: {meta_path}", file=sys.stderr)
        return 1

    if not args.no_latest:
        latest_link = Path(args.latest_link) if args.latest_link else out_dir.parent / "latest_sequence"
        try:
            make_relative_symlink(out_dir, latest_link)
            print(f"latest sequence: {latest_link} -> {out_dir}")
        except OSError as e:
            print(f"VAROVANI: nejde vytvorit symlink {latest_link}: {e}", file=sys.stderr)

    print("-" * 60)
    print(f"framu: {written_frames}")
    print(f"point packety: {total_point_packets}, IMU packety: {total_imu_packets}, ACK: {total_ack_packets}")
    print(f"body zapsane ve framech: {total_points}")
    print(f"ulozeno: {out_dir}")
    print(f"index: {index_path}")
    print(f"meta: {meta_path}")
    print("-" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
