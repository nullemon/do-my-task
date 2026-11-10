"""Simplified spacecraft stills (Blender 5.1 bpy, Cycles CPU), RGBA 900x900, lit like the asteroid sprite.
Usage: /home/user/bpyenv/bin/python craft.py apex|ramses
apex   : OSIRIS-APEX (ex OSIRIS-REx) - box bus in gold MLI, 2 m dish on top, two solar wings canted back, sampler arm.
ramses : ESA Ramses (Hera-derived design) - cubic bus, two long three-panel wings, side-mounted dish, two CubeSat boxes.
Recognisable layouts only - not engineering models."""
import bpy, bmesh, sys, os, math
from mathutils import Matrix, Vector
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/10-apophis-2029"
which = sys.argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; c = sc.cycles
c.device = "CPU"; c.samples = 96; c.use_denoising = False; c.max_bounces = 4
sc.render.threads_mode = "FIXED"; sc.render.threads = 3
sc.render.resolution_x = sc.render.resolution_y = 900; sc.render.film_transparent = True
sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.16, 0.19, 0.27, 1); bg.inputs[1].default_value = 1.0


def mat(name, col, rough=0.5, metal=0.0, bump=None, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if bump:
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexVoronoi" if bump[0] == "v" else "ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = bump[1]; bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump[2]; bp.inputs["Distance"].default_value = 0.02
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def cell_mat():
    m = bpy.data.materials.new("cells"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.012, 0.022, 0.085, 1); br.inputs["Color2"].default_value = (0.016, 0.03, 0.11, 1); br.inputs["Mortar"].default_value = (0.30, 0.32, 0.36, 1)
    br.inputs["Scale"].default_value = 9.0; br.inputs["Mortar Size"].default_value = 0.012; br.offset = 0.0
    br.inputs["Brick Width"].default_value = 0.42; br.inputs["Row Height"].default_value = 0.42
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"]); nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.22; b.inputs["Metallic"].default_value = 0.2
    return m


GOLD = mat("mli", (0.95, 0.66, 0.24), rough=0.42, metal=0.55, bump=("v", 22.0, 0.8))
GOLD2 = mat("mli2", (0.75, 0.47, 0.16), rough=0.5, metal=0.5, bump=("n", 30.0, 0.9))
SILV = mat("silver", (0.80, 0.82, 0.86), rough=0.3, metal=0.7, bump=("v", 26.0, 0.6))
RAD = mat("radiator", (0.92, 0.93, 0.95), rough=0.25, metal=0.0)
DARK = mat("kapton", (0.05, 0.045, 0.04), rough=0.5, metal=0.3, bump=("n", 25.0, 0.5))
WHITE = mat("white", (0.82, 0.82, 0.80), rough=0.55)
ALU = mat("alu", (0.55, 0.57, 0.6), rough=0.35, metal=0.9)
CELL = cell_mat()
BACK = mat("panelback", (0.10, 0.10, 0.11), rough=0.6)


def add(bm, m, name, smooth=False):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.data.materials.append(m); return ob


def box(m, size, loc, rot=None, name="box", bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if bevel: bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect="EDGES")
    ob = add(bm, m, name); ob.matrix_world = Matrix.Translation(loc) @ (rot or Matrix.Identity(4)); return ob


def cyl(m, r1, r2, depth, loc, rot=None, seg=32, name="cyl", smooth=True):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=depth)
    ob = add(bm, m, name, smooth); ob.matrix_world = Matrix.Translation(loc) @ (rot or Matrix.Identity(4)); return ob


