# What If Betelgeuse Exploded Tonight? (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 37.05 s long. There is also a 16:9 recomposition at 1920×1080. It uses one
locked tripod shot of the user's `A2_park.png` (transparent sky, upscaled 941×1672 → 1080×1920) under the real night sky:
HYG v4.1 stars at their true RA/Dec and B−V colours, latitude 52° N, sidereal time 5.55 h, facing south, with Orion just
east of the meridian and the vivid Milky Way from `../star-dates`. The look follows the reference style (`../other-suns`):
chromatic flash, shockwave rings, rainbow beams, diffraction spikes, bold readouts, and one big orange word at a time.
There are no disclaimer captions (user rule).

## Narration (90 words, Kokoro am_michael @ 1.05, real word timings)
> What if Betelgeuse exploded tonight? First, a silent warning. Neutrinos arrive hours before the light, and detectors
> sound the alarm. Then Orion's shoulder ignites. One point, as bright as the Moon, casting sharp shadows. Next morning,
> it's still there. Visible in daylight, for weeks. Over months, it fades from blue-white to orange-red. Orion loses its
> shoulder forever. And we're safe. It's far too distant to hurt us. Its light takes 550 years to get here. So it might
> already have happened. The light just hasn't reached us yet.

## Beats (`short.py`; times for the 9:16 cut)
| t (s) | picture | readout |
|---|---|---|
| 0–2.5 | Night park, real Orion (stick figure fades in and out), Betelgeuse orange and breathing, airglow drifting. | leader line + BETELGEUSE / 550 LY · RED SUPERGIANT |
| 2.5–9.4 | Neutrino beat: refractive ripples run out of the star on every ping, radial neutrino streaks pass through sky, trees and ground, and Betelgeuse throbs. | phone-style card NEUTRINO ALERT / HOURS BEFORE THE LIGHT |
| 9.4–15.3 | The star swells on "Then", then detonates on "ignites": a white-out flash, a blue-white HDR point with 8 chromatic diffraction spikes (rainbow dispersion along the long ones), rainbow beams, two chromatic shockwave rings and god rays. The lawn is lit blue-white, with long shadows of the conifer, the lamp posts and the big trunk cast by the single point. A second shockwave hits on "Moon". | MAGNITUDE ≈ −11 / AS BRIGHT AS A HALF-TO-FULL MOON / ALL OF IT FROM ONE POINT |
| 15.3–19.4 | Flash cut to a blue daytime sky (camera still locked), with the supernova still blazing and spiked. | VISIBLE IN DAYLIGHT / FOR WEEKS TO MONTHS |
| 19.4–25.4 | Back to night. Over a month counter the point fades and shifts from blue-white through white and yellow to orange-red, then vanishes. Orion's lines come back, dashed into the empty shoulder, with a marker ring. | MONTH 1…12 · FADING · BLUE-WHITE → ORANGE-RED; GONE FOR GOOD / ORION LOSES ITS SHOULDER / LEFT BEHIND: A NEUTRON STAR (MOST LIKELY) |
| 25.4–29.5 | Calm night without the shoulder. | 550 LIGHT-YEARS / DANGER ZONE: WITHIN ~50 LY / WE'RE MORE THAN 10× FARTHER |
| 29.5–37.05 | Twist: a pulse back to tonight's sky with Betelgeuse orange again and an orange shockwave, then a rainbow "light front" ring rolling outward from the star towards us. The final frame matches frame 0, so the Short loops. | THE 1400s / WHEN THE LIGHT WE SEE TONIGHT LEFT |

## Science notes and sources
- **Distance:** ~550 ly. Joyce et al. 2020 (ApJ 902, 63) give 168 (+27/−15) pc ≈ 548 (+88/−49) ly. Older values
  range from ~500 ly (Hipparcos/HYG, 498 ly) to ~650–720 ly (Harper et al. 2008/2017), hence "about 550".
- **When:** Betelgeuse is a ~15–20 M☉ red supergiant in core helium burning. Joyce et al. 2020 estimate core collapse
  in roughly the next 100,000 years. Not "soon" in human terms; the narration says only "what if".
