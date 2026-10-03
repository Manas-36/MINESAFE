# Admin hub v2 - gear events + phone photo verification + body ESP clearance
#   pip install flask
#   python admin_hub.py
#
#   Laptop (admin) : http://localhost:5000
#   Phone (camera) : http://<laptop-ip>:5000/phone   (phone on the same WiFi)
#   Entry station  : ADMIN_URL = http://<laptop-ip>:5000/api/gear
#   Body ESP       : GET http://<laptop-ip>:5000/api/body/<BODY_ID>  -> {"cleared": true/false, ...}
#
# Flow:
#   1. Worker taps gear tags at the entry station (READ mode) -> scans pile up as "pending".
#   2. You open /phone, enter the body unit ID, take the worker's photo, press Send.
#      The photo + all pending scans become one verification card on the admin page.
#   3. Admin checks photo vs gear, types the worker's name, ticks the gear actually
#      worn, and presses APPROVE (or REJECT).
#   4. Approved body unit is "cleared" - body ESP polls /api/body/<id> and starts
#      streaming sensor data once it sees cleared = true.
#
# Everything is in memory (photos saved to ./photos). Swap in a DB later.

import os
import uuid
from datetime import datetime
from flask import (Flask, request, jsonify, render_template_string,
                   redirect, send_from_directory)

app = Flask(__name__)
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")
os.makedirs(PHOTO_DIR, exist_ok=True)

GEAR_LIST = ["HELMET", "VEST", "PANTS", "SHOES"]

events = []          # every scan/write from the entry station
registry = {}        # tag uid -> gear issued
pending_scans = []   # scans since the last photo was sent
verifications = []   # one card per photo
cleared = {}         # body_id -> {"worker": name, "worker_id": .., "gear": [...], "time": ..}


def now():
    return datetime.now().strftime("%H:%M:%S")


# ---------------------------------------------------------------- entry station
@app.post("/api/gear")
def gear():
    d = request.get_json(force=True)
    uid, g, ev = d.get("uid"), d.get("gear"), d.get("event")

    if ev == "write":
        registry[uid] = g
        check = "ISSUED"
    else:
        reg = registry.get(uid)
        check = "UNKNOWN TAG" if reg is None else ("OK" if reg == g else "MISMATCH")
        # remember this scan for the next photo verification (one entry per tag)
        pending_scans[:] = [s for s in pending_scans if s["uid"] != uid]
        pending_scans.append({"uid": uid, "gear": g, "check": check, "time": now()})

    events.insert(0, {"time": now(), "station": d.get("station"), "event": ev,
                      "uid": uid, "gear": g, "registered": registry.get(uid, "-"),
                      "check": check})
    del events[200:]
    print(events[0])
    return jsonify(ok=True, check=check)


