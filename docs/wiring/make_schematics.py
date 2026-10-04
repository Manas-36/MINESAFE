"""Draws the MineSafe wiring schematics as SVG (docs/wiring/*.svg).

Run:  python docs/wiring/make_schematics.py
Pins come from the firmware #defines; edit here if the wiring changes.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "Arial, Helvetica, sans-serif"
INK, MUTED, PAPER, PANEL = "#1d2327", "#5f6b72", "#ffffff", "#f6f4ef"
AMBER = "#F2A900"
NET = {  # wire colours by net
    "3V3": "#d93025", "5V": "#e8710a", "GND": "#202124", "SDA": "#1a73e8", "SCL": "#188038",
    "SIG": "#9334e6", "ANA": "#00838f", "ONE": "#b06000", "RF": "#5f6368",
}


class Sheet:
    def __init__(self, w, h, title, subtitle):
        self.w, self.h, self.o = w, h, []
        self.o.append(f'<rect width="{w}" height="{h}" fill="{PAPER}"/>')
        self.o.append(f'<rect x="0" y="0" width="{w}" height="10" fill="url(#hz)"/>')
        self.text(40, 52, title, 26, INK, weight=700)
        self.text(40, 78, subtitle, 14, MUTED)

    # primitives -----------------------------------------------------------
    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight=400, family=FONT, italic=False):
        st = ' font-style="italic"' if italic else ""
        s = s.replace("&", "&amp;").replace("<", "&lt;")
        self.o.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" fill="{fill}" '
                      f'text-anchor="{anchor}" font-weight="{weight}"{st}>{s}</text>')

    def wire(self, pts, net, width=2.4, dash=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        da = ' stroke-dasharray="7 5"' if dash else ""
        self.o.append(f'<polyline points="{d}" fill="none" stroke="{NET[net]}" stroke-width="{width}" '
                      f'stroke-linejoin="round" stroke-linecap="round"{da}/>')

    def dot(self, x, y, net):
        self.o.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{NET[net]}"/>')

    def box(self, x, y, w, h, title, sub="", fill=PANEL, stroke=INK, dash=False):
        da = ' stroke-dasharray="8 6"' if dash else ""
        self.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"{da}/>')
        ty = y + min(h / 2 - 4, 36) if sub else y + h / 2 + 5
        self.text(x + w / 2, ty, title, 15, INK, "middle", 700)
        if sub:
            self.text(x + w / 2, ty + 19, sub, 11.5, MUTED, "middle")

    def pin(self, x, y, label, side, net=None):
        """Small square pin on a box edge. side: l r t b (which edge)."""
        self.o.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
        off = {"l": (10, 4, "start"), "r": (-10, 4, "end"), "t": (0, 18, "middle"), "b": (0, -10, "middle")}[side]
        self.text(x + off[0], y + off[1], label, 11.5, INK, off[2], 600)

    def vcc(self, x, y, net="3V3"):  # power flag pointing up, wire end at (x,y)
        c = NET[net]
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-14}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-11}" y1="{y-14}" x2="{x+11}" y2="{y-14}" stroke="{c}" stroke-width="3"/>')
        self.text(x, y - 20, net, 11, c, "middle", 700)

    def gnd(self, x, y):
        c = NET["GND"]
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y+10}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-12}" y1="{y+10}" x2="{x+12}" y2="{y+10}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-7}" y1="{y+15}" x2="{x+7}" y2="{y+15}" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x-3}" y1="{y+20}" x2="{x+3}" y2="{y+20}" stroke="{c}" stroke-width="2.4"/>')

    def resistor(self, x, y, length, vertical, label, net):
        """Zig-zag resistor starting at (x,y); returns end point."""
        c, n, amp = NET[net], 6, 7
        lead = (length - 36) / 2
        pts = []
        if vertical:
            pts = [(x, y), (x, y + lead)]
            for i in range(n):
                pts.append((x + (amp if i % 2 == 0 else -amp), y + lead + 3 + i * 5))
            pts += [(x, y + lead + 36), (x, y + length)]
            self.text(x + 14, y + length / 2 + 4, label, 12, INK, "start", 700)
            end = (x, y + length)
        else:
            pts = [(x, y), (x + lead, y)]
            for i in range(n):
                pts.append((x + lead + 3 + i * 5, y + (amp if i % 2 == 0 else -amp)))
            pts += [(x + lead + 36, y), (x + length, y)]
            self.text(x + length / 2, y - 14, label, 12, INK, "middle", 700)
            end = (x + length, y)
        self.wire(pts, net, 2)
        return end

    def button(self, x, y, label):  # horizontal push button, left lead at (x,y), 70 wide
        c = INK
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x+20}" y2="{y}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+50}" y1="{y}" x2="{x+70}" y2="{y}" stroke="{c}" stroke-width="2.2"/>'
                      f'<circle cx="{x+20}" cy="{y}" r="3" fill="#fff" stroke="{c}" stroke-width="2"/>'
                      f'<circle cx="{x+50}" cy="{y}" r="3" fill="#fff" stroke="{c}" stroke-width="2"/>'
                      f'<line x1="{x+14}" y1="{y-12}" x2="{x+56}" y2="{y-12}" stroke="{c}" stroke-width="2.2"/>'
                      f'<line x1="{x+35}" y1="{y-12}" x2="{x+35}" y2="{y-22}" stroke="{c}" stroke-width="2.2"/>')
        self.text(x + 35, y - 28, label, 12, INK, "middle", 700)
        return (x + 70, y)

    def led(self, x, y, label):  # horizontal LED, anode at (x,y), 50 wide
        c = "#d93025"
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x+14}" y2="{y}" stroke="{INK}" stroke-width="2.2"/>'
                      f'<polygon points="{x+14},{y-11} {x+14},{y+11} {x+34},{y}" fill="{c}" stroke="{INK}" stroke-width="1.6"/>'
                      f'<line x1="{x+34}" y1="{y-11}" x2="{x+34}" y2="{y+11}" stroke="{INK}" stroke-width="2.4"/>'
                      f'<line x1="{x+34}" y1="{y}" x2="{x+50}" y2="{y}" stroke="{INK}" stroke-width="2.2"/>'
                      f'<path d="M{x+22},{y-16} l8,-9 M{x+28},{y-15} l8,-9" stroke="{c}" stroke-width="1.6" fill="none"/>')
        self.text(x + 25, y + 28, label, 12, INK, "middle", 700)
        return (x + 50, y)

    def antenna(self, x, y, label):
        c = NET["RF"]
        self.o.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-30}" stroke="{c}" stroke-width="2.4"/>'
                      f'<polyline points="{x-14},{y-52} {x},{y-30} {x+14},{y-52}" fill="none" stroke="{c}" stroke-width="2.4"/>'
                      f'<line x1="{x}" y1="{y-30}" x2="{x}" y2="{y-54}" stroke="{c}" stroke-width="2.4"/>')
        self.text(x + 20, y - 40, label, 12, MUTED, "start", 600)

    def note(self, x, y, lines, w=360):
        h = 26 + 19 * len(lines)
        self.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff8e1" stroke="{AMBER}" stroke-width="2"/>')
        for i, s in enumerate(lines):
            self.text(x + 14, y + 24 + 19 * i, s, 12.5, INK, weight=700 if i == 0 else 400)

    def legend(self, x, y, nets):
        self.text(x, y + 4, "WIRES:", 11, MUTED, weight=700)
        xx = x + 60
        for net, lab in nets:
            self.wire([(xx, y), (xx + 26, y)], net, 3)
            self.text(xx + 34, y + 4, lab, 12, INK)
            xx += 52 + 7.2 * len(lab)

    def save(self, name):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
               f'<defs><pattern id="hz" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               f'<rect width="14" height="28" fill="{AMBER}"/><rect x="14" width="14" height="28" fill="#12171A"/></pattern></defs>'
               + "".join(self.o) + "</svg>")
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


def mcu(s, x, y, w, h, title, sub, left, right):
    """Board with pins. left/right: list of (y_offset, label). returns dict label->(x,y)."""
    s.box(x, y, w, h, "", "", fill="#12171A", stroke="#12171A")
    s.text(x + w / 2, y + 34, title, 16, "#F3F0E8", "middle", 700)
    s.text(x + w / 2, y + 54, sub, 11.5, AMBER, "middle", 600)
    P = {}
    for dy, lab in left:
        px, py = x, y + dy
        s.o.append(f'<rect x="{px-5}" y="{py-5}" width="10" height="10" fill="{AMBER}"/>')
        s.text(px + 12, py + 4, lab, 12, "#F3F0E8", "start", 600)
        P[lab] = (px - 5, py)
    for dy, lab in right:
        px, py = x + w, y + dy
        s.o.append(f'<rect x="{px-5}" y="{py-5}" width="10" height="10" fill="{AMBER}"/>')
        s.text(px - 12, py + 4, lab, 12, "#F3F0E8", "end", 600)
        P[lab] = (px + 5, py)
    return P


# ===================================================================== body
def body():
    s = Sheet(1560, 940, "Body unit — wiring schematic",
              "Worn by the miner · ESP32-S3 DevKit (pin names shown as  S3 GPIO / XIAO ESP32-C6 pin) · all sensors on 3.3 V")
    P = mcu(s, 190, 150, 260, 600, "ESP32-S3 DevKit", "or Seeed XIAO ESP32-C6",
            left=[(110, "3V3"), (200, "5V (USB)"), (540, "GND")],
            right=[(130, "GPIO8 / D4  SDA"), (170, "GPIO9 / D5  SCL"), (300, "GPIO7 / D3"),
                   (380, "GPIO1 / D0  ADC"), (460, "GPIO5 / D8"), (530, "GPIO4 / D10")])
    # power at the board
    x3, y3 = P["3V3"]; s.wire([(x3, y3), (x3 - 30, y3), (x3 - 30, y3 - 30)], "3V3"); s.vcc(x3 - 30, y3 - 30)
    x5, y5 = P["5V (USB)"]; s.wire([(x5, y5), (x5 - 30, y5)], "5V"); s.text(x5 - 34, y5 + 22, "USB / power bank", 11, MUTED, "end")
    s.text(x5 - 34, y5 + 37, "(Li-ion + charger: Week 12)", 11, MUTED, "end", italic=True)
    xg, yg = P["GND"]; s.wire([(xg, yg), (xg - 30, yg), (xg - 30, yg + 20)], "GND"); s.gnd(xg - 30, yg + 20)

    # I2C bus
    sda_y, scl_y = P["GPIO8 / D4  SDA"][1], P["GPIO9 / D5  SCL"][1]
    bus_end = 1300
    s.wire([P["GPIO8 / D4  SDA"], (bus_end, sda_y)], "SDA", 3)
    s.wire([P["GPIO9 / D5  SCL"], (bus_end, scl_y)], "SCL", 3)
    s.text(bus_end + 8, sda_y + 4, "SDA", 12, NET["SDA"], weight=700)
    s.text(bus_end + 8, scl_y + 4, "SCL", 12, NET["SCL"], weight=700)
    s.text(1000, scl_y + 22, "I²C bus · 400 kHz · shared by 3 sensors", 12, MUTED, weight=600)
    mods = [(560, "MPU6050 (GY-521)", "accel + gyro · 0x68"), (820, "BMP180", "pressure / height · 0x77"),
            (1080, "MAX30100 / 30102", "heart rate + SpO₂ · 0x57")]
    for mx, t, sub in mods:
        my, mw, mh = 138, 190, 96       # box above the bus
        s.box(mx, my - 0, mw, mh, t, sub)
        # pins on bottom edge: VCC GND SCL SDA
        pv, pg, pc, pd = mx + 25, mx + 70, mx + 120, mx + 165
        yb = my + mh
        for px, lab in ((pv, "VCC"), (pg, "GND"), (pc, "SCL"), (pd, "SDA")):
            s.pin(px, yb, lab, "b")
        s.wire([(pd, yb), (pd, sda_y)], "SDA"); s.dot(pd, sda_y, "SDA")
        s.wire([(pc, yb), (pc, scl_y)], "SCL"); s.dot(pc, scl_y, "SCL")
        # VCC/GND go up via the top: route around box
        s.wire([(pv, yb), (pv, yb + 9), (mx - 14, yb + 9), (mx - 14, my - 20), (mx + 20, my - 20)], "3V3")
        s.vcc(mx + 20, my - 20)
        s.wire([(pg, yb), (pg, yb + 9), (mx + mw + 12, yb + 9), (mx + mw + 12, my - 4)], "GND")
        s.gnd(mx + mw + 12, my - 4) if False else None
        s.o.append(f'<line x1="{mx+mw+12}" y1="{my-4}" x2="{mx+mw+12}" y2="{my-18}" stroke="{NET["GND"]}" stroke-width="2.4"/>')
        s.text(mx + mw + 12, my - 24, "GND", 11, NET["GND"], "middle", 700)

    # DS18B20 with pull-up
    y7 = P["GPIO7 / D3"][1]
    s.box(840, y7 - 55, 200, 110, "DS18B20", "body temperature · 1-Wire")
    s.pin(840, y7, "DQ", "l")
    s.pin(940, y7 - 55, "VDD", "t"); s.pin(1040, y7 + 20, "GND", "r")
    s.wire([P["GPIO7 / D3"], (840, y7)], "ONE")
    s.dot(640, y7, "ONE")
    s.resistor(640, y7 - 90, 90, True, "4.7 kΩ pull-up", "3V3")
    s.vcc(640, y7 - 90)
    s.wire([(940, y7 - 55), (940, y7 - 75)], "3V3"); s.vcc(940, y7 - 75)
    s.wire([(1040, y7 + 20), (1080, y7 + 20)], "GND"); s.gnd(1080, y7 + 20)

    # HW-827 pulse sensor (backup)
    y1 = P["GPIO1 / D0  ADC"][1]
    s.box(1140, y1 - 55, 200, 110, "HW-827 pulse", "analog backup for HR", dash=True)
    s.pin(1140, y1, "S", "l"); s.pin(1210, y1 - 55, "+", "t"); s.pin(1270, y1 + 55, "−", "b")
    s.wire([P["GPIO1 / D0  ADC"], (1140, y1)], "ANA")
    s.wire([(1210, y1 - 55), (1210, y1 - 75)], "3V3"); s.vcc(1210, y1 - 75)
    s.wire([(1270, y1 + 55), (1270, y1 + 67)], "GND"); s.gnd(1270, y1 + 67)

    # SOS button
    y5b = P["GPIO5 / D8"][1]
    s.wire([P["GPIO5 / D8"], (720, y5b)], "SIG")
    e = s.button(720, y5b, "SOS / I'm OK button")
    s.wire([e, (840, y5b), (840, y5b + 14)], "GND"); s.gnd(840, y5b + 14)
    s.text(500, y5b + 22, "INPUT_PULLUP (no resistor)", 11, MUTED)

    # LED
    y4 = P["GPIO4 / D10"][1]
    end = s.resistor(P["GPIO4 / D10"][0], y4, 170, False, "220 Ω", "SIG")
    e2 = s.led(end[0], y4, "Alert LED (red)")
    s.wire([e2, (e2[0] + 40, y4), (e2[0] + 40, y4 + 14)], "GND"); s.gnd(e2[0] + 40, y4 + 14)

    # antenna
    s.antenna(230, 150, "u.FL (XIAO C6)")

    s.note(1090, 660, ["Notes",
                       "• All sensor boards on 3V3 — never 5 V on the ESP pins.",
                       "• MAX3010x pulls I²C to 1.8 V; shared bus with GY-521",
                       "  3.3 V pull-ups makes it read reliably.",
                       "• Keep still 3 s at power-on (gyro calibration).",
                       "• Dashed = optional part."], 440)
    s.legend(190, 900, [("3V3", "3.3 V"), ("5V", "5 V"), ("GND", "Ground"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL"),
                        ("ONE", "1-Wire data"), ("ANA", "Analog"), ("SIG", "Digital I/O")])
    s.save("body_unit.svg")


# ================================================================= repeater
def repeater():
    s = Sheet(1400, 1040, "Repeater node — wiring schematic",
              "Main repeater (IS_GATEWAY 1, joins Wi-Fi) and tunnel repeaters (IS_GATEWAY 0) use the same circuit · buzzer + MQ gas + AHT air sensor")
    P = mcu(s, 170, 140, 260, 660, "ESP32-S3 DevKit", "or Seeed XIAO ESP32-C6",
            left=[(110, "5V (USB)"), (200, "3V3"), (420, "GND")],
            right=[(140, "GPIO5 / D10"), (300, "GPIO4 / D2  ADC"), (570, "GPIO8 / D4  SDA"), (610, "GPIO9 / D5  SCL")])
    x5, y5 = P["5V (USB)"]; s.wire([(x5, y5), (x5 - 30, y5), (x5 - 30, y5 - 30)], "5V"); s.vcc(x5 - 30, y5 - 30, "5V")
    s.text(x5 - 44, y5 - 26, "USB 5 V adapter", 11, MUTED, "end")
    x3, y3 = P["3V3"]; s.wire([(x3, y3), (x3 - 30, y3), (x3 - 30, y3 - 24)], "3V3"); s.vcc(x3 - 30, y3 - 24)
    s.text(x3 - 34, y3 + 18, "to AHT VCC", 11, MUTED, "end")
    xg, yg = P["GND"]; s.wire([(xg, yg), (xg - 30, yg), (xg - 30, yg + 20)], "GND"); s.gnd(xg - 30, yg + 20)

    # buzzer
    yb = P["GPIO5 / D10"][1]
    s.box(620, yb - 45, 210, 90, "Buzzer", "active, 3–5 V")
    s.pin(620, yb - 15, "+", "l"); s.pin(620, yb + 20, "−", "l")
    s.wire([P["GPIO5 / D10"], (620, yb - 15)], "SIG") if False else s.wire([P["GPIO5 / D10"], (520, yb), (520, yb - 15), (620, yb - 15)], "SIG")
    s.wire([(620, yb + 20), (580, yb + 20), (580, yb + 70)], "GND"); s.gnd(580, yb + 70)
    s.text(880, yb - 18, "Passive buzzer → BUZZER_PASSIVE 1", 11.5, MUTED)
    s.text(880, yb, "3-pin low-trigger module → BUZZER_ACTIVE_LOW 1,", 11.5, MUTED)
    s.text(880, yb + 18, "module VCC to 5V", 11.5, MUTED)

    # MQ sensor + divider
    ya = P["GPIO4 / D2  ADC"][1]
    mx, my = 1000, ya + 50
    s.box(mx, my - 70, 280, 170, "MQ gas sensor", "MQ-2 / MQ-7 / MQ-135 module")
    s.pin(mx, my - 30, "VCC", "l"); s.pin(mx, my, "AO", "l"); s.pin(mx, my + 30, "DO", "l"); s.pin(mx, my + 60, "GND", "l")
    s.text(mx - 12, my + 34, "nc", 11, MUTED, "end")
    s.wire([(mx, my - 30), (940, my - 30), (940, my - 70)], "5V"); s.vcc(940, my - 70, "5V")
    s.wire([(mx, my + 60), (950, my + 60), (950, my + 110)], "GND"); s.gnd(950, my + 110)
    node_x = 640
    end = s.resistor(720, my, 170, False, "10 kΩ", "ANA")
    s.wire([end, (mx, my)], "ANA")
    s.wire([(node_x, my), (720, my)], "ANA")
    s.dot(node_x, my, "ANA")
    s.wire([P["GPIO4 / D2  ADC"], (node_x, ya), (node_x, my)], "ANA")
    s.resistor(node_x, my, 110, True, "20 kΩ", "ANA")
    s.gnd(node_x, my + 110)
    s.text(node_x - 14, my - 10, "0–3.3 V", 11.5, MUTED, "end", 700)
    s.text(930, my - 10, "0–5 V", 11.5, MUTED, "middle", 700)
    s.text(mx + 140, my + 130, "pin order differs between modules — match the labels", 11, MUTED, "middle", italic=True)
    # AHT10 / AHT20 / AHT25 air temperature + humidity (I2C 0x38)
    sda_y, scl_y = P["GPIO8 / D4  SDA"][1], P["GPIO9 / D5  SCL"][1]
    ax, ay, aw, ah = 760, sda_y - 60, 270, 160
    s.box(ax, ay, aw, ah, "AHT20 / AHT10 / AHT25", "air temp + humidity · I²C 0x38")
    s.pin(ax, sda_y - 30, "VCC", "l"); s.pin(ax, sda_y, "SDA", "l"); s.pin(ax, scl_y, "SCL", "l"); s.pin(ax, scl_y + 30, "GND", "l")
    s.wire([P["GPIO8 / D4  SDA"], (ax, sda_y)], "SDA", 3)
    s.wire([P["GPIO9 / D5  SCL"], (ax, scl_y)], "SCL", 3)
    s.wire([(ax, sda_y - 30), (700, sda_y - 30), (700, sda_y - 60)], "3V3"); s.vcc(700, sda_y - 60)
    s.wire([(ax, scl_y + 30), (720, scl_y + 30), (720, scl_y + 60)], "GND"); s.gnd(720, scl_y + 60)
    s.text(ax + aw + 20, sda_y - 18, "Module has its own pull-ups (no resistors needed)", 11.5, MUTED)
    s.text(ax + aw + 20, sda_y, "AHT_ENABLED 1 · reads every 2 s", 11.5, MUTED)
    s.text(ax + aw + 20, sda_y + 18, "XIAO C6: D4 = GPIO22, D5 = GPIO23", 11.5, MUTED)
    s.text(ax + aw + 20, sda_y + 36, "Keep it out of the buzzer / MQ heater air flow", 11.5, MUTED)
    s.antenna(210, 140, "u.FL (XIAO C6)")
    s.note(170, 860, ["Divider: V_pin = V_AO × 20k / (10k + 20k) = 0.667 × V_AO",
                     "Firmware multiplies by 1.5 to recover the sensor voltage; MQ heater needs 5 V, ~150 mA, 60 s warm-up.",
                     "AHT on 3.3 V only. Hub works out wet-bulb temperature: warning 30.5 °C, danger 33.5 °C."], 860)
    s.legend(170, 1000, [("3V3", "3.3 V"), ("5V", "5 V"), ("GND", "Ground"), ("ANA", "Analog (MQ AO)"), ("SIG", "Digital out"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL")])
    s.save("repeater_node.svg")


# ============================================================ entry station
def entry():
    s = Sheet(1300, 780, "Entry station — wiring schematic",
              "Gear-tag gate · Seeed XIAO ESP32-S3 Sense (camera) + PN532 (I²C) + SSD1306 OLED + 3 buttons · NTAG215 tags on helmet, vest, pants, shoes")
    P = mcu(s, 150, 140, 260, 470, "XIAO ESP32-S3 Sense", "entry station + camera",
            left=[(110, "3V3"), (420, "GND")],
            right=[(130, "D4 GPIO5  SDA"), (170, "D5 GPIO6  SCL"), (250, "B2B camera"), (310, "D1 GPIO2"), (370, "D0 GPIO1"), (430, "D3 GPIO4")])
    x3, y3 = P["3V3"]; s.wire([(x3, y3), (x3 - 30, y3), (x3 - 30, y3 - 30)], "3V3"); s.vcc(x3 - 30, y3 - 30)
    xg, yg = P["GND"]; s.wire([(xg, yg), (xg - 30, yg), (xg - 30, yg + 20)], "GND"); s.gnd(xg - 30, yg + 20)
    sda_y, scl_y = P["D4 GPIO5  SDA"][1], P["D5 GPIO6  SCL"][1]
    s.wire([P["D4 GPIO5  SDA"], (1060, sda_y)], "SDA", 3); s.wire([P["D5 GPIO6  SCL"], (1060, scl_y)], "SCL", 3)
    s.text(460, scl_y + 22, "I²C bus (Wire, port 0)", 12, MUTED, weight=600)
    for mx, t, sub in ((520, "PN532 NFC", "DIP: SEL0=1 SEL1=0 → I²C · 0x24"), (820, "SSD1306 OLED", "0.96\" 128×64 · 0x3C")):
        my, mw, mh = 138, 230, 96
        s.box(mx, my, mw, mh, t, sub)
        pv, pg, pc, pd = mx + 30, mx + 80, mx + 140, mx + 190
        yb = my + mh
        for px, lab in ((pv, "VCC"), (pg, "GND"), (pc, "SCL"), (pd, "SDA")):
            s.pin(px, yb, lab, "b")
        s.wire([(pd, yb), (pd, sda_y)], "SDA"); s.dot(pd, sda_y, "SDA")
        s.wire([(pc, yb), (pc, scl_y)], "SCL"); s.dot(pc, scl_y, "SCL")
        s.wire([(pv, yb), (pv, yb + 9), (mx - 14, yb + 9), (mx - 14, my - 20), (mx + 20, my - 20)], "3V3"); s.vcc(mx + 20, my - 20)
        s.wire([(pg, yb), (pg, yb + 9), (mx + mw + 12, yb + 9), (mx + mw + 12, my - 4)], "GND")
        s.o.append(f'<line x1="{mx+mw+12}" y1="{my-4}" x2="{mx+mw+12}" y2="{my-18}" stroke="{NET["GND"]}" stroke-width="2.4"/>')
        s.text(mx + mw + 12, my - 24, "GND", 11, NET["GND"], "middle", 700)
    # camera on the Sense expansion board
    cx, cy = P["B2B camera"]
    s.box(820, cy - 40, 260, 80, "OV2640 / OV3660 camera", "Sense board · own I²C on GPIO39/40 (port 1)")
    s.wire([(cx, cy), (820, cy)], "RF", 3, dash=True)
    s.text(620, cy - 10, "board-to-board connector, no wires", 11.5, MUTED, "middle", 600)
    for lab, name in (("D1 GPIO2", "READ button"), ("D0 GPIO1", "WRITE button"), ("D3 GPIO4", "PHOTO button")):
        x, y = P[lab]
        s.wire([(x, y), (560, y)], "SIG")
        e = s.button(560, y, name)
        s.wire([e, (680, y), (680, y + 14)], "GND"); s.gnd(680, y + 14)
    s.text(460, P["D3 GPIO4"][1] + 40, "INPUT_PULLUP on all buttons", 11, MUTED)
    s.box(860, 450, 260, 80, "NTAG215 tags ×4", "helmet · vest · pants · shoes", fill="#fff", dash=True)
    s.text(990, 552, "tapped on the PN532 · 13.56 MHz · ~3 cm", 11.5, MUTED, "middle", 600)
    s.note(150, 650, ["PSRAM: OPI (Tools menu) · photo SVGA JPEG → POST /api/camphoto · scans → POST /api/gear",
                      "Wi-Fi credentials in secrets.h (not in git) · hub auto-found on the hotspot subnet · libs: Adafruit PN532, SSD1306, GFX"], 1000)
    s.legend(150, 750, [("3V3", "3.3 V"), ("GND", "Ground"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL"), ("SIG", "Button"), ("RF", "Camera connector")])
    s.save("entry_station.svg")


# ================================================================== system
def system():
    s = Sheet(1500, 640, "MineSafe — system interconnection", "How every unit talks · solid = data up, dashed = alert down")
    def unit(x, y, w, h, t, sub, dark=False):
        if dark:
            s.box(x, y, w, h, "", "", fill="#12171A", stroke="#12171A")
            s.text(x + w / 2, y + h / 2 - 4, t, 15, "#F3F0E8", "middle", 700)
            s.text(x + w / 2, y + h / 2 + 16, sub, 11.5, AMBER, "middle", 600)
        else:
            s.box(x, y, w, h, t, sub)
    unit(60, 300, 200, 90, "Body units", "S3 (sensors) · C6 mock · phone")
    unit(360, 300, 180, 90, "REP-03", "XIAO C6 · 2 hops")
    unit(640, 300, 180, 90, "REP-02", "XIAO C6 · 1 hop")
    unit(920, 300, 200, 90, "REP-01 (main)", "XIAO C6 · Wi-Fi to hub")
    unit(1220, 300, 230, 90, "Admin hub", "laptop · Flask · AI · map", dark=True)
    unit(1220, 120, 230, 80, "Entry station", "XIAO S3 Sense · RFID + camera")
    unit(1220, 480, 230, 80, "Phone camera", "entry photo · test worker")
    for a, b in ((260, 360), (540, 640), (820, 920)):
        s.wire([(a, 330), (b, 330)], "SDA", 3); s.wire([(b, 360), (a, 360)], "ANA", 2.4, dash=True)
        s.text((a + b) / 2, 320, "ESP-NOW", 12, NET["SDA"], "middle", 700)
    s.wire([(1120, 330), (1220, 330)], "SCL", 3); s.wire([(1220, 360), (1120, 360)], "ANA", 2.4, dash=True)
    s.text(1170, 318, "Wi-Fi HTTP", 11.5, NET["SCL"], "middle", 700); s.text(1170, 380, "1 s", 11, MUTED, "middle")
    s.wire([(1335, 200), (1335, 300)], "SCL", 3); s.text(1345, 255, "Wi-Fi", 11.5, NET["SCL"], weight=700)
    s.wire([(1335, 480), (1335, 390)], "SCL", 3); s.text(1345, 440, "Wi-Fi", 11.5, NET["SCL"], weight=700)
    for x in (450, 730, 1020):
        s.box(x - 60, 470, 120, 50, "MQ + buzzer", "", fill="#fff")
        s.wire([(x, 390), (x, 470)], "RF", 2)
    s.note(60, 120, ["Packet: 54 bytes / worker / second (MS_VER 3)",
                     "Up: telemetry hops to the main repeater, then HTTP POST to /api/telemetry.",
                     "Down: alert in the HTTP reply → repeater beacons → every buzzer + body LED.",
                     "Routes self-heal: parent = neighbour with fewest hops, RSSI ≥ −92 dBm."], 760)
    s.legend(60, 600, [("SDA", "ESP-NOW data (2.4 GHz)"), ("SCL", "Wi-Fi / HTTP"), ("ANA", "Alert path (dashed)")])
    s.save("system_overview.svg")


if __name__ == "__main__":
    body(); repeater(); entry(); system()
