"""Blender 5.1 (bpy module) scene for 06 Lituya Bay: stylised fjord terrain (pre-baked emission textures),
mirror-ish twilight water, numpy-baked twilight sky.  Renders plates the numpy compositor animates.

Run:  /home/user/bpyenv/bin/python -c "import sys;p='scene.py';sys.argv=['blender','--',CAM,PASS,SPP,W,H];exec(compile(open(p).read(),p,'exec'))"
  PASS = forest | strip | data      (data: emission = world position in metres, water z=-5, alpha 0 for sky)
Writes SCR/plates/{CAM}_{PASS}.npy (float16 HxWx3, or HxWx4 for data) and SCR/plates/{CAM}_cam.json."""
import sys, os, json, math
import numpy as np
import bpy
from mathutils import Vector

HERE = "/home/user/do-my-task/docs-series/06-lituya-bay"
sys.path.insert(0, HERE)
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
TER = os.path.join(SCR, "terrain")
OUT = os.path.join(SCR, "plates"); os.makedirs(OUT, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:]
CAM, PASS = argv[0], argv[1]
SPP = int(argv[2]) if len(argv) > 2 else 4
RW = int(argv[3]) if len(argv) > 3 else 2880
RH = int(argv[4]) if len(argv) > 4 else 1620
REG = {"main": (-10.0, 10.0, -4.0, 16.0), "patch": (-4.4, 0.6, 8.4, 13.4), "far": (-40.0, 40.0, -6.0, 56.0)}

# camera: location (m), target (m), lens (mm)  -- map frame: +y up-bay (~NE), -x = NW (Gilbert Inlet)
CAMS = {
    "wide":    ((-2600, -7200, 1250), (-500, 9200, 250), 30),
    "wide2":   ((-1900, -4200, 820), (-600, 9200, 300), 34),
    "top":     ((-300, 6200, 30000), None, 0),                 # orthographic map
    "gilbert": ((1500, 7000, 820), (-2100, 11050, 260), 28),
    "spur":    ((-1650, 11350, 640), (-1500, 9980, 230), 26),
    "entrance": ((900, 1250, 16), (-250, 9800, 330), 30),
    "after":   ((-200, 7600, 1150), (-1700, 10150, 180), 30),
}

sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SPP
sc.cycles.use_adaptive_sampling = False
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 1; sc.cycles.diffuse_bounces = 0; sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 0; sc.cycles.volume_bounces = 0; sc.cycles.transparent_max_bounces = 0
sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
try:
    sc.cycles.use_light_tree = False
except Exception:
    pass
sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("BTHREADS", "2"))
sc.render.resolution_x = RW; sc.render.resolution_y = RH; sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.film_transparent = (PASS == "data")
if PASS == "data":
    sc.cycles.filter_width = 0.01
    sc.cycles.samples = 1


def build_grid(name, reg, hpath, tex, hole=None):
    h = np.load(hpath).astype(np.float32)
    n = h.shape[0]
    x0, x1, y0, y1 = REG[reg]
    xs = np.linspace(x0, x1, n) * 1000.0; ys = np.linspace(y0, y1, n) * 1000.0
    X, Y = np.meshgrid(xs, ys)
    verts = np.stack([X, Y, h], -1).reshape(-1, 3).astype(np.float32)
    ii, jj = np.meshgrid(np.arange(n - 1), np.arange(n - 1))
    ii = ii.ravel(); jj = jj.ravel()
    if hole is not None:
        cx = (xs[ii] + xs[ii + 1]) / 2000.0; cy = (ys[jj] + ys[jj + 1]) / 2000.0
        hx0, hx1, hy0, hy1 = hole
        keep = ~((cx > hx0) & (cx < hx1) & (cy > hy0) & (cy < hy1))
        ii, jj = ii[keep], jj[keep]
    a = jj * n + ii
    quads = np.stack([a, a + 1, a + 1 + n, a + n], -1).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts)); me.vertices.foreach_set("co", verts.ravel())
    nf = len(quads)
    me.loops.add(nf * 4); me.loops.foreach_set("vertex_index", quads.ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * 4, 4, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(nf, 4, np.int32))
    uv = me.uv_layers.new(name="UVMap")
    vi = quads.ravel()
    u = (vi % n) / (n - 1); v = 1.0 - (vi // n) / (n - 1)     # PNG row 0 = south edge = top of the image
    uv.data.foreach_set("uv", np.stack([u, v], -1).astype(np.float32).ravel())
    me.update(calc_edges=True); me.validate(verbose=False)
    me.polygons.foreach_set("use_smooth", np.ones(nf, bool))
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + "_mat"); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    outp = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    if PASS == "data":
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        nt.links.new(geo.outputs["Position"], em.inputs["Color"])
    else:
        img = bpy.data.images.load(os.path.join(TER, f"{reg}_{tex}.png"))
        it = nt.nodes.new("ShaderNodeTexImage"); it.image = img; it.interpolation = "Linear"
        it.extension = "EXTEND"
        nt.links.new(it.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], outp.inputs["Surface"])
    ob.data.materials.append(mat)
    return ob


