# 02 · What if the Sun became a black hole?

A vertical ominous short (9:16, 24 fps, 56 s), built procedurally by one Blender script: `sun_blackhole.py`.
It renders the scenes, and the same script writes the numpy soundtrack.

## Story and captions

| time | picture | caption |
|---|---|---|
| 0–4.6 s | noon sea, Sun high in a blue sky | What if the Sun became a black hole? |
| 4.8–9.6 s | same | It never will. It would need about 20 times more mass. |
| 10–14.5 s | same, nothing changes (soft boom at the collapse, timer `08:20` starts) | But imagine it collapsed anyway, into a ball about 6 km across. |
| 14.7–22 s | timer runs down to `00:00` | Its last light still needs 8 minutes 20 seconds to reach us. |
| 22 s | **boom**: the Sun's disc and the blue sky are gone, stars fade in | Then the sky goes black. Stars at noon. |
| 30 s | cut to space: Earth on its orbit around a tiny black sphere with a lensed star ring, city lights still on | Earth's orbit wouldn't change. Same mass. Same pull. |
| 37–43 s | ice spreads from the poles | Scientists estimate: below freezing within about a week… |
| 43–48.5 s | the oceans ice over, the lights dim | …around −73°C within a year. |
| 48.8–53.7 s | | We wouldn't fall in. We'd just… freeze. |
| 53.75 s | final boom, cut to black, then silence | |

## Facts and sources

- **The Sun can't become a black hole.** NASA says a star needs to be roughly 20 times more massive than the Sun to end as a black hole. The Sun will end as a white dwarf. (Other sources give lower thresholds, around 10 solar masses. The video says "about 20 times".)
  [NASA: Why the Sun won't become a black hole](https://www.nasa.gov/image-article/why-sun-wont-become-black-hole) · [Live Science](https://www.livescience.com/space/astronomy/will-the-sun-ever-become-a-black-hole)
- **Size.** The Schwarzschild radius of one solar mass is 2GM/c² ≈ 2.95 km, so the event horizon would be about **6 km across** (radius ≈ 3 km).
- **The orbit would not change.** Outside the original Sun, gravity depends only on mass. The same mass gives the same pull at 1 AU, so Earth keeps its orbit.
  [IFLScience](https://www.iflscience.com/if-the-sun-turned-into-a-black-hole-earth-would-continue-its-orbit-73947) · [SciShow, "If the Sun became a black hole, would Earth fall in?"](https://rosetta.to/u/scishow/if-the-sun-became-a-black-hole-would-earth-fall-in) · [xkcd What If 129](https://what-if.xkcd.com/129/)
- **8 min 20 s.** Light takes about 499 s (1 AU / c) to reach Earth. The change in gravity also travels at the speed of light, but here there is no change in gravity at all.
- **The cold.** These are popular-science estimates, not climate-model output. The usual figures are about 0 °C global average within a week, with other estimates nearer −10 °C, and about **−73 °C after one year**. The deep oceans would stay liquid under the ice for a very long time.
  [Vsauce, "What if the Sun disappeared?" (transcript)](https://rosetta.to/u/vsauce/what-if-the-sun-disappeared) · [Business Insider](https://www.businessinsider.in/heres-what-would-happen-if-the-sun-disappeared-right-now/articleshow/48430503.cms)

## Real vs. dramatised

- The whole scenario is a hypothetical, and the captions say so ("What if", "imagine", "It never will").
- The 8 min 20 s wait is compressed into 12 s, with an on-screen timer. A week and a year are compressed into about 10 s.
- The **space view is not to scale.** A 6 km object seen from 1 AU would be far too small to see, and its real Einstein-ring radius would be under an arcminute. Here the black sphere and its ring are huge and close so they can be seen. The lensing is a point-lens approximation in the world shader: a camera ray at angle θ from the hole is bent by θ_E²/θ. The faint ring glow is an artistic touch.
- The faint blue light on the dark Earth is a stand-in for starlight, so the planet can be seen at all. Ice spreading from the poles and the city lights dimming are dramatisations of "the oceans would ice over".
- The Sun's disc is drawn larger than its real 0.5° so it reads on a phone.

## Render

Everything is procedural, so there are no downloads.

```bash
# frames (every 3rd frame; resumable), 540x960 draft:
blender -b -P sun_blackhole.py -- --render --every 3 --res 540 --samples 8 --out frames/
# 1080p on a GPU (enable the GPU in Preferences > Cycles first, or render all frames and skip the blending):
blender -b -P sun_blackhole.py -- --render --every 1 --res 1080 --samples 128 --out frames1080/
# soundtrack (numpy only):
python sun_blackhole.py -- --audio sun_blackhole.wav
# full frame sequence -> video:
ffmpeg -framerate 24 -pattern_type glob -i 'frames1080/frame_*.png' -i sun_blackhole.wav \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest sun_blackhole_1080.mp4
```

The script uses Cycles. The script sets the device to CPU, so for a GPU render change `sc.cycles.device = "GPU"` in `new_scene()` and pick CUDA, OptiX, HIP or Metal in Preferences. For the every-3rd-frame draft, link the frames into a consecutive sequence and encode at `-framerate 8` with `minterpolate=fps=24:mi_mode=blend`; the job script in the session scratchpad does exactly this. All key beats (the collapse, the darkness, the cut to space, the cut to black) fall on frames 1 + 3k.
