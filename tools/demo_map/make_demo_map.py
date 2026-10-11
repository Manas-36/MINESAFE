"""Draws a made-up mine plan (demo_mine_plan.png) and the matching admin map settings (map.json).
Everything is in metres; the image is 8 px per metre with the main shaft bottom at (0, 0), so the
hub can load it already lined up:  copy map.json + demo_mine_plan.png into hub/data/ and hub/data/map/.
FOR TESTING ONLY - not a real mine."""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrow

PPM = 8                                   # pixels per metre
X0, X1, Y0, Y1 = -70, 160, -30, 110       # area drawn, metres
OUT = os.path.dirname(os.path.abspath(__file__))

TUNNELS = [                               # centre lines, metres (also used by the admin map)
    [[-45, 0], [0, 0], [40, 0], [80, 0], [130, 0]],          # main haulage drift (level -40 m)
    [[0, 0], [0, 45]],                                        # XC-0 by the shaft
    [[0, 45], [40, 45], [80, 45], [130, 45]],                 # return airway
    [[40, 0], [40, 45]],                                      # cross-cut XC-1
    [[80, 0], [80, 45]],                                      # cross-cut XC-2
    [[130, 0], [130, 45]],                                    # cross-cut XC-3
    [[80, 45], [80, 90], [125, 90]],                          # panel P-1 development
    [[40, 45], [40, 80]],                                     # panel P-2 (short heading)
]
EXITS = [{"name": "Main shaft", "x": 0, "y": 0},
         {"name": "Escape shaft", "x": 130, "y": 45}]
REPEATERS = {"REP-01": [6, 0], "REP-02": [40, 4], "REP-03": [80, 4], "REP-04": [80, 45],
             "REP-05": [80, 85], "REP-06": [130, 20]}

