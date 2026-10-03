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
#   Body ESP32-S3 --(ESP-NOW, body ID + serial no.)--> nearest repeater
#   --(802.15.4, hop by hop)--> main repeater --(WiFi/HTTP)--> this hub
#   Admin presses ALERT --> hub answers the main repeater's POST with the alert
#   --> alert travels down the chain in beacons --> every repeater buzzes
#   --> body units hear it in the repeater "hello" --> red LED on
#
#  AI kit check: photos from the phone page or the "Kit check" tab are checked with
#  a person/pose model + a YOLOv8 PPE model + YOUR reference photos (Kit check tab).
#  Needs:  pip install ultralytics   (the model files download by themselves on first run)
#
#  MAP (Map tab): upload the mine plan, click the hub = (0,0,0), set the scale, place the
#  repeaters, draw the tunnels. Body units send step count + gyro heading (+ pressure height);
#  the hub walks each worker's dot from the hub, keeps it inside the tunnels and resets
#  the drift every time the worker passes close to a repeater. "Demo walker" = no hardware.
#
#  GAS (Gas & air tab): each repeater's MQ sensor voltage -> sensor resistance Rs -> Rs/R0
#  -> estimated ppm of every gas on that sensor's datasheet curve.
#
#  Saved to disk: data/workers.json (registered workers), data/tags.json (gear tags),
#  data/map.json + data/map/ (map), data/gas.json (gas sensor setup),
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

import urllib.parse
import urllib.request

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
    "hr_warn_lo": 50, "hr_warn_hi": 120,       # heart rate (bpm) - only when the body unit measures it
    "hr_danger_lo": 40, "hr_danger_hi": 150,
    "spo2_warn": 92, "spo2_danger": 88,        # blood oxygen % (estimate from the MAX3010x)
    "signal_warn_s": 10,       # no packet for this long -> WARNING
    "signal_danger_s": 60,     # no packet for this long -> DANGER
    "repeater_offline_s": 10,       # main repeater (posts every second)
    "mesh_repeater_offline_s": 20,  # tunnel repeaters (report every 5 s through the chain)
    "gas_alarm_mv": 4000,           # raw sensor output (mV) that always raises the alert - set it on the Gas & air tab
}

# ---- flag bits sent by the body node (must match body_node.ino) ------
F_FALL, F_NOMOTION, F_IMPACT, F_SOS, F_MPU_FAULT, F_TEMP_FAULT, F_ALERT_LED = (
    1, 2, 4, 8, 16, 32, 64)
NONE16 = 0x7FFF                        # "no value" for heading / height
F_TEST = 128                           # packet made by a repeater's phone test page
FLAG_NAMES = {F_FALL: "Fall detected", F_NOMOTION: "No movement",
              F_IMPACT: "Hard impact", F_SOS: "SOS pressed",
              F_MPU_FAULT: "Motion sensor fault", F_TEMP_FAULT: "Temp sensor fault",
              F_ALERT_LED: "Alert LED on"}

lock = threading.RLock()
GAS_REALERT_S = 60                     # still high 60 s after an admin clears it -> alert again

# ---- AI kit check ---------------------------------------------------------
# Three parts, all running on this laptop:
#  1. Pose model (yolov8n-pose)  - finds the person and their eyes / shoulders / hips,
#     so we know exactly where a helmet and a vest should be ("zones").
#  2. PPE model (YOLOv8, 6 classes) - finds helmet, vest, safety shoes, gloves, goggles, mask.
#     Anything it finds that is NOT on the person (e.g. a yellow chair) is ignored.
#  3. Your reference photos - the colours of YOUR helmet and vest, learned from photos
#     of a worker wearing the correct kit. A zone that matches counts as found.
MODEL_DIR = os.path.join(BASE, "models")
REF_DIR = os.path.join(DATA_DIR, "kit_refs")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REF_DIR, exist_ok=True)
PPE_MODEL = os.path.join(MODEL_DIR, "ppe_best.pt")
PPE_MODEL_URL = "https://huggingface.co/Tanishjain9/yolov8n-ppe-detection-6classes/resolve/main/best.pt"
POSE_MODEL = os.path.join(MODEL_DIR, "yolov8n-pose.pt")   # downloads by itself from GitHub
KIT_REQUIRED = ["HELMET", "VEST", "SHOES"]          # must be seen for "KIT COMPLETE"
KIT_OPTIONAL = ["GLOVES", "GOGGLES", "MASK"]
KIT_NAMES = {"HELMET": "Helmet", "VEST": "Safety vest", "SHOES": "Safety shoes",
             "GLOVES": "Gloves", "GOGGLES": "Goggles", "MASK": "Mask"}
AI_CONF = 0.30
# a zone counts as "helmet"/"vest" when this share of its pixels has the reference colours
# (tested on the TCET reference photos: kit 81-100 %, people without kit 0-47 %)
REF_MATCH = {"HELMET": 0.65, "VEST": 0.45}
CLASS_MAP = {"helmet": "HELMET", "hardhat": "HELMET", "hard hat": "HELMET", "vest": "VEST",
             "safety vest": "VEST", "safety shoe": "SHOES", "safety shoes": "SHOES", "shoe": "SHOES",
             "shoes": "SHOES", "boots": "SHOES", "glove": "GLOVES", "gloves": "GLOVES",
             "goggles": "GOGGLES", "mask": "MASK", "person": "PERSON"}
ai = {"state": "starting", "detail": "", "classes": [], "model": None, "pose": None, "ppe_error": ""}
ai_lock = threading.Lock()
kitchecks = []
kitrefs = {"model": {}, "photos": []}      # colour model + per-photo info for the page


def load_ai():
    """Runs once in the background: download what is missing, then load the models."""
    try:
        from ultralytics import YOLO
    except ImportError:
        ai.update(state="error", detail="AI library missing. In Command Prompt run:  pip install ultralytics  "
                  "then restart admin_hub.py")
        return
    try:
        ai.update(state="loading", detail="Downloading / loading the person model...")
        ai["pose"] = YOLO(POSE_MODEL)                 # ultralytics fetches it from GitHub the first time
    except Exception as e:  # noqa: BLE001
        ai.update(state="error", detail=f"Person model failed to load: {e}")
        return
    try:
        if not os.path.exists(PPE_MODEL):
            ai.update(detail="Downloading the PPE model (about 6 MB)...")
            tmp = PPE_MODEL + ".part"
            urllib.request.urlretrieve(PPE_MODEL_URL, tmp)
            os.replace(tmp, PPE_MODEL)
        m = YOLO(PPE_MODEL)
        names = m.names if isinstance(m.names, dict) else dict(enumerate(m.names))
        ai.update(model=m, classes=[str(v) for v in names.values()])
    except Exception as e:  # noqa: BLE001 - still usable with reference photos only
        ai["ppe_error"] = (f"PPE model not available ({e}). Helmet and vest are checked from your reference "
                           f"photos only; safety shoes can't be checked. Save {PPE_MODEL_URL} as {PPE_MODEL} to enable it.")
    rebuild_refs()
    ai.update(state="ready", detail="Ready")


def classify(label):
    n = str(label).lower().replace("_", " ").replace("-", " ").strip()
    neg = n.startswith("no ")
    return CLASS_MAP.get(n[3:] if neg else n), neg


# ---- person zones + reference colours ----
HUE_BINS, SAT_BINS = 12, 8


def colour_index(hsv):
    import numpy as np
    idx = (hsv[..., 0].astype(int) * HUE_BINS // 180) * SAT_BINS + hsv[..., 1].astype(int) * SAT_BINS // 256
    idx[hsv[..., 2] < 50] = HUE_BINS * SAT_BINS            # too dark to judge -> never matches
    return idx


def find_people(path):
    """Pose model -> list of (box, keypoints xy, keypoint confidences), biggest person first."""
    r = ai["pose"].predict(path, conf=0.4, verbose=False)[0]
    people = []
    for i in range(len(r.boxes)):
        people.append((r.boxes.xyxy[i].tolist(), r.keypoints.xy[i].tolist(), r.keypoints.conf[i].tolist()))
    people.sort(key=lambda p: (p[0][2] - p[0][0]) * (p[0][3] - p[0][1]), reverse=True)
    return people, r.orig_shape[:2]


def kit_zones(xy, cf, w, h):
    """Where a helmet and a vest should be, from eyes / shoulders / hips (pixel boxes)."""
    ok = lambda *ids: all(cf[i] > 0.5 for i in ids)
    z = {}
    if ok(1, 2):
        (lx, ly), (rx, ry) = xy[1], xy[2]
        e = max(abs(lx - rx), 1.0)
        if ok(5, 6):
            e = max(e, abs(xy[5][0] - xy[6][0]) / 4.2)          # head turned: use shoulder width
        cx, ey = (lx + rx) / 2, (ly + ry) / 2
        z["HELMET"] = [cx - 1.2 * e, ey - 2.4 * e, cx + 1.2 * e, ey - 0.7 * e]
    if ok(5, 6):
        sx1, sx2 = sorted([xy[5][0], xy[6][0]])
        sy = (xy[5][1] + xy[6][1]) / 2
        sw = sx2 - sx1
        hy = (xy[11][1] + xy[12][1]) / 2 if ok(11, 12) else sy + 1.4 * sw
        z["VEST"] = [sx1 + 0.12 * sw, sy + 0.12 * (hy - sy), sx2 - 0.12 * sw, hy - 0.08 * (hy - sy)]
    return {k: [int(max(0, min(v, (w if i % 2 == 0 else h) - 1))) for i, v in enumerate(b)] for k, b in z.items()}


def zone_hsv(img, b):
    import cv2
    x1, y1, x2, y2 = b
    crop = img[y1:y2, x1:x2]
    return cv2.cvtColor(crop, cv2.COLOR_BGR2HSV) if crop.size else None


def rebuild_refs():
    """Learn helmet / vest colours from every photo in data/kit_refs."""
    import cv2
    import numpy as np
    if ai["pose"] is None:
        return
    acc, photos = {}, []
    for fn in sorted(os.listdir(REF_DIR)):
        path = os.path.join(REF_DIR, fn)
        img = cv2.imread(path)
        if img is None:
            continue
        people, (h, w) = find_people(path)
        info = {"name": fn, "ok": False, "zones": {}}
        if people:
            z = kit_zones(people[0][1], people[0][2], w, h)
            info["zones"] = {k: [round(100 * b[0] / w, 2), round(100 * b[1] / h, 2),
                                 round(100 * (b[2] - b[0]) / w, 2), round(100 * (b[3] - b[1]) / h, 2)] for k, b in z.items()}
            for k, b in z.items():
                hsv = zone_hsv(img, b)
                if hsv is not None:
                    acc[k] = acc.get(k, 0) + np.bincount(colour_index(hsv).ravel(), minlength=HUE_BINS * SAT_BINS + 1)
            info["ok"] = bool(z)
        photos.append(info)
    model = {}
    for k, hist in acc.items():
        m = (hist / hist.sum()) > 0.003
        m[-1] = False
        model[k] = m
    kitrefs.update(model=model, photos=photos)


def ref_score(img, zone, item):
    m = kitrefs["model"].get(item)
    hsv = zone_hsv(img, zone) if zone else None
    if m is None or hsv is None:
        return None
    return round(float(m[colour_index(hsv)].mean()), 2)


def detect_kit(path):
    """Person + zones, PPE boxes on the person only, reference colour match -> verdict."""
    import cv2
    if ai["state"] != "ready":
        return {"ok": False, "error": ai["detail"] or "AI model not ready"}
    t0 = time.time()
    img = cv2.imread(path)
    if img is None:
        return {"ok": False, "error": "That file is not an image the AI can read."}
    with ai_lock:
        people, (h, w) = find_people(path)
        r = ai["model"].predict(path, conf=AI_CONF, verbose=False)[0] if ai["model"] else None
    pct = lambda b: {"x": round(100 * b[0] / w, 2), "y": round(100 * b[1] / h, 2),
                     "w": round(100 * (b[2] - b[0]) / w, 2), "h": round(100 * (b[3] - b[1]) / h, 2)}
    items = {k: {"found": False, "conf": 0.0, "flagged_missing": False, "how": ""} for k in KIT_REQUIRED + KIT_OPTIONAL}
    boxes = []
    if not people:
        return {"ok": True, "items": items, "boxes": [], "required": KIT_REQUIRED, "optional": KIT_OPTIONAL,
                "missing": KIT_REQUIRED, "complete": False, "no_person": True,
                "verdict": "NO PERSON FOUND - stand in the middle of the photo, whole body visible",
                "ms": int(1000 * (time.time() - t0)), "note": ""}
    pbox, xy, cf = people[0]
    px1, py1, px2, py2 = pbox
    ph = py2 - py1
    zones = kit_zones(xy, cf, w, h)
    feet_visible = cf[15] > 0.4 or cf[16] > 0.4                     # ankles found
    boxes.append({"label": "person", "kind": "person", **pct(pbox)})
    for k, b in zones.items():
        boxes.append({"label": f"{KIT_NAMES[k].lower()} zone", "kind": "zone", **pct(b)})

    # 1) PPE model - keep only detections that sit on the person, in a sensible place
    if r is not None:
        names = r.names if isinstance(r.names, dict) else dict(enumerate(r.names))
        for (x1, y1, x2, y2), conf, cls in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist()):
            label = str(names.get(int(cls), cls))
            kit, neg = classify(label)
            ix = max(0, min(x2, px2) - max(x1, px1)) * max(0, min(y2, py2) - max(y1, py1))
            on_person = ix >= 0.5 * max((x2 - x1) * (y2 - y1), 1)
            cy = ((y1 + y2) / 2 - py1) / max(ph, 1)                  # 0 = top of person, 1 = bottom
            if kit == "HELMET" and cy > 0.35:
                on_person = False                                    # a "helmet" at waist height is not worn
            if kit == "SHOES" and cy < 0.6:
                on_person = False
            boxes.append({"label": label if on_person else f"{label} (ignored: not worn)", "kind": "ppe" if on_person else "ignored",
                          "kit": kit, "missing": neg, "conf": round(conf, 2), **pct([x1, y1, x2, y2])})
            if kit in items and on_person:
                if neg:
                    items[kit]["flagged_missing"] = True
                elif conf > items[kit]["conf"]:
                    items[kit].update(found=True, conf=round(conf, 2), how=f"AI model {round(100 * conf)}%")

    # 2) reference photos - colour match inside the helmet / vest zones
    ref_scores = {}
    for k in ("HELMET", "VEST"):
        sc = ref_score(img, zones.get(k), k)
        ref_scores[k] = sc
        if sc is not None and sc >= REF_MATCH[k] and not items[k]["found"]:
            items[k].update(found=True, conf=sc, how=f"matches reference photos {round(100 * sc)}%")
        elif sc is not None and items[k]["found"]:
            items[k]["how"] += f" · reference match {round(100 * sc)}%"

    missing = [k for k in KIT_REQUIRED if not items[k]["found"]]
    notes = []
    if "SHOES" in missing and not feet_visible:
        items["SHOES"]["how"] = "feet not in the photo"
        notes.append("Feet are not in the photo - take a full-body photo to check safety shoes.")
    if "SHOES" in missing and ai["model"] is None:
        items["SHOES"]["how"] = "needs the PPE model"
    if not kitrefs["model"]:
        notes.append("No reference photos yet - add some below so your own helmet and vest are recognised.")
    notes.append("Pants are not checked by the AI - check them by eye.")
    return {"ok": True, "items": items, "boxes": boxes, "required": KIT_REQUIRED,
            "optional": KIT_OPTIONAL, "missing": missing, "complete": not missing, "ref_scores": ref_scores,
            "verdict": "KIT COMPLETE" if not missing else "MISSING: " + ", ".join(KIT_NAMES[k] for k in missing),
            "ms": int(1000 * (time.time() - t0)), "note": " ".join(notes)}


