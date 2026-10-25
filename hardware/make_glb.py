"""Export the MineSafe CAD as coloured glTF-binary (.glb) models for PowerPoint (Insert > 3D Models) and the web.

glTF is Y-up, metres; we keep millimetres (PowerPoint rescales on insert) and turn the parts so
"up" = +Y and the front faces +Z (towards the viewer).
Run after build_case.py / build_suit.py:  python3 hardware/make_glb.py  ->  hardware/glb/*.glb
"""
import os
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "glb")
os.makedirs(OUT, exist_ok=True)
RC = os.path.join(HERE, "repeater_case")
SC = os.path.join(HERE, "suit_cad", "renders", "stl")

COL = {"base": "#2b3034", "lid": "#F2A900", "pcb": "#1d6b3a", "parts": "#9aa79f", "modules": "#2f5f9e", "xiao": "#151515",
       "battery": "#2a4fb0", "matrix": "#b0201b", "window": "#9fd3ff", "sensor": "#4a6fa5", "button": "#d93025", "metal": "#9aa0a6",
       "charger": "#3c8c6a", "speaker": "#333333", "antenna": "#c9a24a", "coverall": "#24456b", "skin": "#c68642", "glove": "#d8b25a",
       "boot": "#1b1b1b", "band": "#d9dde0", "helmet": "#f4f1e6", "thread": "#c0c6cc", "orange": "#e8710a"}

# Z-up, front -Y  ->  Y-up, front +Z   (rotate -90 deg about X)
ZUP_TO_YUP = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])


def mesh(path, colour, alpha=1.0, transform=None, offset=None):
    m = trimesh.load_mesh(path)
    if transform is not None:
        m.apply_transform(transform)
    if offset is not None:
        m.apply_translation(offset)
    h = colour.lstrip("#")
    rgba = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [alpha]
    m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        baseColorFactor=rgba, metallicFactor=0.05, roughnessFactor=0.6, alphaMode="BLEND" if alpha < 1 else "OPAQUE"))
    return m


VIEW = {"repeater_case": (12, -28), "repeater_inside": (12, -20), "smart_suit": (5, -25),
        "pod_core": (22, -25), "pod_cuff": (22, -25), "pod_helmet": (22, -25), "pod_boot": (22, -25)}


def save(name, parts):
    """the 3/4 viewing angle is baked into the geometry (yaw about Y, then tilt about X), so the model opens in
    PowerPoint at a good angle with rotation 0 and 'Reset 3D model' keeps it"""
    ax, ay = VIEW.get(name, (0, 0))
    Ry = trimesh.transformations.rotation_matrix(np.radians(ay), [0, 1, 0])
    Rx = trimesh.transformations.rotation_matrix(np.radians(ax), [1, 0, 0])
    for _, m in parts:
        m.apply_transform(Ry)
        m.apply_transform(Rx)
    sc = trimesh.Scene()
    for i, (n, m) in enumerate(parts):
        sc.add_geometry(m, node_name=n, geom_name=f"{n}_{i}")
    path = os.path.join(OUT, name + ".glb")
    sc.export(path)
    print(f"{name}.glb  {os.path.getsize(path) / 1e6:.2f} MB  extents {np.round(sc.extents, 1)} mm")


def repeater():
    t = ZUP_TO_YUP
    closed = [("base", mesh(f"{RC}/case_base.stl", COL["base"], transform=t)), ("lid", mesh(f"{RC}/case_lid.stl", COL["lid"], transform=t))]
    save("repeater_case", closed)
    inside = [("base", mesh(f"{RC}/case_base.stl", COL["base"], transform=t))]
    cmap = {"pcb": "pcb", "pcb_parts": "parts", "xiao_usb_plug": "xiao", "matrix": "matrix", "window_pc": "window", "mq4_ch4": "sensor",
            "mq7_co": "sensor", "mq136_h2s": "sensor", "aht20": "band", "battery_3s": "battery", "charger_bms": "charger",
            "sos_button_body": "button", "buzzer": "speaker", "gland_nut": "metal", "vent_nut": "metal"}
    # lid parts (matrix, window, SOS, buzzer) left out of the "inside" view, they hang on the lid
    for n, c in cmap.items():
        if n in ("matrix", "window_pc", "sos_button_body", "buzzer"):
            continue
        inside.append((n, mesh(f"{RC}/renders/stl/{n}.stl", COL[c], transform=t)))
    save("repeater_inside", inside)


def pod(name, lift, up=0.0):
    """pod frame is already Y-up with Z out of the lid: lid lifted along +Z (exploded)"""
    parts = [(f"{name}_base", mesh(f"{SC}/pod_{name}_base.stl", COL["base"])),
             (f"{name}_lid", mesh(f"{SC}/pod_{name}_lid.stl", COL["lid"], offset=(0, up, lift)))]
    for f in sorted(os.listdir(SC)):
        if f.startswith(f"pod_{name}__"):
            n = f[len(f"pod_{name}__"):-4]
            key = next((k for k in ("pcb", "parts", "modules", "xiao", "battery", "button", "sos", "speaker", "antenna", "gx12", "toggle",
                                    "pogo", "charger", "buck", "gauge", "vib") if k in n), "parts")
            c = {"sos": "button", "gx12": "metal", "toggle": "metal", "pogo": "antenna", "buck": "charger", "gauge": "charger", "vib": "metal"}.get(key, key)
            parts.append((n, mesh(f"{SC}/{f}", COL[c])))
    save(f"pod_{name}", parts)


def suit():
    t = ZUP_TO_YUP
    cmap = {"coverall_torso": "coverall", "coverall_limbs": "coverall", "collar": "coverall", "skin": "skin", "gloves": "glove",
            "boots": "boot", "reflective_bands": "band", "helmet": "helmet", "cap_lamp": "metal", "sleeve_cable": "speaker",
            "tear_thread": "thread", "zip": "boot", "reed_switch": "orange", "zip_magnet": "metal"}
    parts = [(n, mesh(f"{SC}/{n}.stl", COL[c], transform=t)) for n, c in cmap.items() if os.path.exists(f"{SC}/{n}.stl")]
    for p in ("core", "cuff", "helmet", "boot"):
        parts.append((f"{p}_base", mesh(f"{SC}/w_{p}_base.stl", COL["base"], transform=t)))
        parts.append((f"{p}_lid", mesh(f"{SC}/w_{p}_lid.stl", COL["lid"], transform=t)))
    save("smart_suit", parts)


if __name__ == "__main__":
    repeater()
    for n, lift, up in (("core", 45, 80), ("cuff", 35, 66), ("helmet", 40, 60), ("boot", 36, 54)):
        pod(n, lift, up)       # lid lifted up and forward, so the inside shows from the front
    suit()
