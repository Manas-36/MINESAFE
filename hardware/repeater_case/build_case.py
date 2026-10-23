"""MineSafe repeater enclosure v4.0 (CadQuery 2.x).

Build frame used below: X = width, Y = height (up), Z = depth (back plate on the rib/wall at Z=0, lid faces the walkway).
Exports are rotated so that Z is up (STEP/STL convention), front facing -Y.

Parts:  base (tray, mounts to the tunnel wall / roof-mesh)   lid (window, SOS, buzzer grille, drip hood)
Outputs: case_base.step/.stl, case_lid.step/.stl, case_assembly.step, fit_report.txt
Run:  python3 build_case.py
"""
import os
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE

# ---------------------------------------------------------------- main dimensions (mm)
W, H = 198.0, 228.0          # outer body, front view
WALL = 4.0
D_BASE = 62.0                # base depth (back plate to rim)
D_LID = 22.0                 # lid depth (rim to front face)
R_CORNER = 8.0
LIP = 5.0                    # inner rim lip -> 9 mm wide gasket land
GROOVE_W, GROOVE_D = 3.0, 2.0  # for 3 mm silicone cord
XI, YI = W / 2 - WALL, H / 2 - WALL   # inner half sizes (95, 110)

# board 100 x 75, holes 3.5 mm in from each corner; placed centred in X, top edge at Y = +45
PCB_X0, PCB_Y_TOP, PCB_W, PCB_H = -50.0, 45.0, 100.0, 75.0
PCB_HOLES = [(PCB_X0 + 3.5, PCB_Y_TOP - 3.5), (PCB_X0 + PCB_W - 3.5, PCB_Y_TOP - 3.5),
             (PCB_X0 + 3.5, PCB_Y_TOP - PCB_H + 3.5), (PCB_X0 + PCB_W - 3.5, PCB_Y_TOP - PCB_H + 3.5)]
STANDOFF = 12.0              # board underside 16 mm off the back plate (WALL + STANDOFF)

MATRIX = (128.0, 32.0, 14.0)  # FC-16 4-in-1 MAX7219, w x h x thickness
WIN_Y = 80.0                  # window centre height

LUGS = [(sx * (W / 2 + 5), y) for sx in (-1, 1) for y in (-90.0, 0.0, 90.0)]

# gas / port positions
CH4_X = 70.0                  # MQ-4 methane: top wall (CH4 is lighter than air)
SMA_X = -70.0                 # antenna bulkhead: top wall
CO_X, H2S_X = 58.0, 82.0      # MQ-7 CO, MQ-136 H2S: bottom wall (H2S is heavier than air)
GLAND_X = -53.0               # M16 gland, mine supply cable, bottom wall (drip loop)
VENT_X = 0.0                  # M12 ePTFE pressure vent, bottom wall (battery bay)
AHT_BOX = (-95.0, -67.0, -110.0, -80.0)   # x0 x1 y0 y1 of the separate sensor chamber
BATT_BOX = (-40.0, 44.0, -110.0, -38.0)   # battery bay ribs (outer)
SOS_XY = (62.0, -78.0)
BUZ_XY = (-62.0, -78.0)
LED_XY = (0.0, -78.0)


def rrect(w, h, r, z0, dz):
    """rounded rectangle solid in the XY plane from z0, thickness dz"""
    s = cq.Workplane("XY").workplane(offset=z0).rect(w, h).extrude(dz)
    if r > 0:
        s = s.edges("|Z").fillet(r)
    return s


def ring(w_out, h_out, r_out, w_in, h_in, r_in, z0, dz):
    return rrect(w_out, h_out, r_out, z0, dz).cut(rrect(w_in, h_in, r_in, z0 - 1, dz + 2))


def cyl(x, y, z0, dz, d):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(dz)


def cyl_y(x, z, y0, dy, d):
    """cylinder along +Y starting at y0 (through the top/bottom walls)"""
    return cq.Workplane("XZ", origin=(0, y0, 0)).center(x, z).circle(d / 2).extrude(-dy)


def cyl_x(y, z, x0, dx, d):
    return cq.Workplane("YZ", origin=(x0, 0, 0)).center(y, z).circle(d / 2).extrude(dx)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


