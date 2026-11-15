# What If a Rogue Planet Passed Earth? (YouTube Short, batch 3)

The cut is vertical only: 1080×1920 at 30 fps. It is one locked tripod shot of the user's `04_city_street_at_night.png`:
a skyscraper canyon with neon and a wet street, with the sky a narrow strip up the middle. The film uses the swap format.

A dark, Jupiter-mass rogue planet (no star) approaches over the city. It is drawn at its **true angular size** for the
plate's own lens (f ≈ 1150 px, ~80° vertical field of view) at each distance:
1. Beyond Neptune: a 3.9″ invisible dot, shown as a star blinking out.
2. Mars's distance: a 0.14° dark speck that passes over a star.
3. The Moon's distance: a 21° dark disc that blots out the stars.
4. 200,000 km: 42° wide, overflowing behind the buildings. The tides heave, the ground shakes and the city lights
   flicker.
5. The flyby: it slides away up the strip, shrinking at its true size as it recedes.

A white-out then returns to the normal city night, and the end loops back to the opening. A star blinks out once more
on "drifting".

Every swap has a tinted flash, a chromatic shockwave and coloured beams, and the city is relit:
- the planet's red glow on the upper facades and skyline edges;
- lightning flashes washing the street;
- flickering windows and neon, whose wet-street reflections flicker in the same columns.

The wet street mirrors the sky as a streaky rough-specular reflection about eye level (y = 1366), weighted by the
plate's own glossiness and added on top of the plate's real neon reflections. In the close beat, the planet's lower half
and its lightning reflect in the street. Readouts are NAME / size line / fact line. Big orange one-word captions sit at
y = 1150. There is no disclaimer small print.

## Narration (74 words, REDO v3 voice)
Kokoro style 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per phrase (`lib/v3_redo_q5.py`, unchanged).
Pauses are 0.45–0.5 s between phrases and 1.0–1.1 s before reveals. The v3 post chain is pitch-only. The mix goes to
−14 LUFS / −1 dBTP, with a 17 kHz low-pass before AAC.

> What if a rogue planet... passed Earth? / A Jupiter... with no star. / Beyond Neptune... just a star, blinking out. /
> At Mars's distance... a dark speck. / Then... the Moon's distance. / A dark disc... forty Moons wide. / Glowing
> faintly... lightning in its clouds. / Closer... / The tides heave. The ground shakes. / It passes... / but our orbit
> could be thrown off. / The odds are tiny... / but rogue planets may outnumber the stars. / Somewhere out there... one
> is drifting.

## Science (`science.py` prints all of this)
The planet has Jupiter's mass, 1.898 × 10²⁷ kg, and mean radius, 69,911 km. θ = 2·asin(R/d), with d measured from the
observer at 34° elevation.

| beat | distance | angular size | on screen | other numbers |
|---|---|---|---|---|
| beyond Neptune | 50 AU (Neptune is at 30 AU) | 3.9″ | sub-pixel | with a Jupiter-like albedo it would be mag ≈ +7.3 (naked-eye limit ~6); as a young, dark rogue, fainter still |
| Mars's distance | 55.76 million km (Mars at its closest, Aug 2003) | 0.144° (0.28 Moon widths) | r = 1.4 px | |
| the Moon's distance | 384,400 km | **21.2°** (40.8 Moon widths) | r = 215 px | tidal pull 25,850× the Moon's (M_J/M_Moon); its pull on Earth is 145× the Sun's |
| closest | 200,000 km | **41.7°** (80 Moon widths) | r = 438 px | tidal pull 183,600× the Moon's; pull 534× the Sun's |

- **Correction to the brief:** at the Moon's distance a Jupiter-size planet is about **21°** wide (40 Moons across), not
  40°. The ~40° view needs ~200,000 km, which is used for the "Closer" beat. That is still outside Earth's fluid Roche
  limit for this planet (106,000 km).
- **"Lensed stars at its edge":** gravitational lensing is negligible here. The Einstein radius at 384,400 km is 25″, and
  the deflection at the limb is 0.017″. What really bends starlight at a giant planet's edge is its **atmosphere**, as in
  stellar occultations by Jupiter, where star images are refracted along the limb and flash. The Short shows that: the
  stars hidden in a thin annulus behind the limb reappear squeezed into a flickering arc hugging it.
