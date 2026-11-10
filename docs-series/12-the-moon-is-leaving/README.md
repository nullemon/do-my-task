# 12 — THE MOON IS LEAVING

*The Moon recedes from the Earth by about 3.8 cm every year. A calm look at how we measure it, why it happens, what it did
to the length of the day, and why it means total solar eclipses will one day end.*

**YouTube title:** The Moon Is Leaving Us (3.8 cm Every Year)

**YouTube description (2 lines):**
Lasers bounced off reflectors left by Apollo and Lunokhod show the Moon moving away at about 3.8 cm a year, because Earth's tides push it outward and slow our spin. Follow the evidence back to 400-day years and a giant young Moon, and forward to the last total solar eclipse, roughly 600 million years from now.

A 4:58 narrated documentary in the series look (thin, widely spaced Inter Light caps, slow camera, grain and vignette at
the final encode), delivered in 16:9 and as a 9:16 recomposition. The thumbnail shows what the first five seconds show:
the cratered Moon in the foreground, the Earth behind it, "3.8 CM A YEAR", and "the last total eclipse is coming"
(the second line appears on screen at 10.6 s and is the subject of the last third of the film).

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with measured times + shot list |
| `timeline.py` | voice starts and shot list |
| `lib.py` | renderers (adapted from film 10): Earth sphere (Blue Marble, night lights, clouds with shadows, relief, ocean glint, limb scattering), **Moon from the LROC WAC 8k colour mosaic shaded with real LOLA slopes (16 px/deg elevation)**, real star field (d3-celestial catalogue to mag 8 + faint synthetic population), Milky Way model, lines, type, bloom |
| `fx.py` | procedural renderers: filtered Sun disc (granulation, spots, limb darkening) and red giant, solar corona (streamers, polar plumes, prominences), eclipse geometry with a rough lunar limb (Baily's beads and the diamond ring come out of the geometry), molten proto-Earth, reflective sea (multi-scale wave slopes, Fresnel reflection of the rendered sky, glitter path), Blender plate views |
| `comp.py` | every shot as a function of film time, laid out for 16:9 or (with `MOON_VERT=1`) 9:16; writes silent x264 CRF 14 segments |
| `blender/reflector.py` | Blender 5.1 (bpy, Cycles CPU) still: retroreflector array (10 x 10 corner-cube prisms, gold thermal blanket, tilt struts, sun-compass dial) on a regolith height field with craters, rocks and boot prints; second pass for the lit prisms |
| `blender/observatory.py` | still: dome with open slit, truss telescope, catwalk, support building, mast, on a rocky summit, moonlit |
| `blender/coral.py` | still: fossil horn coral with annual bands and fine growth ridges on a slab, raking light, depth of field |
| `audio/narration.py`, `audio/gen_voice.py` | narration text, Kokoro TTS (am_michael, speed 0.94) |
| `audio/mix.py`, `audio/placement.json` | voice chain, numpy music bed (D-minor drone and pads, sub swells, laser-echo pings, clock ticks, riser into totality, choir shimmer), ducking, two-pass loudnorm -14 LUFS, SRT |
| `render.sh`, `encode_one.sh`, `thumb.py` | segment renders + join, the deliverables, both thumbnails |
| `the-moon-is-leaving.srt` | subtitles from the placed voice timings (also muxed as a soft track) |

Rebuild: `python blender/reflector.py` (+ `glow`), `blender/coral.py`, `blender/observatory.py` -> `ttsenv/python audio/gen_voice.py && ttsenv/python audio/mix.py`
-> `bash render.sh h A|B|P; bash render.sh h join` (same with `v`) -> `bash encode_one.sh hq|4k|vertical`, `python3 thumb.py`, `MOON_VERT=1 python3 thumb.py`.
Assets (fetched in this session): `lroc_color_poles_8k.jpg` (NASA SVS CGI Moon Kit, via the `nasa/virgo` GitHub repository), `ldem_16_uint.tif` (LOLA elevation, same kit, via `AVSLab/vizard`), Blue Marble / night lights / clouds (`three-globe` npm package), star catalogue (`d3-celestial` npm package). `lib.py` needs `opencv-python-headless` (pip-installed into the scratch `pylib/`).

## The vertical (9:16) version
`out/the-moon-is-leaving-vertical.mp4` is a recomposition, not a crop: the same shot functions run at 1080x1920 with their own layout.
- Hero objects sit in the central column: Moon below and Earth above in the hook; the tide diagram is turned 90 degrees (Moon below the Earth); Sun over Moon in the size comparison; Earth above the Moon in the to-scale shot; the Blender plates were rendered square (2160x2160) so that both a 16:9 band and a 9:16 column could be cut from them.
- All captions, counters and labels are re-laid: centred, stacked, larger relative to the frame, and kept between 12 % from the top and 20 % from the bottom.

## What is to scale, and what is not
Following the user's rule of 10 November, the film carries **no on-screen disclaimer small print** ("not to scale", "illustration", "artist's impression" ...). Only factual notes remain on screen (data sources, numbers, dates, the eclipse-safety line). What is and is not to scale is documented here instead.

| shot | to scale / real | not to scale / illustrative |
|---|---|---|
| hook, leave | real lunar and terrestrial maps | sizes and separation of Earth and Moon |
| reflector, ret | array layout follows Apollo 11's LRRR (100 prisms, 46 cm panel); site coordinates on the inset map | the landscape; the green glint (the return is a few photons per pulse, invisible) |
| obs | star positions (real catalogue) | the observatory is generic; the beam is brightened; the Moon is enlarged |
| tides | Moon/Earth size ratio | distance; the bulge (real open-ocean equilibrium tide is well under a metre) and its lead angle; rotation and orbit rates are time-lapse |
| past | counters end at the published values | present-day geography is shown for 70 million years ago |
| origin, ancient | - | artist's impressions throughout; today's lunar map stands in for the unknown early surface; the first oceans postdate the Moon's closest epoch |
| coin | Sun/Moon size ratio in the first panel (Moon = 1/400 of the Sun's width); apparent sizes in the third | the distance line is schematic |
| eclipse, future, annular | disc size ratios (1.035, 0.94, and 1.03 -> 0.985) | lunar limb relief exaggerated ~3x; corona is procedural; the Sun's surface detail is simulated |
| far | Earth, Moon and their separation | the red giant |
| window | future part of the curve (3.8 cm/yr), today's apparent-size range | the past part of the curve is a smooth illustrative law, not a reconstruction |
| shadow | - | shadow size and track approximate |

## Facts and sources (checked with web search, November 2026)
- **3.8 cm per year, by laser ranging:** lunar laser ranging gives about 3.8 cm/yr (recent analyses 3.83 cm/yr). Reflectors: Apollo 11 (1969), Apollo 14 and 15 (1971), Lunokhod 1 (1970) and Lunokhod 2 (1973). (NASA; Sky & Telescope; Eos, *The End of the Eclipse*; IFLScience.) More reflectors have been landed since (e.g. on commercial and Indian landers); the film names only the classic five.
- **Round trip about 2.5 s; a few photons; millimetres:** light time for 2 x 384,400 km is 2.56 s; the APOLLO station at Apache Point detects of order one photon per pulse and reaches millimetre-level range precision (Murphy et al.; quoted from memory of the APOLLO papers, consistent with the search results that describe it as the most precise station).
- **Fingernails:** about 3.5 cm per year is the usual figure for fingernail growth; the film says "roughly".
- **Tides and the day:** tidal friction alone predicts +2.3 ms per century in the length of day; the observed average from eclipse and occultation records, 720 BC to AD 2015, is +1.78 ms per century, the difference being attributed to changes in the Earth's shape since the last ice age and core-mantle coupling (Stephenson, Morrison & Hohenkerk 2016, *Proc. R. Soc. A*). The search in this session did not return the paper itself; the numbers are quoted from memory of it and should be re-checked before publication.
- **70 million years ago:** 372 (+/- 8) days per year, day about 23.5 h, from daily growth layers in the rudist *Torreites sanchezi* (de Winter et al. 2020, *Paleoceanography and Paleoclimatology*; sci.news, phys.org).
- **Devonian:** Wells (1963, *Nature*) counted about 385-410, typically 400, daily growth lines per year in Middle Devonian corals (Digital Atlas of Ancient Life; Paleontological Research Institution). 8,766 h / 400 = 21.9 h. The year itself (the orbit) is assumed unchanged.
- **Origin:** giant-impact hypothesis, about 4.5 billion years ago, Mars-sized impactor. The Moon is thought to have formed just outside the Roche limit, a few Earth radii out (today: 60), i.e. roughly 15-20 times closer; the film says "more than ten times closer" and "more than ten times wider". "May have turned once every few hours" reflects the usual ~5 h estimates for the post-impact day. Standard textbook values, not re-searched individually.
- **The coincidence:** Sun 1,392,000 km across, Moon 3,474 km: ratio 400.7. Mean distances 149.6 million km and 384,400 km: ratio 389. Mean apparent diameters 0.53 and 0.52 degrees; ranges about 31.6'-32.7' (Sun) and 29.4'-33.5' (Moon).
- **Annular vs total today:** in NASA's five-millennium canon annular eclipses (33 %) slightly outnumber total ones (27 %; hybrids 5 %).
- **The last total eclipse:** "about 600 million years from now" (NASA/R. Vondrak, 2017); Sky & Telescope computes that totality becomes intermittent after ~620 million years and gives ~1.2 billion for the very last; other estimates differ. 600 million years x 3.8 cm = 22,800 km. The film says "roughly six hundred million years, though estimates vary" and repeats the caveat on screen.
- **Far future:** tidal locking of the Earth to the Moon would take of order 50 billion years (commonly quoted estimate); the Sun leaves the main sequence and becomes a red giant in about 5 billion years. The Moon does not escape. Standard values, not re-searched individually.
- **Shadow shot:** modelled loosely on the track of 8 April 2024 across Mexico and the United States.

## Deliverables (`out/`, measured)
DELIVERABLES_TABLE

## Honest limitations
- The Earth and the Moon are analytic spheres shaded in numpy from real maps, not volumetric renders: the Moon has slope shading from LOLA elevation but no cast shadows; Earth's clouds are a single static layer and the atmosphere is a fitted limb glow.
- The three Blender stills (reflector array, observatory, fossil coral) are locked-off plates with slow 2D moves, not moving 3D cameras. The observatory is a generic dome, not a model of Apache Point, Grasse or any other real station; its foreground terrain is darkened because the procedural rock did not hold up in close view. The retroreflector follows the Apollo 11 layout but is not an engineering model, and the regolith is a procedural height field.
- The coral is a modelled illustration: about 40 fine ridges per annual band are shown so that they stay visible, where Wells counted about 400.
- Corona, prominences, Sun granulation/spots, the molten early Earth, the debris ring and the red giant are procedural artist's impressions. The eclipse sequence is geometrically driven (beads and diamond come from a rough limb profile), but the limb relief is exaggerated about three times and is not the real lunar profile.
- The sea under the young Moon is a 2.5D reflection model (multi-scale wave slopes, Fresnel reflection of the rendered sky), not a fluid simulation, and the scene is anachronistic by necessity (stated on screen): the Moon was that close before stable oceans existed.
- The "window" chart's past curve is illustrative; only today's values and the constant-rate future are quantitative. The real recession rate has varied (it is faster today than the long-term average) and the Sun slowly brightens and swells, so the date of the last total eclipse is uncertain by hundreds of millions of years.
- Two figures (the 2.3 / 1.8 ms-per-century pair and APOLLO's photon/millimetre performance) were quoted from memory of the primary papers because this session's searches did not return them; the giant-impact, tidal-locking and red-giant numbers are standard textbook values that were not individually re-searched.
- Kokoro reads "Lunokhod" as "LOO-nuh-kod". The 4K file is a lanczos upscale of the 1080p render.
- The horizontal reflector segment was rendered twice (an improved regolith plate replaced the first one).
