"""
THE IMPOSSIBLE BOUNCE  -  planet-gravity short #3  (Blender 4.2 - 5.x)
=======================================================================

A ball is dropped 2 m on the Sun. Every impact keeps only 80 % of its speed
(64 % of its energy) - yet it bounces HIGHER every time, because gravity
switches to a lighter planet at each impact:

    Sun -> Jupiter -> Earth -> Mars -> Moon -> Pluto

The motion is exact analytic ballistics (no simulation): one keyframe per
video frame, computed from z(t) = v0*t - g*t^2/2 for each planet.
After building, the script samples the evaluated scene frame by frame, fits a
parabola to every bounce, and asserts the measured numbers match the brief.

Run
---
  Scripting tab  : open this file, press Run (builds scene + verifies, no render)
  Headless       : blender -b -P script.py -- --render          (full video)
                   blender -b -P script.py -- --preview         (low-res contact frames)
                   blender -b -P script.py -- --frames 1 200    (frame range)
                   blender -b -P script.py -- --still 90 300 700 (single frames)
  Extra options  : --engine EEVEE|CYCLES|WORKBENCH  --scale 50  --samples 16
                   --out /some/folder  --mp4  --no-verify

Everything (3D scene + text overlays) renders in ONE pass: all captions are
text objects parented to the camera, with dark plates behind them.
"""

import bpy
import bmesh
import math
import os
import random
import sys

from bpy.app.handlers import persistent

# =============================================================================
# CONFIG
# =============================================================================
CONFIG = {
    # --- output -----------------------------------------------------------
    "RES_X": 1080,
    "RES_Y": 1920,
    "FPS": 30,
    "ENGINE": "EEVEE",            # EEVEE (default) | CYCLES | WORKBENCH
    "PREVIEW": False,              # True -> low-res, low-sample, every Nth frame
    "RENDER": False,               # True -> render the full animation after building
    "PREVIEW_SCALE": 40,           # % resolution for preview
    "PREVIEW_STEP": 6,             # render every Nth frame in preview
    "EEVEE_SAMPLES": 32,
    "EEVEE_SAMPLES_PREVIEW": 8,
    "CYCLES_SAMPLES": 64,
    "CYCLES_SAMPLES_PREVIEW": 12,
    "OUTPUT_DIR": "",              # "" -> <folder of this script>/renders/03 (or //renders/03)
    "OUTPUT_FORMAT": "PNG",        # PNG (frame sequence) | MP4
    "VERIFY": True,                # sample the scene + assert numbers match the brief
    # --- physics ----------------------------------------------------------
    "DROP_HEIGHT": 2.0,            # m, initial drop on the Sun
    "RESTITUTION": 0.8,            # speed kept per impact (energy kept = 0.64)
    "SEQUENCE": ["Sun", "Jupiter", "Earth", "Mars", "Moon", "Pluto"],
    # playback speed per planet segment (1 = real time). Brief: speed up Mars/Moon/Pluto 2-4x
    "SPEED": {"Sun": 1.0, "Jupiter": 1.0, "Earth": 1.0, "Mars": 2.0, "Moon": 2.5, "Pluto": 2.5},
    "HOOK_SECONDS": 3.5,           # ball held 2 m above the Sun while the hook caption reads
    "TAIL_SECONDS": 1.0,           # after the final Pluto landing (next bounce starts)
    # --- look -------------------------------------------------------------
    "BALL_RADIUS": 0.28,
    "FONT_PATH": "",               # optional .ttf/.otf; otherwise a bold system font or Blender's built-in
    "SEED": 3,
}

PLANETS = {
    #           g (m/s^2)  sky colour             ground colour         accent (labels/pads)   ground glow  base stars
    "Sun":     dict(g=274.0, sky=(0.30, 0.07, 0.015), ground=(1.00, 0.36, 0.06), accent=(1.00, 0.55, 0.12), glow=1.4, stars=0.0),
    "Jupiter": dict(g=24.79, sky=(0.72, 0.50, 0.30), ground=(0.55, 0.38, 0.24), accent=(0.95, 0.68, 0.40), glow=0.0, stars=0.0),
    "Earth":   dict(g=9.81, sky=(0.33, 0.58, 0.95), ground=(0.16, 0.42, 0.12), accent=(0.35, 0.80, 0.45), glow=0.0, stars=0.0),
    "Mars":    dict(g=3.71, sky=(0.86, 0.62, 0.38), ground=(0.52, 0.19, 0.07), accent=(0.95, 0.45, 0.20), glow=0.0, stars=0.0),
    "Moon":    dict(g=1.62, sky=(0.006, 0.006, 0.008), ground=(0.42, 0.42, 0.42), accent=(0.80, 0.80, 0.84), glow=0.0, stars=0.8),
    "Pluto":   dict(g=0.62, sky=(0.008, 0.010, 0.022), ground=(0.80, 0.85, 0.92), accent=(0.68, 0.84, 1.00), glow=0.0, stars=1.0),
}

# Numbers stated in the brief (planet: launch speed m/s, peak m, air time s, energy %)
BRIEF = {
    "sun_impact_speed": 33.1,
    "Jupiter": (26.5, 14.0, 2.1, 64.0),
    "Earth":   (21.2, 23.0, 4.3, 41.0),
    "Mars":    (17.0, 39.0, 9.1, 26.0),
    "Moon":    (13.6, 57.0, 16.7, 17.0),
    "Pluto":   (10.8, 95.0, 35.0, 11.0),
}

PAD_TOP = 0.06          # contact height (top of the landing pad), m
BALL_X = 0.45           # ball column
RULER_X = -0.55         # ruler column
CAM_X = 0.15
CAM_DIST = 6.0
SENSOR_H = 36.0
LENS = 26.0
T_HALF = (SENSOR_H / 2.0) / LENS   # tan(vertical half-FOV)
PX = T_HALF / 960.0                 # 1 px of a 1920-tall frame, in camera units at distance 1
BALL_Y_DES = -0.085                 # desired ball position (normalised, -1 bottom .. 1 top)
BALL_Y_MIN, BALL_Y_MAX = -0.40, 0.26

# =============================================================================
# argument parsing
# =============================================================================


