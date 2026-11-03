# ANDROMEDA — "The Sky That's Coming" (4-minute narrated documentary)

Format: **landscape 16:9, 1920×1080, 24 fps, 240.0 s (5760 frames)**. Final delivery: 1080p master + 4K (3840×2160) lanczos upscale (state honestly that 4K is upscaled).
Same visual language as `ominous/10-the-sky-thats-coming` (read its script.py + README for facts and look): black ridge + one bare wind-bent tree, violet-white accent, thin widely-spaced Inter Light captions, slow camera, grain + vignette at encode. Calm, awe, slightly ominous. NOT cartoonish.

Narration voice: calm, low, documentary (male or female), ~130 wpm, generous pauses. Music: slow ambient drone/pads + sub swells, ducked under voice.
Lower-third captions only for key numbers (not full subtitles); burn-in subtitles are produced separately as an .srt.

## Rendering strategy (CPU only, 4 shared cores — MUST be fast)
Pre-compute all heavy textures ONCE in numpy (galaxy disks, star fields, Milky Way band, nebula glows) as large PNG/EXR files (e.g. 4096–8192 px), then build Blender scenes from **emission planes with image textures** + camera/plane animation. Cycles CPU, 2–4 samples, no denoise, no lights, no bounces. Target ≤ 1.5 s/frame at 1920×1080. Measure on 3 frames first and simplify until it hits that. Shared texture cache dir: `/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures/` (each chapter agent makes its own files with a chapter prefix; don't overwrite others').
Render detached (setsid nohup) with skip-existing/resume. NEVER `pkill -f` broad patterns — kill only your own PIDs.

## Chapter structure (each chapter = exactly 60.0 s = 1440 frames, rendered as its own script + frames + silent mp4)

### CH1 0:00–1:00 "THE SMUDGE" — today's sky
Visual: opens on black, stars fade in, the ridge+tree under a real-looking present-day dark sky; Milky Way band; slow push toward the constellation Andromeda; the faint grey oval of M31 (true size ~3.2°×1°, about 6 full Moons wide but too faint to see its full extent with the eye — show a faint core + a "long exposure" reveal where the full disk fades up); a full-Moon disc outline overlay for scale comparison; then a slow zoom into a detailed Andromeda (dust lanes, M32/M110 satellites).
Narration (timed, seconds from chapter start):
- 2.0: "Look up on a dark autumn night, far from city lights."
- 7.5: "Near the constellation Andromeda, there's a faint smudge. Most people never notice it."
- 15.0: "It isn't a cloud. It isn't a star. It's another galaxy — a spiral of perhaps a trillion suns."
- 24.0: "If your eyes could gather enough light, it would stretch across the sky, about six full Moons wide."
- 33.0: "The light you're seeing left it two and a half million years ago — before our species existed."
- 43.0: "It is the farthest thing most of us will ever see with our own eyes."
- 51.0: "And it is coming toward us."
Captions: "ANDROMEDA (M31)" · "≈ 2.5 MILLION LIGHT-YEARS" · "≈ 6 FULL MOONS WIDE" · "LIGHT LEFT ≈ 2.5 MILLION YEARS AGO".

### CH2 1:00–2:00 "FALLING" — the approach and the uncertainty
Visual: pull out to a god's-eye view of the Local Group: Milky Way disk and Andromeda disk (face-on/inclined textures) in deep space with M33, LMC as small smudges; a thin arrow/trajectory line; an 1912 photographic-plate look (sepia, scratches) for Slipher; a spectrum strip with lines sliding toward blue (blueshift); then branching faint trajectory paths (uncertainty cone) — some merging, some missing.
Narration:
- 1.0: "In 1912, astronomer Vesto Slipher measured its light — and found it shifted toward blue."
- 9.0: "Andromeda was approaching. Today we know it's closing at about a hundred and ten kilometres every second."
- 18.5: "Four hundred thousand kilometres every hour. Roughly the distance to the Moon."
- 26.0: "For decades, astronomers thought a head-on collision was certain."
- 32.0: "But measuring its sideways drift is extraordinarily hard."
- 37.5: "Recent studies using the Hubble and Gaia spacecraft disagree: some give it a coin-flip chance of merging within ten billion years; newer work puts it closer to ninety percent."
- 50.0: "So let's follow the version where it comes."
Captions: "VESTO SLIPHER · 1912" · "≈ 110 KM/S" · "≈ 400,000 KM PER HOUR" · "MERGER CHANCE: ~50% – ~90%".

### CH3 2:00–3:00 "THE SKY CHANGES" — how it looks from Earth over billions of years
Visual: back to the ridge + tree, locked-off wide shot, a year counter top centre ("+1 BILLION YEARS" … "+3.75 BILLION YEARS"). Andromeda grows from the smudge into a bright, detailed spiral; at its largest it spans much of the sky, tilted, dust lanes crisp, rising over the ridge like a second Milky Way; then the Milky Way band itself begins to warp and bend. Night-time beauty shots: tree silhouette under the giant spiral; a slow tilt-up from the ground to the zenith.
Narration:
- 1.0: "In about two billion years, it would no longer be a smudge."
- 8.0: "Night after night, nothing would seem to change. But over millions of years, it would swell."
- 17.0: "Its spiral arms, its dark lanes of dust, its glowing core — all visible to the naked eye."
- 26.0: "Some four billion years from now, it could fill the sky — a second galaxy, hanging over the horizon."
- 37.0: "Then our own Milky Way would begin to bend, pulled out of shape by the gravity of its neighbour."
- 47.0: "Two galaxies, a hundred billion stars and more each, falling into one another."
Captions: year counter; "IF THEY MERGE" label under counter.

### CH4 3:00–4:00 "MILKOMEDA" — collision, merger, ending
Visual: the sky fills with tidal tails and bright pink star-forming knots (starburst) — the most beautiful frames of the film; the two cores circling; then a slow dissolve into one smooth glowing elliptical with faint shells ("Milkomeda") filling the sky; the tree silhouette; final pull back up into space showing the merged elliptical galaxy alone; fade to black; title card.
Narration:
- 1.0: "And yet, almost no stars would collide. The space between them is simply too vast."
- 9.5: "But the clouds of gas would. They'd crash together and ignite, lighting the sky with newborn stars."
- 19.0: "Over billions of years, the two spirals would settle into one great, glowing elliptical galaxy."
- 28.0: "Astronomers already have a name for it: Milkomeda."
- 34.0: "Our Sun would likely survive — perhaps flung to a new orbit, far from where it is today."
- 42.0: "But no one on Earth will see it. Long before then, the Sun will have grown too bright for oceans, or for us."
- 52.0: "Someone, somewhere, may be watching. It won't be us."
- End: title card "THE SKY THAT'S COMING" at 56–60 s, then black.
Captions: "+ 5 BILLION YEARS" (approximate, IF THEY MERGE) · "MILKOMEDA".

## Fact notes (keep honest)
Distance ~2.5 Mly; radial velocity −301 km/s heliocentric (~−110 km/s relative to Galactic centre); Slipher 1912/1913 measured ~300 km/s approach; ~1 trillion stars (estimates); naked-eye apparent size of the full disk ~3.2° (≈6 full Moons) though only the core is easily seen; Sawala et al. 2025 Nature Astronomy (~50% within 10 Gyr); Wu et al. 2026 arXiv:2603.22863 (~90%); NASA 2012 illustration sequence (2, 3.75, 3.85–3.9, 4, 5.1, 7 Gyr); stars rarely collide; Earth's oceans lost in ~1 Gyr as Sun brightens; Milky Way ~100–400 billion stars ("a hundred billion stars and more" is safe).
