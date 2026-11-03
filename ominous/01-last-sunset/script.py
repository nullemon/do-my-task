"""
OMINOUS #1 - THE LAST SUNSET
A lone ridge on a barren world. The year counter runs from today (1.38e10 yr)
to 1e14 yr. Blue/white stars burn out first, the sky thins to red dwarfs,
then the last dim red dwarf sets behind the ridge. Black.

Fully procedural (no downloads). Emission-only shading, so Cycles is noise-free
at low sample counts and needs no denoiser.

Run headless:
    blender -b -P script.py -- --render
    blender -b -P script.py -- --render --frames 1,240,500   (stills only)
    blender -b -P script.py -- --render --out /some/dir/
    blender -b -P script.py -- --render --out /some/dir/ --resume   (skip existing frames)
With the bpy Python module instead of the blender binary:
    python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
"""

# =============================== CONFIG ====================================
FPS = 24
DURATION_S = 27.0
RES_X, RES_Y = 1080, 1920
RES_PERCENT = 53                 # 53% -> 572x1018 (final encode is scaled to 576x1024)
ENGINE = "CYCLES"                # emission-only scene; Cycles CPU is robust headless
SAMPLES = 8
DEVICE = "CPU"
OUTPUT_DIR = "frames/"           # relative to this script; overridden by --out
FILE_PREFIX = "f_"
SEED = 7
FONT_TEXT = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
FONT_NUM = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Light.ttf"
TEXT_COLOR = (0.86, 0.84, 0.80)
# ===========================================================================

import bpy
import math
import random
import sys
import os

FRAMES = int(round(DURATION_S * FPS))


# ----------------------------------------------------------------- helpers --
def smoothstep(a, b, x):
    if a == b:
        return 1.0 if x >= b else 0.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def fade_window(t, t0, t1, fin=0.6, fout=0.8):
    """0 -> 1 -> 0 envelope for a text beat."""
    return smoothstep(t0, t0 + fin, t) * (1.0 - smoothstep(t1 - fout, t1, t))


def args_after_dashes():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


# ----------------------------------------------------------- timeline ------
# All story timing lives here (seconds).
T_COUNT_START = 4.5     # counter holds at "today" until here
T_COUNT_END = 21.6      # 1e14 reached at the moment of sunset
T_SUNSET = 21.6         # sun disk fully behind the ridge
T_BLACK = 23.2          # afterglow gone

TEXT_BEATS = [
    # key, text, t_in, t_out, y (camera-space), size
    ("hook", "THIS IS THE LAST SUNSET\nTHE UNIVERSE WILL EVER HAVE.", 0.10, 4.3, -0.40, 0.0235),
    ("b1", "THE BRIGHTEST STARS DIE FIRST.", 5.4, 9.6, -0.40, 0.0235),
    ("b2", "THEN THE GAS RUNS OUT.\nNO NEW STARS ARE BORN.", 10.4, 14.6, -0.40, 0.0235),
    ("b3", "THE LAST ONES ARE RED DWARFS.\nTHEY BURN FOR TRILLIONS OF YEARS.", 15.4, 19.8, -0.40, 0.0235),
    ("end", "AFTER THIS,\nNOTHING EVER SHINES AGAIN.", 23.5, 26.6, -0.02, 0.0260),
]


def star_death(t):
    """Lifetime threshold: stars whose random 'lifetime' r < death are gone.
    r low = hot blue/white (short lived), r high = red dwarf (longest)."""
    keys = [(0.0, -0.03), (5.2, -0.03), (11.0, 0.50), (15.5, 0.80), (18.5, 0.93), (20.6, 1.06)]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return lerp(v0, v1, smoothstep(t0, t1, t) if t1 > t0 else 1.0)
    return keys[-1][1]


def year_exponent(t):
    e0, e1 = math.log10(1.38e10), 14.0
    u = smoothstep(T_COUNT_START, T_COUNT_END, t) if t < T_COUNT_END else 1.0
    # gentle ease-in so it visibly accelerates, but keeps moving at the end
    u = (min(1.0, max(0.0, (t - T_COUNT_START) / (T_COUNT_END - T_COUNT_START)))) ** 1.35
    return lerp(e0, e1, u)


def format_years(e):
    v = 10 ** e
    digits = int(math.floor(math.log10(v)))
    q = 10 ** (digits - 2)                  # 3 significant figures
    v = int(round(v / q) * q)
    return f"{v:,}"


