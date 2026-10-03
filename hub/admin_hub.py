# Minimal admin hub for testing the entry station.
#   pip install flask
#   python admin_hub_test.py
# Put this laptop's IP in ADMIN_URL on the ESP (http://<laptop-ip>:5000/api/gear),
# then open http://localhost:5000 to watch events live.
#
# Keeps a UID -> gear registry: a tag is trusted by its factory-locked UID,
# not by the text written on it (anyone with a phone can rewrite that text).
# Registry is in memory only - swap in your real backend/database later.

from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
events = []
registry = {}  # uid -> gear issued at the entry station

PAGE = """
<meta http-equiv="refresh" content="2">
<title>Gear Hub</title>
<h2>Gear events</h2>
<table border="1" cellpadding="5" style="border-collapse:collapse;font-family:sans-serif">
<tr><th>Time</th><th>Station</th><th>Event</th><th>UID</th><th>Gear on tag</th><th>Registry</th><th>Check</th></tr>
{% for e in events %}
<tr style="background:{{ 'white' if e.check in ('OK','ISSUED') else '#ffd6d6' }}">
<td>{{e.time}}</td><td>{{e.station}}</td><td>{{e.event}}</td><td>{{e.uid}}</td>
<td>{{e.gear}}</td><td>{{e.registered}}</td><td>{{e.check}}</td></tr>
{% endfor %}
</table>
<h3>Registry ({{ registry|length }} tags)</h3>
<ul>{% for u, g in registry.items() %}<li>{{u}} : {{g}}</li>{% endfor %}</ul>
"""


@app.post("/api/gear")
def gear():
    d = request.get_json(force=True)
    uid, gear, ev = d.get("uid"), d.get("gear"), d.get("event")

    if ev == "write":
        registry[uid] = gear
        check = "ISSUED"
    else:
        reg = registry.get(uid)
        if reg is None:
            check = "UNKNOWN TAG"
        elif reg == gear:
            check = "OK"
        else:
            check = "MISMATCH"  # tag text doesn't match what was issued

    events.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "station": d.get("station"),
        "event": ev,
        "uid": uid,
        "gear": gear,
        "registered": registry.get(uid, "-"),
        "check": check,
    })
    del events[200:]
    print(events[0])
    return jsonify(ok=True, check=check)


@app.get("/")
def index():
    return render_template_string(PAGE, events=events[:50], registry=registry)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
