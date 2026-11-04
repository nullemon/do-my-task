"""Blender (bpy 5.1.2, Cycles CPU) stills for 05 'Falling into the Mariana Trench'.

Modes:
  floor <A|B> <spp> <scale%>   -> SCR/plates/floor_<A|B>.png  soft hadal sediment lit only by our own lamp
  vessel <trieste|challenger|limiting> <spp>  -> SCR/plates/vessel_<name>.png (RGBA sprite, transparent bg)
Vessels are deliberately simplified, stylised silhouettes (overall proportions only), lit by their own lamps.
Run: /home/user/bpyenv/bin/python -c "import sys;p='deep3d.py';sys.argv=['blender','--','floor','A','32','150'];exec(compile(open(p).read(),p,'exec'))"
"""
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0]
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/05-mariana-trench"
OUT = os.path.join(SCR, "plates"); os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 2
sc.cycles.diffuse_bounces = 1
sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 0
sc.cycles.transparent_max_bounces = 2
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.view_settings.view_transform = "Standard"
sc.render.filter_size = 1.4
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_depth = "16"

w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.0


def mat(name, col, rough=0.6, emit=None, es=0.0, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = es
    return m


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def spot(name, loc, rot, energy, size_deg, blend=0.6, col=(0.85, 0.92, 1.0), radius=0.05):
    ld = bpy.data.lights.new(name, "SPOT"); ld.energy = energy; ld.spot_size = math.radians(size_deg)
    ld.spot_blend = blend; ld.color = col; ld.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, ld); ob.location = loc; ob.rotation_euler = rot
    return link(ob)


def cam(loc, rot, lens=32):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = 36
    ob = bpy.data.objects.new("cam", cd); ob.location = loc; ob.rotation_euler = rot
    link(ob); sc.camera = ob
    return ob


# ------------------------------------------------------------------------------------------------ floor
def fbm(x, y, seed, octaves=5, base=0.08):
    r = np.random.default_rng(seed)
    out = np.zeros_like(x)
    amp, f = 1.0, base
    for o in range(octaves):
        th = r.uniform(0, 6.28, 6); ph = r.uniform(0, 6.28, 6)
        acc = np.zeros_like(x)
        for k in range(6):
            acc += np.sin((x * math.cos(th[k]) + y * math.sin(th[k])) * f * 6.28 + ph[k])
        out += amp * acc / 6
        amp *= 0.5; f *= 2.03
    return out


def build_floor():
    n = 420
    xs = np.linspace(-30, 30, n); ys = np.linspace(-6, 54, n)
    X, Y = np.meshgrid(xs, ys)
    Z = 0.32 * fbm(X, Y, 3, 4, 0.025) + 0.06 * fbm(X, Y, 7, 4, 0.35) + 0.018 * fbm(X, Y, 9, 2, 1.6)
    # soft hummocks and a few burrow pits / mounds (generic ooze features)
    r = np.random.default_rng(11)
    for _ in range(70):
        cx, cy = r.uniform(-14, 14), r.uniform(0, 30); s = r.uniform(0.15, 0.7)
        h = r.choice([-1, 1]) * r.uniform(0.02, 0.09)
        Z += h * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * s * s))
    me = bpy.data.meshes.new("floor")
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    faces = []
    idx = np.arange(n * n).reshape(n, n)
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    faces = np.stack([a, b, c, d], 1)
    me.from_pydata(verts.tolist(), [], faces.tolist())
    for p in me.polygons: p.use_smooth = True
    ob = link(bpy.data.objects.new("floor", me))
    m = bpy.data.materials.new("ooze"); m.use_nodes = True
    t = m.node_tree; bsdf = t.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.95
    tc = t.nodes.new("ShaderNodeTexCoord")
    nz = t.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 8
    t.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = t.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.30, 0.29, 0.26, 1)
    ramp.color_ramp.elements[1].color = (0.55, 0.53, 0.47, 1)
    t.links.new(nz.outputs["Fac"], ramp.inputs[0]); t.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    # fine grain bump (flocculent ooze)
    nz2 = t.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 22; nz2.inputs["Detail"].default_value = 9; nz2.inputs["Roughness"].default_value = 0.62
    t.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    bump = t.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8
    t.links.new(nz2.outputs["Fac"], bump.inputs["Height"]); t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    ob.data.materials.append(m)
    # scattered tiny lumps (fallen organic debris / aggregates)
    rr = np.random.default_rng(5)
    dm = mat("debris", (0.36, 0.34, 0.3), 0.9)
    for i in range(90):
        x, y = rr.uniform(-9, 9), rr.uniform(1.5, 22)
        s = rr.uniform(0.012, 0.05)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=s, location=(x, y, 0))
        o = bpy.context.active_object
        o.scale = (1, rr.uniform(0.6, 1.6), rr.uniform(0.25, 0.45))
        zi = np.interp(y, ys, np.arange(n)); xi = np.interp(x, xs, np.arange(n))
        o.location.z = Z[int(zi), int(xi)] + s * 0.2
        o.data.materials.append(dm)


