"""MineSafe PCB generator (KiCad 7 pcbnew + Freerouting), shared by the suit pod boards.

A board is a Python dict (see hardware/suit_pcb/boards.py):
    name, w, h, parts{ref: (lib, footprint, value, x, y, rot, {pad: net}, opts)}, power_nets, keepouts, texts
    x/y = top-left of the courtyard in mm, or None -> the auto-packer places the part near the pads it connects to.
    opts: {"back": True} puts a part on the bottom side.

Pipeline (python3 pcbgen.py <board-module> <name>):  place -> DSN -> Freerouting -> SES import -> GND pours ->
silkscreen -> zone fill -> DRC report -> Gerbers + drill -> JLCPCB zip -> top/bottom renders.
"""
import math
import os
import re
import subprocess
import zipfile

import pcbnew

LIB = "/usr/share/kicad/footprints"
OX, OY = 100.0, 100.0
mm = pcbnew.FromMM
TOOLS = os.environ.get("MS_PCBTOOLS", "/tmp/claude-0/-home-claude/bfd6cb35-a1c2-568c-8fcf-a502043d96e8/scratchpad/pcbtools")
STACK = os.environ.get("MS_STACKUP", "/tmp/claude-0/-home-claude/bfd6cb35-a1c2-568c-8fcf-a502043d96e8/scratchpad/pcb/stack")
SHOT = os.environ.get("MS_SVGSHOT", "/tmp/claude-0/-home-claude/bfd6cb35-a1c2-568c-8fcf-a502043d96e8/scratchpad/sarang_build")


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def _bbox(fp):
    """courtyard box (front or back) in board mm: (x0, y0, x1, y1)"""
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        c = fp.GetCourtyard(layer)
        if c.OutlineCount():
            b = c.BBox()
            break
    else:
        b = fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(b.GetLeft()) - OX, pcbnew.ToMM(b.GetTop()) - OY,
            pcbnew.ToMM(b.GetRight()) - OX, pcbnew.ToMM(b.GetBottom()) - OY)


def _move_topleft(fp, x, y):
    fp.SetPosition(P(0, 0))
    x0, y0, _, _ = _bbox(fp)
    fp.SetPosition(P(x - x0, y - y0))


