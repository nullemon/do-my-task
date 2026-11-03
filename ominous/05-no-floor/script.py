"""
OMINOUS #5 - NO FLOOR
A fall through Jupiter's cloud decks: ammonia ice -> ammonium hydrosulfide ->
water clouds with lightning -> pressure without end.

Single self-contained, procedural Blender script (no downloads).
Clouds are faked cheaply: stacked emission/transparent planes driven by
numpy-generated tileable noise images. No volumetrics, no lights -> Cycles
output is noise-free at very low sample counts.

Run (Blender binary):   blender -b -P script.py -- --render
Run (bpy module):       python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
Options after "--":
    --render              render the full animation
    --frames 1,120,300    render only these frames (stills for review)
    --out DIR             output directory for PNG frames
    --pct N               resolution percentage (default from CONFIG)
"""

# ============================== CONFIG =====================================
CONFIG = dict(
    fps=24,
    duration=28.0,                 # seconds
    resolution=(1080, 1920),
    resolution_percentage=53,      # -> 576 x 1024 working render
    engine="CYCLES",               # CPU Cycles (no GPU here)
    samples=5,                     # emission-only + transparency = no noise, samples only for AA
    denoise=False,
    output="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/05/frames",
    font_text="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_mono="/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Light.ttf",
    accent=(0.62, 0.42, 1.0),      # storm violet
    offwhite=(0.86, 0.85, 0.82),
    seed=5,
)
# ===========================================================================

import sys, os, math, time
import numpy as np
import bpy

FPS = CONFIG["fps"]
NFRAMES = int(round(CONFIG["duration"] * FPS))

# ---------------------------------------------------------------------------
# Jupiter atmosphere model used by the HUD
#   T(P) = T0 * P^kappa  : dry adiabat fitted to the Galileo probe
#                          (166 K @ 1 bar, ~427 K @ ~22 bar -> kappa ~ 0.305)
#   z(P) = -(H0/kappa) * (P^kappa - 1)  : hydrostatic integration of that
#                          adiabat, H0 = R*T0/(mu*g), mu = 2.31 g/mol, g = 23.1
#                          -> 22 bar sits ~133 km below the 1-bar level
#                          (Seiff et al. 1998: ~132 km).  Beyond 22 bar it is
#                          an extrapolation.
# ---------------------------------------------------------------------------
T0, KAPPA = 166.0, 0.305
H0 = 8.314 * T0 / (2.31e-3 * 23.1) / 1000.0  # km

def atm_T(P):
    return max(110.0, T0 * P ** KAPPA)  # ~110 K floor = tropopause minimum

