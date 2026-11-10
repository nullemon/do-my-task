# What If Famous Nebulas Were in Our Sky? (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 37.28 s long. There is also a 16:9 recomposition at 1920×1080. It uses the
`other-suns/` format: one **locked** tripod shot of the user's `C_city.png` rooftop city view, given a night grade with the
windows and street lamps still lit. The sky swaps from one real nebula photograph to the next, and each swap has a
flash, a chromatic shockwave, coloured light rays and a relit city. One big orange word is shown at a time, synced to
the voice. Each nebula also gets a factual readout: NAME, REAL SIZE · REAL DISTANCE, and IF IT WERE 15 LY AWAY: angle.
There are no disclaimer captions (user rule).

## Narration (95 words, Kokoro am_michael @ 1.05, −14 LUFS)
> What if the Orion Nebula was as close as our nearest stars? It would span seventy-seven degrees of sky. The Ring
> Nebula, a dying star's last breath, seven full Moons wide. The Pillars of Creation, four light-years tall, rising over
> the city. The Crab Nebula, an exploded star, its pulsar flashing thirty times a second. And Carina, over two hundred
> light-years wide. We'd be inside it. Even up close, they'd look fainter to your eyes than in photos, but your phone
> camera would see this. They're all out there right now, just very far away.

## Premise and numbers
Every nebula is moved to **d = 15 light-years** and keeps its real size. The stars within about 15 ly (Alpha Centauri,
Sirius, Procyon, Tau Ceti and others) are our nearest neighbours. The user suggested 10 ly, but at that distance we
would be *inside* the Orion Nebula, whose radius is 12 ly, so 15 ly keeps the premise consistent. The angular size is
θ = 2·atan(D / 2d). The lens is gnomonic with f = 960 px, which gives a 90° vertical field of view on 1920 px; the 16:9
cut uses the same pixel scale. So a nebula D ly across is f·D/d px wide on screen.

| nebula | real size | real distance | θ at 15 ly | on screen | image |
|---|---|---|---|---|---|
| Orion Nebula (M42) | ~24 ly | 1,344 ly (VLBA parallax, Hirota et al. 2007; 414 pc) | 77° | 1536 px (overflows the frame) | NASA (Spitzer + Hubble composite) |
| Ring Nebula (M57) | ~1 ly (main ring, 1.4′ at ~790 pc) | ~2,600 ly (Gaia parallax ≈ 1.27 mas) | 3.8° ≈ 7.4 full Moons | 64 px | JWST NIRCam |
| Pillars of Creation (in M16) | tallest pillar ~4 ly | ~6,500 ly | 15° | ~256 px | JWST NIRCam |
| Crab Nebula (M1) | ~11 ly | ~6,500 ly | 40° | ~700 px | Hubble mosaic |
| Carina Nebula (NGC 3372) | ~230 ly (2° at ~7,500 ly ≈ 260 ly) | ~7,500 ly | we'd be inside it (radius ≫ 15 ly) | all-sky | JWST "Cosmic Cliffs" (NGC 3324, the NW edge of the Carina complex) |

- **Brightness:** surface brightness does not change with distance. A nebula brought closer gets bigger, not brighter
  per square degree. So each photo keeps its own brightness, the "camera view". Even M42 at 15 ly would look like a
  greyish glow to the naked eye. The narration says so, and the picture shows it: on "fainter to your eyes" the sky
  drains to grey ghosts, and on "your phone camera" a shutter flash and a viewfinder bring the colour back.
- **Crab pulsar:** it spins 29.6 times a second. The sound uses a real 29.6 Hz click train. The picture shows a gentler
  7.5 Hz throb, because a 30 Hz strobe cannot be shown at 30 fps and would be a photosensitivity risk. The readout says
  "PULSAR: 30 FLASHES A SECOND".
- **Opening and loop:** the opening sky is the real HYG v4.1 star field (V < 7) around Orion. It uses a gnomonic camera
  centred on M42 with north up, plus the star-dates Milky Way. M42 sits at its real size of 1.0° as a 17 px smudge
  labelled "ORION NEBULA · 1,344 LY". On "close" it rushes in to 77°. The ending white-out returns to that same sky, so
  the Short loops.

## Image sources and licences
All images were taken from the GitHub repo **unit511/space-wallpapers** (commit 78febdc, 2026-04-08), which holds crops
and downscales of NASA/Webb releases. Its README links each file to the original release. Only the image files
listed below were kept, in scratch (`SCR/dl/img/`). Nothing was committed.

