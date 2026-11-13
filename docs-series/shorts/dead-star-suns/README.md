# What If Dead Stars Replaced Our Sun? (YouTube Short, 9:16 only)

This cut is vertical only: 1080×1920 at 30 fps, 35.9 s long. It is one locked tripod shot of the user's `A2_park.png`
(transparent sky), starting in daytime, in the "swap" format of `../other-suns`. Five stellar remnants replace the
Sun one after another. Each sits at 1 au and is drawn at its true angular size and true visible brightness. Each swap
has a flash, a chromatic shockwave and beams, and the park is relit for every object. A bold readout (NAME / size
line / one fact) and one big orange word at a time (at ~46 % height) go with each object. A white-out returns to the
opening Sun, so the Short loops. There are no disclaimer captions (user rule).

## Narration (Kokoro am_michael @ 0.92, ~0.35 s between sentences, ~0.7 s at beat changes, −14 LUFS / −1 dBTP)
77 words. Each sentence is its own TTS line, so the pauses are exact.
> Every star dies. What if a dead one replaced our Sun? A white dwarf: the Sun's mass, Earth's size. Daylight fades to
> twilight. Earth freezes. A neutron star. Noon turns to night. A pulsar, sweeping its beams up to seven hundred times
> a second. A magnetar. One flare from here would strip away our atmosphere. A black dwarf, cold and dark. None exist
> yet. The universe isn't old enough. Our Sun will end as a white dwarf.

## Beats (`short.py`)
| t (s) | object | look | readout |
|---|---|---|---|
| 0–4.8 | Sun | blue sky, rainbow beams, conifer shadow | OUR SUN / 1 SUN'S MASS · 1.4 MILLION KM WIDE / ALIVE · 5,800 K |
| 4.8–12.2 | white dwarf | a blinding blue-white point. A cold, dim blue twilight with the first stars, and the lamps flicker on. A loupe shows the white dwarf beside Earth at the same scale. Frost creeps over the lawn on "freezes" | WHITE DWARF / SUN'S MASS · EARTH'S SIZE / 1/400 OF OUR DAYLIGHT · EARTH −170 °C |
| 12.2–15.6 | neutron star | starry night at noon, Milky Way. A small point with a pointer ring and a point-lens warp of the drifting starfield (arcs and an Einstein ring) | NEUTRON STAR / 1.4 SUNS · 24 KM WIDE / A TEASPOON: 2 BILLION TONNES |
| 15.6–20.6 | pulsar | two lighthouse beams sweeping across the sky, slowed to 0.55 turns/s. Each time a beam crosses us there is a cyan flash and a "ping" | PULSAR / A SPINNING NEUTRON STAR / UP TO 716 TURNS PER SECOND |
| 20.6–26.0 | magnetar | glowing 3-D dipole field lines with particles streaming along them, spinning at the real 7.56 s period. On "flare": a white-violet flash, a double chromatic shockwave, the sky lit violet with rising curtains, and the lamps knocked out | MAGNETAR / FIELD ~1,000 TRILLION × EARTH'S / 2004 FLARE: FELT ACROSS THE GALAXY |
| 26.0–32.5 | black dwarf | a black point hiding the stars, with a pointer ring. Deep-blue starry sky, frozen dark park, lamps off | BLACK DWARF / SUN'S MASS · EARTH'S SIZE · COLD / UNIVERSE: 13.8 BILLION YRS · NOT ENOUGH |
| 31.6–35.9 | white-out → Sun | "Our Sun will end as a white dwarf." Loops to frame 0 | OUR SUN / 1.4 MILLION KM WIDE · ALIVE / WHITE DWARF IN ~8 BILLION YEARS |

## Science notes (checked against the brief; corrections marked ⚠)
- **White dwarf (Sirius B-like):** 1.02 M☉, R = 0.0084 R☉ = 5,840 km (Earth is 6,371 km), T ≈ 25,000 K (Barstow et al.
  2005).
  - ⚠ The angular size from 1 au is 11,680 km / 1 au = 7.8×10⁻⁵ rad = **0.0045° (16″)**, not 0.0005°. That is 0.05 px
    on screen, so it is drawn as a point.
  - Bolometric L = R²T⁴ = 0.025 L☉, inside the brief's 0.03–0.1 L☉ range for a hot young white dwarf. So Earth's
    equilibrium temperature drops from 255 K to 255 × 0.025^¼ ≈ 101 K (**≈ −170 °C**).
  - Visible light: Sirius B has M_V = 11.33 (V = 8.44 at 2.64 pc), against the Sun's 4.83. That is 6.5 mag, so
    **1/400 of our daylight** (apparent magnitude −20.2 from 1 au), about 250 lux. That is deep-overcast or
    early-twilight light, so the park is graded as a cold, dim blue twilight.
