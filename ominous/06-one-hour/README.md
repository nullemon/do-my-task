# OMINOUS #6 — ONE HOUR

> "One hour here costs you seven years back home."

A small craft hangs above a black hole. Two clocks run at the bottom of the frame.
**HERE** ticks normally. **HOME** starts at the same rate, then runs faster and faster
as the craft sinks towards the horizon, until each second here equals about 17 hours there.
The camera keeps creeping in. At the end the craft turns its lamp away from us, and the
last lines appear: **1 HOUR HERE / 7 YEARS AT HOME**. Then it cuts to black, which loops
back to the opening line.

Accent colour: gold lensing light. Everything else is black, starlight and off-white type.

## Timeline (26 s, 24 fps, 624 frames)

| t (s) | picture | text |
|---|---|---|
| 0 – 3.6 | wide shot: black hole, lensed disc arcs, craft silhouette with a blinking lamp | **ONE HOUR HERE / COSTS SEVEN YEARS BACK HOME** (visible on frame 0) |
| 3.6 – 22.7 | slow push in, the craft drifts towards the hole | clocks HERE / HOME and "TIME AT HOME RUNS ×N FASTER" |
| 6.4 / 11.2 / 16.2 | — | THE DEEPER YOU SINK · THE SLOWER YOUR TIME RUNS · NEAR A SPINNING BLACK HOLE |
| 4.2 – 19.0 | dilation factor ramps (log-smooth) 1 → 61,000, then holds | HOME clock spins |
| 20.6 – 24.2 | the craft turns; its lamp swings away and dies | — |
| 22.7 – 25.6 | — | **1 HOUR HERE / 7 YEARS AT HOME** |
| 25.6 – 26 | cut to black, silence (loop point) | — |

## Clock maths

`dHOME/dHERE = f(t)`, where `f` ramps from 1 to 61,000. The HOME clock is the integral
(script.py `home_seconds_table`, 32 substeps per frame), so every frame shows the exact
value. HERE shows plain elapsed time. When `f = 61,000`, one second here is
61,000 s ≈ 16.9 h at home. For one hour: 3,600 s × 61,000 = 2.196 × 10⁸ s ≈ **6.96 years**.
During the 19 s of video, HOME advances about 5 days.

## What's real (and what isn't)

- **Gravitational time dilation is real and measured.** Clocks deeper in a gravity well run
  slower. Examples: the Pound–Rebka experiment (1959), GPS satellite clocks (gravity makes them
  gain about 45 µs/day relative to the ground; after the velocity effect the net is about +38 µs/day),
  and optical clocks that detect a height change of about 33 cm (Chou et al., *Science* 2010).
- **A factor of ~61,000 (1 h ≈ 7 yr) is the "Miller's planet" scenario from *Interstellar*.**
  Kip Thorne's *The Science of Interstellar* (2014) explains that it needs a black hole spinning
  within about 1 part in 10¹⁴ of the maximum possible rate, with the observer orbiting extremely
  close to the horizon. For a **non-spinning** black hole, a static hover would need
  `1/√(1 − r_s/r) = 61,000`, which means hovering within ~3 × 10⁻¹⁰ r_s of the horizon.
  The thrust required for that diverges, so it is not survivable. The video therefore says
  "near a spinning black hole". The descent and the hover are dramatised. The factor and the
  arithmetic are not.
- **The look comes from real lensing, not a copied design.** script.py ray-traces photon paths in
  the Schwarzschild metric (Binet equation `u'' = −u + 3Mu²`, RK4) for every pixel of a
  1440×2880 lens map. The far side of the disc is bent up over the hole and down under it.
  The thin photon ring sits at the critical impact parameter b = 3√3 M, and the starfield
  is warped and multiply imaged near the edge of the shadow. The left side of the disc is
  brighter because of relativistic **Doppler beaming** (g³) and gravitational redshift
  (the film deliberately left this out). The disc has a turbulent, Keplerian-sheared texture
  (inner parts orbit faster, Ω ∝ r^-1.5), a gold temperature ramp, and a slight tilt and roll.
  These are original choices.
- Honest simplifications: the image uses a non-spinning metric, although the story says
  "spinning" (a Kerr image would look slightly asymmetric and flattened on one side). The disc
  is opaque and emission-only. The craft is a stylised model. The camera "descent" is a
  push-in on a fixed lens map, so the lensing geometry does not change with distance.

## How to run

```bash
# 1. frames (Blender 4.2–5.x; Cycles CPU, emission-only, ~1.5–2 s/frame on an idle 4-core box)
blender -b -P script.py -- --render                 # -> CONFIG["output_dir"]/f_0000.png …
blender -b -P script.py -- --stills 0,250,600       # test stills
#   (Blender as a Python module:)
python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"

# 2. sound
python soundtrack.py                                # -> soundtrack.wav (48 kHz)

# 3. encode (bloom + grain + vignette + cut to black)
ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav -filter_complex \
 "[0:v]format=gbrp,split[a][b];[b]gblur=sigma=14[g];[a][g]blend=all_mode=screen:all_opacity=0.4,\
  vignette=angle=0.55,noise=alls=7:allf=t,fade=t=out:st=25.6:d=0.12,format=yuv420p[v]" \
 -map "[v]" -map 1:a -c:v libx264 -crf 20 -c:a aac -b:a 192k -shortest 06-one-hour.mp4
```

The lens map takes about 6 s in numpy and is cached as `.npz` in `CONFIG["cache_dir"]`.
Re-runs skip frames that already exist unless you pass `--overwrite`.

## Sound

`soundtrack.py` uses only numpy and writes a 26 s stereo track at 48 kHz:
- an A1 drone that sinks a semitone during the descent, over a dark wind bed
- sub-bass swells with soft felt hits on the hook, each text beat and the finale
- a quiet tick once per second for **HERE**
- **HOME** ticks that accelerate with the dilation factor and then smear into a thin
  rising shimmer, which collapses when the ship turns away
- silence at the cut

## Posting

**Title:** ONE HOUR

**Caption:** One hour here. Seven years at home. Near a rapidly spinning black hole, gravity
slows time by a factor of ~61,000. Every clock you left behind keeps running.

**Hashtags:** #blackhole #timedilation #relativity #space #astrophysics #physics #interstellar #einstein #ominous #sciencefacts

**Pinned comment:** Real physics: clocks deeper in gravity really do run slower. GPS satellites
correct for it every day. A ratio of 61,000 (1 h ≈ 7 yr) needs an orbit just above the horizon
of a black hole spinning at almost the maximum possible rate. Kip Thorne worked this out for
Miller's planet in *Interstellar*. You can't simply hover there: near a non-spinning hole the
thrust needed would be infinite. The black hole in this video is ray-traced from general
relativity. The brighter left side is Doppler beaming from gas moving towards you at a large
fraction of light speed.
