# What If We Lived Inside a Star Cluster? (YouTube Short, 9:16 only)

1080×1920, 30 fps, 38.4 s. BATCH2 "swap" format: one locked tripod shot of the user's `B_valley.png` at night, under a
deep blue/violet sky that is never pitch black. The sky swaps from today's real sky to the sky seen from inside four star
clusters. Each swap has a tinted flash and a chromatic shockwave that starts at the new cluster's core and reveals the new
sky inside the ring, plus coloured light beams from the core. The valley is relit by the combined starlight: cold blue
today, blue in the Pleiades, warm in the Hyades, golden in Omega Centauri and golden-white at the galactic centre. A
readout appears for each sky: NAME / STARS · DISTANCE / STARS BRIGHTER THAN SIRIUS (counts up) / NEAREST STAR. A
white-out at the end returns to today's quiet sky (sidereal time is re-based, so the last frame matches the first and the
Short loops). Big orange one-word captions. No disclaimer captions (user rule).

## Narration (88 words, Kokoro am_michael @ 1.05, real word timings)
> Our night sky has a few thousand stars. Now imagine living inside a star cluster. The Pleiades. A thousand young blue
> stars. Dozens outshine Sirius, glowing through blue dust. The Hyades. Older, with orange giants brighter than Sirius.
> Omega Centauri. Ten million stars. Near the core, almost a million are naked-eye, thousands beat Sirius, and night
> never gets dark. And the galaxy's heart: a million stars within three light-years. The brightest rival the full Moon.
> We live in the galaxy's quiet suburbs. That's why our sky is dark.

"Hyades" is spoken via the respelling "Hiadeez", because Kokoro read it as "HY-aydz".

## How the skies are made (`clusters.py`)
- **Today:** the real sky from HYG v4.1 (`catalog.py`, the same source as star-dates). It contains 5,019 stars with V < 6.0
  ("about 5,000 naked-eye"), which is roughly 2,500 above the horizon at once. Lat 34° N, facing south, with the real
  Pleiades near the meridian. Milky Way from `mwsky.py` (the star-dates look), lens from `skygeo.py`.
- **Clusters:** population synthesis. Masses come from a Kroupa (2001) IMF. M_V and Teff come from a dwarf table: solar
  (after Pecaut & Mamajek 2013) or metal-poor for Omega Cen (turnoff 0.8 M☉ at M_V ≈ +3.9). For the old populations,
  RGB, HB and AGB stars come from the fuel-consumption theorem. The RGB luminosity function is dN/dM_V ∝ 10^(0.3 M_V),
  with N_HB/N_RGB(above the HB) = 1.3 and AGB = 12–15 % of the HB. Omega Cen gets ~3,000 HB stars, many of them blue.
  Positions use a Plummer sphere (massive stars more concentrated in the open clusters) or, for the nuclear star cluster,
  a broken power law (ρ ∝ r^-1.2 inside 0.2 pc and r^-1.8 outside, cut at 10 pc). The Sun-observer sits 1 pc
  (3.3 ly) from each centre. For every star V = M_V + 5 log(d/10 pc), with no extinction. Stars bright enough are drawn
  as points with a PSF, temperature colour, scintillation, halos and diffraction glints. Fainter stars are summed into an
  integrated-light map. The readout numbers are the simulation's outputs (`SCR/stats.json`).

| sky | inputs | stars brighter than Sirius (whole sky) | V < 6 | nearest star | total starlight |
|---|---|---|---|---|---|
| today (HYG) | real catalogue | 0 | 5,019 | 4.24 ly (Proxima) | – |
| Pleiades | 1,100 stars ≥0.1 M☉, 136 pc (444 ly), Plummer a = 2.6 pc (1.6 pc for >1.8 M☉), the 9 named B stars injected with their real M_V (V − 5.67) | 37 (seed range 32–41) | ~240 + the field | 0.7 ly | V ≈ −8 |
| Hyades | 700 stars, 47 pc (153 ly), a = 3.5 pc, θ² Tau + the 4 K giants (γ, δ¹, ε, θ¹ Tau) injected (V − 3.36) | 8 (7–9); giants at V ≈ −3.2 to −1.5 | ~140 + the field | 0.85 ly | V ≈ −5 |
| Omega Centauri | 10 M stars, ~5.4 kpc (~17,000 ly), metal-poor, Plummer a = 6 pc → central density ~1.0×10⁴ stars/pc³ | ~2,200 (2,219–2,317) | ~842,000 | 0.05 ly (~3,200 AU; typical 0.08 ly) | V ≈ −12.3 (≈ full Moon −12.7) |
| galactic centre (NSC) | 1.5 M stars within 1 pc (~10⁶ M☉ of stars, Genzel+ 2010, Schödel+ 2018), 25 M within 10 pc; 8.2 kpc (26,700 ly); + ~280 young O/B/Wolf-Rayet stars within 0.5 pc (Paumard+ 2006, Lu+ 2009) and the red supergiant IRS 7 | ~12,700 | ~2.2 million | 0.016 ly ≈ 6 light-days (typical ~12 light-days) | V ≈ −15.9 (≈ 20 full Moons) |

