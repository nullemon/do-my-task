"""Blender (bpy 5.1.2, Cycles CPU) stills for the sealed-ocean sequence of 08 'If the Sun vanished right now'.
  ocean.py ice  <spp>   -> SCR/plates/ice_{rgb,depth}.png    underside of the ice lid, lit only by our own lamp
  ocean.py vent <spp>   -> SCR/plates/vent_{rgb,depth}.png + vent.json (pixel positions of the chimney mouths)
Geometry is numpy height fields / displaced lathe meshes with multi-octave detail; water absorption, particles and the
vent plumes are added by the compositor from the depth pass.
"""
import bpy, math, sys, os, json
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
MODE, SPP = argv[0], int(argv[1])
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/08-if-the-sun-vanished"
OUT = os.path.join(SCR, "plates")
RW, RH = int(os.environ.get("RW", 2304)), int(os.environ.get("RH", 1296))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SPP
sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 2; sc.cycles.transmission_bounces = 0
sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"; sc.render.image_settings.color_depth = "16"
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
sc.render.threads_mode = "FIXED"; sc.render.threads = 3
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
def link(ob): sc.collection.objects.link(ob); return ob

def spectral(seed, beta, n):
    r = np.random.default_rng(seed)
    f = np.sqrt((np.fft.fftfreq(n)[:, None] * n) ** 2 + (np.fft.rfftfreq(n)[None, :] * n) ** 2); f[0, 0] = 1
    amp = f ** (-beta); amp[0, 0] = 0
    z = np.fft.irfft2(amp * np.exp(1j * r.uniform(0, 2 * np.pi, amp.shape)), s=(n, n))
    return (z - z.mean()) / z.std()

def grid_mesh(name, X, Y, Z, col=None):
    n0, n1 = X.shape
    me = bpy.data.meshes.new(name)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(n0 * n1).reshape(n0, n1)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me.vertices.add(n0 * n1); me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(faces.size); me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(len(faces)); me.polygons.foreach_set("loop_start", np.arange(0, faces.size, 4)); me.polygons.foreach_set("loop_total", np.full(len(faces), 4))
    me.update(); me.validate(); me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    if col is not None:
        rgba = np.concatenate([col, np.ones(col.shape[:2] + (1,))], -1).reshape(-1, 4).astype(np.float32)
        me.color_attributes.new("Col", "FLOAT_COLOR", "POINT").data.foreach_set("color", rgba.ravel())
    return link(bpy.data.objects.new(name, me))

def vcol_mat(name, rough=0.8, bump_scale=6.0, bump=0.6, bump_dist=0.05, spec=0.5, depth_pass=False):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree
    if depth_pass:
        for n in list(t.nodes): t.nodes.remove(n)
        out = t.nodes.new("ShaderNodeOutputMaterial"); cd = t.nodes.new("ShaderNodeCameraData")
        mul = t.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 1 / 60.0
        t.links.new(cd.outputs["View Distance"], mul.inputs[0]); em = t.nodes.new("ShaderNodeEmission")
        t.links.new(mul.outputs[0], em.inputs[0]); t.links.new(em.outputs[0], out.inputs[0]); return m
    b = t.nodes["Principled BSDF"]; vc = t.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    t.links.new(vc.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    tc = t.nodes.new("ShaderNodeTexCoord"); nz = t.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = bump_scale
    nz.inputs["Detail"].default_value = 12; nz.inputs["Roughness"].default_value = 0.65
    t.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = bump_dist
    t.links.new(nz.outputs["Fac"], bp.inputs["Height"]); t.links.new(bp.outputs[0], b.inputs["Normal"])
    return m

def spot(loc, target, energy, size, col=(0.8, 0.9, 1.0), blend=0.8, radius=0.1):
    ld = bpy.data.lights.new("s", "SPOT"); ld.energy = energy; ld.spot_size = math.radians(size); ld.spot_blend = blend; ld.color = col; ld.shadow_soft_size = radius
    o = link(bpy.data.objects.new("s", ld)); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o

def camera(loc, target, lens):
    cd = bpy.data.cameras.new("c"); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 500
    o = link(bpy.data.objects.new("c", cd)); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); sc.camera = o; return o

