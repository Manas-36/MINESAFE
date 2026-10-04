# Radio protocol (MS_VER 3)

All radio traffic is **ESP-NOW broadcast** on the hotspot's Wi-Fi channel. Every packet starts with `"MS"`, the version and a type byte.

## Body telemetry (`MS_TELEM`, 54 bytes, once per second)
| Field | Type | Unit / meaning |
|---|---|---|
| node | char[10] | body ID, e.g. `BODY-01` |
| boot | uint16 | random per power-on (detects restarts) |
| seq | uint32 | serial number (packet loss) |
| tObj, tAmb | int16 | body / air temperature, 0.01 °C |
| ax, ay, az | int16 | acceleration, mg |
| gx, gy, gz | int16 | rotation, 0.1 °/s |
| flags | uint16 | 1 fall · 2 no movement · 4 impact · 8 SOS · 16 motion-sensor fault · 32 temp-sensor fault · 64 alert LED on · 128 phone test |
| uptime | uint32 | s |
| nearRep, nearRssi | uint8, int8 | strongest repeater heard, dBm |
| hum | uint16 | 0.01 % RH, 0xFFFF = none |
| steps | uint16 | step counter since power-on |
| head | int16 | heading, 0.1° clockwise from power-on direction, 0x7FFF = none |
| alt | int16 | height change from power-on, dm, 0x7FFF = none |
| hr, spo2 | uint8 | bpm, % (0 = none) |

Older, shorter packets are accepted: missing fields read as "none".

## Repeater beacon (`MS_BEACON`, every second)
`rep`, `hop` (255 = no route), `espCh`, `alertId`, `level`, `target[10]` (`*` = everyone).

## Uplink (`MS_UP`)
Header: `senderHop`, `kind` (1 body telemetry, 2 repeater status), `bodyRssi`, `pathLen`, `path[8]`, followed by the inner packet. A repeater only forwards a copy that came from a deeper hop, and drops duplicates by hash.

## Main repeater → hub
`POST /api/telemetry` (JSON) every second:
```json
{"repeater":"REP-01","gateway":true,
 "packets":[{"node":"BODY-01","seq":12,"bt":4711,"to":3650,"ta":3100,"ax":0,"ay":0,"az":1000,
             "gx":0,"gy":0,"gz":0,"fl":0,"up":12,"rssi":-55,"near":"REP-02","near_rssi":-58,
             "hu":65535,"st":42,"hd":900,"al":-30,"hr":78,"sp":97,"path":["REP-02","REP-01"]}],
 "statuses":[{"id":"REP-02","hop":1,"parent":"REP-01","prssi":-70,"alert_id":0,"buzzing":false,
              "up":300,"bodies":120,"nbrs":2,"gas_mv":820,"gas_warm":false,"gas_alarm":false,
              "gas_missing":false,"path":["REP-02","REP-01"],"air_t":29.84,"air_h":76.20}],
 "alert_id":0,"buzzing":false,"wifi_rssi":-50,"esp_ch":6,"ip":"10.180.64.239","uptime":300}
```
`air_t` (°C) and `air_h` (% RH) come from the repeater's AHT sensor (v3.1); both are `null` when no sensor is connected. Over ESP-NOW they travel inside the repeater status as `int16 airT` (0.01 °C, 0x7FFF = none) and `uint16 airH` (0.01 % RH, 0xFFFF = none), appended to the V2 status so older repeaters still decode.

Reply: `{"ok":true,"alert":{"id":1790000000,"level":1,"target":"*"}}` — the repeater adopts any newer alert ID and passes it down in its beacons.
