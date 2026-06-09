# 03 — Problém při seriovém čtení

## Co se stalo

SDK binárka:

```text
unilidar_sdk2/unitree_lidar_sdk/bin/read_serial
```

otevřela port správně:

```text
Serial init OK na /dev/ttyACM0 @ 4000000 baud
```

ale po timeoutu skončila bez dat:

```text
HOTOVO: prijato 0 cloud zprav, 0 IMU zprav.
```

## Proč to bylo podezřelé

USB start příkaz fungoval a vracel `ACK_SUCCESS`.
Navíc přímé syrové čtení ukázalo, že z LiDARu data opravdu tečou:

```text
102 = point cloud
104 = IMU
101 = ACK
```

To znamená: problém nebyl v kabelu ani v tom, že by LiDAR neposílal data.
Problém byl v aktuální cestě přes C++ SDK parser / jeho očekávání bufferu, módu nebo framingu.

## Dočasné řešení

Přidali jsme:

```text
../scan_serial_direct.py
```

Ten:

1. otevře `/dev/ttyACM0` na 4 Mbaud,
2. pošle start command,
3. čte syrové Unitree framy,
4. bere `packet_type 102`,
5. převádí range/angles/kalibraci na XYZ,
6. ukládá binární PCD a PNG náhled.

## Co to znamená pro další práci

Pro statické skeny teď používáme `scan_serial_direct.py`.
Později můžeme opravit/diagnostikovat SDK parser, ale není to blokátor pro sběr statických mračen.