def parse_args(cfg):
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    opts = {"frames": None, "stills": None, "engine": None, "scale": None,
            "samples": None, "out": None}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--render":
            cfg["RENDER"] = True
        elif a == "--preview":
            cfg["PREVIEW"] = True
            cfg["RENDER"] = True
        elif a == "--no-verify":
            cfg["VERIFY"] = False
        elif a == "--mp4":
            cfg["OUTPUT_FORMAT"] = "MP4"
        elif a == "--frames":
            opts["frames"] = (int(args[i + 1]), int(args[i + 2]))
            cfg["RENDER"] = True
            i += 2
        elif a == "--still":
            st = []
            while i + 1 < len(args) and not args[i + 1].startswith("--"):
                st.append(int(args[i + 1]))
                i += 1
            opts["stills"] = st
            cfg["RENDER"] = True
        elif a == "--engine":
            opts["engine"] = args[i + 1].upper()
            i += 1
        elif a == "--scale":
            opts["scale"] = int(args[i + 1])
            i += 1
        elif a == "--samples":
            opts["samples"] = int(args[i + 1])
            i += 1
        elif a == "--out":
            opts["out"] = args[i + 1]
            i += 1
        else:
            print("[impossible-bounce] ignoring unknown arg:", a)
        i += 1
    if opts["engine"]:
        cfg["ENGINE"] = opts["engine"]
    return opts


# =============================================================================
# analytic timeline (the "physics")
# =============================================================================


class Timeline:
    """Piecewise ballistic motion mapped onto video time with per-segment playback speed."""

    def __init__(self, cfg):
        seq = cfg["SEQUENCE"]
        e = cfg["RESTITUTION"]
        H = cfg["DROP_HEIGHT"]
        self.segs = []
        tv, tp = 0.0, 0.0
        g0 = PLANETS[seq[0]]["g"]
        hook = cfg["HOOK_SECONDS"]
        self.segs.append(dict(kind="hold", planet=seq[0], g=g0, z0=H, v0=0.0, T=0.0,
                              speed=1.0, t0=0.0, t1=hook, p0=0.0, idx=0))
        tv = hook
        T = math.sqrt(2 * H / g0)
        sp = cfg["SPEED"][seq[0]]
        self.segs.append(dict(kind="fall", planet=seq[0], g=g0, z0=H, v0=0.0, T=T,
                              speed=sp, t0=tv, t1=tv + T / sp, p0=tp, idx=1))
        tv += T / sp
        tp += T
        v = g0 * T                       # impact speed on the Sun
        self.sun_impact = v
        for name in seq[1:]:
            g = PLANETS[name]["g"]
            v *= e
            T = 2 * v / g
            sp = cfg["SPEED"][name]
            self.segs.append(dict(kind="bounce", planet=name, g=g, z0=0.0, v0=v, T=T,
                                  speed=sp, t0=tv, t1=tv + T / sp, p0=tp, idx=len(self.segs)))
            tv += T / sp
            tp += T
        last = seq[-1]
        g = PLANETS[last]["g"]
        v *= e
        sp = cfg["SPEED"][last]
        tail = cfg["TAIL_SECONDS"]
        self.segs.append(dict(kind="tail", planet=last, g=g, z0=0.0, v0=v, T=tail * sp,
                              speed=sp, t0=tv, t1=tv + tail, p0=tp, idx=len(self.segs)))
        self.total = tv + tail
        # impacts: video time + the planet whose gravity starts at that impact
        self.impacts = []
        for s, nxt in zip(self.segs[1:-1], self.segs[2:]):
            self.impacts.append(dict(t=s["t1"], planet=nxt["planet"], v=nxt["v0"], seg=nxt["idx"]))
        # time of each bounce apex (video)
        self.apexes = {}
        for s in self.segs:
            if s["kind"] == "bounce":
                ta = s["t0"] + (s["v0"] / s["g"]) / s["speed"]
                self.apexes[s["planet"]] = (ta, s["v0"] ** 2 / (2 * s["g"]))

    def seg_at(self, t):
        for s in self.segs:
            if t < s["t1"]:
                return s
        return self.segs[-1]

    def state(self, t):
        s = self.seg_at(t)
        tau = 0.0 if s["kind"] == "hold" else (t - s["t0"]) * s["speed"]
        z = s["z0"] + s["v0"] * tau - 0.5 * s["g"] * tau * tau
        vel = s["v0"] - s["g"] * tau
        if s["kind"] == "hold":
            vel = 0.0
        return dict(seg=s, z=max(0.0, z), vel=vel, phys=s["p0"] + tau, speed=s["speed"])

    def max_height_until(self, t):
        h = CONFIG["DROP_HEIGHT"]
        best = 0.0
        for s in self.segs:
            if s["kind"] in ("bounce", "tail") and t >= s["t0"]:
                st = self.state(min(t, s["t1"] - 1e-9))
                apex_t = s["t0"] + (s["v0"] / s["g"]) / s["speed"]
                if t >= apex_t:
                    best = max(best, s["v0"] ** 2 / (2 * s["g"]))
                else:
                    best = max(best, st["z"])
        return best if best > 0 else 0.0

    def energy_at(self, t):
        """kinetic-energy fraction left (relative to the Sun impact) - steps at each impact"""
        e2 = CONFIG["RESTITUTION"] ** 2
        n = sum(1 for im in self.impacts if t >= im["t"])
        return e2 ** n

    def planet_blend(self, t, fade=0.35):
        """(previous planet, current planet, w) for colour crossfades after each impact"""
        prev = CONFIG["SEQUENCE"][0]
        for im in self.impacts:
            if t < im["t"]:
                return prev, prev, 1.0
            if t < im["t"] + fade:
                return prev, im["planet"], smooth01((t - im["t"]) / fade)
            prev = im["planet"]
        return prev, prev, 1.0


def smooth01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def smoothstep(x, a, b):
    return smooth01((x - a) / (b - a))


def lerp(a, b, w):
    return a + (b - a) * w


def lerp3(a, b, w):
    return tuple(lerp(a[i], b[i], w) for i in range(3))


# =============================================================================
# small Blender helpers (no bpy.ops -> works headless, in bpy module, any context)
# =============================================================================

SCENE = None


