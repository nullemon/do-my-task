"""
ANDROMEDA documentary - CHAPTER 1 "THE SMUDGE" (0:00-1:00), 1920x1080, 24 fps, 1440 frames.

Today's sky over a black ridge and one bare, wind-bent tree, facing north-east on a late-September
evening (lat 40 N, sidereal time 19 h). Stars fade in, the Milky Way rises from the horizon through
Perseus and Cassiopeia, the camera pushes toward the constellation Andromeda and the faint smudge of
M31, a long-exposure reveal shows the full ~3.2 deg disk next to six full-Moon outlines, then a slow
zoom ends on a detailed Andromeda with M32 and M110.

Everything heavy is pre-baked by gen_textures.py (numpy). This file only builds emission planes with
image textures, a star mesh rebuilt per frame (constant on-screen star size at any zoom), a few thin
overlay strips, silhouettes and caption text, then renders with Cycles CPU.

Run (bpy module):
  python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing']; exec(compile(open(p).read(),p,'exec'))"
  ... '--frames','1,240,700'        preview stills
  ... '--render','--start','1','--end','720','--step','1'
"""
CONFIG = dict(
    fps=24,
    frames=1440,
    resolution=(1920, 1080),
    samples=4,
    threads=1,
    tex="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures",
    output="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/ch1/frames",
    font_name="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_thin="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
)

import sys
import os
import math
import json
import time
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV):
            return ARGV[i + 1]
    return default


FPS = CONFIG["fps"]
NF = CONFIG["frames"]
RW, RH = CONFIG["resolution"]
TEX = arg("--tex", CONFIG["tex"])
META = json.load(open(os.path.join(TEX, "ch1_meta.json")))
AZ0 = META["az0"]
D2R = math.pi / 180

TEXT_COL = (0.86, 0.85, 0.88)
ACCENT = (0.80, 0.72, 1.00)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(a):
    a = clamp(a)
    return a * a * a * (a * (a * 6 - 15) + 10)


def smooth(a):
    a = clamp(a)
    return a * a * (3 - 2 * a)


def ramp(t, t0, t1):
    return ease((t - t0) / max(1e-6, t1 - t0))


def sramp(t, t0, t1):
    return smooth((t - t0) / max(1e-6, t1 - t0))


def lerp(a, b, t):
    return a + (b - a) * t


def window(t, t_in, t_out, fin=0.8, fout=0.8):
    return clamp(min(sramp(t, t_in, t_in + fin), 1 - sramp(t, t_out, t_out + fout)))


