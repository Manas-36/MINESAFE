# Competitive product analysis

Nine connected-worker / mining-safety products, checked against vendor websites in July 2026. Original report and presentation brief: [`source/`](source/).

## Feature matrix
✓ confirmed · ~ partial / not detailed · — not found in published material (conservative: unstated = absent)

| Product | AI vision PPE | Continuous vitals | Fall / unconscious | GPS-denied sub-metre location | Gas | Dashboard | Underground focus |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Teknovate MineGuard 360 | — | ✓ | ~ | ~ (tech unspecified) | ✓ | ✓ | ~ |
| MineARC GuardIAN | — | — | ~ | ~ (node / zone) | ✓ | ✓ | ✓ |
| Leantegra Safe Mining | — | — | — | ✓ (UWB) | ✓ | ✓ | ✓ |
| HaloTag (Mine Safe Global) | — | — | — | ~ (proximity only) | — | ~ | ✓ |
| EasyM2M SmartKavach | — | ~ (paired device) | ✓ | — (GPS / cellular) | — | ~ | — |
| Rajant Health (Q-Stat) | — | ✓ | ✓ | ~ (mesh proximity) | ~ | ✓ | ✓ |
| ANTAR IoT Mining | — | ~ | ~ | — | ✓ | ✓ | ~ |
| 36Zero + Bodytrak | ~ (image alerts) | ✓ | ✓ | — | — | ✓ | ~ |
| Jarsh Safety | — | ~ | ✓ (DownAlert) | — | — | ✓ | ~ |
| **MineSafe pilot design** | ✓ YOLO | ✓ | ✓ | ✓ UWB + IMU | ✓ | ✓ | ✓ |
| **MineSafe prototype (built)** | ✓ YOLOv8 + RFID tags | ✓ HR, SpO₂, temp | ✓ IMU rules | ~ IMU dead reckoning + check-points | ✓ MQ per repeater | ✓ | ✓ |

## Each product in one line
| Product | Strength | Flaw | How MineSafe differs |
|---|---|---|---|
| [Teknovate MineGuard 360](https://www.teknovate.in/smart-mining) | Broadest feature list on paper | No accuracy data, location tech not disclosed, no camera PPE | Stated location method + AI PPE layer |
| [MineARC GuardIAN](https://guardian.minearc.com/) | Field-proven gas + refuge chambers | Cap-lamp zone tracking; no vitals | Continuous position + vitals |
| [Leantegra](https://leantegra.com/) | Best positioning (sub-metre UWB, ATEX) | No PPE, no vitals | Adds PPE verification + vitals |
| [HaloTag](https://minesafeglobal.com/collision-prevention-avoidance-systems-mining/) | Collision avoidance (ISO 21815, Level 9 braking) | Proximity is its only sensing | Covers PPE + health; can coexist with a CAS |
| [SmartKavach](https://easym2m.in/smartkavach/) | Fall detection + SOS | GPS / 2G-3G — fails underground | Works without GPS or cellular |
| [Rajant Health](https://rajanthealth.com/) | Best mesh network + vitals wearable | "Compliance" = tag presence; mesh-proximity location | Object-level PPE check + map position |
| [ANTAR IoT](https://antariot.com/mining-2/) | — | Generic page, no named hardware | Every part named and justified |
| [36Zero](https://36zero.io/) | Most validated (100,000+ workers) | Construction-focused; no underground positioning | Built for underground from day one |
| [Jarsh Safety](https://jarshsafety.com/) | Widest product catalogue | Separate products, no single integrated unit | One integrated wearable + dashboard |

## Gap
No product combines **(a)** AI vision PPE compliance, **(b)** continuous physiological monitoring, **(c)** GPS-denied localisation and **(d)** one real-time dashboard for underground mines. All nine sell through enterprise "request a demo" models with no public pricing — an opening for a low-cost design for India's smaller DGMS-regulated mines.

**Closest emerging competitor:** 36Zero's acquisition of Bodytrak (in-ear ATEX physiological sensors) to enter mining and oil & gas (2026).

## Positioning statement
> An integrated, low-cost, underground-mining-purpose-built wearable and dashboard system — the first to combine AI computer-vision PPE compliance detection, continuous multi-parameter physiological monitoring and GPS-denied localisation in a single architecture.

**Talking points**
- Lead with the integration gap; do not claim to beat Leantegra on positioning or HaloTag on collision avoidance.
- Second differentiator: cost (prototype ≈ ₹6,500 vs enterprise-only pricing).
- *"Why not buy Leantegra + Rajant together?"* — separate procurement, separate dashboards, no single source of truth, enterprise pricing.
- Feasibility: each sub-part (YOLO PPE, IMU/UWB location, low-cost vitals) is validated in the literature; the contribution is the integration.
