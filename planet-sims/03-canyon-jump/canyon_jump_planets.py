"""
CAN IT CLEAR THE CANYON?  -  planet-sims #03
=============================================
The same car, at the same speed, launches off the same ramp over the same
canyon on every planet.  Real surface gravity decides the outcome.

Run inside Blender (Scripting tab -> Run Script) or headless:
    blender -b -P canyon_jump_planets.py                 # build scenes only
    blender -b -P canyon_jump_planets.py -- --preview    # + low-res Cycles stills
    blender -b -P canyon_jump_planets.py -- --render     # + full animation per planet

Motion is EXACT ballistic maths from real gravity (deterministic keyframes,
not rigid-body), sampled per frame.  Crushing / suspension sag are faked with
a lattice + shape keys.  See README.md.
Works with Blender 4.2 LTS ... 5.x.
"""

# =============================================================================
# CONFIG
# =============================================================================
PLANETS = ["Pluto", "Moon", "Mars", "Earth", "Jupiter", "Sun"]   # order = scene numbering

GRAVITY = {  # m/s^2 (real surface gravity)
    "Pluto": 0.62, "Moon": 1.62, "Mercury": 3.70, "Mars": 3.71, "Venus": 8.87,
    "Earth": 9.81, "Uranus": 8.69, "Neptune": 11.15, "Saturn": 10.44,
    "Jupiter": 24.79, "Sun": 274.0,
}

# --- the stunt (identical on every planet) ---
LAUNCH_SPEED   = 20.0   # m/s at the ramp lip (72 km/h)
RAMP_ANGLE_DEG = 15.0   # ramp angle
RAMP_HEIGHT    = 1.6    # m, lip height above the cliff top
GAP            = 22.0   # m, canyon width (ramp lip -> far rim)
LANDING_LENGTH = 20.0   # m, length of the far-side mesa (then another, deeper drop)
CANYON_DEPTH   = 28.0   # m
DEEP_DROP      = 60.0   # m, the abyss beyond the landing mesa
CRUSH_G        = 100.0  # m/s^2: above this the car can't hold its own weight -> CRUSHED (faked)
SPACE_AIRTIME  = 5.0    # s: flights longer than this that miss the mesa count as "LOST IN SPACE"
LAUNCH_TIME    = 1.8    # s into the clip when the car leaves the lip

# --- car ---
CAR_MODEL_PATH = ""     # "" = procedural car. Or a .glb/.gltf/.fbx/.blend file with your car.
CAR_MODEL_FORWARD = "+X"  # which axis the imported car's nose points along: +X -X +Y -Y
CAR_MODEL_LENGTH = 4.2  # imported car is rescaled to this length (m); 0 = keep its own scale
CAR_WHEEL_KEYWORDS = ("wheel", "tire", "tyre", "rim")  # imported objects with these names spin
CAR_COLOR = (0.85, 0.08, 0.04)   # procedural body paint (linear RGB)

# --- video ---
FPS        = 30
SECONDS    = 8.0
RESOLUTION = (1080, 1920)      # vertical 9:16
ENGINE     = "EEVEE"           # "EEVEE" or "CYCLES" for --render
CYCLES_SAMPLES = 128
EEVEE_SAMPLES  = 64
MOTION_BLUR = True
OUTPUT_DIR = "//renders/canyon-jump/"   # relative to the .blend (or this script when unsaved)

# --- quick-check stills (always Cycles CPU, low-res) ---
PREVIEW = False
RENDER  = False
PREVIEW_RESOLUTION = (270, 480)
PREVIEW_SAMPLES = 24

HOOK_TEXT = "CAN IT CLEAR\nTHE CANYON?"
# =============================================================================

import bpy
import bmesh
import math
import os
import sys
import random
import time

PFX = "CJ_"          # every datablock this script creates starts with this
SCENE_TAG = "03_"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--preview" in argv:
    PREVIEW = True
if "--render" in argv:
    RENDER = True

THETA = math.radians(RAMP_ANGLE_DEG)
RAMP_LEN = RAMP_HEIGHT / math.tan(THETA)   # horizontal length of the ramp
RIM_NEAR = 0.4                             # cliff edge just past the ramp lip
WHEELBASE = 2.7
HALF_LEN = 2.1
WHEEL_R = 0.36

LOOK = {  # ground, rock, sky_low, sky_high, sun strength, sun colour, stars, emissive ground
    "Pluto":   dict(ground=(0.80, 0.74, 0.66), rock=(0.42, 0.36, 0.33), sky0=(0.020, 0.022, 0.035), sky1=(0.0, 0.0, 0.004), sun=3.2, sunc=(1.0, 0.95, 0.9), stars=True),
    "Moon":    dict(ground=(0.42, 0.42, 0.42), rock=(0.22, 0.22, 0.23), sky0=(0.004, 0.004, 0.006), sky1=(0.0, 0.0, 0.0), sun=4.5, sunc=(1.0, 1.0, 1.0), stars=True),
    "Mercury": dict(ground=(0.40, 0.37, 0.34), rock=(0.22, 0.20, 0.19), sky0=(0.006, 0.005, 0.005), sky1=(0.0, 0.0, 0.0), sun=5.5, sunc=(1.0, 0.98, 0.95), stars=True),
    "Mars":    dict(ground=(0.52, 0.20, 0.08), rock=(0.33, 0.12, 0.05), sky0=(0.85, 0.58, 0.36), sky1=(0.45, 0.30, 0.22), sun=3.0, sunc=(1.0, 0.88, 0.75), stars=False),
    "Venus":   dict(ground=(0.55, 0.42, 0.20), rock=(0.35, 0.25, 0.12), sky0=(0.95, 0.80, 0.40), sky1=(0.75, 0.55, 0.25), sun=1.6, sunc=(1.0, 0.85, 0.55), stars=False),
    "Earth":   dict(ground=(0.12, 0.30, 0.06), rock=(0.55, 0.30, 0.16), sky0=(0.62, 0.78, 0.95), sky1=(0.12, 0.32, 0.78), sun=3.6, sunc=(1.0, 0.96, 0.9), stars=False),
    "Uranus":  dict(ground=(0.50, 0.70, 0.72), rock=(0.30, 0.45, 0.50), sky0=(0.60, 0.85, 0.88), sky1=(0.25, 0.55, 0.65), sun=1.5, sunc=(0.9, 1.0, 1.0), stars=False),
    "Neptune": dict(ground=(0.20, 0.30, 0.65), rock=(0.12, 0.17, 0.40), sky0=(0.35, 0.50, 0.95), sky1=(0.08, 0.15, 0.55), sun=1.4, sunc=(0.85, 0.9, 1.0), stars=False),
    "Saturn":  dict(ground=(0.70, 0.60, 0.40), rock=(0.45, 0.38, 0.25), sky0=(0.95, 0.85, 0.60), sky1=(0.65, 0.55, 0.35), sun=2.0, sunc=(1.0, 0.92, 0.75), stars=False),
    "Jupiter": dict(ground=(0.62, 0.42, 0.24), rock=(0.40, 0.24, 0.13), sky0=(0.90, 0.62, 0.38), sky1=(0.55, 0.32, 0.18), sun=2.6, sunc=(1.0, 0.85, 0.65), stars=False, bands=True),
    "Sun":     dict(ground=(1.00, 0.45, 0.05), rock=(0.35, 0.05, 0.01), sky0=(0.80, 0.30, 0.05), sky1=(0.45, 0.08, 0.01), sun=1.5, sunc=(1.0, 0.7, 0.4), stars=False, emissive=True),
}

VERDICT_STYLE = {
    "CLEARED":       ("CLEARED", "check", (0.10, 0.85, 0.25)),
    "FELL SHORT":    ("FELL SHORT", "cross", (0.95, 0.12, 0.10)),
    "OVERSHOT":      ("OVERSHOT", "cross", (1.00, 0.45, 0.05)),
    "LOST IN SPACE": ("LOST IN SPACE", "rocket", (0.55, 0.35, 1.00)),
    "CRUSHED":       ("CRUSHED", "crush", (0.95, 0.05, 0.05)),
}