def _hit(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def build(spec):
    W, H = spec["w"], spec["h"]
    board = pcbnew.BOARD()
    nets = {}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    fixed, auto = [], []
    for ref, part in spec["parts"].items():
        lib, fpn, val, x, y, rot, pads = part[:7]
        opts = part[7] if len(part) > 7 else {}
        fp = pcbnew.FootprintLoad(os.path.join(LIB, lib + ".pretty"), fpn)
        if fp is None:
            raise SystemExit(f"footprint not found: {lib}:{fpn}")
        fp.SetFPID(pcbnew.LIB_ID(lib, fpn))
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        if opts.get("back"):
            fp.Flip(fp.GetPosition(), False)
        for pad in fp.Pads():
            nm = pads.get(pad.GetNumber())
            if nm:
                pad.SetNet(net(nm))
        (fixed if x is not None else auto).append((ref, fp, x, y, rot, pads))

    occupied = [tuple(k) for k in spec.get("keepouts", [])]
    for ref, fp, x, y, rot, pads in fixed:
        _move_topleft(fp, x, y)
        occupied.append(_bbox(fp))

    # ---- auto-packer: biggest first, nearest free spot to the pads it shares nets with
    def pad_xy(fp):
        out = {}
        for pad in fp.Pads():
            if pad.GetNetname():
                out.setdefault(pad.GetNetname(), []).append((pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY))
        return out

    placed_pads = {}
    for ref, fp, *_ in fixed:
        for n, pts in pad_xy(fp).items():
            if n not in ("GND",) + tuple(spec.get("power_nets", [])):
                placed_pads.setdefault(n, []).extend(pts)
    auto.sort(key=lambda t: -(lambda b: (b[2] - b[0]) * (b[3] - b[1]))(_bbox(t[1])))
    import random
    rnd = random.Random(spec.get("_seed", 0))
    jit = 0.0 if not spec.get("_seed") else 4.0
    margin = spec.get("edge", 0.6)
    for ref, fp, _, _, rot, pads in auto:
        targets = [p for n in set(pads.values()) for p in placed_pads.get(n, [])]
        if not targets:
            targets = [(W / 2, H / 2)]
        tx = sum(p[0] for p in targets) / len(targets) + rnd.uniform(-jit, jit)
        ty = sum(p[1] for p in targets) / len(targets) + rnd.uniform(-jit, jit)
        best = None
        for r in (rot, (rot + 90) % 360):
            fp.SetOrientationDegrees(r)
            _move_topleft(fp, 0, 0)
            bw, bh = _bbox(fp)[2] - _bbox(fp)[0], _bbox(fp)[3] - _bbox(fp)[1]
            y = margin
            while y + bh <= H - margin + 1e-6:
                x = margin
                while x + bw <= W - margin + 1e-6:
                    box = (x, y, x + bw, y + bh)
                    if not any(_hit(box, o, 0.25) for o in occupied):
                        d = math.hypot(x + bw / 2 - tx, y + bh / 2 - ty)
                        if best is None or d < best[0]:
                            best = (d, r, x, y)
                    x += 0.5
                y += 0.5
        if best is None:
            raise SystemExit(f"auto-placer: no room for {ref}")
        _, r, x, y = best
        fp.SetOrientationDegrees(r)
        _move_topleft(fp, x, y)
        occupied.append(_bbox(fp))
        for n, pts in pad_xy(fp).items():
            placed_pads.setdefault(n, []).extend(pts)

    # outline with 2 mm corners
    r = spec.get("corner", 2.0)
    k = r * (1 - 0.70710678)

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)

    def arc(st, mid, en):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(P(*st), P(*mid), P(*en)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1)); board.Add(s)
    seg((r, 0), (W - r, 0)); seg((W, r), (W, H - r)); seg((W - r, H), (r, H)); seg((0, H - r), (0, r))
    arc((W - r, 0), (W - k, k), (W, r)); arc((W, H - r), (W - k, H - k), (W - r, H))
    arc((r, H), (k, H - k), (0, H - r)); arc((0, r), (k, k), (r, 0))
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_CopperEdgeClearance = mm(0.3)        # JLCPCB minimum copper-to-edge for routed boards
    return board, nets


def check(board, spec):
    boxes = [(fp.GetReference(), _bbox(fp), fp.IsFlipped()) for fp in board.GetFootprints()]
    bad, out = [], []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[2] != b[2] and not (a[0].startswith("H") or b[0].startswith("H")):
                # front vs back parts only clash where through-hole pads collide; keep a coarse check
                pass
            if _hit(a[1], b[1], -0.05):
                bad.append((a[0], b[0]))
    for ref, b, _ in boxes:
        if b[0] < -0.01 or b[1] < -0.01 or b[2] > spec["w"] + 0.01 or b[3] > spec["h"] + 0.01:
            out.append((ref, [round(v, 1) for v in b]))
    return bad, out


def export_dsn(board, path, power_nets):
    pcbnew.ExportSpecctraDSN(board, path)
    s = open(path).read()
    names = sorted({n.GetNetname() for n in board.GetNetInfo().NetsByName().values() if n.GetNetname()})
    sig = [n for n in names if n not in power_nets]
    pw = [n for n in names if n in power_nets]
    q = lambda n: f'"{n}"' if re.search(r'[\s()"]', n) else n
    block = (f"    (class signal {' '.join(map(q, sig))}\n      (circuit (use_via Via[0-1]_600:300_um))\n      (rule (width 300) (clearance 220))\n    )\n"
             f"    (class power {' '.join(map(q, pw))}\n      (circuit (use_via Via[0-1]_600:300_um))\n      (rule (width 600) (clearance 250))\n    )\n")
    s = re.sub(r"    \(class kicad_default.*?\n    \)\n", lambda m: block, s, flags=re.S)
    open(path, "w").write(s)