def link(obj, parent=None):
    SCENE.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def mesh_obj(name, bm, mat=None, parent=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if mat:
        me.materials.append(mat)
    return link(ob, parent)


def bm_box(sx, sy, sz, origin_bottom=False, origin_left=False):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
        if origin_bottom:
            v.co.z += sz / 2
        if origin_left:
            v.co.x += sx / 2
    return bm


def bm_rect(w, h, origin_left=False):
    """flat rectangle in the XY plane (faces +Z), for camera-space overlays"""
    bm = bmesh.new()
    x0, x1 = (0.0, w) if origin_left else (-w / 2, w / 2)
    vs = [bm.verts.new((x0, -h / 2, 0)), bm.verts.new((x1, -h / 2, 0)),
          bm.verts.new((x1, h / 2, 0)), bm.verts.new((x0, h / 2, 0))]
    bm.faces.new(vs)
    return bm


def bm_ring(r_in, r_out, seg=96):
    bm = bmesh.new()
    inner, outer = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        inner.append(bm.verts.new((r_in * math.cos(a), r_in * math.sin(a), 0)))
        outer.append(bm.verts.new((r_out * math.cos(a), r_out * math.sin(a), 0)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((inner[i], outer[i], outer[j], inner[j]))
    return bm


def node_tree_of(idblock):
    if getattr(idblock, "node_tree", None) is None:
        try:
            idblock.use_nodes = True
        except Exception:
            pass
    return idblock.node_tree


def sock(node, *names):
    for n in names:
        for s in node.inputs:
            if s.identifier == n or s.name == n:
                return s
    raise KeyError(names)


def mix_rgb_node(nt, blend="MIX"):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    return m, sock(m, "Factor_Float", "Factor"), sock(m, "A_Color"), sock(m, "B_Color"), None


def mix_out(m):
    return [o for o in m.outputs if o.identifier == "Result_Color"][0]


def emit_mat(name, color, strength=1.0, alpha=1.0):
    """unlit material (for overlays / glowing bits). alpha<1 -> mixed with transparency"""
    mat = bpy.data.materials.new(name)
    nt = node_tree_of(mat)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    mat.diffuse_color = (*color, alpha)
    for attr, val in (("shadow_method", "NONE"),):
        if hasattr(mat, attr):
            try:
                setattr(mat, attr, val)
            except Exception:
                pass
    return mat


def principled_mat(name, color, rough=0.5, metallic=0.0, emit=0.0):
    mat = bpy.data.materials.new(name)
    nt = node_tree_of(mat)
    bsdf = nt.nodes.get("Principled BSDF") or nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    sock(bsdf, "Emission Color").default_value = (*color, 1)
    sock(bsdf, "Emission Strength").default_value = emit
    mat.diffuse_color = (*color, 1)
    return mat


def fkey(t):
    """video time (s) -> Blender frame (float)"""
    return 1.0 + t * CONFIG["FPS"]


def key(target, path, frame, index=-1):
    target.keyframe_insert(data_path=path, frame=frame, index=index)


def key_visibility(objs, intervals, total_frames):
    """objs visible only inside [(f_on, f_off), ...] (frames, float ok)"""
    for ob in objs:
        state_frames = [(-10.0, True)]
        for a, b in intervals:
            state_frames.append((a, False))
            state_frames.append((b, True))
        for f, hidden in state_frames:
            ob.hide_render = hidden
            ob.hide_viewport = hidden
            key(ob, "hide_render", f)
            key(ob, "hide_viewport", f)


FONT = None


def load_font():
    cands = [CONFIG["FONT_PATH"],
             "C:/Windows/Fonts/arialbd.ttf",
             "C:/Windows/Fonts/segoeuib.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/Library/Fonts/Arial Bold.ttf",
             "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
             "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
    for p in cands:
        if p and os.path.exists(p):
            try:
                return bpy.data.fonts.load(p, check_existing=True)
            except Exception:
                pass
    return None   # Blender built-in font


def text_obj(name, body, size, mat, align_x="CENTER", align_y="CENTER", parent=None):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align_x
    cu.align_y = align_y
    cu.space_line = 1.0
    if FONT:
        cu.font = FONT
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat)
    return link(ob, parent)


# =============================================================================
# scene construction
# =============================================================================


def reset_scene():
    global SCENE
    scene = bpy.context.scene
    for ob in list(scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.worlds, bpy.data.actions):
        for blk in list(coll):
            if blk.users == 0:
                coll.remove(blk)
    scene.name = "ImpossibleBounce"
    if scene.animation_data:
        scene.animation_data_clear()
    SCENE = scene
    return scene


def set_engine(scene, engine):
    ids = {"EEVEE": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"),      # 4.2-4.x : 5.x
           "CYCLES": ("CYCLES",),
           "WORKBENCH": ("BLENDER_WORKBENCH",)}[engine]
    for ident in ids:
        try:
            scene.render.engine = ident
            return ident
        except TypeError:
            continue
    raise RuntimeError("render engine %s not available" % engine)


def setup_render(scene, tl, opts):
    cfg = CONFIG
    r = scene.render
    r.resolution_x, r.resolution_y = cfg["RES_X"], cfg["RES_Y"]
    r.resolution_percentage = opts["scale"] or (cfg["PREVIEW_SCALE"] if cfg["PREVIEW"] else 100)
    r.fps = cfg["FPS"]
    r.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = int(math.floor(tl.total * cfg["FPS"])) + 1
    scene.frame_step = cfg["PREVIEW_STEP"] if cfg["PREVIEW"] else 1
    r.use_lock_interface = True          # live HUD text is updated by a frame handler
    ident = set_engine(scene, cfg["ENGINE"])
    prev = cfg["PREVIEW"]
    if ident.startswith("BLENDER_EEVEE"):
        ee = scene.eevee
        n = opts["samples"] or (cfg["EEVEE_SAMPLES_PREVIEW"] if prev else cfg["EEVEE_SAMPLES"])
        for attr, val in (("taa_render_samples", n), ("taa_samples", 8),
                          ("use_shadows", True), ("use_raytracing", False)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass
    elif ident == "CYCLES":
        scene.cycles.samples = opts["samples"] or (cfg["CYCLES_SAMPLES_PREVIEW"] if prev else cfg["CYCLES_SAMPLES"])
        scene.cycles.max_bounces = 4
        try:
            scene.cycles.use_denoising = True
        except Exception:
            pass
    try:
        scene.view_settings.view_transform = "Standard"   # true-colour text & planet colours
        scene.view_settings.look = "None"
    except Exception:
        pass
    scene.view_settings.exposure = 0.0
    # output
    out = opts["out"] or cfg["OUTPUT_DIR"] or default_output_dir()
    ims = r.image_settings
    if cfg["OUTPUT_FORMAT"] == "MP4":
        try:
            if hasattr(ims, "media_type"):        # Blender 5.x
                ims.media_type = "VIDEO"
            ims.file_format = "FFMPEG"
            r.ffmpeg.format = "MPEG4"
            r.ffmpeg.codec = "H264"
            r.ffmpeg.constant_rate_factor = "HIGH"
            r.filepath = os.path.join(out, "impossible_bounce_")
        except Exception as ex:
            print("[impossible-bounce] MP4 output unavailable (%s) - writing PNG frames" % ex)
            cfg["OUTPUT_FORMAT"] = "PNG"
    if cfg["OUTPUT_FORMAT"] == "PNG":
        if hasattr(ims, "media_type"):
            try:
                ims.media_type = "IMAGE"
            except Exception:
                pass
        ims.file_format = "PNG"
        ims.color_mode = "RGB"
        r.filepath = os.path.join(out, "frame_")
    return ident


def default_output_dir():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(here):
            return os.path.join(here, "renders", "03")
    except NameError:
        pass
    if bpy.data.filepath:
        return "//renders/03/"
    return os.path.join(os.getcwd(), "renders", "03")


def build_world(scene):
    w = bpy.data.worlds.new("IB_World")
    scene.world = w
    nt = node_tree_of(w)
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    # sky colour <-> space colour by altitude
    sky, sky_f, sky_a, sky_b, _ = mix_rgb_node(nt)
    sky.name = "SkyMix"
    sky_a.default_value = (*PLANETS["Sun"]["sky"], 1)
    sky_b.default_value = (0.002, 0.003, 0.010, 1)
    sky_f.default_value = 0.0
    # stars: voronoi cells on the view direction, keep the brightest ~20 %
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.voronoi_dimensions = "3D"
    vor.inputs["Scale"].default_value = 70.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.09
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], mr.inputs["Value"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs[0])
    gt = nt.nodes.new("ShaderNodeMath")
    gt.operation = "GREATER_THAN"
    gt.inputs[1].default_value = 0.78
    nt.links.new(sep.outputs[0], gt.inputs[0])
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(mr.outputs[0], m1.inputs[0])
    nt.links.new(gt.outputs[0], m1.inputs[1])
    starf = nt.nodes.new("ShaderNodeMath")
    starf.operation = "MULTIPLY"
    starf.name = "StarFac"
    starf.inputs[1].default_value = 0.0
    nt.links.new(m1.outputs[0], starf.inputs[0])
    fin, fin_f, fin_a, fin_b, _ = mix_rgb_node(nt)
    fin_b.default_value = (1.4, 1.4, 1.5, 1)
    nt.links.new(mix_out(sky), fin_a)
    nt.links.new(starf.outputs[0], fin_f)
    nt.links.new(mix_out(fin), bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return dict(sky_col=sky_a, alt=sky_f, stars=starf.inputs[1])


def build_ground(scene):
    mat = bpy.data.materials.new("IB_Ground")
    nt = node_tree_of(mat)
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.35
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1.1, 1.1, 1.1, 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    m, f, a, b, _ = mix_rgb_node(nt, "MULTIPLY")
    f.default_value = 1.0
    a.default_value = (*PLANETS["Sun"]["ground"], 1)
    nt.links.new(ramp.outputs["Color"], b)
    nt.links.new(mix_out(m), bsdf.inputs["Base Color"])
    nt.links.new(mix_out(m), sock(bsdf, "Emission Color"))
    em = sock(bsdf, "Emission Strength")
    bm = bm_rect(6000, 6000)
    ob = mesh_obj("IB_Ground", bm, mat)
    return dict(col=a, emit=em)


def build_pad():
    mat = bpy.data.materials.new("IB_Pad")
    nt = node_tree_of(mat)
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.35
    col = bsdf.inputs["Base Color"]
    ecol = sock(bsdf, "Emission Color")
    est = sock(bsdf, "Emission Strength")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=0.75, radius2=0.72, depth=PAD_TOP)
    for v in bm.verts:
        v.co.z += PAD_TOP / 2
    pad = mesh_obj("IB_Pad", bm, mat, smooth=False)
    pad.location = (BALL_X, 0, 0)
    # white rim ring so the pad reads on every ground colour
    rim = mesh_obj("IB_PadRim", bm_ring(0.72, 0.80), emit_mat("IB_PadRimMat", (0.95, 0.95, 0.95), 1.0))
    rim.location = (BALL_X, 0, 0.004)
    return dict(col=col, ecol=ecol, est=est)


def build_ball():
    R = CONFIG["BALL_RADIUS"]
    root = bpy.data.objects.new("IB_BallRoot", None)      # analytic contact point (bottom of ball)
    root.empty_display_size = 0.3
    link(root)
    root["phys_t"] = 0.0
    root["seg"] = 0.0
    mat = bpy.data.materials.new("IB_Ball")
    nt = node_tree_of(mat)
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.3
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 2.2
    ck.inputs["Color1"].default_value = (0.95, 0.08, 0.06, 1)
    ck.inputs["Color2"].default_value = (0.97, 0.96, 0.93, 1)
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], bsdf.inputs["Base Color"])
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=R)
    ball = mesh_obj("IB_Ball", bm, mat, parent=root, smooth=True)
    return root, ball