# =============================================================================
# Physics: exact ballistic prediction + per-frame motion
# =============================================================================
def predict(g):
    """Closed-form projectile numbers for a launch from the lip (height RAMP_HEIGHT above both rims)."""
    vx, vz = LAUNCH_SPEED * math.cos(THETA), LAUNCH_SPEED * math.sin(THETA)
    t_land = (vz + math.sqrt(vz * vz + 2 * g * RAMP_HEIGHT)) / g     # back to rim level
    rng = vx * t_land
    peak = RAMP_HEIGHT + vz * vz / (2 * g)
    t_gap = GAP / vx
    z_at_far_wall = RAMP_HEIGHT + vz * t_gap - 0.5 * g * t_gap ** 2  # relative to rim level
    if g > CRUSH_G:
        verdict = "CRUSHED"
    elif rng < GAP:
        verdict = "FELL SHORT"
    elif rng <= GAP + LANDING_LENGTH:
        verdict = "CLEARED"
    else:
        # misses the mesa: a long, high flight leaves the frame upward -> space
        verdict = "LOST IN SPACE" if t_land > SPACE_AIRTIME else "OVERSHOT"
    return dict(range=rng, airtime=t_land, peak=peak, z_far_wall=z_at_far_wall,
                verdict=verdict, g_earths=g / 9.81,
                ramp_ok=LAUNCH_SPEED ** 2 >= 2 * g * RAMP_HEIGHT)


def ramp_h(x):
    """Road surface height along the drive path (ramp extended past the lip for pose sampling)."""
    if x < -RAMP_LEN:
        return 0.0
    return (x + RAMP_LEN) * math.tan(THETA)


def simulate(g, fps, n_frames):
    """Returns list of per-frame dicts and an events dict. Integration: exact gravity,
    symplectic sub-steps of 1/(fps*40) s (error vs closed form < 1 cm)."""
    pred = predict(g)
    crush = pred["verdict"] == "CRUSHED"
    v = LAUNCH_SPEED
    path_ramp = RAMP_LEN / math.cos(THETA)
    s_flat = v * LAUNCH_TIME - path_ramp                # flat road driven before the ramp
    x_start = -RAMP_LEN - s_flat

    sub = 40
    dt = 1.0 / (fps * sub)
    st = dict(mode="drive", x=x_start, z=0.0, vx=v, vz=0.0, pitch=0.0, prate=0.0,
              wheel=0.0, omega=v / WHEEL_R, t_event=None, susp_amp=0.0, squash=0.0,
              pancake=0.0, s=0.0, brake=0.0, impact_v=0.0)
    if g > 15:   # heavy planets: suspension sags / bottoms out while driving
        st["squash"] = min(0.35, 0.05 * g / 9.81) if not crush else 0.35
    ev = {}
    frames = []
    t = 0.0
    sag = -min(0.12, 0.03 * g / 9.81)

    def pose_on_path(x):
        zr, zf = ramp_h(x - WHEELBASE / 2), ramp_h(x + WHEELBASE / 2)
        return 0.5 * (zr + zf), math.atan2(zf - zr, WHEELBASE)

    for f in range(n_frames):
        for _ in range(sub if f > 0 else 0):
            t += dt
            m = st["mode"]
            if m == "drive":
                st["s"] += st["vx"] * dt
                s = st["s"]
                if s < s_flat:
                    st["x"] = x_start + s
                else:
                    st["x"] = -RAMP_LEN + (s - s_flat) * math.cos(THETA)
                st["z"], st["pitch"] = pose_on_path(st["x"])
                st["wheel"] += st["vx"] / WHEEL_R * dt
                if crush and st["x"] + WHEELBASE / 2 >= -RAMP_LEN:
                    st["mode"] = "crush"; st["t_event"] = t; ev["crush"] = t
                    ev["crush_x"] = st["x"]
                elif st["x"] >= 0.0:
                    st["mode"] = "flight"; ev["launch"] = t
                    st["vx"], st["vz"] = v * math.cos(THETA), v * math.sin(THETA)
                    st["z"] = RAMP_HEIGHT; st["pitch"] = THETA
            elif m == "crush":
                # pancaked chassis grinds on the ramp: friction mu=0.9 at 274 m/s^2
                te = t - st["t_event"]
                st["pancake"] = min(1.0, te / 0.12)
                decel = 0.9 * g * min(1.0, te / 0.05)
                st["vx"] = max(0.0, st["vx"] - decel * dt)
                st["s"] += st["vx"] * dt
                s = st["s"]
                st["x"] = x_start + s if s < s_flat else -RAMP_LEN + (s - s_flat) * math.cos(THETA)
                st["z"], st["pitch"] = pose_on_path(st["x"])
                st["wheel"] += st["vx"] / WHEEL_R * dt
                if st["vx"] <= 0 and "crush_stop" not in ev:
                    ev["crush_stop"] = t; ev["crush_slide"] = st["x"] - ev["crush_x"]
            elif m in ("flight", "fall", "overshoot"):
                st["vz"] -= g * dt
                st["x"] += st["vx"] * dt
                st["z"] += st["vz"] * dt
                if m == "flight":
                    target = 0.55 * math.atan2(st["vz"], st["vx"])
                    st["pitch"] += (target - st["pitch"]) * min(1.0, dt / 0.35)
                else:
                    st["pitch"] += st["prate"] * dt
                st["omega"] *= math.exp(-dt / 4.0)
                st["wheel"] += st["omega"] * dt
                low = st["z"] - HALF_LEN * abs(math.sin(st["pitch"]))
                x = st["x"]
                if m == "flight" and GAP <= x <= GAP + LANDING_LENGTH and low <= 0.0 and st["vz"] < 0:
                    st["mode"] = "roll"; st["t_event"] = t; ev["land"] = t; ev["land_x"] = x
                    st["impact_v"] = st["vz"]
                    st["susp_amp"] = min(0.22, 0.028 * abs(st["vz"]))
                    st["z"] = 0.0; st["vz"] = 0.0
                    room = (GAP + LANDING_LENGTH - 3.0) - x
                    st["brake"] = st["vx"] ** 2 / (2 * max(room, 1.0))
                    st["prate"] = 0.0
                elif m == "flight" and x + HALF_LEN >= GAP and x < GAP and st["z"] < -0.05:
                    st["mode"] = "fall"; ev["wall"] = t; ev["wall_z"] = st["z"]
                    st["x"] = GAP - HALF_LEN; st["vx"] = -0.8; st["prate"] = -1.2
                    st["squash"] = max(st["squash"], 0.5)
                elif m in ("flight", "fall") and x < GAP and low <= -CANYON_DEPTH:
                    st["mode"] = "wreck"; st["t_event"] = t; ev["floor"] = t
                    st["impact_v"] = st["vz"]; st["p0"] = st["pitch"]
                    st["vx"] = 0.0; st["vz"] = 0.0
                elif m == "flight" and x > GAP + LANDING_LENGTH:
                    st["mode"] = "overshoot"; ev["past_mesa"] = t; st["prate"] = -0.35
                elif m == "overshoot" and st["z"] < -DEEP_DROP:
                    st["vz"] = 0.0; st["vx"] = 0.0; g_eff = 0.0  # noqa: parked off-screen
            elif m == "roll":
                te = t - st["t_event"]
                st["vx"] = max(0.0, st["vx"] - st["brake"] * dt)
                st["x"] += st["vx"] * dt
                st["wheel"] += st["vx"] / WHEEL_R * dt
                # pitch spring back to level (front/rear wheel touch-down)
                st["prate"] += (-80.0 * st["pitch"] - 9.0 * st["prate"]) * dt
                st["pitch"] += st["prate"] * dt
                st["z"] = WHEELBASE / 2 * abs(math.sin(st["pitch"]))
                if st["vx"] <= 0 and "stop" not in ev:
                    ev["stop"] = t; ev["stop_x"] = st["x"]
            elif m == "wreck":
                te = t - st["t_event"]
                k = min(1.0, te / 0.25)
                st["pitch"] = st["p0"] * (1 - k) ** 2 + (-0.12) * (1 - (1 - k) ** 2)
                st["z"] = -CANYON_DEPTH + HALF_LEN * abs(math.sin(st["pitch"])) * 0.6
                st["squash"] = 0.5 + 0.45 * min(1.0, te / 0.08)

        # ------- per-frame derived values -------
        susp = sag if st["mode"] in ("drive",) else 0.0
        squash = st["squash"]
        if st["mode"] == "roll":
            te = t - st["t_event"]
            susp = -st["susp_amp"] * math.exp(-te / 0.28) * math.cos(2 * math.pi * 2.0 * te)
            squash = max(squash, 0.18 * math.exp(-te / 0.12))
        if st["mode"] == "flight":
            susp = 0.05 * (1 - math.exp(-(t - ev["launch"]) / 0.1))  # wheels droop in the air
        if st["mode"] in ("crush",):
            susp = sag
        roll = 0.035 * math.sin(2.1 * t) if st["mode"] in ("flight", "overshoot") else 0.0
        frames.append(dict(t=t, x=st["x"], z=st["z"], pitch=st["pitch"], roll=roll,
                           wheel=st["wheel"], susp=susp, squash=squash,
                           pancake=st["pancake"], mode=st["mode"], vx=st["vx"], vz=st["vz"]))
    return frames, ev, pred


