# Unitree LiDAR L2/L24D — low-level USB/SERIAL debug

Stav: **ověřeno fyzicky i přes ACK_SUCCESS** — přes USB jde LiDAR roztočit a zase zastavit.

Detailní první checklist po připojení LiDARu je v `../SETUP.md`.

Cíl téhle složky: mít oddělené USB/serial ovládání LiDARu, nezávisle na hlavních SDK stream skriptech.

## Ověřený výsledek

Test `./test_usb_start_stop_10s.sh` prošel:

- `--start`: ACK_SUCCESS
- čekání 10 s
- `--standby`: ACK_SUCCESS
- fyzicky potvrzeno: motor se roztočil a zastavil

## Co bylo rozbité před opravou

Původní USB pokus selhával na:

```text
ACK_CRC_ERROR
```

Důvod byl špatný CRC výpočet:

```text
špatně: CRC(header + payload)
správně podle SDK2: CRC(payload only)
```

Skript v této složce už má CRC opravené.

## USB defaulty

```text
port:     auto přes /dev/serial/by-id/*, /dev/ttyACM*, /dev/ttyUSB*, fallback /dev/ttyACM0
baudrate: 4000000
packet:   packet_type=100, cmd_type=2
start:    cmd_value=0
standby:  cmd_value=1
```

## Rychlé příkazy

Vše spouštěj z této složky:

```bash
cd SERIAL
```

### Zastavit přes USB / standby

```bash
./stop_lidar_usb.sh
```

nebo ručně:

```bash
sudo python3 ./unitree_lidar_usb_standby.py --port /dev/ttyACM0 --standby --repeat 5 --listen 2
```

### Roztočit přes USB

```bash
./start_lidar_usb.sh
```

nebo ručně:

```bash
sudo python3 ./unitree_lidar_usb_standby.py --port /dev/ttyACM0 --start --repeat 5 --listen 2
```

### Ověřený USB test: start → čekat 10 s → standby

```bash
./test_usb_start_stop_10s.sh
```

## Jak poznat úspěch

Ověřený dobrý výstup:

```text
ACK: packet_type=100, cmd_type=2, cmd_value=0/1, status=1 (ACK_SUCCESS)
Done: LiDAR accepted command.
```

Fail:

```text
ACK_CRC_ERROR
Command was NOT accepted.
```

Pokud se fyzicky roztočí/zastaví, USB control funguje i kdyby výstup nebyl perfektní.

## Když není port

Zkontroluj:

```bash
ls -l /dev/serial/by-id/* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Pokud port existuje, ale nejde otevřít, použij `sudo` nebo přidej uživatele do `dialout`.

## Vztah k hlavnímu repu

- Tahle složka = low-level debug start/standby přes USB a ověřování ACK/CRC.
- Hlavní stream/vizualizace přes SDK jsou v rootu repa (`start-usb.sh`, `live-usb.sh`, `switch-to-ethernet.sh`).
- Pro tyto Python debug skripty **není potřeba buildovat SDK**.

## Bezpečnost

- `--start` roztočí motor.
- `--standby` motor zastaví.
- Nestrkej prsty do rotující části.
- Když se nechová očekávaně, odpoj 12V napájení / e-stop.