- **Neutron star:** 1.4 M☉, with a radius of 12 km from NICER (12–13 km), so **24 km wide** (the brief's "about 20 km";
  the readout says 24). Its angular size from 1 au is 9×10⁻⁶°.
  - ⚠ It is not completely invisible in visible light. A young, cooling neutron star at ~5×10⁵ K, such as RX
    J1856.5-3754 (V = 25.6 at ~120 pc), would be **mag ≈ −11.4** from 1 au: a point about a third as bright as the full
    Moon. So it is drawn as a small bright point. That gives moonlight-level illumination at most, so the sky is a
    starry night ("noon turns to night" holds). An old, cold neutron star would be truly invisible.
  - Teaspoon: 1.4 M☉ in a 12 km radius gives a mean density of 3.8×10¹⁷ kg/m³, so 5 mL ≈ **1.9 billion tonnes**. The
    readout says "2 BILLION TONNES", the same derivation and wording as `../../11-neutron-star-teaspoon` ("about two
    billion"). The brief's "a billion tonnes" is the low popular figure, and 2 billion keeps us consistent with the
    earlier film.
  - Lensing: Rs = 4.14 km. For a source at infinity, the Einstein radius θE = √(2Rs/1 au) = **48″**, which is 0.27 px
    on screen. That is drawn at 78 px (liberty, below).
- **Pulsar:** spin rates run from ~1 per second to 716 per second (PSR J1748−2446ad, Hessels et al. 2006), so "up to
  seven hundred times a second" and "UP TO 716 TURNS PER SECOND". The beams are shown slowed down (0.55 turns/s).
  - A beam in empty space is invisible from the side: you would only see the star flash when a beam sweeps across you.
    The young Crab pulsar is even an optical pulsar (V ≈ 16.5 at 2 kpc, which would be about Sun-bright at 1 au). The
    flashes are honest; the visible sweeping beams are the "if you could see its beam" device. They are not
    narrated as visible light.
- **Magnetar:** surface fields are 10¹⁰–10¹¹ T, against Earth's ~5×10⁻⁵ T, so ~10¹⁴–10¹⁵× (SGR 1806-20: ~2×10¹¹ T).
  The readout says "~1,000 TRILLION ×".
  - The 27 Dec 2004 giant flare of SGR 1806-20 released ~2×10³⁹ J (isotropic, at the older 15 kpc distance) in ~0.2 s
    and measurably disturbed Earth's ionosphere.
  - Its distance has been revised from ~15 kpc (50,000 ly) to ~8.7 kpc (28,000 ly; Bibby et al. 2008). So the readout
    says "FELT ACROSS THE GALAXY" rather than a single figure.
  - At 1 au, the fluence is 2×10³⁹ J / 4π(1 au)² ≈ 7×10¹⁵ J/m², so Earth intercepts ~9×10²⁹ J. Removing the atmosphere
    (5×10¹⁸ kg against an escape energy of ~6×10⁷ J/kg) needs ~3×10²⁶ J, about 3,000× less. Hence "would strip away
    our atmosphere".
  - Spin: SGR 1806-20 has P = 7.56 s, and the field lines rotate at exactly that rate.
- **Black dwarf:** a white dwarf cooled until it no longer glows. Cooling times are ~10¹⁵ years (estimates range from
  10¹⁴ to 10¹⁵+), far longer than the 13.8-billion-year age of the universe. No black dwarfs exist yet.
- ⚠ **The Sun's end:** the Sun leaves the main sequence in ~5 billion years, and becomes a white dwarf after the
  red-giant and AGB phases, ~7.5–8 billion years from now. So the narration says "Our Sun will end as a white dwarf"
  (no date), and the readout says "WHITE DWARF IN ~8 BILLION YEARS".

## Liberties (deliberately not captioned, per the user)
- **White dwarf:** the dimming is staged. The view is bright for ~1 s after the swap, then settles into twilight, and
  deepens further on "daylight fades". Exposure adapts like the eye. The loupe magnifies ~10⁶×.
- **Neutron star:** the lensing is drawn ~290× larger than reality (θE 78 px versus 0.27 px) so that the arcs read. The
  starfield drifts slowly (sky rotation, sped up) so the lensed arcs move. The pointer ring marks it.
- **Pulsar:** the beams are made visible and slowed by a factor of ~2 to ~1,300. The flash geometry (beam 52° from the
  spin axis, crossing our line of sight once per turn) is chosen.
- **Magnetar:** the field lines are a stylised dipole. The violet sky, the curtains and the knocked-out lamps are art
  direction for the flare hitting the atmosphere. The real fate (the atmosphere stripped away) takes longer and is
  only narrated.
- **Black dwarf:** a point-mass Earth-sized body at 1 au spans 0.05 px. It is drawn as a 6 px black dot so it can be
  seen at all.
- **Grade:** sky colours are stylised per object (deep blue, violet and so on). The sky is never pitch black (user
  rule). Beams, spikes, shockwaves and flashes are artistic devices. The frost texture comes from `../lib/foreground.py`.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (Kokoro via `../lib/voice.py`) and `audio/mix.py`. The mix has a chord
  pad per object, swap whooshes, thumps and shimmers, an icy shimmer as Earth freezes, a ping per pulsar flash, a
  magnetar riser, thump and hit, a black-dwarf drone and the white-out riser and hit. It also writes
  `out/dead-star-suns.srt`.
- `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged). Code adapted from `../second-sun/short.py` (sky, beams, shadows, relight, loupe).
  Scratch: `.../scratchpad/series/B2-dead-star-suns/`.
- Outputs (`out/`, git-ignored): `dead-star-suns-short.mp4`, `dead-star-suns.srt`, `thumb-vertical.jpg`, `thumb.jpg`.

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `thumbnail.py`.
