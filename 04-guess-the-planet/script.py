"""
Guess the Planet -- quiz series generator (brief 4)
====================================================

One self-contained, fully procedural Blender script (Blender 4.2 - 5.x).

  * Scripting tab: open this file, press Run (builds episode 1 + verifies).
  * Headless:      blender -b -P script.py -- --render            (all episodes)
                   blender -b -P script.py -- --render --episode 2
                   blender -b -P script.py -- --render --preview  (fast draft)
                   blender -b -P script.py -- --frames 1,120,400  (stills only)

Extra flags: --engine EEVEE|CYCLES|WORKBENCH, --res-pct N, --samples N,
             --out DIR, --no-verify.

Every fall is an exact analytic ballistic curve keyed on the ball (fall + damped
bounces), the stopwatch text is rewritten per frame by a frame_change_pre handler
(it also runs during animation renders), and the answer label is hidden by
keyframed visibility until the reveal frame.  The script measures the fall time
from 2 m for every planet by sampling the *evaluated* scene and asserts it
against the answer key.
"""

import bpy
import json
import math
import os
import sys

# =============================================================================
# CONFIG
# =============================================================================
CONFIG = {
    # (planet, answer options, bonus planet, bonus options). The planet must be
    # one of its options. 3 options for the main question, 4 for the bonus.
    "EPISODES": [
        ("MOON",    ["MOON", "MARS", "PLUTO"],     "NEPTUNE", ["EARTH", "NEPTUNE", "MARS", "JUPITER"]),
        ("JUPITER", ["MOON", "EARTH", "JUPITER"],  "MARS",    ["MOON", "MARS", "PLUTO", "EARTH"]),
        ("MARS",    ["MARS", "MOON", "PLUTO"],     "EARTH",   ["NEPTUNE", "JUPITER", "EARTH", "MARS"]),
        ("PLUTO",   ["MOON", "PLUTO", "MARS"],     "SUN",     ["JUPITER", "EARTH", "SUN", "NEPTUNE"]),
    ],
    "EPISODE": 1,                 # episode built when run from the Scripting tab
    "COMPARE_PLANET": "EARTH",    # side-by-side reference drop at the reveal
    "PREVIEW": False,             # True -> 50 % res, few samples (draft)
    "RENDER": False,              # True -> render all episodes when run
    "FPS": 30,
    "DURATION_S": 25.0,
    "RESOLUTION": (1080, 1920),
    "ENGINE": "EEVEE",            # EEVEE (default) | CYCLES | WORKBENCH
    "SAMPLES": 64,                # final; PREVIEW uses PREVIEW_SAMPLES
    "PREVIEW_SAMPLES": 8,
    "PREVIEW_RES_PCT": 50,
    "OUTPUT_DIR": "",             # "" -> ./guess_the_planet_renders next to the .blend / cwd
    "OUTPUT_FORMAT": "MP4",       # MP4 (falls back to PNG if FFmpeg unavailable) | PNG
    "DROP_HEIGHT": 2.0,           # metres, ball bottom above floor
    "BALL_RADIUS": 0.09,
    "RESTITUTION": 0.45,          # speed kept per bounce (same on every planet)
    # Beat sheet (seconds)
    "BEATS": {
        "drop1": 2.0, "drop2": 5.0,          # clip plays twice (2-8 s)
        "lock": 8.0, "count": (9.0, 10.0, 11.0),
        "reveal": 12.0, "reveal_drop": 13.0,  # label slams in, side-by-side drop
        "bonus": 18.0, "bonus_drop": 19.0, "bonus_reveal": 22.5,
    },
}

GRAVITY = {"SUN": 274.0, "JUPITER": 24.79, "NEPTUNE": 11.15, "EARTH": 9.81,
           "MARS": 3.71, "MOON": 1.62, "PLUTO": 0.62}
# Brief answer key: fall time from 2 m (s)
ANSWER_KEY = {"SUN": 0.12, "JUPITER": 0.40, "EARTH": 0.64, "MARS": 1.04,
              "MOON": 1.57, "PLUTO": 2.54, "NEPTUNE": 0.60}
KEY_TOL = 0.006   # answer key is rounded to 0.01 s

PREFIX = "GTP_"
HANDLER_NAME = "gtp_frame_handler"

# Overlay palette (linear RGB)
COL_TEXT = (1.0, 1.0, 1.0)
COL_YELLOW = (1.0, 0.78, 0.05)
COL_PLATE = (0.012, 0.013, 0.016)
COL_GREEN = (0.05, 0.55, 0.12)
COL_RED = (0.6, 0.04, 0.03)
COL_BLUE = (0.02, 0.18, 0.6)


# =============================================================================
# Args
# =============================================================================
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"render": CONFIG["RENDER"], "preview": CONFIG["PREVIEW"], "episode": None,
         "frames": None, "engine": CONFIG["ENGINE"], "res_pct": None,
         "samples": None, "out": CONFIG["OUTPUT_DIR"], "verify": True}
    i = 0
    while i < len(argv):
        k = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else None
        if k == "--render":
            a["render"] = True
        elif k == "--preview":
            a["preview"] = True
        elif k == "--no-verify":
            a["verify"] = False
        elif k == "--episode" and nxt:
            a["episode"] = int(nxt); i += 1
        elif k == "--frames" and nxt:
            a["frames"] = [int(x) for x in nxt.split(",") if x.strip()]; i += 1
        elif k == "--engine" and nxt:
            a["engine"] = nxt.upper(); i += 1
        elif k == "--res-pct" and nxt:
            a["res_pct"] = int(nxt); i += 1
        elif k == "--samples" and nxt:
            a["samples"] = int(nxt); i += 1
        elif k == "--out" and nxt:
            a["out"] = nxt; i += 1
        else:
            print("[GTP] ignoring unknown arg:", k)
        i += 1
    return a


