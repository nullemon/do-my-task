# Everything That Happens in Space While You Watch This Short (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and **37.97 s** long (1,139 frames). There is also a 16:9 recomposition at
1920×1080. It is one **locked** tripod shot of the user's valley plate (`B_valley.png`, 941×1672, upscaled), facing WSW
from 34° N on a November evening. The scene moves from golden hour into dusk, and the sky fills with effects as the live
counters stack up. One big orange word is shown at a time, synced to the voice. There are no disclaimer captions (user
rule); the on-screen text is factual readouts only.

## Narration (101 words, Kokoro am_michael @ 1.05, −14 LUFS / −1 dBTP)
> In the next 35 seconds, you'll travel over a thousand kilometers. Without moving. Earth carries you around the Sun at
> thirty kilometers a second. The Sun fuses six hundred million tons of hydrogen. Every second. About half a kilo of
> space dust lands on Earth each second. The solar system circles the galaxy at two hundred thirty a second, and
> crosses the cosmos at three hundred seventy. Across the universe, thousands of stars are born each second, and about
> thirty explode. The sunlight on your face left the Sun before you pressed play. And you watched it all from right here.

The spoken word is "tons", but the caption and subtitles say "TONNES" / "tonnes", because the rate is in metric tonnes.

## Live counters: value = rate × t
`t` is the frame time from the first frame (frame *i* shows `t = i/30`). Each counter is computed from its rate every
frame, so a frame shows exactly the value for that elapsed time. The clock "YOU'VE BEEN WATCHING x.x S" is shown above the
stack so anyone can check them. A counter pops in as a big featured card (with the rate in its label), then flies into
the stack. The stack keeps the latest 5 rows, and older rows slide out the top. At the end, the white-out reaches the
last frame, the first frame starts from the same white with every counter at zero, and the Short loops.

| counter | rate used | at 35 s | last frame (37.93 s) |
|---|---|---|---|
| Earth's orbit | 29.78 km/s | 1,042 km | 1,129 km (crosses 1,000 km at 33.6 s; the row flashes) |
| Hydrogen fused by the Sun | 6.0 × 10⁸ t/s (featured sub-line: 4.3 × 10⁶ t/s become energy) | 21.00 bn t | 22.76 bn t |
| Space dust landed | ~0.5 kg/s (shown with ≈) | ≈ 17.5 kg | ≈ 19.0 kg |
| Around the galaxy | 230 km/s | 8,050 km | 8,724 km |
| Through the cosmos (vs the CMB) | 370 km/s | 12,950 km | 14,035 km |
| Stars born (observable universe) | ~5,000/s (rounded to 1,000, ≈) | ≈ 175,000 | ≈ 190,000 |
| Supernovae (observable universe) | ~30/s (rounded to 10, ≈) | ≈ 1,050 | ≈ 1,140 |
| Sunlight that left the Sun at 0:00 | c = 299,792.458 km/s; trip = 499.0 s | 10.5 M km · 7 % | 11.4 M km · 8 % |

The hook ("in the next 35 seconds… over a thousand kilometers") is checked by the orbit row: 29.78 × 35 = 1,042 km.

## Sources and arithmetic
- **Earth's orbital speed:** 29.78 km/s mean (NASA GSFC Earth Fact Sheet). It ranges from 29.29 km/s at aphelion to
  30.29 km/s at perihelion; in November it is about 30.0 km/s, about 1 % above the mean. The mean is used.
- **Solar fusion:** L☉ = 3.828 × 10²⁶ W (IAU 2015 Resolution B3). The mass converted to energy is
  L/c² = 3.828e26 / 8.988e16 = **4.26 × 10⁹ kg/s ≈ 4.3 million t/s**. For hydrogen burning, 4 ¹H (4.0313 u) → ⁴He
  (4.0026 u) releases 0.71 % of the mass, so the hydrogen consumed is 4.26e9 / 0.0071 ≈ **6.0 × 10¹¹ kg/s ≈ 600 million
  t/s**, and about 596 million t/s of helium are formed. This is the textbook figure (e.g. NASA/Stix, *The Sun*).
