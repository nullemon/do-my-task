"""
OMINOUS #10 - THE SKY THAT'S COMING
The same night landscape (a ridge and one bare tree) while billions of years pass.
Andromeda grows from a faint smudge into a sky-filling spiral, the two galaxies tear
each other apart, the sky fills with newborn stars, and a single glowing elliptical
galaxy ("Milkomeda") is left.

Everything in the sky is a procedural emission shader on a flat plane (no particles,
no lights, no volumes), so frames render fast on CPU Cycles.

Run headless:
  blender -b -P script.py -- --render                       (all frames)
  blender -b -P script.py -- --render --skip-existing       (resume)
  blender -b -P script.py -- --frames 1,300,700             (preview stills)
  blender -b -P script.py -- --render --start 1 --end 400 --step 1
Or with the bpy module:
  python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
"""

# ============================== CONFIG ======================================
CONFIG = dict(
    fps=24,
    duration=52.0,              # seconds
    resolution=(576, 1024),     # rendered at 100 %
    resolution_percentage=100,
    engine="CYCLES",
    samples=4,
    denoise=False,              # emission-only scene: AA noise only, denoiser not needed
    threads=2,                  # 0 = auto (shared machine: 2 per process, run 2 processes)
    output="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/10/frames",
    font_name="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_thin="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
)
# ============================================================================

import sys
import os
import math
import time

import bpy
import bmesh
from mathutils import Vector, Euler, Matrix

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV):
            return ARGV[i + 1]
    return default


FPS = CONFIG["fps"]
N_FRAMES = int(round(CONFIG["duration"] * FPS))
BLENDER5 = bpy.app.version >= (5, 0, 0)

LENS = 28.0
SENSOR_H = 36.0
TANV = (SENSOR_H / 2) / LENS                     # tan(half vertical fov)
TANH = TANV * CONFIG["resolution"][0] / CONFIG["resolution"][1]
PITCH0 = 10.0                                    # camera pitch above horizon (deg)

ACCENT = (0.80, 0.70, 1.00)                      # violet-white
TEXT_COL = (0.88, 0.86, 0.84)


# ---------------------------------------------------------------------------
# Timeline helpers
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


def window(ts, t_in, t_out, fin=0.6, fout=0.6):
    if ts < t_in or ts > t_out + fout:
        return 0.0
    a = smooth((ts - t_in) / fin) if fin > 0 else 1.0
    b = 1.0 - smooth((ts - t_out) / fout) if ts > t_out else 1.0
    return clamp(min(a, b))


# Years shown on the counter, keyed on video time (scenario follows the
# van der Marel et al. 2012 / NASA sequence, IF the galaxies merge).
YEAR_KEYS = [
    (0.0, 0.0), (9.0, 0.0), (20.0, 2.0e9), (25.0, 3.75e9), (31.0, 4.0e9),
    (38.0, 5.1e9), (45.0, 7.0e9), (52.0, 7.3e9),
]


def years_at(ts):
    for (t0, y0), (t1, y1) in zip(YEAR_KEYS, YEAR_KEYS[1:]):
        if ts <= t1:
            a = clamp((ts - t0) / (t1 - t0))
            a = a * a * (3 - 2 * a) * 0.35 + a * 0.65
            return lerp(y0, y1, a)
    return YEAR_KEYS[-1][1]


