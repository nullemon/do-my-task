"""Four ominous space shorts (vertical 9:16), built and rendered entirely by this script.

  rogue   - a black rogue planet swallows the stars over a night ocean
  sunout  - "If the Sun vanished..." 8:20 countdown, then darkness
  saturn  - Saturn rises over the sea at the Moon's distance
  paledot - Earth recedes until it is gone

Run in Blender (Scripting tab) or headless:
  blender -b -P ominous.py -- --video rogue --render
  blender -b -P ominous.py -- --video all --render --res 1080 --samples 64
Frames go to //renders/ominous/<video>/; make_audio.py + ffmpeg (see README) add sound.
"""

import math
import os
import sys

import bpy

# ----------------------------------------------------------------------------- CONFIG
FPS = 24
RES_X = 540                 # 1080 for final
SAMPLES = 16                # 64-128 for final
THREADS = 0                 # 0 = all cores
VIDEO = "all"
RENDER = False
OUT_DIR = None              # default: <script dir>/renders/ominous

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--video" in argv:
    VIDEO = argv[argv.index("--video") + 1]
if "--render" in argv:
    RENDER = True
if "--res" in argv:
    RES_X = int(argv[argv.index("--res") + 1])
if "--samples" in argv:
    SAMPLES = int(argv[argv.index("--samples") + 1])
if "--threads" in argv:
    THREADS = int(argv[argv.index("--threads") + 1])
if "--out" in argv:
    OUT_DIR = argv[argv.index("--out") + 1]
FRAMES_ONLY = None
if "--frames" in argv:  # e.g. --frames 1,120,240 for test stills
    FRAMES_ONLY = [int(x) for x in argv[argv.index("--frames") + 1].split(",")]

RES_Y = RES_X * 16 // 9
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else bpy.path.abspath("//")
OUT_DIR = OUT_DIR or os.path.join(HERE, "renders", "ominous")


# ----------------------------------------------------------------------------- helpers
def new_scene(name, seconds):
    old = bpy.data.scenes.get(name)
    if old:
        for ob in list(old.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.scenes.remove(old)
    sc = bpy.data.scenes.new(name)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
    if THREADS:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = THREADS
    sc.render.resolution_x, sc.render.resolution_y = RES_X, RES_Y
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, int(seconds * FPS)
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    sc.cycles.max_bounces = 4
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


def mat_principled(name, color, rough=0.5, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
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


def star_world(sc, density=0.035, strength=6.0, sky=None, mix_key=None):
    """Procedural star field; optional daytime sky mixed in (mix_key = [(frame, 0..1)])."""
    nt = sc.world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 420.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = density
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    noise = nt.nodes.new("ShaderNodeTexNoise")  # vary star brightness
    noise.inputs["Scale"].default_value = 60
    nt.links.new(tc.outputs["Generated"], noise.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], mul.inputs[1])
    nt.links.new(noise.outputs["Fac"], mul.inputs[2])
    bg_stars = nt.nodes.new("ShaderNodeBackground")
    bg_stars.inputs["Strength"].default_value = strength
    nt.links.new(mul.outputs[0], bg_stars.inputs["Color"])
    if sky is None:
        nt.links.new(bg_stars.outputs[0], out.inputs[0])
        return None
    bg_sky = nt.nodes.new("ShaderNodeBackground")
    bg_sky.inputs["Color"].default_value = (*sky, 1)
    bg_sky.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(bg_stars.outputs[0], mix.inputs[1])
    nt.links.new(bg_sky.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    for f, v in mix_key or []:
        mix.inputs["Fac"].default_value = v
        mix.inputs["Fac"].keyframe_insert("default_value", frame=f)
    return mix


def camera(sc, loc, rot_deg, lens=24):
    cd = bpy.data.cameras.new(sc.name + "_cam")
    cd.lens = lens
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24
    cd.clip_start = 0.05
    cd.clip_end = 1e7
    cam = link(sc, bpy.data.objects.new(sc.name + "_cam", cd))
    cam.location = loc
    cam.rotation_euler = [math.radians(a) for a in rot_deg]
    sc.camera = cam
    return cam


def caption(sc, cam, text, f_in, f_out, y=-0.62, size=0.075, color=(1, 1, 1), strength=1.4, name=None):
    """Text fixed to the camera. y is -1..1 of the frame height. Visible f_in..f_out.
    Auto-fits: the text block is shrunk (and, if it would get too small, re-wrapped)
    so it is at most ~85% of the frame width."""
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

    def text_width():  # width of the text block at cu.size == 1
        cu.size = 1.0
        try:
            sc.view_layers[0].update()
            xs = [v[0] for v in ob.bound_box]
            w = max(xs) - min(xs)
            if w > 0:
                return w
        except Exception:
            pass
        return 0.5 * max(len(s) for s in cu.body.split("\n"))

    w1 = text_width()
    min_size = 0.65 * want
    if w1 * min_size > max_w:  # even shrunk it won't fit: re-wrap words into more lines
        per_char = w1 / max(len(s) for s in cu.body.split("\n"))
        limit = max(8, int(max_w / (per_char * min_size)))
        lines = []
        for para in text.split("\n"):  # keep author's breaks; split long ones evenly
            k = max(1, math.ceil(len(para) / limit))
            target = len(para) / k
            cur = ""
            for wd in para.split():
                if cur and len(cur) + 1 + len(wd) / 2 > target and len(lines) < 99:
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
    ob.visible_shadow = False
    for f, hide in ((1, True), (f_in, False), (f_out, True)):
        ob.hide_render = hide
        ob.keyframe_insert("hide_render", frame=f)
    return ob


def sea(sc, size=20000, color=(0.004, 0.006, 0.012), rough=0.12):
    ob = link(sc, plane("sea", size))
    m = mat_principled("sea_m", color, rough=rough)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 0.6
    n.inputs["Detail"].default_value = 8
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], nt.nodes["Principled BSDF"].inputs["Normal"])
    ob.data.materials.append(m)
    return ob


