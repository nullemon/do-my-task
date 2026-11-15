# Shorts batch 4: 10 new Shorts, proper clean sound, 9:16 ONLY

The user's verdict on ALL previous Shorts: "too much sound effect and weird noises, you can't even hear the voice". This batch must sound clean and professional. The audio rules below override every older brief.

## AUDIO (strict, non-negotiable)
- Use **lib/mix_clean.py** for the whole mix: `clean_voice(dry)` then `mix(voice, dur, swaps=[...], key=...)`. Do NOT add any other sound: no booms, rumbles, risers, crackles, shimmer, sizzle, drones, arpeggios or impact hits. The only extras are the module's soft pad and its gentle whoosh at swaps.
- Voice: Kokoro 0.7 am_michael + 0.3 am_onyx blended style, speed 0.86, one TTS call per phrase (see lib/v3_kit.py `generate` for word timings).
- Do NOT use the v3 post chain's pitch shift and echo (rubberband/aecho). Use `clean_voice` only: no echo or reverb.
- Pauses: 0.4–0.5 s between phrases, 1.0–1.2 s before reveals.
- Encode the AAC at 192k. Measure on the final mp4: about −14 LUFS, true peak ≤ −1.5 dBTP.
- Before the full render, listen-check by measuring: the loudness of the music+whoosh bed alone (voice muted) must be ≥ 20 dB below the full mix.

## SCRIPT
Story style as in REDO_V3.md: "Imagine…" / "What if…", short sentences, "..." beats, one number per beat at most, and an emotional or twist ending. 55–75 words, 42–50 s. Honest science, verified numbers, liberties recorded in the README, no disclaimer small print on screen.

## VISUALS
The swap format, as in other-suns and BATCH3.md:
- One LOCKED shot; each swap has a flash and shockwave; the scene is relit per object.
- Readouts at the top, big orange one-word captions.
- The sky is never pitch black, and the end loops.
- Objects sit BEHIND the foreground plate (fully opaque where alpha > 0.9).
- No glossy/plastic looks and no painted, brush-stroke textures.

## BACKGROUNDS
In /tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/: A_park, A2_park, B_valley, C_city, 01_desert, 02_snowy_mountain_village, 03_calm_lake_wooden_pier (the lake must mirror the sky), 04_city_street_at_night, 05_tropical_beach, 06_farm_field_barn, 07_mountain_observatory, 08_suburban_backyard.

## OUTPUT AND PROCESS
- docs-series/shorts/<name>/out/<name>-short.mp4 (1080x1920, 30 fps), <name>.srt, thumb-vertical.jpg, thumb.jpg.
- Render in restart-safe segments under `nice -n 10`, one heavy process at a time, and never kill others' processes.
- Send a 6-frame test sheet to "main" before the full render; wait ~10 min for a reply.
- When finished, SendMessage "main" with the path, duration, script and the bed-vs-mix dB measurement.
- No git commits, and no media on GitHub.
