# Changelog and progress

Each version is one commit on `main` and has its own branch, `version/v0.0` … `version/v1.0` — pick it from the branch menu on GitHub (or `git checkout version/v0.3`) to see the project at that stage. The history was assembled on 3 Oct 2026 from the files saved during development; dates are approximate.

## Major versions
| | What | Network | Viewing | Guide |
|---|---|---|---|---|
| **V1** | Body ESP only, repeaters on Wi-Fi, data stored in the cloud | Wi-Fi + internet | No website — data extracted by hand | [docs/v1.md](docs/v1.md) |
| **V2** | Body ESP ↔ repeaters over ESP-NOW, entry station, AI kit check, map, gas (git v0.0–v1.0) | ESP-NOW chain → Wi-Fi to laptop | Control-room website | [docs/v2.md](docs/v2.md) |
| **V3** | Camera entry station, XIAO C6 repeaters, AHT air sensing, sensor integration — **in calibration, not complete** (v3.0–v3.2) | ESP-NOW | Website + camera entry | [docs/v3.md](docs/v3.md) |
| **V4** | **Our own PCBs and sensor boards** (body unit, repeater, entry station) replacing breadboard wiring | ESP-NOW | Website | [docs/v4.md](docs/v4.md) (planned) |

Detailed git versions below (v0.0–v1.0 make up V2).