def atm_z(P):  # km, positive = above the 1-bar level
    return -(H0 / KAPPA) * (P ** KAPPA - 1.0)


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) interpolator."""
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    h = np.diff(xs); d = np.diff(ys) / h
    m = np.zeros_like(ys)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        x = min(max(x, xs[0]), xs[-1])
        i = min(np.searchsorted(xs, x, side="right") - 1, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        h00 = 2 * t**3 - 3 * t**2 + 1; h10 = t**3 - 2 * t**2 + t
        h01 = -2 * t**3 + 3 * t**2;    h11 = t**3 - t**2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f

# Story timeline (seconds) -> pressure (bar, log) and camera depth (scene units)
P_of_t = pchip([0, 4, 9, 14, 18.5, 21, 23.4, 26, 28],
               np.log10([0.25, 0.7, 2.0, 5.5, 22, 80, 300, 1000, 2000]))
D_of_t = pchip([0, 3.8, 7.6, 9.5, 14, 18.5, 23, 28],
               [-4.0, 8.5, 18.5, 24.5, 40.0, 52.0, 70.0, 98.0])

def pressure(t):
    return 10 ** P_of_t(t)

# ---------------------------------------------------------------------------
def smooth(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)

def env(t, t0, t1, fin=0.5, fout=0.6):
    return smooth(t0, t0 + fin, t) * (1.0 - smooth(t1 - fout, t1, t))

def lerp(a, b, x):
    return a + (b - a) * x

def lerp3(a, b, x):
    return tuple(lerp(a[i], b[i], x) for i in range(3))

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = CONFIG["samples"]
    cy.use_adaptive_sampling = False
    cy.use_denoising = CONFIG["denoise"]
    cy.max_bounces = 0
    cy.diffuse_bounces = 0
    cy.glossy_bounces = 0
    cy.transmission_bounces = 0
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 96
    try:
        cy.caustics_reflective = False; cy.caustics_refractive = False
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = CONFIG["resolution"]
    sc.render.resolution_percentage = CONFIG["resolution_percentage"]
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, NFRAMES
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    im = sc.render.image_settings
    if hasattr(im, "media_type"):
        try:
            im.media_type = "IMAGE"   # Blender 5.x: before file_format
        except Exception:
            pass
    im.file_format = "PNG"
    im.color_mode = "RGB"
    im.color_depth = "8"
    return sc


def make_noise_image(name, size, seed):
    """Tileable fBm-like noise in R,G,B via FFT power-law filtering."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.rfftfreq(size)[None, :]
    k = np.sqrt(fx * fx + fy * fy); k[0, 0] = 1.0
    chans = []
    for beta, lo in ((1.9, 0.0), (1.45, 4.0 / size), (2.3, 0.0)):
        spec = (rng.normal(size=k.shape) + 1j * rng.normal(size=k.shape)) * k ** (-beta)
        spec[k < lo] *= 0.15
        spec[0, 0] = 0
        n = np.fft.irfft2(spec, s=(size, size))
        n = (n - n.mean()) / (n.std() + 1e-9)
        n = 0.5 + 0.18 * n
        chans.append(np.clip(n, 0, 1))
    # cauliflower / billow look in G: fold
    chans[1] = np.clip(1.0 - np.abs(chans[1] - 0.5) * 2.0, 0, 1) ** 1.5
    rgba = np.dstack(chans + [np.ones((size, size))]).astype(np.float32)
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"   # must be set BEFORE writing pixels (it regenerates the buffer)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


# Cloud zone definitions along scene depth d (positive = downward)
# (d0, d1, spacing, colour, opacity, coverage_threshold, feature size, stretch, shade)
ZONES = [
    # high haze above the ammonia deck
    dict(d0=2.0,  d1=6.0,  sp=2.0, col=(0.80, 0.80, 0.80), op=0.18, thr=0.50, feat=60, st=4.0),
    # NH3 ice deck: cream-white, puffy, zonally sheared
    dict(d0=8.0,  d1=17.5, sp=0.8, col=(1.00, 0.94, 0.84), op=0.62, thr=0.42, feat=24, st=2.2),
    # thin gap
    dict(d0=18.5, d1=21.5, sp=1.5, col=(0.78, 0.62, 0.46), op=0.35, thr=0.55, feat=26, st=4.0),
    # NH4SH: ochre/brown
    dict(d0=22.0, d1=32.0, sp=0.95, col=(0.70, 0.46, 0.28), op=0.88, thr=0.46, feat=18, st=3.0),
    dict(d0=33.0, d1=35.5, sp=1.4, col=(0.32, 0.26, 0.24), op=0.40, thr=0.55, feat=26, st=4.0),
    # H2O clouds: towering, dark, lit by lightning
    dict(d0=36.0, d1=51.0, sp=0.9, col=(0.34, 0.34, 0.42), op=0.90, thr=0.44, feat=15, st=1.5),
    # the deep: sparse dark wisps forever
    dict(d0=53.0, d1=112.0, sp=1.6, col=(0.22, 0.18, 0.24), op=0.55, thr=0.53, feat=22, st=3.0),
]

SUN_TABLE = [(-10, 0.95), (8, 0.95), (11, 0.62), (14, 0.40), (17.5, 0.26), (22, 0.22),
             (26, 0.13), (31, 0.06), (36, 0.03), (44, 0.016), (52, 0.010), (120, 0.006)]

def sunlight(d):
    """Diffuse sunlight reaching depth d (scene units), log-interpolated."""
    xs = [a for a, b in SUN_TABLE]; ys = [math.log(b) for a, b in SUN_TABLE]
    return math.exp(float(np.interp(d, xs, ys)))