def freeroute(dsn, ses, passes=60):
    log = dsn.replace(".dsn", "_freerouting.log")
    for attempt in range(4):              # Freerouting 2.0 sometimes exits before writing the session; just retry
        with open(log, "w") as f:
            subprocess.run(["java", "-jar", os.path.join(TOOLS, "fr2.jar"), "--gui.enabled=false", "-de", dsn, "-do", ses,
                            "-mp", str(passes)], stdout=f, stderr=subprocess.STDOUT, timeout=900)
        if os.path.exists(ses) and os.path.getsize(ses) > 100:
            return True
    raise SystemExit("Freerouting produced no session file")


def _sexp(text):
    tokens = re.findall(r'"[^"]*"|\(|\)|[^\s()]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            d = cur; cur = stack.pop(); cur.append(d)
        else:
            cur.append(t.strip('"'))
    return cur[0]


def import_ses(board, path):
    root = _sexp(open(path).read())
    find = lambda node, key: [c for c in node if isinstance(c, list) and c and c[0] == key]
    routes = find(root, "routes")[0]
    res = find(routes, "resolution")[0]
    scale = {"um": 1e-3, "mm": 1.0, "mil": 0.0254}[res[1]] / float(res[2])
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
                t.SetWidth(mm(width)); t.SetLayer(layers[layer]); t.SetNet(ni); board.Add(t); ntr += 1
        for v in find(net, "via"):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(to(v[2], v[3])); via.SetWidth(mm(0.6)); via.SetDrill(mm(0.3))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(ni); board.Add(via); nvia += 1
    return ntr, nvia


def finish(board, spec):
    W, H = spec["w"], spec["h"]
    gnd = board.FindNet("GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(gnd); z.SetLocalClearance(mm(0.35)); z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(mm(0.35)); z.SetThermalReliefSpokeWidth(mm(0.5))
        o = z.Outline(); o.NewOutline()
        for x, y in ((0.4, 0.4), (W - 0.4, 0.4), (W - 0.4, H - 0.4), (0.4, H - 0.4)):
            o.Append(mm(OX + x), mm(OY + y))
        board.Add(z)
    for fp in board.GetFootprints():          # reference text small so it fits a dense board
        t = fp.Reference()
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); t.SetTextThickness(mm(0.12))
        v = fp.Value()
        if fp.GetReference()[0] in "JU" and not fp.GetReference().startswith("U1"):
            # connectors and modules: print what they are (BATT, CUFF, GY-521 ...) instead of J4 / U2
            v.SetLayer(pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS)
            v.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); v.SetTextThickness(mm(0.13))
            v.SetPosition(t.GetPosition()); v.SetTextAngle(t.GetTextAngle()); v.SetVisible(True)
            t.SetVisible(False)
        else:
            v.SetVisible(False)
    for s, x, y, size, back in spec.get("texts", []):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(s); t.SetPosition(P(x, y)); t.SetLayer(pcbnew.B_SilkS if back else pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(size * 0.17))
        if back:
            t.SetMirrored(True)
        board.Add(t)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def drc(board, path):
    pcbnew.WriteDRCReport(board, path, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(path).read()
    unconnected = re.search(r"Found (\d+) unconnected pads", txt)
    viol = re.search(r"Found (\d+) DRC violations", txt)
    kinds = {}
    for m in re.finditer(r"^\[(\w+)\]", txt, re.M):
        kinds[m.group(1)] = kinds.get(m.group(1), 0) + 1
    return (int(unconnected.group(1)) if unconnected else -1), (int(viol.group(1)) if viol else -1), kinds


def fab(pcb_path, outdir, name):
    g = os.path.join(outdir, "gerbers")
    os.makedirs(g, exist_ok=True)
    layers = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"
    subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "-o", g + "/", pcb_path],
                   check=True, capture_output=True)
    subprocess.run(["kicad-cli", "pcb", "export", "drill", "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2",
                    "-o", g + "/", pcb_path], check=True, capture_output=True)
    for f in os.listdir(g):
        if f.endswith("-drl_map.gbr"):
            os.remove(os.path.join(g, f))
    z = os.path.join(outdir, f"{name}_gerbers_jlcpcb.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(g)):
            zf.write(os.path.join(g, f), f)
    subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "-o",
                    os.path.join(outdir, f"{name}_positions.csv"), pcb_path], check=True, capture_output=True)
    return z


