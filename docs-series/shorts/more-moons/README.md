# What If Earth Had More Moons? (YouTube Short, batch 3)

The cut is vertical only: 1080×1920 at 30 fps, 47.84 s (measured on the final mp4: −14.0 LUFS, −2.2 dBTP). It is one locked tripod shot of the user's
`03_calm_lake_wooden_pier.png` (transparent sky, upscaled from 941×1672), going from dusk into night. It uses the swap
format of `other-moons/` and `planets-as-moon/`. The sky swaps between moon sets: our Moon, then two Moons, a Mars-style
set, a Jupiter-style set, a Saturn-style swarm, and all of them at once. A white-out then returns to our Moon at dusk,
where a small "lost" companion merges into it, and the Short loops.

Every swap has a tinted flash, a chromatic shockwave and coloured beams, and the scene is relit. Big orange one-word
captions follow the voice. There is a readout per set (NAME / size line / fact line) and no disclaimer small print.

**The lake mirrors the sky.** `lake.py` segments the water with GrabCut, seeded with hand-measured polygons for the pier
deck, its ten posts and the left shore. It also stores how much of each water pixel is the photo's own reflection of the
trees, posts and pine, measured as darkness against a smooth envelope of the bright sky reflection. Each frame then:
- keeps the photo's tree and post reflections, relit for the night;
- replaces the old sunset-sky reflection with the rendered sky (moons, beams, stars, ring), mirrored about the shoreline
  (y = 1346);
- adds a Fresnel-like reflectance (0.86 at the shore down to 0.44 near the camera), slight blur and darkening;
- adds a perspective ripple field: fine near the shore and larger near the camera, with faint glitter;
- makes the ripples much rougher, with a rolling swell, while the narration says the tides would turn chaotic.

The moons sit low over the far shore, so their reflections land on the open water on either side of the pier. In the
Two Moons beat there is one reflection on each side.

## Narration (74 words, REDO v3 voice)
Kokoro style 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per phrase (`lib/v3_redo_q5.py`, unchanged).
Pauses are 0.45–0.5 s between phrases and 1.0–1.2 s before reveals. The v3 post chain is pitch-only. The mix goes to
−14 LUFS / −1 dBTP, with a 17 kHz low-pass before AAC (`encode.sh`).

> What if Earth had more moons? / Ours... just one. / Now... a second Moon. / Two reflections on the lake. / Then...
> Mars-style. / A tiny moon... races across the sky. / Now... Jupiter's four giants. / Moons eclipsing moons. / Then... a
> Saturn swarm. / Dozens of moons... and a ring. / All of them... at once. / The tides would turn chaotic... / and some
> moons might collide. / And yet... long ago... / Earth may have had two moons... / that merged into one.

## Geometry and science (`science.py` prints all of this)
**Lens.** The lens is a long telephoto, f = 10,000 px, so the frame is ~6.2° wide. Every disc is drawn at its true
angular size, θ = 2·asin(R/d), where d is the observer-to-moon distance at ~2° elevation over the lake. A realistic
wide lens would make the Moon a 10 px dot. The "giant moon over the far shore" framing follows the precedent of
`other-moons` (approved). Relative sizes and readouts are exact.