# ---------------------------------------------------------------- phone page
PHONE = """
<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Entry Camera</title>
<style>
 body{font-family:sans-serif;margin:0;padding:16px;background:#111;color:#eee}
 h2{margin:0 0 12px} label{display:block;margin:14px 0 4px;font-size:14px;color:#aaa}
 input[type=text]{width:100%;padding:12px;font-size:18px;border-radius:8px;border:0;box-sizing:border-box}
 .cam{display:block;background:#2a6;color:#fff;text-align:center;padding:28px;border-radius:12px;
      font-size:22px;margin-top:16px}
 .cam input{display:none}
 img{width:100%;border-radius:12px;margin-top:12px;display:none}
 button{width:100%;padding:18px;font-size:20px;border:0;border-radius:12px;background:#27f;color:#fff;margin-top:16px}
 .scan{background:#222;padding:10px;border-radius:8px;margin-top:6px;font-size:14px}
 .ok{color:#6d6} .bad{color:#f66} .msg{background:#253;padding:14px;border-radius:8px;margin-bottom:12px}
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
 <input type="text" name="body_id" placeholder="e.g. BODY-03" required>
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

    verifications.insert(0, {
        "id": uuid.uuid4().hex[:8],
        "time": now(),
        "photo": name,
        "body_id": request.form.get("body_id", "").strip().upper(),
        "worker_id": request.form.get("worker_id", "").strip(),
        "scans": list(pending_scans),
        "status": "PENDING",
        "worker": "",
        "gear_ok": [],
    })
    pending_scans.clear()
    return redirect("/phone?msg=Sent! Waiting for admin approval.")


@app.get("/photos/<path:fn>")
def photos(fn):
    return send_from_directory(PHOTO_DIR, fn)


# ---------------------------------------------------------------- admin actions
@app.post("/verify/<vid>")
def verify(vid):
    v = next((x for x in verifications if x["id"] == vid), None)
    if not v:
        return "not found", 404
    action = request.form.get("action")
    v["worker"] = request.form.get("worker", "").strip()
    v["worker_id"] = request.form.get("worker_id", v["worker_id"]).strip()
    v["body_id"] = request.form.get("body_id", v["body_id"]).strip().upper()
    v["gear_ok"] = request.form.getlist("gear")

    if action == "approve":
        v["status"] = "APPROVED"
        cleared[v["body_id"]] = {"worker": v["worker"], "worker_id": v["worker_id"],
                                 "gear": v["gear_ok"], "time": now()}
    else:
        v["status"] = "REJECTED"
        cleared.pop(v["body_id"], None)
    return redirect("/")


@app.post("/revoke/<body_id>")
def revoke(body_id):
    cleared.pop(body_id, None)
    return redirect("/")


# ---------------------------------------------------------------- body ESP
@app.get("/api/body/<body_id>")
def body_status(body_id):
    c = cleared.get(body_id.upper())
    if not c:
        return jsonify(cleared=False)
    return jsonify(cleared=True, worker=c["worker"], worker_id=c["worker_id"], gear=c["gear"])


# ---------------------------------------------------------------- admin page
ADMIN = """
<!doctype html><title>Admin Hub</title>
<style>
 body{font-family:sans-serif;margin:20px;background:#f4f4f4}
 .card{background:#fff;border-radius:10px;padding:14px;margin:10px 0;display:flex;gap:16px;
       box-shadow:0 1px 3px #0002}
 .card img{width:260px;height:260px;object-fit:cover;border-radius:8px}
 .PENDING{border-left:6px solid #f90} .APPROVED{border-left:6px solid #2a2} .REJECTED{border-left:6px solid #d33}
 table{border-collapse:collapse;background:#fff} td,th{border:1px solid #ccc;padding:5px 8px;font-size:14px}
 .bad{background:#ffd6d6} input[type=text]{padding:6px;margin:3px 0;width:220px}
 button{padding:8px 16px;margin-right:6px;border:0;border-radius:6px;color:#fff;cursor:pointer}
 .ap{background:#2a2} .rj{background:#d33}
</style>

<h2>Verifications</h2>
{% for v in verifications %}
<div class="card {{v.status}}">
 <a href="/photos/{{v.photo}}" target="_blank"><img src="/photos/{{v.photo}}"></a>
 <div>
  <b>{{v.status}}</b> &middot; {{v.time}}<br><br>
  <b>Gear scanned:</b><br>
  {% for s in v.scans %}
   <span class="{{'' if s.check=='OK' else 'bad'}}">{{s.gear}} ({{s.uid}}) - {{s.check}}</span><br>
  {% else %}<span class="bad">No gear scanned!</span><br>{% endfor %}
  <br>
  {% if v.status == 'PENDING' %}
  <form method="post" action="/verify/{{v.id}}">
   Worker name<br><input type="text" name="worker" required><br>
   Worker ID<br><input type="text" name="worker_id" value="{{v.worker_id}}"><br>
   Body unit ID<br><input type="text" name="body_id" value="{{v.body_id}}" required><br>
   Gear visible in photo:<br>
   {% set scanned = v.scans|selectattr('check','equalto','OK')|map(attribute='gear')|list %}
   {% for g in gear_list %}
    <label><input type="checkbox" name="gear" value="{{g}}" {{'checked' if g in scanned}}> {{g}}</label>
   {% endfor %}<br><br>
   <button class="ap" name="action" value="approve">APPROVE</button>
   <button class="rj" name="action" value="reject" formnovalidate>REJECT</button>
  </form>
  {% else %}
   Worker: <b>{{v.worker or '-'}}</b> ({{v.worker_id or '-'}})<br>
   Body unit: <b>{{v.body_id}}</b><br>
   Gear confirmed: {{v.gear_ok|join(', ') or 'none'}}
  {% endif %}
 </div>
</div>
{% else %}<p>No photos yet. Open <b>/phone</b> on your mobile.</p>{% endfor %}

<h2>Cleared body units</h2>
<table><tr><th>Body ID</th><th>Worker</th><th>ID</th><th>Gear</th><th>Since</th><th></th></tr>
{% for b, c in cleared.items() %}
<tr><td>{{b}}</td><td>{{c.worker}}</td><td>{{c.worker_id}}</td><td>{{c.gear|join(', ')}}</td><td>{{c.time}}</td>
<td><form method="post" action="/revoke/{{b}}"><button class="rj">Revoke</button></form></td></tr>
{% endfor %}</table>

<h2>Pending scans (not yet in a photo): {{pending|length}}</h2>
<h2>Gear events</h2>
<table><tr><th>Time</th><th>Station</th><th>Event</th><th>UID</th><th>Gear</th><th>Registry</th><th>Check</th></tr>
{% for e in events %}
<tr class="{{'' if e.check in ('OK','ISSUED') else 'bad'}}"><td>{{e.time}}</td><td>{{e.station}}</td>
<td>{{e.event}}</td><td>{{e.uid}}</td><td>{{e.gear}}</td><td>{{e.registered}}</td><td>{{e.check}}</td></tr>
{% endfor %}</table>

<script>
 // auto-refresh every 4 s, but not while the admin is typing in a form
 setInterval(() => {
   const a = document.activeElement;
   if (!a || !['INPUT','BUTTON'].includes(a.tagName)) location.reload();
 }, 4000);
</script>
"""


@app.get("/")
def index():
    return render_template_string(ADMIN, verifications=verifications[:20], events=events[:40],
                                  cleared=cleared, pending=pending_scans, gear_list=GEAR_LIST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
