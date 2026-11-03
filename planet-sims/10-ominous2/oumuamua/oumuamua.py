"""'Oumuamua - the first known interstellar object (2017). Ominous vertical short (9:16, 24 fps, 57 s).

Self-contained Blender script (Cycles). Everything is procedural.

  blender -b -P oumuamua.py -- --render                      # all frames -> --out dir
  blender -b -P oumuamua.py -- --render --step 3             # every 3rd frame (1, 4, 7, ...)
  blender -b -P oumuamua.py -- --render --frames 1,300,700   # test stills
  blender -b -P oumuamua.py -- --audio out.wav               # soundtrack only (numpy), no scene
Options: --gpu  --res 540|1080  --samples N  --threads N  --out DIR  --range FIRST,LAST

Shots (seconds):
  A  0.0-17.5  wide: the Sun far off, the object swings round it on a hyperbolic arc (trail line)
  B 17.5-24.5  telescope view with crosshair: a faint speck, already leaving
  C 24.5-42.5  close: a dark reddish elongated body tumbling, lit by the distant Sun
  D 42.5-50.0  it recedes into the dark and fades
  cut to black at 50.0 s (final boom), last line on black, silence.
"""

import math
import os
import sys

FPS = 24
SECONDS = 57.0
RES_X = 540
SAMPLES = 8
THREADS = 0
RENDER = False
STEP = 1
OUT_DIR = None
AUDIO = None
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
AUDIO = _arg("--audio", str, None)
FRAME_RANGE = _arg("--range", str, None)   # e.g. 1,24 (inclusive) - limits a --render run
if "--frames" in argv:
    FRAMES_ONLY = [int(x) for x in argv[argv.index("--frames") + 1].split(",")]
