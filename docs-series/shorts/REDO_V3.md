# REDO v3: storytelling narration (user-approved style "C", 14 Nov)

User feedback: the narration was too fast and "not interesting". The visuals are good. Redo the VOICE and SCRIPT of each Short and re-time the visuals to it. Output 9:16 only.

## Script style (the most important part)
- Tell a short STORY, not a fact list. 55–75 words. Fewer numbers (at most one per beat); put other numbers in the on-screen readouts.
- Build suspense: open with "Imagine…" or "What if…", then a pause before each reveal ("Now…", "And then…"). End on an emotional or twist line.
- Short sentences. Use "..." for a dramatic beat.
- Reference script (Black Holes):
  "Imagine our Sun... / replaced by a black hole. / First, one with exactly the same mass. / Just six kilometers wide. / Earth keeps orbiting... / but the light is gone. / Forever. / Now... Sagittarius A star. / Four million Suns. / Its shadow would cover a quarter of the sky. / And TON 618. / Sixty-six billion Suns. / Its edge... is bigger than our entire solar system. / Suddenly... / the Sun seems kind."
- Keep the facts honest (same science as before).

## Voice (exact)
- Kokoro voice style = 0.7 × am_michael + 0.3 × am_onyx (`k.get_voice_style()` vectors blended; pass the array as `voice`). Speed **0.86**, lang en-us.
- One TTS call per short line/phrase (as in the reference). Pauses: 0.4–0.5 s between phrases, 1.0–1.2 s at each beat change / before a reveal.
- Word timings: keep using lib/voice.py's timed-model approach; it must accept the blended style vector (wrap or copy it, don't edit lib/ in place).
- Post chain on the voice (pitch-only, so the timings stay valid):
  `aresample=48000,rubberband=pitch=0.944:formant=preserved,highpass=f=60,equalizer=f=140:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=1.5,equalizer=f=7000:t=q:w=1:g=-1.5,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,aecho=0.85:0.5:35|65:0.12|0.07`
- Music bed under the voice as before, ducked. Final mix −14 LUFS, −1 dBTP.
- Reference sample: scratchpad/voiceAB/ (C2.wav, mixC.wav) and lib/voice_v3_sample_gen.py.

## Length
Up to **50 s** is fine (the user OK'd it). Aim for 42–50 s. Give the reveals time to breathe.

## Visuals
Keep all visuals, fixes and readouts. Re-time the beats, swaps, captions and readouts to the new word timings. The captions stay as big orange words.

## Output (per Short)
- out/<name>-short.mp4 (1080x1920, 30 fps). Overwrite the old one if present.
- Updated out/<name>.srt. The thumbnails can stay; regenerate them only if they're missing.
- 9:16 ONLY.

## Process
- Run one heavy process at a time, under `nice -n 10`. Never kill processes you didn't start.
- Render in segments if possible, so a container restart loses little.
- Don't use `-shortest` with subtitles. Verify the duration with ffprobe and check about 8 frames.
- Do NOT git commit, and never put media on GitHub.
- After EACH Short is finished, SendMessage to "main" with: the path, duration, and new script.
