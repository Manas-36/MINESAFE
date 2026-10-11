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
              "Worn by the miner · ESP32-C6-WROOM-1 DevKit (board: ESP32C6 Dev Module) · all sensors on 3.3 V · S3 / XIAO C6 pins in the firmware")
    P = mcu(s, 190, 150, 260, 600, "ESP32-C6-WROOM-1", "DevKit · on-board PCB antenna",
            left=[(110, "3V3"), (200, "5V (USB)"), (540, "GND")],
            right=[(130, "GPIO6  SDA"), (170, "GPIO7  SCL"), (300, "GPIO10  1-Wire"),
                   (380, "GPIO2  ADC"), (460, "GPIO18"), (530, "GPIO19")])
    x3, y3 = P["3V3"]; s.wire([(x3, y3), (x3 - 30, y3), (x3 - 30, y3 - 30)], "3V3"); s.vcc(x3 - 30, y3 - 30)
    x5, y5 = P["5V (USB)"]; s.wire([(x5, y5), (x5 - 30, y5)], "5V"); s.text(x5 - 34, y5 + 22, "USB / power bank", 11, MUTED, "end")
    s.text(x5 - 34, y5 + 37, "(Li-ion + charger in V4)", 11, MUTED, "end", italic=True)
    xg, yg = P["GND"]; s.wire([(xg, yg), (xg - 30, yg), (xg - 30, yg + 20)], "GND"); s.gnd(xg - 30, yg + 20)

    sda_y, scl_y = P["GPIO6  SDA"][1], P["GPIO7  SCL"][1]
    bus_end = 1300
    s.wire([P["GPIO6  SDA"], (bus_end, sda_y)], "SDA", 3)
    s.wire([P["GPIO7  SCL"], (bus_end, scl_y)], "SCL", 3)
    s.text(bus_end + 8, sda_y + 4, "SDA", 12, NET["SDA"], weight=700)
    s.text(bus_end + 8, scl_y + 4, "SCL", 12, NET["SCL"], weight=700)
    s.text(1000, scl_y + 22, "I²C bus · shared by 3 sensors (all in parallel)", 12, MUTED, weight=600)
    mods = [(560, "MPU6050 (GY-521)", "accel + gyro · 0x68"), (820, "BMP180", "pressure / height · 0x77"),
            (1080, "MAX30100 / 30102", "heart rate + SpO₂ · 0x57")]
    for mx, t, sub in mods:
        my, mw, mh = 138, 190, 96
        s.box(mx, my, mw, mh, t, sub, dash=(mx == 1080))
        pv, pg, pc, pd = mx + 25, mx + 70, mx + 120, mx + 165
        yb = my + mh
        for px, lab in ((pv, "VCC"), (pg, "GND"), (pc, "SCL"), (pd, "SDA")):
            s.pin(px, yb, lab, "b")
        s.wire([(pd, yb), (pd, sda_y)], "SDA"); s.dot(pd, sda_y, "SDA")
        s.wire([(pc, yb), (pc, scl_y)], "SCL"); s.dot(pc, scl_y, "SCL")
        s.wire([(pv, yb), (pv, yb + 9), (mx - 14, yb + 9), (mx - 14, my - 20), (mx + 20, my - 20)], "3V3")
        s.vcc(mx + 20, my - 20)
        s.wire([(pg, yb), (pg, yb + 9), (mx + mw + 12, yb + 9), (mx + mw + 12, my - 4)], "GND")
        s.o.append(f'<line x1="{mx+mw+12}" y1="{my-4}" x2="{mx+mw+12}" y2="{my-18}" stroke="{NET["GND"]}" stroke-width="2.4"/>')
        s.text(mx + mw + 12, my - 24, "GND", 11, NET["GND"], "middle", 700)

    y7 = P["GPIO10  1-Wire"][1]
    s.box(840, y7 - 55, 200, 110, "DS18B20", "skin temperature · 1-Wire")
    s.pin(840, y7, "DQ", "l")
    s.pin(940, y7 - 55, "VDD", "t"); s.pin(1040, y7 + 20, "GND", "r")
    s.wire([P["GPIO10  1-Wire"], (840, y7)], "ONE")
    s.dot(640, y7, "ONE")
    s.resistor(640, y7 - 90, 90, True, "4.7 kΩ pull-up", "3V3")
    s.vcc(640, y7 - 90)
    s.wire([(940, y7 - 55), (940, y7 - 75)], "3V3"); s.vcc(940, y7 - 75)
    s.wire([(1040, y7 + 20), (1080, y7 + 20)], "GND"); s.gnd(1080, y7 + 20)
    s.text(660, y7 + 26, "red → 3V3 · black → GND · yellow → GPIO10", 11, MUTED)

    y1 = P["GPIO2  ADC"][1]
    s.box(1140, y1 - 55, 200, 110, "HW-827 pulse", "analog heart-rate sensor")
    s.pin(1140, y1, "S", "l"); s.pin(1210, y1 - 55, "+", "t"); s.pin(1270, y1 + 55, "−", "b")
    s.wire([P["GPIO2  ADC"], (1140, y1)], "ANA")
    s.wire([(1210, y1 - 55), (1210, y1 - 75)], "3V3"); s.vcc(1210, y1 - 75)
    s.wire([(1270, y1 + 55), (1270, y1 + 67)], "GND"); s.gnd(1270, y1 + 67)

    y5b = P["GPIO18"][1]
    s.wire([P["GPIO18"], (720, y5b)], "SIG")
    e = s.button(720, y5b, "SOS / I'm OK button")
    s.wire([e, (840, y5b), (840, y5b + 14)], "GND"); s.gnd(840, y5b + 14)
    s.text(500, y5b + 22, "INPUT_PULLUP (no resistor)", 11, MUTED)

    y4 = P["GPIO19"][1]
    end = s.resistor(P["GPIO19"][0], y4, 170, False, "220 Ω", "SIG")
    e2 = s.led(end[0], y4, "Alert LED (red)")
    s.wire([e2, (e2[0] + 40, y4), (e2[0] + 40, y4 + 14)], "GND"); s.gnd(e2[0] + 40, y4 + 14)

    s.note(1050, 640, ["Notes",
                       "• All sensor boards on 3V3 — never 5 V on the ESP pins.",
                       "• Avoid GPIO8 (RGB LED), 9 (BOOT), 4/5/15 (strapping),",
                       "  12/13 (USB). Only GPIO0–6 read analog on the C6.",
                       "• Check first with firmware/tests/body_sensor_test.",
                       "• Keep still 3 s at power-on (gyro calibration).",
                       "• Dashed = optional part."], 470)
    s.legend(190, 900, [("3V3", "3.3 V"), ("5V", "5 V"), ("GND", "Ground"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL"),
                        ("ONE", "1-Wire data"), ("ANA", "Analog"), ("SIG", "Digital I/O")])
    s.save("body_unit.svg")


# ================================================================= repeater
def repeater():
    s = Sheet(1500, 1360, "Repeater node v3.3 — wiring schematic",
              "Seeed XIAO ESP32-C6 (ESP32-S3 pin in brackets) · LED exit sign + buzzer + 3 MQ gas channels + AHT air sensor + SOS · main repeater = IS_GATEWAY 1")
    P = mcu(s, 170, 140, 290, 1000, "Seeed XIAO ESP32-C6", "or ESP32-S3 DevKit [pins in brackets]",
            left=[(110, "5V (USB)"), (200, "3V3"), (600, "GND")],
            right=[(120, "D10 GPIO18 [S3 5]"), (260, "D9 GPIO20 [S3 11]"), (300, "D3 GPIO21 [S3 10]"),
                   (340, "D8 GPIO19 [S3 12]"), (430, "D2 GPIO2 [S3 4] ADC"), (560, "D0 GPIO0 [S3 6] ADC"),
                   (690, "D1 GPIO1 [S3 7] ADC"), (870, "D6 GPIO16 [S3 13]"), (940, "D4 GPIO22 [S3 8] SDA"),
                   (980, "D5 GPIO23 [S3 9] SCL")])
    x5, y5 = P["5V (USB)"]; s.wire([(x5, y5), (x5 - 30, y5), (x5 - 30, y5 - 30)], "5V"); s.vcc(x5 - 30, y5 - 30, "5V")
    s.text(x5 - 44, y5 - 26, "USB 5 V, 2 A", 11, MUTED, "end")
    s.text(x5 - 44, y5 - 10, "(matrix + 3 MQ heaters)", 11, MUTED, "end")
    x3, y3 = P["3V3"]; s.wire([(x3, y3), (x3 - 30, y3), (x3 - 30, y3 - 24)], "3V3"); s.vcc(x3 - 30, y3 - 24)
    xg, yg = P["GND"]; s.wire([(xg, yg), (xg - 30, yg), (xg - 30, yg + 20)], "GND"); s.gnd(xg - 30, yg + 20)

    # buzzer
    yb = P["D10 GPIO18 [S3 5]"][1]
    s.box(640, yb - 45, 210, 90, "Buzzer", "active, 3–5 V")
    s.pin(640, yb - 15, "+", "l"); s.pin(640, yb + 20, "−", "l")
    s.wire([P["D10 GPIO18 [S3 5]"], (540, yb), (540, yb - 15), (640, yb - 15)], "SIG")
    s.wire([(640, yb + 20), (600, yb + 20), (600, yb + 60)], "GND"); s.gnd(600, yb + 60)
    s.text(900, yb - 8, "3 short beeps every 1.5 s during an evacuation", 11.5, MUTED)
    s.text(900, yb + 10, "passive buzzer → BUZZER_PASSIVE 1", 11.5, MUTED)

    # MAX7219 matrix
    pd, pc, pk = (P[k][1] for k in ("D9 GPIO20 [S3 11]", "D3 GPIO21 [S3 10]", "D8 GPIO19 [S3 12]"))
    mx, my, mw, mh = 700, pd - 50, 400, 135
    s.box(mx, my, mw, mh, "MAX7219 LED matrix 8×32", "FC-16 · 4 modules · exit sign / arrow + distance")
    for y, lab, src in ((pd, "DIN", "D9 GPIO20 [S3 11]"), (pc, "CS", "D3 GPIO21 [S3 10]"), (pk, "CLK", "D8 GPIO19 [S3 12]")):
        s.pin(mx, y, lab, "l"); s.wire([P[src], (mx, y)], "SIG")
    s.pin(mx + 300, my, "VCC", "t"); s.pin(mx + 350, my, "GND", "t")
    s.wire([(mx + 300, my), (mx + 300, my - 20)], "5V"); s.vcc(mx + 300, my - 20, "5V")
    s.wire([(mx + 350, my), (mx + 350, my - 10), (mx + mw + 30, my - 10), (mx + mw + 30, my + 10)], "GND"); s.gnd(mx + mw + 30, my + 10)
    s.text(mx + mw + 20, pk + 4, "use the IN side of the chain", 11, MUTED)
    s.text(mx + mw + 20, pk + 22, "flip: MATRIX_FLIP_X / _Y / REVERSE", 11, MUTED)

    # three MQ channels
    def gas(pin, title, sub, dashed):
        ya = P[pin][1]
        node_x, r1 = 580, 660
        s.wire([P[pin], (node_x, ya)], "ANA"); s.dot(node_x, ya, "ANA")
        s.resistor(node_x, ya, 80, True, "20 kΩ", "ANA"); s.gnd(node_x, ya + 80)
        end = s.resistor(r1, ya, 170, False, "10 kΩ", "ANA")
        s.wire([(node_x, ya), (r1, ya)], "ANA")
        bx = 1000
        s.wire([end, (bx, ya)], "ANA")
        s.box(bx, ya - 55, 300, 110, title, sub, dash=dashed)
        s.pin(bx, ya - 30, "VCC", "l"); s.pin(bx, ya, "AO", "l"); s.pin(bx, ya + 30, "DO", "l")
        s.text(bx - 12, ya + 34, "nc", 11, MUTED, "end")
        s.wire([(bx, ya - 30), (950, ya - 30), (950, ya - 50)], "5V"); s.vcc(950, ya - 50, "5V")
        s.pin(bx + 300, ya + 30, "GND", "r")
        s.wire([(bx + 300, ya + 30), (bx + 340, ya + 30), (bx + 340, ya + 40)], "GND"); s.gnd(bx + 340, ya + 40)
        s.text(node_x - 12, ya - 10, "0–3.3 V", 11, MUTED, "end", 700)
    gas("D2 GPIO2 [S3 4] ADC", "Gas 1 · MQ-2 / MQ-4", "methane / flammable · always fitted", False)
    gas("D0 GPIO0 [S3 6] ADC", "Gas 2 · MQ-7", "carbon monoxide · GAS_CHANNELS 2", True)
    gas("D1 GPIO1 [S3 7] ADC", "Gas 3 · MQ-136 / MQ-135", "H₂S / air quality · GAS_CHANNELS 3", True)

    # SOS
    ys = P["D6 GPIO16 [S3 13]"][1]
    s.wire([P["D6 GPIO16 [S3 13]"], (600, ys)], "SIG")
    e = s.button(600, ys, "SOS button (hold 1.5 s)")
    s.wire([e, (720, ys), (720, ys + 14)], "GND"); s.gnd(720, ys + 14)
    s.text(470, ys + 30, "INPUT_PULLUP · sends SOS to the hub", 11.5, MUTED)

    # AHT
    sda_y, scl_y = P["D4 GPIO22 [S3 8] SDA"][1], P["D5 GPIO23 [S3 9] SCL"][1]
    ax, ay, aw, ah = 860, sda_y - 50, 270, 130
    s.box(ax, ay, aw, ah, "AHT20 / AHT10 / AHT25", "air temp + humidity · 0x38")
    s.pin(ax, sda_y - 25, "VCC", "l"); s.pin(ax, sda_y, "SDA", "l"); s.pin(ax, scl_y, "SCL", "l"); s.pin(ax, scl_y + 25, "GND", "l")
    s.wire([P["D4 GPIO22 [S3 8] SDA"], (ax, sda_y)], "SDA", 3)
    s.wire([P["D5 GPIO23 [S3 9] SCL"], (ax, scl_y)], "SCL", 3)
    s.wire([(ax, sda_y - 25), (800, sda_y - 25), (800, sda_y - 45)], "3V3"); s.vcc(800, sda_y - 45)
    s.wire([(ax, scl_y + 25), (820, scl_y + 25), (820, scl_y + 45)], "GND"); s.gnd(820, scl_y + 45)
    s.text(ax + aw + 16, sda_y, "3.3 V only · own pull-ups", 11.5, MUTED)
    s.text(ax + aw + 16, sda_y + 18, "away from MQ heaters", 11.5, MUTED)
    s.antenna(215, 140, "u.FL ext. antenna (XIAO C6)")

    s.note(170, 1190, ["Divider on every MQ output: V_pin = 0.667 × V_AO (10 kΩ top, 20 kΩ to GND) — firmware × 1.5 to undo it.",
                      "MQ heaters need 5 V, ~150 mA each, 24–48 h burn-in, 60 s warm-up. Limits are set on the hub Limits tab.",
                      "Unused channels: set GAS_CHANNELS 1 or 2 and leave those pins empty. Serial 'd' = matrix test."], 1160)
    s.legend(170, 1320, [("3V3", "3.3 V"), ("5V", "5 V"), ("GND", "Ground"), ("ANA", "Analog (MQ AO)"), ("SIG", "Digital"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL")])
    s.save("repeater_node.svg")


# ============================================================ entry station
def entry():
    s = Sheet(1300, 840, "Entry / scanning station — wiring schematic",
              "ESP32-C6-WROOM-1 DevKit + HW-147C PN532 (I²C) + SSD1306 OLED + 3 buttons · NTAG215 tags on helmet, vest, pants, shoes · photo from phone")
    P = mcu(s, 150, 140, 260, 470, "ESP32-C6-WROOM-1", "DevKit · ESP32C6 Dev Module",
            left=[(110, "3V3"), (420, "GND")],
            right=[(130, "GPIO6  SDA"), (170, "GPIO7  SCL"), (310, "GPIO18"), (370, "GPIO19"), (430, "GPIO20")])
    x3, y3 = P["3V3"]; s.wire([(x3, y3), (x3 - 30, y3), (x3 - 30, y3 - 30)], "3V3"); s.vcc(x3 - 30, y3 - 30)
    xg, yg = P["GND"]; s.wire([(xg, yg), (xg - 30, yg), (xg - 30, yg + 20)], "GND"); s.gnd(xg - 30, yg + 20)
    sda_y, scl_y = P["GPIO6  SDA"][1], P["GPIO7  SCL"][1]
    s.wire([P["GPIO6  SDA"], (1060, sda_y)], "SDA", 3); s.wire([P["GPIO7  SCL"], (1060, scl_y)], "SCL", 3)
    s.text(460, scl_y + 22, "I²C bus", 12, MUTED, weight=600)
    for mx, t, sub in ((520, "PN532 · HW-147C", "DIP 1 ON, 2 OFF → I²C · 0x24"), (820, "SSD1306 OLED", "0.96\" 128×64 · 0x3C")):
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
    for lab, name in (("GPIO18", "READ button"), ("GPIO19", "WRITE button"), ("GPIO20", "PHOTO button (optional)")):
        x, y = P[lab]
        s.wire([(x, y), (560, y)], "SIG")
        e = s.button(560, y, name)
        s.wire([e, (680, y), (680, y + 14)], "GND"); s.gnd(680, y + 14)
    s.text(460, P["GPIO20"][1] + 40, "INPUT_PULLUP on all buttons", 11, MUTED)
    s.box(860, 420, 260, 80, "NTAG215 tags ×4", "helmet · vest · pants · shoes", fill="#fff", dash=True)
    s.text(990, 522, "tapped on the PN532 coil · 13.56 MHz · 3–5 cm", 11.5, MUTED, "middle", 600)
    s.box(860, 560, 260, 80, "Phone camera", "http://<laptop-ip>:5000/phone", fill="#fff", dash=True)
    s.text(990, 662, "entry photo over Wi-Fi (no wires)", 11.5, MUTED, "middle", 600)
    s.note(150, 680, ["PN532: use the 4-pin header (GND VCC SDA SCL), power from 3V3 · check first with firmware/tests/entry_hw_test",
                      "Libraries: Adafruit PN532, Adafruit SSD1306, Adafruit GFX (+ BusIO)",
                      "Wi-Fi + hub address in secrets.h (not in git) · scans → POST /api/gear · XIAO C6 option: SDA D4, SCL D5, D1/D0/D3"], 1000)
    s.legend(150, 815, [("3V3", "3.3 V"), ("GND", "Ground"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL"), ("SIG", "Button")])
    s.save("entry_station.svg")


# ================================================================== system
def system():
    s = Sheet(1500, 640, "MineSafe — system interconnection", "How every unit talks · solid = data up, dashed = alerts + evacuation guide down")
    def unit(x, y, w, h, t, sub, dark=False):
        if dark:
            s.box(x, y, w, h, "", "", fill="#12171A", stroke="#12171A")
            s.text(x + w / 2, y + h / 2 - 4, t, 15, "#F3F0E8", "middle", 700)
            s.text(x + w / 2, y + h / 2 + 16, sub, 11.5, AMBER, "middle", 600)
        else:
            s.box(x, y, w, h, t, sub)
    unit(60, 300, 200, 90, "Body units", "ESP32-C6 DevKit · sensors")
    unit(360, 300, 180, 90, "REP-03", "XIAO C6 · 2 hops")
    unit(640, 300, 180, 90, "REP-02", "XIAO C6 · 1 hop")
    unit(920, 300, 200, 90, "REP-01 (main)", "XIAO C6 · Wi-Fi to hub")
    unit(1220, 300, 230, 90, "Admin hub", "laptop · Flask · map · evac routes", dark=True)
    unit(1220, 120, 230, 80, "Scanning station", "ESP32-C6 · HW-147C RFID")
    unit(1220, 480, 230, 80, "Phone", "entry photo · test worker")
    for a, b in ((260, 360), (540, 640), (820, 920)):
        s.wire([(a, 330), (b, 330)], "SDA", 3); s.wire([(b, 360), (a, 360)], "ANA", 2.4, dash=True)
        s.text((a + b) / 2, 320, "ESP-NOW", 12, NET["SDA"], "middle", 700)
    s.wire([(1120, 330), (1220, 330)], "SCL", 3); s.wire([(1220, 360), (1120, 360)], "ANA", 2.4, dash=True)
    s.text(1170, 318, "Wi-Fi HTTP", 11.5, NET["SCL"], "middle", 700); s.text(1170, 380, "1 s", 11, MUTED, "middle")
    s.wire([(1335, 200), (1335, 300)], "SCL", 3); s.text(1345, 255, "Wi-Fi", 11.5, NET["SCL"], weight=700)
    s.wire([(1335, 480), (1335, 390)], "SCL", 3); s.text(1345, 440, "Wi-Fi", 11.5, NET["SCL"], weight=700)
    for x in (450, 730, 1020):
        s.box(x - 100, 470, 200, 56, "LED exit sign · buzzer", "3× MQ · AHT · SOS", fill="#fff")
        s.wire([(x, 390), (x, 470)], "RF", 2)
    s.note(60, 120, ["Up: worker telemetry hops repeater to repeater, then HTTP POST /api/telemetry.",
                     "Down: alerts + evacuation guide (arrow and distance per repeater) in the HTTP reply",
                     "→ repeater beacons → every exit sign, buzzer and body LED.",
                     "Routes self-heal: parent = neighbour with fewest hops, RSSI ≥ −92 dBm."], 760)
    s.legend(60, 600, [("SDA", "ESP-NOW data (2.4 GHz)"), ("SCL", "Wi-Fi / HTTP"), ("ANA", "Alert / guide path (dashed)")])
    s.save("system_overview.svg")


if __name__ == "__main__":
    body(); repeater(); entry(); system()
