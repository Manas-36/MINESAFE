"""MineSafe V4 suit pod enclosures (CadQuery). Each function returns (parts dict, contents dict).

Pod frame: X = width, Y = up (when worn), Z = out from the body / helmet / boot (back of the pod at Z~0).
Contents = the real PCB (from KiCad, see pcb3d.py) + batteries, modules, buttons as blocks for the fit check.
"""
import math
import cadquery as cq
import pcb3d

T = pcb3d.T


# ------------------------------------------------------------------ helpers
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(x, y, z0, dz, d):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(dz)


def cyl_x(y, z, x0, dx, d):
    return cq.Workplane("YZ", origin=(x0, 0, 0)).center(y, z).circle(d / 2).extrude(dx)


def cyl_y(x, z, y0, dy, d):
    return cq.Workplane("XZ", origin=(0, y0, 0)).center(x, z).circle(d / 2).extrude(-dy)


def rbox(w, h, z0, z1, r):
    return cq.Workplane("XY").workplane(offset=z0).rect(w, h).extrude(z1 - z0).edges("|Z").fillet(r)


def place(shape, rot_z=0, flip=False, t=(0, 0, 0)):
    s = shape
    if flip:
        s = s.rotate((0, 0, 0), (0, 1, 0), 180)
    if rot_z:
        s = s.rotate((0, 0, 0), (0, 0, 1), rot_z)
    return s.translate(t)


def board_contents(name, low, mods, xiao=True, rot_z=0, flip=False, t=(0, 0, 0)):
    s, info = pcb3d.board(name, low, mods)
    out = {f"{name}_pcb": place(s["pcb"], rot_z, flip, t), f"{name}_parts": place(s["parts"], rot_z, flip, t)}
    if s["modules"] is not None:
        out[f"{name}_modules"] = place(s["modules"], rot_z, flip, t)
    if xiao:
        xb, cx = pcb3d.xiao_body(info)
        out[f"{name}_xiao"] = place(xb, rot_z, flip, t)
        info["xiao_cx"] = cx
    return out, info


def shell_pod(W, H, zb, r, wall=2.2, floor=2.2, concave=None):
    """open-top tray. concave = ('cyl_x'|'cyl_y'|'sphere', R, depth) carves the back to sit on an arm / boot / helmet"""
    b = rbox(W, H, 0, zb, r)
    if concave:
        kind, R, dep = concave
        if kind == "cyl_x":
            cut = cq.Workplane("YZ", origin=(-W, 0, 0)).center(0, dep - R).circle(R).extrude(2 * W)
        elif kind == "cyl_y":
            cut = cq.Workplane("XZ", origin=(0, H, 0)).center(0, dep - R).circle(R).extrude(2 * H)
        else:
            cut = cq.Workplane("XY").sphere(R).translate((0, 0, dep - R))
        outer = b.cut(cut)
        inner = rbox(W - 2 * wall, H - 2 * wall, 0, zb + 1, max(r - wall, 0.5)).cut(cut.translate((0, 0, floor)))
        return outer.cut(inner), cut
    return b.faces(">Z").shell(-wall), None


def lid_plate(W, H, z0, plate, r, wall=2.2, skirt=3.0, skirt_t=1.4):
    l = rbox(W, H, z0, z0 + plate, r)
    sk = rbox(W - 2 * wall - 0.3, H - 2 * wall - 0.3, z0 - skirt, z0, max(r - wall, 0.5))
    sk = sk.cut(rbox(W - 2 * wall - 0.3 - 2 * skirt_t, H - 2 * wall - 0.3 - 2 * skirt_t, z0 - skirt - 1, z0 + 1, max(r - wall - skirt_t, 0.5)))
    return l.union(sk)


def screw_bosses(b, pts, z0, z1, d=6.0, pilot=1.8):
    for x, y in pts:
        b = b.union(cyl(x, y, z0, z1 - z0, d)).cut(cyl(x, y, z0 + 2, z1 - z0, pilot))
    return b


def lid_screws(l, pts, ztop, d=2.4, head=4.4):
    for x, y in pts:
        l = l.cut(cyl(x, y, ztop - 10, 11, d))
        l = l.cut(cq.Workplane("XY").workplane(offset=ztop - (head - d) / 2).center(x, y).circle(d / 2).workplane(offset=(head - d) / 2).circle(head / 2).loft().translate((0, 0, 0)))
    return l