- **Meteoric dust:** estimates of the material arriving at Earth vary a lot:
  - Love & Brownlee 1993 (*Science* 262, 550) give about 40,000 ± 20,000 t/yr, which is about 1.3 kg/s.
  - Carrillo-Sánchez et al. 2016 (*GRL* 43, 11,979) give 43 ± 14 t/day, which is about 0.5 kg/s.
  - Rojas et al. 2021 (*EPSL* 560, 116794) give about 5,200 t/yr, about 0.17 kg/s, reaching the surface as unmelted
    micrometeorites and cosmic spherules.
  We chose the mid value, **0.5 kg/s**. It is hedged "about" in the voice and "≈ / ~" on screen.
- **Galactic orbit:** the circular speed at the Sun is Θ₀ ≈ 229–236 km/s (Eilers et al. 2019, *ApJ* 871, 120: 229 km/s;
  Reid et al. 2019, *ApJ* 885, 131: 236 km/s). **230 km/s** is used.
- **CMB dipole:** the Sun moves at **369.82 ± 0.11 km/s** relative to the CMB rest frame (Planck 2018 I, *A&A* 641, A1).
  370 km/s is used. The narration says "crosses the cosmos", and the readout says "relative to the Big Bang's afterglow".
- **Stars born per second (order of magnitude):**
  - The present-day cosmic star-formation rate density is ψ(z=0) ≈ 0.015 M☉ yr⁻¹ Mpc⁻³ with a Salpeter IMF (Madau &
    Dickinson 2014, *ARA&A* 52, 415).
  - The comoving volume of the observable universe (radius 46.5 Gly = 14.3 Gpc) is about 1.2 × 10¹³ Mpc³.
  - Together they give about 1.8 × 10¹¹ M☉/yr, about 5,800 M☉/s, or about 3,700 M☉/s with a Chabrier/Kroupa IMF.
  - Mean stellar masses of about 0.4–0.7 M☉ give about **5,000–15,000 stars/s**.
  - We use the conservative **~5,000/s**, and the voice says "thousands".
- **Supernovae per second (order of magnitude):**
  - The local volumetric rates are 0.705 × 10⁻⁴ (core-collapse) + 0.301 × 10⁻⁴ (Ia) yr⁻¹ Mpc⁻³ (Li et al. 2011, *MNRAS*
    412, 1473).
  - Over 1.2 × 10¹³ Mpc³ that is about 1.2 × 10⁹ per year, about 40 per second. Star-formation-based estimates give
    roughly 30–50 per second, and popular figures quote 10–30.
  - We chose **~30/s**, hedged "about thirty" and "≈".
- **Sunlight:** 1 au / c = 149,597,870.7 km / 299,792.458 km/s = **499.0 s = 8 min 19 s**. Light leaving the Sun at
  0:00 has covered c·t: 11.4 million km (about 8 %) by the last frame. So the light reaching you at the end left the Sun
  more than 7 minutes before you pressed play.
- **Sky:** the HYG v4.1 catalogue (V < 6.5) and the vivid Milky Way are copied from `../star-dates/`
  (`skygeo.py`, `mwsky.py`; the caches `stars.npz` and `mw_gal.npz` are copied into scratch).
  - The sidereal time 19.75 → 20.20 h is a November dusk at 34° N, with the Sun at RA ≈ 15.0 h and Dec ≈ −17°.
  - It drifts ~32× faster than real time ("the stars slide subtly").
  - The galactic core sits low in the SW, and the band climbs through Aquila to Cygnus.
  - The ecliptic is drawn with a 23.44° obliquity. Its chevrons flow towards the setting Sun and beyond, which is the
    direction Earth is heading (λ☉ − 90°, below the western horizon at dusk).
  - The speed lines radiate from the real direction of the Sun's galactic motion (l = 90°, b = 0°, in Cygnus, near the
    zenith at the top of the frame).