def key(ob, path, frames_values, index=-1):
    for f, v in frames_values:
        if index >= 0:
            getattr(ob, path)[index] = v
        else:
            setattr(ob, path, v)
        ob.keyframe_insert(path, frame=f, index=index)


def smooth_all(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    # 4.x keeps fcurves on the action; 5.x moves them into layered channelbags.
    curves = list(getattr(ad.action, "fcurves", []) or [])
    if not curves and hasattr(ad.action, "layers"):
        for layer in ad.action.layers:
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    curves.extend(bag.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "AUTO"


# ----------------------------------------------------------------------------- 1. rogue planet
def _star_layers(nt, tc, layers):
    """Point stars large enough (~1-2 px) to survive the denoiser. layers = [(scale, radius, gain)].
    Returns a color socket (additive star light)."""
    acc = None
    for scale, radius, gain in layers:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = scale
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        core = nt.nodes.new("ShaderNodeMapRange")
        core.inputs["From Min"].default_value = 0.0
        core.inputs["From Max"].default_value = radius
        core.inputs["To Min"].default_value = 1.0
        core.inputs["To Max"].default_value = 0.0
        nt.links.new(vor.outputs["Distance"], core.inputs["Value"])
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        nt.links.new(vor.outputs["Color"], bw.inputs["Color"])
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 5.0
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
    tint = nt.nodes.new("ShaderNodeMixRGB")  # slightly blue-white stars
    tint.blend_type = "MULTIPLY"
    tint.inputs["Fac"].default_value = 1.0
    tint.inputs[2].default_value = (0.85, 0.92, 1.0, 1)
    nt.links.new(acc, tint.inputs[1])
    return tint.outputs[0]


def _horizon_glow(nt, tc, color, height=0.18, power=3.0):
    """Color socket: a soft glow band hugging the horizon (world direction z ~ 0)."""
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.01
    mr.inputs["From Max"].default_value = height
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = power
    nt.links.new(mr.outputs["Result"], pw.inputs[0])
    col = nt.nodes.new("ShaderNodeMixRGB")
    col.blend_type = "MULTIPLY"
    col.inputs["Fac"].default_value = 1.0
    col.inputs[2].default_value = (*color, 1)
    nt.links.new(pw.outputs[0], col.inputs[1])
    return col.outputs[0]


def _add_rgb(nt, a, b):
    add = nt.nodes.new("ShaderNodeMixRGB")
    add.blend_type = "ADD"
    add.inputs["Fac"].default_value = 1.0
    nt.links.new(a, add.inputs[1])
    nt.links.new(b, add.inputs[2])
    return add.outputs[0]


def build_rogue():
    sc = new_scene("ominous_rogue", 11)
    sc.render.use_persistent_data = True
    end = sc.frame_end
    # world: visible stars + a faint moonlit band along the horizon
    nt = sc.world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    stars = _star_layers(nt, tc, [(110, 0.17, 140.0), (230, 0.2, 60.0)])
    glow = _horizon_glow(nt, tc, (0.010, 0.016, 0.030), height=0.16, power=3.0)
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(_add_rgb(nt, stars, glow), bg.inputs["Color"])
    nt.links.new(bg.outputs[0], wout.inputs[0])
    # glassy night sea that faintly mirrors the stars
    so = sea(sc, color=(0.002, 0.003, 0.006), rough=0.035)
    snt = so.data.materials[0].node_tree
    for n in snt.nodes:
        if n.type == "BUMP":
            n.inputs["Strength"].default_value = 0.06
        if n.type == "TEX_NOISE":
            n.inputs["Scale"].default_value = 0.35
    cam = camera(sc, (0, 0, 1.6), (100, 0, 0), lens=22)
    # The planet: a near-black disc with only a thin, faint dark-red rim.
    pl = link(sc, uv_sphere("rogue", 1.0, 128, 64))
    m = bpy.data.materials.new("rogue_m")
    m.use_nodes = True
    mnt = m.node_tree
    mnt.nodes.clear()
    out = mnt.nodes.new("ShaderNodeOutputMaterial")
    lw = mnt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.5
    ramp = mnt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.86, (0, 0, 0, 1)
    el[1].position, el[1].color = 1.0, (0.30, 0.025, 0.008, 1)
    el.new(0.96).color = (0.10, 0.008, 0.003, 1)
    nt_link = mnt.links.new
    nt_link(lw.outputs["Facing"], ramp.inputs["Fac"])
    em = mnt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 0.9
    nt_link(ramp.outputs["Color"], em.inputs["Color"])
    dark = mnt.nodes.new("ShaderNodeBsdfDiffuse")
    dark.inputs["Color"].default_value = (0.004, 0.004, 0.004, 1)
    addsh = mnt.nodes.new("ShaderNodeAddShader")
    nt_link(dark.outputs[0], addsh.inputs[0])
    nt_link(em.outputs[0], addsh.inputs[1])
    nt_link(addsh.outputs[0], out.inputs[0])
    pl.data.materials.append(m)
    pl.visible_shadow = False
    # Fixed size, approaching: angular size grows exponentially from a speck to most of the sky.
    R = 600.0
    pl.scale = (R, R, R)
    elev = math.radians(28)
    d0, d1 = 300000.0, 1350.0
    for f in range(1, end + 1, 3):
        t = (f - 1) / (end - 1)
        d = d0 * (d1 / d0) ** (t ** 1.15)
        pl.location = (0, d * math.cos(elev), 1.6 + d * math.sin(elev))
        pl.keyframe_insert("location", frame=f)
    pl.location = (0, d1 * math.cos(elev), 1.6 + d1 * math.sin(elev))
    pl.keyframe_insert("location", frame=end)
    # faint moonlight so the sea reads
    sun = bpy.data.lights.new("rogue_moonlight", "SUN")
    sun.energy = 0.06
    sun.color = (0.6, 0.7, 1.0)
    link(sc, bpy.data.objects.new("moonlight", sun)).rotation_euler = (math.radians(70), 0, math.radians(30))
    caption(sc, cam, "There are more rogue planets\nthan stars in our galaxy.", 12, 92)
    caption(sc, cam, "No sun. No light.\nThey drift in total darkness.", 100, 180)
    caption(sc, cam, "You would only notice one\nwhen the stars began to vanish.", 186, end + 1)
    return sc


# ----------------------------------------------------------------------------- 2. the sun goes out
def build_sunout():
    sc = new_scene("ominous_sunout", 13)
    sc.render.use_persistent_data = True
    end = sc.frame_end
    off = 200  # frame the Sun's light stops
    sun_el, sun_az = math.radians(8.5), math.radians(7)   # sun direction (az from +Y toward +X)
    sdir = (math.sin(sun_az) * math.cos(sun_el), math.cos(sun_az) * math.cos(sun_el), math.sin(sun_el))
    # world: golden-hour sky gradient + glow around the sun; cuts to black, then stars fade in
    nt = sc.world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    grad = nt.nodes.new("ShaderNodeMapRange")
    grad.inputs["From Min"].default_value = 0.0
    grad.inputs["From Max"].default_value = 0.45
    nt.links.new(sep.outputs["Z"], grad.inputs["Value"])
    sky = nt.nodes.new("ShaderNodeValToRGB")
    se = sky.color_ramp.elements
    se[0].position, se[0].color = 0.0, (1.0, 0.42, 0.12, 1)
    se[1].position, se[1].color = 1.0, (0.08, 0.16, 0.42, 1)
    se.new(0.12).color = (0.85, 0.45, 0.22, 1)
    se.new(0.4).color = (0.32, 0.30, 0.42, 1)
    nt.links.new(grad.outputs["Result"], sky.inputs["Fac"])
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = sdir
    nt.links.new(tc.outputs["Generated"], dot.inputs[0])
    gl = nt.nodes.new("ShaderNodeMapRange")
    gl.inputs["From Min"].default_value = 0.93
    gl.inputs["From Max"].default_value = 1.0
    nt.links.new(dot.outputs["Value"], gl.inputs["Value"])
    glp = nt.nodes.new("ShaderNodeMath")
    glp.operation = "POWER"
    glp.inputs[1].default_value = 3.0
    nt.links.new(gl.outputs["Result"], glp.inputs[0])
    glc = nt.nodes.new("ShaderNodeMixRGB")
    glc.blend_type = "MULTIPLY"
    glc.inputs["Fac"].default_value = 1.0
    glc.inputs[2].default_value = (4.0, 1.9, 0.6, 1)
    nt.links.new(glp.outputs[0], glc.inputs[1])
    bg_sky = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(_add_rgb(nt, sky.outputs["Color"], glc.outputs[0]), bg_sky.inputs["Color"])
    bg_sky.inputs["Strength"].default_value = 1.0
    bg_sky.inputs["Strength"].keyframe_insert("default_value", frame=off - 1)
    bg_sky.inputs["Strength"].default_value = 0.0
    bg_sky.inputs["Strength"].keyframe_insert("default_value", frame=off)
    stars = _star_layers(nt, tc, [(110, 0.17, 140.0), (230, 0.2, 60.0)])
    bg_st = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(stars, bg_st.inputs["Color"])
    for f, v in ((1, 0.0), (off + 6, 0.0), (off + 50, 1.0)):
        bg_st.inputs["Strength"].default_value = v
        bg_st.inputs["Strength"].keyframe_insert("default_value", frame=f)
    addw = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bg_sky.outputs[0], addw.inputs[0])
    nt.links.new(bg_st.outputs[0], addw.inputs[1])
    nt.links.new(addw.outputs[0], wout.inputs[0])
    if nt.animation_data and nt.animation_data.action:
        for fc in getattr(nt.animation_data.action, "fcurves", []) or []:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    # desert dunes: broad swells + sharp-crested ridges, grazing golden light
    import bmesh
    me = bpy.data.meshes.new("dunes")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=260, y_segments=260, size=1200)
    bm.to_mesh(me)
    bm.free()
    dunes = link(sc, bpy.data.objects.new("dunes", me))
    dunes.location = (0, 800, 0)
    t1 = bpy.data.textures.new("dune_swell", "CLOUDS")
    t1.noise_scale = 260
    d1 = dunes.modifiers.new("swell", "DISPLACE")
    d1.texture, d1.strength, d1.mid_level = t1, 40, 0.5
    t2 = bpy.data.textures.new("dune_ridge", "CLOUDS")
    t2.noise_type = "HARD_NOISE"
    t2.noise_scale = 90
    t2.noise_depth = 1
    d2 = dunes.modifiers.new("ridge", "DISPLACE")
    d2.texture, d2.strength, d2.mid_level = t2, -22, 0.5
    for p in me.polygons:
        p.use_smooth = True
    sand = mat_principled("sand", (0.78, 0.47, 0.22), rough=0.85)
    snt = sand.node_tree
    stc = snt.nodes.new("ShaderNodeTexCoord")
    wave = snt.nodes.new("ShaderNodeTexWave")  # wind ripples
    wave.inputs["Scale"].default_value = 0.35
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 2
    sb = snt.nodes.new("ShaderNodeBump")
    sb.inputs["Strength"].default_value = 0.25
    snt.links.new(stc.outputs["Object"], wave.inputs["Vector"])
    snt.links.new(wave.outputs["Fac"], sb.inputs["Height"])
    snt.links.new(sb.outputs["Normal"], snt.nodes["Principled BSDF"].inputs["Normal"])
    dunes.data.materials.append(sand)
    cam = camera(sc, (0, -300, 48), (87, 0, 0), lens=26)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.angle = math.radians(1.0)
    sun.color = (1.0, 0.72, 0.45)
    sun_ob = link(sc, bpy.data.objects.new("sun", sun))
    # light travels along -sdir
    sun_ob.rotation_euler = (math.pi / 2 - sun_el, 0, math.pi - sun_az)
    sun.energy = 5.0
    sun.keyframe_insert("energy", frame=off - 1)
    sun.energy = 0.0
    sun.keyframe_insert("energy", frame=off)
    # visible sun disc, low over the dunes
    disc = link(sc, uv_sphere("sun_disc", 1.0, 48, 24))
    disc.data.materials.append(mat_emit("sun_disc_m", (1.0, 0.78, 0.5), 25))
    disc.visible_shadow = False
    d = 50000
    disc.location = (d * sdir[0], -300 + d * sdir[1], 48 + d * sdir[2])
    disc.scale = [d * math.tan(math.radians(1.1))] * 3
    key(disc, "hide_render", [(1, False), (off, True)])
    # countdown text driven per frame
    cnt = caption(sc, cam, "08:20", 70, off, y=0.62, size=0.12, name="countdown")
    caption(sc, cam, "If the Sun vanished right now…", 8, 70)
    caption(sc, cam, "you'd still see it shining for\n8 minutes and 20 seconds.", 72, 150)
    caption(sc, cam, "Its last light is already\non the way.", 152, off)
    caption(sc, cam, "Then darkness.", off + 6, off + 50, y=0.0, size=0.09)
    caption(sc, cam, "Then the cold.", off + 56, end + 1, y=0.0, size=0.09)

    def tick(scene, *_):
        if scene.name != sc.name:
            return
        f = scene.frame_current
        if f < 70:
            left = 500
        else:  # 8:20 counted down over frames 70..off (time-lapse)
            left = max(0, round(500 * (1 - (f - 70) / (off - 70))))
        bpy.data.curves["countdown"].body = f"{left // 60:02d}:{left % 60:02d}"

    bpy.app.handlers.frame_change_pre.append(tick)
    return sc


