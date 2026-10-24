"""MineSafe V4 smart suit — full system CAD.

Builds the four pod enclosures (pods.py) with their real PCBs inside, then places them on a 1.75 m mannequin
wearing the FR coverall: helmet pod on the helmet, core pod on the chest, wrist cuff on the left forearm,
boot pod on the right heel, plus the sleeve cable, the tear-detection thread in the seams, the zip reed switch,
skin pad / skin-temperature probe, helmet-worn switch and heel force sensor.

World frame: Z up, the worker faces -Y, worker's LEFT = +X.   Run: python3 build_suit.py
Outputs (hardware/suit_cad/):  pods/<pod>_base|lid.step/.stl · suit_assembly.step · fit_report.txt · renders/
"""
import json
import math
import os
import time

import cadquery as cq

import pods

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PODS = os.path.join(HERE, "pods")
OUT_R = os.path.join(HERE, "renders", "stl")
os.makedirs(OUT_PODS, exist_ok=True)
os.makedirs(OUT_R, exist_ok=True)


# ------------------------------------------------------------------ vector helpers
def norm(v):
    l = math.sqrt(sum(c * c for c in v))
    return tuple(c / l for c in v)


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x * k for x in a)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def to_frame(shape, origin, X, Y, Z):
    """move a part built in its own frame (X, Y, Z axes) to world axes X, Y, Z at origin"""
    from OCP.gp import gp_Ax3, gp_Pnt, gp_Dir, gp_Trsf
    t = gp_Trsf()
    t.SetDisplacement(gp_Ax3(), gp_Ax3(gp_Pnt(*origin), gp_Dir(*Z), gp_Dir(*X)))
    return cq.Workplane(obj=shape.val().moved(cq.Location(t)))


def frustum(p0, p1, r0, r1):
    d = sub(p1, p0)
    h = math.sqrt(dot(d, d))
    if abs(r0 - r1) < 1e-6:
        s = cq.Solid.makeCylinder(r0, h, cq.Vector(*p0), cq.Vector(*norm(d)))
    else:
        s = cq.Solid.makeCone(r0, r1, h, cq.Vector(*p0), cq.Vector(*norm(d)))
    return cq.Workplane(obj=s)


def ball(p, r):
    return cq.Workplane(obj=cq.Solid.makeSphere(r, cq.Vector(*p), angleDegrees1=-90, angleDegrees2=90))


def tube(points, r):
    out = None
    for a, b in zip(points[:-1], points[1:]):
        seg = frustum(a, b, r, r).union(ball(b, r))
        out = seg if out is None else out.union(seg)
    return out.union(ball(points[0], r))


def ell_ring(z, a, b, h, t):
    o = cq.Workplane("XY").workplane(offset=z).ellipse(a + t, b + t).extrude(h)
    return o.cut(cq.Workplane("XY").workplane(offset=z - 1).ellipse(a - 1, b - 1).extrude(h + 2))


# ------------------------------------------------------------------ mannequin + coverall
TORSO = [(880, 175, 118), (1000, 168, 112), (1150, 158, 106), (1300, 182, 116), (1420, 200, 114), (1480, 188, 100)]


def torso_b(z):
    for (z0, _, b0), (z1, _, b1) in zip(TORSO[:-1], TORSO[1:]):
        if z0 <= z <= z1:
            return b0 + (b1 - b0) * (z - z0) / (z1 - z0)
    return TORSO[-1][2]


def torso_a(z):
    for (z0, a0, _), (z1, a1, _) in zip(TORSO[:-1], TORSO[1:]):
        if z0 <= z <= z1:
            return a0 + (a1 - a0) * (z - z0) / (z1 - z0)
    return TORSO[-1][1]


SH = {s: (s * 205, 0, 1440) for s in (-1, 1)}
EL = {s: (s * 250, 10, 1170) for s in (-1, 1)}
WR = {s: (s * 270, -50, 930) for s in (-1, 1)}
HIP = {s: (s * 95, 0, 900) for s in (-1, 1)}
KN = {s: (s * 105, 15, 500) for s in (-1, 1)}
AN = {s: (s * 110, 20, 120) for s in (-1, 1)}
HELMET_C, HELMET_R = (0, 5, 1660), 128.0


