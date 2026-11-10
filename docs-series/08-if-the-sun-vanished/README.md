# 08 — IF THE SUN VANISHED RIGHT NOW

**YouTube title:** What Happens If the Sun Disappears Right Now?

**YouTube description (2 lines):**
If the Sun vanished this instant, nothing would change for 8 minutes 20 seconds: the light and the gravity already on their way would keep arriving. Then the sky goes black, Earth leaves in a straight line, the planets wink out one by one, and the long freeze begins. Temperatures and timescales are rough published estimates, and it cannot actually happen.

A 4:47 narrated documentary (1920×1080, 24 fps) in the series look: thin, widely spaced Inter captions, slow camera, grain
and vignette added at the final encode. A clock in the top-left corner (`T + hh:mm:ss`, then days, then years) runs through
the whole film; T = 0 is the frame the Sun disappears (2.35 s in). The opening five seconds deliver what the thumbnail
promises: the Sun is gone, the Earth is still lit, and the caption reads `8 MIN 20 SEC — THEN EVERYTHING CHANGES`.

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with measured times and the shot list |
| `timeline.py`, `audio/locked_starts.json` | voice starts (measured Kokoro durations + the pause before each line), total length |
| `lib.py` | numpy/cv2 renderer, linear HDR: procedural star field and Milky Way; analytic spheres with real maps: Earth (Blue Marble day, night lights, drifting cloud layer with cloud shadows, ocean glint, relief from the topology map, limb scattering, warm terminator, frost), Moon (map + bump relief + extra small craters), Jupiter, Saturn with rings and shadows; procedural Sun (granulation, limb darkening, spots, faculae, prominences, corona); bloom, lens streak, filmic tone-map, type |
| `comp.py` | every shot, locked to the voice. Relights the lake plate (day / starlight / frost), adds sky, sun glare, cirrus, Fresnel lake reflection with ripples, haze, mist, falling flakes; solar-system diagrams (distances to scale); under-ice and vent shots (water absorption, particles, plumes, shimmer). Writes silent x264 CRF 14 segments |
| `blender/landscape.py`, `render_land.sh` | Blender 5.1.2 (bpy, Cycles CPU): one locked-off lake-and-mountain view from a numpy height field (1500² grid, ridged spectral noise), rendered as separate passes (sun, sky/ambient, depth, mirror mask) for bare rock and for snow, so the compositor can relight it |
| `blender/ocean.py`, `render_ocean.sh` | underside of the ice lid and a vent field (lathed, noise-displaced chimneys on a height-field floor), lit by "our own lamp", plus depth passes |
| `audio/narration.py`, `gen_voice.py`, `mix.py` | text, Kokoro TTS (am_michael, speed 0.94, the series voice), voice chain, numpy music bed, ducking, two-pass loudnorm to −14 LUFS, SRT |
| `render_all.sh`, `encode_one.sh` | 2-worker segment render + concat; final encodes (`hq`, `4k`) with vignette, grain, AAC 256k, soft subtitle track |
| `thumbnail.py` | `out/thumb.jpg` 1280×720 |

Rebuild: `gen_voice.py` → `mix.py` (ttsenv) → `bash blender/render_land.sh; bash blender/render_ocean.sh` →
`bash render_all.sh` → `bash encode_one.sh hq|4k` → `python3 thumbnail.py`.

## Facts and sources (checked by web search, Nov 2026)
Only search-result summaries were reachable from this machine (the article pages themselves were blocked), so quotes are
as reported by the search tool. Standard constants are from memory and are marked as such.

- **8 min 20 s.** 1 au = 149,597,870.7 km; at 299,792.458 km/s that is 499.0 s = 8 min 19 s, commonly rounded to
  8 min 20 s (standard constants). Live Science and IFLScience both state that Earth would notice nothing for
  8 min 20 s. The film says "eight minutes and twenty seconds".
- **Gravity travels at light speed.** GW170817 + GRB 170817A arrived 1.74 ± 0.05 s apart after ~130 million light-years,
  constraining the speed of gravity to within −3×10⁻¹⁵ … +7×10⁻¹⁶ of c (Abbott et al. 2017, ApJL 848 L13;
  arXiv:1710.05834). So Earth keeps orbiting the empty point until the same front arrives.