HAZE_STOPS = [
    (-6, (0.10, 0.12, 0.155), 26.0),
    (6, (0.20, 0.20, 0.215), 22.0),
    (17, (0.22, 0.17, 0.13), 16.0),
    (24, (0.16, 0.10, 0.06), 12.0),
    (34, (0.035, 0.028, 0.03), 10.0),
    (44, (0.010, 0.010, 0.016), 10.0),
    (56, (0.004, 0.003, 0.007), 12.0),
    (78, (0.003, 0.002, 0.005), 12.0),
    (104, (0.006, 0.0028, 0.0032), 12.0),
    (200, (0.006, 0.0028, 0.0032), 12.0),
]

def haze_at(d):
    st = HAZE_STOPS
    for i in range(len(st) - 1):
        a, b = st[i], st[i + 1]
        if d <= b[0]:
            x = smooth(a[0], b[0], d) if d >= a[0] else 0.0
            return lerp3(a[1], b[1], x), lerp(a[2], b[2], x)
    return st[-1][1], st[-1][2]


def build_globals_group():
    g = bpy.data.node_groups.new("NF_Globals", "ShaderNodeTree")
    if hasattr(g, "interface"):
        g.interface.new_socket("Haze", in_out="OUTPUT", socket_type="NodeSocketColor")
        g.interface.new_socket("HazeLen", in_out="OUTPUT", socket_type="NodeSocketFloat")
        g.interface.new_socket("Flash", in_out="OUTPUT", socket_type="NodeSocketColor")
        g.interface.new_socket("FlashR", in_out="OUTPUT", socket_type="NodeSocketFloat")
    else:  # very old API
        g.outputs.new("NodeSocketColor", "Haze"); g.outputs.new("NodeSocketFloat", "HazeLen")
        g.outputs.new("NodeSocketColor", "Flash"); g.outputs.new("NodeSocketFloat", "FlashR")
    out = g.nodes.new("NodeGroupOutput")
    haze = g.nodes.new("ShaderNodeRGB"); haze.name = "haze"
    hl = g.nodes.new("ShaderNodeValue"); hl.name = "hazelen"
    fl = g.nodes.new("ShaderNodeRGB"); fl.name = "flash"
    fr = g.nodes.new("ShaderNodeValue"); fr.name = "flashr"
    g.links.new(haze.outputs[0], out.inputs[0])
    g.links.new(hl.outputs[0], out.inputs[1])
    g.links.new(fl.outputs[0], out.inputs[2])
    g.links.new(fr.outputs[0], out.inputs[3])
    return g


