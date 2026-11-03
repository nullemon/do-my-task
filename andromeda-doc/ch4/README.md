# CH4 — "MILKOMEDA" (3:00–4:00)

60.0 s · 1440 frames · 24 fps · 1920×1080 · Cycles CPU, 2 spp, emission only, AgX Medium High Contrast.
Silent master: `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/ch4.mp4` (libx264 crf 16, preset slow, yuv420p, no grain).

## Files
- `gen_textures.py` — numpy-only texture baker (run once, ~2 min). It writes `ch4_m31.png` (face-on Andromeda with
  dust lanes, star clouds and HII knots), `ch4_tails.png` (two tidal tails with pink tidal-dwarf knots),
  `ch4_burst.png` (sky-wide starburst: arcs of starlight, H-alpha complexes, blue young clusters, dust in alpha),
  `ch4_ell.png` (Sérsic n=4 elliptical with faint interleaved shells) and `ch4_mw.png`/`ch4_stars.png` (not used by the final scene)
  into the shared texture cache.
- `script.py` — the Blender scene. `--frames a,b,c` gives stills. `--render [--skip-existing] [--start --end]` renders the sequence.

The scene has **CH3's sky maps** (`ch3_stars.png`, `ch3_mw.png`, `ch3_m31_L1.png`, `ch3_atmo.png`, `ch3_meta.json`) as an input.
At start-up it also reads `ch3/script.py` read-only (with ast/regex) for CH3's key tables (camera, Andromeda
position, width, brightness, Milky Way warp and the year counter) and its `fbm1`/`ridge`/`tree` builders. Because of this, CH4's first frame
reproduces CH3's last frame: the same stars, the same bent Milky Way, the same Andromeda, ridge, tree and counter, at
camera yaw −9°, pitch 43°, lens 16.5 mm. Run CH3's `gen_textures.py` first.

## Render design (speed)
- One sky dome sphere (emission). Its shader converts the view direction into CH3's alt-az star map and galactic
  Milky Way map. It also converts it into a gnomonic "sky plane" coordinate, where CH4's own textures are placed
  (centre, rotation and scale are maths on Value nodes) and warped. Andromeda gets a tidal twist, an elongation and an S-shear.
- Each layer sits behind a Mix-Shader gate whose factor is a constant 0 or 1. Cycles constant-folds the gates, so a layer that is
  off costs nothing.
- Ridge and tree are black meshes. The captions are Inter Light/ExtraLight text objects on a HUD parented to the camera.
- 2 spp with a fixed seed. Static edges (tree, text) therefore do not flicker.

## Shots / timeline (narration timestamps from `audio/placement.json`)
| t (s) | Narration | Picture |
|---|---|---|
| 0.0 | — | Identical to CH3's last frame: tilted up, giant Andromeda, Milky Way bending. Counter "+ 3.90 BILLION YEARS / IF THEY MERGE". |
| 0.6–8.5 | 1.0 "And yet, almost no stars would collide…" | Slow tilt down to the ridge and the tree. CH3's Andromeda cross-fades (0.8–6.5 s) into CH4's version, which starts to twist and stretch. Tidal tails grow, the Milky Way keeps bending, and the two bright cores start to circle. |
| 9.5–19 | 9.5 "But the clouds of gas would… lighting the sky with newborn stars." | The starburst ignites (9.5–15 s). Pink H-alpha complexes and blue young clusters spread along sweeping arcs across the whole sky, the far ridges are lit pink, and the two cores circle faster. The counter passes **+5 billion years** (5.10 at 19 s). |
| 19–28 | 19.0 "…settle into one great, glowing elliptical galaxy." | The cores merge (~24 s), the burst and the spiral disks fade, and the smooth elliptical with faint shells grows over the tree. The counter reaches +7.00. |
| 28.4–33.9 | 28.0 "…a name for it: Milkomeda." | Caption **MILKOMEDA** (violet accent). The counter fades out at 33–34 s. |
| 34–41 | 34.0 "Our Sun would likely survive…" | Locked-off wide shot: tree under Milkomeda, faint tail remnants. |
| 41–51 | 42.0 "But no one on Earth will see it…" | The camera rises about 90 units and tilts up. The ridge drops out of frame and the airglow fades (into space). |
| 41.5–54 | | Pull-back: the elliptical shrinks to a single galaxy, alone and centred among the stars. |
| 52–55 | 52.0 "Someone, somewhere, may be watching. It won't be us." | The lone galaxy holds. |
| 54.6–56.1 | | Fade to black. |
| 56.35–59.9 | | Title card **THE SKY THAT'S COMING** (Inter ExtraLight) on black, then black. |

## Facts and honesty notes
- The year counter continues CH3's and follows NASA's 2012 illustration sequence for the van der Marel et al. 2012 scenario:
  first pass ~3.9 Gyr, bright starbursts ~4 Gyr, cores merge ~5.1 Gyr, elliptical ~7 Gyr. It always carries **IF THEY MERGE**, because the
  merger is not certain: ~50% within 10 Gyr per Sawala et al. 2025, and ~90% in Wu et al. 2026 (arXiv:2603.22863), whose median is ~6.5 Gyr.
- "Almost no stars would collide": the stars are not shown colliding. The disks pass through each other, and only the gas clouds collide and form stars, shown
  as pink H-alpha knots and blue clusters.
- "Milkomeda" is the popular nickname (Cox & Loeb 2008).
- The remnant is shown as a smooth elliptical with faint shells. Shells are a common signature of mergers, and their brightness is exaggerated so they read on screen.
- The landscape is symbolic. Billions of years from now Earth will not have oceans or trees: the Sun's rising brightness ends liquid
  oceans in ~1 Gyr, as the narration says. The "rise into space" is a camera move, not a real trajectory.
- Sizes and brightnesses of the galaxies in the sky are artistic and loosely based on the NASA illustrations. All textures are procedural
  impressions, not simulation output.

## Render log
1440 frames, 2 spp, 1 thread × 2 processes. The machine was shared with the other chapter renders (load ~8 on 4 cores).
Wall time was ~87 min (10:32–11:59 UTC), averaging 6.4 s per frame per process under contention; uncontended frames measured ~2 s at 2 spp.
The master is 60.000 s and 1440 frames, verified with ffprobe.
