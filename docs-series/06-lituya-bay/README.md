# 06 — THE 524-METRE WAVE

5:36 narrated documentary short (1920×1080, 24 fps, 336.0 s) on the Lituya Bay, Alaska, megatsunami of 9 July 1958.
Twilight fjord → the earthquake → the rockslide into Gilbert Inlet → the surge racing 524 m up the facing slope →
true-scale Eiffel Tower / Empire State Building silhouettes → run-up vs wave height → why this was not an ocean tsunami →
the three boats → Miller's trimline → lab models and simulations → modern risk (Taan Fiord, Barry Arm) → the forest grew back, the line remains.

Script, locked timings and shot list: [`SCRIPT.md`](SCRIPT.md).

## Deliverables (`out/`, gitignored)
- `lituya-bay-1080p.mp4` — master: x264 CRF 18 (slow, tune film), AAC 256 kb/s, +faststart, soft English subtitle track.
- `lituya-bay-1080p-hq.mp4` — same picture, CRF 18 capped at 8 Mb/s (for chat delivery, ≤ 380 MB).
- `lituya-bay-4k.mp4` — **3840×2160 lanczos UPSCALE of the 1080p render** (not native 4K detail), CRF 20.
- `lituya-bay-4k-share.mp4` — the same upscale, capped at 10.5 Mb/s (≤ 480 MB).
- `lituya-bay.srt` — subtitles generated from the real placed narration timings.
Sizes / durations: see the table at the bottom.

