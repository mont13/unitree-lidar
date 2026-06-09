# Continuous movement — LiDAR-only SLAM pokus

Cíl této složky: samostatně vést pokusy, kde se LiDAR **pohybuje v ruce** a mapu skládáme bez externího sledování polohy. Tedy varianta:

```text
point cloud framy -> LiDAR-only registrace / KISS-ICP -> složená mapa
```

Očekávání: půjde to zkusit, ale kvalita bude horší než u statických multi-position scanů. Bude drift, rychlá rotace může sken rozmazat a bez IMU/deskew se pohyb během jedné otočky projeví deformací.

## Stav při založení

- Statické scany a nejlepší 3-position mapa jsou popsané v `../merge_03_3poses.md`.
- Existuje KISS-ICP skládání přes `../../slam_map.py`.
- Existuje live 3D náhled přes `../../live-usb.sh` / `../../live_view.py`.
- Protože dříve zlobila serial cesta přes C++ SDK parser, přidali jsme i přímý recorder sekvence:

```text
../../record_serial_sequence_direct.py
```

Ten používá stejný funkční raw serial parser jako `../../scan_serial_direct.py`, ale ukládá krátké PCD framy místo jednoho dlouhého statického PCD.

## Struktura

```text
continuous_movement/
  README.md
  01_plan_a_pravidla.md
  02_nahravani_sekvence.md
  03_slozeni_mapy.md
  04_live_preview.md
  05_mereni_20260604_230117.md
  record_sequence.sh
  build_map.sh
  live_preview.sh
  check_components.sh
  scans/      # sem se ukládají sekvence frame_*.pcd
  results/    # sem se ukládá výsledná složená mapa
```

## Rychlý postup

Z kořene projektu:

```bash
cd /path/to/unitree-lidar
```

1. Kontrola komponent:

```bash
measurements/continuous_movement/check_components.sh
```

2. Volitelně živý náhled toho, co LiDAR vidí:

```bash
measurements/continuous_movement/live_preview.sh usb
```

3. Nahrát krátkou pohybovou sekvenci:

```bash
measurements/continuous_movement/record_sequence.sh
```

4. Složit sekvenci do jedné mapy:

```bash
measurements/continuous_movement/build_map.sh
```

5. Otevřít výslednou mapu:

```bash
./view.sh measurements/continuous_movement/results/latest_map.pcd
```

Bez displeje aspoň zkontrolovat PNG:

```text
measurements/continuous_movement/results/latest_map.png
```

## Doporučený první pohyb

Pro první pokus nedělat chůzi po místnosti. Jen:

- držet LiDAR pevně,
- pomalu se otáčet na místě,
- minimum prudkého zápěstí,
- délka cca 10–20 s,
- velký překryv — stále vidět stejné stěny/rohy.

Až potom zkoušet pomalou chůzi.
