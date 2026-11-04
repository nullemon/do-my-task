# 03 — YOU ARE NOT SITTING STILL

A 4:30 narrated documentary short (1920×1080, 24 fps, 270.0 s). A stylised figure sits perfectly still by a
window at night; the camera pulls back level by level (room → spinning Earth → orbit → the Sun's helical
path → the Milky Way → the Local Group and the cosmic web) while speed counters stack up and a running
counter shows how far the viewer has travelled since the video began. It ends back in the still room:
"You've never been still. Not for one second." with the final distance (≈ 99,800 km) on screen.

Narration, timings and shot list: [`SCRIPT.md`](SCRIPT.md).

## Files
| Path | What |
|---|---|
| `audio/narration.py` | narration lines (scene, pause, text) |
| `audio/gen_voice.py` | Kokoro TTS, voice **am_michael**, speed 0.94 (same voice as the series) |
| `audio/timeline.py` → `audio/timeline.json` | locks the timeline to the measured voice clips (pauses scaled to fill 270 s) |
| `audio/mix.py` | voice processing, numpy music bed, ducking, two-pass loudnorm, SRT |
| `visuals/earth_blender.py` | Blender 5.1 / Cycles CPU: one seamless 288-frame Earth rotation (RGBA) |
| `visuals/gen_assets.py` | pre-baked 2D plates: room, window sky, horizon, deep-space stars, CMB all-sky map |
| `visuals/compose.py` | numpy/PIL compositor: all 3D projection scenes, transitions, captions, live counters |
| `visuals/png16.py` | reader for the 16-bit galaxy textures reused from `andromeda-doc/ch2` |
| `visuals/render_parts.sh`, `assemble.sh` | detached part renders (resume/skip-existing) and final encodes |
| `you-are-not-sitting-still.srt` | subtitles from the real placed narration timings |
| `out/` | final MP4s (gitignored) |

Big intermediates live in `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still/`.

## Facts on screen / in the narration (and how they are hedged)
| Claim | Value used | Notes / source |
|---|---|---|
| Earth's rotation at the equator | ≈ 1,670 km/h | 40,075 km / 23.93 h (sidereal day) = 1,674 km/h |
| Depends on latitude | 1,670 × cos(lat); London (51.5° N) ≈ 1,040 km/h; poles ≈ 0 | geometry |
| Earth around the Sun | 29.8 km/s ≈ 107,000 km/h | mean orbital speed 29.78 km/s |
| London → New York in ~3 min | 5,570 km / 29.8 km/s ≈ 3.1 min | |
| Sun around the Milky Way | ≈ 230 km/s ≈ 828,000 km/h | estimates ≈ 220–240 km/s; Live Science "How long is a galactic year?" |
| One lap | ≈ 230 million years (on screen: estimates 225–250 Myr) | Live Science; galactic-year literature |
| Dinosaurs | "the last time the Sun was at this point in its orbit, the first dinosaurs were only just appearing" | earliest undisputed dinosaurs ≈ 231–233 Ma (Late Triassic, Carnian); older contested candidates ≈ 243–245 Ma (Bernardi et al. 2018, *Nat. Commun.* 9:1499). The brief's "dinosaurs hadn't appeared yet" is only true for the long end (≈ 250 Myr) of the galactic-year range, so the wording was softened. |
| Vertical bobbing | crosses the disk "every thirty million years or so"; swing ≈ ±80 pc (shown ×10) | period ≈ 63–66 Myr ⇒ a crossing every ≈ 30–35 Myr; amplitude ≈ 50–100 pc (Bahcall & Bahcall 1985, *Nature* 316:706; Gies & Helsel 2005, astro-ph/0503306) |
| Planets' plane vs the galaxy | ≈ 60° | ecliptic ↔ galactic plane ≈ 60.2°; the direction of galactic rotation is also ≈ 60° from the ecliptic plane. The "vortex" video is wrong about planets trailing the Sun (Phil Plait, "No, our solar system is NOT a vortex") |
| Helix proportions | the Sun moves ≈ 48 AU per year; Earth's orbit is 2 AU across | 230 km/s × 1 yr = 7.3×10⁹ km = 48.5 AU. Drawn to these true proportions (no exaggerated vortex). |
| Sun relative to the CMB | ≈ 370 km/s ≈ 1.33 million km/h | 369.82 ± 0.11 km/s toward (l, b) = (264.0°, 48.3°) (Planck 2018; COBE 369 ± 2.5 km/s, Kogut et al.) |
| CMB dipole | "≈ 0.1 % warmer ahead" | 3.36 mK / 2.7255 K ≈ 0.12 %; the inset's colours are exaggerated (labelled) |
| Local Group relative to the CMB | ≈ 600 km/s ≈ 2.2 million km/h | 627 ± 22 km/s toward (l, b) = (276°, 30°) (Kogut et al. 1993; CMB mini-review arXiv:1005.0555) |
| "drawn toward … the Great Attractor, and beyond it, the Shapley Supercluster" | GA ≈ 200 Mly (Norma region ≈ 65–70 Mpc), Shapley ≈ 650 Mly (≈ 200 Mpc) | the split between the two is debated (Erdoğdu et al. 2006: ~44 % GA infall, ~56 % more distant structure; Kocevski & Ebeling 2006, astro-ph/0510106). Narration says "drawn toward", map labelled "directions approximate" |
| Not a simple sum | stated in narration and on screen | velocities are vectors |
| Distance counter | 369.82 km/s × elapsed time; ≈ 99,800 km at 4:30 | clearly labelled as the Sun's speed relative to the CMB. Earth's own orbital motion (±30 km/s, up to ±8 %, averaging out over a year) and spin (≤ 0.5 km/s) are ignored |
| A quarter of the way to the Moon | 99,800 / 384,400 ≈ 26 % | |
| Why we don't feel it | constant velocity: Galileo's ship (*Dialogue*, 1632), Newton's first law (1687) | honesty note on screen: Earth's spin does curve your path, ≈ 0.034 m/s² at the equator ≈ 0.35 % of g |

