"""Stylised Holmdel-style horn-reflector antenna at blue hour (no real likeness of people; simplified shape).

Modes:
  still <cam> <spp> <scale%>          -> plates/horn_<cam>.png (single frame, e.g. 4K for 2D moves)
  orbit <start> <end> <spp>           -> frames/horn_orbit/f_%04d.png (true 3D camera orbit, 1080p)
Run via: /home/user/bpyenv/bin/python -c "import sys;p='horn.py';sys.argv=['blender','--',...];exec(...)"
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "still"
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv"
ORBIT_N = 41           # key frames every 6 video frames over 10 s; in-betweens are cross-blended (very slow move)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.use_denoising = True            # OpenImageDenoise, albedo+normal guided -> few samples needed
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
sc.cycles.denoising_prefilter = "ACCURATE"
sc.cycles.max_bounces = 2
sc.cycles.diffuse_bounces = 1
sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 0
sc.cycles.transparent_max_bounces = 0
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.light_sampling_threshold = 0.05
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = 0.7
sc.render.filter_size = 1.4

# world: pre-baked sky texture
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
nt = w.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(SCR, "tex", "horn_sky.png"))
mp = nt.nodes.new("ShaderNodeMapping"); tc = nt.nodes.new("ShaderNodeTexCoord")
mp.inputs["Rotation"].default_value = (0, 0, math.radians(200))
nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.5


def mat(name, col, rough=0.6, emit=None, es=0.0, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = es
    return m


def weathered_alu(name):
    """Weathered aluminium sheet: metallic, roughness + tone varied by noise, vertical grime streaks, panel seams."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree; b = t.nodes["Principled BSDF"]
    b.inputs["Metallic"].default_value = 0.75
    tcn = t.nodes.new("ShaderNodeTexCoord")
    nz = t.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.9; nz.inputs["Detail"].default_value = 6
    t.links.new(tcn.outputs["Object"], nz.inputs["Vector"])
    # grime streaks: noise stretched along z
    mp = t.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (3.0, 3.0, 0.25)
    t.links.new(tcn.outputs["Object"], mp.inputs[0])
    st = t.nodes.new("ShaderNodeTexNoise"); st.inputs["Scale"].default_value = 2.5; st.inputs["Detail"].default_value = 3
    t.links.new(mp.outputs[0], st.inputs["Vector"])
    # panel seams every ~1.2 m along the horn axis
    wv = t.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 0.42; wv.bands_direction = "X"
    wv.wave_profile = "SAW"
    t.links.new(tcn.outputs["Object"], wv.inputs["Vector"])
    seam = t.nodes.new("ShaderNodeMath"); seam.operation = "GREATER_THAN"; seam.inputs[1].default_value = 0.96
    t.links.new(wv.outputs["Fac"], seam.inputs[0])
    c1 = t.nodes.new("ShaderNodeMix"); c1.data_type = "RGBA"
    c1.inputs["A"].default_value = (0.58, 0.59, 0.60, 1); c1.inputs["B"].default_value = (0.40, 0.40, 0.38, 1)
    t.links.new(nz.outputs["Fac"], c1.inputs["Factor"])
    c2 = t.nodes.new("ShaderNodeMix"); c2.data_type = "RGBA"
    c2.inputs["B"].default_value = (0.20, 0.19, 0.17, 1)
    gr = t.nodes.new("ShaderNodeMapRange"); gr.inputs["From Min"].default_value = 0.55; gr.inputs["From Max"].default_value = 0.8
    gr.inputs["To Max"].default_value = 0.6
    t.links.new(st.outputs["Fac"], gr.inputs["Value"])
    t.links.new(gr.outputs[0], c2.inputs["Factor"]); t.links.new(c1.outputs[2], c2.inputs["A"])
    c3 = t.nodes.new("ShaderNodeMix"); c3.data_type = "RGBA"; c3.inputs["B"].default_value = (0.08, 0.08, 0.08, 1)
    t.links.new(seam.outputs[0], c3.inputs["Factor"]); t.links.new(c2.outputs[2], c3.inputs["A"])
    t.links.new(c3.outputs[2], b.inputs["Base Color"])
    rr = t.nodes.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.28; rr.inputs["To Max"].default_value = 0.62
    t.links.new(nz.outputs["Fac"], rr.inputs["Value"]); t.links.new(rr.outputs[0], b.inputs["Roughness"])
    bump = t.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15
    t.links.new(seam.outputs[0], bump.inputs["Height"]); t.links.new(bump.outputs[0], b.inputs["Normal"])
    return m


