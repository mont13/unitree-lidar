# 04 — Real-time live preview

V projektu už existuje živý 3D náhled:

```text
../../live_view.py
../../live-usb.sh
../../live-ethernet.sh
../../unilidar_sdk2/unitree_lidar_sdk/bin/stream_cloud
```

Tato složka ho přidává jako součást pokusu přes wrapper:

```bash
cd /path/to/unitree-lidar
measurements/continuous_movement/live_preview.sh usb
```

Pro ethernet režim:

```bash
measurements/continuous_movement/live_preview.sh ethernet
```

## Co musí být splněné

- LiDAR je v odpovídajícím režimu: serial pro `usb`, ENET pro `ethernet`.
- Je dostupný displej (`echo $DISPLAY`).
- Je nainstalované `.venv` s Open3D.
- Existuje SDK binárka `stream_cloud`.

Rychlá kontrola:

```bash
measurements/continuous_movement/check_components.sh
```

## Stav v této pracovní kopii při založení složky

- SDK binárky `stream_cloud` a `record_seq` existovaly.
- `.venv` v kořeni repa nebylo nalezené.
- Systémový Python měl `numpy`/`matplotlib`, ale neměl `open3d`, `kiss_icp`, `rerun` ani `pyserial`.

Proto live preview bereme jako připravenou komponentu, kterou po instalaci `.venv` vyzkoušíme.

## Instalace pro live preview

```bash
python3.12 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 -c "import open3d; print('Open3D OK')"
```

Potom:

```bash
measurements/continuous_movement/live_preview.sh usb
```

V okně: myš = otáčení, kolečko = zoom, `Q`/Esc = konec.
