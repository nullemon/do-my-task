# What If the Sun Became a Black Hole? (YouTube Short)

1080×1920, 30 fps, ~39.6 s. Format follows the reference "Sun Explosion Simulation" Short: a real-looking ground-level
park plate (the user's `A_park.png`, transparent sky), a replaced and animated sky, a scene grade that follows the sky,
and one big orange word at a time at mid-height, synced to the voice. There is also a 16:9 recomposition.

## Narration (102 words, Kokoro am_michael @ 1.12)
> If the Sun became a black hole right now, you wouldn't notice. For eight minutes and twenty seconds, its last light
> keeps arriving. Then the Sun just… goes out. No sunset. No twilight. The blue sky is scattered sunlight, so day turns
> black, and stars come out at noon. Earth's orbit? Unchanged. Same mass, same gravity. The black hole is only six
> kilometers wide. Through a telescope, you'd see starlight bending around it. Then the cold. In a week, below minus
> eighteen. In a year, minus seventy-three. And Earth keeps orbiting perfectly. A frozen world, circling a hole you
> can't even see.

## Delivered version: stylized VFX, one locked shot (`short_vfx.py`, audio `mix.py vfx`)
After two realistic versions were rejected as too dark and too subtle, the user asked for a reference-style spectacle.
- **0–7.9 s:** six giant chromatic beams (smooth spectral gradients) fan out from the Sun, rotating and flaring over a
  deep-blue sky. A big "T + m:ss" countdown runs.
- **7.9–9.85 s:** the beams twist into an inward spiral and turn hot orange/red/violet. The Sun swells and wobbles, then
  implodes. White flash, a chromatic shockwave ring and a sub-bass hit on "OUT".
- **9.85 s on:** a deep indigo night; the park stays readable and the lamps come on. The black hole grows in to ~45% of
  the frame width: black core, white-violet photon ring, a gold disk band with Doppler beaming, the lensed far side
  arching over and under the core, a violet infalling spiral, and the starfield lensed and swirling around it. It pulses
  and flares on key words.
- **~28 s on:** a feathered blue-white frost wave with sparkles, ground mist, and a big temperature readout.
- **Last ~1.3 s:** the hole flares to a full white-out (loopable).
- Readouts only, with no disclaimer text (user rule): SAME MASS · SAME ORBIT, EVENT HORIZON ≈ 6 KM,
  EINSTEIN RING ≈ 1.4′, the countdown and the temperature counter.
- `short.py` (multi-shot) and `short_locked.py` (realistic locked shot) are kept as code only. Their renders were
  scrapped.

## Science notes and sources
- **Event horizon.** The Schwarzschild radius is r_s = 2GM☉/c² = 2.95 km (GM☉ = 1.327×10²⁰ m³ s⁻², standard), so the
  horizon is 5.9 km across. The narration says "six kilometers wide" and the label says "~6 km across".
- **The orbit is unchanged.** Outside a spherical mass, gravity depends only on the mass (shell theorem / Birkhoff's
  theorem), so 1 au sees the same pull and Earth keeps the same orbit and year. The Sun's share of the tides is also
  unchanged.
- **8 min 20 s.** 1 au / c = 499 s = 8 min 19 s, usually rounded to 8:20. The light already on its way keeps arriving.
  The gravity does not change, so nothing about it arrives.
- **No twilight.** The blue daytime sky is sunlight scattered by air (Rayleigh scattering). Twilight is the same
  scattered light while the Sun is below the horizon. With no sunlight at all, the sky goes dark everywhere at once,
  and the stars are visible "at noon".
- **Invisible black hole, telescope lensing.** Einstein radius for a background star: θ_E = √(2 r_s / 1 au) = 1.99×10⁻⁴
  rad = 41″, so the ring is about 82″ ≈ 1.4′ across. (The brief's "about 40 arcseconds" is the radius.) The "shadow"
  itself is about 0.02″, which is invisible even through a telescope, so no black dot is drawn.
  The inset uses the exact point-lens solution. Each star (a point source) has two images at
  θ± = (u ± √(u²+4))/2 · θ_E with magnifications μ± = (u²+2)/(2u√(u²+4)) ± ½, blurred by 0.9″ seeing.
  Faint background galaxies are extended sources, rendered by inverse ray-shooting (β = θ − θ_E²·θ/|θ|²), and one
  near alignment becomes an arc or ring. The drift is a time-lapse. The real relative motion is about 1°/day
  (≈150″/h), so a ring crossing takes about half an hour.
- **No accretion disk.** Nothing is falling in. The planets keep their orbits, and the solar wind stops along with
  the Sun.
- **Temperatures** (rough published estimates). David Stevenson (Caltech), quoted by Popular Science: the global mean
  surface temperature falls below 0 °F (−18 °C) within about a week and to about −100 °F (−73 °C) within a year. Video
  08 checked these by web search in Nov 2026 (see `../../08-if-the-sun-vanished/README.md`). The on-screen counter
  interpolates between those anchor points in log-time from +15 °C. The same source says the ocean surface freezes
  over while the deep ocean stays liquid for a very long time. That part is not narrated, to keep the Short under 40 s.
- **It cannot happen.** The Sun has far too little mass to collapse into a black hole. It will end as a white dwarf.

## Liberties (deliberately not captioned, per the user)
The VFX version is stylized: the beams, the spiral collapse, the shockwave, the visible accretion disk (a real Sun-mass
hole would have nothing falling in) and the huge apparent size are artistic. The narration's facts stay accurate.

The sky, stars and Milky Way are procedural, not a real star chart. Time is compressed: the clock, the lamps switching
on after dark, a year of frost in about 10 s, and the lensing time-lapse. The camera "adapts" to night in about 2 s,
where real eyes take minutes. The night foreground is a grade of the daylight photo, so faint traces of the daylight
shadows can remain.

## Files
`audio/narration.py` (text and timing markup), `audio/gen_voice.py` (Kokoro with word timings), `audio/mix.py`
(sound + SRT), `short.py` (picture), `encode.sh` (mux), `thumbnail.py`. Shared code: `../lib/` (see its README).
Scratch: `.../scratchpad/series/S1-sun-black-hole/`. Outputs: `out/` (git-ignored).