- **Peak brightness:** published estimates for a Type II-P supernova at this distance give an apparent magnitude of
  about −10 to −12. The Moon is about −10 at quarter phase and −12.7 when full, so "as bright as the (half-to-full)
  Moon", with all that light concentrated in one point. That is why it would cast sharp shadows, and why it would stay
  visible in daylight for weeks to months (Venus, at −4.6, is already visible in daylight when you know where to look).
- **Fading and colour:** a II-P plateau lasts ~3 months, then the brightness drops and the radioactive tail fades over
  about a year. The shock-breakout flash is very hot and blue; the plateau photosphere cools to ~5,000–6,000 K, and the
  nebular phase looks reddish (Hα). The Short simplifies this to blue-white → orange-red over about a year.
- **Neutrinos first:** in core collapse the neutrinos escape within seconds, while the shock takes hours (around half a
  day for a red supergiant envelope) to break out of the surface. Detectors such as Super-Kamiokande and IceCube would
  register the burst, and the SuperNova Early Warning System (SNEWS) would send alerts. Pre-supernova neutrinos may even
  be detectable days ahead for a star this close.
- **Safety:** the commonly quoted danger distance for ozone damage is ~25–50 ly (Gehrels et al. 2003: ~8 pc; Melott &
  Thomas 2011). 550 ly is more than 10× farther.
- **The Great Dimming (2019–2020):** caused by a dust cloud ejected by the star, plus a cooler surface patch (Montargès
  et al. 2021, Nature 594, 365). It was not a sign of imminent explosion. This is not narrated, for time.
- **The twist:** the light left ~550 years ago (2026 − 550 ≈ 1476, so "the 1400s"). If it had exploded since then, we
  could not know yet. "Might" is accurate, but the chance is small (~550 / 100,000 ≈ 0.5 %).
- **Left behind:** for its mass, a neutron star is the most likely remnant ("MOST LIKELY" in the readout).

## Liberties (deliberately not captioned, per the user)
- **Shadows:** the shadows are computed on a 2.5-D ground plane fitted to the plate (vanishing line, focal length and
  camera height estimated). The supernova sits ~45° up, which would give short shadows for far objects. The shadow light
  is kept low (19°, and 7° for the distant lamp posts) so the shadows run long towards the camera. Their direction is
  correct for the star's azimuth. Only the conifer, the three lamp posts and the big trunk cast shadows (clean shapes,
  as the lead asked); the canopy and hedge shadows are left out. Real supernova light would be about moonlight-level,
  but the park is lit brighter than that for the spectacle.
- **Daytime:** the camera stays locked south and the supernova stays at Orion's place. In reality, the morning after a
  November explosion Betelgeuse would be low in the west. Later in the winter it is up in the afternoon sky.
- **Colour sequence and "months"** are simplified (see above). The light front ring, the neutrino streaks and ripples,
  the beams and the spikes are artistic devices. Neutrinos are invisible, and the alert card is a stylised "phone alert".
- The sky colours and the Milky Way brightness are stylised (vivid, never pitch black), as the style requires.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (Kokoro via `../lib/voice.py`), and `audio/mix.py`. The mix has a pad that
  turns from night to explosion to day to fade to calm to night, sonar pings and a notification chime, neutrino fizz, a
  riser and a blast/thump/hit at detonation, cut whooshes, daylight chirps, month ticks and the twist riser and pulse.
  It is mixed to −14 LUFS / −1 dBTP and also writes `out/betelgeuse-tonight.srt`.
- `catalog.py` (HYG → `SCR/stars.npz`), `skygeo.py` and `mwsky.py` (copied from `../star-dates`; the latitude and lens
  are changed), `short.py` (picture), `encode.sh` (mux, no `-shortest`) and `thumbnail.py`.
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/S9-betelgeuse/`. Outputs: `out/` (git-ignored):
  `betelgeuse-tonight-short.mp4`, `betelgeuse-tonight-16x9.mp4`, `betelgeuse-tonight.srt`, `thumb.jpg`,
  `thumb-vertical.jpg`.

Pipeline: `catalog.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `short.py wide` →
`encode.sh wide` → `thumbnail.py`.
