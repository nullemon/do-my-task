"""
DOMINO PLANETS -- one continuous domino run that crosses six planets.

One long domino track (gentle S-curve) runs over coloured ground zones. Each zone
is a planet with its own REAL surface gravity. As the wave front enters a zone the
gravity of the whole rigid-body world switches to that planet, so the wave visibly
crawls on the Moon, floats on Pluto, hurries on Jupiter and slams down on the Sun.
One scene, one tracking camera that follows the wave front.

How the per-zone gravity works (Blender has ONE global rigid-body gravity):
  * The simulation is stepped frame by frame from Python. When the first domino of
    the next zone starts to tip (= the wave front crosses the boundary) a CONSTANT
    keyframe is written on scene.gravity for the next frame. The rigid-body solver
    reads the animated scene.gravity every frame, so the gravity switch is real
    physics, not a time-remap.
  * Everything behind the front is lying still and asleep (Bullet deactivation),
    everything ahead is standing still and asleep (start deactivated), so the only
    bodies the gravity change acts on are the ones in the moving wave.
  * The in-memory cache from that pass is then converted to a proper bake
    (ptcache.bake_from_cache), so playback and rendering are deterministic.

Run:
  Blender UI : open the Scripting tab, load this file, press Run (builds + bakes, ~1 min)
  Headless   : blender -b -P domino_planets.py -- --render      (full video, Eevee)
               blender -b -P domino_planets.py -- --preview     (a few low-res Cycles stills)
  Options    : --out DIR  (output folder), --no-bake (build only)

Works on Blender 4.2 LTS .. 5.x.
"""

import bpy
import bmesh
import math
import os
import sys
import time
from mathutils import Vector, Matrix

# =============================================================================
# CONFIG
# =============================================================================
CONFIG = dict(
    # The run, in order: (planet, number of dominoes in that zone).
    # Counts are tuned so each zone lasts ~5-7 s (the Sun is a ~2 s slam).
    ZONES=[
        ("Earth", 45),
        ("Moon", 20),
        ("Jupiter", 70),
        ("Pluto", 16),
        ("Sun", 80),
        ("Mars", 30),
    ],
    FPS=30,
    RESOLUTION=(1080, 1920),        # vertical 9:16
    ENGINE="EEVEE",                 # "EEVEE" or "CYCLES" for --render
    EEVEE_SAMPLES=64,
    CYCLES_SAMPLES=128,
    RENDER=False,                   # same as --render
    PREVIEW=False,                  # same as --preview
    PREVIEW_RESOLUTION=(270, 480),
    PREVIEW_SAMPLES=16,
    OUTPUT="//renders/domino_planets/",   # relative to .blend (or script dir if unsaved)

    # Domino geometry (metres). Giant-ish dominoes are far more stable in Bullet.
    DOMINO_H=1.0,
    DOMINO_W=0.5,
    DOMINO_T=0.15,
    SPACING=0.5,                    # centre to centre along the track
    FRICTION=0.6,
    START_TILT_DEG=12.0,            # first domino is tipped this far by a kinematic nudge
    START_FRAME=24,                 # when the first domino is let go (intro hold)

    # Solver. 20 substeps/frame @30fps = 600 Hz; needed so the Sun zone (274 m/s^2)
    # does not tunnel or explode.
    SUBSTEPS=20,
    SOLVER_ITERATIONS=20,

    # Track shape: S-curve amplitude (m) and how many half-waves along the run.
    S_AMPLITUDE=7.0,
    S_HALF_WAVES=2,
    ZONE_HALF_WIDTH=40.0,           # how wide each coloured floor zone is

    OUTRO_SECONDS=2.0,
    MAX_SECONDS=80,                 # safety limit for the simulation
    HOOK_TEXT="SAME DOMINOES · 6 PLANETS",
)

# Real surface gravity (m/s^2)
GRAVITY = {
    "Pluto": 0.62, "Moon": 1.62, "Mercury": 3.70, "Mars": 3.71, "Venus": 8.87,
    "Earth": 9.81, "Uranus": 8.69, "Neptune": 11.15, "Saturn": 10.44,
    "Jupiter": 24.79, "Sun": 274.0,
}