fig = plt.figure(figsize=((X1 - X0) * PPM / 100, (Y1 - Y0) * PPM / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.axis("off")
fig.patch.set_facecolor("#f4f1e8")
# rock hatching
for x in range(X0 - 140, X1, 6):
    ax.plot([x, x + 140], [Y0, Y1], color="#e4ddc9", lw=0.6, zorder=0)
# tunnels: 4.5 m wide, dark outline + light floor
for line in TUNNELS:
    xs, ys = zip(*line)
    ax.plot(xs, ys, color="#3b3f42", lw=4.5 * PPM * 0.72 + 3, solid_capstyle="round", solid_joinstyle="round", zorder=2)
for line in TUNNELS:
    xs, ys = zip(*line)
    ax.plot(xs, ys, color="#d9d4c5", lw=4.5 * PPM * 0.72, solid_capstyle="round", solid_joinstyle="round", zorder=3)
    ax.plot(xs, ys, color="#9a9384", lw=0.8, ls=(0, (4, 4)), zorder=4)
# goaf / worked-out area
ax.add_patch(Rectangle((92, 55), 30, 26, facecolor="#cfc6ae", edgecolor="#7d7563", hatch="xx", lw=1, zorder=1))
ax.text(107, 68, "GOAF\n(sealed)", ha="center", va="center", fontsize=9, color="#5d5647", zorder=5)
# shafts
for (x, y), name, sub in [((0, 0), "MAIN SHAFT", "downcast · cage · hub"), ((130, 45), "ESCAPE SHAFT", "upcast · ladderway")]:
    ax.add_patch(Circle((x, y), 5, facecolor="#ffffff", edgecolor="#1d1f21", lw=2.5, zorder=6))
    ax.plot([x - 3.5, x + 3.5], [y - 3.5, y + 3.5], color="#1d1f21", lw=2, zorder=7)
    ax.plot([x - 3.5, x + 3.5], [y + 3.5, y - 3.5], color="#1d1f21", lw=2, zorder=7)
    ax.text(x, y - 8.5 if y < 10 else y + 7.5, name, ha="center", fontsize=10, fontweight="bold", color="#1d1f21", zorder=7)
    ax.text(x, y - 12 if y < 10 else y + 11, sub, ha="center", fontsize=8, color="#4a4d50", zorder=7)
# refuge chamber at the west end
ax.add_patch(Rectangle((-58, -6), 13, 12, facecolor="#e7f5ea", edgecolor="#1f7a3a", lw=2, zorder=6))
ax.text(-51.5, 0, "REFUGE\nCHAMBER", ha="center", va="center", fontsize=8, fontweight="bold", color="#1f7a3a", zorder=7)
# labels
lab = dict(fontsize=9, color="#2c2f31", zorder=8, fontweight="bold")
ax.text(60, -5.5, "MAIN HAULAGE DRIFT  (intake air →)", ha="center", **lab)
ax.text(60, 50.5, "RETURN AIRWAY  (← return air)", ha="center", **lab)
for x, n in [(40, "XC-1"), (80, "XC-2"), (130, "XC-3")]:
    ax.text(x + 3.2, 22, n, rotation=90, va="center", **lab)
ax.text(3.2, 22, "XC-0", rotation=90, va="center", **lab)
ax.text(103, 93.5, "PANEL P-1  (development heading)", ha="center", **lab)
ax.text(43, 72, "PANEL P-2", rotation=90, va="center", **lab)
# ventilation stoppings and door
for x, y in [(40, 30), (80, 30)]:
    ax.plot([x - 2.6, x + 2.6], [y, y], color="#b3261e", lw=3, zorder=8)
ax.text(85.5, 30, "air door", fontsize=7, color="#b3261e", va="center", zorder=8)
ax.plot([0, 0], [30 - 2.6, 30 + 2.6], color="#1d1f21", lw=0)
# belt conveyor + pump sump symbols
ax.plot([10, 125], [-1.4, -1.4], color="#5a5f63", lw=1, ls=(0, (1, 2)), zorder=5)
ax.text(118, -10, "belt conveyor", fontsize=7, color="#5a5f63")
ax.add_patch(Circle((-30, -2), 1.8, facecolor="#9cc3e6", edgecolor="#2d5f8a", zorder=6))
ax.text(-30, -8, "sump / pump", fontsize=7, color="#2d5f8a", ha="center")
# scale bar + north arrow + title block
ax.add_patch(Rectangle((X0 + 6, Y0 + 7), 20, 1.6, facecolor="#1d1f21", zorder=9))
ax.add_patch(Rectangle((X0 + 26, Y0 + 7), 20, 1.6, facecolor="#ffffff", edgecolor="#1d1f21", zorder=9))
for v, x in [(0, X0 + 6), (20, X0 + 26), ("40 m", X0 + 46)]:
    ax.text(x, Y0 + 3.2, str(v), ha="center", fontsize=8, zorder=9)
ax.add_patch(FancyArrow(X1 - 12, Y1 - 26, 0, 14, width=1.2, head_width=5, head_length=5, color="#1d1f21", zorder=9))
ax.text(X1 - 12, Y1 - 31, "N", ha="center", fontsize=12, fontweight="bold", zorder=9)
ax.add_patch(Rectangle((X0 + 3, Y1 - 24), 82, 21, facecolor="#ffffff", edgecolor="#1d1f21", lw=1.2, zorder=9))
ax.text(X0 + 6, Y1 - 9, "MINESAFE DEMO MINE — LEVEL −40 m", fontsize=12, fontweight="bold", zorder=10)
ax.text(X0 + 6, Y1 - 15, "Underground plan · scale 1 : 500 · grid in metres from the main shaft", fontsize=8, zorder=10)
ax.text(X0 + 6, Y1 - 20.5, "FICTIONAL PLAN FOR TESTING ONLY — not a real mine", fontsize=8, color="#b3261e", fontweight="bold", zorder=10)
fig.savefig(os.path.join(OUT, "demo_mine_plan.png"), dpi=100, facecolor=fig.get_facecolor())
plt.close(fig)

W, H = (X1 - X0) * PPM, (Y1 - Y0) * PPM
mapcfg = {"image": "demo_mine_plan.png", "img_w": W, "img_h": H, "ox": -X0 * PPM, "oy": Y1 * PPM, "ppm": PPM,
          "repeaters": {k: {"x": v[0], "y": v[1], "z": -40 if k != "REP-01" else -40, "face": None} for k, v in REPEATERS.items()},
          "tunnels": TUNNELS, "start_dir": 90, "step_m": 0.7, "snap_rssi": -55, "range_m": 40.0, "exits": EXITS, "rev": 1}
for r in mapcfg["repeaters"].values():
    r["z"] = 0
json.dump(mapcfg, open(os.path.join(OUT, "map.json"), "w"), indent=2)
print("saved", W, "x", H)
