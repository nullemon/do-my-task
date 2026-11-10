"""Hero still: a fossil horn coral (rugose, Devonian type) on a slab, raking light, shallow depth of field.
The fine transverse ridges are the daily growth lines; the broader swellings are annual bands (about 400 fine lines per band
in Wells's 1963 counts - here ~40 are modelled per band so they stay visible). Illustration, not a scan of a specimen."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sc = setup(res=(2160, 2160), samples=160, bounces=6, transparent=False, world=(0.004, 0.004, 0.005), exposure=0.3)
rng = np.random.default_rng(4)

def coral_mesh(length=0.105, rtop=0.021, nu=3600, nv=420, bands=11, seed=0, curl=0.9):
    r_ = np.random.default_rng(seed)
    u = np.linspace(0, 1, nu)[:, None]; v = np.linspace(0, 2 * np.pi, nv, endpoint=False)[None, :]
    R = rtop * (0.07 + 0.93 * u ** 0.72)
    # annual bands (uneven spacing) + ~40 fine "daily" ridges per band + irregular rejuvenation steps
    bpos = np.cumsum(r_.uniform(0.7, 1.3, bands + 1)); bpos = bpos / bpos[-1]
    phase = np.interp(u[:, 0], np.concatenate([[0], bpos]), np.arange(bands + 2))[:, None]
    annual = 0.050 * np.cos(2 * np.pi * phase) + 0.022 * np.cos(4 * np.pi * phase + 1.0)
    fine = 0.0105 * (np.abs(np.sin(np.pi * phase * 40 + 0.35 * np.sin(3 * v + 5 * phase))) ** 0.6 - 0.6)
    lon = 0.012 * np.cos(46 * v + 0.6 * np.sin(phase * 2)) * (0.4 + 0.6 * u)                 # septal grooves (interseptal ridges)
    lump = 0.035 * fbm(np.broadcast_to(u * 9, (nu, nv)).copy(), np.broadcast_to(np.cos(v) * 1.5 + np.sin(v) * 0.7 + 3, (nu, nv)).copy(), 4, 1.0, 0.55, seed + 9)
    pit = 0.012 * fbm(np.broadcast_to(u * 160, (nu, nv)).copy(), np.broadcast_to(v * 30, (nu, nv)).copy(), 3, 1.0, 0.6, seed + 19)
    Rr = R * (1 + annual + fine + lon + lump + pit)
    # curved axis (horn shape) in the x-z plane
    th = curl * (1 - u) ** 1.6
    ax = np.cumsum(np.cos(th[:, 0])) / nu * length; az = -np.cumsum(np.sin(th[:, 0])) / nu * length * -1
    ax = ax[:, None]; az = az[:, None]
    tx, tz = np.cos(th), np.sin(th)                                                          # tangent; normal1 = (-tz, 0, tx), normal2 = y
    X = ax + Rr * np.cos(v) * (-tz); Y = Rr * np.sin(v) + 0 * u; Z = az + Rr * np.cos(v) * tx
    X = np.concatenate([X, X[:, :1]], 1); Y = np.concatenate([Y, Y[:, :1]], 1); Z = np.concatenate([Z, Z[:, :1]], 1)
    # calyx: cup going back down inside from the rim, with radial septa
    nc = 260; w = np.linspace(0, 1, nc)[:, None]
    Rc = Rr[-1:, :] * (1 - 0.10 * w) * (1 - w ** 2.2) ** 0.5 * (1 + 0.07 * (np.abs(np.cos(23 * v)) ** 6) * (0.2 + 0.8 * w) * -1 + 0.0)
    Rc = np.maximum(Rc * (1 + 0.10 * np.abs(np.cos(23 * v)) ** 8 * np.clip(w * 3, 0, 1)), 0)
    dep = -0.016 * (w ** 1.3)
    Xc = ax[-1] + dep * tx[-1] + Rc * np.cos(v) * (-tz[-1]); Yc = Rc * np.sin(v); Zc = az[-1] + dep * tz[-1] + Rc * np.cos(v) * tx[-1]
    Xc = np.concatenate([Xc, Xc[:, :1]], 1); Yc = np.concatenate([Yc, Yc[:, :1]], 1); Zc = np.concatenate([Zc, Zc[:, :1]], 1)
    return np.concatenate([X, Xc]), np.concatenate([Y, Yc]), np.concatenate([Z, Zc])

cm, nt, b = new_mat("coral")
tc = nt.nodes.new("ShaderNodeTexCoord"); geo = nt.nodes.new("ShaderNodeNewGeometry")
n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 60; n1.inputs["Detail"].default_value = 10; nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 900; n2.inputs["Detail"].default_value = 6; nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.3; e[0].color = (0.20, 0.155, 0.11, 1); e[1].position = 0.75; e[1].color = (0.62, 0.55, 0.44, 1)
nt.links.new(n1.outputs[0], ramp.inputs[0])
pr = nt.nodes.new("ShaderNodeValToRGB"); e = pr.color_ramp.elements; e[0].position = 0.42; e[0].color = (0.18, 0.15, 0.12, 1); e[1].position = 0.56; e[1].color = (1, 1, 1, 1)
nt.links.new(geo.outputs["Pointiness"], pr.inputs[0])
mx = nt.nodes.new("ShaderNodeMixRGB"); mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1.0
nt.links.new(ramp.outputs[0], mx.inputs[1]); nt.links.new(pr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 0.62
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.inputs["Distance"].default_value = 0.0004
nt.links.new(n2.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])

X, Y, Z = coral_mesh(seed=1)
c1 = grid_mesh(X, Y, Z, "coral1", cm); c1.rotation_euler = (math.radians(86), math.radians(-8), math.radians(38)); c1.location = (-0.040, -0.030, 0.021)
X, Y, Z = coral_mesh(length=0.07, rtop=0.015, nu=2400, nv=320, bands=8, seed=5, curl=0.6)
c2 = grid_mesh(X, Y, Z, "coral2", cm); c2.rotation_euler = (math.radians(95), math.radians(14), math.radians(160)); c2.location = (0.085, 0.075, 0.014)

# slab
s = np.linspace(-1, 1, 1500); SX, SY = np.meshgrid(s * 0.35, s * 0.35)
SZ = 0.006 * fbm(SX, SY, 6, 14, 0.55, 3) + 0.0018 * fbm(SX, SY, 5, 120, 0.6, 4) + 0.0007 * fbm(SX, SY, 4, 700, 0.6, 5)
SZ += 0.003 * np.floor(fbm(SX, SY, 3, 6, 0.5, 6) * 4) / 4                                   # bedding steps
for k in range(60):                                                                          # small fossil debris: crinoid ossicle rings, shell hash
    cx, cy = rng.uniform(-0.3, 0.3, 2); r = rng.uniform(0.002, 0.006)
    d = np.hypot(SX - cx, SY - cy) / r
    SZ += 0.0012 * np.exp(-((d - 1) / 0.28) ** 2) + 0.0006 * np.exp(-(d / 0.3) ** 2)
sm, nt, b = new_mat("slab")
tc = nt.nodes.new("ShaderNodeTexCoord"); n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 30; n1.inputs["Detail"].default_value = 12; nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
ramp = nt.nodes.new("ShaderNodeValToRGB"); e = ramp.color_ramp.elements; e[0].position = 0.3; e[0].color = (0.035, 0.034, 0.036, 1); e[1].position = 0.8; e[1].color = (0.13, 0.12, 0.11, 1)
nt.links.new(n1.outputs[0], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 2500; n2.inputs["Detail"].default_value = 4; nt.links.new(tc.outputs["Object"], n2.inputs["Vector"])
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5; bp.inputs["Distance"].default_value = 0.0003
nt.links.new(n2.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
grid_mesh(SX, SY, SZ, "slab", sm)

def area(loc, target, size, power, col):
    l = bpy.data.lights.new("a", "AREA"); l.energy = power; l.size = size; l.color = col
    o = bpy.data.objects.new("a", l); sc.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o
area((-0.42, 0.18, 0.13), (0, 0, 0.01), 0.10, 9.0, (1.0, 0.86, 0.68))        # raking warm key
area((0.30, -0.35, 0.30), (0, 0, 0.0), 0.5, 0.9, (0.55, 0.7, 1.0))            # cool fill
area((0.1, 0.45, 0.10), (0, 0, 0.02), 0.2, 2.2, (0.8, 0.9, 1.0))              # rim
camera((0.0, -0.20, 0.34), (0.0, 0.0, 0.012), lens=60, dof=0.385, fstop=5.6)
render(SCR + "/plates/coral%s.png" % os.environ.get("TAG", ""))