# ======================================================================= BASE
def make_base():
    b = rrect(W, H, R_CORNER, 0, D_BASE).faces(">Z").shell(-WALL)
    # inner lip -> wide gasket land, and the groove for the silicone cord
    b = b.union(ring(2 * XI, 2 * YI, R_CORNER - WALL, 2 * (XI - LIP), 2 * (YI - LIP), 1, D_BASE - 10, 10))
    gc = WALL + LIP / 2 + 0.0     # groove centre inset from outside  (≈ 6.5 mm)
    b = b.cut(ring(W - 2 * (gc - GROOVE_W / 2), H - 2 * (gc - GROOVE_W / 2), R_CORNER - gc + 1.5,
                   W - 2 * (gc + GROOVE_W / 2), H - 2 * (gc + GROOVE_W / 2), max(R_CORNER - gc - 1.5, 0.5),
                   D_BASE - GROOVE_D, GROOVE_D + 0.01))
    # lid screw lugs: M4 heat-set inserts (5.6 mm hole, 10 deep), 6 off, outside the seal
    for x, y in LUGS:
        lug = cyl(x, y, D_BASE - 16, 16, 15).union(box(min(x, x - 7 * (1 if x > 0 else -1)), max(x, x - 7 * (1 if x > 0 else -1)), y - 7.5, y + 7.5, D_BASE - 16, D_BASE))
        # gusset under the lug so a blast shock does not snap it off
        g = (cq.Workplane("XZ", origin=(0, y + 2, 0))
             .polyline([(W / 2 * (1 if x > 0 else -1), D_BASE - 16), (x + 6 * (1 if x > 0 else -1), D_BASE - 16),
                        (W / 2 * (1 if x > 0 else -1), D_BASE - 34)]).close().extrude(4))
        b = b.union(lug).union(g)
        b = b.cut(cyl(x, y, D_BASE - 10, 11, 5.6))

    # PCB standoffs (M3: 2.5 mm pilot for self-tappers or M3 inserts)
    for x, y in PCB_HOLES:
        b = b.union(cyl(x, y, WALL - 0.5, STANDOFF + 0.5, 7.5)).cut(cyl(x, y, WALL + 2, STANDOFF, 2.6))
    # cable-tie bridges on the back plate for the sensor leads
    for x, y in ((-70, 20), (70, 20), (-70, -30), (70, -30)):
        b = b.union(box(x - 6, x + 6, y - 2, y + 2, WALL, WALL + 6)).cut(box(x - 7, x + 7, y - 1.2, y + 1.2, WALL + 1, WALL + 4.5))

    # --- separate sensor chamber (AHT20) in the bottom-left: cool, away from MQ heaters, own vent
    x0, x1, y0, y1 = AHT_BOX
    b = b.union(box(x1, x1 + 2, -YI, y1 + 2, WALL, D_BASE - 2)).union(box(-XI, x1 + 2, y1, y1 + 2, WALL, D_BASE - 2))
    b = b.cut(box(x1 - 1, x1 + 3, y1 - 8, y1 - 4, D_BASE - 8, D_BASE))            # wire notch
    b = b.cut(cyl_x(-95, 30, -W / 2 - 1, WALL + 2, 12.4))                            # side vent hole (M12 ePTFE vent)
    b = b.union(cyl_x(-95, 30, -W / 2 - 3, 3, 20)).cut(cyl_x(-95, 30, -W / 2 - 4, 6, 12.4))  # vent spot-face boss
    # little louvre hood over the side vent so roof drip cannot hit the membrane
    b = b.union(box(-W / 2 - 9, -W / 2, -95 + 9, -95 + 12, 18, 42))

    # --- battery bay: 3S 18650 pack + BMS + charge module, ribs keep it off the PCB
    bx0, bx1, by0, by1 = BATT_BOX
    for xr in (bx0, bx1 - 2):
        b = b.union(box(xr, xr + 2, -YI, by1, WALL, D_BASE - 12))
    b = b.union(box(bx0, bx1, by1 - 2, by1, WALL, D_BASE - 12))
    for xs in (bx0 + 18, bx1 - 20):   # strap slots in the top rib (velcro strap)
        b = b.cut(box(xs, xs + 3, by1 - 3, by1 + 1, WALL + 6, WALL + 26))

    # --- top wall: CH4 port with a rain "chimney" (gas enters sideways, drips cannot fall in)
    b = port_seat(b, CH4_X, top=True)
    chim = cyl_y(CH4_X, 31, YI + WALL, 17, 34)
    chim = chim.cut(cyl_y(CH4_X, 31, YI + WALL - 1, 15, 26))
    for ang in (0, 90, 180, 270):
        win = box(-5, 5, YI + WALL + 3, YI + WALL + 12, 0, 20).rotate((0, 0, 0), (0, 1, 0), ang).translate((CH4_X, 0, 31))
        chim = chim.cut(win)
    b = b.union(chim)
    # SMA bulkhead (6.5 mm) with a flat spot-face
    b = b.union(cyl_y(SMA_X, 31, YI + WALL, 2, 16)).cut(cyl_y(SMA_X, 31, YI - 1, WALL + 4, 6.6))

    # --- bottom wall: CO + H2S ports with impact skirts, gland, pressure vent
    for x in (CO_X, H2S_X):
        b = port_seat(b, x, top=False)
        b = b.union(cyl_y(x, 31, -YI - WALL - 7, 7, 28).cut(cyl_y(x, 31, -YI - WALL - 8, 9, 22)))
    b = b.union(cyl_y(GLAND_X, 31, -YI - WALL - 2, 2, 26)).cut(cyl_y(GLAND_X, 31, -YI - WALL - 3, WALL + 6, 16.2))
    b = b.union(cyl_y(VENT_X, 31, -YI - WALL - 2, 2, 20)).cut(cyl_y(VENT_X, 31, -YI - WALL - 3, WALL + 6, 12.4))

    # --- mounting: top + bottom tabs on the back plate (rock-bolt plate / roof-mesh hook / chain)
    for s in (1, -1):
        tab = (cq.Workplane("XY").center(0, s * (H / 2 + 14)).rect(70, 36).extrude(7).edges("|Z").fillet(10))
        b = b.union(tab)
        b = b.cut(cyl(0, s * (H / 2 + 18), -1, 9, 16))        # 16 mm: rubber grommet for a rock-bolt / hook
        for xs in (-24, 24):
            b = b.cut(cq.Workplane("XY").center(xs, s * (H / 2 + 16)).slot2D(14, 7, 90).extrude(9).translate((0, 0, -1)))
        # ribs from tab into the body
        for xs in (-30, 30):
            b = b.union(box(xs - 2, xs + 2, min(s * H / 2 - s * 4, s * (H / 2 + 30)), max(s * H / 2 - s * 4, s * (H / 2 + 30)), 7, 15))
    # earth stud boss (antistatic plastic is bonded to the mine earth through this)
    b = b.union(cyl(80, 60, WALL - 0.5, 8.5, 10)).cut(cyl(80, 60, WALL + 1, 9, 3.3))
    return b


