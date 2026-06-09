# 01 — Co jsme udělali

Datum práce: 2026-06-04.

## 1. Ethernet pokus

Nejdřív jsme zkusili LiDAR přes Ethernet:

- PC interface: `enp14s0`
- PC IP: `192.168.1.2/24`
- LiDAR IP: `192.168.1.62`
- LiDAR ping odpovídal.

Problém: přes Ethernet nechodily point-cloud data do `read_udp` / `scan_cloud`.
Krátký test skončil s:

```text
HOTOVO: prijato 0 cloud zprav, 0 IMU zprav.
```

## 2. Přepnutí na USB/serial

Po resetu / přepnutí LiDARu na USB/serial se ukázalo:

- `/dev/ttyACM0` existuje
- USB start command funguje
- LiDAR vrací `ACK_SUCCESS`
- syrové Unitree framy po USB skutečně tečou

Syrově jsme viděli:

```text
packet_type 102 = point cloud
packet_type 104 = IMU
```

## 3. Obejití SDK parseru

C++ SDK čtečka `read_serial` otevřela port, ale nedostávala validní cloudy přes `getPointCloud()`.
Proto jsme přidali přímý Python parser:

```text
../scan_serial_direct.py
```

Ten čte syrové serial framy, převádí packet `102` na XYZ body podle Unitree kalibračních polí a ukládá rovnou:

```text
PCD + PNG
```

## 4. Hotová měření

První scan:

```text
../scans/usb_scan_20260604_141856.pcd
../scans/usb_scan_20260604_141856.png
```

Druhý scan:

```text
../scans/usb_scan_pos2_20260604_142400.pcd
../scans/usb_scan_pos2_20260604_142400.png
```

Druhá pozice byla uživatelem popsána jako LiDAR posunutý cca o 0.5 m dál a výš v prostoru.