# Look per planet: floor colours (a, b), floor style, sky colour + strength,
# domino colour, label card accent, sun-lamp colour + strength
LOOK = {
    "Earth":   dict(fa=(0.10, 0.30, 0.06), fb=(0.22, 0.45, 0.10), style="noise",
                    sky=(0.30, 0.55, 0.95), sky_s=1.0, dom=(0.92, 0.91, 0.87),
                    card=(0.15, 0.55, 1.00), lamp=(1.0, 0.96, 0.9), lamp_s=4.0),
    "Moon":    dict(fa=(0.20, 0.20, 0.20), fb=(0.50, 0.50, 0.50), style="craters",
                    sky=(0.003, 0.003, 0.005), sky_s=1.0, dom=(0.98, 0.70, 0.12),
                    card=(0.85, 0.85, 0.85), lamp=(1.0, 1.0, 1.0), lamp_s=5.0),
    "Jupiter": dict(fa=(0.42, 0.18, 0.07), fb=(0.92, 0.78, 0.58), style="bands",
                    sky=(0.80, 0.50, 0.28), sky_s=0.9, dom=(0.08, 0.16, 0.40),
                    card=(1.00, 0.55, 0.15), lamp=(1.0, 0.85, 0.65), lamp_s=3.0),
    "Pluto":   dict(fa=(0.62, 0.52, 0.42), fb=(0.88, 0.92, 0.98), style="noise",
                    sky=(0.010, 0.012, 0.030), sky_s=1.0, dom=(0.35, 0.55, 0.95),
                    card=(0.90, 0.84, 0.72), lamp=(0.85, 0.9, 1.0), lamp_s=2.5),
    "Sun":     dict(fa=(0.60, 0.08, 0.00), fb=(1.00, 0.45, 0.05), style="lava",
                    sky=(0.35, 0.07, 0.01), sky_s=1.0, dom=(0.03, 0.03, 0.03),
                    card=(1.00, 0.80, 0.10), lamp=(1.0, 0.6, 0.3), lamp_s=3.0),
    "Mars":    dict(fa=(0.35, 0.10, 0.04), fb=(0.62, 0.26, 0.10), style="noise",
                    sky=(0.85, 0.58, 0.32), sky_s=0.9, dom=(0.93, 0.92, 0.88),
                    card=(0.90, 0.35, 0.12), lamp=(1.0, 0.85, 0.7), lamp_s=3.5),
    "Mercury": dict(fa=(0.25, 0.23, 0.21), fb=(0.50, 0.47, 0.43), style="craters",
                    sky=(0.003, 0.003, 0.005), sky_s=1.0, dom=(0.9, 0.5, 0.2),
                    card=(0.75, 0.70, 0.65), lamp=(1.0, 1.0, 1.0), lamp_s=6.0),
    "Venus":   dict(fa=(0.45, 0.35, 0.12), fb=(0.70, 0.58, 0.25), style="noise",
                    sky=(0.90, 0.75, 0.35), sky_s=0.9, dom=(0.25, 0.15, 0.10),
                    card=(0.95, 0.80, 0.30), lamp=(1.0, 0.9, 0.6), lamp_s=2.0),
    "Uranus":  dict(fa=(0.40, 0.70, 0.75), fb=(0.65, 0.88, 0.90), style="bands",
                    sky=(0.45, 0.75, 0.85), sky_s=0.9, dom=(0.10, 0.20, 0.30),
                    card=(0.50, 0.90, 0.95), lamp=(0.9, 1.0, 1.0), lamp_s=2.5),
    "Neptune": dict(fa=(0.08, 0.15, 0.50), fb=(0.20, 0.35, 0.80), style="bands",
                    sky=(0.10, 0.20, 0.60), sky_s=0.9, dom=(0.95, 0.95, 0.95),
                    card=(0.30, 0.50, 1.00), lamp=(0.8, 0.9, 1.0), lamp_s=2.5),
    "Saturn":  dict(fa=(0.65, 0.55, 0.35), fb=(0.88, 0.80, 0.60), style="bands",
                    sky=(0.85, 0.75, 0.55), sky_s=0.9, dom=(0.30, 0.20, 0.10),
                    card=(0.95, 0.85, 0.55), lamp=(1.0, 0.95, 0.8), lamp_s=3.0),
}

SCENE_NAME = "DominoPlanets"
PREFIX = "DP_"


# =============================================================================
# helpers
# =============================================================================
def log(*a):
    print("[domino_planets]", *a, flush=True)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = dict(render=CONFIG["RENDER"], preview=CONFIG["PREVIEW"], out=None, bake=True)
    i = 0
    while i < len(argv):
        if argv[i] == "--render":
            a["render"] = True
        elif argv[i] == "--preview":
            a["preview"] = True
        elif argv[i] == "--no-bake":
            a["bake"] = False
        elif argv[i] == "--out" and i + 1 < len(argv):
            a["out"] = argv[i + 1]
            i += 1
        i += 1
    return a


def output_dir(args):
    if args["out"]:
        return os.path.abspath(args["out"])
    rel = CONFIG["OUTPUT"]
    if bpy.data.filepath:
        return bpy.path.abspath(rel)
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(base):
            raise OSError
    except (NameError, OSError):
        base = os.getcwd()
    return os.path.join(base, rel.lstrip("/").lstrip("\\"))


def get_fcurve(idb, path, index):
    """Find an F-Curve on an ID; works with legacy (4.2) and layered (4.4+/5.x) actions."""
    ad = idb.animation_data
    act = ad.action
    fcs = None
    try:
        from bpy_extras import anim_utils
        if hasattr(anim_utils, "action_get_channelbag_for_slot") and getattr(ad, "action_slot", None):
            cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
            if cb is not None:
                fcs = cb.fcurves
    except Exception:
        fcs = None
    if fcs is None:
        fcs = act.fcurves
    return fcs.find(path, index=index)


def all_fcurves(idb):
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    try:
        from bpy_extras import anim_utils
        if hasattr(anim_utils, "action_get_channelbag_for_slot") and getattr(ad, "action_slot", None):
            cb = anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
            if cb is not None:
                return list(cb.fcurves)
    except Exception:
        pass
    return list(getattr(act, "fcurves", []))


def set_interp(idb, mode):
    for fc in all_fcurves(idb):
        for k in fc.keyframe_points:
            k.interpolation = mode


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


# =============================================================================
# scene reset
# =============================================================================
def fresh_scene():
    old = bpy.data.scenes.get(SCENE_NAME)
    sc = bpy.data.scenes.new(SCENE_NAME + "_new")
    win = bpy.context.window
    if win is not None:
        win.scene = sc
    if old is not None:
        for o in list(old.collection.all_objects):
            if o.name.startswith(PREFIX):
                bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.scenes.remove(old)
    sc.name = SCENE_NAME
    # orphan data from previous runs
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.worlds, bpy.data.collections):
        for d in list(coll):
            if d.name.startswith(PREFIX) and d.users == 0:
                coll.remove(d)
    # remove the default scene's cube etc. only if it is the untouched startup "Scene"
    return sc


