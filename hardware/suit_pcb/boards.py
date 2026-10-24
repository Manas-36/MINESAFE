"""MineSafe V4 smart-suit pod boards: core (chest), wrist cuff, helmet pod, boot pod.

All four are carrier boards for a Seeed XIAO ESP32-C6 and off-the-shelf breakout modules, all through-hole,
so the team can solder them by hand. Run:  python3 boards.py [core|cuff|helmet|boot|all] [--place]

XIAO pins, USB-C at the top edge:  left socket  D0 D1 D2 D3 D4/SDA D5/SCL D6   (top -> bottom)
                                   right socket 5V GND 3V3 D10 D9 D8 D7
ADC is only on D0-D2 (GPIO0-2). The ESP32-C6 has no capacitive-touch peripheral, so skin contact is read by
RC charge time on a normal GPIO (1 M pull-up, the pad + body adds capacitance).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pcbgen  # noqa: E402

SOCK = lambda n: ("Connector_PinSocket_2.54mm", f"PinSocket_1x0{n}_P2.54mm_Vertical")
HDR = lambda n: ("Connector_PinHeader_2.54mm", f"PinHeader_1x0{n}_P2.54mm_Vertical")
PH = lambda n: ("Connector_JST", f"JST_PH_B{n}B-PH-K_1x0{n}_P2.00mm_Vertical")
RV = ("Resistor_THT", "R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical")
CD = ("Capacitor_THT", "C_Disc_D3.0mm_W1.6mm_P2.50mm")
CE = ("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm")
TO92 = ("Package_TO_SOT_THT", "TO-92_Inline")
D41 = ("Diode_THT", "D_DO-41_SOD81_P2.54mm_Vertical_AnodeUp")
D35 = ("Diode_THT", "D_DO-35_SOD27_P2.54mm_Vertical_AnodeUp")
LED = ("LED_THT", "LED_D3.0mm")
M2 = ("MountingHole", "MountingHole_2.2mm_M2")
A = None   # auto-placed


def xiao(parts, x, y, left, right):
    """left = nets for D0..D6, right = nets for 5V GND 3V3 D10 D9 D8 D7 ('' = not connected)"""
    parts["U1A"] = (*SOCK(7), "XIAO D0-D6", x, y, 0, {str(i + 1): n for i, n in enumerate(left) if n})
    parts["U1B"] = (*SOCK(7), "XIAO 5V-D7", x + 15.24, y, 0, {str(i + 1): n for i, n in enumerate(right) if n})
    return (x + 3.6, y - 1.0, x + 15.24, y + 19.5)          # keep-out under the XIAO body


def holes(parts, pts):
    for i, (x, y) in enumerate(pts):
        parts[f"H{i + 1}"] = (*M2, "M2", x, y, 0, {})


# =============================================================================== CORE POD (chest)
def core():
    p = {}
    ko = [xiao(p, 24.0, 1.0,
               ["BTN", "SKIN", "TEAR", "ONEWIRE", "SDA", "SCL", "SOS"],
               ["", "GND", "+3V3", "IMU_INT", "HAPTIC", "LED", "ZIP"])]
    # wire pads to the three power modules that sit beside the board in the pod
    p["J10"] = (*HDR(6), "CHARGER", 0.5, 1.0, 0, {"1": "POGO+", "2": "GND", "3": "BAT+", "4": "BAT_N", "5": "CHG_OUT", "6": "GND"})
    p["J11"] = (*HDR(3), "BUCK-BOOST", 0.5, 19.0, 0, {"1": "VSYS", "2": "GND", "3": "+3V3"})   # EN tied to VIN on the module
    p["J12"] = (*HDR(5), "GAUGE", 4.8, 1.0, 0, {"1": "BAT+", "2": "GND", "3": "SDA", "4": "SCL", "5": "+3V3"})
    # JST-PH to the battery, switch, dock, cuff and the suit sensors
    p["J1"] = (*PH(2), "BATT", 44.0, 0.5, 0, {"1": "BAT+", "2": "BAT_N"})
    p["J2"] = (*PH(2), "PWR SW", 51.8, 0.5, 0, {"1": "CHG_OUT", "2": "VSYS"})
    p["J3"] = (*PH(2), "POGO", 60.3, 0.5, 90, {"1": "POGO+", "2": "GND"})
    p["J4"] = (*PH(6), "CUFF", 60.3, 8.5, 90, {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "BTN", "6": "HAPTIC"})
    p["J5"] = (*PH(3), "SKIN T", 60.3, 24.4, 90, {"1": "+3V3", "2": "ONEWIRE", "3": "GND"})
    p["J6"] = (*PH(2), "SOS", 60.3, 34.3, 90, {"1": "SOS_RAW", "2": "GND"})
    p["J7"] = (*PH(2), "ZIP", 60.3, 42.3, 90, {"1": "ZIP_RAW", "2": "GND"})
    p["J8"] = (*PH(2), "TEAR", 44.0, 48.0, 0, {"1": "TEAR_RAW", "2": "GND"})
    p["J9"] = (*PH(2), "SKIN PAD", 51.8, 48.0, 0, {"1": "SKIN_PAD", "2": "GND"})
    # sensor modules on sockets
    p["U2"] = (*SOCK(8), "GY-521 MPU6050", 6.0, 49.5, 90,
               {"1": "+3V3", "2": "GND", "3": "SCL", "4": "SDA", "8": "IMU_INT"})
    ko.append((6.0, 33.0, 27.4, 49.3))
    p["U3"] = (*SOCK(4), "GY-68 BMP180", 54.0, 24.0, 0, {"1": "+3V3", "2": "GND", "3": "SCL", "4": "SDA"})
    ko.append((41.5, 23.5, 54.0, 35.5))
    holes(p, [(0, 31.5), (9.5, 0), (38.0, 49.0), (54.5, 37.5)])
    # passives
    p["R1"] = (*RV, "4.7k", A, A, 0, {"1": "+3V3", "2": "ONEWIRE"})
    p["R2"] = (*RV, "1M", A, A, 0, {"1": "+3V3", "2": "SKIN"})
    p["R3"] = (*RV, "470", A, A, 0, {"1": "SKIN", "2": "SKIN_PAD"})
    for i, (raw, sig) in enumerate((("SOS_RAW", "SOS"), ("ZIP_RAW", "ZIP"), ("TEAR_RAW", "TEAR"))):
        p[f"R{4 + i}"] = (*RV, "1k", A, A, 0, {"1": raw, "2": sig})
        p[f"C{1 + i}"] = (*CD, "100nF", A, A, 0, {"1": sig, "2": "GND"})
    p["R7"] = (*RV, "1k", A, A, 0, {"1": "LED", "2": "LED_A"})
    p["LED1"] = (*LED, "STATUS", A, A, 0, {"1": "GND", "2": "LED_A"})
    p["C4"] = (*CE, "100uF 10V", A, A, 0, {"1": "+3V3", "2": "GND"})
    p["C5"] = (*CD, "100nF", A, A, 0, {"1": "+3V3", "2": "GND"})
    p["C6"] = (*CE, "100uF 10V", A, A, 0, {"1": "VSYS", "2": "GND"})
    return dict(name="core", w=66.0, h=54.0, parts=p, keepouts=ko,
                power_nets=["BAT+", "BAT_N", "CHG_OUT", "VSYS", "POGO+", "+3V3"],
                texts=[("MineSafe CORE POD v4.0", 33, 30, 1.3, True), ("TCET MME · Pednekar · Satale · Kanojia", 33, 33, 0.9, True),
                       ("github.com/Manas-36/MINESAFE", 33, 35.5, 0.9, True)])


# =============================================================================== WRIST CUFF
def cuff():
    p = {}
    # 1.3" SH1106 OLED on a 4-pin socket (sits over the whole board), MAX30102 underneath facing the skin
    p["U1"] = (*SOCK(4), "OLED 1.3in", 17.4, 0.5, 90, {"1": "GND", "2": "+3V3", "3": "SCL", "4": "SDA"})
    p["U2"] = (*SOCK(7), "MAX30102", 13.5, 24.0, 90, {"1": "+3V3", "2": "SCL", "3": "SDA", "7": "GND"}, {"back": True})
    p["J1"] = (*PH(6), "TO CORE", 15.5, 36.0, 0, {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "BTN", "6": "HAPTIC"})
    p["J2"] = (*PH(4), "BUTTONS", 0.5, 13.0, 90, {"1": "BTN", "2": "OK_R", "3": "MENU_R", "4": "GND"})
    p["J3"] = (*PH(2), "MOTOR", 40.0, 14.0, 90, {"1": "+3V3", "2": "MOT_N"})
    holes(p, [(0, 0), (41, 0), (0, 37), (41, 37)])
    # 3 buttons on one ADC line: 10k pull-up; OK -> 2.2k (0.6 V), MENU -> 6.8k (1.3 V), SOS -> GND (0 V), none = 3.3 V
    p["R1"] = (*RV, "10k", A, A, 0, {"1": "+3V3", "2": "BTN"})
    p["R2"] = (*RV, "2.2k", A, A, 0, {"1": "OK_R", "2": "GND"})
    p["R3"] = (*RV, "6.8k", A, A, 0, {"1": "MENU_R", "2": "GND"})
    p["C1"] = (*CD, "100nF", A, A, 0, {"1": "BTN", "2": "GND"})
    # vibration motor driver
    p["R4"] = (*RV, "1k", A, A, 0, {"1": "HAPTIC", "2": "Q_B"})
    p["R5"] = (*RV, "10k", A, A, 0, {"1": "Q_B", "2": "GND"})
    p["Q1"] = (*TO92, "S8050", A, A, 0, {"1": "GND", "2": "Q_B", "3": "MOT_N"})
    p["D1"] = (*D35, "1N4148", A, A, 0, {"1": "+3V3", "2": "MOT_N"})
    p["C2"] = (*CD, "100nF", A, A, 0, {"1": "+3V3", "2": "MOT_N"})
    p["C3"] = (*CD, "100nF", A, A, 0, {"1": "+3V3", "2": "GND"})
    return dict(name="cuff", w=46.0, h=42.0, parts=p, keepouts=[(13.0, 22.0, 33.0, 30.0)],
                power_nets=["+3V3"],
                texts=[("MineSafe WRIST CUFF v4.0", 23, 32, 1.1, True), ("MAX30102 this side - faces the skin", 23, 18, 0.9, True)])


# =============================================================================== HELMET POD
def helmet():
    p = {}
    ko = [xiao(p, 12.5, 1.0,
               ["VBAT_SNS", "WORN", "LED", "", "", "", ""],
               ["+5V", "GND", "+3V3", "I2S_DIN", "I2S_LRC", "I2S_BCLK", "AMP_SD"])]
    # MAX98357A breakout (Adafruit pin order) runs straight from the LiPo for full loudness
    p["U2"] = (*SOCK(7), "MAX98357A", 12.5, 44.0, 90,
               {"1": "I2S_LRC", "2": "I2S_BCLK", "3": "I2S_DIN", "5": "AMP_SD", "6": "GND", "7": "BAT+"})
    ko.append((12.0, 23.5, 32.0, 43.8))
    p["J1"] = (*PH(2), "BATT 600mAh", 0.5, 1.0, 90, {"1": "BAT+", "2": "GND"})
    p["J2"] = (*HDR(2), "TO XIAO BAT", 7.0, 1.0, 0, {"1": "BAT+", "2": "GND"})
    p["J3"] = (*PH(2), "POGO", 38.0, 1.0, 90, {"1": "POGO+", "2": "GND"})
    p["J4"] = (*PH(2), "WORN SW", 38.0, 9.0, 90, {"1": "WORN", "2": "GND"})
    holes(p, [(0, 42.5), (39, 42.5)])
    p["R1"] = (*RV, "220k", A, A, 0, {"1": "BAT+", "2": "VBAT_SNS"})
    p["R2"] = (*RV, "220k", A, A, 0, {"1": "VBAT_SNS", "2": "GND"})
    p["C1"] = (*CD, "100nF", A, A, 0, {"1": "VBAT_SNS", "2": "GND"})
    p["D1"] = (*D41, "1N5819", A, A, 0, {"1": "+5V", "2": "POGO+"})
    p["R3"] = (*RV, "1k", A, A, 0, {"1": "LED", "2": "LED_A"})
    p["LED1"] = (*LED, "STATUS", A, A, 0, {"1": "GND", "2": "LED_A"})
    p["C2"] = (*CE, "100uF 10V", A, A, 0, {"1": "BAT+", "2": "GND"})
    p["C3"] = (*CD, "100nF", A, A, 0, {"1": "+3V3", "2": "GND"})
    p["C4"] = (*CD, "100nF", A, A, 0, {"1": "WORN", "2": "GND"})
    return dict(name="helmet", w=44.0, h=48.0, parts=p, keepouts=ko,
                power_nets=["BAT+", "+5V", "POGO+", "+3V3"],
                texts=[("MineSafe HELMET POD v4.0", 22, 30, 1.1, True), ("antenna: XIAO u.FL -> FPC", 22, 33, 0.9, True)])


# =============================================================================== BOOT POD
def boot():
    p = {}
    ko = [xiao(p, 7.5, 1.0,
               ["FSR", "VBAT_SNS", "LED", "IMU_INT", "SDA", "SCL", ""],
               ["+5V", "GND", "+3V3", "", "", "", ""])]
    p["U2"] = (*SOCK(6), "BMI270", 8.85, 38.0, 90, {"1": "+3V3", "2": "GND", "3": "SCL", "4": "SDA", "5": "GND", "6": "IMU_INT"})
    ko.append((8.5, 25.5, 25.5, 37.8))
    p["J1"] = (*PH(2), "BATT 300mAh", 0.5, 1.0, 90, {"1": "BAT+", "2": "GND"})
    p["J2"] = (*PH(2), "POGO", 0.5, 9.0, 90, {"1": "POGO+", "2": "GND"})
    p["J3"] = (*PH(2), "FSR", 28.0, 1.0, 90, {"1": "+3V3", "2": "FSR"})
    p["J4"] = (*HDR(2), "TO XIAO BAT", 29.0, 9.0, 0, {"1": "BAT+", "2": "GND"})
    holes(p, [(0, 37), (29, 37)])
    p["R1"] = (*RV, "10k", A, A, 0, {"1": "FSR", "2": "GND"})
    p["C1"] = (*CD, "100nF", A, A, 0, {"1": "FSR", "2": "GND"})
    p["R2"] = (*RV, "220k", A, A, 0, {"1": "BAT+", "2": "VBAT_SNS"})
    p["R3"] = (*RV, "220k", A, A, 0, {"1": "VBAT_SNS", "2": "GND"})
    p["C2"] = (*CD, "100nF", A, A, 0, {"1": "VBAT_SNS", "2": "GND"})
    p["D1"] = (*D41, "1N5819", A, A, 0, {"1": "+5V", "2": "POGO+"})
    p["R4"] = (*RV, "1k", A, A, 0, {"1": "LED", "2": "LED_A"})
    p["LED1"] = (*LED, "STATUS", A, A, 0, {"1": "GND", "2": "LED_A"})
    p["C3"] = (*CD, "100nF", A, A, 0, {"1": "+3V3", "2": "GND"})
    return dict(name="boot", w=34.0, h=42.0, parts=p, keepouts=ko,
                power_nets=["BAT+", "+5V", "POGO+", "+3V3"],
                texts=[("MineSafe BOOT POD v4.0", 17, 30, 1.0, True), ("BMI270 axis X = walking direction", 17, 32.5, 0.8, True)])


BOARDS = {"core": core, "cuff": cuff, "helmet": helmet, "boot": boot}

if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if not a.startswith("--")] or ["all"]
    names = list(BOARDS) if "all" in which else which
    here = os.path.dirname(os.path.abspath(__file__))
    for n in names:
        print(f"== {n}")
        pcbgen.run(BOARDS[n](), os.path.join(here, n), "place" if "--place" in sys.argv else "all")
