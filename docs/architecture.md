# Architecture

## Data and alert paths
```mermaid
flowchart LR
  B["Body unit<br>worn by miner"] -->|ESP-NOW| R3["REP-03<br>2 hops"]
  R3 -->|ESP-NOW| R2["REP-02<br>1 hop"]
  R2 -->|ESP-NOW| R1["REP-01 main<br>hop 0"]
  R1 -->|"Wi-Fi HTTP every 1 s"| H["Admin hub (laptop)<br>Flask + AI + map + gas"]
  P["Phone camera<br>entry photo"] -->|Wi-Fi| H
  E["Entry station<br>RFID gear tags"] -->|Wi-Fi| H
  H -.->|"alert in reply"| R1
  R1 -.->|beacons| R2
  R2 -.->|beacons| R3
  R3 -.->|"beacons → LED"| B
```
- **Up:** a body unit broadcasts one 54-byte packet per second; every repeater that hears it forwards it toward the main repeater (fewest hops), which posts all packets to the hub every second.
- **Down:** the hub's HTTP reply carries the alert (`id`, `level`, `target`). Repeaters adopt any newer alert ID and repeat it in their beacons, so every buzzer sounds and every body LED lights.

## Worker journey
```mermaid
flowchart LR
  A["1 Register<br>name, blood group,<br>medical notes, body ID"] --> B["2 Gear scan<br>RFID tags at gate"]
  B --> C["3 AI photo<br>helmet, vest, shoes"]
  C --> D["4 Approve<br>body unit paired"]
  D --> E["5 Monitor<br>vitals, motion,<br>map every second"]
  E --> F{"Danger?"}
  F -->|"fall / SOS / gas / heat"| G["6 Alert<br>buzzers + LED,<br>rescue with location<br>+ medical card"]
  F -->|no| E
```

## Self-forming repeater chain
- Every repeater beacons once a second: number, hops to the main repeater, radio channel, current alert.
- Each repeater picks the neighbour with the fewest hops (signal ≥ −92 dBm) as its parent; routes form and heal on their own.
- A repeater or body unit that hears nothing for 8 s scans channels 1–13 and rejoins; the chain follows the hotspot's Wi-Fi channel.

## GPS-free location (hub side)
1. Steps × step length along the gyro heading (heading = rotation about the gravity vector).
2. Map matching: the tunnel that runs the way the worker walks wins over a closer crossing one; tunnel direction slowly corrects gyro drift.
3. Repeater check-points: strong signal (≥ −55 dBm) = within a few metres → error resets.
4. Height from BMP180 pressure (z).

## Software
| Component | Language | Notes |
|---|---|---|
| `firmware/body_node` | Arduino C++ (ESP32 core 3.x) | sensor drivers written in-house, no libraries |
| `firmware/repeater_node` | Arduino C++ | ESP-NOW chain, HTTP uplink, phone test page, gas |
| `firmware/entry_station` | Arduino C++ | Adafruit PN532 / SSD1306 / GFX |
| `hub/admin_hub.py` | Python 3, Flask | dashboard in one file; optional `ultralytics` for AI |