# =============================================================================
# track geometry: arc-length parametrised S-curve
# =============================================================================
class Track:
    def __init__(self, length, amp, half_waves, margin_before=60.0, margin_after=300.0):
        self.length = length
        self.s0 = -margin_before
        self.s1 = length + margin_after
        lx = length
        n = 8000
        pts = []
        x0, x1 = self.s0, self.s1
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            y = amp * math.sin(math.pi * half_waves * x / lx) if 0 <= x <= lx else (
                0.0 if x < 0 else amp * math.sin(math.pi * half_waves))
            # smooth ramp-in/out of the curve so tangents are continuous at ends
            pts.append(Vector((x, y, 0.0)))
        # cumulative arc length, zero at x = 0
        s = [0.0]
        for i in range(1, len(pts)):
            s.append(s[-1] + (pts[i] - pts[i - 1]).length)
        i0 = min(range(len(pts)), key=lambda i: abs(pts[i].x))
        off = s[i0]
        self.s = [v - off for v in s]
        self.p = pts

    def _idx(self, s):
        ss = self.s
        lo, hi = 0, len(ss) - 1
        if s <= ss[0]:
            return 0, 0.0
        if s >= ss[-1]:
            return hi - 1, 1.0
        while hi - lo > 1:
            m = (lo + hi) // 2
            if ss[m] <= s:
                lo = m
            else:
                hi = m
        t = (s - ss[lo]) / max(1e-9, ss[lo + 1] - ss[lo])
        return lo, t

    def point(self, s):
        i, t = self._idx(s)
        return self.p[i].lerp(self.p[i + 1], t)

    def tangent(self, s):
        a, b = self.point(s - 0.25), self.point(s + 0.25)
        return (b - a).normalized()

    def normal(self, s):  # left normal on ground
        t = self.tangent(s)
        return Vector((-t.y, t.x, 0.0))


# =============================================================================
# materials
# =============================================================================
def mat_principled(name, color, rough=0.4, spec=0.5, emission=None, em_strength=0.0):
    m = bpy.data.materials.new(PREFIX + name)
    if bpy.app.version < (5, 0, 0) or m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if emission is not None:
        key = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[key].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = em_strength
    m.diffuse_color = (*color, 1)
    return m


def mat_emission(name, color, strength=1.0):
    m = bpy.data.materials.new(PREFIX + name)
    if bpy.app.version < (5, 0, 0) or m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    m.diffuse_color = (*color, 1)
    return m


def mat_floor(planet):
    L = LOOK[planet]
    m = bpy.data.materials.new(PREFIX + "Floor_" + planet)
    if bpy.app.version < (5, 0, 0) or m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links
    bsdf = N.get("Principled BSDF")
    out = N.get("Material Output")
    geo = N.new("ShaderNodeNewGeometry")
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*L["fa"], 1)
    ramp.color_ramp.elements[1].color = (*L["fb"], 1)
    style = L["style"]
    if style == "bands":
        tex = N.new("ShaderNodeTexWave")
        tex.wave_type = "BANDS"
        tex.bands_direction = "Y"
        tex.inputs["Scale"].default_value = 0.12
        tex.inputs["Distortion"].default_value = 2.5
        tex.inputs["Detail"].default_value = 3.0
        Lk.new(geo.outputs["Position"], tex.inputs["Vector"])
        Lk.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    else:
        tex = N.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 0.35 if style != "lava" else 0.25
        tex.inputs["Detail"].default_value = 8.0
        tex.inputs["Roughness"].default_value = 0.6
        Lk.new(geo.outputs["Position"], tex.inputs["Vector"])
        Lk.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        ramp.color_ramp.elements[0].position = 0.35
        ramp.color_ramp.elements[1].position = 0.65
    Lk.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    # bump
    if style in ("craters", "noise", "lava"):
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 0.6 if style == "craters" else 1.5
        Lk.new(geo.outputs["Position"], vor.inputs["Vector"])
        bump = N.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.35 if style == "craters" else 0.15
        Lk.new(vor.outputs["Distance"], bump.inputs["Height"])
        Lk.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if style == "lava":
        # dark crust broken by glowing cracks (Voronoi edges) + hot patches
        vor2 = N.new("ShaderNodeTexVoronoi")
        vor2.feature = "DISTANCE_TO_EDGE"
        vor2.inputs["Scale"].default_value = 0.45
        if "Randomness" in vor2.inputs:
            vor2.inputs["Randomness"].default_value = 1.0
        Lk.new(geo.outputs["Position"], vor2.inputs["Vector"])
        cr = N.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].color = (1.0, 0.85, 0.30, 1)
        cr.color_ramp.elements[0].position = 0.0
        cr.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1)
        cr.color_ramp.elements[1].position = 0.12
        e = cr.color_ramp.elements.new(0.04)
        e.color = (1.0, 0.35, 0.03, 1)
        Lk.new(vor2.outputs["Distance"], cr.inputs["Fac"])
        add = N.new("ShaderNodeMix")
        add.data_type = "RGBA"
        add.blend_type = "ADD"
        add.inputs["Factor"].default_value = 1.0
        hot = N.new("ShaderNodeMix")  # patches of glowing crust from the noise ramp
        hot.data_type = "RGBA"
        hot.blend_type = "MULTIPLY"
        hot.inputs["Factor"].default_value = 1.0
        Lk.new(ramp.outputs["Color"], hot.inputs[6])
        hot.inputs[7].default_value = (0.35, 0.35, 0.35, 1)
        Lk.new(cr.outputs["Color"], add.inputs[6])
        Lk.new(hot.outputs[2], add.inputs[7])
        key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        Lk.new(add.outputs[2], bsdf.inputs[key])
        bsdf.inputs["Emission Strength"].default_value = 3.0
        bsdf.inputs["Base Color"].default_value = (0.05, 0.01, 0.0, 1)
        for l in list(bsdf.inputs["Base Color"].links):
            Lk.remove(l)
    m.diffuse_color = (*L["fb"], 1)
    return m


