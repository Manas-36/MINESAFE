"""Builds the MineSafe repeater carrier PCB (KiCad 7) from the netlist below.

    python3 build_board.py            -> repeater.kicad_pcb (placed, unrouted) + repeater.dsn for Freerouting
    python3 build_board.py --finish   -> imports repeater.ses (routes), adds ground pours, silkscreen, saves

Pins follow firmware/repeater_node/repeater_node.ino (XIAO ESP32-C6 build, v3.3):
  gas 1 D2/GPIO2 · gas 2 D0/GPIO0 · gas 3 D1/GPIO1 · matrix DIN D9 / CS D3 / CLK D8 · SDA D4 · SCL D5
  SOS D6/GPIO16 · buzzer D10/GPIO18 · NEW: mains-present D7/GPIO17 (low = mine supply on, running on battery when high)
"""
import os
import sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = "/usr/share/kicad/footprints"
BOARD_W, BOARD_H = 100.0, 75.0
OX, OY = 100.0, 100.0                      # board origin on the KiCad sheet

mm = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


# ---------------------------------------------------------------- parts
# ref: (library, footprint, value, left, top, rotation, {pad: net})
# left/top = top-left corner of the part's courtyard on the board (mm), so parts never overlap by accident
R0207 = ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal")
CDISC = ("Capacitor_THT", "C_Disc_D5.0mm_W2.5mm_P5.00mm")
XH = lambda n: ("Connector_JST", f"JST_XH_B{n}B-XH-A_1x0{n}_P2.50mm_Vertical")
TB2 = ("TerminalBlock_Phoenix", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal")
XL = 44.0                                   # XIAO left socket courtyard; right socket = +15.24 mm (XIAO row spacing)
PARTS = {
    # --- power in: mine DC supply 9-30 V and a 12 V backup battery, OR-ed by Schottky diodes -> fuse -> TVS -> 5 V module
    "J1": (*TB2, "MAIN 9-30V", 0.5, 9.0, 90, {"1": "VIN_MAIN", "2": "GND"}),
    "J2": (*TB2, "BATT 12V", 0.5, 22.0, 90, {"1": "VIN_BAT", "2": "GND"}),
    "D1": ("Diode_THT", "D_DO-201AD_P15.24mm_Horizontal", "1N5822", 13.0, 9.0, 0, {"1": "VRAIL", "2": "VIN_MAIN"}),
    "D2": ("Diode_THT", "D_DO-201AD_P15.24mm_Horizontal", "1N5822", 13.0, 16.5, 0, {"1": "VRAIL", "2": "VIN_BAT"}),
    "F1": ("Fuse", "Fuse_Littelfuse_372_D8.50mm", "T1.6A TR5", 13.0, 24.0, 0, {"1": "VRAIL", "2": "VPROT"}),
    "C1": ("Capacitor_THT", "CP_Radial_D10.0mm_P5.00mm", "470uF 50V", 24.0, 24.0, 0, {"1": "VPROT", "2": "GND"}),
    "D3": ("Diode_THT", "D_DO-15_P10.16mm_Horizontal", "P6KE36A", 14.0, 35.5, 0, {"1": "VPROT", "2": "GND"}),
    "U1": ("Converter_DCDC", "Converter_DCDC_RECOM_R-78B-2.0_THT", "K7805-2000R3", 14.5, 41.0, 0, {"1": "VPROT", "2": "GND", "3": "+5V"}),
    "C2": ("Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm", "220uF 16V", 28.0, 41.0, 0, {"1": "+5V", "2": "GND"}),
    "C3": (*CDISC, "100nF", 28.0, 51.0, 0, {"1": "+5V", "2": "GND"}),
    # mains-present detector: mine supply on -> Q2 on -> MAINS_N low (to D7)
    "R2": (*R0207, "22k", 0.5, 35.5, 0, {"1": "VIN_MAIN", "2": "Q2_B"}),
    "Q2": ("Package_TO_SOT_THT", "TO-92_Inline", "S8050", 1.0, 40.0, 0, {"1": "GND", "2": "Q2_B", "3": "MAINS_N"}),
    "R3": (*R0207, "10k", 0.5, 46.0, 0, {"1": "Q2_B", "2": "GND"}),
    "R4": (*R0207, "10k", 0.5, 50.5, 0, {"1": "+3V3", "2": "MAINS_N"}),
    # power LED
    "R1": (*R0207, "1k", 0.5, 56.0, 0, {"1": "+5V", "2": "LED_A"}),
    "LED1": ("LED_THT", "LED_D3.0mm", "PWR", 14.5, 55.5, 0, {"1": "GND", "2": "LED_A"}),
    # --- XIAO ESP32-C6 on two 7-pin sockets, USB-C towards the top edge (left column D0-D6, right 5V GND 3V3 D10 D9 D8 D7)
    "U2A": ("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "XIAO D0-D6", XL, 2.0, 0,
            {"1": "GAS2", "2": "GAS3", "3": "GAS1", "4": "MX_CS", "5": "SDA", "6": "SCL", "7": "SOS"}),
    "U2B": ("Connector_PinSocket_2.54mm", "PinSocket_1x07_P2.54mm_Vertical", "XIAO 5V-D7", XL + 15.24, 2.0, 0,
            {"1": "+5V", "2": "GND", "3": "+3V3", "4": "BUZ", "5": "MX_DIN", "6": "MX_CLK", "7": "MAINS_N"}),
    # --- 3.3 V -> 5 V logic for the MAX7219 matrix (needs 3.5 V high at 5 V supply)
    "U3": ("Package_DIP", "DIP-14_W7.62mm_Socket", "74HCT125", 68.0, 2.0, 0,
           {"1": "GND", "2": "MX_DIN", "3": "DIN5", "4": "GND", "5": "MX_CS", "6": "CS5", "7": "GND",
            "8": "CLK5", "9": "MX_CLK", "10": "GND", "12": "GND", "13": "+5V", "14": "+5V"}),
    "C4": (*CDISC, "100nF", 64.6, 2.0, 90, {"1": "+5V", "2": "GND"}),
    # --- right edge connectors
    "J7": (*XH(5), "MATRIX", 92.5, 9.0, 90, {"1": "+5V", "2": "GND", "3": "DIN5", "4": "CS5", "5": "CLK5"}),
    "J8": (*XH(2), "BUZZER", 92.5, 27.0, 90, {"1": "+5V", "2": "BUZ_N"}),
    "J9": (*XH(2), "SOS", 92.5, 37.0, 90, {"1": "SOS", "2": "GND"}),
    "J6": (*XH(4), "AHT20", 92.5, 47.0, 90, {"1": "+3V3", "2": "GND", "3": "SDA", "4": "SCL"}),
    # buzzer driver
    "R5": (*R0207, "1k", 68.5, 27.0, 0, {"1": "BUZ", "2": "Q1_B"}),
    "D4": ("Diode_THT", "D_DO-35_SOD27_P7.62mm_Horizontal", "1N4148", 81.0, 27.0, 90, {"1": "+5V", "2": "BUZ_N"}),
    "Q1": ("Package_TO_SOT_THT", "TO-92_Inline", "S8050", 85.0, 28.0, 0, {"1": "GND", "2": "Q1_B", "3": "BUZ_N"}),
    # SOS debounce, I2C pull-ups
    "C5": (*CDISC, "100nF", 84.5, 38.0, 0, {"1": "SOS", "2": "GND"}),
    "R6": (*R0207, "4.7k", 66.0, 40.0, 0, {"1": "+3V3", "2": "SDA"}),
    "R7": (*R0207, "4.7k", 66.0, 44.5, 0, {"1": "+3V3", "2": "SCL"}),
}
# --- three MQ gas sensor inputs on the bottom edge: AO -> 10k -> GASx (ADC) -> 20k -> GND, 100 nF filter
for n, x in ((1, 36.0), (2, 54.0), (3, 72.0)):
    PARTS[f"J{2 + n}"] = (*XH(4), f"MQ{n}", x, 67.0, 0, {"1": "+5V", "2": "GND", "4": f"AO{n}"})
    PARTS[f"R{10 + n}"] = (*R0207, "10k", x + 1.0, 52.0, 90, {"1": f"AO{n}", "2": f"GAS{n}"})
    PARTS[f"R{20 + n}"] = (*R0207, "20k", x + 5.0, 52.0, 90, {"1": f"GAS{n}", "2": "GND"})
    PARTS[f"C{10 + n}"] = (*CDISC, "100nF", x + 9.0, 57.0, 90, {"1": f"GAS{n}", "2": "GND"})
BOARD_W, BOARD_H = 100.0, 75.0
for i, (x, y) in enumerate([(0, 0), (BOARD_W - 7, 0), (0, BOARD_H - 7), (BOARD_W - 7, BOARD_H - 7)]):
    PARTS[f"H{i + 1}"] = ("MountingHole", "MountingHole_3.2mm_M3", "M3", x, y, 0, {})

POWER_NETS = ["VIN_MAIN", "VIN_BAT", "VRAIL", "VPROT", "+5V", "GND"]


def build():
    board = pcbnew.BOARD()
    nets = {}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    for ref, (lib, fpn, val, x, y, rot, pads) in PARTS.items():
        fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), fpn)
        if fp is None:
            raise SystemExit(f"footprint not found: {lib}:{fpn}")
        fp.SetFPID(pcbnew.LIB_ID(lib, fpn))            # keeps the link to the standard KiCad library
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(0, 0))
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox(False, False)
        fp.SetPosition(pcbnew.VECTOR2I(mm(OX + x) - (bb.GetLeft() - mm(OX)), mm(OY + y) - (bb.GetTop() - mm(OY))))
        board.Add(fp)
        for pad in fp.Pads():
            nm = pads.get(pad.GetNumber())
            if nm:
                pad.SetNet(net(nm))

    # board outline with 3 mm corner radius
    ec = pcbnew.Edge_Cuts
    r = 3.0
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(ec); s.SetWidth(mm(0.1))
        board.Add(s)
    def arc(c, start, mid, end):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(P(*start), P(*mid), P(*end)); s.SetLayer(ec); s.SetWidth(mm(0.1))
        board.Add(s)
    W, H = BOARD_W, BOARD_H
    k = r * (1 - 0.70710678)
    seg((r, 0), (W - r, 0)); seg((W, r), (W, H - r)); seg((W - r, H), (r, H)); seg((0, H - r), (0, r))
    arc(None, (W - r, 0), (W - k, k), (W, r)); arc(None, (W, H - r), (W - k, H - k), (W - r, H))
    arc(None, (r, H), (k, H - k), (0, H - r)); arc(None, (0, r), (k, k), (r, 0))

    # design rules: 0.3 mm tracks / 0.25 mm clearance, power 0.8 mm (set again in the DSN for Freerouting)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    return board, nets


