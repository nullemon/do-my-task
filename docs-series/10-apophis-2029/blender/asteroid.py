"""Apophis model + render (Blender 5.1 bpy module, Cycles CPU).
Usage: /home/user/bpyenv/bin/python asteroid.py MODE [args]
  ast  F0 F1 [STEP]   rotation sequence, RGBA, orthographic 0.4 m/px, 1600x1000  -> $SCR/spr/ast/f_####.png
  test                one frame -> $SCR/chk/ast_test.png
  tower               Eiffel Tower (330 m) at the same scale and lighting          -> $SCR/spr/tower.png
Scene units: 1 unit = 100 m.  Shape: elongated two-lobed body ~450 x 300 x 265 m (volume-equivalent diameter ~340 m),
an artist's model guided by the radar description (Brozovic et al. 2018), not the real surface.
"""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Matrix, Vector, Euler
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/10-apophis-2029"
args = sys.argv[1:]
MODE = args[0] if args else "test"
RES = (1600, 1000); MPP = 0.4            # metres per pixel
rng = np.random.default_rng(42)


def fbm(p, f0, octaves, H, seed, ndir=10):
    r = np.random.default_rng(seed); out = np.zeros(len(p)); amp = 1.0; f = f0; tot = 0
    for o in range(octaves):
        k = r.standard_normal((ndir, 3)); k /= np.linalg.norm(k, axis=1, keepdims=True); k *= f * r.uniform(0.7, 1.4, (ndir, 1))
        ph = r.uniform(0, 6.283, ndir)
        out += amp * np.cos(p @ k.T + ph).sum(1) / math.sqrt(ndir); tot += amp
        amp *= 2 ** (-H); f *= 2
    return out / tot


