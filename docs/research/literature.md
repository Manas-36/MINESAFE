# Literature review

From *Assignment 1 — Research Analysis and Problem Statement* (31 Jul 2026) and the *Existing Research Papers (2021 onward)* list. Originals: [`source/`](source/).

## 1. Why the problem is real

| Source | Finding |
|---|---|
| ILO | ≈ **2.93 million** work-related deaths per year worldwide, ≈ **0.33 million** of them fatal occupational accidents |
| ICMM member companies | Fatalities rose two years running: **33 (2022) → 36 (2023) → 42 (2024)**, reversing a decade-long decline |
| DGMS (India), 2024 | **38 fatal accidents in coal mines** and **32 in metalliferous mines**; fall of ground, fall of person and powered haulage are the leading categories |
| DGMS guidance | Missing chin-strap helmets, harnesses and safety footwear named as recurring root causes; PPE non-compliance is a contributing factor that is rarely counted separately |
| UWB localisation literature | Underground mines are GPS-denied and communication-limited, which delays locating an injured worker |

## 2. What the literature says (four research streams)

| Stream | State of the art | What is missing |
|---|---|---|
| Smart helmets (2021–24) | Gas sensing + accelerometer impact alert + LoRa/Wi-Fi | Single-function; no camera PPE check, no precise location |
| AI PPE detection | YOLOv5/v7/v8, mAP up to ~97 % | Validated on construction sites, not underground mines |
| Health wearables | MAX30102, MLX90614, nRF52840 designs | Clinical/consumer; not combined with location or PPE status |
| Underground localisation | UWB + IMU fusion, ~0.2–0.5 m accuracy (2023–24) | Positioning only, no health or PPE data |

**Research gap:** no reviewed paper integrates PPE vision, health monitoring, localisation and a dashboard in one field-tested underground system.

## 3. Literature survey table (Assignment 1)

| # | Paper | Venue, year | Parameters found | Drawback | Gap MineSafe addresses |
|---|---|---|---|---|---|
| 1 | Advanced IoT-Based Smart Mining Helmet with LoRa-Enabled Communication | IJRASET, 2024 | LoRa link; gas and helmet-status sensors | Single function; no PPE vision or location | AI PPE check + location on the same system |
| 2 | LoRaWAN Based Smart Safety Helmet with Protection Mask for Miners | IEEE IC3IoT, 2024 | Mask integration; LoRaWAN hazard alerts | No vitals, no positioning | Continuous HR / SpO₂ / temperature + location |
| 3 | Improved YOLOv7 Architecture for Miners' PPE Detection and Tracking | ScienceDirect (Comput. Electr. Eng.), 2025 | High-accuracy PPE detection and tracking | Standalone vision model | PPE result fused with vitals and position in one dashboard |
| 4 | Real-Time PPE Compliance Detection Based on Deep Learning | MDPI Sustainability, 2023 | Deep-learning PPE classifier | Construction sites only | Tested at the mine entry checkpoint |
| 5 | Healthcare Monitoring Using an IoT-Based Cardio System | MDPI IoT, 2025 | Continuous cardiac vitals over IoT | Clinical, not rugged | Vitals in a mining wearable with PPE + location |
| 6 | Evaluating the Accuracy of Low-Cost Wearable Sensors for Healthcare Monitoring | MDPI Sensors, 2025 | Accuracy of nRF52840 / MAX32664D sensors | No location or PPE | Same class of low-cost sensors inside a fused system |
| 7 | IMU-Assisted UWB-Based Positioning Algorithm in Underground Coal Mines | MDPI Micromachines / PMC, 2023 | Sub-metre UWB + IMU fusion | Positioning only | IMU dead reckoning carries vitals + PPE on the same link |
| 8 | Accurate Integrated Position Measurement System for GPS-Denied Coal Mine | ScienceDirect (Measurement), 2023 | Integrated positioning accuracy | No health monitoring | Health telemetry alongside position |
| 9 | Development and Evaluation of a UWB-Based Indoor Positioning System for Underground Mines | Mining, Metallurgy & Exploration (Springer), 2024 | Field-validated UWB underground | No PPE or vitals | One wearable, one dashboard |
| 10 | UWB-Based Localization System Aided With Inertial Sensor for Underground Coal Mine Applications | IEEE Journals & Magazine | Inertial-aided UWB accuracy | Standalone localisation | Packaged into a worker-safety platform |

## 4. Full reading list (2021 onward)

