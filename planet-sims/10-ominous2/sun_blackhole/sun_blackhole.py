"""Ominous short 02: "What if the Sun became a black hole?"  (9:16, 24 fps, 56 s)

Self-contained Blender (Cycles) script plus a numpy soundtrack generator.

  # frames (every 3rd frame, resumable):
  blender -b -P sun_blackhole.py -- --render --every 3 --out /path/frames
  # (or with the bpy module:  python sun_blackhole.py -- --render ...)
  # test stills:
  python sun_blackhole.py -- --render --frames 60,600,1000 --res 270 --samples 8 --threads 1 --out /tmp/t
  # soundtrack only (no Blender needed, just numpy):
  python sun_blackhole.py -- --audio out.wav

Story: a sunny sea at noon -> the Sun collapses into a ~6 km black hole -> for 8 min 20 s nothing
changes -> the Sun's disc vanishes, stars at noon -> space: Earth still orbiting a tiny black dot
with a lensed star ring -> the oceans freeze over -> "We wouldn't fall in. We'd just... freeze."
"""

import math
import os
import sys

FPS = 24
SECONDS = 56
END = SECONDS * FPS            # 1344
RES_X = 540
SAMPLES = 8
THREADS = 0
RENDER = False
OUT_DIR = None
FRAMES_ONLY = None
EVERY = 1
AUDIO = None

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(name, cast=str, default=None):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


RENDER = "--render" in argv
RES_X = _arg("--res", int, RES_X)
SAMPLES = _arg("--samples", int, SAMPLES)
THREADS = _arg("--threads", int, THREADS)
OUT_DIR = _arg("--out", str, None)
EVERY = _arg("--every", int, 1)
AUDIO = _arg("--audio", str, None)
if "--frames" in argv:
    FRAMES_ONLY = [int(x) for x in _arg("--frames").split(",")]
RES_Y = RES_X * 16 // 9
RES_Y -= RES_Y % 2

# ----------------------------------------------------------------------------- timeline (frames)
# Every key beat sits on the every-3rd-frame grid (1 + 3k) so the blended video keeps it sharp.
COLLAPSE = 241     # 10.0 s  the Sun collapses (nothing visible changes)
OFF = 529          # 22.0 s  8 min 20 s later (compressed): its last light has passed us
CUT_SPACE = 721    # 30.0 s  cut to space
FREEZE0 = 880      # oceans start icing over
YEAR = 1159        # "...about -73 C within a year" fully frozen look
FINAL = 1171       # final line
CUT_BLACK = 1291   # 53.75 s final boom, cut to black; silence to 56 s


def t_of(f):
    return (f - 1) / FPS