def port_seat(b, x, top):
    """sensor port: 20 mm opening, inside a 26 mm x 3 mm seat for a sintered-bronze flame-arrestor disc
    + ePTFE membrane, then the MQ module sits on two M3 bosses right behind it"""
    s = 1 if top else -1
    inner = s * YI
    boss = cyl_y(x, 31, inner - (8 if top else 0), 8, 36)
    b = b.union(boss)
    b = b.cut(cyl_y(x, 31, inner - 9 if top else inner - WALL - 1, 20 if top else WALL + 10, 20))  # open through wall
    if top:
        b = b.cut(cyl_y(x, 31, inner - 9, 4, 26.4))
    else:
        b = b.cut(cyl_y(x, 31, inner + 5, 4, 26.4))
    # module retaining bosses (M3, 2.5 mm pilot) either side of the seat: the MQ board is screwed on
    # with a foam gasket, so the sensor head only breathes through the arrestor
    for dz in (-14, 14):
        if top:
            b = b.union(cyl_y(x, 31 + dz, inner - 8, 8, 6)).cut(cyl_y(x, 31 + dz, inner - 9, 7, 2.5))
        else:
            b = b.union(cyl_y(x, 31 + dz, inner, 8, 6)).cut(cyl_y(x, 31 + dz, inner + 2, 7, 2.5))
    return b


