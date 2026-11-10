# When You See the Sun Touch the Horizon, It's Already Gone (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and **35.74 s** long (1,072 frames). There is also a 16:9 recomposition at
1920×1080. It is one **locked** tripod shot of the user's valley plate (`B_valley.png`, 941×1672, upscaled) at sunset.
The VFX follow the reference look: rainbow beams, chromatic bloom, flashes with chromatic shockwaves, a hologram X-ray
cutaway, glowing ray paths, and a big green flash. One big orange word is shown at a time, synced to the voice. The
on-screen text is factual readouts only; there are no disclaimer captions (user rule).

## Narration (95 words, Kokoro am_michael @ 1.05, −14 LUFS / −1 dBTP)
> This Sun isn't really there. When it touches the horizon, the real Sun has already set, completely below the ridge.
> Air bends light. Near the ground it's denser, so sunlight curves down to you, lifting the Sun's image by more than its
> own width. The bottom edge lifts most, squashing the Sun into an oval. Then, on a clear evening, the last sliver can
> flash green. Your days are a few minutes longer because of it. And no, it's not the eight-minute light delay. That's
> a myth. Every sunset you've ever watched... was a mirage.

## How the Sun is drawn (`short.py`)
The visible Sun is rendered **through a refraction model**, not as a hand-squashed ellipse:
- The ridge under the Sun is the horizon (altitude 0). The angular scale is K px per arcminute: K = 6.25 in the
  vertical cut (Sun radius 16′ = 100 px) and K = 5 in the 16:9 cut.
- For every pixel at apparent altitude *a*, the true altitude is h = a − R(a). R is Bennett's (1982) standard
  refraction, R = cot(a + 7.31/(a + 4.4)) arcmin with *a* in degrees, which gives **34.5′ at the horizon**.
- The true disc (round and limb-darkened) is sampled at *h*. The lift and the squash therefore come straight from the
  formula:
  - When the lower limb appears to touch the ridge, the true centre is at −18.5′ and the true **upper** limb is at
    −2.5′. The real Sun is entirely below the horizon.
  - The apparent upper limb is then at 26.8′ (refraction 29.3′, against 34.5′ at the bottom), so the disc is
    26.8′ tall by 32′ wide: **16 % squashed**.
- Each colour channel gets a slightly different refraction, so the green/blue image sits higher than the red. This
  gives a green upper rim, exaggerated for visibility.
- The "Etruscan vase" step mirage is a periodic stair term added to h(a) during the squash beat.
- The ghost (dashed ring, "REAL POSITION") is drawn at the true, unrefracted position. The 0.57° arrow joins the true
  centre and the apparent centre.

## Beats
| t (s) | picture |
|---|---|
| 0–1.6 | Golden sunset with rainbow beams; the Sun's lower edge settles onto the ridge ("This Sun isn't really there"). |
| 3.9 | Cyan flash and shockwave. An X-ray hologram window opens in the mountains, showing the true Sun as a dim orange orb with a dashed glowing ring, crosshair ticks and "REAL POSITION". A dashed HORIZON line, "WHAT YOU SEE" and the 0.57° arrow appear. Readout: REFRACTION ≈ 0.57° · MORE THAN THE SUN'S WIDTH (0.53°). |
| 7.7–16 | Rainbow air layers fill the sky (and the cutaway); they crowd together and brighten toward the ground on "denser". Nine glowing ray paths arch from the true Sun over the ridge and down into the camera, with light pulses running along them and a dashed line of sight through the visible Sun. On "lifting", chromatic copies of the disc slide from the true position up to the image. |
| 16–23.4 | The Sun sinks; its oval gets a stepped Etruscan-vase edge and a green upper rim. Readout: SQUASHED ≈ 16 % · 34′ AT THE BOTTOM · 29′ AT THE TOP. |
| 23.5 | **Green flash:** the last sliver turns emerald, with an 8-point green starburst, a horizon streak, green beams, then a green shockwave. The wide green wash fades in ~0.3 s. Readout: GREEN FLASH. |
| 24.8–27.5 | Dusk sky (deep violet, readable). Two stopwatch rings sweep round the set point. Readout: +4–6 MIN OF DAYLIGHT, EVERY DAY · SUNRISE ~2–3 MIN EARLIER · SUNSET ~2–3 MIN LATER. |
| 27.6–31.4 | Gold and magenta light wavefronts roll out of the set point. Readout: MYTH BUSTED · 8 MIN 19 S LIGHT DELAY ≠ A 2° SHIFT · REAL DIRECTION SHIFT: ~20″ (ABERRATION). |
| 31.5–35.7 | The ghost, the rays and the air layers return ("…was a mirage"). Riser, white-out at 34.49 s, and the Sun pops back to its start position, which is also frame 0 (loop). |