Brightest single stars: Pleiades −6.3, Hyades −3.2 (an orange giant), Omega Cen −8, galactic centre −12.1 (young
Wolf-Rayet/O stars about 1 pc away: "the brightest rival the full Moon", −12.7).

## Corrections to the brief (verified numbers)
- **Omega Cen density:** the core holds about 10⁴ stars/pc³, which is roughly **100,000×** the solar neighbourhood
  (~0.1 stars/pc³). This is consistent with the often-quoted "~0.1 ly between stars". The brief's "~1,000×" is about the
  cluster-wide average (10⁷ stars in a 150-ly sphere is ~200 stars/pc³). The Short does not quote a density factor.
- **Omega Cen, stars brighter than Sirius:** the brief said "tens of thousands". The simulation gives about **2,200**, so
  the narration says "thousands". "Almost a million naked-eye stars" (842,000 with V < 6) and "night never gets dark"
  (the total starlight is about a full Moon) both hold.
- **Finale:** the nuclear star cluster was chosen over 47 Tuc. It gives ~1.5 million stars within 1 pc (3.3 ly); the
  narration's "a million stars within three light-years" is the round lower figure, and the readout says ~1.5 million.
  Its density at 1 pc is ~1.5×10⁵ stars/pc³ (~1.5 million× ours).

## Liberties (recorded here, deliberately not captioned)
- Each swap's flash, shockwave, beams and reveal are artistic. The sidereal drift is a slow, stylised time-lapse, re-based
  under the white-out so the Short loops.
- In the Pleiades and the Hyades, today's HYG sky (minus the cluster's own catalogued members) stands in for the
  surrounding field stars. The Milky Way keeps its Earth-view look there. It is omitted inside Omega Cen and the galactic
  centre, where integrated starlight would wash it out.
- The point brightness is perceptually compressed (display flux ∝ 10^(−0.32 V)) with bloom halos and 4-point diffraction
  glints. Star colours are saturated ×1.7 (as in star-dates). The open-cluster bright stars get extra glint size.
  Integrated light is compressed (∝ S^0.6). The atmosphere's glow from scattered starlight and the valley gain
  (∝ E^0.3, E = starlight on the ground) are stylised but ordered correctly.
- The Pleiades nebula: the real cluster is passing through a dust cloud (the Merope-nebula reflection). Its wispy blue
  veils are procedural and screen-space around the brightest stars. From inside, they would be fainter.
- Galactic centre: no extinction within the cluster is assumed, but the dark dust lanes are procedural and stylised. The
  circumnuclear disk, 1.5–4 pc out, is real dusty gas. The young stars' M_V (−7 to −1) is approximate, and the
  ~1,000,000-strong population is drawn as a smooth glow plus ~70k distinct stars with V < −0.8.
- The star shadows on the valley are faint 2D shears of the two trees' silhouettes, cast from the three brightest stars.
  They are physically faint because diffuse light dominates.
- The counts depend on the random seed and on where the observer stands. Ranges over seeds are given in the table.

## Files
- `catalog.py` (HYG → `SCR/stars.npz`), `clusters.py` (population synthesis → `SCR/cl_*.npz`, `SCR/stats.json`),
  `skygeo.py`, `mwsky.py` (copied from star-dates), `short.py` (picture; `info`, stills, `patch`), `encode.sh` (mux, no
  `-shortest`), `thumbnail.py`, `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT, −14 LUFS).
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/B2-star-clusters/`. Outputs (git-ignored) in `out/`:
  `star-clusters-short.mp4`, `star-clusters.srt`, `thumb-vertical.jpg`, `thumb.jpg`.

Pipeline: `catalog.py` → `clusters.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh` →
`thumbnail.py vert` / `thumbnail.py wide`.