def verdict_time(ev, pred):
    v = pred["verdict"]
    if v == "CRUSHED":
        return ev.get("crush", 1.5) + 0.8
    if v == "CLEARED":
        return ev.get("stop", ev.get("land", 3.0) + 1.0) + 0.3
    if v == "FELL SHORT":
        return ev.get("floor", ev.get("wall", 3.0) + 0.8) + 0.35
    if v == "OVERSHOT":
        return ev.get("past_mesa", 3.5) + 0.5
    return LAUNCH_TIME + 2.7


# =============================================================================
# Helpers
# =============================================================================
def find_engine(want):
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if want.upper().startswith("EEVEE"):
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            if e in items:
                return e
    return "CYCLES"


def out_root():
    if bpy.data.filepath:
        return bpy.path.abspath(OUTPUT_DIR)
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(base):
            raise ValueError
    except Exception:
        base = os.getcwd()
    rel = OUTPUT_DIR[2:] if OUTPUT_DIR.startswith("//") else OUTPUT_DIR
    return os.path.join(base, rel)


def cleanup():
    for sc in list(bpy.data.scenes):
        if sc.name.startswith(SCENE_TAG):
            bpy.data.scenes.remove(sc)
    colls = [bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.lattices,
             bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.worlds,
             bpy.data.actions, bpy.data.collections, bpy.data.shape_keys if hasattr(bpy.data, "shape_keys") else []]
    for c in colls:
        for d in list(c):
            if d.name.startswith(PFX):
                try:
                    c.remove(d)
                except Exception:
                    pass


def new_mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emit=None, emit_strength=0.0,
            coat=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.new(PFX + name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    def setin(names, val):
        for n in names:
            if n in b.inputs:
                b.inputs[n].default_value = val
                return
    setin(["Base Color"], (*color, 1.0))
    setin(["Roughness"], rough)
    setin(["Metallic"], metal)
    if coat:
        setin(["Coat Weight", "Clearcoat"], coat)
    if transmission:
        setin(["Transmission Weight", "Transmission"], transmission)
    if emit is not None:
        setin(["Emission Color", "Emission"], (*emit, 1.0))
        setin(["Emission Strength"], emit_strength)
    if alpha < 1.0:
        setin(["Alpha"], alpha)
    return m


def emit_mat(name, color, strength=1.0, alpha=1.0):
    m = bpy.data.materials.new(PFX + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        if hasattr(m, "blend_method"):
            try:
                m.blend_method = "BLEND"
            except Exception:
                pass
        if hasattr(m, "surface_render_method"):
            try:
                m.surface_render_method = "BLENDED"
            except Exception:
                pass
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mesh_obj(name, bm, mats=(), smooth_angle=None, scene_coll=None):
    me = bpy.data.meshes.new(PFX + name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth_angle is not None:
        for p in me.polygons:
            p.use_smooth = True
        if hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    ob = bpy.data.objects.new(PFX + name, me)
    if scene_coll is not None:
        scene_coll.objects.link(ob)
    return ob


def prism(bm, profile_xz, y0, y1, mat_index=0):
    """Extrude a closed (x,z) polygon along y."""
    a = [bm.verts.new((x, y0, z)) for x, z in profile_xz]
    b = [bm.verts.new((x, y1, z)) for x, z in profile_xz]
    n = len(profile_xz)
    faces = [bm.faces.new(a[::-1]), bm.faces.new(b)]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    for f in faces:
        f.material_index = mat_index
    return faces


def box(bm, c, s, mat_index=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r["verts"]:
        v.co.x = v.co.x * s[0] + c[0]
        v.co.y = v.co.y * s[1] + c[1]
        v.co.z = v.co.z * s[2] + c[2]
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat_index
    return r["verts"]


def add_bevel(ob, width, segs=3, angle=40):
    md = ob.modifiers.new("Bevel", "BEVEL")
    md.width = width
    md.segments = segs
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angle)
    if hasattr(md, "harden_normals"):
        md.harden_normals = False
    return md


def link(ob, coll):
    if ob.name not in coll.objects:
        coll.objects.link(ob)
    return ob


def key(ob, path, frame, index=-1):
    try:
        ob.keyframe_insert(path, index=index, frame=frame)
    except TypeError:
        ob.keyframe_insert(path, frame=frame)


# =============================================================================
# Shared assets (built once, shared by all planet scenes)
# =============================================================================
class Shared:
    pass


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def build_terrain_mesh():
    rnd = random.Random(7)
    waves = [(rnd.uniform(0.05, 0.35), rnd.uniform(0, 6.28), rnd.uniform(0.5, 1.0)) for _ in range(6)]
    def n1(y, seed):
        return sum(a * math.sin(f * y * (1 + 0.3 * seed) + p + seed * 1.7) for f, p, a in waves) / 2.5
    def n2(x, y, seed=0.0):
        return (math.sin(0.11 * x + 1.3 + seed) * math.cos(0.09 * y + 0.4) +
                0.5 * math.sin(0.23 * x - 0.31 * y + 2.0 + seed) +
                0.25 * math.sin(0.61 * x + 0.47 * y + seed * 3))

    # non-uniform x grid: fine near cliff edges
    def frange(a, b, step):
        out, v = [], a
        while v < b:
            out.append(v); v += step
        return out
    edges = [RIM_NEAR, GAP, GAP + LANDING_LENGTH]
    xs = set()
    for x in frange(-100, 150, 0.9):
        xs.add(round(x, 3))
    for e in edges:
        for x in frange(e - 6, e + 6, 0.22):
            xs.add(round(x, 3))
    xs = sorted(xs)
    ys = sorted(set([round(y, 3) for y in frange(-32, 40, 0.55)] + [round(y, 3) for y in frange(40, 170, 1.6)]))

    def height(x, y):
        ay = abs(y)
        amp = smoothstep(3.5, 12, ay) * 2.6
        e1 = RIM_NEAR - amp * (0.6 + n1(y, 0.0))
        e2 = GAP + amp * (0.6 + n1(y, 1.0))
        e3 = GAP + LANDING_LENGTH + amp * 1.3 * (0.6 + n1(y, 2.0))
        # plateau top: flat near the road, bumpy further out, hills behind
        top = smoothstep(4, 9, ay) * 0.25 * n2(x * 3, y * 3)
        top += smoothstep(16, 70, y) * (5.0 + 4.0 * n2(x, y))
        top += smoothstep(95, 160, y) * 38.0 * (0.8 + 0.3 * n2(x * 0.5, y * 0.5, 2.0))
        # canyon carve
        d = min(x - e1, e2 - x)
        wall = 1.4 + 0.6 * smoothstep(5, 30, ay)
        f = 0.0 if d <= 0 else min(1.0, d / wall) ** 0.6
        close = 1.0 - smoothstep(105, 150, y)
        f *= close
        floor = -CANYON_DEPTH + smoothstep(3, 8, ay) * (0.6 * n2(x * 2, y * 2, 1.0) + 0.6) * 1.0
        h = top + (floor - top) * f
        # abyss beyond the landing mesa
        d3 = x - e3
        if d3 > 0:
            f3 = min(1.0, d3 / 2.5) ** 0.6 * close
            h = h + (-DEEP_DROP + 2.0 * n2(x, y) - h) * f3
        # ledges/strata steps on the walls
        if 0 < f < 1:
            h += 0.35 * math.sin(h * 1.7)
        return h

    bm = bmesh.new()
    nx = len(xs)
    vgrid = []
    for y in ys:
        row = [bm.verts.new((x, y, height(x, y))) for x in xs]
        vgrid.append(row)
    for j in range(len(ys) - 1):
        r0, r1 = vgrid[j], vgrid[j + 1]
        for i in range(nx - 1):
            bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))
    me = bpy.data.meshes.new(PFX + "Terrain")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(None)
    return me


def build_rock_meshes():
    out = []
    for k in range(4):
        rnd = random.Random(100 + k)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for v in bm.verts:
            v.co *= rnd.uniform(0.8, 1.15)
            v.co.z *= 0.7
        bmesh.ops.bevel(bm, geom=list(bm.edges)[:0], offset=0.0) if False else None
        me = bpy.data.meshes.new(PFX + "Rock%d" % k)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(None)
        out.append(me)
    return out


def build_shared():
    S = Shared()
    S.mats = dict(
        paint=new_mat("CarPaint", CAR_COLOR, rough=0.25, coat=1.0),
        trim=new_mat("CarTrim", (0.02, 0.02, 0.022), rough=0.45),
        glass=new_mat("CarGlass", (0.02, 0.03, 0.05), rough=0.03, metal=0.3),
        stripe=new_mat("CarStripe", (0.9, 0.9, 0.88), rough=0.3, coat=1.0),
        rubber=new_mat("Tyre", (0.025, 0.025, 0.025), rough=0.85),
        rim=new_mat("Rim", (0.85, 0.86, 0.9), rough=0.18, metal=1.0),
        head=emit_mat("HeadLight", (1.0, 0.95, 0.8), 12.0),
        tail=emit_mat("TailLight", (1.0, 0.03, 0.02), 6.0),
        asphalt=new_mat("Asphalt", (0.035, 0.035, 0.04), rough=0.9),
        paintline=emit_mat("RoadLine", (0.95, 0.9, 0.7), 0.9),
        ramp=new_mat("RampTop", (0.5, 0.5, 0.52), rough=0.35, metal=0.9),
        cone=new_mat("Cone", (1.0, 0.25, 0.02), rough=0.5),
        white=new_mat("White", (0.9, 0.9, 0.9), rough=0.5),
        marker=emit_mat("Marker", (1.0, 1.0, 1.0), 2.5),
    )
    S.mats["ramp_side"] = stripes_mat()
    S.mats["checker"] = checker_mat()
    S.terrain = build_terrain_mesh()
    S.rocks = build_rock_meshes()
    S.car_parts = build_car_meshes(S.mats) if not CAR_MODEL_PATH else None
    S.imported = import_car_model() if CAR_MODEL_PATH else None
    return S


def stripes_mat():
    m = new_mat("RampStripes", (1, 0.8, 0), rough=0.5)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mth = nt.nodes.new("ShaderNodeMath"); mth.operation = "ADD"
    sc = nt.nodes.new("ShaderNodeMath"); sc.operation = "MULTIPLY"; sc.inputs[1].default_value = 1.6
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = 0.5
    mix = nt.nodes.new("ShaderNodeMix") if bpy.app.version >= (3, 4, 0) else None
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs[0], mth.inputs[0]); nt.links.new(sep.outputs[2], mth.inputs[1])
    nt.links.new(mth.outputs[0], sc.inputs[0]); nt.links.new(sc.outputs[0], fr.inputs[0])
    nt.links.new(fr.outputs[0], gt.inputs[0])
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (1.0, 0.72, 0.0, 1)
    mix.inputs["B"].default_value = (0.02, 0.02, 0.02, 1)
    nt.links.new(gt.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def checker_mat():
    m = new_mat("Checker", (1, 1, 1), rough=0.6)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 1.0
    ck.inputs["Color1"].default_value = (0.9, 0.9, 0.9, 1)
    ck.inputs["Color2"].default_value = (0.02, 0.02, 0.02, 1)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.25, 1.25, 1.25)
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    nt.links.new(mp.outputs[0], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], b.inputs["Base Color"])
    return m


