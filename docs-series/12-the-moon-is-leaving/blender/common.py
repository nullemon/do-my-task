"""Shared Blender 5.1 (bpy, Cycles CPU) helpers for the three hero stills of "THE MOON IS LEAVING"."""
import bpy, bmesh, sys, os, math
import numpy as np
from mathutils import Matrix, Vector
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/12-the-moon-is-leaving"


def setup(res=(2160, 2160), samples=96, transparent=True, bounces=6, world=(0.0, 0.0, 0.0), wstr=1.0, exposure=0.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
    c.device = "CPU"; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02
    c.max_bounces = bounces; c.diffuse_bounces = 2; c.glossy_bounces = bounces; c.transmission_bounces = bounces
    try:
        c.use_denoising = True; c.denoiser = "OPENIMAGEDENOISE"
    except Exception as e:
        print("no OIDN", e); c.use_denoising = False
    sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", "2"))
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = int(os.environ.get("PCT", "100"))
    sc.render.film_transparent = transparent
    sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "16"
    sc.view_settings.view_transform = "Filmic" if "Filmic" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "AgX"
    sc.view_settings.exposure = exposure
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*world, 1); bg.inputs[1].default_value = wstr
    return sc


def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    return m, nt, nt.nodes["Principled BSDF"]


def simple(name, col, rough=0.5, metal=0.0, emit=None, estr=1.0, noise_bump=None, trans=0.0, ior=1.45):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if trans: b.inputs["Transmission Weight"].default_value = trans; b.inputs["IOR"].default_value = ior
    if emit: b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = estr
    if noise_bump:
        sc_, st = noise_bump
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = sc_; n.inputs["Detail"].default_value = 8
        bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = st
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def obj_from(verts, faces, name, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces]); me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if mat: ob.data.materials.append(mat)
    return ob


def grid_mesh(X, Y, Z, name, mat=None):
    """fast grid mesh from 2D numpy arrays"""
    ny, nx = X.shape
    v = np.stack([X, Y, Z], -1).reshape(-1, 3).astype(np.float32)
    i = np.arange(ny * nx).reshape(ny, nx)
    f = np.stack([i[:-1, :-1], i[:-1, 1:], i[1:, 1:], i[1:, :-1]], -1).reshape(-1, 4)
    me = bpy.data.meshes.new(name); me.vertices.add(len(v)); me.vertices.foreach_set("co", v.ravel())
    me.loops.add(f.size); me.loops.foreach_set("vertex_index", f.ravel().astype(np.int32))
    me.polygons.add(len(f)); me.polygons.foreach_set("loop_start", np.arange(0, f.size, 4, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(len(f), 4, np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(f), bool)); me.update(calc_edges=True); me.validate()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if mat: ob.data.materials.append(mat)
    return ob


def prim(kind, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), smooth=False, bevel=0.0, **kw):
    bm = bmesh.new()
    if kind == "box": bmesh.ops.create_cube(bm, size=1.0)
    elif kind == "cyl": bmesh.ops.create_cone(bm, cap_ends=True, segments=kw.get("seg", 48), radius1=1, radius2=kw.get("r2", 1), depth=1)
    elif kind == "sphere": bmesh.ops.create_uvsphere(bm, u_segments=kw.get("seg", 48), v_segments=kw.get("seg", 48) // 2, radius=1)
    elif kind == "ico": bmesh.ops.create_icosphere(bm, subdivisions=kw.get("sub", 3), radius=1)
    me = bpy.data.meshes.new(kind); bm.to_mesh(me); bm.free()
    if smooth: me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(kind, me); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot; ob.scale = scale
    if mat: ob.data.materials.append(mat)
    if bevel:
        md = ob.modifiers.new("bev", "BEVEL"); md.width = bevel; md.segments = 2
    return ob


def parent(ch, par):
    for c in ch: c.parent = par


def empty(loc=(0, 0, 0), rot=(0, 0, 0)):
    e = bpy.data.objects.new("e", None); bpy.context.scene.collection.objects.link(e); e.location = loc; e.rotation_euler = rot; return e


def sun(direction_to, strength, col=(1, 1, 1), angle=0.5):
    l = bpy.data.lights.new("sun", "SUN"); l.energy = strength; l.color = col; l.angle = math.radians(angle)
    o = bpy.data.objects.new("sun", l); bpy.context.scene.collection.objects.link(o)
    d = Vector(direction_to).normalized(); o.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler(); return o


def point(loc, strength, col=(1, 0.8, 0.5), radius=0.1):
    l = bpy.data.lights.new("p", "POINT"); l.energy = strength; l.color = col; l.shadow_soft_size = radius
    o = bpy.data.objects.new("p", l); bpy.context.scene.collection.objects.link(o); o.location = loc; return o


def camera(loc, target, lens=35, sensor=36, dof=None, fstop=4.0, shift=(0, 0)):
    cam = bpy.data.cameras.new("cam"); cam.lens = lens; cam.sensor_width = sensor; cam.shift_x, cam.shift_y = shift
    o = bpy.data.objects.new("cam", cam); bpy.context.scene.collection.objects.link(o); o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if dof: cam.dof.use_dof = True; cam.dof.focus_distance = dof; cam.dof.aperture_fstop = fstop
    bpy.context.scene.camera = o; cam.clip_end = 20000; cam.clip_start = 0.01; return o


def project(p):
    """world point -> pixel (x, y from top-left) at full resolution"""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene; bpy.context.view_layer.update()
    v = world_to_camera_view(sc, sc.camera, Vector(p)); return [v.x * sc.render.resolution_x, (1 - v.y) * sc.render.resolution_y]


def fbm(X, Y, octs=6, base=1.0, gain=0.5, seed=0, ridged=False):
    """value-noise fbm on numpy arrays (bilinear lattice with smoothstep)"""
    rng = np.random.default_rng(seed); out = np.zeros_like(X, dtype=np.float32); amp = 1.0; f = base; tot = 0
    for o in range(octs):
        tab = rng.uniform(-1, 1, (256, 256)).astype(np.float32); ox, oy = rng.uniform(0, 256, 2)
        x = X * f + ox; y = Y * f + oy; xi = np.floor(x).astype(np.int64); yi = np.floor(y).astype(np.int64)
        fx = (x - xi).astype(np.float32); fy = (y - yi).astype(np.float32); fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
        a = tab[yi & 255, xi & 255]; b = tab[yi & 255, (xi + 1) & 255]; c = tab[(yi + 1) & 255, xi & 255]; d = tab[(yi + 1) & 255, (xi + 1) & 255]
        n = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
        if ridged: n = 1 - 2 * np.abs(n)
        out += amp * n; tot += amp; amp *= gain; f *= 2.03
    return out / tot


def render(path):
    sc = bpy.context.scene; sc.render.filepath = path; bpy.ops.render.render(write_still=True); print("wrote", path)
