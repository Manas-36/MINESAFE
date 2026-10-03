# Setup and testing

## 1. Network
- Phone hotspot, **2.4 GHz**, WPA2 (Wi-Fi 6 off if the ESP32 cannot connect). Laptop joins it.
- Laptop IP: `ipconfig` → *Wireless LAN adapter Wi-Fi* → IPv4. Android picks a new hotspot subnet now and then; the main repeater searches the subnet for the hub by itself when its configured IP stops answering.
- Windows: set the hotspot network to **Private** and allow Python through the firewall.

## 2. Admin hub
```bash
cd hub
pip install -r requirements.txt
python admin_hub.py
```
Open http://localhost:5000 and keep the window open. Data is saved next to the script in `data/` and `photos/`.

AI kit check (optional): `pip install ultralytics`; the pose and PPE models download on first run. Add 3–6 reference photos of your own helmet and vest on the *Kit check (AI)* tab.

## 3. Firmware (Arduino IDE, ESP32 core 3.x)
| Setting | Value |
|---|---|
| Board | ESP32S3 Dev Module / XIAO_ESP32C6 |
| USB CDC On Boot | Enabled |
| Serial Monitor | 115200 baud |

- `repeater_node`: copy `secrets.example.h` → `secrets.h`. Main repeater `IS_GATEWAY 1`, `REPEATER_NO 1`; tunnel repeaters `IS_GATEWAY 0`, `REPEATER_NO` 2, 3, 4 …
  `GAS_ENABLED 0` if no gas sensor is fitted. Buzzer options: `BUZZER_PASSIVE`, `BUZZER_ACTIVE_LOW`; type `b` in Serial Monitor for a 1 s buzzer test.
- `body_node`: set `BODY_ID` (must match the admin page). Wear or hold upright and keep still for 3 s at power-on (gyro zero).
- `entry_station`: copy `secrets.example.h` → `secrets.h`.
- Body and repeater share one packet format — flash both after updating either.

## 4. Map
1. *Map* tab → **Mine plan…** (PNG/JPG; PDF → screenshot first). Or skip and draw on the grid.
2. **Set hub (0,0,0)** → click the entry.
3. **Set scale** → click two points, type the real distance.
4. **Draw tunnel** along each tunnel; Enter to finish.
5. **Place** each repeater where it is mounted; set its height z.

## 5. Test without a body unit
1. Phone on the hotspot → `http://<repeater IP>/` (IP shown on the Serial Monitor and the Network tab).
2. PHONE-01 appears on *Live*. Try Fall, SOS, heart-rate slider.
3. Walk buttons (5 steps, 90°, Auto walk) move the dot on the map.
4. ALERT on the laptop → phone LED circle lights, repeater buzzes.

Or with no hardware at all: `python tools/sim_repeater.py`, or **▶ Demo walker** on the Map tab.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Repeaters 0/0 | `HUB_URL` wrong, admin hub not running, or firewall. From the phone, open `http://<laptop IP>:5000`. |
| `hub error -1` | Firewall / Public network profile. |
| Buzzer silent | `b` test; try `BUZZER_PASSIVE 1` or `BUZZER_ACTIVE_LOW 1`; check wiring. |
| Gas alarm in clean air | New MQ sensors need burn-in; backup alarm 4000 mV; *Calibrate in clean air* after 10–15 min. |
| Garbage on Serial Monitor | Baud must be 115200. |
| MAX board not found | Check its 1.8 V / 3V3 jumper; keep it on the same bus as the GY-521. |
| No body temperature | 4.7 kΩ pull-up missing on the DS18B20 data line. |
