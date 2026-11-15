# What If Earth Spun Faster? (YouTube Short, batch 4)

The Short is vertical only: 1080×1920 at 30 fps, 43.33 s (measured on the final mp4: −14.3 LUFS, −2.0 dBTP, AAC 192k). It is one locked tripod shot of the user's `01_desert.png`,
made in the BATCH4 swap format. Each spin-up swaps in with a tinted flash and a chromatic shockwave, and the dunes are
relit by the racing day–night cycle. Readouts sit at the top and big orange one-word captions sit on the dunes. There is
no disclaimer small print, the night sky stays deep blue, and a white-out returns to the 24-hour day so the Short loops
(the clock is reset to the opening hour angle).

## Beats
1. **24 h:** a calm morning, with the Sun 10° up and creeping.
2. **12 h:** the Sun shoots up out of the frame, the sky reddens and the first night arrives with **star trails**.
3. **6 h:** day and night every ~5 s, longer trails, and the sand starts to blow.
4. **2 h:** day and night **flicker** (~1.8 s per day) and the Sun streaks up with motion blur. The trails become long
   arcs, and a dense haze of sand races over the dunes.
5. **84 min (the breakup limit):** at the equator, sand grains drift up off the dunes. "Earth would start to fly apart."
6. White-out, then the calm 24-hour morning.

**The sky is real spherical astronomy.** The camera stands on the equator, looking SE (azimuth 135°), in December. The
Sun (declination −23.44°) and ~2,600 stars are placed by hour angle for latitude 0 and projected through the lens
(f = 1,100 px, ~83° vertical field). The Sun's path, its sunrise point (azimuth 113.5°) and the star-trail curvature
(around the south celestial pole, off-frame right on the horizon, so the trails are arcs) are therefore true. The sky colour (day / twilight /
night) follows the Sun's instantaneous elevation. The star trails are a fixed ~2.6 s "exposure", weighted by how dark
the sky was at each instant.

## Narration (63 words)
Voice: Kokoro 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per phrase. Pauses are 0.45–0.5 s between
phrases and 1.1–1.2 s before reveals.
> What if Earth... spun faster? / Today, one day... takes twenty-four hours. / Now... twelve. / The Sun races across the
> sky. / Six hours. / The oceans rush... toward the equator. / Two hours. / Day and night... flicker past. / Winds
> howl... and the equator bulges. / And at just eighty-four minutes... / at the equator... you'd weigh nothing. /
> Earth... would start to fly apart. / Twenty-four hours... / suddenly feels just right.

## Sound (BATCH4 clean rules)
`lib/mix_clean` only, through `lib/b4_kit.make_mix`: `clean_voice` (no pitch, no echo), then `mix` with the soft pad
and the module's gentle whoosh at each swap. Nothing else is added.
**Bed vs mix:** the pad + whoosh bed alone (voice muted) is **23.0 dB** under the full mix (−40.6 vs −17.6 LUFS, before the
shared normaliser).

## Science (`short.py info`)
- **Breakup limit:** the day length at which the centrifugal acceleration at the equator equals gravity:
  T = 2π √(R³/GM), with R = 6,378 km and GM = 3.986 × 10¹⁴ m³/s². That gives **84.5 min = 1.41 h** (verified). At that
  spin the equator moves at orbital speed (~28,500 km/h), so you would weigh nothing there.
- **Equator speed and weight loss** (fraction of g cancelled at the equator, ω²R/g):

  | day | equator speed | weight loss at the equator |
  |---|---|---|
  | 24 h | 1,670 km/h | 0.34 % |
  | 12 h | 3,340 km/h | 1.4 % |
  | 6 h | 6,680 km/h | 5.5 % |
  | 2 h | 20,000 km/h | 49.6 % (shown as −50 %) |
  | 84.5 min | 28,500 km/h | 100 % |
- **Bulge:** today the equatorial radius is 21.4 km larger than the polar radius. For small spins the flattening scales
  with ω², which gives ~85 km at 12 h and **~340 km at 6 h** (readout). At 2 h this linear scaling no longer holds (the
  shape becomes strongly flattened), so the readout there gives only the weight. A real, flattened Earth, with its
  equator pushed outward, would start shedding mass a little *before* 84 min.
- **Oceans to the equator:** the water responds to the stronger centrifugal pull at once, while the solid Earth re-shapes
  only slowly. So with a faster spin the oceans pile up at the equator and drain from high latitudes (narration only: no
  ocean in this shot).
- **Winds:** a faster spin means a stronger Coriolis effect and more violent weather, in line with common "faster Earth"
  analyses. This is shown as wind-blown sand that grows stronger stage by stage.

## Liberties (not captioned, per the user rule)
- Screen time per day is not one constant factor: 240 s (calm opening), 10 s, 5 s, 1.8 s and 1.25 s. This keeps the
  24-hour stage calm and the 84-minute flicker below ~1 Hz.
- The sky is instantaneous, but the star trails are a 2.6 s exposure (the classic long-exposure look). During the calm
  opening, the stars are shown as points.
- Cirrus wisps race and smear across the sky as the spin grows, and the dunes get relief shading that sweeps with the Sun
  (from the photo's own luminance relief). Both are art direction.
- Sand floating up shows the "weightless at the equator" beat. The air would of course also be moving violently.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`, `short.py` (`info`, `stills`, `segs`), `encode.py`, `thumbnail.py`.
- Scratch: `.../scratchpad/series/B4-earth-spins-faster/`. Outputs (`out/`, git-ignored): `earth-spins-faster-short.mp4`,
  `earth-spins-faster.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