# =============================================================================
# meshes
# =============================================================================
def domino_mesh(name, H, W, T, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * T, v.co.y * W, v.co.z * H))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.02, segments=3, affect="EDGES",
                    profile=0.5)
    me = bpy.data.meshes.new(PREFIX + name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    return me


def strip_mesh(name, track, sa, sb, half_w, z, ds=1.0, across=8):
    n = max(2, int(math.ceil((sb - sa) / ds)))
    verts, faces = [], []
    for i in range(n + 1):
        s = sa + (sb - sa) * i / n
        p, nn = track.point(s), track.normal(s)
        for j in range(across + 1):
            u = -half_w + 2 * half_w * j / across
            q = p + nn * u
            verts.append((q.x, q.y, z))
    w = across + 1
    for i in range(n):
        for j in range(across):
            a = i * w + j
            faces.append((a, a + 1, a + 1 + w, a + w))
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata(verts, [], faces)
    me.update()
    return me


def box_mesh(name, dx, dy, dz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dx, v.co.y * dy, v.co.z * dz))
    me = bpy.data.meshes.new(PREFIX + name)
    bm.to_mesh(me)
    bm.free()
    return me


def rounded_rect_mesh(name, w, h, r, seg=8):
    pts = []
    corners = [(w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
               (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)]
    for cx, cy, a0 in corners:
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), 0))
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata(pts, [], [list(range(len(pts)))])
    me.update()
    return me


def new_obj(sc, coll, name, data):
    o = bpy.data.objects.new(PREFIX + name, data)
    coll.objects.link(o)
    return o


