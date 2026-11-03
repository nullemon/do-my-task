# OMINOUS #3 — 72 SECONDS

Night. Fog moves over a ridge where a radio telescope stares at the sky, with a red obstruction light blinking on its rim. A line-printer column scrolls up and slows. The characters **6EQUJ5** stop in the middle of the screen, a green pen circles them, and "Wow!" is written in the margin. Then: *72 seconds. Never heard again. We're still listening.* Static, one green blip, cut to black.

- Vertical 1080×1920 design, rendered at 572×1017 (53 %), encoded at 576×1024 and 24 fps. Length 26 s. Full render took about 90 min wall-clock on 4 shared CPU cores (roughly 9–20 s per frame under heavy contention).
- Accent colour: signal green, used only for the circle, "Wow!" and the final blip.
- Final video: `../videos/03-72-seconds.mp4`

## On-screen text (timing)

| t (s) | text |
|---|---|
| 0.0 | IN 1977, SOMETHING / CALLED TO US |
| 0.9 | FOR 72 SECONDS. |
| 5.0 | AUGUST 15, 1977 · BIG EAR RADIO TELESCOPE · OHIO STATE UNIVERSITY |
| 8.3 | printout scrolls (caption: INTENSITY, 12-SECOND STEPS) |
| 12.85 | 6EQUJ5 circled in green, "Wow!" at 14.0 |
| 16.4 | 72 SECONDS. / AS EARTH TURNED, IT DRIFTED THROUGH THE BEAM. |
| 19.6 | NEVER HEARD AGAIN. |
| 22.6 | WE'RE STILL LISTENING. |
| 24.6–25.6 | static, one blip, hard cut to black |

## What's real

- **The Wow! signal** was received on **15 August 1977** (about 10:16 pm EDT) by Ohio State University's **Big Ear** radio telescope in Delaware, Ohio, during a SETI survey.
- A few days later the volunteer astronomer **Jerry R. Ehman** went through the computer printout. He circled the characters **6EQUJ5** in red ink and wrote **"Wow!"** in the margin.
- Each character is the signal strength, measured against background noise, for one sample. A new sample was printed every **12 seconds** (about 10 s of integration plus processing time). The scale runs 1–9 and then A–Z. "U" means 30–31 times the noise level, the strongest value in the sequence.
- **72 seconds**: Big Ear did not move to track the sky. It was a transit instrument, so Earth's rotation carried each patch of sky through its beam in about 72 s. The signal rose and fell over that window in the way a source fixed on the sky would. Its frequency was close to the 1420 MHz hydrogen line.
- **Never heard again**: Ehman and others searched the same spot repeatedly, and so did later searches with the VLA and other telescopes. None of them detected it again. Its origin is still unexplained. In 2024 a team proposed a natural explanation, a brief brightening of a cold hydrogen cloud; it has not been confirmed.
- Searches for technosignatures continue today (for example Breakthrough Listen and the SETI Institute), which is the basis for "we're still listening".

### Honest liberties
- **The dish is stylised.** The real Big Ear was a Kraus-type telescope: a huge tilting flat reflector and a fixed curved reflector over an aluminium ground plane, about the size of three football fields. A dish reads as "radio telescope" in one second on a phone. The dish in the film stays still and the sky moves past it, which matches the transit idea. Big Ear itself was demolished in 1998.
- **The printout is a generic recreation.** Only 6EQUJ5 in the second channel column is real. The surrounding 1s, 2s and blanks are randomised noise, and the original showed many more channels. Ehman's circle was red ink; here it is the series accent green.
- The 1420 Hz tone in the soundtrack is a nod to 1420 MHz, not the real signal.
- "Something called to us" is a poetic hook. Nobody knows what it was.

## How to run

```bash
# Blender (4.2 – 5.x)
blender -b -P script.py -- --render                 # all frames -> //frames/f_####.png
blender -b -P script.py -- --frames 1,300,600       # stills
#   options: --out DIR/  --percent N  --samples N  --start N --step N

# No blender binary: bpy as a Python module (how this was made)
/home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--out','/path/frames/f_']; exec(compile(open(p).read(),p,'exec'))"

# soundtrack (numpy only) -> soundtrack.wav (48 kHz stereo)
python soundtrack.py

# encode: grain + vignette, a static burst 24.6–25.5 s, a gentle contrast curve
ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav \
  -vf "scale=576:1024:flags=lanczos,eq=contrast=1.06:saturation=0.9,vignette=PI/5,noise=c0s=8:c0f=t,noise=c0s=70:c0f=t:enable='between(t,24.6,24.98)+between(t,25.3,25.58)'" \
  -c:v libx264 -preset slow -pix_fmt yuv420p -crf 23 -c:a aac -b:a 192k -shortest ../videos/03-72-seconds.mp4
```

Render design, for CPU-only Cycles: 8 samples plus OpenImageDenoise, adaptive sampling, persistent data and 2 bounces. Most of the scene is emission-shaded. The fog is four camera-facing planes with 3D noise and transparency, with no volumetrics. Text is Blender text parented to the camera. Each overlay is `hide_render`-keyed outside its beat so it costs nothing while hidden, and the printout sits on an opaque card so the scene behind it is skipped.

## Posting

**Title:** 72 seconds.

**Caption:**
On August 15, 1977, the Big Ear radio telescope in Ohio picked up a narrowband signal so strong the astronomer reviewing the printout circled it and wrote "Wow!". It lasted 72 seconds, exactly as long as the telescope could see any one point in the sky. We've pointed telescopes back at that spot many times since. Nothing. 🎧 sound on.

**Hashtags:** #wowsignal #space #SETI #astronomy #radiotelescope #unexplained #1977 #science #cosmos #ominous

**Pinned comment:**
Real details: the signal was recorded by Ohio State's Big Ear telescope on 15 Aug 1977. "6EQUJ5" is the printed intensity, one character every 12 seconds (U ≈ 30× background noise), near the 1420 MHz hydrogen frequency. Big Ear didn't move to follow the sky, so Earth's rotation swept each point through its beam in ~72 s. Never detected again despite many searches. Natural explanations have been proposed (a 2024 study suggests a flaring hydrogen cloud), but none is confirmed. The dish in the video is stylised: the real Big Ear was a flat-and-curved-reflector design and was demolished in 1998.
