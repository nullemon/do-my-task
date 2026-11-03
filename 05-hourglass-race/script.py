"""
THE HOURGLASS RACE  -  six identical hourglasses, six planets, flipped at once.
=============================================================================

Blender 4.2 - 5.x, single self-contained script, everything procedural.

  * Scripting tab: open this file and press Run Script (builds scene + prints
    verification; then render with Render > Render Animation).
  * Headless:  blender -b -P script.py -- --render            (full quality)
               blender -b -P script.py -- --preview --render  (fast draft)
               blender -b -P script.py -- --frames 1,400,1700 --engine CYCLES

Physics model (Beverloo): mass flow through an orifice  W ~ rho * sqrt(g) * D^2.5
-> it does NOT depend on how much sand is left above the neck, so the top
volume drops LINEARLY in time, and the drain time scales as  T ~ 1/sqrt(g).
Calibrated so Earth = 60.0 s.

Because Pluto needs 238.7 s but the video must be 45-60 s, simulated time
("sim time") is mapped onto video time: real time until the Sun is done, then a
smooth fast-forward.  The on-screen timer always shows SIM seconds, so the
finish times on screen are the true ones from the table.
"""

import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

# =============================================================================
# CONFIG
# =============================================================================
CONFIG = dict(
    # name, gravity m/s^2, accent colour (UI), screen order = fastest first
    planets=[
        ("SUN",     274.0, (1.00, 0.50, 0.08)),
        ("JUPITER", 24.79, (0.95, 0.66, 0.38)),
        ("EARTH",   9.81,  (0.25, 0.80, 0.40)),
        ("MARS",    3.71,  (0.95, 0.42, 0.18)),
        ("MOON",    1.62,  (0.78, 0.78, 0.80)),
        ("PLUTO",   0.62,  (0.70, 0.86, 1.00)),
    ],
    earth_g=9.81,
    earth_drain_s=60.0,          # calibration: Earth hourglass empties in 60 s

    fps=30,
    duration_s=58.0,             # total video length (must be 45-60 s)
    resolution=(1080, 1920),

    # --- timeline (video seconds) -------------------------------------------
    lift_end=1.0,                # hourglasses lift (motion from frame 1)
    flip_start=1.0,
    flip_end=1.85,
    sim_start=2.0,               # sand starts flowing (sim t = 0)
    realtime_until=13.6,         # 1:1 real time until just after the Sun
    speed1=4.0,                  # first fast-forward rate
    speed1_ramp=1.4,             # seconds to ramp 1x -> speed1
    speed2_from=37.0,            # start of second ramp (after Mars)
    speed2_ramp=2.0,
    pluto_finish_at=55.0,        # video second at which Pluto empties
                                 # (speed2 is solved so this holds exactly)

    # --- render ---------------------------------------------------------------
    engine="EEVEE",              # EEVEE | CYCLES | WORKBENCH
    eevee_samples=64,
    cycles_samples=96,
    preview_scale=50,            # % resolution in PREVIEW mode
    preview_samples=16,
    output_dir="//hourglass_race_out",   # '//' = next to the .blend / cwd
    video=True,                  # FFMPEG H.264 (falls back to PNG sequence)

    PREVIEW=False,
    RENDER=False,
)

TABLE = {"SUN": 11.4, "JUPITER": 37.7, "EARTH": 60.0,
         "MARS": 97.6, "MOON": 147.6, "PLUTO": 238.7}   # brief, seconds

# =============================================================================
# CLI  (args after "--")
# =============================================================================
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = dict(frames=None, verify=True, range=None)
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--preview":
            CONFIG["PREVIEW"] = True
        elif a == "--render":
            CONFIG["RENDER"] = True
        elif a == "--out":
            i += 1; CONFIG["output_dir"] = argv[i]
        elif a == "--engine":
            i += 1; CONFIG["engine"] = argv[i].upper()
        elif a == "--samples":
            i += 1; CONFIG["eevee_samples"] = CONFIG["cycles_samples"] = \
                CONFIG["preview_samples"] = int(argv[i])
        elif a == "--res-pct":
            i += 1; CONFIG["preview_scale"] = int(argv[i]); CONFIG["PREVIEW"] = True
        elif a == "--frames":          # e.g. 1,400,1700  -> stills
            i += 1; opts["frames"] = [int(x) for x in argv[i].split(",") if x]
        elif a == "--range":           # e.g. 1-120 -> partial animation
            i += 1; opts["range"] = tuple(int(x) for x in argv[i].split("-"))
        elif a == "--png":
            CONFIG["video"] = False
        elif a == "--no-verify":
            opts["verify"] = False
        else:
            print("[hourglass] unknown arg ignored:", a)
        i += 1
    return opts


# =============================================================================
# PHYSICS + TIME MAPPING (pure python, no bpy)
# =============================================================================
def drain_time(g):
    """Beverloo: flow ~ sqrt(g)  ->  T = T_earth * sqrt(g_earth / g)."""
    return CONFIG["earth_drain_s"] * math.sqrt(CONFIG["earth_g"] / g)


def rate_points(speed2):
    c = CONFIG
    return [(c["sim_start"], 1.0),
            (c["realtime_until"], 1.0),
            (c["realtime_until"] + c["speed1_ramp"], c["speed1"]),
            (c["speed2_from"], c["speed1"]),
            (c["speed2_from"] + c["speed2_ramp"], speed2),
            (1e9, speed2)]


def rate_at(v, pts):
    if v < pts[0][0]:
        return 0.0
    for (v0, r0), (v1, r1) in zip(pts, pts[1:]):
        if v <= v1:
            return r0 + (r1 - r0) * (v - v0) / (v1 - v0)
    return pts[-1][1]


def sim_at(v, pts):
    """Exact integral of the piecewise-linear playback rate."""
    if v <= pts[0][0]:
        return 0.0
    s = 0.0
    for (v0, r0), (v1, r1) in zip(pts, pts[1:]):
        if v <= v0:
            break
        ve = min(v, v1)
        re = r0 + (r1 - r0) * (ve - v0) / (v1 - v0)
        s += 0.5 * (r0 + re) * (ve - v0)
    return s


def solve_speed2(t_last):
    lo, hi = CONFIG["speed1"], 200.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if sim_at(CONFIG["pluto_finish_at"], rate_points(mid)) < t_last:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def video_at_sim(t, pts):
    lo, hi = pts[0][0], CONFIG["duration_s"] + 100
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if sim_at(mid, pts) < t:
            lo = mid
        else:
            hi = mid
    return hi


