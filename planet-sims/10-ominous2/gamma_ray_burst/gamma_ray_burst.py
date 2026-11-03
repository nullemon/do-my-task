"""Ominous short #06: "Gamma-ray burst" (vertical 9:16, 24 fps, 58.5 s), built + rendered by this script.

Story: Earth at night from orbit -> a distant giant star collapses and fires two narrow jets ->
one jet swings toward us -> a silent flash floods the sky -> Earth's ozone shell tears -> cut to black.

Headless (Blender as a Python module, or blender -b -P):
  python gamma_ray_burst.py -- --render --out frames/ --res 540 --samples 8 --threads 2 --step 3
  python gamma_ray_burst.py -- --render --frames 1,400,880 --res 270      # test stills
  python gamma_ray_burst.py -- --audio gamma_ray_burst.wav                 # soundtrack only (numpy)
Frame N is rendered from the Earth scene or the star close-up scene depending on the shot.
"""

import math
import os
import sys

FPS = 24
DUR = 58.5
RES_X = 540
SAMPLES = 8
THREADS = 0
RENDER = False
OUT_DIR = None
STEP = 1
FRAMES_ONLY = None
AUDIO = None

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(name, cast=str, default=None):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


RENDER = "--render" in argv
RES_X = _arg("--res", int, RES_X)
SAMPLES = _arg("--samples", int, SAMPLES)
THREADS = _arg("--threads", int, THREADS)
STEP = _arg("--step", int, STEP)
AUDIO = _arg("--audio")
LAST = _arg("--last", int, None)            # render only up to this frame (job TEST mode)
if "--frames" in argv:
    FRAMES_ONLY = [int(x) for x in _arg("--frames").split(",")]
RES_Y = RES_X * 16 // 9
RES_Y += RES_Y % 2
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = _arg("--out", str, os.path.join(HERE, "renders"))


def _sec(s):
    """Seconds -> frame number (frame 1 = t 0)."""
    return int(round(s * FPS)) + 1


END = int(DUR * FPS)                 # 1404
S2 = _sec(7.0)                       # 169: cut to the star close-up
COLLAPSE = _sec(16.5)                # 397: core collapses (boom)
JETS = _sec(17.25)                   # jets erupt
SWING = _sec(25.0)                   # jet axis starts turning toward camera
S3 = _sec(30.5)                      # 733: whiteout -> back to Earth
FLASH = _sec(36.5)                   # 877: the burst hits Earth (big boom)
TEAR0, TEAR1 = _sec(38.0), _sec(48.0)
CUT = _sec(56.5)                     # 1357: final boom, cut to black

CAPTIONS = [  # (scene, text, t_in, t_out)
    ("earth", "What is the most powerful\nexplosion in the universe?", 0.25, 6.6),
    ("star", "A gamma-ray burst.", 7.6, 12.4),
    ("star", "A dying giant star collapses\ninto a black hole…", 12.9, 18.6),
    ("star", "…and fires two narrow jets\nout into space.", 19.0, 24.4),
    ("star", "In seconds, it can release as much\nenergy as the Sun will in\nits whole 10-billion-year life.", 24.8, 30.2),
    ("earth", "Now imagine one aimed at Earth,\nfrom a few thousand\nlight-years away.", 31.0, 36.2),
    ("earth", "Studies suggest it could\nstrip away about a third\nof our ozone layer.", 39.0, 45.0),
    ("earth", "Some scientists think one\nmay have helped trigger\na mass extinction\n~440 million years ago.", 45.5, 51.6),
    ("earth", "It would last only seconds.\nWe would never see it coming.", 52.2, 56.5),
]


