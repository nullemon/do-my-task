# If Your Eyes Saw Gamma Rays, the Moon Would Outshine the Sun (YouTube Short)

This Short is 1080×1920 at 30 fps and runs 46.15 s (REDO v3, 9:16 only; the older 16:9 cut is not re-rendered). The look follows the lead's VFX direction in `../lib/README.md`: a huge, saturated sky that is always moving.

It uses a locked camera: one tripod frame of the park plate `A2_park.png` (941×1672, upscaled to 1080×1920) for the whole Short. Only the sky and the grade change. The sky switches "eyes": visible → infrared → radio → microwave → gamma rays → visible. The last switch loops back to the first frame. Each switch is a diagonal wipe with a rainbow edge, plus a stereo whoosh and a thump.

## Narration (REDO v3, 14 Nov: storytelling style, 75 words, 9:16 only, 46.15 s)
Kokoro voice style 0.7 × am_michael + 0.3 × am_onyx (blended vectors) @ 0.86, one TTS call per phrase, 0.4–0.5 s between
phrases and 1.0–1.2 s at each beat change. Voice post chain (pitch-only, timings stay valid): rubberband pitch 0.944 with
formants preserved, HPF 60 Hz, EQ, gentle compressor, short echo (`lib/v3_redo_q5.py`). The beats, swaps, readouts and
captions are re-timed to the new word timings. −14 LUFS / −1 dBTP. Scratch: `.../scratchpad/series/V3-<name>/`.
Render: `short.py segs` (restart-safe segments) → `audio/mix.py` → `encode.sh vert`.

> Imagine your eyes saw gamma rays.  
> The Moon would outshine the Sun.  
> First... infrared eyes.  
> Warm things glow... even the galaxy's dust.  
> Radio eyes.  
> The Sun dims...  
> but the Milky Way roars.  
> Microwave eyes.  
> The whole sky glows... with the Big Bang's afterglow.  
> And then... gamma rays.  
> The quiet Sun... nearly vanishes.  
> Cosmic rays slam into the Moon...  
> and it blazes.  
> NASA's Fermi telescope confirmed it.  
> Your eyes...  
> see a tiny slice of the sky.

## Beats
| t (s) | mode | picture |
|---|---|---|
| 0–4.5 | VISIBLE LIGHT | Blue morning sky with cirrus. The Sun sits low over the houses with slow rainbow beams. A pale waning crescent Moon is high up. |
| 4.5–9.5 | INFRARED EYES | Real Planck 857 GHz dust map: the dusty Milky Way burns gold and orange on a magenta sky. The air glows near the horizon. Foliage and grass turn white (Wood effect). The lamps and house windows heat up and glow. Heat shimmer. |
| 9.5–16.2 | RADIO EYES | Real Haslam 408 MHz map: the inner Galaxy is a blazing band and the North Polar Spur shows. A modest radio Sun. Twinkling radio sources: 4FGL blazars, which are radio-loud quasars, and named radio galaxies with ripple rings. |
| 16.2–21.8 | MICROWAVE EYES | Real Planck 100 GHz map: the CMB anisotropy is contrast-boosted into a blue/cream/orange mottle across the whole sky, with the Galaxy as a white-gold band. A slow luminous swell rolls across it. |
| 21.8–34.1 | GAMMA-RAY EYES | Real Fermi-LAT 3FHL photon map: a violet Galactic plane with sparkling single-photon hits and twinkling blazars. "The quiet Sun nearly vanishes": the Sun becomes a dark disc. Cosmic-ray streaks slam into the Moon, which becomes a huge filled, mottled, pulsing violet-white orb with a shock ring on "blazes". A gamma-ray burst flashes upper right. Fact card: NASA FERMI TELESCOPE · MOON > SUN · IN GAMMA RAYS ABOVE 31 MeV. |
| 34.1–38.5 | VISIBLE LIGHT | A white-out snap back to daylight, matching the opening (loop). |

## Data and sky geometry (all real, fetched from GitHub; media stays in scratch)
- **Radio:** Haslam et al. 408 MHz all-sky survey, the LAMBDA `lambda_haslam408_nofilt.fits` (HEALPix nside 512),
  via the git-LFS copy in `ingemarh/guisdap` (`matfiles/`).
- **Infrared and microwave:** Planck PR2 HFI 857 GHz and 100 GHz frequency maps at nside 128,
  `HFI_SkyMap_{857,100}_128_R2.00_*.fits`, from the git-LFS test data of `abeelen/hpproj`. The 100 GHz map is in K_CMB.
  Away from the Galactic plane it is dominated by the CMB anisotropy.
