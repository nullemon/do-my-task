"""What if the Sun went supernova?  (ominous vertical short, ~56 s, 9:16, 24 fps)

The Sun can't go supernova (far too little mass). This is a clearly framed "what if":
calm sea at midday -> neutrinos -> 8:20 countdown -> blinding white flash ->
view from space: the expanding blast shell engulfs a glowing, ablating Earth -> black.

Everything is procedural. Run headless with the Blender Python module (or `blender -b -P`):

  python sun_supernova.py -- --render --out DIR [--res 540] [--samples 8] [--threads 2]
                             [--every 3] [--frames 150,700] [--first 1 --last 1344]
  python sun_supernova.py -- --audio OUT.wav        # soundtrack only (numpy), no rendering
"""

import math
import os
import sys

import bpy

# ----------------------------------------------------------------------------- CONFIG
FPS = 24
SECONDS = 56
END = SECONDS * FPS               # 1344 frames
RES_X, SAMPLES, THREADS = 540, 8, 0
RENDER, OUT_DIR, AUDIO = False, None, None
FRAMES_ONLY, EVERY, FIRST, LAST = None, 1, 1, END

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(name, cast=str, default=None):
    return cast(argv[argv.index(name) + 1]) if name in argv else default


RENDER = "--render" in argv
RES_X = _arg("--res", int, RES_X)
SAMPLES = _arg("--samples", int, SAMPLES)
THREADS = _arg("--threads", int, THREADS)
OUT_DIR = _arg("--out", str, None)
AUDIO = _arg("--audio", str, None)
EVERY = _arg("--every", int, 1)
FIRST = _arg("--first", int, 1)
LAST = _arg("--last", int, END)
if "--frames" in argv:
    FRAMES_ONLY = [int(x) for x in _arg("--frames").split(",")]
