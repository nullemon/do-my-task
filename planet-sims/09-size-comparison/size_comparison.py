"""Planet size comparison - vertical 9:16, ominous/cinematic. Built, rendered and scored by this script.

Mercury -> Mars -> Venus -> Earth -> Neptune -> Uranus -> Saturn -> Jupiter
-> KELT-9 b -> WASP-17 b -> HAT-P-67 b (largest precisely measured planet) -> the Sun.
Real radii (see PLANETS / README). 1 Blender unit = 1000 km.

Headless (Blender as Python module or `blender -b -P`):
  python size_comparison.py -- --out DIR --frames 1,400,1300      # test stills
  python size_comparison.py -- --out DIR --render                  # all frames (resumable)
  python size_comparison.py -- --out DIR --audio --encode          # WAV + MP4
Full quality on a desktop GPU:
  blender -b -P size_comparison.py -- --out DIR --res 1080 --engine eevee --samples 64 --threads 0 --render --audio --encode
  (or keep Cycles: --engine cycles --samples 128 --gpu)
"""

import math
import os
import sys
import wave

import bpy
from mathutils import Vector

# ----------------------------------------------------------------------------- CONFIG
FPS = 24
RES_X = 540                  # 1080 for final
SAMPLES = 8                  # Cycles: 64-128 for final; Eevee: 64
THREADS = 2                  # 0 = all cores
ENGINE = "cycles"            # or "eevee"
GPU = False
OUT_DIR = None
FONT_DIR = "/usr/share/fonts/opentype/inter"   # falls back to Blender's built-in font

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None, cast=str):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


RES_X = arg("--res", RES_X, int)
SAMPLES = arg("--samples", SAMPLES, int)
THREADS = arg("--threads", THREADS, int)
ENGINE = arg("--engine", ENGINE).lower()
GPU = "--gpu" in argv
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else bpy.path.abspath("//")
OUT_DIR = arg("--out", os.path.join(HERE, "renders"))
FRAMES_ONLY = [int(x) for x in arg("--frames", "").split(",") if x]
STEP = arg("--step", 1, int)  # 2 = render odd frames only; --encode blends them back to FPS
RES_Y = RES_X * 16 // 9
KM = 1000.0  # km per Blender unit
R_EARTH = 6371.0
R_JUP_EQ = 71492.0  # exoplanet radii are quoted in equatorial Jupiter radii

# ----------------------------------------------------------------------------- FACTS
# Solar-system values: NASA planetary fact sheets, volumetric MEAN radius.
# Exoplanets: radius in R_J (71,492 km), NASA Exoplanet Archive default-parameter papers.
PLANETS = [
    dict(key="mercury", name="MERCURY", r_km=2439.7),
    dict(key="mars", name="MARS", r_km=3389.5),
    dict(key="venus", name="VENUS", r_km=6051.8),
    dict(key="earth", name="EARTH", r_km=6371.0),
    dict(key="neptune", name="NEPTUNE", r_km=24622.0),
    dict(key="uranus", name="URANUS", r_km=25362.0, ext=1.15),
    dict(key="saturn", name="SATURN", r_km=58232.0, ext=2.27),
    dict(key="jupiter", name="JUPITER", r_km=69911.0),
    dict(key="kelt9", name="KELT-9 b", r_rj=1.891, note="EXOPLANET · 670 LIGHT-YEARS"),       # Gaudi+ 2017
    dict(key="wasp17", name="WASP-17 b", r_rj=1.991, note="EXOPLANET · 1,300 LIGHT-YEARS"),    # Anderson+ 2011
    dict(key="hatp67", name="HAT-P-67 b", r_rj=2.140, note="EXOPLANET · 1,200 LIGHT-YEARS"),   # Wang+ 2025, AJ 169, 336
]
SUN = dict(key="sun", name="THE SUN", r_km=695700.0)
for p in PLANETS + [SUN]:
    if "r_rj" in p:
        p["r_km"] = p["r_rj"] * R_JUP_EQ
    p["r"] = p["r_km"] / KM
    p["e"] = p["r"] * p.get("ext", 1.0)  # horizontal half-extent (rings)

# ----------------------------------------------------------------------------- TIMELINE (seconds)
# per stage: (transition-in, hold, caption during hold, caption during transition)
STAGES = [
    ("mercury", 0.0, 2.7, "Start with the smallest.", None),
    ("mars", 1.4, 2.0, None, None),
    ("venus", 1.4, 2.0, None, None),
    ("earth", 1.5, 2.9, "Earth feels big.", None),
    ("neptune", 1.6, 2.6, "It isn't.", None),
    ("uranus", 1.4, 2.0, None, None),
    ("saturn", 1.5, 2.4, None, None),
    ("jupiter", 1.6, 3.2, "1,300 Earths would fit inside.", None),
    ("kelt9", 2.4, 3.0, "Hotter than most stars.", "Now leave the Solar System."),
    ("wasp17", 1.6, 2.7, "Twice as wide as Jupiter.", None),
    ("hatp67", 1.8, 3.6, "The largest planet\never measured.", None),
    ("lineup", 2.6, 2.6, "Every world. Side by side.", None),
    ("sun", 3.4, 5.0, "...and it's still nothing\nnext to a star.", None),
]
TAIL = 1.0  # seconds after the last hold (fade to black)


def fr(t):
    return int(round(t * FPS)) + 1


# ----------------------------------------------------------------------------- LAYOUT
def layout():
    x = 0.0
    prev = None
    spans = []
    for i, p in enumerate(PLANETS + [SUN]):
        if prev is None:
            p["x"] = 0.0
        else:
            span_prev = spans[-1]
            gap = max(0.95 * p["r"], 0.26 * span_prev)
            if p is SUN:
                gap = 0.35 * p["r"]
            p["x"] = prev["x"] + prev["e"] + gap + p["e"]
        # framing span for this planet: previous globe (left) .. this planet's extent (right)
        left = (prev["x"] - prev["r"]) if prev else p["x"] - p["e"]
        spans.append(p["x"] + p["e"] - left)
        p["left"] = left
        prev = p


layout()
BY_KEY = {p["key"]: p for p in PLANETS + [SUN]}


def framing(key):
    """(center_x, visible_width) for a stage."""
    if key == "lineup":
        a = PLANETS[0]["x"] - PLANETS[0]["e"]
        b = PLANETS[-1]["x"] + PLANETS[-1]["e"]
        return (a + b) / 2 + 0.02 * (b - a), (b - a) * 1.10
    if key == "sun":
        a = PLANETS[-1]["x"] - PLANETS[-1]["e"]
        b = SUN["x"] + SUN["r"]
        return (a + b) / 2, (b - a) * 1.12
    p = BY_KEY[key]
    if key == "mercury":
        return p["x"], 2 * p["e"] / 0.50
    a, b = p["left"], p["x"] + p["e"]
    w = max((b - a) * 1.18, 2 * p["e"] / 0.80)
    return (a + b) / 2, w