# --------------------------------------------------------------- scene -----
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = FRAMES
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.resolution_percentage = RES_PERCENT
    sc.render.engine = ENGINE
    cy = sc.cycles
    cy.device = DEVICE
    cy.samples = SAMPLES
    try:
        cy.use_adaptive_sampling = False
    except Exception:
        pass
    cy.use_denoising = False          # emission only -> no path noise to remove
    cy.max_bounces = 0
    cy.diffuse_bounces = 0
    cy.glossy_bounces = 0
    cy.transmission_bounces = 0
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    sc.render.film_transparent = False
    sc.render.filter_size = 1.2
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    # output (5.x needs media_type before file_format)
    ims = sc.render.image_settings
    if hasattr(ims, "media_type"):
        try:
            ims.media_type = "IMAGE"
        except Exception:
            pass
    ims.file_format = "PNG"
    ims.color_mode = "RGB"
    ims.color_depth = "8"
    ims.compression = 15
    return sc


def node(nt, typ, loc=(0, 0), **props):
    n = nt.nodes.new(typ)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def math_node(nt, op, a=None, b=None, va=None, vb=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    if a is not None:
        nt.links.new(a, n.inputs[0])
    elif va is not None:
        n.inputs[0].default_value = va
    if b is not None:
        nt.links.new(b, n.inputs[1])
    elif vb is not None:
        n.inputs[1].default_value = vb
    return n


def value_node(nt, name, v):
    n = nt.nodes.new("ShaderNodeValue")
    n.name = name
    n.label = name
    n.outputs[0].default_value = v
    return n


def map_range(nt, x, fmin, fmax, tmin=0.0, tmax=1.0, fmin_sock=None, fmax_sock=None, interp="LINEAR"):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.interpolation_type = interp
    n.clamp = True
    nt.links.new(x, n.inputs["Value"])
    if fmin_sock is not None:
        nt.links.new(fmin_sock, n.inputs["From Min"])
    else:
        n.inputs["From Min"].default_value = fmin
    if fmax_sock is not None:
        nt.links.new(fmax_sock, n.inputs["From Max"])
    else:
        n.inputs["From Max"].default_value = fmax
    n.inputs["To Min"].default_value = tmin
    n.inputs["To Max"].default_value = tmax
    return n


def color_ramp(nt, x, stops):
    n = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(x, n.inputs[0])
    el = n.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = el.new(p)
        e.color = (*c, 1)
    return n


def vec_scale(nt, vec_sock, scalar_sock):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = "SCALE"
    nt.links.new(vec_sock, n.inputs[0])
    nt.links.new(scalar_sock, n.inputs["Scale"])
    return n


def vec_add(nt, a, b):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = "ADD"
    nt.links.new(a, n.inputs[0])
    nt.links.new(b, n.inputs[1])
    return n


# ---------------------------------------------------------------- world ----
STAR_COLORS = [   # lifetime r -> colour (short-lived hot blue ... long-lived red dwarf)
    (0.00, (0.55, 0.68, 1.00)),
    (0.22, (0.78, 0.85, 1.00)),
    (0.42, (1.00, 0.97, 0.92)),
    (0.55, (1.00, 0.86, 0.62)),
    (0.70, (1.00, 0.62, 0.36)),
    (0.84, (1.00, 0.36, 0.18)),
    (1.00, (0.90, 0.16, 0.08)),
]


def star_layer(nt, vec, scale, radius, density, strength, death_sock, seed_offset):
    """Voronoi point stars on the view sphere. Returns an emission colour socket."""
    off = nt.nodes.new("ShaderNodeVectorMath")
    off.operation = "ADD"
    nt.links.new(vec, off.inputs[0])
    off.inputs[1].default_value = (seed_offset, seed_offset * 1.7, seed_offset * 0.3)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.feature = "F1"
    vor.distance = "EUCLIDEAN"
    nt.links.new(off.outputs[0], vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = scale
    if "Randomness" in vor.inputs:
        vor.inputs["Randomness"].default_value = 1.0
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs[0])
    r, g, b = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    # point profile
    core = map_range(nt, vor.outputs["Distance"], 0.0, radius, 1.0, 0.0)
    core2 = math_node(nt, "POWER", core.outputs[0], vb=2.2)
    # keep only a fraction of cells
    sel = math_node(nt, "LESS_THAN", b, vb=density)
    # alive: fades out as the death threshold passes this star's lifetime
    d_hi = math_node(nt, "ADD", death_sock, vb=0.045)
    alive = map_range(nt, r, 0, 1, 0.0, 1.0, fmin_sock=death_sock, fmax_sock=d_hi.outputs[0],
                      interp="SMOOTHSTEP")
    # brightness: hot stars are intrinsically brighter; random magnitude spread
    g3 = math_node(nt, "POWER", g, vb=3.0)
    hot = map_range(nt, r, 0.0, 1.0, 1.5, 0.95)
    br = math_node(nt, "MULTIPLY", g3.outputs[0], hot.outputs[0])
    br = math_node(nt, "ADD", br.outputs[0], vb=0.12)
    m = math_node(nt, "MULTIPLY", core2.outputs[0], sel.outputs[0])
    m = math_node(nt, "MULTIPLY", m.outputs[0], alive.outputs[0])
    m = math_node(nt, "MULTIPLY", m.outputs[0], br.outputs[0])
    m = math_node(nt, "MULTIPLY", m.outputs[0], vb=strength)
    col = color_ramp(nt, r, STAR_COLORS)
    out = vec_scale(nt, col.outputs[0], m.outputs[0])
    return out.outputs[0]


def build_world(sc):
    w = bpy.data.worlds.new("Sky")
    sc.world = w
    w.use_nodes = True
    try:
        w.cycles.sampling_method = "NONE"     # no importance map rebuild per frame
    except Exception:
        try:
            w.cycles.sample_as_light = False
        except Exception:
            pass
    nt = w.node_tree
    nt.nodes.clear()
    outn = node(nt, "ShaderNodeOutputWorld")
    bg = node(nt, "ShaderNodeBackground")
    nt.links.new(bg.outputs[0], outn.inputs[0])

    tc = node(nt, "ShaderNodeTexCoord")
    D = tc.outputs["Generated"]          # world: normalized view direction
    nrm = nt.nodes.new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    nt.links.new(D, nrm.inputs[0])
    D = nrm.outputs[0]

    v_death = value_node(nt, "death", 0.0)
    v_rot = value_node(nt, "sky_rot", 0.0)
    v_band = value_node(nt, "band", 1.0)
    v_sun_i = value_node(nt, "sun_i", 1.0)
    v_haze = value_node(nt, "haze", 0.0)
    sun_dir = node(nt, "ShaderNodeCombineXYZ")
    sun_dir.name = "sun_dir"

    rot = node(nt, "ShaderNodeVectorRotate")
    rot.rotation_type = "AXIS_ANGLE"
    nt.links.new(D, rot.inputs["Vector"])
    rot.inputs["Axis"].default_value = (0.25, 0.55, 0.80)
    nt.links.new(v_rot.outputs[0], rot.inputs["Angle"])
    R = rot.outputs[0]

    death = v_death.outputs[0]
    s1 = star_layer(nt, R, 260.0, 0.17, 0.70, 1.0, death, 0.0)      # faint dust of stars
    s2 = star_layer(nt, R, 95.0, 0.12, 0.45, 3.0, death, 13.37)      # brighter sparse stars
    s3 = star_layer(nt, R, 40.0, 0.07, 0.35, 7.0, death, 71.1)       # a few bright ones

    # faint galactic band (dies early with the bright stars)
    bandv = nt.nodes.new("ShaderNodeVectorMath")
    bandv.operation = "DOT_PRODUCT"
    nt.links.new(R, bandv.inputs[0])
    bandv.inputs[1].default_value = (0.62, -0.25, 0.74)
    bd = math_node(nt, "MULTIPLY", bandv.outputs["Value"], bandv.outputs["Value"])
    bd = math_node(nt, "MULTIPLY", bd.outputs[0], vb=-22.0)
    bd = math_node(nt, "EXPONENT", bd.outputs[0])
    nz = node(nt, "ShaderNodeTexNoise")
    nt.links.new(R, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 5.0
    nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.62
    nzm = map_range(nt, nz.outputs["Fac"], 0.42, 0.75, 0.0, 1.0)
    bm = math_node(nt, "MULTIPLY", bd.outputs[0], nzm.outputs[0])
    bm = math_node(nt, "MULTIPLY", bm.outputs[0], v_band.outputs[0])
    bm = math_node(nt, "MULTIPLY", bm.outputs[0], vb=0.034)
    bandc = vec_scale(nt, color_ramp(nt, nz.outputs["Fac"], [(0.3, (0.55, 0.58, 0.72)), (0.7, (0.85, 0.72, 0.62))]).outputs[0], bm.outputs[0])

    # the red dwarf: disk + two-scale glow
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(D, dot.inputs[0])
    nt.links.new(sun_dir.outputs[0], dot.inputs[1])
    dcl = math_node(nt, "MINIMUM", dot.outputs["Value"], vb=1.0)
    ang = math_node(nt, "ARCCOSINE", dcl.outputs[0])            # radians
    SR = math.radians(1.05)
    disk = map_range(nt, ang.outputs[0], SR * 0.80, SR, 1.0, 0.0, interp="SMOOTHSTEP")
    core = map_range(nt, ang.outputs[0], 0.0, SR * 0.85, 1.0, 0.0, interp="SMOOTHSTEP")
    g1 = math_node(nt, "MULTIPLY", ang.outputs[0], vb=-1.0 / math.radians(2.2))
    g1 = math_node(nt, "EXPONENT", g1.outputs[0])
    g2 = math_node(nt, "MULTIPLY", ang.outputs[0], vb=-1.0 / math.radians(11.0))
    g2 = math_node(nt, "EXPONENT", g2.outputs[0])
    disk_c = vec_scale(nt, nt.nodes.new("ShaderNodeRGB").outputs[0], disk.outputs[0])
    disk_c.inputs[0].links[0].from_node.outputs[0].default_value = (1.25, 0.20, 0.07, 1)
    core_c = vec_scale(nt, nt.nodes.new("ShaderNodeRGB").outputs[0], core.outputs[0])
    core_c.inputs[0].links[0].from_node.outputs[0].default_value = (0.6, 0.30, 0.10, 1)
    g1c = math_node(nt, "MULTIPLY", g1.outputs[0], vb=0.55)
    g2c = math_node(nt, "MULTIPLY", g2.outputs[0], vb=0.10)
    gsum = math_node(nt, "ADD", g1c.outputs[0], g2c.outputs[0])
    glow_c = vec_scale(nt, nt.nodes.new("ShaderNodeRGB").outputs[0], gsum.outputs[0])
    glow_c.inputs[0].links[0].from_node.outputs[0].default_value = (0.55, 0.045, 0.018, 1)
    sun = vec_add(nt, disk_c.outputs[0], core_c.outputs[0])
    sun = vec_add(nt, sun.outputs[0], glow_c.outputs[0])
    sun = vec_scale(nt, sun.outputs[0], v_sun_i.outputs[0])

    # low red haze along the horizon toward the sun (dust; fades with the sun)
    sepD = node(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(D, sepD.inputs[0])
    el = math_node(nt, "MAXIMUM", sepD.outputs[2], vb=0.0)
    hz = math_node(nt, "MULTIPLY", el.outputs[0], vb=-1.0 / 0.10)
    hz = math_node(nt, "EXPONENT", hz.outputs[0])
    dp = math_node(nt, "ADD", dot.outputs["Value"], vb=1.0)
    dp = math_node(nt, "MULTIPLY", dp.outputs[0], vb=0.5)
    dp = math_node(nt, "POWER", dp.outputs[0], vb=6.0)
    hzm = math_node(nt, "MULTIPLY", hz.outputs[0], dp.outputs[0])
    hzm = math_node(nt, "MULTIPLY", hzm.outputs[0], v_haze.outputs[0])
    haze_c = vec_scale(nt, nt.nodes.new("ShaderNodeRGB").outputs[0], hzm.outputs[0])
    haze_c.inputs[0].links[0].from_node.outputs[0].default_value = (0.20, 0.022, 0.010, 1)

    total = vec_add(nt, s1, s2)
    total = vec_add(nt, total.outputs[0], s3)
    total = vec_add(nt, total.outputs[0], bandc.outputs[0])
    total = vec_add(nt, total.outputs[0], sun.outputs[0])
    total = vec_add(nt, total.outputs[0], haze_c.outputs[0])
    nt.links.new(total.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    return w


# ---------------------------------------------------------------- ridges ---
def ridge_profile(n, rnd, peaks):
    """Fractal jagged profile in [0..1] x; returns heights (scene units)."""
    xs = [i / (n - 1) for i in range(n)]
    h = []
    phase = [rnd.uniform(0, 6.28) for _ in range(6)]
    for x in xs:
        v = 0.0
        for (cx, w, a) in peaks:
            v += a * math.exp(-((x - cx) / w) ** 2)
        amp = 1.0
        for k in range(6):
            f = 2.0 ** k * 3.0
            v += amp * 0.18 * math.sin(f * x * 6.283 + phase[k]) * (1 if k % 2 else 0.7)
            amp *= 0.55
        h.append(v)
    # midpoint jitter for rocky crags
    for i in range(1, n - 1):
        h[i] += rnd.uniform(-1, 1) * 0.05
    return xs, h


def make_ridge(name, dist, half_w, base_h, scale_h, peaks, rim, seed, n=700):
    rnd = random.Random(seed)
    xs, hs = ridge_profile(n, rnd, peaks)
    verts, faces = [], []
    rim_vals = []
    for x, h in zip(xs, hs):
        X = lerp(-half_w, half_w, x)
        top = base_h + h * scale_h
        verts += [(X, dist, top), (X, dist, top - rim), (X, dist, -dist * 1.5)]
        rim_vals += [1.0, 0.0, 0.0]
    for i in range(n - 1):
        a, b = 3 * i, 3 * (i + 1)
        faces.append((a + 1, b + 1, b, a))
        faces.append((a + 2, b + 2, b + 1, a + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    at = me.attributes.new("rim", "FLOAT", "POINT")
    for i, v in enumerate(rim_vals):
        at.data[i].value = v
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, xs, hs


def ridge_material(name, base_col, rim_col):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    v_rim = value_node(nt, "rim_i", 0.0)
    v_sx = value_node(nt, "sun_x", 0.0)
    v_base = value_node(nt, "base_i", 1.0)
    at = node(nt, "ShaderNodeAttribute")
    at.attribute_type = "GEOMETRY"
    at.attribute_name = "rim"
    tc = node(nt, "ShaderNodeTexCoord")
    sx = node(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sx.inputs[0])
    dx = math_node(nt, "SUBTRACT", sx.outputs[0], v_sx.outputs[0])
    dx = math_node(nt, "MULTIPLY", dx.outputs[0], vb=1.0 / 7.0)
    dx = math_node(nt, "MULTIPLY", dx.outputs[0], dx.outputs[0])
    dx = math_node(nt, "MULTIPLY", dx.outputs[0], vb=-1.0)
    dx = math_node(nt, "EXPONENT", dx.outputs[0])
    r4 = math_node(nt, "POWER", at.outputs["Fac"], vb=5.0)
    k = math_node(nt, "MULTIPLY", r4.outputs[0], dx.outputs[0])
    k = math_node(nt, "MULTIPLY", k.outputs[0], v_rim.outputs[0])
    rimc = vec_scale(nt, nt.nodes.new("ShaderNodeRGB").outputs[0], k.outputs[0])
    rimc.inputs[0].links[0].from_node.outputs[0].default_value = (*rim_col, 1)
    basec = vec_scale(nt, nt.nodes.new("ShaderNodeRGB").outputs[0], v_base.outputs[0])
    basec.inputs[0].links[0].from_node.outputs[0].default_value = (*base_col, 1)
    tot = vec_add(nt, rimc.outputs[0], basec.outputs[0])
    nt.links.new(tot.outputs[0], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    return m


# ----------------------------------------------------------------- text ----
def load_font(path):
    try:
        if os.path.exists(path):
            return bpy.data.fonts.load(path, check_existing=True)
    except Exception:
        pass
    return None


def text_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (*TEXT_COLOR, 1)
    em.inputs["Strength"].default_value = 1.0
    tr = node(nt, "ShaderNodeBsdfTransparent")
    mix = node(nt, "ShaderNodeMixShader")
    v = value_node(nt, "fade", 0.0)
    nt.links.new(v.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.blend_method = "BLEND"
    except Exception:
        pass
    return m


def make_text(cam, name, body, y, size, font, spacing=1.32, z=-1.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    if font:
        cu.font = font
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_character = spacing
    cu.space_word = 1.6
    cu.space_line = 1.75
    cu.resolution_u = 4
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = cam
    ob.location = (0.0, y, z)
    mat = text_material(name + "_mat")
    cu.materials.append(mat)
    try:
        ob.visible_shadow = False
    except Exception:
        pass
    return ob, mat


# ---------------------------------------------------------------- build ----
STATE = {}


def build():
    sc = reset_scene()
    build_world(sc)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 28.0
    cam_data.sensor_fit = "AUTO"
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.05
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.rotation_mode = "XYZ"

    # far range (faintly lifted by red haze) and near ridge (pure black + rim light)
    far, _, _ = make_ridge("FarRange", 520.0, 900.0, 0.0, 26.0,
                           [(0.30, 0.10, 0.8), (0.62, 0.07, 1.1), (0.85, 0.12, 0.6)], 0.0, SEED + 3)
    near, nxs, nhs = make_ridge("Ridge", 60.0, 70.0, -1.0, 4.0,
                                [(0.38, 0.06, 1.25), (0.555, 0.035, 1.55), (0.47, 0.10, 0.7),
                                 (0.80, 0.12, 0.6), (0.12, 0.10, 0.25)], 0.22, SEED)
    far_m = ridge_material("FarMat", (0.010, 0.0035, 0.003), (0.0, 0.0, 0.0))
    near_m = ridge_material("RidgeMat", (0.0, 0.0, 0.0), (1.0, 0.13, 0.04))
    far.data.materials.append(far_m)
    near.data.materials.append(near_m)

    f_txt = load_font(FONT_TEXT)
    f_num = load_font(FONT_NUM) or f_txt
    texts = {}
    for key, body, t0, t1, y, size in TEXT_BEATS:
        texts[key] = (make_text(cam, "T_" + key, body, y, size, f_txt), t0, t1)
    counter = make_text(cam, "T_counter", "13,800,000,000", 0.475, 0.030, f_num, spacing=1.18)
    label = make_text(cam, "T_label", "YEARS AFTER THE BIG BANG", 0.435, 0.0125, f_txt, spacing=1.6)

    STATE.update(sc=sc, cam=cam, far_m=far_m, near_m=near_m, texts=texts,
                 counter=counter, label=label, ridge=(nxs, nhs))
    return sc


# ------------------------------------------------------------- animation ---
def cam_pose(t):
    u = t / DURATION_S
    loc = (lerp(-0.6, 0.4, u), lerp(0.0, 7.0, smoothstep(0, 1, u)), 1.2)
    pitch = lerp(14.8, 12.2, smoothstep(0.0, 0.85, u))
    yaw = lerp(0.4, -0.3, u)
    return loc, pitch, yaw


def ridge_elev(az_deg, t):
    """Angular elevation (deg) of the near ridge crest seen from the camera."""
    xs, hs = STATE["ridge"]
    (cx, cy, cz), _, _ = cam_pose(t)
    d = 60.0 - cy
    X = cx + d * math.tan(math.radians(az_deg))
    fx = (X + 70.0) / 140.0
    i = min(len(xs) - 2, max(0, int(fx * (len(xs) - 1))))
    top = max(hs[max(0, i - 2):i + 3]) * 4.0 - 1.0
    return math.degrees(math.atan2(top - cz, d))


SUN_AZ_END = 4.6


def sun_track(t):
    """Sun (azimuth, elevation) in degrees. Descends along a slanted path and
    slips behind the flank of the tallest crag exactly at T_SUNSET."""
    u = min(1.0, t / T_SUNSET)
    az = lerp(-6.5, SUN_AZ_END, u) + max(0.0, t - T_SUNSET) * 0.3
    el_end = ridge_elev(SUN_AZ_END, T_SUNSET) - 1.25
    el = lerp(21.0, el_end, u ** 0.92) - max(0.0, t - T_SUNSET) * 0.9
    return az, el


def set_world_val(name, v):
    STATE["sc"].world.node_tree.nodes[name].outputs[0].default_value = v


def update(scene, *_):
    t = (scene.frame_current - 1) / FPS
    sc = scene
    cam = STATE["cam"]

    # camera: very slow push and tilt down after the sun
    u = t / DURATION_S
    loc, pitch, yaw = cam_pose(t)
    cam.location = loc
    cam.rotation_euler = (math.radians(90 + pitch), 0.0, math.radians(yaw))

    # sky
    death = star_death(t)
    set_world_val("death", death)
    set_world_val("sky_rot", math.radians(lerp(0.0, 3.2, u)))
    set_world_val("band", 1.0 - smoothstep(5.5, 12.0, t))
    az, el = sun_track(t)
    a, e = math.radians(az), math.radians(el)
    sd = (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))
    nd = sc.world.node_tree.nodes["sun_dir"]
    nd.inputs[0].default_value, nd.inputs[1].default_value, nd.inputs[2].default_value = sd
    # the last star dims slightly as it reddens toward the end of its life
    sun_i = lerp(1.0, 0.62, smoothstep(8.0, 21.0, t)) * (1.0 - smoothstep(T_SUNSET + 0.2, T_BLACK, t))
    set_world_val("sun_i", sun_i)
    haze = (0.35 + 0.65 * smoothstep(4.0, 17.0, t)) * (1.0 - smoothstep(T_SUNSET - 0.6, T_BLACK, t))
    set_world_val("haze", haze)

    # ridge rim light: brightens as the sun touches the crag, then dies away
    nm = STATE["near_m"].node_tree.nodes
    ridge_d = 60.0 - cam.location[1]
    sun_x = cam.location[0] + ridge_d * math.tan(a)
    nm["sun_x"].outputs[0].default_value = sun_x
    rim = smoothstep(16.5, 21.0, t) * (1.0 - smoothstep(T_SUNSET + 0.3, T_BLACK - 0.2, t))
    nm["rim_i"].outputs[0].default_value = 1.6 * rim
    STATE["far_m"].node_tree.nodes["base_i"].outputs[0].default_value = (
        0.6 + 0.8 * smoothstep(4, 17, t)) * (1.0 - smoothstep(T_SUNSET - 1.0, T_BLACK, t))

    # text beats
    for key, ((ob, mat), t0, t1) in STATE["texts"].items():
        f = fade_window(t, t0, t1, fin=0.55 if key != "hook" else 0.35, fout=0.8)
        if key == "end":
            f = smoothstep(t0, t0 + 1.1, t) * (1.0 - smoothstep(t1 - 0.05, t1, t))
        mat.node_tree.nodes["fade"].outputs[0].default_value = f * 0.92
        ob.hide_render = f <= 0.001

    (cob, cmat), (lob, lmat) = STATE["counter"], STATE["label"]
    cob.data.body = format_years(year_exponent(t))
    cf = smoothstep(0.6, 1.4, t) * (1.0 - smoothstep(T_SUNSET + 0.4, T_BLACK - 0.2, t))
    cmat.node_tree.nodes["fade"].outputs[0].default_value = cf * 0.85
    lmat.node_tree.nodes["fade"].outputs[0].default_value = cf * 0.55
    cob.hide_render = lob.hide_render = cf <= 0.001


# ------------------------------------------------------------------ main ---
def main():
    args = args_after_dashes()
    out_dir = OUTPUT_DIR
    frames = None
    if "--out" in args:
        out_dir = args[args.index("--out") + 1]
    if "--frames" in args:
        frames = [int(x) for x in args[args.index("--frames") + 1].split(",")]
    sc = build()
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "update":
            bpy.app.handlers.frame_change_pre.remove(h)
    bpy.app.handlers.frame_change_pre.append(update)
    sc.frame_set(1)

    if "--render" not in args:
        return
    if not out_dir.endswith("/"):
        out_dir += "/"
    if not os.path.isabs(out_dir):
        here = os.path.dirname(os.path.abspath(globals().get("__file__") or os.path.join(os.getcwd(), "x")))
        out_dir = os.path.join(here, out_dir)
    out_abs = out_dir
    os.makedirs(out_abs, exist_ok=True)
    rng = frames if frames else range(sc.frame_start, sc.frame_end + 1)
    import time
    t_all = time.time()
    for f in rng:
        t0 = time.time()
        fp = os.path.join(out_abs, f"{FILE_PREFIX}{f:04d}.png")
        if "--resume" in args and os.path.exists(fp) and os.path.getsize(fp) > 0:
            continue
        sc.frame_set(f)
        update(sc)
        sc.render.filepath = os.path.join(out_abs, f"{FILE_PREFIX}{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"frame {f} {time.time() - t0:.2f}s", flush=True)
    print(f"done {time.time() - t_all:.1f}s", flush=True)


main()