def mannequin():
    P = {}
    wp = cq.Workplane("XY").workplane(offset=TORSO[0][0]).ellipse(TORSO[0][1], TORSO[0][2])
    for z, a, b in TORSO[1:]:
        wp = wp.workplane(offset=z - (wp.plane.origin.z)).ellipse(a, b)
    P["coverall_torso"] = wp.loft(ruled=False)
    cov = []
    for s in (-1, 1):
        cov += [ball(SH[s], 68), frustum(SH[s], EL[s], 64, 54), ball(EL[s], 54), frustum(EL[s], WR[s], 52, 42),
                frustum(HIP[s], KN[s], 98, 78), ball(KN[s], 78), frustum(KN[s], AN[s], 76, 66)]
    cov.append(cq.Workplane("XY").workplane(offset=860).ellipse(178, 120).extrude(60))   # seat / crotch fill
    c = cov[0]
    for q in cov[1:]:
        c = c.union(q)
    P["coverall_limbs"] = c
    P["collar"] = ell_ring(1470, 120, 92, 40, 8)
    P["skin"] = frustum((0, 0, 1470), (0, 0, 1570), 55, 52).union(ball((0, 4, 1645), 92))
    gl = None
    for s in (-1, 1):
        g = ball(add(WR[s], (s * 6, -12, -40)), 46)
        gl = g if gl is None else gl.union(g)
    P["gloves"] = gl
    boots = None
    for s in (-1, 1):
        x = s * 110
        bt = cq.Workplane("XY").box(124, 300, 125).translate((x, -40, 62.5)).edges("|Z").fillet(40).edges(">Z or <Z").fillet(12)
        boots = bt if boots is None else boots.union(bt)
    P["boots"] = boots
    # high-vis reflective bands (FR coverall): chest, upper arms, lower legs
    bands = ell_ring(1240, torso_a(1240), torso_b(1240), 50, 3)
    for s in (-1, 1):
        for p0, p1, r0, r1, f in ((SH[s], EL[s], 64, 54, 0.55), (KN[s], AN[s], 76, 66, 0.45), (KN[s], AN[s], 76, 66, 0.7)):
            d = norm(sub(p1, p0))
            c0 = add(p0, mul(sub(p1, p0), f))
            r = r0 + (r1 - r0) * f
            ring = frustum(c0, add(c0, mul(d, 45)), r + 3, r + 2.6).cut(frustum(add(c0, mul(d, -1)), add(c0, mul(d, 47)), r - 2, r - 2))
            bands = bands.union(ring)
    P["reflective_bands"] = bands
    # helmet: shell, brim, peak, cap-lamp bracket
    hc = HELMET_C
    shell = ball(hc, HELMET_R).cut(cq.Workplane("XY").box(600, 600, 600).translate((hc[0], hc[1], hc[2] - 320)))
    shell = shell.union(cq.Workplane("XY").workplane(offset=hc[2] - 22).center(hc[0], hc[1]).ellipse(150, 158).extrude(6))
    shell = shell.union(cq.Workplane("XY").box(130, 60, 8).translate((0, hc[1] - 160, hc[2] - 19)).edges("|Z").fillet(25))
    shell = shell.union(cq.Workplane("XY").box(50, 22, 50).translate((0, hc[1] - 126, hc[2] + 22)).edges("|Y").fillet(6))
    P["helmet"] = shell
    P["cap_lamp"] = cq.Workplane("XZ", origin=(0, hc[1] - 137, 0)).center(0, hc[2] + 22).circle(20).extrude(18)
    return P


# ------------------------------------------------------------------ pods on the body
def frames():
    F = {}
    # core pod: chest, pod +Z -> -Y (forward), +Y -> +Z, +X -> +X (worker's left)
    zc = 1330.0
    F["core"] = ((0.0, -torso_b(zc) - 6.5, zc), (1, 0, 0), (0, 0, 1), (0, -1, 0))
    # wrist cuff: left forearm, X along the arm towards the elbow, display facing forward/outward
    s = 1
    X = norm(sub(EL[s], WR[s]))
    n0 = norm((0.35, -1.0, 0.0))
    Z = norm(sub(n0, mul(X, dot(n0, X))))
    Y = cross(Z, X)
    P = add(EL[s], mul(sub(WR[s], EL[s]), 0.55))
    rr = 52 + (42 - 52) * 0.55
    F["cuff"] = (add(P, mul(Z, rr - 6.0)), X, Y, Z)
    # helmet pod: back of the helmet, 20 deg above the centre line
    d = (0.0, math.cos(math.radians(20)), math.sin(math.radians(20)))
    Yh = (0.0, -d[2], d[1])
    F["helmet"] = (add(HELMET_C, mul(d, HELMET_R - 5.0)), cross(Yh, d), Yh, d)
    # boot pod: right heel counter, facing backwards (+Y)
    F["boot"] = ((-110.0, 110.0 - 4.0 + 0.5, 72.0), (-1, 0, 0), (0, 0, 1), (0, 1, 0))
    return F


