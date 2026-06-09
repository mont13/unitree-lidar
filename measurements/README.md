# Measurements — Unitree L2 skeny místnosti

Tahle složka popisuje aktuální měření a postup práce se skeny z LiDARu.

## Soubory

- [`01_co_jsme_udelali.md`](01_co_jsme_udelali.md) — časová osa a co se povedlo.
- [`02_co_pouzivame.md`](02_co_pouzivame.md) — aktuální pracovní nástroje a příkazy.
- [`03_problem_serial_cteni.md`](03_problem_serial_cteni.md) — proč SDK serial čtečka nefungovala a jak jsme to obešli.
- [`04_spojovani_vice_skenu.md`](04_spojovani_vice_skenu.md) — plán spojování více skenů do jedné mapy.
- [`scan_01.md`](scan_01.md) — první statické měření.
- [`scan_02.md`](scan_02.md) — druhé statické měření.
- [`scan_03.md`](scan_03.md) — třetí statické měření.
- [`merge_01.md`](merge_01.md) — první spojení scan_01 + scan_02 do jedné mapy.
- [`merge_02_pos3.md`](merge_02_pos3.md) — přidání třetího scanu do samostatné nové mapy.
- [`merge_03_3poses.md`](merge_03_3poses.md) — nové sjednocení tří raw scanů se 3 pozicemi LiDARu.
- [`05_rozsireni_handheld_mapping.md`](05_rozsireni_handheld_mapping.md) — rozšiřování mapy, LiDAR-only SLAM a handheld mapping.
- [`kvalitativní-rekonstrukce.md`](kvalitativní-rekonstrukce.md) — pipeline pro přesnější point cloud, filtraci, segmentaci, clustering a mesh/objemovou rekonstrukci.
- [`continuous_movement/`](continuous_movement/) — nová pracovní složka pro pohybový LiDAR-only SLAM pokus, sekvence framů, live preview a výslednou složenou mapu.
- [`real-time/`](real-time/) — poznámky k real-time detekci překážek pro dron z aktuálního point cloudu.

## Aktuální hlavní vstupy

```text
../scans/latest_usb_scan.pcd
../scans/latest_usb_scan_pos2.pcd
../scans/latest_usb_scan_pos3.pcd
```

## Aktuální spojení

První spojení dvou statických skenů je uložené zde:

```text
../scans/latest_room_merged.pcd
../scans/latest_room_merged.png
../scans/latest_room_merged.overlay.png
../scans/latest_room_merged.transform.txt
```


## Aktuální spojení se třetím scanem

Nová mapa se třetí pozicí je uložená samostatně, aby původní merge zůstal nedotčený:

```text
../scans/latest_room_merged_pos3.pcd
../scans/latest_room_merged_pos3.png
../scans/latest_room_merged_pos3.overlay.png
../scans/latest_room_merged_pos3.transform.txt
```


## Aktuální nejlepší 3-position mapa

Nově sjednocené raw scany se všemi 3 pozicemi LiDARu:

```text
../scans/latest_room_merged_3poses.pcd
../scans/latest_room_merged_3poses.png
../scans/latest_room_merged_3poses.overlay.png
../scans/latest_room_merged_3poses.report.txt
```

## Handheld / další rozšiřování

Samostatný plán pro rozšiřování mapy a handheld pokusy je zde:

```text
05_rozsireni_handheld_mapping.md
```

Nový konkrétní pracovní prostor pro continuous movement pokusy:

```text
continuous_movement/
continuous_movement/scans/
continuous_movement/results/
```