# Build the frame timeline
TL = []  # dicts: key, f_move0, f_arrive, f_hold_end
t = 0.0
for key, trans, hold, cap, cap_move in STAGES:
    TL.append(dict(key=key, t0=t, ta=t + trans, te=t + trans + hold, cap=cap, cap_move=cap_move))
    t += trans + hold
DURATION = t + TAIL
F_END = fr(DURATION) - 1

LENS, SENSOR = 50.0, 36.0
K_DIST = LENS / SENSOR  # distance = width * K_DIST
DRIFT = 1.06            # slow pull-back during each hold
HALF_W = 0.5 / K_DIST   # at distance 1
HALF_H = HALF_W * 16 / 9


def smoother(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (u * 6 - 15) + 10)


def cam_state(tsec):
    """camera (cx, width) at time tsec."""
    for i, st in enumerate(TL):
        cx, w = framing(st["key"])
        if tsec < st["ta"] and i > 0:  # transition from previous hold-end
            pcx, pw = framing(TL[i - 1]["key"])
            pw *= DRIFT
            u = smoother((tsec - st["t0"]) / (st["ta"] - st["t0"]))
            lw = math.log(pw) + (math.log(w) - math.log(pw)) * u
            # move x in "screen widths" so pans feel even across scales
            return pcx + (cx - pcx) * u, math.exp(lw)
        if tsec <= st["te"] or i == len(TL) - 1:
            hold = max(st["te"] - st["ta"], 1e-3)
            u = min(max((tsec - st["ta"]) / hold, 0.0), 1.2)
            return cx, w * DRIFT ** u
    return framing(TL[-1]["key"])


# ----------------------------------------------------------------------------- SCENE HELPERS
sc = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)


def link(ob):
    sc.collection.objects.link(ob)
    return ob


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    try:
        m.surface_render_method = "BLENDED"  # Eevee (4.2+): smooth transparency
    except Exception:
        pass
    return m, nt, out


def N(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k.startswith("_"):
            setattr(n, k[1:], v)
        else:
            n.inputs[k].default_value = v
    return n


def L(nt, a, b):
    nt.links.new(a, b)


def ramp(nt, fac_socket, stops, interp="LINEAR"):
    r = nt.nodes.new("ShaderNodeValToRGB")
    cr = r.color_ramp
    cr.interpolation = interp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1) if len(stops[0][1]) == 3 else stops[0][1]
    for pos, col in stops[1:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1) if len(col) == 3 else col
    L(nt, fac_socket, r.inputs["Fac"])
    return r


def grey(v):
    return (v, v, v)


def sphere(name, segs=96, rings=48, radius=1.0):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def annulus(name, r_in, r_out, segs=160):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        verts += [(r_in * math.cos(a), r_in * math.sin(a), 0), (r_out * math.cos(a), r_out * math.sin(a), 0)]
    for i in range(segs):
        j = (i + 1) % segs
        faces.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
    me.from_pydata(verts, [], faces)
    return link(bpy.data.objects.new(name, me))


def obj_coords(nt):
    return N(nt, "ShaderNodeTexCoord").outputs["Object"]


def bands(nt, scale=3.0, distortion=3.0, detail=4.0, warp=0.15, warp_scale=2.5):
    """Wave bands along Z, warped by noise (gas-giant look). Returns Fac socket."""
    co = obj_coords(nt)
    nz = N(nt, "ShaderNodeTexNoise", Scale=warp_scale, Detail=4.0)
    L(nt, co, nz.inputs["Vector"])
    sub = N(nt, "ShaderNodeVectorMath", _operation="SUBTRACT")
    L(nt, nz.outputs["Color"], sub.inputs[0])
    sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    mul = N(nt, "ShaderNodeVectorMath", _operation="SCALE")
    L(nt, sub.outputs[0], mul.inputs[0])
    mul.inputs["Scale"].default_value = warp
    add = N(nt, "ShaderNodeVectorMath", _operation="ADD")
    L(nt, co, add.inputs[0])
    L(nt, mul.outputs[0], add.inputs[1])
    wv = N(nt, "ShaderNodeTexWave", _wave_type="BANDS", _bands_direction="Z",
           Scale=scale, Distortion=distortion, Detail=detail)
    wv.inputs["Detail Scale"].default_value = 1.5
    L(nt, add.outputs[0], wv.inputs["Vector"])
    return wv.outputs["Fac"], add.outputs[0]


