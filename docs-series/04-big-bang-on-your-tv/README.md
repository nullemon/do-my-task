# 04 — THE BIG BANG IS ON YOUR TV

4:30 narrated documentary short (1920×1080, 24 fps, 270.0 s). Nostalgic + mind-blowing: a CRT glowing with
snow in a dark room → "Some of this static is left over from the Big Bang" → the cosmic microwave background
story → the TV is switched off, the last dot fades → "The oldest light in the universe. And we used to just change the channel."

Script, locked timings and shot list: [`SCRIPT.md`](SCRIPT.md).

## Deliverables (`out/`, gitignored)
See the report table at the bottom (sizes / durations filled after the final encode).
- `bigbang-tv-1080p.mp4` — master: x264 CRF 18 (slow, tune film), AAC 256 kb/s, +faststart, soft English subtitle track (off by default).
- `bigbang-tv-1080p-hq.mp4` — same picture, CRF 18 capped at 10 Mb/s (for chat delivery, ≤ 380 MB).
- `bigbang-tv-4k.mp4` — **3840×2160 lanczos UPSCALE of the 1080p render** (not native 4K detail), CRF 20.
- `bigbang-tv-4k-share.mp4` — the same upscale, capped at 13 Mb/s (≤ 480 MB).
- `bigbang-tv.srt` — subtitles generated from the real placed narration timings.

## Pipeline
| step | file | notes |
|---|---|---|
| narration text + pronunciation | `audio/narration.py` | 29 lines, 499 words. Dates spelled for TTS ("nineteen sixty-four"…), "Dicke" → "Dicky", COBE → "Koh-bee", WMAP → "W-map". |
| voice | `audio/gen_voice.py` | Kokoro-82M v1.0 (kokoro-onnx, offline), voice **am_michael**, speed 0.94 (series voice). Clips trimmed of silence. |
| timeline lock | `audio/timeline.py` → `audio/placement.json` | Line start = previous end + scripted pause × 1.31, so speech ends at 263.0 s; shot boundaries derived from it. Nothing is time-stretched. |
| room plates | `room.py`, `render_plates.sh`, `render_plates_dn.sh` | Blender 5.1.2 (bpy module), Cycles CPU. Two cameras × three *linear* passes saved as float16 .npy at 2880×1620: moonlight only, TV-light only (screen invisible to camera), screen UV. Light passes: 16 spp + OpenImageDenoise (albedo/normal guided); the UV/mask pass is never denoised. |
| horn antenna | `gen_sky.py`, `horn.py`, `render_horn.sh` | Stylised horn-reflector: long square pyramidal horn with a flared profile and 12 stiffening frames, reflector hood with the side aperture, elevation wheel, receiver cab, turntable pad + circular rail. Weathered-aluminium shader (metallic, noise-varied roughness, grime streaks, panel seams), painted-steel structure; night lighting with a low moon behind-left giving a cold rim, faint warm horizon, cab lamp. Three 4K stills (12 spp + OIDN) for 2D moves + a 41-key 3D orbit (1280×720, 6 spp + OIDN, cross-blended in-betweens, upscaled). |
| compositor | `common.py`, `tv.py`, `cosmos.py`, `shots.py`, `run_queue.sh` | python3 + numpy + PIL; every frame is composited in numpy and piped straight into x264 per shot (no PNG sequences on disk). |
| audio | `audio/mix.py` | voice chain (70 Hz HPF, EQ, 3:1 comp, short room), analog hiss + crackle, very quiet 15.734 kHz line whine, power-off click/thump/zap, numpy pad bed, 8 dB sidechain ducking, 2-pass loudnorm → −14 LUFS, limiter. |
| final | `assemble.sh` | concat segments (stream copy) → vignette + fine temporal grain → mux audio + mov_text subtitles → 1080p / hq / 4K / 4K-share. |

### How the TV works (cheap but convincing)
- **Snow** (`tv.static_tex`): a new 1280×480 field every frame — Gaussian noise smeared along the scan line (band-limited, as in a real
  receiver), a little line-to-line level jitter, impulse streaks, a slow rolling darker band, a gamma that makes white flecks pop.
- **In the room**: the UV pass maps the snow onto the bulged screen (rounded picture corners, edge falloff, glass highlight);
  the room is `moon_pass × 0.26 + tv_light_pass × (3.1 × mean snow brightness)`, so the room flickers with the picture, plus bloom.
- **Close-up**: barrel-curved 4:3 glass, scan-line profile and an RGB aperture grille whose contrast fades in only when the zoom makes
  them resolvable (no moiré).
- **Switch-off**: the picture collapses vertically to a bright line (energy-conserving gain), then horizontally to a dot that decays
  with a phosphor-like exponential; the TV-light pass goes to zero, leaving the cold moonlight.

### The early universe
- Plasma: periodic FFT noise fields; ~700 protons, 800 electrons, 520 photons. Photons random-walk (frequent scattering = opaque
  fog), then at recombination each electron is pulled onto a proton at its own random moment, scattering drops to zero and photons
  stream in straight lines; the fog dims to a translucent orange glow.