- **Straight line at ~30 km/s.** Earth's mean orbital speed is 29.78 km/s ≈ 107,200 km/h (standard value). Other speeds
  used in the diagram: Mercury 47.4, Venus 35.0, Mars 24.1 km/s.
- **The day side goes dark "at once".** The front crosses one Earth radius (6,371 km) in 0.021 s; the slow-motion shot
  is labelled as such.
- **Moon.** Mean distance 384,400 km = 1.28 light-seconds. A full Moon's extra path is about twice that, so it goes dark
  ≈ 2.6 s after the sky; other phases sooner. Narration: "within about two seconds".
- **Planets** (light time from the Sun: Mercury 3.2 min, Venus 6.0, Mars 12.7, Jupiter 43.3, Saturn 79–80 min; WorldAtlas
  and others give 43.2 and 79.3). A planet's last reflected light reaches us at (Sun→planet) + (planet→Earth). Computed
  from mean distances, counted from the moment our own sky goes dark: Venus 0–12 min, Mars 9–26 min, Jupiter 70–87 min,
  Saturn 143–160 min. Narration: "within about half an hour", "more than an hour", "more than two". The on-screen clock
  values (Jupiter at T+1:25, Saturn at T+2:40) are one possible configuration.
- **Photosynthesis, plants, trees.** Popular Science, "If the Sun went out, how long would life on Earth survive?":
  most plants would die within weeks; large trees could survive much longer on stored sugar (the article says decades;
  the film says "might last for years, if they didn't freeze first").
- **Temperatures (rough estimates).** The same Popular Science piece (quoting Caltech's David Stevenson): the global
  average surface temperature would drop below 0 °F (≈ −18 °C) within a week and to −100 °F (≈ −73 °C) within a year.
  Other outlets repeat the numbers as "0 °C within a week, −73 °C within a year". The film says "below freezing … the
  most quoted figure is around minus eighteen" and "around minus seventy", and labels both as rough estimates.
  South Pole winter means are about −60 °C (standard climatology), hence "colder than a winter at the South Pole".
- **Oceans.** Same source: the surface freezes, the ice insulates, and the deep ocean stays liquid for hundreds of
  thousands of years. Spoken as "by one estimate".
- **Hydrothermal vents.** Chemosynthetic microbes use chemical energy from vent fluids. The film deliberately says
  *microbes* have "the best chance": vent animals such as tube worms also depend on dissolved oxygen that ultimately
  came from photosynthesis.
- **Air condensing.** Boiling points at 1 atm: oxygen −183 °C (90.2 K), nitrogen −196 °C (77.4 K) (standard values).
  When the atmosphere would actually condense is not well constrained in the sources found; the film says "estimates
  run from decades to far longer" and "at normal pressure".
- **Final temperature.** Popular Science / Stevenson: a stable ≈ −400 °F (−240 °C) after millions of years, where heat
  from the interior balances radiation to space. Cross-check: 0.09 W/m² of internal heat gives a black-body
  temperature of ≈ 35 K. A Straight Dope calculation gives 43.6 K (≈ −230 °C). The film says "near minus two hundred
  and forty".
- **It cannot happen; 5 billion years.** Mass-energy conservation. The Sun is ≈ 4.6 billion years old and has roughly
  5 billion years of main-sequence life left (Virginia Tech news, 2026; The Week; standard figure).
- **"Rogue planet" caption.** Free-floating planets are known from microlensing surveys; "thought to be common" is
  hedged on screen.

## Image sources
- Earth day, night lights, water mask, topology and clouds: NASA Blue Marble / Black Marble derived maps shipped in the
  `three-globe` npm package (`example/img`, `example/clouds`).
- Moon, Jupiter, Saturn, Saturn's rings, sunspot map: the planet maps in `jeromeetienne/threex.planets` (MIT repo; the
  maps originate from Planet Pixel Emporium, 1k–2k). Fine detail on top of them is procedural.
- Stars and Milky Way are procedural (not a real sky): star magnitudes follow N(>flux) ∝ flux⁻¹, colours are black-body.
- The lake, the ice and the vent field are original Blender scenes built from numpy height fields.

## Honest limitations
See the hand-off report (kept in sync with what was actually rendered).
