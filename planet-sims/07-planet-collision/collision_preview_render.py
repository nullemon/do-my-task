"""
PLANET COLLISION  -  simple Blender preview renderer (planet-sims / 07)
======================================================================
Verification / preview tool for the SPH cache written by collision_sim.py
(the final volumetric look-dev renderer is collision_render.py).

Shows every SPH particle as a small glowing sphere: emission colour from the
cached `temp` (dark red -> orange -> yellow-white), iron particles a bit
deeper red, compositor glare for the soft glow, black sky with a procedural
starfield, slow camera drift, vertical 9:16, caption + "Simulated: 1.2 h".

Run:
  * Blender UI: Scripting tab -> open -> Run.  Press play (frame handler
    streams the cache).  Set CACHE_DIR below or env COLLISION_CACHE.
  * Headless:   blender -b -P collision_preview_render.py -- --render [--cache DIR]
  * Preview:    blender -b -P collision_preview_render.py -- --preview [--cache DIR]
               (low-res Cycles stills at key moments -> ./preview/*.jpg)
"""
import bpy
import json
import math
import os
import sys

import numpy as np
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
CACHE_DIR = os.environ.get("COLLISION_CACHE", "")   # "" -> <script dir>/cache/theia
FPS = 30
VIDEO_SECONDS = 30.0
RESOLUTION = (1080, 1920)
ENGINE = "EEVEE"                 # EEVEE | CYCLES
CYCLES_SAMPLES = 64
EEVEE_SAMPLES = 32
PRIMITIVE = "AUTO"               # AUTO (Cycles: points, Eevee: ico spheres) | POINTS | SPHERES
RENDER = False
PREVIEW = False
PREVIEW_RES = (360, 640)
PREVIEW_SAMPLES = 16
PREVIEW_HOURS = None             # None -> auto key moments around contact
OUTPUT_DIR = "//renders/collision/"
CAPTION = "What made our Moon?"
SUBCAPTION = "Theia hits the young Earth"
# video second -> simulated hour.  None = auto from meta (slow motion around the impact)
TIME_KEYS = None
# simulated hour -> visible frame height (Earth radii).  None = auto
VIEW_KEYS = None
CAM_TILT_DEG = 38.0              # 0 = straight down onto the orbital plane
CAM_DRIFT_DEG = 30.0             # slow azimuth drift over the whole clip
RADIUS_FACTOR = 0.75             # sphere radius = factor * SPH smoothing length h
RADIUS_CAP = 1.0                 # x median initial h (far debris stays small)
GLOW = 1.0                       # compositor glare strength
EMISSION = 1.7

SCENE_NAME = "07_Collision"
TAG = "pc07"


# ----------------------------------------------------------------------------
def script_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def cache_dir():
    return CACHE_DIR or os.path.join(script_dir(), "cache", "theia")


class Cache:
    def __init__(self, d):
        self.dir = d
        with open(os.path.join(d, "meta.json")) as fh:
            self.meta = json.load(fh)
        files = sorted(f for f in os.listdir(d) if f.startswith("frame_") and f.endswith(".npz"))
        self.n = len(files)
        if self.n == 0:
            raise RuntimeError(f"no frames in {d}")
        self.dt_h = float(self.meta["time_unit_hours"])
        self._mem = {}
        f0 = self.get(0)
        self.h0 = float(np.median(f0["h"]))

    @property
    def hours(self):
        return (self.n - 1) * self.dt_h

    def get(self, i):
        i = int(min(max(i, 0), self.n - 1))
        if i not in self._mem:
            if len(self._mem) > 6:
                self._mem.clear()
            z = np.load(os.path.join(self.dir, f"frame_{i:05d}.npz"))
            self._mem[i] = {k: z[k] for k in ("pos", "temp", "h", "mat")}
        return self._mem[i]

    def at_hours(self, h):
        x = min(max(h / self.dt_h, 0.0), self.n - 1.0)
        i = int(math.floor(x))
        w = x - i
        a = self.get(i)
        if w < 1e-6 or i + 1 >= self.n:
            return a["pos"], a["temp"], a["h"], a["mat"]
        b = self.get(i + 1)
        return ((1 - w) * a["pos"] + w * b["pos"], (1 - w) * a["temp"] + w * b["temp"],
                (1 - w) * a["h"] + w * b["h"], a["mat"])


