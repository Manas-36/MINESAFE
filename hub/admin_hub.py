# =====================================================================
#  MINER SAFETY - ADMIN HUB v3
#  pip install flask
#  python admin_hub.py
#
#  Laptop (admin)  : http://localhost:5000
#  Phone (camera)  : http://<laptop-ip>:5000/phone
#  Entry station   : POST /api/gear               (RFID gear scans/writes)
#  Repeaters       : POST /api/telemetry          (body packets in, alert state out)
#  Test without HW : python sim_repeater.py
#
#  Data flow
#   Body ESP --(802.15.4 radio, body ID + serial no.)--> Repeater --(WiFi/HTTP)--> this hub
#   Admin presses ALERT --> hub answers every repeater POST with the alert
#   --> repeaters buzz + broadcast alert frames --> body ESP turns its red LED on
#
#  Saved to disk: data/workers.json (registered workers), data/tags.json (gear tags),
#  photos/ (entry photos). Live readings are kept in memory only.
# =====================================================================

import json
import math
import os
import threading
import time
import uuid
from collections import deque
from datetime import datetime

from flask import (Flask, jsonify, redirect, render_template_string, request,
                   send_from_directory)

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE, "photos")
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

GEAR_LIST = ["HELMET", "VEST", "PANTS", "SHOES"]

# ---- danger thresholds (tune these for your sensors) ----------------
LIMITS = {
    "temp_warn_hi": 38.0,      # deg C, body temperature from MLX90614
    "temp_danger_hi": 39.5,
    "temp_warn_lo": 32.0,      # below this: sensor off the skin, or cold exposure
    "signal_warn_s": 10,       # no packet for this long -> WARNING
    "signal_danger_s": 60,     # no packet for this long -> DANGER
    "repeater_offline_s": 10,
}

# ---- flag bits sent by the body node (must match body_node.ino) ------
F_FALL, F_NOMOTION, F_IMPACT, F_SOS, F_MPU_FAULT, F_TEMP_FAULT, F_ALERT_LED = (
    1, 2, 4, 8, 16, 32, 64)
FLAG_NAMES = {F_FALL: "Fall detected", F_NOMOTION: "No movement",
              F_IMPACT: "Hard impact", F_SOS: "SOS pressed",
              F_MPU_FAULT: "Motion sensor fault", F_TEMP_FAULT: "Temp sensor fault",
              F_ALERT_LED: "Alert LED on"}

lock = threading.RLock()


def load(name, default):
    try:
        with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(name, obj):
    tmp = os.path.join(DATA_DIR, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, os.path.join(DATA_DIR, name))


def clock(t=None):
    return datetime.fromtimestamp(t or time.time()).strftime("%H:%M:%S")


# ---- state ------------------------------------------------------------
workers = load("workers.json", {})     # body_id -> worker record
registry = load("tags.json", {})       # tag uid -> gear
events = []                            # gear scan/write log
pending_scans = []                     # scans waiting for a photo
verifications = []                     # photo cards
cleared = {}                           # body_id -> entry approval

latest = {}                            # body_id -> last decoded packet
history = {}                           # body_id -> deque of samples
seqinfo = {}                           # body_id -> serial-number bookkeeping
repeaters = {}                         # repeater_id -> status
alert = {"id": 0, "level": 0, "target": "*", "msg": "", "time": None}
alert_log = []
incidents = []                         # status changes (SAFE -> DANGER etc.)
last_status = {}


# =====================================================================
#  Entry station (unchanged behaviour from v2)
# =====================================================================
@app.post("/api/gear")
def gear():
    d = request.get_json(force=True)
    uid, g, ev = d.get("uid"), d.get("gear"), d.get("event")
    with lock:
        if ev == "write":
            registry[uid] = g
            save("tags.json", registry)
            check = "ISSUED"
        else:
            reg = registry.get(uid)
            check = "UNKNOWN TAG" if reg is None else ("OK" if reg == g else "MISMATCH")
            pending_scans[:] = [s for s in pending_scans if s["uid"] != uid]
            pending_scans.append({"uid": uid, "gear": g, "check": check, "time": clock()})
        events.insert(0, {"time": clock(), "station": d.get("station"), "event": ev,
                          "uid": uid, "gear": g, "registered": registry.get(uid, "-"),
                          "check": check})
        del events[200:]
    return jsonify(ok=True, check=check)


PHONE = """
<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Entry Camera</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#0f1417;color:#e8eef0}
 h2{margin:0 0 12px} label{display:block;margin:14px 0 4px;font-size:14px;color:#9fb0b6}
 input[type=text]{width:100%;padding:12px;font-size:18px;border-radius:8px;border:0;box-sizing:border-box}
 .cam{display:block;background:#1f8a5b;color:#fff;text-align:center;padding:28px;border-radius:12px;font-size:22px;margin-top:16px}
 .cam input{display:none}
 img{width:100%;border-radius:12px;margin-top:12px;display:none}
 button{width:100%;padding:18px;font-size:20px;border:0;border-radius:12px;background:#2b6fd6;color:#fff;margin-top:16px}
 .scan{background:#1b2226;padding:10px;border-radius:8px;margin-top:6px;font-size:14px}
 .ok{color:#5fd68d} .bad{color:#ff6b6b} .msg{background:#1d3b2c;padding:14px;border-radius:8px;margin-bottom:12px}
</style>
<h2>Entry verification</h2>
{% if msg %}<div class="msg">{{msg}}</div>{% endif %}
<b>Gear scanned so far ({{scans|length}}):</b>
{% for s in scans %}
 <div class="scan">{{s.gear}} &middot; {{s.uid}} &middot;
   <span class="{{'ok' if s.check=='OK' else 'bad'}}">{{s.check}}</span></div>
{% else %}<div class="scan">None yet - tap gear tags on the reader first</div>{% endfor %}
<form method="post" action="/api/photo" enctype="multipart/form-data">
 <label>Body unit ID (sticker on the body ESP)</label>
 <input type="text" name="body_id" placeholder="e.g. BODY-01" required>
 <label>Worker ID (optional)</label>
 <input type="text" name="worker_id" placeholder="e.g. EMP-1042">
 <label class="cam">&#128247; Take photo
  <input type="file" name="photo" accept="image/*" capture="environment" required
         onchange="p.src=URL.createObjectURL(this.files[0]);p.style.display='block'">
 </label>
 <img id="p">
 <button type="submit">Send to admin</button>
</form>
"""


@app.get("/phone")
def phone():
    return render_template_string(PHONE, scans=pending_scans, msg=request.args.get("msg"))


@app.post("/api/photo")
def photo():
    f = request.files.get("photo")
    if not f:
        return "no photo", 400
    name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}.jpg"
    f.save(os.path.join(PHOTO_DIR, name))
    with lock:
        verifications.insert(0, {
            "id": uuid.uuid4().hex[:8], "time": clock(), "photo": name,
            "body_id": request.form.get("body_id", "").strip().upper(),
            "worker_id": request.form.get("worker_id", "").strip(),
            "scans": list(pending_scans), "status": "PENDING", "worker": "", "gear_ok": [],
        })
        del verifications[50:]
        pending_scans.clear()
    return redirect("/phone?msg=Sent! Waiting for admin approval.")


@app.get("/photos/<path:fn>")
def photos(fn):
    return send_from_directory(PHOTO_DIR, fn)


