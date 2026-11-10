"""Photoreal teaspoon and gold ring (Blender 5.1 bpy module, Cycles CPU).  1 unit = 1 cm.
Usage: /home/user/bpyenv/bin/python spoon.py MODE [F0 F1 [STEP]]
  test [on|off] [frame]   one frame -> $SCR/chk/spoon_test_<on|off>.png
  on / off  F0 F1         spoon sequence with / without the glowing bead, RGBA 1800x1200 -> $SCR/spr/spoon_<mode>/f_###.png
  ring  F0 F1             gold wedding band, slow tumble, RGBA 1200x1200            -> $SCR/spr/ring/f_###.png
The spoon is a 14 cm stainless teaspoon (bowl 4.6 x 3.1 cm, about 5 mL); the bead is an emissive sphere.
Lighting: an HDR environment made by ../env.py (the Earth from high orbit) plus a sun lamp."""
import bpy, bmesh, sys, os, math, json
import numpy as np
from mathutils import Matrix, Vector, Euler
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/11-neutron-star-teaspoon"
args = sys.argv[1:]
MODE = args[0] if args else "test"
NF = 80
BEAD_R = float(os.environ.get("BEAD_R", "0.5"))


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def half_width(x):
    wb = 1.55 * np.sqrt(np.clip(1 - ((x - 2.28) / 2.32) ** 2, 0, 1)) ** 0.92 * (1 + 0.06 * np.tanh((x - 2.3)))  # ovoid bowl
    wh = 0.26 + 0.50 * ss(6.0, 12.6, x) ** 1.3
    wh = wh * np.sqrt(np.clip(1 - np.clip((x - 13.0) / 1.0, 0, 1) ** 2, 0, 1))
    w = np.where(x < 4.0, wb, np.maximum(wb, wh * ss(3.6, 4.6, x)))
    k = ss(3.9, 5.2, x); w = np.maximum(w, 0) * (1 - 0) ; w = np.where((x > 3.9) & (x < 5.2), np.maximum(w, (1 - k) * wb + k * wh), w)
    return np.maximum(w, 0.012)


def centre_z(x):
    return 1.15 * ss(3.9, 8.2, x) + 0.42 * np.sin(np.clip((x - 7.0) / 7.0, 0, 1) * np.pi) * 0.9 - 0.25 * ss(10.5, 14, x)


def build_spoon():
    n = 220; m = 28
    u = np.linspace(0, 1, n); xs = 14.0 * (0.5 - 0.5 * np.cos(np.pi * u)) * 0.35 + 14.0 * u * 0.65        # denser at both ends
    xs[0] = 0.0; xs[-1] = 14.0; xs = -0.037 + xs * (14.037 / 14.0)
    ts = np.linspace(-1, 1, m); ts = np.sign(ts) * np.abs(ts) ** 0.85                                    # denser near the rim
    verts = []
    for x in xs:
        w = float(half_width(np.array([x]))[0]); cz = float(centre_z(np.array([x]))[0])
        dep = 0.86 * math.sqrt(max(0.0, 1 - ((x - 2.3) / 2.34) ** 2)) ** 1.15 if x < 4.64 else 0.0
        hk = float(ss(4.6, 6.5, np.array([x]))[0])
        for t in ts:
            z = cz - dep * (1 - abs(t) ** 2.3) ** 0.85 + hk * 0.045 * (1 - t * t) - (1 - hk) * 0.0
            verts.append((x, t * w, z))
    faces = [(i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j) for i in range(n - 1) for j in range(m - 1)]
    me = bpy.data.meshes.new("spoon"); me.from_pydata(verts, [], faces); me.update()
    ob = bpy.data.objects.new("spoon", me); bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    so = ob.modifiers.new("solid", "SOLIDIFY"); so.thickness = 0.13; so.offset = -1.0; so.use_even_offset = True
    sb = ob.modifiers.new("sub", "SUBSURF"); sb.levels = 1; sb.render_levels = 2
    return ob


