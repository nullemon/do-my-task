"""
Generic blocky (Roblox R6-style) character builder for Blender 4.x (headless).

Builds a 3D character from a 3-view character sheet (FRONT | SIDE facing left | BACK)
by creating box parts whose UVs are *planar projections* of the matching sheet view:
  front faces  <- FRONT view, back faces <- BACK view, +X/-X faces <- SIDE view
  (the -X face automatically comes out mirrored), top/bottom faces <- edge row of FRONT view.
Hair is real 3D geometry (ellipsoid cap + cone spikes).

Usage:
  blender -b -P build_character.py -- <name> [--build] [--previews] [--sprites] [--turntable]
  names: naruto kakashi sasuke obito
EEVEE needs an OpenGL context; on a headless box run under `xvfb-run -a`.
"""
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector, Matrix, Euler
import numpy as np
from PIL import Image

IMG_DIR = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/images"
OUT = "/home/user/do-my-task/skit/3d"
S = 0.002  # metres per sheet pixel

# ---------------------------------------------------------------- character specs
# All numbers are sheet pixel coordinates.
#   cxF / cxB : body centre column in FRONT / BACK view;  cyS : body centre column in SIDE view
#   feet      : row of the soles
#   parts: f=(front col0,col1)  s=(side col0,col1)  r=(row0,row1)
#          fb/sb = front/side cols at the bottom edge (flared skirt)
#          ov = per-face UV overrides: face letter -> mode
#               faces: F front(-Y) B back(+Y) L(+X, char left) R(-X, char right) T top D bottom
#               modes: 'edgeF' stretch the FRONT-view column at that edge across the face
#                      'clean' use the inpainted copy of the SIDE view
CHARS = {
  "naruto": dict(
    sheet="11.webp", cxF=275, cxB=1174, cyS=708.5, feet=976,
    parts={
      "Head":  dict(f=(165, 375), s=(603, 815), r=(215, 402), parent="Torso", pivot="neck"),
      "Torso": dict(f=(150, 400), s=(617, 800), r=(403, 692), parent=None, pivot="hip_center",
                    ov={"L": "edgeF", "R": "edgeF"}),
      "ArmR":  dict(f=(18, 150), s=(619, 800), r=(405, 690), parent="Torso", pivot="shoulder",
                    fuv=((32, 150), (18, 150)), buv=((1300, 1416), (1300, 1431))),
      "ArmL":  dict(f=(400, 532), s=(619, 800), r=(405, 690), parent="Torso", pivot="shoulder",
                    fuv=((400, 512), (400, 528)), buv=((937, 1048), (918, 1048))),
      "LegR":  dict(f=(122, 272), s=(618, 803), r=(690, 976), parent="Torso", pivot="hip"),
      "LegL":  dict(f=(279, 429), s=(618, 803), r=(690, 976), parent="Torso", pivot="hip",
                    ov={"L": "clean"}),
    },
    # inpaint ops for the "clean" SIDE copy: (col0,col1,row0,row1, src_row) copy src_row down the block
    clean=[(610, 810, 700, 840, 862)],
    hair=dict(px=(230, 170), cap=(1.0, 1.02, 58, -12, 8), n=28, length=100, radius=44,
              bias=(0, 0.05, 0.3), front_min=0.5, zmin=-0.3, seed=3),
    extras=[
      dict(name="Pouch", parent="LegR", f=(112, 140), s=(688, 762), r=(712, 832), mat="atlas"),
      dict(name="HeadbandTail1", parent="Head", color_px=(840, 360), size=(24, 12, 165),
           at=(-12, 818, 300), rot=(28, 6, 0)),
      dict(name="HeadbandTail2", parent="Head", color_px=(840, 360), size=(22, 12, 140),
           at=(14, 818, 300), rot=(14, -8, 0)),
    ],
  ),
  "kakashi": dict(
    sheet="9.webp", cxF=307, cxB=1146, cyS=712, feet=967,
    parts={
      "Head":   dict(f=(205, 409), s=(604, 804), r=(228, 388), parent="Torso", pivot="neck"),
      "Collar": dict(f=(206, 407), s=(613, 806), r=(380, 412), parent="Torso", pivot="center"),
      "Torso":  dict(f=(178, 435), s=(614, 810), r=(410, 665), parent=None, pivot="hip_center",
                     ov={"L": "edgeF", "R": "edgeF"}),
      "ArmR":   dict(f=(45, 178), s=(625, 785), r=(415, 705), parent="Torso", pivot="shoulder",
                    fuv=((75, 178), (46, 178)), buv=((1268, 1373), (1268, 1402))),
      "ArmL":   dict(f=(435, 568), s=(625, 785), r=(415, 705), parent="Torso", pivot="shoulder",
                    fuv=((435, 535), (435, 566)), buv=((914, 1013), (881, 1013))),
      "LegR":   dict(f=(161, 305), s=(627, 795), r=(665, 967), parent="Torso", pivot="hip"),
      "LegL":   dict(f=(311, 457), s=(627, 795), r=(665, 967), parent="Torso", pivot="hip"),
    },
    clean=[],
    hair=dict(px=(330, 160), cap=(1.05, 1.08, 50, -8, 12), n=18, length=145, radius=40,
              bias=(0.55, 0.45, 0.55), front_min=0.45, zmin=-0.1, seed=7),
    extras=[
      dict(name="Holster", parent="LegR", f=(150, 178), s=(650, 760), r=(712, 812), mat="atlas"),
      dict(name="HipPouch", parent="Torso", f=(1200, 1280), s=(775, 830), r=(662, 760),
           color_px=(1240, 720), back_f=True),
    ],
  ),
  "sasuke": dict(
    sheet="10.webp", cxF=290, cxB=1172, cyS=715, feet=934,
    parts={
      "Head":   dict(f=(196, 386), s=(615, 812), r=(200, 352), parent="Torso", pivot="neck"),
      "Collar": dict(f=(180, 398), s=(612, 820), r=(343, 395), parent="Torso", pivot="center"),
      "Torso":  dict(f=(178, 405), s=(627, 803), r=(392, 625), parent=None, pivot="hip_center",
                     ov={"L": "edgeF", "R": "edgeF"}),
      "Skirt":  dict(f=(165, 415), s=(615, 815), r=(620, 762), fb=(135, 442), sb=(600, 822),
                     parent="Torso", pivot="center", ov={"L": "edgeF", "R": "edgeF"}),
      "ArmR":   dict(f=(40, 178), s=(645, 800), r=(388, 665), parent="Torso", pivot="shoulder",
                    fuv=((55, 178), (35, 178)), buv=((1295, 1402), (1295, 1422))),
      "ArmL":   dict(f=(405, 540), s=(645, 800), r=(388, 665), parent="Torso", pivot="shoulder",
                    fuv=((405, 519), (405, 539)), buv=((942, 1050), (918, 1050))),
      "LegR":   dict(f=(137, 283), s=(653, 810), r=(640, 934), parent="Torso", pivot="hip"),
      "LegL":   dict(f=(296, 442), s=(653, 810), r=(640, 934), parent="Torso", pivot="hip"),
    },
    clean=[],
    hair=dict(px=(250, 180), cap=(1.08, 1.1, 50, -6, 14), n=20, length=115, radius=38,
              bias=(0, 0.9, 0.1), front_min=0.4, zmin=-0.45, seed=11),
    extras=[
      dict(name="Sword", parent="Torso", color_px=(1200, 600), sword=True),
    ],
  ),
  "obito": dict(
    sheet="8.webp", cxF=295, cxB=1160, cyS=716, feet=969,
    parts={
      "Head":   dict(f=(186, 404), s=(612, 830), r=(205, 362), parent="Torso", pivot="neck",
                     ov={"D": ("px", 200, 385)}),
      "Collar": dict(f=(172, 418), s=(601, 836), r=(348, 402), parent="Torso", pivot="center",
                     ov={"T": ("px", 200, 385)}),
      "Torso":  dict(f=(175, 420), s=(616, 816), r=(398, 650), parent=None, pivot="hip_center",
                     ov={"L": "edgeF", "R": "edgeF"}),
      "Skirt":  dict(f=(162, 428), s=(612, 818), r=(645, 852), fb=(105, 480), sb=(604, 836),
                     parent="Torso", pivot="center", ov={"L": "edgeF", "R": "edgeF"}),
      "ArmR":   dict(f=(22, 172), s=(620, 812), r=(398, 685), parent="Torso", pivot="shoulder",
                    fuv=((54, 172), (20, 172)), buv=((1290, 1400), (1290, 1433))),
      "ArmL":   dict(f=(420, 568), s=(620, 812), r=(398, 685), parent="Torso", pivot="shoulder",
                    fuv=((420, 537), (420, 567)), buv=((921, 1033), (885, 1033))),
      "LegR":   dict(f=(131, 281), s=(640, 820), r=(650, 969), parent="Torso", pivot="hip"),
      "LegL":   dict(f=(301, 452), s=(640, 820), r=(650, 969), parent="Torso", pivot="hip"),
    },
    clean=[],
    hair=dict(px=(1160, 190), cap=(1.08, 1.06, 55, -4, 6), n=26, length=80, radius=32,
              bias=(0, 0.15, 0.2), front_min=0.55, zmin=-0.35, seed=5),
    extras=[],
  ),
}

