"""
65 DAYS — Blender (bpy 5.1.2 module, Cycles CPU) shots.

  land   : 1 still, RGBA silhouette plate of the headland + wind-bent tree (sky/sea/Sun are composited in numpy)
  orbit  : 1 still 2880x1620 RGBA, Earth half-lit (the comp pans/zooms it over stars: 2.5D, video 14.5–36.5 s)
  moon   : 2 stills (--layer earth|moon) RGBA, backlit crescents; the comp adds the 1.4° Sun and drifts the Moon
  dive   : 540 frames (video 197–219.5 s) the final plunge to the photosphere, real fall kinematics (time-compressed)

Units: 1 BU = 1000 km for space shots, metres for the landscape.
Run:
  /home/user/bpyenv/bin/python -c "import sys; p='shots.py'; sys.argv=['blender','--','--shot','orbit','--frames','1,200']; exec(compile(open(p).read(),p,'exec'))"
  ... '--render','--skip-existing','--start',N,'--end',M,'--step',K,'--threads',T
"""
import sys, os, math, time, json
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV): return ARGV[i + 1]
    return default

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/01-65-days"
TEX = SCR + "/tex"
HERE = "/home/user/do-my-task/docs-series/01-65-days"
SHOT = arg("--shot", "orbit")
FPS = 24
NFR = {"land": 1, "orbit": 1, "moon": 1, "dive": 540}[SHOT]
SPP = int(arg("--spp", {"land": 16, "orbit": 24, "moon": 24, "dive": 3}[SHOT]))

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def smooth(a): a = clamp(a); return a * a * (3 - 2 * a)
def ease(a): a = clamp(a); return a * a * a * (a * (a * 6 - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t

# ---------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, NFR
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"; cy.samples = SPP
    cy.use_adaptive_sampling = False; cy.use_denoising = False
    cy.max_bounces = 0
    cy.diffuse_bounces = cy.glossy_bounces = cy.transmission_bounces = cy.volume_bounces = 0
    cy.transparent_max_bounces = 6
    cy.caustics_reflective = cy.caustics_refractive = False
    for k, v in (("use_light_tree", False), ("pixel_filter_width", 1.2), ("seed", 7)):
        try: setattr(cy, k, v)
        except Exception: pass
    th = int(arg("--threads", 2))
    sc.render.threads_mode = "FIXED"; sc.render.threads = th
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    ims = sc.render.image_settings
    try: ims.media_type = "IMAGE"
    except Exception: pass
    ims.file_format = "PNG"
    ims.color_mode = "RGB" if SHOT == "dive" else "RGBA"
    ims.color_depth = "8"
    sc.render.film_transparent = (SHOT != "dive")
    if SHOT in ("orbit", "moon"):
        sc.render.resolution_percentage = 150          # 2880x1620 still, the comp crops/zooms
    try: sc.render.use_persistent_data = True
    except Exception: pass
    return sc

def node(nt, t, **kw):
    n = nt.nodes.new(t)
    for k, v in kw.items():
        if k in n.inputs: n.inputs[k].default_value = v
        else: setattr(n, k, v)
    return n
def link(nt, a, b): nt.links.new(a, b)
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    try: m.cycles.emission_sampling = "NONE"     # emissive shells/surfaces must not act as lights
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial")
    return m, nt, out
def img(path, colorspace="sRGB"):
    im = bpy.data.images.load(path, check_existing=True)
    try: im.colorspace_settings.name = colorspace
    except Exception: pass
    return im
def link_ob(ob): bpy.context.scene.collection.objects.link(ob); return ob
def uv_sphere(name, r, seg=128, ring=64, mat=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r, calc_uvs=True)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free()
    if mat: me.materials.append(mat)
    ob = link_ob(bpy.data.objects.new(name, me)); ob.location = loc
    if name in ("atmo", "chromo"):        # glow shells: camera-visible only, never light or shadow anything
        ob.visible_diffuse = False; ob.visible_shadow = False; ob.visible_glossy = False
    return ob
def camera(lens, loc, sensor=36.0):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = sensor; cd.sensor_fit = "HORIZONTAL"
    cd.clip_start = 0.01; cd.clip_end = 1e7
    ob = link_ob(bpy.data.objects.new("cam", cd)); ob.location = loc
    bpy.context.scene.camera = ob
    return ob
def look_at(ob, target, roll=0.0):
    d = Vector(target) - ob.location
    q = d.to_track_quat("-Z", "Y")
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = q @ Matrix.Rotation(roll, 4, "Z").to_quaternion()
def world_stars(strength):
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld")
    tc = node(nt, "ShaderNodeTexCoord")
    env = node(nt, "ShaderNodeTexEnvironment"); env.image = img(TEX + "/stars_eq.png")
    bg = node(nt, "ShaderNodeBackground", Strength=strength)
    link(nt, tc.outputs["Generated"], env.inputs["Vector"])
    link(nt, env.outputs["Color"], bg.inputs["Color"]); link(nt, bg.outputs[0], out.inputs["Surface"])
    return bg
def sun_lamp(direction, strength=4.0, angle_deg=0.53):
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = strength; ld.angle = math.radians(angle_deg)
    ob = link_ob(bpy.data.objects.new("sun", ld))
    d = Vector(direction).normalized()            # direction the light travels
    ob.rotation_mode = "QUATERNION"; ob.rotation_quaternion = d.to_track_quat("-Z", "Y")
    return ob

# ---------------------------------------------------------------- Earth / Moon materials
def earth_material(sun_travel_dir, night_gain=1.0):
    m, nt, out = new_mat("earth")
    tc = node(nt, "ShaderNodeTexCoord")
    day = node(nt, "ShaderNodeTexImage"); day.image = img(TEX + "/earth-blue-marble.jpg")
    nig = node(nt, "ShaderNodeTexImage"); nig.image = img(TEX + "/earth-night.jpg")
    link(nt, tc.outputs["UV"], day.inputs["Vector"]); link(nt, tc.outputs["UV"], nig.inputs["Vector"])
    # slightly deepen/cool the oceans, keep land natural
    hsv = node(nt, "ShaderNodeHueSaturation", Saturation=1.08, Value=1.05)
    link(nt, day.outputs["Color"], hsv.inputs["Color"])
    dif = node(nt, "ShaderNodeBsdfDiffuse"); link(nt, hsv.outputs["Color"], dif.inputs["Color"])
    # night-side mask: dot(N, toward-sun)
    geo = node(nt, "ShaderNodeNewGeometry")
    dp = node(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
    link(nt, geo.outputs["Normal"], dp.inputs[0]); dp.inputs[1].default_value = tuple(-Vector(sun_travel_dir).normalized())
    mr = node(nt, "ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.08; mr.inputs["From Max"].default_value = -0.12
    link(nt, dp.outputs["Value"], mr.inputs["Value"])
    em = node(nt, "ShaderNodeEmission")
    link(nt, nig.outputs["Color"], em.inputs["Color"])
    mul = node(nt, "ShaderNodeMath", operation="MULTIPLY"); mul.inputs[1].default_value = 0.9 * night_gain
    link(nt, mr.outputs["Result"], mul.inputs[0]); link(nt, mul.outputs[0], em.inputs["Strength"])
    add = node(nt, "ShaderNodeAddShader"); link(nt, dif.outputs[0], add.inputs[0]); link(nt, em.outputs[0], add.inputs[1])
    link(nt, add.outputs[0], out.inputs["Surface"])
    return m

def atmo_material(sun_travel_dir, gain=1.0, back=False):
    """Thin limb glow: emission ∝ (1-facing)^p, only where the shell is sunlit (or forward-scattered when backlit)."""
    m, nt, out = new_mat("atmo")
    lw = node(nt, "ShaderNodeLayerWeight", Blend=0.5)
    pw = node(nt, "ShaderNodeMath", operation="POWER"); pw.inputs[1].default_value = 2.2
    inv = node(nt, "ShaderNodeMath", operation="SUBTRACT"); inv.inputs[0].default_value = 1.0
    link(nt, lw.outputs["Facing"], inv.inputs[1]); link(nt, inv.outputs[0], pw.inputs[0])
    # rim: invert so edge-on = 1  -> (Facing is 0 when facing camera, 1 at grazing in Blender) use Facing directly
    rim = node(nt, "ShaderNodeMath", operation="POWER"); rim.inputs[1].default_value = 3.0
    link(nt, lw.outputs["Facing"], rim.inputs[0])
    geo = node(nt, "ShaderNodeNewGeometry")
    dp = node(nt, "ShaderNodeVectorMath", operation="DOT_PRODUCT")
    link(nt, geo.outputs["Normal"], dp.inputs[0]); dp.inputs[1].default_value = tuple(-Vector(sun_travel_dir).normalized())
    mr = node(nt, "ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.25 if back else -0.15; mr.inputs["From Max"].default_value = 0.35
    link(nt, dp.outputs["Value"], mr.inputs["Value"])
    s = node(nt, "ShaderNodeMath", operation="MULTIPLY"); link(nt, rim.outputs[0], s.inputs[0]); link(nt, mr.outputs["Result"], s.inputs[1])
    s2 = node(nt, "ShaderNodeMath", operation="MULTIPLY"); s2.inputs[1].default_value = 2.4 * gain
    link(nt, s.outputs[0], s2.inputs[0])
    em = node(nt, "ShaderNodeEmission"); em.inputs["Color"].default_value = (0.32, 0.55, 1.0, 1)
    link(nt, s2.outputs[0], em.inputs["Strength"])
    tr = node(nt, "ShaderNodeBsdfTransparent")
    add = node(nt, "ShaderNodeAddShader"); link(nt, tr.outputs[0], add.inputs[0]); link(nt, em.outputs[0], add.inputs[1])
    link(nt, add.outputs[0], out.inputs["Surface"])
    try: m.blend_method = "BLEND"
    except Exception: pass
    return m

def moon_material():
    m, nt, out = new_mat("moon")
    tc = node(nt, "ShaderNodeTexCoord")
    t = node(nt, "ShaderNodeTexImage"); t.image = img(TEX + "/moon.png")
    link(nt, tc.outputs["UV"], t.inputs["Vector"])
    dif = node(nt, "ShaderNodeBsdfDiffuse"); link(nt, t.outputs["Color"], dif.inputs["Color"])
    link(nt, dif.outputs[0], out.inputs["Surface"])
    return m

def emit_material(name, color, strength):
    m, nt, out = new_mat(name)
    em = node(nt, "ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1); em.inputs["Strength"].default_value = strength
    link(nt, em.outputs[0], out.inputs["Surface"])
    return m

# ---------------------------------------------------------------- photosphere (dive)
def sun_surface_material(R):
    """Granulation: two pre-baked periodic Worley tiles (box-projected), supergranulation + fine noise, limb darkening."""
    m, nt, out = new_mat("photosphere")
    tc = node(nt, "ShaderNodeTexCoord")
    def tile(path, scale, rot):
        mp = node(nt, "ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale)
        mp.inputs["Rotation"].default_value = rot
        link(nt, tc.outputs["Object"], mp.inputs["Vector"])
        t = node(nt, "ShaderNodeTexImage"); t.image = img(path, "Non-Color")
        t.projection = "BOX"; t.projection_blend = 0.25; t.extension = "REPEAT"; t.interpolation = "Cubic"
        link(nt, mp.outputs[0], t.inputs["Vector"])
        return t
    # tile a: 160 cells per tile -> tile = 160 BU (1 granule ~ 1000 km); tile b: 136 cells, rotated
    ta = tile(TEX + "/gran_a.png", 1 / 160.0, (0.3, 0.1, 0.7))
    tb = tile(TEX + "/gran_b.png", 1 / 128.0, (1.1, 0.6, 0.2))
    mix = node(nt, "ShaderNodeMix", data_type="FLOAT"); mix.inputs["Factor"].default_value = 0.5
    link(nt, ta.outputs["Color"], mix.inputs[2]); link(nt, tb.outputs["Color"], mix.inputs[3])
    # gran tiles store g/2 -> *2
    g = node(nt, "ShaderNodeMath", operation="MULTIPLY"); g.inputs[1].default_value = 2.0
    link(nt, mix.outputs[0], g.inputs[0])
    # contrast boost so the lanes read: g' = g^1.6
    gp = node(nt, "ShaderNodeMath", operation="POWER"); gp.inputs[1].default_value = 1.7
    link(nt, g.outputs[0], gp.inputs[0])
    sup = node(nt, "ShaderNodeTexNoise", Scale=1 / 30.0 * 1.0, Detail=2.0, Roughness=0.5)
    link(nt, tc.outputs["Object"], sup.inputs["Vector"])
    supm = node(nt, "ShaderNodeMapRange"); supm.inputs["To Min"].default_value = 0.90; supm.inputs["To Max"].default_value = 1.10
    link(nt, sup.outputs["Fac"], supm.inputs["Value"])
    fine = node(nt, "ShaderNodeTexNoise", Scale=6.0, Detail=3.0, Roughness=0.6)
    link(nt, tc.outputs["Object"], fine.inputs["Vector"])
    finem = node(nt, "ShaderNodeMapRange"); finem.inputs["To Min"].default_value = 0.93; finem.inputs["To Max"].default_value = 1.07
    link(nt, fine.outputs["Fac"], finem.inputs["Value"])
    b1 = node(nt, "ShaderNodeMath", operation="MULTIPLY"); link(nt, gp.outputs[0], b1.inputs[0]); link(nt, supm.outputs["Result"], b1.inputs[1])
    b2 = node(nt, "ShaderNodeMath", operation="MULTIPLY"); link(nt, b1.outputs[0], b2.inputs[0]); link(nt, finem.outputs["Result"], b2.inputs[1])
    # limb darkening: I = 1 - u(1-mu), mu = facing cos
    lw = node(nt, "ShaderNodeLayerWeight", Blend=0.5)
    mu = node(nt, "ShaderNodeMath", operation="SUBTRACT"); mu.inputs[0].default_value = 1.0
    link(nt, lw.outputs["Facing"], mu.inputs[1])
    ld = node(nt, "ShaderNodeMapRange"); ld.inputs["To Min"].default_value = 0.38; ld.inputs["To Max"].default_value = 1.0
    link(nt, mu.outputs[0], ld.inputs["Value"])
    b3 = node(nt, "ShaderNodeMath", operation="MULTIPLY"); link(nt, b2.outputs[0], b3.inputs[0]); link(nt, ld.outputs["Result"], b3.inputs[1])
    # colour ramp: dark lanes deep orange -> granule centres yellow-white
    cr = node(nt, "ShaderNodeValToRGB")
    els = cr.color_ramp.elements
    els[0].position = 0.0; els[0].color = (0.10, 0.012, 0.0, 1)
    els[1].position = 1.6; els[1].color = (1.0, 0.92, 0.62, 1)
    e = els.new(0.45); e.color = (0.55, 0.13, 0.01, 1)
    e = els.new(0.95); e.color = (0.98, 0.52, 0.10, 1)
    sc = node(nt, "ShaderNodeMath", operation="MULTIPLY"); sc.inputs[1].default_value = 0.625
    link(nt, b3.outputs[0], sc.inputs[0]); link(nt, sc.outputs[0], cr.inputs["Fac"])
    em = node(nt, "ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    link(nt, cr.outputs["Color"], em.inputs["Color"])
    link(nt, em.outputs[0], out.inputs["Surface"])
    return m

def chromo_material():
    m, nt, out = new_mat("chromo")
    lw = node(nt, "ShaderNodeLayerWeight", Blend=0.5)
    p = node(nt, "ShaderNodeMath", operation="POWER"); p.inputs[1].default_value = 6.0
    link(nt, lw.outputs["Facing"], p.inputs[0])
    s = node(nt, "ShaderNodeMath", operation="MULTIPLY"); s.inputs[1].default_value = 1.6
    link(nt, p.outputs[0], s.inputs[0])
    em = node(nt, "ShaderNodeEmission"); em.inputs["Color"].default_value = (1.0, 0.30, 0.10, 1)
    link(nt, s.outputs[0], em.inputs["Strength"])
    tr = node(nt, "ShaderNodeBsdfTransparent")
    add = node(nt, "ShaderNodeAddShader"); link(nt, tr.outputs[0], add.inputs[0]); link(nt, em.outputs[0], add.inputs[1])
    link(nt, add.outputs[0], out.inputs["Surface"])
    return m

# ---------------------------------------------------------------- landscape geometry
def fbm1(x, seed, octaves=7):
    v, a, f = 0.0, 1.0, 1.0
    for i in range(octaves):
        v += a * (math.sin(x * f * 0.9 + seed * 1.7 + i * 2.3) * 0.6 + math.sin(x * f * 2.1 + seed * 3.1 + i) * 0.4)
        a *= 0.5; f *= 2.03
    return v

def profile_mesh(name, y, xs, zs, mat, bottom=-200.0):
    me = bpy.data.meshes.new(name); verts, faces = [], []
    for x, z in zip(xs, zs): verts += [(x, y, z), (x, y, bottom)]
    for i in range(len(xs) - 1):
        a, c = 2 * i, 2 * i + 2; faces.append((a + 1, c + 1, c, a))
    me.from_pydata(verts, [], faces); me.materials.append(mat)
    return link_ob(bpy.data.objects.new(name, me))

def tree(name, base, height, mat):
    """Bare wind-bent tree (same recipe as the series look), leaning right (downwind)."""
    import random
    rnd = random.Random(11); bm = bmesh.new(); WIND = Vector((1.0, 0.0, 0.0))
    def seg(p, q, r0, r1):
        d = (q - p); L = d.length; d.normalize()
        mtx = Matrix.Translation((p + q) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=r0, radius2=r1, depth=L * 1.06, matrix=mtx)
    def branch(p, d, length, rad, depth):
        cur, dd, r = p.copy(), d.copy(), rad
        for i in range(3):
            dd = (dd + WIND * 0.045 * (1.0 + (6 - depth) * 0.10) + Vector((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.05, 0.05), -0.012 * (6 - depth)))).normalized()
            nxt = cur + dd * (length / 3); seg(cur, nxt, r, r * 0.86); cur, r = nxt, r * 0.86
        if depth == 0 or rad < 0.010: return
        for k in range(rnd.choice((2, 2, 3))):
            side = rnd.uniform(-1.0, 1.0)
            ax = Vector((side, rnd.uniform(-0.5, 0.5), rnd.uniform(0.25, 0.9)))
            nd = (dd * 0.75 + ax * rnd.uniform(0.5, 0.9) + WIND * 0.18).normalized()
            if nd.z < -0.15: nd.z = -0.15; nd.normalize()
            branch(cur, nd, length * rnd.uniform(0.60, 0.78), r * rnd.uniform(0.55, 0.72), depth - 1)
    p = Vector(base) - Vector((0, 0, 0.8)); pts = [p]
    for dx, dz in ((0.05, 1.0), (0.22, 1.0), (0.38, 1.0), (0.55, 0.9)):
        p = p + Vector((dx, 0, dz)).normalized() * height * 0.13; pts.append(p)
    rad = height * 0.030
    for a, c in zip(pts, pts[1:]): seg(a, c, rad, rad * 0.88); rad *= 0.88
    top = pts[-1]
    for ang, lf in ((-0.75, 0.38), (-0.2, 0.46), (0.3, 0.48), (0.85, 0.42)):
        d = Vector((math.sin(ang) * 0.9 + 0.25, rnd.uniform(-0.3, 0.3), math.cos(ang))).normalized()
        branch(top, d, height * lf * 0.55, rad * 0.72, 6)
    branch(pts[2], Vector((0.9, 0.1, 0.6)).normalized(), height * 0.26, rad * 0.75, 5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    return link_ob(bpy.data.objects.new(name, me))

# Landscape camera: hFOV 40°, horizon (pitch 0) at y = 713 px via lens shift. f_px = 960/tan(20°) = 2637.6
LAND_LENS = 18.0 / math.tan(math.radians(20.0))
LAND_SHIFT = (713 - 540) / 1920.0

def build_land():
    """Two RGBA layers (--layer near|far) so the comp can haze the far headland separately."""
    world_black()
    cam = camera(LAND_LENS, (0, 0, 1.7)); cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.shift_y = LAND_SHIFT
    blk = emit_material("blk", (0, 0, 0), 0.0)
    f = 2637.6
    def wx(px, dist): return (px - 960) / f * dist
    def wz(el, dist): return 1.7 + dist * math.tan(math.radians(el))
    layer = arg("--layer", "near")
    if layer == "far":
        # long low headland 2.5 km away, from the left edge tapering into the sea at px ~ 930
        xs, zs = [], []
        for i in range(700):
            px = -150 + i / 699.0 * 1150
            el = 1.25 * (1 - smooth((px + 50) / 980)) ** 0.8 + 0.12 * fbm1(px / 55.0, 5, 7) * (1 - smooth((px - 700) / 250)) + 0.08
            el = el * (1 - smooth((px - 820) / 170)) - 0.06 * smooth((px - 900) / 80)
            xs.append(wx(px, 2500)); zs.append(wz(el, 2500))
        profile_mesh("far", 2500, xs, zs, blk, bottom=0.0)
    else:
        # near grassy knoll 140 m away on the left; it rolls down below the horizon by px ~ 760
        def el_near(px):
            return (3.3 * (1 - smooth((px - 60) / 700)) ** 1.1 + 0.10 * fbm1(px / 40.0, 9, 7) - 1.1 * smooth((px - 520) / 300) - 0.25
                    - 6.0 * smooth((px - 720) / 520))
        xs, zs = [], []
        for i in range(900):
            px = -120 + i / 899.0 * 1400
            xs.append(wx(px, 140)); zs.append(wz(el_near(px), 140))
        profile_mesh("knoll", 140, xs, zs, blk, bottom=-40)
        # thin dark shoreline rocks along the very bottom of frame
        xs, zs = [], []
        for i in range(600):
            px = -80 + i / 599.0 * 2080
            el = -6.5 + 0.30 * fbm1(px / 35.0, 13, 7) + 0.7 * (1 - smooth(px / 900))
            xs.append(wx(px, 40)); zs.append(wz(el, 40))
        profile_mesh("shore", 40, xs, zs, blk, bottom=-30)
        px = 330
        base = (wx(px, 138), 138, wz(el_near(px), 138) - 0.3)
        tree("tree", base, 10.5, blk)

def world_black():
    w = bpy.data.worlds.new("w"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear(); out = node(nt, "ShaderNodeOutputWorld")
    bg = node(nt, "ShaderNodeBackground", Strength=0.0); link(nt, bg.outputs[0], out.inputs["Surface"])

# ---------------------------------------------------------------- orbit still (2.5D: the comp pans/zooms it over a separate star layer)
def build_orbit():
    world_black()
    sdir = Vector((1.0, 0.30, -0.10)).normalized()     # light travels +x: the Sun is off-frame left
    sun_lamp(sdir, 4.5)
    earth = uv_sphere("earth", 6.371, 256, 128, earth_material(sdir))
    earth.rotation_euler = (math.radians(-23.4), 0, math.radians(205))
    uv_sphere("atmo", 6.371 * 1.018, 192, 96, atmo_material(sdir, 1.0))
    cam = camera(50.0, (0, -46, 0.0))
    look_at(cam, (-4.6, 0, 0.4))
    return dict(cam=cam)

# ---------------------------------------------------------------- moon stills (Earth layer + Moon layer, Sun drawn in comp)
MOON_SUN = Vector((8186.0, 56800.0, 3215.0))      # 0.38 AU ahead: 1.40° disc at screen (1344, 389) of the 1080p frame
MOON_EARTH = Vector((-23.0, 160.0, -7.8))         # screen (576, 670), 4.6° wide
MOON_MOON = Vector((-142.0, 520.0, 42.0))         # 383 thousand km from Earth, screen (230, 324)
def build_moon():
    world_black()
    layer = arg("--layer", "earth")
    tgt = MOON_EARTH if layer == "earth" else MOON_MOON
    sdir = (tgt - MOON_SUN).normalized()
    sun_lamp(sdir, 6.0, angle_deg=1.4)
    if layer == "earth":
        earth = uv_sphere("earth", 6.371, 256, 128, earth_material(sdir, night_gain=0.0), loc=MOON_EARTH)
        earth.rotation_euler = (math.radians(-23.4), 0, math.radians(110))
        uv_sphere("atmo", 6.371 * 1.022, 192, 96, atmo_material(sdir, 2.2, back=True), loc=MOON_EARTH)
    else:
        uv_sphere("moon", 1.737, 128, 64, moon_material(), loc=MOON_MOON)
    cam = camera(50.0, (0, 0, 0))
    cam.rotation_euler = (math.radians(90), 0, 0)
    return dict(cam=cam)

# ---------------------------------------------------------------- dive shot
RS_BU = 695.7
def build_dive():
    world_black()
    m = sun_surface_material(RS_BU)
    uv_sphere("photosphere", RS_BU, 512, 256, m)
    uv_sphere("chromo", RS_BU * 1.006, 256, 128, chromo_material())
    cam = camera(32.0, (0, 0, RS_BU + 400))
    return dict(cam=cam)

def dive_altitude(t_video):
    """Height of the camera (Earth's sunward surface) above the photosphere, in BU, from the exact fall solution."""
    sys.path.insert(0, HERE); sys.path.insert(0, HERE + "/physics")
    import timeline as TL
    import fall as FL
    import numpy as np
    sim = TL.sim_of(t_video)
    s = FL.state(np.array([min(sim, TL.T_IMPACT_D) * 86400.0]))
    return float(s["r_km"][0]) / 1000.0 - 6.371 - RS_BU

def update_dive(S, f):
    tv = 197.0 + (f - 1) / FPS
    h = max(0.02, dive_altitude(tv))
    cam = S["cam"]
    cam.location = (0, 0, RS_BU + h)
    # look angle from nadir: keep the limb in the upper frame for most of the fall, then pitch down into the surface
    limb = math.degrees(math.asin(RS_BU / (RS_BU + h)))
    tilt = min(limb - 4.0, lerp(36.0, 66.0, smooth((tv - 197.0) / 17.0)))
    tilt = lerp(tilt, 25.0, smooth((tv - 214.6) / 3.4))
    cam.rotation_mode = "XYZ"
    cam.rotation_euler = (math.radians(tilt), 0.0, math.radians(8.0 * smooth((tv - 197) / 21)))
    return dict(t=tv, h=h, tilt=tilt)

# ---------------------------------------------------------------- main
def main():
    sc = reset_scene()
    S = {"land": build_land, "orbit": build_orbit, "moon": build_moon, "dive": build_dive}[SHOT]()
    upd = {"dive": update_dive}.get(SHOT, lambda S, f: {})
    out = arg("--out", f"{SCR}/frames/{SHOT}" + (("_" + arg("--layer", "earth")) if SHOT == "moon" else "") + (("_" + arg("--layer", "near")) if SHOT == "land" else ""))
    os.makedirs(out, exist_ok=True)
    if arg("--frames"): frames = [int(v) for v in arg("--frames").split(",")]
    else:
        a = int(arg("--start", 1)); e = int(arg("--end", NFR)); st = int(arg("--step", 1))
        frames = list(range(a, e + 1, st))
    skip = "--skip-existing" in ARGV
    print(f"[{SHOT}] rendering {len(frames)} frames -> {out}", flush=True)
    for f in frames:
        path = os.path.join(out, f"f_{f:04d}.png")
        if skip and os.path.exists(path) and os.path.getsize(path) > 0: continue
        t0 = time.time()
        sc.frame_set(f)
        info = upd(S, f) or {}
        tmp = path[:-4] + "_tmp.png"
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True)
        os.replace(tmp, path)
        print(f"frame {f} {time.time() - t0:.2f}s {json.dumps({k: round(v, 3) for k, v in info.items()})}", flush=True)

main()