def build_cloud_material(name, img, zone, d, flash_empty, glob, rng):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    N.clear()
    def node(t, **kw):
        n = N.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n
    def math_(op, a=None, b=None, clamp=False):
        n = node("ShaderNodeMath", operation=op); n.use_clamp = clamp
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]

    out = node("ShaderNodeOutputMaterial")
    oi = node("ShaderNodeObjectInfo")   # Color = haze colour, Alpha = flash intensity (set per frame, no recompile)
    tc = node("ShaderNodeTexCoord")
    mp = node("ShaderNodeMapping"); mp.name = "map"
    feat = zone["feat"] * rng.uniform(0.8, 1.25)
    mp.inputs["Scale"].default_value = (1.0 / (feat * zone["st"]), 1.0 / feat, 1.0)
    mp.inputs["Location"].default_value = (rng.uniform(0, 1), rng.uniform(0, 1), 0)
    mp.inputs["Rotation"].default_value = (0, 0, rng.uniform(-0.12, 0.12))
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    tex = node("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Linear"
    L.new(mp.outputs[0], tex.inputs[0])
    # second sample offset towards the "sun" for fake relief shading
    off = node("ShaderNodeVectorMath", operation="ADD")
    off.inputs[1].default_value = (0.006, 0.010, 0)
    L.new(mp.outputs[0], off.inputs[0])
    tex2 = node("ShaderNodeTexImage"); tex2.image = img; tex2.interpolation = "Linear"
    L.new(off.outputs[0], tex2.inputs[0])
    sep = node("ShaderNodeSeparateColor"); L.new(tex.outputs[0], sep.inputs[0])
    sep2 = node("ShaderNodeSeparateColor"); L.new(tex2.outputs[0], sep2.inputs[0])
    wa, wb = 0.74, 0.26
    dens = math_("ADD", math_("MULTIPLY", sep.outputs[0], wa), math_("MULTIPLY", sep.outputs[1], wb))
    dens2 = math_("ADD", math_("MULTIPLY", sep2.outputs[0], wa), math_("MULTIPLY", sep2.outputs[1], wb))
    # coverage
    mr = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    L.new(dens, mr.inputs["Value"])
    mr.inputs["From Min"].default_value = zone["thr"]
    mr.inputs["From Max"].default_value = zone["thr"] + 0.17
    cov = mr.outputs[0]
    # near fade so planes never slam into the lens
    cam = node("ShaderNodeCameraData")
    nf = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    L.new(cam.outputs["View Distance"], nf.inputs["Value"])
    nf.inputs["From Min"].default_value = 0.25; nf.inputs["From Max"].default_value = 1.6
    alpha = math_("MULTIPLY", math_("MULTIPLY", cov, zone["op"]), nf.outputs[0])
    # fade planes seen edge-on (kills streaks / aliasing at the horizon)
    lw = node("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    gz = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    L.new(lw.outputs["Facing"], gz.inputs["Value"])
    gz.inputs["From Min"].default_value = 0.97; gz.inputs["From Max"].default_value = 0.80
    alpha = math_("MULTIPLY", alpha, gz.outputs[0])
    # relief shading (lit from above-ish) + density brightening
    rel = math_("ADD", math_("MULTIPLY", math_("SUBTRACT", dens, dens2), 16.0), 0.55)
    rel = math_("MAXIMUM", rel, 0.10)
    edge = math_("MULTIPLY", math_("SUBTRACT", dens, zone["thr"]), 5.0, clamp=True)
    bright = math_("MULTIPLY", rel, math_("ADD", math_("MULTIPLY", edge, 0.8), 0.3))
    sun = sunlight(d)
    base = tuple(c * sun for c in zone["col"])
    # light that reaches deep is filtered warm/brown
    warm = 1.0 - min(1.0, sun / 1.25)
    base = (base[0], base[1] * (1 - 0.15 * warm), base[2] * (1 - 0.35 * warm))
    # far below the probe's reach the gas is >1000 K: a faint thermal ember glow from beneath
    th = 0.028 * smooth(66.0, 110.0, d)
    base = (base[0] + th * 1.0, base[1] + th * 0.42, base[2] + th * 0.36)
    colnode = node("ShaderNodeRGB"); colnode.outputs[0].default_value = (*base, 1)
    cm = node("ShaderNodeMixRGB", blend_type="MULTIPLY"); cm.inputs[0].default_value = 1.0
    L.new(colnode.outputs[0], cm.inputs[1])
    L.new(bright, cm.inputs[2])
    # lightning: 3D falloff around the flash empty, lights the cloud mass from inside
    tcf = node("ShaderNodeTexCoord"); tcf.object = flash_empty
    ln = node("ShaderNodeVectorMath", operation="LENGTH")
    L.new(tcf.outputs["Object"], ln.inputs[0])
    q = ln.outputs["Value"]          # flash radius = empty scale
    fall = math_("DIVIDE", 1.0, math_("ADD", math_("MULTIPLY", q, q), 0.06))
    fall = math_("MULTIPLY", fall, math_("ADD", math_("MULTIPLY", math_("MULTIPLY", dens, dens), 2.4), 0.05))
    fall = math_("MULTIPLY", fall, oi.outputs["Alpha"])
    fc = lerp3(CONFIG["accent"], (0.9, 0.88, 1.0), 0.35)
    fm = node("ShaderNodeMixRGB", blend_type="MULTIPLY"); fm.inputs[0].default_value = 1.0
    fm.inputs[1].default_value = (*fc, 1)
    L.new(fall, fm.inputs[2])
    add = node("ShaderNodeMixRGB", blend_type="ADD"); add.inputs[0].default_value = 1.0
    L.new(cm.outputs[0], add.inputs[1]); L.new(fm.outputs[0], add.inputs[2])
    # aerial perspective / murk
    hl = haze_at(d)[1]
    fog = math_("SUBTRACT", 1.0, math_("EXPONENT", math_("MULTIPLY", cam.outputs["View Distance"], -1.0 / hl)))
    hm = node("ShaderNodeMixRGB", blend_type="MIX")
    L.new(fog, hm.inputs[0]); L.new(add.outputs[0], hm.inputs[1]); L.new(oi.outputs["Color"], hm.inputs[2])
    em = node("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    L.new(hm.outputs[0], em.inputs["Color"])
    tr = node("ShaderNodeBsdfTransparent")
    mix = node("ShaderNodeMixShader")
    L.new(alpha, mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.blend_method = "BLEND"
    except Exception:
        pass
    return m, mp, feat


def build_text_material(name, color, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    oi = N.new("ShaderNodeObjectInfo")
    L.new(oi.outputs["Alpha"], mix.inputs[0])
    L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    return m, None


def build_scrim_material():
    """Black with alpha = top band (HUD) + centre glow (obj colour A) + lower band (obj colour R)."""
    m = bpy.data.materials.new("NF_Scrim_M")
    m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    N.clear()
    def mth(op, a, b=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    def ss(v, a, b):
        n = N.new("ShaderNodeMapRange"); n.interpolation_type = "SMOOTHSTEP"
        L.new(v, n.inputs["Value"]); n.inputs["From Min"].default_value = a; n.inputs["From Max"].default_value = b
        return n.outputs[0]
    out = N.new("ShaderNodeOutputMaterial")
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    oi = N.new("ShaderNodeObjectInfo")
    sepc = N.new("ShaderNodeSeparateColor"); L.new(oi.outputs["Color"], sepc.inputs[0])
    x = sep.outputs[0]; y = sep.outputs[1]          # object space, -0.5..0.5
    top = mth("MULTIPLY", ss(y, 0.22, 0.46), 0.72)
    r = mth("SQRT", mth("ADD", mth("MULTIPLY", mth("MULTIPLY", x, x), 0.32), mth("MULTIPLY", y, y)))
    cen = mth("MULTIPLY", mth("SUBTRACT", 1.0, ss(r, 0.04, 0.36)), mth("MULTIPLY", oi.outputs["Alpha"], 0.80))
    yl = mth("ABSOLUTE", mth("ADD", y, 0.30))
    low = mth("MULTIPLY", mth("SUBTRACT", 1.0, ss(yl, 0.0, 0.14)), mth("MULTIPLY", sepc.outputs[0], 0.72))
    a = mth("MAXIMUM", mth("MAXIMUM", top, cen), low)
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0, 0, 0, 1)
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    L.new(a, mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    return m


def load_font(path):
    try:
        if path and os.path.exists(path):
            return bpy.data.fonts.load(path)
    except Exception:
        pass
    return None


class Scene:
    pass


def build():
    S = Scene()
    sc = reset_scene()
    S.sc = sc
    rng = np.random.default_rng(CONFIG["seed"])

    # world
    w = bpy.data.worlds.new("NF_World"); sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    S.world_bg = bg
    try:
        w.cycles.sampling_method = "NONE"
    except Exception:
        pass

    S.glob = None
    S.flash_empty = bpy.data.objects.new("NF_Flash", None)
    sc.collection.objects.link(S.flash_empty)

    img = make_noise_image("NF_Noise", 1024, CONFIG["seed"])

    # cloud planes
    S.planes = []
    mesh_cache = {}
    for zi, z in enumerate(ZONES):
        d = z["d0"]
        while d <= z["d1"]:
            dd = d + rng.uniform(-0.2, 0.2) * z["sp"]
            size = 700.0
            if size not in mesh_cache:
                me = bpy.data.meshes.new("NF_Plane")
                s = size / 2
                me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
                me.update()
                mesh_cache[size] = me
            me = mesh_cache[size].copy()
            ob = bpy.data.objects.new(f"NF_Cloud_{zi}_{len(S.planes):03d}", me)
            ob.location = (0, 0, -dd)
            sc.collection.objects.link(ob)
            mat, mp, feat = build_cloud_material(ob.name + "_M", img, z, dd, S.flash_empty, S.glob, rng)
            me.materials.append(mat)
            base = tuple(mp.inputs["Location"].default_value)
            # zonal wind shear: alternate directions like Jupiter's jets
            wind = rng.uniform(0.010, 0.030) * (1 if (len(S.planes) // 3) % 2 == 0 else -1)
            S.planes.append(dict(ob=ob, d=dd, mp=mp, base=base, wind=wind, feat=feat))
            d += z["sp"]

    # camera
    camd = bpy.data.cameras.new("NF_Cam")
    camd.lens = 20.0
    camd.sensor_width = 36.0
    camd.sensor_fit = "AUTO"
    camd.clip_start = 0.01
    camd.clip_end = 2000
    cam = bpy.data.objects.new("NF_Camera", camd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    S.cam = cam
    # text rig: a child of the camera; HUD plane at distance HD
    HD = 0.12
    vfov = 2 * math.atan(camd.sensor_width / 2 / camd.lens)  # portrait: sensor spans height
    H = 2 * HD * math.tan(vfov / 2)
    W = H * CONFIG["resolution"][0] / CONFIG["resolution"][1]
    S.H, S.W, S.HD = H, W, HD

    ftext = load_font(CONFIG["font_text"])
    fmono = load_font(CONFIG["font_mono"])

    def text(name, body, x, y, size, font, color, align="CENTER", spacing=1.25, strength=1.0):
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = body
        if font: cu.font = font
        cu.size = size * H
        cu.align_x = align
        cu.align_y = "CENTER"
        cu.space_character = spacing
        cu.space_line = 1.35
        ob = bpy.data.objects.new(name, cu)
        ob.parent = cam
        ob.location = (x * W, y * H, -HD)
        sc.collection.objects.link(ob)
        mat, _ = build_text_material(name + "_M", color, strength)
        cu.materials.append(mat)
        return dict(ob=ob, cu=cu)

    ow, ac = CONFIG["offwhite"], CONFIG["accent"]
    S.t_hook1 = text("T_hook1", "JUPITER HAS NO SURFACE.", 0, 0.035, 0.028, ftext, ow, spacing=1.35, strength=1.6)
    S.t_hook2 = text("T_hook2", "THIS IS WHAT FALLING IN LOOKS LIKE.", 0, -0.012, 0.0165, ftext, ow, spacing=1.45, strength=1.3)
    S.t_big = text("T_big", "", 0, 0.0, 0.034, ftext, ow, spacing=1.5, strength=1.3)
    S.t_lay1 = text("T_lay1", "", 0, -0.285, 0.0175, ftext, ow, spacing=1.5, strength=1.4)
    S.t_lay2 = text("T_lay2", "", 0, -0.315, 0.0135, fmono, ac, spacing=1.3, strength=2.0)
    # HUD (top-left), labels dim off-white, values accent
    hx = -0.40
    S.t_hudl = text("T_hudl", "PRESSURE\nTEMPERATURE\nALTITUDE", hx, 0.402, 0.0132, fmono, ow, align="LEFT", spacing=1.15, strength=0.8)
    S.t_hudv = text("T_hudv", "", 0.40, 0.402, 0.0132, fmono, ac, align="RIGHT", spacing=1.15, strength=2.0)
    S.t_hudh = text("T_hudh", "JUPITER  /  DESCENT", hx, 0.452, 0.0110, fmono, ow, align="LEFT", spacing=1.35, strength=0.6)

    # thin accent rule under the HUD
    me = bpy.data.meshes.new("NF_Rule")
    s = 0.5
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    rule = bpy.data.objects.new("NF_Rule", me)
    rule.parent = cam
    rule.location = (0, 0.432 * H, -HD)
    rule.scale = (0.80 * W, 0.0009 * H, 1)
    sc.collection.objects.link(rule)
    rm, ra = build_text_material("NF_Rule_M", ow, 0.35)
    me.materials.append(rm)
    S.rule = dict(ob=rule)

    # soft dark scrim behind the typography (keeps off-white text legible over bright cloud)
    me = bpy.data.meshes.new("NF_Scrim")
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    scrim = bpy.data.objects.new("NF_Scrim", me)
    scrim.parent = cam
    scrim.location = (0, 0, -HD * 1.3)
    scrim.scale = (W * 1.3 * 1.02, H * 1.3 * 1.02, 1)
    sc.collection.objects.link(scrim)
    me.materials.append(build_scrim_material())
    S.scrim = scrim

    S.flashes = make_flashes(rng)
    return S


# ---------------------------------------------------------------------------
# Lightning schedule (seconds). Each event: multi-stroke flicker.
# ---------------------------------------------------------------------------
def make_flashes(rng):
    ev = []
    times = [11.6, 12.9, 13.6, 14.8, 15.3, 16.4, 17.1, 18.0, 19.2, 20.3, 21.9, 23.6, 25.1, 26.8]
    for i, t0 in enumerate(times):
        deep = t0 > 19.5
        strokes = []
        tt = t0
        for k in range(int(rng.integers(2, 5))):
            strokes.append((tt, rng.uniform(0.05, 0.11), rng.uniform(0.5, 1.0)))
            tt += rng.uniform(0.06, 0.16)
        ang = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(4, 11)
        ev.append(dict(
            strokes=strokes,
            xy=(r * math.cos(ang), r * math.sin(ang)),
            below=(rng.uniform(4, 8) if not deep else rng.uniform(9, 18)),
            amp=(rng.uniform(0.9, 1.6) if not deep else rng.uniform(0.7, 1.2)),
            uv=(rng.uniform(-0.8, 0.8), rng.uniform(-0.5, 0.9)),
            rad=(rng.uniform(1.3, 2.0) if not deep else rng.uniform(1.8, 2.8)),
        ))
    return ev


def flash_state(S, t, camd):
    best = None
    for e in S.flashes:
        v = 0.0
        for (s0, dur, a) in e["strokes"]:
            if t >= s0:
                x = (t - s0) / dur
                v = max(v, a * math.exp(-x * 2.2) if x < 6 else 0.0)
        if v > 0.003 and (best is None or v * e["amp"] > best[0]):
            best = (v * e["amp"], e)
    return best


# ---------------------------------------------------------------------------
def fmt_p(P):
    if P < 10: return f"{P:5.2f} BAR"
    if P < 100: return f"{P:5.1f} BAR"
    return f"{P:,.0f} BAR"


def setalpha(o, a):
    o["ob"].color = (1, 1, 1, float(a))


def update(S, frame):
    t = (frame - 1) / FPS
    sc = S.sc
    camd = D_of_t(t)
    # camera: begins tilted toward the hazy horizon, rotates to face straight down
    tilt = lerp(math.radians(50), math.radians(34), smooth(0.0, 9.0, t))
    tilt = lerp(tilt, math.radians(18), smooth(19.0, 27.0, t)) + math.radians(4) * math.sin(t * 0.35)
    spin = 0.5 + 0.05 * t + 0.0016 * t * t  # slow helical fall
    shake = 0.002 + 0.006 * smooth(10, 20, t)
    jx = shake * (math.sin(t * 7.3) + 0.6 * math.sin(t * 13.1 + 1.0))
    jy = shake * (math.sin(t * 6.1 + 2.0) + 0.6 * math.sin(t * 11.7))
    S.cam.rotation_mode = "ZXY"
    S.cam.rotation_euler = (tilt + jx, jy, spin)
    S.cam.location = (0.4 * math.sin(t * 0.21), 0.3 * math.cos(t * 0.17), -camd)

    # visible window of planes
    for p in S.planes:
        vis = (camd - 0.2) < p["d"] < (camd + 22.0)
        p["ob"].hide_render = not vis
        if vis:
            b = p["base"]
            p["ob"].location.x = p["wind"] * p["feat"] * 3.0 * t

    # global haze colour tracks where the camera is (stored in object colour -> no shader recompile)
    haze, _ = haze_at(camd)
    S.world_bg.inputs["Color"].default_value = (*haze, 1)
    S.world_bg.inputs["Strength"].default_value = 1.0
    fs = flash_state(S, t, camd)
    fval = 0.0
    if fs:
        fval, e = fs
        # place the flash along a ray inside the frame (u,v in normalised screen space)
        import mathutils
        bpy.context.view_layer.update()
        mw = S.cam.matrix_world
        u, v = e["uv"]
        ray = (mw.to_3x3() @ mathutils.Vector((u * 0.4, v * 0.7, -1.0))).normalized()
        dz = max(-ray.z, 0.15)
        pos = mw.translation + ray * (e["below"] / dz)
        S.flash_empty.location = pos
        S.flash_empty.scale = (e["rad"],) * 3
    for p in S.planes:
        if not p["ob"].hide_render:
            p["ob"].color = (*haze, fval)

    # ---------------- typography ----------------
    setalpha(S.t_hook1, env(t, 0.12, 3.6, 0.35, 0.7))
    setalpha(S.t_hook2, env(t, 0.75, 3.6, 0.45, 0.7) * 0.9)

    layers = [
        (3.9, 7.7, "AMMONIA ICE CLOUDS", "~0.7 BAR  /  -120 C"),
        (8.6, 12.6, "AMMONIUM HYDROSULFIDE", "~2 BAR  /  SUNLIGHT FADING"),
        (13.3, 17.4, "WATER CLOUDS", "~5 BAR  /  LIGHTNING"),
        (17.9, 21.2, "GALILEO PROBE, 1995", "LAST SIGNAL  /  ~22 BAR"),
    ]
    a1 = 0.0
    for (t0, t1, l1, l2) in layers:
        e = env(t, t0, t1, 0.5, 0.6)
        if e > 0:
            S.t_lay1["cu"].body = l1
            S.t_lay2["cu"].body = l2
            a1 = e
    setalpha(S.t_lay1, a1)
    setalpha(S.t_lay2, a1 * 0.95)

    bigs = [(21.6, 24.0, "NO SURFACE."), (24.2, 26.2, "JUST PRESSURE."), (26.3, 28.5, "NO FLOOR.")]
    ab = 0.0
    for (t0, t1, s) in bigs:
        e = env(t, t0, t1, 0.4, 0.45 if s != "NO FLOOR." else 0.01)
        if e > 0:
            S.t_big["cu"].body = s
            ab = e
    setalpha(S.t_big, ab)
    hook = max(env(t, 0.0, 3.6, 0.2, 0.7), ab)
    S.scrim.color = (a1, 0, 0, hook)

    P = pressure(t)
    T = atm_T(P)
    z = atm_z(P)
    label3 = "ALTITUDE" if z > 0 else "DEPTH"
    S.t_hudl["cu"].body = f"PRESSURE\nTEMPERATURE\n{label3}"
    zz = abs(z)
    S.t_hudv["cu"].body = f"{fmt_p(P)}\n{T:,.0f} K\n{zz:,.0f} KM"
    hud_a = smooth(0.3, 1.0, t) * (1.0 - smooth(27.6, 28.0, t))
    for o in (S.t_hudl, S.t_hudv, S.rule):
        setalpha(o, hud_a)
    setalpha(S.t_hudh, hud_a * 0.9)
    return t


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    a = dict(render=False, frames=None, out=CONFIG["output"], pct=None)
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--render": a["render"] = True
        elif k == "--frames": a["frames"] = [int(x) for x in argv[i + 1].split(",")]; i += 1
        elif k == "--out": a["out"] = argv[i + 1]; i += 1
        elif k == "--pct": a["pct"] = int(argv[i + 1]); i += 1
        i += 1
    return a


def main():
    args = parse_args()
    S = build()
    if args["pct"]:
        S.sc.render.resolution_percentage = args["pct"]
    frames = args["frames"] if args["frames"] else (list(range(1, NFRAMES + 1)) if args["render"] else [])
    if not frames:
        print("[no-floor] scene built; pass --render or --frames to render")
        return
    os.makedirs(args["out"], exist_ok=True)
    t_all = time.time()
    for f in frames:
        path = os.path.join(args["out"], f"f_{f:04d}.png")
        if args["render"] and not args["frames"] and os.path.exists(path):
            continue  # resumable
        S.sc.frame_set(f)
        update(S, f)
        S.sc.render.filepath = path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[no-floor] frame {f} t={(f-1)/FPS:5.2f}s  {time.time()-t0:5.2f}s", flush=True)
    print(f"[no-floor] done {len(frames)} frames in {time.time()-t_all:.1f}s")


main()