def overlaps(board):
    """Report footprints whose courtyards overlap (placement check)."""
    fps = list(board.GetFootprints())
    boxes = []
    for fp in fps:
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False, False)
        boxes.append((fp.GetReference(), bb))
    bad = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][1], boxes[j][1]
            if a.Intersects(b):
                ov = min(a.GetRight(), b.GetRight()) - max(a.GetLeft(), b.GetLeft()), min(a.GetBottom(), b.GetBottom()) - max(a.GetTop(), b.GetTop())
                if ov[0] > mm(0.05) and ov[1] > mm(0.05):
                    bad.append((boxes[i][0], boxes[j][0], round(pcbnew.ToMM(ov[0]), 2), round(pcbnew.ToMM(ov[1]), 2)))
    # outside the board?
    out = []
    for ref, bb in boxes:
        if bb.GetLeft() < mm(OX - 0.01) or bb.GetTop() < mm(OY - 0.01) or bb.GetRight() > mm(OX + BOARD_W + 0.01) or bb.GetBottom() > mm(OY + BOARD_H + 0.01):
            out.append((ref, [round(pcbnew.ToMM(v) - o, 1) for v, o in ((bb.GetLeft(), OX), (bb.GetTop(), OY), (bb.GetRight(), OX), (bb.GetBottom(), OY))]))
    return bad, out