M_horn = weathered_alu("horn")
M_dark = mat("inside", (0.01, 0.01, 0.012), 0.9)
M_steel = mat("paintedsteel", (0.16, 0.18, 0.17), 0.55, metal=0.15)
M_ground = mat("ground", (0.016, 0.02, 0.015), 1.0)
M_cab = mat("cab", (0.45, 0.42, 0.36), 0.8)
M_win = mat("cabwin", (0.1, 0.07, 0.03), 0.5, emit=(1.0, 0.62, 0.28), es=6.0)
M_rail = mat("rail", (0.2, 0.2, 0.2), 0.4, metal=0.8)


def add_obj(name, verts, faces, m, parent=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    o.data.materials.append(m)
    if parent: o.parent = parent
    return o


def box(name, size, loc, m, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)
    if parent:
        o.parent = parent
    return o


def cyl(name, r, a, b, m, verts=12):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=verts)
    o = bpy.context.object; o.name = name
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)
    return o


AX_Z = 5.2          # height of the horn axis
pivot = bpy.data.objects.new("pivot", None); sc.collection.objects.link(pivot)
pivot.location = (0, 0, AX_Z)
# --- long pyramidal horn, gently flaring (not a straight cone) to a square mouth, with stiffening frames
x0, x1, r0, r1 = -9.0, 5.0, 0.32, 2.9


def rad(x):
    u = (x - x0) / (x1 - x0)
    return r0 + (r1 - r0) * (0.55 * u + 0.45 * u ** 2.2)


def loft(name, xs, rs, m, parent):
    V, Fc = [], []
    for x, r in zip(xs, rs):
        V += [(x, -r, -r), (x, r, -r), (x, r, r), (x, -r, r)]
    for i in range(len(xs) - 1):
        a = 4 * i; b2 = a + 4
        for k in range(4):
            Fc.append((a + k, a + (k + 1) % 4, b2 + (k + 1) % 4, b2 + k))
    return add_obj(name, V, Fc, m, parent)


xs = [x0 + (x1 - x0) * i / 24 for i in range(25)]
horn = loft("horn", xs, [rad(x) for x in xs], M_horn, pivot)
add_obj("throatcap", [(x0, -r0, -r0), (x0, r0, -r0), (x0, r0, r0), (x0, -r0, r0)], [(0, 3, 2, 1)], M_horn, pivot)
for i, x in enumerate([x0 + 0.6 + k * 1.15 for k in range(12)]):
    r = rad(x) + 0.06
    loft(f"rib{i}", [x - 0.07, x + 0.07], [r, r], M_steel, pivot)
R = r1
# --- reflector housing at the wide end: box whose +Z face is the open aperture (dark inside)
hx0, hx1 = x1, x1 + 2 * R * 0.95
Vh = [(hx0, -R, -R), (hx1, -R, -R), (hx1, R, -R), (hx0, R, -R),
      (hx0, -R, R), (hx1, -R, R * 0.2), (hx1, R, R * 0.2), (hx0, R, R)]
Fh = [(0, 1, 2, 3), (0, 1, 5, 4), (3, 2, 6, 7), (1, 2, 6, 5)]
add_obj("hood", Vh, Fh, M_horn, pivot)
# curved back reflector (dark inner face visible through the aperture)
bm = bmesh.new(); segs = 16
rows = []
for i in range(segs + 1):
    a = i / segs * math.pi / 2
    x = hx0 + (hx1 - hx0) * math.sin(a)
    z = -R + (R * 1.2) * (1 - math.cos(a)) * 0.95
    rows.append((bm.verts.new((x, -R * 0.98, z)), bm.verts.new((x, R * 0.98, z))))
for i in range(segs):
    bm.faces.new((rows[i][0], rows[i + 1][0], rows[i + 1][1], rows[i][1]))
me = bpy.data.meshes.new("refl"); bm.to_mesh(me); bm.free()
refl = bpy.data.objects.new("refl", me); sc.collection.objects.link(refl); refl.parent = pivot
refl.data.materials.append(M_dark)
# aperture rim frame
# elevation wheel (ring around the horn)
bpy.ops.mesh.primitive_torus_add(major_radius=R * 1.48, minor_radius=0.16, location=(3.2, 0, 0),
                                 rotation=(0, math.pi / 2, 0), major_segments=64, minor_segments=8)
ring = bpy.context.object; ring.parent = pivot; ring.data.materials.append(M_steel)
bpy.ops.mesh.primitive_torus_add(major_radius=0.9, minor_radius=0.12, location=(-7.4, 0, 0),
                                 rotation=(0, math.pi / 2, 0), major_segments=32, minor_segments=8)