# =============================================================================
# Physics (analytic, deterministic)
# =============================================================================
def drop_profile(g, h, e, min_h=0.004, max_bounces=14):
    """Free fall from height h (bottom of ball) then bounces keeping speed*e.
    Returns dict with first-impact time, impact times, apex times and arcs."""
    t0 = math.sqrt(2.0 * h / g)
    v = math.sqrt(2.0 * g * h) * e
    t = t0
    arcs, impacts, apexes = [], [t0], []
    while v * v / (2.0 * g) > min_h and len(arcs) < max_bounces:
        arcs.append((t, v))
        apexes.append(t + v / g)
        t += 2.0 * v / g
        impacts.append(t)
        v *= e
    return {"g": g, "h": h, "t_fall": t0, "impacts": impacts, "apexes": apexes,
            "arcs": arcs, "t_rest": t}


def profile_height(p, t):
    """Height of ball bottom above floor at time t after release."""
    if t <= 0.0:
        return p["h"]
    if t <= p["t_fall"]:
        return max(0.0, p["h"] - 0.5 * p["g"] * t * t)
    for ts, v in p["arcs"]:
        if ts <= t <= ts + 2.0 * v / p["g"]:
            tau = t - ts
            return max(0.0, v * tau - 0.5 * p["g"] * tau * tau)
    return 0.0


# =============================================================================
# Version-robust helpers
# =============================================================================
def iter_fcurves(id_data):
    """Yield F-curves of an ID's action for both legacy (<=4.3) and layered
    (4.4+/5.x) action APIs."""
    ad = getattr(id_data, "animation_data", None)
    if not ad or not ad.action:
        return
    act = ad.action
    try:
        fcs = act.fcurves  # removed in 5.0
        for fc in fcs:
            yield fc
        return
    except AttributeError:
        pass
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves:
                        yield fc
    except AttributeError:
        return


def make_linear(id_data):
    for fc in iter_fcurves(id_data):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'


def set_engine(scene, name):
    name = name.upper()
    if name in ("EEVEE", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        ids = ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT") if bpy.app.version >= (5, 0, 0) \
            else ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")
    elif name == "CYCLES":
        ids = ("CYCLES",)
    else:
        ids = ("BLENDER_WORKBENCH",)
    for eid in ids:
        try:
            scene.render.engine = eid
            return eid
        except TypeError:
            continue
    raise RuntimeError("Could not set render engine " + name)


def safe_set(obj, attr, value):
    if hasattr(obj, attr):
        try:
            setattr(obj, attr, value)
        except Exception:
            pass


# =============================================================================
# Scene reset
# =============================================================================
def clear_scene(scene):
    for o in list(scene.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in list(bpy.data.collections):
        if coll.name.startswith(PREFIX):
            bpy.data.collections.remove(coll)
    for datas in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                  bpy.data.cameras, bpy.data.lights, bpy.data.actions,
                  bpy.data.node_groups):
        for d in list(datas):
            if d.users == 0 or d.name.startswith(PREFIX):
                try:
                    datas.remove(d)
                except Exception:
                    pass


