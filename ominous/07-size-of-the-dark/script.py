"""
OMINOUS #7 - SIZE OF THE DARK
A cinematic planet size comparison: Mercury -> the largest-radius planet known.
All bodies are rendered at TRUE relative size (1 Blender unit = 1 Earth equatorial radius)
with an orthographic camera, so the pull-back keeps the scale exact.

Run headless:
  blender -b -P script.py -- --render
  blender -b -P script.py -- --frames 1,120,500      (preview stills)
  blender -b -P script.py -- --render --start 1 --end 300
Or with the bpy module:
  python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
"""

# ============================== CONFIG ======================================
CONFIG = dict(
    fps=24,
    duration=44.0,             # seconds (recomputed from the timeline below)
    resolution=(1080, 1920),
    resolution_percentage=53,  # -> 572x1018 (final encode scales to 576x1024)
    engine="CYCLES",
    samples=5,
    denoise=True,
    output="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/07/frames",
    font_name="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_thin="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
)
# ============================================================================

import sys
import os
import math

import bpy
import bmesh
from mathutils import Vector, Euler

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV):
            return ARGV[i + 1]
    return default


FPS = CONFIG["fps"]
BLENDER5 = bpy.app.version >= (5, 0, 0)

# ---------------------------------------------------------------------------
# DATA  (radii in Earth equatorial radii, R_E = 6378.1 km; R_J = 71492 km)
#   Solar System: NASA Planetary Fact Sheet equatorial radii.
#   Exoplanets:   R[R_J] x 11.209
# ---------------------------------------------------------------------------
RJ = 71492.0 / 6378.1  # 11.209
PLANETS = [
    # key,      label,          r,                value text,       sub text
    ("mercury", "MERCURY",      2439.7 / 6378.1,  "× 0.38 EARTH",   ""),
    ("mars",    "MARS",         3396.2 / 6378.1,  "× 0.53 EARTH",   ""),
    ("venus",   "VENUS",        6051.8 / 6378.1,  "× 0.95 EARTH",   ""),
    ("earth",   "EARTH",        1.0,              "× 1",            ""),
    ("neptune", "NEPTUNE",      24764 / 6378.1,   "× 3.88 EARTH",   ""),
    ("uranus",  "URANUS",       25559 / 6378.1,   "× 4.01 EARTH",   ""),
    ("saturn",  "SATURN",       60268 / 6378.1,   "× 9.45 EARTH",   ""),
    ("jupiter", "JUPITER",      RJ,               "× 11.2 EARTH",   ""),
    ("tres4",   "TrES-4 b",     1.838 * RJ,       "× 20.6 EARTH",   "1.84 × JUPITER"),
    ("kelt9",   "KELT-9 b",     1.891 * RJ,       "× 21.2 EARTH",   "1.89 × JUPITER  ·  HOTTER THAN MOST STARS"),
    ("hatp67",  "HAT-P-67 b",   2.140 * RJ,       "× 24.0 EARTH",   "2.14 × JUPITER  ·  LARGEST PLANET KNOWN"),
]
# timeline: (transition seconds INTO this planet, hold seconds ON this planet)
TIMING = {
    "mercury": (0.0, 3.2),
    "mars":    (1.2, 1.5),
    "venus":   (1.2, 1.5),
    "earth":   (1.2, 1.7),
    "neptune": (1.5, 1.7),
    "uranus":  (1.2, 1.5),
    "saturn":  (1.7, 2.1),
    "jupiter": (1.7, 1.9),
    "tres4":   (3.0, 1.8),   # long pan through the void between stars
    "kelt9":   (1.6, 2.2),
    "hatp67":  (1.8, 2.5),
}
FINAL_TRANS = 2.4      # pull back to reveal Earth beside the giant
FINAL_HOLD = 3.2       # "WE ARE HERE."
FADE_OUT = 1.2
TAIL_BLACK = 0.3

SATURN_RING_OUT = 136775 / 60268   # A ring outer edge, in Saturn radii (2.27)
SATURN_RING_IN = 74658 / 60268     # C ring inner edge (1.24)
FILL = 0.62                        # newest planet fills this fraction of frame width
ASPECT = 16 / 9

# sun direction (towards the sun): low, from the right, slightly behind
SUN_DIR = Vector((0.86, 0.10, 0.42)).normalized()

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def extent(key, r):
    return r * SATURN_RING_OUT if key == "saturn" else r


LAYOUT = {}
x = 0.0
prev = None
for key, label, r, val, sub in PLANETS:
    if prev is not None:
        pk, pr = prev
        gap = 0.18 * r
        if key == "tres4":
            gap = 70.0          # the dark between the stars
        if key == "hatp67":
            gap = 0.30 * r
        x += extent(pk, pr) + gap + extent(key, r)
    LAYOUT[key] = x
    prev = (key, r)

# timeline in seconds
SEG = []   # list of dict(key, t_in0, t_arr, t_leave)
t = 0.0
for key, label, r, val, sub in PLANETS:
    tr, hold = TIMING[key]
    SEG.append(dict(key=key, t0=t, ta=t + tr, tl=t + tr + hold, r=r, label=label, val=val, sub=sub))
    t += tr + hold
T_FINAL0 = t
T_FINAL_ARR = t + FINAL_TRANS
T_FADE0 = T_FINAL_ARR + FINAL_HOLD
T_END = T_FADE0 + FADE_OUT + TAIL_BLACK
CONFIG["duration"] = T_END
N_FRAMES = int(round(T_END * FPS))