def steel():
    mat = bpy.data.materials.new("steel"); mat.use_nodes = True; nt = mat.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.78, 0.79, 0.81, 1); b.inputs["Metallic"].default_value = 1.0
    tc = N.new("ShaderNodeTexCoord")
    # brushed micro-scratches along the length + a few random fine scratches + soft smudges in the roughness
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.6, 60, 60); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 9.0; n1.inputs["Detail"].default_value = 6; L.new(mp.outputs["Vector"], n1.inputs["Vector"])
    mp2 = N.new("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (40, 1.5, 40); mp2.inputs["Rotation"].default_value = (0, 0, 0.6); L.new(tc.outputs["Object"], mp2.inputs["Vector"])
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 6.0; n2.inputs["Detail"].default_value = 5; L.new(mp2.outputs["Vector"], n2.inputs["Vector"])
    n3 = N.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = 0.9; n3.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n3.inputs["Vector"])
    r2 = N.new("ShaderNodeMapRange"); r2.inputs[1].default_value = 0.62; r2.inputs[2].default_value = 0.70; L.new(n2.outputs["Fac"], r2.inputs[0])
    mx = N.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.inputs[1].default_value = 0.10; mx.inputs[2].default_value = 0.075; L.new(n3.outputs["Fac"], mx.inputs[0])
    ad = N.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"; ad.inputs[1].default_value = 0.10; L.new(r2.outputs[0], ad.inputs[0]); L.new(mx.outputs[0], ad.inputs[2])
    L.new(ad.outputs[0], b.inputs["Roughness"])
    hm = N.new("ShaderNodeMath"); hm.operation = "MULTIPLY_ADD"; hm.inputs[1].default_value = 0.35; L.new(r2.outputs[0], hm.inputs[0]); L.new(n1.outputs["Fac"], hm.inputs[2])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.035; bp.inputs["Distance"].default_value = 0.02
    L.new(hm.outputs[0], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    try: b.inputs["Anisotropic"].default_value = 0.35
    except Exception: pass
    return mat


def gold():
    mat = bpy.data.materials.new("gold"); mat.use_nodes = True; nt = mat.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1.0, 0.72, 0.29, 1); b.inputs["Metallic"].default_value = 1.0
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (3, 3, 90); L.new(tc.outputs["Object"], mp.inputs["Vector"])
    n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 14.0; n1.inputs["Detail"].default_value = 7; L.new(mp.outputs["Vector"], n1.inputs["Vector"])
    n3 = N.new("ShaderNodeTexNoise"); n3.inputs["Scale"].default_value = 2.2; n3.inputs["Detail"].default_value = 5; L.new(tc.outputs["Object"], n3.inputs["Vector"])
    mx = N.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.inputs[1].default_value = 0.14; mx.inputs[2].default_value = 0.06; L.new(n3.outputs["Fac"], mx.inputs[0])
    L.new(mx.outputs[0], b.inputs["Roughness"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.05; bp.inputs["Distance"].default_value = 0.01
    L.new(n1.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs["Normal"], b.inputs["Normal"])
    return mat


def build_ring():
    """comfort-fit band: inner radius 0.87 cm, 0.5 cm wide, 0.17 cm thick (lathe of a rounded profile)"""
    k = 40; seg = 256; prof = []
    for i in range(k):
        a = 2 * math.pi * i / k; c, s = math.cos(a), math.sin(a)
        px = 0.25 * math.copysign(abs(c) ** 0.55, c)                       # across the band (z)
        pr = 0.085 * math.copysign(abs(s) ** (0.9 if s > 0 else 0.6), s)   # radial: domed outside, gently curved inside
        prof.append((0.955 + pr, px))
    verts = [(r * math.cos(2 * math.pi * j / seg), r * math.sin(2 * math.pi * j / seg), z) for j in range(seg) for (r, z) in prof]
    faces = [(j * k + i, j * k + (i + 1) % k, ((j + 1) % seg) * k + (i + 1) % k, ((j + 1) % seg) * k + i) for j in range(seg) for i in range(k)]
    me = bpy.data.meshes.new("ring"); me.from_pydata(verts, [], faces); me.update()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new("ring", me); bpy.context.scene.collection.objects.link(ob)
    sb = ob.modifiers.new("sub", "SUBSURF"); sb.levels = 1; sb.render_levels = 1
    ob.data.materials.append(gold())
    return ob


def setup(res, env, env_gain, samples):
    sc = bpy.context.scene
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02
    c.use_denoising = True
    try: c.denoiser = "OPENIMAGEDENOISE"
    except Exception as e: print("denoiser", e)
    c.max_bounces = 6; c.glossy_bounces = 5; c.diffuse_bounces = 1; c.transmission_bounces = 0; c.sample_clamp_indirect = 8.0
    sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", "2"))
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "16"
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; N = w.node_tree.nodes; L = w.node_tree.links
    e = N.new("ShaderNodeTexEnvironment"); e.image = bpy.data.images.load(env)
    bg = N["Background"]; bg.inputs["Strength"].default_value = env_gain; L.new(e.outputs["Color"], bg.inputs["Color"])
    return sc


def add_cam(sc, loc, target, lens):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.5; cd.clip_end = 2000
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def spoon_scene(bead_on):
    sc = setup((1800, 1200), SCR + "/tex/env_earth.hdr", 2.2, int(os.environ.get("SPP", "40")))
    sp = build_spoon(); sp.data.materials.append(steel())
    piv = bpy.data.objects.new("pivot", None); sc.collection.objects.link(piv); piv.location = (6.2, 0, 0.3)
    sp.parent = piv; sp.location = (-6.2, 0, -0.3)
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 7.0; sun.angle = math.radians(1.2); sun.color = (1.0, 0.97, 0.92)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    so.rotation_euler = Vector((-0.62, -0.50, 0.42)).to_track_quat("Z", "Y").to_euler()
    bead = None
    if bead_on:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=BEAD_R, location=(2.3 - 6.2, 0, -0.86 + BEAD_R + 0.10 - 0.3))
        bead = bpy.context.active_object; bead.parent = piv
        m = bpy.data.materials.new("bead"); m.use_nodes = True; N = m.node_tree.nodes; L = m.node_tree.links
        em = N.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.62, 0.80, 1.0, 1); em.inputs["Strength"].default_value = 900.0
        L.new(em.outputs[0], N["Material Output"].inputs["Surface"]); bead.data.materials.append(m)
    cam = add_cam(sc, (-13.0, -33.0, 17.0), (6.4, 0.0, 0.2), 86)
    return sc, piv, cam, bead


