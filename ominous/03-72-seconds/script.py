"""
OMINOUS #3 - 72 SECONDS
A radio telescope on a fogbound ridge at night. Days later, a printout under a
desk lamp. A line-printer column scrolls past; 6EQUJ5 is circled. "Wow!"
72 seconds. 1420 MHz. Searched again and again. Torn down in 1998.
The sky, still listening. One green blip.

Procedural only. Blender 4.2 - 5.x.
    blender -b -P script.py -- --render                  # full animation
    blender -b -P script.py -- --frames 1,120,300        # a few stills
    options: --out DIR  --percent N  --samples N  --start N --end N --step N  --skip-existing
Without the blender binary (bpy module):
    python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
"""

# ============================== CONFIG ======================================
CONFIG = dict(
    fps=24,
    duration_s=55.0,                  # 1320 frames
    resolution=(1080, 1920),
    resolution_percentage=53,         # -> 572x1017 (fast), set 100 for full
    engine="CYCLES",
    samples=8,
    denoise=True,
    output="//frames/f_",             # overridden by --out
    seed=1977,
)
ACCENT = (0.25, 1.0, 0.45)            # signal green (linear-ish)
OFFWHITE = (0.92, 0.91, 0.87)
FONT_TITLE = ["/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
              "/usr/share/fonts/opentype/inter/Inter-Light.otf"]
FONT_SUB = ["/usr/share/fonts/opentype/inter/Inter-Light.otf"]
FONT_HAND = ["/usr/share/fonts/opentype/inter/Inter-LightItalic.otf"]
FONT_MONO = ["/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
# ============================================================================

import sys, os, math, random
import bpy
import bmesh
from mathutils import Vector, Euler

FPS = CONFIG["fps"]
NFRAMES = int(round(CONFIG["duration_s"] * FPS))


_FOFF = 0   # frame offset applied to a block of beats (see TIMELINE)


def F(sec):
    """seconds -> frame number (frame 1 = t 0), plus the current block offset"""
    return int(round(sec * FPS)) + 1 + _FOFF


# ---------------------------------------------------------------- TIMELINE (55 s)
#  S1  0.00-8.29   hook, date, place                     (Cam,  wide ridge)
#  S2  8.29-14.29  "a few days later": printout + lamp   (CamDesk)
#  S3 14.29-25.38  printout reveal, 6EQUJ5, Wow!, 72 s   (Cam; beats authored on the
#                   v1 26 s timeline and shifted +138 frames = 5.75 s, via _FOFF)
#  S4 25.38-31.50  narrowband, 1420 MHz, hydrogen line   (Cam2)
#  S5 31.50-38.50  searched again; VLA 1995/96; nothing  (Cam2, sky turning)
#  S6 38.50-44.50  1998: torn down for a golf course     (Cam2, dish dissolves)
#  S7 44.50-55.00  empty ridge, tilt to the sky, still listening, one blip, black
FR_S2, FR_S3, FR_S4 = 200, 344, 610
S3_OFF = 138
T_S4 = (FR_S4 - 1) / 24.0
T_S5, T_S6, T_S7 = 31.5, 38.5, 44.5
T_CUT = 54.6


# ---------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ARGS = {"end": None, "skip": False, "start": None, "step": None, "render": False, "frames": None, "out": None, "percent": None, "samples": None}
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--render":
        ARGS["render"] = True
    elif a == "--frames":
        ARGS["frames"] = [int(x) for x in argv[i + 1].split(",")]; i += 1
    elif a == "--out":
        ARGS["out"] = argv[i + 1]; i += 1
    elif a == "--percent":
        ARGS["percent"] = int(argv[i + 1]); i += 1
    elif a == "--skip-existing":
        ARGS["skip"] = True
    elif a == "--end":
        ARGS["end"] = int(argv[i + 1]); i += 1
    elif a == "--start":
        ARGS["start"] = int(argv[i + 1]); i += 1
    elif a == "--step":
        ARGS["step"] = int(argv[i + 1]); i += 1
    elif a == "--samples":
        ARGS["samples"] = int(argv[i + 1]); i += 1
    i += 1

random.seed(CONFIG["seed"])
V5 = bpy.app.version >= (5, 0, 0)

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = NFRAMES
scene.render.fps = FPS


def load_font(paths):
    for p in paths:
        if os.path.exists(p):
            try:
                return bpy.data.fonts.load(p, check_existing=True)
            except Exception:
                pass
    return None  # Blender built-in font


def use_nodes(idb):
    try:
        if not idb.use_nodes:
            idb.use_nodes = True
    except Exception:
        pass


def key_socket(sock, frame, value):
    sock.default_value = value
    sock.keyframe_insert("default_value", frame=frame)


# ---------------------------------------------------------------- materials
def mat_emit_fade(name, color, strength=1.0):
    """Emission mixed with transparency; returns (mat, fac socket). fac 1 = visible."""
    m = bpy.data.materials.new(name)
    use_nodes(m)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    mix.inputs[0].default_value = 0.0
    return m, mix.inputs[0], em


VANISH = []   # mix factors that dissolve the telescope (S6)


def mat_diffuse(name, color, rough=0.6, metallic=0.0, vanish=False):
    m = bpy.data.materials.new(name)
    use_nodes(m)
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if vanish:
        nt = m.node_tree
        out = nt.nodes.get("Material Output")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(b.outputs[0], mx.inputs[1])
        nt.links.new(tr.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
        mx.inputs[0].default_value = 0.0
        VANISH.append(mx.inputs[0])
    return m


# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("Night")
scene.world = world
use_nodes(world)
wn = world.node_tree
wn.nodes.clear()
wout = wn.nodes.new("ShaderNodeOutputWorld")
tc = wn.nodes.new("ShaderNodeTexCoord")
sep = wn.nodes.new("ShaderNodeSeparateXYZ")
wn.links.new(tc.outputs["Generated"], sep.inputs[0])
# vertical gradient (z of view direction)
ramp = wn.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.030, 0.040, 0.045, 1)   # horizon glow
ramp.color_ramp.elements[1].position = 0.45
ramp.color_ramp.elements[1].color = (0.0025, 0.0035, 0.0055, 1)  # zenith
wn.links.new(sep.outputs["Z"], ramp.inputs[0])
# stars: voronoi points on the view direction
vor = wn.nodes.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 300.0
try:
    vor.inputs["Randomness"].default_value = 1.0
except Exception:
    pass
# the sky can turn (S5: nights passing) about a tilted pole (~40 deg N, Ohio)
srot = wn.nodes.new("ShaderNodeVectorRotate")
srot.rotation_type = "AXIS_ANGLE"
srot.inputs["Axis"].default_value = (0.0, 0.77, 0.64)
srot.inputs["Angle"].default_value = 0.0
wn.links.new(tc.outputs["Generated"], srot.inputs["Vector"])
wn.links.new(srot.outputs[0], vor.inputs["Vector"])
star_mr = wn.nodes.new("ShaderNodeMapRange")
star_mr.inputs["From Min"].default_value = 0.0
star_mr.inputs["From Max"].default_value = 0.075
star_mr.inputs["To Min"].default_value = 1.0
star_mr.inputs["To Max"].default_value = 0.0
wn.links.new(vor.outputs["Distance"], star_mr.inputs[0])
# random brightness: keep only some voronoi cells as stars
bright = wn.nodes.new("ShaderNodeSeparateColor") if hasattr(bpy.types, "ShaderNodeSeparateColor") else wn.nodes.new("ShaderNodeSeparateRGB")
wn.links.new(vor.outputs["Color"], bright.inputs[0])
thr = wn.nodes.new("ShaderNodeMapRange")
thr.inputs["From Min"].default_value = 0.80
thr.inputs["From Max"].default_value = 1.0
thr.inputs["To Min"].default_value = 0.0
thr.inputs["To Max"].default_value = 1.0
wn.links.new(bright.outputs[0], thr.inputs[0])
pw = wn.nodes.new("ShaderNodeMath"); pw.operation = "POWER"
pw.inputs[1].default_value = 3.0
wn.links.new(thr.outputs[0], pw.inputs[0])
m1 = wn.nodes.new("ShaderNodeMath"); m1.operation = "MULTIPLY"
wn.links.new(star_mr.outputs[0], m1.inputs[0])
wn.links.new(pw.outputs[0], m1.inputs[1])
# stars fade toward horizon (haze)
hz = wn.nodes.new("ShaderNodeMapRange")
hz.inputs["From Min"].default_value = 0.02
hz.inputs["From Max"].default_value = 0.35
wn.links.new(sep.outputs["Z"], hz.inputs[0])
m2 = wn.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
wn.links.new(m1.outputs[0], m2.inputs[0])
wn.links.new(hz.outputs[0], m2.inputs[1])
m3 = wn.nodes.new("ShaderNodeMath"); m3.operation = "MULTIPLY"
m3.inputs[1].default_value = 7.0
wn.links.new(m2.outputs[0], m3.inputs[0])
addc = wn.nodes.new("ShaderNodeMixRGB") if not hasattr(bpy.types, "ShaderNodeMix") else None
# combine: color = gradient + stars*starcolor
star_col = wn.nodes.new("ShaderNodeCombineXYZ")
wn.links.new(m3.outputs[0], star_col.inputs[0])
wn.links.new(m3.outputs[0], star_col.inputs[1])
m4 = wn.nodes.new("ShaderNodeMath"); m4.operation = "MULTIPLY"
m4.inputs[1].default_value = 1.08
wn.links.new(m3.outputs[0], m4.inputs[0])
wn.links.new(m4.outputs[0], star_col.inputs[2])
vadd = wn.nodes.new("ShaderNodeVectorMath"); vadd.operation = "ADD"
wn.links.new(ramp.outputs["Color"], vadd.inputs[0])
wn.links.new(star_col.outputs[0], vadd.inputs[1])
bg = wn.nodes.new("ShaderNodeBackground")
bg.inputs["Strength"].default_value = 1.0
wn.links.new(vadd.outputs[0], bg.inputs["Color"])
wn.links.new(bg.outputs[0], wout.inputs["Surface"])

# ---------------------------------------------------------------- terrain (ridge)
def build_ridge():
    n = 160
    size = 900.0
    mesh = bpy.data.meshes.new("Ridge")
    bm = bmesh.new()
    verts = []
    rnd = random.Random(7)
    ph = [rnd.uniform(0, 6.28) for _ in range(8)]
    for j in range(n + 1):
        row = []
        for i2 in range(n + 1):
            x = (i2 / n - 0.5) * size
            y = (j / n - 0.5) * size
            # ridge along x, crest near y=0, gently undulating
            crest = 6.0 * math.sin(x * 0.012 + ph[0]) + 3.0 * math.sin(x * 0.031 + ph[1])
            d = (y - crest)
            z = -0.0022 * d * d - 0.00002 * abs(d) ** 3
            z += 2.0 * math.sin(x * 0.02 + ph[2]) * math.exp(-abs(d) / 80)
            z += 0.6 * math.sin(x * 0.11 + y * 0.07 + ph[3]) + 0.35 * math.sin(x * 0.23 - y * 0.19 + ph[4])
            z = max(z, -70.0)
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)
    for j in range(n):
        for i2 in range(n):
            bm.faces.new((verts[j][i2], verts[j][i2 + 1], verts[j + 1][i2 + 1], verts[j + 1][i2]))
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("Ridge", mesh)
    scene.collection.objects.link(ob)
    ob.data.materials.append(mat_diffuse("Ground", (0.012, 0.014, 0.013), rough=0.95))
    return ob


