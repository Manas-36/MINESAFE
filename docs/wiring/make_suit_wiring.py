"""Wiring diagram for the V4 smart suit pod boards (core, cuff, helmet, boot), pin by pin.
Run: python docs/wiring/make_suit_wiring.py  ->  docs/wiring/suit_v4_wiring.svg
Pins follow hardware/suit_pcb/boards.py.
"""
from make_schematics import Sheet, INK, MUTED, AMBER

COL = {"+3V3": "#d93025", "+5V": "#e8710a", "BAT+": "#d93025", "BAT_N": "#202124", "GND": "#202124", "SDA": "#1a73e8", "SCL": "#188038",
       "POGO+": "#e8710a", "CHG_OUT": "#d93025", "VSYS": "#d93025", "NC": "#bdbdbd"}
SIG = "#9334e6"


def main():
    s = Sheet(2000, 2180, "V4 smart suit — pod wiring (PCB v4.0)",
              "Each pod board: every connector, pin by pin, to the part it plugs into · all JST-PH 2.0 mm unless noted · XIAO ESP32-C6 in every pod except the cuff")

    def w(pts, col, width=3.0, dash=False):
        d = " ".join(f"{x},{y}" for x, y in pts)
        da = ' stroke-dasharray="6 5"' if dash else ""
        s.o.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="{width}" stroke-linecap="round"{da}/>')

    def pin(x, y, n):
        s.o.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
        s.text(x, y + 4, str(n), 9.5, INK, "middle", 700)

    def board(x, y, w_, h_, title, sub, xiao=None):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w_}" height="{h_}" rx="12" fill="#1d6b3a" stroke="#0e3d20" stroke-width="3"/>')
        s.text(x + 16, y + 30, title, 17, "#fff", "start", 700)
        s.text(x + 16, y + 50, sub, 11.5, "#cfe8d6")
        if xiao:
            yy = y + 72
            for line in xiao:
                s.text(x + 16, yy, line, 11, "#cfe8d6"); yy += 16

    def conn(bx, by, name, pins, dev, dev_sub, dx=430, dw=300, note=""):
        """connector on the board's right edge at (bx, by); pins = [(num, net, device_pin)]"""
        n = len(pins)
        h = 24 * n + 10
        s.o.append(f'<rect x="{bx - 34}" y="{by}" width="34" height="{h}" rx="4" fill="#f3f0e8" stroke="{INK}" stroke-width="1.5"/>')
        s.text(bx - 42, by + 16, name, 11.5, "#fff", "end", 700)   # on the green board
        tx = bx + dx
        dh = max(h, 58)
        s.o.append(f'<rect x="{tx}" y="{by - 4}" width="{dw}" height="{dh + 8}" rx="9" fill="#fff" stroke="{INK}" stroke-width="1.8"/>')
        s.text(tx + 120, by + 17, dev, 13, INK, "start", 700)
        s.text(tx + 120, by + 34, dev_sub, 10.5, MUTED, "start")
        if note:
            s.text(tx + 120, by + 50, note, 10.5, "#d93025", "start", 700)
        for i, (num, net, dp) in enumerate(pins):
            py = by + 17 + i * 24
            pin(bx - 17, py, num)
            col = COL.get(net, SIG)
            w([(bx - 10, py), (tx, py)], col, 3.0, dash=(net == "NC"))
            s.text(bx + 10, py - 5, net, 10.5, col if net not in ("GND", "BAT_N") else INK, "start", 700)
            s.text(tx + 8, py + 4, dp, 10.5, INK, "start", 700)
        return by + max(h, dh) + 22

    def section(x, y, title, btitle, bsub, info, bw, conns, dx, dw, after=None):
        """draw a pod: heading, board sized to its connectors, connectors + devices; returns bottom y"""
        s.text(x, y, title, 18, AMBER, weight=700)
        by = y + 20
        hc = 70
        for c in conns:
            if c == "SNAPS":
                hc += 30
                continue
            n = len(c[1])
            hc += max(24 * n + 10, 58) + 22
        bh = max(hc, 70 + 16 * len(info) + 20)
        board(x, by, bw, bh, btitle, bsub, info)
        ex, yy = x + bw, by + 70
        for c in conns:
            if c == "SNAPS":
                s.text(ex + 20, yy + 4, "Suit wiring through the 6 snaps on the back:", 12, INK, weight=700)
                yy += 30
                continue
            name, pins, dev, sub = c[:4]
            yy = conn(ex, yy, name, pins, dev, sub, dx=dx, dw=dw, note=c[4] if len(c) > 4 else "")
        end = by + bh
        if after:
            s.text(x, end + 22, after, 11, MUTED)
            end += 30
        return end

    yc = section(40, 120, "CORE POD (chest)", "Core board 66 × 54 mm", "XIAO C6 + GY-521 + GY-68 on sockets",
            ["D0 BTN (cuff ladder, ADC)", "D1 SKIN (RC sense)", "D2 TEAR loop", "D3 1-Wire (DS18B20)", "D4 SDA · D5 SCL", "D6 SOS · D7 ZIP",
             "D8 LED · D9 HAPTIC", "D10 IMU_INT", "", "I²C bus: MPU6050 0x68,", "BMP180 0x77, MAX17048 0x36,", "cuff OLED 0x3C, MAX30102 0x57",
             "", "Power: LiPo → TP4056 →", "switch → TPS63020 → 3.3 V", "(XIAO fed on its 3V3 pin;", "flash with the switch OFF)"], 330,
            [("J1 BATT", [(1, "BAT+", "red +"), (2, "BAT_N", "black −")], "LiPo 3.7 V 3000 mAh", "805070 with protection", "never short — pouch cell"),
             ("J10 CHARGER", [(1, "POGO+", "IN+"), (2, "GND", "IN−"), (3, "BAT+", "B+"), (4, "BAT_N", "B−"), (5, "CHG_OUT", "OUT+"), (6, "GND", "OUT−")],
              "TP4056 USB-C module", "protected version · wire pads, 26 AWG"),
             ("J2 PWR SW", [(1, "CHG_OUT", "common"), (2, "VSYS", "ON")], "Power toggle", "top wall, behind the guard"),
             ("J11 BUCK", [(1, "VSYS", "VIN (+EN)"), (2, "GND", "GND"), (3, "+3V3", "VOUT")], "TPS63020 buck-boost", "set 3.3 V · EN tied to VIN on the module"),
             ("J12 GAUGE", [(1, "BAT+", "CELL+"), (2, "GND", "GND"), (3, "SDA", "SDA"), (4, "SCL", "SCL"), (5, "+3V3", "VDD (if fitted)")],
              "MAX17048 fuel gauge", "battery % to the hub and cuff"),
             ("J3 POGO", [(1, "POGO+", "+ contact"), (2, "GND", "− contact")], "Magnetic 2-pin pogo", "bottom wall → charging dock 5 V"),
             ("J4 CUFF", [(1, "+3V3", "GX12-1"), (2, "GND", "GX12-2"), (3, "SDA", "GX12-3"), (4, "SCL", "GX12-4"), (5, "BTN", "GX12-5"), (6, "HAPTIC", "GX12-6")],
              "GX12 6-pin panel socket", "6-core sleeve cable to the cuff"),
             ("J6 SOS", [(1, "SOS_RAW", "NO"), (2, "GND", "NO")], "22 mm SOS button", "on the lid, guarded"),
             "SNAPS",
             ("J5 SKIN T", [(1, "+3V3", "snap 5 (red)"), (2, "ONEWIRE", "snap 6 (yellow)"), (3, "GND", "snap 1 (black)")], "DS18B20 skin probe", "under the arm, in the lining"),
             ("J7 ZIP", [(1, "ZIP_RAW", "snap 3"), (2, "GND", "snap 1")], "Reed switch at the zip top", "magnet in the puller: closed = LOW"),
             ("J8 TEAR", [(1, "TEAR_RAW", "snap 2"), (2, "GND", "snap 1")], "Conductive-thread loop", "stainless thread through all seams"),
             ("J9 SKIN PAD", [(1, "SKIN_PAD", "snap 4"), (2, "GND", "shield")], "Skin-contact pad", "copper / conductive fabric")],
            dx=340, dw=350)

    X2, DX, DW = 1100, 70, 330
    y = section(X2, 120, "WRIST CUFF (left forearm)", "Cuff board 46 × 42 mm", "no MCU — on the core's I²C bus",
                ["OLED + MAX30102 on short", "2.5 mm headers (thin cuff)", "", "Buttons on one ADC line:", "10 k pull-up · OK 2.2 k (0.6 V)",
                 "MENU 6.8 k (1.3 V) · SOS 0 V", "", "Motor: S8050 + 1N4148", "+ 100 nF, from +3V3"], 300,
                [("J1 TO CORE", [(1, "+3V3", "GX12-1"), (2, "GND", "GX12-2"), (3, "SDA", "GX12-3"), (4, "SCL", "GX12-4"), (5, "BTN", "GX12-5"), (6, "HAPTIC", "GX12-6")],
                  "GX12 6-pin socket", "elbow end · same pin = same wire"),
                 ("J2 BUTTONS", [(1, "BTN", "all 3, one side"), (2, "OK_R", "OK, other side"), (3, "MENU_R", "MENU, other side"), (4, "GND", "SOS, other side")],
                  "3 × 16 mm buttons", "short body ≤ 12 mm"),
                 ("J3 MOTOR", [(1, "+3V3", "red"), (2, "MOT_N", "blue")], "Coin motor 10 mm", "3 V, in the floor pocket")],
                DX, DW, "On the board: 1.3\" OLED (GND VCC SCL SDA — check yours) · MAX30102 underneath (VIN SCL SDA … GND)")
    y = section(X2, y + 50, "HELMET POD", "Helmet board 44 × 48 mm", "XIAO C6 + MAX98357A",
                ["D0 VBAT sense (220k/220k)", "D1 WORN · D2 LED", "D7 AMP_SD · D8 BCLK", "D9 LRC · D10 DIN", "", "LiPo on the XIAO BAT pads:",
                 "XIAO charges it (100 mA)", "from the pogo via 1N5819", "", "u.FL → FPC antenna in the lid"], 300,
                [("J1 BATT", [(1, "BAT+", "red +"), (2, "GND", "black −")], "LiPo 600 mAh", "503040, protected"),
                 ("J2 TO XIAO BAT", [(1, "BAT+", "XIAO BAT+"), (2, "GND", "XIAO BAT−")], "XIAO underside pads", "two short wires"),
                 ("J3 POGO", [(1, "POGO+", "+ contact"), (2, "GND", "− contact")], "Magnetic pogo", "dock 5 V"),
                 ("J4 WORN SW", [(1, "WORN", "NO"), (2, "GND", "C")], "Micro switch", "in the head harness")],
                DX, DW, "MAX98357A soldered low: LRC BCLK DIN GAIN SD GND VIN=BAT+ · 28 mm 8 Ω 1 W speaker on its terminal")
    y = section(X2, y + 50, "BOOT POD (right heel)", "Boot board 34 × 42 mm", "XIAO C6 + BMI270",
                ["D0 FSR (10 k to GND, ADC)", "D1 VBAT sense · D2 LED", "D3 IMU_INT · D4 SDA · D5 SCL", "", "BMI270 soldered low, glued:",
                 "X axis = walking direction", "", "LiPo on the XIAO BAT pads"], 300,
                [("J1 BATT", [(1, "BAT+", "red +"), (2, "GND", "black −")], "LiPo 300 mAh", "402030, protected"),
                 ("J2 POGO", [(1, "POGO+", "+ contact"), (2, "GND", "− contact")], "Magnetic pogo", "dock 5 V"),
                 ("J3 FSR", [(1, "+3V3", "lead 1"), (2, "FSR", "lead 2")], "FSR402 force sensor", "under the heel insole"),
                 ("J4 TO XIAO BAT", [(1, "BAT+", "XIAO BAT+"), (2, "GND", "XIAO BAT−")], "XIAO underside pads", "two short wires")],
                DX, DW)

    yb = max(yc, y) + 40
    s.note(40, yb, ["Radio and power",
                      "Helmet and boot pods are separate XIAO C6 nodes that talk to the core over ESP-NOW (suit key). Only the cuff is wired (6-core sleeve cable).",
                      "Every pod charges from the dock through its magnetic pogo socket (5 V). The core charges at 1 A (TP4056), helmet / boot through the XIAO's own charger.",
                      "Bring-up: modules out, power on, check 3.3 V on the core J11 pin 3 (and 5 V / BAT on the small pods) before fitting the XIAO and modules."], 1920)
    s.h = yb + 190
    s.o[0] = f'<rect width="{s.w}" height="{s.h}" fill="#ffffff"/>'
    s.legend(40, yb + 165, [("3V3", "3.3 V / battery +"), ("5V", "5 V / pogo"), ("GND", "GND / BAT−"), ("SDA", "SDA"), ("SCL", "SCL"), ("SIG", "signal")])
    s.save("suit_v4_wiring.svg")


if __name__ == "__main__":
    main()