def render(outdir, name):
    g = os.path.join(outdir, "gerbers")
    rd = os.path.join(outdir, "renders")
    os.makedirs(rd, exist_ok=True)
    base = os.path.join(rd, name)
    subprocess.run(["node", os.path.join(STACK, "render.js"), g, base], check=True, capture_output=True, cwd=STACK)
    for side in ("top", "bottom"):
        svg = f"{base}_{side}.svg"
        html = svg.replace(".svg", ".html")
        open(html, "w").write('<html><body style="margin:0;background:#f4f2ec;padding:30px">' + open(svg).read() + "</body></html>")
        subprocess.run(["node", os.path.join(SHOT, "svgshot.mjs"), html, f"{base}_{side}.png", "1100"], check=True,
                       capture_output=True, cwd=SHOT)
        os.remove(html); os.remove(svg)


def run(spec, outdir, stage="all", tries=10):
    best = None
    for seed in range(tries):
        spec["_seed"] = seed
        res = _run_once(spec, outdir, stage)
        if res is None or res[0] == 0:
            return res
        print(f"  {res[0]} connection(s) left unrouted - re-placing (attempt {seed + 2})")
        best = res
    return best


def _run_once(spec, outdir, stage):
    os.makedirs(outdir, exist_ok=True)
    name = spec["name"]
    pcb = os.path.join(outdir, name + ".kicad_pcb")
    board, nets = build(spec)
    bad, out = check(board, spec)
    for b in bad:
        print("  OVERLAP", b)
    for o in out:
        print("  OUTSIDE", o)
    pcbnew.SaveBoard(pcb, board)
    print(f"  placed {len(spec['parts'])} parts, {len(nets)} nets")
    if stage == "place" or bad or out:
        return None
    dsn, ses = pcb.replace(".kicad_pcb", ".dsn"), pcb.replace(".kicad_pcb", ".ses")
    export_dsn(board, dsn, spec.get("power_nets", []) + ["GND"])
    if os.path.exists(ses):
        os.remove(ses)
    freeroute(dsn, ses)
    board = pcbnew.LoadBoard(pcb)
    ntr, nvia = import_ses(board, ses)
    finish(board, spec)
    pcbnew.SaveBoard(pcb, board)
    rpt = os.path.join(outdir, "drc.rpt")
    unc, viol, kinds = drc(board, rpt)
    if kinds.get("starved_thermal"):
        # pads whose thermal relief only got one spoke: connect them solidly to the ground pour instead
        txt = open(rpt).read()
        hits = re.findall(r"\[starved_thermal\].*?PTH pad (\S+) \[GND\] of (\S+)", txt, re.S)
        for padnum, ref in hits:
            for pd in board.FindFootprintByReference(ref).Pads():
                if pd.GetNumber() == padnum:
                    pd.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(pcb, board)
        unc, viol, kinds = drc(board, rpt)
    print(f"  routed: {ntr} segments, {nvia} vias · DRC unconnected {unc}, violations {viol} {kinds}")
    fab(pcb, outdir, name)
    render(outdir, name)
    return unc, viol, kinds