def ai_summary(res):
    if not res or not res.get("ok"):
        return ""
    return " · ".join(f"{KIT_NAMES[k]} {'✓' if res['items'][k]['found'] else '✗'}" for k in KIT_REQUIRED)


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
LIMITS.update({k: v for k, v in load("settings.json", {}).items() if k in LIMITS})
gas_state = {}                         # repeater -> {"high": bool, "last_alert": t}
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
    res = detect_kit(os.path.join(PHOTO_DIR, name)) if ai["state"] == "ready" else None
    bid = request.form.get("body_id", "").strip().upper()
    with lock:
        verifications.insert(0, {
            "id": uuid.uuid4().hex[:8], "time": clock(), "photo": name, "body_id": bid,
            "worker_id": request.form.get("worker_id", "").strip(),
            "scans": list(pending_scans), "status": "PENDING", "worker": "", "gear_ok": [], "ai": res,
        })
        del verifications[50:]
        pending_scans.clear()
        if res and res.get("ok"):
            kitchecks.insert(0, {"id": uuid.uuid4().hex[:8], "time": clock(), "photo": name,
                                 "body_id": bid, "source": "Entry phone", "result": res})
            del kitchecks[40:]
    msg = "Sent! Waiting for admin approval."
    if res and res.get("ok"):
        msg = f"Sent! AI check: {res['verdict']} ({ai_summary(res)})"
    return redirect("/phone?msg=" + urllib.parse.quote(msg))


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
                 "medication", "contact_name", "contact_phone", "notes", "step_m"]


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
    path = [str(x).upper()[:16] for x in (p.get("path") or [rep])][:8]
    via = path[0]                          # repeater that heard the body directly
    near = str(p.get("near") or "").upper()[:16] or via
    boot = int(p.get("bt", 0))             # random number the body picks at power-on
    si = seqinfo.setdefault(bid, {"last": -1, "rx": 0, "lost": 0, "boot": boot, "recent": {}})

    if boot != si["boot"]:                 # body restarted -> serial numbers start again
        si.update(boot=boot, last=-1, recent={})

    # same packet heard by a second repeater (within 5 s) -> only note the extra repeater
    seen = si["recent"].get(seq)
    if seen is not None and now - seen < 5:
        L = latest.get(bid)
        if L:
            L["heard_by"][via] = rssi
            if rssi > L["rssi"]:
                L["rssi"], L["repeater"] = rssi, via
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
    latest[bid] = {"seq": seq, "time": now, "repeater": via, "rssi": rssi, "path": path,
                   "near": near, "near_rssi": int(p.get("near_rssi", rssi)), "hops": len(path) - 1,
                   "heard_by": {via: rssi}, "temp": temp, "amb": amb,
                   "ax": ax / 1000, "ay": ay / 1000, "az": az / 1000,
                   "gx": gx / 10, "gy": gy / 10, "gz": gz / 10,
                   "amag": amag, "gmag": gmag, "fl": fl, "up": int(p.get("up", 0)),
                   "hum": None if int(p.get("hu", 0xFFFF)) == 0xFFFF else round(int(p["hu"]) / 100, 1),
                   "st": int(p.get("st", 0)) & 0xFFFF, "boot": boot,
                   "hd": None if int(p.get("hd", NONE16)) == NONE16 else int(p["hd"]) / 10,
                   "al": None if int(p.get("al", NONE16)) == NONE16 else int(p["al"]) / 10,
                   "hr": int(p.get("hr", 0)) or None, "spo2": int(p.get("sp", 0)) or None}
    update_position(bid, latest[bid], now)
    h = history.setdefault(bid, deque(maxlen=900))
    h.append((round(now, 2), None if fl & F_TEMP_FAULT else temp,
              None if fl & F_MPU_FAULT else amag, None if fl & F_MPU_FAULT else gmag, latest[bid]["hr"]))


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
                 tx_fail=d.get("tx_fail"), uptime=d.get("uptime"), rssi=d.get("wifi_rssi"),
                 gateway=bool(d.get("gateway")), esp_ch=d.get("esp_ch"), via_mesh=False)
        if r["gateway"]:
            r.update(hop=0, parent="ADMIN")
        # status reports from repeaters further down the chain
        for st in d.get("statuses", []) or []:
            sid = str(st.get("id", "")).strip().upper()[:16]
            if not sid:
                continue
            x = repeaters.setdefault(sid, {"id": sid, "first_seen": now, "posts": 0, "packets": 0})
            x.update(last_seen=now, hop=int(st.get("hop", 255)), alert_id=int(st.get("alert_id", 0)),
                     buzzing=bool(st.get("buzzing")), uptime=st.get("up"), bodies=st.get("bodies"),
                     nbrs=st.get("nbrs"), prssi=st.get("prssi"), path=st.get("path", []))
            if "gas_mv" in st:
                x.update(gas_mv=int(st.get("gas_mv", 0)), gas_warm=bool(st.get("gas_warm")),
                         gas_local=bool(st.get("gas_alarm")), gas_missing=bool(st.get("gas_missing")))
                g = x.setdefault("gas_hist", [])
                g.append([round(now, 1), x["gas_mv"]])
                del g[:-600]
                gas_sample(sid, x, now)
            if sid != rep:
                x.update(parent=str(st.get("parent", "")).upper(), via_mesh=True)
        for p in pk:
            ingest(p, rep, now)
        return jsonify(ok=True, alert=alert_payload())


# =====================================================================
#  Alerts
# =====================================================================
def next_alert_id():
    # always larger than any earlier id, even after the hub restarts - repeaters
    # only accept an alert that is newer than the one they already have
    return max(alert["id"] + 1, int(time.time()) - 1_700_000_000)


@app.post("/api/alert")
def raise_alert():
    d = request.get_json(force=True, silent=True) or {}
    target = str(d.get("target", "*")).strip().upper() or "*"
    msg = str(d.get("msg", "")).strip()[:80]
    with lock:
        alert.update(id=next_alert_id(), level=1, target=target, msg=msg, time=time.time())
        who = "ALL WORKERS" if target == "*" else f"{target} ({workers.get(target, {}).get('name', 'unregistered')})"
        alert_log.insert(0, {"time": clock(), "action": "ALERT", "target": who, "msg": msg})
        del alert_log[100:]
    return jsonify(ok=True, alert=alert_payload())


