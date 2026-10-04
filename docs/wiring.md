# Wiring

Schematics are generated from `docs/wiring/make_schematics.py` (run it after changing a pin). SVG = sharp/zoomable, PNG = for slides, Notion and the report.

## System interconnection
![System](wiring/system_overview.svg)

## Body unit
![Body unit schematic](wiring/body_unit.svg)

## Body unit

| Connection | ESP32-S3 | XIAO ESP32-C6 |
|---|---|---|
| I2C SDA — MPU6050, BMP180, MAX3010x (all in parallel) | GPIO8 | D4 |
| I2C SCL — same three | GPIO9 | D5 |
| Sensor VCC/VIN, GND | 3V3, GND | 3V3, GND |
| DS18B20 data (red → 3V3, black → GND) + **4.7 kΩ data → 3V3** | GPIO7 | D3 |
| HW-827 pulse sensor S (+ → 3V3, − → GND) | GPIO1 | D0 |
| SOS button (other leg → GND) | GPIO5 | D8 |
| Red LED via 220 Ω (LED − → GND) | GPIO4 | D10 |

I2C addresses: MPU6050 `0x68`, BMP180 `0x77`, MAX30100/30102 `0x57`.
The green MAX3010x board pulls its I2C lines to 1.8 V; sharing the bus with the GY-521 (3.3 V pull-ups) usually makes it read reliably.

## Repeater

![Repeater schematic](wiring/repeater_node.svg)

| Connection | ESP32-S3 | XIAO ESP32-C6 |
|---|---|---|
| Buzzer + (− → GND) | GPIO5 | D10 (GPIO18) |
| MQ gas AO → 10 kΩ → pin, pin → 20 kΩ → GND (module VCC → 5 V) | GPIO4 | D2 |
| External 2.4 GHz antenna (u.FL → SMA pigtail) | — | u.FL, `USE_EXTERNAL_ANTENNA 1` |

The 10 k / 20 k divider keeps the 0–5 V MQ output safe for the 3.3 V pin; the code multiplies by 1.5 to undo it.

## Entry station (XIAO ESP32-C6)

![Entry station schematic](wiring/entry_station.svg)

| Connection | Pin |
|---|---|
| PN532 + SSD1306 OLED SDA | D4 |
| PN532 + OLED SCL | D5 |
| READ button (→ GND) | D1 |
| WRITE button (→ GND) | D0 |
| VCC / GND | 3V3 / GND |

Libraries: Adafruit PN532, Adafruit SSD1306, Adafruit GFX. PN532 DIP switches set to I2C.
