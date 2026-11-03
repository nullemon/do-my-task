"""
SPLIT WORLD  --  "Half Moon, half Jupiter (watch the water)"
================================================================
One locked-off vertical shot of a kitchen table split by a glowing seam at
x = 0.  Left of the seam gravity is the Moon's (1.62 m/s^2), right of it
Jupiter's (24.79 m/s^2).

Beats (36 s @ 30 fps):
   0 -  5 s  hand pours water left->right; slow Moon arc, Jupiter slam + splash
   5 - 12 s  twin balls roll off a 1 m table: Moon 1.11 s vs Jupiter 0.28 s
  12 - 20 s  a deck of cards bursts across the seam: left flutters, right drops
  20 - 30 s  long pendulum swings across the seam (live half-swing timers)
  27 - 30 s  eggs tossed on the Moon side ...
  30 - 33 s  ... the seam slides left, Jupiter eats the frame, everything crashes
  33 - 36 s  "Which side would you live on?"

Physics: Blender's Bullet world has ONE gravity vector and force fields apply a
*force* (not an acceleration) that cannot be cleanly box-bounded, so every
moving thing here is integrated by a small deterministic Python integrator
(1200 Hz sub-steps, exact constant-acceleration update per sub-step, gravity
looked up from the body's x position and the seam position at that instant)
and baked to keyframes.  See README.md.

Run
  Blender UI : Scripting tab -> open -> Run Script   (builds the scene)
  Headless   : blender -b -P script.py -- --preview  (low-res mp4)
               blender -b -P script.py -- --render   (final mp4)
  Extra args : --frames 1,150,400  (render only these stills)
               --engine EEVEE|CYCLES|WORKBENCH  --samples N  --res-pct N
               --range 1,90 (animation sub-range)  --out /some/folder
"""

import bpy
import math
import os
import random
import sys
import time
from bpy.app.handlers import persistent
from mathutils import Vector, Euler, Matrix

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
CONFIG = {
    # planets
    "LEFT":  {"name": "MOON",    "g": 1.62},
    "RIGHT": {"name": "JUPITER", "g": 24.79},

    # video
    "FPS": 30,
    "DURATION": 36.0,                # seconds
    "RESOLUTION": (1080, 1920),      # vertical
    "ENGINE": "EEVEE",               # EEVEE | CYCLES | WORKBENCH
    "MODE": "PREVIEW",               # PREVIEW | RENDER  (CLI flags override)
    "PREVIEW": {"res_pct": 50, "samples": 16},
    "RENDER":  {"res_pct": 100, "samples": 64},
    "OUTPUT_DIR": "split_world_out",  # relative to the .blend / working dir
    "SEED": 7,

    # physics
    "SUBSTEPS": 40,                  # integrator sub-steps per frame (1200 Hz)
    "TABLE_H": 1.0,                  # table top height (m) -> the 1 m drop
    "TABLE_HALF_X": 1.2,
    "TABLE_HALF_Y": 0.55,
    "SEAM_SLIDE": (30.2, 32.0),      # seconds: seam moves from x=0 ...
    "SEAM_END_X": -3.0,              # ... to here (off the left of frame)
    "PEND_L": 2.5,                   # pendulum length (m)
    "PEND_PIVOT": (0.0, 0.32, 4.1),
    "PEND_THETA0_DEG": -35.0,        # released on the Moon side
    "PEND_RELEASE": 20.0,
    "CARD_DRAG": 1.0,                # quadratic drag k (1/m), same air both sides
    "N_CARDS": 26,
}

FPS = CONFIG["FPS"]
SUB = CONFIG["SUBSTEPS"]
DT = 1.0 / (FPS * SUB)
GL = CONFIG["LEFT"]["g"]
GR = CONFIG["RIGHT"]["g"]
N_FRAMES = int(round(CONFIG["DURATION"] * FPS))
TH = CONFIG["TABLE_H"]
TX = CONFIG["TABLE_HALF_X"]
TY = CONFIG["TABLE_HALF_Y"]


def t2f(t):
    """time (s) -> frame number (frame 1 is t = 0)."""
    return t * FPS + 1.0


def f2t(f):
    return (f - 1.0) / FPS


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(u):
    u = clamp(u)
    return u * u * (3.0 - 2.0 * u)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = {"action": None, "frames": None, "engine": None, "samples": None,
         "res_pct": None, "out": None, "range": None}
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--render":
            a["action"] = "RENDER"
        elif k == "--preview":
            a["action"] = "PREVIEW"
        elif k == "--frames" and i + 1 < len(argv):
            a["frames"] = [int(x) for x in argv[i + 1].split(",") if x.strip()]
            i += 1
        elif k == "--engine" and i + 1 < len(argv):
            a["engine"] = argv[i + 1].upper(); i += 1
        elif k == "--samples" and i + 1 < len(argv):
            a["samples"] = int(argv[i + 1]); i += 1
        elif k == "--res-pct" and i + 1 < len(argv):
            a["res_pct"] = int(argv[i + 1]); i += 1
        elif k == "--range" and i + 1 < len(argv):
            a["range"] = [int(x) for x in argv[i + 1].split(",")][:2]; i += 1
        elif k == "--out" and i + 1 < len(argv):
            a["out"] = argv[i + 1]; i += 1
        i += 1
    return a


# ----------------------------------------------------------------------------
# Gravity field: two zones split by a (moving) seam
# ----------------------------------------------------------------------------
def seam_x(t):
    t0, t1 = CONFIG["SEAM_SLIDE"]
    if t <= t0:
        return 0.0
    u = clamp((t - t0) / (t1 - t0))
    # ease-in (accelerating) then settle: Jupiter "eats" the frame
    return CONFIG["SEAM_END_X"] * smooth(u)


def g_at(x, t):
    return GL if x < seam_x(t) else GR


# ----------------------------------------------------------------------------
# Animation helpers (Blender 4.2 - 5.x safe)
# ----------------------------------------------------------------------------
def fcurves_for(idb):
    """Return the fcurve collection of an ID's action (legacy or layered)."""
    ad = idb.animation_data
    act = ad.action if ad else None
    if act is None:
        return None
    try:
        from bpy_extras import anim_utils
        fn = getattr(anim_utils, "action_get_channelbag_for_slot", None)
        slot = getattr(ad, "action_slot", None)
        if fn is not None and slot is not None:
            cb = fn(act, slot)
            if cb is not None:
                return cb.fcurves
    except Exception:
        pass
    return getattr(act, "fcurves", None)   # Blender 4.2/4.3 legacy actions


_IPO = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}


def bake_prop(idb, path, frames, values, interp="LINEAR"):
    """Fast bulk keyframing: one keyframe_insert creates the F-curve, the rest
    are written with foreach_set."""
    if not frames:
        return
    vec = not isinstance(values[0], (int, float))
    n = len(values[0]) if vec else 1
    for i in range(n):
        idb.keyframe_insert(data_path=path, index=(i if vec else -1), frame=frames[0])
    fcs = fcurves_for(idb)
    for i in range(n):
        fc = fcs.find(path, index=i) if fcs is not None else None
        if fc is None:   # extremely defensive fallback: slow path
            for f, v in zip(frames, values):
                if vec:
                    getattr(idb, path)[i] = v[i]
                else:
                    setattr(idb, path, v)
                idb.keyframe_insert(data_path=path, index=(i if vec else -1), frame=f)
            continue
        kp = fc.keyframe_points
        missing = len(frames) - len(kp)
        if missing > 0:
            kp.add(missing)
        co = []
        for f, v in zip(frames, values):
            co.append(float(f))
            co.append(float(v[i] if vec else v))
        kp.foreach_set("co", co)
        try:
            kp.foreach_set("interpolation", [_IPO[interp]] * len(kp))
        except Exception:
            for k in kp:
                k.interpolation = interp
        fc.update()


def key_scalar(idb, path, pairs, interp="BEZIER"):
    """pairs: [(time_s, value)]"""
    pairs = sorted(pairs)
    bake_prop(idb, path, [t2f(t) for t, _ in pairs], [v for _, v in pairs], interp)


class Track:
    """Per-frame samples of an object's transform."""

    def __init__(self):
        self.f, self.loc, self.rot, self.scl = [], [], [], []

    def add(self, frame, loc, rot=(0, 0, 0), scl=(1, 1, 1)):
        if self.f and frame <= self.f[-1]:
            return
        self.f.append(frame)
        self.loc.append(tuple(loc))
        self.rot.append(tuple(rot))
        self.scl.append(tuple(scl))

    def apply(self, obj, rot=True, scl=True):
        if not self.f:
            return
        bake_prop(obj, "location", self.f, self.loc)
        if rot:
            bake_prop(obj, "rotation_euler", self.f, self.rot)
        if scl:
            bake_prop(obj, "scale", self.f, self.scl)


