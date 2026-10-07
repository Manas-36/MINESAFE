# Running MineSafe from your Desktop\MINESAFE folder (Windows)

## 1. Folder layout
Download the repository from GitHub (Code → Download ZIP) and unzip it so it looks like this:
```
Desktop\MINESAFE\
  hub\admin_hub.py          <- the admin website (control room)
  hub\requirements.txt
  tools\sim_repeater.py     <- fake repeaters for testing without hardware
  firmware\repeater_node\   <- repeater code (+ your secrets.h)
  firmware\body_node\       <- body unit code
  firmware\entry_station\   <- scanning station code (+ your secrets.h)
  docs\                     <- wiring, limits, BOM
```
Keep `secrets.h` files on your laptop only (they hold the Wi-Fi password).

## 2. One-time setup
1. Install **Python 3.11 or newer** from python.org — tick **"Add python.exe to PATH"**.
2. Open **Command Prompt** and run:
```
cd %USERPROFILE%\Desktop\MINESAFE\hub
pip install -r requirements.txt
pip install ultralytics
```
(`ultralytics` is only for the AI kit check; the rest works without it.)
3. Arduino IDE 2.x → Boards Manager → **esp32 by Espressif (3.x)**. Library Manager → Adafruit PN532, Adafruit SSD1306, Adafruit GFX (scanning station only).

## 3. Every time
1. Turn on the phone hotspot (2.4 GHz). Connect the laptop to it.
2. Start the hub:
```
cd %USERPROFILE%\Desktop\MINESAFE\hub
python admin_hub.py
```
   Allow Python through the Windows firewall (**Private networks**) the first time.
3. Open **http://localhost:5000** in Chrome. Keep the Command Prompt window open.
4. Find the laptop IP for the ESPs: `ipconfig` → Wireless LAN adapter Wi-Fi → IPv4 Address. Put it in `HUB_URL` / `ADMIN_URL` in the `secrets.h` files (the repeater and station also find a changed IP by themselves).
5. Power the main repeater (REP-01) first, then the tunnel repeaters, the body units and the scanning station.

## 4. Test without hardware
In a second Command Prompt:
```
cd %USERPROFILE%\Desktop\MINESAFE\tools
python sim_repeater.py http://127.0.0.1:5000 gas
```
Three fake repeaters (each with 3 gas sensors + AHT) and three workers appear; with `gas` methane rises at REP-03 after ~45 s.

## 5. First-time set-up on the website
1. **Map** → Mine plan… → Set hub (0,0,0) → Set scale → Draw tunnel → Place each repeater.
2. **🚪 Exit** → click every exit (shaft, adit, refuge chamber) and name it.
3. Check each repeater's sign direction (amber arrow = where its ▶ points); press ⇄ if it is mounted the other way.
4. **Limits** → check the gas limits, pick the sensor on each gas channel (MQ-4 / MQ-7 / MQ-136), turn auto evacuation on or off → Save all limits.
5. **Register workers** → one entry per body unit.

## 6. In an emergency
- Automatic: a gas at its danger level starts the evacuation (if switched on) with that repeater's area as the danger zone.
- By hand: **Map → 🔥 Emergency** → click the spot → **START EVACUATION**.
- Every buzzer beeps, every body LED lights, every repeater sign shows the arrow and distance to the nearest safe exit, and the map draws each worker's route. **End evacuation** when everyone is out.
