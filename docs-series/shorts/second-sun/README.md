# What If Earth Had a Second Sun? (YouTube Short)

The cut is vertical only: 1080×1920 at 30 fps, 39.88 s long. It is one locked tripod shot of the user's `A2_park.png`
(transparent sky) in the "swap" format of `../other-suns`. Our lone Sun is replaced by one real binary-star system
after another. Every swap has a flash, a chromatic shockwave and coloured beams, and each system gets its own sky and
grade. The park is relit by every star separately, so there are coloured double shadows. Each system gets a bold
readout (SYSTEM / STAR A + STAR B / one fact) and one big orange word at a time at ~46 % height. A white-out returns
to the opening Sun, so the Short loops. There are no disclaimer captions (user rule).

## Narration (re-voiced 13 Nov: Kokoro am_michael @ 0.92, ~0.35 s between sentences, ~0.65 s at beat changes)
77 words as written (82 spoken, counting "Kepler sixteen B", "two point eight seven", "Double-U"):
> What if Earth had a second Sun? Alpha Centauri: its orange partner outshines hundreds of full Moons. Some nights
> never get dark. Sirius: a blue-white blaze, and a white dwarf. A Sun's mass, the size of Earth. Kepler-16b, a real
> planet with two suns. Double sunset. Double shadows. Algol, the Demon Star. Every 2.87 days, one star eclipses the
> other. W Ursae Majoris. Two stars, touching. Nearly half of Sun-like stars have a partner. Ours is single.

The first cut (1.05, 95 words) was rejected as rushed. Each sentence is now its own voice line, so the pauses are
exact. The visuals are re-timed to the new word times; the picture is unchanged.

## The framing (one rule for every system)
We stand on a planet where a planet could really orbit. Each disc is drawn at its true angular size through the
plate's own lens (f = 1148 px, the ground-plane fit of `../betelgeuse-tonight`).
- **Earth-equivalent orbit:** the planet gets the same total starlight Earth gets from the Sun, at d = √(L/L☉) au. This
  is used for Alpha Centauri A (1.23 au), Sirius A (5.04 au), Algol (14.1 au, circling the whole triple) and W UMa
  (1.54 au). Daylight is therefore "normal" brightness; only its colour and the companion change.
- **Kepler-16:** we use the real circumbinary planet's orbit, Kepler-16b at 0.705 au, which gets 31 % of Earth's
  sunlight. The real planet is a cold Saturn-mass gas giant; we imagine standing on a rocky world there. A habitable-zone
  orbit (~0.39 au) would be inside the binary's stability limit, so it is not used.

| system | stars (R, T) | as seen from the planet | on screen |
|---|---|---|---|
| Sun | 1 R☉, 5,772 K | 0.53° | r = 5.3 px |
| α Cen | A 1.22 R☉ 5,790 K; B 0.86 R☉ 5,260 K | A 0.53°; B a point, mag −18.1 to −20.6 | A 5.3 px; B point |
| Sirius | A 1.71 R☉ 9,940 K; B 0.0084 R☉ (5,840 km) 25,000 K | A 0.18°; B a point, mag −12.7 to −15.7 | A 1.8 px; B point (+ loupe) |
| Kepler-16 | A 0.649 R☉ 4,450 K; B 0.226 R☉ ~3,300 K | A 0.49°, B 0.17°, up to 17.7° apart | 4.9 / 1.7 px, ~9° apart |
| Algol | A 2.73 R☉ 12,550 K; B 3.48 R☉ ~4,500 K; a = 0.0618 au | 0.10° and 0.13° discs, 0.25° apart | ~1 px each (+ loupe ×35) |
| W UMa | 1.08 + 0.78 R☉, ~6,200 K, a = 2.44 R☉ (touching) | 0.75° long "peanut" | 15 px (+ loupe ×16) |

## Beats (`short.py`)
| t (s) | beat | look |
|---|---|---|
| 0–2.7 | our Sun | blue sky, rainbow beams, single conifer shadow |
| 2.7–10.7 | α Cen | golden afternoon. A is Sun-like, B is a vivid orange point, and there are two conifer shadows in a V. On "Some nights" A sets: an orange-tinted night with stars and lamps, lit and shadowed by B alone |
| 10.7–16.8 | Sirius | deep-cyan sky, harsh blue-white glare, crisp blue-graded shadow. Loupe: Sirius B beside Earth at the same scale |
| 16.8–23.7 | Kepler-16 | the sky turns red-orange. Both suns flank the conifer with big halos and sink toward the treeline, casting a V of shadows: A's shadow is lit crimson by B, and B's shadow is lit gold by A |
| 23.7–30.5 | Algol | blue-white day. The loupe shows B (big, dim, orange) sliding across A with a gas stream. The total light follows the computed eclipse: the sky drops to violet dusk, stars appear, lamps flicker on, then it all recovers |
| 30.5–34.7 | W UMa | violet-white glare. The loupe shows the tidally stretched peanut, the shared glowing envelope and a spiral outflow. The daylight pulses twice per orbit (computed light curve) |
| 34.7–39.9 | white-out → our Sun | "Nearly half of Sun-like stars have a partner. Ours is single." Loops to frame 0 |

## Science notes and sources
- **α Centauri:** radii from Kervella et al. 2017, Teff A 5,790 K and B 5,260 K, L ≈ 1.52 and 0.50 L☉. Orbit:
  a ≈ 23.6 au, e = 0.52, so the separation runs ~11.4–35.9 au (Pourbaix & Boffin 2016). B's V magnitude from the planet
  is M_V(B) = 5.71, giving m = −20.6 at 11.4 au and −18.1 at 35.9 au. The full Moon is −12.74, so B is **~140 to
  ~1,400× brighter than the full Moon** ("hundreds of times"). That is ~250–2,500 lux-scale light, enough that nights
  with B above the horizon never get dark ("some nights"). The narration says "outshines hundreds of full Moons".