- **Dark, but lit by the Sun and its own heat:**
  - Over a night city, a planet opposite the Sun would be fully lit. Here it is placed ~50° from the Sun (phase angle
    ~140°), so only a thin crescent at its bottom is sunlit.
  - It is modelled as a *young* rogue: hot, nearly cloud-free and very dark (geometric albedo ~0.05, like the darkest hot
    Jupiters).
  - A young Jupiter-mass object (~1–10 Myr old) is still ~500–1,000 K inside, so its night side would glow a faint deep
    red. It is brightest in the belts, where deeper, hotter layers show (as in Jupiter's 5 µm hot spots).
  - An old (billions of years) rogue would be ~100 K and black to the eye. The narration says only "glowing faintly".
- **Lightning:** Galileo, Cassini and Juno saw lightning flashes on Jupiter's night side. Here they are Poisson flashes,
  clustered in the belts, each a few return strokes. The thunder in the mix is a liberty; there is no sound through
  space.
- **Auroral ovals:** Jupiter has the strongest aurorae in the Solar System. Near Earth, a magnetised giant would be
  driven by the solar wind. The ovals are faint and tinted green and red (a liberty: Jupiter's are mostly UV and IR).
- **"Our orbit could be thrown off":**
  - At 200,000 km its pull on Earth is ~530× the Sun's.
  - The impulse estimate 2GM/(b·v) for v ≈ 40 km/s gives a kick of ~32 km/s at 200,000 km and ~16 km/s at the Moon's
    distance. Earth's orbital speed is 29.8 km/s, and solar escape at 1 AU is 42.1 km/s.
  - That is enough to change Earth's orbit drastically, possibly ejecting it. The impulse approximation is only
    indicative at this strength, so the narration hedges with "could".
- **The odds:**
  - Jupiter-mass rogues number fewer than ~0.25 per star (Mróz et al. 2017, OGLE microlensing), about 0.025 per pc³
    locally.
  - A pass within 200,000 km at ~40 km/s, with ~3× focusing by the Sun, happens ~once in 10²¹ years. Even a pass within
    1 AU is ~once in 10¹⁵ years.
  - Counting all masses, microlensing surveys suggest free-floating planets may outnumber stars, roughly 20 per star and
    mostly Earth-mass or smaller (Sumi et al. 2023, MOA). Hence "may outnumber the stars", hedged.
- **Tides and quakes:** a tidal acceleration 10⁴–10⁵ times the Moon's, lasting a few hours, would raise extreme ocean
  surges and solid-Earth stresses. The narration only says "the tides heave, the ground shakes".

## Liberties (not captioned, per the user rule)
- Motion is time-compressed: the approach, flyby and recession take seconds instead of hours to weeks. The planet drifts
  slowly while visible.
- The planet's map is Jupiter's (Solar System Scope 8k), darkened and recoloured for a hot, dark young giant.
- The red glow and the aurorae are brightened for readability. Beams, shockwaves, pointer rings and swap animations are
  artistic devices.
- The quake shakes the frame by a few pixels (the tripod shakes with the ground); otherwise the shot is locked.
- Captions sit at y = 1150, at the end of the street, so the narrow sky strip is free for the planet.

## Sources
- Jupiter map: Solar System Scope `8k_jupiter.jpg` (CC BY 4.0).
- Foreground: the user's `04_city_street_at_night.png`.
- Rogue-planet statistics: Mróz et al. 2017 (Nature 548, 183); Sumi et al. 2023 (AJ 166, 108).
- Jupiter lightning: Galileo / Juno (e.g. Brown et al. 2018, Nature 558, 87).

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`.
- `science.py`, `moons.py` (copied from `../more-moons/moons.py`), `short.py` (`info`, `stills`, `segs`).
- `encode.sh`, `thumbnail.py`. `../lib/` is unchanged.
- Scratch: `.../scratchpad/series/B3-rogue-planet/`.
- Outputs (`out/`, git-ignored): `rogue-planet-short.mp4`, `rogue-planet.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
