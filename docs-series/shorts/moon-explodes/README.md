# What If the Moon Exploded? (YouTube Short, batch 4)

The Short is vertical only: 1080×1920 at 30 fps, 43.54 s (measured on the final mp4: −14.4 LUFS, −2.0 dBTP, AAC 192k). It is one locked tripod shot of the user's
`03_calm_lake_wooden_pier.png` at night, made in the BATCH4 swap format. Every beat swaps in with a tinted flash and a
chromatic shockwave, and the pier and shore are relit for the new sky. Readouts sit at the top and big orange one-word
captions sit on the pier. There is no disclaimer small print, the sky stays deep blue (never black), and a white-out
returns to the Moon so the Short loops.

**The lake mirrors the sky.** `lake.py` is copied unchanged from `../more-moons/`: a GrabCut water mask, with the photo's
own tree and post reflections kept. Each frame, the rendered sky (Moon, fireball cloud, ring, meteors, stars) is mirrored
about the shoreline, with Fresnel-like reflectance, slight blur and small perspective ripples. The Moon sits low over the
far shore, right of the pier, so its reflection lands on open water.

## Beats
1. **Our Moon:** a full Moon at its true 0.52°.
2. **The blast:** a huge white-hot flash lights the lake and trees, followed by two chromatic shockwaves. The Moon glows
   and cracks along jagged lines, then breaks into 40 tumbling fragments with glowing orange rims. Around them,
   14,000 incandescent particles (orange-hot, each cooling to grey at its own rate) and a streaming dust and smoke cloud
   expand outward.
3. **The ring:** over "days", the debris spreads along the Moon's orbit into a wide, bright band. It rises out of the far
   trees and arcs up-left across the sky, with a glowing core, soft ringlets and gaps, clumps and a faint outer haze. The
   fragments grind down as they spread.
4. **The hard rain:** a rising stream of meteors radiating from the ring, peaking at about 22 a second. About a third are
   fireballs with long trains and fragmenting sparks, and these briefly light the scene. All of it is mirrored in the lake.
5. **Ring sky:** a brighter, settled ring that lights the scene a little, with a few meteors.
6. White-out, then our Moon again.

## Narration (74 words)
Voice: Kokoro 0.7 × am_michael + 0.3 × am_onyx at speed 0.86, one TTS call per phrase (`lib/b4_kit.generate`, i.e.
`lib/v3_kit.generate`). Pauses are 0.45–0.5 s between phrases and 1.1–1.2 s before reveals.
> What if the Moon... exploded? / There it is... calm over the lake. / Then... a flash. / It cracks... into glowing
> pieces. / Over days... the pieces spread along its orbit... / into a ring around Earth. / But some pieces fall. /
> Meteors streak across the sky... for years. / A hard rain. / And then... a bright ring... arcing over us... for ages. /
> No more eclipses... and gentler tides. / Look up tonight... / and be glad... it's still in one piece.

## Sound (BATCH4 clean rules)
`audio/mix.py` uses `lib/mix_clean` only, through `lib/b4_kit.make_mix`:
- `clean_voice(dry)`: no pitch shift, no echo or reverb.
- `mix(voice, dur, swaps=[5 swap times], key="D")`: the module's soft pad, plus its gentle whoosh at each swap
  (−26 dB re the voice peak since the 15 Nov module update).

Nothing else is added: no booms, rumbles, risers or impacts. The mix fades in over 30 ms and out over 0.35 s.

**Bed vs mix:** the pad + whoosh bed alone, with the voice muted, measures **24.1 dB** under the full mix (integrated
LUFS, measured before the shared normaliser). With the old module whoosh (−15 dB) it was only 9.9 dB, so the old version
was not used.

`encode.py` produces AAC 192k with soft subtitles and no `-shortest`. Loudness and true peak are measured on the final mp4.

## Science (`short.py info` prints the numbers)
- **Moon:** 3,474 km wide, 384,400 km away, 0.52°. Lens f = 22,400 px (the frame is ~2.8° wide), so r = 101 px, and every
  size stays true relative to it.
- **Energy:** to disperse the Moon, you must at least supply its gravitational binding energy. For a uniform sphere that is
  3GM²/5R = **1.24 × 10²⁹ J**. That equals all the sunlight Earth intercepts (1361 W/m² × πR⊕² = 1.74 × 10¹⁷ W) for
  **~22,700 years**, hence the readout "~22,000 YEARS OF EARTH'S SUNLIGHT".
- **Ring:** debris thrown off with a range of speeds ends up on slightly different orbits. Differential orbital periods
  shear the cloud along the Moon's path, so a band forms along the orbit, 2π × 384,400 km = **2.4 million km** around.
  This follows the general picture in popular-science treatments of the scenario (e.g. the *Science Focus* explainer
  "What would happen if we blew up the Moon?", the Rothery-style analysis cited in the brief): most debris stays in orbit
  as a ring, and some falls to Earth. I could not re-fetch that page here (the site is blocked from this sandbox), so the
  wording stays general.
- **Meteors:** debris that falls onto Earth enters at least at Earth's escape speed, **~11 km/s**, which is slower than
  typical asteroid impacts. "For years" is the narration's hedge. In Neal Stephenson's novel *Seveneves* the "Hard Rain"
  lasts thousands of years and sterilises the surface: that is fiction, and the Short only borrows the phrase.
- **Ring sky:** without a single Moon there are no more solar or lunar eclipses. Tides: a ring spread evenly around the
  orbit raises no moving tidal bulge, so only the Sun's tide (~46 % of the Moon's) remains. Spring tides drop from 1 + 0.46
  to 0.46 of today's lunar tide, or **~1/3** of today's spring range, hence the readout "TIDES ~1/3 AS HIGH".
- **"For ages", not "forever":** the brief said "forever", but the narration says "for ages". The ring sits far outside
  Earth's Roche limit (~18,000 km for lunar rock), so over long times collisions and self-gravity could gather much of it
  back into new moonlets. It is not permanent.

## Liberties (not captioned, per the user rule)
- The telephoto framing and time compression: "days" of spreading take ~5 s, and "years" of meteors take ~8 s.
- The blast picture is stylised: fragment count, glow colours, smoke streaks and the cooling rates are art direction. A
  real dispersal would also fling much debris out of Earth orbit.
- The ring is drawn as a gently curved arc. A ring at the Moon's distance would look almost like a great circle (a near-
  straight band in a rectilinear lens). Its width, ringlets and gaps are illustrative.
- The meteor rate is far beyond any real shower, so that the beat reads on a phone.
- The fragments "grind down" (shrink) as they spread, standing in for collisional grinding.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (clean mix + SRT).
- `short.py` (picture; `info`, `stills`, `segs`), `lake.py` and `moons.py` (copied unchanged from `../more-moons/`).
- `encode.py`, `thumbnail.py`.
- Scratch: `.../scratchpad/series/B4-moon-explodes/`.
- Outputs (`out/`, git-ignored): `moon-explodes-short.mp4`, `moon-explodes.srt`, `thumb-vertical.jpg`, `thumb.jpg`.
- Sources: the Moon is Solar System Scope `8k_moon` (CC BY 4.0). The foreground is the user's photo.