ridge = build_ridge()


def ground_z(x, y):
    # sample the analytic function again (approx; good enough for placement)
    return 0.0


# ---------------------------------------------------------------- the dish
metal = mat_diffuse("DishMetal", (0.32, 0.34, 0.35), rough=0.55, metallic=0.25, vanish=True)
dark_metal = mat_diffuse("DarkMetal", (0.05, 0.055, 0.06), rough=0.6, metallic=0.3, vanish=True)


def cyl_between(name, a, b, r, mat, verts=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length,
                                        location=(a + b) / 2)
    ob = bpy.context.active_object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    ob.data.materials.append(mat)
    return ob


def build_dish():
    R, f = 13.0, 6.5                        # 26 m dish, focal length 6.5 m
    rings, segs = 22, 72
    mesh = bpy.data.meshes.new("Reflector")
    bm = bmesh.new()
    grid = []
    for r_i in range(rings + 1):
        r = R * (r_i / rings)
        row = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            x, y = r * math.cos(a), r * math.sin(a)
            row.append(bm.verts.new((x, y, r * r / (4 * f))))
            if r_i == 0:
                break
        grid.append(row)
    for s in range(segs):
        bm.faces.new((grid[0][0], grid[1][s], grid[1][(s + 1) % segs]))
    for r_i in range(1, rings):
        for s in range(segs):
            bm.faces.new((grid[r_i][s], grid[r_i + 1][s], grid[r_i + 1][(s + 1) % segs], grid[r_i][(s + 1) % segs]))
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    dish = bpy.data.objects.new("Reflector", mesh)
    scene.collection.objects.link(dish)
    dish.data.materials.append(metal)
    sol = dish.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.12
    parts = [dish]
    zr = R * R / (4 * f)
    # rim
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=0.18, major_segments=72,
                                     minor_segments=6, location=(0, 0, zr))
    rim = bpy.context.active_object; rim.data.materials.append(dark_metal); parts.append(rim)
    # back ribs
    for k in range(16):
        a = 2 * math.pi * k / 16
        pts = []
        for t in range(9):
            r = 1.2 + (R - 1.2) * t / 8
            z = r * r / (4 * f) - 0.25 - 1.6 * (1 - t / 8)
            pts.append((r * math.cos(a), r * math.sin(a), z))
        for t in range(8):
            parts.append(cyl_between("rib", pts[t], pts[t + 1], 0.09, dark_metal, 5))
        parts.append(cyl_between("ribstrut", pts[4], (pts[4][0], pts[4][1], pts[4][2] + 1.1), 0.05, dark_metal, 4))
    # hub
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.8, depth=2.2, location=(0, 0, -1.0))
    hub = bpy.context.active_object; hub.data.materials.append(dark_metal); parts.append(hub)
    # quadripod to feed
    focus = (0, 0, f)
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        p = (R * 0.93 * math.cos(a), R * 0.93 * math.sin(a), (R * 0.93) ** 2 / (4 * f))
        parts.append(cyl_between("leg", p, focus, 0.11, dark_metal, 6))
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.7, depth=1.6, location=(0, 0, f + 0.5))
    feed = bpy.context.active_object; feed.data.materials.append(dark_metal); parts.append(feed)
    # join into one object, origin at focal-axis base
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = dish
    bpy.ops.object.join()
    dish = bpy.context.active_object
    return dish, f