- **Sirius:** A 1.711 R☉, 9,940 K, 25.4 L☉ (Davis et al. 2011; Adelman 2004; Liebert et al. 2005). B is 1.02 M☉,
  0.0084 R☉ ≈ 5,840 km (Earth is 6,371 km), ~25,000 K (Barstow et al. 2005). Orbit a = 19.8 au, e = 0.59, so 8.1–31.5
  au. From 5 au around A, B is mag −12.7 to −15.7: as bright as 1 to 15 full Moons, a brilliant point.
- **Kepler-16 (Doyle et al. 2011):** M = 0.690 + 0.203 M☉, R = 0.649 + 0.226 R☉, T_A = 4,450 K, binary period 41.1 d,
  a = 0.224 au. The planet has P = 228.8 d ("229-day year"), a = 0.705 au, 0.33 M_J. The maximum angular separation of
  the suns is atan(0.224/0.705) = 17.7°. L_B/L_A ≈ 0.037.
- **Algol (Baron et al. 2012):** A 3.17 M☉, 2.73 R☉, ~182 L☉; B 0.70 M☉, 3.48 R☉, ~6.9 L☉; P = 2.867 d,
  a = 0.0618 au, i = 98.7°. Primary minimum is ~1.2–1.3 mag (V 2.1 → 3.4). The Short computes the eclipse from that
  geometry (limb-darkened discs, B at ~10 % of A's surface brightness). Minimum light is 32 % (1.22 mag), and that drives
  the daylight. The primary eclipse lasts ~10 h in reality. "Demon Star" comes from the Arabic ra's al-ghūl, "the
  demon's head". There is also a third star, Algol C (F-type, 2.7 au from the pair, ~10 L☉). From a circumtriple orbit
  it would be another very bright point. It is left out of the picture and the narration for time.
- **W UMa:** P = 0.3336 d (8 h); M ≈ 1.19 + 0.57 M☉ → a = 2.44 R☉ (Kepler's third law); R ≈ 1.08 + 0.78 R☉; F8,
  ~6,200 K; i ≈ 86°. A contact binary: both stars overfill their Roche lobes and share one envelope. The computed light
  curve gives ~0.65 mag between maxima and minima (observed ~0.7 mag).
- **Ending:** Raghavan et al. 2010 find ~44 % of solar-type (F6–K3) stars are in binary or multiple systems, and
  Moe & Di Stefano 2017 agree. Hence "nearly half of Sun-like stars", not "half of all stars". Most stars are M dwarfs,
  and their multiplicity is lower (~25–30 %).
- **Extinction at sunset:** Kasten & Young airmass, 0.21 mag/airmass in V. Low suns are reddened per channel.

## Liberties (deliberately not captioned, per the user)
- **Double-shadow strength.** A genuinely visible second shadow needs the second star to give a sizeable share of
  the light. Shown with honest geometry but boosted strength:
  - **Kepler-16:** at sunset the extinction gap between the low A and the higher B narrows the ratio to ~5–20 %. B's
    shadow-casting light is boosted (×6, with a floor of 0.75× A's) so its shadow reads.
  - **α Cen by day:** B's real share is 1/250–1/2,500, so its daytime shadow is drawn at 0.5× A's. B's night shadow is
    honest (B is then the only source, with eye-adapted exposure).
  - **Sirius, Algol and W UMa:** these keep one shadow. Sirius B is 1/8,000 of A. The Algol and W UMa pairs are only
    0.25° and 0.75° apart, so their shadows coincide.
- **Shadow geometry:** the 2.5-D ground plane follows `../betelgeuse-tonight`, extended with the treeline profile as a
  caster. The shadow light is stylised low (14°, sunset ≥ 9°/11°) so the shadows run long. The suns are placed
  within ~3° of the conifer's azimuth, because only then do the shadows of distant objects run towards a 1.3 m-high
  camera as wide wedges.
- **Placement and timing:** companions sit at plausible but chosen positions. α Cen B is 7° from A, which happens only
  at certain orbital phases. Orbital motion, the sunset (~15° in 5.7 s), the Algol eclipse (10 h) and the W UMa orbit
  (8 h in 5 s) are time-compressed.
- **Sky and grade:** sky colours per system are stylised, tinted by the mixed starlight. W UMa's "violet-white glare"
  and Algol's "violet dusk" are art direction; an F star's daylight is essentially white. Kepler-16 B's light is
  pushed crimson-pink to separate the two shadow colours. Exposure adapts like the eye (the sunset and the night are
  brightened).
- **Loupes:** these are magnifier insets, at about ×35 (Algol), ×16 (W UMa) and ×~600,000 (Sirius B vs Earth). Algol B
  is shown brighter than its true ~2 % surface brightness so it is visible. The Algol gas stream and the W UMa outflow
  spiral are real phenomena drawn artistically. Beams, spikes, shockwaves and flashes are artistic devices.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (Kokoro via `../lib/voice.py`), and `audio/mix.py`. The mix has a chord
  pad per system (it sags with the Algol eclipse and pulses with the W UMa orbit), swap whooshes, thumps and shimmers,
  a night shimmer, a double-sunset riser and hit, an eclipse drone and the white-out riser and hit. It is mixed to
  −14 LUFS / −1 dBTP and also writes `out/second-sun.srt`.
- `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/B2-second-sun/`.
- Outputs (`out/`, git-ignored): `second-sun-short.mp4`, `second-sun.srt`, `thumb-vertical.jpg`, `thumb.jpg`.

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `thumbnail.py`.