# ----------------------------------------------------------------------------- 3. saturn rises
def build_saturn():
    sc = new_scene("ominous_saturn", 13)
    end = sc.frame_end
    star_world(sc, density=0.03, strength=4)
    sea(sc, color=(0.005, 0.008, 0.015))
    cam = camera(sc, (0, 0, 2.0), (90, 0, 0), lens=17)
    # Real proportions at the Moon's distance (scaled: 1 unit = 384.4 km).
    D = 1000.0
    R = D * math.tan(math.radians(17.8 / 2))
    ring_in, ring_out = R * 74658 / 60268, R * 136775 / 60268
    sat = link(sc, uv_sphere("saturn", R, 128, 64))
    sat.scale = (1, 1, 0.902)  # Saturn is visibly flattened
    m = mat_principled("saturn_m", (0.8, 0.7, 0.5), rough=0.8)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 3.0
    wave.inputs["Distortion"].default_value = 2.0
    wave.inputs["Detail"].default_value = 4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].color = (0.55, 0.42, 0.26, 1)
    el[1].color = (0.92, 0.84, 0.66, 1)
    el.new(0.5).color = (0.75, 0.6, 0.4, 1)
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    sat.data.materials.append(m)
    # rings: annulus mesh with radial banding + transparency
    import bmesh
    me = bpy.data.meshes.new("rings")
    bm = bmesh.new()
    n = 256
    vin = [bm.verts.new((ring_in * math.cos(2 * math.pi * i / n), ring_in * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
    vout = [bm.verts.new((ring_out * math.cos(2 * math.pi * i / n), ring_out * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
    for i in range(n):
        bm.faces.new((vin[i], vout[i], vout[(i + 1) % n], vin[(i + 1) % n]))
    bm.to_mesh(me)
    bm.free()
    rings = link(sc, bpy.data.objects.new("rings", me))
    rm = bpy.data.materials.new("rings_m")
    rm.use_nodes = True
    rnt = rm.node_tree
    rnt.nodes.clear()
    out = rnt.nodes.new("ShaderNodeOutputMaterial")
    tc2 = rnt.nodes.new("ShaderNodeTexCoord")
    length = rnt.nodes.new("ShaderNodeVectorMath")
    length.operation = "LENGTH"
    rng = rnt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = ring_in
    rng.inputs["From Max"].default_value = ring_out
    alpha = rnt.nodes.new("ShaderNodeValToRGB")
    a = alpha.color_ramp.elements
    a[0].position, a[0].color = 0.0, (0.15, 0.15, 0.15, 1)    # faint C ring
    a[1].position, a[1].color = 1.0, (0.0, 0.0, 0.0, 1)
    for pos, v in ((0.2, 0.25), (0.28, 0.9), (0.55, 0.95), (0.58, 0.0), (0.62, 0.0), (0.66, 0.75), (0.9, 0.6), (0.97, 0.0)):
        e = a.new(pos)
        e.color = (v, v, v, 1)
    diff = rnt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (0.85, 0.78, 0.65, 1)
    tr = rnt.nodes.new("ShaderNodeBsdfTransparent")
    mix = rnt.nodes.new("ShaderNodeMixShader")
    rnt.links.new(tc2.outputs["Object"], length.inputs[0])
    rnt.links.new(length.outputs["Value"], rng.inputs["Value"])
    rnt.links.new(rng.outputs["Result"], alpha.inputs["Fac"])
    rnt.links.new(alpha.outputs["Color"], mix.inputs["Fac"])
    rnt.links.new(tr.outputs[0], mix.inputs[1])
    rnt.links.new(diff.outputs[0], mix.inputs[2])
    rnt.links.new(mix.outputs[0], out.inputs[0])
    rings.data.materials.append(rm)
    rings.parent = sat
    rings.scale = (1, 1, 1 / 0.902)
    sat.rotation_euler = (math.radians(70), math.radians(18), 0)
    # rise from below the horizon to ~18° up
    for f, elev in ((1, -12), (int(end * 0.55), 6), (end, 18)):
        e = math.radians(elev)
        sat.location = (D * 0.15, D * math.cos(e), 2.0 + D * math.sin(e))
        sat.keyframe_insert("location", frame=f)
    smooth_all(sat)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    sun.color = (1.0, 0.95, 0.88)
    link(sc, bpy.data.objects.new("sun", sun)).rotation_euler = (math.radians(95), 0, math.radians(-60))
    # slow camera tilt up as it rises
    key(cam, "rotation_euler", [(1, math.radians(88)), (end, math.radians(96))], index=0)
    caption(sc, cam, "What if Saturn replaced the Moon?", 10, 90)
    caption(sc, cam, "It would fill a third of the sky.\nIts rings, nearly half.", 96, 180)
    caption(sc, cam, "And at first…\nyou wouldn't feel a thing.", 186, end + 1)
    return sc


# ----------------------------------------------------------------------------- 4. pale dot
def build_paledot():
    sc = new_scene("ominous_paledot", 13)
    end = sc.frame_end
    star_world(sc, density=0.03, strength=6)
    earth = link(sc, uv_sphere("earth", 1.0, 160, 80))
    m = mat_principled("earth_m", (0.02, 0.08, 0.25), rough=0.6)
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    land = nt.nodes.new("ShaderNodeTexNoise")
    land.inputs["Scale"].default_value = 1.6
    land.inputs["Detail"].default_value = 10
    lr = nt.nodes.new("ShaderNodeValToRGB")
    e = lr.color_ramp.elements
    e[0].position, e[0].color = 0.53, (0.015, 0.06, 0.2, 1)
    e[1].position, e[1].color = 0.56, (0.16, 0.22, 0.08, 1)
    e.new(0.66).color = (0.42, 0.33, 0.2, 1)
    cloud = nt.nodes.new("ShaderNodeTexNoise")
    cloud.inputs["Scale"].default_value = 4.0
    cloud.inputs["Detail"].default_value = 12
    cr = nt.nodes.new("ShaderNodeValToRGB")
    c = cr.color_ramp.elements
    c[0].position, c[0].color = 0.52, (0, 0, 0, 1)
    c[1].position, c[1].color = 0.7, (1, 1, 1, 1)
    mixc = nt.nodes.new("ShaderNodeMixRGB")
    mixc.inputs[2].default_value = (0.95, 0.95, 0.95, 1)
    for a_, b_ in ((tc.outputs["Object"], land.inputs["Vector"]), (land.outputs["Fac"], lr.inputs["Fac"]),
                   (tc.outputs["Object"], cloud.inputs["Vector"]), (cloud.outputs["Fac"], cr.inputs["Fac"]),
                   (cr.outputs["Color"], mixc.inputs["Fac"]), (lr.outputs["Color"], mixc.inputs[1]),
                   (mixc.outputs[0], nt.nodes["Principled BSDF"].inputs["Base Color"])):
        nt.links.new(a_, b_)
    earth.data.materials.append(m)
    earth.rotation_euler = (math.radians(23.4), 0, 0)
    key(earth, "rotation_euler", [(1, 0.0), (end, math.radians(40))], index=2)
    atm = link(sc, uv_sphere("atmosphere", 1.025, 128, 64))
    am = bpy.data.materials.new("atm_m")
    am.use_nodes = True
    ant = am.node_tree
    ant.nodes.clear()
    out = ant.nodes.new("ShaderNodeOutputMaterial")
    lw = ant.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.25
    em = ant.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.25, 0.5, 1.0, 1)
    em.inputs["Strength"].default_value = 1.2
    tr = ant.nodes.new("ShaderNodeBsdfTransparent")
    mix = ant.nodes.new("ShaderNodeMixShader")
    ant.links.new(lw.outputs["Facing"], mix.inputs["Fac"])
    ant.links.new(tr.outputs[0], mix.inputs[1])
    ant.links.new(em.outputs[0], mix.inputs[2])
    ant.links.new(mix.outputs[0], out.inputs[0])
    atm.data.materials.append(am)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 4.0
    link(sc, bpy.data.objects.new("sun", sun)).rotation_euler = (math.radians(80), 0, math.radians(-50))
    cam = camera(sc, (0, -3.2, 0), (90, 0, 0), lens=35)
    # exponential pull-back: 3.2 Earth radii -> 60,000 radii
    steps = 24
    for i in range(steps + 1):
        f = 1 + round((end - 1) * i / steps)
        t = i / steps
        ease = t * t * (3 - 2 * t) * 0.35 + t * 0.65
        cam.location = (0, -3.2 * (60000 / 3.2) ** ease, 0)
        cam.keyframe_insert("location", frame=f)
    caption(sc, cam, "This is everything\nyou have ever known.", 10, 90)
    caption(sc, cam, "Every person who ever lived.\nEvery war. Every love.", 96, 176)
    caption(sc, cam, "From far enough away…", 182, 250)
    caption(sc, cam, "it's gone.", 256, end + 1, y=0.0, size=0.09)
    return sc


BUILDERS = {"rogue": build_rogue, "sunout": build_sunout, "saturn": build_saturn, "paledot": build_paledot}


def render(sc, name):
    out = os.path.join(OUT_DIR, name)
    os.makedirs(out, exist_ok=True)
    if getattr(bpy.context, "window", None):
        bpy.context.window.scene = sc
    frames = FRAMES_ONLY or range(sc.frame_start, sc.frame_end + 1)
    for f in frames:
        path = os.path.join(out, f"frame_{f:04d}.png")
        if FRAMES_ONLY is None and os.path.exists(path):
            continue  # resumable
        # Headless bpy has no window, so sc is not the context scene: frame_set() then
        # never evaluates its animation and the render uses stale transforms (identity
        # camera sitting in the sea plane -> black frames, captions stuck hidden).
        # Overriding the context scene makes frame_set/render evaluate sc properly.
        with bpy.context.temp_override(scene=sc):
            sc.frame_set(f)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[ominous] {name} {f}/{sc.frame_end}", flush=True)


def main():
    names = list(BUILDERS) if VIDEO == "all" else [VIDEO]
    for name in names:
        sc = BUILDERS[name]()
        print(f"[ominous] built {name}: {sc.frame_end} frames at {FPS} fps", flush=True)
        if RENDER:
            render(sc, name)


main()
