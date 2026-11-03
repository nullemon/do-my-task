# 04 · earth_stops: "What if Earth stopped spinning... instantly?"

A vertical (9:16) short: 24 fps, 57 s, everything procedural in `earth_stops.py` (Blender 4.2+/5.x and Cycles). The soundtrack is made with numpy in the same script.

## Story beats and captions

| Time (s) | Picture | Caption |
|---|---|---|
| 0.3–4.6 | A calm seaside street at dusk: palms, street lamps, lit windows, clouds | What if Earth stopped spinning... instantly? |
| 5.0–13.4 | Slow push along the promenade | At the equator, the ground moves at about 1,670 km/h |
| 14.0–17.4 | Same shot; the noise swells | Now stop the planet. But not the air. |
| **17.5** | **JOLT (boom).** Camera shake, palms snap east, cars, crates and roof debris fly sideways, the cloud deck streaks, the lights die, dust fills the sky | – |
| 18.6–24.2 | A stream of debris and speed lines with motion blur | Winds of about 1,670 km/h. Faster than any tornado. |
| 23.5–31.5 | The camera turns toward the sea; a wall of water rises and races in from the west | And the oceans keep going too. |
| **31.5** | **The wave hits (boom)**, black | – |
| 32.5–34 | Cut to space (soft boom at 34): a non-rotating Earth, one half lit and the other in night | – |
| 34.6–41.0 | Polar oceans | Over time, the seas would pool at the two poles... |
| 41.6–47.4 | The equatorial land band | ...leaving one giant continent at the equator. |
| 48.0–52.4 | The terminator creeps slowly across (a time-lapse of the year-long day) | Six months of daylight. Six months of night. |
| 52.9–55.0 | | One day would last a year. |
| **55.0** | **Boom, cut to black**, then silence | – |

## The facts

- **Equatorial rotation speed.** Earth's circumference is about 40,075 km, and it turns once in about 23.93 h, so the equator moves at about 1,670 km/h (about 465 m/s). The speed falls toward the poles (about cos(latitude) × 1,670 km/h).
- **Sudden stop.** The atmosphere and oceans are not rigidly attached to the crust. If the solid planet stopped instantly, they would keep moving east at up to about that speed relative to the ground. That gives winds of about 1,670 km/h at the equator. They would be faster than the speed of sound (about 1,235 km/h) and well beyond the strongest tornado winds ever measured (about 480 km/h, Bridge Creek–Moore 1999). Anything not anchored, and anything that hits an anchored object, would be swept east. The oceans would surge east too.
- **Afterwards: one day = one year.** With no spin, the Sun's position in the sky changes only because Earth orbits it. The Sun would rise and set once per orbit, so a solar day would last a year: about six months of daylight followed by about six months of night. The exact split varies with latitude and axial tilt, so the caption is approximate.
- **Oceans migrate to the poles.** Spin is what gives Earth its equatorial bulge (the equatorial radius is about 21 km larger than the polar radius). Without the centrifugal effect, ocean water flows "downhill" toward the poles over time. The result is two great polar oceans and one giant equatorial continent. This comes from Witold Fraczek's 2010 GIS model for Esri. The solid Earth would relax its bulge only over geological time, so this happens after the stop, not during the stop itself. The video says "over time".
- **Real world.** Earth is slowing very gradually because of tidal braking, and it will not stop within any relevant timescale. An instant stop is physically impossible. This is a "what if" scenario.

### What's dramatised
- On-screen debris speeds are scaled down (about 15–90 m/s scene units instead of 465 m/s) so the eye can follow them. The cloud deck streaks at about the true speed.
- The size, shape and timing of the wall of water are artistic. Nobody has modelled the real surge at street level.
- The space shot jumps straight to the end state (oceans at the poles) and compresses the year-long day into a slow terminator crawl. The continent's shape is a procedural stand-in, not Fraczek's map.

### Sources
- [ScienceFocus: What would happen if the Earth stopped spinning?](https://www.sciencefocus.com/planet-earth/the-thought-experiment-what-would-happen-if-the-earth-stopped-spinning/)
- [IFLScience: What would happen if the Earth suddenly stopped spinning](https://www.iflscience.com/editors-blog/what-would-happen-if-the-earth-suddenly-stopped-spinning/)
- [Esri, Witold Fraczek: What would happen if the Earth stopped spinning?](https://community.esri.com/t5/applications-prototype-lab-blog/what-would-happen-if-the-earth-stopped-spinning/ba-p/903630)
- [Popular Science: What would the Earth look like if it stopped spinning? (polar oceans, equatorial megacontinent)](https://www.popsci.com/science/article/2010-07/what-would-earth-look-if-it-stopped-spinning)
- [UCSB Geography: What would happen if the Earth stopped spinning?](https://legacy.geog.ucsb.edu/what-would-happen-if-the-earth-stopped-spinning/)
- [Astronomy.com: What happens if Earth stops rotating](https://www.astronomy.com/science/what-happens-if-earth-stops-rotating/)
- [Science Notes: What would happen if the Earth stopped rotating](https://sciencenotes.org/what-would-happen-if-the-earth-stopped-rotating/)

## Rendering

```bash
# test stills
python earth_stops.py -- --render --frames 160,475,1000 --res 270 --samples 8 --out /tmp/es
# production: 1080x1920 on a GPU (OPTIX, CUDA, HIP or METAL), every frame
blender -b -P earth_stops.py -- --render --gpu OPTIX --res 1080 --samples 64 --out renders/frames
python earth_stops.py -- --audio earth_stops.wav          # or: blender -b -P earth_stops.py -- --audio ...
ffmpeg -framerate 24 -i renders/frames/frame_%04d.png -i earth_stops.wav -c:v libx264 -crf 18 \
       -pix_fmt yuv420p -c:a aac -b:a 192k -shortest earth_stops.mp4
```
At 24 fps, render every frame (`--step 1`, the default). The CPU job in this repo renders every 3rd frame (`--step 3`) and blends them to 24 fps with `ffmpeg minterpolate=mi_mode=blend`. The cut frames sit on that 3-frame grid, and visibility toggles fall between rendered frames, which avoids motion-blur smears.

`preview/` holds the stills.