def render(name, mats_normal, mats_depth, objs):
    sc.render.filepath = os.path.join(OUT, name + "_rgb.png"); bpy.ops.render.render(write_still=True)
    for o in objs:
        o.data.materials.clear(); o.data.materials.append(mats_depth)
    for o in bpy.data.objects:
        if o.type == "LIGHT": o.hide_render = True
    sc.cycles.samples = 8; sc.cycles.use_denoising = False
    sc.render.filepath = os.path.join(OUT, name + "_depth.png"); bpy.ops.render.render(write_still=True)

dm = vcol_mat("depth", depth_pass=True)
if MODE == "ice":
    # underside of the ice: z = 0 is the mean ice base, keels and domes hang below / rise above it; camera is under water
    N = 1400
    xs = np.linspace(-45, 45, N); ys = np.linspace(-8, 82, N); X, Y = np.meshgrid(xs, ys)
    a = spectral(1, 1.9, N); b = spectral(2, 1.5, N); c = spectral(3, 1.1, N)
    keel = np.clip(np.abs(spectral(4, 1.7, N)) * -1 + 0.35, -3, 0.35)              # ridged: pressure-ridge keels hang down
    Z = 0.9 * a + 0.12 * b + 0.015 * c + 1.6 * keel
    # refrozen leads / cracks: thin bright lines (shallow grooves) from a second ridged field
    cr = np.abs(spectral(5, 1.3, N)); crack = np.clip(1 - cr / 0.045, 0, 1)
    Z += 0.10 * crack
    base = np.array([0.50, 0.66, 0.74]); deep = np.array([0.10, 0.30, 0.42]); white = np.array([0.86, 0.92, 0.95])
    k = np.clip((Z - Z.min()) / (Z.max() - Z.min()), 0, 1)[..., None]
    col = deep * (1 - k) + base * k
    col = col * (1 - crack[..., None] * 0.8) + white * crack[..., None] * 0.8
    fr = np.clip(b * 0.5 + c * 0.6, 0, 1)[..., None]; col = col * (1 - 0.35 * fr) + white * 0.35 * fr      # frost / bubble bloom patches
    ob = grid_mesh("ice", X, Y, Z, col)
    m = vcol_mat("icem", rough=0.32, bump_scale=14.0, bump=0.35, bump_dist=0.03)
    ob.data.materials.append(m)
    camera((0, -3.0, -5.2), (0, 24, 0.4), 22)
    spot((-2.4, -3.2, -6.4), (-1.0, 12, 0.5), 3200, 62, col=(0.75, 0.90, 1.0), blend=0.9, radius=0.3)
    spot((3.0, -2.5, -6.8), (4.0, 22, 0.5), 1300, 50, col=(0.6, 0.8, 1.0), blend=1.0, radius=0.3)
    render("ice", m, dm, [ob])
