# Stand-in for the repeater firmware's web server + hub uplink, used only to test the
# phone page and the JSON format end to end on a PC. Mirrors repeater_node.ino:
#   GET /            -> phone test page (extracted from the .ino)
#   GET /fake?...    -> builds a body packet like handleFake() and queues it
#   GET /status?id=  -> status JSON like statusJson()
#   every 1 s        -> POST /api/telemetry to the hub like postToHub()
import json, math, random, threading, time, urllib.request, urllib.parse, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HUB = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/api/telemetry"
PAGE = open(__file__.replace("mock_repeater.py", "page.html")).read().encode()
REP = "REP-01"
st = {"seq": 0, "boot": random.randint(1, 65535), "sent": 0, "alert": {"id": 0, "level": 0, "target": "*"},
      "hub_ok": 0, "hub_code": 0, "packets": []}
lock = threading.Lock()


def alert_for(i):
    a = st["alert"]
    return bool(a["level"]) and (a["target"] == "*" or a["target"].upper() == i)


def status(i):
    return {"rep": REP, "gateway": True, "hop": 0, "parent": "", "ch": 6,
            "hub_age": int((time.time() - st["hub_ok"]) * 1000) if st["hub_ok"] else -1,
            "hub_code": st["hub_code"], "gas_mv": 0, "gas_warm": False, "gas_missing": True,
            "led": alert_for(i), "sent": st["sent"]}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if u.path == "/":
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(PAGE); return
        i = (q.get("id") or "PHONE-01").upper()[:10]
        if u.path == "/fake":
            t, h, sc = float(q.get("t", 33)), float(q.get("h", 60)), int(q.get("s", 0))
            ph = time.time() * 6
            if sc in (1, 2):
                ax, ay, az, gx, gy, gz = 980, 20, 50, 0, 0, 0
            else:
                ax, ay, az = int(150 * math.sin(ph)), int(80 * math.cos(ph / 2)), int(1000 + 250 * abs(math.sin(ph)))
                gx, gy, gz = int(300 * math.sin(ph)), int(120 * math.cos(ph / 3)), random.randint(-50, 49)
            f = 128 | {1: 1, 2: 2, 3: 8, 4: 4, 5: 16}.get(sc, 0) | (64 if alert_for(i) else 0)
            with lock:
                st["seq"] += 1; st["sent"] += 1
                st["packets"].append({"node": i, "seq": st["seq"], "bt": st["boot"], "to": int(t * 100), "ta": int(t * 100),
                                      "ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz, "fl": f,
                                      "up": int(time.time()) % 100000, "rssi": -40, "near": REP, "near_rssi": -40,
                                      "hu": int(h * 100), "st": int(q.get("st", 0)), "hd": int(q.get("hd", 32767)),
                                      "al": int(float(q.get("al", 32767))), "path": [REP]})
        body = json.dumps(status(i)).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(body)


def uplink():
    while True:
        time.sleep(1)
        with lock:
            pk, st["packets"] = st["packets"], []
        body = {"repeater": REP, "gateway": True, "packets": pk,
                "statuses": [{"id": REP, "hop": 0, "parent": "", "prssi": -127, "alert_id": st["alert"]["id"],
                              "buzzing": bool(st["alert"]["level"]), "up": 10, "bodies": st["sent"], "nbrs": 0,
                              "gas_mv": 0, "gas_warm": False, "gas_alarm": False, "gas_missing": True, "path": [REP]}],
                "alert_id": st["alert"]["id"], "buzzing": bool(st["alert"]["level"]), "radio_rx": 0, "tx_fail": 0,
                "wifi_rssi": -55, "esp_ch": 6, "ip": "127.0.0.1", "uptime": 10}
        try:
            r = urllib.request.urlopen(urllib.request.Request(HUB, json.dumps(body).encode(),
                                                              {"Content-Type": "application/json"}), timeout=3)
            st["hub_code"] = r.status
            st["hub_ok"] = time.time()
            st["alert"] = json.load(r).get("alert", st["alert"])
        except Exception as e:
            st["hub_code"] = -1
            print("hub:", e)


threading.Thread(target=uplink, daemon=True).start()
ThreadingHTTPServer(("127.0.0.1", 8081), H).serve_forever()