def terrain_mat(planet):
    L = LOOK[planet]
    m = bpy.data.materials.new(PFX + "Ground_" + planet)
    m.use_nodes = True
    nt = m.node_tree
    N, Lk = nt.nodes, nt.links
    b = N.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 0.92
    geo = N.new("ShaderNodeNewGeometry")
    sepn = N.new("ShaderNodeSeparateXYZ")
    Lk.new(geo.outputs["Normal"], sepn.inputs[0])
    flat = N.new("ShaderNodeMapRange")
    flat.inputs["From Min"].default_value = 0.45
    flat.inputs["From Max"].default_value = 0.7
    Lk.new(sepn.outputs[2], flat.inputs["Value"])
    tc = N.new("ShaderNodeTexCoord")
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.35
    noise.inputs["Detail"].default_value = 8.0
    Lk.new(tc.outputs["Object"], noise.inputs["Vector"])
    # strata: bands along Z for the cliff walls
    wave = N.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 0.06
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    Lk.new(tc.outputs["Object"], wave.inputs["Vector"])
    rock_ramp = N.new("ShaderNodeValToRGB")
    r = L["rock"]
    rock_ramp.color_ramp.elements[0].color = (r[0] * 0.75, r[1] * 0.75, r[2] * 0.75, 1)
    rock_ramp.color_ramp.elements[1].color = (min(1, r[0] * 1.25), min(1, r[1] * 1.25), min(1, r[2] * 1.25), 1)
    Lk.new(wave.outputs["Fac"], rock_ramp.inputs["Fac"])
    gnd_ramp = N.new("ShaderNodeValToRGB")
    gcol = L["ground"]
    gnd_ramp.color_ramp.elements[0].color = (gcol[0] * 0.6, gcol[1] * 0.6, gcol[2] * 0.6, 1)
    gnd_ramp.color_ramp.elements[1].color = (min(1, gcol[0] * 1.25), min(1, gcol[1] * 1.25), min(1, gcol[2] * 1.25), 1)
    Lk.new(noise.outputs["Fac"], gnd_ramp.inputs["Fac"])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    Lk.new(flat.outputs["Result"], mix.inputs["Factor"])
    Lk.new(rock_ramp.outputs["Color"], mix.inputs["A"])
    Lk.new(gnd_ramp.outputs["Color"], mix.inputs["B"])
    Lk.new(mix.outputs["Result"], b.inputs["Base Color"])
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    n2 = N.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 3.0
    n2.inputs["Detail"].default_value = 6.0
    Lk.new(tc.outputs["Object"], n2.inputs["Vector"])
    Lk.new(n2.outputs["Fac"], bump.inputs["Height"])
    Lk.new(bump.outputs["Normal"], b.inputs["Normal"])
    if L.get("emissive"):
        # glowing photosphere: hot granules on top, dark crust with glowing seams on walls
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 0.6
        Lk.new(tc.outputs["Object"], vor.inputs["Vector"])
        er = N.new("ShaderNodeValToRGB")
        er.color_ramp.elements[0].color = (1.0, 0.85, 0.3, 1)
        er.color_ramp.elements[1].color = (0.9, 0.25, 0.02, 1)
        Lk.new(vor.outputs["Distance"], er.inputs["Fac"])
        st = N.new("ShaderNodeMath"); st.operation = "MULTIPLY"; st.inputs[1].default_value = 1.1
        Lk.new(flat.outputs["Result"], st.inputs[0])
        Lk.new(er.outputs["Color"], b.inputs["Emission Color"])
        Lk.new(st.outputs[0], b.inputs["Emission Strength"])
    return m


def rock_mat(planet):
    L = LOOK[planet]
    m = new_mat("Rock_" + planet, L["rock"], rough=0.95)
    if L.get("emissive"):
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Color"].default_value = (1.0, 0.3, 0.02, 1)
        b.inputs["Emission Strength"].default_value = 0.6
    return m