# ---------------------------------------------------------------- texture prep
def load_sheet(c):
    im = Image.open(os.path.join(IMG_DIR, c["sheet"])).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255.0
    rgb, al = a[..., :3].copy(), a[..., 3]
    solid = al > 0.5
    rgb[~solid] = 0
    # dilate opaque colours into transparent background (so box crops never show white/grey edges)
    filled = solid.copy()
    for _ in range(40):
        acc = np.zeros_like(rgb); cnt = np.zeros(al.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sh = np.roll(filled, (dy, dx), (0, 1)); shc = np.roll(rgb, (dy, dx), (0, 1))
            acc += shc * sh[..., None]; cnt += sh
        new = (~filled) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        filled |= new
        if filled.all():
            break
    clean = rgb.copy()
    for (c0, c1, r0, r1, src) in c.get("clean", []):
        clean[r0:r1, c0:c1] = clean[src, c0:c1][None]
    atlas = np.concatenate([rgb, clean], 0)  # bottom half = cleaned copy
    return rgb, atlas


def make_image(name, atlas):
    H, W, _ = atlas.shape
    img = bpy.data.images.new(name, W, H, alpha=False)
    px = np.concatenate([atlas[::-1], np.ones((H, W, 1), np.float32)], 2)
    img.pixels.foreach_set(px.ravel())
    img.file_format = "PNG"
    img.pack()
    return img


def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ---------------------------------------------------------------- geometry
class Ctx:
    pass


def X(ctx, col): return (col - ctx.c["cxF"]) * S
def Y(ctx, col): return (col - ctx.c["cyS"]) * S
def Z(ctx, row): return (ctx.c["feet"] - row) * S


def uv_of(ctx, face, co, part_box, mode=None, p=None):
    """Planar projection of a world-space rest point to atlas UV."""
    c = ctx.c; H = ctx.H; W = ctx.W
    x, y, z = co
    row = c["feet"] - z / S
    p = p or {}
    if isinstance(mode, tuple) and mode[0] == "px":  # constant colour from one sheet pixel
        return (mode[1] / W, 1.0 - mode[2] / H)
    x0, x1, z0, z1 = part_box[0], part_box[1], part_box[4], part_box[5]
    if face in ("F", "B") and (("fuv" if face == "F" else "buv") in p):
        # trapezoid crop: ((col0_top, col1_top), (col0_bottom, col1_bottom)) in that view's columns
        (t0, t1), (b0, b1) = p["fuv" if face == "F" else "buv"]
        sz = (z - z0) / (z1 - z0)
        c0 = b0 + (t0 - b0) * sz; c1 = b1 + (t1 - b1) * sz
        t = (x - x0) / (x1 - x0) if face == "F" else (x1 - x) / (x1 - x0)
        return ((c0 + t * (c1 - c0)) / W, 1.0 - row / H)
    if face == "F":
        col = c["cxF"] + x / S
    elif face == "B":
        col = c["cxB"] - x / S
    elif face in ("L", "R"):
        col = c["cyS"] + y / S
        if mode == "edgeF":  # stretch the FRONT view's edge column across the side face
            x0, x1 = part_box[0], part_box[1]
            ex = (x1 - 8 * S) if face == "L" else (x0 + 8 * S)
            col = c["cxF"] + ex / S
        elif mode == "clean":
            row += H / 2
    elif face == "T":
        col = c["cxF"] + x / S
        row = c["feet"] - (part_box[5] / S) + 6
    else:  # D
        col = c["cxF"] + x / S
        row = c["feet"] - (part_box[4] / S) - 6
    return (col / W, 1.0 - row / H)


def box_mesh(ctx, name, p, mat):
    """p: dict with f,s,r (+fb,sb). Returns object (mesh in world coords)."""
    x0, x1 = X(ctx, p["f"][0]), X(ctx, p["f"][1])
    y0, y1 = Y(ctx, p["s"][0]), Y(ctx, p["s"][1])
    z1, z0 = Z(ctx, p["r"][0]), Z(ctx, p["r"][1])
    bx0, bx1 = (X(ctx, p["fb"][0]), X(ctx, p["fb"][1])) if "fb" in p else (x0, x1)
    by0, by1 = (Y(ctx, p["sb"][0]), Y(ctx, p["sb"][1])) if "sb" in p else (y0, y1)
    v = [(bx0, by0, z0), (bx1, by0, z0), (bx1, by1, z0), (bx0, by1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = {"F": (0, 1, 5, 4), "B": (2, 3, 7, 6), "L": (1, 2, 6, 5), "R": (3, 0, 4, 7),
             "T": (4, 5, 6, 7), "D": (3, 2, 1, 0)}
    box = (min(x0, bx0), max(x1, bx1), min(y0, by0), max(y1, by1), z0, z1)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bv = [bm.verts.new(co) for co in v]
    uvl = bm.loops.layers.uv.new("UVMap")
    ov = p.get("ov", {})
    for fk, idx in faces.items():
        f = bm.faces.new([bv[i] for i in idx])
        for loop in f.loops:
            loop[uvl].uv = uv_of(ctx, fk, loop.vert.co, box, ov.get(fk), p)
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ctx.col.objects.link(ob)
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.012; bev.segments = 3; bev.limit_method = "ANGLE"; bev.harden_normals = False
    for poly in me.polygons:
        poly.use_smooth = True
    return ob, box


def set_origin(ob, pivot):
    """Move object origin to world point pivot (mesh stays in place)."""
    pv = Vector(pivot)
    ob.data.transform(Matrix.Translation(-pv))
    ob.location = pv


def parent_keep(ch, par):
    mw = ch.matrix_world.copy()
    ch.parent = par
    ch.matrix_parent_inverse = par.matrix_world.inverted()
    ch.matrix_world = mw


def solid_mat(name, rgb_srgb, rough=0.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    lin = srgb_to_lin(rgb_srgb)
    b.inputs["Base Color"].default_value = (float(lin[0]), float(lin[1]), float(lin[2]), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Specular IOR Level"].default_value = 0.35
    return m


def atlas_mat(name, img):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img; t.interpolation = "Linear"
    t.extension = "EXTEND"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.42
    b.inputs["Specular IOR Level"].default_value = 0.3
    return m


def make_hair(ctx, head_box, hp, mat):
    x0, x1, y0, y1, z0, z1 = head_box
    kx, ky, rz_px, dz_px, dy_px = hp["cap"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + dy_px * S
    cz = z1 + dz_px * S
    rx, ry, rz = (x1 - x0) / 2 * kx, (y1 - y0) / 2 * ky, rz_px * S
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0,
                              matrix=Matrix.Translation((cx, cy, cz)) @ Matrix.Diagonal((rx, ry, rz, 1)))
    rng = random.Random(hp["seed"])
    bias = Vector(hp["bias"])
    n = hp["n"]; golden = math.pi * (3 - math.sqrt(5))
    zmin = hp["zmin"]
    m = int(n * 1.5)
    for i in range(m):
        t = (i + 0.5) / m
        dz = 1 - t * (1 - zmin)
        r = math.sqrt(max(0, 1 - dz * dz))
        ang = i * golden
        d = Vector((r * math.cos(ang), r * math.sin(ang), dz))
        if d.y < -0.35 and d.z < hp["front_min"]:
            continue  # keep the face / headband clear
        base = Vector((cx + rx * d.x * 0.8, cy + ry * d.y * 0.8, cz + rz * d.z * 0.8))
        axis = (d + bias).normalized()
        L = hp["length"] * S * rng.uniform(0.75, 1.25)
        R = hp["radius"] * S * rng.uniform(0.8, 1.15)
        rot = axis.to_track_quat("Z", "Y").to_matrix().to_4x4()
        mtx = Matrix.Translation(base) @ rot @ Matrix.Translation((0, 0, L / 2))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=R, radius2=0.0,
                              depth=L, matrix=mtx)
    me = bpy.data.meshes.new("Hair")
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new("Hair", me)
    ctx.col.objects.link(ob)
    return ob


def sample(ctx, px):
    c, r = px
    return tuple(float(v) for v in ctx.rgb[int(r), int(c)])


# ---------------------------------------------------------------- build
def build(name):
    c = CHARS[name]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ctx = Ctx(); ctx.c = c
    ctx.rgb, atlas = load_sheet(c)
    ctx.H, ctx.W = atlas.shape[0], atlas.shape[1]
    ctx.col = bpy.context.scene.collection
    img = make_image(f"{name}_atlas", atlas)
    mat = atlas_mat(f"{name}_body", img)

    root = bpy.data.objects.new(f"{name}_root", None)
    root.empty_display_type = "PLAIN_AXES"
    ctx.col.objects.link(root)

    objs, boxes = {}, {}
    for pn, p in c["parts"].items():
        ob, box = box_mesh(ctx, pn, p, mat)
        x0, x1, y0, y1, z0, z1 = box
        cxp, cyp = (x0 + x1) / 2, (y0 + y1) / 2
        pv = {"neck": (cxp, cyp, z0), "hip": (cxp, cyp, z1), "center": (cxp, cyp, (z0 + z1) / 2),
              "hip_center": (cxp, cyp, z0), "shoulder": (cxp, cyp, z1 - (x1 - x0) / 2)}[p["pivot"]]
        set_origin(ob, pv)
        objs[pn], boxes[pn] = ob, box

    hp = c["hair"]
    hair_rgb = sample(ctx, hp["px"])
    hair = make_hair(ctx, boxes["Head"], hp, solid_mat(f"{name}_hair", hair_rgb, 0.38))
    set_origin(hair, objs["Head"].location)
    objs["Hair"] = hair

    for e in c["extras"]:
        if e.get("sword"):
            tb = boxes["Torso"]
            L = 330 * S
            me = bpy.data.meshes.new("Sword")
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((0.055, 0.035, L, 1)))
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, L * 0.2)) @ Matrix.Diagonal((0.075, 0.05, 0.014, 1)))
            bm.to_mesh(me); bm.free()
            me.materials.append(solid_mat("sword", (0.11, 0.11, 0.13), 0.3))
            ob = bpy.data.objects.new("Sword", me); ctx.col.objects.link(ob)
            ob.location = (-0.04, tb[3] + 0.03, Z(ctx, 640))
            ob.rotation_euler = (0, math.radians(-16), 0)
            objs["Sword"] = ob
            continue
        if "size" in e:  # free box (headband tails)
            w, d, h = (v * S for v in e["size"])
            me = bpy.data.meshes.new(e["name"]); bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, -h / 2)) @ Matrix.Diagonal((w, d, h, 1)))
            bm.to_mesh(me); bm.free()
            me.materials.append(solid_mat(e["name"] + "_m", sample(ctx, e["color_px"]), 0.5))
            ob = bpy.data.objects.new(e["name"], me); ctx.col.objects.link(ob)
            ax, ay, ar = e["at"]
            ob.location = (ax * S, Y(ctx, ay), Z(ctx, ar))
            ob.rotation_euler = tuple(math.radians(a) for a in e["rot"])
            objs[e["name"]] = ob
            continue
        if e.get("back_f"):
            # box given in BACK-view columns
            f0, f1 = e["f"]
            cxB = c["cxB"]
            p = dict(f=(c["cxF"] - (f1 - cxB), c["cxF"] - (f0 - cxB)), s=e["s"], r=e["r"])
        else:
            p = dict(f=e["f"], s=e["s"], r=e["r"])
        m = mat if e.get("mat") == "atlas" else solid_mat(e["name"] + "_m", sample(ctx, e["color_px"]), 0.5)
        ob, box = box_mesh(ctx, e["name"], p, m)
        ob.modifiers["Bevel"].width = 0.006
        set_origin(ob, ((box[0] + box[1]) / 2, (box[2] + box[3]) / 2, (box[4] + box[5]) / 2))
        objs[e["name"]] = ob

    bpy.context.view_layer.update()
    # hierarchy
    parent_keep(objs["Torso"], root)
    for pn, p in c["parts"].items():
        if p["parent"]:
            parent_keep(objs[pn], objs[p["parent"]])
    parent_keep(hair, objs["Head"])
    for e in c["extras"]:
        parent_keep(objs[e["name"]], objs[e.get("parent", "Torso")])
    bpy.context.view_layer.update()
    return root, objs


