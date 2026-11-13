# What If Galaxies Were Bright Enough to See? (YouTube Short, 9:16 only)

1080×1920 at 30 fps, 37.07 s. Batch-2 swap format: one **locked** tripod shot of the user's `C_city.png` rooftop city at
night, with windows and street lamps still lit. The sky swaps from one galaxy to the next, each with a flash, a chromatic
shockwave and coloured light rays. The city is relit in each galaxy's colour. One big orange word is shown at a time.
Each galaxy gets a readout: NAME / × MOON'S SIZE / DISTANCE / STARS. A real full Moon (0.52°) sits next to each galaxy at
the same scale. The ending is a white-out back to the plain city sky, so the Short loops. There are no disclaimer
captions (user rule).

## Narration (94 words, Kokoro am_michael @ 1.05, −14.0 LUFS)
> There's a galaxy in our sky six times wider than the full Moon. You just can't see it. But what if your eyes could?
> Andromeda. A trillion stars, two and a half million light-years away. Triangulum, a face-on spiral, almost three million
> light-years out. Down south, the Magellanic Clouds. The large one spans twenty full Moons, its Tarantula Nebula glowing
> pink. The Whirlpool is tiny, a third of the Moon, thirty million light-years away. They're all up there right now, this
> big. Their light is just spread too thin. Your eyes aren't sensitive enough.

## Premise and geometry
Every galaxy is shown at its **true angular size**. Only its surface brightness is raised to long-exposure-camera level.
The lens is gnomonic with f = 6000 px per radian, which is **104.7 px per degree**: a telephoto view about 18° tall and
10° wide. At that scale a galaxy that is θ degrees across is θ × 104.7 px wide. The full Moon (0.52°) is 54 px.

| galaxy | visible extent | × Moon | distance | stars | on screen |
|---|---|---|---|---|---|
| Andromeda (M31) + M32 + M110 | 3.17° × 1.0° (D25, PA 35°) | 6.1× | 2.5 Mly (≈765 kpc) | ~1 trillion | 332 px |
| Triangulum (M33) | 70.8′ × 41.7′ (PA 23°) | 2.3× | 2.7 Mly | ~40 billion | 124 px |
| Large Magellanic Cloud | 10.75° × 9.17° | 20.7× | ~160,000 ly (≈50 kpc) | ~30 billion | 1126 px (fills the width) |
| Small Magellanic Cloud | 5.33° × 3.08° | 10.3× | ~200,000 ly (≈62 kpc) | a few hundred million | 558 px |
| Whirlpool (M51) | 11.2′ × 6.9′ | 0.36× (about ⅓) | ~30 Mly (28–31 Mly in recent TRGB/SN work) | ~100 billion (rough estimate) | 20 px, plus a ×25 loupe |

