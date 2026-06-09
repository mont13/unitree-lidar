# Unitree 4D LiDAR L2 — zprovoznění (technické poznámky)

> **Hlavní návod (instalace, použití, řešení problémů) je v [README.md](README.md).**
> Tento soubor je doplňková technická reference. K přenositelnosti: skripty berou
> síťové rozhraní z `LIDAR_IFACE` (default `eno1`) a port z `LIDAR_PORT`
> (default `/dev/ttyACM0`); C++ SDK se kompiluje lokálně (viz README, krok 3);
> sériový port vyžaduje členství ve skupině `dialout`.

Stav: **funkční přes ethernet** (ověřeno — point cloud + IMU teče). USB/serial připraveno (vyžaduje jednorázové přepnutí + restart LiDARu).

První checklist po připojení a low-level debug timeoutů/ACK je v [`SETUP.md`](SETUP.md), detailní runbooky pak v [`ETHERNET/README.md`](ETHERNET/README.md) a [`SERIAL/README.md`](SERIAL/README.md).

## Hardware / připojení
- Zařízení: **Unitree 4D LiDAR L2** (firmware 2.8.11.1, hardware 2.2.1.1)
- Napájení: z přibaleného DC adaptéru (USB ani serial LiDAR **nenapájí**)
- **Ethernet**: RJ45 do `eno1`. LiDAR má pevnou IP `192.168.1.62`, PC musí mít `192.168.1.2/24`. (DHCP LiDAR neumí.)
- **USB/serial**: adaptér → USB-C → PC, naběhne jako `/dev/ttyACM0`, 4 000 000 baud.

## Klíčový princip (důležité!)
LiDAR posílá data **vždy jen jedním kanálem** — ENET **nebo** serial, ne oběma.
- Z výroby je v **ENET** režimu (`workMode 0`).
- Přepnutí na serial (`workMode 8`) se musí poslat **přes ethernet**, pak **power-cycle**.
- Přepnutí zpět na ethernet se posílá **přes serial**, pak **power-cycle**.
- Příkaz se vždy přijímá jen na aktivním rozhraní.

| workMode | význam |
|---|---|
| 0 | Ethernet (default), IMU on, 3D, standard FOV, self-start |
| 8 | Serial (bit 3 = 1), jinak stejné |

## Skripty (v této složce)
| Skript | Co dělá |
|---|---|
| `./start.sh` | **Ethernet**: nastaví IP na eno1 + živě čte point cloud + IMU |
| `./stop.sh` | Ukončí čtení + **vrátí síť do původního stavu** (odebere IP z eno1) |
| `./switch-to-serial.sh` | Přepne LiDAR ENET→serial (přes UDP). Pak **power-cycle** + `./start-usb.sh` |
| `./start-usb.sh` | **USB/serial**: živě čte z `/dev/ttyACM0` |
| `./switch-to-ethernet.sh` | Přepne LiDAR serial→ENET (přes serial). Pak **power-cycle** + `./start.sh` |
| `./setup-temp-sudo.sh` | (root) dočasné bezheslové sudo na 4 h (kvůli `ip addr`) |
| `./remove-temp-sudo.sh` | (root) okamžité zrušení dočasného sudo |

Low-level start/standby debug mimo SDK stream najdeš ve složkách `ETHERNET/` a `SERIAL/`.

## Rychlý start — ethernet
```bash
./start.sh      # uvidíš [CLOUD ...] a [IMU ...]; Ctrl+C ukončí
./stop.sh       # úklid + návrat sítě do původního stavu
```

## Přechod na USB
```bash
./switch-to-serial.sh   # přes ethernet pošle příkaz
#   --> VYPNI A ZAPNI NAPÁJENÍ LiDARu <--
./start-usb.sh          # čtení přes /dev/ttyACM0
```
Zpět na ethernet: `./switch-to-ethernet.sh` → power-cycle → `./start.sh`.

## SDK
- Repozitář: `unilidar_sdk2/` (z github.com/unitreerobotics/unilidar_sdk2)
- Knihovna: `unilidar_sdk2/unitree_lidar_sdk/lib/x86_64/libunilidar_sdk2.a`
- Vlastní čtečky (bez `resetLidar()`, čistý konec): `examples/read_udp.cpp`, `examples/read_serial.cpp`
- Build: `cmake -S unilidar_sdk2/unitree_lidar_sdk -B .../build && cmake --build .../build`

## Vizualizace (co LiDAR vidí)
Python prostředí je ve `.venv/` (Open3D 0.19, numpy, matplotlib).

| Příkaz | Co dělá |
|---|---|
| `./view.sh` | interaktivní 3D okno se zachyceným mračnem (`lidar_cloud.pcd`); myš=otáčení, kolečko=zoom |
| `./live-usb.sh` | **živý** 3D náhled v reálném čase přes USB (LiDAR v serial režimu) |
| `./live-ethernet.sh` | živý 3D náhled přes ethernet (LiDAR v ENET režimu) |

Nástroje: `dump_cloud` (sejme N otoček → `lidar_cloud.csv`/`.pcd`), `render_cloud.py` (statický PNG přes matplotlib), `render_o3d.py` (hezčí PNG přes Open3D), `stream_cloud` (streamuje snímky na stdout pro `live_view.py`).

Souřadnice: X = proti vývodu kabelu, Z = nahoru, jednotky **metry**; intenzita = odrazivost.

## ROS / ROS2
SDK obsahuje i `unitree_lidar_ros/` a `unitree_lidar_ros2/` (potřebují ROS + PCL). Zatím nenasazeno.

## Digitální dvojče / SLAM (3D mapa prostoru)
Python prostředí `.venv/` má navíc **KISS-ICP 1.3.0** (SLAM).

| Příkaz | Co dělá |
|---|---|
| `bin/record_seq N [serial\|udp] [slozka]` | nahraje N snímků jako jednotlivé binární PCD (pro SLAM) |
| `.venv/bin/python3 slam_map.py <slozka> <out.pcd> [voxel]` | KISS-ICP slepí snímky do jedné 3D mapy (+ PNG), voxel-downsampluje (disk-safe) |
| `bin/scan_cloud N` + `process_scan.py` | jeden statický sken → kompaktní PCD + rozměry + PNG (smaže raw) |
| `measure.py <pcd>` | interaktivní měření vzdáleností (shift+klik, metry) |

Postup (handheld): `bin/record_seq 180 serial seq` (pomalu naklánět/otáčet) → `slam_map.py seq room_map.pcd` → `view.sh room_map.pcd`.

**Poznatky:** KISS-ICP je lidar-only (bez IMU, bez loop closure) → handheld **driftuje** (rotace/náklon = bohaté pokrytí, ale zkosené; translace = čisté, ale řídké). Kabel (~0,7 m dosah) je hlavní limit pokrytí. Pro čistý dvojník: **multi-station statické skeny** (sedí na kabel) nebo **FAST-LIO2** (lidar+IMU, ROS2 + vyřešit mobilitu = dlouhý ethernet + přenosné napájení). Rozpoznání objektů = AI vrstva navrch (3D segmentace / kamera+YOLO).
