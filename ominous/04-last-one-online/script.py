"""
OMINOUS #4 -- LAST ONE ONLINE
Earth's night side from low orbit. Procedural city lights (clustered along
coastlines via noise masks), airglow + atmospheric limb, aurora on the limb.
The lights go out region by region. One remains, blinking. Then it goes too.

Fully procedural, no downloads. Everything is emission-shaded (no lamps) so it
renders cheaply on CPU Cycles.

Run headless:
    blender -b -P script.py -- --render
    blender -b -P script.py -- --still 300          # single test frame
    blender -b -P script.py -- --render --frames 0 100 --out /tmp/frames
With the bpy Python module:
    python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
"""

# =============================================================================
# CONFIG
# =============================================================================
FPS          = 24
DURATION     = 24.0                      # seconds
RES_X, RES_Y = 1080, 1920                # nominal (vertical 9:16)
SCALE        = 0.5334                    # 1080x1920 * 0.5334 -> 576x1024
ENGINE       = "CYCLES"                  # CPU Cycles, emission only
SAMPLES      = 6
DENOISE      = True
BAKE_FIELDS  = True                      # bake static globe noise fields to a texture (big speed-up)
BAKE_TEXEL   = 0.0010                    # world units per texel (Earth radius = 10)
BAKE_SAMPLES = 3
OUTPUT       = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/04/frames"
FONT_PATHS   = ["/usr/share/fonts/opentype/inter/Inter-Light.otf",
                "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

# Accent: sodium amber
AMBER        = (1.00, 0.50, 0.14)
AMBER_HOT    = (1.00, 0.78, 0.48)
OFF_WHITE    = (0.92, 0.90, 0.86)

# Story timing (seconds)
WAVE_START   = 2.2       # first regions fail
WAVE_END     = 16.8      # everything but one light is dark
BLINK_START  = 16.2      # last light starts blinking
LAST_OUT     = 21.6      # last light dies
TEXTS = [  # (text, start, end, y-position in camera space)
    ("EVERY LIGHT\nIS SOMEONE", 0.25, 4.6, -0.24),
    ("STILL AWAKE",             5.2, 8.9, -0.24),
    ("ONE BY ONE",              10.0, 13.6, -0.24),
    ("LAST ONE ONLINE",         17.4, 21.4, -0.30),
]

# =============================================================================
import bpy, math, sys, os, time
from mathutils import Vector, Matrix

R_EARTH = 10.0
ALT     = 0.65            # ~410 km at this scale (ISS-like)
PITCH   = 31.0            # degrees below horizontal
FOV_V   = 56.0            # vertical field of view (deg)
ROLL    = -5.0            # slight dutch angle on the horizon

def argv_after_dashes():
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []

ARGS = argv_after_dashes()

def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)

# ----------------------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 0
    sc.frame_end = int(round(DURATION * FPS)) - 1
    return sc

def setup_render(sc, scale=SCALE):
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = SAMPLES
    try:
        sc.cycles.use_adaptive_sampling = False
    except Exception:
        pass
    sc.cycles.use_denoising = DENOISE
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    for k, v in (("max_bounces", 0), ("diffuse_bounces", 0), ("glossy_bounces", 0),
                 ("transmission_bounces", 0), ("volume_bounces", 0),
                 ("transparent_max_bounces", 12)):
        try:
            setattr(sc.cycles, k, v)
        except Exception:
            pass
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.resolution_x = int(round(RES_X * scale / 2) * 2)
    sc.render.resolution_y = int(round(RES_Y * scale / 2) * 2)
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    # colour management: AgX gives a filmic highlight roll-off for hot city cores
    vs = sc.view_settings
    for vt in ("AgX", "Filmic", "Standard"):
        try:
            vs.view_transform = vt
            break
        except Exception:
            continue
    try:
        vs.look = 'None'
    except Exception:
        pass
    vs.exposure = 0.0
    vs.gamma = 1.0
    ims = sc.render.image_settings
    if hasattr(ims, "media_type"):          # Blender 5.x
        try:
            ims.media_type = 'IMAGE'
        except Exception:
            pass
    ims.file_format = 'PNG'
    ims.color_mode = 'RGB'
    ims.color_depth = '8'

