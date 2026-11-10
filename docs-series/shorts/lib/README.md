# shorts/lib — reusable pipeline for ground-level "What if… the sky" Shorts

Built for `sun-black-hole/`; meant to be reused by the next park-foreground Shorts (other stars replacing the Sun,
Betelgeuse). Everything is numpy/cv2 in **linear HDR float32**, tone-mapped once per frame. CPU only.

Run with `/home/user/ttsenv/bin/python` (numpy, scipy, soundfile, kokoro_onnx). `lib.core` puts
`.../scratchpad/series/shorts-common/pylib` (opencv-python-headless, pillow, onnx) on `sys.path`, so `import lib.core`
before importing cv2 yourself. Shared caches (`stars_42.npz`, `kokoro-timed.onnx`) are under `shorts-common/`.

| module | what |
|---|---|
| `core.py` | colour transforms, `kf`/`ramp`/`ease`, `fbm2` spectral noise, `noise1`, `bbcolor`, `splat`, `Layout(vertical)` (frame size, caption row, HUD row, safe areas: top 12 %, bottom 20 %) |
| `foreground.py` | `Foreground(png, layout, lamps=[(head_x, head_y, base_y) in SOURCE px], hz_frac)`: any RGBA PNG with a transparent sky. Lanczos on premultiplied colour + light unsharp, 1 px alpha erosion, edge-colour decontamination, horizon auto-detect (first row opaque across 97 % of columns), `skyline`. States: `day()`, `night(level)` (shadows flattened with an anisotropic perspective-aware kernel, scotopic desaturation, cold grade), `frost(img, amount, t, level)` (creeping front from the near lawn, follows blade/leaf texture, glints), `lamps_light(img, on, t)` (heads + small ground pools). 16:9: fits width and crops so the horizon sits at `hz_frac` of the height. |
| `sky.py` | `SkyCam(W, H, horizon, f)`; `day_sky` (Rayleigh gradient with (1+cos²) phase, Mie aureole, optional cirrus); `sun_disc` (0.53° limb-darkened HDR disc); `lens_flare` (faint hex ghosts + weak 6-blade spikes, no rainbow spokes); `StarSky.render` (procedural Milky Way plate + 2600 bright stars splatted per frame with airmass-dependent scintillation, chromatic near the horizon, extinction + airglow); `LensField.view` (point-mass lens: stars as point sources with two images and magnifications μ±, galaxies as extended sources via inverse ray-shooting; seeing PSF in the image plane). |
| `text.py` | `Captions(layout, words, emphasis)`: one word at a time, Inter Display Black, orange #FF9210, dark stroke, soft shadow, 45 ms pop-in; `hud_text` (spaced small labels/counters). Drawn on the sRGB frame after tone-mapping. |
| `post.py` | `camera()` zoom about a point + hand-held micro-motion; `bloom`; `tonemap` (filmic shoulder); `finish` (vignette + luminance-weighted grain); `Encoder` (rawvideo pipe → x264 under nice). |
| `voice.py` | `generate(LINES, out_dir, speed)`: Kokoro am_michael **with real word timings**. The stock `kokoro-v1.0.onnx` has no duration output; `make_timed_model()` appends the duration predictor tensor (`/encoder/Clip_output_0`, cast to int64, named `duration`) as a graph output, which kokoro_onnx's `create_timed` then uses. Markup `{CAPTION\|spoken words}` shows one caption for several spoken words (numbers). Writes `<key>.wav` + `words.json`. |
| `audio.py` | `place(words.json, lead)`; `build_voice` (HPF/EQ/compressor/small room); sound design: `drone`, `riser`, `thump`, `ticks`, `shimmer`, `hit`; `duck`; two-pass `loudnorm` (−14 LUFS, −1 dBTP); `write_srt`. |
| `sheet.py` | contact sheet of stills for review. |

Pattern for a new Short (copy `sun-black-hole/`): `audio/narration.py` (LINES with pauses) → `audio/gen_voice.py` →
`short.py` (timeline from word times; `Scene.st(t)` state + `frame(t)`) → `audio/mix.py` → `short.py vert` →
`encode.sh vert` → `thumbnail.py` → `short.py wide` → `encode.sh wide`. Render at most one heavy process at a time,
under `nice -n 10`; about 2–3 s per 1080×1920 frame on the shared box.