# ---------------------------------------------------------------- scene / render setup
PPM = 450.0           # sprite pixels per metre
SPR_W, SPR_H = 900, 1100
FEET_ROW = 1040       # pixel row (from top) of the ground plane z=0 in sprites


def setup_scene(transparent=True, res=(SPR_W, SPR_H), samples=24):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_soft_shadows = True
    sc.eevee.use_gtao = True
    sc.eevee.gtao_distance = 0.25
    sc.eevee.shadow_cube_size = "1024"
    sc.eevee.shadow_cascade_size = "2048"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("World"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.62, 0.62, 0.64, 1)
    bg.inputs["Strength"].default_value = 0.55
    # key: soft sun from front-left & above
    def light(name, typ, energy, rot, size=None, color=(1, 1, 1), loc=(0, 0, 0)):
        ld = bpy.data.lights.new(name, typ); ld.energy = energy; ld.color = color
        if typ == "SUN": ld.angle = math.radians(size or 8)
        if typ == "AREA": ld.size = size or 2
        ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = tuple(math.radians(a) for a in rot)
        return ob
    light("Key", "SUN", 3.2, (52, 0, -38), 12, (1.0, 0.97, 0.92))      # front-left high
    light("Fill", "SUN", 1.0, (70, 0, 50), 25, (0.9, 0.94, 1.0))       # front-right low
    light("Rim", "SUN", 2.0, (60, 0, 165), 6, (1, 1, 1))               # behind
    return sc


