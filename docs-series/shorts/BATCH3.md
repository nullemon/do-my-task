# Shorts batch 3: new backgrounds, swap format, storytelling voice, 9:16 ONLY

Read BATCH2.md (format, user rules, examples, process) and REDO_V3.md (the APPROVED storytelling script style and voice). Both apply in full. Where they conflict, REDO_V3.md wins for voice and length (up to 50 s).

**Format.** The user's favourite format:
- One LOCKED shot.
- The sky swaps between real-size objects/scenes, each with a flash, a chromatic shockwave and beams.
- The scene is relit for each swap.
- Bold readouts and big orange one-word captions.
- No disclaimer small print.
- The sky is never pitch black.
- The end loops back to the opening.

**Voice.** REDO_V3 exactly:
- 0.7 am_michael + 0.3 am_onyx at speed 0.86, one TTS call per phrase.
- Pauses: 0.4–0.5 s between phrases and 1.0–1.2 s before reveals.
- The v3 post chain, then a low-pass at 17 kHz before AAC.
- 55–75 words, 42–50 s, −14 LUFS, −1 dBTP measured on the final mp4.
- Shared helpers already exist in docs-series/shorts/lib/: v3.py, v3_kit.py, voice_v3.py, audio_v3.py, render_v3.py, v3_redo_q5.py. Reuse one; don't edit lib in place.

**New backgrounds.** Each is 941x1672 RGBA with a transparent sky; upscale to 1080x1920. They're in /tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/:
1. 01_desert.png: golden dunes; sky about 63%.
2. 02_snowy_mountain_village.png: snowy chalets with lit windows, pines, an alpine ridge; sky about 49%.
3. 03_calm_lake_wooden_pier.png: a mirror-calm lake, a pier, a pine shore; sky about 62%. The lake MUST reflect the sky: mirror the sky render into the water region with slight ripple distortion and darkening. Keep it calm and convincing; the user hated fake water once.
4. 04_city_street_at_night.png: a skyscraper canyon, neon, a wet street; sky about 35%, a narrow strip up the middle.
5. 05_tropical_beach.png: palms, white sand, calm turquoise shallows, a hut; sky about 46%.
6. 06_farm_field_barn.png: wheat, a red barn, a silo, an oak; sky about 45%.
7. 07_mountain_observatory.png: a white dome on a rocky summit, distant peaks; sky about 79%.
8. 08_suburban_backyard.png: lawn, fence, trampoline, shed, string lights; sky about 74%.

**Output.**
- docs-series/shorts/<name>/out/<name>-short.mp4 (1080x1920, 30 fps), out/<name>.srt, out/thumb-vertical.jpg and out/thumb.jpg (1280x720).
- Render in restart-safe segments.
- Send a 6-frame test sheet to "main" before the full render; proceed after ~10 min if there's no reply.
- SendMessage "main" when each Short is finished: path, duration and script.
- One heavy process at a time, under `nice -n 10`. Never kill processes you didn't start.
- No git commits, and no media on GitHub.