# =============================================================================
# GEOMETRY CONSTANTS (metres, hourglass centred on the neck)
# =============================================================================
RN = 0.014           # neck inner radius
HC = 0.150           # height of conical part of each bulb
RB = 0.150           # bulb (cylinder) radius
HCYL = 0.285         # end of cylindrical part
HEND = 0.295         # glass end (goes into the wooden cap)
TAN_A = (RB - RN) / HC
Z_APEX = -RN / TAN_A                 # apex of the ideal cone through the neck
SAND_INSET = 0.965
SAND_TAN = TAN_A * SAND_INSET
SAND_TOP_Z = 0.120                   # initial sand surface in the top bulb
H0 = SAND_TOP_Z - Z_APEX             # top-cone height
V0 = math.pi / 3.0 * SAND_TAN ** 2 * H0 ** 3          # sand volume (m^3)
R_HEAP = RB * 0.955
REPOSE = math.radians(32.0)
K_HEAP = R_HEAP * math.tan(REPOSE)
V_HEAP = math.pi * R_HEAP ** 2 * K_HEAP / 3.0
FLOOR_Z = -0.287
CAP_T = 0.032
CAP_R = 0.205
HALF_H = HEND + CAP_T                # half height of whole hourglass
STREAM_R = 0.0075

GRID_X = (-0.60, 0.60)
GRID_Z = (2.35, 1.20, 0.05)          # hourglass centre heights, rows top->bottom
PED_H = 0.14


def bottom_state(vb):
    """Bottom pile: a cone heap (angle of repose) that grows until it spans
    the bulb, then a flat layer under the full heap. Returns
    (heap_scale, layer_thickness, surface_top_z) in hourglass-local z."""
    vb = max(0.0, vb)
    if vb <= V_HEAP:
        s = (vb / V_HEAP) ** (1.0 / 3.0)
        return s, 0.0, FLOOR_Z + s * K_HEAP
    y = (vb - V_HEAP) / (math.pi * R_HEAP ** 2)
    return 1.0, y, FLOOR_Z + y + K_HEAP


# =============================================================================
# SMALL BPY HELPERS
# =============================================================================
def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    return link(bpy.data.objects.new(name, me), coll)


