"""
ANDROMEDA documentary - CH4 "MILKOMEDA" (3:00-4:00), 60.0 s, 1440 frames, 1920x1080 @ 24 fps.

Opens exactly where CH3 ends (camera tilted up toward the zenith, the giant tilted Andromeda,
the Milky Way band bending), tilts back down to the ridge and the bare tree while the two
galaxies tear into each other: tidal tails, a sky-wide starburst of pink star-forming knots,
the two bright cores circling; they settle into one smooth glowing elliptical (Milkomeda);
the camera rises off the ground into space, the elliptical shrinks to a lone galaxy, fade to
black, title card "THE SKY THAT'S COMING".

Render design (CPU Cycles, fast):
* One sky dome (sphere around the camera, emission only). Its shader turns the view direction
  into (a) CH3's alt-az star map and galactic Milky Way map (shared texture cache, read-only,
  so the cut from CH3 is seamless) and (b) a gnomonic "sky plane" coordinate S in which CH4's
  own pre-baked numpy textures (gen_textures.py -> ch4_*.png) are placed, rotated, scaled and
  warped by cheap math.
* Every animated value is an object custom property read by Attribute nodes, so changing it per
  frame does NOT recompile the shader (Value-node edits recompile, ~seconds/frame).
* Layers that are fully off are skipped through Mix Shader gates (factor exactly 0).
* CH3's own Andromeda plane is kept for the first seconds and cross-fades into CH4's
  tidally-twisted Andromeda layer.
* Ridge + tree: black meshes (same construction/placement as CH3). Captions: Inter text on a HUD.

Run (bpy module):
  /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--frames','1,300,700']; exec(compile(open(p).read(),p,'exec'))"
  ... '--render' [--skip-existing] [--start N --end M --step S] [--threads T] [--samples S] [--out DIR]
"""
import sys
import os
import json
import math
import time

import bpy
import bmesh
from mathutils import Vector, Matrix

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda"
CONFIG = dict(
    fps=24,
    n_frames=1440,
    resolution=(1920, 1080),
    samples=2,
    threads=1,
    textures=SCR + "/textures",
    output=SCR + "/ch4/frames",
    font_name="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_thin="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
)

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV):
            return ARGV[i + 1]
    return default


FPS = CONFIG["fps"]
N_FRAMES = CONFIG["n_frames"]
RX, RY = CONFIG["resolution"]
TEX = CONFIG["textures"]
META = json.load(open(os.path.join(TEX, "ch3_meta.json")))

# ---------------------------------------------------------------------------
# CH3 continuity: CH3's last frame (t = 1439/24 s) is re-derived from ch3/script.py itself
# (its key tables are parsed read-only with ast/regex), so the cut stays seamless even if
# CH3 is re-tuned. The defaults below are used only if parsing fails.
# ---------------------------------------------------------------------------
SENSOR_W = 36.0
REF_LENS = 20.0
ASPECT = RY / RX
CH3_SCRIPT = "/home/user/do-my-task/andromeda-doc/ch3/script.py"
CH3 = dict(
    CAM_KEYS=[(0.0, -9.0, 43.0, 16.5)],
    POS_KEYS=[(0.0, 17.0, 23.0, 36.0), (11.0, 15.0, 23.5, 34.0), (17.0, 12.0, 24.0, 32.0),
              (25.0, 8.0, 22.0, 28.0), (31.0, 3.0, 19.0, 22.0), (60.0, 1.0, 19.5, 20.0)],
    WIDTH_KEYS=[(0.0, 134.0)], YEAR_KEYS=[(0.0, 3.90)], MW_GAIN=2.0,
    BR=[(0.0, 2.2)], WARP=[(0.0, 1.35)],
    far=(900.0, -62.0, 34.0, 1500.0, 4.0, 7.0), mid=(330.0, -30.0, 9.0, 700.0, 9.0, 6.0),
    near=(80.0, -9.5, 2.4, 160.0, 1.0, 3.2), tree_x=-25.0, tree_h=21.0,
    ifm=(0.878, 0.0155, 2.0, (0.74, 0.66, 0.90)),
)


