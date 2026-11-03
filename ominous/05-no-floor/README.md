# OMINOUS #5 — NO FLOOR

**Hook (first second):** "Jupiter has no surface. This is what falling in looks like."

A 28-second vertical (9:16) fall through Jupiter's cloud decks. We start above sunlit
ammonia-ice cloud tops with a hazy horizon, sink through the ochre ammonium
hydrosulfide layer as the sunlight fails, into the dark water-cloud deck where
violet lightning flickers inside the clouds, past the depth where the Galileo probe
went silent, and keep falling. A HUD counts pressure, temperature and depth. The
last lines are "NO SURFACE." / "JUST PRESSURE." / "NO FLOOR.", over a faint glow of
>1000 K gas rising from below. Accent colour: storm violet.

## What's real

- **No solid surface.** Jupiter is mostly hydrogen and helium. Going down, the gas just
  gets denser and hotter and turns gradually into a supercritical fluid. Thousands of
  kilometres down the hydrogen becomes metallic. "Altitude zero" is a convention: the
  **1-bar level**.
- **Cloud layers** (from equilibrium cloud-condensation models, e.g. Weidenschilling & Lewis 1973,
  Atreya et al. 1999): **ammonia ice ~0.5–1 bar**, **ammonium hydrosulfide (NH₄SH) ~1.5–3 bar**,
  **water ice/water clouds ~5–7 bar**.
- **Lightning:** detected by Voyager, Galileo and Cassini, and mapped in detail by **Juno**
  (Brown et al. 2018, *Nature*). Most of it is thought to come from the water-cloud
  level. Juno also found shallow "sprite"-like and higher-altitude lightning
  (Becker et al. 2020).
- **Galileo probe, 7 Dec 1995:** it transmitted for about 58 minutes and reached
  about **22 bar and about 425 K (152 °C)**, roughly **130–150 km below the 1-bar level**,
  before the signal was lost (Seiff et al. 1998, *JGR*).
- Pressure rises continuously to **thousands of bar** and far beyond (millions of bar near
  the metallic-hydrogen region).

### HUD model (the numbers on screen)
The HUD numbers are **computed**, not typed in. They come from a simple model:

- **Temperature:** a dry adiabat fitted to the Galileo probe,
  `T(P) = 166 K · P^0.305` (P in bar). This gives 166 K at 1 bar and about 427 K at
  22 bar, which matches the probe. It is clamped at about 110 K (the tropopause minimum)
  above the cloud tops.
- **Depth:** hydrostatic integration of that adiabat,
  `z(P) = −(H₀/κ)(P^κ − 1)` with `H₀ = R·T₀/(μ·g)`, μ = 2.31 g/mol, g = 23.1 m/s², κ = 0.305
  (H₀ is about 26 km). This puts 22 bar about 133 km below the 1-bar level. Seiff et al.
  measured about 132 km.
- Pressure follows a story curve from 0.25 bar to about 2,000 bar over 28 s, and the
  temperature and depth readouts are derived from it. Beyond 22 bar the model is
  **extrapolated**. It gives about 1,360 K and about 610 km at 1,000 bar. Real models
  run a few hundred K hotter there because the adiabatic exponent changes (H₂
  vibrational modes, non-ideal gas), so the deep readouts are order-of-magnitude, not
  precise.

Artistic liberties: camera speed and cloud spacing are compressed for pacing. The
clouds are stylised (layered planes, not a simulation). The lightning colour is
stylised violet. The faint ember glow at the bottom is a nod to thermal emission
from >1000 K gas, not a rendering of a measured feature.

## How it was made / how to run

- `script.py`: a single procedural Blender script (Cycles CPU, no downloads). The clouds
  are about 70 stacked emission/transparent planes, shaded with tileable FFT noise
  generated in numpy. They have fake relief lighting, depth haze, edge-on fade and a
  3D lightning falloff around an empty. There are no lights and no volumetrics, so
  the image is noise-free at 5 samples. Typography and the HUD are Blender text
  objects parented to the camera, with a soft scrim behind them for legibility.
  Per-frame changes use object colour (Object Info), so no shaders are recompiled.
  ```
  blender -b -P script.py -- --render                 # full sequence -> CONFIG["output"]
  blender -b -P script.py -- --frames 1,200,400 --out /tmp/stills
  # bpy-as-module:
  python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
  ```
- `soundtrack.py`: numpy only. Writes `soundtrack.wav` (48 kHz stereo, 28 s): upper-air
  wind that closes down to a muffled rumble as pressure rises, a low drone on A that
  sags 3 semitones over the fall, sub swells and soft hits on every text beat, distant
  thunder after each lightning flash, a thin pressure whine past 22 bar, and a hard
  cut at the end.
- Encode (grain and vignette added here):
  ```
  ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav \
    -vf "scale=1080:1920:flags=lanczos,noise=alls=5:allf=t,vignette=PI/4.5" \
    -c:v libx264 -pix_fmt yuv420p -crf 23 -preset slow -c:a aac -b:a 192k -shortest 05-no-floor.mp4
  ```

## Posting

**Title:** NO FLOOR

**Caption:**
Jupiter has no surface. Fall in and the clouds just keep going: ammonia ice, then
ammonium hydrosulfide, then water clouds full of lightning. In 1995 the Galileo probe
made it about 150 km down, to 22 bar and 152 °C, before it went silent.
Below that there's only pressure.

**Hashtags:** #jupiter #space #astronomy #nasa #juno #galileo #planets #cosmichorror #ominous #science

**Pinned comment:**
Numbers on the HUD come from a simple model fitted to the Galileo probe's real
measurements (166 K at 1 bar, ~425 K at ~22 bar, ~130–150 km down). Past 22 bar
it's an extrapolation. Nobody has measured that deep. Jupiter's "surface" is just
the 1-bar level by convention: there's nothing to stand on, all the way down.
