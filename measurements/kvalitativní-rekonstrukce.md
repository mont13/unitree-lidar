# Kvalitativní rekonstrukce místnosti z LiDAR dat

Cíl tohoto dokumentu je popsat, co musíme dělat, pokud chceme z našeho Unitree L2 získat **přesnější a čistší rekonstrukci místnosti**, ne jen rychlý náhled point cloudu.

Krátká odpověď: zatím to řešíme jen částečně.

Aktuálně máme:

- zachycení point cloudu přes USB serial,
- více statických scanů,
- základní registraci / merge,
- PNG náhledy,
- uložené transformace mezi pozicemi.

Zatím nemáme plnou pipeline:

```text
point cloud -> filtrace -> registrace -> segmentace rovin -> clustering objektů -> mesh / objemová rekonstrukce
```

---

## Stav teď

| Krok | Stav | Poznámka |
|---|---:|---|
| Point cloud capture | hotovo | `scan_serial_direct.py`, USB `/dev/ttyACM0`, packety `102` |
| IMU data | vidíme, ale nepoužíváme | packety `104` chodí, ale nejsou zatím fusionované |
| Registrace statických scanů | částečně hotovo | `merge_scans_simple.py`, `merge_three_known_poses.py` |
| Filtrace šumu | jen základ | voxel downsample, ale ne plná statistická filtrace |
| Segmentace rovin | ne | zatím nedělíme podlaha/strop/stěny |
| Clustering objektů | ne | zatím nehledáme samostatný nábytek/objekty |
| Mesh rekonstrukce | ne | zatím jen point cloud, ne povrchová síť |
| Objemová rekonstrukce | ne | zatím bez TSDF/voxel fusion |

---

## Doporučená pipeline

### 1. Point cloud

Vstup jsou PCD soubory:

```text
../scans/latest_usb_scan.pcd
../scans/latest_usb_scan_pos2.pcd
../scans/latest_usb_scan_pos3.pcd
../scans/latest_room_merged_3poses.pcd
```

Pro přesnější rekonstrukci je důležité:

- LiDAR při statickém scanu nehýbat,
- mít velký překryv mezi pozicemi,
- zapisovat přibližný posun a natočení LiDARu,
- používat více pozic, ne jeden scan,
- držet podobnou výšku nebo ji aspoň zaznamenat,
- vyhnout se sklu, zrcadlům a lesklým plochám.

---

### 2. Filtrace

Účel: odstranit šum, osamocené body, artefakty a přebytečnou hustotu.

Typické kroky:

1. **Range crop**
   - vyhodit body moc blízko LiDARu,
   - vyhodit body za rozumným dosahem místnosti.

2. **Voxel downsample**
   - sjednotit hustotu bodů,
   - typicky `0.02–0.05 m` podle požadované kvality.

3. **Statistical outlier removal**
   - odstranit izolované body,
   - vhodné pro body mimo stěny / strop.

4. **Radius outlier removal**
   - bod musí mít dost sousedů v okolí.

5. **Ořez podle Z / prostoru**
   - pokud chceme jen místnost, můžeme odříznout body mimo fyzický rozsah.

Aktuálně používáme hlavně voxel downsample. Plná filtrace ještě není implementovaná.

---

### 3. Registrace

Účel: dostat všechny scany do jedné souřadné soustavy.

Aktuální stav:

- první merge: `scan_02 -> scan_01`,
- druhý merge: `scan_03 -> mapa`,
- opravený třípoziční merge: všechny raw scany + 3 pozice LiDARu.

Aktuálně používáme pracovní registraci:

```text
2D occupancy grid + odhad Z posunu + voxel merge
```

Pro vyšší kvalitu by měla pipeline být:

1. hrubý odhad podle fyzického posunu,
2. globální registrace — například FPFH/RANSAC,
3. jemná registrace — ICP,
4. ideálně point-to-plane ICP,
5. pose graph optimalizace pro více pozic,
6. kontrola driftu a dvojitých stěn.

Doporučený budoucí nástroj:

```text
Open3D
```

---

### 4. Segmentace rovin

Účel: najít hlavní plochy místnosti:

- podlaha,
- strop,
- stěny,
- velké rovné plochy nábytku.

Typický postup:

1. najít dominantní rovinu přes RANSAC,
2. označit ji jako podlahu / strop / stěnu podle normály,
3. odstranit její body,
4. opakovat pro další roviny,
5. uložit parametry rovin.

Výstup může být například:

```text
planes.json
floor.pcd
ceiling.pcd
wall_01.pcd
wall_02.pcd
objects_without_planes.pcd
```

Pro přesnou rekonstrukci je to důležité, protože roviny místnosti jsou stabilnější než jednotlivé raw body.

---

### 5. Clustering objektů

Po odstranění hlavních rovin zůstanou body objektů:

- židle,
- stůl,
- kabely,
- krabice,
- monitor,
- další nábytek.

