# OMINOUS #3 — 72 SECONDS

A 55-second piece. At night, fog moves over a ridge where a radio telescope stares at the sky, with a red obstruction light blinking on its rim. A few days later, under a desk lamp, a fanfold printout full of 1s and 2s slides past. A line-printer column scrolls up and slows. **6EQUJ5** stops in the middle of the screen, a green pen circles it, and "Wow!" is written in the margin. Then *72 seconds*. The camera looks into the bowl of the dish while a spectrum trace draws a single narrow green spike: *1420 MHz, the hydrogen line*. The sky wheels overhead: *Big Ear looked again. The Very Large Array, 1995 and 1996. Nothing.* The telescope dissolves out of the landscape (*torn down in 1998 to make room for a golf course*). From the empty ridge the camera tilts up into the stars: *The signal was never heard again. We're still listening.* Static, silence, one green blip, cut to black.

- Vertical 1080×1920 design, rendered at 572×1017 (53 %), encoded at 576×1024 and 24 fps. Length 55 s (1320 frames). Rendering the 855 new frames took about 2 h 20 min wall-clock on 4 shared CPU cores: about 7–9 s per frame when the machine was quiet and about 20 s under contention. The 465 reused frames took about 90 min in the first render.
- Accent colour: signal green, used only for the circle, "Wow!", the spectrum spike and the final blip.
- Final video: `../videos/03-72-seconds.mp4`

## Timeline

| t (s) | shot | text |
|---|---|---|
| 0.0 | wide ridge, slow push | IN 1977, SOMETHING / CALLED TO US / FOR 72 SECONDS. |
| 5.0 | 〃 | AUGUST 15, 1977 · BIG EAR RADIO TELESCOPE · OHIO STATE UNIVERSITY |
| 8.3 | desk lamp, printout (shallow focus) | A FEW DAYS LATER, / ASTRONOMER JERRY EHMAN / WAS GOING THROUGH THE PRINTOUTS. |
| 14.3 | printout overlay scrolls | INTENSITY, 12-SECOND STEPS |
| 18.6 | 〃 | 6EQUJ5 circled in green; "Wow!" at 19.75 |
| 22.2 | under the dish | 72 SECONDS. / AS EARTH TURNED, IT DRIFTED THROUGH THE BEAM. |
| 25.4 | into the bowl, spectrum trace | 1420 MHz / A NARROWBAND SIGNAL, RIGHT BY THE HYDROGEN LINE / THE FREQUENCY SCIENTISTS HAD PROPOSED FOR SIGNALS BETWEEN THE STARS. |
| 31.5 | side-on, the sky turning | BIG EAR LOOKED AGAIN. AND AGAIN. AND AGAIN. / THE VERY LARGE ARRAY, 1995 AND 1996. OTHER TELESCOPES SINCE. / NOTHING. |
| 38.5 | wide; the dish dissolves | IN 1998, BIG EAR WAS TORN DOWN / TO MAKE ROOM FOR A GOLF COURSE. |
| 44.5 | empty ridge, tilt up into the stars | THE SIGNAL WAS / NEVER HEARD AGAIN. / WE'RE STILL LISTENING. |
| 52.8–54.6 | | static · silence · one green blip (53.8) · static · cut to black |

## What's real

- **The Wow! signal** was received on **15 August 1977** (about 10:16 pm EDT) by Ohio State University's **Big Ear** radio telescope in Delaware, Ohio, during a SETI survey.
- A few days later the volunteer astronomer **Jerry R. Ehman** went through the computer printout. He circled the characters **6EQUJ5** in red ink and wrote **"Wow!"** in the margin.
- Each character is the signal strength, measured against background noise, for one sample. A new sample was printed every **12 seconds** (about 10 s of integration plus processing time). The scale runs 1–9 and then A–Z. "U" means 30–31 times the noise level, the strongest value in the sequence.
- **72 seconds**: Big Ear did not move to track the sky. It was a transit instrument, so Earth's rotation carried each patch of sky through its beam in about 72 s. The signal rose and fell over that window in the way a source fixed on the sky would. Its frequency was close to the 1420 MHz hydrogen line.
- **1420 MHz**: the signal was narrowband and sat near the 1420 MHz (21 cm) emission line of neutral hydrogen. In 1959 Cocconi and Morrison proposed that frequency as a natural channel for interstellar communication, and Big Ear's SETI survey was listening there.
- **Never heard again**: Big Ear re-observed that part of the sky many times in the weeks and months that followed. Robert Gray searched with Harvard's META system in the late 1980s. Gray and Kevin Marvel searched with the **Very Large Array in 1995 and 1996**, and other telescopes have searched since. None of them detected it again. Its origin is still unexplained. In 2024 a team proposed a natural explanation, a brief brightening of a cold hydrogen cloud; it has not been confirmed.
- **Demolished**: Big Ear was dismantled in **1998**, when its land was sold to developers to expand a golf course.
- Searches for technosignatures continue today (for example Breakthrough Listen and the SETI Institute), which is the basis for "we're still listening".