def build_ruler(font_mat_white):
    top = 100.0
    mat = emit_mat("IB_RulerMat", (0.92, 0.92, 0.92), 1.0)
    dark = emit_mat("IB_RulerBack", (0.03, 0.03, 0.04), 1.0)
    back = mesh_obj("IB_RulerBack", bm_box(0.11, 0.02, top, origin_bottom=True), dark)
    back.location = (RULER_X, 0.03, PAD_TOP)
    for m in range(0, int(top) + 1):
        w = 0.34 if m % 5 == 0 else 0.17
        hgt = 0.035 if m % 5 == 0 else 0.018
        t = mesh_obj("IB_Tick%03d" % m, bm_box(w, 0.02, hgt), mat)
        t.location = (RULER_X + 0.055 - w / 2 + 0.02, -0.01, PAD_TOP + m)
        if m % 5 == 0 and m > 0:
            tx = text_obj("IB_RulerNum%03d" % m, "%d m" % m, 0.30, font_mat_white,
                          align_x="RIGHT", align_y="CENTER")
            tx.location = (RULER_X - 0.32, -0.01, PAD_TOP + m)
            tx.rotation_euler = (math.pi / 2, 0, 0)
    fill_mat = emit_mat("IB_RulerFill", (1.0, 0.82, 0.15), 1.0)
    fill = mesh_obj("IB_RulerFill", bm_box(0.07, 0.03, 1.0, origin_bottom=True), fill_mat)
    fill.location = (RULER_X, -0.005, PAD_TOP)
    return fill


def build_clouds():
    rnd = random.Random(CONFIG["SEED"])
    mat = principled_mat("IB_Cloud", (0.95, 0.96, 1.0), rough=1.0, emit=0.35)
    n = 0
    while n < 64:
        # kept close (y < 60) so they never show from the ground: they appear as the ball climbs
        x = rnd.uniform(-45, 45)
        y = rnd.uniform(4, 60)
        if abs(x - BALL_X) < 4 and y < 12:
            continue          # keep the ball's column clear
        z = rnd.uniform(62, 72)
        bm = bmesh.new()
        for k in range(rnd.randint(4, 7)):
            tmp = bmesh.new()
            bmesh.ops.create_icosphere(tmp, subdivisions=2, radius=1.0)
            sx, sy, sz = rnd.uniform(3, 6), rnd.uniform(2.5, 4.5), rnd.uniform(1.2, 2.2)
            ox, oy, oz = rnd.uniform(-4, 4), rnd.uniform(-2, 2), rnd.uniform(-0.5, 1.2)
            for v in tmp.verts:
                v.co.x = v.co.x * sx + ox
                v.co.y = v.co.y * sy + oy
                v.co.z = v.co.z * sz + oz
            me = bpy.data.meshes.new("tmp")
            tmp.to_mesh(me)
            tmp.free()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        ob = mesh_obj("IB_Cloud%02d" % n, bm, mat, smooth=True)
        ob.location = (x, y, z)
        n += 1


