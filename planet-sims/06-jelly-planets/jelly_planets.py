"""
JELLY ON EVERY PLANET  -  Blender procedural scene (planet-sims / 06)
=====================================================================
A glossy fluted raspberry jelly with a cherry on top is dropped onto a plate
under the REAL surface gravity of each planet.  Same jelly, same material
settings, only gravity (and solver substeps) change:
    Moon   -> slow drop, gentle jiggle
    Earth  -> normal wobble
    Jupiter-> hard squash
    Sun    -> SPLAT

The jelly is a Blender *cloth* shell with volume-preserving pressure and
internal springs (tested against the Soft Body modifier: soft body was far
slower here and sank through the plate, cloth+pressure stayed on the plate and
kept its volume).  Cloth gravity = scene.gravity x effector_weights.gravity, so
each planet scene gets its own scene.gravity and weight 1.0.

Run:
  * In Blender: Scripting tab -> open this file -> Run (builds all scenes,
    bakes them; pick a planet scene in the top bar and press play).
  * Headless full render:   blender -b -P jelly_planets.py -- --render
  * Headless quick preview: blender -b -P jelly_planets.py -- --preview
"""
import bpy
import bmesh
import math
import os
import sys
import time
from mathutils import Vector

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
PLANETS = ["Pluto", "Moon", "Mars", "Earth", "Jupiter", "Sun"]
FPS = 30
SECONDS = 5.0                 # length of each planet clip
HOLD_SECONDS = 0.5            # jelly hangs still before it is released
RESOLUTION = (1080, 1920)     # vertical 9:16
ENGINE = "EEVEE"              # "EEVEE" or "CYCLES"
CYCLES_SAMPLES = 128
EEVEE_SAMPLES = 64
RENDER = False                # render every planet animation (or pass --render)
PREVIEW = False               # low-res Cycles still per planet at max squash (or --preview)
PREVIEW_RES = (270, 480)
PREVIEW_SAMPLES = 24
OUTPUT_DIR = "//renders/jelly_planets/"   # relative to .blend (or script dir when unsaved)
HOOK_TEXT = "JELLY ON EVERY PLANET"
DROP_HEIGHT = 0.20            # m, gap between jelly bottom and plate at release
JELLY_COLOR = (0.85, 0.03, 0.10)   # raspberry
CHERRY = True

GRAVITY = {  # m/s^2 (shared planet-sims table)
    "Pluto": 0.62, "Moon": 1.62, "Mercury": 3.70, "Mars": 3.71, "Venus": 8.87,
    "Earth": 9.81, "Uranus": 8.69, "Neptune": 11.15, "Saturn": 10.44,
    "Jupiter": 24.79, "Sun": 274.0,
}

# pastel studio looks: backdrop colour, backdrop secondary (bands), text colour, world
LOOKS = {
    "Pluto":   dict(bg=(0.80, 0.74, 0.68), bg2=(0.62, 0.60, 0.72), text=(0.20, 0.17, 0.30), world=(0.30, 0.30, 0.42), emit=0.0),
    "Moon":    dict(bg=(0.62, 0.63, 0.67), bg2=(0.20, 0.21, 0.26), text=(0.06, 0.06, 0.10), world=(0.08, 0.08, 0.12), emit=0.0),
    "Mercury": dict(bg=(0.66, 0.62, 0.58), bg2=(0.45, 0.42, 0.40), text=(0.15, 0.12, 0.10), world=(0.2, 0.2, 0.2), emit=0.0),
    "Mars":    dict(bg=(0.93, 0.62, 0.45), bg2=(0.98, 0.80, 0.55), text=(0.35, 0.08, 0.03), world=(0.6, 0.4, 0.25), emit=0.0),
    "Venus":   dict(bg=(0.96, 0.88, 0.55), bg2=(0.90, 0.78, 0.45), text=(0.35, 0.25, 0.02), world=(0.6, 0.5, 0.3), emit=0.0),
    "Earth":   dict(bg=(0.62, 0.86, 0.70), bg2=(0.62, 0.80, 0.98), text=(0.04, 0.20, 0.25), world=(0.45, 0.6, 0.8), emit=0.0),
    "Uranus":  dict(bg=(0.65, 0.88, 0.90), bg2=(0.55, 0.80, 0.85), text=(0.05, 0.25, 0.30), world=(0.4, 0.6, 0.6), emit=0.0),
    "Neptune": dict(bg=(0.55, 0.65, 0.95), bg2=(0.45, 0.55, 0.90), text=(0.05, 0.08, 0.30), world=(0.3, 0.4, 0.7), emit=0.0),
    "Saturn":  dict(bg=(0.95, 0.85, 0.62), bg2=(0.90, 0.78, 0.55), text=(0.30, 0.20, 0.05), world=(0.6, 0.5, 0.35), emit=0.0),
    "Jupiter": dict(bg=(0.96, 0.78, 0.58), bg2=(0.86, 0.58, 0.40), text=(0.32, 0.12, 0.03), world=(0.6, 0.42, 0.28), emit=0.0),
    "Sun":     dict(bg=(1.00, 0.72, 0.22), bg2=(1.00, 0.92, 0.45), text=(0.35, 0.05, 0.00), world=(1.0, 0.55, 0.2), emit=1.2),
}

