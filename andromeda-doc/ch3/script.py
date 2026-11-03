"""
ANDROMEDA documentary - CHAPTER 3 "THE SKY CHANGES" (2:00-3:00), 60.0 s, 1440 frames, 1920x1080 @ 24 fps.

The ridge and the lone wind-bent tree, while billions of years pass (IF THEY MERGE).
Andromeda grows from a small oval into a sky-spanning, tilted spiral with crisp dust lanes;
then our own Milky Way band bends; the shot ends on a slow tilt up toward the zenith.

Everything heavy is pre-baked by gen_textures.py (numpy) into 8-bit PNGs; this scene is just
a world shader (alt-az star map + Milky Way map in galactic coords, warpable), one emission
plane for Andromeda (LOD-blended textures), black ridge/tree geometry and Inter Light text.

Run (bpy module):
  /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--frames','30,400,820']; exec(compile(open(p).read(),p,'exec'))"
  ... '--render','--skip-existing' [--start N --end M --step K] [--threads T] [--out DIR]
"""
CONFIG = dict(
    fps=24,
    duration=60.0,
    resolution=(1920, 1080),
    samples=int(__import__("os").environ.get("CH3_SPP", "4")),
    threads=1,
    output="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/ch3/frames",
    textures="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures",
    font_name="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_thin="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
)

import sys
import os
import json
import math
import time

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
N_FRAMES = int(round(CONFIG["duration"] * FPS))
TEX = CONFIG["textures"]
META = json.load(open(os.path.join(TEX, "ch3_meta.json")))
SENSOR_W = 36.0
ASPECT = CONFIG["resolution"][1] / CONFIG["resolution"][0]
REF_LENS = 20.0
TEXT_COL = (0.88, 0.86, 0.84)
ACCENT = (0.80, 0.70, 1.00)


# ---------------------------------------------------------------------------
# timeline helpers
# ---------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(a):
    a = clamp(a)
    return a * a * a * (a * (a * 6 - 15) + 10)


def smooth(a):
    a = clamp(a)
    return a * a * (3 - 2 * a)


def lerp(a, b, t):
    return a + (b - a) * t


def keys(ts, ks, fn=smooth):
    """piecewise interpolation through (t, value) keys with eased segments"""
    if ts <= ks[0][0]:
        return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if ts <= t1:
            return lerp(v0, v1, fn((ts - t0) / (t1 - t0)))
    return ks[-1][1]


def window(ts, t_in, t_out, fin=0.6, fout=0.6):
    if ts < t_in or ts > t_out + fout:
        return 0.0
    a = smooth((ts - t_in) / fin) if fin > 0 else 1.0
    b = 1.0 - smooth((ts - t_out) / fout) if ts > t_out else 1.0
    return clamp(min(a, b))


# Narration (chapter seconds):  1.0 two billion years | 8.0 night after night ... swell (~11)
# 17.0 arms / dust / core | 26.0 fill the sky | 37.0 Milky Way bends | 47.0 falling into one another
YEAR_KEYS = [(0.0, 1.00), (5.0, 2.00), (8.0, 2.03), (11.0, 2.10), (17.0, 2.60), (25.0, 3.05),
             (32.0, 3.60), (36.0, 3.75), (47.0, 3.83), (60.0, 3.90)]
# Andromeda angular width (deg, full texture width; the bright disk is ~85% of it)
WIDTH_KEYS = [(0.0, 8.0), (5.0, 15.0), (11.0, 17.5), (17.0, 34.0), (25.0, 62.0), (31.0, 112.0),
              (37.0, 122.0), (47.0, 128.0), (60.0, 134.0)]
# camera: (t, yaw, pitch, lens)
CAM_KEYS = [(0.0, 0.0, 10.5, 20.0), (17.0, 0.0, 11.0, 20.0), (24.0, 6.5, 19.0, 30.0),
            (25.5, 6.0, 18.0, 29.0), (31.0, 0.0, 11.0, 17.0), (37.0, 0.0, 11.5, 16.5),
            (46.5, -17.0, 15.0, 16.5), (59.5, -9.0, 43.0, 16.5), (60.0, -9.0, 43.0, 16.5)]