def floor(view, spp, scale):
    build_floor()
    if view == "A":      # oblique, looking ahead across the floor
        cam((0, -2.0, 2.3), (math.radians(58), 0, 0), lens=28)
        spot("lamp", (1.6, -2.4, 3.6), (math.radians(42), math.radians(14), 0), 260, 62, 0.85)
        spot("lamp2", (-1.4, -2.0, 2.9), (math.radians(52), math.radians(-12), 0), 90, 55, 0.9, col=(0.8, 0.88, 1.0))
    else:                # closer, steeper (amphipod scene)
        cam((0, 0.0, 1.35), (math.radians(38), 0, 0), lens=30)
        spot("lamp", (1.2, -0.6, 2.4), (math.radians(26), math.radians(18), 0), 140, 70, 0.85)
    sc.cycles.samples = spp
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = scale
    sc.render.filepath = os.path.join(OUT, f"floor_{view}.png")
    bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------------------------------------ vessels
def cyl(r, depth, loc, rot=(0, 0, 0), m=None, verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=rot, vertices=verts)
    o = bpy.context.active_object
    if m: o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def sph(r, loc, m=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    o = bpy.context.active_object; o.scale = scale
    if m: o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def box(size, loc, m=None, bevel=0.05):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.scale = size
    if bevel:
        bm = o.modifiers.new("b", "BEVEL"); bm.width = bevel; bm.segments = 3
    if m: o.data.materials.append(m)
    return o


def lamp_glow(loc, r=0.06, col=(0.85, 0.93, 1.0), es=25):
    return sph(r, loc, mat("lamp", (0, 0, 0), emit=col, es=es))


def vessel(name, spp):
    paint = mat("paint", (0.62, 0.64, 0.66), 0.45)
    dark = mat("dark", (0.05, 0.05, 0.06), 0.5)
    ti = mat("ti", (0.55, 0.55, 0.57), 0.35, metal=0.8)
    if name == "trieste":
        # float: long cigar hull with a flat deck, observation sphere slung beneath, two shot-ballast tubs
        hull = sph(1.0, (0, 0, 0), paint, scale=(7.5, 1.7, 1.75))
        box((8.0, 1.3, 0.14), (0, 0, 1.72), dark, 0.02)               # deck
        box((1.1, 0.9, 1.0), (1.2, 0, 2.2), paint, 0.12)              # small conning tower
        cyl(0.9, 1.6, (-3.0, 0, -1.6), m=dark)                         # ballast tubs
        cyl(0.9, 1.6, (2.6, 0, -1.6), m=dark)
        cyl(0.35, 1.0, (0, 0, -1.9), m=dark)                           # access tube
        sph(1.08, (0, 0, -2.7), ti)                                    # crew sphere
        lamp_glow((0.0, -0.95, -2.95), 0.08)
        lamp_glow((-6.8, 0, -0.8), 0.07); lamp_glow((6.8, 0, -0.8), 0.07)
        target, dist, ortho = (0, 0, -0.4), 30, 19.0
        lamps = [((0, -1.5, -3.3), (math.radians(150), 0, 0)), ((-6.8, -0.6, -1.2), (math.radians(160), 0, 0))]
    elif name == "challenger":
        # vertical 'torpedo': tall streamlined body, pilot sphere at the base, a lamp boom across it
        lime = mat("lime", (0.38, 0.62, 0.12), 0.4)
        body = sph(1.0, (0, 0, 0.6), lime, scale=(0.85, 0.85, 3.5))
        cyl(0.07, 3.2, (0, 0, -0.9), (0, math.radians(90), 0), dark)   # lamp boom
        for x in (-1.55, 1.55):
            lamp_glow((x, -0.12, -0.9), 0.09)
        sph(0.62, (0, 0, -2.75), ti)                                    # pilot sphere
        for z in (2.5, 3.2):
            cyl(0.12, 0.4, (0.7, 0, z), (0, math.radians(90), 0), dark)  # thrusters
            cyl(0.12, 0.4, (-0.7, 0, z), (0, math.radians(90), 0), dark)
        target, dist, ortho = (0, 0, 0.3), 30, 9.6
        lamps = [((1.55, -0.6, -1.2), (math.radians(165), 0, 0)), ((-1.55, -0.6, -1.2), (math.radians(165), 0, 0))]
    else:
        # Triton-style full-ocean-depth sub: tall slab-sided foam body, titanium sphere low at the front,
        # vertical/horizontal thrusters, lamp bar
        white = mat("white", (0.8, 0.8, 0.78), 0.5)
        box((3.9, 1.9, 3.2), (-0.3, 0, 0.9), white, 0.2)
        fr = box((1.3, 1.9, 2.6), (1.55, 0, 1.25), white, 0.2); fr.rotation_euler = (0, math.radians(-22), 0)
        box((3.4, 1.5, 0.35), (-0.4, 0, 2.6), dark, 0.08)
        box((4.4, 2.0, 0.22), (0.1, 0, -0.75), dark, 0.04)              # skids frame
        sph(0.8, (1.95, 0, -0.35), ti)
        box((0.22, 2.05, 0.18), (2.55, 0, 0.75), dark, 0.02)            # lamp bar
        for y in (-0.8, -0.27, 0.27, 0.8):
            lamp_glow((2.68, y, 0.75), 0.07)
        for x in (-1.6, 0.6):
            cyl(0.3, 0.5, (x, 0, 3.0), m=dark)                          # vertical thrusters
        cyl(0.32, 0.7, (-2.5, -0.7, 0.4), (0, math.radians(90), 0), dark)
        cyl(0.32, 0.7, (-2.5, 0.7, 0.4), (0, math.radians(90), 0), dark)
        target, dist, ortho = (0.1, 0, 0.9), 30, 7.6
        lamps = [((2.6, -0.5, 0.2), (math.radians(110), 0, math.radians(-90))), ((2.6, 0.5, 0.2), (math.radians(110), 0, math.radians(-90)))]
    # three-quarter camera, orthographic for a clean diagram-like sprite
    yaw = math.radians({"trieste": -28, "challenger": -20}.get(name, 58))
    loc = Vector(target) + Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, 1.5))
    c = cam(tuple(loc), (0, 0, 0))
    c.data.type = "ORTHO"; c.data.ortho_scale = ortho
    d = Vector(target) - loc
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # cold rim light from above-behind (residual of our scene lighting) + soft fill from the camera side
    spot("rim", (-6, 10, 14), Vector((6, -10, -14)).to_track_quat("-Z", "Y").to_euler(), 9000, 50, 0.9, col=(0.55, 0.7, 1.0), radius=2)
    spot("fill", tuple(loc + Vector((0, 0, 6))), (Vector(target) - loc - Vector((0, 0, 6))).to_track_quat("-Z", "Y").to_euler(),
         2600, 40, 0.9, col=(0.6, 0.72, 0.95), radius=3)
    for i, (p, r) in enumerate(lamps):
        spot(f"own{i}", p, r, 300, 60, 0.8)
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = "RGBA"
    sc.cycles.samples = spp
    sc.render.resolution_x = sc.render.resolution_y = 900
    if name == "trieste":
        sc.render.resolution_x, sc.render.resolution_y = 1200, 800
    sc.render.resolution_percentage = 100
    sc.render.filepath = os.path.join(OUT, f"vessel_{name}.png")
    bpy.ops.render.render(write_still=True)


if MODE == "floor":
    floor(argv[1], int(argv[2]), int(argv[3]))
else:
    vessel(argv[1], int(argv[2]))