def strap_lugs(b, xs, side_y, z0, z1, strap=25.0, along="x"):
    """loops either side of the pod for webbing: slot opening faces down the body (Z) so the strap wraps the limb"""
    for sx in (-1, 1):
        if along == "x":      # lugs on the +/-Y sides, strap width along X
            y_out = sx * side_y
            for xc in xs:
                lug = box(xc - strap / 2 - 2.5, xc + strap / 2 + 2.5, min(y_out, y_out + sx * 6.5), max(y_out, y_out + sx * 6.5), z0, z1)
                lug = lug.cut(box(xc - strap / 2 - 0.5, xc + strap / 2 + 0.5, min(y_out + sx * 1.5, y_out + sx * 4.5),
                                  max(y_out + sx * 1.5, y_out + sx * 4.5), z0 - 1, z1 + 1))
                b = b.union(lug.edges("|Z").fillet(1.0))
        else:                 # lugs on the +/-X sides, strap width along Y
            x_out = sx * side_y
            for yc in xs:
                lug = box(min(x_out, x_out + sx * 6.5), max(x_out, x_out + sx * 6.5), yc - strap / 2 - 2.5, yc + strap / 2 + 2.5, z0, z1)
                lug = lug.cut(box(min(x_out + sx * 1.5, x_out + sx * 4.5), max(x_out + sx * 1.5, x_out + sx * 4.5),
                                  yc - strap / 2 - 0.5, yc + strap / 2 + 0.5, z0 - 1, z1 + 1))
                b = b.union(lug.edges("|Z").fillet(1.0))
    return b


def text_on(l, s, x, y, z, size, depth=0.6):
    try:
        return l.union(cq.Workplane("XY").workplane(offset=z).center(x, y).text(s, size, depth, kind="bold"))
    except Exception:
        return l