dish, FOCAL = build_dish()
# mount: elevation axis on top of a pedestal
PED_H = 11.0
mount = bpy.data.objects.new("ElevAxis", None)
scene.collection.objects.link(mount)
mount.location = (0, 0, PED_H + 1.5)
dish.parent = mount
dish.location = (0, 0, 2.2)
EL = math.radians(58)      # elevation of dish axis above horizon
AZ = math.radians(132)     # dish faces up and away-left
mount.rotation_euler = Euler((0, math.pi / 2 - EL, AZ), "XYZ")

# pedestal & yoke
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=3.6, radius2=1.8, depth=PED_H, location=(0, 0, PED_H / 2 - 1.0))
ped = bpy.context.active_object; ped.data.materials.append(dark_metal)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, PED_H))
yk = bpy.context.active_object; yk.scale = (3.6, 3.6, 1.2); yk.data.materials.append(dark_metal)
yk.rotation_euler = (0, 0, AZ)
for s in (-1, 1):
    side = Vector((math.cos(AZ + math.pi / 2), math.sin(AZ + math.pi / 2), 0)) * 2.4 * s
    cyl_between("yokearm", (side.x, side.y, PED_H), (side.x, side.y, PED_H + 2.6), 0.45, dark_metal, 6)

# aviation light at feed tip (world position from mount transform)
bpy.context.view_layer.update()
# red obstruction light on the highest point of the rim (visible from behind the dish)
_R = 13.0
_cands = [dish.matrix_world @ Vector((_R * 1.02 * math.cos(a), _R * 1.02 * math.sin(a), _R * _R / (4 * FOCAL) + 0.35))
          for a in [2 * math.pi * k / 90 for k in range(90)]]
feed_world = max(_cands, key=lambda v: v.z)
red_mat, red_fac, red_em = mat_emit_fade("AvLight", (1.0, 0.05, 0.02), 40.0)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.28, segments=12, ring_count=8, location=feed_world)
avl = bpy.context.active_object; avl.data.materials.append(red_mat)
# halo billboard
halo_m = bpy.data.materials.new("Halo"); use_nodes(halo_m)
hn = halo_m.node_tree; hn.nodes.clear()
ho = hn.nodes.new("ShaderNodeOutputMaterial")
htc = hn.nodes.new("ShaderNodeTexCoord")
hgr = hn.nodes.new("ShaderNodeTexGradient"); hgr.gradient_type = "SPHERICAL"
hn.links.new(htc.outputs["Object"], hgr.inputs[0])
hp = hn.nodes.new("ShaderNodeMath"); hp.operation = "POWER"; hp.inputs[1].default_value = 3.0
hn.links.new(hgr.outputs[0], hp.inputs[0])
hm = hn.nodes.new("ShaderNodeMath"); hm.operation = "MULTIPLY"
hn.links.new(hp.outputs[0], hm.inputs[0])
halo_amt = hm.inputs[1]
hem = hn.nodes.new("ShaderNodeEmission"); hem.inputs["Color"].default_value = (1.0, 0.08, 0.04, 1)
hem.inputs["Strength"].default_value = 3.0
htr = hn.nodes.new("ShaderNodeBsdfTransparent")
hmix = hn.nodes.new("ShaderNodeMixShader")
hn.links.new(hm.outputs[0], hmix.inputs[0])
hn.links.new(htr.outputs[0], hmix.inputs[1])
hn.links.new(hem.outputs[0], hmix.inputs[2])
hn.links.new(hmix.outputs[0], ho.inputs["Surface"])
bpy.ops.mesh.primitive_plane_add(size=9.0, location=feed_world)
halo = bpy.context.active_object; halo.data.materials.append(halo_m)
halo.visible_shadow = False if hasattr(halo, "visible_shadow") else None
try:
    halo.visible_shadow = False; halo.visible_diffuse = False; halo.visible_glossy = False
    avl.visible_shadow = False
except Exception:
    pass

# ---------------------------------------------------------------- moon light
bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
moon = bpy.context.active_object
moon.data.energy = 1.1
moon.data.color = (0.62, 0.72, 0.85)
moon.data.angle = math.radians(1.5)
moon.rotation_euler = Euler((math.radians(64), 0, math.radians(200)), "XYZ")

# ---------------------------------------------------------------- cameras
def new_cam(name, lens=35):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_fit = "AUTO"
    cd.sensor_width = 36
    cd.clip_start = 0.02
    cd.clip_end = 3000
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    return ob


cam = new_cam("Cam")
camD = new_cam("CamDesk", 45)
cam2 = new_cam("Cam2")
scene.camera = cam
for fr, c in [(1, cam), (FR_S2, camD), (FR_S3, cam), (FR_S4, cam2)]:
    mk = scene.timeline_markers.new("shot%d" % fr, frame=fr)
    mk.camera = c


def cam_key(c, frame, loc, look, lens=None, roll=0.0):
    c.location = Vector(loc)
    d = Vector(look) - Vector(loc)
    q = d.to_track_quat("-Z", "Y")
    e = q.to_euler("XYZ")
    e.rotate_axis("Z", roll)
    c.rotation_euler = e
    c.keyframe_insert("location", frame=frame)
    c.keyframe_insert("rotation_euler", frame=frame)
    if lens:
        c.data.lens = lens
        c.data.keyframe_insert("lens", frame=frame)


# S1 shot A 0.0 - 8.3 s : wide, low, slow push in
cam_key(cam, F(0.0), (-34, -96, 3.0), (2, 0, 15.5), 32)
cam_key(cam, F(8.4), (-27, -80, 2.4), (2, 0, 15.0), 34)
# S3 shot B (v1 times, shifted): under the dish, looking up
cam_key(cam, F(8.45) + S3_OFF, (-19, -38, 3.5), (0, 0, 17), 30)
cam_key(cam, F(22.3) + S3_OFF, (-12, -30, 4.5), (0, 0, 18.5), 30)
# S4: in front of the reflector, looking into the bowl
cam_key(cam2, F(T_S4), (-44, 30, 1.0), (0, 0, 19), 26)
cam_key(cam2, F(T_S5) - 1, (-39, 25, 1.5), (0, 0, 19.5), 27)
# S5: side-on, sky turning behind
cam_key(cam2, F(T_S5), (70, -62, 0.0), (0, 0, 16), 28)
cam_key(cam2, F(T_S6) - 1, (64, -57, 0.5), (0, 0, 16), 28)
# S6: wide again (as the opening), the dish dissolves
cam_key(cam2, F(T_S6), (-40, -112, 3.0), (2, 0, 14.5), 32)
cam_key(cam2, F(T_S7) - 1, (-36, -104, 2.8), (2, 0, 14.5), 33)
# S7: from the empty ridge top, tilt up into the sky
cam_key(cam2, F(T_S7), (-6, -24, 1.0), (40, 160, 30), 24)
cam_key(cam2, F(51.5), (-6, -24, 1.5), (34, 140, 80), 24)
cam_key(cam2, F(55.0), (-6, -24, 1.5), (33, 136, 86), 24)

# moon off while we're indoors (S2)
for fr, en in [(1, 1.1), (FR_S2 - 1, 1.1), (FR_S2, 0.0), (FR_S3 - 1, 0.0), (FR_S3, 1.1)]:
    moon.data.energy = en
    moon.data.keyframe_insert("energy", frame=fr)

# sky rotation during S5 (time-lapse: nights pass), slow drift after
for fr, ang in [(1, 0.0), (F(T_S5), 0.0), (F(T_S6) - 1, 0.55), (F(55.0), 0.62)]:
    key_socket(srot.inputs["Angle"], fr, ang)