### Honest liberties
- **The dish is stylised.** The real Big Ear was a Kraus-type telescope: a huge tilting flat reflector and a fixed curved reflector over an aluminium ground plane, about the size of three football fields. A dish reads as "radio telescope" in one second on a phone. The dish in the film stays still and the sky moves past it, which matches the transit idea. Big Ear itself was demolished in 1998, as the video says.
- **The printouts are generic recreations**, both the desk sheet and the overlay. Only the sequence 6EQUJ5 is real. The surrounding 1s, 2s and blanks are randomised noise, and the column layout is simplified.
- **The desk scene is evocative, not documentary.** It shows no person or likeness: just a lamp, a sheet of fanfold paper and a pen. The spectrum trace is an illustration of "narrowband", not the real data, because Big Ear recorded intensity, not a plotted spectrum. Ehman's circle was red ink; here it is the series accent green.
- The 1420 Hz tone in the soundtrack is a nod to 1420 MHz, not the real signal.
- "Something called to us" is a poetic hook. Nobody knows what it was.

## How to run

```bash
# Blender (4.2 – 5.x)
blender -b -P script.py -- --render                 # all frames -> //frames/f_####.png
blender -b -P script.py -- --frames 1,300,600       # stills
#   options: --out DIR/  --percent N  --samples N  --start N --step N  --skip-existing

# No blender binary: bpy as a Python module (how this was made)
/home/user/bpyenv/bin/python -c "import sys; p='script.py'; sys.argv=['blender','--','--render','--out','/path/frames/f_']; exec(compile(open(p).read(),p,'exec'))"

# soundtrack (numpy only) -> soundtrack.wav (48 kHz stereo)
python soundtrack.py

# encode: grain + vignette, static bursts at 52.8–53.3 s and 54.25–54.55 s, a gentle contrast curve
ffmpeg -framerate 24 -i frames/f_%04d.png -i soundtrack.wav \
  -vf "scale=576:1024:flags=lanczos,eq=contrast=1.06:saturation=0.9,vignette=PI/5,noise=c0s=8:c0f=t,noise=c0s=70:c0f=t:enable='between(t,52.8,53.3)+between(t,54.25,54.55)'" \
  -c:v libx264 -preset slow -pix_fmt yuv420p -crf 23 -c:a aac -b:a 192k -shortest ../videos/03-72-seconds.mp4
```

There are three cameras: the ridge and printout camera, the desk camera and a camera for the later shots. Timeline markers switch between them. The desk set sits 3 km away from the ridge in the same scene.

**Frame reuse.** The 55 s cut keeps the first 26 s version's frames for the opening (frames 1–199) and for the printout and "72 seconds" section (v1 frames 206–471 became frames 344–609). `script.py` places those beats at exactly the same frames, shifted by `S3_OFF = 138`, so a full render from scratch gives the same timeline. The other 855 frames were rendered with `--skip-existing`.

Render design, for CPU-only Cycles: 8 samples plus OpenImageDenoise, adaptive sampling, persistent data and 2 bounces. Most of the scene is emission-shaded. The fog is four camera-facing planes with 3D noise and transparency, with no volumetrics. Text is Blender text parented to the camera. Each overlay is `hide_render`-keyed outside its beat so it costs nothing while hidden, and the printout sits on an opaque card so the scene behind it is skipped.

## Posting

**Title:** 72 seconds.

**Caption:**
On August 15, 1977, the Big Ear radio telescope in Ohio picked up a narrowband signal so strong the astronomer reviewing the printout circled it and wrote "Wow!". It lasted 72 seconds, exactly as long as the telescope could see any one point in the sky. It was near 1420 MHz, the hydrogen line, the frequency scientists had proposed for interstellar signals. We've pointed telescopes back at that spot many times since. Nothing. In 1998 the telescope was torn down for a golf course. 🎧 sound on.

**Hashtags:** #wowsignal #space #SETI #astronomy #radiotelescope #unexplained #1977 #science #cosmos #ominous

**Pinned comment:**
Real details: the signal was recorded by Ohio State's Big Ear telescope on 15 Aug 1977. "6EQUJ5" is the printed intensity, one character every 12 seconds (U ≈ 30× background noise). Big Ear didn't move to follow the sky, so Earth's rotation swept each point through its beam in ~72 s. Narrowband, near the 1420 MHz hydrogen line, which Cocconi & Morrison proposed in 1959 as a natural interstellar channel. Never detected again despite many searches (Big Ear itself, META in the late 1980s, the VLA in 1995/96, others since). Natural explanations have been proposed (a 2024 study suggests a flaring hydrogen cloud), but none is confirmed. The dish in the video is stylised: the real Big Ear was a flat-and-curved-reflector design and was demolished in 1998 when its land went to a golf course expansion.
