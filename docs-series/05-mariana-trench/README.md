# 05 — FALLING INTO THE MARIANA TRENCH

5:52 narrated documentary short (1920×1080, 24 fps, 352.0 s). One continuous fall from the surface of the western Pacific
to the floor of Challenger Deep, with a live HUD (depth, pressure, water temperature, sunlight) and a 0–11 km depth gauge.
Sunlight fading to black is the visual spine; bioluminescence is the beauty; the ending replaces the outdated
"more people have walked on the Moon" line with an accurate comparison.

Script, locked timings and shot list: [`SCRIPT.md`](SCRIPT.md).

## Deliverables (`out/`, gitignored)
- `mariana-trench-1080p.mp4` — master: x264 CRF 18 (preset medium, tune film), AAC 256 kb/s, +faststart, soft English subtitle track. **424 MB**, 352.0 s.
- `mariana-trench-1080p-hq.mp4` — same picture, CRF 18 capped at 8 Mb/s (for chat delivery). **361 MB**.
- `mariana-trench-4k.mp4` — **3840×2160 lanczos UPSCALE of the 1080p render** (not native 4K detail), CRF 20, preset ultrafast (the shared CPU was at load ≈ 30; hence the large file). **2.36 GB**.
- `mariana-trench-4k-share.mp4` — the same upscale, capped at 10 Mb/s. **453 MB**.

Audio: −14.1 LUFS integrated, LRA 3.1 LU, true peak −1.8 dBTP (measured with ebur128 on the final AAC).
- `mariana-trench.srt` — subtitles generated from the real placed narration timings.

## Pipeline
| step | file | notes |
|---|---|---|
| narration | `audio/narration.py` | 44 lines, 703 words. Years spelled for TTS; "Trieste" fixed at phoneme level (tree-EST), Nitsch → "Nitch", Piccard → "Pickard". |
| voice | `audio/gen_voice.py` | Kokoro-82M v1.0 (kokoro-onnx), voice **am_michael**, speed 0.94 (series voice). |
| timeline lock | `audio/timeline.py` → `audio/placement.json` | line start = previous end + scripted pause × 0.995; last word ends 343.5 s. The camera depth is a monotone (PCHIP) curve through keys "depth X at the start of line N", so every depth is on screen when it is named. Nothing is time-stretched. |
| Blender assets | `deep3d.py`, `render_plates.sh` | bpy 5.1.2, Cycles CPU. Floor plates: a 1M-vertex numpy heightfield (fbm relief, burrow mounds with pits, dimpled trails, small debris), ooze material with fine bump, lit only by two spot lamps (our "lander"), 2880×1620, 24 spp. Vessel sprites: stylised low-detail models of Trieste, Deepsea Challenger and Limiting Factor (proportions only), orthographic ¾ view, rim + own lamps, transparent RGBA, 16 spp + OIDN. |
| compositor | `common.py`, `creatures.py`, `descent.py`, `run_queue.sh` | python3 + numpy + PIL, linear light, piped straight into x264 per 24 s segment (crf 14). |
| audio | `audio/mix.py` | voice chain (70 Hz HPF, EQ, 3:1 comp, small room), surface wash, splash + bubbles, depth-driven underwater rumble (gets lower/heavier with depth), sparse hadal groans, sperm-whale clicks, glassy chimes on bioluminescence, floor thump, lamp click; numpy pad bed that descends from airy D to low drones and is progressively low-passed with depth; 8 dB sidechain ducking; 2-pass loudnorm → −14 LUFS, limiter. |
| final | `assemble.sh` (+ `assemble4k.sh`, the 4K half, run in parallel) | concat segments (stream copy) → vignette + fine temporal grain → mux audio + mov_text subtitles → 1080p / hq / 4K / 4K-share. |

### How the picture works
- **Water colour** = surface colour × per-channel exponential attenuation (red 6 m, green 95 m, blue 175 m e-folding —
  display constants, chosen so red goes in the first tens of metres and the frame is black-blue by ~1,000 m), brighter
  towards the top (light from above) until ~1 km; god-rays (angular noise around a vanishing point above frame) to ~300 m.
- **Over/under opening**: sky gradient + sun + drifting cloud noise, a strip of sea with a glitter path, a wobbling waterline with
  meniscus, and the bright rippled underside of the surface; the waterline rises out of frame as the camera sinks.
