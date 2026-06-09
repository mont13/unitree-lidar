# Merge 01 — spojení scan_01 + scan_02

První pracovní spojení dvou statických měření je hotové.

## Vstupy

```text
../scans/latest_usb_scan.pcd       -> scan_01
../scans/latest_usb_scan_pos2.pcd  -> scan_02
```

## Použitý nástroj

```text
../merge_scans_simple.py
```

Nástroj nevyžaduje Open3D. Používá jen `numpy` + `matplotlib`:

1. načte binární PCD `x y z intensity`,
2. v půdorysu XY udělá occupancy-grid korelaci,
3. vybere transformaci `scan_02 -> scan_01`,
4. dorovná výšku přes horní kvantil Z — tady strop,
5. sloučí body,
6. udělá voxel downsample,
7. uloží PCD, PNG, kontrolní overlay a transformační report.

## Spuštěný příkaz

```bash
cd /path/to/unitree-lidar
./merge_scans_simple.py scans/latest_usb_scan.pcd scans/latest_usb_scan_pos2.pcd \
  --out scans/room_merged_20260604_144126.pcd \
  --max-sensor-move 1.2 \
  --z-align upper \
  --voxel 0.03
```

`--max-sensor-move 1.2` bylo důležité, protože místnost má symetrii: absolutně nejlepší hrubý kandidát by položil druhý LiDAR asi 3 m od prvního, což neodpovídá tomu, že scan_02 byl posunut přibližně o 0,5 m.

## Výstupy

```text
../scans/room_merged_20260604_144126.pcd
../scans/room_merged_20260604_144126.png
../scans/room_merged_20260604_144126.overlay.png
../scans/room_merged_20260604_144126.transform.txt
```

Aktuální symlinky:

```text
../scans/latest_room_merged.pcd
../scans/latest_room_merged.png
../scans/latest_room_merged.overlay.png
../scans/latest_room_merged.transform.txt
```

## Výsledek registrace

```text
yaw Z scan_02 -> scan_01: 150.50 deg
pozice LiDARu scan_02 ve scan_01: x=-0.419 m, y=0.048 m, z=0.717 m
XY vzdálenost senzorů: 0.421 m
Z posun: 0.717 m podle horního kvantilu Z q=0.95
score: 0.720180
body před downsample: 1 021 089
body po downsample: 134 331 při voxel 0.03 m
```

## Hodnocení kvality

Je to použitelný první merge. Půdorys dává smysl a druhá pozice LiDARu vyšla blízko očekávanému fyzickému posunu.

Není to ale finální přesná mapa:

- zarovnání je zatím 2D + jednoduchý odhad výšky,
- rotace a posun se hledají podle půdorysu, ne plným 3D ICP,
- u symetrické místnosti existují falešné kandidáty,
- při dalším skenu je dobré zapisovat odhad fyzického posunu a směr otočení LiDARu.

## Další doporučený krok

Pro další scan:

1. nechat překryv aspoň 40–60 % se stávající mapou,
2. posunout LiDAR o cca 0,5–1,0 m, ne přes celou místnost,
3. poznamenat si posun a natočení,
4. spustit stejný scan,
5. merge pouštět s odpovídajícím `--max-sensor-move`.