R_H = PLANETS[-1][2]
X_H = LAYOUT["hatp67"]
EARTH_DOT = Vector((X_H + 1.18 * R_H, -2.0, -0.86 * R_H))  # tiny Earth beside the giant
FINAL_CAM_X = X_H + 0.30 * R_H
FINAL_W = 2 * R_H / 0.54


def smooth(a):
    a = min(1.0, max(0.0, a))
    return a * a * a * (a * (a * 6 - 15) + 10)


def ease(a):
    a = min(1.0, max(0.0, a))
    return a * a * (3 - 2 * a)


def frame_w(r):
    return 2 * r / FILL


def camera_at(ts):
    """returns (cam_x, cam_z, W) at time ts (seconds)."""
    def hold_state(i, a):
        s = SEG[i]
        W0 = frame_w(s["r"])
        return LAYOUT[s["key"]], W0 * (1.0 + 0.045 * a)

    for i, s in enumerate(SEG):
        if ts < s["ta"] and i > 0:
            # transition from SEG[i-1] end-of-hold to SEG[i]
            xa, Wa = hold_state(i - 1, 1.0)
            xb, Wb = hold_state(i, 0.0)
            a = smooth((ts - s["t0"]) / (s["ta"] - s["t0"]))
            # zoom leads slightly, pan follows -> the newcomer drifts in
            az = ease((ts - s["t0"]) / (s["ta"] - s["t0"]) * 1.15)
            if s["key"] == "tres4":      # the void: pan through pure darkness first
                az = a
            xc = xa + (xb - xa) * a
            W = math.exp(math.log(Wa) + (math.log(Wb) - math.log(Wa)) * az)
            return xc, -0.10 * W * ASPECT, W
        if ts < s["tl"]:
            hold = (s["tl"] - s["ta"])
            a = (ts - s["ta"]) / hold if hold > 0 else 0
            xc, W = hold_state(i, max(0.0, a))
            if i == 0:
                xc, W = hold_state(0, ts / s["tl"])
            return xc, -0.10 * W * ASPECT, W
    # final beat
    xa, Wa = hold_state(len(SEG) - 1, 1.0)
    za = -0.10 * Wa * ASPECT
    zb = -0.12 * FINAL_W * ASPECT
    a = smooth((ts - T_FINAL0) / FINAL_TRANS)
    drift = max(0.0, ts - T_FINAL_ARR) / (T_END - T_FINAL_ARR)
    W = math.exp(math.log(Wa) + (math.log(FINAL_W) - math.log(Wa)) * a) * (1 + 0.05 * drift)
    return xa + (FINAL_CAM_X - xa) * a, za + (zb - za) * a, W


# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = N_FRAMES
    sc.render.resolution_x, sc.render.resolution_y = CONFIG["resolution"]
    sc.render.resolution_percentage = CONFIG["resolution_percentage"]
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = CONFIG["samples"]
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.05
    cy.use_denoising = CONFIG["denoise"]
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    cy.max_bounces = 4
    cy.diffuse_bounces = 0
    cy.glossy_bounces = 0
    cy.transmission_bounces = 0
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 6
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    try:
        cy.use_light_tree = False
    except Exception:
        pass
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Base Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
    # world: pure black void
    w = bpy.data.worlds.new("Void")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg is None:
        bg = w.node_tree.nodes.new("ShaderNodeBackground")
        out = w.node_tree.nodes.new("ShaderNodeOutputWorld")
        w.node_tree.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0
    sc.world = w
    # image output
    ims = sc.render.image_settings
    if BLENDER5:
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


