"""Replace picture placeholders named M3D_<model> with native PowerPoint 3D models (.glb, Insert > 3D Models).

Each placeholder picture becomes mc:AlternateContent:
  Choice  (PowerPoint 2019 / 365): p:graphicFrame > a:graphicData[model3d] > am3d:model3d  -> rotatable model
  Fallback (older viewers, LibreOffice, Google Slides): the original picture (a render of the same model)
Structure, units, lighting rig and camera formula follow PowerPoint's own files, as implemented in OfficeCLI
(Apache-2.0, src/officecli/Handlers/Pptx/PowerPointHandler.Add.Model3D.cs) and [MS-ODRAWXML] 2.31 CT_Model3D.
Usage: python3 add_3d_models.py in.pptx out.pptx
"""
import math
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile

import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
GLB_DIR = os.path.join(HERE, "..", "..", "hardware", "glb")
AM3D = "http://schemas.microsoft.com/office/drawing/2017/model3d"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
REL_MODEL = "http://schemas.microsoft.com/office/2017/06/relationships/model3d"
CT_GLB = "model/gltf.binary"           # PowerPoint writes a dot, not a dash


def bounds(glb):
    sc = trimesh.load(glb, force="scene")
    lo, hi = sc.bounds
    c = (lo + hi) / 2
    e = hi - lo
    return c, e


def model_xml(shape_id, name, model_rid, img_rid, x, y, cx, cy, c, e, fallback_pic):
    max_ext = max(e)
    mpu = 1.0 / max_ext if max_ext > 0 else 0.5
    half = e / 2
    max_half = max(half)
    norm = 1.0 / (2.0 * max_half) if max_half > 0 else 0.5
    radius = norm * math.sqrt(sum(h * h for h in half)) or 1.0
    fov = 2700000                                   # 45 degrees in 60000ths
    cam_z = int(radius / math.sin(math.radians(fov / 60000.0) / 2) * 36000000)
    pre = mpu * 36000000.0
    vp = max(cx, cy)
    guid = "{" + str(uuid.uuid4()).upper() + "}"
    lights = "".join(
        f'<am3d:ptLight rad="0"><am3d:clr><a:scrgbClr r="{r}" g="{g}" b="{b}"/></am3d:clr><am3d:intensity n="{i}" d="1000000"/>'
        f'<am3d:pos x="{px}" y="{py}" z="{pz}"/></am3d:ptLight>'
        for r, g, b, i, px, py, pz in (("100000", "75000", "50000", "9765625", "21959998", "70920001", "16344003"),
                                       ("40000", "60000", "95000", "12250000", "-37964106", "51130435", "57631972"),
                                       ("86837", "72700", "100000", "3125000", "-37739122", "58056624", "-34769649")))
    return (
        f'<mc:AlternateContent xmlns:mc="{MC}">'
        f'<mc:Choice xmlns:am3d="{AM3D}" Requires="am3d">'
        f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{shape_id}" name="{name}" descr="3D model: {name} - drag to rotate">'
        f'<a:extLst><a:ext uri="{{FF2B5EF4-FFF2-40B4-BE49-F238E27FC236}}"><a16:creationId xmlns:a16="http://schemas.microsoft.com/office/drawing/2014/main" id="{guid}"/></a:ext></a:extLst>'
        f'</p:cNvPr><p:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
        f'<p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></p:xfrm>'
        f'<a:graphic><a:graphicData uri="{AM3D}"><am3d:model3d r:embed="{model_rid}">'
        f'<am3d:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></am3d:spPr>'
        f'<am3d:camera><am3d:pos x="0" y="0" z="{cam_z}"/><am3d:up dx="0" dy="36000000" dz="0"/><am3d:lookAt x="0" y="0" z="0"/>'
        f'<am3d:perspective fov="{fov}"/></am3d:camera>'
        f'<am3d:trans><am3d:meterPerModelUnit n="{int(mpu * 1000000)}" d="1000000"/>'
        f'<am3d:preTrans dx="{int(-c[0] * pre)}" dy="{int(-c[1] * pre)}" dz="{int(-c[2] * pre)}"/>'
        f'<am3d:scale><am3d:sx n="1000000" d="1000000"/><am3d:sy n="1000000" d="1000000"/><am3d:sz n="1000000" d="1000000"/></am3d:scale>'
        f'<am3d:rot ax="0" ay="0" az="0"/><am3d:postTrans dx="0" dy="0" dz="0"/></am3d:trans>'
        f'<am3d:raster rName="Office3DRenderer" rVer="16.0.8326"><am3d:blip r:embed="{img_rid}"/></am3d:raster>'
        f'<am3d:objViewport viewportSz="{vp}"/>'
        f'<am3d:ambientLight><am3d:clr><a:scrgbClr r="50000" g="50000" b="50000"/></am3d:clr><am3d:illuminance n="500000" d="1000000"/></am3d:ambientLight>'
        f'{lights}</am3d:model3d></a:graphicData></a:graphic></p:graphicFrame>'
        f'</mc:Choice><mc:Fallback>{fallback_pic}</mc:Fallback></mc:AlternateContent>')