# telescope dissolves (S6); stays gone
for fv in VANISH:
    key_socket(fv, 1, 0.0)
    key_socket(fv, F(40.6), 0.0)
    key_socket(fv, F(43.4), 1.0)
    key_socket(fv, F(55.0), 1.0)

# ---------------------------------------------------------------- desk set (S2), far from the ridge
DX = Vector((3000.0, 0.0, 0.0))


def desk_set():
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=DX)
    desk = bpy.context.active_object
    desk.data.materials.append(mat_diffuse("Desk", (0.022, 0.02, 0.018), rough=0.75))
    paper_m = mat_diffuse("Paper", (0.50, 0.50, 0.47), rough=0.92)
    ink_m = mat_diffuse("Ink", (0.025, 0.025, 0.03), rough=0.7)
    hole_m = mat_diffuse("Hole", (0.01, 0.01, 0.01), rough=0.9)
    # an older sheet underneath, skewed
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=DX + Vector((0.03, 0.05, 0.0008)))
    under = bpy.context.active_object
    under.scale = (0.40, 1.6, 1); under.rotation_euler = (0, 0, math.radians(-4))
    under.data.materials.append(paper_m)
    # the fanfold strip being read
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=DX + Vector((0, 0, 0.0016)))
    paper = bpy.context.active_object
    paper.scale = (0.38, 1.6, 1)
    paper.data.materials.append(paper_m)
    # tractor-feed holes along both edges
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.0022, depth=0.0004,
                                            location=DX + Vector((sx * 0.178, -0.78, 0.0019)))
        h = bpy.context.active_object
        h.data.materials.append(hole_m)
        arr = h.modifiers.new("arr", "ARRAY")
        arr.count = 123
        arr.use_relative_offset = False
        arr.use_constant_offset = True
        arr.constant_offset_displace = (0, 0.0127, 0)
    # printed rows: 16 channels, same noise statistics as the overlay
    prnd = random.Random(77)
    nch, tgt = 16, 2
    rows_d = []
    for r_ in range(70):
        ch = []
        for _ in range(nch):
            v = prnd.random()
            ch.append(" " if v < 0.55 else ("1" if v < 0.88 else ("2" if v < 0.97 else "3")))
        rows_d.append(ch)
    tgt_row = 52
    for k, c in enumerate("6EQUJ5"):
        rows_d[tgt_row + k][tgt] = c
        rows_d[tgt_row + k][tgt - 1] = " "
        rows_d[tgt_row + k][tgt + 1] = " "
    pitch = 0.0185
    y0 = 0.70
    for r_, ch in enumerate(rows_d):
        cu = bpy.data.curves.new("prow", "FONT")
        cu.body = " ".join(ch)
        if font_mono_desk:
            cu.font = font_mono_desk
        cu.size = 0.0125
        cu.align_x = "LEFT"
        cu.materials.append(ink_m)
        ob = bpy.data.objects.new("prow", cu)
        scene.collection.objects.link(ob)
        ob.location = DX + Vector((-0.15, y0 - r_ * pitch, 0.0021))
    # a pen lying across the sheet
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.0045, depth=0.14,
                                        location=DX + Vector((0.13, -0.33, 0.0065)))
    pen = bpy.context.active_object
    pen.rotation_euler = (math.radians(90), 0, math.radians(62))
    pen.data.materials.append(mat_diffuse("Pen", (0.015, 0.015, 0.017), rough=0.35))
    # desk lamp: a warm, tight pool
    bpy.ops.object.light_add(type="SPOT", location=DX + Vector((-0.30, 0.10, 0.62)))
    lamp = bpy.context.active_object
    lamp.data.energy = 5.0
    lamp.data.color = (1.0, 0.86, 0.70)
    lamp.data.spot_size = math.radians(95)
    lamp.data.spot_blend = 0.85
    lamp.data.shadow_soft_size = 0.05
    d = (DX + Vector((0.0, -0.12, 0))) - lamp.location
    lamp.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return tgt_row, y0, pitch


font_mono_desk = load_font(FONT_MONO)
_tr, _y0, _pt = desk_set()
y_word = _y0 - (_tr + 2.5) * _pt          # middle of 6EQUJ5 on the sheet
focus = bpy.data.objects.new("DeskFocus", None)
scene.collection.objects.link(focus)
camD.data.dof.use_dof = True
camD.data.dof.focus_distance = 0.345   # fixed: sheet centre ~0.36 m, titles at 0.33 m
camD.data.dof.aperture_fstop = 2.8
# slide down the sheet, ending on the column that holds 6EQUJ5
for fr, lk, off in [(F(8.29), 0.24, (0.10, -0.20, 0.30)), (F(14.3), y_word + 0.02, (0.08, -0.19, 0.29))]:
    look = DX + Vector((-0.06, lk, 0.0))
    focus.location = look
    focus.keyframe_insert("location", frame=fr)
    cam_key(camD, fr, look + Vector(off), look, 45)

