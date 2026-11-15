# What If Earth Moved Closer to the Sun? (YouTube Short, batch 3)

The cut is vertical only: 1080×1920 at 30 fps, about 44 s long. It is one locked shot of the user's `01_desert.png`,
upscaled from 941×1672 with its transparent sky filled by the render, in the swap format from `../BATCH3.md`. Earth is
moved closer to the Sun in steps. Each step brings a tinted flash, a chromatic shockwave, beams and a relight of the
dunes. A bold readout appears for every distance, with big orange one-word captions. There is no disclaimer small print.
A white-out at the end returns to today's Sun, so the Short loops.

## Narration (REDO v3 storytelling voice, 73 words)
Kokoro voice style 0.7 × am_michael + 0.3 × am_onyx (blended vectors) at speed 0.86, with one TTS call per phrase
(`audio/narration.py`). There are 0.4–0.5 s pauses between phrases and 1.1–1.15 s before each reveal. The v3 post
chain is applied in `lib/v3_kit.build_voice`, a 17 kHz low-pass before AAC, and the loudness target is −14 LUFS /
−1 dBTP, measured on the final mp4.
> Imagine Earth... drifting closer to the Sun. First... Venus's orbit. Almost twice the sunlight. The oceans begin to
> boil. Now... Mercury's orbit. Nearly seven times the light. The rocks... glow red. Closer still. A hundred times the
> light. The sand... melts into glass. And then... we skim the Sun. Fifty times wider than today. Hot Jupiters...
> really orbit this close. The desert... turns to lava. Turns out... we're in just the right place.

## Beats (`short.py`)
The Sun is always drawn at its true angular size through a lens with f = 1500 px, which gives a 65° vertical field of
view (close to the photo's own lens). The apparent radius is f·tan(asin(R☉/d)).

| step | d (au) | width | × wider | sunlight | on screen (radius) | look |
|---|---|---|---|---|---|---|
| today | 1 | 0.53° | 1 | 1× | 7 px + glare | blue sky, rainbow beams |
| Venus's orbit | 0.723 | 0.74° | 1.38 | 1.91× | 9.6 px crisp textured disc | paler, hazy sky; heat shimmer; steam haze rolls over the dunes on "boil" |
| Mercury's orbit | 0.387 | 1.38° | 2.58 | 6.7× | 18 px textured disc | bleached white sky; sand darkens and its ripple crests glow red; the bush chars |
| 0.1 au | 0.1 | 5.33° | 10 | 100× | 70 px, granulation + sunspots | orange glare sky; glowing orange sand turns to glossy glass (sky reflection, glints, glitter path) |
| skimming | 0.02 | 26.9° | 50 | 2,500× | 359 px: supergranulation, granulation, sunspots, prominences | deep orange sky; the dunes become flowing lava with a dark crust and glowing cracks, the giant Sun mirrored in the melt; smoke, embers, strong shimmer |

From the Venus step onwards, a faint dashed ring of today's size (0.53°) sits on the Sun so that the growth can be read
(requested by the lead). The solar surface reuses the Worley convection cells from `../other-suns/short.py`, coloured
with a solar ramp, and adds limb darkening and sunspot groups.

## Science (checked)
- **Width:** θ = 2·asin(R☉/d), with R☉/1 au = 0.00465. That gives 0.533° at 1 au, 0.737° at 0.723 au, 1.377° at
  0.387 au, 5.33° at 0.1 au and 26.9° at 0.02 au. The "× wider" values are 1/d: 1.38, 2.58, 10 and 50.
- **Light:** sunlight scales as 1/d², giving 1.91×, 6.68×, 100× and 2,500×.
- **Venus's orbit, runaway greenhouse:** the runaway-greenhouse limit for an Earth-like planet is about 1.1× today's
  sunlight, so the inner edge of the habitable zone sits at roughly 0.95–0.99 au (Kopparapu et al. 2013; Leconte
  et al. 2013). At 1.9× the oceans evaporate. The phrase "begin to boil" describes the start of that runaway.
- **Mercury's orbit, rocks glow:** this is TRUE ONLY WITH A THICK ATMOSPHERE. An airless surface would peak at about
  630 K (360 °C) at 0.39 au, which is not hot enough to glow. Once the oceans have become a steam/CO₂ blanket, though,
  scaling Venus's 737 K surface by (6.7/1.9)^¼ gives about 1,000 K. That is above the Draper point (~800 K), so the
  rocks glow dull red. The readout keeps it short: "ROCKS GLOW".
- **0.1 au, sand melts into glass:** the global equilibrium temperature is about 800 K (albedo 0.3), and the airless
  subsolar point is about 1,250 K. With the greenhouse blanket, the Venus scaling gives about 2,000 K. Quartz melts at
  1,713 °C, and impure sand starts to fuse lower.
- **0.02 au:** this is 4.3 R☉ from the Sun's centre, still outside Earth's fluid Roche limit (~1.55 R☉). The airless
  subsolar temperature is about 2,800 K and the global equilibrium about 1,800 K, above the melting point of rock: a
  lava world. Hot Jupiters really orbit this close. For example, WASP-18b orbits at 0.020 au and WASP-12b at 0.023 au,
  and lava worlds such as 55 Cancri e (0.015 au) orbit even closer.

## Liberties (not captioned, per the user rule)
- The changes are instant and the landscape survives each step until the finale. In reality the oceans would take a
  long time to boil away, and the desert would be under a thick steam atmosphere and clouds from the Venus step onwards.
- The sky colours (paler, then bleached, orange and red) are stylized to show heat and glare. The eye-adaptation
  exposure is also compressed: 2,500× the light is not shown as 2,500× brighter.
- The beams, spikes, shockwaves, swap animation and the dashed comparison ring are graphic devices.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `short.py` (picture; `info`,
  stills, `seg` restart-safe segment render via `lib/v3_kit.render`), `encode.sh` (mux, 17 kHz low-pass, no
  `-shortest`, measures LUFS/dBTP), `thumbnail.py`.
- Scratch: `.../scratchpad/series/B3-sun-closer/`.
- Outputs (`out/`, git-ignored): `sun-closer-short.mp4`, `sun-closer.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