# =============================================================================
# build
# =============================================================================
def build(sc):
    C = CONFIG
    H, W, T, SP = C["DOMINO_H"], C["DOMINO_W"], C["DOMINO_T"], C["SPACING"]
    zones = [(p, int(n)) for p, n in C["ZONES"]]
    for p, _ in zones:
        if p not in GRAVITY:
            raise ValueError("Unknown planet in CONFIG ZONES: %s" % p)
    ntot = sum(n for _, n in zones)
    length = (ntot - 1) * SP
    track = Track(length, C["S_AMPLITUDE"], C["S_HALF_WAVES"])

    fps = C["FPS"]
    sc.render.fps = fps
    sc.render.resolution_x, sc.render.resolution_y = C["RESOLUTION"]
    sc.render.resolution_percentage = 100
    sc.frame_start = 1
    max_frames = int(C["MAX_SECONDS"] * fps)
    sc.frame_end = max_frames

    coll = bpy.data.collections.new(PREFIX + "Scene")
    sc.collection.children.link(coll)

    # ----- rigid body world
    with bpy.context.temp_override(scene=sc):
        bpy.ops.rigidbody.world_add()
    rbw = sc.rigidbody_world
    rbw.substeps_per_frame = C["SUBSTEPS"]
    rbw.solver_iterations = C["SOLVER_ITERATIONS"]
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = max_frames
    sc.use_gravity = True

    # ----- ground collider (hidden) + floor zones (visual)
    ground = new_obj(sc, coll, "GroundCollider", box_mesh("GroundCollider", track.s1 - track.s0 + 40, 120, 1.0))
    ground.location = (0.5 * (track.s0 + track.s1), track.point(length / 2).y, -0.5)
    ground.hide_render = True
    ground.display_type = "WIRE"
    with bpy.context.temp_override(scene=sc, object=ground, active_object=ground,
                                   selected_objects=[ground], selected_editable_objects=[ground]):
        bpy.ops.rigidbody.object_add(type="PASSIVE")
    ground.rigid_body.friction = C["FRICTION"]
    ground.rigid_body.collision_shape = "BOX"

    base = new_obj(sc, coll, "BaseGround", box_mesh("BaseGround", 2000, 2000, 0.01))
    base.location = (length / 2, 0, -0.03)
    base.data.materials.append(mat_principled("Base", (0.03, 0.03, 0.035), rough=0.95))

    # domino arc positions + zone ranges
    s_dom = [i * SP for i in range(ntot)]
    zone_first = []
    k = 0
    for p, n in zones:
        zone_first.append(k)
        k += n
    zone_bounds = []  # (s_start, s_end) for floor strips
    for zi, (p, n) in enumerate(zones):
        i0, i1 = zone_first[zi], zone_first[zi] + n - 1
        sa = track.s0 if zi == 0 else 0.5 * (s_dom[i0 - 1] + s_dom[i0])
        sb = track.s1 if zi == len(zones) - 1 else 0.5 * (s_dom[i1] + s_dom[i1 + 1])
        zone_bounds.append((sa, sb))
        fl = new_obj(sc, coll, "Floor_%02d_%s" % (zi + 1, p),
                     strip_mesh("Floor_%s" % p, track, sa, sb, C["ZONE_HALF_WIDTH"], 0.0))
        fl.data.materials.append(mat_floor(p))
        if zi > 0:
            nxt = LOOK[p]["card"]
            line = new_obj(sc, coll, "Boundary_%02d_%s" % (zi + 1, p),
                           strip_mesh("Boundary_%s" % p, track, sa - 0.05, sa + 0.05, 2.2, 0.004, ds=0.1, across=4))
            line.data.materials.append(mat_emission("Line_" + p, nxt, 4.0))

    # ----- dominoes
    dom_mats = {p: mat_principled("Domino_" + p, LOOK[p]["dom"], rough=0.25, spec=0.6) for p, _ in zones}
    dom_meshes = {p: domino_mesh("Domino_" + p, H, W, T, dom_mats[p]) for p, _ in zones}
    doms = []
    template = None
    for zi, (p, n) in enumerate(zones):
        for j in range(n):
            i = zone_first[zi] + j
            s = s_dom[i]
            pt, tg = track.point(s), track.tangent(s)
            yaw = math.atan2(tg.y, tg.x)
            if template is None:
                o = new_obj(sc, coll, "Domino_%03d" % i, dom_meshes[p])
                with bpy.context.temp_override(scene=sc, object=o, active_object=o,
                                               selected_objects=[o], selected_editable_objects=[o]):
                    bpy.ops.rigidbody.object_add(type="ACTIVE")
                rb = o.rigid_body
                rb.collision_shape = "BOX"
                rb.mass = 1.0
                rb.friction = C["FRICTION"]
                rb.restitution = 0.0
                rb.linear_damping = 0.0
                rb.angular_damping = 0.0
                rb.use_deactivation = True
                rb.use_start_deactivated = True
                rb.deactivate_linear_velocity = 0.01
                rb.deactivate_angular_velocity = 0.01
                template = o
            else:
                o = template.copy()
                o.data = dom_meshes[p]
                o.name = PREFIX + "Domino_%03d" % i
                coll.objects.link(o)
                if o.name not in rbw.collection.objects:
                    rbw.collection.objects.link(o)
            o.location = (pt.x, pt.y, H / 2)
            o.rotation_euler = (0, 0, yaw)
            doms.append(o)

    # first domino: kinematic nudge (hold upright, tip to START_TILT, then release)
    d0 = doms[0]
    d0.rigid_body.use_start_deactivated = False
    f_rel = C["START_FRAME"]
    pivot_s = s_dom[0] + T / 2
    tg0 = track.tangent(0)
    yaw0 = math.atan2(tg0.y, tg0.x)
    for f, ang, kin in ((1, 0.0, True), (f_rel - 8, 0.0, True), (f_rel, C["START_TILT_DEG"], True),
                        (f_rel + 1, C["START_TILT_DEG"], False)):
        a = math.radians(ang)
        # rotate about the front-bottom edge (local +X side)
        local = Vector((-T / 2 * math.cos(a) + H / 2 * math.sin(a), 0, T / 2 * math.sin(a) + H / 2 * math.cos(a)))
        world = track.point(pivot_s) + Matrix.Rotation(yaw0, 3, "Z") @ local
        d0.location = world
        d0.rotation_euler = (0, a, yaw0)
        d0.rigid_body.kinematic = kin
        d0.keyframe_insert("location", frame=f)
        d0.keyframe_insert("rotation_euler", frame=f)
        d0.rigid_body.keyframe_insert("kinematic", frame=f)
    # tip with an ease
    for fc in all_fcurves(d0):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT" if fc.data_path.endswith("kinematic") else "BEZIER"

    # ----- gravity animation: start with zone-1 gravity
    sc.gravity = (0, 0, -GRAVITY[zones[0][0]])
    sc.keyframe_insert("gravity", index=2, frame=1)
    set_interp(sc, "CONSTANT")

    return dict(track=track, doms=doms, zones=zones, zone_first=zone_first,
                zone_bounds=zone_bounds, s_dom=s_dom, coll=coll, rbw=rbw, length=length)


# =============================================================================
# simulate: step frames, switch gravity at zone boundaries, record everything
# =============================================================================
def tilt_deg(o):
    z = o.matrix_world.col[2].z
    return math.degrees(math.acos(max(-1.0, min(1.0, z))))