## Visual honesty notes
- The figure is a generic, stylised silhouette (no likeness). The room's star drift is decorative.
- Earth: NASA Blue Marble + NASA night-lights maps (public domain imagery, shipped in the `three-globe` npm
  package examples). Rotation is a labelled time-lapse (one day in 12 s); the terminator does not move
  during the loop (Sun direction fixed).
- Solar system: orbits are circular, to scale relative to each other; Sun and planet dots enlarged (labelled).
  The galaxy-frame helix uses the true ratio of the Sun's speed to the planets' orbital speeds.
- Milky Way: an illustration (procedural face-on spiral from andromeda-doc ch2), not a map; the Sun's
  position/arm placement is schematic. Bobbing exaggerated ×10 (labelled).
- Local Group: true distances (Andromeda ≈ 770 kpc), galaxies drawn 3× true size (labelled).
- Cosmic web: procedural and illustrative; only the directions/distances of the Great Attractor and Shapley
  regions and the Local Group's motion vector are taken from data, and approximately.
- 4K files are lanczos **upscales** of the 1080p render, not native 4K.

## Render / pipeline notes
- Earth loop: 288 frames, Cycles CPU 3 spp, 0 bounces, 2 threads: ≈ 19 min (≈ 4 s/frame on the shared box).
- Compositor: 6,480 frames in 27 ten-second parts (2–3 detached workers, skip-existing): ≈ 2.9 h of
  worker wall time in total (≈ 1.6 s/frame while 4 videos shared 4 cores; ≈ 0.5–1 s/frame unloaded).
  Only the Earth needed Blender; everything else is projected/splatted in numpy, so no 3D frames were
  stored (disk on the shared machine was down to ≈ 3 GB).
- Audio: Kokoro am_michael @ 0.94, 26 clips, pauses scaled ×1.43 so the voice fills 270 s with a 10 s tail;
  70 Hz HPF, light EQ, 3:1 compression, small room reverb; numpy pad/drone/choir bed in D minor that adds
  a layer at each pull-back and lifts to D major on "You've never been still"; sidechain duck 8 dB;
  two-pass loudnorm → −14.0 LUFS integrated, −1.5 dBTP. The ducking envelope uses an O(N) moving sum
  (the original np.convolve version took > 10 min).
- Final (after a container restart killed the first encode): `visuals/final.sh` makes the graded 1080p master
  from the joined parts (vignette + temporal luma grain, x264 crf 18 preset medium, AAC 256k, soft English
  mov_text subtitles, +faststart), then `visuals/assemble2.sh` derives the rest from that master:
  - `-1080p-hq.mp4` is a **hard link to the master**: at crf 18 it is already 290 MB (< 380 MB), so
    re-encoding could only lose quality.
  - `-4k-share.mp4` is a lanczos upscale at 12 Mb/s (413 MB).
  - `-4k.mp4` is a lanczos upscale at crf 21, capped at 22 Mb/s because disk on the shared box was down
    to about 1.4 GB (441 MB). Both 4K files are **upscaled** and have no native 4K detail.
- Verified: all four files are 270.000 s with 6,480 frames, video + AAC + subtitle streams; −14.0 LUFS
  integrated, −1.2 dBTP after AAC.

## Deliverables (`out/`)
| File | Size | Notes |
|---|---|---|
| `you-are-not-sitting-still-1080p.mp4` | 290 MB | master, 1920×1080 |
| `you-are-not-sitting-still-1080p-hq.mp4` | 290 MB | hard link to the master (≤ 380 MB) |
| `you-are-not-sitting-still-4k.mp4` | 441 MB | 3840×2160 lanczos upscale |
| `you-are-not-sitting-still-4k-share.mp4` | 413 MB | 3840×2160 upscale, ≤ 480 MB |

Rebuild:
```
/home/user/ttsenv/bin/python audio/gen_voice.py && /home/user/ttsenv/bin/python audio/timeline.py
/home/user/ttsenv/bin/python audio/mix.py
/usr/bin/python3 -I visuals/gen_assets.py
/home/user/bpyenv/bin/python visuals/earth_blender.py -- --render --skip-existing
bash visuals/render_parts.sh "$(seq -s ' ' 0 26)"
# concat the parts into joined.mp4 (first half of visuals/assemble.sh), then:
bash visuals/final.sh      # 1080p master + assemble2.sh (hq / 4K)
```