def build_world(planet):
    L = LOOK[planet]
    w = bpy.data.worlds.new(PFX + "Sky_" + planet)
    w.use_nodes = True
    nt = w.node_tree
    N, Lk = nt.nodes, nt.links
    bg = N.get("Background")
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    Lk.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*L["sky0"], 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (*L["sky1"], 1)
    Lk.new(sep.outputs[2], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    if L.get("bands"):
        wave = N.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"; wave.bands_direction = "Z"
        wave.inputs["Scale"].default_value = 2.2
        wave.inputs["Distortion"].default_value = 3.0
        wave.inputs["Detail"].default_value = 2.0
        Lk.new(tc.outputs["Generated"], wave.inputs["Vector"])
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 0.45
        br = N.new("ShaderNodeValToRGB")
        br.color_ramp.elements[0].color = (0.75, 0.55, 0.45, 1)
        br.color_ramp.elements[1].color = (1.0, 0.95, 0.85, 1)
        Lk.new(wave.outputs["Fac"], br.inputs["Fac"])
        Lk.new(col, mix.inputs["A"]); Lk.new(br.outputs["Color"], mix.inputs["B"])
        col = mix.outputs["Result"]
    if L.get("stars"):
        vor = N.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 260.0
        Lk.new(tc.outputs["Generated"], vor.inputs["Vector"])
        thr = N.new("ShaderNodeMapRange")
        thr.inputs["From Min"].default_value = 0.06
        thr.inputs["From Max"].default_value = 0.0
        thr.inputs["To Max"].default_value = 3.0
        Lk.new(vor.outputs["Distance"], thr.inputs["Value"])
        add = N.new("ShaderNodeMix"); add.data_type = "RGBA"; add.blend_type = "ADD"
        add.inputs["Factor"].default_value = 1.0
        Lk.new(col, add.inputs["A"])
        Lk.new(thr.outputs["Result"], add.inputs["B"])
        col = add.outputs["Result"]
    Lk.new(col, bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0 if not L.get("stars") else 1.0
    return w


# =============================================================================
# Car
# =============================================================================
def build_car_meshes(M):
    parts = {}
    # body side profile (x forward, z up), origin = ground under car centre
    prof = [(-2.10, 0.30), (2.08, 0.30), (2.14, 0.48), (2.06, 0.70), (1.75, 0.80),
            (0.85, 0.90), (-1.75, 0.95), (-2.08, 0.92), (-2.14, 0.62)]
    bm = bmesh.new()
    prism(bm, prof, -0.90, 0.90, 0)
    # lower trim / skirt
    prism(bm, [(-2.05, 0.24), (2.0, 0.24), (2.05, 0.40), (-2.1, 0.40)], -0.92, 0.92, 1)
    # rear spoiler
    box(bm, (-1.95, 0.0, 1.13), (0.32, 1.7, 0.05), 0)
    box(bm, (-1.88, 0.55, 1.03), (0.12, 0.06, 0.18), 1)
    box(bm, (-1.88, -0.55, 1.03), (0.12, 0.06, 0.18), 1)
    # bumpers / grille
    box(bm, (2.11, 0.0, 0.42), (0.12, 1.5, 0.14), 1)
    box(bm, (-2.13, 0.0, 0.42), (0.10, 1.6, 0.14), 1)
    parts["body"] = mesh_obj("CarBody", bm, (M["paint"], M["trim"]), smooth_angle=35)
    add_bevel(parts["body"], 0.05, 3)

    bm = bmesh.new()   # cabin glass
    prism(bm, [(0.78, 0.88), (-0.05, 1.33), (-1.20, 1.33), (-1.68, 0.92)], -0.76, 0.76, 0)
    parts["glass"] = mesh_obj("CarGlass", bm, (M["glass"],), smooth_angle=30)
    add_bevel(parts["glass"], 0.06, 3)

    bm = bmesh.new()   # roof + racing stripes
    prism(bm, [(0.02, 1.32), (-1.18, 1.32), (-1.16, 1.37), (0.0, 1.37)], -0.70, 0.70, 0)
    box(bm, (0.55, 0.0, 0.875), (2.6, 0.32, 0.06), 1)
    parts["roof"] = mesh_obj("CarRoof", bm, (M["paint"], M["stripe"]), smooth_angle=30)
    add_bevel(parts["roof"], 0.02, 2)

    bm = bmesh.new()   # headlights + taillights
    for y in (-0.62, 0.62):
        box(bm, (2.08, y, 0.62), (0.08, 0.38, 0.10), 0)
        box(bm, (-2.13, y, 0.78), (0.06, 0.40, 0.08), 1)
    parts["lights"] = mesh_obj("CarLights", bm, (M["head"], M["tail"]))

    # wheel: tyre + 5-spoke rim (spokes make the spin readable)
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=WHEEL_R, radius2=WHEEL_R, depth=0.28)
    for f in bm.faces:
        f.material_index = 0
    r2 = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=0.235, radius2=0.235, depth=0.30)
    rimverts = set(r2["verts"])
    for f in bm.faces:
        if set(f.verts) <= rimverts:
            f.material_index = 1
    for k in range(5):
        a = 2 * math.pi * k / 5
        vs = box(bm, (0, 0, 0), (0.07, 0.07, 0.44), 2)
        for v in vs:
            x, z = v.co.x, v.co.z + 0.11
            v.co.x = x * math.cos(a) - z * math.sin(a)
            v.co.y = z * math.cos(a) + x * math.sin(a)
            v.co.z = 0.16
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                     matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "X"))
    # after rotation the cylinder axis is Y; spokes sit on +Y side? mirror for left wheels at runtime
    parts["wheel"] = mesh_obj("Wheel", bm, (M["rubber"], M["trim"], M["rim"]), smooth_angle=40)
    add_bevel(parts["wheel"], 0.03, 2)
    return parts


def import_car_model():
    """Import the owner's car once into a hidden collection; normalised to CAR_MODEL_LENGTH."""
    path = bpy.path.abspath(CAR_MODEL_PATH)
    if not os.path.isfile(path):
        print("[canyon] CAR_MODEL_PATH not found:", path, "- using procedural car")
        return None
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=path)
        elif ext == ".blend":
            with bpy.data.libraries.load(path, link=False) as (src, dst):
                dst.objects = list(src.objects)
            for o in dst.objects:
                if o is not None:
                    bpy.context.scene.collection.objects.link(o)
        else:
            print("[canyon] unsupported car format", ext); return None
    except Exception as e:
        print("[canyon] car import failed:", e, "- using procedural car")
        return None
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        o.name = PFX + "Imp_" + o.name
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        print("[canyon] no meshes in car file"); return None
    import mathutils
    rot = {"+X": 0.0, "-X": math.pi, "+Y": -math.pi / 2, "-Y": math.pi / 2}.get(CAR_MODEL_FORWARD, 0.0)
    R = mathutils.Matrix.Rotation(rot, 4, "Z")
    pts = []
    for o in meshes:
        mw = o.matrix_world
        pts += [R @ (mw @ mathutils.Vector(c)) for c in o.bound_box]
    mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
    mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
    length = mx.x - mn.x
    s = CAR_MODEL_LENGTH / length if CAR_MODEL_LENGTH and length > 1e-6 else 1.0
    centre = mathutils.Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    norm = mathutils.Matrix.Scale(s, 4) @ mathutils.Matrix.Translation(-centre) @ R
    roots = [o for o in new if o.parent is None or o.parent not in new]
    for o in roots:
        o.matrix_world = norm @ o.matrix_world
    return dict(objects=new, roots=roots, scale=s)


