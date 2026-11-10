# What If Earth Had Rings Like Saturn? (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 33.0 s long. There is also a 16:9 recomposition at 1920×1080. It uses one
locked tripod shot of the user's `B_valley.png` (transparent sky) and the `other-suns/` look: swap flashes, chromatic
shockwaves, chromatic bloom and a bold readout per beat. One big orange word is shown at a time, synced to the voice.
There are no disclaimer captions (user rule).

## Narration (86 words, Kokoro am_michael @ 1.05)
> What if Earth had rings like Saturn? From New York, a vast arch of ice would span the whole southern sky, striping
> the land with its shadows. At night, they'd outshine the full Moon, except where Earth's own shadow slices right
> through them. At the equator, they'd shrink to a razor-thin line, straight overhead, from horizon to horizon. Up in
> Oslo, they'd sink into a giant glowing wall along the horizon. And Earth may really have had rings once, about
> 466 million years ago.

## Beats (`short.py`)
| beat | latitude / time | sky | readout |
|---|---|---|---|
| hook | 41° N, winter golden hour | no rings → FLASH on "rings": the rings unfurl outward from the inner edge, with a hot leading edge | — |
| ny | 41° N, sun 4–9° up in the ESE (δ −8.5°) | arch peaking ~39° (dense rings), faint halo to ~46°; we see the UNLIT face, glowing gold by forward scattering; the far ridges sit in the A-ring shadow and shadow bands sweep over the land | NEW YORK · 41° N |
| night | 41° N, before midnight (δ +20°) | lit face, silver ring-lit valley, Earth's shadow cuts a dark wedge that drifts across the arch (time-lapse), red refracted-light fringe at its edge, stars, meteors | NEW YORK · MIDNIGHT |
| eq | 0.05° N, noon (δ +6°), lens facing EAST | the ring plane edge-on: a razor line from the horizon straight up through the zenith; a shadow band sweeps over the land | EQUATOR · 0° |
| oslo | 60° N, midsummer night (sun 4–6° below) | low band peaking ~17°, lower part in Earth's shadow, pastel sky | OSLO · 60° N |
| end | flash → ringless golden sky (same as frame 0), a ghost of the Ordovician ring fades in and out | — |

## Geometry and rendering (`rings.py`)
- Earth frame: z = axis, observer at O = R⊕(cos φ, 0, sin φ). The ring plane is z = 0, the celestial equator. Every
  sky pixel's ray is intersected with that plane (r = |O + s·d|), so the arch, its curvature, the altitude of each ring
  and its foreshortening are all physically projected. Only ring radii r > R⊕/cos φ rise above the horizon in the
  south (8,440 km at 41°, 12,740 km at 60°).
- Sky lens: a locked cylindrical (azimuth, altitude) mapping behind the plate's alpha: ±72° × 0–93° (9:16) and
  ±85° × 0–62° (16:9). It is an ultra-wide panorama in which the celestial equator becomes a true arch rising from both
  lower corners. The plate itself is not warped.
- Ring set (radii from Earth's centre): D 6,700–7,000 km (faint); C 7,000–9,500; B 9,500–19,000; Cassini division
  19,000–21,500; A 21,500–28,000; F ~29,300; G ~33,500 (faint); a diffuse E-like halo to 80,000 km. The C/B/Cassini/A/F
  structure is the real Saturn radial profile (Solar System Scope 8k ring texture, the same calibration as
  `planets-as-moon/planets.py`), re-mapped piecewise onto these radii. Opacity α → normal optical depth τ = −ln(1−α), plus
  1-D noise for fine ringlets. The profile is mip-filtered to each pixel's radial footprint, so there is no moiré.
- Meridian altitudes: at 41° N, B inner 7°, B outer 33°, A outer 39°, halo 46° (→ 49°, the celestial equator, as
  r → ∞). At 60° N, A outer 17.5°, halo 26°.
- Photometry: single scattering (lit face), diffuse transmission (unlit face), Henyey–Greenstein phase (back-scattering
  ice and forward-scattering dust), atmospheric extinction (Kasten–Young airmass; reddens the rings near the horizon),
  Earth's shadow cylinder with a penumbra. The rings block stars but not the airlight in front of them.
- Ground: the ring shadow is computed by tracing the sun ray from the site through the ring plane (r ≈ 29–30k km in the
  NY beat, at the A/F edge). The landscape's depth is mapped onto a few thousand km of ring radius so the bands are visible.

## Science notes and sources
- **Roche limit:** for a rigid icy body the Roche limit is about 1.26 R⊕ (ρ⊕/ρ_ice)^⅓ ≈ 14,500 km, and for a fluid one
  about 2.44 R⊕ (ρ⊕/ρ_ice)^⅓ ≈ 28,000 km (ρ_ice ≈ 0.93). For rock (~3.3 g/cm³) the rigid value is ≈ 9,500 km, the
  brief's figure. The dense rings here end at 28,000 km (the fluid ice limit). Beyond that only thin dust is shown, like
  Saturn's own faint G and E rings, which extend to ~8 Saturn radii.
- **Ringlight:** with Saturn-like reflectivity (B-ring I/F ≈ 0.45), the illuminance from the lit rings at 41° N comes
  out at roughly 5,000–25,000 full Moons (a few thousand lux, deep-twilight to overcast-day levels) depending on season
  and how much lies in Earth's shadow. The readout says "≈ 1,000s × full Moon".
- **Seasons:** in winter the Sun is south of the ring plane, so the northern hemisphere sees the dark, unlit face and
  lies in the rings' shadow. In summer it sees the lit face.
- **Ordovician ring:** Tomkins, Martin & Cawood (2024), "Evidence suggesting that Earth had a ring in the Ordovician",
  *Earth and Planetary Science Letters* 646, 118991, doi:10.1016/j.epsl.2024.118991. 21 impact craters from the
  Ordovician impact spike lie close to the equator of that time. They propose a debris ring from the tidal break-up of
  a large asteroid at ~466 Ma. It is a hypothesis, debated, hence "may".
- Ring texture: Solar System Scope `8k_saturn_ring_alpha` (CC BY 4.0), cached in `shorts-common/dl/sss/`.

## Liberties (deliberately not captioned, per the user)
- The unlit face's diffuse glow and the faint-ring optical depths are boosted so the arch reads in daylight. Ring
  colours are warmed per beat (gold at golden hour, silver at night, pink at Oslo).
- Time-lapse: the Sun's hour angle advances within each beat (the shadow wedge drifts, bands sweep). The ground-shadow
  band scale is exaggerated.
- Exactly at the equator the ground is never in ring shadow. The sweeping band in the equator beat stands for the
  shadow of the ring edge crossing the tropics around the equinox. Seasons differ between beats (winter golden hour,
  summer night).
- The flashes, shockwaves, unfurling reveal, spokes, glints and meteors are artistic devices.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `rings.py` (geometry, profile,
  photometry), `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/S7-earth-rings/`.
- Outputs: `out/` (git-ignored): `earth-rings-short.mp4`, `earth-rings-16x9.mp4`, `earth-rings.srt`, `thumb.jpg`,
  `thumb-vertical.jpg`.
