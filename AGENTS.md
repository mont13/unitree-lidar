# AGENTS.md

## What this repo is

Operational scripts (Bash + Python) and a C++ example overlay for the **Unitree 4D LiDAR L2** sensor on Linux. The vendored Unitree C++ SDK is **not** in this repo — it is cloned separately and the `sdk-overlay/` is copied into it. Python tools assume a local `.venv/`. User-facing READMEs (`README.md`, `README-LIDAR.md`) are in Czech.

## Layout

- `*.sh` — top-level entrypoints. Each derives its own root from `${BASH_SOURCE[0]}`; no hardcoded paths.
- `*.py` — Python tools; all assume `.venv/bin/python3` (called directly by `view.sh`, `rerun-view.sh`, `live-usb.sh`).
- `sdk-overlay/` — C++ sources + `CMakeLists.txt` to overlay onto a fresh `unilidar_sdk2` clone. Builds produce binaries in `unilidar_sdk2/unitree_lidar_sdk/bin/`.
- `glim_config/` — tuned GLIM config (Unitree topics, CPU-only, IMU off, custom extrinsics). **Active**.
- `glim_config_ref/` — upstream reference config (Ouster topics, GPU, IMU on). Do not edit; kept only for diffs.
- `glim_config/` vs `glim_config_ref/`: they differ in `config.json` (CPU vs GPU backend), `config_ros.json` (topic names), `config_sensors.json` (extrinsics + intensity field), and `config_*_mapping_cpu.json` (`enable_imu` flag). Trust `glim_config/` for actual runs.

## Required setup (in order)

1. **System packages** (Ubuntu): `python3.12 python3.12-venv cmake g++ libgl1 libgomp1 libusb-1.0-0`.
2. **Python venv** — must use `python3.12` (system `python3` is often 3.10 and versions in `requirements.txt` will not resolve):
   ```
   python3.12 -m venv .venv
   .venv/bin/pip install -U pip
   .venv/bin/pip install -r requirements.txt
   ```
   `requirements.txt` is a flat pinned lockfile (every entry has `==`).
3. **Clone + overlay the SDK** (one-time, not committed — see `.gitignore`):
   ```
   git clone https://github.com/unitreerobotics/unilidar_sdk2.git
   cp sdk-overlay/examples/*.cpp unilidar_sdk2/unitree_lidar_sdk/examples/
   cp sdk-overlay/CMakeLists.txt  unilidar_sdk2/unitree_lidar_sdk/CMakeLists.txt
   cmake -S unilidar_sdk2/unitree_lidar_sdk -B unilidar_sdk2/unitree_lidar_sdk/build
   cmake --build unilidar_sdk2/unitree_lidar_sdk/build -j
   ```
   Produced binaries: `read_udp`, `read_serial`, `stream_cloud`, `dump_cloud`, `lidar_motor`, `record_seq`, `record_glim`, `scan_cloud`, `set_to_serial_mode`, `set_to_udp_mode`.
4. **Serial port group** — `/dev/ttyACM0` needs `dialout`. Either `sudo usermod -aG dialout $USER` + relogin, or `sg dialout -c "<cmd>"`, or `sudo`. `setup-temp-sudo.sh` grants 4h NOPASSWD sudo (`remove-temp-sudo.sh` revokes).

## Critical operational rules

- **Never move prebuilt SDK binaries between machines.** Different GCC/libstdc++ versions cause `GLIBCXX_... not found` at run time. Always rebuild locally with the cmake steps above.
- **The LiDAR is single-channel.** It streams point cloud over ethernet **or** serial, never both. Modes are `workMode 0` (ENET, factory default) and `workMode 8` (serial).
- **Every `workMode` change requires a hardware power-cycle** (DC adapter off/on) before the new mode takes effect.
- **The workMode switch is asymmetric**: `switch-to-serial.sh` (ENET→serial) sends the command **over ethernet**; `switch-to-ethernet.sh` (serial→ENET) sends it **over serial**. Trying the wrong transport will silently no-op.
- **Ethernet scripts have a hard safety guard**: `start.sh`, `live-ethernet.sh`, `switch-to-serial.sh` refuse to add `192.168.1.2/24` to a NIC that carries the default route. On a single-NIC host, use USB/serial. To target a different NIC, set `LIDAR_IFACE=<name>`.
- **Fixed LiDAR ENET addressing**: LiDAR = `192.168.1.62`, PC = `192.168.1.2/24` (no DHCP on the LiDAR). USB serial = `/dev/ttyACM0` at 4 000 000 baud.
- **DC power is required.** The LiDAR does not power itself from USB or PoE. If `/dev/ttyACM0` is missing or the device is silent, check the DC adapter and `lsusb` (WCH/QinHeng chip) before debugging further.
- **Lidar-only SLAM (KISS-ICP) drifts when handheld** — no IMU fusion, no loop closure. For better results use multi-station static scans or the GLIM/FAST-LIO2 path (`record_glim` → `make_rosbag.py` → GLIM).

## Common workflows

- **Live ENET read**: `./start.sh` (Ctrl+C to stop, then `./stop.sh` to remove the IP).
- **Live USB read**: `./start-usb.sh` (LiDAR must already be in serial mode).
- **Live 3D preview**: `./live-ethernet.sh` or `./live-usb.sh` (requires a display; Open3D window).
- **Headless preview**: `.venv/bin/python3 render_pcd.py <in.pcd> [out.png]` — works over SSH, uses matplotlib/Agg.
- **KISS-ICP mapping**: `bin/record_seq 180 serial seq` (slowly tilt/rotate) → `.venv/bin/python3 slam_map.py seq room_map.pcd` → `./view.sh room_map.pcd`.
- **Static scan + measure**: `bin/scan_cloud N` → `process_scan.py` → `measure.py room_scan.pcd` (shift+click to pick points, Q to print distances).
- **Motor standby**: `./lidar-quiet.sh` (stops rotation, ~1 W); wake with `./lidar-wake.sh`. Requires serial mode.
- **GLIM export**: `bin/record_glim` writes `glim_seq/{imu.csv,index.csv,clouds/*.bin}`; `make_rosbag.py glim_seq` produces an MCAP with topics `/unilidar/cloud` (sensor_msgs/PointCloud2, xyz only) and `/unilidar/imu` (sensor_msgs/Imu). Add `--with-time` to include per-point `t` (deskew).

## Environment variables

- `LIDAR_PORT` — serial device (default `/dev/ttyACM0`).
- `LIDAR_IFACE` — NIC for ethernet mode (default `eno1`).

## Testing / linting / CI

None. There is no test framework, no `pyproject.toml`, no linter, no formatter config, and no CI workflow. `.gitignore` covers Python caches, CMake build dirs, the vendored SDK clone, and all generated artifacts (`*.pcd`, `*.png`, `*.csv`, `*.mcap`, `*.bin`, `seq/`, `glim_seq/`). Verify Python changes by running the script with a real sensor or a fixture `.pcd`; verify Bash changes by `bash -n <file>` and reading end-to-end with `set -x`.

## License notes (if adding files)

Root repo (`*.py`, `*.sh`, `sdk-overlay/` originals) is **MIT** (see `LICENSE`). `sdk-overlay/examples/` are derived from Unitree's BSD-3-Clause examples — keep that header attribution. `unilidar_sdk2/` (cloned separately) is BSD-3-Clause © Unitree Robotics.
