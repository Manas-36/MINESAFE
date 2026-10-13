# Control-room website (admin hub)

The website is `hub/admin_hub.py` — one Python file (Flask) that serves every page below. It runs on the laptop, not on the internet: start it with `hub\start_admin.bat` (or `python admin_hub.py`) and open `http://localhost:5000`; phones on the same hotspot use `http://<laptop-ip>:5000` (see [run_on_laptop.md](run_on_laptop.md)).

Screens captured on 13 Oct 2026 (v3.4) with the [demo mine map](../tools/demo_map/), the repeater simulator (`tools/sim_repeater.py … gas`) and three **fictional demo workers**.

## Opening screen
![Splash](images/website/splash.png)

## Live — every worker as a card (body temperature, heart rate, signal, alarms)
![Live](images/website/live.png)

## Map — tunnel plan, workers, repeaters, exits
![Map](images/website/map.png)

## Evacuation — danger zone, safest route for every worker, arrow + distance on every exit sign
![Map during an evacuation](images/website/map_evac.png)

![Live during an evacuation](images/website/live_evac.png)

## Gas & air — every MQ channel per repeater, air temperature / humidity / wet-bulb
![Gas and air](images/website/gas.png)

## Limits — warning / danger / alarm level for every gas (CMR 2017, NIOSH / OSHA)
![Limits](images/website/limits.png)

## Network — the repeater chain and every body unit's route
![Network](images/website/network.png)

![Network during an evacuation](images/website/network_evac.png)

## Register workers
![Workers](images/website/workers.png)

## Entry check, kit check (AI) and incident log
![Entry check](images/website/entry.png)

![Kit check](images/website/kit.png)

![Incident log](images/website/log.png)

## Phone page (`/phone`) — entry photo for the kit check
<img src="images/website/phone.png" width="300" alt="Phone page">

## Body unit display (v3.4)
![Body unit OLED screens](images/body_oled_screens.png)
