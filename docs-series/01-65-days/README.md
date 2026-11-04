# 01 — 65 DAYS

*If Earth suddenly stopped orbiting, we'd fall into the Sun. It would take about 65 days.*

A 4:26 narrated documentary (1920×1080, 24 fps) in the series look (thin widely-spaced Inter Light/ExtraLight
type, slow camera, grain + vignette at the final encode). A day-by-day countdown seen from one headland with
a bare wind-bent tree: at first nothing seems to happen, then the fall accelerates, and the final hours fill
the sky with the photosphere. It ends on the orbit itself: a fall that keeps missing.

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with times, shot list, captions |
| `timeline.py` | the locked timeline: voice line starts, shots, video-time → story-time mapping |
| `physics/fall.py` | exact radial free-fall solution → `physics/table.csv` (per day) + `fine.json` |
| `gen_textures.py` | numpy: star map, Moon albedo, Worley granulation tiles, low-frequency photosphere map |
| `blender/shots.py` | Blender 5.1.2 (bpy module, Cycles CPU): landscape silhouettes, orbit Earth still, Moon-shot stills, the dive (frame-by-frame) |
| `comp.py` | numpy/PIL compositor: sky, Sun disc (exact sphere geometry), sea glints, haze, HUD, diagrams, captions → silent shot segments |
| `audio/narration.py`, `audio/gen_voice.py` | narration text, Kokoro TTS (am_michael, speed 0.94) |
| `audio/mix.py`, `audio/placement.json` | voice chain, numpy music bed (C minor; ticks on every day change; heartbeat + riser + roar into impact; hard cut to silence at impact), ducking, two-pass loudnorm |
| `65-days.srt` | subtitles from the real placed voice timings (also muxed as a soft track) |
| `assemble.sh` | concat + grain/vignette + mux → the four deliverables in `out/` |

Rebuild: `python3 physics/fall.py` → `python3 gen_textures.py` → Blender stills/dive (see `blender/shots.py` header)
→ `/home/user/ttsenv/bin/python audio/gen_voice.py && /home/user/ttsenv/bin/python audio/mix.py`
→ `python3 comp.py open orbit landA diagram landB moon landC dive black orbitdg title` → `bash assemble.sh`.

## The physics (everything on screen comes from `physics/fall.py`)
Earth starts at rest 1 AU from a point-mass Sun (GM☉ = 1.32712440018×10²⁰ m³/s², IAU) and falls radially.
Closed form: t(r) = √(r₀³/2GM)·[√(x(1−x)) + arccos √x], x = r/r₀. To the centre: t = π/(2√2)·√(a³/GM) =
**64.57 days** (= one year / 4√2). Earth's surface touches the photosphere (R☉ = 695,700 km) at **64.56 days**.

