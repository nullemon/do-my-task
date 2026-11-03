"""
THE MACHINE THAT ONLY WORKS ON ONE PLANET
=========================================
A compact Rube Goldberg machine, built identically on every planet:

  spring plunger -> ball flies over a pit -> lands in a funnel basket -> drops
  down a chute + quarter-pipe -> knocks over 8 dominoes -> last domino pushes a
  golf ball into a cup -> lamp lights, flag rises, confetti = SUCCESS.

Why only one planet works: the plunger is a fixed-stroke motor (same launch
speed everywhere), so how far the ball flies over the pit depends on gravity.
The launch speed is tuned so the ball lands in the basket only at
TARGET_PLANET's gravity (default Mars).  Weaker gravity -> it sails over the
basket into the void; stronger -> it drops into the pit (Earth: smacks the
basket wall, so close!).  On the Sun the cantilevered launch ledge is held by a
breakable joint rated for ~90 m/s^2 and it snaps instantly.

Run inside Blender (Scripting tab -> Run) or headless:
    blender -b -P rube_goldberg_planets.py -- --preview   # low-res Cycles stills
    blender -b -P rube_goldberg_planets.py -- --render    # full animation per planet
One scene per planet (e.g. "06_Mars"); switch scenes and press play.
"""

import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Euler

# =============================================================================
# CONFIG
# =============================================================================
IDEA = "rube_goldberg_one_planet"
# Video order: the success planet goes LAST for the payoff.
PLANETS = ["Moon", "Pluto", "Jupiter", "Sun", "Earth", "Mars"]
TARGET_PLANET = "Mars"          # the one planet where the machine works
FPS = 30
SECONDS = 7.5
RESOLUTION = (1080, 1920)       # vertical 9:16
ENGINE = "EEVEE"                # "EEVEE" or "CYCLES"
CYCLES_SAMPLES = 128
EEVEE_SAMPLES = 64
RENDER = False                  # True = render all planets when run from the UI
PREVIEW = False                 # True = quick Cycles stills (also: -- --preview)
PREVIEW_RES = (270, 480)
PREVIEW_SAMPLES = 12
OUTPUT_DIR = "//renders/" + IDEA + "/"   # relative to .blend (or script dir when unsaved)
HOOK_TEXT = "Only ONE planet makes\nthis work. Guess which?"
SHOW_HOOK = True
LAUNCH_SPEED_TRIM = 1.0         # fine-tune multiplier on the plunger speed
PLUNGER_FIRE_TIME = 0.5         # seconds into the clip
SUBSTEPS = 40                   # rigid-body substeps per frame (1200 Hz at 30 fps)
SOLVER_ITERATIONS = 40
LEDGE_RATED_G = 90.0            # launch-ledge joint breaks above this gravity (m/s^2)
PREFIX = "RG_"                  # everything this script makes starts with this

GRAVITY = {"Pluto": 0.62, "Moon": 1.62, "Mercury": 3.70, "Mars": 3.71,
           "Venus": 8.87, "Earth": 9.81, "Uranus": 8.69, "Neptune": 11.15,
           "Saturn": 10.44, "Jupiter": 24.79, "Sun": 274.0}

# ground colour, sky colour, sky strength, ground emission strength
LOOKS = {
    "Pluto":   ((0.80, 0.74, 0.66), (0.010, 0.012, 0.030), 1.0, 0.0),
    "Moon":    ((0.42, 0.42, 0.42), (0.004, 0.004, 0.006), 1.0, 0.0),
    "Mercury": ((0.45, 0.40, 0.36), (0.005, 0.005, 0.008), 1.0, 0.0),
    "Mars":    ((0.55, 0.20, 0.08), (0.80, 0.55, 0.30), 0.9, 0.0),
    "Venus":   ((0.60, 0.48, 0.20), (0.90, 0.75, 0.35), 0.9, 0.0),
    "Earth":   ((0.20, 0.42, 0.14), (0.42, 0.65, 0.95), 1.0, 0.0),
    "Uranus":  ((0.50, 0.75, 0.78), (0.55, 0.80, 0.85), 0.9, 0.0),
    "Neptune": ((0.20, 0.30, 0.70), (0.25, 0.40, 0.85), 0.9, 0.0),
    "Saturn":  ((0.75, 0.65, 0.45), (0.85, 0.75, 0.55), 0.9, 0.0),
    "Jupiter": ((0.62, 0.42, 0.25), (0.85, 0.58, 0.35), 0.9, 0.0),
    "Sun":     ((1.00, 0.45, 0.05), (1.00, 0.55, 0.10), 1.2, 3.0),
}