def bsdf(nt, out, color_socket=None, color=None, rough=0.9, emission_socket=None, em_strength=0.0, normal=None):
    b = N(nt, "ShaderNodeBsdfPrincipled", Roughness=rough)
    b.inputs["Specular IOR Level"].default_value = 0.2
    if color_socket is not None:
        L(nt, color_socket, b.inputs["Base Color"])
    elif color is not None:
        b.inputs["Base Color"].default_value = (*color, 1)
    if emission_socket is not None:
        L(nt, emission_socket, b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = em_strength
    if normal is not None:
        L(nt, normal, b.inputs["Normal"])
    L(nt, b.outputs[0], out.inputs["Surface"])
    return b


def shell_glow(name, radius, color, strength, stops):
    """Transparent shell adding emission by view angle - atmosphere rims and heat halos."""
    ob = sphere(name, 96, 48, radius)
    m, nt, out = new_mat(name + "_m")
    lw = N(nt, "ShaderNodeLayerWeight", Blend=0.5)
    rp = ramp(nt, lw.outputs["Facing"], stops)
    em = N(nt, "ShaderNodeEmission", Strength=strength)
    em.inputs["Color"].default_value = (*color, 1)
    mul = N(nt, "ShaderNodeMixShader")  # fac -> emission amount
    tr = N(nt, "ShaderNodeBsdfTransparent")
    addn = N(nt, "ShaderNodeAddShader")
    # emission * ramp  (scale emission strength via math)
    sep = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
    L(nt, rp.outputs["Color"], sep.inputs[0])
    sep.inputs[1].default_value = strength
    L(nt, sep.outputs[0], em.inputs["Strength"])
    L(nt, tr.outputs[0], addn.inputs[0])
    L(nt, em.outputs[0], addn.inputs[1])
    L(nt, addn.outputs[0], out.inputs["Surface"])
    del mul
    ob.data.materials.append(m)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


# ----------------------------------------------------------------------------- PLANET LOOKS
def look_mercury(nt, out):
    co = obj_coords(nt)
    n = N(nt, "ShaderNodeTexNoise", Scale=5.0, Detail=6.0, Roughness=0.6)
    L(nt, co, n.inputs["Vector"])
    col = ramp(nt, n.outputs["Fac"], [(0.3, grey(0.10)), (0.5, grey(0.22)), (0.7, (0.36, 0.34, 0.32))])
    vor = N(nt, "ShaderNodeTexVoronoi", Scale=7.0)
    L(nt, co, vor.inputs["Vector"])
    crater = ramp(nt, vor.outputs["Distance"], [(0.0, grey(0.0)), (0.22, grey(0.25)), (0.30, grey(0.6)), (0.40, grey(0.45))])
    vor2 = N(nt, "ShaderNodeTexVoronoi", Scale=19.0)
    L(nt, co, vor2.inputs["Vector"])
    crater2 = ramp(nt, vor2.outputs["Distance"], [(0.0, grey(0.0)), (0.2, grey(0.3)), (0.28, grey(0.55)), (0.38, grey(0.45))])
    h = N(nt, "ShaderNodeMath", _operation="ADD")
    L(nt, crater.outputs["Color"], h.inputs[0])
    L(nt, crater2.outputs["Color"], h.inputs[1])
    h2 = N(nt, "ShaderNodeMath", _operation="ADD")
    L(nt, h.outputs[0], h2.inputs[0])
    L(nt, n.outputs["Fac"], h2.inputs[1])
    bump = N(nt, "ShaderNodeBump", Strength=0.6, Distance=0.02)
    L(nt, h2.outputs[0], bump.inputs["Height"])
    bsdf(nt, out, col.outputs["Color"], rough=0.95, normal=bump.outputs["Normal"])


def look_mars(nt, out):
    co = obj_coords(nt)
    n = N(nt, "ShaderNodeTexNoise", Scale=2.6, Detail=6.0, Roughness=0.62)
    L(nt, co, n.inputs["Vector"])
    col = ramp(nt, n.outputs["Fac"], [(0.35, (0.16, 0.05, 0.025)), (0.5, (0.45, 0.14, 0.05)), (0.62, (0.62, 0.3, 0.14))])
    sepz = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, co, sepz.inputs[0])
    az = N(nt, "ShaderNodeMath", _operation="ABSOLUTE")
    L(nt, sepz.outputs["Z"], az.inputs[0])
    cap = ramp(nt, az.outputs[0], [(0.90, grey(0.0)), (0.94, grey(1.0))])
    mix = N(nt, "ShaderNodeMix", _data_type="RGBA")
    L(nt, cap.outputs["Color"], mix.inputs["Factor"])
    L(nt, col.outputs["Color"], mix.inputs["A"])
    mix.inputs["B"].default_value = (0.8, 0.75, 0.72, 1)
    bump = N(nt, "ShaderNodeBump", Strength=0.25, Distance=0.02)
    L(nt, n.outputs["Fac"], bump.inputs["Height"])
    bsdf(nt, out, mix.outputs["Result"], rough=0.95, normal=bump.outputs["Normal"])


def look_venus(nt, out):
    fac, _ = bands(nt, scale=0.5, distortion=2.0, detail=4.0, warp=0.6, warp_scale=1.3)
    col = ramp(nt, fac, [(0.0, (0.72, 0.58, 0.34)), (0.5, (0.86, 0.75, 0.50)), (1.0, (0.93, 0.86, 0.64))])
    bsdf(nt, out, col.outputs["Color"], rough=1.0)


def look_earth(nt, out):
    co = obj_coords(nt)
    n = N(nt, "ShaderNodeTexNoise", Scale=1.9, Detail=7.0, Roughness=0.62)
    L(nt, co, n.inputs["Vector"])
    land = ramp(nt, n.outputs["Fac"], [(0.53, grey(0.0)), (0.545, grey(1.0))])
    n2 = N(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=6.0)
    L(nt, co, n2.inputs["Vector"])
    lcol = ramp(nt, n2.outputs["Fac"], [(0.35, (0.03, 0.12, 0.03)), (0.55, (0.10, 0.17, 0.05)), (0.7, (0.32, 0.26, 0.13))])
    mix = N(nt, "ShaderNodeMix", _data_type="RGBA")
    L(nt, land.outputs["Color"], mix.inputs["Factor"])
    mix.inputs["A"].default_value = (0.004, 0.02, 0.09, 1)
    L(nt, lcol.outputs["Color"], mix.inputs["B"])
    sepz = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, co, sepz.inputs[0])
    az = N(nt, "ShaderNodeMath", _operation="ABSOLUTE")
    L(nt, sepz.outputs["Z"], az.inputs[0])
    cap = ramp(nt, az.outputs[0], [(0.88, grey(0.0)), (0.92, grey(1.0))])
    mix2 = N(nt, "ShaderNodeMix", _data_type="RGBA")
    L(nt, cap.outputs["Color"], mix2.inputs["Factor"])
    L(nt, mix.outputs["Result"], mix2.inputs["A"])
    mix2.inputs["B"].default_value = (0.85, 0.88, 0.92, 1)
    rough = ramp(nt, land.outputs["Color"], [(0.0, grey(0.35)), (1.0, grey(0.95))])
    b = bsdf(nt, out, mix2.outputs["Result"])
    L(nt, rough.outputs["Color"], b.inputs["Roughness"])


def look_clouds(nt, out):
    co = obj_coords(nt)
    n = N(nt, "ShaderNodeTexNoise", Scale=3.5, Detail=8.0, Roughness=0.6, Distortion=0.6)
    L(nt, co, n.inputs["Vector"])
    a = ramp(nt, n.outputs["Fac"], [(0.5, grey(0.0)), (0.66, grey(0.9))])
    tr = N(nt, "ShaderNodeBsdfTransparent")
    df = N(nt, "ShaderNodeBsdfDiffuse")
    df.inputs["Color"].default_value = (0.9, 0.92, 0.95, 1)
    mx = N(nt, "ShaderNodeMixShader")
    L(nt, a.outputs["Color"], mx.inputs["Fac"])
    L(nt, tr.outputs[0], mx.inputs[1])
    L(nt, df.outputs[0], mx.inputs[2])
    L(nt, mx.outputs[0], out.inputs["Surface"])


