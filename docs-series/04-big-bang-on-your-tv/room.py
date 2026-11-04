"""CRT room plates for 04 'The Big Bang is on your TV'.

Renders, for each camera, three linear passes as float16 .npy (3840x2160) that the numpy compositor
combines per frame (lighting is linear, so the flickering TV light is just a scaled LIT pass):
  off : room lit only by cold moonlight through the window, TV screen = dark grey-green glass
  lit : room lit only by the TV screen (screen itself invisible to camera), emission strength 1
  uv  : screen only, emitting (u, v, 1) -> where the screen is and how to map the static onto it
Run: /home/user/bpyenv/bin/python -c "import sys;p='room.py';sys.argv=['blender','--',CAM,PASS,SPP,SCALE];exec(compile(open(p).read(),p,'exec'))"
"""
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CAM = argv[0] if len(argv) > 0 else "wide"
PASS = argv[1] if len(argv) > 1 else "off"
SPP = int(argv[2]) if len(argv) > 2 else 64
SCALE = int(argv[3]) if len(argv) > 3 else 200       # percent of 1920x1080
OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv/plates"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SPP
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 2 if PASS != "uv" else 0
sc.cycles.diffuse_bounces = 1 if PASS != "uv" else 0
sc.cycles.glossy_bounces = 1 if PASS != "uv" else 0
sc.cycles.transmission_bounces = 0
sc.cycles.transparent_max_bounces = 2
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = SCALE
sc.render.film_transparent = False
sc.render.filter_size = 1.2 if PASS != "uv" else 0.01
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.world = bpy.data.worlds.new("w")
sc.world.use_nodes = True
sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.0


def mat(name, col, rough=0.6, emit=None, emit_strength=0.0, spec=0.3):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m