def body_sdf(p):
    """smooth union of two ellipsoids (approximate sdf), units of 100 m"""
    def ell(p, c, r):
        q = (p - c) / r; k0 = np.linalg.norm(q, axis=1); k1 = np.linalg.norm(q / r, axis=1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    a = ell(p, np.array([-0.78, 0.0, 0.05]), np.array([1.40, 1.36, 1.20]))
    b = ell(p, np.array([1.18, 0.10, -0.10]), np.array([1.02, 0.98, 0.90]))
    k = 0.95
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def icosphere(sub):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    v = np.array([x.co[:] for x in bm.verts]); f = np.array([[x.index for x in fc.verts] for fc in bm.faces]); bm.free()
    return v, f


def build_asteroid():
    d, faces = icosphere(8)
    # radius along each ray by bisection on the sdf
    lo = np.zeros(len(d)); hi = np.full(len(d), 4.0)
    for _ in range(34):
        mid = (lo + hi) / 2; s = body_sdf(d * mid[:, None]); hi = np.where(s > 0, mid, hi); lo = np.where(s > 0, lo, mid)
    r = (lo + hi) / 2
    P = d * r[:, None]
    # large and medium relief
    r = r + 0.24 * fbm(P, 1.1, 3, 0.9, 1) + 0.10 * fbm(P, 4.5, 4, 0.8, 2)
    P = d * r[:, None]
    # smooth "ponds": mask where fine roughness is reduced
    smooth = np.clip(fbm(P, 1.6, 2, 1.0, 5) * 2.2 + 0.1, 0, 1)
    # craters
    cr = np.random.default_rng(9)
    for i in range(46):
        c = cr.standard_normal(3); c /= np.linalg.norm(c)
        j = int(np.argmax(d @ c)); pc = P[j]
        Rc = float(np.clip(cr.pareto(1.6) * 0.07 + 0.07, 0.07, 0.62))
        x = np.linalg.norm(P - pc, axis=1) / Rc
        prof = np.where(x < 1, 0.27 * Rc * (x ** 2 - 1), 0.0) + 0.065 * Rc * np.exp(-((x - 1.0) / 0.28) ** 2)
        r = r + prof * (x < 2.2)
        P = d * r[:, None]
    r = r + (0.022 * fbm(P, 22.0, 4, 0.7, 3)) * (1 - 0.75 * smooth) + 0.006 * fbm(P, 90.0, 3, 0.6, 4) * (1 - 0.6 * smooth)
    P = d * r[:, None]
    V = [P]; F = [faces]; SM = [np.ones(len(faces), bool)]; nv = len(P)
    # boulders
    b1v, b1f = icosphere(1); b2v, b2f = icosphere(2)
    br = np.random.default_rng(17)
    nb = 5200
    dirs = br.standard_normal((nb, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    idx = np.concatenate([np.argmax(dirs[i:i+400] @ d.T, axis=1) for i in range(0, nb, 400)])
    sizes = np.clip(0.008 * (1 + br.pareto(1.9, nb)) , 0.008, 0.15)
    keep = br.uniform(0, 1, nb) > smooth[idx] * 0.85            # fewer boulders in the smooth ponds
    for i in np.where(keep)[0]:
        s = sizes[i]; bv, bf = (b2v, b2f) if s > 0.022 else (b1v, b1f)
        v = bv * (1 + 0.13 * br.standard_normal((len(bv), 1))) * np.array([br.uniform(0.8, 1.3), br.uniform(0.7, 1.1), br.uniform(0.45, 0.8)]) * s
        a = br.uniform(0, 6.283, 3); R = np.array(Euler(a).to_matrix())
        v = v @ R.T + P[idx[i]] * (1 - 0.25 * s / np.linalg.norm(P[idx[i]]))
        V.append(v); F.append(bf + nv); SM.append(np.zeros(len(bf), bool)); nv += len(v)
    V = np.concatenate(V); F = np.concatenate(F); SM = np.concatenate(SM)
    me = bpy.data.meshes.new("apophis"); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
    me.polygons.foreach_set("use_smooth", SM.tolist())
    ob = bpy.data.objects.new("apophis", me); bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(rock_material())
    ext = V.max(0) - V.min(0); print("extent (m):", (ext * 100).round(0), "verts", len(V))
    return ob


def rock_material():
    m = bpy.data.materials.new("rock"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 0.92
    for nm in ("Specular IOR Level",):
        if nm in bsdf.inputs: bsdf.inputs[nm].default_value = 0.12
    tc = N.new("ShaderNodeTexCoord")
    n1 = N.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 1.6; n1.inputs["Detail"].default_value = 9; n1.inputs["Roughness"].default_value = 0.62
    n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 38; n2.inputs["Detail"].default_value = 8; n2.inputs["Roughness"].default_value = 0.7
    n3 = N.new("ShaderNodeTexVoronoi"); n3.inputs["Scale"].default_value = 60
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30; ramp.color_ramp.elements[0].color = (0.115, 0.098, 0.082, 1)
    ramp.color_ramp.elements[1].position = 0.72; ramp.color_ramp.elements[1].color = (0.30, 0.265, 0.225, 1)
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs["Factor"].default_value = 0.55
    r2 = N.new("ShaderNodeValToRGB"); r2.color_ramp.elements[0].color = (0.55, 0.55, 0.55, 1); r2.color_ramp.elements[1].color = (1.25, 1.2, 1.15, 1)
    for n in (n1, n2, n3): L.new(tc.outputs["Object"], n.inputs["Vector"])
    L.new(n1.outputs["Fac"], ramp.inputs["Fac"]); L.new(n2.outputs["Fac"], r2.inputs["Fac"])
    L.new(ramp.outputs["Color"], mix.inputs["A"]); L.new(r2.outputs["Color"], mix.inputs["B"])
    L.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    b1 = N.new("ShaderNodeBump"); b1.inputs["Strength"].default_value = 0.55; b1.inputs["Distance"].default_value = 0.02
    b2 = N.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = 0.35; b2.inputs["Distance"].default_value = 0.012
    L.new(n2.outputs["Fac"], b1.inputs["Height"]); L.new(n3.outputs["Distance"], b2.inputs["Height"])
    L.new(b1.outputs["Normal"], b2.inputs["Normal"]); L.new(b2.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def setup(res):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = 14; c.use_adaptive_sampling = False; c.use_denoising = False
    c.max_bounces = 1; c.diffuse_bounces = 1; c.glossy_bounces = 0; c.transmission_bounces = 0; c.caustics_reflective = False; c.caustics_refractive = False
    c.pixel_filter_type = "BLACKMAN_HARRIS"; c.filter_width = 1.5
    sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", "2"))
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "8"; sc.render.image_settings.compression = 30
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.004, 0.005, 0.008, 1)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = "ORTHO"; cam.data.ortho_scale = res[0] * MPP / 100.0
    cam.location = (0, -30, 0); cam.rotation_euler = (math.radians(90), 0, 0); cam.data.clip_end = 100
    def sun(name, d, strength, col, ang):
        l = bpy.data.lights.new(name, "SUN"); l.energy = strength; l.color = col; l.angle = math.radians(ang)
        o = bpy.data.objects.new(name, l); sc.collection.objects.link(o)
        o.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()      # light shines along -Z of the object
        return o
    # d = direction TO the light (camera looks along +Y; +X right, +Z up)
    sun("key", (-0.72, -0.34, 0.60), 8.5, (1.0, 0.965, 0.92), 0.6)
    sun("fill", (0.80, -0.25, -0.50), 0.16, (0.45, 0.62, 1.0), 20)          # earthshine-like cool fill
    sun("rim", (0.3, 0.9, 0.3), 0.5, (0.8, 0.88, 1.0), 4)
    return sc


def orient(ob, f):
    """slow tumble: 0.30 deg/frame about a tilted axis plus a slow wobble (non-principal-axis look)"""
    a = math.radians(0.30 * f)
    q1 = Matrix.Rotation(a, 4, Vector((0.25, 0.42, 0.87)).normalized())
    q2 = Matrix.Rotation(math.radians(14) * math.sin(a * 0.6 + 0.4), 4, "X")
    q0 = Matrix.Rotation(math.radians(-18), 4, "Y") @ Matrix.Rotation(math.radians(25), 4, "X")
    ob.matrix_world = q1 @ q2 @ q0


def build_tower():
    """Eiffel Tower, 330 m to the tip: lattice from the real silhouette (125 m base, platforms at 57 / 116 / 276 m)."""
    H = np.array([0, 20, 40, 57, 80, 100, 116, 150, 190, 230, 276, 300, 330.0]) / 100
    Wd = np.array([62.5, 49.0, 39.5, 33.0, 26.0, 21.0, 17.5, 12.5, 9.0, 6.8, 5.0, 2.6, 0.4]) / 100   # half-width
    bm = bmesh.new()
    def ring(h, w, leg=None):
        return [bm.verts.new((sx * w, sy * w, h)) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    def hw(h): return float(np.interp(h, H, Wd))
    # upper shaft (above 2nd platform): one tapering square lattice
    hs = np.concatenate([np.linspace(1.16, 2.76, 15), np.linspace(2.84, 3.30, 5)])
    prev = None
    for h in hs:
        r = ring(h, hw(h))
        if prev:
            for i in range(4): bm.faces.new((prev[i], prev[(i + 1) % 4], r[(i + 1) % 4], r[i]))
        prev = r
    # four legs below the 2nd platform
    hl = np.linspace(0, 1.16, 13)
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        prev = None
        for h in hl:
            w = hw(h); lw = float(np.interp(h, [0, 0.57, 1.16], [0.125, 0.085, 0.07]))    # leg half-width
            cx, cy = sx * (w - lw), sy * (w - lw)
            if h > 0.58: lw = min(lw, w / 2); cx, cy = sx * w / 2, sy * w / 2
            r = [bm.verts.new((cx + ax * lw, cy + ay * lw, h)) for ax, ay in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
            if prev:
                for i in range(4): bm.faces.new((prev[i], prev[(i + 1) % 4], r[(i + 1) % 4], r[i]))
            prev = r
    bmesh.ops.poke(bm, faces=bm.faces[:])                      # X bracing
    me = bpy.data.meshes.new("lattice"); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new("lattice", me); bpy.context.scene.collection.objects.link(ob)
    wf = ob.modifiers.new("wf", "WIREFRAME"); wf.thickness = 0.016; wf.use_replace = True
    mat = bpy.data.materials.new("iron"); mat.use_nodes = True; b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.42, 0.30, 0.20, 1); b.inputs["Roughness"].default_value = 0.6; b.inputs["Metallic"].default_value = 0.4
    ob.data.materials.append(mat)
    # platforms and arches (solid)
    bm = bmesh.new()
    for h, th, grow in ((0.57, 0.035, 1.06), (1.16, 0.03, 1.10), (2.76, 0.04, 1.5)):
        w = hw(h) * grow
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, 0, h)) @ Matrix.Diagonal((2 * w, 2 * w, th, 1)))
    # arches between the legs under the first platform (four faces)
    for k in range(4):
        rot = Matrix.Rotation(math.radians(90 * k), 4, "Z")
        n = 20; w0 = hw(0.0) - 0.25; pts = []
        for i in range(n + 1):
            u = -1 + 2 * i / n; x = u * w0; z = 0.50 - 0.36 * (abs(u) ** 2.2)
            pts.append((x, z))
        yv = -(hw(0.4))
        prev = None
        for (x, z) in pts:
            a = bm.verts.new(rot @ Vector((x, yv, z))); b_ = bm.verts.new(rot @ Vector((x, yv, z + 0.035)))
            c_ = bm.verts.new(rot @ Vector((x, yv + 0.03, z))); d_ = bm.verts.new(rot @ Vector((x, yv + 0.03, z + 0.035)))
            if prev:
                bm.faces.new((prev[0], a, b_, prev[1])); bm.faces.new((prev[2], prev[3], d_, c_)); bm.faces.new((prev[1], b_, d_, prev[3])); bm.faces.new((prev[0], prev[2], c_, a))
            prev = (a, b_, c_, d_)
    me2 = bpy.data.meshes.new("solid"); bm.to_mesh(me2); bm.free()
    ob2 = bpy.data.objects.new("solid", me2); bpy.context.scene.collection.objects.link(ob2); ob2.data.materials.append(mat)
    for o in (ob, ob2):
        o.matrix_world = Matrix.Translation((0, 0, -1.65)) @ Matrix.Rotation(math.radians(28), 4, "Z")


if MODE in ("ast", "test"):
    sc = setup(RES); ob = build_asteroid()
    out = os.path.join(SCR, "spr", "ast"); os.makedirs(out, exist_ok=True)
    if MODE == "test":
        fr = [int(a) for a in args[1:]] or [0]
        for f in fr:
            orient(ob, f); sc.render.filepath = os.path.join(SCR, "chk", f"ast_test_{f:04d}.png"); bpy.ops.render.render(write_still=True)
    else:
        f0, f1 = int(args[1]), int(args[2]); step = int(args[3]) if len(args) > 3 else 1
        for f in range(f0, f1, step):
            fn = os.path.join(out, f"f_{f:04d}.png")
            if os.path.exists(fn): continue
            orient(ob, f); sc.render.filepath = fn; bpy.ops.render.render(write_still=True)
elif MODE == "tower":
    sc = setup((500, 1000)); build_tower()
    sc.cycles.samples = 48
    sc.render.filepath = os.path.join(SCR, "spr", "tower.png"); bpy.ops.render.render(write_still=True)