def look_gas(stops, scale=3.0, distortion=2.5, warp=0.12, em=None, em_strength=0.0, rough=0.85, spot=None):
    def f(nt, out):
        fac, co = bands(nt, scale=scale, distortion=distortion, warp=warp)
        col = ramp(nt, fac, stops)
        csock = col.outputs["Color"]
        if spot is not None:  # Jupiter's Great Red Spot: ellipse mask around a surface point
            d = N(nt, "ShaderNodeVectorMath", _operation="SUBTRACT")
            L(nt, co, d.inputs[0])
            d.inputs[1].default_value = spot
            s = N(nt, "ShaderNodeVectorMath", _operation="MULTIPLY")
            L(nt, d.outputs[0], s.inputs[0])
            s.inputs[1].default_value = (1.0, 1.0, 2.1)
            ln = N(nt, "ShaderNodeVectorMath", _operation="LENGTH")
            L(nt, s.outputs[0], ln.inputs[0])
            mk = ramp(nt, ln.outputs["Value"], [(0.0, grey(1.0)), (0.15, grey(0.9)), (0.24, grey(0.0))])
            mx = N(nt, "ShaderNodeMix", _data_type="RGBA")
            L(nt, mk.outputs["Color"], mx.inputs["Factor"])
            L(nt, csock, mx.inputs["A"])
            mx.inputs["B"].default_value = (0.55, 0.16, 0.07, 1)
            csock = mx.outputs["Result"]
        esock = None
        if em is not None:
            esock = ramp(nt, fac, em).outputs["Color"]
        bsdf(nt, out, csock, rough=rough, emission_socket=esock, em_strength=em_strength)
    return f


def look_sun(nt, out):
    co = obj_coords(nt)
    n = N(nt, "ShaderNodeTexNoise", Scale=40.0, Detail=4.0)
    L(nt, co, n.inputs["Vector"])
    n2 = N(nt, "ShaderNodeTexNoise", Scale=4.0, Detail=3.0)
    L(nt, co, n2.inputs["Vector"])
    m = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
    L(nt, n.outputs["Fac"], m.inputs[0])
    L(nt, n2.outputs["Fac"], m.inputs[1])
    col = ramp(nt, m.outputs[0], [(0.1, (1.0, 0.12, 0.01)), (0.25, (1.0, 0.30, 0.03)), (0.4, (1.0, 0.55, 0.15))])
    lw = N(nt, "ShaderNodeLayerWeight", Blend=0.5)
    limb = ramp(nt, lw.outputs["Facing"], [(0.0, grey(1.0)), (0.6, grey(0.6)), (1.0, grey(0.15))])
    mul = N(nt, "ShaderNodeMix", _data_type="RGBA", _blend_type="MULTIPLY")
    mul.inputs["Factor"].default_value = 1.0
    L(nt, col.outputs["Color"], mul.inputs["A"])
    L(nt, limb.outputs["Color"], mul.inputs["B"])
    em = N(nt, "ShaderNodeEmission", Strength=1.5)
    L(nt, mul.outputs["Result"], em.inputs["Color"])
    L(nt, em.outputs[0], out.inputs["Surface"])


SPIN = math.radians(4.0)  # rad / s