tex = "strip" if PASS == "strip" else "forest"
px, py_ = REG["patch"][:2], REG["patch"][2:]
build_grid("main", "main", os.path.join(TER, "main_h.npy"), tex,
           hole=(REG["patch"][0] + 0.03, REG["patch"][1] - 0.03, REG["patch"][2] + 0.03, REG["patch"][3] - 0.03))
build_grid("patch", "patch", os.path.join(TER, "patch_h.npy"), tex)
build_grid("far", "far", os.path.join(TER, "far_h.npy"), "forest", hole=(-9.95, 9.95, -3.95, 15.95))

# ------------------------------------------------------------------ water
bpy.ops.mesh.primitive_plane_add(size=400000, location=(0, 0, 0))
wat = bpy.context.active_object; wat.name = "water"
wm = bpy.data.materials.new("water"); wm.use_nodes = True
nt = wm.node_tree; nt.nodes.clear()
outp = nt.nodes.new("ShaderNodeOutputMaterial")
if PASS == "data":
    em = nt.nodes.new("ShaderNodeEmission")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); com = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nt.links.new(sep.outputs[0], com.inputs[0]); nt.links.new(sep.outputs[1], com.inputs[1])
    com.inputs[2].default_value = -5.0
    nt.links.new(com.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], outp.inputs["Surface"])
else:
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.035
    gl.inputs["Color"].default_value = (1, 1, 1, 1)
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.004, 0.007, 0.011, 1)
    em.inputs["Strength"].default_value = 1.0
    fr = nt.nodes.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.333
    # gentle ripples (world-space noise -> bump)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.02, 0.05, 0.02)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], gl.inputs["Normal"]); nt.links.new(bump.outputs["Normal"], fr.inputs["Normal"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fr.outputs[0], mix.inputs[0]); nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(gl.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], outp.inputs["Surface"])
wat.data.materials.append(wm)