| milestone | when (exact model) | values |
|---|---|---|
| end of day 1 | t = 1 d | fallen 22,000 km, 0.51 km/s |
| day 10 | t = 10 d | fallen 2.2 million km, Sun 2 % wider, sunlight ×1.03 |
| one month | t = 30 d | 14 % of the way, 17 km/s, sunlight ×1.35 |
| Venus's orbit (0.723 AU) | t = 41.2 d (day 42) | 26 km/s, sunlight ×1.9 (×2.0 at 42.2 d) |
| halfway (0.5 AU) | t = 52.8 d | **first half 52.8 d, second half 11.7 d** |
| Mercury's orbit (0.387 AU) | t = 57.0 d (day 57) | 53 km/s, sunlight ×6.7, **7.6 days left** |
| end of day 60 / 62 / 63 | | sunlight ×12.4 / ×25.6 / ×48 |
| 64 days elapsed | T − 13.4 h | 149 km/s, Sun 13.5× wider, sunlight ×181 |
| T − 8 h | | Sun 10.0° (18.8× today's 0.533°), sunlight ×353 |
| T − 1 h | | Sun 36° (68×), 342 km/s |
| fluid Roche limit (2.44·R☉·(ρ☉/ρ⊕)^⅓ ≈ 1.55 R☉) | T − 11 min | 495 km/s |
| impact | t = 64.56 d | **613 km/s** vs solar escape speed √(2GM/R☉) = 617.7 km/s; Earth's width (12,742 km) in 21 s |

**Temperature (rough, stated on screen as a rough model).** HUD "EST. AVERAGE TEMP*" = today's 15 °C mean
(288 K) scaled as (sunlight)^¼, i.e. instant radiative equilibrium with today's albedo and greenhouse effect held fixed.
It ignores thermal lag (oceans), clouds, runaway-greenhouse feedback and day/night contrasts — so early on the real
world would lag behind it, later feedbacks could make it worse. Values: 37 °C at day 30, ~70 °C at Venus's orbit,
100 °C on day 49, ~190 °C at Mercury's orbit. (Alternative no-greenhouse equilibrium, albedo 0.3, is in `table.csv`.)

**The oceans do not boil away.** Energy to heat all oceans (1.335×10²¹ kg) from 15 °C to 100 °C and vaporise them:
≈3.5×10²⁷ J. Integrating all sunlight Earth absorbs (albedo 0.3, cross-section πR⊕²) over the entire fall gives
≈1.3×10²⁵ J — 0.36 % of that, enough to boil off only the top ≈15 m of ocean even if every joule went into the sea.
This is why the film says the oceans are "too deep" — a deliberate correction of the popular "the oceans boil" claim.

**The Moon.** Assumed to stop with Earth (the Earth–Moon barycentre stops); it keeps its ~1 km/s orbital motion
around Earth, so both fall together. The Sun's tidal pull (Hill radius r_H = d·(m⊕/3M☉)^⅓) shrinks below twice the
Moon's distance around day 52–53 and below the Moon's distance on day 61, so "in these last days the Sun's pull
begins to tear it away". It cannot escape: with ≤1 km/s sideways at ≤1 AU its closest approach to the Sun is
< 100,000 km, far inside the Sun — it falls in too.

**Seasons freeze.** With no orbital motion the Sun stays over the same latitude (ignoring the slow precession).

**Sky view.** Camera 40° horizontal FOV, the Sun's centre ~6° above a sea horizon. The Sun's disc is drawn with
exact sphere geometry (angular radius asin(R☉/r); limb darkening via μ; surface coordinates from the true ray–sphere
hit point), so the granulation (≈1,000 km cells, two pre-baked Worley tiles + mip levels) and the two sunspot groups
appear at their real angular scale — visible only in the last half hour. Exposure adapts as sunlight grows (a real
eye could not look); in the final hours the disc is shown "filtered" (orange, like a solar-filter photo).

## Honesty notes / simplifications
- Stopping a planet is physically impossible (and doing it suddenly would itself be catastrophic) — said twice
  (voice + caption "A THOUGHT EXPERIMENT · NOTHING COULD REALLY STOP A PLANET").
- Point-mass Sun, no other planets, no drag from the corona/solar wind, no Sun–Earth tidal energy losses before contact.
- The "time compressed" segments: the day counter / hours clock always show the true model state for the moment
  shown; the video speeds through story time (piecewise-linear map in `timeline.py`). The dive uses the real fall
  kinematics, compressed ~30× (T − 12 min → impact in 21 s).
- "Sunlight ×N" is the inverse-square factor relative to 1 AU (ignores the Sun's angular size for the last minutes).
- "Sun ≈ 70× wider" at T − 1 h is 67.9× (rounded in the narration, "≈70" on screen).
- The landscape is fictional and stylised (silhouettes); late-stage sky colours, haze and steam are artistic.
- 4K files are **lanczos upscales** of the 1080p render, not native 4K.

## Render / CPU notes (4 shared cores, load ~20–30 during this job)
- Blender: 5 stills (land near/far 16 spp, orbit Earth 2880×1620 24 spp, Moon-shot Earth/Moon 24 spp) + the dive
  (510 frames at 3 spp, no denoise/bounces, all frames rendered; 5–33 s/frame on the overloaded CPU, ≈1.6 h wall).
  Frames after impact (505+) are covered by the white-out.
- Orbit and Moon shots are 2.5D (stills panned/zoomed over a separate star layer) — true 3D motion is only in the dive.
- Compositor 0.8–2.5 s/frame (numpy, one core per process, 2–3 processes); landA was re-rendered twice to keep the
  on-screen day counter in sync with the narration.

## Sources
- Universe Today, "What if Earth stopped orbiting the Sun?" (≈65 days): https://www.universetoday.com/articles/earth-stopped-orbiting-sun
- ScienceABC (fall = half of a degenerate Kepler ellipse, T/(4√2) ≈ 64.6 d): https://www.scienceabc.com/nature/universe/happen-earth-stopped-revolving-around-crashing-into-sun-consequences
- NASA NSSDC Sun fact sheet (GM☉, radius, escape velocity ≈ 617.6 km/s): https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html
- Ocean mass ≈ 1.35×10²¹ kg: https://hypertextbook.com/facts/1998/AvijeetDut.shtml
- Granule size ≈ 1,000 km (mean 1,050 km): https://spaceacademy.net.au/env/sol/solgran.htm , https://www.arxiv.org/pdf/1208.4337
- Earth imagery: NASA Blue Marble / Black Marble (public domain), via the `three-globe` npm package example images.
- Constants: IAU 2015 nominal R☉ = 695,700 km, L☉ = 3.828×10²⁶ W; Earth/Sun mass ratio 1/333,000; Venus a = 0.723 AU,
  Mercury a = 0.387 AU; Earth's mean orbital speed 29.78 km/s.