def ch3_sync():
    import ast
    import re
    try:
        src = open(CH3_SCRIPT).read()
    except Exception as ex:
        print("[ch4] CH3 sync: using defaults (", ex, ")")
        return
    tree_ = ast.parse(src)
    for node in tree_.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
            if nm in ("CAM_KEYS", "POS_KEYS", "WIDTH_KEYS", "YEAR_KEYS", "MW_GAIN"):
                try:
                    CH3[nm] = ast.literal_eval(node.value)
                except Exception:
                    pass

    def grab(pat, conv=ast.literal_eval):
        m = re.search(pat, src)
        if m:
            try:
                return conv(m.group(1))
            except Exception:
                return None
        return None

    v = grab(r"\bbr = keys\(ts, (\[[^\]]*\])")
    if v:
        CH3["BR"] = v
    v = grab(r"\bwarp = keys\(ts, (\[[^\]]*\])")
    if v:
        CH3["WARP"] = v
    for nm in ("far", "mid"):
        m = re.search(r'ridge\("ridge_%s", ([-\d.]+), ([-\d.]+), ([-\d.]+), ([-\d.]+), ([-\d.]+), .*?freq=([-\d.]+)\)' % nm, src)
        if m:
            CH3[nm] = tuple(float(x) for x in m.groups())
    m = re.search(r"near_top, near_amp, near_w = ([-\d.]+), ([-\d.]+), ([-\d.]+)", src)
    m2 = re.search(r'ridge\("ridge_near", ([-\d.]+), near_top, near_amp, near_w, ([-\d.]+), black, freq=([-\d.]+)\)', src)
    if m and m2:
        CH3["near"] = (float(m2.group(1)), float(m.group(1)), float(m.group(2)), float(m.group(3)),
                       float(m2.group(2)), float(m2.group(3)))
    v = grab(r"\n    tx = ([-\d.]+)", float)
    if v is not None:
        CH3["tree_x"] = v
    v = grab(r'tree\("tree", \(tx, [-\d.]+, tz\), ([-\d.]+)', float)
    if v is not None:
        CH3["tree_h"] = v
    m = re.search(r'make_text\("ifm", "IF THEY MERGE", ([-\d.]+), ([-\d.]+), ([-\d.]+), (\([^)]*\))', src)
    if m:
        CH3["ifm"] = (float(m.group(1)), float(m.group(2)), float(m.group(3)), ast.literal_eval(m.group(4)))
    # reuse CH3's own landscape builders verbatim (same ridge profile and the same tree)
    funcs = {}
    for node in tree_.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("fbm1", "ridge", "tree"):
            funcs[node.name] = ast.get_source_segment(src, node)
    CH3["funcs"] = funcs
    print("[ch4] CH3 sync ok:", sorted(funcs))


ch3_sync()
TEXT_COL = (0.88, 0.86, 0.84)
ACCENT = (0.80, 0.70, 1.00)

# gnomonic sky frame for CH4's own layers: centred on yaw 0, elevation E0
E0 = 30.0
N_AX = (0.0, math.cos(math.radians(E0)), math.sin(math.radians(E0)))
EX_AX = (1.0, 0.0, 0.0)
EY_AX = (0.0, -math.sin(math.radians(E0)), math.cos(math.radians(E0)))
SU = 0.6                                       # 1 sky unit = tan-distance 0.6


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(a):
    a = clamp(a)
    return a * a * (3 - 2 * a)


def ease(a):
    a = clamp(a)
    return a * a * a * (a * (a * 6 - 15) + 10)


def ramp(ts, t0, t1):
    return ease((ts - t0) / max(1e-6, t1 - t0))


def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


def keys(ts, ks, fn=smooth):
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


def sdir(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return Vector((math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)))


def sky_S(yaw, pitch):
    """direction -> CH4 sky-plane coordinates (units of SU)."""
    d = sdir(yaw, pitch)
    k = d.dot(Vector(N_AX))
    return (d.dot(Vector(EX_AX)) / k / SU, d.dot(Vector(EY_AX)) / k / SU)


# ---- CH3 end state (its last rendered frame) --------------------------------
T3 = 1439.0 / 24.0


def _seg(ts, ks, fn):
    for a, c in zip(ks, ks[1:]):
        if ts <= c[0]:
            u = fn(clamp((ts - a[0]) / (c[0] - a[0])))
            return tuple(lerp(a[i], c[i], u) for i in range(1, len(a)))
    return tuple(ks[-1][1:])