def pose(piv, f):
    u = f / (NF - 1)
    piv.rotation_euler = Euler((math.radians(-4 + 7 * u), math.radians(3 - 5 * u), math.radians(-22 + 9 * u)), "XYZ")


def render_seq(sc, piv, cam, bead, name, f0, f1, step=1):
    from bpy_extras.object_utils import world_to_camera_view
    os.makedirs(f"{SCR}/spr/{name}", exist_ok=True); meta = {}
    for f in range(f0, f1, step):
        fn = f"{SCR}/spr/{name}/f_{f:03d}.png"
        pose(piv, f); bpy.context.view_layer.update()
        if bead is not None:
            p = world_to_camera_view(sc, cam, bead.matrix_world.translation); meta[f] = [p.x * sc.render.resolution_x, (1 - p.y) * sc.render.resolution_y]
        if os.path.exists(fn): continue
        sc.render.filepath = fn; bpy.ops.render.render(write_still=True); print("rendered", fn, flush=True)
    if bead is not None and f0 == 0 and f1 >= NF:
        json.dump(meta, open(f"{SCR}/spr/{name}/bead.json", "w"))


if MODE == "test":
    on = (args[1] if len(args) > 1 else "on") == "on"; f = int(args[2]) if len(args) > 2 else 60
    sc, piv, cam, bead = spoon_scene(on); pose(piv, f)
    sc.render.filepath = f"{SCR}/chk/spoon_test_{'on' if on else 'off'}.png"; bpy.ops.render.render(write_still=True)
elif MODE in ("on", "off"):
    sc, piv, cam, bead = spoon_scene(MODE == "on")
    if MODE == "on":                                   # bead position for every frame (compositor glare)
        from bpy_extras.object_utils import world_to_camera_view
        meta = {}
        for f in range(NF):
            pose(piv, f); bpy.context.view_layer.update(); p = world_to_camera_view(sc, cam, bead.matrix_world.translation)
            meta[f] = [p.x * 1800, (1 - p.y) * 1200]
        os.makedirs(f"{SCR}/spr/spoon_on", exist_ok=True); json.dump(meta, open(f"{SCR}/spr/spoon_on/bead.json", "w"))
    render_seq(sc, piv, cam, None, "spoon_" + MODE, int(args[1]), int(args[2]), int(args[3]) if len(args) > 3 else 1)
elif MODE in ("ring", "ringtest"):
    sc = setup((1200, 1200), SCR + "/tex/env_studio.hdr", 1.0, int(os.environ.get("SPP", "96")))
    ring = build_ring()
    cam = add_cam(sc, (0, -11.0, 3.2), (0, 0, 0), 105)
    key = bpy.data.lights.new("k", "AREA"); key.energy = 60; key.size = 3; ko = bpy.data.objects.new("k", key); sc.collection.objects.link(ko)
    ko.location = (-5, -5, 6); ko.rotation_euler = (Vector((0, 0, 0)) - Vector(ko.location)).to_track_quat("-Z", "Y").to_euler()
    os.makedirs(f"{SCR}/spr/ring", exist_ok=True)
    fr = [int(args[1]) if len(args) > 1 else 40] if MODE == "ringtest" else range(int(args[1]), int(args[2]))
    for f in fr:
        u = f / (NF - 1)
        ring.rotation_euler = Euler((math.radians(62 - 10 * u), math.radians(14 + 8 * u), math.radians(-30 + 70 * u)), "XYZ")
        fn = f"{SCR}/chk/ring_test.png" if MODE == "ringtest" else f"{SCR}/spr/ring/f_{f:03d}.png"
        if os.path.exists(fn) and MODE == "ring": continue
        sc.render.filepath = fn; bpy.ops.render.render(write_still=True); print("rendered", fn, flush=True)
