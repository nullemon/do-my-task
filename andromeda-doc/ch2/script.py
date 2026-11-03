"""
ANDROMEDA documentary - CHAPTER 2 "FALLING" (1:00-2:00 of the film, 60.0 s, 1440 frames @ 24 fps)

Shots (seconds from chapter start; narration timestamps from PLAN.md):
  0.0-5.6   1912 glass-plate negative of M31, backlit, slow push-in       VO 1.0 "In 1912 ... Slipher"
  4.6-10.4  Slipher's measurement as a thin spectrum: sepia -> colour,
            absorption lines slide off their rest marks toward the blue   VO "...shifted toward blue"
  9.0-26    god's-eye Local Group: Milky Way close in the foreground,
            Andromeda + M33 far off, LMC beside us; camera pulls back     VO 9.0 "approaching" / 18.5 "400,000 km"
  26-32     the classic picture: one straight line, head-on              VO 26.0
  32-37.5   sideways drift unknown: a trembling fan of possible headings VO 32.0
  37.5-50   uncertainty: ~48 possible orbits blossom; some merge, some   VO 37.5 "coin-flip ... ninety percent"
            swing past
  50-60     one merging path is chosen; Andromeda starts to fall along   VO 50.0 "So let's follow ..."
            it, camera chases; fade to black

All heavy imagery is pre-baked by gen_textures.py (numpy) into PNGs; the scene is only
emission planes with image textures, thin emission curves, and text. Cycles CPU, no lights.

Run (bpy module):
  /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing']; exec(compile(open(p).read(),p,'exec'))"
Options after '--':
  --frames 1,240,700      render only these frames (stills)
  --render [--start a --end b --step s] [--skip-existing]
  --out DIR               output folder (default CONFIG['output'])
  --threads N --samples N
"""

CONFIG = dict(
    fps=24,
    duration=60.0,
    resolution=(1920, 1080),
    samples=3,
    threads=2,
    textures="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures",
    output="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/ch2/frames",
    font_light="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_thin="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
)

import sys
import os
import math
import time

import numpy as np
import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

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
LENS, SENSOR_W = 35.0, 36.0
TW = (SENSOR_W / 2) / LENS                 # tan(half horizontal fov)
TH = TW * CONFIG["resolution"][1] / CONFIG["resolution"][0]
PX = 2 * TH / CONFIG["resolution"][1]       # HUD units (at distance 1) per pixel

ACCENT = (0.80, 0.72, 1.00)                 # violet-white
TEXT_COL = (0.86, 0.85, 0.84)
SEPIA_TXT = (0.045, 0.028, 0.014)     # dark "ink" on the bright plate

# world layout (1 unit = 1 kpc). Milky Way at the origin, Andromeda 770 kpc away.
P_MW = Vector((0.0, 0.0, 0.0))
P_M31 = Vector((770.0, 0.0, 0.0))
P_M33 = Vector((805.0, -205.0, -35.0))     # ~205 kpc from M31, ~830 kpc from us
P_LMC = Vector((-24.0, -38.0, -24.0))      # ~50 kpc from the Galactic centre
GAL_SCALE = 1.6                             # galaxy disks drawn 1.6x their true size (see README)
HALF_MW = 23.0 * GAL_SCALE                  # texture disk fades out at ~0.85 of the half-size
HALF_M31 = 36.0 * GAL_SCALE
HALF_M33 = 11.0 * GAL_SCALE
HALF_LMC = 7.0 * GAL_SCALE


# ------------------------------------------------------------------ timing helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(a):
    a = clamp(a)
    return a * a * a * (a * (a * 6 - 15) + 10)


def smooth(a):
    a = clamp(a)
    return a * a * (3 - 2 * a)


def ramp(ts, t0, t1):
    return ease((ts - t0) / max(1e-6, t1 - t0))


def lerp(a, b, t):
    return a + (b - a) * t


def window(ts, t_in, t_out, fin=0.7, fout=0.7):
    if ts < t_in or ts > t_out + fout:
        return 0.0
    a = smooth((ts - t_in) / fin) if fin > 0 else 1.0
    b = 1.0 - smooth((ts - t_out) / fout) if ts > t_out else 1.0
    return clamp(min(a, b))


# ------------------------------------------------------------------ orbits
G = 4.30091e-6        # kpc (km/s)^2 / Msun
TU = 0.9778           # Gyr per kpc/(km/s)


