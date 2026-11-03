# Build instructions (shared for every OMINOUS video)

Goal: produce ONE finished, beautiful, ominous vertical video + the Blender script that makes it.

Read /home/user/do-my-task/ominous/CONCEPTS.md (series look + your concept).

Deliverables, only inside your folder /home/user/do-my-task/ominous/0N-name/ :
- `script.py` — single self-contained Blender Python script (procedural only, no downloads). CONFIG block at top (fps 24, duration, resolution 1080x1920, engine, samples, output). Works headless: `blender -b -P script.py -- --render`. Should also work for Blender 4.2–5.x (guard API differences: Eevee id BLENDER_EEVEE_NEXT on 4.x vs BLENDER_EEVEE on 5.x; in 5.x set image_settings.media_type='IMAGE' BEFORE file_format='PNG'; avoid action.fcurves direct access or guard it; Sky texture enum names changed in 5.x — guard).
- `soundtrack.py` — pure Python + numpy, writes `soundtrack.wav` (48 kHz) synced to the video beats: low ominous drone, sub-bass swells, subtle hits on text beats, silence/cut at the end. Must sound good, not harsh.
- `README.md` — concept, what's real (cite facts briefly), how to run, title + caption + hashtags + pinned comment for posting.
- The final video: `/home/user/do-my-task/ominous/videos/0N-name.mp4`.

Environment (important):
- No `blender` binary. Blender 5.1.2 is a Python module: `/home/user/bpyenv/bin/python` (import bpy, numpy available). Run your script as `/home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--', ...]; exec(compile(open(p).read(),p,'exec'))"`.
- No GPU: Eevee and Workbench fail (no libEGL). Render with Cycles CPU. Only 4 CPU cores shared by 6 agents working at the same time, so DESIGN FOR CHEAP RENDERING: emission-heavy shading, few lights, no volumetrics unless tiny, low samples (8–16) + OpenImageDenoise, max_bounces low, simple geometry. Text = Blender text objects parented to the camera (or compositor-free overlays).
- Final render: 576x1024 (resolution_percentage ~53), 24 fps, 20–30 s. Target < 2 s per frame. Measure early on a few frames and simplify if slower.
- Grain/vignette: can be done in ffmpeg at encode (e.g. `noise=alls=8:allf=t`, `vignette`) — cheap and effective.
- Encode: `ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 192k -shortest out.mp4`. Render frames into the scratchpad `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/0N/`, NOT the repo.
- LOOK at several rendered stills with the Read tool before the full render (composition, text legibility, aesthetic). Iterate until it looks genuinely striking — this must be scroll-stopping, cinematic, minimal. Then do the full render and check 2–3 frames from the final mp4 (ffmpeg -ss … -frames:v 1).
- Do NOT git commit or push. Don't touch other folders.
Report back: path of the mp4, duration, render time, what's in it, any honest limitations.
