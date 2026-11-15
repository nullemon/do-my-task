# What If Earth Moved Farther from the Sun? (YouTube Short, batch 3)

The cut is vertical only: 1080×1920 at 30 fps, about 47 s long. It is one locked shot of the user's
`02_snowy_mountain_village.png`, upscaled from 941×1672 with its transparent sky filled by the render, in the swap
format from `../BATCH3.md`. Earth is moved away from the Sun in steps. Each step brings a flash, a chromatic shockwave,
beams and a relight. A bold readout sits in the upper sky, so the chalets stay clear, with big orange one-word captions.
There is no disclaimer small print. A white-out at the end returns to the warm village, so the Short loops.

## Narration (REDO v3 storytelling voice, 72 words)
Kokoro voice style 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, with one TTS call per phrase. There are 0.4–0.5 s
pauses between phrases and 1.1–1.15 s before each reveal. The v3 post chain is applied in `lib/v3_kit.build_voice`, a
17 kHz low-pass before AAC, and the loudness target is −14 LUFS / −1 dBTP, measured on the final mp4.
> Imagine Earth... drifting away from the Sun. First... Mars's orbit. Less than half the sunlight. Winter... never ends.
> Now... Jupiter's orbit. The Sun shrinks... to a tiny disc. Noon... as dim as a stormy day. Saturn's orbit. Ninety
> times dimmer. Then... Neptune. The Sun... is just a brilliant star. And the air itself... freezes into snow.
> Finally... the Oort cloud. Our Sun... just a bright star among many. Come home... little Earth.

## Beats (`short.py`)
The lens has f = 1500 px, a 65° vertical field of view, and the Sun is drawn at its true angular size.

| step | d (au) | width | sunlight | on screen | look |
|---|---|---|---|---|---|
| today | 1 | 0.53° | 100% | 7 px disc + glare | low afternoon sun, blue sky with a warm horizon, rainbow beams; the chalet windows are lit |
| Mars's orbit | 1.524 | 0.35° | 43% | 4.6 px crisp disc inside a dashed ring of today's size | cooler, paler sky; frost starts creeping |
| Jupiter's orbit | 5.20 | 0.10° (6′) | 1/27 | 1.3 px tiny disc | grey-blue "stormy day" light; ice spreads; the windows stand out |
| Saturn's orbit | 9.54 | 0.056° | 1/91 | sub-pixel point + spikes | deep twilight blue; the first stars appear |
| Neptune's orbit | 30.1 | 0.018° (64″) | 1/904 | brilliant star with spikes | navy sky full of stars; the frozen air falls as snow; ice ferns grow in from the frame edges |
| Oort cloud | ~2,000 | ~1″ | 1/4,000,000 | a bright star among the Milky Way | deepest navy (never black); everything iced, only the windows glow |

The chalet windows and porch lamps are cut from the plate as a warm-light mask. They keep a constant warm emission (plus
a soft spill on the snow) while everything else dims, so they read as islands of warmth.

## Science (checked)
- **Width:** θ = 2·asin(R☉/d): 0.350° at 1.524 au, 0.102° at 5.20 au, 0.056° at 9.54 au, 64″ at 30.1 au and about
  1″ at 2,000 au. Light scales as 1/d²: 43%, 1/27.1, 1/91, 1/904 and 1/4,000,000.
- **Mars's orbit, endless winter:** the equilibrium temperature is about 207 K (−66 °C) for albedo 0.3, versus 255 K
  today, which means a snowball Earth.
- **Jupiter's orbit, "as dim as a stormy day":** this is a CORRECTION to the brief's "like dusk at noon". Direct sun
  plus sky is about 120,000 lux, and 1/27 of that is about 4,400 lux. That is overcast or stormy-day light, far brighter
  than dusk (sunset is about 400 lux). Dusk-level light (about 130 lux) arrives only at Neptune's distance. The Sun's
  disc is 6 arcminutes wide, so a tiny disc is still resolvable by the eye.
- **Neptune's orbit:** the Sun is 64″ across, about the eye's resolution limit, so it looks like a brilliant star. The
  Sun/full Moon ratio is 10^((26.74 − 12.74)/2.5) ≈ 400,000 (≈ 450,000 for a −12.6 Moon), and dividing by 904 gives
  440–500×. The readout says "~450×" rather than the brief's "500×". The equilibrium temperature is about 47 K, below
  the freezing points of nitrogen (63 K) and oxygen (54 K). Nitrogen at 1 bar already condenses below 77 K, which
  happens beyond about 11 au. So the atmosphere freezes out as snow.
- **Oort cloud (~2,000 au, its inner edge):** the Sun's apparent magnitude is −26.74 + 5·log₁₀(2000) ≈ −10.2. That
  is still about 3,000× brighter than Sirius, but it is a point. The narration says "a bright star among many", and the
  readout adds "STILL THE BRIGHTEST STAR" so it stays honest.

## Liberties (not captioned, per the user rule)
- The windows stay lit and warm throughout. In reality nobody could live there for long.
- The sky is never pitch black (user rule). Beyond the point where the air freezes out, the real sky would be black
  even at noon. The stylized navy also stands for eye adaptation. Exposure is compressed throughout: 1/900 of the
  light is not shown as 900× darker.
- The changes are instant. Freezing and the atmosphere's collapse would really take a long time.
- The photo itself is a blue-hour plate, relit to a warm low afternoon sun for "today".
- The beams, spikes, shockwaves, edge ice ferns and the dashed comparison ring are graphic devices.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py`, `short.py` (`info`, stills, `seg`),
  `encode.sh`, `thumbnail.py`.
- Scratch: `.../scratchpad/series/B3-sun-farther/`.
- Outputs (`out/`, git-ignored): `sun-farther-short.mp4`, `sun-farther.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
