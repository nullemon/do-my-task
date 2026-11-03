# 4. Guess the Planet (25 s quiz series)

One self-contained, procedural Blender script (`script.py`). It is built for Blender 4.2–5.x and was tested on 5.1.2. Each episode drops the same striped ball from 2 m in a neutral grey studio, with a 2 m ruler and a frame-synced stopwatch on screen. Viewers guess the planet from the fall speed. Then the reveal slams in, with a side-by-side Earth drop and a harder bonus round with 4 options.

## Run

| How | Command |
|---|---|
| Scripting tab | Open `script.py` and press ▶. This builds `CONFIG["EPISODE"]` and runs the verification. Nothing is rendered unless `CONFIG["RENDER"] = True`. |
| Render all episodes | `blender -b -P script.py -- --render` |
| One episode | `blender -b -P script.py -- --render --episode 2` |
| Fast draft | `blender -b -P script.py -- --render --preview` (50 % res, 8 samples) |
| Stills only | `blender -b -P script.py -- --frames 1,100,450,720 --episode 1` |

Other flags: `--engine EEVEE|CYCLES|WORKBENCH`, `--res-pct N`, `--samples N`, `--out DIR`, `--no-verify`.

Output goes to `--out`, or by default `guess_the_planet_renders/` next to the .blend file (or in the current directory). Each episode becomes `epNN_<planet>_0001-0750.mp4` (H.264). If FFmpeg is not available, the script writes a PNG sequence instead.

Edit the `CONFIG` block to change things. `EPISODES` is a list of `(planet, [3 options], bonus planet, [4 options])`. You can also change `COMPARE_PLANET`, `BEATS` (seconds), `PREVIEW`, `RENDER`, the engine, samples and the output folder. The video is 1080×1920 at 30 fps, 750 frames.

## Beat sheet (default)
- **0–2 s:** "WHICH PLANET IS THIS?" and "Most people get this wrong", with the A/B/C buttons. Everything is readable on frame 1 and settles slightly, so the first frame already moves. The camera also pushes in slowly for the whole video.
- **2–8 s:** Ball released from 2 m twice (2.0 s and 5.0 s). A big stopwatch counts up each frame and freezes at the exact landing time. Captions: "WATCH THE DROP · 2 m", then "ONE MORE TIME".
- **8–12 s:** "LOCK IN YOUR ANSWER" with a 3-2-1 countdown.
- **12–18 s:** Green answer plate `MOON · 1.62 m/s²` slams in and the correct button turns green. At 13 s the quiz ball and an Earth ball (`COMPARE_PLANET`) drop side by side, each with its own stopwatch.
- **18–25 s:** "BONUS ROUND · HARDER" with 4 options in a 2×2 grid. Drop at 19 s, reveal at 22.5 s, then "How many did you get? Comment below".

## Real vs faked
- **Real:** The fall and bounce heights use exact analytic ballistics with the real g values: Sun 274, Jupiter 24.79, Neptune 11.15, Earth 9.81, Mars 3.71, Moon 1.62, Pluto 0.62. The ball is keyed on every frame, plus extra keys at the exact fractional impact and apex frames. Playback is fully deterministic and needs no bake.
- **Real:** The stopwatch is computed from frame number and fps. A `frame_change_pre` handler rewrites the text on every frame, including during animation renders (`use_lock_interface` is on), and freezes it at the true fall time.
- **Simplified:** Bounces use a fixed restitution of 0.45 on every planet (same bounce ratio, time scales with 1/√g). There is no rigid-body sim and no squash and stretch. There is no air drag, which would matter on Earth, Jupiter and Neptune.
- **Simplified:** Overlays are text objects parented to the camera, on opaque dark plates, using emission materials and no shadows. The default font has no emoji, so emoji are used only in the title and comment.
- **Answer hidden before the reveal:** The answer label, the green highlight and the bonus answer are hidden with keyframed `hide_render`/`hide_viewport` and scale 0 until the reveal frame. The verification step checks every earlier frame.

## Verification (printed every run, with asserts)
For each planet, a temporary ball is dropped from 2 m. The script samples the *evaluated* scene (`frame_set` with subframes) to find the first floor contact and asserts it within ±0.006 s of the answer key. It then measures every drop in the built episode the same way, checks the frozen stopwatch text, and checks that the answer labels are invisible before the reveal.

```
SUN      measured=0.1208 s  key=0.12 OK     MOON     measured=1.5713 s  key=1.57 OK
JUPITER  measured=0.4017 s  key=0.40 OK     PLUTO    measured=2.5400 s  key=2.54 OK
EARTH    measured=0.6385 s  key=0.64 OK     NEPTUNE  measured=0.5989 s  key=0.60 OK
MARS     measured=1.0383 s  key=1.04 OK
```

## Render time (estimate)
- **Eevee** (default) at 1080×1920 with 64 samples on a mid-range GPU: about 0.3–0.8 s per frame, so about 4–10 min per 750-frame episode. `--preview` is about 4× faster. Eevee was not measured here because the test machine has no GPU.
- **Cycles CPU** (4 cores) at 40 % resolution with 16 samples took about 2.5 s per frame, so about 30 min per episode. At full resolution with 64 samples on CPU, expect several hours per episode.

## Title & pinned comment
- **Title:** Guess the planet from ONE drop 🪐
- **Pinned comment:** Which planet was it, A, B or C? 👇 And did you get the bonus? Score out of 2 below.

## Known limits
- The stopwatch text depends on the Python handler. If you reopen a saved .blend without running the script (or with auto-run scripts off), the text stays frozen. The ball animation and the answer gating still work because they are keyframes.
- Eevee had no GPU on the test machine, so test stills were rendered with Cycles. Eevee is still the default engine. The engine id is chosen per version: `BLENDER_EEVEE_NEXT` for 4.2–4.x, `BLENDER_EEVEE` for 5.x.