def build_planet(p):
    k = p["key"]
    r, x = p["r"], p["x"]
    segs = 128 if k == "sun" else 96
    ob = sphere(k, segs, segs // 2)
    ob.location = (x, 0, 0)
    ob.scale = (r, r, r)
    m, nt, out = new_mat(k + "_m")
    tilt = (0.0, 0.0)
    if k == "mercury":
        look_mercury(nt, out)
    elif k == "mars":
        look_mars(nt, out)
    elif k == "venus":
        look_venus(nt, out)
    elif k == "earth":
        look_earth(nt, out)
        tilt = (math.radians(-23.4), 0)
    elif k == "neptune":
        look_gas([(0.0, (0.03, 0.08, 0.36)), (0.5, (0.04, 0.10, 0.44)), (1.0, (0.07, 0.16, 0.52))],
                 scale=0.9, distortion=0.5, warp=0.08)(nt, out)
    elif k == "uranus":
        look_gas([(0.0, (0.30, 0.58, 0.64)), (1.0, (0.45, 0.74, 0.78))], scale=0.6, distortion=0.3, warp=0.03, rough=1.0)(nt, out)
        tilt = (0, math.radians(82))
    elif k == "saturn":
        look_gas([(0.0, (0.55, 0.42, 0.24)), (0.35, (0.78, 0.64, 0.40)), (0.6, (0.70, 0.55, 0.33)), (1.0, (0.88, 0.78, 0.56))],
                 scale=1.5, distortion=0.4, warp=0.04)(nt, out)
        tilt = (math.radians(24), math.radians(-7))
    elif k == "jupiter":
        ta = next(s["ta"] for s in TL if s["key"] == "jupiter")
        lon = -math.pi / 2 + math.radians(12) - SPIN * (ta + 1.2)  # faces camera, right side, at arrival
        spot = (0.92 * math.cos(lon), 0.92 * math.sin(lon), -0.38)
        look_gas([(0.0, (0.30, 0.15, 0.08)), (0.25, (0.62, 0.38, 0.20)), (0.5, (0.90, 0.80, 0.64)),
                  (0.75, (0.70, 0.46, 0.26)), (1.0, (0.95, 0.90, 0.80))],
                 scale=1.7, distortion=0.6, warp=0.06, spot=spot)(nt, out)
    elif k == "kelt9":  # ultra-hot: glows from its own heat
        look_gas([(0.0, (0.5, 0.12, 0.02)), (1.0, (0.9, 0.45, 0.12))], scale=1.1, distortion=0.8, warp=0.2,
                 em=[(0.0, (1.0, 0.18, 0.01)), (0.6, (1.0, 0.42, 0.06)), (1.0, (1.0, 0.72, 0.30))], em_strength=2.2)(nt, out)
    elif k == "wasp17":  # dark, bloated
        look_gas([(0.0, (0.008, 0.006, 0.008)), (0.5, (0.025, 0.018, 0.022)), (1.0, (0.05, 0.035, 0.04))],
                 scale=1.0, distortion=0.6, warp=0.25,
                 em=[(0.0, (0.0, 0.0, 0.0)), (0.8, (0.0, 0.0, 0.0)), (1.0, (0.18, 0.02, 0.01))], em_strength=0.5)(nt, out)
    elif k == "hatp67":  # the puffiest: hazy amber giant
        look_gas([(0.0, (0.42, 0.20, 0.12)), (0.4, (0.72, 0.44, 0.28)), (0.7, (0.86, 0.62, 0.42)), (1.0, (0.95, 0.80, 0.62))],
                 scale=0.8, distortion=0.4, warp=0.3,
                 em=[(0.0, (0.25, 0.04, 0.0)), (1.0, (0.6, 0.2, 0.05))], em_strength=0.25)(nt, out)
    elif k == "sun":
        look_sun(nt, out)
        for a in ("visible_diffuse", "visible_glossy", "visible_shadow"):
            setattr(ob, a, False)
    ob.data.materials.append(m)
    ob.rotation_euler = (tilt[0], tilt[1], 0)
    extras = []
    if k == "earth":
        c = sphere("earth_clouds", 96, 48, 1.012)
        cm, cnt, cout = new_mat("clouds_m")
        look_clouds(cnt, cout)
        c.data.materials.append(cm)
        extras.append((c, 1.35))
        atm = shell_glow("earth_atm", 1.03, (0.25, 0.5, 1.0), 1.4,  # limb of the globe sits at facing ~0.76
                         [(0.0, grey(0.0)), (0.62, grey(0.0)), (0.74, grey(0.25)), (0.78, grey(1.0)), (0.9, grey(0.25)), (1.0, grey(0.0))])
        extras.append((atm, None))
    if k == "neptune":
        extras.append((shell_glow("nep_atm", 1.03, (0.2, 0.35, 1.0), 0.8,
                                  [(0.0, grey(0.0)), (0.66, grey(0.0)), (0.77, grey(0.8)), (0.9, grey(0.15)), (1.0, grey(0.0))]), None))
    if k == "kelt9":
        extras.append((shell_glow("kelt_halo", 1.30, (1.0, 0.35, 0.06), 1.2,
                                  [(0.0, grey(0.06)), (0.36, grey(0.45)), (0.6, grey(0.10)), (1.0, grey(0.0))]), None))
    if k == "wasp17":
        extras.append((shell_glow("wasp_haze", 1.05, (0.40, 0.22, 0.55), 0.35,
                                  [(0.0, grey(0.0)), (0.6, grey(0.03)), (0.71, grey(0.7)), (0.85, grey(0.1)), (1.0, grey(0.0))]), None))
    if k == "hatp67":
        extras.append((shell_glow("hat_haze", 1.10, (1.0, 0.55, 0.3), 0.9,
                                  [(0.0, grey(0.02)), (0.45, grey(0.10)), (0.6, grey(0.8)), (0.8, grey(0.12)), (1.0, grey(0.0))]), None))
    if k == "sun":
        extras.append((shell_glow("corona", 1.12, (1.0, 0.45, 0.1), 2.5,
                                  [(0.0, grey(0.0)), (0.5, grey(0.1)), (0.56, grey(0.6)), (0.75, grey(0.12)), (1.0, grey(0.0))]), None))
    if k == "saturn":
        rg = annulus("saturn_rings", 1.24, 2.27)
        rm, rnt, rout = new_mat("rings_m")
        co = obj_coords(rnt)
        ln = N(rnt, "ShaderNodeVectorMath", _operation="LENGTH")
        L(rnt, co, ln.inputs[0])
        mr = N(rnt, "ShaderNodeMapRange", **{"From Min": 1.24, "From Max": 2.27})
        L(rnt, ln.outputs["Value"], mr.inputs["Value"])
        alpha = ramp(rnt, mr.outputs["Result"], [
            (0.0, grey(0.05)), (0.27, grey(0.18)), (0.30, grey(0.8)), (0.62, grey(0.95)), (0.68, grey(0.03)),
            (0.72, grey(0.6)), (0.93, grey(0.55)), (0.95, grey(0.1)), (0.97, grey(0.4)), (1.0, grey(0.0))])
        stripes = N(rnt, "ShaderNodeTexWave", _wave_type="RINGS", Scale=22.0, Distortion=0.0, Detail=2.0)
        L(rnt, co, stripes.inputs["Vector"])
        am = N(rnt, "ShaderNodeMath", _operation="MULTIPLY")
        L(rnt, alpha.outputs["Color"], am.inputs[0])
        st = N(rnt, "ShaderNodeMapRange", **{"To Min": 0.6})
        L(rnt, stripes.outputs["Fac"], st.inputs["Value"])
        L(rnt, st.outputs["Result"], am.inputs[1])
        col = ramp(rnt, mr.outputs["Result"], [(0.0, (0.35, 0.30, 0.25)), (0.5, (0.85, 0.75, 0.58)), (1.0, (0.7, 0.62, 0.5))])
        df = N(rnt, "ShaderNodeBsdfDiffuse")
        L(rnt, col.outputs["Color"], df.inputs["Color"])
        tr = N(rnt, "ShaderNodeBsdfTransparent")
        mx = N(rnt, "ShaderNodeMixShader")
        L(rnt, am.outputs[0], mx.inputs["Fac"])
        L(rnt, tr.outputs[0], mx.inputs[1])
        L(rnt, df.outputs[0], mx.inputs[2])
        L(rnt, mx.outputs[0], rout.inputs["Surface"])
        rg.data.materials.append(rm)
        extras.append((rg, 0.0))
    if k == "uranus":
        rg = annulus("uranus_ring", 1.62, 2.02)
        rm, rnt, rout = new_mat("uring_m")
        co = obj_coords(rnt)
        ln = N(rnt, "ShaderNodeVectorMath", _operation="LENGTH")
        L(rnt, co, ln.inputs[0])
        mr = N(rnt, "ShaderNodeMapRange", **{"From Min": 1.62, "From Max": 2.02})
        L(rnt, ln.outputs["Value"], mr.inputs["Value"])
        alpha = ramp(rnt, mr.outputs["Result"], [
            (0.0, grey(0.0)), (0.05, grey(0.12)), (0.10, grey(0.0)), (0.45, grey(0.0)), (0.5, grey(0.10)), (0.55, grey(0.0)),
            (0.9, grey(0.0)), (0.95, grey(0.35)), (1.0, grey(0.0))])
        em = N(rnt, "ShaderNodeEmission", Strength=0.12)
        em.inputs["Color"].default_value = (0.7, 0.8, 0.85, 1)
        df = N(rnt, "ShaderNodeBsdfDiffuse")
        df.inputs["Color"].default_value = (0.35, 0.38, 0.42, 1)
        ad = N(rnt, "ShaderNodeAddShader")
        L(rnt, em.outputs[0], ad.inputs[0])
        L(rnt, df.outputs[0], ad.inputs[1])
        tr = N(rnt, "ShaderNodeBsdfTransparent")
        mx = N(rnt, "ShaderNodeMixShader")
        L(rnt, alpha.outputs["Color"], mx.inputs["Fac"])
        L(rnt, tr.outputs[0], mx.inputs[1])
        L(rnt, ad.outputs[0], mx.inputs[2])
        L(rnt, mx.outputs[0], rout.inputs["Surface"])
        rg.data.materials.append(rm)
        rg.visible_shadow = False
        extras.append((rg, 0.0))
    for e, _ in extras:
        e.location = ob.location
        e.scale = ob.scale
        e.rotation_euler = ob.rotation_euler
        if e.name in ("uranus_ring",):
            e.rotation_mode = "ZYX"
            e.rotation_euler = (0, math.radians(82), math.radians(-12))
    # slow spin (keyframed linear)
    spinners = [(ob, 1.0)] + [(e, s) for e, s in extras if s]
    for o, mult in spinners:
        o.rotation_mode = "ZYX"  # spin about the planet's own (tilted) axis
        base = list(o.rotation_euler)
        for f, tt in ((1, 0.0), (F_END + 1, DURATION)):
            o.rotation_euler = (base[0], base[1], base[2] + SPIN * mult * tt)
            o.keyframe_insert("rotation_euler", index=2, frame=f)
        if o.animation_data and o.animation_data.action:
            set_linear(o)
    return ob


def set_linear(o):
    try:
        for fc in o.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    except Exception:  # Blender 5 layered actions
        try:
            for layer in o.animation_data.action.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = "LINEAR"
        except Exception:
            pass


# ----------------------------------------------------------------------------- WORLD, LIGHTS, CAMERA
def star_image():
    """Screen-space star backdrop made with numpy (the camera never rotates, so stars are
    fixed in screen space anyway; an image lookup is ~20x cheaper than a procedural sky)."""
    import numpy as np
    W, H = RES_X, RES_Y
    rng = np.random.default_rng(42)
    img = np.zeros((H, W, 3), np.float32)
    k = W / 540.0
    n = int(1400 * k * k)
    xs, ys = rng.uniform(0, W, n), rng.uniform(0, H, n)
    mag = rng.pareto(2.2, n) * 0.06 + 0.02
    mag = np.minimum(mag, 1.6)
    tint = np.stack([np.ones(n), 0.9 + 0.1 * rng.random(n), 0.75 + 0.3 * rng.random(n)], 1)
    tint[rng.random(n) < 0.25] = (1.0, 0.82, 0.65)
    rad = 2 + int(2 * k)
    gy, gx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    for x, y, m, c in zip(xs, ys, mag, tint):
        sig = (0.45 + 0.5 * min(m, 1.0)) * k
        spl = np.exp(-((gx + (int(x) - x)) ** 2 + (gy + (int(y) - y)) ** 2) / (2 * sig * sig)) * m
        x0, y0 = int(x) - rad, int(y) - rad
        xa, ya = max(x0, 0), max(y0, 0)
        xb, yb = min(x0 + 2 * rad + 1, W), min(y0 + 2 * rad + 1, H)
        img[ya:yb, xa:xb] += spl[ya - y0:yb - y0, xa - x0:xb - x0, None] * c
    # faint cold nebula: smooth noise from upsampled random grids
    neb = np.zeros((H, W), np.float32)
    for cells, amp in ((4, 1.0), (9, 0.5), (20, 0.25)):
        g = rng.random((cells * 2 + 2, cells + 2)).astype(np.float32)
        yi = np.linspace(0, g.shape[0] - 2, H)
        xi = np.linspace(0, g.shape[1] - 2, W)
        y0i, x0i = yi.astype(int), xi.astype(int)
        fy, fx = (yi - y0i)[:, None], (xi - x0i)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        v = (g[y0i][:, x0i] * (1 - fx) + g[y0i][:, x0i + 1] * fx) * (1 - fy) + \
            (g[y0i + 1][:, x0i] * (1 - fx) + g[y0i + 1][:, x0i + 1] * fx) * fy
        neb += amp * v
    neb = np.clip(neb / 1.75 - 0.45, 0, 1) ** 2
    img += neb[:, :, None] * np.array([0.020, 0.010, 0.035], np.float32)
    im = bpy.data.images.new("stars", W, H, float_buffer=True)
    rgba = np.concatenate([img, np.ones((H, W, 1), np.float32)], 2)[::-1]  # Blender rows go bottom-up
    im.pixels.foreach_set(rgba.ravel())
    im.pack()
    return im


def build_world():
    w = bpy.data.worlds.new("space")
    w.use_nodes = True
    sc.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = N(nt, "ShaderNodeTexCoord")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = star_image()
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"
    L(nt, tc.outputs["Window"], tex.inputs["Vector"])
    bg = N(nt, "ShaderNodeBackground", Strength=1.0)
    L(nt, tex.outputs["Color"], bg.inputs["Color"])
    # stars only to camera; planets get (almost) no ambient from them
    lp = N(nt, "ShaderNodeLightPath")
    dark = N(nt, "ShaderNodeBackground", Strength=1.0)
    dark.inputs["Color"].default_value = (0.0015, 0.002, 0.004, 1)
    mx = N(nt, "ShaderNodeMixShader")
    L(nt, lp.outputs["Is Camera Ray"], mx.inputs["Fac"])
    L(nt, dark.outputs[0], mx.inputs[1])
    L(nt, bg.outputs[0], mx.inputs[2])
    L(nt, mx.outputs[0], out.inputs["Surface"])
    try:
        w.cycles.sampling_method = "NONE"  # world is black for lighting; skip importance map
    except Exception:
        pass


def sun_lamp(name, frm, energy, color, angle=0.6):
    ld = bpy.data.lights.new(name, "SUN")
    ld.energy = energy
    ld.color = color
    ld.angle = math.radians(angle)
    ob = link(bpy.data.objects.new(name, ld))
    d = -Vector(frm).normalized()  # direction the light travels
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def build_lights():
    sun_lamp("key", (1.0, -0.75, 0.55), 4.2, (1.0, 0.93, 0.84))      # from the right/front (where the Sun is)
    sun_lamp("rim", (-1.1, 1.6, 0.35), 7.0, (0.62, 0.74, 1.0))       # back-left rim


def build_camera():
    cd = bpy.data.cameras.new("cam")
    cd.lens = LENS
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = SENSOR
    cd.clip_start = 0.05
    cd.clip_end = 1e6
    cam = link(bpy.data.objects.new("cam", cd))
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    for f in range(1, F_END + 2):
        cx, w = cam_state((f - 1) / FPS)
        d = w * K_DIST
        h = w * 16 / 9
        cam.location = (cx, -d, -0.05 * h)  # planets sit a little above centre
        cam.keyframe_insert("location", frame=f)
    set_linear(cam)
    return cam


# ----------------------------------------------------------------------------- TEXT
FONTS = {}


def font(name):
    if name not in FONTS:
        path = os.path.join(FONT_DIR, name)
        FONTS[name] = bpy.data.fonts.load(path) if os.path.exists(path) else None
    return FONTS[name]


def fade_keys(sock, keys):
    for f, v in keys:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)