def pchip(xs, ys):
    """monotone cubic interpolation (no overshoot)"""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = d[0] * 0.5; m[-1] = d[-1] * 0.5

    def f(x):
        x = min(max(x, xs[0]), xs[-1])
        i = min(np.searchsorted(xs, x) - 1, len(xs) - 2)
        i = max(i, 0)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] +
                (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def dir_altaz(alt_deg, az_deg):
    a, d = alt_deg * D2R, (az_deg - AZ0) * D2R
    return np.array([math.sin(d) * math.cos(a), math.cos(d) * math.cos(a), math.sin(a)])


def altaz_of(v):
    v = unit(v)
    return math.degrees(math.asin(v[2])), AZ0 + math.degrees(math.atan2(v[0], v[1]))


M31 = unit(META["m31"])
M31_ALT, M31_AZ = altaz_of(M31)


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, NF
    sc.render.resolution_x, sc.render.resolution_y = RW, RH
    sc.render.resolution_percentage = int(arg("--pct", 100))     # always 100 for delivery
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = int(arg("--samples", CONFIG["samples"]))
    cy.use_adaptive_sampling = False
    cy.use_denoising = False
    for k in ("max_bounces", "diffuse_bounces", "glossy_bounces", "transmission_bounces", "volume_bounces"):
        setattr(cy, k, 0)
    cy.transparent_max_bounces = 16
    cy.caustics_reflective = cy.caustics_refractive = False
    try:
        cy.use_light_tree = False
    except Exception:
        pass
    try:
        cy.filter_width = 1.5
    except Exception:
        sc.render.filter_size = 1.5
    cy.seed = 0
    try:
        cy.use_animated_seed = True
    except Exception:
        pass
    sc.render.threads_mode = "FIXED"
    sc.render.threads = int(arg("--threads", CONFIG["threads"]))
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.film_transparent = False
    ims = sc.render.image_settings
    try:
        ims.media_type = "IMAGE"
    except Exception:
        pass
    ims.file_format = "PNG"
    ims.color_mode = "RGB"
    ims.color_depth = "8"
    sc.render.use_persistent_data = True
    return sc


class NB:
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")

    def n(self, t, **kw):
        nd = self.nt.nodes.new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.nt.links.new(a, b)

    def m(self, op, a, b=None):
        nd = self.n("ShaderNodeMath", operation=op)
        for s, v in zip(nd.inputs, (a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                s.default_value = v
            else:
                self.link(v, s)
        return nd.outputs[0]


PARAM = {}


def param(b, name, v=0.0):
    nd = b.n("ShaderNodeValue")
    nd.outputs[0].default_value = v
    PARAM.setdefault(name, []).append(nd.outputs[0])
    return nd.outputs[0]


def set_param(name, v):
    for s in PARAM.get(name, []):
        s.default_value = v


def emit_out(b, color_sock, strength_sock):
    em = b.n("ShaderNodeEmission")
    b.link(color_sock, em.inputs["Color"])
    if isinstance(strength_sock, (int, float)):
        em.inputs["Strength"].default_value = strength_sock
    else:
        b.link(strength_sock, em.inputs["Strength"])
    tr = b.n("ShaderNodeBsdfTransparent")
    ad = b.n("ShaderNodeAddShader")
    b.link(tr.outputs[0], ad.inputs[0])
    b.link(em.outputs[0], ad.inputs[1])
    b.link(ad.outputs[0], b.out.inputs["Surface"])


def load_img(name):
    im = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    return im


def mat_image(name, img, pname, interp="Linear"):
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    uv = b.n("ShaderNodeTexCoord")
    tx = b.n("ShaderNodeTexImage")
    tx.image = load_img(img)
    tx.interpolation = interp
    tx.extension = "CLIP"
    b.link(uv.outputs["UV"], tx.inputs["Vector"])
    emit_out(b, tx.outputs["Color"], param(b, pname, 1.0))
    return mat


def mat_flat(name, color, pname=None):
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    em = b.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    if pname:
        b.link(param(b, pname, 1.0), em.inputs["Strength"])
    b.link(em.outputs[0], b.out.inputs["Surface"])
    return mat


def mat_line(name, color, pname):
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    uv = b.n("ShaderNodeTexCoord")
    sp = b.n("ShaderNodeSeparateXYZ")
    b.link(uv.outputs["UV"], sp.inputs[0])
    # soft cross-section: v in 0..1 across the strip
    d = b.m("SUBTRACT", sp.outputs[1], 0.5)
    prof = b.m("EXPONENT", b.m("MULTIPLY", b.m("MULTIPLY", d, d), -16.0))
    # fade toward the ends of each segment
    u = sp.outputs[0]
    ends = b.m("MINIMUM", b.m("MULTIPLY", u, 6.0), b.m("MULTIPLY", b.m("SUBTRACT", 1.0, u), 6.0))
    ends = b.m("MINIMUM", ends, 1.0)
    a = b.m("MULTIPLY", b.m("MULTIPLY", prof, ends), param(b, pname, 0.0))
    col = b.n("ShaderNodeRGB")
    col.outputs[0].default_value = (*color, 1)
    emit_out(b, col.outputs[0], a)
    return mat


def mat_stars():
    """per-star quads; colour attribute 'col' (rgb peak, a = halo amp), 'shp' (r core k, g halo k)"""
    mat = bpy.data.materials.new("M_stars")
    b = NB(mat)
    uv = b.n("ShaderNodeTexCoord")
    sp = b.n("ShaderNodeSeparateXYZ")
    b.link(uv.outputs["UV"], sp.inputs[0])
    dx = b.m("SUBTRACT", sp.outputs[0], 0.5)
    dy = b.m("SUBTRACT", sp.outputs[1], 0.5)
    d2 = b.m("MULTIPLY", b.m("ADD", b.m("MULTIPLY", dx, dx), b.m("MULTIPLY", dy, dy)), 4.0)   # 0 centre .. 1 edge
    ca = b.n("ShaderNodeAttribute", attribute_name="col")
    sa = b.n("ShaderNodeAttribute", attribute_name="shp")
    ss = b.n("ShaderNodeSeparateColor")
    b.link(sa.outputs["Color"], ss.inputs[0])
    core = b.m("EXPONENT", b.m("MULTIPLY", d2, b.m("MULTIPLY", ss.outputs[0], -1.0)))
    halo = b.m("EXPONENT", b.m("MULTIPLY", d2, b.m("MULTIPLY", ss.outputs[1], -1.0)))
    edge = b.m("SUBTRACT", 1.0, b.m("POWER", b.m("MINIMUM", d2, 1.0), 3.0))
    prof = b.m("MULTIPLY", b.m("ADD", core, b.m("MULTIPLY", halo, ca.outputs["Alpha"])), edge)
    vm = b.n("ShaderNodeVectorMath", operation="SCALE")
    b.link(ca.outputs["Color"], vm.inputs[0])
    b.link(prof, vm.inputs["Scale"])
    emit_out(b, vm.outputs[0], param(b, "stars", 1.0))
    return mat


WORLD = dict(comp={})


def set_world_active(names):
    """Sum only the sky components that contribute this frame. Unused image lookups are unlinked,
    so Cycles never evaluates them (the world shader is the main per-sample cost)."""
    names = [n for n in ("bg", "mw", "eye", "lo", "mid", "hi") if n in names] or ["bg"]
    if names == WORLD["active"]:
        return
    nt, bg = WORLD["nt"], WORLD["bg"]
    for nd in [n for n in nt.nodes if n.label == "chain"]:
        nt.nodes.remove(nd)
    col = WORLD["comp"][names[0]]
    for n in names[1:]:
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "ADD"
        vm.label = "chain"
        nt.links.new(col, vm.inputs[0])
        nt.links.new(WORLD["comp"][n], vm.inputs[1])
        col = vm.outputs[0]
    nt.links.new(col, bg.inputs["Color"])
    WORLD["active"] = names


def world_shader():
    """The whole sky lives in the world shader: airglow gradient + Milky Way + the M31 textures, each
    sampled through its own gnomonic projection of the ray direction. One shader evaluation per camera
    sample (no transparent sky planes) keeps Cycles CPU fast."""
    w = bpy.data.worlds.new("Sky")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    dirv = tc.outputs["Generated"]
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(dirv, sp.inputs[0])

    def m(op, a, b_=None):
        nd = nt.nodes.new("ShaderNodeMath")
        nd.operation = op
        for s_, v in zip(nd.inputs, (a, b_)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                s_.default_value = v
            else:
                nt.links.new(v, s_)
        return nd.outputs[0]

    def vconst(v):
        c = nt.nodes.new("ShaderNodeCombineXYZ")
        for i in range(3):
            c.inputs[i].default_value = float(v[i])
        return c.outputs[0]

    def dot(a, vec):
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "DOT_PRODUCT"
        nt.links.new(a, vm.inputs[0])
        nt.links.new(vconst(vec), vm.inputs[1])
        return vm.outputs["Value"]

    def vscale(vec_sock, fac):
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "SCALE"
        nt.links.new(vec_sock, vm.inputs[0])
        if isinstance(fac, (int, float)):
            vm.inputs["Scale"].default_value = fac
        else:
            nt.links.new(fac, vm.inputs["Scale"])
        return vm.outputs[0]

    def vadd(a, b_):
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "ADD"
        nt.links.new(a, vm.inputs[0]); nt.links.new(b_, vm.inputs[1])
        return vm.outputs[0]

    def pval(name, v=1.0):
        pv = nt.nodes.new("ShaderNodeValue")
        pv.outputs[0].default_value = v
        PARAM.setdefault(name, []).append(pv.outputs[0])
        return pv.outputs[0]

    def proj_uv(c, r, u, tx, ty):
        wv = m("MAXIMUM", dot(dirv, c), 1e-4)
        U = m("ADD", m("MULTIPLY", m("DIVIDE", dot(dirv, r), wv), 0.5 / tx), 0.5)
        V = m("ADD", m("MULTIPLY", m("DIVIDE", dot(dirv, u), wv), 0.5 / ty), 0.5)
        # push rays from the back hemisphere outside the image
        V = m("ADD", V, m("MULTIPLY", m("LESS_THAN", dot(dirv, c), 0.05), 10.0))
        cxyz = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(U, cxyz.inputs[0]); nt.links.new(V, cxyz.inputs[1])
        return cxyz.outputs[0]

    def img(name, uvs, interp):
        tx_ = nt.nodes.new("ShaderNodeTexImage")
        tx_.image = load_img(name)
        tx_.interpolation = interp
        tx_.extension = "CLIP"
        nt.links.new(uvs, tx_.inputs["Vector"])
        return tx_.outputs["Color"]

    col = vconst(META["mw_plane"]["bg_m31"])
    WORLD["comp"]["bg"] = vscale(col, pval("bg", 1.0))
    mp = META["mw_plane"]
    WORLD["comp"]["mw"] = vscale(img("ch1_mw.png", proj_uv(mp["c"], mp["r"], mp["u"], mp["tx"], mp["ty"]), "Linear"), pval("mw", 1.0))
    guv = proj_uv(GP["c"], GP["r"], GP["u"], GP["tx"], GP["ty"])
    for k, f in (("eye", "ch1_m31_eye.png"), ("lo", "ch1_m31_lo.png"), ("mid", "ch1_m31_mid.png"), ("hi", "ch1_m31_hi.png")):
        WORLD["comp"][k] = vscale(img(f, guv, "Linear"), pval(k, 0.0))
    WORLD["nt"], WORLD["bg"] = nt, bg
    WORLD["active"] = None
    set_world_active(["bg"])
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    try:
        w.cycles.sampling_method = "NONE"      # no world importance map (rebuilt on every change otherwise)
    except Exception:
        pass
    bpy.context.scene.world = w


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def sky_plane(name, mat, c, r, u, tx, ty, D):
    """gnomonic plane: centre direction c, basis r (right), u (up), half extents tan tx, ty, at distance D"""
    me = bpy.data.meshes.new(name)
    c, r, u = np.array(c), np.array(r), np.array(u)
    P = lambda sx, sy: tuple((c + sx * tx * r + sy * ty * u) * D)
    verts = [P(-1, -1), P(1, -1), P(1, 1), P(-1, 1)]
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name="UVMap")
    for i, uvv in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uvl.data[i].uv = uvv
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def fbm1(x, seed, octaves=7):
    v, a, f = 0.0, 1.0, 1.0
    for i in range(octaves):
        v += a * (math.sin(x * f * 0.9 + seed * 1.7 + i * 2.3) * 0.6 + math.sin(x * f * 2.1 + seed * 3.1 + i) * 0.4)
        a *= 0.5
        f *= 2.03
    return v


def ridge(name, dist, alt_base, amp, seed, mat, az_span=(-75, 75), nseg=700, freq=3.0):
    """silhouette strip on a cylinder of radius dist around the camera; heights given as altitudes"""
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(nseg + 1):
        a = az_span[0] + (az_span[1] - az_span[0]) * i / nseg
        alt = alt_base + amp * fbm1(a / 60.0 * freq, seed)
        x, y = dist * math.sin(a * D2R), dist * math.cos(a * D2R)
        z = dist * math.tan(alt * D2R)
        verts += [(x, y, z), (x, y, -dist * 0.6)]
    for i in range(nseg):
        a0, a1 = 2 * i, 2 * i + 2
        faces.append((a0 + 1, a1 + 1, a1, a0))
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ridge_z(dist, alt_base, amp, seed, a_deg, freq=3.0):
    alt = alt_base + amp * fbm1(a_deg / 60.0 * freq, seed)
    return dist * math.tan(alt * D2R)


def tree(name, base, height, mat, seed=7):
    """bare, wind-bent tree: recursive tapered branches (low-poly cones)"""
    import random
    rnd = random.Random(seed)
    bm = bmesh.new()

    def branch(p, d, length, rad, depth):
        q = p + d * length
        mtx = Matrix.Translation((p + q) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=7, radius1=rad, radius2=rad * 0.68,
                              depth=length * 1.04, matrix=mtx)
        if depth == 0 or rad < 0.006:
            return
        nb = 2
        for i in range(nb):
            ax = Vector((rnd.uniform(-1.2, 1.0), rnd.uniform(-0.4, 0.4), rnd.uniform(-0.35, 0.45)))
            nd = (d + ax * rnd.uniform(0.6, 1.1) + Vector((0.30, 0, -0.02))).normalized()
            branch(q, nd, length * rnd.uniform(0.62, 0.84), rad * 0.62, depth - 1)
        if rnd.random() < 0.35:
            branch(q, (d + Vector((0.28, 0, 0.0))).normalized(), length * 0.7, rad * 0.66, depth - 1)

    branch(Vector(base) - Vector((0, 0, 0.6)), Vector((0.16, 0, 1)).normalized(), height * 0.42 + 0.6, height * 0.030, 7)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
OBJ = {}
TEXTS = {}
D_MW, D_GAL, D_OVER, D_STAR, D_LINE = 9000.0, 8000.0, 7000.0, 6000.0, 6500.0
GP = META["gal_plane"]
GC, GR, GU = np.array(GP["c"]), np.array(GP["r"]), np.array(GP["u"])


def gal_dir(xdeg, ydeg):
    """direction of a point given in the galaxy plane frame (deg)"""
    return unit(GC + math.tan(xdeg * D2R) * GR + math.tan(ydeg * D2R) * GU)


def build():
    global CAM, HUD, STARS, STAR_DATA
    world_shader()
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36.0
    cd.clip_start = 0.05
    cd.clip_end = 20000.0
    CAM = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(CAM)
    bpy.context.scene.camera = CAM
    HUD = bpy.data.objects.new("HUD", None)
    bpy.context.scene.collection.objects.link(HUD)
    HUD.parent = CAM
    HUD.location = (0, 0, -1.0)

    # six full-Moon outlines along the major axis (Moon ~0.52 deg; ring drawn at 0.96 of the half size)
    ring_m = []
    for k in range(6):
        xo = (k - 2.5) * 0.52
        c = gal_dir(xo, 0.0)
        r = unit(GR - np.dot(GR, c) * c); u = np.cross(r, c) * -1.0
        u = unit(GU - np.dot(GU, c) * c); r = np.cross(c, u)
        half = math.tan(0.26 / 0.96 * D2R)
        OBJ[f"moon{k}"] = sky_plane(f"moon{k}", mat_image(f"M_moon{k}", "ch1_ring.png", f"moon{k}", "Linear"),
                                    c, r, u, half, half, D_OVER)
    # marker circle around the smudge
    half = math.tan(1.15 * D2R)
    OBJ["marker"] = sky_plane("marker", mat_image("M_marker", "ch1_ring.png", "marker", "Linear"),
                              M31, unit(np.cross(M31, unit(np.array([0, 0, 1.0]) - M31[2] * M31))), unit(np.array([0, 0, 1.0]) - M31[2] * M31),
                              half, half, D_OVER + 10)

    # constellation lines (geometry rebuilt per frame for a constant on-screen width)
    me = bpy.data.meshes.new("lines")
    OBJ["lines"] = bpy.data.objects.new("lines", me)
    bpy.context.scene.collection.objects.link(OBJ["lines"])
    me.materials.append(mat_line("M_lines", ACCENT, "lines"))

    # stars
    data = np.load(os.path.join(TEX, "ch1_stars.npz"))
    STAR_DATA = dict(d=data["dirs"].astype(np.float64), m=data["mag"].astype(np.float64), c=data["col"].astype(np.float64))
    me = bpy.data.meshes.new("stars")
    STARS = bpy.data.objects.new("stars", me)
    bpy.context.scene.collection.objects.link(STARS)
    me.materials.append(mat_stars())

    # landscape: three silhouette layers + the tree (world space; camera at origin, +Y = az 46)
    black = mat_flat("M_black", (0, 0, 0))
    OBJ["far"] = ridge("ridge_far", 1400.0, 2.6, 1.3, 4.0, mat_flat("M_far", (0.0045, 0.0055, 0.0078), "haze"), freq=2.2)
    OBJ["mid"] = ridge("ridge_mid", 300.0, 1.9, 1.5, 9.0, mat_flat("M_mid", (0.0016, 0.0019, 0.0027), "haze"), freq=3.4)
    OBJ["near"] = ridge("ridge_near", 60.0, 0.2, 3.0, 1.0, black, az_span=(-80, 80), freq=2.6)
    ta = -21.0
    tz = ridge_z(60.0, 0.2, 3.0, 1.0, ta, freq=2.6)
    tpos = (60.0 * math.sin(ta * D2R), 60.0 * math.cos(ta * D2R), tz)
    OBJ["tree"] = tree("tree", tpos, 17.0, black)


# --- captions ---------------------------------------------------------------
FONTS = {}


def font(path):
    if path not in FONTS:
        try:
            FONTS[path] = bpy.data.fonts.load(path)
        except Exception:
            FONTS[path] = None
    return FONTS[path]


REF_TAN = math.tan(math.radians(76.0) / 2)        # HUD units are defined at this half-fov
HUD_W = REF_TAN                                  # half frame width in HUD units
HUD_H = REF_TAN * RH / RW


def make_text(tid, body, fx, fy, size, spacing=1.0, thin=False, color=TEXT_COL, align="CENTER"):
    cu = bpy.data.curves.new(tid, "FONT")
    cu.body = body
    f = font(CONFIG["font_thin"] if thin else CONFIG["font_name"])
    if f:
        cu.font = f
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.size = size
    cu.space_character = spacing
    ob = bpy.data.objects.new(tid, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = HUD
    ob.location = ((fx - 0.5) * 2 * HUD_W, (fy - 0.5) * 2 * HUD_H, 0)
    mat = bpy.data.materials.new("MT_" + tid)
    b = NB(mat)
    em = b.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    tr = b.n("ShaderNodeBsdfTransparent")
    mx = b.n("ShaderNodeMixShader")
    b.link(tr.outputs[0], mx.inputs[1])
    b.link(em.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs["Surface"])
    cu.materials.append(mat)
    TEXTS[tid] = (ob, mx)
    return ob


# (id, text, t_in, t_out)
CAPTIONS = [
    ("c1", "ANDROMEDA (M31)", 9.6, 14.6),
    ("c2", "≈ 2.5 MILLION LIGHT-YEARS", 16.8, 22.6),
    ("c3", "≈ 6 FULL MOONS WIDE", 27.0, 32.3),
    ("c4", "LIGHT LEFT ≈ 2.5 MILLION YEARS AGO", 35.0, 41.6),
]


def build_texts():
    s = 0.025 * 2 * HUD_H         # font size relative to frame height
    for tid, body, t0, t1 in CAPTIONS:
        make_text(tid, body, 0.5, 0.115, s, spacing=1.45)


def set_alpha(tid, a):
    ob, mx = TEXTS[tid]
    mx.inputs[0].default_value = a
    ob.hide_render = a <= 0.002


# ---------------------------------------------------------------------------
# camera path
# ---------------------------------------------------------------------------
HFOV = pchip([0.0, 7.0, 12.0, 16.5, 24.0, 33.0, 43.0, 51.0, 60.0],
             np.log([76.0, 71.0, 41.0, 20.5, 12.6, 8.7, 4.75, 3.85, 2.85]))
W_END = (18.3, 47.4)          # alt, az of the wide shot at the start of the push


def camera_state(t):
    hfov = math.exp(HFOV(t))
    # wide drift, then push toward M31
    a0 = lerp(17.6, W_END[0], ramp(t, 0.0, 7.5))
    z0 = lerp(46.0, W_END[1], ramp(t, 0.0, 7.5))
    s = ramp(t, 6.8, 17.0)
    s = s ** 0.85
    # final framing: M31 slightly offset, very slow drift across the disk in the close-up
    gx = lerp(0.0, -0.10, ramp(t, 30.0, 60.0))
    gy = lerp(0.0, -0.03, ramp(t, 30.0, 60.0))
    tgt = gal_dir(gx, gy)
    ta, tz = altaz_of(tgt)
    alt = lerp(a0, ta, s)
    az = lerp(z0, tz, s)
    fwd = dir_altaz(alt, az)
    roll = ROLL_TARGET * ramp(t, 15.0, 50.0)
    pos = (lerp(-1.4, 1.4, sramp(t, 0.0, 16.0)), lerp(0.0, 1.2, sramp(t, 0.0, 16.0)), 0.0)
    return fwd, roll, hfov, pos


def cam_basis(fwd, roll):
    f = unit(fwd)
    z = np.array([0, 0, 1.0])
    up0 = unit(z - np.dot(z, f) * f)
    r0 = np.cross(f, up0)
    up = math.cos(roll) * up0 + math.sin(roll) * r0
    r = np.cross(f, up)
    return f, r, up


def compute_roll_target():
    """roll (rad) so the M31 major axis sits at ~ +20 deg from horizontal in the close-up"""
    f, r, up = cam_basis(M31, 0.0)
    ax = GR - np.dot(GR, f) * f
    ang = math.degrees(math.atan2(np.dot(ax, up), np.dot(ax, r)))
    # bring to (-90, 90]
    while ang > 90:
        ang -= 180
    while ang <= -90:
        ang += 180
    best = None
    for want in (22.0, -22.0):
        d_ = want - ang
        d_ = (d_ + 90) % 180 - 90
        if best is None or abs(d_) < abs(best):
            best = d_
    return math.radians(best)


ROLL_TARGET = 0.0


def set_camera(t):
    fwd, roll, hfov, pos = camera_state(t)
    f, r, up = cam_basis(fwd, roll)
    M = Matrix(((r[0], up[0], -f[0], pos[0]), (r[1], up[1], -f[1], pos[1]), (r[2], up[2], -f[2], pos[2]), (0, 0, 0, 1)))
    CAM.matrix_world = M
    CAM.data.lens = 18.0 / math.tan(math.radians(hfov) / 2)
    k = math.tan(math.radians(hfov) / 2) / REF_TAN
    HUD.scale = (k, k, k)
    return f, r, up, hfov


# ---------------------------------------------------------------------------
# per-frame star mesh
# ---------------------------------------------------------------------------
def completeness(rdeg):
    """catalogue limiting magnitude as a function of distance from M31 (see gen_textures.py)"""
    if rdeg < 6.0:
        return 15.4
    if rdeg < 14.0:
        return 13.2
    if rdeg < 24.0:
        return 11.2
    return 9.2


def update_stars(t, f, r, up, hfov, fade_mlim, gain):
    d, m, c = STAR_DATA["d"], STAR_DATA["m"], STAR_DATA["c"]
    tanh = math.tan(math.radians(hfov) / 2)
    tanv = tanh * RH / RW
    pxrad = (RW / 2) / tanh                      # px per tan-unit at the image centre
    z = d @ f
    x = (d @ r) / np.maximum(z, 1e-6)
    y = (d @ up) / np.maximum(z, 1e-6)
    inview = (z > 0.05) & (np.abs(x) < tanh * 1.04 + 0.01) & (np.abs(y) < tanv * 1.06 + 0.01)
    # limiting magnitude grows as we zoom (bigger "aperture"), bounded by catalogue completeness
    mlim = 7.9 + 4.3 * math.log10(max(1.0, 76.0 / hfov))
    rf = math.degrees(math.atan(math.hypot(tanh, tanv))) + math.degrees(math.acos(clamp(float(np.dot(f, M31)), -1, 1)))
    mlim = min(mlim, completeness(rf + 0.5) - 1.0, fade_mlim)
    lf = 0.4 * (mlim - m)
    vis = inview & (lf > -0.4)
    idx = np.nonzero(vis)[0]
    lf = lf[idx]
    pk = np.minimum(0.066 * np.power(10.0, 0.72 * lf), 1.7) * gain
    pk = pk * np.clip((lf + 0.4) / 0.3, 0, 1)                            # no popping at the limit
    sig = 0.60 + 0.34 * np.clip(lf - 1.2, 0, None)                        # core sigma (px)
    sig = np.minimum(sig, 2.6)
    hamp = 0.03 * np.clip(lf - 1.8, 0, None) ** 1.3                       # halo amplitude
    hsig = sig * 4.5
    half_px = np.maximum(3.0 * sig, np.where(hamp > 0, 3.0 * hsig, 0))
    half_px = np.maximum(half_px, 1.6)
    kc = 0.5 * (half_px / sig) ** 2                                        # exp(-kc*d2), d2=1 at edge
    kh = 0.5 * (half_px / hsig) ** 2
    n = len(idx)
    dd = d[idx]
    # quad corners: tangent basis per star facing the origin
    zz = np.cross(dd, up[None, :])
    zz /= np.linalg.norm(zz, axis=1, keepdims=True)                       # "right-ish"
    yy = np.cross(zz, dd)
    # world half size: half_px px -> tan units -> world at distance D_STAR (approx. constant near centre)
    hw = (half_px / pxrad) * D_STAR / np.maximum(z[idx], 0.2)
    P = dd * D_STAR / np.maximum(z[idx], 0.2)[:, None] * z[idx][:, None]   # = dd*D_STAR
    P = dd * D_STAR
    corners = np.stack([P - zz * hw[:, None] - yy * hw[:, None], P + zz * hw[:, None] - yy * hw[:, None],
                        P + zz * hw[:, None] + yy * hw[:, None], P - zz * hw[:, None] + yy * hw[:, None]], 1)
    me = STARS.data
    me.clear_geometry()
    for a in list(me.attributes):
        if a.name in ("col", "shp"):
            me.attributes.remove(a)
    if n == 0:
        return 0
    me.vertices.add(n * 4)
    me.vertices.foreach_set("co", corners.reshape(-1).astype(np.float32))
    me.loops.add(n * 4)
    me.loops.foreach_set("vertex_index", np.arange(n * 4, dtype=np.int32))
    me.polygons.add(n)
    me.polygons.foreach_set("loop_start", (np.arange(n, dtype=np.int32) * 4))
    me.polygons.foreach_set("loop_total", np.full(n, 4, np.int32))
    me.update(calc_edges=False)
    uvl = me.uv_layers.new(name="UVMap") if not me.uv_layers else me.uv_layers[0]
    uvs = np.tile(np.array([0, 0, 1, 0, 1, 1, 0, 1], np.float32), n)
    uvl.data.foreach_set("uv", uvs)
    col = np.concatenate([c[idx] * pk[:, None], hamp[:, None]], 1).astype(np.float32)
    shp = np.stack([kc, kh, np.zeros(n), np.ones(n)], 1).astype(np.float32)
    ca = me.color_attributes.new("col", "FLOAT_COLOR", "CORNER")
    ca.data.foreach_set("color", np.repeat(col, 4, axis=0).reshape(-1))
    sa = me.color_attributes.new("shp", "FLOAT_COLOR", "CORNER")
    sa.data.foreach_set("color", np.repeat(shp, 4, axis=0).reshape(-1))
    return n


def update_lines(f, r, up, hfov, alpha):
    me = OBJ["lines"].data
    me.clear_geometry()
    OBJ["lines"].hide_render = alpha <= 0.002
    if alpha <= 0.002:
        return
    tanh = math.tan(math.radians(hfov) / 2)
    radpp = tanh / (RW / 2)                     # tan units per px (centre)
    verts, faces, uvs = [], [], []
    # Andromeda figure + star-hop Mirach -> mu -> nu, which points straight at the marked smudge
    segs = [(np.array(a), np.array(b)) for a, b in META["line_world"]]
    for a, b in segs:
        a = unit(a); b = unit(b)
        gap = 11.0 * radpp
        ang = math.acos(clamp(float(np.dot(a, b)), -1, 1))
        if ang < 3 * gap:
            continue
        # shorten both ends by 'gap' along the great circle
        def slerp(t_):
            return unit(math.sin((1 - t_) * ang) * a + math.sin(t_ * ang) * b)
        ta_, tb_ = gap / ang, 1 - gap / ang
        p0, p1 = slerp(ta_) * D_LINE, slerp(tb_) * D_LINE
        mid = unit(p0 + p1)
        side = unit(np.cross(p1 - p0, mid)) * (1.1 * radpp * D_LINE)
        i0 = len(verts)
        verts += [tuple(p0 - side), tuple(p1 - side), tuple(p1 + side), tuple(p0 + side)]
        faces.append((i0, i0 + 1, i0 + 2, i0 + 3))
        uvs += [(0, 0), (1, 0), (1, 1), (0, 1)]
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for i, uv in enumerate(uvs):
        uvl.data[i].uv = uv


# ---------------------------------------------------------------------------
# per-frame state
# ---------------------------------------------------------------------------
def update(frame):
    sc = bpy.context.scene
    t = (frame - 1) / FPS
    f, r, up, hfov = set_camera(t)

    # opening: black -> brightest stars first -> the full sky (all within ~2 s)
    fade_mlim = lerp(1.5, 12.0, sramp(t, 0.0, 2.0) ** 0.75)
    expo = sramp(t, 0.0, 1.1)
    # ending: fade to black for the chapter cut
    expo *= 1.0 - sramp(t, 58.4, 59.96)
    sc.view_settings.exposure = math.log2(max(expo, 1e-4))
    n = update_stars(t, f, r, up, hfov, fade_mlim, gain=1.0)

    # sky background dims as the "telescope" view takes over (cleaner blacks in the close-up)
    z = math.log(76.0 / hfov) / math.log(76.0 / 8.0)
    dim = lerp(1.0, 0.45, sramp(z, 0.45, 1.0))
    mwf = sramp(hfov, 7.0, 12.0)              # textured sky (Milky Way + airglow + naked-eye M31)
    mw = sramp(t, 0.0, 1.8) * mwf * dim
    bgw = (1.0 - mwf) * dim                   # matching flat background once zoomed in
    set_param("mw", mw)
    set_param("bg", bgw)

    # Andromeda: naked-eye smudge -> long-exposure reveal (24.5-29) -> detailed close-up
    reveal = ramp(t, 24.6, 29.0)
    eye = 0.0                                 # the naked-eye smudge is baked into the sky texture
    lo_w = reveal
    # resolution hand-over with zoom (texture px per screen px stays ~1-2)
    sp_deg = RW / hfov
    k_mid = sramp(sp_deg, 205.0, 265.0)
    k_hi = sramp(sp_deg, 400.0, 470.0)
    a_lo = lo_w * (1 - k_mid)
    a_mid = lo_w * k_mid * (1 - k_hi)
    a_hi = lo_w * k_hi
    # final approach: the galaxy brightens a touch ("it is coming toward us")
    boost = 1.0 + 0.10 * ramp(t, 50.0, 58.0)
    active = (["bg"] if bgw > 0.002 else []) + (["mw"] if mw > 0.0005 else [])
    for k, a in (("eye", eye), ("lo", a_lo * boost), ("mid", a_mid * boost), ("hi", a_hi * boost)):
        set_param(k, a)
        if a > 0.002:
            active.append(k)
    set_world_active(active)

    # Moon outlines: one by one along the major axis, then gone
    for k in range(6):
        a = window(t, 25.8 + 0.42 * k, 32.4, 0.55, 1.0) * 0.85
        set_param(f"moon{k}", a)
        OBJ[f"moon{k}"].hide_render = a <= 0.002
    # constellation figure + marker on the smudge while it is introduced
    la = window(t, 8.3, 14.6, 1.2, 1.6) * 0.55
    update_lines(f, r, up, hfov, la)
    set_param("lines", la)
    ma = window(t, 9.6, 14.6, 1.0, 1.6) * 0.55
    set_param("marker", ma)
    OBJ["marker"].hide_render = ma <= 0.002

    # landscape is culled once out of view
    for k in ("far", "mid", "near", "tree"):
        OBJ[k].hide_render = t > 18.0

    for tid, body, t0, t1 in CAPTIONS:
        set_alpha(tid, window(t, t0, t1, 0.8, 0.9) * 0.92)
    return n


# ---------------------------------------------------------------------------
def main():
    global ROLL_TARGET
    sc = reset_scene()
    build()
    build_texts()
    ROLL_TARGET = compute_roll_target()
    out = arg("--out", CONFIG["output"])
    os.makedirs(out, exist_ok=True)
    print(f"[ch1] {NF} frames -> {out}  M31 alt {M31_ALT:.1f} az {M31_AZ:.1f}  roll {math.degrees(ROLL_TARGET):.1f}")
    frames = []
    if arg("--frames"):
        frames = [int(v) for v in arg("--frames").split(",")]
    elif "--render" in ARGV:
        a = int(arg("--start", 1)); e = int(arg("--end", NF)); st = int(arg("--step", 1))
        frames = list(range(a, e + 1, st))
    skip = "--skip-existing" in ARGV
    if "--blend" in ARGV:
        update(int(arg("--blend")))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "..", "ch1_debug.blend"))
    for fr in frames:
        path = os.path.join(out, f"f_{fr:04d}.png")
        if skip and os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        t0 = time.time()
        sc.frame_set(fr)
        n = update(fr)
        t1 = time.time()
        tmp = path[:-4] + "_tmp.png"
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, path)
        print(f"frame {fr} {time.time() - t0:.2f}s (update {t1 - t0:.2f}s) stars={n}", flush=True)


main()
