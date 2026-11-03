"""Ominous short #04 - "What if Earth stopped spinning... instantly?" (9:16, 24 fps, 57 s).

A calm seaside street at dusk. The planet stops; the air, the sea and everything loose do not.
Supersonic wind, flying debris, a wall of water from the west. Then the aftermath from space:
a non-rotating Earth with its oceans pooled at the poles, one equatorial continent, one half in a
months-long day and the other in a months-long night.

Headless (Blender Python module or blender -b):
  python earth_stops.py -- --render --res 540 --samples 8 --threads 2 --step 3 --out DIR
  python earth_stops.py -- --render --frames 1,421,1000 --res 270 --out DIR     (test stills)
  python earth_stops.py -- --audio out.wav                                      (soundtrack only)
"""

import math
import os
import random
import sys
import wave

# ----------------------------------------------------------------------------- CONFIG
FPS = 24
DURATION = 57.0
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
OUT_DIR = _arg("--out", str, None)
STEP = _arg("--step", int, 1)
AUDIO = _arg("--audio", str, None)
if "--frames" in argv:
    FRAMES_ONLY = [int(x) for x in argv[argv.index("--frames") + 1].split(",")]
RES_Y = RES_X * 16 // 9
RES_Y += RES_Y % 2
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = OUT_DIR or os.path.join(HERE, "renders")


def F(s):
    """Seconds -> frame number, snapped to a rendered frame (1, 4, 7, ...) so cuts stay crisp."""
    f = int(round(s * FPS)) + 1
    return 3 * int(round((f - 1) / 3)) + 1


END = int(DURATION * FPS)          # 1368 frames
JOLT = F(17.5)                     # the planet stops: boom
WAVE0 = F(23.5)                    # the wall of water appears over the sea
HIT = F(31.5)                      # the wave reaches the camera: boom, black
CUT = F(32.5)                      # cut to space
REVEAL = F(34.0)                   # soft boom as Earth fades up
YEAR0, YEAR1 = F(41.0), F(55.0)    # the Sun's slow year-long crawl across the sky
FINAL = F(55.0)                    # "One day would last a year." boom, cut to black

CAPTIONS = [
    (0.3, 4.6, "What if Earth stopped\nspinning... instantly?"),
    (5.0, 13.4, "At the equator, the ground\nmoves at about 1,670 km/h"),
    (14.0, 17.45, "Now stop the planet.\nBut not the air."),
    (18.6, 24.2, "Winds of about 1,670 km/h.\nFaster than any tornado."),
    (25.0, 31.0, "And the oceans\nkeep going too."),
    (34.6, 41.0, "Over time, the seas would\npool at the two poles..."),
    (41.6, 47.4, "...leaving one giant\ncontinent at the equator."),
    (48.0, 52.4, "Six months of daylight.\nSix months of night."),
    (52.9, 55.0, "One day would last a year."),
]