def system_wiring(F, cuff_end, core_gx):
    W = {}
    # sleeve cable core GX12 -> armpit -> inside of the left arm -> cuff GX12 (runs inside the sleeve)
    W["sleeve_cable"] = tube([core_gx, add(core_gx, (25, 0, 0)), (178, -95, 1345), (212, -45, 1300), (236, -20, 1200),
                              (252, -12, 1130), cuff_end], 4.0)
    # tear-detection loop: stainless conductive thread in the seams (side seams, shoulders, waist, leg outer seams)
    pts_l = [(0, -torso_b(1290) - 1, 1290), (torso_a(1290) * 0.55, -torso_b(1290) * 0.85, 1290), (torso_a(1300) + 1, 0, 1300),
             (torso_a(1420) + 1, 0, 1420), (150, 0, 1478), (70, 0, 1500)]
    pts_r = [(-x, y, z) for x, y, z in pts_l]
    side_l = [(torso_a(1300) + 1, 0, 1300), (torso_a(1150) + 1, 0, 1150), (torso_a(1000) + 1, 0, 1000), (178, 0, 905),
              (95 + 96, 15, 700), (105 + 79, 15, 500), (110 + 69, 20, 200)]
    side_r = [(-x, y, z) for x, y, z in side_l]
    W["tear_thread"] = tube(pts_l, 2.2).union(tube(pts_r, 2.2)).union(tube(side_l, 2.2)).union(tube(side_r, 2.2)) \
        .union(ell_ring(1000, torso_a(1000), torso_b(1000), 4, 1.5))
    # front zip, reed switch at the top (magnet in the zip puller)
    zp = [(0, -torso_b(z) - 1.5, z) for z in (1478, 1420, 1300, 1150, 1000, 905)]
    W["zip"] = tube(zp, 3.5)
    W["reed_switch"] = cq.Workplane("XY").box(10, 6, 22).translate((14, -torso_b(1460) - 3, 1460))
    W["zip_magnet"] = cq.Workplane("XY").box(9, 6, 14).translate((0, -torso_b(1468) - 6, 1468))
    # inside the lining: skin-contact pad + skin-temperature probe (under the arm), shown in the x-ray view
    W["skin_pad"] = cq.Workplane("XZ", origin=(0, -torso_b(1390) + 32, 0)).center(-70, 1390).circle(22).extrude(1.5)
    W["skin_temp_probe"] = frustum((-torso_a(1360) + 6, -30, 1360), (-torso_a(1360) + 6, 10, 1360), 4, 4)
    W["helmet_worn_switch"] = cq.Workplane("XY").box(14, 8, 8).translate((0, HELMET_C[1], HELMET_C[2] + HELMET_R - 26))
    W["heel_fsr"] = cq.Workplane("XY").workplane(offset=14).center(-110, 70).circle(9).extrude(1.0)
    return W


def export_stl(shape, name, tol=0.2):
    cq.exporters.export(shape, os.path.join(OUT_R, name + ".stl"), tolerance=tol, angularTolerance=0.3)


