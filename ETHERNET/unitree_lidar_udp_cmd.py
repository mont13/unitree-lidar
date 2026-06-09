#!/usr/bin/env python3
"""
Send Unitree L2/L24D-style LiDAR commands over Ethernet/UDP.

Official SDK2 defaults are used:
  LiDAR IP/port: 192.168.1.62:6101
  PC/local port: 6201 (PC interface normally 192.168.1.2/24)

Examples:
  sudo python3 unitree_lidar_udp_cmd.py --standby
  sudo python3 unitree_lidar_udp_cmd.py --reset
  sudo python3 unitree_lidar_udp_cmd.py --work-mode 16   # Ethernet + no autostart
"""

import argparse
import binascii
import errno
import select
import socket
import struct
import sys
import time

HEADER = b"\x55\xAA\x05\x0A"
TAIL = b"\x00\xFF"

LIDAR_USER_CMD_PACKET_TYPE = 100
LIDAR_ACK_DATA_PACKET_TYPE = 101
# Public header says 107, but the SDK2 x86_64 lib's setLidarWorkMode()
# actually sends packet_type 2002 with a 4-byte mode payload.
LIDAR_WORK_MODE_CONFIG_PACKET_TYPE = 2002
LIDAR_COMMAND_PACKET_TYPE = 2000

USER_CMD_RESET_TYPE = 1
USER_CMD_STANDBY_TYPE = 2  # value 0=start, 1=standby

CMD_RESET_TYPE = 1
CMD_STANDBY_TYPE = 5

ACK_SUCCESS = 1
ACK_NAMES = {
    1: "ACK_SUCCESS",
    2: "ACK_CRC_ERROR",
    3: "ACK_HEADER_ERROR",
    4: "ACK_BLOCK_ERROR",
    5: "ACK_WAIT_ERROR",
}


def int_auto(value: str) -> int:
    return int(value, 0)


def crc32_unitree(data: bytes) -> int:
    # SDK2 computes the frame CRC over the payload/data only,
    # not over the header + payload.
    return binascii.crc32(data) & 0xFFFFFFFF


def make_packet(packet_type: int, payload: bytes, msg_type_check: int = 0) -> bytes:
    packet_size = 12 + len(payload) + 12
    head_and_payload = HEADER + struct.pack("<II", packet_type, packet_size) + payload
    crc = crc32_unitree(payload)
    return head_and_payload + struct.pack("<II2s2s", crc, msg_type_check, b"\x00\x00", TAIL)


def make_user_cmd(cmd_type: int, cmd_value: int) -> bytes:
    return make_packet(LIDAR_USER_CMD_PACKET_TYPE, struct.pack("<II", cmd_type, cmd_value))


def make_legacy_cmd(cmd_type: int, cmd_value: int) -> bytes:
    return make_packet(LIDAR_COMMAND_PACKET_TYPE, struct.pack("<II", cmd_type, cmd_value))


def make_work_mode(mode: int) -> bytes:
    return make_packet(LIDAR_WORK_MODE_CONFIG_PACKET_TYPE, struct.pack("<I", mode))


def parse_frames(buf: bytes):
    frames = []
    i = 0
    while True:
        start = buf.find(HEADER, i)
        if start < 0 or len(buf) - start < 24:
            break
        packet_type, packet_size = struct.unpack_from("<II", buf, start + 4)
        if packet_size < 24 or packet_size > 65536:
            i = start + 1
            continue
        end = start + packet_size
        if len(buf) < end:
            break
        frame = buf[start:end]
        if frame[-2:] == TAIL:
            frames.append((packet_type, packet_size, frame))
        i = start + 1
    return frames


def describe_frame(packet_type: int, frame: bytes) -> str:
    if packet_type == LIDAR_ACK_DATA_PACKET_TYPE and len(frame) >= 40:
        got_packet_type, cmd_type, cmd_value, status = struct.unpack_from("<IIII", frame, 12)
        return (
            f"ACK: packet_type={got_packet_type}, cmd_type={cmd_type}, "
            f"cmd_value={cmd_value}, status={status} ({ACK_NAMES.get(status, 'unknown')})"
        )
    return f"frame packet_type={packet_type}, size={len(frame)}"


def collect_frames(sock: socket.socket, seconds: float):
    end = time.monotonic() + seconds
    frames = []
    datagrams = 0
    while time.monotonic() < end:
        timeout = max(0.0, min(0.2, end - time.monotonic()))
        r, _, _ = select.select([sock], [], [], timeout)
        if not r:
            continue
        try:
            data, addr = sock.recvfrom(65536)
        except BlockingIOError:
            continue
        datagrams += 1
        parsed = parse_frames(data)
        if parsed:
            for packet_type, packet_size, frame in parsed:
                frames.append((packet_type, packet_size, frame, addr))
        else:
            print(f"  received non-Unitree UDP datagram from {addr}: {len(data)} bytes")
    return frames, datagrams