RES_Y = (RES_X * 16 // 9) // 2 * 2
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
OUT_DIR = OUT_DIR or os.path.join(HERE, "renders")


def _sec(s):
    """Seconds -> frame number (frame 1 = t 0)."""
    return int(round(s * FPS)) + 1


def _t(f):
    return (f - 1) / FPS


def _smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


END = int(SECONDS * FPS)          # 1368
T_B, T_C, T_D, T_CUT = 17.5, 24.5, 42.5, 50.0
F_CUT = _sec(T_CUT)               # 1201 (on the every-3rd-frame grid)
BOOMS = [(0.35, 0.45), (T_B, 0.7), (T_C, 0.6), (37.0, 0.55), (T_CUT, 1.0)]   # (seconds, gain)


# ============================================================================ soundtrack (numpy only)
def write_audio(path, sr=48000):
    import wave
    import numpy as np
    n = int(SECONDS * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(3)
    cut = int(T_CUT * sr)

    def env(points):  # piecewise-linear envelope [(sec, value)]
        xs, ys = zip(*points)
        return np.interp(t, xs, ys)

    # drone: 44 Hz + 44.35 Hz (slow beating) + a fifth and an octave, very quiet upper partials
    drone = (np.sin(2 * np.pi * 44.0 * t) + 0.8 * np.sin(2 * np.pi * 44.35 * t + 1.0)
             + 0.35 * np.sin(2 * np.pi * 66.1 * t + 0.4) + 0.18 * np.sin(2 * np.pi * 88.2 * t + 2.0)
             + 0.05 * np.sin(2 * np.pi * 131.7 * t))
    drone *= 1.0 + 0.25 * np.sin(2 * np.pi * t / 9.0)
    drone *= env([(0, 0), (2.5, 0.5), (17, 0.6), (24, 0.75), (42, 0.9), (49.9, 1.0), (T_CUT, 0.0), (SECONDS, 0)])

    # filtered noise swells (one-pole low-pass, moving cutoff), rising into each boom
    white = rng.standard_normal(n)
    sw = env([(0, 0.05), (3, 0.15), (12, 0.25), (17.3, 0.7), (18.5, 0.2), (24.3, 0.6), (26, 0.15),
              (36.8, 0.6), (38.5, 0.2), (46, 0.35), (49.9, 1.0), (T_CUT, 0.0), (SECONDS, 0)])
    cutoff = 120 + 900 * sw
    a = np.exp(-2 * np.pi * cutoff / sr)
    lp = np.empty(n)
    y = 0.0
    for i in range(0, n, 256):  # block-wise with per-block coefficient (fast enough, smooth enough)
        ai = a[i]
        seg = white[i:i + 256]
        out = np.empty_like(seg)
        for k, x in enumerate(seg):
            y = ai * y + (1 - ai) * x
            out[k] = y
        lp[i:i + 256] = out
    noise = lp * sw * 3.0

    # booms: pitched-down sine thump + sub tail + a little noise crack
    boom = np.zeros(n)
    for s0, g in BOOMS:
        i0 = int(s0 * sr)
        L = int((6.5 if s0 == T_CUT else 4.0) * sr)
        tt = np.arange(min(L, n - i0)) / sr
        f = 30 + 45 * np.exp(-tt * 3.0)
        ph = 2 * np.pi * np.cumsum(f) / sr
        e = np.exp(-tt * (0.9 if s0 == T_CUT else 1.4)) * (1 - np.exp(-tt * 300))
        b = np.sin(ph) * e + 0.4 * np.sin(ph * 0.5) * e
        b += 0.25 * rng.standard_normal(len(tt)) * np.exp(-tt * 18)
        boom[i0:i0 + len(tt)] += g * b

    mix = 0.26 * drone + 0.2 * noise + 1.1 * boom
    mix[int((T_CUT + 6.6) * sr):] = 0.0
    tail = np.clip((t - (T_CUT + 5.0)) / 1.6, 0, 1)        # fade the boom tail fully into silence
    mix *= 1 - tail
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    mix /= max(1e-9, np.abs(mix).max()) / 0.89
    st = np.stack([mix, np.roll(mix, int(0.011 * sr)) * 0.97], axis=1)  # tiny Haas width
    pcm = (st * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"[oumuamua] wrote {path}", flush=True)


if AUDIO and not RENDER:
    write_audio(AUDIO)
    sys.exit(0)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402


# ============================================================================ orbit (hyperbola, Sun at origin)
E_ECC = 1.2          # 'Oumuamua's real eccentricity is ~1.20
Q_PERI = 14.0        # perihelion distance (scene units; not to scale with the bodies)
A_SEMI = Q_PERI / (E_ECC - 1)
B_SEMI = A_SEMI * math.sqrt(E_ECC ** 2 - 1)


def _hpos(H):
    return Vector((A_SEMI * (E_ECC - math.cosh(H)), B_SEMI * math.sinh(H), 0.0))


_HS = [-4.0 + 9.0 * i / 6000 for i in range(6001)]
_SS = [0.0]
for _i in range(1, len(_HS)):
    _SS.append(_SS[-1] + (_hpos(_HS[_i]) - _hpos(_HS[_i - 1])).length)
_S0 = _SS[min(range(len(_HS)), key=lambda i: abs(_HS[i]))]
_SS = [s - _S0 for s in _SS]


def path_pos(s):
    """Position at arc length s from perihelion (negative = incoming)."""
    import bisect
    k = min(max(bisect.bisect_left(_SS, s), 1), len(_SS) - 1)
    u = (s - _SS[k - 1]) / max(1e-9, _SS[k] - _SS[k - 1])
    return _hpos(_HS[k - 1] + u * (_HS[k] - _HS[k - 1]))


def path_tan(s):
    return (path_pos(s + 0.5) - path_pos(s - 0.5)).normalized()


V0 = 22.0  # cruise speed along the path, units/s (dramatised; it speeds up past the Sun)


def s_of_t(t):
    if t < T_B:   # shot A: perihelion at t = 11 s, a bit faster near the Sun
        return V0 * (t - 11) + V0 * 0.5 * 2.5 * math.sqrt(math.pi) / 2 * math.erf((t - 11) / 2.5)
    if t < T_C:   # shot B (telescope, slowed so the speck drifts gently)
        return 230 + 6.0 * (t - T_B)
    if t < T_D:   # shot C (camera rides along)
        return 300 + V0 * (t - T_C)
    return 700 + 9.0 * (t - T_D)   # shot D: recedes slowly into the dark


def shot(t):
    return "A" if t < T_B else "B" if t < T_C else "C" if t < T_D else "D"


# ============================================================================ scene helpers
def new_scene(name):
    old = bpy.data.scenes.get(name)
    if old:
        bpy.data.scenes.remove(old)
    sc = bpy.data.scenes.new(name)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    if "--gpu" in argv:   # uses whatever compute backend is enabled in Preferences (CUDA/OptiX/HIP/Metal)
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for be in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                try:
                    prefs.compute_device_type = be
                    prefs.get_devices()
                    if any(d.type == be for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = d.type == be
                        sc.cycles.device = "GPU"
                        break
                except TypeError:
                    continue
        except Exception as exc:
            print("[oumuamua] GPU setup failed, using CPU:", exc)
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 3
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
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
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


def plane(name, sx, sy=None):
    sy = sx if sy is None else sy
    me = bpy.data.meshes.new(name)
    a, b = sx / 2, sy / 2
    me.from_pydata([(-a, -b, 0), (a, -b, 0), (a, b, 0), (-a, b, 0)], [], [(0, 1, 2, 3)])
    return bpy.data.objects.new(name, me)


def uv_sphere(name, radius, segs=64, rings=32):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    return bpy.data.objects.new(name, me)


def camera_only(ob):
    for attr in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter"):
        setattr(ob, attr, False)


def hide_keys(ob, pairs):
    """pairs = [(frame, hidden)] constant switches."""
    for f, h in pairs:
        ob.hide_render = h
        ob.keyframe_insert("hide_render", frame=f)


def key_every(ob, path, fn, index=-1):
    for f in range(1, END + 1):
        v = fn(f)
        if index >= 0:
            getattr(ob, path)[index] = v
        else:
            setattr(ob, path, v)
        ob.keyframe_insert(path, frame=f, index=index)


def key_value(sock, pairs):
    for f, v in pairs:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)


def _font():
    for p in ("/usr/share/fonts/opentype/inter/Inter-Light.otf",
              "/usr/share/fonts/truetype/inter/Inter-Light.ttf"):
        if os.path.exists(p):
            try:
                return bpy.data.fonts.load(p, check_existing=True)
            except RuntimeError:
                pass
    return None  # Blender's built-in font


LENS = 35.0
CAP_D = 2.0


def caption(sc, cam, text, f_in, f_out, y=-0.6, size=0.05, color=(1, 1, 1), strength=1.6, name=None):
    """Text fixed to the camera. y is -1..1 of the frame height. Visible f_in..f_out.
    Auto-fits: shrunk (and re-wrapped if needed) to at most 85% of the frame width."""
    cu = bpy.data.curves.new(name or f"cap_{f_in}", "FONT")
    fnt = _font()
    if fnt:
        cu.font = fnt
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_line = 1.12
    d = CAP_D
    half_h = d * (cam.data.sensor_height / 2) / cam.data.lens
    half_w = half_h * sc.render.resolution_x / sc.render.resolution_y
    max_w = 0.85 * 2 * half_w
    want = size * 2 * half_h
    ob = link(sc, bpy.data.objects.new(cu.name, cu))

    def text_width():
        cu.size = 1.0
        try:
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
    if w1 * min_size > max_w:
        per_char = w1 / max(len(s) for s in cu.body.split("\n"))
        limit = max(8, int(max_w / (per_char * min_size)))
        lines = []
        for para in text.split("\n"):
            k = max(1, math.ceil(len(para) / limit))
            target = len(para) / k
            cur = ""
            for wd in para.split():
                if cur and len(cur) + 1 + len(wd) / 2 > target:
                    lines.append(cur)
                    cur = wd
                else:
                    cur = (cur + " " + wd).strip()
            lines.append(cur)
        cu.body = "\n".join(lines)
        w1 = text_width()
    cu.size = min(want, max_w / w1)
    ob.data.materials.append(mat_emit(cu.name + "_m", color, strength))
    ob.parent = cam
    ob.location = (0, y * half_h, -d)
    camera_only(ob)
    hide_keys(ob, [(1, True), (f_in, False), (f_out, True)])
    return ob


# ============================================================================ world: stars
def star_world(sc):
    nt = sc.world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    acc = None
    for scale, radius, gain, power in [(110, 0.15, 110.0, 24.0), (230, 0.18, 45.0, 26.0), (60, 0.11, 160.0, 34.0)]:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        core = nt.nodes.new("ShaderNodeMapRange")
        core.inputs["From Max"].default_value = radius
        core.inputs["To Min"].default_value = 1.0
        core.inputs["To Max"].default_value = 0.0
        nt.links.new(vor.outputs["Distance"], core.inputs["Value"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(vor.outputs["Color"], bw.inputs["Color"])
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = power
        nt.links.new(bw.outputs[0], pw.inputs[0])
        m1 = nt.nodes.new("ShaderNodeMath")
        m1.operation = "MULTIPLY"
        nt.links.new(core.outputs["Result"], m1.inputs[0])
        nt.links.new(pw.outputs[0], m1.inputs[1])
        m2 = nt.nodes.new("ShaderNodeMath")
        m2.operation = "MULTIPLY"
        m2.inputs[1].default_value = gain
        nt.links.new(m1.outputs[0], m2.inputs[0])
        if acc is None:
            acc = m2.outputs[0]
        else:
            add = nt.nodes.new("ShaderNodeMath")
            add.operation = "ADD"
            nt.links.new(acc, add.inputs[0])
            nt.links.new(m2.outputs[0], add.inputs[1])
            acc = add.outputs[0]
    # faint dusty band of the Milky Way (very low), so the black isn't flat
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    nr = nt.nodes.new("ShaderNodeMapRange")
    nr.inputs["From Min"].default_value, nr.inputs["From Max"].default_value = 0.5, 0.75
    nr.inputs["To Max"].default_value = 0.0035
    nt.links.new(nz.outputs["Fac"], nr.inputs["Value"])
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    nt.links.new(acc, add.inputs[0])
    nt.links.new(nr.outputs["Result"], add.inputs[1])
    tint = nt.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs["Fac"].default_value = 1.0
    tint.inputs[2].default_value = (0.82, 0.9, 1.0, 1)
    nt.links.new(add.outputs[0], tint.inputs[1])
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(tint.outputs[0], bg.inputs["Color"])
    # the world must not light the object (it should be lit by the Sun only)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


# ============================================================================ build
def build():
    sc = new_scene("oumuamua")
    star_world(sc)

    # --- the camera, keyed per frame from the shot plan
    cd = bpy.data.cameras.new("cam")
    cd.lens = LENS
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.05
    cd.clip_end = 1e5
    cam = link(sc, bpy.data.objects.new("cam", cd))
    cam.rotation_mode = "QUATERNION"
    sc.camera = cam

    sB0 = s_of_t(T_B)
    sD0 = s_of_t(T_D)
    pB = path_pos(s_of_t(21.0))
    camB = pB + (pB.normalized() * -0.35 + Vector((0.55, -0.6, 0.45))).normalized() * 300.0
    pD = path_pos(sD0)
    tD = path_tan(sD0)
    nD = Vector((0, 0, 1)).cross(tD).normalized()
    camD = pD - tD * 7.0 + nD * 1.8 + Vector((0, 0, 0.9))

    def cam_state(f):
        t = _t(f)
        sh = shot(t)
        p = path_pos(s_of_t(t))
        if sh == "A":
            u = _smoothstep(0, T_B, t)
            loc = Vector((-40 + 30 * u, -330 + 50 * u, 380 - 50 * u))
            tgt = Vector((-55 + 10 * u, 5, 0))
            up = Vector((0, 1, 0.2))
        elif sh == "B":
            lag = 1.0 - _smoothstep(T_B, T_B + 3.2, t)   # telescope slews onto the speck
            tgt = p + Vector((0, 0, 1)).cross(path_tan(s_of_t(t))) * (-18.0 * lag) + path_tan(s_of_t(t)) * (-14 * lag)
            loc = camB
            up = Vector((0, 0, 1))
        elif sh == "C":
            u = _smoothstep(T_C, T_D, t)
            to_sun = (-p).normalized()
            ang = math.radians(118 - 36 * u)                # 3/4 lit, slowly swinging round towards its night side
            dirv = Vector((to_sun.x * math.cos(ang) - to_sun.y * math.sin(ang),
                           to_sun.x * math.sin(ang) + to_sun.y * math.cos(ang), 0)).normalized()
            R = 2.7 - 0.4 * u
            loc = p - dirv * R + Vector((0, 0, 0.7 - 0.4 * u))
            tgt = p + Vector((0, 0, 0.05))
            up = Vector((0, 0, 1))
        else:
            u = _smoothstep(T_D, T_CUT, t)
            loc = camD + tD * (1.5 * u)
            tgt = camD + tD * 100 + nD * -9.0 * (1 - 0.6 * u) + Vector((0, 0, -4.5))
            up = Vector((0, 0, 1))
        fwd = (tgt - loc).normalized()
        right = fwd.cross(up).normalized()
        up2 = right.cross(fwd)
        from mathutils import Matrix
        m = Matrix((right, up2, -fwd)).transposed()
        return loc, m.to_quaternion()

    states = {f: cam_state(f) for f in range(1, END + 1)}
    for f in range(1, END + 1):
        loc, q = states[f]
        cam.location = loc
        cam.rotation_quaternion = q
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)

    # --- the Sun: emissive ball + camera-facing glow card
    sun = link(sc, uv_sphere("sun", 3.2, 48, 24))
    sun.data.materials.append(mat_emit("sun_m", (1.0, 0.86, 0.65), 40.0))
    camera_only(sun)
    glow = link(sc, plane("sun_glow", 400))
    camera_only(glow)
    con = glow.constraints.new("TRACK_TO")
    con.target = cam
    con.track_axis = "TRACK_Z"
    con.up_axis = "UP_Y"
    gm = bpy.data.materials.new("sun_glow_m")
    gm.use_nodes = True
    g = gm.node_tree
    g.nodes.clear()
    gout = g.nodes.new("ShaderNodeOutputMaterial")
    gtc = g.nodes.new("ShaderNodeTexCoord")
    vl = g.nodes.new("ShaderNodeVectorMath")
    vl.operation = "LENGTH"
    g.links.new(gtc.outputs["Object"], vl.inputs[0])
    sq = g.nodes.new("ShaderNodeMath")
    sq.operation = "MULTIPLY"
    g.links.new(vl.outputs["Value"], sq.inputs[0])
    g.links.new(vl.outputs["Value"], sq.inputs[1])
    add = g.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    add.inputs[1].default_value = 14.0
    g.links.new(sq.outputs[0], add.inputs[0])
    div = g.nodes.new("ShaderNodeMath")
    div.operation = "DIVIDE"
    div.inputs[0].default_value = 70.0
    g.links.new(add.outputs[0], div.inputs[1])
    edge = g.nodes.new("ShaderNodeMapRange")     # fade to 0 at the card edge
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 20.0, 190.0
    edge.inputs["To Min"].default_value, edge.inputs["To Max"].default_value = 1.0, 0.0
    g.links.new(vl.outputs["Value"], edge.inputs["Value"])
    mul = g.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    g.links.new(div.outputs[0], mul.inputs[0])
    g.links.new(edge.outputs["Result"], mul.inputs[1])
    em = g.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.78, 0.52, 1)
    g.links.new(mul.outputs[0], em.inputs["Strength"])
    tr = g.nodes.new("ShaderNodeBsdfTransparent")
    ash = g.nodes.new("ShaderNodeAddShader")
    g.links.new(tr.outputs[0], ash.inputs[0])
    g.links.new(em.outputs[0], ash.inputs[1])
    g.links.new(ash.outputs[0], gout.inputs[0])
    glow.data.materials.append(gm)

    # --- sunlight on the object: a Sun lamp aimed from the Sun at the object, every frame
    li = bpy.data.lights.new("sunlight", "SUN")
    li.energy = 5.0
    li.color = (1.0, 0.93, 0.85)
    li.angle = math.radians(0.6)
    lamp = link(sc, bpy.data.objects.new("sunlight", li))
    lamp.rotation_mode = "QUATERNION"
    for f in range(1, END + 1):
        p = path_pos(s_of_t(_t(f)))
        lamp.rotation_quaternion = p.normalized().to_track_quat("-Z", "Y")  # light travels Sun -> object
        lamp.keyframe_insert("rotation_quaternion", frame=f)
    # fade the light as it leaves (shot D), so it sinks into the dark
    key_value_light(li, [(1, 5.0), (_sec(46.0), 5.0), (_sec(49.6), 0.0)])

    # --- the object: elongated, lumpy, dark reddish; tumbling
    obj = link(sc, uv_sphere("oumuamua", 1.0, 96, 48))
    from mathutils import noise
    for v in obj.data.vertices:   # lumpy rock, then squashed into a long, flattened body
        c = v.co.copy()
        n = 0.22 * noise.noise(c * 1.4 + Vector((3.1, 0.7, 5.2))) + 0.06 * noise.noise(c * 4.5) \
            + 0.02 * noise.noise(c * 11.0)
        c *= 1.0 + n
        # ~6:1 cigar/pancake; "up to ~10:1" is the extreme estimate and the true shape is uncertain
        v.co = Vector((c.x * 0.62, c.y * 0.14, c.z * 0.1))
    sm = obj.modifiers.new("smooth", "SUBSURF")
    sm.levels = sm.render_levels = 1
    om = bpy.data.materials.new("rock_m")
    om.use_nodes = True
    ont = om.node_tree
    bsdf = ont.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.92
    otc = ont.nodes.new("ShaderNodeTexCoord")
    onz = ont.nodes.new("ShaderNodeTexNoise")
    onz.inputs["Scale"].default_value = 9.0
    onz.inputs["Detail"].default_value = 8
    ont.links.new(otc.outputs["Object"], onz.inputs["Vector"])
    ramp = ont.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.3, (0.028, 0.014, 0.011, 1)
    el[1].position, el[1].color = 0.75, (0.12, 0.05, 0.034, 1)
    ont.links.new(onz.outputs["Fac"], ramp.inputs["Fac"])
    ont.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    vor = ont.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 14.0
    ont.links.new(otc.outputs["Object"], vor.inputs["Vector"])
    bump = ont.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.85
    bump.inputs["Distance"].default_value = 0.02
    mixh = ont.nodes.new("ShaderNodeMath")
    mixh.operation = "ADD"
    ont.links.new(vor.outputs["Distance"], mixh.inputs[0])
    ont.links.new(onz.outputs["Fac"], mixh.inputs[1])
    ont.links.new(mixh.outputs[0], bump.inputs["Height"])
    ont.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    obj.data.materials.append(om)
    obj.rotation_mode = "XYZ"
    key_every(obj, "location", lambda f: path_pos(s_of_t(_t(f))))
    key_every(obj, "rotation_euler", lambda f: (0.21 * _t(f) + 0.4, 0.09 * _t(f) + 0.2, 0.31 * _t(f)))
    key_every(obj, "scale", lambda f: (4.5,) * 3 if shot(_t(f)) in "AB" else (1.0,) * 3)
    # In the wide/telescope shots it is only a few pixels: a faint emissive core keeps the speck readable
    spk = ont.nodes.new("ShaderNodeEmission")
    spk.inputs["Color"].default_value = (1.0, 0.55, 0.35, 1)
    spk_s = spk.inputs["Strength"]
    key_value(spk_s, [(1, 1.4), (_sec(T_C) - 1, 1.4), (_sec(T_C), 0.0)])
    ash2 = ont.nodes.new("ShaderNodeAddShader")
    outn = ont.nodes["Material Output"]
    ont.links.new(bsdf.outputs[0], ash2.inputs[0])
    ont.links.new(spk.outputs[0], ash2.inputs[1])
    ont.links.new(ash2.outputs[0], outn.inputs["Surface"])

    # --- the trail: the hyperbolic path drawn behind it in the wide shot (bevel_factor_end follows it)
    s_a0, s_a1 = s_of_t(0), s_of_t(T_B)
    for nm, depth, strength, col, full in (("trail", 0.55, 2.2, (1.0, 0.62, 0.42), False),
                                          ("orbit_ghost", 0.3, 0.35, (0.6, 0.7, 0.9), True)):
        cu = bpy.data.curves.new(nm, "CURVE")
        cu.dimensions = "3D"
        sp = cu.splines.new("POLY")
        N = 400
        s_lo, s_hi = (s_a0 - 120, s_a1 + 260) if full else (s_a0, s_a1)
        sp.points.add(N - 1)
        for i in range(N):
            pp = path_pos(s_lo + (s_hi - s_lo) * i / (N - 1))
            sp.points[i].co = (pp.x, pp.y, pp.z, 1)
        cu.bevel_depth = depth
        cu.bevel_resolution = 2
        cob = link(sc, bpy.data.objects.new(nm, cu))
        cob.data.materials.append(mat_emit(nm + "_m", col, strength))
        camera_only(cob)
        if not full:
            cu.bevel_factor_mapping_end = "SPLINE"
            for f in range(1, _sec(T_B) + 1):
                cu.bevel_factor_end = max(0.001, (s_of_t(_t(f)) - s_a0) / (s_a1 - s_a0))
                cu.keyframe_insert("bevel_factor_end", frame=f)
        hide_keys(cob, [(1, False), (_sec(T_B), True)])

    # --- telescope HUD (shot B): crosshair, reticle ring, circular field stop, label
    fB0, fB1 = _sec(T_B), _sec(T_C)
    dh = 2.6
    hh = dh * 12.0 / LENS
    hw = hh * RES_X / RES_Y
    hud = []
    lw = 0.0022 * hh * 2
    hm = mat_emit("hud_m", (0.85, 0.95, 1.0), 1.1)
    for nm, (x, y, sx, sy) in {"ch_l": (-0.55 * hw, 0, 0.7 * hw, lw), "ch_r": (0.55 * hw, 0, 0.7 * hw, lw),
                               "ch_t": (0, 0.55 * hw, lw, 0.7 * hw), "ch_b": (0, -0.55 * hw, lw, 0.7 * hw)}.items():
        p_ = link(sc, plane(nm, sx, sy))
        p_.data.materials.append(hm)
        p_.parent = cam
        p_.location = (x, y, -dh)
        hud.append(p_)
    for i in range(4):   # small corner brackets around the target
        a = math.pi / 4 + i * math.pi / 2
        for j, (sx, sy, ox, oy) in enumerate(((0.06 * hw, lw, -0.03 * hw * (1 if i in (0, 3) else -1), 0),
                                              (lw, 0.06 * hw, 0, -0.03 * hw * (1 if i in (0, 1) else -1)))):
            cx = 0.11 * hw * math.copysign(1, math.cos(a))
            cy = 0.11 * hw * math.copysign(1, math.sin(a))
            p_ = link(sc, plane(f"br_{i}_{j}", sx, sy))
            p_.data.materials.append(hm)
            p_.parent = cam
            p_.location = (cx + ox, cy + oy, -dh)
            hud.append(p_)
    ring_cu = bpy.data.curves.new("reticle", "CURVE")
    rsp = ring_cu.splines.new("POLY")
    rsp.points.add(127)
    rr = 0.9 * hw
    for i in range(128):
        a = 2 * math.pi * i / 128
        rsp.points[i].co = (rr * math.cos(a), rr * math.sin(a), 0, 1)
    rsp.use_cyclic_u = True
    ring_cu.bevel_depth = lw / 2
    ring = link(sc, bpy.data.objects.new("reticle", ring_cu))
    ring.data.materials.append(hm)
    ring.parent = cam
    ring.location = (0, 0, -dh)
    hud.append(ring)
    # field stop: black outside a circle (radius just outside the reticle), with a soft edge
    fs = link(sc, plane("field_stop", 4 * hh, 4 * hh))
    fs.parent = cam
    fs.location = (0, 0, -dh - 0.05)
    fsm = bpy.data.materials.new("field_stop_m")
    fsm.use_nodes = True
    fnt = fsm.node_tree
    fnt.nodes.clear()
    fo = fnt.nodes.new("ShaderNodeOutputMaterial")
    ftc = fnt.nodes.new("ShaderNodeTexCoord")
    fl = fnt.nodes.new("ShaderNodeVectorMath")
    fl.operation = "LENGTH"
    fnt.links.new(ftc.outputs["Object"], fl.inputs[0])
    fr = fnt.nodes.new("ShaderNodeMapRange")
    fr.inputs["From Min"].default_value, fr.inputs["From Max"].default_value = 0.92 * hw, 1.0 * hw
    fnt.links.new(fl.outputs["Value"], fr.inputs["Value"])
    ftr = fnt.nodes.new("ShaderNodeBsdfTransparent")
    fbk = fnt.nodes.new("ShaderNodeEmission")
    fbk.inputs["Color"].default_value = (0.004, 0.006, 0.008, 1)
    fbk.inputs["Strength"].default_value = 1.0
    fmx = fnt.nodes.new("ShaderNodeMixShader")
    fnt.links.new(fr.outputs["Result"], fmx.inputs[0])
    fnt.links.new(ftr.outputs[0], fmx.inputs[1])
    fnt.links.new(fbk.outputs[0], fmx.inputs[2])
    fnt.links.new(fmx.outputs[0], fo.inputs[0])
    fs.data.materials.append(fsm)
    hud.append(fs)
    for ob in hud:
        camera_only(ob)
        hide_keys(ob, [(1, True), (fB0, False), (fB1, True)])
    lab = caption(sc, cam, "PAN-STARRS1   HALEAKALA, HAWAII\n19 OCT 2017", fB0 + 10, fB1, y=0.74, size=0.024,
                  color=(0.8, 0.92, 1.0), strength=1.0, name="hud_label")

    # --- captions (9)
    S = _sec
    caption(sc, cam, "What came through\nour solar system\nin 2017?", S(0.35), S(5.2))
    caption(sc, cam, "It wasn't from here.\nIt came from\nbetween the stars.", S(6.0), S(11.2))
    caption(sc, cam, "It swung around the Sun.\nNo one saw it coming.", S(12.0), S(17.2))
    caption(sc, cam, "A telescope in Hawaii\nspotted it…\nalready leaving.", S(18.6), S(24.2))
    caption(sc, cam, "They named it 'Oumuamua:\n\"a messenger from afar,\narriving first.\"", S(25.2), S(30.6))
    caption(sc, cam, "Reddish. Tumbling.\nPerhaps up to ten times\nlonger than it is wide.", S(31.4), S(36.6))
    caption(sc, cam, "As it left, it sped up,\nvery slightly.\nNo visible tail.", S(37.2), S(42.4))
    caption(sc, cam, "Ice? Gas we couldn't see?\nScientists still\ndon't agree.", S(43.2), S(49.0))
    caption(sc, cam, "We'll never\nsee it again.", F_CUT + 12, END + 1, y=0.0, size=0.06)

    # --- hard cut to black (a black card behind the captions)
    card = link(sc, plane("blackout", 30))
    card.data.materials.append(mat_emit("blackout_m", (0, 0, 0), 0.0))
    card.parent = cam
    card.location = (0, 0, -3.0)
    camera_only(card)
    hide_keys(card, [(1, True), (F_CUT, False)])
    return sc


def key_value_light(li, pairs):
    for f, v in pairs:
        li.energy = v
        li.keyframe_insert("energy", frame=f)


def render(sc):
    os.makedirs(OUT_DIR, exist_ok=True)
    lo, hi = (int(x) for x in FRAME_RANGE.split(",")) if FRAME_RANGE else (1, END)
    frames = FRAMES_ONLY or range(lo, hi + 1, STEP)
    for f in frames:
        path = os.path.join(OUT_DIR, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue
        with bpy.context.temp_override(scene=sc):   # headless: makes frame_set evaluate this scene
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[oumuamua] {f}/{END}", flush=True)


sc = build()
print(f"[oumuamua] built: {END} frames at {FPS} fps", flush=True)
if AUDIO:
    write_audio(AUDIO)
if RENDER:
    render(sc)