# =============================================================================
# Materials
# =============================================================================
def mat_emission(name, color, strength=1.0):
    m = bpy.data.materials.new(PREFIX + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (*color, 1.0)
    return m


def mat_principled(name, color, rough=0.6, spec=0.3):
    m = bpy.data.materials.new(PREFIX + name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs:
            b.inputs[key].default_value = spec
            break
    m.diffuse_color = (*color, 1.0)
    return m


def mat_ball(name):
    """Two-tone striped toy ball (neutral colours, stripes show the motion)."""
    m = bpy.data.materials.new(PREFIX + name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    at = nt.nodes.new("ShaderNodeMath"); at.operation = 'ARCTAN2'
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = 6.0 / math.pi          # 6 stripes
    fl = nt.nodes.new("ShaderNodeMath"); fl.operation = 'FLOOR'
    md = nt.nodes.new("ShaderNodeMath"); md.operation = 'FLOORED_MODULO' \
        if 'FLOORED_MODULO' in [i.identifier for i in md.bl_rna.properties['operation'].enum_items] else 'MODULO'
    md.inputs[1].default_value = 2.0
    mix = nt.nodes.new("ShaderNodeMix") if hasattr(bpy.types, "ShaderNodeMix") else nt.nodes.new("ShaderNodeMixRGB")
    if mix.bl_idname == "ShaderNodeMix":
        mix.data_type = 'RGBA'
        a_in, b_in, f_in, o = mix.inputs[6], mix.inputs[7], mix.inputs[0], mix.outputs[2]
    else:
        a_in, b_in, f_in, o = mix.inputs[1], mix.inputs[2], mix.inputs[0], mix.outputs[0]
    a_in.default_value = (0.85, 0.85, 0.83, 1.0)
    b_in.default_value = (0.05, 0.05, 0.06, 1.0)
    L = nt.links
    L.new(tc.outputs["Object"], sep.inputs[0])
    L.new(sep.outputs[1], at.inputs[0])
    L.new(sep.outputs[0], at.inputs[1])
    L.new(at.outputs[0], mul.inputs[0])
    L.new(mul.outputs[0], fl.inputs[0])
    L.new(fl.outputs[0], md.inputs[0])
    L.new(md.outputs[0], f_in)
    L.new(o, b.inputs["Base Color"])
    m.diffuse_color = (0.6, 0.6, 0.6, 1.0)
    return m


# =============================================================================
# Geometry helpers
# =============================================================================
def link(obj, coll):
    coll.objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, coll, mat=None):
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(PREFIX + name, me)
    if mat:
        me.materials.append(mat)
    return link(o, coll)


def box(name, size, loc, coll, mat=None):
    sx, sy, sz = (s * 0.5 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj(name, v, f, coll, mat)
    o.location = loc
    return o


def plane(name, w, h, coll, mat=None):
    v = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    return mesh_obj(name, v, [(0, 1, 2, 3)], coll, mat)


def uv_sphere(name, r, coll, mat, seg=48, rings=24):
    verts, faces = [], []
    verts.append((0, 0, r))
    for i in range(1, rings):
        th = math.pi * i / rings
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            verts.append((r * math.sin(th) * math.cos(ph), r * math.sin(th) * math.sin(ph), r * math.cos(th)))
    verts.append((0, 0, -r))
    bot = len(verts) - 1
    for j in range(seg):
        faces.append((0, 1 + j, 1 + (j + 1) % seg))
    for i in range(rings - 2):
        for j in range(seg):
            a = 1 + i * seg + j
            b = 1 + i * seg + (j + 1) % seg
            faces.append((a, a + seg, b + seg, b))
    base = 1 + (rings - 2) * seg
    for j in range(seg):
        faces.append((base + (j + 1) % seg, base + j, bot))
    o = mesh_obj(name, verts, faces, coll, mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def cyclorama(coll, mat):
    """Floor that curves seamlessly up into a back wall (infinity cove)."""
    prof = [(-8.0, 0.0), (1.0, 0.0)]
    R = 2.0
    for i in range(1, 13):
        a = (math.pi / 2) * i / 12
        prof.append((1.0 + R * math.sin(a), R - R * math.cos(a)))
    prof.append((1.0 + R, 9.0))
    W = 9.0
    verts, faces = [], []
    for y, z in prof:
        verts += [(-W, y, z), (W, y, z)]
    for i in range(len(prof) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    o = mesh_obj("Cyclorama", verts, faces, coll, mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def text_obj(name, body, size, coll, mat, align="CENTER", bold=True):
    cu = bpy.data.curves.new(PREFIX + name, 'FONT')
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = 'CENTER'
    if bold:
        cu.offset = size * 0.022     # faux-bold for readability
    o = bpy.data.objects.new(PREFIX + name, cu)
    cu.materials.append(mat)
    return link(o, coll)


def no_shadow(o):
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy",
                 "visible_transmission", "visible_volume_scatter"):
        safe_set(o, attr, False)


# =============================================================================
# Visibility keying
# =============================================================================
def key_hide(objs, frame, hidden):
    for o in objs:
        o.hide_render = hidden
        o.hide_viewport = hidden
        o.keyframe_insert("hide_render", frame=frame)
        o.keyframe_insert("hide_viewport", frame=frame)


def show_window(group, f_in, f_out, pop=True, slam=False):
    """Make an overlay group visible on frames [f_in, f_out) with a pop-in."""
    kids = [group] + list(group.children_recursive)
    first = 1
    if f_in > first:
        key_hide(kids, first, True)
    key_hide(kids, f_in, False)
    if f_out is not None:
        key_hide(kids, f_out, True)
    s_final = group.scale.copy()
    if pop:
        if f_in <= first:   # on screen and readable from frame 1, gentle settle = motion
            seq = [(first, 1.04), (first + 8, 1.0)]
        else:
            seq = [(f_in - 1, 0.0), (f_in, 1.6 if slam else 0.4), (f_in + 3, 0.92 if slam else 1.12),
                   (f_in + 5, 1.0)]
        for fr, s in seq:
            if fr < first:
                continue
            group.scale = s_final * max(s, 1e-4)
            group.keyframe_insert("scale", frame=fr)
        group.scale = s_final


# =============================================================================
# Overlay rig (text parented to camera, dark plates)
# =============================================================================
class Overlay:
    D = 1.0  # distance in front of camera

    def __init__(self, cam, coll):
        self.cam = cam
        self.coll = coll
        cd = cam.data
        self.hh = (cd.sensor_height * 0.5) / cd.lens * self.D
        rx, ry = CONFIG["RESOLUTION"]
        self.hw = self.hh * rx / ry
        self.mats = {}

    def mat(self, col, key):
        if key not in self.mats:
            self.mats[key] = mat_emission("ov_" + key, col)
        return self.mats[key]

    def label(self, name, body, u, v, size, color=COL_TEXT, plate=COL_PLATE,
              pad=(0.5, 0.35), max_w=0.92, fixed_w=None, plate_h=None):
        """u,v in [-1,1] screen coords, size as fraction of half frame height."""
        g = bpy.data.objects.new(PREFIX + "ov_" + name, None)
        g.empty_display_size = 0.02
        link(g, self.coll)
        g.parent = self.cam
        g.location = (u * self.hw, v * self.hh, -self.D)
        s = size * self.hh
        t = text_obj("ov_" + name + "_txt", body, s, self.coll,
                     self.mat(color, "c%.2f%.2f%.2f" % color))
        t.parent = g
        no_shadow(t)
        bpy.context.view_layer.update()
        w = t.dimensions.x
        limit = max_w * 2 * self.hw - pad[0] * s * 2
        if fixed_w:
            limit = min(limit, fixed_w * 2 * self.hw - pad[0] * s)
        if w > limit and w > 0:
            t.data.size *= limit / w
            t.data.offset *= limit / w
            bpy.context.view_layer.update()
            w = t.dimensions.x
        if plate is not None:
            pw = fixed_w * 2 * self.hw if fixed_w else w + pad[0] * s * 2
            ph = plate_h * self.hh if plate_h else s * (1.0 + pad[1] * 2)
            p = plane("ov_" + name + "_plate", pw, ph, self.coll,
                      self.mat(plate, "p%.3f%.3f%.3f" % plate))
            p.parent = g
            p.location = (0, -s * 0.02, -0.003)
            no_shadow(p)
            g["plate"] = p.name
        g["text"] = t.name
        return g


# =============================================================================
# Frame handler: stopwatches (deterministic, synced to frames)
# =============================================================================
def stopwatch_value(events, frame, fps):
    """events: list of [start_frame, fall_time]. Returns seconds shown."""
    cur = None
    for ev in events:
        if frame >= ev[0]:
            cur = ev
    if cur is None:
        return 0.0
    t = (frame - cur[0]) / fps
    return min(t, cur[1])


@bpy.app.handlers.persistent
def gtp_frame_handler(scene, depsgraph=None):
    data = scene.get("gtp_stopwatches")
    if not data:
        return
    try:
        sws = json.loads(data)
    except Exception:
        return
    fps = scene.render.fps / scene.render.fps_base
    frame = scene.frame_current
    for sw in sws:
        o = bpy.data.objects.get(sw["obj"])
        if o is None or o.type != 'FONT':
            continue
        val = stopwatch_value(sw["events"], frame, fps)
        body = "%s%5.2f s" % (sw.get("prefix", ""), val)
        if o.data.body != body:
            o.data.body = body


gtp_frame_handler.__name__ = HANDLER_NAME


def register_handler():
    for lst in (bpy.app.handlers.frame_change_pre,):
        for h in list(lst):
            if getattr(h, "__name__", "") == HANDLER_NAME:
                lst.remove(h)
        lst.append(gtp_frame_handler)


# =============================================================================
# Build
# =============================================================================
def sec2frame(s):
    return int(round(s * CONFIG["FPS"])) + 1


def key_drop(ball, fs, f_end, planet, h, r):
    """Key exact analytic fall+bounces for frames [fs, f_end). fs integer."""
    p = drop_profile(GRAVITY[planet], h, CONFIG["RESTITUTION"])
    fps = CONFIG["FPS"]
    frames = set(range(fs, f_end))
    for t in p["impacts"] + p["apexes"]:
        fr = fs + t * fps
        if fr < f_end - 1e-3:
            frames.add(round(fr, 6))
    for fr in sorted(frames):
        ball.location.z = r + profile_height(p, (fr - fs) / fps)
        ball.keyframe_insert("location", index=2, frame=fr)
    return p


def build_episode(scene, ep_index, args):
    planet, options, bonus, bonus_opts = CONFIG["EPISODES"][ep_index]
    assert planet in options, "episode %d: %s not in options" % (ep_index + 1, planet)
    assert bonus in bonus_opts, "episode %d: %s not in bonus options" % (ep_index + 1, bonus)
    compare = CONFIG["COMPARE_PLANET"]
    if compare == planet:
        compare = "MOON" if planet != "MOON" else "EARTH"

    clear_scene(scene)
    fps = CONFIG["FPS"]
    n_frames = int(round(CONFIG["DURATION_S"] * fps))
    scene.frame_start, scene.frame_end = 1, n_frames
    scene.render.fps, scene.render.fps_base = fps, 1.0
    scene.render.resolution_x, scene.render.resolution_y = CONFIG["RESOLUTION"]
    scene.render.resolution_percentage = 100
    scene.frame_set(1)

    coll = bpy.data.collections.new(PREFIX + "Episode")
    scene.collection.children.link(coll)
    B = CONFIG["BEATS"]
    F = {k: (sec2frame(v) if not isinstance(v, tuple) else tuple(sec2frame(x) for x in v))
         for k, v in B.items()}
    H, R = CONFIG["DROP_HEIGHT"], CONFIG["BALL_RADIUS"]

    # ---------- studio (neutral grey, no planet colours) ----------
    world = bpy.data.worlds.get(PREFIX + "World") or bpy.data.worlds.new(PREFIX + "World")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.20, 0.20, 0.21, 1.0)
    bg.inputs["Strength"].default_value = 0.5
    scene.world = world

    grey = mat_principled("StudioGrey", (0.16, 0.16, 0.17), rough=0.75, spec=0.2)
    cyclorama(coll, grey)
    ruler_mat = mat_principled("Ruler", (0.80, 0.80, 0.78), rough=0.5)
    ink = mat_principled("Ink", (0.02, 0.02, 0.02), rough=0.6)
    accent = mat_emission("StartLine", (1.0, 0.75, 0.05), 2.0)

    LANE_MAIN, LANE_CMP = -0.36, 0.36
    box("Ruler", (0.15, 0.02, H + 0.06), (0, 0.10, (H + 0.06) / 2), coll, ruler_mat)
    for i in range(0, 21):
        z = i * 0.1
        L = 0.10 if i % 5 == 0 else 0.05
        box("Tick%02d" % i, (L, 0.006, 0.010), (-0.075 + L / 2, 0.088, z), coll, ink)
    for z, s in ((0.5, "0.5"), (1.0, "1.0"), (1.5, "1.5"), (2.0, "2 m")):
        t = text_obj("RulerNum_" + s, s, 0.075, coll, ruler_mat, align="LEFT")
        t.location = (0.095, 0.10, z + (0.045 if z >= H else 0.0))
        t.rotation_euler = (math.pi / 2, 0, 0)
    box("StartLine", (1.3, 0.004, 0.008), (0, 0.12, H), coll, accent)
    box("FloorLine", (1.3, 0.004, 0.006), (0, 0.12, 0.003), coll, ink)
    clamp_mat = mat_principled("Clamp", (0.08, 0.08, 0.09), rough=0.4)
    box("Arm", (0.95, 0.03, 0.03), (0, 0.10, H + 2 * R + 0.06), coll, clamp_mat)
    for x in (LANE_MAIN, LANE_CMP):
        box("Clamp%.2f" % x, (0.05, 0.05, 0.05), (x, 0.0, H + 2 * R + 0.03), coll, clamp_mat)
        box("Rod%.2f" % x, (0.02, 0.10, 0.02), (x, 0.05, H + 2 * R + 0.06), coll, clamp_mat)

    # lights
    def area(name, loc, rot, energy, size):
        ld = bpy.data.lights.new(PREFIX + name, 'AREA')
        ld.energy, ld.size = energy, size
        o = bpy.data.objects.new(PREFIX + name, ld)
        o.location, o.rotation_euler = loc, rot
        return link(o, coll)
    area("Key", (-2.2, -2.5, 4.0), (math.radians(45), 0, math.radians(-40)), 260, 2.5)
    area("Fill", (2.5, -3.0, 2.0), (math.radians(70), 0, math.radians(40)), 90, 3.0)
    area("Top", (0, 0.5, 5.0), (0, 0, 0), 120, 4.0)

    # balls
    bmat = mat_ball("Ball")
    ball = uv_sphere("Ball", R, coll, bmat)
    ball.location = (LANE_MAIN, 0, R + H)
    ball.rotation_euler = (math.radians(20), math.radians(-15), 0)
    cball = uv_sphere("BallCompare", R, coll, bmat)
    cball.location = (LANE_CMP, 0, R + H)
    cball.rotation_euler = (math.radians(20), math.radians(-15), 0)

    prefs = bpy.context.preferences.edit
    old_interp = prefs.keyframe_new_interpolation_type
    try:
        prefs.keyframe_new_interpolation_type = 'LINEAR'
        # main ball timeline
        drops = []   # (obj, start_frame, planet)
        ball.location.z = R + H
        ball.keyframe_insert("location", index=2, frame=1)
        key_drop(ball, F["drop1"], F["drop2"], planet, H, R)
        key_drop(ball, F["drop2"], F["reveal_drop"], planet, H, R)
        key_drop(ball, F["reveal_drop"], F["bonus"], planet, H, R)
        ball.location.z = R + H
        ball.keyframe_insert("location", index=2, frame=F["bonus"])
        key_drop(ball, F["bonus_drop"], n_frames + 1, bonus, H, R)
        drops += [(ball, F["drop1"], planet), (ball, F["drop2"], planet),
                  (ball, F["reveal_drop"], planet), (ball, F["bonus_drop"], bonus)]
        # comparison ball (visible only during reveal)
        cball.location.z = R + H
        cball.keyframe_insert("location", index=2, frame=1)
        key_drop(cball, F["reveal_drop"], n_frames + 1, compare, H, R)
        drops.append((cball, F["reveal_drop"], compare))
        key_hide([cball], 1, True)
        key_hide([cball], F["reveal"], False)
        key_hide([cball], F["bonus"], True)

        # ---------- camera ----------
        cd = bpy.data.cameras.new(PREFIX + "Cam")
        cd.lens, cd.sensor_fit, cd.sensor_height, cd.sensor_width = 35.0, 'VERTICAL', 36.0, 36.0
        cd.clip_start, cd.clip_end = 0.05, 100.0
        cam = link(bpy.data.objects.new(PREFIX + "Camera", cd), coll)
        cam.rotation_euler = (math.radians(90), 0, 0)
        scene.camera = cam
        cam.location = (0.0, -4.75, 1.08)
        cam.keyframe_insert("location", frame=1)
        cam.location = (0.0, -4.45, 1.08)
        cam.keyframe_insert("location", frame=n_frames)

        # ---------- overlays ----------
        ov = Overlay(cam, coll)
        V_TITLE, V_SUB, V_SW, V_BTN = 0.80, 0.665, -0.60, -0.80
        hook = ov.label("hook", "WHICH PLANET IS THIS?", 0, V_TITLE, 0.085)
        show_window(hook, 1, F["drop1"])
        hook2 = ov.label("hook2", "Most people get this wrong", 0, V_SUB, 0.055, color=COL_YELLOW)
        show_window(hook2, 1, F["drop1"])
        watch = ov.label("watch", "WATCH THE DROP  ·  2 m", 0, V_TITLE, 0.075)
        show_window(watch, F["drop1"], F["lock"])
        again = ov.label("again", "ONE MORE TIME", 0, V_SUB, 0.055, color=COL_YELLOW)
        show_window(again, F["drop2"], F["lock"])
        lock = ov.label("lock", "LOCK IN YOUR ANSWER", 0, V_TITLE, 0.08, color=COL_YELLOW)
        show_window(lock, F["lock"], F["reveal"])
        lock2 = ov.label("lock2", "Comment A, B or C below", 0, V_SUB, 0.05)
        show_window(lock2, F["lock"], F["reveal"])
        for i, fr in enumerate(F["count"]):
            end = F["count"][i + 1] if i + 1 < len(F["count"]) else F["reveal"]
            c = ov.label("count%d" % (3 - i), str(3 - i), 0, 0.12, 0.30, color=COL_YELLOW,
                         pad=(0.35, 0.12))
            show_window(c, fr, end, slam=True)

        # answer label: hidden (keyed) until the reveal frame
        ans = ov.label("answer", "%s  ·  %.2f m/s²" % (planet, GRAVITY[planet]), 0, V_TITLE, 0.085,
                       plate=COL_GREEN)
        show_window(ans, F["reveal"], F["bonus"], slam=True)
        cmp_cap = ov.label("vs", "vs %s %.2f m/s²  (same 2 m drop)" % (compare, GRAVITY[compare]),
                           0, V_SUB, 0.045)
        show_window(cmp_cap, F["reveal"] + 6, F["bonus"])

        # stopwatches
        sws = []
        sw_clip = ov.label("sw_clip", " 0.00 s", 0, V_SW, 0.09, pad=(0.45, 0.3), fixed_w=0.5)
        show_window(sw_clip, 1, F["reveal"], pop=False)
        sws.append({"obj": sw_clip["text"], "prefix": "",
                    "events": [[F["drop1"], ANSWER_FALL(planet)], [F["drop2"], ANSWER_FALL(planet)]]})
        sw_l = ov.label("sw_l", "%s  0.00 s" % planet, -0.5, V_SW, 0.055, pad=(0.3, 0.4),
                        fixed_w=0.48)
        show_window(sw_l, F["reveal"], F["bonus"])
        sws.append({"obj": sw_l["text"], "prefix": planet + "  ",
                    "events": [[F["reveal_drop"], ANSWER_FALL(planet)]]})
        sw_r = ov.label("sw_r", "%s  0.00 s" % compare, 0.5, V_SW, 0.055, pad=(0.3, 0.4),
                        fixed_w=0.48, plate=COL_BLUE)
        show_window(sw_r, F["reveal"], F["bonus"])
        sws.append({"obj": sw_r["text"], "prefix": compare + "  ",
                    "events": [[F["reveal_drop"], ANSWER_FALL(compare)]]})
        sw_b = ov.label("sw_bonus", " 0.00 s", 0, V_SW, 0.09, pad=(0.45, 0.3), fixed_w=0.5)
        show_window(sw_b, F["bonus"], None, pop=False)
        sws.append({"obj": sw_b["text"], "prefix": "",
                    "events": [[F["bonus_drop"], ANSWER_FALL(bonus)]]})
        scene["gtp_stopwatches"] = json.dumps(sws)

        # answer buttons (3 across)
        letters = "ABCD"
        n = len(options)
        bw = 2.0 / n * 0.92
        for i, opt in enumerate(options):
            u = -1 + (2.0 / n) * (i + 0.5)
            btn = ov.label("btn%d" % i, "%s  %s" % (letters[i], opt), u, V_BTN, 0.05,
                           fixed_w=bw / 2, plate_h=0.10)
            show_window(btn, 1, F["bonus"])
            if opt == planet:
                hl = ov.label("btn%d_ok" % i, "%s  %s" % (letters[i], opt), u, V_BTN, 0.05,
                              fixed_w=bw / 2, plate_h=0.10, plate=COL_GREEN)
                hl.location.z += 0.001
                show_window(hl, F["reveal"], F["bonus"], slam=True)

        # bonus round
        bt = ov.label("bonus_t", "BONUS ROUND  ·  HARDER", 0, V_TITLE, 0.075, color=COL_YELLOW)
        show_window(bt, F["bonus"], F["bonus_reveal"], slam=True)
        bt2 = ov.label("bonus_t2", "Which planet now?", 0, V_SUB, 0.055)
        show_window(bt2, F["bonus"], F["bonus_reveal"])
        bans = ov.label("bonus_ans", "%s  ·  %.2f m/s²" % (bonus, GRAVITY[bonus]), 0, V_TITLE, 0.085,
                        plate=COL_GREEN)
        show_window(bans, F["bonus_reveal"], None, slam=True)
        bend = ov.label("bonus_end", "How many did you get? Comment below", 0, V_SUB, 0.045,
                        color=COL_YELLOW)
        show_window(bend, F["bonus_reveal"] + 8, None)
        cols = 2
        for i, opt in enumerate(bonus_opts):
            r_, c_ = divmod(i, cols)
            u = -0.5 + c_ * 1.0
            v = -0.68 - r_ * 0.13
            btn = ov.label("bbtn%d" % i, "%s  %s" % (letters[i], opt), u, v, 0.05,
                           fixed_w=0.46, plate_h=0.10)
            show_window(btn, F["bonus"] + 2 * i, None)
            if opt == bonus:
                hl = ov.label("bbtn%d_ok" % i, "%s  %s" % (letters[i], opt), u, v, 0.05,
                              fixed_w=0.46, plate_h=0.10, plate=COL_GREEN)
                hl.location.z += 0.001
                show_window(hl, F["bonus_reveal"], None, slam=True)
        # bonus stopwatch sits above the 2x2 grid
        sw_b.location.y = -0.43 * ov.hh
    finally:
        prefs.keyframe_new_interpolation_type = old_interp

    # belt and braces: force LINEAR on every animated object (both action APIs)
    for o in scene.objects:
        make_linear(o)

    scene["gtp_episode"] = ep_index + 1
    scene["gtp_meta"] = json.dumps({
        "planet": planet, "bonus": bonus, "compare": compare,
        "reveal": F["reveal"], "bonus_reveal": F["bonus_reveal"],
        "answer_obj": ans.name, "bonus_obj": bans.name,
        "drops": [[o.name, fs, pl] for o, fs, pl in drops],
    })
    register_handler()
    scene.frame_set(1)
    return scene


def ANSWER_FALL(planet):
    return math.sqrt(2.0 * CONFIG["DROP_HEIGHT"] / GRAVITY[planet])


# =============================================================================
# Render settings
# =============================================================================
def configure_render(scene, args, out_dir, ep_index):
    eng = set_engine(scene, args["engine"])
    prev = args["preview"]
    samples = args["samples"] or (CONFIG["PREVIEW_SAMPLES"] if prev else CONFIG["SAMPLES"])
    scene.render.resolution_percentage = args["res_pct"] or (CONFIG["PREVIEW_RES_PCT"] if prev else 100)
    if "EEVEE" in eng:
        safe_set(scene.eevee, "taa_render_samples", samples)
        safe_set(scene.eevee, "use_shadows", True)
    elif eng == "CYCLES":
        scene.cycles.samples = samples
        safe_set(scene.cycles, "use_denoising", True)
        safe_set(scene.cycles, "device", 'CPU')
    else:
        sh = scene.display.shading
        safe_set(sh, "light", 'STUDIO')
        safe_set(sh, "color_type", 'MATERIAL')
    vs = scene.view_settings
    try:
        vs.view_transform = 'Standard'   # keep overlay colours true
    except TypeError:
        pass
    scene.render.use_lock_interface = True   # safe text edits from handler during render
    planet = CONFIG["EPISODES"][ep_index][0].lower()
    base = os.path.join(out_dir, "ep%02d_%s" % (ep_index + 1, planet))
    img = scene.render.image_settings
    fmt = CONFIG["OUTPUT_FORMAT"].upper()
    if fmt == "MP4" and not args["frames"]:
        try:
            if hasattr(img, "media_type"):
                img.media_type = 'VIDEO'     # Blender 5.x
            img.file_format = 'FFMPEG'
            ff = scene.render.ffmpeg
            ff.format = 'MPEG4'
            ff.codec = 'H264'
            safe_set(ff, "constant_rate_factor", 'HIGH')
            safe_set(ff, "audio_codec", 'NONE')
            scene.render.filepath = base + "_"
            return eng
        except Exception as e:
            print("[GTP] FFmpeg unavailable (%s), writing PNG frames" % e)
    if hasattr(img, "media_type"):
        try:
            img.media_type = 'IMAGE'
        except Exception:
            pass
    img.file_format = 'PNG'
    scene.render.filepath = os.path.join(base, "frame_")
    return eng


def resolve_out_dir(arg_out):
    if arg_out:
        return os.path.abspath(bpy.path.abspath(arg_out))
    if bpy.data.filepath:
        return os.path.join(os.path.dirname(bpy.data.filepath), "guess_the_planet_renders")
    return os.path.join(os.getcwd(), "guess_the_planet_renders")


# =============================================================================
# Verification (samples the evaluated scene)
# =============================================================================
def eval_z(scene, obj, frame_float):
    f = int(math.floor(frame_float))
    scene.frame_set(f, subframe=frame_float - f)
    dg = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(dg).matrix_world.translation.z


def measure_fall(scene, obj, fs, r, max_frames):
    """Time from release (frame fs) until the ball bottom first touches the
    floor: scan the evaluated scene in sub-frame steps until the ball stops
    descending, then ternary-search the contact minimum inside that bracket."""
    z0 = eval_z(scene, obj, fs)
    start_h = z0 - r
    step = 0.05   # frames; far shorter than any bounce arc
    f, z_prev = float(fs), z0
    while True:
        if f > fs + max_frames:
            raise AssertionError("ball %s never landed" % obj.name)
        z = eval_z(scene, obj, f + step)
        if z >= z_prev and z_prev < z0 - 1e-6:
            break
        z_prev = z
        f += step
    lo, hi = f - step, f + step
    for _ in range(60):
        m1, m2 = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
        if eval_z(scene, obj, m1) <= eval_z(scene, obj, m2):
            hi = m2
        else:
            lo = m1
    t_hit = 0.5 * (lo + hi)
    contact = eval_z(scene, obj, t_hit) - r
    assert abs(contact) < 1e-3, "ball %s: lowest point %.4f m off the floor" % (obj.name, contact)
    return (t_hit - fs) / CONFIG["FPS"], start_h


def verify_answer_key(scene):
    """Drop a temp ball for every planet in the answer key, sample the evaluated
    scene and assert fall time from 2 m."""
    print("\n[GTP] === Answer-key verification (fall from %.1f m, sampled from evaluated scene) ==="
          % CONFIG["DROP_HEIGHT"])
    coll = bpy.data.collections.new(PREFIX + "Verify")
    scene.collection.children.link(coll)
    R, H = CONFIG["BALL_RADIUS"], CONFIG["DROP_HEIGHT"]
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    balls = {}
    try:
        prefs.keyframe_new_interpolation_type = 'LINEAR'
        mat = mat_principled("VerifyBall", (0.5, 0.5, 0.5))
        for i, pl in enumerate(ANSWER_KEY):
            b = uv_sphere("Verify_" + pl, R, coll, mat, seg=8, rings=4)
            b.location = (50 + i, 0, R + H)
            b.hide_render = True
            key_drop(b, 10, 10 + 4 * CONFIG["FPS"], pl, H, R)
            make_linear(b)
            balls[pl] = b
    finally:
        prefs.keyframe_new_interpolation_type = old
    ok = True
    rows = []
    for pl, b in balls.items():
        t, h0 = measure_fall(scene, b, 10, R, 4 * CONFIG["FPS"])
        exp = ANSWER_KEY[pl]
        good = abs(t - exp) <= KEY_TOL and abs(h0 - H) < 1e-4
        ok &= good
        rows.append((pl, GRAVITY[pl], h0, t, exp, good))
        print("[GTP]   %-8s g=%6.2f  drop=%.3f m  measured=%.4f s  key=%.2f s  %s"
              % (pl, GRAVITY[pl], h0, t, exp, "OK" if good else "FAIL"))
    for b in balls.values():
        bpy.data.objects.remove(b, do_unlink=True)
    bpy.data.collections.remove(coll)
    scene.frame_set(1)
    assert ok, "Answer-key verification failed"
    print("[GTP] Answer key: ALL %d PLANETS MATCH" % len(rows))
    return rows


def verify_episode(scene):
    meta = json.loads(scene["gtp_meta"])
    R = CONFIG["BALL_RADIUS"]
    print("[GTP] --- Episode %d verification (%s, bonus %s) ---"
          % (scene["gtp_episode"], meta["planet"], meta["bonus"]))
    for name, fs, pl in meta["drops"]:
        obj = bpy.data.objects[name]
        t, h0 = measure_fall(scene, obj, fs, R, 4 * CONFIG["FPS"])
        exp = ANSWER_KEY[pl]
        good = abs(t - exp) <= KEY_TOL and abs(h0 - CONFIG["DROP_HEIGHT"]) < 1e-4
        print("[GTP]   %-14s frame %3d  %-8s drop=%.3f m  measured=%.4f s  key=%.2f  %s"
              % (name.replace(PREFIX, ""), fs, pl, h0, t, exp, "OK" if good else "FAIL"))
        assert good, "episode drop mismatch"
    # stopwatch freezes at the exact fall time
    sws = json.loads(scene["gtp_stopwatches"])
    sw = sws[0]
    fr = sw["events"][0][0] + int(3.0 * CONFIG["FPS"]) - 1
    scene.frame_set(fr)
    body = bpy.data.objects[sw["obj"]].data.body
    print("[GTP]   stopwatch at frame %d reads '%s'" % (fr, body.strip()))
    assert body.strip() == "%.2f s" % ANSWER_KEY[meta["planet"]], "stopwatch mismatch"

    # answer labels must be invisible before their reveal
    def visible(gname, f):
        scene.frame_set(f)
        g = bpy.data.objects[gname]
        t = bpy.data.objects[g["text"]]
        dg = bpy.context.evaluated_depsgraph_get()
        sc = g.evaluated_get(dg).matrix_world.to_scale().length
        return (not t.hide_render) and sc > 1e-3
    for gname, rf in ((meta["answer_obj"], meta["reveal"]), (meta["bonus_obj"], meta["bonus_reveal"])):
        before = [f for f in range(1, rf)]
        leaks = [f for f in before if visible(gname, f)]
        assert not leaks, "answer label visible before reveal at frames %s" % leaks[:5]
        assert visible(gname, rf + 6), "answer label not visible after reveal"
        print("[GTP]   %s hidden on frames 1-%d, visible from %d: OK"
              % (gname.replace(PREFIX, ""), rf - 1, rf))
    scene.frame_set(1)
    print("[GTP] Episode %d: VERIFIED" % scene["gtp_episode"])


# =============================================================================
# Main
# =============================================================================
def main():
    args = parse_args()
    scene = bpy.context.scene
    n = len(CONFIG["EPISODES"])
    if args["episode"]:
        eps = [args["episode"] - 1]
    elif args["render"]:
        eps = list(range(n))
    else:
        eps = [CONFIG["EPISODE"] - 1]
    for e in eps:
        assert 0 <= e < n, "episode out of range"
    out_dir = resolve_out_dir(args["out"])

    if args["verify"]:
        clear_scene(scene)
        verify_answer_key(scene)

    for e in eps:
        build_episode(scene, e, args)
        if args["verify"]:
            verify_episode(scene)
        eng = configure_render(scene, args, out_dir, e)
        if args["frames"] or args["render"]:
            os.makedirs(out_dir, exist_ok=True)
        print("[GTP] Episode %d built: %s, engine %s, %d%% res"
              % (e + 1, CONFIG["EPISODES"][e][0], eng, scene.render.resolution_percentage))
        if args["frames"]:
            base = scene.render.filepath
            planet = CONFIG["EPISODES"][e][0].lower()
            for f in args["frames"]:
                scene.frame_set(f)
                scene.render.filepath = os.path.join(out_dir, "ep%02d_%s_f%04d.png" % (e + 1, planet, f))
                bpy.ops.render.render(write_still=True)
                print("[GTP] wrote", scene.render.filepath)
            scene.render.filepath = base
        elif args["render"]:
            print("[GTP] rendering episode %d -> %s" % (e + 1, scene.render.filepath))
            bpy.ops.render.render(animation=True)
    scene.frame_set(1)
    print("[GTP] done.")


main()
