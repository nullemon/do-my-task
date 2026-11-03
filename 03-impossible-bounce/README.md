# 03 · The Impossible Bounce

A ball dropped 2 m on the Sun keeps only 80 % of its speed (64 % of its energy) at every impact. It still bounces higher each time, because gravity switches to a lighter planet at every impact:
**Sun → Jupiter → Earth → Mars → Moon → Pluto**. The ending explains why: *Height = speed² ÷ 2g*, and the energy still went down.

- Vertical 1080×1920, 30 fps, **36.3 s** (1091 frames)
- Eevee by default (`BLENDER_EEVEE_NEXT` on 4.2–4.x, `BLENDER_EEVEE` on 5.x, picked automatically)
- Everything is procedural, and the text overlays render in the same pass (text objects parented to the camera, with dark plates behind them)

## How to run

| What | Command |
|---|---|
| Build the scene and verify it (no render) | Scripting tab → open `script.py` → ▶ Run. Use a new, empty file: the script clears the current scene. |
| Full render | `blender -b -P script.py -- --render` |
| Quick preview (40 % res, every 6th frame) | `blender -b -P script.py -- --preview` |
| Frame range | `blender -b -P script.py -- --frames 100 300` |
| Single frames | `blender -b -P script.py -- --still 1 110 851` |
| Options | `--engine EEVEE\|CYCLES\|WORKBENCH`, `--scale 50`, `--samples 16`, `--out DIR`, `--mp4`, `--no-verify` |

Output goes to `renders/03/` next to the script (`frame_####.png`), or to `//renders/03/` if the script has no file path. To change this, set `OUTPUT_DIR` in the CONFIG block. `--mp4` (or `OUTPUT_FORMAT="MP4"`) writes H.264 directly. On Blender 5.x this also sets `media_type`, and if that fails the script falls back to PNG.

The CONFIG block at the top holds the resolution, fps, engine, sample counts, PREVIEW/RENDER flags, output folder, drop height, restitution, planet order, the fast-forward factor for each planet, and the hook and tail lengths.

## Timeline

| Video time | Beat |
|---|---|
| 0–3.5 s | Hook: "This ball loses 1/3 of its energy every bounce. / So why does it go HIGHER?" The ball spins 2 m above the glowing Sun pad and the camera pushes in, so there is motion on the first frame. |
| 3.5 s | Sun drop (0.12 s), impact at 33.1 m/s, camera shake. The pad flashes, a shockwave ring spreads, and the label slams to JUPITER. |
| 3.7–5.8 s | Jupiter: 26.5 m/s, peak 14.1 m, 2.1 s in the air (real time) |
| 5.8–10.1 s | Earth: 21.2 m/s, 22.9 m, 4.3 s (real time) |
| 10.1–14.7 s | Mars: 17.0 m/s, 38.7 m, 9.1 s (**⏩ 2×**) |
| 14.7–21.4 s | Moon: 13.6 m/s, 56.8 m, 16.7 s (**⏩ 2.5×**). The ball climbs into the cloud layer and the stars come out. |
| 21.4–35.4 s | Pluto: 10.8 m/s, **94.9 m, above the clouds**, 35 s (**⏩ 2.5×**). The end card appears just after the apex: "Height = speed² ÷ 2g / Less gravity → same speed goes way higher. / Energy still went DOWN ✓" |
| 35.4–36.3 s | The ball lands on the Pluto pad and starts its next (smaller) bounce, which leaves the video loop-friendly. |

On-screen elements:
- Planet name and g in the top third
- A stats line for each bounce (launch speed, energy %, peak, air time)
- A ⏩ tag on the sped-up segments
- A bottom HUD with an ENERGY bar that drains, a MAX HEIGHT bar that grows, and a live height and real-time readout (the clock counts real physics time, so the fast-forward is honest)
- In world space: a 0–100 m ruler beside the ball with a fill that grows, plus a peak marker for each planet

## Verification (printed on every run)