# ================================================================== CORE POD (chest)
def core_pod():
    W, H, R = 116.0, 86.0, 10.0
    ZB, ZT = 25.6, 31.1                 # base rim, lid top
    LID_IN = 28.6                       # lid inner face
    XI, YI = W / 2 - 2.5, H / 2 - 2.5   # inner half sizes 55.5 x 40.5
    b, _ = shell_pod(W, H, ZB, R, wall=2.5, floor=2.5)
    # board hangs under the lid, components down: x = 19 - u, y = 31 - v, top (component side) at z 24.5
    C, info = board_contents("core", (), {"U2": (0.2, -12.4, 21.2, 3.6, 3.0), "U3": (-9.4, 0.5, 3.6, 10.7, 2.5)},
                             flip=True, t=(19.0, 31.0, 24.5 + T))
    holes = [(19.0 - u, 31.0 - v) for u, v in info["holes"]]
    corner = [(50.0, 35.5), (-50.0, 35.5), (-50.0, -35.5), (50.0, -35.5)]
    b = screw_bosses(b, corner, 0, ZB, 7.0, 1.8)
    # battery tray (805070 LiPo 3000 mAh) + module bay ribs
    bx0, bx1, by0, by1 = -36.0, 36.0, -21.0, 31.0
    for x in (bx0 - 1.5, bx1):
        b = b.union(box(x, x + 1.5, by0, by1, 2.5, 7.0))
    b = b.union(box(bx0 - 1.5, bx1 + 1.5, by0 - 1.5, by0, 2.5, 7.0))
    # USB-C service port (XIAO) with plug recess, top wall
    ux = 19.0 - info["xiao_cx"]
    b = b.cut(box(ux - 6, ux + 6, YI - 1, YI + 4, 11.0, 17.0))
    b = b.cut(box(ux - 8, ux + 8, YI + 1.5, YI + 4, 9.5, 18.5))
    # power toggle (6 mm) on the top wall inside a guard fence
    b = b.cut(cyl_y(40.0, 16.0, YI - 1, 5, 6.4))
    for dx in (-7, 7):
        b = b.union(box(40 + dx - 1.2, 40 + dx + 1.2, YI + 2.5, YI + 9, 9.0, 23.0))
    # cuff cable: GX12 6-pin panel socket on the worker's LEFT side (= pod +X)
    b = b.cut(cyl_x(-14.0, 14.0, XI - 1, 5, 12.2))
    b = b.union(cyl_x(-14.0, 14.0, XI + 2.5, 1.5, 20).cut(cyl_x(-14.0, 14.0, XI, 6, 12.2)))
    # magnetic 2-pin pogo charge socket, bottom wall (drops into the dock)
    b = b.cut(box(30.0, 46.0, -YI - 4, -YI + 1, 5.0, 11.0))
    # 6 snap studs on the back to the suit wiring: GND TEAR ZIP SKIN-PAD 3V3 1-WIRE
    for i in range(6):
        x = -40.0 + i * 8.0
        b = b.cut(cyl(x, -30.0, -1, 4, 4.2)).cut(cyl(x, -30.0, -1, 1.2, 9.5))
    # webbing loops on the back for the chest harness (25 mm strap runs along X behind the pod)
    for sx in (-1, 1):
        loop = box(sx * 40 - 6, sx * 40 + 6, -17, 17, -6.0, 0.2)
        loop = loop.cut(box(sx * 40 - 7, sx * 40 + 7, -14, 14, -4.5, -1.5))
        b = b.union(loop.edges("|X").fillet(1.0))
    # ---------------- lid
    l = lid_plate(W, H, LID_IN, ZT - LID_IN, R, wall=2.5)
    l = l.union(rbox(W, H, ZB, LID_IN, R).cut(rbox(W - 5, H - 5, ZB - 1, LID_IN + 0.01, R - 2.5)))
    for x, y in holes:                  # PCB bosses hanging from the lid
        l = l.union(cyl(x, y, 24.5 + T, LID_IN - 24.5 - T + 0.1, 5.0)).cut(cyl(x, y, 24.0, 4.0, 1.8))
    l = lid_screws(l, corner, ZT)
    # SOS: 22 mm IP67 short-body button + guard ring with two finger gaps
    sx, sy = 36.0, 8.0
    l = l.cut(cyl(sx, sy, LID_IN - 1, 5, 22.5))
    g = cyl(sx, sy, ZT, 7, 44).cut(cyl(sx, sy, ZT - 1, 9, 35))
    l = l.union(g.cut(box(sx - 25, sx + 25, sy - 5, sy + 5, ZT - 1, ZT + 8)))
    # reflective band + label
    l = l.cut(box(-W / 2 + 6, W / 2 - 6, -H / 2 + 6, -H / 2 + 14, ZT - 0.6, ZT + 1))
    l = text_on(l, "MINESAFE", -14, 22, ZT, 9)
    l = text_on(l, "SOS", sx, sy - 18, ZT, 6)
    # ---------------- contents
    C["battery_3000mAh"] = box(-35.5, 34.5, -20.5, 30.5, 2.6, 10.6)
    C["charger_tp4056"] = box(-45, -17, -40.0, -24.0, 3.5, 8.5)
    C["buck_tps63020"] = box(-15, 7, -40.0, -24.0, 3.5, 8.5)
    C["gauge_max17048"] = box(9, 29, -40.0, -24.0, 3.5, 6.5)
    C["sos_button"] = cyl(sx, sy, LID_IN - 17.0, 17.0, 24.0)
    C["gx12_socket"] = cyl_x(-14.0, 14.0, XI - 14.0, 14.0, 13.0)
    C["toggle"] = cyl_y(40.0, 16.0, YI - 14.0, 14.0, 7.0)
    C["pogo_socket"] = box(30.5, 45.5, -YI - 3.0, -YI + 7.0, 5.5, 10.5)
    return {"core_base": b, "core_lid": l}, C