## Science notes and sources
- **Refraction at the horizon:** ~34′ is the standard value (Bennett 1982, *J. Navigation* 35, 255; Saemundsson 1986;
  the *Explanatory Supplement to the Astronomical Almanac*). The Sun's diameter is 31.5′–32.5′ over the year, so
  refraction is slightly more than one solar diameter. Real horizon refraction varies by several arcminutes with the
  temperature profile, and much more under strong inversions.
- **"Already set":** the almanac's sunset is when the Sun's centre is 50′ below the true horizon (34′ refraction + 16′
  semi-diameter), that is, when the upper limb appears to touch the horizon. When the lower limb appears to touch, the
  true upper limb is about 2′ below the horizon (computed above).
- **Squash:** refraction falls off quickly with altitude: 34.5′ at 0°, 29.3′ at 0.45°. That flattens the disc
  vertically by about 16 % when it rests on the horizon, and more at sunset itself. The lower limb is lifted more.
- **Green flash:** air disperses light, so green and blue images are refracted slightly more than red (by a fraction of
  an arcminute at the horizon). Blue is mostly scattered away, so the last sliver can look green for about 1–2 s.
  It needs a clear, distant, sharp horizon; it is often enhanced by mirages (Young, *Green flashes and mirages*,
  SDSU; O'Connell 1958). The 16:9 and vertical cuts exaggerate its size, brightness and duration.
- **Longer days:** refraction moves the Sun by 34′ of altitude at each end of the day. Near the horizon the Sun's
  altitude changes at 15°/h × cos φ × cos δ × sin H. At the equinox that is 15 cos φ °/h, so 0.57° takes
  2.3/cos φ minutes: **2.3 min at the equator, 2.6 at 30°, 3.0 at 40°**, at each end. That gives **≈ 4.5–6 min of
  daylight per day** at low and mid latitudes. The extension is longer near the solstices and at high latitudes,
  which is why the readout gives a range. (The brief suggested "+2–4 min of daylight"; that is the per-end figure,
  so the readout says +4–6 MIN a day with 2–3 MIN at each end.)
- **Light travel time:** 1 au / c = 499.0 s = 8 min 19 s. In that time the Sun moves about 2° across the sky
  (15°/h × 8.3 min), but that does **not** displace where we see it. What shifts the apparent direction is annual
  aberration from Earth's orbital velocity, κ = v/c ≈ 20.5″, which is about 1/100 of a degree. (The solar-system
  barycentre/light-time correction is also tiny.) That is the myth-bust.

## Liberties (deliberately not captioned, per the user)
- The Sun is drawn about 4–5× larger than a phone-width field would show it, and its setting is time-lapsed: the real
  Sun sinks one diameter in about 2–3 minutes. The refraction geometry is to scale with the drawn Sun (34.5′ lift
  against a 32′ disc).
- The ridge is treated as the astronomical horizon. A real elevated ridge is above 0° altitude, where refraction is a
  little smaller.
- Dispersion (green rim), the Etruscan-vase steps and the green flash are exaggerated. Ray paths, air bands, the
  hologram cutaway, beams and shockwaves are graphic devices. The ray curvature is drawn hugely exaggerated, since
  real rays bend by only half a degree.
- The post-sunset sky is kept bright and readable, per the user's rule.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (Kokoro am_michael 1.05 with word timings via `lib.voice`).
- `audio/mix.py`: an A maj9 golden pad changing to an F min9 dusk pad after the green flash, a low drone, and a
  whoosh and sub thump per flash. There are a hologram hum and data blips under the ghost, airy rising tones for the
  rays, and a wobbling mirage tone through the squash. The green flash gets a riser, a bell chord, a shimmer and a
  boom. Clock ticks play for the extra minutes, a glitch sweep for the myth, and a riser and impact for the white-out
  loop. The mix is ducked under the voice, loudnormed to −14 LUFS / −1 dBTP, and the script writes
  `out/sunset-mirage.srt`.
- `short.py` (picture; `info`, stills, `patch`), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (read-only). Scratch: `.../scratchpad/series/S8-sunset-mirage/`.
- Outputs: `out/` (git-ignored): `sunset-mirage-short.mp4`, `sunset-mirage-16x9.mp4`, `sunset-mirage.srt`,
  `thumb.jpg`, `thumb-vertical.jpg`.

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `short.py wide` →
`encode.sh wide` → `thumbnail.py`.
