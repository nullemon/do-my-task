# 09 · Planet size comparison (ominous, vertical 9:16)

Mercury → Mars → Venus → Earth → Neptune → Uranus → Saturn → Jupiter → KELT-9 b → WASP-17 b →
**HAT-P-67 b** → every world side by side → the Sun slides in. ~60 s, 24 fps, 9:16.
Everything (scene, procedural planet materials, camera move, captions, numpy soundtrack, ffmpeg
encode) is built by `size_comparison.py`. No downloaded assets.

## Facts used (1 Blender unit = 1000 km, true scale, real gaps are not to scale)

| Planet | Radius used | × Earth | Source |
|---|---|---|---|
| Mercury | 2,439.7 km | 0.38 | NASA planetary fact sheet (mean radius) |
| Mars | 3,389.5 km | 0.53 | NASA fact sheet |
| Venus | 6,051.8 km | 0.95 | NASA fact sheet |
| Earth | 6,371.0 km | 1.00 | NASA fact sheet |
| Neptune | 24,622 km | 3.86 | NASA fact sheet |
| Uranus | 25,362 km | 3.98 | NASA fact sheet |
| Saturn | 58,232 km | 9.14 | NASA fact sheet (rings 1.24–2.27 R) |
| Jupiter | 69,911 km | 10.97 | NASA fact sheet |
| KELT-9 b | 1.891 R_J ≈ 135,200 km | 21.2 | Gaudi et al. 2017, *Nature* 546, 514 (the hottest known planet, dayside ~4,600 K) |
| WASP-17 b | 1.991 R_J ≈ 142,300 km | 22.3 | Anderson et al. 2011, *MNRAS* 416, 2108 |
| **HAT-P-67 b** | **2.140 ± 0.025 R_J ≈ 153,000 km** | **24.0** | **Wang et al. 2025, *AJ* 169, 336, "A Revised Density Estimate for the Largest Known Exoplanet, HAT-P-67 b" (arXiv:2504.13997)** |
| Sun | 695,700 km | 109.2 | IAU nominal solar radius |

Exoplanet radii are given in R_J = 71,492 km (Jupiter's equatorial radius, the convention used by
the NASA Exoplanet Archive). Solar-system planets use mean radii.

**Why HAT-P-67 b and how firm is "largest".** As of late 2026, HAT-P-67 b has the largest
*precisely measured* radius of any confirmed planet: 2.140 ± 0.025 R_J. The NASA Exoplanet Archive
overview page lists this value, and the 2025 *AJ* paper calls it "the Largest Known Exoplanet" in its
title. I checked these through web search. The archive's TAP API and arXiv couldn't be reached from the
render box, so it's worth re-checking the archive before publishing. Some
archive rows are bigger, but they don't measure a planet's body. For example, HD 100546 b is listed at
about 6.9 R_J, but that figure comes from the glowing region seen in direct imaging, possibly a
circumplanetary disk, so it has huge uncertainty and isn't a planet's radius. Young directly imaged
objects such as PDS 70 b have similar model-dependent sizes. The other inflated hot Jupiters people
cite are smaller: WASP-17 b (~1.99 R_J), KELT-9 b (~1.89 R_J), TrES-4 b (~1.8 R_J), WASP-12 b (~1.9 R_J).
For that reason the caption says "The largest planet ever measured", and a small on-screen footnote
reads *"largest precisely measured planet radius (Wang et al. 2025)"*. If a new discovery beats it,
change `PLANETS[-1]` and the caption in `STAGES`.

Other caption facts: Jupiter could hold (69,911/6,371)³ ≈ 1,321 Earths, so "1,300 Earths would fit
inside". KELT-9 b's ~4,600 K dayside is hotter than most stars, which are M dwarfs below ~3,900 K.
WASP-17 b is 1.99 R_J, so "Twice as wide as Jupiter". Distances in the HUD: KELT-9 ~670 ly,
WASP-17 ~1,300 ly, HAT-P-67 ~1,200 ly (rounded from Gaia distances).

## Run