def interp(keys, x):
    xs = [k[0] for k in keys]
    ys = [k[1] for k in keys]
    if x <= xs[0]:
        return ys[0]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            w = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            w = w * w * (3 - 2 * w)  # smoothstep between keys
            return ys[i - 1] + w * (ys[i] - ys[i - 1])
    return ys[-1]


def contact_hours(c):
    imp = c.meta.get("impact") or {}
    return float(imp.get("time_to_contact_hours", 0.8))


def time_keys(c):
    if TIME_KEYS:
        return TIME_KEYS
    tc = contact_hours(c)
    H = c.hours
    ks = [(0.0, 0.0), (4.0, tc), (13.0, tc + 2.5), (21.0, tc + 8.0), (VIDEO_SECONDS, 24.0)]
    out = []
    for s, h in ks:
        if h >= H:
            out.append((s, H))
            break
        out.append((s, h))
    return out


def view_keys(c):
    if VIEW_KEYS:
        return VIEW_KEYS
    tc = contact_hours(c)
    return [(0.0, 9.0), (tc, 8.5), (tc + 1.0, 12.0), (tc + 4.0, 17.0), (tc + 10.0, 22.0), (24.0, 24.0)]


def frame_hours(c, frame):
    return interp(time_keys(c), (frame - 1) / FPS)


# ----------------------------------------------------------------------------
def tag(idb):
    idb[TAG] = True
    return idb


def cleanup():
    sc = bpy.data.scenes.get(SCENE_NAME)
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.curves,
                 bpy.data.cameras, bpy.data.node_groups, bpy.data.worlds):
        for idb in list(coll):
            if idb.get(TAG):
                coll.remove(idb)
    if sc is None:
        sc = bpy.data.scenes.new(SCENE_NAME)
    return sc


def pick_engine(want):
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    if want.upper().startswith("EEVEE"):
        for e in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            if e in items:
                return e
    return "CYCLES"


def mat_particles(primitive):
    m = tag(bpy.data.materials.new("PC07_Molten"))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "temp"
    ac = nt.nodes.new("ShaderNodeAttribute")
    ac.attribute_name = "core"
    for a in (at, ac):
        a.attribute_type = "GEOMETRY"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.85, 0.16, 0.015, 1)     # cool molten: deep orange-red
    cr.elements[1].position = 1.0
    cr.elements[1].color = (1.0, 0.97, 0.88, 1)       # hottest: yellow-white
    e = cr.elements.new(0.30)
    e.color = (1.0, 0.38, 0.04, 1)
    e = cr.elements.new(0.62)
    e.color = (1.0, 0.72, 0.22, 1)
    # iron: deeper red tint
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0, 0, 0, 1)
    nt.links.new(ac.outputs["Fac"], mix.inputs[0])
    nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs["Color"], tint.inputs[6])
    tint.inputs[7].default_value = (0.75, 0.32, 0.22, 1)
    nt.links.new(ramp.outputs["Color"], mix.inputs[6])
    nt.links.new(tint.outputs[2], mix.inputs[7])
    nt.links.new(at.outputs["Fac"], ramp.inputs["Fac"])
    # brightness: hotter = brighter, limb darkening per sphere for a blobby look
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    curve = nt.nodes.new("ShaderNodeMapRange")
    curve.inputs["To Min"].default_value = 0.35
    curve.inputs["To Max"].default_value = 1.0
    nt.links.new(inv.outputs[0], curve.inputs["Value"])
    hot = nt.nodes.new("ShaderNodeMapRange")
    hot.inputs["To Min"].default_value = EMISSION * 0.55
    hot.inputs["To Max"].default_value = EMISSION * 2.2
    nt.links.new(at.outputs["Fac"], hot.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(curve.outputs[0], mul.inputs[0])
    nt.links.new(hot.outputs[0], mul.inputs[1])
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_text():
    m = tag(bpy.data.materials.new("PC07_Text"))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.93, 0.85, 1)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def build_world(sc):
    w = tag(bpy.data.worlds.new("PC07_Space"))
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 260.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.045
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    # random brightness per star, most faint
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 6.0
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(vor.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[0], pw.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(ramp.outputs["Color"], mul.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 3.0
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], bg.inputs["Strength"])
    bg.inputs["Color"].default_value = (0.85, 0.9, 1.0, 1)
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def build_particles(sc, c, primitive):
    N = int(c.meta["n_particles"])
    me = tag(bpy.data.meshes.new("PC07_Particles"))
    me.vertices.add(N)
    for nm in ("temp", "core", "rad"):
        me.attributes.new(nm, "FLOAT", "POINT")
    ob = tag(bpy.data.objects.new("PC07_Particles", me))
    sc.collection.objects.link(ob)
    mat = mat_particles(primitive)
    ng = tag(bpy.data.node_groups.new("PC07_Points", "GeometryNodeTree"))
    if hasattr(ng, "interface"):
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    else:  # pragma: no cover (Blender < 4.0)
        ng.inputs.new("NodeSocketGeometry", "Geometry")
        ng.outputs.new("NodeSocketGeometry", "Geometry")
    gi = ng.nodes.new("NodeGroupInput")
    go = ng.nodes.new("NodeGroupOutput")
    rad = ng.nodes.new("GeometryNodeInputNamedAttribute")
    rad.data_type = "FLOAT"
    rad.inputs["Name"].default_value = "rad"
    sm = ng.nodes.new("GeometryNodeSetMaterial")
    sm.inputs["Material"].default_value = mat
    if primitive == "POINTS":
        mp = ng.nodes.new("GeometryNodeMeshToPoints")
        ng.links.new(gi.outputs[0], mp.inputs["Mesh"])
        ng.links.new(rad.outputs["Attribute"], mp.inputs["Radius"])
        ng.links.new(mp.outputs[0], sm.inputs["Geometry"])
    else:
        ico = ng.nodes.new("GeometryNodeMeshIcoSphere")
        ico.inputs["Radius"].default_value = 1.0
        ico.inputs["Subdivisions"].default_value = 2
        sh = ng.nodes.new("GeometryNodeSetShadeSmooth")
        ng.links.new(ico.outputs["Mesh"], sh.inputs["Geometry"])
        iop = ng.nodes.new("GeometryNodeInstanceOnPoints")
        ng.links.new(gi.outputs[0], iop.inputs["Points"])
        ng.links.new(sh.outputs[0], iop.inputs["Instance"])
        ng.links.new(rad.outputs["Attribute"], iop.inputs["Scale"])
        rz = ng.nodes.new("GeometryNodeRealizeInstances")
        ng.links.new(iop.outputs["Instances"], rz.inputs["Geometry"])
        ng.links.new(rz.outputs[0], sm.inputs["Geometry"])
    ng.links.new(sm.outputs[0], go.inputs[0])
    mod = ob.modifiers.new("PC07_Points", "NODES")
    mod.node_group = ng
    return ob


