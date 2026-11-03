# 2. Split World

**Title:** Half Moon, half Jupiter 🌗 (watch the water)

One locked-off vertical (1080×1920, 30 fps, 36 s) shot of a kitchen table split by a glowing seam at x = 0. Left of the seam is the Moon (1.62 m/s²), right of it is Jupiter (24.79 m/s²).

| Time | Beat |
|---|---|
| 0–5 s | Hook "LEFT: MOON · RIGHT: JUPITER". A hand pours water left→right: slow Moon arc, then a slam and splash once it crosses the seam. A glass stands on the seam line. |
| 5–12 s | Twin balls get the same push off a 1 m table. Live fall timers stop at **1.11 s** (Moon) and **0.28 s** (Jupiter), then "→ 4× slower". |
| 12–20 s | A deck of giant cards bursts across the seam. Moon cards flutter (about 2.3 s in the air); Jupiter cards drop (about 0.3 s). |
| 20–30 s | A 2.5 m pendulum swings across the seam. A live timer shows each half-swing, then "full swing 4.99 s = average of a Moon & a Jupiter swing". |
| 27–30 s | Three eggs are tossed on the Moon side and hang in slow arcs… |
| 30–33 s | …then the seam slides left and Jupiter takes over the frame. The eggs splat, the pendulum speeds up, the MOON label falls off and the cool grade turns warm. "JUPITER WINS". |
| 33–36 s | End card: "Which side would you live on? ↓" |

## Run

```bash
blender -b -P script.py -- --preview   # 50 % res, 16 samples -> split_world_out/split_world_preview.mp4
blender -b -P script.py -- --render    # full 1080x1920, 64 samples -> split_world_out/split_world_render.mp4
blender -b -P script.py -- --frames 1,250,700 --engine CYCLES --samples 16 --res-pct 30   # test stills
```

Other options after `--`: `--engine EEVEE|CYCLES|WORKBENCH`, `--samples N`, `--res-pct N`, `--range a,b` (render only part of the animation) and `--out DIR`.

In the Blender UI: open `script.py` in the Scripting tab and press ▶. It builds the scene and prints the checks; then use Render ▸ Render Animation.

- **Warning:** the script deletes every object, material and similar item in the open file before it builds the scene.
- Settings are in the `CONFIG` block at the top: planets, fps, duration, resolution, engine, PREVIEW/RENDER quality, output folder, seed, sub-steps, timings and sizes.
- It works with Blender 4.2–5.x. The Eevee engine is called `BLENDER_EEVEE_NEXT` in 4.x and `BLENDER_EEVEE` in 5.x, and the script tries both. Keyframes are written through `keyframe_insert` plus a channelbag-aware F-curve lookup, so both the 4.x and 5.x Action APIs work.
- The live timers are text objects updated by a `frame_change_pre` handler. That handler is registered when the script runs. If you save the .blend and render it later without re-running the script, the timer texts stay frozen.

## What's real and what's faked

**Real (computed with the true g values):**
- **How gravity is applied.** The Bullet rigid-body solver is not used. A quick test showed two problems:
  - Blender force fields apply a *force*, not an acceleration. With the same field, a 5 kg ball fell about 5× slower than a 1 kg ball.
  - Fields can only be limited with sphere, tube or cone falloff, not a box, so they leak across the seam.

  Instead, `sc.gravity = 0` and a small deterministic Python integrator moves everything:
  - It runs 40 sub-steps per frame (1200 Hz).
  - Each sub-step uses the exact constant-acceleration update.
  - Gravity is looked up from the body's x position and the seam position at that moment.
  - Results are baked to keyframes, so playback is deterministic. The bake takes about 1.5 s.
- **Ball falls.** Ballistic motion off the table edge; the edge crossing and the landing are both interpolated inside the sub-step.
- **Pendulum.** θ is integrated with velocity-Verlet, using the g of the bob's current side. The script checks it against the exact elliptic-integral period for each side's amplitude. Energy is conserved, so the swing reaches 35° on the Moon side but only 8.8° on the Jupiter side.
- **Seam slide.** The gravity boundary itself moves over 30.2–32 s, so anything on the left changes from Moon to Jupiter gravity the moment the seam passes it.

**Simplified or faked:**
- **Water** is fake: there is no Mantaflow. About 110 soft blobs are each integrated with their side's g and stretched along their velocity. When a blob hits the table it disappears and throws out 2 droplets, and a puddle disc grows as blobs land. The pour also gives the water a small sideways throw so the Moon arc reads well.
- **Cards** have the same "kitchen air" on both sides (quadratic drag k = 1.0) plus a "falling-leaf" sideways flutter and tumble. This is a hand-made model, not aerodynamics; it just lets the Moon cards flutter while gravity wins on Jupiter. There is no air on the real Moon.
- **No collisions between objects.** Things only land on the table top or the floor. Landed cards snap flat, and eggs splat above 4.5 m/s, which only happens under Jupiter gravity.
- **The two balls** start together from the seam and roll outward, one to each side, so both 1 m drops can be timed side by side. The brief describes a single ball rolling left→right.
- **Hand** is a simple stylised shape (blobby hand and sleeve) holding a procedural pitcher.
- **Grade:** every material goes through a shared node group. The group desaturates and cools colours left of the animated `SeamX` value and warms them right of it. It also draws a shimmering glowing line wherever the seam cuts a surface. The key lights are cool on the left and warm on the right, and the left one turns warm during the slide. A transparent emissive sheet with animated noise forms the glowing seam.

## Verification (printed every run, asserts)

```
1 m fall off table edge, MOON     measured 1.112 s  analytic 1.111 s  OK
1 m fall off table edge, JUPITER  measured 0.285 s  analytic 0.284 s  OK
pendulum L=2.50 m, amplitude Moon side 35.0 deg, Jupiter side 8.8 deg
  half-swings on Moon side    : 3.996  exact 3.996  small-angle 3.903
  half-swings on Jupiter side : 0.999, 0.999  exact 0.999  small-angle 0.998
  full split period 4.995 s ; average of full Moon (7.991) & Jupiter (1.998) periods = 4.995 s  OK
  small-angle rule: ... = 4.900 s (amplitude correction 1.9%) OK
```

**Pendulum rule:** split period = Moon half-swing + Jupiter half-swing, which equals the average of the full Moon and full Jupiter periods. The check uses a 0.5 % tolerance against the exact periods and 4 % against the small-angle formula.

## Render time

| Setup | Time per frame | 1080 frames |
|---|---|---|
| Eevee, a typical desktop GPU, 64 samples at 1080×1920 (**estimate**) | about 0.5–1.5 s | 10–25 min |
| Preview at 50 % and 16 samples | | about 3–6 min |
| Cycles CPU fallback, 4 cores, 30 % res, 12 samples (**measured**) | about 6 s | |

The Eevee figures are estimates: Eevee could not run on the headless test machine because it has no EGL/GPU. The test stills were rendered with Cycles instead.