```bash
# test stills (look at them first)
python size_comparison.py -- --out OUT --frames 60,300,700,1180,1400
# all frames (resumable: existing PNGs are skipped), soundtrack, MP4
python size_comparison.py -- --out OUT --render            # add --step 2 for a half-rate draft
python size_comparison.py -- --out OUT --audio --encode
```
Use Blender as a Python module (`bpy`) or `blender -b -P size_comparison.py -- ...`. Flags:
`--res 540|1080` (width; height = 16:9 portrait), `--samples N`, `--threads N` (0 = all cores),
`--engine cycles|eevee`, `--gpu`, `--start/--end` frame range, `--blend` (also saves a .blend file).

**On a desktop PC (full quality):**
```bash
blender -b -P size_comparison.py -- --out OUT --res 1080 --engine eevee --samples 64 --threads 0 --render --audio --encode
# or Cycles on GPU:
blender -b -P size_comparison.py -- --out OUT --res 1080 --samples 128 --gpu --threads 0 --render --audio --encode
```

## How it's built
- **Layout**: the planets sit in a row, centers on one line, each gap scaled to the planets beside it.
  The next world always starts just outside the frame. Camera: 50 mm, distance = width × 50/36.
  Every frame keys one framing: (center, visible width), eased with smootherstep on x and on
  log(width), so each reveal trucks right while pulling back. Each hold adds a slow 6 % pull-back.
- **Looks** (all procedural): Mercury uses noise plus two Voronoi crater bump layers. Mars is rust noise
  with polar caps. Venus has pale banded haze. Earth has a noise land mask, ice caps, a separate cloud
  shell and a rim-only atmosphere shell. Neptune and Uranus have faint bands, and Uranus is tilted
  82° with faint vertical rings. Saturn has banding and a ring annulus with C/B/A rings and the Cassini
  gap. Jupiter has bands and an elliptical Great Red Spot, placed so it faces the camera on arrival.
  KELT-9 b is self-emissive orange-white with a heat halo. WASP-17 b is near-black with faint red bands
  and a violet haze rim. HAT-P-67 b is a hazy amber, bloated look with a glow shell. The Sun is an
  emissive granulated disk with limb darkening and a corona, and it is invisible to diffuse rays so it
  doesn't light the scene. Lighting: a warm key Sun lamp from the right (where the Sun is revealed)
  plus a cold back-left rim. Planets spin slowly about their own tilted axes.
- **Stars** are a screen-space image made with numpy (the camera never rotates). An image lookup costs
  about 20× less than a procedural sky in Cycles.
- **Text** is parented to the camera. Each block auto-fits to ≤ 85 % of frame width (its width is
  measured from its bounding box), and fades are keyed on object alpha, so shaders don't re-sync
  every frame.
- **Soundtrack** (numpy → `soundtrack.wav`): a D-minor saw drone (36.7/73.4/110/87.3 Hz, low-passed,
  slow LFOs) with dark band-passed wind. Over it: a master swell, then a filtered-noise riser and a
  deep sweeping boom (78→26 Hz) on each reveal. The bigger the world, the bigger the boom. The Sun
  gets a chord bloom, and everything goes through a 3 s FFT-convolution reverb with soft clipping.
- **Encode**: ffmpeg adds a vignette and light film grain, fades in and out, and writes H.264
  yuv420p at CRF 20 with AAC audio.

## Render used here
540×960, 24 fps, 1438 frames (59.9 s). Cycles CPU, 2 threads, 8 spp adaptive, OpenImageDenoise
(quality FAST, albedo + normal, no prefilter), persistent data. About 3.5–6 s/frame on a shared
4-core box. To save time only the odd frames were rendered (`--render --step 2`, 719 frames;
frames 1–340 were already rendered at full rate). `--encode --step 2` then blends them back to 24 fps
with `minterpolate=mi_mode=blend`, so timing and audio sync stay exact. On a PC, leave out `--step`.
Output: `size_comparison.mp4`, 59.8 s, 540×960, H.264 CRF 20 plus AAC, 27 MB.
Preview stills are in `preview/`.