def add_text(sc, cam, body, size, y, mat, bold=False):
    cu = tag(bpy.data.curves.new("PC07_Txt", "FONT"))
    cu.body = body
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.size = size
    cu.extrude = 0.0
    if bold:
        cu.offset = 0.0
        cu.space_character = 1.05
    ob = tag(bpy.data.objects.new("PC07_Txt", cu))
    sc.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob.parent = cam
    ob.location = (0.0, y, -1.0)
    return ob


def look_at(ob, eye, target, up):
    f = (Vector(target) - Vector(eye)).normalized()
    r = f.cross(Vector(up)).normalized()
    u = r.cross(f)
    M = Matrix(((r.x, u.x, -f.x), (r.y, u.y, -f.y), (r.z, u.z, -f.z)))
    ob.matrix_world = Matrix.Translation(eye) @ M.to_4x4()


def build_compositor(sc, preview):
    glare_strength = GLOW
    if bpy.app.background and hasattr(sc.render, "compositor_device"):
        sc.render.compositor_device = "CPU"     # GPU compositor needs EGL -> abort when headless
    if hasattr(sc, "compositing_node_group"):        # Blender 5.x
        ng = tag(bpy.data.node_groups.new("PC07_Comp", "CompositorNodeTree"))
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        sc.compositing_node_group = ng
        rl = ng.nodes.new("CompositorNodeRLayers")
        rl.scene = sc
        go = ng.nodes.new("NodeGroupOutput")
        nodes, links, out_in = ng.nodes, ng.links, go.inputs[0]
    else:                                             # Blender 4.x
        sc.use_nodes = True
        tree = sc.node_tree
        tree.nodes.clear()
        rl = tree.nodes.new("CompositorNodeRLayers")
        comp = tree.nodes.new("CompositorNodeComposite")
        nodes, links, out_in = tree.nodes, tree.links, comp.inputs[0]

    def glare(src, kind, size, strength, thresh):
        g = nodes.new("CompositorNodeGlare")
        if "glare_type" in g.bl_rna.properties:        # 4.2 - 4.3
            g.glare_type = kind
            g.quality = "MEDIUM"
            if hasattr(g, "size"):
                g.size = int(size)
            if hasattr(g, "threshold"):
                g.threshold = thresh
            if hasattr(g, "mix"):
                g.mix = -1.0 + min(strength, 1.0)
        else:                                          # 4.4+ / 5.x socket API
            ty = g.inputs.get("Type")
            for nm in ({"FOG_GLOW": ("Fog Glow", "FOG_GLOW"), "BLOOM": ("Bloom", "BLOOM")}[kind]):
                try:
                    ty.default_value = nm
                    break
                except Exception:
                    pass
            q = g.inputs.get("Quality")
            if q is not None:
                for nm in ("Medium", "MEDIUM"):
                    try:
                        q.default_value = nm
                        break
                    except Exception:
                        pass
            for nm, val in (("Threshold", thresh), ("Strength", strength), ("Size", size / 9.0),
                            ("Saturation", 1.0)):
                s = g.inputs.get(nm)
                if s is not None:
                    try:
                        s.default_value = val
                    except Exception:
                        pass
        links.new(src, g.inputs[0])
        return g.outputs[0]

    img = rl.outputs["Image"]
    img = glare(img, "BLOOM", 7, 0.6 * glare_strength, 0.95)
    img = glare(img, "FOG_GLOW", 6, 0.25 * glare_strength, 1.5)
    links.new(img, out_in)


