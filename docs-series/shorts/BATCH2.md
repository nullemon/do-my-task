# Shorts batch 2: "swap" format, 9:16 ONLY

Shared rules for every Short in this batch:
- **Format:** the user's favourite, like docs-series/shorts/other-suns/ (read its short.py, README.md, encode.sh, thumbnail.py, audio/).
  - One LOCKED tripod shot.
  - The sky swaps between real-size objects one after another, each with a flash, a chromatic shockwave and beams.
  - The scene is relit per object.
  - A bold readout per object: NAME / a × size or brightness line / a factual line.
  - The end is a white-out back to the opening, so it loops.
- **Closest finished examples to copy from (copy, don't edit):**
  - planets-as-moon/ (planets.py: lit spheres, rings, phase lighting, Solar System Scope textures in scratchpad/series/shorts-common/dl/sss/)
  - other-moons/ (moons.py; USGS moon maps in shorts-common/dl/moons/)
  - star-dates/ (HYG real sky: catalog.py, skygeo.py, mwsky.py)
  - nebula-sky/ (real Hubble/Webb images via GitHub repo unit511/space-wallpapers)
  - sun-black-hole/short_vfx.py (lensing and black-hole VFX)
  - solar-storm/ (city window and lamp layers)
- **OUTPUT: 9:16 ONLY.** 1080x1920, 30 fps, strictly 30–40 s.
  - out/<name>-short.mp4, out/<name>.srt, out/thumb-vertical.jpg, and out/thumb.jpg (1280x720 is still useful for the channel page).
  - NO 16:9 video.
- **Voice:** Kokoro **am_michael**, speed 1.05 (via lib/voice.py with word timings). 80–110 words, with a hook in the first 2 s. Big orange one-word captions at about 50% height. −14 LUFS.
- **USER RULES** (see lib/README.md):
  - Big, bold, colourful VFX spectacle with constant motion.
  - The sky is never pitch black.
  - NO disclaimer small print.
  - Honest science in the narration; record liberties in the README.
- **Backgrounds** (RGBA, transparent sky) in /tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/:
  - A_park.png (big leafy tree, conifer, white building, 2 lamps)
  - A2_park.png (big tree, conifer, house, 2 lamps)
  - B_valley.png (golden-hour mountain valley, path, pines)
  - C_city.png (rooftop city at dusk, lit windows)
- **Network:** npm, PyPI, GitHub and huggingface.co are reachable; most other sites are not.
- **Process:**
  - Scripts go in docs-series/shorts/<name>/. Scratch goes in scratchpad/series/B2-<name>/, under 1.5 GB.
  - Do NOT git commit, and never put media on GitHub.
  - Run ONE heavy process at a time, under `nice -n 10`. Never kill processes you didn't start; track your own PIDs.
  - Never use `-shortest` with subtitles. Verify the duration with ffprobe.
  - Send a 6-frame test sheet to the lead (SendMessage to "main") BEFORE the full render, then wait up to ~10 min for an OK; proceed if there's no reply.
  - Review 10+ frames from the final file.
  - Final report: paths, narration, sources, caveats.

## Queue (lead's tracking)
| # | name | title | bg | status |
|---|---|---|---|---|
| B1 | black-hole-suns | What If Black Holes Replaced Our Sun? | A_park | delivered |
| B2 | moon-closer | What If the Moon Got Closer? | B_valley | delivered |
| B3 | exoplanet-moons | What If Strange Exoplanets Replaced Our Moon? | B_valley | delivered |
| B4 | second-sun | What If Earth Had a Second Sun? | A2_park | delivered |
| B5 | comet-close | What If Comets Passed as Close as the Moon? | A2_park | in progress |
| B6 | galaxies-visible | What If Galaxies Were Bright Enough to See? | C_city | in progress |
| B7 | star-neighbours | What If Famous Stars Were Our Nearest Neighbour? | C_city | in progress |
| B8 | star-clusters | What If Star Clusters Were Close By? | B_valley | in progress |
| B9 | dead-star-suns | What If Dead Stars Replaced Our Sun? | A2_park | queued |
| B10 | moon-ratios | What If Our Moon Matched Other Moons' Size Ratios? | A_park | queued |
