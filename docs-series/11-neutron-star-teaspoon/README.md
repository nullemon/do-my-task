# 11 — ONE TEASPOON OF A NEUTRON STAR

*A teaspoon of neutron-star matter would outweigh a mountain. The honest answer to "what would it do to Earth?" is that
you could never scoop it: away from the star's gravity it would blow itself apart. A calm look at what a neutron star is,
to scale, and at the one way its matter really does reach us: as gold.*

**YouTube title:** What One Teaspoon of a Neutron Star Would Do to Earth

**YouTube description (2 lines):**
Five millilitres of neutron-star matter has a mass of billions of tonnes, more than every human alive combined. This film shows what a neutron star is, to scale over New York, why you could never bring a spoonful home, what would happen if you somehow could, and why the gold in a ring was probably made when two of them collided.

A 5:13 narrated documentary (1920×1080 and a 1080×1920 recomposition, 24 fps) in the series look: thin, widely spaced
Inter Light caps, slow camera, grain and vignette added at the final encode. The thumbnail shows what the first five
seconds show: the teaspoon holding a blinding blue-white speck above the Earth's limb, "1 TEASPOON", "= A MOUNTAIN".

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with measured times + shot list |
| `timeline.py` | voice starts, shot list, and the physical constants / derived numbers used on screen (`python3 timeline.py` prints them) |
| `lib.py` | shared renderers from film 10: Earth sphere (Blue Marble day map, clouds with shadows, relief, ocean glint, limb scattering), real star field (d3-celestial catalogue to mag 8 + synthetic faint stars), Milky Way model, lines, type, bloom |
| `ns.py` | this film's renderers: neutron-star surface (cellular crust plates at three scales, hair-line fractures, granulation, hot magnetic poles) drawn with gravitational light bending; weak-field lensing of the background sky; dipole field lines; hollow-cone pulsar beams integrated along the line of sight; red supergiant; layered filament explosions (supernova, blast, kilonova); cut-away spheres (neutron star, Earth); the New York relief map and its perspective view |
| `comp.py` | every shot as a function of film time, in both aspect ratios (`NS_VERT=1` re-lays everything for 9:16); writes silent x264 CRF 14 segments |
| `env.py` | HDR environments for Blender (the Earth from high orbit; a dark studio for the ring) |
| `blender/spoon.py` | Blender 5.1 (bpy, Cycles CPU): a 14 cm stainless teaspoon (lofted bowl and handle, solidify + subdivision, brushed micro-scratches, roughness smudges) with and without the emissive bead, and a comfort-fit gold wedding band; 80-frame slow moves, RGBA |
| `audio/narration.py`, `audio/gen_voice.py` | narration text, Kokoro TTS (am_michael, speed 0.94) |
| `audio/mix.py`, `audio/placement.json` | voice chain, numpy music bed (D-minor drone and pads, sub swells, risers and low impacts on the three explosions, soft ticks that follow the pulsar's spin, choir shimmer on the gold and the ending), ducking, two-pass loudnorm −14 LUFS, SRT |
| `render_all.sh`, `render_list.sh`, `encode_one.sh`, `thumb.py` | segment renders + join, the deliverables, the two thumbnails |
| `neutron-star-teaspoon.srt` | subtitles from the placed voice timings (also muxed as a soft track) |

Rebuild: `python3 env.py` → `bash blender/render_sprites.sh` → `ttsenv/python audio/gen_voice.py && ttsenv/python audio/mix.py`
→ `bash render_all.sh h 0; bash render_all.sh h 1; bash render_all.sh h join` (same with `v`) → `bash encode_one.sh hq|4k|vertical`
→ `python3 thumb.py; NS_VERT=1 python3 thumb.py`. (`lib.py` needs `opencv-python-headless` and `scipy`; they live in the scratch `pylib/`.)

## The vertical (9:16) version
`out/neutron-star-teaspoon-vertical.mp4` is a recomposition, not a crop: `comp.py` re-runs the same renderers at 1080×1920
with the same timeline, voice and subtitles.
- Hero objects sit in the central column: the spoon is turned about 50° so that it runs up the frame, with the Earth's limb
  lower; stars, cut-aways, the merger and the kilonova are centred in the upper two thirds; the city shot keeps the star
  over New York with more ground below it.
- All captions, read-outs and notes are re-laid: centred, larger, stacked, and kept between 12 % from the top and 20 % from
  the bottom; the cut-away labels become a legend under the star; the mass bars move under the spoon.

## What is to scale, computed, or illustrative
| shot | to scale / computed | illustrative |
|---|---|---|
| hook, answer, thought A, final | — | spoon, bead and Earth share no scale; the bead is drawn smaller than the 2.1 cm sphere that 5 mL makes, and is shown as a point of light |
| giant, supernova | — | artist's impression; time compressed (the collapse takes under a second, the remnant shell years) |
| city | the star (25 km) and the map share one scale; the map is real elevation data (zoom-12 terrain tiles), Manhattan's 21.6 km is measured on it | relief exaggerated ×9; the star could not exist here — it is a size comparison only; the star's light on the ground is artistic |
| dens | layer order; crust ≈ 1 km of a 12 km radius | layer thicknesses approximate, the inner core is unknown |
| mass | the bars are to scale | — |
| grav | light bending: surface mapping 1 − cos α = (1 − cos ψ)(1 − r_s/R) (Beloborodov 2002) for 1.4 M☉, R = 12 km, which shows ≈ 76 % of the surface; the background is displaced by the weak-field deflection 2 r_s/b | surface detail; the weak-field formula is only approximate this close to the star |
| pulsar, magnetar | geometry of an inclined dipole | spin slowed about a thousand-fold; field lines schematic; beam shape artistic |
| thought B | simple harmonic fall through a uniform-density Earth (period 84.4 min; clock, depth and speed read-outs follow that model); entry point New York, antipode in the Indian Ocean | no drag, no rotation of the Earth; bead enlarged; the interior colours are conventional |
| merger, kilonova, gold | separation follows a ∝ (t_c − t)^¼ | slowed enormously; ripples exaggerated; colours compressed in time (the 2017 kilonova faded from blue to red over days) |
| end | — | the black hole is a black disc with a photon ring and stronger lensing, not a ray-traced metric |

## Facts and sources (checked with web search, November 2026)
- **Density, the teaspoon.** There is no single authoritative figure: published popular numbers for a teaspoon run from
  "a billion tons" (Mental Floss quoting NASA Goddard) through 3 billion (Princeton), 4 and 6 billion, to "of order
  10 billion tons" for 10¹⁸ kg/m³ (Gizmodo's *Ask a Physicist*). The film derives its own: 1.4 M☉ in a 12 km radius is a
  mean density of 3.8 × 10¹⁷ kg/m³, so 5 mL ≈ 1.9 billion tonnes ("about two billion"); core densities of ≈ 10¹⁸ kg/m³
  give ≈ 5 billion tonnes ("perhaps five billion, or more"); the top of the crust, at ≈ 10⁹ kg/m³, gives only ≈ 5 tonnes.
  Radii of 12–13 km come from NICER (PSR J0030+0451: 12.7–13 km at ≈ 1.4 M☉; PSR J0740+6620: 12.4–13.7 km at 2.08 M☉;
  Miller et al. 2019/2021, Riley et al. 2019/2021), hence "about twenty-five kilometres across".
- **"A mountain".** Astronomy magazine ("Ask Astro", 2018) compares a tablespoon (>1 billion tons) to Mount Everest. The
  film's own check: 2 billion tonnes of granite (2.7 t/m³) is 0.7 km³, a hill-to-mountain-sized block; the bar chart
  shows 1 km³ of granite = 2.7 billion tonnes.
- **Humanity.** Adult human biomass was ≈ 287 million tonnes in 2005 (Walpole et al. 2012, *BMC Public Health*); scaled to
  about 8.2 billion people including children this is roughly 0.4–0.5 billion tonnes (the bar uses 0.5). So a teaspoon is
  2–10 times all of humanity; the narration says "more than every human being on Earth, combined". Great Pyramid ≈ 6
  million tonnes (commonly quoted; not re-searched in this session).
- **Formation.** Stars above about 8 solar masses end in core collapse; "in less than a second, the core shrinks from a
  diameter of about 8,000 km to about 19 km" (Chandra X-ray Center education pages).
- **Structure.** Outer crust of nuclei and electrons from ≈ 10⁹ kg/m³, neutron drip at ≈ 4 × 10¹⁴ kg/m³ (inner crust),
  a core of mostly neutrons above about nuclear density (2.3–2.8 × 10¹⁷ kg/m³), and an inner core of unknown composition
  (standard textbook picture; quoted from memory, not re-searched).
- **Gravity.** Derived for 1.4 M☉, 12 km: g = GM/R² = 1.3 × 10¹² m/s² ≈ 1.3 × 10¹¹ g ("around a hundred billion times");
  a 1 m drop takes 1.2 µs and ends at 1,600 km/s (Newtonian; "well over a thousand kilometres per second"); escape
  velocity c·√(r_s/R) = 0.59 c ("more than half the speed of light").
- **Fastest pulsar.** PSR J1748−2446ad in Terzan 5: 716.36 Hz, found by Hessels et al. with the Green Bank Telescope
  (discovered 2004, published 2006); equatorial speed ≈ 24 % of c for a 16 km radius; still listed as the record holder.
- **Magnetars.** Fields of 10¹⁴–10¹⁵ gauss; NASA: "one thousand trillion times the strength of Earth's magnetic field"
  (1998 release on SGR 1900+14) and "the strongest of any object in the observable universe".
- **What would really happen.** Physicists' popular answers agree that the matter would expand explosively once the
  star's gravity no longer confines it (Gizmodo *Ask a Physicist*; Astronomy "Ask Astro"). Gizmodo's estimate is ≈ 50
  trillion Hiroshima-class bombs, ≈ 3 × 10²⁷ J. The film's own bracket: 1 MeV per nucleon to 1 % of mc² for 2 × 10¹²
  kg is 2 × 10²⁶ – 2 × 10²⁷ J, i.e. hundreds to thousands of times the Chicxulub impact (taken as ≈ 4 × 10²³ J, the
  usual "100 million megatons"; that figure is itself uncertain by a factor of several). This is an order-of-magnitude
  estimate and is labelled so on screen.
- **Thought experiment.** Derived: a 2 × 10¹² kg bead pulls with 1 g at 3.7 m (2.6–5.8 m for 1–5 × 10¹² kg). Its weight,
  2 × 10¹³ N on a few cm², exceeds the strength of any material by many orders of magnitude. Falling through a
  uniform-density Earth takes 21.1 min to the centre (about 19 min with the real density profile), 42 min to the far
  side, 84 min for the round trip; the rock it sweeps on one pass is ≈ 2.5 × 10⁷ kg, about a hundred-thousandth of its
  own mass, so drag is negligible at first ("the planet would barely slow it"). The Earth's rotation, heating and the
  bead's effect on the rock around it are ignored.
- **GW170817.** Detected 17 August 2017 by LIGO and Virgo; host galaxy NGC 4993 at 40 Mpc ≈ 130 million light-years;
  kilonova AT 2017gfo; ejecta 0.03–0.05 M☉ with lanthanides (Pian et al. 2017, *Nature*). Gold yield estimates differ:
  "about 10 times the Earth's mass in gold and platinum" (E. Berger, quoted by Live Science) up to ≈ 100 Earth masses
  of gold in some press reports; the film says "by some estimates, several times the mass of the Earth in gold alone".
- **Origin of gold.** Mergers are thought to be a major r-process site, but the share is debated; a 2025 study (Patel et
  al., *ApJL*) argues that magnetar giant flares could make 1–10 % of the Galaxy's heavy elements. The film says "very
  likely made like this" and carries an on-screen note that other sources are debated.
- **Black-hole limit.** The maximum neutron-star mass is not known precisely; "roughly 2–3 solar masses" covers current
  estimates (heaviest well-measured pulsar: 2.08 M☉, PSR J0740+6620).
- **Data.** Elevation: Mapzen/AWS Terrain Tiles (terrarium, zoom 12; sources include USGS 3DEP lidar). Earth maps: NASA
  Blue Marble via the `three-globe` package. Stars: `d3-celestial` catalogue.

## Deliverables (`out/`, measured)
See the table at the end of this file after the final encode.

## Honest limitations
- Nobody has seen a neutron star's surface; the crust pattern, colours and hot spots are an artist's impression. The star
  is drawn far cooler than reality so that structure is visible (a real one would be a featureless blinding point).
- Lensing uses two approximations (Beloborodov's formula for the surface, weak-field deflection for the sky) rather than
  ray tracing in the Schwarzschild metric; field lines and beams are not lensed. Rotation effects (oblateness, Doppler
  beaming, frame dragging) are ignored.
- The supernova, blast and kilonova are layered 2D filament textures that expand self-similarly, not fluid simulations.
- The Earth is an analytic sphere shaded in numpy from 4K NASA maps with a single static cloud layer.
- The New York map is a shaded-relief rendering of elevation data only (no buildings, roads or satellite imagery; the
  open tile servers for those were not reachable). Its water mask is "elevation below 1.5 m", so tidal marsh reads as
  water and a few small islands are dropped.
- The spoon and ring are Blender models rendered at 40 spp with denoising; the frames between rendered ones are
  cross-blended in the compositor (the motion is under two pixels per rendered frame).
- The bead in the spoon is symbolic (a small emitter with glare); 5 mL as a sphere would be 2.1 cm across.
- Voice is synthetic (Kokoro); "J1748−2446ad" is shown on screen but not spoken.
