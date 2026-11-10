# 13 — SUNSET ON EVERY WORLD

**YouTube title:** What Sunset Looks Like on Every Planet

**YouTube description (2 lines):**
One moment, the Sun touching the horizon, seen through the same lens from Earth, Mars, Mercury, Venus, the cloud tops of Jupiter, Saturn and Uranus, Titan, Pluto and a world with two suns. Every view except Earth's is an artist's reconstruction built from spacecraft measurements; sizes of the Sun are to scale, colours of the giant planets' skies are informed guesses.

A 5:37 narrated documentary (1920×1080 and a recomposed 1080×1920, 24 fps) in the series look. The opening five seconds
deliver the thumbnail: a Martian horizon with the small white Sun inside a cold blue glow and the caption
`MARS SUNSETS ARE BLUE`.

The device that ties the film together: **every world is filmed with the same 24-degree lens** (about an 85 mm lens on
a full-frame camera), so the Sun's disc is drawn at its true relative size everywhere: 43 px across from Earth,
28 px from Mars, 139 px from Mercury at perihelion, 8 px from Jupiter, 4 px from Saturn and Titan, 2 px from Uranus
(drawn at a 3.4 px minimum so it survives video compression), a point from Pluto. A small HUD gives the world's name,
the Sun's apparent size relative to Earth's, the distance in light-time and the length of the day.

By the series rule (10 Nov) there is no disclaimer small print on screen: no "artist's reconstruction", "time-lapse"
or "same lens" lines. What each view is based on, and where it is speeded up, guessed or imagined, is said in the
narration ("Every one of these views is a reconstruction, built from measurements", "from a moon of it, if it has one")
and listed below.

## Files
| file | what |
|---|---|
| `SCRIPT.md` (`make_script_md.py`) | locked narration with measured times and the shot list |
| `timeline.py`, `audio/locked_starts.json` | voice starts (measured Kokoro durations + pauses), shot boundaries, total length |
| `blender/world.py`, `run.sh`, `all_passes.sh` | Blender 5.1.2 (bpy, Cycles CPU): one 2160² telephoto plate per world. Each world has its own numpy height field on a perspective fan grid (uniform in screen angle near the camera, logarithmic and then dense for far ranges), its own rocks as real geometry (convex plane-cut blocks, slabs, rounded pebbles, jointed sea stacks; thousands of instances at several scales) and its own albedo. Rendered as separable passes: white-material beauty with the Sun, a wide horizon glow and the sky dome in the R, G and B channels (64 or 48 spp + OIDN), albedo, normal, log depth + material flag |
| `lib.py` | numpy/OpenCV library, linear HDR: plate loader with per-pixel elevation / azimuth, limb-darkened Sun discs, cloud decks in perspective, procedural stars, Saturn's rings projected from a latitude on the cloud tops (C, B, Cassini division, A, Encke gap, F), an analytic sea (four bands of travelling waves, each resolved only where the pixel grid can carry it and counted as roughness elsewhere; Fresnel reflection of the rendered sky bent by the wave slopes; Cox–Munk style glitter path; rock reflections), bloom, tone-map, type |
| `comp.py` | every shot: per-world sky model (functions of direction and of the Sun's elevation), lighting of the plate with that world's Sun colour, haze by distance, HUD, captions, opening montage, recap grid; writes silent x264 CRF 14 segments. `VERT=1` switches to the 9:16 layout |
| `audio/narration.py`, `gen_voice.py`, `mix.py` | text, Kokoro TTS (am_michael, speed 0.94, the series voice), voice chain, numpy music bed (one harmonic colour per world, D major only for Earth), ducking, two-pass loudnorm to −14 LUFS, SRT |
| `render_all.sh`, `encode_one.sh` | 2-worker segment render + concat; final encodes (`hq`, `4k`, `vertical`) with vignette, grain, AAC 256k, soft subtitle track |
| `thumbnail.py` | `out/thumb.jpg` 1280×720 and (`VERT=1`) `out/thumb-vertical.jpg` 1080×1920 |

Rebuild: `gen_voice.py` → `mix.py` (ttsenv) → `bash blender/all_passes.sh <world>` for the ten worlds →
`bash render_all.sh` → `bash encode_one.sh hq|4k` → `VERT=1 bash render_all.sh` → `bash encode_one.sh vertical` →
`python3 thumbnail.py`.

## Facts and sources (checked by web search, Nov 2026)
Only search-result summaries were reachable from this machine (article pages were blocked), so quotes are as reported by
the search tool. Values marked *(computed)* follow from standard orbital elements; values marked *(from memory)* were
not re-confirmed by a search and are standard reference figures.

**Sun's apparent size** *(computed from mean distance; Earth = 0.533°)*: Mercury 0.387 au → 2.6× (0.307 au at perihelion
→ 3.26×, 0.467 au at aphelion → 2.14×); Venus 0.723 au → 1.38×; Mars 1.524 au → 0.66×; Jupiter 5.20 au → 0.19×;
Saturn / Titan 9.58 au → 0.10×; Uranus 19.2 au → 0.052×; Neptune 30.1 au → 0.033×; Pluto 39.5 au → 0.025×.
**Light-time** *(computed, 8.317 min per au)*: 3.2, 6.0, 8.3, 12.7, 43, 80 light-minutes; Uranus 2.7 light-hours (2 h 40 min);
Neptune 4.2 h; Pluto 5.5 h (mean distance; 4.6 h at the 2015 fly-by).

