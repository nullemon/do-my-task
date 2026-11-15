# What If Earth Stopped Spinning? (YouTube Short, batch 4)

Vertical only: 1080×1920, 30 fps, 44.1 s. One locked tripod shot of the user's `06_farm_field_barn.png` (wheat, a red
barn, a silo, an oak) in the swap format. Every swap has a tinted flash and a chromatic shockwave, and the farm is relit.
Readouts sit at the top and big orange one-word captions at y = 1390.

1. **A normal day.** Blue sky, the Sun at its true 0.53° (f = 1300 px), soft rainbow beams.
2. **A sudden stop.** The atmosphere keeps moving. The sky turns to ochre dust, and streaming dust sheets and debris
   cross the frame. The wheat is bent, flattened and streaked by the wind, the oak sways, and the tripod is buffeted a
   couple of pixels.
3. **A slow stop.** The Sun sweeps up its arc as ghosted time-lapse copies, stalls and freezes. A day counter runs
   from DAY 1 to DAY 180 ("SUN STILL HERE"). The light turns hot and hazy, the wheat bakes brown and droops, and a heat
   shimmer rises over the field.
4. **The long night.** Six months of stars, green and red aurora curtains, and creeping frost (`Foreground.frost`).
5. **The oceans move.** A globe in the sky (NASA Blue Marble, from three-globe) with a soft atmosphere rim. The ocean
   floor drains from the equator, and the water pools into two polar oceans, leaving one equatorial belt of land.
6. A white-out returns to the normal day, and the end loops to the opening.

## Narration (75 words)
Kokoro, style 0.7 × am_michael + 0.3 × am_onyx, speed 0.86, one TTS call per phrase (`lib/v3_kit.generate`). Pauses
are 0.45 s between phrases and 1.05–1.15 s before reveals.

> What if Earth... / stopped spinning? / Right now, this farm is racing east... / and you feel nothing. / Stop it
> suddenly... / and the air keeps going. / Winds of over sixteen hundred kilometres an hour. / Everything... flattened. /
> Stop it slowly... / and the Sun freezes in the sky. / One day... lasts six months. / Then... the long night. / Six
> months of stars... and frost. / Even the oceans move... / draining toward the poles. / So tonight... / be glad the
> ground keeps spinning.

## Sound (BATCH4 clean rules)
`audio/mix.py` builds the voice with `lib.mix_clean.clean_voice` (no pitch shift, echo or reverb). It then calls
`lib.mix_clean.mix` (the soft pad, ducked under speech, plus its gentle whoosh at each swap, −26 dB re the voice peak).
Nothing else is added: no wind sound, despite the storm on screen.

Levels are measured on the stems mix() builds, before its final loudnorm, and saved to `SCR/audio/levels.json`:
- the bed (pad + whoosh, voice muted) is −41.8 LUFS against −17.4 LUFS for the full mix, so it sits **24.6 dB below**;
- the final mp4 measures −14.4 LUFS integrated with a −2.0 dBTP true peak (AAC 192k).

## Science
- **Rotation speed:** Earth's equator moves at 465 m/s = 1,674 km/h, so "over sixteen hundred". A farm at 40° N moves
  at 1,674 × cos 40° ≈ 1,280 km/h. On a sudden stop the air keeps that speed relative to the ground.
- **Tornado comparison:** the fastest measured tornado wind is ~486 km/h (Bridge Creek–Moore, 3 May 1999, Doppler on
  Wheels), and 1,670 / 486 ≈ 3.4, hence "3×".
- **Slow stop:** with no rotation relative to the stars, the solar day equals the year. Each place gets ~6 months of
  day and ~6 months of night. Earth's orbital motion moves the Sun eastward among the stars, about 1° per day, so it
  would rise in the west and set in the east.
- **Oceans:** today's spin gives an equatorial bulge of 21 km (6,378 vs 6,357 km). Without the centrifugal effect the
  sea level would follow a sphere-like geoid, while the rock bulge relaxes far more slowly. The water drains toward
  the poles, leaving two polar oceans and one equatorial supercontinent (W. Fraczek, ESRI, 2010). The globe's boundary
  at ~38° latitude (with a wobbly edge) is a simplification of that model.
- **The long night:** six months without sunlight freezes the night side. No temperature is claimed.

## Liberties (not captioned)
- Time is compressed: the stop, the 6-month day and night, and the ocean migration (which takes far longer) run in
  seconds.
- The day counter is illustrative of the six-month day.
- The wind does not destroy the farm; the barn and silo stay rigid so the shot stays readable.
- Aurora at a mid-latitude farm is a liberty. Earth's field would not vanish at once if it stopped spinning.
- The globe in the sky is an illustration device.
- Beams, flashes and shockwaves are artistic.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`.
- `short.py` (`info`, `vert t,...`, `segs`), `thumbnail.py`, `encode.sh`.
- Shared FX: `../lib/swapfx_b4.py` (a new module; nothing else in `lib/` is edited).
- Scratch: `.../scratchpad/series/B4-earth-stops-spinning/`.
- Outputs (`out/`, git-ignored): `earth-stops-spinning-short.mp4`, `earth-stops-spinning.srt`, `thumb-vertical.jpg`,
  `thumb.jpg`.

Sources: Blue Marble map (NASA, via the three-globe package), Solar System Scope textures (CC BY 4.0), and the user's farm
plate.