def ack_success(frames) -> bool:
    for packet_type, _size, frame, _addr in frames:
        if packet_type == LIDAR_ACK_DATA_PACKET_TYPE and len(frame) >= 40:
            _got_packet_type, _cmd_type, _cmd_value, status = struct.unpack_from("<IIII", frame, 12)
            if status == ACK_SUCCESS:
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Unitree LiDAR Ethernet/UDP standby/start/reset/work-mode command")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--standby", action="store_true", help="stop rotation / standby (default)")
    group.add_argument("--start", action="store_true", help="start rotation")
    group.add_argument("--reset", action="store_true", help="reset/reboot LiDAR")
    group.add_argument("--work-mode", type=int_auto, metavar="MODE", help="set work mode uint32, e.g. 0=Ethernet autostart, 16=Ethernet no-autostart, 8=serial autostart, 24=serial no-autostart")
    parser.add_argument("--legacy-too", action="store_true", help="also send legacy packet_type=2000 command for standby/start/reset")
    parser.add_argument("--lidar-ip", default="192.168.1.62", help="LiDAR IP, default: 192.168.1.62")
    parser.add_argument("--lidar-port", type=int, default=6101, help="LiDAR UDP port, default: 6101")
    parser.add_argument("--local-ip", default="0.0.0.0", help="local bind IP, default: 0.0.0.0; official PC IP is 192.168.1.2")
    parser.add_argument("--local-port", type=int, default=6201, help="local UDP port, default: 6201")
    parser.add_argument("--repeat", type=int, default=3, help="send command N times, default: 3")
    parser.add_argument("--listen", type=float, default=2.0, help="seconds to listen for ACK/data after sending, default: 2.0")
    args = parser.parse_args()

    packets = []
    if args.work_mode is not None:
        action = f"work-mode {args.work_mode}"
        packets.append(make_work_mode(args.work_mode))
    elif args.reset:
        action = "reset"
        packets.append(make_user_cmd(USER_CMD_RESET_TYPE, 0))
        if args.legacy_too:
            packets.append(make_legacy_cmd(CMD_RESET_TYPE, 0))
    elif args.start:
        action = "start"
        packets.append(make_user_cmd(USER_CMD_STANDBY_TYPE, 0))
        if args.legacy_too:
            packets.append(make_legacy_cmd(CMD_STANDBY_TYPE, 0))
    else:
        action = "standby"
        packets.append(make_user_cmd(USER_CMD_STANDBY_TYPE, 1))
        if args.legacy_too:
            packets.append(make_legacy_cmd(CMD_STANDBY_TYPE, 1))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(False)

    try:
        sock.bind((args.local_ip, args.local_port))
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(f"ERROR: UDP {args.local_ip}:{args.local_port} is already in use. Stop ROS/Unilidar/SDK first.", file=sys.stderr)
        elif exc.errno == errno.EADDRNOTAVAIL:
            print(f"ERROR: local IP {args.local_ip} is not configured on this PC.", file=sys.stderr)
            print("If using Unitree defaults, set your Ethernet interface to 192.168.1.2/24.", file=sys.stderr)
        else:
            print(f"ERROR: cannot bind UDP {args.local_ip}:{args.local_port}: {exc}", file=sys.stderr)
        return 2

    dest = (args.lidar_ip, args.lidar_port)
    bound_ip, bound_port = sock.getsockname()
    print(f"Opening UDP {bound_ip}:{bound_port} -> {args.lidar_ip}:{args.lidar_port} ...")
    print(f"Sending Unitree LiDAR {action!r} command over Ethernet ...")

    # Drain already queued point/IMU packets, if any.
    collect_frames(sock, 0.2)

    for _ in range(args.repeat):
        for pkt in packets:
            sock.sendto(pkt, dest)
            print(f"  sent {len(pkt)} bytes: {pkt.hex()}")
        time.sleep(0.12)

    frames, datagrams = collect_frames(sock, args.listen)
    if frames:
        for packet_type, _size, frame, addr in frames[:20]:
            print(f"  received from {addr}: {describe_frame(packet_type, frame)}")
        if ack_success(frames):
            print("Done: LiDAR accepted command.")
            if args.work_mode is not None:
                print("Note: a reset/power-cycle may be needed before a work-mode change fully takes effect.")
            return 0
        print("Command was NOT accepted. Check ACK status above.")
        return 1

    if datagrams:
        print("Received UDP datagrams, but no valid Unitree frame/ACK was parsed.")
    else:
        print("No ACK/data frame seen after command.")
    print("Check that the PC Ethernet interface is 192.168.1.2/24, LiDAR is 192.168.1.62, and no other process owns UDP port 6201.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
