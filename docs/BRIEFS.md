# Six planet-gravity video formats — production briefs

Gravity (m/s²): Pluto 0.62 · Moon 1.62 · Mars 3.71 · Earth 9.81 · Jupiter 24.79 · Sun 274 (Neptune 11.15 for quiz bonus)

## Shared rules (apply to every script)
- One self-contained Blender Python script for Blender 4.2–5.x, no downloaded assets, everything procedural. Run from Scripting tab ▶, or headless: `blender -b -P script.py -- --render`.
- CONFIG block at top: planets, fps, duration, resolution, engine (Eevee by default), quality, PREVIEW/RENDER flags, output folder.
- Vertical 1080×1920 @ 30 fps. Big readable label in top third (e.g. `MOON · 1.62 m/s²`) and hook caption in first 2 s. Text readable on bright scenes like the Sun (dark plate behind text, toned-down glow).
- Physics: real gravity values. Bake simulations so playback is deterministic. Very high gravity (Sun) needs more substeps / solver iterations so nothing tunnels or explodes.
- Verification: the script prints the measured outcome and it must match the brief. README says what's real vs faked and gives expected render time.
- Planet looks: Pluto pale ice/dark sky · Moon grey/black sky · Mars rust/butterscotch sky · Earth green & blue · Jupiter tan & orange haze · Sun glowing orange ground.
- Scene gravity is one global value; it can be animated (solver follows keyed scene.gravity during bake). Different gravity in different places at once needs zone force fields (briefs 1, 2).

## 1. Planet Marble League (75 s)
Marble race on a track through planet zones; gravity changes under each marble as it crosses zones. Hook 0–2 s: 8 coloured numbered marbles on gate, "PICK YOUR MARBLE 👇", 3-2-1 countdown.
Beats: 0–3 s Start, gate drops, "AND THEY'RE OFF". 3–15 Earth: normal, pack bunches, chicane bumping. 15–30 Moon: small jumps become floaty arcs, wide turn makes leader drift, order shuffles. 30–42 Jupiter: banked hairpin, anyone too fast jumps the wall "❌ OUT". 42–60 Pluto: gap jump near slow motion (~1.8 s hang per metre drop). 60–68 Sun: straight sprint, marbles glued, speed readout. 68–75 Finish: photo finish slow-mo replay, podium 🥇🥈🥉 + standings table, "Next race: Mars Canyon. Pick again 👇".
Numbers: free fall from 1 m: Pluto 1.8 s, Moon 1.1 s, Earth 0.45 s, Jupiter 0.28 s, Sun 0.09 s. Max corner speed ∝ √(μ·g·r): Jupiter ~1.6× Earth, Moon ~0.4× Earth.
Build: spline track pieces (Curve→bevel→mesh) with walls as passive rigid bodies; coloured floor strip + zone arch with label per zone. 8 spheres (r 2.5–4 cm; may scale ×10 for Bullet stability keeping gravity ratios), glass/metal/paint materials with number decal. Per-zone gravity: scene gravity 0, per-zone downward force fields bounded to zone (or fallback per-frame handler / analytic). Prototype 2 zones first. Seeded start order + tiny nudges. Bake, read finishing order from cache → podium. Camera follows leader (smoothed), replay cutaways. Live position tower, commentator captions.
Title: "Marble race through every planet 🪐 Pick yours!"

## 2. Split World (30–40 s)
One locked-off shot split by glowing seam at x=0: left Moon, right Jupiter, each with own gravity. Hook: kitchen table split by seam, "LEFT: MOON · RIGHT: JUPITER", glass of water on the line.
Beats: 0–5 s hand pours water left→right; left stream arcs slow blobs, crosses seam and slams/splashes. 5–12 ball rolls left→right; falls off edge in 0.28 s on Jupiter vs 1.1 s on Moon from 1 m. 12–20 deck of cards thrown across seam; left flutters, right drops. 20–30 long pendulum swings across seam, slow left / fast right; then seam slides sideways and Jupiter eats the frame, everything crashes. End: "Which side would you live on? 👇".
Numbers: 1 m fall Moon 1.11 s, Jupiter 0.28 s (~4×). Pendulum half on each side = average of the two half-periods (show timer).
Build: scene gravity 0 + two box-limited downward force fields meeting at seam; rigid bodies (ball, cards, hinge pendulum). Water: Mantaflow if force fields affect FLIP, else fake slow soft blobs (say so in README). Seam: thin emissive plane with noise shimmer; cool grey grade left, warm orange right. Do rigid-body beats first, then water.
Title: "Half Moon, half Jupiter 🌗 (watch the water)"

