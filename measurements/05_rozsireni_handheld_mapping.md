# 05 — Rozšiřování mapy a handheld mapping

Tento dokument odděluje dvě cesty, jak mapu místnosti rozšiřovat dál:

1. **multi-station static scan** — LiDAR stojí, uděláme scan, posuneme ho, znovu scan, pak spojíme,
2. **handheld mapping** — LiDAR držíme v ruce a pohyb/rotaci rekonstruujeme ze sekvence dat.

Aktuálně máme ověřené, že statické spojení funguje relativně dobře: viz [`merge_01.md`](merge_01.md).

---

## Krátké doporučení

Pro nejhezčí výsledek teď pokračovat přes **multi-station static scan**:

1. Položit LiDAR.
2. Udělat scan.
3. Posunout o cca `0.5–1.5 m`.
4. Nechat velký překryv s předchozím skenem — ideálně `40–60 %` stejného prostoru.
5. Udělat další scan.
6. Spojit přes registraci / ICP.

Handheld chůzi brát jako další fázi, až budeme mít stabilně zvládnuté spojování statických pozic.

---

## 1. Bez dalšího sledování polohy — jde to, ale kvalita bude horší

LiDAR-only SLAM odhaduje pohyb jen z toho, jak se mění point cloud v čase.
Typicky sem patří například **KISS-ICP**.

### Výhody

- nepotřebuje externí čidlo,
- dá se zkusit i jen z LiDAR dat,
- může fungovat v místnosti, kde je dost stěn, rohů a objektů,
- je to dobrý první experiment pro handheld sekvenci.

### Nevýhody

- při chůzi v ruce bude drift,
- rychlá rotace rozmaže sken,
- když je málo stěn/rohů, algoritmus může ztratit orientaci,
- bez IMU / deskew se pohyb během jedné otočky projeví jako deformace,
- bez loop-closure se chyba postupně hromadí.

### Co by bylo potřeba pro pokus

Současný `scan_serial_direct.py` dělá statický scan tak, že všechny point packety uloží do jednoho PCD ve stejných souřadnicích LiDARu.
To je dobré, když LiDAR stojí.

Pro handheld LiDAR-only rekonstrukci potřebujeme místo toho ukládat **sekvenci krátkých framů**:

```text
frame_000001.pcd + timestamp
frame_000002.pcd + timestamp
frame_000003.pcd + timestamp
...
```

Pak se řeší transformace:

```text
frame_002 -> frame_001
frame_003 -> frame_002
frame_004 -> frame_003
...
```

A postupně se skládá trajektorie LiDARu a mapa.

### Očekávání kvality

Jestli LiDAR jen držíme v ruce a pomalu se otáčíme na jednom místě, může být výsledek použitelný jako širší scan z jedné pozice.
Jestli s ním chodíme po místnosti, kvalita bez IMU bude spíš experimentální:

- část místnosti se může hezky složit,
- vzdálenější část může driftovat,
- při rychlém otočení vzniknou duchy / dvojité stěny,
- výsledek nemusí být metrický přesný.

---

## 2. Kvalitní handheld mapping — potřebuje pose / IMU fusion

Pro opravdu dobrý výsledek musí systém znát v každém okamžiku:

```text
kde LiDAR je + jak je natočený
```

To se řeší přes:

- IMU uvnitř Unitree LiDARu,
- LiDAR-inertial SLAM: **GLIM / FAST-LIO2 / LIO-SAM**,
- případně kamera,
- AprilTags,
- wheel odometry,
- externí tracker.

### Dobrá zpráva pro náš hardware

Unitree LiDAR už posílá IMU packety.
Při USB čtení jsme viděli:

```text
packet_type 102 = point cloud
packet_type 104 = IMU
packet_type 101 = ACK
```

Takže nutně nemusíme přidávat další fyzické čidlo.
Musíme ale správně propojit:

```text
point cloud + timestamp + IMU + kalibrace + SLAM software
```

### Proč IMU pomůže

