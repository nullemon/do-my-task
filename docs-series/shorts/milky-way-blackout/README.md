# In 1994, People Called 911 About a Strange Cloud. It Was the Milky Way. (YouTube Short)

1080×1920, 30 fps, 37.23 s, plus a 16:9 recomposition. The style follows the lead's VFX direction (big, saturated, moving sky; see `../lib/README.md`). **Locked camera:** a single tripod frame of the user's city
plate (`C_city.png`, upscaled 941×1672 → 1080×1920) for the whole Short. There are no cutaways and no punch-ins. The
only camera motion is about 1.4 s of tripod rattle during the earthquake itself. Everything else happens in the sky and
in the city lights.

## Narration (Kokoro am_michael @ 1.05, real word timings)
> In 1994, people in Los Angeles reportedly called for help, because of something in the sky. Before dawn, the
> Northridge earthquake hit. And much of the city went dark. Then they looked up. According to astronomers at Griffith
> Observatory, people called about the strange sky. Some reportedly described a silver cloud. It was the Milky Way.
> They'd never seen it. Today, nearly 80% of North Americans can't see it from home. It's still there. Every night.
> Right above you.

## Beats
| t (s) | picture / sound |
|---|---|
| 0–9.5 | City at night under an orange sodium sky dome, with only the brightest stars showing. Mains hum, traffic, passing cars. Label: 17 JAN 1994 · 4:31 AM / NORTHRIDGE EARTHQUAKE · M6.7. |
| ≈9.5 | "hit": the tripod jolts for ~1.4 s. Rumble, sub thump, rattling glass. Brown-out flicker of the lights and of the whole frame. 120 Hz crackling buzz. |
| 10.2–11.9 | Three blue-green transformer flashes on the skyline, each with an arc zap and a boom. About 1,240 detected windows spark and switch off one by one in 4 block waves. The 5 street lamps buzz, flicker and die with a pop, and their warm light leaves the trees and road. The hum powers down to silence. |
| 12–14 | The orange dome drains down into the horizon. The grade turns deep blue (it stays readable and never goes black). Crickets and wind come in. |
| 13.5–17 | Stars, then a huge, vivid Milky Way: gold/pink core between the towers, teal/violet arms, a dust rift, a green airglow band and strong bloom. A meteor, a low hit, shimmer, and a swelling pad (D → Bm → G → A → D). The sky turns slowly the whole time and the stars twinkle. Two more meteors follow later. |
| 17–33 | AS RECOUNTED BY GRIFFITH OBSERVATORY, then the Falchi et al. fact block. |
| 33.6–37.2 | "Right above you": the windows and lamps come back in waves and the hum powers up. The orange glow climbs from the horizon and eats the Milky Way. The last frame matches the first, so the video loops. |

## Sources and how the facts are phrased
- **Northridge earthquake:** 17 Jan 1994, 4:30:55 a.m. PST, Mw 6.7. It caused widespread power outages across Los
  Angeles.
- **The calls:** Griffith Observatory staff, including then-director E. C. Krupp, have recounted calls from residents
  about the unfamiliar sky after the quake knocked out the power. The "silver cloud" wording and the "911" detail
  appear in popular retellings, for example one attributed to Terence Dickinson's *NightWatch* and many web posts.
  They are weaker than the observatory account. So the narration says "reportedly" twice, attributes the calls to
  Griffith astronomers, and gives no call counts. (Search, Nov 2026: Medium/Timeline "During a 1994 blackout, L.A.
  residents called 911…", NPS "Connect with the Galaxy", Discover "For our own good, let there be dark".)
- **Light pollution:** Falchi F. et al. (2016), "The new world atlas of artificial night sky brightness",
  *Science Advances* 2:e1600377. The reported finding is that the Milky Way is hidden from more than one third of
  humanity, including nearly 80% of North Americans and 60% of Europeans. The atlas also says that more than 80% of
  the world's population lives under light-polluted skies. That is a different statistic, and it is not used here.

## Liberties and caveats
- **The sky is stylised on purpose** (lead/user direction: saturated colours, no disclaimer text on screen). The bright stars and colours come from `lib/sky.StarSky`. The Milky Way
  band is this folder's `mw.py`, built in frame coordinates because the lib plate filled the whole frame at this
  framing; `vivid=True` adds the stylised palette. In reality, at 4:31 a.m. on 17 January from LA, the galactic core sits below the horizon (the Sun is in
  Sagittarius). What people saw was the fainter winter/spring Milky Way, lying low. The Moon had set (waxing crescent),
  so a moonless sky is right.
- **The plate is not Los Angeles.** It is the user's European-looking city photo, used as a stand-in.
- **Time compression.** Dark adaptation takes about 2 s on screen versus minutes in reality. The lights also return
  much faster than they did in reality.
- **The thumbnail text "THEY CALLED 911"** follows the requested title. The 911 detail is the folklore version.

## Files
`audio/narration.py` (text), `audio/gen_voice.py` (Kokoro with word timings; it wraps `lib.voice` and fixes
alignment for function words that Kokoro fuses, such as "in the" → "ɪnðə"), `audio/mix.py` (sound design, −14 LUFS,
SRT), `short.py` (picture: `City` light decomposition and `Scene`), `mw.py` (Milky Way), `encode.sh` (mux),
`thumbnail.py`. `encode.sh` muxes without `-shortest`, because with a subtitle stream that flag cut the file at the last cue (36.0 s instead of 37.2 s). `sun-black-hole/encode.sh` has the same pattern. Shared code: `../lib/` (read-only). Scratch:
`.../scratchpad/series/S2-milky-way-blackout/`. Outputs: `out/` (git-ignored).

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `thumbnail.py vert` →
`short.py wide` → `encode.sh wide` → `thumbnail.py wide`.
