# What If Comets Passed as Close as the Moon? (YouTube Short)

The cut is vertical only: 1080×1920 at 30 fps, 38.82 s. It is one locked tripod shot of `A2_park.png` at night, under a
deep-blue sky that is never black, in the "swap" format of `../other-suns` and `../planets-as-moon`. The Moon is
replaced by famous comets placed at the Moon's distance (384,400 km). Every swap has a tinted flash, a chromatic
shockwave and beams. The new comet blooms in and its tails shoot out. The park is relit by the comet's light, which is
green for the C2 comas and golden for the dust-rich comets. Hale-Bopp and McNaught also cast soft shadows. Each comet
gets a 4-line readout (NAME / NUCLEUS / TAIL / fact). Big orange one-word captions sit at 50 % height. A white-out
returns to the Moon, so the Short loops. There are no disclaimer captions (user rule).

Files: `short.py` (scene and timeline), `comets.py` (comet renderer and nucleus loupe), `audio/` (narration, voice,
mix), `encode.sh vert`, `thumbnail.py`. Scratch is in `scratchpad/series/B2-comet-close/`.
Outputs are in `out/`: `comet-close-short.mp4`, `comet-close.srt`, `thumb-vertical.jpg` and `thumb.jpg`.

## Narration (74 words, Kokoro am_michael @ 0.92, real word timings; ~0.35 s between sentences, ~0.7 s at beat changes)
> What if a comet passed as close as the Moon? / Halley's Comet. Its nucleus is a dark potato, just 15 kilometres long.
> But its green coma would span 15 degrees. / Hale-Bopp. Bright enough to cast shadows. / NEOWISE. A golden tail,
> tinted by sodium. / 67P, the rubber-duck comet. Spitting jets. / And McNaught. A striped fan, filling the entire sky. /
> Comets are dirty snowballs, a few kilometres wide... with tails millions of kilometres long.

## Geometry (the plate's lens, f = 1148 px, horizon at y = 1501)
| object | true size | at 384,400 km | on screen |
|---|---|---|---|
| Moon | 3,474 km | 0.52° | r = 5.2 px |
| Halley nucleus | 15.3 × 7.2 km (Giotto/Vega) | 0.0023° | 0.02 px, so it is shown in a loupe |
| Halley coma | ~100,000 km | **14.8°** | r = 149 px (the soft green halo) |
| Hale-Bopp nucleus | 60 ± 20 km | 0.009° | sub-pixel |
| Hale-Bopp coma | ~300,000 km bright coma, with a faint halo to ~10⁶ km | 43° | r = 448 px |
| NEOWISE nucleus / coma | ~5 km / ~50,000 km | 0.0007° / 7.4° | r = 75 px |
| 67P nucleus / coma | 4.3 × 4.1 km / ~20,000 km | 0.0006° / 3.0° | loupe / r = 30 px |
| McNaught nucleus / coma | ~3 km / ~80,000 km | 0.0005° / 11.9° | r = 119 px |
| tails | 10⁷–10⁸ km+ | → the anti-sun point | run off the frame |

A tail 10⁷–10⁸ km long, seen from 384,400 km, converges on the anti-sun point, which is up to ~180° away. It would
therefore stretch from the head across the whole sky. Each tail runs off the frame (FOV ~53° above the horizon).

## The comet model (`comets.py`)
- **Coma:** C2 Swan-band green. The profile is ~1/ρ (a freely expanding gas), cut off at the true coma radius, plus a
  soft halo that marks the full extent. The coma is compressed on the sunward side (the parabolic hood). Hale-Bopp also
  has expanding shells, after its famous jets and spiral shells.
- **Ion tail:** CO⁺ blue, straight along the anti-sun line. It is made of fine, smooth, field-aligned filaments that
  stream outward. A disconnection event repeats every 5.5–9 s: the tail snaps at a front that moves outward, with a
  kink beyond it.
- **Dust tail:** yellow-white reflected sunlight, curved because older dust lags the orbit. It is drawn as a fan of
  synchrones. McNaught has many uneven striae; these really are synchronic bands, which Wikipedia links to three active
  areas on the rotating nucleus.
- **Sodium tail:** a narrow yellow-orange tail between the ion and dust tails. NEOWISE's was confirmed on 13 July 2020,
  and Hale-Bopp also had one.
