"""Hero still: a laser retroreflector array (Apollo 11 LRRR-like layout: 10 x 10 fused-silica corner cubes in a 46 cm
panel on a tilted pallet) on lunar regolith. Hard single-key sunlight, black sky, RGBA.
Usage: /home/user/bpyenv/bin/python reflector.py [glow]   ('glow' renders only the lit prism faces for the laser-return layer)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
GLOW = len(sys.argv) > 1 and sys.argv[1] == "glow"
sc = setup(res=(2160, 2160), samples=16 if GLOW else 128, bounces=10, world=(0.0, 0.0, 0.0), exposure=0.0)
rng = np.random.default_rng(11)

# ------------------------------------------------------------------ regolith height field (dense in the middle)
N = 1300; L = 60.0; a = 0.05
s = np.linspace(-1, 1, N); m = L * np.sign(s) * (a * np.abs(s) + (1 - a) * np.abs(s) ** 5)
X, Y = np.meshgrid(m, m)
Z = 0.55 * fbm(X, Y, 5, 0.03, 0.5, 1) + 0.10 * fbm(X, Y, 5, 0.35, 0.5, 2) + 0.018 * fbm(X, Y, 5, 3.0, 0.55, 3) + 0.004 * fbm(X, Y, 4, 25.0, 0.6, 4)
Z += 0.0016 * fbm(X, Y, 3, 140.0, 0.6, 5) * (np.hypot(X, Y) < 3)
# craters: power-law sizes, bowl + raised rim + faint ejecta
nc = 900
cr = 0.04 * (1 - rng.uniform(0, 1, nc)) ** (-1 / 1.9); cr = np.clip(cr, 0.04, 4.0)
cxy = rng.uniform(-1, 1, (nc, 2)); cxy = np.sign(cxy) * np.abs(cxy) ** 1.8 * 30
for (cx, cy), r in zip(cxy, cr):
    if math.hypot(cx - 0.0, cy - 0.0) < 0.55 + r: continue            # keep the pallet's footing clear
    sel = (np.abs(X - cx) < 2.2 * r) & (np.abs(Y - cy) < 2.2 * r)
    if not sel.any(): continue
    d = np.hypot(X[sel] - cx, Y[sel] - cy) / r
    depth = 0.22 * r * rng.uniform(0.5, 1.0)
    prof = np.where(d < 1, depth * (d * d - 1), 0) + 0.32 * depth * np.exp(-((d - 1.02) / 0.22) ** 2) * (d > 0.75) + 0.08 * depth * np.exp(-(d - 1) / 0.5) * (d >= 1)
    Z[sel] += prof.astype(np.float32)
# boot prints: ribbed rectangles pressed ~1.5 cm into the dust
def boot(bx, by, ang, left):
    c, s_ = math.cos(ang), math.sin(ang)
    sel = (np.abs(X - bx) < 0.3) & (np.abs(Y - by) < 0.3)
    u = (X[sel] - bx) * c + (Y[sel] - by) * s_; v = -(X[sel] - bx) * s_ + (Y[sel] - by) * c
    w = 0.075 - 0.012 * np.cos(u / 0.165 * 2.2)                       # waist
    inside = np.clip((1 - np.abs(u) / 0.165) / 0.08, 0, 1) * np.clip((1 - np.abs(v) / w) / 0.12, 0, 1)
    ribs = 0.5 + 0.5 * np.sign(np.sin(u / 0.027 * math.pi))
    Z[sel] += (-0.007 - 0.006 * ribs) * inside + 0.004 * np.exp(-((np.abs(v) / w - 1.15) / 0.2) ** 2) * (np.abs(u) < 0.19)
ang0 = 2.35
for k in range(9):
    px = -1.9 + k * 0.42 * math.cos(ang0 + 3.14) * -1; py = -0.25 + k * 0.42 * math.sin(ang0) * 0.2
    px = 0.80 + k * 0.56; py = -0.35 + k * 0.30 + (0.12 if k % 2 else -0.12)
    boot(px, py, 0.49 + rng.uniform(-0.12, 0.12), k % 2)
for (px, py, an) in ((-0.72, -0.30, 1.2), (-0.95, -0.12, 1.35), (0.50, 0.85, 0.3), (0.80, 0.72, 0.15)):
    boot(px, py, an, 0)

reg, nt, b = new_mat("regolith")
tc = nt.nodes.new("ShaderNodeTexCoord")
def noise(scale, detail=10, rough=0.6):
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail; n.inputs["Roughness"].default_value = rough
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); return n
n1 = noise(900, 6, 0.7); n2 = noise(120, 8, 0.65); n3 = noise(9, 8, 0.6)
vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 260; nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.25; ramp.color_ramp.elements[0].color = (0.075, 0.072, 0.068, 1)
ramp.color_ramp.elements[1].position = 0.8; ramp.color_ramp.elements[1].color = (0.24, 0.235, 0.225, 1)
mixn = nt.nodes.new("ShaderNodeMath"); mixn.operation = "ADD"; nt.links.new(n2.outputs[0], mixn.inputs[0])
m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 0.5; nt.links.new(n3.outputs[0], m2.inputs[0]); nt.links.new(m2.outputs[0], mixn.inputs[1])
m3 = nt.nodes.new("ShaderNodeMath"); m3.operation = "MULTIPLY"; m3.inputs[1].default_value = 0.6; nt.links.new(mixn.outputs[0], m3.inputs[0])
nt.links.new(m3.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 1.0
if "Diffuse Roughness" in b.inputs: b.inputs["Diffuse Roughness"].default_value = 1.0
b1 = nt.nodes.new("ShaderNodeBump"); b1.inputs["Strength"].default_value = 0.55; b1.inputs["Distance"].default_value = 0.004; nt.links.new(n1.outputs[0], b1.inputs["Height"])
b2 = nt.nodes.new("ShaderNodeBump"); b2.inputs["Strength"].default_value = 0.5; b2.inputs["Distance"].default_value = 0.01; nt.links.new(n2.outputs[0], b2.inputs["Height"]); nt.links.new(b1.outputs["Normal"], b2.inputs["Normal"])
b3 = nt.nodes.new("ShaderNodeBump"); b3.inputs["Strength"].default_value = 0.35; b3.inputs["Distance"].default_value = 0.004; b3.invert = True
nt.links.new(vor.outputs["Distance"], b3.inputs["Height"]); nt.links.new(b2.outputs["Normal"], b3.inputs["Normal"]); nt.links.new(b3.outputs["Normal"], b.inputs["Normal"])
ground = grid_mesh(X, Y, Z, "ground", reg)

# distant rolling hills to a far horizon
s2 = np.linspace(-1, 1, 500); XX, YY = np.meshgrid(s2 * 2600, s2 * 2600)
RR = np.hypot(XX, YY)
ZZ = 55 * fbm(XX, YY, 6, 0.0011, 0.5, 21) * np.clip((RR - 150) / 900, 0, 1) + 6 * fbm(XX, YY, 5, 0.01, 0.5, 22) * np.clip((RR - 60) / 300, 0, 1) - 0.6 - 1.2 * np.clip((60 - RR) / 60, 0, 1)
ZZ += 90 * np.exp(-((XX - 300) ** 2 + (YY - 1900) ** 2) / 500 ** 2) + 60 * np.exp(-((XX + 900) ** 2 + (YY - 1500) ** 2) / 350 ** 2)
grid_mesh(XX, YY, ZZ, "far", reg)

# rocks
rockm, nt, b = new_mat("rock"); b.inputs["Base Color"].default_value = (0.13, 0.125, 0.12, 1); b.inputs["Roughness"].default_value = 0.95
tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 14; n.inputs["Detail"].default_value = 12
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.9
nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
def zat(x, y):
    i = np.searchsorted(m, x); j = np.searchsorted(m, y); return float(Z[min(j, N - 1), min(i, N - 1)])
protos = []
for k in range(8):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1)
    co = np.array([v.co[:] for v in bm.verts]); r_ = np.random.default_rng(100 + k)
    sx = r_.uniform(0.6, 1.2, 3); co2 = co * sx
    disp = 1 + 0.35 * fbm(co[:, 0] * 1.3 + 7 * k, co[:, 1] * 1.3 + co[:, 2] * 2.1, 4, 1.0, 0.55, 30 + k) + 0.10 * fbm(co[:, 0] * 6 + co[:, 2] * 3, co[:, 1] * 6 - co[:, 2] * 2, 3, 1.0, 0.6, 50 + k)
    # a few flat fracture facets
    for _ in range(4):
        nrm = r_.standard_normal(3); nrm /= np.linalg.norm(nrm); d = co @ nrm; cut = r_.uniform(0.45, 0.8)
        disp = np.where(d * disp > cut, cut / np.maximum(d, 1e-3), disp)
    for v, c_, dd in zip(bm.verts, co2, disp): v.co = Vector(c_ * dd)
    me = bpy.data.meshes.new("rock%d" % k); bm.to_mesh(me); bm.free(); me.polygons.foreach_set("use_smooth", [True] * len(me.polygons)); me.materials.append(rockm); protos.append(me)
nr = 520
for k in range(nr):
    r = 0.012 * (1 - rng.uniform()) ** (-1 / 1.6); r = min(r, 0.35)
    p = rng.uniform(-1, 1, 2); p = np.sign(p) * np.abs(p) ** 1.6 * 16
    if math.hypot(p[0], p[1]) < 0.5: continue
    if r > 0.12 and math.hypot(p[0], p[1] + 2.2) < 2.0: continue     # nothing big between camera and array
    o = bpy.data.objects.new("r", protos[k % 8]); sc.collection.objects.link(o)
    o.location = (p[0], p[1], zat(p[0], p[1]) + r * 0.25); o.scale = (r, r, r * rng.uniform(0.6, 1.0)); o.rotation_euler = tuple(rng.uniform(0, 6.28, 3))

# ------------------------------------------------------------------ the array
ALU = simple("alu", (0.78, 0.79, 0.80), rough=0.32, metal=1.0, noise_bump=(60, 0.08))
ALU2 = simple("alu_dark", (0.42, 0.43, 0.45), rough=0.45, metal=1.0)
WHT = simple("white", (0.86, 0.86, 0.84), rough=0.55)
GOLD, nt, b = new_mat("kapton"); b.inputs["Base Color"].default_value = (0.95, 0.62, 0.18, 1); b.inputs["Metallic"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.22
tc = nt.nodes.new("ShaderNodeTexCoord"); vr = nt.nodes.new("ShaderNodeTexVoronoi"); vr.inputs["Scale"].default_value = 38
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.9; bp.inputs["Distance"].default_value = 0.01
nt.links.new(tc.outputs["Object"], vr.inputs["Vector"]); nt.links.new(vr.outputs["Distance"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
MIRROR = simple("mirror", (0.9, 0.93, 0.97), rough=0.02, metal=1.0, emit=(0.15, 1.0, 0.35) if GLOW else None, estr=6.0)
GLASS = simple("silica", (1, 1, 1), rough=0.0, trans=1.0, ior=1.46)
BLK = simple("black", (0.02, 0.02, 0.02), rough=0.6)

root = empty(); parts = []
PW = 0.46; TH = 0.075
parts.append(prim("box", ALU, loc=(0, 0, 0), scale=(PW, PW, TH), bevel=0.004))
parts.append(prim("box", ALU2, loc=(0, 0, TH / 2 + 0.002), scale=(PW - 0.02, PW - 0.02, 0.004)))            # face plate
pitch = 0.0415; r_c = 0.0165
for i in range(10):
    for j in range(10):
        x = (i - 4.5) * pitch; y = (j - 4.5) * pitch
        # recessed socket ring, corner-cube (three mirror facets), front glass
        parts.append(prim("cyl", ALU, loc=(x, y, TH / 2 + 0.004), scale=(r_c + 0.0035, r_c + 0.0035, 0.006), seg=28, smooth=False))
        parts.append(prim("cyl", BLK, loc=(x, y, TH / 2 + 0.0045), scale=(r_c + 0.0005, r_c + 0.0005, 0.0062), seg=28))
        cc = prim("cyl", MIRROR, loc=(x, y, TH / 2 - 0.004), rot=(math.pi, 0, rng.uniform(0, 0.2)), scale=(r_c, r_c, 0.024), seg=3, r2=0.0); parts.append(cc)
        if not GLOW: parts.append(prim("cyl", GLASS, loc=(x, y, TH / 2 + 0.0068), scale=(r_c, r_c, 0.0016), seg=28))
# gold thermal skirt + corner brackets + carry handle + sun-compass gnomon
parts.append(prim("box", GOLD, loc=(0, 0, -0.012), scale=(PW + 0.012, PW + 0.012, TH - 0.03)))
for sx in (-1, 1):
    for sy in (-1, 1):
        parts.append(prim("box", ALU2, loc=(sx * PW / 2, sy * PW / 2, 0), scale=(0.03, 0.03, TH + 0.006), bevel=0.003))
parts.append(prim("cyl", ALU, loc=(0, PW / 2 + 0.05, 0.0), rot=(0, math.pi / 2, 0), scale=(0.008, 0.008, 0.30), seg=16, smooth=True))
for sx in (-1, 1): parts.append(prim("cyl", ALU, loc=(sx * 0.15, PW / 2 + 0.025, 0.0), rot=(math.pi / 2, 0, 0), scale=(0.007, 0.007, 0.05), seg=12, smooth=True))
parts.append(prim("cyl", WHT, loc=(PW / 2 + 0.045, -0.12, TH / 2 - 0.01), scale=(0.035, 0.035, 0.006), seg=32))
parts.append(prim("cyl", BLK, loc=(PW / 2 + 0.045, -0.12, TH / 2 + 0.012), scale=(0.0018, 0.0018, 0.04), seg=8))
parts.append(prim("box", ALU2, loc=(PW / 2 + 0.02, -0.12, TH / 2 - 0.018), scale=(0.05, 0.02, 0.008)))
parent(parts, root)
tilt = math.radians(27)
root.rotation_euler = (tilt, 0, math.radians(-24)); z0 = zat(0, 0)
root.location = (0, 0, z0 + 0.20)
# pallet + legs
base = []
base.append(prim("box", GOLD, loc=(0, 0.02, z0 + 0.035), rot=(0, 0, math.radians(-24)), scale=(0.52, 0.60, 0.035), bevel=0.004))
base.append(prim("box", ALU2, loc=(0, 0.02, z0 + 0.012), rot=(0, 0, math.radians(-24)), scale=(0.56, 0.64, 0.012)))
def strut(p0, p1, r=0.007, mat=ALU):
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    o = prim("cyl", mat, loc=(p0 + p1) / 2, scale=(r, r, d.length), seg=14, smooth=True); o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); return o
bpy.context.view_layer.update()
Mw = root.matrix_world
for sx in (-1, 1):
    top = Mw @ Vector((sx * 0.19, 0.20, -TH / 2)); bot = Matrix.Rotation(math.radians(-24), 4, "Z") @ Vector((sx * 0.21, 0.27, 0)) + Vector((0, 0.02, z0 + 0.05))
    strut(top, bot); prim("cyl", ALU2, loc=bot, scale=(0.016, 0.016, 0.012), seg=16)
    top = Mw @ Vector((sx * 0.19, -0.20, -TH / 2)); bot = Matrix.Rotation(math.radians(-24), 4, "Z") @ Vector((sx * 0.21, -0.25, 0)) + Vector((0, 0.02, z0 + 0.05))
    strut(top, bot, r=0.009); prim("cyl", ALU2, loc=bot, scale=(0.016, 0.016, 0.012), seg=16)
    strut(Mw @ Vector((sx * 0.19, 0.20, -TH / 2)), Matrix.Rotation(math.radians(-24), 4, "Z") @ Vector((sx * 0.21, -0.25, 0)) + Vector((0, 0.02, z0 + 0.05)), r=0.004, mat=ALU2)

# ------------------------------------------------------------------ light + camera
if not GLOW:
    sun((-0.86, -0.30, 0.30), 6.5, (1.0, 0.98, 0.95), angle=0.53)
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.006, 0.006, 0.006, 1)        # faint fill (ground bounce stand-in)
else:
    for o in sc.objects:
        if o.type == "MESH":
            for sl in o.material_slots:
                if sl.material.name not in ("mirror",): sl.material = BLK
    BLK.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0, 0, 0, 1); BLK.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0
    sc.cycles.use_denoising = False
cam = camera((0.50, -1.42, z0 + 0.60), (0.02, 0.10, z0 + 0.36), lens=30, dof=None)
import json
bpy.context.view_layer.update()
json.dump(dict(center=project(Mw @ Vector((0, 0, TH / 2))), normal=list((Mw.to_3x3() @ Vector((0, 0, 1)))[:]),
               corners=[project(Mw @ Vector((sx * PW / 2, sy * PW / 2, TH / 2))) for sx in (-1, 1) for sy in (-1, 1)]), open(SCR + "/plates/reflector.json", "w"))
render(SCR + "/plates/reflector_glow.png" if GLOW else SCR + "/plates/reflector.png")
