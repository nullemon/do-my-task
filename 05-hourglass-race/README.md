# 5. The Hourglass Race (58 s, 1080×1920 @ 30 fps)

Six identical hourglasses (2 columns × 3 rows) on planet-coloured pedestals flip together.
Sun → Jupiter → Earth → Mars → Moon → Pluto finish in that order. Each tile greys out and
shows its finish time. Everything is built procedurally by `script.py`.

## Run

| How | Command |
|---|---|
| Blender UI | Scripting tab → open `script.py` → ▶ Run Script, then Render → Render Animation |
| Final render (headless) | `blender -b -P script.py -- --render` |
| Draft render | `blender -b -P script.py -- --preview --render` (50 % resolution, 16 samples) |
| Sample stills | `blender -b -P script.py -- --frames 1,250,1400,1730 --out /tmp/hg` |
| Part of the video | `blender -b -P script.py -- --render --range 380-420` |

Other flags: `--engine EEVEE|CYCLES|WORKBENCH`, `--samples N`, `--res-pct N`, `--out DIR`,
`--png` (PNG frames instead of MP4), `--no-verify`.
Default output is `hourglass_race_out/hourglass_race_final.mp4` (H.264), saved next to the
.blend file, or in the current directory if the .blend has not been saved. Change the
`CONFIG` block at the top of the script to edit planets, timeline, engine, quality or the
output folder.
The script works in Blender 4.2 to 5.x. It picks `BLENDER_EEVEE_NEXT` or `BLENDER_EEVEE`
depending on the version. It writes keyframes through `fcurve_ensure_for_datablock`
(slotted actions in 4.4+/5.x), through `action.fcurves` on 4.2/4.3, and falls back to
`keyframe_insert`.

## Timeline

| Video time | What happens |
|---|---|
| 0–2 s | Hook "Same sand. Same glass. 6 planets. Which finishes first?" Hourglasses lift (moving from frame 1), then flip at 1.0–1.85 s. Sand starts flowing at 2.0 s |
| 2–13.6 s | Real time (1×). The Sun empties at 13.35 s: "SUN DONE in 11 s!" |
| 13.6–37 s | Speeds up to 4× (">> 4x FAST-FORWARD"). Jupiter finishes at 20.7 s, Earth at 26.2 s, Mars at 35.6 s |
| 37–58 s | Speeds up to 7.74×. Moon finishes at 43.2 s. "PLUTO: still going… 4 minutes total". Pluto finishes at 55.0 s: "PLUTO DONE: 238.7 s / sand flow ∝ √g", which is the payoff in the last 3 s |

The large timer always shows **simulated** seconds. The speed is the integral of a
piecewise-linear playback rate, so the sim-time-to-video-time mapping is smooth and
monotonic. The second speed is solved automatically so that Pluto empties at the video time
set by `pluto_finish_at`.

## Verification (printed on every run)

The script steps through every frame of the evaluated scene and measures the world-space
volume of the top-sand mesh. It finds where that volume reaches zero and extrapolates
linearly to get the exact empty time. It then asserts that this time matches the table:

```
SUN 11.353 (11.4) · JUPITER 37.744 (37.7) · EARTH 60.000 (60.0)
MARS 97.566 (97.6) · MOON 147.648 (147.6) · PLUTO 238.666 (238.7)   -> ALL OK
```

It also checks:
- **Constant flow rate:** dV/dt with the bulb nearly full matches dV/dt with it nearly empty, to within 1e-5.
- **Sand is conserved:** the bottom volume at the end equals the starting volume.
- **Time mapping:** it is monotonic.
- **Length:** the video runs 58 s, inside the 45–60 s limit.
- **On-screen labels:** the finish times shown match the table.

## Real vs faked

**Real**
- Drain time follows the Beverloo law, T = 60 s · √(9.81 / g), using the real gravity values.
- The flow is **independent of fill level**: the top volume drops linearly with time, as in a real hourglass.
- The finish times on screen are the true simulated times.

**Faked or simplified**
- There is no grain simulation. The sand is analytic geometry:
  - the top is a cone at the neck, scaled so that its volume follows a straight line in time;
  - the bottom is a heap at a 32° angle of repose that grows, then a flat layer forms under it;
  - the falling stream is a thin cylinder.
- The grain look is a procedural noise bump on the sand surface.
- The glass is a "fake glass" shader (transparent with a glossy rim), not refractive. This keeps the sand clearly visible and gives the same result in Eevee and Cycles.
- The flip is keyframed. When it ends, the sand jumps from the end cap into the funnel; this happens while the glass is still moving.
- Time is compressed. The video is fast-forwarded and labelled as such; the timer shows simulated time.
- No physics bake is needed, because everything is deterministic keyframes.
- A `frame_change_pre` handler rewrites only the timer text and the speed-badge text. It runs during rendering in the same session in which the script was run. If you reopen a saved .blend, run the script again before rendering.

## Render time

| Engine | Estimate |
|---|---|
| Eevee, 64 samples, mid-range GPU | about 0.5–1.5 s per frame, so roughly 15–40 min for 1740 frames |
| Cycles fallback (`--engine CYCLES`), 4-core CPU | 16 samples at 50 % resolution took about 4 s per frame here; 96 samples at full resolution would take several hours |

Eevee could not be test-rendered in the headless environment used during development
(it had no EGL/GPU). The test frames were rendered with Cycles.

## Posting

- **Title:** Hourglass on every planet ⏳ Pluto takes FOREVER
- **Pinned comment:** Which planet would YOU want to wait on? 🪐 Sun 11 s · Jupiter 38 s · Earth 60 s · Mars 98 s · Moon 2.5 min · Pluto 4 min. Fun fact: an hourglass drains at the same rate whether it's full or nearly empty. The sand's weight is held up by the glass walls, not the hole. Flow only depends on gravity (∝ √g) and the neck size.
- **Note:** emoji are kept out of the on-screen text because Blender's built-in font has no emoji glyphs. They are used only in the title and comment.