RES_X -= RES_X % 2
RES_Y = (RES_X * 16 // 9) // 2 * 2
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else bpy.path.abspath("//")
OUT_DIR = OUT_DIR or os.path.join(HERE, "renders")


def S(sec):
    """Seconds -> frame number."""
    return int(round(sec * FPS)) + 1


# ----------------------------------------------------------------------------- timeline (frames)
F_HOOK = (S(0.15), S(3.7))
F_CANT = (S(4.3), S(10.0))
F_BUT = (S(10.8), S(14.6))          # soft boom
F_NEUT = (S(15.4), S(21.6))
F_LIGHT = (S(22.4), S(33.0))        # countdown 08:20 -> 00:00 over this span
FLASH = S(33.0)                     # the light arrives: big boom
CUT = S(35.0)                       # (under the white) switch to the space set
WHITE_OUT = (S(36.0), S(37.6))      # white fades away to reveal space
F_GALAXY = (S(37.8), S(43.2))
F_BLAST = (S(44.0), S(49.6))
ENGULF = S(47.4)                    # blast front reaches Earth's centre: boom
WHITE2 = (S(50.6), S(51.4))         # front reaches the camera
BLACK = S(51.8)                     # hard cut to black: final boom
F_END = (S(52.6), END + 1)


# ----------------------------------------------------------------------------- helpers
def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def ease_pts(pts, x):
    """Piecewise smoothstep through [(x, value), ...]."""
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
    sc.cycles.max_bounces = 4
    sc.cycles.transparent_max_bounces = 16
    w = bpy.data.worlds.new(name + "_world")
    w.use_nodes = True
    sc.world = w
    return sc


def link(sc, ob):
    sc.collection.objects.link(ob)
    return ob


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def math_node(nt, op, a=None, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def anim(target, path, fn, index=-1, frames=None):
    """Key fn(frame) on every frame (exact values; no interpolation surprises)."""
    for f in frames or range(1, END + 1):
        v = fn(f)
        if index >= 0:
            getattr(target, path)[index] = v
        else:
            setattr(target, path, v)
        target.keyframe_insert(path, frame=f, index=index)


def anim_sock(sock, fn, frames=None):
    for f in frames or range(1, END + 1):
        sock.default_value = fn(f)
        sock.keyframe_insert("default_value", frame=f)


def show_between(ob, f_in, f_out):
    for f, hide in ((1, True), (f_in, False), (f_out, True)):
        if f < 1:
            continue
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)


def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission", Color=(*color, 1), Strength=strength)
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


def caption(sc, cam, text, f_in, f_out, y=-0.62, size=0.062, color=(1, 1, 1), strength=2.2, name=None):
    """Thin white text fixed to the camera, auto-fit to <= 85% of the frame width."""
    cu = bpy.data.curves.new(name or f"cap_{f_in}", "FONT")
    cu.body = text
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    d = 2.0
    half_h = d * cam.data.sensor_height / 2 / cam.data.lens
    half_w = half_h * RES_X / RES_Y
    max_w = 0.85 * 2 * half_w
    want = size * 2 * half_h
    ob = link(sc, bpy.data.objects.new(cu.name, cu))
    cu.size = 1.0
    w1 = 0.0
    try:
        sc.view_layers[0].update()
        xs = [v[0] for v in ob.bound_box]
        w1 = max(xs) - min(xs)
    except Exception:
        pass
    if w1 <= 0:
        w1 = 0.55 * max(len(s) for s in text.split("\n"))
    cu.size = min(want, max_w / w1)
    ob.data.materials.append(mat_emit(cu.name + "_m", color, strength))
    ob.parent = cam
    ob.location = (0, y * half_h, -d)
    ob.visible_shadow = False
    try:
        ob.visible_diffuse = ob.visible_glossy = ob.visible_transmission = False
    except AttributeError:
        pass
    show_between(ob, f_in, f_out)
    # drop shadow (same text, black, slightly offset and behind) keeps it readable on bright frames
    sh = link(sc, ob.copy())
    sh.name = cu.name + "_shadow"
    sh.material_slots[0].link = "OBJECT"
    sh.material_slots[0].material = mat_emit(cu.name + "_sm", (0, 0, 0), 0.0)
    off = 0.045 * cu.size
    sh.location = (off, y * half_h - off, -d - 0.01)
    if sh.animation_data:
        sh.animation_data_clear()
    show_between(sh, f_in, f_out)
    return ob


def card(sc, cam, name, dist, color, fac_fn):
    """Full-frame card in front of the lens; fac_fn(frame) 0 = invisible .. 1 = opaque color."""
    ob = link(sc, plane(name, 40.0))
    m = bpy.data.materials.new(name + "_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = node(nt, "ShaderNodeEmission", Color=(*color, 1), Strength=1.0 if max(color) > 0 else 0.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    anim_sock(mix.inputs["Fac"], fac_fn)
    ob.data.materials.append(m)
    ob.parent = cam
    ob.location = (0, 0, -dist)
    ob.visible_shadow = False
    try:
        ob.visible_diffuse = ob.visible_glossy = ob.visible_transmission = False
    except AttributeError:
        pass
    # only render it while it is doing something (saves transparent bounces)
    on = [f for f in range(1, END + 1) if fac_fn(f) > 0.001]
    if on:
        show_between(ob, on[0], on[-1] + 1)
    return ob


def star_layers(nt, tc, layers):
    """Point stars ~1-2 px so they survive the denoiser. layers = [(scale, radius, gain, power)]."""
    acc = None
    for scale, radius, gain, power in layers:
        vor = node(nt, "ShaderNodeTexVoronoi", Scale=scale)
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        core = node(nt, "ShaderNodeMapRange")
        core.inputs["From Max"].default_value = radius
        core.inputs["To Min"].default_value, core.inputs["To Max"].default_value = 1.0, 0.0
        nt.links.new(vor.outputs["Distance"], core.inputs["Value"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(vor.outputs["Color"], bw.inputs["Color"])
        v = math_node(nt, "MULTIPLY", core.outputs["Result"], math_node(nt, "POWER", bw.outputs[0], power))
        v = math_node(nt, "MULTIPLY", v, gain)
        acc = v if acc is None else math_node(nt, "ADD", acc, v)
    return acc


# ----------------------------------------------------------------------------- the scene
SUN_EL = math.radians(27.0)
SDIR = (0.0, math.cos(SUN_EL), math.sin(SUN_EL))      # ground set: direction to the Sun
SPACE = (0.0, 0.0, 0.0)          # space set shares the origin (ground set is hidden by then; keeps float precision)
U = (1.0, 0.22, 0.08)                                 # space set: direction to the (exploding) Sun
_n = math.sqrt(sum(c * c for c in U))
U = tuple(c / _n for c in U)
R_E = 100.0                                           # Earth radius (space set units)
D_SHELL = 6000.0                                      # shell centre distance (not to scale)
CAM_SPACE_0 = (-215.0, -1000.0, 45.0)                 # camera offset from Earth (start / end)
CAM_SPACE_1 = (-170.0, -820.0, 30.0)


def front_s(f):
    """Signed distance of the blast front from Earth's centre along U (constant speed)."""
    f0, s0, f1, s1 = S(41.5), 650.0, ENGULF, 0.0
    return s0 + (s1 - s0) * (f - f0) / (f1 - f0)


def flash_k(f):
    """0 before the light arrives, rising to 1 in ~0.4 s."""
    return smoothstep(FLASH - 1, FLASH + 9, f)


def build():
    from mathutils import Vector
    sc = new_scene("sun_supernova")
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    except Exception:
        pass
    is_space = lambda f: f >= CUT

    # ---------------- world: midday sky (+sun glow) -> star field in space
    nt = sc.world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    grad = node(nt, "ShaderNodeMapRange")
    grad.inputs["From Min"].default_value, grad.inputs["From Max"].default_value = -0.02, 0.7
    nt.links.new(sep.outputs["Z"], grad.inputs["Value"])
    sky = nt.nodes.new("ShaderNodeValToRGB")
    sky.color_ramp.interpolation = "EASE"
    el = sky.color_ramp.elements
    el[0].position, el[0].color = 0.0, (0.62, 0.72, 0.84, 1)
    el[1].position, el[1].color = 1.0, (0.05, 0.16, 0.48, 1)
    el.new(0.06).color = (0.42, 0.58, 0.80, 1)
    el.new(0.3).color = (0.16, 0.34, 0.70, 1)
    nt.links.new(grad.outputs["Result"], sky.inputs["Fac"])
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = SDIR
    nt.links.new(tc.outputs["Generated"], dot.inputs[0])
    # glow around the Sun; its width (power) collapses at the flash so the whole sky goes white
    glow_p = nt.nodes.new("ShaderNodeValue")
    anim_sock(glow_p.outputs[0], lambda f: 900.0 * (1 - flash_k(f)) + 6.0 * flash_k(f))
    gl = math_node(nt, "POWER", math_node(nt, "MAXIMUM", dot.outputs["Value"], 0.0), glow_p.outputs[0])
    gl_gain = nt.nodes.new("ShaderNodeValue")
    anim_sock(gl_gain.outputs[0], lambda f: 6.0 + 400.0 * flash_k(f))
    gl = math_node(nt, "MULTIPLY", gl, gl_gain.outputs[0])
    glc = nt.nodes.new("ShaderNodeMixRGB")
    glc.blend_type = "MULTIPLY"
    glc.inputs["Fac"].default_value = 1.0
    glc.inputs[2].default_value = (1.0, 0.93, 0.82, 1)
    nt.links.new(gl, glc.inputs[1])
    skyc = nt.nodes.new("ShaderNodeMixRGB")
    skyc.blend_type = "ADD"
    skyc.inputs["Fac"].default_value = 1.0
    nt.links.new(sky.outputs["Color"], skyc.inputs[1])
    nt.links.new(glc.outputs[0], skyc.inputs[2])
    bg_sky = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(skyc.outputs[0], bg_sky.inputs["Color"])
    anim_sock(bg_sky.inputs["Strength"], lambda f: 0.0 if is_space(f) else 1.0 + 30.0 * flash_k(f))
    stars = star_layers(nt, tc, [(110, 0.17, 300.0, 20.0), (230, 0.2, 90.0, 22.0)])
    lp = nt.nodes.new("ShaderNodeLightPath")         # stars are seen but light nothing
    st = math_node(nt, "MULTIPLY", stars, lp.outputs["Is Camera Ray"])
    bg_st = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(st, bg_st.inputs["Color"])
    anim_sock(bg_st.inputs["Strength"], lambda f: 1.0 if is_space(f) else 0.0)
    addw = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bg_sky.outputs[0], addw.inputs[0])
    nt.links.new(bg_st.outputs[0], addw.inputs[1])
    nt.links.new(addw.outputs[0], wout.inputs[0])

    # ---------------- ground set: calm midday sea
    sea = link(sc, plane("sea", 40000))
    sm = bpy.data.materials.new("sea_m")
    sm.use_nodes = True
    snt = sm.node_tree
    b = snt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.010, 0.040, 0.065, 1)
    b.inputs["Roughness"].default_value = 0.06
    b.inputs["IOR"].default_value = 1.33
    stc = snt.nodes.new("ShaderNodeTexCoord")
    mp = node(snt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.22, 0.6, 1.0)
    snt.links.new(stc.outputs["Object"], mp.inputs["Vector"])
    nz = snt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 1.1
    nz.inputs["Detail"].default_value = 6
    snt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    anim_sock(nz.inputs["W"], lambda f: 0.0012 * f)
    bump = node(snt, "ShaderNodeBump", Strength=0.3, Distance=0.25)
    snt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    snt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    sea.data.materials.append(sm)
    sea.visible_shadow = False
    show_between(sea, 1, CUT)

    li = bpy.data.lights.new("sunlight", "SUN")
    li.color = (1.0, 0.95, 0.88)
    li.angle = math.radians(0.53)
    sun_ob = link(sc, bpy.data.objects.new("sunlight", li))
    sun_ob.rotation_mode = "QUATERNION"
    sun_ob.rotation_quaternion = (-Vector(SDIR)).to_track_quat("-Z", "Y")
    anim(li, "energy", lambda f: 0.0 if is_space(f) else 4.5 + 300.0 * flash_k(f))

    disc = link(sc, uv_sphere("sun_disc", 1.0, 48, 24))
    dm = mat_emit("sun_disc_m", (1.0, 0.95, 0.86), 60.0)
    anim_sock(dm.node_tree.nodes["Emission"].inputs["Strength"], lambda f: 60.0 + 6000.0 * flash_k(f))
    disc.data.materials.append(dm)
    disc.visible_shadow = False
    dd = 50000.0
    CAM_G = (0.0, 0.0, 2.2)
    disc.location = (CAM_G[0] + dd * SDIR[0], CAM_G[1] + dd * SDIR[1], CAM_G[2] + dd * SDIR[2])
    r0 = dd * math.tan(math.radians(0.36))
    anim(disc, "scale", lambda f: [r0 * (1.0 + 14.0 * flash_k(f))] * 3)
    show_between(disc, 1, CUT)

    # ---------------- space set: Earth, the blast shell, ablation plume
    O = Vector(SPACE)
    u = Vector(U)
    earth = link(sc, uv_sphere("earth", R_E, 192, 96))
    earth.location = O
    em_ = bpy.data.materials.new("earth_m")
    em_.use_nodes = True
    ent = em_.node_tree
    eb = ent.nodes["Principled BSDF"]
    eb.inputs["Roughness"].default_value = 0.6
    etc = ent.nodes.new("ShaderNodeTexCoord")
    land = node(ent, "ShaderNodeTexNoise", Scale=1.6 / R_E, Detail=10.0, Roughness=0.6)
    ent.links.new(etc.outputs["Object"], land.inputs["Vector"])
    lr = ent.nodes.new("ShaderNodeValToRGB")
    le = lr.color_ramp.elements
    le[0].position, le[0].color = 0.0, (0.006, 0.03, 0.12, 1)
    le[1].position, le[1].color = 1.0, (0.35, 0.30, 0.22, 1)
    le.new(0.585).color = (0.012, 0.05, 0.16, 1)
    le.new(0.6).color = (0.07, 0.13, 0.04, 1)
    le.new(0.7).color = (0.22, 0.20, 0.10, 1)
    ent.links.new(land.outputs["Fac"], lr.inputs["Fac"])
    cl = node(ent, "ShaderNodeTexNoise", Scale=3.5 / R_E, Detail=8.0, Roughness=0.62, Distortion=0.6)
    ent.links.new(etc.outputs["Object"], cl.inputs["Vector"])
    clm = node(ent, "ShaderNodeMapRange")
    clm.inputs["From Min"].default_value, clm.inputs["From Max"].default_value = 0.52, 0.72
    ent.links.new(cl.outputs["Fac"], clm.inputs["Value"])
    # the clouds burn off as the planet heats
    heat = ent.nodes.new("ShaderNodeValue")
    heat_fn = lambda f: ease_pts([(CUT, 0.0), (S(40.0), 0.0), (S(45.5), 0.6), (ENGULF, 3.0), (WHITE2[0], 8.0)], f)
    anim_sock(heat.outputs[0], heat_fn)
    cloud_amt = math_node(nt=ent, op="MULTIPLY", a=clm.outputs["Result"],
                          b=math_node(ent, "MAXIMUM", math_node(ent, "SUBTRACT", 1.0, math_node(ent, "MULTIPLY", heat.outputs[0], 0.6)), 0.0))
    cmix = ent.nodes.new("ShaderNodeMixRGB")
    nt_l = ent.links.new
    nt_l(cloud_amt, cmix.inputs["Fac"])
    nt_l(lr.outputs["Color"], cmix.inputs[1])
    cmix.inputs[2].default_value = (0.85, 0.86, 0.88, 1)
    nt_l(cmix.outputs[0], eb.inputs["Base Color"])
    # day-side incandescence: emission ~ max(0, N.U) * heat, colour from dull red to white
    geo = ent.nodes.new("ShaderNodeNewGeometry")
    nd = ent.nodes.new("ShaderNodeVectorMath")
    nd.operation = "DOT_PRODUCT"
    nd.inputs[1].default_value = tuple(U)
    nt_l(geo.outputs["Normal"], nd.inputs[0])
    day = math_node(ent, "POWER", math_node(ent, "MAXIMUM", nd.outputs["Value"], 0.0), 0.6)
    lava = node(ent, "ShaderNodeTexNoise", Scale=6.0 / R_E, Detail=6.0)
    nt_l(etc.outputs["Object"], lava.inputs["Vector"])
    lav = math_node(ent, "ADD", math_node(ent, "MULTIPLY", lava.outputs["Fac"], 1.2), 0.2)
    glowv = math_node(ent, "MULTIPLY", math_node(ent, "MULTIPLY", day, lav), heat.outputs[0])
    hot = ent.nodes.new("ShaderNodeValToRGB")
    he = hot.color_ramp.elements
    he[0].position, he[0].color = 0.0, (0.5, 0.05, 0.0, 1)
    he[1].position, he[1].color = 1.0, (1.0, 0.95, 0.85, 1)
    he.new(0.4).color = (1.0, 0.35, 0.05, 1)
    nt_l(math_node(ent, "MULTIPLY", glowv, 0.18), hot.inputs["Fac"])
    for nm in ("Emission Color", "Emission"):
        if nm in eb.inputs:
            nt_l(hot.outputs["Color"], eb.inputs[nm])
            break
    nt_l(math_node(ent, "MULTIPLY", glowv, 2.5), eb.inputs["Emission Strength"])
    earth.data.materials.append(em_)
    show_between(earth, CUT, BLACK)

    # thin glowing atmosphere/ablation envelope, stretched away from the blast into a plume
    plume = link(sc, uv_sphere("plume", 1.0, 96, 48))
    plume.rotation_mode = "QUATERNION"
    plume.rotation_quaternion = (-u).to_track_quat("X", "Z")
    pk = lambda f: smoothstep(S(45.0), WHITE2[0], f)
    anim(plume, "scale", lambda f: (R_E * (1.05 + 1.8 * pk(f) ** 1.3), R_E * (1.05 + 0.18 * pk(f)), R_E * (1.05 + 0.18 * pk(f))))
    anim(plume, "location", lambda f: tuple(O + (-u) * (R_E * 1.3 * pk(f) ** 1.3)))
    pm = bpy.data.materials.new("plume_m")
    pm.use_nodes = True
    pnt = pm.node_tree
    pnt.nodes.clear()
    pout = pnt.nodes.new("ShaderNodeOutputMaterial")
    lw = node(pnt, "ShaderNodeLayerWeight", Blend=0.35)
    ptc = pnt.nodes.new("ShaderNodeTexCoord")
    pn = pnt.nodes.new("ShaderNodeTexNoise")
    pn.noise_dimensions = "4D"
    pn.inputs["Scale"].default_value = 3.0
    pn.inputs["Detail"].default_value = 8
    pn.inputs["Distortion"].default_value = 1.5
    pnt.links.new(ptc.outputs["Object"], pn.inputs["Vector"])
    anim_sock(pn.inputs["W"], lambda f: 0.004 * f)
    pstr = pnt.nodes.new("ShaderNodeValue")
    anim_sock(pstr.outputs[0], lambda f: 0.15 * smoothstep(CUT, S(39), f) + 4.0 * pk(f))
    edge = math_node(pnt, "POWER", math_node(pnt, "SUBTRACT", 1.0, lw.outputs["Facing"]), 2.0)
    pv = math_node(pnt, "MULTIPLY", math_node(pnt, "MULTIPLY", edge, math_node(pnt, "MULTIPLY", math_node(pnt, "POWER", pn.outputs["Fac"], 3.0), 4.0)),
                   pstr.outputs[0])
    pemi = node(pnt, "ShaderNodeEmission", Color=(1.0, 0.45, 0.12, 1))
    pnt.links.new(pv, pemi.inputs["Strength"])
    ptr = pnt.nodes.new("ShaderNodeBsdfTransparent")
    padd = pnt.nodes.new("ShaderNodeAddShader")
    pnt.links.new(ptr.outputs[0], padd.inputs[0])
    pnt.links.new(pemi.outputs[0], padd.inputs[1])
    pnt.links.new(padd.outputs[0], pout.inputs[0])
    plume.data.materials.append(pm)
    plume.visible_shadow = False
    show_between(plume, CUT, BLACK)

    # blast shell: three nested spherical caps (front, mid, deep) facing Earth = cheap volume
    import bmesh
    a = -u
    t1 = a.orthogonal().normalized()
    t2 = a.cross(t1).normalized()
    half = math.radians(40.0)
    n_r, n_a = 220, 256
    centre = O + u * D_SHELL
    for i, (off, col, gain, alpha) in enumerate((
            (0.0, (1.0, 0.72, 0.38), 5.0, 0.35),
            (140.0, (1.0, 0.40, 0.10), 3.5, 0.35),
            (420.0, (0.9, 0.20, 0.04), 2.5, 0.8))):
        me = bpy.data.meshes.new(f"shell{i}")
        bm = bmesh.new()
        tip = bm.verts.new(tuple(a))
        rows = []
        for r in range(1, n_r + 1):
            th = half * (r / n_r) ** 1.6       # denser near the axis (where Earth is)
            row = []
            for k in range(n_a):
                ph = 2 * math.pi * k / n_a
                d = a * math.cos(th) + (t1 * math.cos(ph) + t2 * math.sin(ph)) * math.sin(th)
                row.append(bm.verts.new(tuple(d)))
            rows.append(row)
        for k in range(n_a):
            bm.faces.new((tip, rows[0][k], rows[0][(k + 1) % n_a]))
        for r in range(n_r - 1):
            for k in range(n_a):
                k2 = (k + 1) % n_a
                bm.faces.new((rows[r][k], rows[r + 1][k], rows[r + 1][k2], rows[r][k2]))
        for f_ in bm.faces:
            f_.smooth = True
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        sh = link(sc, bpy.data.objects.new(f"shell{i}", me))
        sh.location = centre
        anim(sh, "scale", lambda f, off=off: [max(10.0, D_SHELL - front_s(f) - off)] * 3)
        m = bpy.data.materials.new(f"shell{i}_m")
        m.use_nodes = True
        mt = m.node_tree
        mt.nodes.clear()
        mout = mt.nodes.new("ShaderNodeOutputMaterial")
        mtc = mt.nodes.new("ShaderNodeTexCoord")
        n1 = mt.nodes.new("ShaderNodeTexNoise")
        n1.noise_dimensions = "4D"
        n1.inputs["Scale"].default_value = 18.0 + 8.0 * i
        n1.inputs["Detail"].default_value = 10
        n1.inputs["Roughness"].default_value = 0.62
        n1.inputs["Distortion"].default_value = 2.5
        mt.links.new(mtc.outputs["Object"], n1.inputs["Vector"])
        anim_sock(n1.inputs["W"], lambda f, i=i: 0.002 * f + 3.1 * i)
        fil = node(mt, "ShaderNodeMapRange")
        fil.inputs["From Min"].default_value, fil.inputs["From Max"].default_value = 0.38, 0.72
        mt.links.new(n1.outputs["Fac"], fil.inputs["Value"])
        fil_v = math_node(mt, "POWER", fil.outputs["Result"], 1.8)
        lw2 = node(mt, "ShaderNodeLayerWeight", Blend=0.5)
        limb = math_node(mt, "ADD", 0.35, math_node(mt, "MULTIPLY", math_node(mt, "POWER", math_node(
            mt, "SUBTRACT", 1.0, lw2.outputs["Facing"]), 3.0), 3.0))
        strength = math_node(mt, "MULTIPLY", math_node(mt, "MULTIPLY", math_node(mt, "ADD", fil_v, 0.12), limb), gain)
        emi = node(mt, "ShaderNodeEmission", Color=(*col, 1))
        mt.links.new(strength, emi.inputs["Strength"])
        tr = mt.nodes.new("ShaderNodeBsdfTransparent")
        mix = mt.nodes.new("ShaderNodeMixShader")
        mt.links.new(math_node(mt, "MINIMUM", math_node(mt, "MULTIPLY", math_node(mt, "ADD", fil_v, 0.35), alpha), 1.0),
                     mix.inputs["Fac"])
        mt.links.new(tr.outputs[0], mix.inputs[1])
        mt.links.new(emi.outputs[0], mix.inputs[2])
        mt.links.new(mix.outputs[0], mout.inputs[0])
        sh.data.materials.append(m)
        sh.visible_shadow = False
        show_between(sh, CUT, BLACK)

    # light in space: the supernova itself, off-frame to the right, very bright
    sl = bpy.data.lights.new("nova_light", "SUN")
    sl.color = (1.0, 0.9, 0.8)
    sl.angle = math.radians(2.0)
    sl_ob = link(sc, bpy.data.objects.new("nova_light", sl))
    sl_ob.rotation_mode = "QUATERNION"
    sl_ob.rotation_quaternion = (-u).to_track_quat("-Z", "Y")
    anim(sl, "energy", lambda f: (9.0 + 10.0 * smoothstep(S(44), ENGULF, f)) if is_space(f) else 0.0)

    # ---------------- camera
    cd = bpy.data.cameras.new("cam")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.1
    cd.clip_end = 1e7
    cam = link(sc, bpy.data.objects.new("cam", cd))
    sc.camera = cam
    cam.rotation_mode = "QUATERNION"

    def cam_loc(f):
        if not is_space(f):
            t = (f - 1) / (CUT - 1)
            return (0.0, 0.0, CAM_G[2] + 0.6 * t)
        t = smoothstep(CUT, WHITE2[1], f)
        return tuple(O + Vector(CAM_SPACE_0).lerp(Vector(CAM_SPACE_1), t))

    def cam_rot(f):
        if not is_space(f):
            t = (f - 1) / (CUT - 1)
            pitch = math.radians(11.0 - 1.5 * t)     # slow tilt down toward the horizon
            fwd = Vector((0.0, math.cos(pitch), math.sin(pitch)))
            return tuple(fwd.to_track_quat("-Z", "Y"))
        loc = Vector(cam_loc(f))
        tgt = O + Vector((35.0, 0.0, -10.0))
        return tuple((tgt - loc).normalized().to_track_quat("-Z", "Z"))

    def cam_lens(f):
        return 20.0 if not is_space(f) else 34.0

    anim(cam, "location", cam_loc)
    anim(cam, "rotation_quaternion", cam_rot)
    anim(cd, "lens", cam_lens)
    cd.lens = 20.0      # lens used for caption sizing (captions scale with lens: re-fit below)

    # ---------------- cards: whiteout, blackout
    def white_fac(f):
        if f < CUT:
            return smoothstep(FLASH + 2, FLASH + 14, f)
        if f < WHITE2[0]:
            return 1.0 - smoothstep(WHITE_OUT[0], WHITE_OUT[1], f)
        return smoothstep(WHITE2[0], WHITE2[1], f)

    card(sc, cam, "whiteout", 2.8, (1.0, 0.97, 0.92), white_fac)
    blk = link(sc, plane("blackout", 40.0))
    blk.data.materials.append(mat_emit("blackout_m", (0, 0, 0), 0.0))
    blk.parent = cam
    blk.location = (0, 0, -2.5)
    blk.visible_shadow = False
    show_between(blk, BLACK, END + 2)

    # ---------------- captions (fitted for the lens in use when each is shown)
    def cap(text, span, **kw):
        cd.lens = cam_lens(span[0])
        ob = caption(sc, cam, text, span[0], span[1], **kw)
        # keep its size right if the lens changes while it is shown (it doesn't here)
        return ob

    cap("What if the Sun\nwent supernova?", F_HOOK, size=0.072)
    cap("It can't. It's far too small.\nIt will swell into a red giant,\nthen fade to a white dwarf.", F_CANT)
    cap("…but what if it did?", F_BUT, size=0.07)
    cap("First, a flood of neutrinos.\nThis close, even they\ncould be lethal.", F_NEUT)
    cap("Then the light,\n8 minutes 20 seconds behind.", F_LIGHT)
    cnt = cap("08:20", (F_LIGHT[0], FLASH), y=0.78, size=0.085, strength=2.6)
    cnt.data.name = "countdown"
    cap("For weeks, it would outshine\nthe entire galaxy.", F_GALAXY)
    cap("Within hours, the blast\nwould boil Earth away.", F_BLAST)
    cap("No one would be left\nto see it.", F_END, y=0.0, size=0.066)
    cd.lens = 20.0

    def tick(scene, *_):
        if scene.name != sc.name:
            return
        f = scene.frame_current
        span = F_LIGHT[1] - F_LIGHT[0]
        left = 500 if f <= F_LIGHT[0] else max(0, int(math.ceil(500 * (1 - (f - F_LIGHT[0]) / span))))
        bpy.data.curves["countdown"].body = f"{left // 60:02d}:{left % 60:02d}"

    bpy.app.handlers.frame_change_pre.append(tick)
    return sc


# ----------------------------------------------------------------------------- soundtrack
BOOMS = [(F_BUT[0] + 2, 0.45, 2.5), (FLASH, 1.0, 6.0), (ENGULF - 20, 0.8, 4.0), (BLACK, 1.0, 5.0)]


def write_audio(path, sr=48000):
    import wave
    import numpy as np
    n = int(SECONDS * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(1)
    fr = lambda fnum: (fnum - 1) / FPS

    def env(points):
        xs, ys = zip(*points)
        return np.interp(t, xs, ys)

    def lowpass(x, cutoff):
        """Gentle 2nd-order low-pass done in the frequency domain."""
        X = np.fft.rfft(x)
        fq = np.fft.rfftfreq(len(x), 1.0 / sr)
        return np.fft.irfft(X / (1.0 + (fq / cutoff) ** 2), len(x))

    t_flash, t_black = fr(FLASH), fr(BLACK)
    # drone: 45 Hz + 45.35 Hz beating + octave, swells toward the flash; cut under the final boom
    drone_amp = env([(0, 0.0), (2.0, 0.16), (fr(F_LIGHT[0]), 0.2), (t_flash - 0.6, 0.34), (t_flash - 0.05, 0.0),
                     (t_flash + 0.3, 0.0), (t_flash + 2.5, 0.22), (fr(ENGULF), 0.32), (t_black, 0.32),
                     (t_black + 0.02, 0.0), (SECONDS, 0.0)])
    drone = (np.sin(2 * np.pi * 45.0 * t) + 0.8 * np.sin(2 * np.pi * 45.35 * t + 1.0)
             + 0.35 * np.sin(2 * np.pi * 90.2 * t) + 0.18 * np.sin(2 * np.pi * 135.5 * t))
    drone *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
    # filtered noise swells (rising wind before the flash, a roar for the blast)
    noise = rng.standard_normal(n)
    nl = lowpass(noise, 300.0)
    nl /= np.abs(nl).max() + 1e-9
    swell = env([(0, 0.0), (5.0, 0.06), (9.0, 0.02), (fr(F_NEUT[0]), 0.05), (fr(F_LIGHT[0]), 0.06),
                 (t_flash - 0.4, 0.55), (t_flash - 0.05, 0.0), (t_flash + 0.5, 0.0), (t_flash + 3.0, 0.15),
                 (fr(F_BLAST[0]), 0.2), (fr(ENGULF), 0.6), (t_black, 0.7), (t_black + 0.01, 0.0), (SECONDS, 0.0)])
    mix = drone_amp * drone * 0.6 + swell * nl
    # booms: pitched-down sine thump + low noise burst, long decay
    for fnum, amp, decay in BOOMS:
        t0 = fr(fnum)
        i0 = int(t0 * sr)
        m = n - i0
        tt = np.arange(m) / sr
        f_inst = 28.0 + 50.0 * np.exp(-tt * 6.0)
        ph = 2 * np.pi * np.cumsum(f_inst) / sr
        body = np.sin(ph) * np.exp(-tt * (5.0 / decay)) * np.minimum(1.0, tt / 0.004)
        rum = lowpass(rng.standard_normal(m), 120.0)
        rum /= np.abs(rum).max() + 1e-9
        rum *= np.exp(-tt * (3.0 / decay)) * np.minimum(1.0, tt / 0.02)
        hit = amp * (1.1 * body + 0.9 * rum)
        if fnum == BLACK:      # final boom fades fully to silence well before the end
            hit *= np.clip((SECONDS - 1.2 - (t0 + tt)) / 1.5, 0.0, 1.0)
        mix[i0:] += hit
    mix = np.tanh(mix * 1.1) * 0.9
    stereo = np.stack([mix, np.roll(mix, int(0.0007 * sr))], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32000).astype(np.int16)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"[supernova] wrote {path} ({SECONDS} s)", flush=True)


# ----------------------------------------------------------------------------- render
def render(sc):
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = FRAMES_ONLY or range(FIRST, min(LAST, END) + 1, EVERY)
    for f in frames:
        path = os.path.join(OUT_DIR, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue  # resumable
        # Headless: override the context scene so frame_set evaluates this scene's animation.
        with bpy.context.temp_override(scene=sc):
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[supernova] frame {f}/{END}", flush=True)


def main():
    if AUDIO:
        write_audio(AUDIO)
        if not RENDER:
            return
    sc = build()
    print(f"[supernova] built: {END} frames at {FPS} fps", flush=True)
    if RENDER:
        render(sc)


main()
