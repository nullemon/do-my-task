# What If Our Moon Was as Big as Other Moons Are to Their Planets? (YouTube Short, 9:16 only)

The video is 1080×1920 at 30 fps and 48.71 s long (REDO v3 voice, 14 Nov). It uses the BATCH2 "swap" format, like `other-moons/` and
`moon-closer/`: one locked tripod shot of the user's `A_park.png` (transparent sky), from dusk into night. Our Moon is
re-sized so that its diameter has the same ratio to Earth's that a famous moon has to its own planet. It stays at its
real distance (384,400 km), is drawn at its true angular size, and wears that moon's map.

Every swap has a flash, a chromatic shockwave and coloured moonlight beams, and the park is relit by the new moonlight,
which is proportional to the disc's area. A tiny Moon gives a dark night: the lamps come up and the stars come out. The
tiny discs get three aids: a glowing pointer ring with a sonar ping, a dashed "TODAY'S MOON" ghost outline at the true
size of today's Moon, and a rainbow-rimmed zoom loupe ("ZOOM ×72" and so on). The payoff is the Charon-ratio Moon,
1.9× today's: it rises over the park behind the tree and the conifer, with today's Moon shown as a ghost inside it. On
"ours", a white-out returns to today's Moon at dusk, so the Short loops.

Each moon has a readout: RATIO OF X TO PLANET / ratio / OUR MOON WOULD BE N KM / ×TODAY'S SIZE · angle. Big orange
one-word captions are synced to the voice. There are no disclaimer captions.

## Narration (REDO v3, 14 Nov: storytelling style, 73 words, 9:16 only, 48.71 s)
Kokoro voice style 0.7 × am_michael + 0.3 × am_onyx (blended vectors) @ 0.86, one TTS call per phrase, 0.4–0.5 s between
phrases and 1.0–1.2 s at each beat change. Voice post chain (pitch-only, timings stay valid): rubberband pitch 0.944 with
formants preserved, HPF 60 Hz, EQ, gentle compressor, short echo (`lib/v3_redo_q5.py`). The beats, swaps, readouts and
captions are re-timed to the new word timings. −14 LUFS / −1 dBTP. Scratch: `.../scratchpad/series/V3-<name>/`.
Render: `short.py segs` (restart-safe segments) → `audio/mix.py` → `encode.sh vert`.

> Imagine our Moon...  
> sized like other moons... to their planets.  
> Today, it's over a quarter of Earth's width.  
> First... Phobos.  
> Forty-two kilometers.  
> Barely visible.  
> Ganymede...  
> a tiny dot.  
> Titan...  
> a little orange spark.  
> Triton...  
> still five times smaller.  
> And then... Sharon.  
> Half as wide as Pluto.  
> Our Moon... nearly twice as big.  
> A double world.  
> But Pluto's a dwarf planet...  
> Of all the real planets...  
> ours has the biggest moon for its size.

## Numbers (`short.py info`)
Mean radii come from the NASA/JPL fact sheets, and every ratio uses mean diameters on both sides.
- New radius = ratio × 6,371 km.
- θ = 2·asin(R/384,400 km).
- Lens: f = 24,000 px (4.6° vertical field of view).

| ratio | moon / planet D (km) | ratio | our Moon would be | × today | angle | radius on screen |
|---|---|---|---|---|---|---|
| Moon / Earth | 3,474.8 / 12,742 | 0.2727 | 3,475 km | 1 | 0.518° | 108.5 px |
| Phobos / Mars | 22.16 / 6,779 | 0.00327 | 41.7 km | 0.012 | 0.0062° | 1.3 px |
| Ganymede / Jupiter | 5,268 / 139,822 | 0.0377 | 480 km | 0.138 | 0.072° | 15.0 px |
| Titan / Saturn | 5,149 / 116,464 | 0.0442 | 563 km | 0.162 | 0.084° | 17.6 px |
| Triton / Neptune | 2,707 / 49,244 | 0.0550 | 700 km | 0.202 | 0.104° | 21.9 px |
| Charon / Pluto | 1,212 / 2,376.6 | 0.510 | 6,498 km | 1.87 | 0.969° | 202.9 px |

Checks against the brief:
- **Phobos:** the brief's 41 km uses Phobos = 22 km. The mean diameter is 22.16 km (27×22×18 km body), which gives
  41.7 km, so the narration and the readout say 42 km.
- **Triton:** the brief's 49,528 km for Neptune is the equatorial diameter. With the mean (49,244 km) the result is
  700 km. With the equatorial diameter it is 696 km. Either way it is about 700 km and 0.10°.
- **"Five times smaller":** 1/0.202 = 4.96.
- **"Nearly twice":** 1.87×.
- **"Ours has the biggest moon for its size":** among the eight planets the next best is Triton/Neptune at 0.055. Charon
  wins overall only because Pluto is a dwarf planet. Mercury and Venus have no moons. Mars/Phobos is 0.0033.
- **Moonlight:** this is ∝ the disc's area (the same surface brightness): Phobos ratio 1/7,000, Ganymede 1/53, Titan
  1/38, Triton 1/25, Charon 3.5×. The park relight is compressed (gain ∝ area^0.3).

## Liberties (recorded here, not captioned)
- Each re-sized Moon wears the map of the moon it imitates. This is a visual cue, not physics: it is still "our Moon",
  and its brightness is computed from our Moon's area. Titan is drawn as its orange haze ball.
- The telephoto framing makes the discs readable. Relative sizes are exact.
- The loupe magnification is stated on screen (×72 for Phobos, ×6, ×5, ×4).
- The swap animations, beams, coronas, shockwaves and the ~2.6 s Charon moonrise are artistic and time-compressed.
- **Charon map:** the south was in polar night during the 2015 flyby and is black in the map. It is filled with the
  north mirrored across the equator, shifted 180° and greyed, so there is no second red cap. The colour is the map's
  enhanced colour, slightly desaturated.
- **Phobos:** the map is wrapped on a sphere (the real Phobos is lumpy).

## Sources
- **Moon:** Solar System Scope `8k_moon` (CC BY 4.0, NASA LRO data), `shorts-common/dl/sss/`.
- **Ganymede, Titan, Triton:** USGS/NASA global mosaics (public domain) in `shorts-common/dl/moons/`, prepped as in
  `other-moons/`.
- **Phobos:** `shorts-common/dl/moons/phobos-2048.jpg` turned out to be a 404 text stub. A 4096×2048 equirectangular
  Phobos map was fetched instead from the GitHub LFS of `jackbelmore/spayly` (`public/textures/phobos.jpg`). It looks
  like the USGS Viking/MEX Phobos mosaic, but its provenance is not documented there. It is saved to
  `scratchpad/series/B2-moon-ratios/dl/phobos/`.
- **Charon:** the New Horizons enhanced-colour global map (NASA/JHUAPL/SwRI, public domain), 6000×3000, from the same
  repo's LFS (`public/textures/charon.jpg`). It is saved to `.../B2-moon-ratios/dl/charon/`.
- **Foreground:** the user's `A_park.png`.

## Files
- **Code:** `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `moons.py` (copied from
  `../other-moons/moons.py`), `short.py` (`info`, stills and `patch` modes), `encode.sh` (mux without `-shortest`),
  `thumbnail.py`.
- **Scratch:** `.../scratchpad/series/V3-moon-ratios/` (maps copied from `B2-moon-ratios/dl/`).
- **Outputs** (`out/`, git-ignored): `moon-ratios-short.mp4`, `moon-ratios.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