def build_lights():
    ld = bpy.data.lights.new("IB_Sun", "SUN")
    ld.energy = 3.2
    ld.angle = math.radians(3)
    ob = link(bpy.data.objects.new("IB_Sun", ld))
    ob.rotation_euler = (math.radians(48), math.radians(-18), math.radians(-25))


# ------------------------------------------------------------------ overlays


def hud_group(name, parent, x_px, y_px):
    g = bpy.data.objects.new(name, None)
    g.empty_display_size = 0.02
    link(g, parent)
    g.location = (x_px * PX, y_px * PX, 0)
    return g


def hud_text(name, body, parent, x_px, y_px, size_px, mat, align="CENTER"):
    t = text_obj(name, body, size_px * PX, mat, align_x=align, parent=parent)
    t.location = (x_px * PX, y_px * PX, 0)
    return t


def hud_plate(name, parent, x_px, y_px, w_px, h_px, mat):
    p = mesh_obj(name, bm_rect(w_px * PX, h_px * PX), mat, parent=parent)
    p.location = (x_px * PX, y_px * PX, -0.002)
    return p


def fast_forward_icon(name, parent, x_px, y_px, size_px, mat):
    bm = bmesh.new()
    s = size_px * PX
    for off in (0.0, 0.55):
        a = bm.verts.new(((off - 0.5) * s, -0.45 * s, 0))
        b = bm.verts.new(((off - 0.5) * s, 0.45 * s, 0))
        c = bm.verts.new(((off + 0.05) * s, 0.0, 0))
        bm.faces.new((a, c, b))
    ob = mesh_obj(name, bm, mat, parent=parent)
    ob.location = (x_px * PX, y_px * PX, 0)
    return ob


def check_icon(name, parent, x_px, y_px, size_px, mat):
    bm = bmesh.new()
    s = size_px * PX
    w = 0.16 * s
    pts = [(-0.45, 0.0), (-0.12, -0.35), (0.48, 0.42)]
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * w / 2, dx / L * w / 2
        ext = w / 2 / L
        x0e, y0e = x0 * s - dx / L * w / 2, y0 * s - dy / L * w / 2
        x1e, y1e = x1 * s + dx / L * w / 2 * 0, y1 * s + dy / L * w / 2 * 0
        vs = [bm.verts.new((x0e + nx, y0e + ny, 0)), bm.verts.new((x0e - nx, y0e - ny, 0)),
              bm.verts.new((x1e - nx, y1e - ny, 0)), bm.verts.new((x1e + nx, y1e + ny, 0))]
        bm.faces.new(vs)
    ob = mesh_obj(name, bm, mat, parent=parent)
    ob.location = (x_px * PX, y_px * PX, 0.0005)
    return ob


def pop(group, frame, frm=1.4):
    group.scale = (frm, frm, frm)
    key(group, "scale", frame - 0.01)
    group.scale = (1, 1, 1)
    key(group, "scale", frame + 5)
    # make sure it is at rest before
    key(group, "scale", frame - 0.02)


def fmt(v, nd=1):
    return ("%." + str(nd) + "f") % v


