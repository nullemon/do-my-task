# What If the Moon Had Rings? (YouTube Short, BATCH4)

9:16 only, 1080×1920 at 30 fps, about 44 s. One locked tripod shot of `02_snowy_mountain_village.png` at night. The
sky swaps between a normal Moon and a Moon carrying Saturn's ring system. Each swap gets a tinted flash, a chromatic
shockwave and a soft burst of beams, and the village is relit. Readouts sit at the top and the big orange one-word
captions follow the voice. The end goes through a white-out back to our plain Moon, so the Short loops.

## Narration (74 words, Kokoro 0.7 am_michael + 0.3 am_onyx, speed 0.86, one TTS call per phrase)
> What if our Moon... had rings? Tonight, it looks like this. Now... give it Saturn's rings. Rising over the
> mountains... more than twice as wide as the Moon. A silver halo. The rings cast a shadow... a dark stripe across
> its face. Sometimes they turn edge-on... a razor-thin line of light. And on snowy nights... moonlight is five times
> brighter. The whole village glows. Then... they're gone. And our Moon... looks a little lonely.

## Beats (`short.py`)
| beat | readout | look |
|---|---|---|
| normal Moon | OUR MOON · 0.52° WIDE · 384,400 KM AWAY | near-full Moon, starry night, village windows glowing |
| ringed Moon | RINGED MOON · RINGS 1.2° ACROSS · 2.3× ITS WIDTH | rises from behind the ridge; reddened by extinction near the horizon; rings open 26.7° |
| ring shadow | RING SHADOW · SUNLIGHT FROM ABOVE THE RINGS | rings open 6°, Sun about 16° above the ring plane: a curved, soft-edged dark band crosses the lower disc |
| edge-on | EDGE-ON · 1.2° LONG · ONLY METRES THICK | the rings swing shut to a sunlit hairline (0.35°) with a glint; their shadow is a stripe across the face |
| brighter nights | ~5.5× TODAY'S FULL-MOON LIGHT | rings wide open at full Moon; the sky brightens and the snow, rims and glints of the village light up |
| back | OUR MOON | white-out, plain Moon (loop) |

## Lens and rendering
- **Lens:** a long telephoto, f = 21,000 px (the frame is about 2.9° wide). Every beat uses the same lens, so all
  sizes stay true relative to each other. Moon radius = f·tan(asin(1737.4/384,400)) = 95 px. The rings reach
  2.27 R = 216 px (the A-ring edge), and the faint F-ring region goes out to 2.33 R.
- **Rings:** `rings.py` is a copy of `../planets-as-moon/planets.py`. It uses the real 8192 px Saturn ring profile
  (C ring to F ring, calibrated in km) in units of the body radius, so it scales directly from Saturn's radius to the
  Moon's. Its additions:
  - a separate globe frame, so the Moon keeps its familiar near side while the ring plane tilts on its own;
  - `set_sun()`, so the phase can change;
  - ring colour desaturated to icy white-grey;
  - a penumbra-blurred ring profile for the ring shadow on the globe.
  The globe's shadow on the rings and the lit/unlit faces are unchanged from planets.py.
- The Moon and rings sit behind the plate, which is fully opaque where alpha > 0.9.

## Science (`science.py`)
- **Size:** Saturn's A-ring outer edge is 136,775 km / 60,268 km = 2.27 Saturn radii. Scaled to the Moon that is
  3,943 km, which spans 2·atan(3,943/384,400) = **1.18°** (about 1.2°), 2.27× the Moon's 0.518°. Verified.
- **Could it exist?** Yes. The Roche limit for icy material around the Moon is 2.44·R·(3.34/0.92)^⅓ = 3.75 Moon
  radii, so rings ending at 2.27 R lie inside it and could not clump into a moon. The Moon's Hill sphere is about
  35 Moon radii.
- **Moonlight:** ring area projected at a 26.7° opening × ring I/F (B ring ≈ 0.5, A ≈ 0.35, C ≈ 0.1, Cassini
  Division ≈ 0.05), compared with the full Moon's disc-averaged I/F of about 0.12. The rings add about 4.5× the
  Moon's own light, so total moonlight is **about 5.5×** ("five times brighter"). The part of the rings behind the
  Moon and the part of the Moon behind the rings roughly cancel. Icy ring material reflects about 4× more than lunar
  rock (0.5 vs 0.12).

## Liberties
- **Ring tilt:** rings would lie in the Moon's equatorial plane, which is within about 7° of our line of sight, so
  from Earth they would always look nearly edge-on. We borrow Saturn's 26.7° opening, and the tilt changes between
  beats (6° for the shadow beat, a hairline for the edge-on beat). The shadow and edge-on beats compress what would
  take years.
- **Phase:** the lighting changes between beats, which compresses a lunar month.
- **Altitude:** through a 2.9° telephoto the Moon stays only a few degrees above the ridge. The reddening is a mild
  version of the true extinction.
- **Stars:** the stars use a wider-field star plate (not the telephoto scale), as in the other Moon Shorts.

## Sound (BATCH4 clean rules)
- **Mix:** `audio/mix.py` uses only `lib/mix_clean.py`: `clean_voice(dry)` (no pitch shift, echo or reverb), then
  `mix(voice, DUR, swaps=[5 swap times], key="D")`, which adds the soft pad and the gentle whoosh at the swaps.
  Nothing else is added.
- **Bed check:** with the voice muted, the bed is **−25.1 dB** under the full mix (`SCR/audio/bedcheck.txt`).
- **Encode:** AAC 192k (`encode.sh`). Measured on the final mp4: **−14.2 LUFS, −1.9 dBTP**. The video is 44.15 s
  long (1,324 frames).

## Files
`short.py` (picture), `rings.py`, `science.py`, `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`,
`encode.sh`, `thumbnail.py`. Outputs are in `out/`.
