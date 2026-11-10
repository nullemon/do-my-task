# What If Planets Replaced Our Moon? (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 35.0 s long. There is also a 16:9 recomposition at 1920×1080. The Short
uses the format of `other-suns/`: one locked tripod shot of the user's `B_valley.png` (transparent sky), here at blue
hour. The sky swaps from our Moon to one planet after another, each placed at the Moon's distance. Every swap has a
flash, a chromatic shockwave and coloured planet-shine beams, and the valley is relit by each planet. One big orange
word is shown at a time, synced to the voice. A readout appears for each planet: NAME, × MOON'S SIZE and the
angular width in degrees. There are no disclaimer captions (user rule).

## Narration (85 words, Kokoro am_michael @ 1.05)
> What if planets replaced our Moon? Same distance, true size. Here's our Moon, for scale. Mars. Twice as wide, a
> rusty red lantern. Neptune. Fourteen times wider, a deep blue world. Uranus, tipped on its side, wearing faint
> rings. Saturn. Its rings stretch forty degrees across the sky. And Jupiter. Forty-one times wider than the Moon,
> bright enough to light the whole valley, with its own moons beside it. Of course, Jupiter would tear Earth apart.
> But what a view. Suddenly, our Moon seems... cosy.

## Beats (`short.py`)
Every body is placed at d = 384,400 km and drawn at its true angular size, θ = 2·asin(R/d). The lens has
f = 1400 px, a 69° vertical field of view on the 1920 px frame. The 16:9 cut keeps the same pixel scale. The apparent
radius is f·tan(asin(R/d)), and the rings' radius is f·r/d.

| body | R (km) | × Moon | angular width | radius on screen | look |
|---|---|---|---|---|---|
| Moon | 1,737.4 | 1 | 0.52° | 6.3 px | silver disc showing its maria, iridescent corona, faint rays, cool blue-hour valley |
| Mars | 3,389.5 | 1.95 | 1.01° | 12.3 px | red gibbous disc, red corona, rusty sky tint |
| Neptune | 24,764 | 14.3 | 7.39° | 90 px | deep blue, Great Dark Spot, blue limb haze, blue valley light |
| Uranus | 25,559 | 14.7 | 7.62° | 93 px | pale cyan, pole tipped towards the Sun, the ten narrow rings (6 … ε) at their real radii |
| Saturn | 60,268 (oblate 0.902) | 34.7 | 18.0° (rings 40.2°) | 222 px, rings 513 px | real ring radial profile, transparent; shadow of the globe on the rings and of the rings on the globe; golden light |
| Jupiter | 71,492 (oblate 0.935) | 41.1 | 21.4° | 265 px | rises diagonally over the ridge, reddened by extinction; bands shear (zonal winds); Great Red Spot; Io, Europa, Ganymede and Callisto along its equator; the valley turns golden |

Phase lighting comes from the Sun, which is below the horizon behind the camera (a 14° phase angle, so the discs are
nearly full with a soft terminator and a faint night side). The Moon and Mars use Lommel–Seeliger shading. The giants
use Minnaert limb darkening plus limb haze and a thin lit atmospheric rim. Atmospheric extinction near the horizon
uses the Kasten–Young airmass with τ = (0.06, 0.09, 0.17) for R, G and B. The sky is a blue-hour sky: the Belt of
Venus, the Earth's-shadow band, twinkling stars (`lib.sky.StarSky`) that fade as the planet-shine brightens the sky,
and a planet-coloured aureole. Discs are rendered at 2× supersampling. Their maps are pre-filtered to the on-screen
scale, so no textures are upscaled, and a fine procedural detail layer is added on top.

The swaps follow `other-suns`: the old body swells, then implodes. Then come a tinted flash, a chromatic shockwave
ring, a whoosh and a boom, and the new body blooms in with an overshoot. On "tear Earth apart", the ground trembles
(a local warp; the camera stays locked), dust rises and the sky flushes red. On "Suddenly", a white-out returns to
our little Moon, so the Short loops.

## Science notes
- **Radii:** IAU/NASA fact-sheet equatorial radii. Angular widths use θ = 2·asin(R/d).
- **Correction to the brief:** Neptune is **7.4°** wide and Uranus **7.6°**. The brief's 3.7° and 3.8° are the
  half-angles.
- **Saturn's rings:** the 8192 px radial profile is calibrated on the inner edge of the C ring (74,658 km) and the
  outer edge of the A ring (136,775 km). The texture ends at about 140,900 km, near the F ring (140,180 km), which
  gives 2·atan(140,180/384,400) ≈ 40°. The ring opening angle is 24°.
- **Jupiter's moons:** Earth at 384,400 km would sit *inside* Io's orbit (421,700 km). The four moons are shown as
  small discs a few px across, at plausible separations (13–28° from Jupiter) and distances (0.8–2 million km). The
  exact geometry is approximate.
- **Tides:** at 384,400 km, Earth would be well inside Jupiter's Roche limit for a fluid body (≈ 2.44·R_J·(ρ_J/ρ_E)^⅓
  ≈ 120,000 km for the Jupiter–Earth pair, and roughly the same order for the others with Earth as the satellite).
  The Earth–Jupiter tidal stresses would be enormous, and Earth's orbit around the Sun would be dominated by Jupiter.
  The narration covers this in one line: "Of course, Jupiter would tear Earth apart."
- **Brightness:** Jupiter would have about 1,700 times the Moon's disc area and roughly 4 times its albedo, about
  7,000 times full-moon light. That is overcast-daylight levels, so the valley is lit golden.

## Liberties (deliberately not captioned, per the user)
- The beams, corona rings, shockwaves and swap animations are artistic devices.
- Rotation and zonal winds are sped up so the discs visibly move. Jupiter's rise is time-compressed (a few seconds),
  and the moons drift.
- Uranus's rings are almost black in reality (albedo about 0.02). They are drawn as faint grey-blue lines and widened
  to at least about half a pixel so they show.
- The valley survives everything.

## Sources
- Planet and Moon maps: Solar System Scope textures (CC BY 4.0, based on NASA mission data). The files are
  `8k_moon`, `8k_mars`, `8k_jupiter` (4096×2048), `8k_saturn` (4096×2048), `8k_saturn_ring_alpha` (8192×500),
  `2k_uranus` and `2k_neptune`. They were fetched from the GitHub LFS mirror `computationalcore/worldline-kinematics`
  (`apps/web/public/textures`) into `shorts-common/dl/sss/`. jeromeetienne/threex.planets (1k maps, already cached)
  was checked, but its maps are too small for these disc sizes.
- Foreground: the user's `B_valley.png`.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `planets.py` (lit sphere / ring
  renderer), `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no `-shortest`),
  `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/S11-planets-as-moon/`.
- Outputs: `out/` (git-ignored): `planets-as-moon-short.mp4`, `planets-as-moon-16x9.mp4`, `planets-as-moon.srt`,
  `thumb.jpg`, `thumb-vertical.jpg`.