# ================================================================== WRIST CUFF
def cuff():
    L, Wd, R = 88.0, 62.0, 8.0
    ZB, LID_IN, ZT = 21.0, 21.0, 23.5
    b, cut = shell_pod(L, Wd, ZB, R, concave=("cyl_x", 40.0, 6.0))
    # board: X = -39 + v, Y = u - 23 (rotation 90 deg), bottom at z 13.2 so the MAX30102 sensor sits in the floor window
    C, info = board_contents("cuff", ("U1", "U2"), {"U1": (-12.1, -0.5, 23.3, 33, 3.4), "U2": (0, -3, 18.9, 11, 2.5)},
                             xiao=False, rot_z=90, t=(-39.0, -23.0, 13.2))
    holes = [(-39.0 + v, u - 23.0) for u, v in info["holes"]]
    for x, y in holes:
        b = b.union(cyl(x, y, 0, 13.2, 5.0).cut(cut.translate((0, 0, 0.01)))).cut(cyl(x, y, 6, 8, 1.8))
    # MAX30102 skin window (12 x 12) with a 1 mm recess for a clear acrylic disc + light-block foam
    mx, my = -11.0, 0.0
    b = b.cut(box(mx - 6, mx + 6, my - 6, my + 6, -5, 12))                 # through the floor
    b = b.cut(box(mx - 8, mx + 8, my - 8, my + 8, -5, 7.0))                  # 1 mm outside recess, clear acrylic disc
    # coin vibration motor pocket (10 mm) in the floor, under the board edge
    b = b.union(cyl(-30.0, 16.0, 2.0, 9.8, 13.0).cut(cyl(-30.0, 16.0, 6.8, 5, 10.4)).cut(cut.translate((0, 0, 0.01))))
    # cable to the core: GX12 on the elbow end
    b = b.cut(cyl_x(0.0, 14.6, L / 2 - 4, 6, 12.2))
    # strap loops (25 mm webbing around the forearm), two per side
    b = strap_lugs(b, (-24.0, 22.0), Wd / 2, 2.0, 9.0)
    # lid: screen window with bezel, three 16 mm glove buttons, screws
    l = lid_plate(L, Wd, LID_IN, ZT - LID_IN, R)
    wx, wy = -26.0, 0.0
    l = l.cut(box(wx - 8.5, wx + 8.5, wy - 15.5, wy + 15.5, LID_IN - 1, ZT + 1))
    l = l.cut(box(wx - 11, wx + 11, wy - 18.5, wy + 18.5, LID_IN - 0.01, LID_IN + 1.0))     # clear PC window recess
    bez = box(wx - 13.5, wx + 13.5, wy - 21, wy + 21, ZT, ZT + 3.5).edges("|Z").fillet(3).cut(box(wx - 9.5, wx + 9.5, wy - 16.5, wy + 16.5, ZT - 1, ZT + 5))
    l = l.union(bez)
    for i, y in enumerate((-18.0, 0.0, 18.0)):
        l = l.cut(cyl(18.0, y, LID_IN - 1, 5, 16.2))
    l = l.cut(box(36.0, 44.0, -8.0, 8.0, LID_IN - 4, LID_IN))         # skirt notch for the GX12 socket
    # raised ribs between the buttons so one glove press hits one button
    for y in (-9.0, 9.0):
        l = l.union(box(10.0, 26.0, y - 1.2, y + 1.2, ZT, ZT + 3.0))
    corner = [(-39.5, 26.0), (39.5, 26.0), (-39.5, -26.0), (39.5, -26.0)]
    b = screw_bosses(b, corner, 0, ZB, 5.5, 1.8).cut(cut.translate((0, 0, 0.0)))
    l = lid_screws(l, corner, ZT)
    l = text_on(l, "OK", 31.0, -18.0, ZT, 4.5)
    l = text_on(l, "MENU", 32.0, 0.0, ZT, 3.6)
    l = text_on(l, "SOS", 31.5, 18.0, ZT, 4.5)
    # contents
    C["button_ok"] = cyl(18.0, -18.0, LID_IN - 12, 12, 18)
    C["button_menu"] = cyl(18.0, 0.0, LID_IN - 12, 12, 18)
    C["button_sos"] = cyl(18.0, 18.0, LID_IN - 12, 12, 18)
    C["gx12_socket"] = cyl_x(0.0, 14.6, L / 2 - 2.2 - 14, 14, 12.0)
    C["vib_motor"] = cyl(-30.0, 16.0, 6.8, 3.0, 10.0)
    return {"cuff_base": b, "cuff_lid": l}, C


