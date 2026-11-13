# What If Black Holes Replaced Our Sun? (YouTube Short, 9:16 only)

The cut is 1080×1920 at 30 fps and 39.70 s long (ffprobe). It uses the `other-suns/` swap format: one **locked** tripod shot
of the user's `A_park.png`, which starts in daytime. The sky swaps from the Sun to five black holes, and each swap has
a flash, a chromatic shockwave, light beams and a relit park. One big orange word is shown at a time, synced to the
voice. Each object gets a readout: NAME / × SUN'S MASS / HORIZON radius, plus an optional fact line. The ending is a
white-out back to the Sun, so the Short loops. There are no disclaimer captions (user rule). There is no 16:9 video.
`out/thumb.jpg` (1280×720) is a separate 16:9 render for the channel page, made with a wider lens (f = 600 px) so the
whole TON 618 shadow fits.

## Narration (92 words, Kokoro am_michael @ 1.05, −14 LUFS / −1 dBTP)
> What if black holes replaced our Sun? Let's start small. One Sun of mass, six kilometers wide. Same gravity, same
> orbit. But it's dark forever. Cygnus X-1, twenty-one Suns. Earth's year would last weeks. Sagittarius A*. Four
> million Suns. Its shadow spans twenty-four degrees. M87*. Six and a half billion Suns. Its horizon is four times past
> Neptune. We're inside. And TON 618? Up to sixty-six billion Suns. It would swallow our solar system, so here it is
> eight thousand times farther. Suddenly, the Sun seems… kind.

## Beats and numbers
Constants: Rs = 2GM/c² = 2.953 km per solar mass (GM☉ = 1.32712×10²⁰ m³ s⁻²), 1 au = 1.495979×10⁸ km. The camera is
a gnomonic lens with f = 960 px (90° vertical field of view). The hole sits at pixel (540, 600).

| object | mass (M☉) | Rs | at 1 au | on screen | readout |
|---|---|---|---|---|---|
| Sun | 1 | (no horizon) | 0.53° disc | 4.4 px + glow, rainbow beams | NO HORIZON · 1.4 MILLION KM WIDE |
| Sun-mass hole | 1 | 2.95 km (5.9 km across, "six kilometers wide") | shadow 0.021″; Einstein ring θE = √(2Rs/1 au) = 41″ radius, so 1.4′ across | invisible (0.4 px), so a pointer ring marks it: "LENSING RING · 1.4′ WIDE"; dark night sky, lamps on | HORIZON: 3 KM RADIUS |
| Cygnus X-1 | 21.2 ± 2.2 (Miller-Jones et al. 2021, Science 371, 1046) | 62.6 km | shadow 0.25″, θE ≈ 3′ | glowing disk point (a few px), accretion stream from the blue supergiant HDE 226868 (R ≈ 22 R☉, ~31,000 K) drawn at its true 11.9° | 21× / HORIZON: 62 KM RADIUS / 1 YEAR → 11 WEEKS |
| Sgr A* | 4.297×10⁶ (GRAVITY 2022) | 1.269×10⁷ km = 0.0848 au | camera at 11.79 Rs; shadow **24.3°** across | exact Schwarzschild ray trace, EHT-orange ring with Doppler beaming, lensed starfield | 4.3 MILLION × / 12.7 MILLION KM / SHADOW: 24° ACROSS |
| M87* | 6.5×10⁹ (EHT 2019) | 1.92×10¹⁰ km = 128 au | 1 au = 0.0078 Rs, so we are inside the horizon | lensed "tunnel": the outside sky squeezed into a shrinking window, with lensed disk rings | 6.5 BILLION × / 128 AU / WE'RE INSIDE IT |
| TON 618 | 4.07×10¹⁰ to 6.6×10¹⁰ | 803 to 1,303 au | at 1 au we'd be deep inside | first a close-in framing (the shadow overfills the sky), then a pull-back to the view **from 8,000 au** (6.14 Rs for 66 billion M☉): shadow **45.6°** across, Interstellar-style lensed disk | 40–66 BILLION × / 800–1,300 AU RADIUS / SEEN FROM 8,000 AU |

- **Shadow size.** A static observer at radius r sees the shadow edge at sin α = (3√3/2)(Rs/r)·√(1 − Rs/r) (Synge
  1966). For Sgr A* at 1 au: r = 11.79 Rs, α = 12.17°, so the diameter is 24.3°. The flat-space estimate,
  2·atan(2.6 Rs / 1 au) = 24.9°, matches the brief's "roughly 25°". The narration says "twenty-four degrees".
- **Sun-mass hole.** Same mass, so by Birkhoff's theorem the same gravity at 1 au and the same orbit and year. There is
  no light source, so the sky is dark: "dark forever".
- **Cygnus X-1: "Earth's year would last weeks."** Around 21.2 M☉, P = 1 yr / √21.2 = 79 days ≈ 11 weeks. If the
  companion's 40.6 M☉ were counted too, the total is 61.8 M☉ and P ≈ 46 days ≈ 7 weeks. Either way it is "weeks".
  The real binary separation is 0.244 au (P = 5.6 d), so from 1 au the companion appears about 14° from the hole. It
  is drawn 13° away at its true 11.9° size.