TINY = (1e-4, 1e-4, 1e-4)


# ----------------------------------------------------------------------------
# Scene reset
# ----------------------------------------------------------------------------
def reset_scene():
    if bpy.context.scene is None:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "split_world_update":
            bpy.app.handlers.frame_change_pre.remove(h)
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves,
                 bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.node_groups, bpy.data.actions, bpy.data.worlds):
        for item in list(coll):
            try:
                coll.remove(item)
            except Exception:
                pass
    sc = bpy.context.scene
    for c in list(sc.collection.children):
        sc.collection.children.unlink(c)
    return sc


# ----------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------
def build_grade_group():
    """Node group shared by every scene material: cool grey grade left of the
    seam, warm orange grade right of it, plus a shimmering seam line glow on
    every surface the seam cuts through.  'SeamX' is keyed to the physics."""
    ng = bpy.data.node_groups.new("SplitGrade", "ShaderNodeTree")
    ng.interface.new_socket("Color", in_out="INPUT", socket_type="NodeSocketColor")
    ng.interface.new_socket("Color", in_out="OUTPUT", socket_type="NodeSocketColor")
    ng.interface.new_socket("Glow", in_out="OUTPUT", socket_type="NodeSocketFloat")
    N, L = ng.nodes, ng.links
    gi = N.new("NodeGroupInput")
    go = N.new("NodeGroupOutput")
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(geo.outputs["Position"], sep.inputs[0])
    seam = N.new("ShaderNodeValue"); seam.name = seam.label = "SeamX"
    seam.outputs[0].default_value = 0.0
    shim = N.new("ShaderNodeValue"); shim.name = shim.label = "ShimmerW"
    d = N.new("ShaderNodeMath"); d.operation = "SUBTRACT"
    L.new(sep.outputs[0], d.inputs[0]); L.new(seam.outputs[0], d.inputs[1])
    mask = N.new("ShaderNodeMapRange"); mask.interpolation_type = "SMOOTHSTEP"
    mask.inputs["From Min"].default_value = -0.03
    mask.inputs["From Max"].default_value = 0.03
    L.new(d.outputs[0], mask.inputs["Value"])

    def graded(sat, val, tint):
        hs = N.new("ShaderNodeHueSaturation")
        hs.inputs["Saturation"].default_value = sat
        hs.inputs["Value"].default_value = val
        L.new(gi.outputs[0], hs.inputs["Color"])
        mul = N.new("ShaderNodeVectorMath"); mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = tint
        L.new(hs.outputs[0], mul.inputs[0])
        return mul.outputs[0]

    cool = graded(0.35, 0.95, (0.82, 0.90, 1.05))
    warm = graded(1.25, 1.0, (1.22, 0.86, 0.58))
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    L.new(mask.outputs[0], mix.inputs[0])
    L.new(cool, mix.inputs[6]); L.new(warm, mix.inputs[7])
    L.new(mix.outputs[2], go.inputs["Color"])
    # seam line glow with noise shimmer
    ad = N.new("ShaderNodeMath"); ad.operation = "ABSOLUTE"
    L.new(d.outputs[0], ad.inputs[0])
    line = N.new("ShaderNodeMapRange")
    line.inputs["From Min"].default_value = 0.0
    line.inputs["From Max"].default_value = 0.022
    line.inputs["To Min"].default_value = 1.0
    line.inputs["To Max"].default_value = 0.0
    L.new(ad.outputs[0], line.inputs["Value"])
    nz = N.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 4.0
    L.new(geo.outputs["Position"], nz.inputs["Vector"])
    L.new(shim.outputs[0], nz.inputs["W"])
    nzm = N.new("ShaderNodeMapRange")
    nzm.inputs["From Min"].default_value = 0.3
    nzm.inputs["From Max"].default_value = 0.7
    nzm.inputs["To Min"].default_value = 0.6
    nzm.inputs["To Max"].default_value = 3.0
    L.new(nz.outputs[0], nzm.inputs["Value"])
    gl = N.new("ShaderNodeMath"); gl.operation = "MULTIPLY"
    L.new(line.outputs[0], gl.inputs[0]); L.new(nzm.outputs[0], gl.inputs[1])
    L.new(gl.outputs[0], go.inputs["Glow"])
    return ng


SEAM_GLOW_COL = (1.0, 0.72, 0.38, 1.0)


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    return m


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def mat_graded(name, color=None, rough=0.5, metal=0.0, transmission=0.0,
               ior=1.45, coat=0.0, color_socket_fn=None, glow=True):
    """color_socket_fn(nodes, links) -> output socket giving the base colour."""
    m = new_mat(name)
    N, L = m.node_tree.nodes, m.node_tree.links
    bs = principled(m)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    bs.inputs["IOR"].default_value = ior
    if transmission:
        bs.inputs["Transmission Weight"].default_value = transmission
    if coat:
        bs.inputs["Coat Weight"].default_value = coat
    grp = N.new("ShaderNodeGroup"); grp.node_tree = bpy.data.node_groups["SplitGrade"]
    if color_socket_fn:
        L.new(color_socket_fn(N, L), grp.inputs[0])
    else:
        grp.inputs[0].default_value = (*color, 1.0)
    L.new(grp.outputs["Color"], bs.inputs["Base Color"])
    if glow:
        bs.inputs["Emission Color"].default_value = SEAM_GLOW_COL
        L.new(grp.outputs["Glow"], bs.inputs["Emission Strength"])
    return m


def mat_emit(name, color, strength=1.0, alpha=1.0):
    m = new_mat(name)
    N, L = m.node_tree.nodes, m.node_tree.links
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    for n in list(N):
        if n.type != "OUTPUT_MATERIAL":
            N.remove(n)
    em = N.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1.0)
    em.inputs["Strength"].default_value = strength
    if alpha < 1.0:
        tr = N.new("ShaderNodeBsdfTransparent")
        mx = N.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = alpha
        L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2])
        L.new(mx.outputs[0], out.inputs[0])
        set_blend(m)
    else:
        L.new(em.outputs[0], out.inputs[0])
    return m


def set_blend(m):
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(m, attr, val)
            break
        except Exception:
            pass


def tex_wood(scale=(1.0, 6.0, 1.0), c1=(0.33, 0.18, 0.08), c2=(0.55, 0.33, 0.16)):
    def fn(N, L):
        tc = N.new("ShaderNodeTexCoord")
        mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = scale
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 3.0
        wv.inputs["Distortion"].default_value = 6.0
        wv.inputs["Detail"].default_value = 3.0
        L.new(mp.outputs[0], wv.inputs["Vector"])
        cr = N.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].color = (*c1, 1)
        cr.color_ramp.elements[1].color = (*c2, 1)
        L.new(wv.outputs["Fac"], cr.inputs[0])
        return cr.outputs[0]
    return fn


def tex_bricks(c1, c2, mortar, scale, bw, rh, mortar_size=0.02, offset=0.5):
    def fn(N, L):
        tc = N.new("ShaderNodeTexCoord")
        br = N.new("ShaderNodeTexBrick")
        br.offset = offset
        br.inputs["Color1"].default_value = (*c1, 1)
        br.inputs["Color2"].default_value = (*c2, 1)
        br.inputs["Mortar"].default_value = (*mortar, 1)
        br.inputs["Scale"].default_value = scale
        br.inputs["Mortar Size"].default_value = mortar_size
        br.inputs["Brick Width"].default_value = bw
        br.inputs["Row Height"].default_value = rh
        L.new(tc.outputs["Object"], br.inputs["Vector"])
        return br.outputs["Color"]
    return fn


def tex_stripes(c1, c2, scale=3.0):
    def fn(N, L):
        tc = N.new("ShaderNodeTexCoord")
        wv = N.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = scale
        wv.wave_profile = "SIN"
        L.new(tc.outputs["Object"], wv.inputs["Vector"])
        gt = N.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        L.new(wv.outputs["Fac"], gt.inputs[0])
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"
        mx.inputs[6].default_value = (*c1, 1); mx.inputs[7].default_value = (*c2, 1)
        L.new(gt.outputs[0], mx.inputs[0])
        return mx.outputs[2]
    return fn


