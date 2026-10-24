"""3D stand-ins for the suit PCBs, read straight from the KiCad boards (part positions + realistic heights),
so the CadQuery enclosures are checked against the real layouts.

Local frame: x = u (KiCad right), y = -v (KiCad down -> up), board bottom at z=0, top at z=1.6.
"""
import os
import cadquery as cq
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.join(HERE, "..", "suit_pcb")
T = 1.6

HEIGHT = {"PinSocket": 8.5, "PinHeader": 3.0, "JST_PH": 6.0, "R_Axial": 5.5, "C_Disc": 6.0, "CP_Radial": 7.5,
          "TO-92": 5.0, "D_DO-41": 6.5, "D_DO-35": 5.5, "LED_D3": 5.5}


def _box(x0, y0, x1, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def board(name, low=(), modules=None):
    """returns (dict of named solids, info). low = refs soldered on short 2.5 mm headers instead of sockets.
    modules = {ref: (du0, dv0, du1, dv1, thickness)} module body footprint relative to that socket's courtyard."""
    b = pcbnew.LoadBoard(os.path.join(PCB_DIR, name, name + ".kicad_pcb"))
    W = H = 0
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            bb = d.GetBoundingBox()
            W = max(W, pcbnew.ToMM(bb.GetRight()) - 100); H = max(H, pcbnew.ToMM(bb.GetBottom()) - 100)
    W, H = round(W - 0.05, 2), round(H - 0.05, 2)      # outline drawn with a 0.1 mm line
    plate = cq.Workplane("XY").rect(W, H, centered=False).extrude(T).translate((0, -H, 0)).edges("|Z").fillet(2.0)
    holes, parts, bodies = [], [], []
    info = {"w": W, "h": H, "holes": [], "refs": {}}
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        fpn = fp.GetFPID().GetLibItemName().wx_str()
        p = fp.GetPosition()
        u, v = pcbnew.ToMM(p.x) - 100, pcbnew.ToMM(p.y) - 100
        if fpn.startswith("MountingHole"):
            info["holes"].append((u, v))
            plate = plate.cut(cq.Workplane("XY").center(u, -v).circle(1.1).extrude(5).translate((0, 0, -1)))
            continue
        cy = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
        bb = cy.BBox()
        u0, v0 = pcbnew.ToMM(bb.GetLeft()) - 100, pcbnew.ToMM(bb.GetTop()) - 100
        u1, v1 = pcbnew.ToMM(bb.GetRight()) - 100, pcbnew.ToMM(bb.GetBottom()) - 100
        info["refs"][ref] = (u0, v0, u1, v1, fp.IsFlipped())
        k = next((k for k in HEIGHT if k in fpn), None)
        h = HEIGHT.get(k, 3.0)
        if ref in low:
            h = 2.5
        # shrink the courtyard a little to the real body
        s = 0.25
        if fp.IsFlipped():
            parts.append(_box(u0 + s, -v1 + s, u1 - s, -v0 - s, -h, 0))
        else:
            parts.append(_box(u0 + s, -v1 + s, u1 - s, -v0 - s, T, T + h))
        if modules and ref in modules:
            du0, dv0, du1, dv1, th = modules[ref]
            if fp.IsFlipped():
                bodies.append(_box(u0 + du0, -(v0 + dv1), u0 + du1, -(v0 + dv0), -h - th, -h))
            else:
                bodies.append(_box(u0 + du0, -(v0 + dv1), u0 + du1, -(v0 + dv0), T + h, T + h + th))
    comp = parts[0]
    for q in parts[1:]:
        comp = comp.union(q)
    mod = None
    for q in bodies:
        mod = q if mod is None else mod.union(q)
    return {"pcb": plate, "parts": comp, "modules": mod}, info


def xiao_body(info, h_socket=8.5):
    """XIAO ESP32-C6 module on its two sockets (21 x 17.5 mm, USB-C 1 mm over the top edge)"""
    a, b_ = info["refs"]["U1A"], info["refs"]["U1B"]
    cx = (a[0] + a[2] + b_[0] + b_[2]) / 4
    z0 = T + h_socket
    body = _box(cx - 8.75, -21.0 + 0.2, cx + 8.75, 1.0, z0, z0 + 1.2)
    body = body.union(_box(cx - 4.5, -7.0, cx + 4.5, 1.0, z0 + 1.2, z0 + 4.4))     # USB-C
    body = body.union(_box(cx - 6.5, -18.0, cx + 6.5, -8.0, z0 + 1.2, z0 + 3.2))   # shield can
    return body, cx
