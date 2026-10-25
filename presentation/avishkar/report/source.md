# MineSafe — Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Miners

Oct 25, 2026 · @Manas

## 1. Project at a glance

MineSafe is a low-cost system that checks a miner's safety kit at the gate, monitors health and movement underground, shows each worker's position on a tunnel map, and lets the control room alert everyone in seconds. It works **without GPS, mobile network, internet or new cabling**.

| Item | Detail |
| --- | --- |
| Title | MineSafe — Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Miners |
| Category | Engineering and Technology (UG) |
| Team | Manas Pednekar (Roll 36), Amey Satale (Roll 46), Aaryaa Kanojia (Roll 18) |
| Guide | Mr Dipesh Tare |
| Department / Institute | B.E. Mechanical and Mechatronics Engineering (Additive Manufacturing), Thakur College of Engineering and Technology (TCET), Mumbai |
| Academic year | 2026–27 |
| Stage | V3 working prototype in calibration; V4 (own PCBs, mine-rated enclosures, smart suit) designed |
| Code and designs | [github.com/Manas-36/MINESAFE](https://github.com/Manas-36/MINESAFE) |

**Abstract.** Underground mines have no GPS and no mobile signal, so the control room cannot see where a worker is or what condition they are in. Kit checks at the gate are manual, and gas build-up, falls and heat stress are usually found after the fact. MineSafe joins four parts into one system:

- **Entry station:** RFID tags plus an AI (YOLOv8) photo check confirm the full kit before a worker enters.
- **Wearable:** tracks heart rate, SpO₂, body temperature, falls, inactivity and steps.
- **Repeater chain:** ESP32-C6 nodes along the tunnel relay data hop by hop over ESP-NOW. Each node also measures gas, temperature and humidity and shows an LED exit sign.
- **Control room:** a laptop hub with a 3D mine map that raises alerts and plans evacuation routes.

Position comes from pedestrian dead reckoning, corrected at every repeater. The V4 design moves the electronics onto five custom PCBs and replaces the tagged kit with a smart suit that checks itself through the whole shift.

**Key numbers**

| Measure | Value |
| --- | --- |
| Radio | ESP-NOW, 2.4 GHz; repeater hop chain that forms and heals by itself |
| Status update rate | 1 packet per second per worker; alerts pushed back down the chain |
| Sensing per worker | Heart rate, SpO₂, body / skin temperature, fall, no-movement, steps, heading, level (pressure) |
| Sensing per repeater | CH₄, CO, H₂S (MQ-4 / MQ-7 / MQ-136), air temperature, humidity, wet-bulb |
| Custom PCBs designed | 5 (repeater, core pod, wrist cuff, helmet pod, boot pod) — all routed, 0 unconnected pads |
| Cost per repeater (PCB + mine case) | ≈ ₹6,900 |
| Cost of one smart suit (V4) | ≈ ₹12,800 (≈ ₹10,800 without the certified helmet and boots) |
| Prototype set (1 body unit, 3 repeaters, entry station) | ≈ ₹10,800 |

## 2. Problem statement

Indian coal mines alone recorded **141 deaths in 2023–2025** (41, 49 and 51 a year), with 355 serious accidents in the same period ([Ministry of Mines data via ETV Bharat, Aug 2026](https://www.etvbharat.com/en/bharat/141-die-in-coal-mine-accidents-in-two-years-government-enn26081305600)). The main causes listed are falls from height, landslides and fall of roof, failure of ropes and haulage gear, dumper and drilling-machine accidents, and explosions.

Recent rescues show the same gap again and again: **nobody knows exactly who is underground, where they are, or whether they are alive.**

| Incident | What happened | What was missing |
| --- | --- | --- |
| [SLBC tunnel, Telangana, Feb 2025](https://www.deccanherald.com/amp/story/india%2Ftelangana%2Ftelangana-tunnel-collapse-whereabouts-of-four-trapped-persons-located-says-state-minister-krishna-rao-3427625) | 8 trapped; ground radar needed to find them | Last known position without GPS |
| [Umrangso, Assam, Jan 2025](https://www.newsonair.gov.in/rescue-operations-continue-at-assams-umrangso-mine-3-bodies-recovered-after-150-hours) | Flooded mine, at least 9 trapped, 150+ h search | Entry log and position at the surface |
| [Kolihan, Rajasthan, May 2024](https://www.deccanherald.com/india/rajasthan/all-15-hindustan-copper-limited-officials-rescued-from-collapsed-lift-at-rajasthans-kolihan-mine-3023138) | Cage rope snapped, 15 trapped overnight, 1 died | Fall alarm, vitals and location |
| [Ksan, Meghalaya, Dec 2018](https://en.wikipedia.org/wiki/2018_Meghalaya_mining_accident) | 15 trapped by flooding, about 80-day search | Position relayed to the surface |

**Why it happens — the gaps in current practice**

1. **No GPS and no mobile network underground.** Phones and GPS trackers stop working at the portal, so the control room is blind once a shift starts.
2. **Manual kit checks.** Helmets, vests and boots are checked by eye at the gate, and a worker can remove kit once inside without anyone knowing.
3. **Health is not monitored.** Heat stress, exhaustion, a fall or loss of consciousness is found only when someone is missed.
4. **Gas is measured at a few points.** Hand-held detectors and fixed stations cover only part of the tunnel, and alarms are local.
5. **Evacuation is by shouting and sirens.** There is no way to tell each worker which way to go.
6. **Commercial systems are expensive and fragmented.** Our survey of nine products (section 4) found none that combines kit compliance, vitals and GPS-free location, and all are sold only on enterprise quotes. That puts them out of reach of India's many smaller mines.

**Who is affected:** underground workers in coal and metal mines and tunnelling projects, shift supervisors and control-room operators, and the rescue teams who need a last known position.

## 3. Aim, objectives and scope

**Aim:** build an affordable, integrated system that keeps every underground worker checked, monitored, located and reachable for the whole shift, using only hardware a small mine can install itself.

**Objectives**

1. **Kit compliance:** verify helmet, vest, trousers and boots at entry, using RFID tags plus a YOLOv8 photo check, before a worker is cleared.
2. **Health monitoring:** measure heart rate, SpO₂ and body temperature, and detect falls and no-movement, on the worker.
3. **GPS-free location:** estimate each worker's position from steps and heading, and correct it at every repeater, so the map is right to within the repeater spacing.
4. **Self-healing network:** relay data and alerts hop by hop through a repeater chain, with no cabling or internet.
5. **Environment sensing:** measure CH₄, CO, H₂S, air temperature, humidity and wet-bulb temperature at every repeater, against Indian mine limits.
6. **Control room:** one live dashboard and 3D mine map, with one-click alert, automatic gas alarms and evacuation routes shown on each repeater's LED exit sign.
7. **Productisation (V4):** move to custom PCBs and mine-rated enclosures, and replace tagged kit with a smart suit that reports tears, removal and kit state all shift.
8. **Cost target:** under ₹7,000 per repeater and about ₹12,800 per smart suit.

**In scope:** underground coal and metal mines and tunnels; a single control room; demonstration on a bench and in a corridor test track.

**Out of scope for the capstone:** intrinsic-safety certification (Ex ia / Ex d) for gassy coal mines, medical-grade accuracy of vitals, and a long-range LoRa backbone. The LoRa backbone is planned (section 17).

## 4. Existing solutions and novelty

Each part of MineSafe has been shown to work in the literature. What no existing product or paper does is **combine kit compliance, continuous vitals and GPS-free location in one low-cost underground system**.

**Literature survey (summary)**

| Theme | What earlier work shows | What we take from it |
| --- | --- | --- |
| Smart mining helmets (IEEE 2023–24, IJRASET 2024, arXiv 2023) | Gas, temperature and fall sensing on a helmet, with Wi-Fi, GSM or LoRa links | Sensor choice; the need for an underground link that does not depend on GSM |
| AI PPE detection (YOLOv7 / YOLOv8 papers, MDPI 2023, PeerJ 2022) | YOLO models detect helmets and vests in real time with high accuracy on construction sites | YOLOv8 photo check at the entry station |
| Low-cost wearable vitals (MDPI 2024–25 reviews) | Optical HR / SpO₂ sensors are usable for trends but less accurate in motion | Use for alerts on trends, not diagnosis; wrist placement in V4 |
| Underground positioning (UWB + IMU, MDPI Micromachines 2023; Mining, Metallurgy & Exploration 2024) | UWB gives sub-metre accuracy; IMU dead reckoning drifts unless it is corrected | Dead reckoning corrected at each repeater now; foot-mounted IMU in V4; UWB as a pilot option |
| Mine wireless networks (CSIR-CIMFR, J. Sci. Ind. Research 2009) | ZigBee mesh with routers every 50–80 m carried safety data in Indian mines | Hop-chain repeaters; spacing to be fixed by our own range test |

**Commercial products** (nine checked against vendor websites, July 2026)

| Product | Kit / PPE check | Continuous vitals | Fall alert | GPS-free location | Gas |
| --- | --- | --- | --- | --- | --- |
| Teknovate MineGuard 360 | No | Yes | Partial | Partial | Yes |
| MineARC GuardIAN | No | No | Partial | Zone only | Yes |
| Leantegra Safe Mining | No | No | No | Yes (UWB) | Yes |
| Rajant Health | Tag presence | Yes | Yes | Mesh proximity | Partial |
| EasyM2M SmartKavach | No | Partial | Yes | No (GPS / cellular) | No |
| 36Zero + Bodytrak | Image alerts | Yes | Yes | No | No |
| HaloTag, ANTAR IoT, Jarsh Safety | No | Partial or no | Partial or no | Proximity or no | Partial or no |
| **MineSafe** | **RFID + YOLOv8 (V4: self-checking suit)** | **Yes** | **Yes** | **Dead reckoning + repeater fixes** | **Yes, at every repeater** |

**What is novel in MineSafe**

- **One integrated system:** entry compliance, wearable vitals, location, gas and evacuation all run on one network and one dashboard.
- **Location that works without GPS or new infrastructure:** step-based dead reckoning, snapped to the tunnel map and reset at each repeater.
- **Repeaters that double as exit signs:** each node shows the evacuation direction and distance on an LED matrix, computed by the hub around the danger zone.
- **Continuous kit compliance (V4):** the suit detects helmet off, boots off, zip opened or fabric torn during the shift, not just at the gate. It is detected and reported, never locked.
- **Cost:** about ₹6,900 per repeater and ₹12,800 per suit, against enterprise-only pricing for every product above.

## 5. System architecture

Four subsystems share one network: the entry station, the worker's wearable, the repeater chain and the control-room hub. Data rises hop by hop to the hub once a second; alerts and evacuation routes ride back down the same chain.

&#91;embedded content: MineSafe system architecture · V4\]

The helmet and boot pods talk to the core pod over ESP-NOW with a key unique to each suit; only the wrist cuff is wired. The core sends one packet a second to whichever repeater hears it. The main repeater (hop 0) links to the hub over Wi-Fi.

&#91;image: Figure 5.1 – System overview as built in V3\]

*Figure 5.1 – V3 system overview: body unit, repeaters, entry station and hub.*

### 5.1 Data flow

| Data | From → to | Rate |
| --- | --- | --- |
| Worker telemetry (vitals, steps, heading, fall, kit state, battery) | core pod → nearest repeater → chain → hub | 1 packet / s |
| Repeater status (gas, air, neighbours, signal) | repeater → chain → hub | every 5 s, at once on a gas or temperature step |
| Beacons with alerts and guidance | hub → main repeater → chain → workers | every 1 s |
| Entry record (tags / ID, photo, AI verdict) | entry station / phone → hub | per worker at the gate |
| Live state for the dashboards | hub → 3D app / admin page | polled every 1 s |

### 5.2 Development versions

| Version | What it added | Network |
| --- | --- | --- |
| V1 | Body ESP only; repeaters on Wi-Fi; cloud storage | Wi-Fi + internet |
| V2 | ESP-NOW chain, entry station, AI kit check, tunnel map, gas | ESP-NOW → Wi-Fi to laptop |
| V3 (now) | Camera entry station, XIAO C6 repeaters with air sensing, exit-sign repeaters, evacuation routes, 3D control app; sensor calibration in progress | ESP-NOW |
| V4 (designed) | Smart suit (core, helmet, cuff, boot pods), five custom PCBs, mine-rated repeater case | ESP-NOW + planned LoRa backbone |

## 6. Design considerations

Every hardware decision starts from the conditions inside an underground mine. Each condition below has a design answer.

| Mine condition | Typical value | Design answer |
| --- | --- | --- |
| Water: roof drips, wet walls, humidity | up to 100 % RH | Gasketed IP65 repeater case with a drip hood. Glands, vents and the CO / H₂S ports face down. ePTFE pressure vent. PCB conformal-coated after test |
| Dust (coal, rock) | heavy, conductive | Same seal; sensors breathe only through sintered-bronze discs and ePTFE membranes |
| Methane (lighter than air) | collects at the roof; explosive 5–15 % | CH₄ sensor port on the **top** wall under a rain chimney. Alarm at 0.75 % / 1.25 % (Coal Mines Regulations 2017, reg. 153) |
| H₂S (heavier than air), CO | collect low / spread | Ports on the **bottom** wall with impact skirts |
| Ignition risk | hot MQ heaters, sparks | Flame-arrestor disc seat at every sensor port. Full intrinsic-safety certification is noted as product work |
| Heat | 30–45 °C air; wet-bulb limit 30.5 / 33.5 °C | AHT20 in a separate walled chamber away from the MQ heaters. Switching regulator instead of a hot linear 7805 |
| Blasting shock and vibration | repeated impact | Boards on screw bosses, latching JST connectors, gussets on lugs, rubber grommets in the mounting holes |
| Falling rock, machines | impact | 3.5–4 mm PC-ABS FR walls, 3 mm polycarbonate window behind a bezel, guarded SOS button |
| Mine power cuts | frequent | Diode-OR of 9–30 V mine supply and a 12 V battery: switch-over with no reset. “Mains present” signal to the firmware |
| No GPS, no mobile signal | — | ESP-NOW hop chain + dead reckoning with repeater fixes |
| RF in rock tunnels | 2.4 GHz attenuates fast, bends badly | Repeaters at line-of-sight spacing (to be fixed by range test). External antenna on an SMA bulkhead; helmet-height antenna in V4 |
| Darkness and smoke | cap-lamp only | LED-matrix exit signs, reflective hi-vis tape on every enclosure |
| Gloves and dirt | thick gloves | 16–22 mm buttons, ribs between buttons, vibration and voice alerts |
| Worker comfort and heat stress | 8–12 h shifts | Breathable FR coverall, not a sealed suit; pods removable for washing |
| Worker safety in an emergency | — | **The suit is never locked.** Opening or tearing is detected and reported, never prevented |
| Static electricity | dry air near fans | Antistatic FR plastic, earth stud in the repeater case |
| Cost and maintenance | small mines | Off-the-shelf modules on sockets, through-hole PCBs, hand-solderable, 3D-printable cases |

The gas limits used by the system follow Indian regulations where they exist. They are set out in section 16.

## 7. Mechanical design

All enclosures were modelled parametrically in **CadQuery** (Python CAD). Every one was checked by an automatic fit test against the real PCB, which is built in 3D from the KiCad file, plus its batteries, modules, buttons and connectors. All passed with no collisions. STEP and STL files are in the repository.

### 7.1 Repeater enclosure (wall / rib mounted)

&#91;image: Figure 7.1 – Repeater case: drip hood over the exit-sign window, guarded SOS button, siren grille, hi-vis tape, CH4 chimney and antenna on top\]

*Figure 7.1 – Repeater case, closed.*

&#91;image: Figure 7.2 – Inside the repeater: PCB on four standoffs, LED matrix behind the window, CH4 sensor top, CO and H2S bottom, sealed AHT20 chamber, 3S battery bay\]

*Figure 7.2 – Exploded view showing the internal layout.*

&#91;image: Figure 7.3 – Bottom face: M16 power gland, M12 pressure vent, CO and H2S ports with impact skirts\]

*Figure 7.3 – Everything that must not collect water faces down.*

| Feature (see Figures 7.1–7.3) | Specification |
| --- | --- |
| 1. Outer size | 223 × 292 × 118 mm with tabs and hood; body 198 × 228 × 84 mm |
| 2. Seal | 3 mm silicone cord in a groove on a 9 mm land, tongue on the lid; 6 × M4 stainless screws into heat-set inserts (target IP65) |
| 3. Drip hood | full-width sloped roof over the window |
| 4. Exit-sign window | 136 × 40 mm opening, 3 mm polycarbonate in a recess behind a raised bezel |
| 5. CH₄ port | top wall, 20 mm opening under a chimney with side windows; seat for 25 × 3 mm sintered-bronze flame arrestor + ePTFE membrane |
| 6. CO / H₂S ports | bottom wall, same seats, impact skirts |
| 7. AHT20 chamber | separate walled corner with its own side vent under a drip lip |
| 8. Battery bay | 3S 18650 pack + BMS + charge module, ribs and strap slots |
| 9. Openings | M16 gland (power), M12 vent, 22 mm SOS (guarded), buzzer grille, SMA antenna bulkhead |
| 10. Mounting | top and bottom tabs: 16 mm hole for a rock bolt / roof-mesh hook / chain (rubber grommet) + slots |
| Mass and material | ≈ 1.1 kg in PC-ABS FR (antistatic, V-0); PETG / ASA for the prototype print |

### 7.2 V4 smart suit and pods

&#91;image: Figure 7.4 – V4 smart suit, front view with labels\]

*Figure 7.4 – Core pod on the chest, wrist cuff on the left forearm, tear-detection thread in the seams, reed switch on the zip.*

&#91;image: Figure 7.5 – V4 smart suit, back view with labels\]

*Figure 7.5 – Helmet pod (antenna, speaker) and boot pod (foot IMU) on the right heel.*

&#91;image: Figure 7.6 – X-ray view: sleeve cable and hidden sensors\]

*Figure 7.6 – Only the cuff is wired; the helmet and boot pods use ESP-NOW. Lining sensors connect by snaps.*

| Pod | Outer size | Mounting | Key mechanical features |
| --- | --- | --- | --- |
| Core (chest) | 118 × 93 × 44 mm | chest harness loops / pocket | board hangs under the lid, battery tray beneath, guarded 22 mm SOS, GX12 to the cuff, pogo charge socket, 6 snap studs |
| Wrist cuff | 88 × 75 × 27 mm | 4 × 25 mm strap loops | base curved to the forearm (R 40), OLED window with bezel, three 16 mm glove buttons with ribs, 12 mm skin window for the pulse sensor |
| Helmet pod | 75 × 66 × 31 mm | VHB foam + strap lugs | spherical back (R 115), speaker grille, FPC antenna in the lid |
| Boot pod | 57 × 58 × 29 mm | 20 mm ankle strap | back curved to the heel (R 45), FSR cable exit |

&#91;image: Figure 7.7 – Core pod exploded\]

*Figure 7.7 – Core pod: PCB under the lid, 3000 mAh LiPo, charger / buck-boost / gauge bay, GX12, pogo socket.*

&#91;image: Figure 7.8 – Wrist cuff exploded\]

*Figure 7.8 – Wrist cuff: OLED under the window, buttons, motor, sensor window in the base.*

&#91;image: Figure 7.9 – Helmet pod exploded\]

*Figure 7.9 – Helmet pod.*

&#91;image: Figure 7.10 – Boot pod exploded\]

*Figure 7.10 – Boot pod.*

## 8. Electrical design

Every node uses an Espressif ESP32 (C6 or S3) with its built-in 2.4 GHz radio. The C6 also supports Zigbee and Thread. Sensors connect on one shared I²C bus plus a few analog and digital pins. The pin maps below are taken directly from the firmware and PCB netlists.

### 8.1 V3 prototype schematics (built and running)

&#91;image: Figure 8.1 – Body unit wiring schematic\]

*Figure 8.1 – Body unit: MPU6050 (motion), BMP180 (pressure), DS18B20 (body temperature), MAX30102 / pulse sensor, SOS button, LED, OLED and vibration motor.*

&#91;image: Figure 8.2 – Repeater node v3.3 wiring schematic\]

*Figure 8.2 – Repeater: XIAO ESP32-C6, MAX7219 8×32 LED matrix, three MQ channels with dividers, AHT20, buzzer, SOS.*

&#91;image: Figure 8.3 – Entry station wiring schematic\]

*Figure 8.3 – Entry station: PN532 RFID reader, OLED, READ / WRITE / PHOTO buttons; photo from a camera or phone.*

### 8.2 V4 repeater PCB schematic

&#91;image: Figure 8.4 – Repeater PCB v4.0 schematic\]

*Figure 8.4 – Power path, controller, 3.3 V → 5 V matrix interface, three gas inputs, outputs.*

**Power path.** The mine supply (9–30 V, J1) and a 12 V battery (J2) are joined through two 1N5822 Schottky diodes. Whichever is higher feeds the board, so a power cut switches to battery with no reset. After that come a T1.6 A slow fuse, a P6KE36A TVS diode and 470 µF bulk capacitance, then a K7805-2000R3 switching regulator (5 V / 2 A, ≈ 90 % efficient). A linear 7805 would dissipate (24 − 5) V × 0.6 A ≈ 11 W at a 24 V supply.

**Mains-present detector.** VIN\_MAIN → 22 kΩ → S8050 base (10 kΩ to ground). When the mine supply is on, the collector pulls MAINS\_N low on D7, so the firmware can report “running on battery”.

**Gas inputs.** MQ modules output 0–5 V; the ESP32 ADC accepts 0–3.3 V. A 10 kΩ / 20 kΩ divider scales the signal, with a 100 nF filter:

```latex
V_{pin} = V_{AO} \cdot \frac{20\,k\Omega}{10\,k\Omega + 20\,k\Omega} = 0.667\,V_{AO} \qquad (5\,V \rightarrow 3.33\,V)
```

**Matrix interface.** The MAX7219 needs at least 3.5 V for a logic high at a 5 V supply. A 74HCT125 buffer lifts the 3.3 V signals (DIN, CS, CLK) to clean 5 V.

**Buzzer driver.** An S8050 NPN with a 1 kΩ base resistor and a 1N4148 flyback diode switches a 5 V, ≥ 85 dB buzzer.

| XIAO pin | Repeater function |  | XIAO pin | Repeater function |
| --- | --- | --- | --- | --- |
| D0 (GPIO0, ADC) | Gas 2 – MQ-7 CO |  | 5V | +5 V rail |
| D1 (GPIO1, ADC) | Gas 3 – MQ-136 H₂S |  | 3V3 | +3.3 V (AHT20, pull-ups) |
| D2 (GPIO2, ADC) | Gas 1 – MQ-4 CH₄ |  | D10 (GPIO18) | Buzzer |
| D3 (GPIO21) | Matrix CS |  | D9 (GPIO20) | Matrix DIN |
| D4 (GPIO22) | I²C SDA (AHT20) |  | D8 (GPIO19) | Matrix CLK |
| D5 (GPIO23) | I²C SCL (AHT20) |  | D7 (GPIO17) | MAINS\_N (supply present) |
| D6 (GPIO16) | SOS button (pull-up, 100 nF) |  |  |  |

&#91;image: Figure 8.5 – Repeater prototype wiring harness\]

*Figure 8.5 – Every cable from the repeater PCB to the parts in the case, pin by pin, with lengths and colours.*

### 8.3 V4 smart-suit electronics

&#91;image: Figure 8.6 – V4 suit architecture\]

*Figure 8.6 – Core, helmet, wrist and boot pods and their links.*

**Core pod power path.** 3.7 V 3000 mAh LiPo → TP4056 protected charger (1 A, from the magnetic pogo dock) → power switch → TPS63020 buck-boost (stable 3.3 V from a 3.0–4.2 V cell) → 3.3 V rail for the XIAO and all sensors. A MAX17048 fuel gauge reports battery % on I²C.

**Shared I²C bus** (no address clashes): MPU6050 0x68, BMP180 0x77, MAX17048 0x36, cuff OLED 0x3C, MAX30102 0x57.

**Glove buttons on one ADC pin.** Each cuff button pulls a 10 kΩ pull-up through a different resistor to ground:

```latex
V = 3.3\,V \cdot \frac{R_x}{10\,k\Omega + R_x}: \quad OK\ (2.2\,k\Omega) = 0.60\,V, \quad MENU\ (6.8\,k\Omega) = 1.34\,V, \quad SOS\ (0\,\Omega) = 0\,V
```

**Skin contact.** The ESP32-C6 has no capacitive-touch peripheral, so skin contact is measured by RC charge time on a normal GPIO (1 MΩ pull-up, 470 Ω series). Body contact adds capacitance and slows the rise.

**Suit sensing loop.** A stainless conductive thread runs through the seams and returns to the core on a pulled-up input. A tear or cut opens the loop and the pin goes high. A reed switch at the zip top reads low when the magnet in the puller is closed.

| Pod | XIAO pin map |
| --- | --- |
| Core | D0 cuff buttons (ADC) · D1 skin RC · D2 tear loop · D3 1-Wire DS18B20 · D4 SDA · D5 SCL · D6 SOS · D7 zip reed · D8 LED · D9 haptic (to cuff) · D10 IMU interrupt |
| Helmet | D0 battery sense (220 k / 220 k) · D1 helmet-worn switch · D2 LED · D7 amplifier shutdown · D8 I²S BCLK · D9 I²S LRC · D10 I²S DIN |
| Boot | D0 FSR (10 kΩ divider, ADC) · D1 battery sense · D2 LED · D3 IMU interrupt · D4 SDA · D5 SCL |
| Wrist cuff | no MCU: 6-core cable to the core (3.3 V, GND, SDA, SCL, BTN, HAPTIC); S8050 motor driver with 1N4148 + 100 nF |

&#91;image: Figure 8.7 – Suit pod wiring\]

*Figure 8.7 – Every connector on every pod board, pin by pin.*

## 9. PCB design

Five custom boards replace the breadboard wiring. All are 2-layer FR-4, 1.6 mm, through-hole only, so students can assemble and repair them by hand. Every board routes 100 % with **0 unconnected pads** in the KiCad design-rule check.

**Toolchain.** KiCad 7 (pcbnew Python API) and Freerouting 2.0.1, driven by our own generator script (`hardware/pcbgen.py`). The script:

1. places parts from the netlist and auto-packs the passives next to the pads they connect to;
2. exports to Freerouting and routes;
3. re-places and retries until routing is complete;
4. adds ground pours on both layers;
5. runs the design-rule check and writes Gerbers, drill files and renders.

A pin change is one line in the netlist and one command.

| Board | Size (mm) | Parts | Track segments / vias | Main contents |
| --- | --- | --- | --- | --- |
| Repeater | 100 × 75 | 46 | 312 / 8 | XIAO C6, diode-OR power, fuse, TVS, 5 V / 2 A switcher, 74HCT125, 3 gas inputs, buzzer driver, 9 connectors |
| Core pod | 66 × 54 | 34 | 312 / 25 | XIAO C6, GY-521, GY-68, pads for the charger / buck-boost / gauge, 12 connectors |
| Wrist cuff | 46 × 42 | 19 | 101 / 1 | OLED header, MAX30102 (underneath), button ladder, motor driver |
| Helmet pod | 44 × 48 | 18 | 112 / 0 | XIAO C6, MAX98357A amplifier, battery sense, pogo input |
| Boot pod | 34 × 42 | 18 | 109 / 2 | XIAO C6, BMI270, FSR divider, battery sense |

**Design rules**

| Rule | Value | Reason |
| --- | --- | --- |
| Layers / thickness | 2 / 1.6 mm FR-4, HASL | lowest-cost standard process |
| Signal track / clearance | 0.30 / 0.22–0.25 mm | well above the 0.127 mm fab minimum; easy to repair |
| Power track / clearance | 0.6–0.8 / 0.25–0.3 mm | ≈ 1.5–2 A for 1 oz copper at a 10 °C rise (MQ heaters, matrix, battery) |
| Via | 0.6 mm pad / 0.3 mm drill | standard |
| Copper to board edge | ≥ 0.3 mm | JLCPCB minimum for routed boards |
| Ground | pour on both layers, thermal reliefs, 0.35–0.4 mm clearance | low-noise ADC reference for the gas sensors, RF ground |
| Connectors | JST-XH (repeater) / JST-PH (pods), latching | survive vibration; cannot be plugged in backwards |
| Mounting | M3 (repeater) / M2 (pods) holes matched to the case bosses | fit-checked in CAD |

&#91;image: Figure 9.1 – Repeater PCB, top side\]

*Figure 9.1 – Repeater PCB v4.0: power terminals on the left, MQ inputs along the bottom, matrix / buzzer / SOS / AHT20 on the right, USB-C up.*

&#91;image: Figure 9.2 – Core pod PCB\]

*Figure 9.2 – Core pod board.*

&#91;image: Figure 9.3 – Wrist cuff PCB\]

*Figure 9.3 – Wrist cuff board.*

&#91;image: Figure 9.4 – Helmet pod PCB\]

*Figure 9.4 – Helmet pod board.*

&#91;image: Figure 9.5 – Boot pod PCB\]

*Figure 9.5 – Boot pod board.*

**Fabrication and assembly.** Upload each board's Gerber zip to JLCPCB or PCBWay with default settings (5 boards ≈ USD 2 plus shipping). Then:

1. Solder the low parts first, then the sockets and connectors.
2. Before fitting the XIAO, power the board and check the rails: 5.0 V on the repeater, 3.3 V on core J11 pin 3.
3. Conformal-coat after test.

The remaining design-rule notes are silkscreen overlaps and “library not configured” warnings only. There are no copper or clearance errors.

## 10. Component selection and trade-offs

Each part was chosen on five criteria: it does the job underground, it costs little, it can be bought in India, it has an open library, and it can be upgraded to a certified part in the product.

### 10.1 Selected components

| Function | Chosen part | Alternatives considered | Why this one |
| --- | --- | --- | --- |
| Controller (repeater, pods) | Seeed XIAO ESP32-C6 | ESP32-S3 DevKit, ESP32-C3, Arduino + radio | 21 × 17.5 mm; Wi-Fi 6, BLE, 802.15.4 (Zigbee / Thread) and ESP-NOW on one chip; u.FL antenna option; on-board LiPo charger; ≈ ₹600 |
| Radio protocol | ESP-NOW | Zigbee, LoRa, Wi-Fi mesh, BLE mesh | No pairing or joining delay, so a moving worker is heard by any repeater in range; runs on every ESP32; Zigbee adds no range at 2.4 GHz; LoRa kept as the long-tunnel backbone |
| Location | Step + heading dead reckoning (MPU6050; BMI270 foot IMU in V4) + repeater fixes | UWB (DWM3000) | UWB is ≈ ₹2,000 per worker and per anchor; dead reckoning with map-matching gives repeater-spacing accuracy at near-zero cost; UWB remains the pilot option |
| Motion / fall | MPU6050 (6-axis) → BMI270 | ADXL345, LSM6DS3 | In stock and well documented; BMI270 has lower power and a built-in step counter |
| Level / depth | BMP180 → BMP390 | BMP280 | Pressure gives the floor level (z) of the worker |
| Heart rate, SpO₂ | MAX30102 → MAX30101 | pulse sensor HW-827 | Two-wavelength optical sensor gives HR and SpO₂ on I²C; trend accuracy is enough for alerts |
| Body / skin temperature | DS18B20 probe → MAX30208 patch | MLX90614 IR | Contact probe is cheaper and steadier inside clothing |
| Gas (prototype) | MQ-4 (CH₄), MQ-7 (CO), MQ-136 (H₂S) | electrochemical / NDIR modules | ₹150–400 each, analog, prove the system; the hub accepts direct-reading digital sensors for the product (NDIR CH₄, electrochemical CO / H₂S / O₂) |
| Air temperature / humidity | AHT20 | DHT22, SHT40 | I²C, ±0.3 °C / ±2 % RH; wet-bulb is computed from it |
| Exit sign | MAX7219 8×32 LED matrix (FC-16) | OLED, e-paper | Bright in smoke and darkness; arrows and distances; ₹250–350 |
| Repeater 5 V supply | K7805-2000R3 switching module | LM7805 linear | 8–32 V in, ≈ 90 % efficient; a linear regulator would burn ≈ 11 W at 24 V |
| Logic level shift | 74HCT125 | resistor divider, BSS138 | Guaranteed 5 V logic levels for the MAX7219 |
| Pod 3.3 V supply | TPS63020 buck-boost | LDO (ME6211) | Keeps 3.3 V from 4.2 V down to 3.0 V, so the whole cell capacity is usable |
| Pod charging | TP4056 (core, 1 A); XIAO on-board charger (helmet, boot) | MCP73831 | Protected module; magnetic pogo dock |
| Battery % | MAX17048 | voltage divider only | Accurate state-of-charge sent to the hub and the cuff |
| Voice alerts | MAX98357A I²S amplifier + 28 mm 1 W speaker | buzzer only | Clear spoken directions such as “Evacuate — go left, 80 m” |
| Kit identity (V3) | NTAG215 NFC tags + PN532 | UHF RFID portal | A UHF fixed reader is ≈ ₹28,000; PN532 is a few hundred rupees |
| AI kit check | YOLOv8 on the hub laptop | Raspberry Pi edge AI | The laptop already runs the hub; no extra hardware |
| Connectors | JST-XH / JST-PH, GX12 panel, magnetic pogo | Dupont jumpers | Latching, keyed, vibration-proof; glove-friendly docking |
| Enclosure material | PC-ABS FR, antistatic (PETG / ASA for prototypes) | PLA | Flame-retardant V-0, antistatic; PLA softens at mine temperatures |

### 10.2 Why ESP-NOW and not Zigbee or LoRa

| Criterion | ESP-NOW (chosen) | Zigbee | LoRa |
| --- | --- | --- | --- |
| Frequency | 2.4 GHz | 2.4 GHz | 865–867 MHz (India) |
| Range per hop in a tunnel | short (line of sight) | short (same band) | long, bends round corners |
| Moving worker | heard by any repeater at once, no joining | must re-join the mesh | fine |
| Data rate | 1 Mbit/s, 250-byte packets | 250 kbit/s | 0.3–27 kbit/s |
| Extra hardware | none (built into every ESP32) | C6 / H2 only | SX1262 module + antenna (≈ ₹900 per repeater) |
| Role in MineSafe | worker ↔ repeater and repeater chain | not used | planned long-range repeater backbone |

## 11. Energy consumption and battery life

A repeater draws about **3.7 W** from the mine supply and runs about **7 h on its backup battery**. The core pod lasts about **21 h** on one charge, almost twice a 12 h shift. The helmet and boot pods reach a full shift only with a duty-cycled radio, so that is a firmware requirement for V4.

The currents are typical datasheet values at the operating points we use. They are design estimates to be confirmed by measurement (section 15, test T10).

### 11.1 Repeater (5 V rail)

| Load | Current at 5 V | Power |
| --- | --- | --- |
| XIAO ESP32-C6, radio always listening (ESP-NOW) | 90 mA | 0.45 W |
| 3 × MQ gas sensor heaters (≈ 150 mA each) | 450 mA | 2.25 W |
| MAX7219 8×32 matrix, arrow + distance at intensity 4/15 | 120 mA | 0.60 W |
| AHT20, 74HCT125, LED, pull-ups | < 5 mA | 0.03 W |
| **Total on the 5 V rail** | **≈ 665 mA** | **≈ 3.3 W** |
| Input power through the 90 % switching regulator | 0.31 A at 12 V | **≈ 3.7 W** |

The buzzer (30 mA) adds only during alarms. A full 3S 18650 pack (3 × 2600 mAh, 11.1 V) stores ≈ 28.9 Wh:

```latex
t_{backup} = \frac{28.9\,Wh \times 0.9\ (usable)}{3.7\,W} \approx 7\,h
```

On mine power a repeater uses ≈ 89 Wh a day. Ten repeaters use ≈ 0.9 kWh a day, about ₹7 a day at ₹8 per kWh.

### 11.2 Core pod (3.3 V rail, 3000 mAh LiPo)

| Load | Average current at 3.3 V |
| --- | --- |
| ESP32-C6, ESP-NOW listening + 1 packet/s | 80 mA |
| Cuff OLED 1.3" (about half the pixels lit) | 20 mA |
| MAX30102 (LEDs pulsed) | 6 mA |
| MPU6050 / BMI270 | 4 mA |
| BMP180, MAX17048, DS18B20, vibration motor (alerts only) | 2 mA |
| **Total** | **≈ 112 mA (0.37 W)** |

```latex
I_{bat} = \frac{0.37\,W}{0.9 \times 3.7\,V} \approx 111\,mA \qquad t = \frac{3000\,mAh \times 0.8}{111\,mA} \approx 21\,h
```

### 11.3 Helmet and boot pods

| Pod | Radio always on | Duty-cycled radio (V4 firmware) |
| --- | --- | --- |
| Helmet (600 mAh) | ≈ 84 mA → **≈ 5.7 h** (not enough for a shift) | listens 50 ms each second, sleeps the rest, speaker ≈ 1 % of the time: ≈ 8.5 mA → **≈ 56 h** |
| Boot (300 mAh) | ≈ 81 mA → **≈ 3 h** | BMI270 counts steps on its own, ESP32 wakes 20 ms a second to send: ≈ 2.6 mA → **≈ 92 h** |

Charging times from the dock: core ≈ 3.5 h at 1 A, helmet ≈ 7 h at 100 mA, boot ≈ 3.5 h. All three complete between shifts.

**Energy-saving measures in the design:**

- **No gas sensors on the body:** gas is measured on the repeaters, where mine power is available.
- **Switching and buck-boost regulators** instead of linear regulators.
- **Low matrix brightness,** with a bright flash only during evacuation.
- **Event-based reporting:** repeaters send at once only when gas or temperature changes past a step.
- **Duty-cycled radios** on the small pods.

## 12. Firmware, software and algorithms

The software stack has three parts:

- **Firmware:** Arduino C++ on the ESP32 nodes (body unit, repeater, entry station).
- **Hub:** a Python Flask hub on the control-room laptop, with the API, classic admin page, YOLOv8 kit check and evacuation planner.
- **3D control app:** React + three.js, served by the hub.

The hub's limits are all editable without reprogramming.

### 12.1 Network protocol

- **Beacons.** Each repeater broadcasts a beacon every 1 s with its hop count to the main repeater (hop 0). A repeater picks as parent the neighbour with the lowest hop count, so the chain forms by itself.
- **Forwarding.** Packets carry the sender hop, kind, body RSSI and the path so far (up to 8 hops). A repeater forwards only copies from a deeper hop and drops duplicates by hash.
- **Healing.** If no beacon is heard for 8 s, the repeater scans the channels, finds a new parent and rejoins.
- **Uplink.** The main repeater posts to the hub over Wi-Fi every 1 s. It finds the hub by itself if the laptop's address changes.
- **Downlink.** Alerts, evacuation guidance and target lists ride back down in the beacons, to everyone or to selected workers.

### 12.2 Location without GPS (pedestrian dead reckoning)

Double-integrating acceleration drifts by about 175 m in a minute, so MineSafe counts steps instead:

```latex
x_k = x_{k-1} + L \cos\theta_k, \qquad y_k = y_{k-1} + L \sin\theta_k, \qquad z = f(p_{BMP})
```

The terms are:

- L = step length (default 0.7 m, set per worker);
- θ = gyro heading;
- z = level from barometric pressure.

Two corrections keep the error bounded:

1. **Map matching.** Each position is snapped onto the nearest tunnel centre line drawn on the mine map.
2. **Repeater fixes.** When the body hears a repeater at ≥ −55 dBm, it is next to it, and the position resets to that repeater's surveyed point. The worker can never be shown more than the repeater range (40 m by default) from the strongest repeater.

In V4 the foot-mounted BMI270 measures each real stride (zero-velocity update at heel strike), replacing the fixed step length.

### 12.3 Health and safety detection rules

| Event | Rule (editable) |
| --- | --- |
| Fall | free fall < 0.4 g and / or impact > 3 g, then body angle > 55° after 2 s |
| No movement | no motion for 30 s (demo setting; longer on site) |
| Body temperature | warning ≥ 38 °C, danger ≥ 39.5 °C |
| Heart rate | warning < 50 or > 120 bpm, danger < 40 or > 150 bpm |
| SpO₂ (estimate) | warning ≤ 92 %, danger ≤ 88 % |
| Heat (per repeater) | wet-bulb warning 30.5 °C, danger 33.5 °C (Indian mine regulation) |
| SOS | button held 1.5 s on the body, cuff or repeater |
| Kit (V4) | helmet off, boots off, zip open, seam loop broken, suit not worn → admin alert at once |

### 12.4 Gas measurement

Each MQ sensor learns its clean-air level after a 60 s warm-up. Its resistance ratio Rₛ/R₀ is converted to ppm with the datasheet curve, ppm = a · (Rₛ/R₀)^b. Only the gases a sensor is built for raise alarms. A rise of 1 V triggers a local fail-safe buzzer, even if the hub is offline. When a danger limit is crossed, the hub starts an automatic evacuation, if that option is on.

### 12.5 Evacuation routing

1. The hub turns the tunnel centre lines into a graph and finds the junctions automatically.
2. Dijkstra's algorithm runs from all exits at once.
3. Tunnels inside a danger zone (25 m radius around the hazard) cost 1000× more. Routes therefore go around a gas or fire area when another way exists, and straight out of it when it does not.
4. Every repeater gets its own instruction for its LED exit sign: LEFT, RIGHT, UP, HERE, NO WAY or DANGER, plus the distance.
5. Every worker gets a route drawn on the map. In V4 the helmet speaks it and the cuff vibrates.

### 12.6 Control-room software

&#91;image: Figure 12.1 – 3D control room: mine, repeaters with live exit signs, workers by status\]

*Figure 12.1 – 3D mine view built from the hub map.*

&#91;image: Figure 12.2 – Evacuation: routes to the nearest exit around the danger zone\]

*Figure 12.2 – Evacuation mode.*

&#91;image: Figure 12.3 – Worker details: vitals with limits, location, radio path, history\]

*Figure 12.3 – Worker panel.*

&#91;image: Figure 12.4 – Gas and air at a repeater against limits\]

*Figure 12.4 – Repeater gas and air panel.*

&#91;image: Figure 12.5 – Body-unit OLED screens\]

*Figure 12.5 – What the worker sees on the body unit / cuff.*

## 13. Usage

A worker adds under a minute at the gate. After that the system runs on its own until the exit scan.

### 13.1 Worker's shift

1. **Kit up.** Take a charged body unit from the dock. In V4, take a suit and put it on; it self-checks helmet, boots, cuff, zip and skin contact, and the cuff shows anything missing.
2. **Entry check.** Tap the kit tags on the entry station and press PHOTO. In V4, tap the ID card instead. The hub runs the YOLOv8 kit check; the supervisor approves, and the body unit or suit is paired to the worker.
3. **Underground.** Vitals, steps, falls and position go to the control room every second through the nearest repeater. The worker sees status on the OLED or cuff screen.
4. **Alert.** The body unit or cuff vibrates and shows the message; in V4 the helmet speaks it. Repeater exit signs show the arrow and distance to the nearest safe exit.
5. **Emergency.** Hold SOS for 1.5 s on the body, cuff or any repeater.
6. **Exit.** Scan out at the gate, return the unit or suit to the dock to charge, and the pairing ends.

### 13.2 Control-room operator

| Task | How |
| --- | --- |
| See who is underground and where | 3D mine map and workers list, live |
| Act on an alert | “Needs attention” list → worker panel (vitals, location, radio path, history, medical card) |
| Warn one worker or everyone | Alert button with confirmation; message reaches the body units and repeater buzzers |
| Evacuate | Mark the hazard → routes are computed, exit signs and worker maps update. Starts automatically on a gas danger reading |
| Approve entry | Entry page: tags, photo, AI verdict, approve / reject / revoke |
| Watch gas and air | Gas & air page per repeater against the limits, 5-minute trends |
| Check the network | Network page: hop, parent, signal of every repeater |

### 13.3 Installation and maintenance

| Item | Interval | Action |
| --- | --- | --- |
| Repeater installation | once | Bolt to the rib at line-of-sight spacing (from the range test), connect the mine supply through the gland, survey its position on the map |
| MQ sensor burn-in | once, 24–48 h | Run powered before the first calibration |
| Gas calibration | monthly (prototype) | Clean-air baseline; bump test with test gas for the product sensors |
| Battery check | weekly | Repeater “on battery” test by switching off the mine supply |
| Seals, filters | monthly | Inspect the gasket, flame-arrestor discs and ePTFE membranes; replace if clogged |
| Suit | every shift | Remove pods, wash the coverall, dock pods to charge |
| Software | as needed | Limits and map edited from the admin page; firmware by USB-C |

## 14. Cost analysis

A complete repeater costs about **₹6,860** and one smart suit about **₹12,800**. A site with 10 repeaters and 20 suits needs about **₹3.3 lakh** of hardware. Prices are approximate Indian online prices from October 2026; full lists are in the repository (`docs/final_bom.md`, `docs/v4_bom.csv`, `hardware/repeater_x2_shopping_list.xlsx`).

### 14.1 One repeater (V4 PCB + mine case)

| Group | Main parts | ≈ ₹ |
| --- | --- | --- |
| Modules | XIAO ESP32-C6, MAX7219 8×32 matrix, MQ-4, MQ-7, MQ-136, AHT20, 85 dB buzzer | 1,905 |
| PCB and soldered parts | board (share of 5), K7805 regulator, diodes, fuse, TVS, 74HCT125, connectors, passives | 1,237 |
| Case, power and fittings | PETG print, 3S 18650 pack + BMS + charger, adapter, SOS button, antenna, vents, flame-arrestor discs, gland, gasket, window, wire | 3,720 |
| **Total per repeater** |  | **6,862** |

### 14.2 One smart suit (V4)

| Part | Main parts | ≈ ₹ |
| --- | --- | --- |
| Core pod | ESP32-C6, 3000 mAh LiPo, charger, buck-boost, fuel gauge, IMU, pressure sensor, SOS, pogo, case | 2,790 |
| Helmet pod | XIAO C6, antenna, I²S amplifier + speaker, 600 mAh LiPo, worn switch, helmet, housing | 2,260 |
| Wrist cuff | 1.3" OLED, 3 glove buttons, vibration motor, MAX30102, sleeve cable + GX12, case | 1,480 |
| Boot pod | XIAO C6, BMI270, 300 mAh LiPo, FSR, safety boots, clip | 3,270 |
| Suit fabric and sensing | FR coverall, conductive thread, snaps, zip reed switch, skin probe, contact pad | 3,040 |
| **Total per suit** |  | **≈ 12,800** (≈ 10,800 without the certified helmet and boots a mine already issues) |

### 14.3 Example site and comparison

| Item | Quantity | ≈ ₹ |
| --- | --- | --- |
| Repeaters | 10 | 68,620 |
| Smart suits | 20 | 2,56,000 |
| Entry chamber (main repeater reuse, PN532 reader, ID cards, 4-slot dock) | 1 | 1,290 |
| **Hardware total** |  | **≈ 3,25,910** |

The control room runs on an existing laptop, or a mini-PC for a permanent install. None of the nine commercial systems in section 4 publishes a price; all are sold through enterprise quotes. A UHF RFID portal alone costs about ₹28,000 and one UWB tag or anchor about ₹2,000, which is why MineSafe avoids them. At volume, moulded cases and an assembled PCB would cut the per-unit cost further.

**Running cost:** about ₹7 a day of electricity for 10 repeaters. Gas sensors have a limited life and are replaced on the interval given in their datasheets.

## 15. Validation and testing

Validation runs at three levels: **design checks** (done for all PCBs and enclosures), **bench tests** of each subsystem (most done), and **field tests** against measurable acceptance criteria. The field tests are the V3 calibration work now in progress. Results are recorded here as each test is completed.

### 15.1 Design verification (completed)

| ID | Test | Method | Result | Status |
| --- | --- | --- | --- | --- |
| D1 | PCB electrical rules | KiCad DRC on all 5 boards | 0 unconnected pads; no copper or clearance errors | Passed |
| D2 | Enclosure fit | Automated CAD collision check of every PCB (built from KiCad), battery, module, button, connector against its case | Repeater + 4 pods: no collisions | Passed |
| D3 | Power budget | Datasheet calculation (section 11) | Core pod 21 h ≥ 12 h shift; repeater 7 h backup; helmet / boot need duty-cycled radio | Passed |
| D4 | Signal levels | Hand calculation | MQ divider 5 V → 3.33 V within the ADC range; MAX7219 driven at 5 V logic via 74HCT125 | Passed |

### 15.2 Bench tests on the V3 prototype

| ID | Test | Method | Result | Status |
| --- | --- | --- | --- | --- |
| B1 | Repeater chain forms by itself | 3 XIAO C6 repeaters powered in any order | 3/3 linked on the Network page; hop and parent shown | Passed |
| B2 | Air sensing | AHT20 on each repeater vs room reading | 31.3 °C / 62 % RH read and logged; wet-bulb computed | Passed |
| B3 | Gas channel + local buzzer | MQ sensor exposed to a gas source (lighter gas, unlit) | Reading rises, local fail-safe buzzer and hub alert. A fixed-voltage false alarm on a new sensor was found and fixed with the clean-air baseline | Passed |
| B4 | Body sensors | Library tests per sensor | Pulse sensor reading. I²C (MPU6050, BMP180) and DS18B20 wiring being corrected | In progress |
| B5 | Hub logic with simulator | Simulated workers and repeaters | Alerts, map, gas limits, “NO SENSOR” detection, incident log all correct | Passed |
| B6 | Robustness | Hotspot subnet changed; non-JPEG photo sent | Main repeater found the hub again by itself; bad photo rejected | Passed |

### 15.3 Field and performance tests (acceptance criteria)

| ID | Test | Method | Pass if | Status |
| --- | --- | --- | --- | --- |
| F1 | Radio range per hop | Corridor / tunnel walk, packet delivery logged at 5 m steps | ≥ 98 % packets delivered at the chosen repeater spacing; spacing set from this | Planned |
| F2 | Alert latency | Alert from hub to the deepest worker, 3-hop chain, 50 trials | 95 % of alerts delivered in ≤ 3 s | Planned |
| F3 | Step and distance accuracy | 100 m measured corridor, 5 walkers, with and without repeater fixes | Distance error ≤ 5 %; position never off by more than one repeater spacing | In progress |
| F4 | Fall detection | 20 staged falls on a mat + 1 h of normal walking, sitting, climbing | ≥ 90 % falls detected; ≤ 1 false alarm per hour | Planned |
| F5 | No-movement alert | Worker lies still | Alert at the set time ± 2 s | Planned |
| F6 | Heart rate and SpO₂ | Against a clinical fingertip oximeter, 10 people, rest and after exercise | HR within ± 5 bpm; SpO₂ within ± 3 % at rest | Planned |
| F7 | Gas response | Against a reference detector with test gas (or a safe proxy) | Alarm at the set threshold; response time ≤ 60 s after warm-up | Planned |
| F8 | Evacuation guidance | Hazard placed at each tunnel segment of a test map | Every repeater shows the direction away from the hazard to the nearest exit | Planned |
| F9 | AI kit check | Our own kit dataset, photos with and without each item | ≥ 90 % correct, no unsafe pass in the test set | Planned |
| F10 | Power and battery | Measured current with a USB / bench meter; battery run-down | Within 20 % of section 11; repeater switches to battery with no reset | Planned |
| F11 | Water and dust (repeater case) | Hose test 30 min; dust box | No water inside; electronics run (target IP65) | Planned |
| F12 | Shock and heat | 1 m drop on concrete; 24 h at 45 °C | No cracks or resets; readings stable | Planned |
| F13 | Full trial | 2 workers, 3 repeaters, 30 min scenario with gas alarm, fall, SOS and evacuation | All events reach the control room and the workers; the location trace matches the walked path | Planned |

**Evidence kept for each test:** a test log (date, setup, raw data), screenshots of the dashboard and a short video. These form the demonstration at Avishkar.

## 16. Safety, standards and limitations

MineSafe is a capstone prototype. It follows Indian mine limits for its alarms, but it is **not yet certified** for use in gassy (Degree II / III) coal mines.

### 16.1 Alarm limits used

| Gas / condition | Warning | Danger | Basis |
| --- | --- | --- | --- |
| Methane CH₄ | 0.75 % | 1.25 % | Coal Mines Regulations 2017, reg. 153(2) |
| Oxygen O₂ (too little) | < 19.5 % | < 19.0 % | CMR 2017 reg. 153(2); OSHA |
| Carbon monoxide CO | 35 ppm | 100 ppm | NIOSH REL; OSHA PEL 50 ppm |
| Hydrogen sulphide H₂S | 10 ppm | 20 ppm | NIOSH ceiling; OSHA ceiling |
| Carbon dioxide CO₂ | 0.5 % | 3 % | CMR 2017; NIOSH STEL |
| Wet-bulb temperature | 30.5 °C | 33.5 °C | CMR 2017 reg. 153(2) |

All limits are editable on the hub and are checked against the latest DGMS circulars before any site use.

### 16.2 Standards that apply to a product version

| Area | Standard / rule | MineSafe status |
| --- | --- | --- |
| Equipment in gassy mines | DGMS approval; IS/IEC 60079-0 (general), 60079-11 (intrinsic safety “Ex ia”), 60079-1 (flameproof “Ex d”) | Design notes only: flame-arrestor seats, low-energy electronics, protected cells. Certification is product work |
| Enclosure protection | IEC 60529 (IP codes) | Designed for IP65; hose test planned (F11) |
| Lithium cells | IEC 62133 (portable cells), protected packs | Protected cells and BMS specified |
| Radio | WPC delicensed bands in India: 2.4–2.4835 GHz (ESP-NOW), 865–867 MHz (LoRa) | Uses these bands only |
| Head protection | Certified mining helmet, issued by the mine | The helmet pod clips on; the helmet itself is not modified |
| Tracking in mines (reference) | US MSHA post-Sago rules require underground communication and tracking | Shows the need MineSafe addresses |

### 16.3 Safety by design

- **Never lock the worker in:** suit opening, removal and tears are detected and reported, never prevented. A quick release always works.
- **Fail-safe local alarms:** every repeater sounds its own buzzer on a gas rise, even if the hub or the link is down.
- **Power-cut ride-through:** repeaters switch to battery without a reset.
- **No high voltage:** everything on the worker runs at 3.3–4.2 V; repeaters run on a 9–30 V DC mine supply.
- **Data privacy:** health data stays on the site hub; there is no cloud in V2 onwards.

### 16.4 Limitations (honest)

1. **MQ gas sensors are indicative only.** They react to several gases and drift with temperature and humidity. The product uses NDIR (CH₄) and electrochemical (CO, H₂S, O₂) sensors, which the hub already accepts.
2. **Low-cost optical vitals are trend-level, not medical-grade,** especially during movement.
3. **Dead-reckoning accuracy depends on repeater spacing** and is not sub-metre. UWB is the option where sub-metre is required.
4. **2.4 GHz needs line of sight in tunnels,** so repeaters must be closer at bends. LoRa is planned for long straight runs.
5. **V3 field calibration and V4 builds are still in progress** (section 15).

## 17. Impact, commercialisation and future scope

MineSafe targets the gap that recent Indian rescues exposed: knowing at once who is underground, where they are and whether they are safe. It does this at a price smaller mines can afford.

### 17.1 Impact

| Area | Impact |
| --- | --- |
| Social | Faster rescue with a last known position; fewer deaths from unnoticed falls, gas and heat stress; families and unions can see that kit and health are watched |
| Economic | Hardware ≈ ₹6,860 per repeater and ₹12,800 per suit; built from Indian-available modules; less lost time from accidents and stoppages |
| Operational | Digital entry log, automatic kit compliance, gas and heat records per location for DGMS inspections |
| UN SDGs | SDG 3 Good health and well-being · SDG 8 Decent work (safe working environments) · SDG 9 Industry, innovation and infrastructure |
| National programmes | Make in India / Atmanirbhar Bharat: designed, built and manufacturable in India |

### 17.2 Commercialisation path

- **Users:** small and medium coal and metal mines, tunnelling projects (metro, hydro, road tunnels), quarries with underground workings.
- **Offer:** hardware kit (repeaters, suits, entry chamber) plus an annual support plan for calibration, sensor replacement and software updates.
- **Steps:**
  1. Field trial with a partner mine or a tunnelling site.
  2. Intrinsic-safety design and DGMS approval.
  3. Moulded enclosures and assembled PCBs.
  4. Pilot sales.
- **Protection:** design registration for the enclosures and suit; patent search on the self-checking suit and the exit-sign repeaters.

### 17.3 Future scope

1. **LoRa backbone** (SX1262, 865–867 MHz) between repeaters for long tunnels.
2. **Certified gas sensing:** NDIR CH₄, electrochemical CO / H₂S / O₂ modules, with bump-test and calibration logs.
3. **Intrinsically safe redesign** (Ex ia) of the wearable and the repeater.
4. **UWB anchors** at junctions where sub-metre location is needed.
5. **Heat-stress and fatigue prediction** from heart rate, skin temperature, wet-bulb and activity trends.
6. **Two-way voice** through the helmet pod.
7. **Integration** with refuge chambers, proximity-detection systems and the mine's SCADA.

## 18. References

**Accident data and incidents**

1. [141 die in coal mine accidents in two years: Government](https://www.etvbharat.com/en/bharat/141-die-in-coal-mine-accidents-in-two-years-government-enn26081305600) — ETV Bharat, Ministry of Mines data, 13 Aug 2026.
2. [Telangana tunnel collapse: whereabouts of trapped persons located](https://www.deccanherald.com/amp/story/india%2Ftelangana%2Ftelangana-tunnel-collapse-whereabouts-of-four-trapped-persons-located-says-state-minister-krishna-rao-3427625) — Deccan Herald, 2025.
3. [Rescue operations continue at Assam's Umrangso mine](https://www.newsonair.gov.in/rescue-operations-continue-at-assams-umrangso-mine-3-bodies-recovered-after-150-hours) — All India Radio, Jan 2025.
4. [All 15 Hindustan Copper officials rescued from collapsed lift at Kolihan mine](https://www.deccanherald.com/india/rajasthan/all-15-hindustan-copper-limited-officials-rescued-from-collapsed-lift-at-rajasthans-kolihan-mine-3023138) — Deccan Herald, May 2024.
5. [2018 Meghalaya mining accident](https://en.wikipedia.org/wiki/2018_Meghalaya_mining_accident) — Wikipedia.
6. [Communications and tracking in underground mines](https://www.msha.gov/compliance-and-enforcement/equipment-approval-certification/communications-and-tracking-underground-mines) — US MSHA.

**Regulations and exposure limits**

7. [Coal Mines Regulations 2017, regulation 153](https://indiankanoon.org/doc/24960800/) — Government of India.
8. [NIOSH Pocket Guide to Chemical Hazards](https://www.cdc.gov/niosh/npg/) and [IDLH values](https://www.cdc.gov/niosh/idlh/).
9. [30 CFR 75.323 — Actions for excessive methane](https://www.law.cornell.edu/cfr/text/30/75.323) — US MSHA.

**Literature (from the team's literature review)**

10. Bandyopadhyay, Chaulya, Mishra — [Wireless Information and Safety System for Mines](https://www.researchgate.net/publication/226510179_Wireless_Information_and_Safety_System_for_Mines), J. Scientific & Industrial Research 68(2), 2009 (CSIR-CIMFR).
11. [Research on IMU-assisted UWB-based positioning algorithm in underground coal mines](https://pmc.ncbi.nlm.nih.gov/articles/PMC10384321/) — MDPI Micromachines, 2023.
12. [Development and evaluation of a UWB-based indoor positioning system for underground mine environments](https://doi.org/10.1007/s42461-023-00797-z) — Mining, Metallurgy & Exploration, 2024.
13. [IoT-based smart helmet for hazard detection in mining industry](https://arxiv.org/pdf/2304.10156) — arXiv, 2023.
14. [IoT based smart security helmet for miner's safety](https://ieeexplore.ieee.org/document/10146728/) — IEEE Xplore, 2023.
15. [Real-time PPE compliance detection based on deep learning](https://doi.org/10.3390/su15010391) — MDPI Sustainability, 2023.
16. [PPE detector: a YOLO-based architecture to detect PPE for construction sites](https://doi.org/10.7717/peerj-cs.999) — PeerJ Computer Science, 2022.
17. [Evaluating the accuracy of low-cost wearable sensors for healthcare monitoring](https://www.mdpi.com/2072-666X/16/7/791) — MDPI, 2025.
18. [Recent advances on IoT-assisted wearable sensor systems for healthcare monitoring](https://pmc.ncbi.nlm.nih.gov/articles/PMC8534204/) — review.

**Commercial products reviewed (July 2026)**

19. [Teknovate MineGuard 360](https://www.teknovate.in/smart-mining) · [MineARC GuardIAN](https://guardian.minearc.com/) · [Leantegra](https://leantegra.com/) · [Rajant Health](https://rajanthealth.com/) · [EasyM2M SmartKavach](https://easym2m.in/smartkavach/) · [36Zero](https://36zero.io/) · [HaloTag](https://minesafeglobal.com/collision-prevention-avoidance-systems-mining/) · [ANTAR IoT](https://antariot.com/mining-2/) · [Jarsh Safety](https://jarshsafety.com/).

**Competition format**

20. [Guidelines for the Aavishkar workshop](https://sppucirculars.unipune.ac.in/wp-content/uploads/2025/01/Guidelines-and-Time-Table-for-Aavishkar-Workshop-on-2nd-January-2025_31122024.pdf) (problem, relevance, objectives, methodology, data, findings, application, model), used to check the structure of this document.

**Project repository:** [github.com/Manas-36/MINESAFE](https://github.com/Manas-36/MINESAFE) — firmware, hub, 3D control app, KiCad boards, CadQuery models and BOMs.
