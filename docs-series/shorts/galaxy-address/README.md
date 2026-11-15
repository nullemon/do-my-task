# What If Earth Were Somewhere Else in the Galaxy? (YouTube Short, 9:16 only)

1080×1920 at 30 fps, about 45.6 s. BATCH3 swap format: one **locked** shot of the user's `07_mountain_observatory.png`
(a white dome on a rocky summit, 79 % sky) at night. The sky swaps between five "addresses" for Earth. Each swap has a
tinted flash and a chromatic shockwave that reveals the new sky inside its ring, plus coloured light beams from the scene's
centre. The summit is relit in the light of each sky, a readout shows NAME / three factual lines, and the captions are
one big orange word at a time. A white-out returns to today's sky (the sidereal drift is re-based so it loops). There
is no disclaimer small print (user rule).

## Narration (REDO v3 style: 75 words, ~44 s of speech)
Voice: Kokoro 0.7 am_michael + 0.3 am_onyx at 0.86, one TTS call per phrase, real word timings, v3 post chain
(`../lib/v3_kit.py`), 0.45 s between phrases and 1.15 s before each reveal. In the mux: a 17 kHz low-pass before AAC.
> Imagine moving Earth... to a new address in the galaxy. / First... the galactic centre. / Millions of stars crowd the
> sky. / Night never gets dark. / Now... a stellar nursery. / Glowing clouds... and newborn blue stars. / Then... we rise
> above the disk. / Thirty thousand light-years up... / the whole Milky Way... hangs over us. / And now... the Boötes Void.
> / No stars at all. / Just a few faint galaxies... far away. / Back home... / we got a pretty good seat.

"Boötes" is spoken via the respelling "Bo-oh-tees". Each swap lands on the name of the place.

## The skies and the numbers (verified)
| beat | how it's made | readout (checked) |
|---|---|---|
| **Today** (home) | Real HYG v4.1 sky (V < 6.5) at 34° N, sidereal time 19.3 h, so the summer Milky Way arches up from the south. Milky Way band from `mwsky.py` (star-dates look). Lens: stereographic, f = 540 px, centred at alt 60° facing south (`skygeo.py`, `catalog.py`, `mwsky.py` copied from star-dates). | The Sun is ~26,000 ly from the centre (GRAVITY 2019: 8.18 kpc = 26,700 ly), in the Orion Spur. HYG has 5,019 stars with V < 6 ("~5,000 visible by eye", whole sky). |
| **Galactic centre** | star-clusters' population synthesis of the nuclear star cluster (`clusters.py nsc`, copied, unchanged apart from SCR): 25 M stars, broken power law, the young O/B/WR cluster and IRS 7; the observer 1 pc (3.3 ly) from Sgr A*. Stars with V < −3.2 (3,369) are drawn as distinct spiked points; all others are summed into a smooth integrated glow. Procedural dark dust lanes. | Simulation output (`SCR/stats.json`): 1.51 million stars within 1 pc (≈3.3 ly; "~1.5 million within 3 ly"); 12,729 brighter than Sirius; total starlight V ≈ −15.9, i.e. ~19× the full Moon (−12.7) → "≈ 20 full Moons". "Millions of stars crowd the sky": 2.2 million with V < 6. |
| **Stellar nursery** | Procedural plate (`prep.py`): domain-warped pink H-alpha clouds, teal O III cores near five young clusters, dust lanes with bright ionisation rims, ~200 young O/B stars plus 9,000 field stars, one Eta-Car-like star. | Modelled on the Carina Nebula: ~7,500 ly away (Gaia 2.35 kpc) in the Carina–Sagittarius arm, ~2° across ≈ 250 ly, dozens of O stars only a few Myr old. The readout says "like the Carina Nebula", not "the Carina Nebula". |
| **Halo, 30,000 ly up** | NASA/JPL-Caltech/R. Hurt face-on Milky Way (PIA10748), mapped physically for an observer 30,000 ly above the galactic centre: a ray at angle θ from the centre direction hits the disc at R = h·tan θ, with an optically-thin brightening ∝ (1/cos θ)^0.5. The image width is taken as 120,000 ly (disc ~100,000 ly). Plus 140 faint halo giants and 14 globular clusters. | Disc of radius 50,000 ly at 30,000 ly: 2·atan(5/3) = 118° → "spans ~120° of sky". |
| **Boötes Void** | Very dark blue sky (never black: lin ≈ 0.004–0.02) plus airglow (green 557.7 nm band peaking ~12° up, faint red above), no stars, six small faint galaxies (two spirals clearly shaped), ringed on "faint galaxies". | ~330 million ly across, centre ~700 Mly away, ~60 galaxies found inside (Kirshner et al. 1981; Kirshner et al. 1987). If the Milky Way sat in its centre, the nearest large galaxies would be too faint for the naked eye (the classic remark that we would not have known about other galaxies until the 1960s). |

## Liberties (deliberately not captioned)
- **Moving Earth:** Earth (and the Sun) are simply dropped into each place; Earth's orientation is chosen so each sky's
  centre faces the camera. In the halo, a planet would really have the disc in half its sky; here it is overhead.
- **Brightness:** the nebula, the face-on galaxy and the void galaxies are shown at long-exposure-camera brightness and
  colour. To the eye, H II regions and a face-on galactic disc (~21–24 mag/arcsec²) would look much fainter and greyer, and
  the void galaxies would need a telescope. The galactic-centre sky is drawn with perceptual compression.
- **Galactic centre:** no extinction inside the cluster; dust lanes are stylised (as in star-clusters).
- **Nursery:** entirely procedural (no real 3-D map of Carina from inside exists).
- **Halo:** an artist's concept (PIA10748), turned slowly; the disc thickness, warp and bulge height are not modelled.
- **Void:** the galaxy positions are invented; their faintness is exaggerated upwards so they read on a phone.
- **Motion:** the sidereal drift (0.05 h of LST per second) is a stylised time-lapse. Flashes, shockwaves, beams and the
  summit relighting are VFX.

## Sources and licences (nothing committed; the files are in scratch only)
- Face-on Milky Way: images.nasa.gov **PIA10748** "Our Milky Way Gets a Makeover", NASA/JPL-Caltech/R. Hurt (SSC) — NASA,
  no copyright claimed.
- Star positions: HYG v4.1 (astronexus/HYG-Database) — CC BY-SA 4.0.
- Galactic centre: population synthesis from star-clusters/clusters.py (Kroupa IMF; Genzel+ 2010, Schödel+ 2018;
  Paumard+ 2006, Lu+ 2009).

**Credit line for the description:**
> Milky Way illustration: NASA/JPL-Caltech/R. Hurt (SSC). Star positions: HYG Database (CC BY-SA 4.0). Other skies:
> digital renderings.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (galaxies-visible wrapper of `lib.voice`, v3 style), `audio/mix.py` (sound + SRT).
- `catalog.py`, `skygeo.py`, `mwsky.py` (from star-dates), `clusters.py` (from star-clusters), `prep.py` (plates).
- `short.py` (`info`, `stills t,t`, `seg` = restart-safe segment render), `encode.sh` (mux, 17 kHz low-pass, no
  `-shortest`, prints loudness), `thumbnail.py`.
- Scratch: `scratchpad/series/B3-galaxy-address/` (downloads in `B3-common/dl/`).
- Outputs (git-ignored): `out/galaxy-address-short.mp4`, `out/galaxy-address.srt`, `out/thumb-vertical.jpg`, `out/thumb.jpg`.

Pipeline: `catalog.py` → `clusters.py nsc` → `prep.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py seg` →
`encode.sh` → `thumbnail.py`.
