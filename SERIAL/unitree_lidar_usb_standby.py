#!/usr/bin/env python3
"""
Put Unitree L2/L24D-style LiDAR into Standby over USB serial.

Default command is Unitree USER_CMD_STANDBY_TYPE=2, value=1.
Standby should stop both motors and laser/measurement until start command or power cycle.

Usage:
  sudo python3 unitree_lidar_usb_standby.py
  sudo python3 unitree_lidar_usb_standby.py --port /dev/ttyACM0 --start
"""

import argparse
import binascii
import glob
import os
import select
import struct
import sys
import termios
import time

HEADER = b"\x55\xAA\x05\x0A"
TAIL = b"\x00\xFF"

LIDAR_USER_CMD_PACKET_TYPE = 100
LIDAR_COMMAND_PACKET_TYPE = 2000
LIDAR_ACK_DATA_PACKET_TYPE = 101

USER_CMD_RESET_TYPE = 1
USER_CMD_STANDBY_TYPE = 2  # value 0=start, 1=standby
USER_CMD_VERSION_GET = 3

CMD_STANDBY_TYPE = 5       # legacy command packet type

ACK_SUCCESS = 1
ACK_NAMES = {
    1: "ACK_SUCCESS",
    2: "ACK_CRC_ERROR",
    3: "ACK_HEADER_ERROR",
    4: "ACK_BLOCK_ERROR",
    5: "ACK_WAIT_ERROR",
}


def crc32_unitree(data: bytes) -> int:
    # Same polynomial/init/final as Unitree SDK2 utility crc32().
    # Important: SDK2 computes the frame CRC over the payload/data only,
    # not over the header + payload.
    return binascii.crc32(data) & 0xFFFFFFFF


def make_packet(packet_type: int, cmd_type: int, cmd_value: int, msg_type_check: int = 0) -> bytes:
    payload = struct.pack("<II", cmd_type, cmd_value)
    packet_size = 12 + len(payload) + 12
    head_and_payload = HEADER + struct.pack("<II", packet_type, packet_size) + payload
    crc = crc32_unitree(payload)
    return head_and_payload + struct.pack("<II2s2s", crc, msg_type_check, b"\x00\x00", TAIL)


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


def set_serial_raw_4m(fd: int, baud: int):
    attrs = termios.tcgetattr(fd)

    # raw mode: 8N1, no flow control, no echo/canonical processing
    attrs[0] = 0  # iflag
    attrs[1] = 0  # oflag
    attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8  # cflag
    attrs[3] = 0  # lflag

    # VMIN/VTIME for non-blocking-ish reads
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1

    speed_const = getattr(termios, f"B{baud}", None)
    if speed_const is None:
        raise RuntimeError(f"Python/termios on this system does not expose B{baud}")
    attrs[4] = speed_const  # ispeed
    attrs[5] = speed_const  # ospeed

    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


def read_some(fd: int, seconds: float) -> bytes:
    end = time.monotonic() + seconds
    out = bytearray()
    while time.monotonic() < end:
        timeout = max(0.0, min(0.2, end - time.monotonic()))
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


def choose_default_port() -> str:
    for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return "/dev/ttyACM0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Unitree LiDAR USB standby/start command")
    parser.add_argument("--port", default=choose_default_port(), help="serial port, default: auto or /dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=4000000, help="baudrate, default: 4000000")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--standby", action="store_true", help="stop rotation / standby (default)")
    group.add_argument("--start", action="store_true", help="start rotation")
    group.add_argument("--reset", action="store_true", help="reset LiDAR")
    parser.add_argument("--legacy-too", action="store_true", help="also send legacy packet_type=2000 standby/start command")
    parser.add_argument("--repeat", type=int, default=3, help="send command N times, default: 3")
    parser.add_argument("--listen", type=float, default=1.5, help="seconds to listen for ACK after sending, default: 1.5")
    args = parser.parse_args()

    if args.reset:
        action = "reset"
        cmd_type = USER_CMD_RESET_TYPE
        cmd_value = 0
    elif args.start:
        action = "start"
        cmd_type = USER_CMD_STANDBY_TYPE
        cmd_value = 0
    else:
        action = "standby"
        cmd_type = USER_CMD_STANDBY_TYPE
        cmd_value = 1

    print(f"Opening {args.port} at {args.baud} baud ...")
    try:
        fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    except PermissionError:
        print(f"ERROR: permission denied opening {args.port}. Run with sudo:", file=sys.stderr)
        print(f"  sudo python3 {sys.argv[0]} --port {args.port}", file=sys.stderr)
        return 13
    except FileNotFoundError:
        print(f"ERROR: {args.port} not found. Available ports:", file=sys.stderr)
        for p in sorted(glob.glob('/dev/serial/by-id/*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')):
            print(f"  {p}", file=sys.stderr)
        return 2

    try:
        set_serial_raw_4m(fd, args.baud)
        # Drain any cloud data already queued.
        read_some(fd, 0.2)

        packets = [make_packet(LIDAR_USER_CMD_PACKET_TYPE, cmd_type, cmd_value)]
        if args.legacy_too and not args.reset:
            legacy_cmd = CMD_STANDBY_TYPE
            packets.append(make_packet(LIDAR_COMMAND_PACKET_TYPE, legacy_cmd, cmd_value))

        print(f"Sending Unitree LiDAR {action!r} command over USB ...")
        for n in range(args.repeat):
            for pkt in packets:
                os.write(fd, pkt)
                termios.tcdrain(fd)
                print(f"  sent {len(pkt)} bytes: {pkt.hex()}")
            time.sleep(0.12)

        data = read_some(fd, args.listen)
        frames = parse_frames(data)
        if frames:
            for packet_type, _size, frame in frames[:10]:
                print("  received", describe_frame(packet_type, frame))
            ok = False
            for packet_type, _size, frame in frames:
                if packet_type == LIDAR_ACK_DATA_PACKET_TYPE and len(frame) >= 40:
                    got_packet_type, cmd_type, cmd_value, status = struct.unpack_from("<IIII", frame, 12)
                    if status == ACK_SUCCESS:
                        ok = True
            if ok:
                print("Done: LiDAR accepted command.")
                return 0
            else:
                print("Command was NOT accepted. Check ACK status above.")
                return 1
        else:
            print("No ACK/data frame seen after command. If the motor stopped, it still worked.")
            print("If it did NOT stop: LiDAR may still be in Ethernet-only comm mode; use Ethernet/Unilidar or cut 12V power.")
    finally:
        os.close(fd)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