# ============================================================================= AUDIO (numpy)
def make_audio(path, sr=44100):
    import numpy as np
    rng = np.random.default_rng(4)
    n = int(DURATION * sr)
    t = np.arange(n) / sr
    tj, th, tc, tr, tf = [(fr - 1) / FPS for fr in (JOLT, HIT, CUT, REVEAL, FINAL)]

    def filt(x, lo=None, hi=None, order=2):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / sr)
        if hi:
            X *= 1 / (1 + (f / hi) ** (2 * order))
        if lo:
            X *= 1 - 1 / (1 + (f / lo) ** (2 * order))
        return np.fft.irfft(X, len(x))

    def ramp(a, b):
        return np.clip((t - a) / (b - a), 0, 1)

    # drone: 41 / 55 Hz with slowly beating partners (0.3 and 0.2 Hz beats)
    drone = np.zeros((2, n))
    for ch in range(2):
        det = 1 + (0.0012 if ch else -0.0012)
        for f0, a in ((41.2, 0.55), (41.5, 0.45), (55.0, 0.30), (55.2, 0.25), (82.4, 0.10)):
            ph = 2 * np.pi * f0 * det * t + 0.3 * np.sin(2 * np.pi * 0.05 * t + f0)
            drone[ch] += a * sum(np.sin(k * ph) / k ** 1.5 for k in range(1, 5))
        drone[ch] = filt(drone[ch], hi=260)
    d_env = (0.35 + 0.35 * ramp(4, 17) + 0.25 * ramp(tj, tj + 1)) * (1 - 0.45 * ramp(tc, tc + 0.1))
    d_env *= ramp(0, 2.5) * (1 - 0.5 * ramp(tf - 2, tf))
    d_env *= np.where(t < tf, 1.0, 0.0)  # the drone dies with the final boom
    mix = drone * d_env * 0.5

    # filtered-noise swells (calm part + space part) and the pre-jolt crescendo
    for ch in range(2):
        nz = filt(rng.standard_normal(n), lo=60, hi=700)
        sw = 0.05 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 9.0 + ch)) * ramp(1, 4)
        sw = sw * (1 - ramp(tj - 0.05, tj)) + 0.06 * ramp(tc, tr + 2) * (1 - ramp(tf - 0.5, tf))
        cres = 0.22 * ramp(tj - 4.5, tj - 0.05) ** 3 * (1 - ramp(tj - 0.05, tj))
        mix[ch] += nz * (sw + cres)
    # supersonic wind roar between the jolt and the wave hit (louder as the wave nears)
    gust = np.interp(t, np.arange(0, DURATION + 1, 0.4), rng.uniform(0.6, 1.0, int(DURATION / 0.4) + 2))
    for ch in range(2):
        roar = filt(rng.standard_normal(n), lo=90, hi=2200) * 0.30 + filt(rng.standard_normal(n), hi=120) * 0.6
        env = ramp(tj, tj + 0.35) * (1 - ramp(th - 0.02, th)) * gust * (0.75 + 0.6 * ramp(th - 7, th))
        mix[ch] += roar * env

    # booms
    def boom(t0, w, tail=1.6):
        L = int((tail * 3.5) * sr)
        tt = np.arange(L) / sr
        fs = 24 + 60 * np.exp(-tt / 0.3)
        body = np.sin(2 * np.pi * np.cumsum(fs) / sr) * np.exp(-tt / tail)
        hit = filt(rng.standard_normal(L), hi=280) * np.exp(-tt / 0.07) * 1.6
        b = (body + 0.5 * hit) * w
        i0 = int(t0 * sr)
        seg = slice(i0, min(n, i0 + L))
        mix[:, seg] += b[: seg.stop - seg.start]

    boom(tj, 1.6, 2.2)
    boom(th, 1.5, 1.8)
    boom(tr, 0.6, 2.0)
    boom(tf, 1.5, 1.4)

    # dark reverb
    irL = int(2.6 * sr)
    ir_t = np.arange(irL) / sr
    out = np.zeros_like(mix)
    for ch in range(2):
        ir = filt(rng.standard_normal(irL), hi=1500) * np.exp(-ir_t / 0.7)
        ir /= np.sqrt(np.sum(ir ** 2))
        m = n + irL
        nfft = 1 << (m - 1).bit_length()
        wet = np.fft.irfft(np.fft.rfft(mix[ch], nfft) * np.fft.rfft(ir, nfft), nfft)[:n]
        out[ch] = 0.75 * mix[ch] + 0.4 * wet
    out = np.tanh(out / np.max(np.abs(out)) * 1.5)
    out *= 0.89 / np.max(np.abs(out))
    out *= 1 - ramp(tf + 1.3, tf + 1.9)   # silence after the last boom's tail
    pcm = (out.T * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print("audio ->", path, flush=True)


if AUDIO:
    make_audio(AUDIO)
    sys.exit(0)

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"


# ============================================================================= helpers
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
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.cycles.max_bounces = 3
    sc.render.use_motion_blur = True
    for v in (2.0, 1.0):  # every 3rd frame is rendered: a long shutter bridges the gaps
        try:
            sc.render.motion_blur_shutter = v
            break
        except Exception:
            pass
    w = bpy.data.worlds.new(name + "_world")
    w.use_nodes = True
    sc.world = w
    return sc


SC = None


def link(ob):
    SC.collection.objects.link(ob)
    return ob


def N(nt, kind, **inputs):
    nd = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k.startswith("_"):
            setattr(nd, k[1:], v)
        else:
            nd.inputs[k].default_value = v
    return nd


def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = N(nt, "ShaderNodeEmission", Color=(*color, 1), Strength=strength)
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def mat_pr(name, color, rough=0.6, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    return m


def box(name, size, loc, mat=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    if mat:
        me.materials.append(mat)
    return ob


def cyl(name, r, h, loc, mat=None, segs=10, r2=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, vec=Vector((0, 0, h / 2)), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    if mat:
        me.materials.append(mat)
    return ob


def sphere(name, r, loc, mat=None, segs=64, rings=32, ico=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if ico:
        bmesh.ops.create_icosphere(bm, subdivisions=ico, radius=r)
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    if mat:
        me.materials.append(mat)
    return ob


def plane(name, sx, sy, loc, mat=None, cuts=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=cuts + 1, y_segments=cuts + 1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, 1)), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    if mat:
        me.materials.append(mat)
    return ob


def key_sock(sock, fv):
    for f, v in fv:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)


def key_prop(ob, path, fv, index=-1):
    for f, v in fv:
        if index >= 0:
            getattr(ob, path)[index] = v
        else:
            setattr(ob, path, v)
        ob.keyframe_insert(path, frame=f, index=index)


def visible(ob, f_in, f_out=None):
    vals = [(1, True), (f_in, False)] + ([(f_out, True)] if f_out else [])
    for f, hide in vals:
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)


def smoothstep(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


def camera(loc, rot_deg, lens):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.05
    cd.clip_end = 1e6
    cam = link(bpy.data.objects.new("cam", cd))
    cam.location = loc
    cam.rotation_euler = [math.radians(a) for a in rot_deg]
    SC.camera = cam
    return cam


def caption(cam, text, f_in, f_out, y=-0.60, size=0.062):
    """Text fixed to the camera, auto-fit to <= 85% of the frame width (re-wrapped if needed)."""
    cu = bpy.data.curves.new(f"cap_{f_in}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    d = 2.0
    half_h = d * cam.data.sensor_height / 2 / cam.data.lens
    half_w = half_h * RES_X / RES_Y
    max_w = 0.85 * 2 * half_w
    want = size * 2 * half_h
    ob = link(bpy.data.objects.new(cu.name, cu))

    def width():
        cu.size = 1.0
        SC.view_layers[0].update()
        xs = [v[0] for v in ob.bound_box]
        w = max(xs) - min(xs)
        return w if w > 0 else 0.5 * max(len(s) for s in cu.body.split("\n"))

    w1 = width()
    if w1 * 0.5 * want > max_w:  # would get too small: re-wrap into more lines
        words, lines, cur = text.replace("\n", " ").split(), [], ""
        per = w1 / max(len(s) for s in cu.body.split("\n"))
        limit = max(10, int(max_w / (per * 0.5 * want)))
        for wd in words:
            if cur and len(cur) + 1 + len(wd) > limit:
                lines.append(cur)
                cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        cu.body = "\n".join(lines)
        w1 = width()
    cu.size = min(want, max_w / w1)
    cu.space_line = 1.1
    ob.data.materials.append(mat_emit(cu.name + "_m", (1, 1, 1), 1.3))
    ob.parent = cam
    ob.location = (0, y * half_h, -d)
    ob.visible_shadow = False
    visible(ob, f_in, f_out)
    return ob


def black_card(cam, fv):
    """fv = [(frame, hidden?)] - a black card right in front of the lens."""
    card = link(bpy.data.objects.new("black", bpy.data.meshes.new("black")))
    card.data.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    card.data.materials.append(mat_emit("black_m", (0, 0, 0), 0.0))
    card.parent = cam
    card.location = (0, 0, -0.5)
    card.visible_shadow = False
    for f, hide in fv:
        card.hide_render = hide
        card.keyframe_insert("hide_render", frame=f)
    return card


# ============================================================================= WORLD
def build_world():
    """Dusk sky (town) and a star field (space); keyed gains switch between them at the cut."""
    nt = SC.world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = N(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    # stars
    acc = None
    for scale, radius, gain in ((150, 0.13, 90.0),):
        vor = N(nt, "ShaderNodeTexVoronoi", Scale=scale)
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        core = N(nt, "ShaderNodeMapRange", **{"From Min": 0.0, "From Max": radius, "To Min": 1.0, "To Max": 0.0})
        nt.links.new(vor.outputs["Distance"], core.inputs["Value"])
        bw = N(nt, "ShaderNodeRGBToBW")
        nt.links.new(vor.outputs["Color"], bw.inputs["Color"])
        pw = N(nt, "ShaderNodeMath", _operation="POWER")
        pw.inputs[1].default_value = 18.0
        nt.links.new(bw.outputs[0], pw.inputs[0])
        m1 = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
        nt.links.new(core.outputs["Result"], m1.inputs[0])
        nt.links.new(pw.outputs[0], m1.inputs[1])
        m2 = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
        m2.inputs[1].default_value = gain
        nt.links.new(m1.outputs[0], m2.inputs[0])
        if acc is None:
            acc = m2.outputs[0]
        else:
            ad = N(nt, "ShaderNodeMath", _operation="ADD")
            nt.links.new(acc, ad.inputs[0])
            nt.links.new(m2.outputs[0], ad.inputs[1])
            acc = ad.outputs[0]
    sgain = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
    nt.links.new(acc, sgain.inputs[0])
    key_sock(sgain.inputs[1], [(1, 0.0), (CUT - 1, 0.0), (CUT, 1.0)])
    # dusk gradient: orange horizon (brighter toward the west, -x) to deep blue
    ramp = N(nt, "ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.5, (0.10, 0.045, 0.03, 1)
    el[1].position, el[1].color = 0.80, (0.004, 0.007, 0.022, 1)
    el.new(0.515).color = (0.32, 0.12, 0.05, 1)
    el.new(0.56).color = (0.09, 0.06, 0.08, 1)
    el.new(0.64).color = (0.022, 0.03, 0.065, 1)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    west = N(nt, "ShaderNodeMapRange", **{"From Min": 0.5, "From Max": 0.0, "To Min": 0.35, "To Max": 1.6})
    nt.links.new(sep.outputs["X"], west.inputs["Value"])
    skyw = N(nt, "ShaderNodeMixRGB", _blend_type="MULTIPLY", Fac=1.0)
    nt.links.new(ramp.outputs["Color"], skyw.inputs[1])
    nt.links.new(west.outputs["Result"], skyw.inputs[2])
    # after the jolt the sky turns a dusty, dim brown
    dust = N(nt, "ShaderNodeMixRGB", _blend_type="MIX")
    nt.links.new(skyw.outputs[0], dust.inputs[1])
    dust.inputs[2].default_value = (0.20, 0.095, 0.045, 1)
    key_sock(dust.inputs["Fac"], [(1, 0.0), (JOLT, 0.0), (JOLT + 48, 0.65), (HIT, 0.8)])
    gain = N(nt, "ShaderNodeMixRGB", _blend_type="MULTIPLY", Fac=1.0)
    nt.links.new(dust.outputs[0], gain.inputs[1])
    key_sock(gain.inputs[2], [(1, (1, 1, 1, 1)), (JOLT, (1, 1, 1, 1)), (HIT, (0.8, 0.8, 0.8, 1)),
                              (CUT - 1, (0.8, 0.8, 0.8, 1)), (CUT, (0, 0, 0, 1))])
    add = N(nt, "ShaderNodeMixRGB", _blend_type="ADD", Fac=1.0)
    nt.links.new(gain.outputs[0], add.inputs[1])
    nt.links.new(sgain.outputs[0], add.inputs[2])
    bg = N(nt, "ShaderNodeBackground", Strength=1.0)
    nt.links.new(add.outputs[0], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])


# ============================================================================= TOWN
def window_material(name, wall, seed):
    """World-space window grid (Brick texture) with random lit windows; lights die after the jolt."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*wall, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = N(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    add = N(nt, "ShaderNodeMath", _operation="ADD")
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    comb = N(nt, "ShaderNodeCombineXYZ")
    nt.links.new(add.outputs[0], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    comb.inputs["Z"].default_value = seed
    br = N(nt, "ShaderNodeTexBrick", Scale=1.0, **{"Mortar Size": 0.55, "Brick Width": 2.2, "Row Height": 3.2,
                                                    "Bias": 0.35, "Mortar Smooth": 0.0})
    br.offset = 0.0
    br.squash = 1.0
    br.inputs["Color1"].default_value = (1.0, 0.62, 0.30, 1)
    br.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1)
    br.inputs["Mortar"].default_value = (0, 0, 0, 1)
    nt.links.new(comb.outputs[0], br.inputs["Vector"])
    em = N(nt, "ShaderNodeEmission")
    nt.links.new(br.outputs["Color"], em.inputs["Color"])
    # power flickers and fails after the jolt
    rng = random.Random(seed)
    fv = [(1, 3.0), (JOLT, 3.0)]
    f = JOLT + 2
    while f < JOLT + 60:
        fv.append((f, rng.choice((0.2, 2.5, 0.0, 3.5))))
        f += rng.randint(2, 5)
    fv.append((f + 1, 0.0))
    key_sock(em.inputs["Strength"], fv)
    win = N(nt, "ShaderNodeMath", _operation="SUBTRACT")
    win.inputs[0].default_value = 1.0
    nt.links.new(br.outputs["Fac"], win.inputs[1])
    addsh = nt.nodes.new("ShaderNodeAddShader")
    mul = N(nt, "ShaderNodeMixShader")
    blackem = N(nt, "ShaderNodeEmission", Strength=0.0)
    nt.links.new(win.outputs[0], mul.inputs["Fac"])
    nt.links.new(blackem.outputs[0], mul.inputs[1])
    nt.links.new(em.outputs[0], mul.inputs[2])
    nt.links.new(bsdf.outputs[0], addsh.inputs[0])
    nt.links.new(mul.outputs[0], addsh.inputs[1])
    nt.links.new(addsh.outputs[0], nt.nodes["Material Output"].inputs[0])
    return m


def sea_material():
    m = mat_pr("sea_m", (0.006, 0.012, 0.018), rough=0.06)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = N(nt, "ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    # calm swell drifts slowly; after the jolt the sea races east and stretches into streaks
    key_sock(mp.inputs["Location"], [(1, (0, 0, 0)), (JOLT, (0.6, 0.3, 0)), (END, (0.6 + 1.0 * (END - JOLT), 0.3, 0))])
    key_sock(mp.inputs["Scale"], [(1, (1, 1, 1)), (JOLT, (1, 1, 1)), (JOLT + 6, (0.18, 1.3, 1))])
    n = N(nt, "ShaderNodeTexNoise", Scale=0.22, Detail=8.0)
    nt.links.new(mp.outputs[0], n.inputs["Vector"])
    bump = N(nt, "ShaderNodeBump", Strength=0.3)
    key_sock(bump.inputs["Strength"], [(1, 0.3), (JOLT, 0.3), (JOLT + 12, 0.8)])
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


def cloud_material():
    """Emissive dusk cloud deck with alpha; streaks sideways at speed after the jolt."""
    m = bpy.data.materials.new("cloud_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = N(nt, "ShaderNodeMapping")
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    key_sock(mp.inputs["Location"], [(1, (0, 0, 0)), (JOLT, (0.00002 * JOLT, 0, 0)),
                                     (END, (0.00002 * JOLT + 0.002 * (END - JOLT), 0, 0))])
    key_sock(mp.inputs["Scale"], [(1, (1, 1, 1)), (JOLT, (1, 1, 1)), (JOLT + 10, (0.12, 1.2, 1))])
    n = N(nt, "ShaderNodeTexNoise", Scale=30.0, Detail=6.0, Roughness=0.6)
    nt.links.new(mp.outputs[0], n.inputs["Vector"])
    cr = N(nt, "ShaderNodeMapRange", **{"From Min": 0.5, "From Max": 0.72, "To Min": 0.0, "To Max": 1.0})
    nt.links.new(n.outputs["Fac"], cr.inputs["Value"])
    em = N(nt, "ShaderNodeEmission", Color=(0.35, 0.16, 0.10, 1))
    key_sock(em.inputs["Strength"], [(1, 0.35), (JOLT, 0.35), (JOLT + 40, 0.12)])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = N(nt, "ShaderNodeMixShader")
    nt.links.new(cr.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def wave_material():
    m = mat_pr("wave_m", (0.004, 0.016, 0.02), rough=0.12)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = N(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    n = N(nt, "ShaderNodeTexNoise", Scale=0.08, Detail=10.0)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    # foam: white on the crest (object z high) and in noisy streaks
    hz = N(nt, "ShaderNodeMapRange", **{"From Min": 50.0, "From Max": 82.0, "To Min": 0.0, "To Max": 1.0})
    nt.links.new(sep.outputs["Z"], hz.inputs["Value"])
    fn = N(nt, "ShaderNodeMath", _operation="ADD")
    nt.links.new(hz.outputs["Result"], fn.inputs[0])
    nn = N(nt, "ShaderNodeMapRange", **{"From Min": 0.55, "From Max": 0.75, "To Min": 0.0, "To Max": 0.7})
    nt.links.new(n.outputs["Fac"], nn.inputs["Value"])
    nt.links.new(nn.outputs["Result"], fn.inputs[1])
    col = N(nt, "ShaderNodeMixRGB", _blend_type="MIX")
    col.use_clamp = True
    nt.links.new(fn.outputs[0], col.inputs["Fac"])
    col.inputs[1].default_value = (0.004, 0.016, 0.02, 1)
    col.inputs[2].default_value = (0.35, 0.38, 0.40, 1)
    nt.links.new(col.outputs[0], b.inputs["Base Color"])
    nt.links.new(col.outputs[0], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 0.5
    bump = N(nt, "ShaderNodeBump", Strength=0.4)
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def build_wave():
    """A long breaking wall of water (~50 m) extruded along the coast, racing in from the west."""
    prof = [(-140, -2), (-70, 6), (-35, 18), (-15, 34), (-4, 46), (3, 52), (9, 51), (13, 46), (12, 40),
            (8, 33), (5, 20), (3, 8), (2, -2)]
    ys = [-150 + 12 * i for i in range(56)]
    me = bpy.data.meshes.new("wave")
    verts, faces = [], []
    rng = random.Random(7)
    wob = [rng.uniform(-1, 1) for _ in ys]
    for j, y in enumerate(ys):
        sx = 1 + 0.08 * math.sin(y * 0.021) + 0.03 * wob[j]
        sz = 1 + 0.10 * math.sin(y * 0.013 + 1.0)
        for x, z in prof:
            verts.append((x * sx * 1.4, y, 1.6 * z * sz if z > 0 else z))
    P = len(prof)
    for j in range(len(ys) - 1):
        for i in range(P - 1):
            a = j * P + i
            faces.append((a, a + 1, a + P + 1, a + P))
    me.from_pydata(verts, [], faces)
    for p in me.polygons:
        p.use_smooth = True
    ob = link(bpy.data.objects.new("wave", me))
    sub = ob.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 1
    tex = bpy.data.textures.new("wave_tex", "CLOUDS")
    tex.noise_scale = 6.0
    dsp = ob.modifiers.new("disp", "DISPLACE")
    dsp.texture = tex
    dsp.strength = 3.0
    ob.data.materials.append(wave_material())
    # x position of the crest: far out at sea -> sweeps over the camera (accelerating)
    for f in range(WAVE0, HIT + 4):
        u = (f - WAVE0) / (HIT - WAVE0)
        x = -420 + 425 * u ** 1.7
        ob.location = (x, 0, -1.0 - 40 * (1 - smoothstep(0.0, 0.35, u)))
        ob.keyframe_insert("location", frame=f)
    visible(ob, WAVE0, CUT)
    return ob


def build_town():
    rng = random.Random(42)
    m_road = mat_pr("road", (0.03, 0.03, 0.032), rough=0.5)
    m_walk = mat_pr("walk", (0.09, 0.085, 0.08), rough=0.8)
    m_trunk = mat_pr("trunk", (0.06, 0.04, 0.025), rough=0.9)
    m_leaf = mat_pr("leaf", (0.02, 0.04, 0.018), rough=0.8)
    m_pole = mat_pr("pole", (0.05, 0.05, 0.05), rough=0.4, metallic=0.8)
    m_lamp = mat_emit("lamp", (1.0, 0.7, 0.4), 30.0)
    plane("road", 9, 900, (3.5, 300, 0), m_road)
    plane("walk", 4, 900, (-3, 300, 0.12), m_walk)
    box("seawall", (1.0, 900, 2.0), (-5.5, 300, -0.88), m_walk)
    plane("walk_r", 4, 900, (10, 300, 0.12), m_walk)
    plane("ground", 200, 900, (110, 300, 0.05), m_walk)
    sea = plane("sea", 6000, 6000, (-3006, 0, -0.8), sea_material())
    clouds = plane("clouds", 8000, 8000, (0, 2000, 380), cloud_material())
    clouds.visible_shadow = False
    # buildings along the east side of the street
    walls = [(0.10, 0.09, 0.085), (0.13, 0.11, 0.09), (0.07, 0.07, 0.08), (0.12, 0.10, 0.10)]
    y = -6.0
    k = 0
    while y < 420:
        w = rng.uniform(9, 18)
        h = rng.uniform(8, 26) if y < 200 else rng.uniform(12, 40)
        d = rng.uniform(10, 18)
        mat = window_material(f"bld{k}_m", walls[k % 4], seed=k * 1.37)
        box(f"bld{k}", (d, w, h), (12 + d / 2, y + w / 2, h / 2), mat)
        y += w + rng.uniform(0.3, 3)
        k += 1
    # a second skyline far behind for depth
    for j in range(14):
        h = rng.uniform(30, 70)
        box(f"far{j}", (25, 30, h), (rng.uniform(30, 120), 460 + j * 35, h / 2), window_material(f"far{j}_m", (0.06, 0.06, 0.07), seed=50 + j))
    # promenade: palms + street lamps (the loose parts get torn away later)
    loose = []
    trunks = []
    for i in range(14):
        yy = 6 + i * 13 + rng.uniform(-2, 2)
        tr = cyl(f"palm{i}", 0.22, 7.5, (-3.6, yy, 0.1), m_trunk, segs=8, r2=0.14)
        trunks.append(tr)
        for j in range(5):
            leaf = sphere(f"frond{i}_{j}", 1.0, (-3.6 + rng.uniform(-1.4, 1.4), yy + rng.uniform(-1.4, 1.4),
                                                 7.4 + rng.uniform(-0.4, 0.6)), m_leaf, ico=2)
            leaf.scale = (rng.uniform(1.6, 2.4), rng.uniform(0.35, 0.5), rng.uniform(0.08, 0.14))
            leaf.rotation_euler = (0, rng.uniform(0.15, 0.5), rng.uniform(0, 6.3))
            loose.append((leaf, 0.3))
    lamps = []
    for i in range(7):
        yy = 12 + i * 26
        cyl(f"pole{i}", 0.08, 6.0, (0.4, yy, 0.1), m_pole, segs=8)
        bulb = sphere(f"bulb{i}", 0.28, (0.4, yy, 6.1), m_lamp, segs=12, rings=6)
        lamps.append(bulb)
        if i < 4:
            li = bpy.data.lights.new(f"lamp{i}", "POINT")
            li.energy = 400
            li.color = (1.0, 0.68, 0.38)
            li.shadow_soft_size = 0.3
            lo = link(bpy.data.objects.new(f"lamp{i}", li))
            lo.location = (0.4, yy, 5.7)
            key_sock_obj(li, [(1, 400), (JOLT, 400), (JOLT + 3, 50), (JOLT + 5, 380), (JOLT + 9, 0)])
    # parked cars (boxes) along the curb, crates, bins, signs on the walk
    m_car = [mat_pr(f"car{c}", col, rough=0.25, metallic=0.5) for c, col in
             enumerate([(0.25, 0.02, 0.02), (0.02, 0.05, 0.12), (0.2, 0.2, 0.2), (0.4, 0.3, 0.1)])]
    for i in range(10):
        yy = 9 + i * 9 + rng.uniform(-1, 1)
        car = box(f"car{i}", (1.9, 4.3, 1.4), (7.0, yy, 0.8), m_car[i % 4])
        loose.append((car, 1.2))
    m_junk = [mat_pr(f"junk{c}", col) for c, col in
              enumerate([(0.15, 0.13, 0.1), (0.3, 0.25, 0.18), (0.08, 0.08, 0.08), (0.4, 0.38, 0.35)])]
    for i in range(70):
        s = rng.uniform(0.2, 1.2)
        ob = box(f"junk{i}", (s * rng.uniform(0.6, 1.6), s, s * rng.uniform(0.3, 1.0)),
                 (rng.uniform(-4.5, 11), rng.uniform(2, 140), s / 2 + 0.1), m_junk[i % 4])
        loose.append((ob, 0.4))
    # roof debris on the building tops
    for i in range(40):
        s = rng.uniform(0.6, 2.5)
        ob = box(f"roof{i}", (s, s * 1.4, s * 0.25), (rng.uniform(13, 22), rng.uniform(0, 150),
                                                       rng.uniform(9, 26)), m_junk[(i + 1) % 4])
        loose.append((ob, 0.6))
    return loose, trunks, lamps


def key_sock_obj(data, fv):
    for f, v in fv:
        data.energy = v
        data.keyframe_insert("energy", frame=f)


def fling(loose, trunks):
    """Everything not bolted down keeps going east (+x) when the ground stops.
    On-screen speeds are scaled down (real: ~465 m/s) so the eye can follow it."""
    rng = random.Random(3)
    for ob, delay in loose:
        t0 = JOLT + int(rng.uniform(0, 40) * delay)
        v = rng.uniform(16, 38) / FPS          # m per frame (scene speed, dramatised)
        vz = rng.uniform(0.5, 6.0) / FPS
        loc0 = ob.location.copy()
        rot0 = ob.rotation_euler.copy()
        dur = END - t0
        key_prop(ob, "location", [(1, loc0), (t0, loc0),
                                  (END, loc0 + Vector((v * dur, rng.uniform(-0.3, 0.3) * dur / FPS, vz * dur)))])
        spin = Vector((rng.uniform(-8, 8), rng.uniform(-8, 8), rng.uniform(-8, 8))) / FPS
        key_prop(ob, "rotation_euler", [(1, rot0), (t0, rot0), (END, Vector(rot0) + spin * dur)])
    # a constant stream of debris blown in from the sea and the town upwind (west)
    m = mat_pr("stream_m", (0.12, 0.1, 0.08))
    for i in range(260):
        s = rng.uniform(0.12, 1.2)
        y = rng.uniform(3, 90)
        z = rng.uniform(0.3, 18)
        ob = box(f"stream{i}", (s * rng.uniform(0.6, 2), s, s * rng.uniform(0.2, 1)), (-300, y, z), m)
        v = rng.uniform(22, 50) / FPS
        t0 = rng.randint(JOLT + 2, HIT)
        x0 = -15 - y * 1.2                       # just outside the frame's left edge at that depth
        key_prop(ob, "location", [(1, (-300, y, z)), (t0 - 3, (-300, y, z)), (t0 - 2, (x0 - 2 * v, y, z)),
                                  (END, (x0 - 2 * v + v * (END - t0 + 2), y, z + rng.uniform(-0.5, 2) * (END - t0) / FPS))])
        spin = Vector((rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(-10, 10))) / FPS
        key_prop(ob, "rotation_euler", [(t0, (0, 0, 0)), (END, spin * (END - t0))])
        visible(ob, t0, None)
    # dust streaks: thin glowing grit that the long shutter turns into speed lines
    ms = mat_emit("streak_m", (0.9, 0.55, 0.3), 1.2)
    for i in range(160):
        y = rng.uniform(2.5, 45)
        z = rng.uniform(0.2, 9)
        ob = box(f"streak{i}", (rng.uniform(0.6, 2.5), 0.025, 0.025), (-300, y, z), ms)
        ob.visible_shadow = False
        v = rng.uniform(40, 75) / FPS
        t0 = rng.randint(JOLT + 1, HIT)
        x0 = -10 - y * 1.2
        key_prop(ob, "location", [(1, (-300, y, z)), (t0 - 3, (-300, y, z)), (t0 - 2, (x0 - 2 * v, y, z)),
                                  (END, (x0 - 2 * v + v * (END - t0 + 2), y, z))])
        visible(ob, t0, None)
    # palm trunks snap and bow east
    for tr in trunks:
        t0 = JOLT + rng.randint(1, 8)
        key_prop(tr, "rotation_euler", [(1, (0, 0, 0)), (t0, (0, 0, 0)),
                                        (t0 + 4, (0, math.radians(rng.uniform(55, 85)), 0))])


def build_town_camera():
    cam = camera((-2.2, -9.0, 1.75), (88, 0, 12), 17)
    rng = random.Random(11)
    # slow push along the promenade before the jolt; violent shake after it
    for f in range(1, CUT - 1):   # ends at CUT-2; the jump to space happens behind the black card
        s = (f - 1) / FPS
        y = -9.0 + 0.28 * min(s, 17.5)
        sh = 0.0
        if f >= JOLT:
            dt = (f - JOLT) / FPS
            sh = 1.6 * math.exp(-dt / 0.6) + 0.35 + 0.35 * smoothstep(HIT - 120, HIT, f)
        jx = sh * math.sin(f * 2.7 + rng.uniform(-1, 1))
        jy = sh * math.sin(f * 3.9 + rng.uniform(-1, 1))
        cam.location = (-2.2 + 0.03 * jx, y, 1.75 + 0.03 * jy)
        cam.rotation_euler = (math.radians(88 + 1.2 * jy + 4 * smoothstep(WAVE0, HIT, f)),
                              math.radians(0.8 * jx), math.radians(12 - 0.5 * min(s, 17.5) + 40 * smoothstep(WAVE0 - 24, WAVE0 + 72, f) + 1.2 * jx))
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    return cam


# ============================================================================= SPACE
SPACE_Z = 60000.0
EARTH_R = 1000.0


def earth_material(sun_vec_keys):
    """Non-rotating Earth after the oceans settle: polar oceans, one equatorial continent."""
    m = bpy.data.materials.new("earth_m")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = N(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    absz = N(nt, "ShaderNodeMath", _operation="ABSOLUTE")
    nt.links.new(sep.outputs["Z"], absz.inputs[0])
    coast = N(nt, "ShaderNodeTexNoise", Scale=2.2, Detail=8.0, Roughness=0.62)
    nt.links.new(tc.outputs["Object"], coast.inputs["Vector"])
    cn = N(nt, "ShaderNodeMath", _operation="MULTIPLY_ADD")
    nt.links.new(coast.outputs["Fac"], cn.inputs[0])
    cn.inputs[1].default_value = 0.55
    nt.links.new(absz.outputs[0], cn.inputs[2])
    sea = N(nt, "ShaderNodeMapRange", **{"From Min": 0.86, "From Max": 0.875, "To Min": 0.0, "To Max": 1.0})
    nt.links.new(cn.outputs[0], sea.inputs["Value"])
    land_n = N(nt, "ShaderNodeTexNoise", Scale=7.0, Detail=10.0, Roughness=0.6)
    nt.links.new(tc.outputs["Object"], land_n.inputs["Vector"])
    lr = N(nt, "ShaderNodeValToRGB")
    el = lr.color_ramp.elements
    el[0].position, el[0].color = 0.35, (0.36, 0.25, 0.13, 1)
    el[1].position, el[1].color = 0.68, (0.10, 0.08, 0.06, 1)
    el.new(0.5).color = (0.55, 0.42, 0.26, 1)
    el.new(0.6).color = (0.20, 0.17, 0.10, 1)
    nt.links.new(land_n.outputs["Fac"], lr.inputs["Fac"])
    # exposed old sea floor (pale salt) along the equator
    eq = N(nt, "ShaderNodeMapRange", **{"From Min": 0.18, "From Max": 0.0, "To Min": 0.0, "To Max": 0.6})
    nt.links.new(absz.outputs[0], eq.inputs["Value"])
    salt_n = N(nt, "ShaderNodeTexNoise", Scale=12.0, Detail=4.0)
    nt.links.new(tc.outputs["Object"], salt_n.inputs["Vector"])
    sm = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
    nt.links.new(eq.outputs["Result"], sm.inputs[0])
    nt.links.new(salt_n.outputs["Fac"], sm.inputs[1])
    land = N(nt, "ShaderNodeMixRGB", _blend_type="MIX")
    nt.links.new(sm.outputs[0], land.inputs["Fac"])
    nt.links.new(lr.outputs["Color"], land.inputs[1])
    land.inputs[2].default_value = (0.62, 0.58, 0.52, 1)
    col = N(nt, "ShaderNodeMixRGB", _blend_type="MIX")
    nt.links.new(sea.outputs["Result"], col.inputs["Fac"])
    nt.links.new(land.outputs[0], col.inputs[1])
    col.inputs[2].default_value = (0.004, 0.018, 0.055, 1)
    nt.links.new(col.outputs[0], b.inputs["Base Color"])
    rough = N(nt, "ShaderNodeMapRange", **{"To Min": 0.85, "To Max": 0.28})
    nt.links.new(sea.outputs["Result"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], b.inputs["Roughness"])
    bump = N(nt, "ShaderNodeBump", Strength=0.25)
    nt.links.new(land_n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def atmo_material(sun_vec_keys):
    """Thin blue rim, only on the sunlit side (normal . sun)."""
    m = bpy.data.materials.new("atmo_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    lw = N(nt, "ShaderNodeLayerWeight", Blend=0.35)
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = N(nt, "ShaderNodeVectorMath", _operation="DOT_PRODUCT")
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    key_sock(dot.inputs[1], sun_vec_keys)
    lit = N(nt, "ShaderNodeMapRange", **{"From Min": -0.15, "From Max": 0.5, "To Min": 0.0, "To Max": 1.0})
    nt.links.new(dot.outputs["Value"], lit.inputs["Value"])
    pw = N(nt, "ShaderNodeMath", _operation="POWER")
    pw.inputs[1].default_value = 2.5
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    mul = N(nt, "ShaderNodeMath", _operation="MULTIPLY")
    nt.links.new(pw.outputs[0], mul.inputs[0])
    nt.links.new(lit.outputs["Result"], mul.inputs[1])
    em = N(nt, "ShaderNodeEmission", Color=(0.25, 0.5, 1.0, 1), Strength=2.2)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    add = nt.nodes.new("ShaderNodeAddShader")
    emm = N(nt, "ShaderNodeMixShader")
    blk = N(nt, "ShaderNodeEmission", Strength=0.0)
    nt.links.new(mul.outputs[0], emm.inputs["Fac"])
    nt.links.new(blk.outputs[0], emm.inputs[1])
    nt.links.new(em.outputs[0], emm.inputs[2])
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(emm.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs[0])
    return m


def sun_dir(f):
    """Direction to the Sun (world). It creeps around the planet once per year: here a time-lapse."""
    a0 = math.radians(-8)   # terminator just left of centre: one half baked, the other in night
    u = smoothstep(YEAR0, YEAR1, f)
    a = a0 + math.radians(70) * u
    return Vector((math.cos(a), -math.sin(a) * 0.9, 0.08)).normalized()


def build_space(cam):
    center = Vector((0, 0, SPACE_Z))
    keys = [(f, tuple(sun_dir(f))) for f in range(CUT, END + 1, 6)]
    e = sphere("earth", 1.0, center, earth_material(keys), segs=128, rings=64)
    e.scale = (EARTH_R,) * 3
    e.rotation_euler = (math.radians(14), 0, 0)   # tip the north polar ocean toward us
    a = sphere("atmo", 1.022, center, atmo_material(keys), segs=96, rings=48)
    a.scale = (EARTH_R,) * 3
    a.visible_shadow = False
    li = bpy.data.lights.new("sun_space", "SUN")
    li.angle = math.radians(0.5)
    li.color = (1.0, 0.96, 0.9)
    sun = link(bpy.data.objects.new("sun_space", li))
    sun.rotation_mode = "QUATERNION"
    key_sock_obj(li, [(1, 0.0), (CUT - 1, 0.0), (CUT, 6.0)])
    for f, v in keys:
        sun.rotation_quaternion = (-Vector(v)).to_track_quat("-Z", "Y")
        sun.keyframe_insert("rotation_quaternion", frame=f)
    # camera: slow drift in toward the planet (Earth sits a little above the captions)
    for f in [CUT - 1] + list(range(CUT, END + 1, 3)):
        u = max(0, f - CUT) / (END - CUT)
        d = 4300 - 1000 * smoothstep(0, 1, u)
        yaw = math.radians(-4 + 8 * u)
        loc = center + Vector((d * math.sin(yaw), -d * math.cos(yaw), -0.07 * d))
        cam.location = loc
        look = (center + Vector((0, 0, -0.22 * EARTH_R)) - loc)
        cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    return e


# ============================================================================= BUILD
def build():
    global SC
    SC = new_scene("earth_stops")
    build_world()
    dusk = bpy.data.lights.new("dusk", "SUN")
    dusk.angle = math.radians(3)
    dusk.color = (1.0, 0.45, 0.22)
    dsun = link(bpy.data.objects.new("dusk", dusk))
    dsun.rotation_mode = "QUATERNION"
    dsun.rotation_quaternion = (-Vector((-1, 0.5, 0.06)).normalized()).to_track_quat("-Z", "Y")
    key_sock_obj(dusk, [(1, 2.4), (JOLT, 2.4), (JOLT + 48, 1.2), (CUT - 1, 1.2), (CUT, 0.0)])
    fill = bpy.data.lights.new("skyfill", "SUN")
    fill.angle = math.radians(60)
    fill.color = (0.35, 0.45, 0.8)
    fo = link(bpy.data.objects.new("skyfill", fill))
    fo.rotation_euler = (math.radians(20), math.radians(-10), 0)
    key_sock_obj(fill, [(1, 0.25), (CUT - 1, 0.25), (CUT, 0.0)])
    loose, trunks, _ = build_town()
    fling(loose, trunks)
    build_wave()
    cam = build_town_camera()
    build_space(cam)
    # town camera keys end at CUT-1; space keys start at CUT -> make that jump instantaneous
    black_card(cam, [(1, True), (HIT, False), (CUT, True), (FINAL, False)])
    for a, b, text in CAPTIONS:
        caption(cam, text, F(a) if a > 0.5 else 1 + int(a * FPS), F(b))
    # fade the space shot up from black: an opacity-keyed card would need alpha; use exposure
    key_prop(SC.view_settings, "exposure", [(1, 0.0), (CUT - 1, 0.0), (CUT, -4.0), (REVEAL + 12, 0.0)])
    # The camera's town keys run to CUT-1 and the space keys start at CUT: nothing between them is
    # rendered (black card from HIT), and motion blur at the CUT frame must not smear across the jump,
    # so blur is switched off for the space shot (nothing there moves fast anyway).
    try:
        key_prop(SC.render, "use_motion_blur", [(1, True), (CUT - 1, True), (CUT, False)])
    except Exception as ex:  # not animatable in this build: keep blur on (the space shot is slow)
        print("[earth_stops] motion blur key failed:", ex)
    return SC


def render(sc):
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = FRAMES_ONLY or range(sc.frame_start, sc.frame_end + 1, STEP)
    for f in frames:
        path = os.path.join(OUT_DIR, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue
        with bpy.context.temp_override(scene=sc):
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[earth_stops] {f}/{sc.frame_end}", flush=True)


sc = build()
print(f"[earth_stops] built: {sc.frame_end} frames, jolt {JOLT}, hit {HIT}, cut {CUT}, final {FINAL}", flush=True)
if RENDER:
    render(sc)