# ============================================================================= SOUNDTRACK
def write_audio(path, sr=44100):
    import wave
    import numpy as np
    n = int(SECONDS * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(2)

    def env(points):  # piecewise-linear envelope [(sec, gain)]
        xs, ys = zip(*points)
        return np.interp(t, xs, ys)

    def lowpass(x, fc):  # FFT brick-ish lowpass with soft roll-off
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(len(x), 1 / sr)
        X *= 1 / (1 + (fr / fc) ** 4)
        return np.fft.irfft(X, len(x))

    def bandpass(x, lo, hi):
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(len(x), 1 / sr)
        X *= (1 / (1 + (fr / hi) ** 4)) * (1 / (1 + (lo / np.maximum(fr, 1e-3)) ** 4))
        return np.fft.irfft(X, len(x))

    t_off, t_space, t_end = t_of(OFF), t_of(CUT_SPACE), t_of(CUT_BLACK)
    # --- drone: 44 Hz pair beating at ~0.5 Hz, a sub-octave and a soft fifth; drops after the dark
    f0 = np.where(t < t_off, 44.0, 44.0 - 3.0 * np.clip((t - t_off) / 6.0, 0, 1))
    ph = 2 * np.pi * np.cumsum(f0) / sr
    drone_l = (np.sin(ph) + 0.8 * np.sin(ph * 1.0115 + 0.3) + 0.45 * np.sin(ph * 0.5)
               + 0.18 * np.sin(ph * 1.5 + 1.0) + 0.08 * np.sin(ph * 3.0))
    drone_r = (np.sin(ph * 1.0012 + 0.7) + 0.8 * np.sin(ph * 1.0128) + 0.45 * np.sin(ph * 0.5 + 0.4)
               + 0.18 * np.sin(ph * 1.5 + 2.0) + 0.08 * np.sin(ph * 3.0 + 0.5))
    slow = 1 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    d_env = env([(0, 0), (2.5, 0.35), (t_of(COLLAPSE), 0.45), (t_off - 0.3, 0.6), (t_off + 2, 0.5),
                 (t_space, 0.55), (t_end - 0.05, 0.75), (t_end, 0.0), (SECONDS, 0.0)]) * slow
    # --- filtered noise swells (wind / rumble), rising into the darkness and into the final line
    noise = rng.standard_normal(n)
    rumble = lowpass(noise, 140.0)
    air = bandpass(rng.standard_normal(n), 300.0, 1800.0)
    rumble /= np.abs(rumble).max()
    air /= np.abs(air).max()
    s_env = env([(0, 0), (3, 0.15), (9, 0.25), (10.5, 0.1), (t_off - 0.2, 0.7), (t_off, 0.05),
                 (t_off + 4, 0.15), (t_space - 1, 0.35), (t_space + 1, 0.12), (40, 0.3), (46, 0.18),
                 (t_end - 0.1, 0.8), (t_end, 0.0), (SECONDS, 0.0)])
    a_env = env([(0, 0), (4, 0.05), (t_off - 0.5, 0.25), (t_off, 0.0), (t_space + 3, 0.0), (t_end - 2, 0.12),
                 (t_end, 0.0), (SECONDS, 0.0)])

    # --- deep booms on the key beats
    def boom(at, gain, length=3.5, f_hi=75.0, f_lo=28.0):
        out = np.zeros(n)
        i0 = int(at * sr)
        m = min(n - i0, int(length * sr))
        tt = np.arange(m) / sr
        f = f_lo + (f_hi - f_lo) * np.exp(-tt * 3.0)
        p = 2 * np.pi * np.cumsum(f) / sr
        body = np.sin(p) * np.exp(-tt * 1.3) * (1 - np.exp(-tt * 300))
        thump = lowpass(rng.standard_normal(m), 90.0)
        thump = thump / np.abs(thump).max() * np.exp(-tt * 6.0)
        out[i0:i0 + m] = gain * (body + 0.5 * thump)
        return out

    booms = (boom(t_of(COLLAPSE), 0.35, 3.0) + boom(t_off, 1.0, 4.0) + boom(t_space, 0.55, 3.5)
             + boom(t_of(YEAR) - 5.0, 0.3, 3.0) + boom(t_end, 1.0, 1.8, 70.0, 26.0))
    left = 0.30 * d_env * drone_l + 0.35 * s_env * rumble + 0.10 * a_env * air + 0.55 * booms
    right = 0.30 * d_env * drone_r + 0.35 * s_env * np.roll(rumble, 911) + 0.10 * a_env * np.roll(air, 377) \
        + 0.55 * booms
    st = np.stack([left, right], 1)
    st /= max(1e-9, np.abs(st).max()) / 0.89
    tail = int((t_end + 1.7) * sr)       # pure silence after the last boom has died away
    fade = int(0.5 * sr)
    st[tail - fade:tail] *= np.linspace(1, 0, fade)[:, None]
    st[tail:] = 0
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    print(f"[sun_blackhole] wrote {path} ({SECONDS} s)", flush=True)


if AUDIO and not RENDER:
    write_audio(AUDIO)
    sys.exit(0)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else bpy.path.abspath("//")
OUT_DIR = OUT_DIR or os.path.join(HERE, "renders", "sun_blackhole")


# ============================================================================= helpers (from 08-ominous)
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
    for look in ("AgX - Punchy", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            pass
    sc.cycles.max_bounces = 2
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


def mat_principled(name, color, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
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


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k == "op":
            n.operation = v
        else:
            n.inputs[k].default_value = v
    return n


def math_op(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def vec_op(nt, op, a, b=None, scale=None):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    nt.links.new(a, n.inputs[0])
    if b is not None:
        nt.links.new(b, n.inputs[1])
    if scale is not None:
        if isinstance(scale, (int, float)):
            n.inputs["Scale"].default_value = scale
        else:
            nt.links.new(scale, n.inputs["Scale"])
    return n


def mix_rgb(nt, blend, a, b, fac=1.0):
    n = nt.nodes.new("ShaderNodeMixRGB")
    n.blend_type = blend
    n.inputs["Fac"].default_value = fac
    for i, x in ((1, a), (2, b)):
        if isinstance(x, tuple):
            n.inputs[i].default_value = (*x, 1) if len(x) == 3 else x
        else:
            nt.links.new(x, n.inputs[i])
    return n.outputs[0]


def key_sock(sock, frames_values):
    for f, v in frames_values:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)


def key_every(ob, path, fn, f0, f1):
    for f in range(f0, f1 + 1):
        setattr(ob, path, fn(f))
        ob.keyframe_insert(path, frame=f)


def key_hide(ob, frames_hidden):
    for f, h in frames_hidden:
        ob.hide_render = h
        ob.keyframe_insert("hide_render", frame=f)


def smoothstep(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


def caption(sc, cam, text, f_in, f_out, y=-0.62, size=0.062, color=(1, 1, 1), strength=3.0, name=None):
    """Text fixed to the camera (y in -1..1 of frame height), visible f_in..f_out, auto-fit to <=85% width."""
    cu = bpy.data.curves.new(name or f"cap_{f_in}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    d = 2.0
    half_h = d * math.tan(math.atan(cam.data.sensor_height / 2 / cam.data.lens))
    half_w = half_h * sc.render.resolution_x / sc.render.resolution_y
    max_w = 0.85 * 2 * half_w
    want = size * 2 * half_h
    ob = link(sc, bpy.data.objects.new(cu.name, cu))

    def text_width():
        cu.size = 1.0
        try:
            bpy.context.view_layer.update()
        except Exception:
            pass
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
    cu.size = min(want, max_w / w1)
    ob.data.materials.append(mat_emit(cu.name + "_m", color, strength))
    ob.parent = cam
    ob.location = (0, y * half_h, -d)
    ob.visible_shadow = False
    try:
        ob.visible_diffuse = ob.visible_glossy = False
    except AttributeError:
        pass
    key_hide(ob, ((1, True), (f_in, False), (f_out, True)))
    return ob


# ============================================================================= the film
SP = Vector((0.0, 0.0, 20000.0))   # the black hole (space set lives far above the sea set)
ORBIT_R = 9.0                       # dramatised: Earth radius = 1
BH_R = 0.5                          # dramatised size of the black "shadow"
THETA_E = 0.11                      # dramatised Einstein-ring angle (radians) seen from the camera
SHADOW = 0.6 * THETA_E              # angular radius of the black shadow


def earth_phi(f):
    return math.radians(-25 + 55 * (f - CUT_SPACE) / (END - CUT_SPACE))


def earth_pos(f):
    p = earth_phi(f)
    return SP + Vector((ORBIT_R * math.cos(p), ORBIT_R * math.sin(p), 0.0))


def space_cam(f):
    """Camera rides behind Earth (outward from the hole), above the orbital plane; slow push-in."""
    e = earth_pos(f)
    out = (e - SP).normalized()
    side = Vector((0, 0, 1)).cross(out)
    u = smoothstep(CUT_SPACE, CUT_BLACK, f)
    back = 6.2 - 2.4 * u
    up = 3.4 - 1.0 * u
    c = e + out * back + Vector((0, 0, up)) + side * (0.9 - 0.4 * u)
    tgt = e.lerp(SP, 0.42 - 0.04 * u) + Vector((0, 0, -0.2))
    return c, tgt


def ground_cam(f):
    u = smoothstep(1, CUT_SPACE, f)
    c = Vector((0.0, -40.0 + 22.0 * u, 3.2))
    pitch = math.radians(7.0 + 3.0 * u)
    d = Vector((math.sin(math.radians(3)) * math.cos(pitch), math.cos(pitch), math.sin(pitch)))
    return c, c + d * 100


def cam_at(f):
    return ground_cam(f) if f < CUT_SPACE else space_cam(f)


SUN_EL, SUN_AZ = math.radians(29.0), math.radians(5.0)
SDIR = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))


def build_world(sc):
    nt = sc.world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    D = vec_op(nt, "NORMALIZE", tc.outputs["Generated"]).outputs[0]
    # ---- gravitational lensing of the star field (point-lens approximation, deflection theta_E^2/theta)
    B = nt.nodes.new("ShaderNodeCombineXYZ")          # unit vector camera -> black hole (keyed per frame)
    dB = vec_op(nt, "DOT_PRODUCT", D, B.outputs[0]).outputs["Value"]
    perp = vec_op(nt, "SUBTRACT", B.outputs[0], vec_op(nt, "SCALE", D, scale=dB).outputs[0]).outputs[0]
    p2 = math_op(nt, "MAXIMUM", vec_op(nt, "DOT_PRODUCT", perp, perp).outputs["Value"], 1e-7)
    front = math_op(nt, "GREATER_THAN", dB, 0.0)
    lens = nt.nodes.new("ShaderNodeValue")             # theta_E^2, 0 before the space shots
    k = math_op(nt, "MULTIPLY", math_op(nt, "DIVIDE", lens.outputs[0], p2), front)
    D2 = vec_op(nt, "NORMALIZE", vec_op(nt, "ADD", D, vec_op(nt, "SCALE", perp, scale=k).outputs[0]).outputs[0])
    D2 = D2.outputs[0]
    # ---- point stars (big enough to survive the denoiser), on the lensed direction
    acc = None
    for scale, radius, gain, power in ((110, 0.17, 300.0, 20.0), (230, 0.2, 90.0, 22.0), (60, 0.12, 400.0, 30.0)):
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        nt.links.new(D2, vor.inputs["Vector"])
        core = node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": radius, "To Min": 1.0, "To Max": 0.0})
        nt.links.new(vor.outputs["Distance"], core.inputs["Value"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(vor.outputs["Color"], bw.inputs["Color"])
        s = math_op(nt, "MULTIPLY", math_op(nt, "MULTIPLY", core.outputs["Result"],
                                            math_op(nt, "POWER", bw.outputs[0], power)), gain)
        acc = s if acc is None else math_op(nt, "ADD", acc, s)
    # faint star dust + a lensed galactic band: smooth textures make the warping obvious
    dust = nt.nodes.new("ShaderNodeTexVoronoi")
    dust.inputs["Scale"].default_value = 520
    nt.links.new(D2, dust.inputs["Vector"])
    dcore = node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.22, "To Min": 1.0, "To Max": 0.0})
    nt.links.new(dust.outputs["Distance"], dcore.inputs["Value"])
    sep2 = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(D2, sep2.inputs[0])
    band = math_op(nt, "EXPONENT", math_op(nt, "MULTIPLY", math_op(nt, "POWER",
                   math_op(nt, "DIVIDE", math_op(nt, "SUBTRACT", sep2.outputs["Z"], 0.18), 0.22), 2.0), -1.0))
    neb = node(nt, "ShaderNodeTexNoise", Scale=4.0, Detail=2.0, Roughness=0.5)
    nt.links.new(D2, neb.inputs["Vector"])
    nebm = node(nt, "ShaderNodeMapRange", **{"From Min": 0.42, "From Max": 0.75})
    nt.links.new(neb.outputs["Fac"], nebm.inputs["Value"])
    nebv = math_op(nt, "MULTIPLY", math_op(nt, "MULTIPLY", band, nebm.outputs["Result"]), 0.008)
    # rings (theta ~ sqrt(p2)): a thin bright Einstein ring with a soft halo, and a faint photon ring
    th = math_op(nt, "SQRT", p2)

    def gauss(center, width, gain):
        g = math_op(nt, "DIVIDE", math_op(nt, "SUBTRACT", th, center), width)
        g = math_op(nt, "EXPONENT", math_op(nt, "MULTIPLY", math_op(nt, "POWER", g, 2.0), -1.0))
        return math_op(nt, "MULTIPLY", g, gain)

    ring = math_op(nt, "ADD", gauss(THETA_E, THETA_E * 0.022, 1.3), gauss(THETA_E, THETA_E * 0.2, 0.04))
    ring = math_op(nt, "ADD", ring, gauss(SHADOW * 1.03, THETA_E * 0.015, 0.25))
    ringv = nt.nodes.new("ShaderNodeValue")
    ring = math_op(nt, "MULTIPLY", math_op(nt, "MULTIPLY", ring, front), ringv.outputs[0])
    stars = mix_rgb(nt, "MULTIPLY", acc, (0.86, 0.92, 1.0))
    stars = mix_rgb(nt, "ADD", stars, mix_rgb(nt, "MULTIPLY", nebv, (0.55, 0.6, 1.0)))
    stars = mix_rgb(nt, "ADD", stars, mix_rgb(nt, "MULTIPLY", ring, (0.8, 0.88, 1.0)))
    # pure black shadow (only once the lens is on)
    inside = math_op(nt, "MULTIPLY", math_op(nt, "LESS_THAN", th, SHADOW), front)
    inside = math_op(nt, "MULTIPLY", inside, math_op(nt, "GREATER_THAN", lens.outputs[0], 0.0))
    stars = mix_rgb(nt, "MIX", stars, (0.0, 0.0, 0.0))
    nt.links.new(inside, stars.node.inputs["Fac"])
    lp = nt.nodes.new("ShaderNodeLightPath")
    cam_only = mix_rgb(nt, "MIX", (0.0, 0.0, 0.0), stars)
    nt.links.new(lp.outputs["Is Camera Ray"], cam_only.node.inputs["Fac"])
    bg_st = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(cam_only, bg_st.inputs["Color"])
    # ---- noon sky (unlensed): blue gradient + glow around the Sun
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(D, sep.inputs[0])
    grad = node(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": 0.7})
    nt.links.new(sep.outputs["Z"], grad.inputs["Value"])
    sky = nt.nodes.new("ShaderNodeValToRGB")
    se = sky.color_ramp.elements
    se[0].position, se[0].color = 0.0, (0.32, 0.52, 0.85, 1)
    se[1].position, se[1].color = 1.0, (0.008, 0.04, 0.26, 1)
    se.new(0.12).color = (0.06, 0.2, 0.62, 1)
    se.new(0.45).color = (0.02, 0.09, 0.42, 1)
    nt.links.new(grad.outputs["Result"], sky.inputs["Fac"])
    sd = vec_op(nt, "DOT_PRODUCT", D, None).outputs["Value"]
    sd.node.inputs[1].default_value = tuple(SDIR)
    gl = node(nt, "ShaderNodeMapRange", **{"From Min": 0.996, "From Max": 1.0})
    nt.links.new(sd, gl.inputs["Value"])
    glow = mix_rgb(nt, "MULTIPLY", math_op(nt, "POWER", gl.outputs["Result"], 4.0), (1.6, 1.5, 1.3))
    bg_sky = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(mix_rgb(nt, "ADD", sky.outputs["Color"], glow), bg_sky.inputs["Color"])
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bg_sky.outputs[0], add.inputs[0])
    nt.links.new(bg_st.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], wout.inputs[0])
    # ---- keys
    key_sock(bg_sky.inputs["Strength"], [(1, 0.55), (OFF - 1, 0.55), (OFF, 0.0)])
    key_sock(bg_st.inputs["Strength"], [(1, 0.0), (OFF + 6, 0.0), (OFF + 100, 1.0)])
    key_sock(lens.outputs[0], [(1, 0.0), (CUT_SPACE - 1, 0.0), (CUT_SPACE, THETA_E ** 2)])
    key_sock(ringv.outputs[0], [(1, 0.0), (CUT_SPACE - 1, 0.0), (CUT_SPACE, 1.0)])
    for f in range(1, END + 1):
        if f < CUT_SPACE and f not in (1, CUT_SPACE - 1):
            continue
        c, _ = cam_at(f)
        b = (SP - c).normalized() if f >= CUT_SPACE else Vector((0, 0, 1))
        for i in range(3):
            B.inputs[i].default_value = b[i]
            B.inputs[i].keyframe_insert("default_value", frame=f)


def build_ground(sc):
    """Noon sea with low islands on the horizon, the Sun's disc and its light."""
    objs = []
    sea = link(sc, plane("sea", 30000))
    m = mat_principled("sea_m", (0.002, 0.03, 0.07), rough=0.16)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = node(nt, "ShaderNodeTexNoise", Scale=0.35, Detail=8.0)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    bump = node(nt, "ShaderNodeBump", Strength=0.22)
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    sea.data.materials.append(m)
    objs.append(sea)
    land = mat_principled("isle_m", (0.06, 0.08, 0.05), rough=0.9)
    for i, (x, y, sx, sy, sz) in enumerate(((-900, 4200, 1300, 500, 130), (700, 5200, 900, 400, 220),
                                            (1900, 4600, 700, 300, 90))):
        isle = link(sc, uv_sphere(f"isle{i}", 1.0, 48, 24))
        isle.location = (x, y, -sz * 0.35)
        isle.scale = (sx, sy, sz)
        isle.data.materials.append(land)
        objs.append(isle)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.angle = math.radians(0.6)
    sun.color = (1.0, 0.95, 0.88)
    sun_ob = link(sc, bpy.data.objects.new("sun", sun))
    sun_ob.rotation_mode = "QUATERNION"
    sun_ob.rotation_quaternion = (-SDIR).to_track_quat("-Z", "Y")
    key_sock_obj = [(1, 4.5), (OFF - 1, 4.5), (OFF, 0.0)]
    for f, v in key_sock_obj:
        sun.energy = v
        sun.keyframe_insert("energy", frame=f)
    disc = link(sc, uv_sphere("sun_disc", 1.0, 48, 24))
    disc.data.materials.append(mat_emit("sun_disc_m", (1.0, 0.95, 0.85), 60.0))
    disc.visible_shadow = False
    d = 50000
    disc.location = Vector((0, -30, 3.2)) + SDIR * d
    disc.scale = [d * math.tan(math.radians(0.75))] * 3
    key_hide(disc, ((1, False), (OFF, True)))
    # faint starlight once the eyes adapt
    night = bpy.data.lights.new("starlight_g", "SUN")
    night.color = (0.55, 0.65, 1.0)
    night.angle = math.radians(30)
    nob = link(sc, bpy.data.objects.new("starlight_g", night))
    nob.rotation_euler = (math.radians(40), 0, math.radians(160))
    for f, v in ((1, 0.0), (OFF + 30, 0.0), (OFF + 150, 0.06), (CUT_SPACE - 1, 0.06), (CUT_SPACE, 0.0)):
        night.energy = v
        night.keyframe_insert("energy", frame=f)
    for ob in objs:
        key_hide(ob, ((1, False), (CUT_SPACE, True)))


def build_space(sc):
    """A tiny black sphere (the 'shadow') + Earth on its unchanged orbit, freezing over."""
    hole = link(sc, uv_sphere("black_hole", BH_R, 64, 32))
    hole.location = SP
    hole.data.materials.append(mat_emit("hole_m", (0, 0, 0), 0.0))
    hole.visible_shadow = False
    earth = link(sc, uv_sphere("earth", 1.0, 192, 96))
    m = mat_principled("earth_m", (0.02, 0.08, 0.25), rough=0.6)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    landn = node(nt, "ShaderNodeTexNoise", Scale=1.15, Detail=14.0, Roughness=0.62, Distortion=0.35)
    nt.links.new(tc.outputs["Object"], landn.inputs["Vector"])
    lc = nt.nodes.new("ShaderNodeValToRGB")
    e = lc.color_ramp.elements
    e[0].position, e[0].color = 0.35, (0.004, 0.014, 0.05, 1)
    e[1].position, e[1].color = 0.80, (0.42, 0.38, 0.32, 1)
    for pos, col in ((0.50, (0.008, 0.03, 0.09)), (0.535, (0.02, 0.08, 0.14)), (0.545, (0.09, 0.13, 0.05)),
                     (0.58, (0.07, 0.12, 0.04)), (0.62, (0.20, 0.18, 0.09)), (0.66, (0.52, 0.38, 0.21)),
                     (0.72, (0.36, 0.28, 0.18))):
        e.new(pos).color = (*col, 1)
    nt.links.new(landn.outputs["Fac"], lc.inputs["Fac"])
    # ice: grows from the poles towards the equator, ragged edge
    sepz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sepz.inputs[0])
    icen = node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=10.0, Roughness=0.65)
    nt.links.new(tc.outputs["Object"], icen.inputs["Vector"])
    lat = math_op(nt, "ABSOLUTE", sepz.outputs["Z"])
    wob = math_op(nt, "MULTIPLY_ADD", icen.outputs["Fac"], 0.35)
    nt.links.new(lat, wob.node.inputs[2])
    ice = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(wob, ice.inputs["Value"])
    key_sock(ice.inputs["From Min"], [(1, 1.17), (FREEZE0, 1.17), (YEAR, 0.24)])
    key_sock(ice.inputs["From Max"], [(1, 1.23), (FREEZE0, 1.23), (YEAR, 0.30)])
    icef = ice.outputs["Result"]
    icem = mix_rgb(nt, "MIX", lc.outputs["Color"], (0.9, 0.95, 1.0))
    nt.links.new(icef, icem.node.inputs["Fac"])
    nt.links.new(icem, b.inputs["Base Color"])
    rr = node(nt, "ShaderNodeMapRange", **{"From Min": 0.535, "From Max": 0.545, "To Min": 0.3, "To Max": 0.92})
    nt.links.new(landn.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    # city lights still burning on a planet that is all night side; they dim as the ice comes
    city = node(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=4.0)
    nt.links.new(tc.outputs["Object"], city.inputs["Vector"])
    cm = node(nt, "ShaderNodeMapRange", **{"From Min": 0.6, "From Max": 0.72})
    nt.links.new(city.outputs["Fac"], cm.inputs["Value"])
    landm = node(nt, "ShaderNodeMapRange", **{"From Min": 0.545, "From Max": 0.6})
    nt.links.new(landn.outputs["Fac"], landm.inputs["Value"])
    lights = math_op(nt, "MULTIPLY", cm.outputs["Result"], landm.outputs["Result"])
    lights = math_op(nt, "MULTIPLY", lights, math_op(nt, "SUBTRACT", 1.0, icef))
    lv = nt.nodes.new("ShaderNodeValue")
    key_sock(lv.outputs[0], [(1, 2.2), (FREEZE0, 2.2), (YEAR, 0.5), (END, 0.3)])
    lights = math_op(nt, "MULTIPLY", lights, lv.outputs[0])
    # ice glows faintly pale blue (dramatised so it reads on a night-side planet), brighter at its edge
    edge = math_op(nt, "MULTIPLY", math_op(nt, "MULTIPLY", icef, math_op(nt, "SUBTRACT", 1.0, icef)), 4.0)
    glowi = math_op(nt, "ADD", math_op(nt, "MULTIPLY", icef, 0.10), math_op(nt, "MULTIPLY", edge, 0.9))
    b.inputs["Emission Color"].default_value = (1.0, 0.6, 0.26, 1)
    ecol = mix_rgb(nt, "MIX", (1.0, 0.6, 0.26), (0.7, 0.85, 1.0))
    nt.links.new(math_op(nt, "MINIMUM", math_op(nt, "MULTIPLY", icef, 4.0), 1.0), ecol.node.inputs["Fac"])
    nt.links.new(ecol, b.inputs["Emission Color"])
    nt.links.new(math_op(nt, "ADD", lights, glowi), b.inputs["Emission Strength"])
    earth.data.materials.append(m)
    earth.rotation_euler = (math.radians(23.4), 0, 0)
    key_every(earth, "location", earth_pos, CUT_SPACE, END)
    earth.keyframe_insert("rotation_euler", index=2, frame=CUT_SPACE)
    earth.rotation_euler[2] = math.radians(70)
    earth.keyframe_insert("rotation_euler", index=2, frame=END)
    # faint cold rim so the planet's shape reads (starlight, dramatised)
    rim = mat_emit("atm_m", (0.25, 0.45, 1.0), 0.0)
    rnt = rim.node_tree
    em = rnt.nodes["Emission"]
    geo = rnt.nodes.new("ShaderNodeNewGeometry")
    nd = rnt.nodes.new("ShaderNodeVectorMath")
    nd.operation = "DOT_PRODUCT"
    rnt.links.new(geo.outputs["Normal"], nd.inputs[0])
    rnt.links.new(geo.outputs["Incoming"], nd.inputs[1])
    fr = math_op(rnt, "POWER", math_op(rnt, "SUBTRACT", 1.0, math_op(rnt, "ABSOLUTE", nd.outputs["Value"])), 5.0)
    rnt.links.new(math_op(rnt, "MULTIPLY", fr, 0.9), em.inputs["Strength"])
    tr = rnt.nodes.new("ShaderNodeBsdfTransparent")
    addm = rnt.nodes.new("ShaderNodeAddShader")
    rnt.links.new(tr.outputs[0], addm.inputs[0])
    rnt.links.new(em.outputs[0], addm.inputs[1])
    rnt.links.new(addm.outputs[0], rnt.nodes["Material Output"].inputs[0])
    atm = link(sc, uv_sphere("atmosphere", 1.02, 128, 64))
    atm.data.materials.append(rim)
    atm.visible_shadow = False
    atm.parent = earth
    starl = bpy.data.lights.new("starlight_s", "SUN")
    starl.color = (0.6, 0.7, 1.0)
    starl.angle = math.radians(40)
    sob = link(sc, bpy.data.objects.new("starlight_s", starl))
    sob.rotation_euler = (math.radians(35), 0, math.radians(-40))
    for f, v in ((1, 0.0), (CUT_SPACE - 1, 0.0), (CUT_SPACE, 0.8)):
        starl.energy = v
        starl.keyframe_insert("energy", frame=f)
    hole.hide_render = True   # the shadow is drawn by the lensing world shader instead
    for ob in (earth, atm):
        key_hide(ob, ((1, True), (CUT_SPACE, False)))


def blackout(sc, cam, frame):
    card = link(sc, plane("blackout", 6.0))
    card.data.materials.append(mat_emit("blackout_m", (0, 0, 0), 0.0))
    card.parent = cam
    card.location = (0, 0, -0.8)
    card.visible_shadow = False
    key_hide(card, ((1, True), (frame, False)))


def build():
    sc = new_scene("sun_blackhole")
    cd = bpy.data.cameras.new("cam")
    cd.lens = 26
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.05
    cd.clip_end = 1e6
    cam = link(sc, bpy.data.objects.new("cam", cd))
    cam.rotation_mode = "QUATERNION"
    sc.camera = cam
    for f in range(1, END + 1):
        c, tgt = cam_at(f)
        cam.location = c
        cam.rotation_quaternion = (tgt - c).to_track_quat("-Z", "Y")
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_quaternion", frame=f)
    build_world(sc)
    build_ground(sc)
    build_space(sc)
    # ---- captions
    caption(sc, cam, "What if the Sun\nbecame a black hole?", 4, 112, y=-0.55, size=0.07)
    caption(sc, cam, "It never will.\nIt would need about\n20 times more mass.", 118, 232, y=-0.55)
    caption(sc, cam, "But imagine it collapsed anyway,\ninto a ball about 6 km across.", 238, 348, y=-0.55)
    caption(sc, cam, "Its last light still needs\n8 minutes 20 seconds\nto reach us.", 354, OFF - 4, y=-0.55)
    timer = caption(sc, cam, "08:20", COLLAPSE + 6, OFF + 1, y=0.66, size=0.09, color=(1, 0.97, 0.9),
                    strength=4.0, name="timer")
    caption(sc, cam, "Then the sky goes black.\nStars at noon.", OFF + 14, CUT_SPACE - 8, y=-0.55)
    caption(sc, cam, "Earth's orbit wouldn't change.\nSame mass. Same pull.", CUT_SPACE + 14, FREEZE0 + 20,
            y=0.72)
    caption(sc, cam, "Scientists estimate:\nbelow freezing within about a week…", FREEZE0 + 26, 1030, y=0.72)
    caption(sc, cam, "…around −73°C\nwithin a year.", 1036, FINAL - 6, y=0.72)
    caption(sc, cam, "We wouldn't fall in.\nWe'd just… freeze.", FINAL, CUT_BLACK, y=0.72, size=0.075)
    blackout(sc, cam, CUT_BLACK)

    def tick(scene, *_):
        if scene.name != sc.name:
            return
        f = scene.frame_current
        left = 500 if f < COLLAPSE + 30 else max(0, round(500 * (1 - (f - COLLAPSE - 30) / (OFF - COLLAPSE - 30))))
        timer.data.body = f"{left // 60:02d}:{left % 60:02d}"

    bpy.app.handlers.frame_change_pre.append(tick)
    return sc


def render(sc):
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = FRAMES_ONLY or range(1, END + 1, EVERY)
    for f in frames:
        path = os.path.join(OUT_DIR, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue  # resumable
        # headless fix: without the scene override frame_set() does not evaluate the animation
        with bpy.context.temp_override(scene=sc):
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[sun_blackhole] {f}/{END}", flush=True)


sc = build()
print(f"[sun_blackhole] built: {END} frames at {FPS} fps, {RES_X}x{RES_Y}", flush=True)
if AUDIO:
    write_audio(AUDIO)
if RENDER:
    render(sc)
