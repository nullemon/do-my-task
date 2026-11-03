"""
Pouring water on every planet  --  Blender 4.2 LTS ... 5.x
=========================================================

A glass of water tilts and pours onto a table on each planet.  Real gravity,
real-world units, Mantaflow FLIP liquid.  One scene per planet (01_Moon, ...).

Run inside Blender: Scripting tab -> open this file -> Run Script (builds +
bakes if BAKE_ON_RUN).  Then pick a scene and press play.

Headless:
    blender -b -P water_pour_planets.py -- --render        # bake + render all
    blender -b -P water_pour_planets.py -- --preview       # tiny bake + stills
    extra args:  --out DIR   (output/cache base folder)
                 --planets Moon,Sun   (subset)
                 --no-bake            (build only)
"""

import bpy
import bmesh
import math
import os
import sys
import json
import time
from mathutils import Vector, Matrix

# =============================================================================
# CONFIG
# =============================================================================
PLANETS = ["Moon", "Mars", "Earth", "Jupiter", "Sun", "Pluto"]   # order = scene order

FPS = 30
SECONDS = 5.0                    # length of the final clip
RES_X, RES_Y = 1080, 1920        # vertical 9:16
ENGINE = "EEVEE"                 # "EEVEE" (auto-picks EEVEE_NEXT on 4.2-4.4) or "CYCLES"
CYCLES_SAMPLES = 256             # final Cycles samples (water looks best in Cycles)
EEVEE_SAMPLES = 64

# --- fluid quality ---------------------------------------------------------
RESOLUTION = 128                 # domain divisions along the longest side (48 preview, 128-192 final)
MESH_UPRES = 2                   # liquid mesh upres ("mesh_scale"), 1 = off
MESH_SMOOTH_POS = 2              # liquid mesh smoothing (positive / negative)
MESH_SMOOTH_NEG = 2
MESH_PARTICLE_RADIUS = 1.6       # smaller = more detailed (but noisier) surface
CFL = 2.0                        # Courant number for normal gravity
CFL_HIGH_G = 1.0                 # Courant number used when g > 50 m/s^2 (the Sun)
SURFACE_TENSION = 0.0            # Mantaflow surface tension (0 = off, see README)
CACHE_DIR = "//cache_water_pour" # per-planet sub folders are created inside
BAKE_ON_RUN = True               # bake when the script is run

# --- output ------------------------------------------------------------------
RENDER = False                   # same as --render
OUTPUT_DIR = "//renders/water_pour"

# --- preview (headless verification) -----------------------------------------
PREVIEW = False                  # same as --preview
PREVIEW_RESOLUTION = 48
PREVIEW_SECONDS = 2.4
PREVIEW_FRAME = 58               # (1.9 s) the still that is rendered for each planet
PREVIEW_RES = (270, 480)
PREVIEW_SAMPLES = 24
PREVIEW_IMPACT_STILLS = ["Sun", "Moon"]   # also render these planets 2 frames after impact

HOOK_CAPTION = "POURING WATER ON"

# =============================================================================
# PLANET DATA (m/s^2) and looks
# =============================================================================
GRAVITY = {
    "Pluto": 0.62, "Moon": 1.62, "Mercury": 3.70, "Mars": 3.71, "Venus": 8.87,
    "Earth": 9.81, "Uranus": 8.69, "Neptune": 11.15, "Saturn": 10.44,
    "Jupiter": 24.79, "Sun": 274.0,
}
# ground colour, backdrop low colour, backdrop high colour, world colour, ground emission
LOOKS = {
    "Moon":    dict(ground=(0.32, 0.32, 0.33), low=(0.035, 0.035, 0.04), high=(0.0, 0.0, 0.0), world=(0.0, 0.0, 0.0), emit=0.0),
    "Mars":    dict(ground=(0.42, 0.13, 0.05), low=(0.55, 0.30, 0.13), high=(0.12, 0.05, 0.02), world=(0.12, 0.06, 0.03), emit=0.0),
    "Earth":   dict(ground=(0.10, 0.28, 0.07), low=(0.35, 0.55, 0.85), high=(0.04, 0.10, 0.30), world=(0.08, 0.13, 0.25), emit=0.0),
    "Jupiter": dict(ground=(0.55, 0.36, 0.20), low=(0.75, 0.42, 0.18), high=(0.20, 0.09, 0.04), world=(0.15, 0.08, 0.04), emit=0.0),
    "Sun":     dict(ground=(1.00, 0.45, 0.06), low=(1.00, 0.55, 0.10), high=(0.35, 0.06, 0.0), world=(0.25, 0.08, 0.01), emit=2.5),
    "Pluto":   dict(ground=(0.78, 0.72, 0.62), low=(0.06, 0.06, 0.08), high=(0.0, 0.0, 0.01), world=(0.01, 0.01, 0.015), emit=0.0),
    "Mercury": dict(ground=(0.35, 0.33, 0.31), low=(0.04, 0.04, 0.04), high=(0.0, 0.0, 0.0), world=(0.0, 0.0, 0.0), emit=0.0),
    "Venus":   dict(ground=(0.55, 0.45, 0.20), low=(0.85, 0.70, 0.30), high=(0.35, 0.25, 0.08), world=(0.3, 0.24, 0.1), emit=0.0),
    "Saturn":  dict(ground=(0.70, 0.60, 0.40), low=(0.80, 0.68, 0.45), high=(0.25, 0.20, 0.12), world=(0.2, 0.16, 0.1), emit=0.0),
    "Uranus":  dict(ground=(0.45, 0.70, 0.75), low=(0.50, 0.80, 0.85), high=(0.08, 0.20, 0.25), world=(0.1, 0.18, 0.2), emit=0.0),
    "Neptune": dict(ground=(0.15, 0.25, 0.65), low=(0.20, 0.35, 0.85), high=(0.02, 0.05, 0.20), world=(0.03, 0.06, 0.2), emit=0.0),
}

