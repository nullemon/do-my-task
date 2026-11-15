# What If Venus Were Our Moon? (YouTube Short, batch 4)

The Short is vertical only: 1080×1920 at 30 fps, ~42.5 s. It is one locked tripod shot of the user's
`08_suburban_backyard.png` at night, with the string lights and the house window glowing. It is made in the BATCH4 swap
format: each beat swaps in with a tinted flash and a chromatic shockwave, and the yard is relit for the new light
source. Readouts sit at the top and big orange one-word captions sit below the disc. There is no disclaimer small print,
the sky stays deep blue, and a white-out returns to our Moon so the Short loops.

## Beats
1. **Our Moon:** 0.52° and small.
2. **Venus at the Moon's distance:** 1.80° wide. It blooms in as a **crescent** (phase angle 120°), lit from below by
   the set Sun, and is already ~9× brighter than the full Moon.
3. **Half** (90°): ~19× the full Moon.
4. **Full** (~4°): ~69× the full Moon. The sky turns dusk-blue, the stars wash out, and **crisp shadows** of the fence,
   shed and trampoline (mat, frame legs, net poles, and the net mesh at 25 %) stretch across the lawn towards us.
5. **"Under those clouds":** the readout swaps to the surface conditions and the tides.
6. White-out, then our Moon again.

**Venus:** no Venus map is in `shorts-common/`, so the disc is a procedural cloud deck (`venus_proc.png`, made once).
It is a creamy white-yellow with very low contrast, with zonal bands, sheared streaks, faint polar collars and a very
subtle dark "Y". It is rendered with `moons.Body` (copied from `../more-moons/`) as a "giant" with Minnaert limb darkening,
a thick limb haze and a lit atmospheric rim (prominent around the crescent). The clouds super-rotate slowly. Its surface
brightness relative to the Moon follows the geometric albedos (0.69 vs 0.12), so it reads as blazing white.

**Shadows:** a per-pixel ground projection with the yard photo's own perspective (f ≈ 771 px, eye-level horizon at
y = 1590). Each caster pixel is lifted off its ground line by its height and thrown along the ground away from the light
(elevation 35°, azimuth 6° left), then projected back. The penumbra is narrow because a 1.8° source gives ~3 cm of blur
per metre. The shadows only fall on the lawn (a green mask that excludes the patio, pot and chair).

## Narration (75 words)
Voice: Kokoro 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per phrase.
> What if Venus... were our Moon? / Here's our Moon... small and quiet. / Now... Venus. / Three and a half times wider. /
> Its thin crescent... already outshines the full Moon. / At half... twenty times brighter. / And when it's full... /
> the light of seventy full Moons. / Night looks like dusk... with crisp shadows. / But under those clouds... a world hot
> enough to melt lead. / And its tides... would swamp our coasts. / Maybe one small Moon... / is just perfect.

## Sound (BATCH4 clean rules)
`lib/mix_clean` only (`clean_voice`, then `mix` with the soft pad and the gentle whoosh at each swap), through
`lib/b4_kit.make_mix`. Nothing else is added.

## Science (`short.py info` prints all of it)
- **Size:** 2·atan(6,051.8 / 384,400) = **1.80°** (verified), against the Moon's 0.52°: **3.48×** wider and 12× the area.
- **Brightness:** the Mallama (2006) Venus phase curve, V(1,α) = −4.384 − 1.044×10⁻³α + 3.687×10⁻⁴α² − 2.814×10⁻⁶α³ +
  8.938×10⁻⁹α⁴, placed at 384,400 km from us and 1 au from the Sun. That gives V = −17.33 at full, against −12.74 for the
  full Moon, so **~69×** ("seventy full Moons"). Half (α = 90°) gives −15.9, **~19×** ("twenty times brighter"). The
  crescent (α = 120°) gives −15.2, **~9×**, so "outshines the full Moon". The reasons are its size (12× the area) and its
  cloud albedo (geometric 0.69 against the Moon's 0.12; Bond 0.76, hence "reflects 76 %").
- **Light:** a full Moon gives ~0.25 lux, so full Venus gives **~17 lux**. That is roughly the light partway through civil
  twilight (civil twilight ends near 3.4 lux), hence "like dusk".
- **Surface:** ~465 °C (lead melts at 327 °C) and **92× Earth's air pressure**, under sulfuric-acid clouds.
- **Tides:** at the same distance, the tidal acceleration scales with mass. M♀/M☾ = 4.87×10²⁴ / 7.34×10²² = **66×**.
- **Not in the script, but true:** Venus is 82 % of Earth's mass, so the pair would be a double planet. Their barycentre
  would be 172,600 km from Earth's centre, outside Earth, and the orbit would take ~20.4 days instead of 27.3.

## Liberties (not captioned, per the user rule)
- The discs use a telephoto scale (f = 9,000 px) over a wide-angle yard. The relative sizes are exact.
- The shadow geometry assumes the light at 35° elevation (the telephoto framing compresses where the disc appears).
- The screen brightness of the sky and yard is compressed (6×–69× cannot be shown linearly on a phone screen). The string
  lights stay on.
- Phases change at the swaps. A real phase cycle would take ~20 days.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`, `short.py` (`info`, `stills`, `segs`), `moons.py` (copied
  unchanged from `../more-moons/`), `encode.py`, `thumbnail.py`.
- Scratch: `.../scratchpad/series/B4-venus-as-moon/`. Outputs (`out/`, git-ignored): `venus-as-moon-short.mp4`,
  `venus-as-moon.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
- Sources: the Moon is Solar System Scope `8k_moon` (CC BY 4.0). Venus is procedural. The foreground is the user's photo.