- **Gamma rays:** Fermi-LAT 3FHL event list (`fermi_3fhl_events_selected.fits.gz`, photons above 10 GeV, whole sky), binned
  and smoothed adaptively. Blazar positions and fluxes come from 4FGL-DR4 `gll_psc_v35.fit.gz`. Both are from
  `gammapy/gammapy-data`, licensed CC BY-NC-SA 4.0.
- `prep_maps.py` uses healpy and astropy, pip-installed into `SCR/pylib`, to turn all of these into galactic plate carrée
  textures (`SCR/maps.npz`).
- `ephem.py` (astropy, bundled IERS data) computes per frame, for Cape Town's latitude on **15 Jan 2026 at 07:30 local**, the Sun and Moon directions and the horizon → galactic rotation. The sky clock runs 30× real time, so the sky turns slowly.
  - The camera faces east and is aimed so the Moon sits at x = 630.
  - The Moon is a waning crescent 40° from the Sun and 10° from the Galactic Centre. A day later it sits right on it.
- `skymaps.py` projects the textures through a level pinhole camera that matches `lib.sky.SkyCam` (f = 480 px vertical, 300 px wide; the wide lens is shorter so the high Moon and its gamma orb stay in frame).

## Fact check
- **The claim:** NASA Goddard / Fermi release, 15 Aug 2019 ("Fermi sees the Moon in gamma rays", svs.gsfc.nasa.gov/13236). At gamma-ray energies above about 31 MeV, the Moon is brighter than the Sun.
- **Why the Moon glows:** cosmic rays hit the airless, unmagnetised lunar surface and make gamma rays. The glow has no phases, so the gamma Moon is drawn as a full disc while the visible Moon is a crescent.
- **Where it stops holding:** above about 1 GeV the Sun is brighter. The quiet Sun's magnetic field screens lower-energy cosmic rays.
- **How the Short phrases it:** the narration says "found the Moon outshines the Sun in gamma rays", and the on-screen card gives the energy cut ("ABOVE 31 MeV").

## Liberties and caveats
- **Stylised on purpose:** false-colour palettes, contrast boost, bloom and twinkle. Following the lead/user rule, there is no disclaimer text on screen. The maps' structure is real, but colours and brightness are art-directed.
- **Sizes are exaggerated:**
  - The visible and infrared Moon is drawn at 26 px radius; the real Moon would be about 2 px at this focal length.
  - The radio and microwave Sun discs are modest glows.
  - The gamma-ray Moon is a huge filled orb (100–142 px radius): a white-hot violet core, a mottled PSF-blurred edge, a centre-peaked bloom halo and a gentle pulse, roughly echoing Fermi's fuzzy gamma-ray Moon. The shock ring at "blazes" is a separate expanding ring.
- **Gamma energy mismatch:** the gamma-ray sky uses >10 GeV photons (3FHL), where the Sun would actually beat the Moon. The Moon and Sun brightness follow the >31 MeV statement instead.
  - The LAT exposure is not divided out; it is nearly uniform.
  - The photon "sparkles" are random draws weighted by the map.
- **Not in the data:** the gamma-ray burst position, the cosmic-ray streaks and the radio ripple rings are illustrative effects.
- **Infrared mixes two wavelengths:** the infrared beat combines a near-IR photo look (white foliage) with thermal effects (warm lamps and house, glowing air) and the far-IR Planck dust map.
- **The plate is a generic European park,** used under a South African sky.

## Files
- `audio/narration.py` and `audio/gen_voice.py`: Kokoro with word timings. The alignment merges only phoneme groups that really are fused, such as "of the".
- `audio/mix.py`: sound design, −14 LUFS / −1 dBTP, and the SRT.
- `prep_maps.py`, `ephem.py`, `skymaps.py`: data and geometry.
- `short.py`: picture. `encode.sh`: mux; it uses no `-shortest`. `thumbnail.py`.
- Shared code comes from `../lib/` (read-only). Scratch is `.../scratchpad/series/V3-gamma-ray-eyes/` (maps refetched 14 Nov: Haslam and Planck via media.githubusercontent.com LFS, sha256 matching the LFS pointers; Fermi files via raw.githubusercontent.com from gammapy-data master; healpy 1.20.1 + astropy 8.0.2 in SCR/pylib; ephem.npz written for 55 s). Outputs go to `out/` (git-ignored).

Pipeline: `prep_maps.py` → `ephem.py write` → `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `thumbnail.py vert` → `short.py wide` → `encode.sh wide` → `thumbnail.py wide`. Run the Python scripts with `/home/user/ttsenv/bin/python`. For `prep_maps.py` and `ephem.py`, also put `SCR/pylib` on the path.