def main():
    t0 = time.time()
    report = []
    F = frames()
    asm = cq.Assembly(name="minesafe_v4_suit")
    COL = {"base": (0.17, 0.19, 0.2), "lid": (0.95, 0.66, 0.0)}
    manifest = {"items": [], "pods": {}}

    def add_item(shape, name, color, group, opacity=1.0, tol=0.2):
        export_stl(shape, name, tol)
        manifest["items"].append({"name": name, "color": color, "group": group, "opacity": opacity})

    pod_world = {}
    for name, fn in pods.POD_FUNCS.items():
        parts, contents = fn()
        # fit check
        bad = []
        for cn, c in contents.items():
            for pn, p in parts.items():
                try:
                    v = c.intersect(p).val().Volume()
                except Exception:
                    v = 0.0
                if v > 0.5:
                    bad.append(f"{cn} x {pn} {v:.1f} mm3")
        bb = parts[f"{name}_base"].union(parts[f"{name}_lid"]).val().BoundingBox()
        report.append(f"{name:7s} pod {bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f} mm  " + ("fit OK" if not bad else "CLASH " + "; ".join(bad)))
        for pn, p in parts.items():
            cq.exporters.export(p, os.path.join(OUT_PODS, pn + ".step"))
            cq.exporters.export(p, os.path.join(OUT_PODS, pn + ".stl"), tolerance=0.05, angularTolerance=0.2)
        # pod-frame STLs for the close-up renders
        pm = {"parts": [], "contents": []}
        for pn, p in parts.items():
            export_stl(p, "pod_" + pn, 0.05)
            pm["parts"].append(pn)
        for cn, c in contents.items():
            export_stl(c, "pod_" + name + "__" + cn, 0.1)
            pm["contents"].append(cn)
        manifest["pods"][name] = pm
        # world placement
        o, X, Y, Z = F[name]
        for pn, p in parts.items():
            wpart = to_frame(p, o, X, Y, Z)
            col = "#2b3034" if pn.endswith("base") else "#F2A900"
            add_item(wpart, "w_" + pn, col, "pods")
            asm.add(wpart, name=pn, color=cq.Color(*(COL["base"] if pn.endswith("base") else COL["lid"])))
        inner = None
        for cn, c in contents.items():
            inner = c if inner is None else inner.union(c)
        wi = to_frame(inner, o, X, Y, Z)
        add_item(wi, "w_" + name + "_inside", "#1d6b3a", "inside")
        asm.add(wi, name=name + "_electronics", color=cq.Color(0.11, 0.42, 0.23))
        pod_world[name] = (o, X, Y, Z)

    # body
    M = mannequin()
    colors = {"coverall_torso": "#24456b", "coverall_limbs": "#24456b", "collar": "#1b3554", "skin": "#c68642", "gloves": "#d8b25a",
              "boots": "#1b1b1b", "reflective_bands": "#d9dde0", "helmet": "#f4f1e6", "cap_lamp": "#555a5e"}
    for n, s in M.items():
        add_item(s, n, colors[n], "body", tol=0.8)
        c = colors[n].lstrip("#")
        asm.add(s, name=n, color=cq.Color(*(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))))

    def world(pod, p):
        o, X, Y, Z = pod_world[pod]
        return add(o, add(mul(X, p[0]), add(mul(Y, p[1]), mul(Z, p[2]))))
    core_gx = world("core", (116 / 2 + 1.5, -14.0, 14.0))
    cuff_end = world("cuff", (88 / 2 + 6, 0.0, 14.6))
    Wr = system_wiring(F, cuff_end, core_gx)
    wcol = {"sleeve_cable": "#3a3f44", "tear_thread": "#c0c6cc", "zip": "#111111", "reed_switch": "#e8710a", "zip_magnet": "#9aa0a6",
            "skin_pad": "#b87333", "skin_temp_probe": "#b87333", "helmet_worn_switch": "#e8710a", "heel_fsr": "#e8710a"}
    for n, s in Wr.items():
        add_item(s, n, wcol[n], "wiring" if n in ("sleeve_cable", "tear_thread", "zip") else "sensors", tol=0.3)
        c = wcol[n].lstrip("#")
        asm.add(s, name=n, color=cq.Color(*(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))))

    # callout anchors for the renders
    manifest["anchors"] = {
        "helmet": list(world("helmet", (0, 0, 30))), "core": list(world("core", (0, 0, 31))),
        "sos": list(world("core", (36, 8, 36))), "cuff": list(world("cuff", (-26, 0, 24))),
        "boot": list(world("boot", (0, 0, 29))), "sleeve": [212, -45, 1300], "tear": [torso_a(1150) + 2, 0, 1150],
        "zip": [14, -torso_b(1460) - 6, 1460], "skinpad": [-70, -torso_b(1390), 1390],
        "probe": [-torso_a(1360), -10, 1360], "worn": [0, HELMET_C[1], HELMET_C[2] + HELMET_R - 26], "fsr": [-110, 70, 15],
        "lamp": [0, HELMET_C[1] - 150, HELMET_C[2] + 22]}
    json.dump(manifest, open(os.path.join(HERE, "renders", "manifest.json"), "w"), indent=1)
    asm.save(os.path.join(HERE, "suit_assembly.step"))
    open(os.path.join(HERE, "fit_report.txt"), "w").write("\n".join(report) + "\n")
    print("\n".join(report))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
