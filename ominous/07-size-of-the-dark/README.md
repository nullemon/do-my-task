# 07 — SIZE OF THE DARK

**Accent colour:** ember red (only the hot Jupiters glow).

An ominous planet size comparison. A black void, one low hard sun from the right. Each world drifts
out of the darkness, dwarfs the last one and pushes it off the frame, while the camera keeps pulling back.
The order goes Mercury → Mars → Venus → Earth → Neptune → Uranus → Saturn → Jupiter. Then comes a pan through
empty darkness ("THEN WE LOOKED AT OTHER STARS."), and three inflated hot Jupiters: TrES-4 b, KELT-9 b
(which glows, being hotter than most stars) and finally **HAT-P-67 b**, the largest-radius planet known.
The camera pulls back one last time. Next to the giant, Earth is a tiny circled dot: **"WE ARE HERE."** Fade to black.

Every body is rendered at **true relative size**. 1 Blender unit = 1 Earth equatorial radius, and an
orthographic camera keeps the scale exact as it zooms.

## What's real (the numbers on screen)

| On screen | Radius | × Earth | Source |
|---|---|---|---|
| MERCURY | 2,439.7 km | × 0.38 | NASA Planetary Fact Sheet |
| MARS | 3,396.2 km | × 0.53 | NASA Planetary Fact Sheet |
| VENUS | 6,051.8 km | × 0.95 | NASA Planetary Fact Sheet |
| EARTH | 6,378.1 km | × 1 | NASA Planetary Fact Sheet |
| NEPTUNE | 24,764 km | × 3.88 | NASA Planetary Fact Sheet |
| URANUS | 25,559 km | × 4.01 | NASA Planetary Fact Sheet |
| SATURN | 60,268 km | × 9.45 | NASA Planetary Fact Sheet (rings to 136,775 km, A-ring edge) |
| JUPITER | 71,492 km | × 11.2 | NASA Planetary Fact Sheet |
| TrES-4 b | 1.838 R_J | × 20.6 | Sozzetti et al. 2015, A&A 575, L15 (GAPS VI), arXiv:1501.06403 |
| KELT-9 b | 1.891 R_J | × 21.2 | Gaudi et al. 2017, Nature 546, 514 |
| HAT-P-67 b | 2.140 ± 0.025 R_J | × 24.0 | Wang et al. 2025, AJ 169, 336, "A Revised Density Estimate for the Largest Known Exoplanet, HAT-P-67 b" (arXiv:2504.13997). The NASA Exoplanet Archive lists the same 2.140 R_J |

All radii are equatorial. The multiples use R_J = 71,492 km and R_E = 6,378.1 km (R_J = 11.209 R_E).
Saturn and Jupiter are drawn with their real oblateness (0.902 and 0.935).
"HOTTER THAN MOST STARS" is KELT-9 b's dayside temperature of about 4,600 K (Gaudi et al. 2017), which is hotter than most stars (red dwarfs).

**Caveats**
- These are **inflated hot Jupiters**. They orbit very close to hot stars and are puffed up by irradiation. They are
  huge in radius but not in mass: HAT-P-67 b has about 0.45 Jupiter masses, with a density near 0.06 g/cm³.
- "Largest planet known" means the largest **measured radius** among **confirmed planets** with precise
  radii. **Brown dwarfs** and objects above about 13 Jupiter masses are excluded. A few poorly constrained or
  unconfirmed candidates have larger quoted radii.
- Published radii differ between papers. TrES-4 b is between 1.71 and 1.84 R_J depending on the analysis.
  HAT-P-67 b was 2.085 R_J in its 2017 discovery paper (Zhou et al. 2017) and 2.140 R_J in the 2025 revision.
  WASP-17 b (about 1.9–2.0 R_J) was left out because its published values disagree more.
- The planet surfaces are procedural artistic impressions, not maps. Nobody has imaged the surface of any exoplanet.
  Showing KELT-9 b and HAT-P-67 b as dark, red-glowing worlds is a stylised take on their hot, low-albedo atmospheres.
- The sun direction is the same for every planet. Distances between them are not to scale; only sizes are.

## How to run

Requirements: Blender 4.2–5.x (or the `bpy` module), numpy, ffmpeg. Uses the Inter Light font if it is
installed (`/usr/share/fonts/opentype/inter/`) and falls back to Blender's default font otherwise.

```bash
# soundtrack (pure numpy) -> soundtrack.wav
python soundtrack.py

# frames (Cycles CPU). Headless Blender:
blender -b -P script.py -- --render
# or with the bpy module:
python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
# options: --frames 1,300,900 (stills)  --start N --end M  --skip-existing  --out DIR

# encode (grain + vignette added here)
ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav \
  -vf "scale=576:1024:flags=lanczos,vignette=PI/4.5,noise=alls=7:allf=t" \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 192k -shortest 07-size-of-the-dark.mp4
```

All settings (fps, resolution, samples, output path, fonts) are in the `CONFIG` block at the top of `script.py`.
The beat timing is in `TIMING`, and `soundtrack.py` mirrors it.

## Posting

**Title:** SIZE OF THE DARK

**Caption:** Mercury to the largest planet ever found, at true scale. Stay for the last one.

**Hashtags:** #space #planets #astronomy #exoplanets #scale #universe #jupiter #nasa #ominous #sizecomparison

**Pinned comment:** All sizes are true to scale. The last planet is HAT-P-67 b, about 2.14 times Jupiter's radius
(Wang et al. 2025). It's a "puffy" hot Jupiter: enormous but lighter than Saturn, and so close to its star that
it's slowly losing its atmosphere. Brown dwarfs aren't counted, since they're not planets. KELT-9 b's day side is about 4,600 K,
hotter than most stars.
