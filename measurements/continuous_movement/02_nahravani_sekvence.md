# 02 — Nahrávání pohybové sekvence

Máme dvě možné cesty.

## A) Doporučená cesta teď: přímý serial recorder

Používá nový nástroj:

```text
../../record_serial_sequence_direct.py
```

Výhoda: navazuje na funkční raw parser ze `scan_serial_direct.py`, který obešel problém C++ SDK serial parseru.

Spuštění přes wrapper:

```bash
cd /path/to/unitree-lidar
measurements/continuous_movement/record_sequence.sh
```

Výchozí hodnoty wrapperu:

```text
FRAMES=150
DURATION_SECONDS=30
PACKETS_PER_FRAME=20
OUT_DIR=measurements/continuous_movement/scans/seq_<timestamp>
```

Po doběhnutí vznikne:

```text
measurements/continuous_movement/scans/seq_YYYYMMDD_HHMMSS/
  000000.pcd
  000001.pcd
  ...
  index.csv
  meta.txt
```

A symlink:

```text
measurements/continuous_movement/scans/latest_sequence
```

### Kratší první test

```bash
FRAMES=80 DURATION_SECONDS=15 PACKETS_PER_FRAME=20 \
  measurements/continuous_movement/record_sequence.sh
```

### Ruční spuštění bez wrapperu

```bash
./record_serial_sequence_direct.py \
  --port /dev/ttyACM0 \
  --frames 120 \
  --seconds 20 \
  --packets-per-frame 20 \
  --out-dir measurements/continuous_movement/scans/seq_test
```

## B) Alternativa: C++ SDK `record_seq`

Pokud bude fungovat SDK parser, jde použít i původní cesta:

```bash
unilidar_sdk2/unitree_lidar_sdk/bin/record_seq 180 serial \
  measurements/continuous_movement/scans/seq_sdk_test
```

Poznámka: dříve serial čtení přes SDK vracelo 0 cloudů, proto je pro tuto složku připravená přímá Python cesta A.

## Pohyb při nahrávání

Pro první mapu:

- LiDAR držet co nejstabilněji,
- pomalu se otáčet,
- nechodit rychle,
- nezakrývat LiDAR rukou/kabelem,
- ideálně stále vidět stejné hrany místnosti.
