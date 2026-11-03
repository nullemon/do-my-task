"""The Bootes Void ("the Great Nothing"): an ominous vertical space short (9:16, 24 fps, 58 s).

We start inside a dense, procedural cosmic web (hundreds of thousands of galaxy points
arranged on the walls and filaments of a weighted Voronoi foam), then drift, very slowly,
into one enormous empty cell: the Bootes Void. Galaxies thin out, a lone faint spiral or
two drifts past, the void swallows the frame, and we cut to black.

Units: 1 Blender unit = 1 million light-years (Mly). The void is ~330 Mly across.

Headless (Blender Python module or blender -b):
  python bootes_void.py -- --render --out DIR [--res 540] [--samples 8] [--threads 2]
                           [--step 3] [--frames 1,600,1200] [--wav out.wav]
  --wav writes the soundtrack (numpy) and can be used without --render.
"""

import math
import os
import sys

import bpy
import numpy as np

# ----------------------------------------------------------------------------- CONFIG
FPS = 24
SECONDS = 58.0
RES_X = 540
SAMPLES = 8
THREADS = 0
STEP = 1
RENDER = False
OUT_DIR = None
WAV = None
FRAMES_ONLY = None

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(name, cast=str, default=None):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


RENDER = "--render" in argv
RES_X = _arg("--res", int, RES_X)
SAMPLES = _arg("--samples", int, SAMPLES)
THREADS = _arg("--threads", int, THREADS)
STEP = _arg("--step", int, STEP)
OUT_DIR = _arg("--out", str, None)
WAV = _arg("--wav", str, None)
if "--frames" in argv:
    FRAMES_ONLY = [int(x) for x in _arg("--frames").split(",")]
FRAME_END = _arg("--frame-end", int, None)  # cap (for test runs)

RES_Y = RES_X * 16 // 9
RES_Y += RES_Y % 2
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else bpy.path.abspath("//")
OUT_DIR = OUT_DIR or os.path.join(HERE, "renders", "bootes_void")
N_FRAMES = int(SECONDS * FPS)


def sec(s):
    return int(round(s * FPS)) + 1


# ----------------------------------------------------------------------------- story timing
# (text, start s, end s)
CAPTIONS = [
    ("What is the emptiest place\nwe have ever found?", 0.3, 4.8),
    ("Galaxies gather in a vast web\nof walls and filaments.", 6.0, 11.5),
    ("In 1981, astronomers found\na hole in it.", 13.0, 18.5),
    ("The Boötes Void.\nAbout 330 million light-years across.", 20.0, 26.5),
    ("Light would take 330 million years\nto cross it.", 28.0, 34.0),
    ("Thousands of galaxies should be here.\nWe have found about 60.", 35.5, 42.0),
    ("Had we been born at its centre, we might\nnot have known other galaxies existed\nuntil the 1960s.", 43.5, 50.5),
    ("And most of space\nlooks like this.", 52.0, 56.5),
]
BOOMS = [13.0, 20.0, 35.5, 56.5]   # key beats (s); the last one is the cut to black
CUT_S = 56.5


# ----------------------------------------------------------------------------- helpers
def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def ease_pts(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, v0), (x1, v1) in zip(pts, pts[1:]):
        if x <= x1:
            return v0 + (v1 - v0) * smoothstep(x0, x1, x)
    return pts[-1][1]


def new_scene(name):
    old = bpy.data.scenes.get(name)
    if old:
        bpy.data.scenes.remove(old)
    sc = bpy.data.scenes.new(name)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 0
    sc.cycles.transparent_max_bounces = 4
    if THREADS:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = THREADS
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, N_FRAMES
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    w = bpy.data.worlds.new(name + "_world")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0, 0, 0, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    sc.world = w
    return sc


def link(sc, ob):
    sc.collection.objects.link(ob)
    return ob


def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def plane(name, size):
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    return bpy.data.objects.new(name, me)


