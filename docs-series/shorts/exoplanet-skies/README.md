# The Skies of Earth-Like Exoplanets (YouTube Short, batch 3)

This Short is 9:16 only: 1080×1920 at 30 fps, 46.35 s long. It uses the swap format: one locked tripod shot of the user's
`06_farm_field_barn.png` (941×1672 RGBA, transparent sky, upscaled to 1080×1920). The premise is "if this farm were on…".
The Sun is swapped for each planet's star, with a flash, a chromatic shockwave and coloured beams. The wheat, barn, silo
and oak are relit in that star's colour and eye-adapted brightness. Each world gets a readout: PLANET / STAR TYPE /
LIGHT YEARS / one fact. Captions are big orange words, one at a time. There is no disclaimer small print. A white-out
returns to Earth at the end, so the Short loops.

## Narration (REDO v3 storytelling voice, 75 words)
The voice and audio settings match REDO v3: Kokoro 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per
phrase. Pauses are 0.40–0.45 s between phrases and 1.05–1.15 s before each reveal. The v3 post chain is followed by a
17 kHz low-pass before AAC, and the loudness is −14 LUFS, −1 dBTP, measured on the final mp4.

> Imagine this farm... / on another world. / Proxima b. / A red sun, three times wider... / and it flares. /
> TRAPPIST-1e. / A salmon-pink sun... / and neighbour worlds in the daytime sky. / Kepler-16b... / two suns. /
> Kepler-186f. / Noon feels like golden hour... / so plants might grow dark... to soak it up. / Kepler-452b... /
> Earth's older cousin. / A slightly bigger, brighter Sun. / It feels like home... / but it's 1,800 light-years away.

## True sizes
One lens is used throughout: f = 5000 px, about a 22° vertical field of view. Each star's apparent size is
R★/a relative to our Sun seen from 1 au (`short.py info`).

| world | star (type, R★, Teff) | orbit a | star size vs our Sun | distance |
|---|---|---|---|---|
| Earth | Sun, G2V, 1 R☉, 5,772 K | 1 au | 1× (0.53°) | 8 light-minutes |
| Proxima b | M5.5V, 0.154 R☉, 3,042 K | 0.0486 au | 3.2× (1.7°) | 4.24 ly |
| TRAPPIST-1e | M8V, 0.119 R☉, 2,566 K | 0.0293 au | 4.1× (2.2°) | 40.7 ly |
| Kepler-16b | K (0.65 R☉, 4,450 K) + M (0.23 R☉, 3,311 K) | 0.705 au | 0.92× and 0.32× | ~245 ly (Gaia) |
| Kepler-186f | M1V, 0.52 R☉, ~3,760 K | 0.432 au | 1.2× | ~580 ly (Gaia) |
| Kepler-452b | G2V, 1.11 R☉, 5,757 K | 1.046 au | 1.06× | ~1,800 ly (Gaia DR2; the 2015 paper said 1,400) |

### Science checks and corrections to the brief
- **Proxima b:** the star is 3.2× the Sun's apparent width, which matches the brief's "about 3×". The planet gets about
  65 % of Earth's total insolation, but only about 2 % of our visible light, because a red dwarf emits mostly infrared.
  That makes a dim red day. Proxima is a flare star: in the May 2019 flare it brightened about 14,000× in the far-UV
  (MacGregor et al. 2021). The flares here are shown as visible flashes; that is a stylisation.
- **TRAPPIST-1e:** the star is 4.1× the Sun's width, matching the brief's "about 4×". Its light is salmon-coloured
  (2,566 K). The sister planets were checked with the Agol et al. 2021 radii and orbits. At closest approach, d and f
  appear about 0.53–0.55°, which is the size of our Moon (0.52°), not clearly bigger. So the readout says "NEIGHBOURS
  ~MOON-SIZED" and the narration makes no size claim. c is about 0.4° and g about 0.3°. They are drawn at about
  closest-approach size, lit with phases from the star.
- **Kepler-16b:** it is a cold, Saturn-mass gas giant, not an Earth-like planet. The readout says so ("A COLD GAS GIANT ·
  THE REAL TATOOINE"). The beat is kept short because there is already a Second Sun Short.
- **Kepler-186f:** NASA notes that its noon would look about as bright as an hour before sunset on Earth: visible light
  is about 11 % of ours, and total insolation about 30 %. Plants under red dwarfs might evolve dark pigments to absorb
  more of the available light (Kiang et al. 2007). The narration hedges this with "might".
- **Kepler-452b:** the star is 1.06× the Sun's apparent size, gives about 10 % more energy, and is about 6 billion
  years old, 1.5 billion years older than the Sun. The planet's confirmation was later questioned (Mullally et al.
  2018); that caveat lives here, not on screen.

## Liberties (deliberately not captioned, per the user)
- One locked telephoto lens (true relative sizes). Beams, flashes, shockwaves, spikes and starspots are artistic.
- Brightness is eye-adapted. A dim star gives a darker, tinted scene, but it is compressed so the farm stays readable.
- Sky colours under each star are plausible renderings, not radiative-transfer results.
- Kepler-16B is placed at a mid-orbit separation from its companion. A double-shadow pass exists in `short.py`
  (`SHADOWS = False`); it was dropped because it read as a blob on the wheat.
- Kepler-452b is graded as a warm, hazy, golden "older Earth" afternoon, so it is distinct from the Earth opening.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `short.py` (picture; `info`, stills,
  `segs`), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/B3-exoplanet-skies/`.
- Outputs (git-ignored): `out/exoplanet-skies-short.mp4`, `out/exoplanet-skies.srt`, `out/thumb-vertical.jpg`, `out/thumb.jpg`.
