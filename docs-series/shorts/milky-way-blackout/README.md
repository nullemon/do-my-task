# In 1994, People Called 911 About a Strange Cloud. It Was the Milky Way. (YouTube Short)

1080×1920, 30 fps, about 37.2 s, plus a 16:9 recomposition. **Locked camera:** a single tripod frame of the user's city
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
| 0–9 | City at night under an orange-grey sodium sky dome, with only the brightest stars showing. Mains hum, traffic, passing cars. Label: 17 JAN 1994 · 4:31 AM / NORTHRIDGE EARTHQUAKE · M6.7. |
| ≈9.5 | "hit": the tripod jolts for ~1.4 s. Low rumble, sub thump, rattling glass. Brown-out flicker and 120 Hz crackling buzz. |
| 10.2–11.9 | About 1,240 detected windows switch off individually in 4 block waves (far right → near left), each with a last-gasp flash. The 5 street lamps buzz, flicker and die with a transformer pop, and their warm light leaves the trees and road. The hum powers down. Then silence. |
| 12–14 | The skyglow drains over 2.2 s. The exposure adapts, the grade turns cool blue, and crickets and wind come in. |
| 13–17 | Stars appear, then the Milky Way rises: warm core low between the towers, a dust rift, star clouds, faint airglow. A low hit, shimmer, and a pad that swells (D → Bm → G → A → D). The city becomes silhouettes with a faint starlit rim, a residual distant glow on the horizon, and a few surviving battery and car lights. |
| 17–32 | Small text: AS RECOUNTED BY GRIFFITH OBSERVATORY. Then the Falchi et al. fact block. |
| 33–37 | "Right above you": the lamps and windows come back in waves, the hum powers up, the dome returns and the Milky Way drowns. The last frame matches the first, so the video loops. |

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
- **The sky is a procedural illustration.** The bright stars and colours come from `lib/sky.StarSky`. The Milky Way
  band is this folder's `mw.py`, built in frame coordinates because the lib plate filled the whole frame at this
  framing. In reality, at 4:31 a.m. on 17 January from LA, the galactic core sits below the horizon (the Sun is in
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
`thumbnail.py`. Shared code: `../lib/` (read-only). Scratch:
`.../scratchpad/series/S2-milky-way-blackout/`. Outputs: `out/` (git-ignored).

Pipeline: `audio/gen_voice.py` → `audio/mix.py` → `short.py vert` → `encode.sh vert` → `thumbnail.py vert` →
`short.py wide` → `encode.sh wide` → `thumbnail.py wide`.