- **Real sky:** the star field is the HYG v4.1 catalogue (V < 7), projected about Andromeda. M31 sits at its real place
  among those stars. The frame is rolled 103° (one moment of the night's turning sky), so the disc runs across the
  frame. The GALEX image is registered to the sky with an exact 3-point affine: the measured pixel positions of the
  nucleus, M32 and M110 are mapped to their real RA/Dec. That fixes scale (23 px per arcmin in the 4K file), rotation
  and handedness (no mirror).
- **Hook:** the opening shows what the eye gets from a city: a faint grey smudge (Andromeda's core) with a pointer
  ring. Six real-scale full Moons are laid along Andromeda's true length ("6 FULL MOONS WIDE"). On "what if your eyes
  could", it charges up and flashes in.
- **Brightness (honest in the narration):** surface brightness is what limits us. The light of a galaxy is spread over
  a large area, so it falls below the eye's threshold, and city skyglow removes the rest. In the video, each galaxy is
  shown with the brightness and colour of a long-exposure camera view.

## Image sources and licences (nothing committed; the files are in scratch only)
| used for | file / ID | source | credit | licence |
|---|---|---|---|---|
| Andromeda (M31, M32, M110) | `4K/andromeda_4K.png` from GitHub **unit511/space-wallpapers** (commit 78febdc) = images.nasa.gov **PIA15416** | NASA GALEX ultraviolet | NASA/JPL-Caltech | NASA: public domain (no copyright claimed) |
| Triangulum (M33) | images.nasa.gov **PIA03033** "Anatomy of a Triangulum" (orig 2904²) | NASA GALEX | NASA/JPL-Caltech | public domain |
| Whirlpool (M51 + NGC 5195) | images.nasa.gov **PIA10200** "A Classic Beauty" (orig 1978×2850) | Chandra + GALEX + Hubble + Spitzer composite | X-ray: NASA/CXC; UV: NASA/JPL-Caltech; Optical: NASA/ESA/STScI/AURA; IR: NASA/JPL-Caltech/Univ. of Arizona | NASA: public domain |
| Moon disc | `8k_moon.jpg` (shorts-common, Solar System Scope) | Solar System Scope textures (based on NASA data) | Solar System Scope | CC BY 4.0 |
| Star positions | HYG v4.1 (astronexus/HYG-Database) | | | CC BY-SA 4.0 |

**LMC, SMC and the Milky Way core are procedural** (see liberties). No whole-galaxy colour photograph of the Clouds was
reachable from a source with a usable licence and resolution. The ISS photos iss071e418742 and iss072e281189 show both
Clouds, but only about 100 px across. ESO's wide-field shots are of the sites, with the Clouds small.

**Ready-to-paste credit line for the video description:**
> Galaxy images: Andromeda and Triangulum – NASA/JPL-Caltech (GALEX); Whirlpool – X-ray: NASA/CXC; UV: NASA/JPL-Caltech;
> Optical: NASA/ESA/STScI/AURA; IR: NASA/JPL-Caltech/Univ. of Arizona. Moon texture: Solar System Scope (CC BY 4.0).
> Star positions: HYG Database (CC BY-SA 4.0). Magellanic Clouds and Milky Way core: digital renderings.

## Liberties (deliberately not captioned, per the user)
- **Ultraviolet look:** the Andromeda and Triangulum photos are GALEX ultraviolet images, so their arms are bluer than
  in visible light. Andromeda also gets a warm-yellow bulge glow and a faint outer disc that extends the image to the
  3.2° visible extent. Saturation and contrast are boosted ("camera view").
- **Positions:** only Andromeda is at its real sky position, and only in its own scene. Triangulum (really 14.8° from
  M31, just out of frame), the Magellanic Clouds (southern sky, never above the horizon together with Andromeda) and
  M51 are placed above the skyline in the same star field. In the finale all five are rearranged to fit the frame, still
  at true size.
- **Orientation:** every image keeps its real north-up/east-left orientation and is turned by the same 103° frame roll.
  M33 and M51 are assumed north-up as released; M51 was checked against NGC 5195's position (4.4′ N, 15° E). The M33
  image scale is estimated so that its disc spans the 70.8′ D25 diameter.
- **Procedural LMC/SMC:** they are faithful lookalikes, with these features at their real sizes and real offsets:
  - the off-centre bar at PA 115°;
  - 30 Doradus (the Tarantula) with a teal core;
  - N11, N44 and N159/N160, plus about 34 smaller pink H II regions placed randomly;
  - about 70 blue young-star knots;
  - clumpy star clouds made of about 1 million fine stars;
  - the SMC bar at PA 45°, its Wing, and NGC 346;
  - **47 Tucanae**, which is really a Milky Way globular cluster in front of the SMC. It is included because every
    photo shows it there.
- **Milky Way core (finale):** a procedural long-exposure bulge (about 24° × 12°, with dust lanes and pink
  Lagoon/Trifid-like knots). It is drawn low and diagonal behind the city. It is not at its real place.
- **Loupe:** the Whirlpool is shown honestly at 20 px with a pointer ring. A magnifier inset (about ×25) shows its shape.
- **Sky and city:** the night sky is a stylised deep blue and violet. The city relighting by galaxy light is hugely
  exaggerated. Swap flashes, shockwaves, rays and a slow drift and parallax shimmer are VFX.
- **Thumbnails:** Andromeda is drawn about 3× its true size there, so it reads at thumbnail scale.

## Files
- `audio/narration.py`, `audio/gen_voice.py` (copy of the nebula-sky wrapper of `lib.voice`), `audio/mix.py` (sound + SRT).
- `catalog.py` (HYG → `SCR/stars.npz`; copied from star-dates), `skygeo.py`, `mwsky.py` (copied unchanged).
- `prep.py`: builds all sprites (`SCR/sprites.npz`) in one common north-up, 2× screen-scale frame.
- `short.py` (picture; `info`, stills, `vert`), `encode.sh` (mux, no `-shortest`), `thumbnail.py`.
- Scratch: `.../scratchpad/series/B2-galaxies-visible/` (downloads in `dl/`).
- Outputs in `out/` (git-ignored): `galaxies-visible-short.mp4`, `galaxies-visible.srt`, `thumb-vertical.jpg`, `thumb.jpg`.

Pipeline: `catalog.py` → `prep.py` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh` → `thumbnail.py`.
