# Unitree 4D LiDAR L2 — čtení, vizualizace a 3D mapování (SLAM)

Kompletní nástroje pro **Unitree 4D LiDAR L2**: čtení point cloudu + IMU (přes USB/serial
i ethernet), vizualizace (Open3D / matplotlib / Rerun) a 3D mapování prostoru pomocí
**KISS-ICP** (+ volitelný export do ROS2 bagu pro GLIM/FAST-LIO2).

Skripty jsou **přenositelné** — cesty se odvozují z umístění skriptu, síťové rozhraní
i sériový port jsou konfigurovatelné přes proměnné prostředí.

> Detailní technické poznámky (workMode, SLAM zkušenosti, souřadnice) jsou v [README-LIDAR.md](README-LIDAR.md).

---

## Hardware a požadavky

- **Unitree 4D LiDAR L2** (testováno na firmware 2.8.11.1, HW 2.2.1.1).
- **Napájení: vlastní DC adaptér LiDARu** — USB ani serial LiDAR **nenapájí**. Bez DC se nerozběhne.
- Připojení: **USB/serial** (naběhne jako `/dev/ttyACM0`, 4 000 000 baud) **nebo** **ethernet** (RJ45).
- OS: Linux. Potřeba **Python 3.12**, `cmake` + `g++` (C++17), systémové knihovny `libgl1`, `libgomp1`, `libusb-1.0-0`.

---

## Instalace (krok za krokem)

### 1) Systémové závislosti
```bash
sudo apt install python3.12 python3.12-venv cmake g++ libgl1 libgomp1 libusb-1.0-0
```

### 2) Python prostředí
> **Použij `python3.12`**, ne systémový `python3` (často 3.10) — jinak nesednou verze balíčků.
```bash
python3.12 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -c "import open3d, kiss_icp, numpy; print('venv OK')"
```

### 3) C++ SDK (není součástí tohoto repa)
SDK Unitree se zde neverzuje. Naklonuj ho a aplikuj **overlay** s vlastními nástroji:
```bash
git clone https://github.com/unitreerobotics/unilidar_sdk2.git
cp sdk-overlay/examples/*.cpp unilidar_sdk2/unitree_lidar_sdk/examples/
cp sdk-overlay/CMakeLists.txt  unilidar_sdk2/unitree_lidar_sdk/CMakeLists.txt
cmake -S unilidar_sdk2/unitree_lidar_sdk -B unilidar_sdk2/unitree_lidar_sdk/build
cmake --build unilidar_sdk2/unitree_lidar_sdk/build -j
```
Overlay přidá nástroje `read_udp`, `read_serial`, `stream_cloud`, `dump_cloud`,
`lidar_motor`, `record_seq`, `record_glim`, `scan_cloud` (čisté ukončení bez resetu LiDARu).