def orbit(M, vt, k=2.5, rs=60.0, soft=40.0, gyr=10.0, dt=0.0025):
    """Relative M31 orbit in the Milky Way frame (orbital plane = XY).
    Softened point mass + a crude dynamical-friction drag that switches on near pericentre.
    Starts at 770 kpc closing at 110 km/s with a sideways speed vt (km/s).
    Returns (points every 8 steps, merge time in Gyr or None)."""
    r = np.array([770.0, 0.0])
    v = np.array([-110.0, vt])
    pts = [r.copy()]
    merged = None

    def acc(r, v):
        d2 = r @ r
        return -G * M * r / (d2 + soft * soft) ** 1.5 - k * v / (1 + d2 / rs ** 2)
    n = int(gyr / TU / dt)
    for i in range(n):
        a1 = acc(r, v)
        rm, vm = r + 0.5 * dt * v, v + 0.5 * dt * a1
        a2 = acc(rm, vm)
        r, v = r + dt * vm, v + dt * a2
        if i % 8 == 7:
            pts.append(r.copy())
        if merged is None and math.sqrt(r @ r) < 14.0 and math.sqrt(v @ v) < 90.0:
            merged = (i + 1) * dt * TU
            pts.append(r.copy())
            # let it settle into the centre over a short tail
            for j in range(12):
                pts.append(r * (1 - (j + 1) / 12.0))
            break
    return np.array(pts), merged


def build_ensemble(n=26, seed=4):
    rng = np.random.default_rng(seed)
    out = []
    qs = (np.arange(n) + 0.5) / n
    rng.shuffle(qs)
    for j in range(n):
        # sideways speed: broad, poorly constrained (0 to ~180 km/s), either sense
        vt = qs[j] ** 1.15 * 180.0 * (1 if j % 2 else -1)
        M = rng.uniform(3.3e12, 4.8e12)
        pts, mt = orbit(M, vt)
        out.append(dict(pts=pts, merged=mt, vt=vt, M=M))
    return out


# ------------------------------------------------------------------ scene
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
    cy.samples = int(arg("--samples", CONFIG["samples"]))
    ad = arg("--adaptive", CONFIG.get("adaptive"))
    cy.use_adaptive_sampling = bool(ad)
    if ad:
        cy.adaptive_threshold = float(ad)
        cy.adaptive_min_samples = int(arg("--min-samples", CONFIG.get("min_samples", 2)))
    cy.use_denoising = False
    for a in ("max_bounces", "diffuse_bounces", "glossy_bounces", "transmission_bounces", "volume_bounces"):
        setattr(cy, a, 0)
    cy.transparent_max_bounces = 16
    cy.caustics_reflective = cy.caustics_refractive = False
    try:
        cy.use_light_tree = False
    except Exception:
        pass
    sc.render.filter_size = 1.3
    thr = int(arg("--threads", CONFIG["threads"]))
    if thr:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = thr
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
    w = bpy.data.worlds.new("Void")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
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
    ims.compression = 15
    sc.render.use_persistent_data = True
    return sc


# ------------------------------------------------------------------ materials
PARAM = {}


