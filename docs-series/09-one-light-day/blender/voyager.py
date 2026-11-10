"""ONE LIGHT-DAY FROM HOME - stylised-but-detailed Voyager model + renders (Blender 5.1.2 bpy module, Cycles CPU).

Our own model built from numbers (not NASA imagery): 3.66 m high-gain dish, decagonal bus, RTG boom with three
finned units, science boom + scan platform, 13 m magnetometer lattice boom, two 10 m whip antennas, golden record.
+Z is the dish boresight (towards Earth / the Sun).  Film is transparent; stars are added by the compositor from
the exported camera matrices.

Run: /home/user/bpyenv/bin/python -c "import sys;p='blender/voyager.py';sys.argv=['blender','--','SHOT','[f0]','[f1]','[step]'];exec(compile(open(p).read(),p,'exec'))"
SHOT: hero | end | sig | fly | plate_record | plate_cover | plate_rtg | plate_thumb | test
"""
import bpy, bmesh, math, sys, os, json
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHOT = argv[0] if argv else "test"
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day"
TEX = os.path.join(SCR, "tex")

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 3
sc.cycles.diffuse_bounces = 1
sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 0
sc.cycles.transparent_max_bounces = 2
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.cycles.sample_clamp_indirect = 4.0
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.03
sc.render.film_transparent = True
sc.view_settings.view_transform = "Filmic" if "Filmic" in [i.identifier for i in type(sc.view_settings).bl_rna.properties["view_transform"].enum_items] else "AgX"
sc.view_settings.look = "None"
sc.render.filter_size = 1.3
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.color_depth = "8"
sc.render.image_settings.compression = 30
sc.render.use_persistent_data = True
sc.render.threads_mode = "FIXED"
sc.render.threads = int(os.environ.get("THREADS", "2"))
sc.render.fps = 24

