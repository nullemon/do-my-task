"""Blender 5.1 (bpy module): the wave arriving at the Edrie (shot B1) as a real displaced mesh.
A ~32 m water wall (steep dark face, curling lip, turbulent back) whose front is curved (the centre of the bay leads),
with per-vertex foam (crest, streaks running down the face, churn behind), twilight sky reflections (Fresnel glossy)
and two translucent spray sheets above the crest.  Rendered alone with a transparent film through a camera that
matches the compositor's crop of the 'entrance' plate frame by frame (lens = 30 mm x zoom, lens shift = pan).
Usage: /home/user/bpyenv/bin/python -c "import sys;p='wave.py';sys.argv=['blender','--',F0,F1];exec(...)"
Writes SCR/wave/w_XXXX.png (RGBA, sRGB, straight alpha). Skips existing frames."""
import sys, os, json, math
import numpy as np
import bpy
from mathutils import Vector

HERE = "/home/user/do-my-task/docs-series/06-lituya-bay"
sys.path.insert(0, HERE)
import world as Wd
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
OUT = os.path.join(SCR, "wave"); os.makedirs(OUT, exist_ok=True)
PRM = json.load(open(os.path.join(SCR, "wave_params.json")))
argv = sys.argv[sys.argv.index("--") + 1:]
F0 = int(argv[0]) if argv else PRM["frames"][0]["f"]
F1 = int(argv[1]) if len(argv) > 1 else PRM["frames"][-1]["f"] + 1
SPP = int(os.environ.get("WSPP", "6"))
HW = 32.0
XC = 250.0                     # bay centre line near the entrance (m)
CURVE = 1.2e-4                 # front lags towards the shores: y_front(x) = yf + CURVE (x - XC)^2

sc = bpy.context.scene
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.cycles.samples = SPP; sc.cycles.use_adaptive_sampling = False; sc.cycles.use_denoising = False
sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 0; sc.cycles.glossy_bounces = 1
sc.cycles.transmission_bounces = 0; sc.cycles.transparent_max_bounces = 3
sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("BTHREADS", "2"))
sc.render.resolution_x = 1920; sc.render.resolution_y = 1080; sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
sc.render.film_transparent = True
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "8"

# ------------------------------------------------------------------ sky (same function as scene.py, re-used for reflections)
src = open(os.path.join(HERE, "scene.py")).read()
a = src.index("def sky_image("); b = src.index("world = bpy.data.worlds.new")
exec(src[a:b])
world = bpy.data.worlds.new("sky"); sc.world = world; world.use_nodes = True
nt = world.node_tree; nt.nodes.clear()
wo = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
sk = sky_image()
im = bpy.data.images.new("skyimg", sk.shape[1], sk.shape[0], float_buffer=True, alpha=False)
im.pixels.foreach_set(np.concatenate([sk, np.ones(sk.shape[:2] + (1,), np.float32)], -1).ravel())
et = nt.nodes.new("ShaderNodeTexEnvironment"); et.image = im
nt.links.new(et.outputs["Color"], bg.inputs["Color"]); nt.links.new(bg.outputs[0], wo.inputs["Surface"])

# ------------------------------------------------------------------ wave mesh topology
NX, NS = 1400, 70
xs = np.linspace(-1500, 1900, NX)
# cross-section profile (s = metres behind the toe, z / H): toe, steep face, curling lip, crest, turbulent back
PROF = np.array([(-25, 0.0), (-6, 0.0), (0, 0.04), (6, 0.18), (12, 0.42), (17, 0.70), (20, 0.88), (20.5, 0.98),
                 (19, 1.06), (22, 1.10), (30, 1.08), (45, 0.98), (70, 0.86), (110, 0.72), (170, 0.58), (260, 0.45),
                 (400, 0.33)])
seg = np.hypot(np.diff(PROF[:, 0]) / 30.0, np.diff(PROF[:, 1]))
cum = np.concatenate([[0], np.cumsum(seg)]); tt = np.linspace(0, cum[-1], NS)
PS = np.interp(tt, cum, PROF[:, 0]); PZ = np.interp(tt, cum, PROF[:, 1])
TV = tt / cum[-1]                            # 0 at the toe .. 1 far behind


