# 10 — THE SKY THAT'S COMING

**Accent colour:** violet-white. **Length:** 52 s, 24 fps, 576×1024.

One night landscape: a black ridge and a single bare, wind-bent tree. Nothing on the ground moves, but a counter
in the sky runs from **NOW** to **+7,300,000,000 YEARS**.
Andromeda starts as a faint smudge beside the Milky Way band. It grows into a spiral that fills the sky.
Then the two galaxies tear each other apart: the disk shears, tidal tails arc across the sky and our own Milky Way
band bends. Pink star-forming knots light up ("but the gas does"). In the end one smooth, glowing
elliptical is left, with faint merger shells: **Milkomeda**. The final line, "Someone will be watching. It won't be us.", is followed by a hard cut to black and silence.

Everything in the sky is a procedural emission shader on a flat plane: a log-spiral galaxy with dust lanes, a
star field built from Voronoi cells, a dusty Milky Way band, tidal-tail arcs and an elliptical with shells. There are no particle sims, lights or volumes.

## On-screen text (in order)

1. ANDROMEDA IS ALREADY / FALLING TOWARD US.
2. 2.5 MILLION LIGHT-YEARS AWAY. / CLOSING AT ~110 KM/S.
3. THAT'S ABOUT 400,000 KM / EVERY HOUR.
4. WILL IT HIT US? / RECENT STUDIES: ~50% TO ~90%.
5. IF IT DOES, / IT WILL FILL THE SKY.  *(the counter now also reads "IF THEY MERGE")*
6. STARS ALMOST NEVER COLLIDE. / THE SPACE BETWEEN THEM IS TOO VAST.
7. BUT THE GAS DOES. / NEW STARS IGNITE.
8. TWO GALAXIES BECOME ONE. / MILKOMEDA.
9. SOMEONE WILL BE WATCHING.
10. IT WON'T BE US.

## What's real