# =============================================================================
# SCENE GEOMETRY (metres, real-world size)
# =============================================================================
GLASS_R = 0.040          # outer radius
GLASS_H = 0.125          # height
GLASS_WALL = 0.004
GLASS_BASE = 0.012
FILL = 0.62              # fraction of inner height filled with water
LIP = Vector((-0.05, 0.0, 0.30))      # pour lip = rotation pivot (world)
TILT_START_S = 0.20      # hand starts tipping the glass (seconds)
TILT_DUR_S = 0.40        # quick tip, same hand on every planet
TILT_DEG = 100.0         # final pour angle; the glass is then held still
BOWL_X = 0.07            # bowl centre (the stream lands ~0.12 m right of the lip on every planet)
BOWL_R = 0.105           # bowl rim radius
BOWL_H = 0.060           # bowl height
BOWL_WALL = 0.006
DOMAIN_MIN = Vector((-0.21, -0.14, 0.0))   # table top is z = 0 (domain floor)
DOMAIN_MAX = Vector((0.21, 0.14, 0.42))
TAG = "wp_"              # prefix of everything this script creates

# =============================================================================
# helpers
# =============================================================================
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a = dict(render=RENDER, preview=PREVIEW, out=None, planets=None, bake=BAKE_ON_RUN)
    i = 0
    while i < len(argv):
        k = argv[i]
        if k == "--render": a["render"] = True
        elif k == "--preview": a["preview"] = True
        elif k == "--no-bake": a["bake"] = False
        elif k == "--out": a["out"] = argv[i + 1]; i += 1
        elif k == "--planets": a["planets"] = [p.strip() for p in argv[i + 1].split(",")]; i += 1
        i += 1
    return a


def base_dir(args):
    if args["out"]:
        return os.path.abspath(args["out"])
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    f = globals().get("__file__", "")
    if f and os.path.isfile(f):
        return os.path.dirname(os.path.abspath(f))
    return os.getcwd()


def resolve(path, base):
    if path.startswith("//"):
        return os.path.join(base, path[2:])
    return path


def eevee_engine_id():
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if e in items:
            return e
    return "CYCLES"


def setp(obj, name, value):
    """set attribute only if it exists (API differences 4.2 ... 5.x)"""
    if hasattr(obj, name):
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            pass
    return False


def link(obj, coll):
    coll.objects.link(obj)
    return obj


def new_obj(name, data, coll):
    o = bpy.data.objects.new(TAG + name, data)
    coll.objects.link(o)
    return o


def node_mat(name):
    m = bpy.data.materials.new(TAG + name)
    m.use_nodes = True
    return m


def principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def pset(bsdf, names, value):
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return


def clear_previous():
    for sc in list(bpy.data.scenes):
        if sc.name.startswith(TAG) or sc.get(TAG + "scene"):
            if len(bpy.data.scenes) > 1:
                bpy.data.scenes.remove(sc)
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras, bpy.data.worlds, bpy.data.collections,
                 bpy.data.actions):
        for d in list(coll):
            if d.name.startswith(TAG) and d.users == 0 or (d.name.startswith(TAG) and coll is bpy.data.objects):
                try:
                    coll.remove(d)
                except Exception:
                    pass
    # second pass for now-orphaned data
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.worlds, bpy.data.collections, bpy.data.actions):
        for d in list(coll):
            if d.name.startswith(TAG) and d.users == 0:
                coll.remove(d)


# =============================================================================
# materials
# =============================================================================
def mat_water():
    m = node_mat("water")
    b = principled(m)
    pset(b, "Base Color", (0.82, 0.93, 1.0, 1))
    pset(b, "Roughness", 0.0)
    pset(b, "IOR", 1.333)
    pset(b, ["Transmission Weight", "Transmission"], 1.0)
    pset(b, ["Specular IOR Level", "Specular"], 0.5)
    # Eevee: raytraced / screen-space refraction where available
    setp(m, "use_raytrace_refraction", True)        # 4.2+ (Eevee Next)
    setp(m, "use_screen_refraction", True)          # legacy Eevee
    setp(m, "surface_render_method", "DITHERED")
    if hasattr(m, "blend_method") and not hasattr(m, "surface_render_method"):
        m.blend_method = "OPAQUE"
    setp(m, "thickness_mode", "SPHERE")
    return m