@app.post("/api/verify/<vid>")
def verify(vid):
    d = request.get_json(force=True)
    with lock:
        v = next((x for x in verifications if x["id"] == vid), None)
        if not v:
            return jsonify(ok=False, error="not found"), 404
        v["worker"] = d.get("worker", "").strip()
        v["worker_id"] = d.get("worker_id", v["worker_id"]).strip()
        v["body_id"] = d.get("body_id", v["body_id"]).strip().upper()
        v["gear_ok"] = [g for g in d.get("gear", []) if g in GEAR_LIST]
        if d.get("action") == "approve":
            v["status"] = "APPROVED"
            cleared[v["body_id"]] = {"worker": v["worker"], "worker_id": v["worker_id"],
                                     "gear": v["gear_ok"], "time": clock(), "photo": v["photo"]}
        else:
            v["status"] = "REJECTED"
            cleared.pop(v["body_id"], None)
    return jsonify(ok=True)


@app.post("/api/revoke/<body_id>")
def revoke(body_id):
    with lock:
        cleared.pop(body_id.upper(), None)
    return jsonify(ok=True)


@app.get("/api/body/<body_id>")
def body_status(body_id):
    c = cleared.get(body_id.upper())
    if not c:
        return jsonify(cleared=False)
    return jsonify(cleared=True, worker=c["worker"], worker_id=c["worker_id"], gear=c["gear"])


# =====================================================================
#  Workers
# =====================================================================
WORKER_FIELDS = ["name", "emp_id", "work", "zone", "blood", "allergies", "conditions",
                 "medication", "contact_name", "contact_phone", "notes"]


@app.post("/api/workers")
def upsert_worker():
    d = request.get_json(force=True)
    bid = str(d.get("body_id", "")).strip().upper()
    if not bid or not str(d.get("name", "")).strip():
        return jsonify(ok=False, error="Body ESP code and name are required"), 400
    old = str(d.get("original_id", "")).strip().upper()
    with lock:
        if old and old != bid:
            if bid in workers:
                return jsonify(ok=False, error=f"{bid} is already registered"), 400
            workers.pop(old, None)
        rec = workers.get(bid, {"registered": clock(), "registered_date": f"{datetime.now():%Y-%m-%d}"})
        rec["body_id"] = bid
        for k in WORKER_FIELDS:
            rec[k] = str(d.get(k, "")).strip()[:200]
        workers[bid] = rec
        save("workers.json", workers)
    return jsonify(ok=True, worker=rec)


@app.delete("/api/workers/<bid>")
def delete_worker(bid):
    with lock:
        workers.pop(bid.upper(), None)
        save("workers.json", workers)
    return jsonify(ok=True)


# =====================================================================
#  Repeaters -> telemetry in, alert out
# =====================================================================
def alert_payload():
    return {"id": alert["id"], "level": alert["level"], "target": alert["target"]}


def ingest(p, rep, now):
    """One body packet as forwarded by a repeater. Raw integer units:
    to/ta = 0.01 C, ax..az = milli-g, gx..gz = 0.1 deg/s, fl = flag bits."""
    try:
        bid = str(p["node"]).strip().upper()[:16]
        seq = int(p["seq"])
    except (KeyError, ValueError, TypeError):
        return
    if not bid:
        return
    rssi = int(p.get("rssi", -127))
    boot = int(p.get("bt", 0))             # random number the body picks at power-on
    si = seqinfo.setdefault(bid, {"last": -1, "rx": 0, "lost": 0, "boot": boot, "recent": {}})

    if boot != si["boot"]:                 # body restarted -> serial numbers start again
        si.update(boot=boot, last=-1, recent={})

    # same packet heard by a second repeater (within 5 s) -> only note the extra repeater
    seen = si["recent"].get(seq)
    if seen is not None and now - seen < 5:
        L = latest.get(bid)
        if L:
            L["heard_by"][rep] = rssi
            if rssi > L["rssi"]:
                L["rssi"], L["repeater"] = rssi, rep
        return
    if si["last"] >= 0 and seq <= si["last"]:
        if si["last"] - seq < 20:
            return                         # older packet arriving late - newer data already shown
        si["last"] = -1                    # counter jumped back (shouldn't happen) - resync
    if si["last"] >= 0:
        si["lost"] += min(seq - si["last"] - 1, 1000)
    si["last"] = seq
    si["rx"] += 1
    si["recent"][seq] = now
    if len(si["recent"]) > 64:
        for k in sorted(si["recent"], key=si["recent"].get)[:16]:
            del si["recent"][k]

    ax, ay, az = (int(p.get(k, 0)) for k in ("ax", "ay", "az"))
    gx, gy, gz = (int(p.get(k, 0)) for k in ("gx", "gy", "gz"))
    fl = int(p.get("fl", 0))
    temp = round(int(p.get("to", 0)) / 100, 2)
    amb = round(int(p.get("ta", 0)) / 100, 2)
    amag = round(math.sqrt(ax * ax + ay * ay + az * az) / 1000, 3)
    gmag = round(math.sqrt(gx * gx + gy * gy + gz * gz) / 10, 1)
    latest[bid] = {"seq": seq, "time": now, "repeater": rep, "rssi": rssi,
                   "heard_by": {rep: rssi}, "temp": temp, "amb": amb,
                   "ax": ax / 1000, "ay": ay / 1000, "az": az / 1000,
                   "gx": gx / 10, "gy": gy / 10, "gz": gz / 10,
                   "amag": amag, "gmag": gmag, "fl": fl, "up": int(p.get("up", 0))}
    h = history.setdefault(bid, deque(maxlen=900))
    h.append((round(now, 2), None if fl & F_TEMP_FAULT else temp,
              None if fl & F_MPU_FAULT else amag, None if fl & F_MPU_FAULT else gmag))


@app.post("/api/telemetry")
def telemetry():
    d = request.get_json(force=True, silent=True) or {}
    rep = str(d.get("repeater", "REP-?")).strip().upper()[:16]
    now = time.time()
    with lock:
        r = repeaters.setdefault(rep, {"id": rep, "first_seen": now, "posts": 0, "packets": 0})
        pk = d.get("packets", []) or []
        r.update(last_seen=now, ip=request.remote_addr, posts=r["posts"] + 1,
                 packets=r["packets"] + len(pk), alert_id=int(d.get("alert_id", 0)),
                 buzzing=bool(d.get("buzzing")), radio_rx=d.get("radio_rx"),
                 tx_fail=d.get("tx_fail"), uptime=d.get("uptime"), rssi=d.get("wifi_rssi"))
        for p in pk:
            ingest(p, rep, now)
        return jsonify(ok=True, alert=alert_payload())


# =====================================================================
#  Alerts
# =====================================================================
@app.post("/api/alert")
def raise_alert():
    d = request.get_json(force=True, silent=True) or {}
    target = str(d.get("target", "*")).strip().upper() or "*"
    msg = str(d.get("msg", "")).strip()[:80]
    with lock:
        alert.update(id=alert["id"] + 1, level=1, target=target, msg=msg, time=time.time())
        who = "ALL WORKERS" if target == "*" else f"{target} ({workers.get(target, {}).get('name', 'unregistered')})"
        alert_log.insert(0, {"time": clock(), "action": "ALERT", "target": who, "msg": msg})
        del alert_log[100:]
    return jsonify(ok=True, alert=alert_payload())


@app.post("/api/alert/clear")
def clear_alert():
    with lock:
        if alert["level"]:
            alert.update(id=alert["id"] + 1, level=0, time=time.time())
            alert_log.insert(0, {"time": clock(), "action": "CLEARED", "target": "", "msg": ""})
    return jsonify(ok=True, alert=alert_payload())


# =====================================================================
#  Danger evaluation
# =====================================================================
LEVELS = ["SAFE", "WARNING", "DANGER"]


