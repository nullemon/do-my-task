# If the 1859 Solar Storm Hit Today (YouTube Short)

1080×1920, 30 fps, 38.5 s, plus a 16:9 recomposition (1920×1080). It follows the bold VFX style (see
`../lib/README.md`). **Locked camera:** one tripod frame of the user's city plate (`C_city.png`) for the whole Short.
All the action is in the sky and the city lights.

## Narration (90 words, Kokoro am_michael @ 1.05, real word timings)
> In 1859, the Sun fired the biggest storm in recorded history. If it hit today… Richard Carrington saw a white flare.
> 17.6 hours later, it hit Earth. The sky erupted. Auroras reached the Caribbean. People read newspapers by their
> light. Telegraphs sparked and shocked operators. Today, it could burn out transformers. Cities could go dark for
> months. No phones. No GPS. Damage could reach trillions of dollars. In 2012, one this big missed us by about nine
> days. It's only a matter of when.

## Beats
| t (s) | picture / sound |
|---|---|
| 0–6.3 | Dusk city with all lights on. On "fired", a white flare flashes from the Sun just below the horizon glow and chromatic beams fan out (riser, whoosh, boom). Label: THE CARRINGTON EVENT · 1–2 SEPTEMBER 1859. |
| 6.6–12.8 | Second flare pulse on "flare" (1 SEP 1859 · WHITE-LIGHT SOLAR FLARE / SEEN BY RICHARD CARRINGTON). The sky darkens to deep blue. The "17.6 HOURS" counter runs with ticks. A faint aurora rises on the horizon, then a chromatic shock front sweeps the sky on "hit Earth". |
| 12.8–20.6 | "ERUPTED": the hero aurora. Folded green curtains with bright lower edges and magenta fringes, and crimson tops, race overhead and bend into a corona at the magnetic zenith. Rays drift and flicker, pulses run up the curtains, and brightness surges travel along them. The city is tinted green and red. Readouts: AURORAS IN THE CARIBBEAN · NEWSPAPERS READ BY AURORA LIGHT · TELEGRAPHS SPARKED (with spark zaps). Audio: shimmer, crackle and a pulsing minor pad. |
| 21–24.8 | TODAY · POWER GRID FAILING. Brown-out flicker, then five blue-green transformer flashes along the skyline (arcs and booms). The windows die in four block waves and the five street lamps pop. The hum powers down and the music drops to near silence. |
| 24.8–28 | A dark city silhouette under the blazing aurora, lit only by its green and red light and a few flickering emergency lights. Glitching phone and GPS icons: NO SIGNAL / GPS LOST (digital glitch sounds). |
| 28–34.5 | CARRINGTON-CLASS STORM, US COST · $0.6–2.6 TRILLION · LLOYD'S ESTIMATE (2013). Then 23 JULY 2012 · MISSED BY ~9 DAYS (pass-by whoosh). |
| 34.7–38.5 | The aurora fades. The lights flicker back on in waves and the hum powers up. The dusk sky returns, so the last frame matches the first (loop). |

## The aurora (`aurora.py`)
The aurora is physically inspired. Each curtain is a folded sheet whose lower border is at about 100 km. The sheet
is extruded upward along the geomagnetic field direction. Field-aligned rays are parallel in 3-D, so in the image
they converge on one vanishing point, the magnetic zenith. That is how the overhead curtains turn into a corona.

Emission along each field line:
- 557.7 nm green, with a sharp, bright lower edge, decaying upward.
- 630 nm crimson, high up at about 200–400 km. Red dominated great storms such as 1859.
- An N₂ magenta lower fringe (storm-time).

Rendering: sample points are projected and splatted into a polar canvas centred on the zenith point. The canvas is
blurred along the angle at a constant width in screen pixels, so the rays stay soft near the zenith instead of
turning into laser spokes. It is then remapped to the screen. Overlapping folds brighten naturally. Liberties:
- The magnetic zenith is placed in frame, at roughly 40° elevation, for the composition.
- Colours are saturated.
- Motion runs faster than real time.

## Sources and phrasing
- **Carrington Event:** 1–2 September 1859. Richard Carrington (and independently Richard Hodgson) saw a white-light
  flare on 1 Sep. The CME took about 17.6 h to reach Earth. Auroras were seen at low latitudes (Cuba, Jamaica, the
  Caribbean, Hawaii, south-central Mexico; Colombia reports are debated). In the US northeast, people could read
  newspapers by the aurora light. Telegraph systems sparked and gave operators shocks, and some lines kept working on
  auroral current with their batteries disconnected (the Boston–Portland exchange). Source: Wikipedia, "Carrington Event", and the sources it cites.
- **Cost:** Lloyd's & AER (2013), "Solar Storm Risk to the North American Electric Grid", estimates $0.6–2.6 trillion
  (US) for a Carrington-level storm, with 20–40 million people facing outages lasting weeks to 1–2 years. The narration
  says "could", and the label says "estimate".
- **July 2012 near miss:** a Carrington-class CME crossed Earth's orbit on 23 July 2012 and hit STEREO-A (Baker et al.
  2013, *Space Weather*; NASA Science 2014). Berkeley News and other outlets say the source region pointed at Earth about
  nine days earlier. NASA's own wording is "one week earlier". The narration says "about nine days" and the label says "~9 DAYS".
- **May 2024 "Gannon" storm:** the first G5 storm since 2003. It was left out of the narration so the Short fits under 40 s.

## Caveats
- **"No phones. No GPS."** is a possible consequence in the "could" scenario. Phone networks depend on grid power
  (towers have limited battery backup). GPS can be degraded by ionospheric disturbance and could be lost outright.
  The icons are a dramatisation.
- **The plate is a modern European city.** It stands in for "a city today".
- **Time is compressed.** 17.6 h becomes about 3 s, and the blackout and restoration take seconds.

## Files
- `audio/narration.py`: text.
- `audio/gen_voice.py`: Kokoro with word timings (copied from S2).
- `audio/mix.py`: sound design, −14 LUFS, SRT.
- `aurora.py`: the aurora.
- `short.py`: the picture. Its `City` light decomposition is copied from `../milky-way-blackout/short.py`.
- `encode.sh`: muxes without `-shortest`.
- `thumbnail.py`: the thumbnails.

Scratch: `.../scratchpad/series/S6-solar-storm/`. Outputs: `out/` (git-ignored).

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` (`short.py patch vert t0:t1,…` re-renders ranges) → `encode.sh vert` → `short.py wide` →
`encode.sh wide` → `thumbnail.py vert` / `thumbnail.py wide`.
