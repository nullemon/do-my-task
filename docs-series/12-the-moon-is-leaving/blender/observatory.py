"""Hero still: a laser-ranging observatory on a mountain summit at night (generic 3.5 m-class dome, slit open, telescope
truss visible). Moonlight key + warm practicals, transparent sky (the real star field, the Moon and the green beam are
composited in comp.py). Writes plates/observatory.png + observatory.json (pixel position of the beam exit)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sc = setup(res=(2160, 2160), samples=128, bounces=5, transparent=True, world=(0.016, 0.022, 0.040), exposure=0.0)
rng = np.random.default_rng(8)

# ------------------------------------------------------------------ summit terrain
N = 900; L = 260.0; a = 0.22
s = np.linspace(-1, 1, N); m = L * np.sign(s) * (a * np.abs(s) + (1 - a) * np.abs(s) ** 3)
X, Y = np.meshgrid(m, m); R = np.hypot(X, Y)
plateau = np.clip(1 - R / 26.0, 0, 1) ** 0.5
Z = -0.0016 * R ** 2 * np.clip(R / 40, 0, 1) - 0.25 * np.clip(R - 22, 0, None) ** 1.05
Z += (1 - 0.92 * plateau) * (5.5 * fbm(X, Y, 6, 0.02, 0.5, 1, ridged=True) + 1.2 * fbm(X, Y, 5, 0.11, 0.55, 2, ridged=True) + 0.28 * fbm(X, Y, 4, 0.6, 0.55, 3))
Z += 0.06 * fbm(X, Y, 4, 2.5, 0.6, 4) + 0.5 * fbm(X, Y, 3, 0.05, 0.5, 9) * plateau
Z += -0.9 * np.clip((-Y - 13) / 10, 0, 1) ** 1.5 * (1 + 0.8 * fbm(X, Y, 4, 0.25, 0.55, 12))
Z += 0.9 * np.clip(fbm(X, Y, 5, 0.22, 0.6, 14, ridged=True), 0, 1) ** 2 * np.clip((R - 7.5) / 5, 0, 1)                                           # falls away toward the camera's low side
rk, nt, b = new_mat("rock")
tc = nt.nodes.new("ShaderNodeTexCoord"); geo = nt.nodes.new("ShaderNodeNewGeometry")
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 12; nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 9; n2.inputs["Detail"].default_value = 10; nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.35; e[0].color = (0.055, 0.048, 0.042, 1); e[1].position = 0.75; e[1].color = (0.17, 0.15, 0.13, 1)
nt.links.new(n1.outputs[0], ramp.inputs[0])
# snow where the surface is flat-ish and the noise allows
sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Normal"], sep.inputs[0])
ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "ADD"; nt.links.new(sep.outputs["Z"], ad.inputs[0])
ml = nt.nodes.new("ShaderNodeMath"); ml.operation = "MULTIPLY"; ml.inputs[1].default_value = 0.5; nt.links.new(n1.outputs[0], ml.inputs[0]); nt.links.new(ml.outputs[0], ad.inputs[1])
sr = nt.nodes.new("ShaderNodeValToRGB"); e = sr.color_ramp.elements; e[0].position = 1.06; e[0].color = (0, 0, 0, 1); e[1].position = 1.14; e[1].color = (1, 1, 1, 1)
nt.links.new(ad.outputs[0], sr.inputs[0])
mx = nt.nodes.new("ShaderNodeMixRGB"); mx.inputs[2].default_value = (0.75, 0.80, 0.88, 1); nt.links.new(sr.outputs[0], mx.inputs[0]); nt.links.new(ramp.outputs[0], mx.inputs[1])
nt.links.new(mx.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.8; bp.inputs["Distance"].default_value = 0.15
nt.links.new(n2.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
grid_mesh(X, Y, Z, "terrain", rk)
def zat(x, y):
    i = np.searchsorted(m, x); j = np.searchsorted(m, y); return float(Z[min(j, N - 1), min(i, N - 1)])
# boulders
bm_ = []
for k in range(6):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1)
    co = np.array([v.co[:] for v in bm.verts])
    d = 1 + 0.4 * fbm(co[:, 0] * 1.4 + 5 * k, co[:, 1] * 1.4 + co[:, 2] * 2, 4, 1.0, 0.55, 60 + k)
    for v, c_, dd in zip(bm.verts, co, d): v.co = Vector(c_ * dd)
    me = bpy.data.meshes.new("b%d" % k); bm.to_mesh(me); bm.free(); me.polygons.foreach_set("use_smooth", [True] * len(me.polygons)); me.materials.append(rk); bm_.append(me)
for k in range(260):
    p = rng.uniform(-60, 60, 2); r = min(0.15 * (1 - rng.uniform()) ** (-1 / 1.5), 2.2)
    if math.hypot(*p) < 9 or math.hypot(p[0] - 19, p[1] - 12) < 5: continue
    o = bpy.data.objects.new("r", bm_[k % 6]); sc.collection.objects.link(o); o.location = (p[0], p[1], zat(*p) + 0.2 * r); o.scale = (r, r * rng.uniform(0.7, 1.2), r * rng.uniform(0.5, 0.9)); o.rotation_euler = tuple(rng.uniform(0, 6.28, 3))

# ------------------------------------------------------------------ materials
WHITE = simple("white", (0.80, 0.81, 0.82), rough=0.38, noise_bump=(3.0, 0.05))
WHITE2 = simple("white2", (0.62, 0.63, 0.65), rough=0.45)
GREY = simple("grey", (0.22, 0.23, 0.25), rough=0.5, metal=0.6)
DARK = simple("dark", (0.03, 0.03, 0.035), rough=0.6)
CONC = simple("concrete", (0.30, 0.29, 0.28), rough=0.9, noise_bump=(6.0, 0.4))
STEEL = simple("steel", (0.55, 0.57, 0.6), rough=0.35, metal=1.0)
WARM = simple("warm", (0, 0, 0), emit=(1.0, 0.62, 0.28), estr=14.0)
REDL = simple("redl", (0, 0, 0), emit=(1.0, 0.08, 0.03), estr=30.0)
MIRR = simple("mirr", (0.9, 0.9, 0.95), rough=0.05, metal=1.0)


def dome(radius, base_h, slit_az, slit_half=math.radians(10), nseg=96, nring=40, at=(0, 0), z0=0.0, tel=True):
    parts = []
    cx, cy = at
    # base drum: stacked rings with shadow gaps + vertical pilasters
    nb = 4
    for k in range(nb):
        h = base_h / nb
        parts.append(prim("cyl", WHITE, loc=(cx, cy, z0 + h * (k + 0.5)), scale=(radius * 0.97, radius * 0.97, h - 0.06), seg=96, smooth=True))
    parts.append(prim("cyl", GREY, loc=(cx, cy, z0 + base_h / 2), scale=(radius * 0.955, radius * 0.955, base_h), seg=96, smooth=True))
    for k in range(24):
        a_ = k * 2 * math.pi / 24
        parts.append(prim("box", WHITE2, loc=(cx + radius * 0.975 * math.cos(a_), cy + radius * 0.975 * math.sin(a_), z0 + base_h / 2), rot=(0, 0, a_), scale=(0.10, 0.22, base_h)))
    parts.append(prim("cyl", CONC, loc=(cx, cy, z0 - 0.3), scale=(radius * 1.12, radius * 1.12, 0.9), seg=96, smooth=True))      # plinth
    # ring girder + catwalk with railing
    zt = z0 + base_h
    parts.append(prim("cyl", WHITE2, loc=(cx, cy, zt + 0.12), scale=(radius * 1.03, radius * 1.03, 0.30), seg=96, smooth=True))
    parts.append(prim("cyl", GREY, loc=(cx, cy, zt - 0.5), scale=(radius * 1.22, radius * 1.22, 0.08), seg=96, smooth=True))
    for k in range(48):
        a_ = k * 2 * math.pi / 48; px, py = cx + radius * 1.21 * math.cos(a_), cy + radius * 1.21 * math.sin(a_)
        parts.append(prim("cyl", STEEL, loc=(px, py, zt + 0.05), scale=(0.022, 0.022, 1.1), seg=8))
        if k % 4 == 0: parts.append(prim("box", GREY, loc=(cx + radius * 1.09 * math.cos(a_), cy + radius * 1.09 * math.sin(a_), zt - 0.75), rot=(0, 0, a_), scale=(radius * 0.26, 0.07, 0.45)))
    for hz in (0.58, 0.15):
        bm = bmesh.new(); bmesh.ops.create_circle(bm, segments=96, radius=radius * 1.21); me = bpy.data.meshes.new("rail"); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new("rail", me); sc.collection.objects.link(o); o.location = (cx, cy, zt + hz)
        md = o.modifiers.new("sk", "SKIN"); 
        for v in o.data.skin_vertices[0].data: v.radius = (0.02, 0.02)
        o.data.materials.append(STEEL); parts.append(o)
    # dome shell with slit (from horizon past the zenith), built as quads; ribs + shutters
    th = np.linspace(0, math.pi / 2, nring + 1); ph = np.linspace(0, 2 * math.pi, nseg + 1)
    V = []; F = []
    for i, t in enumerate(th):
        for j, p in enumerate(ph[:-1]):
            V.append((radius * math.cos(t) * math.cos(p), radius * math.cos(t) * math.sin(p), radius * math.sin(t) * 0.98))
    def in_slit(t, p):
        x, y, z = math.cos(t) * math.cos(p), math.cos(t) * math.sin(p), math.sin(t)
        fx = x * math.cos(slit_az) + y * math.sin(slit_az); lx = -x * math.sin(slit_az) + y * math.cos(slit_az)
        return abs(lx) < math.sin(slit_half) and (fx > -0.28)
    for i in range(nring):
        for j in range(nseg):
            tm = (th[i] + th[i + 1]) / 2; pm = (ph[j] + ph[j + 1]) / 2
            if in_slit(tm, pm): continue
            F.append((i * nseg + j, i * nseg + (j + 1) % nseg, (i + 1) * nseg + (j + 1) % nseg, (i + 1) * nseg + j))
    d = obj_from(V, F, "dome", WHITE); d.location = (cx, cy, zt + 0.25)
    md = d.modifiers.new("sol", "SOLIDIFY"); md.thickness = 0.12; md.offset = -1
    parts.append(d)
    # meridian ribs and ring seams (thin raised strips)
    def strip(pts, w=0.05, h=0.035, mat=WHITE2):
        bm = bmesh.new(); vs = [bm.verts.new(p) for p in pts]
        for a_, b_ in zip(vs, vs[1:]): bm.edges.new((a_, b_))
        me = bpy.data.meshes.new("strip"); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new("strip", me); sc.collection.objects.link(o); o.location = (cx, cy, zt + 0.25)
        o.modifiers.new("sk", "SKIN")
        for v in o.data.skin_vertices[0].data: v.radius = (w, h)
        o.data.materials.append(mat); parts.append(o); return o
    for k in range(24):
        p = k * 2 * math.pi / 24 + 0.01
        pts = [(1.004 * radius * math.cos(t) * math.cos(p), 1.004 * radius * math.cos(t) * math.sin(p), 1.004 * radius * math.sin(t) * 0.98) for t in np.linspace(0.02, math.pi / 2 - 0.12, 26) if not in_slit(t, p)]
        if len(pts) > 3: strip(pts)
    for t in (0.35, 0.7, 1.05):
        seg = []
        for p in np.linspace(0, 2 * math.pi, 121):
            if in_slit(t, p):
                if len(seg) > 2: strip(seg, 0.035, 0.03)
                seg = []
            else: seg.append((1.004 * radius * math.cos(t) * math.cos(p), 1.004 * radius * math.cos(t) * math.sin(p), 1.004 * radius * math.sin(t) * 0.98))
        if len(seg) > 2: strip(seg, 0.035, 0.03)
    # slit frame rails + the two shutter leaves parked either side
    fwd = np.array([math.cos(slit_az), math.sin(slit_az), 0]); lat = np.array([-math.sin(slit_az), math.cos(slit_az), 0]); up = np.array([0, 0, 1.0])
    for sgn in (-1, 1):
        off = math.sin(slit_half) * radius * sgn
        pts = [tuple(lat * off * 1.02 + (fwd * math.cos(t) + up * math.sin(t) * 0.98) * radius * 1.012 * math.sqrt(max(0.0, 1 - (off / radius) ** 2))) for t in np.linspace(0.0, math.pi - 1.25, 40)]
        strip(pts, 0.11, 0.10, WHITE2)
        V2 = []; F2 = []; nt_, nl_ = 30, 6
        for i, t in enumerate(np.linspace(0.03, math.pi - 1.3, nt_)):
            for j, q in enumerate(np.linspace(1.08, 2.85, nl_)):
                o_ = math.sin(slit_half) * radius * q * sgn; rr = radius * 1.03 * math.sqrt(max(0.0, 1 - (o_ / (radius * 1.03)) ** 2))
                V2.append(tuple(lat * o_ + (fwd * math.cos(t) + up * math.sin(t) * 0.98) * rr))
        for i in range(nt_ - 1):
            for j in range(nl_ - 1): F2.append((i * nl_ + j, i * nl_ + j + 1, (i + 1) * nl_ + j + 1, (i + 1) * nl_ + j))
        sh = obj_from(V2, F2, "shutter", WHITE2); sh.location = (cx, cy, zt + 0.25); mdd = sh.modifiers.new("sol", "SOLIDIFY"); mdd.thickness = 0.10; parts.append(sh)
    exit_pt = None
    if tel:
        # telescope: fork + truss tube pointing out of the slit at 52 deg elevation
        el = math.radians(52); axis = fwd * math.cos(el) + up * math.sin(el)
        piv = np.array([cx, cy, zt + 0.6])
        tube_r = radius * 0.30; tl = radius * 0.95
        def P(s_, ang, rr=tube_r):
            e1 = lat; e2 = np.cross(axis, lat); return piv + axis * s_ + (e1 * math.cos(ang) + e2 * math.sin(ang)) * rr
        def strut(p0, p1, r=0.045, mat=STEEL):
            p0 = Vector(p0); p1 = Vector(p1); dd = p1 - p0
            o = prim("cyl", mat, loc=(p0 + p1) / 2, scale=(r, r, dd.length), seg=10, smooth=True); o.rotation_euler = dd.to_track_quat("Z", "Y").to_euler(); return o
        for sring in (-0.25 * tl, 0.15 * tl, tl):
            for k in range(16): strut(P(sring, k * math.pi / 8), P(sring, (k + 1) * math.pi / 8), 0.06, WHITE2)
        for k in range(8):
            strut(P(0.15 * tl, k * math.pi / 4), P(tl, (k + 0.5) * math.pi / 4), 0.035); strut(P(0.15 * tl, (k + 1) * math.pi / 4), P(tl, (k + 0.5) * math.pi / 4), 0.035)
            strut(P(-0.25 * tl, k * math.pi / 4), P(0.15 * tl, k * math.pi / 4), 0.05, WHITE2)
        cell = prim("cyl", GREY, loc=tuple(piv - axis * 0.3 * tl), scale=(tube_r * 1.02, tube_r * 1.02, 0.5), seg=32, smooth=True); cell.rotation_euler = Vector(axis).to_track_quat("Z", "Y").to_euler()
        mir = prim("cyl", MIRR, loc=tuple(piv - axis * 0.22 * tl), scale=(tube_r * 0.95, tube_r * 0.95, 0.04), seg=48, smooth=True); mir.rotation_euler = cell.rotation_euler
        sec = prim("cyl", DARK, loc=tuple(piv + axis * tl * 0.98), scale=(tube_r * 0.28, tube_r * 0.28, 0.5), seg=24, smooth=True); sec.rotation_euler = cell.rotation_euler
        for k in range(4): strut(P(tl, k * math.pi / 2 + 0.3), P(tl, k * math.pi / 2 + 0.3, tube_r * 0.28), 0.02, DARK)
        for sgn in (-1, 1):                                               # fork arms + pier
            strut(piv + lat * sgn * tube_r * 1.25 - up * 2.6, piv + lat * sgn * tube_r * 1.25 + up * 0.1, 0.32, WHITE)
        prim("cyl", WHITE2, loc=(cx, cy, zt - 1.6), scale=(tube_r * 1.6, tube_r * 1.6, 1.2), seg=32, smooth=True)
        point(tuple(piv - fwd * 1.5 - up * 1.0), 60, (1.0, 0.12, 0.05), 0.4)            # dim red work light inside
        exit_pt = piv + axis * tl * 1.0
    return exit_pt

AZ = math.radians(-28)
exit_pt = dome(5.2, 6.0, AZ, at=(0, 0), z0=zat(0, 0) - 0.2)
# door + stair + lit window on the drum, facing the camera side
z0 = zat(0, 0) - 0.2
for a_, kind in ((math.radians(-112), "door"), (math.radians(-150), "win"), (math.radians(-80), "win")):
    px, py = 5.07 * math.cos(a_), 5.07 * math.sin(a_)
    if kind == "door":
        prim("box", WARM, loc=(px, py, z0 + 1.25), rot=(0, 0, a_), scale=(0.06, 1.0, 2.1)); prim("box", GREY, loc=(px * 1.004, py * 1.004, z0 + 1.25), rot=(0, 0, a_), scale=(0.05, 1.2, 2.3))
        prim("box", DARK, loc=(px * 1.012, py * 1.012 , z0 + 1.25), rot=(0, 0, a_), scale=(0.03, 0.5, 2.1))            # door leaf ajar
        point((px * 1.25, py * 1.25, z0 + 2.6), 35, (1.0, 0.6, 0.3), 0.15)
        for k in range(5): prim("box", CONC, loc=(px * (1.08 + 0.06 * k), py * (1.08 + 0.06 * k), z0 - 0.1 - 0.18 * k), rot=(0, 0, a_), scale=(0.34, 1.8, 0.18))
    else:
        prim("box", WARM, loc=(px, py, z0 + 3.9), rot=(0, 0, a_), scale=(0.06, 0.8, 0.55)); prim("box", GREY, loc=(px * 1.003, py * 1.003, z0 + 3.9), rot=(0, 0, a_), scale=(0.05, 0.95, 0.7))
# support building + small second dome + weather mast
bx, by = 19.0, 12.0; bz = zat(bx, by) - 0.3
prim("box", WHITE2, loc=(bx, by, bz + 2.0), rot=(0, 0, 0.3), scale=(12, 6.5, 4.0), bevel=0.05); prim("box", GREY, loc=(bx, by, bz + 4.1), rot=(0, 0, 0.3), scale=(12.5, 7.0, 0.25))
for k in range(4):
    wx = bx - 4.2 + k * 2.8; 
    p = Matrix.Rotation(0.3, 4, "Z") @ Vector((-4.2 + k * 2.8, -3.27, 0)) + Vector((bx, by, bz + 2.3))
    prim("box", WARM if k in (1, 2) else DARK, loc=p, rot=(0, 0, 0.3), scale=(1.3, 0.06, 0.9))
dome(2.6, 3.2, math.radians(200), at=(-24.0, 16.0), z0=zat(-24, 16) - 0.3, tel=False, nseg=64, nring=24)
mx_, my_ = 10.5, -3.0; mz = zat(mx_, my_)
prim("cyl", STEEL, loc=(mx_, my_, mz + 5), scale=(0.05, 0.05, 10), seg=10); prim("ico", REDL, loc=(mx_, my_, mz + 10.1), scale=(0.11, 0.11, 0.11), sub=2)
prim("box", STEEL, loc=(mx_, my_, mz + 9.2), scale=(1.4, 0.04, 0.04)); point((mx_, my_, mz + 10.3), 25, (1.0, 0.1, 0.05), 0.1)

# ------------------------------------------------------------------ light + camera
sun((0.78, 0.10, 0.62), 1.5, (0.62, 0.74, 1.0), angle=1.0)            # moonlight from the upper right, toward the camera side
cam = camera((-7.0, -23.0, z0 - 0.6), (2.2, 0.0, z0 + 9.5), lens=24, shift=(0.0, 0.0))
bpy.context.view_layer.update()
far = exit_pt + (np.array([math.cos(AZ), math.sin(AZ), 0]) * math.cos(math.radians(52)) + np.array([0, 0, 1.0]) * math.sin(math.radians(52))) * 60
json.dump(dict(exit=project(tuple(exit_pt)), far=project(tuple(far))), open(SCR + "/plates/observatory.json", "w"))
render(SCR + "/plates/observatory%s.png" % os.environ.get("TAG", ""))