# =============================================================================
# MACHINE GEOMETRY (metres, side view: x right, z up, camera looks along +y)
# =============================================================================
R_BALL = 0.065                  # launched ball
M_BALL = 0.15
LEDGE_X = (-1.35, -0.95)        # cantilevered launch ledge
LEDGE_TOP = 3.35
BALL_START_X = -1.20
PLUNGER_STROKE = 0.20
TOWER_X = (-1.75, -1.35)
PIT_FLOOR_TOP = 1.00
STAND_X = (0.58, 0.66)          # pit right wall == basket stand
RIM_Z = 1.95                    # basket rim height
BASKET_RIGHT_X = (1.26, 1.32)
BASKET_CENTER_X = 0.975         # where the ball should cross rim height
HOLE_X = (0.87, 1.03)           # funnel exit / chute
CHUTE_BOTTOM = 0.70
QP_CENTER = (0.55, 0.70)        # quarter-pipe centre
QP_R = HOLE_X[1] - QP_CENTER[0]
DECK_TOP = QP_CENTER[1] - QP_R  # small deck the ball rolls along
DECK_X = (0.36, QP_CENTER[0])
DOM_H, DOM_T, DOM_W = 0.38, 0.055, 0.18
DOM_X0, DOM_STEP, DOM_N = 0.30, 0.15, 8
PED_X = (-1.00, -0.86)          # golf-ball pedestal
PED_TOP = 0.20
R_GOLF = 0.045
CUP_CX, CUP_R_IN, CUP_WALL, CUP_H = -1.175, 0.155, 0.02, 0.14
POLE_X = 1.50
CAM_Z = 2.95


def argv_flags():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return set(a)


# =============================================================================
# helpers
# =============================================================================
def mat(name, color, rough=0.5, metal=0.0, emit=0.0, emit_color=None):
    name = PREFIX + name
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    if p is None:
        nt.nodes.clear()
        p = nt.nodes.new("ShaderNodeBsdfPrincipled")
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(p.outputs[0], o.inputs[0])
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    ec = p.inputs.get("Emission Color") or p.inputs.get("Emission")
    ec.default_value = (*(emit_color or color), 1)
    p.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*color, 1)
    return m


def link(obj, coll):
    coll.objects.link(obj)
    return obj


