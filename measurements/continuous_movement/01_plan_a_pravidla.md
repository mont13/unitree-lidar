# 01 — Plán a pravidla continuous movement pokusu

## Cíl

Chceme získat výslednou složenou mapu z pohybového záznamu bez externího trackingu:

```text
krátké PCD framy -> KISS-ICP -> jedna 3D mapa + PNG náhled
```

Toto je LiDAR-only SLAM. Nepoužívá IMU, kameru ani AprilTagy.

## Proč ne jeden dlouhý PCD scan

Statický `scan_serial_direct.py` ukládá všechny body do jedné souřadné soustavy LiDARu. To funguje, když LiDAR stojí.

Při pohybu ale LiDAR mění pozici pořád, takže potřebujeme sekvenci:

```text
000000.pcd
000001.pcd
000002.pcd
...
```

Každý frame se potom odhadne vůči předchozímu.

## Omezení

- Bez IMU není deskew.
- Rychlé otočení vytvoří dvojité / duchové stěny.
- Chůze v ruce způsobí drift.
- V prázdném prostoru bez rohů a stěn může registrace ztratit orientaci.
- Bez loop closure se chyba nevrátí zpět, jen narůstá.

## První bezpečný experiment

1. LiDAR v serial/USB režimu.
2. Délka záznamu 10–20 s.
3. Pohyb jen pomalá rotace na místě.
4. Nemířit dlouho do prázdna.
5. Sledovat, jestli výsledná mapa nemá dvojité stěny.

## Co hodnotit ve výsledku

- Sedí hlavní stěny na jednom místě, nebo jsou zdvojené?
- Není místnost spirálovitě/banánovitě ohnutá?
- Kolik bodů zůstalo po voxel downsample?
- Je PNG půdorys čitelný?
- Pokud se mapa rozpadá: zkrátit záznam, zpomalit pohyb, zvětšit překryv.
