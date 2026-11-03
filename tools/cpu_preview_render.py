"""Render a low-res CPU preview video of any format script (no GPU needed).

Builds the scene by running the format script with no render args, then
overrides the render settings to Cycles CPU, low samples, reduced resolution,
every Nth frame, and writes PNGs. Encode with ffmpeg afterwards.

Usage (bpy module):
  python tools/cpu_preview_render.py SCRIPT OUTDIR [res_pct] [samples] [step] [first] [last]
"""
import sys, os, runpy
script, out = sys.argv[1], sys.argv[2]
res = int(sys.argv[3]) if len(sys.argv) > 3 else 33
spp = int(sys.argv[4]) if len(sys.argv) > 4 else 6
step = int(sys.argv[5]) if len(sys.argv) > 5 else 2
first = int(sys.argv[6]) if len(sys.argv) > 6 else None
last = int(sys.argv[7]) if len(sys.argv) > 7 else None

sys.argv = ["blender", "--"]
runpy.run_path(script, run_name="__main__")

import bpy
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = spp
try:
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
sc.cycles.max_bounces = 4
sc.render.resolution_percentage = res
sc.frame_step = step
if first: sc.frame_start = first
if last: sc.frame_end = last
os.makedirs(out, exist_ok=True)
try:
    sc.render.image_settings.media_type = "IMAGE"  # Blender 5.x
except Exception:
    pass
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = os.path.join(out, "f_")
print("RENDER", sc.frame_start, sc.frame_end, step, sc.render.resolution_x, res)
bpy.ops.render.render(animation=True)