def caption(sc, cam, text, f_in, f_out, y=-0.62, size=0.034, strength=1.3):
    """Thin white text fixed to the camera, auto-fit to <= 85% of the frame width."""
    cu = bpy.data.curves.new(f"cap_{f_in}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    d = 2.0
    half_h = d * math.tan(math.atan(cam.data.sensor_height / 2 / cam.data.lens))
    half_w = half_h * sc.render.resolution_x / sc.render.resolution_y
    max_w = 0.85 * 2 * half_w
    want = size * 2 * half_h
    ob = link(sc, bpy.data.objects.new(cu.name, cu))
    cu.size = 1.0
    w1 = 0.0
    try:
        bpy.context.view_layer.update()
        sc.view_layers[0].update()
        xs = [v[0] for v in ob.bound_box]
        w1 = max(xs) - min(xs)
    except Exception:
        pass
    if w1 <= 0:
        w1 = 0.55 * max(len(s) for s in text.split("\n"))
    cu.size = min(want, max_w / w1)
    ob.data.materials.append(mat_emit(cu.name + "_m", (1, 1, 1), strength))
    ob.parent = cam
    ob.location = (0, y * half_h, -d)
    ob.visible_shadow = False
    for f, hide in ((1, True), (f_in, False), (f_out, True)):
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)
    return ob


def blackout(sc, cam, frame):
    card = link(sc, plane("blackout", 6.0))
    card.data.materials.append(mat_emit("blackout_m", (0, 0, 0), 0.0))
    card.parent = cam
    card.location = (0, 0, -0.8)
    for f, hide in ((1, True), (frame, False)):
        card.hide_render = hide
        card.keyframe_insert("hide_render", frame=f)


# ----------------------------------------------------------------------------- the cosmic web
VOID_R = 165.0       # radius of the carved void (Mly): ~330 Mly across
WEB_R = 620.0        # galaxies are generated out to this radius around the void centre