## Beats
| t (s) | picture |
|---|---|
| 0–0.5 | The white flash fades into the golden-hour valley. Big Sun over the ridge with rainbow beams. The orbit card starts at 0 km. |
| 1.4–14 | The ecliptic with flowing cyan chevrons. "30 km a second". The Sun card on "fuses" sends fusion pulses on every 0.8 s beat, with chromatic rings rolling out over the sky. |
| 14–17.7 | The dust card: a meteor shower of green, orange, cyan and magenta streaks. Dusk falls, stars come out and the Milky Way rises. |
| 17.9–25 | The galaxy card: rainbow speed lines rush out from Cygnus. On "cosmos" they surge magenta at double speed. Distant spiral galaxies fade in. |
| 25.3–31 | Star-birth sparkles burst along the Milky Way ("thousands"). On "explode", supernova flashes and chromatic rings pop in the galaxies (a burst of 9, then ~2/s). |
| 31.2–34.7 | The sunlight card: golden light wavefronts roll out of the Sun, the beams brighten and the valley warms. |
| 35–38 | "WHILE YOU WATCHED, YOU TRAVELLED 1,0xx KM + 13,xxx KM THROUGH THE COSMOS". Speed lines, riser, white-out into the last frame, and the loop. |

Every new card brings a coloured flash and a chromatic shockwave, and the camera never moves.

## Liberties (deliberately not captioned, per the user)
- The Sun is drawn about 5× its true size (true 0.53°) with stylised beams and rings. Its "pulses" are a visual stand-in for
  continuous fusion. It sinks ~4° over 38 s, a time-lapse; in reality the sky would not get this dark while the Sun is
  still up. The dusk is compressed and stylised.
- Star births and supernovae across the observable universe are invisible to the eye. The sparkles along the Milky Way and
  the flashes in procedural spiral galaxies are symbolic, and the galaxies are not real ones.
- The meteor numbers are stylised too: real dust is mostly microscopic, and visible meteors are a few per hour.
- **"Now" across the universe** is a convention. The star and supernova rates use present-day cosmic rates × present-day
  comoving volume. With other conventions (e.g. what we *see* on our past light cone), the numbers change by factors of
  a few. Hence "thousands" and "about thirty", and ≈ on screen.
- The voice says "lands on Earth" for the dust. Much of it ablates high in the atmosphere and settles later as meteoric
  smoke. The ~0.5 kg/s is the total arriving, which is mid-range of the estimates.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (Kokoro am_michael 1.05, word timings via `lib.voice`).
- `audio/mix.py`: a pad and a plucked arpeggio at 75 BPM (the beat is the Sun's 0.8 s pulse), sub pulses on the fusion
  beats, counter ticks that get busier as rows stack up, and a whoosh, bell and thump per card. There are swishes for
  bright meteors, a wind roar that follows the speed-line drive, a riser into "cosmos", a shimmer for star births and
  booms for supernovae. A warm swell plays under the sunlight beat, a riser leads into the white-out, and the loop's
  impact is at t = 0. The mix is ducked under the voice and normalised to −14 LUFS / −1 dBTP, and the script writes
  `out/while-you-watch.srt`.
- `short.py` (picture; `info`, stills), `skygeo.py` and `mwsky.py` (copied from `../star-dates/`, unchanged),
  `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (read-only). Scratch: `.../scratchpad/series/S12-while-you-watch/`.
- Outputs: `out/` (git-ignored): `while-you-watch-short.mp4`, `while-you-watch-16x9.mp4`, `while-you-watch.srt`,
  `thumb.jpg`, `thumb-vertical.jpg`.

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `short.py wide` →
`encode.sh wide` → `thumbnail.py`.