- **Earth.** Rayleigh scattering (∝ λ⁻⁴) — standard physics. The Sun moves 15° per hour, so its 0.53° disc takes
  ≈ 2 min 8 s to cross the horizon at the equator at an equinox, longer at higher latitudes *(computed)*.
- **Mars — blue sunset.** NASA's caption for the 2005 Spirit sunset: the dust "scatters blue light in the forward
  direction, creating a bluish sky glow near the setting sun". Curiosity team member Mark Lemmon (2015): "the very fine
  dust is the right size so that blue light penetrates the atmosphere slightly more efficiently"; the blue stays closer
  to the Sun's direction than other colours. (cbsnews.com, spaceflightnow.com 2015-05-11, phys.org, livescience.com;
  NASA APOD 2025-06-15 "Two Worlds, One Sun".) One source notes the mechanism is "not fully understood" in detail; the
  film says the grains are "just the right size to scatter blue light forward". Surface pressure ≈ 0.6 % of Earth's
  *(from memory)* → "less than a hundredth". Sol = 24 h 39.6 min *(from memory)*.
- **Mercury.** Solar day ≈ 176 Earth days (twice its 88-day year); rotation 58.65 d in 3:2 resonance. About four days
  before perihelion the orbital angular speed equals the spin rate, the Sun's apparent motion stops and reverses, and
  resumes about four days after perihelion; only observers who are at sunrise or sunset during those days see a double
  sunrise / sunset (Wikipedia "Mercury (planet)" and mirrors). Perihelion 46 million km, aphelion 70 million km (same).
  The film says "from some places"; the shot compresses days into seconds. The sky is black because the exosphere
  is negligible ("almost no air").
- **Venus.** Surface daylight "about as intense as on Earth during an overcast day", hazy, and filtered to orange
  (astrosociety.org "Venus" unit; stardate.org; astronomy.com Sept 2015). Sidereal rotation 243 d, year 225 d, solar
  day ≈ 117 d; retrograde, so "if the Sun could shine through the thick clouds, it would rise in the west" (NASA Space
  Place "All About Venus"; Universe Today). The film says the disc is never seen from the surface and shows a brighter
  patch of cloud only.
- **Jupiter.** 5.2 au → sunlight 1/27 of Earth's *(computed)*. Rotation 9 h 56 min *(from memory)* → 36° per hour, so
  the 0.10° disc crosses a level horizon in ≈ 10 s at the equator, ignoring refraction *(computed; "about ten seconds")*.
- **Saturn.** Rotation ≈ 10 h 33 min *(from memory; Cassini ring-seismology value)*. Ring radii used (Saturn radii):
  C 1.24–1.53, B 1.53–1.95, Cassini division 1.95–2.03, A 2.03–2.27, Encke gap 2.21, F 2.33 *(from memory)*. The view
  arch is projected from 47° north, looking about 70° south of the sunset point, with the Sun 2° north of the ring
  plane, and drawn as a wider-angle view of the sky (5.5× the 24° lens in 16:9, 4× in 9:16) so that it reads as a thin
  bright band arching across the sky and down towards the Sun. **Artistic licence (README only):** from any one spot
  the true ring band and the setting Sun would not both fit inside a 24° frame this way; the earlier physically framed
  version (14° north, same lens) showed the rings as near-vertical streaks and was rejected by the lead.
- **Uranus.** Tilt 97.8°, orbit 84 years, each pole ≈ 42 years of sunlight then 42 of darkness (JPL Night Sky Network;
  Guinness World Records; Britannica; EBSCO). Rotation 17 h 14 min *(from memory)*. *(Computed)* at a pole the Sun's
  elevation changes by at most ≈ 0.02° per day near equinox, so the 0.028° disc itself crosses the horizon in a day or
  two, while twilight (Sun 0–18° below the horizon) lasts 2–3 years. Hence "the tiny disc is gone within a couple of
  days. But the twilight can linger for years" — not "a sunset that takes years".
- **Neptune** (spoken and captioned, no separate vista): 30.1 au → 1/30 the width, ≈ 4.2 light-hours *(computed)*.
- **Titan.** Tomasko's Nature commentary on Huygens (as summarised by ESA "First view of Titan" and free-astro.org):
  surface illumination "about a thousand times dimmer than full solar illumination on the Earth" (≈ Earth 10 minutes
  after sunset); the sky is orange "due to the much greater attenuation of blue light by Titan's haze relative to red
  light"; with the Sun high it is "a small, bright spot, ten times smaller than the solar disk seen from Earth".
  Synchronous rotation, 15.95 Earth days. Huygens landed 14 January 2005 on a pebbly, damp surface near the equator
  (NASA "Huygens landing site"); the pebbles being water ice is the standard interpretation *(from memory)*. The seas
  (Kraken, Ligeia, Punga Mare) are near the north pole, so the shot combines a Huygens-like pebble field with a sea
  shore; Cassini radar found Ligeia Mare flat to about a millimetre *(from memory, Zebker et al. 2014)*, hence the
  nearly still surface. The film says the Sun "never shows a clean edge" at sunset (long slant path through the haze).