def ortho_camera(sc):
    cd = bpy.data.cameras.new("Cam"); cd.type = "ORTHO"
    cd.ortho_scale = SPR_H / PPM
    cam = bpy.data.objects.new("Cam", cd); sc.collection.objects.link(cam)
    zc = (FEET_ROW - SPR_H / 2) / PPM
    cam.location = (0, -12, zc); cam.rotation_euler = (math.radians(90), 0, 0)
    cd.clip_end = 50
    sc.camera = cam
    return cam


# ---------------------------------------------------------------- posing
def deg(*a): return tuple(math.radians(v) for v in a)


def reset_pose(objs, root):
    for k, o in objs.items():
        if k in ("ArmL", "ArmR", "LegL", "LegR", "Head"):
            o.rotation_euler = (0, 0, 0)
    root.location = (0, 0, 0)


def apply_pose(objs, root, yaw, pose, lift=0.0, ground=True):
    reset_pose(objs, root)
    root.rotation_euler = (0, 0, math.radians(-yaw))
    for k, r in pose.items():
        objs[k].rotation_euler = Euler(deg(*r), "XYZ")
    bpy.context.view_layer.update()
    if ground:
        dg = bpy.context.evaluated_depsgraph_get()
        zmin = 1e9
        for k in ("LegL", "LegR"):
            o = objs[k]
            for v in o.data.vertices:
                zmin = min(zmin, (o.matrix_world @ v.co).z)
        root.location.z = -zmin + lift
    else:
        root.location.z = lift
    bpy.context.view_layer.update()


