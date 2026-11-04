"""
03 "You Are Not Sitting Still" - Earth globe loop (Blender 5.1 / Cycles CPU).

One full rotation of the Earth in N_LOOP frames (seamless loop: the Sun direction and camera are fixed,
only the globe turns). The compositor plays this loop for the whole "Earth's spin" scene (time-lapse,
labelled on screen), so only N_LOOP frames are ever rendered.

Globe: NASA Blue Marble day map + NASA night-lights map (from the three-globe npm package examples),
cloud alpha map; lit by a fixed Sun direction computed in the shader (emission only, no lights, no bounces).
Overlays modelled in 3D so they rotate / occlude correctly: equator ring, 51.5 N (London) latitude ring,
and a small London marker. London's screen position per frame is written to london_xy.json for labels.
Output: RGBA PNG frames (transparent background; stars are added in the compositor).

Run:
  /home/user/bpyenv/bin/python earth_blender.py -- [--frames 1,100] [--skip-existing] [--samples 3]
"""
import sys, os, math, json
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

S = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still"
TEX = S + "/tex"
OUT = S + "/earth_frames"
N_LOOP = 288                     # 1 rotation = 288 frames = 12 s at 24 fps (time-lapse ~7,200x)
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(n, d=None):
    return ARGV[ARGV.index(n) + 1] if n in ARGV else d


SAMPLES = int(arg("--samples", 3))
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 0
sc.cycles.transparent_max_bounces = 4
sc.cycles.use_adaptive_sampling = False
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.render.resolution_percentage = 100
sc.render.threads_mode = "FIXED"
sc.render.threads = int(arg("--threads", 2))
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.image_settings.compression = 40
sc.view_settings.view_transform = "Standard"
sc.frame_start, sc.frame_end = 1, N_LOOP
world = bpy.data.worlds.new("w"); sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[1].default_value = 0.0

SUN = Vector((-0.28, -0.95, 0.18)).normalized()   # light from front-left: day on the left, night on the right


def img(name, non_color=False):
    im = bpy.data.images.load(f"{TEX}/{name}")
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    return im


# ------------------------------------------------------------------ globe
bpy.ops.mesh.primitive_uv_sphere_add(segments=160, ring_count=80, radius=1.0)
earth = bpy.context.object
earth.name = "Earth"
bpy.ops.object.shade_smooth()
m = bpy.data.materials.new("earth"); m.use_nodes = True
nt = m.node_tree; N = nt.nodes; L = nt.links
for n in list(N):
    N.remove(n)
out = N.new("ShaderNodeOutputMaterial")
tc = N.new("ShaderNodeTexCoord")
# equirectangular mapping from object-space position (u = lon, v = lat)
sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
at2 = N.new("ShaderNodeMath"); at2.operation = "ARCTAN2"
L.new(sep.outputs["Y"], at2.inputs[0]); L.new(sep.outputs["X"], at2.inputs[1])
u = N.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"
L.new(at2.outputs[0], u.inputs[0]); u.inputs[1].default_value = 1 / (2 * math.pi); u.inputs[2].default_value = 0.5
asn = N.new("ShaderNodeMath"); asn.operation = "ARCSINE"; L.new(sep.outputs["Z"], asn.inputs[0])
v = N.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"
L.new(asn.outputs[0], v.inputs[0]); v.inputs[1].default_value = 1 / math.pi; v.inputs[2].default_value = 0.5
uv = N.new("ShaderNodeCombineXYZ"); L.new(u.outputs[0], uv.inputs[0]); L.new(v.outputs[0], uv.inputs[1])


def tex(name, nc=False):
    t = N.new("ShaderNodeTexImage"); t.image = img(name, nc); t.interpolation = "Cubic"
    t.extension = "REPEAT"; L.new(uv.outputs[0], t.inputs[0]); return t