| Claim | Status | Source |
|---|---|---|
| Andromeda (M31) is about 2.5 million light-years away (~770 kpc) | Standard value | van der Marel et al. 2012 / NASA-Hubble release, May 2012 ([ScienceDaily](https://www.sciencedaily.com/releases/2012/05/120531135438.htm), [Astronomy](https://www.astronomy.com/science/hubble-shows-milky-way-is-destined-for-head-on-collision-with-andromeda-galaxy/)) |
| Closing at ~110 km/s | Its radial velocity is −301 km/s relative to the Sun. After removing the Sun's orbit around the Galaxy, that is about −109 km/s relative to the Milky Way's centre. 110 km/s × 3600 s ≈ 396,000 km/h, so "about 400,000 km every hour" | [Wikipedia: Andromeda Galaxy](https://en.wikipedia.org/wiki/Andromeda_Galaxy); Project AMIGA, Lehner et al. 2020 ([arXiv:2002.07818](https://arxiv.org/pdf/2002.07818)) |
| The classic prediction: a direct hit in ~4 billion years, with the merger complete ~2 billion years later | van der Marel et al. 2012 (HST proper motions). The counter's milestones (2, 3.75, ~3.9–4, 5.1 and 7 Gyr) follow NASA's 2012 illustration sequence for that scenario | [Nature News 2012](https://www.nature.com/news/andromeda-on-collision-course-with-the-milky-way-1.10765), [Sci.News](https://www.sci.news/astronomy/article00363.html) |
| **But a merger is NOT certain.** Sawala et al. 2025 used Gaia and Hubble data to model the Milky Way, M31, M33 and the LMC. They found a **~50% chance** of a merger within 10 billion years, and only ~2% within the next 4–5 billion years | Sawala et al. 2025, *Nature Astronomy*, "No certainty of a Milky Way–Andromeda collision" | [National Geographic](https://www.nationalgeographic.com/science/article/milky-way-andromeda-galaxy-collision-odds), [UWA](https://www.uwa.edu.au/news/article/2025/june/astronomers-thought-the-milky-way-was-doomed-to-crash-into-andromeda), [Universe Today](https://universetoday.com/articles/the-hubble-just-cancelled-the-milky-way-andromeda-collision) |
| A 2026 re-analysis using Gaia-based proper motions corrected for systematics raises it again. The fiducial model gives a **~90%** merger probability with a median merger time of ~6.5 Gyr, and the range is 65–100% across the 2σ uncertainty | Wu et al. 2026, "The Fate of the Milky Way–Andromeda System: To Merge or Not?" | [arXiv:2603.22863](https://arxiv.org/abs/2603.22863), [KIAA](https://kiaa.pku.edu.cn/info/1031/11252.htm) |
| Stars almost never collide in a galaxy merger | The distances between stars are enormous compared with their sizes | 2012 NASA/STScI release (above) |
| Gas clouds collide and trigger bursts of star formation; the remnant is likely an elliptical galaxy | Standard merger physics, described in the 2012 release | same |
| "Milkomeda" | A popular nickname for the merged galaxy (Cox & Loeb 2008 used "Milkomeda") | [Avi Loeb](https://avi-loeb.medium.com/when-will-the-milky-way-collide-with-andromeda-28116fd0815f) |
| "It won't be us" | The Sun brightens over time. Earth is expected to lose its oceans in roughly a billion years, long before any merger, and the Sun leaves the main sequence ~5 Gyr from now | general stellar evolution |

**Honesty notes**
- The counter shows **one possible future**. From the "will it hit us?" beat on, a label reads **IF THEY MERGE**.
  The timings follow the classic 2012 scenario. Newer work makes a merger **less certain** (2025: ~50%) or later
  (2026 fiducial: ~90%, median ~6.5 Gyr). The video says **"~50% to ~90%"** and does not claim a merger is certain.
- Andromeda's starting size (~3.2° across, about six full Moons) is roughly to scale. Its brightness is exaggerated so it reads on a phone;
  to the naked eye it is only a faint smudge. Its later sizes are artistic, loosely based on the NASA illustrations.
- The landscape is symbolic. Billions of years from now Earth's surface will be lifeless, and there will be no tree.
- All galaxy textures are procedural impressions, not simulations.

## How to run

Requires Blender 4.2–5.x (or the `bpy` module), numpy and ffmpeg. Uses Inter Light/ExtraLight if
`/usr/share/fonts/opentype/inter/` exists and falls back to Blender's default font otherwise.

```bash
python soundtrack.py                                   # -> soundtrack.wav (48 kHz)

blender -b -P script.py -- --render                    # all 1248 frames
blender -b -P script.py -- --render --skip-existing    # resume
blender -b -P script.py -- --frames 30,400,820         # preview stills
# split across two processes (odd/even frames):
blender -b -P script.py -- --render --skip-existing --start 1 --step 2 &
blender -b -P script.py -- --render --skip-existing --start 2 --step 2 &
# with the bpy module instead of a blender binary:
python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--skip-existing']; exec(compile(open(p).read(),p,'exec'))"

ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav \
  -vf "noise=alls=5:allf=t,vignette=PI/5" -c:v libx264 -preset slow -pix_fmt yuv420p -crf 23 \
  -c:a aac -b:a 192k -shortest -movflags +faststart 10-the-sky-thats-coming.mp4
```

Settings: Cycles CPU, 4 samples, no denoiser (the scene is emission-only, so the only noise is anti-aliasing).
It renders at 576×1024 at 100%. Output goes to the `output` path in the CONFIG block (or `--out DIR`).

## Posting

**Title:** The Sky That's Coming

**Caption:**
Andromeda is 2.5 million light-years away and closing at ~110 km/s. If it hits us, it will fill the night sky,
tear our galaxy apart, and leave one giant elliptical: "Milkomeda". Whether it actually hits is still debated:
recent studies put the odds anywhere from ~50% to ~90%. Either way, nobody here will see it.

**Hashtags:** #andromeda #milkyway #space #astronomy #galaxy #universe #cosmos #science #spacefacts #ominous

**Pinned comment:**
Sources: van der Marel et al. 2012 (HST: ~4 Gyr to first encounter); Sawala et al. 2025, Nature Astronomy
(Gaia+Hubble: ~50% chance of merging within 10 Gyr, ~2% in the next 4–5 Gyr); Wu et al. 2026, arXiv:2603.22863
(updated Gaia motions: ~90%, median ~6.5 Gyr). The ~110 km/s is Andromeda's speed toward the Milky Way's centre
(−301 km/s relative to the Sun). The timeline shown is one scenario, not a certainty. Stars almost never collide, but the gas does.
