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
    """Point stars large enough (~1-2 px) to survive the denoiser. layers = [(scale, radius, gain, power)].
    Returns a color socket (additive star light)."""
    acc = None
    for scale, radius, gain, power in layers:
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
    stars = _star_layers(nt, tc, [(110, 0.17, 300.0, 20.0), (230, 0.2, 90.0, 22.0)])
    glow = _horizon_glow(nt, tc, (0.010, 0.016, 0.030), height=0.16, power=3.0)
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(_add_rgb(nt, stars, glow), bg.inputs["Color"])
    nt.links.new(bg.outputs[0], wout.inputs[0])
    # glassy night sea that faintly mirrors the stars
    so = sea(sc, color=(0.002, 0.003, 0.006), rough=0.035)
    snt = so.data.materials[0].node_tree
    try:
        snt.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.22
    except KeyError:
        pass
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
    se[0].position, se[0].color = 0.0, (0.9, 0.28, 0.05, 1)
    se[1].position, se[1].color = 1.0, (0.03, 0.07, 0.22, 1)
    se.new(0.10).color = (0.6, 0.22, 0.08, 1)
    se.new(0.4).color = (0.16, 0.13, 0.22, 1)
    nt.links.new(grad.outputs["Result"], sky.inputs["Fac"])
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = sdir
    nt.links.new(tc.outputs["Generated"], dot.inputs[0])
    gl = nt.nodes.new("ShaderNodeMapRange")
    gl.inputs["From Min"].default_value = 0.96
    gl.inputs["From Max"].default_value = 1.0
    nt.links.new(dot.outputs["Value"], gl.inputs["Value"])
    glp = nt.nodes.new("ShaderNodeMath")
    glp.operation = "POWER"
    glp.inputs[1].default_value = 3.0
    nt.links.new(gl.outputs["Result"], glp.inputs[0])
    glc = nt.nodes.new("ShaderNodeMixRGB")
    glc.blend_type = "MULTIPLY"
    glc.inputs["Fac"].default_value = 1.0
    glc.inputs[2].default_value = (3.0, 1.1, 0.25, 1)
    nt.links.new(glp.outputs[0], glc.inputs[1])
    bg_sky = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(_add_rgb(nt, sky.outputs["Color"], glc.outputs[0]), bg_sky.inputs["Color"])
    bg_sky.inputs["Strength"].default_value = 1.0
    bg_sky.inputs["Strength"].keyframe_insert("default_value", frame=off - 1)
    bg_sky.inputs["Strength"].default_value = 0.0
    bg_sky.inputs["Strength"].keyframe_insert("default_value", frame=off)
    stars = _star_layers(nt, tc, [(110, 0.17, 300.0, 20.0), (230, 0.2, 90.0, 22.0)])
    lp = nt.nodes.new("ShaderNodeLightPath")  # stars seen, but they don't light the sand
    cam_only = nt.nodes.new("ShaderNodeMixRGB")
    cam_only.blend_type = "MIX"
    cam_only.inputs[1].default_value = (0.0, 0.0, 0.0, 1)
    nt.links.new(stars, cam_only.inputs[2])
    nt.links.new(lp.outputs["Is Camera Ray"], cam_only.inputs["Fac"])
    bg_st = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(cam_only.outputs[0], bg_st.inputs["Color"])
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
    bmesh.ops.create_grid(bm, x_segments=400, y_segments=400, size=1200)
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
    try:
        dunes.shadow_terminator_geometry_offset = 0.6
        dunes.shadow_terminator_shading_offset = 0.15
    except AttributeError:
        pass
    sand = mat_principled("sand", (0.8, 0.38, 0.13), rough=0.85)
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
    sun.color = (1.0, 0.6, 0.3)
    sun_ob = link(sc, bpy.data.objects.new("sun", sun))
    # light travels along -sdir
    sun_ob.rotation_euler = (math.pi / 2 - sun_el, 0, math.pi - sun_az)
    sun.energy = 6.0
    sun.keyframe_insert("energy", frame=off - 1)
    sun.energy = 0.0
    sun.keyframe_insert("energy", frame=off)
    # visible sun disc, low over the dunes
    disc = link(sc, uv_sphere("sun_disc", 1.0, 48, 24))
    disc.data.materials.append(mat_emit("sun_disc_m", (1.0, 0.62, 0.3), 14))
    disc.visible_shadow = False
    d = 50000
    disc.location = (d * sdir[0], -300 + d * sdir[1], 48 + d * sdir[2])
    disc.scale = [d * math.tan(math.radians(1.1))] * 3
    key(disc, "hide_render", [(1, False), (off, True)])
    # countdown text driven per frame
    cnt = caption(sc, cam, "08:20", 70, off, y=0.62, size=0.12, color=(1, 0.97, 0.92), strength=5.0,
                  name="countdown")
    caption(sc, cam, "If the Sun vanished right now…", 8, 70, strength=3.0)
    caption(sc, cam, "you'd still see it shining for\n8 minutes and 20 seconds.", 72, 150, strength=3.0)
    caption(sc, cam, "Its last light is already\non the way.", 152, off, strength=3.0)
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
def _sky_world(sc, stars, sky_stops=None, star_fade=None):
    """World for saturn/paledot. stars = [(voronoi scale, core radius, gain)] - point stars ~1-2 px so
    they survive the denoiser. sky_stops = [(z 0..1, rgb)] vertical gradient (dusk sky).
    star_fade = (z0, z1): stars fade in between those heights (haze near the horizon)."""
    nt = sc.world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    acc = None
    for scale, radius, gain in stars:
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
        pw.inputs[1].default_value = 6.0
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
    if star_fade:
        fade = nt.nodes.new("ShaderNodeMapRange")
        fade.inputs["From Min"].default_value, fade.inputs["From Max"].default_value = star_fade
        nt.links.new(sep.outputs["Z"], fade.inputs["Value"])
        mf = nt.nodes.new("ShaderNodeMath")
        mf.operation = "MULTIPLY"
        nt.links.new(acc, mf.inputs[0])
        nt.links.new(fade.outputs["Result"], mf.inputs[1])
        acc = mf.outputs[0]
    tint = nt.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs["Fac"].default_value = 1.0
    tint.inputs[2].default_value = (0.88, 0.93, 1.0, 1)
    nt.links.new(acc, tint.inputs[1])
    col = tint.outputs[0]
    if sky_stops:
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "EASE"
        el = ramp.color_ramp.elements
        el[0].position, el[0].color = sky_stops[0][0], (*sky_stops[0][1], 1)
        el[1].position, el[1].color = sky_stops[-1][0], (*sky_stops[-1][1], 1)
        for pos, c in sky_stops[1:-1]:
            el.new(pos).color = (*c, 1)
        nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
        add = nt.nodes.new("ShaderNodeMixRGB")
        add.blend_type = "ADD"
        add.inputs["Fac"].default_value = 1.0
        nt.links.new(col, add.inputs[1])
        nt.links.new(ramp.outputs["Color"], add.inputs[2])
        col = add.outputs[0]
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(col, bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])


