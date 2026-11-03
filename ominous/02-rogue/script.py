"""
OMINOUS #2 - ROGUE
A free-floating planet drifts out of the dark and swallows the Milky Way.

Procedural only (no downloads). Blender 4.2 - 5.x.
    blender -b -P script.py -- --render
    blender -b -P script.py -- --render --frames 1 576 --step 1
Optional: --frames A B   --step N   --out DIR   --percent P   --samples S
"""

# ============================== CONFIG ==============================
CONFIG = dict(
    fps=24,
    duration_s=24.0,
    res_x=1080,
    res_y=1920,
    percent=53,                 # 1080x1920 * 0.53 -> 572x1018 (final upscaled at encode)
    engine="CYCLES",            # Cycles CPU (no GPU / EGL here); emission-only scene
    samples=10,
    denoise=False,              # pure emission: AA noise only, denoiser would smear stars
    output="//frames/f_",      # overridable with --out DIR
    font_paths=[
        "/usr/share/fonts/opentype/inter/Inter-Light.otf",
        "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
        "C:/Windows/Fonts/segoeuil.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ],
    accent=(0.45, 0.92, 1.0),   # ice cyan
    text_rgb=(0.93, 0.93, 0.90),
    band_gain=0.2,
)
# ====================================================================

import bpy
import math
import os
import sys

FPS = CONFIG["fps"]
NFR = int(round(CONFIG["duration_s"] * FPS))


def argval(flag, n=1, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if flag not in argv:
        return default
    i = argv.index(flag)
    vals = argv[i + 1:i + 1 + n]
    return vals if n > 1 else (vals[0] if vals else default)


def has_flag(flag):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return flag in argv


def smooth(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------ scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = NFR
    sc.render.resolution_x = CONFIG["res_x"]
    sc.render.resolution_y = CONFIG["res_y"]
    sc.render.resolution_percentage = int(argval("--percent", default=CONFIG["percent"]))
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = int(argval("--samples", default=CONFIG["samples"]))
    cy.use_adaptive_sampling = False
    for attr in ("use_denoising",):
        if hasattr(cy, attr):
            setattr(cy, attr, CONFIG["denoise"])
    cy.max_bounces = 0
    cy.diffuse_bounces = 0
    cy.glossy_bounces = 0
    cy.transmission_bounces = 0
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.filter_width = 1.2
    sc.render.use_persistent_data = True
    # colour management
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        try:
            sc.view_settings.look = "Medium High Contrast"
        except TypeError:
            pass
    sc.view_settings.exposure = 0.0
    # output
    im = sc.render.image_settings
    if hasattr(im, "media_type"):
        im.media_type = "IMAGE"           # Blender 5.x: must precede file_format
    im.file_format = "PNG"
    im.color_mode = "RGB"
    im.color_depth = "8"
    sc.render.film_transparent = False
    return sc


def node(nt, typ, loc=(0, 0), **inputs):
    n = nt.nodes.new(typ)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def math_n(nt, op, a=None, b=None, loc=(0, 0), clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.location = loc
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def vmath(nt, op, a=None, b=None, loc=(0, 0)):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    n.location = loc
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n


def mixrgb(nt, fac, c1, c2, blend="MIX"):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    n.blend_type = blend
    sockets = [s for s in n.inputs if s.enabled]
    # sockets: Factor, A, B (RGBA variants)
    f = n.inputs["Factor"] if "Factor" in n.inputs else n.inputs[0]
    a = [s for s in n.inputs if s.name == "A" and s.type == "RGBA"][0]
    b = [s for s in n.inputs if s.name == "B" and s.type == "RGBA"][0]
    for sock, v in ((f, fac), (a, c1), (b, c2)):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, (tuple, list)):
            sock.default_value = tuple(v) + ((1.0,) if len(v) == 3 else ())
        else:
            nt.links.new(v, sock)
    out = [s for s in n.outputs if s.type == "RGBA"][0]
    return out


def voronoi_feature_out(n, name):
    return n.outputs[name]


# ------------------------------------------------------------ sky
def build_world(sc):
    w = bpy.data.worlds.new("Sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld", (1800, 0))
    bg = node(nt, "ShaderNodeBackground", (1600, 0))
    nt.links.new(bg.outputs[0], out.inputs[0])

    tc = node(nt, "ShaderNodeTexCoord", (-1600, 0))
    # orient galactic plane: tilted so the band runs diagonally across the frame
    mp = node(nt, "ShaderNodeMapping", (-1400, 0))
    mp.inputs["Rotation"].default_value = (math.radians(0), math.radians(-38), math.radians(8))
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    D = mp.outputs[0]
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, 300))
    nt.links.new(D, sep.inputs[0])
    z = sep.outputs["Z"]
    # direction toward galactic centre (bulge) -> brighter region
    gc = vmath(nt, "DOT_PRODUCT", D, (0.15, 1.0, 0.25), (-1200, 500))
    bulge = math_n(nt, "MAXIMUM", gc.outputs["Value"], 0.0)
    bulge = math_n(nt, "POWER", bulge, 3.0)

    # band profile exp(-z^2 / w^2), plus wider faint halo
    z2 = math_n(nt, "MULTIPLY", z, z)
    core = math_n(nt, "EXPONENT", math_n(nt, "MULTIPLY", z2, -1.0 / (0.085 ** 2)))
    halo = math_n(nt, "EXPONENT", math_n(nt, "MULTIPLY", z2, -1.0 / (0.26 ** 2)))

    # clouds of unresolved stars
    n1 = node(nt, "ShaderNodeTexNoise", (-1000, 0))
    n1.noise_dimensions = "3D"
    n1.inputs["Scale"].default_value = 3.2
    n1.inputs["Detail"].default_value = 6.0
    n1.inputs["Roughness"].default_value = 0.62
    nt.links.new(D, n1.inputs["Vector"])
    cloud = math_n(nt, "POWER", math_n(nt, "MAXIMUM", math_n(nt, "SUBTRACT", n1.outputs["Fac"], 0.36), 0.0), 2.0)
    # dark dust lanes hugging the plane
    n2 = node(nt, "ShaderNodeTexNoise", (-1000, -300))
    n2.inputs["Scale"].default_value = 7.0
    n2.inputs["Detail"].default_value = 5.0
    n2.inputs["Roughness"].default_value = 0.6
    if "Distortion" in n2.inputs:
        n2.inputs["Distortion"].default_value = 0.4
    nt.links.new(D, n2.inputs["Vector"])
    dust = math_n(nt, "MULTIPLY", math_n(nt, "MAXIMUM", math_n(nt, "SUBTRACT", n2.outputs["Fac"], 0.45), 0.0), 4.0)
    zlane = math_n(nt, "EXPONENT", math_n(nt, "MULTIPLY", z2, -1.0 / (0.05 ** 2)))
    dustmask = math_n(nt, "SUBTRACT", 1.0, math_n(nt, "MULTIPLY", dust, math_n(nt, "ADD", math_n(nt, "MULTIPLY", zlane, 0.8), 0.25)), clamp=True)

    bandv = math_n(nt, "ADD", math_n(nt, "MULTIPLY", core, math_n(nt, "ADD", math_n(nt, "MULTIPLY", cloud, 6.0), 0.05)),
                   math_n(nt, "MULTIPLY", halo, 0.035))
    bandv = math_n(nt, "MULTIPLY", bandv, math_n(nt, "ADD", math_n(nt, "MULTIPLY", bulge, 2.0), 0.55))
    bandv = math_n(nt, "MULTIPLY", bandv, dustmask)

    # star fields (Voronoi points on the direction sphere)
    def starlayer(scale, radius, power, gain, loc):
        v = node(nt, "ShaderNodeTexVoronoi", loc)
        v.voronoi_dimensions = "3D"
        v.feature = "F1"
        v.inputs["Scale"].default_value = scale
        if "Randomness" in v.inputs:
            v.inputs["Randomness"].default_value = 1.0
        nt.links.new(D, v.inputs["Vector"])
        d = v.outputs["Distance"]
        shape = math_n(nt, "SUBTRACT", 1.0, math_n(nt, "DIVIDE", d, radius), clamp=True)
        shape = math_n(nt, "MULTIPLY", shape, shape)
        sepc = node(nt, "ShaderNodeSeparateColor", (loc[0] + 200, loc[1] - 150))
        nt.links.new(v.outputs["Color"], sepc.inputs[0])
        bright = math_n(nt, "POWER", sepc.outputs[0], power)
        return math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", shape, bright), gain), sepc.outputs[1]

    s_hero, tint = starlayer(38.0, 0.055, 14.0, 60.0, (-1000, -700))
    s_mid, _ = starlayer(150.0, 0.16, 7.0, 6.0, (-1000, -1000))
    s_fine, _ = starlayer(420.0, 0.30, 4.0, 1.2, (-1000, -1300))
    # fine stars crowd into the band
    fine_mask = math_n(nt, "ADD", math_n(nt, "MULTIPLY", math_n(nt, "ADD", core, halo), 1.6), 0.06)
    s_fine = math_n(nt, "MULTIPLY", s_fine, math_n(nt, "MULTIPLY", fine_mask, dustmask))
    stars = math_n(nt, "ADD", math_n(nt, "ADD", s_hero, s_mid), s_fine)

    # colours: band warm-grey, slight cool halo; stars white with blue/amber spread
    band_col = mixrgb(nt, halo, (0.55, 0.62, 0.70), (0.80, 0.74, 0.66))
    band_rgb = vmath(nt, "SCALE", band_col, None, (600, 200))
    nt.links.new(math_n(nt, "MULTIPLY", bandv, CONFIG["band_gain"]), band_rgb.inputs["Scale"])
    star_col = mixrgb(nt, tint, (0.80, 0.88, 1.0), (1.0, 0.90, 0.78))
    star_rgb = vmath(nt, "SCALE", star_col, None, (600, -200))
    nt.links.new(stars, star_rgb.inputs["Scale"])
    total = vmath(nt, "ADD", band_rgb.outputs[0], star_rgb.outputs[0], (900, 0))
    # deep space floor (never pure black)
    total = vmath(nt, "ADD", total.outputs[0], (0.0012, 0.0016, 0.0022), (1100, 0))
    nt.links.new(total.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    return w


# ------------------------------------------------------------ planet
def build_planet(sc):
    R = 8.0
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=R, location=(0, 60, 0))
    p = bpy.context.active_object
    p.name = "Rogue"
    bpy.ops.object.shade_smooth()
    p.rotation_euler = (math.radians(14), math.radians(-20), 0)

    m = bpy.data.materials.new("RogueIce")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (1600, 0))
    em = node(nt, "ShaderNodeEmission", (1400, 0))
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    em.inputs["Strength"].default_value = 1.0

    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
    geo = node(nt, "ShaderNodeNewGeometry", (-1400, -300))
    obi = node(nt, "ShaderNodeObjectInfo", (-1400, 300))
    O = tc.outputs["Object"]

    # frozen surface: mottled albedo + bright fracture lines + impact pits
    n = node(nt, "ShaderNodeTexNoise", (-1100, 200))
    n.inputs["Scale"].default_value = 0.35
    n.inputs["Detail"].default_value = 8.0
    n.inputs["Roughness"].default_value = 0.6
    nt.links.new(O, n.inputs["Vector"])
    vo = node(nt, "ShaderNodeTexVoronoi", (-1100, -100))
    vo.feature = "DISTANCE_TO_EDGE"
    vo.inputs["Scale"].default_value = 0.55
    nt.links.new(n.outputs["Color"], vo.inputs["Vector"])
    crack = math_n(nt, "SUBTRACT", 1.0, math_n(nt, "DIVIDE", vo.outputs["Distance"], 0.012), clamp=True)
    vo2 = node(nt, "ShaderNodeTexVoronoi", (-1100, -400))
    vo2.feature = "DISTANCE_TO_EDGE"
    vo2.inputs["Scale"].default_value = 1.6
    nt.links.new(O, vo2.inputs["Vector"])
    crack2 = math_n(nt, "SUBTRACT", 1.0, math_n(nt, "DIVIDE", vo2.outputs["Distance"], 0.02), clamp=True)
    alb = math_n(nt, "ADD", math_n(nt, "MULTIPLY", n.outputs["Fac"], 0.9), 0.15)
    alb = math_n(nt, "ADD", alb, math_n(nt, "MULTIPLY", math_n(nt, "ADD", crack, math_n(nt, "MULTIPLY", crack2, 0.5)), 0.45))

    # starlight: the limb facing the galactic band catches a whisper of light
    N = geo.outputs["Normal"]
    V = geo.outputs["Incoming"]
    ndv = vmath(nt, "DOT_PRODUCT", N, V, (-900, -700)).outputs["Value"]
    fres = math_n(nt, "SUBTRACT", 1.0, math_n(nt, "MAXIMUM", ndv, 0.0), clamp=True)
    rim = math_n(nt, "POWER", fres, 3.5)
    Ldir = vmath(nt, "NORMALIZE", (0.75, 0.35, 0.65), None, (-900, -900))
    ndl = vmath(nt, "DOT_PRODUCT", N, Ldir.outputs[0], (-700, -900)).outputs["Value"]
    lit = math_n(nt, "POWER", math_n(nt, "MAXIMUM", math_n(nt, "ADD", math_n(nt, "MULTIPLY", ndl, 0.8), 0.2), 0.0), 2.0)
    gain = node(nt, "ShaderNodeSeparateColor", (-1200, 300))
    nt.links.new(obi.outputs["Color"], gain.inputs[0])   # object colour R = rim gain (animated)
    rimv = math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", rim, lit), alb)
    rimv = math_n(nt, "MULTIPLY", rimv, gain.outputs[0])
    # a sliver of the dark face itself (barely there)
    face = math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", alb, math_n(nt, "ADD", math_n(nt, "MULTIPLY", lit, 0.010), 0.0012)), gain.outputs[0])
    val = math_n(nt, "ADD", rimv, face)
    col = vmath(nt, "SCALE", tuple(CONFIG["accent"]), None, (1200, 0))
    nt.links.new(val, col.inputs["Scale"])
    nt.links.new(col.outputs[0], em.inputs["Color"])
    p.data.materials.append(m)

    # thin exosphere-like glow hugging the limb (transparent shell)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=R * 1.012, location=(0, 0, 0))
    h = bpy.context.active_object
    h.name = "RogueHalo"
    bpy.ops.object.shade_smooth()
    hm = bpy.data.materials.new("Halo")
    hm.use_nodes = True
    nt = hm.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (800, 0))
    add = node(nt, "ShaderNodeAddShader", (600, 0))
    tr = node(nt, "ShaderNodeBsdfTransparent", (400, 100))
    em = node(nt, "ShaderNodeEmission", (400, -100))
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    geo = node(nt, "ShaderNodeNewGeometry", (-600, 0))
    obi = node(nt, "ShaderNodeObjectInfo", (-600, 300))
    ndv = vmath(nt, "DOT_PRODUCT", geo.outputs["Normal"], geo.outputs["Incoming"], (-400, 0)).outputs["Value"]
    ndv = math_n(nt, "ABSOLUTE", ndv)
    edge = math_n(nt, "POWER", math_n(nt, "SUBTRACT", 1.0, ndv, clamp=True), 6.0)
    Ldir = vmath(nt, "NORMALIZE", (0.75, 0.35, 0.65), None, (-400, -300))
    ndl = vmath(nt, "DOT_PRODUCT", geo.outputs["Normal"], Ldir.outputs[0], (-200, -300)).outputs["Value"]
    lit = math_n(nt, "ADD", math_n(nt, "MULTIPLY", math_n(nt, "MAXIMUM", ndl, 0.0), 1.0), 0.06)
    gsep = node(nt, "ShaderNodeSeparateColor", (-400, 300))
    nt.links.new(obi.outputs["Color"], gsep.inputs[0])
    v = math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", edge, lit), 0.35), gsep.outputs[0])
    col = vmath(nt, "SCALE", tuple(CONFIG["accent"]), None, (200, -100))
    nt.links.new(v, col.inputs["Scale"])
    nt.links.new(col.outputs[0], em.inputs["Color"])
    h.data.materials.append(hm)
    h.visible_shadow = False
    return p, h