class NB:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")

    def n(self, t, **kw):
        node = self.nt.nodes.new(t)
        for k, v in kw.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def param(self, name, v=1.0):
        node = self.n("ShaderNodeValue")
        node.outputs[0].default_value = v
        PARAM.setdefault(name, []).append(node.outputs[0])
        return node.outputs[0]

    def image(self, fname, ext="CLIP", vec=None, interp="Linear"):
        node = self.n("ShaderNodeTexImage")
        node.image = bpy.data.images.load(os.path.join(TEX, fname), check_existing=True)
        node.extension = ext
        node.interpolation = interp
        if vec is not None:
            self.link(vec, node.inputs["Vector"])
        return node

    def math(self, op, a, b=None):
        node = self.n("ShaderNodeMath", operation=op)
        for s, v in zip(node.inputs, (a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                s.default_value = v
            else:
                self.link(v, s)
        return node.outputs[0]

    def vmul(self, vec, f):
        node = self.n("ShaderNodeVectorMath", operation="SCALE")
        self.link(vec, node.inputs[0])
        if isinstance(f, (int, float)):
            node.inputs["Scale"].default_value = f
        else:
            self.link(f, node.inputs["Scale"])
        return node.outputs["Vector"]

    def additive(self, color, strength=1.0):
        em = self.n("ShaderNodeEmission")
        self.link(color, em.inputs["Color"])
        if isinstance(strength, (int, float)):
            em.inputs["Strength"].default_value = strength
        else:
            self.link(strength, em.inputs["Strength"])
        tr = self.n("ShaderNodeBsdfTransparent")
        ad = self.n("ShaderNodeAddShader")
        self.link(tr.outputs[0], ad.inputs[0])
        self.link(em.outputs[0], ad.inputs[1])
        self.link(ad.outputs[0], self.out.inputs["Surface"])

    def over(self, color, alpha):
        """emission over the scene with alpha (0 = fully transparent)."""
        em = self.n("ShaderNodeEmission")
        self.link(color, em.inputs["Color"])
        tr = self.n("ShaderNodeBsdfTransparent")
        mx = self.n("ShaderNodeMixShader")
        if isinstance(alpha, (int, float)):
            mx.inputs[0].default_value = alpha
        else:
            self.link(alpha, mx.inputs[0])
        self.link(tr.outputs[0], mx.inputs[1])
        self.link(em.outputs[0], mx.inputs[2])
        self.link(mx.outputs[0], self.out.inputs["Surface"])


def mat_image_add(name, fname, pname, gamma=1.0):
    """galaxy disk: additive emission of a pre-baked texture (black = nothing)."""
    b = NB(name)
    tc = b.n("ShaderNodeTexCoord")
    img = b.image(fname, "CLIP", tc.outputs["UV"])
    c = img.outputs["Color"]
    if gamma != 1.0:
        g = b.n("ShaderNodeGamma")
        b.link(c, g.inputs[0])
        g.inputs[1].default_value = gamma
        c = g.outputs[0]
    b.additive(c, b.param(pname, 1.0))
    return b.mat


def world_space():
    """tileable deep-space field as the WORLD background, mapped in screen (window) space;
    the UV offset follows camera yaw/pitch. Much cheaper than a camera-locked plane."""
    w = bpy.context.scene.world
    try:
        w.cycles.sampling_method = "NONE"       # no importance map: the world lights nothing
    except Exception:
        pass
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Window"], mp.inputs["Vector"])
    PARAM.setdefault("space_mapping", []).append(mp)
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(TEX, "ch2_space.png"), check_existing=True)
    img.extension = "REPEAT"
    img.interpolation = "Linear"
    nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
    nt.links.new(img.outputs["Color"], bg.inputs["Color"])
    val = nt.nodes.new("ShaderNodeValue")
    PARAM.setdefault("space", []).append(val.outputs[0])
    nt.links.new(val.outputs[0], bg.inputs["Strength"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def mat_line():
    """thin emission line; intensity/colour from the object's colour (set per frame)."""
    b = NB("M_line")
    oi = b.n("ShaderNodeObjectInfo")
    # fade lines out as they reach the Milky Way, so the galaxy itself stays clean
    geo = b.n("ShaderNodeNewGeometry")
    ln = b.n("ShaderNodeVectorMath", operation="LENGTH")
    b.link(geo.outputs["Position"], ln.inputs[0])
    mr = b.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    b.link(ln.outputs["Value"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = 22.0
    mr.inputs["From Max"].default_value = 115.0
    b.additive(b.vmul(oi.outputs["Color"], mr.outputs["Result"]), 1.0)
    return b.mat


def mat_glint():
    """small soft point of light on a camera-facing quad; colour from object colour."""
    b = NB("M_glint")
    tc = b.n("ShaderNodeTexCoord")
    sep = b.n("ShaderNodeSeparateXYZ")
    b.link(tc.outputs["Object"], sep.inputs[0])
    x2 = b.math("MULTIPLY", sep.outputs[0], sep.outputs[0])
    y2 = b.math("MULTIPLY", sep.outputs[1], sep.outputs[1])
    r2 = b.math("ADD", x2, y2)
    core = b.math("EXPONENT", b.math("MULTIPLY", r2, -60.0))
    halo = b.math("MULTIPLY", b.math("EXPONENT", b.math("MULTIPLY", r2, -7.0)), 0.18)
    f = b.math("ADD", core, halo)
    oi = b.n("ShaderNodeObjectInfo")
    b.additive(b.vmul(oi.outputs["Color"], f), 1.0)
    return b.mat


def mat_plate():
    b = NB("M_plate")
    tc = b.n("ShaderNodeTexCoord")
    img = b.image("ch2_plate.png", "CLIP", tc.outputs["UV"])
    c = b.vmul(img.outputs["Color"], b.param("plate_gain", 1.0))
    b.over(c, b.param("plate_a", 0.0))
    return b.mat


def mat_spectrum():
    """spectrum strip: mix(sepia, colour) x absorption mask sampled at lambda*(1+z)."""
    b = NB("M_spec")
    tc = b.n("ShaderNodeTexCoord")
    col = b.image("ch2_spec.png", "CLIP", tc.outputs["UV"])
    grey = b.image("ch2_specgrey.png", "CLIP", tc.outputs["UV"])
    mx = b.n("ShaderNodeMix", data_type="RGBA")
    sid = lambda socks, ident: [k for k in socks if k.identifier == ident][0]
    b.link(b.param("spec_col", 0.0), sid(mx.inputs, "Factor_Float"))
    b.link(grey.outputs["Color"], sid(mx.inputs, "A_Color"))
    b.link(col.outputs["Color"], sid(mx.inputs, "B_Color"))
    # line mask lookup: u' = u*(1+z) + z*L0/span
    sep = b.n("ShaderNodeSeparateXYZ")
    b.link(tc.outputs["UV"], sep.inputs[0])
    z = b.param("spec_z", 0.0)
    u2 = b.math("ADD", b.math("MULTIPLY", sep.outputs[0], b.math("ADD", z, 1.0)),
                b.math("MULTIPLY", z, 380.0 / 320.0))
    cmb = b.n("ShaderNodeCombineXYZ")
    b.link(u2, cmb.inputs[0])
    cmb.inputs[1].default_value = 0.5
    ln = b.image("ch2_lines.png", "EXTEND", cmb.outputs[0], "Linear")
    mul = b.n("ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    sid(mul.inputs, "Factor_Float").default_value = 1.0
    b.link(sid(mx.outputs, "Result_Color"), sid(mul.inputs, "A_Color"))
    b.link(ln.outputs["Color"], sid(mul.inputs, "B_Color"))
    c = b.vmul(sid(mul.outputs, "Result_Color"), b.param("spec_gain", 1.0))
    b.additive(c, b.param("spec_a", 0.0))
    return b.mat


def mat_text(name, color):
    b = NB(name)
    em = b.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    tr = b.n("ShaderNodeBsdfTransparent")
    mx = b.n("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.0
    b.link(tr.outputs[0], mx.inputs[1])
    b.link(em.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs["Surface"])
    return b.mat, mx


def set_param(name, v):
    for s in PARAM.get(name, []):
        s.default_value = v


# ------------------------------------------------------------------ geometry
def quad(name, mat, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for li, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = (u, v)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def poly_curve(name, pts, mat, depth=0.5):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = depth
    cu.bevel_resolution = 1
    cu.use_fill_caps = False
    cu.bevel_factor_mapping_start = "SEGMENTS"
    cu.bevel_factor_mapping_end = "SEGMENTS"
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (float(p[0]), float(p[1]), float(p[2]), 1.0)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    return ob


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


def make_text(tid, body, x, y, size, spacing=1.5, color=TEXT_COL, thin=False, align="CENTER", z=0.0):
    """HUD text. x,y in HUD units (frame spans x in [-TW,TW], y in [-TH,TH] at distance 1)."""
    cu = bpy.data.curves.new(tid, "FONT")
    cu.body = body
    f = font(CONFIG["font_thin"] if thin else CONFIG["font_light"])
    if f:
        cu.font = f
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.size = size
    cu.space_character = spacing
    ob = bpy.data.objects.new(tid, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = HUD
    ob.location = (x, y, z)
    mat, mx = mat_text("MT_" + tid, color)
    cu.materials.append(mat)
    TEXTS[tid] = (ob, mx)
    return ob


def set_alpha(tid, a):
    ob, mx = TEXTS[tid]
    mx.inputs[0].default_value = clamp(a)
    ob.hide_render = a <= 0.002


def build():
    global CAM, HUD, ORBITS, CHOSEN
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("Cam")
    cd.lens = LENS
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = SENSOR_W
    cd.clip_start = 0.05
    cd.clip_end = 60000.0
    CAM = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(CAM)
    sc.camera = CAM
    HUD = bpy.data.objects.new("HUD", None)
    sc.collection.objects.link(HUD)
    HUD.parent = CAM
    HUD.location = (0, 0, -1.0)

    # deep-space backdrop, locked to the camera far behind everything
    world_space()

    # galaxies
    mw = quad("milkyway", mat_image_add("M_mw", "ch2_mw.png", "mw", 1.0))
    mw.location = P_MW
    mw.scale = (HALF_MW, HALF_MW, 1)
    mw.rotation_euler = (math.radians(44.4), math.radians(29.4), 0.0)   # disk normal ~ (0.35,-0.70,0.62)
    m31 = quad("andromeda", mat_image_add("M_m31", "ch2_m31.png", "m31", 1.0))
    m31.location = P_M31
    m31.scale = (HALF_M31, HALF_M31, 1)
    m31.rotation_euler = (math.radians(58), math.radians(14), math.radians(-35))
    m33 = quad("m33", mat_image_add("M_m33", "ch2_m33.png", "m33", 1.0))
    m33.location = P_M33
    m33.scale = (HALF_M33, HALF_M33, 1)
    m33.rotation_euler = (math.radians(40), math.radians(-20), 0)
    lmc = quad("lmc", mat_image_add("M_lmc", "ch2_lmc.png", "lmc", 1.0))
    lmc.location = P_LMC
    lmc.scale = (HALF_LMC, HALF_LMC * 0.8, 1)
    lmc.rotation_euler = (math.radians(30), math.radians(10), 0)
    OBJ.update(mw=mw, m31=m31, m33=m33, lmc=lmc)

    # orbits: the classic head-on line + the uncertainty ensemble
    lm = mat_line()
    gm = mat_glint()
    hp = [P_M31 + (P_MW - P_M31) * (i / 60.0) for i in range(61)]
    OBJ["headon"] = poly_curve("headon", [(p.x, p.y, p.z) for p in hp], lm, 0.6)
    ORBITS = build_ensemble()
    for i, o in enumerate(ORBITS):
        p3 = np.c_[o["pts"], np.zeros(len(o["pts"]))]
        o["p3"] = p3
        ob = poly_curve(f"orbit{i:02d}", p3 - P_M31.to_tuple(), lm, 0.6)
        ob.location = P_M31        # origin at Andromeda so the fan can tremble around it
        o["ob"] = ob
        g = quad(f"glint{i:02d}", gm)
        g.scale = (6, 6, 1)
        o["glint"] = g
        o["phase"] = (i * 0.618) % 1.0
    # the path we follow at the end: a merging orbit with a wide, elegant first passage
    cands = [o for o in ORBITS if o["merged"] is not None and abs(o["vt"]) > 45]
    CHOSEN = min(cands, key=lambda o: o["merged"]) if cands else ORBITS[0]
    hg = quad("glint_head", gm)
    hg.scale = (6, 6, 1)
    OBJ["glint_head"] = hg

    # 1912 plate and spectrum (HUD, in front of everything)
    pl = quad("plate", mat_plate(), HUD)
    pl.location = (0, 0, -0.02)
    OBJ["plate"] = pl
    spm = quad("spectrum", mat_spectrum(), HUD)
    spm.location = (0, 0.0, -0.015)
    OBJ["spec"] = spm
    SW = TW * 0.80                       # half-width of the strip
    OBJ["spec_hw"] = SW
    spm.scale = (SW, 34 * PX, 1)         # strip ~ 1530 x 92 px incl. soft edges
    # rest-wavelength ticks above and below the strip
    tick_m, OBJ["ticks"] = None, []
    tb = NB("M_tick")
    tick_mx = None
    em = tb.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.92, 0.90, 0.95, 1)
    tr = tb.n("ShaderNodeBsdfTransparent")
    tick_mx = tb.n("ShaderNodeMixShader")
    tb.link(tr.outputs[0], tick_mx.inputs[1])
    tb.link(em.outputs[0], tick_mx.inputs[2])
    tb.link(tick_mx.outputs[0], tb.out.inputs["Surface"])
    OBJ["tick_mx"] = tick_mx
    for lam in (393.37, 396.85, 430.8, 486.13, 517.3, 589.3, 656.28):
        u = (lam - 380.0) / 320.0
        for s in (1, -1):
            t = quad(f"tick{lam}_{s}", tb.mat, HUD)
            t.location = (-SW + 2 * SW * u, s * 29 * PX, -0.014)
            t.scale = (1.0 * PX, 8 * PX, 1)
            OBJ["ticks"].append(t)

    # text
    cy = -TH + 0.165 * 2 * TH           # caption baseline: lower third
    make_text("cap_slipher", "VESTO SLIPHER  ·  1912", 0, cy, 0.0205, 1.55, SEPIA_TXT)
    make_text("spec_blue", "BLUE", -SW, -50 * PX, 0.0104, 2.0, (0.70, 0.72, 0.95))
    make_text("spec_red", "RED", SW, -50 * PX, 0.0104, 2.0, (0.95, 0.70, 0.66))
    make_text("spec_rest", "WHERE THE LINES SHOULD BE", 0, 50 * PX, 0.0100, 1.9, (0.70, 0.70, 0.74))
    make_text("spec_shift", "←  SHIFTED TOWARD BLUE", 0, -50 * PX, 0.0100, 1.9, ACCENT)
    make_text("cap_kms", "≈ 110 KM/S", 0, cy, 0.0205, 1.6)
    make_text("cap_kms_sub", "CLOSING SPEED, RELATIVE TO THE MILKY WAY", 0, cy - 0.028, 0.0102, 1.9, (0.70, 0.69, 0.76))
    make_text("cap_kmh", "≈ 400,000 KM PER HOUR", 0, cy, 0.0205, 1.6)
    make_text("cap_kmh_sub", "ROUGHLY THE DISTANCE TO THE MOON, EVERY HOUR", 0, cy - 0.028, 0.0102, 1.9, (0.70, 0.69, 0.76))
    make_text("cap_odds", "MERGER CHANCE:  ~50%  –  ~90%", 0, cy, 0.0205, 1.6, ACCENT)
    make_text("cap_odds_sub", "WITHIN 10 BILLION YEARS  ·  HUBBLE + GAIA STUDIES, 2025–2026", 0, cy - 0.028, 0.0102, 1.9, (0.70, 0.69, 0.76))
    for lid, txt in (("lab_mw", "MILKY WAY"), ("lab_m31", "ANDROMEDA"), ("lab_m33", "M33"), ("lab_lmc", "LMC")):
        make_text(lid, txt, 0, 0, 0.0096, 2.0, (0.74, 0.73, 0.80), align="LEFT")


# ------------------------------------------------------------------ camera choreography
def catmull(keys, ts):
    """keys: [(t, Vector)], Catmull-Rom in time with clamped ends; local time eased per segment."""
    if ts <= keys[0][0]:
        return keys[0][1].copy()
    if ts >= keys[-1][0]:
        return keys[-1][1].copy()
    for i in range(len(keys) - 1):
        t0, t1 = keys[i][0], keys[i + 1][0]
        if t0 <= ts <= t1:
            break
    p0 = keys[max(i - 1, 0)][1]
    p1 = keys[i][1]
    p2 = keys[i + 1][1]
    p3 = keys[min(i + 2, len(keys) - 1)][1]
    u = (ts - t0) / (t1 - t0)
    u = 0.5 * u + 0.5 * smooth(u)            # soften velocity changes at the keys
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


V = Vector
CAM_KEYS = [          # solved so the Milky Way / Andromeda land on chosen screen positions
    (8.6, V((-73, -72, 24))),
    (13.0, V((-113, -110, 37))),
    (19.0, V((-254, -331, 118))),
    (25.5, V((79, -922, 601))),
    (31.0, V((250, -871, 807))),
    (37.0, V((416, -633, 987))),
    (43.0, V((345, -438, 1047))),
    (50.0, V((327, -415, 1134))),
    (54.5, V((995, -926, 698))),
    (60.0, V((1174, -234, 180))),
]
TGT_KEYS = [
    (8.6, V((110, 3, 0))),
    (13.0, V((227, 37, 0))),
    (19.0, V((255, 31, 0))),
    (25.5, V((344, 3, 0))),
    (31.0, V((376, -11, 0))),
    (37.0, V((469, -11, 0))),
    (43.0, V((344, -3, 0))),
    (50.0, V((329, -2, 0))),
    (54.5, V((434, 25, 0))),
    (60.0, V((493, -4, 0))),
]


def chosen_point(p):
    """position along the chosen orbit at fraction p (0..1) of its length in time."""
    pts = CHOSEN["p3"]
    f = clamp(p) * (len(pts) - 1)
    i = min(int(f), len(pts) - 2)
    a = f - i
    return V(tuple(pts[i] * (1 - a) + pts[i + 1] * a))


def m31_follow_frac(ts):
    """how far (fraction of the chosen orbit) Andromeda has travelled at time ts."""
    return 0.085 * ramp(ts, 51.5, 60.5) ** 1.3


def camera_at(ts):
    loc = catmull(CAM_KEYS, ts)
    tgt = catmull(TGT_KEYS, ts)
    # final shot: the camera swings round behind Andromeda and drifts with it as it
    # starts to fall along the chosen path
    k = ramp(ts, 54.5, 60.0)
    if k > 0:
        loc = loc + (OBJ["m31"].location - P_M31) * k
    return loc, tgt


def place_camera(ts):
    loc, tgt = camera_at(ts)
    CAM.location = loc
    d = (tgt - loc).normalized()
    CAM.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return loc, tgt


# ------------------------------------------------------------------ per frame
LAST_ROT = {}


def set_color(ob, rgb, k):
    ob.color = (rgb[0] * k, rgb[1] * k, rgb[2] * k, 1.0)
    ob.hide_render = k <= 1e-4


def orbit_draw_frac(o, p):
    """paths advance in sync with (simulated) time: p is fraction of 10 Gyr."""
    n_full = 1 + int(10.0 / TU / 0.0025) // 8
    return clamp(p * n_full / max(1, len(o["pts"]) - 1))


def update(frame):
    sc = bpy.context.scene
    ts = (frame - 1) / FPS

    # ---------------- shot A: the 1912 plate
    pa = ramp(ts, 0.05, 1.1) * (1 - ramp(ts, 4.8, 6.2))
    flick = 1.0 + 0.025 * math.sin(ts * 17.3) * math.sin(ts * 5.1 + 1.3)
    set_param("plate_a", pa)
    set_param("plate_gain", 1.18 * flick * (1 - 0.35 * ramp(ts, 4.2, 5.8)))
    push = lerp(1.0, 1.12, ease(ts / 6.2))
    OBJ["plate"].scale = (TW * push, TW * push * 9 / 16, 1)
    OBJ["plate"].location = (lerp(0.0, -0.012, ease(ts / 6.2)), lerp(0.0, 0.006, ease(ts / 6.2)), -0.02)
    OBJ["plate"].rotation_euler = (0, 0, math.radians(lerp(-0.5, 0.4, ease(ts / 6.2))))
    OBJ["plate"].hide_render = pa <= 0.002

    # ---------------- shot B: the spectrum (sepia on the plate, then colour)
    sa = ramp(ts, 4.3, 5.4) * (1 - ramp(ts, 9.2, 10.4))
    set_param("spec_a", sa)
    set_param("spec_col", ramp(ts, 5.6, 7.0))
    set_param("spec_gain", lerp(0.8, 1.15, ramp(ts, 5.6, 7.0)))
    set_param("spec_z", 0.016 * ramp(ts, 6.3, 8.4))
    OBJ["spec"].hide_render = sa <= 0.002
    drift = lerp(1.0, 1.04, ease((ts - 4.3) / 6.0))
    OBJ["spec"].scale = (OBJ["spec_hw"] * drift, 34 * PX, 1)
    ta = window(ts, 5.9, 9.1, 0.8, 0.8) * 0.5
    OBJ["tick_mx"].inputs[0].default_value = ta
    for t in OBJ["ticks"]:
        x0 = t.get("x0")
        if x0 is None:
            t["x0"] = t.location.x
            x0 = t.location.x
        t.location.x = x0 * drift
        t.hide_render = ta <= 0.002
    set_alpha("spec_blue", window(ts, 6.0, 9.1, 0.9, 0.8) * 0.8)
    set_alpha("spec_red", window(ts, 6.0, 9.1, 0.9, 0.8) * 0.8)
    set_alpha("spec_rest", window(ts, 6.1, 7.6, 0.7, 0.6) * 0.7)
    set_alpha("spec_shift", window(ts, 7.6, 9.1, 0.7, 0.8) * 0.95)
    TEXTS["spec_blue"][0].location.x = -OBJ["spec_hw"] * drift
    TEXTS["spec_red"][0].location.x = OBJ["spec_hw"] * drift
    set_alpha("cap_slipher", window(ts, 1.5, 5.4, 0.9, 0.8))

    # ---------------- space
    # Andromeda falls along the chosen orbit in the last shot
    pf = m31_follow_frac(ts)
    OBJ["m31"].location = chosen_point(pf) if pf > 0 else P_M31
    spc = ramp(ts, 8.9, 10.8) * (1 - ramp(ts, 58.3, 59.85))
    loc, tgt = place_camera(max(ts, 8.6))
    bpy.context.view_layer.update()
    # backdrop parallax: offset the tileable field with camera yaw/pitch
    d = (tgt - loc).normalized()
    yaw = math.atan2(d.y, d.x)
    pitch = math.asin(clamp(d.z, -1, 1))
    if "yaw0" not in LAST_ROT:
        l0, t0_ = camera_at(8.6)
        d0 = (t0_ - l0).normalized()
        LAST_ROT["yaw0"] = math.atan2(d0.y, d0.x)
    k = 0.52 / (2 * math.atan(TW))           # texture widths per radian (frame = 0.52 of texture)
    mp = PARAM["space_mapping"][0]
    mp.inputs["Scale"].default_value = (0.52, 0.52 * 9 / 16, 1)
    mp.inputs["Location"].default_value = (-(yaw - LAST_ROT["yaw0"]) * k + 0.13, pitch * k + 0.21, 0)
    set_param("space", 1.35 * spc)
    set_param("mw", 1.05 * spc)
    set_param("m31", 1.15 * spc)
    set_param("m33", 1.1 * spc)
    set_param("lmc", 0.9 * spc)
    for key in ("mw", "m31", "m33", "lmc"):
        OBJ[key].hide_render = spc <= 0.002


    # line width ~1.3 px whatever the camera distance
    dist = (tgt - loc).length
    px_world = dist * 2 * TW / CONFIG["resolution"][0]
    lw = 0.62 * px_world
    px_m31 = (OBJ["m31"].location - loc).length * 2 * TW / CONFIG["resolution"][0]
    lw_m31 = 0.62 * px_m31

    # ---------------- head-on line (26-33)
    h = OBJ["headon"]
    hd = ramp(ts, 26.3, 29.6)
    hk = window(ts, 26.3, 32.6, 0.4, 3.0) * 0.55 * spc
    h.data.bevel_factor_end = max(0.001, hd)
    h.data.bevel_depth = lw
    set_color(h, (0.92, 0.90, 1.0), hk)
    hg = OBJ["glint_head"]
    gp = P_M31.lerp(P_MW, hd)
    hg.location = gp
    hg.rotation_euler = CAM.rotation_euler
    hg.scale = (9 * px_world, 9 * px_world, 1)
    set_color(hg, (1.0, 0.95, 1.0), 1.6 * hk * (1 - ramp(ts, 29.2, 30.0)))

    # ---------------- uncertainty fan (32-50) and the chosen path (50-60)
    stub = 0.055 * ramp(ts, 32.4, 35.0)
    grow = ramp(ts, 37.8, 47.5)
    p = stub + (1 - stub) * grow
    fan_k = ramp(ts, 32.4, 34.0) * spc
    tremble = (1 - ramp(ts, 36.0, 38.2)) * ramp(ts, 32.4, 33.5)
    follow = ramp(ts, 50.3, 53.5)
    for i, o in enumerate(ORBITS):
        ob, g = o["ob"], o["glint"]
        f = orbit_draw_frac(o, p)
        ob.data.bevel_factor_end = max(0.001, f)
        ob.data.bevel_depth = lw_m31 if o is CHOSEN and follow > 0 else lw
        ob.rotation_euler = (0, 0, math.radians(7.0 * tremble * math.sin(ts * 2.1 + o["phase"] * 6.28)))
        merges = o["merged"] is not None
        base = (0.86, 0.80, 1.0) if merges else (0.62, 0.70, 0.86)
        kk = (0.075 if merges else 0.05) * fan_k
        if o is CHOSEN:
            kk = lerp(kk, 0.42 * spc, follow)
            base = tuple(lerp(b, a, follow) for b, a in zip(base, ACCENT))
        else:
            kk *= 1 - 0.97 * follow
        set_color(ob, base, kk)
        # glint at the path tip ("where Andromeda could be")
        pts = o["p3"]
        fi = f * (len(pts) - 1)
        j = min(int(fi), len(pts) - 2)
        a = fi - j
        tip = V(tuple(pts[j] * (1 - a) + pts[j + 1] * a))
        g.location = tip
        g.rotation_euler = CAM.rotation_euler
        gs = 7 * (px_m31 if o is CHOSEN and follow > 0 else px_world)
        g.scale = (gs, gs, 1)
        done = f >= 0.999 and merges
        gk = 0.8 * fan_k * ramp(ts, 37.8, 39.0) * (0.0 if done else 1.0) * (1 - follow)
        set_color(g, (1.0, 0.94, 1.0) if merges else (0.80, 0.86, 1.0), gk)

    # ---------------- labels (projected world positions)
    lab = window(ts, 11.2, 35.5, 1.2, 1.4) * 0.8 * spc
    lab2 = window(ts, 13.0, 30.0, 1.2, 1.4) * 0.7 * spc
    for lid, P, off, aa in (("lab_mw", P_MW, (-0.7, -1.7), lab), ("lab_m31", OBJ["m31"].location.copy(), (0.95, 0.45), lab),
                            ("lab_m33", P_M33, (1.0, 0.4), lab2), ("lab_lmc", P_LMC, (1.2, -0.3), lab2)):
        co = world_to_camera_view(sc, CAM, V(P))
        ob, _ = TEXTS[lid]
        if co.z <= 0:
            set_alpha(lid, 0)
            continue
        # offset scaled by the object's apparent radius
        rad = {"lab_mw": HALF_MW, "lab_m31": HALF_M31, "lab_m33": HALF_M33, "lab_lmc": HALF_LMC}[lid] * 0.62
        rpx = rad / max(1e-3, co.z * 2 * TW) * 2 * TW
        hx = (co.x - 0.5) * 2 * TW + off[0] * rpx * 0.7 + 10 * PX
        hy = (co.y - 0.5) * 2 * TH + off[1] * rpx * 0.7
        ob.location = (hx, hy, 0)
        inside = 0.04 < co.x < 0.86 and 0.06 < co.y < 0.95
        set_alpha(lid, aa if inside else 0.0)

    # ---------------- captions
    set_alpha("cap_kms", window(ts, 12.3, 17.6, 0.9, 0.9))
    set_alpha("cap_kms_sub", window(ts, 12.9, 17.6, 0.9, 0.9) * 0.85)
    set_alpha("cap_kmh", window(ts, 18.8, 24.6, 0.9, 0.9))
    set_alpha("cap_kmh_sub", window(ts, 20.6, 24.6, 0.9, 0.9) * 0.85)
    set_alpha("cap_odds", window(ts, 41.0, 49.4, 1.0, 0.9))
    set_alpha("cap_odds_sub", window(ts, 41.8, 49.4, 1.0, 0.9) * 0.85)


# ------------------------------------------------------------------ main
def main():
    sc = reset_scene()
    build()
    out = arg("--out", CONFIG["output"])
    os.makedirs(out, exist_ok=True)
    nm = sum(o["merged"] is not None for o in ORBITS)
    print(f"[ch2] {N_FRAMES} frames -> {out}; ensemble {nm}/{len(ORBITS)} merge within 10 Gyr; "
          f"chosen vt={CHOSEN['vt']:.0f} km/s merges at {CHOSEN['merged']}", flush=True)
    frames = []
    if arg("--frames"):
        frames = [int(v) for v in arg("--frames").split(",")]
    elif "--render" in ARGV:
        a = int(arg("--start", 1))
        e = int(arg("--end", N_FRAMES))
        st = int(arg("--step", 1))
        frames = list(range(a, e + 1, st))
    skip = "--skip-existing" in ARGV
    if "--blend" in ARGV:
        update(int(arg("--blend-frame", 300)))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "ch2.blend"))
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