def build_overlays(cam, tl, nframes):
    """everything 2D: parented to the camera 1 unit in front of the lens"""
    root = bpy.data.objects.new("IB_HUD", None)
    link(root, cam)
    root.location = (0, 0, -1.0)
    white = emit_mat("IB_TxtWhite", (1, 1, 1), 1.0)
    yellow = emit_mat("IB_TxtYellow", (1.0, 0.84, 0.15), 1.0)
    green = emit_mat("IB_TxtGreen", (0.35, 0.95, 0.45), 1.0)
    grey = emit_mat("IB_TxtGrey", (0.72, 0.74, 0.78), 1.0)
    plate = emit_mat("IB_Plate", (0.015, 0.016, 0.022), 1.0, alpha=0.9)
    track = emit_mat("IB_BarTrack", (0.16, 0.16, 0.19), 1.0)
    fps = CONFIG["FPS"]
    F = lambda t: fkey(t)
    end_f = nframes + 5
    imp_f = [F(im["t"]) for im in tl.impacts]

    # -------- planet label (top third), one per planet, slams in at its impact
    seq = CONFIG["SEQUENCE"]
    # planet changes only (the final Pluto->Pluto landing is not a new planet)
    changes = [im for im in tl.impacts if tl.segs[im["seg"]]["kind"] == "bounce"]
    starts = [0.0] + [F(im["t"]) for im in changes]
    planet_on = {}
    for i, name in enumerate(seq):
        f_on = 1.0 if i == 0 else starts[i]
        f_off = starts[i + 1] if i + 1 < len(starts) else end_f
        planet_on[name] = (f_on, f_off)
        p = PLANETS[name]
        g = hud_group("IB_LabelGrp_" + name, root, 0, 715)
        acc = emit_mat("IB_TxtAccent_" + name, p["accent"], 1.0)
        t1 = hud_text("IB_Label_" + name, name.upper(), g, 0, 50, 150, acc)
        t2 = hud_text("IB_LabelG_" + name, "g = %s m/s²" % ("%g" % p["g"]), g, 0, -75, 66, white)
        pl = hud_plate("IB_LabelPlate_" + name, g, 0, 0, 760, 290, plate)
        key_visibility([t1, t2, pl], [(f_on, f_off)], nframes)
        if i > 0:
            pop(g, f_on, 1.5)

    # -------- hook caption (first seconds)
    hook_off = imp_f[0]                     # disappears at the Sun impact
    hg = hud_group("IB_HookGrp", root, 0, 360)
    h1 = hud_text("IB_Hook1", "This ball loses 1/3 of its\nenergy every bounce.", hg, 0, 45, 62, white)
    h2 = hud_text("IB_Hook2", "So why does it go HIGHER?", hg, 0, -78, 70, yellow)
    hp = hud_plate("IB_HookPlate", hg, 0, 0, 1000, 290, plate)
    key_visibility([h1, h2, hp], [(-10, hook_off)], nframes)

    # -------- per-bounce stats line
    end_on = F(tl.apexes[seq[-1]][0] + 0.4)
    for k, im in enumerate(changes):
        s = tl.segs[im["seg"]]
        h = s["v0"] ** 2 / (2 * s["g"])
        air = 2 * s["v0"] / s["g"]
        f_on = F(im["t"])
        f_off = F(changes[k + 1]["t"]) if k + 1 < len(changes) else end_on
        body = "leaves pad at %s m/s  ·  %d%% energy\npeak %s m  ·  %s s in the air" % (
            fmt(s["v0"]), round(100 * tl.energy_at(im["t"] + 1e-6)), fmt(h), fmt(air))
        g = hud_group("IB_StatGrp%d" % k, root, 0, 400)
        t = hud_text("IB_Stat%d" % k, body, g, 0, 0, 44, white)
        pl = hud_plate("IB_StatPlate%d" % k, g, 0, 0, 900, 140, plate)
        key_visibility([t, pl], [(f_on, f_off)], nframes)
    # -------- fast-forward tags
    for name in seq:
        sp = CONFIG["SPEED"][name]
        if sp <= 1.0:
            continue
        f_on, f_off = planet_on[name]
        f_off = min(f_off, end_on) if name == seq[-1] else f_off
        g = hud_group("IB_FFGrp_" + name, root, 300, 522)
        ic = fast_forward_icon("IB_FFIcon_" + name, g, -112, 0, 52, yellow)
        t = hud_text("IB_FF_" + name, "%s×" % ("%g" % sp), g, -70, 0, 50, yellow, align="LEFT")
        pl = hud_plate("IB_FFPlate_" + name, g, -30, 0, 230, 78, plate)
        key_visibility([ic, t, pl], [(f_on, f_off)], nframes)

    # -------- bottom HUD: energy bar drains, peak-height bar grows, live readouts
    hud = hud_group("IB_BottomHUD", root, 0, -735)
    hud_plate("IB_HUDPlate", hud, 0, 0, 1010, 330, plate)
    bar_x0, bar_w, bar_h = -230, 520, 36
    hud_text("IB_EnergyLbl", "ENERGY", hud, -470, 95, 40, grey, align="LEFT")
    hud_plate("IB_EnergyTrack", hud, bar_x0 + bar_w / 2, 95, bar_w, bar_h, track).location.z = -0.001
    efill = mesh_obj("IB_EnergyFill", bm_rect(bar_w * PX, bar_h * PX, origin_left=True),
                     emit_mat("IB_EnergyMat", (0.30, 0.90, 0.40), 1.0), parent=hud)
    efill.location = (bar_x0 * PX, 95 * PX, 0)
    hud_text("IB_EnergyVal", "100%", hud, 470, 95, 44, white, align="RIGHT")

    hud_text("IB_PeakLbl", "MAX HEIGHT", hud, -470, 15, 40, grey, align="LEFT")
    hud_plate("IB_PeakTrack", hud, bar_x0 + bar_w / 2, 15, bar_w, bar_h, track).location.z = -0.001
    pfill = mesh_obj("IB_PeakFill", bm_rect(bar_w * PX, bar_h * PX, origin_left=True),
                     emit_mat("IB_PeakMat", (1.0, 0.82, 0.15), 1.0), parent=hud)
    pfill.location = (bar_x0 * PX, 15 * PX, 0)
    hud_text("IB_PeakVal", "0 m", hud, 470, 15, 44, white, align="RIGHT")

    hud_text("IB_Live", "height 2.0 m   ·   real time 0.0 s", hud, 0, -75, 40, white)

    # energy bar keyed: steps at impacts with a quick 0.25 s drain
    E = 1.0
    efill.scale = (1, 1, 1)
    key(efill, "scale", 1)
    for im in tl.impacts:
        f = F(im["t"])
        efill.scale = (E, 1, 1)
        key(efill, "scale", f)
        E *= CONFIG["RESTITUTION"] ** 2
        efill.scale = (E, 1, 1)
        key(efill, "scale", f + 0.25 * fps)

    # -------- end card
    eg = hud_group("IB_EndGrp", root, 0, 360)
    e1 = hud_text("IB_End1", "Height = speed² ÷ 2g", eg, 0, 110, 76, yellow)
    e2 = hud_text("IB_End2", "Less gravity → same speed\ngoes way higher.", eg, 0, -5, 52, white)
    e3 = hud_text("IB_End3", "Energy still went DOWN", eg, -40, -120, 56, green)
    e4 = check_icon("IB_EndCheck", eg, 330, -118, 70, green)
    ep = hud_plate("IB_EndPlate", eg, 0, 0, 1000, 340, plate)
    key_visibility([e1, e2, e3, e4, ep], [(end_on, end_f)], nframes)
    pop(eg, end_on, 1.25)
    return efill, pfill


# ------------------------------------------------------------------ world-space markers


def build_peak_markers(tl, nframes):
    for name, (ta, h) in tl.apexes.items():
        acc = PLANETS[name]["accent"]
        m = emit_mat("IB_PeakLine_" + name, acc, 1.0)
        ln = mesh_obj("IB_PeakLine_" + name, bm_box(BALL_X - RULER_X + 0.35, 0.02, 0.035), m)
        ln.location = ((RULER_X + BALL_X + 0.35) / 2, -0.02, PAD_TOP + h)
        tx = text_obj("IB_PeakTxt_" + name, "%s\n%s m" % (name.upper(), fmt(h)), 0.17, m,
                      align_x="LEFT", align_y="CENTER")
        tx.location = (BALL_X + 0.42, -0.02, PAD_TOP + h)
        tx.rotation_euler = (math.pi / 2, 0, 0)
        key_visibility([ln, tx], [(fkey(ta), nframes + 5)], nframes)


def build_shockwaves(tl, nframes):
    for k, im in enumerate(tl.impacts):
        m = emit_mat("IB_Shock%d" % k, PLANETS[im["planet"]]["accent"], 2.0)
        ob = mesh_obj("IB_Shock%d" % k, bm_ring(0.85, 1.0), m)
        ob.location = (BALL_X, 0, PAD_TOP + 0.01)
        f = fkey(im["t"])
        ob.scale = (0.4, 0.4, 1)
        key(ob, "scale", f)
        ob.scale = (4.0, 4.0, 1)
        key(ob, "scale", f + 0.5 * CONFIG["FPS"])
        key_visibility([ob], [(f, f + 0.5 * CONFIG["FPS"])], nframes)


# =============================================================================
# animation bake (one key per frame for everything that moves)
# =============================================================================


def camera_y_norm(zb, zc, pitch):
    return math.tan(math.atan((zb - zc) / CAM_DIST) + pitch) / T_HALF


def camera_z_for(zb, ynorm, pitch):
    return zb - CAM_DIST * math.tan(math.atan(ynorm * T_HALF) - pitch)


