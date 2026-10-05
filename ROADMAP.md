<div align="center">

# 🗺️ MineSafe Roadmap

**Week-by-week progress of the capstone — from research to final review**

![Progress](https://img.shields.io/badge/progress-71%25-F2A900?style=for-the-badge)
![Done](https://img.shields.io/badge/done-42-2ea44f?style=for-the-badge)
![In progress](https://img.shields.io/badge/in_progress-0-fb8c00?style=for-the-badge)
![To do](https://img.shields.io/badge/to_do-17-6e7781?style=for-the-badge)
![Week](https://img.shields.io/badge/now-week_9_of_14-1f6feb?style=for-the-badge)

`█████████████████████░░░░░░░░░`  **42 / 59 tasks**

</div>

> Week 1 = Mon 3 Aug 2026. Weeks 1–8 dates are approximate. The same list lives in Notion as a board + timeline (*MineSafe → Project Roadmap & To-Do*); keep both in sync when a task is finished.

---

## 📊 Week by week

| | Week | Dates | Focus | Version | Progress |
|:-:|:-:|---|---|:-:|---|
| ✅ | 01 | 3 Aug – 9 Aug | 📚 Research & problem definition | `v0.0` | `██████████` 3/3 |
| ✅ | 02 | 10 Aug – 16 Aug | 🔍 Competitive analysis & architecture | `v0.0` | `██████████` 4/4 |
| ✅ | 03 | 17 Aug – 23 Aug | 🏷️ Entry station v1 (RFID) | `v0.1` | `██████████` 3/3 |
| ✅ | 04 | 24 Aug – 30 Aug | 📷 Photo verification | `v0.2` | `██████████` 2/2 |
| ✅ | 05 | 31 Aug – 6 Sep | 🖥️ Control room v3 + simulator | `v0.3` | `██████████` 4/4 |
| ✅ | 06 | 7 Sep – 13 Sep | 📡 Zigbee → ESP-NOW, repeater chain, AI, gas | `v0.4` | `██████████` 4/4 |
| ✅ | 07 | 14 Sep – 20 Sep | 🔗 Multi-hop chain + alert propagation | `v0.4` | `██████████` 3/3 |
| ✅ | 08 | 21 Sep – 27 Sep | 🎯 First end-to-end run | `v0.5` | `██████████` 4/4 |
| ✅ | **09** ◀ now | 28 Sep – 4 Oct | 🗺️ Map tracking, gas analysis, real sensors, docs | `v0.6 / v1.0` | `██████████` 13/13 |
| 🔄 | 10 | 5 Oct – 11 Oct | 🧪 V3: camera entry station, mock worker, bench test | `v3.0` | `███░░░░░░░` 2/6 |
| ⏳ | 11 | 12 Oct – 18 Oct | 🤖 AI kit dataset + entry flow + kit-removal | `v3.1` | `░░░░░░░░░░` 0/3 |
| ⏳ | 12 | 19 Oct – 25 Oct | 🔋 Power, enclosure, range test | `v3.2` | `░░░░░░░░░░` 0/3 |
| ⏳ | 13 | 26 Oct – 1 Nov | 🎬 Full system trial + demo video | `v3.3` | `░░░░░░░░░░` 0/3 |
| ⏳ | 14 | 2 Nov – 8 Nov | 🏁 Report, final review, release | `v4.0` | `░░░░░░░░░░` 0/4 |

## 🗓️ Timeline

```mermaid
gantt
    title MineSafe capstone, 2026
    dateFormat YYYY-MM-DD
    axisFormat %d %b
    todayMarker stroke-width:3px,stroke:#F2A900
    section Research
    W01 Research and problem definition :done, w1, 2026-08-03, 7d
    W02 Competitive analysis and architecture :done, w2, 2026-08-10, 7d
    section Entry station & control room
    W03 Entry station v1 RFID :done, w3, 2026-08-17, 7d
    W04 Photo verification :done, w4, 2026-08-24, 7d
    W05 Control room v3 and simulator :done, w5, 2026-08-31, 7d
    section Radio network & gas
    W06 Zigbee to ESP-NOW repeater chain AI gas :done, w6, 2026-09-07, 7d
    W07 Multi-hop chain and alert propagation :done, w7, 2026-09-14, 7d
    W08 First end-to-end run :done, w8, 2026-09-21, 7d
    section Body unit, map & docs
    W09 Map tracking gas analysis real sensors docs :done, w9, 2026-09-28, 7d
    section Testing & hardware
    W10 V3  camera entry station mock worker bench test : w10, 2026-10-05, 7d
    W11 AI kit dataset and entry flow and kit-removal : w11, 2026-10-12, 7d
    W12 Power enclosure range test : w12, 2026-10-19, 7d
    section Final
    W13 Full system trial and demo video : w13, 2026-10-26, 7d
    W14 Report final review release : w14, 2026-11-02, 7d
```

## ✅ Tasks

<details>
<summary>📚 <b>Week 01</b> · 3 Aug – 9 Aug · Research & problem definition · <code>v0.0</code> · 3/3</summary>

- [x] Finalise problem statement and project title — <sub>Research</sub>
- [x] Literature review: ILO, DGMS, MSHA accident data and papers — <sub>Research</sub>
- [x] List required functions: kit check, health, location, gas, alerts — <sub>Research</sub>

</details>

<details>
<summary>🔍 <b>Week 02</b> · 10 Aug – 16 Aug · Competitive analysis & architecture · <code>v0.0</code> · 4/4</summary>

- [x] Competitive analysis of 9 commercial products — <sub>Research</sub>
- [x] Patent search and gap identification — <sub>Research</sub>
- [x] 7-layer system architecture — <sub>Research</sub>
- [x] Pilot BOM for 20 workers (Total_System_BOM.xlsx) — <sub>Hardware</sub>

</details>

<details>
<summary>🏷️ <b>Week 03</b> · 17 Aug – 23 Aug · Entry station v1 (RFID) · <code>v0.1</code> · 3/3</summary>

- [x] I2C scanner and PN532 NTAG215 read/write test — <sub>Entry station</sub>
- [x] Entry station v1: PN532 + OLED gear tag reader — <sub>Entry station</sub>
- [x] Hub v1: UID tag registry (admin_hub_test) — <sub>Control room</sub>

</details>

<details>
<summary>📷 <b>Week 04</b> · 24 Aug – 30 Aug · Photo verification · <code>v0.2</code> · 2/2</summary>

- [x] Hub v2: phone camera photo verification — <sub>Control room</sub>
- [x] Body-unit clearance after kit check — <sub>Control room</sub>

</details>

<details>
<summary>🖥️ <b>Week 05</b> · 31 Aug – 6 Sep · Control room v3 + simulator · <code>v0.3</code> · 4/4</summary>

- [x] Control room v3: worker registry + medical card — <sub>Control room</sub>
- [x] Live monitoring dashboard and one-click alert — <sub>Control room</sub>
- [x] Entry station v2 sends scans to hub over Wi-Fi — <sub>Entry station</sub>
- [x] Repeater simulator (sim_repeater.py) and RC522 test — <sub>Testing</sub>

</details>

<details>
<summary>📡 <b>Week 06</b> · 7 Sep – 13 Sep · Zigbee → ESP-NOW, repeater chain, AI, gas · <code>v0.4</code> · 4/4</summary>

- [x] Try Zigbee on ESP32-S3 → fails (no 802.15.4), switch to ESP-NOW — <sub>Network</sub>
- [x] Self-forming repeater chain (beacons, hop count, channel search) — <sub>Network</sub>
- [x] AI kit check with YOLOv8 (helmet, vest, shoes) — <sub>Control room</sub>
- [x] MQ gas sensor on each repeater + gas alert — <sub>Gas</sub>

</details>

<details>
<summary>🔗 <b>Week 07</b> · 14 Sep – 20 Sep · Multi-hop chain + alert propagation · <code>v0.4</code> · 3/3</summary>

- [x] Multi-hop forwarding with duplicate filter — <sub>Network</sub>
- [x] Alert travels down the chain in beacons; repeater buzzer — <sub>Network</sub>
- [x] Phone test page on repeater (phone acts as worker) — <sub>Testing</sub>

</details>

<details>
<summary>🎯 <b>Week 08</b> · 21 Sep – 27 Sep · First end-to-end run · <code>v0.5</code> · 4/4</summary>

- [x] End-to-end: phone worker → repeaters → admin hub — <sub>Testing</sub>
- [x] Fix silent buzzer (active-low / passive options) — <sub>Network</sub>
- [x] Hub auto-find when laptop IP changes — <sub>Network</sub>
- [x] Body unit v1: button + LED over ESP-NOW — <sub>Body unit</sub>

</details>

<details open>
<summary>🗺️ <b>Week 09</b> · 28 Sep – 4 Oct · Map tracking, gas analysis, real sensors, docs · <code>v0.6 / v1.0</code> · 13/13 · <b>◀ now</b></summary>

- [x] Tunnel map + GPS-free tracking (steps, heading, repeater check-points) — <sub>Location & map</sub>
- [x] Direction-aware map snapping + demo walker — <sub>Location & map</sub>
- [x] Gas & air tab: all gases in ppm per sensor, auto calibration — <sub>Gas</sub>
- [x] Body unit v2 code: MPU6050, BMP180, DS18B20, MAX3010x drivers — <sub>Body unit</sub>
- [x] Heart rate / SpO2 limits and alerts on hub — <sub>Body unit</sub>
- [x] 12–15 min presentation (22 slides) — <sub>Docs & review</sub>
- [x] Notion wiki, BOM and test log — <sub>Docs & review</sub>
- [x] Structured GitHub repo with version history v0.0 → v1.0 — <sub>Docs & review</sub>
- [x] Add guide name and branch to deck, Notion and GitHub — <sub>Docs & review</sub>
- [x] Wiring schematics for every unit (SVG + PNG) — <sub>Hardware</sub>
- [x] Admin themed like the deck + MINESAFE opening screen — <sub>Control room</sub>
- [x] Add DGMS accident statistic to the deck — <sub>Docs & review</sub>
- [x] Attach literature review document to References — <sub>Docs & review</sub>

</details>

<details open>
<summary>🧪 <b>Week 10</b> · 5 Oct – 11 Oct · V3: camera entry station, mock worker, bench test · <code>v3.0</code> · 2/6</summary>

- [x] Entry station v3: XIAO S3 Sense camera + PHOTO button + /api/camphoto — <sub>Entry station</sub>
- [x] Mock worker: ESP32-C6 + MPU6050 (MOCK_MPU_ONLY) — <sub>Body unit</sub>
- [ ] Flash body unit v2 and bench-test every sensor — <sub>Body unit</sub> 🔴
- [ ] Calibrate step length and heading on a measured corridor — <sub>Location & map</sub> 🔴
- [ ] Validate fall / no-movement detection with test drops — <sub>Body unit</sub> 🔴
- [ ] Choose antenna placement (body XIAO u.FL) and log range — <sub>Hardware</sub>

</details>

<details>
<summary>🤖 <b>Week 11</b> · 12 Oct – 18 Oct · AI kit dataset + entry flow + kit-removal · <code>v3.1</code> · 0/3</summary>

- [ ] Collect reference photos and test AI kit check accuracy — <sub>Control room</sub> 🔴
- [ ] Full entry flow: RFID scan + photo + approve + pair body unit — <sub>Entry station</sub> 🔴
- [ ] Kit-removal sensing prototype (helmet IR, vest reed switch) — <sub>Body unit</sub>

</details>

<details>
<summary>🔋 <b>Week 12</b> · 19 Oct – 25 Oct · Power, enclosure, range test · <code>v3.2</code> · 0/3</summary>

- [ ] Battery + charger for body unit, measure battery life — <sub>Hardware</sub> 🔴
- [ ] Enclosures for body unit and repeaters (3D print) — <sub>Hardware</sub>
- [ ] Repeater range test along a long corridor — <sub>Network</sub>

</details>

<details>
<summary>🎬 <b>Week 13</b> · 26 Oct – 1 Nov · Full system trial + demo video · <code>v3.3</code> · 0/3</summary>

- [ ] Full trial: 3 repeaters, body unit, phone workers, gas test — <sub>Testing</sub> 🔴
- [ ] Record demo video, add photos to GitHub and Notion — <sub>Docs & review</sub>
- [ ] Fill Test Log with results — <sub>Testing</sub>

</details>

<details>
<summary>🏁 <b>Week 14</b> · 2 Nov – 8 Nov · Report, final review, release · <code>v4.0</code> · 0/4</summary>

- [ ] Write project report — <sub>Docs & review</sub> 🔴
- [ ] Final presentation rehearsal and viva questions — <sub>Docs & review</sub> 🔴
- [ ] Release v4.0 (final) on GitHub — <sub>Docs & review</sub>
- [ ] Plan Zigbee (802.15.4) migration on ESP32-C6 nodes — <sub>Network</sub>

</details>

🔴 = high priority, still open

## 🧩 By subsystem

| Subsystem | Done | Open | Progress |
|---|:-:|:-:|---|
| Research | 6 | 0 | `██████████` 100 % |
| Hardware | 2 | 3 | `████░░░░░░` 40 % |
| Entry station | 4 | 1 | `████████░░` 80 % |
| Control room | 7 | 1 | `█████████░` 88 % |
| Testing | 3 | 2 | `██████░░░░` 60 % |
| Network | 6 | 2 | `████████░░` 75 % |
| Gas | 2 | 0 | `██████████` 100 % |
| Body unit | 4 | 3 | `██████░░░░` 57 % |
| Location & map | 2 | 1 | `███████░░░` 67 % |
| Docs & review | 6 | 4 | `██████░░░░` 60 % |

## 🏷️ Versions

Each finished stage is a `version/*` branch — see [CHANGELOG.md](CHANGELOG.md).

```mermaid
timeline
    title MineSafe versions
    Aug : v0.0 Research and architecture : v0.1 Entry station v1 : v0.2 Photo verification
    Early Sep : v0.3 Control room v3 : v0.4 ESP-NOW repeater chain, AI, gas
    Late Sep : v0.5 First end-to-end run
    Oct wk 1 : v0.6 Map tracking, gas analysis, real sensors : v1.0 Repo, docs, slides, Notion
    Oct wk 2 : V3 (v3.0) Camera entry station, mock worker, schematics
    Oct wk 2–3 : v3.1 AHT air sensing : v3.2 Sensor integration and calibration (now)
    Nov onward : V4 Own PCBs and sensor boards
```

<div align="center"><sub>Manas Pednekar · Amey Satale · Aaryaa Kanojia · Guide: Mr Dipesh Tare, Assistant Professor<br>Mechanical and Mechatronics Engineering · TCET Mumbai · 2026–27</sub></div>
