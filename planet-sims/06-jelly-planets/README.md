# 06 · Jelly on every planet

A glossy fluted raspberry jelly with a cherry on top drops 20 cm onto a porcelain plate, once per planet (Pluto, Moon, Mars, Earth, Jupiter, Sun). The jelly, material and drop height are identical in every scene. Only gravity changes, plus the solver substeps that higher gravity needs. You get one Blender scene per planet (`01_Pluto` … `06_Sun`), each with a pastel studio cyclorama in that planet's colours, soft area lights, a 70 mm camera with shallow depth of field, and labels sized for a phone screen.

## Run
- **In Blender (4.2 – 5.x):** open `jelly_planets.py` in the Scripting tab and press ▶. The script builds and bakes every scene. Pick a planet scene in the top bar and press play. Re-running the script replaces everything it made before.
- **Headless render:** `blender -b -P jelly_planets.py -- --render` writes PNG frames to `renders/jelly_planets/NN_Planet/frame_####.png`. The folder sits next to the .blend, or next to the script if the file isn't saved.
- **Quick check:** `-- --preview` renders one low-sample Cycles still per planet at its maximum squash, into `renders/jelly_planets/preview/`.
- Pick planets: `-- --planets=Moon,Earth,Sun`

## CONFIG knobs (top of the file)
- `PLANETS`, `FPS` (30), `SECONDS` (5), `HOLD_SECONDS`, `RESOLUTION` (1080×1920), `ENGINE` (EEVEE/CYCLES) and samples.
- `DROP_HEIGHT`, `JELLY_COLOR`, `CHERRY`, `HOOK_TEXT`, `LABEL_MAX_WIDTH` (labels shrink to fit 85 % of the frame width).
- `JELLY` dict with the material physics: density, skin stiffness, bending, internal springs, damping and pressure. These are the same on every planet.
- `BASE_QUALITY` sets cloth substeps at Earth gravity and scales with √g, up to `MAX_QUALITY` = 50. `PLATE_FRICTION` and `SELF_COLLISION` are also here.
- `LOOKS` holds the per-planet backdrop, text and world colours.

## Measured result (printed after baking; rest height 0.635 m)
| planet | g | max squash (min h / rest) | final h | max width / rest | wobble |
|---|---|---|---|---|---|
| Pluto | 0.62 | 1.00 | 1.04 | 1.11 | ~1 Hz, very slow fall (lands after ~0.75 s) |
| Moon | 1.62 | 0.99 | 1.06 | 1.10 | ~1 Hz, slow fall (lands after ~0.45 s) |
| Mars | 3.71 | 1.00 | 1.03 | 1.05 | 1.7 Hz |
| Earth | 9.81 | 0.89 | 1.01 | 1.06 | 1.5 Hz jiggle |
| Jupiter | 24.79 | 0.85 | 0.96 | 1.10 | big squash, stays slumped |
| Sun | 274 | **0.41** | **0.52** | **1.38** | splats into a pancake, ~3 Hz ripples |

Jelly volume stays within 1–4 % of rest on every planet except the Sun, where it stays within 10–16 %. Nothing tunnels through the plate.

## Real vs. faked
- **Real:** each planet's surface gravity (scene gravity × cloth gravity weight 1.0), the same 20 cm drop, a jelly mass from a density of 1050 kg/m³, and the same material everywhere. The higher substeps on Jupiter and the Sun keep the solver stable; they don't change the material.
- **Simplified:** this is not a solid-mechanics simulation of gelatin. Blender models the jelly as a cloth skin with internal pressure (a water-balloon model), and the stiffness values were tuned so it looks like jelly. The jelly is party-sized (62 cm tall), because the cloth solver was unstable at a real 10 cm size. How fast it jiggles depends on the stiffness settings, not on gravity. The Moon and Pluto runs look slow mainly because the fall itself is slow. In low gravity the skin relaxes slightly, so it ends up 3–6 % taller than it started.
- **Cherry:** decorative. It is vertex-parented to the jelly's crown, so it rides the squash, but it has no mass in the simulation.
- The baked cloth is stored as per-frame shape keys. Headless Blender would not render the in-memory cloth cache.

## Render time
- **Bake:** about 30–70 s for each normal planet and about 5–6 min for the Sun (4-core CPU). That's roughly 11 min in total, including the preview stills.
- **Preview stills:** about 20 s each at 270×480 and 24 samples.
- **Full 1080×1920 render:** with Eevee, expect about 1–3 s per frame on a GPU, which is about 15–40 min for 6 × 150 frames. With Cycles at 128 samples on CPU, expect several minutes per frame because the jelly is a refractive volume.
