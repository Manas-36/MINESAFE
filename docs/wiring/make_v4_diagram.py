"""Draws the V4 smart-suit architecture (docs/wiring/v4_suit_architecture.svg). Run: python make_v4_diagram.py"""
from make_schematics import Sheet, NET, INK, MUTED, AMBER


def main():
    s = Sheet(1700, 1060, "MineSafe V4 — smart suit architecture",
              "One suit replaces the tagged kit · pods are removable so the suit can be washed · opening / tearing is reported, never locked")

    def unit(x, y, w, h, t, sub, dark=False, dash=False):
        if dark:
            s.box(x, y, w, h, "", "", fill="#12171A", stroke="#12171A")
            s.text(x + w / 2, y + 34, t, 16, "#F3F0E8", "middle", 700)
            for i, line in enumerate(sub):
                s.text(x + w / 2, y + 58 + i * 18, line, 12, AMBER, "middle", 600)
        else:
            s.box(x, y, w, h, "", "", dash=dash)
            s.text(x + w / 2, y + 30, t, 15, INK, "middle", 700)
            for i, line in enumerate(sub):
                s.text(x + w / 2, y + 52 + i * 18, line, 12, MUTED, "middle")

    # suit outline group
    s.box(40, 110, 860, 800, "", "", fill="#fbfaf6", dash=True)
    s.text(60, 140, "THE SUIT (one worker)", 14, INK, weight=700)
    unit(70, 170, 380, 150, "Helmet pod", ["XIAO ESP32-C6 · 2.4 GHz antenna (head height)", "speaker + amp: voice alerts", "helmet-worn switch · own 600 mAh battery"])
    unit(480, 170, 390, 150, "Wrist cuff", ["1.3\" OLED · 3 large buttons", "vibration motor", "MAX30102 heart rate + SpO₂"])
    unit(70, 400, 800, 180, "Core pod (chest)", ["ESP32-C6 · 3000 mAh battery · fuel gauge · charge contacts",
                                                  "IMU (fall, no movement) · pressure (level) · big SOS button",
                                                  "joins everything, decides SAFE / WARNING / DANGER, talks to the repeaters"], dark=True)
    unit(70, 660, 380, 170, "Suit fabric", ["FR coverall · conductive-thread loop in seams", "zip-closed reed switch · skin-contact pad",
                                            "skin temperature (chest)"])
    unit(480, 660, 390, 170, "Boot pod", ["XIAO ESP32-C6 · BMI270 foot IMU", "exact step length (foot-mounted)", "boot-worn force sensor"])
    # links inside the suit
    for (x1, y1, x2, y2, lab, net) in [(260, 320, 260, 400, "ESP-NOW (suit key)", "SDA"), (675, 320, 675, 400, "sleeve cable (I²C + GPIO)", "SCL"),
                                       (260, 580, 260, 660, "sewn wires / snaps", "SCL"), (675, 580, 675, 660, "ESP-NOW (suit key)", "SDA")]:
        s.wire([(x1, y1), (x2, y2)], net, 3)
        s.text(x1 + 10, (y1 + y2) / 2 + 4, lab, 12, NET[net], weight=700)

    # mine side
    unit(1000, 170, 300, 120, "Repeaters (tunnel)", ["ESP-NOW chain · LED exit signs", "gas + air · SOS · (LoRa backbone opt.)"])
    unit(1000, 400, 300, 140, "Entry chamber", ["main repeater (pairs the suit)", "ID-card tap (PN532) · phone photo", "charging dock for suits"])
    unit(1380, 400, 280, 140, "Hub + control app", ["laptop / mini-PC", "admin_hub.py · /control 3D app", "login · alerts · history"], dark=True)
    s.wire([(870, 470), (1000, 470)], "SDA", 3); s.text(935, 458, "ESP-NOW", 12, NET["SDA"], "middle", 700)
    s.wire([(1150, 290), (1150, 400)], "SDA", 3); s.text(1160, 350, "ESP-NOW chain", 12, NET["SDA"], weight=700)
    s.wire([(1300, 470), (1380, 470)], "SCL", 3); s.text(1305, 460, "Wi-Fi", 12, NET["SCL"], weight=700)
    s.wire([(1380, 500), (1300, 500)], "ANA", 2.4, dash=True)
    s.text(1305, 520, "alerts / route", 11, MUTED)

    s.note(960, 600, ["Shift flow",
                      "1  Take a charged suit from the dock, put it on.",
                      "2  Suit self-check: helmet, boots, cuff connected, zip closed, skin contact.",
                      "3  Tap ID card in the entry chamber (+ photo) → hub pairs suit ↔ worker.",
                      "4  Monitoring starts; kit is checked all shift, not only at the gate.",
                      "5  Helmet off / suit opened / torn → admin alert (never a lock).",
                      "6  Exit: unpair at the chamber, suit back on the dock."], 700)
    s.legend(40, 1020, [("SDA", "ESP-NOW radio"), ("SCL", "Wire / Wi-Fi"), ("ANA", "Commands down (dashed)")])
    s.save("v4_suit_architecture.svg")


if __name__ == "__main__":
    main()