def black_mat():
    m = bpy.data.materials.new("holdblack")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[1].default_value = 0.0
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def wallpaper_mat():
    """Faded vertical-stripe wallpaper (procedural, cheap)."""
    m = bpy.data.materials.new("wallpaper")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 9.0
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"
    nt.links.new(sep.outputs[0], add.inputs[0]); nt.links.new(sep.outputs[1], add.inputs[1])
    nt.links.new(add.outputs[0], mul.inputs[0])
    sn = nt.nodes.new("ShaderNodeMath"); sn.operation = "SINE"
    nt.links.new(mul.outputs[0], sn.inputs[0])
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = -1; ramp.inputs["From Max"].default_value = 1
    nt.links.new(sn.outputs[0], ramp.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.36, 0.30, 0.22, 1)
    mix.inputs["B"].default_value = (0.30, 0.33, 0.27, 1)
    st = nt.nodes.new("ShaderNodeMath"); st.operation = "GREATER_THAN"; st.inputs[1].default_value = 0.72
    nt.links.new(ramp.outputs[0], st.inputs[0])
    nt.links.new(st.outputs[0], mix.inputs["Factor"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"; mix2.inputs["Factor"].default_value = 0.25
    nt.links.new(mix.outputs[2], mix2.inputs["A"]); nt.links.new(noise.outputs["Color"], mix2.inputs["B"])
    nt.links.new(mix2.outputs[2], b.inputs["Base Color"])
    return m


def wood_mat(name, base=(0.20, 0.10, 0.05), scale=(1, 18, 1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    w = nt.nodes.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value = 2.0
    w.inputs["Distortion"].default_value = 6.0
    nt.links.new(mp.outputs[0], w.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*base, 1)
    mix.inputs["B"].default_value = (base[0] * 0.55, base[1] * 0.55, base[2] * 0.55, 1)
    nt.links.new(w.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    return m


def box(name, size, loc, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        md = o.modifiers.new("b", "BEVEL"); md.width = bevel; md.segments = 3
    o.data.materials.append(m)
    return o


def cyl(name, r, depth, loc, rot, m, verts=16):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.object; o.name = name; o.data.materials.append(m)
    return o


BLACK = black_mat()
uvpass = PASS == "uv"

M_wall = BLACK if uvpass else wallpaper_mat()
M_floor = BLACK if uvpass else wood_mat("floor", (0.16, 0.09, 0.05), (1, 6, 1))
M_wood = BLACK if uvpass else wood_mat("tvwood", (0.24, 0.12, 0.05), (1, 1, 30))
M_dark = BLACK if uvpass else mat("darkplastic", (0.025, 0.022, 0.02), 0.35, spec=0.5)
M_metal = BLACK if uvpass else mat("chrome", (0.6, 0.6, 0.62), 0.25, spec=0.6)
M_fabric = BLACK if uvpass else mat("fabric", (0.12, 0.07, 0.06), 0.95)
M_rug = BLACK if uvpass else mat("rug", (0.11, 0.05, 0.04), 1.0)
M_cream = BLACK if uvpass else mat("cream", (0.55, 0.50, 0.42), 0.8)
M_knob = BLACK if uvpass else mat("knob", (0.08, 0.07, 0.06), 0.3, spec=0.6)
M_window = BLACK if uvpass else mat("windowframe", (0.45, 0.43, 0.40), 0.7)

# ---------------- room shell
box("floor", (8, 8, 0.02), (0, 0, -0.01), M_floor)
box("backwall", (8, 0.05, 3.0), (0, 2.05, 1.5), M_wall)
lw = box("leftwall", (0.05, 8, 3.0), (-2.45, 0, 1.5), M_wall)
box("rightwall", (0.05, 8, 3.0), (2.6, 0, 1.5), M_wall)
box("ceiling", (8, 8, 0.02), (0, 0, 2.6), M_cream if not uvpass else BLACK)
box("skirting", (8, 0.04, 0.12), (0, 2.01, 0.06), M_cream)
# window hole in left wall (boolean)
hole = box("hole", (0.4, 1.0, 1.15), (-2.45, 0.55, 1.45), BLACK)
bm = lw.modifiers.new("win", "BOOLEAN"); bm.object = hole; bm.operation = "DIFFERENCE"
hole.hide_render = True
for zz in (0.875, 1.45, 2.025):
    box(f"wf_h{zz}", (0.09, 1.0, 0.05), (-2.45, 0.55, zz), M_window)
for yy in (0.05, 0.55, 1.05):
    box(f"wf_v{yy}", (0.09, 0.05, 1.2), (-2.45, yy, 1.45), M_window)
# thin curtain to one side of the window
box("curtain", (0.06, 0.45, 2.1), (-2.38, 1.35, 1.35), M_fabric)
box("rug", (2.6, 1.8, 0.01), (0.1, 0.3, 0.005), M_rug)

# ---------------- TV stand + TV
box("stand", (1.15, 0.5, 0.42), (0, 1.55, 0.21), M_wood, 0.01)
box("stand_shelf_gap", (1.0, 0.02, 0.12), (0, 1.295, 0.22), M_dark)
TVX, TVY, TVZ = 0.0, 1.55, 0.42 + 0.30
box("tv_cabinet", (0.80, 0.52, 0.58), (TVX, TVY, TVZ), M_wood, 0.025)
box("tv_back", (0.56, 0.30, 0.42), (TVX, TVY + 0.38, TVZ - 0.02), M_dark, 0.04)
FRONT = TVY - 0.26
box("tv_bezel", (0.60, 0.02, 0.48), (TVX - 0.08, FRONT - 0.005, TVZ + 0.01), M_dark, 0.02)
# knob panel on the right
box("knobpanel", (0.13, 0.02, 0.46), (TVX + 0.31, FRONT - 0.006, TVZ), M_dark if not uvpass else BLACK, 0.01)
for k, kz in enumerate((0.13, 0.03)):
    cyl(f"knob{k}", 0.028, 0.035, (TVX + 0.31, FRONT - 0.03, TVZ + kz), (math.pi / 2, 0, 0), M_knob, 24)
for k in range(5):
    box(f"grille{k}", (0.09, 0.012, 0.006), (TVX + 0.31, FRONT - 0.018, TVZ - 0.08 - k * 0.025), M_metal)
# curved CRT screen: subdivided plane with spherical bulge, rounded-rect outline
SW, SH = 0.50, 0.375
bm_ = bmesh.new()
nx, ny = 64, 48
verts = {}
for j in range(ny + 1):
    for i in range(nx + 1):
        u, v = i / nx, j / ny
        x = (u - 0.5) * SW
        z = (v - 0.5) * SH
        bulge = 0.022 * (1 - (2 * (u - 0.5)) ** 2) * (1 - (2 * (v - 0.5)) ** 2)
        verts[i, j] = bm_.verts.new((x, -bulge, z))
uvl = bm_.loops.layers.uv.new("UVMap")
for j in range(ny):
    for i in range(nx):
        f = bm_.faces.new((verts[i, j], verts[i + 1, j], verts[i + 1, j + 1], verts[i, j + 1]))
        for lp, (a, b_) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
            lp[uvl].uv = (a / nx, b_ / ny)
me = bpy.data.meshes.new("screen"); bm_.to_mesh(me); bm_.free()
screen = bpy.data.objects.new("screen", me)
sc.collection.objects.link(screen)
screen.location = (TVX - 0.08, FRONT - 0.018, TVZ + 0.01)
for p in me.polygons:
    p.use_smooth = True

sm = bpy.data.materials.new("screenmat"); sm.use_nodes = True
nt = sm.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new("ShaderNodeOutputMaterial")
if PASS == "uv":
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    nt.links.new(sep.outputs[0], comb.inputs[0]); nt.links.new(sep.outputs[1], comb.inputs[1])
    comb.inputs[2].default_value = 1.0
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[1].default_value = 1.0
    nt.links.new(comb.outputs[0], e.inputs[0]); nt.links.new(e.outputs[0], out.inputs[0])
elif PASS == "lit":
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs[0].default_value = (0.80, 0.86, 1.0, 1)
    e.inputs[1].default_value = 6.0
    nt.links.new(e.outputs[0], out.inputs[0])
    screen.visible_camera = False
    screen.visible_glossy = False
else:   # off: dark slightly glossy grey-green glass
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.018, 0.022, 0.020, 1)
    b.inputs["Roughness"].default_value = 0.12
    nt.links.new(b.outputs[0], out.inputs[0])
screen.data.materials.append(sm)

# rabbit-ear antenna
base = cyl("ant_base", 0.06, 0.03, (TVX + 0.05, TVY + 0.02, TVZ + 0.305), (0, 0, 0), M_dark, 24)
for side in (-1, 1):
    L = 0.62
    ang = math.radians(28)
    tilt_y = side * ang
    cx = TVX + 0.05 + side * math.sin(ang) * L / 2
    cz = TVZ + 0.32 + math.cos(ang) * L / 2
    cyl(f"ear{side}", 0.0055, L, (cx, TVY + 0.02 - 0.05 * side, cz), (math.radians(6 * side), tilt_y, 0), M_metal, 8)
    tipx = TVX + 0.05 + side * math.sin(ang) * L
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008, location=(tipx, TVY + 0.02 - 0.1 * side, TVZ + 0.32 + math.cos(ang) * L))
    bpy.context.object.data.materials.append(M_metal)
# a few objects on the stand: VHS box + small vase
box("vhs", (0.19, 0.11, 0.03), (TVX - 0.42, TVY - 0.08, 0.435), M_dark)
box("vhs2", (0.19, 0.11, 0.03), (TVX - 0.43, TVY - 0.07, 0.465), M_cream)
cyl("vase", 0.045, 0.22, (TVX + 0.47, TVY - 0.05, 0.53), (0, 0, 0), M_cream, 24)

# armchair in the foreground (silhouette)
box("chair_seat", (0.8, 0.75, 0.42), (-0.95, -0.85, 0.21), M_fabric, 0.06)
box("chair_back", (0.8, 0.2, 0.9), (-0.95, -1.25, 0.55), M_fabric, 0.08)
box("chair_armL", (0.16, 0.8, 0.62), (-1.35, -0.88, 0.31), M_fabric, 0.06)
box("chair_armR", (0.16, 0.8, 0.62), (-0.55, -0.88, 0.31), M_fabric, 0.06)
# floor lamp (off) right
cyl("lamp_pole", 0.012, 1.45, (1.45, 1.3, 0.72), (0, 0, 0), M_metal)
cyl("lamp_base", 0.14, 0.03, (1.45, 1.3, 0.015), (0, 0, 0), M_dark, 24)
bpy.ops.mesh.primitive_cone_add(radius1=0.24, radius2=0.14, depth=0.28, location=(1.45, 1.3, 1.5))
bpy.context.object.data.materials.append(M_cream)
# picture frame on the back wall
box("frame", (0.55, 0.03, 0.40), (-1.0, 2.01, 1.55), M_wood)
box("frame_in", (0.45, 0.02, 0.30), (-1.0, 2.0, 1.55), M_dark if not uvpass else BLACK)

# ---------------- lights
if PASS == "off":
    bpy.ops.object.light_add(type="AREA", location=(-3.2, 0.3, 2.3))
    moon = bpy.context.object
    moon.data.shape = "RECTANGLE"; moon.data.size = 0.6; moon.data.size_y = 0.6
    moon.data.energy = 140
    moon.data.color = (0.55, 0.68, 1.0)
    d = Vector((-0.6, 0.6, 0.2)) - moon.location
    moon.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # very faint fill so the room is not pure black
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.4, 0.5, 0.8, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.004

# ---------------- cameras
cams = {
    "wide":   ((0.75, -2.55, 1.12), (TVX - 0.08, TVY, TVZ + 0.05), 32),
    "medium": ((-0.62, -0.62, 0.98), (TVX - 0.03, TVY, TVZ + 0.10), 42),
}
loc, tgt, lens = cams[CAM]
cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = 36
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam)
cam.location = loc
cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
sc.camera = cam

sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "OPEN_EXR"
sc.render.image_settings.color_depth = "16"
exr = os.path.join(OUT, f"room_{CAM}_{PASS}.exr")
sc.render.filepath = exr
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(exr)
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
np.save(os.path.join(OUT, f"room_{CAM}_{PASS}.npy"), px.astype(np.float16))
os.remove(exr)
print("saved", CAM, PASS, w, h, float(px.mean()), float(px.max()))