def simulate(sc, B):
    C = CONFIG
    doms, zones, zf = B["doms"], B["zones"], B["zone_first"]
    n = len(doms)
    gfc = get_fcurve(sc, "gravity", 2)
    trig = [None] * n          # frame each domino passed 10 deg
    touch = [None] * n         # frame each domino passed 2 deg (hit)
    switch_frames = [1]        # frame the gravity of zone k starts
    zone_k = 0
    front_s = []               # per frame: continuous front arc position
    max_z, max_off = 0.0, 0.0
    t0 = time.time()
    end_frame = None
    last_progress = 1
    f = 1
    track = B["track"]
    lo = 0  # dominoes below lo are settled and need no checking for trigger
    while f <= sc.frame_end:
        sc.frame_set(f)
        front = -1
        frac = 0.0
        for i in range(lo, min(n, lo + 40)):
            if trig[i] is None:
                t = tilt_deg(doms[i])
                if t > 2 and touch[i] is None:
                    touch[i] = f
                if t > 10:
                    trig[i] = f
                    last_progress = f
            if trig[i] is not None:
                front = i
            elif touch[i] is not None:
                frac = max(frac, min(1.0, tilt_deg(doms[i]) / 30.0))
        while lo < n and trig[lo] is not None and lo < front - 5:
            lo += 1
        if front < 0:
            front_s.append(B["s_dom"][0] if f >= C["START_FRAME"] else B["s_dom"][0] - 0.0)
        else:
            front_s.append(B["s_dom"][front] + frac * C["SPACING"])
        # gravity switch: first domino of the next zone got hit
        if zone_k + 1 < len(zones) and touch[zf[zone_k + 1]] is not None:
            zone_k += 1
            g = GRAVITY[zones[zone_k][0]]
            kp = gfc.keyframe_points.insert(f + 1, -g)
            kp.interpolation = "CONSTANT"
            gfc.update()
            switch_frames.append(f + 1)
            log("frame %4d  wave enters %-8s g=%6.2f m/s^2" % (f + 1, zones[zone_k][0], g))
        # sanity: nothing flies away (check a window around the front)
        for i in range(max(0, front - 30), min(n, front + 5)):
            p = doms[i].matrix_world.translation
            max_z = max(max_z, p.z)
            max_off = max(max_off, abs((p - track.point(B["s_dom"][i])).dot(track.normal(B["s_dom"][i]))))
        if all(t is not None for t in trig[-1:]) and end_frame is None:
            end_frame = f + int(C["OUTRO_SECONDS"] * C["FPS"])
        if end_frame is not None and f >= end_frame:
            break
        if f - last_progress > 10 * C["FPS"] and f > C["START_FRAME"] + 10:
            log("!! WAVE STALLED at domino %d (zone %s) frame %d" % (front, zones[zone_k][0], f))
            end_frame = f
            break
        if f % 150 == 0:
            log("  sim frame %d  front domino %d/%d  (%.0fs)" % (f, front, n, time.time() - t0))
        f += 1
    log("simulation: %d frames in %.1f s" % (f, time.time() - t0))
    return dict(trig=trig, touch=touch, switch_frames=switch_frames, front_s=front_s,
                end_frame=f, max_z=max_z, max_off=max_off)


def bake_cache(sc, B):
    rbw = B["rbw"]
    try:
        with bpy.context.temp_override(scene=sc, point_cache=rbw.point_cache):
            r = bpy.ops.ptcache.bake_from_cache()
        log("bake_from_cache:", r, "baked =", rbw.point_cache.is_baked)
    except Exception as e:  # pragma: no cover
        log("bake_from_cache failed (%s); the cache stays as a simulation cache" % e)


def report(sc, B, S):
    C = CONFIG
    fps = C["FPS"]
    zones, zf, trig = B["zones"], B["zone_first"], S["trig"]
    log("=" * 74)
    log("%-8s %7s %5s %9s %9s %9s" % ("zone", "g", "doms", "zone[s]", "s/domino", "m/s"))
    earth_ref = None
    rows = []
    for zi, (p, n) in enumerate(zones):
        i0 = zf[zi]
        i1 = i0 + n - 1
        fr = [trig[i] for i in range(i0, i1 + 1)]
        if None in fr:
            log("%-8s  INCOMPLETE: %d of %d fell" % (p, sum(x is not None for x in fr), n))
            rows.append(None)
            continue
        # time per domino measured over the zone (skip the first 2 so the
        # previous zone's momentum does not dominate)
        a = min(2, n - 2)
        per = (fr[-1] - fr[a]) / max(1, (n - 1 - a)) / fps
        zone_t = (fr[-1] - fr[0]) / fps
        rows.append((p, per))
        log("%-8s %7.2f %5d %9.2f %9.3f %9.2f" % (
            p, GRAVITY[p], n, zone_t, per, C["SPACING"] / max(per, 1e-6)))
    # theory: time per domino scales with 1/sqrt(g)
    ref = next((r for r in rows if r and r[0] == "Earth"), None) or next(r for r in rows if r)
    log("-" * 74)
    log("check: wave time ~ 1/sqrt(g)   (measured / predicted from %s)" % ref[0])
    for r in rows:
        if r:
            pred = ref[1] * math.sqrt(GRAVITY[ref[0]] / GRAVITY[r[0]])
            log("  %-8s measured %.3f s  predicted %.3f s  ratio %.2f" % (r[0], r[1], pred, r[1] / pred))
    fallen = sum(1 for t in trig if t is not None)
    log("dominoes fallen: %d / %d" % (fallen, len(trig)))
    final_tilts = [tilt_deg(o) for o in B["doms"]]
    log("final tilt: min %.1f deg (all > 20 = everything is down)" % min(final_tilts))
    log("max domino height seen %.2f m (H=%.2f), max sideways drift %.2f m" % (S["max_z"], C["DOMINO_H"], S["max_off"]))
    log("total length %.1f s (%d frames)" % (S["end_frame"] / fps, S["end_frame"]))
    log("=" * 74)


# =============================================================================
# camera, labels, sky
# =============================================================================
def gaussian_smooth(v, sigma):
    r = int(3 * sigma)
    w = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    out = []
    n = len(v)
    for i in range(n):
        acc = ws = 0.0
        for k in range(-r, r + 1):
            j = min(n - 1, max(0, i + k))
            acc += v[j] * w[k + r]
            ws += w[k + r]
        out.append(acc / ws)
    return out