| Version | When | Milestone |
|---|---|---|
| [v0.0](#v00--research-and-design) | Aug–Sep 2026 | Research, competitive analysis, architecture, pilot BOM |
| [v0.1](#v01--entry-station-and-tag-registry) | Sep 2026 | Entry station reads/writes gear tags; tag registry hub |
| [v0.2](#v02--photo-verification) | Sep 2026 | Phone photo verification and body-unit clearance |
| [v0.3](#v03--control-room-v3) | late Sep 2026 | Control room v3: workers, live monitoring, alerts; entry station v2 |
| [v0.4](#v04--repeater-chain-ai-kit-check-gas) | late Sep 2026 | Repeater chain, AI kit check, gas; Zigbee → ESP-NOW |
| [v0.5](#v05--end-to-end-chain-working) | 1–2 Oct 2026 | First end-to-end run: phone worker, body unit, alerts, buzzer |
| [v0.6](#v06--map-gas-analysis-real-sensors) | 3 Oct 2026 | Tunnel map + GPS-free tracking, gas analysis, real body sensors |
| [v1.0](#v10--documentation-release) | 3 Oct 2026 | Structured repo, docs, presentation, Notion |
| [**V3 · v3.0**](#v3--v30--camera-entry-station-mock-worker-schematics) | 4 Oct 2026 | Camera entry station, mock worker, schematics, admin theme, research docs |
| [v3.1](#v31--aht-air-temperature--humidity-on-repeaters) | 4 Oct 2026 | AHT air temperature + humidity on every repeater, shown in the admin |

---

## v0.0 — Research and design
- Literature review (ILO, DGMS, MSHA, papers) and competitive analysis of nine products.
- Seven-layer architecture; pilot BOM for 20 workers (≈ ₹3,01,000).
- `docs/research/`, `hardware/bom_pilot.csv`.

## v0.1 — Entry station and tag registry
- `firmware/entry_station`: XIAO ESP32-C6 + PN532 + OLED, one button; READ / SELECT / WRITE modes; NTAG215 tag format `MS1:<gear>`.
- `hub/admin_hub.py` (test hub): tags trusted by factory UID, not by the rewritable text; live event list.
- `firmware/tests`: I2C scanner, PN532 + NTAG215 test.

## v0.2 — Photo verification
- Hub v2: phone camera page (`/phone`), gear scans + photo become one verification card, admin approves / rejects, approved body unit is "cleared".

## v0.3 — Control room v3
- Hub v3: worker registration with blood group and medical card, live cards, SAFE / WARNING / DANGER rules, incident log, ALERT to all or one worker, `/api/telemetry` for repeaters.
- Entry station v2: two buttons (READ, WRITE), gear menu with hold-to-select, write counters.
- `tools/sim_repeater.py`: fake repeater chain + three workers for testing without hardware.
- RC522 (I2C, 0x28) reader test.

## v0.4 — Repeater chain, AI kit check, gas
- Hub: AI kit check (YOLOv8 pose + PPE model + reference-photo colours), repeater chain view, gas readings and automatic gas alert.
- `firmware/repeater_node`: self-forming chain (beacons, hop count, parent), channel search, phone test page, gas sensor, buzzer + LED.
- Zigbee build failed on the ESP32-S3 (no 802.15.4 radio) → **whole system moved to ESP-NOW**.

## v0.5 — End-to-end chain working
- Main repeater ↔ hub verified over the phone hotspot; phone as a fake worker (fall, SOS, ALERT → LED).
- Repeater simplified to buzzer only; passive / active-low buzzer options, boot beeps, Serial `b` test.
- Main repeater finds the laptop by itself when the hotspot changes subnet.
- `firmware/body_node` v1: SOS button + alert LED over ESP-NOW, placeholder readings; BODY-01 reached the admin page through REP-01.

## v0.6 — Map, gas analysis, real sensors
- **Map tab:** upload mine plan, hub = (0,0,0), scale, tunnels, repeaters; worker dots with trails and uncertainty circle; step + gyro dead reckoning with direction-aware tunnel matching and repeater check-points; BMP180 height; Demo walker.
- **Gas & air tab:** MQ-2/4/5/7/9/135 curves, Rs/R0 with automatic clean-air calibration, per-gas ppm, main-gas alarms, backup mV alarm.
- Phone test page: walk buttons, auto walk, height and heart-rate sliders.
- **Body unit v2:** MPU6050 (steps, heading, fall, impact, no movement), BMP180, DS18B20, MAX30100/30102 or HW-827 (heart rate, SpO₂ estimate); "I'm OK" button; no external libraries.
- Packet extended: steps, heading, height, heart rate, SpO₂. Repeater: gas back on with sensor-present check and relative local alarm; optional external antenna (XIAO).
- Hub: heart-rate / SpO₂ limits, worker panel with heart-rate chart, repeater IP + phone-page link.
- Secrets (hotspot password, laptop IP) moved to `secrets.h` (not uploaded).

## v1.0 — Documentation release
- Repository restructured: `firmware/`, `hub/`, `tools/`, `hardware/`, `docs/`.
- README, architecture, wiring, setup, protocol, design decisions, screenshots.
- 22-slide presentation (Claude Slides) and Notion project wiki with BOM and test-log databases.

## Next
- [ ] Bench-test body unit v2 with all sensors (I2C scan, steps, fall, heart rate)
- [ ] AI kit check with reference photos of our helmet and vest
- [ ] Entry station connected to the hub over Wi-Fi
- [ ] Kit-removal sensing (helmet IR sensor, vest buckle reed switch)
- [ ] Battery, enclosure, demo video

## v3.2 — Sensor integration and calibration (in progress)
Status: **V3 is being calibrated — not complete.** Sensors are being integrated and checked one board at a time before V4 moves everything onto our own PCBs.
- `firmware/body_node`: own pin map for the **ESP32-C6-WROOM-1 DevKit** (SDA 6, SCL 7, DS18B20 10, HW-827 2, button 18, LED 19), picked automatically on *ESP32C6 Dev Module*; output on **both** USB and UART sockets so the Serial Monitor works whatever the *USB CDC On Boot* setting.
- `firmware/tests/body_sensor_test`: PASS / FAIL for MPU6050, BMP180, MAX3010x, DS18B20, HW-827, button and LED; live readings; **wire check** (pull-up test) and **`f` pin finder**.
- `firmware/tests/entry_hw_test`: XIAO ESP32-S3 Sense — PN532 RFID, OLED, three buttons, camera; live photo at `http://<station IP>/`.
- `docs/wiring.md`: C6 DevKit body-unit table.
- Bench: Serial output on the C6 DevKit confirmed, HW-827 reading (~2.1 V at rest); I²C sensors and DS18B20 not yet answering — wiring being checked.

## v3.1 — AHT air temperature + humidity on repeaters
- `firmware/repeater_node`: AHT10/20/25 on I²C (XIAO C6 SDA D4 / SCL D5, ESP32-S3 GPIO8 / 9), own non-blocking driver, `AHT_ENABLED`; reading every 2 s; sent in the repeater status (`airT`, `airH` appended — V2 repeaters still decode) and as `air_t` / `air_h` in the hub JSON; phone test page shows it; Serial `a` command.
- `hub/admin_hub.py`: stores air temperature / humidity history per repeater, works out wet-bulb temperature (Stull formula); **Air** panel on each *Gas & air* card, **Air (AHT)** column + chain line on *Network*, top-bar chip; heat warnings (wet-bulb 30.5 / 33.5 °C, air 35 °C, humidity 90 %) logged in the *Incident log*.
- `tools/sim_repeater.py`: simulated repeaters send air readings (warmer deeper in the mine).
- Repeater schematic, `docs/wiring.md`, `docs/v3.md`, `docs/protocol.md` updated.

## V3 · v3.0 — Camera entry station, mock worker, schematics
Branch: [`version/v3.0`](https://github.com/Manas-36/MINESAFE/tree/version/v3.0) · flashing guide: [`docs/v3.md`](docs/v3.md)

Hardware set for the prototype demo (all ESP-NOW; Zigbee planned later — see decision 13):
body unit **ESP32-S3 N16R8** · repeaters **XIAO ESP32-C6** (main one on Wi-Fi to the hub) · **mock body unit** ESP32-C6 + MPU6050 · phone test worker · entry station **XIAO ESP32-S3 Sense**.
- `firmware/entry_station` v3: camera + **PHOTO button (D3)** — countdown, SVGA JPEG, `POST /api/camphoto` with the scanned tags; OLED shows the AI kit-check verdict. Hub auto-find on the hotspot subnet. Still builds for the XIAO C6 (no camera).
- `firmware/body_node`: `MOCK_MPU_ONLY` mode and flag `BF_NO_VITALS (256)` for a motion-only demo worker.
- `hub/admin_hub.py`: `/api/camphoto` (raw JPEG from the station → verification card + AI check); mock workers show no temperature / heart-rate warnings; deck-style dark/amber theme with MINESAFE opening screen.
- `docs/wiring/`: schematics for every unit (SVG + PNG) generated by `make_schematics.py`.
- `docs/research/`: literature review, competitor analysis, pilot design, original reports, real accident case list.

