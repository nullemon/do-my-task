# What If a Black Hole Passed Through the Solar System? (YouTube Short, batch 4)

Vertical only: 1080×1920, 30 fps, 42.1 s. One locked tripod shot of the user's `04_city_street_at_night.png` (a
skyscraper canyon, with the sky a narrow strip up the middle) in the swap format. Every swap has a flash, a chromatic
shockwave and coloured beams, and the facades are relit in the beat's colour. The wet street mirrors the sky, as in
rogue-planet. Readouts sit at the top and captions at y = 1150.

At its true size the 10 M☉ hole is invisible: the horizon is 59 km across, and even its Einstein ring is only 0.4′ to
2.5′ wide. So the sky strip carries a circular **TELESCOPE ×N** inset centred on the hole.

## The lensing (`lensmap.py` ← `../black-hole-suns/lens.py`)
- `lens.Tracer` integrates exact Schwarzschild null geodesics for an observer 0.5 AU from a 10 M☉ hole
  (r_obs = 2.5 million Rs).
- The resulting table α → α_sky is expressed in Einstein radii: y(x) = β/θE with x = θ/θE. It matches the point lens
  x − 1/x to better than 0.1 % (printed by `python lensmap.py`).
- In this weak-field regime the curve is universal, so one table serves every distance.
- Each inset pixel is inverse-ray-shot to the source plane. Stars are analytic Gaussian sources found with a KD-tree,
  so arcs, image pairs and the Einstein ring come out with surface brightness conserved. The lensed Milky Way glow
  sits behind them.
- A bright star sits on the hole's path, giving a full Einstein ring on "bend".
- The inset spans 1.75 θE, so the ring sits at 57 % of its radius. The zoom label is the inset scale against the
  plate's lens (f = 1150 px): ×1,160 when far away, ×150 when close.

## Beats (numbers from `science.py`)

| beat | readout | numbers |
|---|---|---|
| the hole | 10× THE SUN'S MASS · 59 KM WIDE; EINSTEIN RING x.x′ | Rs = 29.5 km; θE = √(2Rs/D): 0.39′ at 30 AU, 2.2′ at 1 AU |
| Neptune's orbit | 30 AU; PULL ON NEPTUNE UP TO 90× THE SUN'S | (10/10²)/(1/30.07²) = 90 when the hole is 10 AU from Neptune |
| past the Sun | CLOSEST 1.65 AU; IT COULD OUTSHINE VENUS | N-body run below |
| Earth's orbit | 1 AU → 0.56–3.4 AU; A SLIGHTLY CLOSER PASS EJECTS EARTH | N-body run below |
| gone | 50 km/s, back to interstellar space | |
| the odds | ~1 IN 250,000 OVER THE SUN'S LIFE; ~100 MILLION BLACK HOLES IN OUR GALAXY | see below |

- **N-body run** (`science.py`): leapfrog with the Sun, Earth, Jupiter, Neptune and the hole, in the ecliptic, with
  v∞ = 50 km/s. The Short uses b = 4 AU at Earth phase 3.0: closest 1.65 AU to the Sun and 0.75 AU to Earth. Earth
  ends on a = 1.99 AU, e = 0.72 (perihelion 0.56, aphelion 3.42 AU). With b = 3–3.5 AU and other phases, Earth is
  ejected, hence "or flung away".
- **Glow from stolen gas:** Bondi accretion of the solar wind (5 cm⁻³ at 1 AU, falling as 1/r², at 450 km/s) at
  1.65 AU gives Ṁ ≈ 9 × 10⁵ kg/s. With 10⁻³ to 10⁻¹ radiative efficiency that is L ≈ 10²⁰–10²² W, magnitude about −10
  to −15 seen from ~1 AU. It "could outshine Venus" (−4.6) even at much lower efficiency. The Bondi radius 2GM/v² ≈
  0.09 AU (~2 θE on screen) motivates the size of the orange-to-violet swirl in the inset.
- **Odds:**
  - local stellar black-hole density ~10⁻⁴ pc⁻³ (~10⁸ holes in the Galaxy);
  - v = 50 km/s; a pass inside Neptune's orbit, with gravitational focusing ×1.26;
  - that gives one passage per 2.3 × 10¹⁵ yr, a 4 × 10⁻⁶ chance (≈ 1 in 250,000) over 10 Gyr.
  - This is uncertain by a factor of a few.

## Narration (71 words)
Kokoro, style 0.7 × am_michael + 0.3 × am_onyx, speed 0.86, one TTS call per phrase. Pauses are 0.5 s and 1.2 s.

> What if a black hole... / passed through the solar system? / Ten times the Sun's mass... / only sixty kilometres
> wide. / You can't see it... / but the stars behind it... bend. / It crosses Neptune's orbit... / and the planets
> wobble. / It swings past the Sun... / glowing with stolen gas. / And Earth's orbit... / is stretched... or flung away.
> / Then it's gone. / The odds are almost zero... / but our galaxy hides a hundred million of them.

## Sound (BATCH4 clean rules)
The sound is `lib.mix_clean.clean_voice` plus `lib.mix_clean.mix` (pad and gentle swap whoosh) and nothing else. The bed
alone is **23.7 dB** under the full mix (stems before the final loudnorm). Final mp4: −14.2 LUFS, −1.9 dBTP (AAC 192k).

## Liberties (not captioned)
- **The black shadow is drawn at 0.2 θE so it reads.** At true scale it is ~0.001 θE (≈0.2″), sub-pixel even in the
  inset.
- **The star field is very rich:** ~110 stars per θE², defined in Einstein-radius units so the warping reads at every
  distance.
- The hole's motion across the background is time-compressed and constant in θE per second. The whole passage
  (years) runs in about 30 s.
- The inset is a telescope view; its border, ticks and zoom label are a display device.
- The accretion swirl's shape is artistic; its existence and rough scale are from the Bondi estimate.
- The city's tints and the beams are artistic.

## Files
- `audio/` (`narration.py`, `gen_voice.py`, `mix.py`), `science.py`, `lensmap.py`.
- `short.py` (`info`, `vert t,...`, `segs`), `thumbnail.py`, `encode.sh`.
- Scratch: `.../scratchpad/series/B4-black-hole-flyby/`.
- Outputs in `out/`.
