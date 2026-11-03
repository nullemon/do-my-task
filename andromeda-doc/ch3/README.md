# CH3 — "THE SKY CHANGES" (2:00–3:00)

60.0 s, 1440 frames, 1920×1080, 24 fps. This is a silent master; grain and vignette are added at final assembly.
The chapter shows the ridge and the lone wind-bent tree while billions of years pass. A counter at the top
centre runs from **+ 1.00** to **+ 3.90 BILLION YEARS**, with **IF THEY MERGE** underneath. Andromeda grows from a small
oval into a tilted spiral that spans the sky. Its dust lanes, ring of star formation, pink HII knots, core and
satellites M32 and M110 are all visible. Near the horizon it reddens from atmospheric extinction and rises
behind the ridge. Our own Milky Way band then bends toward it. The chapter ends on a slow tilt up toward the zenith, where the two galaxies cross.

## Files
- `gen_textures.py` is the numpy-only texture baker. Run it once (about 1 min). It writes to
  `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures/ch3_*`:
  - `ch3_m31_L0..L4.png`: Andromeda, pre-inclined at ~72.5°. L0 is 8192×3072 (LODs down to 512 px). It has a
    tightly wound two-arm spiral, the 10 kpc "ring of fire" and an inner ring, and feathered dust lanes on the inner arm edges. Dust is silhouetted
    against the bulge on the near side. The disk is warm inside and bluer outside, and has HII and OB knots. The texture also includes M32 and M110.
  - `ch3_stars.png`: an alt-az star map at 26 px/deg (~100k stars with a magnitude distribution plus a faint dust of stars,
    denser toward the Milky Way plane).
  - `ch3_mw.png`: the Milky Way in galactic (l, b) coordinates at 20 px/deg. It has the bulge, star clouds, the Great Rift
    and unresolved-star grain. Alpha holds the dust opacity, so our galaxy's dust dims Andromeda where the two overlap.
  - `ch3_atmo.png`: a LUT over altitude for extinction/reddening and a faint violet airglow.
  - `ch3_meta.json`: the encoding constants and the Milky Way's orientation on the sky.
- `script.py` is the Blender scene and render loop (Cycles CPU, 2 spp, no denoise, no lights).

## Run
```bash
cd /home/user/do-my-task/andromeda-doc/ch3
/home/user/bpyenv/bin/python gen_textures.py
# preview stills
CH3_SPP=2 /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--frames','120,550,880,1120,1430','--threads','2']; exec(compile(open(p).read(),p,'exec'))"
# full render (resumable), split into two contiguous halves
CH3_SPP=2 setsid nohup /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing','--start','1','--end','720','--threads','1']; exec(compile(open(p).read(),p,'exec'))" &
CH3_SPP=2 setsid nohup /home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing','--start','721','--end','1440','--threads','1']; exec(compile(open(p).read(),p,'exec'))" &
ffmpeg -framerate 24 -i frames/f_%04d.png -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p ch3.mp4
```

## How it renders fast
- The whole sky (stars, Milky Way, Andromeda, airglow and extinction) is one emission shader on a sky-dome sphere.
  Andromeda is not a plane. The shader projects the view direction onto the galaxy's tangent plane (gnomonic) and
  looks it up in the texture. Two LOD levels are blended by on-screen size, because Cycles has no mipmaps.
- Animated values are **object custom properties read by Attribute nodes**. With Value nodes, every change
  recompiled the shaders, which cost about 4 s per frame. After setting the properties, the objects are tagged for update; persistent data misses the change otherwise.
- Textures are 8-bit sRGB of L/Lmax, so Blender decodes them for free.
- Measured cost: ~3 s/frame per CPU thread at 2 spp. On this shared 4-core box that is ~1.5–2 s/frame of wall time with
  two single-thread processes. The time is spent on per-ray cost in Cycles (a trivial dome alone costs ~0.6 s per spp per thread), not on texture work.

## Shots and timing (chapter seconds; narration from audio/placement.json)
| t | narration | picture |
|---|---|---|
| 0–1.4 | — | fade up from black on the wide locked-off ridge shot (20 mm). Andromeda is an 8° oval upper right and the Milky Way glows at the left edge. Counter + 1.00 BILLION YEARS |
| 1.0 | "In about two billion years, it would no longer be a smudge." | counter reaches +2.00 at 5 s; Andromeda grows to ~15° with a visible core and arms |
| 8.0 | "Night after night, nothing would seem to change…" | the counter ticks slowly (2.03→2.10) and the sky holds still |
| ~11 | "…it would swell." | Andromeda swells from 17° to 34° by 17 s |
| 17.0 | "Its spiral arms, its dark lanes of dust, its glowing core…" | slow push-in (20→30 mm) on the galaxy: dust lanes, HII knots, core, M32/M110 |
| 25–31 | "Some four billion years from now, it could fill the sky…" (26.0) | pull back to a wider lens (17 mm) as it balloons to ~112° across, tilted and hanging over the ridge, reddened at the horizon. The tree is silhouetted against it. Counter +3.60 at 32 s, +3.75 at 36 s |
| 37.0 | "Then our own Milky Way would begin to bend…" | the camera pans left to the Milky Way band, which bends toward Andromeda in an S-shaped tidal warp and thickens. Its dust lanes cross in front of Andromeda |
| 47.0 | "Two galaxies… falling into one another." | slow tilt-up (pitch 15°→43°) toward the zenith. The warped Milky Way arches overhead across Andromeda's arms. The counter ends at +3.90 |

Captions: only the year counter and "IF THEY MERGE" (Inter Light, widely tracked), as PLAN.md specifies.

## Facts and honesty notes
- Milestones follow the classic van der Marel et al. 2012 / NASA illustration sequence (2 Gyr: clearly larger;
  3.75 Gyr: fills the sky; first passage ~3.85–3.9 Gyr). That is **one possible future**. The label "IF THEY MERGE"
  stays on screen throughout. Sawala et al. 2025 give ~50% within 10 Gyr, and Wu et al. 2026 ~90%, with a median of ~6.5 Gyr, so the real timing
  could be later.
- Angular sizes are artistic, loosely based on the NASA 2012 illustrations. Today M31 is ~3.2° across; here it starts
  at 8° at +1 Gyr.
- **Brightness is exaggerated.** Surface brightness does not increase as a galaxy approaches, so a real
  Andromeda would grow but stay faint. The narration's "visible to the naked eye" refers to its size and structure. Our film
  makes it vivid so it reads on screen.
- The Milky Way warp is an artistic impression of tidal distortion, not a simulation. From inside the disk, the
  real distortion would show up as a slow change over hundreds of millions of years.
- The landscape is symbolic: Earth's oceans are expected to be lost within ~1 Gyr as the Sun brightens, so no tree would stand here.
- All textures are procedural (numpy). They are impressions, not data. The orientation and position angle of M31 and the band are chosen for composition.

## Render log (this delivery)
- 1440 frames, Cycles CPU 2 spp. Two single-thread processes ran 10:26 to 11:41 UTC (~75 min wall), at 3.5 to 6.5 s/frame per process
  depending on load from the other chapters' renders (≈1.75 to 3.2 s/frame of wall time).
- Master: `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/ch3.mp4`
  (libx264 crf 16 slow, yuv420p, no grain): 1440 frames, 60.000 s.
