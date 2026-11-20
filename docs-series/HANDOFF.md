# HANDOFF: space YouTube channel (read this first)

This is everything a new Claude session needs to carry on with this channel. It covers what the owner wants, what's already made, how the pipeline works and how to set it up again from scratch.

Repo: `nullemon/do-my-task`, branch `claude/kind-maxwell-02hzfk`. Everything lives under `docs-series/`.

---

## 1. The channel and the owner's rules (most important)

The channel makes space videos. It is **not monetised**, so non-commercial licences (CC BY-NC etc.) are fine. Credit them in the README.

The current focus is **YouTube Shorts in the "swap" format**:
- One **locked** camera shot over a real landscape photo with a transparent sky (the owner supplies these).
- The sky swaps between real-size objects. Each swap has a bright flash or shockwave, the scene is relit for the new object, readouts sit at the top and a big orange one-word caption sits in the middle.
- The video loops back to its start.

### Hard rules (all from the owner; never break them)
1. **SOUND: voice first, clean mix.** This is the owner's biggest complaint. Older videos had too much music and SFX with "weird noises", and you couldn't hear the voice. The owner said those videos might not even get used.
   - Use **only** `docs-series/shorts/lib/mix_clean.py`, i.e. `clean_voice()` and then `mix()`.
   - The only extras allowed are its very soft pad and a gentle whoosh at each swap. No booms, rumbles, risers, crackles, drones, arpeggios or impact hits.
   - No echo, reverb or pitch shift on the voice. Don't use the old `REDO_V3.md` post chain (rubberband/aecho), which is superseded.
   - Check that the bed (music + whoosh, voice muted) is **≥ 20 dB under** the full mix. The batch-4 Shorts landed at 23–25 dB.
   - Final mp4: about **−14 LUFS**, true peak **≤ −1.5 dBTP**, AAC 192k.
2. **9:16 only** (1080x1920, 30 fps) for Shorts.
3. **Locked camera.** No zooms or shake.
4. **Bold, colourful VFX:** big sky effects, saturated light, glowing objects and flashes. The night sky stays deep blue and readable, never pitch black. No glossy/plastic or painted-brush looks.
5. **No disclaimer small print** on screen ("not to scale", "illustration", "enlarged", "time-lapse"…). Keep only factual readouts. Record any liberties in the Short's README instead.
6. **Voice: Kokoro TTS, style "C"**, an exact blend of **0.7 × am_michael + 0.3 × am_onyx** at **speed 0.86**, en-us. Use one TTS call per phrase, with pauses of 0.4–0.5 s between phrases and 1.0–1.2 s before a reveal. The owner tested many other open TTS models (Chatterbox, Zonos, StyleTTS2, F5, XTTS v2, Dia, Piper, am_fenrir) and rejected them all.
7. **Script = a short STORY, not a fact list:**
   - 55–75 words, 42–50 s.
   - Open with "Imagine…" or "What if…", use "Now…" / "And then…" before reveals, and end on an emotional or twist line.
   - Short sentences with "..." beats, and at most one number per beat (other numbers go in the on-screen readouts).
   - Reference script: *"Imagine our Sun... / replaced by a black hole. / First, one with exactly the same mass. / Just six kilometers wide. / Earth keeps orbiting... / but the light is gone. / Forever. / Now... Sagittarius A star. / Four million Suns. / Its shadow would cover a quarter of the sky. / And TON 618. / Sixty-six billion Suns. / Its edge... is bigger than our entire solar system. / Suddenly... / the Sun seems kind."*
8. **Honest science.** Verify every number, and list sources and liberties in each Short's README.
9. **Media never goes on GitHub.** Only commit scripts and docs. `out/` folders and mp4/wav/png are gitignored.
10. **Delivery is via Gofile.** Upload finished videos to the owner's Gofile folder (link below). The owner prefers **one message with the link and the full file list when a whole batch is done**, not one message per video.
11. Delete local media only after the owner confirms they've downloaded it, and **never delete thumbnails**.

