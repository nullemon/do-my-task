# OMINOUS #1 — THE LAST SUNSET

27 s, vertical, near-silent. A lone ridge on a barren world under a sky full of stars.
A counter at the top runs from today (13,800,000,000 years after the Big Bang) to
100,000,000,000,000 (10^14 years), faster and faster. The blue-white stars go out first, the
sky thins to a scatter of red points, and a single dim red dwarf slides down and sets behind the
tallest crag, catching a thin red rim of light on the rock. Black. *"After this, nothing ever
shines again."* Hard cut to silence, which loops back to the starfield.

Accent colour: deep red.

## On-screen text (timing)
| t (s) | text |
|---|---|
| 0.1–4.3 | THIS IS THE LAST SUNSET / THE UNIVERSE WILL EVER HAVE. |
| 5.4–9.6 | THE BRIGHTEST STARS DIE FIRST. |
| 10.4–14.6 | THEN THE GAS RUNS OUT. / NO NEW STARS ARE BORN. |
| 15.4–19.8 | THE LAST ONES ARE RED DWARFS. / THEY BURN FOR TRILLIONS OF YEARS. |
| 1–22.8 | year counter, 1.38×10^10 → 10^14, "YEARS AFTER THE BIG BANG" |
| 21.6 | the last sun sets |
| 23.5–26.6 | AFTER THIS, / NOTHING EVER SHINES AGAIN. |

## What's real
- **Age of the universe today:** ~13.8 billion years (Planck 2018).
- **Massive stars die first:** stellar lifetime scales steeply with mass (roughly M^-2.5);
  O/B stars live a few million years, the Sun ~10 billion, red dwarfs far longer.
- **Red dwarfs are the last stars:** the lowest-mass red dwarfs (~0.08–0.1 M☉) are expected to
  shine for up to ~10^13 years (Laughlin, Bodenheimer & Adams 1997, *ApJ* 482:420).
- **Star formation ends / the Stelliferous Era closes around 10^14 years:** galaxies use up their
  gas, star formation stops, and the last red dwarfs burn out (Adams & Laughlin 1997,
  *Rev. Mod. Phys.* 69:337, "A dying universe").
- **Honest nuance:** "nothing ever shines again" is the poetic version. After 10^14 yr there are
  still cooling white dwarfs (fading toward black dwarfs), rare brown-dwarf collisions that can
  ignite a short-lived new star, and eventually Hawking radiation — but no normal stars ever
  form again. The planet's sky, its rotation and the time-lapse compression are artistic.

## How to run
Requires Blender 4.2–5.x (or the `bpy` module) and Python 3 + numpy for the sound.

```bash
# frames (Cycles CPU, emission-only so 8 samples, no denoiser) -> ./frames/
blender -b -P script.py -- --render
blender -b -P script.py -- --render --out /tmp/ls/ --frames 1,250,520   # test stills
# with the bpy module instead of a blender binary:
python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--out','/tmp/ls/']; exec(compile(open(p).read(),p,'exec'))"

# soundtrack -> soundtrack.wav (48 kHz)
python soundtrack.py

# encode (scale to 576x1024, light grain + vignette)
ffmpeg -framerate 24 -i /tmp/ls/f_%04d.png -i soundtrack.wav \
  -vf "scale=576:1024:flags=lanczos,vignette=PI/5,noise=alls=5:allf=t" \
  -c:v libx264 -preset slow -tune grain -pix_fmt yuv420p -crf 23 -c:a aac -b:a 192k -shortest 01-last-sunset.mp4
```
The CONFIG block at the top of `script.py` sets fps, duration, resolution, samples and output.
All timing (text beats, sunset, star death schedule) lives in the timeline section below it.

## Posting
**Title:** The Last Sunset

**Caption:**
In about 100 trillion years, the last star in the universe goes out.
It won't be a big one. It'll be a small, dim red dwarf — the only kind that lasts that long.
Somewhere, maybe, it sets for the last time.

**Hashtags:** #space #astronomy #universe #cosmology #endoftheuniverse #reddwarf #stars #science #physics #ominous

**Pinned comment:**
The science: the biggest, brightest stars burn out in millions of years. Sun-like stars last
~10 billion. Red dwarfs sip their fuel so slowly they can shine for up to ~10 trillion years.
Once galaxies run out of gas (~10^14 years), no new stars form — astronomers call the end of
this "Stelliferous Era". What's left: cooling white dwarfs, black holes, and the dark.
(Adams & Laughlin, "A dying universe", Rev. Mod. Phys. 1997.)