# --- jelly material physics (identical on every planet) ---
JELLY = dict(
    density=1050.0,           # kg/m^3 (gelatin dessert) -> cloth per-vertex mass = density*volume/verts
    stiffness=0.6,            # tension / compression
    shear=0.3,
    bending=0.15,
    internal=0.6,             # internal springs (gives the shell a "body")
    damping=0.0,              # spring damping (low = wobbly)
    air_damping=0.05,
    pressure_factor=4.0,      # pulls volume back to the rest volume
)
BASE_QUALITY = 10             # cloth substeps per frame at Earth gravity

TAG = "jelly_planets"         # custom property put on everything we create
PREFIX = "JP_"

# ----------------------------------------------------------------------------
# args
# ----------------------------------------------------------------------------
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--render" in argv:
    RENDER = True
if "--preview" in argv:
    PREVIEW = True
for a in argv:
    if a.startswith("--planets="):
        PLANETS = [p.strip().capitalize() for p in a.split("=", 1)[1].split(",") if p.strip()]

FRAME_START = 1
FRAME_END = int(round(SECONDS * FPS))
RELEASE_FRAME = FRAME_START + int(round(HOLD_SECONDS * FPS))


def out_root():
    if bpy.data.filepath:
        return bpy.path.abspath(OUTPUT_DIR)
    base = os.getcwd()
    try:
        if os.path.isfile(__file__):
            base = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        pass
    rel = OUTPUT_DIR[2:] if OUTPUT_DIR.startswith("//") else OUTPUT_DIR
    return os.path.join(base, rel)


# ----------------------------------------------------------------------------
# cleanup (idempotent re-runs)
# ----------------------------------------------------------------------------
def cleanup():
    keep = None
    for sc in list(bpy.data.scenes):
        if sc.get(TAG):
            if keep is None and len(bpy.data.scenes) == 1:
                keep = sc
            else:
                if bpy.context.window and bpy.context.window.scene == sc:
                    others = [s for s in bpy.data.scenes if not s.get(TAG)]
                    if others:
                        bpy.context.window.scene = others[0]
                    else:
                        tmp = bpy.data.scenes.new("Scene")
                        bpy.context.window.scene = tmp
                bpy.data.scenes.remove(sc)
    if keep is not None:  # can't delete the last scene
        tmp = bpy.data.scenes.new("Scene")
        if bpy.context.window:
            bpy.context.window.scene = tmp
        bpy.data.scenes.remove(keep)
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for idb in list(coll):
            if idb.get(TAG) or idb.name.startswith(PREFIX):
                try:
                    coll.remove(idb)
                except Exception:
                    pass


def tag(idb):
    idb[TAG] = True
    return idb