### The owner's review style
The owner reviews test frames and asks for visual fixes, typically: make the object bigger or more visible, show more spectacle and motion, make the text readable, and don't let the flash wash everything out. Show a 6-frame test sheet before each full render.

---

## 2. What's been made (all delivered on Gofile)

Gofile folder: **https://gofile.io/d/xpiUozuT**. Uploading needs the owner's Gofile account token and that folder's id. They're deliberately **not** stored in this repo, so ask the owner for them.

### Shorts (folders in `docs-series/shorts/`)
- **Batch 4 (clean mix; the current standard), 15–20 Nov, files `b4-<name>-short.mp4`:**
  - moon-explodes
  - earth-spins-faster
  - venus-as-moon
  - earth-stops-spinning
  - black-hole-flyby
  - moons-sky-views
  - dark-matter-visible
  - sun-twice-as-big
  - ringed-moon
  - biggest-explosions
- **Older Shorts** (louder mixes the owner disliked; they could be re-mixed with `mix_clean` if wanted):
  - The first queue, S1–S16, is in `shorts/QUEUE.md`.
  - BATCH2: black-hole-suns, moon-closer, exoplanet-moons, second-sun, comet-close, galaxies-visible, star-neighbours, star-clusters, dead-star-suns, moon-ratios.
  - BATCH3 is listed in `shorts/BATCH3.md`.
  - The REDO v3 re-voicing of 18 Shorts was uploaded as `v3-<name>-short.mp4`.
- **The format the owner liked best:** other-suns (S4), the "swap" format that every later Short copies.

### Long documentaries (16:9, 4–6 min)
These are in `docs-series/01-…` to `13-…`. The brief for them is `docs-series/BRIEF.md`, and they use Blender + numpy. They were all delivered earlier; this work is finished.

---

## 3. How a Short is built

Each Short is a folder `docs-series/shorts/<name>/` holding:
```
short.py           timeline + frame(t) renderer (numpy, linear HDR -> tonemap -> captions)
audio/narration.py LINES (phrases + pauses)
audio/gen_voice.py Kokoro -> <key>.wav + words.json (real word timings)
audio/mix.py       lib.mix_clean (via lib.b4_kit.make_mix) + bed check
encode.py/.sh      mux AAC 192k + soft subs, measure LUFS/dBTP on the final mp4
thumbnail.py       thumb.jpg (1280x720) + thumb-vertical.jpg (1080x1920)
README.md          script, numbers, sources, liberties
out/               <name>-short.mp4, <name>.srt, thumbs   (gitignored)
```
**The best templates to copy are the batch-4 folders**, e.g. `ringed-moon/` or `venus-as-moon/`.

Order of work for a Short:
1. Write the script.
2. Generate the voice.
3. Lock the beats and swaps to the word timings.
4. Make the 6-frame test sheet and get the owner's OK.
5. Mix and run the bed check.
6. Render in restart-safe segments under `nice -n 10`.
7. Encode.
8. Check 8 frames plus the loudness of the final mp4.
9. Upload.

