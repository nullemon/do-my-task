# 04 · Pouring water on every planet

A glass of water is tipped and poured into a bowl on the Moon, Mars, Earth, Jupiter, the Sun and Pluto.
Mantaflow FLIP liquid, real-world size (a 0.29 L tumbler, lip 0.30 m above the table) and real gravity per planet.
One scene per planet (`01_Moon`, `02_Mars`, …): pick one in the scene selector and press play.

## Run

```
# inside Blender: Scripting tab -> open water_pour_planets.py -> Run Script  (builds + bakes when BAKE_ON_RUN)
blender -b -P water_pour_planets.py -- --render            # bake + render every planet
blender -b -P water_pour_planets.py -- --preview           # small fast bake + Cycles stills + printed metrics
   options: --out DIR   --planets Moon,Sun   --no-bake
```

Heads-up: with `BAKE_ON_RUN = True`, Run Script in the UI bakes all planets at `RESOLUTION` and Blender stays busy for
hours (see the time budget below). For a quick look, set `RESOLUTION = 48` or `BAKE_ON_RUN = False` and bake one scene from
*Physics > Fluid > Bake All*.

Output: `//renders/water_pour/<NN_Planet>/frame_####.png` (next to the .blend, or the script folder when unsaved),
fluid caches in `//cache_water_pour/<NN_Planet>_r<res>/`, metrics in `renders/water_pour/metrics*.json`.

## CONFIG knobs (top of the script)

| knob | meaning |
|---|---|
| `PLANETS` | which planets / order (any of the 11 in `GRAVITY`) |
| `RESOLUTION` | domain divisions on the longest side. 128 default; 160–192 for hero shots; preview uses `PREVIEW_RESOLUTION` = 48 |
| `MESH_UPRES`, `MESH_SMOOTH_POS/NEG`, `MESH_PARTICLE_RADIUS` | liquid surface: upres and smoothing |
| `CFL`, `CFL_HIGH_G` | Courant number (2.0 normally, 1.0 for g > 50 = the Sun) |
| `SURFACE_TENSION` | Mantaflow surface tension, off by default (see below) |
| `CACHE_DIR`, `BAKE_ON_RUN` | cache folder; bake when the script runs |
| `FPS`, `SECONDS`, `RES_X/RES_Y`, `ENGINE` | 30 fps, 5 s, 1080×1920, Eevee (Cycles looks best for water) |
| `TILT_*`, `FILL`, `LIP`, `BOWL_*` | the tip motion, fill level and layout |
| `PREVIEW*` | preview resolution, length, still frame, samples |

## How gravity and the time step are set

- Mantaflow uses `scene.gravity` when *Scene > Gravity* is enabled (×`effector_weights.gravity`), otherwise
  the domain's own `domain_settings.gravity`. The script sets both, so it's right either way (4.2–5.x).
  Gravity is in m/s² because the domain's grid spacing comes from its size in metres.
- Time step: the fastest liquid is the stream falling from the lip, v ≈ √(2gh)+1. Each planet gets
  `timesteps_max = 1.5·v/(fps·dx·CFL)` and `timesteps_min` ≈ a third of that, so liquid never moves more
  than CFL cells per sub-step. At preview resolution that is 2..6 sub-steps for the Moon and **18..79 for the Sun**
  (CFL 1.0). At 128 the Sun hits the cap of 250. Check: the script warns if any splash goes higher than the lip,
  which energy says can't happen. That warning never fired in the tests.

## Measured (preview bake, res 48, 4-core CPU)

| planet | g | leaves glass | hits bowl | fall | falling front speed (ideal √2gh) | bake |
|---|---|---|---|---|---|---|
| Pluto | 0.62 | 1.17 s | 1.97 s | 0.80 s | 0.57 m/s (0.60) | 26 s |
| Moon | 1.62 | 0.90 s | 1.40 s | 0.50 s | 0.93 m/s (0.98) | 12 s |
| Mars | 3.71 | 0.80 s | 1.13 s | 0.33 s | 1.42 m/s (1.48) | 37 s |
| Earth | 9.81 | 0.73 s | 0.90 s | 0.17 s | 1.94 m/s (2.40) | 43 s |
| Jupiter | 24.79 | 0.67 s | 0.80 s | 0.13 s | 3.03 m/s (3.82) | 63 s |
| Sun | 274 | 0.60 s | 0.63 s | 0.03 s | 7.95 m/s* (12.7) | 198 s |