# =============================================================================== soundtrack
def write_audio(out):
    import wave
    import numpy as np
    SR = 48000
    t = np.arange(int(DUR * SR)) / SR
    N = len(t)
    rng = np.random.default_rng(6)

    def bandpass(x, lo, hi):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / SR)
        w = np.clip((f - lo * 0.7) / (lo * 0.3), 0, 1) * np.clip((hi * 1.4 - f) / (hi * 0.4), 0, 1)
        return np.fft.irfft(X * w, len(x))

    def env(pts):
        xs, ys = zip(*pts)
        return np.interp(t, xs, ys)

    def boom(at, size=1.0, decay=2.4, tail=0.9):
        tb = np.clip(t - at, 0, None)
        on = (t >= at).astype(float)
        freq = 24 + 42 * np.exp(-tb / 0.35)
        b = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tb / decay)
        b += 0.6 * bandpass(rng.standard_normal(N), 30, 170) * np.exp(-tb / 0.28)
        b *= on * np.clip(tb / 0.012, 0, 1)
        ir_t = np.arange(int(3.0 * SR)) / SR
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / tail)
        ir[0] += 25
        wet = np.fft.irfft(np.fft.rfft(b, 2 * N) * np.fft.rfft(ir, 2 * N), 2 * N)[:N]
        wet = bandpass(wet, 22, 900)
        return size * wet / np.abs(wet).max()

    t_coll, t_flash, t_cut = (COLLAPSE - 1) / FPS, (FLASH - 1) / FPS, (CUT - 1) / FPS
    L = np.zeros(N)
    R = np.zeros(N)
    for f0, f1, a in ((41.2, 41.65, 1.0), (49.0, 49.35, 0.55), (55.0, 55.45, 0.7), (82.4, 82.8, 0.22),
                      (110, 110.5, 0.08)):
        p = rng.uniform(0, 6.28, 2)
        L += a * (np.sin(2 * np.pi * f0 * t + p[0]) + 0.8 * np.sin(2 * np.pi * f1 * t + p[1]))
        R += a * (np.sin(2 * np.pi * f1 * t + p[0]) + 0.8 * np.sin(2 * np.pi * f0 * t + p[1]))
    breathe = 0.78 + 0.22 * np.sin(2 * np.pi * t / 8.0 - 1.3)
    noise_lr = [bandpass(rng.standard_normal(N), 70, 520) for _ in range(2)]
    hiss = [bandpass(rng.standard_normal(N), 2500, 7000) for _ in range(2)]
    shimmer = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (622.3, 659.3, 932.3, 1244.5)) / 4
    shimmer *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.21 * t)
    # drone: builds through the star shots, drops to near silence right after the flash, creeps back
    drone = env([(0, 0), (3.5, 0.7), (t_coll - 0.1, 1.0), (t_coll + 3, 0.85), (t_flash - 0.05, 1.3),
                 (t_flash + 0.01, 0.0), (t_flash + 6.0, 0.0), (t_flash + 12, 0.75), (t_cut, 1.2),
                 (t_cut + 0.01, 0), (DUR, 0)])
    swell = env([(0, 0.05), (8, 0.1), (t_coll - 0.05, 0.6), (t_coll + 0.4, 0.12), (24, 0.15),
                 (30.3, 0.75), (31.5, 0.1), (t_flash - 0.05, 1.35), (t_flash, 0), (t_flash + 9, 0),
                 (t_flash + 14, 0.2), (t_cut - 0.05, 1.1), (t_cut, 0), (DUR, 0)])
    sh = env([(0, 0), (17, 0), (21, 0.7), (30, 0.9), (31, 0.3), (t_flash, 0.6), (t_flash + 0.5, 1.0),
              (t_flash + 6, 0.5), (t_cut, 0.8), (t_cut + 0.01, 0), (DUR, 0)])
    # rising pitch-less hiss into the whiteout and into the flash (no sound in space: the flash
    # itself is the boom and then the air goes dead)
    hs = env([(0, 0), (27, 0), (30.4, 0.5), (30.6, 0), (33, 0), (t_flash - 0.02, 0.8), (t_flash, 0), (DUR, 0)])
    rate = np.interp(t, [t_flash + 8, t_cut], [0.55, 1.4])          # heartbeat after the flash
    pulse = np.exp(-((np.cumsum(rate) / SR % 1.0) / 0.07)) * np.sin(2 * np.pi * 38 * t)
    pulse *= env([(0, 0), (t_flash + 8, 0), (t_flash + 13, 0.6), (t_cut, 1.0), (t_cut + 0.01, 0), (DUR, 0)])
    booms = boom(t_coll, 0.6, 2.0) + boom(t_flash, 1.4, 3.4, 1.1) + boom(t_cut, 1.3, 2.6, 0.7)
    L = (L * drone * breathe * 0.11 + noise_lr[0] * swell * 0.5 + shimmer * sh * 0.014
         + hiss[0] * hs * 0.25 + pulse * 0.22 + booms * 0.95)
    R = (R * drone * breathe * 0.11 + noise_lr[1] * swell * 0.5 + np.roll(shimmer, 700) * sh * 0.014
         + hiss[1] * hs * 0.25 + pulse * 0.22 + booms * 0.95)
    sm = lambda x: 0.5 - 0.5 * np.cos(np.pi * np.clip(x, 0, 1))  # noqa: E731
    master = sm(t / 1.2) * sm((DUR - t) / 0.3)
    y = np.stack([L, R], 1) * master[:, None]
    y = np.tanh(1.4 * y / np.abs(y).max()) / np.tanh(1.4) * 0.89
    # hard silence after the last boom's tail
    y[t > t_cut + 1.3] *= np.clip(1 - (t[t > t_cut + 1.3] - t_cut - 1.3) / 0.25, 0, 1)[:, None]
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())
    print("[grb] wrote", out, flush=True)


if AUDIO:
    write_audio(AUDIO)
    if not RENDER:
        sys.exit(0)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402


# =============================================================================== helpers
def new_scene(name):
    old = bpy.data.scenes.get(name)
    if old:
        bpy.data.scenes.remove(old)
    sc = bpy.data.scenes.new(name)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.device = "CPU"
    if THREADS:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = THREADS
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, END
    sc.render.image_settings.file_format = "PNG"
    sc.render.use_persistent_data = True
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.cycles.max_bounces = 3
    sc.cycles.transparent_max_bounces = 64   # many nested additive glow shells
    w = bpy.data.worlds.new(name + "_world")
    w.use_nodes = True
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


def uv_sphere(name, radius, segs=96, rings=48):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    return bpy.data.objects.new(name, me)


def plane(name, size):
    me = bpy.data.meshes.new(name)
    s = size / 2
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    return bpy.data.objects.new(name, me)


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def key_every_frame(target, path, index, fn, f0=1, f1=END):
    """Sample fn(frame) onto every frame (exact, no Bezier overshoot)."""
    for f in range(f0, f1 + 1):
        v = fn(f)
        if index >= 0:
            getattr(target, path)[index] = v
        else:
            setattr(target, path, v)
        target.keyframe_insert(path, frame=f, index=index)


def key_sock(sock, fn, f0=1, f1=END, every=1):
    for f in list(range(f0, f1 + 1, every)) + [f1]:
        sock.default_value = fn(f)
        sock.keyframe_insert("default_value", frame=f)


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k == "op":
            n.operation = v
        else:
            n.inputs[k].default_value = v
    return n


