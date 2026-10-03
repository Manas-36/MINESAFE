# Research and design (v0.0)

Summary of the research phase that came before the build. The full literature review, competitive analysis and architecture documents were prepared as separate reports; add them to this folder as PDF/DOCX.

## Project
**Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Miners** — capstone project, B.E. Mechatronics, TCET Mumbai.

## Concept selection
Problem-statement trends (SIH), Aavishkar judging themes and past winning projects were reviewed, and five blueprints were compared (agriculture robotics, disaster management, assistive healthcare, smart manufacturing, counter-drone defence) before choosing mine safety.

## Literature review
Sources: ILO, DGMS (Directorate General of Mines Safety), MSHA (US Mine Safety and Health Administration) and peer-reviewed papers on PPE compliance, wearable physiological monitoring and underground localisation.

## Competitive analysis
Nine commercial products were compared feature by feature.

**Central finding:** no verified commercial product combines AI-based PPE compliance detection, continuous physiological monitoring and sub-metre GPS-denied localisation in a single underground-mining architecture.

## Designed architecture (seven layers)
1. Identity tags — worker NFC badge + UHF RFID tags in each PPE item
2. Entry chamber — UHF RFID portal, camera + edge AI (YOLO), door lock
3. Wearable hub — ESP32 + UWB + LoRa + MAX30102 + MLX90614 + MPU6050
4. Repeater chain — UWB anchors + LoRa relays
5. Surface gateway — LTE / LoRa concentrator
6. Server — multilateration engine, database, backend
7. Dashboard — live monitoring and alerts

Pilot budget for 20 workers, 2 entry chambers, 8 repeaters, 1 gateway and 1 server: **≈ ₹3,01,000** — see [`Total_System_BOM.xlsx`](Total_System_BOM.xlsx) and [`../../hardware/bom_pilot.csv`](../../hardware/bom_pilot.csv).

## Later phases
Backend software design and a patent search were completed before hardware work began. The built prototype (v0.1 onwards) keeps the same seven layers but uses lower-cost parts — see [`../decisions.md`](../decisions.md).
