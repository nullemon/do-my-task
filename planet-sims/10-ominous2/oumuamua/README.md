# 03 · 'Oumuamua: the first known interstellar object (2017)

An ominous vertical short (9:16, 24 fps, 57 s), built procedurally by one Blender script (`oumuamua.py`, Cycles), with a numpy soundtrack.

## Story and captions

| Time (s) | Shot | Caption |
|---|---|---|
| 0.35 to 5.2 | A: deep space, the Sun far off, a faint speck on a curved path | What came through / our solar system / in 2017? |
| 6.0 to 11.2 | A | It wasn't from here. / It came from / between the stars. |
| 12.0 to 17.2 | A: it whips round the Sun; the trail bends and leaves | It swung around the Sun. / No one saw it coming. |
| 18.6 to 24.2 | B: telescope view (crosshair, field stop, "PAN-STARRS1, HALEAKALA, HAWAII, 19 OCT 2017") | A telescope in Hawaii / spotted it… / already leaving. |
| 25.2 to 30.6 | C: close, a dark reddish, elongated body tumbling | They named it 'Oumuamua: / "a messenger from afar, / arriving first." |
| 31.4 to 36.6 | C | Reddish. Tumbling. / Perhaps up to ten times / longer than it is wide. |
| 37.2 to 42.4 | C | As it left, it sped up, / very slightly. / No visible tail. |
| 43.2 to 49.0 | D: it recedes, shrinks and fades into the dark | Ice? Gas we couldn't see? / Scientists still / don't agree. |
| 50.0 | Cut to black, final boom | |
| 50.5 to 57 | Black | We'll never / see it again. |

Booms land at 0.35 s (hook), 17.5 s (telescope cut), 24.5 s (close-up reveal), 37 s (acceleration) and 50 s (cut to black). After the last boom the sound decays to silence.

## The facts

- **Discovery:** Robert Weryk found it on **19 October 2017** in images from the **Pan-STARRS1** telescope on **Haleakalā, Maui, Hawaii**. It is designated 1I/2017 U1, the first interstellar object ever confirmed.
- **From outside the solar system:** its orbit is **hyperbolic** (eccentricity about 1.2), so it is not bound to the Sun. It came in from interstellar space.
- **Already leaving:** its closest approach to the Sun (perihelion, about 0.25 AU, inside Mercury's orbit) was on about **9 Sept 2017**, roughly 40 days before anyone saw it. No one saw it coming in.
- **Name:** Hawaiian, roughly **"a messenger from afar arriving first"** (often glossed as "scout").
- **Shape:** its brightness changed by about a factor of 10 as it rotated. The usual reading is a very elongated body, **perhaps up to ~10:1**, a few hundred metres long. Later modelling says it could instead be a flattened, pancake-like disc (about 6:1) and that the true ratio is uncertain. The captions say "perhaps up to".
- **Motion and colour:** it was **tumbling** (non-principal-axis rotation) rather than spinning neatly. Its colour was **reddish**, like many outer solar system bodies.
- **Non-gravitational acceleration:** Micheli et al. (Nature, 2018) found a small extra push away from the Sun as it left, about 0.1% of the Sun's pull. **No coma, tail or gas was detected.**
- **Unresolved:** proposed explanations include comet-like outgassing that couldn't be seen, hydrogen ice, and nitrogen-ice fragments. There is no consensus. A fringe proposal of an artificial "light sail" was widely publicised but rejected by most researchers (e.g. the ISSI 'Oumuamua team, Nature Astronomy 2019). It is not mentioned in the video.
- **Gone:** it is now far beyond the reach of any telescope and will not return.

### Sources
- NASA, 'Oumuamua in depth: https://solarsystem.nasa.gov/asteroids-comets-and-meteors/comets/oumuamua/in-depth/
- NASA SVS, "From Interstellar Space": https://svs.gsfc.nasa.gov/13132/
- Wikipedia, 'Oumuamua (discovery, orbit, name, hypotheses): https://en.wikipedia.org/wiki/%CA%BBOumuamua
- ESA/Hubble heic1813, non-gravitational acceleration (Micheli et al. 2018): https://esahubble.org/news/heic1813/
- Micheli et al. 2018 (paper, ESO-hosted): https://messenger.eso.org/public/archives/releases/sciencepapers/eso1820/eso1820a.pdf
- Sky & Telescope, "'Oumuamua: red, tumbling and silent": https://skyandtelescope.org/astronomy-news/solar-system/oumuamua-red-tumbling-and-silent/
- Aspect ratio caveats: https://arxiv.org/pdf/2001.09283
- University of Hawaiʻi IfA, "'Oumuamua is not an alien spacecraft" (2019): https://www.ifa.hawaii.edu/2019/07/%CA%BBoumuamua-is-not-an-alien-spacecraft/

## What's real and what's dramatised

- **Real:** the hyperbolic shape of the path (eccentricity 1.2, the real value), the discovery date, place and telescope, that it was found only after perihelion, the reddish colour, the elongated tumbling body, the acceleration with no tail, and that it is gone.
- **Dramatised:**
  - The bodies are not to scale: the Sun is a small glowing ball, and in the wide and telescope shots the object is enlarged hugely so it reads as a speck.
  - Timing is compressed. The real perihelion-to-discovery gap was about 40 days, and the tumble period was about 8 hours (slowed here to a visible drift).
  - The telescope shot is stylised. Pan-STARRS took survey images; there was no live crosshair.
  - The exact shape (cigar vs. pancake) is unknown. The model is a lumpy ~6:1 body.
  - The orbit's orientation relative to the planets is not modelled.

## Render

Rendering at 540 px (what the queue job does) takes every 3rd frame and blends it up to 24 fps:
```
blender -b -P oumuamua.py -- --render --step 3 --res 540 --samples 8 --out /path/frames
blender -b -P oumuamua.py -- --audio oumuamua.wav
```
For **1080p on a GPU**, pass `--gpu` (it picks OptiX, CUDA, HIP, Metal or oneAPI, whichever is available) and render every frame:
```
blender -b -P oumuamua.py -- --render --gpu --res 1080 --samples 64 --out /path/frames
blender -b -P oumuamua.py -- --audio oumuamua.wav
ffmpeg -framerate 24 -i /path/frames/frame_%04d.png -i oumuamua.wav -t 57 \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k oumuamua_1080.mp4
```
To render only part of the film, use `--range FIRST,LAST`. For test stills, use `--frames 193,505,793`. Captions use Inter Light if it is installed (`/usr/share/fonts/opentype/inter/Inter-Light.otf`) and fall back to Blender's built-in font otherwise.