# ----------------------------------------------------------------------------
# materials
# ----------------------------------------------------------------------------
def bsdf_set(b, name, val):
    if name in b.inputs:
        b.inputs[name].default_value = val


def mat_principled(name, color, rough=0.4, metal=0.0, spec=0.5, coat=0.0, emission=None, estr=0.0):
    m = tag(bpy.data.materials.new(PREFIX + name))
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    bsdf_set(b, "Base Color", (*color, 1))
    bsdf_set(b, "Roughness", rough)
    bsdf_set(b, "Metallic", metal)
    bsdf_set(b, "Specular IOR Level", spec)
    bsdf_set(b, "Coat Weight", coat)
    if emission is not None:
        bsdf_set(b, "Emission Color", (*emission, 1))
        bsdf_set(b, "Emission Strength", estr)
    return m


def mat_jelly():
    m = tag(bpy.data.materials.new(PREFIX + "Jelly"))
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    c = JELLY_COLOR
    bsdf_set(b, "Base Color", (min(1, c[0] * 1.1), c[1] * 1.5 + 0.05, c[2] * 1.3 + 0.03, 1))
    bsdf_set(b, "Roughness", 0.04)
    bsdf_set(b, "IOR", 1.36)
    bsdf_set(b, "Transmission Weight", 1.0)
    bsdf_set(b, "Coat Weight", 0.4)
    bsdf_set(b, "Coat Roughness", 0.02)
    bsdf_set(b, "Subsurface Weight", 0.08)
    bsdf_set(b, "Subsurface Radius", (0.3, 0.05, 0.05))
    # coloured depth: volume absorption inside the jelly
    out = nt.nodes.get("Material Output")
    va = nt.nodes.new("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = (c[0], c[1] + 0.02, c[2] + 0.04, 1)
    va.inputs["Density"].default_value = 2.5
    nt.links.new(va.outputs[0], out.inputs["Volume"])
    # Eevee (Next) refraction
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    if hasattr(m, "use_raytrace_refraction"):
        m.use_raytrace_refraction = True
    if hasattr(m, "use_screen_refraction"):
        m.use_screen_refraction = True
    if hasattr(m, "thickness_mode"):
        m.thickness_mode = "SPHERE"
    return m


def mat_backdrop(look):
    m = tag(bpy.data.materials.new(PREFIX + "Backdrop"))
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    bsdf_set(b, "Roughness", 0.8)
    bsdf_set(b, "Specular IOR Level", 0.2)
    # soft bands (Jupiter-ish) / gentle gradient everywhere: mix bg and bg2 with a wave
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 0.35
    wave.inputs["Distortion"].default_value = 3.0
    wave.inputs["Detail"].default_value = 1.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*look["bg"], 1)
    ramp.color_ramp.elements[1].color = (*look["bg2"], 1)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 1.0
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    if look["emit"] > 0:
        nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"])
        bsdf_set(b, "Emission Strength", look["emit"])
    return m


def mat_text(color):
    m = tag(bpy.data.materials.new(PREFIX + "Text"))
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return m


# ----------------------------------------------------------------------------
# geometry
# ----------------------------------------------------------------------------
JELLY_R = 0.50
JELLY_H = 0.62
FLUTES = 8
SEG = 48


def jelly_profile():
    """(r, z, flute_amount) from bottom centre round to top centre (poles excluded)."""
    R, H = JELLY_R, JELLY_H
    pts = []
    # bottom disc (flat) -> rounded bottom edge
    for i in range(1, 6):
        t = i / 6
        pts.append((R * 0.94 * t, 0.0, t ** 2))
    pts.append((R * 0.985, 0.012, 1.0))
    # side: classic mould - slight bulge, tapering to a shoulder
    NSIDE = 15
    for i in range(NSIDE + 1):
        t = i / NSIDE
        z = 0.035 + t * (H - 0.11)
        r = R * (1.0 + 0.03 * math.sin(math.pi * min(1, t * 2.2)) - 0.30 * t ** 1.4)
        pts.append((r, z, 1.0))
    # rounded shoulder
    rt = pts[-1][0]
    zt = pts[-1][1]
    for i in range(1, 5):
        a = i / 5 * (math.pi / 2)
        pts.append((rt - 0.07 + 0.07 * math.cos(a), zt + 0.075 * math.sin(a), 1.0 - 0.15 * i / 5))
    # top crown (slightly domed)
    r0 = pts[-1][0]
    for i in range(1, 6):
        t = i / 6
        r = r0 * (1 - t)
        pts.append((r, H + 0.015 * (1 - (1 - t) ** 2), 0.85 * (1 - t) ** 1.5))
    return pts