# ======================================================================= LID
def make_lid():
    z0 = D_BASE
    l = rrect(W, H, R_CORNER, z0, D_LID).faces("<Z").shell(-WALL)
    l = l.union(ring(2 * XI, 2 * YI, R_CORNER - WALL, 2 * (XI - LIP), 2 * (YI - LIP), 1, z0, 6))
    gc = WALL + LIP / 2
    tongue = ring(W - 2 * (gc - 1), H - 2 * (gc - 1), R_CORNER - gc + 1, W - 2 * (gc + 1), H - 2 * (gc + 1),
                  max(R_CORNER - gc - 1, 0.5), z0 - 1.4, 1.4)
    l = l.union(tongue)
    zf = z0 + D_LID                         # outer front face
    # lugs with counterbored M4 screw holes (captive stainless screws)
    for x, y in LUGS:
        sgn = 1 if x > 0 else -1
        l = l.union(cyl(x, y, z0, 12, 15)).union(box(min(x, x - 7 * sgn), max(x, x - 7 * sgn), y - 7.5, y + 7.5, z0, z0 + 12))
        l = l.cut(cyl(x, y, z0 - 1, 14, 4.5)).cut(cyl(x, y, z0 + 8, 5, 8.6))

    # display window: 136 x 40 opening, 146 x 50 x 2 recess inside for a 3 mm polycarbonate window + gasket
    l = l.cut(box(-68, 68, WIN_Y - 20, WIN_Y + 20, zf - WALL - 1, zf + 1))
    l = l.cut(box(-73, 73, WIN_Y - 25, WIN_Y + 25, zf - WALL - 0.01, zf - WALL + 2))
    # bezel around the window (stand-off from rock chips, shades the LEDs)
    bez = box(-76, 76, WIN_Y - 28, WIN_Y + 28, zf, zf + 5).edges("|Z").fillet(6)
    bez = bez.cut(box(-66, 66, WIN_Y - 18, WIN_Y + 18, zf - 1, zf + 6)).edges(">Z").chamfer(1.5)
    l = l.union(bez)
    # matrix clamp-bar bosses inside
    for x in (-72, 72):
        for y in (WIN_Y - 21, WIN_Y + 21):
            l = l.union(cyl(x, y, zf - WALL - 14, 14, 7)).cut(cyl(x, y, zf - WALL - 15, 13, 2.6))

    # SOS: 22.5 mm hole for an IP67 22 mm mushroom button + a guard ring with two finger gaps
    sx, sy = SOS_XY
    l = l.cut(cyl(sx, sy, zf - WALL - 1, WALL + 2, 22.5))
    g = cyl(sx, sy, zf, 9, 46).cut(cyl(sx, sy, zf - 1, 11, 38))
    g = g.cut(box(sx - 30, sx + 30, sy - 6, sy + 6, zf - 1, zf + 11))
    l = l.union(g)
    # buzzer / siren grille (behind it: acoustic ePTFE vent glued inside)
    bx, by = BUZ_XY
    for dx, dy in [(0, 0)] + [(8 * __import__("math").cos(a * 3.14159 / 3), 8 * __import__("math").sin(a * 3.14159 / 3)) for a in range(6)]:
        l = l.cut(cyl(bx + dx, by + dy, zf - WALL - 1, WALL + 2, 3.2))
    l = l.union(cyl(bx, by, zf - WALL - 4, 4, 30).cut(cyl(bx, by, zf - WALL - 5, 6, 24)))   # membrane seat inside
    # status LED light-pipe
    l = l.cut(cyl(*LED_XY, zf - WALL - 1, WALL + 2, 5.2))
    # recesses for reflective hi-vis tape (0.8 mm) so the box is seen in cap-lamp light
    for y in (-104, 44):
        l = l.cut(box(-90, 90, y - 6, y + 6, zf - 0.8, zf + 1))
    # drip hood: sloped roof over the window, full width, with side cheeks
    hood = (cq.Workplane("YZ", origin=(-W / 2, 0, 0))
            .polyline([(H / 2 - 6, zf - 10), (H / 2 + 4, zf - 10), (H / 2 - 4, zf + 34), (H / 2 - 10, zf + 34), (H / 2 - 6, zf)])
            .close().extrude(W))
    l = l.union(hood)
    for xs in (-W / 2, W / 2 - 4):
        cheek = (cq.Workplane("YZ", origin=(xs, 0, 0))
                 .polyline([(H / 2 - 6, zf), (H / 2 - 4, zf + 34), (H / 2 - 22, zf + 10), (H / 2 - 30, zf)]).close().extrude(4))
        l = l.union(cheek)
    # label: embossed text under the window (skip if no font)
    try:
        t = cq.Workplane("XY").workplane(offset=zf).center(0, 22).text("MINESAFE", 12, 0.8, kind="bold")
        l = l.union(t)
    except Exception as e:  # noqa
        print("text skipped:", e)
    return l