def main(src, dst):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(src) as z:
        z.extractall(tmp)
        order = z.namelist()
    n_models = 0
    sdir = os.path.join(tmp, "ppt", "slides")
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".xml"):
            continue
        sp = os.path.join(sdir, fn)
        xml = open(sp, encoding="utf-8").read()
        if 'name="M3D_' not in xml:
            continue
        rp = os.path.join(sdir, "_rels", fn + ".rels")
        rels = open(rp, encoding="utf-8").read()
        rid_n = max(int(m) for m in re.findall(r'Id="rId(\d+)"', rels)) + 1
        while True:
            m = re.search(r'<p:pic>(?:(?!</p:pic>).)*?name="M3D_([a-z_]+)"(?:(?!</p:pic>).)*?</p:pic>', xml, re.S)
            if not m:
                break
            pic, model = m.group(0), m.group(1)
            shape_id = re.search(r'<p:cNvPr id="(\d+)"', pic).group(1)
            img_rid = re.search(r'r:embed="(rId\d+)"', pic).group(1)
            off = re.search(r'<a:off x="(\d+)" y="(\d+)"/>', pic)
            ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', pic)
            x, y, cx, cy = int(off.group(1)), int(off.group(2)), int(ext.group(1)), int(ext.group(2))
            glb = os.path.join(GLB_DIR, model + ".glb")
            n_models += 1
            media = f"model3d{n_models}.glb"
            shutil.copy(glb, os.path.join(tmp, "ppt", "media", media))
            model_rid = f"rId{rid_n}"
            rid_n += 1
            rels = rels.replace("</Relationships>", f'<Relationship Id="{model_rid}" Type="{REL_MODEL}" Target="../media/{media}"/></Relationships>')
            c, e = bounds(glb)
            name = model.replace("_", " ").title()
            new = model_xml(shape_id, name, model_rid, img_rid, x, y, cx, cy, c, e, pic.replace('name="M3D_', 'name="Render '))
            xml = xml.replace(pic, new, 1)
            print(f"  {fn}: {model} -> {media} ({cx / 914400:.1f} x {cy / 914400:.1f} in)")
        # root: declare mc + am3d and mark am3d ignorable, as PowerPoint does
        root = re.search(r"<p:sld\b[^>]*>", xml).group(0)
        new_root = root
        if "xmlns:mc=" not in new_root:
            new_root = new_root[:-1] + f' xmlns:mc="{MC}">'
        if "xmlns:am3d=" not in new_root:
            new_root = new_root[:-1] + f' xmlns:am3d="{AM3D}">'
        if "mc:Ignorable=" in new_root:
            new_root = re.sub(r'mc:Ignorable="([^"]*)"', lambda mm: f'mc:Ignorable="{mm.group(1)} am3d"' if "am3d" not in mm.group(1) else mm.group(0), new_root)
        else:
            new_root = new_root[:-1] + ' mc:Ignorable="am3d">'
        xml = xml.replace(root, new_root, 1)
        open(sp, "w", encoding="utf-8").write(xml)
        open(rp, "w", encoding="utf-8").write(rels)
    ctp = os.path.join(tmp, "[Content_Types].xml")
    ct = open(ctp, encoding="utf-8").read()
    if 'Extension="glb"' not in ct:
        ct = ct.replace("<Default ", f'<Default Extension="glb" ContentType="{CT_GLB}"/><Default ', 1)
    open(ctp, "w", encoding="utf-8").write(ct)
    # re-zip, [Content_Types].xml first
    if os.path.exists(dst):
        os.remove(dst)
    files = []
    for d, _, fs in os.walk(tmp):
        for f in fs:
            files.append(os.path.relpath(os.path.join(d, f), tmp))
    files.sort(key=lambda f: (f != "[Content_Types].xml", order.index(f) if f in order else 10 ** 6, f))
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(tmp, f), f)
    shutil.rmtree(tmp)
    print(f"{n_models} 3D models embedded -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