def evaluate(bid, now):
    L = latest.get(bid)
    if not L:
        return "NO DATA", ["No readings received yet"]
    level, why = 0, []

    def bump(lv, text):
        nonlocal level
        level = max(level, lv)
        why.append(text)

    age = now - L["time"]
    if age > LIMITS["signal_danger_s"]:
        bump(2, f"No signal for {int(age)} s")
    elif age > LIMITS["signal_warn_s"]:
        bump(1, f"Signal lost {int(age)} s")
    fl = L["fl"]
    if fl & F_SOS:
        bump(2, "SOS button pressed")
    if fl & F_FALL:
        bump(2, "Fall detected")
    if fl & F_NOMOTION:
        bump(2, "No movement for 30 s")
    if fl & F_IMPACT:
        bump(1, "Hard impact")
    if fl & F_MPU_FAULT:
        bump(1, "Motion sensor not responding")
    if fl & F_TEMP_FAULT:
        bump(1, "Temperature sensor not responding")
    else:
        t = L["temp"]
        if t >= LIMITS["temp_danger_hi"]:
            bump(2, f"Body temp {t:.1f} °C")
        elif t >= LIMITS["temp_warn_hi"]:
            bump(1, f"Body temp high {t:.1f} °C")
        elif t <= LIMITS["temp_warn_lo"]:
            bump(1, f"Body temp low {t:.1f} °C")
    return LEVELS[level], why


def watchdog():
    """Logs status changes every second, even if no browser is open."""
    while True:
        now = time.time()
        with lock:
            for bid in set(workers) | set(latest):
                st, why = evaluate(bid, now)
                prev = last_status.get(bid)
                if prev is not None and st != prev and st != "NO DATA":
                    incidents.insert(0, {"t": now, "time": clock(now), "body_id": bid,
                                         "name": workers.get(bid, {}).get("name", "Unregistered"),
                                         "from": prev, "to": st, "why": ", ".join(why) or "Back to normal"})
                    del incidents[300:]
                last_status[bid] = st
        time.sleep(1)


# =====================================================================
#  Dashboard data
# =====================================================================
def live_view(bid, now):
    L = latest.get(bid)
    if not L:
        return None
    si = seqinfo.get(bid, {"rx": 0, "lost": 0})
    total = si["rx"] + si["lost"]
    return {"temp": L["temp"], "amb": L["amb"], "amag": L["amag"], "gmag": L["gmag"],
            "ax": L["ax"], "ay": L["ay"], "az": L["az"], "gx": L["gx"], "gy": L["gy"], "gz": L["gz"],
            "age": round(now - L["time"], 1), "seq": L["seq"], "rssi": L["rssi"],
            "repeater": L["repeater"], "heard_by": L["heard_by"], "fl": L["fl"],
            "flags": [n for b, n in FLAG_NAMES.items() if L["fl"] & b],
            "loss": round(100 * si["lost"] / total, 1) if total else 0, "rx": si["rx"],
            "up": L["up"]}


@app.get("/api/state")
def state():
    now = time.time()
    with lock:
        ws = []
        for bid, w in workers.items():
            st, why = evaluate(bid, now)
            ws.append({**w, "status": st, "reasons": why, "live": live_view(bid, now),
                       "cleared": cleared.get(bid)})
        order = {"DANGER": 0, "WARNING": 1, "NO DATA": 2, "SAFE": 3}
        ws.sort(key=lambda x: (order.get(x["status"], 9), x["name"].lower()))
        unknown = []
        for bid in latest:
            if bid not in workers:
                st, why = evaluate(bid, now)
                unknown.append({"body_id": bid, "status": st, "reasons": why, "live": live_view(bid, now)})
        reps = []
        for r in repeaters.values():
            age = now - r["last_seen"]
            reps.append({**r, "age": round(age, 1), "online": age < LIMITS["repeater_offline_s"]})
        reps.sort(key=lambda r: r["id"])
        online = [r for r in reps if r["online"]]
        a = dict(alert)
        if a["level"]:
            tgt = a["target"]
            a["rep_ack"] = sum(1 for r in online if r.get("alert_id") == a["id"] and r.get("buzzing"))
            a["rep_total"] = len(online)
            targets = [w for w in ws if tgt == "*" or w["body_id"] == tgt]
            a["led_ack"] = sum(1 for w in targets if w["live"] and w["live"]["age"] < 10 and w["live"]["fl"] & F_ALERT_LED)
            a["led_total"] = len(targets)
            a["target_name"] = "All workers" if tgt == "*" else workers.get(tgt, {}).get("name", tgt)
            a["since"] = clock(a["time"])
        summary = {k: sum(1 for w in ws if w["status"] == k) for k in ("SAFE", "WARNING", "DANGER", "NO DATA")}
        return jsonify(
            now=now, clock=clock(now), alert=a, summary=summary, workers=ws, unknown=unknown,
            repeaters=reps, incidents=incidents[:60], alert_log=alert_log[:30],
            verifications=verifications[:20], cleared=cleared, events=events[:40],
            pending_scans=len(pending_scans), gear_list=GEAR_LIST, limits=LIMITS)


@app.get("/api/worker/<bid>/history")
def worker_history(bid):
    n = min(int(request.args.get("n", 240)), 900)
    with lock:
        h = list(history.get(bid.upper(), []))[-n:]
    now = time.time()
    return jsonify(t=[round(x[0] - now, 1) for x in h], temp=[x[1] for x in h],
                   amag=[x[2] for x in h], gmag=[x[3] for x in h])


@app.get("/")
def index():
    return DASHBOARD


# =====================================================================
#  Dashboard page (plain HTML + JS, no internet needed)
# =====================================================================
DASHBOARD = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mine Safety Control Room</title>
<style>
:root{
  --bg:#0e1316; --panel:#161d21; --panel2:#1c252a; --line:#2a353b; --ink:#e7eef0; --muted:#8fa2a9;
  --safe:#35c47c; --warn:#f0b429; --danger:#ff4d4f; --info:#4c9bf0; --nodata:#6b7a80;
  --font:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; --mono:ui-monospace,Consolas,Menlo,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);font-size:15px}
