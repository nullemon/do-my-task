# Six unique planet-gravity video formats: full production briefs

Each brief is self-contained. To build one on another account, paste **"Shared rules"**
plus **one brief**, and ask for a single Blender Python script. The finished scripts in this
folder (`01-domino-planets`, `02-rube-goldberg-one-planet`, `03-canyon-jump`,
`05-gravity-music-sync`) are working examples of the style. Every number below is
calculated from real gravity values. Nothing here is guaranteed to go viral, but each
format is designed around something that reliably drives the algorithm: **predictions,
comments, watching to the end, rewatches, and a series to follow**.

Gravity (m/s²): Pluto 0.62 · Moon 1.62 · Mars 3.71 · Earth 9.81 · Jupiter 24.79 · Sun 274

| # | Format | Main hook | Engagement engine | Difficulty |
|---|---|---|---|---|
| 1 | Planet Marble League | "Pick your marble 👇" | comments + series | hard |
| 2 | Split World | half Moon, half Jupiter in one frame | rewatches + shares | medium-hard |
| 3 | The Impossible Bounce | "It loses energy… so why does it go HIGHER?" | debate in comments | easy |
| 4 | Guess the Planet | quiz: which planet is this? | comments + rewatches | easy |
| 5 | Hourglass Race | "Which runs out first?" | watching to the end | easy |
| 6 | Saturn at the Moon's distance | an epic sky + a myth-buster | shares | medium |

---

## Shared rules (paste with every brief)

- **The script:** one self-contained Blender Python script for Blender 4.2–5.x, with no
  downloaded assets; everything is built procedurally. Run it from the Scripting tab with
  ▶, or headless with `blender -b -P script.py -- --render`.
- **CONFIG block at the top:** planets, fps, duration, resolution, engine (Eevee by default),
  quality, PREVIEW/RENDER flags, output folder.
- **Format:** vertical 1080×1920 at 30 fps. A big readable label in the top third
  (`MOON · 1.62 m/s²`) and the hook caption in the first 2 seconds. The text must stay
  readable on bright scenes like the Sun (darker plate behind it, toned-down glow).
- **Physics:** real gravity values. Bake simulations so playback is deterministic. Very high
  gravity (the Sun) needs more substeps and solver iterations so nothing tunnels or
  explodes.
- **Verification:** the script prints the measured outcome and it must match the brief. The
  README says what's real and what's faked, and gives the expected render time.
- **Planet looks:**

  | Planet | Look |
  |---|---|
  | Pluto | pale ice, dark sky |
  | Moon | grey, black sky |
  | Mars | rust, butterscotch sky |
  | Earth | green and blue |
  | Jupiter | tan and orange haze |
  | Sun | glowing orange ground |

- **Blender tip:** scene gravity is one global value. You can animate it (the solver follows
  keyed `scene.gravity` during a bake). Different gravity in different *places at the same
  time* needs zone force fields instead; see briefs 1 and 2.

---

## 1. Planet Marble League 🏆 (the series)

**Pitch:** a marble race on a track that passes through planet zones. The gravity changes
under each marble as it crosses into the next zone. Viewers pick a marble before the start.

**Why it can work:**
- Marble races are a proven huge format, and gravity zones that reshuffle the race are new.
- Everyone picks a side, so they comment and they stay until the finish.
- A league table turns it into a recurring series.

**Hook (0–2 s):** 8 coloured, numbered marbles on the gate. Text: **"PICK YOUR MARBLE 👇"**,
with a 3-2-1 countdown.

**Beat sheet (75 s):**

| Time | Zone | What happens |
|---|---|---|
| 0–3 s | Start | Gate drops. Commentator-style caption: "AND THEY'RE OFF". |
| 3–15 s | Earth | Normal pace. The pack bunches up; a chicane causes bumping. |
| 15–30 s | Moon | Small jumps become huge floaty arcs, and a wide turn makes the leader drift outward. **The order shuffles.** |
| 30–42 s | Jupiter | Marbles slam into a banked hairpin. Anyone carrying too much speed jumps the wall: **"❌ OUT"**. |
| 42–60 s | Pluto | A gap jump in near slow motion, about 1.8 s of hang time per metre of drop. Any marble can win here. |
| 60–68 s | Sun | Straight sprint, marbles glued to the floor. Very fast; show a speed readout. |
| 68–75 s | Finish | Photo finish shown in slow-motion replay. **Podium 🥇🥈🥉** and a standings table. "Next race: Mars Canyon. Pick again 👇". |