def box(name, size, loc, mat=None, coll=None):
    sx, sy, sz = (s / 2 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj(name, v, f, coll)
    o.location = loc
    if mat:
        o.data.materials.append(mat)
    return o


def lathe(name, profile, segs=48, cap_bottom=False, cap_top=False, coll=None):
    """Solid of revolution from (r, z) list (z ascending).  r == 0 -> pole."""
    verts, faces, rings = [], [], []
    for r, z in profile:
        if r <= 1e-9:
            rings.append([len(verts)]); verts.append((0, 0, z))
        else:
            ring = []
            for i in range(segs):
                a = 2 * math.pi * i / segs
                ring.append(len(verts)); verts.append((r * math.cos(a), r * math.sin(a), z))
            rings.append(ring)
    for ra, rb in zip(rings, rings[1:]):
        if len(ra) == 1 and len(rb) > 1:
            for i in range(segs):
                faces.append((ra[0], rb[(i + 1) % segs], rb[i]))
        elif len(rb) == 1 and len(ra) > 1:
            for i in range(segs):
                faces.append((ra[i], ra[(i + 1) % segs], rb[0]))
        elif len(ra) > 1 and len(rb) > 1:
            for i in range(segs):
                j = (i + 1) % segs
                faces.append((ra[i], ra[j], rb[j], rb[i]))
    if cap_bottom and len(rings[0]) > 1:
        faces.append(tuple(reversed(rings[0])))
    if cap_top and len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    o = mesh_obj(name, verts, faces, coll)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def set_blend(m):
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    elif hasattr(m, "blend_method"):
        m.blend_method = "BLEND"


def principled(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=0.0):
    m, nt, out = new_mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    nt.links.new(b.outputs[0], out.inputs[0])
    m.diffuse_color = (*color, 1)
    return m


def emission_mat(name, color, strength=1.0, alpha=1.0):
    m, nt, out = new_mat(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    if alpha < 1.0:
        t = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        nt.links.new(t.outputs[0], mx.inputs[1])
        nt.links.new(e.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
        set_blend(m)
    else:
        nt.links.new(e.outputs[0], out.inputs[0])
    m.diffuse_color = (*color, alpha)
    return m


def add_greyout(mat):
    """Wrap a material's surface in Mix(original, grey diffuse). Returns the
    Mix node (key inputs[0] to grey the tile out)."""
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs[0].links[0].from_socket
    grey = nt.nodes.new("ShaderNodeBsdfDiffuse")
    grey.inputs[0].default_value = (0.13, 0.13, 0.13, 1)
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.name = "GREYOUT"
    mx.inputs[0].default_value = 0.0
    nt.links.new(src, mx.inputs[1])
    nt.links.new(grey.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return mx


def bake_curve(id_data, data_path, index, frames, values):
    """Write one F-curve with a key on every given frame (fast path).
    Blender 4.4+/5.x: slotted actions (fcurve_ensure_for_datablock).
    Blender 4.2/4.3: legacy action.fcurves.  Fallback: keyframe_insert."""
    ad = id_data.animation_data or id_data.animation_data_create()
    if ad.action is None:
        ad.action = bpy.data.actions.new(f"HG_{id_data.name}_act")
    act = ad.action
    fc = None
    try:
        if hasattr(act, "fcurve_ensure_for_datablock"):
            fc = act.fcurve_ensure_for_datablock(id_data, data_path, index=index)
        else:
            fc = act.fcurves.find(data_path, index=index) or act.fcurves.new(data_path, index=index)
    except Exception:
        fc = None
    if fc is None:      # slow but universal
        for f, val in zip(frames, values):
            prop = id_data.path_resolve(data_path)
            prop[index] = val
            id_data.keyframe_insert(data_path, index=index, frame=f)
        return
    kp = fc.keyframe_points
    if len(kp):
        kp.clear()
    kp.add(len(frames))
    co = []
    for f, val in zip(frames, values):
        co += [float(f), float(val)]
    kp.foreach_set("co", co)
    for k in kp:
        k.interpolation = "LINEAR"
        k.handle_left_type = k.handle_right_type = "VECTOR"
    fc.update()


def compress(frames, values):
    """Drop keys inside runs of identical values (exact; no curve fitting)."""
    if len(frames) < 3:
        return frames, values
    kf, kv = [frames[0]], [values[0]]
    for i in range(1, len(frames) - 1):
        a, b, c = values[i - 1], values[i], values[i + 1]
        if not (a == b == c):
            kf.append(frames[i]); kv.append(b)
    kf.append(frames[-1]); kv.append(values[-1])
    return kf, kv


# =============================================================================
# SCENE BUILD
# =============================================================================
STATE = {}          # shared with the frame handler


def reset_scene():
    scn = bpy.context.scene
    for o in list(scn.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(scn.collection.children):
        if c.name.startswith("HG_"):
            bpy.data.collections.remove(c)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.actions, bpy.data.cameras, bpy.data.lights):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    # remove previous handler
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "hourglass_race_update":
            bpy.app.handlers.frame_change_pre.remove(h)
    return scn


def make_world(scn):
    w = bpy.data.worlds.get("HG_World") or bpy.data.worlds.new("HG_World")
    w.use_nodes = True
    nt = w.node_tree
    bg = next((n for n in nt.nodes if n.type == "BACKGROUND"), None) or nt.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.012, 0.012, 0.018, 1)
    bg.inputs[1].default_value = 1.0
    out = next((n for n in nt.nodes if n.type == "OUTPUT_WORLD"), None) or nt.nodes.new("ShaderNodeOutputWorld")
    if not out.inputs[0].links:
        nt.links.new(bg.outputs[0], out.inputs[0])
    scn.world = w


def backdrop_material(planet):
    """Planet-look panel behind each hourglass."""
    m, nt, out = new_mat(f"HG_backdrop_{planet}")
    N = nt.nodes.new
    L = nt.links.new
    tc = N("ShaderNodeTexCoord")
    if planet == "SUN":
        noise = N("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 6.0
        noise.inputs["Detail"].default_value = 8.0
        L(tc.outputs["Object"], noise.inputs["Vector"])
        ramp = N("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (0.55, 0.10, 0.0, 1)
        ramp.color_ramp.elements[1].color = (1.0, 0.55, 0.08, 1)
        L(noise.outputs["Fac"], ramp.inputs[0])
        e = N("ShaderNodeEmission"); e.inputs[1].default_value = 0.9
        L(ramp.outputs[0], e.inputs[0]); L(e.outputs[0], out.inputs[0])
        return m
    if planet in ("MOON", "PLUTO"):
        # dark sky with stars
        v = N("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 60.0
        L(tc.outputs["Object"], v.inputs["Vector"])
        ramp = N("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
        ramp.color_ramp.elements[1].position = 0.035
        ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
        L(v.outputs["Distance"], ramp.inputs[0])
        sky = (0.006, 0.006, 0.010) if planet == "MOON" else (0.008, 0.010, 0.025)
        mix = N("ShaderNodeMix"); mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*sky, 1)
        mix.inputs["B"].default_value = (0.9, 0.9, 1.0, 1)
        L(ramp.outputs[0], mix.inputs["Factor"])
        # horizon glow at the bottom of the panel
        e = N("ShaderNodeEmission"); e.inputs[1].default_value = 1.0
        L(mix.outputs["Result"], e.inputs[0]); L(e.outputs[0], out.inputs[0])
        return m
    # gradient skies / bands via a colour ramp on object Z (or noise)
    sep = N("ShaderNodeSeparateXYZ"); L(tc.outputs["Object"], sep.inputs[0])
    ramp = N("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    if planet == "JUPITER":
        wave = N("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "Z"
        wave.inputs["Scale"].default_value = 2.2
        wave.inputs["Distortion"].default_value = 6.0
        wave.inputs["Detail"].default_value = 4.0
        L(tc.outputs["Object"], wave.inputs["Vector"])
        cr.elements[0].color = (0.55, 0.28, 0.12, 1)
        cr.elements[1].color = (0.95, 0.80, 0.58, 1)
        cr.elements.new(0.5).color = (0.85, 0.45, 0.18, 1)
        L(wave.outputs["Fac"], ramp.inputs[0])
        strength = 0.55
    else:
        maprange = N("ShaderNodeMapRange")
        maprange.inputs["From Min"].default_value = -0.45
        maprange.inputs["From Max"].default_value = 0.45
        L(sep.outputs["Z"], maprange.inputs["Value"])
        L(maprange.outputs[0], ramp.inputs[0])
        if planet == "EARTH":
            cr.elements[0].color = (0.10, 0.35, 0.12, 1)     # green hills
            cr.elements[1].color = (0.18, 0.45, 0.95, 1)     # blue sky
            e2 = cr.elements.new(0.30); e2.color = (0.20, 0.55, 0.18, 1)
            e3 = cr.elements.new(0.36); e3.color = (0.60, 0.80, 1.0, 1)
        else:  # MARS
            cr.elements[0].color = (0.45, 0.13, 0.05, 1)     # rust ground
            cr.elements[1].color = (0.80, 0.55, 0.32, 1)     # butterscotch sky
            e2 = cr.elements.new(0.30); e2.color = (0.62, 0.22, 0.08, 1)
            e3 = cr.elements.new(0.36); e3.color = (0.92, 0.66, 0.40, 1)
        strength = 0.6
    e = N("ShaderNodeEmission"); e.inputs[1].default_value = strength
    L(ramp.outputs[0], e.inputs[0]); L(e.outputs[0], out.inputs[0])
    return m


PEDESTAL = {
    "SUN":     dict(color=(1.0, 0.35, 0.05), emit=(1.0, 0.38, 0.05), es=0.8, rough=0.6),
    "JUPITER": dict(color=(0.75, 0.52, 0.30), rough=0.6),
    "EARTH":   dict(color=(0.12, 0.45, 0.18), rough=0.7),
    "MARS":    dict(color=(0.60, 0.20, 0.07), rough=0.8),
    "MOON":    dict(color=(0.42, 0.42, 0.43), rough=0.9),
    "PLUTO":   dict(color=(0.82, 0.88, 0.95), rough=0.35),
}


def build_hourglass_parts(coll, mats):
    """Template meshes (shared data) built once, in hourglass-local space."""
    # bottom end -> neck -> top end, (r, z)
    n = 10
    def half(sign):
        pts = [(RB - 0.018, HEND), (RB - 0.004, HEND - 0.004), (RB, HCYL)]
        pts.append((RB, HC + 0.02))
        # rounded join cylinder -> cone
        for i in range(1, n):
            t = i / n
            z = HC + 0.02 - 0.04 * t
            r_cone = RN + TAN_A * z
            r = (1 - t) * RB + t * min(RB, r_cone) if z > HC else r_cone
            pts.append((min(RB, r), z))
        for i in range(0, 8):
            z = HC - 0.02 - (HC - 0.02 - 0.01) * i / 7
            pts.append((RN + TAN_A * z, z))
        pts.append((RN, 0.0))
        if sign > 0:
            return list(reversed(pts))
        return [(r, -z) for r, z in pts]
    prof = half(-1) + half(+1)[1:]
    glass = lathe("HG_tpl_glass", prof, segs=56, coll=coll)
    glass.data.materials.append(mats["glass"])
    sub = glass.modifiers.new("smooth", "SUBSURF"); sub.levels = 1; sub.render_levels = 1
    glass.hide_render = glass.hide_viewport = True

    cap = lathe("HG_tpl_cap", [(0, -CAP_T / 2), (CAP_R - 0.01, -CAP_T / 2), (CAP_R, -CAP_T / 2 + 0.01),
                                (CAP_R, CAP_T / 2 - 0.01), (CAP_R - 0.01, CAP_T / 2), (0, CAP_T / 2)],
                segs=48, coll=coll)
    cap.data.materials.append(mats["wood"])
    cap.hide_render = cap.hide_viewport = True
    post_prof = [(0, -HEND), (0.011, -HEND)]
    for i in range(1, 12):
        z = -HEND + 2 * HEND * i / 12
        post_prof.append((0.011 + 0.004 * math.sin(i * 1.3) ** 2, z))
    post_prof += [(0.011, HEND), (0, HEND)]
    post = lathe("HG_tpl_post", post_prof, segs=12, coll=coll)
    post.data.materials.append(mats["wood"])
    post.hide_render = post.hide_viewport = True

    # top sand: cone, apex at origin, height H0 (scaled about apex)
    seg = 40
    cone = lathe("HG_tpl_topcone", [(0, 0), (SAND_TAN * H0, H0), (0, H0)], segs=seg,
                 coll=coll)
    # heap: base at origin, apex up
    heap = lathe("HG_tpl_heap", [(0, 0), (R_HEAP, 0), (0, K_HEAP)], segs=seg, coll=coll)
    # layer: unit-height cylinder (scale z = thickness)
    layer = lathe("HG_tpl_layer", [(0, 0), (R_HEAP, 0), (R_HEAP, 1.0), (0, 1.0)], segs=seg, coll=coll)
    # stream: unit-length cylinder hanging down from origin
    stream = lathe("HG_tpl_stream", [(0, -1.0), (STREAM_R, -1.0), (STREAM_R, 0), (0, 0)], segs=10,
                   coll=coll)
    for o in (cone, heap, layer, stream):
        o.data.materials.append(mats["sand"])
        for p in o.data.polygons:
            p.use_smooth = False
        o.hide_render = o.hide_viewport = True
    return dict(glass=glass, cap=cap, post=post, cone=cone, heap=heap, layer=layer, stream=stream)


def inst(tpl, name, parent=None, loc=(0, 0, 0), coll=None):
    o = link(bpy.data.objects.new(name, tpl.data), coll)
    for md in tpl.modifiers:
        if md.type == "SUBSURF":
            m2 = o.modifiers.new(md.name, "SUBSURF"); m2.levels = md.levels; m2.render_levels = md.render_levels
    o.parent = parent
    o.location = loc
    return o


def build_materials():
    mats = {}
    # fake-but-robust glass: transparent core, glossy rim (works in Eevee & Cycles)
    m, nt, out = new_mat("HG_glass")
    N = nt.nodes.new; L = nt.links.new
    lw = N("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.12
    tr = N("ShaderNodeBsdfTransparent"); tr.inputs[0].default_value = (0.96, 0.98, 1.0, 1)
    gl = N("ShaderNodeBsdfGlossy") if "ShaderNodeBsdfGlossy" in dir(bpy.types) else N("ShaderNodeBsdfAnisotropic")
    gl.inputs[0].default_value = (1, 1, 1, 1)
    gl.inputs[1].default_value = 0.04
    mx = N("ShaderNodeMixShader")
    rng = N("ShaderNodeMapRange")
    rng.inputs["To Min"].default_value = 0.06
    rng.inputs["To Max"].default_value = 0.85
    L(lw.outputs["Facing"], rng.inputs["Value"])
    L(rng.outputs[0], mx.inputs[0])
    L(tr.outputs[0], mx.inputs[1]); L(gl.outputs[0], mx.inputs[2])
    L(mx.outputs[0], out.inputs[0])
    set_blend(m)
    if hasattr(m, "use_backface_culling"):
        m.use_backface_culling = False
    m.diffuse_color = (0.9, 0.95, 1, 0.2)
    mats["glass"] = m

    # sand with grain bump (world-space so grain doesn't stretch as cones scale)
    m, nt, out = new_mat("HG_sand")
    N = nt.nodes.new; L = nt.links.new
    b = N("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.95
    geo = N("ShaderNodeNewGeometry")
    noise = N("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 450.0
    noise.inputs["Detail"].default_value = 2.0
    L(geo.outputs["Position"], noise.inputs["Vector"])
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.70, 0.42, 0.16, 1)
    ramp.color_ramp.elements[1].color = (0.98, 0.74, 0.40, 1)
    L(noise.outputs["Fac"], ramp.inputs[0]); L(ramp.outputs[0], b.inputs["Base Color"])
    bump = N("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    L(noise.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs[0], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    m.diffuse_color = (0.85, 0.68, 0.42, 1)
    mats["sand"] = m

    m, nt, out = new_mat("HG_wood")
    N = nt.nodes.new; L = nt.links.new
    b = N("ShaderNodeBsdfPrincipled"); b.inputs["Roughness"].default_value = 0.45
    wave = N("ShaderNodeTexWave"); wave.inputs["Scale"].default_value = 18.0
    wave.inputs["Distortion"].default_value = 4.0
    ramp = N("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.16, 0.07, 0.03, 1)
    ramp.color_ramp.elements[1].color = (0.36, 0.17, 0.07, 1)
    L(wave.outputs["Fac"], ramp.inputs[0]); L(ramp.outputs[0], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs[0])
    m.diffuse_color = (0.3, 0.15, 0.07, 1)
    mats["wood"] = m

    mats["shelf"] = principled("HG_shelf", (0.045, 0.045, 0.05), rough=0.55)
    mats["wall"] = principled("HG_wall", (0.02, 0.02, 0.025), rough=0.8)
    mats["text"] = emission_mat("HG_text_white", (1, 1, 1), 4.0)
    mats["plate"] = emission_mat("HG_plate", (0.0, 0.0, 0.0), 1.0, alpha=0.78)
    return mats


# ---------------------------------------------------------------------------
# camera + overlay text
# ---------------------------------------------------------------------------
TEXT_DIST = 1.0
FOCAL = 70.0
SENSOR_H = 36.0
HH = TEXT_DIST * (SENSOR_H / 2) / FOCAL       # half frame height at TEXT_DIST


def make_camera(scn):
    cd = bpy.data.cameras.new("HG_cam")
    cd.lens = FOCAL
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = SENSOR_H
    cd.clip_start = 0.05
    cd.clip_end = 100
    cam = link(bpy.data.objects.new("HG_camera", cd))
    frame_h = 5.15
    frame_bottom = -0.86
    dist = frame_h / 2 / ((SENSOR_H / 2) / FOCAL)
    cam.location = (0.0, -dist, frame_bottom + frame_h / 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scn.camera = cam
    bpy.context.view_layer.update()
    return cam


def project(cam, p):
    """World point -> overlay coords (u, v) in units of half frame height."""
    q = cam.matrix_world.inverted() @ Vector(p)
    k = (SENSOR_H / 2) / FOCAL
    return (q.x / -q.z) / k, (q.y / -q.z) / k


def make_text(cam, name, body, u, v, size, mats, color=None, plate=True,
              pad=(0.035, 0.022), plate_size=None, coll=None, align="CENTER"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size * HH
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_line = 0.95
    cu.offset = 0.0
    o = link(bpy.data.objects.new(name, cu), coll)
    o.parent = cam
    o.location = (u * HH, v * HH, -TEXT_DIST)
    if color is None:
        o.data.materials.append(mats["text"])
    else:
        o.data.materials.append(emission_mat(f"HG_txt_{name}", color, 4.0))
    if plate:
        bpy.context.view_layer.update()
        if plate_size:
            w, h = plate_size[0] * HH, plate_size[1] * HH
            cx, cy = 0.0, 0.0
        else:
            bb = [Vector(c) for c in o.bound_box]
            xs = [c.x for c in bb]; ys = [c.y for c in bb]
            w = (max(xs) - min(xs)) + 2 * pad[0] * HH
            h = (max(ys) - min(ys)) + 2 * pad[1] * HH
            cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        pl = mesh_obj(name + "_plate", [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)],
                      [(0, 1, 2, 3)], coll)
        pl.data.materials.append(mats["plate"])
        pl.parent = o
        pl.location = (cx, cy, -0.002)
    return o


def key_visibility(o, windows, fps, pop=True):
    """Show object (scale 1) only inside [(v_in, v_out)] video-second windows
    (v_out None = until the end). Pop-in with a small overshoot."""
    keys = {1: 0.0}
    for v_in, v_out in windows:
        f_in = 1 + round(v_in * fps)
        if f_in > 1:
            keys[f_in - 1] = 0.0
        if pop:
            keys[f_in] = 0.6; keys[f_in + 3] = 1.15; keys[f_in + 6] = 1.0
        else:
            keys[f_in] = 1.0
        if v_out is not None:
            f_out = 1 + round(v_out * fps)
            keys[f_out - 1] = 1.0; keys[f_out] = 0.0
    for f in sorted(keys):
        o.scale = (keys[f],) * 3
        o.keyframe_insert("scale", frame=f)


# ---------------------------------------------------------------------------
def build(opts):
    c = CONFIG
    scn = reset_scene()
    fps = c["fps"]
    scn.render.fps = fps
    scn.render.fps_base = 1.0
    n_frames = int(round(c["duration_s"] * fps))
    scn.frame_start = 1
    scn.frame_end = n_frames
    scn.render.resolution_x, scn.render.resolution_y = c["resolution"]
    scn.render.resolution_percentage = c["preview_scale"] if c["PREVIEW"] else 100
    scn.gravity = (0, 0, -9.81)   # unused (no rigid bodies) - sand is analytic

    coll = bpy.data.collections.new("HG_Hourglass_Race")
    scn.collection.children.link(coll)
    tcoll = bpy.data.collections.new("HG_templates")
    scn.collection.children.link(tcoll)

    make_world(scn)
    mats = build_materials()
    tpl = build_hourglass_parts(tcoll, mats)
    cam = make_camera(scn)

    # ---------- time mapping ----------
    planets = c["planets"]
    T = {p[0]: drain_time(p[1]) for p in planets}
    speed2 = solve_speed2(max(T.values()))
    pts = rate_points(speed2)
    frames = list(range(1, n_frames + 1))
    vt = [(f - 1) / fps for f in frames]
    sim = [sim_at(v, pts) for v in vt]
    finish_v = {k: video_at_sim(t, pts) for k, t in T.items()}
    STATE.update(sim=sim, pts=pts, fps=fps, speed2=speed2, T=T, finish_v=finish_v,
                 frames=frames)

    # ---------- shelf / environment ----------
    wall = box("HG_wall", (8, 0.1, 8), (0, 0.75, 1.6), mats["wall"], coll)
    for zi, zc in enumerate(GRID_Z):
        box(f"HG_shelf_{zi}", (2.7, 1.1, 0.06), (0, 0.0, zc - HALF_H - PED_H - 0.03), mats["shelf"], coll)
    box("HG_div_mid", (0.06, 0.25, 3.6), (0, 0.55, 1.15), mats["shelf"], coll)

    flip_f0 = 1 + round(c["flip_start"] * fps)
    flip_f1 = 1 + round(c["flip_end"] * fps)
    sim_f0 = 1 + round(c["sim_start"] * fps)
    STATE["planet_objs"] = {}

    for idx, (name, g, accent) in enumerate(planets):
        col, row = idx % 2, idx // 2
        x, zc = GRID_X[col], GRID_Z[row]
        # backdrop panel (planet look) + pedestal (planet colour)
        bd = box(f"HG_{name}_backdrop", (1.12, 0.04, 0.98), (x, 0.50, zc + 0.02), backdrop_material(name), coll)
        pdef = PEDESTAL[name]
        pm = principled(f"HG_ped_{name}", pdef["color"], rough=pdef["rough"],
                        emit=pdef.get("emit"), emit_strength=pdef.get("es", 0.0))
        ped = box(f"HG_{name}_pedestal", (0.62, 0.62, PED_H), (x, 0, zc - HALF_H - PED_H / 2), pm, coll)
        mixes = [add_greyout(bd.active_material), add_greyout(pm)]

        # pivot that lifts + flips the hourglass
        piv = link(bpy.data.objects.new(f"HG_{name}_pivot", None), coll)
        piv.empty_display_size = 0.2
        piv.location = (x, 0, zc)
        inst(tpl["glass"], f"HG_{name}_glass", piv, coll=coll)
        inst(tpl["cap"], f"HG_{name}_capT", piv, (0, 0, HEND + CAP_T / 2), coll)
        inst(tpl["cap"], f"HG_{name}_capB", piv, (0, 0, -HEND - CAP_T / 2), coll)
        for k in range(3):
            a = 2 * math.pi * k / 3 + math.pi / 2
            inst(tpl["post"], f"HG_{name}_post{k}", piv, (0.172 * math.cos(a), 0.172 * math.sin(a), 0), coll)
        # pre-flip sand (resting in the lower bulb, flips with the glass)
        pre_heap = inst(tpl["heap"], f"HG_{name}_preheap", piv, coll=coll)
        hs, ly, _ = bottom_state(V0)
        pre_heap.location = (0, 0, FLOOR_Z + ly)
        pre_layer = inst(tpl["layer"], f"HG_{name}_prelayer", piv, (0, 0, FLOOR_Z), coll)
        pre_layer.scale = (1, 1, max(ly, 1e-4))
        # world-space sand after the flip (not parented to the rotating pivot)
        top = inst(tpl["cone"], f"HG_{name}_sand_top", None, (x, 0, zc + Z_APEX), coll)
        heap = inst(tpl["heap"], f"HG_{name}_sand_heap", None, (x, 0, zc + FLOOR_Z), coll)
        layer = inst(tpl["layer"], f"HG_{name}_sand_layer", None, (x, 0, zc + FLOOR_Z), coll)
        stream = inst(tpl["stream"], f"HG_{name}_sand_stream", None, (x, 0, zc + 0.005), coll)

        # --- lift + flip (sparse keys, bezier ease) ---
        lift = 0.07
        piv.location = (x, 0, zc); piv.keyframe_insert("location", frame=1)
        piv.location = (x, 0, zc + lift); piv.keyframe_insert("location", frame=flip_f0)
        piv.keyframe_insert("location", frame=flip_f1)
        piv.location = (x, 0, zc); piv.keyframe_insert("location", frame=sim_f0)
        piv.rotation_euler = (0, 0, 0); piv.keyframe_insert("rotation_euler", frame=flip_f0)
        piv.rotation_euler = (math.pi, 0, 0); piv.keyframe_insert("rotation_euler", frame=flip_f1)

        # --- sand: one key per frame, from the analytic linear-flow model ---
        Tn = T[name]
        top_s, heap_s, heap_z, layer_s, str_r, str_len, pre_s = [], [], [], [], [], [], []
        for f, t in zip(frames, sim):
            before = f < flip_f1                  # still the pre-flip pile
            frac_top = max(0.0, 1.0 - t / Tn)    # LINEAR in time: Beverloo
            vtop = V0 * frac_top
            if before:
                top_s.append(0.0); heap_s.append(0.0); layer_s.append(0.0)
                heap_z.append(zc + FLOOR_Z); str_r.append(0.0); str_len.append(0.0)
                pre_s.append(1.0)
                continue
            pre_s.append(0.0)
            top_s.append(frac_top ** (1.0 / 3.0))
            hs, ly, surf = bottom_state(V0 - vtop)
            heap_s.append(hs)
            heap_z.append(zc + FLOOR_Z + ly)
            layer_s.append(ly)
            flowing = 0.0 < t < Tn and f >= sim_f0
            str_r.append(1.0 if flowing else 0.0)
            str_len.append(max(0.0, 0.005 - surf) if flowing else 0.0)
        for i in range(3):
            bake_curve(top, "scale", i, *compress(frames, top_s))
            bake_curve(heap, "scale", i, *compress(frames, heap_s))
        bake_curve(heap, "location", 2, *compress(frames, heap_z))
        bake_curve(layer, "scale", 2, *compress(frames, layer_s))
        bake_curve(layer, "scale", 0, *compress(frames, [1.0 if s > 0 else 0.0 for s in layer_s]))
        bake_curve(layer, "scale", 1, *compress(frames, [1.0 if s > 0 else 0.0 for s in layer_s]))
        bake_curve(stream, "scale", 0, *compress(frames, str_r))
        bake_curve(stream, "scale", 1, *compress(frames, str_r))
        bake_curve(stream, "scale", 2, *compress(frames, str_len))
        for i in range(3):
            bake_curve(pre_heap, "scale", i, *compress(frames, pre_s))
        bake_curve(pre_layer, "scale", 0, *compress(frames, pre_s))
        bake_curve(pre_layer, "scale", 1, *compress(frames, pre_s))

        # --- grey-out at the finish frame ---
        ff = 1 + math.ceil(finish_v[name] * fps)
        for mx in mixes:
            sock = mx.inputs[0]
            sock.default_value = 0.0; sock.keyframe_insert("default_value", frame=ff - 1)
            sock.default_value = 0.82; sock.keyframe_insert("default_value", frame=ff + 8)

        STATE["planet_objs"][name] = dict(top=top, heap=heap, layer=layer, stream=stream,
                                          finish_frame=ff, zc=zc, x=x)

        # --- tile labels (camera-parented text) ---
        u, v = project(cam, (x, -0.31, zc - HALF_H - PED_H - 0.12))
        lab = make_text(cam, f"HG_lbl_{name}", f"{name} · {g:g} m/s²", u, v, 0.050, mats,
                        color=tuple(min(1, ch * 1.1) for ch in accent), coll=coll)
        # small one-line badge on the pedestal front -> glass stays visible
        u2, v2 = project(cam, (x, -0.32, zc - HALF_H - PED_H / 2))
        done = make_text(cam, f"HG_done_{name}", f"DONE {TABLE_FMT(Tn)} s", u2, v2, 0.040, mats,
                         color=(1.0, 0.95, 0.6), coll=coll, pad=(0.03, 0.012))
        key_visibility(done, [(finish_v[name] + 1.0 / fps, None)], fps)
        STATE["planet_objs"][name]["done_text"] = done

    # ---------- top band overlay ----------
    hook = make_text(cam, "HG_hook", "Same sand. Same glass.\n6 planets.\nWhich finishes first?",
                     0, 0.73, 0.088, mats, coll=coll, pad=(0.05, 0.03))
    key_visibility(hook, [(0.0, 3.2)], fps, pop=False)
    hook.scale = (0.92, 0.92, 0.92); hook.keyframe_insert("scale", frame=1)
    hook.scale = (1, 1, 1); hook.keyframe_insert("scale", frame=12)

    timer_label = make_text(cam, "HG_timer_label", "SIMULATED TIME", 0, 0.905, 0.040, mats,
                            color=(0.8, 0.8, 0.8), coll=coll, plate=False)
    timer = make_text(cam, "HG_timer", "0.0 s", 0, 0.83, 0.115, mats, coll=coll,
                      plate_size=(0.56, 0.25))
    timer_label.parent = timer
    timer_label.location = (0, 0.092 * HH, 0.001)
    speed = make_text(cam, "HG_speed", "REAL TIME", 0, 0.675, 0.046, mats, color=(1.0, 0.85, 0.3),
                      coll=coll, plate_size=(0.46, 0.075))
    key_visibility(timer, [(3.2, None)], fps)
    key_visibility(speed, [(3.2, None)], fps)

    # event captions
    cap_v = 0.565   # between speed badge and top row (never over the tiles)
    caps = [
        (finish_v["SUN"], 4.0, f"SUN DONE in {T['SUN']:.0f} s!"),
        (finish_v["JUPITER"], 3.4, f"JUPITER DONE: {TABLE_FMT(T['JUPITER'])} s"),
        (finish_v["EARTH"], 3.6, f"EARTH DONE: {TABLE_FMT(T['EARTH'])} s"),
        (finish_v["MARS"], 3.6, f"MARS DONE: {TABLE_FMT(T['MARS'])} s"),
        (finish_v["MOON"], 3.0, f"MOON DONE: {TABLE_FMT(T['MOON'])} s"),
        (finish_v["MOON"] + 3.1, finish_v["PLUTO"] - finish_v["MOON"] - 3.1,
         "PLUTO: still going...\n4 minutes total"),
        (finish_v["PLUTO"], c["duration_s"] + 1 - finish_v["PLUTO"],
         f"PLUTO DONE: {TABLE_FMT(T['PLUTO'])} s\nsand flow ∝ √g"),
    ]
    caption_objs = []
    for k, (v0, dur, txt) in enumerate(caps):
        o = make_text(cam, f"HG_caption_{k}", txt, 0, cap_v, 0.062, mats, color=(1, 1, 1), coll=coll,
                      pad=(0.05, 0.025))
        v_out = v0 + dur if v0 + dur < c["duration_s"] else None
        key_visibility(o, [(v0 + 1.0 / fps, v_out)], fps)
        caption_objs.append((v0, txt))
    STATE["captions"] = caption_objs

    # ---------- lights ----------
    ld = bpy.data.lights.new("HG_key", "AREA"); ld.size = 5.0; ld.energy = 650
    key = link(bpy.data.objects.new("HG_key", ld), coll)
    key.location = (0.6, -5.5, 5.0)
    key.rotation_euler = (Vector((0, 0, 1.2)) - key.location).to_track_quat("-Z", "Y").to_euler()
    ld2 = bpy.data.lights.new("HG_rim", "AREA"); ld2.size = 3.0; ld2.energy = 120
    rim = link(bpy.data.objects.new("HG_rim", ld2), coll)
    rim.location = (-2.5, -1.0, 4.5)
    rim.rotation_euler = (Vector((0, 0, 1.2)) - rim.location).to_track_quat("-Z", "Y").to_euler()

    STATE["timer"] = timer
    STATE["speed"] = speed
    bpy.app.handlers.frame_change_pre.append(hourglass_race_update)
    setup_render(scn)
    scn.frame_set(1)
    return scn


def TABLE_FMT(t):
    return f"{t:.1f}"


# =============================================================================
# FRAME HANDLER (text bodies only - geometry is keyframed)
# =============================================================================
def hourglass_race_update(scene, depsgraph=None):
    try:
        f = scene.frame_current
        sim = STATE["sim"]
        i = min(max(f - 1, 0), len(sim) - 1)
        t = sim[i]
        timer = STATE["timer"]
        timer.data.body = f"{t:.1f} s"
        v = (f - 1) / STATE["fps"]
        r = rate_at(v, STATE["pts"])
        if r <= 0:
            txt = "GET READY..."
        elif r < 1.05:
            txt = "REAL TIME"
        else:
            txt = f">> {r:.0f}x FAST-FORWARD"
        STATE["speed"].data.body = txt
    except (KeyError, ReferenceError):
        pass


# =============================================================================
# RENDER SETTINGS
# =============================================================================
def resolve_out():
    out = CONFIG["output_dir"]
    if out.startswith("//"):
        base = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
        out = os.path.join(base, out[2:])
    return os.path.abspath(out)


def setup_render(scn):
    c = CONFIG
    eng = c["engine"]
    r = scn.render
    if eng == "EEVEE":
        for ident in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                r.engine = ident
                break
            except TypeError:
                continue
        ee = scn.eevee
        samples = c["preview_samples"] if c["PREVIEW"] else c["eevee_samples"]
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = samples
        for attr, val in (("use_raytracing", False), ("use_shadows", True), ("use_gtao", True)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass
    elif eng == "CYCLES":
        r.engine = "CYCLES"
        scn.cycles.samples = c["preview_samples"] if c["PREVIEW"] else c["cycles_samples"]
        scn.cycles.use_denoising = True
        try:
            scn.cycles.device = "CPU"
        except Exception:
            pass
    else:
        r.engine = "BLENDER_WORKBENCH"
        scn.display.shading.color_type = "MATERIAL"
        scn.display.shading.light = "STUDIO"
    try:
        scn.view_settings.view_transform = "Standard"
        scn.view_settings.look = "None"
    except TypeError:
        try:
            scn.view_settings.look = "None"
        except TypeError:
            pass
    r.use_motion_blur = False
    out = resolve_out()
    os.makedirs(out, exist_ok=True)
    tag = "preview" if c["PREVIEW"] else "final"
    if c["video"]:
        try:
            if hasattr(r.image_settings, "media_type"):
                r.image_settings.media_type = "VIDEO"
            r.image_settings.file_format = "FFMPEG"
            r.ffmpeg.format = "MPEG4"
            r.ffmpeg.codec = "H264"
            r.ffmpeg.constant_rate_factor = "HIGH"
            r.ffmpeg.audio_codec = "NONE"
            r.filepath = os.path.join(out, f"hourglass_race_{tag}.mp4")
            return
        except Exception as e:
            print("[hourglass] FFMPEG unavailable, writing PNG sequence:", e)
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.filepath = os.path.join(out, f"hourglass_race_{tag}_")


# =============================================================================
# VERIFICATION (measured from the evaluated scene)
# =============================================================================
def mesh_volume_world(obj, dg):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    me.calc_loop_triangles()
    co = [mw @ v.co for v in me.vertices]
    vol = 0.0
    for tri in me.loop_triangles:
        a, b, cc = (co[i] for i in tri.vertices)
        vol += a.dot(b.cross(cc)) / 6.0
    ev.to_mesh_clear()
    return vol


def verify(scn):
    print("\n" + "=" * 72)
    print("HOURGLASS RACE - VERIFICATION (measured from evaluated scene)")
    print("=" * 72)
    sim = STATE["sim"]; fps = STATE["fps"]
    frames = STATE["frames"]
    objs = STATE["planet_objs"]
    vols = {k: [] for k in objs}
    bvols = {k: [] for k in objs}
    for f in frames:
        scn.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for k, d in objs.items():
            vols[k].append(mesh_volume_world(d["top"], dg))
            if f in (frames[-1],):
                bvols[k].append(mesh_volume_world(d["heap"], dg) + mesh_volume_world(d["layer"], dg))
    ok = True
    print(f"{'planet':8} {'g':>7} {'table':>7} {'measured':>9} {'video@':>7} {'flow lin.':>10}  status")
    for name, g, _ in CONFIG["planets"]:
        v = vols[name]
        vmax = max(v)
        # first frame (after sand start) where top volume is (numerically) zero
        i0 = next(i for i, x in enumerate(v) if x > 0.5 * vmax)
        iz = next((i for i in range(i0, len(v)) if v[i] <= 1e-9 * vmax), None)
        assert iz is not None, f"{name}: top bulb never emptied inside the video"
        # volume is linear in sim time -> extrapolate the last two non-empty
        # frames to zero (exact for linear flow, frame-rate independent)
        i1, i2 = iz - 2, iz - 1
        t1, t2 = sim[i1], sim[i2]
        slope = (v[i2] - v[i1]) / (t2 - t1)
        t_empty = t2 - v[i2] / slope
        # linearity check: dV/dt measured early vs late must agree
        sim_start_i = next(i for i, t in enumerate(sim) if t > 0)
        def idx(frac):
            return next(i for i in range(sim_start_i, len(sim)) if sim[i] >= frac * t_empty)
        a, b, c2, d2 = idx(0.05), idx(0.35), idx(0.60), idx(0.95)
        s_early = (v[b] - v[a]) / (sim[b] - sim[a])     # nearly full bulb
        s_late = (v[d2] - v[c2]) / (sim[d2] - sim[c2])  # nearly empty bulb
        lin = abs(s_early / s_late - 1)
        expected = TABLE[name]
        good = abs(round(t_empty, 1) - expected) < 1e-6 and lin < 1e-3
        # conservation: everything ended in the bottom bulb
        cons = abs(bvols[name][-1] / vmax - 1) if bvols[name] else 0
        good = good and cons < 2e-2
        ok &= good
        print(f"{name:8} {g:7.2f} {expected:7.1f} {t_empty:9.3f} {STATE['finish_v'][name]:6.2f}s "
              f"{lin:10.2e}  {'OK' if good else 'FAIL'}  (bottom/initial vol err {cons:.1e})")
        assert good, f"{name}: measured {t_empty:.3f}s vs table {expected}"
    # time mapping
    mono = all(b >= a for a, b in zip(sim, sim[1:]))
    strict = all(b > a for a, b in zip(sim, sim[1:]) if a > 0)
    dur = len(frames) / fps
    print(f"\nvideo duration {dur:.2f} s ({len(frames)} frames @ {fps} fps) -> "
          f"{'OK' if 45 <= dur <= 60 else 'FAIL'} (45-60 s)")
    print(f"sim(video) monotonic: {mono}, strictly increasing after flip: {strict}")
    print(f"playback rate: 1x until {CONFIG['realtime_until']} s video, "
          f"{CONFIG['speed1']:.0f}x, then {STATE['speed2']:.2f}x; sim at last frame = {sim[-1]:.1f} s")
    print("finish (video s): " + ", ".join(f"{k} {v:.2f}" for k, v in STATE["finish_v"].items()))
    assert mono and strict and 45 <= dur <= 60
    assert all(v < dur for v in STATE["finish_v"].values())
    # on-screen text = table
    for name, d in objs.items():
        body = d["done_text"].data.body
        assert TABLE_FMT(TABLE[name]) in body, (name, body)
    print("on-screen finish labels match table: True")
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    print("=" * 72 + "\n")
    scn.frame_set(1)
    return ok


# =============================================================================
# MAIN
# =============================================================================
def main():
    opts = parse_args()
    scn = build(opts)
    if opts["verify"]:
        verify(scn)
    if opts["frames"]:
        out = resolve_out()
        r = scn.render
        if hasattr(r.image_settings, "media_type"):
            r.image_settings.media_type = "IMAGE"
        r.image_settings.file_format = "PNG"
        for f in opts["frames"]:
            scn.frame_set(f)
            r.filepath = os.path.join(out, f"frame_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
            print("[hourglass] wrote", r.filepath)
    elif CONFIG["RENDER"]:
        if opts["range"]:
            scn.frame_start, scn.frame_end = opts["range"]
        print(f"[hourglass] rendering {scn.frame_end} frames -> {scn.render.filepath}")
        bpy.ops.render.render(animation=True)
    else:
        print("[hourglass] scene built. Render with Render > Render Animation "
              "(or run headless with -- --render).")


if __name__ == "__main__":
    main()
