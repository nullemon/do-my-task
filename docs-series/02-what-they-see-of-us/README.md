# 02 — WHAT THEY SEE OF US

A 4:41 narrated documentary (1920×1080, 24 fps). We pull back from Earth in one continuous flight, looking back at
home; each real star we pass is labelled with its distance and the year on Earth whose light is arriving there *now*
(November 2026 minus the distance), with a small silhouette vignette of that moment. Script, beats and shot list:
`SCRIPT.md`.

## Deliverables (`out/`, gitignored)
See the bottom of this file for sizes/durations of the final encodes.
- `what-they-see-of-us-1080p.mp4` — master: x264 CRF 18, AAC 256 kb/s, +faststart, soft English subtitle track.
- `what-they-see-of-us-1080p-hq.mp4` — chat-delivery size (CRF 19 capped at 9.5 Mb/s, ≤ 380 MB).
- `what-they-see-of-us-4k.mp4` — **3840×2160 lanczos UPSCALE of the 1080p render** (not native 4K detail), CRF 20.
- `what-they-see-of-us-4k-share.mp4` — the same upscale, capped at 12.5 Mb/s (≤ 480 MB).
- `what-they-see-of-us.srt` — subtitles from the real narration timings (also muxed, off by default).

## Pipeline (rebuild)
```
# voice (Kokoro am_michael @0.94, same voice as the series), then lock the timeline to it
/home/user/ttsenv/bin/python audio/gen_voice.py
python3 timeline.py                                   # -> timeline.json (line times, camera log-distance s(t), objects)
# Blender (bpy 5.1.2, Cycles CPU)
/home/user/bpyenv/bin/python -c "import sys; p='blender/bg_loop.py'; sys.argv=['blender','--','--frames','0-191','--samples','6']; exec(compile(open(p).read(),p,'exec'))"
/home/user/bpyenv/bin/python -c "import sys; p='blender/bodies.py'; sys.argv=['blender','--','earth']; exec(compile(open(p).read(),p,'exec'))"   # and 'moon'
python3 gen_tex.py && python3 vignettes.py            # numpy plates + PIL silhouette vignettes
bash render_all.sh                                    # comp.py in 3 parallel segments -> master_silent.mp4
/home/user/ttsenv/bin/python audio/mix.py             # voice chain, music bed, ducking, loudnorm, SRT
bash assemble.sh                                      # grain + vignette, mux, 4 deliverables
```

### How the flight works (and why it was cheap)
- **One camera model everywhere.** Earth at the origin, camera at distance D looking back at it, horizontal FOV 50°.
  Every object sits at its *true* distance d in a chosen direction; it slides in from the frame edge once the
  camera is past it and drifts toward Earth as we recede. The film's clock drives `s(t) = log10(D)` (monotone-cubic
  through keyframes tied to the narration), from 0.11 light-seconds to 600 million light-years.
- **The starfield is a 192-frame Blender loop.** `bg_loop.py` renders a *self-similar* point-cloud starfield (one
  shell of 650 stars copied at scales 10^(n/2)); because the field is scale-invariant, receding by ×√10 returns the
  identical picture, so 192 frames loop forever. The compositor maps `s(t)` to loop phase and blends up to 10
  neighbouring loop frames when we move fast (motion blur). That replaced ~6,750 Blender frames with 192
  (~16 min of CPU at 6 spp, no denoise, 0 bounces). The stream is switched off inside the solar system and fades
  out as we leave the galaxy.
- Earth (NASA Blue Marble texture from the public-domain image bundled in the `three-globe` npm package) and the
  Moon (procedural) are single Blender stills scaled by 1/distance; the Milky Way is a perspective-warped plane
  through the galactic centre, tilted so the flight climbs out at 40°; galaxy textures reused from the series'
  Andromeda film; labels, counter, rings and cards are drawn in `comp.py` (Inter Light) and piped straight into x264.
- Vignettes (`vignettes.py`) are flat duotone silhouettes drawn with PIL — no people, no likenesses.