def math_(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def maprange(nt, val, a, b, c=0.0, d=1.0):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.inputs["From Min"].default_value, n.inputs["From Max"].default_value = a, b
    n.inputs["To Min"].default_value, n.inputs["To Max"].default_value = c, d
    nt.links.new(val, n.inputs["Value"])
    return n.outputs["Result"]


def vec_const(nt, v):
    cv = nt.nodes.new("ShaderNodeCombineXYZ")
    for i in range(3):
        cv.inputs[i].default_value = float(v[i])
    return cv.outputs[0]


def facing(nt):
    """|dot(N, I)|: 1 at the centre of a sphere, 0 at its limb."""
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    d = nt.nodes.new("ShaderNodeVectorMath")
    d.operation = "DOT_PRODUCT"
    nt.links.new(geo.outputs["Normal"], d.inputs[0])
    nt.links.new(geo.outputs["Incoming"], d.inputs[1])
    return math_(nt, "ABSOLUTE", d.outputs["Value"])


def glow_material(name, color):
    """Transparent + emission; returns (material, node tree, strength socket to drive)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs[0])
    return m, nt, em.inputs["Strength"]


def camera(sc, loc, rot_deg, lens):
    cd = bpy.data.cameras.new(sc.name + "_cam")
    cd.lens = lens
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.05
    cd.clip_end = 1e6
    cam = link(sc, bpy.data.objects.new(sc.name + "_cam", cd))
    cam.location = loc
    cam.rotation_euler = [math.radians(a) for a in rot_deg]
    sc.camera = cam
    return cam


def caption(sc, cam, text, f_in, f_out, y=-0.62, size=0.05):
    """Thin white text fixed to the camera, with a soft dark outline behind it so it stays readable
    over the jets / flash. Auto-fits to <= 85% of the frame width (shrinks, then re-wraps)."""
    d = 2.0
    half_h = d * cam.data.sensor_height / 2 / cam.data.lens
    half_w = half_h * sc.render.resolution_x / sc.render.resolution_y
    max_w = 0.85 * 2 * half_w
    want = size * 2 * half_h
    cu = bpy.data.curves.new(f"cap_{sc.name}_{f_in}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_line = 1.15
    ob = link(sc, bpy.data.objects.new(cu.name, cu))

    def text_width():
        cu.size = 1.0
        try:
            bpy.context.view_layer.update()
            sc.view_layers[0].update()
            xs = [v[0] for v in ob.bound_box]
            w = max(xs) - min(xs)
            if w > 0:
                return w
        except Exception:
            pass
        return 0.55 * max(len(s) for s in cu.body.split("\n"))

    w1 = text_width()
    min_size = 0.7 * want
    if w1 * min_size > max_w:  # re-wrap words into more lines
        per_char = w1 / max(len(s) for s in cu.body.split("\n"))
        limit = max(8, int(max_w / (per_char * min_size)))
        words = text.replace("\n", " ").split()
        lines, cur = [], ""
        for wd in words:
            if cur and len(cur) + 1 + len(wd) > limit:
                lines.append(cur)
                cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        cu.body = "\n".join(lines)
        w1 = text_width()
    cu.size = min(want, max_w / w1)
    ob.data.materials.append(mat_emit(cu.name + "_m", (1, 1, 1), 1.6))
    ob.parent = cam
    ob.location = (0, y * half_h, -d)
    ob.visible_shadow = False
    # dark outline: same text, fattened with the font offset, just behind
    sh_cu = cu.copy()
    sh_cu.offset = 0.008
    sh_cu.materials.clear()
    sh = link(sc, bpy.data.objects.new(cu.name + "_sh", sh_cu))
    sh.data.materials.append(mat_emit(cu.name + "_shm", (0, 0, 0), 0.0))
    sh.parent = cam
    sh.location = (0, y * half_h, -d - 0.004)
    sh.visible_shadow = False
    for o in (ob, sh):
        for f, hide in ((1, True), (f_in, False), (f_out, True)):
            o.hide_render = hide
            o.keyframe_insert("hide_render", frame=f)
    return ob


def card(sc, cam, name, color, dist, fac_fn, strength=8.0, f0=1, f1=END, every=1):
    """Full-frame card in front of the lens: fac 0 = invisible, 1 = solid colour."""
    ob = link(sc, plane(name, 8.0 * dist))
    m = bpy.data.materials.new(name + "_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    ob.data.materials.append(m)
    ob.parent = cam
    ob.location = (0, 0, -dist)
    ob.visible_shadow = False
    key_sock(mix.inputs["Fac"], fac_fn, f0, f1, every)
    return ob


def blackout(sc, cam, frame):
    ob = link(sc, plane("blackout", 6.0))
    ob.data.materials.append(mat_emit("blackout_m", (0, 0, 0), 0.0))
    ob.parent = cam
    ob.location = (0, 0, -0.5)
    ob.visible_shadow = False
    for f, hide in ((1, True), (frame, False)):
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)


def sky_world(sc, band_normal, flash_fn=None):
    """Point stars (voronoi cores, survive the denoiser) + a faint Milky Way band + optional flash."""
    nt = sc.world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    dirv = tc.outputs["Generated"]
    acc = None
    for scale, radius, gain in ((160, 0.12, 0.9), (60, 0.08, 2.2), (420, 0.16, 0.45)):
        vor = node(nt, "ShaderNodeTexVoronoi", Scale=scale)
        nt.links.new(dirv, vor.inputs["Vector"])
        core = maprange(nt, vor.outputs["Distance"], 0.0, radius, 1.0, 0.0)
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(vor.outputs["Color"], bw.inputs["Color"])
        s = math_(nt, "MULTIPLY", core, math_(nt, "POWER", bw.outputs[0], 6.0))
        s = math_(nt, "MULTIPLY", s, gain)
        acc = s if acc is None else math_(nt, "ADD", acc, s)
    # galaxy band: |dot(dir, n)| small
    d = nt.nodes.new("ShaderNodeVectorMath")
    d.operation = "DOT_PRODUCT"
    nt.links.new(dirv, d.inputs[0])
    nt.links.new(vec_const(nt, band_normal), d.inputs[1])
    band = maprange(nt, math_(nt, "ABSOLUTE", d.outputs["Value"]), 0.0, 0.28, 1.0, 0.0)
    band = math_(nt, "POWER", band, 1.8)
    cloud = node(nt, "ShaderNodeTexNoise", Scale=5.0, Detail=10.0, Roughness=0.62)
    nt.links.new(dirv, cloud.inputs["Vector"])
    dust = node(nt, "ShaderNodeTexNoise", Scale=11.0, Detail=8.0, Roughness=0.6)
    nt.links.new(dirv, dust.inputs["Vector"])
    neb = math_(nt, "MULTIPLY", band, maprange(nt, cloud.outputs["Fac"], 0.38, 0.7))
    neb = math_(nt, "MULTIPLY", neb, maprange(nt, dust.outputs["Fac"], 0.42, 0.6, 1.0, 0.15))
    stars = math_(nt, "MULTIPLY", acc, math_(nt, "ADD", math_(nt, "MULTIPLY", band, 1.6), 1.0))
    st_c = nt.nodes.new("ShaderNodeMixRGB")
    st_c.blend_type = "MULTIPLY"
    st_c.inputs["Fac"].default_value = 1.0
    st_c.inputs[2].default_value = (0.88, 0.93, 1.0, 1)
    nt.links.new(stars, st_c.inputs[1])
    nb_c = nt.nodes.new("ShaderNodeMixRGB")
    nb_c.blend_type = "MULTIPLY"
    nb_c.inputs["Fac"].default_value = 1.0
    nb_c.inputs[2].default_value = (0.05, 0.048, 0.06, 1)
    nt.links.new(neb, nb_c.inputs[1])
    add = nt.nodes.new("ShaderNodeMixRGB")
    add.blend_type = "ADD"
    add.inputs["Fac"].default_value = 1.0
    nt.links.new(st_c.outputs[0], add.inputs[1])
    nt.links.new(nb_c.outputs[0], add.inputs[2])
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(add.outputs[0], bg.inputs["Color"])
    if flash_fn is None:
        nt.links.new(bg.outputs[0], out.inputs[0])
        return
    fb = nt.nodes.new("ShaderNodeBackground")
    fb.inputs["Color"].default_value = (0.82, 0.8, 1.0, 1)
    key_sock(fb.inputs["Strength"], flash_fn, 1, END)
    sh = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bg.outputs[0], sh.inputs[0])
    nt.links.new(fb.outputs[0], sh.inputs[1])
    nt.links.new(sh.outputs[0], out.inputs[0])


# =============================================================================== Earth scene
def flash_curve(f):
    """0 before the burst, instant peak, fast decay with a long dim tail."""
    if f < FLASH:
        return 0.0
    s = (f - FLASH) / FPS
    return math.exp(-s / 0.9) * 0.96 + 0.04 * math.exp(-s / 3.0)


def build_earth():
    sc = new_scene("grb_earth")
    view_el = 29.0                                                # camera pitch above horizontal
    view = Vector((0, math.cos(math.radians(view_el)), math.sin(math.radians(view_el))))
    sky_world(sc, (0.8, -0.29, 0.52), flash_fn=lambda f: 3.0 * flash_curve(f))
    to_sun = Vector((0.35, 0.9, 0.25)).normalized()
    sun_li = bpy.data.lights.new("sun", "SUN")
    sun_li.energy = 4.0
    sun_li.color = (1.0, 0.96, 0.9)
    sun_li.angle = math.radians(0.5)
    sun = link(sc, bpy.data.objects.new("sun", sun_li))
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = (-to_sun).to_track_quat("-Z", "Y")

    def sun_dot(nt, v, lo, hi):
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        d = nt.nodes.new("ShaderNodeVectorMath")
        d.operation = "DOT_PRODUCT"
        nt.links.new(geo.outputs["Normal"], d.inputs[0])
        nt.links.new(vec_const(nt, v), d.inputs[1])
        return maprange(nt, d.outputs["Value"], lo, hi)

    # --- Earth (same recipe as the pale-dot short: noise continents, ice, glossy sea, city lights)
    earth = link(sc, uv_sphere("earth", 1.0, 192, 96))
    m = bpy.data.materials.new("earth_m")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    land = node(nt, "ShaderNodeTexNoise", Scale=1.15, Detail=14.0, Roughness=0.62, Distortion=0.35)
    nt.links.new(tc.outputs["Object"], land.inputs["Vector"])
    lc = nt.nodes.new("ShaderNodeValToRGB")
    e = lc.color_ramp.elements
    e[0].position, e[0].color = 0.35, (0.002, 0.008, 0.035, 1)
    e[1].position, e[1].color = 0.80, (0.42, 0.38, 0.32, 1)
    for pos, col in ((0.50, (0.004, 0.018, 0.06)), (0.535, (0.012, 0.06, 0.11)), (0.545, (0.09, 0.13, 0.05)),
                     (0.58, (0.07, 0.12, 0.04)), (0.62, (0.20, 0.18, 0.09)), (0.66, (0.52, 0.38, 0.21)),
                     (0.72, (0.36, 0.28, 0.18))):
        e.new(pos).color = (*col, 1)
    nt.links.new(land.outputs["Fac"], lc.inputs["Fac"])
    nt.links.new(lc.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(maprange(nt, land.outputs["Fac"], 0.535, 0.545, 0.32, 0.92), b.inputs["Roughness"])
    city = node(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=4.0)
    nt.links.new(tc.outputs["Object"], city.inputs["Vector"])
    cm = math_(nt, "MULTIPLY", maprange(nt, city.outputs["Fac"], 0.58, 0.72),
               maprange(nt, land.outputs["Fac"], 0.545, 0.6))
    cm = math_(nt, "MULTIPLY", cm, sun_dot(nt, to_sun, 0.0, -0.2))
    cm = math_(nt, "MULTIPLY", cm, 1.1)
    b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.28, 1)
    nt.links.new(cm, b.inputs["Emission Strength"])
    earth.data.materials.append(m)
    earth.rotation_euler = (math.radians(23.4), 0, 0)
    key_every_frame(earth, "rotation_euler", 2, lambda f: math.radians(-40 + 14 * f / END))

    # --- clouds
    clouds = link(sc, uv_sphere("clouds", 1.006, 192, 96))
    cmat = bpy.data.materials.new("clouds_m")
    cmat.use_nodes = True
    cnt = cmat.node_tree
    cnt.nodes.clear()
    cout = cnt.nodes.new("ShaderNodeOutputMaterial")
    ctc = cnt.nodes.new("ShaderNodeTexCoord")
    cmap = cnt.nodes.new("ShaderNodeMapping")
    cmap.inputs["Scale"].default_value = (1.0, 1.0, 1.6)
    cnt.links.new(ctc.outputs["Object"], cmap.inputs["Vector"])
    cn = node(cnt, "ShaderNodeTexNoise", Scale=2.6, Detail=12.0, Roughness=0.6, Distortion=0.9)
    cnt.links.new(cmap.outputs["Vector"], cn.inputs["Vector"])
    cdiff = node(cnt, "ShaderNodeBsdfDiffuse", Color=(0.92, 0.93, 0.95, 1))
    ctr = cnt.nodes.new("ShaderNodeBsdfTransparent")
    cmix = cnt.nodes.new("ShaderNodeMixShader")
    cnt.links.new(maprange(cnt, cn.outputs["Fac"], 0.52, 0.68), cmix.inputs["Fac"])
    cnt.links.new(ctr.outputs[0], cmix.inputs[1])
    cnt.links.new(cdiff.outputs[0], cmix.inputs[2])
    cnt.links.new(cmix.outputs[0], cout.inputs[0])
    clouds.data.materials.append(cmat)
    clouds.rotation_euler = (math.radians(23.4), 0, 0)
    key_every_frame(clouds, "rotation_euler", 2, lambda f: math.radians(-30 + 22 * f / END))

    # --- thin blue atmosphere: limb glow, stronger on the sunlit crescent
    atm = link(sc, uv_sphere("atmosphere", 1.02, 160, 80))
    am, ant, ast = glow_material("atm_m", (0.22, 0.48, 1.0))
    limb = math_(ant, "POWER", math_(ant, "SUBTRACT", 1.0, facing(ant)), 6.0)
    lit = math_(ant, "ADD", math_(ant, "MULTIPLY", sun_dot(ant, to_sun, -0.4, 0.3), 2.6), 0.35)
    ant.links.new(math_(ant, "MULTIPLY", math_(ant, "MULTIPLY", limb, lit), 2.2), ast)
    atm.data.materials.append(am)
    atm.visible_shadow = False

    # --- the burst: direction in the sky (a slightly brighter blue-white star), and its light
    star_dir = Vector((-0.06, math.cos(math.radians(view_el + 5.5)), math.sin(math.radians(view_el + 5.5))))
    star_dir.normalize()
    cam_loc = Vector((0, -2.6, 0))

    # --- ozone layer (dramatised: a thin glowing teal shell that tears open, burst side first)
    oz = link(sc, uv_sphere("ozone", 1.034, 160, 80))
    om, ont, ost = glow_material("ozone_m", (0.3, 1.0, 0.78))
    otc = ont.nodes.new("ShaderNodeTexCoord")
    on = node(ont, "ShaderNodeTexNoise", Scale=2.4, Detail=7.0, Roughness=0.6, Distortion=0.4)
    ont.links.new(otc.outputs["Object"], on.inputs["Vector"])
    bd = sun_dot(ont, star_dir, -1.0, 1.0)                        # 0..1, 1 = facing the burst
    v = math_(ont, "ADD", on.outputs["Fac"], math_(ont, "MULTIPLY", bd, 0.45))
    thr_n = ont.nodes.new("ShaderNodeValue")
    key_sock(thr_n.outputs[0], lambda f: 2.0 - 1.25 * smoothstep(TEAR0, TEAR1, f) ** 0.8, 1, END, 3)
    dd = math_(ont, "SUBTRACT", v, thr_n.outputs[0])
    keep = maprange(ont, dd, -0.025, 0.02, 1.0, 0.0)
    edge = maprange(ont, math_(ont, "ABSOLUTE", dd), 0.0, 0.018, 1.0, 0.0)
    edge = math_(ont, "MULTIPLY", edge, maprange(ont, thr_n.outputs[0], 1.6, 1.5))   # only once tearing
    olimb = math_(ont, "POWER", math_(ont, "SUBTRACT", 1.0, facing(ont)), 5.0)
    base = math_(ont, "ADD", math_(ont, "MULTIPLY", olimb, 1.0), 0.03)
    s = math_(ont, "ADD", math_(ont, "MULTIPLY", base, keep), math_(ont, "MULTIPLY", edge, 1.4))
    gain = ont.nodes.new("ShaderNodeValue")

    def oz_gain(f):
        g = 0.0 if f < S3 else 0.9 * smoothstep(S3 + 24, FLASH - 24, f)   # the shield appears before the burst
        g += 1.6 * flash_curve(f) if f >= FLASH else 0.0
        return g
    key_sock(gain.outputs[0], oz_gain, 1, END, 3)
    ont.links.new(math_(ont, "MULTIPLY", s, gain.outputs[0]), ost)
    oz.data.materials.append(om)
    oz.visible_shadow = False

    star = link(sc, uv_sphere("grb_star", 1.0, 16, 8))
    star.location = cam_loc + star_dir * 3000
    star.scale = (5.5, 5.5, 5.5)
    sm = mat_emit("grb_star_m", (0.7, 0.8, 1.0), 30.0)
    star.data.materials.append(sm)
    star.visible_shadow = False
    key_sock(sm.node_tree.nodes["Emission"].inputs["Strength"],
             lambda f: 30.0 * (1 - smoothstep(S2 - 30, S2, f)), 1, END, 3)
    bli = bpy.data.lights.new("burst", "SUN")
    bli.color = (0.85, 0.85, 1.0)
    bli.angle = math.radians(0.3)
    burst = link(sc, bpy.data.objects.new("burst", bli))
    burst.rotation_mode = "QUATERNION"
    burst.rotation_quaternion = (-star_dir).to_track_quat("-Z", "Y")
    for f in sorted(set(range(1, END + 1, 3)) | {FLASH - 1, FLASH}):
        bli.energy = 0.0 if f < FLASH else 45.0 * flash_curve(f)
        bli.keyframe_insert("energy", frame=f)

    # --- camera: slow drift up toward the star (shot 1), calmer re-frame (shot 3), shake on the flash
    cam = camera(sc, tuple(cam_loc), (90 + view_el, 0, 0), lens=35)

    def pitch(f):
        if f < S3:
            return 90 + view_el - 1.0 + 2.2 * smoothstep(1, S2, f)
        p = 90 + view_el + 0.6 - 1.4 * smoothstep(S3, END, f)
        return p

    def shake(f, k):
        if f < FLASH:
            return 0.0
        s = (f - FLASH) / FPS
        return 0.35 * math.exp(-s / 0.8) * math.sin(s * (17 + 5 * k) + k)
    key_every_frame(cam, "rotation_euler", 0, lambda f: math.radians(pitch(f) + shake(f, 0)))
    key_every_frame(cam, "rotation_euler", 2, lambda f: math.radians(0.8 - 1.6 * f / END + shake(f, 1)))
    key_every_frame(cam.data, "lens", -1, lambda f: 33 + 4 * smoothstep(1, S2, f) if f < S3
                    else 36 - 3 * smoothstep(S3, END, f))
    # whiteout carried over from the star close-up, fading back to Earth
    card(sc, cam, "white_in", (1.0, 0.98, 1.0), 0.9,
         lambda f: 0.0 if f < S3 else 1.0 - smoothstep(S3, S3 + 30, f), f0=S3 - 3, f1=S3 + 33)
    card(sc, cam, "flash", (0.95, 0.93, 1.0), 0.85,
         lambda f: 0.0 if f < FLASH else min(1.0, 1.15 * math.exp(-((f - FLASH) / FPS) / 0.7)),
         f0=FLASH - 3, f1=FLASH + 120)
    for scn, text, a, z in CAPTIONS:
        if scn == "earth":
            caption(sc, cam, text, _sec(a), _sec(z), y=0.62)
    blackout(sc, cam, CUT)
    return sc


# =============================================================================== star close-up
def build_star():
    sc = new_scene("grb_star")
    sky_world(sc, (0.7, 0.0, 0.71))

    # the giant star: blue-white granulated surface (voronoi cells x large-scale activity), limb darkened
    star = link(sc, uv_sphere("star", 0.8, 128, 64))
    m = bpy.data.materials.new("star_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    key_sock(mp.inputs["Location"], lambda f: (0.0, 0.0, f * 0.003), 1, END, 24)
    cells = nt.nodes.new("ShaderNodeTexVoronoi")
    cells.feature = "DISTANCE_TO_EDGE"
    cells.inputs["Scale"].default_value = 26.0
    cells.inputs["Randomness"].default_value = 0.9
    warp = node(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=4.0)
    nt.links.new(mp.outputs["Vector"], warp.inputs["Vector"])
    wv = nt.nodes.new("ShaderNodeVectorMath")
    wv.operation = "MULTIPLY_ADD"
    wv.inputs[1].default_value = (0.04, 0.04, 0.04)
    nt.links.new(warp.outputs["Color"], wv.inputs[0])
    nt.links.new(mp.outputs["Vector"], wv.inputs[2])
    nt.links.new(wv.outputs[0], cells.inputs["Vector"])
    gran = maprange(nt, cells.outputs["Distance"], 0.0, 0.12, 0.45, 1.0)
    act = node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=6.0, Roughness=0.6)
    nt.links.new(mp.outputs["Vector"], act.inputs["Vector"])
    actv = maprange(nt, act.outputs["Fac"], 0.35, 0.65, 0.7, 1.15)
    lum = math_(nt, "MULTIPLY", gran, actv)
    limb = math_(nt, "POWER", facing(nt), 0.55)
    lum = math_(nt, "MULTIPLY", lum, limb)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.1, (0.05, 0.08, 0.45, 1)
    el[1].position, el[1].color = 1.0, (1.0, 1.0, 1.0, 1)
    el.new(0.45).color = (0.25, 0.38, 1.0, 1)
    el.new(0.75).color = (0.62, 0.74, 1.0, 1)
    nt.links.new(lum, ramp.inputs["Fac"])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    sg = nt.nodes.new("ShaderNodeValue")

    def star_gain(f):
        if f < COLLAPSE - 70:
            return 0.9 + 0.08 * math.sin(f / 9.0)
        if f < COLLAPSE:
            return 0.9 + 22.0 * smoothstep(COLLAPSE - 70, COLLAPSE, f) ** 2
        return 25.0
    key_sock(sg.outputs[0], star_gain, 1, END, 1)
    nt.links.new(math_(nt, "MULTIPLY", math_(nt, "ADD", lum, 0.15), sg.outputs[0]), em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs[0])
    star.data.materials.append(m)
    star.visible_shadow = False

    def star_scale(f):
        if f < COLLAPSE - 70:
            return 1.0
        if f < COLLAPSE - 6:
            return 1.0 + 0.12 * smoothstep(COLLAPSE - 70, COLLAPSE - 6, f)
        return max(0.03, 1.12 * (1 - smoothstep(COLLAPSE - 6, COLLAPSE + 6, f)))
    key_every_frame(star, "scale", -1, lambda f: [star_scale(f)] * 3, COLLAPSE - 80, COLLAPSE + 10)

    def glow_sphere(name, R, color, r0, w, gain_fn, streaks=0.0, every=1):
        """Additive glow around the origin: emission ~ exp(-(b - r0)/w), b = ray's impact parameter."""
        ob = link(sc, uv_sphere(name, R, 64, 32))
        gm, gnt, gst = glow_material(name + "_m", color)
        fc = facing(gnt)
        b = math_(gnt, "MULTIPLY", math_(gnt, "SQRT", math_(gnt, "SUBTRACT", 1.0,
                                                               math_(gnt, "MULTIPLY", fc, fc), clamp=True)), R)
        x = math_(gnt, "MULTIPLY", math_(gnt, "MAXIMUM", math_(gnt, "SUBTRACT", b, r0), 0.0), -1.0 / w)
        g = math_(gnt, "EXPONENT", x)
        if streaks:
            gtc = gnt.nodes.new("ShaderNodeTexCoord")
            sn = node(gnt, "ShaderNodeTexNoise", Scale=4.0, Detail=5.0, Roughness=0.7)
            gnt.links.new(gtc.outputs["Object"], sn.inputs["Vector"])
            g = math_(gnt, "MULTIPLY", g, maprange(gnt, sn.outputs["Fac"], 0.3, 0.7, 1 - streaks, 1 + streaks))
        gv = gnt.nodes.new("ShaderNodeValue")
        key_sock(gv.outputs[0], gain_fn, 1, END, every)
        gnt.links.new(math_(gnt, "MULTIPLY", g, gv.outputs[0]), gst)
        ob.data.materials.append(gm)
        ob.visible_shadow = False
        return ob

    def corona_gain(f):
        if f < COLLAPSE - 70:
            return 0.3
        if f < COLLAPSE:
            return 0.3 + 1.5 * smoothstep(COLLAPSE - 70, COLLAPSE, f)
        return 2.0 * math.exp(-((f - COLLAPSE) / FPS) / 0.35)
    # corona: soft streaky blue glow hugging the limb, plus a faint wide glare
    glow_sphere("corona", 2.0, (0.45, 0.6, 1.0), 0.8, 0.13, corona_gain, streaks=0.5)
    glow_sphere("glare", 4.0, (0.4, 0.45, 1.0), 0.8, 0.55, lambda f: 0.12 * corona_gain(f))

    # the source after the collapse: bright compact white-violet glow that flickers
    def src_gain(f):
        if f < COLLAPSE:
            return 0.0
        s = (f - COLLAPSE) / FPS
        flick = 1.0 + 0.12 * math.sin(f * 1.7) * math.sin(f * 0.53 + 1.0)
        return (2.2 + 6.0 * math.exp(-s / 0.6) + 1.2 * smoothstep(SWING, S3, f)) * flick
    glow_sphere("source", 0.9, (0.9, 0.88, 1.0), 0.0, 0.07, src_gain)
    glow_sphere("source_glare", 3.0, (0.55, 0.45, 1.0), 0.0, 0.42,
                lambda f: 0.0 if f < COLLAPSE else 0.18 * src_gain(f) / 2.2)

    # jets: nested additive cones per side - wide violet glare, violet-blue sheath, hot white core.
    # Brightness peaks on the axis (|N.I|^p), fades along the length, with streaming turbulence + flicker.
    import bmesh
    base_me = bpy.data.meshes.new("jet")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.0, radius2=1.0, depth=1.0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.5))
    for fc_ in bm.faces:
        fc_.smooth = True
    bm.to_mesh(base_me)
    bm.free()
    pivot = link(sc, bpy.data.objects.new("jet_pivot", None))

    def jet_env(f):
        if f < JETS - 3:
            return 0.0
        return smoothstep(JETS - 3, JETS + 20, f) * (1.0 + 0.9 * smoothstep(SWING, S3, f))

    def jet_material(name, color, power, gain, fade, turb):
        jm, jnt, jst = glow_material(name, color)
        jtc = jnt.nodes.new("ShaderNodeTexCoord")
        jsep = jnt.nodes.new("ShaderNodeSeparateXYZ")
        jnt.links.new(jtc.outputs["Object"], jsep.inputs[0])
        along = math_(jnt, "POWER", math_(jnt, "SUBTRACT", 1.0, jsep.outputs["Z"], clamp=True), fade)
        jmp = jnt.nodes.new("ShaderNodeMapping")
        jmp.inputs["Scale"].default_value = (3.0, 3.0, 7.0)
        jnt.links.new(jtc.outputs["Object"], jmp.inputs["Vector"])
        key_sock(jmp.inputs["Location"], lambda f: (0.0, 0.0, -f * 0.03), 1, END, 12)
        tn = jnt.nodes.new("ShaderNodeTexNoise")
        tn.noise_dimensions = "4D"
        tn.inputs["Scale"].default_value = 1.6
        tn.inputs["Detail"].default_value = 6.0
        tn.inputs["Roughness"].default_value = 0.6
        key_sock(tn.inputs["W"], lambda f: f * 0.05, 1, END, 6)
        jnt.links.new(jmp.outputs["Vector"], tn.inputs["Vector"])
        tv = maprange(jnt, tn.outputs["Fac"], 0.3, 0.7, 1.0 - turb, 1.0 + turb)
        core = math_(jnt, "POWER", facing(jnt), power)
        js = math_(jnt, "MULTIPLY", math_(jnt, "MULTIPLY", along, core), tv)
        jg = jnt.nodes.new("ShaderNodeValue")
        key_sock(jg.outputs[0], lambda f: gain * jet_env(f), 1, END, 1)
        jnt.links.new(math_(jnt, "MULTIPLY", js, jg.outputs[0]), jst)
        return jm

    jet_len, jet_r = 13.0, 0.5
    layers = [("glare", (0.42, 0.36, 1.0), 1.2, 0.22, 2.4, 0.5, 2.6),      # name, colour, power, gain,
              ("sheath", (0.45, 0.55, 1.0), 2.5, 1.3, 1.6, 0.6, 1.0),      # fade, turbulence, radius x
              ("core", (0.92, 0.95, 1.0), 6.0, 3.2, 1.2, 0.35, 0.32)]
    for lname, col, pw, gn, fade, turb, rx_ in layers:
        me = base_me.copy()
        me.materials.append(jet_material("jet_" + lname, col, pw, gn, fade, turb))
        for i, rx in enumerate((0.0, 180.0)):
            jet = link(sc, bpy.data.objects.new(f"jet_{lname}{i}", me))
            jet.parent = pivot
            jet.rotation_euler = (math.radians(rx), 0, 0)
            jet.visible_shadow = False

            def jscale(f, rr=jet_r * rx_):
                g = smoothstep(JETS - 3, JETS + 48, f) ** 0.7
                return [rr * max(g, 0.02), rr * max(g, 0.02), max(jet_len * g, 0.001)]
            key_every_frame(jet, "scale", -1, jscale, JETS - 6, JETS + 51)
            for f, hide in ((1, True), (JETS - 3, False)):
                jet.hide_render = hide
                jet.keyframe_insert("hide_render", frame=f)
    # tilt: diagonal at first, then the upper jet swings round toward the camera
    key_every_frame(pivot, "rotation_euler", 1, lambda f: math.radians(-22 + 8 * smoothstep(SWING, S3, f)),
                    JETS - 6, S3 + 3)
    key_every_frame(pivot, "rotation_euler", 0, lambda f: math.radians(-74 * smoothstep(SWING, S3, f) ** 1.6),
                    JETS - 6, S3 + 3)
    pivot.location = (0, 0, 0)

    cam = camera(sc, (0, -10, -0.9), (90, 0, 0), lens=40)
    key_every_frame(cam, "location", 1, lambda f: -10.0 + 1.6 * smoothstep(S2, S3, f), S2 - 3, S3 + 3)
    key_every_frame(cam, "location", 0, lambda f: 0.25 - 0.5 * smoothstep(S2, S3, f), S2 - 3, S3 + 3)
    key_every_frame(cam, "rotation_euler", 2, lambda f: math.radians(-1.2 + 2.4 * smoothstep(S2, S3, f)), S2 - 3, S3 + 3)
    key_every_frame(cam, "rotation_euler", 0, lambda f: math.radians(87.0 + 0 * f), S2 - 3, S2 - 2)
    # collapse flare + final whiteout as we stare down the jet
    card(sc, cam, "flare", (0.85, 0.88, 1.0), 0.9,
         lambda f: 0.0 if f < COLLAPSE else 0.55 * (1 - smoothstep(COLLAPSE, COLLAPSE + 30, f)),
         f0=COLLAPSE - 3, f1=COLLAPSE + 40)
    card(sc, cam, "white_out", (1.0, 0.98, 1.0), 0.85, lambda f: smoothstep(S3 - 30, S3 - 2, f) ** 1.5,
         f0=S3 - 33, f1=S3 + 3)
    for scn, text, a, z in CAPTIONS:
        if scn == "star":
            caption(sc, cam, text, _sec(a), _sec(z), y=-0.62)
    return sc


# =============================================================================== render
def scene_for(f, earth, star):
    return star if S2 <= f < S3 else earth


def render(earth, star):
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = FRAMES_ONLY or list(range(1, (LAST or END) + 1, STEP))
    for f in frames:
        path = os.path.join(OUT_DIR, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue  # resumable
        sc = scene_for(f, earth, star)
        # headless: without the override frame_set() does not evaluate sc's animation
        with bpy.context.temp_override(scene=sc):
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[grb] {sc.name} {f}/{END}", flush=True)


earth_sc = build_earth()
star_sc = build_star()
print(f"[grb] built: {END} frames at {FPS} fps ({DUR} s)", flush=True)
if RENDER:
    render(earth_sc, star_sc)
