# Merge 03 — sjednocení tří raw scanů a vykreslení 3 pozic LiDARu

Tento merge opravuje problém z `merge_02_pos3.md`: v obrázku byly vidět jen 2 pozice LiDARu, protože druhý merge používal jako referenci už hotovou mapu `scan_01 + scan_02` a nový `scan_03`. Render tedy znal jen:

```text
referenční mapa + nový scan_03
```

Body ze scan_02 v mapě byly, ale jeho pozice už nebyla předaná jako samostatný marker.

## Nový správný postup

Nově se berou všechny tři raw scany samostatně:

```text
scan_01 raw
scan_02 raw + transformace scan_02 -> scan_01
scan_03 raw + transformace scan_03 -> scan_01/mapa
```

Tím zůstávají známé všechny 3 pozice LiDARu.

## Použitý nástroj

```text
../merge_three_known_poses.py
```

## Příkaz

```bash
cd /path/to/unitree-lidar
./merge_three_known_poses.py \
  --out scans/room_merged_3poses_20260604_224959.pcd \
  --voxel 0.03
```

Výchozí vstupy nástroje:

```text
../scans/latest_usb_scan.pcd
../scans/latest_usb_scan_pos2.pcd
../scans/latest_usb_scan_pos3.pcd
../scans/latest_room_merged.transform.txt
../scans/latest_room_merged_pos3.transform.txt
```

## Výstupy

```text
../scans/room_merged_3poses_20260604_224959.pcd
../scans/room_merged_3poses_20260604_224959.png
../scans/room_merged_3poses_20260604_224959.overlay.png
../scans/room_merged_3poses_20260604_224959.report.txt
```

Aktuální symlinky:

```text
../scans/latest_room_merged_3poses.pcd
../scans/latest_room_merged_3poses.png
../scans/latest_room_merged_3poses.overlay.png
../scans/latest_room_merged_3poses.report.txt
```

## Pozice LiDARu v souřadnicích scan_01

```text
scan_01: x= 0.000 m, y= 0.000 m, z= 0.000 m
scan_02: x=-0.419 m, y= 0.048 m, z= 0.717 m
scan_03: x=-1.317 m, y=-0.563 m, z= 0.022 m
```

## Počty bodů

```text
scan_01 raw: 434 392
scan_02 raw: 586 697
scan_03 raw: 597 273
celkem před downsample: 1 618 362
po voxel downsample 0.03 m: 206 756
```

## Poznámka

Toto je teď nejlepší soubor pro vizuální kontrolu tří statických pozic, protože PNG i overlay explicitně ukazují všechny tři LiDAR pozice.
Původní merge soubory zůstaly zachované.
