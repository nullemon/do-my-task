# 06 · Gamma-ray burst

Ominous vertical short (9:16, 24 fps, 58.5 s). Everything is procedural and comes from a single Blender
script, `gamma_ray_burst.py`. That script also writes the numpy soundtrack.

## Story beats / captions

| t (s) | shot | caption |
|---|---|---|
| 0.25–6.6 | Earth at night from orbit, thin blue limb, Milky Way; one blue-white star | What is the most powerful explosion in the universe? |
| 7.6–12.4 | close-up: a giant blue-white star | A gamma-ray burst. |
| 12.9–18.6 | star swells, then collapses (boom at 16.5 s) | A dying giant star collapses into a black hole… |
| 19.0–24.4 | two narrow jets erupt | …and fires two narrow jets out into space. |
| 24.8–30.2 | the jet axis swings toward camera, whiteout | In seconds, it can release as much energy as the Sun will in its whole 10-billion-year life. |
| 31.0–36.2 | back to Earth; a teal ozone shell fades in | Now imagine one aimed at Earth, from a few thousand light-years away. |
| 36.5 | silent flash floods the sky (big boom), then near-silence | (none) |
| 39.0–45.0 | ozone shell tears open, burst-facing side first | Studies suggest it could strip away about a third of our ozone layer. |
| 45.5–51.6 | torn shell, heartbeat pulse | Some scientists think one may have helped trigger a mass extinction ~440 million years ago. |
| 52.2–56.5 | (final boom at 56.5, cut to black, silence) | It would last only seconds. We would never see it coming. |

## Facts and sources

- **The most energetic explosions known.** NASA describes gamma-ray bursts as the most powerful explosions in the universe. A typical burst releases as much energy in a few seconds as the Sun will radiate over its ~10-billion-year lifetime (NASA Goddard / Swift press material, e.g. 2007 release reported by UPI: https://www.upi.com/Science_News/2007/03/09/Astronomers-report-on-dying-star/33281173450624/). That is why the caption says "can release". Note that the energy is beamed into the jets.
- **Origin.** Long GRBs (more than ~2 s) come from the core collapse of a massive, rapidly rotating star into a black hole (the "collapsar" model). Short GRBs come from neutron-star mergers (confirmed with GW170817 / GRB 170817A in 2017). Both fire two narrow, relativistic jets, and we only see a burst if a jet points at us. The video shows the long (collapsar) kind.
- **Ozone damage.** Thomas et al. 2005 (ApJ 634, 509; arXiv:astro-ph/0505472) modelled a burst ~2 kpc (~6,500 light-years) away and pointed at Earth. They found globally averaged ozone depletion of up to ~38%, with more in some places, lasting years. Melott's KU press release says a burst "within 6,000 light years" would be devastating (https://phys.org/news3625.html). The caption hedges this as "Studies suggest… about a third".
- **Late Ordovician extinction (hypothesis).** Melott et al. 2004, "Did a gamma-ray burst initiate the late Ordovician mass extinction?" (Int. J. Astrobiology; arXiv:astro-ph/0309415) proposes this as a working hypothesis. There is no direct evidence. The extinction happened ~440–445 million years ago. The caption says "Some scientists think… may have helped".
- **WR 104** is deliberately left out of the video. It was once discussed as a possible future GRB source, but later spectroscopy suggests its rotation axis is probably tilted well away from us. Whether it would make a GRB at all is also uncertain.

## Real vs dramatised

- Real: the energy comparison, the collapse-to-black-hole origin, the two narrow jets, ozone loss within a few thousand light-years (from models), and the Ordovician idea (labelled as a hypothesis).
- Dramatised: the ozone layer isn't visible and doesn't "tear" like a shell. It is drawn as a glowing teal shell so the loss can be seen. The flash is also shown in visible light. A real GRB's prompt emission is gamma rays, absorbed high in the atmosphere, and any visible flash would be brief. There is no sound in space; the booms are the score. The jets are far narrower and longer than shown, and the star close-up compresses minutes to hours of collapse into a second. "We would never see it coming" holds because the gamma rays travel at light speed, so no earlier signal could warn us.

## Render

The job used here is `scratchpad/queue/pending/06_gamma_ray_burst.sh`. It renders every 3rd frame at 540x960, 8 samples, OIDN, then blend-interpolates to 24 fps. To run at 1080p on a GPU:

```bash
# frames (all 1404 at full res, GPU: set Preferences > System > Cycles device, or edit new_scene()'s device)
blender -b -P gamma_ray_burst.py -- --render --res 1080 --samples 64 --out frames/
python gamma_ray_burst.py -- --audio gamma_ray_burst.wav     # bpy-free: numpy only (or run with blender's python)
ffmpeg -framerate 24 -i frames/frame_%04d.png -i gamma_ray_burst.wav -c:v libx264 -crf 18 \
       -pix_fmt yuv420p -c:a aac -b:a 192k -shortest gamma_ray_burst.mp4
```
To use a GPU, set `sc.cycles.device = "GPU"` in `new_scene()` and enable CUDA/OptiX in preferences. Test stills: `--frames 300,460,1150 --res 270`.
