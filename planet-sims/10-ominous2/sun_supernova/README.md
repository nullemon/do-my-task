# 01 · What if the Sun went supernova?

Vertical (9:16) ominous short, 56 s at 24 fps. Everything is procedural and built by `sun_supernova.py`
(one self-contained Blender script, Cycles; the soundtrack is generated with numpy).

## Story beats and captions
| time | picture | caption |
|---|---|---|
| 0–3.7 s | calm midday sea, the Sun high in a blue sky | **What if the Sun went supernova?** |
| 4.3–10 s | same | **It can't. It's far too small. It will swell into a red giant, then fade to a white dwarf.** |
| 10.8–14.6 s | same, soft boom | **…but what if it did?** |
| 15.4–21.6 s | same, wind rising | **First, a flood of neutrinos. This close, even they could be lethal.** |
| 22.4–33 s | countdown 08:20 → 00:00 (time-lapse) | **Then the light, 8 minutes 20 seconds behind.** |
| 33 s | the Sun swells, the sky burns white, full whiteout (big boom) | — |
| 36–43 s | white clears to space: Earth, its day side starting to glow | **For weeks, it would outshine the entire galaxy.** |
| 44–50 s | a glowing blast shell sweeps in and engulfs Earth, the day side incandescent and streaming away (boom) | **Within hours, the blast would boil Earth away.** |
| 50.6–51.8 s | the front reaches the camera: white, then hard cut to black (final boom) | — |
| 52.6–56 s | black, then silence | **No one would be left to see it.** |

## What's real, what's dramatised
- **Real: the Sun can't go supernova.** Core-collapse supernovae need roughly 8–10 solar masses or more. The Sun will become a red giant in about 5 billion years and end as a white dwarf. A white dwarf can only explode (Type Ia) by taking matter from a companion star, and the Sun has none. The video says this before any "what if".
- **Real: light takes about 8 min 20 s** (≈499 s) to travel 1 AU, so nothing would look different until then.
- **Real: neutrinos come first.** For SN 1987A, the neutrino burst reached detectors (Kamiokande II, IMB, Baksan) roughly 2–3 hours before the light. The light leaves only when the shock breaks out of the star's surface. Neutrinos escape the core straight away.
- **Hedged estimate: neutrinos could be lethal this close.** Randall Munroe's *What If? #73* estimates the neutrino dose is lethal (~4 Sv) out to about 2.3 AU from a core-collapse supernova. The video says "could be".
- **Real: a supernova can outshine its whole host galaxy for weeks.**
- **Order-of-magnitude, hedged: "within hours, the blast would boil Earth away".** Ejecta move at roughly 10,000 km/s or more, so they would cross 1 AU in about 4 hours. A typical ~10⁴⁴ J of kinetic energy, spread over a sphere 1 AU in radius, puts ~4×10³⁴ J onto Earth's cross-section. That is ~100× Earth's gravitational binding energy (~2×10³² J). Even before that, the light flash (peak ~10⁹–10¹⁰ L☉) would heat the day side to tens of thousands of kelvin.
- **Dramatised:** the countdown is a time-lapse (8:20 shown in ~10 s). Shell speed, size and distances in the space shot are not to scale (Earth is shown large, the shell crosses it in ~2 s). The flash visual is artistic. In reality you'd be blinded and the sky would turn white at the instant the light arrives, which is what's shown.

## Sources
- SN 1987A neutrino timing: <https://en.wikipedia.org/wiki/SN_1987A>, <https://www.symmetrymagazine.org/article/february-2006/supernova-1987a>, <https://digfir-published.macmillanusa.com/universe10e/universe10e_ch20_9.html>
- The Sun won't go supernova (mass, red giant, white dwarf): <https://www.discovermagazine.com/dont-worry-were-not-in-danger-of-the-sun-going-supernova-45761>, <https://www.nasa.gov/image-article/why-sun-wont-become-black-hole>
- Lethal neutrinos: <https://what-if.xkcd.com/73/>
- Light travel time Sun–Earth (1 AU / c ≈ 499 s), supernova outshining galaxies, and ejecta speeds/energies: standard textbook values, e.g. <https://en.wikipedia.org/wiki/Supernova>

## Render
Development and test (CPU, small): `python sun_supernova.py -- --render --res 270 --samples 8 --threads 1 --frames 120,760,1090 --out /tmp/t`
(`python` is a Blender-as-module venv. `blender -b -P sun_supernova.py -- ...` works too.)

Final 1080p on a GPU:
```
blender -b -P sun_supernova.py -- --render --res 1080 --samples 64 --out renders/frames   # all 1344 frames
blender -b -P sun_supernova.py -- --audio renders/sun_supernova.wav
ffmpeg -framerate 24 -i renders/frames/frame_%04d.png -i renders/sun_supernova.wav \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest sun_supernova.mp4
```
Add `--glare` on a GPU machine for compositor bloom (headless Blender 5 without EGL crashes in the compositor, so it is off by default). To enable the GPU, set `scene.cycles.device = "GPU"` and choose CUDA/OptiX/Metal in Preferences → System. With a GPU, render every frame (no frame blending needed).
The CPU preview build here renders every 3rd frame at 540×960 and blends them to 24 fps with `minterpolate=mi_mode=blend`
(see the queue job `01_sun_supernova.sh`). Flags: `--every N --first A --last B` select frames, rendering is resumable (existing PNGs are skipped), and `--threads N` sets the CPU threads.
