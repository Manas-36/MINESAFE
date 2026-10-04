# Research and design (v0.0)

Everything the team prepared before the build: problem validation, literature review, competitive analysis and the full-scale pilot design.

## Project
**Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Miners** — capstone project, B.E. Mechanical and Mechatronics Engineering, TCET Mumbai, 2026–27. Domain: Mechatronics / Embedded Systems — IoT-based mining safety. Guide: Mr Dipesh Tare, Assistant Professor.

## Key numbers
| | |
|---|---|
| 38 + 32 | Fatal accidents in Indian coal + metalliferous mines in 2024 (DGMS) |
| 33 → 36 → 42 | ICMM member fatalities 2022 → 2024, rising again |
| 2.93 million | Work-related deaths per year worldwide (ILO) |
| 10 + 31 | Papers in the survey table + papers in the full reading list |
| 9 | Commercial products compared — none combines AI PPE, vitals and GPS-free location |
| ≈ ₹6,500 vs ≈ ₹3,01,000 | Built prototype vs 20-worker pilot design |

## Documents
| File | What it covers |
|---|---|
| [literature.md](literature.md) | Problem statistics, 4 research streams, survey table, full reading list with links |
| [competitors.md](competitors.md) | 9-product feature matrix, flaws, gap, positioning statement and talking points |
| [pilot_design.md](pilot_design.md) | 7-layer pilot architecture, entry-chamber logic, data flow, costs, planned vs built software |
| [../decisions.md](../decisions.md) | Why the prototype differs from the pilot design |

### Original files ([`source/`](source/))
| File | Prepared |
|---|---|
| Assignment_1_Research_Analysis_Problem_Statement.docx | 31 Jul 2026 — research analysis, survey table, final problem statement |
| Week_3_Architecture_Design_Block_Diagram.docx | 31 Jul 2026 — block diagram, component list, algorithms |
| Competitive_Product_Analysis_Mining_Safety.docx | July 2026 — 9 vendor profiles and matrix |
| Hardware_Architecture_and_BOM.docx | July 2026 — layer-by-layer hardware, data flow, indicative BOM |
| Presentation_Brief_Flaws_and_Software_Integration.docx | 31 Jul 2026 — flaws vs differentiation, software stack |
| Existing_Research_Papers_2021_onward.pdf | Reading list by topic |
| Total_System_BOM.xlsx | Pilot BOM workbook |

## Final problem statement
Underground mining remains one of the most hazardous occupations; fall of ground, fall of person, powered haulage and gas incidents lead fatality statistics in India (DGMS) and abroad (MSHA, ICMM). Outcomes are made worse by PPE non-compliance, late detection of a worker's medical distress or fall, and the difficulty of locating an incapacitated worker without GPS. Existing research and products address these risks in isolation, and commercial systems are priced for large enterprises.

**Need:** an integrated, low-cost system that verifies PPE with AI vision at the entry checkpoint, continuously monitors heart rate, SpO₂ and body temperature with automatic fall / unconsciousness detection, locates workers without GPS, and reports everything in real time to a supervisor dashboard.

## Concept selection
Problem-statement trends (SIH), Aavishkar judging themes and past winning projects were reviewed, and five blueprints were compared (agriculture robotics, disaster management, assistive healthcare, smart manufacturing, counter-drone defence) before choosing mine safety.