def build_camera(sc, B, S):
    C = CONFIG
    track = B["track"]
    cam_d = bpy.data.cameras.new(PREFIX + "Camera")
    cam_d.lens = 30
    cam_d.sensor_fit = "AUTO"
    cam_d.clip_start = 0.05
    cam_d.clip_end = 600
    cam = new_obj(sc, B["coll"], "Camera", cam_d)
    sc.camera = cam
    tgt = new_obj(sc, B["coll"], "CamTarget", None)
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    fs = S["front_s"]
    # monotonic + smooth
    m = []
    best = -1e9
    for v in fs:
        best = max(best, v)
        m.append(best)
    sm = gaussian_smooth(m, 9.0)
    sm2 = gaussian_smooth(m, 4.0)
    for i, s in enumerate(sm):
        f = i + 1
        sc_ = s
        p = track.point(sc_ - 3.8) + track.normal(sc_) * 3.6 + Vector((0, 0, 2.7))
        q = track.point(sm2[i] + 2.2) + Vector((0, 0, 0.35))
        cam.location = p
        tgt.location = q
        cam.keyframe_insert("location", frame=f)
        tgt.keyframe_insert("location", frame=f)
    sc.frame_end = len(sm)
    return cam


def build_labels(sc, B, S, cam):
    C = CONFIG
    zones = B["zones"]
    sw = S["switch_frames"]
    cam_d = cam.data
    d = 1.0
    vis_h = d * 36.0 / cam_d.lens          # sensor 36 mm on the long (vertical) side
    vis_w = vis_h * C["RESOLUTION"][0] / C["RESOLUTION"][1]
    n = len(zones)

    def text_obj(name, body, size, mat):
        cu = bpy.data.curves.new(PREFIX + name, "FONT")
        cu.body = body
        cu.size = size
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.materials.append(mat)
        o = new_obj(sc, B["coll"], name, cu)
        return o

    # hook caption (top)
    hook_mat = mat_emission("HookText", (1, 1, 1), 1.6)
    hook = text_obj("Hook", C["HOOK_TEXT"], 0.05, hook_mat)
    hook.parent = cam
    bpy.context.view_layer.update() if bpy.context.view_layer else None
    sc.view_layers[0].update()
    wmax = vis_w * 0.86
    if hook.dimensions.x > 0:
        hook.data.size *= wmax / hook.dimensions.x
    hook.location = (0, vis_h * 0.41, -d)
    sc.view_layers[0].update()
    hook.location = (0, vis_h * 0.415, -d + 0.002)
    hb = new_obj(sc, B["coll"], "HookCard",
                 rounded_rect_mesh("HookCard", hook.dimensions.x + 0.04, hook.data.size * 1.7, hook.data.size * 0.6))
    hb.data.materials.append(mat_emission("HookCard", (0.0, 0.0, 0.0), 1.0))
    hb.parent = cam
    hb.location = (0, vis_h * 0.415 + hook.data.size * 0.04, -d)

    for zi, (p, _) in enumerate(zones):
        L = LOOK[p]
        g = GRAVITY[p]
        body = "%s · %s m/s²" % (p.upper(), ("%.2f" % g) if g < 100 else ("%.0f" % g))
        root = new_obj(sc, B["coll"], "Label_%02d_%s" % (zi + 1, p), None)
        root.parent = cam
        root.location = (0, vis_h * 0.31, -d)
        dark = lum(L["card"]) > 0.35
        tmat = mat_emission("LabelText_" + p, (0.01, 0.01, 0.01) if dark else (1, 1, 1), 1.0 if dark else 1.6)
        t = text_obj("LabelText_%02d_%s" % (zi + 1, p), body, 0.05, tmat)
        t.parent = root
        sc.view_layers[0].update()
        if t.dimensions.x > 0:
            t.data.size *= (vis_w * 0.74) / t.dimensions.x
        sc.view_layers[0].update()
        tw, th = t.dimensions.x, t.data.size
        t.location = (0, -th * 0.04, 0.002)
        card = new_obj(sc, B["coll"], "LabelCard_%02d_%s" % (zi + 1, p),
                       rounded_rect_mesh("Card_" + p, tw + th * 1.0, th * 1.75, th * 0.5))
        card.data.materials.append(mat_emission("Card_" + p, L["card"], 1.0))
        card.parent = root
        # pop in when the wave enters, pop out when it leaves
        f_in = sw[zi] if zi > 0 else 6
        f_out = sw[zi + 1] if zi + 1 < n else None
        keys = [(f_in - 1, 0.0), (f_in + 4, 1.12), (f_in + 8, 1.0)]
        if f_out is not None:
            keys += [(f_out - 2, 1.0), (f_out + 1, 0.0)]
        for f, s in keys:
            root.scale = (s, s, s)
            root.keyframe_insert("scale", frame=max(0, f))

    # small gravity bar under the label? keep it clean: no.


