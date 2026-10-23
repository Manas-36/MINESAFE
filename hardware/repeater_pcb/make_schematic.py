"""Draws the repeater PCB schematic (renders/repeater_schematic.svg) from the same parts as build_board.py.
Net labels (coloured tags) join the blocks: two tags with the same name are the same net."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "docs", "wiring"))
from make_schematics import Sheet, NET, INK, MUTED, AMBER  # noqa: E402

COL = {"VIN_MAIN": "#e8710a", "VIN_BAT": "#e8710a", "VRAIL": "#e8710a", "VPROT": "#e8710a", "+5V": "#e8710a",
       "+3V3": "#d93025", "GND": "#202124", "SDA": "#1a73e8", "SCL": "#188038"}


def main():
    s = Sheet(2000, 1000, "MineSafe repeater PCB v4.0 — schematic",
              "Carrier board for the Seeed XIAO ESP32-C6 · 100 × 75 mm, 2 layers · pins as in firmware/repeater_node (v3.3) + mains-present on D7")

    def tag(x, y, name, side="r"):
        c = COL.get(name, "#9334e6")
        w = 8 + 7.2 * len(name)
        x0 = x if side == "r" else x - w
        s.o.append(f'<rect x="{x0}" y="{y-9}" width="{w}" height="18" rx="4" fill="{c}"/>')
        s.text(x0 + w / 2, y + 4, name, 11, "#fff", "middle", 700)

    def wire(pts, name="SIG"):
        c = COL.get(name, "#9334e6")
        d = " ".join(f"{x},{y}" for x, y in pts)
        s.o.append(f'<polyline points="{d}" fill="none" stroke="{c}" stroke-width="2"/>')

    def part(x, y, w, h, ref, val, pins_l=(), pins_r=(), pins_t=(), pins_b=()):
        """box with pins; pins_* = list of (label, net). returns dict net-> (x,y) end points"""
        s.box(x, y, w, h, ref, val)
        pts = {}
        for i, (lab, net) in enumerate(pins_l):
            py = y + 26 + i * 24
            s.text(x + 6, py + 4, lab, 11, INK, weight=600)
            wire([(x, py), (x - 40, py)], net); tag(x - 40, py, net, "l") if net else None
        for i, (lab, net) in enumerate(pins_r):
            py = y + 26 + i * 24
            s.text(x + w - 6, py + 4, lab, 11, INK, "end", 600)
            wire([(x + w, py), (x + w + 40, py)], net); tag(x + w + 40, py, net) if net else None
        return pts

    def block(x, y, w, h, title):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="none" stroke="{AMBER}" stroke-width="2" stroke-dasharray="8 6"/>')
        s.text(x + 12, y + 22, title, 14, INK, weight=700)

    # ---------------- power
    block(30, 100, 640, 470, "Power: mine supply or battery → 5 V (2 A)")
    s.text(50, 140, "J1 MAIN 9–30 V", 12, INK, weight=700); tag(160, 162, "VIN_MAIN"); s.text(50, 166, "pin 1 (+)", 11, MUTED)
    s.text(50, 196, "pin 2 (−)", 11, MUTED); tag(160, 192, "GND")
    s.text(50, 236, "J2 BATT 12 V", 12, INK, weight=700); tag(160, 258, "VIN_BAT"); s.text(50, 262, "pin 1 (+)", 11, MUTED)
    s.text(50, 292, "pin 2 (−)", 11, MUTED); tag(160, 288, "GND")
    # diodes OR
    for i, (net, ref) in enumerate((("VIN_MAIN", "D1"), ("VIN_BAT", "D2"))):
        y = 172 + i * 62
        tag(300, y, net, "l"); wire([(300, y), (330, y)], "VIN_MAIN")
        s.o.append(f'<polygon points="330,{y-12} 330,{y+12} 352,{y}" fill="#fff" stroke="{INK}" stroke-width="2"/><line x1="352" y1="{y-12}" x2="352" y2="{y+12}" stroke="{INK}" stroke-width="2.4"/>')
        s.text(341, y - 18, f"{ref} 1N5822", 11, INK, "middle", 700)
        wire([(352, y), (400, y), (400, 203)], "VRAIL")
    wire([(400, 203), (430, 203)], "VRAIL"); tag(430, 203, "VRAIL")
    s.text(340, 290, "Schottky OR: whichever input is higher feeds the board;", 11, MUTED)
    s.text(340, 305, "mine power cut → battery takes over with no reset", 11, MUTED)
    # fuse, TVS, cap, regulator
    tag(90, 360, "VRAIL", "l"); wire([(90, 360), (120, 360)], "VRAIL")
    s.box(120, 345, 70, 30, "F1", ""); s.text(155, 395, "T1.6 A TR5", 11, MUTED, "middle")
    wire([(190, 360), (260, 360)], "VPROT")
    tag(260, 360, "VPROT")
    s.text(50, 420, "D3 P6KE36A TVS + C1 470 µF 50 V", 11, INK, weight=600)
    s.text(50, 436, "on VPROT → GND: clamp surges and spikes", 11, MUTED)
    s.box(420, 330, 200, 90, "U1 K7805-2000R3", "switching 5 V / 2 A, 8–32 V in")
    s.text(428, 440, "1 VIN ← VPROT · 2 GND · 3 VOUT → +5V", 11, INK, weight=600)
    s.text(428, 456, "C2 220 µF + C3 100 nF on +5V", 11, MUTED)
    tag(510, 481, "+5V"); s.text(428, 485, "+5V feeds:", 11, MUTED)
    s.text(428, 500, "XIAO, 3 MQ heaters, matrix, buzzer, U3", 11, MUTED)
    s.text(50, 470, "LED1 power: +5V → R1 1 k → LED → GND", 11, INK, weight=600)
    # mains detect
    s.text(50, 510, "Mains-present (Q2 S8050): VIN_MAIN → R2 22 k → base,", 11, INK, weight=600)
    s.text(50, 526, "R3 10 k base→GND, collector → MAINS_N, R4 10 k to +3V3.", 11, INK, weight=600)
    s.text(50, 542, "Mine supply on → MAINS_N low (D7).", 11, MUTED); tag(560, 540, "MAINS_N")

    # ---------------- XIAO
    block(720, 100, 520, 470, "Controller: Seeed XIAO ESP32-C6 (on sockets U2A / U2B)")
    left = [("D0 GPIO0", "GAS2"), ("D1 GPIO1", "GAS3"), ("D2 GPIO2", "GAS1"), ("D3 GPIO21", "MX_CS"), ("D4 GPIO22", "SDA"), ("D5 GPIO23", "SCL"), ("D6 GPIO16", "SOS")]
    right = [("5V", "+5V"), ("GND", "GND"), ("3V3", "+3V3"), ("D10 GPIO18", "BUZ"), ("D9 GPIO20", "MX_DIN"), ("D8 GPIO19", "MX_CLK"), ("D7 GPIO17", "MAINS_N")]
    part(880, 150, 200, 200, "", "", left, right)
    s.text(980, 380, "u.FL → pigtail → SMA bulkhead antenna on the case", 11, MUTED, "middle")
    s.text(980, 396, "USB-C (top edge) for programming", 11, MUTED, "middle")
    s.text(980, 430, "ADC only on GPIO0–6 → the three gas inputs use D0, D1, D2", 11, MUTED, "middle")

    # ---------------- level shifter
    block(1290, 100, 680, 330, "Matrix interface: 3.3 V → 5 V (74HCT125, U3) + J7")
    s.text(1565, 142, "U3 74HCT125", 13, INK, "middle", 700)
    part(1480, 150, 170, 200, "", "", [("2 1A", "MX_DIN"), ("5 2A", "MX_CS"), ("9 3A", "MX_CLK"), ("1,4,10 OE", "GND"), ("7 GND", "GND")],
         [("3 1Y", "DIN5"), ("6 2Y", "CS5"), ("8 3Y", "CLK5"), ("14 VCC", "+5V"), ("12 4A / 13 4OE", "")])
    s.text(1310, 380, "MAX7219 needs ≥ 3.5 V logic-high at 5 V — the HCT buffer gives clean 5 V edges.", 11, MUTED)
    s.text(1310, 396, "J7 MATRIX (XH-5): 1 +5V · 2 GND · 3 DIN5 · 4 CS5 · 5 CLK5   ·   C4 100 nF at U3", 11, INK, weight=600)

    # ---------------- gas inputs
    block(30, 610, 1210, 330, "Gas inputs ×3: MQ sensor AO (0–5 V) → divider → ADC (0–3.3 V)")
    for i, (n, gp) in enumerate(((1, "D2"), (2, "D0"), (3, "D1"))):
        x = 70 + i * 390
        s.text(x, 650, f"J{2 + n} MQ{n} (XH-4): 1 +5V · 2 GND · 3 DO (n.c.) · 4 AO{n}", 11, INK, weight=600)
        tag(x + 30, 700, f"AO{n}", "l"); wire([(x + 30, 700), (x + 60, 700)])
        s.resistor(x + 60, 700, 100, False, f"R1{n} 10 k", "ANA")
        wire([(x + 160, 700), (x + 220, 700)], f"GAS{n}"); s.dot(x + 190, 700, "ANA")
        s.resistor(x + 190, 700, 90, True, f"R2{n} 20 k", "ANA"); s.gnd(x + 190, 790)
        tag(x + 220, 700, f"GAS{n}")
        s.text(x + 250, 760, f"C1{n} 100 nF GAS{n}→GND", 11, MUTED)
        s.text(x, 830, f"→ XIAO {gp} · V_pin = 0.667 × V_AO", 11, MUTED)
    s.text(70, 900, "Firmware multiplies by 1.5 to recover the sensor voltage. MQ heaters ≈ 150 mA each from +5V.", 11, INK, weight=600)

    # ---------------- outputs
    block(1290, 460, 680, 480, "Outputs and sensors on the right edge")
    s.text(1310, 500, "Buzzer J8 (XH-2): 1 +5V · 2 BUZ_N", 12, INK, weight=700)
    s.text(1310, 520, "Q1 S8050: base ← R5 1 k ← BUZ (D10), collector BUZ_N, emitter GND; D4 1N4148 across the buzzer", 11, MUTED)
    s.text(1310, 560, "SOS J9 (XH-2): 1 SOS (D6, internal pull-up) · 2 GND · C5 100 nF debounce", 12, INK, weight=700)
    s.text(1310, 600, "AHT20 J6 (XH-4): 1 +3V3 · 2 GND · 3 SDA · 4 SCL · R6 / R7 4.7 k pull-ups to +3V3", 12, INK, weight=700)
    s.text(1310, 620, "flying lead so the sensor sits in the cool, vented chamber away from the MQ heaters", 11, MUTED)
    s.text(1310, 660, "Mounting: 4 × M3 at the corners (3.5 mm in), board 100 × 75 mm", 12, INK, weight=700)
    s.text(1310, 700, "Nets: VIN_MAIN VIN_BAT VRAIL VPROT +5V +3V3 GND (0.8 mm tracks for power,", 11, MUTED)
    s.text(1310, 716, "0.3 mm signals, 0.25 mm clearance), GND pour on both layers", 11, MUTED)
    s.legend(30, 975, [("5V", "power"), ("3V3", "3.3 V"), ("GND", "ground"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL"), ("ANA", "analog"), ("SIG", "digital")])
    out = os.path.join(HERE, "renders")
    os.makedirs(out, exist_ok=True)
    # Sheet.save writes next to make_schematics.py; write ours here instead
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w}" height="{s.h}" viewBox="0 0 {s.w} {s.h}">'
           f'<defs><pattern id="hz" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           f'<rect width="14" height="28" fill="{AMBER}"/><rect x="14" width="14" height="28" fill="#12171A"/></pattern></defs>'
           + "".join(s.o) + "</svg>")
    open(os.path.join(out, "repeater_schematic.svg"), "w", encoding="utf-8").write(svg)
    print("wrote renders/repeater_schematic.svg")


if __name__ == "__main__":
    main()
