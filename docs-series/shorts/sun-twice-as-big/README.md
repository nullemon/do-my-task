# What If the Sun Were Bigger? (YouTube Short, 9:16 only, BATCH4)

The Short is 1080×1920 at 30 fps and about 44.6 s long. It uses the BATCH3/4 swap format: one **locked** shot of the
user's `A_park.png`. The Sun stays at 1 au and **keeps its surface temperature** (5,772 K); only its radius grows, through
1× → 2× → 5× → 10×. Each swap has a flash and a chromatic shockwave, the old Sun swells and implodes, and the new one
blooms in. The park is relit, and a readout sits at the top. A faint dashed ring marks today's Sun size for comparison.
Captions are big orange words. A white-out returns to today's Sun, so the Short loops. There is no disclaimer small
print.

## Narration (72 words, about 43.3 s of speech)
The voice is Kokoro 0.7 am_michael + 0.3 am_onyx at speed 0.86, one TTS call per phrase, with real word timings. Pauses
are 0.45–0.5 s between phrases and 1.15 s before each reveal.
> Imagine the Sun... growing bigger. / Just as hot... only wider. / First... twice as wide. / Already... more light than
> Venus gets. / The sky turns white... / and every shadow turns sharp. / Now... twenty-five times the light. / The grass
> turns brown... / and starts to steam. / And then... a hundred times the light. / The air shimmers... / and the
> oceans... boil away. / Earth... becomes another Venus. / Back to normal... / Our Sun isn't too small. / It's just right.

## Sound (BATCH4 clean-audio rules)
`audio/mix.py` uses **only** `lib/mix_clean.py`: `clean_voice`, then `mix(..., swaps=[the 4 swap times], key="A")`.
That is the soft pad plus the gentle whoosh at the swaps, nothing else: no echo, reverb or pitch shift, and only click-free
0.4 s / 30 ms fades. The bed alone (voice muted) is **−25.4 dB** below the full mix (`SCR/audio/bed_check.txt`, on
mix_clean's stems, 15 Nov version). The mix is −14.3 LUFS and −2.0 dBTP. AAC is 192k; the final mp4 values are in the
delivery message.

## The physics (verified)
- **Angular size** at 1 au: θ = 2·asin(R/1 au), with R☉/1 au = 0.00465. That gives 1× = 0.533°, **2× = 1.066°,
  5× = 2.665°, 10× = 5.331°** (the readouts say 1.07°, 2.67°, 5.33°). The lens is f = 3,400 px (a 31.5° vertical field
  of view), applied identically to all beats, so the sizes are true relative to the park: 16, 32, 79 and 158 px radius.
- **Light:** L = 4πR²σT⁴ at fixed T, so L ∝ R², giving **4×, 25×, 100×**.
- **Venus** receives 1.91× Earth's sunlight (0.723 au), so 4× is already "more than Venus gets".
- **~25 kW per m²:** clear-sky noon irradiance at the ground today is ~1 kW/m², and 25× that is ~25 kW/m².
- **Earth ≥ 500 °C at 10×:** the equilibrium temperature scales as L^¼: 255 K × 100^¼ = 806 K ≈ 533 °C, before any
  greenhouse effect, so "≥ 500 °C". At 5× it is 570 K ≈ 300 °C, and at 2× it is 361 K ≈ 88 °C.
- **"The oceans boil away... another Venus":** above roughly 1.1–1.4× today's sunlight, models give a runaway (or moist)
  greenhouse: the oceans evaporate and Earth ends up Venus-like (Kasting 1988; Kopparapu et al. 2013).

## Liberties (deliberately not captioned)
- **Escalation is staged.** Physically, the oceans would already start boiling away at 2× (4× the light, more than Venus
  gets). The Short shows a visual escalation per beat (bleached sky and hard shadows → browning grass and steam → scorched
  ground and boiling oceans). The 2× line hints at this ("more light than Venus gets").
- **Instant effects:** the browning, scorching, steam and shimmer happen within seconds rather than days to years.
- **Exposure:** the camera exposure is pulled down at each step (as a real camera would), so the scene reads as bleached
  rather than pure white. The sky turning white-hot near the Sun is a stylised view of the glare.
- The beams, spikes, corona streamers, shockwaves, implosions and the dashed comparison ring are VFX. The park plate is
  used unchanged with a long lens, so the camera's field of view is a framing choice.
- The Sun's surface (granulation, supergranulation, spots and prominences) is procedural (from sun-closer/other-suns) and
  its features are not to scale.

## Files
- `audio/narration.py`, `audio/gen_voice.py`, `audio/mix.py` (mix_clean only, the bed check and the SRT).
- `short.py` (`info`, `stills t,t`, and `seg` for the restart-safe segment render), `encode.sh` (mux, AAC 192k, no
  `-shortest`, prints loudness), `thumbnail.py`.
- Scratch: `scratchpad/series/B4-sun-twice-as-big/`.
- Outputs (git-ignored): `out/sun-twice-as-big-short.mp4`, `out/sun-twice-as-big.srt`, `out/thumb-vertical.jpg`, `out/thumb.jpg`.