# world: faint cool ambient with a brighter band (Milky Way stand-in) so metals have something to reflect
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
nt = w.node_tree; bg = nt.nodes["Background"]
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = (0.010, 0.014, 0.024, 1)
ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (0.010, 0.014, 0.024, 1)
e = ramp.color_ramp.elements.new(0.5); e.color = (0.10, 0.11, 0.14, 1)
e = ramp.color_ramp.elements.new(0.42); e.color = (0.014, 0.018, 0.03, 1)
e = ramp.color_ramp.elements.new(0.58); e.color = (0.014, 0.018, 0.03, 1)
mp = nt.nodes.new("ShaderNodeMapRange"); mp.inputs[1].default_value = -1; mp.inputs[2].default_value = 1
# band along the plane x*0.5 + y*0.3 + z*0.8 = 0  (arbitrary galactic plane, the compositor uses the same normal)
GAL_N = Vector((0.45, 0.35, 0.82)).normalized()
dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = "DOT_PRODUCT"; dot.inputs[1].default_value = GAL_N
nt.links.new(tc.outputs["Generated"], dot.inputs[0]); nt.links.new(dot.outputs["Value"], mp.inputs[0])
nt.links.new(mp.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 1.0

COL = bpy.context.scene.collection


def link(ob):
    COL.objects.link(ob); return ob


# ------------------------------------------------------------------------------------------- materials
def mat(name, col, rough=0.5, metal=0.0, bump=0.0, bscale=30.0, coat=0.0, emit=None, es=0.0, bdetail=3.0,
        crinkle=0.0, cscale=14.0, wear=0.12, bevel=0.004):
    """Principled material with: roughness/albedo wear variation (noise), optional fine bump, optional crinkled-foil
    normal (Voronoi distance-to-edge facets + noise warp), and rounded edges via the Cycles Bevel node."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    t = m.node_tree; b = t.nodes["Principled BSDF"]
    L = t.links.new
    tcn = t.nodes.new("ShaderNodeTexCoord")
    b.inputs["Metallic"].default_value = metal
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = es
    # wear: large + small noise drives roughness and darkens albedo slightly
    wn = t.nodes.new("ShaderNodeTexNoise"); wn.inputs["Scale"].default_value = 3.5; wn.inputs["Detail"].default_value = 8.0
    wn.inputs["Roughness"].default_value = 0.7
    L(tcn.outputs["Object"], wn.inputs["Vector"])
    mr = t.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.3; mr.inputs[2].default_value = 0.75
    mr.inputs[3].default_value = max(0.03, rough - wear); mr.inputs[4].default_value = min(1.0, rough + wear * 1.6)
    L(wn.outputs["Fac"], mr.inputs[0]); L(mr.outputs[0], b.inputs["Roughness"])
    mx = t.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (*col, 1); mx.inputs["B"].default_value = (*[c * 0.55 for c in col], 1)
    mr2 = t.nodes.new("ShaderNodeMapRange"); mr2.inputs[1].default_value = 0.45; mr2.inputs[2].default_value = 0.8
    L(wn.outputs["Fac"], mr2.inputs[0]); L(mr2.outputs[0], mx.inputs["Factor"]); L(mx.outputs["Result"], b.inputs["Base Color"])
    normal = None
    if bevel > 0:
        bv = t.nodes.new("ShaderNodeBevel"); bv.samples = 2; bv.inputs["Radius"].default_value = bevel
        normal = bv.outputs["Normal"]
    if crinkle > 0:
        nz = t.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = cscale * 0.5; nz.inputs["Detail"].default_value = 2.0
        L(tcn.outputs["Object"], nz.inputs["Vector"])
        mxv = t.nodes.new("ShaderNodeMix"); mxv.data_type = "VECTOR"; mxv.inputs["Factor"].default_value = 0.12
        L(tcn.outputs["Object"], mxv.inputs["A"]); L(nz.outputs["Color"], mxv.inputs["B"])
        vo = t.nodes.new("ShaderNodeTexVoronoi"); vo.feature = "DISTANCE_TO_EDGE"; vo.inputs["Scale"].default_value = cscale
        L(mxv.outputs["Result"], vo.inputs["Vector"])
        vo2 = t.nodes.new("ShaderNodeTexVoronoi"); vo2.feature = "F1"; vo2.inputs["Scale"].default_value = cscale * 2.7
        L(mxv.outputs["Result"], vo2.inputs["Vector"])
        ad = t.nodes.new("ShaderNodeMath"); ad.operation = "ADD"
        L(vo.outputs["Distance"], ad.inputs[0]); L(vo2.outputs["Distance"], ad.inputs[1])
        bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = crinkle; bp.inputs["Distance"].default_value = 0.03
        L(ad.outputs[0], bp.inputs["Height"])
        if normal is not None: L(normal, bp.inputs["Normal"])
        normal = bp.outputs["Normal"]
    if bump > 0:
        n = t.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = bscale
        n.inputs["Detail"].default_value = bdetail; n.inputs["Roughness"].default_value = 0.6
        L(tcn.outputs["Object"], n.inputs["Vector"])
        bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump; bp.inputs["Distance"].default_value = 0.01
        L(n.outputs["Fac"], bp.inputs["Height"])
        if normal is not None: L(normal, bp.inputs["Normal"])
        normal = bp.outputs["Normal"]
    if normal is not None:
        L(normal, b.inputs["Normal"])
    return m


M_WHITE = mat("white", (0.78, 0.78, 0.76), rough=0.55, bump=0.05, bscale=40)
M_WHITEB = mat("whiteback", (0.60, 0.60, 0.58), rough=0.6, bump=0.05, bscale=40)
M_BLACK = mat("blanket", (0.016, 0.016, 0.018), rough=0.30, crinkle=0.85, cscale=13, coat=0.25, wear=0.14)
M_GOLDFOIL = mat("goldfoil", (1.0, 0.60, 0.20), rough=0.22, metal=1.0, crinkle=0.9, cscale=16, wear=0.12)
M_GOLD = mat("gold", (1.0, 0.72, 0.30), rough=0.2, metal=1.0, wear=0.08)
M_ALU = mat("alu", (0.78, 0.79, 0.80), rough=0.33, metal=1.0, bump=0.03, bscale=120)
M_ALUD = mat("aludark", (0.26, 0.27, 0.29), rough=0.42, metal=1.0, bump=0.04, bscale=90)
M_TRUSS = mat("truss", (0.40, 0.41, 0.44), rough=0.34, metal=1.0, bevel=0.0, wear=0.1)
M_RTG = mat("rtg", (0.055, 0.055, 0.06), rough=0.46, metal=0.7, bump=0.08, bscale=160, wear=0.18)
M_RTGEND = mat("rtgend", (0.5, 0.5, 0.52), rough=0.4, metal=1.0, bump=0.04, bscale=120)
M_LENS = mat("lens", (0.01, 0.012, 0.03), rough=0.05, coat=1.0, wear=0.0, bevel=0.0)
M_WHIP = mat("whip", (0.85, 0.70, 0.42), rough=0.3, metal=1.0, bevel=0.0)
M_LOUV = mat("louver", (0.85, 0.85, 0.86), rough=0.22, metal=1.0, bevel=0.002)
M_CABLE = mat("cable", (0.75, 0.50, 0.20), rough=0.3, metal=1.0, crinkle=0.9, cscale=45, bevel=0.0)


# ------------------------------------------------------------------------------------------- mesh helpers
class MB:
    """mesh builder: accumulates primitives into one bmesh per material"""
    def __init__(self):
        self.bm = {}

    def get(self, m):
        if m.name not in self.bm:
            self.bm[m.name] = (bmesh.new(), m)
        return self.bm[m.name][0]

    def cyl(self, m, a, b, r, seg=10, r2=None, caps=True):
        bm = self.get(m); a = Vector(a); b = Vector(b); d = b - a; L = d.length
        if L < 1e-6: return
        mtx = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=L, matrix=mtx)

    def box(self, m, c, size, rot=None):
        bm = self.get(m)
        mtx = Matrix.Translation(Vector(c)) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)

    def sphere(self, m, c, r, seg=16):
        bm = self.get(m)
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r, matrix=Matrix.Translation(Vector(c)))

    def cable(self, m, pts, r=0.014, sag=0.03, seed=0, sub=6):
        rg = np.random.default_rng(seed); pts = [Vector(p) for p in pts]; out = []
        for a, b in zip(pts, pts[1:]):
            for i in range(sub):
                t = i / sub
                out.append(a.lerp(b, t) + Vector(rg.normal(0, sag * 0.35, 3)) * math.sin(math.pi * t) + Vector((0, 0, -sag)) * math.sin(math.pi * t))
        out.append(pts[-1])
        for a, b in zip(out, out[1:]):
            self.cyl(m, a, b, r, 7); self.sphere(m, b, r * 1.02, 8)

    def finish(self, name, smooth_angle=40):
        obs = []
        for k, (bm, m) in self.bm.items():
            me = bpy.data.meshes.new(name + "_" + k); bm.to_mesh(me); bm.free()
            me.materials.append(m)
            for p in me.polygons: p.use_smooth = True
            ob = link(bpy.data.objects.new(name + "_" + k, me))
            md = ob.modifiers.new("es", "EDGE_SPLIT"); md.split_angle = math.radians(smooth_angle)
            obs.append(ob)
        return obs


def truss(mb, m, a, b, wa, wb, up, bays, r=0.012, n=4):
    """n-longeron tapered truss from a to b with battens and diagonals"""
    a = Vector(a); b = Vector(b); ax = (b - a).normalized(); up = Vector(up)
    u = (up - ax * up.dot(ax)).normalized(); v = ax.cross(u)
    def ring(t):
        c = a.lerp(b, t); wdt = wa + (wb - wa) * t
        return [c + (u * math.cos(2 * math.pi * (k + 0.5) / n) + v * math.sin(2 * math.pi * (k + 0.5) / n)) * wdt for k in range(n)]
    prev = ring(0)
    for i in range(1, bays + 1):
        cur = ring(i / bays)
        for k in range(n):
            mb.cyl(m, prev[k], cur[k], r, 6)
            mb.cyl(m, cur[k], cur[(k + 1) % n], r * 0.8, 6)
            mb.cyl(m, prev[k], cur[(k + 1) % n] if i % 2 else cur[(k - 1) % n], r * 0.65, 6)
        prev = cur
    for k in range(n):
        mb.cyl(m, ring(0)[k], ring(0)[(k + 1) % n], r * 0.8, 6)


def pydata_obj(name, verts, faces, m, smooth=True, uvs=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.materials.append(m)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if uvs is not None:
        uvl = me.uv_layers.new(name="UVMap")
        for li, l in enumerate(me.loops):
            uvl.data[li].uv = uvs[l.vertex_index]
    return link(bpy.data.objects.new(name, me))


# ------------------------------------------------------------------------------------------- the spacecraft
DISH_R = 1.83; DISH_F = 1.22; DISH_Z = 0.62      # vertex height above the bus centre
BUS_R = 0.89; BUS_H = 0.47
REC_ANG = math.radians(-90 + 18)                  # bus face carrying the record (faces roughly -Y)


def dish_z(r):
    return DISH_Z + r * r / (4 * DISH_F)


def build_voyager():
    mb = MB()
    # ---------------- bus: decagonal prism + panel detail
    n = 10
    ap = BUS_R * math.cos(math.pi / n)
    for k in range(n):
        ang = 2 * math.pi * k / n + math.radians(18)
        c = Vector((math.cos(ang) * ap, math.sin(ang) * ap, 0))
        rot = Matrix.Rotation(ang, 3, "Z")
        wface = 2 * BUS_R * math.sin(math.pi / n)
        mb.box(M_BLACK, c * 0.5, (ap, wface, BUS_H), rot)                      # wedge-ish filler (overlaps; fine)
        mb.box(M_ALUD, c * 1.004, (0.012, wface * 1.0, BUS_H * 1.02), rot)      # frame
        mb.box(M_BLACK, c * 1.012, (0.014, wface * 0.90, BUS_H * 0.88), rot)    # blanket panel
        if k in (1, 4, 6, 8):                                                   # louvers
            for j in range(7):
                z = (j - 3) * 0.052
                mb.box(M_LOUV, c * 1.024 + Vector((0, 0, z)), (0.01, wface * 0.62, 0.036), rot @ Matrix.Rotation(0.5, 3, "Y"))
        mb.cyl(M_ALU, (math.cos(ang + math.pi / n) * BUS_R, math.sin(ang + math.pi / n) * BUS_R, -BUS_H / 2),
               (math.cos(ang + math.pi / n) * BUS_R, math.sin(ang + math.pi / n) * BUS_R, BUS_H / 2), 0.018, 8)
    mb.cyl(M_BLACK, (0, 0, -BUS_H / 2 - 0.01), (0, 0, BUS_H / 2 + 0.01), ap * 0.99, 10)
    rg = np.random.default_rng(5)
    for k in range(n):                                                          # frame bolts, deck boxes, harness loops
        ang = 2 * math.pi * k / n + math.radians(18)
        rot = Matrix.Rotation(ang, 3, "Z"); wface = 2 * BUS_R * math.sin(math.pi / n)
        for sy in (-0.42, -0.2, 0.0, 0.2, 0.42):
            for sz in (-0.47, 0.47):
                pb = rot @ Vector((ap * 1.008, sy * wface, sz * BUS_H))
                mb.cyl(M_ALU, pb, pb + rot @ Vector((0.012, 0, 0)), 0.007, 6)
        if rg.random() < 0.7:
            pb = rot @ Vector((ap * 0.72, rg.uniform(-0.1, 0.1), BUS_H / 2 + 0.05))
            mb.box(M_GOLDFOIL if rg.random() < 0.5 else M_ALUD, pb, (rg.uniform(0.1, 0.2), rg.uniform(0.12, 0.25), 0.1), rot)
        mb.cable(M_CABLE if k % 2 else M_BLACK, [rot @ Vector((ap * 0.95, -wface * 0.5, BUS_H / 2 + 0.02)), rot @ Vector((ap * 0.97, 0, BUS_H / 2 + 0.035)),
                                                 rot @ Vector((ap * 0.95, wface * 0.5, BUS_H / 2 + 0.02))], 0.012, 0.015, 10 + k, sub=4)
    for ang in (1.0, 1.35):                                                     # star trackers on the top deck
        pb = Vector((math.cos(ang) * 0.62, math.sin(ang) * 0.62, BUS_H / 2))
        mb.cyl(M_BLACK, pb, pb + Vector((math.cos(ang) * 0.1, math.sin(ang) * 0.1, 0.34)), 0.06, 14)
        mb.cyl(M_LENS, pb + Vector((math.cos(ang) * 0.1, math.sin(ang) * 0.1, 0.34)), pb + Vector((math.cos(ang) * 0.101, math.sin(ang) * 0.101, 0.343)), 0.05, 14)
    mb.sphere(M_GOLDFOIL, (0, 0, -0.16), 0.36, 20)                             # propellant tank bulging below
    # thruster clusters
    for ang in (0.6, 2.2, 3.75, 5.3):
        p = Vector((math.cos(ang) * (BUS_R + 0.08), math.sin(ang) * (BUS_R + 0.08), -BUS_H / 2 - 0.03))
        mb.box(M_ALUD, p, (0.09, 0.09, 0.07), Matrix.Rotation(ang, 3, "Z"))
        for dz in (-1, 1):
            mb.cyl(M_ALU, p + Vector((0, 0, -0.03)), p + Vector((math.cos(ang + dz) * 0.07, math.sin(ang + dz) * 0.07, -0.09)), 0.012, 8, r2=0.024)
    # support truss stub below the bus (propulsion-module adapter)
    ringz = -0.85
    for k in range(8):
        a0 = 2 * math.pi * k / 8
        top = Vector((math.cos(a0) * 0.8, math.sin(a0) * 0.8, -BUS_H / 2))
        for da in (-0.5, 0.5):
            a1 = 2 * math.pi * (k + da) / 8
            mb.cyl(M_TRUSS, top, (math.cos(a1) * 0.42, math.sin(a1) * 0.42, ringz), 0.012, 6)
        a1 = 2 * math.pi * (k + 0.5) / 8; a2 = 2 * math.pi * (k + 1.5) / 8
        mb.cyl(M_TRUSS, (math.cos(a1) * 0.42, math.sin(a1) * 0.42, ringz), (math.cos(a2) * 0.42, math.sin(a2) * 0.42, ringz), 0.014, 6)
    # ---------------- dish support struts
    for k in range(n):
        a0 = 2 * math.pi * k / n + math.radians(18) + math.pi / n
        base = Vector((math.cos(a0) * BUS_R * 0.97, math.sin(a0) * BUS_R * 0.97, BUS_H / 2))
        for da in (-0.5, 0.5):
            a1 = a0 + da * 2 * math.pi / n; rr = 1.12
            mb.cyl(M_TRUSS, base, (math.cos(a1) * rr, math.sin(a1) * rr, dish_z(rr) - 0.03), 0.013, 6)
    # ---------------- dish back ribs + rim
    for k in range(24):
        a0 = 2 * math.pi * k / 24
        prev = None
        for r in np.linspace(0.3, DISH_R - 0.01, 9):
            p = Vector((math.cos(a0) * r, math.sin(a0) * r, dish_z(r) - 0.02))
            if prev is not None: mb.cyl(M_WHITEB, prev, p, 0.011, 5)
            prev = p
    for rr in (0.3, 1.12, DISH_R):
        prev = None
        for k in range(49):
            a0 = 2 * math.pi * k / 48
            p = Vector((math.cos(a0) * rr, math.sin(a0) * rr, dish_z(rr) - (0.02 if rr < DISH_R else 0.0)))
            if prev is not None: mb.cyl(M_WHITEB if rr < DISH_R else M_ALU, prev, p, 0.014 if rr < DISH_R else 0.016, 6)
            prev = p
    # ---------------- feed, subreflector, struts, low-gain antenna
    sub_z = DISH_Z + 1.06
    mb.cyl(M_ALU, (0, 0, DISH_Z), (0, 0, DISH_Z + 0.10), 0.20, 24)
    mb.cyl(M_WHITE, (0, 0, DISH_Z + 0.10), (0, 0, DISH_Z + 0.52), 0.10, 24, r2=0.19, caps=False)
    mb.cyl(M_ALUD, (0, 0, DISH_Z + 0.10), (0, 0, DISH_Z + 0.50), 0.095, 24, r2=0.18)
    mb.cyl(M_WHITE, (0, 0, sub_z), (0, 0, sub_z + 0.07), 0.25, 32, r2=0.27)
    mb.cyl(M_ALU, (0, 0, sub_z - 0.05), (0, 0, sub_z), 0.06, 32, r2=0.25)
    mb.cyl(M_ALU, (0, 0, sub_z + 0.07), (0, 0, sub_z + 0.30), 0.045, 16)        # low-gain antenna
    mb.cyl(M_WHITE, (0, 0, sub_z + 0.30), (0, 0, sub_z + 0.34), 0.085, 16)
    for k in range(3):
        a0 = 2 * math.pi * k / 3 + 0.3
        for da in (-0.16, 0.16):
            rr = 1.25
            mb.cyl(M_TRUSS, (math.cos(a0 + da) * rr, math.sin(a0 + da) * rr, dish_z(rr)),
                   (math.cos(a0) * 0.26, math.sin(a0) * 0.26, sub_z + 0.03), 0.011, 6)
    # ---------------- RTG boom (-X, drooping slightly)
    d = Vector((-1, 0.0, -0.20)).normalized(); up = Vector((0, 0, 1))
    a = Vector((-BUS_R * 0.95, 0, -0.05)); b = a + d * 1.55
    truss(mb, M_TRUSS, a, b, 0.24, 0.14, up, 5, r=0.013)
    side = d.cross(up).normalized()
    p = b + d * 0.06
    for i in range(3):
        q = p + d * 0.50
        mb.cyl(M_RTG, p, q, 0.115, 20)
        for k in range(6):                                                      # radiator fins
            ang = 2 * math.pi * k / 6
            fdir = (side * math.cos(ang) + d.cross(side).normalized() * math.sin(ang))
            rot = Matrix((d, fdir, d.cross(fdir))).transposed()
            mb.box(M_RTG, (p + q) / 2 + fdir * 0.17, (0.46, 0.13, 0.008), rot)
        mb.cyl(M_RTGEND, p - d * 0.02, p, 0.125, 20); mb.cyl(M_RTGEND, q, q + d * 0.02, 0.125, 20)
        for j in range(1, 8):                                                   # circumferential ribs between the fins
            c0 = p + d * (0.5 * j / 8)
            mb.cyl(M_RTG, c0 - d * 0.004, c0 + d * 0.004, 0.121, 20)
        for k in range(12):                                                     # end-flange bolts
            ang = 2 * math.pi * k / 12
            fdir = (side * math.cos(ang) + d.cross(side).normalized() * math.sin(ang))
            mb.cyl(M_ALUD, p - d * 0.028 + fdir * 0.108, p - d * 0.018 + fdir * 0.108, 0.008, 6)
            mb.cyl(M_ALUD, q + d * 0.018 + fdir * 0.108, q + d * 0.028 + fdir * 0.108, 0.008, 6)
        for k in range(6):                                                      # fin edge stiffeners
            ang = 2 * math.pi * k / 6
            fdir = (side * math.cos(ang) + d.cross(side).normalized() * math.sin(ang))
            mb.cyl(M_RTGEND, p + d * 0.02 + fdir * 0.235, q - d * 0.02 + fdir * 0.235, 0.006, 6)
        mb.cyl(M_ALUD, q + d * 0.02, q + d * 0.06, 0.05, 12)
        p = q + d * 0.06
    mb.cyl(M_RTGEND, p - d * 0.04, p, 0.09, 16, r2=0.03)
    # cable harnesses along the booms
    mb.cable(M_CABLE, [a + Vector((0, 0.1, 0.1)), a + d * 0.5 + Vector((0, 0.12, 0.12)), a + d * 1.0 + Vector((0, 0.1, 0.1)), b + Vector((0, 0.06, 0.08)), b + d * 0.12], 0.016, 0.03, 1)
    mb.cable(M_BLACK, [a + Vector((0, -0.1, 0.12)), a + d * 0.8 + Vector((0, -0.1, 0.1)), b + Vector((0, -0.05, 0.08))], 0.011, 0.04, 2)
    # ---------------- science boom (+X) with instruments and scan platform
    d2 = Vector((1, 0.0, 0.10)).normalized()
    a = Vector((BUS_R * 0.95, 0, 0.0)); b = a + d2 * 2.3
    truss(mb, M_TRUSS, a, b, 0.22, 0.13, up, 7, r=0.012)
    mb.cable(M_CABLE, [a + Vector((0, 0.09, 0.12)), a + d2 * 0.6 + Vector((0, 0.1, 0.1)), a + d2 * 1.15 + Vector((0, 0.14, 0.1)), a + d2 * 1.8 + Vector((0, 0.06, 0.08)), b + Vector((0.05, 0, -0.1))], 0.015, 0.03, 3)
    mb.cable(M_BLACK, [a + Vector((0, -0.09, 0.11)), a + d2 * 1.2 + Vector((0, -0.12, 0.08)), a + d2 * 1.6 + Vector((0, -0.2, 0.0))], 0.011, 0.04, 4)
    mid = a + d2 * 1.15
    mb.box(M_BLACK, mid + Vector((0, 0.27, 0.05)), (0.30, 0.24, 0.26))          # cosmic ray system
    mb.cyl(M_ALU, mid + Vector((0, 0.38, 0.12)), mid + Vector((0.0, 0.52, 0.22)), 0.045, 12)
    mb.cyl(M_ALU, mid + Vector((0.08, 0.38, 0.05)), mid + Vector((0.20, 0.5, 0.0)), 0.04, 12)
    mb.box(M_GOLDFOIL, mid + Vector((0.45, -0.25, 0.0)), (0.22, 0.2, 0.22))     # LECP
    mb.cyl(M_ALUD, mid + Vector((0.45, -0.36, 0.0)), mid + Vector((0.45, -0.50, 0.04)), 0.07, 14)
    pl = a + d2 * 1.9 + Vector((0, 0, 0.26))                                    # plasma detector
    mb.cyl(M_GOLDFOIL, pl, pl + Vector((0.05, 0, 0.16)), 0.14, 16)
    mb.cyl(M_ALUD, pl + Vector((0.05, 0, 0.16)), pl + Vector((0.055, 0, 0.18)), 0.12, 16)
    sp = b + Vector((0.12, 0, -0.42))                                           # scan platform
    mb.cyl(M_ALUD, b, sp + Vector((0, 0, 0.2)), 0.05, 12)
    mb.box(M_BLACK, sp, (0.5, 0.62, 0.36))
    look = Vector((0.25, -1, 0.1)).normalized()
    c0 = sp + Vector((0.12, -0.3, 0.10))
    mb.cyl(M_WHITE, c0, c0 + look * 0.85, 0.095, 20); mb.cyl(M_LENS, c0 + look * 0.85, c0 + look * 0.855, 0.085, 20)
    mb.cyl(M_ALU, c0 + look * 0.80, c0 + look * 0.87, 0.105, 20, caps=False)
    c1 = sp + Vector((-0.14, -0.3, 0.12))
    mb.cyl(M_BLACK, c1, c1 + look * 0.32, 0.06, 16); mb.cyl(M_LENS, c1 + look * 0.32, c1 + look * 0.325, 0.05, 16)
    c2 = sp + Vector((0.0, -0.25, -0.30))                                       # IRIS: gold telescope dish
    mb.cyl(M_GOLDFOIL, c2, c2 + look * 0.30, 0.14, 20, r2=0.26)
    mb.cyl(M_GOLD, c2 + look * 0.30, c2 + look * 0.31, 0.26, 24)
    mb.cyl(M_ALUD, c2 + look * 0.31, c2 + look * 0.45, 0.04, 10)
    mb.box(M_GOLDFOIL, sp + Vector((0.2, 0.42, 0.0)), (0.2, 0.34, 0.2))         # UVS
    mb.cyl(M_ALU, sp + Vector((-0.2, 0.3, 0.0)), sp + Vector((-0.2, 0.3, 0.0)) + look * (-0.3), 0.05, 12)
    # ---------------- magnetometer boom: 13 m triangular lattice
    m0 = Vector((-0.55, 0.62, -0.05)); md = Vector((-0.42, 0.88, -0.22)).normalized(); m1 = m0 + md * 13.0
    truss(mb, M_TRUSS, m0, m1, 0.115, 0.115, up, 44, r=0.0075, n=3)
    for t in (0.52, 1.0):
        c = m0.lerp(m1, t)
        mb.box(M_GOLDFOIL, c + Vector((0, 0, 0.0)), (0.16, 0.16, 0.16), md.to_track_quat("X", "Z").to_matrix())
    # ---------------- two 10 m whip antennas (planetary radio astronomy / plasma wave), 90 degrees apart
    w0 = Vector((0.25, 0.55, -BUS_H / 2 - 0.05))
    base_dir = Vector((0.55, 0.75, -0.36)).normalized(); perp = base_dir.cross(Vector((0.2, -0.1, 1))).normalized()
    for sgn in (-1, 1):
        dd = (base_dir + perp * sgn).normalized()
        mb.cyl(M_WHIP, w0, w0 + dd * 10.0, 0.0075, 6)
    mb.box(M_ALUD, w0, (0.14, 0.14, 0.12))
    # ---------------- calibration target / radiator plate under the RTG side
    mb.box(M_ALUD, (-0.55, -0.55, -0.62), (0.55, 0.36, 0.012), Matrix.Rotation(0.5, 3, "X"))
    mb.cyl(M_TRUSS, (-0.5, -0.5, -BUS_H / 2), (-0.55, -0.5, -0.6), 0.01, 6)
    mb.cyl(M_TRUSS, (-0.7, -0.6, -BUS_H / 2), (-0.6, -0.6, -0.62), 0.01, 6)
    obs = mb.finish("voy")

    # ---------------- dish surface (double-sided shell)
    nr, na = 40, 96
    verts, faces = [], []
    for i in range(nr + 1):
        r = 0.2 + (DISH_R - 0.2) * i / nr
        for j in range(na):
            a0 = 2 * math.pi * j / na
            verts.append((r * math.cos(a0), r * math.sin(a0), dish_z(r)))
    for i in range(nr):
        for j in range(na):
            faces.append((i * na + j, i * na + (j + 1) % na, (i + 1) * na + (j + 1) % na, (i + 1) * na + j))
    duv = [(0.5 + v[0] / (2 * DISH_R) * 0.98, 0.5 + v[1] / (2 * DISH_R) * 0.98) for v in verts]
    dish = pydata_obj("dish", verts, faces, dish_material(), uvs=duv)
    sm = dish.modifiers.new("sol", "SOLIDIFY"); sm.thickness = 0.012; sm.offset = -1
    obs.append(dish)

    # ---------------- golden record on the bus face
    ang = REC_ANG
    nrm = Vector((math.cos(ang), math.sin(ang), 0)); tan = Vector((-math.sin(ang), math.cos(ang), 0))
    c = nrm * (ap + 0.03)
    mrec = record_material()
    R = 0.152
    nseg = 96; verts = [tuple(c + nrm * 0.034)]; uvs = [(0.5, 0.5)]
    for j in range(nseg):
        a0 = 2 * math.pi * j / nseg
        verts.append(tuple(c + nrm * 0.034 + (tan * math.cos(a0) + Vector((0, 0, 1)) * math.sin(a0)) * R))
        uvs.append((0.5 + 0.5 * math.cos(a0), 0.5 + 0.5 * math.sin(a0)))
    faces = [(0, 1 + j, 1 + (j + 1) % nseg) for j in range(nseg)]
    rec = pydata_obj("record", verts, faces, mrec, smooth=False, uvs=uvs)
    obs.append(rec)
    mb2 = MB()
    mb2.cyl(M_GOLD, c + nrm * 0.004, c + nrm * 0.0335, R + 0.004, 96)
    mb2.cyl(M_ALU, c - nrm * 0.02, c + nrm * 0.004, R + 0.03, 48)
    for k in range(3):
        a0 = 2 * math.pi * k / 3 + 0.5
        p = c + (tan * math.cos(a0) + Vector((0, 0, 1)) * math.sin(a0)) * (R + 0.017)
        mb2.cyl(M_ALUD, p + nrm * 0.0, p + nrm * 0.045, 0.011, 6)
    obs += mb2.finish("recmount")
    root = bpy.data.objects.new("voyager", None); link(root)
    for o in obs: o.parent = root
    return root


def dish_material():
    """white painted reflector: gore seams, ring seams, fastener dots and faint stains baked with numpy"""
    path = os.path.join(TEX, "dish.png"); N = 2048
    if not os.path.exists(path):
        yy, xx = np.mgrid[0:N, 0:N].astype(np.float32); x = (xx / N - 0.5) / 0.49; y = (yy / N - 0.5) / 0.49
        r = np.hypot(x, y); th = np.arctan2(y, x)
        seam = np.zeros((N, N), np.float32)
        g = np.abs(((th / (2 * math.pi) * 24 + 0.5) % 1.0) - 0.5) * (2 * math.pi / 24) * np.maximum(r, 0.05)
        seam = np.maximum(seam, np.clip(1 - g / 0.0035, 0, 1))
        for rr in (0.17, 0.42, 0.61, 0.82, 0.985):
            seam = np.maximum(seam, np.clip(1 - np.abs(r - rr) / 0.0035, 0, 1))
        dots = np.clip(1 - np.hypot(((th / (2 * math.pi) * 24 + 0.5) % 1.0 - 0.5) * (2 * math.pi / 24) * r, ((r * 28) % 1.0 - 0.5) / 28) / 0.004, 0, 1)
        rg = np.random.default_rng(3); f = np.fft.fftfreq(N) * N; kx, ky = np.meshgrid(f, f); k = np.hypot(kx, ky)
        nz = np.real(np.fft.ifft2(np.fft.fft2(rg.standard_normal((N, N))) * np.where(k < 2, 0, (k + 1e-6) ** -1.5))); nz = (nz - nz.min()) / (nz.max() - nz.min())
        panel = (np.floor(th / (2 * math.pi) * 24 + 0.5) * 7 + np.searchsorted([0.17, 0.42, 0.61, 0.82], r) * 13) % 5 / 5.0
        alb = 1.0 - 0.45 * seam - 0.25 * dots - 0.22 * np.clip(nz - 0.45, 0, 1) - 0.05 * panel
        img = np.stack([alb, np.clip(seam + dots * 0.6, 0, 1), nz, np.ones_like(alb)], -1)
        im = bpy.data.images.new("dish", N, N, alpha=False); im.pixels.foreach_set(np.ascontiguousarray(img, np.float32).ravel())
        im.filepath_raw = path; im.file_format = "PNG"; im.save(); bpy.data.images.remove(im)
    m = bpy.data.materials.new("dish"); m.use_nodes = True
    t = m.node_tree; b = t.nodes["Principled BSDF"]; L = t.links.new
    img = t.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(path); img.image.colorspace_settings.name = "Non-Color"
    sp = t.nodes.new("ShaderNodeSeparateColor"); L(img.outputs["Color"], sp.inputs[0])
    mx = t.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs["A"].default_value = (0.06, 0.06, 0.06, 1); mx.inputs["B"].default_value = (0.70, 0.70, 0.68, 1)
    L(sp.outputs[0], mx.inputs["Factor"]); L(mx.outputs["Result"], b.inputs["Base Color"])
    mr = t.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = 0.42; mr.inputs[4].default_value = 0.7
    L(sp.outputs[2], mr.inputs[0]); L(mr.outputs[0], b.inputs["Roughness"])
    bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.004; bp.invert = True
    L(sp.outputs[1], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def record_material():
    """gold cover with our own engraved diagram texture (tex/record_cover.png made by make_record_tex)"""
    path = os.path.join(TEX, "record_cover.png")
    if not os.path.exists(path):
        make_record_tex(path)
    m = bpy.data.materials.new("record"); m.use_nodes = True
    t = m.node_tree; b = t.nodes["Principled BSDF"]
    img = t.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(path); img.image.colorspace_settings.name = "Non-Color"
    b.inputs["Metallic"].default_value = 1.0
    mix = t.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (1.0, 0.70, 0.27, 1); mix.inputs["B"].default_value = (0.42, 0.24, 0.06, 1)
    t.links.new(img.outputs["Color"], mix.inputs["Factor"]); t.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    mr = t.nodes.new("ShaderNodeMapRange"); mr.inputs[3].default_value = 0.20; mr.inputs[4].default_value = 0.5
    t.links.new(img.outputs["Color"], mr.inputs[0]); t.links.new(mr.outputs[0], b.inputs["Roughness"])
    bp = t.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6; bp.inputs["Distance"].default_value = 0.002; bp.invert = True
    t.links.new(img.outputs["Color"], bp.inputs["Height"]); t.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def make_record_tex(path, N=2048):
    """Our own line drawing in the spirit of the record cover (record top/side view, pulsar-map style radial lines,
    two-circle hydrogen diagram, picture-frame diagrams). Stylised: not a tracing of the real engraving.
    Rasterised with numpy only (the bpy env has no PIL)."""
    img = np.zeros((N, N), np.float32)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32); xx /= N; yy /= N

    def line(x0, y0, x1, y1, w=0.0022):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy + 1e-12
        t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0, 1)
        d = np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy))
        np.maximum(img, np.clip((w - d) / 0.0012 + 0.5, 0, 1), out=img)

    def circle(cx, cy, r, w=0.0022):
        d = np.abs(np.hypot(xx - cx, yy - cy) - r)
        np.maximum(img, np.clip((w - d) / 0.0012 + 0.5, 0, 1), out=img)

    def ticks(cx, cy, r, n, seed, l=0.012):
        rg = np.random.default_rng(seed)
        for k in range(n):
            a = 2 * math.pi * k / n
            if rg.random() < 0.55:
                line(cx + math.cos(a) * r, cy + math.sin(a) * r, cx + math.cos(a) * (r + l), cy + math.sin(a) * (r + l), 0.0016)
            else:
                circle(cx + math.cos(a) * (r + l * 0.5), cy + math.sin(a) * (r + l * 0.5), 0.0025, 0.0014)

    # fine concentric machining rings over the whole cover
    rr = np.hypot(xx - 0.5, yy - 0.5)
    img += 0.10 * (0.5 + 0.5 * np.sin(rr * 2 * math.pi * 150))
    # upper-left: record seen from above with stylus + binary ticks
    circle(0.30, 0.66, 0.115); circle(0.30, 0.66, 0.045); circle(0.30, 0.66, 0.008, 0.004)
    ticks(0.30, 0.66, 0.123, 40, 1)
    line(0.385, 0.74, 0.345, 0.70); line(0.385, 0.74, 0.40, 0.725)
    # below it: record side view
    line(0.18, 0.50, 0.42, 0.50); line(0.18, 0.488, 0.42, 0.488); line(0.18, 0.50, 0.18, 0.488); line(0.42, 0.50, 0.42, 0.488)
    line(0.40, 0.512, 0.36, 0.50); ticks(0.30, 0.47, 0.0, 1, 2)
    for k in range(12):
        x = 0.19 + k * 0.02
        line(x, 0.468, x + (0.008 if k % 3 else 0.0), 0.458, 0.0016)
    # upper-right: waveform frame + picture raster frames
    def rect(x0, y0, x1, y1):
        line(x0, y0, x1, y0); line(x1, y0, x1, y1); line(x1, y1, x0, y1); line(x0, y1, x0, y0)
    rect(0.56, 0.74, 0.80, 0.80)
    px = np.linspace(0.565, 0.795, 40); rg = np.random.default_rng(4)
    py = 0.77 + 0.02 * np.sin(np.arange(40) * 0.9) * rg.uniform(0.3, 1, 40)
    for k in range(39): line(px[k], py[k], px[k + 1], py[k + 1], 0.0014)
    rect(0.56, 0.60, 0.80, 0.71)
    for k in range(9):
        x = 0.575 + k * 0.026
        line(x, 0.61, x, 0.70, 0.0012)
    rect(0.60, 0.44, 0.76, 0.57); circle(0.68, 0.505, 0.045)
    # lower-left: pulsar-map-style burst (radial lines of different lengths with binary dashes) - our own angles
    cx, cy = 0.33, 0.30; rg = np.random.default_rng(1977)
    for k in range(14):
        a = rg.uniform(0, 2 * math.pi) if k else math.pi; L = rg.uniform(0.07, 0.19) if k else 0.21
        ex, ey = cx + math.cos(a) * L, cy + math.sin(a) * L
        line(cx, cy, ex, ey, 0.0015)
        for j in range(int(L / 0.012)):
            if rg.random() < 0.5:
                t0 = j * 0.012 / L
                bx, by = cx + (ex - cx) * t0, cy + (ey - cy) * t0
                line(bx - math.sin(a) * 0.004, by + math.cos(a) * 0.004, bx + math.sin(a) * 0.004, by - math.cos(a) * 0.004, 0.0012)
    # lower-right: two-circle hydrogen diagram
    circle(0.64, 0.28, 0.028); circle(0.74, 0.28, 0.028); line(0.668, 0.28, 0.712, 0.28)
    line(0.64, 0.28, 0.64, 0.30, 0.0016); line(0.74, 0.28, 0.74, 0.26, 0.0016)
    circle(0.64, 0.28, 0.004, 0.004); circle(0.74, 0.28, 0.004, 0.004)
    # centre hole ring + outer rim
    circle(0.5, 0.5, 0.012, 0.004); circle(0.5, 0.5, 0.485, 0.003); circle(0.5, 0.5, 0.47, 0.0015)
    img = np.clip(img, 0, 1)[::-1]
    rgba = np.stack([img, img, img, np.ones_like(img)], -1)
    im = bpy.data.images.new("reccover", N, N, alpha=False); im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = path; im.file_format = "PNG"; im.save()
    bpy.data.images.remove(im)


# ------------------------------------------------------------------------------------------- lights / camera
def sun(dirv, strength, col=(1.0, 0.96, 0.9), angle=0.6):
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = strength; ld.color = col; ld.angle = math.radians(angle)
    ob = link(bpy.data.objects.new("sun", ld))
    ob.rotation_euler = Vector(dirv).normalized().to_track_quat("Z", "Y").to_euler()   # light shines along -Z local
    return ob


def area(loc, target, energy, size, col):
    ld = bpy.data.lights.new("area", "AREA"); ld.energy = energy; ld.size = size; ld.color = col
    ob = link(bpy.data.objects.new("area", ld)); ob.location = loc
    ob.rotation_euler = (Vector(loc) - Vector(target)).to_track_quat("Z", "Y").to_euler()
    return ob


def make_cam(lens=35):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 2000
    ob = link(bpy.data.objects.new("cam", cd)); sc.camera = ob
    return ob


def look(cam, loc, target, roll=0.0):
    cam.location = loc
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    cam.rotation_euler = (q.to_matrix() @ Matrix.Rotation(roll, 3, "Z")).to_euler()


def sst(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0); return t * t * (3 - 2 * t)


SUN_DIR = Vector((0.30, -0.52, 0.80)).normalized()     # direction TO the sun (theatrical: ~37 deg off boresight)

root = build_voyager()
sun(SUN_DIR, 5.0)
area(Vector((-9, -12, -5)), (0, 0, 0), 520, 9, (0.5, 0.68, 1.0))       # cool fill from below/behind
area(Vector((10, 8, -6)), (0, 0, 0), 1100, 6, (1.0, 0.72, 0.45))         # faint warm kicker
cam = make_cam()


def cam_state(shot, t):
    """returns (loc, target, lens, roll) for time t (s) within the shot"""
    if shot == "hero":        # 24 s: slow orbit on the sunlit side, from dish front round to the record side
        u = t / 24.0
        az = math.radians(-128 + 46 * u); el = math.radians(24 - 10 * u); dist = 12.5 - 2.5 * sst(0, 1, u)
        loc = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
        return loc, Vector((-0.4, 0.6, 0.35)), 40, math.radians(-8)
    if shot == "sig":         # 14 s: looking past the dish along the boresight (towards the Sun / Earth)
        u = t / 14.0
        az = math.radians(200 - 14 * u); el = math.radians(-33 + 4 * u); dist = 10.5 + 1.0 * u
        loc = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
        return loc, Vector((0.0, 0.0, 1.4)), 30, math.radians(6)
    if shot == "end":         # 34 s: the craft recedes; we fall behind
        u = t / 34.0
        az = math.radians(-62 - 18 * u); el = math.radians(12 + 6 * u); dist = 9.0 * (24.0) ** (u ** 1.25)
        loc = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
        return loc, Vector((0, 0, 0.3)) * (1 - u), 38, math.radians(5 - 10 * u)
    if shot == "fly":         # 8 s loop-free pass sprite: craft seen from the side, slowly turning
        u = t / 8.0
        az = math.radians(-100 + 30 * u); el = math.radians(18); dist = 30
        loc = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
        return loc, Vector((-0.8, 1.2, 0.2)), 50, 0.0
    def orb(az, el, dist):
        az = math.radians(az); el = math.radians(el)
        return Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * dist
    if shot == "plate_heroA":
        return orb(-122, 22, 11.0), Vector((-0.5, 0.7, 0.35)), 40, math.radians(-8)
    if shot == "plate_heroB":
        return orb(-80, 12, 8.6), Vector((-0.1, 0.4, 0.3)), 40, math.radians(-5)
    if shot == "plate_sig":      # from behind and below: the Sun (on the boresight) sits just past the dish rim
        return orb(200, -70, 11.5), Vector((0.0, 0.0, 3.2)), 30, math.radians(14)
    if shot == "plate_end":
        return orb(-60, 48, 10.5), Vector((-0.3, 0.5, 0.3)), 45, math.radians(12)
    if shot == "plate_fly":
        return orb(-95, 15, 26), Vector((-0.8, 1.2, 0.2)), 50, 0.0
    if shot == "plate_record":
        return Vector((1.9, -4.6, 0.25)), Vector((0.2, -0.6, 0.25)), 50, math.radians(-4)
    if shot == "plate_cover":
        a = REC_ANG
        return Vector((math.cos(a - 0.5) * 1.62, math.sin(a - 0.5) * 1.62, 0.17)), Vector((math.cos(a) * 0.86, math.sin(a) * 0.86, 0.0)), 85, math.radians(3)
    if shot == "plate_rtg":
        return Vector((-5.2, -4.4, 0.9)), Vector((-2.3, 0.1, -0.25)), 60, math.radians(-5)
    if shot == "plate_thumb":
        return Vector((-5.5, -9.5, 4.2)), Vector((-0.6, 0.9, 0.5)), 42, math.radians(-10)
    return Vector((6, -11, 5)), Vector((-0.4, 0.6, 0.3)), 40, 0.0


def export_cam(path, shot, frames):
    out = []
    for f in frames:
        loc, tgt, lens, roll = cam_state(shot, f / 24.0)
        look(cam, loc, tgt, roll); cam.data.lens = lens
        bpy.context.view_layer.update()
        R = cam.matrix_world.to_3x3()
        out.append(dict(f=f, R=[list(r) for r in R], loc=list(loc), lens=lens))
    json.dump(dict(shot=shot, sun=list(SUN_DIR), gal_n=list(GAL_N), frames=out), open(path, "w"))


def render(shot, frames, res, spp, outdir):
    os.makedirs(outdir, exist_ok=True)
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.cycles.samples = spp
    export_cam(os.path.join(outdir, "cam.json"), shot, frames)
    for f in frames:
        fn = os.path.join(outdir, f"{f:04d}.png")
        if os.path.exists(fn): continue
        loc, tgt, lens, roll = cam_state(shot, f / 24.0)
        look(cam, loc, tgt, roll); cam.data.lens = lens
        sc.render.filepath = fn[:-4] + ".tmp.png"
        bpy.ops.render.render(write_still=True)
        os.replace(sc.render.filepath, fn)
        print("rendered", shot, f, flush=True)


f0 = int(argv[1]) if len(argv) > 1 and SHOT != "test" else None
f1 = int(argv[2]) if len(argv) > 2 and SHOT != "test" else None
step = int(argv[3]) if len(argv) > 3 else 1
if SHOT == "test":
    which = argv[1]; t = float(argv[2])
    sc.render.resolution_x, sc.render.resolution_y = 960, 540; sc.cycles.samples = 24
    loc, tgt, lens, roll = cam_state(which, t); look(cam, loc, tgt, roll); cam.data.lens = lens
    sc.render.filepath = os.path.join(SCR, "chk", f"test_{which}_{int(t)}.png"); bpy.ops.render.render(write_still=True)
elif SHOT in ("hero", "sig", "end"):
    n = {"hero": 24, "sig": 14, "end": 34}[SHOT] * 24
    render(SHOT, range(f0 or 0, f1 if f1 is not None else n, step), (1920, 1080), 40, os.path.join(SCR, "fr_" + SHOT))
elif SHOT == "fly":
    render(SHOT, range(0, 8 * 24, 1), (640, 360), 32, os.path.join(SCR, "fr_fly"))
elif SHOT.startswith("plate_"):
    big = SHOT in ("plate_heroA", "plate_heroB", "plate_end", "plate_thumb")
    res = (3200, 1800) if big else ((1600, 900) if SHOT == "plate_fly" else (2560, 1440))
    sc.cycles.adaptive_threshold = 0.012
    render(SHOT, [0], res, 200 if big else 110, os.path.join(SCR, "plates", SHOT))
