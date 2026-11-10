# Space documentary series — shared brief (same pipeline as andromeda-doc)

Each video: **16:9 1920×1080, 24 fps, 4:00–5:00 long (target 4:30 = 270 s)**, narrated, cinematic, calm-awe-slightly-ominous tone, same look family as `/home/user/do-my-task/andromeda-doc` (thin widely-spaced Inter Light captions, slow camera, grain + vignette at final encode, minimal elegant diagrams). Every on-screen and spoken fact must be accurate — verify with WebSearch (load via ToolSearch "select:WebSearch") and cite sources in README; hedge approximate numbers honestly.

## Reuse what exists (read these first)
- `/home/user/do-my-task/andromeda-doc/PLAN.md`, `AGENT_RULES.md` — format, render rules.
- `/home/user/do-my-task/andromeda-doc/ch1..ch4/` — Blender scripts (sky domes, star maps, ridge/tree, text, pre-baked numpy textures, speed tricks).
- `/home/user/do-my-task/andromeda-doc/audio/` — Kokoro TTS (venv `/home/user/ttsenv`, models `/home/user/tts-models/`, voice **am_michael**, speed ~0.94, processing chain), music bed generator `mix.py`, ducking, loudnorm −14 LUFS, `assemble.sh`, SRT. Use the SAME voice for the whole series.

## Workflow per video (you do all of it)
1. Write `SCRIPT.md`: narration (~550–650 words, ~130 wpm, generous pauses) split into timed beats + shot list. Hook in the first 3 seconds. Payoff at the end.
2. Generate voice first (Kokoro), measure real line durations, then lock the timeline to the voice.
3. Build visuals in Blender (bpy 5.1.2 module at `/home/user/bpyenv/bin/python`, Cycles CPU only — no GPU; in 5.x set image_settings.media_type='IMAGE' before file_format='PNG'). Split into shots/scenes, each its own render.
4. **CPU is shared by 4 videos on 4 cores** → be very economical: pre-baked numpy textures on emission planes, 2–4 spp, no denoise, no bounces. **Reuse frames**: for locked-off or slow shots render a background plate once (or at low frame count) and do text/counters/fades/slow zooms in ffmpeg (overlay, zoompan, drawtext with Inter font, xfade). Only render true 3D motion frame-by-frame. Aim for total render ≤ ~2 h per video.
5. Music bed (numpy) + ducking + loudnorm (−14 LUFS, ≤ −1 dBTP), SRT subtitles.
6. Final: `<name>-1080p.mp4` (x264 crf 18, AAC 256k, faststart, embedded subtitle track), `<name>-1080p-hq.mp4` (≤ 380 MB, for chat delivery), `<name>-4k.mp4` (lanczos upscale, crf 20 — labelled upscaled), `<name>-4k-share.mp4` (≤ 480 MB).
7. Check 6+ frames from the final mp4 with Read, and audio levels (ebur128).

## Rules
- Folder: `/home/user/do-my-task/docs-series/<NN-name>/` (scripts, SCRIPT.md, README.md). Big media (frames, wavs, mp4s) go in `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/<NN-name>/`, final mp4s in `/home/user/do-my-task/docs-series/<NN-name>/out/` (gitignored).
- Launch long renders/encodes detached (`setsid nohup … &`) with resume/skip-existing. NEVER `pkill -f` broad patterns — kill only your own PIDs.
- Don't touch other videos' folders. Don't git commit.
- Report: final file paths + sizes + durations, render time, voice/audio notes, fact sources, honest limitations.

## Wave 2 ("Earth's Extremes") overrides
- Length **4:00–6:00** (target ~5:00 = 300 s), narration ~600–750 words.
- **Disk is tight (≈9 GB free shared by 3 videos):** keep your scratch ≤ 2.5 GB. Delete intermediate frames once a shot is encoded to a lossless/near-lossless segment (x264 crf 14). Check `df -h /` before big steps.
- **Memory:** avoid running more than 2 heavy processes yourself at once (an earlier agent was OOM-killed).
- Folders: `docs-series/05-mariana-trench/`, `06-lituya-bay/`, `07-megalodon-to-scale/`.

## Wave 3 ("Space, round two") overrides — these win over anything above
- Length **4:00–6:00** (target ~5:00), narration ~600–750 words, same voice (am_michael @ 0.94).
- **3 videos render at once on 4 cores / 15 GB RAM / ~20 GB free disk.** Keep scratch ≤ 3 GB, at most 2 heavy processes of your own at a time, delete frames once a shot is encoded to a segment. Check `df -h /` before big steps.
- **Look must be premium** (the user rejected flat/clip-art visuals): real textures where they exist (NASA Blue Marble / night lights / clouds ship in the `three-globe` npm package under `example/img` — `npm pack three-globe`; npm, PyPI and GitHub releases are reachable, most other sites are not), proper lighting, atmosphere glow, bloom, depth; clean thin typography. No stick-figure silhouettes, no flat vector shapes as hero imagery. Reference: `docs-series/03-you-are-not-sitting-still/visuals/thumbnail_earth.py` (numpy analytic Earth) and the 05/07 films.
- **Deliverables** in `docs-series/<NN-name>/out/`: `<name>-1080p-hq.mp4` (≤ 380 MB), `<name>-4k.mp4` (lanczos upscale, **≤ 740 MB total** so it can be cut into two halves under 380 MB), plus `<name>.srt`, and a **YouTube thumbnail** `thumb.jpg` 1280×720 in the style of thumbnail_earth.py (photoreal hero object, 3–5 huge words, yellow key number/word). No other encodes.
- Videos are delivered in chat only — never put media on GitHub, don't git commit.
- Facts: verify every number with WebSearch; list sources in README; hedge honestly.
- **Detail bar (user: "highly detailed, not AI shape-ish"):** no hero object may be a bare primitive or flat gradient. Real texture maps or multi-octave procedural detail (albedo + displacement + roughness) on everything seen close; spacecraft with real proportions, panel lines, blankets, struts; rocky bodies with craters/boulders/regolith; Earth with clouds, cloud shadows, ocean glint, layered atmosphere; Sun with granulation and corona; realistic star fields with Milky Way structure; hard single-key lighting, deep shadows, bloom, grain. Prefer fewer, richer shots with slow camera moves over many thin ones. Longer render time is acceptable. Review 8+ final frames at full size against "premium space documentary" and rebuild any shot that reads as simple shapes.
- **Both aspect ratios:** also deliver `<name>-vertical.mp4` (1080×1920, full length, ≤ 380 MB) and `thumb-vertical.jpg` (1080×1920). Proper vertical recomposition, not a blind centre crop: plan shots so the hero sits in the central column (taller plates / second camera where needed), re-lay all text and diagrams for vertical (larger, stacked, clear of top 12% and bottom 20%), check 6+ vertical frames.
