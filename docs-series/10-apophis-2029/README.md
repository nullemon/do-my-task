# 10 — FRIDAY THE 13TH, 2029

*On Friday 13 April 2029 the asteroid 99942 Apophis passes about 32,000 km above the Earth — closer than the ring of
geostationary satellites — and it will miss. A calm, true-scale look at how we know, what people will see, and what the
flyby does to the asteroid.*

**YouTube title:** An Asteroid Will Pass Closer Than Our Satellites in 2029

**YouTube description (2 lines):**
On Friday 13 April 2029 the 340-metre asteroid Apophis will pass about 32,000 km above Earth, inside the distance of our geostationary satellites, visible to the naked eye for some two billion people. It will not hit us: this film shows, to true scale, how we know, what you will see, and what Earth's gravity will do to it.

A 5:18 narrated documentary (1920×1080, 24 fps) in the series look: thin, widely spaced Inter Light caps, slow camera,
grain and vignette added at the final encode. The thumbnail (`out/thumb.jpg`) shows exactly what the first five seconds
show: the Apophis model in the foreground, the Earth and its satellite ring behind, "32,000 KM", and "it will miss".

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with measured times + shot list |
| `timeline.py` | voice starts, shot list, and the physical flyby model (hyperbola from published perigee distance and speed, Earth rotation, Sun direction) |
| `lib.py` | renderers: Earth sphere (Blue Marble day map, night lights, cloud layer with shadows, relief shading from an elevation map, ocean glint, limb scattering), Moon (albedo + bump relief), real star field (d3-celestial catalogue to mag 8 + a faint synthetic population), Milky Way model, anti-aliased 3D lines, glints, type, bloom |
| `comp.py` | every shot as a function of film time; writes silent x264 CRF 14 segments |
| `ground.py` | the naked-eye scene: procedural night landscape (layered ridges, conifers, valley town, mist) under the real sky for 13 April 2029, ≈21:46 UTC, 40° N |
| `blender/asteroid.py` | Blender 5.1 (bpy, Cycles CPU): the Apophis model and its 540-frame tumble (orthographic, 0.4 m per pixel, RGBA), and the Eiffel Tower at the same scale and lighting |
| `blender/craft.py` | simplified OSIRIS-APEX and Ramses stills |
| `ast_interp.py` | fills the asteroid frames that were not path-traced (see limitations) by optical-flow interpolation |
| `audio/narration.py`, `audio/gen_voice.py` | narration text, Kokoro TTS (am_michael, speed 0.94) |
| `audio/mix.py`, `audio/placement.json` | voice chain, numpy music bed (D-minor drone and pads, sub swells, soft pings, choir shimmer at the end), ducking, two-pass loudnorm −14 LUFS, SRT |
| `render_all.sh`, `encode_one.sh`, `thumb.py` | segment renders + join, the two deliverables, the thumbnail |
| `apophis-2029.srt` | subtitles from the placed voice timings (also muxed as a soft track) |

Rebuild: `python blender/asteroid.py ast 0 540` (+ `tower`), `python blender/craft.py apex|ramses`, `python3 ast_interp.py`
→ `ttsenv/python audio/gen_voice.py && ttsenv/python audio/mix.py` → `bash render_all.sh noast; bash render_all.sh ast; bash render_all.sh join`
→ `bash encode_one.sh hq|4k`, `python3 thumb.py`. (`lib.py` needs `opencv-python-headless`; it was pip-installed into the scratch `pylib/`.)

## What is to scale, and what is not
| shot | to scale | not to scale / illustrative |
|---|---|---|
| hook, tides, rock, missions | Earth's ring is 6.6 Earth radii; in *tides* the Earth has its true apparent size from 38,000 km (≈19°) | the asteroid is a foreground object, hugely enlarged relative to the Earth; spacecraft are enlarged relative to the asteroid |
| scare / relief | Earth, and the 38,000 km to the real pass point | the "range of possible positions" band is schematic (its real length and orientation are not reproduced) |
| size | asteroid and Eiffel Tower share one scale (the model is ≈460 × 310 × 265 m, volume-equivalent ≈340 m; the tower is 330 m) | — |
| geo, moon, pass, endpass, night | Earth, ring radius, Moon size and distance, the hyperbola, the clock, the Earth's rotation and day/night side | satellite positions on the ring; Moon position and lighting; Apophis is drawn as a point (at true size it would be far below a pixel) |
| orbit | sizes and shapes of the orbits (a = 0.922 AU, e = 0.191 before; a ≈ 1.10 AU, e ≈ 0.19 after), both through the encounter point | orientation in space, tilt of the orbits, Sun and planet sizes |
| ground | star positions for the date, hour and latitude | the landscape; the asteroid's path among the stars (it depends on the observer's location by several degrees) |

## Facts and sources (checked with web search, November 2026)
- **Date, distance:** closest approach 13 April 2029, 21:46 UT; "less than 32,000 km from Earth's surface" (ESA), about
  31,600 km above the surface / ≈38,000 km from the centre (JPL values as quoted on Wikipedia; NASA's Apophis page says
  "about 20,000 miles (32,000 km)"). Geostationary altitude is 35,786 km; the Moon's mean distance is 384,400 km, so the
  pass is about a tenth of the way to the Moon. Predicted to within a few kilometres (3-sigma ≈ ±3.4 km).
  The film says "roughly thirty-two thousand kilometres above the surface"; the read-out shows 31,600.
- **Size, shape, spin:** radar gives an equivalent diameter of 0.34 ± 0.04 km and suggests an elongated, possibly
  bi-lobed body (Brozović et al. 2018, *Icarus* 300, Goldstone + Arecibo 2012–13). It tumbles (non-principal-axis
  rotation) with a main period of ≈30.6 h (Pravec et al. 2014; radar solution 30.62 h). Stony (Sq-type).