def setup_render(sc, preview, c):
    r = sc.render
    if preview:
        r.engine = "CYCLES"
        r.resolution_x, r.resolution_y = PREVIEW_RES
        sc.cycles.samples = PREVIEW_SAMPLES
    else:
        r.engine = pick_engine(ENGINE) if ENGINE.upper().startswith("EEVEE") else "CYCLES"
        r.resolution_x, r.resolution_y = RESOLUTION
    r.resolution_percentage = 100
    if r.engine == "CYCLES":
        sc.cycles.device = "CPU"
        if not preview:
            sc.cycles.samples = CYCLES_SAMPLES
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 0
        sc.cycles.diffuse_bounces = 0
    else:
        ee = sc.eevee
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = EEVEE_SAMPLES
        if hasattr(ee, "use_bloom"):
            ee.use_bloom = False
    sc.view_settings.view_transform = "Standard"     # keeps the molten orange saturated
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    r.fps = FPS
    sc.frame_start = 1
    sc.frame_end = int(round(time_keys(c)[-1][0] * FPS)) or 1
    r.film_transparent = False


# ----------------------------------------------------------------------------
STATE = {}


def update(sc, frame=None):
    c = STATE.get("cache")
    if c is None:
        return
    f = sc.frame_current if frame is None else frame
    hrs = frame_hours(c, f)
    pos, temp, h, mat = c.at_hours(hrs)
    ob = STATE["ob"]
    me = ob.data
    N = len(pos)
    me.vertices.foreach_set("co", pos.astype(np.float32).ravel())
    me.attributes["temp"].data.foreach_set("value", np.clip(temp, 0, 1).astype(np.float32))
    me.attributes["core"].data.foreach_set("value", ((mat == 0) | (mat == 2)).astype(np.float32))
    rad = RADIUS_FACTOR * np.minimum(h, RADIUS_CAP * c.h0)
    me.attributes["rad"].data.foreach_set("value", rad.astype(np.float32))
    me.update()
    # camera: framing + slow azimuth drift
    cam = STATE["cam"]
    vh = interp(view_keys(c), hrs)
    lens = cam.data.lens
    D = 0.5 * vh * lens / 18.0
    s = (f - 1) / max(sc.frame_end - 1, 1)
    az = math.radians(CAM_DRIFT_DEG * s)                # screen-up direction in the orbital plane
    tilt = math.radians(CAM_TILT_DEG)
    up = Vector((math.cos(az), math.sin(az), 0.0))     # impactor starts at +x -> comes from the top
    eye = Vector((0, 0, D * math.cos(tilt))) - up * (D * math.sin(tilt))
    look_at(cam, eye, (0, 0, 0), up)
    STATE["clock"].data.body = f"Simulated: {hrs:.1f} h"


def frame_handler(scene, *args):
    if scene.name == SCENE_NAME:
        update(scene)


def register_handler():
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "frame_handler":
            bpy.app.handlers.frame_change_pre.remove(h)
    bpy.app.handlers.frame_change_pre.append(frame_handler)