## Pipeline
| step | file | notes |
|---|---|---|
| narration | `audio/narration.py` | 34 lines, 727 words. TTS spellings: "nineteen fifty-eight", "Tahn Fjord" (Taan), "Ulrick", "Edree", "Sun-more"; phoneme fix for "fjord". |
| voice | `audio/gen_voice.py` | Kokoro-82M v1.0 (kokoro-onnx, offline), voice **am_michael**, speed 0.94 (series voice). Clips trimmed of silence. |
| timeline lock | `audio/timeline.py` → `audio/placement.json` | Line start = previous end + scripted pause × 0.892 so the last word ends at 328.5 s; shot boundaries derived from it. Nothing is time-stretched. |
| world model | `world.py` | **Stylised** Lituya Bay built from distance fields + FFT noise, sized after the real bay (≈11 km main bay, 0.5 km entrance, Cenotaph Island ~4.8 km in, T-shaped head along the Fairweather trench, Gilbert/Crillon inlets with tidewater glaciers, slide on the NE wall of Gilbert Inlet up to ~900 m, run-up field peaking at 524 m on the spur opposite). Also the stylised wave kinematics (arrival time per point). |
| terrain bake | `gen_terrain.py` | numpy: three heightfields (main 1536² over 20×20 km; Gilbert-Inlet patch 1024² over 5×5 km; far range 1024² over 80×62 km) + 4096² emission textures with the twilight lighting baked in (sky dome + afterglow from the computed sun azimuth, ambient occlusion from blurred-height differences, horizon shadowing). Two versions: *forest* (before) and *strip* (trimline zone stripped to grey bare rock / soil + fresh slide scar). Close-range detail: erosion-like spurs and gullies running straight downslope (ridged noise in along-shore / distance-from-shore coordinates, soft-blended between shorelines), scree aprons below cliffs, shaded individual conifer crowns (~2.6 m radius, ~1 per 26 m², lit from the glow side) on the 1.2 m/texel close-up patch, and a light smoothing of the meshes to remove heightmap spikes (patch mesh 1536² ≈ 3.3 m). |
| Blender plates | `scene.py`, `render_plates.sh` | Blender 5.1.2 bpy module, Cycles CPU, 6 spp, 1 glossy bounce, no denoise. Emission-only terrain, near-mirror water (glossy + Fresnel + faint ripple bump), numpy-baked twilight sky (glow towards the sun's azimuth, Earth shadow + Belt of Venus opposite, a few stars). Per camera three 2880×1620 passes: forest, strip, **data** (world xyz in metres + alpha, 1 spp, no pixel filter). 7 cameras. |
| the wave at the boats | `wave.py`, `wave_params.py` | **Real displaced mesh in Blender**, rendered alone (transparent film) for every frame of shot B1 through a camera that reproduces the compositor's crop of the entrance plate (lens = 30 mm × zoom, lens shift = pan). 1400×70-vertex wall: toe → steep dark face → curling lip → crest → turbulent back, ~32 m high with along-front height variation, a front that curves (the centre of the bay leads, it dies out where it reaches the shores); per-vertex foam attribute (crest, streaks running down the face, toe, churn behind) × 4D noise, foam lit towards the twilight glow, Fresnel glossy reflections of the same twilight sky, two translucent animated spray sheets above the crest. 6 spp, 1920×1080. In the compositor, land nearer than the front hides it; the Edrie silhouette (13 m, true scale) rides up the face and is lost behind the lip. |
| map | `gen_map.py` | numpy shaded map of the same world model, north up (the bay axis is drawn at ~45°, as in reality), saved as a pseudo-plate. |
| compositor | `common.py`, `fx.py`, `shots.py`, `run_queue.sh` | python3 + numpy + PIL; each frame is composited and piped straight into x264 (CRF 14 segments). The **data pass makes the wave cheap**: for every pixel the compositor knows its world position, hence its 1958 run-up height, its arrival time and whether it is water, land or the slide scar. The surge is a moving front through that per-pixel arrival-time field (ragged with noise), drawn as dark turbulent water with flow-aligned foam and a bright front, plus screen-space spray; behind it the *strip* plate is revealed (trimline). Splash = 9,000 ballistic particles projected through the real camera matrix. The wall of water at the boats is extruded per screen column from the front line using the projected scale (~32 m face). Silhouettes and labels are projected at true scale through the same camera. No fluid simulation. |
| audio | `audio/mix.py` | voice chain (70 Hz HPF, EQ, 3:1 comp, short room), wind + water lapping, quake rumble, rockslide roar + impact boom, surge wash, the down-bay wave roar, chain crack; numpy pad bed (D minor), 8 dB sidechain ducking, 2-pass loudnorm → −14 LUFS, limiter. |
| final | `assemble.sh` | concat segments → vignette + fine temporal grain → mux audio + mov_text subtitles → 1080p / hq / 4K / 4K-share. |

## Facts and sources (checked Nov 2026)
WebFetch was not reachable from this session (only web search), so facts were cross-checked across search results from several sources.

| claim (on screen / spoken) | source |
|---|---|
| 9 July 1958, ~22:15 local time; magnitude ~7.8 strike-slip quake on the Fairweather Fault (some sources give 7.8–8.3) | Wikipedia "1958 Lituya Bay earthquake and megatsunami"; Alaska Earthquake Center "60 years ago: The 1958 earthquake and Lituya Bay megatsunami" (earthquake.alaska.edu); UAF Geophysical Institute "The giant waves of Lituya Bay" |
| Rockslide ~30 million m³ (40 million yd³; Miller's 30.6 × 10⁶ m³), from a maximum altitude of ~3,000 ft (~900 m) on the NE wall of Gilbert Inlet | Miller, D. J. (1960) *Giant waves in Lituya Bay, Alaska*, USGS Professional Paper 354-C (pubs.usgs.gov/pp/0354c), as quoted by González-Vida et al. 2019 (NHESS 19, 369) and the USGS publication page |
| Run-up 524 m (1,720 ft) on the spur opposite (SW of Gilbert Inlet), the highest wave run-up recorded | Miller 1960; NPS "Taan Fjord landslide and tsunami" table of ≥50 m tsunamis (Lituya Bay 1958, max run-up 524 m); Earth Magazine "Benchmarks: July 9, 1958" |
| Run-up ≠ wave height; lab model wave ~150 m at the headland; model run-up matched the trimline | Fritz, Hager & Minor (2001) *Lituya Bay case: rockslide impact and wave run-up*, Science of Tsunami Hazards 19(1) — 2D model at 1:675 at VAW, ETH Zurich; Fritz, Mohammed & Yoo (2009) PAGEOPH 50th-anniversary review (also a 3D 1:400 model at Oregon State) |
| Later simulations reproduced the run-up | Weiss, Fritz & Wünnemann (2009) GRL (hybrid iSALE modelling); González-Vida et al. (2019) NHESS 19, 369 (Landslide-HySEA); Franco et al. (2020) NHESS 20, 2255 (FLOW-3D, 5 m grid) |
| Wave in the main bay "tens of metres" high; speed estimates >150 km/h | Earth Magazine (~30 m as it spread into the main bay); speed estimates of ~97–130 mph (156–209 km/h) appear in popular summaries attributed to Miller — **hedged** as "by some estimates" |
| Boats: Edrie — Howard Ulrich and his young son Sonny (age given as 7 or 8, so the film says "young son"); let out anchor chain, turned to face the wave; chain snapped; carried toward/over the shore and back; both survived | Miller 1960 eyewitness accounts; Anchorage Daily News 2023 "It looks like the end of the world"; SitNews (Dave Kiffer) "Surviving the biggest wave ever"; Wikipedia "Lituya Bay" |
| Badger — Bill and Vivian Swanson, near the entrance; carried across La Chaussée Spit to sea; sank; escaped in a skiff and were picked up by another fishing boat | USGS account via Wikipedia; Anchorage Daily News 2023 |
| Sunmore — Orville and Mickey Wagner; tried to leave; lost | same |
| Trimline photographed by Don Miller (USGS) soon after; at least four giant waves "during a little more than a century" | Miller 1960 abstract |
| Sun only just set: at 06:15 UTC 10 Jul 1958 at 58.65 N 137.5 W the Sun is ~1° below the horizon at azimuth ~319°, and never goes lower than ~9° below that night (nautical twilight all night) | computed (standard solar-position formulae) |
| Eiffel Tower 330 m (with antennas); Empire State Building 443 m to the antenna tip (381 m roof) | standard reference values |
| Taan Fiord, 17 Oct 2015: ~180 million t of rock at the retreating Tyndall Glacier; tsunami run-up 193 m | Higman et al. (2018) *Scientific Reports* 8, 12993; USGS / NPS summaries |
| Barry Arm, Prince William Sound: unstable slope (~455 million m³ in the 2020 USGS estimate, up to 689 million m³ in the 2021 scenario); worst-case model: >200 m waves near the source and run-up >500 m on the opposite wall; monitored | Dai et al. 2020 (USGS); Barnhart et al. 2021, USGS Open-File Report 2021-1071 (pubs.usgs.gov/publication/ofr20211071); Alaska DGGS statements |
| Glacier retreat can leave steep walls unsupported (debuttressing) | Higman et al. 2018 (framing Taan Fiord as an indirect effect of climate change); USGS Barry Arm reports |

## Honest limitations
- **The terrain is stylised**, built from the bay's real proportions, not from survey data (no DEM was available offline). The map says "STYLISED TERRAIN · NOT TO SURVEY". Mountain walls are rougher/spikier than the real forested slopes; steep faces show some texture stretching.
- The wave is not a fluid simulation (the B1 wall is an animated displaced mesh): it is a stylised front through a run-up/arrival-time field. Event time is **compressed** (×3.2 for the surge, much more for the run down the bay); the film makes no claim about real durations.
- The run-up field is shaped after Miller's trimline map only qualitatively (524 m at the spur, ~100–150 m around the head, tens of metres near the entrance).
- Boat positions are schematic ("near the entrance": Badger and Sunmore near the north shore, Edrie near the south shore). Boats are generic silhouettes at true scale; no likenesses of people.
- The "Miller photograph" is a reconstruction of the stylised terrain graded as a B&W print, labelled "RECONSTRUCTION".
- The speed figure is hedged; the ~150 m wave height is a laboratory-model estimate; Barry Arm is a modelled worst case (hatched bar), not an event.
- 4K files are lanczos upscales of the 1080p render.
- The B1 wall is a cheap displaced mesh (no overturning fluid); its last ~1.5 s are covered by a dark "engulfed" fade as the wave reaches the camera. Spray/foam use procedural noise and show some sampling grain at 6 spp.
- Close terrain still shows some top-down texture stretching on the steepest faces.

## Results (final encode 4 Nov 2026)
| file | duration | size |
|---|---|---|
| `out/lituya-bay-1080p.mp4` | 336.0 s (5:36), 8,064 frames | 608 MB |
| `out/lituya-bay-1080p-hq.mp4` | 336.0 s | 345 MB (≤ 380 MB) |
| `out/lituya-bay-4k.mp4` (upscaled) | 336.0 s | 776 MB |
| `out/lituya-bay-4k-share.mp4` (upscaled) | 336.0 s | 319 MB (≤ 480 MB) |

Audio: −14.1 LUFS integrated, LRA 3.2 LU, true peak −1.1 dBTP (measured with ffmpeg ebur128 on the master). 61 subtitle cues.
Render time (wall clock, on a CPU shared with three other videos, load average 9–30 on 4 cores): terrain bakes ~6 min each,
Blender plates ~1 min per pass (7 cameras × 2–3 passes), Blender wave layer ~355 frames at 8 s–2 min per frame (the last
~40 frames of B1 are covered by the "engulfed" fade and were not needed), numpy compositing ~1 h 45 min across two/three
workers, final encodes ~70 min.