- **Discovery:** 19 June 2004, Kitt Peak, by Roy Tucker, David Tholen and Fabrizio Bernardi (ESA; *Astronomy*); followed
  for two nights, then recovered on 18 December 2004 from Siding Spring, Australia.
- **The scare:** in late December 2004 the estimated chance of impact on 13 April 2029 rose to 2.7 % (1 in 37), and
  Apophis reached level 4 on the Torino scale, the highest rating yet given to any object (ESA). (In 2025 asteroid
  2024 YR4 briefly had a higher *probability*, 3.1 %, but only Torino level 3, so the film says "highest rating", not
  "highest probability".) Pre-discovery images from March 2004, identified on 27 December 2004, removed the 2029 risk.
- **Later risks:** an impact in 2036 was ruled out in January 2013; radar from Goldstone and Green Bank in March 2021
  ruled out 2068 and any impact for at least 100 years, and Apophis was taken off ESA's risk list on 26 March 2021
  (ESA; NASA/JPL; Universe Today).
- **Speed:** ≈7.4 km/s relative to the Earth at closest approach, about 6 km/s on the way in (Wikipedia, from JPL Horizons).
- **How rare:** NASA: an asteroid this size passes this close "only every few thousand years on average"; a 2025
  estimate gives ≈7,500 years (Live Science). The film says "once in several thousand years".
- **Visibility:** peak brightness about magnitude 3 (3.1); visible without optical aid across much of Europe, Africa
  and western Asia; "around two billion people" (ESA, as reported by Space.com and others). It becomes naked-eye
  visible first over Australia, crosses the Indian Ocean and Africa, and is over the Atlantic at closest approach
  (NASA). "As bright as the stars of the Little Dipper" and "more than the width of the full Moon within a minute" are
  from NASA/JPL's 2019 release *Scientists Planning Now for Asteroid Flyby a Decade Away*; that release was quoted from
  memory, since this session's searches did not return its text.
- **Orbit change:** Aten class (a = 0.92 AU, period ≈0.9 yr) before, Apollo class (a ≈ 1.1 AU, ≈1.2 yr) after
  (NASA Apophis facts; NASA SAT briefing; Wikipedia).
- **Tides:** the spin state is likely to change, by up to hours in either direction (Benson et al. 2023 and others);
  predictions for surface motion range from none to metre-scale boulders moving (Ballouz et al. 2024, *PSJ*; Kim et
  al. 2023). The pass is at ≈6 Earth radii, outside the Roche limit.
- **Missions (status late 2026):** NASA's OSIRIS-APEX (ex OSIRIS-REx) is en route after its September 2025 Earth
  flyby, with rendezvous planned after the 2029 flyby; it survived a proposed cancellation for FY2026 and its funding is
  reviewed yearly (Live Science; Scientific American). ESA's Ramses was approved at the November 2025 Ministerial,
  passed its critical design review in February 2026, is being built by OHB Italia, is due to launch in April–May 2028
  on a Japanese H3 with JAXA's DESTINY+, and to arrive about February 2029 with two CubeSats (ESA; Sky & Telescope).
  DESTINY+ is planned to fly past Apophis in 2029 on its way to Phaethon.
- **Hypothetical impact:** ≈1,200 megatons of TNT (JPL Sentry's former estimate, as quoted on Wikipedia and elsewhere);
  the film says "roughly a thousand megatons", more than twenty times the 50-megaton Tsar Bomba (1961). "Devastate a
  whole region, not end civilisation" is the standard qualitative assessment for an object of this size.

### Numbers derived here (not quoted from a source)
- **The flyby path** in the true-scale shots is a two-body hyperbola built from the published perigee distance
  (38,000 km) and speed (7.42 km/s, so v∞ ≈ 5.84 km/s, e ≈ 4.25), with closest approach placed over the mid-Atlantic at
  about 27° N, 42° W and the outbound leg toward the Sun. Its ground track (southern Australia → Indian Ocean →
  Africa → Atlantic → North America) matches NASA's description, but it is a reconstruction, not an ephemeris.
- **"Bends the path by roughly 27°"** is the deflection of that hyperbola.
- **"Passes north of the ring's plane"** follows from the same reconstruction (closest approach at ≈27° N).
- **Sidereal time and Sun position** for the date were computed by hand (GMST ≈ 11.3 h at 21:46 UT; Sun at RA ≈ 21.8°,
  Dec ≈ +9.2°) and are good to about a degree.
- **Earth spans ≈19°** from 38,000 km: 2·asin(6371 / 38,000).

## Honest limitations
- The asteroid is an artist's model. Nobody has seen Apophis's surface; boulders, craters and colour are modelled on
  Itokawa-like rubble piles, and the two-lobed outline is only "possible" in the radar data.
- Only every fourth frame of the asteroid's tumble after frame 122 (every second from 90 to 122) was path-traced; the
  frames between were interpolated by optical flow (measured structural error ≈1/255 against real renders). The machine
  was shared by three films and a full render would have taken several more hours.
- The Earth is an analytic sphere shaded in numpy from 4K NASA maps, not a volumetric render: clouds are a single
  static layer and the atmosphere is a fitted limb glow. The Moon map is only 1K.
- The night landscape is procedural 2D layering, not a photograph or a 3D terrain.
- Spacecraft are simplified recognisable layouts, kept small in frame.
- In the hook, tides, missions and rock shots the asteroid is composited as a large foreground object; those frames say
  so in the footer.
- Kokoro pronounces "Apophis" with a slightly synthetic stress; the name was phoneme-corrected to end in /s/.
