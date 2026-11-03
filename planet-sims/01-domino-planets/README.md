# 01 · Domino Planets

One continuous domino run (261 dominoes on a gentle S-curve, 130 m long) that crosses
coloured ground zones, one per planet: **Earth → Moon → Jupiter → Pluto → Sun → Mars**.
When the wave enters a zone, gravity switches to that planet's real value, so the wave
crawls on the Moon, nearly floats on Pluto, hurries on Jupiter and slams down on the Sun.
It is one shot: one scene, one camera tracking the wave front, a label card
(`MOON · 1.62 m/s²`) that pops in as the wave enters each zone, and a sky, floor and light
for each planet. Runs about 36.6 s at 30 fps (1097 frames).

## Run

- **Blender UI:** open the Scripting tab, open `domino_planets.py`, press ▶. It builds the
  `DominoPlanets` scene and bakes it in about 20 s. Press play. The timeline has a marker for
  each zone (`02_Moon` and so on).
- **Headless full render (Eevee, 1080×1920):** `blender -b -P domino_planets.py -- --render`
  This writes `renders/domino_planets/frame_####.png` next to the .blend, or next to the
  script if the .blend is unsaved. Use `--out DIR` to write somewhere else.
- **Preview:** `blender -b -P domino_planets.py -- --preview` renders one low-res Cycles still
  per zone to `renders/domino_planets/preview/`.

Works on Blender 4.2 LTS through 5.x. Tested with bpy 5.2.3.

## CONFIG knobs (top of script)

| Knob | What it does |
|---|---|
| `ZONES` | List of `(planet, domino count)` pairs, in order. Any planet in `GRAVITY` works. The counts set how long each zone lasts. |
| `FPS`, `RESOLUTION`, `ENGINE`, `EEVEE_SAMPLES`, `CYCLES_SAMPLES` | Output settings. |
| `PREVIEW_*`, `RENDER`, `PREVIEW`, `OUTPUT` | Preview stills, render flags and output folder. |
| `DOMINO_H/W/T`, `SPACING`, `FRICTION` | Domino geometry and friction. |
| `SUBSTEPS`, `SOLVER_ITERATIONS` | Solver settings. 20 substeps per frame (600 Hz) keeps the Sun zone stable. |
| `S_AMPLITUDE`, `S_HALF_WAVES`, `ZONE_HALF_WIDTH` | Track shape and floor width. |
| `START_FRAME`, `START_TILT_DEG`, `OUTRO_SECONDS`, `HOOK_TEXT` | Intro, outro and the hook caption. |

## Gravity per zone

Blender has one global rigid-body gravity, so the script handles it like this:

1. It steps the simulation one frame at a time from Python.
2. When the first domino of the next zone starts to tip (the wave front reaches the
   boundary), it writes a constant keyframe on `scene.gravity` for the next frame.
   - The rigid-body solver reads the animated gravity every frame, so the switch is real
     physics.
   - The dominoes behind the front are lying asleep and the ones ahead are standing asleep
     (Bullet deactivation), so in practice only the moving wave feels the change.
3. `ptcache.bake_from_cache` turns that in-memory run into a real bake. I checked that
   replaying the bake gives the same result.

## Measured results (printed by the script on every run)

| Zone | g (m/s²) | Dominoes | Time in zone | Time per domino | Wave speed |
|---|---|---|---|---|---|
| Earth | 9.81 | 45 | 6.9 s | 0.140 s | 3.6 m/s |
| Moon | 1.62 | 20 | 5.9 s | 0.325 s | 1.5 m/s |
| Jupiter | 24.79 | 70 | 6.0 s | 0.086 s | 5.8 m/s |
| Pluto | 0.62 | 16 | 6.4 s | 0.474 s | 1.05 m/s |
| Sun | 274 | 80 | 2.0 s | 0.026 s | 19.6 m/s |
| Mars | 3.71 | 30 | 5.6 s | 0.204 s | 2.45 m/s |

- Time per domino scales as 1/√g, within 0–15 %. Pluto and Mars run a little fast because
  the wave carries momentum in from the zone before.
- All 261 dominoes fall. The wave never stalls, and no push is added anywhere.
- At Sun gravity, the highest any domino got was 0.53 m (domino height 1 m), and the
  largest sideways drift was 0.2 m. Nothing tunnels or explodes.

## Real vs. faked

- **Real:**
  - The rigid-body physics.
  - The real gravity values.
  - Each zone's wave speed, which comes from the simulation.
  - No time remapping. Pluto is slow enough as it is.
- **Stylised:**
  - Gravity is global, so for one frame at each boundary, the few dominoes still falling
    in the old zone feel the new gravity.
  - A kinematic nudge tips the first domino 12°.
  - The dominoes are giant (1 m tall) because Bullet is much more stable at that scale.
    Wave speed only scales with √(g·h), so the gravity ratios hold.

## Render time

- Bake: about 20 s.
- Eevee at 1080×1920 with 64 samples: about 1–2 s per frame on a mid-range GPU, so roughly
  20–40 min for 1097 frames.
- Cycles CPU at full resolution would take hours.
- The preview (6 stills at 270×480, 16 samples, CPU) takes about 1 min.

## Preview

`preview/01_Earth.jpg` … `preview/06_Mars.jpg`: one still per zone, taken mid-wave.
