# Fake repeater chain for testing the admin hub without any hardware.
#   python sim_repeater.py                        (hub on this laptop)
#   python sim_repeater.py http://127.0.0.1:5000  (faster on Windows)
#
# Simulates the mine layout:
#     Admin <-WiFi- REP-01 (main) <-802.15.4- REP-02 <-802.15.4- REP-03   (deepest)
#   BODY-01 starts near REP-01 and walks deeper to REP-02 after ~60 s
#   BODY-02 works near REP-03, falls after ~40 s, then lies still
#   BODY-03 works near REP-02, body temperature slowly rises (warning at 38 C)
# Only the main repeater talks to the hub, exactly like the real one: it posts
# every second with the body packets and the status of every repeater in the chain.
# When you press ALERT, the fake repeaters start "buzzing" one hop at a time and
# the fake body units report their red LED on. Stop with Ctrl+C.

import json
import math
import random
import sys
import time
import urllib.request

HUB = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000").rstrip("/")
F_FALL, F_NOMOTION, F_IMPACT, F_SOS, F_MPU, F_TEMP, F_LED = 1, 2, 4, 8, 16, 32, 64

CHAIN = {  # repeater -> (hops to main, parent)
    "REP-01": (0, "ADMIN"),
    "REP-02": (1, "REP-01"),
    "REP-03": (2, "REP-02"),
}
bodies = {
    "BODY-01": {"seq": 0, "temp": 36.4, "bt": random.randint(1, 65535)},
    "BODY-02": {"seq": 0, "temp": 36.7, "bt": random.randint(1, 65535)},
    "BODY-03": {"seq": 0, "temp": 37.2, "bt": random.randint(1, 65535)},
}
alert = {"id": 0, "level": 0, "target": "*"}
rep_alert = {r: (0, 0) for r in CHAIN}   # what each repeater currently knows: (id, level)
alert_seen_at = 0
start = time.time()


def path_from(rep):
    path = [rep]
    while CHAIN[path[-1]][1] != "ADMIN":
        path.append(CHAIN[path[-1]][1])
    return path


def nearest(bid, t):
    if bid == "BODY-01":
        return "REP-01" if t < 60 else "REP-02"
    return {"BODY-02": "REP-03", "BODY-03": "REP-02"}[bid]


def make_packet(bid, b, t):
    fl, gx, gy, gz = 0, 0.0, 0.0, 0.0
    if bid == "BODY-02" and t > 40:
        ax, ay, az = 0.98, 0.02, 0.05                     # lying on the side, not moving
        fl |= F_FALL | (F_NOMOTION if t > 85 else 0)
    else:
        step = math.sin(t * 6)
        ax, ay, az = 0.15 * step, 0.08 * math.cos(t * 3), 1 + 0.25 * abs(step)
        gx, gy, gz = 30 * step, 12 * math.cos(t * 2), 5 * random.uniform(-1, 1)
    if bid == "BODY-03":
        b["temp"] = min(39.8, 37.2 + t * 0.015)
    near = nearest(bid, t)
    rid, lvl = rep_alert[near]                            # the body hears the alert from its repeater
    if lvl and alert["target"] in ("*", bid):
        fl |= F_LED
    b["seq"] += 1
    rssi = random.randint(-72, -50)
    return {"node": bid, "seq": b["seq"], "bt": b["bt"],
            "to": int((b["temp"] + random.uniform(-0.05, 0.05)) * 100), "ta": 2950,
            "ax": int(ax * 1000), "ay": int(ay * 1000), "az": int(az * 1000),
            "gx": int(gx * 10), "gy": int(gy * 10), "gz": int(gz * 10),
            "fl": fl, "up": int(t), "rssi": rssi, "near": near, "near_rssi": rssi,
            "path": path_from(near)}


def statuses(t):
    out = []
    for rep, (hop, parent) in CHAIN.items():
        aid, lvl = rep_alert[rep]
        out.append({"id": rep, "hop": hop, "parent": parent, "prssi": random.randint(-80, -60),
                    "alert_id": aid, "buzzing": bool(lvl), "up": int(t), "bodies": int(t) * 2,
                    "nbrs": 2 if rep == "REP-02" else 1, "path": path_from(rep)})
    return out


print(f"Simulating main repeater REP-01 + chain REP-02, REP-03 and 3 body units -> {HUB}   (Ctrl+C to stop)")
while True:
    t = time.time() - start
    # the alert walks down the chain one hop per second, like real beacons
    for rep, (hop, _) in CHAIN.items():
        if time.time() - alert_seen_at >= hop:
            rep_alert[rep] = (alert["id"], alert["level"])
    body = {"repeater": "REP-01", "gateway": True,
            "packets": [make_packet(bid, b, t) for bid, b in bodies.items()],
            "statuses": statuses(t), "alert_id": rep_alert["REP-01"][0],
            "buzzing": bool(rep_alert["REP-01"][1]), "wifi_rssi": random.randint(-60, -48),
            "esp_ch": 6, "uptime": int(t)}
    try:
        req = urllib.request.Request(HUB + "/api/telemetry", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r:
            a = json.load(r).get("alert", {})
        if a.get("id") != alert["id"]:
            alert.update(a)
            alert_seen_at = time.time()
            print("ALERT" if a.get("level") else "CLEAR", "target:", a.get("target"))
    except OSError as e:
        print("hub not reachable:", e)
    time.sleep(1)
