# What If the Moon Got Closer? (YouTube Short, 9:16 only)

The video is 1080×1920 at 30 fps and 38.6 s long. It follows the BATCH2 "swap" format, as in `other-moons/` and
`planets-as-moon/`. It is one locked tripod shot of the user's `B_valley.png` (transparent sky), going from blue hour
into night. The Moon is swapped in at closer and closer distances. Every swap has a flash, a chromatic shockwave and
coloured moonlight beams, and the valley is relit by a brighter Moon each time. At the Roche limit the Moon cracks,
breaks into fragments that shear along its orbit, and spreads into a glowing ring. A white-out then returns to today's
small Moon, so the Short loops. Big orange one-word captions are synced to the voice. A readout appears at each stage:
DISTANCE / × TODAY'S SIZE · degrees / TIDES × STRONGER / OCEAN TIDE. There are no disclaimer captions (user rule).

## Narration (80 words, Kokoro am_michael @ 1.05)
> What if the Moon got closer? Much closer? Here's today's Moon, for scale. Two hundred thousand kilometers: twice as
> wide, tides seven times stronger. A hundred thousand: fifty-seven times. Oceans surge inland. Fifty thousand: four
> hundred fifty times. Quakes, volcanoes, and every crater in sharp detail. Twenty thousand. Tides kilometers high.
> Moonlight hundreds of times brighter. Eighteen thousand: the Roche limit. Earth's gravity rips the Moon into a
> ring. In reality, it's drifting away: three point eight centimeters a year.

"Roche" is spoken as "Roshe" (Kokoro reads "Roche" as "roach"). "Rips" replaced "tears", which Kokoro read as "teers".

## Stages (`short.py info`)
Every disc uses θ = 2·asin(1737.4 km / d) through one fixed lens, f = 4000 px (27° vertical field of view). Relative
sizes are exact. Today's Moon is 36 px wide and the Roche-limit Moon is 760 px.

| stage | d (km) | angle | × today | tides ∝ 1/d³ | eq. tide range | moonlight ∝ 1/d² | Moon radius |
|---|---|---|---|---|---|---|---|
| today | 384,400 | 0.52° | 1 | 1 | 0.54 m | 1 | 18 px |
| 200k | 200,000 | 1.0° | 1.9 | 7.1 | 3.8 m | 3.7 | 35 px |
| 100k | 100,000 | 2.0° | 3.8 | 57 | 30 m | 15 | 70 px |
| 50k | 50,000 | 4.0° | 7.7 | 454 | 240 m | 59 | 139 px |
| 20k | 20,000 | 10.0° | 19 | 7,100 | 3.8 km | 369 | 349 px (rises over the ridge) |
| Roche | 18,365 | 10.9° | 21 | 9,200 | 4.9 km | 438 | 380 px |

## Science notes
- **Roche limit:** the fluid limit is d = 2.44·R⊕·(ρ⊕/ρ☾)^⅓ = 2.44 × 6,371 km × (5.514/3.344)^⅓ = 18,365 km. The
  rigid-body limit is 1.26·R⊕·(ρ⊕/ρ☾)^⅓ = 9,480 km. I chose the fluid value because the Moon is far too big for
  material strength to matter, so self-gravity dominates and it behaves close to a fluid body. This is the usual
  textbook figure, "about 18,000 km". The narration says "eighteen thousand" and the readout says "≈ 18,000 KM".
- **Tides:** tidal force ∝ M/d³. The tide-range readout scales the equilibrium lunar tide range, 1.5·(m☾/M⊕)·(R⊕/d)³·R⊕
  = 0.535 m today. Real coastal tides are amplified or damped by basin resonance. At hundreds of metres to kilometres
  this linear scaling is only indicative: oceans and crust would respond nonlinearly.
- **"Oceans surge inland":** at 100,000 km the orbital period would be about 3.6 days, so the lunar tide cycle is about
  16.6 h. A ~30 m equilibrium tide would flood low coasts deeply on every cycle.
- **Quakes and volcanoes:** each body raises tides on the other that also scale as 1/d³. Earth raises tides on the Moon
  81× stronger than the Moon raises on Earth, so tidal heating and stress would rise on both. This is plausible but
  qualitative.
- **Moonlight:** the Moon's surface brightness does not change with distance, so the illuminance it gives scales with
  its solid angle, ∝ 1/d². That is 369× full moonlight at 20,000 km (roughly 40–100 lux, like a lit room), hence
  "hundreds of times brighter". In the picture the valley light is compressed (∝ M^0.56) and the camera stops down.
- **3.8 cm/year:** the recession rate measured by Lunar Laser Ranging.
- **Phase:** a gibbous Moon with a ~36° phase angle, lit from the lower right (the Sun is below the horizon behind the
  camera at blue hour). Earthshine on the night side grows as the Moon nears, because Earth's light on the Moon goes
  as 1/d².

## Liberties (recorded here, deliberately not captioned)
- The distance is geocentric, as the brief specified. Near the horizon the observer is closer by up to √(d²−R⊕²): for
  example, 18,960 km instead of 20,000 km, which makes the disc about 5 % bigger.
- The swap animations, beams, coronas, shockwaves and the 2.8 s Moonrise at the 20,000 km stage are time-compressed
  or artistic. A real close Moon would also move fast across the sky.
- The break-up is stylised. Voronoi fragments with glowing molten seams shear along a screen-space orbit arc and
  flatten into a band in about 3 s, with dust grains and Saturn-like ringlets and faint prismatic edges. A real ring
  would take months to years to form.
- The lava hot spots on the Moon's night side (50,000 km and closer) illustrate tidal volcanism. Earthshine
  brightness is exaggerated for visibility.
- The ocean is not in the plate, so tides are shown only by the readouts, surging valley haze, a ground tremble on
  quake beats and the rumble in the mix. No water is drawn.

## Sources
- Moon: Solar System Scope `8k_moon` (CC BY 4.0, from NASA LRO data), `shorts-common/dl/sss/`.
- Foreground: the user's `B_valley.png`.
- Renderer: `moon.py`, copied and reduced from `../other-moons/moons.py`.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `moon.py`, `short.py` (`info`,
  stills and `patch` modes), `encode.sh` (mux without `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/B2-moon-closer/`.
- Outputs (`out/`, git-ignored): `moon-closer-short.mp4`, `moon-closer.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