# ---------------------------------------------------------------------------
# Node helpers
# ---------------------------------------------------------------------------
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

    @staticmethod
    def sock(sockets, name):
        for s in sockets:
            if s.identifier == name:
                return s
        for s in sockets:
            if s.name == name and s.enabled:
                return s
        return sockets[name]

    def setin(self, node, name, val):
        s = self.sock(node.inputs, name)
        if hasattr(val, "bl_idname") or hasattr(val, "links"):
            self.link(val, s)
        else:
            s.default_value = val

    # ---- building blocks returning output sockets ----
    def coord(self):
        tc = self.n("ShaderNodeTexCoord")
        return tc.outputs["Object"]

    def noise(self, vec, scale, detail=4.0, rough=0.5, distortion=0.0):
        nn = self.n("ShaderNodeTexNoise")
        try:
            nn.noise_dimensions = "3D"
        except Exception:
            pass
        self.link(vec, nn.inputs["Vector"])
        nn.inputs["Scale"].default_value = scale
        nn.inputs["Detail"].default_value = detail
        nn.inputs["Roughness"].default_value = rough
        if "Distortion" in nn.inputs:
            nn.inputs["Distortion"].default_value = distortion
        return nn

    def wave(self, vec, scale, distortion, detail=3.0, dscale=1.0, phase=0.0):
        wv = self.n("ShaderNodeTexWave", wave_type="BANDS")
        wv.bands_direction = "Z"
        self.link(vec, wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = scale
        wv.inputs["Distortion"].default_value = distortion
        wv.inputs["Detail"].default_value = detail
        wv.inputs["Detail Scale"].default_value = dscale
        if "Phase Offset" in wv.inputs:
            wv.inputs["Phase Offset"].default_value = phase
        return wv.outputs["Fac"]

    def ramp(self, fac, stops, interp="LINEAR"):
        r = self.n("ShaderNodeValToRGB")
        cr = r.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (p, c) in zip(cr.elements, stops):
            el.position = p
            el.color = (c[0], c[1], c[2], 1.0) if len(c) == 3 else c
        self.link(fac, r.inputs["Fac"])
        return r

    def mix(self, fac, a, b, blend="MIX"):
        m = self.n("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        m.clamp_result = True
        self.setin(m, "Factor_Float", fac)
        self.setin(m, "A_Color", a if not isinstance(a, tuple) else (*a, 1.0))
        self.setin(m, "B_Color", b if not isinstance(b, tuple) else (*b, 1.0))
        return self.sock(m.outputs, "Result_Color")

    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op)
        m.use_clamp = clamp
        ins = [s for s in m.inputs]
        for s, v in zip(ins, [a, b]):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                s.default_value = v
            else:
                self.link(v, s)
        return m.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        m = self.n("ShaderNodeVectorMath", operation=op)
        ins = [s for s in m.inputs if s.enabled]
        if isinstance(a, (tuple, Vector)):
            m.inputs[0].default_value = a
        else:
            self.link(a, m.inputs[0])
        if b is not None:
            if isinstance(b, (tuple, Vector)):
                m.inputs[1].default_value = b
            else:
                self.link(b, m.inputs[1])
        if scale is not None:
            s = m.inputs.get("Scale")
            if isinstance(scale, (int, float)):
                s.default_value = scale
            else:
                self.link(scale, s)
        return m.outputs["Value"] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else m.outputs["Vector"]

    def smoothstep(self, v, lo, hi):
        mr = self.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self.link(v, mr.inputs["Value"])
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        mr.inputs["To Min"].default_value = 0.0
        mr.inputs["To Max"].default_value = 1.0
        return mr.outputs["Result"]

    def latitude(self, co, Z, amp, stretch):
        """(Z+1)/2 perturbed by longitude-streaked turbulence -> belts & zones."""
        q = self.vmath("MULTIPLY", co, (1.0, 1.0, stretch))
        n = self.noise(q, 2.2, 7, 0.62, 0.6)
        n2 = self.noise(co, 9.0, 4, 0.55)
        off = self.math("ADD", self.math("MULTIPLY", self.math("SUBTRACT", n.outputs["Fac"], 0.5), amp * 2),
                        self.math("MULTIPLY", self.math("SUBTRACT", n2.outputs["Fac"], 0.5), amp * 0.6))
        return self.math("ADD", self.math("MULTIPLY", self.math("ADD", Z, 1.0), 0.5), off)

    def scale_color(self, col, s):
        return self.vmath("SCALE", col, scale=s)


# ---------------------------------------------------------------------------
# Planet materials
# ---------------------------------------------------------------------------
REVEAL = {}   # key -> Value node (0 = hidden in darkness, 1 = fully lit)


def planet_material(mkey):
    mat = bpy.data.materials.new("M_" + mkey)
    key = "earth" if mkey == "earth_here" else mkey
    b = NB(mat)
    co = b.coord()
    z = b.n("ShaderNodeSeparateXYZ")
    b.link(co, z.inputs[0])
    Z = z.outputs["Z"]
    absZ = b.math("ABSOLUTE", Z)
    height = None
    bump_strength = 0.0
    atm = None          # (color, strength, power)
    night = None        # (color, strength, pattern socket)
    day_glow = None
    rough = 1.0

    if key == "mercury":
        n1 = b.noise(co, 2.5, 6, 0.55)
        base = b.ramp(n1.outputs["Fac"], [(0.3, (0.12, 0.115, 0.11)), (0.7, (0.31, 0.29, 0.27))])
        warp = b.vmath("ADD", co, b.vmath("SCALE", n1.outputs["Color"], scale=0.18))
        h = b.math("MULTIPLY", n1.outputs["Fac"], 0.5)
        rims = None
        for sc_, w_, thr in ((5.0, 0.9, 0.55), (13.0, 0.45, 0.45), (31.0, 0.2, 0.35)):
            v = b.n("ShaderNodeTexVoronoi", feature="F1")
            b.link(warp, v.inputs["Vector"]); v.inputs["Scale"].default_value = sc_
            sep = b.n("ShaderNodeSeparateColor")
            b.link(v.outputs["Color"], sep.inputs[0])
            rnd = sep.outputs[0]
            on = b.smoothstep(rnd, thr, thr + 0.05)                 # only some cells hold a crater
            size = b.math("ADD", 0.12, b.math("MULTIPLY", sep.outputs[1], 0.22))
            dn = b.math("DIVIDE", v.outputs["Distance"], size)
            bowl = b.math("SUBTRACT", 1.0, b.smoothstep(dn, 0.0, 1.0))
            rim = b.math("MULTIPLY", b.smoothstep(dn, 0.75, 1.0), b.math("SUBTRACT", 1.0, b.smoothstep(dn, 1.0, 1.5)))
            c = b.math("SUBTRACT", b.math("MULTIPLY", rim, 0.35), bowl)
            h = b.math("ADD", h, b.math("MULTIPLY", b.math("MULTIPLY", c, on), w_))
            r_on = b.math("MULTIPLY", rim, on)
            rims = r_on if rims is None else b.math("MAXIMUM", rims, r_on)
        height = h
        bump_strength = 0.5
        albedo = b.mix(b.math("MULTIPLY", rims, 0.45), base.outputs["Color"], (0.42, 0.40, 0.37))
    elif key == "mars":
        n1 = b.noise(co, 2.2, 7, 0.6, 0.3)
        base = b.ramp(n1.outputs["Fac"], [(0.35, (0.20, 0.075, 0.035)), (0.55, (0.46, 0.18, 0.075)),
                                          (0.75, (0.56, 0.26, 0.12))])
        cap = b.smoothstep(Z, 0.86, 0.93)
        albedo = b.mix(cap, base.outputs["Color"], (0.75, 0.72, 0.68))
        height = n1.outputs["Fac"]; bump_strength = 0.25
        atm = ((0.75, 0.42, 0.25), 0.05, 4.0)
    elif key == "venus":
        n1 = b.noise(co, 1.6, 4, 0.5, 1.2)
        wv = b.wave(n1.outputs["Color"], 1.6, 4.0, 2.0, 1.0)
        base = b.ramp(wv, [(0.0, (0.62, 0.53, 0.36)), (1.0, (0.86, 0.78, 0.60))])
        albedo = base.outputs["Color"]
        atm = ((1.0, 0.85, 0.6), 0.35, 3.0)
    elif key == "earth":
        n1 = b.noise(co, 1.3, 7, 0.6)
        land = b.smoothstep(n1.outputs["Fac"], 0.505, 0.515)
        landcol = b.ramp(b.noise(co, 6, 5, 0.6).outputs["Fac"],
                         [(0.3, (0.07, 0.10, 0.04)), (0.7, (0.30, 0.24, 0.13))])
        ocean = (0.008, 0.03, 0.10)
        surf = b.mix(land, ocean, landcol.outputs["Color"])
        ice = b.smoothstep(absZ, 0.88, 0.94)
        surf = b.mix(ice, surf, (0.8, 0.82, 0.85))
        cl = b.noise(co, 2.6, 7, 0.62, 0.6)
        cloud = b.smoothstep(cl.outputs["Fac"], 0.56, 0.72)
        albedo = b.mix(b.math("MULTIPLY", cloud, 0.9), surf, (0.85, 0.86, 0.88))
        height = cl.outputs["Fac"]; bump_strength = 0.08
        atm = ((0.25, 0.5, 1.0), 0.8 if mkey == "earth" else 3.0, 2.6 if mkey == "earth" else 1.4)
    elif key == "neptune":
        lat = b.latitude(co, Z, 0.05, 3.0)
        base = b.ramp(lat, [(0.0, (0.03, 0.08, 0.32)), (0.30, (0.05, 0.13, 0.45)), (0.42, (0.10, 0.22, 0.58)),
                            (0.47, (0.04, 0.11, 0.42)), (0.60, (0.06, 0.15, 0.50)), (0.80, (0.10, 0.20, 0.55)),
                            (1.0, (0.05, 0.12, 0.42))])
        spot_p = b.vmath("MULTIPLY", b.vmath("SUBTRACT", co, (0.55, -0.70, -0.40)), (1.0, 1.0, 1.9))
        spot = b.math("SUBTRACT", 1.0, b.smoothstep(b.vmath("LENGTH", spot_p), 0.08, 0.14))
        albedo = b.mix(b.math("MULTIPLY", spot, 0.8), base.outputs["Color"], (0.01, 0.02, 0.10))
        atm = ((0.2, 0.4, 1.0), 0.6, 2.6)
    elif key == "uranus":
        lat = b.latitude(co, Z, 0.02, 2.0)
        base = b.ramp(lat, [(0.0, (0.42, 0.66, 0.70)), (0.5, (0.50, 0.74, 0.78)), (1.0, (0.44, 0.68, 0.73))])
        albedo = base.outputs["Color"]
        atm = ((0.55, 0.9, 1.0), 0.45, 2.8)
    elif key == "saturn":
        lat = b.latitude(co, Z, 0.025, 4.0)
        base = b.ramp(lat, [(0.0, (0.36, 0.38, 0.40)), (0.12, (0.45, 0.42, 0.36)), (0.25, (0.62, 0.52, 0.34)),
                            (0.33, (0.74, 0.63, 0.42)), (0.40, (0.66, 0.54, 0.34)), (0.46, (0.84, 0.74, 0.54)),
                            (0.52, (0.86, 0.77, 0.58)), (0.58, (0.70, 0.58, 0.38)), (0.66, (0.78, 0.67, 0.46)),
                            (0.76, (0.60, 0.50, 0.33)), (0.88, (0.48, 0.44, 0.38)), (1.0, (0.36, 0.38, 0.42))])
        albedo = base.outputs["Color"]
        atm = ((1.0, 0.85, 0.55), 0.15, 3.0)
    elif key == "jupiter":
        lat = b.latitude(co, Z, 0.035, 7.0)
        base = b.ramp(lat, [(0.0, (0.40, 0.36, 0.32)), (0.10, (0.50, 0.42, 0.34)), (0.18, (0.78, 0.70, 0.58)),
                            (0.24, (0.55, 0.38, 0.25)), (0.30, (0.82, 0.74, 0.62)), (0.36, (0.48, 0.30, 0.18)),
                            (0.41, (0.62, 0.42, 0.27)), (0.45, (0.90, 0.85, 0.74)), (0.55, (0.86, 0.78, 0.64)),
                            (0.59, (0.45, 0.28, 0.17)), (0.65, (0.60, 0.40, 0.25)), (0.70, (0.88, 0.82, 0.70)),
                            (0.76, (0.58, 0.44, 0.31)), (0.84, (0.76, 0.68, 0.56)), (0.92, (0.52, 0.45, 0.38)),
                            (1.0, (0.40, 0.37, 0.34))])
        grs_p = b.vmath("MULTIPLY", b.vmath("SUBTRACT", co, (0.62, -0.60, -0.38)), (1.0, 1.0, 2.0))
        d = b.vmath("LENGTH", grs_p)
        grs = b.math("SUBTRACT", 1.0, b.smoothstep(d, 0.09, 0.16))
        ring = b.math("MULTIPLY", b.smoothstep(d, 0.11, 0.16), b.math("SUBTRACT", 1.0, b.smoothstep(d, 0.16, 0.22)))
        a1 = b.mix(b.math("MULTIPLY", ring, 0.6), base.outputs["Color"], (0.95, 0.90, 0.82))
        albedo = b.mix(grs, a1, (0.62, 0.24, 0.11))
        atm = ((1.0, 0.85, 0.65), 0.12, 3.0)
    else:  # hot Jupiters: charcoal day side, self-luminous night side
        lat = b.latitude(co, Z, 0.05, 6.0)
        bands = b.ramp(lat, [(0.0, (0.2, 0.2, 0.2)), (0.15, (0.7, 0.7, 0.7)), (0.27, (0.3, 0.3, 0.3)),
                             (0.38, (1.0, 1.0, 1.0)), (0.46, (0.35, 0.35, 0.35)), (0.54, (0.9, 0.9, 0.9)),
                             (0.63, (0.3, 0.3, 0.3)), (0.74, (0.8, 0.8, 0.8)), (0.86, (0.25, 0.25, 0.25)),
                             (1.0, (0.15, 0.15, 0.15))]).outputs["Color"]
        tn = b.noise(b.vmath("MULTIPLY", co, (1.0, 1.0, 5.0)), 3.0, 6, 0.6, 0.8)
        pat = b.mix(0.45, bands, tn.outputs["Color"], blend="MULTIPLY")
        pat = b.vmath("MULTIPLY", pat, (1.6, 1.6, 1.6))
        pat = b.vmath("SCALE", b.vmath("MULTIPLY", pat, pat), scale=1.6)
        albedo = b.mix(b.math("MULTIPLY", tn.outputs["Fac"], 0.6), (0.03, 0.027, 0.025), (0.09, 0.075, 0.065))
        if key == "tres4":
            night = ((0.95, 0.10, 0.02), 0.075, pat)
            atm = ((1.0, 0.30, 0.12), 0.10, 3.0)
        elif key == "kelt9":
            night = ((1.0, 0.24, 0.04), 0.7, pat)
            day_glow = ((1.0, 0.55, 0.26), 0.8, pat)
            atm = ((1.0, 0.55, 0.25), 1.3, 2.2)
        else:  # hatp67
            night = ((0.95, 0.09, 0.02), 0.11, pat)
            atm = ((1.0, 0.28, 0.10), 0.30, 2.4)

    # --- shading ---
    geo = b.n("ShaderNodeNewGeometry")
    diff = b.n("ShaderNodeBsdfDiffuse")
    b.link(albedo, diff.inputs["Color"])
    diff.inputs["Roughness"].default_value = rough
    if height is not None and bump_strength > 0:
        bp = b.n("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump_strength
        bp.inputs["Distance"].default_value = 0.02
        b.link(height, bp.inputs["Height"])
        b.link(bp.outputs["Normal"], diff.inputs["Normal"])
    ndl = b.vmath("DOT_PRODUCT", geo.outputs["Normal"], tuple(SUN_DIR))
    lit = b.smoothstep(ndl, -0.12, 0.35)
    unlit = b.math("SUBTRACT", 1.0, lit)
    lw = b.n("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    facing = lw.outputs["Facing"]

    emis_col = b.scale_color((0, 0, 0), 0.0)
    # faint cold rim on the dark limb: silhouettes barely visible against the void
    dark_rim = b.math("MULTIPLY", b.math("POWER", facing, 7.0), unlit)
    emis_col = b.vmath("ADD", emis_col, b.vmath("SCALE", (0.55, 0.62, 0.75), scale=b.math("MULTIPLY", dark_rim, 0.05)))
    if atm:
        col, strength, pw = atm
        lit_wide = b.smoothstep(ndl, -0.25, 0.25)
        rimv = b.math("MULTIPLY", b.math("POWER", facing, pw), lit_wide)
        emis_col = b.vmath("ADD", emis_col, b.vmath("SCALE", col, scale=b.math("MULTIPLY", rimv, strength)))
    if night:
        col, strength, pat = night
        glow_mask = b.math("POWER", unlit, 1.5)
        g = b.vmath("MULTIPLY", pat, b.vmath("SCALE", col, scale=b.math("MULTIPLY", glow_mask, strength)))
        emis_col = b.vmath("ADD", emis_col, g)
    if day_glow:
        col, strength, pat = day_glow
        g = b.vmath("MULTIPLY", pat, b.vmath("SCALE", col, scale=b.math("MULTIPLY", lit, strength)))
        emis_col = b.vmath("ADD", emis_col, g)
    em = b.n("ShaderNodeEmission")
    b.link(emis_col, em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    add = b.n("ShaderNodeAddShader")
    b.link(diff.outputs[0], add.inputs[0])
    b.link(em.outputs[0], add.inputs[1])
    # reveal (planet materialises out of the dark)
    blk = b.n("ShaderNodeEmission")
    blk.inputs["Color"].default_value = (0, 0, 0, 1)
    blk.inputs["Strength"].default_value = 0.0
    rv = b.n("ShaderNodeValue")
    rv.outputs[0].default_value = 1.0
    REVEAL[mkey] = rv
    mx = b.n("ShaderNodeMixShader")
    b.link(rv.outputs[0], mx.inputs[0])
    b.link(blk.outputs[0], mx.inputs[1])
    b.link(add.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs["Surface"])
    return mat


def ring_material():
    mat = bpy.data.materials.new("M_rings")
    b = NB(mat)
    co = b.coord()
    rr = b.vmath("LENGTH", co)
    # radial fine structure
    cx = b.n("ShaderNodeCombineXYZ")
    b.link(b.math("MULTIPLY", rr, 60.0), cx.inputs["X"])
    fine = b.noise(cx.outputs[0], 1.0, 3, 0.6)
    i0, i1 = SATURN_RING_IN, SATURN_RING_OUT

    def p(rad):
        return (rad - i0) / (i1 - i0)
    alpha = b.ramp(b.math("DIVIDE", b.math("SUBTRACT", rr, i0), i1 - i0), [
        (0.0, (0.0, 0.0, 0.0)), (p(1.25), (0.15, 0.15, 0.15)), (p(1.52), (0.30, 0.30, 0.30)),
        (p(1.54), (0.85, 0.85, 0.85)), (p(1.93), (0.95, 0.95, 0.95)), (p(1.952), (0.05, 0.05, 0.05)),
        (p(2.02), (0.08, 0.08, 0.08)), (p(2.03), (0.70, 0.70, 0.70)), (p(2.20), (0.62, 0.62, 0.62)),
        (p(2.215), (0.10, 0.10, 0.10)), (p(2.225), (0.55, 0.55, 0.55)), (p(2.26), (0.45, 0.45, 0.45)),
        (1.0, (0.0, 0.0, 0.0))])
    a = b.math("MULTIPLY", alpha.outputs["Color"], b.math("ADD", 0.6, b.math("MULTIPLY", fine.outputs["Fac"], 0.8)), clamp=True)
    col = b.ramp(fine.outputs["Fac"], [(0.3, (0.45, 0.38, 0.28)), (0.7, (0.78, 0.70, 0.56))])
    diff = b.n("ShaderNodeBsdfDiffuse")
    b.link(col.outputs["Color"], diff.inputs["Color"])
    tr = b.n("ShaderNodeBsdfTransparent")
    mx = b.n("ShaderNodeMixShader")
    b.link(a, mx.inputs[0])
    b.link(tr.outputs[0], mx.inputs[1])
    b.link(diff.outputs[0], mx.inputs[2])
    # reveal
    blk = b.n("ShaderNodeEmission"); blk.inputs["Strength"].default_value = 0.0
    hold = b.n("ShaderNodeMixShader")
    b.link(a, hold.inputs[0])
    b.link(tr.outputs[0], hold.inputs[1])
    b.link(blk.outputs[0], hold.inputs[2])
    rvn = b.n("ShaderNodeValue"); rvn.outputs[0].default_value = 1.0
    REVEAL["rings"] = rvn
    fin = b.n("ShaderNodeMixShader")
    b.link(rvn.outputs[0], fin.inputs[0])
    b.link(hold.outputs[0], fin.inputs[1])
    b.link(mx.outputs[0], fin.inputs[2])
    b.link(fin.outputs[0], b.out.inputs["Surface"])
    try:
        mat.blend_method = "HASHED"
    except Exception:
        pass
    return mat


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------
def uv_sphere(name, r, seg=128, rings=64):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.scale = (r, r, r)
    return ob


def annulus(name, r_in, r_out, seg=256):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    inner, outer = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        inner.append(bm.verts.new((r_in * math.cos(a), r_in * math.sin(a), 0)))
        outer.append(bm.verts.new((r_out * math.cos(a), r_out * math.sin(a), 0)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((inner[i], outer[i], outer[j], inner[j]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_shadow(ob, cast):
    try:
        ob.visible_shadow = cast
    except Exception:
        try:
            ob.cycles_visibility.shadow = cast
        except Exception:
            pass


OBJ = {}
SPIN = {}


def build_planets():
    for key, label, r, val, sub in PLANETS:
        xk = LAYOUT[key]
        if key == "saturn":
            piv = bpy.data.objects.new("saturn_tilt", None)
            bpy.context.scene.collection.objects.link(piv)
            piv.location = (xk, 0, 0)
            piv.rotation_euler = Euler((math.radians(19), math.radians(-16), 0), "XYZ")
            sph = uv_sphere("saturn", r, 160, 80)
            sph.parent = piv
            sph.location = (0, 0, 0)
            sph.scale = (r, r, r * 0.902)          # Saturn's oblateness
            sph.data.materials.append(planet_material(key))
            rg = annulus("saturn_rings", SATURN_RING_IN, SATURN_RING_OUT)
            rg.parent = piv
            rg.scale = (r, r, r)
            rg.data.materials.append(ring_material())
            set_shadow(sph, True)
            set_shadow(rg, True)
            OBJ[key] = sph
            OBJ["rings"] = rg
            SPIN[key] = (sph, 0.0)
            continue
        ob = uv_sphere(key, r, 160 if r > 3 else 96, 80 if r > 3 else 48)
        ob.location = (xk, 0, 0)
        if key == "jupiter":
            ob.scale = (r, r, r * 0.935)
        ob.data.materials.append(planet_material(key))
        set_shadow(ob, False)
        # axial tilt: planets face the camera with their equator roughly horizontal
        tilt = {"earth": 23.4, "mars": 25.2, "neptune": 28.3, "uranus": 97.8}.get(key, 4.0)
        ob.rotation_mode = "ZXY"
        OBJ[key] = ob
        SPIN[key] = (ob, math.radians(tilt))
    # the tiny Earth for the final beat
    e2 = uv_sphere("earth_here", 1.0, 64, 32)
    e2.location = EARTH_DOT
    e2.data.materials.append(planet_material("earth_here"))
    set_shadow(e2, False)
    OBJ["earth_here"] = e2


def spin_planets(ts):
    for key, (ob, tilt) in SPIN.items():
        if key == "saturn":
            ob.rotation_euler = (0, 0, 0.6 + 0.012 * ts)
            continue
        if key == "uranus":
            ob.rotation_euler = (math.radians(-80), 0.0, 0.3 + 0.01 * ts)
            continue
        # ZXY: spin about Z, then tilt slightly towards camera/side
        ob.rotation_euler = (math.radians(-12), math.radians(tilt * 0.6), 0.4 + 0.02 * ts)


# ---------------------------------------------------------------------------
# Camera, light, HUD text
# ---------------------------------------------------------------------------
CAM = None
HUD = None
TEXTS = {}


def build_camera_light():
    global CAM, HUD
    cd = bpy.data.cameras.new("Cam")
    cd.type = "ORTHO"
    cd.sensor_fit = "HORIZONTAL"
    cd.ortho_scale = 3.0
    cd.clip_start = 1.0
    cd.clip_end = 20000.0
    CAM = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(CAM)
    CAM.rotation_euler = (math.radians(90), 0, 0)
    CAM.location = (0, -5000, 0)
    bpy.context.scene.camera = CAM
    HUD = bpy.data.objects.new("HUD", None)
    bpy.context.scene.collection.objects.link(HUD)
    HUD.parent = CAM
    HUD.location = (0, 0, -50)

    ld = bpy.data.lights.new("Sun", "SUN")
    ld.energy = 5.0
    ld.angle = math.radians(0.6)
    ld.color = (1.0, 0.96, 0.90)
    try:
        ld.cycles.cast_shadow = True
    except Exception:
        pass
    sun = bpy.data.objects.new("Sun", ld)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = SUN_DIR.to_track_quat("Z", "Y").to_euler()


def text_material(name, color):
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    em = b.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = 1.0
    tr = b.n("ShaderNodeBsdfTransparent")
    mx = b.n("ShaderNodeMixShader")
    mx.inputs[0].default_value = 1.0
    b.link(tr.outputs[0], mx.inputs[1])
    b.link(em.outputs[0], mx.inputs[2])
    b.link(mx.outputs[0], b.out.inputs["Surface"])
    try:
        mat.blend_method = "BLEND"
    except Exception:
        pass
    return mat, mx


FONTS = {}


def font(path):
    if path not in FONTS:
        try:
            FONTS[path] = bpy.data.fonts.load(path)
        except Exception:
            FONTS[path] = None
    return FONTS[path]


def make_text(tid, body, y, size, spacing=1.5, thin=False, color=(0.86, 0.84, 0.80), x=0.0, align="CENTER"):
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
    ob.location = (x, y, 0)
    mat, mx = text_material("MT_" + tid, color)
    cu.materials.append(mat)
    set_shadow(ob, False)
    TEXTS[tid] = (ob, mx)
    return ob


ACCENT = (1.0, 0.36, 0.20)


def build_texts():
    make_text("hook1", "HOW BIG", 0.66, 0.050, 1.6)
    make_text("hook2", "CAN A PLANET GET?", 0.585, 0.050, 1.6)
    for s in SEG:
        k = s["key"]
        hot = k in ("kelt9", "hatp67", "tres4")
        make_text(k + "_n", s["label"], -0.47, 0.058, 1.55)
        make_text(k + "_v", s["val"], -0.55, 0.040, 1.6, thin=False,
                  color=ACCENT if hot else (0.80, 0.78, 0.75))
        if s["sub"]:
            make_text(k + "_s", s["sub"], -0.615, 0.026, 1.4, thin=False, color=(0.66, 0.64, 0.61))
    make_text("void1", "THEN WE LOOKED", 0.04, 0.042, 1.6, thin=True)
    make_text("void2", "AT OTHER STARS.", -0.025, 0.042, 1.6, thin=True)
    make_text("here", "WE ARE HERE.", 0.0, 0.040, 1.6)
    # thin ring marker around the tiny Earth
    me_ob = annulus("marker_ring", 0.90, 1.0, 96)
    me_ob.parent = HUD
    me_ob.rotation_euler = (0, 0, 0)
    mat, mx = text_material("MT_marker", (0.86, 0.84, 0.80))
    me_ob.data.materials.append(mat)
    set_shadow(me_ob, False)
    TEXTS["marker"] = (me_ob, mx)


def fade_window(ts, t_in, t_out, fin=0.5, fout=0.5):
    if ts < t_in or ts > t_out + fout:
        return 0.0
    a = ease((ts - t_in) / fin) if fin > 0 else 1.0
    b = 1.0 - ease((ts - t_out) / fout) if ts > t_out else 1.0
    return max(0.0, min(a, b))


def set_alpha(tid, a):
    ob, mx = TEXTS[tid]
    mx.inputs[0].default_value = a
    ob.hide_render = a <= 0.002


# ---------------------------------------------------------------------------
# Per-frame update
# ---------------------------------------------------------------------------
def update(frame):
    sc = bpy.context.scene
    ts = (frame - 1) / FPS
    cx, cz, W = camera_at(ts)
    CAM.location = (cx, -5000, cz)
    CAM.data.ortho_scale = W
    HUD.scale = (W, W, W)
    spin_planets(ts)

    # global exposure: fade in from black, fade out at the end
    g = ease(ts / 1.4) * (1.0 - ease((ts - T_FADE0) / FADE_OUT))
    sc.view_settings.exposure = math.log2(max(g, 1e-4))

    # reveals: each planet comes out of the dark as the camera reaches it
    for i, s in enumerate(SEG):
        k = s["key"]
        if i == 0:
            rv = 1.0
        else:
            rv = 0.04 + 0.96 * ease((ts - s["t0"] - 0.15) / max(0.4, (s["ta"] - s["t0"]) * 0.95))
        if k == "kelt9":
            rv *= 1.0 - ease((ts - T_FINAL0) / FINAL_TRANS)
        REVEAL[k].outputs[0].default_value = rv
        if k == "saturn":
            REVEAL["rings"].outputs[0].default_value = rv
    re = ease((ts - T_FINAL0 - 0.9 * FINAL_TRANS) / 0.9)
    OBJ["earth_here"].hide_render = re <= 0.0
    REVEAL["earth_here"].outputs[0].default_value = re

    # texts
    set_alpha("hook1", fade_window(ts, 0.5, 2.5, 0.8, 0.6))
    set_alpha("hook2", fade_window(ts, 0.9, 2.5, 0.8, 0.6))
    for i, s in enumerate(SEG):
        k = s["key"]
        t_in = (2.6 if i == 0 else s["ta"] - 0.35)
        t_out = s["tl"] - 0.05 if i < len(SEG) - 1 else T_FINAL0 + 0.6
        a = fade_window(ts, t_in, t_out, 0.45, 0.35)
        set_alpha(k + "_n", a)
        set_alpha(k + "_v", fade_window(ts, t_in + 0.15, t_out, 0.45, 0.35))
        if s["sub"]:
            set_alpha(k + "_s", fade_window(ts, t_in + 0.35, t_out, 0.5, 0.35))
    sv = [s for s in SEG if s["key"] == "tres4"][0]
    set_alpha("void1", fade_window(ts, sv["t0"] + 0.25, sv["ta"] - 1.0, 0.6, 0.6))
    set_alpha("void2", fade_window(ts, sv["t0"] + 0.55, sv["ta"] - 1.0, 0.6, 0.6))

    # final: marker + text locked to the tiny Earth's projected position
    hx = (EARTH_DOT.x - cx) / W
    hy = (EARTH_DOT.z - cz) / W
    am = fade_window(ts, T_FINAL_ARR - 0.3, T_END, 0.8, 0.1)
    mk, _ = TEXTS["marker"]
    rad = 0.032 * (1.0 + 0.6 * (1.0 - ease((ts - (T_FINAL_ARR - 0.3)) / 1.0)))
    mk.location = (hx, hy, 0.5)
    mk.scale = (rad, rad, rad)
    set_alpha("marker", am * 0.85)
    ht, _ = TEXTS["here"]
    ht.location = (hx, hy - 0.075, 0)
    set_alpha("here", fade_window(ts, T_FINAL_ARR + 0.5, T_END, 0.9, 0.1))


# ---------------------------------------------------------------------------
def main():
    sc = reset_scene()
    build_camera_light()
    build_planets()
    build_texts()
    out = arg("--out", CONFIG["output"])
    os.makedirs(out, exist_ok=True)
    print(f"[size-of-the-dark] duration {T_END:.2f}s, {N_FRAMES} frames")
    for s in SEG:
        print(f"   {s['key']:8s} arrive {s['ta']:6.2f}s  leave {s['tl']:6.2f}s  r={s['r']:.3f}")
    print(f"   final arrive {T_FINAL_ARR:.2f}s  fade {T_FADE0:.2f}s  end {T_END:.2f}s")
    if "--blend" in ARGV:
        update(1)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "scene.blend"))
    frames = []
    if arg("--frames"):
        frames = [int(v) for v in arg("--frames").split(",")]
    elif "--render" in ARGV:
        a = int(arg("--start", 1)); e = int(arg("--end", N_FRAMES)); st = int(arg("--step", 1))
        frames = list(range(a, e + 1, st))
    skip = "--skip-existing" in ARGV
    import time
    for f in frames:
        path = os.path.join(out, f"f_{f:04d}.png")
        if skip and os.path.exists(path):
            continue
        t0 = time.time()
        sc.frame_set(f)
        update(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"frame {f} {time.time() - t0:.2f}s", flush=True)


main()