def make_grid(name, nx, ns):
    me = bpy.data.meshes.new(name)
    me.vertices.add(nx * ns)
    ii, jj = np.meshgrid(np.arange(nx - 1), np.arange(ns - 1))
    a_ = (jj * nx + ii).ravel()
    q = np.stack([a_, a_ + 1, a_ + nx + 1, a_ + nx], -1).astype(np.int32)
    me.loops.add(q.size); me.loops.foreach_set("vertex_index", q.ravel())
    me.polygons.add(len(q)); me.polygons.foreach_set("loop_start", np.arange(0, q.size, 4, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(q), 4, np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(q), bool))
    me.color_attributes.new("foam", "FLOAT_COLOR", "POINT")
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    return ob


wave = make_grid("wave", NX, NS)
NSP = 14
spray = make_grid("spray", NX // 2, NSP)
spray2 = make_grid("spray2", NX // 2, NSP)


def mat_wave():
    m = bpy.data.materials.new("wave"); m.use_nodes = True
    n = m.node_tree; n.nodes.clear()
    out = n.nodes.new("ShaderNodeOutputMaterial")
    gl = n.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.22
    em = n.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.006, 0.010, 0.014, 1)
    fr = n.nodes.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.333
    # fine turbulent bump
    tc = n.nodes.new("ShaderNodeTexCoord")
    nz = n.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.35; nz.inputs["Detail"].default_value = 6
    nz.noise_dimensions = "4D"; nz.name = "nz"
    bump = n.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    n.links.new(tc.outputs["Object"], nz.inputs["Vector"]); n.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    n.links.new(bump.outputs["Normal"], gl.inputs["Normal"]); n.links.new(bump.outputs["Normal"], fr.inputs["Normal"])
    mw = n.nodes.new("ShaderNodeMixShader")
    n.links.new(fr.outputs[0], mw.inputs[0]); n.links.new(em.outputs[0], mw.inputs[1]); n.links.new(gl.outputs[0], mw.inputs[2])
    # foam: vertex attribute x detail noise
    at = n.nodes.new("ShaderNodeAttribute"); at.attribute_name = "foam"
    sep = n.nodes.new("ShaderNodeSeparateColor")
    n.links.new(at.outputs["Color"], sep.inputs[0])
    nz2 = n.nodes.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 1.6; nz2.inputs["Detail"].default_value = 8
    nz2.noise_dimensions = "4D"; nz2.name = "nz2"
    n.links.new(tc.outputs["Object"], nz2.inputs["Vector"])
    # foam coverage = clamp((attr - (1 - noise)) * 3)
    sub = n.nodes.new("ShaderNodeMath"); sub.operation = "ADD"
    inv = n.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    n.links.new(nz2.outputs["Fac"], inv.inputs[1])
    mul = n.nodes.new("ShaderNodeMath"); mul.operation = "SUBTRACT"
    n.links.new(sep.outputs[0], mul.inputs[0]); n.links.new(inv.outputs[0], mul.inputs[1])
    cov = n.nodes.new("ShaderNodeMath"); cov.operation = "MULTIPLY"; cov.use_clamp = True; cov.inputs[1].default_value = 3.0
    n.links.new(mul.outputs[0], cov.inputs[0])
    fe = n.nodes.new("ShaderNodeEmission")
    # foam brightness (lit side) from the G channel
    cmb = n.nodes.new("ShaderNodeCombineColor")
    for c, k in ((0, 0.40), (1, 0.45), (2, 0.53)):
        mm = n.nodes.new("ShaderNodeMath"); mm.operation = "MULTIPLY"; mm.inputs[1].default_value = k
        n.links.new(sep.outputs[1], mm.inputs[0]); n.links.new(mm.outputs[0], cmb.inputs[c])
    n.links.new(cmb.outputs[0], fe.inputs["Color"])
    mf = n.nodes.new("ShaderNodeMixShader")
    n.links.new(cov.outputs[0], mf.inputs[0]); n.links.new(mw.outputs[0], mf.inputs[1]); n.links.new(fe.outputs[0], mf.inputs[2])
    n.links.new(mf.outputs[0], out.inputs["Surface"])
    return m


def mat_spray(strength):
    m = bpy.data.materials.new("spray"); m.use_nodes = True
    n = m.node_tree; n.nodes.clear()
    out = n.nodes.new("ShaderNodeOutputMaterial")
    tr = n.nodes.new("ShaderNodeBsdfTransparent")
    em = n.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.30, 0.34, 0.40, 1)
    em.inputs["Strength"].default_value = 1.0
    tc = n.nodes.new("ShaderNodeTexCoord")
    nz = n.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.11; nz.inputs["Detail"].default_value = 5
    nz.inputs["Roughness"].default_value = 0.65; nz.noise_dimensions = "4D"; nz.name = "nz"
    n.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    at = n.nodes.new("ShaderNodeAttribute"); at.attribute_name = "foam"
    sep = n.nodes.new("ShaderNodeSeparateColor"); n.links.new(at.outputs["Color"], sep.inputs[0])
    # alpha = clamp((noise - 0.45) * 3) * vertical falloff (attr R) * strength
    s1 = n.nodes.new("ShaderNodeMath"); s1.operation = "SUBTRACT"; s1.inputs[1].default_value = 0.40
    n.links.new(nz.outputs["Fac"], s1.inputs[0])
    s2 = n.nodes.new("ShaderNodeMath"); s2.operation = "MULTIPLY"; s2.use_clamp = True; s2.inputs[1].default_value = 1.4
    n.links.new(s1.outputs[0], s2.inputs[0])
    s3 = n.nodes.new("ShaderNodeMath"); s3.operation = "MULTIPLY"
    n.links.new(s2.outputs[0], s3.inputs[0]); n.links.new(sep.outputs[0], s3.inputs[1])
    s4 = n.nodes.new("ShaderNodeMath"); s4.operation = "MULTIPLY"; s4.use_clamp = True; s4.inputs[1].default_value = strength
    n.links.new(s3.outputs[0], s4.inputs[0])
    mx = n.nodes.new("ShaderNodeMixShader")
    n.links.new(s4.outputs[0], mx.inputs[0]); n.links.new(tr.outputs[0], mx.inputs[1]); n.links.new(em.outputs[0], mx.inputs[2])
    n.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


