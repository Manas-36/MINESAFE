"""Wiring (harness) diagram for the repeater prototype on the v4.0 PCB.

Shows every cable from the PCB connectors (J1-J9, u.FL) to the parts mounted in the case, pin by pin,
with the real pin order on the board (right-edge connectors count pin 1 from the BOTTOM).
Run:  python docs/wiring/make_repeater_v4_wiring.py   ->  docs/wiring/repeater_v4_wiring.svg
"""
from make_schematics import Sheet, INK, MUTED, AMBER

C = {  # conductor colours (what to actually use)
    "+": "#d93025", "-": "#202124", "AO": "#c98a00", "DIN": "#e8710a", "CS": "#188038", "CLK": "#1a73e8",
    "SDA": "#1a73e8", "SCL": "#188038", "3V3": "#d93025", "BUZ": "#9334e6", "SOS": "#9334e6", "RF": "#5f6368",
    "NC": "#bdbdbd", "BAT+": "#d93025", "BAT-": "#202124",
}
PCB_G = "#1d6b3a"


def main():
    s = Sheet(2000, 1720, "Repeater prototype — wiring diagram (PCB v4.0 in the mine case)",
              "Every cable from the board to the parts in the case, pin by pin · same for the main repeater (IS_GATEWAY 1) and tunnel repeaters (IS_GATEWAY 0)")

    def w(pts, col, width=3.2, dash=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        da = ' stroke-dasharray="6 5"' if dash else ""
        s.o.append(f'<polyline points="{d}" fill="none" stroke="{C[col]}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{da}/>')

    def dot(x, y, col):
        s.o.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{C[col]}"/>')

    def pinc(x, y, num, lab=None, side="r"):
        s.o.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#fff" stroke="{INK}" stroke-width="1.6"/>')
        s.text(x, y + 4, str(num), 9.5, INK, "middle", 700)
        if lab:
            dx, anc = {"r": (12, "start"), "l": (-12, "end"), "t": (0, "middle"), "b": (0, "middle")}[side]
            dy = {"t": -12, "b": 22}.get(side, 4)
            s.text(x + dx, y + dy, lab, 11, INK, anc, 600)

    def conn(x, y, w_, h_, name, sub=""):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="4" fill="#f3f0e8" stroke="{INK}" stroke-width="1.6"/>')
        return name

    def module(x, y, w_, h_, title, sub="", sub2=""):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="10" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        s.text(x + w_ / 2, y + 24, title, 14, INK, "middle", 700)
        if sub:
            s.text(x + w_ / 2, y + 42, sub, 11, MUTED, "middle")
        if sub2:
            s.text(x + w_ / 2, y + 58, sub2, 11, MUTED, "middle")

    def lenlab(x, y, txt, anchor="middle"):
        s.o.append(f'<rect x="{x - (len(txt) * 3.4 + 6) if anchor == "middle" else x - 3}" y="{y - 12}" width="{len(txt) * 6.8 + 12}" height="17" rx="8" fill="#fff8e1" stroke="{AMBER}"/>')
        s.text(x if anchor == "middle" else x + 3, y + 1, txt, 10.5, INK, anchor, 700)

    # ----------------------------------------------------------------- PCB
    X0, Y0, PW, PH = 720, 360, 560, 440
    s.o.append(f'<rect x="{X0}" y="{Y0}" width="{PW}" height="{PH}" rx="14" fill="{PCB_G}" stroke="#0e3d20" stroke-width="3"/>')
    for hx, hy in ((X0 + 20, Y0 + 20), (X0 + PW - 20, Y0 + 20), (X0 + 20, Y0 + PH - 20), (X0 + PW - 20, Y0 + PH - 20)):
        s.o.append(f'<circle cx="{hx}" cy="{hy}" r="9" fill="#d8c27a" stroke="#0e3d20" stroke-width="2"/><circle cx="{hx}" cy="{hy}" r="4" fill="#0e3d20"/>')
    s.text(X0 + PW / 2, Y0 + PH - 120, "MineSafe REPEATER PCB v4.0", 18, "#ffffff", "middle", 700)
    s.text(X0 + PW / 2, Y0 + PH - 100, "100 × 75 mm · 4 × M3 on the case standoffs · conformal-coat after test", 11.5, "#cfe8d6", "middle")
    # XIAO
    xx, xy = X0 + 250, Y0 + 14
    s.o.append(f'<rect x="{xx}" y="{xy}" width="110" height="130" rx="8" fill="#12171A" stroke="{AMBER}" stroke-width="2"/>')
    s.text(xx + 55, xy + 58, "XIAO", 14, "#F3F0E8", "middle", 700)
    s.text(xx + 55, xy + 76, "ESP32-C6", 12, AMBER, "middle", 700)
    s.text(xx + 55, xy + 94, "on sockets", 10.5, "#c9c4b8", "middle")
    s.o.append(f'<rect x="{xx + 35}" y="{xy - 10}" width="40" height="16" rx="5" fill="#9aa0a6" stroke="#202124"/>')
    s.text(xx + 55, xy - 16, "USB-C", 10.5, "#fff", "middle", 700)
    s.o.append(f'<circle cx="{xx + 95}" cy="{xy + 18}" r="6" fill="#d8c27a" stroke="#202124"/>')
    # inner labels
    s.text(X0 + PW / 2, Y0 + 210, "U1 5 V / 2 A · fuse · TVS · diode OR", 11, "#cfe8d6", "middle")
    s.text(X0 + PW / 2, Y0 + 228, "U3 74HCT125 (matrix 5 V logic)", 11, "#cfe8d6", "middle")
    s.text(X0 + PW / 2, Y0 + 246, "PWR LED shows +5 V", 11, "#cfe8d6", "middle")

    # ----------------------------------------------------------------- left: power (J1, J2)
    # J1: pin 2 (GND) above pin 1 (+) as on the board
    jx = X0 + 6
    J1 = {2: (jx + 20, Y0 + 70), 1: (jx + 20, Y0 + 100)}
    J2 = {2: (jx + 20, Y0 + 150), 1: (jx + 20, Y0 + 180)}
    for J, name, sub in ((J1, "J1  MAIN 9–30 V", "screw terminal"), (J2, "J2  BATT 12 V", "screw terminal")):
        y_top = min(p[1] for p in J.values()) - 14
        s.o.append(f'<rect x="{jx}" y="{y_top}" width="40" height="58" rx="4" fill="#3d8ed8" stroke="{INK}" stroke-width="1.6"/>')
        s.text(jx + 50, y_top + 12, name, 11.5, "#ffffff", "start", 700)
        for n, (px, py) in J.items():
            pinc(px, py, n)
        s.text(jx + 50, J[2][1] + 18, "pin 2 = −   pin 1 = +", 10.5, "#cfe8d6")

    # adapter -> gland -> Wago splitter
    module(40, 150, 270, 78, "DC adapter 15–24 V, 2 A", "stands in for the mine supply", "(24 V laptop-style is ideal)")
    s.text(205, 262, "2-core 0.75 mm² cable", 11, MUTED, "start")
    gx, gy = 175, 300
    s.o.append(f'<rect x="{gx - 40}" y="{gy - 16}" width="80" height="32" rx="6" fill="#9aa0a6" stroke="{INK}" stroke-width="1.6"/>')
    s.text(gx, gy + 5, "M16 gland", 11.5, "#fff", "middle", 700)
    s.text(gx + 52, gy + 5, "bottom wall · drip loop", 11, MUTED)
    w([(160, 228), (160, gy - 16)], "+", 4); w([(190, 228), (190, gy - 16)], "-", 4)
    wx, wy = 420, 400
    module(wx - 60, wy - 50, 150, 100, "Wago 221-413", "lever splitter ×2", "(+ and −)")
    w([(160, gy + 16), (160, wy - 12), (wx - 60, wy - 12)], "+", 4)
    w([(190, gy + 16), (190, wy + 14), (wx - 60, wy + 14)], "-", 4)
    # wago -> J1
    w([(wx + 90, wy - 12), (600, wy - 12), (600, J1[1][1]), J1[1]], "+", 4)
    w([(wx + 90, wy + 14), (630, wy + 14), (630, J1[2][1]), J1[2]], "-", 4)
    lenlab(560, J1[2][1] - 14, "0.75 mm² · 150 mm")

    # charger + BMS + pack
    cx, cy = 40, 600
    module(cx, cy, 300, 120, "Charge module (buck-boost CC/CV)", "set 12.6 V and 1 A before connecting", "IN from the splitter · OUT to the pack")
    s.text(cx + 292, cy + 34, "IN+", 11, INK, "end", 700); s.text(cx + 292, cy + 60, "IN−", 11, INK, "end", 700)
    s.text(cx + 292, cy + 90, "OUT+", 11, INK, "end", 700); s.text(cx + 292, cy + 112, "OUT−", 11, INK, "end", 700)
    w([(wx - 20, wy + 50), (wx - 20, 560), (cx + 380, 560), (cx + 380, cy + 30), (cx + 300, cy + 30)], "+", 3)
    w([(wx + 20, wy + 50), (wx + 20, 580), (cx + 400, 580), (cx + 400, cy + 56), (cx + 300, cy + 56)], "-", 3)
    bx, by = 40, 800
    module(bx, by, 300, 150, "3S Li-ion pack + BMS", "3 × 18650 in series · 11.1 V nom, 12.6 V full", "common-port BMS: P+ / P− (charge and load)")
    s.o.append(f'<rect x="{bx + 30}" y="{by + 78}" width="240" height="52" rx="6" fill="#2a4fb0"/>')
    for i in range(3):
        s.o.append(f'<rect x="{bx + 40 + i * 78}" y="{by + 86}" width="70" height="36" rx="16" fill="#5b7fd6" stroke="#fff"/>')
    s.text(bx + 150, by + 145, "B− · B1 · B2 · B+ balance leads to the BMS", 10.5, MUTED, "middle")
    # charger OUT -> P+ / P-, P+/P- -> J2
    pp, pm = (bx + 300, by + 30), (bx + 300, by + 56)
    s.text(pp[0] - 8, pp[1] + 4, "P+", 11, INK, "end", 700); s.text(pm[0] - 8, pm[1] + 4, "P−", 11, INK, "end", 700)
    w([(cx + 300, cy + 86), (cx + 440, cy + 86), (cx + 440, pp[1]), pp], "BAT+", 3.4)
    w([(cx + 300, cy + 108), (cx + 470, cy + 108), (cx + 470, pm[1]), pm], "BAT-", 3.4)
    dot(cx + 440, pp[1], "BAT+"); dot(cx + 470, pm[1], "BAT-")
    w([(cx + 440, pp[1]), (650, pp[1]), (650, J2[1][1]), J2[1]], "BAT+", 4)
    w([(cx + 470, pm[1]), (680, pm[1]), (680, J2[2][1]), J2[2]], "BAT-", 4)
    lenlab(560, by + 6, "0.75 mm² · 150 mm · battery bay")
    s.text(bx + 150, by + 175, "inline 3 A blade fuse in P+ recommended", 11, "#d93025", "middle", 700)

    # ----------------------------------------------------------------- top: antenna + USB
    ax_, ay_ = xx + 95, xy + 18
    w([(ax_, ay_), (ax_, 250), (ax_ + 160, 250)], "RF", 3)
    s.o.append(f'<rect x="{ax_ + 160}" y="238" width="70" height="24" rx="5" fill="#d8c27a" stroke="{INK}"/>')
    s.text(ax_ + 195, 255, "SMA", 11, INK, "middle", 700)
    s.antenna(ax_ + 260, 250, "2.4 GHz 3–5 dBi antenna, outside the top wall")
    w([(ax_ + 230, 250), (ax_ + 260, 250)], "RF", 3)
    s.text(ax_ + 10, 232, "u.FL → SMA bulkhead pigtail, 150 mm", 11, INK, "start", 700)
    s.text(ax_ + 10, 214, "firmware: USE_EXTERNAL_ANTENNA 1", 11, MUTED)
    s.text(xx + 25, Y0 - 44, "USB-C: programming / serial log only", 11, MUTED, "end")
    s.text(xx + 25, Y0 - 28, "leave a service loop to the top", 11, MUTED, "end")

    # ----------------------------------------------------------------- bottom: MQ1-3 (J3-J5)
    mq = [("J3  MQ1", "MQ-4 · methane (CH₄)", "TOP wall port (chimney)", "lead 300 mm", "GAS1 → D2"),
          ("J4  MQ2", "MQ-7 · carbon monoxide", "BOTTOM wall port", "lead 200 mm", "GAS2 → D0"),
          ("J5  MQ3", "MQ-136 · H₂S", "BOTTOM wall port", "lead 200 mm", "GAS3 → D1")]
    for i, (jn, t1, t2, ln, gp) in enumerate(mq):
        cxm = X0 + 110 + i * 170
        jy = Y0 + PH - 6
        s.o.append(f'<rect x="{cxm - 62}" y="{jy - 22}" width="124" height="30" rx="4" fill="#f3f0e8" stroke="{INK}" stroke-width="1.6"/>')
        s.text(cxm, jy - 30, jn, 11.5, "#ffffff", "middle", 700)
        pins = [(cxm - 45 + k * 30, jy - 7) for k in range(4)]
        for k, p in enumerate(pins):
            pinc(*p, k + 1)
        my = 1010
        module(cxm - 78, my, 156, 120, t1.split(" · ")[0] + " module", t1.split(" · ")[1], t2)
        labs = ["VCC", "GND", "DO", "AO"]
        cols = ["+", "-", "NC", "AO"]
        for k in range(4):
            px, py = pins[k]
            w([(px, py + 8), (px, my)], cols[k], 3.2, dash=(k == 2))
            s.text(px, my + 112 - 0, "", 1)
            s.text(px, my - 8, labs[k], 9.5, INK, "middle", 700)
        s.text(cxm, my + 104, gp, 10.5, "#c98a00", "middle", 700)
        lenlab(cxm, 920 + (i % 2) * 22, ln)
    s.text(X0 + 280, 1160, "DO (pin 3) is not used — leave it unconnected. MQ module headers are usually VCC GND DO AO;", 11, MUTED, "middle")
    s.text(X0 + 280, 1176, "if yours differs, match by the printed names, not by position.", 11, MUTED, "middle")

    # ----------------------------------------------------------------- right: J7, J8, J9, J6
    rx = X0 + PW - 46
    RX_MOD = 1560

    def right_conn(name, y_top, n, labs, cols, mod_title, mod_sub, mod_sub2, mod_labs, ln, mod_h=None):
        pitch = 26
        h_ = n * pitch + 6
        s.o.append(f'<rect x="{rx}" y="{y_top}" width="40" height="{h_}" rx="4" fill="#f3f0e8" stroke="{INK}" stroke-width="1.6"/>')
        s.text(rx - 8, y_top + 14, name, 11.5, "#ffffff", "end", 700)
        ys = []
        for k in range(n):           # pin n on top ... pin 1 at the bottom (as on the board)
            num = n - k
            py = y_top + 16 + k * pitch
            pinc(rx + 20, py, num)
            ys.append((num, py))
        mh = mod_h or max(h_ + 20, 76)
        mtop = y_top - 10
        module(RX_MOD, mtop, 330, mh, mod_title, "", "")
        s.text(RX_MOD + 200, mtop + 44, mod_sub, 11, MUTED, "middle")
        if mod_sub2:
            s.text(RX_MOD + 200, mtop + 60, mod_sub2, 11, MUTED, "middle")
        for (num, py), lab, col, ml in zip(ys, labs, cols, mod_labs):
            w([(rx + 27, py), (RX_MOD, py)], col, 3.2)
            s.text(rx + 50, py - 5, lab, 10.5, C[col] if col not in ("-",) else INK, "start", 700)
            s.text(RX_MOD + 8, py + 4, ml, 10.5, INK, "start", 700)
        lenlab((rx + RX_MOD) / 2 + 40, y_top - 4, ln)

    right_conn("J7  MATRIX", Y0 + 20, 5, ["CLK5", "CS5", "DIN5", "GND", "+5V"], ["CLK", "CS", "DIN", "-", "+"],
               "MAX7219 8×32 matrix (FC-16)", "IN side of the chain", "on the lid, behind the window",
               ["CLK", "CS", "DIN", "GND", "VCC"], "XH-5 · 350 mm (lid opens)", 150)
    right_conn("J8  BUZZER", Y0 + 190, 2, ["BUZ_N", "+5V"], ["BUZ", "+"], "Buzzer 5 V active, ≥ 85 dB", "on the lid, behind the grille", "",
               ["−", "+"], "XH-2 · 350 mm", 80)
    right_conn("J9  SOS", Y0 + 280, 2, ["GND", "SOS"], ["-", "SOS"], "22 mm IP67 SOS button (NO)", "on the lid · hold 1.5 s", "",
               ["NO 2", "NO 1"], "XH-2 · 350 mm", 80)
    right_conn("J6  AHT20", Y0 + 330 + 30, 4, ["SCL", "SDA", "GND", "+3V3"], ["SCL", "SDA", "-", "3V3"],
               "AHT20 temp + humidity", "in the sealed bottom-left chamber", "3.3 V ONLY — never 5 V",
               ["SCL", "SDA", "GND", "VIN"], "XH-4 · 250 mm", 130)

    # ----------------------------------------------------------------- wire table
    ty = 1230
    s.text(40, ty, "Cable list (make one set per repeater)", 16, INK, weight=700)
    rows = [("Cable", "From → to", "Wires", "Length", "Connector at the module"),
            ("Mine supply", "Adapter → M16 gland → Wago → J1 1(+) 2(−) and charge-module IN", "2 × 0.75 mm² red / black", "150 mm inside", "screw terminal, ferrules"),
            ("Battery", "BMS P+ / P− → charge-module OUT and J2 1(+) 2(−)", "2 × 0.75 mm² red / black", "150 mm", "solder + heat-shrink, 3 A fuse in P+"),
            ("MQ1 / MQ2 / MQ3", "J3 / J4 / J5 → MQ-4 (top) / MQ-7 / MQ-136 (bottom)", "3 used: red VCC, black GND, yellow AO", "300 / 200 / 200 mm", "Dupont 4-pin housing on the module header"),
            ("Matrix", "J7 → FC-16 IN header", "5: red, black, orange DIN, green CS, blue CLK", "350 mm", "Dupont 5-pin"),
            ("Buzzer", "J8 1(+5V) → buzzer +, 2(BUZ_N) → buzzer −", "2: red, purple", "350 mm", "solder + heat-shrink"),
            ("SOS", "J9 1(SOS), 2(GND) → button NO contacts", "2: purple, black", "350 mm", "6.3 mm spade or screw"),
            ("AHT20", "J6 1(+3V3) 2(GND) 3(SDA) 4(SCL) → VIN GND SDA SCL", "4: red, black, blue SDA, green SCL", "250 mm", "Dupont 4-pin, pass through the chamber notch"),
            ("Antenna", "XIAO u.FL → SMA bulkhead (top wall) → antenna", "RG178 pigtail", "150 mm", "u.FL push-on, do not bend at the plug")]
    colx = [40, 230, 830, 1240, 1420]
    for r_, row in enumerate(rows):
        yy = ty + 28 + r_ * 26
        if r_ == 0:
            s.o.append(f'<rect x="30" y="{yy - 18}" width="1940" height="26" fill="#12171A"/>')
        elif r_ % 2 == 0:
            s.o.append(f'<rect x="30" y="{yy - 18}" width="1940" height="26" fill="#f6f4ef"/>')
        for cx_, t in zip(colx, row):
            s.text(cx_, yy, t, 11.5, "#F3F0E8" if r_ == 0 else INK, weight=700 if r_ == 0 or cx_ == 40 else 400)

    s.note(40, 1500, ["Before the first power-up",
                      "1. Set the charge module to 12.6 V / 1 A with nothing connected, then wire it to the pack.",
                      "2. XIAO out of its sockets: power J1, check 5.0 V between the 5V and GND socket pins.",
                      "3. Fit the XIAO, flash with USB (unplug the matrix + MQ leads while flashing from a laptop port).",
                      "4. Plug the leads one at a time; MQ heaters need 24–48 h burn-in before calibration."], 900)
    s.note(980, 1500, ["Why a 15–24 V adapter",
                       "Supply and battery feed the board through two diodes; the higher one wins.",
                       "With a 12 V adapter the full pack (12.6 V) wins, so the board runs from the pack",
                       "while the charger tops it up — works, but set the charger to at least 1 A.",
                       "D7 (MAINS_N) is LOW whenever the mine supply is present."], 980)
    lx = 40
    s.text(lx, 1694, "WIRE COLOURS:", 11, MUTED, weight=700); lx += 110
    for col, lab in (("+", "+ supply (red)"), ("-", "GND (black)"), ("AO", "gas AO (yellow)"), ("DIN", "DIN (orange)"), ("CS", "CS / SCL (green)"),
                     ("CLK", "CLK / SDA (blue)"), ("BUZ", "buzzer / SOS (purple)"), ("RF", "antenna coax")):
        w([(lx, 1690), (lx + 28, 1690)], col, 4); s.text(lx + 36, 1694, lab, 12, INK); lx += 60 + 7.0 * len(lab)
    s.save("repeater_v4_wiring.svg")


if __name__ == "__main__":
    main()
