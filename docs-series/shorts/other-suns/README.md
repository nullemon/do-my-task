# What If Other Stars Replaced Our Sun? (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 38.65 s long. There is also a 16:9 recomposition at 1920×1080. It uses one
locked tripod shot of the user's `A_park.png` (transparent sky) and the reference-style VFX look: rainbow and coloured
light beams, chromatic bloom, diffraction spikes and swap shockwaves. One big orange word is shown at a time, synced
to the voice. A bold readout appears for each star: NAME, × SUN'S SIZE, temperature and angular width. There are no
disclaimer captions (user rule).

## Narration (82 words, Kokoro am_michael @ 1.05)
> What if our Sun was replaced by other stars? Let's start small. Proxima Centauri. A red dwarf, fifteen percent of the
> Sun's width. Noon turns to dim red dusk, and Earth freezes. Sirius. Not even twice as wide, but twenty-five times
> brighter. Oceans boil. Arcturus, an orange giant. Twenty-five times wider, covering thirteen degrees of sky. Rigel, a
> blue supergiant, seventy-nine times wider. Earth? Vaporized. And Betelgeuse? Seven hundred times wider, reaching past
> Mars. We'd be inside the star. Welcome back, Sun.

## Beats (`short.py`)
Each star is placed at 1 au and drawn at its true angular size. The lens has f = 960 px, which is a 90° vertical field
of view on the 1920 px frame. The 16:9 cut keeps the same pixel scale, which gives a 90° horizontal field of view. The
apparent radius is f·tan(asin(R/1 au)), the full geometry rather than the small-angle 0.53°×R rule.

| star | R (R☉) | T (K) | angular width | on screen (radius) | look |
|---|---|---|---|---|---|
| Sun | 1 | 5,772 | 0.53° | 4.5 px + glow | blue sky, rainbow beams |
| Proxima Centauri | 0.154 | ~3,040 | 0.08° | 0.7 px dot | plum/red dusk sky, red-graded park, lamps on, blue-white frost on "freezes" |
| Sirius A | 1.71 | ~9,940 | 0.91° | 7.6 px | harsh blue-white light, hard contrast, heat haze on "boil" |
| Arcturus | 25.4 | ~4,290 | 13.6° | 114 px | orange disc with convection cells, prominences, golden sky |
| Rigel | 78.9 | ~12,100 | 43° | 379 px | blinding blue-white disc, then steam/white-hot park on "vaporized" |
| Betelgeuse | ~764 (640–1,000+) | ~3,600 | (we're inside) | swells until it fills the sky | boiling red-orange plasma sky, embers, heat shimmer |

At each swap, the old star swells, wobbles and implodes. Then come a tinted flash, a chromatic shockwave ring and a
"whoosh". The new star blooms in with an overshoot. At the end, the sky inside Betelgeuse flares to a white-out and
snaps back to the normal Sun on "Welcome back", so the Short loops.

Star surfaces: limb darkening, animated Worley convection cells on the sphere (domain-warped, two scales, rotating),
colour from the local temperature (blackbody LUT) or from a fire ramp for the red/orange giants, prominence tongues on
the limb, corona glow, and 6-blade chromatic diffraction spikes. The foreground is relit per star: gain, light colour,
flattened-shadow fraction, ambient sky colour, a rim light on the skyline, and harsher contrast for the hot stars.

## Science notes and sources
- **Angular size:** θ = 2·asin(R/d). Here R☉/1 au = 0.00465, which gives the Sun's 0.53°. For Arcturus the value is
  2·asin(0.1181) = 13.6°, and for Rigel 2·asin(0.367) = 43.0°. Betelgeuse at 764 R☉ is 3.55 au (1 au = 215 R☉), so
  at 1 au Earth would be inside the star.
- **Sun:** R☉ and Teff = 5,772 K are the IAU 2015 nominal values (Resolution B3).
- **Proxima Centauri:** R = 0.154 R☉ (Boyajian et al. 2012, interferometry). Teff ≈ 3,040 K (Ségransan et al. 2003),
  and L ≈ 0.0016–0.0017 L☉. With L^¼ scaling, Earth's equilibrium temperature would be about 255 K × 0.0017^¼ ≈ 50 K,
  so "Earth freezes". Its visible-light output is only about 1/20,000 of the Sun's, so noon would be very dim.
- **Sirius A:** R = 1.71 R☉ (Davis et al. 2011), Teff ≈ 9,940 K (Adelman 2004), L ≈ 25 L☉ (Liebert et al. 2005).
  The equilibrium temperature would be about 255 K × 25^¼ ≈ 570 K (~300 °C), which means a runaway greenhouse:
  "oceans boil".
- **Arcturus:** R = 25.4 R☉, Teff ≈ 4,290 K (Ramírez & Allende Prieto 2011). The narration says "thirteen degrees"
  and the readout says 13.6°.
- **Rigel:** R = 78.9 R☉ (Moravveji et al. 2012), Teff ≈ 12,100 K (Przybilla et al. 2006), L ≈ 6–12 × 10⁴ L☉. At
  1 au that is tens of thousands of times the solar constant, with an equilibrium temperature of about 4,000 K or
  more, well above the boiling point of rock: "vaporized".
- **Betelgeuse:** R = 764 (+116/−62) R☉ (Joyce et al. 2020). Older estimates run from about 640 to over 1,000 R☉,
  depending on the assumed distance, which is why the readout says "~700–1,000×". Teff ≈ 3,600 K (Levesque & Massey
  2020). Even the low estimate (~3 au) reaches past Mars (1.52 au) and the asteroid belt.

## Liberties (deliberately not captioned, per the user)
- The beams, spikes, shockwaves, swap animation and Betelgeuse's swelling are artistic devices. Betelgeuse is shown
  growing from a disc until it engulfs the sky. Inside its real outer envelope the gas is extremely tenuous, so the
  view would not literally look like a boiling surface.
- The sky colours are stylized for each star. Proxima's sky is a readable plum/red dusk rather than a near-black sky,
  because the user never wants a pitch-black screen. The red dwarf's light would look more orange than deep red to the
  eye.
- The consequences happen instantly: the frost, the boiling haze and the vaporisation steam. The park itself would of
  course not survive Sirius, Rigel or Betelgeuse.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `short.py` (picture; `info`, stills,
  `patch` modes), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/S4-other-suns/`.
- Outputs: `out/` (git-ignored): `other-suns-short.mp4`, `other-suns-16x9.mp4`, `other-suns.srt`, `thumb.jpg`,
  `thumb-vertical.jpg`.