def cam_at(ts):
    ks = CAM_KEYS
    for a, b in zip(ks, ks[1:]):
        if ts <= b[0]:
            u = clamp((ts - a[0]) / (b[0] - a[0]))
            # long segments use gentle ease, the push-in and pull-back are eased fully
            u = ease(u)
            return tuple(lerp(a[i], b[i], u) for i in (1, 2, 3))
    return ks[-1][1:]


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, N_FRAMES
    sc.render.resolution_x, sc.render.resolution_y = CONFIG["resolution"]
    sc.render.resolution_percentage = 100
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = CONFIG["samples"]
    cy.use_adaptive_sampling = False
    cy.use_denoising = False
    cy.max_bounces = 0
    cy.diffuse_bounces = cy.glossy_bounces = cy.transmission_bounces = cy.volume_bounces = 0
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = cy.caustics_refractive = False
    for k, v in (("use_light_tree", False), ("pixel_filter_width", 1.15), ("seed", 3)):
        try:
            setattr(cy, k, v)
        except Exception:
            pass
    th = int(arg("--threads", CONFIG["threads"]))
    if th:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = th
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            pass
    ims = sc.render.image_settings
    try:
        ims.media_type = "IMAGE"
    except Exception:
        pass
    ims.file_format = "PNG"
    ims.color_mode = "RGB"
    ims.color_depth = "8"
    try:
        sc.render.use_persistent_data = True
    except Exception:
        pass
    return sc