def _key_every_frame(ob, path, index, fn, f0, f1):
    """Sample fn(frame) onto every frame (exact, no Bezier overshoot)."""
    for f in range(f0, f1 + 1):
        v = fn(f)
        if index >= 0:
            getattr(ob, path)[index] = v
        else:
            setattr(ob, path, v)
        ob.keyframe_insert(path, frame=f, index=index)


def _smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def _sun(sc, name, to_sun, energy, color=(1, 1, 1), angle_deg=0.5):
    from mathutils import Vector
    li = bpy.data.lights.new(name, "SUN")
    li.energy = energy
    li.color = color
    li.angle = math.radians(angle_deg)
    ob = link(sc, bpy.data.objects.new(name, li))
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = (-Vector(to_sun).normalized()).to_track_quat("-Z", "Y")
    return ob


def _look(sc):
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        try:
            sc.view_settings.look = "Medium High Contrast"
        except TypeError:
            pass


SATURN_CLEAR = 192   # frame Saturn's disc fully clears the horizon (soundtrack boom)


def build_saturn():
    import bmesh
    sc = new_scene("ominous_saturn", 13)
    sc.render.use_persistent_data = True
    _look(sc)
    end = sc.frame_end
    _sky_world(sc, stars=[(140, 0.14, 1.2), (60, 0.09, 2.5)],
               sky_stops=[(0.0, (0.11, 0.07, 0.10)), (0.05, (0.05, 0.045, 0.08)),
                          (0.18, (0.014, 0.018, 0.045)), (0.55, (0.003, 0.005, 0.014))],
               star_fade=(0.04, 0.35))
    # --- calm dusk sea: dark, glossy, slow anisotropic swell (animated 4D noise), casts no shadow
    sea_ob = sea(sc, color=(0.002, 0.003, 0.006), rough=0.035)
    sea_ob.visible_shadow = False
    snt = sea_ob.data.materials[0].node_tree
    for nd in list(snt.nodes):
        if nd.type in ("TEX_NOISE", "BUMP", "TEX_COORD"):
            snt.nodes.remove(nd)
    bsdf = snt.nodes["Principled BSDF"]
    bsdf.inputs["IOR"].default_value = 1.33
    tc = snt.nodes.new("ShaderNodeTexCoord")
    mp = snt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.18, 0.55, 1.0)  # long crests running across the view
    snt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = snt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 1.0
    nz.inputs["Detail"].default_value = 6
    nz.inputs["Roughness"].default_value = 0.55
    snt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nz.inputs["W"].default_value = 0.0
    nz.inputs["W"].keyframe_insert("default_value", frame=1)
    nz.inputs["W"].default_value = 1.6
    nz.inputs["W"].keyframe_insert("default_value", frame=end)
    for fc in (snt.animation_data.action.fcurves if hasattr(snt.animation_data.action, "fcurves") else []):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    bump = snt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.25
    snt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    snt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    H = 2.0  # eye height above the water
    cam = camera(sc, (0, 0, H), (90, 0, 0), lens=14.5)   # ~50° wide: rings (39°) just fit
    cam.data.clip_start = 0.5
    cam.data.clip_end = 5e4

    # --- Saturn at the Moon's distance. Scale: D = 1000 units; real angular sizes.
    D = 1000.0
    R = D * math.tan(math.radians(17.8 / 2))           # equatorial radius -> 17.8° disc
    ring_in, ring_out = R * 74658 / 60268, R * 136775 / 60268   # C ring inner .. A ring outer (~39°)
    sat = link(sc, uv_sphere("saturn", R, 192, 96))
    sat.scale = (1, 1, 0.902)                          # oblate
    m = mat_principled("saturn_m", (0.8, 0.7, 0.5), rough=0.92)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    for nm in ("Specular IOR Level", "Specular"):
        if nm in b.inputs:
            b.inputs[nm].default_value = 0.15
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sepz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sepz.inputs[0])
    lat = nt.nodes.new("ShaderNodeMapRange")            # z/R -> 0..1 (south..north)
    lat.inputs["From Min"].default_value, lat.inputs["From Max"].default_value = -R, R
    nt.links.new(sepz.outputs["Z"], lat.inputs["Value"])
    turb = nt.nodes.new("ShaderNodeTexNoise")           # zonal turbulence: wobble the band edges
    turb.inputs["Scale"].default_value = 3.0 / R
    turb.inputs["Detail"].default_value = 8
    turb.inputs["Distortion"].default_value = 1.5
    nt.links.new(tc.outputs["Object"], turb.inputs["Vector"])
    tw = nt.nodes.new("ShaderNodeMapRange")
    tw.inputs["To Min"].default_value, tw.inputs["To Max"].default_value = -0.018, 0.018
    nt.links.new(turb.outputs["Fac"], tw.inputs["Value"])
    lsum = nt.nodes.new("ShaderNodeMath")
    lsum.operation = "ADD"
    nt.links.new(lat.outputs["Result"], lsum.inputs[0])
    nt.links.new(tw.outputs["Result"], lsum.inputs[1])
    bands = nt.nodes.new("ShaderNodeValToRGB")
    bands.color_ramp.interpolation = "EASE"
    stops = [(0.0, (0.30, 0.34, 0.38)), (0.07, (0.42, 0.40, 0.36)), (0.13, (0.58, 0.47, 0.33)),
             (0.20, (0.80, 0.68, 0.49)), (0.27, (0.64, 0.51, 0.35)), (0.34, (0.86, 0.76, 0.58)),
             (0.41, (0.69, 0.54, 0.35)), (0.46, (0.90, 0.80, 0.62)), (0.50, (0.95, 0.88, 0.70)),
             (0.54, (0.88, 0.76, 0.56)), (0.585, (0.66, 0.52, 0.34)), (0.64, (0.87, 0.77, 0.58)),
             (0.70, (0.62, 0.50, 0.35)), (0.77, (0.80, 0.70, 0.52)), (0.85, (0.55, 0.48, 0.38)),
             (0.93, (0.42, 0.43, 0.44)), (1.0, (0.32, 0.36, 0.42))]
    el = bands.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
    for pos, c in stops[1:-1]:
        el.new(pos).color = (*c, 1)
    nt.links.new(lsum.outputs[0], bands.inputs["Fac"])
    fine = nt.nodes.new("ShaderNodeTexWave")            # thin belts on top of the broad zones
    fine.wave_type = "BANDS"
    fine.bands_direction = "Z"
    fine.inputs["Scale"].default_value = 9.0 / R
    fine.inputs["Distortion"].default_value = 1.2
    fine.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], fine.inputs["Vector"])
    fr = nt.nodes.new("ShaderNodeMapRange")
    fr.inputs["To Min"].default_value, fr.inputs["To Max"].default_value = 0.88, 1.0
    nt.links.new(fine.outputs["Fac"], fr.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs["Fac"].default_value = 1.0
    nt.links.new(bands.outputs["Color"], mul.inputs[1])
    nt.links.new(fr.outputs["Result"], mul.inputs[2])
    nt.links.new(mul.outputs[0], b.inputs["Base Color"])
    sat.data.materials.append(m)

    # --- rings: annulus, radial opacity profile (C, B, Cassini division, A, Encke gap) + ringlets
    me = bpy.data.meshes.new("rings")
    bm = bmesh.new()
    n = 384
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
    rnt.links.new(tc2.outputs["Object"], length.inputs[0])
    rng = rnt.nodes.new("ShaderNodeMapRange")
    rng.inputs["From Min"].default_value = ring_in
    rng.inputs["From Max"].default_value = ring_out
    rnt.links.new(length.outputs["Value"], rng.inputs["Value"])
    op = rnt.nodes.new("ShaderNodeValToRGB")             # opacity vs radius (0 = inner C edge)
    a = op.color_ramp.elements
    a[0].position, a[0].color = 0.0, (0.10, 0.10, 0.10, 1)
    a[1].position, a[1].color = 1.0, (0.0, 0.0, 0.0, 1)
    for pos, v in ((0.25, 0.22), (0.278, 0.55), (0.30, 0.85), (0.45, 0.97), (0.60, 0.95), (0.68, 0.85),
                   (0.69, 0.06), (0.745, 0.08), (0.755, 0.72), (0.93, 0.62), (0.935, 0.05), (0.945, 0.05),
                   (0.95, 0.6), (0.985, 0.55), (0.995, 0.0)):
        e = a.new(pos)
        e.color = (v, v, v, 1)
    rnt.links.new(rng.outputs["Result"], op.inputs["Fac"])
    col = rnt.nodes.new("ShaderNodeValToRGB")            # tint vs radius: grey C, creamy B, beige A
    c = col.color_ramp.elements
    c[0].position, c[0].color = 0.0, (0.45, 0.43, 0.40, 1)
    c[1].position, c[1].color = 1.0, (0.70, 0.64, 0.55, 1)
    c.new(0.30).color = (0.80, 0.72, 0.58, 1)
    c.new(0.55).color = (0.92, 0.84, 0.70, 1)
    c.new(0.76).color = (0.78, 0.71, 0.60, 1)
    rnt.links.new(rng.outputs["Result"], col.inputs["Fac"])
    rl = rnt.nodes.new("ShaderNodeTexNoise")             # ringlets: 1D noise along radius
    rl.noise_dimensions = "1D"
    rl.inputs["Scale"].default_value = 1.0
    rl.inputs["Detail"].default_value = 6
    rlm = rnt.nodes.new("ShaderNodeMath")
    rlm.operation = "MULTIPLY"
    rlm.inputs[1].default_value = 140.0
    rnt.links.new(rng.outputs["Result"], rlm.inputs[0])
    rnt.links.new(rlm.outputs[0], rl.inputs["W"])
    rlr = rnt.nodes.new("ShaderNodeMapRange")
    rlr.inputs["From Min"].default_value, rlr.inputs["From Max"].default_value = 0.3, 0.7
    rlr.inputs["To Min"].default_value, rlr.inputs["To Max"].default_value = 0.55, 1.0
    rnt.links.new(rl.outputs["Fac"], rlr.inputs["Value"])
    opm = rnt.nodes.new("ShaderNodeMath")
    opm.operation = "MULTIPLY"
    rnt.links.new(op.outputs["Color"], opm.inputs[0])
    rnt.links.new(rlr.outputs["Result"], opm.inputs[1])
    diff = rnt.nodes.new("ShaderNodeBsdfDiffuse")
    trl = rnt.nodes.new("ShaderNodeBsdfTranslucent")
    rnt.links.new(col.outputs["Color"], diff.inputs["Color"])
    rnt.links.new(col.outputs["Color"], trl.inputs["Color"])
    dt = rnt.nodes.new("ShaderNodeMixShader")
    dt.inputs["Fac"].default_value = 0.3
    rnt.links.new(diff.outputs[0], dt.inputs[1])
    rnt.links.new(trl.outputs[0], dt.inputs[2])
    tr = rnt.nodes.new("ShaderNodeBsdfTransparent")
    mix = rnt.nodes.new("ShaderNodeMixShader")
    rnt.links.new(opm.outputs[0], mix.inputs["Fac"])
    rnt.links.new(tr.outputs[0], mix.inputs[1])
    rnt.links.new(dt.outputs[0], mix.inputs[2])
    rnt.links.new(mix.outputs[0], out.inputs[0])
    rings.data.materials.append(rm)
    rings.parent = sat
    rings.scale = (1, 1, 1 / 0.902)
    # ring plane opened ~24° toward us (we see its sunlit north face), rolled a little
    sat.rotation_euler = (math.radians(24), math.radians(-14), 0)
    key(sat, "rotation_euler", [(1, 0.0), (end, math.radians(4))], index=2)  # slow spin: bands drift

    # --- rise: centre elevation from below the horizon to clear by SATURN_CLEAR, then keeps easing up
    from mathutils import Euler, Vector
    rot = Euler(sat.rotation_euler).to_matrix()
    lowest = min([-R * 0.91] + [(rot @ Vector((ring_out * 0.99 * math.cos(t), ring_out * 0.99 * math.sin(t), 0))).z
                                for t in [2 * math.pi * k / 360 for k in range(360)]])
    clear_elev = math.degrees(math.atan(-lowest / D)) + 0.4    # planet AND rings just clear the horizon

    def elev(f):
        if f <= SATURN_CLEAR:
            t = (f - 1) / (SATURN_CLEAR - 1)
            t = t * t * (3 - 2 * t) * 0.35 + t * 0.65        # steady, slightly eased
            return -11.0 + (clear_elev + 11.0) * t
        u = (f - SATURN_CLEAR) / (end - SATURN_CLEAR)
        slope = (clear_elev + 11.0) / (SATURN_CLEAR - 1) * 1.0  # keep velocity, then ease out
        return clear_elev + slope * (end - SATURN_CLEAR) * (u - 0.45 * u * u)

    az = math.radians(-2.0)

    def loc(f, i):
        e = math.radians(elev(f))
        return (D * math.sin(az) * math.cos(e), D * math.cos(az) * math.cos(e), H + D * math.sin(e))[i]

    for i in range(3):
        _key_every_frame(sat, "location", i, lambda f, i=i: loc(f, i), 1, end)
    # dusk: the Sun has just set behind us, low on the left -> gibbous Saturn, terminator on the right
    _sun(sc, "sun", (-0.86, -0.50, 0.07), 3.4, color=(1.0, 0.86, 0.70))
    # --- camera: slow tilt-up following the rise, tiny drift
    _key_every_frame(cam, "rotation_euler", 0,
                     lambda f: math.radians(91.5 + 9.5 * _smoothstep(1, end + 30, f)), 1, end)
    _key_every_frame(cam, "rotation_euler", 2,
                     lambda f: math.radians(0.6 * math.sin(f / end * math.pi)), 1, end)
    caption(sc, cam, "What if Saturn replaced the Moon?", 10, 95)
    caption(sc, cam, "It would fill a third of the sky.\nIts rings, nearly half.", 101, 188)
    caption(sc, cam, "And at first…\nyou wouldn't feel a thing.", 200, end + 1)
    return sc


# ----------------------------------------------------------------------------- 4. pale dot
PALEDOT_GONE = 256   # "it's gone." (soundtrack boom)


def build_paledot():
    import numpy as np
    sc = new_scene("ominous_paledot", 13)
    sc.render.use_persistent_data = True
    _look(sc)
    end = sc.frame_end
    _sky_world(sc, stars=[(150, 0.13, 1.6), (55, 0.08, 3.0)])
    to_sun = (-0.92, -0.22, 0.30)
    _sun(sc, "sun", to_sun, 4.5, color=(1.0, 0.97, 0.92))
    sun_v = np.array(to_sun) / np.linalg.norm(to_sun)

    def vec_const(nt, v):
        cv = nt.nodes.new("ShaderNodeCombineXYZ")
        cv.inputs[0].default_value, cv.inputs[1].default_value, cv.inputs[2].default_value = (float(x) for x in v)
        return cv.outputs[0]

    def sun_dot(nt, lo, hi):
        """0..1 mask: map_range(dot(world normal, sun dir), lo, hi)."""
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(geo.outputs["Normal"], dot.inputs[0])
        nt.links.new(vec_const(nt, sun_v), dot.inputs[1])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = lo, hi
        nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
        return mr.outputs["Result"]

    # --- Earth surface
    earth = link(sc, uv_sphere("earth", 1.0, 192, 96))
    m = mat_principled("earth_m", (0.02, 0.08, 0.25), rough=0.6)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    land = nt.nodes.new("ShaderNodeTexNoise")
    land.inputs["Scale"].default_value = 1.15
    land.inputs["Detail"].default_value = 14
    land.inputs["Roughness"].default_value = 0.62
    land.inputs["Distortion"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], land.inputs["Vector"])
    lc = nt.nodes.new("ShaderNodeValToRGB")              # ocean depth -> coast -> lowland -> desert -> highland
    e = lc.color_ramp.elements
    e[0].position, e[0].color = 0.35, (0.002, 0.008, 0.035, 1)
    e[1].position, e[1].color = 0.80, (0.42, 0.38, 0.32, 1)
    for pos, col in ((0.50, (0.004, 0.018, 0.06)), (0.535, (0.012, 0.06, 0.11)), (0.545, (0.09, 0.13, 0.05)),
                     (0.58, (0.07, 0.12, 0.04)), (0.62, (0.20, 0.18, 0.09)), (0.66, (0.52, 0.38, 0.21)),
                     (0.72, (0.36, 0.28, 0.18))):
        e.new(pos).color = (*col, 1)
    nt.links.new(land.outputs["Fac"], lc.inputs["Fac"])
    # ice caps: by latitude (object z), wobbled
    sepz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sepz.inputs[0])
    absz = nt.nodes.new("ShaderNodeMath")
    absz.operation = "ABSOLUTE"
    nt.links.new(sepz.outputs["Z"], absz.inputs[0])
    wob = nt.nodes.new("ShaderNodeMath")
    wob.operation = "MULTIPLY_ADD"
    wob.inputs[1].default_value = 0.12
    nt.links.new(land.outputs["Fac"], wob.inputs[0])
    nt.links.new(absz.outputs[0], wob.inputs[2])
    ice = nt.nodes.new("ShaderNodeMapRange")
    ice.inputs["From Min"].default_value, ice.inputs["From Max"].default_value = 0.93, 0.97
    nt.links.new(wob.outputs[0], ice.inputs["Value"])
    icem = nt.nodes.new("ShaderNodeMixRGB")
    icem.inputs[2].default_value = (0.75, 0.80, 0.86, 1)
    nt.links.new(ice.outputs["Result"], icem.inputs["Fac"])
    nt.links.new(lc.outputs["Color"], icem.inputs[1])
    nt.links.new(icem.outputs[0], b.inputs["Base Color"])
    # glossy ocean (sun glint), matte land
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value, rr.inputs["From Max"].default_value = 0.535, 0.545
    rr.inputs["To Min"].default_value, rr.inputs["To Max"].default_value = 0.32, 0.92
    nt.links.new(land.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    # city lights on the night side only
    city = nt.nodes.new("ShaderNodeTexNoise")
    city.inputs["Scale"].default_value = 60.0
    city.inputs["Detail"].default_value = 4
    nt.links.new(tc.outputs["Object"], city.inputs["Vector"])
    cm = nt.nodes.new("ShaderNodeMapRange")
    cm.inputs["From Min"].default_value, cm.inputs["From Max"].default_value = 0.58, 0.72
    nt.links.new(city.outputs["Fac"], cm.inputs["Value"])
    landm = nt.nodes.new("ShaderNodeMapRange")
    landm.inputs["From Min"].default_value, landm.inputs["From Max"].default_value = 0.545, 0.6
    nt.links.new(land.outputs["Fac"], landm.inputs["Value"])
    night = sun_dot(nt, 0.0, -0.2)
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(cm.outputs["Result"], m1.inputs[0])
    nt.links.new(landm.outputs["Result"], m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    m2.inputs[1].default_value = 0.9
    nt.links.new(m1.outputs[0], m2.inputs[0])
    m3 = nt.nodes.new("ShaderNodeMath")
    m3.operation = "MULTIPLY"
    nt.links.new(m2.outputs[0], m3.inputs[0])
    nt.links.new(night, m3.inputs[1])
    b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.28, 1)
    nt.links.new(m3.outputs[0], b.inputs["Emission Strength"])
    earth.data.materials.append(m)
    earth.rotation_euler = (math.radians(23.4), 0, 0)
    key(earth, "rotation_euler", [(1, math.radians(-30)), (end, math.radians(2))], index=2)

    # --- cloud shell
    clouds = link(sc, uv_sphere("clouds", 1.006, 192, 96))
    cmat = bpy.data.materials.new("clouds_m")
    cmat.use_nodes = True
    cnt = cmat.node_tree
    cnt.nodes.clear()
    cout = cnt.nodes.new("ShaderNodeOutputMaterial")
    ctc = cnt.nodes.new("ShaderNodeTexCoord")
    cmap = cnt.nodes.new("ShaderNodeMapping")
    cmap.inputs["Scale"].default_value = (1.0, 1.0, 1.6)  # zonal streaks
    cnt.links.new(ctc.outputs["Object"], cmap.inputs["Vector"])
    cn = cnt.nodes.new("ShaderNodeTexNoise")
    cn.inputs["Scale"].default_value = 2.6
    cn.inputs["Detail"].default_value = 12
    cn.inputs["Roughness"].default_value = 0.6
    cn.inputs["Distortion"].default_value = 0.9
    cnt.links.new(cmap.outputs["Vector"], cn.inputs["Vector"])
    cr = cnt.nodes.new("ShaderNodeMapRange")
    cr.inputs["From Min"].default_value, cr.inputs["From Max"].default_value = 0.52, 0.68
    cnt.links.new(cn.outputs["Fac"], cr.inputs["Value"])
    cdiff = cnt.nodes.new("ShaderNodeBsdfDiffuse")
    cdiff.inputs["Color"].default_value = (0.92, 0.93, 0.95, 1)
    ctr = cnt.nodes.new("ShaderNodeBsdfTransparent")
    cmix = cnt.nodes.new("ShaderNodeMixShader")
    cnt.links.new(cr.outputs["Result"], cmix.inputs["Fac"])
    cnt.links.new(ctr.outputs[0], cmix.inputs[1])
    cnt.links.new(cdiff.outputs[0], cmix.inputs[2])
    cnt.links.new(cmix.outputs[0], cout.inputs[0])
    clouds.data.materials.append(cmat)
    clouds.rotation_euler = (math.radians(23.4), 0, 0)
    key(clouds, "rotation_euler", [(1, math.radians(-20)), (end, math.radians(18))], index=2)

    # --- thin atmosphere: emissive limb glow on the day side only
    atm = link(sc, uv_sphere("atmosphere", 1.022, 160, 80))
    am = bpy.data.materials.new("atm_m")
    am.use_nodes = True
    ant = am.node_tree
    ant.nodes.clear()
    aout = ant.nodes.new("ShaderNodeOutputMaterial")
    geo = ant.nodes.new("ShaderNodeNewGeometry")
    nd = ant.nodes.new("ShaderNodeVectorMath")
    nd.operation = "DOT_PRODUCT"
    ant.links.new(geo.outputs["Normal"], nd.inputs[0])
    ant.links.new(geo.outputs["Incoming"], nd.inputs[1])
    ab = ant.nodes.new("ShaderNodeMath")
    ab.operation = "ABSOLUTE"
    ant.links.new(nd.outputs["Value"], ab.inputs[0])
    inv = ant.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    ant.links.new(ab.outputs[0], inv.inputs[1])
    pw = ant.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 6.0
    ant.links.new(inv.outputs[0], pw.inputs[0])
    lit = sun_dot(ant, -0.35, 0.35)
    mm = ant.nodes.new("ShaderNodeMath")
    mm.operation = "MULTIPLY"
    ant.links.new(pw.outputs[0], mm.inputs[0])
    ant.links.new(lit, mm.inputs[1])
    base = ant.nodes.new("ShaderNodeMath")             # faint blue haze over the whole day side
    base.operation = "MULTIPLY_ADD"
    base.inputs[1].default_value = 0.012
    ant.links.new(lit, base.inputs[0])
    ant.links.new(mm.outputs[0], base.inputs[2])
    st = ant.nodes.new("ShaderNodeMath")
    st.operation = "MULTIPLY"
    st.inputs[1].default_value = 2.6
    ant.links.new(base.outputs[0], st.inputs[0])
    em = ant.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.22, 0.48, 1.0, 1)
    ant.links.new(st.outputs[0], em.inputs["Strength"])
    tr = ant.nodes.new("ShaderNodeBsdfTransparent")
    add = ant.nodes.new("ShaderNodeAddShader")
    ant.links.new(tr.outputs[0], add.inputs[0])
    ant.links.new(em.outputs[0], add.inputs[1])
    ant.links.new(add.outputs[0], aout.inputs[0])
    atm.data.materials.append(am)
    atm.visible_shadow = False

    # --- camera: slow drift for ~40%, then exponential pull-back to a dot, then nothing.
    cam = camera(sc, (0, -5.6, 0), (88.5, 0, 0), lens=35)
    cam.data.clip_start = 0.01
    cam.data.clip_end = 1e7
    # log-distance control points (Earth radii), monotone cubic between them
    pts = [(1, 6.4), (60, 6.8), (125, 7.8), (150, 9.5), (176, 22), (205, 120), (235, 1100),
           (250, 3200), (PALEDOT_GONE, 6500), (275, 4e4), (end, 4e5)]
    xs = np.array([p[0] for p in pts], float)
    ys = np.log([p[1] for p in pts])
    h = np.diff(xs)
    dl = np.diff(ys) / h
    dk = np.zeros_like(ys)  # Fritsch-Carlson slopes
    for k in range(1, len(xs) - 1):
        if dl[k - 1] * dl[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            dk[k] = (w1 + w2) / (w1 / dl[k - 1] + w2 / dl[k])
    dk[0], dk[-1] = dl[0], dl[-1]

    def logd(f):
        k = min(max(np.searchsorted(xs, f) - 1, 0), len(xs) - 2)
        t = (f - xs[k]) / h[k]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[k] + h10 * h[k] * dk[k] + h01 * ys[k + 1] + h11 * h[k] * dk[k + 1]

    _key_every_frame(cam, "location", 1, lambda f: -float(math.exp(logd(f))), 1, end)
    _key_every_frame(cam, "location", 0, lambda f: -0.15 + 0.3 * _smoothstep(1, 150, f), 1, end)
    # The pale dot: once Earth shrinks below ~2 px it would just vanish in the denoiser, so a tiny
    # emissive point (hidden inside Earth while Earth is bigger) keeps it a single pale-blue pixel
    # until it fades out at "it's gone".
    dot = link(sc, uv_sphere("pale_dot", 1.0, 24, 12))
    dot.data.materials.append(mat_emit("pale_dot_m", (0.55, 0.7, 1.0), 1.0))
    dot.visible_shadow = False
    dem = dot.data.materials[0].node_tree.nodes["Emission"].inputs["Strength"]
    for f, v in ((1, 3.0), (PALEDOT_GONE - 12, 3.0), (PALEDOT_GONE, 0.0)):
        dem.default_value = v
        dem.keyframe_insert("default_value", frame=f)
    px = math.radians(21.8) / RES_X                                # ~ angular size of one pixel
    _key_every_frame(dot, "scale", -1, lambda f: [max(0.3, 1.1 * px * math.exp(logd(f)))] * 3, 1, end)
    caption(sc, cam, "This is everything\nyou have ever known.", 10, 92)
    caption(sc, cam, "Every person who ever lived.\nEvery war. Every love.", 98, 176)
    caption(sc, cam, "From far enough away…", 184, 250)
    caption(sc, cam, "it's gone.", PALEDOT_GONE, end + 1, y=0.0, size=0.09)
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
