# Merge 02 — přidání scan_03 do existující mapy scan_01 + scan_02

Tento merge přidává třetí statickou pozici do už existující mapy ze scan_01 + scan_02.

Důležité: původní merge zůstal nedotčený:

```text
../scans/latest_room_merged.pcd
../scans/latest_room_merged.png
../scans/latest_room_merged.overlay.png
../scans/latest_room_merged.transform.txt
```

Nový výsledek má samostatné názvy `*_pos3*`.

## Vstupy

```text
../scans/latest_room_merged.pcd      -> reference: scan_01 + scan_02
../scans/latest_usb_scan_pos3.pcd    -> nový scan_03
```

## Příkaz

```bash
cd /path/to/unitree-lidar
./merge_scans_simple.py scans/latest_room_merged.pcd scans/latest_usb_scan_pos3.pcd \
  --out scans/room_merged_pos3_20260604_224447.pcd \
  --z-align upper \
  --voxel 0.03 \
  --no-latest
```

`--no-latest` zajistilo, že původní `latest_room_merged.*` symlinky zůstaly na starém merge.

## Výstupy

```text
../scans/room_merged_pos3_20260604_224447.pcd
../scans/room_merged_pos3_20260604_224447.png
../scans/room_merged_pos3_20260604_224447.overlay.png
../scans/room_merged_pos3_20260604_224447.transform.txt
```

Nové symlinky pro mapu se třetím scanem:

```text
../scans/latest_room_merged_pos3.pcd
../scans/latest_room_merged_pos3.png
../scans/latest_room_merged_pos3.overlay.png
../scans/latest_room_merged_pos3.transform.txt
```

## Výsledek registrace

```text
yaw Z scan_03 -> mapa scan_01+scan_02: -160.00 deg
pozice LiDARu scan_03 v mapě: x=-1.317 m, y=-0.563 m, z=0.022 m
XY vzdálenost od počátku scan_01: 1.433 m
Z posun: 0.022 m podle horního kvantilu Z q=0.95
score: 0.932760
body před downsample: 731 604
body po downsample: 206 754 při voxel 0.03 m
```

## Hodnocení kvality

Výsledek vypadá kvalitněji než první merge samotný, protože třetí pozice doplnila další pohledy na stejnou místnost.
Overlay ukazuje dobré překrytí stěn a objektů.

Stále platí, že jde o pracovní registraci:

- reference je už downsamplovaná mapa scan_01 + scan_02,
- registrace je zatím hlavně 2D půdorys + výškový odhad,
- přesnější cesta bude později Open3D / ICP nebo LiDAR-inertial SLAM.