def make_web(seed=7, n_cand=4_000_000, n_seeds=520):
    """Galaxy positions on the walls/filaments of a weighted Voronoi foam.
    The cell at the origin is weighted up into a giant void (the Bootes Void)."""
    rng = np.random.default_rng(seed)
    # foam seeds (void centres); keep them out of the big void
    S = rng.uniform(-900, 900, (n_seeds * 3, 3))
    S = S[np.linalg.norm(S, axis=1) > VOID_R * 1.9][:n_seeds]
    S = np.vstack([[0, 0, 0], S])
    W = np.zeros(len(S))
    W[0] = 95.0  # additive weight: d_eff = d - W  -> the origin cell grows
    # candidates uniform in a ball
    u = rng.normal(size=(n_cand, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    r = WEB_R * rng.random(n_cand) ** (1 / 3)
    P = u * r[:, None]
    keep = np.zeros(n_cand, bool)
    kind = np.zeros(n_cand, np.float32)
    ch = 15_000
    for i in range(0, n_cand, ch):
        p = P[i:i + ch]
        d = np.sqrt(((p[:, None, :] - S[None, :, :]) ** 2).sum(-1)) - W[None, :]
        part = np.partition(d, 3, axis=1)[:, :4]
        part.sort(axis=1)
        wall = part[:, 1] - part[:, 0]
        fil = part[:, 2] - part[:, 0]
        node = part[:, 3] - part[:, 0]
        prob = (0.10 * np.exp(-(wall / 9.0) ** 2) + 0.45 * np.exp(-(fil / 9.0) ** 2)
                + 1.0 * np.exp(-(node / 14.0) ** 2))
        k = rng.random(len(p)) < prob
        keep[i:i + ch] = k
        kind[i:i + ch] = np.clip(prob, 0, 1)
    G = P[keep]
    K = kind[keep]
    # hard-carve the big void, leaving its wall dense
    rr = np.linalg.norm(G, axis=1)
    G, K = G[rr > VOID_R], K[rr > VOID_R]
    # ~60 lonely galaxies inside the void (a few along a thin tendril, as observed)
    lone = []
    while len(lone) < 40:
        q = rng.uniform(-VOID_R, VOID_R, 3)
        if np.linalg.norm(q) < VOID_R * 0.92:
            lone.append(q)
    a, b = np.array([-120, 40, -60.0]), np.array([110, -30, 70.0])
    for t in rng.random(20):
        lone.append(a + (b - a) * t + rng.normal(0, 6, 3))
    L = np.array(lone)
    G = np.vstack([G, L])
    K = np.concatenate([K, np.full(len(L), 0.2, np.float32)])
    return G, K, rng


def cam_path_fn():
    """Camera position (Mly) and forward direction as a function of time (s)."""
    # distance from the void centre along a gently curving approach
    dist = [(0.0, 400.0), (8.0, 352.0), (20.0, 200.0), (32.0, 105.0), (44.0, 45.0), (58.0, 8.0)]

    def pos(t):
        s = ease_pts(dist, t) if t > 0 else 400.0
        # linear-ish interior: blend the eased curve with a constant-speed curve to avoid stalls
        lin = 400.0 - (392.0 * t / 58.0)
        s = 0.55 * s + 0.45 * lin
        ang = math.radians(10.0) * (s / 400.0)
        return np.array([s * math.sin(ang) * 0.6, -s * math.cos(ang), 18.0 * (s / 400.0)])

    def fwd(t):
        a, b = pos(max(0, t - 0.5)), pos(t + 0.5)
        v = b - a
        return v / np.linalg.norm(v)
    return pos, fwd


def points_modifier(ob, cam, mat, size_floor=0.0007):
    """Geometry Nodes: mesh vertices -> point cloud. Radius = max(attr radius, k * distance
    to camera) so far galaxies never shrink below ~1 px (they dim in the shader instead)."""
    ng = bpy.data.node_groups.new(ob.name + "_gn", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    gin = N.new("NodeGroupInput")
    gout = N.new("NodeGroupOutput")
    m2p = N.new("GeometryNodeMeshToPoints")
    rad = N.new("GeometryNodeInputNamedAttribute")
    rad.data_type = "FLOAT"
    rad.inputs["Name"].default_value = "radius"
    oi = N.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = cam
    oi.transform_space = "RELATIVE"
    posn = N.new("GeometryNodeInputPosition")
    dist = N.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    mul = N.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = size_floor
    mx = N.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    setm = N.new("GeometryNodeSetMaterial")
    setm.inputs["Material"].default_value = mat
    L = ng.links.new
    L(gin.outputs[0], m2p.inputs["Mesh"])
    L(posn.outputs[0], dist.inputs[0])
    L(oi.outputs["Location"], dist.inputs[1])
    L(dist.outputs["Value"], mul.inputs[0])
    L(rad.outputs["Attribute"], mx.inputs[0])
    L(mul.outputs[0], mx.inputs[1])
    L(mx.outputs[0], m2p.inputs["Radius"])
    L(m2p.outputs[0], setm.inputs["Geometry"])
    L(setm.outputs[0], gout.inputs[0])
    md = ob.modifiers.new("points", "NODES")
    md.node_group = ng
    return md


def galaxy_material(name, d0=90.0, power=1.6):
    """Emission = col * gain / (1 + (dist/d0)^power). gain is animated (global fade)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_type = "GEOMETRY"
    at.attribute_name = "col"
    cd = nt.nodes.new("ShaderNodeCameraData")
    dv = nt.nodes.new("ShaderNodeMath")
    dv.operation = "DIVIDE"
    dv.inputs[1].default_value = d0
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = power
    ad = nt.nodes.new("ShaderNodeMath")
    ad.operation = "ADD"
    ad.inputs[1].default_value = 1.0
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "DIVIDE"
    inv.inputs[0].default_value = 1.0
    gain = nt.nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.name = "gain"
    gain.inputs[1].default_value = 1.0
    L = nt.links.new
    L(cd.outputs["View Distance"], dv.inputs[0])
    L(dv.outputs[0], pw.inputs[0])
    L(pw.outputs[0], ad.inputs[0])
    L(ad.outputs[0], inv.inputs[1])
    L(inv.outputs[0], gain.inputs[0])
    L(at.outputs["Color"], em.inputs["Color"])
    L(gain.outputs[0], em.inputs["Strength"])
    L(em.outputs[0], out.inputs[0])
    return m, gain, dv


def point_mesh(name, P, R, C):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P))
    me.vertices.foreach_set("co", P.astype(np.float32).ravel())
    ra = me.attributes.new("radius", "FLOAT", "POINT")
    ra.data.foreach_set("value", R.astype(np.float32))
    ca = me.attributes.new("col", "FLOAT_COLOR", "POINT")
    C4 = np.concatenate([C, np.ones((len(C), 1))], axis=1).astype(np.float32)
    ca.data.foreach_set("color", C4.ravel())
    me.update()
    return bpy.data.objects.new(name, me)


def galaxy_colors(rng, n, bright):
    """Mix of warm ellipticals and blue-white spirals."""
    warm = np.array([1.0, 0.78, 0.55])
    cool = np.array([0.70, 0.82, 1.0])
    t = rng.random(n)[:, None]
    c = warm * t + cool * (1 - t)
    return c * bright[:, None]


def spiral_galaxy(rng, n=30000, radius=0.12, arms=2, tilt=(0.0, 0.0)):
    """A small point-made spiral (local coords, disc in XY)."""
    nb = n // 5
    # bulge
    b = rng.normal(0, radius * 0.12, (nb, 3))
    b[:, 2] *= 0.6
    # arms (log spirals) + disc scatter
    na = n - nb
    rr = radius * (0.08 + 0.92 * rng.random(na) ** 0.8)
    arm = rng.integers(0, arms, na)
    th = np.log(rr / (radius * 0.08)) / 0.28 + arm * (2 * math.pi / arms) + rng.normal(0, 0.38, na)
    a = np.stack([rr * np.cos(th), rr * np.sin(th), rng.normal(0, radius * 0.02, na)], 1)
    P = np.vstack([b, a])
    cb = np.tile([1.0, 0.82, 0.6], (nb, 1)) * 2.2
    ca = np.tile([0.62, 0.78, 1.0], (na, 1)) * (0.6 + 0.8 * rng.random((na, 1)))
    C = np.vstack([cb, ca])
    R = np.full(len(P), radius * 0.008)
    return P, R, C


# ----------------------------------------------------------------------------- build
def build():
    from mathutils import Vector
    sc = new_scene("bootes_void")
    pos, fwd = cam_path_fn()

    # camera
    cd = bpy.data.cameras.new("cam")
    cd.lens = 24
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.01
    cd.clip_end = 5000
    cam = link(sc, bpy.data.objects.new("cam", cd))
    sc.camera = cam
    cam.rotation_mode = "QUATERNION"
    for f in range(1, N_FRAMES + 1):
        t = (f - 1) / FPS
        p = pos(t)
        v = Vector(fwd(t))
        # slow hypnotic sway: tiny yaw/pitch wander and a slow roll
        yaw = math.radians(3.0) * math.sin(t * 0.11)
        pit = math.radians(2.0) * math.sin(t * 0.07 + 1.0)
        v = Vector((v.x * math.cos(yaw) - v.y * math.sin(yaw), v.x * math.sin(yaw) + v.y * math.cos(yaw), v.z + pit)).normalized()
        q = v.to_track_quat("-Z", "Y")
        from mathutils import Quaternion
        q = q @ Quaternion((0, 0, 1), math.radians(4.0) * math.sin(t * 0.05) + t * math.radians(0.25))
        cam.location = p
        cam.rotation_quaternion = q
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)

    # web
    G, K, rng = make_web()
    # clear a narrow tunnel around the camera path so nothing pops right through the lens
    path = np.array([pos(t) for t in np.linspace(0, SECONDS, 600)])
    near = np.zeros(len(G), bool)
    for i in range(0, len(G), 50_000):
        g = G[i:i + 50_000]
        dmin = np.sqrt(((g[:, None, :] - path[None, ::3, :]) ** 2).sum(-1)).min(1)
        near[i:i + 50_000] = dmin < 2.5
    G, K = G[~near], K[~near]
    n = len(G)
    bright = np.exp(rng.normal(0, 0.55, n)) * (0.8 + 1.2 * K)
    R = 0.05 * np.exp(rng.normal(0, 0.35, n)) * (1 + 0.8 * K)
    C = galaxy_colors(rng, n, bright * 14.0)
    web = link(sc, point_mesh("web", G, R, C))
    mat, gain, d0 = galaxy_material("galaxy_m", power=2.0)
    points_modifier(web, cam, mat)
    print(f"[bootes] web galaxies: {n}", flush=True)

    # global fade: the void swallows the frame
    for t, v in [(0, 1.0), (22, 1.0), (40, 0.6), (50, 0.35), (CUT_S, 0.18)]:
        gain.inputs[1].default_value = v
        gain.inputs[1].keyframe_insert("default_value", frame=sec(t))
    # apparent-brightness falloff tightens: the walls recede into darkness
    for t, v in [(0, 90.0), (16, 85.0), (30, 55.0), (42, 34.0), (CUT_S, 22.0)]:
        d0.inputs[1].default_value = v
        d0.inputs[1].keyframe_insert("default_value", frame=sec(t))

    # two lone hero spirals that drift past (moved with the camera so they pass slowly)
    hmat, hgain, _ = galaxy_material("hero_m", d0=2.0, power=2.0)
    heroes = [  # (start s, end s, side offset, height, radius, tilt deg)
        (29.0, 41.0, 0.18, 0.55, 0.16, (62, 18)),
        (42.0, 53.5, -0.15, 0.5, 0.11, (40, -30)),
    ]
    for i, (t0, t1, side, up, rad, tilt) in enumerate(heroes):
        P, Rh, Ch = spiral_galaxy(rng, radius=rad)
        hob = link(sc, point_mesh(f"hero{i}", P, Rh, Ch * 0.55))
        points_modifier(hob, cam, hmat, size_floor=0.0006)
        hob.rotation_euler = (math.radians(tilt[0]), math.radians(tilt[1]), rng.random() * 6.28)
        for f in range(max(1, sec(t0) - 2), min(N_FRAMES, sec(t1) + 2) + 1):
            t = (f - 1) / FPS
            u = (t - t0) / (t1 - t0)
            p = Vector(pos(t))
            fw = Vector(fwd(t))
            rt = fw.cross(Vector((0, 0, 1))).normalized()
            upv = rt.cross(fw).normalized()
            ahead = 7.0 - 8.5 * u            # from far ahead to just behind
            lat = side * (0.3 + 0.7 * u)
            hob.location = p + fw * ahead + rt * lat + upv * up * (0.4 + 0.6 * u)
            hob.keyframe_insert("location", frame=f)
        for f, hide in ((1, True), (sec(t0) - 2, False), (sec(t1) + 2, True)):
            hob.hide_render = hide
            hob.keyframe_insert("hide_render", frame=f)
    for t, v in [(0, 0.0), (29, 0.0), (31.5, 0.38), (40, 0.38), (43, 0.3), (54, 0.18)]:
        hgain.inputs[1].default_value = v
        hgain.inputs[1].keyframe_insert("default_value", frame=sec(t))

    for text, a, b in CAPTIONS:
        caption(sc, cam, text, sec(a), sec(b))
    blackout(sc, cam, sec(CUT_S))
    return sc


# ----------------------------------------------------------------------------- soundtrack
def write_wav(path, sr=48000):
    import wave
    n = int(SECONDS * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(3)
    cut = CUT_S

    def env(pts):
        xs, ys = zip(*pts)
        return np.interp(t, xs, ys)

    # drone: two detuned pairs -> slow beating (0.35 Hz and 0.6 Hz)
    drone_amp = env([(0, 0), (3, 0.6), (20, 0.8), (40, 1.0), (cut - 0.05, 1.0), (cut, 0.0), (SECONDS, 0)])
    L = (np.sin(2 * np.pi * 43.0 * t) + np.sin(2 * np.pi * 43.35 * t)
         + 0.6 * np.sin(2 * np.pi * 55.0 * t + 1) + 0.6 * np.sin(2 * np.pi * 55.6 * t))
    Rr = (np.sin(2 * np.pi * 43.0 * t + 0.4) + np.sin(2 * np.pi * 43.4 * t)
          + 0.6 * np.sin(2 * np.pi * 55.0 * t) + 0.6 * np.sin(2 * np.pi * 55.55 * t + 2))
    L *= 0.12 * drone_amp
    Rr *= 0.12 * drone_amp
    # deepening sub layer as we sink into the void
    sub = 0.10 * np.sin(2 * np.pi * 41.0 * t) * env([(0, 0), (24, 0), (40, 0.8), (cut - 0.05, 1), (cut, 0), (SECONDS, 0)])
    L += sub
    Rr += sub

    def lowpass_noise(fc_lo, fc_hi, seed):
        x = np.random.default_rng(seed).normal(size=n)
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(n, 1 / sr)
        X *= ((f > fc_lo) & (f < fc_hi)) * 1.0
        y = np.fft.irfft(X, n)
        return y / np.abs(y).max()

    swell = env([(0, 0), (4, 0.25), (9, 0.6), (13, 0.15), (17, 0.5), (20, 0.15), (27, 0.55),
                 (35.5, 0.2), (42, 0.55), (46, 0.35), (52, 0.7), (cut, 0.9), (cut + 0.02, 0), (SECONDS, 0)])
    L += 0.10 * swell * lowpass_noise(60, 420, 11)
    Rr += 0.10 * swell * lowpass_noise(60, 420, 12)

    def boom(t0, amp):
        tt = t - t0
        m = tt >= 0
        y = np.zeros(n)
        x = tt[m]
        freq = 28 + 34 * np.exp(-x * 3.0)
        ph = 2 * np.pi * np.cumsum(freq) / sr
        y[m] = np.sin(ph) * np.exp(-x / 1.8) * (1 - np.exp(-x * 400))
        thump = lowpass_noise(20, 160, int(t0 * 10))
        y[m] += 0.5 * thump[m] * np.exp(-x / 0.25)
        return amp * y

    for b in BOOMS[:-1]:
        bb = boom(b, 0.55)
        L += bb
        Rr += bb
    last = boom(cut, 0.85)   # the final boom rings out into silence
    L += last
    Rr += last
    # fade to true silence after the last boom
    tail = env([(0, 1), (cut + 3.5, 1), (SECONDS - 0.3, 0), (SECONDS, 0)])
    L *= tail
    Rr *= tail
    st = np.stack([L, Rr], 1)
    st /= max(1e-9, np.abs(st).max()) / 0.89
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"[bootes] wrote {path}", flush=True)


# ----------------------------------------------------------------------------- render
def render(sc):
    os.makedirs(OUT_DIR, exist_ok=True)
    end = min(sc.frame_end, FRAME_END or sc.frame_end)
    frames = FRAMES_ONLY or range(1, end + 1, STEP)
    for f in frames:
        path = os.path.join(OUT_DIR, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue
        with bpy.context.temp_override(scene=sc):
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[bootes] frame {f}/{sc.frame_end}", flush=True)


def main():
    if WAV:
        write_wav(WAV)
    if RENDER or "--build" in argv:
        sc = build()
        print(f"[bootes] built: {sc.frame_end} frames at {FPS} fps", flush=True)
        if RENDER:
            render(sc)


main()