button{font:inherit;cursor:pointer}
input,select,textarea{font:inherit;color:var(--ink);background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:9px 10px;width:100%}
input:focus,select:focus,textarea:focus,button:focus-visible{outline:2px solid var(--info);outline-offset:1px}
label{display:grid;gap:5px;font-size:13px;color:var(--muted)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
/* top bar */
.top{position:sticky;top:0;z-index:20;background:#0b1013ee;backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;gap:14px;padding:10px 18px;flex-wrap:wrap}
.brand{font-weight:800;letter-spacing:.04em;font-size:17px;display:flex;align-items:center;gap:8px}
.brand i{width:10px;height:10px;border-radius:50%;background:var(--safe);box-shadow:0 0 10px var(--safe)}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{display:flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;background:var(--panel);border:1px solid var(--line);font-size:13px;cursor:pointer}
.chip b{font-size:15px}.chip .d{width:8px;height:8px;border-radius:50%}
.spacer{flex:1}
.clock{font-family:var(--mono);color:var(--muted)}
.btn{border:1px solid var(--line);background:var(--panel2);color:var(--ink);padding:9px 14px;border-radius:9px;font-weight:600}
.btn:hover{border-color:var(--muted)}
.btn.red{background:var(--danger);border-color:var(--danger);color:#fff}
.btn.red:hover{filter:brightness(1.1)}
.btn.green{background:var(--safe);border-color:var(--safe);color:#062414}
.btn.ghost{background:transparent}
.btn.small{padding:5px 10px;font-size:13px}
.alertbtn{font-size:16px;padding:10px 18px;letter-spacing:.05em}
nav{display:flex;gap:4px;padding:0 14px;overflow-x:auto}
nav button{background:none;border:0;color:var(--muted);padding:10px 12px;border-bottom:2px solid transparent;font-weight:600;white-space:nowrap}
nav button.on{color:var(--ink);border-bottom-color:var(--info)}
nav .n{background:var(--danger);color:#fff;border-radius:999px;padding:0 6px;font-size:11px;margin-left:4px}
/* alert banner */
.banner{display:none;background:repeating-linear-gradient(45deg,#7a1416,#7a1416 14px,#8f1a1c 14px,#8f1a1c 28px);padding:12px 18px;align-items:center;gap:16px;flex-wrap:wrap;animation:pulse 1.2s infinite}
.banner.on{display:flex}
.banner b{font-size:18px;letter-spacing:.06em}
@keyframes pulse{50%{filter:brightness(1.25)}}
@media (prefers-reduced-motion:reduce){.banner{animation:none}}
main{padding:18px;max-width:1400px;margin:0 auto}
.view{display:none}.view.on{display:block}
h2{margin:0 0 12px;font-size:19px}
h3{margin:0 0 8px;font-size:15px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.empty{color:var(--muted);padding:30px;text-align:center;border:1px dashed var(--line);border-radius:12px}
/* worker cards */
.card{background:var(--panel);border:1px solid var(--line);border-left:5px solid var(--nodata);border-radius:12px;padding:14px;cursor:pointer;display:grid;gap:10px;transition:transform .12s}
.card:hover{transform:translateY(-2px);border-color:var(--muted)}
.card.SAFE{border-left-color:var(--safe)}.card.WARNING{border-left-color:var(--warn)}
.card.DANGER{border-left-color:var(--danger);box-shadow:0 0 0 1px var(--danger),0 0 22px #ff4d4f40}
.card .head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.card .name{font-weight:700;font-size:16px}
.card .sub{color:var(--muted);font-size:13px}
.pill{font-size:11px;font-weight:800;letter-spacing:.06em;padding:4px 8px;border-radius:999px;white-space:nowrap}
.pill.SAFE{background:#35c47c22;color:var(--safe)}.pill.WARNING{background:#f0b42922;color:var(--warn)}
.pill.DANGER{background:var(--danger);color:#fff}.pill.NO{background:#6b7a8033;color:var(--muted)}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.metric{background:var(--panel2);border-radius:8px;padding:8px}
.metric small{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.metric span{font-family:var(--mono);font-size:18px;font-weight:600}
.reasons{font-size:13px;color:var(--warn);min-height:18px}
.card.DANGER .reasons{color:#ff8a8c;font-weight:600}
.tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:11px;padding:3px 7px;border-radius:6px;background:var(--panel2);color:var(--muted);border:1px solid var(--line)}
.tag.ok{color:var(--safe);border-color:#35c47c55}.tag.red{color:#fff;background:var(--danger);border-color:var(--danger)}
.sig{display:inline-flex;gap:2px;align-items:flex-end;height:12px;vertical-align:middle}
.sig i{width:3px;background:var(--line);border-radius:1px}.sig i.on{background:var(--safe)}
/* drawer */
.shade{position:fixed;inset:0;background:#0008;z-index:30;display:none}
.shade.on{display:block}
.drawer{position:fixed;top:0;right:0;height:100%;width:min(640px,100%);background:var(--bg);border-left:1px solid var(--line);z-index:31;transform:translateX(100%);transition:transform .2s;overflow-y:auto;padding:18px;display:grid;gap:14px;align-content:start}
.drawer.on{transform:none}
.dhead{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.dhead .name{font-size:22px;font-weight:800}
.aid{display:grid;grid-template-columns:110px 1fr;gap:14px;background:#2a1215;border:1px solid #5a1f24;border-radius:12px;padding:14px}
.blood{background:var(--danger);color:#fff;border-radius:10px;display:grid;place-items:center;text-align:center;padding:8px}
.blood b{font-size:34px;line-height:1}.blood small{font-size:11px;letter-spacing:.08em}
.kv{display:grid;grid-template-columns:120px 1fr;gap:4px 10px;font-size:14px}
.kv dt{color:var(--muted)}.kv dd{margin:0}
.chart{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.chart .ct{display:flex;justify-content:space-between;font-size:13px;color:var(--muted);margin-bottom:4px}
.chart .ct b{color:var(--ink);font-family:var(--mono)}
canvas{width:100%;height:120px;display:block}
.axes{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
/* tables */
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;background:var(--panel)}
tr:last-child td{border-bottom:0}
tr.bad td{background:#ff4d4f14}
/* forms */
.two{display:grid;grid-template-columns:minmax(300px,420px) 1fr;gap:18px;align-items:start}
@media (max-width:900px){.two{grid-template-columns:1fr}}
.form{display:grid;gap:10px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.note{font-size:13px;color:var(--muted)}
.err{color:#ff8a8c;font-size:14px;min-height:18px}
/* verification cards */
.vcard{display:grid;grid-template-columns:200px 1fr;gap:14px;background:var(--panel);border:1px solid var(--line);border-left:5px solid var(--warn);border-radius:12px;padding:12px;margin-bottom:12px}
.vcard.APPROVED{border-left-color:var(--safe)}.vcard.REJECTED{border-left-color:var(--danger)}
.vcard img{width:200px;height:200px;object-fit:cover;border-radius:8px}
@media (max-width:600px){.vcard{grid-template-columns:1fr}.vcard img{width:100%}}
.checks{display:flex;gap:12px;flex-wrap:wrap}.checks label{display:flex;flex-direction:row;align-items:center;gap:6px;color:var(--ink)}
.checks input{width:auto}
/* modal + toast */
.modal{position:fixed;inset:0;z-index:40;display:none;place-items:center;background:#000a;padding:16px}
.modal.on{display:grid}
.mbox{background:var(--panel);border:1px solid var(--danger);border-radius:14px;padding:20px;width:min(460px,100%);display:grid;gap:12px}
.toasts{position:fixed;bottom:16px;right:16px;z-index:50;display:grid;gap:8px;width:min(360px,calc(100% - 32px))}
.toast{background:var(--panel2);border:1px solid var(--line);border-left:5px solid var(--danger);border-radius:10px;padding:12px;box-shadow:0 8px 24px #0008;cursor:pointer}
.toast.WARNING{border-left-color:var(--warn)}.toast.SAFE{border-left-color:var(--safe)}
</style></head>
<body>
<div class="top">
  <div class="bar">
    <div class="brand"><i id="live-dot"></i>MINE SAFETY · CONTROL ROOM</div>
    <div class="chips" id="chips"></div>
    <div class="spacer"></div>
    <span class="clock" id="clock">--:--:--</span>
    <button class="btn red alertbtn" id="alert-open">⚠ ALERT</button>
  </div>
  <div class="banner" id="banner">
    <b>⚠ ALERT ACTIVE</b><span id="banner-text"></span><div class="spacer"></div>
    <button class="btn" id="alert-clear">Clear alert</button>
  </div>
  <nav id="tabs">
    <button data-v="live" class="on">Live</button>
    <button data-v="workers">Register workers</button>
    <button data-v="entry">Entry check <span class="n" id="n-entry" hidden></span></button>
    <button data-v="network">Network</button>
    <button data-v="log">Incident log</button>
  </nav>
</div>

<main>
  <section class="view on" id="v-live">
    <div id="unknown-hint"></div>
    <div class="grid" id="cards"></div>
  </section>

  <section class="view" id="v-workers">
    <div class="two">
      <div class="panel">
        <h2 id="form-title">Register a worker</h2>
        <form class="form" id="wform" autocomplete="off">
          <input type="hidden" id="f-original">
          <label>Body ESP code *<input id="f-body_id" placeholder="BODY-01" required list="bodylist"></label>
          <datalist id="bodylist"></datalist>
          <label>Full name *<input id="f-name" required></label>
          <div class="row2">
            <label>Employee ID<input id="f-emp_id"></label>
            <label>Blood group
              <select id="f-blood"><option value="">Unknown</option>
                <option>A+</option><option>A-</option><option>B+</option><option>B-</option>
                <option>AB+</option><option>AB-</option><option>O+</option><option>O-</option></select></label>
          </div>
          <div class="row2">
            <label>Work assigned<input id="f-work" placeholder="Drilling, haulage..."></label>
            <label>Zone / level<input id="f-zone" placeholder="Level 2, Section B"></label>
          </div>
          <label>Allergies<input id="f-allergies" placeholder="e.g. Penicillin, none"></label>
          <label>Medical conditions<input id="f-conditions" placeholder="e.g. Asthma, diabetes, none"></label>
          <label>Regular medication<input id="f-medication"></label>
          <div class="row2">
            <label>Emergency contact<input id="f-contact_name"></label>
            <label>Contact phone<input id="f-contact_phone" inputmode="tel"></label>
          </div>
          <label>Notes for rescuers<textarea id="f-notes" rows="2"></textarea></label>
          <div class="err" id="f-err"></div>
          <div style="display:flex;gap:8px"><button class="btn green" type="submit" id="f-save">Register worker</button>
          <button class="btn ghost" type="button" id="f-reset">Clear form</button></div>
        </form>
      </div>
      <div>
        <h2>Registered workers</h2>
        <div class="tbl"><table><thead><tr><th>Body ESP</th><th>Name</th><th>Work</th><th>Blood</th><th>Contact</th><th></th></tr></thead>
        <tbody id="wtable"></tbody></table></div>
        <p class="note">Body ESPs that are sending data but aren't registered appear in the Body ESP code box suggestions.</p>
      </div>
    </div>
  </section>

  <section class="view" id="v-entry">
    <h2>Photo verifications</h2>
    <p class="note">Phone camera page: <span class="mono" id="phone-url"></span></p>
    <div id="vcards"></div>
    <h2 style="margin-top:22px">Cleared body units</h2>
    <div class="tbl"><table><thead><tr><th>Body ID</th><th>Worker</th><th>ID</th><th>Gear</th><th>Since</th><th></th></tr></thead><tbody id="ctable"></tbody></table></div>
    <h2 style="margin-top:22px">Gear tag events <span class="note" id="pending-note"></span></h2>
    <div class="tbl"><table><thead><tr><th>Time</th><th>Station</th><th>Event</th><th>UID</th><th>Gear</th><th>Registry</th><th>Check</th></tr></thead><tbody id="etable"></tbody></table></div>
  </section>

  <section class="view" id="v-network">
    <h2>Repeaters</h2>
    <div class="tbl"><table><thead><tr><th>Repeater</th><th>Status</th><th>Last seen</th><th>Packets</th><th>WiFi</th><th>Buzzer</th><th>IP</th></tr></thead><tbody id="rtable"></tbody></table></div>
    <h2 style="margin-top:22px">Body units on air</h2>
    <div class="tbl"><table><thead><tr><th>Body ESP</th><th>Worker</th><th>Last packet</th><th>Serial no.</th><th>Packet loss</th><th>Best repeater</th><th>Heard by</th></tr></thead><tbody id="btable"></tbody></table></div>
  </section>

  <section class="view" id="v-log">
    <div class="two">
      <div><h2>Status changes</h2><div class="tbl"><table><thead><tr><th>Time</th><th>Worker</th><th>Change</th><th>Reason</th></tr></thead><tbody id="itable"></tbody></table></div></div>
      <div><h2>Alerts sent</h2><div class="tbl"><table style="min-width:300px"><thead><tr><th>Time</th><th>Action</th><th>Target</th></tr></thead><tbody id="atable"></tbody></table></div></div>
    </div>
  </section>
</main>

<div class="shade" id="shade"></div>
<aside class="drawer" id="drawer" aria-label="Worker details"></aside>

<div class="modal" id="modal">
  <div class="mbox">
    <h2 style="color:var(--danger)">Send danger alert</h2>
    <label>Who gets the alert
      <select id="a-target"></select></label>
    <label>Note for the log (optional)<input id="a-msg" placeholder="Gas leak, Level 2"></label>
    <p class="note">All repeaters start buzzing and the selected workers' body units turn their red LED on.</p>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button class="btn ghost" id="a-cancel">Cancel</button>
      <button class="btn red" id="a-send">Send alert</button>
    </div>
  </div>
</div>
<div class="toasts" id="toasts"></div>

<script>
const $ = s => document.querySelector(s);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let S = null, openId = null, lastIncidentT = 0, audioCtx = null, drawn = {};
const statusCls = s => s === "NO DATA" ? "NO" : s;
const api = (url, body, method) => fetch(url, {method: method || (body ? "POST" : "GET"),
  headers: {"Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined}).then(r => r.json());

/* ---------- tabs ---------- */
function showTab(v){
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("on", b.dataset.v === v));
  document.querySelectorAll(".view").forEach(x => x.classList.toggle("on", x.id === "v-" + v));
  history.replaceState(null, "", "#" + v);
}
$("#tabs").onclick = e => { const b = e.target.closest("button"); if (b) showTab(b.dataset.v); };
if (location.hash.length > 1 && $("#v-" + location.hash.slice(1))) showTab(location.hash.slice(1));

/* ---------- sound (browser needs one click first) ---------- */
document.addEventListener("click", () => { if (!audioCtx) try { audioCtx = new AudioContext(); } catch(e){} }, {once:true});
function beep(){ if (!audioCtx) return; const o = audioCtx.createOscillator(), g = audioCtx.createGain();
  o.frequency.value = 880; o.connect(g); g.connect(audioCtx.destination); g.gain.value = .15;
  o.start(); o.stop(audioCtx.currentTime + .35); }
function toast(html, cls, onclick){ const t = document.createElement("div"); t.className = "toast " + (cls||"");
  t.innerHTML = html; t.onclick = () => { t.remove(); onclick && onclick(); }; $("#toasts").prepend(t);
  setTimeout(() => t.remove(), 12000); }

/* ---------- helpers ---------- */
function sig(rssi){ const n = rssi >= -60 ? 4 : rssi >= -70 ? 3 : rssi >= -80 ? 2 : rssi >= -90 ? 1 : 0;
  return `<span class="sig" title="${rssi} dBm">${[4,7,10,12].map((h,i)=>`<i style="height:${h}px" class="${i<n?'on':''}"></i>`).join("")}</span>`; }
const ago = s => s == null ? "–" : s < 2 ? "now" : s < 60 ? Math.round(s) + " s ago" : Math.round(s/60) + " min ago";
const fmt = (v, d=1) => v == null ? "–" : Number(v).toFixed(d);
function setIfChanged(el, key, html){ if (drawn[el] !== key){ drawn[el] = key; $(el).innerHTML = html(); } }

/* ---------- render ---------- */
function render(){
  $("#clock").textContent = S.clock;
  const sm = S.summary;
  $("#chips").innerHTML = [["SAFE","var(--safe)","Safe"],["WARNING","var(--warn)","Warning"],["DANGER","var(--danger)","Danger"],["NO DATA","var(--nodata)","No data"]]
    .map(([k,c,l]) => `<span class="chip" onclick="showTab('live')"><span class="d" style="background:${c}"></span>${l} <b>${sm[k]}</b></span>`).join("")
    + `<span class="chip" onclick="showTab('network')">Repeaters <b>${S.repeaters.filter(r=>r.online).length}/${S.repeaters.length}</b></span>`;
  $("#live-dot").style.background = sm.DANGER ? "var(--danger)" : sm.WARNING ? "var(--warn)" : "var(--safe)";

  // alert banner
  const a = S.alert;
  $("#banner").classList.toggle("on", !!a.level);
  if (a.level) $("#banner-text").innerHTML = `${esc(a.target_name)} · since ${esc(a.since)}${a.msg ? " · " + esc(a.msg) : ""}
     · Repeaters buzzing <b class="mono">${a.rep_ack}/${a.rep_total}</b> · Red LED confirmed <b class="mono">${a.led_ack}/${a.led_total}</b>`;

  // live cards
  $("#cards").innerHTML = S.workers.length ? S.workers.map(card).join("") :
    `<div class="empty">No workers registered yet. Open <b>Register workers</b> to add the first one.</div>`;
  $("#unknown-hint").innerHTML = S.unknown.length ? `<div class="panel" style="margin-bottom:14px;border-color:var(--warn)">
     <b style="color:var(--warn)">Unregistered body units on air:</b> ${S.unknown.map(u =>
     `<button class="btn small" onclick="prefill('${esc(u.body_id)}')">${esc(u.body_id)} → Register</button>`).join(" ")}</div>` : "";

  // workers table + datalist
  setIfChanged("#wtable", JSON.stringify(S.workers.map(w=>[w.body_id,w.name,w.work,w.blood,w.contact_phone])), () =>
    S.workers.length ? S.workers.map(w => `<tr><td class="mono">${esc(w.body_id)}</td><td>${esc(w.name)}</td><td>${esc(w.work)}</td>
      <td><b>${esc(w.blood||"–")}</b></td><td>${esc(w.contact_name)} ${esc(w.contact_phone)}</td>
      <td style="white-space:nowrap"><button class="btn small" onclick="editWorker('${esc(w.body_id)}')">Edit</button>
      <button class="btn small ghost" onclick="delWorker('${esc(w.body_id)}')">Delete</button></td></tr>`).join("")
      : `<tr><td colspan="6" class="note">Nobody registered yet.</td></tr>`);
  $("#bodylist").innerHTML = S.unknown.map(u => `<option value="${esc(u.body_id)}">`).join("");

  // entry
  $("#phone-url").textContent = location.origin.replace("localhost", "<laptop-ip>").replace("127.0.0.1","<laptop-ip>") + "/phone";
  const pend = S.verifications.filter(v => v.status === "PENDING").length;
  $("#n-entry").hidden = !pend; $("#n-entry").textContent = pend;
  setIfChanged("#vcards", JSON.stringify(S.verifications.map(v=>[v.id,v.status])), () =>
    S.verifications.length ? S.verifications.map(vcard).join("") : `<div class="empty">No photos yet. Open the phone camera page on your mobile.</div>`);
  $("#ctable").innerHTML = Object.entries(S.cleared).map(([b,c]) => `<tr><td class="mono">${esc(b)}</td><td>${esc(c.worker)}</td>
     <td>${esc(c.worker_id)}</td><td>${esc(c.gear.join(", "))}</td><td>${esc(c.time)}</td>
     <td><button class="btn small ghost" onclick="revoke('${esc(b)}')">Revoke</button></td></tr>`).join("") || `<tr><td colspan="6" class="note">None yet.</td></tr>`;
  $("#pending-note").textContent = S.pending_scans ? `· ${S.pending_scans} scan(s) waiting for a photo` : "";
  $("#etable").innerHTML = S.events.map(e => `<tr class="${["OK","ISSUED"].includes(e.check)?"":"bad"}"><td>${esc(e.time)}</td><td>${esc(e.station)}</td>
     <td>${esc(e.event)}</td><td class="mono">${esc(e.uid)}</td><td>${esc(e.gear)}</td><td>${esc(e.registered)}</td><td>${esc(e.check)}</td></tr>`).join("")
     || `<tr><td colspan="7" class="note">No tag scans yet.</td></tr>`;

  // network
  $("#rtable").innerHTML = S.repeaters.map(r => `<tr class="${r.online?"":"bad"}"><td class="mono"><b>${esc(r.id)}</b></td>
     <td>${r.online ? '<span class="pill SAFE">ONLINE</span>' : '<span class="pill DANGER">OFFLINE</span>'}</td>
     <td>${ago(r.age)}</td><td class="mono">${r.packets}</td><td>${r.rssi != null ? sig(r.rssi) + " " + r.rssi + " dBm" : "–"}</td>
     <td>${r.buzzing ? '<span class="tag red">BUZZING</span>' : "quiet"}</td><td class="mono">${esc(r.ip)}</td></tr>`).join("")
     || `<tr><td colspan="7" class="note">No repeater has connected yet. Power one on, or run <span class="mono">python sim_repeater.py</span>.</td></tr>`;
  const all = [...S.workers.map(w=>({id:w.body_id,name:w.name,live:w.live})), ...S.unknown.map(u=>({id:u.body_id,name:"(unregistered)",live:u.live}))].filter(x=>x.live);
  $("#btable").innerHTML = all.map(x => `<tr><td class="mono">${esc(x.id)}</td><td>${esc(x.name)}</td><td>${ago(x.live.age)}</td>
     <td class="mono">#${x.live.seq}</td><td class="mono">${x.live.loss}%</td><td>${esc(x.live.repeater)} ${sig(x.live.rssi)}</td>
     <td class="mono">${Object.entries(x.live.heard_by).map(([r,s])=>esc(r)+" ("+s+")").join(", ")}</td></tr>`).join("")
     || `<tr><td colspan="7" class="note">No body units heard yet.</td></tr>`;

  // log
  $("#itable").innerHTML = S.incidents.map(i => `<tr class="${i.to==="DANGER"?"bad":""}"><td>${esc(i.time)}</td><td>${esc(i.name)} <span class="note mono">${esc(i.body_id)}</span></td>
     <td><span class="pill ${statusCls(i.from)}">${esc(i.from)}</span> → <span class="pill ${statusCls(i.to)}">${esc(i.to)}</span></td><td>${esc(i.why)}</td></tr>`).join("")
     || `<tr><td colspan="4" class="note">No status changes yet.</td></tr>`;
  $("#atable").innerHTML = S.alert_log.map(l => `<tr><td>${esc(l.time)}</td><td><b>${esc(l.action)}</b></td><td>${esc(l.target)} ${esc(l.msg)}</td></tr>`).join("")
     || `<tr><td colspan="3" class="note">No alerts sent.</td></tr>`;

  // new incidents -> toast + beep
  const fresh = S.incidents.filter(i => i.t > lastIncidentT);
  if (lastIncidentT) fresh.reverse().forEach(i => {
    toast(`<b>${esc(i.name)}</b> is now <b>${esc(i.to)}</b><br><span class="note">${esc(i.why)}</span>`, i.to, () => openWorker(i.body_id));
    if (i.to === "DANGER") beep();
  });
  if (S.incidents.length) lastIncidentT = Math.max(lastIncidentT, S.incidents[0].t); else if (!lastIncidentT) lastIncidentT = S.now;

  if (openId) renderDrawer();
}

function card(w){
  const L = w.live;
  return `<div class="card ${statusCls(w.status)}" onclick="openWorker('${esc(w.body_id)}')" tabindex="0">
    <div class="head"><div><div class="name">${esc(w.name)}</div><div class="sub">${esc(w.work || "No work assigned")} · <span class="mono">${esc(w.body_id)}</span></div></div>
      <span class="pill ${statusCls(w.status)}">${esc(w.status)}</span></div>
    <div class="metrics">
      <div class="metric"><small>Body temp</small><span>${L ? fmt(L.temp) : "–"}</span> °C</div>
      <div class="metric"><small>Motion</small><span>${L ? fmt(L.amag,2) : "–"}</span> g</div>
      <div class="metric"><small>Signal</small>${L ? sig(L.rssi) : ""} <span style="font-size:13px">${L ? ago(L.age) : "–"}</span></div>
    </div>
    <div class="reasons">${esc(w.reasons.join(" · "))}</div>
    <div class="tags">${w.cleared ? '<span class="tag ok">Entry cleared ✓</span>' : '<span class="tag">Entry not verified</span>'}
      <span class="tag">Blood ${esc(w.blood || "?")}</span>${L && (L.fl & 64) ? '<span class="tag red">LED ALERT ON</span>' : ""}
      ${L ? `<span class="tag">${esc(L.repeater)}</span>` : ""}</div>
  </div>`;
}

function vcard(v){
  const scanned = v.scans.filter(s => s.check === "OK").map(s => s.gear);
  const pending = v.status === "PENDING";
  return `<div class="vcard ${v.status}" id="vc-${v.id}">
    <a href="/photos/${esc(v.photo)}" target="_blank"><img src="/photos/${esc(v.photo)}" alt="Entry photo"></a>
    <div class="form">
      <div><span class="pill ${v.status==="APPROVED"?"SAFE":v.status==="REJECTED"?"DANGER":"WARNING"}">${esc(v.status)}</span> <span class="note">${esc(v.time)}</span></div>
      <div><b>Gear scanned:</b> ${v.scans.length ? v.scans.map(s => `<span class="tag ${s.check==="OK"?"ok":"red"}">${esc(s.gear)} · ${esc(s.check)}</span>`).join(" ") : '<span class="tag red">No gear scanned</span>'}</div>
      ${pending ? `
        <div class="row2"><label>Worker name<input class="v-worker" value="${esc((S.workers.find(w=>w.body_id===v.body_id)||{}).name||"")}"></label>
          <label>Body unit ID<input class="v-body" value="${esc(v.body_id)}"></label></div>
        <label>Worker ID<input class="v-wid" value="${esc(v.worker_id)}"></label>
        <div class="checks">${S.gear_list.map(g => `<label><input type="checkbox" value="${g}" ${scanned.includes(g)?"checked":""}> ${g}</label>`).join("")}</div>
        <div style="display:flex;gap:8px"><button class="btn green" onclick="decide('${v.id}','approve')">Approve</button>
          <button class="btn ghost" onclick="decide('${v.id}','reject')">Reject</button></div>`
      : `<div class="kv"><dt>Worker</dt><dd>${esc(v.worker||"–")} ${esc(v.worker_id)}</dd><dt>Body unit</dt><dd class="mono">${esc(v.body_id)}</dd>
          <dt>Gear confirmed</dt><dd>${esc(v.gear_ok.join(", ") || "none")}</dd></div>`}
    </div></div>`;
}

/* ---------- worker drawer ---------- */
function openWorker(id){ openId = id; drawn.drawer = null; $("#drawer").classList.add("on"); $("#shade").classList.add("on"); renderDrawer(); loadHistory(); }
function closeWorker(){ openId = null; $("#drawer").classList.remove("on"); $("#shade").classList.remove("on"); }
$("#shade").onclick = closeWorker;
document.addEventListener("keydown", e => { if (e.key === "Escape") { closeWorker(); $("#modal").classList.remove("on"); } });

function renderDrawer(){
  const w = S.workers.find(x => x.body_id === openId);
  if (!w) { const u = S.unknown.find(x => x.body_id === openId); if (!u) return closeWorker(); }
  const x = w || {body_id: openId, name: "Unregistered unit", status: "NO DATA", reasons: [], live: null};
  const L = x.live;
  const key = JSON.stringify([x.body_id, x.name, x.status, x.blood, x.allergies, x.conditions, x.medication, x.contact_name, x.contact_phone, x.notes, x.cleared && x.cleared.time]);
  if (drawn.drawer !== key){
    drawn.drawer = key;
    $("#drawer").innerHTML = `
      <div class="dhead"><div><div class="name">${esc(x.name)}</div>
        <div class="note">${esc(x.work||"")} ${x.zone ? "· " + esc(x.zone) : ""} · <span class="mono">${esc(x.body_id)}</span> ${x.emp_id ? "· " + esc(x.emp_id) : ""}</div></div>
        <button class="btn ghost" onclick="closeWorker()" aria-label="Close">✕</button></div>
      <div id="d-status"></div>
      <div class="aid"><div class="blood"><small>BLOOD</small><b>${esc(x.blood || "?")}</b></div>
        <dl class="kv"><dt>Allergies</dt><dd>${esc(x.allergies || "–")}</dd><dt>Conditions</dt><dd>${esc(x.conditions || "–")}</dd>
          <dt>Medication</dt><dd>${esc(x.medication || "–")}</dd><dt>Emergency</dt><dd>${esc(x.contact_name || "–")} <b class="mono">${esc(x.contact_phone || "")}</b></dd>
          ${x.notes ? `<dt>Notes</dt><dd>${esc(x.notes)}</dd>` : ""}</dl></div>
      <div id="d-live"></div>
      <div class="chart"><div class="ct"><span>Body temperature (°C) · last 4 min</span><b id="c-temp-v"></b></div><canvas id="c-temp"></canvas></div>
      <div class="chart"><div class="ct"><span>Acceleration (g) · 1 g = still</span><b id="c-acc-v"></b></div><canvas id="c-acc"></canvas></div>
      <div class="chart"><div class="ct"><span>Rotation (°/s)</span><b id="c-gyro-v"></b></div><canvas id="c-gyro"></canvas></div>
      <div class="panel"><h3>Entry check</h3>${x.cleared ? `<div style="display:flex;gap:12px;align-items:center">
          ${x.cleared.photo ? `<img src="/photos/${esc(x.cleared.photo)}" style="width:80px;height:80px;object-fit:cover;border-radius:8px">` : ""}
          <div>Cleared at ${esc(x.cleared.time)}<br>Gear: <b>${esc(x.cleared.gear.join(", ") || "none")}</b></div></div>` : `<span class="note">Not verified at the entry today.</span>`}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn red" onclick="sendAlert('${esc(x.body_id)}')">⚠ Alert this worker</button>
        ${w ? `<button class="btn" onclick="closeWorker();editWorker('${esc(x.body_id)}')">Edit details</button>` : `<button class="btn green" onclick="closeWorker();prefill('${esc(x.body_id)}')">Register this unit</button>`}
      </div>`;
  }
  $("#d-status").innerHTML = `<div class="panel" style="border-color:${x.status==="DANGER"?"var(--danger)":x.status==="WARNING"?"var(--warn)":"var(--line)"}">
      <span class="pill ${statusCls(x.status)}">${esc(x.status)}</span> <span style="margin-left:8px">${esc(x.reasons.join(" · ") || "All readings normal")}</span></div>`;
  $("#d-live").innerHTML = L ? `<div class="axes">
      <div class="metric"><small>Body temp</small><span>${fmt(L.temp)}</span> °C</div>
      <div class="metric"><small>Air temp</small><span>${fmt(L.amb)}</span> °C</div>
      <div class="metric"><small>Last packet</small><span style="font-size:15px">${ago(L.age)}</span></div>
      <div class="metric"><small>Accel X / Y / Z (g)</small><span style="font-size:14px">${fmt(L.ax,2)} / ${fmt(L.ay,2)} / ${fmt(L.az,2)}</span></div>
      <div class="metric"><small>Gyro X / Y / Z (°/s)</small><span style="font-size:14px">${fmt(L.gx,0)} / ${fmt(L.gy,0)} / ${fmt(L.gz,0)}</span></div>
      <div class="metric"><small>Radio</small><span style="font-size:14px">${esc(L.repeater)} ${sig(L.rssi)} #${L.seq}</span></div></div>
      <div class="tags" style="margin-top:8px">${L.flags.map(f => `<span class="tag ${f==="Alert LED on"||f.includes("fault")?"":"red"}">${esc(f)}</span>`).join("") || '<span class="tag ok">No flags</span>'}
      <span class="tag">Packet loss ${L.loss}%</span><span class="tag">Up ${Math.round(L.up/60)} min</span></div>`
    : `<div class="empty">No readings from ${esc(x.body_id)} yet. Switch the body unit on near a repeater.</div>`;
}

async function loadHistory(){
  if (!openId) return;
  try {
    const h = await api(`/api/worker/${encodeURIComponent(openId)}/history?n=240`);
    const L = (S.workers.find(w=>w.body_id===openId)||S.unknown.find(u=>u.body_id===openId)||{}).live;
    drawChart("#c-temp", h.t, h.temp, "#ff7a45", [S.limits.temp_warn_lo, S.limits.temp_warn_hi, S.limits.temp_danger_hi]);
    drawChart("#c-acc", h.t, h.amag, "#4c9bf0", [1]);
    drawChart("#c-gyro", h.t, h.gmag, "#b37feb", []);
    if (L){ $("#c-temp-v").textContent = fmt(L.temp) + " °C"; $("#c-acc-v").textContent = fmt(L.amag,2) + " g"; $("#c-gyro-v").textContent = fmt(L.gmag,0) + " °/s"; }
  } catch(e){}
}

function drawChart(sel, t, v, color, refs){
  const c = $(sel); if (!c) return;
  const dpr = window.devicePixelRatio || 1, W = c.clientWidth, H = c.clientHeight;
  c.width = W * dpr; c.height = H * dpr; const g = c.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0,0,W,H);
  const pts = t.map((x,i) => [x, v[i]]).filter(p => p[1] != null);
  const css = getComputedStyle(document.body);
  g.font = "11px " + css.getPropertyValue("--mono"); g.fillStyle = css.getPropertyValue("--muted");
  if (pts.length < 2){ g.fillText("Waiting for data…", 8, H/2); return; }
  let lo = Math.min(...pts.map(p=>p[1]), ...refs), hi = Math.max(...pts.map(p=>p[1]), ...refs);
  if (hi - lo < 1e-6){ hi += 1; lo -= 1; } const pad = (hi-lo)*.12; lo -= pad; hi += pad;
  const x0 = Math.min(-60, pts[0][0]), L = 40, X = x => L + (x - x0) / (0 - x0) * (W - L - 6), Y = y => 6 + (hi - y) / (hi - lo) * (H - 22);
  g.strokeStyle = css.getPropertyValue("--line"); g.lineWidth = 1;
  [lo + pad, (lo+hi)/2, hi - pad].forEach(y => { g.beginPath(); g.moveTo(L, Y(y)); g.lineTo(W-6, Y(y)); g.stroke(); g.fillText(y.toFixed(1), 2, Y(y)+4); });
  g.setLineDash([4,4]); g.strokeStyle = "#f0b42999"; refs.forEach(r => { g.beginPath(); g.moveTo(L, Y(r)); g.lineTo(W-6, Y(r)); g.stroke(); }); g.setLineDash([]);
  g.fillText(Math.round(x0) + " s", L, H-4); g.fillText("now", W-30, H-4);
  g.strokeStyle = color; g.lineWidth = 2; g.beginPath(); pts.forEach((p,i) => i ? g.lineTo(X(p[0]), Y(p[1])) : g.moveTo(X(p[0]), Y(p[1]))); g.stroke();
  const last = pts[pts.length-1]; g.fillStyle = color; g.beginPath(); g.arc(X(last[0]), Y(last[1]), 3.5, 0, 7); g.fill();
}

/* ---------- worker form ---------- */
const FIELDS = ["body_id","name","emp_id","work","zone","blood","allergies","conditions","medication","contact_name","contact_phone","notes"];
function fillForm(w){ FIELDS.forEach(f => $("#f-"+f).value = w[f] || ""); $("#f-original").value = w.body_id || "";
  $("#form-title").textContent = w.body_id && S.workers.some(x=>x.body_id===w.body_id) ? "Edit " + (w.name||w.body_id) : "Register a worker";
  $("#f-save").textContent = $("#f-original").value && S.workers.some(x=>x.body_id===$("#f-original").value) ? "Save changes" : "Register worker"; $("#f-err").textContent = ""; }
function editWorker(id){ showTab("workers"); fillForm(S.workers.find(w => w.body_id === id) || {}); $("#f-name").focus(); }
function prefill(id){ showTab("workers"); fillForm({body_id: id}); $("#f-original").value = ""; $("#f-name").focus(); }
$("#f-reset").onclick = () => fillForm({});
$("#wform").onsubmit = async e => {
  e.preventDefault(); const body = {original_id: $("#f-original").value};
  FIELDS.forEach(f => body[f] = $("#f-"+f).value);
  const r = await api("/api/workers", body);
  if (!r.ok) { $("#f-err").textContent = r.error; return; }
  toast(`<b>${esc(r.worker.name)}</b> saved with body unit <span class="mono">${esc(r.worker.body_id)}</span>`, "SAFE");
  fillForm({}); poll();
};
async function delWorker(id){ const w = S.workers.find(x=>x.body_id===id);
  const row = event.target.closest("td"); if (row.dataset.confirm !== "1"){ row.dataset.confirm = "1"; event.target.textContent = "Confirm delete"; event.target.classList.add("red"); setTimeout(()=>{drawn["#wtable"]=null;},4000); return; }
  await api("/api/workers/" + encodeURIComponent(id), null, "DELETE"); toast(`Removed ${esc(w ? w.name : id)}`, "WARNING"); poll(); }

/* ---------- entry ---------- */
async function decide(vid, action){
  const c = $("#vc-" + vid);
  const body = {action, worker: c.querySelector(".v-worker").value, body_id: c.querySelector(".v-body").value,
    worker_id: c.querySelector(".v-wid").value, gear: [...c.querySelectorAll(".checks input:checked")].map(i=>i.value)};
  if (action === "approve" && !body.worker.trim()) { c.querySelector(".v-worker").focus(); return toast("Type the worker's name before approving.", "WARNING"); }
  await api("/api/verify/" + vid, body); drawn["#vcards"] = null; poll();
}
async function revoke(b){ await api("/api/revoke/" + encodeURIComponent(b), {}); poll(); }

/* ---------- alerts ---------- */
function sendAlert(target){
  $("#a-target").innerHTML = `<option value="*">ALL workers</option>` + S.workers.map(w => `<option value="${esc(w.body_id)}">${esc(w.name)} (${esc(w.body_id)})</option>`).join("");
  $("#a-target").value = target || "*"; $("#a-msg").value = ""; $("#modal").classList.add("on"); $("#a-send").focus();
}
$("#alert-open").onclick = () => sendAlert("*");
$("#a-cancel").onclick = () => $("#modal").classList.remove("on");
$("#a-send").onclick = async () => { await api("/api/alert", {target: $("#a-target").value, msg: $("#a-msg").value});
  $("#modal").classList.remove("on"); toast("<b>Alert sent.</b> Repeaters will start buzzing within 1–2 seconds."); poll(); };
$("#alert-clear").onclick = async () => { await api("/api/alert/clear", {}); toast("Alert cleared.", "SAFE"); poll(); };

/* ---------- polling ---------- */
let polling = false;
async function poll(){
  if (polling) return; polling = true;
  try { S = await api("/api/state"); render(); $("#live-dot").style.opacity = 1; }
  catch(e){ $("#clock").textContent = "hub offline"; $("#live-dot").style.opacity = .3; }
  polling = false;
}
poll(); setInterval(poll, 1000); setInterval(loadHistory, 2000);
</script>
</body></html>
"""


if __name__ == "__main__":
    threading.Thread(target=watchdog, daemon=True).start()
    print("Admin hub running:  http://localhost:5000   (phone: http://<laptop-ip>:5000/phone)")
    app.run(host="0.0.0.0", port=5000, threaded=True)
