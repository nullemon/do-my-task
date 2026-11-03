# OMINOUS #2 — ROGUE

**Concept.** Deep space, the Milky Way laid diagonally across a vertical frame. Something dark slides in
from the left and starts eating the stars. At first it is only a hole in the galaxy; then the faint glow
of the Milky Way catches a hairline of ice-cyan on its limb and you can make out a frozen, fractured
surface. It keeps coming, faster, until it fills the frame and everything goes black and silent.

Text beats (thin, letter-spaced, lower third):

| time | line |
|------|------|
| 0.0 s | THERE'S A PLANET OUT THERE / WITH NO SUN. |
| 4.3 s | NO SUN. |
| 8.2 s | NO DAY. |
| 12.3 s | BILLIONS MAY DRIFT / THROUGH OUR GALAXY. *(small cyan: MICROLENSING SURVEYS · OGLE / MOA)* |
| 17.8 s | YOU WOULDN'T / SEE ONE COMING. |
| 22.6 s | black, hard cut to silence (loops to the starfield) |

Accent colour: ice cyan (rim light, source line). Everything else desaturated.

## What's real

- **Free-floating ("rogue") planets exist.** They are planetary-mass objects that orbit no star. They give off
  almost no light, so the main way to find them is **gravitational microlensing**: when one passes in front of a
  background star, the star briefly brightens.
- **There may be a lot of them.** Microlensing surveys estimate free-floating planets in the Milky Way in the
  billions or more. Examples: MOA/OGLE, Sumi et al. 2011 (Nature), whose high early figure was later revised
  down by Mróz et al. 2017 (Nature); Mróz et al. 2020 (an Earth-mass rogue candidate); Sumi et al. 2023
  (AJ, MOA: roughly 20 Earth-mass-or-larger rogues per star, or about 10^12 in the galaxy). NASA's
  Nancy Grace Roman Space Telescope is expected to detect hundreds more. The on-screen wording ("billions *may*
  drift") stays at the low end of these estimates.
- **No sun, no day.** With no host star there is no daylight cycle. The surface is lit only by starlight and
  stays at a few tens of kelvin (it could be warmer if a thick atmosphere or internal heat keeps it warm,
  which is beyond the claim made here).
- **"You wouldn't see one coming."** They are dark, cold and small. We find them only by microlensing, as brief
  one-off blips in starlight, which is why we can't track them coming.
- Artistic licence: the rim light, the halo and the speed of the approach are dramatised. The ice texture is invented.

## How to run

```bash
# Blender (4.2 – 5.x), headless
blender -b -P script.py -- --render --out /path/to/frames          # all 576 frames
blender -b -P script.py -- --render --frames 1 576 --step 60 --out /tmp/preview

# bpy-as-module environment (used here)
/home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--out','FRAMES']; exec(compile(open(p).read(),p,'exec'))"

python3 soundtrack.py        # -> soundtrack.wav (48 kHz stereo, 24 s)

ffmpeg -framerate 24 -i FRAMES/f_%04d.png -i soundtrack.wav \
  -vf "scale=576:1024:flags=lanczos,noise=alls=7:allf=t,vignette=PI/4.5" \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 192k -shortest ../videos/02-rogue.mp4
```

Render setup: Cycles CPU, 10 samples, no denoiser. The scene is all emission, so the samples only do
anti-aliasing: there are no lamps and no bounces. The sky (stars from Voronoi points, the galactic band
from noise, the dust lanes) is one world shader. The planet is an emission shader with a fresnel rim lit
from the direction of the band. The text is Blender text objects parented to the camera, faded in and out
by keyframing their object-colour alpha. Render size is 572x1018 (53%), scaled to 576x1024 at encode (H.264 needs even dimensions).

## Posting

**Title:** ROGUE

**Caption:** There are planets with no sun. No day. No warmth. They drift through the dark between the stars,
and we only notice one when it passes in front of something else.

**Hashtags:** #space #astronomy #rogueplanet #exoplanet #milkyway #science #ominous #cosmos #astrophysics #darkness

**Pinned comment:** Real science: "free-floating" or rogue planets orbit no star. We detect them with
gravitational microlensing, where a background star briefly brightens as one passes in front of it. Surveys
(OGLE, MOA) suggest the Milky Way may hold billions of them, possibly more than it holds stars. NASA's Roman
telescope should find many more. The visuals are an artistic rendering.
