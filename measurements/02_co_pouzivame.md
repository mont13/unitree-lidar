# 02 — Co teď používáme

## Aktuální transport

Používáme **USB/serial**:

```text
/dev/ttyACM0
baudrate 4 000 000
```

Ethernet odpovídal na ping, ale point-cloud stream se v té chvíli nedařilo číst.

## Start / standby motoru přes USB

Start:

```bash
cd SERIAL
python3 ./unitree_lidar_usb_standby.py --port /dev/ttyACM0 --start --repeat 5 --listen 2
```

Standby / ztišení:

```bash
cd SERIAL
python3 ./unitree_lidar_usb_standby.py --port /dev/ttyACM0 --standby --repeat 5 --listen 2
```

Úspěch poznáme podle:

```text
ACK_SUCCESS
```

## Scan přes přímý parser

Aktuální pracovní scan příkaz:

```bash
cd /path/to/unitree-lidar
./scan_serial_direct.py --port /dev/ttyACM0 --packets 2000 --seconds 25 --out scans/<nazev>.pcd
```

Skript ukládá:

```text
scans/<nazev>.pcd
scans/<nazev>.png
```

## Aktuální vstupy pro spojení

```text
scans/latest_usb_scan.pcd
scans/latest_usb_scan_pos2.pcd
```

Symlinky míří na poslední dobrá měření.
