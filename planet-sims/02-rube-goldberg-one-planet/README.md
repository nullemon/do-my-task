# The machine that only works on one planet

`rube_goldberg_planets.py` builds the same small Rube Goldberg machine on each planet, one Blender scene per planet (`01_Moon` … `06_Mars`), and bakes the rigid-body physics:

**spring plunger → ball flies over a pit → lands in a funnel basket → chute + quarter-pipe → 8 dominoes → last domino pushes a golf ball into a cup → lamp lights up, flag rises, confetti.**

At the top is the hook caption *"Only ONE planet makes this work. Guess which?"* and the planet label. When the outcome is decided, a `✓ WORKS` / `✗ FAILS` stamp pops in with a short reason. Scenes are numbered in the recommended video order, with the winner last.

## Measured result (printed after every bake)

| planet | g | result | what happens |
|---|---|---|---|
| Moon | 1.62 | FAILS | flies over the basket (crosses rim height at x=1.97 m; basket is at 0.66–1.26) |
| Pluto | 0.62 | FAILS | flies way over (x=3.78 m), off into the void |
| Jupiter | 24.79 | FAILS | barely launches and drops into the pit at x=−0.05 m |
| Sun | 274 | FAILS | the launch ledge snaps under its own weight (falls 2.27 m) |
| Earth | 9.81 | FAILS | hits the outside of the basket wall ("SO CLOSE…") |
| **Mars** | 3.71 | **WORKS** | lands in the basket (x=0.96), dominoes fall, golf ball ends in the cup |

Mars still succeeds when the launch speed is changed by ±12%, so the result isn't fragile. Every miss falls into a walled pit, so it can't set off the rest of the machine by accident.

## Run

- **In Blender:** open the Scripting tab, open the script and press ▶. It builds and bakes all scenes in about 10 s. Switch scenes and press play. The default engine is Eevee at 1080×1920 and 30 fps.
- **Headless preview** (low-sample Cycles stills): `blender -b -P rube_goldberg_planets.py -- --preview`
- **Full render:** `blender -b -P rube_goldberg_planets.py -- --render`. This writes `renders/rube_goldberg_one_planet/NN_Planet/frame_####.png`, next to the .blend or in the working directory. You can also set `RENDER = True` in CONFIG.

## CONFIG knobs

- `PLANETS`: the planets and their order (default Moon, Pluto, Jupiter, Sun, Earth, Mars).
- `TARGET_PLANET`: the planet where the machine works. The plunger speed is calculated so the ball lands in the basket at that planet's gravity. I tested Earth and Moon as targets and each gave exactly one success.
- Other knobs: `FPS`, `SECONDS`, `RESOLUTION`, `ENGINE`, samples, `HOOK_TEXT`/`SHOW_HOOK`, `LAUNCH_SPEED_TRIM`, `SUBSTEPS` (40 per frame, which is 1200 Hz), and `LEDGE_RATED_G` (the gravity at which the ledge joint breaks).
- The table above uses the default planet list. Mercury (3.70) has almost the same gravity as Mars, so it would also succeed if you added it.

## What's real and what's faked

**Real:**
- Gravity values.
- All Bullet rigid-body motion: the flight, the basket, the chute, the dominoes, the golf ball and the cup.
- The Sun collapse. The ledge hangs on a breakable fixed joint whose strength is set for about 90 m/s², and it is the same on every planet. It breaks only at 274 m/s².

**Not physical:**
- The plunger is a keyframed "motor" (a kinematic object) with a fixed stroke and speed. Its launch speed doesn't depend on gravity, and that is the whole trick. A machine driven only by gravity would behave the same on every planet, just faster or slower.
- The lamp, the flag, the confetti and the stamp are keyframed from the measured outcome, like a sensor would trigger them. The confetti is a simple ballistic motion with drag, using the planet's own gravity.

## Render time

- Each clip is 225 frames (7.5 s); all 6 are 1350 frames.
- Eevee at 1080×1920 on a GPU: roughly 0.5–2 s per frame, so about 15–45 minutes in total.
- Cycles on a CPU at 128 samples: several hours.
- `--preview` takes about 50 s here (7 stills at 270×480, 12 samples).

`preview/` holds one still per planet at its key moment, plus a still of Mars mid-flight.