### Sound
- Voice: Kokoro-82M (offline ONNX), **am_michael, speed 0.94** — the series voice. Pronunciation helpers: Caph →
  "Kaff", Dubhe → "DUB-ee", Betelgeuse → "Beetlejuice", VY → "Vee Why", Maya → "MY-ah". 70 Hz HPF, light EQ, 3:1
  compression, short room reverb (same chain as the Andromeda film). Lines are placed with fixed pauses; no
  time-stretching.
- Music bed (numpy): A-minor world, detuned additive pads + low drone; tense beating cluster and sub swell at the
  radio-bubble crossing; sparkles at the Arcturus/Voyager callback; wide choir as the galaxy opens below us; dark
  Ab colour for the asteroid; resolves to an open A(add9) at "Somewhere, it's still happening"; silent at the end.
  Bed ducked ~8 dB under the voice. Two-pass `loudnorm` → −14 LUFS integrated, ≤ −1 dBTP.

## Facts, numbers and sources
Year seen = 2026.84 (early Nov 2026) − distance in light-years.

| object | distance used | source | sees |
|---|---|---|---|
| Moon | 384,400 km = 1.28 light-s | standard | 1.3 s ago |
| Sun | 1 AU = 499 light-s (8 min 19 s) | standard | 8 min 20 s ago |
| Pale Blue Dot | Voyager 1, 14 Feb 1990, 6.06 billion km (40.5 AU) | [NASA photojournal](https://science.nasa.gov/photojournal/solar-system-portrait-earth-as-pale-blue-dot) | — |
| Proxima Centauri | 4.2465 ly | [list of nearest stars](https://ipfs.ssi.eecc.de/ipns/en.wikipedia-on-ipfs.org/wiki/List_of_nearest_stars_and_brown_dwarfs) | ~Aug 2022 (JWST first images 12 Jul 2022) |
| Sirius | 8.60 ly | same | ~Mar 2018 |
| Vega | 25.0 ly | [Britannica](https://www.Britannica.Com/science/star-astronomy/Distances-to-the-stars) | late 2001 (ISS crewed since 2 Nov 2000) |
| Arcturus | 36.7 ± 0.2 ly (Hipparcos π = 88.83 ± 0.54 mas) | [Wikipedia](https://en.wikipedia.org/wiki/Arcturus) | ~Feb 1990 ± 3 months — the month of the Pale Blue Dot photo |
| Caph (β Cas) | 54.7 ± 0.3 ly (π = 59.58 ± 0.38 mas) | [Wikipedia](https://en.wikipedia.org/wiki/Beta_Cassiopeiae) | ~early 1972 (Apollo 16 Apr, Apollo 17 Dec 1972) |
| radio bubble | first regular broadcasts Nov 1920 → ~106 ly | [EarthSky](https://earthsky.org/space/earths-radio-bubble-extent-of-radio-signals/) | 1920s |
| Dubhe | 123 ± 2 ly (π = 26.54 ± 0.48 mas) | [Wikipedia](https://en.wikipedia.org/wiki/Dubhe), [Sky & Telescope](https://skyandtelescope.org/astronomy-news/meet-dubhe-giant-star-big-dipper/) | ~1904 ± 2 (Wright Flyer 17 Dec 1903) |
| Polaris | 446 ± 1 ly (Gaia DR3 via Polaris B; Hipparcos 433; Turner 2012 claimed 323) | [phys.org](https://phys.org/news/2012-11-astronomers-clash-distance-famed-north.html), [Nat Geo](https://www.nationalgeographic.com/adventure/article/121204-north-star-distance-closer-solar-system-space-science) | ~1580 (telescope 1608) |
| Betelgeuse | 548 +88/−49 ly (Joyce et al. 2020); older estimates up to ~650–720 | [Universe Today](https://www.universetoday.com/148423/wow-betelgeuse-might-be-25-closer-than-previously-believed/), [Kavli IPMU](https://www.ipmu.jp/en/node/8466) | ~1300s–1500s (Gutenberg press c. 1450) |
| Orion Nebula | 414 ± 7 pc ≈ 1,350 ly (Menten 2007); Gaia ~386–410 pc | [Menten et al.](https://www.arxiv.org/pdf/0709.0485), [S&T](https://skyandtelescope.org/astronomy-news/the-orion-nebula-exactly/) | ~AD 680–770 (Classic Maya) |
| Deneb | 1,400–2,600 ly — **very uncertain** (802 pc adopted from Cyg OB7 membership; reanalysed Hipparcos 433 ± 60 pc) | [Wikipedia](https://en.wikipedia.org/wiki/Deneb) | ~600 BC – AD 600 |
| VY Canis Majoris | 1.20 +0.13/−0.10 kpc ≈ 3,900 ly (Zhang et al. 2012, VLBA) | [ApJ 744, 23](https://ui.adsabs.harvard.edu/abs/2012ApJ...744...23Z/abstract) | ~1900 BC (range ~2300–1550 BC). Great Pyramid c. 2560 BC; Wrangel Island mammoths survived to ~4,000 years ago | 
| Galactic centre | 8.18–8.28 kpc ≈ 26,700–27,000 ly (GRAVITY 2019/2021) | [GRAVITY 2019](https://www.aanda.org/articles/aa/abs/2019/05/aa35656-19/aa35656-19.html) | ~25,000 BC — Last Glacial Maximum, 26,000–20,000 years ago ([Wikipedia](https://en.wikipedia.org/wiki/Last_Glacial_Maximum)) |
| LMC | ~49.6 kpc ≈ 162,000 ly | standard (Pietrzyński et al. 2019) | ~160,000 years ago |
| Andromeda | ~2.5 million ly | standard | Oldowan stone tools ~2.6 Mya (older Lomekwi tools ~3.3 Mya, hence "some of the first") |
| 66 Mly shell | Chicxulub impact 66 Mya | standard | — |

Minor labelled stars (≈ values, commonly cited): Alpha Cen A·B 4.37, Barnard's 5.96, Wolf 359 7.86, Altair 16.7,
Fomalhaut 25.1, Pollux 33.8, Capella 42.9, Castor ~51, Aldebaran 65.3 ± 1, Regulus 79, Spica ~250, Canopus ~310,
Rigel ~860 ly ([bright-star lists](https://web.pa.msu.edu/courses/2006fall/AST101/brightstars.pdf),
[Aldebaran](https://en.wikipedia.org/wiki/Aldebaran)).

**The telescope twist.** Diffraction limit θ = 1.22 λ / D with λ = 550 nm and D = 12,742 km gives 5.3 × 10⁻¹⁴ rad;
at Proxima (4.02 × 10¹³ km) that is ≈ 2.1 km, at VY CMa (3.7 × 10¹⁶ km) ≈ 1,900 km. ("A trickle of photons":
Earth's reflected light at those distances is vanishingly faint even before resolution is considered.)

**Radio.** Stars within ~100 ly number in the thousands to ~15,000+ (estimates vary), so the script says nothing
more precise. "Far too faint to pick out" — early AM broadcasts fall below any plausible receiver's sensitivity
within a few light-years.

## Honest limitations
- **Geometry is stylised.** Directions of the stars on screen are chosen for composition, not their real sky
  positions; distances (and therefore the years) are real. The camera is just *beyond* each star when it is
  labelled, so the top counter ("light arriving here left Earth …") always reads a little earlier than the label —
  that is correct, not a bug. The starfield stream is self-similar (equal stars per decade of distance), not a true
  uniform-density field; the Orion Nebula sprite is drawn ~5× its real size; the Milky Way is a generic barred-spiral
  texture, not a map, and the Sun's place in it is approximate.
- Years are central values; the uncertainties are shown on the labels where they matter (Betelgeuse, Deneb,
  VY CMa) and narrated ("give or take", "uncertain by a hundred or so", "a mystery").
- "Our first radio broadcasts, from the 1920s": regular public broadcasting began in 1920; a handful of experimental
  transmissions (Marconi 1901, Fessenden 1906) are a little farther out, but were far weaker still.
- "The first printing presses" refers to Gutenberg's press (c. 1450); woodblock and movable-type printing in East
  Asia are older.
- 4K files are lanczos upscales of the 1080p render.
- Shared CPU (4 cores, 4 videos): compositing ran at ~2–3.5 s/frame under heavy load.