- **Pluto.** "Pluto Time" (NASA / New Horizons, 2015; space.com, Sky & Telescope, EarthSky): noon on Pluto matches
  Earth's light when the Sun is ≈ 1.5° below the horizon, 8–10 minutes after sunset; sunlight ≈ 1/1000 (1/1560 at
  39.5 au) of Earth's. The Sun from Pluto ≈ 250× the full Moon on average, 150–450× over the orbit (Scientific
  American "Under Pluto's sunny skies…"; Discover "BAFact math"). Blue haze of tholin particles in many layers, seen
  backlit by New Horizons (NASA "New Horizons finds blue skies and water ice on Pluto", Oct 2015; JHU Hub). Rotation
  6.39 d *(from memory)*. Charon is not drawn: Sputnik Planitia lies on the hemisphere facing away from it.
- **Kepler-16 b.** First transiting circumbinary planet (Doyle et al., Science 333, 1602, 2011; JPL news release
  "NASA's Kepler discovery confirms first planet orbiting two stars"): Saturn-mass, 229-day orbit at 0.7048 au around a
  K dwarf (0.649 R☉) and an M dwarf (0.226 R☉) that orbit each other every 41 days (Wikipedia "Kepler-16"). Apparent
  sizes *(computed)*: 0.649/0.705 = 0.92× and 0.226/0.705 = 0.32× our Sun's from Earth (they vary a little as the stars
  move). Distance ≈ 245 light-years (Gaia-based; NASA's 2011 release said "about 200"). The planet is a gas giant with
  no known moons: the narration says "from a moon of it, if it has one" and the caption states that Kepler-16 b itself is a gas giant.
- **Payoff line.** "There is only one sunset that human eyes have watched from the ground": the Apollo landings were
  all made in the lunar morning and left before sunset *(from memory)*; astronauts in orbit see the Sun set behind
  Earth's own limb. Sunsets have been photographed from the surface of Mars by rovers; Cassini (Titan, Saturn) and New
  Horizons (Pluto) observed the Sun passing behind those atmospheres from space.

## 9:16 version
The Blender plates are square (2160², 24° × 24°): the 16:9 film uses a 2160 × 1215 band around the horizon and the
9:16 film a 1215 × 2160 column around the sunset point, both at the same 0.89 scale, so neither is a crop of the other
and the Sun is the same size in both. `VERT=1` re-lays the HUD (larger, stacked, below the top 12 %), the captions
(above the bottom 20 %), the titles and the recap grid; Saturn and Uranus use a narrower sweep so the Sun
and the rings stay in the column.

## What each view is based on
Mars: rover sunset images (Spirit, Curiosity, Perseverance). Mercury: MESSENGER imaging and the orbit. Venus: Venera 13
and 14 surface panoramas. Jupiter: Juno and Galileo data. Saturn: Cassini data and ring geometry. Uranus: Voyager 2 data
and the 98° tilt. Titan: Huygens surface images and Cassini radar of the seas. Pluto: New Horizons images of Sputnik
Planitia. Kepler-16 b: Kepler photometry; the moon is imagined. All shots are time-lapses except Jupiter (real time).

## Honest limitations
- Everything is computer-generated, Earth included. The landscapes are plausible, not maps of real places:
  no specific crater, mesa or mountain is reproduced.
- Sky colours for Jupiter, Saturn and Uranus at cloud-top level have never been photographed; they are informed guesses. The same goes for the imagined moon of Kepler-16 b, where the red dwarf's share of the light
  is also exaggerated so that its shadows can be seen.
- The cloud decks are height fields with translucent shading and distance haze, not volumetric clouds; they do not
  evolve during a shot. Earth's cloud decks drift but do not change shape.
- The plates are lit from one fixed Sun elevation; as the Sun sinks the compositor dims and recolours that light but the
  shadows do not lengthen. On Uranus, where the Sun moves sideways, the directional light is recomputed from the normal
  pass without shadows.
- Mercury's double sunset is shown from an idealised spot and compressed from days into seconds; Uranus's polar sunset
  likewise. Jupiter's is real time but ignores atmospheric refraction, which is unknown for that viewpoint and would
  stretch it.
- Venus: the brighter patch of cloud is a guess; Venera images show the horizon but not where the Sun was.
- Titan combines an equatorial pebble field with a polar sea shore in one frame.
- Neptune is mentioned and captioned but has no vista of its own.
- Stars are procedural, not the real sky. Brightness is exposure-normalised on every world: Pluto at noon is really
  about a thousand times dimmer than Earth, Titan likewise.
- Slow shots are rendered every 2nd or 3rd frame with linear blends between; the sea, Uranus and all cross-fades are
  rendered at a higher rate.
- 4K is a Lanczos upscale of the 1080p master.
