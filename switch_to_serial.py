#!/usr/bin/env python3
import socket
import time
import sys

# Raw UDP packet for LidarWorkModeConfigPacket (mode = 8, serial)
# 0x55, 0xaa, 0x05, 0x0a -> Header magic
# 0x6b, 0x00, 0x00, 0x00 -> Packet type 107 (LIDAR_WORK_MODE_CONFIG_PACKET_TYPE)
# 0x1c, 0x00, 0x00, 0x00 -> Packet size 28
# 0x08, 0x00, 0x00, 0x00 -> Mode 8 (Serial)
# 0xd2, 0x21, 0x6a, 0xf6 -> CRC32 checksum (0xf66a21d2)
# 0x00, 0x00, 0x00, 0x00 -> Msg type check
# 0x00, 0x00, 0x00, 0xff -> Reserve + Tail magic
PACKET_BYTES = b'\x55\xaa\x05\x0a\x6b\x00\x00\x00\x1c\x00\x00\x00\x08\x00\x00\x00\xd2\x21\x6a\xf6\x00\x00\x00\x00\x00\x00\x00\xff'

LIDAR_IP = "192.168.1.62"
LIDAR_PORT = 6101
LOCAL_PORT = 6201

def main():
    print("=== Unitree LiDAR L2 Serial Switcher (UDP) ===")
    print("Návod k použití na druhém PC:")
    print("1. Propoj LiDAR ethernetovým kabelem přímo s tímto druhým PC.")
    print("2. Nastav na ethernetové kartě tohoto PC statickou IP adresu: 192.168.1.2")
    print("   Maska podsítě: 255.255.255.0")
    print("3. Zapoj LiDAR do 12V napájení a ujisti se, že běží (točí se).")
    print("4. Spusť tento skript.")
    print("-" * 46)

    # Vytvoření UDP socketu
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Bind na port 6201, který LiDAR očekává jako zdrojový port pro komunikaci
        sock.bind(('', LOCAL_PORT))
    except Exception as e:
        print(f"CHYBA: Nepodařilo se vytvořit nebo nabindovat socket: {e}", file=sys.stderr)
        print("Ujisti se, že na portu 6201 neběží jiný program.", file=sys.stderr)
        sys.exit(1)

    print(f"Odesílám příkaz pro přepnutí na SERIAL (workMode 8) na {LIDAR_IP}:{LIDAR_PORT}...")
    
    # Odesíláme paket opakovaně v průběhu 2 sekund, abychom měli jistotu, že dorazí
    for i in range(20):
        try:
            sock.sendto(PACKET_BYTES, (LIDAR_IP, LIDAR_PORT))
            time.sleep(0.1)
        except Exception as e:
            print(f"Chyba při odesílání paketu: {e}", file=sys.stderr)
            sys.exit(1)

    print("\n>>> PŘÍKAZ BYL ÚSPĚŠNĚ ODESLÁN!")
    print(">>> TED PROVEĎ POWER-CYCLE LiDARu: odpoj 12V napájení na 5 sekund a zapoj zpět.")
    print(">>> Po zapnutí se LiDAR přepne do sériového režimu.")
    print(">>> Poté ho můžeš připojit k původnímu PC přes USB a používat.")

if __name__ == "__main__":
    main()