def build(preview=False):
    c = Cache(cache_dir())
    print(f"[pc07] cache {c.dir}: {c.n} frames, {c.hours:.1f} h, N={c.meta['n_particles']}")
    sc = cleanup()
    try:
        bpy.context.window.scene = sc
    except Exception:
        pass
    setup_render(sc, preview, c)
    prim = PRIMITIVE
    if prim == "AUTO":
        prim = "POINTS" if sc.render.engine == "CYCLES" else "SPHERES"
    build_world(sc)
    ob = build_particles(sc, c, prim)
    camd = tag(bpy.data.cameras.new("PC07_Cam"))
    camd.lens = 50.0
    camd.clip_start = 0.05
    camd.clip_end = 1000.0
    cam = tag(bpy.data.objects.new("PC07_Cam", camd))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tm = mat_text()
    add_text(sc, cam, CAPTION, 0.040, 0.27, tm)
    add_text(sc, cam, SUBCAPTION, 0.020, 0.232, tm)
    clock = add_text(sc, cam, "Simulated: 0.0 h", 0.024, -0.30, tm)
    STATE.update(cache=c, ob=ob, cam=cam, clock=clock)
    build_compositor(sc, preview)
    register_handler()
    sc.frame_set(1)
    update(sc, 1)
    return sc, c


def out_root():
    p = bpy.path.abspath(OUTPUT_DIR) if bpy.data.filepath else os.path.join(script_dir(), OUTPUT_DIR[2:])
    os.makedirs(p, exist_ok=True)
    return p


def render_animation(sc, frames=None):
    root = out_root()
    fr = frames or range(sc.frame_start, sc.frame_end + 1)
    sc.render.image_settings.file_format = "PNG"
    for f in fr:
        sc.frame_set(f)
        update(sc, f)          # explicit (handler also fires) -> never renders a stale frame
        sc.render.filepath = os.path.join(root, f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[pc07] frame {f} ({frame_hours(STATE['cache'], f):.2f} h) -> {sc.render.filepath}", flush=True)


def render_preview(sc, c, outdir=None):
    outdir = outdir or os.path.join(script_dir(), "preview")
    os.makedirs(outdir, exist_ok=True)
    tc = contact_hours(c)
    hrs = PREVIEW_HOURS or [max(tc - 0.35, 0.0), tc + 0.15, tc + 0.6, tc + 1.5, tc + 4.0, c.hours]
    keys = time_keys(c)
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 82
    names = ["1_approach", "2_contact", "3_arms", "4_splash", "5_recollapse", "6_disc"]
    for k, h in enumerate(hrs):
        h = min(h, c.hours)
        # find the video frame showing that simulated hour
        f = 1
        for fi in range(1, sc.frame_end + 1):
            if frame_hours(c, fi) >= h - 1e-6:
                f = fi
                break
        else:
            f = sc.frame_end
        sc.frame_set(f)
        update(sc, f)
        nm = names[k] if k < len(names) else f"{k + 1}_extra"
        sc.render.filepath = os.path.join(outdir, f"{nm}.jpg")
        bpy.ops.render.render(write_still=True, scene=sc.name)
        print(f"[pc07] preview {nm}: frame {f}, {frame_hours(c, f):.2f} h -> {sc.render.filepath}", flush=True)


def main():
    global CACHE_DIR, PREVIEW_RES, PREVIEW_SAMPLES, PREVIEW_HOURS
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_render = RENDER or "--render" in argv
    do_prev = PREVIEW or "--preview" in argv
    if "--cache" in argv:
        CACHE_DIR = argv[argv.index("--cache") + 1]
    outdir = argv[argv.index("--outdir") + 1] if "--outdir" in argv else None
    if "--res" in argv:
        w, h = argv[argv.index("--res") + 1].split("x")
        PREVIEW_RES = (int(w), int(h))
    if "--hours" in argv:
        PREVIEW_HOURS = [float(x) for x in argv[argv.index("--hours") + 1].split(",")]
    if "--samples" in argv:
        PREVIEW_SAMPLES = int(argv[argv.index("--samples") + 1])
    sc, c = build(preview=do_prev and not do_render)
    frames = None
    if "--frames" in argv:
        a, b = argv[argv.index("--frames") + 1].split("-")
        frames = range(int(a), int(b) + 1)
    if do_prev and not do_render:
        render_preview(sc, c, outdir)
    if do_render:
        render_animation(sc, frames)


if __name__ == "__main__":
    main()