def bake_animation(tl, nframes, root, ball, cam, world_socks, ground_socks, pad_socks, rfill, pfill):
    cfg = CONFIG
    fps = cfg["FPS"]
    R = cfg["BALL_RADIUS"]
    rnd = random.Random(cfg["SEED"])
    imp_t = [im["t"] for im in tl.impacts]
    zc_s = None
    spin = 0.0
    shake_t0 = imp_t[0]
    for f in range(1, nframes + 1):
        t = (f - 1) / fps
        st = tl.state(t)
        h = st["z"]
        seg = st["seg"]
        # ---- ball root: exact analytic contact point
        root.location = (BALL_X, 0, PAD_TOP + h)
        root["phys_t"] = st["phys"]
        root["seg"] = float(seg["idx"])
        key(root, "location", f)
        key(root, '["phys_t"]', f)
        key(root, '["seg"]', f)
        # ---- squash & stretch (visual only, on the child mesh)
        near = min(imp_t, key=lambda x: abs(x - t))
        sz, off = 1.0, 0.0
        if abs(t - near) <= 0.5 / fps + 1e-9 and h < 3.0:
            sz = 0.62                       # impact frame: ball drawn flattened on the pad
            off = -h
        else:
            screen_v = abs(st["vel"]) * st["speed"]
            sz = 1.0 + min(0.32, 0.011 * screen_v)
        sxy = 1.0 / math.sqrt(sz)
        ball.location = (0, 0, R * sz + off)
        ball.scale = (sxy, sxy, sz)
        spin += 3.5 / fps
        ball.rotation_euler = (0.3, spin, 0.2)
        key(ball, "location", f)
        key(ball, "scale", f)
        key(ball, "rotation_euler", f)
        # ---- camera follow
        pitch = math.radians(lerp(4.0, 11.0, smoothstep(h, 45, 90)))
        zb = PAD_TOP + h + R
        target = max(2.15, camera_z_for(zb, BALL_Y_DES, pitch))
        if zc_s is None:
            zc_s = target
        a = 1 - math.exp(-(1.0 / fps) / 0.10)
        zc_s += (target - zc_s) * a
        lo = camera_z_for(zb, BALL_Y_MAX, pitch)     # camera at least this low (ball not too high)
        hi = camera_z_for(zb, BALL_Y_MIN, pitch)     # camera at most this high
        zc_s = min(max(zc_s, lo), hi)
        zc_s = max(zc_s, 1.0)
        dist = CAM_DIST
        if t < cfg["HOOK_SECONDS"]:
            dist = lerp(7.6, CAM_DIST, smooth01(t / cfg["HOOK_SECONDS"]))
        sx = sz_ = 0.0
        if 0 <= t - shake_t0 < 0.45:              # Sun impact camera shake
            amp = 0.07 * (1 - (t - shake_t0) / 0.45)
            sx, sz_ = rnd.uniform(-amp, amp), rnd.uniform(-amp, amp)
        cam.location = (CAM_X + sx, -dist, zc_s + sz_)
        cam.rotation_euler = (math.pi / 2 - pitch, 0, 0)
        key(cam, "location", f)
        key(cam, "rotation_euler", f)
        # ---- world: planet sky crossfade, darker + starrier with altitude
        pa, pb, w = tl.planet_blend(t)
        sky = lerp3(PLANETS[pa]["sky"], PLANETS[pb]["sky"], w)
        world_socks["sky_col"].default_value = (*sky, 1)
        world_socks["alt"].default_value = smoothstep(h, 6, 85) * 0.97
        base_st = lerp(PLANETS[pa]["stars"], PLANETS[pb]["stars"], w)
        world_socks["stars"].default_value = max(base_st, smoothstep(h, 25, 80))
        key(world_socks["sky_col"], "default_value", f)
        key(world_socks["alt"], "default_value", f)
        key(world_socks["stars"], "default_value", f)
        # ---- growing ruler fill + peak bar
        mh = tl.max_height_until(t)
        rfill.scale = (1, 1, max(0.001, mh))
        key(rfill, "scale", f)
        pfill.scale = (max(0.001, min(1.0, mh / 100.0)), 1, 1)
        key(pfill, "scale", f)

    # ---- ground + pad colours: keyed only around each impact
    def set_ground(p, f):
        ground_socks["col"].default_value = (*PLANETS[p]["ground"], 1)
        ground_socks["emit"].default_value = PLANETS[p]["glow"]
        key(ground_socks["col"], "default_value", f)
        key(ground_socks["emit"], "default_value", f)

    def set_pad(p, f, strength):
        c = (*PLANETS[p]["accent"], 1)
        pad_socks["col"].default_value = c
        pad_socks["ecol"].default_value = c
        pad_socks["est"].default_value = strength
        key(pad_socks["col"], "default_value", f)
        key(pad_socks["ecol"], "default_value", f)
        key(pad_socks["est"], "default_value", f)

    prev = cfg["SEQUENCE"][0]
    set_ground(prev, 1)
    set_pad(prev, 1, 0.6)
    for im in tl.impacts:
        f = fkey(im["t"])
        set_ground(prev, f)
        set_ground(im["planet"], f + 0.35 * fps)
        set_pad(prev, f - 0.02, 0.6)
        set_pad(im["planet"], f, 6.0)
        set_pad(im["planet"], f + 0.6 * fps, 0.6)
        prev = im["planet"]


# =============================================================================
# live HUD text (frame handler)
# =============================================================================

_TL = None


@persistent
def ib_hud_update(scene, depsgraph=None):
    tl = _TL
    if tl is None or "IB_Live" not in bpy.data.objects:
        return
    t = (scene.frame_current + scene.frame_subframe - 1) / scene.render.fps
    st = tl.state(t)
    try:
        bpy.data.objects["IB_Live"].data.body = "height %s m   ·   real time %s s" % (fmt(st["z"]), fmt(st["phys"]))
        bpy.data.objects["IB_EnergyVal"].data.body = "%d%%" % round(100 * tl.energy_at(t))
        bpy.data.objects["IB_PeakVal"].data.body = "%s m" % fmt(tl.max_height_until(t))
    except Exception:
        pass


def register_handler():
    for lst in (bpy.app.handlers.frame_change_pre,):
        for h in list(lst):
            if getattr(h, "__name__", "") == "ib_hud_update":
                lst.remove(h)
        lst.append(ib_hud_update)


# =============================================================================
# verification: measure the outcome from the evaluated scene
# =============================================================================


def fit_parabola(ts, zs):
    """least-squares z = a + b t + c t^2 (pure python, 3x3 normal equations)"""
    n = len(ts)
    S = [sum(t ** k for t in ts) for k in range(5)]
    Y = [sum(z * t ** k for t, z in zip(ts, zs)) for k in range(3)]
    A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]]
    # Cramer's rule
    def det(M):
        return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
                - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    D = det(A)
    sol = []
    for c in range(3):
        M = [row[:] for row in A]
        for r in range(3):
            M[r][c] = Y[r]
        sol.append(det(M) / D)
    return sol  # a, b, c


