# What If You Could See Dark Matter? (YouTube Short, 9:16 only, BATCH4)

The Short is 1080×1920 at 30 fps and about 44.0 s long. It uses the BATCH3/4 swap format: one **locked** shot of the user's
`07_mountain_observatory.png` at night. The real sky (HYG v4.1 stars with V < 6.5 at 34° N, plus the Milky Way band from
galaxy-address/star-dates) stays in place, and at each swap another dark-matter layer is revealed. Each swap has a tinted
flash, a chromatic shockwave that reveals the new layer inside its ring, soft beams, a relit summit (purple light) and a
readout at the top. Captions are big orange words. The base night sky is a deep blue-black (never pitch black). A
white-out returns to the normal sky, and the sidereal drift is re-based so the Short loops. There is no disclaimer small
print.

## Narration (75 words, about 42.4 s of speech)
The voice is Kokoro 0.7 am_michael + 0.3 am_onyx at speed 0.86, one TTS call per phrase, with real word timings
(`audio/gen_voice.py`, the galaxy-address wrapper of `lib/voice.py`). Pauses are 0.45–0.5 s between phrases and 1.15 s
before each reveal.
> What if you could see... dark matter? / Tonight... just the Milky Way. / Now... a ghostly glow swallows the galaxy. /
> Five times more of it... than all the atoms in the universe. / And it's lumpy. / Thousands of dark clumps... drifting
> around us. / And then... the cosmic web. / Giant threads... stretching across the whole sky. / The strangest part? /
> It's flowing through you... right now. / Maybe billions of particles... every second. / Blink... / It's gone. But it
> never left.

## Sound (BATCH4 clean-audio rules)
- `audio/mix.py` uses **only** `lib/mix_clean.py`: `clean_voice(dry)`, then `mix(voice, DUR, swaps=[the five swap
  times], key="D")`. The only extras are the module's soft pad and its gentle whoosh at the swaps. There are no other
  sounds, and no pitch shift, echo or reverb. The only post-processing is a 0.4 s fade-out and a 30 ms fade-in to avoid
  clicks.
