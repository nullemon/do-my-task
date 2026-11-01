# The Long Way Home — project brief for Claude Code

A daily animated Facebook Reels series about Rusty, an old golden-retriever mix who is abandoned
200 miles from home and walks back. Each episode is 60 seconds, vertical 1080×1920, 24 fps, ends on
a cliffhanger, and works with the sound off (the on-screen text carries the story).

Episode 1 already exists as a 2D silhouette film made in code: see `long-way-home/` and its README.
It is the reference for story, shot list, timing, captions (`src/main.js` → `CAPTIONS`, `SCENES`),
color script (`src/scenes.js`) and the soundtrack (`audio/soundtrack.py`).

## The job now: remake it as a 3D animated short in Blender

Look: a stylized 3D animated film, in the spirit of a Pixar short. Soft, appealing shapes, expressive
eyes, cinematic lighting (volumetric light, rain, wet reflections, golden hour, blue hour, a
lightning storm, dawn). Keep the one-color accent: Rusty's yellow-green tennis ball is the most
saturated thing in every shot.

Everything is built by code in Blender with Python (`bpy`). **No downloaded 3D models, rigs or
animations.** Characters, sets and props are modeled, rigged and animated by our scripts. Textures
and HDRIs should be procedural; anything downloaded must be CC0 and noted in `long-way-home/blender/ASSETS.md`.

### Characters

- **Rusty** (the star): golden retriever mix, about 8 years old, warm reddish-gold coat (hence the
  name), grey on the muzzle and around the eyes, floppy ears, feathered tail and chest, a worn red
  collar with a round brass tag. Stylized proportions: head ~15% larger than real, big dark eyes
  with clear catchlights and visible brows so he can look hopeful, confused and heartbroken.
  Needs: walk, trot, gallop, sit, sit-to-stand, lie down, head turn/tilt, ear perk and droop,
  tail wag and tail drop, blink, mouth open/pant, carrying the ball in his mouth.
- **Dad**: early 40s, tired, stubble, flannel shirt and jeans. Needs: sitting with head in hands,
  throw, walk, standing at a window.
- **Lily**: 8 years old, two braids. Needs: walking with a backpack, standing at a window in
  pajamas, hand on the glass. Also a baby version in a crib for the flashback.
- Props/sets: family hatchback/wagon, school bus, a highway gas station (canopy, pumps, sign that
  reads GAS 3.49, small store), the kitchen, the lease document, the house exterior with porch
  light and Rusty's bowl, a long straight road at dawn.

Suggested approach (change it if you find something better): model with bmesh/skin modifier +
subdivision, then remesh and shape; armature with IK legs and controllers; shape keys for blinks,
brows and mouth; fur with Geometry Nodes hair curves (Blender's built-in hair node groups) or a
shell/card approach if hair is too slow; eyes as separate spheres with a refractive cornea.

## Hardware and rendering

Alienware m16 R2, Windows 11, **RTX 4060 Laptop GPU (8 GB VRAM)** (confirmed by nvidia-smi), Intel Core Ultra.
Drives: C: has ~120 GB free, D: ~425 GB free; put big caches and renders on D:.

- Run Blender headless: `blender -b <file.blend> -P <script.py> -- <args>`. `BLENDER_EXE` is set.
- Every render script enables the GPU itself (OptiX, fall back to CUDA). See `long-way-home/tools/gpu-check.py`.
- Previews: EEVEE, 540×960. Finals: Cycles + OptiX denoiser, 1080×1920, motion blur on.
  Aim for under ~30 s per final frame (8 GB VRAM: keep scenes lean, prefer EEVEE); tell the user before
  starting anything that will take hours.
- Render to `long-way-home/blender/renders/<shot>/####.png` (git-ignored), then assemble with ffmpeg.
- Captions, title card, grain and grading can reuse the existing compositor in `long-way-home/src/main.js`
  (draw the Blender frame as the background, then the existing captions on top), or be done in ffmpeg.

## How to work with the user

The user is non-technical and wants a finished, beautiful result. Work in phases and stop for
approval at each checkpoint, showing rendered stills (and short MP4 previews) rather than describing:

1. **Rusty look development**: turntable (front, 3/4, side, back) and an expression sheet
   (happy, curious, worried, heartbroken). Iterate until the user loves him.
2. **Animation test**: walk, trot, gallop, sit, sit-to-stand, carrying the ball, 10–15 s preview.
3. **One hero shot at final quality**: shot S1 (night, rain, gas station, taillights leaving).
4. **Full Episode 1** in 3D, matched to the existing timing, captions and soundtrack.
5. **Episode 2, "The Trucker"**, then onward.

Rules:
- Look at your own renders (open the PNGs) before showing them; fix obvious problems first.
- Commit working scripts often with clear messages; never commit renders or big caches.
- Keep scripts small and re-runnable: `blender/build_rusty.py`, `blender/rig_rusty.py`,
  `blender/anim_library.py`, `blender/sets/*.py`, `blender/shots/*.py`, `blender/render_shot.py`.
- If `GEMINI_API_KEY` is set, you may use Google's current Gemini image model through its REST API
  to sketch concept art before modeling (check Google's docs for the current model name). Never print
  or commit the key. Final pictures must come from Blender.
- Sound: keep `audio/soundtrack.py` for now; a voice/real-SFX pass comes later.

## Track 2: local AI studio

`ai-studio/` sets up ComfyUI with open image and video models (generation, image edit, image-to-video,
motion transfer, character replacement, video object swap) on the Alienware. Its brief is
`ai-studio/CLAUDE.md`. The "no downloaded models" rule above is about 3D assets for the Blender remake;
it does not apply to AI model weights in `ai-studio/`.