- **Sgr A*:** the orbit question is not narrated. For the record: a circular orbit at 11.8 Rs is technically stable
  (the ISCO is at 3 Rs), but the year would be 4.2 hours at 0.21 c. Earth is outside its Roche limit (0.60 au) but
  under strong tides. The beat is presented as "the view".
- **M87*:** Rs = 128 au ≈ 4.3 × Neptune's 30 au, hence "four times past Neptune". From r = 1 au, any infall reaches
  the singularity in ≲ 30 s of proper time (τ ≈ (2/3) r^{3/2}/(c√Rs) = 29 s). This is not narrated.
- **TON 618:** mass from Shemmer et al. 2004 (6.6×10¹⁰, Hβ). Lower estimates are about 4×10¹⁰ M☉, hence "up to" and
  the range in the readout. Even the low value gives Rs ≈ 800 au, far beyond the planets, the Kuiper belt and the
  heliopause (~120 au): "it would swallow our solar system". (The Oort cloud extends further.) The view distance of
  8,000 au = 6.14 Rs is chosen so that the shadow spans 45.6°. "Eight thousand times farther" means 8,000 au versus
  the Sun's 1 au. With the 40-billion value, the same view would be from about 4,900 au.

## How the lensing works (`lens.py`)
This extends `../sun-black-hole/short_vfx.py`'s point-lens warp to exact null geodesics in Schwarzschild spacetime.
- Each pixel's angle α from the hole sets the photon's impact parameter, b = r sin α / √(1 − 1/r), with Rs = 1.
- The orbit equation u″ = −u + 1.5u² (u = 1/r) is integrated with RK4, backwards from the camera. This gives 1-D
  tables for the escape direction ("alpha_sky", including the higher-order images) and the orbit u(α, φ).
- The disk is a tilted plane. For each pixel the code finds the plane crossings (k = 0, 1, 2) and the hit radius r.
  This yields the lensed far side arching over and under the shadow, the front band, and the photon-ring copies.
- The Doppler and gravitational shift is g = √(1−1/r_e) / √(1−1/r_o) / (γ(1 − β·k̂)), with the Keplerian speed seen
  by a static observer β = √(1/(2(r−1))).
  - Sgr A* uses an "afmhot" ramp on g^1.6·emission (EHT look).
  - TON 618 colours the disk by temperature × g (blue-white on the approaching side, orange on the receding side) with
    brightness ~g³.
- Stars:
  - The faint stars and the Milky Way come from the shared procedural plate, sampled through the lens as an extended
    source.
  - The 2,600 bright stars are point sources. Each lensed image of order 1–3 is drawn with its magnification
    μ = |sin α / sin β · dα/dβ|.
  - The sky drifts at 1.6°/s, so stars stream through the lens and brighten near the Einstein ring.
- M87* (inside): the camera radius is animated from 1.06 Rs to 1.004 Rs, looking outward. The escape cone shrinks
  from about 36° to 9° (half-angle): the "tunnel".

## Liberties (deliberately not captioned, per the user)
- **The sky is never pitch black.** The shadows show a dim atmospheric glow in front of them, the dark Sun-mass sky
  is a readable deep blue, and the walls inside M87* carry stylised violet swirling streaks and rings outside the
  physically traced window.
- **M87\* inside view:** no observer can hover inside a horizon. The tunnel is the view of a static observer just
  outside it (1.06 → 1.004 Rs), looking out, used as a stand-in for "we're inside". The blueshift and the wall
  streaks are approximate or artistic.
- **TON 618:** during "it would swallow…" the framing is a 1.9× close-in of the 8,000 au view rather than a true inside
  view. On "so here it is" it pulls back to the true 8,000 au framing. The disk is truncated at 4.8 Rs (the camera
  is at 6.14 Rs). Extra glow/halo blur is added for the thick Interstellar look.
- **Cygnus X-1:** the companion would light (and roast) Earth like a supergiant sun, so the sky is shown as a blazing
  blue day. Its tidal stretch, the shape of the stream and the disk glow are drawn by hand rather than simulated; the
  real system is largely wind-fed. The 1-year→11-weeks readout ignores the three-body mess.
- **Sgr A*:** the disk (inner edge 1.6 Rs, inclination 32°) is a stylised hot flow. Sgr A* is really very dim, and the
  EHT's orange is a false-colour radio image. The park's orange relight is artistic.
- Beams, flashes, shockwaves, pulses and the relight strengths are VFX choices.

## Sources
Miller-Jones et al. 2021 (Cyg X-1 mass, companion 40.6 M☉, distance); Orosz et al. 2011 / Miller-Jones 2021
(companion radius ~22 R☉, Teff ~31 kK); GRAVITY Collaboration 2022 (Sgr A* mass 4.297×10⁶ M☉); EHT Collaboration
2019 Paper VI (M87* 6.5×10⁹ M☉) and 2022 (Sgr A* ring); Shemmer et al. 2004 (TON 618); Synge 1966 (shadow formula).

## Files
- `audio/narration.py`, `audio/gen_voice.py` (a copy of the nebula-sky wrapper of `lib.voice`), `audio/mix.py`
  (sound + SRT).
- `lens.py` (Schwarzschild tracer), `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no
  `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/B2-black-hole-suns/`.
- Outputs: `out/` (git-ignored): `black-hole-suns-short.mp4`, `black-hole-suns.srt`, `thumb-vertical.jpg`,
  `thumb.jpg`.