CH3_CAM_END = _seg(T3, CH3["CAM_KEYS"], ease)                 # yaw, pitch, lens
_p = _seg(T3, CH3["POS_KEYS"], smooth)                         # yaw, pitch, pa
CH3_M31_END = (_p[0], _p[1], _p[2], keys(T3, CH3["WIDTH_KEYS"]))
CH3_POS_KEYS = CH3["POS_KEYS"]
CH3_M31_GAIN = META["m31_lmax"] * keys(T3, CH3["BR"])
CH3_WARP_END = keys(T3, CH3["WARP"])
CH3_MW_GAIN = CH3["MW_GAIN"]
CH3_YEAR_END = keys(T3, CH3["YEAR_KEYS"], fn=lambda a: a * a * (3 - 2 * a) * 0.4 + a * 0.6)
CH3_HAZE_END = 2.0
CH3_GLOW_END = 0.02 * 1.8
print("[ch4] CH3 end: cam", [round(x, 2) for x in CH3_CAM_END], "m31", [round(x, 2) for x in CH3_M31_END],
      "gain", round(CH3_M31_GAIN, 2), "warp", round(CH3_WARP_END, 2), "year", round(CH3_YEAR_END, 2))


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = N_FRAMES
    sc.render.resolution_x, sc.render.resolution_y = RX, RY
    sc.render.resolution_percentage = 100
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = int(arg("--samples", CONFIG["samples"]))
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
    sc.render.threads_mode = "FIXED"
    sc.render.threads = int(arg("--threads", CONFIG["threads"]))
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            pass
    w = bpy.data.worlds.new("Void")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Strength"].default_value = 0.0
    sc.world = w
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
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")

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

    def add(self, a, b): return self.m("ADD", a, b)
    def sub(self, a, b): return self.m("SUBTRACT", a, b)
    def mul(self, a, b): return self.m("MULTIPLY", a, b)
    def div(self, a, b): return self.m("DIVIDE", a, b)
    def madd(self, a, b, c): return self.m("MULTIPLY_ADD", a, b, c)

    def vm(self, op, a, b=None, scale=None):
        node = self.n("ShaderNodeVectorMath", operation=op)
        self._set(node.inputs[0], a)
        if b is not None:
            self._set(node.inputs[1], b)
        if scale is not None:
            self._set(node.inputs["Scale"], scale)
        return node.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH") else node.outputs["Vector"]

    def comb(self, x, y, z=0.0):
        c = self.n("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._set(c.inputs[i], v)
        return c.outputs[0]

    def sep(self, v):
        s = self.n("ShaderNodeSeparateXYZ")
        self.link(v, s.inputs[0])
        return s.outputs[0], s.outputs[1], s.outputs[2]

    def image(self, img, vec, ext="CLIP"):
        t = self.n("ShaderNodeTexImage", interpolation="Linear", extension=ext)
        t.image = img
        self.link(vec, t.inputs["Vector"])
        return t.outputs["Color"]


PARAM = {}          # name -> current value
SOCKETS = {}        # name -> Value-node sockets (one per material)


def P(b, name, v=0.0):
    """animated scalar = a Value node (one per material and name). Cycles constant-folds
    them, so a gated-off layer costs nothing; the per-frame shader update is cheap here."""
    PARAM.setdefault(name, float(v))
    cache = b.__dict__.setdefault("pcache", {})
    if name not in cache:
        node = b.n("ShaderNodeValue")
        node.outputs[0].default_value = PARAM[name]
        cache[name] = node.outputs[0]
        SOCKETS.setdefault(name, []).append(node.outputs[0])
    return cache[name]


def setp(name, v):
    PARAM[name] = float(v)


def getp(name):
    return PARAM[name]


def flush_params():
    for k, socks in SOCKETS.items():
        v = PARAM[k]
        for s in socks:
            if abs(s.default_value - v) > 1e-9:
                s.default_value = v


IMAGES = {}


def load(name, alpha=False):
    if name not in IMAGES:
        img = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
        img.colorspace_settings.name = "sRGB"
        img.alpha_mode = "CHANNEL_PACKED" if alpha else "NONE"
        IMAGES[name] = img
    return IMAGES[name]


# ---------------------------------------------------------------------------
# sky dome shader
# ---------------------------------------------------------------------------
def layer(b, Sx, Sy, key, img_name, warp=None):
    """CH4 texture placed in sky-plane coords: centre (cx,cy), rotation (cos,sin), 1/(2*half)."""
    dx = b.sub(Sx, P(b, key + "_cx"))
    dy = b.sub(Sy, P(b, key + "_cy"))
    c, s = P(b, key + "_cos", 1.0), P(b, key + "_sin")
    qx = b.mul(b.add(b.mul(dx, c), b.mul(dy, s)), P(b, key + "_ihx", 0.25))
    qy = b.mul(b.sub(b.mul(dy, c), b.mul(dx, s)), P(b, key + "_ihy", 0.25))
    if warp:
        qx, qy = warp(b, qx, qy)
    uv = b.comb(b.add(qx, 0.5), b.add(qy, 0.5))
    return b.image(load(img_name), uv)


def warp_m31(b, x, y):
    """tidal twist (rotation growing with r^2), elongation and an S-shear of the face-on disk."""
    r2 = b.add(b.mul(x, x), b.mul(y, y))
    a = b.mul(r2, P(b, "m31_twist"))
    ca, sa = b.m("COSINE", a), b.m("SINE", a)
    xr = b.sub(b.mul(x, ca), b.mul(y, sa))
    yr = b.add(b.mul(x, sa), b.mul(y, ca))
    xr = b.div(xr, P(b, "m31_stretch", 1.0))
    yr = b.add(yr, b.mul(P(b, "m31_shear"), b.mul(xr, b.mul(xr, xr))))
    return xr, yr


def core_sprite(b, Sx, Sy, name):
    dx = b.sub(Sx, P(b, name + "_x"))
    dy = b.sub(Sy, P(b, name + "_y"))
    u2 = b.div(b.add(b.mul(dx, dx), b.mul(dy, dy)), P(b, name + "_s2", 0.0025))
    moff = b.m("POWER", b.add(1.0, u2), -1.6)
    tight = b.m("EXPONENT", b.mul(u2, -9.0))
    lum = b.mul(b.madd(moff, 0.35, b.mul(tight, 2.5)), P(b, name + "_amp"))
    return b.vm("SCALE", (1.0, 0.86, 0.66), scale=lum)


def mat_sky():
    mat = bpy.data.materials.new("M_sky")
    b = NB(mat)
    geo = b.n("ShaderNodeNewGeometry")
    rel = b.vm("SUBTRACT", geo.outputs["Position"], b.comb(P(b, "cam_x"), P(b, "cam_y"), P(b, "cam_z")))
    d = b.vm("NORMALIZE", rel)
    dx, dy, dz = b.sep(d)
    shaders = []

    def emit(color, gate=None):
        em = b.n("ShaderNodeEmission")
        b.link(color, em.inputs["Color"])
        em.inputs["Strength"].default_value = 1.0
        if gate is None:
            shaders.append(em.outputs[0])
            return
        mx = b.n("ShaderNodeMixShader")
        b.link(P(b, "on_" + gate, 1.0), mx.inputs[0])
        b.link(em.outputs[0], mx.inputs[2])
        shaders.append(mx.outputs[0])

    allg = P(b, "g_all", 1.0)
    # atmosphere LUT from CH3 (extinction + airglow over sin(altitude)); fades out in space
    z = b.m("MAXIMUM", dz, 0.0)
    ext = b.image(load("ch3_atmo.png"), b.comb(z, 0.75), "EXTEND")
    glow = b.image(load("ch3_atmo.png"), b.comb(z, 0.25), "EXTEND")
    mixn = b.n("ShaderNodeMix", data_type="RGBA", blend_type="MIX")
    b.link(P(b, "space"), mixn.inputs["Factor"])
    b.link(ext, mixn.inputs[6])
    mixn.inputs[7].default_value = (1, 1, 1, 1)
    extc = mixn.outputs[2]

    # alt-az stars + galactic Milky Way (CH3 maps)
    p0, p1 = math.radians(META["star_pmin"]), math.radians(META["star_pmax"])
    u = b.madd(b.m("ARCTAN2", dx, dy), 1 / (2 * math.pi), 0.5)
    v = b.madd(b.m("ARCSINE", dz), 1 / (p1 - p0), -p0 / (p1 - p0))
    stars = b.image(load("ch3_stars.png"), b.comb(u, v), "EXTEND")
    gx = b.vm("DOT_PRODUCT", d, tuple(META["gx"]))
    gy = b.vm("DOT_PRODUCT", d, tuple(META["gy"]))
    gz = b.vm("DOT_PRODUCT", d, tuple(META["gz"]))
    l = b.m("ARCTAN2", gy, gx)
    bb = b.m("ARCSINE", gz)

    def lgauss(l_c, width):
        vx = tuple(math.cos(l_c) * META["gx"][i] + math.sin(l_c) * META["gy"][i] for i in range(3))
        dd = b.vm("DOT_PRODUCT", d, vx)
        return b.m("EXPONENT", b.madd(dd, 2.0 / width ** 2, -2.0 / width ** 2))

    g = lgauss(MW_BEND["l0"], math.radians(55.0))
    g2 = lgauss(MW_BEND["l0"] + math.radians(48.0), math.radians(32.0))
    shift = b.madd(g, P(b, "mw_shiftA"), b.mul(g2, P(b, "mw_shiftB")))
    thick = b.madd(g, P(b, "mw_thick"), 1.0)
    b2 = b.div(b.sub(bb, shift), thick)
    bmax = math.radians(META["mw_bmax"])
    mwt = b.n("ShaderNodeTexImage", interpolation="Linear", extension="CLIP")
    mwt.image = load("ch3_mw.png", alpha=True)
    b.link(b.comb(b.madd(l, 1 / (2 * math.pi), 0.5), b.madd(b2, 1 / (2 * bmax), 0.5)), mwt.inputs["Vector"])
    mw = mwt.outputs["Color"]
    # Milky Way dust in front of Andromeda (as in CH3)
    mwocc = b.sub(1.0, b.mul(b.mul(mwt.outputs["Alpha"], 0.85), P(b, "mw_occ", 1.0)))
    # CH3's pre-inclined Andromeda: gnomonic projection about its own direction
    dn = b.vm("DOT_PRODUCT", d, b.comb(P(b, "m3n_x"), P(b, "m3n_y"), P(b, "m3n_z")))
    gu = b.add(b.div(b.vm("DOT_PRODUCT", d, b.comb(P(b, "m3x_x"), P(b, "m3x_y"), P(b, "m3x_z"))), dn), 0.5)
    gv = b.add(b.div(b.vm("DOT_PRODUCT", d, b.comb(P(b, "m3y_x"), P(b, "m3y_y"), P(b, "m3y_z"))), dn), 0.5)
    g3 = b.image(load("ch3_m31_L1.png"), b.comb(gu, gv))
    f3 = b.mul(b.mul(b.m("GREATER_THAN", dn, 0.05), P(b, "m31ch3_gain")), b.mul(mwocc, allg))
    emit(b.vm("MULTIPLY", b.vm("SCALE", g3, scale=f3), extc), "m31ch3")
    emit(b.vm("MULTIPLY", b.vm("SCALE", stars, scale=b.mul(P(b, "star_gain", 1.0), allg)), extc))
    emit(b.vm("MULTIPLY", b.vm("SCALE", mw, scale=b.mul(P(b, "mw_gain", 1.0), allg)), extc), "mw")
    # airglow (CH3 LUT) tinted by the starburst
    gl = b.vm("MULTIPLY", glow, b.comb(P(b, "glow_r", 1.0), P(b, "glow_g", 1.0), P(b, "glow_b", 1.0)))
    emit(b.vm("SCALE", gl, scale=b.mul(P(b, "glow_gain", 0.02), allg)), "glow")

    # CH4 gnomonic sky-plane coords
    k = b.vm("DOT_PRODUCT", d, N_AX)
    kk = b.m("MAXIMUM", k, 0.05)
    Sx = b.div(b.vm("DOT_PRODUCT", d, EX_AX), b.mul(kk, SU))
    Sy = b.div(b.vm("DOT_PRODUCT", d, EY_AX), b.mul(kk, SU))
    vis = b.m("GREATER_THAN", k, 0.06)
    lg = b.mul(allg, vis)
    for key, img, warp in (("m31", "ch4_m31.png", warp_m31), ("tails", "ch4_tails.png", None),
                           ("ell", "ch4_ell.png", None), ("burst", "ch4_burst.png", None)):
        c = layer(b, Sx, Sy, key, img, warp)
        gain = b.mul(P(b, "g_" + key), lg)
        if key == "m31":
            c = b.vm("MULTIPLY", c, extc)
            gain = b.mul(gain, mwocc)
        emit(b.vm("SCALE", c, scale=gain), key)
    for cn in ("coreA", "coreB", "coreE"):
        emit(b.vm("SCALE", core_sprite(b, Sx, Sy, cn), scale=lg), cn)
    tot = shaders[0]
    for s in shaders[1:]:
        ad = b.n("ShaderNodeAddShader")
        b.link(tot, ad.inputs[0])
        b.link(s, ad.inputs[1])
        tot = ad.outputs[0]
    b.link(tot, b.out.inputs["Surface"])
    return mat


def mat_emit(name, color, param=None, grad=False):
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    em = b.n("ShaderNodeEmission")
    if grad:
        tc = b.n("ShaderNodeTexCoord")
        z = b.sep(tc.outputs["Generated"])[2]
        g = b.m("POWER", z, 40.0)
        tint = b.comb(P(b, "haze_r", 1.0), P(b, "haze_g", 1.0), P(b, "haze_b", 1.0))
        c = b.vm("MULTIPLY", color, tint)
        c = b.vm("SCALE", c, scale=b.mul(b.madd(g, 0.8, 0.2), b.mul(P(b, param, 1.0), P(b, "g_all", 1.0))))
        b.link(c, em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (*color, 1)
    b.link(em.outputs[0], b.out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# geometry (identical construction to CH3)
# ---------------------------------------------------------------------------
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
        verts += [(xx, y, zz), (xx, y, bottom)]
    for i in range(nseg):
        a, c = 2 * i, 2 * i + 2
        faces.append((a + 1, c + 1, c, a))
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def tree(name, base, height, mat):
    import random
    rnd = random.Random(7)
    bm = bmesh.new()

    def branch(p, d, length, rad, depth):
        q = p + d * length
        mtx = Matrix.Translation((p + q) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=7, radius1=rad, radius2=rad * 0.68,
                              depth=length * 1.04, matrix=mtx)
        if depth == 0 or rad < 0.006:
            return
        nb = 2 if depth > 2 else 3
        for i in range(nb):
            ax = Vector((rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.6)))
            nd = (d + ax * rnd.uniform(0.55, 0.95) + Vector((0.20, 0, 0))).normalized()
            branch(q, nd, length * rnd.uniform(0.62, 0.8), rad * 0.64, depth - 1)
        if rnd.random() < 0.6:
            branch(q, (d + Vector((0.16, 0, 0.05))).normalized(), length * 0.75, rad * 0.7, depth - 1)

    branch(Vector(base) - Vector((0, 0, 0.6)), Vector((0.10, 0, 1)).normalized(), height * 0.36 + 0.6, height * 0.032, 7)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


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


def set_ch3_m31(yaw, pitch, width_deg, pa_deg):
    """same projection as CH3's place_m31 (gnomonic about Andromeda's direction)."""
    d = sdir(yaw, pitch)
    right = Vector((math.cos(math.radians(yaw)), -math.sin(math.radians(yaw)), 0.0))
    up = right.cross(d)
    ca, sa = math.cos(math.radians(pa_deg)), math.sin(math.radians(pa_deg))
    xa = right * ca + up * sa
    ya = -right * sa + up * ca
    th = math.tan(math.radians(min(width_deg, 160.0)) / 2)
    asp = META["m31_h"] / META["m31_w"]
    for nm, vec in (("m3n", d), ("m3x", xa / (2 * th)), ("m3y", ya / (2 * th * asp))):
        for i, c in enumerate("xyz"):
            setp(nm + "_" + c, vec[i])


def ch3_m31_pos(ts):
    ks = CH3_POS_KEYS
    for a, c in zip(ks, ks[1:]):
        if ts <= c[0]:
            u = smooth((ts - a[0]) / (c[0] - a[0]))
            return tuple(lerp(a[i], c[i], u) for i in (1, 2, 3))
    return ks[-1][1:]


def bend_setup():
    gx, gy, gz = (Vector(META[k]) for k in ("gx", "gy", "gz"))
    yaw, pitch, _ = ch3_m31_pos(40.0)
    m = sdir(yaw, pitch)
    l_m = math.atan2(m.dot(gy), m.dot(gx))
    b_m = math.asin(max(-1, min(1, m.dot(gz))))
    sgn = 1.0 if b_m > 0 else -1.0
    return dict(l0=l_m + math.radians(-8.0), amp=sgn * math.radians(15.0))


MW_BEND = {}
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
    b = NB(mat)
    em = b.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    tr = b.n("ShaderNodeBsdfTransparent")
    mx = b.n("ShaderNodeMixShader")
    b.link(tr.outputs[0], mx.inputs[1])
    b.link(em.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs["Surface"])
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


# captions: id, text, y, size, spacing, colour, t_in, t_out
CAPTIONS = [
    ("milk", "MILKOMEDA", 0.115, 0.044, 2.4, ACCENT, 28.4, 33.9),
    ("title", "THE SKY THAT'S COMING", 0.50, 0.046, 1.9, (0.90, 0.88, 0.96), 56.35, 59.2),
]
# year counter continues CH3's (+3.90 at the cut); NASA 2012 sequence: ~4 Gyr starbursts,
# ~5.1 Gyr cores merge, ~7 Gyr elliptical. Shown only IF THEY MERGE.
YEAR_KEYS = [(0.0, CH3_YEAR_END), (9.5, 4.00), (14.0, 4.70), (19.0, 5.10), (24.0, 6.00), (29.0, 7.00), (60.0, 7.00)]
T_YEAR_OUT = 33.0


def build():
    global CAM, HUD
    MW_BEND.update(bend_setup())
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

    me = bpy.data.meshes.new("dome")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=8000.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat_sky())
    OBJ["dome"] = bpy.data.objects.new("dome", me)
    bpy.context.scene.collection.objects.link(OBJ["dome"])

    set_ch3_m31(CH3_M31_END[0], CH3_M31_END[1], CH3_M31_END[3], CH3_M31_END[2])

    for fname, fsrc in CH3.get("funcs", {}).items():
        try:
            exec(compile(fsrc, CH3_SCRIPT, "exec"), globals())
        except Exception as ex:
            print("[ch4] could not reuse CH3", fname, ex)
    black = mat_emit("M_black", (0.0, 0.0, 0.0))
    haze = mat_emit("M_haze", (0.020, 0.018, 0.036), "haze", grad=True)
    L = CH3
    OBJ["far"] = ridge("ridge_far", *L["far"][:5], haze, freq=L["far"][5])
    OBJ["mid"] = ridge("ridge_mid", *L["mid"][:5], mat_emit("M_mid", (0.006, 0.0055, 0.011), "haze", grad=True),
                       freq=L["mid"][5])
    ny, ntop, namp, nw, nseed, nfreq = L["near"]
    OBJ["near"] = ridge("ridge_near", ny, ntop, namp, nw, nseed, black, freq=nfreq)
    tx = L["tree_x"]
    tz = ntop + namp * fbm1(tx / nw * nfreq, nseed)
    OBJ["tree"] = tree("tree", (tx, ny, tz), L["tree_h"], black)

    make_text("year", "+ 3.90 BILLION YEARS", 0.915, 0.0235, 1.55, (0.84, 0.82, 0.90))
    fy, fs, fsp, fcol = CH3["ifm"]
    make_text("ifm", "IF THEY MERGE", fy, fs, fsp, tuple(fcol))
    for tid, body, fy, size, sp, col, *_ in CAPTIONS:
        make_text(tid, body, fy, size, sp, col, thin=(tid == "title"))


# ---------------------------------------------------------------------------
# choreography (seconds from chapter start)
# ---------------------------------------------------------------------------
CAM_KEYS = [(0.0, CH3_CAM_END[0], CH3_CAM_END[1], CH3_CAM_END[2]),
            (0.6, CH3_CAM_END[0], CH3_CAM_END[1], CH3_CAM_END[2]),
            (8.5, 0.0, 9.0, 17.5), (41.0, 0.0, 10.0, 17.5), (51.0, 0.0, 26.0, 17.5), (60.0, 0.0, 26.0, 17.5)]


def cam_at(ts):
    ks = CAM_KEYS
    for a, c in zip(ks, ks[1:]):
        if ts <= c[0]:
            u = ease((ts - a[0]) / (c[0] - a[0]))
            return tuple(lerp(a[i], c[i], u) for i in (1, 2, 3))
    return ks[-1][1:]


A0 = sky_S(CH3_M31_END[0], CH3_M31_END[1])          # Andromeda centre at the cut
B0 = sky_S(-64.0, 3.0)                              # our galactic centre (low, far left)
M_END = (0.12, -0.20)                               # where the merged core settles
FINAL_DIR = sky_S(0.0, 26.0)                        # centre of the frame at the end
T_MERGE = 25.0
T_ORBIT0 = 3.5                                      # orbit starts once the CH3 cross-fade is under way


def orbit(ts):
    """the two nuclei fall together, circling faster as they close."""
    d0 = (A0[0] - B0[0], A0[1] - B0[1])
    sep0 = math.hypot(*d0)
    phi0 = math.atan2(d0[1], d0[0])
    u = clamp((ts - T_ORBIT0) / (T_MERGE - T_ORBIT0))
    sep = sep0 * (1 - smooth(u)) ** 1.3
    psi = 2 * math.pi * 1.25 * u ** 1.6
    ox, oy = math.cos(psi) * sep / 2, 0.5 * math.sin(psi) * sep / 2
    c, s = math.cos(phi0), math.sin(phi0)
    ox, oy = c * ox - s * oy, s * ox + c * oy
    w = 0.3 + 0.2 * smooth(u)                        # M31 is the heavier one at first
    mid0 = (A0[0] * (1 - w) + B0[0] * w, A0[1] * (1 - w) + B0[1] * w)
    mid = lerp2(mid0, M_END, ease(u * 1.1))
    pa = (mid[0] + ox * 2 * w, mid[1] + oy * 2 * w)
    pb = (mid[0] - ox * 2 * (1 - w), mid[1] - oy * 2 * (1 - w))
    return pa, pb, mid, psi + phi0


def place(key, cx, cy, hx, hy, rot_deg):
    setp(key + "_cx", cx)
    setp(key + "_cy", cy)
    setp(key + "_cos", math.cos(math.radians(rot_deg)))
    setp(key + "_sin", math.sin(math.radians(rot_deg)))
    setp(key + "_ihx", 1.0 / (2 * hx))
    setp(key + "_ihy", 1.0 / (2 * hy))


def update(frame):
    ts = (frame - 1) / FPS

    yaw, pitch, lens = cam_at(ts)
    rise = ramp(ts, 41.0, 51.0)
    CAM.location = (0.0, 0.0, 90.0 * rise ** 1.3)
    CAM.rotation_euler = (math.radians(90 + pitch), 0, math.radians(-yaw))
    CAM.data.lens = lens
    HUD.location = (0, 0, -lens / REF_LENS)
    setp("cam_x", 0.0)
    setp("cam_y", 0.0)
    setp("cam_z", CAM.location.z)
    OBJ["dome"].location = CAM.location
    setp("space", ramp(ts, 43.0, 50.0))

    pa, pb, mid, ang = orbit(ts)

    # --- CH3's Andromeda: identical at the cut, cross-fades into CH4's tidally distorted disk
    xf = ramp(ts, 0.8, 6.5)
    setp("m31ch3_gain", CH3_M31_GAIN * (1 - xf))
    setp("g_m31ch3", CH3_M31_GAIN * (1 - xf))

    hx0 = math.tan(math.radians(CH3_M31_END[3] / 2)) / SU
    tw = ramp(ts, 2.0, 17.0)
    setp("m31_twist", -0.2 - 4.0 * tw)
    setp("m31_stretch", 1.0 + 0.30 * tw)
    setp("m31_shear", 0.9 * tw)
    hx = hx0 * lerp(1.0, 0.80, ramp(ts, 3.0, 20.0))
    asp = lerp(META["m31_cosi"], 0.48, tw)
    place("m31", pa[0], pa[1], hx, hx * asp, CH3_M31_END[2] - 26.0 * tw)
    gm = xf * (1 - 0.35 * ramp(ts, 8.0, 15.0)) * (1 - ramp(ts, 13.0, 24.0))
    setp("g_m31", 1.25 * gm)

    # --- Milky Way: CH3's bend keeps growing, the band thickens, then dissolves into the merger
    warp = CH3_WARP_END + 1.2 * ramp(ts, 0.0, 18.0)
    setp("mw_shiftA", warp * MW_BEND["amp"])
    setp("mw_shiftB", -warp * MW_BEND["amp"] * 0.45)
    setp("mw_thick", warp * 0.55)
    gmw = (1 - 0.35 * ramp(ts, 9.0, 15.0)) * (1 - ramp(ts, 13.0, 25.0))
    setp("mw_gain", META["mw_lmax"] * CH3_MW_GAIN * (1.0 + 0.25 * warp) * gmw)
    setp("star_gain", META["star_lmax"] * (1.0 - 0.25 * ramp(ts, 10.0, 18.0) * (1 - ramp(ts, 26.0, 40.0))))

    # --- tidal tails ---
    tl = ramp(ts, 2.0, 12.0) * (1 - 0.7 * ramp(ts, 22.0, 34.0)) * (1 - ramp(ts, 42.0, 48.0))
    sz = lerp(2.2, 3.4, ramp(ts, 2.0, 30.0))
    place("tails", mid[0], mid[1], sz, sz, math.degrees(ang) * 0.35 + 10.0)
    setp("g_tails", 0.9 * tl)

    # --- starburst: the gas clouds collide and ignite ---
    bu = ramp(ts, 9.5, 15.0) * (1 - 0.85 * ramp(ts, 19.5, 30.0)) * (1 - ramp(ts, 36.0, 46.0))
    bsc = lerp(0.95, 1.12, ramp(ts, 8.0, 36.0))
    brot = -14.0 * ramp(ts, 6.0, 40.0)
    c, s = math.cos(math.radians(brot)), math.sin(math.radians(brot))
    ox, oy = 0.0, -0.25 * bsc                 # texture swirl centre sits at (0, 0.25)
    place("burst", mid[0] + c * ox - s * oy, mid[1] + s * ox + c * oy, 2.6 * bsc, 1.625 * bsc, brot)
    setp("g_burst", 1.6 * bu)

    # --- Milkomeda ---
    e = ramp(ts, 16.0, 30.0)
    pull = ramp(ts, 41.5, 54.0)
    ehx = lerp(lerp(1.9, 2.7, ramp(ts, 16.0, 40.0)), 0.50, pull ** 0.8)
    ec = lerp2(M_END, FINAL_DIR, ramp(ts, 41.0, 51.0))
    place("ell", ec[0], ec[1], ehx, ehx * 0.70, 16.0)
    setp("g_ell", 1.15 * e * (1 + 0.6 * pull))

    # --- nuclei ---
    amp_pre = 2.5 * ramp(ts, 3.0, 16.0)
    merged = ramp(ts, T_MERGE - 2.0, T_MERGE + 0.5)
    for key, p, a in (("coreA", pa, 1.0), ("coreB", pb, 0.8)):
        setp(key + "_x", p[0])
        setp(key + "_y", p[1])
        setp(key + "_amp", a * amp_pre * (1 - merged))
        setp(key + "_s2", 0.05 ** 2)
    setp("coreE_x", ec[0])
    setp("coreE_y", ec[1])
    setp("coreE_amp", 1.3 * merged * (1 - 0.3 * pull))
    setp("coreE_s2", lerp(0.08, 0.02, pull) ** 2)

    # --- airglow + hazy far ridges, lit pink by the starburst ---
    big = 1.0 - ramp(ts, 42.0, 47.0)
    setp("glow_gain", (CH3_GLOW_END + 0.05 * bu + 0.02 * e) * big)
    setp("glow_r", lerp(1.0, 1.9, bu))
    setp("glow_g", lerp(1.0, 0.75, bu))
    setp("glow_b", lerp(1.0, 1.05, bu))
    setp("haze", CH3_HAZE_END * (1 + 1.2 * bu + 0.5 * e))
    setp("haze_r", lerp(1.0, 1.8, bu))
    setp("haze_g", lerp(1.0, 0.8, bu))
    setp("haze_b", 1.0)
    for kk in ("far", "mid", "near", "tree"):
        OBJ[kk].hide_render = ts > 51.0

    # --- fade to black, title on black ---
    fade = 1.0 - ramp(ts, 54.6, 56.1)
    setp("g_all", max(fade, 0.0))
    OBJ["dome"].hide_render = fade <= 0.0

    setp("mw_occ", 1.0 if getp("mw_gain") > 1e-4 else 0.0)
    for key in ("m31ch3", "m31", "tails", "ell", "burst", "mw", "glow"):
        gk = "mw_gain" if key == "mw" else ("glow_gain" if key == "glow" else "g_" + key)
        setp("on_" + key, 1.0 if (getp(gk) > 1e-4 and fade > 0) else 0.0)
    for key in ("coreA", "coreB", "coreE"):
        setp("on_" + key, 1.0 if (getp(key + "_amp") > 1e-4 and fade > 0) else 0.0)
    flush_params()

    # --- captions ---
    yv = keys(ts, YEAR_KEYS, fn=lambda a: a * a * (3 - 2 * a) * 0.4 + a * 0.6)
    TEXTS["year"][0].data.body = f"+ {yv:.2f} BILLION YEARS"
    ya = 1.0 if ts <= T_YEAR_OUT else 1.0 - smooth((ts - T_YEAR_OUT) / 1.2)
    set_alpha("year", 0.92 * ya)
    set_alpha("ifm", 0.90 * ya)
    for tid, body, fy, size, sp, col, t0, t1 in CAPTIONS:
        set_alpha(tid, window(ts, t0, t1, 0.8 if tid != "title" else 1.1, 0.7))


# ---------------------------------------------------------------------------
def main():
    sc = reset_scene()
    build()
    out = arg("--out", CONFIG["output"])
    os.makedirs(out, exist_ok=True)
    frames = []
    if arg("--frames"):
        frames = [int(v) for v in arg("--frames").split(",")]
    elif "--render" in ARGV:
        a = int(arg("--start", 1))
        e = int(arg("--end", N_FRAMES))
        st = int(arg("--step", 1))
        frames = list(range(a, e + 1, st))
    if "--blend" in ARGV:
        update(int(arg("--blend-frame", 1)))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "scene.blend"))
    skip = "--skip-existing" in ARGV
    for f in frames:
        path = os.path.join(out, f"f_{f:04d}.png")
        if skip and os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        t0 = time.time()
        sc.frame_set(f)
        update(f)
        tmp = path[:-4] + "_tmp.png"
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, path)
        print(f"frame {f} {time.time() - t0:.2f}s", flush=True)


main()