@app.post("/api/settings")
def settings():
    d = request.get_json(force=True, silent=True) or {}
    try:
        mv = int(d.get("gas_alarm_mv"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Type a number in mV"), 400
    if not 100 <= mv <= 5000:
        return jsonify(ok=False, error="Pick a level between 100 and 5000 mV"), 400
    with lock:
        LIMITS["gas_alarm_mv"] = mv
        save("settings.json", {"gas_alarm_mv": mv})
    return jsonify(ok=True, gas_alarm_mv=mv)


@app.post("/api/alert/clear")
def clear_alert():
    with lock:
        for gs in gas_state.values():
            gs["last_alert"] = time.time()        # gas still high -> alert again after GAS_REALERT_S
        if alert["level"]:
            alert.update(id=next_alert_id(), level=0, time=time.time())
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
        bump(2, "No movement (man down?)")
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
    hr, sp = L.get("hr"), L.get("spo2")
    if hr:
        if hr >= LIMITS["hr_danger_hi"] or hr <= LIMITS["hr_danger_lo"]:
            bump(2, f"Heart rate {hr} bpm")
        elif hr >= LIMITS["hr_warn_hi"] or hr <= LIMITS["hr_warn_lo"]:
            bump(1, f"Heart rate {hr} bpm")
    if sp:
        if sp <= LIMITS["spo2_danger"]:
            bump(2, f"SpO2 {sp} %")
        elif sp <= LIMITS["spo2_warn"]:
            bump(1, f"SpO2 low {sp} %")
    return LEVELS[level], why


candidate = {}                          # body_id -> (status, first time seen)


def check_gas(now):
    """Raise the alert for everyone when any repeater's gas reading crosses the limit."""
    limit = LIMITS["gas_alarm_mv"]
    for rid, r in repeaters.items():
        online = now - r["last_seen"] < LIMITS["mesh_repeater_offline_s"]
        if "gas_mv" not in r or r.get("gas_warm") or r.get("gas_missing") or not online:
            continue
        ga = gas_analysis(rid, r)
        bad = [g for g in (ga or {}).get("gases", []) if g["level"] == 2 and g["main"]]   # only the gases this sensor is made for
        high = r["gas_mv"] >= limit or r.get("gas_local") or bool(bad)
        what = ", ".join(f"{g['key']} ~{g['ppm']:.0f} ppm" for g in bad) or f"{r['gas_mv']} mV"
        gs = gas_state.setdefault(rid, {"high": False, "last_alert": 0})
        if high != gs["high"]:
            incidents.insert(0, {"t": now, "time": clock(now), "body_id": rid, "name": f"Gas at {rid}",
                                 "from": "SAFE" if high else "DANGER", "to": "DANGER" if high else "SAFE",
                                 "why": f"Gas {what} (sensor {r['gas_mv']} mV)" if high else f"Gas back to normal ({r['gas_mv']} mV)"})
            gs["high"] = high
        if high and not alert["level"] and now - gs["last_alert"] > GAS_REALERT_S:
            gs["last_alert"] = now
            msg = f"AUTO: gas {what} at {rid}"
            alert.update(id=next_alert_id(), level=1, target="*", msg=msg, time=now)
            alert_log.insert(0, {"time": clock(now), "action": "AUTO ALERT", "target": "ALL WORKERS", "msg": msg})


def watchdog():
    """Logs status changes every second, even if no browser is open.
    DANGER is logged at once; other changes must hold for 3 s (stops flicker
    when a reading sits right on a threshold)."""
    while True:
        now = time.time()
        with lock:
            for bid in set(workers) | set(latest):
                st, why = evaluate(bid, now)
                prev = last_status.get(bid)
                if prev is None or st == "NO DATA":
                    last_status[bid] = st if prev is None else prev
                    continue
                if st == prev:
                    candidate.pop(bid, None)
                    continue
                c = candidate.get(bid)
                if not c or c[0] != st:
                    candidate[bid] = (st, now)
                    if st != "DANGER":
                        continue
                elif now - c[1] < 3 and st != "DANGER":
                    continue
                name = workers.get(bid, {}).get("name") or f"{bid} (unregistered)"
                incidents.insert(0, {"t": now, "time": clock(now), "body_id": bid, "name": name,
                                     "from": prev, "to": st,
                                     "why": ", ".join(why) or ("Came online" if prev == "NO DATA" else "Back to normal")})
                del incidents[300:]
                last_status[bid] = st
                candidate.pop(bid, None)
            check_gas(now)
        time.sleep(1)


# =====================================================================
#  Map + worker positions
#  Coordinates are metres. The hub (entry / main repeater area) is (0, 0, 0).
#  x = right on the map, y = up on the map, z = height (negative = deeper).
#  Headings are degrees clockwise from map-up (0 = up, 90 = right).
# =====================================================================
MAP_DIR = os.path.join(DATA_DIR, "map")
os.makedirs(MAP_DIR, exist_ok=True)
MAP_DEFAULT = {
    "image": None, "img_w": 0, "img_h": 0,   # uploaded mine plan (pixels)
    "ox": 0.0, "oy": 0.0,                    # hub (0,0) position on the plan, in image pixels
    "ppm": 10.0,                             # image pixels per metre
    "repeaters": {},                         # "REP-02": {"x": 25.0, "y": 4.0, "z": 0.0}
    "tunnels": [],                           # [[[x, y], [x, y], ...], ...] centre lines
    "start_dir": None,                       # direction workers face at the hub (None = along the first tunnel)
    "step_m": 0.7,                           # default step length
    "snap_rssi": -55,                        # body hears a repeater this strongly -> it is next to it
    "range_m": 40.0,                         # a body can't be further than this from its nearest repeater
}
mapcfg = {**MAP_DEFAULT, **load("map.json", {})}
positions = {}                               # body_id -> position state


def _num(v, lo, hi, default):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    return default if not math.isfinite(v) else min(max(v, lo), hi)


def tunnel_segments():
    segs = []
    for line in mapcfg["tunnels"]:
        for a, b in zip(line, line[1:]):
            if a != b:
                segs.append((a, b))
    return segs


def project(x, y, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return qx, qy, math.hypot(x - qx, y - qy), math.degrees(math.atan2(dx, dy)) % 360


def snap_tunnel(x, y, heading=None):
    """Best point on the tunnel centre lines -> (x, y, tunnel direction) or None.
    With a walking direction, a tunnel that runs the same way wins over one that is a bit
    closer but crosses it - so a worker can turn into a side tunnel at a junction."""
    best, cost_best = None, None
    for a, b in tunnel_segments():
        q = project(x, y, a, b)
        cost = q[2]
        if heading is not None:
            mis = abs(angle_diff(q[3], heading))
            cost += 0.1 * min(mis, 180 - mis)          # 0.1 m per degree off the tunnel axis
        if best is None or cost < cost_best:
            best, cost_best = q, cost
    return None if best is None else (best[0], best[1], best[3])


def start_heading():
    if mapcfg.get("start_dir") is not None:
        return float(mapcfg["start_dir"]) % 360
    best = None                               # tunnel end closest to the hub -> direction into the mine
    for a, b in tunnel_segments():
        for p, q in ((a, b), (b, a)):
            d = math.hypot(*p)
            if best is None or d < best[0]:
                best = (d, math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) % 360)
    return best[1] if best and best[0] < 5 else 0.0


def rep_pos(rid):
    r = mapcfg["repeaters"].get(rid or "")
    return (r["x"], r["y"], r.get("z", 0.0)) if r else None


def angle_diff(a, b):
    return (a - b + 180) % 360 - 180


def update_position(bid, L, now):
    """Pedestrian dead reckoning: steps x step length along the gyro heading, kept inside
    the tunnels and pulled back to a repeater whenever the body is right next to one."""
    pdr = L.get("hd") is not None
    near, nrssi = L.get("near"), L.get("near_rssi", -127)
    rp = rep_pos(near)
    P = positions.get(bid)
    gateway = repeaters.get(near or "", {}).get("gateway")
    if P is None or P["boot"] != L["boot"] or P["pdr"] != pdr:
        if pdr:                               # switched on at the hub, or restarted right next to a repeater
            x, y, z = rp if rp is not None and not gateway and nrssi >= mapcfg["snap_rssi"] else (0.0, 0.0, 0.0)
        else:                                 # no step data: only "near this repeater" (if it is on the map)
            x, y, z = rp if rp is not None else (None, None, None)
        P = positions[bid] = {"boot": L["boot"], "pdr": pdr, "x": x, "y": y, "z": z,
                              "z0": (L.get("al") or 0.0) - (z or 0.0), "steps": L.get("st", 0),
                              "off": start_heading() - (L.get("hd") or 0.0), "since_fix": 0.0,
                              "walked": 0.0, "fix": None, "trail": deque(maxlen=400), "t": now,
                              "src": "start at hub" if (x, y) == (0.0, 0.0) else f"start at {near}"}
        if x is not None:
            P["trail"].append((round(x, 2), round(y, 2)))
    P["t"] = now
    if not pdr:                               # only "which repeater is it near" is known
        if rp is not None:
            if P["x"] is None:
                P["x"], P["y"], P["z"] = rp
            P["x"] += (rp[0] - P["x"]) * 0.5
            P["y"] += (rp[1] - P["y"]) * 0.5
            P["z"] = rp[2]
            P["src"] = f"near {near} (no step sensor)"
            P["fix"] = {"rep": near, "t": now}
        return
    step = _num(workers.get(bid, {}).get("step_m"), 0.3, 1.2, mapcfg["step_m"])
    n = (L.get("st", 0) - P["steps"]) & 0xFFFF
    P["steps"] = L.get("st", 0)
    if n > 300:                               # counter glitch - ignore
        n = 0
    heading = (L["hd"] + P["off"]) % 360
    x, y = P["x"], P["y"]
    seg_dir = None
    for _ in range(n):
        x += step * math.sin(math.radians(heading))
        y += step * math.cos(math.radians(heading))
        sn = snap_tunnel(x, y, heading)
        if sn:
            x, y, seg_dir = sn
    if n and seg_dir is not None:             # walking along a tunnel -> slowly correct the gyro drift
        d = angle_diff(seg_dir, heading)
        if abs(d) > 90:
            d = angle_diff((seg_dir + 180) % 360, heading)
        if abs(d) < 35:
            P["off"] += d * 0.2
    P["walked"] += n * step
    P["since_fix"] += n * step
    P["src"] = "steps + gyro"
    # repeater landmarks (skipped for the phone test page: the phone talks to the repeater over
    # WiFi, so its "signal" says nothing about where the pretend worker is walking)
    if rp is not None and not L["fl"] & F_TEST:
        dist = math.hypot(x - rp[0], y - rp[1])
        lim = 6.0 if nrssi >= mapcfg["snap_rssi"] else mapcfg["range_m"]   # strong signal = within a few metres
        if dist > lim:
            k = (dist - lim) / dist
            x += (rp[0] - x) * k
            y += (rp[1] - y) * k
            sn = snap_tunnel(x, y)
            if sn and math.hypot(sn[0] - x, sn[1] - y) < 3:
                x, y = sn[0], sn[1]
        if nrssi >= mapcfg["snap_rssi"]:
            P["since_fix"] = 0.0
            P["fix"] = {"rep": near, "t": now}
            P["src"] = f"steps + gyro, checked at {near}"
    P["x"], P["y"] = x, y
    if L.get("al") is not None:
        P["z"] = round(L["al"] - P["z0"], 1)
    tr = P["trail"]
    if not tr or math.hypot(x - tr[-1][0], y - tr[-1][1]) > 0.3:
        tr.append((round(x, 2), round(y, 2)))


def positions_view(now):
    out = {}
    for bid, P in positions.items():
        if P["x"] is None:
            continue
        out[bid] = {"x": round(P["x"], 2), "y": round(P["y"], 2), "z": None if P["z"] is None else round(P["z"], 1),
                    "pdr": P["pdr"], "src": P["src"], "acc": round(1.0 + 0.05 * P["since_fix"], 1) if P["pdr"] else None,
                    "walked": round(P["walked"]), "fix_rep": (P["fix"] or {}).get("rep"),
                    "fix_age": round(now - P["fix"]["t"]) if P["fix"] else None,
                    "trail": list(P["trail"])[-150:], "truth": P.get("truth")}
    return out


@app.get("/api/map")
def get_map():
    return jsonify(mapcfg)


@app.post("/api/map")
def set_map():
    d = request.get_json(force=True, silent=True) or {}
    with lock:
        for k in ("ox", "oy"):
            if k in d:
                mapcfg[k] = _num(d[k], -1e6, 1e6, mapcfg[k])
        if "ppm" in d:
            mapcfg["ppm"] = _num(d["ppm"], 0.01, 10000, mapcfg["ppm"])
        if "step_m" in d:
            mapcfg["step_m"] = _num(d["step_m"], 0.3, 1.2, 0.7)
        if "snap_rssi" in d:
            mapcfg["snap_rssi"] = int(_num(d["snap_rssi"], -90, -30, -55))
        if "range_m" in d:
            mapcfg["range_m"] = _num(d["range_m"], 5, 500, 40)
        if "start_dir" in d:
            mapcfg["start_dir"] = None if d["start_dir"] in (None, "") else _num(d["start_dir"], -360, 720, 0) % 360
        if "repeaters" in d and isinstance(d["repeaters"], dict):
            mapcfg["repeaters"] = {str(k).upper()[:16]: {"x": _num(v.get("x"), -1e5, 1e5, 0), "y": _num(v.get("y"), -1e5, 1e5, 0),
                                                         "z": _num(v.get("z"), -5000, 5000, 0)}
                                   for k, v in d["repeaters"].items() if isinstance(v, dict)}
        if "tunnels" in d and isinstance(d["tunnels"], list):
            mapcfg["tunnels"] = [[[_num(p[0], -1e5, 1e5, 0), _num(p[1], -1e5, 1e5, 0)] for p in line if len(p) >= 2]
                                 for line in d["tunnels"][:500] if isinstance(line, list) and len(line) >= 2]
        mapcfg["rev"] = mapcfg.get("rev", 0) + 1     # lets the page ignore an older copy still on its way
        save("map.json", mapcfg)
        return jsonify(ok=True, map=mapcfg)


@app.post("/api/map/image")
def map_image():
    f = request.files.get("image")
    if not f:
        return jsonify(ok=False, error="No image received"), 400
    ext = os.path.splitext(f.filename or "")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        return jsonify(ok=False, error="Use a PNG, JPG, GIF, WEBP or SVG image"), 400
    name = f"plan_{datetime.now():%Y%m%d_%H%M%S}{ext}"
    f.save(os.path.join(MAP_DIR, name))
    with lock:
        w, h = _num(request.form.get("w"), 1, 50000, 1000), _num(request.form.get("h"), 1, 50000, 1000)
        first = not mapcfg["image"]
        mapcfg.update(image=name, img_w=w, img_h=h)
        if first:                              # hub starts in the middle until the admin clicks it
            mapcfg.update(ox=w / 2, oy=h / 2, ppm=max(w, h) / 100)
        mapcfg["rev"] = mapcfg.get("rev", 0) + 1     # lets the page ignore an older copy still on its way
        save("map.json", mapcfg)
    return jsonify(ok=True, map=mapcfg)


@app.delete("/api/map/image")
def map_image_delete():
    with lock:
        mapcfg["image"] = None
        mapcfg["rev"] = mapcfg.get("rev", 0) + 1     # lets the page ignore an older copy still on its way
        save("map.json", mapcfg)
    return jsonify(ok=True)


@app.get("/mapimg/<path:fn>")
def map_img(fn):
    return send_from_directory(MAP_DIR, fn)


@app.post("/api/positions/reset")
def reset_position():
    bid = str((request.get_json(force=True, silent=True) or {}).get("body_id", "")).upper()
    with lock:
        if bid == "*":
            positions.clear()
        else:
            positions.pop(bid, None)
    return jsonify(ok=True)


# ---- demo walker: a pretend worker walking the tunnels (no hardware needed) ----
demo = {"on": False, "bid": "DEMO-01"}


def _demo_graph():
    lines = mapcfg["tunnels"] or [[[0, 0], [0, 20], [15, 20], [15, 0], [0, 0]]]
    nodes, edges = [], {}

    def node(p):
        for i, q in enumerate(nodes):
            if math.hypot(p[0] - q[0], p[1] - q[1]) < 1.0:
                return i
        nodes.append((float(p[0]), float(p[1])))
        return len(nodes) - 1
    for line in lines:
        ids = [node(p) for p in line]
        for a, b in zip(ids, ids[1:]):
            if a != b:
                edges.setdefault(a, set()).add(b)
                edges.setdefault(b, set()).add(a)
    return nodes, edges


def demo_loop():
    import random
    D = None
    while True:
        time.sleep(1)
        with lock:
            if not demo["on"]:
                D = None
                continue
            now = time.time()
            if D is None:
                nodes, edges = _demo_graph()
                start = min(range(len(nodes)), key=lambda i: math.hypot(*nodes[i]))
                nxt = sorted(edges.get(start, {start}))[0]
                D = {"nodes": nodes, "edges": edges, "a": start, "b": nxt, "t": 0.0, "steps": 0.0, "seq": 0,
                     "boot": random.randint(1, 65000), "drift": 0.0, "h0": None, "pause": 0}
                positions.pop(demo["bid"], None)
            nodes, edges = D["nodes"], D["edges"]
            true_step = 0.75                   # the hub assumes 0.7 m -> a realistic step-length error
            if D["pause"] > 0:
                D["pause"] -= 1
                dist = 0.0
            else:
                dist = 1.05 + random.uniform(-0.15, 0.15)
            a, b = nodes[D["a"]], nodes[D["b"]]
            while dist > 0:
                seg = math.hypot(b[0] - a[0], b[1] - a[1]) or 0.01
                left = (1 - D["t"]) * seg
                if dist < left:
                    D["t"] += dist / seg
                    D["steps"] += dist / true_step
                    dist = 0
                else:
                    D["steps"] += left / true_step
                    dist -= left
                    prev, cur = D["a"], D["b"]
                    opts = [n for n in edges.get(cur, ()) if n != prev] or [prev]
                    D["a"], D["b"], D["t"] = cur, random.choice(opts), 0.0
                    if random.random() < 0.15:
                        D["pause"] = random.randint(2, 6)
                    a, b = nodes[D["a"]], nodes[D["b"]]
            tx, ty = a[0] + (b[0] - a[0]) * D["t"], a[1] + (b[1] - a[1]) * D["t"]
            true_h = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360
            if D["h0"] is None:
                D["h0"] = true_h
            D["drift"] += 0.35 + random.gauss(0, 0.15)          # gyro drift, degrees per second
            hd = angle_diff(true_h - D["h0"] + D["drift"] + random.gauss(0, 2), 0)
            best = None
            for rid, r in mapcfg["repeaters"].items():
                d = math.hypot(tx - r["x"], ty - r["y"])
                if best is None or d < best[1]:
                    best = (rid, d)
            if best and best[1] <= mapcfg["range_m"]:
                near, rssi = best[0], int(-38 - 30 * math.log10(max(best[1], 1)) + random.gauss(0, 2))
            elif best:                          # out of range of every repeater on the map
                near, rssi = "", -127
            else:
                near = next((r["id"] for r in repeaters.values() if r.get("gateway")), "REP-01")
                rssi = -60
            D["seq"] += 1
            p = {"node": demo["bid"], "seq": D["seq"], "bt": D["boot"], "to": int(3640 + random.gauss(0, 8)),
                 "ta": 3100, "ax": int(random.gauss(0, 120)), "ay": int(random.gauss(0, 80)),
                 "az": int(1000 + random.gauss(0, 150)), "gx": 0, "gy": 0, "gz": 0, "fl": 0, "up": D["seq"],
                 "rssi": rssi, "near": near, "near_rssi": rssi, "hu": 7200, "hr": int(88 + random.gauss(0, 3)), "sp": 97,
                 "st": int(D["steps"]) & 0xFFFF, "hd": int(hd * 10), "al": 0, "path": [near or "DEMO"]}
            ingest(p, near, now)
            if demo["bid"] in positions:
                positions[demo["bid"]]["truth"] = [round(tx, 2), round(ty, 2)]


@app.post("/api/demo")
def demo_toggle():
    d = request.get_json(force=True, silent=True) or {}
    with lock:
        demo["on"] = bool(d.get("on"))
        if not demo["on"]:
            positions.pop(demo["bid"], None)
            latest.pop(demo["bid"], None)
            seqinfo.pop(demo["bid"], None)
            last_status.pop(demo["bid"], None)
    return jsonify(ok=True, on=demo["on"])


# =====================================================================
#  Gas analysis (MQ sensors)
#  Rs = RL x (Vc - Vout) / Vout ; R0 = Rs in clean air / clean-air ratio (datasheet)
#  ppm = a x (Rs/R0)^b   (curve fits of the datasheet graphs, MQUnifiedsensor library)
#  One MQ sensor reacts to all of its gases at once: each number assumes that gas is the
#  only one present. Good for "is the air changing / dangerous", not a lab analysis.
#  "main" = the gases the sensor is built for: only these raise the automatic alert. The others
#  are shown for information (a small humidity / temperature change can move them a lot).
# =====================================================================
GAS_MODELS = {
    "MQ-2":   {"clean": 9.83, "note": "LPG, propane, hydrogen, smoke (also reacts to methane)",
               "main": ["LPG", "Propane", "H2"],
               "gases": [("LPG", 574.25, -2.222), ("Propane", 658.71, -2.168), ("H2", 987.99, -2.162),
                         ("CO", 36974, -3.109), ("Alcohol", 3616.1, -2.675)]},
    "MQ-4":   {"clean": 4.4, "note": "methane (best choice for mines)",
               "main": ["CH4"],
               "gases": [("CH4", 1012.7, -2.786), ("LPG", 3811.9, -3.113)]},
    "MQ-5":   {"clean": 6.5, "note": "natural gas / LPG",
               "main": ["CH4", "LPG"],
               "gases": [("CH4", 177.65, -2.56), ("LPG", 80.897, -2.431), ("H2", 1163.8, -3.874)]},
    "MQ-7":   {"clean": 27.5, "note": "carbon monoxide (needs heater cycling for accuracy)",
               "main": ["CO"],
               "gases": [("CO", 99.042, -1.518), ("H2", 69.014, -1.374)]},
    "MQ-9":   {"clean": 9.6, "note": "CO + methane + LPG",
               "main": ["CO", "CH4"],
               "gases": [("CO", 599.65, -2.244), ("CH4", 4269.6, -2.648), ("LPG", 1000.5, -2.186)]},
    "MQ-135": {"clean": 3.6, "note": "air quality: CO2, ammonia, VOCs",
               "main": ["CO2", "NH3"],
               "gases": [("CO2", 110.47, -2.862, 400), ("NH3", 102.2, -2.473), ("CO", 605.18, -3.937),
                         ("Alcohol", 77.255, -3.18), ("Toluene", 44.947, -3.445), ("Acetone", 34.668, -3.369)]},
}
# name, warning ppm, danger ppm (mine-safety style limits; methane limits = % of the explosive limit)
GAS_INFO = {"CH4": ["Methane", 5000, 12500], "CO": ["Carbon monoxide", 35, 100], "LPG": ["LPG", 1000, 2100],
            "Propane": ["Propane", 1000, 2100], "H2": ["Hydrogen", 4000, 10000], "Alcohol": ["Alcohol vapour", 1000, 3000],
            "CO2": ["Carbon dioxide", 5000, 15000], "NH3": ["Ammonia", 25, 50], "Toluene": ["Toluene", 50, 100],
            "Acetone": ["Acetone", 500, 1000]}
GAS_CFG = {"model": "MQ-2", "rl_k": 1.0, "vc": 5.0, "r0": {}, **load("gas.json", {})}


def gas_rs(mv):
    v = min(mv / 1000.0, GAS_CFG["vc"] * 0.98)          # at/above the supply voltage = sensor saturated
    if v <= 0.02:
        return None
    return GAS_CFG["rl_k"] * (GAS_CFG["vc"] - v) / v


def gas_sample(rid, r, now):
    """Called for every gas reading. Auto-calibrates R0 from the first minute of clean
    readings after warm-up (until the admin calibrates by hand)."""
    if r.get("gas_missing"):                 # unplugged: learn clean air again once it is back
        if GAS_CFG["r0"].pop(rid, None):
            save("gas.json", GAS_CFG)
        r.pop("rs_hist", None)
        return
    if r.get("gas_warm"):
        return
    rs = gas_rs(r["gas_mv"])
    if rs is None:
        return
    h = r.setdefault("rs_hist", deque(maxlen=30))
    h.append(rs)
    cal = GAS_CFG["r0"].get(rid)
    if cal is None and len(h) >= 12:
        med = sorted(h)[len(h) // 2]
        GAS_CFG["r0"][rid] = {"r0": med / GAS_MODELS[GAS_CFG["model"]]["clean"], "rs_clean": med,
                              "how": "auto", "time": clock(now), "model": GAS_CFG["model"]}
        save("gas.json", GAS_CFG)


def gas_analysis(rid, r):
    if r.get("gas_missing") or "gas_mv" not in r:
        return None
    model = GAS_MODELS[GAS_CFG["model"]]
    rs = gas_rs(r["gas_mv"])
    cal = GAS_CFG["r0"].get(rid)
    out = {"model": GAS_CFG["model"], "note": model["note"], "rs": None if rs is None else round(rs, 2),
           "cal": None, "ratio": None, "gases": [], "warming": bool(r.get("gas_warm"))}
    if cal:
        out["cal"] = {"how": cal["how"], "time": cal["time"]}
        r0 = cal["rs_clean"] / model["clean"]             # follows a sensor-model change
    if rs is None or not cal or r.get("gas_warm"):
        return out
    ratio = rs / r0
    out["ratio"] = round(ratio, 3)
    for g in model["gases"]:
        key, a, b = g[0], g[1], g[2]
        # curve value minus what the same curve gives for clean air: clean air reads ~0 ppm
        # (the curve fits are poor at the clean-air end), CO2 adds the normal 400 ppm of fresh air
        ppm = max(0.0, a * ratio ** b - a * model["clean"] ** b)
        ppm = min(ppm + (g[3] if len(g) > 3 else 0), 1e6)
        name, warn, danger = GAS_INFO[key]
        out["gases"].append({"key": key, "name": name, "ppm": round(ppm, 1), "warn": warn, "danger": danger,
                             "level": 2 if ppm >= danger else 1 if ppm >= warn else 0, "main": key in model["main"]})
    return out


@app.post("/api/gas")
def gas_settings():
    d = request.get_json(force=True, silent=True) or {}
    with lock:
        if d.get("model") in GAS_MODELS:
            GAS_CFG["model"] = d["model"]
        if "rl_k" in d:
            GAS_CFG["rl_k"] = _num(d["rl_k"], 0.1, 100, 1.0)
        if "vc" in d:
            GAS_CFG["vc"] = _num(d["vc"], 3.0, 5.5, 5.0)
        if "gas_alarm_mv" in d:
            LIMITS["gas_alarm_mv"] = int(_num(d["gas_alarm_mv"], 100, 5000, LIMITS["gas_alarm_mv"]))
            save("settings.json", {"gas_alarm_mv": LIMITS["gas_alarm_mv"]})
        save("gas.json", GAS_CFG)
    return jsonify(ok=True)


@app.post("/api/gas/calibrate")
def gas_calibrate():
    rid = str((request.get_json(force=True, silent=True) or {}).get("repeater", "")).upper()
    with lock:
        r = repeaters.get(rid)
        h = list((r or {}).get("rs_hist", []))[-10:]
        if not h:
            return jsonify(ok=False, error=f"No gas readings from {rid} yet (sensor still warming up?)"), 400
        med = sorted(h)[len(h) // 2]
        GAS_CFG["r0"][rid] = {"r0": med / GAS_MODELS[GAS_CFG["model"]]["clean"], "rs_clean": med,
                              "how": "clean air", "time": clock(), "model": GAS_CFG["model"]}
        save("gas.json", GAS_CFG)
    return jsonify(ok=True)


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
            "near": L["near"], "near_rssi": L["near_rssi"], "path": L["path"], "hops": L["hops"],
            "flags": [n for b, n in FLAG_NAMES.items() if L["fl"] & b],
            "loss": round(100 * si["lost"] / total, 1) if total else 0, "rx": si["rx"],
            "up": L["up"], "hum": L.get("hum"), "steps": L.get("st"), "hd": L.get("hd"), "al": L.get("al"),
            "hr": L.get("hr"), "spo2": L.get("spo2")}


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
            limit = LIMITS["mesh_repeater_offline_s"] if r.get("via_mesh") else LIMITS["repeater_offline_s"]
            reps.append({**{k: v for k, v in r.items() if k not in ("gas_hist", "rs_hist")}, "age": round(age, 1),
                         "online": age < limit, "gas_spark": [g[1] for g in r.get("gas_hist", [])[-40:]],
                         "gas": gas_analysis(r["id"], r) if "gas_mv" in r else None})
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
            pending_scans=len(pending_scans), gear_list=GEAR_LIST, limits=LIMITS,
            ai={k: ai[k] for k in ("state", "detail", "classes", "ppe_error")}, kitchecks=kitchecks[:24],
            kitrefs=kitrefs["photos"], ref_match=REF_MATCH,
            kit_names=KIT_NAMES, map=mapcfg, map_start=start_heading(), positions=positions_view(now), demo=demo["on"],
            gas_cfg={k: GAS_CFG[k] for k in ("model", "rl_k", "vc")}, gas_models=list(GAS_MODELS),
            gas_info=GAS_INFO)


@app.post("/api/kitcheck")
def kitcheck():
    f = request.files.get("photo")
    if not f:
        return jsonify(ok=False, error="No photo received"), 400
    if ai["state"] != "ready":
        return jsonify(ok=False, error=ai["detail"] or "AI model not ready"), 503
    name = f"kit_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}.jpg"
    path = os.path.join(PHOTO_DIR, name)
    f.save(path)
    try:
        res = detect_kit(path)
    except Exception as e:  # noqa: BLE001 - unreadable image etc.
        return jsonify(ok=False, error=f"Could not analyse that image: {e}"), 400
    bid = request.form.get("body_id", "").strip().upper()
    rec = {"id": uuid.uuid4().hex[:8], "time": clock(), "photo": name, "body_id": bid,
           "source": "Kit check tab", "result": res}
    with lock:
        kitchecks.insert(0, rec)
        del kitchecks[40:]
    return jsonify(ok=True, check=rec)


@app.post("/api/kitrefs")
def add_kitrefs():
    files = request.files.getlist("photos")
    if not files:
        return jsonify(ok=False, error="No photos received"), 400
    for f in files:
        f.save(os.path.join(REF_DIR, f"ref_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:4]}.jpg"))
    if ai["pose"] is not None:
        with ai_lock:
            rebuild_refs()
    bad = [p["name"] for p in kitrefs["photos"] if not p["ok"]]
    return jsonify(ok=True, count=len(kitrefs["photos"]), unusable=bad)


@app.delete("/api/kitrefs/<name>")
def del_kitref(name):
    path = os.path.join(REF_DIR, os.path.basename(name))
    if os.path.exists(path):
        os.remove(path)
    if ai["pose"] is not None:
        with ai_lock:
            rebuild_refs()
    return jsonify(ok=True)


@app.get("/refs/<path:fn>")
def ref_photo(fn):
    return send_from_directory(REF_DIR, fn)


@app.get("/api/worker/<bid>/history")
def worker_history(bid):
    n = min(int(request.args.get("n", 240)), 900)
    with lock:
        h = list(history.get(bid.upper(), []))[-n:]
    now = time.time()
    return jsonify(t=[round(x[0] - now, 1) for x in h], temp=[x[1] for x in h],
                   amag=[x[2] for x in h], gmag=[x[3] for x in h], hr=[x[4] if len(x) > 4 else None for x in h])


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
.blood b{font-size:34px;line-height:1}
@media (max-width:520px){.aid{grid-template-columns:72px 1fr;gap:10px;padding:10px}.blood b{font-size:24px}.kv{grid-template-columns:86px 1fr}.axes{grid-template-columns:1fr 1fr}}.blood small{font-size:11px;letter-spacing:.08em}
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
/* chain map */
.chain{display:flex;gap:0;overflow-x:auto;padding:6px 2px 14px;align-items:flex-start}
.hopcol{display:grid;gap:10px;min-width:210px;align-content:start}
.hophead{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;text-align:center}
.arrow{align-self:center;color:var(--muted);font-size:22px;padding:0 10px;margin-top:22px}
.rnode{background:var(--panel);border:1px solid var(--line);border-top:4px solid var(--safe);border-radius:12px;padding:10px 12px;display:grid;gap:6px}
.rnode.off{border-top-color:var(--danger);opacity:.8}.rnode.admin{border-top-color:var(--info)}
.rnode .t{display:flex;justify-content:space-between;align-items:center;gap:8px;font-weight:800}
.rnode .m{font-size:12px;color:var(--muted)}
.wchip{font-size:12px;padding:3px 7px;border-radius:6px;background:var(--panel2);border-left:3px solid var(--safe);cursor:pointer}
.wchip.WARNING{border-left-color:var(--warn)}.wchip.DANGER{border-left-color:var(--danger);background:#ff4d4f22}
/* gas */
.gas{display:grid;gap:3px;font-size:12px}
.gas .gl{display:flex;justify-content:space-between;color:var(--muted)}
.gas b{color:var(--ink)}
.gbar{height:6px;background:var(--panel2);border-radius:3px;overflow:hidden}
.gbar i{display:block;height:100%;background:var(--safe);transition:width .4s}
.gas.warn .gbar i{background:var(--warn)}
.gas.high .gbar i{background:var(--danger)}.gas.high b{color:#ff8a8c}
.gas svg{width:100%;height:22px;display:block}
.setrow{display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin-bottom:12px}
.setrow label{width:200px}
/* kit check */
.drop{display:grid;place-items:center;text-align:center;border:2px dashed var(--line);border-radius:12px;padding:30px 12px;color:var(--ink);font-size:16px;cursor:pointer;background:var(--panel2)}
.drop:hover,.drop.over{border-color:var(--info)}
.drop input{display:none}
.aist{padding:10px 12px;border-radius:8px;font-size:14px;background:var(--panel2);border-left:4px solid var(--warn)}
.aist.ready{border-left-color:var(--safe)}.aist.error{border-left-color:var(--danger)}
.aist code{font-family:var(--mono);background:#0008;padding:1px 5px;border-radius:4px}
.verdict{font-size:20px;font-weight:800;padding:10px 14px;border-radius:10px;margin-bottom:10px}
.verdict.ok{background:#35c47c22;color:var(--safe)}.verdict.bad{background:#ff4d4f22;color:#ff8a8c}
.kimg{position:relative;display:inline-block;max-width:100%;border-radius:10px;overflow:hidden;line-height:0}
.kimg img{max-width:100%;max-height:60vh;display:block}
.kbox{position:absolute;border:2px solid var(--info);border-radius:3px}
.kbox.req{border-color:var(--safe)}.kbox.neg{border-color:var(--danger)}
.kbox.person{border:1px dashed #4c9bf0aa}.kbox.person span{display:none}
.kbox.zone{border:2px dotted #ffffffaa}.kbox.zone span{top:auto;bottom:-18px;background:#0009;font-weight:400}
.kbox.ignored{border:2px dashed #8a8a8a}.kbox.ignored span{background:#555c;text-decoration:line-through}
.refs{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;margin-top:10px}
.ref{position:relative;border-radius:8px;overflow:hidden;border:1px solid var(--line);line-height:0}
.ref img{width:100%;height:160px;object-fit:cover}
.ref .zb{position:absolute;border:2px solid var(--safe)}.ref .zb.v{border-color:#c6ff3d}
.ref button{position:absolute;top:4px;right:4px;line-height:1}
.ref.bad{border-color:var(--danger)}
.kbox span{position:absolute;left:-2px;top:-20px;background:inherit;font:600 11px/18px var(--font);padding:0 5px;white-space:nowrap;color:#fff;border-radius:3px 3px 0 0;background:#000b}
.kitems{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:12px}
.kitem{background:var(--panel2);border-radius:8px;padding:8px 10px;border-left:4px solid var(--line)}
.kitem b{margin-right:4px}.kitem small{display:block;color:var(--muted);font-size:12px}
.kitem.ok{border-left-color:var(--safe)}.kitem.ok b{color:var(--safe)}.kitem.bad{border-left-color:var(--danger)}.kitem.bad b{color:#ff8a8c}
.kgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.kthumb{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;cursor:pointer}
.kthumb img{width:100%;height:120px;object-fit:cover;display:block}
.kthumb div{padding:6px 8px;font-size:12px}
.spin{display:inline-block;width:16px;height:16px;border:2px solid var(--line);border-top-color:var(--info);border-radius:50%;animation:sp 1s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes sp{to{transform:rotate(360deg)}}
/* modal + toast */
.modal{position:fixed;inset:0;z-index:40;display:none;place-items:center;background:#000a;padding:16px}
.modal.on{display:grid}
.mbox{background:var(--panel);border:1px solid var(--danger);border-radius:14px;padding:20px;width:min(460px,100%);display:grid;gap:12px}
.toasts{position:fixed;bottom:16px;right:16px;z-index:50;display:grid;gap:8px;width:min(360px,calc(100% - 32px))}
.toast{background:var(--panel2);border:1px solid var(--line);border-left:5px solid var(--danger);border-radius:10px;padding:12px;box-shadow:0 8px 24px #0008;cursor:pointer}
.toast.WARNING{border-left-color:var(--warn)}.toast.SAFE{border-left-color:var(--safe)}
/* map */
.maplay{display:grid;grid-template-columns:1fr 330px;gap:14px;align-items:start}
@media (max-width:1000px){.maplay{grid-template-columns:1fr}}
.mapwrap{padding:0;overflow:hidden;position:relative}
.mtools{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:10px;border-bottom:1px solid var(--line)}
.mtools .sep{width:1px;align-self:stretch;background:var(--line);margin:0 4px}
.mtools .btn.on{background:var(--info);border-color:var(--info);color:#fff}
.mtools select{width:auto;padding:5px 8px;font-size:13px}
.mhint{padding:8px 12px;font-size:13px;color:var(--muted);background:var(--panel2);border-bottom:1px solid var(--line);min-height:34px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.mhint b{color:var(--ink)}.mhint input{width:110px;padding:5px 8px}
#msvg{display:block;width:100%;height:min(72vh,760px);background:#0a0f12;touch-action:none;user-select:none;cursor:grab}
#msvg.tool{cursor:crosshair}#msvg.panning{cursor:grabbing}
#msvg text{font-family:var(--font);paint-order:stroke;stroke:#0a0f12;stroke-width:3px;stroke-linejoin:round}
.mcoord{position:absolute;right:10px;bottom:10px;font:12px var(--mono);color:var(--muted);background:#0a0f12cc;padding:3px 8px;border-radius:6px;pointer-events:none}
.mside{display:grid;gap:14px}
.mw{display:grid;gap:3px;padding:8px 10px;background:var(--panel2);border-radius:8px;border-left:4px solid var(--nodata);cursor:pointer}
.mw.SAFE{border-left-color:var(--safe)}.mw.WARNING{border-left-color:var(--warn)}.mw.DANGER{border-left-color:var(--danger)}
.mw .t{display:flex;justify-content:space-between;gap:6px;font-weight:700}
.mw small{color:var(--muted);font-size:12px}
.mrep{display:grid;grid-template-columns:1fr 70px auto;gap:6px;align-items:center;font-size:13px}
.mrep input{padding:4px 6px}
@keyframes ring{from{r:9;opacity:.9}to{r:26;opacity:0}}
.ring{animation:ring 1.2s infinite}
@media (prefers-reduced-motion:reduce){.ring{animation:none}}
/* gas tab */
.gcard{background:var(--panel);border:1px solid var(--line);border-top:4px solid var(--safe);border-radius:12px;padding:14px;display:grid;gap:10px;align-content:start}
.gcard.WARNING{border-top-color:var(--warn)}.gcard.DANGER{border-top-color:var(--danger);box-shadow:0 0 22px #ff4d4f40}.gcard.OFF{border-top-color:var(--nodata)}
.gcard .head{display:flex;justify-content:space-between;align-items:center;gap:8px}
.grow{display:grid;grid-template-columns:1fr auto;gap:2px 10px;align-items:center;font-size:14px}
.grow .v{font-family:var(--mono);font-weight:700;text-align:right}
.grow .v.l1{color:var(--warn)}.grow .v.l2{color:#ff8a8c}
.grow .gbar{grid-column:1/-1}
.grow small{grid-column:1/-1;color:var(--muted);font-size:11px;margin-top:-1px}
.gbar i.l1{background:var(--warn)}.gbar i.l2{background:var(--danger)}
.graw{display:flex;justify-content:space-between;font-size:13px;color:var(--muted)}
.graw b{color:var(--ink);font-family:var(--mono)}
.gcard svg{width:100%;height:46px;display:block;background:var(--panel2);border-radius:6px}
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
    <button data-v="map">Map</button>
    <button data-v="gas">Gas &amp; air <span class="n" id="n-gas" hidden>!</span></button>
    <button data-v="workers">Register workers</button>
    <button data-v="entry">Entry check <span class="n" id="n-entry" hidden></span></button>
    <button data-v="kit">Kit check (AI)</button>
    <button data-v="network">Network</button>
    <button data-v="log">Incident log</button>
  </nav>
</div>

<main>
  <section class="view on" id="v-live">
    <div id="unknown-hint"></div>
    <div class="grid" id="cards"></div>
  </section>

  <section class="view" id="v-map">
    <div class="maplay">
      <div class="panel mapwrap">
        <div class="mtools" id="mtools">
          <button class="btn small on" data-tool="move">✋ Move</button>
          <button class="btn small" data-tool="origin">🏠 Set hub (0,0,0)</button>
          <button class="btn small" data-tool="scale">📏 Set scale</button>
          <button class="btn small" data-tool="tunnel">〰 Draw tunnel</button>
          <button class="btn small" data-tool="repeater">📡 Place</button><select id="m-rep" aria-label="Repeater to place"></select>
          <button class="btn small" data-tool="erase">🧽 Erase</button>
          <span class="sep"></span>
          <button class="btn small" id="m-zin" aria-label="Zoom in">＋</button><button class="btn small" id="m-zout" aria-label="Zoom out">－</button>
          <button class="btn small" id="m-fit">Fit</button>
          <span class="sep"></span>
          <label class="btn small" style="display:inline-block;color:var(--ink)">🗺 Mine plan…<input type="file" id="m-file" accept="image/*" hidden></label>
          <button class="btn small ghost" id="m-noimg" hidden>Remove plan</button>
          <span class="spacer"></span>
          <button class="btn small" id="m-demo">▶ Demo walker</button>
        </div>
        <div class="mhint" id="m-hint"></div>
        <svg id="msvg" aria-label="Mine map"></svg>
        <div class="mcoord" id="m-coord"></div>
      </div>
      <aside class="mside">
        <div class="panel"><h3>Workers on the map</h3><div id="m-workers" style="display:grid;gap:8px"></div></div>
        <div class="panel"><h3>Repeaters</h3><div id="m-reps" style="display:grid;gap:6px"></div>
          <p class="note" style="margin:8px 0 0">z = height of the repeater (level), metres. Negative = below the hub.</p></div>
        <div class="panel form"><h3>Tracking settings</h3>
          <div class="row2"><label>Step length (m)<input id="ms-step" type="number" step="0.05" min="0.3" max="1.2"></label>
            <label>Start direction (°)<input id="ms-dir" type="number" step="5" placeholder="auto"></label></div>
          <div class="row2"><label>"Next to repeater" (dBm)<input id="ms-snap" type="number" step="1" min="-90" max="-30"></label>
            <label>Repeater range (m)<input id="ms-range" type="number" step="5" min="5" max="500"></label></div>
          <button class="btn" id="ms-save">Save settings</button>
          <p class="note" style="margin:0">Workers start at the hub facing the start direction (blank = along the tunnel that leaves the hub).
            A worker's own step length can be set on Register workers.</p></div>
      </aside>
    </div>
  </section>

  <section class="view" id="v-gas">
    <div class="panel setrow" style="align-items:end">
      <label style="width:150px">Gas sensor model<select id="g-model"></select></label>
      <label style="width:120px">Load resistor RL (kΩ)<input id="g-rl" type="number" step="0.1" min="0.1"></label>
      <label style="width:110px">Sensor supply (V)<input id="g-vc" type="number" step="0.1" min="3" max="5.5"></label>
      <label style="width:170px">Backup alarm (sensor mV)<input id="g-limit" type="number" min="100" max="5000" step="50" inputmode="numeric"></label>
      <button class="btn" id="g-save">Save</button>
      <p class="note" style="flex:1;min-width:260px;margin:0" id="g-note"></p>
    </div>
    <div class="grid" id="gascards" style="grid-template-columns:repeat(auto-fill,minmax(320px,1fr));align-items:start"></div>
    <p class="note" style="margin-top:14px">How the numbers are made: sensor voltage → sensor resistance Rs → Rs/R0 (R0 = Rs in clean air ÷ datasheet ratio)
      → ppm from the datasheet curve of each gas, counted above the clean-air level. One MQ sensor reacts to all of its gases together, so each value assumes it is the only gas present —
      treat them as <b>estimates</b>. Any gas reaching its danger level, or the backup mV level, alerts <b>all</b> workers automatically.
      R0 is learned by itself from the first minute after warm-up (assumes clean air); press <b>Calibrate in clean air</b> to redo it.</p>
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
          <label>Step length for the map (m)<input id="f-step_m" type="number" step="0.05" min="0.3" max="1.2" placeholder="0.7 (about 0.41 × height)"></label>
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

  <section class="view" id="v-kit">
    <div class="two">
      <div class="panel form">
        <h2>AI kit check</h2>
        <div id="ai-status" class="aist">Checking the AI model…</div>
        <label>Worker (optional)<select id="k-worker"></select></label>
        <label class="drop" id="k-drop">📷 Take or choose a photo<br><span class="note">or drag an image here</span>
          <input type="file" id="k-file" accept="image/*" capture="environment"></label>
        <p class="note">Helmet, safety vest and safety shoes must all be seen for <b>KIT COMPLETE</b>.
          Gloves, goggles and mask are shown when found. Pants are not checked by the AI.
          Use a full-body photo in good light. Photos from the entry phone page are checked here too.</p>
        <h3 style="margin-top:8px">Reference photos</h3>
        <p class="note">Photos of a worker wearing the <b>correct</b> helmet and vest, taken where the check happens.
          The AI learns their colours, so your own helmet and vest are recognised. 3–6 photos work well.</p>
        <label class="drop" style="padding:14px">➕ Add reference photos<input type="file" id="r-file" accept="image/*" multiple></label>
        <div class="refs" id="refs"></div>
      </div>
      <div class="panel" id="k-view"><div class="empty">Take a photo to check a worker's kit.</div></div>
    </div>
    <h2 style="margin-top:22px">Recent checks</h2>
    <div class="kgrid" id="k-list"></div>
  </section>

  <section class="view" id="v-network">
    <h2>Repeater chain</h2>
    <p class="note">Body units send to the nearest repeater; each repeater passes data to the one closer to the main repeater, which sends it to this laptop.</p>
    <div class="chain" id="chain"></div>
    <h2 style="margin-top:14px">Repeaters</h2>
    <div class="tbl"><table><thead><tr><th>Repeater</th><th>Status</th><th>Hops to main</th><th>Sends to</th><th>Link signal</th><th>Last report</th><th>Body packets</th><th>Gas</th><th>Buzzer</th></tr></thead><tbody id="rtable"></tbody></table></div>
    <h2 style="margin-top:22px">Body units on air</h2>
    <div class="tbl"><table><thead><tr><th>Body ESP</th><th>Worker</th><th>Last packet</th><th>Serial no.</th><th>Packet loss</th><th>Nearest repeater</th><th>Route to admin</th></tr></thead><tbody id="btable"></tbody></table></div>
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
  if (S) { renderMap(); renderMapSide(); renderGas(); }
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
  setTimeout(() => t.remove(), 12000);
  while ($("#toasts").children.length > 3) $("#toasts").lastChild.remove(); }

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
    + `<span class="chip" onclick="showTab('network')">Repeaters <b>${S.repeaters.filter(r=>r.online).length}/${S.repeaters.length}</b></span>`
    + (() => { const g = S.repeaters.filter(r => r.online && r.gas_mv != null && !r.gas_missing); if (!g.length) return "";
        const lvl = r => r.gas_local || r.gas_mv >= S.limits.gas_alarm_mv || (r.gas && r.gas.gases.some(q => q.main && q.level === 2)) ? 2 : r.gas && r.gas.gases.some(q => q.main && q.level === 1) ? 1 : 0;
        const top = g.reduce((a, b) => lvl(b) > lvl(a) || (lvl(b) === lvl(a) && b.gas_mv > a.gas_mv) ? b : a), high = lvl(top) === 2;
        return `<span class="chip" onclick="showTab('gas')" style="${high ? "background:var(--danger);border-color:var(--danger);color:#fff" : ""}"><span class="d" style="background:${high ? "#fff" : "var(--safe)"}"></span>Gas <b>${top.gas_mv} mV</b> ${esc(top.id)}</span>`; })();
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
  const hopTxt = r => r.hop == null || r.hop >= 255 ? "no route" : r.hop === 0 ? "main" : r.hop;
  $("#rtable").innerHTML = S.repeaters.map(r => `<tr class="${r.online?"":"bad"}"><td class="mono"><b>${esc(r.id)}</b>${r.gateway ? ' <span class="tag ok">MAIN</span>' : ""}</td>
     <td>${r.online ? '<span class="pill SAFE">ONLINE</span>' : '<span class="pill DANGER">OFFLINE</span>'}</td>
     <td class="mono">${hopTxt(r)}</td><td class="mono">${esc(r.gateway ? "Admin (WiFi)" : r.parent || "–")}${r.gateway && r.ip ? `<br><a href="http://${esc(r.ip)}/" target="_blank" style="color:var(--info)">phone page: http://${esc(r.ip)}/</a>` : ""}</td>
     <td>${r.gateway ? (r.rssi != null ? sig(r.rssi) + " " + r.rssi + " dBm WiFi" : "–") : (r.prssi != null ? sig(r.prssi) + " " + r.prssi + " dBm" : "–")}</td>
     <td>${ago(r.age)}</td><td class="mono">${r.bodies ?? r.packets ?? 0}</td>
     <td class="mono">${r.gas_mv == null ? "–" : r.gas_missing ? "no sensor" : r.gas_mv + " mV" + (r.gas_warm ? " (warming)" : "")}</td>
     <td>${r.buzzing ? '<span class="tag red">BUZZING</span>' : "quiet"}</td></tr>`).join("")
     || `<tr><td colspan="9" class="note">No repeater has connected yet. Power the main repeater on, or run <span class="mono">python sim_repeater.py</span>.</td></tr>`;
  const all = [...S.workers.map(w=>({id:w.body_id,name:w.name,live:w.live,status:w.status})), ...S.unknown.map(u=>({id:u.body_id,name:"(unregistered)",live:u.live,status:u.status}))].filter(x=>x.live);
  $("#btable").innerHTML = all.map(x => `<tr><td class="mono">${esc(x.id)}</td><td>${esc(x.name)}</td><td>${ago(x.live.age)}</td>
     <td class="mono">#${x.live.seq}</td><td class="mono">${x.live.loss}%</td><td>${esc(x.live.near)} ${sig(x.live.near_rssi)}</td>
     <td class="mono">${route(x.live)}</td></tr>`).join("")
     || `<tr><td colspan="7" class="note">No body units heard yet.</td></tr>`;
  renderChain(all);

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

  renderKit();
  renderMap(); renderMapSide(); renderGas();
  if (openId) renderDrawer();
}

const route = L => [...(L.path || []), "Admin"].map(esc).join(" → ");

function gasHtml(r){
  if (r.gas_mv == null) return "";
  if (r.gas_missing) return `<div class="m" style="color:var(--warn)">Gas sensor not connected</div>`;
  const lim = S.limits.gas_alarm_mv, high = r.gas_mv >= lim || r.gas_local, warn = !high && r.gas_mv >= 0.75 * lim;
  const d = r.gas_spark || [], top = Math.max(lim * 1.25, ...d, 1);
  const pts = d.map((v, i) => `${(i / Math.max(d.length - 1, 1) * 100).toFixed(1)},${(22 - v / top * 20).toFixed(1)}`).join(" ");
  return `<div class="gas ${high ? "high" : warn ? "warn" : ""}"><div class="gl"><span>Gas${r.gas_warm ? " · warming up" : ""}</span><b class="mono">${r.gas_mv} mV</b></div>
    <div class="gbar"><i style="width:${Math.min(100, r.gas_mv / lim * 100).toFixed(0)}%"></i></div>
    ${d.length > 1 ? `<svg viewBox="0 0 100 22" preserveAspectRatio="none"><line x1="0" x2="100" y1="${(22 - lim / top * 20).toFixed(1)}" y2="${(22 - lim / top * 20).toFixed(1)}" stroke="#f0b42999" stroke-dasharray="3 3" stroke-width="1"/>
      <polyline points="${pts}" fill="none" stroke="${high ? "#ff4d4f" : "#4c9bf0"}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>` : ""}</div>`;
}

function renderChain(all){
  const near = {};
  all.forEach(x => (near[x.live.near] = near[x.live.near] || []).push(x));
  const cols = {};
  S.repeaters.forEach(r => { const h = r.hop == null || r.hop >= 255 ? 99 : r.hop; (cols[h] = cols[h] || []).push(r); });
  const hops = Object.keys(cols).map(Number).sort((a,b) => a-b);
  let html = `<div class="hopcol"><div class="hophead">Control room</div><div class="rnode admin"><div class="t">🖥 Admin hub</div>
    <div class="m">${S.workers.length} workers registered</div></div></div>`;
  hops.forEach(h => {
    html += `<div class="arrow">◀</div><div class="hopcol"><div class="hophead">${h === 0 ? "Main repeater" : h === 99 ? "No route yet" : h + (h === 1 ? " hop" : " hops") + " in"}</div>` +
      cols[h].map(r => `<div class="rnode ${r.online ? "" : "off"}"><div class="t"><span class="mono">${esc(r.id)}</span>
        ${r.buzzing ? '<span class="tag red">BUZZING</span>' : r.online ? '<span class="pill SAFE">ON</span>' : '<span class="pill DANGER">OFF</span>'}</div>
        <div class="m">${r.gateway ? "WiFi to admin" + (r.ip ? " · IP " + esc(r.ip) : "") : "sends to " + esc(r.parent || "?")} ${r.gateway ? "" : sig(r.prssi ?? -127)} · ${ago(r.age)}</div>
        ${gasHtml(r)}
        ${(near[r.id] || []).map(x => `<div class="wchip ${esc(x.status)}" onclick="openWorker('${esc(x.id)}')">👷 ${esc(x.name)} <span class="note">${sig(x.live.near_rssi)}</span></div>`).join("") || '<div class="m">No workers nearby</div>'}
      </div>`).join("") + `</div>`;
  });
  $("#chain").innerHTML = S.repeaters.length ? html : `<div class="empty">Waiting for the main repeater…</div>`;
}

function card(w){
  const L = w.live;
  return `<div class="card ${statusCls(w.status)}" onclick="openWorker('${esc(w.body_id)}')" tabindex="0">
    <div class="head"><div><div class="name">${esc(w.name)}</div><div class="sub">${esc(w.work || "No work assigned")} · <span class="mono">${esc(w.body_id)}</span></div></div>
      <span class="pill ${statusCls(w.status)}">${esc(w.status)}</span></div>
    <div class="metrics">
      <div class="metric"><small>Body temp</small><span>${L ? fmt(L.temp) : "–"}</span> °C</div>
      <div class="metric"><small>Heart rate</small><span>${L && L.hr ? L.hr : "–"}</span> bpm${L && L.spo2 ? `<br><span style="font-size:12px;color:var(--muted)">SpO₂ ${L.spo2}%</span>` : ""}</div>
      <div class="metric"><small>Signal</small>${L ? sig(L.rssi) : ""} <span style="font-size:13px">${L ? ago(L.age) : "–"}</span></div>
    </div>
    <div class="reasons">${esc(w.reasons.join(" · "))}</div>
    <div class="tags">${w.cleared ? '<span class="tag ok">Entry cleared ✓</span>' : '<span class="tag">Entry not verified</span>'}
      <span class="tag">Blood ${esc(w.blood || "?")}</span>${L && (L.fl & 64) ? '<span class="tag red">LED ALERT ON</span>' : ""}
      ${L ? `<span class="tag">📍 Near ${esc(L.near)} · ${L.hops} hop${L.hops===1?"":"s"}</span>` : ""}
      ${S.positions[w.body_id] ? `<span class="tag" onclick="event.stopPropagation();showTab('map');centerOn('${esc(w.body_id)}')">🗺 ${Math.round(Math.hypot(S.positions[w.body_id].x, S.positions[w.body_id].y))} m from hub${S.positions[w.body_id].z ? " · z " + S.positions[w.body_id].z + " m" : ""}</span>` : ""}</div>
  </div>`;
}

function vcard(v){
  const scanned = v.scans.filter(s => s.check === "OK").map(s => s.gear);
  const pending = v.status === "PENDING";
  return `<div class="vcard ${v.status}" id="vc-${v.id}">
    <a href="/photos/${esc(v.photo)}" target="_blank"><img src="/photos/${esc(v.photo)}" alt="Entry photo"></a>
    <div class="form">
      <div><span class="pill ${v.status==="APPROVED"?"SAFE":v.status==="REJECTED"?"DANGER":"WARNING"}">${esc(v.status)}</span> <span class="note">${esc(v.time)}</span></div>
      ${v.ai && v.ai.ok ? `<div><b>AI check:</b> <span class="tag ${v.ai.complete ? "ok" : "red"}">${esc(v.ai.verdict)}</span>
        ${v.ai.required.map(k => `<span class="tag ${v.ai.items[k].found ? "ok" : ""}">${esc(S.kit_names[k])} ${v.ai.items[k].found ? "✓" : "✗"}</span>`).join(" ")}</div>` : ""}
      <div><b>Gear scanned:</b> ${v.scans.length ? v.scans.map(s => `<span class="tag ${s.check==="OK"?"ok":"red"}">${esc(s.gear)} · ${esc(s.check)}</span>`).join(" ") : '<span class="tag red">No gear scanned</span>'}</div>
      ${pending ? `
        <div class="row2"><label>Worker name<input class="v-worker" value="${esc((S.workers.find(w=>w.body_id===v.body_id)||{}).name||"")}"></label>
          <label>Body unit ID<input class="v-body" value="${esc(v.body_id)}"></label></div>
        <label>Worker ID<input class="v-wid" value="${esc(v.worker_id)}"></label>
        <div class="checks">${S.gear_list.map(g => `<label><input type="checkbox" value="${g}" ${scanned.includes(g) || aiSaw(v, g) ?"checked":""}> ${g}</label>`).join("")}</div>
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
      <div class="chart"><div class="ct"><span>Heart rate (bpm)</span><b id="c-hr-v"></b></div><canvas id="c-hr"></canvas></div>
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
      <div class="metric"><small>Air temp${L.hum != null ? " / humidity" : ""}</small><span>${fmt(L.amb)}</span> °C${L.hum != null ? ` <span style="font-size:14px">${fmt(L.hum,0)} %</span>` : ""}</div>
      <div class="metric"><small>Heart rate / SpO₂</small><span>${L.hr || "–"}</span> bpm <span style="font-size:14px">${L.spo2 ? L.spo2 + " %" : ""}</span></div>
      <div class="metric"><small>Steps · height</small><span style="font-size:15px">${L.steps ?? "–"} · ${L.al != null ? fmt(L.al) + " m" : "–"}</span></div>
      <div class="metric"><small>Last packet</small><span style="font-size:15px">${ago(L.age)}</span></div>
      <div class="metric"><small>Accel X / Y / Z (g)</small><span style="font-size:14px">${fmt(L.ax,2)} / ${fmt(L.ay,2)} / ${fmt(L.az,2)}</span></div>
      <div class="metric"><small>Gyro X / Y / Z (°/s)</small><span style="font-size:14px">${fmt(L.gx,0)} / ${fmt(L.gy,0)} / ${fmt(L.gz,0)}</span></div>
      <div class="metric"><small>Nearest repeater</small><span style="font-size:14px">${esc(L.near)} ${sig(L.near_rssi)} #${L.seq}</span></div></div>
      <div class="note" style="margin-top:6px">Route: <span class="mono">${route(L)}</span></div>
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
    drawChart("#c-hr", h.t, h.hr || [], "#ff4d6d", [S.limits.hr_warn_lo, S.limits.hr_warn_hi]);
    drawChart("#c-acc", h.t, h.amag, "#4c9bf0", [1]);
    drawChart("#c-gyro", h.t, h.gmag, "#b37feb", []);
    if (L){ $("#c-hr-v").textContent = L.hr ? L.hr + " bpm" : "–"; $("#c-temp-v").textContent = fmt(L.temp) + " °C"; $("#c-acc-v").textContent = fmt(L.amag,2) + " g"; $("#c-gyro-v").textContent = fmt(L.gmag,0) + " °/s"; }
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
const FIELDS = ["body_id","name","emp_id","work","zone","blood","allergies","conditions","medication","contact_name","contact_phone","notes","step_m"];
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

/* ---------- AI kit check ---------- */
const GEAR_TO_KIT = {HELMET: "HELMET", VEST: "VEST", SHOES: "SHOES"};
const aiSaw = (v, g) => !!(v.ai && v.ai.ok && GEAR_TO_KIT[g] && v.ai.items[GEAR_TO_KIT[g]].found);
function renderKit(){
  const a = S.ai;
  const st = $("#ai-status");
  st.className = "aist " + (a.state === "ready" ? "ready" : a.state === "error" ? "error" : "");
  st.innerHTML = a.state === "ready" ? `<b>AI ready</b> · person finder${a.classes.length ? " + PPE model (" + esc(a.classes.join(", ")) + ")" : ""} + ${S.kitrefs.length} reference photo${S.kitrefs.length === 1 ? "" : "s"}
      ${a.ppe_error ? `<br><span style="color:var(--warn)">${esc(a.ppe_error)}</span>` : ""}`
    : a.state === "error" ? `<b>AI not available.</b> ${esc(a.detail).replace(/pip install ultralytics/, "<code>pip install ultralytics</code>")}`
    : `<span class="spin"></span>${esc(a.detail || "Starting the AI model…")}`;
  setIfChanged("#k-worker", JSON.stringify(S.workers.map(w=>w.body_id)), () =>
    `<option value="">(not linked)</option>` + S.workers.map(w => `<option value="${esc(w.body_id)}">${esc(w.name)} (${esc(w.body_id)})</option>`).join(""));
  setIfChanged("#refs", JSON.stringify(S.kitrefs), () => S.kitrefs.map(r => `<div class="ref ${r.ok ? "" : "bad"}" title="${r.ok ? "" : "No person found in this photo - it is not used"}">
      <img src="/refs/${esc(r.name)}" alt="Reference photo">
      ${Object.entries(r.zones).map(([k, z]) => `<div class="zb ${k === "VEST" ? "v" : ""}" style="left:${z[0]}%;top:${z[1]}%;width:${z[2]}%;height:${z[3]}%"></div>`).join("")}
      <button class="btn small ghost" onclick="delRef('${esc(r.name)}')" aria-label="Remove reference">✕</button></div>`).join("")
    || `<div class="note">No reference photos yet.</div>`);
  setIfChanged("#k-list", JSON.stringify(S.kitchecks.map(k=>k.id)), () => S.kitchecks.length ? S.kitchecks.map(k =>
    `<div class="kthumb" onclick="showKitById('${k.id}')"><img src="/photos/${esc(k.photo)}" alt="">
      <div><span class="pill ${k.result.complete ? "SAFE" : "DANGER"}">${k.result.complete ? "COMPLETE" : "MISSING"}</span>
      <span class="note">${esc(k.time)}${k.body_id ? " · " + esc(k.body_id) : ""}</span></div></div>`).join("")
    : `<div class="note">No checks yet.</div>`);
}
function kitView(k){
  const r = k.result, who = S.workers.find(w => w.body_id === k.body_id);
  const box = b => `<div class="kbox ${b.kind === "person" || b.kind === "zone" || b.kind === "ignored" ? b.kind : b.missing ? "neg" : r.required.includes(b.kit) ? "req" : ""}" style="left:${b.x}%;top:${b.y}%;width:${b.w}%;height:${b.h}%"><span>${esc(b.label)}${b.conf != null ? " " + Math.round(b.conf*100) + "%" : ""}</span></div>`;
  const item = it => { const x = r.items[it], req = r.required.includes(it);
    return `<div class="kitem ${x.found ? "ok" : req ? "bad" : ""}"><b>${x.found ? "✓" : req ? "✗" : "–"}</b>${esc(S.kit_names[it])}
      <small>${x.found ? esc(x.how) : x.how ? esc(x.how) : req ? (x.flagged_missing ? "seen WITHOUT it" : "not seen") : "not seen (optional)"}</small></div>`; };
  return `<div class="verdict ${r.complete ? "ok" : "bad"}">${r.complete ? "✓" : "✗"} ${esc(r.verdict)}</div>
    <div class="kimg"><img src="/photos/${esc(k.photo)}" alt="Checked photo">${r.boxes.map(box).join("")}</div>
    <div class="kitems">${[...r.required, ...r.optional].map(item).join("")}<div class="kitem"><b>?</b>Pants<small>check by eye</small></div></div>
    ${r.note ? `<p class="note" style="color:var(--warn)">${esc(r.note)}</p>` : ""}
    <p class="note">${esc(k.time)} · ${esc(k.source)}${who ? " · " + esc(who.name) : k.body_id ? " · " + esc(k.body_id) : ""} · analysed in ${r.ms} ms</p>`;
}
function showKitById(id){ const k = S.kitchecks.find(x => x.id === id); if (k) { $("#k-view").innerHTML = kitView(k); $("#k-view").scrollIntoView({behavior:"smooth", block:"nearest"}); } }
async function runKit(file){
  if (!file) return;
  $("#k-view").innerHTML = `<div class="empty"><span class="spin"></span>Checking the kit…</div>`;
  const fd = new FormData(); fd.append("photo", file); fd.append("body_id", $("#k-worker").value);
  try {
    const r = await fetch("/api/kitcheck", {method: "POST", body: fd}).then(x => x.json());
    if (!r.ok) { $("#k-view").innerHTML = `<div class="empty" style="color:#ff8a8c">${esc(r.error)}</div>`; return; }
    drawn["#k-list"] = null; await poll(); $("#k-view").innerHTML = kitView(r.check);
    if (!r.check.result.complete) beep();
  } catch(e) { $("#k-view").innerHTML = `<div class="empty" style="color:#ff8a8c">Upload failed. Is admin_hub.py still running?</div>`; }
  $("#k-file").value = "";
}
$("#k-file").onchange = e => runKit(e.target.files[0]);
$("#r-file").onchange = async e => {
  const fd = new FormData(); [...e.target.files].forEach(f => fd.append("photos", f));
  $("#refs").innerHTML = `<div class="note"><span class="spin"></span>Learning your kit…</div>`; drawn["#refs"] = null;
  const r = await fetch("/api/kitrefs", {method: "POST", body: fd}).then(x => x.json()).catch(() => ({ok: false, error: "Upload failed"}));
  toast(r.ok ? `<b>${r.count} reference photo(s)</b> in use${r.unusable.length ? " · " + r.unusable.length + " had no person and are ignored" : ""}` : esc(r.error), r.ok ? "SAFE" : "WARNING");
  e.target.value = ""; poll();
};
async function delRef(name){ await api("/api/kitrefs/" + encodeURIComponent(name), null, "DELETE"); drawn["#refs"] = null; poll(); }
const drop = $("#k-drop");
["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", e => runKit(e.dataTransfer.files[0]));

/* ================= MAP ================= */
const MV = {k: 8, tx: 300, ty: 300, fitted: false};     // screen px per metre + where (0,0) is on screen
let M = null, mapKey = "", tool = "move", draft = [], scalePts = [], mouseW = null, pan = null, mapBusy = 0;
const svgEl = $("#msvg");
const W2S = (x, y) => [MV.tx + x * MV.k, MV.ty - y * MV.k];
const S2W = (sx, sy) => [(sx - MV.tx) / MV.k, (MV.ty - sy) / MV.k];
const STC = {SAFE: "#35c47c", WARNING: "#f0b429", DANGER: "#ff4d4f", "NO DATA": "#6b7a80"};
const f1 = v => (Math.round(v * 10) / 10).toFixed(1);

function mapItems(){                       // everything the dashboard knows about, by body id
  const out = {};
  S.workers.forEach(w => out[w.body_id] = {id: w.body_id, name: w.name, status: w.status, reasons: w.reasons});
  S.unknown.forEach(u => out[u.body_id] = {id: u.body_id, name: u.body_id === "DEMO-01" ? "Demo walker" : u.body_id + " (unregistered)", status: u.status, reasons: u.reasons});
  return out;
}
function svgPoint(e){ const r = svgEl.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
function syncMap(){                        // take the hub's map unless we are in the middle of an edit
  const key = JSON.stringify(S.map);
  if (key !== mapKey && !mapBusy && (!M || (S.map.rev || 0) >= (M.rev || 0))){ mapKey = key; M = JSON.parse(key); }
}
async function saveMap(part){
  Object.assign(M, part); mapBusy++;
  try { const r = await api("/api/map", part); if (r.ok){ M = r.map; mapKey = JSON.stringify(r.map); } }
  catch(e){ toast("Could not save the map. Is admin_hub.py running?", "WARNING"); }
  mapBusy--; renderMap();
}

const HINTS = {
  move: () => `<b>Move:</b> drag to pan, mouse wheel to zoom. Click a worker to open their details.`,
  origin: () => `<b>Set hub:</b> click the spot on the plan where the hub / entry is. It becomes <b>(0, 0, 0)</b> and everything is measured from there.`,
  scale: () => scalePts.length < 2 ? `<b>Set scale:</b> click two points whose real distance you know (e.g. the ends of a tunnel) — point ${scalePts.length + 1} of 2.`
    : `Distance between the two points: <input id="m-dist" type="number" step="0.1" min="0.1"> m <button class="btn small green" id="m-dist-ok">Set scale</button> <button class="btn small ghost" id="m-dist-x">Cancel</button>`,
  tunnel: () => `<b>Draw tunnel:</b> click along the tunnel's centre line. Start on an existing tunnel to join it. ` +
    (draft.length ? `${draft.length} point(s) — <button class="btn small green" id="m-fin">Finish (Enter)</button> <button class="btn small ghost" id="m-undo">Undo point</button> <button class="btn small ghost" id="m-cancel">Cancel (Esc)</button>` : ""),
  repeater: () => `<b>Place repeater:</b> pick it in the list, then click where it is mounted. It jumps onto the tunnel if you click close to one.`,
  erase: () => `<b>Erase:</b> click a repeater to take it off the map, or a tunnel to remove that tunnel line.`,
};
function setTool(t){
  tool = t; draft = []; scalePts = [];
  document.querySelectorAll("#mtools [data-tool]").forEach(b => b.classList.toggle("on", b.dataset.tool === t));
  svgEl.classList.toggle("tool", t !== "move"); renderHint(); renderMap();
}
function renderHint(){
  $("#m-hint").innerHTML = HINTS[tool]();
  const b = id => document.getElementById(id);
  if (b("m-fin")) b("m-fin").onclick = finishTunnel;
  if (b("m-undo")) b("m-undo").onclick = () => { draft.pop(); renderHint(); renderMap(); };
  if (b("m-cancel")) b("m-cancel").onclick = () => setTool("tunnel");
  if (b("m-dist-ok")) { b("m-dist").focus(); b("m-dist-ok").onclick = applyScale; b("m-dist").onkeydown = e => e.key === "Enter" && applyScale(); }
  if (b("m-dist-x")) b("m-dist-x").onclick = () => setTool("scale");
}
$("#mtools").addEventListener("click", e => { const b = e.target.closest("[data-tool]"); if (b) setTool(b.dataset.tool); });

/* snapping to existing tunnels (for joining tunnels / placing repeaters) */
function nearestOnTunnels(x, y){
  let best = null;
  (M.tunnels || []).forEach((line, li) => line.forEach((a, i) => {
    if (!i) return; const b = line[i - 1], dx = a[0] - b[0], dy = a[1] - b[1], L2 = dx*dx + dy*dy;
    const t = L2 ? Math.max(0, Math.min(1, ((x - b[0]) * dx + (y - b[1]) * dy) / L2)) : 0;
    const q = [b[0] + t * dx, b[1] + t * dy], d = Math.hypot(x - q[0], y - q[1]);
    if (!best || d < best.d) best = {d, q, li};
  }));
  (M.tunnels || []).forEach(line => line.forEach(p => { const d = Math.hypot(x - p[0], y - p[1]);
    if (d * MV.k < 14 && (!best || d <= best.d + 0.01)) best = {d, q: [p[0], p[1]], vertex: true}; }));
  return best;
}
const r2 = v => Math.round(v * 100) / 100;

function mapClick(sx, sy){
  const [x, y] = S2W(sx, sy);
  if (tool === "move"){
    let hit = null;
    Object.entries(S.positions).forEach(([id, p]) => { const [px, py] = W2S(p.x, p.y); if (Math.hypot(px - sx, py - sy) < 14) hit = id; });
    if (hit) openWorker(hit);
    return;
  }
  if (tool === "origin"){                  // move everything so the clicked point becomes (0,0)
    const part = {repeaters: {}, tunnels: M.tunnels.map(l => l.map(p => [r2(p[0] - x), r2(p[1] - y)]))};
    Object.entries(M.repeaters).forEach(([k, r]) => part.repeaters[k] = {...r, x: r2(r.x - x), y: r2(r.y - y)});
    if (M.image){ part.ox = M.ox + x * M.ppm; part.oy = M.oy - y * M.ppm; }
    MV.tx += x * MV.k; MV.ty -= y * MV.k;
    saveMap(part); api("/api/positions/reset", {body_id: "*"});
    toast("Hub set. All distances are now measured from this point.", "SAFE"); setTool("move"); return;
  }
  if (tool === "scale"){
    if (scalePts.length < 2) scalePts.push([x, y]);
    renderHint(); renderMap(); return;
  }
  if (tool === "tunnel"){
    const n = nearestOnTunnels(x, y);
    draft.push(n && n.d * MV.k < 12 ? [r2(n.q[0]), r2(n.q[1])] : [r2(x), r2(y)]);
    renderHint(); renderMap(); return;
  }
  if (tool === "repeater"){
    const id = $("#m-rep").value; if (!id) return toast("No repeater to place. Type a name in the list first.", "WARNING");
    const n = nearestOnTunnels(x, y), p = n && n.d < 3 ? n.q : [x, y];
    const reps = {...M.repeaters, [id]: {x: r2(p[0]), y: r2(p[1]), z: (M.repeaters[id] || {}).z || 0}};
    saveMap({repeaters: reps});
    const next = [...$("#m-rep").options].map(o => o.value).find(v => !reps[v]); if (next) $("#m-rep").value = next;
    return;
  }
  if (tool === "erase"){
    const hitR = Object.entries(M.repeaters).find(([k, r]) => { const [px, py] = W2S(r.x, r.y); return Math.hypot(px - sx, py - sy) < 14; });
    if (hitR){ const reps = {...M.repeaters}; delete reps[hitR[0]]; saveMap({repeaters: reps}); return; }
    const n = nearestOnTunnels(x, y);
    if (n && n.li != null && n.d * MV.k < 12){ saveMap({tunnels: M.tunnels.filter((_, i) => i !== n.li)}); }
  }
}
function finishTunnel(){
  if (draft.length >= 2) saveMap({tunnels: [...M.tunnels, draft]});
  draft = []; renderHint(); renderMap();
}
function applyScale(){
  const D = parseFloat($("#m-dist").value), [a, b] = scalePts, dw = Math.hypot(a[0] - b[0], a[1] - b[1]);
  if (!(D > 0) || !(dw > 0)) return toast("Type the real distance in metres.", "WARNING");
  const f = D / dw;                         // new metres per old metre - everything is stretched about the hub
  const part = {repeaters: {}, tunnels: M.tunnels.map(l => l.map(p => [r2(p[0] * f), r2(p[1] * f)]))};
  Object.entries(M.repeaters).forEach(([k, r]) => part.repeaters[k] = {...r, x: r2(r.x * f), y: r2(r.y * f)});
  if (M.image) part.ppm = M.ppm / f;
  MV.k /= f; saveMap(part); api("/api/positions/reset", {body_id: "*"});
  toast(`Scale set: ${D} m between the two points.`, "SAFE"); setTool("move");
}
document.addEventListener("keydown", e => {
  if (!$("#v-map").classList.contains("on") || e.target.matches("input,select,textarea")) return;
  if (e.key === "Enter" && tool === "tunnel") finishTunnel();
  if (e.key === "Escape" && tool !== "move") setTool("move");
});

/* pan + zoom */
svgEl.addEventListener("pointerdown", e => { const [sx, sy] = svgPoint(e); pan = {sx, sy, tx: MV.tx, ty: MV.ty, moved: false}; svgEl.setPointerCapture(e.pointerId); });
svgEl.addEventListener("pointermove", e => {
  const [sx, sy] = svgPoint(e); mouseW = S2W(sx, sy);
  $("#m-coord").textContent = `x ${f1(mouseW[0])}  y ${f1(mouseW[1])} m`;
  if (pan){ const dx = sx - pan.sx, dy = sy - pan.sy;
    if (Math.hypot(dx, dy) > 4) pan.moved = true;
    if (pan.moved && (tool === "move" || e.buttons === 4 || e.shiftKey)){ MV.tx = pan.tx + dx; MV.ty = pan.ty + dy; svgEl.classList.add("panning"); } }
  if (pan && pan.moved || draft.length || scalePts.length === 1) renderMap();
});
svgEl.addEventListener("pointerup", e => { const [sx, sy] = svgPoint(e); const p = pan; pan = null; svgEl.classList.remove("panning");
  if (p && !p.moved) mapClick(sx, sy); });
svgEl.addEventListener("dblclick", e => { if (tool === "tunnel"){ draft.pop(); finishTunnel(); } });
svgEl.addEventListener("wheel", e => { e.preventDefault(); const [sx, sy] = svgPoint(e); zoomAt(sx, sy, e.deltaY < 0 ? 1.2 : 1 / 1.2); }, {passive: false});
function zoomAt(sx, sy, f){ const k = Math.max(0.3, Math.min(400, MV.k * f)); MV.tx = sx - (sx - MV.tx) * k / MV.k; MV.ty = sy - (sy - MV.ty) * k / MV.k; MV.k = k; renderMap(); }
$("#m-zin").onclick = () => zoomAt(svgEl.clientWidth / 2, svgEl.clientHeight / 2, 1.4);
$("#m-zout").onclick = () => zoomAt(svgEl.clientWidth / 2, svgEl.clientHeight / 2, 1 / 1.4);
$("#m-fit").onclick = () => fitMap();
function fitMap(){
  const pts = [[0, 0]];
  if (M.image) pts.push([-M.ox / M.ppm, M.oy / M.ppm], [(M.img_w - M.ox) / M.ppm, (M.oy - M.img_h) / M.ppm]);
  M.tunnels.forEach(l => pts.push(...l)); Object.values(M.repeaters).forEach(r => pts.push([r.x, r.y]));
  Object.values(S.positions).forEach(p => pts.push([p.x, p.y]));
  let x0 = Math.min(...pts.map(p => p[0])), x1 = Math.max(...pts.map(p => p[0])), y0 = Math.min(...pts.map(p => p[1])), y1 = Math.max(...pts.map(p => p[1]));
  if (x1 - x0 < 20){ const c = (x0 + x1) / 2; x0 = c - 10; x1 = c + 10; } if (y1 - y0 < 20){ const c = (y0 + y1) / 2; y0 = c - 10; y1 = c + 10; }
  const W = svgEl.clientWidth || 800, H = svgEl.clientHeight || 600;
  MV.k = Math.min((W - 60) / (x1 - x0), (H - 60) / (y1 - y0));
  MV.tx = W / 2 - (x0 + x1) / 2 * MV.k; MV.ty = H / 2 + (y0 + y1) / 2 * MV.k; MV.fitted = true; renderMap();
}

/* plan image */
$("#m-file").onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  const url = URL.createObjectURL(f), img = new Image();
  img.onload = async () => {
    const fd = new FormData(); fd.append("image", f); fd.append("w", img.naturalWidth || 1000); fd.append("h", img.naturalHeight || 1000);
    const r = await fetch("/api/map/image", {method: "POST", body: fd}).then(x => x.json()).catch(() => ({ok: false, error: "Upload failed"}));
    URL.revokeObjectURL(url); e.target.value = "";
    if (!r.ok) return toast(esc(r.error), "WARNING");
    M = r.map; mapKey = JSON.stringify(r.map); fitMap();
    toast("Plan loaded. Next: <b>Set hub</b>, then <b>Set scale</b>.", "SAFE"); setTool("origin");
  };
  img.src = url;
};
$("#m-noimg").onclick = async () => { await api("/api/map/image", null, "DELETE"); mapKey = ""; poll(); };
$("#m-demo").onclick = async () => { const on = !S.demo; await api("/api/demo", {on});
  toast(on ? "Demo walker started: <b>Demo walker</b> walks the tunnels. Dashed white ring = where it really is." : "Demo walker stopped.", "SAFE"); poll(); };

function gridStep(){ for (const g of [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]) if (g * MV.k >= 45) return g; return 1000; }
function renderMap(){
  if (!S || !$("#v-map").classList.contains("on")) return;
  syncMap(); if (!M) return;
  if (!MV.fitted && svgEl.clientWidth) fitMap();
  const W = svgEl.clientWidth, H = svgEl.clientHeight, k = MV.k, out = [];
  // plan image
  if (M.image){ const [ix, iy] = W2S(-M.ox / M.ppm, M.oy / M.ppm);
    out.push(`<image href="/mapimg/${encodeURIComponent(M.image)}" x="${ix}" y="${iy}" width="${M.img_w / M.ppm * k}" height="${M.img_h / M.ppm * k}" opacity=".55" preserveAspectRatio="none"/>`); }
  // grid
  const g = gridStep(), [wx0, wy1] = S2W(0, 0), [wx1, wy0] = S2W(W, H);
  for (let x = Math.ceil(wx0 / g) * g; x <= wx1; x += g){ const sx = W2S(x, 0)[0];
    out.push(`<line x1="${sx}" x2="${sx}" y1="0" y2="${H}" stroke="${Math.abs(x) < 1e-9 ? "#4c9bf055" : "#ffffff10"}"/>`,
      `<text x="${sx + 3}" y="${H - 6}" font-size="10" fill="#6b7a80">${+x.toFixed(1)}</text>`); }
  for (let y = Math.ceil(wy0 / g) * g; y <= wy1; y += g){ const sy = W2S(0, y)[1];
    out.push(`<line x1="0" x2="${W}" y1="${sy}" y2="${sy}" stroke="${Math.abs(y) < 1e-9 ? "#4c9bf055" : "#ffffff10"}"/>`,
      `<text x="4" y="${sy - 3}" font-size="10" fill="#6b7a80">${+y.toFixed(1)}</text>`); }
  // scale bar
  out.push(`<line x1="${W - 20 - g * k}" x2="${W - 20}" y1="${H - 30}" y2="${H - 30}" stroke="#e7eef0" stroke-width="2"/>`,
    `<text x="${W - 20 - g * k}" y="${H - 36}" font-size="11" fill="#e7eef0">${g} m</text>`);
  // tunnels
  const tw = Math.max(6, 3 * k);
  M.tunnels.forEach(l => { const pts = l.map(p => W2S(p[0], p[1]).join(",")).join(" ");
    out.push(`<polyline points="${pts}" fill="none" stroke="#3a4a52" stroke-width="${tw}" stroke-linecap="round" stroke-linejoin="round"/>`,
      `<polyline points="${pts}" fill="none" stroke="#8fa2a955" stroke-width="1" stroke-dasharray="4 4"/>`); });
  if (draft.length){ const pts = [...draft, ...(mouseW ? [mouseW] : [])].map(p => W2S(p[0], p[1]).join(",")).join(" ");
    out.push(`<polyline points="${pts}" fill="none" stroke="#4c9bf0" stroke-width="${tw}" stroke-opacity=".45" stroke-linecap="round" stroke-linejoin="round"/>`);
    draft.forEach(p => { const [x, y] = W2S(p[0], p[1]); out.push(`<circle cx="${x}" cy="${y}" r="4" fill="#4c9bf0"/>`); }); }
  if (scalePts.length){ const pts = [...scalePts, ...(scalePts.length === 1 && mouseW ? [mouseW] : [])].map(p => W2S(p[0], p[1]));
    out.push(`<polyline points="${pts.map(p => p.join(",")).join(" ")}" fill="none" stroke="#f0b429" stroke-width="2" stroke-dasharray="6 4"/>`);
    pts.forEach(p => out.push(`<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="#f0b429"/>`)); }
  // hub + start direction
  const [hx, hy] = W2S(0, 0), sd = (M.start_dir ?? S.map_start ?? 0) * Math.PI / 180;
  out.push(`<line x1="${hx}" y1="${hy}" x2="${hx + Math.sin(sd) * 34}" y2="${hy - Math.cos(sd) * 34}" stroke="#4c9bf0" stroke-width="2" marker-end="url(#arr)"/>`,
    `<circle cx="${hx}" cy="${hy}" r="11" fill="#0a0f12" stroke="#4c9bf0" stroke-width="2"/><circle cx="${hx}" cy="${hy}" r="4" fill="#4c9bf0"/>`,
    `<text x="${hx + 14}" y="${hy + 18}" font-size="12" font-weight="700" fill="#4c9bf0">HUB (0,0,0)</text>`);
  // repeaters
  const live = {}; S.repeaters.forEach(r => live[r.id] = r);
  Object.entries(M.repeaters).forEach(([id, r]) => {
    const [x, y] = W2S(r.x, r.y), L = live[id];
    const gl = L && L.gas ? Math.max(0, ...L.gas.gases.filter(q => q.main).map(q => q.level)) : 0, gasHigh = L && (gl === 2 || L.gas_local);
    const col = !L ? "#6b7a80" : !L.online ? "#ff4d4f" : "#35c47c";
    out.push(`<circle cx="${x}" cy="${y}" r="${Math.max(2.5 * k, 10)}" fill="${gasHigh ? "#ff4d4f22" : "#35c47c0d"}" stroke="${gasHigh ? "#ff4d4f" : gl === 1 ? "#f0b429" : "#35c47c33"}" stroke-dasharray="3 3"/>`);
    if (L && L.buzzing) out.push(`<circle class="ring" cx="${x}" cy="${y}" r="9" fill="none" stroke="#ff4d4f" stroke-width="2"/>`);
    out.push(`<rect x="${x - 7}" y="${y - 7}" width="14" height="14" rx="3" fill="${col}" stroke="#0a0f12" stroke-width="2"/>`,
      `<text x="${x + 11}" y="${y - 9}" font-size="12" font-weight="700" fill="#e7eef0">${esc(id)}${r.z ? ` <tspan fill="#8fa2a9" font-weight="400">z ${r.z}</tspan>` : ""}${gasHigh ? ` <tspan fill="#ff8a8c">GAS</tspan>` : ""}</text>`);
  });
  // workers
  const items = mapItems();
  Object.entries(S.positions).forEach(([id, p]) => {
    const it = items[id] || {name: id, status: "NO DATA"}, c = STC[it.status] || "#6b7a80";
    if (p.trail.length > 1) out.push(`<polyline points="${p.trail.map(q => W2S(q[0], q[1]).join(",")).join(" ")}" fill="none" stroke="${c}" stroke-opacity=".45" stroke-width="2" stroke-linejoin="round"/>`);
    const [x, y] = W2S(p.x, p.y);
    if (p.acc) out.push(`<circle cx="${x}" cy="${y}" r="${Math.max(p.acc * k, 9)}" fill="${c}18" stroke="${c}55"/>`);
    if (!p.pdr) out.push(`<circle cx="${x}" cy="${y}" r="${Math.max(2.5 * k, 16)}" fill="none" stroke="${c}" stroke-dasharray="2 4"/>`);
    if (p.truth){ const [txx, tyy] = W2S(p.truth[0], p.truth[1]);
      out.push(`<line x1="${x}" y1="${y}" x2="${txx}" y2="${tyy}" stroke="#ffffff66" stroke-dasharray="2 3"/><circle cx="${txx}" cy="${tyy}" r="6" fill="none" stroke="#fff" stroke-dasharray="3 2"/>`); }
    if (it.status === "DANGER") out.push(`<circle class="ring" cx="${x}" cy="${y}" r="9" fill="none" stroke="#ff4d4f" stroke-width="2"/>`);
    out.push(`<circle cx="${x}" cy="${y}" r="8" fill="${c}" stroke="#0a0f12" stroke-width="2" style="cursor:pointer"/>`,
      `<text x="${x + 12}" y="${y + 4}" font-size="13" font-weight="700" fill="#e7eef0">${esc(it.name)}${p.z ? ` <tspan fill="#8fa2a9" font-weight="400">z ${p.z} m</tspan>` : ""}</text>`);
  });
  svgEl.innerHTML = `<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#4c9bf0"/></marker></defs>` + out.join("");
}

let msEdited = false;
["#ms-step", "#ms-dir", "#ms-snap", "#ms-range"].forEach(s => $(s).addEventListener("input", () => msEdited = true));
$("#ms-save").onclick = async () => {
  await saveMap({step_m: $("#ms-step").value, start_dir: $("#ms-dir").value === "" ? null : $("#ms-dir").value,
                 snap_rssi: $("#ms-snap").value, range_m: $("#ms-range").value});
  msEdited = false; toast("Tracking settings saved.", "SAFE");
};
async function resetPos(id){ await api("/api/positions/reset", {body_id: id}); toast("Position reset: the dot restarts at the hub.", "SAFE"); poll(); }
function centerOn(id){ const p = S.positions[id]; if (!p) return; MV.tx = svgEl.clientWidth / 2 - p.x * MV.k; MV.ty = svgEl.clientHeight / 2 + p.y * MV.k; renderMap(); }
async function setRepZ(id, v){ const reps = {...M.repeaters}; if (!reps[id]) return; reps[id] = {...reps[id], z: parseFloat(v) || 0}; saveMap({repeaters: reps}); }

function renderMapSide(){
  if (!M) syncMap(); if (!M) return;
  $("#m-demo").textContent = S.demo ? "■ Stop demo" : "▶ Demo walker"; $("#m-demo").classList.toggle("red", S.demo);
  $("#m-noimg").hidden = !M.image;
  const ids = [...new Set([...S.repeaters.map(r => r.id), ...Object.keys(M.repeaters)])].sort();
  setIfChanged("#m-rep", JSON.stringify([ids, Object.keys(M.repeaters)]), () => {
    const cur = $("#m-rep").value;
    return (ids.length ? ids : ["REP-01"]).map(id => `<option value="${esc(id)}" ${id === cur ? "selected" : ""}>${esc(id)}${M.repeaters[id] ? " ✓" : ""}</option>`).join("");
  });
  if (!$("#m-hint").innerHTML) renderHint();
  const items = mapItems(), now = Object.entries(S.positions);
  $("#m-workers").innerHTML = now.length ? now.map(([id, p]) => { const it = items[id] || {name: id, status: "NO DATA"};
    return `<div class="mw ${esc(it.status)}" onclick="centerOn('${esc(id)}')"><div class="t"><span>${esc(it.name)}</span><span class="pill ${statusCls(it.status)}">${esc(it.status)}</span></div>
      <small class="mono">x ${f1(p.x)} · y ${f1(p.y)} · z ${p.z == null ? "–" : f1(p.z)} m · ${Math.round(Math.hypot(p.x, p.y))} m from hub</small>
      <small>${esc(p.src)}${p.acc ? ` · ±${p.acc} m` : ""}${p.fix_rep ? ` · last check ${esc(p.fix_rep)} ${ago(p.fix_age)}` : ""}</small>
      ${p.pdr ? `<button class="btn small ghost" style="justify-self:start" onclick="event.stopPropagation();resetPos('${esc(id)}')">Reset to hub</button>` : ""}</div>`; }).join("")
    : `<div class="note">No worker on the map yet. Body units appear here once they send data — with a step sensor they start at the hub, without one they show next to their repeater (place it first). Try <b>▶ Demo walker</b>.</div>`;
  setIfChanged("#m-reps", JSON.stringify([ids, M.repeaters, S.repeaters.map(r => [r.id, r.online])]), () => ids.length ? ids.map(id => { const r = M.repeaters[id], L = S.repeaters.find(x => x.id === id);
    return `<div class="mrep"><span><b class="mono">${esc(id)}</b> <span class="note">${L ? (L.online ? "online" : "offline") : "not seen"}</span><br><span class="note mono">${r ? `x ${f1(r.x)} y ${f1(r.y)}` : "not on the map"}</span></span>
      ${r ? `<input type="number" step="1" value="${r.z || 0}" title="z (m)" aria-label="${esc(id)} height" onchange="setRepZ('${esc(id)}', this.value)">` : "<span></span>"}
      <button class="btn small ghost" onclick="$('#m-rep').value='${esc(id)}';setTool('repeater')">${r ? "Move" : "Place"}</button></div>`; }).join("")
    : `<div class="note">No repeaters seen yet.</div>`);
  if (!msEdited && !document.activeElement.id.startsWith("ms-")){
    $("#ms-step").value = M.step_m; $("#ms-dir").value = M.start_dir ?? ""; $("#ms-snap").value = M.snap_rssi; $("#ms-range").value = M.range_m; }
}

/* ================= GAS ================= */
let gasEdited = false;
["#g-model", "#g-rl", "#g-vc", "#g-limit"].forEach(s => $(s).addEventListener("input", () => gasEdited = true));
$("#g-save").onclick = async () => {
  await api("/api/gas", {model: $("#g-model").value, rl_k: $("#g-rl").value, vc: $("#g-vc").value, gas_alarm_mv: $("#g-limit").value});
  gasEdited = false; toast("Gas settings saved.", "SAFE"); poll();
};
async function calibrate(id){ const r = await api("/api/gas/calibrate", {repeater: id});
  toast(r.ok ? `<b>${esc(id)}</b> calibrated: this air now counts as clean.` : esc(r.error), r.ok ? "SAFE" : "WARNING"); poll(); }
const ppmTxt = v => v >= 10000 ? (v / 10000).toFixed(2) + " %" : v >= 100 ? Math.round(v) + " ppm" : v.toFixed(1) + " ppm";
function gasCard(r){
  const g = r.gas, lv = g ? Math.max(0, ...g.gases.filter(q => q.main).map(q => q.level)) : 0;
  const high = lv === 2 || r.gas_local || r.gas_mv >= S.limits.gas_alarm_mv;
  const st = r.gas_missing ? "OFF" : high ? "DANGER" : lv === 1 ? "WARNING" : "SAFE";
  const label = r.gas_missing ? "NO SENSOR" : r.gas_warm ? "WARMING UP" : st;
  const d = (r.gas_spark || []), top = Math.max(S.limits.gas_alarm_mv * 1.1, ...d, 1);
  const pts = d.map((v, i) => `${(i / Math.max(d.length - 1, 1) * 100).toFixed(1)},${(44 - v / top * 40).toFixed(1)}`).join(" ");
  const body = r.gas_missing ? `<div class="note">No gas sensor on this repeater (or not wired). Connect AO through the 10k/20k divider.</div>`
    : r.gas_warm ? `<div class="note"><span class="spin"></span>Sensor heater warming up (about 1 minute after power-on).</div>`
    : !g || !g.cal ? `<div class="note"><span class="spin"></span>Learning the clean-air level… (about 12 readings after warm-up). Keep the sensor in clean air.</div>`
    : g.gases.map(q => `<div class="grow" style="${q.main ? "" : "opacity:.6"}"><span>${esc(q.name)}${q.name !== q.key ? ` <span class="note">${esc(q.key)}</span>` : ""}</span><span class="v ${q.level ? "l" + q.level : ""}">${ppmTxt(q.ppm)}</span>
        <div class="gbar"><i class="${q.level ? "l" + q.level : ""}" style="width:${Math.min(100, Math.max(1.5, q.ppm / q.danger * 100)).toFixed(1)}%"></i></div>
        <small>${q.main ? `warning ${ppmTxt(q.warn)} · danger ${ppmTxt(q.danger)}` : "side reading (sensor not made for this gas) · info only, no alarm"}</small></div>`).join("");
  return `<div class="gcard ${st}"><div class="head"><b class="mono" style="font-size:17px">${esc(r.id)}</b>
      <span class="pill ${st === "OFF" ? "NO" : st}">${label}</span></div>
    <div class="note">${esc(g ? g.model + " · " + g.note : "")}${r.online ? "" : ' · <b style="color:#ff8a8c">repeater offline</b>'}</div>
    ${body}
    ${r.gas_missing ? "" : `<div class="graw"><span>Sensor output <b>${r.gas_mv} mV</b></span><span>Rs <b>${g && g.rs != null ? g.rs + " kΩ" : "–"}</b></span><span>Rs/R0 <b>${g && g.ratio != null ? g.ratio : "–"}</b></span></div>
    ${d.length > 1 ? `<svg viewBox="0 0 100 46" preserveAspectRatio="none" aria-label="Sensor output, last readings"><line x1="0" x2="100" y1="${(44 - S.limits.gas_alarm_mv / top * 40).toFixed(1)}" y2="${(44 - S.limits.gas_alarm_mv / top * 40).toFixed(1)}" stroke="#f0b42999" stroke-dasharray="3 3" stroke-width="1" vector-effect="non-scaling-stroke"/>
      <polyline points="${pts}" fill="none" stroke="${high ? "#ff4d4f" : "#4c9bf0"}" stroke-width="1.8" vector-effect="non-scaling-stroke"/></svg>` : ""}
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span class="note">${g && g.cal ? `R0 ${g.cal.how === "auto" ? "auto-learned" : "calibrated"} at ${esc(g.cal.time)}` : ""}</span>
      ${r.gas_warm ? "" : `<button class="btn small" onclick="calibrate('${esc(r.id)}')">Calibrate in clean air</button>`}</div>`}
  </div>`;
}
function renderGas(){
  const reps = S.repeaters.filter(r => r.gas_mv != null);
  const anyHigh = reps.some(r => !r.gas_missing && ((r.gas && r.gas.gases.some(q => q.main && q.level === 2)) || r.gas_local || r.gas_mv >= S.limits.gas_alarm_mv));
  $("#n-gas").hidden = !anyHigh;
  if (!$("#v-gas").classList.contains("on")) return;
  setIfChanged("#g-model", JSON.stringify(S.gas_models), () => S.gas_models.map(m => `<option>${esc(m)}</option>`).join(""));
  if (!gasEdited && !["g-model", "g-rl", "g-vc", "g-limit"].includes(document.activeElement.id)){
    $("#g-model").value = S.gas_cfg.model; $("#g-rl").value = S.gas_cfg.rl_k; $("#g-vc").value = S.gas_cfg.vc; $("#g-limit").value = S.limits.gas_alarm_mv; }
  $("#g-note").innerHTML = `The model is printed on the side of the sensor (MQ-2, MQ-4 …). Most MQ boards use RL = 1 kΩ (resistor marked <b>102</b>) and run on 5 V.
    Backup alarm: any repeater whose raw sensor output reaches this level alerts everyone, even before calibration.`;
  $("#gascards").innerHTML = reps.length ? reps.map(gasCard).join("")
    : `<div class="empty">No gas readings yet. Repeater firmware with <span class="mono">GAS_ENABLED 1</span> reports its MQ sensor here.</div>`;
}

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
    threading.Thread(target=load_ai, daemon=True).start()
    threading.Thread(target=demo_loop, daemon=True).start()
    print("Admin hub running:  http://localhost:5000   (phone: http://<laptop-ip>:5000/phone)")
    app.run(host="0.0.0.0", port=5000, threaded=True)