def build_jelly_mesh(name):
    prof = jelly_profile()
    bm = bmesh.new()
    vbot = bm.verts.new((0, 0, 0))
    rings = []
    for (r, z, f) in prof:
        ring = []
        for i in range(SEG):
            a = 2 * math.pi * i / SEG
            # rounded flutes: cosine lobes
            fl = 1.0 + 0.075 * f * (0.5 + 0.5 * math.cos(FLUTES * a)) ** 1.5 - 0.03 * f
            ring.append(bm.verts.new((r * fl * math.cos(a), r * fl * math.sin(a), z)))
        rings.append(ring)
    vtop = bm.verts.new((0, 0, JELLY_H + 0.015))
    for i in range(SEG):
        j = (i + 1) % SEG
        bm.faces.new((vbot, rings[0][j], rings[0][i]))
        bm.faces.new((vtop, rings[-1][i], rings[-1][j]))
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(SEG):
            j = (i + 1) % SEG
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = tag(bpy.data.meshes.new(PREFIX + name))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    top_index = len(me.vertices) - 1
    return me, top_index


def build_lathe(name, prof, seg=96, close_center=True):
    """revolve (r,z) profile; first point at r=0 if close_center."""
    bm = bmesh.new()
    rings = []
    center = None
    for (r, z) in prof:
        if r == 0:
            center = bm.verts.new((0, 0, z))
            rings.append(None)
            continue
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            if a is None:
                bm.faces.new((center, b[i], b[j]))
            elif b is None:
                bm.faces.new((a[i], a[j], center))
            else:
                bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = tag(bpy.data.meshes.new(PREFIX + name))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


PLATE_TOP = 0.012   # visible plate surface sits on the (hidden) collider's outer shell


def plate_mesh():
    t = PLATE_TOP
    prof = [(0, t), (0.80, t), (0.92, t + 0.012), (1.02, t + 0.05), (1.08, t + 0.075), (1.10, t + 0.07),
            (1.06, t + 0.03), (0.95, t - 0.02), (0.70, t - 0.035), (0.68, t - 0.06), (0.62, t - 0.06),
            (0.60, t - 0.04), (0, t - 0.04)]
    return build_lathe("Plate", prof)


def backdrop_mesh():
    """curved studio cyclorama (floor that sweeps up into a wall)."""
    bm = bmesh.new()
    W = 14.0
    prof = []
    for i in range(10):
        prof.append((-8.0 + i * 0.8, -0.06))       # floor (y, z) toward camera is -y
    Rr = 2.5
    for i in range(1, 13):
        a = i / 12 * (math.pi / 2)
        prof.append((0.0 + Rr * math.sin(a), -0.06 + Rr * (1 - math.cos(a))))
    for i in range(1, 6):
        prof.append((Rr, -0.06 + Rr + i * 2.0))
    nx = 20
    grid = []
    for (y, z) in prof:
        grid.append([bm.verts.new((-W / 2 + W * i / nx, y + 2.0, z)) for i in range(nx + 1)])
    for k in range(len(grid) - 1):
        for i in range(nx):
            bm.faces.new((grid[k][i], grid[k][i + 1], grid[k + 1][i + 1], grid[k + 1][i]))
    me = tag(bpy.data.meshes.new(PREFIX + "Backdrop"))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def new_obj(sc, name, data):
    o = tag(bpy.data.objects.new(PREFIX + name, data))
    sc.collection.objects.link(o)
    return o


