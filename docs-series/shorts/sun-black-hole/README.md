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

## Versions
- **B — locked camera (preferred)**: `out/sun-black-hole-short-locked.mp4` (9:16) and `out/sun-black-hole-16x9-locked.mp4`,
  built by `short_locked.py` with the `mix.py locked` audio. One tripod frame for the whole Short. The Sun swells, flickers,
  implodes to a point and flashes. Instant night, and stars fade in over ~1 s. The black hole hangs where the Sun was
  (drawn about 450× larger than real). The real night sky is lensed around it with the exact point-lens map, and as the
  stars drift past they split into image pairs; on "bending" a bright one lines up into a full Einstein ring. Facts sit
  in the lower safe band. Then the frost, the countdown and the temperature counter.
- **A — multi-shot**: `out/sun-black-hole-short.mp4`, built by `short.py`. The park is the anchor, with cut-aways to a
  solar-telescope Sun (granulation, sunspot map, prominences), the implosion, the dark Earth on its unchanged orbit around
  the lensing black hole, a telescope inset, and Earth icing over.
- User rule: no disclaimer captions ("illustration", "enlarged", "time-lapse", "not to scale", "brightened"). Only
  factual text appears on screen.

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
The sky, stars and Milky Way are procedural, not a real star chart. Time is compressed: the clock, the lamps switching
on after dark, a year of frost in about 10 s, and the lensing time-lapse. The camera "adapts" to night in about 2 s,
where real eyes take minutes. The night foreground is a grade of the daylight photo, so faint traces of the daylight
shadows can remain.

## Files
`audio/narration.py` (text and timing markup), `audio/gen_voice.py` (Kokoro with word timings), `audio/mix.py`
(sound + SRT), `short.py` (picture), `encode.sh` (mux), `thumbnail.py`. Shared code: `../lib/` (see its README).
Scratch: `.../scratchpad/series/S1-sun-black-hole/`. Outputs: `out/` (git-ignored).
