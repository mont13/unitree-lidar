# Scan 03 — třetí statická pozice

Třetí scan byl zachycen na nové pozici LiDARu. Předchozí scany ani starý merge nebyly přepsané.

## Vstupy / stav

- LiDAR byl spuštěný uživatelem.
- USB serial `/dev/ttyACM0` byl dostupný až mimo sandbox; port měl ACL pro uživatele `hans`.
- Scan byl čten přes přímý parser `scan_serial_direct.py`.

## Příkaz

```bash
cd /path/to/unitree-lidar
./scan_serial_direct.py \
  --port /dev/ttyACM0 \
  --packets 2000 \
  --seconds 25 \
  --out scans/usb_scan_pos3_20260604_224333.pcd
```

## Výstupy

```text
../scans/usb_scan_pos3_20260604_224333.pcd
../scans/usb_scan_pos3_20260604_224333.png
../scans/usb_scan_pos3_20260604_224333.meta.txt
```

Aktuální symlinky pro třetí pozici:

```text
../scans/latest_usb_scan_pos3.pcd
../scans/latest_usb_scan_pos3.png
../scans/latest_usb_scan_pos3.meta.txt
```

## Naměřené hodnoty

```text
point packety: 2023
IMU packety: 2642
ACK: 3
body: 597 273
rozměr X x Y x Z: 6.05 x 6.05 x 3.18 m
PCD velikost: cca 9.6 MB
PNG velikost: cca 1.1 MB
```

## Poznámka

Třetí scan vypadá použitelně a má dobrý překryv s předchozí mapou.
