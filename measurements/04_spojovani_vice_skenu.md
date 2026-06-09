# 04 — Jak spojit více skenů dohromady

Každý statický scan má vlastní souřadnice LiDARu:

```text
LiDAR = (0, 0, 0)
```

Když LiDAR posuneme nebo pootočíme, místnost se ve výsledném obrázku posune/otočí.
Spojení tedy znamená najít transformaci:

```text
scan_N -> scan_1
```

Transformace je:

```text
rotace R + posun t
```

## Doporučený praktický postup

1. Udělat více statických skenů.
2. Mezi pozicemi zachovat výrazný překryv — ideálně 40–60 % stejného prostoru.
3. Zapsat přibližný fyzický posun LiDARu.
4. Hrubě zarovnat skeny podle odhadu.
5. Doladit přes ICP / registraci point cloudů.
6. Sloučit a downsamplovat výsledek.

## Proč je překryv důležitý

ICP funguje dobře, pokud vidí stejné stěny, rohy nebo nábytek v obou skenech.
Když překryv chybí, algoritmus může spojit špatné stěny nebo mapu otočit.

## Hotový první merge

První merge je uložený jako:

```text
../scans/latest_room_merged.pcd
../scans/latest_room_merged.png
../scans/latest_room_merged.overlay.png
../scans/latest_room_merged.transform.txt
```

Detaily jsou v [`merge_01.md`](merge_01.md).

## Hotový druhý merge — přidán scan_03

Nová mapa se třetí pozicí je samostatná a nepřepisuje původní merge:

```text
../scans/latest_room_merged_pos3.pcd
../scans/latest_room_merged_pos3.png
../scans/latest_room_merged_pos3.overlay.png
../scans/latest_room_merged_pos3.transform.txt
```

Detaily jsou v [`merge_02_pos3.md`](merge_02_pos3.md).

## Aktuální první pokus

Protože tady zatím nemáme Open3D v `.venv`, spojení se udělá jednoduchým numpy nástrojem:

- načíst binární PCD,
- vybrat hlavně horizontální / plošné body,
- udělat hrubé 2D zarovnání přes occupancy grid,
- doladit 2D ICP v půdorysu,
- přenést transformaci na celé 3D mračno,
- sloučit do jednoho PCD + PNG.

Tento první merge nebude absolutní geodetická pravda. Je to pracovní odhad pro vizuální sjednocení místnosti.

## Kvalitnější budoucí cesta

Pro lepší výsledky:

- nainstalovat Open3D,
- použít voxel-downsample + FPFH/RANSAC + ICP,
- případně použít GLIM/FAST-LIO2 s IMU daty,
- pro handheld chůzi použít LiDAR-inertial SLAM.
