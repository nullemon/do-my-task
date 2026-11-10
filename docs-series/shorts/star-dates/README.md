# Every Star You See Is a Date (YouTube Short)

1080×1920, 30 fps, 34.37 s, plus a 16:9 recomposition (1920×1080). It follows the lead's VFX direction (big, saturated,
moving sky; see `../lib/README.md`). **Locked camera:** a single tripod frame of the user's valley plate (`B_valley.png`,
941×1672 upscaled), facing south. Everything happens in the sky.

## Narration (Kokoro am_michael @ 1.05, real word timings, 83 words)
> That star? Its light left in 2017. That one? Probably before Columbus. Every star you see is a date.
> Arcturus? 1989. Vega? 2001. Deneb? Roughly the Roman Empire. And Andromeda? 2.5 million years ago, before modern
> humans existed. The whole sky is a time machine. And no, almost none of them are dead. Stars live millions to
> billions of years. This light is mostly just centuries old. When you look up, you're looking back in time.

## Beats
| t (s) | picture |
|---|---|
| 0–3 | The golden-hour valley under a pink and orange afterglow, with Sirius already out. A fast fall to a deep blue/violet night. Real stars switch on brightest first, each bright one with a sparkle. The vivid Milky Way rises. |
| 0.5–5.7 | Sirius gets a ring, a burst, a leader line and the label SIRIUS · 8.6 LY, then a big glowing **2017**. Betelgeuse gets BETELGEUSE · ~550 LY and **1400s**. |
| 6–8 | Every star you see is a date: the sky whips round in a time-lapse sweep with rainbow star trails. |
| 8–12 | Arcturus gets **1989** and Vega gets **2001**. The galactic core rises behind the mountains. |
| 12–14.5 | Deneb: **ROMAN EMPIRE** (roughly; ~1,500–2,600 LY). |
| 14.7–19.6 | Andromeda: a big procedural spiral at M31's real place and orientation (PA 35°) grows to about 6× its real 3.2° size, with **2.5 MILLION / YEARS AGO · BEFORE MODERN HUMANS**. |
| 19.6–22.5 | The time-machine swirl: a fast spin, rainbow trails and a colour vortex. About 50 glowing years (2026 − distance) ride their real stars. Near (bright) ones are bigger, and 7 hero years are bigger still. |
| 22.5–30.5 | Myth-bust. A rainbow pulse wave runs over the sky, and every star flares as it passes. The years vanish ("almost none of them are dead"). Then the factual readouts STAR LIFETIMES / MILLIONS–BILLIONS OF YEARS and THIS STARLIGHT / MOSTLY CENTURIES OLD. |
| 30.9–34.4 | Looking back in time: the sky finishes exactly one full turn and the afterglow returns. The last frame matches the first, so the video loops. |

## Data and how the years are computed
- **Catalogue:** HYG v4.1 (`astronexus/HYG-Database`, `hyg/CURRENT/hygdata_v41.csv`, commit c7f7f88, Feb 2025). It
  merges Hipparcos, Yale BSC and Gliese. All 15,458 stars with V < 7 are drawn at their true RA/Dec, with B−V colours.
  `catalog.py` builds `SCR/stars.npz`.
- **Year = 2026 − distance (ly):**
  - Sirius: 8.6 ly → 2017 (HYG 2.64 pc).
  - Vega: 25.0 ly → 2001.
  - Arcturus: 36.7 ly → 1989.
  - Betelgeuse: ~550 ly. Joyce et al. 2020, ApJ 902, 63 gives 168 (+27/−15) pc ≈ 548 (+88/−49) ly. HYG/Hipparcos gives
    498 ly. So the light left about 1390–1527, central about 1478. The label says "1400s" and the narration says
    "probably before Columbus" (1492).
  - Deneb: very uncertain. Hipparcos (HYG) gives 1,412 ly; Schiller & Przybilla 2008 gives ~2,600 ly. The range
    ~1,500–2,600 ly puts the light leaving about 570 BC to AD 530, hedged as "roughly the Roman Empire".
  - Andromeda (M31): ~2.5 million ly (~765–780 kpc). Homo sapiens is about 300,000 years old.
- The tiny swirl years use HYG distances for stars with V < 4.2 and 4–2,500 ly. One label per ~6.5° patch, up to 56 on
  screen. Far stars carry Hipparcos parallax uncertainty, so those small labels are indicative.
- **Lifetimes:** massive stars live millions of years, and Sun-like and smaller stars live billions. Naked-eye stars are
  mostly within ~1,000 ly, so their light is mostly centuries old. Of the six featured, only Betelgeuse is near the end
  of its life (core collapse expected within ~100,000 years). It is almost certainly still there.

## Liberties and caveats
- **One view cannot hold all six targets.** Sirius and Betelgeuse are winter stars; Vega, Deneb, Arcturus and M31 are
  summer/autumn objects. So sidereal time is keyframed as a **stylised time-lapse**: the real sky (34° N, facing south)
  turns about the real pole by one full sidereal day over the Short. At every frame each star is at its true position for
  the sidereal time shown, but the Sun is ignored, so it's a "night" that lasts a whole turn. Latitude 34° N keeps Sirius
  above the caption row.
- **Captions:** 9:16 at y = 1000 (52 %), clear of the Shorts UI; 16:9 at y = 790 (73 %), over the mountains. Labels keep 8 % side margins and avoid the caption row.
- **Lens:** a tilted stereographic (conformal) projection. 9:16 is centred 56° up with f = 700 px. 16:9 is centred 68° up
  with f = 440 px, which is ultra-wide. In 16:9 the true horizon arcs up at the far sides, so stars there are faded at the
  plate's skyline rather than at the true horizon, and a little below-horizon sky shows at the extreme edges.
- **Andromeda** is enlarged to about 6× while it is featured (its real full extent is ~3.2°; to the eye it is a small
  smudge). The sky colours, the Milky Way brightness and the star brightnesses are stylised (vivid), as the style requires.
- The Milky Way is the `milky-way-blackout/mw.py` look, re-built in galactic coordinates in `mwsky.py` so it turns with
  the sky. Its fine structure is procedural, not a survey map, but the band, the core and the Cygnus rift sit at the right
  galactic places.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (a wrapper of `lib.voice` that also fuses "that one?").
- `audio/mix.py`: pad and arpeggio, chimes and bursts per label, whooshes that follow the sky's turning speed, a riser
  into the swirl, pulse thumps. −14 LUFS / −1 dBTP. Writes `out/star-dates.srt`.
- `catalog.py`, `skygeo.py` (sidereal rotation, lens), `mwsky.py`, `short.py` (picture), `encode.sh` (mux, no
  `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (read-only). Scratch: `.../scratchpad/series/S5-star-dates/`. Outputs: `out/` (git-ignored).

Pipeline: `catalog.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `short.py wide` →
`encode.sh wide` → `thumbnail.py vert` / `thumbnail.py wide`.