def walk_pose(i, amp=30):
    ph = 2 * math.pi * i / 8
    s = math.sin(ph)
    return {"LegL": (-amp * s, 0, 0), "LegR": (amp * s, 0, 0),
            "ArmL": (amp * s, 0, -4), "ArmR": (-amp * s, 0, 4), "Head": (0, 0, 0)}


TALK = [
    {"Head": (-3, 4, 0), "ArmR": (-18, 12, 0), "ArmL": (0, -4, 0)},
    {"Head": (3, -3, 3), "ArmR": (-30, 18, 0), "ArmL": (-8, -8, 0)},
    {"Head": (-2, 0, -4), "ArmR": (-8, 6, 0), "ArmL": (-22, -14, 0)},
    {"Head": (4, 5, 2), "ArmR": (-26, 10, 0), "ArmL": (-14, -10, 0)},
]
SPECIAL = {
    "sasuke": {"yell_00": ({"ArmR": (-20, 95, 0), "ArmL": (-20, -95, 0), "Head": (-8, 0, 0)}, 0.0),
               "yell_01": ({"ArmR": (-10, 140, 0), "ArmL": (-10, -140, 0), "Head": (-14, 3, 0)}, 0.0)},
    "naruto": {"jump_00": ({"ArmR": (0, 150, 0), "ArmL": (0, -150, 0), "LegR": (-40, 0, 0),
                            "LegL": (25, 0, 0), "Head": (-6, 0, 0)}, 0.22),
               "cheer_00": ({"ArmR": (-170, 0, 8), "ArmL": (-10, -6, 0), "Head": (-6, 4, 0)}, 0.0),
               "cheer_01": ({"ArmR": (-160, 12, 0), "ArmL": (-25, -12, 0), "Head": (-4, -5, 4)}, 0.0)},
    "obito": {"shrug_00": ({"ArmR": (-55, 40, 0), "ArmL": (-55, -40, 0), "Head": (0, 10, 0)}, 0.0)},
}