day = tex("earth_day.png"); night = tex("earth_lights.png", True); cl = tex("earth_clouds.png", True)
# lighting term: dot(world normal, SUN)
dp = N.new("ShaderNodeVectorMath"); dp.operation = "DOT_PRODUCT"
L.new(N.new("ShaderNodeNewGeometry").outputs["Normal"], dp.inputs[0])
dp.inputs[1].default_value = SUN
lam = N.new("ShaderNodeMath"); lam.operation = "MAXIMUM"; L.new(dp.outputs["Value"], lam.inputs[0]); lam.inputs[1].default_value = 0.0
# soft terminator: smoothstep(-0.08, 0.25, dot)
term = N.new("ShaderNodeMapRange"); term.interpolation_type = "SMOOTHSTEP"
L.new(dp.outputs["Value"], term.inputs["Value"]); term.inputs["From Min"].default_value = -0.10; term.inputs["From Max"].default_value = 0.20
nightw = N.new("ShaderNodeMath"); nightw.operation = "SUBTRACT"; nightw.inputs[0].default_value = 1.0
L.new(term.outputs[0], nightw.inputs[1])
# day surface = mix(day, white clouds, cloud alpha) * (0.15 + 1.15*lambert^0.8)
mixc = N.new("ShaderNodeMix"); mixc.data_type = "RGBA"
L.new(cl.outputs["Color"], mixc.inputs["Factor"]); L.new(day.outputs["Color"], mixc.inputs[6])
mixc.inputs[7].default_value = (0.92, 0.93, 0.95, 1)
pw = N.new("ShaderNodeMath"); pw.operation = "POWER"; L.new(lam.outputs[0], pw.inputs[0]); pw.inputs[1].default_value = 0.8
k = N.new("ShaderNodeMath"); k.operation = "MULTIPLY_ADD"; L.new(pw.outputs[0], k.inputs[0]); k.inputs[1].default_value = 1.25; k.inputs[2].default_value = 0.0
kt = N.new("ShaderNodeMath"); kt.operation = "MULTIPLY"; L.new(k.outputs[0], kt.inputs[0]); L.new(term.outputs[0], kt.inputs[1])
dayc = N.new("ShaderNodeMix"); dayc.data_type = "RGBA"; dayc.blend_type = "MULTIPLY"; dayc.inputs["Factor"].default_value = 1.0
L.new(mixc.outputs[2], dayc.inputs[6])
kc = N.new("ShaderNodeCombineXYZ"); [L.new(kt.outputs[0], kc.inputs[i]) for i in range(3)]
L.new(kc.outputs[0], dayc.inputs[7])
# night lights (warm), dimmed under clouds
nl = N.new("ShaderNodeMix"); nl.data_type = "RGBA"; nl.blend_type = "MULTIPLY"; nl.inputs["Factor"].default_value = 1.0
L.new(night.outputs["Color"], nl.inputs[6]); nl.inputs[7].default_value = (1.0, 0.72, 0.42, 1)
ncl = N.new("ShaderNodeMath"); ncl.operation = "MULTIPLY_ADD"; L.new(cl.outputs["Color"], ncl.inputs[0])
ncl.inputs[1].default_value = -0.7; ncl.inputs[2].default_value = 1.0
nw = N.new("ShaderNodeMath"); nw.operation = "MULTIPLY"; L.new(ncl.outputs[0], nw.inputs[0]); L.new(nightw.outputs[0], nw.inputs[1])
nw2 = N.new("ShaderNodeMath"); nw2.operation = "MULTIPLY"; L.new(nw.outputs[0], nw2.inputs[0]); nw2.inputs[1].default_value = 1.1
nlc = N.new("ShaderNodeMix"); nlc.data_type = "RGBA"; nlc.blend_type = "MULTIPLY"; nlc.inputs["Factor"].default_value = 1.0
L.new(nl.outputs[2], nlc.inputs[6]); nwc = N.new("ShaderNodeCombineXYZ"); [L.new(nw2.outputs[0], nwc.inputs[i]) for i in range(3)]
L.new(nwc.outputs[0], nlc.inputs[7])
addc = N.new("ShaderNodeMix"); addc.data_type = "RGBA"; addc.blend_type = "ADD"; addc.inputs["Factor"].default_value = 1.0
L.new(dayc.outputs[2], addc.inputs[6]); L.new(nlc.outputs[2], addc.inputs[7])
# faint ambient so the night side isn't pure black (earthshine-ish blue)
amb = N.new("ShaderNodeMix"); amb.data_type = "RGBA"; amb.blend_type = "ADD"; amb.inputs["Factor"].default_value = 1.0
L.new(addc.outputs[2], amb.inputs[6]); amb.inputs[7].default_value = (0.004, 0.006, 0.012, 1)
em = N.new("ShaderNodeEmission"); L.new(amb.outputs[2], em.inputs[0]); em.inputs[1].default_value = 1.0
L.new(em.outputs[0], out.inputs[0])
earth.data.materials.append(m)

# ------------------------------------------------------------------ atmosphere shell (rim glow, lit side)
bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.025)
atm = bpy.context.object; bpy.ops.object.shade_smooth()
ma = bpy.data.materials.new("atm"); ma.use_nodes = True; 
nt = ma.node_tree; N = nt.nodes; L = nt.links
for n in list(N):
    N.remove(n)
o = N.new("ShaderNodeOutputMaterial")
lw = N.new("ShaderNodeLayerWeight"); lw.inputs[0].default_value = 0.35
geo = N.new("ShaderNodeNewGeometry")
d2 = N.new("ShaderNodeVectorMath"); d2.operation = "DOT_PRODUCT"; L.new(geo.outputs["Normal"], d2.inputs[0]); d2.inputs[1].default_value = SUN
lit = N.new("ShaderNodeMapRange"); lit.interpolation_type = "SMOOTHSTEP"; L.new(d2.outputs["Value"], lit.inputs["Value"])
lit.inputs["From Min"].default_value = -0.05; lit.inputs["From Max"].default_value = 0.5
pf = N.new("ShaderNodeMath"); pf.operation = "POWER"; L.new(lw.outputs["Facing"], pf.inputs[0]); pf.inputs[1].default_value = 3.0
st = N.new("ShaderNodeMath"); st.operation = "MULTIPLY"; L.new(pf.outputs[0], st.inputs[0]); L.new(lit.outputs[0], st.inputs[1])
st2 = N.new("ShaderNodeMath"); st2.operation = "MULTIPLY"; L.new(st.outputs[0], st2.inputs[0]); st2.inputs[1].default_value = 1.3
e2 = N.new("ShaderNodeEmission"); e2.inputs[0].default_value = (0.35, 0.58, 1.0, 1); L.new(st2.outputs[0], e2.inputs[1])
tr = N.new("ShaderNodeBsdfTransparent")
ad = N.new("ShaderNodeAddShader"); L.new(e2.outputs[0], ad.inputs[0]); L.new(tr.outputs[0], ad.inputs[1])
L.new(ad.outputs[0], o.inputs[0])
atm.data.materials.append(ma)
atm.visible_shadow = False


