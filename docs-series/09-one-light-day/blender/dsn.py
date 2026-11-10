"""ONE LIGHT-DAY FROM HOME - a stylised 70 m Deep Space Network antenna at night (Blender 5.1.2 bpy, Cycles CPU).
Our own model from rough public dimensions (70 m reflector, quadripod + subreflector, feed cones, alidade on a round
concrete pedestal). Film transparent: sky and stars are composited behind it.  Output: SCR/plates/plate_dsn/0000.png
Run: /home/user/bpyenv/bin/python -c "import sys;p='blender/dsn.py';sys.argv=['blender','--','final'];exec(compile(open(p).read(),p,'exec'))"
"""
import bpy, bmesh, math, sys, os, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "test"
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day"
TEX = os.path.join(SCR, "tex"); os.makedirs(TEX, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.cycles.sample_clamp_indirect = 3.0
sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
sc.render.film_transparent = True
sc.view_settings.view_transform = "Filmic"; sc.view_settings.look = "None"
sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "8"
sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", "3"))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.06, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
COL = sc.collection


def link(ob):
    COL.objects.link(ob); return ob


def mat(name, col, rough=0.6, metal=0.0, bump=0.0, bscale=1.0, emit=None, es=0.0, wear=0.1):
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree; b = t.nodes["Principled BSDF"]; L = t.links.new
    b.inputs["Metallic"].default_value = metal
    tcn = t.nodes.new("ShaderNodeTexCoord")
    wn = t.nodes.new("ShaderNodeTexNoise"); wn.inputs["Scale"].default_value = 0.35; wn.inputs["Detail"].default_value = 9.0
    wn.inputs["Roughness"].default_value = 0.7; L(tcn.outputs["Object"], wn.inputs["Vector"])
    mx = t.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (*col, 1); mx.inputs["B"].default_value = (*[c * 0.5 for c in col], 1)
    mr2 = t.nodes.new("ShaderNodeMapRange"); mr2.inputs[1].default_value = 0.4; mr2.inputs[2].default_value = 0.8
    L(wn.outputs["Fac"], mr2.inputs[0]); L(mr2.outputs[0], mx.inputs["Factor"]); L(mx.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = es
    if bump > 0:
        n = t.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = bscale; n.inputs["Detail"].default_value = 6.0
        L(tcn.outputs["Object"], n.inputs["Vector"])
        bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.2
        L(n.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    return m


M_STEEL = mat("steel", (0.62, 0.63, 0.62), rough=0.5, metal=0.2)
M_STEELD = mat("steeld", (0.25, 0.26, 0.27), rough=0.5, metal=0.5)
M_CONC = mat("concrete", (0.42, 0.40, 0.37), rough=0.9, bump=0.5, bscale=1.2)
M_GROUND = mat("ground", (0.16, 0.12, 0.085), rough=1.0, bump=1.0, bscale=0.5)
M_WIN = mat("window", (0.1, 0.1, 0.1), emit=(1.0, 0.62, 0.25), es=14.0)
M_RED = mat("red", (0.1, 0, 0), emit=(1.0, 0.05, 0.02), es=120.0)
M_LAMP = mat("lamp", (0.1, 0.1, 0.1), emit=(1.0, 0.7, 0.4), es=160.0)
M_ROAD = mat("road", (0.05, 0.05, 0.055), rough=0.8)


class MB:
    def __init__(self): self.bm = {}
    def get(self, m):
        if m.name not in self.bm: self.bm[m.name] = (bmesh.new(), m)
        return self.bm[m.name][0]
    def cyl(self, m, a, b, r, seg=8, r2=None, caps=True):
        a = Vector(a); b = Vector(b); d = b - a
        if d.length < 1e-6: return
        mtx = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(self.get(m), cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=d.length, matrix=mtx)
    def box(self, m, c, size, rot=None):
        mtx = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(self.get(m), size=1.0, matrix=mtx)
    def beam(self, m, a, b, wdt):
        a = Vector(a); b = Vector(b); d = b - a
        mtx = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((wdt, wdt, d.length, 1))
        bmesh.ops.create_cube(self.get(m), size=1.0, matrix=mtx)
    def truss(self, m, a, b, wdt, bays, r, up=(0, 0, 1)):
        a = Vector(a); b = Vector(b); ax = (b - a).normalized(); up = Vector(up)
        if abs(ax.dot(up)) > 0.95: up = Vector((1, 0, 0))
        u = (up - ax * up.dot(ax)).normalized(); v = ax.cross(u)
        def ring(t):
            c = a.lerp(b, t); return [c + (u * sx + v * sy) * wdt / 2 for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        prev = ring(0)
        for i in range(1, bays + 1):
            cur = ring(i / bays)
            for k in range(4):
                self.cyl(m, prev[k], cur[k], r, 5); self.cyl(m, cur[k], cur[(k + 1) % 4], r * 0.7, 5)
                self.cyl(m, prev[k], cur[(k + 1) % 4] if i % 2 else cur[(k - 1) % 4], r * 0.6, 5)
            prev = cur
    def finish(self, name, parent=None, mtx=None):
        obs = []
        for k, (bm, m) in self.bm.items():
            me = bpy.data.meshes.new(name + k); bm.to_mesh(me); bm.free(); me.materials.append(m)
            ob = link(bpy.data.objects.new(name + k, me))
            if mtx is not None: ob.matrix_world = mtx
            obs.append(ob)
        return obs


D_R = 35.0; D_F = 27.0
def dz(r): return r * r / (4 * D_F)


def dish_tex():
    path = os.path.join(TEX, "dsn_dish.png"); N = 2048
    if not os.path.exists(path):
        yy, xx = np.mgrid[0:N, 0:N].astype(np.float32); x = (xx / N - 0.5) / 0.49; y = (yy / N - 0.5) / 0.49
        r = np.hypot(x, y); th = np.arctan2(y, x); seam = np.zeros((N, N), np.float32)
        rings = np.linspace(0.12, 1.0, 14); ridx = np.searchsorted(rings, r)
        npan = np.take(np.array([16, 16, 32, 32, 32, 64, 64, 64, 64, 96, 96, 96, 96, 96, 96]), np.clip(ridx, 0, 14))
        g = np.abs(((th / (2 * math.pi) * npan + 0.5) % 1.0) - 0.5) * (2 * math.pi / npan) * np.maximum(r, 0.05)
        seam = np.maximum(seam, np.clip(1 - g / 0.0022, 0, 1))
        for rr in rings: seam = np.maximum(seam, np.clip(1 - np.abs(r - rr) / 0.0022, 0, 1))
        pid = (np.floor(th / (2 * math.pi) * npan + 0.5) * 7 + ridx * 13)
        tone = ((np.sin(pid * 12.9898) * 43758.5453) % 1.0)
        rg = np.random.default_rng(3); f = np.fft.fftfreq(N) * N; kx, ky = np.meshgrid(f, f); k = np.hypot(kx, ky)
        nz = np.real(np.fft.ifft2(np.fft.fft2(rg.standard_normal((N, N))) * np.where(k < 2, 0, (k + 1e-6) ** -1.4))); nz = (nz - nz.min()) / (nz.max() - nz.min())
        alb = 1.0 - 0.5 * seam - 0.10 * tone - 0.25 * np.clip(nz - 0.45, 0, 1)
        img = np.stack([alb, seam, nz, np.ones_like(alb)], -1)
        im = bpy.data.images.new("d", N, N, alpha=False); im.pixels.foreach_set(np.ascontiguousarray(img, np.float32).ravel())
        im.filepath_raw = path; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
    m = bpy.data.materials.new("dish"); m.use_nodes = True
    t = m.node_tree; b = t.nodes["Principled BSDF"]; L = t.links.new
    img = t.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(path); img.image.colorspace_settings.name = "Non-Color"
    sp = t.nodes.new("ShaderNodeSeparateColor"); L(img.outputs["Color"], sp.inputs[0])
    mx = t.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (0.05, 0.05, 0.05, 1); mx.inputs["B"].default_value = (0.78, 0.78, 0.76, 1)
    L(sp.outputs[0], mx.inputs["Factor"]); L(mx.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6; bp.inputs["Distance"].default_value = 0.05; bp.invert = True
    L(sp.outputs[1], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    return m


EL = math.radians(52); AZ = math.radians(-28)       # pointing direction of the dish
AXIS_H = 38.0                                        # elevation axis height
TILT = Matrix.Translation((0, 0, AXIS_H)) @ Matrix.Rotation(AZ, 4, "Z") @ Matrix.Rotation(math.pi / 2 - EL, 4, "Y")
# local dish frame: +Z = boresight, vertex at z = 6 above the elevation axis


def build():
    # ---------- reflector assembly (in local frame, then tilted)
    mb = MB(); V0 = 6.0
    nr, na = 28, 96; verts, faces, uvs = [], [], []
    for i in range(nr + 1):
        r = 2.0 + (D_R - 2.0) * i / nr
        for j in range(na):
            a0 = 2 * math.pi * j / na
            verts.append((r * math.cos(a0), r * math.sin(a0), V0 + dz(r))); uvs.append((0.5 + r * math.cos(a0) / (2 * D_R) * 0.98, 0.5 + r * math.sin(a0) / (2 * D_R) * 0.98))
    for i in range(nr):
        for j in range(na):
            faces.append((i * na + j, i * na + (j + 1) % na, (i + 1) * na + (j + 1) % na, (i + 1) * na + j))
    me = bpy.data.meshes.new("refl"); me.from_pydata(verts, [], faces); me.materials.append(dish_tex())
    for p in me.polygons: p.use_smooth = True
    uvl = me.uv_layers.new(name="UVMap")
    for li, l in enumerate(me.loops): uvl.data[li].uv = uvs[l.vertex_index]
    refl = link(bpy.data.objects.new("refl", me)); refl.matrix_world = TILT
    sm = refl.modifiers.new("s", "SOLIDIFY"); sm.thickness = 0.25; sm.offset = -1
    # backing structure: 48 radial rib trusses + 5 hoops
    nrib = 48
    def back(r): return V0 + dz(r) - (1.2 + 7.5 * (1 - (r / D_R)) ** 1.0 * (r / D_R + 0.25))
    for k in range(nrib):
        a0 = 2 * math.pi * k / nrib; c, s_ = math.cos(a0), math.sin(a0); prev = None
        for r in np.linspace(3.0, D_R, 9):
            top = Vector((c * r, s_ * r, V0 + dz(r) - 0.3)); bot = Vector((c * r, s_ * r, back(r)))
            mb.cyl(M_STEEL, top, bot, 0.10, 5)
            if prev is not None:
                mb.cyl(M_STEEL, prev[0], top, 0.11, 5); mb.cyl(M_STEEL, prev[1], bot, 0.12, 5); mb.cyl(M_STEEL, prev[1], top, 0.08, 5)
            prev = (top, bot)
    for r in np.linspace(3.0, D_R, 9)[1:]:
        for k in range(nrib):
            a0 = 2 * math.pi * k / nrib; a1 = 2 * math.pi * (k + 1) / nrib
            mb.cyl(M_STEEL, (math.cos(a0) * r, math.sin(a0) * r, back(r)), (math.cos(a1) * r, math.sin(a1) * r, back(r)), 0.09, 5)
            if k % 2 == 0:
                mb.cyl(M_STEEL, (math.cos(a0) * r, math.sin(a0) * r, back(r)), (math.cos(a1) * r, math.sin(a1) * r, V0 + dz(r) - 0.3), 0.07, 5)
    # quadripod + subreflector
    apex = V0 + 24.5
    for k in range(4):
        a0 = math.pi / 4 + k * math.pi / 2; r0 = 24.0
        base = Vector((math.cos(a0) * r0, math.sin(a0) * r0, V0 + dz(r0)))
        top = Vector((math.cos(a0) * 4.2, math.sin(a0) * 4.2, apex + 1.5))
        mb.truss(M_STEEL, base, top, 1.5, 14, 0.11, up=(math.cos(a0), math.sin(a0), 0))
    for k in range(4):
        a0 = math.pi / 4 + k * math.pi / 2; a1 = a0 + math.pi / 2
        mb.cyl(M_STEEL, (math.cos(a0) * 4.2, math.sin(a0) * 4.2, apex + 1.5), (math.cos(a1) * 4.2, math.sin(a1) * 4.2, apex + 1.5), 0.18, 6)
    mb.cyl(M_STEEL, (0, 0, apex - 0.4), (0, 0, apex + 0.6), 2.0, 40, r2=3.9)       # subreflector (convex side down)
    mb.cyl(M_STEELD, (0, 0, apex + 0.6), (0, 0, apex + 2.2), 3.9, 40, r2=3.6)
    mb.cyl(M_RED, (0, 0, apex + 2.2), (0, 0, apex + 2.6), 0.22, 8)
    # feed cones (three, tricone)
    for k in range(3):
        a0 = 2 * math.pi * k / 3 + 0.4; c = Vector((math.cos(a0) * 2.3, math.sin(a0) * 2.3, V0))
        mb.cyl(M_STEEL, c + Vector((0, 0, 0.3)), c + Vector((0, 0, 7.5)), 1.9, 20, r2=1.1)
        mb.cyl(M_STEELD, c + Vector((0, 0, 7.5)), c + Vector((0, 0, 8.3)), 1.1, 20, r2=0.7)
    mb.cyl(M_STEEL, (0, 0, V0 - 0.5), (0, 0, V0 + 0.6), 5.2, 32)
    # elevation wheel (half gear) + counterweights, in the local x-z plane
    for sy in (-9.0, 9.0):
        prev = None
        for i in range(25):
            ang = math.pi + math.pi * i / 24
            p = Vector((math.cos(ang) * 17, sy, math.sin(ang) * 17 + 1.0))
            if prev is not None: mb.beam(M_STEELD, prev, p, 0.7)
            if i % 3 == 0: mb.cyl(M_STEEL, p, (0, sy, 0), 0.16, 6); mb.cyl(M_STEEL, p, (math.cos(ang) * 9, sy * 1.6, back(12.0)), 0.13, 6)
            prev = p
        mb.box(M_STEELD, (0, sy, -15.5), (7, 2.2, 3.5))
    mb.cyl(M_STEELD, (0, -15.5, 0), (0, 15.5, 0), 1.2, 16)
    mb.finish("dishasm", mtx=TILT)
    # ---------- alidade + pedestal (world frame, rotated by AZ)
    mb = MB(); RZ = Matrix.Rotation(AZ, 3, "Z")
    for sy in (-14.0, 14.0):
        top = RZ @ Vector((0, sy, AXIS_H))
        for sx in (-11.0, 11.0):
            base = RZ @ Vector((sx, sy * 0.9, 12.5))
            mb.truss(M_STEEL, base, top + RZ @ Vector((sx * 0.12, 0, -1.5)), 2.6, 8, 0.2, up=RZ @ Vector((0, 1, 0)))
        mb.box(M_STEELD, top, (5, 3.2, 4.5), RZ)
        mb.truss(M_STEEL, RZ @ Vector((-11, sy * 0.9, 12.5)), RZ @ Vector((11, sy * 0.9, 12.5)), 2.2, 8, 0.18)
        mb.truss(M_STEEL, RZ @ Vector((-5.5, sy * 0.95, 25)), RZ @ Vector((5.5, sy * 0.95, 25)), 1.6, 5, 0.14)
    for sx in (-11.0, 11.0):
        mb.truss(M_STEEL, RZ @ Vector((sx, -12.6, 12.5)), RZ @ Vector((sx, 12.6, 12.5)), 2.2, 9, 0.18)
        mb.truss(M_STEEL, RZ @ Vector((sx, -12.6, 12.5)), RZ @ Vector((-sx, 12.6, 12.5)), 1.5, 12, 0.14)
    mb.box(M_STEEL, RZ @ Vector((9, 0, 15.5)), (7, 9, 4.5), RZ)                       # equipment room on the alidade
    for k in range(4): mb.box(M_WIN, RZ @ Vector((12.52, -3 + 2 * k, 16.0)), (0.05, 1.1, 0.9), RZ)
    # stairs / railing ring
    for k in range(60):
        a0 = 2 * math.pi * k / 60; a1 = 2 * math.pi * (k + 1) / 60
        for hh in (11.3, 12.0):
            mb.cyl(M_STEELD, (math.cos(a0) * 15.6, math.sin(a0) * 15.6, hh), (math.cos(a1) * 15.6, math.sin(a1) * 15.6, hh), 0.05, 4)
        mb.cyl(M_STEELD, (math.cos(a0) * 15.6, math.sin(a0) * 15.6, 10.5), (math.cos(a0) * 15.6, math.sin(a0) * 15.6, 12.0), 0.05, 4)
    mb.cyl(M_CONC, (0, 0, 0), (0, 0, 10.0), 15.0, 64)
    mb.cyl(M_CONC, (0, 0, 10.0), (0, 0, 10.6), 16.0, 64)
    mb.cyl(M_STEELD, (0, 0, 10.6), (0, 0, 11.6), 13.5, 64)
    for k in range(10):
        a0 = 2 * math.pi * k / 10 + 0.2
        mb.box(M_WIN if k % 3 else M_STEELD, (math.cos(a0) * 15.02, math.sin(a0) * 15.02, 6.5), (0.1, 1.3, 1.0), Matrix.Rotation(a0, 3, "Z"))
    mb.box(M_STEELD, (math.cos(-1.9) * 15.05, math.sin(-1.9) * 15.05, 1.3), (0.2, 2.2, 2.6), Matrix.Rotation(-1.9, 3, "Z"))
    # small buildings, lamp posts, fence
    rg = np.random.default_rng(4)
    for (x, y, sx, sy, h) in ((-42, -18, 16, 9, 4.5), (-60, 6, 10, 8, 3.5), (34, -30, 12, 7, 4), (48, 12, 8, 6, 3.2)):
        mb.box(M_CONC, (x, y, h / 2), (sx, sy, h))
        for k in range(int(sx / 3)):
            mb.box(M_WIN if rg.random() < 0.6 else M_STEELD, (x - sx / 2 + 1.5 + k * 3, y - sy / 2 - 0.03, h * 0.55), (1.2, 0.06, 1.0))
    for (x, y) in ((-25, -34), (8, -40), (30, -22), (-50, -30), (22, 20), (-30, 22)):
        mb.cyl(M_STEELD, (x, y, 0), (x, y, 9), 0.12, 6); mb.box(M_LAMP, (x, y, 9.0), (0.9, 0.35, 0.12))
        ld = bpy.data.lights.new("l", "SPOT"); ld.energy = 26000; ld.color = (1.0, 0.68, 0.36); ld.spot_size = math.radians(150); ld.spot_blend = 0.8
        ld.shadow_soft_size = 0.3
        ob = link(bpy.data.objects.new("l", ld)); ob.location = (x, y, 8.7)
    mb.box(M_ROAD, (0, -52, 0.03), (240, 7, 0.06))
    mb.finish("ground_objs")
    # up-lights on the structure (warm, as work lights) and a cool moon
    for (x, y, z, e) in ((-22, -22, 2, 95000), (24, -16, 2, 70000), (0, 0, 13, 40000)):
        ld = bpy.data.lights.new("up", "SPOT"); ld.energy = e; ld.color = (1.0, 0.8, 0.55); ld.spot_size = math.radians(75); ld.spot_blend = 0.6
        ob = link(bpy.data.objects.new("up", ld)); ob.location = (x, y, z)
        ob.rotation_euler = (Vector((x, y, z)) - Vector((0, 0, 44))).to_track_quat("Z", "Y").to_euler()
    ld = bpy.data.lights.new("moon", "SUN"); ld.energy = 0.55; ld.color = (0.55, 0.68, 1.0); ld.angle = math.radians(1.5)
    ob = link(bpy.data.objects.new("moon", ld)); ob.rotation_euler = Vector((-0.75, -0.25, 0.55)).to_track_quat("Z", "Y").to_euler()
    # ---------- terrain: desert floor with low dunes and a far ridge
    n = 500; xs = np.linspace(-900, 900, n); ys = np.linspace(-300, 1500, n); X, Y = np.meshgrid(xs, ys)
    rg = np.random.default_rng(9); Z = np.zeros_like(X)
    for o in range(6):
        fq = 0.004 * 2 ** o
        for k in range(4):
            th = rg.uniform(0, 6.28); Z += (1.6 / 2 ** o) * np.sin((X * math.cos(th) + Y * math.sin(th)) * fq * 6.28 + rg.uniform(0, 6.28))
    d0 = np.hypot(X, Y); Z *= np.clip((d0 - 90) / 250, 0, 1) ** 1.5
    ridge = np.clip((Y - 600) / 500, 0, 1) ** 1.6 * (110 + 60 * np.sin(X * 0.006 + 1) + 35 * np.sin(X * 0.017 + 2) + 14 * np.sin(X * 0.05))
    Z = Z * 1.2 + ridge
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1); idx = np.arange(n * n).reshape(n, n)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me = bpy.data.meshes.new("terrain"); me.from_pydata(verts.tolist(), [], faces.tolist()); me.materials.append(M_GROUND)
    for p in me.polygons: p.use_smooth = True
    link(bpy.data.objects.new("terrain", me))
    # scrub bushes (dark low blobs)
    mb = MB(); M_BUSH = mat("bush", (0.03, 0.035, 0.02), rough=1.0)
    for _ in range(500):
        x, y = rg.uniform(-250, 250), rg.uniform(-140, 260)
        if math.hypot(x, y) < 28 or abs(y + 52) < 6: continue
        s0 = rg.uniform(0.5, 1.6)
        bmesh.ops.create_icosphere(mb.get(M_BUSH), subdivisions=1, radius=s0, matrix=Matrix.Translation((x, y, s0 * 0.3)) @ Matrix.Diagonal((1, 1, 0.6, 1)))
    mb.finish("bush")


build()
cd = bpy.data.cameras.new("cam"); cd.lens = 26; cd.sensor_width = 36; cd.clip_start = 0.5; cd.clip_end = 5000
cam = link(bpy.data.objects.new("cam", cd)); sc.camera = cam
loc = Vector((-58, -118, 3.2)); tgt = Vector((6, 0, 47))
cam.location = loc; cam.rotation_euler = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
out = os.path.join(SCR, "plates", "plate_dsn"); os.makedirs(out, exist_ok=True)
bpy.context.view_layer.update()
json.dump(dict(R=[list(r) for r in cam.matrix_world.to_3x3()], lens=26, boresight=list((TILT.to_3x3() @ Vector((0, 0, 1))))), open(os.path.join(out, "cam.json"), "w"))
if MODE == "final":
    sc.render.resolution_x, sc.render.resolution_y = 2880, 1620; sc.cycles.samples = 200
    sc.render.filepath = os.path.join(out, "0000.png")
else:
    sc.render.resolution_x, sc.render.resolution_y = 960, 540; sc.cycles.samples = 32
    sc.render.filepath = os.path.join(SCR, "chk", "test_dsn.png")
bpy.ops.render.render(write_still=True)