# ------------------------------------------------------------------ twilight sky (numpy -> equirect image)
def sky_image(w=2048, h=1024):
    u = (np.arange(w) + 0.5) / w; v = (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    phi = (0.5 - U) * 2 * np.pi                 # Blender equirect: u = -atan2(y, x) / 2pi + 0.5 ; row 0 = bottom
    lat = (V - 0.5) * np.pi
    dx = np.cos(phi) * np.cos(lat); dy = np.sin(phi) * np.cos(lat); dz = np.sin(lat)
    e = np.clip(dz, -1, 1)
    az = math.radians(319 - 45)
    g = np.array([math.sin(az), math.cos(az)])                 # glow direction in map xy (~ -x)
    hor = np.sqrt(dx ** 2 + dy ** 2) + 1e-6
    cosg = (dx * g[0] + dy * g[1]) / hor
    ag = np.arccos(np.clip(cosg, -1, 1))                       # angle from glow azimuth
    ee = np.maximum(e, 0)
    zen = np.array([0.020, 0.040, 0.105]); horz = np.array([0.16, 0.20, 0.32])
    base = zen[None, None] + (horz - zen)[None, None] * np.exp(-ee / 0.28)[..., None]
    glow = np.exp(-(ag / 1.05) ** 2)[..., None] * np.exp(-ee / 0.10)[..., None] * np.array([1.10, 0.52, 0.26])
    glow2 = np.exp(-(ag / 0.6) ** 2)[..., None] * np.exp(-ee / 0.035)[..., None] * np.array([0.9, 0.48, 0.22])
    # anti-twilight: earth shadow (dark blue) + belt of venus (pink) opposite the glow
    opp = np.exp(-((np.pi - ag) / 1.3) ** 2)[..., None]
    belt = opp * np.exp(-((ee - 0.13) / 0.06) ** 2)[..., None] * np.array([0.12, 0.07, 0.09])
    shadow = opp * np.exp(-ee / 0.07)[..., None] * -0.06
    col = base * (1 + 0.0 * glow) + glow + glow2 + belt + shadow
    # a few faint stars high in the sky, opposite the glow
    rng = np.random.default_rng(3)
    st = np.zeros((h, w)); n = 260
    sx = rng.integers(0, w, n); sy = rng.integers(int(h * 0.62), h, n)
    st[sy, sx] = rng.uniform(0.2, 1.0, n) ** 3 * 0.6
    col += (st * np.clip((np.pi - ag) / np.pi, 0, 1) ** 2 * np.clip(e * 3, 0, 1))[..., None]
    col = np.where((e < 0)[..., None], horz[None, None] * 0.5, col)
    return np.clip(col, 0, None).astype(np.float32)


world = bpy.data.worlds.new("sky"); sc.world = world; world.use_nodes = True
nt = world.node_tree; nt.nodes.clear()
wo = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
if PASS == "data":
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
else:
    sk = sky_image()
    im = bpy.data.images.new("skyimg", sk.shape[1], sk.shape[0], float_buffer=True, alpha=False)
    px4 = np.concatenate([sk, np.ones(sk.shape[:2] + (1,), np.float32)], -1)
    im.pixels.foreach_set(px4.ravel())
    et = nt.nodes.new("ShaderNodeTexEnvironment"); et.image = im
    nt.links.new(et.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs[0], wo.inputs["Surface"])

# ------------------------------------------------------------------ camera
loc, tgt, lens = CAMS[CAM]
cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam)
sc.camera = cam
cd.clip_start = 5.0; cd.clip_end = 300000.0; cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36.0
cam.location = Vector(loc)
if CAM == "top":
    cd.type = "ORTHO"; cd.ortho_scale = 17500.0
    cam.rotation_euler = (0.0, 0.0, math.radians(-90))     # entrance on the left, head on the right
else:
    cd.lens = lens
    d = Vector(tgt) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()
mw = [list(r) for r in cam.matrix_world]
json.dump(dict(cam=CAM, matrix_world=mw, lens=cd.lens, sensor_width=36.0, ortho=(CAM == "top"),
               ortho_scale=cd.ortho_scale, res=[RW, RH], loc=list(loc), tgt=tgt),
          open(os.path.join(OUT, f"{CAM}_cam.json"), "w"), indent=1)

# ------------------------------------------------------------------ render
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "OPEN_EXR"
sc.render.image_settings.color_depth = "32"
sc.render.image_settings.color_mode = "RGBA" if PASS == "data" else "RGB"
exr = os.path.join(OUT, f"{CAM}_{PASS}.exr")
sc.render.filepath = exr
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(exr)
w, h = img.size
pxs = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(pxs)
pxs = pxs.reshape(h, w, 4)[::-1]
arr = pxs if PASS == "data" else pxs[..., :3]
np.save(os.path.join(OUT, f"{CAM}_{PASS}.npy"), arr.astype(np.float32 if PASS == "data" else np.float16))
os.remove(exr)
print("saved", CAM, PASS, arr.shape, float(arr[..., :3].max()))