# ---------------------------------------------------------------------------
# Scene
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
    cy.use_adaptive_sampling = False
    cy.use_denoising = CONFIG["denoise"]
    if CONFIG["denoise"]:
        try:
            cy.denoiser = "OPENIMAGEDENOISE"
        except Exception:
            pass
    cy.max_bounces = 0
    cy.diffuse_bounces = 0
    cy.glossy_bounces = 0
    cy.transmission_bounces = 0
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 12
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    try:
        cy.use_light_tree = False
    except Exception:
        pass
    try:
        cy.pixel_filter_width = 1.2
    except Exception:
        pass
    if CONFIG["threads"]:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = CONFIG["threads"]
    try:
        sc.view_settings.view_transform = "AgX"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except Exception:
            continue
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
# Node helper
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

    def _set(self, sock, v):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = v
        else:
            self.link(v, sock)

    def m(self, op, a, b=None, c=None, clamp=False):
        node = self.n("ShaderNodeMath", operation=op)
        node.use_clamp = clamp
        for s, v in zip(node.inputs, (a, b, c)):
            if v is not None:
                self._set(s, v)
        return node.outputs[0]

    # sugar
    def add(self, a, b): return self.m("ADD", a, b)
    def sub(self, a, b): return self.m("SUBTRACT", a, b)
    def mul(self, a, b): return self.m("MULTIPLY", a, b)
    def pw(self, a, b): return self.m("POWER", a, b)

    def expneg(self, a, k):
        """exp(-a/k)"""
        return self.m("EXPONENT", self.m("MULTIPLY", a, -1.0 / k))

    def gauss(self, a, w):
        """exp(-(a/w)^2)"""
        q = self.m("MULTIPLY", a, 1.0 / w) if isinstance(w, (int, float)) else self.m("DIVIDE", a, w)
        return self.m("EXPONENT", self.m("MULTIPLY", self.m("MULTIPLY", q, q), -1.0))

    def sstep(self, v, lo, hi):
        mr = self.n("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        self._set(mr.inputs["Value"], v)
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        mr.inputs["To Min"].default_value = 0.0
        mr.inputs["To Max"].default_value = 1.0
        return mr.outputs["Result"]

    def value(self, v=0.0):
        node = self.n("ShaderNodeValue")
        node.outputs[0].default_value = v
        return node

    def xyz(self):
        tc = self.n("ShaderNodeTexCoord")
        sp = self.n("ShaderNodeSeparateXYZ")
        self.link(tc.outputs["Object"], sp.inputs[0])
        return tc.outputs["Object"], sp.outputs[0], sp.outputs[1], sp.outputs[2]

    def combine(self, x, y, z=0.0):
        c = self.n("ShaderNodeCombineXYZ")
        self._set(c.inputs[0], x)
        self._set(c.inputs[1], y)
        self._set(c.inputs[2], z)
        return c.outputs[0]

    def noise(self, vec, scale, detail=3.0, rough=0.5, w=None):
        nn = self.n("ShaderNodeTexNoise")
        try:
            nn.noise_dimensions = "3D" if w is None else "4D"
        except Exception:
            pass
        self.link(vec, nn.inputs["Vector"])
        nn.inputs["Scale"].default_value = scale
        nn.inputs["Detail"].default_value = detail
        nn.inputs["Roughness"].default_value = rough
        if w is not None and "W" in nn.inputs:
            nn.inputs["W"].default_value = w
        return nn.outputs["Fac"]

    def voronoi(self, vec, scale, rnd=1.0):
        vn = self.n("ShaderNodeTexVoronoi")
        try:
            vn.voronoi_dimensions = "3D"
        except Exception:
            pass
        vn.feature = "F1"
        self.link(vec, vn.inputs["Vector"])
        vn.inputs["Scale"].default_value = scale
        if "Randomness" in vn.inputs:
            vn.inputs["Randomness"].default_value = rnd
        return vn.outputs["Distance"], vn.outputs["Color"]

    def vscale(self, vec, s):
        node = self.n("ShaderNodeVectorMath", operation="SCALE")
        self.link(vec, node.inputs[0])
        self._set(node.inputs["Scale"], s)
        return node.outputs["Vector"]

    def vadd(self, a, b):
        node = self.n("ShaderNodeVectorMath", operation="ADD")
        self._set(node.inputs[0], a)
        self._set(node.inputs[1], b)
        return node.outputs["Vector"]

    def col(self, rgb):
        """constant colour as a vector socket"""
        c = self.n("ShaderNodeCombineXYZ")
        for i in range(3):
            c.inputs[i].default_value = rgb[i]
        return c.outputs[0]

    def ctimes(self, rgb, f):
        """colour constant * float socket -> vector"""
        return self.vscale(self.col(rgb), f)

    def emit_add(self, color_vec, transp=None, strength=1.0):
        em = self.n("ShaderNodeEmission")
        self.link(color_vec, em.inputs["Color"])
        self._set(em.inputs["Strength"], strength)
        tr = self.n("ShaderNodeBsdfTransparent")
        if transp is not None:
            self.link(transp, tr.inputs["Color"])
        ad = self.n("ShaderNodeAddShader")
        self.link(tr.outputs[0], ad.inputs[0])
        self.link(em.outputs[0], ad.inputs[1])
        self.link(ad.outputs[0], self.out.inputs["Surface"])


PARAM = {}     # name -> Value node output (animated per frame)


def P(b, name, v=0.0):
    node = b.value(v)
    PARAM.setdefault(name, []).append(node.outputs[0])
    return node.outputs[0]


def set_param(name, v):
    for s in PARAM.get(name, []):
        s.default_value = v


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def mat_stars():
    """background star field + faint horizon airglow. Plane object coords -1..1."""
    mat = bpy.data.materials.new("M_stars")
    b = NB(mat)
    co, x, y, z = b.xyz()
    co = b.combine(b.mul(x, TANH / TANV), y, 0.0)      # square texels on the non-square plane
    tot = None
    px = 2.0 / 1.25 / CONFIG["resolution"][1]           # object-coord units per pixel
    for scale, thr, size, gain in ((90.0, 0.80, 0.9, 0.9), (34.0, 0.88, 1.4, 3.0)):
        d, c = b.voronoi(co, scale)
        sc = b.n("ShaderNodeSeparateColor")
        b.link(c, sc.inputs[0])
        rnd = sc.outputs[0]
        keep = b.sstep(rnd, thr, 1.0)                       # only some cells host a star
        core = b.m("SUBTRACT", 1.0, b.sstep(d, 0.0, size * px * scale))
        s = b.mul(b.mul(keep, core), gain)
        tint = b.n("ShaderNodeMix", data_type="RGBA", blend_type="MIX")
        sid = lambda socks, ident: [k for k in socks if k.identifier == ident][0]
        b.link(sc.outputs[1], sid(tint.inputs, "Factor_Float"))
        sid(tint.inputs, "A_Color").default_value = (1.0, 0.82, 0.66, 1)
        sid(tint.inputs, "B_Color").default_value = (0.70, 0.78, 1.0, 1)
        cv = b.vscale(sid(tint.outputs, "Result_Color"), s)
        tot = cv if tot is None else b.vadd(tot, cv)
    # faint dust of unresolved stars
    fn = b.noise(co, 6.0, 3, 0.6)
    haze = b.mul(b.sstep(fn, 0.45, 0.8), 0.006)
    tot = b.vadd(tot, b.ctimes((0.6, 0.6, 0.85), haze))
    # airglow near the horizon (local y ~ -0.42 is the horizon line on this plane)
    hz = b.expneg(b.m("MAXIMUM", b.add(y, 0.40), 0.0), 0.16)
    glow = b.mul(hz, b.add(0.055, b.mul(P(b, "skyglow"), 0.06)))
    tot = b.vadd(tot, b.ctimes((0.42, 0.36, 0.75), glow))
    # overall lift of the sky (late phases: the merger lights up the night)
    tot = b.vadd(tot, b.ctimes((0.30, 0.25, 0.50), b.mul(P(b, "skyglow"), 0.008)))
    tot = b.vscale(tot, P(b, "stars", 1.0))
    b.emit_add(tot)
    return mat


def mat_galaxy(name, pname, arm_col, core_col, pitch_deg=14.0, seed=0.0):
    """Procedural two-armed logarithmic spiral. Object coords -1..1 on a plane.
    params: <p>_bright, <p>_warp (tidal winding), <p>_burst (star-forming knots)."""
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    co, x, y, z = b.xyz()
    warp = P(b, pname + "_warp")
    burst = P(b, pname + "_burst")
    bright = P(b, pname + "_bright", 1.0)
    # tidal shear: stretch x with warp, so the disk elongates
    xs = b.mul(x, b.sub(1.0, b.mul(warp, 0.25)))
    ys = b.add(y, b.mul(b.mul(warp, 0.25), b.m("SINE", b.mul(x, 2.2))))
    r2 = b.add(b.mul(xs, xs), b.mul(ys, ys))
    r = b.m("SQRT", r2)
    th = b.m("ARCTAN2", ys, xs)
    lnr = b.m("LOGARITHM", b.add(r, 0.003), math.e)
    co2 = b.combine(xs, ys, seed)
    n1 = b.noise(co2, 3.0, 3, 0.55)
    thw = b.add(th, b.mul(b.mul(warp, 4.0), r2))                    # extra winding
    k = 2.0 / math.tan(math.radians(pitch_deg))
    phase = b.add(b.sub(b.mul(thw, 2.0), b.mul(lnr, k)), b.mul(b.sub(n1, 0.5), 2.2))
    arm = b.pw(b.add(b.mul(b.m("COSINE", phase), 0.5), 0.5), 3.0)
    dustp = b.pw(b.add(b.mul(b.m("COSINE", b.add(phase, 0.85)), 0.5), 0.5), 5.0)
    disk = b.mul(b.expneg(r, 0.26), b.sub(1.0, b.sstep(r, 0.62, 0.98)))
    clump = b.sstep(b.noise(co2, 16.0, 2, 0.6), 0.45, 0.78)
    fine = b.noise(co2, 45.0, 2, 0.5)
    armlum = b.mul(disk, b.add(0.05, b.mul(arm, b.add(0.35, b.mul(clump, 1.2)))))
    armlum = b.mul(armlum, b.add(0.75, b.mul(fine, 0.5)))
    bulge = b.add(b.mul(b.expneg(r, 0.022), 3.0), b.mul(b.expneg(r, 0.08), 0.55))
    halo = b.mul(b.mul(b.expneg(r, 0.40), 0.025), b.sub(1.0, b.sstep(r, 0.7, 1.0)))
    dustmask = b.mul(b.mul(dustp, b.sstep(r, 0.05, 0.16)), b.sub(1.0, b.sstep(r, 0.38, 0.72)))
    dustmask = b.mul(dustmask, b.sstep(b.noise(co2, 9.0, 2, 0.6), 0.3, 0.6))
    dim = b.sub(1.0, b.mul(dustmask, 0.85))
    # star-forming knots (pink HII + blue clusters), boosted by 'burst'
    # tiny star-forming knots: voronoi points (aspect-corrected so they stay round)
    asp = b.combine(x, b.mul(y, P(b, pname + "_aspect", 0.5)), seed)
    vd, vc = b.voronoi(b.vscale(asp, 1.0), 240.0)
    vsc = b.n("ShaderNodeSeparateColor")
    b.link(vc, vsc.inputs[0])
    pts = b.mul(b.sub(1.0, b.sstep(vd, 0.0, 0.36)), b.sstep(vsc.outputs[0], 0.35, 0.85))
    hii = b.sstep(b.noise(co2, 7.0, 1, 0.5), 0.5, 0.75)
    kn = b.mul(pts, b.add(0.3, hii))
    knots = b.mul(b.mul(b.mul(kn, arm), b.add(disk, b.mul(burst, 0.12))), b.add(0.1, b.mul(burst, 3.5)))
    c = b.vadd(b.ctimes(core_col, bulge), b.ctimes(arm_col, b.add(armlum, halo)))
    c = b.vscale(c, dim)
    c = b.vadd(c, b.ctimes((1.0, 0.42, 0.70), b.mul(knots, 1.0)))
    c = b.vadd(c, b.ctimes((0.80, 0.45, 0.85), b.mul(b.mul(hii, b.mul(arm, b.mul(disk, burst))), 0.35)))
    c = b.vscale(c, bright)
    tr = b.combine(b.sub(1.0, b.mul(dustmask, 0.7)), b.sub(1.0, b.mul(dustmask, 0.72)), b.sub(1.0, b.mul(dustmask, 0.65)))
    b.emit_add(c, tr)
    return mat


def mat_tail(name, pname):
    """Curved tidal tail: an arc of stars that fades along its length."""
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    co, x, y, z = b.xyz()
    amt = P(b, pname)
    cx, cy, R = 0.0, -0.35, 0.62
    dx = b.sub(x, cx)
    dy = b.sub(y, cy)
    rr = b.m("SQRT", b.add(b.mul(dx, dx), b.mul(dy, dy)))
    phi = b.m("ARCTAN2", dy, dx)                    # 0 at +x, pi/2 at top
    nn = b.noise(co, 4.0, 4, 0.6)
    d = b.m("ABSOLUTE", b.sub(b.add(rr, b.mul(b.sub(nn, 0.5), 0.10)), R))
    along = b.sstep(phi, -0.3, 0.4)
    fade = b.sub(1.0, b.sstep(phi, 1.2, 2.9))
    width = b.add(0.025, b.mul(b.sstep(phi, 0.0, 2.8), 0.07))
    band = b.m("EXPONENT", b.mul(b.mul(b.m("DIVIDE", d, width), b.m("DIVIDE", d, width)), -1.0))
    clump = b.add(0.4, b.mul(b.sstep(b.noise(co, 22.0, 2, 0.5), 0.4, 0.75), 1.2))
    lum = b.mul(b.mul(b.mul(b.mul(band, along), fade), clump), b.mul(amt, 0.45))
    b.emit_add(b.ctimes((0.74, 0.72, 1.0), lum))
    return mat


def mat_milkyway():
    """Our own galaxy seen from inside: a dusty band. params mw_warp, mw_bright."""
    mat = bpy.data.materials.new("M_mw")
    b = NB(mat)
    co, x, y, z = b.xyz()
    warp = P(b, "mw_warp")
    bright = P(b, "mw_bright", 1.0)
    nw = b.noise(b.combine(b.mul(x, 1.2), b.mul(y, 1.2), 3.0), 1.5, 2, 0.5)
    v = b.add(y, b.mul(b.sub(nw, 0.5), 0.08))
    v = b.add(v, b.mul(warp, b.mul(b.m("SINE", b.add(b.mul(x, 2.6), 0.6)), 0.32)))
    v = b.add(v, b.mul(warp, b.mul(b.mul(x, x), -0.25)))
    wdt = b.add(0.055, b.mul(warp, 0.08))
    q = b.m("DIVIDE", v, wdt)
    band = b.m("EXPONENT", b.mul(b.mul(q, q), -1.0))
    core = b.add(0.35, b.mul(b.gauss(b.sub(x, 0.30), 0.22), 1.6))
    ends = b.sub(1.0, b.sstep(b.m("ABSOLUTE", x), 0.75, 1.0))
    co2 = b.combine(x, v, 1.0)
    cl = b.add(0.35, b.mul(b.sstep(b.noise(co2, 12.0, 3, 0.6), 0.4, 0.8), 1.3))
    lum = b.mul(b.mul(b.mul(band, core), cl), ends)
    dust = b.mul(b.gauss(b.sub(v, 0.008), b.add(0.022, b.mul(warp, 0.03))),
                 b.sstep(b.noise(co2, 7.0, 3, 0.6), 0.35, 0.65))
    dust = b.mul(dust, ends)
    lum = b.mul(lum, b.sub(1.0, b.mul(dust, 0.85)))
    c = b.vadd(b.ctimes((0.74, 0.72, 0.98), b.mul(lum, 0.11)),
               b.ctimes((1.0, 0.85, 0.65), b.mul(b.mul(lum, b.gauss(b.sub(x, 0.30), 0.15)), 0.12)))
    c = b.vadd(c, b.ctimes((0.85, 0.40, 0.80), b.mul(b.mul(lum, cl), b.mul(P(b, "burst"), 0.25))))
    c = b.vscale(c, bright)
    t = b.sub(1.0, b.mul(dust, b.mul(bright, 0.6)))
    b.emit_add(c, b.combine(t, t, t))
    return mat


def mat_burst():
    """Whole-sky overlay of glowing star-forming clouds. param 'burst'."""
    mat = bpy.data.materials.new("M_burst")
    b = NB(mat)
    co, x, y, z = b.xyz()
    amt = P(b, "burst")
    n = b.noise(co, 2.4, 6, 0.62)
    neb = b.sstep(n, 0.52, 0.78)
    n2 = b.noise(b.vadd(co, (3.1, 1.7, 0.0)), 5.0, 5, 0.6)
    fil = b.mul(b.sstep(n2, 0.5, 0.75), neb)
    d, c = b.voronoi(co, 90.0)
    sc = b.n("ShaderNodeSeparateColor")
    b.link(c, sc.inputs[0])
    st = b.mul(b.sub(1.0, b.sstep(d, 0.0, 0.08)), b.sstep(sc.outputs[0], 0.55, 1.0))
    st = b.mul(st, b.add(0.2, neb))
    edge = b.sub(1.0, b.sstep(b.m("MAXIMUM", b.m("ABSOLUTE", x), b.m("ABSOLUTE", y)), 0.85, 1.0))
    col = b.vadd(b.ctimes((1.0, 0.30, 0.55), b.mul(neb, 0.22)), b.ctimes((1.0, 0.55, 0.75), b.mul(fil, 0.35)))
    col = b.vadd(col, b.ctimes((0.6, 0.75, 1.0), b.mul(st, 2.2)))
    col = b.vscale(col, b.mul(amt, edge))
    b.emit_add(col)
    return mat


def mat_elliptical():
    """Milkomeda: smooth giant elliptical with faint merger shells. param 'ell'."""
    mat = bpy.data.materials.new("M_ell")
    b = NB(mat)
    co, x, y, z = b.xyz()
    amt = P(b, "ell")
    r = b.m("SQRT", b.add(b.mul(x, x), b.mul(y, y)))
    lum = b.add(b.add(b.mul(b.expneg(r, 0.025), 2.2), b.mul(b.expneg(r, 0.09), 0.55)),
                b.mul(b.expneg(r, 0.28), 0.10))
    th = b.m("ARCTAN2", y, x)
    shells = b.mul(b.pw(b.add(b.mul(b.m("COSINE", b.mul(b.add(r, b.mul(b.m("SINE", th), 0.03)), 38.0)), 0.5), 0.5), 6.0),
                   b.mul(b.sstep(r, 0.25, 0.4), b.sub(1.0, b.sstep(r, 0.6, 0.85))))
    shells = b.mul(shells, b.sstep(b.m("COSINE", b.add(th, 0.6)), 0.2, 0.9))
    lum = b.add(lum, b.mul(shells, 0.05))
    lum = b.mul(lum, b.sub(1.0, b.sstep(r, 0.75, 1.0)))
    grain = b.add(0.88, b.mul(b.noise(co, 60.0, 2, 0.5), 0.24))
    c = b.vadd(b.ctimes((1.0, 0.86, 0.66), b.mul(lum, grain)),
               b.ctimes((0.55, 0.45, 0.95), b.mul(b.mul(b.expneg(r, 0.45), 0.035), b.sub(1.0, b.sstep(r, 0.7, 1.0)))))
    c = b.vscale(c, amt)
    b.emit_add(c)
    return mat


def mat_flat(name, color=(0, 0, 0), param=None):
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    em = b.n("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    if param:
        b.link(P(b, param), em.inputs["Strength"])
    else:
        em.inputs["Strength"].default_value = 1.0
    b.link(em.outputs[0], b.out.inputs["Surface"])
    return mat


def mat_fade(name, color=(0, 0, 0), param=None):
    """Emission colour that is premultiplied: fades toward black-holdout of the scene."""
    mat = bpy.data.materials.new(name)
    b = NB(mat)
    co, x, y, z = b.xyz()
    em = b.n("ShaderNodeEmission")
    # vertical gradient: brighter at the ridge top (fog), dark lower down
    g = b.sstep(z, -1.0, 1.0)
    cv = b.ctimes(color, b.mul(g, P(b, param, 1.0)))
    b.link(cv, em.inputs["Color"])
    b.link(em.outputs[0], b.out.inputs["Surface"])
    return mat


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def plane(name, mat, parent=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def fbm1(x, seed, octaves=6):
    v, a, f = 0.0, 1.0, 1.0
    for i in range(octaves):
        v += a * (math.sin(x * f * 0.9 + seed * 1.7 + i * 2.3) * 0.6 + math.sin(x * f * 2.1 + seed * 3.1 + i) * 0.4)
        a *= 0.5
        f *= 2.03
    return v


def ridge(name, y, z_top, amp, wid, seed, mat, nseg=400, bottom=-200.0):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(nseg + 1):
        xx = -wid + 2 * wid * i / nseg
        zz = z_top + amp * fbm1(xx / wid * 3.0, seed)
        verts.append((xx, y, zz))
        verts.append((xx, y, bottom))
    for i in range(nseg):
        a, bq = 2 * i, 2 * i + 2
        faces.append((a + 1, bq + 1, bq, a))
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ridge_height(xx, z_top, amp, wid, seed):
    return z_top + amp * fbm1(xx / wid * 3.0, seed)


def tree(name, base, height, mat):
    """Bare, wind-bent tree: recursive tapered branches as low-poly cones."""
    import random
    rnd = random.Random(7)
    bm = bmesh.new()

    def branch(p, d, length, rad, depth):
        q = p + d * length
        mtx = Matrix.Translation((p + q) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=rad, radius2=rad * 0.68,
                              depth=length * 1.04, matrix=mtx)
        if depth == 0 or rad < 0.012:
            return
        nb = 2 if depth > 1 else 3
        for i in range(nb):
            ax = Vector((rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.6)))
            nd = (d + ax * rnd.uniform(0.55, 0.95) + Vector((0.18, 0, 0))).normalized()
            branch(q, nd, length * rnd.uniform(0.62, 0.8), rad * 0.66, depth - 1)
        if rnd.random() < 0.6:
            branch(q, (d + Vector((0.15, 0, 0.05))).normalized(), length * 0.75, rad * 0.7, depth - 1)

    branch(Vector(base) - Vector((0, 0, 0.5)), Vector((0.08, 0, 1)).normalized(), height * 0.36 + 0.5, height * 0.035, 6)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------
# Camera, sky rig, text
# ---------------------------------------------------------------------------
OBJ = {}
TEXTS = {}


def build_world():
    global CAM, HUD, SKY
    cd = bpy.data.cameras.new("Cam")
    cd.lens = LENS
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = SENSOR_H
    cd.clip_start = 0.05
    cd.clip_end = 5000.0
    CAM = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(CAM)
    CAM.location = (0, 0, 0)
    CAM.rotation_euler = (math.radians(90 + PITCH0), 0, 0)
    bpy.context.scene.camera = CAM
    HUD = bpy.data.objects.new("HUD", None)
    bpy.context.scene.collection.objects.link(HUD)
    HUD.parent = CAM
    HUD.location = (0, 0, -1.0)

    # sky rig: same orientation as the camera at t=0, so sky planes are placed
    # in "screen" coordinates: local (u*D*TANH*2, v*D*TANV*2, -D)
    SKY = bpy.data.objects.new("SkyRig", None)
    bpy.context.scene.collection.objects.link(SKY)
    SKY.rotation_euler = (math.radians(90 + PITCH0), 0, 0)

    st = plane("stars", mat_stars(), SKY)
    D = 2000.0
    st.location = (0, 0, -D)
    st.scale = (D * TANH * 1.25, D * TANV * 1.25, 1)
    OBJ["stars"] = st

    mw = plane("milkyway", mat_milkyway(), SKY)
    D = 1600.0
    mw.location = (-D * TANH * 0.62, D * TANV * 0.10, -D)
    mw.scale = (D * TANV * 1.8, D * TANV * 1.2, 1)
    mw.rotation_euler = (0, 0, math.radians(74))
    OBJ["mw"] = mw

    an = plane("andromeda", mat_galaxy("M_m31", "m31", (0.74, 0.76, 1.0), (1.0, 0.86, 0.66)), SKY)
    OBJ["m31"] = an
    for i in (0, 1):
        t = plane(f"tail{i}", mat_tail(f"M_tail{i}", "tail"), an)
        t.location = (0, 0, 0.001 * (i + 1))
        t.scale = (2.0, 2.0, 1)
        t.rotation_euler = (0, 0, math.pi * i + 0.4)
        OBJ[f"tail{i}"] = t


    el = plane("milkomeda", mat_elliptical(), SKY)
    OBJ["ell"] = el

    # landscape (world space, camera looks +Y)
    black = mat_flat("M_black", (0, 0, 0))
    far = ridge("ridge_far", 420.0, -38.0, 9.0, 380.0, 4.0, mat_fade("M_far", (0.20, 0.17, 0.34), "haze"))
    near_top, near_amp, near_w = -14.0, 3.2, 120.0
    near = ridge("ridge_near", 80.0, near_top, near_amp, near_w, 1.0, black)
    tx = -10.5
    tz = ridge_height(tx, near_top, near_amp, near_w, 1.0)
    tr = tree("tree", (tx, 80.0, tz), 15.0, black)
    OBJ.update(far=far, near=near, tree=tr)


def galaxy_place(u, v, D, width_deg, aspect, pa_deg, ob):
    """Place a sky plane: screen-normalised centre (u,v in -0.5..0.5 of frame), distance D,
    angular major-axis width in degrees, axis ratio, position angle."""
    ob.location = (u * 2 * D * TANH, v * 2 * D * TANV, -D)
    half = D * math.tan(math.radians(min(width_deg, 170.0)) / 2)
    ob.scale = (half, half * aspect, 1)
    ob.rotation_euler = (0, 0, math.radians(pa_deg))


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
    return mat, mx


FONTS = {}


def font(path):
    if path not in FONTS:
        try:
            FONTS[path] = bpy.data.fonts.load(path)
        except Exception:
            FONTS[path] = None
    return FONTS[path]


def sy(frac):
    """screen fraction from bottom (0..1) -> HUD y"""
    return (frac - 0.5) * 2 * TANV


def make_text(tid, body, frac_y, size, spacing=1.35, thin=False, color=TEXT_COL):
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
    ob.location = (0, sy(frac_y), 0)
    mat, mx = text_material("MT_" + tid, color)
    cu.materials.append(mat)
    TEXTS[tid] = (ob, mx)
    return ob


# (id, line1, line2, t_in, t_out, accent line2?)
BEATS = [
    ("hook", "ANDROMEDA IS ALREADY", "FALLING TOWARD US.", 0.35, 4.6, False),
    ("dist", "2.5 MILLION LIGHT-YEARS AWAY.", "CLOSING AT ~110 KM/S.", 5.1, 9.5, False),
    ("kmh", "THAT'S ABOUT 400,000 KM", "EVERY HOUR.", 10.0, 14.4, False),
    ("odds", "WILL IT HIT US?", "RECENT STUDIES: ~50% TO ~90%.", 15.0, 19.7, True),
    ("fill", "IF IT DOES,", "IT WILL FILL THE SKY.", 20.4, 24.6, False),
    ("vast", "STARS ALMOST NEVER COLLIDE.", "THE SPACE BETWEEN THEM IS TOO VAST.", 25.4, 30.6, False),
    ("gas", "BUT THE GAS DOES.", "NEW STARS IGNITE.", 31.3, 37.4, True),
    ("one", "TWO GALAXIES BECOME ONE.", "MILKOMEDA.", 38.6, 44.4, True),
    ("watch", "SOMEONE WILL BE WATCHING.", "", 45.3, 48.0, False),
    ("us", "IT WON'T BE US.", "", 48.7, 50.9, True),
]
T_CUT = 51.25


def build_texts():
    for tid, l1, l2, t0, t1, acc in BEATS:
        big = tid in ("hook", "us", "watch")
        s1 = 0.036 if big else 0.030
        if len(l1) > 24:
            s1 = 0.027
        make_text(tid + "_1", l1, 0.155 if l2 else 0.13, s1, 1.35)
        if l2:
            s2 = 0.030 if len(l2) <= 22 else 0.023
            if tid == "one":
                s2 = 0.044
            make_text(tid + "_2", l2, 0.105 if tid != "one" else 0.098, s2, 1.35 if tid != "one" else 1.9,
                      color=ACCENT if acc else TEXT_COL)
    make_text("year", "NOW", 0.925, 0.024, 1.6, color=(0.80, 0.78, 0.86))
    make_text("ifm", "IF THEY MERGE", 0.897, 0.0145, 1.9, color=(0.62, 0.58, 0.72))


def set_alpha(tid, a):
    ob, mx = TEXTS[tid]
    mx.inputs[0].default_value = a
    ob.hide_render = a <= 0.002


def year_text(y):
    if y < 1.0:
        return "NOW"
    v = int(round(y / 1e6)) * 1000000
    return "+ " + f"{v:,}" + " YEARS"


# ---------------------------------------------------------------------------
# Per-frame state
# ---------------------------------------------------------------------------
def update(frame):
    sc = bpy.context.scene
    ts = (frame - 1) / FPS

    # camera: very slow tilt up as the sky becomes the subject
    tilt = PITCH0 + 2.2 * ease(ts / 40.0) - 0.6 * ramp(ts, 44.0, 52.0)
    CAM.rotation_euler = (math.radians(90 + tilt), 0, 0)
    CAM.location = (0, 0.6 * ts / 52.0, 0)

    # --- Andromeda growth ------------------------------------------------
    # angular width: ~3.2 deg today; ~a big oval at 2 Gyr; fills the sky at 3.75 Gyr
    g1 = ramp(ts, 8.0, 20.0)
    g2 = ramp(ts, 18.5, 25.5)
    g3 = ramp(ts, 25.0, 31.0)
    width = 3.4 * (1 - g1) + 22.0 * g1
    width = lerp(width, 120.0, g2)
    width = lerp(width, 150.0, g3)
    u = lerp(0.16, 0.10, g1)
    u = lerp(u, -0.02, g2)
    v = lerp(0.22, 0.20, g1)
    v = lerp(v, 0.12, g2)
    aspect = lerp(0.32, 0.40, g1)
    aspect = lerp(aspect, 0.55, g2)
    pa = lerp(36.0, 30.0, g1)
    pa = lerp(pa, 22.0, g2) + 18.0 * g3
    galaxy_place(u, v, 1400.0, width, aspect, pa, OBJ["m31"])
    set_param("m31_aspect", aspect)

    warp = ramp(ts, 25.0, 33.0) * 1.0 + 0.6 * ramp(ts, 31.0, 38.0)
    set_param("m31_warp", warp)
    set_param("tail", ramp(ts, 25.5, 31.5) * (1.0 - 0.75 * ramp(ts, 38.0, 44.0)))
    burst = ramp(ts, 30.5, 34.5) * (1.0 - ramp(ts, 38.5, 43.0))
    set_param("m31_burst", burst)
    set_param("burst", burst * 1.0)
    # brightness: a faint smudge now (it is barely naked-eye), brighter as it nears
    br = lerp(1.6, 0.85, g1)
    br = lerp(br, 0.55, g2)
    br *= (1.0 - 0.92 * ramp(ts, 37.5, 43.5))
    br *= ramp(ts, -0.2, 1.6)
    set_param("m31_bright", br)

    # --- our own Milky Way band -----------------------------------------
    set_param("mw_warp", ramp(ts, 25.0, 36.0))
    mwb = 1.0 * (1.0 - 0.3 * ramp(ts, 22.0, 26.0)) * (1.0 - 0.95 * ramp(ts, 37.5, 43.5))
    set_param("mw_bright", mwb * ramp(ts, -0.2, 1.4))

    # --- Milkomeda --------------------------------------------------------
    e = ramp(ts, 37.0, 44.0)
    set_param("ell", e)
    galaxy_place(0.0, 0.10, 1300.0, lerp(70.0, 95.0, e), 0.70, 14.0, OBJ["ell"])

    # --- sky ----------------------------------------------------------------
    sky = 0.15 * ramp(ts, 12.0, 25.0) + 0.5 * ramp(ts, 25.0, 33.0) - 0.2 * ramp(ts, 38.0, 46.0)
    set_param("skyglow", sky)
    set_param("stars", ramp(ts, -0.2, 1.2))
    # cull layers that contribute nothing (render time)
    OBJ["ell"].hide_render = e <= 0.0
    OBJ["tail0"].hide_render = OBJ["tail1"].hide_render = ts < 25.5
    OBJ["m31"].hide_render = br <= 0.004
    OBJ["mw"].hide_render = mwb <= 0.004
    set_param("haze", 0.35 + 1.4 * sky)

    # global fade at the very end (hard cut to black at T_CUT)
    fade = 1.0 - 0.55 * ramp(ts, 45.0, 51.0)
    if ts >= T_CUT:
        fade = 1e-4
    sc.view_settings.exposure = math.log2(max(fade, 1e-4)) + 0.25

    # --- texts ------------------------------------------------------------
    for tid, l1, l2, t0, t1, acc in BEATS:
        a1 = window(ts, t0, t1, 0.55, 0.45)
        if ts >= T_CUT:
            a1 = 0.0
        set_alpha(tid + "_1", a1)
        if l2:
            set_alpha(tid + "_2", window(ts, t0 + 0.45, t1, 0.6, 0.45) if ts < T_CUT else 0.0)
    yv = years_at(ts)
    ob, _ = TEXTS["year"]
    ob.data.body = year_text(yv)
    set_alpha("year", window(ts, 0.9, 50.9, 0.8, 0.35) * 0.9)
    set_alpha("ifm", window(ts, 20.4, 50.9, 1.0, 0.35))


# ---------------------------------------------------------------------------
def main():
    sc = reset_scene()
    build_world()
    build_texts()
    out = arg("--out", CONFIG["output"])
    os.makedirs(out, exist_ok=True)
    print(f"[sky-thats-coming] {CONFIG['duration']}s, {N_FRAMES} frames -> {out}")
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
