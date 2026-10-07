# Mine gases and the limits MineSafe uses

All limits are editable on the admin page (**Limits** tab) and saved on the laptop (`hub/data/gas_limits.json`).
**Warning** = long-term exposure / legal working limit (repeater turns yellow, logged).
**Danger** = short-term / stop-work limit (all buzzers + LEDs, and an evacuation if "auto evacuation" is on).

| Gas | Where it comes from in a mine | Warning | Danger | Basis |
|---|---|---|---|---|
| Methane CH₄ (firedamp) | coal seams, old workings — explosive 5–15 % | 0.75 % | 1.25 % | Coal Mines Regulations 2017, reg. 153(2): ≤ 0.75 % in return air, ≤ 1.25 % anywhere. (US MSHA 30 CFR 75.323: adjust at 1.0 %, withdraw at 1.5 %) |
| Oxygen O₂ (too little) | displaced by CH₄ / CO₂ / N₂, poor ventilation | below 19.5 % | below 19.0 % | CMR 2017 reg. 153(2): not less than 19 %; OSHA 19.5 % |
| Carbon dioxide CO₂ (blackdamp) | breathing, oxidation, blasting, strata | 0.5 % (5000 ppm) | 3 % (30 000 ppm) | CMR 2017: ≤ 0.5 %; NIOSH STEL 3 %; IDLH 4 % |
| Carbon monoxide CO | fires, spontaneous heating, blasting, diesel | 35 ppm | 100 ppm | NIOSH REL 35 ppm (10 h), ceiling 200, IDLH 1200; OSHA PEL 50 |
| Hydrogen sulphide H₂S (stinkdamp) | sulphide ores, stagnant water | 10 ppm | 20 ppm | NIOSH ceiling 10; OSHA ceiling 20; IDLH 100 |
| Nitrogen dioxide NO₂ | blasting fumes, diesel exhaust | 1 ppm | 5 ppm | NIOSH STEL 1; OSHA ceiling 5; IDLH 20 |
| Sulphur dioxide SO₂ | blasting sulphide ores, fires | 2 ppm | 5 ppm | NIOSH 2 (10 h) / 5 (15 min); IDLH 100 |
| Ammonia NH₃ | blasting (ammonium nitrate) | 25 ppm | 35 ppm | NIOSH 25 (10 h) / 35 (15 min); IDLH 300 |
| Hydrogen H₂ | battery charging bays | 0.4 % | 1 % | 10 % / 25 % of the lower explosive limit (4 %) |
| Wet-bulb temperature | deep hot, humid workings | 30.5 °C | 33.5 °C | CMR 2017 reg. 153(2) |

Sources: Coal Mines Regulations 2017 reg. 153(2) (indiankanoon.org/doc/24960800); 30 CFR 75.323 (law.cornell.edu/cfr/text/30/75.323); NIOSH Pocket Guide / IDLH values (cdc.gov/niosh/npg, cdc.gov/niosh/idlh); OSHA chemical data for CO (osha.gov/chemicaldata/462). Check the values against the latest DGMS circulars before using the system in a real mine.

## Which sensor for which gas

| Gas | Prototype (cheap, analog — indicative only) | Final product (accurate) |
|---|---|---|
| CH₄ | MQ-4 | NDIR methane module (e.g. Winsen MH-440D) or catalytic pellistor |
| CO | MQ-7 | electrochemical CO cell / module (e.g. Winsen ZE07-CO, ME2-CO) |
| H₂S | MQ-136 | electrochemical H₂S (e.g. ZE03-H2S / ME3-H2S) |
| O₂ | — (MQ cannot measure it) | electrochemical O₂ cell (e.g. ME2-O2 / ZE03-O2) |
| CO₂ | MQ-135 (very rough) | NDIR CO₂ (e.g. MH-Z19C, Sensirion SCD41) |
| NO₂, SO₂, NH₃ | MQ-135 (NH₃ only, rough) | electrochemical cells / ZE03 modules |
| H₂ | MQ-8 | electrochemical H₂ |

MQ sensors react to several gases at once and drift with temperature and humidity, so their ppm values are estimates. The hub already accepts direct readings (`"direct": {"O2": 20.8, "CO": 3}` in a repeater status) for sensors that report the value themselves — that is the path for the V4 boards.
