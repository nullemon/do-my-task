# What Eclipses Look Like on Other Worlds (YouTube Short, batch 3)

This Short is 9:16 only: 1080×1920 at 30 fps, 44.83 s long. It uses the swap format: one locked tripod shot of the user's
`05_tropical_beach.png` (941×1672 RGBA with a transparent sky, upscaled to 1080×1920). The beach is the stage ("if you stood
here"). The Sun is eclipsed by a different body on each world, with a flash, a chromatic shockwave and coloured beams at
every swap. The beach is relit each time, and the turquoise shallows reflect the sky. Readouts are big and bold, and the
orange captions show one word at a time. There is no disclaimer small print. A white-out at the end returns to the sunny
beach, so the Short loops.

## Narration (REDO v3 storytelling voice, 72 words)
Voice: Kokoro 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per phrase (`lib/v3_redo_q5.py`). Pauses are
0.40–0.50 s between phrases and 1.05–1.15 s before each reveal. The audio uses the v3 post chain, then a low-pass at
17 kHz before AAC. The mix is −14 LUFS and −1 dBTP or lower, measured on the final mp4.

> Imagine standing here... / watching the Sun go dark. / On Earth... the Moon slides in. / A perfect fit. /
> On Mars... Phobos. / Too small to cover the Sun... / just a bite. / From the Moon... / Earth blocks the Sun. /
> Its edge glows red... / every sunrise and sunset, at once. / From Io... / Jupiter swallows the Sun whole. /
> And behind Saturn... / the rings light up. / That tiny dot? / That's us. / Somewhere in that dot... / is this beach.

## Beats and true sizes
One lens is used for every world: f = 2700 px, about a 39° vertical field of view. Every disc is at its true angular
size as seen from that world, so the sizes can be compared both within a beat and across beats (`short.py info`).

| beat | eclipser | Sun | readout |
|---|---|---|---|
| Earth | Moon 0.55° (near perigee; the range is 0.49–0.56°) | 0.533° | FROM EARTH · MOON 0.55° · SUN 0.53° · TOTALITY: UP TO 7½ MINUTES |
| Mars | Phobos 27×22 km from ~6,000 km ≈ 0.26°×0.21° | 0.533/1.524 = 0.35° | PHOBOS ~0.2° · SUN 0.35° · TRANSIT: UNDER A MINUTE |
| the Moon | Earth 2·asin(6371/382,663) = 1.91° | 0.53° | EARTH 1.9° · SUN 0.53° · TOTALITY CAN LAST HOURS |
| Io | Jupiter 2·asin(71,492/419,878) = 19.6° (equatorial; polar 18.3°) | 0.533/5.204 = 0.10° | JUPITER 19.6° · SUN 0.10° · AN ECLIPSE EVERY 42 HOURS |
| Saturn | Saturn 5.76° from 1.2 million km; A ring 13° across; E ring ~40° | 0.056° (hidden) | CASSINI · 19 JULY 2013 · EARTH: 1.44 BILLION KM AWAY |

### Science checks
- **Earth:** a total eclipse needs the Moon's apparent size to be at least the Sun's. The longest possible totality is
  7 min 32 s. The corona, the pink prominences and the diamond ring at second contact are drawn. The sky goes
  twilight-blue, with a 360° sunset-coloured glow on the horizon.
- **Mars:** Phobos (mean radius 11.1 km, orbit 9,376 km, altitude ~6,000 km) can never cover the 0.35° Sun. Its transits
  are annular "bites" lasting about 30–40 s; Perseverance filmed one on 2 April 2022 that lasted just over 40 s. The
  butterscotch Martian day sky, with a bluish aureole around the Sun, is real. Mars gets 43 % of Earth's sunlight, so
  the beach is shown dimmer and dusty-warm.
- **Moon:** during a total lunar eclipse, an observer on the Moon sees Earth hide the Sun. Sunlight refracted through
  Earth's atmosphere makes a red ring: every sunrise and sunset on Earth at once. Ozone adds a turquoise fringe. Earth's
  umbra is about 2.7 Moon-diameters wide at the Moon's distance, so the whole Moon stays in totality for up to about
  1 h 47 min, and a single point for longer ("hours"). City lights speckle Earth's night side.
- **Io:** Io orbits in Jupiter's equatorial plane every 42.5 h (1.769 d), so its Jupiter-facing side gets an eclipse
  every orbit, lasting about 2 h 15 min (Jupiter's shadow is ~143,000 km wide and Io moves at 17.3 km/s). Io has no
  air, so its sky is dark even in daylight. Jupiter's night side shows lightning (seen by Galileo and Juno) and a faint
  auroral oval.
- **Saturn:** this recreates Cassini's "The Day the Earth Smiled" mosaic (PIA17172), taken 19 July 2013 from about
  1.2 million km from Saturn, with Earth 1.44 billion km away. The Sun is behind Saturn, so the globe is a dark
  silhouette with a thin, bright atmospheric limb. Rings in forward scattering use the real radial profile:
  brightness ∝ τ·e^(−2.3τ), so the dense B ring stays dark while the C ring, the Cassini division, the A ring and the
  dusty F and G rings glow. The E ring is a broad blue haze peaking at Enceladus's orbit (238,000 km). The near rings in
  front of the globe lie in its shadow; Saturn-shine lights them faintly. Earth is a single pale-blue point.

## Liberties (deliberately not captioned, per the user)
- One locked telephoto lens (true relative sizes). The beams, flashes, shockwaves and pointer brackets are artistic devices.
- The time scales are compressed: the Moon slides into totality in about 2 s, Phobos crosses in about 3 s, and the
  Sun slips behind Jupiter in about 2 s.
- Airless worlds (the Moon, Io, space near Saturn) get a deep navy, star-filled sky instead of pure black (user rule:
  the sky is never pitch black). The beach's light is eye-adapted, so dark beats stay readable.
- Saturn's ring opening angle (17°) and the sky positions are stylised. Jupiter's ring of scattered light and its
  colour are a plausible rendering, not a measured one.
- The water reflection is a mirrored sky render with slight ripple, softened and Fresnel-weighted (calm, no waves).

## Sources
Textures: Solar System Scope `8k_jupiter`, `8k_saturn` and `8k_saturn_ring_alpha` (CC BY 4.0) from `shorts-common/dl/sss/`,
and threex.planets `earthspec1k` (a land mask for the city lights). The foreground is the user's `05_tropical_beach.png`.
The facts come from NASA/JPL fact sheets: NASA PIA17171/PIA17172 (Cassini, 2013) and NASA's Perseverance Phobos-transit release (April 2022).

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `short.py` (picture; `info`, stills,
  `segs`), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/B3-eclipses-other-worlds/`.
- Outputs (git-ignored): `out/eclipses-other-worlds-short.mp4`, `out/eclipses-other-worlds.srt`, `out/thumb-vertical.jpg`,
  `out/thumb.jpg`.