def tex_card():
    """White face with red border + diamond on the front, red back."""
    def fn(N, L):
        tc = N.new("ShaderNodeTexCoord")
        sep = N.new("ShaderNodeSeparateXYZ")
        L.new(tc.outputs["UV"], sep.inputs[0])

        def absd(sock, c):
            s = N.new("ShaderNodeMath"); s.operation = "SUBTRACT"
            s.inputs[1].default_value = c
            L.new(sock, s.inputs[0])
            a = N.new("ShaderNodeMath"); a.operation = "ABSOLUTE"
            L.new(s.outputs[0], a.inputs[0])
            return a.outputs[0]
        du, dv = absd(sep.outputs[0], 0.5), absd(sep.outputs[1], 0.5)
        su = N.new("ShaderNodeMath"); su.operation = "MULTIPLY"; su.inputs[1].default_value = 1 / 0.16
        L.new(du, su.inputs[0])
        sv = N.new("ShaderNodeMath"); sv.operation = "MULTIPLY"; sv.inputs[1].default_value = 1 / 0.2
        L.new(dv, sv.inputs[0])
        ad = N.new("ShaderNodeMath"); ad.operation = "ADD"
        L.new(su.outputs[0], ad.inputs[0]); L.new(sv.outputs[0], ad.inputs[1])
        dia = N.new("ShaderNodeMath"); dia.operation = "LESS_THAN"; dia.inputs[1].default_value = 1.0
        L.new(ad.outputs[0], dia.inputs[0])
        mxd = N.new("ShaderNodeMath"); mxd.operation = "MAXIMUM"
        L.new(du, mxd.inputs[0]); L.new(dv, mxd.inputs[1])
        brd = N.new("ShaderNodeMath"); brd.operation = "GREATER_THAN"; brd.inputs[1].default_value = 0.43
        L.new(mxd.outputs[0], brd.inputs[0])
        red = N.new("ShaderNodeMath"); red.operation = "MAXIMUM"
        L.new(dia.outputs[0], red.inputs[0]); L.new(brd.outputs[0], red.inputs[1])
        front = N.new("ShaderNodeMix"); front.data_type = "RGBA"
        front.inputs[6].default_value = (0.95, 0.94, 0.9, 1)
        front.inputs[7].default_value = (0.75, 0.04, 0.05, 1)
        L.new(red.outputs[0], front.inputs[0])
        geo = N.new("ShaderNodeNewGeometry")
        side = N.new("ShaderNodeMix"); side.data_type = "RGBA"
        side.inputs[7].default_value = (0.55, 0.03, 0.05, 1)
        L.new(geo.outputs["Backfacing"], side.inputs[0])
        L.new(front.outputs[2], side.inputs[6])
        return side.outputs[2]
    return fn


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, verts, faces, mat=None, uvs=None, smooth_shade=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if uvs:
        uvl = me.uv_layers.new(name="UVMap")
        for i, loop in enumerate(me.loops):
            uvl.data[i].uv = uvs[loop.vertex_index]
    me.update()
    if smooth_shade:
        for p in me.polygons:
            p.use_smooth = True
    ob = link(bpy.data.objects.new(name, me))
    if mat:
        me.materials.append(mat)
    return ob


def prim(kind, name, mat=None, smooth_shade=True, **kw):
    getattr(bpy.ops.mesh, "primitive_%s_add" % kind)(**kw)
    ob = bpy.context.active_object
    ob.name = name
    if mat:
        ob.data.materials.append(mat)
    if smooth_shade and hasattr(ob.data, "polygons"):
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def box(name, center, size, mat, bevel=0.0):
    ob = prim("cube", name, mat, smooth_shade=False, location=center)
    ob.data.transform(Matrix.Diagonal((size[0] / 2, size[1] / 2, size[2] / 2, 1.0)))
    ob.data.update()
    if bevel:
        bm = ob.modifiers.new("bevel", "BEVEL")
        bm.width = bevel; bm.segments = 2
        try:
            bm.use_clamp_overlap = True
        except Exception:
            pass
    return ob


def parent(child, par):
    child.parent = par
    child.matrix_parent_inverse = Matrix.Identity(4)


# ----------------------------------------------------------------------------
# PHYSICS  -- deterministic sub-stepped integrators
# ----------------------------------------------------------------------------
def ballistic_step(x, z, vx, vz, ax_extra, t):
    """Exact update for constant acceleration over one sub-step."""
    g = g_at(x, t)
    az = -g
    x += vx * DT + 0.5 * ax_extra * DT * DT
    z += vz * DT + 0.5 * az * DT * DT
    vx += ax_extra * DT
    vz += az * DT
    return x, z, vx, vz


def support_height(x, y):
    return TH if (abs(x) <= TX and abs(y) <= TY) else 0.0


def sim_ball(side, y, t_appear, t_push, t_end, x0, speed):
    """Ball rolls on the table, leaves the edge, falls 1 m, bounces."""
    r = 0.1
    trk = Track()
    sgn = -1 if side == "L" else 1
    x, z, vx, vz, ang = x0, TH + r, 0.0, 0.0, 0.0
    on_table = True
    t_leave = t_land = None
    n0 = int(math.ceil(t2f(t_appear) - 1)) * SUB
    n_end = int(t_end * FPS) * SUB
    # appearance pop
    f_ap = int(math.ceil(t2f(t_appear)))
    trk.add(f_ap - 1, (x, y, z), (0, 0, 0), TINY)
    for n in range(n0, n_end + 1):
        t = n * DT
        if n % SUB == 0:
            f = n // SUB + 1
            pop = clamp((t - t_appear) / 0.25)
            s = 0.0001 + smooth(pop) * (1.0 - 0.0001)
            trk.add(f, (x, y, z), (0, ang, 0), (s, s, s))
        if t < t_push:
            continue
        if on_table and vx == 0.0:
            vx = sgn * speed
        if on_table:
            nx = x + vx * DT
            if abs(nx) > TX:
                # exact edge crossing time
                t_leave = t + (TX - abs(x)) / abs(vx)
                on_table = False
            x = nx
            ang += vx / r * DT
            continue
        zp = z
        x, z, vx, vz = ballistic_step(x, z, vx, vz, 0.0, t)
        ang += vx / r * DT
        if z - r <= 0.0:
            if t_land is None:
                # linear interpolation inside the sub-step
                t_land = t + DT * (zp - r) / (zp - z)
            z = r
            if abs(vz) > 0.25:
                vz = -0.5 * vz
                vx *= 0.6
            else:
                vz = 0.0
        if z <= r + 1e-9 and vz == 0.0 and vx != 0.0:
            dec = 0.25 * g_at(x, t) * DT
            vx = 0.0 if abs(vx) <= dec else vx - math.copysign(dec, vx)
    return trk, t_leave, t_land


