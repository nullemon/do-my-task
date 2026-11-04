# 07 — MEGALODON TO SCALE

*An underwater size-comparison film that builds up to Otodus megalodon. Every animal is drawn at true relative
scale, alongside a 1.8 m diver.*

A 5:16 narrated documentary (1920×1080, 24 fps) in the series look: thin, widely spaced Inter Light caps, slow
camera, grain and vignette added at the final encode. An orthographic "long-lens" camera pulls back step by
step: diver → bull shark → great white → school bus → whale shark → orca → humpback → megalodon. Next comes the
honest part: what the fossils actually are, how the size estimates changed, and a ghosted range of possible sizes.
Then the twist (the blue whale, and Perucetus, which is contested). The film ends as the megalodon passes over the
diver into darkness.

## Files
| file | what |
|---|---|
| `SCRIPT.md` | locked narration with measured times + shot list + captions |
| `timeline.py` | locked timeline: voice starts, orthographic camera keys (frame width in metres), light level, every actor's path/lane/length |
| `blender/animals.py` | Blender 5.1.2 (bpy module, Cycles CPU). Procedural low-detail models built from numbers (depth/width profiles, fin outlines in body-length units, numpy-painted pattern textures). Each one renders a seamless swim-cycle loop through an orthographic side camera (tilted 12° to look up slightly from below) with a transparent film. Shading is emission only (top light + fill + rim from the normal): 6 spp, no bounces, no denoise |
| `comp.py` | numpy/PIL compositor. Ocean background (depth gradient, pre-baked god-ray textures, three parallax layers of marine snow, sprite shadows cast down through the light shafts, diver bubbles). It places sprites in metres (px/m = 1920 / W) and draws the overlays: labels, scale bar, bus outline, 141-centrum column, growth-band inset, tooth-vs-hand inset, fossil-record axis, uncertainty ghosts (dashed outlines), captions. Writes silent x264 CRF 14 segments |
| `render_all.sh` | renders the 16 × 20 s segments with 2 workers (resume-safe), then concats them into the joined master |
| `encode_one.sh` | one deliverable (`1080p` / `hq` / `4k` / `share`) from the joined master + mix + SRT (vignette + temporal grain here) |
| `audio/narration.py`, `audio/gen_voice.py` | narration text, Kokoro TTS (am_michael, speed 0.94, the series voice) |
| `audio/mix.py`, `audio/placement.json` | voice chain (HPF/EQ/compression/small room), numpy music bed (D minor drone + pads, deep ocean rumble, diver bubbles, distant whale moans, sub swells at the megalodon reveal, blue whale and final pass), ducking, two-pass loudnorm −14 LUFS, SRT |
| `megalodon-to-scale.srt` | subtitles from the real placed voice timings (also muxed as a soft track) |

Rebuild: `/home/user/bpyenv/bin/python -c "import sys; p='blender/animals.py'; sys.argv=['blender','--','all']; exec(compile(open(p).read(),p,'exec'))"`
→ `/home/user/ttsenv/bin/python audio/gen_voice.py && /home/user/ttsenv/bin/python audio/mix.py`
→ `bash render_all.sh` → `bash encode_one.sh 1080p|hq|4k|share`.

## Sizes drawn (metres, true relative scale)
| animal | drawn | what the narration/caption says |
|---|---|---|
| diver | 2.45 m incl. fins (1.8 m person) | ≈1.8 m tall |
| bull shark | 3.3 m | large females ≈3.5 m |
| great white | 6.0 m | adults 4–5 m; largest reliable ≈6 m (≈6.1 m verified female; 6.4 m claims unverified) |
| school bus | 12.0 m outline | ≈12 m (a long US Type D bus is 12–13.7 m) |
| whale shark | 12.0 m | big adults ≈12 m; largest reliable ≈18.8 m (partly an estimate) |
| orca | 8.0 m | large males ≈8 m (max reports ≈9.8 m) |
| humpback | 15.0 m | ≈15 m; flippers ≈⅓ of body length |
| megalodon, "as usually pictured" | 16.0 m, great-white proportions | older estimates 15 / 18 / 20 m (dashed ghosts) |
| megalodon, slender | 16.4 m (lemon-shark-like) | ≈16 m best-grounded individual; ghosts at 20 and 24.3 m (upper limit) |
| blue whale | 29.9 m | up to ≈30 m, well over 100 t |
| Perucetus colossus | 17 m ghost | 85–340 t proposed (2023) → 60–70 t (2024) |

## Facts and sources (verified with web search, Nov 2026)
- **What survives:** megalodon's skeleton was cartilage. It is known from teeth and from rare vertebral columns;
  only two Miocene columns are known, from Belgium and Denmark (Shimada et al. 2021, *Historical Biology*;
  PMC9385135).
- **Teeth:** the largest are ≈18 cm slant height (record ≈18.9 cm, Peru). Most are 10–13 cm. The film says
  "around eighteen centimetres, about the length of a human hand" (adult hand ≈18–19 cm).