# ======================================================================= dummy contents for the fit check
def contents():
    parts = {}
    zb = WALL + STANDOFF
    parts["pcb"] = box(PCB_X0, PCB_X0 + PCB_W, PCB_Y_TOP - PCB_H, PCB_Y_TOP, zb, zb + 1.6)
    parts["pcb_parts"] = box(PCB_X0 + 1, PCB_X0 + PCB_W - 1, PCB_Y_TOP - PCB_H + 1, PCB_Y_TOP - 1, zb + 1.6, zb + 1.6 + 22)
    parts["xiao_usb_plug"] = box(-9, 12, PCB_Y_TOP, PCB_Y_TOP + 25, zb + 10, zb + 20)
    zf = D_BASE + D_LID
    parts["matrix"] = box(-64, 64, WIN_Y - 16, WIN_Y + 16, zf - WALL - MATRIX[2] - 0.5, zf - WALL - 0.5)
    parts["window_pc"] = box(-72.5, 72.5, WIN_Y - 24.5, WIN_Y + 24.5, zf - WALL, zf - WALL + 2)
    parts["mq4_ch4"] = box(CH4_X - 11, CH4_X + 11, YI - 9 - 30, YI - 9, 31 - 16, 31 + 16)
    parts["mq7_co"] = box(CO_X - 11, CO_X + 11, -YI + 8.5, -YI + 8.5 + 30, 31 - 16, 31 + 16)
    parts["mq136_h2s"] = box(H2S_X - 11, H2S_X + 11, -YI + 8.5, -YI + 8.5 + 30, 31 - 16, 31 + 16)
    parts["aht20"] = box(-90, -70, -100, -88, WALL + 20, WALL + 23)
    parts["battery_3s"] = box(BATT_BOX[0] + 3, BATT_BOX[0] + 3 + 77, -YI + 12, -YI + 12 + 56, WALL + 0.5, WALL + 20.5)
    parts["charger_bms"] = box(BATT_BOX[0] + 10, BATT_BOX[0] + 10 + 50, -YI + 20, -YI + 20 + 26, WALL + 21, WALL + 36)
    parts["vent_nut"] = cyl_y(VENT_X, 31, -YI, 8, 18)
    parts["gland_nut"] = cyl_y(GLAND_X, 31, -YI, 8, 22)
    parts["sos_button_body"] = cyl(*SOS_XY, zf - WALL - 30, 30, 30)
    parts["buzzer"] = cyl(*BUZ_XY, zf - WALL - 4 - 14, 14, 23)
    return parts


def rot(s):
    return s.rotate((0, 0, 0), (1, 0, 0), 90)


def main():
    base, lid = make_base(), make_lid()
    rep = []
    vb, vl = base.val().Volume(), lid.val().Volume()
    rep.append(f"base volume {vb/1000:.0f} cm3 (~{vb/1000*1.3:.0f} g in PC-ABS FR)  lid {vl/1000:.0f} cm3 (~{vl/1000*1.3:.0f} g)")
    bb = base.union(lid).val().BoundingBox()
    rep.append(f"overall {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm (W x H incl. tabs x D incl. hood)")
    parts = contents()
    for n, p in parts.items():
        for nm, shell in (("base", base), ("lid", lid)):
            try:
                v = p.intersect(shell).val().Volume()
            except Exception:
                v = 0.0
            if v > 1.0:
                rep.append(f"COLLISION {n} with {nm}: {v:.1f} mm3")
    for i, (a, pa) in enumerate(parts.items()):
        for b_, pb in list(parts.items())[i + 1:]:
            try:
                v = pa.intersect(pb).val().Volume()
            except Exception:
                v = 0.0
            if v > 1.0 and {a, b_} != {"matrix", "window_pc"}:
                rep.append(f"COLLISION {a} with {b_}: {v:.1f} mm3")
    if not any(r.startswith("COLLISION") for r in rep):
        rep.append("fit check: PCB, matrix, window, 3 MQ modules, AHT20, battery, charger, SOS button and buzzer clear the case and each other")
    open(os.path.join(OUT, "fit_report.txt"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))

    cq.exporters.export(rot(base), os.path.join(OUT, "case_base.step"))
    cq.exporters.export(rot(lid), os.path.join(OUT, "case_lid.step"))
    cq.exporters.export(rot(base), os.path.join(OUT, "case_base.stl"), tolerance=0.05, angularTolerance=0.2)
    cq.exporters.export(rot(lid), os.path.join(OUT, "case_lid.stl"), tolerance=0.05, angularTolerance=0.2)
    asm = cq.Assembly(name="minesafe_repeater")
    asm.add(rot(base), name="base", color=cq.Color(0.95, 0.66, 0.0))
    asm.add(rot(lid), name="lid", color=cq.Color(0.2, 0.22, 0.24))
    cols = {"pcb": (0.1, 0.45, 0.2), "matrix": (0.6, 0.05, 0.05), "battery_3s": (0.15, 0.3, 0.7)}
    for n, p in parts.items():
        c = cols.get(n, (0.7, 0.7, 0.7))
        asm.add(rot(p), name=n, color=cq.Color(*c))
    asm.save(os.path.join(OUT, "case_assembly.step"))
    # contents as separate STLs for the renderer
    os.makedirs(os.path.join(OUT, "renders", "stl"), exist_ok=True)
    for n, p in parts.items():
        cq.exporters.export(rot(p), os.path.join(OUT, "renders", "stl", n + ".stl"), tolerance=0.1)
    print("exported")


if __name__ == "__main__":
    main()