def verify(scene, tl, nframes):
    cfg = CONFIG
    root = bpy.data.objects["IB_BallRoot"]
    samples = {}
    for f in range(1, nframes + 1):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = root.evaluated_get(dg)
        z = ev.matrix_world.translation.z - PAD_TOP
        seg = int(round(root["seg"]))
        samples.setdefault(seg, []).append((root["phys_t"], z, f))
    scene.frame_set(1)

    rows = []
    ok = True
    sun_v = None
    print("\n=== THE IMPOSSIBLE BOUNCE - measured from the evaluated scene (%d frames @ %d fps, %.2f s) ==="
          % (nframes, cfg["FPS"], (nframes - 1) / cfg["FPS"]))
    hdr = "%-8s %8s %8s | %9s %6s | %8s %6s | %7s %5s | %7s %5s | %s"
    print(hdr % ("planet", "g fit", "g real", "v m/s", "brief", "peak m", "brief", "air s", "brief",
                 "energy", "brief", "result"))
    print("-" * 108)
    for s in tl.segs:
        if s["kind"] not in ("fall", "bounce"):
            continue
        pts = [(p, z) for (p, z, f) in samples.get(s["idx"], []) if z > 1e-6]
        if len(pts) < 3:
            raise AssertionError("not enough samples in segment %s" % s["planet"])
        ts = [p for p, _ in pts]
        zs = [z for _, z in pts]
        a, b, c = fit_parabola(ts, zs)
        g_fit = -2 * c
        disc = math.sqrt(max(0.0, b * b - 4 * c * a))
        r1, r2 = sorted(((-b + disc) / (2 * c), (-b - disc) / (2 * c)))
        peak = a - b * b / (4 * c)
        g_ok = abs(g_fit - s["g"]) / s["g"] < 0.005
        if s["kind"] == "fall":
            sun_v = abs(b + 2 * c * r2)
            exp = BRIEF["sun_impact_speed"]
            good = g_ok and abs(sun_v - exp) <= 0.1 and abs(peak - cfg["DROP_HEIGHT"]) < 0.02
            print("%-8s %8.2f %8.2f | %9.2f %6.1f | %8.2f %6.1f | %7s %5s | %7s %5s | %s" % (
                s["planet"], g_fit, s["g"], sun_v, exp, peak, cfg["DROP_HEIGHT"], "-", "-", "100%", "-",
                "OK  (drop / impact speed)" if good else "FAIL"))
            ok &= good
            continue
        v_launch = b + 2 * c * r1
        air = r2 - r1
        energy = 100 * (v_launch / sun_v) ** 2
        ev, eh, ea, ee = BRIEF[s["planet"]]
        checks = [g_ok,
                  abs(v_launch - ev) <= 0.1,
                  abs(peak - eh) <= max(0.6, 0.01 * eh),
                  abs(air - ea) <= max(0.06, 0.005 * ea),
                  abs(energy - ee) <= 0.6]
        good = all(checks)
        ok &= good
        print("%-8s %8.2f %8.2f | %9.2f %6.1f | %8.2f %6.1f | %7.2f %5.1f | %6.1f%% %4.0f%% | %s" % (
            s["planet"], g_fit, s["g"], v_launch, ev, peak, eh, air, ea, energy, ee,
            "OK" if good else "FAIL " + str(checks)))
        rows.append((s["planet"], v_launch, peak, air, energy))
    # the paradox itself: energy strictly down, height strictly up
    for (p0, v0, h0, a0, e0), (p1, v1, h1, a1, e1) in zip(rows, rows[1:]):
        if not (e1 < e0 and h1 > h0):
            ok = False
            print("FAIL: %s -> %s energy/height trend" % (p0, p1))
    dur = (nframes - 1) / cfg["FPS"]
    dur_ok = 35.0 <= dur <= 45.0
    print("-" * 108)
    print("energy every bounce DOWN, peak height every bounce UP: %s" % ("OK" if ok else "FAIL"))
    print("video length %.2f s (brief 35-45 s): %s" % (dur, "OK" if dur_ok else "FAIL"))
    for name in cfg["SEQUENCE"]:
        if cfg["SPEED"][name] != 1.0:
            print("  %-7s shown at %gx (fast-forward tag on screen)" % (name, cfg["SPEED"][name]))
    ok &= dur_ok
    assert ok, "Verification FAILED - measured outcome does not match the brief"
    print("VERIFICATION PASSED\n")
    return rows


# =============================================================================
# main
# =============================================================================


def build(opts):
    global FONT, _TL
    cfg = CONFIG
    prefs = None
    old_interp = None
    try:
        prefs = bpy.context.preferences.edit
        old_interp = prefs.keyframe_new_interpolation_type
        prefs.keyframe_new_interpolation_type = "LINEAR"
    except Exception:
        prefs = None
    try:
        scene = reset_scene()
        tl = Timeline(cfg)
        _TL = tl
        nframes = int(math.floor(tl.total * cfg["FPS"])) + 1
        engine = setup_render(scene, tl, opts)
        FONT = load_font()

        cam_data = bpy.data.cameras.new("IB_Camera")
        cam_data.lens = LENS
        cam_data.sensor_fit = "VERTICAL"
        cam_data.sensor_height = SENSOR_H
        cam_data.clip_start = 0.05
        cam_data.clip_end = 8000
        cam = link(bpy.data.objects.new("IB_Camera", cam_data))
        scene.camera = cam

        world_socks = build_world(scene)
        ground_socks = build_ground(scene)
        pad_socks = build_pad()
        root, ball = build_ball()
        white_world = emit_mat("IB_RulerTxt", (0.95, 0.95, 0.95), 1.0)
        rfill = build_ruler(white_world)
        build_clouds()
        build_lights()
        build_peak_markers(tl, nframes)
        build_shockwaves(tl, nframes)
        efill, pfill = build_overlays(cam, tl, nframes)
        bake_animation(tl, nframes, root, ball, cam, world_socks, ground_socks, pad_socks, rfill, pfill)
        register_handler()
        scene.frame_set(1)
        print("[impossible-bounce] scene built: %d frames (%.1f s) @ %d fps, engine %s, font %s"
              % (nframes, tl.total, cfg["FPS"], engine, FONT.filepath if FONT else "built-in"))
        return scene, tl, nframes
    finally:
        if prefs is not None and old_interp is not None:
            prefs.keyframe_new_interpolation_type = old_interp


def render(scene, opts):
    out = scene.render.filepath
    os.makedirs(os.path.dirname(bpy.path.abspath(out)), exist_ok=True)
    if opts["stills"]:
        base = scene.render.filepath
        for f in opts["stills"]:
            scene.frame_set(f)
            scene.render.filepath = base + "%04d" % f
            bpy.ops.render.render(write_still=True)
            print("[impossible-bounce] wrote", bpy.path.abspath(scene.render.filepath) + ".png")
        scene.render.filepath = base
        return
    if opts["frames"]:
        scene.frame_start, scene.frame_end = opts["frames"]
    print("[impossible-bounce] rendering frames %d-%d step %d -> %s"
          % (scene.frame_start, scene.frame_end, scene.frame_step, out))
    bpy.ops.render.render(animation=True)


def main():
    opts = parse_args(CONFIG)
    scene, tl, nframes = build(opts)
    if CONFIG["VERIFY"]:
        verify(scene, tl, nframes)
    if CONFIG["RENDER"]:
        render(scene, opts)


main()