## 3. The Impossible Bounce (35–45 s) — easiest
Ball loses energy each bounce yet bounces higher because gravity switches to lighter planet each bounce. Hook: "This ball loses ⅓ of its energy every bounce. So why does it go HIGHER?"
Dropped 2 m on Sun; each bounce keeps 80% speed (64% energy).
Sun (start, 2 m drop) hits at 33.1 m/s · Jupiter 26.5 m/s, peak 14 m, air 2.1 s, 64% · Earth 21.2, 23 m, 4.3 s, 41% · Mars 17.0, 39 m, 9.1 s, 26% · Moon 13.6, 57 m, 16.7 s, 17% · Pluto 10.8, 95 m, 35 s, 11%.
Beats: each bounce hits a pad flashing new planet colour + label; height ruler grows beside ball, energy bar drains while height rises. Speed up Mars/Moon/Pluto 2–4× with "⏩". Final apex above clouds. End card: "Height = speed² ÷ 2g. Less gravity → same speed goes higher. Energy still went DOWN ✅".
Build: exact analytic keyframes (ballistic arc per planet g, speed ×0.8 per impact). Squash & stretch at impacts. Ground pad per bounce, environment colour fade per planet. Camera tracks ball up; world darker/starrier as it climbs. Overlays energy bar + ruler. Cheap Eevee.
Title: "This ball breaks physics… or does it? 🤯"

## 4. Guess the Planet (25 s) — quiz series
Same simple action (ball from 2 m / mug / toy) shown with no label; viewers guess planet from fall speed; reveal.
Beats: 0–2 hook "Which planet is this? Most people get this wrong 👀" + 3 answer buttons (A Moon · B Mars · C Pluto). 2–8 clip plays twice with 2 m ruler + stopwatch. 8–12 "Lock in your answer 👇" ticking 3-2-1. 12–18 reveal: label slams in + side-by-side same drop on Earth. 18–25 harder bonus round with 4 options.
Answer key (fall 2 m): Sun 0.12 · Jupiter 0.40 · Earth 0.64 · Mars 1.04 · Moon 1.57 · Pluto 2.54 s. Tiers: Easy Moon vs Jupiter; Medium Mars vs Moon; Hard Earth vs Neptune (11.15).
Build: reusable quiz rig: neutral grey studio (no planet colours), ruler, stopwatch synced to frames, action chosen from CONFIG. Exact analytic fall, bounce via rigid body (or analytic). Renders clip, reveal, Earth comparison. Renders N episodes from list of (planet, options).
Title: "Guess the planet from ONE drop 🪐"

## 5. Hourglass Race (45–60 s)
Six identical hourglasses in 2×3 grid flipped at once, each on a different planet. Sand flow ∝ √g (Beverloo), calibrated Earth = 60 s:
Sun 11.4 · Jupiter 37.7 · Earth 60.0 · Mars 97.6 · Moon 147.6 · Pluto 238.7 s. Flow independent of fill level.
Beats: 0–2 "Same sand. Same glass. 6 planets. Which finishes first?" with labelled tiles. 2 s all flip. 2–13 Sun empties "☀️ DONE in 11 s". 13–60 ⏩ timer speed-up; Jupiter, Earth, Mars finish, each tile greys out with its time. End: Moon & Pluto still trickling "Pluto: still going… 4 minutes total". Optional loop.
Build: hourglass via screw/lathe on profile curve, glass material. Sand procedural: top cone shrinking linearly, bottom cone growing, thin falling stream cylinder; grain texture + displacement. One wide shot of six hourglasses on planet-coloured pedestals (or 6 cameras composited).
Title: "Hourglass on every planet ⏳ Pluto takes FOREVER"

## 6. Saturn at the Moon's distance (50 s) — cinematic
Numbers: Saturn at 384,400 km spans 17.8° (~34× Moon width); rings ~39°. Mass ~7,700× Moon → tides ~7,700× stronger (hundreds of m). Weight change < 0.1%. Roche limit for Earth ~73,000 km (~5× closer than Moon).
Beats: 0–3 calm beach golden hour, waves, "What if Saturn replaced the Moon?". 3–12 rings rise over horizon then planet, "Distance: 384,400 km". 12–20 night, sunlit rings light beach; "You'd feel… nothing. (weight change < 0.1%)". 20–35 sea pulls back hundreds of m, seabed exposed, boats on mud, wall of water returns. 35–45 tremors, distant volcano glow, Moon drifts off course insert. 45–50 "And this was the SAFE distance. At 73,000 km, Earth gets torn apart…" cut to black.
Build: Saturn UV sphere banded procedural (wave texture + colour ramp tan/cream). Rings: disc with radial gradient alpha + gaps via ramp, tilted, shadow on Saturn. Beach: ocean modifier plane, sand, simple procedural palms, Nishita sky golden hour→night. Tide: keyframe ocean Z + shoreline retreat; returning wave via ocean displacement pulse. Camera low beach angle, slow push-ins, shake during tremors. Saturn angular size must be correct for camera FOV.
Title: "What if Saturn replaced the Moon? 🪐 (you'd feel nothing… at first)"

## Posting checklist
Question on screen within 1 s, first frame already shows motion. 25–60 s, payoff in last 3 s, loop-friendly. Real numbers on screen. One pinned prompt question. Same intro sting, fonts, planet colours every time.
