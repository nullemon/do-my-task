# 06 · Saturn at the Moon's distance (50 s, cinematic)

**Title:** What if Saturn replaced the Moon? 🪐 (you'd feel nothing… at first)

A single procedural Blender script (Blender 4.2 – 5.x) that builds the whole shot: a beach at golden hour, Saturn rising at true angular size, night lit by the rings, the tide pulling out and coming back, tremors and a volcano, then a cut to black. It needs no downloaded assets and prints its own physics check.

## Run

```bash
blender -b -P script.py -- --render         # full quality: 1080x1920, 30 fps, 1500 frames -> render_06/saturn_moon_distance.mp4
blender -b -P script.py -- --preview        # 50 % resolution, low samples
blender -b -P script.py -- --frames 1,240,450,780,1010,1480   # stills only
blender -b -P script.py -- --verify-only    # build the scene and print the verification, no render
# options: --engine eevee|cycles  --out <folder>  --samples N  --res-pct N
```

In the GUI, open `script.py` in the Scripting tab and press ▶. The scene is built and the verification is printed to the system console.

Settings live in the `CONFIG` block at the top of the script: fps, duration, resolution, engine (Eevee by default), samples, the PREVIEW and RENDER flags, the output folder, and all the astronomy constants. If the build has no FFmpeg, the MP4 output falls back to a PNG sequence.

## Beats

| t (s) | Picture | Caption |
|---|---|---|
| 0–3 | Golden-hour beach, ocean waves, palms, boats | **What if Saturn replaced the Moon?** |
| 3–12 | The rings come over the horizon first, then the planet, rising on a diagonal and reddened near the horizon | **Distance: 384,400 km** / 17.8° wide, rings 39° = 34 full Moons across |
| 12–20 | Night falls, stars come out, Saturn-shine lights the beach | **You'd feel… nothing.** (weight change < 0.1%) |
| 20–28 | The sea drops 10 m and the shoreline moves back ~333 m. The seabed, rocks and grounded boats are exposed | **Tides ~7,700× stronger** / The sea pulls back hundreds of metres… |
| 28–35 | A 33 m wall of water rushes in, the camera shakes, white flash, the boats are thrown up the beach | **…then it comes back.** |
| 35–45 | Tremors shake the camera, a distant volcano glows. Inset: the Moon is flung off its orbit | **Earthquakes. Volcanoes.** |
| 45–50 | Hard cut to black at 49.0 s | **And this was the SAFE distance.** / **At 73,000 km, Earth gets torn apart…** |

A permanent top-third label reads `SATURN · at the Moon's distance | 384,400 km`. All text is Blender text objects parented to the camera, set on dark rounded plates.

## Verification (printed by the script, `assert`ed)

The angular sizes are measured from the evaluated scene geometry, from the camera's world position:

```
t=12.0s camera->Saturn 5997 m (= 384,210 km) | Saturn disc 17.83° (limb 18.05°) | rings 39.19° | in frame: True
OK   Saturn angular diameter 17.83° ~ 17.8°
OK   Ring angular diameter 39.19° ~ 39°
OK   Saturn + full rings fit inside the 50°-wide portrait frame
OK   Camera horizontal FOV 50.00° (lens 38.60 mm, 36 mm sensor)
OK   At 3 s the whole ring system is below the horizon
OK   At 12 s the whole planet is above the horizon
OK   Mass ratio Saturn/Moon = 7740 (~7,700)
OK   Tidal acceleration 2GMR/d^3 = 0.00851 m/s^2 = 0.087 % of g (< 0.1 %)
     Equilibrium tide bulge: Moon 0.53 m -> Saturn ~4,140 m (static upper bound)
OK   On-screen sea drop 10 m on a 3% beach -> shoreline retreats 333 m
     Roche limit: fluid 2.44·R_S·(ρ_S/ρ_E)^(1/3) = 73,447 km (2.455 coeff: 73,898 km); rigid 1.26 coeff: 37,927 km
OK   Fluid Roche limit 73,447 km ~ 73,000 km (5.2x closer than the Moon)
```

Inputs:
- Saturn: equatorial radius 60,268 km, polar radius 54,364 km, mass 5.683e26 kg, density 687 kg/m³.
- A-ring outer edge: 136,780 km.
- Moon: mass 7.342e22 kg.
- Earth: radius 6,371 km, density 5,514 kg/m³.

Results:
- **Saturn:** 2·atan(R/d) = **17.82°**. The true limb of a sphere, 2·asin(R/d), gives 18.04°. The brief's 17.8° uses the atan (flat-disc) convention.
- **Rings:** 2·atan(136,780/384,400) = **39.17°**.
- **Roche limit:** the ~73,000 km figure comes from the fluid-body formula d ≈ 2.44 R_Saturn (ρ_Saturn/ρ_Earth)^(1/3) = 73,447 km. The rigid-body formula gives about 38,000 km.

## Real vs faked

**Real**
- **Saturn scale:** Saturn sits 6,000 scene metres from the camera, which stands for 384,400 km. Its radius and ring radius are scaled by the same factor. The camera has a real 50° horizontal FOV, so the on-screen size is physically correct. Push-ins are dollies, not zooms, so Saturn's apparent size never changes.
- **Saturn shape:** it is oblate (polar/equatorial ratio 0.902).
- **Rings:** ring boundaries are real: C ring, B ring, Cassini Division, A ring and Encke Gap.
- **Lighting and shadows:** the shadow of the rings on Saturn and the shadow of Saturn on the rings are computed analytically in the shaders. The sunlight direction is the same one that lights the beach.
- **Rising motion:** the rise is a rigid rotation about a tilted celestial pole, so the rings keep their real geometry as Saturn rises.
- **Numbers:** every number on screen comes from the physics printed above.

**Faked or stylised**
- **Rise speed:** Saturn rises about 47° in 9 s, where real time would be about 3 h.
- **Golden hour to night:** compressed into about 10 s.
- **Planet surfaces:** Saturn and the rings are self-lit emission shaders (lit analytically), not lit by scene lights. This keeps Saturn lit after the Earth sun sets, which is correct, since Saturn is still in sunlight. A separate low "Saturn-shine" sun lamp lights the beach at night.
- **Tide size:** a static equilibrium tide would be about 4 km. Real oceans respond dynamically, so we show the brief's "hundreds of metres": a 10 m sea-level drop on a 3 % beach moves the shoreline back 333 m. The retreat and the returning wave are keyframed, not simulated. The wave is a keyed mesh wall with a white flash hiding the impact, and the sea level is a keyed parent empty for the Ocean-modifier patch plus a flat far-sea plane.
- **Disasters:** the tremors are keyframed camera shake (seeded random, deterministic). The volcano is an emissive cone plus a glow billboard and a point light. The Moon "flung off course" is a 2D inset diagram, not an orbital integration.
- **Camera height:** the camera is 4.5 m above the sand, as if on a dune or lifeguard tower, so the sea and the tide line read well in a vertical frame.
- **Fallbacks:**
  - Ocean modifier unavailable → noise-displaced grid.
  - Sky texture types: `NISHITA` on 4.x, `MULTIPLE_SCATTERING`/`SINGLE_SCATTERING` on 5.x; gradient sky if none is available.
  - Eevee engine ID: `BLENDER_EEVEE_NEXT` on 4.2–4.x, `BLENDER_EEVEE` on 5.x.

## Render time (estimates)

- **Eevee (default), 1080×1920, 64 samples:** about 2–6 s per frame on a mid-range GPU, so about 1–2.5 h for 1500 frames. Each frame also evaluates the ocean modifier (~0.5 M vertices).
- **`--preview`:** about 4× faster.
- **Cycles CPU (4 cores), half resolution, 16 samples:** about 12 s per frame was measured. Full-res Cycles at 128 samples is many hours on CPU, so use a GPU.
- **Building the scene and verifying:** about 3 s.

Test stills were rendered with Cycles at low resolution, because Eevee needs a GPU/EGL context that was not available in the headless test environment.