### Shared library `docs-series/shorts/lib/` (see `lib/README.md`)
- `core.py` has colour maths, noise and the layout (safe areas: top 12 %, bottom 20 %).
- `foreground.py` loads the transparent-sky photo, finds the horizon and provides night/relight states.
- `sky.py` covers the day sky, sun disc, star sky (real HYG stars) and gravitational lensing.
- `space.py` holds planet and globe helpers.
- `text.py` draws the orange one-word captions (Inter Display Black, #FF9210) and the readouts.
- `post.py` does bloom, tonemapping and the encoder.
- `voice.py` handles Kokoro with **word timings**. The stock model has no duration output, so `make_timed_model()` patches the onnx and saves `kokoro-timed.onnx`.
- `v3_kit.py` provides `style()` (the 0.7/0.3 blend), `generate()` and `render()` (segments).
- **`mix_clean.py`** is the only mixer to use (rule 1).
- **`b4_kit.py`** provides `generate`, `dry_voice`, `make_mix` (with the bed check) and `encode` (with LUFS/dBTP).
- `swapfx_b4.py` contains the batch-4 swap flash and shockwave effects.
- `audio.py`, `audio_v3.py` and `voice_v3.py` are **old**. Don't use their sound design.

---

## 4. Setting it up again in a new session or account

The code has some **hard-coded paths** from the old container, so change them when you move:
- `lib/core.py` sets `COMMON` = `.../scratchpad/series/shorts-common` (pylib, `stars_42.npz`, `kokoro-timed.onnx`, `dl/` textures).
- `lib/sheet.py` and `lib/space.py` point at the scratchpad, including `dl_globe/package/example` for the NASA Earth textures from the `three-globe` npm package.
- Kokoro models are at `/home/user/tts-models/kokoro-v1.0.onnx` and `voices-v1.0.bin`.
- The Python venv is `/home/user/ttsenv`.

Easiest fix: point those constants at new folders, e.g. a single `ASSETS` directory.

Setup steps:
```bash
python3 -m venv /home/user/ttsenv
/home/user/ttsenv/bin/pip install kokoro-onnx==0.6.1 onnxruntime numpy scipy soundfile onnx opencv-python-headless pillow
mkdir -p /home/user/tts-models && cd /home/user/tts-models
# Kokoro v1.0 model files (github.com/thewh1teagle/kokoro-onnx releases, tag model-files-v1.0)
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
# ffmpeg (6.x) must be installed; NASA globe textures: npm pack three-globe  (example/img)
```
Then run `lib/voice.py`'s `make_timed_model()` once to create `kokoro-timed.onnx`.

**The assets zip** on Gofile (`HANDOFF-assets.zip`, in the same folder) contains:
- `backgrounds/`: the 12 transparent-sky PNGs (941x1672 RGBA):
  - A_park, A2_park, B_valley, C_city
  - 01_desert, 02_snowy_mountain_village, 03_calm_lake_wooden_pier (the lake must mirror the sky), 04_city_street_at_night
  - 05_tropical_beach, 06_farm_field_barn, 07_mountain_observatory, 08_suburban_backyard
- `thumbnails/`: every thumbnail made so far (100 files, named `<video>__thumb*.jpg`).
- `textures/`:
  - `shorts-common-dl` (moon/planet maps, Pluto, threex.planets)
  - `stars_42.npz` (star cache)
  - `globe-img` (NASA Blue Marble, night lights, clouds)

Put these back where the paths above expect them, or update the paths.

### Machine notes
CPU only, shared. Rendering takes about 2–3 s per 1080x1920 frame. Render in segments so a container restart loses little, run one heavy process at a time, and never `pkill` broad patterns.

---

## 5. Checking a Short before delivery
```bash
ffmpeg -v error -y -i out/<name>-short.mp4 -vf "fps=1/5.5,scale=200:-1,tile=8x1" -frames:v 1 sheet.jpg   # look at it
ffmpeg -nostats -i out/<name>-short.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -A12 Summary          # ~-14 LUFS, <= -1.5 dBTP
```
`b4_kit.bed_check` gives the bed-vs-mix margin, which must be ≥ 20 dB.

---

## 6. Ideas not made yet (ask the owner first)
- Re-mix the older Shorts with `mix_clean` so they sound as clean as batch 4. The visuals are fine; only the audio needs changing.
- New swap Shorts that build on what worked:
  - What if the Moon were made of… (ice / iron / gas)
  - Your sky from the Moon's surface
  - What if Earth had Saturn's moons
  - Famous exoplanets rising over the beach
  - What if the Milky Way were brighter
  - Sunsets with two or three suns
