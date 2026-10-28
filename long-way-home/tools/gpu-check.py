# blender -b --factory-startup -P gpu-check.py
# Turns on OptiX (or CUDA), lists devices, renders a quick Cycles test and reports the time.
import bpy, os, tempfile, time

prefs = bpy.context.preferences.addons['cycles'].preferences
chosen = None
for kind in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = kind
    except TypeError:
        continue
    prefs.get_devices()
    if any(d.type == kind for d in prefs.devices):
        chosen = kind
        break
for d in prefs.devices:
    d.use = d.type == chosen
print('\nCompute backend:', chosen)
for d in prefs.devices:
    print(f'  {d.name:40s} {d.type:6s} use={d.use}')

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU' if chosen else 'CPU'
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
bpy.ops.mesh.primitive_monkey_add(location=(0, 0, 1))
bpy.ops.object.modifier_add(type='SUBSURF')
bpy.context.object.modifiers[0].levels = 2
out = os.path.join(tempfile.gettempdir(), 'gpu_check.png')
scene.render.filepath = out
t = time.time()
bpy.ops.render.render(write_still=True)
print(f'\nTest frame 1080x1920, 128 samples: {time.time() - t:.1f}s  ->  {out}')
print('GPU OK' if chosen else 'WARNING: no NVIDIA GPU backend found; update the NVIDIA driver')
