# CH2 — "FALLING" (1:00–2:00)

60.0 s · 1440 frames · 24 fps · 1920×1080 · silent master (grain is added at final assembly).

- `gen_textures.py` — numpy-only texture baker (run once). It writes `ch2_*.png` (16-bit) to the shared cache
  `…/scratchpad/andromeda/textures/`: face-on Milky Way and Andromeda (4096²), M33 and LMC (1024²), a tileable
  intergalactic star field (4096²), the 1912 glass-plate negative (3840×2160), and the spectrum strips plus the absorption-line mask.
- `script.py` — the Blender scene. It uses only emission planes with those textures, the star field as a world background in screen space, thin
  emission curves for the orbits, and Inter Light text. Cycles CPU, 3 samples, no lights, no bounces. On 2 threads a frame took ~1.0–1.5 s with the machine quiet and 3–4.5 s while the other chapters were rendering. The full render took 73 min of render time.

```
/home/user/bpyenv/bin/python gen_textures.py
/home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing','--threads','2']; exec(compile(open(p).read(),p,'exec'))"
#   stills:  ... sys.argv=['blender','--','--frames','49,190,300,1151,1380','--out','/some/dir']
```

## Shots and narration sync (seconds from chapter start)

| Time | Picture | VO (PLAN.md) |
|---|---|---|
| 0.0–5.6 | Fade up on a backlit, sepia **glass-plate negative** of M31 (dark galaxy and stars on pale emulsion, scratches, dust, chipped edge, a slight lightbox flicker). Slow push-in. Caption **VESTO SLIPHER · 1912** in dark "ink", 1.5–5.4 | 1.0 "In 1912, astronomer Vesto Slipher measured its light…" |
| 4.3–10.4 | A thin **spectrum strip** appears in sepia on the plate. The plate falls away and colour blooms in (5.6–7.0). Faint rest-wavelength ticks show "WHERE THE LINES SHOULD BE". The absorption lines (Ca H&K, G band, Hβ, Mg b, Na D, Hα) slide off the ticks toward the blue end (6.3–8.4), and "← SHIFTED TOWARD BLUE" appears | "…and found it shifted toward blue" (≈5.5–7.6) |
| 8.9–26 | Dissolve to the **god's-eye Local Group**. The Milky Way is large in the foreground (lower left), Andromeda small and far (upper right), M33 off to its side, and the LMC beside us. The camera pulls back and rises to reveal true separation. Thin labels MILKY WAY / ANDROMEDA / M33 / LMC. Captions **≈ 110 KM/S** (12.3–17.6, sub: "closing speed, relative to the Milky Way") and **≈ 400,000 KM PER HOUR** (18.8–24.6, sub: "roughly the distance to the Moon, every hour") | 9.0 "Andromeda was approaching…", 18.5 "Four hundred thousand kilometres…" |
| 26.3–33 | The classic picture: **one straight thin line** draws from Andromeda to the Milky Way's centre, a glint riding its tip | 26.0 "…a head-on collision was certain." |
| 32.4–37.5 | The straight line fades. A **trembling fan** of short headings opens at Andromeda, showing the unknown sideways drift | 32.0 "But measuring its sideways drift…" |
| 37.8–50 | The fan **blossoms into 26 possible orbits**, all drawn in step with simulated time. Some swing in and settle into the Milky Way, which shows as faint violet-white lines. Others swing past and away, which shows as fainter blue-grey lines. Lines fade out near the Milky Way, so the galaxy itself stays clean. Caption **MERGER CHANCE: ~50% – ~90%** (41.0–49.4, sub: "within 10 billion years · Hubble + Gaia studies, 2025–2026") | 37.5 "Recent studies… coin-flip… ninety percent." |
| 50–60 | All paths fade except one merging orbit, which brightens in the violet accent. The camera swings round behind Andromeda, which begins to move along that path toward the distant Milky Way. Fade to black 58.3–59.9 | 50.0 "So let's follow the version where it comes." |

## Facts used, and honesty notes

- **Slipher.** Vesto Slipher (Lowell Observatory) measured Andromeda's spectrum in 1912 (published 1913). He found an approach speed of ~300 km/s, the first measured galaxy blueshift.
  - **The plate is a stylised evocation, not a facsimile.** Slipher's plates were tiny spectrograms, not portraits of M31. The galaxy negative is our own render of the baked M31 texture, seen at M31's real ~77° inclination with M32 and M110 added.
- **Blueshift exaggerated about 10–15× for visibility.** The real shift is ~0.1% of wavelength (≈0.4 nm at Ca K). On screen the lines move by ~1.6% (λ·(1+z) with z_vis = 0.016). Because the shift is proportional to wavelength, the red lines move further than the blue ones, as in reality. The line list is a typical old-stellar-population absorption set; the spectrum colours are approximate.
- **110 km/s** is the approach speed relative to the Milky Way's centre. The heliocentric value is −301 km/s. 110 km/s × 3600 s ≈ 396,000 km/h, about the Earth–Moon distance (384,400 km) each hour.
- **Layout (1 unit = 1 kpc).** The layout follows real distances:
  - Milky Way–Andromeda: 770 kpc (≈2.5 Mly).
  - M33: ~205 kpc from M31 and ~830 kpc from us.
  - LMC: ~50 kpc from the Galactic centre.
- **Galaxy disks are drawn 1.6× their true size relative to the separation** so they read at 1080p. The disk orientations are artistic. The galaxy textures are procedural, not real imagery.
- **The orbit fan is illustrative, not a published simulation.** It is a toy model: Andromeda's motion relative to the Milky Way, in the Milky Way's frame, in one orbital plane. It uses:
  - a softened point mass of 3.3–4.8 ×10¹² M☉ (total), plus crude dynamical friction near pericentre;
  - a start at 770 kpc, closing at 110 km/s;
  - a sideways speed spread from 0 to ~180 km/s, either sense.

  In this toy ensemble, 18 of 26 paths (69%) merge within 10 Gyr, which sits inside the quoted range. It does **not** include M33 or the LMC, which the real studies show matter. Merging paths are cut a little after the merger. Non-merging paths are drawn to 10 Gyr.
- **Merger odds.** The caption gives the range from two studies:
  - Sawala et al. 2025 (*Nature Astronomy*, Gaia + HST, including M33 and the LMC): ≈50% chance of a merger within 10 Gyr.
  - Wu et al. 2026 (arXiv:2603.22863): ≈90%.

  The older "certain head-on collision" picture is van der Marel et al. 2012 (HST proper motions).
- **The final shot is one scenario.** Andromeda moves ~8% of the way along one merging path in 10 s of screen time. That is roughly the first billion years of approach, compressed.

## Render

The render is resumable (`--skip-existing`; frames write to a `_tmp` file, then are renamed atomically). Frames go to
`…/scratchpad/andromeda/ch2/frames/f_%04d.png`. The master is `…/scratchpad/andromeda/ch2.mp4`
(libx264, crf 16, preset slow, yuv420p, no grain).
