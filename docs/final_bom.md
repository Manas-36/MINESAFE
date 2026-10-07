# MineSafe — components for the final product

Prices are approximate Indian online prices (Oct 2026); check before ordering. "Prototype" = what works on the bench now. "Final" = what we recommend for the demo unit / V4 boards.

## 1. Body unit (one per worker)
| Part | Prototype (have / use now) | Final product | Qty | ≈ ₹ |
|---|---|---|---|---|
| Controller | ESP32-C6-WROOM-1 DevKit | ESP32-C6-MINI-1 module on our own PCB (V4) | 1 | 300–800 |
| Motion | MPU6050 (GY-521) | BMI270 / LSM6DSO (smaller, lower power) | 1 | 150–350 |
| Pressure (height) | BMP180 | BMP390 | 1 | 120–450 |
| Skin temperature | DS18B20 probe + 4.7 kΩ | MAX30208 / TMP117 chip on the back plate | 1 | 120–500 |
| Pulse + SpO₂ | MAX30102 (+ HW-827 backup) | MAX30101 / MAX30102 behind a window | 1 | 150–400 |
| SOS button | tactile button | large glove-friendly button | 1 | 20 |
| Alert | red LED + 220 Ω | LED + **vibration motor** (with NPN / MOSFET driver) | 1 | 60 |
| Battery | 3.7 V Li-ion / LiPo 1000 mAh | LiPo 500–1000 mAh with protection | 1 | 250 |
| Charging | TP4056 module with protection | charger IC (e.g. TP4056 / MCP73831) + pogo-pin dock | 1 | 50 |
| 3.3 V regulator | on the DevKit | low-quiescent LDO (e.g. ME6211, HT7333) | 1 | 20 |
| Enclosure + strap | 3D-printed case, elastic strap | sealed case (IP65+) chest strap or arm band | 1 | 300 |

## 2. Repeater (one every ~30–60 m of tunnel, to be found in the range test)
| Part | Prototype | Final product | Qty | ≈ ₹ |
|---|---|---|---|---|
| Controller | Seeed XIAO ESP32-C6 | XIAO ESP32-C6 or ESP32-C6-MINI-1 on own PCB | 1 | 600 |
| Antenna | built-in | 2.4 GHz u.FL → SMA pigtail + 3–5 dBi antenna | 1 | 250 |
| **Exit sign display** | — | **MAX7219 8×32 LED matrix (FC-16, 4-in-1)** | 1 | 250–350 |
| Buzzer | active 3.3 V buzzer | loud 5 V / 12 V buzzer (≥ 85 dB) + NPN driver | 1 | 60 |
| Gas sensor 1 | MQ-2 | **MQ-4 (methane)** → final: NDIR CH₄ module | 1 | 150 / 2500+ |
| Gas sensor 2 | — | **MQ-7 (CO)** → final: electrochemical CO module | 1 | 150 / 1500+ |
| Gas sensor 3 | — | **MQ-136 (H₂S)** or O₂ cell → final: electrochemical | 1 | 400 / 2000+ |
| Divider for each MQ | 10 kΩ + 20 kΩ | same | 3 sets | 10 |
| Air temperature + humidity | AHT20 | AHT20 / SHT40 | 1 | 245 |
| SOS button | — | panel push button (hold 1.5 s) | 1 | 40 |
| Power | USB power bank | 5 V 3 A supply / 18650 pack with backup + charger (MQ heaters ≈ 150 mA each) | 1 | 500 |
| Enclosure | — | IP65 ABS box with a clear window for the display, gas-sensor vents | 1 | 300 |

## 3. Entry / scanning station (at the gate)
| Part | Choice | Qty | ≈ ₹ |
|---|---|---|---|
| Controller | ESP32-C6 (C6-WROOM-1 DevKit or XIAO C6) | 1 | 600–800 |
| RFID / NFC reader | **HW-147C PN532** (I²C mode) | 1 | 300 |
| Tags | NTAG215 stickers (helmet, vest, pants, shoes) | 4 per worker | 40 each |
| Display | SSD1306 0.96" OLED (I²C) | 1 | 200 |
| Buttons | READ, WRITE, PHOTO | 3 | 30 |
| Photo for the AI kit check | phone camera page (`/phone`) | — | 0 |
| Power + box | 5 V adapter, small enclosure | 1 | 300 |

## 4. Control room
| Part | Choice |
|---|---|
| Hub | laptop (Windows / Linux) running `admin_hub.py`; for a permanent install a mini-PC or Raspberry Pi 5 |
| Network | phone hotspot for the demo → a dedicated 2.4 GHz Wi-Fi router for a real site |
| Backup | UPS for the hub + router |

## 5. Wiring and tools
Jumper wires, perfboard / PCB, headers, heat-shrink, JST connectors, soldering kit, multimeter.

## Prototype set to build now (1 body unit, 3 repeaters, 1 entry station)
≈ ₹2,000 body unit + 3 × ≈ ₹2,300 repeaters (with matrix + 3 MQ sensors) + ≈ ₹1,600 entry station ≈ **₹10,500**, plus wiring and boxes. Upgrading every repeater's gas sensors to electrochemical / NDIR adds roughly ₹5,000–8,000 per repeater.
