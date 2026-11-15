# The Biggest Explosions in the Universe, Seen From Earth (YouTube Short, BATCH4)

9:16 only, 1080×1920 at 30 fps, about 47 s. One locked tripod shot of `C_city.png` at night. The code comes from
`../star-neighbours` and uses the real southern sky: HYG v4.1 stars at latitude 34° S, LST 13.6 h, with the Milky
Way's core rising in the east over the skyline. Every event appears at one point of the sky, the direction of the
galactic centre, at its real brightness.
- **Swaps:** a tinted flash, a chromatic shockwave and beams.
- **Relighting:** the city is relit by each event's light (rim light, lit roofs, cast shadows, skyglow), and the
  faint stars wash out.
- **Readouts:** EVENT / DISTANCE / BRIGHTNESS at the top, plus big orange one-word captions.
- **Ending:** a white-out back to the night sky, so the Short loops.

## Narration (74 words, Kokoro 0.7 am_michael + 0.3 am_onyx, speed 0.86, one TTS call per phrase)
> Imagine the biggest explosions... in our sky. A supernova, a thousand light years away. A hundred times brighter
> than Venus. Two dead stars collide... forging gold. A gamma-ray burst... billions of light years away. A faint
> spark. A magnetar flare... brighter than the full Moon. In gamma rays. And a quasar. Now... at our galaxy's heart.
> Brighter than the Sun? No... almost a full Moon, in one tiny point. Lucky us... they're far away.

## Events (`science.py`; m = M + 5·log10(d / 10 pc))
| event | distance | brightness | why there |
|---|---|---|---|
| core-collapse supernova (peak M_V ≈ −17, typical Type II-P) | 1,000 ly | **m −9.6**, 97× Venus, 1/18 of the full Moon; visible in daylight | lethal within ~25–50 ly (X-rays to ~160 ly) |
| kilonova (AT2017gfo-like, peak M ≈ −15.8) | 500 ly | **m −9.9**, blue at first, then red as the r-process debris cools; fades in days | lethal within ~36 ly; an on-axis short-GRB jet within ~300 ly (Perkins et al. 2024) |
| GRB 080319B, the "naked-eye burst" (z = 0.937) | 7.5 billion ly (light travel) | **peak V 5.3**, at the naked-eye limit, for ~30 s | real event |
| SGR 1806-20 giant flare (27 Dec 2004) | ~28,000 ly (8.7 kpc; older estimates 50,000 ly) | 0.2 s spike with fluence ~1 erg/cm², about 5 mW/m², **≈1.5× the full Moon's total irradiance, all in gamma rays**; invisible to the eye | real event |
| quasar 3C 273 (V 12.9, M_V ≈ −26.7) | 2.4 billion ly | m 12.9: telescope only | real |
| 3C 273 moved to the galactic centre | 26,000 ly | **m −12.2 ≈ 0.63× the full Moon**, from one point; the Sun is still ~660,000× brighter | the brief's "brighter than the Sun?": no |

## Liberties
- All events appear at the galactic centre's position in the sky, so one city-shadow solve serves the whole Short.
- Light curves are compressed into a few seconds each: the supernova cools, the kilonova reddens and fades, the GRB
  flickers.
- **Magnetar:** gamma rays are invisible, so the flash and relight are shown as a capped ~0.35 s pulse in false-colour
  violet. The readout says
  "INVISIBLE TO THE EYE".
- **Quasar at the core:** ~30 magnitudes of dust extinction toward the real galactic centre would hide it completely.
  The comparison ignores the dust, like any "if it were here" thought experiment.
- **Display mapping:** the city's relight brightness is a display mapping of log flux, not linear.

## Sound (BATCH4 clean rules)
- **Mix:** `audio/mix.py` uses only `lib/mix_clean.py`: `clean_voice(dry)` (no echo, reverb or pitch shift), then
  `mix(voice, DUR, swaps=[7 swap times], key="D")` with the soft pad and the gentle whoosh. Nothing else is added.
- **Bed check:** with the voice muted, the bed is **−24.3 dB** under the full mix (`SCR/audio/bedcheck.txt`).
- **Encode:** AAC 192k (`encode.sh`). Measured on the final mp4: **−14.2 LUFS, −2.0 dBTP**. The video is 47.38 s
  long (1,421 frames).

## Files
`short.py`, `science.py`, `skygeo.py` and `mwsky.py` (copied from star-neighbours), `catalog.py` (HYG → SCR/stars.npz),
`audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`, `encode.sh`, `thumbnail.py`.
