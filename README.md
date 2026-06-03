# Unitree 4D LiDAR L2 — čtení, vizualizace a 3D mapování (SLAM)

Nástroje pro čtení point cloudu + IMU z **Unitree 4D LiDAR L2**, jejich vizualizaci
(Open3D / matplotlib / Rerun) a 3D mapování prostoru pomocí **KISS-ICP**
(volitelně export do ROS2 bagu pro GLIM/FAST-LIO2).

Skripty jsou **přenositelné** — cesty se odvozují z umístění skriptu, síťové
rozhraní i sériový port jdou přepsat přes proměnné prostředí.

## Požadavky
- Python **3.12**, `cmake` + `g++` (C++17), `libgl1`, `libgomp1`, `libusb`.
- Unitree 4D LiDAR L2 napájený z DC adaptéru (USB/serial ho nenapájí).
- Pro sériové čtení: uživatel ve skupině `dialout` (`sudo usermod -aG dialout $USER`, pak relogin).

## Instalace

### 1) Python prostředí
```bash
python3.12 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -c "import open3d, kiss_icp, numpy; print('venv OK')"
```

### 2) C++ SDK (není součástí tohoto repa)
SDK Unitree se neverzuje zde — naklonuj ho a aplikuj overlay s vlastními nástroji:
```bash
git clone https://github.com/unitreerobotics/unilidar_sdk2.git
cp sdk-overlay/examples/*.cpp unilidar_sdk2/unitree_lidar_sdk/examples/
cp sdk-overlay/CMakeLists.txt  unilidar_sdk2/unitree_lidar_sdk/CMakeLists.txt
cmake -S unilidar_sdk2/unitree_lidar_sdk -B unilidar_sdk2/unitree_lidar_sdk/build
cmake --build unilidar_sdk2/unitree_lidar_sdk/build -j
```
Overlay přidává nástroje `read_udp`, `read_serial`, `stream_cloud`, `dump_cloud`,
`lidar_motor`, `record_seq`, `record_glim`, `scan_cloud` (čisté ukončení bez resetu LiDARu).

## Použití

| Příkaz | Co dělá |
|---|---|
| `./start-usb.sh` | živé čtení přes USB/serial (`/dev/ttyACM0`) |
| `./live-usb.sh` | živý 3D náhled (Open3D) přes USB |
| `./lidar-quiet.sh` / `./lidar-wake.sh` | standby (zastaví rotaci) / probuzení motoru |
| `.venv/bin/python3 slam_map.py <složka_pcd> <out.pcd>` | KISS-ICP slepí snímky do 3D mapy |
| `.venv/bin/python3 render_pcd.py <in.pcd> [out.png]` | bezdisplejový render mračna do PNG |
| `./view.sh <in.pcd>` | interaktivní 3D prohlížeč (Open3D) |
| `bin/.../record_seq N serial seq` | nahraje N snímků pro SLAM |

Ethernet režim (`start.sh`, `live-ethernet.sh`, `switch-to-serial.sh`) je k dispozici,
ale na stroji s jedinou síťovkou ho nepoužívej — viz Bezpečnost.

### Proměnné prostředí
- `LIDAR_PORT` — sériový port (default `/dev/ttyACM0`).
- `LIDAR_IFACE` — síťové rozhraní pro ethernet režim (default `eno1`).

## Bezpečnost (síť)
Ethernetové skripty nastavují dočasnou IP na `LIDAR_IFACE`. Obsahují pojistku,
která **odmítne sáhnout na rozhraní nesoucí výchozí (default) route** stroje,
aby nerozbily jeho internet. Na stroji s jednou síťovkou preferuj **USB/serial režim**.

## Licence
- Vlastní kód v kořeni repa (`*.py`, `*.sh`, `sdk-overlay/`) — **MIT** (viz [LICENSE](LICENSE)).
  Soubory v `sdk-overlay/examples/` vycházejí z příkladů Unitree SDK (BSD-3-Clause).
- **unilidar_sdk2** (klonuje se zvlášť) — BSD-3-Clause, © 2024 Unitree Robotics.
- Manuál výrobce (PDF) není součástí repa kvůli autorským právům — stáhni z oficiálních stránek Unitree.
