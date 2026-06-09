# 03 — Složení výsledné mapy

Výslednou mapu chceme vidět jako jeden soubor:

```text
results/latest_map.pcd
results/latest_map.png
```

## Složení poslední sekvence

```bash
cd /path/to/unitree-lidar
measurements/continuous_movement/build_map.sh
```

Wrapper vezme:

```text
measurements/continuous_movement/scans/latest_sequence
```

a spustí:

```bash
.venv/bin/python3 slam_map.py <sequence_dir> <out.pcd> 0.03
```

Výstup:

```text
measurements/continuous_movement/results/continuous_map_YYYYMMDD_HHMMSS.pcd
measurements/continuous_movement/results/continuous_map_YYYYMMDD_HHMMSS.png
measurements/continuous_movement/results/latest_map.pcd
measurements/continuous_movement/results/latest_map.png
```

## Otevření mapy

S displejem:

```bash
./view.sh measurements/continuous_movement/results/latest_map.pcd
```

Bez displeje:

```bash
ls -lh measurements/continuous_movement/results/latest_map.png
```

PNG je hlavní rychlá kontrola, jestli se mapa složila do čitelného půdorysu.

## Když `build_map.sh` hlásí chybějící `.venv`

Nainstalovat Python prostředí v kořeni repa:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -c "import open3d, kiss_icp; print('SLAM deps OK')"
```

Pokud instalace nejde, existuje nouzový rychlý náhled bez Open3D/KISS-ICP:

```bash
measurements/continuous_movement/build_map_simple.sh
```

Ten používá `../../continuous_map_simple.py` a skládá framy jednoduchým 2D ICP přes `numpy/scipy`.
Výsledek je jen pracovní kontrola, ne plnohodnotný SLAM.

## Když je mapa špatná

Zkusit:

- kratší sekvenci,
- pomalejší pohyb,
- větší `PACKETS_PER_FRAME` pro hustší framy,
- menší prostor bez symetrie,
- držet LiDAR stabilněji.

Příklady:

```bash
FRAMES=60 DURATION_SECONDS=12 PACKETS_PER_FRAME=30 \
  measurements/continuous_movement/record_sequence.sh
measurements/continuous_movement/build_map.sh
```

Nebo jemnější výsledný voxel:

```bash
measurements/continuous_movement/build_map.sh \
  measurements/continuous_movement/scans/latest_sequence \
  measurements/continuous_movement/results/map_voxel_002.pcd \
  0.02
```