def sexp(text):
    """Tiny s-expression reader for the Freerouting .ses file."""
    import re
    tokens = re.findall(r'"[^"]*"|\(|\)|[^\s()]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        else:
            cur.append(t.strip('"'))
    return cur[0]


def import_ses(board, path):
    """Adds the routed wires and vias from a Freerouting session (units 0.1 um, y axis flipped)."""
    root = sexp(open(path).read())
    def find(node, key):
        return [c for c in node if isinstance(c, list) and c and c[0] == key]
    routes = find(root, "routes")[0]
    res = find(routes, "resolution")[0]
    scale = {"um": 1e-3, "mm": 1.0, "mil": 0.0254}[res[1]] / float(res[2])      # file unit -> mm
    to = lambda x, y: pcbnew.VECTOR2I(mm(float(x) * scale), mm(-float(y) * scale))
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    ntr = nvia = 0
    for net in find(find(routes, "network_out")[0], "net"):
        ni = board.FindNet(net[1])
        for w in find(net, "wire"):
            path = find(w, "path")[0]
            layer, width, pts = path[1], float(path[2]) * scale, path[3:]
            for i in range(0, len(pts) - 2, 2):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(to(pts[i], pts[i + 1])); t.SetEnd(to(pts[i + 2], pts[i + 3]))
                t.SetWidth(mm(width)); t.SetLayer(layers[layer]); t.SetNet(ni)
                board.Add(t); ntr += 1
        for v in find(net, "via"):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(to(v[2], v[3])); via.SetWidth(mm(0.6)); via.SetDrill(mm(0.3))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(ni)
            board.Add(via); nvia += 1
    return ntr, nvia


if __name__ == "__main__":
    pcb = os.path.join(HERE, "repeater.kicad_pcb")
    if "--finish" not in sys.argv:
        board, nets = build()
        bad, out = overlaps(board)
        for b in bad:
            print("OVERLAP", b)
        for o in out:
            print("OUTSIDE", o)
        pcbnew.SaveBoard(pcb, board)
        print("nets:", len(nets), "parts:", len(PARTS))
    else:
        board = pcbnew.LoadBoard(pcb)
        ntr, nvia = import_ses(board, os.path.join(HERE, "repeater.ses"))
        print(f"imported {ntr} track segments, {nvia} vias")
        gnd = board.FindNet("GND")
        # ground pour on both layers, 0.4 mm clearance, thermal reliefs on pads
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            z = pcbnew.ZONE(board)
            z.SetLayer(layer)
            z.SetNet(gnd)
            z.SetLocalClearance(mm(0.4))
            z.SetMinThickness(mm(0.3))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(mm(0.4))
            z.SetThermalReliefSpokeWidth(mm(0.6))
            o = z.Outline()
            o.NewOutline()
            for x, y in ((0.5, 0.5), (BOARD_W - 0.5, 0.5), (BOARD_W - 0.5, BOARD_H - 0.5), (0.5, BOARD_H - 0.5)):
                o.Append(mm(OX + x), mm(OY + y))
            board.Add(z)
        # silkscreen: title, connector labels, polarity and warnings
        def text(s, x, y, size=1.2, layer=pcbnew.F_SilkS, bold=False, rot=0):
            t = pcbnew.PCB_TEXT(board)
            t.SetText(s); t.SetPosition(P(x, y)); t.SetLayer(layer)
            t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
            t.SetTextAngleDegrees(rot)
            if layer == pcbnew.B_SilkS:
                t.SetMirrored(True)
            board.Add(t)
        text("MineSafe REPEATER v4.0", 17.5, 62.0, 1.6, bold=True)
        text("conformal-coat after test", 17.5, 64.6, 0.9)
        text("XIAO ESP32-C6 - USB-C UP", 53.4, 27.6, 0.9)
        text("MAIN 9-30V", 6.0, 7.6, 0.9); text("BATT 12V", 6.0, 21.1, 0.9)
        for fp in board.GetFootprints():                      # + / - next to each screw of the power terminals
            if fp.GetReference() in ("J1", "J2"):
                for pad in fp.Pads():
                    y = pcbnew.ToMM(pad.GetPosition().y) - OY
                    text("+" if pad.GetNumber() == "1" else "-", 12.3, y, 1.4, bold=True)
        text("TCET MME 2026-27 · Pednekar · Satale · Kanojia", 50, 72.8, 1.0, pcbnew.B_SilkS)
        text("github.com/Manas-36/MINESAFE", 50, 70.8, 1.0, pcbnew.B_SilkS)
        for fp in board.GetFootprints():
            if fp.GetReference() in ("J1", "J2"):
                fp.Reference().SetVisible(False)          # the value text (MAIN 9-30V / BATT 12V) names them
            if fp.GetReference() == "C13":
                for pad in fp.Pads():
                    if pad.GetNumber() == "2":
                        pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(pcb, board)
        print("routed board saved")