- Listen-check by measurement (`SCR/audio/bed_check.txt`): the pad + whoosh bed alone (voice muted) is **−24.9 dB**
  below the full mix (integrated LUFS on mix_clean's own stems and gains, before the common loudnorm). This uses the
  15 Nov mix_clean (fftconvolve ducking, whoosh −26 dB).
- The mix is −14.2 LUFS and −2.0 dBTP. The encode is AAC 192k; the final mp4 is measured by `encode.sh` (values in the
  delivery message).

## Beats and numbers (verified)
| beat | how it's made | readout |
|---|---|---|
| **Tonight** | HYG v4.1 stars and the Milky Way band (neutral, star-white grade), stereographic lens f = 540 px, centre alt 60° facing south (`skygeo.py`, `mwsky.py`, `catalog.py` from galaxy-address) | Milky Way: 100–400 billion stars (the usual range of estimates); plus gas and dust; all of it normal matter |
| **Halo** (swap on "ghostly") | `prep.py`: line-of-sight column of an **NFW halo** (r_s = 20 kpc, flattening q = 0.9) seen from the Sun at R0 = 8.2 kpc, integrated to 250 kpc. It is brightest towards the galactic centre (17.8× the anticentre). Rendered as a violet core, cyan outer veil and lavender-white centre, with slowly flowing ridged 3-D wisps and a soft edge 42° from the GC | ~1 trillion Suns of mass (MW halo ~1–1.5 × 10¹² M☉); over a million light-years across (virial radius ~200–290 kpc, i.e. a diameter of 1.3–1.9 Mly); dark : normal matter ≈ 5.4 : 1 (Planck 2018: Ω_c h² = 0.120, Ω_b h² = 0.0224 → 5.36) |
| **Subhalos** (on "lumpy") | 420 small cores with power-law sizes, one big clump at the Sagittarius dwarf (l = 5.6°, b = −14.2°), and 40 big soft clumps drifting slowly across the sky | Thousands in simulations (Aquarius / Via Lactea resolve tens of thousands); ~60 known satellite galaxies of the Milky Way live in them; most small subhalos are predicted to hold no stars at all |
| **Cosmic web** (on "cosmic") | `prep.py build_web`: a graph of ~116 cluster knots (most grouped into superclusters), linked to their nearest neighbours by filaments. The filaments are thick near the knots and taper in between, are bent by a domain warp, and have short side branches. Each has a broad faint "sheet" glow, the voids between are empty, galaxies speckle the threads, and there are two depth layers (near: thick violet-white; far: thin cyan-blue) | Filaments hundreds of millions of ly long; ~85 % of all matter is dark (0.120 / 0.1424 = 0.84); galaxies grow where threads meet |
| **Wind** (on "flowing") | 2,600 particles in a periodic box flowing at us from **Cygnus** (l = 90°, b = 0, the direction of the Sun's orbit), with a small dispersion and a gentle common curl. Each streak is a curved 4-point polyline with a soft glow. Purple glints flicker on the summit | ~230 km/s, blowing from Cygnus (the Sun's orbital speed is ~230–240 km/s); ~1 proton mass in every 3 cm³ (local density ~0.3 GeV/cm³; m_p = 0.938 GeV); if WIMPs: ~1 billion per second through you |

**WIMP flux estimate:** ρ = 0.3–0.4 GeV/cm³ and m = 50–100 GeV give n ≈ 0.003–0.008 cm⁻³. With a mean relative speed of
~300 km/s, the flux is ~10⁵ cm⁻² s⁻¹. Over a body cross-section of ~0.6–0.7 m², that is ~6 × 10⁸ to 2 × 10⁹ per
second, so "~1 billion" and "maybe billions". It depends on the particle: for axions the number would be vastly larger,
and for very heavy candidates much smaller. Hence "maybe" in the script and "if WIMPs" on screen.

## Liberties (deliberately not captioned)
- Dark matter emits no light; the whole Short is a "what if you could see it" visualisation. The colours, the glow
  brightness and the purple light on the summit are invented.
- **Halo edge:** an observer inside an NFW halo would see no edge. The soft boundary 42° from the GC (where the line of
  sight leaves the dense inner halo) is drawn as a visual aid, and the column is compressed perceptually.
- **"Five times":** this is the cosmic ratio (5.4 : 1). Inside the Milky Way's halo, dark matter outweighs the stars and
  gas roughly 10–20 to 1.
- **Subhalo** positions and sizes are random apart from the Sagittarius dwarf, and their drift is sped up.
- **Cosmic web:** a stylised network "à la" Millennium/Illustris, not a map of the real local web (the Local Sheet,
  Laniakea). In reality the filaments are tens to hundreds of Mpc away and would overlap in depth.
- **Wind:** individual particles can't be seen; the streak density, speed and curl are stylised. The Cygnus apex and the
  speed are real.
- The sidereal drift is a stylised time-lapse (0.05 h of LST per second). The flashes, shockwaves and beams are VFX.

## Sources
- Planck Collaboration 2018 VI (Ω_c h², Ω_b h²); Navarro, Frenk & White 1997 (NFW profile); MW halo mass and virial
  radius: e.g. Wang et al. 2020 review (~1–1.5 × 10¹² M☉); local DM density ~0.3–0.4 GeV/cm³ (Read 2014; de Salas & Widmark
  2021); MW satellites: Drlica-Wagner et al. 2020; Springel et al. 2008 (Aquarius), Diemand et al. 2008 (Via Lactea II).
- Star positions: HYG v4.1 (astronexus/HYG-Database), CC BY-SA 4.0. Credit line: *Star positions: HYG Database
  (CC BY-SA 4.0). Dark matter: digital visualisation.*

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (mix_clean only, the bed check and the SRT).
- `catalog.py`, `skygeo.py`, `mwsky.py` (from galaxy-address), `prep.py` (dark-matter canvases → `SCR/dm.npz`).
- `short.py` (`info`, `stills t,t`, and `seg` for the restart-safe segment render), `encode.sh` (mux, AAC 192k, no
  `-shortest`, prints loudness), `thumbnail.py`.
- Scratch: `scratchpad/series/B4-dark-matter-visible/` (HYG CSV in `B4-common/dl/`).
- Outputs (git-ignored): `out/dark-matter-visible-short.mp4`, `out/dark-matter-visible.srt`, `out/thumb-vertical.jpg`,
  `out/thumb.jpg`.