ring2 = bpy.context.object; ring2.parent = pivot; ring2.data.materials.append(M_steel)
# tilt the whole horn about its axis so the aperture looks up at the sky
pivot.rotation_euler = (math.radians(38), 0, 0)
# supports (A-frames) from the turntable to the wheels
for xs, rr in ((3.2, R * 1.48), (-7.4, 0.9)):
    for s in (-1, 1):
        cyl(f"leg{xs}{s}", 0.11, (xs + 0.0, s * (rr + 1.2), 0.3), (xs, s * 0.25, AX_Z - rr), M_steel, 8)
        cyl(f"legb{xs}{s}", 0.08, (xs - 1.3, s * (rr + 0.6), 0.3), (xs, s * 0.25, AX_Z - rr), M_steel, 8)
box("base_beam", (12.5, 0.5, 0.35), (-2.0, 0, 0.35), M_steel)
for s in (-1, 1):
    box(f"base_side{s}", (12.5, 0.3, 0.3), (-2.0, s * 4.2, 0.3), M_steel)
# receiver cab at the narrow end
box("cab", (2.6, 2.4, 2.2), (-10.6, 0, 1.4), M_cab)
box("cabroof", (2.9, 2.7, 0.15), (-10.6, 0, 2.55), M_steel)
box("cabwin", (0.02, 0.8, 0.5), (-9.29, 0.5, 1.6), M_win)
box("cabdoor", (0.02, 0.7, 1.6), (-9.29, -0.6, 1.1), M_dark)
# circular rail track
bpy.ops.mesh.primitive_torus_add(major_radius=11.0, minor_radius=0.08, location=(-2.0, 0, 0.08),
                                 major_segments=128, minor_segments=6)
bpy.context.object.data.materials.append(M_rail)
bpy.ops.mesh.primitive_cylinder_add(radius=11.6, depth=0.1, location=(-2.0, 0, 0.0), vertices=96)
bpy.context.object.data.materials.append(mat("pad", (0.10, 0.10, 0.095), 0.9))
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.02))
bpy.context.object.data.materials.append(M_ground)
# distant tree line silhouettes (cheap boxes) for scale
import random
random.seed(3)
M_tree = mat("tree", (0.006, 0.008, 0.006), 1.0)
for k in range(260):
    a = random.uniform(0, 2 * math.pi); d = random.uniform(170, 210); hgt = random.uniform(5, 11)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(math.cos(a) * d, math.sin(a) * d, hgt * 0.55))
    o = bpy.context.object; o.scale = (random.uniform(4, 9), random.uniform(4, 9), hgt * 0.5)
    o.data.materials.append(M_tree)

# lights: cold moon low behind the antenna (rim light), weak warm horizon fill, a small cab lamp
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(64), 0, math.radians(160)))
moon = bpy.context.object; moon.data.energy = 2.4; moon.data.color = (0.62, 0.74, 1.0); moon.data.angle = math.radians(1.0)
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(84), 0, math.radians(-70)))
sun = bpy.context.object; sun.data.energy = 0.35; sun.data.color = (1.0, 0.6, 0.38)
bpy.ops.object.light_add(type="POINT", location=(-9.0, 0.6, 2.6))
lamp = bpy.context.object; lamp.data.energy = 120; lamp.data.color = (1.0, 0.7, 0.4); lamp.data.shadow_soft_size = 0.15

cd = bpy.data.cameras.new("cam"); cd.sensor_width = 36
cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.clip_end = 1000


def aim(loc, tgt, lens):
    cam.location = loc; cd.lens = lens
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


STILLS = {
    "wide": ((24.0, -27.0, 8.5), (-1.5, 0, 4.0), 30),
    "throat": ((-15.5, -9.5, 3.0), (-8.6, 0, 3.6), 40),
    "low": ((14.0, -13.0, 0.9), (0.5, 0, 6.5), 22),
}
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "8"
if MODE == "still":
    name, spp, scale = argv[1], int(argv[2]), int(argv[3])
    sc.cycles.samples = spp; sc.render.resolution_percentage = scale
    aim(*STILLS[name])
    sc.render.filepath = os.path.join(SCR, "plates", f"horn_{name}.png")
    bpy.ops.render.render(write_still=True)
else:
    a0, a1, spp = int(argv[1]), int(argv[2]), int(argv[3])
    sc.cycles.samples = spp; sc.render.resolution_percentage = int(argv[4]) if len(argv) > 4 else 100
    od = os.path.join(SCR, "frames", "horn_orbit"); os.makedirs(od, exist_ok=True)
    for f in range(a0, a1):
        p = os.path.join(od, f"f_{f:04d}.png")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            continue
        s = f / (ORBIT_N - 1)
        e = s * s * (3 - 2 * s) * 0.35 + s * 0.65          # gentle ease
        ang = math.radians(-112 + 16 * e)
        d = 26.0 - 1.5 * e
        aim((-2.0 + math.cos(ang) * d, math.sin(ang) * d, 2.6 + 0.8 * e), (-1.5, 0, 4.4 + 0.2 * e), 30)
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print("frame", f, flush=True)