def build_world_and_light(sc, B, S):
    zones = B["zones"]
    sw = S["switch_frames"]
    w = bpy.data.worlds.new(PREFIX + "World")
    if bpy.app.version < (5, 0, 0) or w.node_tree is None:
        w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    sc.world = w
    lamp_d = bpy.data.lights.new(PREFIX + "Sun", "SUN")
    lamp_d.angle = math.radians(4.0)
    lamp = new_obj(sc, B["coll"], "SunLamp", lamp_d)
    lamp.rotation_euler = (math.radians(52), math.radians(0), math.radians(-35))
    fade = 12
    # the far-away ground outside the zone strips follows the current zone colour
    bmat = bpy.data.materials.get(PREFIX + "Base")
    bcol = bmat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"] if bmat else None
    for zi, (p, _) in enumerate(zones):
        L = LOOK[p]
        f = sw[zi] if zi > 0 else 1
        frames = [f] if zi == 0 else [f - 1 + fade]
        if zi > 0:
            # hold the previous colour until the switch, then blend over `fade` frames
            Lp = LOOK[zones[zi - 1][0]]
            bg.inputs[0].default_value = (*Lp["sky"], 1)
            bg.inputs[0].keyframe_insert("default_value", frame=f - 1)
            lamp_d.color = Lp["lamp"]
            lamp_d.energy = Lp["lamp_s"]
            lamp_d.keyframe_insert("color", frame=f - 1)
            lamp_d.keyframe_insert("energy", frame=f - 1)
            if bcol is not None:
                bcol.default_value = (*[c * 0.8 for c in Lp["fa"]], 1)
                bcol.keyframe_insert("default_value", frame=f - 1)
        bg.inputs[0].default_value = (*L["sky"], 1)
        bg.inputs[1].default_value = L["sky_s"]
        bg.inputs[0].keyframe_insert("default_value", frame=frames[0])
        lamp_d.color = L["lamp"]
        lamp_d.energy = L["lamp_s"]
        lamp_d.keyframe_insert("color", frame=frames[0])
        lamp_d.keyframe_insert("energy", frame=frames[0])
        if bcol is not None:
            bcol.default_value = (*[c * 0.8 for c in L["fa"]], 1)
            bcol.keyframe_insert("default_value", frame=frames[0])


def add_markers(sc, B, S):
    sc.timeline_markers.clear()
    for zi, (p, _) in enumerate(B["zones"]):
        f = S["switch_frames"][zi] if zi > 0 else 1
        sc.timeline_markers.new("%02d_%s" % (zi + 1, p), frame=f)


# =============================================================================
# render settings
# =============================================================================
def eevee_id():
    ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for k in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if k in ids:
            return k
    return ids[0]


def setup_render(sc, engine, samples, res, out_path):
    r = sc.render
    r.engine = engine
    r.resolution_x, r.resolution_y = res
    r.resolution_percentage = 100
    r.filepath = out_path
    r.image_settings.file_format = "PNG"
    try:
        sc.view_settings.view_transform = "AgX"
        for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
            try:
                sc.view_settings.look = look
                break
            except TypeError:
                pass
    except TypeError:
        pass
    if engine == "CYCLES":
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 4
    else:
        ee = sc.eevee
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = samples
        for attr, val in (("use_shadows", True), ("use_raytracing", True), ("use_gtao", True)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)


# =============================================================================
# main
# =============================================================================
def main():
    args = parse_args()
    t0 = time.time()
    sc = fresh_scene()
    B = build(sc)
    log("built %d dominoes over %.0f m of track in %d zones" % (len(B["doms"]), B["length"], len(B["zones"])))
    if not args["bake"]:
        return
    S = simulate(sc, B)
    report(sc, B, S)
    cam = build_camera(sc, B, S)
    build_labels(sc, B, S, cam)
    build_world_and_light(sc, B, S)
    add_markers(sc, B, S)
    sc.frame_end = S["end_frame"]
    bake_cache(sc, B)
    out = output_dir(args)
    setup_render(sc, eevee_id() if CONFIG["ENGINE"].upper() != "CYCLES" else "CYCLES",
                 CONFIG["EEVEE_SAMPLES"] if CONFIG["ENGINE"].upper() != "CYCLES" else CONFIG["CYCLES_SAMPLES"],
                 CONFIG["RESOLUTION"], os.path.join(out, "frame_"))
    sc.frame_set(1)
    log("ready in %.0f s; %d frames (%.1f s @ %d fps)" % (time.time() - t0, sc.frame_end, sc.frame_end / CONFIG["FPS"], CONFIG["FPS"]))

    if args["preview"]:
        pdir = os.path.join(out, "preview")
        os.makedirs(pdir, exist_ok=True)
        setup_render(sc, "CYCLES", CONFIG["PREVIEW_SAMPLES"], CONFIG["PREVIEW_RESOLUTION"], "")
        fs = S["front_s"]
        for zi, (p, nz) in enumerate(B["zones"]):
            # frame when the wave front is ~60% through the zone (Sun: mid-slam)
            i_mid = B["zone_first"][zi] + int(nz * (0.45 if p == "Sun" else 0.6))
            f = S["trig"][i_mid] or 1
            sc.frame_set(f)
            sc.render.filepath = os.path.join(pdir, "%02d_%s_f%04d.png" % (zi + 1, p, f))
            bpy.ops.render.render(write_still=True, scene=sc.name)
            log("preview ->", sc.render.filepath)
    if args["render"]:
        setup_render(sc, eevee_id() if CONFIG["ENGINE"].upper() != "CYCLES" else "CYCLES",
                     CONFIG["EEVEE_SAMPLES"] if CONFIG["ENGINE"].upper() != "CYCLES" else CONFIG["CYCLES_SAMPLES"],
                     CONFIG["RESOLUTION"], os.path.join(out, "frame_"))
        bpy.ops.render.render(animation=True, scene=sc.name)
        log("rendered frames ->", out)


if __name__ == "__main__":
    main()
