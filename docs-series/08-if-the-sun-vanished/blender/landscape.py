"""Blender (bpy 5.1.2, Cycles CPU) still plates for 08 'If the Sun vanished right now': one locked-off lake-and-mountain
view rendered as separable light passes, so the compositor can relight it (day / moonlight / starlight / frozen).
  landscape.py <variant: rock|snow> <pass: sun|amb|depth|mirror> <spp>
-> SCR/plates/land_<variant>_<pass>.png  (2560x1440, 16-bit, Standard view transform, transparent sky)
Run: /home/user/bpyenv/bin/python -c "import sys;p='blender/landscape.py';sys.argv=['blender','--','rock','sun','64'];exec(compile(open(p).read(),p,'exec'))"
"""
import bpy, math, sys, os
import numpy as np
argv = sys.argv[sys.argv.index("--") + 1:]
VAR, PASS, SPP = argv[0], argv[1], int(argv[2])
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/08-if-the-sun-vanished"
OUT = os.path.join(SCR, "plates"); os.makedirs(OUT, exist_ok=True)
RW, RH = int(os.environ.get("RW", 2304)), int(os.environ.get("RH", 1296))
LENS, SHIFT_Y = 26.0, 0.06
SUN_EL, SUN_AZ = 15.0, -22.0     # degrees; azimuth from +y (view axis) towards +x

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.cycles.samples = SPP
sc.cycles.use_denoising = PASS in ("sun", "amb"); sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 0; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.view_settings.view_transform = "Standard"
sc.render.film_transparent = True
sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "16"
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
sc.render.threads_mode = "FIXED"; sc.render.threads = 3
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (1, 1, 1, 1); bg.inputs[1].default_value = 1.0 if PASS == "amb" else 0.0

def link(ob): sc.collection.objects.link(ob); return ob

# ------------------------------------------------------------------ terrain heightfield (numpy, spectral fbm)
N = 1500
XS = np.linspace(-70, 70, N); YS = np.linspace(-6, 134, N)
X, Y = np.meshgrid(XS, YS)
def spectral(seed, beta, n=N):
    r = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.rfftfreq(n)[None, :] ** 2
    f[0, 0] = 1
    amp = f ** (-beta / 2.0); amp[0, 0] = 0
    ph = r.uniform(0, 2 * np.pi, amp.shape)
    z = np.fft.irfft2(amp * np.exp(1j * ph), s=(n, n))
    return (z - z.mean()) / z.std()
a = spectral(3, 1.8); b = spectral(8, 1.95); c = spectral(21, 1.5); e = spectral(33, 1.7)
ridge = 1 - np.abs(a) * 0.85
ridge = np.clip(ridge, -1, 1)
ridge2 = 1 - np.abs(e)                                         # finer secondary ridges (spurs, gullies)
far = 1 / (1 + np.exp(-(Y - 38) / 6.0))                       # mountains rise beyond y ~ 38
side = np.clip((np.abs(X) - 15) / 24, 0, 1) ** 1.3 * np.clip(1 - (Y - 4) / 60, 0.25, 1)
M = np.clip(0.55 + 0.55 * ridge + 0.22 * b, 0.02, 2.0) ** 1.45         # sharpened: flat valleys, steep peaks
Z = far * (15.0 * M + 1.5) + side * (4.0 + 3.0 * b + 4.5 * M) + 0.45 * b
Z += (far + side) * np.clip(M, 0, 1.2) * (1.5 * ridge2 + 0.55 * c)
Z += 0.07 * c
basin = np.exp(-((X / 30.0) ** 2 + ((Y - 20) / 20.0) ** 2) ** 1.4)
Z = Z * (1 - 0.95 * basin) - 1.1 * basin
# open water in front of the camera
near = np.clip(1 - (Y - 6) / 9.0, 0, 1) * np.exp(-(X / 30.0) ** 4)
Z = Z * (1 - near) - 0.7 * near
if VAR == "snow":
    # snow blanket: fills hollows a little, rounds the detail
    Z = Z + 0.10 + 0.05 * b
verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
idx = np.arange(N * N).reshape(N, N)
faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
me = bpy.data.meshes.new("terrain")
me.vertices.add(N * N); me.vertices.foreach_set("co", verts.ravel())
me.loops.add(faces.size); me.loops.foreach_set("vertex_index", faces.ravel())
me.polygons.add(len(faces)); me.polygons.foreach_set("loop_start", np.arange(0, faces.size, 4)); me.polygons.foreach_set("loop_total", np.full(len(faces), 4))
me.update(); me.validate()
me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
# vertex colours: altitude / slope driven
gy, gx = np.gradient(Z, YS[1] - YS[0], XS[1] - XS[0])
slope = np.sqrt(gx ** 2 + gy ** 2)
nz = spectral(55, 1.5)
if VAR == "rock":
    rockc = np.array([0.20, 0.185, 0.17]); grass = np.array([0.095, 0.135, 0.055]); forest = np.array([0.035, 0.065, 0.03])
    sand = np.array([0.30, 0.26, 0.20]); snowc = np.array([0.86, 0.88, 0.92])
    strata = 0.93 + 0.07 * np.sin(Z * 4.3 + 5 * nz + 3 * b)[..., None]
    col = np.broadcast_to(rockc, Z.shape + (3,)).copy() * (0.8 + 0.3 * nz[..., None]).clip(0.45, 1.5) * strata * (1 + 0.12 * np.array([1, 0.2, -0.6]) * spectral(60, 2.2)[..., None])
    veg = np.clip(1 - slope / 0.75, 0, 1) * np.clip((6.0 - Z) / 3.0, 0, 1)
    fmask = np.clip((nz + 0.2) * 2, 0, 1)[..., None]
    vcol = grass * (1 - fmask) + forest * fmask
    col = col * (1 - veg[..., None]) + vcol * veg[..., None]
    sh = np.clip(1 - (Z - 0.02) / 0.5, 0, 1)[..., None]
    col = col * (1 - sh) + sand * sh * (0.75 + 0.2 * nz[..., None])
    sn = (np.clip((Z - 8.0 + 1.8 * b) / 2.5, 0, 1) * np.clip(1.9 - slope / 1.3, 0, 1))[..., None]
    col = col * (1 - sn) + snowc * sn
else:
    snowc = np.array([0.80, 0.84, 0.90]); rockc = np.array([0.10, 0.10, 0.105])
    bare = np.clip((slope - 1.05 + 0.25 * nz) / 0.5, 0, 1)[..., None]
    col = snowc * (1 - bare) + rockc * bare
rgba = np.concatenate([col, np.ones(Z.shape + (1,))], -1).reshape(-1, 4).astype(np.float32)
ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT"); ca.data.foreach_set("color", rgba.ravel())
terr = link(bpy.data.objects.new("terrain", me))

def emis_mat(name, build):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree
    for n in list(t.nodes): t.nodes.remove(n)
    out = t.nodes.new("ShaderNodeOutputMaterial"); build(t, out); return m

def depth_color(t, flag):
    """emission = (flag, viewdist/200, 0)"""
    cd = t.nodes.new("ShaderNodeCameraData"); mul = t.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 1 / 200.0
    t.links.new(cd.outputs["View Distance"], mul.inputs[0])
    cmb = t.nodes.new("ShaderNodeCombineColor"); cmb.inputs[0].default_value = flag; t.links.new(mul.outputs[0], cmb.inputs[1]); cmb.inputs[2].default_value = 0
    em = t.nodes.new("ShaderNodeEmission"); t.links.new(cmb.outputs[0], em.inputs[0]); return em

if PASS in ("sun", "amb"):
    m = bpy.data.materials.new("ground"); m.use_nodes = True; t = m.node_tree; bsdf = t.nodes["Principled BSDF"]
    vc = t.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    t.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9 if VAR == "rock" else 0.6
    tc = t.nodes.new("ShaderNodeTexCoord")
    n1 = t.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 3.0 if VAR == "rock" else 1.2; n1.inputs["Detail"].default_value = 12; n1.inputs["Roughness"].default_value = 0.62
    t.links.new(tc.outputs["Object"], n1.inputs["Vector"])
    bump = t.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.9 if VAR == "rock" else 0.35; bump.inputs["Distance"].default_value = 0.12
    t.links.new(n1.outputs["Fac"], bump.inputs["Height"]); t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
elif PASS == "depth":
    m = emis_mat("d", lambda t, out: t.links.new(depth_color(t, 1.0).outputs[0], out.inputs[0]))
else:
    def b_(t, out):
        em = t.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (1, 1, 1, 1); t.links.new(em.outputs[0], out.inputs[0])
    m = emis_mat("white", b_)
terr.data.materials.append(m)

# ------------------------------------------------------------------ lake (z = 0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 60, 0)); lake = bpy.context.active_object; lake.scale = (300, 300, 1)
if PASS == "depth":
    lm = emis_mat("ld", lambda t, out: t.links.new(depth_color(t, 0.0).outputs[0], out.inputs[0]))
elif VAR == "snow" and PASS in ("sun", "amb"):
    lm = bpy.data.materials.new("ice"); lm.use_nodes = True; t = lm.node_tree; bsdf = t.nodes["Principled BSDF"]
    tc = t.nodes.new("ShaderNodeTexCoord"); n1 = t.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 10
    t.links.new(tc.outputs["Object"], n1.inputs["Vector"]); t.nodes.remove(tc) if False else None
    mp = t.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (300, 300, 1)
    t.links.new(tc.outputs["Object"], mp.inputs[0]); t.links.new(mp.outputs[0], n1.inputs["Vector"])
    ramp = t.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.62, 0.70, 0.80, 1)
    ramp.color_ramp.elements[1].position = 0.7; ramp.color_ramp.elements[1].color = (0.82, 0.86, 0.92, 1)
    t.links.new(n1.outputs["Fac"], ramp.inputs[0]); t.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    bump = t.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.05
    t.links.new(n1.outputs["Fac"], bump.inputs["Height"]); t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