> ⚠️ **Vždy kompiluj lokálně.** Předkompilované binárky z jiného stroje mohou selhat
> na `GLIBCXX_... not found` (jiná verze GCC/libstdc++). Viz [Řešení problémů](#-řešení-problémů).

### 4) Přístup k sériovému portu
`/dev/ttyACM0` patří skupině `dialout`:
```bash
sudo usermod -aG dialout $USER     # pak se ODHLAS A PŘIHLAS (skupina se načte při loginu)
```
Bez reloginu lze dočasně: `sg dialout -c "<příkaz>"`, případně spouštět přes `sudo`.

---

## Režimy LiDARu (důležité)

LiDAR posílá data **vždy jen jedním kanálem** — ethernet **nebo** serial:

| workMode | režim |
|---|---|
| 0 | Ethernet (tovární default) |
| 8 | Serial / USB |

- Přepnutí ENET→serial se posílá **přes ethernet** (`./switch-to-serial.sh`), zpět **přes serial** (`./switch-to-ethernet.sh`).
- **Po každém přepnutí je nutný power-cycle** (vypnout/zapnout DC napájení LiDARu).

---

## Použití

| Příkaz | Co dělá |
|---|---|
| `./start-usb.sh` | živé čtení přes USB/serial |
| `./live-usb.sh` | živý 3D náhled (Open3D) přes USB |
| `./lidar-quiet.sh` / `./lidar-wake.sh` | standby (zastaví rotaci, ~1 W) / probuzení motoru |
| `bin/.../record_seq N serial seq` | nahraje N snímků pro SLAM |
| `.venv/bin/python3 slam_map.py <složka_pcd> <out.pcd>` | KISS-ICP slepí snímky do 3D mapy |
| `.venv/bin/python3 render_pcd.py <in.pcd> [out.png]` | bezdisplejový render mračna do PNG |
| `./view.sh <in.pcd>` | interaktivní 3D prohlížeč (Open3D, vyžaduje displej) |
| `.venv/bin/python3 measure.py <in.pcd>` | interaktivní měření vzdáleností |
| `.venv/bin/python3 make_rosbag.py <glim_seq>` | export do ROS2 bagu (MCAP) pro GLIM |

### Proměnné prostředí
- `LIDAR_PORT` — sériový port (default `/dev/ttyACM0`).
- `LIDAR_IFACE` — síťové rozhraní pro ethernet režim (default `eno1`).

---

## Vizualizace
- **S displejem:** `./view.sh mapa.pcd` (Open3D okno; myš = otáčení, kolečko = zoom, Q = konec). Živě: `./live-usb.sh`.
- **Bez displeje (headless/SSH):** `render_pcd.py` (matplotlib → PNG, půdorys + 3D). Funguje i bez X serveru.

## 3D mapování / SLAM
```bash
bin/.../record_seq 180 serial seq          # nahraj sekvenci (pomalu naklánět/otáčet)
.venv/bin/python3 slam_map.py seq mapa.pcd # KISS-ICP -> jedna 3D mapa + PNG
./view.sh mapa.pcd
```
KISS-ICP je lidar-only (bez IMU, bez loop closure) → handheld driftuje. Pro čistší dvojník
multi-station statické skeny nebo GLIM/FAST-LIO2 (lidar+IMU). Viz [README-LIDAR.md](README-LIDAR.md).

---

## ⚠️ Bezpečnost sítě
Ethernetové skripty (`start.sh`, `live-ethernet.sh`, `switch-to-serial.sh`) nastavují dočasnou
IP na `LIDAR_IFACE`. Obsahují **pojistku, která odmítne sáhnout na rozhraní nesoucí výchozí
(default) route** stroje — aby nerozbily jeho internet. **Na stroji s jedinou síťovkou
preferuj USB/serial režim.** Pro jiný NIC: `LIDAR_IFACE=<nic> ./start.sh`.

---

## 🔧 Řešení problémů

| Příznak | Příčina / řešení |
|---|---|
| `GLIBCXX_3.4.32 not found` při spuštění SDK binárky | Binárka zkompilovaná na novějším GCC. **Rebuildni SDK lokálně** (krok 3); nepřenášej binárky z jiného stroje. |
| `Permission denied` / nejde otevřít `/dev/ttyACM0` | Uživatel není v `dialout`. `sudo usermod -aG dialout $USER` + **relogin**, nebo dočasně `sg dialout -c "<příkaz>"`. |
| `pip install` selže (`Could not find a version`, `python-apt`…) | Nepoužívej systémový `pip freeze`. Tenhle `requirements.txt` je čistý — instaluj přes **python3.12**, ne systémový python. |
| Open3D okno se neotevře / je prázdné | Chybí `DISPLAY` nebo GL. Zkontroluj `echo $DISPLAY`. Bez displeje použij **`render_pcd.py`** (headless → PNG). |
| Po ethernet skriptu spadne síť/internet stroje | Ethernet režim mění IP na NIC. Na stroji s jednou síťovkou **nepoužívej** — preferuj USB. Pro jiný NIC `LIDAR_IFACE=<nic>`. |
| LiDAR se nehlásí / `/dev/ttyACM0` chybí | LiDAR musí mít **DC napájení** (USB ho nenapájí). Ověř `lsusb` (čip WCH/QinHeng) a `ls /dev/ttyACM*`. |
| LiDAR hučí / točí se a nečteš ho | `./lidar-quiet.sh` (motor stop, standby). Probuzení `./lidar-wake.sh`. |
| Přepnutí ENET↔serial se neprojeví | Po `switch-to-*.sh` je nutný **power-cycle** LiDARu (vypnout/zapnout DC). |
| Živý náhled přes USB nic neukazuje | LiDAR musí být v **serial** režimu a **probuzený** (`./lidar-wake.sh`); spouštěj s displejem: `DISPLAY=:0 sg dialout -c ./live-usb.sh`. |

---

## Licence
- Vlastní kód v kořeni repa (`*.py`, `*.sh`, `sdk-overlay/`) — **MIT** (viz [LICENSE](LICENSE)).
  Soubory v `sdk-overlay/examples/` vycházejí z příkladů Unitree SDK (BSD-3-Clause).
- **unilidar_sdk2** (klonuje se zvlášť) — BSD-3-Clause, © 2024 Unitree Robotics.
- Manuál výrobce (PDF) není součástí repa kvůli autorským právům — stáhni z oficiálních stránek Unitree.
