# 04 — THE BIG BANG IS ON YOUR TV

Narrated, 1920×1080, 24 fps, **270.0 s** (4:30). Voice: Kokoro `am_michael`, speed 0.94 (series voice).
499 words of narration. The timeline is locked to the measured voice clips (`audio/timeline.py` →
`audio/placement.json`): each line starts after the previous one ends plus its scripted pause × 1.31.

Tone: nostalgic + mind-blowing. Hook (0.8 s): a glowing CRT in a dark room — "Some of this static is left over from the Big Bang."
Payoff: the TV is switched off, the last dot fades — "And we used to just change the channel."

## Narration (locked timings, seconds)
| time | shot | line |
|---|---|---|
|   0.80–  3.92 | room | Some of this static is left over from the Big Bang. |
|   6.80– 13.00 | room | If you grew up with an old television, you've seen it. Between the channels: a hissing, crawling snow. |
|  15.10– 22.91 | room | Most of it was made right here on Earth. Warm electronics inside the set. Distant transmitters. Even the Sun. |
|  24.74– 33.67 | room | But a tiny part of it, often quoted as about one percent, though it was never precisely measured, came from much, much farther away. |
|  35.76– 38.12 | push | It is the oldest light in the universe. |
|  42.31– 52.76 | fog | Go back nearly fourteen billion years. The young universe is a hot, dense fog of charged particles. Light can't travel far before it's scattered. |
|  54.59– 62.32 | fog | Then, about three hundred and eighty thousand years after the Big Bang, the fog cools to around three thousand degrees. |
|  63.89– 68.64 | fog | Electrons settle onto atoms. And for the first time, light breaks free. |
|  70.22– 77.09 | fog | The whole universe glows like the surface of a cool star: a dull orange light, everywhere at once. |
|  80.23– 86.69 | stretch | That light has been travelling ever since. And as space expanded, it stretched the light along with it. |
|  88.27– 98.30 | stretch | Orange became red. Red became infrared. The waves grew about a thousand times longer, until the glow was invisible: microwaves. |
| 100.14–107.87 | stretch | Today it is just two point seven degrees above absolute zero. And it reaches us from every direction in the sky. |
| 109.70–117.77 | stretch | Roughly four hundred of these ancient photons fill every cubic centimetre of space. Including the room you're sitting in. |
| 119.87–124.40 | stretch | An old TV antenna, tuned to nothing, catches a faint whisper of it. |
| 127.55–137.07 | horn | In 1964, at Bell Labs in New Jersey, Arno Penzias and Robert Wilson were testing a giant horn-shaped antenna. |
| 138.38–146.81 | horn | It had been built to catch faint signals from the first communication satellites. It was one of the quietest radio receivers on Earth. |
| 148.38–153.98 | horn | They found a faint hiss they couldn't get rid of. Day or night. Whichever way they pointed it. |
| 155.55–163.86 | horn | They even evicted a pair of nesting pigeons, and cleaned out what Penzias politely called "white dielectric material". |
| 165.69–174.68 | horn | The hiss remained. Nearby, at Princeton, physicists had been preparing to search for exactly this: the afterglow of a hot beginning. |
| 176.25–183.99 | horn | When their leader, Robert Dicke, heard about the Bell Labs hiss, he reportedly told his team: "Boys, we've been scooped." |
| 185.56–190.95 | horn | In 1978, Penzias and Wilson shared the Nobel Prize in Physics. |
| 194.09–200.63 | map | Since then, the COBE, WMAP and Planck spacecraft have mapped this glow across the whole sky. |
| 202.20–211.14 | map | It is almost perfectly smooth. Its tiny ripples, about one part in a hundred thousand, are the seeds of everything that came later. |
| 212.71–223.85 | map | The warmer and cooler spots trace places that were very slightly denser or thinner than average. Over billions of years, gravity pulled the denser places together. |
| 225.16–227.33 | map | Galaxies. Stars. Planets. Us. |
| 230.74–243.43 | return | Today, analog television is gone from most of the world. The United States switched off full-power analog broadcasts in 2009. The UK finished in 2012. |
| 245.00–250.53 | return | And with it, this little window to the beginning of time quietly disappeared from our homes. |
| 257.07–259.08 | end | The oldest light in the universe. |
| 260.92–263.00 | end | And we used to just change the channel. |

## Shot list
| shot | time (s) | picture | how it is made |
|---|---|---|---|
| R1 | 0–14.05 | Dark 1980s living room, moonlight through a window, old wood-veneer CRT glowing with snow, rabbit ears, armchair silhouette. Very slow push. | Blender plates (moonlight-only pass, TV-light-only pass, screen-UV pass) composited per frame in numpy: snow mapped onto the curved screen through the UV pass, room lit by `lit × screen brightness` (flicker), bloom. |
| R2 | 14.05–34.5 | Three-quarter medium on the set; caption "≈ 1% OF THE SNOW". | same, medium camera |
| PF | 34.5–78.35 | Push into the screen → full-frame CRT close-up (curved glass, scan lines, aperture grille appear) → the snow turns orange and dissolves into the hot plasma of the early universe: protons, electrons, photons scattering in an opaque glow → recombination: electrons settle onto protons, fog clears, photons fly straight → the whole universe glowing at ~3,000 K. | numpy: CRT model + particle simulation (photon random walk, electron capture) on a pre-baked periodic noise field |
| S1 | 78.35–100 | A light wave on a stretching grid of space: wavelength grows, colour goes orange → red → (infrared) invisible; dashed trace = microwaves. Live temperature (3,000 K → 2.7 K), stretch counter (×1 → ×1,101) and a log spectrum strip with the peak-wavelength marker (≈ 0.97 µm → 1.06 mm). | numpy (blackbody colour, Wien peak) |
| S2 | 100–109 | "From every direction": tiny Earth dot, wavefronts converging from a faint shell. | numpy |
| S3 | 109–119 | A rotating 1 cm cube with 411 jittering photons. | numpy |
| S4 | 119–125.7 | Back to the TV, drifting up to the rabbit ears. | room plates |
| H1 | 125.7–138 | Stylised horn-reflector antenna at blue hour, slow push (no people, simplified shape). | Blender still (4K) + 2D move |
| H2 | 138–148 | True 3D slow orbit around the horn. | Blender frames |
| H3 | 148–155.2 | Diagram: antenna pointing anywhere, day and night — the noise meter stays at ≈ 3.5 K. | PIL/numpy |
| H4 | 155.2–165.2 | The narrow end of the horn; two pigeon silhouettes leave. "WHITE DIELECTRIC MATERIAL". | Blender still + 2D silhouettes |
| H5 | 165.2–175.4 | Holmdel ↔ Princeton (≈ 40 km), the two 1965 letters. | numpy |
| H6 | 175.4–192.2 | Low angle under the stars; "Boys, we've been scooped" (as recalled); Nobel Prize 1978. | Blender still + 2D move |
| M | 192.2–228.7 | Rotating CMB sphere → all-sky Mollweide map (clearly labelled ARTIST'S IMPRESSION) → zoom into the hot and cold spots → points of light condense on the overdense regions: galaxies. "Us." | numpy: isotropic random field on the sphere (sum of plane waves on unit vectors), Planck-like colour map |
| G | 228.7–263.2 | The room again, slow pull back; US 2009 / UK 2012 captions; the click: picture collapses to a line, a dot, the dot fades; the room goes dark. Last two lines over the dark room. | room plates + CRT power-off model |
| T | 263.8–269.5 | Title card "THE BIG BANG IS ON YOUR TV", fade to black. | numpy text |