Typický postup:

1. odstranit podlahu/strop/stěny,
2. použít Euclidean clustering nebo DBSCAN,
3. pro každý cluster spočítat:
   - bounding box,
   - rozměry,
   - těžiště,
   - počet bodů,
   - orientaci.

Možný výstup:

```text
objects/object_001.pcd
objects/object_001.json
objects/object_002.pcd
objects/object_002.json
```

Tohle zatím vůbec neděláme.

---

### 6. Mesh / povrchová rekonstrukce

Point cloud není mesh. Mesh znamená spojit body do povrchu.

Možnosti:

#### Poisson reconstruction

Výhody:

- umí vytvořit spojitý povrch,
- dobré pro organické / uzavřené tvary.

Nevýhody:

- může „domýšlet“ plochy, které LiDAR neviděl,
- potřebuje dobré normály,
- u místnosti může vytvářet falešné uzávěry.

#### Ball Pivoting / Alpha Shapes

Výhody:

- méně halucinuje než Poisson,
- vhodnější pro lokální povrchy.

Nevýhody:

- citlivé na hustotu bodů,
- díry zůstanou dírami.

#### TSDF / volumetric fusion

Výhody:

- nejlepší cesta pro objemovou rekonstrukci z více pozic,
- přirozeně slučuje více pohledů,
- dá se převést na mesh.

Nevýhody:

- potřebuje kvalitní pozice scanů,
- ideálně časovou trajektorii nebo dobře optimalizovaný pose graph,
- náročnější implementace.

Pro místnost bych jako cílovou cestu bral:

```text
multi-station scany -> dobrá registrace -> TSDF / voxel fusion -> mesh
```

---

## Co znamená „přesnější scan“ prakticky

Přesnost není jen počet bodů. Důležité jsou:

- stěny nejsou dvojité,
- rohy sedí,
- podlaha a strop jsou rovné,
- objekty nemají duchy,
- mapy z více pozic se nepřekrývají špatně,
- mesh nemá falešné plochy.

Metriky, které má smysl sledovat:

```text
počet bodů před/po filtraci
ICP fitness / inlier RMSE
průměrná tloušťka stěny po merge
odchylka bodů od nalezené roviny
počet outlierů
překryv scanů
```

---

## Doporučené fáze práce

### Fáze 1 — lepší point cloud bez meshe

1. Přidat filtrační skript:

```text
filter_cloud.py
```

2. Vstup:

```text
latest_room_merged_3poses.pcd
```

3. Výstup:

```text
reconstruction/filtered_room.pcd
reconstruction/filtered_room.png
reconstruction/filter_report.md
```

Cíl: čistší point cloud bez výrazných outlierů.

---

### Fáze 2 — lepší registrace

1. Nainstalovat / zprovoznit Open3D.
2. Udělat:

```text
voxel downsample -> normals -> FPFH/RANSAC -> point-to-plane ICP
```

3. Pro více scanů přidat pose graph.

Cíl: méně dvojitých stěn a lepší rohy.

---

### Fáze 3 — segmentace místnosti

1. RANSAC roviny.
2. Oddělit:

```text
floor
ceiling
walls
objects
```

3. Vykreslit samostatné náhledy.

Cíl: pochopit strukturu místnosti, nejen bodový oblak.

---

### Fáze 4 — clustering objektů

1. Po odstranění rovin spustit DBSCAN / Euclidean clustering.
2. Vypsat objekty a bounding boxy.
3. Uložit každý cluster samostatně.

Cíl: začít rozlišovat vybavení místnosti.

---

### Fáze 5 — mesh / objemová rekonstrukce

1. Z odfiltrovaného a registrovaného point cloudu spočítat normály.
2. Zkusit Poisson / Ball Pivoting.
3. Pro kvalitnější výsledek zkusit TSDF / volumetric fusion.
4. Exportovat:

```text
room_mesh.ply
room_mesh.obj
room_volume_report.md
```

Cíl: převést mračno bodů na 3D model.

---

## Doporučená struktura výstupů

```text
measurements/
  kvalitativní-rekonstrukce.md

reconstruction/
  filtered_room.pcd
  filtered_room.png
  planes.json
  floor.pcd
  ceiling.pcd
  wall_01.pcd
  objects/
    object_001.pcd
    object_001.json
  mesh/
    room_mesh.ply
    room_mesh.obj
    mesh_report.md
```

---

## Verdikt

Ano, pro přesnější rekonstrukci budeme potřebovat pipeline:

```text
point cloud -> filtrace -> registrace -> segmentace rovin -> clustering objektů -> mesh / objemová rekonstrukce
```

Ale v aktuálním stavu řešíme hlavně první dvě části:

```text
point cloud -> základní registrace
```

Nejbližší rozumný další krok je přidat filtraci a report kvality pro `latest_room_merged_3poses.pcd`.
