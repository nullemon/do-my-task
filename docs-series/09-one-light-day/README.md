# 09 — ONE LIGHT-DAY FROM HOME

*Voyager 1, launched in 1977, is the most distant thing humans have built. On 18 November 2026 (NASA/JPL
projection) it reaches one light-day from Earth. This film tells how it got there, how it is still heard, and
how small one light-day is next to the distance to the nearest star.*

**YouTube title:** Voyager 1 Is About to Reach One Light-Day From Earth

**YouTube description (2 lines):**
On 18 November 2026, by NASA's calculation, Voyager 1 will be one light-day from Earth: about 25.9 billion km, 49 years after launch.
The grand tour, the Pale Blue Dot, the Golden Record, a 23-watt signal, and why the nearest star is still about 75,000 years away at this speed.

(The film was finished on 10 November 2026, eight days before the projected date, so the title, the narration and
the captions say "about to" / "reaches", never "has reached". If it is published after the 18th, change the title
verb to "Just Reached"; nothing in the film itself needs to change.)

A 4:48 narrated documentary (558 words of narration, 21 lines), 1920×1080 at 24 fps, plus a 1080×1920 vertical version with its own layout for every shot. Same series look:
thin, widely spaced Inter Light captions, slow camera, grain and vignette at the final encode.

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with measured times, shot list |
| `timeline.py` | voice start times, shot boundaries, cross-fade length |
| `blender/voyager.py` | our own Voyager model (Blender 5.1.2 bpy, Cycles CPU): 3.66 m dish with feed, subreflector and struts, decagonal bus with louvres, bolts, harnesses and star trackers, RTG boom with three finned units, science boom with scan platform and optics, 13 m magnetometer lattice boom, two 10 m whip antennas, thruster clusters, crinkled-foil materials, and the gold record with a stylised etched cover. Renders high-resolution RGBA plates (hero A/B, record, cover, RTG, signal, end, fly-by sprite, thumbnail) and writes each camera to `cam.json` |
| `blender/dsn.py` | our own stylised 70 m Deep Space Network antenna at night (reflector with panel seams, backing truss, quadripod, subreflector, feed cones, elevation wheel, alidade, pedestal, buildings, lamps, desert ridge) |
| `sky.py` | procedural sky: a structured Milky Way panorama (bulge, disk, dust lanes with reddening, star clouds, nebulae) and a one-million-star catalogue with a realistic magnitude distribution and blackbody colours, rendered through any camera rotation |
| `planets.py` | analytic planet renderer (oblate ellipsoids, limb darkening, atmosphere limb, Saturn's rings with gaps, transparency, ring shadow on the globe and globe shadow on the rings). Jupiter, Saturn, Io, Neptune and the Moon use procedural textures; Earth uses NASA Blue Marble / night lights / clouds from the `three-globe` npm package |
| `lib.py`, `comp.py` | numpy/PIL compositor. Every frame is built in linear light (sky, plates placed with sub-pixel LANCZOS, planets, flares, particles), bloomed, tone-mapped and captioned. `VERT=1` switches every shot to its own 9:16 layout |
| `thumb.py` | 16:9 and 9:16 thumbnails |
| `render_plates.sh`, `render_segs.sh`, `join.sh`, `encode_one.sh` | plate queue, segment queue (12 s segments, resume-safe), concat, final encodes. `waitrun.sh`, `finalq.sh`, `lastq.sh`, `endq.sh`, `queueC.sh`, `render_dsn.sh` are the one-off chaining scripts used during this render |
| `audio/` | narration, Kokoro TTS (`am_michael`, speed 0.94, the series voice), mix (voice chain, numpy music bed in D minor, sub swells, telemetry pips under the signal section, ducking, two-pass loudnorm), SRT |
| `one-light-day.srt` | subtitles from the placed voice timings (also muxed as a soft track) |

Rebuild: `bash render_plates.sh` → `python blender/dsn.py final` → `audio/gen_voice.py`, `audio/mix.py` →
`bash render_segs.sh 0 12 … 276` (and again with `VERT=1`) → `bash join.sh` / `bash join.sh v` → `bash encode_one.sh hq|4k|vertical` → `python3 thumb.py` (and `VERT=1 python3 thumb.py`).

## Facts and sources (checked with web search on 10 November 2026)
- **One light-day:** light travels 25,902,068,371 km in 24 hours (299,792.458 km/s × 86,400 s). NASA/JPL project
  that Voyager 1 will be that far from Earth on **18 November 2026 at about 10:16 UTC** (2:16 a.m. PST). Reported by
  IFLScience ("It's official: Voyager 1 will cross the 1 light-day threshold on November 18, 2026"), Popular
  Science, Sky at Night Magazine, EarthSky, AccuWeather. Earlier coverage gave 13 or 15 November; the film uses
  the date the mission team confirmed and labels it a projection. Because Earth circles the Sun, the Earth–Voyager
  distance wobbles through the year; reports say the crossing is permanent.
- **Launch:** 5 September 1977, Titan IIIE–Centaur, Cape Canaveral. Primary mission (Jupiter and Saturn) was
  planned to last about five years (NASA).
- **Jupiter:** closest approach 5 March 1979, 18 months after launch. Active volcanism on Io was discovered in
  Voyager 1 images (Linda Morabito, March 1979): the first active volcanoes seen beyond Earth (NASA).
- **Saturn:** closest approach 12 November 1980. The close Titan flyby bent the path northward out of the
  ecliptic plane, which ended the planetary tour (NASA).
- **Pale Blue Dot:** 14 February 1990, about 6 billion km from Earth; a 60-frame mosaic showing six planets (the
  "Family Portrait"); Earth is about 0.12 pixel across; taken at Carl Sagan's suggestion; cameras were powered
  off 34 minutes later (NASA Science, "10 things you might not know about Voyager's famous Pale Blue Dot photo";
  NASA/JPL "Voyager celebrates 20-year-old valentine to solar system"; Space.com). "A mote of dust suspended in a
  sunbeam" is from Sagan's *Pale Blue Dot* (1994); the film quotes those eight words with attribution.
- **Interstellar space:** heliopause crossing on 25 August 2012 at about 121 AU (NASA/JPL, announced 2013).
  The on-screen note adds that Voyager is still far inside the Oort cloud.
- **Golden Record:** gold-plated copper, 12 inches (30 cm); 115 images (NASA/JPL and Smithsonian count; some
  sources say 116 by counting the calibration image), greetings in 55 languages, sounds of Earth (surf, wind,
  thunder, birds, whales), 90 minutes of music including Bach and Chuck Berry; playing instructions on the cover;
  expected to last about a billion years (NASA/JPL "What is the Golden Record?"; Smithsonian Magazine).
- **Signal:** transmitter about 22–23 W (NASA describes it as about the power of a refrigerator light bulb);
  received power of order 10⁻¹⁸ W or below (published estimates range from about 10⁻¹⁸ to 10⁻¹⁹ W, so the
  film says "far weaker than a billionth of a billionth of a watt"); science telemetry at 160 bits per second;
  the DSN's 70 m antennas are at Goldstone (California), Madrid and Canberra (NASA DSN; JPL telecom documents).
  From Voyager, Earth is never more than about 0.33° from the Sun (asin(1 AU / 173 AU)).
- **Power and instruments:** three plutonium-238 RTGs, output falling about 4 W per year. Of ten science
  instruments, two are on (magnetometer, plasma wave subsystem). Off dates on screen: photopolarimeter 1980,
  cameras 1990, infrared spectrometer 1998, plasma science 2007, planetary radio astronomy 2008, ultraviolet
  spectrometer 2016, cosmic ray subsystem 25 February 2025, low-energy charged particles 17 April 2026 (NASA
  Voyager status table; LASP; reporting by Fox News, Hypebeast, ScienceDaily, The Debrief). In September 2026 the
  team swapped three devices for lower-power ones (the "Big Bang" reconfiguration), confirmed by JPL on 29 October
  2026 (secondary coverage: NewSpace Economy, Xenospectrum). The narration says only "this year ... shut down one
  more, and reworked the power system", because I could reach secondary coverage but not the JPL release itself.
- **Speed and the scale payoff:** about 17 km/s (61,000 km/h) relative to the Sun. One light-year is 365.25
  light-days, so Proxima Centauri (4.246 ly) is about 1,551 light-days away and Alpha Centauri A/B (4.37 ly) about
  1,596. At 17 km/s one light-year takes about 17,600 years, so 4.25 ly takes about 75,000 years. Voyager 1 is not
  aimed there: in about 40,000 years it passes about 1.6 ly from Gliese 445, a red dwarf that is itself
  approaching the Sun (NASA).
- **End of mission:** NASA hopes to keep at least one instrument running into the 2030s; the narration says
  "probably within the next ten years".

## Honesty notes / limitations
- **Everything on screen is our own render.** No NASA spacecraft imagery is used. The Voyager model is stylised:
  proportions and the main parts follow public descriptions, but small parts, blanket layout, bracketry and the
  exact boom angles are approximate, and the truss members are simplified.
- **The Pale Blue Dot view is a labelled reconstruction** (procedural scattered-light bands, grain, a sub-pixel
  dot). It is not the photograph and the band colours and positions are only in the spirit of the original.
- **The record cover engraving is stylised**, drawn by us from the general layout (record view, pulsar-map-like
  burst, hydrogen diagram, picture frames). It is not a tracing and its details are not the real ones.
- **Lighting is theatrical.** Real sunlight at Voyager is about 30,000 times weaker than at Earth and the Sun
  sits within a third of a degree of the dish axis, so the real spacecraft body is in the dish's shadow. The film
  lights the model from about 37° off-axis with faint fills (stated on screen in the signal shot).
- **Camera moves on the spacecraft are 2.5D:** each Voyager shot is one high-resolution Cycles plate with a slow
  push and a drifting star field, not a frame-by-frame 3D orbit (the shared 4-core machine made per-frame Cycles
  far too slow). The spacecraft therefore never rotates on screen.
- **Planets:** Jupiter, Saturn, Io, Titan, Neptune and the Moon are procedural. Jupiter's bands, eddies and Great
  Red Spot are plausible, not a map of the 1979 planet. Sizes, spacing and the Voyager sprite in the fly-by shots
  are not to scale; flight paths are schematic. The launch shot shows Earth and a schematic arc, not the rocket.
- **Heliosphere shot** is a schematic (a Rankine half-body flow); the real shape is uncertain.
- **Scale shot:** distances along each line are to scale, directions are flattened onto the screen.
- **The Milky Way and stars are procedural**, not the real sky; constellations are not real.
- **The DSN antenna** is a generic stylised 70 m dish, not a specific station.
- **4K** is a lanczos upscale of the 1080p render. The **vertical** version is re-composed per shot from the same
  plates (crops and pans of the 16:9 plates plus a separate caption layout); in close-ups the booms run off the
  sides of the frame.

## Deliverables (`out/`, not in git)
| file | what |
|---|---|
| `one-light-day-1080p-hq.mp4` | 1920×1080, x264 CRF 17 capped at 9.5 Mb/s, AAC 256k, soft subtitle track |
| `one-light-day-4k.mp4` | 3840×2160 lanczos upscale of the 1080p render (labelled in metadata), CRF 20 capped at 19 Mb/s |
| `one-light-day-vertical.mp4` | 1080×1920, every shot re-composed and every caption re-laid for 9:16 (text kept out of the top 12 % and bottom 20 %), same audio and subtitles |
| `one-light-day.srt` | subtitles |
| `thumb.jpg`, `thumb-vertical.jpg` | 1280×720 and 1080×1920 covers: our Voyager model, a pale-blue Earth dot, "1 LIGHT-DAY FROM EARTH · 49 years to get here" |

## Vertical version: how each shot was re-composed
Plates were reused; no shot needed a second camera, but every layout is separate (`P(h, v)` picks the value in `comp.py`).
Hero, record, RTG and end shots re-centre and enlarge the 16:9 plates so the dish and bus sit in the central column
(the long booms run off the sides). The record-cover and RTG close-ups become slow pans across the plate. The
light-time strip and the scale diagram are rebuilt as vertical axes (Earth at the bottom; the Sun at the bottom and
Alpha Centauri at the top). Jupiter, Saturn, the heliosphere, the Family Portrait and the DSN dish are re-framed and
re-scaled. Captions are larger, wrapped and stacked.

## Render / encode notes
- Blender plates (Cycles CPU, 110–220 spp, OIDN): eleven Voyager plates plus the DSN antenna, 8–49 minutes each on a
  4-core machine shared with two other films (load 14–20), about 4 h of wall clock in two queues. The dish plates
  (hero A, end, thumbnail, fly-by sprite) were rendered twice: the second pass added gore panels, fasteners, tone
  variation, a rim lip and uneven roughness to the reflector after review.
- Compositor: 6,912 frames per format in 24 segments, about 0.8–1.0 s per frame per worker.
- Audio: −14.1 LUFS integrated, −1.3 dBFS peak, measured with ebur128 on the final `-1080p-hq.mp4` and `-vertical.mp4` (the WAV mix itself is −14.0 LUFS, −1.5 dBTP).
- Sizes: `-1080p-hq.mp4` 352.6 MB, `-vertical.mp4` 352.4 MB (both 288.0 s, 6,912 frames); `-4k.mp4` 694.5 MB (capped at 19 Mb/s to stay under 740 MB).
- Checked before delivery: 21 frames of each format on contact sheets and 8 frames of the final 16:9 file at full size. Fixed along the way: two labels that ran off the right edge (the Sun note in the 23-watt shot, the Gliese 445 note), small print raised to 15 px in 16:9, and the dish re-rendered.