def build_car(scene, S, planet):
    """Hierarchy: Root (path + pitch) -> Susp (bounce) -> body parts; Root -> wheel pivots.
    A lattice parented to Root deforms everything for sag / squash / pancake (faked crushing)."""
    coll = scene.collection
    root = link(bpy.data.objects.new(PFX + "Car_" + planet, None), coll)
    root.empty_display_type = "ARROWS"
    root.rotation_mode = "XYZ"
    susp = link(bpy.data.objects.new(PFX + "Susp_" + planet, None), coll)
    susp.parent = root
    # lattice (bottom stays on the ground, top layer moves)
    lat = bpy.data.lattices.new(PFX + "Lattice_" + planet)
    lat.points_u, lat.points_v, lat.points_w = 3, 2, 2
    lat_ob = link(bpy.data.objects.new(PFX + "CrushLattice_" + planet, lat), coll)
    lat_ob.parent = root
    lat_ob.location = (0, 0, 0.75)
    lat_ob.scale = (4.9, 2.3, 1.6)
    lat_ob.hide_render = True
    lat_ob.shape_key_add(name="Basis")
    for name, ztop, sx, sy, bulge in (("Squash", 0.62, 1.03, 1.06, 0.0), ("Pancake", 0.10, 1.15, 1.32, 0.0)):
        kb = lat_ob.shape_key_add(name=name, from_mix=False)
        for p, d in zip(lat.points, kb.data):
            co = p.co.copy()
            # co in [-0.5, 0.5]; bottom (w=-0.5) stays
            co.x *= sx; co.y *= sy
            if co.z > 0:
                co.z = -0.5 + (co.z + 0.5) * ztop
            d.co = co
    mods_targets = []
    wheels = []
    if S.imported:
        import mathutils
        for o in S.imported["objects"]:
            c = o.copy()
            if c.data is not None and o.type == "MESH":
                pass
            link(c, coll)
            c["src"] = o.name
        mapping = {o.name: c for o in S.imported["objects"] for c in coll.objects if c.get("src") == o.name}
        for o in S.imported["objects"]:
            c = mapping[o.name]
            if o.parent in S.imported["objects"]:
                c.parent = mapping[o.parent.name]
                c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
        for o in S.imported["roots"]:
            c = mapping[o.name]
            mw = o.matrix_world.copy()
            c.parent = susp
            c.matrix_parent_inverse = mathutils.Matrix.Identity(4)
            c.matrix_world = mw
        for o in S.imported["objects"]:
            c = mapping[o.name]
            if c.type == "MESH":
                mods_targets.append(c)
            if any(k in o.name.lower() for k in CAR_WHEEL_KEYWORDS) and c.type == "MESH":
                # spin around its own bbox centre, axis = car's Y
                mw = o.matrix_world
                pts = [mw @ mathutils.Vector(b) for b in o.bound_box]
                cen = sum(pts, mathutils.Vector()) / 8
                piv = link(bpy.data.objects.new(PFX + "WheelPivot_" + planet, None), coll)
                piv.parent = root
                piv.location = cen
                piv.rotation_mode = "XYZ"
                wmw = c.matrix_world.copy()
                c.parent = piv
                c.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                c.matrix_world = mathutils.Matrix.Translation(cen) @ (mathutils.Matrix.Translation(-cen) @ wmw)
                c.matrix_parent_inverse = piv.matrix_world.inverted() if False else mathutils.Matrix.Translation(-cen)
                c.matrix_basis = wmw
                wheels.append(piv)
    else:
        P = S.car_parts
        for k in ("body", "glass", "roof", "lights"):
            o = link(bpy.data.objects.new(PFX + k + "_" + planet, P[k].data), coll)
            for md in P[k].modifiers:
                nm = o.modifiers.new(md.name, md.type)
                nm.width, nm.segments, nm.limit_method, nm.angle_limit = md.width, md.segments, md.limit_method, md.angle_limit
            o.parent = susp
            mods_targets.append(o)
        for (x, y) in ((1.35, 0.84), (1.35, -0.84), (-1.35, 0.84), (-1.35, -0.84)):
            piv = link(bpy.data.objects.new(PFX + "WheelPivot_" + planet, None), coll)
            piv.parent = root
            piv.location = (x, y, WHEEL_R)
            piv.rotation_mode = "XYZ"
            w = link(bpy.data.objects.new(PFX + "Wheel_" + planet, P["wheel"].data), coll)
            md = P["wheel"].modifiers[0]
            nm = w.modifiers.new("Bevel", "BEVEL"); nm.width, nm.segments = md.width, md.segments
            nm.limit_method, nm.angle_limit = md.limit_method, md.angle_limit
            w.parent = piv
            if y < 0:   # rim face outward on the camera side
                w.scale = (1, -1, 1)
            mods_targets.append(w)
            wheels.append(piv)
    for o in mods_targets:
        md = o.modifiers.new("Crush", "LATTICE")
        md.object = lat_ob
    return dict(root=root, susp=susp, lattice=lat_ob, wheels=wheels)


# =============================================================================
# Scene dressing
# =============================================================================
def build_props(scene, S, planet):
    coll = scene.collection
    M = S.mats
    # terrain
    t = link(bpy.data.objects.new(PFX + "Terrain_" + planet, S.terrain), coll)
    t.material_slots[0].link = "OBJECT"
    t.material_slots[0].material = terrain_mat(planet)
    rmat = rock_mat(planet)
    # road (near side + landing mesa)
    bm = bmesh.new()
    box(bm, ((-100 - RAMP_LEN) / 2, 0, 0.005), (100 - RAMP_LEN, 4.6, 0.02), 0)
    box(bm, (GAP + LANDING_LENGTH / 2 + 0.3, 0, 0.005), (LANDING_LENGTH - 0.6, 4.6, 0.02), 0)
    x = -100
    while x < -RAMP_LEN - 2:
        box(bm, (x, 0, 0.018), (2.0, 0.14, 0.01), 1); x += 5
    for side in (-2.1, 2.1):
        box(bm, ((-100 - RAMP_LEN) / 2, side, 0.018), (100 - RAMP_LEN, 0.1, 0.01), 1)
    road = mesh_obj("Road_" + planet, bm, (M["asphalt"], M["paintline"]), scene_coll=coll)
    # landing pad checker
    bm = bmesh.new()
    box(bm, (GAP + 3.0, 0, 0.022), (4.0, 4.0, 0.012), 0)
    mesh_obj("LandingPad_" + planet, bm, (M["checker"],), scene_coll=coll)
    # ramp wedge
    bm = bmesh.new()
    prism(bm, [(-RAMP_LEN, 0.0), (0.0, 0.0), (0.0, RAMP_HEIGHT), (-0.15, RAMP_HEIGHT + 0.0)], -1.5, 1.5, 1)
    for f in bm.faces:   # top face = metal
        if f.normal.z > 0.5:
            f.material_index = 0
    ramp = mesh_obj("Ramp_" + planet, bm, (M["ramp"], M["ramp_side"]), scene_coll=coll)
    add_bevel(ramp, 0.03, 2)
    # traffic cones: at ramp entry and at the end of the landing mesa
    cone_bm = bmesh.new()
    bmesh.ops.create_cone(cone_bm, cap_ends=True, segments=20, radius1=0.2, radius2=0.03, depth=0.7)
    for v in cone_bm.verts:
        v.co.z += 0.37
    box(cone_bm, (0, 0, 0.02), (0.45, 0.45, 0.04), 0)
    cone_me = bpy.data.meshes.new(PFX + "Cone_" + planet)
    cone_bm.to_mesh(cone_me); cone_bm.free()
    cone_me.materials.append(M["cone"])
    for (cx, cy) in ((-RAMP_LEN - 1, -2.6), (-RAMP_LEN - 1, 2.6), (-RAMP_LEN - 6, -2.6),
                     (GAP + LANDING_LENGTH - 1.2, -1.6), (GAP + LANDING_LENGTH - 1.2, 0.0),
                     (GAP + LANDING_LENGTH - 1.2, 1.6), (GAP + 0.8, -2.6), (GAP + 0.8, 2.6)):
        c = link(bpy.data.objects.new(PFX + "ConeObj_" + planet, cone_me), coll)
        c.location = (cx, cy, 0.0)
    # gap measuring line (dashed) + label, on the camera side of the road
    bm = bmesh.new()
    yl = -3.2
    n = 22
    for i in range(n):
        x0 = RIM_NEAR * 0 + i * GAP / n
        box(bm, (x0 + GAP / n * 0.3, yl, 0.15), (GAP / n * 0.55, 0.06, 0.06), 0)
    for xe in (0.0, GAP):
        box(bm, (xe, yl, 0.15), (0.08, 0.06, 1.0), 0)
    mesh_obj("GapLine_" + planet, bm, (M["marker"],), scene_coll=coll)
    txt = make_text(coll, "GapText_" + planet, "GAP: %g m" % GAP, size=1.6, mat=M["marker"])
    txt.location = (GAP / 2, yl, 0.75)
    txt.rotation_euler = (math.radians(90), 0, 0)
    # rocks
    rnd = random.Random(42)
    placed = 0
    tries = 0
    while placed < 70 and tries < 2000:
        tries += 1
        zone = rnd.random()
        if zone < 0.5:
            x = rnd.uniform(2.5, GAP - 2.5); y = rnd.uniform(-6, 70); z = -CANYON_DEPTH
            if abs(y) < 4.5:
                continue
            s = rnd.uniform(0.6, 2.4)
        elif zone < 0.8:
            x = rnd.uniform(-60, -RAMP_LEN - 3) if rnd.random() < 0.6 else rnd.uniform(GAP + 2, GAP + LANDING_LENGTH - 2)
            y = rnd.choice([-1, 1]) * rnd.uniform(5.5, 16)
            if y < -9:
                continue
            z = 0.0; s = rnd.uniform(0.25, 1.0)
        else:
            x = rnd.uniform(-60, 120); y = rnd.uniform(18, 60); z = None; s = rnd.uniform(1.0, 3.0)
        ob = link(bpy.data.objects.new(PFX + "Rock_" + planet, S.rocks[placed % 4]), coll)
        if z is None:
            z = 4.0
        ob.location = (x, y, z - 0.25 * s)
        ob.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6.28))
        ob.scale = (s * rnd.uniform(0.8, 1.4), s, s * rnd.uniform(0.6, 1.0))
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = rmat
        placed += 1
    # lights
    L = LOOK[planet]
    sun_d = bpy.data.lights.new(PFX + "SunLight_" + planet, "SUN")
    sun_d.energy = L["sun"]
    sun_d.color = L["sunc"]
    sun_d.angle = math.radians(2.0 if L.get("stars") else 4.0)
    sun = link(bpy.data.objects.new(PFX + "SunLight_" + planet, sun_d), coll)
    sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-35))


def drop_rocks_on_terrain(scene):
    pass