| set | moon | orbit (km from Earth's centre) | angular size | on screen (radius) |
|---|---|---|---|---|
| ours | Moon (R 1,737.4) | 384,400 | 0.52° | 45 px |
| two | second Moon, Moon-sized | 610,200 = 1.587× (2:1 mean-motion resonance; period 55 d vs 27.5 d) | 0.33° | 28 px |
| Mars-style | Phobos-like (mean R 11.08 km, 27×22×18 km) | 20,000 (period 7.8 h; Phobos's is 7.65 h) | 0.07° at 2° elevation (0.09° overhead) | 6 px |
| | Deimos-like ×2 (R 6.2 km) | 44,000 (just beyond geostationary; period 25.5 h) | 1′ | 1.4 px speck |
| Jupiter-style (Galilean orbits × 0.359, so Ganymede sits at the Moon's distance) | Io / Europa / Ganymede / Callisto | 151,400 / 241,000 / 384,400 / 676,100 | 1.38° / 0.74° / 0.79° / 0.41° | 121 / 65 / 69 / 36 px |
| Saturn-style (orbits × 0.315, so Titan sits at the Moon's distance) | Titan / Rhea / Dione / Tethys / Enceladus / Mimas | 384,400 / 165,800 / 118,700 / 92,700 / 74,900 / 58,400 | 0.77° / 0.53° / 0.54° / 0.66° / 0.39° / 0.39° | 67 / 46 / 47 / 58 / 34 / 34 px |
| | Janus, Epimetheus, Prometheus, Pandora, Hyperion + 26 moonlets | 43,800–466,000 | 0.03–0.22° | 3–19 px; moonlets 0.4–3 px |

Mean radii, masses and semi-major axes come from the NASA/JPL fact sheets.

**Readouts:**
- Moon 0.52°; second Moon 0.33° at 610,000 km in a 2:1 resonance.
- Phobos-like 0.07° wide, one orbit every 7.8 h.
- Io 1.38°, Ganymede 0.79°. Io's tides are 20× the Moon's: tidal acceleration ∝ M/d³, (8.93e22 / 7.342e22) × (384,400 / 151,438)³ = 19.9.
- Titan 0.77°. Saturn swarm: "dozens" = 11 named moons + 26 moonlets = 37.
- Finale "46 moons + a ring" counts 17 named discs and specks, 2 Deimos-like, 1 Phobos-like and 26 moonlets.
- "Tides up to 30× today's" is the sum of the finale's tidal accelerations relative to the Moon's, if aligned:
  1 + 0.25 + 19.9 + 2.7 + 2.0 + 0.27 + 1.83 + 0.6 + 0.5 + 0.39 + 0.2 + 0.15 ≈ 29.8.

**Stability (honest physics):**
- Earth's Hill radius is 1.50 million km, and prograde moons are long-term stable within ~0.49 r_H = 733,000 km. Every
  orbit used is inside that: the second Moon is at 0.41 r_H and Callisto-like at 0.45 r_H.
- Phobos-like at 20,000 km is inside the fluid Roche limit for its density (22,300 km) but outside the rigid one
  (11,500 km). Real Phobos is in the same position around Mars, and is slowly being torn apart.
- Big moons around a planet as light as Earth are crowded. Adjacent orbits are only ~2.1–2.3 mutual Hill radii apart (Moon
  and second Moon: 2.25), below the ~3.5 needed for two orbits to be safe without a resonance. A 2:1 resonance (like
  Io–Europa) can protect such a pair, and scaling the Galilean orbits keeps their 1:2:4 Laplace resonance. Even so,
  several heavy moons would perturb each other strongly, hence "the tides would turn chaotic... and some moons might
  collide" (hedged).
- **Eclipses:** all the moons are lit near opposition (phase angle 2.5°): full moons rising at dusk opposite the set Sun.
  Io's shadow on Ganymede is computed from the true geometry: 233,000 km behind Io, umbra 1,475 km and penumbra 5,811 km
  across (Ganymede is 5,268 km). It is offset along the Sun direction by (d_B − d_A)/d_B × f × tan(2.5°), and soft
  across the Sun's 0.27° radius. Io later passes in front of Europa, and its shadow crosses Europa too.
- **The lost moon:** the giant-impact "second moon" hypothesis is Jutzi & Asphaug (2011, *Nature*). A ~1,200 km
  companion (~⅓ of the Moon's width) formed from the impact debris at a Trojan point and, tens of millions of years
  later, collided slowly with the Moon. That collision may have built the far-side highlands. The narration hedges it
  ("may have had"). The merge is shown as the companion drifting behind the Moon's far limb, with a soft flash.

## Liberties (not captioned, per the user rule)
- The telephoto framing (above).
- Motion is time-compressed. The Phobos-like moon crosses the frame in ~6 s, where at a true 31°/h relative rate it would
  take ~12 min to cross 6°. Io slides across in ~6 s, and the finale jitter shows "perturbed orbits".
- The finale puts the Moon, Ganymede and Titan all at 384,400 km at once: a stylised "everything".
- The ring arc is a faint, narrow ring with the Saturn ring radial profile, not scaled from Saturn's rings (scaled, those
  would sit outside Earth's ~18,000–28,000 km Roche zone and fill the sky).
- Beams, corona rings, shockwaves, pointer rings and swap animations are artistic devices. The lake's ripple strength and
  glitter are tuned for readability.
- There is no Phobos map in the cache, so its surface is procedural: a dark, cratered regolith with a large
  Stickney-like crater.
- Captions sit on the pier (y = 1470), not at 50 % height, to keep the low sky clear for the moons.

## Sources
- Moon: Solar System Scope `8k_moon` (CC BY 4.0).
- Io, Europa, Ganymede, Callisto, Titan: USGS mosaics (public domain), as in `other-moons`.
- Mimas, Enceladus, Tethys, Dione, Rhea: Cassini ISS global colour mosaics (Schenk 2014; PIA18437/18435/18439/18434/18438;
  NASA/JPL-Caltech/SSI/LPI, public domain). They were fetched as 1024 px rungs from the GitHub LFS mirror
  `alexmensch/stellata` (`data/textures/*-1024.jpg`) into `shorts-common/dl/moons/`.
- Saturn ring radial profile: Solar System Scope `8k_saturn_ring_alpha.png`.
- Foreground: the user's `03_calm_lake_wooden_pier.png`.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT).
- `science.py` (all numbers), `lake.py` (water mask), `moons.py` (copied from `other-moons/moons.py`, with a settable Sun
  direction), `short.py` (picture; `info`, `stills`, `segs`).
- `encode.sh` (mux, no `-shortest`, 17 kHz low-pass before AAC), `thumbnail.py`. `../lib/` is unchanged.
- Scratch: `.../scratchpad/series/B3-more-moons/`.
- Outputs (`out/`, git-ignored): `more-moons-short.mp4`, `more-moons.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