(The glass finishes tipping at 0.6 s, which is when the simulation starts. *At 30 fps the Sun's stream lands within about one frame, so the
frame-sampled speed is a lower bound.) The Moon and Pluto give a slow, thick, ropy stream that is still pouring at 1.9 s. On the Sun the
whole glass empties into the bowl as one sheet within about 0.1 s.

## Real vs faked

- **Real:** gravity per planet, real-world dimensions, the liquid flow (FLIP), how fast the glass empties, how the stream
  falls and thins, the impact, sloshing and splashing in the bowl.
- **Faked / simplified:** the hand tipping the glass (0.2–0.6 s) is plain keyframe animation, with a still water mesh riding
  inside the glass. The fluid sim starts when the glass is held still at 100°: the water starts with the upright fill shape inside
  the tipped glass, which is the same as a very fast tip. Why: Mantaflow (4.x/5.x) loses liquid that is *inside a moving
  closed container*. In tests the water got deleted as the glass rotated, whatever the collider shape, thickness, subframes or
  velocity factor. Static obstacles work fine.
- The glass collider is a hidden set of convex pieces (a base plus 16 wall staves, at least 1.5 cells thick), and the bowl has a hidden
  thicker twin. Blender treats a cell as inside a mesh when all 26 test rays hit it, so a deep tipped tumbler would make
  its whole cavity solid. Thin 4 mm walls also leak on a coarse grid.
- **No surface tension by default.** Water's capillary length is 2.7 mm on Earth and only about 11 mm even on Pluto, which is below
  one grid cell at any practical resolution, so the round "blobby" low-g look can't come from real physics here. `SURFACE_TENSION` is
  exposed if you want to exaggerate it (in grid units, so tune it by eye).
- Splash height in metres is roughly the same on every planet (an energy argument: everything just runs faster
  at high g, measured 0.14–0.24 m). What changes is speed and violence: impact speed scales with √g, and the slosh time with 1/√g.

## Time budget (final quality, 1080×1920, 5 s / 150 frames, 6 planets)

Baking scales roughly with res³ × sub-steps. Measured preview bakes, scaled up:

- Measured here: the Sun at res 80 took 1364 s for 1.5 s of clip, about 50 s per simulated frame with 30–100 sub-steps. It stayed
  stable: the splash topped out at 0.29 m, just below the 0.30 m lip.
- `RESOLUTION = 128` on a 4-core CPU: Moon/Pluto/Mars about 0.5–1 h each, Earth/Jupiter 1.5–2 h, **Sun 10–13 h** (5–6 min per
  frame, up to 250 sub-steps), so **about 16–20 h total**. A 12–16-core desktop takes roughly a third of that. Tip: bake the Sun
  separately at a lower `RESOLUTION` (`--planets Sun`), or use res 96 everywhere for a quick pass (about 2.5× faster).
- 160–192: 2–3.5× longer again. Caches are about 1–3 GB per planet at 128 (OpenVDB + mesh).
- Render: Eevee 1080×1920 takes 2–6 s/frame on a decent GPU, so about 30–90 min for all 900 frames. Cycles 256 samples
  (best-looking water) takes 20–60 s/frame on GPU, so 5–15 h. On CPU expect 3–5× longer.
- `--preview` (res 48, 2.4 s, 8 Cycles stills at 270×480) takes about 7 min on 4 cores.

## Preview

`preview/` holds stills at the same moment (t = 1.9 s) for each planet from the res-48 preview bake, plus
`01_Moon_impact.jpg` (two frames after the water first lands) and `05_Sun_res80_splash.jpg`: a res-80 bake of the Sun 0.1 s
after impact, where the whole glass hits the bowl as one sheet and sprays out. That's the look to expect at final resolution.
They are low-res, 24-sample Cycles renders.