| used for | file in repo | original release (per repo README) | credit | licence |
|---|---|---|---|---|
| Orion | `4K/orion_hearth_4K.png` | images.nasa.gov **PIA01322** | NASA/JPL-Caltech/STScI (Spitzer + Hubble composite; verify the exact credit on the PIA page before upload) | NASA imagery, public domain (no copyright claimed) |
| Crab | `4K/crab_nebula_4K.png` | images.nasa.gov **PIA03606** | NASA, ESA, J. Hester and A. Loll (Arizona State University) | NASA: public domain. ESA/Hubble version: CC BY 4.0 |
| Ring | `4K/webb_ring.png` | webbtelescope.org 01H82G0PP38P6PBXQ11BEVSMY0 (2023) | ESA/Webb, NASA, CSA, M. Barlow, N. Cox, R. Wesson | **CC BY 4.0** (ESA/Webb). STScI material is public domain unless noted |
| Pillars | `4K/webb_pillars.png` | webbtelescope.org 01GK2KKTR81SGYF24YBGYG7TAP (2022) | NASA, ESA, CSA, STScI; J. DePasquale, A. Koekemoer, A. Pagan (STScI) | STScI: public domain unless noted. ESA/Webb version: CC BY 4.0 |
| Carina | `4K/webb_carina_4K.png` | webbtelescope.org 01G77PKB8NKR7S8Z6HBXMYATGJ (2022) | NASA, ESA, CSA, STScI | STScI: public domain unless noted. ESA/Webb version: CC BY 4.0 |

The HYG v4.1 star catalogue (astronexus/HYG-Database) is CC BY-SA 4.0 and is only used to place the background stars.

**Ready-to-paste credit line for the video description:**
> Nebula images: Orion Nebula – NASA/JPL-Caltech/STScI; Crab Nebula – NASA, ESA, J. Hester & A. Loll (ASU); Ring
> Nebula – ESA/Webb, NASA, CSA, M. Barlow, N. Cox, R. Wesson (CC BY 4.0); Pillars of Creation and Carina "Cosmic
> Cliffs" – NASA, ESA, CSA, STScI (J. DePasquale, A. Koekemoer, A. Pagan). Star positions: HYG Database (CC BY-SA 4.0).

## Liberties (deliberately not captioned, per the user)
- **Ring instead of Helix:** the brief suggested the Helix Nebula, but no Helix image was available from a reachable
  source. The Ring Nebula is used instead, a planetary nebula with a real JWST image. It is labelled honestly.
- **Positions and orientation:** every nebula is placed at the same spot in the sky (the swap format); only Orion is at
  its real place, in Orion's sword. The Pillars photo is turned upright (rotated 47.6°).
- **Image scale:** each photo frame is scaled so that the nebula's listed size matches its true angle. The Orion photo
  shows the bright core region and is mapped to the full 24 ly, so its outer faint structure is approximated by the
  photo's own extent. Carina is shown as an all-sky backdrop, because at 15 ly we would be inside it.
- **Enhancement:** the Orion photo gets a contrast, saturation and sharpening boost and a glowing Trapezium core. Edge
  masks are soft and noisy, and there are slow parallax drift, gas shimmer, twinkling of each photo's own stars, light
  rays, flashes and shockwaves. These are artistic VFX choices.
- **Sky and city:** the night sky is a stylised rich deep blue and violet, and the city glow at the horizon is
  stylised. The city is relit in each nebula's colour much more strongly than real nebula light could manage.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (a copy of the star-dates wrapper of `lib.voice`), `audio/mix.py` (sound +
  SRT).
- `prep.py`: builds the nebula sprites (`SCR/sprites.npz`) from the images.
- `skygeo.py`, `mwsky.py`: copied unchanged from `star-dates/`. The HYG `stars.npz` and `mw_gal.npz` caches are copied
  from the star-dates scratch folder.
- `short.py` (picture; `info`, stills and `vert`/`wide`), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged). Scratch: `.../scratchpad/series/S16-nebula-sky/`.
- Outputs in `out/` (git-ignored): `nebula-sky-short.mp4`, `nebula-sky-16x9.mp4`, `nebula-sky.srt`, `thumb.jpg`,
  `thumb-vertical.jpg`.

Pipeline: `prep.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `short.py wide` →
`encode.sh wide` → `thumbnail.py`.