# ---------------------------------------------------------------- fake fog
def fog_plane(name, loc, rot_z, w, h, density, color, speed, scale, seed, lift=0.0):
    m = bpy.data.materials.new(name); use_nodes(m)
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tcn = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tcn.outputs["Object"], mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (w * scale, h * scale * 2.2, w * scale)
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "3D"
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 2.0
    nz.inputs["Roughness"].default_value = 0.55
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    nmr = nt.nodes.new("ShaderNodeMapRange")
    nmr.inputs["From Min"].default_value = 0.42
    nmr.inputs["From Max"].default_value = 0.72
    nt.links.new(nz.outputs["Fac"], nmr.inputs[0])
    # vertical falloff (object local y: -1 bottom .. +1 top for plane)
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tcn.outputs["Generated"], sp.inputs[0])
    vmr = nt.nodes.new("ShaderNodeMapRange")
    vmr.inputs["From Min"].default_value = 1.0
    vmr.inputs["From Max"].default_value = 0.15 + lift
    vmr.interpolation_type = "SMOOTHSTEP"
    nt.links.new(sp.outputs["Y"], vmr.inputs[0])
    # soft side edges
    emr = nt.nodes.new("ShaderNodeMapRange")
    emr.inputs["From Min"].default_value = 0.0
    emr.inputs["From Max"].default_value = 0.15
    absx = nt.nodes.new("ShaderNodeMath"); absx.operation = "SUBTRACT"
    absx.inputs[0].default_value = 0.5
    nt.links.new(sp.outputs["X"], absx.inputs[1])
    absx2 = nt.nodes.new("ShaderNodeMath"); absx2.operation = "ABSOLUTE"
    nt.links.new(absx.outputs[0], absx2.inputs[0])
    edge = nt.nodes.new("ShaderNodeMath"); edge.operation = "SUBTRACT"
    edge.inputs[0].default_value = 0.5
    nt.links.new(absx2.outputs[0], edge.inputs[1])
    nt.links.new(edge.outputs[0], emr.inputs[0])
    a1 = nt.nodes.new("ShaderNodeMath"); a1.operation = "MULTIPLY"
    nt.links.new(nmr.outputs[0], a1.inputs[0]); nt.links.new(vmr.outputs[0], a1.inputs[1])
    a2 = nt.nodes.new("ShaderNodeMath"); a2.operation = "MULTIPLY"
    nt.links.new(a1.outputs[0], a2.inputs[0]); nt.links.new(emr.outputs[0], a2.inputs[1])
    a3 = nt.nodes.new("ShaderNodeMath"); a3.operation = "MULTIPLY"
    a3.inputs[1].default_value = density
    nt.links.new(a2.outputs[0], a3.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(a3.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    # drift
    # drift: x slides, z (depth in noise space) evolves the shapes slowly
    mp.inputs["Location"].default_value = (seed, 0, seed * 0.7)
    mp.inputs["Location"].keyframe_insert("default_value", frame=1)
    mp.inputs["Location"].default_value = (seed + speed * CONFIG["duration_s"], 0,
                                           seed * 0.7 + 0.012 * CONFIG["duration_s"])
    mp.inputs["Location"].keyframe_insert("default_value", frame=NFRAMES)
    # linear interpolation for drift
    try:
        ad = m.node_tree.animation_data
        if ad and ad.action:
            fcs = getattr(ad.action, "fcurves", None)
            if fcs is not None:
                for fc in fcs:
                    for kp in fc.keyframe_points:
                        kp.interpolation = "LINEAR"
    except Exception:
        pass
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (w, h, 1)
    ob.rotation_euler = (math.pi / 2, 0, rot_z)
    ob.data.materials.append(m)
    try:
        ob.visible_shadow = False; ob.visible_diffuse = False; ob.visible_glossy = False
    except Exception:
        pass
    return ob


FOG = (0.105, 0.125, 0.135)
# planes face roughly toward -y (camera side); ordered far -> near
fog_plane("FogFar", (20, 110, 6), 0.0, 900, 60, 1.0, (0.12, 0.15, 0.16), 0.05, 0.016, 1.0, lift=0.10)
fog_plane("FogBehind", (5, 22, 2), 0.0, 520, 30, 0.95, (0.22, 0.26, 0.27), 0.09, 0.030, 3.0)
fog_plane("FogMid", (0, -18, -4), 0.0, 420, 20, 0.85, (0.17, 0.20, 0.21), -0.12, 0.040, 5.0)
fog_plane("FogNear", (-20, -70, -15), 0.0, 520, 34, 0.9, (0.13, 0.155, 0.165), 0.08, 0.026, 7.0, lift=0.05)

# ---------------------------------------------------------------- overlay rig (camera-parented)
DEPTH = 3.0
VIS_H = DEPTH * 36.0 / 30.0         # visible height at DEPTH for the smallest lens used (approx)

def make_rig(c, name, depth=DEPTH):
    rg = bpy.data.objects.new(name, None)
    scene.collection.objects.link(rg)
    rg.parent = c
    rg.location = (0, 0, -depth)
    k = depth / DEPTH                 # same apparent size at any depth
    rg.scale = (k, k, k)
    return rg


rig = make_rig(cam, "OverlayRig")
rigD = make_rig(camD, "OverlayRigDesk", 0.33)   # on the focus plane, upper frame (paper is farther there)
rig2 = make_rig(cam2, "OverlayRig2")

font_title = load_font(FONT_TITLE)
font_sub = load_font(FONT_SUB)
font_hand = load_font(FONT_HAND)
font_mono = load_font(FONT_MONO)


def make_text(body, size, y, font, color=OFFWHITE, spacing=1.0, strength=1.0, x=0.0,
              align="CENTER", parent=None, max_w=None):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    if font:
        cu.font = font
    cu.size = size
    cu.space_character = spacing
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new("T_" + body[:10], cu)
    scene.collection.objects.link(ob)
    ob.parent = parent or rig
    ob.location = (x, y, 0)
    m, fac, em = mat_emit_fade("M_" + body[:10], color, strength)
    cu.materials.append(m)
    try:
        ob.visible_shadow = False
    except Exception:
        pass
    if max_w:
        bpy.context.view_layer.update()
        if ob.dimensions.x > max_w:
            s = max_w / ob.dimensions.x
            ob.scale = (s, s, s)
    return ob, fac


def vis_range(obs, t_in, t_out):
    """hide_render outside [t_in, t_out] so invisible overlays cost nothing"""
    if not isinstance(obs, (list, tuple)):
        obs = [obs]
    for ob in obs:
        ob.hide_render = True
        ob.keyframe_insert("hide_render", frame=1)
        ob.hide_render = False
        ob.keyframe_insert("hide_render", frame=max(1, F(t_in) - 1))
        ob.hide_render = True
        ob.keyframe_insert("hide_render", frame=F(t_out) + 1)


def fade(fac, t_in, t_out, d_in=0.6, d_out=0.6, peak=1.0, ob=None):
    if ob is not None:
        vis_range(ob, t_in, t_out + d_out)
    key_socket(fac, max(1, F(t_in) - 1), 0.0)
    key_socket(fac, F(t_in + d_in), peak)
    key_socket(fac, F(t_out), peak)
    key_socket(fac, F(t_out + d_out), 0.0)


MAXW = 1.45
LS = 1.55    # letter spacing (wide)

# --- Beat 1: hook (frame 1 already readable)
t, fac = make_text("IN 1977, SOMETHING", 0.085, -0.52, font_title, spacing=LS, max_w=MAXW)
key_socket(fac, 1, 0.55); key_socket(fac, F(0.35), 1.0); key_socket(fac, F(4.3), 1.0); key_socket(fac, F(4.9), 0.0)
t.hide_render = False; t.keyframe_insert("hide_render", frame=1); t.hide_render = True; t.keyframe_insert("hide_render", frame=F(5.0))
t, fac = make_text("CALLED TO US", 0.085, -0.65, font_title, spacing=LS, max_w=MAXW)
key_socket(fac, 1, 0.55); key_socket(fac, F(0.35), 1.0); key_socket(fac, F(4.3), 1.0); key_socket(fac, F(4.9), 0.0)
t.hide_render = False; t.keyframe_insert("hide_render", frame=1); t.hide_render = True; t.keyframe_insert("hide_render", frame=F(5.0))
t, fac = make_text("FOR 72 SECONDS.", 0.085, -0.80, font_title, spacing=LS, max_w=MAXW)
fade(fac, 0.9, 4.3, 0.7, 0.6, ob=t)

# --- Beat 2: date / place
t, fac = make_text("AUGUST 15, 1977", 0.085, -0.58, font_title, spacing=LS, max_w=MAXW)
fade(fac, 5.0, 8.0, 0.7, 0.5, ob=t)
t, fac = make_text("BIG EAR RADIO TELESCOPE", 0.042, -0.72, font_sub, spacing=1.7, max_w=MAXW, strength=0.75)
fade(fac, 5.5, 8.0, 0.7, 0.5, ob=t)
t, fac = make_text("OHIO STATE UNIVERSITY", 0.042, -0.78, font_sub, spacing=1.7, max_w=MAXW, strength=0.75)
fade(fac, 5.7, 8.0, 0.7, 0.5, ob=t)

# --- S2: days later
t, fac = make_text("A FEW DAYS LATER,", 0.075, 0.80, font_title, spacing=LS, max_w=MAXW, parent=rigD)
fade(fac, 8.7, 13.8, 0.8, 0.45, ob=t)
t, fac = make_text("ASTRONOMER JERRY EHMAN", 0.045, 0.67, font_sub, spacing=1.7, max_w=MAXW, strength=0.8, parent=rigD)
fade(fac, 9.4, 13.8, 0.8, 0.45, ob=t)
t, fac = make_text("WAS GOING THROUGH THE PRINTOUTS.", 0.045, 0.60, font_sub, spacing=1.7, max_w=MAXW, strength=0.8, parent=rigD)
fade(fac, 9.6, 13.8, 0.8, 0.45, ob=t)

# --- S3 (authored on the v1 timeline; every F() below is shifted by S3_OFF frames)
_FOFF = S3_OFF

# --- Beat 3: the printout
card_m = bpy.data.materials.new("Card"); use_nodes(card_m)
cn = card_m.node_tree; cn.nodes.clear()
co = cn.nodes.new("ShaderNodeOutputMaterial")
ce = cn.nodes.new("ShaderNodeEmission"); ce.inputs["Color"].default_value = (0.004, 0.005, 0.005, 1)
ctr = cn.nodes.new("ShaderNodeBsdfTransparent")
cmx = cn.nodes.new("ShaderNodeMixShader")
cn.links.new(ctr.outputs[0], cmx.inputs[1]); cn.links.new(ce.outputs[0], cmx.inputs[2])
cn.links.new(cmx.outputs[0], co.inputs["Surface"])
card_fac = cmx.inputs[0]
bpy.ops.mesh.primitive_plane_add(size=1.0)
card = bpy.context.active_object
card.data.materials.append(card_m)
card.parent = rig
card.location = (0, 0, 0.02)   # slightly behind the text (rig local -z is away from camera? rig faces camera)
card.location = (0, 0, -0.05)
card.scale = (8, 8, 1)
try:
    card.visible_shadow = False
except Exception:
    pass

T_CARD_IN, T_CARD_OUT = 8.3, 15.9
key_socket(card_fac, 1, 0.0)
key_socket(card_fac, F(T_CARD_IN) - 1, 0.0)
key_socket(card_fac, F(T_CARD_IN + 0.2), 1.0)
key_socket(card_fac, F(T_CARD_OUT), 1.0)
key_socket(card_fac, F(T_CARD_OUT + 0.6), 0.0)
card.hide_render = True; card.keyframe_insert("hide_render", frame=1)
card.hide_render = False; card.keyframe_insert("hide_render", frame=F(T_CARD_IN) - 1)
card.hide_render = True; card.keyframe_insert("hide_render", frame=F(T_CARD_OUT + 0.6) + 1)

pr = bpy.data.objects.new("Printout", None)
scene.collection.objects.link(pr)
pr.parent = rig

NCH = 9                # channels shown
TGT = 2                # target column (channel 2 as on the original printout)
WORD = "6EQUJ5"
ROWS = 44
TGT_ROW = 30           # first row of 6EQUJ5
rnd = random.Random(15)


def noise_char():
    v = rnd.random()
    if v < 0.52:
        return " "
    if v < 0.86:
        return "1"
    if v < 0.97:
        return "2"
    return "3"


rows = []
for r_ in range(ROWS):
    chars = [noise_char() for _ in range(NCH)]
    if TGT_ROW <= r_ < TGT_ROW + 6:
        chars[TGT] = chars[TGT - 1] = chars[TGT + 1] = " "
    if r_ in (TGT_ROW - 1, TGT_ROW + 6):
        chars[TGT] = chars[TGT - 1] = chars[TGT + 1] = " "
    rows.append(" ".join(chars))

LH = 0.088        # line pitch
MSIZE = 0.074
# measure width of one row to centre it
probe, _ = make_text("0" * (2 * NCH - 1), MSIZE, 0, font_mono, align="LEFT", parent=pr)
bpy.context.view_layer.update()
ROW_W = probe.dimensions.x
bpy.data.objects.remove(probe)
X0 = -ROW_W / 2
mono_mat, mono_fac, mono_em = mat_emit_fade("Mono", (0.80, 0.80, 0.76), 1.0)
# vertical vignette for the printout via camera-space Y
mnt = mono_mat.node_tree
mtc = mnt.nodes.new("ShaderNodeTexCoord")
msep = mnt.nodes.new("ShaderNodeSeparateXYZ")
mnt.links.new(mtc.outputs["Camera"], msep.inputs[0])
mabs = mnt.nodes.new("ShaderNodeMath"); mabs.operation = "ABSOLUTE"
mnt.links.new(msep.outputs["Y"], mabs.inputs[0])
mvr = mnt.nodes.new("ShaderNodeMapRange")
mvr.inputs["From Min"].default_value = 0.45
mvr.inputs["From Max"].default_value = 1.12
mvr.inputs["To Min"].default_value = 1.0
mvr.inputs["To Max"].default_value = 0.0
mnt.links.new(mabs.outputs[0], mvr.inputs[0])
mmul = mnt.nodes.new("ShaderNodeMath"); mmul.operation = "MULTIPLY"
mnt.links.new(mvr.outputs[0], mmul.inputs[0])
mono_mix = [n for n in mnt.nodes if n.bl_idname == "ShaderNodeMixShader"][0]
mmul.inputs[1].default_value = 0.0
mono_fac = mmul.inputs[1]
mnt.links.new(mmul.outputs[0], mono_mix.inputs[0])

for r_, line in enumerate(rows):
    cu = bpy.data.curves.new("row", "FONT")
    cu.body = line
    if font_mono:
        cu.font = font_mono
    cu.size = MSIZE
    cu.align_x = "LEFT"; cu.align_y = "CENTER"
    cu.materials.append(mono_mat)
    ob = bpy.data.objects.new("row%02d" % r_, cu)
    scene.collection.objects.link(ob)
    ob.parent = pr
    ob.location = (X0, -r_ * LH, 0)

# the signal characters (separate, so they can stay bright)
sig_mat, sig_fac, sig_em = mat_emit_fade("Signal", (0.97, 0.96, 0.92), 1.6)
for k, ch in enumerate(WORD):
    cu = bpy.data.curves.new("sig", "FONT")
    cu.body = " " * (2 * TGT) + ch
    if font_mono:
        cu.font = font_mono
    cu.size = MSIZE
    cu.align_x = "LEFT"; cu.align_y = "CENTER"
    cu.materials.append(sig_mat)
    ob = bpy.data.objects.new("sig%d" % k, cu)
    scene.collection.objects.link(ob)
    ob.parent = pr
    ob.location = (X0, -(TGT_ROW + k) * LH, 0)

# scroll: start with row 0 near bottom, end with the WORD centred slightly above middle
CHAR_W = ROW_W / (2 * NCH - 1)
x_tgt = X0 + (2 * TGT + 0.5) * CHAR_W
y_word_mid = -(TGT_ROW + 2.5) * LH
END_Y = 0.10 - y_word_mid
START_Y = -0.9
T_SCROLL0, T_SCROLL1 = 8.3, 12.6
pr.location = (0, START_Y, 0)
pr.keyframe_insert("location", frame=F(T_SCROLL0))
# printer-like: a few intermediate keys for a decelerating feed
for k, tt in enumerate([0.25, 0.5, 0.7, 0.85, 0.94]):
    ease = 1 - (1 - tt) ** 2.2
    pr.location = (0, START_Y + (END_Y - START_Y) * ease, 0)
    pr.keyframe_insert("location", frame=F(T_SCROLL0 + (T_SCROLL1 - T_SCROLL0) * tt))
pr.location = (0, END_Y, 0)
pr.keyframe_insert("location", frame=F(T_SCROLL1))
# slow creep afterwards
pr.location = (0, END_Y + 0.03, 0)
pr.keyframe_insert("location", frame=F(T_CARD_OUT + 0.6))

# visibility of printout text
key_socket(mono_fac, 1, 0.0)
key_socket(mono_fac, F(T_CARD_IN), 0.0)
key_socket(mono_fac, F(T_CARD_IN + 0.3), 0.85)
key_socket(mono_fac, F(12.9), 0.85)
key_socket(mono_fac, F(13.6), 0.28)        # everything else dims once circled
key_socket(mono_fac, F(T_CARD_OUT - 0.2), 0.28)
key_socket(mono_fac, F(T_CARD_OUT + 0.4), 0.0)
key_socket(sig_fac, 1, 0.0)
key_socket(sig_fac, F(T_CARD_IN), 0.0)
key_socket(sig_fac, F(T_CARD_IN + 0.3), 0.85)
key_socket(sig_fac, F(T_CARD_OUT - 0.2), 1.0)
key_socket(sig_fac, F(T_CARD_OUT + 0.4), 0.0)

# hand-drawn ellipse (pen loop with overshoot), drawn on
circ_cu = bpy.data.curves.new("Circle", "CURVE")
circ_cu.dimensions = "3D"
sp = circ_cu.splines.new("POLY")
NP = 120
rx, ry = CHAR_W * 2.6, LH * 3.7
cy = -(TGT_ROW + 2.5) * LH
crnd = random.Random(3)
pts = []
for k in range(NP):
    u = k / (NP - 1)
    a = math.radians(100) + u * (2 * math.pi + math.radians(38))
    wob = 1.0 + 0.035 * math.sin(3 * a + 0.7) + 0.02 * math.sin(7 * a) - 0.06 * u
    pts.append((x_tgt + rx * wob * math.cos(a) + 0.006 * math.sin(5 * a),
                cy + ry * wob * math.sin(a), 0.01))
sp.points.add(len(pts) - 1)
for k, p in enumerate(pts):
    sp.points[k].co = (*p, 1)
circ_cu.bevel_depth = 0.0050
circ_cu.bevel_resolution = 2
try:
    circ_cu.bevel_factor_mapping_end = "SPLINE"
except Exception:
    pass
circ = bpy.data.objects.new("Circle", circ_cu)
scene.collection.objects.link(circ)
circ.parent = pr
circ_m, circ_fac, circ_em = mat_emit_fade("CircleMat", ACCENT, 2.2)
circ_cu.materials.append(circ_m)
circ_cu.bevel_factor_end = 0.0
circ_cu.keyframe_insert("bevel_factor_end", frame=F(12.85))
circ_cu.bevel_factor_end = 1.0
circ_cu.keyframe_insert("bevel_factor_end", frame=F(13.75))
key_socket(circ_fac, 1, 0.0)
key_socket(circ_fac, F(12.8), 0.0)
key_socket(circ_fac, F(12.85), 1.0)
key_socket(circ_fac, F(T_CARD_OUT - 0.2), 1.0)
key_socket(circ_fac, F(T_CARD_OUT + 0.4), 0.0)

# "Wow!" in the margin, as Jerry Ehman wrote it
wow, wow_fac = make_text("Wow!", 0.10, cy, font_hand, color=ACCENT, spacing=1.05, strength=2.0,
                         x=X0 - 0.16, parent=pr)
wow.rotation_euler = (0, 0, math.radians(8))
fade(wow_fac, 14.0, T_CARD_OUT - 0.2, 0.35, 0.6, ob=wow)

# small caption under the printout
t, fac = make_text("INTENSITY, 12-SECOND STEPS", 0.032, -1.30, font_sub, spacing=1.8, max_w=MAXW, strength=0.55)
fade(fac, 9.0, T_CARD_OUT - 0.2, 0.8, 0.6, ob=t)

# --- Beat 4: 72 seconds
t, fac = make_text("72 SECONDS.", 0.10, 0.06, font_title, spacing=LS, max_w=MAXW)
fade(fac, 16.4, 19.2, 0.8, 0.5, ob=t)
t, fac = make_text("AS EARTH TURNED,", 0.040, -0.08, font_sub, spacing=1.7, max_w=MAXW, strength=0.75)
fade(fac, 16.9, 19.2, 0.8, 0.5, ob=t)
t, fac = make_text("IT DRIFTED THROUGH THE BEAM.", 0.040, -0.135, font_sub, spacing=1.7, max_w=MAXW, strength=0.75)
fade(fac, 17.1, 19.2, 0.8, 0.5, ob=t)

_FOFF = 0   # back to the 55 s timeline

# --- S4: narrowband, 1420 MHz
t, fac = make_text("1420 MHz", 0.11, 0.55, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 25.8, 31.0, 0.9, 0.45, ob=t)
t, fac = make_text("A NARROWBAND SIGNAL,", 0.042, 0.42, font_sub, spacing=1.7, max_w=MAXW, strength=0.8, parent=rig2)
fade(fac, 26.4, 31.0, 0.8, 0.45, ob=t)
t, fac = make_text("RIGHT BY THE HYDROGEN LINE", 0.042, 0.36, font_sub, spacing=1.7, max_w=MAXW, strength=0.8, parent=rig2)
fade(fac, 26.6, 31.0, 0.8, 0.45, ob=t)
t, fac = make_text("THE FREQUENCY SCIENTISTS HAD PROPOSED", 0.036, -0.70, font_sub, spacing=1.7, max_w=MAXW, strength=0.7, parent=rig2)
fade(fac, 28.4, 31.0, 0.8, 0.45, ob=t)
t, fac = make_text("FOR SIGNALS BETWEEN THE STARS.", 0.036, -0.755, font_sub, spacing=1.7, max_w=MAXW, strength=0.7, parent=rig2)
fade(fac, 28.6, 31.0, 0.8, 0.45, ob=t)

# a spectrum trace: noise floor + one narrow green spike
spec = bpy.data.objects.new("Spectrum", None)
scene.collection.objects.link(spec)
spec.parent = rig2
spec.location = (0, -0.52, 0)


def poly_curve(name, pts, mat, depth=0.0028, parent=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp_ = cu.splines.new("POLY")
    sp_.points.add(len(pts) - 1)
    for k, p in enumerate(pts):
        sp_.points[k].co = (p[0], p[1], 0, 1)
    cu.bevel_depth = depth
    cu.bevel_resolution = 1
    try:
        cu.bevel_factor_mapping_end = "SPLINE"
    except Exception:
        pass
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.parent = parent
    return ob, cu


srnd = random.Random(1420)
base_pts = [(-0.62 + 1.24 * k / 179, 0.012 * (srnd.random() - 0.5) + 0.008 * math.sin(k * 0.21)) for k in range(180)]
base_m, base_fac, _ = mat_emit_fade("SpecBase", OFFWHITE, 0.55)
base_ob, base_cu = poly_curve("SpecBase", base_pts, base_m, 0.0022, spec)
base_cu.bevel_factor_end = 0.0
base_cu.keyframe_insert("bevel_factor_end", frame=F(25.6))
base_cu.bevel_factor_end = 1.0
base_cu.keyframe_insert("bevel_factor_end", frame=F(27.0))
fade(base_fac, 25.6, 31.0, 0.2, 0.45, ob=base_ob)
spike_m, spike_fac, _ = mat_emit_fade("Spike", ACCENT, 2.2)
spike_pts = [(-0.02, 0.0), (-0.006, 0.01), (-0.002, 0.16), (0.0, 0.2), (0.002, 0.16), (0.006, 0.01), (0.02, 0.0)]
spike_ob, spike_cu = poly_curve("Spike", spike_pts, spike_m, 0.0030, spec)
spike_ob.scale = (1, 0.0, 1); spike_ob.keyframe_insert("scale", frame=F(26.85))
spike_ob.scale = (1, 1.15, 1); spike_ob.keyframe_insert("scale", frame=F(27.2))
spike_ob.scale = (1, 1.0, 1); spike_ob.keyframe_insert("scale", frame=F(27.6))
fade(spike_fac, 26.8, 31.0, 0.1, 0.45, ob=spike_ob)

# --- S5: the searches
t, fac = make_text("BIG EAR LOOKED AGAIN.", 0.075, 0.72, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 31.9, 34.3, 0.8, 0.4, ob=t)
t, fac = make_text("AND AGAIN. AND AGAIN.", 0.042, 0.62, font_sub, spacing=1.7, max_w=MAXW, strength=0.8, parent=rig2)
fade(fac, 32.7, 34.3, 0.7, 0.4, ob=t)
t, fac = make_text("THE VERY LARGE ARRAY, 1995 AND 1996.", 0.042, 0.72, font_sub, spacing=1.7, max_w=MAXW, strength=0.85, parent=rig2)
fade(fac, 34.7, 37.0, 0.7, 0.35, ob=t)
t, fac = make_text("OTHER TELESCOPES SINCE.", 0.042, 0.66, font_sub, spacing=1.7, max_w=MAXW, strength=0.85, parent=rig2)
fade(fac, 35.3, 37.0, 0.7, 0.35, ob=t)
t, fac = make_text("NOTHING.", 0.10, 0.70, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 37.3, 38.3, 0.5, 0.2, ob=t)

# --- S6: torn down
t, fac = make_text("IN 1998, BIG EAR WAS TORN DOWN", 0.060, -0.58, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 39.0, 44.0, 0.9, 0.45, ob=t)
t, fac = make_text("TO MAKE ROOM FOR A GOLF COURSE.", 0.042, -0.70, font_sub, spacing=1.7, max_w=MAXW, strength=0.8, parent=rig2)
fade(fac, 40.0, 44.0, 0.9, 0.45, ob=t)

# --- S7: still listening
t, fac = make_text("THE SIGNAL WAS", 0.075, -0.50, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 45.4, 48.8, 1.0, 0.6, ob=t)
t, fac = make_text("NEVER HEARD AGAIN.", 0.075, -0.63, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 45.8, 48.8, 1.0, 0.6, ob=t)
t, fac = make_text("WE'RE STILL LISTENING.", 0.075, -0.55, font_title, spacing=LS, max_w=MAXW, parent=rig2)
fade(fac, 49.6, 52.6, 1.2, 0.5, ob=t)

# the final blip: a single green point in the sky, then black
blip_m, blip_fac, blip_em = mat_emit_fade("Blip", ACCENT, 2.6)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, segments=10, ring_count=6)
blip = bpy.context.active_object
blip.data.materials.append(blip_m)
blip.parent = rig2
blip.location = (0.10, 0.42, 0.0)
vis_range(blip, 53.6, 54.5)
key_socket(blip_fac, 1, 0.0)
key_socket(blip_fac, F(53.70), 0.0)
key_socket(blip_fac, F(53.76), 1.0)
key_socket(blip_fac, F(54.05), 1.0)
key_socket(blip_fac, F(54.35), 0.0)
blip.scale = (1, 1, 1); blip.keyframe_insert("scale", frame=F(53.70))
blip.scale = (1.7, 1.7, 1.7); blip.keyframe_insert("scale", frame=F(53.80))
blip.scale = (1.1, 1.1, 1.1); blip.keyframe_insert("scale", frame=F(54.35))

# end card: hard cut to black
endc_m, endc_fac, endc_em = mat_emit_fade("EndCard", (0, 0, 0), 0.0)
bpy.ops.mesh.primitive_plane_add(size=1.0)
endc = bpy.context.active_object
endc.data.materials.append(endc_m)
endc.parent = rig2
endc.location = (0, 0, -0.04)
endc.scale = (8, 8, 1)
vis_range(endc, T_CUT, 56.0)
key_socket(endc_fac, 1, 1.0)

# ---------------------------------------------------------------- aviation light blink (1.5 s period), gone with the dish
period = 1.5
t0 = 0.2
while t0 < 40.4:
    key_socket(red_fac, F(t0), 0.0)
    key_socket(red_fac, F(t0 + 0.12), 1.0)
    key_socket(red_fac, F(t0 + 0.55), 1.0)
    key_socket(red_fac, F(t0 + 0.75), 0.0)
    key_socket(halo_amt, F(t0), 0.0)
    key_socket(halo_amt, F(t0 + 0.12), 0.9)
    key_socket(halo_amt, F(t0 + 0.55), 0.8)
    key_socket(halo_amt, F(t0 + 0.9), 0.0)
    t0 += period
for o in (avl, halo):
    o.hide_render = False; o.keyframe_insert("hide_render", frame=1)
    o.hide_render = True; o.keyframe_insert("hide_render", frame=F(41.2))
# halo always faces the camera
con = halo.constraints.new("TRACK_TO")
con.target = cam
con.track_axis = "TRACK_Z"
con.up_axis = "UP_Y"
con2 = halo.constraints.new("TRACK_TO")      # after S4 the active camera is Cam2
con2.target = cam2
con2.track_axis = "TRACK_Z"
con2.up_axis = "UP_Y"
con2.influence = 0.0
con2.keyframe_insert("influence", frame=FR_S4 - 1)
con2.influence = 1.0
con2.keyframe_insert("influence", frame=FR_S4)

# ---------------------------------------------------------------- render settings
r = scene.render
r.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = ARGS["samples"] or CONFIG["samples"]
try:
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.05
except Exception:
    pass
scene.cycles.use_denoising = CONFIG["denoise"]
try:
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
scene.cycles.max_bounces = 2
scene.cycles.diffuse_bounces = 1
scene.cycles.glossy_bounces = 1
scene.cycles.transmission_bounces = 0
scene.cycles.volume_bounces = 0
scene.cycles.transparent_max_bounces = 24
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.seed = 0
try:
    scene.cycles.use_animated_seed = True
except Exception:
    pass
r.resolution_x, r.resolution_y = CONFIG["resolution"]
r.resolution_percentage = ARGS["percent"] or CONFIG["resolution_percentage"]
r.film_transparent = False
try:
    r.use_persistent_data = True
except Exception:
    pass
try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy" if not V5 else "None"
except Exception:
    try:
        scene.view_settings.view_transform = "Filmic"
    except Exception:
        pass
scene.view_settings.exposure = 0.6
img = r.image_settings
if V5:
    try:
        img.media_type = "IMAGE"
    except Exception:
        pass
img.file_format = "PNG"
img.color_mode = "RGB"
img.color_depth = "8"
out = ARGS["out"] or CONFIG["output"]
if not out.endswith(("_", "/")):
    out = os.path.join(out, "f_")
r.filepath = out

# ---------------------------------------------------------------- go
if ARGS["frames"]:
    for fr in ARGS["frames"]:
        scene.frame_set(fr)
        r.filepath = out + "%04d.png" % fr
        bpy.ops.render.render(write_still=True)
elif ARGS["render"]:
    # --start/--step allow interleaved passes (e.g. odd frames first, then even)
    if ARGS["start"]:
        scene.frame_start = ARGS["start"]
    if ARGS["end"]:
        scene.frame_end = ARGS["end"]
    if ARGS["step"]:
        scene.frame_step = ARGS["step"]
    if ARGS["skip"]:
        r.use_overwrite = False      # resume: skip frames already on disk
    bpy.ops.render.render(animation=True)
