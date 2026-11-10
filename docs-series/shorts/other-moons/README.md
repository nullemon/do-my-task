# What If Other Moons Replaced Our Moon? (YouTube Short)

The vertical cut is 1080×1920 at 30 fps and 36.77 s long. There is also a 16:9 recomposition at 1920×1080. The Short
uses the format of `other-suns/` and `planets-as-moon/`: one locked tripod shot of the user's `A2_park.png`
(transparent sky), here at blue hour. The sky swaps from our Moon to one moon after another, each placed at the Moon's
distance. Every swap has a flash, a chromatic shockwave and coloured moonlight beams, and the park is relit in each
moon's tint (the lamps come up when the sky goes dark for Phobos). One big orange word is shown at a time, synced to
the voice. A readout appears for each moon: NAME, × MOON'S SIZE and the angular width in degrees. There are no
disclaimer captions (user rule).

## Narration (90 words, Kokoro am_michael @ 1.05)
> What if other moons replaced our Moon? Same distance, true size. Here's our Moon, for scale. Mars's moon Phobos.
> Where did it go? That speck. You'd barely see it. Europa. Slightly smaller, a cracked ball of ice. Io. A little
> bigger, and covered in erupting volcanoes. Titan. One and a half times wider, wrapped in thick orange haze. Ganymede.
> The biggest moon in the solar system, even wider than Mercury. Now imagine all of them at once. Still, compared to
> its planet, ours is the biggest moon of any planet.

## Beats (`short.py`)
Every moon is placed at d = 384,400 km and drawn at its true angular size, θ = 2·asin(R/d). The lens is a long
telephoto, f = 16,000 px (about 7° vertical field of view), which gives the classic "giant moon behind the tree" shot
(approved by the lead). The relative sizes and the readouts stay exact. A realistic wide lens (f = 1400 px, as in
`planets-as-moon`) would make every moon a 5–10 px dot. The sky gradient, extinction and star field use a stylised
1400 px dome. The 16:9 cut keeps the same pixel scale.

| moon | R (km) | × Moon | angular width | radius on screen | look |
|---|---|---|---|---|---|
| Moon | 1,737.4 | 1 | 0.52° | 72 px | silver, iridescent corona |
| Phobos | 11.08 (mean; 27×22×18 km) | 0.006 | 0.0033° | 0.46 px | a sparkle; glowing pointer ring with brackets + sonar ping; the sky darkens, stars and lamps come up |
| Europa | 1,560.8 | 0.90 | 0.47° | 65 px | white water ice, reddish-brown lineae (colourised USGS mosaic), cyan sky |
| Io | 1,821.6 | 1.05 | 0.54° | 76 px | sulfur yellow-orange, Pele's red ring; two ballistic plumes on the limb (Pele-like umbrella ≈0.28 R) + flickering lava hot spots |
| Titan | 2,574.7 | 1.48 | 0.77° | 107 px | featureless orange haze ball (faint surface + darker northern hood), haze envelope and blue detached haze layer |
| Ganymede | 2,634.1 | 1.52 | 0.79° | 110 px | real colour mosaic; faint auroral ovals |
| finale | + Callisto 2,410.3, Triton 1,353.4 | | | | all eight pop in around Ganymede, with a name under each, hold ~1.6 s |

Phase lighting comes from the Sun, below the horizon behind the camera (`moons.py`, copied from `planets.py`): about
a 14° phase angle, Lommel–Seeliger for the rocky/icy moons, Minnaert and limb haze for Titan. Discs are 2×
supersampled, with maps pre-filtered to the on-screen scale. On "Still," a white-out returns to our lone Moon, so the
Short loops.

## Science notes
- **Radii:** NASA/JPL mean radii (Moon 1,737.4; Europa 1,560.8; Io 1,821.6; Titan 2,574.7; Ganymede 2,634.1; Callisto
  2,410.3; Triton 1,353.4; Phobos 11.08 km mean). The brief's angles check out: 0.52°, 0.003°, 0.47° (brief 0.46°),
  0.54°, 0.77°, 0.79° (brief 0.78°).
- **Ganymede vs Mercury:** 5,268 km vs 4,879 km diameter. Titan (5,150 km) is also wider than Mercury but less massive.
- **Ending line:** the Moon/Earth diameter ratio is 0.27. The next best among the planets' moons are Triton/Neptune
  (0.055), Titan/Saturn (0.044) and Ganymede/Jupiter (0.038). Charon/Pluto (0.51) is bigger relative to its body, but
  Pluto is a dwarf planet, hence "of any planet".
- **Brightness:** Europa (geometric albedo ≈0.67), Io (≈0.63) and Ganymede (≈0.43) would be several times brighter
  than our full Moon (≈0.12). Phobos (≈0.07, 0.46 px) would be a faint star-like point. The park relighting follows
  this order, compressed.

## Liberties (deliberately not captioned, per the user)
- Telephoto framing (see above). The beams, corona rings, shockwaves, pointer ring and swap animations are artistic
  devices.
- Io's plume heights are realistic (Pele ≈300–400 km), but the glow is exaggerated. Ganymede's aurora is UV in
  reality.
- The finale puts all the moons at the Moon's distance at once, a stylised "what if".
- Titan's map is a 938 nm surface mosaic, kept at about 10 % contrast under a uniform orange haze, as the eye would see it.

## Sources
- Moon: Solar System Scope `8k_moon` (CC BY 4.0), `shorts-common/dl/sss/`.
- Europa, Io, Ganymede, Callisto: USGS Voyager/Galileo SSI global mosaics. Titan: USGS Cassini ISS PIA19658 global
  mosaic. Triton: Voyager 2 PIA18668 (Schenk 2014). All are public domain (NASA/JPL/USGS). They were fetched as the 2048 px
  rungs from the GitHub LFS mirror `alexmensch/stellata` (`data/textures/*-2048.jpg`; provenance table in its
  `data/textures/src/README.md`) into `shorts-common/dl/moons/`.
- Foreground: the user's `A2_park.png`.

## Files
- Code: `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (sound + SRT), `moons.py` (lit sphere renderer),
  `short.py` (picture; `info`, stills and `patch` modes), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Shared code: `../lib/` (unchanged).
- Scratch: `.../scratchpad/series/S14-other-moons/`.
- Outputs: `out/` (git-ignored): `other-moons-short.mp4`, `other-moons-16x9.mp4`, `other-moons.srt`, `thumb.jpg`,
  `thumb-vertical.jpg`.