def hud_text(cam, text, y, size, f_in, f_out, fontfile="InterDisplay-Light.otf", color=(1, 1, 1),
             strength=1.0, spacing=1.0, fade=0.45, max_frac=0.85):
    """Text fixed to the camera. y in -1..1 of frame height, size = fraction of frame height.
    Auto-fit: shrunk so the widest line is <= max_frac of the frame width."""
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_character = spacing
    cu.space_line = 1.05
    fnt = font(fontfile)
    if fnt:
        cu.font = fnt
    ob = link(bpy.data.objects.new("txt", cu))
    cu.size = 1.0
    w1 = 0.0
    try:
        bpy.context.view_layer.update()
        xs = [v[0] for v in ob.bound_box]
        w1 = max(xs) - min(xs)
    except Exception:
        pass
    if w1 <= 0:
        w1 = 0.55 * spacing * max(len(s) for s in text.split("\n"))
    want = size * 2 * HALF_H
    max_w = max_frac * 2 * HALF_W
    cu.size = min(want, max_w / w1)
    m, nt, out = new_mat("txt_m")
    em = N(nt, "ShaderNodeEmission", Strength=strength)
    em.inputs["Color"].default_value = (*color, 1)
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    oi = N(nt, "ShaderNodeObjectInfo")
    L(nt, oi.outputs["Alpha"], mx.inputs["Fac"])
    L(nt, tr.outputs[0], mx.inputs[1])
    L(nt, em.outputs[0], mx.inputs[2])
    L(nt, mx.outputs[0], out.inputs["Surface"])
    fd = int(fade * FPS)
    for f, a in [(1, 0.0), (f_in, 0.0), (f_in + fd, 1.0), (f_out - fd, 1.0), (f_out, 0.0)]:
        ob.color = (1, 1, 1, a)
        ob.keyframe_insert("color", index=3, frame=f)
    ob.data.materials.append(m)
    ob.parent = cam
    ob.location = (0, y * HALF_H, -1.0)
    ob.visible_shadow = False
    for f, hide in ((1, True), (f_in, False), (f_out + 1, True)):
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)
    return ob