# ------------------------------------------------------------ camera + text
def build_camera(sc):
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 36.0
    cd.lens = 30.0
    cd.clip_start = 0.05
    cd.clip_end = 1000
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (0, 0, 0)
    cam.rotation_euler = (math.radians(90), 0, 0)
    return cam


def load_font():
    for p in CONFIG["font_paths"]:
        if os.path.exists(p):
            try:
                return bpy.data.fonts.load(p)
            except Exception:
                pass
    return None


def text_material():
    m = bpy.data.materials.new("Type")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (600, 0))
    mix = node(nt, "ShaderNodeMixShader", (400, 0))
    tr = node(nt, "ShaderNodeBsdfTransparent", (200, 100))
    em = node(nt, "ShaderNodeEmission", (200, -100))
    obi = node(nt, "ShaderNodeObjectInfo", (0, 200))
    nt.links.new(obi.outputs["Alpha"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(obi.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.6
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def add_text(cam, font, mat, body, y, size, spacing, rgb, max_w=0.52, z=-1.0):
    cu = bpy.data.curves.new("T", "FONT")
    cu.body = body
    if font:
        cu.font = font
    cu.size = size
    cu.space_character = spacing
    cu.space_line = 1.55
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new("T_" + body[:10], cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob.parent = cam
    ob.location = (0, y, z)
    bpy.context.view_layer.update()
    w = ob.dimensions.x
    if w > max_w:
        s = max_w / w
        cu.size = size * s
    ob.color = (rgb[0], rgb[1], rgb[2], 0.0)
    return ob


def key_alpha(ob, t_in, t_out, fade_in=0.45, fade_out=0.6, peak=1.0):
    """Keyframe object-colour alpha (drives text visibility)."""
    def k(t, a):
        f = 1 + t * FPS
        ob.color[3] = a
        ob.keyframe_insert("color", index=3, frame=f)
    if t_in > 0:
        k(0, 0.0)
        k(t_in, 0.0)
    k(t_in + fade_in, peak)
    k(t_out, peak)
    k(t_out + fade_out, 0.0)


# ------------------------------------------------------------ timeline
# beats (seconds) - shared with soundtrack.py
BEATS = dict(
    hook=(0.0, 3.3),
    nosun=(4.3, 7.2),
    noday=(8.2, 11.1),
    billions=(12.3, 16.6),
    coming=(17.8, 21.6),
    black=22.6,
)


def planet_state(t):
    """Planet centre + rim gain at time t (seconds). Camera looks down +Y."""
    T = CONFIG["duration_s"]
    u = min(1.0, max(0.0, t / 22.8))
    e = u ** 1.55                                   # accelerating approach
    dist = 75.0 * (8.35 / 75.0) ** e                # looming: log-distance closes
    # horizontal screen position of centre (in units of half-width tangent)
    tan_w = 0.6 * CONFIG["res_x"] / CONFIG["res_y"]
    sx = -2.05 + 1.95 * (u ** 0.85)
    sz = 0.18 - 0.22 * u
    x = sx * tan_w * dist
    z = sz * 0.6 * dist
    gain = 0.06 + 0.55 * smooth(2.5, 10.0, t) + 0.75 * smooth(11.0, 20.0, t)
    return (x, dist, z), gain


def animate(sc, planet, halo, cam):
    for f in range(1, NFR + 2):
        t = (f - 1) / FPS
        loc, gain = planet_state(t)
        planet.location = loc
        planet.keyframe_insert("location", frame=f)
        planet.rotation_euler[2] = math.radians(-30 + 14 * t / CONFIG["duration_s"])
        planet.keyframe_insert("rotation_euler", index=2, frame=f)
        planet.color = (gain, 0, 0, 1)
        planet.keyframe_insert("color", frame=f)
        halo.color = (gain, 0, 0, 1)
        halo.keyframe_insert("color", frame=f)
        # slow camera drift: a few degrees of yaw/roll, imperceptible push
        cam.rotation_euler = (math.radians(90 + 1.2 * t / 24.0), math.radians(-1.5 + 2.5 * t / 24.0),
                              math.radians(2.2 - 3.0 * t / 24.0))
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.lens = 30.0 + 2.0 * (t / 24.0)
        cam.data.keyframe_insert("lens", frame=f)


def build():
    sc = reset_scene()
    build_world(sc)
    planet, halo = build_planet(sc)
    cam = build_camera(sc)
    font = load_font()
    tm = text_material()
    W = (1, 1, 1)
    TXT = CONFIG["text_rgb"]
    ACC = CONFIG["accent"]
    # all type sits in the lower third
    Y = -0.30
    hook = add_text(cam, font, tm, "THERE'S A PLANET OUT THERE\nWITH NO SUN.", Y, 0.026, 1.35, TXT, max_w=0.56)
    nosun = add_text(cam, font, tm, "NO SUN.", Y, 0.034, 1.6, TXT)
    noday = add_text(cam, font, tm, "NO DAY.", Y, 0.034, 1.6, TXT)
    bil = add_text(cam, font, tm, "BILLIONS MAY DRIFT\nTHROUGH OUR GALAXY.", Y, 0.026, 1.35, TXT, max_w=0.50)
    src = add_text(cam, font, tm, "MICROLENSING SURVEYS  \u00b7  OGLE  /  MOA", Y - 0.075, 0.0115, 1.5,
                   tuple(c * 0.75 for c in ACC), max_w=0.40)
    com = add_text(cam, font, tm, "YOU WOULDN'T\nSEE ONE COMING.", Y, 0.030, 1.45, TXT, max_w=0.50)
    # hook is fully visible on frame 1 (scroll stop), others fade
    for f, a in ((1, 1.0), (1 + int(3.3 * FPS), 1.0), (1 + int(3.9 * FPS), 0.0)):
        hook.color[3] = a
        hook.keyframe_insert("color", index=3, frame=f)
    key_alpha(nosun, *BEATS["nosun"])
    key_alpha(noday, *BEATS["noday"])
    key_alpha(bil, *BEATS["billions"])
    key_alpha(src, BEATS["billions"][0] + 0.8, BEATS["billions"][1], 0.8, 0.6, 0.9)
    key_alpha(com, *BEATS["coming"], fade_in=0.7, fade_out=0.9)
    animate(sc, planet, halo, cam)
    # halo follows planet via copy-location constraint
    c = halo.constraints.new("COPY_TRANSFORMS")
    c.target = planet
    return sc


def main():
    sc = build()
    out = argval("--out", default=None)
    if out:
        sc.render.filepath = os.path.join(os.path.abspath(out), "f_")
    else:
        sc.render.filepath = CONFIG["output"]
    if has_flag("--save"):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argval("--save")))
    if has_flag("--render"):
        fr = argval("--frames", 2, None)
        a, b = (int(fr[0]), int(fr[1])) if fr else (1, NFR)
        step = int(argval("--step", default=1))
        outdir = os.path.dirname(bpy.path.abspath(sc.render.filepath))
        for f in range(a, b + 1, step):
            fp = os.path.join(outdir, "f_%04d.png" % f)
            if has_flag("--skip-existing") and os.path.exists(fp) and os.path.getsize(fp) > 0:
                continue
            sc.frame_set(f)
            sc.render.filepath = fp
            bpy.ops.render.render(write_still=True)
            print("frame", f, "done", flush=True)


main()
