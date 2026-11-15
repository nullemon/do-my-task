# The Sky From Other Moons (YouTube Short, batch 4)

Vertical only: 1080×1920, 30 fps, 46.5 s. One locked tripod shot of the user's `05_tropical_beach.png` in the swap
format. The beach stays the stage while its sky becomes the sky above each moon. The giant planet hangs at its **true
angular size** as seen from that moon's sub-planet surface point, through one fixed lens (f = 1700 px, 59° vertical
field of view).

Each swap has a tinted flash and a chromatic shockwave. The beach is relit by the planet-shine and the distant Sun, and
the calm shallows mirror the sky with a slow, small ripple (the water reflection of eclipses-other-worlds). Readouts
sit at the top and captions at y = 1440.

## Sizes (`python short.py info`; θ = 2·asin(R/d), d = orbit radius − moon radius)

| from | planet | R (km) | d (km) | width | × our Moon |
|---|---|---|---|---|---|
| Earth | the Moon | 1,737.4 | 384,400 | 0.52° | 1 |
| Europa | Jupiter (equatorial) | 71,492 | 669,539 | **12.26°** | 24 |
| Titan | Saturn (equatorial) | 60,268 | 1,219,295 | **5.67°** (A ring edge: 12.9°) | 11 |
| Triton | Neptune | 24,764 | 353,406 | **8.04°** | 15 |
| Charon | Pluto | 1,188.3 | 18,990 | **7.18°** | 14 |
| Phobos | Mars | 3,396.2 | 9,363 | **42.5°** | 82 |

**Correction to the brief:** Pluto from Charon is ~7.2° wide, not ~3.5°; 3.5° is its angular radius. All other brief
values check out.

## Honesty notes
- **Titan:** its thick haze (1.5 bar) hides Saturn from the surface in visible light. The narration therefore goes
  "Saturn hides behind an orange haze... Rise above it..." and the readout changes to "ABOVE TITAN'S HAZE".
- **Saturn's rings from Titan:** Titan orbits almost in Saturn's ring plane (inclination 0.35°), so the rings are shown
  nearly edge-on: a thin bright line 12.9° across, plus the ring shadow on the globe.
- **Pluto:** Charon and Pluto are mutually tidally locked, so Pluto never moves in Charon's sky and Charon always sees
  the same hemisphere. That hemisphere is the one centred on 0° longitude, away from the Sputnik Planitia "heart". The
  map is the New Horizons 2015 colour map (Wikimedia Commons "Pluto-map-sept-16-2015.jpg", CC BY-SA 4.0).
- **Triton** orbits Neptune backwards (retrograde), as the readout says.
- **Phobos** orbits ~6,000 km above Mars's surface.
- **Phases:** each planet is lit from a chosen Sun direction (gibbous or crescent) for readability.

## Narration (74 words)
Kokoro, style 0.7 × am_michael + 0.3 × am_onyx, speed 0.86, one TTS call per phrase. Pauses are 0.45 s and 1.1–1.2 s.

> Imagine standing on another moon... / and looking up. / From Europa... / Jupiter fills the sky. / Twenty-four times
> wider than our Moon. / From Titan... / Saturn hides behind an orange haze. / Rise above it... and there it is, rings
> and all. / From Triton... / Neptune. A deep blue giant. / From Charon... / Pluto hangs in one spot... and never moves.
> / And from Phobos... / Mars. / Eighty times wider than our Moon. / Back home... / our Moon looks tiny. / But it's ours.

## Sound (BATCH4 clean rules)
The sound is `lib.mix_clean.clean_voice` plus `lib.mix_clean.mix` (pad and gentle swap whoosh) and nothing else. The bed
alone is **24.8 dB** under the full mix.

## Liberties (not captioned)
- The tropical beach (palms, sea, hut) stands in for each moon's surface; only the sky, light and reflection change.
- The skies of airless moons are drawn deep navy with stars, never pitch black.
- The planets turn faster than real.
- Beams and flashes are artistic.

## Files
- `audio/` (`narration.py`, `gen_voice.py`, `mix.py`).
- `planets.py`, copied from `../planets-as-moon` with a per-body Sun direction and absolute texture paths.
- `short.py`, `thumbnail.py`, `encode.sh`.
- Textures: Solar System Scope 8k/2k (CC BY 4.0) and the New Horizons Pluto map (CC BY-SA 4.0).
- Scratch: `.../scratchpad/series/B4-moons-sky-views/`.
- Outputs in `out/`.