def fmt_km(km):
    if km >= 100000:
        return f"{round(km, -2):,.0f} km"
    return f"{km:,.0f} km"


def fmt_x(v):
    return f"{v:.2f}×" if v < 10 else f"{v:.1f}×"


def build_text(cam):
    for i, st in enumerate(TL):
        k = st["key"]
        nxt = TL[i + 1]["t0"] if i + 1 < len(TL) else DURATION
        if k in BY_KEY:
            p = BY_KEY[k]
            fi = fr(max(st["ta"] - 0.15, 0.25))
            fo = fr(min(nxt + 0.35, DURATION - 0.1))
            hud_text(cam, p["name"], -0.60, 0.050, fi, fo, "InterDisplay-SemiBold.otf", spacing=1.12, strength=1.1)
            line = f"{fmt_km(p['r_km'])} radius   ·   {fmt_x(p['r_km'] / R_EARTH)} Earth"
            hud_text(cam, line, -0.69, 0.021, fi + 4, fo, "Inter-Regular.otf", color=(0.75, 0.80, 0.88), strength=0.9)
            if "note" in p:
                hud_text(cam, f"{p['r_rj']:.2f}× JUPITER   ·   {p['note']}", -0.755, 0.016, fi + 8, fo,
                         "Inter-Medium.otf", color=(1.0, 0.62, 0.38), strength=0.9, spacing=1.08)
            if k == "hatp67":
                hud_text(cam, "largest precisely measured planet radius (Wang et al. 2025)", -0.815, 0.0145,
                         fi + 12, fo, "Inter-Light.otf", color=(0.6, 0.6, 0.65), strength=0.8)
        if st["cap"]:
            cs = st["ta"] + 0.35 if k != "mercury" else 0.5
            ce = st["te"] - 0.05 if k != "sun" else DURATION - 0.3
            hud_text(cam, st["cap"], 0.66, 0.040, fr(cs), fr(ce), "InterDisplay-Light.otf", strength=1.15, fade=0.6)
        if st["cap_move"]:
            hud_text(cam, st["cap_move"], 0.66, 0.036, fr(st["t0"] + 0.1), fr(st["ta"] + 0.1),
                     "InterDisplay-LightItalic.otf", color=(0.85, 0.88, 0.95), strength=1.0, fade=0.5)


