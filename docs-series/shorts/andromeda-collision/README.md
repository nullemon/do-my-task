# The Night Andromeda Hits Us (YouTube Short, 9:16 only)

1080×1920 at 30 fps, about 42.6 s. BATCH3 swap format: one **locked** shot of the user's `08_suburban_backyard.png` at
night, with the string lights and the house window glowing. The sky is a time-lapse over billions of years. Each beat
swaps in with a tinted flash, a chromatic shockwave that reveals the new sky inside its ring, coloured light beams, a
relit yard and a readout. A big glowing **YEAR counter** ("2026" → "+2.10 BILLION" …) keeps running. A white-out returns
to today's sky so the Short loops. There is no disclaimer small print (user rule).

## Narration (REDO v3 style: 73 words, ~41 s of speech)
Voice: Kokoro 0.7 am_michael + 0.3 am_onyx at 0.86, one TTS call per phrase, real word timings, v3 post chain
(`../lib/v3_kit.py`); 0.45 s between phrases and 1.15 s before each reveal; a 17 kHz low-pass before AAC.
> See that faint smudge? / That's Andromeda... six full Moons wide. / And it's heading our way. / Two billion years from
> now... / it's ten full Moons wide. / Then... it looms across the sky. / And the galaxies may collide. / Gas crashes
> together... new stars ignite everywhere. / But the stars themselves... almost never hit. / Finally... one giant galaxy.
> Milkomeda. / By then... our Sun will be dying. / Will it really happen? / New studies say... it's a coin flip.

## Timeline and numbers (verified)
- **Today:** M31 is 2.5 Mly away (~765–785 kpc) and its visible disc (D25) is 3.17° × 1.0°, i.e. ~6 full Moons. It
  approaches at ~110 km/s relative to the Milky Way (~300 km/s heliocentric). Six real-size full Moons (0.52°) are laid
  along its major axis on "six full Moons".
- **Distances over time:** a radial two-body infall (770 kpc, −110 km/s, 2×10¹² M☉) gives ~500 kpc at +2 Gyr. After
  +3 Gyr the curve follows van der Marel et al. (2012, ApJ 753, 9): first pericentre ~31 kpc at ~3.9 Gyr; the merger
  completes ~6 Gyr and the remnant is a giant elliptical. NASA/STScI's 2012 illustrated sequence uses the same beats
  (2 Gyr, 3.75 Gyr "fills the field of view", 3.85–4 Gyr starburst and tidal distortion, 7 Gyr elliptical).
  | beat | distance | bright disc | readout |
  |---|---|---|---|
  | +2 Gyr | ~500 kpc ≈ 1.6 Mly | 5.0° ≈ 10 full Moons (1.6× today) | "~1.6 MILLION LY AWAY / ~10 FULL MOONS WIDE" |
  | +3.75 Gyr | ~85 kpc ≈ 280,000 ly | 28.6° ≈ 55 full Moons (+ outer disc and halo far beyond) | "~280,000 LY / ~55 FULL MOONS" |
  | ~+4 Gyr | first close pass, ~31 kpc | ~70° | "STARBURST / STAR-ON-STAR HITS: ALMOST NONE" |
  | ~+7 Gyr | Milkomeda | the whole sky | "ONE GIANT ELLIPTICAL GALAXY" |
- **Correction to the brief:** the brief asked for Andromeda to cover "a big part of the sky" at ~2 Gyr. Physically it is
  then still ~500 kpc away and only ~5° wide, so the narration and readout say "ten full Moons wide".
- **Hedging (2025):** Sawala et al. (2025, *Nature Astronomy*), including the LMC, M33 and Gaia/HST proper-motion
  uncertainties, find only a ~50 % chance of a Milky Way–Andromeda merger within the next 10 Gyr, and ~2 % within 5 Gyr.
  So the narration says "may collide" and ends on "a coin flip". The +4 Gyr readout says "IF IT HAPPENS AT ALL", the
  Milkomeda readout says "IF THE MERGER HAPPENS", and the end readout gives "~50 % chance… in the next 10 billion years".
- **Stars almost never collide:** stars are separated by millions of times their own diameters, so essentially no
  stellar collisions occur. Gas clouds do collide, which triggers the starburst.
- **The Sun:** it leaves the main sequence in ~5 Gyr and becomes a red giant over the following ~2–3 Gyr, so "by then
  (~7 Gyr) our Sun will be dying" holds. Earth is likely uninhabitable much earlier (~1 Gyr), as the Sun brightens; the
  video does not address that.

## How it's made
- Sky: real HYG v4.1 stars (V < 6.5) at 40° N and the Milky Way band (star-dates `catalog.py`, `skygeo.py`, `mwsky.py`).
  The lens is stereographic, f = 1100 px (19.2 px per degree), centred on M31 at alt 40°, az 62° (LST 20.45 h).
- Andromeda: the galaxies-visible recipe in `prep.py`. NASA GALEX PIA15416 is registered with an exact 3-point affine
  (nucleus, M32, M110 → real RA/Dec) at 500 px/deg, then drawn at its true angular size for each distance and in its
  real sky orientation, with a mip pyramid.
- +3.75 Gyr: a camera-stretch lift so the D25 disc reads at its true size, plus an extended outer disc and halo, two
  tidal tails and a slight twist.
- First pass: the disc is drawn ~25× its present size with a strong tidal swirl, plus a mirrored, counter-swirling
  second disc standing in for the Milky Way's torn arms, a warped Milky Way band, and a starburst (the galaxy-address
  nursery plate: pink H II regions, plus 900 blue young stars).
- Milkomeda: a Sérsic n = 2 envelope (r_e ≈ 900 px) with a soft warm core, fading remnant dust, and 2,600 old
  golden stars.

## Liberties (deliberately not captioned)
- **Brightness:** Andromeda is shown at long-exposure-camera brightness from +2 Gyr on. Its surface brightness does not
  rise as it approaches; to the eye it would stay a faint glow until the merger lights up the sky. Today's view is kept
  as a faint smudge.
- **Sky orientation:** the time-lapse keeps the same backyard sky. Over billions of years the Sun's orbit would carry us
  elsewhere in the galaxy, and the constellations would change completely.
- **First pass and Milkomeda:** these are artistic renderings, not an N-body simulation. The second (Milky Way) disc is
  a mirrored copy of the GALEX image.
- **Distances:** the distance table is a simple model matched to the published orbit (see above).
- **Flashes, shockwaves, beams and the yard relighting are VFX.**

## Sources and licences (nothing committed; the files are in scratch only)
- Andromeda: NASA/JPL-Caltech GALEX, images.nasa.gov **PIA15416** (via GitHub unit511/space-wallpapers 4K). NASA, no
  copyright claimed.
- Star positions: HYG v4.1 (astronexus/HYG-Database). CC BY-SA 4.0.

**Credit line for the description:**
> Andromeda image: NASA/JPL-Caltech (GALEX). Star positions: HYG Database (CC BY-SA 4.0). Future skies: digital
> renderings based on van der Marel et al. 2012 and Sawala et al. 2025.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT); `catalog.py`, `skygeo.py`, `mwsky.py`;
  `prep.py` (M31 sprite); `short.py` (`info`, `stills`, `seg`); `encode.sh`; `thumbnail.py`.
- Scratch: `scratchpad/series/B3-andromeda-collision/`. The nursery plate is read from `B3-galaxy-address/plates.npz`.
- Outputs (git-ignored): `out/andromeda-collision-short.mp4`, `out/andromeda-collision.srt`, `out/thumb-vertical.jpg`,
  `out/thumb.jpg`.
