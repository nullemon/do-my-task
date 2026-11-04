"""WHAT THEY SEE OF US - background starfield flight LOOP (Blender, Cycles CPU).

A self-similar ("logarithmic") starfield: one shell of stars between radius 1 and F is copied at
scales F^n (n = -7..0). The camera sits at distance D from Earth (origin) looking back at it and
recedes exponentially from D=1 to D=F over N frames. Because the field is scale-invariant, frame N
is identical to frame 0, so these N frames loop forever: the compositor maps the film's
log-distance s(t) to a loop phase and blends neighbouring frames (motion blur at speed).
Same camera model as comp.py (horizontal FOV 50 deg).

Run: /home/user/bpyenv/bin/python -c "import sys; p='bg_loop.py'; sys.argv=['blender','--','--frames','0-191']; exec(compile(open(p).read(),p,'exec'))"
"""
import sys, os, math
import numpy as np
import bpy

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(n, d=None):
    return ARGV[ARGV.index(n) + 1] if n in ARGV else d

OUT = arg("--out", "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us/bgloop")
N = 192
F = 10 ** 0.5
SAMPLES = int(arg("--samples", 8))
RES = (1920, 1080)
HFOV = math.radians(50.0)
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(7)
M = 650                                   # stars per shell
u = rng.normal(size=(M, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
r = F ** rng.uniform(0, 1, M)             # log-uniform inside the shell
base = u * r[:, None]
size = 0.00045 * np.exp(rng.normal(0, 0.55, M))          # radius relative to distance from Earth
big = rng.uniform(0, 1, M) < 0.05
size[big] *= 3.2
temp = rng.uniform(0, 1, M)               # colour: blue-white .. white .. warm
cols = np.empty((M, 3))
for i, t in enumerate(temp):
    if t < 0.2:   c = (0.70, 0.80, 1.00)
    elif t < 0.65: c = (1.00, 0.98, 0.95)
    elif t < 0.88: c = (1.00, 0.88, 0.70)
    else:         c = (1.00, 0.72, 0.50)
    cols[i] = c

pos, rad, col = [], [], []
for n in range(-7, 1):
    s = F ** n
    pos.append(base * s); rad.append(size * r * s); col.append(cols)
pos = np.concatenate(pos); rad = np.concatenate(rad); col = np.concatenate(col)

# --- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 0
sc.cycles.use_adaptive_sampling = False
sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
sc.cycles.filter_width = 1.8
sc.render.threads_mode = "FIXED"; sc.render.threads = int(arg("--threads", 2))
sc.render.resolution_x, sc.render.resolution_y = RES
sc.render.resolution_percentage = 100
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGB"
sc.render.image_settings.color_depth = "8"
sc.view_settings.view_transform = "Standard"
sc.render.film_transparent = False
w = bpy.data.worlds.new("w"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)

me = bpy.data.meshes.new("stars")
me.from_pydata([tuple(p) for p in pos], [], [])
a = me.attributes.new("rad", "FLOAT", "POINT"); a.data.foreach_set("value", rad.astype(np.float32))
c = me.attributes.new("scol", "FLOAT_COLOR", "POINT")
c.data.foreach_set("color", np.concatenate([col, np.ones((len(col), 1))], 1).astype(np.float32).ravel())
ob = bpy.data.objects.new("stars", me); sc.collection.objects.link(ob)

ng = bpy.data.node_groups.new("pts", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
m2p = ng.nodes.new("GeometryNodeMeshToPoints")
na = ng.nodes.new("GeometryNodeInputNamedAttribute"); na.data_type = "FLOAT"; na.inputs["Name"].default_value = "rad"
ng.links.new(gi.outputs[0], m2p.inputs["Mesh"])
ng.links.new(na.outputs["Attribute"], m2p.inputs["Radius"])
ng.links.new(m2p.outputs["Points"], go.inputs[0])
mod = ob.modifiers.new("pts", "NODES"); mod.node_group = ng

mat = bpy.data.materials.new("starmat"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "scol"
em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 2.6
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(at.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
me.materials.append(mat)
# set material on points: Set Material node
sm = ng.nodes.new("GeometryNodeSetMaterial"); sm.inputs["Material"].default_value = mat
ng.links.remove(ng.nodes["Group Output"].inputs[0].links[0])
ng.links.new(m2p.outputs["Points"], sm.inputs["Geometry"]); ng.links.new(sm.outputs[0], go.inputs[0])

cam_d = bpy.data.cameras.new("cam"); cam_d.sensor_fit = "HORIZONTAL"; cam_d.angle = HFOV
cam_d.clip_start = 1e-5; cam_d.clip_end = 100
cam = bpy.data.objects.new("cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_euler = (0, 0, 0)            # Blender camera looks down -Z: toward Earth at origin

fr = arg("--frames", f"0-{N-1}")
a0, a1 = (int(x) for x in fr.split("-"))
import time
for f in range(a0, a1 + 1):
    fn = os.path.join(OUT, f"bg_{f:04d}.png")
    if os.path.exists(fn): continue
    D = F ** (f / N)
    cam.location = (0, 0, D)
    sc.render.filepath = fn
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"frame {f} D={D:.3f} {time.time()-t0:.2f}s", flush=True)
