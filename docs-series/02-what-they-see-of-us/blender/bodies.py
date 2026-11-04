"""WHAT THEY SEE OF US - Earth and Moon hero stills (Blender, Cycles CPU).
Earth: NASA Blue Marble texture (public domain, via the three-globe npm package), sun lamp from
near the camera (we look back at the day side), thin blue atmospheric rim. Moon: procedural maria.
Each is rendered once as an RGBA still; comp.py scales it by 1/distance as we fly away.
"""
import sys, os, math
import bpy
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
W = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us"
which = ARGV[0] if ARGV else "earth"
RES = 1200

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16
sc.cycles.use_denoising = False; sc.cycles.max_bounces = 0
sc.render.threads_mode = "FIXED"; sc.render.threads = 2
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)

bpy.ops.mesh.primitive_uv_sphere_add(segments=192, ring_count=96, radius=1.0)
body = bpy.context.object
bpy.ops.object.shade_smooth()
mat = bpy.data.materials.new("m"); mat.use_nodes = True; nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.9
if which == "earth":
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(W, "tex", "earth-blue-marble.jpg"))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    # face Africa/Europe toward the camera (+Y view below), north tilted slightly toward us
    body.rotation_euler = (math.radians(14), 0, math.radians(-105))
else:
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 8; noise.inputs["Roughness"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.53; ramp.color_ramp.elements[0].color = (0.62, 0.61, 0.59, 1)
    ramp.color_ramp.elements[1].position = 0.60; ramp.color_ramp.elements[1].color = (0.20, 0.20, 0.21, 1)
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 40; n2.inputs["Detail"].default_value = 10
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.35
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"]); nt.links.new(n2.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
body.data.materials.append(mat)

if False:   # (atmosphere rim now added in numpy, gen_tex.py): emission strongest at grazing angles, otherwise transparent
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.018)
    atm = bpy.context.object; bpy.ops.object.shade_smooth()
    am = bpy.data.materials.new("atm"); am.use_nodes = True; an = am.node_tree; an.nodes.clear()
    lw = an.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    pw = an.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 3.0
    em = an.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.35, 0.6, 1.0, 1)
    em.inputs["Strength"].default_value = 1.6
    tr = an.nodes.new("ShaderNodeBsdfTransparent")
    ad = an.nodes.new("ShaderNodeAddShader"); mx = an.nodes.new("ShaderNodeMixShader")
    o = an.nodes.new("ShaderNodeOutputMaterial")
    an.links.new(lw.outputs["Facing"], pw.inputs[0])
    an.links.new(pw.outputs[0], mx.inputs[0]); an.links.new(tr.outputs[0], mx.inputs[1]); an.links.new(em.outputs[0], mx.inputs[2])
    an.links.new(mx.outputs[0], o.inputs[0])
    am.blend_method = "BLEND" if hasattr(am, "blend_method") else None
    atm.data.materials.append(am)

sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 7.5 if which == "earth" else 5.0
sun.angle = math.radians(0.53)
so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(90 - 12), 0, math.radians(-28))  # light from camera side, upper-left

camd = bpy.data.cameras.new("c"); dist = 6.0
camd.angle = 2 * math.asin(1.05 / dist) * 1.02
cam = bpy.data.objects.new("c", camd); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -dist, 0); cam.rotation_euler = (math.radians(90), 0, 0)
sc.render.filepath = os.path.join(W, "tex", f"{which}.png")
bpy.ops.render.render(write_still=True)