def add_text(sc, cam, body, size, z_frac, mat, focus, extrude=0.0, bold=0.0):
    cu = tag(bpy.data.curves.new(PREFIX + "Txt", "FONT"))
    cu.body = body
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    cu.extrude = extrude
    cu.offset = bold
    o = new_obj(sc, "Label", cu)
    o.data.materials.append(mat)
    o.parent = cam
    # place in the camera's focal plane (sharp under DOF); z_frac in [-0.5,0.5] of frame height
    half_h = focus * (cam.data.sensor_width / 2) / cam.data.lens
    o.location = (0, z_frac * 2 * half_h, -focus)
    o.visible_shadow = False
    if hasattr(o, "visible_diffuse"):
        o.visible_diffuse = False
        o.visible_glossy = True
        o.visible_transmission = False
    return o


# ----------------------------------------------------------------------------
# scene per planet
# ----------------------------------------------------------------------------
def pick_engine(want):
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    if want.upper().startswith("EEVEE"):
        for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            if e in items:
                return e
    return "CYCLES"


def setup_render(sc, preview):
    r = sc.render
    r.fps = FPS
    sc.frame_start = FRAME_START
    sc.frame_end = FRAME_END
    if preview:
        r.engine = "CYCLES"
        r.resolution_x, r.resolution_y = PREVIEW_RES
    else:
        r.engine = pick_engine(ENGINE)
        r.resolution_x, r.resolution_y = RESOLUTION
    r.resolution_percentage = 100
    r.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy" if not preview else "AgX - Punchy"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = PREVIEW_SAMPLES if preview else CYCLES_SAMPLES
    cy.use_denoising = True
    try:
        cy.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    cy.max_bounces = 12
    cy.transmission_bounces = 12
    cy.volume_bounces = 2
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    ee = getattr(sc, "eevee", None)
    if ee is not None:
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = EEVEE_SAMPLES
        for attr, val in (("use_raytracing", True), ("use_ssr", True), ("use_ssr_refraction", True),
                          ("use_gtao", True), ("use_shadows", True), ("use_soft_shadows", True)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass
    r.image_settings.file_format = "PNG"


def build_planet_scene(idx, planet, preview):
    g = GRAVITY[planet]
    look = LOOKS.get(planet, LOOKS["Earth"])
    sc = bpy.data.scenes.new(f"{idx:02d}_{planet}")
    sc[TAG] = True
    sc["planet"] = planet
    setup_render(sc, preview)
    sc.use_gravity = True
    sc.gravity = (0.0, 0.0, -g)

    # world
    w = tag(bpy.data.worlds.new(PREFIX + "World_" + planet))
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*look["world"], 1)
    bg.inputs["Strength"].default_value = 0.35
    sc.world = w

    # backdrop
    bd = new_obj(sc, "Backdrop", backdrop_mesh())
    bd.data.materials.append(mat_backdrop(look))

    # plate (visual) + collider
    plate = new_obj(sc, "Plate", plate_mesh())
    plate.data.materials.append(mat_principled("Porcelain", (0.92, 0.92, 0.95), rough=0.12, coat=0.6))
    bev = plate.modifiers.new("Sub", "SUBSURF")
    bev.levels = 1
    bev.render_levels = 2
    col_me = build_lathe("Collider", [(0, 0.0), (0.95, 0.0)], seg=48)
    col = new_obj(sc, "PlateCollider", col_me)
    col.hide_render = True
    col.display_type = "WIRE"
    col.modifiers.new("Collision", "COLLISION")
    cs = col.collision
    cs.thickness_outer = PLATE_TOP
    cs.thickness_inner = 0.2
    cs.cloth_friction = 15.0
    cs.damping = 0.1
    if hasattr(cs, "use_culling"):
        cs.use_culling = False

    # jelly
    me, top_idx = build_jelly_mesh("Jelly_" + planet)
    jel = new_obj(sc, "Jelly", me)
    jel.location = (0, 0, PLATE_TOP + DROP_HEIGHT)
    me.materials.append(mat_jelly())
    clm = jel.modifiers.new("Cloth", "CLOTH")
    s = clm.settings
    q = int(math.ceil(BASE_QUALITY * math.sqrt(max(g, 1.0) / 9.81)))
    q = max(BASE_QUALITY, min(80, q))
    s.quality = q
    bmv = bmesh.new()
    bmv.from_mesh(me)
    rest_vol = bmv.calc_volume()
    bmv.free()
    s.mass = JELLY["density"] * rest_vol / len(me.vertices)
    sc["jelly_mass_kg"] = JELLY["density"] * rest_vol
    s.tension_stiffness = s.compression_stiffness = JELLY["stiffness"]
    s.shear_stiffness = JELLY["shear"]
    s.bending_stiffness = JELLY["bending"]
    s.tension_damping = s.compression_damping = s.shear_damping = JELLY["damping"]
    s.bending_damping = 0.05
    s.air_damping = JELLY["air_damping"]
    s.use_internal_springs = True
    s.internal_spring_max_length = 0.0
    s.internal_spring_max_diversion = math.radians(45)
    s.internal_tension_stiffness = s.internal_compression_stiffness = JELLY["internal"]
    s.use_pressure = True
    s.uniform_pressure_force = 0.0
    s.use_pressure_volume = False      # target = rest volume of the mesh
    s.pressure_factor = JELLY["pressure_factor"]
    s.effector_weights.gravity = 1.0   # cloth gravity = scene.gravity x this
    s.vertex_group_mass = ""
    cc = clm.collision_settings
    cc.use_collision = True
    cc.distance_min = 0.006
    cc.collision_quality = 2 if g < 30 else 6
    cc.use_self_collision = False
    pc = clm.point_cache
    pc.frame_start = RELEASE_FRAME
    pc.frame_end = FRAME_END
    sub = jel.modifiers.new("Smooth", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2

    # cherry on top, parented to the jelly's top-centre vertex (follows the squash)
    if CHERRY:
        cm_ = bmesh.new()
        bmesh.ops.create_uvsphere(cm_, u_segments=32, v_segments=16, radius=0.085)
        for v in cm_.verts:  # little dimple at the stem
            if v.co.z > 0.07:
                v.co.z -= 0.012 * (v.co.z - 0.07) / 0.015
        cme = tag(bpy.data.meshes.new(PREFIX + "Cherry"))
        cm_.to_mesh(cme)
        cm_.free()
        for p in cme.polygons:
            p.use_smooth = True
        ch = new_obj(sc, "Cherry", cme)
        cme.materials.append(mat_principled("CherryMat", (0.55, 0.0, 0.03), rough=0.08, coat=1.0))
        ch.parent = jel
        ch.parent_type = "VERTEX"
        ch.parent_vertices = (top_idx, 0, 0)
        ch.location = (0, 0, 0.072)
        # stem
        cu = tag(bpy.data.curves.new(PREFIX + "Stem", "CURVE"))
        cu.dimensions = "3D"
        cu.bevel_depth = 0.006
        sp = cu.splines.new("BEZIER")
        sp.bezier_points.add(1)
        p0, p1 = sp.bezier_points
        p0.co = (0, 0, 0.06); p0.handle_left = (0, 0, 0.02); p0.handle_right = (0, 0.0, 0.11)
        p1.co = (0.05, 0.03, 0.19); p1.handle_left = (0.0, 0.02, 0.16); p1.handle_right = (0.08, 0.04, 0.21)
        stem = new_obj(sc, "Stem", cu)
        cu.materials.append(mat_principled("StemMat", (0.18, 0.12, 0.03), rough=0.5))
        stem.parent = ch

    # lights: big soft key, rim for glossy highlights, fill
    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = tag(bpy.data.lights.new(PREFIX + name, "AREA"))
        ld.energy = energy
        ld.size = size
        ld.color = color
        lo = new_obj(sc, name, ld)
        lo.location = loc
        d = Vector((0, 0, 0.35)) - Vector(loc)
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return lo
    area("Key", (-2.6, -2.8, 3.2), 900, 2.5, (1.0, 0.97, 0.93))
    area("Rim", (2.2, 2.6, 2.2), 900, 1.6, (1.0, 0.95, 1.0))
    area("Fill", (3.0, -3.0, 1.2), 250, 3.0, (0.92, 0.96, 1.0))
    area("Top", (0.0, 0.0, 4.0), 250, 2.0)
    if planet == "Sun":
        area("SunGlow", (0.0, 3.5, 1.5), 1200, 3.0, (1.0, 0.6, 0.2))

    # camera: macro-ish telephoto, slightly above, shallow DOF
    camd = tag(bpy.data.cameras.new(PREFIX + "Cam"))
    camd.lens = 70
    camd.sensor_width = 36
    camd.sensor_fit = "AUTO"
    cam = new_obj(sc, "Camera", camd)
    target = Vector((0, 0, 0.42))
    cam_loc = Vector((0, -6.4, 2.25))
    cam.location = cam_loc
    cam.rotation_euler = (target - cam_loc).to_track_quat("-Z", "Y").to_euler()
    focus = (target - cam_loc).length
    camd.dof.use_dof = True
    camd.dof.focus_distance = focus - 0.3
    camd.dof.aperture_fstop = 1.6
    # shift so the jelly sits in the lower half and the labels own the top third
    camd.shift_y = 0.16
    sc.camera = cam

    # labels (top third)
    tmat = mat_text(look["text"])
    add_text(sc, cam, f"{planet.upper()} · {g:g} m/s²", 0.25, 0.34, tmat, focus - 0.3, bold=0.012)
    add_text(sc, cam, HOOK_TEXT, 0.13, 0.43, tmat, focus - 0.3, bold=0.006)

    return sc, jel


# ----------------------------------------------------------------------------
# bake + measure
# ----------------------------------------------------------------------------
def bake_scene(sc, jel):
    t0 = time.time()
    ok = False
    try:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.ptcache.free_bake_all()
            res = bpy.ops.ptcache.bake_all(bake=True)
        ok = "FINISHED" in res
    except Exception as e:
        print("  bake op failed (%s); stepping frames instead" % e)
    if not ok:
        for f in range(FRAME_START, FRAME_END + 1):
            sc.frame_set(f)
    return time.time() - t0


def measure(sc, jel):
    dg = sc.view_layers[0].depsgraph
    rows = []
    for f in range(FRAME_START, FRAME_END + 1):
        sc.frame_set(f)
        e = jel.evaluated_get(dg)
        mw = e.matrix_world
        bm = bmesh.new()
        bm.from_mesh(e.to_mesh())
        bm.transform(mw)
        zs = [v.co.z for v in bm.verts]
        w = 2 * max(math.hypot(v.co.x, v.co.y) for v in bm.verts)
        vol = bm.calc_volume()
        bm.free()
        e.to_mesh_clear()
        rows.append(dict(f=f, zmin=min(zs), zmax=max(zs), h=max(zs) - min(zs), w=w, vol=vol))
    return rows


def analyse(planet, rows):
    r0 = rows[0]
    H0, W0, V0 = r0["h"], r0["w"], r0["vol"]
    # contact = first frame the bottom is within 1 cm of the plate shell
    contact = next((r for r in rows if r["zmin"] < PLATE_TOP + 0.02), None)
    cf = contact["f"] if contact else None
    post = [r for r in rows if cf and r["f"] >= cf]
    hmin_r = min(post or rows, key=lambda r: r["h"])
    wmax = max(r["w"] for r in rows)
    vols = [r["vol"] / V0 for r in post] or [1.0]
    tail = post[-int(FPS * 0.5):] if post else rows[-5:]
    hfin = sum(r["h"] for r in tail) / len(tail)
    # settle: last frame where |h - hfin| > 2% of rest height
    settle = None
    if post:
        last_big = cf
        for r in post:
            if abs(r["h"] - hfin) > 0.02 * H0:
                last_big = r["f"]
        settle = (last_big - cf) / FPS
    # wobble frequency from sign changes of (h - hfin) while amplitude is visible
    freq = None
    if post:
        sig = [r["h"] - hfin for r in post]
        xs = [i for i in range(1, len(sig)) if (sig[i - 1] > 0) != (sig[i] > 0) and
              max(abs(sig[i - 1]), abs(sig[i])) > 0.004 * H0]
        if len(xs) >= 3:
            freq = (len(xs) - 1) / 2 / ((xs[-1] - xs[0]) / FPS)
    return dict(planet=planet, g=GRAVITY[planet], H0=H0, contact=cf, hmin=hmin_r["h"],
                squash=hmin_r["h"] / H0, squash_frame=hmin_r["f"], hfinal=hfin / H0,
                wmax=wmax, spread=wmax / W0, settle=settle, freq=freq,
                vol_min=min(vols), vol_max=max(vols), tunnel=min(r["zmin"] for r in rows) < -0.01)


def print_table(results):
    print("\n=== JELLY RESULTS (rest height %.3f m) ===" % results[0]["H0"])
    print("%-8s %7s %7s %8s %8s %8s %8s %7s %8s %11s %s" % (
        "planet", "g", "contact", "min h", "squash", "final h", "max w", "spread", "settle", "wobble Hz", "volume range"))
    for r in results:
        print("%-8s %7.2f %7s %8.3f %8.2f %8.2f %8.3f %7.2f %8s %11s %.2f-%.2f%s" % (
            r["planet"], r["g"], r["contact"], r["hmin"], r["squash"], r["hfinal"], r["wmax"], r["spread"],
            "%.2fs" % r["settle"] if r["settle"] is not None else "-",
            "%.1f" % r["freq"] if r["freq"] else "-", r["vol_min"], r["vol_max"],
            "  TUNNEL!" if r["tunnel"] else ""))
    print()


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    t_all = time.time()
    cleanup()
    root = out_root()
    results = []
    scenes = []
    for i, planet in enumerate(PLANETS, start=1):
        if planet not in GRAVITY:
            print("unknown planet", planet)
            continue
        sc, jel = build_planet_scene(i, planet, PREVIEW and not RENDER)
        dt = bake_scene(sc, jel)
        rows = measure(sc, jel)
        res = analyse(planet, rows)
        res["bake_s"] = dt
        results.append(res)
        scenes.append((sc, res))
        print("baked %s in %.1fs (cloth quality %d)" % (sc.name, dt, jel.modifiers["Cloth"].settings.quality))
    print_table(results)

    # make the first planet scene active, drop the empty default scene
    for s in list(bpy.data.scenes):
        if not s.get(TAG) and not s.objects and len(bpy.data.scenes) > 1:
            if bpy.context.window and bpy.context.window.scene == s:
                bpy.context.window.scene = scenes[0][0]
            bpy.data.scenes.remove(s)
    if bpy.context.window and scenes:
        bpy.context.window.scene = scenes[0][0]

    if PREVIEW and not RENDER:
        pdir = os.path.join(root, "preview")
        os.makedirs(pdir, exist_ok=True)
        for sc, res in scenes:
            sc.frame_set(res["squash_frame"])
            sc.render.filepath = os.path.join(pdir, f"{sc.name}_f{res['squash_frame']:03d}.png")
            t0 = time.time()
            bpy.ops.render.render(write_still=True, scene=sc.name)
            print("preview", sc.render.filepath, "%.1fs" % (time.time() - t0))
    if RENDER:
        for sc, res in scenes:
            d = os.path.join(root, sc.name)
            os.makedirs(d, exist_ok=True)
            sc.render.filepath = os.path.join(d, "frame_")
            t0 = time.time()
            bpy.ops.render.render(animation=True, scene=sc.name)
            print("rendered", d, "%.0fs" % (time.time() - t0))
        print("renders in", root)
    print("total %.1fs" % (time.time() - t_all))


if not os.environ.get("JP_NO_MAIN"):
    main()
