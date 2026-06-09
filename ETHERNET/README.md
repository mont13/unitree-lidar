# Unitree LiDAR L2/L24D — low-level Ethernet debug

Stav: **ověřeno fyzicky** — přes Ethernet jde LiDAR roztočit a zase zastavit.

Detailní první checklist po připojení LiDARu je v `../SETUP.md`.

Tahle složka je runbook pro nízkoúrovňové UDP ovládání, aby se nemusel znovu opakovat debug s timeouty, ACK a CRC.

## Ověřená síť

Unitree defaulty:

```text
LiDAR IP:        192.168.1.62
LiDAR UDP port:  6101
PC IP:           192.168.1.2/24
PC UDP port:     6201
```

Ověření:

```bash
ping 192.168.1.62
```

## Nejdůležitější závěr

**Ethernet command funguje.**

Skript může vypsat:

```text
No ACK/data frame seen after command.
exit code: 1
```

To samo o sobě neznamená fail. U tohoto kusu se ACK přes náš UDP socket nemusí vrátit / naparsovat, ale fyzicky motor reaguje:

- `--start` motor roztočil
- po 10 s `--standby` motor zastavil

Tedy rozhodující ověření je fyzický stav motoru.

## Rychlé příkazy

Vše spouštěj z této složky:

```bash
cd ETHERNET
```

### Zastavit LiDAR / standby

```bash
python3 ./unitree_lidar_udp_cmd.py   --local-ip 192.168.1.2   --lidar-ip 192.168.1.62   --standby   --repeat 5   --listen 2
```

### Roztočit LiDAR

```bash
python3 ./unitree_lidar_udp_cmd.py   --local-ip 192.168.1.2   --lidar-ip 192.168.1.62   --start   --repeat 5   --listen 1
```

### Ověřený test: start → čekat 10 s → standby

```bash
./test_start_stop_10s.sh
```

Tenhle test byl fyzicky potvrzený: LiDAR se roztočil a pak zastavil.

## Když není PC IP nastavená

Zjisti interface:

```bash
ip -br addr
```

Nastav Ethernet interface, tady jen jako příklad `enp14s0`:

```bash
sudo ip addr flush dev enp14s0
sudo ip addr add 192.168.1.2/24 dev enp14s0
sudo ip link set enp14s0 up
```

Pak:

```bash
ping 192.168.1.62
```

## Pozor na UDP port

Skript binduje lokální UDP port `6201`. Pokud by byl obsazený ROS/SDK/GUI, zastav ho.

Kontrola:

```bash
ss -ulpn 'sport = :6201'
```

## Proč předtím USB i první UDP selhávalo

Původní ruční packet počítal CRC špatně:

```text
špatně: CRC(header + payload)
správně podle SDK2: CRC(payload only)
```

Proto USB vracelo:

```text
ACK_CRC_ERROR
```

Po opravě CRC odpovídají packety tomu, co generuje SDK2.

## Ověřené packety

Start motoru:

```text
cmd_type=2
cmd_value=0
packet:
55aa050a6400000020000000020000000000000014d8072700000000000000ff
```

Stop / standby:

```text
cmd_type=2
cmd_value=1
packet:
55aa050a6400000020000000020000000100000071bfbb9f00000000000000ff
```

Volání ve skriptu:

```text
packet_type = 100                  # LIDAR_USER_CMD_PACKET_TYPE
cmd_type    = 2                    # USER_CMD_STANDBY_TYPE
cmd_value   = 0 start / 1 standby
CRC         = binascii.crc32(payload)
```

## Přepnutí zpět do USB/serial módu — jen pokud fakt chceš

Nepotřebné pro samotné zastavení/roztočení. Pokud ale chceš přepnout work mode zpět na serial:

```bash
python3 ./unitree_lidar_udp_cmd.py   --local-ip 192.168.1.2   --lidar-ip 192.168.1.62   --work-mode 8   --repeat 3   --listen 2
```

Potom je potřeba LiDAR **vypnout a znovu zapnout**.

Poznámka: SDK2 header říká work-mode packet type `107`, ale x86_64 SDK2 binárka reálně používá `2002`. Tenhle skript používá `2002`.

## Vztah k hlavnímu repu

- Tahle složka = low-level debug start/standby/work-mode po UDP.
- Hlavní stream/vizualizace přes SDK jsou v rootu repa (`start.sh`, `live-ethernet.sh`, `switch-to-serial.sh`).
- Pro tyto Python debug skripty **není potřeba buildovat SDK**.

## Bezpečnost

- Nestrkej prsty do rotující části.
- Když se zařízení nechová očekávaně, odpoj 12V napájení / e-stop.
- `--start` motor roztočí. `--standby` ho zastaví.