### 4.1 Smart helmets and IoT safety systems
- Advanced IoT-Based Smart Mining Helmet with LoRa-Enabled Communication for Enhanced Safety — IJRASET, 2024 — <https://www.ijraset.com/research-paper/advanced-iot-based-smart-mining-helmet-with-lora>
- LoRaWAN Based Smart Safety Helmet with Protection Mask for Miners (Shivaanivarsha et al.) — IEEE IC3IoT, Chennai, 2024 — IEEE Xplore
- Smart Helmet and Monitoring for Miners with Enhanced Protection (Banik, Mishra, Manikandan) — IEEE ICECAA, 2023 — IEEE Xplore
- Power Efficient Intelligent Helmet for Coal Mining Security and Alerting (Banu et al.) — IEEE ICSCSS, 2023 — IEEE Xplore
- A Protection Approach for Coal Miners Safety Helmet Using IoT (Modi, Mali, Sharma et al.) — Springer, Semantic Intelligence, 2024 — <https://doi.org/10.1007/978-981-97-3690-4>
- IoT-Enabled Safety Helmet for Coal Miners: Real-Time Monitoring, Data Collection, and Analysis — IEEE conference, 2024 — <https://ieeexplore.ieee.org/iel8/11026116/11026063/11026450.pdf>
- Development of an Integrated Safety Monitoring System for Coal Miners using Smart Helmets — IEEE conference, 2024 — <https://ieeexplore.ieee.org/iel8/11034706/11034776/11035664.pdf>
- IoT based Smart Security Helmet for Miner's Safety — IEEE Xplore, 2023 — <https://ieeexplore.ieee.org/document/10146728/>
- IoT-Based Smart Helmet for Hazard Detection in Mining Industry — arXiv, 2023 — <https://arxiv.org/pdf/2304.10156>

### 4.2 PPE detection with AI / computer vision
- An effective deep learning approach enabling miners' protective equipment detection and tracking using improved YOLOv7 — Computers & Electrical Engineering, 2025 — <https://www.sciencedirect.com/science/article/abs/pii/S0045790625001168>
- Real-Time PPE Compliance Detection Based on Deep Learning Algorithm (Lo, Lin, Hung) — MDPI Sustainability, 2023 — <https://doi.org/10.3390/su15010391>
- Personal Protective Equipment Detection: A Deep-Learning-Based Sustainable Approach — MDPI Sustainability, 2023 — <https://www.mdpi.com/2071-1050/15/18/13990>
- PPE detector: a YOLO-based architecture to detect PPE for construction sites (Ferdous & Ahsan) — PeerJ Computer Science, 2022 — <https://doi.org/10.7717/peerj-cs.999>
- Automatic PPE Monitoring System for Construction Workers Using YOLO with Deep Reinforcement Learning — 2024 — <https://www.researchgate.net/publication/386252452>
- Fast PPE Detection for Real Construction Sites Using Deep Learning — 2021 — <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8156681/>
- Enhancing Construction Worker Safety through YOLOv8-Based PPE Detection — IJRASET, 2024 — <https://www.ijraset.com/research-paper/enhancing-construction-worker-safety-through-yolov8-based-ppe-detection>

### 4.3 IoT health monitoring and wearable sensors
- Healthcare Monitoring Using an Internet of Things-Based Cardio System — MDPI IoT, 2025 — <https://www.mdpi.com/2624-831x/6/1/10>
- Evaluating the Accuracy of Low-Cost Wearable Sensors for Healthcare Monitoring — MDPI, 2025 — <https://www.mdpi.com/2072-666X/16/7/791>
- A Wearable IoT Device for Noninvasive Remote Monitoring of Vital Signs Related to Heart Failure — MDPI IoT, 2024 — <https://doi.org/10.3390/iot5010008>
- Recent Advances on IoT-Assisted Wearable Sensor Systems for Healthcare Monitoring — review — <https://pmc.ncbi.nlm.nih.gov/articles/PMC8534204/>
- A Comprehensive Survey on Wearable Computing for Mental and Physical Health Monitoring — MDPI Electronics, 2025 — <https://www.mdpi.com/2079-9292/14/17/3443>

### 4.4 Underground localisation and navigation
- Research on IMU-Assisted UWB-Based Positioning Algorithm in Underground Coal Mines — MDPI Micromachines, 2023 — <https://pmc.ncbi.nlm.nih.gov/articles/PMC10384321/>
- Accurate integrated position measurement system for mobile applications in GPS-denied coal mine — 2023 — <https://www.sciencedirect.com/science/article/abs/pii/S0019057823001830>
- Development and Evaluation of a UWB-Based Indoor Positioning System for Underground Mine Environments — Mining, Metallurgy & Exploration, 2024 — <https://doi.org/10.1007/s42461-023-00797-z>
- UWB-Based Localization System Aided With Inertial Sensor for Underground Coal Mine Applications — IEEE — <https://ieeexplore.ieee.org/abstract/document/9007738>
- Underground mine positioning: a review (Seguel, Palacios-Játiva, Azurdia-Meza et al.) — IEEE Sensors Journal, 2022, 22(6), 4755–4771 — IEEE Xplore
- Human Real Time Localization System in Underground Mines using UWB — <https://www.researchgate.net/publication/341036813>

> Several IEEE entries are best found by searching the exact title on ieeexplore.ieee.org, which gives the citation-ready DOI.

## 5. How the literature shaped the build
| Literature finding | MineSafe prototype | Pilot / future |
|---|---|---|
| YOLO PPE detection works (mAP ~97 %) but not tested in mines | YOLOv8 on the admin laptop, phone camera at entry; RFID tags as a second check | YOLO on Raspberry Pi in the entry chamber, tuned for low light and dust |
| UWB + IMU gives sub-metre position | IMU dead reckoning + tunnel map matching + repeater check-points (no UWB cost) | DWM3000 UWB anchors on repeaters, Kalman fusion |
| Low-cost vitals sensors are accurate enough | MAX30100/30102, DS18B20, MPU6050 | MLX90614 / MAX32664 for better accuracy |
| Smart helmets are single-function | One body unit with all sensors + gas on repeaters | Same, plus kit-removal sensing |
