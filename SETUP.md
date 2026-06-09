# SETUP — Unitree LiDAR připojení po zapojení

Tento soubor je první checklist po připojení LiDARu. Pokud chceš nejdřív ověřit jen komunikaci, start/standby motoru a debugovat timeouty/ACK, začni tady.

Detailní low-level runbooky jsou potom v:

```text
ETHERNET/README.md
SERIAL/README.md
```

## 0. Bezpečnost

- Nechytej rotující část rukou.
- `start` motor roztočí.
- `standby` motor zastaví.
- Když se zařízení chová divně, odpoj 12V napájení / e-stop.

## 1. Ethernet setup

Ověřené Unitree defaulty:

```text
LiDAR IP:        192.168.1.62
LiDAR UDP port:  6101
PC IP:           192.168.1.2/24
PC UDP port:     6201
```

### 1.1 Najít síťový interface

```bash
ip -br addr
```

Najdi Ethernet interface připojený k LiDARu. Pokud repo skripty nepoužívají správný NIC, nastav ho přes `LIDAR_IFACE=<nic>`.

### 1.2 Nastavit PC IP pro LiDAR

Pozor: nahraď `enp14s0`, pokud máš jiný interface.

```bash
sudo ip addr flush dev enp14s0
sudo ip addr add 192.168.1.2/24 dev enp14s0
sudo ip link set enp14s0 up
```

### 1.3 Ověřit, že LiDAR odpovídá

```bash
ping 192.168.1.62
```

Očekávání: ping odpovídá.

### 1.4 Zkontrolovat, že UDP port 6201 není obsazený

```bash
ss -ulpn 'sport = :6201'
```

Pokud ho drží ROS/SDK/GUI, zastav ten proces.

### 1.5 Ověřený Ethernet start/stop test

```bash
cd ETHERNET
./test_start_stop_10s.sh
```

Poznámka: u tohoto kusu Ethernet skript nemusí vidět ACK a může vypsat `No ACK/data frame seen`, ale fyzicky bylo ověřeno, že motor reaguje.

Rychlé Ethernet debug příkazy:

```bash
cd ETHERNET
./start_lidar.sh
./stop_lidar.sh
```

## 2. USB/SERIAL setup

USB control je ověřený přes `/dev/ttyACM0` na 4 000 000 baud.

### 2.1 Najít USB serial port

```bash
ls -l /dev/serial/by-id/* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

### 2.2 Permission poznámka

Typicky je port ve skupině `dialout` a wrappery v `SERIAL/` proto používají `sudo`.

Volitelně lze uživatele přidat do `dialout`, potom se odhlásit/přihlásit:

```bash
sudo usermod -aG dialout "$USER"
```

### 2.3 Ověřený USB/SERIAL start/stop test

```bash
cd SERIAL
./test_usb_start_stop_10s.sh
```

Očekávaný dobrý výstup:

```text
status=1 (ACK_SUCCESS)
Done: LiDAR accepted command.
```

Rychlé USB debug příkazy:

```bash
cd SERIAL
./start_lidar_usb.sh
./stop_lidar_usb.sh
```

## 3. Aktuálně ověřené výsledky

- Ethernet: `start` roztočil, `standby` zastavil.
- USB/SERIAL: `start` vrací `ACK_SUCCESS`, `standby` vrací `ACK_SUCCESS`, motor se fyzicky roztočí a zastaví.
- Původní problém byl CRC: správně je `CRC(payload only)`, ne `CRC(header + payload)`.

## 4. Kdy použít které skripty

- `ETHERNET/` a `SERIAL/` = low-level debug start/standby/work-mode, dobré pro timeouty, ACK a CRC.
- `start.sh`, `start-usb.sh`, `live-*.sh` = hlavní repo skripty pro stream, vizualizaci a další práci přes SDK.

## 5. SDK2 pro další práci

Pro samotný start/stop SDK není potřeba, protože to řeší Python debug skripty v `ETHERNET/` a `SERIAL/`.

Pro další věci jako point cloud, IMU data, vizualizace, ROS/ROS2 a PCL se SDK hodí / bude potřeba:

```text
./unilidar_sdk2
```

Build SDK může vyžadovat systémové balíčky popsané v [`README.md`](README.md) v části instalace. Pak:


```bash
cd unilidar_sdk2/unitree_lidar_sdk
mkdir -p build
cd build
cmake ..
make -j$(nproc)
```