MW = mat_wave(); wave.data.materials.append(MW)
MS1 = mat_spray(1.0); spray.data.materials.append(MS1)
MS2 = mat_spray(0.30); spray2.data.materials.append(MS2)

# per-column height variation (fixed) and shore taper
rng = np.random.default_rng(4)
def smooth1d(n, k, seed):
    r = np.random.default_rng(seed); v = r.standard_normal(n + 2 * k)
    v = np.convolve(v, np.hanning(2 * k + 1) / np.hanning(2 * k + 1).sum(), "same")[k:-k]
    return v / (v.std() + 1e-9)
HVAR = 1 + 0.15 * smooth1d(NX, 80, 1) + 0.05 * smooth1d(NX, 18, 2)
_az = math.radians(319 - 45); GLOW = np.array([math.sin(_az), math.cos(_az), 0.25]); GLOW /= np.linalg.norm(GLOW)


def tnoise(x, y, t, s, seed):
    return Wd.noise(x / 1000.0 + 0.0007 * t * (seed % 3 - 1), y / 1000.0 - 0.0011 * t, s, seed)


def build(yf, tau):
    X = np.repeat(xs[None, :], NS, 0)
    yfront = yf + CURVE * (X - XC) ** 2
    # shore taper: the wall dies out where the front line reaches land
    dw = Wd.water_sdf((X[0] / 1000.0).astype(np.float32), (yfront[0] / 1000.0).astype(np.float32))
    taper = np.clip((-dw + 0.06) / 0.25, 0, 1) ** 0.7
    Hx = HW * HVAR * taper
    S = np.repeat(PS[:, None], NX, 1); Zp = np.repeat(PZ[:, None], NX, 1); T = np.repeat(TV[:, None], NX, 1)
    Y = yfront + S
    # lip wobble moves along the front; turbulent heave behind
    wob = 0.9 * tnoise(X, Y * 0 + 0.5, tau, 0.05, 11)
    Y = Y + wob * (T < 0.4) * 2.0
    Z = Zp * Hx[None, :] * (1 + 0.10 * tnoise(X, Y, tau * 4, 0.04, 12) * (Zp > 0.5))
    Z += HW * 0.05 * tnoise(X, Y, tau * 6, 0.02, 13) * np.clip(T * 3, 0, 1) * taper
    Z = np.where(Zp <= 0.001, -0.5, Z)
    co = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    # foam attribute: R = coverage potential, G = brightness (lit towards the twilight glow)
    crest = np.exp(-((T - TV[np.argmax(PZ)]) / 0.06) ** 2)
    face = (T < TV[np.argmax(PZ)]) & (Zp > 0.05)
    streak = np.clip(0.5 + 0.8 * tnoise(X * 6, Y * 0.0 + Z * 2.0, tau * 3, 0.06, 14), 0, 1) * face * 0.55
    toe = np.exp(-((Zp - 0.04) / 0.06) ** 2) * 0.8
    back = np.clip((T - TV[np.argmax(PZ)]) * 6, 0, 1) * np.clip(0.45 + 0.35 * tnoise(X, Y, tau * 3, 0.03, 15), 0, 0.8)
    cov = np.clip(np.maximum.reduce([crest * (0.75 + 0.3 * tnoise(X, Y, tau * 5, 0.015, 16)), streak, toe, back]), 0, 1.0) * (taper[None, :] > 0.02)
    # approximate normals for lighting the foam: from the profile slope
    dz = np.gradient(Z, axis=0); dy = np.gradient(Y, axis=0) + 1e-3
    ny = -dz / np.sqrt(dz ** 2 + dy ** 2); nzn = dy / np.sqrt(dz ** 2 + dy ** 2)
    lit = np.clip(0.55 + 0.6 * (ny * GLOW[1] + nzn * GLOW[2]) + 0.3 * GLOW[0] * 0, 0.35, 1.2)
    col = np.stack([cov, lit, np.zeros_like(cov), np.ones_like(cov)], -1).reshape(-1, 4).astype(np.float32)
    me = wave.data
    me.vertices.foreach_set("co", co.ravel()); me.color_attributes["foam"].data.foreach_set("color", col.ravel())
    me.update()
    # spray sheets above the crest
    ic = int(np.argmax(PZ))
    for ob, back_m, hmul in ((spray, 8.0, 1.0), (spray2, 30.0, 1.4)):
        nx2 = NX // 2
        Xs = np.repeat(xs[::2][None, :], NSP, 0)
        Hs = Hx[::2]
        v = np.linspace(0, 1, NSP)[:, None]
        Ys = yf + CURVE * (Xs - XC) ** 2 + PS[ic] + back_m + 6 * v
        Zs = Hs[None, :] * (0.95 + hmul * 1.1 * v)
        coS = np.stack([Xs, Ys, Zs], -1).reshape(-1, 3).astype(np.float32)
        fall = (np.sin(np.pi * np.clip(v * 1.1, 0, 1)) ** 0.8 * (1 - v) ** 0.6) * (Hs[None, :] > 1.0)
        cS = np.stack([np.broadcast_to(fall, Xs.shape), np.ones_like(Xs), np.zeros_like(Xs), np.ones_like(Xs)], -1)
        ob.data.vertices.foreach_set("co", coS.ravel())
        ob.data.color_attributes["foam"].data.foreach_set("color", cS.reshape(-1, 4).astype(np.float32).ravel())
        ob.data.update()
    for m in (MW, MS1, MS2):
        for nd in m.node_tree.nodes:
            if nd.name in ("nz", "nz2"):
                nd.inputs["W"].default_value = tau * 0.35


# ------------------------------------------------------------------ camera (matches the compositor crop of the plate)
loc, tgt = (900, 1250, 16), (-250, 9800, 330)
cd = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36.0; cd.clip_start = 2.0; cd.clip_end = 100000.0
cam.location = Vector(loc)
cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

for fr in PRM["frames"]:
    f = fr["f"]
    if f < F0 or f >= F1:
        continue
    path = os.path.join(OUT, f"w_{f:05d}.png")
    if os.path.exists(path):
        continue
    z, cx, cy = fr["z"], fr["cx"], fr["cy"]
    cd.lens = 30.0 * z
    cd.shift_x = (cx - PRM["wp"] / 2) * z / PRM["wp"]
    cd.shift_y = (PRM["hp"] / 2 - cy) * z / PRM["wp"]
    build(fr["yf"], fr["tau"])
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("frame", f, flush=True)
