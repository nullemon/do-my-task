# 05 · The Boötes Void ("the Great Nothing")

Vertical 9:16, 24 fps, 58 s. The camera starts inside a dense procedural cosmic web (about 110k galaxy points on the walls and filaments of a weighted Voronoi foam). It drifts very slowly into one enormous empty cell. The galaxies thin out and two lone faint spirals drift past. The far walls fade until the frame is almost black. A final boom, then a cut to black and silence.

1 Blender unit = 1 million light-years. The carved void is 330 Mly across.

## Story beats and captions

| time (s) | caption | sound |
|---|---|---|
| 0.3–4.8 | What is the emptiest place we have ever found? | drone fades in |
| 6.0–11.5 | Galaxies gather in a vast web of walls and filaments. | noise swell |
| 13.0–18.5 | In 1981, astronomers found a hole in it. | boom |
| 20.0–26.5 | The Boötes Void. About 330 million light-years across. | boom |
| 28.0–34.0 | Light would take 330 million years to cross it. | first lone galaxy drifts past |
| 35.5–42.0 | Thousands of galaxies should be here. We have found about 60. | boom |
| 43.5–50.0 | Had we been born at its centre, we might not have known other galaxies existed until the 1960s. | second lone galaxy, sub layer deepens |
| 50.8–55.5 | And most of space looks like this. | swell, final boom at 55.5, cut to black, silence |

## Facts and sources

- **Discovered in 1981.** Kirshner, Oemler, Schechter and Shectman, "A million cubic megaparsec void in Boötes", *ApJ Letters* 248 (1981), from a galaxy redshift survey.
- **Size and distance.** About 330 million light-years across. Some sources give up to roughly 400 Mly, so the caption says "about". Its centre is about 700 million light-years away, in the direction of the constellation Boötes.
- **Galaxy count.** About 60 galaxies had been found in it by 1997. About 2,000 would be expected at the average density. The caption says "thousands should be here" and "about 60".
- **The 1960s line** paraphrases astronomer Greg Aldering: if the Milky Way had sat at the void's centre, we would not have known other galaxies existed until the 1960s. It is paraphrased, not quoted, because the original wording could not be confirmed.
- **"Most of space looks like this."** Cosmic voids fill most of the volume of the universe, while most galaxies sit in walls, filaments and clusters. The Boötes Void is one of the largest voids known.
- **Light-crossing time.** 330 million light-years means about 330 million years for light to cross it, by definition.

Sources:
- Wikipedia, "Boötes Void": https://en.wikipedia.org/wiki/Bo%C3%B6tes_Void
- Kirshner et al. 1981, ApJ 248, L57: https://ui.adsabs.harvard.edu/abs/1981ApJ...248L..57K
- Explorersweb, "Exploration Mysteries: Boötes Void": https://explorersweb.com/exploration-mysteries-bootes-void/
- Cosmic voids (volume fraction): https://en.wikipedia.org/wiki/Void_(astronomy)

### What is real vs dramatised

These parts are real: the void's size, its distance, the discovery year, the galaxy count and the cosmic-web structure in general.

These parts are dramatised:
- **The web is procedural.** It is a Voronoi foam, not the real galaxy map.
- **Galaxies are drawn far too large.** Each point is held at a minimum size of about 1 pixel and dims with distance, so the web reads at all. The dimming also tightens over time so that "the void swallows the frame".
- **The two drifting spirals are moved along with the camera.** At the real flight speed they would flash past in a fraction of a second. They are also much larger and closer than real void galaxies would be.
- **The flight speed is impossible.** The camera covers about 400 Mly in under a minute.

## Render

The script is a single file. It builds the scene, renders the frames and writes the WAV (numpy):

```
blender -b -P bootes_void.py -- --render --res 540 --samples 8 --step 3 --out frames/   # draft (the queue job)
blender -b -P bootes_void.py -- --wav bootes_void.wav
```

**1080p on a GPU:** set the Cycles device to GPU in preferences (CUDA/OptiX/HIP/Metal), then run:

```
blender -b -P bootes_void.py -- --render --res 1080 --samples 32 --out frames1080/
ffmpeg -framerate 24 -i frames1080/frame_%04d.png -i bootes_void.wav \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest bootes_void_1080.mp4
```

- Rendering every frame (`--step 1`) needs no frame blending.
- At 1080 the minimum point size (`size_floor`) still gives sub-pixel-safe points.
- Building the web takes 3–5 minutes on a CPU before the first frame.

The draft pipeline is the queue job `05_bootes_void.sh`:
- it renders every 3rd frame at 540x960, 8 samples, with OIDN;
- it blends to 24 fps with `minterpolate=mi_mode=blend`;
- it encodes H.264 crf 20 with AAC audio;
- it copies 2 stills into `preview/`.