- **Marine snow**: 3,400 world particles with depth-of-field (near ones are soft discs at ¼ resolution), motion-streaked by the
  fall speed (screen speed ∝ v^0.35, compressed so 270 m/s plunges stay readable). 12 % of them are bioluminescent and flash
  (fewer below 4 km). Our lamp lights the snow and leaves a faint scattering haze.
- **Creatures** (`creatures.py`): original, simplified designs built from a spine curve + width profile and drawn as supersampled
  polygons, animated (body waves, fin flaps, pulsing lights): lanternfish school with ventral photophores, giant squid
  silhouette (fins first, arms and two long tentacles), Atolla jellyfish with a chasing blue ring, female ceratioid anglerfish lit by its
  esca, gulper eel with a pink tail organ, sperm whale traced by disturbed plankton sparks, dumbo octopus, hadal snailfish
  (pale, translucent, organs showing), amphipods.
- **Scale markers**: dashed lines with labels cross the frame (constant screen speed) at 40, 200, 253, 1,000, ≈2,035, 4,000,
  6,000, ≈6,960 and 8,336 m; line drawings for an 828 m supertall (its base passes us at 828 m), an 8,849 m mountain whose
  summit crosses at 2,086 m, and the Titanic bow on the seabed at 3,800 m.
- **HUD**: depth; absolute pressure from the UNESCO (Saunders–Fofonoff) depth–pressure relation at 11.4° N, inverted numerically;
  in-situ temperature from a typical tropical West-Pacific profile (29 °C surface, thermocline, ≈1.5 °C minimum near 4 km, slight
  adiabatic warming to ≈2.4 °C at the bottom); sunlight = 100 %·e^(−d/43.4 m) (1 % at ≈200 m, very clear ocean), shown as NONE below 1,000 m.