class NB:
    def __init__(self, nt, out):
        self.nt = nt
        self.out = out

    def n(self, t, **props):
        node = self.nt.nodes.new(t)
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def _set(self, sock, v):
        if isinstance(v, (int, float, tuple)):
            sock.default_value = v
        else:
            self.link(v, sock)

    def m(self, op, a, b=None, c=None):
        node = self.n("ShaderNodeMath", operation=op)
        for s, v in zip(node.inputs, (a, b, c)):
            if v is not None:
                self._set(s, v)
        return node.outputs[0]

    def vm(self, op, a, b=None, scale=None):
        node = self.n("ShaderNodeVectorMath", operation=op)
        self._set(node.inputs[0], a)
        if b is not None:
            self._set(node.inputs[1], b)
        if scale is not None:
            self._set(node.inputs["Scale"], scale)
        return node.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH") else node.outputs["Vector"]

    def combine(self, x, y, z=0.0):
        c = self.n("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._set(c.inputs[i], v)
        return c.outputs[0]

    def sep(self, v):
        s = self.n("ShaderNodeSeparateXYZ")
        self.link(v, s.inputs[0])
        return s.outputs[0], s.outputs[1], s.outputs[2]

    def value(self, v=0.0):
        node = self.n("ShaderNodeValue")
        node.outputs[0].default_value = v
        return node.outputs[0]

    def image(self, img, vec, interp="Linear", ext="CLIP"):
        t = self.n("ShaderNodeTexImage")
        t.image = img
        t.interpolation = interp
        t.extension = ext
        self.link(vec, t.inputs["Vector"])
        return t, t.outputs["Color"]

    def madd(self, a, b, c):
        return self.m("MULTIPLY_ADD", a, b, c)

    def mixv(self, fac, a, b):
        node = self.n("ShaderNodeMix", data_type="VECTOR")
        self._set(node.inputs["Factor"], fac)
        self._set(node.inputs[4], a)   # A_Vector
        self._set(node.inputs[5], b)   # B_Vector
        return node.outputs[1]

    def atmo(self, sinalt):
        """(extinction colour, airglow colour*50) from the baked 1D LUT"""
        z = self.m("MAXIMUM", sinalt, 0.0)
        _, ext = self.image(ATMO, self.combine(z, 0.75, 0.0), ext="EXTEND")
        _, glow = self.image(ATMO, self.combine(z, 0.25, 0.0), ext="EXTEND")
        return ext, glow


PARAM = {}          # name -> default value
PARAM_OBJS = []     # objects whose materials read animated params


def P(b, name, v=0.0):
    """Animated scalar read from an object custom property (Attribute node, OBJECT type).
    Changing a custom property does not recompile shaders, unlike Value-node defaults
    (that recompile cost ~4 s/frame)."""
    PARAM.setdefault(name, v)
    node = b.n("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="p_" + name)
    return node.outputs["Fac"]


def PV(b, name):
    node = b.n("ShaderNodeAttribute", attribute_type="OBJECT", attribute_name="p_" + name)
    return node.outputs["Vector"]


def set_vparam(name, v):
    for ob in PARAM_OBJS:
        ob["p_" + name] = [float(c) for c in v]


def set_param(name, v):
    for ob in PARAM_OBJS:
        if ob.get("p_" + name) != v:
            ob["p_" + name] = float(v)


def load(name):
    img = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    img.colorspace_settings.name = "sRGB"        # textures are stored as sRGB(L / Lmax)
    img.alpha_mode = "CHANNEL_PACKED"
    return img


IMG_NODES = {}
M31_LODS = []
ATMO = None


def build_sky():
    """Sky dome (a big sphere around the camera) instead of a world shader, so its
    animated params can be object attributes. Direction = normalised hit position."""
    w = bpy.data.worlds.new("Void")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    bpy.context.scene.world = w
    mat = bpy.data.materials.new("M_sky")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = NB(nt, out)
    geo = b.n("ShaderNodeNewGeometry")
    d = b.vm("NORMALIZE", geo.outputs["Position"])
    dx, dy, dz = b.sep(d)
    # alt-az star map
    p0, p1 = math.radians(META["star_pmin"]), math.radians(META["star_pmax"])
    u = b.madd(b.m("ARCTAN2", dx, dy), 1 / (2 * math.pi), 0.5)
    v = b.madd(b.m("ARCSINE", dz), 1 / (p1 - p0), -p0 / (p1 - p0))
    _, stars = b.image(load("ch3_stars.png"), b.combine(u, v, 0.0), ext="EXTEND")
    stars = b.vm("SCALE", stars, scale=P(b, "star_gain", 1.0))

    # Milky Way in galactic coordinates, with a tidal S-bend + thickening near Andromeda
    gx = b.vm("DOT_PRODUCT", d, tuple(META["gx"]))
    gy = b.vm("DOT_PRODUCT", d, tuple(META["gy"]))
    gz = b.vm("DOT_PRODUCT", d, tuple(META["gz"]))
    l = b.m("ARCTAN2", gy, gx)
    bb = b.m("ARCSINE", gz)

    def lgauss(l_c, width):
        # ~exp(-((l - l_c)/width)^2) along the band, from one dot product
        vx = tuple(math.cos(l_c) * META["gx"][i] + math.sin(l_c) * META["gy"][i] for i in range(3))
        dd = b.vm("DOT_PRODUCT", d, vx)
        return b.m("EXPONENT", b.madd(dd, 2.0 / width ** 2, -2.0 / width ** 2))

    g = lgauss(MW_BEND["l0"], math.radians(42.0))
    g2 = lgauss(MW_BEND["l0"] + math.radians(48.0), math.radians(32.0))
    shift = b.madd(g, P(b, "mw_shiftA"), b.m("MULTIPLY", g2, P(b, "mw_shiftB")))
    thick = b.madd(g, P(b, "mw_thick"), 1.0)
    b2 = b.m("DIVIDE", b.m("SUBTRACT", bb, shift), thick)
    bmax = math.radians(META["mw_bmax"])
    mu = b.madd(l, 1 / (2 * math.pi), 0.5)
    mv = b.madd(b2, 1 / (2 * bmax), 0.5)
    tmw, mw = b.image(load("ch3_mw.png"), b.combine(mu, mv, 0.0), ext="CLIP")
    mw_opac = tmw.outputs["Alpha"]
    mw = b.vm("SCALE", mw, scale=P(b, "mw_gain", 1.0))
    # Andromeda: gnomonic projection of the view direction onto the galaxy's tangent plane
    # (axes pre-scaled per frame so u,v land in 0..1), two LOD levels blended.
    dn = b.vm("DOT_PRODUCT", d, PV(b, "m31n"))
    gu = b.m("ADD", b.m("DIVIDE", b.vm("DOT_PRODUCT", d, PV(b, "m31x")), dn), 0.5)
    gv = b.m("ADD", b.m("DIVIDE", b.vm("DOT_PRODUCT", d, PV(b, "m31y")), dn), 0.5)
    guv = b.combine(gu, gv, 0.0)
    ta, ca = b.image(M31_LODS[0], guv)
    tb, cb = b.image(M31_LODS[1], guv)
    IMG_NODES["m31_a"], IMG_NODES["m31_b"] = ta, tb
    gal = b.mixv(P(b, "m31_lodmix", 0.0), ca, cb)
    front = b.m("MULTIPLY", b.m("GREATER_THAN", dn, 0.05), P(b, "m31_gain", 1.0))
    front = b.m("MULTIPLY", front, b.m("SUBTRACT", 1.0, b.m("MULTIPLY", mw_opac, 0.85)))
    gal = b.vm("SCALE", gal, scale=front)

    ext, glow = b.atmo(dz)
    sky = b.vm("MULTIPLY", b.vm("ADD", b.vm("ADD", stars, mw), gal), ext)
    sky = b.vm("ADD", sky, b.vm("SCALE", glow, scale=P(b, "glow_gain", 0.02)))
    em = b.n("ShaderNodeEmission")
    b.link(sky, em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    b.link(em.outputs[0], out.inputs["Surface"])
    me = bpy.data.meshes.new("dome")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=8000.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new("dome", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mat_emit(name, color, param=None, grad=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = NB(nt, out)
    em = b.n("ShaderNodeEmission")
    if grad:
        # far ridge: faint haze glow brightest at its crest (local z near top)
        tc = b.n("ShaderNodeTexCoord")
        z = b.sep(tc.outputs["Generated"])[2]
        g = b.m("POWER", z, 40.0)
        c = b.vm("SCALE", color, scale=b.m("MULTIPLY", b.m("ADD", b.m("MULTIPLY", g, 0.8), 0.2), P(b, param, 1.0)))
        b.link(c, em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (*color, 1)
    b.link(em.outputs[0], out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def plane(name, mat):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bm.to_mesh(me)
    bm.free()
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


def ridge(name, y, z_top, amp, wid, seed, mat, nseg=900, bottom=-400.0, freq=3.0):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(nseg + 1):
        xx = -wid + 2 * wid * i / nseg
        zz = z_top + amp * fbm1(xx / wid * freq, seed)
        verts += [(xx, y + 0.0 * xx, zz), (xx, y, bottom)]
    for i in range(nseg):
        a, c = 2 * i, 2 * i + 2
        faces.append((a + 1, c + 1, c, a))
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def tree(name, base, height, mat):
    """Bare, wind-bent tree (recursive tapered cones), leaning right as in the series look."""
    import random
    rnd = random.Random(11)
    bm = bmesh.new()
    WIND = Vector((1.0, 0.0, 0.0))

    def seg(p, q, r0, r1):
        d = (q - p)
        L = d.length
        d.normalize()
        mtx = Matrix.Translation((p + q) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=r0, radius2=r1, depth=L * 1.06, matrix=mtx)

    def branch(p, d, length, rad, depth):
        # each branch is 3 slightly curving sub-segments bending downwind
        n = 3
        cur, dd = p.copy(), d.copy()
        r = rad
        for i in range(n):
            dd = (dd + WIND * 0.045 * (1.0 + (6 - depth) * 0.10) + Vector((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.05, 0.05), -0.012 * (6 - depth)))).normalized()
            nxt = cur + dd * (length / n)
            seg(cur, nxt, r, r * 0.86)
            cur, r = nxt, r * 0.86
        if depth == 0 or rad < 0.010:
            return
        kids = rnd.choice((2, 2, 3))
        for k in range(kids):
            side = rnd.uniform(-1.0, 1.0)
            ax = Vector((side, rnd.uniform(-0.5, 0.5), rnd.uniform(0.25, 0.9)))
            nd = (dd * 0.75 + ax * rnd.uniform(0.5, 0.9) + WIND * 0.18).normalized()
            if nd.z < -0.15:
                nd.z = -0.15
                nd.normalize()
            branch(cur, nd, length * rnd.uniform(0.60, 0.78), r * rnd.uniform(0.55, 0.72), depth - 1)

    # trunk: leaning downwind, slight S-curve
    p = Vector(base) - Vector((0, 0, 0.8))
    pts = [p]
    for i, (dx, dz) in enumerate(((0.05, 1.0), (0.22, 1.0), (0.38, 1.0), (0.55, 0.9))):
        p = p + Vector((dx, 0, dz)).normalized() * height * 0.13
        pts.append(p)
    rad = height * 0.030
    for a, c in zip(pts, pts[1:]):
        seg(a, c, rad, rad * 0.88)
        rad *= 0.88
    top = pts[-1]
    # main limbs
    for ang, lf in ((-0.75, 0.38), (-0.2, 0.46), (0.3, 0.48), (0.85, 0.42)):
        d = Vector((math.sin(ang) * 0.9 + 0.25, rnd.uniform(-0.3, 0.3), math.cos(ang))).normalized()
        branch(top, d, height * lf * 0.55, rad * 0.72, 6)
    # a low limb from the trunk
    branch(pts[2], Vector((0.9, 0.1, 0.6)).normalized(), height * 0.26, rad * 0.75, 5)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def sdir(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return Vector((math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)))


# Andromeda direction over time: (t, yaw, pitch, position angle deg)
POS_KEYS = [(0.0, 17.0, 23.0, 36.0), (11.0, 15.0, 23.5, 34.0), (17.0, 12.0, 24.0, 32.0),
            (25.0, 8.0, 22.0, 28.0), (31.0, 3.0, 19.0, 22.0), (60.0, 1.0, 19.5, 20.0)]


def m31_pos(ts):
    ks = POS_KEYS
    for a, c in zip(ks, ks[1:]):
        if ts <= c[0]:
            u = smooth((ts - a[0]) / (c[0] - a[0]))
            return tuple(lerp(a[i], c[i], u) for i in (1, 2, 3))
    return ks[-1][1:]


def place_m31(yaw, pitch, width_deg, pa_deg):
    """Set the sky-dome attributes that project Andromeda's texture onto the sky.
    Returns tan(half width)."""
    d = sdir(yaw, pitch)
    right = Vector((math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)), 0.0))
    up = right.cross(d)
    ca, sa = math.cos(math.radians(pa_deg)), math.sin(math.radians(pa_deg))
    xa = right * ca + up * sa
    ya = -right * sa + up * ca
    th = math.tan(math.radians(min(width_deg, 160.0)) / 2)
    asp = META["m31_h"] / META["m31_w"]
    set_vparam("m31n", d)
    set_vparam("m31x", xa / (2 * th))
    set_vparam("m31y", ya / (2 * th * asp))
    return th


def bend_setup():
    """Where the Milky Way band passes closest to Andromeda: bend centre in galactic l,
    and the sign so the band is pulled toward M31."""
    gx, gy, gz = (Vector(META[k]) for k in ("gx", "gy", "gz"))
    yaw, pitch, _ = m31_pos(40.0)
    m = sdir(yaw, pitch)
    l_m = math.atan2(m.dot(gy), m.dot(gx))
    b_m = math.asin(max(-1, min(1, m.dot(gz))))
    sgn = 1.0 if b_m > 0 else -1.0
    # shift is subtracted from b in the lookup, so a positive shift moves the band toward +b
    l0 = l_m + math.radians(-8.0)
    return dict(l0=l0, amp=sgn * math.radians(24.0), sgn_l=1.0, b_m=math.degrees(b_m), l_m=math.degrees(l_m))


MW_BEND = {}
MW_GAIN = 2.0
OBJ = {}
TEXTS = {}
FONTS = {}


def font(path):
    if path not in FONTS:
        try:
            FONTS[path] = bpy.data.fonts.load(path)
        except Exception:
            FONTS[path] = None
    return FONTS[path]


def text_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return mat, mx


def make_text(tid, body, frac_y, size, spacing, color, thin=False):
    cu = bpy.data.curves.new(tid, "FONT")
    cu.body = body
    f = font(CONFIG["font_thin"] if thin else CONFIG["font_name"])
    if f:
        cu.font = f
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    cu.space_character = spacing
    ob = bpy.data.objects.new(tid, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = HUD
    tanv = (SENSOR_W / 2 / REF_LENS) * ASPECT
    ob.location = (0, (frac_y - 0.5) * 2 * tanv, 0)
    mat, mx = text_material("MT_" + tid, color)
    cu.materials.append(mat)
    TEXTS[tid] = (ob, mx)


def set_alpha(tid, a):
    ob, mx = TEXTS[tid]
    mx.inputs[0].default_value = a
    ob.hide_render = a <= 0.002


def build():
    global CAM, HUD
    MW_BEND.update(bend_setup())
    print("[ch3] MW bend:", {k: round(v, 3) for k, v in MW_BEND.items()})
    global ATMO
    ATMO = load("ch3_atmo.png")
    for i in range(5):
        M31_LODS.append(load(f"ch3_m31_L{i}.png"))
    OBJ["dome"] = build_sky()

    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = SENSOR_W
    cd.lens = REF_LENS
    cd.clip_start = 0.05
    cd.clip_end = 20000.0
    CAM = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(CAM)
    bpy.context.scene.camera = CAM
    HUD = bpy.data.objects.new("HUD", None)
    bpy.context.scene.collection.objects.link(HUD)
    HUD.parent = CAM
    HUD.location = (0, 0, -1.0)


    black = mat_emit("M_black", (0.0, 0.0, 0.0))
    haze = mat_emit("M_haze", (0.020, 0.018, 0.036), "haze", grad=True)
    OBJ["far"] = ridge("ridge_far", 900.0, -62.0, 34.0, 1500.0, 4.0, haze, freq=7.0)
    OBJ["mid"] = ridge("ridge_mid", 330.0, -30.0, 9.0, 700.0, 9.0, mat_emit("M_mid", (0.006, 0.0055, 0.011), "haze", grad=True), freq=6.0)
    near_top, near_amp, near_w = -9.5, 2.4, 160.0
    OBJ["near"] = ridge("ridge_near", 80.0, near_top, near_amp, near_w, 1.0, black, freq=3.2)
    tx = -25.0
    tz = near_top + near_amp * fbm1(tx / near_w * 3.2, 1.0)
    OBJ["tree"] = tree("tree", (tx, 80.0, tz), 21.0, black)
    PARAM_OBJS.extend([OBJ["dome"], OBJ["far"], OBJ["mid"]])
    for k, v in PARAM.items():
        set_param(k, v)

    make_text("year", "+ 1.00 BILLION YEARS", 0.915, 0.0235, 1.55, (0.84, 0.82, 0.90))
    make_text("ifm", "IF THEY MERGE", 0.878, 0.0155, 2.0, (0.74, 0.66, 0.90))


# ---------------------------------------------------------------------------
def update(frame):
    sc = bpy.context.scene
    ts = (frame - 1) / FPS

    yaw, pitch, lens = cam_at(ts)
    CAM.rotation_euler = (math.radians(90 + pitch), 0, math.radians(-yaw))
    CAM.data.lens = lens
    HUD.location = (0, 0, -lens / REF_LENS)        # keep captions a constant size while zooming
    tanh = SENSOR_W / 2 / lens
    # --- Andromeda --------------------------------------------------------
    width = keys(ts, WIDTH_KEYS)
    my, mp, pa = m31_pos(ts)
    th = place_m31(my, mp, width, pa)
    screen_w = 2 * th * 960 / tanh                    # px across the texture (at its centre)
    lod = clamp(math.log2(max(1.0, META["m31_w"] / max(screen_w, 1.0)) / 1.15), 0.0, 4.0)
    # LOD: single lookup of the nearest level except inside a transition band, where two
    # levels are blended (material slot 1). Avoids sharpness pops at a fraction of the cost.
    l0 = min(3, int(math.floor(lod)))
    fr = clamp(lod - l0)
    na, nb_ = IMG_NODES["m31_a"], IMG_NODES["m31_b"]
    if na.image != M31_LODS[l0]:
        na.image = M31_LODS[l0]
    if nb_.image != M31_LODS[l0 + 1]:
        nb_.image = M31_LODS[l0 + 1]
    set_param("m31_lodmix", fr)
    # surface brightness: faint at first (a naked-eye oval), then vivid
    br = keys(ts, [(0.0, 0.85), (5.0, 1.2), (11.0, 1.3), (17.0, 1.9), (25.0, 2.1), (31.0, 2.2), (60.0, 2.2)])
    master = smooth(ts / 1.4)                      # fade in from black
    set_param("m31_gain", META["m31_lmax"] * br * master)

    # --- Milky Way: bends toward Andromeda from ~37 s ------------------------
    warp = keys(ts, [(0.0, 0.0), (37.0, 0.0), (47.0, 1.0), (60.0, 1.35)])
    set_param("mw_shiftA", warp * MW_BEND["amp"])
    set_param("mw_shiftB", -warp * MW_BEND["amp"] * 0.45)
    set_param("mw_thick", warp * 0.55)
    set_param("mw_gain", META["mw_lmax"] * MW_GAIN * (1.0 + 0.25 * warp) * master)
    set_param("star_gain", META["star_lmax"] * master)
    big = smooth((width - 30) / 90.0)
    set_param("glow_gain", 0.02 * (1.0 + 0.8 * big) * master)
    set_param("haze", (1.0 + 1.0 * big) * master)

    # --- captions ------------------------------------------------------------
    yv = keys(ts, YEAR_KEYS, fn=lambda a: a * a * (3 - 2 * a) * 0.4 + a * 0.6)
    ob, _ = TEXTS["year"]
    ob.data.body = f"+ {yv:.2f} BILLION YEARS"
    set_alpha("year", window(ts, 0.5, 60.0, 0.9, 0.5) * 0.92)
    set_alpha("ifm", window(ts, 1.1, 60.0, 1.0, 0.5) * 0.9)
    # custom-property changes are not seen by Cycles' persistent data unless the objects
    # are tagged for update
    for ob in PARAM_OBJS:
        ob.update_tag()
    return dict(ts=ts, width=width, lod=lod, lens=lens, pitch=pitch)


def main():
    sc = reset_scene()
    build()
    out = arg("--out", CONFIG["output"])
    os.makedirs(out, exist_ok=True)
    frames = []
    if arg("--frames"):
        frames = [int(v) for v in arg("--frames").split(",")]
    elif "--render" in ARGV:
        a = int(arg("--start", 1)); e = int(arg("--end", N_FRAMES)); st = int(arg("--step", 1))
        frames = list(range(a, e + 1, st))
    skip = "--skip-existing" in ARGV
    if "--blend" in ARGV:
        update(int(arg("--blend-frame", 1)))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "ch3.blend"))
    print(f"[ch3] {N_FRAMES} frames -> {out}; rendering {len(frames)}", flush=True)
    for f in frames:
        path = os.path.join(out, f"f_{f:04d}.png")
        if skip and os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        t0 = time.time()
        sc.frame_set(f)
        info = update(f)
        tmp = path[:-4] + "_tmp.png"
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, path)
        print(f"frame {f} {time.time() - t0:.2f}s  t={info['ts']:.2f} w={info['width']:.1f} lod={info['lod']:.2f}", flush=True)


main()