def box(name, coll, x0, x1, z0, z1, y0=-0.15, y1=0.15, material=None, bevel=0.012):
    me = bpy.data.meshes.new(PREFIX + name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= (x1 - x0)
        v.co.y *= (y1 - y0)
        v.co.z *= (z1 - z0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(PREFIX + name, me)
    ob.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    if material:
        me.materials.append(material)
    if bevel:
        md = ob.modifiers.new("bevel", "BEVEL")
        md.width = bevel
        md.segments = 2
        md.limit_method = 'ANGLE'
    for p in me.polygons:
        p.use_smooth = True
    return link(ob, coll)


def plate(name, coll, p0, p1, thick=0.03, y0=-0.16, y1=0.16, material=None):
    """thin slab from point p0 to p1 in the xz plane (its top face on the line)."""
    (xa, za), (xb, zb) = p0, p1
    L = math.hypot(xb - xa, zb - za)
    ang = math.atan2(zb - za, xb - xa)
    ob = box(name, coll, -L / 2, L / 2, -thick, 0.0, y0, y1, material)
    ob.location = ((xa + xb) / 2, (y0 + y1) / 2, (za + zb) / 2)
    ob.rotation_euler = (0, -ang, 0)
    return ob


def sphere(name, coll, r, loc, material=None, seg=32):
    me = bpy.data.meshes.new(PREFIX + name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(PREFIX + name, me)
    ob.location = loc
    if material:
        me.materials.append(material)
    return link(ob, coll)


def cylinder(name, coll, r, depth, loc, material=None, rot=(0, 0, 0), seg=32):
    me = bpy.data.meshes.new(PREFIX + name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(PREFIX + name, me)
    ob.location = loc
    ob.rotation_euler = rot
    if material:
        me.materials.append(material)
    return link(ob, coll)


def quarter_pipe(name, coll, material):
    """inner surface radius QP_R around QP_CENTER, from angle 0 down to -90 deg."""
    cx, cz = QP_CENTER
    me = bpy.data.meshes.new(PREFIX + name)
    bm = bmesh.new()
    n = 24
    t = 0.04
    rows = []
    for i in range(n + 1):
        a = -math.pi / 2 * i / n
        ring = []
        for r in (QP_R, QP_R + t):
            for y in (-0.17, 0.17):
                ring.append(bm.verts.new((cx + r * math.cos(a), y, cz + r * math.sin(a))))
        rows.append(ring)
    for i in range(n):
        a, b = rows[i], rows[i + 1]
        # ring order: (in,-y) (in,+y) (out,-y) (out,+y)
        bm.faces.new((a[0], a[1], b[1], b[0]))   # inner surface
        bm.faces.new((a[2], b[2], b[3], a[3]))   # outer
        bm.faces.new((a[0], b[0], b[2], a[2]))   # side -y
        bm.faces.new((a[1], a[3], b[3], b[1]))   # side +y
    for ring, flip in ((rows[0], False), (rows[-1], True)):
        f = bm.faces.new((ring[0], ring[2], ring[3], ring[1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(PREFIX + name, me)
    me.materials.append(material)
    return link(ob, coll)


def cup_mesh(name, coll, material):
    me = bpy.data.meshes.new(PREFIX + name)
    bm = bmesh.new()
    seg = 32
    ro, ri = CUP_R_IN + CUP_WALL, CUP_R_IN
    def ring(r, z):
        return [bm.verts.new((r * math.cos(2 * math.pi * i / seg),
                              r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)]
    ob_, ot_ = ring(ro, 0.0), ring(ro, CUP_H)
    it_, ib_ = ring(ri, CUP_H), ring(ri, 0.025)
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((ob_[i], ob_[j], ot_[j], ot_[i]))
        bm.faces.new((ot_[i], ot_[j], it_[j], it_[i]))
        bm.faces.new((it_[i], it_[j], ib_[j], ib_[i]))
    bm.faces.new(list(reversed(ob_)))
    bm.faces.new(ib_)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(PREFIX + name, me)
    ob.location = (CUP_CX, 0, 0)
    me.materials.append(material)
    return link(ob, coll)


def text(name, coll, body, size, loc, material, extrude=0.01, align="CENTER"):
    cu = bpy.data.curves.new(PREFIX + name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.space_line = 0.95
    ob = bpy.data.objects.new(PREFIX + name, cu)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    cu.materials.append(material)
    return link(ob, coll)


def outlined_text(name, coll, body, size, loc, mat_front, mat_back, parent=None):
    a = text(name, coll, body, size, loc, mat_front)
    b = text(name + "_shadow", coll, body, size,
             (loc[0] + size * 0.05, loc[1] + 0.02, loc[2] - size * 0.06), mat_back)
    for o in (a, b):
        if parent:
            o.parent = parent
    return a, b


def add_rigid(scene, ob, kind="ACTIVE", shape="BOX", mass=1.0, friction=0.5,
              bounce=0.1, kinematic=False, damping=(0.01, 0.05)):
    with bpy.context.temp_override(scene=scene, object=ob, active_object=ob,
                                   selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.rigidbody.object_add(type=kind)
    rb = ob.rigid_body
    rb.collision_shape = shape
    rb.mass = mass
    rb.friction = friction
    rb.restitution = bounce
    rb.kinematic = kinematic
    rb.use_deactivation = False
    rb.linear_damping, rb.angular_damping = damping
    if shape in ("MESH", "CONVEX_HULL"):
        rb.use_margin = True
        rb.collision_margin = 0.002
    return rb


def key_hide(ob, frame_show):
    """scale 0 until frame_show, then pop."""
    s = ob.scale.copy()
    ob.scale = (0, 0, 0)
    ob.keyframe_insert("scale", frame=frame_show - 1)
    ob.scale = s * 1.25
    ob.keyframe_insert("scale", frame=frame_show + 3)
    ob.scale = s
    ob.keyframe_insert("scale", frame=frame_show + 6)


def set_interp(ob, kind="LINEAR"):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    try:
        curves = ad.action.fcurves
    except AttributeError:          # Blender 5 layered actions
        curves = []
        for layer in ad.action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves.extend(bag.fcurves)
    for fc in curves:
        for k in fc.keyframe_points:
            k.interpolation = kind


# =============================================================================
# cleanup (idempotent re-run)
# =============================================================================
def cleanup():
    for sc in list(bpy.data.scenes):
        if sc.get("rg_made"):
            if len(bpy.data.scenes) == 1:
                bpy.data.scenes.new("Scene")
            bpy.data.scenes.remove(sc)
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.cameras, bpy.data.lights, bpy.data.collections, bpy.data.worlds,
                 bpy.data.actions):
        for d in list(coll):
            if d.name.startswith(PREFIX) and d.users == 0 or (
                    d.name.startswith(PREFIX) and coll in (bpy.data.objects, bpy.data.collections)):
                try:
                    coll.remove(d)
                except Exception:
                    pass


# =============================================================================
# launch speed: lands at basket centre on TARGET_PLANET
# =============================================================================
def launch_speed():
    g = GRAVITY[TARGET_PLANET]
    drop = (LEDGE_TOP + R_BALL) - RIM_Z
    t = math.sqrt(2 * drop / g)
    return (BASKET_CENTER_X - LEDGE_X[1]) / t * LAUNCH_SPEED_TRIM


# =============================================================================
# build one planet scene
# =============================================================================
def build_scene(idx, planet):
    g = GRAVITY[planet]
    ground_c, sky_c, sky_s, ground_emit = LOOKS[planet]
    sc = bpy.data.scenes.new(f"{idx:02d}_{planet}")
    sc["rg_made"] = True
    sc["planet"] = planet
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = int(SECONDS * FPS)
    sc.render.resolution_x, sc.render.resolution_y = RESOLUTION
    sc.use_gravity = True
    sc.gravity = (0, 0, -g)

    root = bpy.data.collections.new(PREFIX + sc.name)
    sc.collection.children.link(root)
    P = planet[:3] + "_"

    # --- world
    w = bpy.data.worlds.new(PREFIX + "World_" + planet)
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*sky_c, 1)
    bg.inputs[1].default_value = sky_s
    sc.world = w

    # --- materials
    m_ground = mat(P + "ground", ground_c, rough=0.95, emit=ground_emit,
                   emit_color=(1.0, 0.35, 0.02))
    m_wood = mat("wood", (0.62, 0.40, 0.20), rough=0.6)
    m_dark = mat("frame", (0.10, 0.11, 0.14), rough=0.4, metal=0.3)
    m_steel = mat("steel", (0.75, 0.77, 0.80), rough=0.25, metal=1.0)
    m_red = mat("red", (0.85, 0.08, 0.06), rough=0.3)
    m_yellow = mat("yellow", (1.0, 0.72, 0.05), rough=0.35)
    m_blue = mat("blue", (0.08, 0.35, 0.90), rough=0.3)
    m_teal = mat("teal", (0.05, 0.65, 0.60), rough=0.35)
    m_white = mat("white", (0.95, 0.95, 0.95), rough=0.3)
    m_ball = mat("ball", (0.95, 0.12, 0.45), rough=0.2)
    m_golf = mat("golf", (0.97, 0.97, 0.93), rough=0.35)
    m_dom = [mat("dom_a", (0.98, 0.98, 0.96), rough=0.25),
             mat("dom_b", (0.08, 0.08, 0.09), rough=0.25)]
    m_txt = mat("txt", (1, 1, 1), emit=1.6, emit_color=(1, 1, 1))
    m_txt_back = mat("txt_back", (0, 0, 0), rough=1.0)
    m_hook = mat("hook", (1, 0.85, 0.1), emit=1.8, emit_color=(1, 0.85, 0.1))
    m_ok = mat("ok", (0.1, 0.95, 0.3), emit=2.5, emit_color=(0.1, 0.95, 0.3))
    m_bad = mat("bad", (1.0, 0.12, 0.1), emit=2.5, emit_color=(1.0, 0.12, 0.1))
    m_bulb = mat(P + "bulb", (1.0, 0.9, 0.6), rough=0.1, emit=0.0, emit_color=(1.0, 0.85, 0.4))

    # --- rigid body world
    with bpy.context.temp_override(scene=sc):
        bpy.ops.rigidbody.world_add()
    rbw = sc.rigidbody_world
    rbc = bpy.data.collections.new(PREFIX + "RB_" + planet)
    rbw.collection = rbc
    rbw.substeps_per_frame = SUBSTEPS
    rbw.solver_iterations = SOLVER_ITERATIONS
    rbw.use_split_impulse = False
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = sc.frame_end
    cons_coll = bpy.data.collections.new(PREFIX + "RBC_" + planet)
    root.children.link(cons_coll)
    rbw.constraints = cons_coll

    objs = {}

    def rb(ob, *a, **k):
        add_rigid(sc, ob, *a, **k)
        return ob

    # ground
    gr = box(P + "Ground", root, -40, 40, -0.2, 0.0, -40, 40, m_ground, bevel=0)
    rb(gr, "PASSIVE", friction=0.8)

    # launch tower + ledge + plunger
    tower = rb(box(P + "Tower", root, *TOWER_X, 0.0, LEDGE_TOP, -0.22, 0.22, m_dark), "PASSIVE")
    ledge = rb(box(P + "Ledge", root, *LEDGE_X, LEDGE_TOP - 0.08, LEDGE_TOP, -0.17, 0.17, m_wood),
               "ACTIVE", mass=2.0, friction=0.05)
    objs["ledge"] = ledge
    # breakable fixed joint: impulse per substep for the ledge weight at LEDGE_RATED_G
    joint = bpy.data.objects.new(PREFIX + P + "LedgeJoint", None)
    joint.location = (LEDGE_X[0], 0, LEDGE_TOP - 0.04)
    joint.empty_display_size = 0.1
    cons_coll.objects.link(joint)
    with bpy.context.temp_override(scene=sc, object=joint, active_object=joint,
                                   selected_objects=[joint]):
        bpy.ops.rigidbody.constraint_add(type='FIXED')
    rc = joint.rigid_body_constraint
    rc.object1, rc.object2 = tower, ledge
    rc.use_breaking = True
    rc.breaking_threshold = (2.0 + M_BALL) * LEDGE_RATED_G / (FPS * SUBSTEPS)
    rc.disable_collisions = True

    # plunger (kinematic, fixed stroke & speed = gravity-independent "motor")
    face = BALL_START_X - R_BALL - 0.005
    plunger = box(P + "Plunger", root, face - 0.06, face, LEDGE_TOP + 0.01, LEDGE_TOP + 0.13,
                  -0.10, 0.10, m_red)
    rod = box(P + "PlungerRod", root, TOWER_X[0] - 0.05, face - 0.06, LEDGE_TOP + 0.05,
              LEDGE_TOP + 0.09, -0.025, 0.025, m_steel, bevel=0.005)
    rod.parent = plunger
    rod.location -= plunger.location
    rb(plunger, "PASSIVE", kinematic=True, friction=0.0, bounce=0.0)
    housing = box(P + "Housing", root, TOWER_X[0] + 0.02, TOWER_X[0] + 0.24, LEDGE_TOP,
                  LEDGE_TOP + 0.16, -0.12, 0.12, m_yellow)
    v = launch_speed()
    f_fire = int(PLUNGER_FIRE_TIME * FPS)
    f_stop = f_fire + PLUNGER_STROKE / v * FPS
    plunger.keyframe_insert("location", frame=1)
    plunger.keyframe_insert("location", frame=f_fire)
    plunger.location.x += PLUNGER_STROKE
    plunger.keyframe_insert("location", frame=f_stop)
    plunger.keyframe_insert("location", frame=f_stop + 6)
    plunger.location.x -= PLUNGER_STROKE
    plunger.keyframe_insert("location", frame=f_stop + 30)
    set_interp(plunger, "LINEAR")

    ball = rb(sphere(P + "Ball", root, R_BALL, (BALL_START_X, 0, LEDGE_TOP + R_BALL), m_ball),
              "ACTIVE", "SPHERE", mass=M_BALL, friction=0.05, bounce=0.15, damping=(0.0, 0.05))
    objs["ball"] = ball

    # pit (catches every miss) + basket stand
    rb(box(P + "PitFloor", root, TOWER_X[1], STAND_X[0], PIT_FLOOR_TOP - 0.08, PIT_FLOOR_TOP,
           -0.2, 0.2, m_teal), "PASSIVE", friction=0.6, bounce=0.2)
    rb(box(P + "Stand", root, *STAND_X, PIT_FLOOR_TOP - 0.08, RIM_Z, -0.2, 0.2, m_dark), "PASSIVE")
    for xp in (TOWER_X[1] + 0.06, STAND_X[0] - 0.06):   # decorative posts, behind
        box(P + "Post", root, xp - 0.03, xp + 0.03, 0, PIT_FLOOR_TOP - 0.08, 0.22, 0.3, m_dark)
    # funnel basket
    rb(plate(P + "FunnelL", root, (STAND_X[0], RIM_Z), (HOLE_X[0], CHUTE_BOTTOM + 0.92),
             material=m_yellow), "PASSIVE", friction=0.2, bounce=0.1)
    rb(plate(P + "FunnelR", root, (HOLE_X[1], CHUTE_BOTTOM + 0.92), (BASKET_RIGHT_X[0], RIM_Z),
             material=m_yellow), "PASSIVE", friction=0.2, bounce=0.1)
    rb(box(P + "BasketBack", root, *BASKET_RIGHT_X, CHUTE_BOTTOM + 0.85, RIM_Z + 0.35,
           -0.2, 0.2, m_dark), "PASSIVE", bounce=0.1)
    box(P + "BasketGlass", root, STAND_X[0], BASKET_RIGHT_X[1], RIM_Z - 0.35, RIM_Z,
        0.17, 0.2, m_yellow)          # back panel (decor)
    # chute
    rb(box(P + "ChuteL", root, HOLE_X[0] - 0.03, HOLE_X[0], CHUTE_BOTTOM, CHUTE_BOTTOM + 0.92,
           -0.17, 0.17, m_blue), "PASSIVE", friction=0.1)
    rb(box(P + "ChuteR", root, HOLE_X[1], HOLE_X[1] + 0.03, QP_CENTER[1], CHUTE_BOTTOM + 0.92,
           -0.17, 0.17, m_blue), "PASSIVE", friction=0.1)
    rb(quarter_pipe(P + "QuarterPipe", root, m_blue), "PASSIVE", "MESH", friction=0.1, bounce=0.0)
    rb(box(P + "Deck", root, *DECK_X, 0.0, DECK_TOP, -0.17, 0.17, m_blue), "PASSIVE", friction=0.1)
    box(P + "QPBase", root, DECK_X[1], HOLE_X[1] + 0.04, 0.0, 0.12, -0.17, 0.17, m_dark)

    # dominoes
    doms = []
    for i in range(DOM_N):
        x = DOM_X0 - DOM_STEP * i
        d = box(P + f"Domino{i}", root, x - DOM_T / 2, x + DOM_T / 2, 0.0, DOM_H,
                -DOM_W / 2, DOM_W / 2, m_dom[i % 2], bevel=0.008)
        rb(d, "ACTIVE", mass=0.25, friction=0.5, bounce=0.05)
        doms.append(d)
    objs["doms"] = doms

    # pedestal, golf ball, cup
    rb(box(P + "Pedestal", root, *PED_X, 0.0, PED_TOP, -0.12, 0.12, m_wood), "PASSIVE", friction=0.3)
    golf = rb(sphere(P + "Golf", root, R_GOLF, (PED_X[0] + 0.095, 0, PED_TOP + R_GOLF), m_golf),
              "ACTIVE", "SPHERE", mass=0.05, friction=0.3, bounce=0.2)
    objs["golf"] = golf
    rb(cup_mesh(P + "Cup", root, m_red), "PASSIVE", "MESH", friction=0.5, bounce=0.1)

    # goal lamp + flag (decor, driven by the measured success)
    cylinder(P + "Pole", root, 0.025, 1.62, (POLE_X, 0.1, 0.81), m_steel)
    cylinder(P + "LampBase", root, 0.13, 0.05, (POLE_X, 0.1, 0.025), m_dark)
    bulb = sphere(P + "Bulb", root, 0.12, (POLE_X, 0.1, 1.74), m_bulb)
    cylinder(P + "BulbCap", root, 0.06, 0.06, (POLE_X, 0.1, 1.63), m_dark)
    flag = box(P + "Flag", root, POLE_X + 0.03, POLE_X + 0.33, -0.10, 0.10, 0.09, 0.11,
               mat("flag", (0.1, 0.85, 0.3), emit=0.4), bevel=0)
    flag.location.z = 0.25
    objs.update(bulb=bulb, flag=flag, m_bulb=m_bulb)

    # --- camera & lights
    cam_d = bpy.data.cameras.new(PREFIX + "Cam_" + planet)
    cam_d.sensor_fit = 'VERTICAL'
    cam_d.sensor_height = 24
    view_h = 6.7
    dist = 14.0
    cam_d.lens = 24 * dist / view_h
    cam = bpy.data.objects.new(PREFIX + "Cam_" + planet, cam_d)
    cam.location = (0.0, -dist, CAM_Z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    link(cam, root)
    sc.camera = cam

    key = bpy.data.lights.new(PREFIX + "Key_" + planet, "SUN")
    key.energy = 3.0 if planet != "Sun" else 1.5
    key.angle = math.radians(8)
    kl = bpy.data.objects.new(PREFIX + "Key_" + planet, key)
    kl.rotation_euler = Euler((math.radians(50), math.radians(-25), math.radians(-30)))
    link(kl, root)
    fill = bpy.data.lights.new(PREFIX + "Fill_" + planet, "AREA")
    fill.energy = 900
    fill.size = 6
    fl = bpy.data.objects.new(PREFIX + "Fill_" + planet, fill)
    fl.location = (2.0, -7, 4.0)
    fl.rotation_euler = (math.radians(70), 0, math.radians(15))
    link(fl, root)
    lamp = bpy.data.lights.new(PREFIX + "LampLight_" + planet, "POINT")
    lamp.energy = 0
    lamp.color = (1.0, 0.85, 0.5)
    ll = bpy.data.objects.new(PREFIX + "LampLight_" + planet, lamp)
    ll.location = (POLE_X, -0.2, 1.74)
    link(ll, root)
    objs["lamp"] = lamp

    # --- labels
    TY = -1.0   # text plane (in front of the machine)
    if SHOW_HOOK:
        outlined_text(P + "Hook", root, HOOK_TEXT, 0.25, (0, TY, 5.55), m_hook, m_txt_back)
    outlined_text(P + "Label", root, f"{planet.upper()} · {g:g} m/s²", 0.36, (0, TY, 4.80),
                  m_txt, m_txt_back)

    return sc, objs


# =============================================================================
# simulate, measure
# =============================================================================
def bake(sc):
    sc.rigidbody_world.point_cache.frame_end = sc.frame_end
    ok = False
    try:
        with bpy.context.temp_override(scene=sc, point_cache=sc.rigidbody_world.point_cache):
            bpy.ops.ptcache.free_bake()
            bpy.ops.ptcache.bake(bake=True)
        ok = sc.rigidbody_world.point_cache.is_baked
    except Exception as e:
        print("  (ptcache.bake unavailable here -> stepping frames:", e, ")")
    return ok


def wpos(ob):
    return ob.matrix_world.translation.copy()


def measure(sc, objs):
    """step through the cache; return per-frame samples."""
    ball, golf, ledge, doms = objs["ball"], objs["golf"], objs["ledge"], objs["doms"]
    samples = []
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        last = doms[-1].matrix_world.to_euler()
        tilt = [math.degrees(math.acos(max(-1, min(1, (d.matrix_world.to_3x3() @ Vector((0, 0, 1))).z))))
                for d in doms]
        samples.append(dict(f=f, ball=wpos(ball), golf=wpos(golf), ledge=wpos(ledge), tilt=tilt))
    return samples


def judge(planet, s):
    """success = golf ball resting inside the cup at the end."""
    end = s[-1]
    gp = end["golf"]
    in_cup = (math.hypot(gp.x - CUP_CX, gp.y) < CUP_R_IN and gp.z < CUP_H)
    res = dict(planet=planet, success=in_cup)
    # frame golf ball entered the cup
    res["success_frame"] = next((x["f"] for x in s if math.hypot(x["golf"].x - CUP_CX, x["golf"].y)
                                 < CUP_R_IN and x["golf"].z < CUP_H), None)
    ledge_drop = s[0]["ledge"].z - end["ledge"].z
    max_x = max(x["ball"].x for x in s)
    # where the ball first crossed rim height (or the lowest point it reached if never)
    cross = next((x for x in s if x["ball"].z < RIM_Z), None)
    in_basket_f = next((x["f"] for x in s if STAND_X[1] < x["ball"].x < BASKET_RIGHT_X[0]
                        and x["ball"].z < RIM_Z - 0.1), None)
    doms_down = sum(1 for t in end["tilt"] if t > 45)
    res.update(ledge_drop=ledge_drop, max_x=max_x, cross_x=cross["ball"].x if cross else None,
               doms_down=doms_down, golf_end=tuple(round(c, 3) for c in gp))
    # landing point in the pit = first frame the ball is near the pit floor
    pit = next((x for x in s if x["ball"].z < PIT_FLOOR_TOP + R_BALL + 0.03), None)
    res["pit_x"] = pit["ball"].x if pit else None
    res["fly_frame"] = next((x["f"] for x in s if x["ball"].x > 0.45), s[0]["f"])
    if in_cup:
        res["reason"], res["short"] = "ball in cup - lamp ON", "MACHINE COMPLETE!"
        res["key_frame"] = res["success_frame"]
    elif ledge_drop > 0.3:
        res["reason"], res["short"] = "launch ledge snapped under its own weight", "COLLAPSED"
        res["key_frame"] = 1 + int(0.35 * FPS)
    elif max_x > BASKET_RIGHT_X[1] + 0.05:
        res["reason"], res["short"] = f"flew over the basket (crossed rim height at x={res['cross_x']:.2f} m)", "FLEW OVER"
        res["key_frame"] = next((x["f"] for x in s if x["ball"].x > 0.3), s[-1]["f"])
    elif res["pit_x"] is not None and in_basket_f is None:
        gap = STAND_X[0] - (res["pit_x"] + R_BALL)
        if gap < 0.03:
            res["reason"], res["short"] = "smacked the outside of the basket wall", "SO CLOSE..."
        elif gap < 0.25:
            res["reason"], res["short"] = f"fell {gap*100:.0f} cm short of the basket wall", "SO CLOSE..."
        else:
            res["reason"], res["short"] = f"barely launched, dropped in the pit (x={res['pit_x']:.2f} m)", "TOO HEAVY"
        res["key_frame"] = pit["f"]
    else:
        res["reason"], res["short"] = f"machine stalled ({doms_down}/{DOM_N} dominoes down)", "STALLED"
        res["key_frame"] = s[-1]["f"] - 20
    return res


# =============================================================================
# outcome-driven dressing: stamp, lamp, flag, confetti
# =============================================================================
def dress(sc, objs, res):
    root = bpy.data.collections[PREFIX + sc.name]
    P = res["planet"][:3] + "_"
    end = sc.frame_end
    if res["success"]:
        f0 = res["success_frame"] + 2
        stamp_f = f0 + 8
    else:
        stamp_f = min(res["key_frame"] + 14, end - 30)
    stamp_f = max(stamp_f, 20)
    res["stamp_frame"] = stamp_f
    ok = res["success"]
    m = bpy.data.materials[PREFIX + ("ok" if ok else "bad")]
    m_back = bpy.data.materials[PREFIX + "txt_back"]
    m_txt = bpy.data.materials[PREFIX + "txt"]
    pivot = bpy.data.objects.new(PREFIX + P + "Stamp", None)
    pivot.location = (0, -1.2, 4.05)
    link(pivot, root)
    # check / cross icon from bars
    if ok:
        bars = [((-0.06, -0.0), 0.16, -45), ((0.10, 0.06), 0.30, 55)]
    else:
        bars = [((0, 0), 0.32, 45), ((0, 0), 0.32, -45)]
    for i, ((bx, bz), L, ang) in enumerate(bars):
        for back in (True, False):
            o = box(P + f"Mark{i}{'b' if back else ''}", root, -L / 2, L / 2, -0.035, 0.035,
                    -0.01, 0.01, m_back if back else m, bevel=0.01)
            o.parent = pivot
            o.location = (-0.80 + bx + (0.015 if back else 0), 0.02 if back else 0,
                          bz - (0.02 if back else 0))
            o.rotation_euler = (0, math.radians(-ang), 0)
            if not ok:
                o.location.x = -0.80 + bx + (0.015 if back else 0)
    outlined_text(P + "StampTxt", root, "WORKS" if ok else "FAILS", 0.42, (0.22, 0, 0),
                  m, m_back, parent=pivot)
    outlined_text(P + "Reason", root, res["short"], 0.2, (0, 0, -0.42), m_txt, m_back, parent=pivot)
    key_hide(pivot, stamp_f)

    if not ok:
        return
    # lamp on
    bulb_m = objs["m_bulb"]
    p = bulb_m.node_tree.nodes.get("Principled BSDF")
    es = p.inputs["Emission Strength"]
    es.default_value = 0.0
    es.keyframe_insert("default_value", frame=f0 - 1)
    es.default_value = 25.0
    es.keyframe_insert("default_value", frame=f0 + 2)
    lamp = objs["lamp"]
    lamp.energy = 0
    lamp.keyframe_insert("energy", frame=f0 - 1)
    lamp.energy = 120
    lamp.keyframe_insert("energy", frame=f0 + 2)
    # flag up
    flag = objs["flag"]
    flag.keyframe_insert("location", frame=f0)
    flag.location.z = 1.42
    flag.keyframe_insert("location", frame=f0 + 18)
    # confetti: ballistic flakes under THIS planet's gravity (+ light flutter drag)
    g = GRAVITY[res["planet"]]
    rnd = random.Random(7)
    cols = [mat(f"conf{i}", c, emit=0.6) for i, c in enumerate(
        [(1, 0.2, 0.3), (1, 0.8, 0.1), (0.2, 0.6, 1), (0.3, 1, 0.4), (0.9, 0.3, 1)])]
    for i in range(70):
        o = box(P + f"Confetti{i}", root, -0.03, 0.03, -0.018, 0.018, -0.002, 0.002,
                cols[i % len(cols)], bevel=0)
        src = Vector((CUP_CX, 0, CUP_H)) if i % 2 else Vector((POLE_X, 0, 1.74))
        ang = math.radians(rnd.uniform(-35, 35) + (10 if i % 2 else -15))
        sp = rnd.uniform(2.0, 4.0)
        vel = Vector((math.sin(ang) * sp, rnd.uniform(-0.6, 0.6), math.cos(ang) * sp))
        spin = Vector((rnd.uniform(-12, 12), rnd.uniform(-12, 12), rnd.uniform(-12, 12)))
        pos, rot = src.copy(), Vector((0, 0, 0))
        dt = 1.0 / FPS
        o.scale = (0, 0, 0)
        o.keyframe_insert("scale", frame=f0 - 1)
        o.scale = (1, 1, 1)
        o.keyframe_insert("scale", frame=f0)
        for f in range(f0, end + 1, 2):
            o.location = pos
            o.rotation_euler = rot
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("rotation_euler", frame=f)
            for _ in range(2):
                vel.z -= g * dt
                vel *= (1 - 1.8 * dt)          # paper flutter drag
                pos = pos + vel * dt
                if pos.z < 0.01:
                    pos.z, vel = 0.01, Vector((0, 0, 0))
                rot = rot + spin * dt


# =============================================================================
# render setup
# =============================================================================
def setup_render(sc, preview):
    r = sc.render
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    if preview or ENGINE == "CYCLES" or not any(e.startswith("BLENDER_EEVEE") for e in engines):
        r.engine = 'CYCLES'
        sc.cycles.device = 'CPU'
        sc.cycles.samples = PREVIEW_SAMPLES if preview else CYCLES_SAMPLES
        sc.cycles.use_denoising = True
        if hasattr(sc.cycles, "max_bounces"):
            sc.cycles.max_bounces = 4
    else:
        r.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in engines else 'BLENDER_EEVEE_NEXT'
        e = sc.eevee
        if hasattr(e, "taa_render_samples"):
            e.taa_render_samples = EEVEE_SAMPLES
        if hasattr(e, "use_shadows"):
            e.use_shadows = True
        if hasattr(e, "use_raytracing"):
            e.use_raytracing = True
    if preview:
        r.resolution_x, r.resolution_y = PREVIEW_RES
    else:
        r.resolution_x, r.resolution_y = RESOLUTION
    r.resolution_percentage = 100
    r.image_settings.file_format = 'PNG'
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Punchy'
    except Exception:
        try:
            sc.view_settings.view_transform = 'Filmic'
        except Exception:
            pass


def out_dir():
    if bpy.data.filepath:
        return bpy.path.abspath(OUTPUT_DIR)
    base = os.getcwd() if bpy.app.background else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, OUTPUT_DIR.replace("//", ""))


# =============================================================================
# main
# =============================================================================
def main():
    flags = argv_flags()
    preview = PREVIEW or "--preview" in flags
    render = RENDER or "--render" in flags
    cleanup()
    results = []
    scenes = []
    for i, planet in enumerate(PLANETS, 1):
        sc, objs = build_scene(i, planet)
        baked = bake(sc)
        s = measure(sc, objs)
        res = judge(planet, s)
        res["baked"] = baked
        dress(sc, objs, res)
        results.append(res)
        scenes.append(sc)
        print(f"[{sc.name}] g={GRAVITY[planet]}  {'WORKS' if res['success'] else 'FAILS'}: {res['reason']}")

    print("\n" + "=" * 96)
    print(f"{'planet':<9}{'g':>7}  {'result':<7} {'cross_x':>8} {'max_x':>7} {'ledge_dz':>8} "
          f"{'doms':>5} {'golf_end':<22} reason")
    for r in results:
        cx = f"{r['cross_x']:.2f}" if r['cross_x'] is not None else "  -"
        print(f"{r['planet']:<9}{GRAVITY[r['planet']]:>7}  {'WORKS' if r['success'] else 'FAILS':<7} "
              f"{cx:>8} {r['max_x']:>7.2f} {r['ledge_drop']:>8.2f} {r['doms_down']:>3}/{DOM_N} "
              f"{str(r['golf_end']):<22} {r['reason']}")
    wins = [r["planet"] for r in results if r["success"]]
    print("=" * 96)
    print(f"launch speed {launch_speed():.3f} m/s (tuned for {TARGET_PLANET})")
    print("SUCCESS ON EXACTLY ONE PLANET:", "YES" if len(wins) == 1 else "NO", wins)

    def show(sc):
        """make sc the active scene (rigid-body caches render reliably that way)."""
        try:
            if bpy.context.window is not None:
                bpy.context.window.scene = sc
        except Exception:
            pass

    def render_still(sc, f, path):
        show(sc)
        sc.frame_set(f)
        sc.render.filepath = path
        with bpy.context.temp_override(scene=sc):
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print("preview:", path)

    od = out_dir()
    if preview:
        os.makedirs(os.path.join(od, "preview"), exist_ok=True)
        for sc, r in zip(scenes, results):
            setup_render(sc, True)
            if r["success"]:
                # extra still: the ball arcing into the basket
                fl = r["fly_frame"]
                render_still(sc, fl, os.path.join(od, "preview", f"{sc.name}_flight_f{fl:03d}.png"))
                f = min(r["stamp_frame"] + 10, sc.frame_end)
            elif r["short"] == "FLEW OVER":
                f = r["stamp_frame"] + 2       # ball still visible flying off
            else:
                f = min(max(r["key_frame"], r["stamp_frame"] + 8), sc.frame_end)
            render_still(sc, f, os.path.join(od, "preview", f"{sc.name}_f{f:03d}.png"))
    elif render:
        for sc in scenes:
            setup_render(sc, False)
            show(sc)
            sc.render.filepath = os.path.join(od, sc.name, "frame_")
            with bpy.context.temp_override(scene=sc):
                bpy.ops.render.render(animation=True, scene=sc.name)
            print("rendered:", os.path.join(od, sc.name))
    else:
        for sc in scenes:
            setup_render(sc, False)
    show(scenes[-1])
    return results


if __name__ == "__main__":
    main()