def mat_glass():
    m = node_mat("glass")
    b = principled(m)
    pset(b, "Base Color", (0.95, 0.98, 1.0, 1))
    pset(b, "Roughness", 0.0)
    pset(b, "IOR", 1.5)
    pset(b, ["Transmission Weight", "Transmission"], 1.0)
    setp(m, "use_raytrace_refraction", True)
    setp(m, "use_screen_refraction", True)
    setp(m, "surface_render_method", "DITHERED")
    setp(m, "thickness_mode", "SLAB")
    return m


def mat_bowl():
    m = node_mat("bowl")
    b = principled(m)
    pset(b, "Base Color", (0.035, 0.04, 0.05, 1))      # dark glazed ceramic: water reads well in it
    pset(b, "Roughness", 0.12)
    pset(b, ["Coat Weight", "Clearcoat"], 0.6)
    return m


def mat_ground(planet):
    lk = LOOKS[planet]
    m = node_mat("ground_" + planet)
    nt = m.node_tree
    b = principled(m)
    # subtle procedural variation so the table is not flat CG grey
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    c = lk["ground"]
    ramp.color_ramp.elements[0].color = (c[0] * 0.75, c[1] * 0.75, c[2] * 0.75, 1)
    ramp.color_ramp.elements[1].color = (min(1, c[0] * 1.15), min(1, c[1] * 1.15), min(1, c[2] * 1.15), 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    pset(b, "Roughness", 0.75)
    pset(b, ["Specular IOR Level", "Specular"], 0.0)   # matte: no grazing-angle glare
    if lk["emit"] > 0:
        nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"] if "Emission Color" in b.inputs else b.inputs["Emission"])
        pset(b, "Emission Strength", lk["emit"])
    return m


def mat_backdrop(planet):
    lk = LOOKS[planet]
    m = node_mat("backdrop_" + planet)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15
    ramp.color_ramp.elements[0].color = (*lk["low"], 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (*lk["high"], 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 0.7
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_text(color=(1, 1, 1), strength=3.0, name="label"):
    m = node_mat(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


# =============================================================================
# geometry
# =============================================================================
def glass_mesh(extra=0.0, name="glass"):
    """Lathe profile of a tumbler.  Object origin = pour lip (+X side, top rim).
    extra > 0 thickens the wall outwards / base downwards (collision proxy)."""
    R, H, w, tb = GLASS_R + extra, GLASS_H + extra, GLASS_WALL + extra, GLASS_BASE + extra
    ri = R - w
    # profile (r, z) from outer bottom centre -> around -> inner bottom centre
    prof = [(0.0, 0.0), (R - 0.004, 0.0), (R - 0.0012, 0.0006), (R, 0.004), (R, H - 0.0015),
            (R - 0.0008, H), (ri + 0.0008, H), (ri, H - 0.0015), (ri, tb + 0.003),
            (ri - 0.003, tb), (0.0, tb)]
    # origin at the lip: shift so (R, 0, H) -> (0, 0, 0)
    return lathe_mesh(prof, name, offset=(-GLASS_R, 0.0, -H))


def lathe_mesh(prof, name, offset=(0, 0, 0), steps=48):
    """Revolve an (r, z) profile that starts and ends on the axis -> closed mesh."""
    me = bpy.data.meshes.new(TAG + name)
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, z)) for r, z in prof]
    for a, b in zip(vs[:-1], vs[1:]):
        bm.edges.new((a, b))
    bmesh.ops.spin(bm, geom=bm.verts[:] + bm.edges[:], cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=math.tau, steps=steps, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.translate(bm, verts=bm.verts[:], vec=offset)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def bowl_mesh(extra=0.0, name="bowl"):
    """Round bowl standing on the table (origin = centre of its foot, z = 0).
    extra > 0 thickens it outwards (hidden collision version)."""
    R, H, w = BOWL_R, BOWL_H, BOWL_WALL
    n = 12
    outer = []
    for i in range(n + 1):                 # quarter ellipse from foot to rim
        a = (math.pi / 2) * i / n
        outer.append((0.045 + (R - 0.045) * math.sin(a) + extra * math.sin(a),
                      (H) * (1 - math.cos(a)) - extra * math.cos(a)))
    inner = []
    for i in range(n, -1, -1):
        a = (math.pi / 2) * i / n
        inner.append((0.040 + (R - w - 0.040) * math.sin(a), w + (H - w) * (1 - math.cos(a))))
    prof = [(0.0, -extra)] + outer + [(R - w * 0.5, H + 0.002)] + inner + [(0.0, w)]
    return lathe_mesh(prof, name, offset=(0, 0, 0), steps=64)


COLLIDER_STAVES = 16


def collider_meshes(thick):
    """Convex closed pieces approximating the tumbler (glass-local, origin at lip)."""
    cx = -GLASS_R
    ri = GLASS_R - GLASS_WALL
    zb = -GLASS_H                      # outer bottom
    zi = -GLASS_H + GLASS_BASE         # inner bottom
    out = [cylinder_mesh("glass_col_base", ri + thick, zb - max(0.0, thick - GLASS_BASE), zi,
                         cx=cx, segs=COLLIDER_STAVES * 2)]
    n = COLLIDER_STAVES
    half_w = (ri + thick) * math.tan(math.pi / n) * 1.25     # overlap between staves
    for i in range(n):
        a = math.tau * i / n
        me = box_mesh(f"glass_col_stave{i:02d}", (ri, -half_w, zb), (ri + thick, half_w, 0.0))
        rot = Matrix.Rotation(a, 4, "Z")
        me.transform(Matrix.Translation((cx, 0, 0)) @ rot)
        out.append(me)
    return out


def cylinder_mesh(name, r, z0, z1, cx=0.0, segs=32):
    me = bpy.data.meshes.new(TAG + name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=z1 - z0)
    bmesh.ops.translate(bm, verts=bm.verts[:], vec=(cx, 0, (z0 + z1) / 2))
    bm.to_mesh(me)
    bm.free()
    return me


def box_mesh(name, mn, mx):
    me = bpy.data.meshes.new(TAG + name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector([mn[i] + (v.co[i] + 0.5) * (mx[i] - mn[i]) for i in range(3)])
    bm.to_mesh(me)
    bm.free()
    return me


def sweep_mesh(name, width=4.0, depth=2.2, height=2.5, radius=0.6, y0=0.25, z0=-0.03):
    """Curved studio backdrop (cyclorama) behind the table."""
    me = bpy.data.meshes.new(TAG + name)
    bm = bmesh.new()
    n = 10
    pts = [(-depth, z0), (y0, z0)]       # floor (y, z) from the camera side backwards
    for i in range(1, n + 1):
        a = (math.pi / 2) * i / n
        pts.append((y0 + radius * math.sin(a), z0 + radius * (1 - math.cos(a))))
    pts.append((y0 + radius, z0 + height))
    rows = []
    for y, z in pts:
        rows.append([bm.verts.new((x, y, z)) for x in (-width / 2, width / 2)])
    for a, b in zip(rows[:-1], rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def text_obj(name, body, coll, mat, size=0.05, extrude=0.0):
    cu = bpy.data.curves.new(TAG + name, type="FONT")
    cu.body = body
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    cu.extrude = extrude
    setp(cu, "bevel_depth", extrude * 0.3)
    o = new_obj(name, cu, coll)
    o.data.materials.append(mat)
    return o


# =============================================================================
# scene builder
# =============================================================================
def build_scene(idx, planet, args, base, res, frames):
    g = GRAVITY[planet]
    sc = bpy.data.scenes.new(f"{idx:02d}_{planet}")
    sc[TAG + "scene"] = True
    sc[TAG + "planet"] = planet
    coll = bpy.data.collections.new(TAG + planet)
    sc.collection.children.link(coll)

    # --- time + gravity ---------------------------------------------------
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = frames
    sc.use_gravity = True
    sc.gravity = (0.0, 0.0, -g)

    # --- world -----------------------------------------------------------
    w = bpy.data.worlds.new(TAG + "world_" + planet)
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*LOOKS[planet]["world"], 1)
    bg.inputs["Strength"].default_value = 0.6
    sc.world = w

    # --- table + backdrop ------------------------------------------------
    table = new_obj("table_" + planet, box_mesh("table", (-1.2, -0.9, -0.05), (1.2, 0.25, 0.0)), coll)
    bev = table.modifiers.new("bevel", "BEVEL")
    bev.width = 0.01
    bev.segments = 4
    table.data.materials.append(mat_ground(planet))
    back = new_obj("backdrop_" + planet, sweep_mesh("backdrop", y0=0.45, z0=-0.05, radius=0.5), coll)
    back.data.materials.append(mat_backdrop(planet))
    # the backdrop should not light the water like a big lamp: keep its light low
    setp(back, "visible_shadow", False)

    # --- glass (visual + collision obstacle, keyframed tilt) -------------
    glass = new_obj("glass_" + planet, glass_mesh(), coll)
    glass.location = LIP
    glass.rotation_mode = "XYZ"
    glass.data.materials.append(mat_glass())
    f0 = 1 + round(TILT_START_S * FPS)
    f1 = f0 + round(TILT_DUR_S * FPS)
    glass.rotation_euler = (0, 0, 0)
    glass.keyframe_insert("rotation_euler", index=1, frame=1)
    glass.keyframe_insert("rotation_euler", index=1, frame=f0)
    glass.rotation_euler = (0, math.radians(TILT_DEG), 0)
    glass.keyframe_insert("rotation_euler", index=1, frame=f1)
    act = glass.animation_data.action
    try:
        fcs = act.fcurves
    except AttributeError:     # 5.x layered actions
        fcs = [fc for layer in act.layers for strip in layer.strips
               for cb in strip.channelbags for fc in cb.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "AUTO"

    # --- water ---------------------------------------------------------------
    # The liquid simulation starts the moment the tip is finished (frame f1);
    # during the tip a still water mesh rides inside the glass.  From f1 on the
    # glass is held still, so the collider is a static obstacle (see README:
    # Mantaflow loses liquid that sits inside a *moving* closed container).
    ri = GLASS_R - GLASS_WALL
    zb = -GLASS_H + GLASS_BASE + 0.002            # glass-local (origin = lip)
    zt = -GLASS_H + GLASS_BASE + FILL * (GLASS_H - GLASS_BASE)
    pose = Matrix.Translation(LIP) @ Matrix.Rotation(math.radians(TILT_DEG), 4, "Y")
    water0 = new_obj("water_init_" + planet,
                     cylinder_mesh("water_init", ri - 0.0015, zb, zt, cx=-GLASS_R), coll)
    water0.matrix_world = pose
    water0.display_type = "WIRE"
    water0.hide_render = True
    intro = new_obj("water_intro_" + planet,
                    cylinder_mesh("water_intro", ri - 0.0003, zb - 0.0015, zt, cx=-GLASS_R, segs=48), coll)
    intro.parent = glass
    for p_ in intro.data.polygons:
        p_.use_smooth = True
    intro.data.materials.append(mat_water())

    # --- fluid domain ------------------------------------------------------
    dom = new_obj("domain_" + planet, box_mesh("domain", DOMAIN_MIN, DOMAIN_MAX), coll)
    dom.data.materials.append(mat_water())
    dm = dom.modifiers.new("Fluid", "FLUID")
    dm.fluid_type = "DOMAIN"
    d = dm.domain_settings
    d.domain_type = "LIQUID"
    d.resolution_max = res
    d.use_mesh = True
    d.mesh_scale = MESH_UPRES
    d.mesh_smoothen_pos = MESH_SMOOTH_POS
    d.mesh_smoothen_neg = MESH_SMOOTH_NEG
    d.mesh_particle_radius = MESH_PARTICLE_RADIUS
    d.use_collision_border_bottom = True        # the table
    for side in ("front", "back", "left", "right", "top"):
        setattr(d, "use_collision_border_" + side, False)   # open: splash leaves, no invisible walls
    d.delete_in_obstacle = True
    d.use_fractions = False                     # fractions leak through the thin glass wall
    d.surface_tension = SURFACE_TENSION
    # gravity: Mantaflow uses scene.gravity when scene.use_gravity is on
    # (x effector_weights.gravity); otherwise its own domain.gravity.  Set both.
    d.gravity = (0.0, 0.0, -g)
    d.effector_weights.gravity = 1.0
    # timestep control: fall speed from the lip ~ sqrt(2 g h); per frame the
    # liquid must not move more than CFL cells per sub-step
    cfl = CFL_HIGH_G if g > 50 else CFL
    dx = max(DOMAIN_MAX - DOMAIN_MIN) / res
    v_max = math.sqrt(2 * g * LIP.z) + 1.0
    steps = v_max / (FPS * dx * cfl)
    d.use_adaptive_timesteps = True
    d.cfl_condition = cfl
    d.timesteps_max = int(min(250, max(4, math.ceil(1.5 * steps))))
    d.timesteps_min = int(max(1, min(d.timesteps_max, math.ceil(steps / 3))))
    d.time_scale = 1.0
    d.cache_type = "ALL"
    d.cache_frame_start = f1
    d.cache_frame_end = frames
    sc[TAG + "sim_start"] = f1
    # before the sim starts: show the intro water, hide the (unbaked) domain box
    for ob, vis_before in ((dom, False), (intro, True)):
        for fr, vis in ((1, vis_before), (f1 - 1, vis_before), (f1, not vis_before)):
            ob.hide_render = not vis
            ob.keyframe_insert("hide_render", frame=fr)
            if ob is intro:             # (the domain must stay enabled for baking)
                ob.hide_viewport = not vis
                ob.keyframe_insert("hide_viewport", frame=fr)
    d.cache_data_format = "OPENVDB" if "OPENVDB" in d.bl_rna.properties["cache_data_format"].enum_items.keys() else d.cache_data_format
    cdir = os.path.join(resolve(CACHE_DIR, base), f"{idx:02d}_{planet}_r{res}")
    d.cache_directory = cdir
    d.fluid_group = coll
    d.effector_group = coll
    dom.display_type = "WIRE"
    sc[TAG + "timesteps"] = (d.timesteps_min, d.timesteps_max)

    fm = water0.modifiers.new("Fluid", "FLUID")
    fm.fluid_type = "FLOW"
    f = fm.flow_settings
    f.flow_type = "LIQUID"
    f.flow_behavior = "GEOMETRY"
    f.flow_source = "MESH"
    f.use_plane_init = False
    f.surface_distance = 0.0
    f.volume_density = 1.0

    # collision obstacle = hidden convex pieces (a base puck + COLLIDER_STAVES wall
    # staves), each its own static effector at the held pour pose.  Why not the
    # glass mesh itself: Blender decides "inside an effector" by casting 26 rays
    # and calls a cell inside when every ray hits the mesh -- inside a deep tilted
    # tumbler every ray hits the glass, so the cavity would become obstacle.
    # Walls are >= 1.5 cells thick so nothing leaks on a coarse preview grid.
    thick = max(GLASS_WALL, 1.5 * dx)
    for k, me in enumerate(collider_meshes(thick)):
        part = new_obj(f"glass_collider{k:02d}_{planet}", me, coll)
        part.matrix_world = pose
        part.display_type = "WIRE"
        part.hide_render = True
        em = part.modifiers.new("Fluid", "FLUID")
        em.fluid_type = "EFFECTOR"
        e = em.effector_settings
        e.effector_type = "COLLISION"
        e.use_plane_init = False
        e.surface_distance = 0.0
        e.subframes = 1

    # --- the bowl on the table (visual + thicker static collider) ----------
    bowl = new_obj("bowl_" + planet, bowl_mesh(), coll)
    bowl.location = (BOWL_X, 0.0, 0.0)
    bowl.data.materials.append(mat_bowl())
    bcol = new_obj("bowl_collider_" + planet, bowl_mesh(max(0.0, 1.5 * dx - BOWL_WALL), "bowl_collider"), coll)
    bcol.location = bowl.location
    bcol.display_type = "WIRE"
    bcol.hide_render = True
    em = bcol.modifiers.new("Fluid", "FLUID")
    em.fluid_type = "EFFECTOR"
    em.effector_settings.effector_type = "COLLISION"
    em.effector_settings.use_plane_init = False

    # --- lights: big soft key, two strip lights behind for glass/water edges
    def area(name, loc, rot, size, size_y, power, color=(1, 1, 1), spread=180):
        L = bpy.data.lights.new(TAG + name, "AREA")
        setp(L, "spread", math.radians(spread))
        L.shape = "RECTANGLE"
        L.size, L.size_y = size, size_y
        L.energy = power
        L.color = color
        o = new_obj(name + "_" + planet, L, coll)
        o.location = loc
        o.rotation_euler = rot
        return o
    # the strip lights only exist to draw highlights on glass and water: keep
    # them off the diffuse table (otherwise they wash the table out to white)
    area("key", (-0.6, -0.7, 1.0), (math.radians(50), 0, math.radians(-38)), 0.8, 0.8, 45)
    sl = area("stripL", (-0.35, 0.35, 0.35), (math.radians(-90), math.radians(-35), 0), 0.08, 0.9, 25, spread=35)
    sr = area("stripR", (0.35, 0.35, 0.35), (math.radians(-90), math.radians(35), 0), 0.08, 0.9, 25, spread=35)
    area("top", (0.0, 0.0, 1.2), (0, 0, 0), 0.6, 0.3, 12)
    for o in (sl, sr):
        setp(o, "visible_diffuse", False)

    # --- camera --------------------------------------------------------------
    camd = bpy.data.cameras.new(TAG + "cam")
    camd.lens = 55
    camd.sensor_fit = "VERTICAL"
    camd.sensor_height = 36
    camd.clip_start = 0.05
    cam = new_obj("camera_" + planet, camd, coll)
    cam.location = (0.0, -1.15, 0.36)
    cam.rotation_euler = (math.radians(87.5), 0, 0)
    sc.camera = cam

    # --- labels (parented to camera so they always sit in the top third) ---
    d_txt = 0.8
    half_h = d_txt * (camd.sensor_height / 2) / camd.lens
    half_w = half_h * RES_X / RES_Y
    lab = text_obj("label_" + planet, f"{planet.upper()} · {g:g} m/s²", coll,
                   mat_text((1, 1, 1), 4.0, "label_mat_" + planet), size=0.05, extrude=0.002)
    hook = text_obj("hook_" + planet, HOOK_CAPTION, coll,
                    mat_text((1.0, 0.85, 0.35), 4.0, "hook_mat_" + planet), size=0.03, extrude=0.001)
    for o, frac_w, y in ((lab, 0.86, 0.62), (hook, 0.62, 0.80)):
        o.parent = cam
        # approximate glyph width ~0.62 * size per character (Bfont)
        n = len(o.data.body)
        o.data.size = (2 * half_w * frac_w) / (0.62 * n)
        o.location = (0.0, y * half_h, -d_txt)
        o.rotation_euler = (0, 0, 0)
        setp(o, "visible_shadow", False)
    sc[TAG + "lip"] = list(LIP)
    return sc, dom


# =============================================================================
# render settings
# =============================================================================
def setup_render(sc, preview, out_dir):
    r = sc.render
    r.fps = FPS
    r.resolution_x, r.resolution_y = (PREVIEW_RES if preview else (RES_X, RES_Y))
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.filepath = out_dir + os.sep + "frame_####"
    setp(sc.view_settings, "view_transform", "AgX") or setp(sc.view_settings, "view_transform", "Filmic")
    setp(sc.view_settings, "look", "AgX - Medium High Contrast")
    engine = "CYCLES" if (preview or ENGINE.upper() == "CYCLES") else eevee_engine_id()
    r.engine = engine
    c = sc.cycles
    c.samples = PREVIEW_SAMPLES if preview else CYCLES_SAMPLES
    setp(c, "use_denoising", True)
    setp(c, "device", "CPU")
    c.max_bounces = 16
    c.transmission_bounces = 16
    c.glossy_bounces = 8
    c.transparent_max_bounces = 16
    c.caustics_reflective = False
    c.caustics_refractive = True
    c.blur_glossy = 1.0
    setp(c, "use_adaptive_sampling", True)
    ee = sc.eevee
    setp(ee, "taa_render_samples", EEVEE_SAMPLES)
    setp(ee, "use_raytracing", True)            # 4.2+ (Eevee Next)
    setp(ee, "ray_tracing_method", "SCREEN")
    setp(ee, "use_ssr", True)                   # legacy Eevee
    setp(ee, "use_ssr_refraction", True)
    setp(ee, "use_gtao", True)
    setp(ee, "use_shadows", True)
    if hasattr(ee, "ray_tracing_options"):
        setp(ee.ray_tracing_options, "resolution_scale", "1")
        setp(ee.ray_tracing_options, "use_denoise", True)


# =============================================================================
# baking + measurement
# =============================================================================
def bake(sc, dom):
    d = dom.modifiers["Fluid"].domain_settings
    os.makedirs(d.cache_directory, exist_ok=True)
    win = bpy.context.window
    vl = sc.view_layers[0]
    kw = dict(scene=sc, view_layer=vl, active_object=dom, object=dom,
              selected_objects=[dom], selected_editable_objects=[dom])
    if win is not None:
        kw["window"] = win
    old = win.scene if win is not None else None
    if win is not None:
        win.scene = sc
    try:
        with bpy.context.temp_override(**kw):
            try:
                bpy.ops.fluid.free_all()
            except Exception:
                pass
            t = time.time()
            bpy.ops.fluid.bake_all()
            return time.time() - t
    finally:
        if win is not None and old is not None:
            win.scene = old


def liquid_points(sc, dom, frame):
    """World-space vertices of the baked liquid mesh + its volume (m^3)."""
    sc.frame_set(frame)
    vl = sc.view_layers[0]
    dg = vl.depsgraph if hasattr(vl, "depsgraph") else bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = dom.evaluated_get(dg)
    me = ev.to_mesh()
    if len(me.vertices) <= 8:          # no liquid -> modifier returns the domain box
        ev.to_mesh_clear()
        return [], 0.0
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    # divergence theorem with F = (0, 0, z): open faces on the table (z = 0) add nothing
    vol = 0.0
    me.calc_loop_triangles()
    for tri in me.loop_triangles:
        a, b, c = (pts[i] for i in tri.vertices)
        n = (b - a).cross(c - a)            # = 2 * area * normal
        vol += 0.5 * n.z * (a.z + b.z + c.z) / 3.0
    ev.to_mesh_clear()
    return pts, abs(vol)


def _seg_dist_xz(p, a, b):
    ax, az, bx, bz = a[0], a[2], b[0], b[2]
    dx, dz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((p.x - ax) * dx + (p.z - az) * dz) / max(1e-9, dx * dx + dz * dz)))
    return math.hypot(p.x - (ax + t * dx), p.z - (az + t * dz))


def measure(sc, dom, glass, frames):
    """Per-frame liquid metrics from the baked liquid mesh."""
    lip = Vector(sc[TAG + "lip"])
    res = dict(front_speed=None, first_out=None, first_table=None, impact_xy=None, splash_z=0.0,
               splash_frame=None, spread_end=0.0, vol0=None, vol_on_table=0.0,
               vol_end=0.0, low_z=None, n_end=0)
    front = {}
    for fr in range(sc[TAG + "sim_start"], frames + 1):
        pts, vol = liquid_points(sc, dom, fr)
        if res["vol0"] is None and pts:
            res["vol0"] = vol
        res["vol_end"] = vol
        if not pts:
            continue
        gi = glass.matrix_world.inverted()
        outside = []
        for p in pts:
            q = gi @ p
            r = math.hypot(q.x + GLASS_R, q.y)
            if not (r < GLASS_R + 0.02 and -GLASS_H - 0.02 < q.z < 0.015):
                outside.append(p)
        if outside and res["first_out"] is None:
            res["first_out"] = fr
        if outside:
            front[fr] = min(p.z for p in outside)
        on_table = [p for p in outside if p.z < 0.02]
        if on_table and res["first_table"] is None:
            res["first_table"] = fr
            # measured speed of the falling front just before it lands
            if fr - 1 in front and fr - 2 in front:
                res["front_speed"] = (front[fr - 2] - front[fr - 1]) * FPS
            elif fr - 1 in front:     # left the glass and landed within ~1 frame
                res["front_speed"] = (front[fr - 1] - on_table[0].z) * FPS
            res["impact_xy"] = (sum(p.x for p in on_table) / len(on_table),
                                sum(p.y for p in on_table) / len(on_table))
        if res["impact_xy"] is not None:
            ix, iy = res["impact_xy"]
            imp = (ix, 0.0, 0.0)
            # splash = liquid thrown up away from the impact point and away from the falling stream
            far = [p for p in outside if math.hypot(p.x - ix, p.y - iy) > 0.06
                   and _seg_dist_xz(p, lip, imp) > 0.05]
            if far:
                z = max(p.z for p in far)
                if z > res["splash_z"]:
                    res["splash_z"], res["splash_frame"] = z, fr
        if fr == frames:
            res["n_end"] = len(pts)
            res["low_z"] = min(p.z for p in pts)
            if res["impact_xy"] is not None:
                ix, iy = res["impact_xy"]
                tbl = [p for p in outside if p.z < 0.03]
                if tbl:
                    res["spread_end"] = max(math.hypot(p.x - ix, p.y - iy) for p in tbl)
    return res


# =============================================================================
# main
# =============================================================================
def main():
    args = parse_args()
    base = base_dir(args)
    preview = args["preview"]
    res = PREVIEW_RESOLUTION if preview else RESOLUTION
    frames = round((PREVIEW_SECONDS if preview else SECONDS) * FPS)
    planets = args["planets"] or PLANETS
    out_root = resolve(OUTPUT_DIR, base)
    print(f"[water_pour] Blender {bpy.app.version_string}  base={base}  res={res}  frames={frames}")

    clear_previous()
    built = []
    for i, p in enumerate(planets, 1):
        sc, dom = build_scene(i, p, args, base, res, frames)
        out_dir = os.path.join(out_root, f"{i:02d}_{p}")
        setup_render(sc, preview, out_dir)
        built.append((sc, dom, p, out_dir))
        tmin, tmax = sc[TAG + "timesteps"]
        print(f"[water_pour] built {sc.name}: g={GRAVITY[p]}  timesteps {tmin}..{tmax}  "
              f"cfl={dom.modifiers['Fluid'].domain_settings.cfl_condition}")
    # make the first planet the active scene in the UI
    if bpy.context.window is not None:
        bpy.context.window.scene = built[0][0]

    report = {}
    if args["bake"] or args["render"] or preview:
        for sc, dom, p, out_dir in built:
            dt = bake(sc, dom)
            glass = next(o for o in sc.objects if o.name.startswith(TAG + "glass_"))
            m = measure(sc, dom, glass, frames)
            g = GRAVITY[p]
            lip_h = sc[TAG + "lip"][2]
            def sec(f):
                return None if f is None else round((f - 1) / FPS, 3)
            fall = None
            if m["first_out"] and m["first_table"]:
                fall = sec(m["first_table"]) - sec(m["first_out"])
            bowl_floor = BOWL_WALL
            report[p] = dict(
                g=g, bake_s=round(dt, 1),
                water_leaves_glass_s=sec(m["first_out"]),
                water_hits_bowl_s=sec(m["first_table"]),
                stream_fall_time_s=None if fall is None else round(fall, 3),
                front_speed_at_impact_ms=None if m["front_speed"] is None else round(m["front_speed"], 2),
                ideal_speed_after_free_fall_from_lip_ms=round(math.sqrt(2 * g * (lip_h - bowl_floor)), 2),
                splash_max_z_m=round(m["splash_z"], 3),
                splash_peak_s=sec(m["splash_frame"]),
                splash_rise_after_impact_s=(None if m["splash_frame"] is None or m["first_table"] is None
                                            else round((m["splash_frame"] - m["first_table"]) / FPS, 3)),
                spread_radius_end_m=round(m["spread_end"], 3),
            )
            r = report[p]
            print(f"[water_pour] {p:8s} g={g:7.2f} bake {r['bake_s']:6.1f}s | leaves glass {r['water_leaves_glass_s']}s"
                  f" | hits bowl {r['water_hits_bowl_s']}s (fall {r['stream_fall_time_s']}s)"
                  f" | front speed {r['front_speed_at_impact_ms']} m/s (free-fall from lip {r['ideal_speed_after_free_fall_from_lip_ms']})"
                  f" | splash top z {r['splash_max_z_m']} m, {r['splash_rise_after_impact_s']}s after impact")
            if r["splash_max_z_m"] > lip_h + 0.02:
                print(f"[water_pour] WARNING {p}: splash higher than the lip -> sim unstable, raise timesteps/lower CFL")
        os.makedirs(out_root, exist_ok=True)
        with open(os.path.join(out_root, "metrics_preview.json" if preview else "metrics.json"), "w") as fh:
            json.dump(report, fh, indent=2)

    if preview:
        pdir = os.path.join(out_root, "preview")
        os.makedirs(pdir, exist_ok=True)
        for sc, dom, p, out_dir in built:
            shots = [(min(PREVIEW_FRAME, sc.frame_end), f"{sc.name}.png")]
            hit = report.get(p, {}).get("water_hits_bowl_s")
            if p in PREVIEW_IMPACT_STILLS and hit is not None:     # extra still right after impact
                shots.append((min(sc.frame_end, 1 + round(hit * FPS) + 2), f"{sc.name}_impact.png"))
            for fr, name in shots:
                sc.frame_set(fr)
                sc.render.filepath = os.path.join(pdir, name)
                t = time.time()
                bpy.ops.render.render(write_still=True, scene=sc.name)
                print(f"[water_pour] preview still {sc.render.filepath} frame {fr} ({time.time() - t:.1f}s)")
    elif args["render"]:
        for sc, dom, p, out_dir in built:
            os.makedirs(out_dir, exist_ok=True)
            t = time.time()
            bpy.ops.render.render(animation=True, scene=sc.name)
            print(f"[water_pour] rendered {sc.name} -> {out_dir} ({time.time() - t:.0f}s)")
    print("[water_pour] done")


if __name__ == "__main__":
    main()