def sim_pendulum(t_start, t_end):
    L = CONFIG["PEND_L"]
    px = CONFIG["PEND_PIVOT"][0]
    th = math.radians(CONFIG["PEND_THETA0_DEG"])
    om = 0.0
    frames, thetas = [], []
    crossings = []   # (time, direction +1 = moving right)
    n0 = int(round(t_start * FPS)) * SUB
    n_end = int(round(t_end * FPS)) * SUB
    t_rel = CONFIG["PEND_RELEASE"]
    for n in range(n0, n_end + 1):
        t = n * DT
        if n % SUB == 0:
            frames.append(n // SUB + 1)
            thetas.append(th)
        if t < t_rel:
            continue
        # velocity-Verlet, g evaluated at the bob's x position
        xb = px + L * math.sin(th)
        a0 = -(g_at(xb, t) / L) * math.sin(th)
        thn = th + om * DT + 0.5 * a0 * DT * DT
        xbn = px + L * math.sin(thn)
        a1 = -(g_at(xbn, t + DT) / L) * math.sin(thn)
        om += 0.5 * (a0 + a1) * DT
        if (th < 0.0) != (thn < 0.0):
            tc = t + DT * (-th) / (thn - th)
            crossings.append((tc, 1 if thn > th else -1))
        th = thn
    return frames, thetas, crossings


def sim_cards(rng, t_launch, t_end):
    """Deck bursts across the seam.  Quadratic drag (same air both sides),
    a 'falling-leaf' flutter force while descending and tumble that decays.
    On the Moon the drag/flutter dominate; on Jupiter gravity wins."""
    k = CONFIG["CARD_DRAG"]
    nC = CONFIG["N_CARDS"]
    tracks, landings = [], []
    landed_xy = []
    for i in range(nC):
        trk = Track()
        y = 0.2 + rng.uniform(-0.05, 0.05)
        x = rng.uniform(-0.03, 0.03)
        z = TH + 0.002 + 0.003 * i
        rz = rng.uniform(-0.15, 0.15)
        side = -1 if i % 2 == 0 else 1
        tl = t_launch + 0.025 * (nC - 1 - i)          # top card leaves first
        vx = side * rng.uniform(0.2, 1.4)
        vy = rng.uniform(-0.35, 0.1)
        vz = rng.uniform(3.0, 4.6)
        wx, wy, wz = rng.uniform(-9, 9), rng.uniform(-9, 9), rng.uniform(-3, 3)
        ph = rng.uniform(0, 2 * math.pi)
        fw = rng.uniform(4.5, 6.5)                     # flutter rad/s
        rx = ry = 0.0
        landed = False
        t_land = None
        n0 = int(round((t_launch - 1.2) * FPS)) * SUB
        n_end = int(round(t_end * FPS)) * SUB
        f_ap = int(round(t2f(t_launch - 1.2)))
        trk.add(f_ap - 1, (x, y, z), (0, 0, rz), TINY)
        for n in range(n0, n_end + 1):
            t = n * DT
            if n % SUB == 0:
                f = n // SUB + 1
                s = 0.0001 + smooth((t - (t_launch - 1.2)) / 0.25) * 0.9999
                trk.add(f, (x, y, z), (rx, ry, rz), (s, s, s))
            if t < tl or landed:
                continue
            g = g_at(x, t)
            sp = math.sqrt(vx * vx + vy * vy + vz * vz)
            vt = math.sqrt(g / k)
            desc = clamp(-vz / vt)                    # 0 rising .. 1 at terminal
            flut = 1.6 * desc * math.sin(fw * (t - tl) + ph)
            ax = -k * sp * vx + flut
            ay = -k * sp * vy
            az = -g - k * sp * vz
            vx += ax * DT; vy += ay * DT; vz += az * DT
            x += vx * DT; y += vy * DT; z += vz * DT
            damp = math.exp(-2.5 * DT)
            wx *= damp; wy *= damp
            rx += wx * DT
            ry += wy * DT
            rz += wz * DT
            # rocking like a leaf - only visible where flutter dominates gravity
            ry_rock = 0.9 * (1.6 / (1.6 + g)) * desc * math.sin(fw * (t - tl) + ph)
            ry += (ry_rock - ry) * min(1.0, 6.0 * DT) if abs(wy) < 1.0 else 0.0
            sup = support_height(x, y)
            if vz < 0 and z <= sup + 0.002:
                landed = True
                t_land = t
                nb = sum(1 for (lx, ly) in landed_xy
                         if abs(lx - x) < 0.18 and abs(ly - y) < 0.25)
                landed_xy.append((x, y))
                z = sup + 0.002 + 0.0025 * nb
                rx = round(rx / math.pi) * math.pi
                ry = 0.0
        tracks.append(trk)
        landings.append((x, t_land - tl if t_land else None))
    return tracks, landings


def sim_eggs(egg_specs, t_appear, t_end):
    """egg_specs: [(x, y, t_toss, vz)]  -> tracks, splat info."""
    out = []
    hz = 0.115
    for (x, y, tt, vz0) in egg_specs:
        trk = Track()
        z, vx, vz = TH + hz, 0.02 * (x + 0.8), 0.0
        state = "rest"
        splat_t = None
        rot = 0.0
        n0 = int(round(t_appear * FPS)) * SUB
        n_end = int(round(t_end * FPS)) * SUB
        trk.add(int(round(t2f(t_appear))) - 1, (x, y, z), (0, 0, 0), TINY)
        for n in range(n0, n_end + 1):
            t = n * DT
            if n % SUB == 0:
                f = n // SUB + 1
                if state == "splat":
                    u = smooth((t - splat_t) / 0.08)
                    sc = (1 + 1.7 * u, 1 + 1.5 * u, 1 - 0.88 * u)
                    zz = TH + hz * (1 - 0.9 * u)
                    trk.add(f, (x, y, zz), (0, 0, 0), sc)
                else:
                    s = 0.0001 + smooth((t - t_appear) / 0.25) * 0.9999
                    trk.add(f, (x, y, z), (rot, 0.3 * rot, 0), (s, s, s))
            if state == "rest" and t >= tt:
                state = "air"
                vz = vz0
            if state != "air":
                continue
            x, z, vx, vz = ballistic_step(x, z, vx, vz, 0.0, t)
            rot += 2.5 * DT
            if vz < 0 and z <= TH + hz:
                spd = abs(vz)
                if spd > 4.5:
                    state, splat_t = "splat", t
                    z = TH + hz
                else:
                    z = TH + hz
                    vz = 0.3 * spd
                    if vz < 0.3:
                        state = "rest2"
        out.append((trk, splat_t, (x, y)))
    return out


def water_rig_pose(t):
    A = Vector((-1.62, -0.15, 2.5))
    B = Vector((-1.35, -0.15, 2.25))
    if t < 4.6:
        loc = A.lerp(B, smooth(t / 0.7))
    else:
        loc = B.lerp(A + Vector((-1.0, 0, 0.3)), smooth((t - 4.6) / 0.9))
    tilt = math.radians(50) * (smooth((t - 0.3) / 0.5) - smooth((t - 4.2) / 0.5))
    return loc, tilt


SPOUT_LOCAL = Vector((0.172, 0.0, 0.14))


def spout_world(t):
    loc, tilt = water_rig_pose(t)
    return loc + Matrix.Rotation(tilt, 3, "Y") @ SPOUT_LOCAL


def pour_intensity(t):
    a, b = 0.65, 4.3
    if t < a or t > b:
        return 0.0
    return 0.45 + 0.55 * smooth((t - a) / 0.3) * (1 - smooth((t - (b - 0.6)) / 0.6))


def sim_water(rng, t_end):
    """Fake water: a stream of soft blobs, each integrated with the gravity of
    the side it is on.  Blobs that hit the table burst into droplets."""
    rate = 30.0
    blobs, drops = [], []
    impacts = {"L": [], "R": []}
    t = 0.65
    emits = []
    while t <= 4.3:
        emits.append(t)
        t += 1.0 / rate

    def run(p, v, t0, r, kind):
        trk = Track()
        x, y, z = p
        vx, vy, vz = v
        f0 = int(math.ceil(t2f(t0)))
        trk.add(f0 - 1, (x, y, z), (0, 0, 0), TINY)
        n = int(math.ceil(t0 * FPS * SUB))
        n_max = int(t_end * FPS) * SUB
        hit = None
        while n <= n_max:
            tt = n * DT
            if n % SUB == 0:
                spd = math.sqrt(vx * vx + vy * vy + vz * vz) + 1e-6
                d = Vector((vx, vy, vz)) / spd
                rot = d.to_track_quat("Z", "Y").to_euler()
                st = 1.0 + 0.14 * spd
                sq = 1.0 / math.sqrt(st)
                trk.add(n // SUB + 1, (x, y, z), tuple(rot), (r * sq, r * sq, r * st))
            x, z, vx, vz = ballistic_step(x, z, vx, vz, 0.0, tt)
            y += vy * DT
            sup = support_height(x, y)
            if vz < 0 and z - r * 0.5 <= sup:
                hit = (tt, x, y, sup, math.sqrt(vx * vx + vz * vz), vx)
                f = int(math.floor(tt * FPS)) + 2
                trk.add(f, (x, y, sup + r * 0.3), (0, 0, 0), (r * 1.8, r * 1.8, r * 0.25))
                trk.add(f + 2, (x, y, sup + 0.002), (0, 0, 0), TINY)
                break
            if x < -2.6 or x > 2.6:
                trk.add(n // SUB + 2, (x, y, z), (0, 0, 0), TINY)
                break
            n += 1
        return trk, hit

    for te in emits:
        inten = pour_intensity(te)
        p = spout_world(te)
        v = (1.25 * inten + rng.uniform(-0.04, 0.04),
             rng.uniform(-0.04, 0.04),
             0.25 * inten + rng.uniform(-0.05, 0.05))
        r = rng.uniform(0.032, 0.046)
        trk, hit = run(p, v, te, r, "blob")
        blobs.append(trk)
        if hit:
            tt, x, y, sup, spd, vxi = hit
            side = "L" if x < seam_x(tt) else "R"
            impacts[side].append((tt, x, y, "blob"))
            for j in range(2):
                ang = rng.uniform(0, 2 * math.pi)
                hs = rng.uniform(0.25, 0.9) * (0.15 * spd + 0.2)
                dv = (0.35 * vxi + hs * math.cos(ang), hs * math.sin(ang) * 0.6,
                      0.32 * spd * rng.uniform(0.6, 1.1) + 0.2)
                dtrk, dhit = run((x, y, sup + 0.02), dv, tt + 0.001,
                                 rng.uniform(0.013, 0.022), "drop")
                drops.append(dtrk)
                if dhit:
                    side2 = "L" if dhit[1] < seam_x(dhit[0]) else "R"
                    impacts[side2].append((dhit[0], dhit[1], dhit[2], "drop"))
    return blobs, drops, impacts


# ----------------------------------------------------------------------------
# Exact pendulum period (for verification)
# ----------------------------------------------------------------------------
def ellip_K(k):
    a, b = 1.0, math.sqrt(1 - k * k)
    for _ in range(30):
        a, b = 0.5 * (a + b), math.sqrt(a * b)
    return math.pi / (2 * a)


def exact_period(g, L, amp):
    return 4 * math.sqrt(L / g) * ellip_K(math.sin(abs(amp) / 2))


# ----------------------------------------------------------------------------
# BUILD
# ----------------------------------------------------------------------------
STATE = {}


def build():
    t_build = time.time()
    rng = random.Random(CONFIG["SEED"])
    sc = reset_scene()
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, N_FRAMES
    sc.render.resolution_x, sc.render.resolution_y = CONFIG["RESOLUTION"]
    sc.gravity = (0.0, 0.0, 0.0)   # all motion comes from our own integrator

    ng = build_grade_group()
    # seam position + shimmer keyed for the whole film
    frames = list(range(1, N_FRAMES + 1))
    bake_prop(ng, 'nodes["SeamX"].outputs[0].default_value', frames,
              [seam_x(f2t(f)) for f in frames])
    bake_prop(ng, 'nodes["ShimmerW"].outputs[0].default_value', [1, N_FRAMES],
              [0.0, CONFIG["DURATION"] * 1.4])

    # ---------------- world / lights ----------------
    world = bpy.data.worlds.new("SplitWorldWorld")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.03, 0.03, 0.035, 1)
    bg.inputs[1].default_value = 1.0

    def area(name, loc, rot, color, power, size):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power; ld.color = color; ld.size = size
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc; ob.rotation_euler = rot
        return ob, ld

    COOL = (0.72, 0.84, 1.0)
    WARM = (1.0, 0.62, 0.32)
    _, l_left = area("KeyMoon", (-2.2, -2.6, 4.6), (math.radians(40), math.radians(-25), 0), COOL, 380, 2.5)
    _, l_right = area("KeyJupiter", (2.2, -2.6, 4.6), (math.radians(40), math.radians(25), 0), WARM, 450, 2.5)
    area("Fill", (0, -6.5, 2.4), (math.radians(90), 0, 0), (1, 1, 1), 60, 4.0)
    area("Rim", (0, 1.0, 5.2), (0, 0, 0), (1, 0.95, 0.9), 90, 5.0)
    t0, t1 = CONFIG["SEAM_SLIDE"]
    l_left.color = COOL
    l_left.keyframe_insert("color", frame=t2f(t0))
    l_left.color = WARM
    l_left.keyframe_insert("color", frame=t2f(t1))

    # ---------------- camera ----------------
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "VERTICAL"; cd.sensor_height = 36.0; cd.lens = 40.0
    cd.clip_start = 0.05; cd.clip_end = 100
    cam = link(bpy.data.objects.new("Camera", cd))
    cam.location = (0.0, -6.8, 2.45)
    cam.rotation_euler = (math.radians(87.0), 0, 0)
    sc.camera = cam

    # ---------------- kitchen ----------------
    m_floor = mat_graded("Floor", rough=0.45, color_socket_fn=tex_bricks(
        (0.20, 0.11, 0.06), (0.16, 0.09, 0.05), (0.05, 0.03, 0.02), 1.0, 1.4, 0.18, 0.006, 0.37))
    m_wall = mat_graded("WallTiles", rough=0.25, color_socket_fn=tex_bricks(
        (0.36, 0.38, 0.37), (0.32, 0.34, 0.33), (0.12, 0.12, 0.12), 1.0, 0.2, 0.2, 0.008, 0.0))
    m_wood = mat_graded("TableWood", rough=0.35, coat=0.3,
                        color_socket_fn=tex_wood((0.6, 5.0, 0.6)))
    m_cab = mat_graded("Cabinet", color=(0.08, 0.14, 0.13), rough=0.4)
    m_counter = mat_graded("Counter", color=(0.15, 0.15, 0.16), rough=0.3)
    m_metal = mat_graded("Steel", color=(0.7, 0.7, 0.72), rough=0.25, metal=1.0)

    floor = box("Floor", (0, 2.0, -0.05), (16, 14, 0.1), m_floor)
    wall = box("BackWall", (0, 1.9, 4.0), (16, 0.1, 8.5), m_wall)
    # counter run along the back wall
    box("Cabinets", (0, 1.5, 0.45), (12, 0.7, 0.9), m_cab, bevel=0.01)
    box("Countertop", (0, 1.45, 0.93), (12.2, 0.8, 0.06), m_counter, bevel=0.01)
    for i, xx in enumerate((-2.4, -1.2, 0.0, 1.2, 2.4)):
        box("Handle%d" % i, (xx, 1.13, 0.75), (0.25, 0.03, 0.03), m_metal)
    box("WallShelf", (0, 1.7, 3.1), (12, 0.35, 0.05), m_wood)
    # table
    box("TableTop", (0, 0, TH - 0.03), (2 * TX, 2 * TY, 0.06), m_wood, bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("Leg", (sx * (TX - 0.08), sy * (TY - 0.08), (TH - 0.06) / 2),
                (0.07, 0.07, TH - 0.06), m_wood)
    # a few jars on the shelf / counter
    m_jar = mat_graded("Jar", color=(0.85, 0.75, 0.55), rough=0.3)
    for i, xx in enumerate((-1.7, -1.45, 1.4, 1.65, 1.9)):
        prim("cylinder", "Jar%d" % i, m_jar, vertices=24, radius=0.08,
             depth=0.2 + 0.05 * (i % 2), location=(xx, 1.65, 3.25 + 0.025 * (i % 2)))

    # ---------------- seam glow sheet ----------------
    m_seam = new_mat("SeamGlow")
    N, Lk = m_seam.node_tree.nodes, m_seam.node_tree.links
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    for n in list(N):
        if n.type != "OUTPUT_MATERIAL":
            N.remove(n)
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ"); Lk.new(tc.outputs["UV"], sep.inputs[0])
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.5
    Lk.new(sep.outputs[0], sub.inputs[0])

    def gauss(width, amp):
        m1 = N.new("ShaderNodeMath"); m1.operation = "DIVIDE"; m1.inputs[1].default_value = width
        Lk.new(sub.outputs[0], m1.inputs[0])
        sq = N.new("ShaderNodeMath"); sq.operation = "MULTIPLY"
        Lk.new(m1.outputs[0], sq.inputs[0]); Lk.new(m1.outputs[0], sq.inputs[1])
        ng_ = N.new("ShaderNodeMath"); ng_.operation = "MULTIPLY"; ng_.inputs[1].default_value = -1.0
        Lk.new(sq.outputs[0], ng_.inputs[0])
        ex = N.new("ShaderNodeMath"); ex.operation = "EXPONENT"; Lk.new(ng_.outputs[0], ex.inputs[0])
        am = N.new("ShaderNodeMath"); am.operation = "MULTIPLY"; am.inputs[1].default_value = amp
        Lk.new(ex.outputs[0], am.inputs[0])
        return am.outputs[0]
    core = gauss(0.012, 4.0)
    halo = gauss(0.07, 0.18)
    nz = N.new("ShaderNodeTexNoise"); nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 3.0
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 8.0, 1.0)
    Lk.new(tc.outputs["UV"], mp.inputs["Vector"]); Lk.new(mp.outputs[0], nz.inputs["Vector"])
    wv = N.new("ShaderNodeValue"); wv.name = "W"
    Lk.new(wv.outputs[0], nz.inputs["W"])
    nzr = N.new("ShaderNodeMapRange")
    nzr.inputs["From Min"].default_value = 0.3; nzr.inputs["From Max"].default_value = 0.7
    nzr.inputs["To Min"].default_value = 0.45; nzr.inputs["To Max"].default_value = 1.4
    Lk.new(nz.outputs[0], nzr.inputs["Value"])
    tot = N.new("ShaderNodeMath"); tot.operation = "ADD"
    Lk.new(core, tot.inputs[0]); Lk.new(halo, tot.inputs[1])
    st = N.new("ShaderNodeMath"); st.operation = "MULTIPLY"
    Lk.new(tot.outputs[0], st.inputs[0]); Lk.new(nzr.outputs[0], st.inputs[1])
    em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = SEAM_GLOW_COL
    Lk.new(st.outputs[0], em.inputs["Strength"])
    tr = N.new("ShaderNodeBsdfTransparent")
    addn = N.new("ShaderNodeAddShader")
    Lk.new(tr.outputs[0], addn.inputs[0]); Lk.new(em.outputs[0], addn.inputs[1])
    Lk.new(addn.outputs[0], out.inputs[0])
    set_blend(m_seam)
    seam = mesh_obj("SeamSheet", [(-0.4, 0, -0.2), (0.4, 0, -0.2), (0.4, 0, 6.8), (-0.4, 0, 6.8)],
                    [(0, 1, 2, 3)], m_seam, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    seam.location = (0, -0.75, 0)
    try:
        seam.visible_shadow = False
    except Exception:
        pass
    bake_prop(seam, "location", frames, [(seam_x(f2t(f)), -0.75, 0.0) for f in frames])
    bake_prop(m_seam.node_tree, 'nodes["W"].outputs[0].default_value', [1, N_FRAMES],
              [0.0, CONFIG["DURATION"] * 1.6])

    # ---------------- glass of water on the seam ----------------
    m_glass = mat_graded("Glass", color=(0.95, 0.97, 1.0), rough=0.03, transmission=1.0, ior=1.45, glow=False)
    m_water = mat_graded("Water", color=(0.35, 0.62, 0.95), rough=0.05, transmission=0.55,
                         ior=1.33, coat=1.0, glow=False)
    glass = prim("cylinder", "GlassCup", m_glass, vertices=40, radius=0.075, depth=0.2,
                 location=(0.0, 0.18, TH + 0.1))
    sol = glass.modifiers.new("solid", "SOLIDIFY"); sol.thickness = 0.006
    prim("cylinder", "GlassWater", m_water, vertices=40, radius=0.066, depth=0.13,
         location=(0.0, 0.18, TH + 0.072))
    # remove glass top cap so it is open
    import bmesh
    bm = bmesh.new(); bm.from_mesh(glass.data)
    caps = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=caps, context="FACES")
    bm.to_mesh(glass.data); bm.free()

    # ---------------- pitcher + stylised hand ----------------
    m_ceramic = mat_graded("Ceramic", color=(0.92, 0.88, 0.80), rough=0.2, coat=0.5)
    m_skin = mat_graded("Skin", color=(0.85, 0.58, 0.44), rough=0.55)
    m_sleeve = mat_graded("Sleeve", color=(0.12, 0.22, 0.45), rough=0.8)
    rig = link(bpy.data.objects.new("PourRig", None))
    parts = []
    body = prim("cylinder", "PitcherBody", m_ceramic, vertices=40, radius=0.11, depth=0.30)
    bev = body.modifiers.new("bev", "BEVEL"); bev.width = 0.015; bev.segments = 3
    parts.append(body)
    sp = prim("cone", "Spout", m_ceramic, vertices=24, radius1=0.05, radius2=0.016, depth=0.13,
              location=(0.12, 0, 0.105), rotation=(0, math.radians(60), 0))
    parts.append(sp)
    hd = prim("torus", "Handle", m_ceramic, major_radius=0.075, minor_radius=0.017,
              location=(-0.12, 0, 0.0), rotation=(math.radians(90), 0, 0))
    parts.append(hd)
    palm = prim("uv_sphere", "Palm", m_skin, radius=1.0, location=(-0.26, -0.01, 0.02))
    palm.scale = (0.075, 0.06, 0.095)
    parts.append(palm)
    for j, zz in enumerate((0.05, 0.017, -0.017, -0.05)):
        fg = prim("uv_sphere", "Finger%d" % j, m_skin, radius=1.0, location=(-0.19, -0.035, zz))
        fg.scale = (0.055, 0.024, 0.019)
        parts.append(fg)
    th_ = prim("uv_sphere", "Thumb", m_skin, radius=1.0, location=(-0.2, 0.0, 0.115))
    th_.scale = (0.05, 0.022, 0.024); th_.rotation_euler = (0, math.radians(25), 0)
    parts.append(th_)
    a0, a1 = Vector((-0.3, 0.0, 0.03)), Vector((-1.6, 0.0, 0.55))
    dvec = a1 - a0
    sl = prim("cylinder", "Sleeve", m_sleeve, vertices=24, radius=0.07, depth=dvec.length,
              location=(a0 + a1) / 2)
    sl.rotation_euler = dvec.to_track_quat("Z", "Y").to_euler()
    parts.append(sl)
    for p in parts:
        parent(p, rig)
    rtrk_f, rtrk_l, rtrk_r = [], [], []
    for f in range(1, int(t2f(6.0)) + 1):
        loc, tilt = water_rig_pose(f2t(f))
        rtrk_f.append(f); rtrk_l.append(tuple(loc)); rtrk_r.append((0.0, tilt, 0.0))
    bake_prop(rig, "location", rtrk_f, rtrk_l)
    bake_prop(rig, "rotation_euler", rtrk_f, rtrk_r)

    # ---------------- water blobs ----------------
    blobs, drops, impacts = sim_water(rng, 7.0)
    blob_me = bpy.data.meshes.new("BlobMesh")
    import bmesh as _bm
    bm = _bm.new(); _bm.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
    bm.to_mesh(blob_me); bm.free()
    for p in blob_me.polygons:
        p.use_smooth = True
    blob_me.materials.append(m_water)
    for i, trk in enumerate(blobs + drops):
        ob = link(bpy.data.objects.new("Water%03d" % i, blob_me))
        ob.scale = TINY
        trk.apply(ob)
    # puddles grow as blobs land
    m_puddle = mat_graded("Puddle", color=(0.25, 0.42, 0.6), rough=0.03, coat=1.0, glow=False)
    for side, imps in impacts.items():
        if not imps:
            continue
        on_table = [(t, x, y) for (t, x, y, kind) in imps if abs(x) <= TX and kind == "blob"]
        if not on_table:
            continue
        cx = sum(x for _, x, _ in on_table) / len(on_table)
        cy = sum(y for _, _, y in on_table) / len(on_table)
        pud = prim("cylinder", "Puddle" + side, m_puddle, vertices=48, radius=1.0, depth=0.004,
                   location=(cx, cy, TH + 0.002))
        ts = sorted(t for t, _, _ in on_table)
        pf, ps = [], []
        cnt = 0
        for f in range(int(t2f(ts[0])) - 1, int(t2f(ts[-1])) + 3):
            while cnt < len(ts) and ts[cnt] <= f2t(f):
                cnt += 1
            r = 0.0001 + 0.016 * math.sqrt(cnt)
            pf.append(f); ps.append((r * 1.5, r * 0.8, 1.0))
        bake_prop(pud, "scale", pf, ps)

    # ---------------- twin balls ----------------
    m_ball = mat_graded("Ball", rough=0.35, color_socket_fn=tex_stripes((0.9, 0.9, 0.9), (0.85, 0.12, 0.1), 2.0))
    ball_data = {}
    for side in ("L", "R"):
        x0 = -0.35 if side == "L" else 0.35
        trk, tl, tld = sim_ball(side, -0.33, 5.2, 5.4, 19.0, x0, 0.3)
        ob = prim("uv_sphere", "Ball" + side, m_ball, radius=0.1, segments=32, ring_count=16)
        trk.apply(ob)
        ball_data[side] = (tl, tld)

    # ---------------- cards ----------------
    m_card = mat_graded("Card", rough=0.35, color_socket_fn=tex_card())
    W2, H2 = 0.10, 0.145      # giant playing cards so they read on a phone
    card_me_obj = mesh_obj("CardProto", [(-W2, -H2, 0), (W2, -H2, 0), (W2, H2, 0), (-W2, H2, 0)],
                           [(0, 1, 2, 3)], m_card, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    card_me = card_me_obj.data
    bpy.data.objects.remove(card_me_obj)
    ctracks, clandings = sim_cards(rng, 12.6, 20.0)
    for i, trk in enumerate(ctracks):
        ob = link(bpy.data.objects.new("Card%02d" % i, card_me))
        trk.apply(ob)

    # ---------------- pendulum ----------------
    m_brass = mat_graded("Brass", color=(0.85, 0.62, 0.28), rough=0.25, metal=1.0)
    m_string = mat_graded("String", color=(0.08, 0.08, 0.08), rough=0.8)
    Lp = CONFIG["PEND_L"]
    pv = link(bpy.data.objects.new("PendPivot", None))
    arm = link(bpy.data.objects.new("PendArm", None))
    parent(arm, pv)
    stem = prim("cylinder", "PendStem", m_metal, vertices=16, radius=0.025, depth=4.0, location=(0, 0, 2.0))
    parent(stem, pv)
    hub = prim("uv_sphere", "PendHub", m_brass, radius=0.045)
    parent(hub, pv)
    string = prim("cylinder", "PendString", m_string, vertices=8, radius=0.006, depth=Lp,
                  location=(0, 0, -Lp / 2))
    parent(string, arm)
    bob = prim("uv_sphere", "PendBob", m_brass, radius=0.12, segments=32, ring_count=16,
               location=(0, 0, -Lp))
    parent(bob, arm)
    P = Vector(CONFIG["PEND_PIVOT"])
    key_scalar(pv, "location", [(18.6, tuple(P + Vector((0, 0, 4.5)))), (19.7, tuple(P))])
    pfr, pth, crossings = sim_pendulum(18.0, CONFIG["DURATION"])
    bake_prop(arm, "rotation_euler", pfr, [(0.0, -th, 0.0) for th in pth])

    # ---------------- eggs ----------------
    m_egg = mat_graded("Egg", color=(0.93, 0.86, 0.74), rough=0.35)
    m_yolk = mat_graded("Yolk", color=(1.0, 0.62, 0.05), rough=0.15, coat=0.6)
    egg_specs = [(-0.5, -0.33, 28.0, 2.7), (-0.82, -0.36, 28.6, 2.55), (-1.08, -0.31, 29.2, 2.4)]
    eggs = sim_eggs(egg_specs, 26.6, CONFIG["DURATION"])
    egg_res = []
    for i, (trk, splat_t, (ex, ey)) in enumerate(eggs):
        ob = prim("uv_sphere", "Egg%d" % i, m_egg, radius=1.0, segments=24, ring_count=12)
        ob.data.transform(Matrix.Diagonal((0.09, 0.09, 0.115, 1.0)))
        trk.apply(ob)
        if splat_t:
            yk = prim("uv_sphere", "Yolk%d" % i, m_yolk, radius=1.0, segments=24, ring_count=12,
                      location=(ex, ey, TH + 0.036))
            yk.scale = TINY
            key_scalar(yk, "scale", [(splat_t - 0.01, TINY), (splat_t + 0.05, (0.085, 0.085, 0.04))])
        egg_res.append((splat_t, egg_specs[i][2]))

    # ---------------- text overlay ----------------
    STATE.clear()
    STATE["ball"] = ball_data
    STATE["cross"] = crossings
    build_text(sc, cam, ball_data, crossings)

    # ---------------- render settings ----------------
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "None"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0

    info = {"balls": ball_data, "crossings": crossings, "cards": clandings,
            "eggs": egg_res, "impacts": impacts, "build_s": time.time() - t_build}
    return sc, info


# ----------------------------------------------------------------------------
# Text (Blender text objects parented to the camera, dark plates behind)
# ----------------------------------------------------------------------------
TEXT_D = 2.0


def build_text(sc, cam, ball_data, crossings):
    cd = cam.data
    h = TEXT_D * cd.sensor_height / cd.lens
    w = h * CONFIG["RESOLUTION"][0] / CONFIG["RESOLUTION"][1]
    m_txt = mat_emit("TextWhite", (1, 1, 1), 1.6)
    m_txt_moon = mat_emit("TextMoon", (0.75, 0.86, 1.0), 1.6)
    m_txt_jup = mat_emit("TextJupiter", (1.0, 0.68, 0.32), 1.8)
    m_plate = mat_emit("Plate", (0.0, 0.0, 0.0), 1.0, alpha=0.86)
    texts = {}

    def make(name, body, u, v, size, mat=None, max_w=0.9, show=None, plate=True,
             plate_chars=None):
        cu = bpy.data.curves.new(name, "FONT")
        cu.body = body if plate_chars is None else plate_chars
        cu.size = size
        cu.align_x = "CENTER"; cu.align_y = "CENTER"
        cu.space_line = 1.05
        try:
            cu.extrude = 0.0
        except Exception:
            pass
        ob = link(bpy.data.objects.new(name, cu))
        cu.materials.append(mat or m_txt)
        parent(ob, cam)
        ob.location = (u * w, v * h, -TEXT_D)
        bpy.context.view_layer.update()
        dw, dh = ob.dimensions.x, ob.dimensions.y
        s = min(1.0, max_w * w / max(dw, 1e-6))
        if plate:
            pw, ph = dw + size * 0.9, dh + size * 0.7
            pl = mesh_obj(name + "_plate", [(-pw / 2, -ph / 2, 0), (pw / 2, -ph / 2, 0),
                                            (pw / 2, ph / 2, 0), (-pw / 2, ph / 2, 0)],
                          [(0, 1, 2, 3)], m_plate)
            parent(pl, ob)
            pl.location = (0, size * 0.08, -0.002)
            for o in (pl,):
                try:
                    o.visible_shadow = False
                except Exception:
                    pass
        cu.body = body
        try:
            ob.visible_shadow = False
        except Exception:
            pass
        ob.scale = (s, s, s)
        if show:
            t_in, t_out = show
            keys = []
            if t_in > 0:
                keys += [(t_in - 0.12, (0.0001,) * 3), (t_in, (s, s, s))]
            else:
                keys += [(0.0, (s, s, s))]
            if t_out < CONFIG["DURATION"]:
                keys += [(t_out - 0.1, (s, s, s)), (t_out, (0.0001,) * 3)]
            key_scalar(ob, "scale", keys)
        return ob

    D = CONFIG["DURATION"]
    L_, R_ = CONFIG["LEFT"], CONFIG["RIGHT"]
    lab_l = make("LabelLeft", "%s\n%.2f m/s²" % (L_["name"], L_["g"]), -0.25, 0.41, 0.085,
                 m_txt_moon, max_w=0.44)
    lab_r = make("LabelRight", "%s\n%.2f m/s²" % (R_["name"], R_["g"]), 0.25, 0.41, 0.085,
                 m_txt_jup, max_w=0.44)
    # Jupiter eats the frame: Moon label falls off, Jupiter label takes centre
    t0, t1 = CONFIG["SEAM_SLIDE"]
    key_scalar(lab_l, "location", [(t0 + 0.35, tuple(lab_l.location)),
                                   (t0 + 0.75, (lab_l.location.x, -0.7 * h, -TEXT_D))])
    key_scalar(lab_r, "location", [(t0 + 0.9, tuple(lab_r.location)),
                                   (t1, (0.0, lab_r.location.y, -TEXT_D))])

    cap = 0.255
    make("Hook", "LEFT: %s · RIGHT: %s" % (L_["name"], R_["name"]), 0, cap, 0.075, show=(0.0, 3.0))
    make("Cap_water", "Watch the water…", 0, cap, 0.07, show=(3.0, 5.2))
    make("Cap_ball", "Same push. Off a 1 m table.", 0, cap, 0.065, show=(5.2, 9.6))
    tm, tj = math.sqrt(2 / L_["g"]), math.sqrt(2 / R_["g"])
    make("Cap_ball2", "%.2f s vs %.2f s  →  %.0f× slower" % (tm, tj, tm / tj), 0, cap, 0.065,
         show=(9.6, 12.0))
    make("Cap_cards", "Throw a deck of cards", 0, cap, 0.07, show=(12.0, 15.5))
    make("Cap_cards2", "Moon: flutter · Jupiter: thud", 0, cap, 0.065, show=(15.5, 19.4))
    make("Cap_pend", "One pendulum. Two gravities.", 0, cap, 0.065, show=(19.4, 27.4))
    make("Cap_eggs", "Toss a few eggs on the Moon side…", 0, cap, 0.06, show=(27.4, 30.2))
    make("Cap_seam", "Uh oh. The seam is moving.", 0, cap, 0.065, show=(30.2, 31.9))
    make("Cap_win", "JUPITER WINS", 0, cap, 0.1, m_txt_jup, show=(31.9, 33.2))
    make("EndText", "Which side would\nyou live on? ↓", 0, 0.12, 0.11, show=(33.2, D + 1))

    # live timers ---------------------------------------------------------
    tlL, tdL = ball_data["L"]
    tlR, tdR = ball_data["R"]

    def fall_timer(name, tl, td):
        def fn(t):
            if t < tl:
                v = 0.0
            elif t < td:
                v = t - tl
            else:
                v = td - tl
            return "%s fall\n%.2f s" % (name, v)
        return fn
    texts["TimerBallL"] = fall_timer(L_["name"], tlL, tdL)
    texts["TimerBallR"] = fall_timer(R_["name"], tlR, tdR)
    make("TimerBallL", texts["TimerBallL"](0), -0.25, -0.405, 0.07, m_txt_moon, max_w=0.44,
         show=(6.0, 12.0), plate_chars="JUPITER fall\n0.00 s")
    make("TimerBallR", texts["TimerBallR"](0), 0.25, -0.405, 0.07, m_txt_jup, max_w=0.44,
         show=(6.0, 12.0), plate_chars="JUPITER fall\n0.00 s")

    rel = CONFIG["PEND_RELEASE"]
    cr = [c for c in crossings if c[0] < CONFIG["SEAM_SLIDE"][0]]

    def pend_timer(t):
        # time spent on each side during the latest (or current) half swing
        left_last = right_last = None
        left_cur = right_cur = None
        prev_t, side = rel, "L"
        first = True
        for (tc, dirn) in cr:
            if tc > t:
                break
            dur = tc - prev_t
            if side == "L":
                if not first:
                    left_last = dur
            else:
                right_last = dur
            first = False if side == "L" else first
            prev_t, side = tc, ("R" if dirn > 0 else "L")
        cur = max(0.0, t - prev_t)
        if t >= CONFIG["SEAM_SLIDE"][0]:
            cur = None
        lv = cur if (side == "L" and cur is not None) else left_last
        rv = cur if (side == "R" and cur is not None) else right_last
        ls = "%.2f s" % lv if lv is not None else "--.-- s"
        rs = "%.2f s" % rv if rv is not None else "--.-- s"
        line3 = ""
        if left_last is not None and right_last is not None:
            per = left_last + right_last
            line3 = "\nfull swing %.2f s = average of a\nMoon & a Jupiter swing" % per
        return "◀ MOON half %s · JUPITER half %s ▶%s" % (ls, rs, line3)
    texts["TimerPend"] = pend_timer
    make("TimerPend", pend_timer(rel), 0, -0.405, 0.05, max_w=0.94, show=(19.8, 30.2),
         plate_chars="◀ MOON half 0.00 s · JUPITER half 0.00 s ▶\nfull swing 0.00 s = average of a\nMoon & a Jupiter swing")
    STATE["texts"] = texts
    register_handler()


@persistent
def split_world_update(scene, depsgraph=None):
    texts = STATE.get("texts")
    if not texts:
        return
    t = (scene.frame_current - 1) / scene.render.fps
    for name, fn in texts.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        body = fn(t)
        if ob.data.body != body:
            ob.data.body = body


def register_handler():
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "split_world_update":
            bpy.app.handlers.frame_change_pre.remove(h)
    bpy.app.handlers.frame_change_pre.append(split_world_update)


# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------
def verify(info):
    print("\n========== SPLIT WORLD verification ==========")
    ok = True
    L_, R_ = CONFIG["LEFT"], CONFIG["RIGHT"]
    for side, pl in (("L", L_), ("R", R_)):
        tl, td = info["balls"][side]
        meas = td - tl
        exp = math.sqrt(2 * TH / pl["g"])
        good = abs(meas - exp) < 0.005
        ok &= good
        print("1 m fall off table edge, %-8s measured %.3f s  analytic %.3f s  %s"
              % (pl["name"], meas, exp, "OK" if good else "FAIL"))
    tm = info["balls"]["L"][1] - info["balls"]["L"][0]
    tj = info["balls"]["R"][1] - info["balls"]["R"][0]
    print("ratio Moon/Jupiter fall time: %.2fx (sqrt(gJ/gM) = %.2fx)" % (tm / tj, math.sqrt(R_["g"] / L_["g"])))

    # pendulum: split crossings into half swings (before the seam moves)
    Lp = CONFIG["PEND_L"]
    cr = [c for c in info["crossings"] if c[0] < CONFIG["SEAM_SLIDE"][0]]
    lefts, rights = [], []
    for (ta, da), (tb, db) in zip(cr, cr[1:]):
        (rights if da > 0 else lefts).append(tb - ta)
    thL = math.radians(abs(CONFIG["PEND_THETA0_DEG"]))
    thR = math.acos(1 - (L_["g"] / R_["g"]) * (1 - math.cos(thL)))
    exL = exact_period(L_["g"], Lp, thL) / 2
    exR = exact_period(R_["g"], Lp, thR) / 2
    smL = math.pi * math.sqrt(Lp / L_["g"])
    smR = math.pi * math.sqrt(Lp / R_["g"])
    print("pendulum L=%.2f m, amplitude Moon side %.1f deg, Jupiter side %.1f deg"
          % (Lp, math.degrees(thL), math.degrees(thR)))
    print("  half-swings on Moon side    :", ", ".join("%.3f" % x for x in lefts),
          " exact %.3f  small-angle %.3f" % (exL, smL))
    print("  half-swings on Jupiter side :", ", ".join("%.3f" % x for x in rights),
          " exact %.3f  small-angle %.3f" % (exR, smR))
    assert lefts and rights, "pendulum did not complete a half swing on each side"
    gL = all(abs(x - exL) / exL < 0.005 for x in lefts)
    gR = all(abs(x - exR) / exR < 0.005 for x in rights)
    ok &= gL and gR
    per = lefts[0] + rights[0]
    avg_exact = (2 * exL + 2 * exR) / 2
    avg_small = (2 * smL + 2 * smR) / 2
    rule_exact = abs(per - avg_exact) / avg_exact < 0.005
    rule_small = abs(per - avg_small) / avg_small < 0.04
    ok &= rule_exact and rule_small
    print("  full split period %.3f s ; average of full Moon (%.3f) & Jupiter (%.3f) periods = %.3f s  %s"
          % (per, 2 * exL, 2 * exR, avg_exact, "OK" if rule_exact else "FAIL"))
    print("  small-angle rule: (2pi sqrt(L/gM) + 2pi sqrt(L/gJ))/2 = %.3f s (amplitude correction %.1f%%) %s"
          % (avg_small, 100 * (per / avg_small - 1), "OK" if rule_small else "FAIL"))
    # cards & eggs (informative)
    cl = [c for c in info["cards"] if c[1] is not None]
    airL = [a for x, a in cl if x < 0]
    airR = [a for x, a in cl if x >= 0]
    if airL and airR:
        print("cards: mean air time Moon side %.2f s (%d cards), Jupiter side %.2f s (%d cards)"
              % (sum(airL) / len(airL), len(airL), sum(airR) / len(airR), len(airR)))
    for i, (st, tt) in enumerate(info["eggs"]):
        print("egg %d tossed %.1f s -> %s" % (i, tt, ("SPLAT at %.2f s" % st) if st else "survived"))
    print("water impacts: Moon side %d, Jupiter side %d" % (len(info["impacts"]["L"]), len(info["impacts"]["R"])))
    print("bake+build time: %.1f s" % info["build_s"])
    print("RESULT:", "ALL CHECKS PASSED" if ok else "CHECKS FAILED")
    print("==============================================\n")
    assert ok, "Split World verification failed"


# ----------------------------------------------------------------------------
# Render setup
# ----------------------------------------------------------------------------
def set_engine(sc, name, samples):
    name = (name or "EEVEE").upper()
    if name == "EEVEE":
        for eid in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):   # 4.2-4.x vs 5.x
            try:
                sc.render.engine = eid
                break
            except Exception:
                continue
        ee = sc.eevee
        for attr, val in (("taa_render_samples", samples), ("use_raytracing", True),
                          ("use_shadows", True), ("use_gtao", True)):
            try:
                setattr(ee, attr, val)
            except Exception:
                pass
    elif name == "CYCLES":
        sc.render.engine = "CYCLES"
        sc.cycles.samples = samples
        sc.cycles.device = "CPU"
        try:
            sc.cycles.use_denoising = True
        except Exception:
            pass
    else:
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "MATERIAL"


def out_dir(args):
    d = args["out"] or CONFIG["OUTPUT_DIR"]
    if not os.path.isabs(d):
        base = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd()
        d = os.path.join(base, d)
    os.makedirs(d, exist_ok=True)
    return d


def setup_output(sc, path_noext):
    try:
        try:
            sc.render.image_settings.media_type = "VIDEO"    # Blender 5.x
        except Exception:
            pass
        sc.render.image_settings.file_format = "FFMPEG"
        ff = sc.render.ffmpeg
        ff.format = "MPEG4"; ff.codec = "H264"
        ff.constant_rate_factor = "HIGH"
        ff.audio_codec = "NONE"
        sc.render.filepath = path_noext + ".mp4"
    except Exception as e:
        print("FFMPEG unavailable (%s) - writing PNG frames" % e)
        try:
            sc.render.image_settings.media_type = "IMAGE"
        except Exception:
            pass
        sc.render.image_settings.file_format = "PNG"
        sc.render.filepath = path_noext + "_"


def main():
    args = parse_args()
    sc, info = build()
    verify(info)
    mode = args["action"] or CONFIG["MODE"]
    q = CONFIG["RENDER"] if mode == "RENDER" else CONFIG["PREVIEW"]
    set_engine(sc, args["engine"] or CONFIG["ENGINE"], args["samples"] or q["samples"])
    sc.render.resolution_percentage = args["res_pct"] or q["res_pct"]
    sc.frame_set(1)
    if args["frames"]:
        d = out_dir(args)
        try:
            sc.render.image_settings.media_type = "IMAGE"
        except Exception:
            pass
        sc.render.image_settings.file_format = "PNG"
        for f in args["frames"]:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(d, "frame_%04d.png" % f)
            t = time.time()
            bpy.ops.render.render(write_still=True)
            print("rendered frame %d in %.1f s -> %s" % (f, time.time() - t, sc.render.filepath))
        return
    if args["action"]:
        if args["range"]:
            sc.frame_start, sc.frame_end = args["range"]
        d = out_dir(args)
        setup_output(sc, os.path.join(d, "split_world_" + mode.lower()))
        t = time.time()
        bpy.ops.render.render(animation=True)
        print("render finished in %.1f min -> %s" % ((time.time() - t) / 60, sc.render.filepath))
    else:
        print("Scene built. Press Render > Render Animation, or run headless with -- --render")


main()