# ================================================================== HELMET POD
def helmet_pod():
    W, H, R = 62.0, 66.0, 10.0
    ZB, LID_IN, ZT = 28.2, 28.2, 30.7
    b, cut = shell_pod(W, H, ZB, R, concave=("sphere", 115.0, 5.0))
    C, info = board_contents("helmet", ("U2",), {"U2": (0, -14.2, 19.4, 3.6, 3.0)}, t=(-22.0, 26.0, 13.5))
    holes = [(-22.0 + u, 26.0 - v) for u, v in info["holes"]]
    for x, y in holes:
        b = b.union(cyl(x, y, 0, 13.5, 5.0)).cut(cyl(x, y, 6, 9, 1.8))
    for x in (-19.0, 19.0):                       # support posts under the top edge of the board
        b = b.union(cyl(x, 23.0, 0, 13.5, 4.0))
    b = b.cut(cut.translate((0, 0, 0)))           # keep the back curve clean
    corner = [(25.5, 28.0), (-25.5, 28.0), (25.5, -28.0), (-25.5, -28.0)]
    b = screw_bosses(b, corner, 0, ZB, 6.0, 1.8).cut(cut)
    # bottom wall: magnetic pogo charge socket + grommet for the head-harness "worn" switch cable
    b = b.cut(box(4.0, 20.0, -H / 2 - 1, -H / 2 + 3.2, 9.0, 15.0))
    b = b.cut(cyl_y(-14.0, 11.0, -H / 2 - 1, 4, 6.0))
    # strap / cable-tie slots to the helmet's rear clip (plus VHB foam pad on the curved back)
    b = strap_lugs(b, (0.0,), W / 2, 1.0, 8.0, strap=20.0, along="y")
    l = lid_plate(W, H, LID_IN, ZT - LID_IN, R)
    l = lid_screws(l, corner, ZT)
    # speaker grille (28 mm speaker glued in a ring on the lid, over the amplifier)
    spx, spy = 0.0, -12.0
    for rr, n in ((0, 1), (5, 6), (10, 12)):
        for k in range(n):
            a = 2 * math.pi * k / n
            l = l.cut(cyl(spx + rr * math.cos(a), spy + rr * math.sin(a), LID_IN - 1, 5, 2.6))
    l = l.union(cyl(spx, spy, LID_IN - 2.2, 2.2, 32.0).cut(cyl(spx, spy, LID_IN - 3, 4, 28.6)))
    # status LED light pipe
    lx, ly = -22.0 + 7.75, 26.0 - 21.35
    l = l.cut(cyl(lx, ly, LID_IN - 1, 5, 3.2))
    l = text_on(l, "MINESAFE", 0, 18, ZT, 6.5)
    C["battery_600mAh"] = box(-15, 15, -18, 22, 7.6, 12.6)
    C["speaker_28mm"] = cyl(spx, spy, LID_IN - 5.2, 5.0, 28.0)
    C["fpc_antenna"] = box(17.0, 26.0, -12.0, 23.0, LID_IN - 0.3, LID_IN)
    C["pogo_socket"] = box(4.5, 19.5, -H / 2 + 0.5, -H / 2 + 9.5, 9.5, 14.5)
    return {"helmet_base": b, "helmet_lid": l}, C


# ================================================================== BOOT POD
def boot_pod():
    W, H, R = 44.0, 58.0, 8.0
    ZB, LID_IN, ZT = 26.2, 26.2, 28.7
    b, cut = shell_pod(W, H, ZB, R, concave=("cyl_y", 45.0, 4.0))
    C, info = board_contents("boot", ("U2",), {"U2": (0, -8.4, 16.3, 3.6, 2.0)}, t=(-17.0, 21.5, 11.5))
    holes = [(-17.0 + u, 21.5 - v) for u, v in info["holes"]]
    for x, y in holes:
        b = b.union(cyl(x, y, 0, 11.5, 5.0)).cut(cyl(x, y, 5, 8, 1.8))
    for x in (-14.0, 14.0):
        b = b.union(cyl(x, 18.5, 0, 11.5, 4.0))
    b = b.cut(cut)
    corner = [(0.0, 25.3), (0.0, -24.3)]
    b = screw_bosses(b, corner, 0, ZB, 5.5, 1.8).cut(cut)
    # bottom wall: pogo charge socket + FSR cable into the boot (heel insole)
    b = b.cut(box(3.0, 15.4, -H / 2 - 1, -H / 2 + 3.2, 6.0, 11.4))
    b = b.cut(cyl_y(-10.0, 10.0, -H / 2 - 1, 4, 4.5))
    # 20 mm strap loops on both sides (strap around the ankle above the heel counter)
    b = strap_lugs(b, (6.0,), W / 2, 1.0, 9.0, strap=20.0, along="y")
    l = lid_plate(W, H, LID_IN, ZT - LID_IN, R)
    l = lid_screws(l, corner, ZT)
    lx, ly = -17.0 + 25.35, 21.5 - 23.8
    l = l.cut(cyl(lx, ly, LID_IN - 1, 5, 3.2))
    l = l.cut(box(-W / 2 + 5, W / 2 - 5, -H / 2 + 8, -H / 2 + 16, ZT - 0.6, ZT + 1))     # reflective tape
    l = text_on(l, "MS", 0, 8, ZT, 7)
    C["battery_300mAh"] = box(-10, 10, -12, 18, 6.6, 10.6)
    C["pogo_socket"] = box(3.2, 15.2, -H / 2 + 0.5, -H / 2 + 7.5, 6.2, 11.2)
    return {"boot_base": b, "boot_lid": l}, C


POD_FUNCS = {"core": core_pod, "cuff": cuff, "helmet": helmet_pod, "boot": boot_pod}