After baking, the script steps through every frame of the **evaluated scene** and reads the ball's world height plus a keyed `phys_t` property. It then fits a parabola to each bounce by least squares, and from each fit derives:
- g
- launch or impact speed
- peak height
- air time
- energy relative to the Sun impact

These are checked against the brief, with tolerances of ±0.1 m/s, ±0.6 m (or 1 %), ±0.06 s and ±0.6 % energy. The script also asserts that energy goes down and peak height goes up at every bounce, and that the video is 35–45 s long.

```
planet      g fit   g real |     v m/s  brief |   peak m  brief |   air s brief |  energy brief | result
Sun        274.00   274.00 |     33.11   33.1 |     2.00    2.0 |       -     - |    100%     - | OK  (drop / impact speed)
Jupiter     24.79    24.79 |     26.48   26.5 |    14.15   14.0 |    2.14   2.1 |   64.0%   64% | OK
Earth        9.81     9.81 |     21.19   21.2 |    22.88   23.0 |    4.32   4.3 |   41.0%   41% | OK
Mars         3.71     3.71 |     16.95   17.0 |    38.72   39.0 |    9.14   9.1 |   26.2%   26% | OK
Moon         1.62     1.62 |     13.56   13.6 |    56.75   57.0 |   16.74  16.7 |   16.8%   17% | OK
Pluto        0.62     0.62 |     10.85   10.8 |    94.90   95.0 |   34.99  35.0 |   10.7%   11% | OK
energy every bounce DOWN, peak height every bounce UP: OK
video length 36.33 s (brief 35-45 s): OK
VERIFICATION PASSED
```

## Real vs faked

**Real**
- The gravity values.
- The 2 m drop, and the restitution of 0.8 in speed (0.64 in energy) at every impact.
- The ballistic arcs: the ball's contact point is keyed every frame from the exact analytic solution z = v₀t − ½gt², so the motion is deterministic with no simulation and nothing to tunnel.
- Every number on screen. The verification measures these from the evaluated scene.
- Heights are true to scale in metres (ruler, clouds at about 62–72 m).
- Real elapsed time is shown in the HUD.

**Faked / stylised**
- **Gravity changes planet at each impact.** That's the whole premise, so the speed carries over and only g changes.
- **Fast-forward**: Mars plays at 2×, Moon and Pluto at 2.5×. Each is tagged ⏩ on screen.
- **Squash & stretch** is applied only to the visual ball mesh, which is a child of the analytic root. On the frame nearest each impact the ball is drawn squashed on the pad even though the true contact point is a few cm–m above it, because the impact happens between frames. Stretch scales with the speed on screen.
- The environment cross-fades over 0.35 s after each impact (sky, ground and pad colour). The cloud deck is decorative: Moon and Pluto have no clouds.
- The sky gets darker and starrier with altitude, as a look rather than a model of the atmosphere. There is no air drag and the ball does not spin physically.
- The hook says "loses 1/3 of its energy". The exact figure is 36 % per bounce (64 % kept).

## Expected render time (1091 frames, 1080×1920)

- **Eevee, 32 samples, mid-range GPU**: about 0.5–1.5 s per frame, so **10–25 min** in total.
- `--preview` (40 % resolution, 8 samples, every 6th frame, 182 frames): about 1–2 min.
- **Cycles CPU, 64 samples**: about 15–40 s per frame, so several hours. Use it only if Eevee isn't available (for example a headless server without a GPU/EGL, where Eevee fails).
- Building the scene and verifying it takes about 5 s.

## Post copy

**Title:** This ball breaks physics… or does it? 🤯

**Pinned comment:** Every bounce the ball LOSES 36 % of its energy, yet it ends up 47× higher than it started 👀 Which planet would you want to play basketball on? 👇

**Description line:** Real gravity (Sun 274 · Jupiter 24.79 · Earth 9.81 · Mars 3.71 · Moon 1.62 · Pluto 0.62 m/s²). Height = v²/2g: the same speed goes higher where gravity is weaker.