## Facts and sources (checked Nov 2026)
| claim | source / note |
|---|---|
| Challenger Deep ≈ 10,935 m (±6 m, 95 %), from 2020 submersible pressure-referenced data | Greenaway, Bongiovanni et al. 2021, *Deep-Sea Research I* (NOAA repository https://repository.library.noaa.gov/view/noaa/33477). Other recent estimates: 10,924 ± 15 m (2019 sonar), 10,925 ± 4 m (2020 loggers), 10,927 m (2023 Hakuho-maru re-analysis). On screen: "± ≈ 6 m … other recent surveys ≈ 10,920–10,935 m". |
| Pressure ≈ 1,100 times the surface; > 1 tonne per cm² | Popular sources quote 1,086 bar; the UNESCO depth–pressure formula gives ≈ 11,270 dbar gauge (≈ 1,128 bar absolute, ≈ 1,110 atm) at 10,935 m, so the film says "about eleven hundred times" and the HUD shows ≈ 1,129 bar. 1,100 bar ≈ 1,120 kgf/cm². Note in hedging: the commonly quoted 1,086 bar figure is lower than the oceanographic formula. |
| ≈ 1 atm per 10 m | standard (ρg ≈ 1.0 bar per 10 m). |
| Bottom water 1–4 °C; ≈ 2.4 °C in situ | Mariana Trench summaries (1–4 °C); in-situ hadal temperature rises slightly with depth by adiabatic compression. |
| Zones: epipelagic 0–200, mesopelagic 200–1,000, bathypelagic 1,000–4,000, abyssopelagic 4,000–6,000, hadal > 6,000 m; practically no sunlight below ~1,000 m | NOAA Ocean Service / standard oceanography. |
| Recreational scuba limit 40 m | PADI/recreational agencies (130 ft). |
| 253 m, Herbert Nitsch, 2012, no-limits (weighted sled) | Guinness lists 253.2 m (2012); AIDA's ratified no-limits record is his 214 m (2007) — hence "deepest a person has gone on a single breath", labelled NO-LIMITS, WEIGHTED SLED. |
| Lanternfish counter-illumination | ventral photophores matching downwelling light — standard (Myctophidae). |
| Giant squid first filmed in its deep habitat 2012, ≈ 630 m off Chichi-jima, Japan | Kubodera / NHK / Discovery expedition (Wetpixel report: filmed at 630 m, followed to 885 m). |
| Burj Khalifa 828 m | standard. |
| ≈ 3/4 of animals bioluminescent | Martini & Haddock 2017, *Sci. Rep.* 7:45750 — 76 % of observed animals, surface to 3,900 m off California. Hedged on screen. |
| Atolla "burglar alarm" | hypothesis (Widder) — said as "some scientists think". |
| Anglerfish lure = modified dorsal-fin spine (illicium) with luminous symbiotic bacteria in the esca | standard (ceratioid females). |
| Gulper eel: huge loose jaws, light organ at tail tip | standard (Eurypharynx pelecanoides; records 750–7,625 m, most 1,200–1,400 m). |
| Sperm whales dive ≈ 2 km to hunt squid | NHM: regularly 1,000–2,000 m; deepest instrument-measured 2,035 m (Watkins et al. 1993). |
| Everest 8,849 m → summit 2,086 m below the surface if it stood on the floor | 2020 China–Nepal survey 8,848.86 m; 10,935 − 8,849 = 2,086 m. |
| Titanic wreck ≈ 3,800 m | NOAA Ocean Exploration (3,800 m / 12,467 ft). 3,800 / 10,935 = 35 % ("a third of the way"). |
| Abyssal plains mostly 3–6 km deep | standard; worded "much of the deep ocean floor lies around here: four, five, six kilometres down". |
| Dumbo octopus seen to ≈ 6,957 m (Java Trench) | Jamieson & Vecchione 2020, *Marine Biodiversity*; NHM "What is a dumbo octopus?". |
| Hadal zone named after Hades; trenches = subduction; Pacific plate sinks beneath the Mariana plate | standard. |
| Deepest fish filmed: snailfish (Pseudoliparis juvenile) at 8,336 m, Izu–Ogasawara Trench, 2022 (announced April 2023) | Smithsonian / Yale e360 / ITV, UWA–Tokyo Univ. of Marine Science & Technology. |
| Fish limit ≈ 8,200–8,400 m (TMAO osmolyte) | Yancey et al. 2014, *PNAS*; said as "scientists think". |
| Trieste, 23 Jan 1960, Piccard & Walsh; outer window cracked on the way down; ~20 min on the bottom | US Navy NHHC H-Gram 041; USNI. |
| James Cameron solo, 26 Mar 2012 (52 years later) | EarthSky / National Geographic. |
| Vescovo from 28 Apr 2019 (Limiting Factor, ≈ 10,925–10,928 m reported), 15 visits by 12 Jul 2022, took others | Guinness World Records ("most visits to Challenger Deep"); Five Deeps Expedition / Triton. |
| Kathy Sullivan: first American woman to walk in space (1984); Challenger Deep 7 Jun 2020 | CNN / NOAA. |
| Moon: 12 moonwalkers (Apollo 11–17, 1969–1972) | NASA. |
| "More people have walked on the Moon than have been to Challenger Deep" — **no longer true** (the count passed 12 in June 2020) | Wikipedia list via EPFL Graph Search: 27 people by July 2022; China reports ≈ 27–32 people taken below 10,000 m by Fendouzhe (2021–2024 reports, Global Times / CAS / China Daily). Tallies differ in what they count, so the film says "dozens" and footnotes both figures with "counts vary". |
| ≈ 780 people have flown to space (2026) | whoisinspace.com tracker (781 as of April 2026); definitions vary — labelled so. |

## Honest limitations
- The camera's fall speed is compressed visually; the HUD always shows the real depth on our scripted descent (which is far faster than any submersible: real dives take ~4 hours down).
- Creature designs are stylised and scale/brightness are exaggerated so they read; the dumbo octopus, snailfish and amphipods are shown lit by an implied lamp (they are not bioluminescent). The giant squid and sperm whale are not drawn to a consistent physical scale with the distance cues.
- Vessels are simplified Blender models (overall proportions only), no people depicted.
- Burj Khalifa, Everest and Titanic are thin generic outline drawings for scale, not accurate profiles.
- Temperature HUD uses a representative profile, not a measured cast from the exact site.
- The film-wide pressure figure (≈ 1,100 bar) intentionally differs from the often quoted 1,086 bar (see table).
- 4K files are lanczos upscales of the 1080p render.
