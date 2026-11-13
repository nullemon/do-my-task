# What If Strange Exoplanets Replaced Our Moon? (YouTube Short)

This is a 9:16 Short only: 1080×1920, 30 fps, 39.46 s. It uses the format of `other-suns/` and `planets-as-moon/`:
one locked tripod shot of the user's `B_valley.png` (transparent sky) at blue hour. Here the objects sit **low over
the ridge**, so the far hills, ridge and pines cut the lower edge of every giant, like a moonrise. The sky swaps from
our Moon to five famous exoplanets, each placed at the Moon's distance. Every swap has a flash, a chromatic shockwave
and coloured beams, and the valley is relit by each planet's light. One big orange word is shown at a time, at about
50 % height, synced to the voice. The readout sits at the top of the sky: NAME, × MOON'S SIZE and one weird fact.
There are no disclaimer captions (user rule).

## Narration (93 words, Kokoro am_michael @ 1.05, −14 LUFS)
> What if the strangest planets ever found replaced our Moon? Same distance, true size. Here's our Moon. Fifty-five
> Cancri e. Seven times wider, likely a glowing ocean of lava. HD 189733 b. Forty-seven times wider. Cobalt blue, and
> it rains glass, sideways. WASP-12 b. Stretched into an egg, as its star slowly eats it. TrES-2 b. Darker than coal.
> A giant shadow, blotting out stars. KELT-9 b. The hottest planet known. Forty-three hundred degrees, hotter than
> most stars. Our Moon? Kind of boring. Thankfully.

## Beats (`short.py`)
Every body is placed at d = 384,400 km and drawn at θ = 2·asin(R/d). The lens has f = 1400 px, the same as
planets-as-moon, and the apparent radius is f·tan(asin(R/d)).

| body | R used | × Moon | θ | radius on screen | readout fact | look |
|---|---|---|---|---|---|---|
| Moon | 1,737.4 km | 1 | 0.52° | 6.3 px | 0.52° WIDE | real map (SSS 8k), small halo so the disc itself reads |
| 55 Cancri e | 1.88 R⊕ = 11,980 km | 6.9 | 3.57° | 44 px | LAVA-OCEAN WORLD | dark crust cut by glowing Voronoi plate cracks, molten seas, glowing night side, rising sparks |
| HD 189733 b | 1.138 R_J = 81,360 km | 46.8 | 24.4° | 303 px | IT RAINS GLASS | cobalt bands of varied width, Kelvin–Helmholtz roll-ups on band edges, oval vortices, limb haze, fast drifting glass-rain glints |
| WASP-12 b | 1.937 R_J = 138,480 km | 79.7 | 42.2° | 541 px (long axis ×1.24) | BEING EATEN BY ITS STAR | egg shape tapered to the L1 tip; hot orange bands as thermal glow, hottest towards the tip; particle gas stream flowing off the tip |
| TrES-2 b | 1.2 R_J = 85,790 km | 49.4 | 25.8° | 320 px | DARKER THAN COAL | near-black disc (albedo ~1 %), thin crescent, faint dull-red thermal glow and red limb; drifts slowly so stars wink out at its edge |
| KELT-9 b | 1.891 R_J = 135,190 km | 77.8 | 41.2° | 526 px | 4,300 °C | rises from behind the ridge like a sunrise; incandescent granulation (4,600 K ± blackbody LUT), red limb darkening, heavy bloom, golden "dawn" sky, valley lit warm, heat shimmer |

On "Our Moon?" a white-out returns to the opening Moon, so the Short loops.

## Science notes (checked)
- **55 Cancri e:** R ≈ 1.88 R⊕ (NASA Exoplanet Archive default; other solutions give 1.9–1.95). Its day side is
  hot enough to melt rock. Spitzer gave ~2,700 K at the hottest point, and JWST (Hu et al. 2024) suggests a
  volatile-rich atmosphere over a magma ocean with a ~1,800 K day side. Hence "likely a glowing ocean of lava", with
  no °C figure on screen.
- **HD 189733 b:** R ≈ 1.14 R_J. Its deep blue colour was measured by Hubble (Evans et al. 2013, geometric albedo
  ≈0.4 in blue). Silicate (glass) particles are thought to rain out sideways in winds of ~7,000–8,700 km/h
  (Louden & Wheatley 2015 measured ~2 km/s). The wind number was cut from the voice for time.
- **WASP-12 b:** R ≈ 1.9 R_J. It is tidally distorted into a prolate, "egg" shape and loses mass through L1 towards
  its star (Li et al. 2010; Hubble/COS escaping-gas detections). Its orbit is decaying (Yee et al. 2020), so "its
  star slowly eats it". It is also one of the darkest hot Jupiters measured (Bell et al. 2017).
- **TrES-2 b (Kepler-1b):** R ≈ 1.17–1.25 R_J; 1.2 is used. Kepler showed it reflects less than 1 % of the light
  that hits it (Kipping & Spiegel 2011): "darker than coal". Its faint red glow is real, from its ~1,500 K
  temperature.
- **KELT-9 b:** R ≈ 1.89 R_J. Its day side is ~4,600 K ≈ 4,300 °C (Gaudi et al. 2017), the hottest known planet.
  Most stars are red dwarfs (< ~4,000 K), so "hotter than most stars" holds.
- **× Moon** = R/R_Moon, rounded: 7, 47, 80, 49, 78.

## Liberties (deliberately not captioned, per the user)
- Nobody has resolved these worlds, so all surfaces are procedural, following what is known (`exoplanets.py`).
- Phase lighting comes from our Sun below the horizon (TrES-2 b is shown as a crescent so it reads as a black disc).
  Each planet's own thermal glow is shown as if its hot day side faced us. WASP-12 b's gas stream points to an
  off-screen star.
- Brightness is compressed. At this size, KELT-9 b would deliver on the order of a thousand Suns' worth of light and
  sterilise Earth, and HD 189733 b would be thousands of times brighter than the full Moon. The gas giants would also
  be far inside the Earth–planet Roche limits. "Thankfully" covers this.
- Beams, shockwaves, swap animations, the sped-up rotation and the glass-rain glints are artistic devices.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `exoplanets.py` (lit + emissive
  sphere renderer, copied from `../planets-as-moon/planets.py` and extended with procedural maps, emission, per-body
  sun, egg shape), `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no `-shortest`),
  `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/B2-exoplanet-moons/`.
- Outputs: `out/` (git-ignored): `exoplanet-moons-short.mp4`, `exoplanet-moons.srt`, `thumb-vertical.jpg`,
  `thumb.jpg` (1280×720).

## Sources
- Moon map: Solar System Scope `8k_moon` (CC BY 4.0, from NASA data), in `shorts-common/dl/sss/`.
- Planet parameters: NASA Exoplanet Archive values and the papers cited above.
- Foreground: the user's `B_valley.png`.