def make_text(coll, name, body, size=1.0, mat=None, align="CENTER", font=None):
    cu = bpy.data.curves.new(PFX + name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = 0.0
    if font is not None:
        cu.font = font
    ob = link(bpy.data.objects.new(PFX + name, cu), coll)
    if mat:
        cu.materials.append(mat)
    return ob


_FONT = [None]


def load_font():
    if _FONT[0] is not None:
        return _FONT[0]
    cands = [
        "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    f = None
    for c in cands:
        if os.path.isfile(c):
            try:
                f = bpy.data.fonts.load(c, check_existing=True); break
            except Exception:
                pass
    _FONT[0] = f or False
    return _FONT[0]


def fit_text(scene, ob, max_w, max_h=None):
    vl = scene.view_layers[0]
    vl.update()
    ev = ob.evaluated_get(vl.depsgraph)
    xs = [v[0] for v in ev.bound_box]
    ys = [v[1] for v in ev.bound_box]
    w = (max(xs) - min(xs)) or 1e-3
    h = (max(ys) - min(ys)) or 1e-3
    s = max_w / w
    if max_h:
        s = min(s, max_h / h)
    s = min(s, 1.0)
    ob.scale = (s, s, s)
    return w * s, h * s


def icon_mesh(kind, color_mat, coll, name):
    bm = bmesh.new()
    import mathutils
    def bar(x0, y0, x1, y1, th):
        vs = box(bm, (0, 0, 0), (1, th, 0.02), 0)
        L = math.hypot(x1 - x0, y1 - y0)
        a = math.atan2(y1 - y0, x1 - x0)
        for v in vs:
            x, y = v.co.x * L, v.co.y
            v.co.x = (x0 + x1) / 2 + x * math.cos(a) - y * math.sin(a)
            v.co.y = (y0 + y1) / 2 + x * math.sin(a) + y * math.cos(a)
    if kind == "check":
        bar(-0.45, 0.0, -0.12, -0.35, 0.2); bar(-0.19, -0.37, 0.5, 0.42, 0.2)
    elif kind == "cross":
        bar(-0.4, -0.4, 0.4, 0.4, 0.2); bar(-0.4, 0.4, 0.4, -0.4, 0.2)
    elif kind == "rocket":
        # body + nose + fins + flame, pointing up-right
        pts = [(-0.12, -0.3), (0.12, -0.3), (0.12, 0.2), (0.0, 0.48), (-0.12, 0.2)]
        vs = [bm.verts.new((x, y, 0)) for x, y in pts]
        bm.faces.new(vs)
        for sx in (-1, 1):
            f = [bm.verts.new((sx * 0.12, -0.05, 0)), bm.verts.new((sx * 0.28, -0.35, 0)), bm.verts.new((sx * 0.12, -0.3, 0))]
            bm.faces.new(f if sx > 0 else f[::-1])
        fl = [bm.verts.new((-0.08, -0.34, 0)), bm.verts.new((0.0, -0.55, 0)), bm.verts.new((0.08, -0.34, 0))]
        bm.faces.new(fl[::-1])
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=mathutils.Matrix.Rotation(-0.6, 3, "Z"))
    else:  # crush: downward arrow onto a flat bar
        bar(-0.45, -0.38, 0.45, -0.38, 0.12)
        pts = [(-0.1, 0.45), (0.1, 0.45), (0.1, 0.0), (0.28, 0.0), (0.0, -0.25), (-0.28, 0.0), (-0.1, 0.0)]
        vs = [bm.verts.new((x, y, 0)) for x, y in pts]
        bm.faces.new(vs[::-1])
    return mesh_obj(name, bm, (color_mat,), scene_coll=coll)


def build_hud(scene, cam, planet, pred, ev, sim_numbers, t_verdict, fps):
    """Text in camera space at 1 m in front of the lens (frame is 0.84 x 1.5 at that distance)."""
    coll = scene.collection
    font = load_font() or None
    white = emit_mat("HudWhite_" + planet, (1, 1, 1), 1.0)
    shadow = emit_mat("HudShadow_" + planet, (0, 0, 0), 0.0, alpha=0.55)
    vname, icon_kind, vcol = VERDICT_STYLE[pred["verdict"]]
    vmat = emit_mat("HudVerdict_" + planet, vcol, 1.0)
    plate_mat = emit_mat("HudPlate_" + planet, (0.0, 0.0, 0.0), 0.0, alpha=0.82)
    hw = 0.42 * 0.93
    items = []

    def hud_text(name, body, y, w, h=None, mat=white, shadow_on=True, parent=None, x=0.0):
        ob = make_text(coll, name + "_" + planet, body, size=0.1, mat=mat, font=font)
        ob.parent = parent or cam
        ob.location = (x, y, -1.0)
        fit_text(scene, ob, w, h)
        if shadow_on:
            sh = make_text(coll, name + "Sh_" + planet, body, size=0.1, mat=shadow, font=font)
            sh.parent = ob.parent
            sh.scale = ob.scale
            sh.location = (x + 0.006, y - 0.006, -1.001)
        return ob

    hud_text("Hook", HOOK_TEXT, 0.60, 2 * hw, 0.20)
    hud_text("Planet", planet.upper() + " \u00b7 %.2f m/s\u00b2" % GRAVITY[planet], 0.425, 2 * hw, 0.075)
    hud_text("Specs", "same car \u00b7 %d km/h \u00b7 %g\u00b0 ramp \u00b7 %g m gap" %
             (round(LAUNCH_SPEED * 3.6), RAMP_ANGLE_DEG, GAP), -0.68, 2 * hw * 0.9, 0.03)
    bm = bmesh.new()
    box(bm, (0, -0.68, -1.004), (0.86, 0.06, 0.001), 0)
    strip = mesh_obj("SpecsPlate_" + planet, bm, (plate_mat,), scene_coll=coll)
    strip.parent = cam
    # verdict card (pops in)
    card = link(bpy.data.objects.new(PFX + "VerdictCard_" + planet, None), coll)
    card.parent = cam
    card.location = (0, 0.12, -1.0)
    bm = bmesh.new()
    box(bm, (0, 0, -0.004), (0.80, 0.30, 0.001), 0)
    plate = mesh_obj("VerdictPlate_" + planet, bm, (plate_mat,), scene_coll=coll)
    plate.parent = card
    bm = bmesh.new()
    box(bm, (0, 0.14, -0.003), (0.80, 0.018, 0.001), 0)
    box(bm, (0, -0.14, -0.003), (0.80, 0.018, 0.001), 0)
    bars = mesh_obj("VerdictBars_" + planet, bm, (vmat,), scene_coll=coll)
    bars.parent = card
    vt = make_text(coll, "VerdictText_" + planet, vname, size=0.1, mat=vmat, font=font)
    vt.parent = card
    w, h = fit_text(scene, vt, 0.56, 0.11)
    icon = icon_mesh(icon_kind, vmat, coll, "VerdictIcon_" + planet)
    icon.parent = card
    isz = min(0.12, h * 1.25)
    icon.scale = (isz, isz, isz)
    total = w + 0.03 + isz
    vt.location = (-total / 2 + w / 2, 0.035, 0)
    icon.location = (total / 2 - isz / 2, 0.035, 0)
    sub = make_text(coll, "VerdictSub_" + planet, sim_numbers, size=0.1, mat=white, font=font)
    sub.parent = card
    sub.location = (0, -0.075, 0)
    fit_text(scene, sub, 0.70, 0.04)
    fv = round(t_verdict * fps) + 1
    for f, s in ((1, 0.3), (fv - 1, 0.3), (fv + 3, 1.15), (fv + 6, 1.0)):
        card.scale = (s, s, s)
        key(card, "scale", f)
    for o in (plate, bars, vt, icon, sub):
        for f, hid in ((1, True), (fv - 1, True), (fv, False)):
            o.hide_render = hid
            o.hide_viewport = hid
            key(o, "hide_render", f)
            key(o, "hide_viewport", f)


# =============================================================================
# Build one planet scene
# =============================================================================
def build_scene(planet, S, preview):
    g = GRAVITY[planet]
    idx = PLANETS.index(planet) + 1
    sc = bpy.data.scenes.new(SCENE_TAG + planet)
    sc.render.fps = FPS
    n_frames = int(round(SECONDS * FPS))
    sc.frame_start, sc.frame_end = 1, n_frames
    sc.world = build_world(planet)
    build_props(sc, S, planet)
    car = build_car(sc, S, planet)

    frames, ev, pred = simulate(g, FPS, n_frames)
    # car keyframes
    root, susp, lat = car["root"], car["susp"], car["lattice"]
    kb = lat.data.shape_keys.key_blocks
    for i, st in enumerate(frames):
        f = i + 1
        root.location = (st["x"], 0.0, st["z"])
        root.rotation_euler = (st["roll"], -st["pitch"], 0.0)
        key(root, "location", f); key(root, "rotation_euler", f)
        susp.location = (0, 0, st["susp"])
        key(susp, "location", f, 2)
        for w in car["wheels"]:
            w.rotation_euler = (0, st["wheel"], 0)
            key(w, "rotation_euler", f, 1)
        kb["Squash"].value = st["squash"]; kb["Squash"].keyframe_insert("value", frame=f)
        kb["Pancake"].value = st["pancake"]; kb["Pancake"].keyframe_insert("value", frame=f)

    # camera: side view, follows with lag, clamped so the overshooters leave the frame
    cam_d = bpy.data.cameras.new(PFX + "Cam_" + planet)
    cam_d.lens = 24
    cam_d.sensor_fit = "AUTO"
    cam_d.clip_start = 0.05
    cam_d.clip_end = 1000
    cam = link(bpy.data.objects.new(PFX + "Cam_" + planet, cam_d), sc.collection)
    sc.camera = cam
    cam.rotation_euler = (math.radians(75), 0, 0)
    DIST = 15.0
    cx = cz = None
    shake_events = [ev[k] for k in ("land", "wall", "floor", "crush") if k in ev]
    rnd = random.Random(3)
    dt = 1.0 / FPS
    for i, st in enumerate(frames):
        x_lim = GAP + LANDING_LENGTH + 5.0
        tx = min(st["x"] + 0.12 * st["vx"], x_lim)
        zmin = -CANYON_DEPTH + 9.0 if st["x"] < GAP else -2.0
        tz = max(min(st["z"], 6.0), zmin)
        if cx is None:
            cx, cz = tx, tz
        cx += (tx - cx) * (1 - math.exp(-dt / 0.10))
        cz += (tz - cz) * (1 - math.exp(-dt / 0.22))
        sx = sz = 0.0
        for te in shake_events:
            a = st["t"] - te
            if 0 <= a < 0.6:
                amp = 0.25 * math.exp(-a / 0.15)
                sx += amp * rnd.uniform(-1, 1); sz += amp * rnd.uniform(-1, 1)
        cam.location = (cx + sx, -DIST, cz + 5.0 + sz)
        key(cam, "location", i + 1)

    # numbers for the end card
    v = pred["verdict"]
    if v == "CLEARED":
        sub = "landed at %.1f m \u00b7 %.1f s airtime" % (ev["land_x"], ev["land"] - ev["launch"])
    elif v == "FELL SHORT":
        sub = "hit the far wall %.1f m below the rim" % (-ev["wall_z"]) if "wall" in ev else "range %.1f m" % pred["range"]
    elif v == "OVERSHOT":
        sub = "range %.0f m \u00b7 missed the %g m mesa" % (pred["range"], LANDING_LENGTH)
    elif v == "LOST IN SPACE":
        sub = "range %.0f m \u00b7 %.1f s in the air" % (pred["range"], pred["airtime"])
    else:
        sub = "%.0f g \u00b7 flattened on the ramp" % pred["g_earths"]
    tv = verdict_time(ev, pred)
    build_hud(sc, cam, planet, pred, ev, sub, tv, FPS)
    setup_render(sc, preview)
    return sc, frames, ev, pred, tv


def setup_render(sc, preview):
    r = sc.render
    if preview:
        r.engine = "CYCLES"
        r.resolution_x, r.resolution_y = PREVIEW_RESOLUTION
        sc.cycles.samples = PREVIEW_SAMPLES
        sc.cycles.device = "CPU"
    else:
        r.engine = find_engine(ENGINE)
        r.resolution_x, r.resolution_y = RESOLUTION
        if r.engine == "CYCLES":
            sc.cycles.samples = CYCLES_SAMPLES
        elif hasattr(sc, "eevee"):
            if hasattr(sc.eevee, "taa_render_samples"):
                sc.eevee.taa_render_samples = EEVEE_SAMPLES
            for attr in ("use_shadows", "use_raytracing"):
                if hasattr(sc.eevee, attr):
                    setattr(sc.eevee, attr, True)
    if hasattr(sc, "cycles"):
        try:
            sc.cycles.use_denoising = True
        except Exception:
            pass
        sc.cycles.max_bounces = 4
    r.resolution_percentage = 100
    r.use_motion_blur = MOTION_BLUR and not preview
    try:
        sc.view_settings.view_transform = "AgX"
        for lk in ("AgX - Medium High Contrast", "Medium High Contrast"):
            try:
                sc.view_settings.look = lk; break
            except Exception:
                pass
    except Exception:
        pass
    r.image_settings.file_format = "PNG"


def render_still(sc, frame, path):
    sc.frame_set(frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)


# =============================================================================
# Main
# =============================================================================
def main():
    t0 = time.time()
    cleanup()
    S = build_shared()
    results = []
    print("\n=== CAN IT CLEAR THE CANYON?  v=%.1f m/s (%.0f km/h), ramp %.0f deg, lip %.1f m, gap %.0f m, mesa %.0f m ==="
          % (LAUNCH_SPEED, LAUNCH_SPEED * 3.6, RAMP_ANGLE_DEG, RAMP_HEIGHT, GAP, LANDING_LENGTH))
    print("%-8s %7s | %8s %8s %7s | %-13s | sim result" % ("planet", "g", "range", "airtime", "peak", "verdict"))
    for p in PLANETS:
        sc, frames, ev, pred, tv = build_scene(p, S, PREVIEW)
        results.append((p, sc, frames, ev, pred, tv))
        last = frames[-1]
        if "land" in ev:
            simr = "landed x=%.2f m (pred %.2f), stopped x=%.1f" % (ev["land_x"], pred["range"], ev.get("stop_x", float("nan")))
        elif "floor" in ev:
            simr = "hit far wall z=%.2f m (pred %.2f), canyon floor t=%.2fs" % (ev["wall_z"], pred["z_far_wall"], ev["floor"])
        elif "crush" in ev:
            simr = "crushed at x=%.2f, slid %.2f m in %.3f s; can climb ramp: %s" % (
                ev["crush_x"], ev.get("crush_slide", 0), ev.get("crush_stop", 0) - ev["crush"], pred["ramp_ok"])
        else:
            simr = "end of clip: x=%.1f z=%.1f (mode %s)" % (last["x"], last["z"], last["mode"])
        print("%-8s %7.2f | %7.1fm %7.2fs %6.1fm | %-13s | %s" % (
            p, GRAVITY[p], pred["range"], pred["airtime"], pred["peak"], pred["verdict"], simr))
    # make the first planet scene active in the UI
    try:
        if bpy.context.window is not None:
            bpy.context.window.scene = results[0][1]
    except Exception:
        pass
    print("[canyon] built %d scenes in %.1fs" % (len(results), time.time() - t0))

    root = out_root()
    if PREVIEW:
        pdir = os.path.join(root, "preview")
        os.makedirs(pdir, exist_ok=True)
        for p, sc, frames, ev, pred, tv in results:
            key_t = {"CLEARED": ev.get("land", 3) + 0.10, "FELL SHORT": ev.get("wall", 3) + 0.07,
                     "CRUSHED": ev.get("crush", 1.5) + 0.25, "OVERSHOT": ev.get("launch", 1.8) + 1.75,
                     "LOST IN SPACE": ev.get("launch", 1.8) + 1.1}[pred["verdict"]]
            shots = [("key", int(key_t * FPS) + 1)]
            if p in ("Earth", "Sun"):
                shots.append(("end", sc.frame_end))
            for tag, fr in shots:
                path = os.path.join(pdir, "%02d_%s_%s.png" % (PLANETS.index(p) + 1, p, tag))
                ts = time.time()
                render_still(sc, fr, path)
                print("[canyon] preview %s frame %d -> %s (%.1fs)" % (p, fr, path, time.time() - ts))
    if RENDER:
        for p, sc, frames, ev, pred, tv in results:
            d = os.path.join(root, "%02d_%s" % (PLANETS.index(p) + 1, p))
            os.makedirs(d, exist_ok=True)
            sc.render.filepath = os.path.join(d, "frame_")
            bpy.ops.render.render(animation=True, scene=sc.name)
            print("[canyon] rendered", p, "->", d)


if __name__ == "__main__":
    main()