# ----------------------------------------------------------------------------- RENDER SETTINGS
def setup_render():
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = RES_X, RES_Y, 100
    r.fps = FPS
    sc.frame_start, sc.frame_end = 1, F_END
    r.image_settings.file_format = "PNG"
    r.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    if THREADS:
        r.threads_mode = "FIXED"
        r.threads = THREADS
    if ENGINE.startswith("eevee"):
        for ident in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try:
                r.engine = ident
                break
            except TypeError:
                continue
        try:
            sc.eevee.taa_render_samples = SAMPLES
            sc.eevee.use_shadows = True
        except Exception:
            pass
        return
    r.engine = "CYCLES"
    c = sc.cycles
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.05
    c.use_denoising = True
    try:
        c.denoising_prefilter = "NONE"
        c.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        c.denoising_quality = "FAST" if SAMPLES <= 32 else "HIGH"  # OIDN HIGH costs ~2 s/frame on 2 threads
    except Exception:
        pass
    try:
        c.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    c.max_bounces = 6
    c.diffuse_bounces = 1
    c.glossy_bounces = 1
    c.transmission_bounces = 0
    c.volume_bounces = 0
    c.transparent_max_bounces = 12
    c.caustics_reflective = c.caustics_refractive = False
    c.device = "CPU"
    r.use_persistent_data = True
    if GPU:
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for t in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                try:
                    prefs.compute_device_type = t
                    prefs.get_devices()
                    if any(d.type == t for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = True
                        c.device = "GPU"
                        break
                except TypeError:
                    continue
        except Exception as ex:
            print("GPU setup failed:", ex)


# ----------------------------------------------------------------------------- AUDIO (numpy)
def reveal_times():
    """(time_sec, weight) for each boom = moment a new world settles in frame."""
    out = []
    for st in TL[1:]:
        k = st["key"]
        wgt = {"earth": 0.8, "neptune": 1.15, "saturn": 1.0, "jupiter": 1.1, "kelt9": 1.15, "wasp17": 1.0,
               "hatp67": 1.35, "lineup": 0.7, "sun": 1.8}.get(k, 0.75)
        out.append((st["ta"] - 0.12, wgt, k))
    return out


def make_audio(path, sr=44100):
    import numpy as np
    rng = np.random.default_rng(9)
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    T = DURATION

    def lowpass(x, fc, order=2):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / sr)
        X *= 1 / (1 + (f / fc) ** (2 * order))
        return np.fft.irfft(X, len(x))

    def bandpass(x, lo, hi):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / sr)
        X *= 1 / (1 + (f / hi) ** 4) * (1 - 1 / (1 + (f / lo) ** 4))
        return np.fft.irfft(X, len(x))

    # master swell: grows through the video, big lift for the Sun
    t_sun = TL[-1]["ta"]
    swell = 0.35 + 0.45 * (t / T) ** 1.4 + 0.35 * np.clip((t - (t_sun - 4)) / 4, 0, 1)
    swell *= np.clip(t / 2.5, 0, 1) * np.clip((T - t) / 2.2, 0, 1)

    # drone: D1 + D2 + A2 + a dark minor third, slowly beating
    drone = np.zeros((2, n))
    for ch in range(2):
        det = 1 + (0.0015 if ch else -0.0015)
        for f0, a in ((36.71, 0.55), (73.42, 0.35), (110.0, 0.16), (87.31, 0.07 + 0.0)):
            lfo = 0.75 + 0.25 * np.sin(2 * np.pi * (0.05 + 0.013 * f0 / 36) * t + ch + f0)
            ph = 2 * np.pi * f0 * det * t + 0.4 * np.sin(2 * np.pi * 0.07 * t)
            saw = sum(np.sin(k * ph) / k for k in range(1, 7))
            drone[ch] += a * lfo * saw
        drone[ch] = lowpass(drone[ch], 300)
    # rising tension: the minor-second rub fades in late
    rub = 0.06 * np.sin(2 * np.pi * 77.78 * t) * np.clip((t - T * 0.55) / (T * 0.3), 0, 1)
    drone += rub
    # dark wind
    wind = np.stack([bandpass(rng.standard_normal(n), 80, 900) for _ in range(2)])
    wind *= 0.08 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.04 * t + 1.0))
    mix = (drone * 0.55 + wind) * swell

    # booms + risers
    for tb, wgt, k in reveal_times():
        i0 = int(tb * sr)
        L_ = int(4.5 * sr)
        tt = np.arange(L_) / sr
        f_sweep = 26 + 52 * np.exp(-tt / 0.35)
        ph = 2 * np.pi * np.cumsum(f_sweep) / sr
        body = np.sin(ph) * np.exp(-tt / (1.0 + 0.5 * wgt))
        hit = lowpass(rng.standard_normal(L_), 300) * np.exp(-tt / 0.08) * 1.5
        boom = (body * 0.9 + hit * 0.5) * wgt
        if k == "sun":  # the last hit: low chord bloom
            bloom = sum(np.sin(2 * np.pi * f * tt) * a for f, a in ((36.71, 0.6), (55.0, 0.35), (73.42, 0.25)))
            boom += 0.6 * bloom * (1 - np.exp(-tt / 0.6)) * np.exp(-tt / 3.0)
        seg = slice(i0, min(n, i0 + L_))
        mix[:, seg] += boom[: seg.stop - seg.start]
        # riser before the hit: filtered noise swelling up
        rL = int(1.3 * sr)
        r0 = max(0, i0 - rL)
        rr = np.arange(i0 - r0) / sr
        env = (rr / 1.3) ** 3
        rs = bandpass(rng.standard_normal(i0 - r0), 200, 2500) * env * 0.12 * wgt
        mix[0, r0:i0] += rs
        mix[1, r0:i0] += np.roll(rs, 37)

    # long dark reverb (FFT convolution with decaying noise)
    irL = int(3.2 * sr)
    ir_t = np.arange(irL) / sr
    out = np.zeros_like(mix)
    for ch in range(2):
        ir = rng.standard_normal(irL) * np.exp(-ir_t / 0.9)
        ir = lowpass(ir, 1800)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = len(mix[ch]) + irL
        nfft = 1 << (m - 1).bit_length()
        wet = np.fft.irfft(np.fft.rfft(mix[ch], nfft) * np.fft.rfft(ir, nfft), nfft)[:n]
        out[ch] = 0.72 * mix[ch] + 0.45 * wet
    out = np.tanh(out / np.max(np.abs(out)) * 1.4)
    out *= 0.89 / np.max(np.abs(out))
    out *= np.clip((T - t) / 1.5, 0, 1)
    pcm = (out.T * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print("audio ->", path)


# ----------------------------------------------------------------------------- MAIN
def frame_path(f):
    return os.path.join(OUT_DIR, "frames", f"f_{f:04d}.png")


def render_frames(frames):
    os.makedirs(os.path.join(OUT_DIR, "frames"), exist_ok=True)
    import time
    for f in frames:
        p = frame_path(f)
        if os.path.exists(p) and os.path.getsize(p) > 0 and not FRAMES_ONLY:
            continue
        t0 = time.time()
        sc.frame_set(f)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"frame {f}/{F_END}  {time.time() - t0:.1f}s", flush=True)


def encode():
    import subprocess
    wav = os.path.join(OUT_DIR, "soundtrack.wav")
    mp4 = os.path.join(OUT_DIR, "size_comparison.mp4")
    vf = "vignette=angle=PI/5,noise=alls=5:allf=t,fade=t=in:st=0:d=1.2,fade=t=out:st=%.2f:d=1.4" % (DURATION - 1.5)
    src = os.path.join(OUT_DIR, "frames", "f_%04d.png")
    rate = FPS
    if STEP > 1:  # half-rate render: link every STEP-th frame into a contiguous sequence, blend back up
        seq = os.path.join(OUT_DIR, f"frames_step{STEP}")
        os.makedirs(seq, exist_ok=True)
        for i, f in enumerate(range(1, F_END + 1, STEP)):
            dst = os.path.join(seq, f"f_{i + 1:04d}.png")
            if not os.path.exists(dst):
                os.symlink(frame_path(f), dst)
        src = os.path.join(seq, "f_%04d.png")
        rate = FPS / STEP
        vf = f"minterpolate=fps={FPS}:mi_mode=blend," + vf
    cmd = ["ffmpeg", "-y", "-framerate", str(rate), "-i", src]
    if os.path.exists(wav):
        cmd += ["-i", wav]
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if os.path.exists(wav):
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd.append(mp4)
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)
    print("video ->", mp4)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"duration {DURATION:.1f}s, {F_END} frames @ {FPS} fps, {RES_X}x{RES_Y}, {ENGINE} {SAMPLES} spp")
    for p in PLANETS + [SUN]:
        print(f"  {p['name']:<11} r={p['r_km']:>9,.0f} km  x={p['x']:9.1f}  ({p['r_km'] / R_EARTH:.2f} Earth)")
    if "--audio" in argv:
        make_audio(os.path.join(OUT_DIR, "soundtrack.wav"))
    need_scene = FRAMES_ONLY or "--render" in argv or "--blend" in argv
    if need_scene:
        setup_render()
        build_world()
        build_lights()
        for p in PLANETS + [SUN]:
            build_planet(p)
        cam = build_camera()
        build_text(cam)
        if "--blend" in argv:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, "size_comparison.blend"))
        if FRAMES_ONLY:
            render_frames(FRAMES_ONLY)
        elif "--render" in argv:
            s = arg("--start", 1, int)
            e = arg("--end", F_END, int)
            render_frames(range(s, e + 1, STEP))
    if "--encode" in argv:
        encode()


main()