else:
    # mirror water with a faint ripple bump (reflects the terrain; the sky reflection is added in the compositor)
    lm = bpy.data.materials.new("water"); lm.use_nodes = True; t = lm.node_tree; bsdf = t.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1); bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.0 if PASS == "mirror" else 0.03
    if PASS != "mirror":
        tc = t.nodes.new("ShaderNodeTexCoord"); mp = t.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (300 * 1.2, 300 * 5.0, 1)
        n1 = t.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 1.0; n1.inputs["Detail"].default_value = 3
        t.links.new(tc.outputs["Object"], mp.inputs[0]); t.links.new(mp.outputs[0], n1.inputs["Vector"])
        bump = t.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.06; bump.inputs["Distance"].default_value = 0.02
        t.links.new(n1.outputs["Fac"], bump.inputs["Height"]); t.links.new(bump.outputs[0], bsdf.inputs["Normal"])
lake.data.materials.append(lm)

# ------------------------------------------------------------------ craggy rocks standing in the water
rr = np.random.default_rng(4)
bm_ = bpy.data.materials.new("boulder"); bm_.use_nodes = True; bt = bm_.node_tree
bb = bt.nodes["Principled BSDF"]; bb.inputs["Roughness"].default_value = 0.8
tcb = bt.nodes.new("ShaderNodeTexCoord"); nb = bt.nodes.new("ShaderNodeTexNoise"); nb.inputs["Scale"].default_value = 9; nb.inputs["Detail"].default_value = 12; nb.inputs["Roughness"].default_value = 0.7
bt.links.new(tcb.outputs["Object"], nb.inputs["Vector"])
rb = bt.nodes.new("ShaderNodeValToRGB")
if VAR == "snow":
    rb.color_ramp.elements[0].color = (0.55, 0.60, 0.68, 1); rb.color_ramp.elements[1].color = (0.85, 0.88, 0.93, 1)
else:
    rb.color_ramp.elements[0].color = (0.05, 0.048, 0.045, 1); rb.color_ramp.elements[1].color = (0.27, 0.25, 0.22, 1)
bt.links.new(nb.outputs["Fac"], rb.inputs[0]); bt.links.new(rb.outputs[0], bb.inputs["Base Color"])
bpb = bt.nodes.new("ShaderNodeBump"); bpb.inputs["Strength"].default_value = 0.8; bpb.inputs["Distance"].default_value = 0.05
bt.links.new(nb.outputs["Fac"], bpb.inputs["Height"]); bt.links.new(bpb.outputs[0], bb.inputs["Normal"])
t1 = bpy.data.textures.new("vor", "VORONOI"); t1.noise_scale = 0.55; t1.distance_metric = "DISTANCE"
t2 = bpy.data.textures.new("cl", "CLOUDS"); t2.noise_scale = 0.16; t2.noise_depth = 5
for (x, y, s) in [(-6.3, 3.6, 0.8), (-4.7, 4.7, 0.36), (5.6, 3.0, 0.62), (7.3, 4.6, 0.33), (3.9, 6.8, 0.27), (-9.8, 8.2, 0.6), (11.5, 9.0, 0.7),
                  (-2.6, 9.6, 0.2), (1.6, 13.5, 0.24), (-7.6, 3.0, 0.22), (6.6, 2.3, 0.2), (-13, 12, 0.5), (15, 14, 0.55), (-5.2, 3.4, 0.16)]:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=s, location=(x, y, -s * 0.12))
    o = bpy.context.active_object; o.scale = (rr.uniform(0.9, 1.5), rr.uniform(0.8, 1.3), rr.uniform(0.55, 0.85)); o.rotation_euler = (rr.uniform(-0.2, 0.2), rr.uniform(-0.2, 0.2), rr.uniform(0, 6))
    d1 = o.modifiers.new("d1", "DISPLACE"); d1.texture = t1; d1.strength = s * 0.4; d1.texture_coords = "GLOBAL"
    d2 = o.modifiers.new("d2", "DISPLACE"); d2.texture = t2; d2.strength = s * 0.28; d2.texture_coords = "GLOBAL"
    bpy.ops.object.shade_smooth()
    o.data.materials.append(m if PASS in ("depth", "mirror") else bm_)

# ------------------------------------------------------------------ light + camera
if PASS == "sun":
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = 3.0; ld.angle = math.radians(0.6)
    so = link(bpy.data.objects.new("sun", ld))
    el, az = math.radians(SUN_EL), math.radians(SUN_AZ)
    d = np.array([math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)])   # direction TO the sun
    from mathutils import Vector
    so.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()
cd = bpy.data.cameras.new("cam"); cd.lens = LENS; cd.sensor_width = 36; cd.shift_y = SHIFT_Y; cd.clip_end = 1000
co = link(bpy.data.objects.new("cam", cd)); co.location = (0, -5.2, 1.75); co.rotation_euler = (math.radians(90), 0, 0)
sc.camera = co
sc.render.filepath = os.path.join(OUT, f"land_{VAR}_{PASS}.png")
bpy.ops.render.render(write_still=True)
print("done", sc.render.filepath)