# ------------------------------------------------------------------ latitude rings + London marker (children of Earth)
def emis_mat(name, col, strength):
    mm = bpy.data.materials.new(name); mm.use_nodes = True
    nn = mm.node_tree.nodes; ll = mm.node_tree.links
    for n in list(nn):
        nn.remove(n)
    e = nn.new("ShaderNodeEmission"); e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength
    oo = nn.new("ShaderNodeOutputMaterial"); ll.new(e.outputs[0], oo.inputs[0])
    return mm


def ring(lat_deg, col, strength, minor=0.0042):
    lat = math.radians(lat_deg)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.004 * math.cos(lat), minor_radius=minor,
                                     major_segments=256, minor_segments=8,
                                     location=(0, 0, 1.004 * math.sin(lat)))
    r = bpy.context.object
    r.data.materials.append(emis_mat(f"ring{lat_deg}", col, strength))
    r.parent = earth
    return r


ring(0.0, (1.0, 0.82, 0.55), 0.9, 0.0030)            # equator (warm)
ring(51.5, (0.78, 0.70, 1.00), 1.0, 0.0030)          # London's latitude (violet-white accent)
LON_LONDON = math.radians(-0.13)
LAT_LONDON = math.radians(51.5)
pL = Vector((math.cos(LAT_LONDON) * math.cos(LON_LONDON), math.cos(LAT_LONDON) * math.sin(LON_LONDON), math.sin(LAT_LONDON)))
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.0095, location=pL * 1.006)
dot = bpy.context.object; dot.data.materials.append(emis_mat("dot", (1.0, 1.0, 1.0), 8.0)); dot.parent = earth

# texture convention check: u=0.5 at lon 0 => object +X is Greenwich. Rotate so London faces the camera
# at the middle of the loop's visible pass. Earth spins about +Z, eastward (counter-clockwise from north).
earth.rotation_mode = "XYZ"
earth.rotation_euler = (0, 0, 0)
# ------------------------------------------------------------------ camera: 23 deg above the equator, globe right of centre
cam_d = 4.6
el = math.radians(23.0)
az = math.radians(-12.0)   # camera azimuth (x toward Greenwich at rot 0)
cpos = Vector((cam_d * math.cos(el) * math.cos(az), cam_d * math.cos(el) * math.sin(az), cam_d * math.sin(el)))
bpy.ops.object.camera_add(location=cpos)
cam = bpy.context.object; sc.camera = cam
cam.data.lens = 35; cam.data.sensor_width = 36
# aim slightly left of the globe so the Earth sits right of frame centre (room for the speed stack on the left)
target = Vector((0, 0, 0)) + Vector((-math.sin(az), math.cos(az), 0)) * -0.62
dvec = (target - cpos)
cam.rotation_euler = dvec.to_track_quat("-Z", "Y").to_euler()


def set_rot(f):
    earth.rotation_euler[2] = 2 * math.pi * (f - 1) / N_LOOP


def frames():
    fl = arg("--frames")
    return [int(x) for x in fl.split(",")] if fl else list(range(1, N_LOOP + 1))


# London screen positions for the whole loop (for the compositor's label)
xy = {}
for f in range(1, N_LOOP + 1):
    set_rot(f)
    bpy.context.view_layer.update()
    wp = earth.matrix_world @ (pL * 1.006)
    p = world_to_camera_view(sc, cam, wp)
    nrm = (earth.matrix_world.to_3x3() @ pL).normalized()
    vis = nrm.dot((cpos - wp).normalized())
    xy[f] = (round(p.x * 1920, 1), round((1 - p.y) * 1080, 1), round(vis, 3))
json.dump(xy, open(S + "/london_xy.json", "w"))

if "--render" in ARGV or "--frames" in ARGV:
    import time
    for f in frames():
        fn = f"{OUT}/e_{f:04d}.png"
        if "--skip-existing" in ARGV and os.path.exists(fn) and os.path.getsize(fn) > 1000:
            continue
        t0 = time.time()
        sc.frame_set(f); set_rot(f)
        sc.render.filepath = fn
        bpy.ops.render.render(write_still=True)
        print(f"frame {f} {time.time() - t0:.1f}s", flush=True)