- **Nucleus loupes:**
  - Halley: a lumpy 15 × 8 km "potato", albedo ~4 %.
  - 67P: two lobes (4.1 × 3.3 × 1.8 km and 2.6 × 2.3 × 1.8 km) joined by a neck: the rubber duck.
  - Both show sunward jets. 67P also has three outbursts, each an expanding sunward puff in the loupe and an expanding
    shell in the sky.

## Brightness (relighting the park)
The comets keep their real peak brightness, but at lunar distance instead of their real Earth distance:
m = m_peak − 5 log10(Δ / 384,400 km).
- **Halley 1986:** +2.4 at 0.42 AU, giving ≈ −8.7.
- **NEOWISE:** ~+1 at 0.69 AU, giving ≈ −11.
- **Hale-Bopp:** −0.8 at 1.32 AU, giving **−14.3**, about 4.4× the full Moon (−12.74). That is the source of the
  readout "~4× brighter than the full Moon" and of "bright enough to cast shadows". The narration no longer says it, but the readout still gives Hale-Bopp's nucleus as ~60 km.
- **67P (2021):** ~+9 at 1.3 AU, giving ≈ −4.5.
- **McNaught:** −5.5 at ~0.82 AU, giving ≈ −18.

The park light follows this order (67P < Halley < NEOWISE < Hale-Bopp < McNaught), compressed into a moonlit range.
The park has a night grade: a scotopic, desaturated blue-green ambient plus the comet's coloured light and the two lamps.

## Sources (Wikipedia, fetched 13 Nov 2026)
- **Halley:** 14.4 × 7.4 × 7.4 km (Giotto) and 15.3 × 7.2 × 7.2 km (Vega); the ion tail "may extend more than 100
  million kilometres".
- **Hale-Bopp:** nucleus 60 ± 20 km; dust tail 40–45° across the sky; a neutral sodium tail.
- **NEOWISE (C/2020 F3):** nucleus ~5 km (NEOWISE IR and Parker Solar Probe). A blue gas/ion tail and a golden dust
  tail; the sodium tail was confirmed on 13 July 2020.
- **67P:** 4.3 × 4.1 km; lobes 4.1 × 3.3 × 1.8 and 2.6 × 2.3 × 1.8 km; the "rubber duck" nickname; Rosetta 2014–16
  observed outbursts, including one linked to a cliff collapse.
- **McNaught (C/2006 P1):** the brightest comet in over 40 years (since Ikeya–Seki, 1965), peak magnitude −5.5. Ulysses
  crossed its ion tail 260 million km from the nucleus. The striae come from active areas on the nucleus. The mean radius
  is 1.58 km by the Fernández (2012) H-magnitude formula, which gives the "~3 km" figure.
- **Comet tail / coma articles:** comas are 10⁴–10⁶ km, can be larger than the Sun, and are made green by C2. Ion tails
  have been observed to 3.8 AU. The comet tail article describes disconnection events.

## Liberties (not in the narration or readouts as claims)
- **Head positions and tail directions:** these are chosen per comet for composition. The anti-sun direction points up
  at night; real geometry would put the head near the Sun's side of the sky.
- **Coma sizes:** Hale-Bopp's (3×10⁵ km plus a halo) and McNaught's, NEOWISE's and 67P's are representative values.
  Only Halley's 100,000 km / 15° is stated in the readout.
- **Tail lengths in the readouts:**
  - Hale-Bopp "100+ million km" is a lower bound: 40° seen from 1.3 AU means ≥ 0.84 AU projected.
  - NEOWISE "tens of millions of km": ≥ 10° seen from 0.69 AU, about 18 million km projected.
  - McNaught's "~3 km" nucleus is an estimate from a formula, not a measurement.
- **Time compression:**
  - Ion streamer flow, disconnection events (real ones take hours to days), tail rippling and coma breathing are sped up.
  - The 67P outbursts are compressed into seconds.
  - The loupe nuclei rotate slowly; 67P really turns once every 12.4 h.
- **Brightness:** the tails are drawn brighter and more saturated than a real eye would see; the park light is compressed.
- **Heliocentric distance:** each comet keeps the brightness and activity it had near its real peak.
- **Tidal effects:** none. Comets this small have no meaningful tidal effect.

## Pipeline
`audio/gen_voice.py` → `short.py info` → `audio/mix.py` (SRT and mix: −14 LUFS) → `short.py vert` (~2.3 s/frame) →
`encode.sh vert` → `thumbnail.py`.
