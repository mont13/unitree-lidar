# Real-time — detekce překážek pro dron

Tahle složka odděluje úvahy a budoucí návrh pro **rychlou real-time detekci překážek** z Unitree L2 LiDARu na dronu.

Navazuje na continuous movement pokus: rekonstrukce mapy z pohybu funguje experimentálně, ale pro dron není hlavní cíl skládat mapu. Hlavní cíl je rychle poznat, že dron letí do překážky.

## Konverzace / závěr

### Otázka

> Poslední problém je: když to namontujeme na dron, bude schopný v real time detekovat to, že letí do větve? A dost pravděpodobně to na dronu budeme muset mít napsané v něčem jiném než Pythonu kvůli maximální rychlosti odezvy.

### Odpověď

Ano — ale **ne jako rekonstrukci mapy**. Pro dron bychom nedělali SLAM jako teď, ale rychlou detekci překážek z aktuálního point cloudu.

Princip:

```text
aktuální LiDAR frame
-> vybrat prostor před dronem
-> najít body v kolizním koridoru
-> spočítat vzdálenost / time-to-collision
-> poslat STOP / zpomal / vyhni se
```

Na větev: **částečně ano**, ale není to 100% jisté.

LiDAR dobře uvidí:

- kmen,
- silnější větev,
- hustší listí,
- keř,
- stěnu / strom / sloup.

Horší bude:

- tenká suchá větvička,
- drát,
- průhledné / šikmé / málo odrazivé objekty,
- rychlý let moc blízko překážky.

Takže prakticky: pro dron bych to bral jako **obstacle warning / avoidance**, ne jako absolutní záruku, že nikdy netrefí větev.

A ano — finální verze by měla být spíš **C++ / Rust**, ne Python. Python je dobrý na prototyp a vizualizaci, ale bezpečnostní smyčka pro dron má běžet co nejrychleji a deterministicky.

Doporučená architektura:

```text
Unitree LiDAR SDK C++
-> realtime point cloud filtr
-> forward collision cone / voxel grid
-> nearest obstacle + confidence
-> MAVLink / PX4 / ArduPilot obstacle message
```

Nejdřív bychom udělali jednoduchý C++ program:

- čte LiDAR přes serial/ethernet,
- bere jen body před dronem,
- ignoruje zem pod určitým úhlem,
- pokud je překážka např. `< 2 m`, vypíše/pošle `OBSTACLE`,
- měří latenci.

Tohle je mnohem jednodušší a vhodnější než skládat mapu. Mapa je na orientaci; pro větev před dronem potřebujeme hlavně **rychlou lokální reakci**.

## Pracovní verdikt

- **SLAM/mapování:** dobré pro offline rekonstrukci prostoru, ale není ideální pro okamžitou bezpečnostní reakci dronu.
- **Real-time avoidance:** má běžet nad aktuálním framem / krátkým oknem framů.
- **Jazyk:** prototyp může být Python, ostrá dron verze C++ nebo Rust.
- **Bezpečnost:** LiDAR může varovat před větvemi, ale tenké větvičky/dráty nejsou garantované.

## Další krok

Připravit minimální C++ test:

```text
stream point cloud
-> crop přední koridor
-> počítat nejbližší překážku
-> tisknout distance / obstacle / latency
```

A pak napojit výstup na autopilota přes MAVLink / PX4 / ArduPilot.
