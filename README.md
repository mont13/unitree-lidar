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
`lidar_motor`, `record_seq`, `record_glim`, `scan_cloud` a zrebuildí i `set_to_serial_mode` / `set_to_udp_mode` pro přepínání `workMode` (čisté ukončení bez resetu LiDARu).

> ⚠️ **Vždy kompiluj lokálně.** Předkompilované binárky z jiného stroje mohou selhat
> na `GLIBCXX_... not found` (jiná verze GCC/libstdc++). Viz [Řešení problémů](#-řešení-problémů).

### 4) Přístup k sériovému portu
`/dev/ttyACM0` patří skupině `dialout`:
```bash
sudo usermod -aG dialout $USER     # pak se ODHLAS A PŘIHLAS (skupina se načte při loginu)
```
Bez reloginu lze dočasně: `sg dialout -c "<příkaz>"`, případně spouštět přes `sudo`.

---

## První připojení / timeout debug

Než začneš buildit SDK nebo řešit stream point cloudu, projdi:

- [`SETUP.md`](SETUP.md) — první checklist po zapojení (Ethernet IP, USB port, permissions, rychlé testy).
- [`ETHERNET/README.md`](ETHERNET/README.md) — low-level UDP start/standby/work-mode debug.
- [`SERIAL/README.md`](SERIAL/README.md) — low-level USB ACK/CRC debug.

Tyhle runbooky vznikly při debugování timeoutů a jsou schválně oddělené od hlavních SDK stream skriptů. Pomůžou rychle poznat, jestli problém je v `workMode`, CRC, obsazeném UDP portu `6201` nebo právech k `/dev/ttyACM0`.

> Pro samotné start/stop debugování **SDK build nepotřebuješ** — stačí Python skripty v `ETHERNET/` a `SERIAL/`.

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
| `./lidar-quiet.sh [auto\|serial\|udp]` / `./lidar-wake.sh [auto\|serial\|udp]` | standby / probuzení; default `auto` zkusí serial a pak ethernet/UDP |
| `./ETHERNET/test_start_stop_10s.sh` | low-level Ethernet start → čekat → standby test pro debug timeoutů/ACK |
| `./SERIAL/test_usb_start_stop_10s.sh` | low-level USB start → čekat → standby test s ACK_SUCCESS |
| `./scan_serial_direct.py` | přímý USB scan do PCD/PNG bez C++ SDK parseru |
| `./record_serial_sequence_direct.py` | přímý USB recorder krátkých PCD framů pro lidar-only SLAM |
| `./merge_scans_simple.py` / `./merge_three_known_poses.py` | jednoduché offline spojování statických scanů bez Open3D |
| `./continuous_map_simple.py` | fallback složení pohybové sekvence bez Open3D/KISS-ICP |
| `bin/.../record_seq N serial seq` | nahraje N snímků pro SLAM |
| `.venv/bin/python3 slam_map.py <složka_pcd> <out.pcd>` | KISS-ICP slepí snímky do 3D mapy |
| `.venv/bin/python3 render_pcd.py <in.pcd> [out.png]` | bezdisplejový render mračna do PNG |
| `./view.sh <in.pcd>` | interaktivní 3D prohlížeč (Open3D, vyžaduje displej) |
| `.venv/bin/python3 measure.py <in.pcd>` | interaktivní měření vzdáleností |
| `.venv/bin/python3 make_rosbag.py <glim_seq>` | export do ROS2 bagu (MCAP) pro GLIM |

### Proměnné prostředí
- `LIDAR_PORT` — sériový port (default `/dev/ttyACM0`). Když není nastavený, USB wrappery zkusí první dostupný `/dev/ttyACM*` nebo `/dev/ttyUSB*`.
- `LIDAR_IFACE` — síťové rozhraní pro ethernet režim (default `eno1`).

---

## Experimentální / fallback nástroje

Další pracovní nástroje převzaté z `jaroslidar/` najdeš přímo v kořeni repa a v [`measurements/`](measurements/):

- `scan_serial_direct.py` — přímé čtení USB/serial point dat bez C++ SDK parseru.
- `record_serial_sequence_direct.py` — přímý záznam krátkých PCD framů pro `slam_map.py`.
- `merge_scans_simple.py`, `merge_three_known_poses.py` — jednoduché spojování statických scanů a kontrola více pozic LiDARu.
- `continuous_map_simple.py` — nouzový 2D ICP fallback, když chybí Open3D/KISS-ICP.
- `switch_to_serial.py` — raw UDP fallback pro ENET→serial přepnutí bez SDK wrapperu.
- `measurements/` — pracovní poznámky, postupy a wrappery pro `continuous_movement/`.

Výstupy těchto nástrojů míří typicky do `scans/` a `measurements/continuous_movement/`.

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
| LiDAR hučí / točí se a nečteš ho | `./lidar-quiet.sh` (motor stop, standby). Probuzení `./lidar-wake.sh`. Pokud je LiDAR v ENET režimu, použij `./lidar-quiet.sh udp` nebo nastav `LIDAR_IFACE=<nic>`. |
| `No ACK/data frame seen after command` při low-level UDP testu | Projdi [`SETUP.md`](SETUP.md) a [`ETHERNET/README.md`](ETHERNET/README.md). U tohoto kusu ACK nemusí přijít zpět, takže rozhoduje fyzický start/stop motoru; zkontroluj IP `192.168.1.2/24` a port `6201`. |
| `ACK_CRC_ERROR` v low-level USB debug skriptu | Správně je `CRC(payload only)`, ne `CRC(header + payload)`. Viz [`SERIAL/README.md`](SERIAL/README.md). |
| Přepnutí ENET↔serial se neprojeví | Po `switch-to-*.sh` je nutný **power-cycle** LiDARu (vypnout/zapnout DC). |
| Živý náhled přes USB nic neukazuje | LiDAR musí být v **serial** režimu a **probuzený** (`./lidar-wake.sh`); spouštěj s displejem: `DISPLAY=:0 sg dialout -c ./live-usb.sh`. |

---

## Licence
- Vlastní kód v kořeni repa a ve složkách `ETHERNET/`, `SERIAL/`, `measurements/`, `sdk-overlay/` — **MIT** (viz [LICENSE](LICENSE)).
  Soubory v `sdk-overlay/examples/` vycházejí z příkladů Unitree SDK (BSD-3-Clause).
- **unilidar_sdk2** (klonuje se zvlášť) — BSD-3-Clause, © 2024 Unitree Robotics.
- Manuál výrobce (PDF) není součástí repa kvůli autorským právům — stáhni z oficiálních stránek Unitree.
