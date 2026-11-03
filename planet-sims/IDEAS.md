# More planet-gravity video ideas

Ten more ideas in the same style as the six already built. Each one has a hook, the beats
of the video, **real numbers** (worked out from each planet's gravity), how to build it in
Blender, and why people will comment.

**To build one on another account:** paste the "Shared rules" section below together with
one idea, and ask for a single self-contained Blender Python script. The six finished
scripts in this folder are working examples to point it at (for example
`02-rube-goldberg-one-planet/` or `03-canyon-jump/`).

Gravity values (m/s²): Pluto 0.62 · Moon 1.62 · Mars 3.71 · Earth 9.81 · Jupiter 24.79 · Sun 274.
Everything below ignores air unless it says otherwise.

---

## Shared rules (paste with any idea)

- One self-contained Blender Python script (Blender 4.2–5.x) that builds everything
  procedurally, with no downloaded assets. Run it from the Scripting tab with ▶, or headless
  with `blender -b -P script.py -- --render`.
- Use real gravity per planet. One scene per planet, or one scene with a planet loop. Bake
  the physics so playback is deterministic.
- Vertical 1080×1920 at 30 fps, rendered in Eevee. Put a big readable label like
  `MOON · 1.62 m/s²` in the top third, plus a hook caption.
- Put a CONFIG block at the top: the planet list, quality, preview/render flags and the
  output folder.
- The script prints the measured outcome per planet, and the result must match the idea.
- The README says honestly what is real and what is faked.
- Per-planet look: Moon grey with a black sky, Mars rust, Earth green/blue, Jupiter tan
  haze, Sun a glowing orange ground (keep the text readable over it), Pluto pale ice with a
  dark sky.

---

## 1. The hourglass race ⏳ (strongest new idea)

**Hook:** "Same hourglass. Six planets. Which one runs out first?" Six hourglasses
side-by-side in a 2×3 grid, each with a timer.

**Why it works:** it's very satisfying to watch, it's an easy guessing game, and the Pluto
one taking four minutes makes people stay to watch it.

**Real physics:** sand flowing through a hole runs at a rate proportional to √g (this is
called the Beverloo law, and it's a real result). Flow time therefore scales as 1/√g.

| Planet | Time if Earth = 60 s |
|---|---|
| Sun | **11.4 s** |
| Jupiter | 37.7 s |
| Earth | 60.0 s |
| Mars | 97.6 s |
| Moon | 147.6 s |
| Pluto | **238.7 s** |

**Video beats:** flip all six at once. The Sun empties almost instantly ("already done?!").
Jupiter finishes, then Earth. Speed the clip up 4× from 60 s, keeping the timer on screen.
End on Pluto still dripping, captioned "4 minutes later…".

**Blender build:**
- Glass hourglass body.
- The sand uses particles or Geometry Nodes points. There's no need to simulate millions of
  grains: drive a **procedural sand level** from the formula, with a thin falling stream (a
  particle emitter or a cylinder) and a growing cone (scale the cone mesh).
- Use a Compositor or Geometry Nodes timer text per tile.
- Cheap to render.

**Comment bait:** "Guess the Pluto time before the end."

---

## 2. Pendulum wave on every planet 〰️

**Hook:** "The famous pendulum wave… but on 6 planets at once."

**Real physics:** the period of a 1 m pendulum is T = 2π√(L/g).

| Planet | Period of a 1 m pendulum |
|---|---|
| Sun | 0.38 s |
| Jupiter | 1.26 s |
| Earth | 2.01 s |
| Mars | 3.26 s |
| Moon | 4.94 s |
| Pluto | 7.98 s |

A pendulum wave is 15 pendulums whose lengths are tuned so that their patterns line up
every N seconds. On another planet the whole pattern runs √g times faster or slower: on
the Sun it's a blur of chaos, on Pluto it's slow and hypnotic. Those are the same pattern
on different clocks.

**Blender build:**
- Pure keyframes from the exact formula θ(t) = θ₀·cos(2πt/T). No simulation is needed, so
  it's perfect and cheap.
- Use a 2×3 split screen, or one long shot that dollies past six rigs.
- Add satisfying "tick" sounds on each crossing.

**Twist:** the pattern lines up on Earth at 60 s. Show which planet lines up first
("Sun: 11 s!").

---

## 3. How high can you jump? (with a comet ending) 🦘

**Hook:** "The same jump on every planet… and on one of them you never come back down."

**Real physics:** take-off at 2.4 m/s, which is about a normal 30 cm jump on Earth.
Height is v²/2g and airtime is 2v/g.

| Planet | Height | Airtime |
|---|---|---|
| Sun | 1 cm (can't even lift a foot) | 0.02 s |
| Jupiter | 12 cm | 0.19 s |
| Earth | 29 cm | 0.49 s |
| Mars | 78 cm | 1.3 s |
| Moon | 1.8 m | 3.0 s |
| Pluto | 4.6 m | 7.7 s |

**Ending:** on a small comet like 67P (Rosetta's comet), the escape speed is only around
1 m/s, so a normal jump sends you off into space forever.

**Blender build:**
- A Mixamo character, or a simple stylised mannequin. Use the jump animation, then keyframe
  the vertical offset from the exact ballistic formula.
- On the Sun, play a "crushed into a squat" pose instead.
- Put a height ruler and the airtime on screen.

---

## 4. Egg drop from 10 m 🥚

**Hook:** "We dropped an egg from 10 m on every planet. Which ones survive?"

**Real physics:** impact speed is √(2gh) and fall time is √(2h/g).

| Planet | Fall time | Impact speed |
|---|---|---|
| Pluto | 5.7 s | 3.5 m/s |
| Moon | 3.5 s | 5.7 m/s |
| Mars | 2.3 s | 8.6 m/s |
| Earth | 1.4 s | 14.0 m/s |
| Jupiter | 0.9 s | 22.3 m/s |
| Sun | 0.27 s | 74 m/s |

**Rule:** the egg lands on a cushion that saves it below about 6 m/s, which is a choice you
make and should state in the video. Pluto and the Moon survive, Mars cracks, Earth breaks,
Jupiter splatters and the Sun vaporises it.

**Blender build:**
- Rigid-body egg. Use **Cell Fracture** for the breaking versions, swapped in at impact.
- Yolk splat: a shape-keyed disc, or a quick particle/fluid splash.
- Cut to slow motion at impact. Show a "SURVIVED ✓ / CRACKED / SPLAT" card.

---

## 5. Same rocket, every planet 🚀

**Hook:** "This rocket barely makes it off Earth. Watch it on Jupiter."

**Real physics:** a rocket's thrust-to-weight ratio (TWR) scales as 1/g. A TWR above 1
lifts off; below 1, the rocket can't leave the pad.

| Planet | TWR (a rocket with 1.3 on Earth, like a real launcher) | What happens |
|---|---|---|
| Pluto | 20.6 | rockets away instantly |
| Moon | 7.9 | rockets away instantly |
| Mars | 3.4 | easy launch |
| Earth | 1.3 | slow, dramatic climb |
| Jupiter | 0.51 | **engines at full power, nothing moves** |
| Sun | 0.05 | engines at full power, nothing moves |

The real Jupiter twist: it's a gas giant, so there's no pad to stand on, and orbital speed
there is about 42 km/s. Show that as a text card.

**Blender build:**
- Keyframed motion from a = (TWR − 1)·g. Clamp at 0 so the Jupiter and Sun rockets sit
  still.
- Smoke: Mantaflow for the hero shot, or cheap volumetric cones.
- Camera shake; the launch tower glows on the Sun.

---

## 6. The bridge load test 🌉

**Hook:** "How many cars can this bridge hold on each planet?"

**Real physics:** the load a bridge feels is mass × g, so the number of cars it holds
scales as 1/g.

| Planet | Cars before it fails (if Earth holds 8) |
|---|---|
| Pluto | 126 |
| Moon | 48 |
| Mars | 21 |
| Earth | 8 |
| Jupiter | 3 |
| Sun | 0, it collapses under its own weight |

**Blender build:**
- The bridge deck is pieces held together by rigid-body constraints with **Breakable**
  turned on. Set the break threshold so Earth fails at about 8 cars.
- Cars drive on one by one with a counter: "CARS: 7… 8… 💥".
- Speed up the long Pluto queue with a time-lapse card.

---

## 7. The marble run that does the same thing everywhere (myth-buster) 🔮

**Hook:** "We expected chaos. Instead every planet did EXACTLY the same thing… just at a
different speed."

**Real physics (counter-intuitive and true):** if gravity is the only thing driving the
marbles, their paths are identical on every planet: the same loops, the same jumps, the
same landings. Only the clock changes, by √g. Friction and air make small differences,
which is a nice detail for viewers to spot.

**Video:** a 2×3 split-screen race. First the paths overlap perfectly ("wait…").
Then add a **motor** (a fixed-speed launcher) halfway down. Now the paths split wildly,
because the motor doesn't scale with gravity. This is the same trick the Rube Goldberg
script uses.

**Blender build:**
- A rigid-body marble run made of track pieces.
- Overlay all six marbles as ghost trails in one final frame to prove the paths match.

**Comment bait:** "Explain why in the comments." The smart-viewer comments boost it.

---

## 8. Slinky drop 🌀

**Hook:** "Drop a slinky on every planet. The bottom floats on ALL of them."

**Real physics:** when you let go of a hanging slinky, the bottom stays perfectly still
until the collapse reaches it. That's a famous slow-motion video.
- **How far it stretches** scales with g. On Jupiter it hangs long, on Pluto it's
  scrunched up.
- **The interesting claim:** for an ideal slinky, the collapse time depends on its mass and
  springiness, *not on g*. Same collapse time, completely different stretch. Check this in
  the simulation before you claim it.

**Blender build:**
- Soft body, or a chain of rigid-body rings with spring constraints.
- Shoot in super slow motion.

---

## 9. Half-court shot that only goes in on one planet 🏀

**Hook:** "Same throw, 6 planets. Only ONE is a swish. Guess which."

It's the same trick as the Rube Goldberg idea, in a sports setting.
- A fixed launch speed and angle, tuned so Mars swishes.
- The Moon flies over the backboard, Earth hits the front rim, Jupiter is an airball, and on
  the Sun the ball drops at the thrower's feet.

**Blender build:**
- Analytic ballistic keyframes until rim contact, then rigid body for the rim bounces.
- Net: a cloth sim, or a shape-key swish.
- Show a scoreboard per planet.

---

## 10. Drop from the Burj Khalifa ⏱️

**Hook:** "A ball dropped from the world's tallest building on every planet. Race."

**Real physics:** 828 m, with no air. Fall time is √(2h/g).

| Planet | Fall time |
|---|---|
| Sun | 2.5 s |
| Jupiter | 8.2 s |
| Earth | 13.0 s |
| Mars | 21.1 s |
| Moon | 32.0 s |
| Pluto | 51.7 s |

Twist card: "On Earth, air would actually slow it to about 60 m/s" (the terminal speed of a
ball). Pluto and the Moon have no real air, so they're accurate.

**Blender build:**
- Six towers in a row, with a vertical dolly camera following the balls.
- Procedural tower: a tapered stack of cylinders with emissive window strips.

---

## Bonus ideas from earlier chats

- **Saturn passes Earth at the Moon's distance:** a visual sky piece with tides and a
  "this was the SAFE distance" ending. The numbers are in the earlier chat.
- **A city where gravity slowly rises:** plan it as shots, not one simulation. Use 1× → 10×
  stages and a counter.

## Format tips that apply to all of them

- **First 1–2 seconds:** state the question on screen ("Which planet…?"). Prediction videos
  keep people watching.
- **Ending:** save the surprising result for last (Pluto's 4-minute hourglass, Mars as the
  only winner, the comet jump).
- **Numbers on screen:** put the real figure on screen (g, time, speed). It makes the video
  feel credible and shareable.
- **Series:** make it a recurring series with the same intro sting and the same planet
  colours, so viewers recognise it instantly.