- Stretching: the wave's on-screen wavelength and the comoving grid grow with (stretch)^0.33 (the true ×1,100 cannot fit on screen);
  colour = blackbody colour at the current temperature, brightness falls off below ~800 K; below that the wave is drawn as a dashed
  "invisible" trace. HUD numbers are physical: T = 3000 K / stretch, Wien peak λ = 2.898 mm·K / T (0.97 µm → 1.06 mm).
- Sky map: an isotropic random field on the sphere (sum of 700 plane waves evaluated on unit vectors), Planck-like colour map,
  rotating globe → Mollweide. **Labelled on screen "ARTIST'S IMPRESSION · NOT REAL SATELLITE DATA"** — the statistics are only
  roughly CMB-like and there is no Galactic foreground.

## Facts and sources (checked Nov 2026)
| claim (on screen / spoken) | source |
|---|---|
| Light released ~380,000 years after the Big Bang at ~3,000 K, when atoms formed and the universe became transparent; z ≈ 1100 | PlanetPhysics / Wikiversity CMB summary https://en.wikiversity.org/wiki/PlanetPhysics/Cosmic_Microwave_Background_Radiation ; Wikipedia "Cosmic microwave background" |
| Today 2.725 K (2.72548 ± 0.00057 K); FIRAS/COBE blackbody | same; Fixsen 2009 |
| Anisotropies ~1 part in 100,000 (rms ~18 µK) | same |
| ≈ 400 CMB photons per cm³ | standard result n = (2ζ(3)/π²)(kT/ħc)³ ≈ 411 cm⁻³ at 2.725 K (computed) |
| "about one percent" of the snow | widely repeated popular figure (e.g. Big Think "How to prove the Big Bang with an old TV set"); a Skeptics StackExchange thread and a 2012 physics-teacher (phys-l) discussion note it was never rigorously measured and is likely ≲ 1% for rabbit ears. **Hedged in narration and on screen.** https://kiwix.lema.org/skeptics.stackexchange.com_en_all_2023-11/questions/5264/ ; https://www.phys-l.org/archives/2012/3_2012/msg00191.html |
| Most snow is receiver/thermal noise, man-made transmissions, the Sun | same sources |
| Penzias & Wilson, Bell Labs Holmdel horn, 1964; ≈ 3.5 K excess antenna temperature at 4,080 MHz; 1965 ApJ Letters 142, 419; Dicke, Peebles, Roll & Wilkinson companion letter in the same issue | https://en.wikipedia.org/wiki/Discovery_of_cosmic_microwave_background_radiation ; https://apc.u-paris.fr/~ganga/CMB/PenziasAndWilson.html ; https://www.cambridge.org/core/books/3k-the-cosmic-microwave-background-radiation/measurement-of-excess-antenna-temperature-at-4080-mcs/28210077E85241B884BB87D24E9BDC26 |
| Pigeons in the horn; "white dielectric material" (Penzias's phrase as recalled by Wilson); the hiss stayed after cleaning | Slate/Atlas Obscura 2013 https://www.slate.com/blogs/atlas_obscura/2013/09/16/how_the_holmdel_horn_antenna_in_new_jersey_changed_our_understanding_of.html ; arXiv:1506.01907. (Accounts differ on the pigeons' fate — mailed away / returned / shot — so the film only says "evicted".) |
| Horn built for Project Echo (1960) | APS historic site https://www.aps.org/funding-recognition/historic-sites/holmdel-horn-antenna ; Atlas Obscura |
| "Boys, we've been scooped" — Dicke | APS historic site ("well boys, we've been scooped"); wording varies, so captioned "as recalled by his colleagues" |
| Princeton ≈ 40 km from Holmdel | straight-line distance from coordinates (40.37 N 74.18 W → 40.35 N 74.66 W) ≈ 41 km |
| Nobel Prize in Physics 1978 to Penzias & Wilson (shared with Kapitsa for unrelated work) | nobelprize.org; Boston Globe obituary 2024 |
| COBE launched 1989, WMAP 2001, Planck 2009 | NASA/ESA mission pages |
| US full-power analog shut-off 12 June 2009 (low-power analog continued for years) | https://en.wikipedia.org/wiki/Digital_television_transition_in_the_United_States |
| UK switchover completed 24 October 2012 (Divis transmitter, Northern Ireland) | https://www.gov.uk/government/news/on-time-and-under-budget-an-all-digital-uk ; https://www.advanced-television.com/2012/10/24/uk-ends-analogue-era |

## Honest limitations
- The "1 %" is a folk number — said as "often quoted … never precisely measured".
- The horn antenna is a stylised reconstruction, not an accurate model; no people are depicted.
- The sky map is procedural and labelled as an impression; the "galaxies condensing" moment is an illustration of the idea that
  denser regions grew into structure, not a simulation.
- On-screen wavelength stretching is compressed (∝ stretch^0.33); the HUD gives the real factor.
- The 3D orbit is 41 rendered (denoised) key frames cross-blended over 10 s (the move is slow, so blending is subtle) and upscaled from 1280×720.
- "Someone turns the TV off" is conveyed by sound (switch click) and the CRT collapse; no hand is shown.
- 4K files are lanczos upscales of the 1080p render.
- Narration is 499 words (slightly under the 550–650 guideline) with generous pauses; the film is exactly 270 s.