# ----------------------------------------------------------------------------- node helpers
class NB:
    """Tiny node-graph builder."""
    def __init__(self, nt):
        self.nt = nt
        self.x = 0

    def node(self, typ, **props):
        n = self.nt.nodes.new(typ)
        n.location = (self.x, 0)
        self.x += 40
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, out, inp):
        self.nt.links.new(out, inp)

    def feed(self, sock, val):
        if hasattr(val, "is_output"):
            self.link(val, sock)
        else:
            if isinstance(val, (tuple, list)):
                try:
                    n = len(sock.default_value)
                except TypeError:
                    n = len(val)
                val = tuple(val) + (1.0,) * (n - len(val))
            sock.default_value = val

    def math(self, op, a, b=0.0, c=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.feed(n.inputs[0], a)
        self.feed(n.inputs[1], b)
        if c is not None:
            self.feed(n.inputs[2], c)
        return n.outputs[0]

    def vmath(self, op, a, b=None, s=None):
        n = self.node('ShaderNodeVectorMath', operation=op)
        self.feed(n.inputs[0], a)
        if b is not None:
            self.feed(n.inputs[1], b)
        if s is not None:
            # 'Scale' input for SCALE op
            sock = n.inputs.get("Scale") or n.inputs[3]
            self.feed(sock, s)
        out = n.outputs.get("Vector") if op not in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs.get("Value")
        return out

    def smooth(self, x, lo, hi):
        n = self.node('ShaderNodeMapRange', data_type='FLOAT', interpolation_type='SMOOTHSTEP')
        self.feed(n.inputs["Value"], x)
        n.inputs["From Min"].default_value = lo
        n.inputs["From Max"].default_value = hi
        n.inputs["To Min"].default_value = 0.0
        n.inputs["To Max"].default_value = 1.0
        return n.outputs["Result"]

    def remap(self, x, a, b, c, d, clamp=True):
        n = self.node('ShaderNodeMapRange', data_type='FLOAT', interpolation_type='LINEAR', clamp=clamp)
        self.feed(n.inputs["Value"], x)
        n.inputs["From Min"].default_value = a
        n.inputs["From Max"].default_value = b
        n.inputs["To Min"].default_value = c
        n.inputs["To Max"].default_value = d
        return n.outputs["Result"]

    def noise(self, vec, scale, detail=2.0, rough=0.5, w=None, dist=0.0):
        n = self.node('ShaderNodeTexNoise')
        n.noise_dimensions = '4D' if w is not None else '3D'
        self.feed(n.inputs["Vector"], vec)
        if w is not None:
            self.feed(n.inputs["W"], w)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        if "Distortion" in n.inputs:
            n.inputs["Distortion"].default_value = dist
        try:
            n.normalize = True
        except Exception:
            pass
        return n.outputs["Fac"]

    def noise_col(self, vec, scale, detail=1.0):
        n = self.node('ShaderNodeTexNoise')
        self.feed(n.inputs["Vector"], vec)
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        return n.outputs["Color"]

    def voronoi(self, vec, scale, rand=1.0):
        n = self.node('ShaderNodeTexVoronoi', voronoi_dimensions='3D', feature='F1', distance='EUCLIDEAN')
        self.feed(n.inputs["Vector"], vec)
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rand
        return n.outputs["Distance"], n.outputs["Color"]

    def sep_r(self, col):
        n = self.node('ShaderNodeSeparateColor') if hasattr(bpy.types, "ShaderNodeSeparateColor") else self.node('ShaderNodeSeparateRGB')
        self.link(col, n.inputs[0])
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def value(self, v, name):
        n = self.node('ShaderNodeValue')
        n.name = name
        n.label = name
        n.outputs[0].default_value = v
        return n.outputs[0]

    def col(self, rgb):
        # vector constant via Combine XYZ
        n = self.node('ShaderNodeCombineXYZ')
        for i in range(3):
            n.inputs[i].default_value = rgb[i]
        return n.outputs[0]

    def lerp_col(self, a, b, f):
        """a + (b-a)*f for colour vectors (a,b tuples or sockets)."""
        av = a if hasattr(a, "is_output") else self.col(a)
        bv = b if hasattr(b, "is_output") else self.col(b)
        d = self.vmath('SUBTRACT', bv, av)
        return self.vmath('ADD', av, self.vmath('SCALE', d, s=f))

    def emission(self, colvec, strength):
        n = self.node('ShaderNodeEmission')
        self.feed(n.inputs["Color"], colvec)
        self.feed(n.inputs["Strength"], strength)
        return n.outputs[0]

    def add_transparent(self, shader):
        t = self.node('ShaderNodeBsdfTransparent')
        a = self.node('ShaderNodeAddShader')
        self.link(t.outputs[0], a.inputs[0])
        self.link(shader, a.inputs[1])
        return a.outputs[0]

def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    out = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
    return m, NB(m.node_tree), out

# ----------------------------------------------------------------------------- Earth
def earth_fields(b, p):
    """Static fields of the night globe at unit position p.
    Returns (lights, off_time, cloud): light intensity (before blackout),
    the moment (0..1.2 on the WaveT scale) this spot goes dark, moonlit cloud cover."""
    # --- continents: low-freq fBm, thresholded ------------------------------
    cont = b.noise(p, 3.2, detail=6.0, rough=0.62, dist=0.25)
    land = b.smooth(cont, 0.505, 0.525)
    # coastal band: 1 at the coastline, falls off inland
    coast_d = b.math('ABSOLUTE', b.math('SUBTRACT', cont, 0.515))
    coast = b.math('SUBTRACT', 1.0, b.smooth(coast_d, 0.0, 0.05))
    # regional population (deserts / dense belts)
    region_pop = b.smooth(b.noise(p, 5.5, detail=3.0, rough=0.5), 0.36, 0.66)
    density = b.math('MULTIPLY', land,
              b.math('MULTIPLY', region_pop,
              b.math('ADD', 0.22, b.math('MULTIPLY', coast, 0.95))))
    # rivers / corridors of towns inland
    corridor = b.math('SUBTRACT', 1.0, b.smooth(
        b.math('ABSOLUTE', b.math('SUBTRACT', b.noise(p, 14.0, detail=3.0, rough=0.5), 0.5)), 0.0, 0.035))
    density = b.math('ADD', density, b.math('MULTIPLY', corridor, b.math('MULTIPLY', land, b.math('MULTIPLY', region_pop, 0.35))))

    density = b.math('MULTIPLY', density, 1.6)

    # --- blackout schedule ----------------------------------------------------
    # gradient: far horizon (+Y) goes first, comes toward camera, slight diagonal
    g = b.vmath('DOT_PRODUCT', p, (0.30, -0.95, 0.0))
    g = b.remap(g, -0.42, 0.02, 0.0, 1.0)
    pd = b.vmath('ADD', p, b.vmath('SCALE', b.vmath('SUBTRACT', b.noise_col(p, 30.0), (0.5, 0.5, 0.5)), s=0.035))
    reg_d, reg_c = b.voronoi(pd, 22.0)
    reg_r, _, _ = b.sep_r(reg_c)
    off_time = b.math('ADD', b.math('MULTIPLY', g, 0.62), b.math('MULTIPLY', reg_r, 0.36))
    # city-scale stagger
    pc = b.vmath('ADD', p, b.vmath('SCALE', b.vmath('SUBTRACT', b.noise_col(p, 160.0, detail=3.0), (0.5, 0.5, 0.5)), s=0.006))
    cty_d, cty_c = b.voronoi(pc, 70.0, rand=0.9)
    cr, cg, cb = b.sep_r(cty_c)
    off_time = b.math('ADD', off_time, b.math('MULTIPLY', cb, 0.04))

    # --- cities: voronoi cores, chosen by density probability -----------------
    city_on = b.smooth(b.math('SUBTRACT', density, cr), 0.0, 0.08)
    radius = b.math('ADD', 0.05, b.math('MULTIPLY', b.math('POWER', cg, 3.0), 0.17))
    core = b.math('SUBTRACT', 1.0, b.math('DIVIDE', cty_d, radius), clamp=True)
    core = b.math('POWER', core, 1.6)
    halo = b.math('SUBTRACT', 1.0, b.math('DIVIDE', cty_d, b.math('MULTIPLY', radius, 1.9)), clamp=True)
    city_size = b.math('ADD', 0.35, b.math('MULTIPLY', cg, 1.2))
    # street texture inside metro areas
    streets = b.noise(p, 2200.0, detail=2.0, rough=0.6)
    streets = b.math('ADD', 0.25, b.math('MULTIPLY', b.smooth(streets, 0.46, 0.70), 0.9))
    metro = b.math('MULTIPLY', city_on, b.math('ADD', b.math('MULTIPLY', core, 3.2),
                    b.math('MULTIPLY', b.math('POWER', halo, 2.2), b.math('MULTIPLY', streets, 1.2))))
    metro = b.math('MULTIPLY', metro, city_size)

    # --- towns: finer voronoi -------------------------------------------------
    twn_d, twn_c = b.voronoi(p, 240.0, rand=1.0)
    tr, tg, _ = b.sep_r(twn_c)
    town_on = b.smooth(b.math('SUBTRACT', b.math('MULTIPLY', density, 0.85), tr), 0.0, 0.05)
    town = b.math('SUBTRACT', 1.0, b.math('DIVIDE', twn_d, b.math('ADD', 0.08, b.math('MULTIPLY', tg, 0.18))), clamp=True)
    town = b.math('MULTIPLY', b.math('POWER', town, 2.0), b.math('MULTIPLY', town_on, 0.9))

    # --- faint rural speckle -----------------------------------------------
    speck = b.smooth(b.noise(p, 1600.0, detail=1.0), 0.70, 0.78)
    speck = b.math('MULTIPLY', speck, b.math('MULTIPLY', density, 0.35))

    lights = b.math('ADD', metro, b.math('ADD', town, speck))

    # --- clouds (moonlit, faint) dim & diffuse the lights -----------------------
    cloud = b.noise(p, 9.0, detail=4.0, rough=0.6, dist=0.6)
    cloud = b.smooth(cloud, 0.52, 0.72)
    lights = b.math('MULTIPLY', lights, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', cloud, 0.75)))
    return lights, off_time, cloud


def bake_plane_p(b):
    """Unit globe position for a flat bake plane lying at z=0 in Earth object space."""
    tc = b.node('ShaderNodeTexCoord')
    sp = b.node('ShaderNodeSeparateXYZ')
    b.link(tc.outputs["Object"], sp.inputs[0])
    x, y = sp.outputs[0], sp.outputs[1]
    r2 = b.math('ADD', b.math('MULTIPLY', x, x), b.math('MULTIPLY', y, y))
    z = b.math('SQRT', b.math('MAXIMUM', b.math('SUBTRACT', R_EARTH * R_EARTH, r2), 0.0))
    cv = b.node('ShaderNodeCombineXYZ')
    b.link(x, cv.inputs[0]); b.link(y, cv.inputs[1]); b.link(z, cv.inputs[2])
    return b.vmath('NORMALIZE', cv.outputs[0])


def build_bake_material(img):
    m, b, out = new_material("EarthBake")
    p = bake_plane_p(b)
    lights, off_time, cloud = earth_fields(b, p)
    cv = b.node('ShaderNodeCombineXYZ')
    b.link(lights, cv.inputs[0]); b.link(off_time, cv.inputs[1]); b.link(cloud, cv.inputs[2])
    b.link(b.emission(cv.outputs[0], 1.0), out.inputs["Surface"])
    tn = b.node('ShaderNodeTexImage')
    tn.image = img
    m.node_tree.nodes.active = tn
    return m


def build_earth_material(img=None, bounds=None):
    """Render-time globe shader. With a baked field image the expensive noise work is a
    single texture lookup; without one it evaluates the procedural fields directly."""
    m, b, out = new_material("EarthNight")
    tc = b.node('ShaderNodeTexCoord')
    p = b.vmath('NORMALIZE', tc.outputs["Object"])           # unit position on globe
    t_val = b.value(0.0, "WaveT")       # blackout threshold, animated
    time_v = b.value(0.0, "Time")       # seconds, for flicker

    if img is not None:
        x0, x1, y0, y1 = bounds
        sp = b.node('ShaderNodeSeparateXYZ')
        b.link(tc.outputs["Object"], sp.inputs[0])
        u = b.remap(sp.outputs[0], x0, x1, 0.0, 1.0, clamp=False)
        v = b.remap(sp.outputs[1], y0, y1, 0.0, 1.0, clamp=False)
        uv = b.node('ShaderNodeCombineXYZ')
        b.link(u, uv.inputs[0]); b.link(v, uv.inputs[1])
        tn = b.node('ShaderNodeTexImage', interpolation='Linear', extension='EXTEND')
        tn.image = img
        b.link(uv.outputs[0], tn.inputs["Vector"])
        lights, off_time, cloud = b.sep_r(tn.outputs["Color"])
    else:
        lights, off_time, cloud = earth_fields(b, p)

    alive = b.smooth(b.math('SUBTRACT', off_time, t_val), -0.004, 0.004)
    # flicker just before dying
    near = b.math('SUBTRACT', 1.0, b.smooth(b.math('SUBTRACT', off_time, t_val), 0.0, 0.045))
    flick_n = b.noise(b.vmath('SCALE', p, s=60.0), 1.0, detail=0.0, w=b.math('MULTIPLY', time_v, 9.0))
    flick = b.smooth(flick_n, 0.42, 0.50)
    alive = b.math('MULTIPLY', alive, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', near, b.math('SUBTRACT', 1.0, flick))))
    lights = b.math('MULTIPLY', lights, alive)
    # colour: amber, hotter (whiter) in dense cores
    hot = b.smooth(lights, 0.6, 2.2)
    lcol = b.lerp_col(AMBER, AMBER_HOT, hot)
    lstr = b.math('MULTIPLY', lights, 2.0)
    lights_rgb = b.vmath('SCALE', lcol, s=lstr)

    # --- base surface: ocean near-black, land faint, clouds moonlit -----------
    base = b.lerp_col((0.0018, 0.0024, 0.0042), (0.020, 0.024, 0.032), b.math('MULTIPLY', cloud, 0.9))
    # limb haze: deep blue toward the horizon
    lw = b.node('ShaderNodeLayerWeight')
    lw.inputs["Blend"].default_value = 0.5
    facing = lw.outputs["Facing"]
    haze = b.math('POWER', facing, 9.0)
    base = b.lerp_col(base, (0.006, 0.016, 0.045), b.math('MULTIPLY', haze, 0.8))
    rgb = b.vmath('ADD', base, lights_rgb)
    # extinction of lights at grazing angles
    rgb = b.vmath('SCALE', rgb, s=b.math('SUBTRACT', 1.0, b.math('MULTIPLY', haze, 0.6)))
    em = b.emission(rgb, 1.0)
    b.link(em, out.inputs["Surface"])
    return m

def build_atmo_material(name, color, power, strength):
    m, b, out = new_material(name)
    lw = b.node('ShaderNodeLayerWeight')
    lw.inputs["Blend"].default_value = 0.5
    f = b.math('POWER', lw.outputs["Facing"], power)
    em = b.emission(color, b.math('MULTIPLY', f, strength))
    b.link(b.add_transparent(em), out.inputs["Surface"])
    m.blend_method = 'BLEND' if hasattr(m, "blend_method") else None
    return m

def build_aurora_material():
    m, b, out = new_material("Aurora")
    tc = b.node('ShaderNodeTexCoord')
    sep = b.node('ShaderNodeSeparateXYZ')
    b.link(tc.outputs["UV"], sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]
    time_v = b.value(0.0, "Time")
    w = b.math('MULTIPLY', time_v, 0.10)
    # vertical rays: stretched noise along u
    rv = b.node('ShaderNodeCombineXYZ')
    b.link(b.math('MULTIPLY', u, 1.0), rv.inputs[0])
    b.link(b.math('MULTIPLY', v, 0.02), rv.inputs[1])
    rays = b.noise(rv.outputs[0], 55.0, detail=2.0, rough=0.55, w=w)
    rays = b.smooth(rays, 0.35, 0.75)
    # large-scale intensity drift along the curtain
    big = b.noise(rv.outputs[0], 3.0, detail=1.0, w=b.math('MULTIPLY', w, 0.6))
    big = b.smooth(big, 0.30, 0.70)
    # vertical profile: sharp lower edge, long soft fade upward
    prof = b.math('MULTIPLY', b.smooth(v, 0.0, 0.07),
                  b.math('POWER', b.math('SUBTRACT', 1.0, v, clamp=True), 1.5))
    fu = b.node('ShaderNodeUVMap')
    fu.uv_map = "Fade"
    fsep = b.node('ShaderNodeSeparateXYZ')
    b.link(fu.outputs[0], fsep.inputs[0])
    fx = fsep.outputs[0]
    taper = b.math('MULTIPLY', b.smooth(fx, 0.0, 0.25), b.math('SUBTRACT', 1.0, b.smooth(fx, 0.70, 1.0)))
    inten = b.math('MULTIPLY', prof, b.math('MULTIPLY', b.math('ADD', 0.25, rays), big))
    inten = b.math('MULTIPLY', inten, taper)
    low = (0.30, 0.85, 0.58)
    high = (0.50, 0.28, 0.48)
    col = b.lerp_col(low, high, b.smooth(v, 0.25, 0.85))
    em = b.emission(col, b.math('MULTIPLY', inten, 2.0))
    b.link(b.add_transparent(em), out.inputs["Surface"])
    return m

def build_world(sc):
    w = bpy.data.worlds.new("Space")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    b = NB(nt)
    out = b.node('ShaderNodeOutputWorld')
    tc = b.node('ShaderNodeTexCoord')
    d, c = b.voronoi(tc.outputs["Generated"], 260.0)
    r, g, _ = b.sep_r(c)
    star = b.math('SUBTRACT', 1.0, b.math('DIVIDE', d, 0.09), clamp=True)
    mag = b.math('POWER', r, 9.0)
    s = b.math('MULTIPLY', b.math('POWER', star, 2.0), b.math('MULTIPLY', mag, 3.5))
    col = b.lerp_col((0.75, 0.82, 1.0), (1.0, 0.88, 0.75), g)
    em = b.node('ShaderNodeBackground')
    b.link(b.vmath('ADD', b.vmath('SCALE', col, s=s), b.col((0.0004, 0.0005, 0.0009))), em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    b.link(em.outputs[0], out.inputs["Surface"])
    try:
        w.cycles_visibility.diffuse = False
    except Exception:
        pass

# ----------------------------------------------------------------------------- geometry
def uv_sphere(name, radius, segs=256, rings=128, mat=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=radius)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    if mat:
        o.data.materials.append(mat)
    return o

def aurora_ribbon(name, center, radius_deg, a0, a1, h0, height, mat, seed=0.0, n=700, fade=True):
    c = Vector(center).normalized()
    e1 = c.cross(Vector((0, 0, 1)))
    if e1.length < 1e-4:
        e1 = c.cross(Vector((1, 0, 0)))
    e1.normalize()
    e2 = c.cross(e1).normalized()
    verts, faces, uvs = [], [], []
    acc = 0.0
    prev = None
    r0 = math.radians(radius_deg)
    for i in range(n + 1):
        t = i / n
        a = a0 + (a1 - a0) * t
        rr = r0 * (1 + 0.07 * math.sin(3 * a + seed) + 0.035 * math.sin(9 * a + 2 * seed)
                   + 0.012 * math.sin(23 * a + seed))
        d = (c * math.cos(rr) + (e1 * math.cos(a) + e2 * math.sin(a)) * math.sin(rr)).normalized()
        hh = height * (0.65 + 0.35 * math.sin(4 * a + seed * 1.7) ** 2)
        bot = d * (R_EARTH + h0)
        top = d * (R_EARTH + h0 + hh)
        if prev is not None:
            acc += (bot - prev).length
        prev = bot
        verts += [bot, top]
        uvs.append(acc)
    for i in range(n):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uvl.data[li].uv = (uvs[vi // 2] + seed * 3.0, float(vi % 2))
    # second UV: normalised position along the arc, for tapering the ends
    uvf = me.uv_layers.new(name="Fade")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uvf.data[li].uv = ((vi // 2) / n, float(vi % 2))
    me.uv_layers.active = uvl
    try:
        uvl.active_render = True
    except Exception:
        pass
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o

def text_obj(name, body, font, size, y, cam, dist=1.0):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    if font:
        cu.font = font
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.space_character = 1.55
    cu.space_line = 1.6
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    o.parent = cam
    o.location = (0.0, y * dist, -dist)
    cu.size = size * dist
    m, b, out = new_material(name + "_mat")
    op = b.value(0.0, "Opacity")
    em = b.emission(OFF_WHITE, 1.15)
    tr = b.node('ShaderNodeBsdfTransparent')
    mix = b.node('ShaderNodeMixShader')
    b.link(op, mix.inputs[0])
    b.link(tr.outputs[0], mix.inputs[1])
    b.link(em, mix.inputs[2])
    b.link(mix.outputs[0], out.inputs["Surface"])
    o.data.materials.append(m)
    return o, m

# ----------------------------------------------------------------------------- build
STATE = {}

def camera_matrix(t):
    """Static-ish orbit camera; slow tilt-up drift."""
    pitch = math.radians(PITCH - 1.2 * smoothstep(0, DURATION, t))
    base = Matrix.Rotation(math.pi / 2 - pitch, 4, 'X')
    roll = Matrix.Rotation(math.radians(ROLL), 4, 'Z')
    m = base @ roll
    m.translation = Vector((0.0, 0.0, R_EARTH + ALT))
    return m

def earth_rot(t):
    # ground drifts toward the camera like an orbital pass (~ISS ground speed, exaggerated)
    return -math.radians(2.6) * (t / DURATION)

def wave_T(t):
    q = STATE.get("quantiles")
    if q:
        # calibrated: fraction of (light-weighted) city light that is already dark
        f = smoothstep(WAVE_START, WAVE_END, t) ** 1.25
        if f <= 0:
            return q[0] - 0.01
        if f >= 1:
            return q[-1] + 0.02
        k = f * (len(q) - 1)
        i = int(k)
        return q[i] + (q[min(i + 1, len(q) - 1)] - q[i]) * (k - i)
    x = smoothstep(WAVE_START, WAVE_END, t)
    x = 0.55 * x + 0.45 * (x ** 1.6)       # slow start, faster middle
    return -0.02 + 1.20 * x

def visible_bounds(margin=0.06):
    """Bounding box (Earth object-space x/y) of all globe points the camera sees during the shot."""
    tv = math.tan(math.radians(FOV_V) / 2)
    th = tv * RES_X / RES_Y
    xs, ys = [], []
    for t in [DURATION * k / 8 for k in range(9)]:
        cm = camera_matrix(t)
        o = cm.translation
        inv = Matrix.Rotation(-earth_rot(t), 4, 'X')
        for i in range(41):
            for j in range(41):
                d = (cm.to_3x3() @ Vector(((i / 20 - 1) * th, (j / 20 - 1) * tv, -1.0))).normalized()
                bq = o.dot(d)
                disc = bq * bq - (o.dot(o) - R_EARTH ** 2)
                if disc < 0:
                    continue
                hit = inv @ (o + d * (-bq - math.sqrt(disc)))
                xs.append(hit.x); ys.append(hit.y)
    # rays just grazing the limb: include the horizon circle
    rh = R_EARTH * math.sqrt(1 - (R_EARTH / (R_EARTH + ALT)) ** 2)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    y1 = max(y1, rh * 1.0)
    w, h = x1 - x0, y1 - y0
    return (x0 - w * margin, x1 + w * margin, y0 - h * margin, y1 + h * margin)


def off_time_quantiles(img, n=201):
    """Light-weighted quantiles of the blackout time, so the wave darkens the
    visible lights at a controlled, even pace."""
    import numpy as np
    W, H = img.size
    px = np.empty(W * H * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    w, ot = px[:, 0], px[:, 1]
    sel = w > 0.02
    w, ot = w[sel], ot[sel]
    order = np.argsort(ot)
    cw = np.cumsum(w[order]); cw /= cw[-1]
    qs = np.interp(np.linspace(0, 1, n), cw, ot[order])
    return [float(v) for v in qs]


def bake_fields(sc, cache_dir):
    bounds = visible_bounds()
    x0, x1, y0, y1 = bounds
    W = min(6000, int((x1 - x0) / BAKE_TEXEL))
    H = min(6000, int((y1 - y0) / BAKE_TEXEL))
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "earth_fields_%dx%d_%d.exr" % (W, H, int(1000 * (x0 + y1))))
    if os.path.exists(path):
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = 'Non-Color'
        print("loaded baked fields", path, flush=True)
        return img, bounds
    t0 = time.time()
    img = bpy.data.images.new("EarthFields", W, H, float_buffer=True, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    me = bpy.data.meshes.new("BakePlane")
    me.from_pydata([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name="UVMap")
    for li, uv in zip(range(4), [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uvl.data[li].uv = uv
    ob = bpy.data.objects.new("BakePlane", me)
    sc.collection.objects.link(ob)
    mat = build_bake_material(img)
    me.materials.append(mat)
    for o in sc.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    old = sc.cycles.samples
    sc.cycles.samples = BAKE_SAMPLES
    sc.render.bake.margin = 0
    bpy.ops.object.bake(type='EMIT')
    sc.cycles.samples = old
    img.filepath_raw = path
    img.file_format = 'OPEN_EXR'
    img.save()
    bpy.data.objects.remove(ob)
    bpy.data.materials.remove(mat)
    print("baked fields %dx%d in %.1fs -> %s" % (W, H, time.time() - t0, path), flush=True)
    return img, bounds


def build():
    sc = reset_scene()
    setup_render(sc)
    build_world(sc)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.sensor_fit = 'VERTICAL'
    cam_data.angle_y = math.radians(FOV_V)
    cam_data.clip_start = 0.01
    cam_data.clip_end = 200
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.matrix_world = camera_matrix(0.0)

    if BAKE_FIELDS and "--no-bake" not in ARGS:
        img, bounds = bake_fields(sc, os.path.join(os.path.dirname(OUTPUT.rstrip("/")), "bake"))
        earth_mat = build_earth_material(img, bounds)
        STATE["quantiles"] = off_time_quantiles(img)
    else:
        earth_mat = build_earth_material()
    earth = uv_sphere("Earth", R_EARTH, 384, 192, earth_mat)
    atm = uv_sphere("Atmosphere", R_EARTH + 0.10, 256, 128,
                    build_atmo_material("AtmoGlow", (0.05, 0.14, 0.50), 14.0, 0.45))
    air = uv_sphere("Airglow", R_EARTH + 0.065, 256, 128,
                    build_atmo_material("Airglow", (0.30, 0.55, 0.22), 90.0, 0.55))
    for o in (atm, air):
        try:
            o.visible_shadow = False
        except Exception:
            pass

    aur_mat = build_aurora_material()
    # auroral oval sitting on the far limb, left of centre
    ctr = Vector((-0.06, math.sin(math.radians(40.0)), math.cos(math.radians(40.0))))
    auroras = [
        aurora_ribbon("Aurora1", ctr, 11.0, math.radians(-150), math.radians(-20), 0.10, 0.62, aur_mat, 0.0, fade=True),
    ]
    for a in auroras:
        a.parent = earth

    # the last light: tiny emitter on the surface, parented to Earth
    ll_mat, b, out = new_material("LastLight")
    ll_str = b.value(0.0, "Strength")
    em = b.emission((1.0, 0.62, 0.26), ll_str)
    b.link(em, out.inputs["Surface"])
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.0026)
    ll = bpy.context.active_object
    ll.name = "LastLight"
    ll.data.materials.append(ll_mat)
    # place it where the view ray through screen point (0.5, 0.33) hits the globe at t=LAST_OUT
    cm = camera_matrix(LAST_OUT)
    ny = (0.33 - 0.5) * 2 * math.tan(math.radians(FOV_V) / 2)
    nx = 0.04 * 2 * math.tan(math.radians(FOV_V) / 2)
    dirv = (cm.to_3x3() @ Vector((nx, ny, -1.0))).normalized()
    o = cm.translation
    bq = o.dot(dirv)
    cq = o.dot(o) - R_EARTH ** 2
    tt = -bq - math.sqrt(bq * bq - cq)
    hit = o + dirv * tt
    hit_local = Matrix.Rotation(-earth_rot(LAST_OUT), 4, 'X') @ hit
    ll.location = hit_local * (1.0 + 0.0004)
    ll.parent = earth

    # soft camera-facing glow around the last light (only used once it is alone)
    g_mat, b, out = new_material("LastGlow")
    gstr = b.value(0.0, "Strength")
    tcg = b.node('ShaderNodeTexCoord')
    d = b.vmath('DISTANCE', tcg.outputs["UV"], (0.5, 0.5, 0.0))
    fall = b.math('POWER', b.math('SUBTRACT', 1.0, b.smooth(d, 0.0, 0.5)), 7.0)
    em = b.emission((1.0, 0.55, 0.18), b.math('MULTIPLY', fall, gstr))
    b.link(b.add_transparent(em), out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    glow = bpy.context.active_object
    glow.name = "LastGlow"
    glow.data.materials.append(g_mat)
    glow.hide_render = True

    font = None
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                font = bpy.data.fonts.load(fp)
                break
            except Exception:
                pass
    texts = []
    for i, (body, t0, t1, y) in enumerate(TEXTS):
        o, m = text_obj("Text%d" % i, body, font, 0.034, y, cam, dist=0.05)
        texts.append((o, m, t0, t1))

    STATE.update(dict(cam=cam, earth=earth, earth_mat=earth_mat, aur_mat=aur_mat,
                      ll=ll, ll_mat=ll_mat, texts=texts, glow=glow, glow_mat=g_mat))
    if update_frame not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(update_frame)
    return sc

def last_light_strength(t):
    if t >= LAST_OUT + 0.6:
        return 0.0
    if t < BLINK_START:
        return 1.6
    if t >= LAST_OUT:
        # one weak dying flicker after it goes out
        return 0.6 if LAST_OUT + 0.30 < t < LAST_OUT + 0.38 else 0.0
    # slow, patient blink: ~1.1 s period, soft edges
    ph = ((t - BLINK_START) % 1.1) / 1.1
    on = smoothstep(0.0, 0.06, ph) * (1.0 - smoothstep(0.42, 0.55, ph))
    return 0.03 + 3.0 * on

def text_opacity(t, t0, t1, fin=0.7, fout=0.8):
    return smoothstep(t0, t0 + fin, t) * (1.0 - smoothstep(t1 - fout, t1, t))

def update_frame(scene, *args):
    t = scene.frame_current / FPS
    st = STATE
    if not st:
        return
    st["cam"].matrix_world = camera_matrix(t)
    st["earth"].rotation_euler = (earth_rot(t), 0.0, 0.0)
    nodes = st["earth_mat"].node_tree.nodes
    nodes["WaveT"].outputs[0].default_value = wave_T(t)
    nodes["Time"].outputs[0].default_value = t
    st["aur_mat"].node_tree.nodes["Time"].outputs[0].default_value = t
    ls = last_light_strength(t)
    st["ll_mat"].node_tree.nodes["Strength"].outputs[0].default_value = ls
    # glow sprite: halfway between camera and light, facing the camera
    glow = st["glow"]
    on = t >= BLINK_START - 0.5
    glow.hide_render = not on
    if on:
        cm = camera_matrix(t)
        lw = Matrix.Rotation(earth_rot(t), 4, 'X') @ st["ll"].location
        pos = cm.translation.lerp(lw, 0.5)
        dist = (lw - cm.translation).length * 0.5
        m = cm.to_3x3().to_4x4()
        m.translation = pos
        glow.matrix_world = m @ Matrix.Scale(0.085 * dist, 4)
        ramp = smoothstep(BLINK_START - 0.5, BLINK_START + 0.5, t)
        st["glow_mat"].node_tree.nodes["Strength"].outputs[0].default_value = 0.10 * ls * ramp
    for o, m, t0, t1 in st["texts"]:
        a = text_opacity(t, t0, t1)
        m.node_tree.nodes["Opacity"].outputs[0].default_value = a
        o.hide_render = a <= 0.001

# ----------------------------------------------------------------------------- main
def main():
    sc = build()
    out = OUTPUT
    if "--out" in ARGS:
        out = ARGS[ARGS.index("--out") + 1]
    if "--scale" in ARGS:
        setup_render(sc, float(ARGS[ARGS.index("--scale") + 1]))
    os.makedirs(out, exist_ok=True)
    if "--save" in ARGS:
        bpy.ops.wm.save_as_mainfile(filepath=ARGS[ARGS.index("--save") + 1])
    frames = []
    if "--still" in ARGS:
        i = ARGS.index("--still") + 1
        while i < len(ARGS) and not ARGS[i].startswith("--"):
            frames.append(int(ARGS[i])); i += 1
    elif "--render" in ARGS:
        a, z = sc.frame_start, sc.frame_end
        if "--frames" in ARGS:
            i = ARGS.index("--frames")
            a, z = int(ARGS[i + 1]), int(ARGS[i + 2])
        step = 1
        if "--step" in ARGS:
            step = int(ARGS[ARGS.index("--step") + 1])
        frames = list(range(a, z + 1, step))
    skip = "--overwrite" not in ARGS
    for f in frames:
        path = os.path.join(out, "f_%04d.png" % f)
        if skip and "--still" not in ARGS and os.path.exists(path):
            continue
        t0 = time.time()
        sc.frame_set(f)
        update_frame(sc)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("frame %d  %.2fs" % (f, time.time() - t0), flush=True)

main()