**Real numbers to show:**
- Free fall from a 1 m ledge: Pluto 1.8 s, Moon 1.1 s, Earth 0.45 s, Jupiter 0.28 s,
  Sun 0.09 s.
- On a flat banked turn, the maximum speed before sliding out scales as √(μ·g·r). On
  Jupiter a marble can hold a corner about 1.6× faster than on Earth. On the Moon it can
  only take about 0.4× Earth's speed, which is why it drifts wide. That's real physics to
  pin in the comments.

**Blender build:**
- **Track:** spline track pieces (Curve → bevel profile → mesh) with walls, as passive
  rigid bodies. Each zone has a coloured floor strip and a big zone arch with a label.
- **Marbles:** 8 spheres (radius around 2.5–4 cm; small objects can be scaled up ×10 for
  Bullet stability, keeping the gravity ratios). Glass, metallic and paint materials, with a
  number decal.
- **Per-zone gravity, the key part:** set **scene gravity to 0**. For each zone, add a
  Force field pointing straight down, limited to that zone: a *Force*/*Wind* field with the
  Plane shape plus a max distance, or one empty per zone with a box-shaped influence region
  via `use_max_distance`. Set its strength so the acceleration equals that planet's g.
  **Prototype this first with 2 zones** and check that a marble crossing the boundary
  changes acceleration within a frame. If force fields can't be bounded cleanly, the
  fallback is a per-frame Python handler applying `g·mass` as an impulse/force through an
  animated force object per marble.
- **Randomness:** a seed-based starting order and tiny initial nudges, so every race differs
  and isn't scripted. Bake, then read the finishing order from the cache to build the
  podium.
- **Camera:** follows the leader (constraint to the lead marble, smoothed), with replay
  cutaways.

**Text and audio:** live position tower on the side (1. 🔴 2. 🔵 …). Commentator captions.
Crowd cheer at the finish.

**Title:** "Marble race through every planet 🪐 Pick yours!"
**Pinned comment:** "Who did you pick? Winner gets a rematch on Mars 👇"
**Episodes:** a different track per planet order ("Sun Start", "Pluto Finale"), a season
standings table, elimination rounds, and fan-named marbles from the comments.

**Risk:** the hardest technical piece of the six (the zone gravity). Build a 2-zone test
first.

---

## 2. Split World 🌗 (the visual showpiece)

**Pitch:** one shot, split down the middle by a glowing seam. The left half is the Moon and
the right half is Jupiter, each with its own gravity. Everything that crosses the seam
changes behaviour instantly.

**Why it can work:** it's never-seen-before visual weirdness that people screenshot,
rewatch and send to friends ("how is half of it floating?!").

**Hook (0–2 s):** a static kitchen table split by the seam. Text: **"LEFT: MOON · RIGHT:
JUPITER"**. A glass of water sits right on the line.

**Beat sheet (30–40 s):**

| Time | What happens |
|---|---|
| 0–5 s | A hand pours water from the left side to the right. On the left the stream arcs up in slow blobs; the moment it crosses the seam, it slams down and splashes. |
| 5–12 s | A ball rolls across the table from left to right. On the left it drifts and bounces lazily; on the right it is pinned to the table, and falls off the edge in 0.28 s. The left one takes 1.1 s from the same 1 m height. |
| 12–20 s | A deck of cards is thrown across the seam. The left half of the cards flutters; the right half drops like stones. |
| 20–30 s | **Finale:** a long pendulum swings back and forth across the seam, slow on the left and snapping fast on the right. Then the seam slides sideways and Jupiter "eats" the whole frame: everything crashes down. |
| End | Text: "Which side would you live on? 👇" |

**Real numbers:**
- Fall from the table (1 m): Moon 1.11 s, Jupiter 0.28 s, about 4× faster.
- A pendulum swing half on each side is the real average of the two half-periods (show a
  timer).

**Blender build:**
- **Zone gravity:** same technique as brief 1, with scene gravity 0 and two box-limited
  downward force fields meeting at the seam (x = 0). Rigid bodies (ball, cards, pendulum
  with a hinge constraint) pick it up automatically.
- **Water:** Mantaflow. The fluid domain has a single gravity, so check whether force fields
  affect FLIP liquid (Mantaflow supports *Force/Wind* field influence via the domain's
  field weights). If they don't, fake the left-side water as slow soft blobs, which is
  acceptable, and say so in the README.
- **Seam:** a thin emissive vertical plane with a subtle shimmer (noise texture), plus a
  different colour grade per side: cool grey Moon on the left, warm orange Jupiter on the
  right, via two compositor masks or two lights.
- **Camera:** locked off, so the seam is the hero.

**Title:** "Half Moon, half Jupiter 🌗 (watch the water)"
**Episodes:** Pluto | Sun, Earth | Mars, and a "4-way split" (four quadrants).

**Risk:** zone gravity (shared with brief 1) and the fluid. Do the rigid-body beats first,
then add water.

---

## 3. The Impossible Bounce 🏀 (the paradox; easiest to make)

**Pitch:** a ball keeps losing energy on every bounce, yet it bounces **higher** each time,
because gravity switches to a lighter planet at each bounce.

**Why it can work:** it looks like it breaks physics, so people argue in the comments
("energy can't increase!"), which is exactly the engagement the algorithm rewards. The
explanation is real and satisfying.

**Hook (0–2 s):** **"This ball loses ⅓ of its energy every bounce. So why does it go
HIGHER?"**

**Real numbers:** dropped from 2 m on the Sun. Each bounce keeps 80% of the speed, which is
64% of the energy. At each bounce, gravity switches to the next planet.

| Bounce → planet | Launch speed | Peak height | Airtime | Energy left |
|---|---|---|---|---|
| Sun (start, 2 m drop) | hits at 33.1 m/s | – | – | 100% |
| Jupiter | 26.5 m/s | **14 m** | 2.1 s | 64% |
| Earth | 21.2 m/s | **23 m** | 4.3 s | 41% |
| Mars | 17.0 m/s | **39 m** | 9.1 s | 26% |
| Moon | 13.6 m/s | **57 m** | 16.7 s | 17% |
| Pluto | 10.8 m/s | **95 m** | 35 s | 11% |

**Beat sheet (35–45 s):** each bounce hits a pad that flashes the new planet's colour and
label. A height ruler grows on screen beside the ball, and an **energy bar** visibly
*drains* while the height *rises*. That contrast is the whole video. Speed up Mars, Moon and
Pluto 2–4× with a "⏩" icon. The final apex is above the clouds.

**End card:** "Height = speed² ÷ 2g. Less gravity → same speed goes higher. Energy still
went DOWN ✅"

**Blender build:**
- **Motion:** exact analytic keyframes, which is the cleanest option and needs no
  simulation: the ballistic arc per bounce with that planet's g, the speed multiplied by
  0.8 at each impact.
- **Look:** squash-and-stretch on the ball at impacts (shape key or scale keys).
- **Ground:** one ground pad per bounce, with an environment colour fade per planet.
- **Camera:** tracks the ball upward. The world gets darker and starrier as it climbs.
- **Overlays:** energy bar and ruler, from animated text/geometry or the compositor.
- **Cost:** cheap; renders fast in Eevee.

**Title:** "This ball breaks physics… or does it? 🤯"
**Pinned comment:** "Explain it in one sentence 👇 (wrong answers only also accepted)"
**Episodes:** the reverse (Pluto to the Sun: shrinking until it's crushed), "Can it reach
space?", and a bouncing jelly version.

---

## 4. Guess the Planet 🔎 (quiz series)

**Pitch:** the same simple action (a ball dropped from 2 m, a cup of coffee spilling, a cat
toy falling off a shelf) is shown with **no label**. Viewers guess the planet from how fast
it falls, then the answer is revealed.

**Why it can work:** quizzes generate huge comment volume (people post guesses), and
people rewatch to check. It's very cheap to make many episodes.

**Hook (0–2 s):** **"Which planet is this? Only 3% get it right 👀"**. Only say a
percentage if you have the real number; "Most people get this wrong" is safer.

**Beat sheet (25 s):**

| Time | What happens |
|---|---|
| 0–2 s | Hook plus 3 answer buttons on screen (A Moon · B Mars · C Pluto). |
| 2–8 s | The clip plays twice. A 2 m ruler and a stopwatch are visible: smart viewers can compute g from the time. |
| 8–12 s | "Lock in your answer 👇" with a ticking 3-2-1. |
| 12–18 s | **Reveal:** the label slams in and a side-by-side shows the same drop on Earth. |
| 18–25 s | A harder bonus round with 4 options. |

**Real answer key** (fall time from 2 m): Sun 0.12 s · Jupiter 0.40 s · Earth 0.64 s ·
Mars 1.04 s · Moon 1.57 s · Pluto 2.54 s.

**Difficulty tiers:**
- Easy: Moon vs Jupiter.
- Medium: Mars vs Moon.
- Hard: Earth vs Neptune (11.15). Those are only 7% apart in fall time, which makes great
  "rigged!" comments.

**Blender build:**
- One reusable "quiz rig": a neutral grey studio (no planet colours, so the look doesn't
  give it away), a ruler, a stopwatch overlay synced to the frames, and an action chosen
  from CONFIG (ball / mug / toy).
- Exact analytic fall with the bounce done in rigid body.
- Render the clip, the reveal frame and the Earth comparison.
- The script renders N episodes from a list of (planet, options) pairs.

**Title:** "Guess the planet from ONE drop 🪐"
**Pinned comment:** "Answer in the comments before the reveal. No cheating 😤"
**Series:** daily episodes, a "streak" challenge, and viewer-submitted actions.

---

## 5. The Hourglass Race ⏳ (oddly satisfying)

**Pitch:** six identical hourglasses in a 2×3 grid are flipped at the same moment. Each
sits on a different planet. Which empties first?

**Why it can work:** oddly-satisfying visuals, an obvious question, and a payoff that keeps
people watching to the end: Pluto takes 4× longer than Earth.

**Real physics:** sand flow through an orifice scales with √g (the Beverloo law, measured
in real experiments). Emptying time is calibrated so Earth = 60 s.

| Planet | Time |
|---|---|
| Sun | **11.4 s** |
| Jupiter | 37.7 s |
| Earth | 60.0 s |
| Mars | 97.6 s |
| Moon | 147.6 s |
| Pluto | **238.7 s** |

Unlike water, sand flow doesn't depend on how full the hourglass is. That's why hourglasses
work, and it's a nice fact for the description.

**Beat sheet (45–60 s):**

| Time | What happens |
|---|---|
| 0–2 s | **"Same sand. Same glass. 6 planets. Which finishes first?"** with the planet tiles labelled. |
| 2 s | All flip together, with a satisfying clunk sound. |
| 2–13 s | The Sun empties almost instantly: "☀️ DONE in 11 s". |
| 13–60 s | ⏩ timer speed-up. Jupiter, then Earth and Mars finish, each tile greying out with its time. |
| End | Cut to Moon and Pluto still trickling: **"Pluto: still going… 4 minutes total"**. Optional loop: the final frame matches the start. |

**Blender build:**
- **Hourglass:** a lathe/screw modifier on a profile curve, with a glass material.
- **Sand:** procedural, with no particle sim needed:
  - a top cone scaled down linearly over the planet's time
  - a bottom pile growing as a cone
  - a thin falling stream (a cylinder, or a particle emitter with a short life)
- A visible grain texture plus displacement makes it read as real sand. The timing comes
  straight from the table, so it's exact and cheap.
- **Layout:** a 2×3 grid via six cameras composited, or one wide shot of six hourglasses on
  planet-coloured pedestals.
- **Audio:** soft sand ASMR (a free sample) plus a "ding" at each finish.

**Title:** "Hourglass on every planet ⏳ Pluto takes FOREVER"
**Episodes:** a candle, a water clock (which speeds up differently), a dripping tap.

---

## 6. Saturn at the Moon's distance 🪐 (the cinematic myth-buster)

**Pitch:** what if Saturn replaced the Moon? An epic, beautiful sky shot, plus a
counter-intuitive science twist.

**Why it can work:** awe-inspiring visuals share well, and "you wouldn't even feel it" is a
surprising, comment-worthy myth-buster. Bonus: no physics simulation is needed, so it's
mostly look-dev.

**Real numbers (Saturn at 384,400 km):**
- **Size in the sky:** Saturn spans **17.8°**, about **34× the Moon's width**. The rings
  span about **39°**, roughly half the way from horizon to overhead.
- **Mass:** Saturn is about **7,700× the Moon's mass**, so tides are about 7,700× stronger.
  Today's ocean tide is under 1 m; this would be hundreds of metres or more, depending on
  how long it stays.
- **What you'd feel:** almost nothing. Earth and you fall toward Saturn together, so your
  weight changes by less than 0.1%.
- **Ripped apart?** Earth only breaks up inside Saturn's Roche limit for Earth, about
  **73,000 km**. That's about 5× closer than the Moon.

**Beat sheet (50 s):**

| Time | What happens |
|---|---|
| 0–3 s | Calm beach at golden hour, waves lapping. Text: **"What if Saturn replaced the Moon?"** |
| 3–12 s | Something huge rises over the horizon: the rings first, slicing the sky, then the planet. Label: "Distance: 384,400 km". |
| 12–20 s | Night: the sunlit rings light up the beach like a second moon. Myth-bust card: **"You'd feel… nothing. (weight change < 0.1%)"** |
| 20–35 s | Then the tides. The sea pulls back hundreds of metres, exposing the seabed; boats on mud. A wall of water returns. |
| 35–45 s | Ground tremors and a distant volcano glow. The Moon drifts off course (insert). |
| 45–50 s | **"And this was the SAFE distance. At 73,000 km, Earth gets torn apart…"** Cut to black. Part 2 tease. |

**Blender build:**
- **Saturn:** a UV sphere with banded procedural materials (a wave texture plus a colour
  ramp in tan and cream). NASA Cassini image maps are free if you want realism; this
  script stays procedural.
- **Rings:** a disc with a radial gradient alpha (separate rings and gaps via a colour
  ramp), tilted. A shadow on Saturn helps.
- **Beach:** an ocean modifier plane, sand, a few palms (procedural or simple), a Nishita
  sky (Sky Texture) for golden hour to night.
- **Tide:** keyframe the ocean plane's Z and the shoreline retreat (fake, but plausible).
  The returning wave is an ocean displacement pulse or a simple fluid for the hero shot.
- **Camera:** low beach angle, with slow push-ins and camera shake during tremors.
- **Cost:** volumetrics and the ocean are the main expense; preview in Eevee.

**Title:** "What if Saturn replaced the Moon? 🪐 (you'd feel nothing… at first)"
**Episodes:** Part 2 "Saturn at 73,000 km", "Jupiter instead of the Moon", "Earth with
rings".

---

## Recommended order for a new account

1. **Impossible Bounce:** the easiest, a strong debate hook, and it tests your pipeline.
2. **Guess the Planet:** a cheap daily series that builds a comment habit.
3. **Hourglass Race:** satisfying, and keeps people watching.
4. **Saturn:** the "big" visual post once you have followers.
5. **Split World**, then **Marble League:** they share the zone-gravity tech, so build that
   once (the 2-zone test) and reuse it for both. The league becomes the long-running
   series.

## Posting checklist (every video)

- **Hook:** the question is on screen within 1 s, and the first frame already shows
  motion.
- **Length:** 25–60 s, with the payoff in the last 3 seconds and a loop-friendly ending.
- **Numbers:** real numbers on screen. A wrong number gets called out, and it's better to be
  the one correcting it.
- **Pinned comment:** one pinned prompt question.
- **Series look:** the same intro sting, fonts and planet colours every time, so viewers
  recognise the series in a second.