def render_to(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["naruto", "--build"]
    name = argv[0]; flags = set(argv[1:])
    root, objs = build(name)
    os.makedirs(OUT, exist_ok=True)
    if "--build" in flags:
        # glb with modifiers applied
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{name}.glb"), export_format="GLB",
                                  export_apply=True, export_yup=True)
    sc = setup_scene(transparent=True)
    cam = ortho_camera(sc)
    if "--build" in flags:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"), compress=True)

    if "--previews" in flags:
        pdir = os.path.join(OUT, "previews", name); os.makedirs(pdir, exist_ok=True)
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
        sc.render.resolution_x, sc.render.resolution_y = 1080, 1350
        cam.data.type = "PERSP"; cam.data.lens = 85
        cam.location = (0, -5.4, 0.93); cam.rotation_euler = deg(90, 0, 0)
        for lab, yaw in [("front", 0), ("three_quarter_front_left", 40), ("side_left", 90),
                         ("back", 180), ("three_quarter_back", 220), ("side_right", 270)]:
            apply_pose(objs, root, yaw, {})
            render_to(os.path.join(pdir, f"{name}_{lab}.png"))
        sc.render.film_transparent = True
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.resolution_x, sc.render.resolution_y = SPR_W, SPR_H
        cam.data.type = "ORTHO"; cam.data.ortho_scale = SPR_H / PPM
        cam.location = (0, -12, (FEET_ROW - SPR_H / 2) / PPM)

    if "--sprites" in flags:
        sdir = os.path.join(OUT, "sprites", name); os.makedirs(sdir, exist_ok=True)
        frames = []
        for yaw in range(0, 360, 10):
            apply_pose(objs, root, yaw, {})
            fn = f"turn_{yaw:03d}.png"; render_to(os.path.join(sdir, fn)); frames.append(fn)
        for side, yaw in (("left", 70), ("right", 290)):
            for i in range(8):
                apply_pose(objs, root, yaw, walk_pose(i))
                fn = f"walk_{side}_{i:02d}.png"; render_to(os.path.join(sdir, fn)); frames.append(fn)
        for i, p in enumerate(TALK):
            apply_pose(objs, root, 0, p)
            fn = f"talk_{i:02d}.png"; render_to(os.path.join(sdir, fn)); frames.append(fn)
        for lab, (p, lift) in SPECIAL.get(name, {}).items():
            apply_pose(objs, root, 0, p, lift=lift)
            fn = f"{lab}.png"; render_to(os.path.join(sdir, fn)); frames.append(fn)
        with open(os.path.join(sdir, "frames.json"), "w") as f:
            json.dump(frames, f, indent=1)

    if "--turntable" in flags:
        tdir = os.path.join(OUT, "turntable_frames", name); os.makedirs(tdir, exist_ok=True)
        sc.render.film_transparent = False
        sc.render.image_settings.color_mode = "RGB"
        sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
        cd = cam.data; cd.type = "PERSP"; cd.lens = 85
        cam.location = (0, -7.6, 1.0); cam.rotation_euler = deg(89, 0, 0)
        sc.eevee.taa_render_samples = 16
        for i in range(120):
            apply_pose(objs, root, -i * 3, {})
            render_to(os.path.join(tdir, f"f_{i:03d}.png"))


if __name__ == "__main__":
    main()