def dish(r, depth, loc, rot, m=WHITE):
    bm = bmesh.new(); n, k = 48, 10
    rings = []
    for j in range(k + 1):
        rr = r * j / k; z = depth * (rr / r) ** 2
        rings.append([bm.verts.new((rr * math.cos(2 * math.pi * i / n), rr * math.sin(2 * math.pi * i / n), z)) for i in range(n)] if j else [bm.verts.new((0, 0, 0))])
    for i in range(n): bm.faces.new((rings[0][0], rings[1][i], rings[1][(i + 1) % n]))
    for j in range(1, k):
        for i in range(n): bm.faces.new((rings[j][i], rings[j + 1][i], rings[j + 1][(i + 1) % n], rings[j][(i + 1) % n]))
    ob = add(bm, m, "dish", True); so = ob.modifiers.new("s", "SOLIDIFY"); so.thickness = 0.02
    ob.matrix_world = Matrix.Translation(loc) @ rot
    # feed + struts
    for a in (0, 120, 240):
        p0 = Vector((r * 0.8 * math.cos(math.radians(a)), r * 0.8 * math.sin(math.radians(a)), depth * 0.64)); p1 = Vector((0, 0, r * 0.62))
        d = p1 - p0; s = cyl(ALU, 0.012, 0.012, d.length, (0, 0, 0), None, 8, "strut")
        s.matrix_world = Matrix.Translation(loc) @ rot @ Matrix.Translation((p0 + p1) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    f = cyl(ALU, 0.07, 0.05, 0.12, (0, 0, 0), None, 16, "feed"); f.matrix_world = Matrix.Translation(loc) @ rot @ Matrix.Translation((0, 0, r * 0.62))
    return ob


def panel(size, loc, rot):
    """solar panel: cells on +Z face, dark back, thin frame"""
    box(CELL, (size[0], size[1], 0.02), loc, rot, "cells").matrix_world = Matrix.Translation(loc) @ rot @ Matrix.Translation((0, 0, 0.012))
    box(BACK, (size[0] + 0.04, size[1] + 0.04, 0.02), loc, rot, "back")


import random
random.seed(7)
def greeble(half, n=26):
    """foil patches, radiators, boxes and conduits on the four side faces and the bottom of a box bus (half-sizes)"""
    hx, hy, hz = half
    faces = [((1, 0, 0), (0, 1, 0), (0, 0, 1), hx, hy, hz), ((-1, 0, 0), (0, 1, 0), (0, 0, 1), hx, hy, hz),
             ((0, 1, 0), (1, 0, 0), (0, 0, 1), hy, hx, hz), ((0, -1, 0), (1, 0, 0), (0, 0, 1), hy, hx, hz)]
    for nrm, u, v, d, su, sv in faces:
        nrm, u, v = Vector(nrm), Vector(u), Vector(v)
        # foil panel seams: a grid of slightly different patches
        nu, nv = 3, 3
        for i in range(nu):
            for j in range(nv):
                m = random.choice([GOLD, GOLD, GOLD2, GOLD2, SILV, DARK]) if random.random() < 0.8 else RAD
                cu = (-1 + (2 * i + 1) / nu) * su; cv = (-1 + (2 * j + 1) / nv) * sv
                size = u * (2 * su / nu - 0.035) + v * (2 * sv / nv - 0.035) + nrm * 0.03
                size = Vector((abs(size.x), abs(size.y), abs(size.z)))
                box(m, size, nrm * (d + 0.012) + u * cu + v * cv, name="patch", bevel=0.006)
        for k in range(n // 4):
            m = random.choice([DARK, ALU, WHITE, SILV]); a = random.uniform(0.08, 0.26); b = random.uniform(0.08, 0.3); h = random.uniform(0.04, 0.16)
            cu = random.uniform(-0.8, 0.8) * su; cv = random.uniform(-0.8, 0.8) * sv
            size = u * a + v * b + nrm * h; size = Vector((abs(size.x), abs(size.y), abs(size.z)))
            box(m, size, nrm * (d + h / 2 + 0.02) + u * cu + v * cv, name="gre", bevel=0.008)
        for k in range(2):
            cv = random.uniform(-0.8, 0.8) * sv; L = random.uniform(0.6, 1.6) * su
            rot = (nrm.cross(u)).to_track_quat("Y", "Z").to_matrix().to_4x4() if False else u.to_track_quat("Z", "Y").to_matrix().to_4x4()
            cyl(ALU, 0.015, 0.015, L, nrm * (d + 0.04) + v * cv + u * random.uniform(-0.2, 0.2) * su, rot, 8, "pipe")


RX = lambda a: Matrix.Rotation(math.radians(a), 4, "X"); RY = lambda a: Matrix.Rotation(math.radians(a), 4, "Y"); RZ = lambda a: Matrix.Rotation(math.radians(a), 4, "Z")
if which == "apex":
    box(GOLD, (2.3, 2.3, 1.9), (0, 0, 0), bevel=0.05); greeble((1.15, 1.15, 0.95))
    box(DARK, (2.36, 2.36, 0.18), (0, 0, 0.9))                      # top deck rim
    dish(1.05, 0.30, (0, 0, 1.05), Matrix.Identity(4))
    for sx in (-1, 1):
        cyl(ALU, 0.05, 0.05, 0.5, (sx * 1.4, 0, -0.75), RY(90), 12)
        panel((2.5, 1.9), (sx * 2.85, 0, -0.75), RY(sx * 10) @ RX(62))
    # instrument deck: cameras and the folded sampler arm
    box(DARK, (0.5, 0.4, 0.45), (0.55, -1.25, 0.3), bevel=0.02); cyl(DARK, 0.11, 0.13, 0.3, (0.55, -1.55, 0.3), RX(90), 20)
    box(WHITE, (0.35, 0.3, 0.3), (-0.5, -1.28, 0.45), bevel=0.02); cyl(DARK, 0.07, 0.08, 0.22, (-0.5, -1.5, 0.45), RX(90), 16)
    cyl(ALU, 0.035, 0.035, 1.5, (0, -1.22, -0.55), RY(90), 10); cyl(ALU, 0.035, 0.035, 0.9, (0.75, -1.5, -0.55), RX(90) @ RZ(0), 10)
    cyl(ALU, 0.16, 0.16, 0.07, (0.75, -1.98, -0.55), RX(90), 24)    # sampler head
    for sx in (-1, 1):
        for sy in (-1, 1): cyl(DARK, 0.09, 0.05, 0.16, (sx * 0.8, sy * 0.8, -1.03), None, 14)
    cyl(DARK, 0.28, 0.16, 0.3, (0, 0, -1.1), None, 20)
    view = Vector((-0.50, -0.74, 0.44)); dist = 20.0; lens = 85
else:
    box(GOLD, (1.6, 1.6, 1.7), (0, 0, 0), bevel=0.04); greeble((0.8, 0.8, 0.85), 20)
    box(DARK, (1.64, 1.64, 0.12), (0, 0, 0.82)); box(DARK, (1.64, 1.64, 0.12), (0, 0, -0.82))
    dish(0.62, 0.17, (0, -0.86, 0.1), RX(90))
    for sx in (-1, 1):
        cyl(ALU, 0.04, 0.04, 0.45, (sx * 1.0, 0, 0), RY(90), 12)
        for k in range(3):
            panel((1.55, 1.25), (sx * (2.05 + k * 1.62), 0, 0), RX(66))
            if k: cyl(ALU, 0.025, 0.025, 0.1, (sx * (2.05 + k * 1.62 - 0.81), 0, 0), RY(90), 8)
    # top deck: instruments and two CubeSat deployers
    box(DARK, (0.36, 0.24, 0.24), (-0.35, -0.5, 1.0), bevel=0.015); box(DARK, (0.36, 0.24, 0.24), (0.35, -0.5, 1.0), bevel=0.015)
    box(WHITE, (0.3, 0.3, 0.34), (0.0, 0.3, 1.02), bevel=0.02); cyl(DARK, 0.08, 0.09, 0.2, (0.0, 0.08, 1.02), RX(90), 16)
    box(ALU, (0.25, 0.25, 0.4), (-0.5, 0.35, 1.05), bevel=0.01)
    for sx in (-1, 1):
        for sy in (-1, 1): cyl(DARK, 0.07, 0.04, 0.14, (sx * 0.6, sy * 0.6, -0.93), None, 14)
    cyl(DARK, 0.2, 0.12, 0.25, (0, 0, -0.98), None, 20)
    view = Vector((-0.42, -0.78, 0.46)); dist = 30.0; lens = 85

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = lens; cam.location = view.normalized() * dist
cam.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
R = cam.matrix_world.to_3x3()
def sun(d_cam, strength, col, ang):
    l = bpy.data.lights.new("s", "SUN"); l.energy = strength; l.color = col; l.angle = math.radians(ang)
    o = bpy.data.objects.new("s", l); sc.collection.objects.link(o)
    d = R @ Vector(d_cam); o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
sun((-0.72, 0.60, 0.34), 6.0, (1.0, 0.97, 0.92), 0.6)        # same camera-space direction as the asteroid's key light
sun((0.8, -0.5, 0.25), 0.9, (0.45, 0.62, 1.0), 20)
sc.render.filepath = os.path.join(SCR, "spr", which + ".png"); bpy.ops.render.render(write_still=True)