else:
    # sea floor with a cluster of sulphide chimneys
    N = 1100
    xs = np.linspace(-22, 22, N); ys = np.linspace(-6, 38, N); X, Y = np.meshgrid(xs, ys)
    a = spectral(11, 1.9, N); b = spectral(12, 1.4, N); c = spectral(13, 1.0, N)
    Z = 0.9 * a + 0.10 * b + 0.012 * c
    chim = [(-1.6, 9.5, 5.2, 0.85), (0.9, 10.6, 3.6, 0.7), (-3.4, 11.5, 2.6, 0.6), (2.6, 9.0, 1.9, 0.5), (4.9, 13.5, 4.3, 0.8),
            (-6.8, 14.0, 3.1, 0.7), (7.6, 17.0, 2.4, 0.6), (-0.4, 8.2, 1.2, 0.4), (-9.5, 19, 3.8, 0.8), (11, 22, 3.0, 0.8)]
    for (cx, cy, h, r) in chim:                                                       # sulphide mound under each chimney
        d2 = (X - cx) ** 2 + (Y - cy) ** 2; Z += 0.30 * h * np.exp(-d2 / (2 * (1.8 * r + 0.8) ** 2)) * (1.0 + 0.12 * a)
    rock = np.array([0.060, 0.055, 0.052]); rust = np.array([0.20, 0.09, 0.035]); mat_ = np.array([0.72, 0.70, 0.60]); yel = np.array([0.50, 0.40, 0.10])
    n1 = spectral(14, 1.9, N); n2 = spectral(15, 1.6, N)
    near = np.zeros_like(Z)
    for (cx, cy, h, r) in chim: near = np.maximum(near, np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * (3.0 * r + 1.2) ** 2)))
    col = rock * (0.7 + 0.5 * np.clip(n1, -1, 1.5)[..., None] * 0.5 + 0.3)
    ru = np.clip(n1 * 0.6 + near * 1.3 - 0.6, 0, 1)[..., None] * 0.8; col = col * (1 - ru) + rust * ru
    mm = (np.clip(n2 * 0.8 + n1 * 0.4 + near * 1.5 - 1.55, 0, 1) ** 0.8)[..., None] * 0.85; col = col * (1 - mm) + mat_ * mm       # microbial mats
    ye = np.clip(n2 * 0.9 - n1 * 0.5 + near - 1.55, 0, 1)[..., None] * 0.7; col = col * (1 - ye) + yel * ye
    floor = grid_mesh("floor", X, Y, Z, col)
    m = vcol_mat("rockm", rough=0.85, bump_scale=9.0, bump=0.9, bump_dist=0.06); floor.data.materials.append(m)
    objs = [floor]; mouths = []
    rr = np.random.default_rng(3)
    for ci, (cx, cy, h, r) in enumerate(chim):
        nu, nv = 220, 260
        th = np.linspace(0, 2 * np.pi, nu); v = np.linspace(0, 1, nv); TH, V = np.meshgrid(th, v)
        tn = spectral(40 + ci, 2.0, 512); tn2 = spectral(60 + ci, 1.5, 512)
        iu = (TH / (2 * np.pi) * 511).astype(int) % 512; iv = (V * 255).astype(int)
        knob = tn[iv, iu]; fine = tn2[iv, iu]
        prof = r * (0.98 - 0.52 * V ** 1.3 + 0.35 * np.exp(-V / 0.05)) * (1 + 0.16 * np.sin(V * rr.uniform(14, 24) + rr.uniform(0, 6)) + 0.08 * np.sin(V * rr.uniform(30, 50)))      # tapering, beaded spire
        rad = prof * (1 + 0.30 * knob + 0.05 * fine)
        lean = rr.uniform(-0.25, 0.25, 2)
        zi = np.interp(cy, ys, np.arange(N)); xi = np.interp(cx, xs, np.arange(N)); z0 = Z[int(zi), int(xi)] - 0.4
        Xc = cx + rad * np.cos(TH) + lean[0] * V ** 1.5 * h * 0.3 + 0.12 * r * np.sin(V * 7 + ci)
        Yc = cy + rad * np.sin(TH) + lean[1] * V ** 1.5 * h * 0.3
        Zc = z0 + V * (h + 0.4) + 0.10 * r * knob
        base_c = rock * 1.3 * (0.8 + 0.4 * np.clip(knob, -1, 1)[..., None])
        ru = np.clip(fine * 0.7 + V * 1.2 - 0.6, 0, 1)[..., None]; cc = base_c * (1 - ru) + rust * 1.1 * ru
        mm = (np.clip(knob * 0.9 + fine * 0.5 - 0.75 + 0.5 * V, 0, 1) ** 0.8)[..., None]; cc = cc * (1 - mm) + mat_ * mm
        tip = np.clip((V - 0.93) / 0.07, 0, 1)[..., None]; cc = cc * (1 - tip) + np.array([0.02, 0.02, 0.02]) * tip   # soot-black mouth
        o = grid_mesh(f"ch{ci}", Xc, Yc, Zc, cc); o.data.materials.append(m); objs.append(o)
        mouths.append((float(Xc[-1].mean()), float(Yc[-1].mean()), float(Zc[-1].mean()), float(prof[-1].mean())))
    cam = camera((0.6, -3.6, 1.7), (0.2, 11, 3.4), 24)
    spot((-4.5, -4.5, 5.5), (-1.0, 10, 2.6), 4200, 58, col=(0.80, 0.92, 1.0), blend=0.9, radius=0.4)
    spot((5.5, -3.0, 3.0), (4, 13, 2.5), 1400, 55, col=(0.65, 0.82, 1.0), blend=1.0, radius=0.4)
    # faint warm glow at the two tallest mouths (the hot fluid itself is not luminous to the eye; kept very subtle)
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    js = []
    for (mx, my, mz, mr) in mouths:
        co = world_to_camera_view(sc, cam, Vector((mx, my, mz)))
        js.append(dict(x=co.x * RW, y=(1 - co.y) * RH, r=mr / co.z * (24 / 36) * RW, dist=co.z))
    json.dump(dict(w=RW, h=RH, mouths=js), open(os.path.join(OUT, "vent.json"), "w"), indent=1)
    render("vent", m, dm, objs)
print("done", MODE)
