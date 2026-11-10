# Your Night Sky in 1 Million Years (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 36.47 s long. There is also a 16:9 recomposition at 1920×1080. It uses one
**locked** tripod shot of the user's `A2_park.png` (big tree, conifer, house, street lamps) at night, with the lamps on.
Everything happens in the sky. The real HYG sky fast-forwards from **YEAR 2026** to **YEAR 1,291,326** under a big
glowing counter that also reads out "N YEARS PER SECOND". Stars leave motion trails. Glowing stick figures stretch like
rubber bands and snap. At the end a rainbow rewind sends everything back to 2026, and the last frame matches the first,
so the Short loops. Captions are one big orange word at a time. There are no disclaimer captions (user rule).

## Narration (87 words, Kokoro am_michael @ 1.05, real word timings)
> The constellations aren't fixed. Watch what happens to the Big Dipper. Every star is moving. Barnard's Star, the
> fastest, shoots right across the sky. Five Dipper stars travel together, as a family. But Dubhe and Alkaid go their
> own way. In 100,000 years, the Dipper is broken. Orion's shoulders drift apart. Stars moving away fade out. And in
> 1.3 million years, Gliese 710 skims past the Sun, blazing brighter than any star we see today. Every constellation
> you know is temporary.

## Beats (`short.py`)
| t (s) | year | picture |
|---|---|---|
| 0–4.6 | 2026 | The Big Dipper glows over the park, with energy beads running along its lines. On "Big Dipper" the label appears and a ring burst fires on each of the 7 stars. |
| 4.6–10 | → 26,000 | The counter starts with a riser and a hit, and every star streaks. **Barnard's Star** shoots across the top of the frame as a red comet, with the readout FASTEST STAR · 10.4″/YR. Its real track runs from Ophiuchus, past the celestial pole (~15,000 yr), to Auriga. |
| 10–19.4 | → 160,000 | Velocity arrows show 60,000 years of motion: 5 cyan arrows point the same way (URSA MAJOR MOVING GROUP · 5 STARS · SAME MOTION), and the arrows for DUBHE and ALKAID point elsewhere. Faint path trails grow. The lines heat up, vibrate, and snap on "broken" with recoil, sparks and bursts. |
| 19.2–23.7 | → 1,000,000 | The sky sweeps to **Orion**. BETELGEUSE and BELLATRIX drift apart (7.5° → 17.4° in 1 Myr), and two lines snap. The vivid Milky Way crosses the frame. |
| 23.7–31.9 | → 1,291,300 | The sky sweeps to **Gliese 710**. It brightens from mag ~6 to −3.1 and streaks ~60° across the sky as it passes the Sun. The readout shows the live MAG and distance in au, ending at ~10,700 AU. A huge glare with spikes and a rainbow halo. The park gets only a faint silver tint (lead's note). |
| 31.7–34.6 | held | The sky sweeps back to the Dipper's place. The 2026 Dipper appears as a dashed ghost, and the 7 stars' million-year paths fan out across the sky ("temporary"). |
| 34.6–35.7 | → 2026 | A rainbow vortex REWIND (log-speed). Everything races back, then the Dipper re-links with a white flash. |
| 35.7–36.47 | 2026 | The opening frame again (loop). |

## Data and method
- **Catalogue:** HYG v4.1 (`astronexus/HYG-Database`, `hyg/CURRENT/hygdata_v41.csv`; Hipparcos + Yale BSC + Gliese).
  `catalog.py` keeps every star with V < 7 today plus every star that becomes brighter than V = 7 within 1.35 Myr
  (15,895 stars).
- **Propagation:** each star gets a heliocentric 3D position from RA, Dec and `dist`. Its 3D space velocity comes from
  `pmra` (μα*), `pmdec` and `rv` (rv = 0 where HYG has none). Each star moves in a straight line, r(t) = r₀ + v·t. The
  sky direction and the distance are recomputed every frame, so magnitudes change too: m = M + 5 log₁₀(d/10 pc).
  Approaching stars brighten and receding ones fade. Stars with absurd space velocities (> 400 km/s, from bad
  parallaxes) are dropped. Stars brighter than ~V 5.4 get shutter-sampled trails.
- **Overrides:**
  - **Barnard's Star:** HYG has `pmdec = 9999.99`, a placeholder. It is replaced by Gaia DR3 values: μα* −801.551,
    μδ +10362.394 mas/yr, parallax 546.976 mas, rv −110.5 km/s. Result: closest approach 1.155 pc (3.77 ly) in
    ~9,700 yr, peak V ≈ 8.5.
  - **Gliese 710:** the Hipparcos-era proper motion and rv are too coarse. Its straight-line trajectory is set to
    reproduce the Gaia DR3 encounter: **0.051 pc ≈ 10,500 au at 1.29 Myr** (Wikipedia, "Gliese 710"; de la Fuente
    Marcos & de la Fuente Marcos 2022: median 0.052 pc, 1.29 ± 0.02 Myr). It starts at its present place, parallax
    52.4 mas = 19.08 pc. The implied radial velocity is −14.5 km/s, which agrees with Gaia's ≈ −14 km/s.
    - Peak brightness comes from its absolute magnitude (V = 9.66 now → M ≈ 8.3): V ≈ −3.2 at 0.051 pc. That is
      brighter than Sirius today (−1.46), so the line says "brighter than any star we see today".
    - Note: the brief's "0.05 ly" should be **0.05 pc** (≈ 0.17 ly ≈ 10,500 au).
    - A 2026 study cited on Wikipedia gives a slightly wider pass, 0.062 pc (~12,800 au).
- **Checks from the propagation:**
  - α Centauri reaches 0.88 pc (2.9 ly) in 27,600 yr at V −0.9, matching the known ~3 ly at ~28 kyr. It is not shown.
  - Sirius goes from −1.44 now to −0.34 at 255 kyr and +2.8 at 1 Myr ("stars moving away fade out").
  - Altair peaks at V −0.6 in ~140 kyr, and Vega at −0.7 in ~290 kyr.
  - The Dubhe–Merak gap grows from 5.4° to 6.9° in 100 kyr, while the Moving Group stars keep together.
- **Moving group:** Merak, Phecda, Megrez, Alioth and Mizar are members of the Ursa Major Moving Group. Dubhe and Alkaid
  are not.
- **Barnard's Star:** at 10.4″/yr it has the largest proper motion of any star.
- **Milky Way:** the `mwsky.py` look (copied from star-dates), turned with the view. The colours of all ~16,000 stars
  come from B−V via a blackbody approximation.

## Liberties and caveats
- **Views:** there are three fixed sky orientations: the Dipper with the polar region, Orion, and the Gliese 710 field.
  Between them the celestial sphere swings along the shortest rotation, a ~1 s stylised sweep. The camera never
  moves. Within a view the Earth's daily rotation is frozen, so only stellar motion shows. The orientations are chosen
  for framing; they are not tied to one latitude or sidereal time.
- **Lens:** a tilted stereographic lens with f = 1320 px in 9:16 (raised ~1.3× at the lead's request so the Dipper
  reads on phones) and f = 1100 px in 16:9 (framed separately).
- **Barnard's Star** (V ≈ 8.5–9.5) is shown as a bright red comet, although it is a telescopic star.
- **Gliese 710:** its glare, spikes and halo are artistic.
- **Straight-line motion:** this ignores the stars' curved orbits in the Galaxy, which is fine for nearby stars over
  ~1 Myr. It also ignores stellar evolution: Betelgeuse is expected to explode within ~100,000 years, but here it
  simply keeps drifting. Stars that are too far for HYG to have good data change little.
- **Stars without a measured rv** get rv = 0, so only their transverse motion is shown.
- **Sky brightness and colours:** sky tint, Milky Way brightness and star brightness are stylised (vivid). The sky
  stays deep blue/violet.

## Files
- `catalog.py` (HYG → `SCR/moving.npz` with overrides), `skygeo.py` (lens + view rotations, adapted from star-dates),
  `mwsky.py` (copy), `short.py` (picture; `info`, stills), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- `audio/narration.py`, `audio/gen_voice.py` (star-dates' aligned wrapper of `lib.voice`), and `audio/mix.py`:
  - pad + arpeggio whose rate follows the counter speed
  - clock ticks and a wind/tone bed following log(years/s)
  - riser + hit at the fast-forward
  - a Doppler pass-by for Barnard's Star
  - rubber-band twang + crack on each snap
  - sweep whooshes
  - a long riser + hit + shimmer into Gliese 710
  - a reverse-tape rewind and a bright hit on the loop point
  - −14 LUFS, true peak limited to ≤ −1.4 dBTP
  - writes `out/sky-million-years.srt`
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/S10-sky-1myr/`.
- Outputs (`out/`, git-ignored): `sky-million-years-short.mp4`, `sky-million-years-16x9.mp4`, `sky-million-years.srt`,
  `thumb.jpg`, `thumb-vertical.jpg`.

Pipeline: `catalog.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `short.py wide`
→ `encode.sh wide` → `thumbnail.py vert` / `thumbnail.py wide`.