- **Belgian column IRSNB P 9893:** 141 centra, 46 growth bands, so ≈46 years old at death (Shimada et al. 2021).
  The 2024 study put its vertebral column at ≈11.1 m (an earlier study had the whole animal at 9.2 m).
- **Body form:** Sternes, Shimada et al. 2024 (*Palaeontologia Electronica*, "White shark comparison reveals a
  slender body for the extinct megatooth shark") argue it was more slender than a scaled-up great white.
  Shimada et al. 2025 (*Palaeontologia Electronica* 28(1):a12, doi:10.26879/1502) find the body form likely
  resembled the lemon shark. They reconstruct the Belgian individual at ≈16.4 m (1.8 m head + 11.1 m trunk +
  3.6 m tail) and call **24.3 m** (from a 230 mm Danish centrum) the largest estimate the evidence can reasonably
  support. Their figures: ≈94 t at 24.3 m, cruising speed 2.1–3.5 km/h, birth size 3.6–3.9 m. The authors call
  many of these interpretations tentative, and the fin shapes and head shape remain unknown.
- **Older estimates:** a great white scaled up from tooth size gave maxima of roughly 15–20 m (e.g. Gottfried et
  al. 1996 ≈15.9 m; Pimiento & Balk 2015 up to ≈17.9 m; Perez et al. 2021 ≈20 m).
- **Age range:** ≈23 Ma (early Miocene) to ≈3.6 Ma (Boessenecker et al. 2019, *PeerJ*; the earlier figure was
  2.6 Ma). Some recent work starts its firm record later (≈16 Ma), so "about 23 million" is the commonly cited
  start, not a settled one.
- **Bite force:** Wroe et al. 2008 (*J. Zoology*) modelled 108,514–182,201 N (≈11–18 tonnes-force). The
  model scaled a great white and covers only jaw closing. It is shown and spoken as a model.
- **Warm-bloodedness:** Griffiths et al. 2023 (*PNAS* 120(27):e2218153120) used clumped-isotope thermometry of
  the teeth. Body ≈27 °C, about 7 °C above the surrounding water: regional endothermy, probably costly in energy.
- **Extinction (hypotheses, not settled):** a cooling climate and sea-level fall shrinking the shallow nurseries
  (Pimiento et al. 2010 found a Panama nursery); changes in marine-mammal prey; and competition with the great
  white. McCormack et al. 2022 (*Nat. Commun.* 13:2980) found zinc isotopes show overlapping trophic levels in
  the early Pliocene, which the authors present as consistent with competition, cautiously.
- **Not alive:** no fossils are younger than ≈3.6 Ma. Its pups grew up in shallow coastal water, and a large,
  warm-bodied coastal-nursing predator could not hide. Discovery's 2013 "Megalodon: The Monster Shark Lives" was
  fiction with a brief disclaimer.
- **Blue whale:** the largest reliably measured is ≈29.9 m (98 ft, 1947). The 33.6 m figures come from older
  conversions. The heaviest weighed ≈190 t (a 1947 figure that mixes units in some sources), so the film says
  "well over a hundred tonnes".
- **Perucetus colossus:** Bianucci et al. 2023 (*Nature*), Peru, ≈39 Ma, estimated 85–340 t (central ≈180 t).
  Motani & Pyenson 2024 (*PeerJ*) revised that to ≈60–70 t at 17 m (≈110 t even at 20 m), below the largest
  blue whales. The animal is known from a partial postcranial skeleton only, so its shape in the film is a ghost
  and conjectural.
- Whale shark ≈18.8 m record; great white ≈6.1 m verified; humpback flippers ≈⅓ of body length (NOAA PMEL);
  orca males ≈6–8 m typical.

## Honesty notes / simplifications
- **Shapes are schematic.** Megalodon's fins, head and colouring are unknown. The slender model follows the
  lemon-shark-like interpretation (2025), and the "classic" model is the great-white model scaled to 16 m, which
  is exactly how the older reconstructions worked. Captions say "as it is often pictured", "schematic", and
  "body shape and fins remain unknown".
- **Holding position:** for the long megalodon analysis, the animals glide very slowly (≈0.1 m/s) instead of
  cruising past, so the comparison can be read. Speeds elsewhere are about 0.9–2 m/s, plausible but not claimed.
  The opening tease moves faster (≈2.4 m/s).
- **The 11.1 m column** is drawn from just behind the head. When it first appears, the body is still the
  great-white-proportioned one, and the morph that follows illustrates the 2024–25 argument.
- **Growth bands, tooth and hand insets** are diagrams. The tooth and hand are drawn at the same inset scale.
- **The camera** is orthographic and tilted 12° about the length axis. Horizontal lengths are exact, and vertical
  sizes are foreshortened by ≈2 %. Background rays and snow are screen-space effects. The vertical-light model
  is stylised.
- **4K files** are lanczos upscales of the 1080p render.