IMU dá odhad rotace a zrychlení mezi LiDAR framy.
To pomůže hlavně při:

- rychlejší rotaci v ruce,
- chůzi,
- deskew — oprava toho, že body v jednom scanu vznikají v různých časech,
- odhadu orientace i ve chvíli, kdy point cloud nemá dost geometrie.

### Co bude potřeba doplnit

1. Parser IMU packetů `104`.
2. Timestampy pro point cloud packety `102` i IMU `104`.
3. Export do formátu pro SLAM:
   - MCAP / ROS bag,
   - nebo sekvence bin / PCD + CSV.
4. Kalibraci orientace IMU vůči LiDARu.
5. Vybraný SLAM backend:
   - GLIM,
   - FAST-LIO2,
   - LIO-SAM,
   - nebo nejdřív jednodušší KISS-ICP bez IMU.

---

## Dá se handheld výsledek spojit podobně jako náš merge?

Ano, ale jen částečně.

Náš aktuální merge funguje takto:

```text
scan_02 jako celek -> scan_01 jako celek
```

To je vhodné pro statické pozice.

Handheld mapování je složitější, protože LiDAR během záznamu mění polohu pořád:

```text
frame_000002 -> frame_000001
frame_000003 -> frame_000002
frame_000004 -> frame_000003
...
```

Takže nejde jen vzít jeden dlouhý handheld PCD a jednou ho zarovnat.
Musíme záznam rozsekat na malé časové framy a každému framu odhadnout vlastní pozici.

### Nejjednodušší experiment

První pokus bez IMU:

1. držet LiDAR co nejstabilněji,
2. pomalu se otáčet,
3. nechodit rychle,
4. nedělat prudké zápěstí / rychlý yaw,
5. zaznamenat krátkou sekvenci,
6. zkusit LiDAR-only registraci framů.

Pokud bude pohyb pomalý a v místnosti je dost geometrie, měla by jít vytvořit mapa podobným principem jako merge — jen mnohokrát za sebou.

### Praktická hranice

- **Pomalé otáčení na místě:** pravděpodobně půjde zkusit brzy.
- **Pomalá chůze s velkým překryvem:** možné, ale bude drift.
- **Rychlá chůze / rychlé rotace:** bez IMU fusion bude špatné.
- **Kvalitní handheld mapa celé místnosti:** cílit na IMU fusion / GLIM / FAST-LIO2.

---

## Doporučený plán další práce

Konkrétní pracovní prostor pro fázi B je nově:

```text
continuous_movement/
```

Tam povedeme návod, sekvence scanů i výsledné složené mapy z pohybového záznamu.

### Fáze A — pokračovat ve statických scanech

1. Udělat scan_03 z další statické pozice.
2. Zapsat fyzický posun a přibližnou rotaci.
3. Spojit `scan_03 -> latest_room_merged`.
4. Ověřit, jestli se nevytváří dvojité stěny.

### Fáze B — první handheld LiDAR-only experiment

1. Přidat recorder, který ukládá krátké framy místo jednoho velkého PCD.
2. Udělat krátký záznam `10–20 s`.
3. Pohyb: pomalá rotace na místě, minimum chůze.
4. Zkusit registraci framů přes LiDAR-only ICP.
5. Porovnat s kvalitou statického merge.

### Fáze C — kvalitní handheld mapping s IMU

1. Rozparsovat IMU packety `104`.
2. Spárovat IMU a point cloud časově.
3. Exportovat data pro GLIM / FAST-LIO2 / LIO-SAM.
4. Zapnout deskew a LiDAR-inertial odometrii.
5. Udělat delší handheld průchod místností.

---

## Verdikt

Ano, handheld rekonstrukci dokážeme zkusit.

Nejdřív ale bude rozdíl proti statickému merge:

- statický merge = jednodušší, stabilnější, už ověřené,
- handheld LiDAR-only = experimentální, riziko driftu,
- handheld + IMU fusion = správná cesta pro kvalitní mapu.
