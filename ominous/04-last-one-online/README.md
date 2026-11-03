# OMINOUS #4 — LAST ONE ONLINE

Earth's night side seen from low orbit. Amber city lights trace coastlines and river corridors, an aurora
rises over the limb, and a thin airglow line hangs above the atmosphere. Then the lights start going out.
There's no sound and no reason given. Whole regions flicker and fail, and the dark rolls in from the horizon toward
the camera. In the end one light is left, blinking. *Last one online.* Then it goes out too.

The piece is an art piece. It makes no factual claim, and the on-screen text is poetic:

| time | text |
|------|------|
| 0.3 – 4.6 s | EVERY LIGHT / IS SOMEONE |
| 5.2 – 8.9 s | STILL AWAKE |
| 10.0 – 13.6 s | ONE BY ONE |
| 17.4 – 21.4 s | LAST ONE ONLINE |
| 21.6 s | the last light dies; aurora and airglow remain; silence; cut |

Accent colour: sodium amber, the colour of high-pressure sodium street lighting.

## What's real (visual reference, not claims)
- **Viewpoint:** the camera sits at about 410 km altitude, roughly where the ISS orbits. The horizon dips about 20° below horizontal, and the
  ground drifts toward the camera like an orbital pass.
- **City lights at night** are mostly orange-amber from sodium-vapour lamps. They cluster on coasts, rivers and
  transport corridors, and deserts and interiors stay dark. The procedural mask copies this pattern.
- **Airglow** is the faint greenish line above Earth's limb in ISS night photos. Oxygen emission at about
  90–100 km altitude causes it. **Aurora** curtains are green at the bottom and fade to red/purple higher up. From orbit they are seen
  rising over the limb.

## Files
- `script.py` — a self-contained procedural Blender script that renders with Cycles on CPU, using emission-only shading.
- `soundtrack.py` — numpy only. It writes `soundtrack.wav` at 48 kHz.
- `../videos/04-last-one-online.mp4` — the final video. It is 576×1024, 24 fps and 24 s long.

## How it's built
- The globe is a single emission shader. The noise fields are a continent fBm with a coastal band, regional population,
  river corridors, Voronoi cities (domain-warped) with street-texture sprawl, finer Voronoi towns and rural speckle.
  Faint moonlit clouds dim the lights. The blackout schedule (`off_time`) mixes a horizon-to-camera gradient with
  per-region random Voronoi cells, so the grid fails *region by region*. A 4D-noise flicker plays just before each light dies.
- **Speed trick:** before rendering, these static fields are baked once into a float EXR. The bake covers only the patch of globe the camera
  ever sees, and takes about 1.5 min. At render time the globe shader is one texture lookup plus the animated blackout and flicker math.
  The bake's light-weighted quantiles of `off_time` are used to pace the blackout evenly over 2.2 to 16.8 s.
- The atmosphere is two transparent emission shells driven by a Layer Weight / facing falloff: a blue limb and a thin airglow line.
  The aurora is a ribbon mesh along an auroral-oval arc beyond the horizon, with stretched 4D-noise rays and a vertical colour profile.
- The last light is a tiny emitter parented to the globe. Its blink is driven by a frame handler.
- Text uses Blender text objects (Inter Light) parented to the camera, with fades driven per frame.
- Post (ffmpeg): two-radius bloom (screen blend), a vignette and luma-only film grain.

## Run
```bash
# Blender binary
blender -b -P script.py -- --render                      # frames -> OUTPUT in CONFIG
blender -b -P script.py -- --still 0 240 470             # test frames
blender -b -P script.py -- --render --frames 0 100 --out /tmp/f
# bpy as a Python module (this environment)
python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
python soundtrack.py
```
Encode (bloom + vignette + grain):
```bash
POST="format=gbrp,split=3[a][b][c];[b]lutrgb=r='clip((val-60)*2,0,255)':g='clip((val-60)*2,0,255)':b='clip((val-60)*2,0,255)',gblur=sigma=6[g1];[c]lutrgb=r='clip((val-40)*1.5,0,255)':g='clip((val-40)*1.5,0,255)':b='clip((val-40)*1.5,0,255)',gblur=sigma=28[g2];[a][g1]blend=all_mode=screen:all_opacity=0.55[x];[x][g2]blend=all_mode=screen:all_opacity=0.35,vignette=PI/4.5,format=yuv420p,noise=c0s=7:c0f=t"
ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav -filter_complex "[0:v]$POST[v]" -map "[v]" -map 1:a \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 192k -shortest -movflags +faststart 04-last-one-online.mp4
```
Flags: `--no-bake` (pure procedural evaluation, about 3× slower), `--scale 1.0` (full 1080×1920), `--overwrite`, `--step N`, `--save file.blend`.

## Sound
A low E/B drone with slow beating, filtered "space air" and a 50 Hz mains hum with harmonics. The hum's level tracks how much of
the grid is still lit, and it crackles and drops out as regions fail. A sub-bass swell builds under the blackout. Soft low hits land on each
text beat, and a quiet ping sounds with each blink of the last light. When it dies, everything cuts to one deep hit and a reverb tail,
then silence.

## Posting
**Title:** Last one online

**Caption:** Every light is someone. Watch until the end.

**Hashtags:** #ominous #earthatnight #space #aurora #liminal #cinematic #blender3d #shortfilm #eerie #nightsky

**Pinned comment:** Everything here is procedural: there is no NASA imagery, and the planet, the cities and the aurora are all noise and math in Blender.
The orange is real, though: from orbit, most city light at night looks amber because of sodium street lamps. If you were the last
light on, what would you be doing?

## Render stats (this machine)
4 shared CPU cores, Cycles CPU, 6 samples + OIDN, persistent data. The one-time field bake took about 1.5 min,
then about 8.9 s per frame (the machine was heavily shared), so 576 frames took about 85 min in total.
