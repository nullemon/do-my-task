# 1 · Planet Marble League (75 s)

**Title:** Marble race through every planet 🪐 Pick yours!
**Pinned comment:** Which number did you pick? 👇 On Jupiter the hairpin grip is 1.6× Earth's, but #8 still flew out. Mars Canyon is next.

8 numbered marbles race down one track through five gravity zones, **Earth → Moon → Jupiter → Pluto → Sun**.
The gravity changes under each marble as it crosses a zone line. Everything is procedural and comes from one file, `script.py`.

## Run

```bash
blender -b -P script.py -- --render            # final: 1080×1920, 30 fps, 75 s, Eevee, MP4
blender -b -P script.py -- --preview           # fast: 50 % res, 8 samples
blender -b -P script.py -- --seed 8 --render   # a different race (start grid + nudges)
blender -b -P script.py -- --frames 1,900,2200 --scale 25 --engine CYCLES   # test stills (PNG)
blender -b -P script.py -- --ff-test           # re-run the force-field prototype (see below)
python3 script.py -- --sim-only                # physics + verification only, no Blender needed
```

You can also open the script in the Scripting tab and press ▶. That builds and bakes the scene (it clears the objects in the current scene first) but does not render.
Settings are in the `CONFIG` block at the top: seed, zone order, fps, duration, resolution, engine, PREVIEW/RENDER, output folder, physics constants and the emoji switch.
The engine id is chosen automatically: `BLENDER_EEVEE_NEXT` on 4.2–4.x and `BLENDER_EEVEE` on 5.x.
Output goes to `//render_marble_league/planet_marble_league_####.mp4`.

## How the per-zone gravity works (real vs faked)

**Prototype first (as the brief asked).** I set scene gravity to 0, added a rigid-body sphere and one force field per zone asking for the Moon's 1.62 m/s², then measured the motion. You can repeat this with `--ff-test`.
- Bullet applied only about **0.1 m/s²**. The ratio is undocumented, and it changes with field placement: an earlier layout gave 0.055.
- The value was noisy, about ±4 % from frame to frame.
- The Wind type pushed the sphere *up*.
- Falloff can only be spherical, tube or cone, so a zone can't be bounded by a box.

In short, force fields can't give a clean, box-bounded "g = 1.62 here". Per-frame handlers can't help either, because they can only change the one global scene gravity.

**What the script does instead (real physics, my own engine):** `simulate()` is a small deterministic rigid-sphere engine in pure Python.
- **Track.** It is a spline-like centre line with a half-pipe cross-section: a flat floor plus curved side walls. The wall height (the "lip") is set per segment. Each marble is located in track coordinates (s, lateral, height) every sub-step.
- **Contacts.** Contacts are one-sided. Marbles really leave the track over crests, at the step, at the gap and over the hairpin wall, and they land again. The restitution is 0.35.
- **Rolling.** While touching the track, the tangential part of gravity is scaled by 5/7. That is the exact result for a solid sphere rolling without slipping.
- **Marbles.** Marble-to-marble collisions are equal-mass impulses (e = 0.6). Each marble's visible spin comes from its rolling (ω = n × v / r).
- **Gravity per zone.** g is picked **per marble, per 1/1200 s sub-step**, from the zone that marble is in. So two marbles a metre apart really do feel different g. The Sun's 274 m/s² is stable at 1200 Hz: about 0.2 mm of penetration per step and no tunnelling.
- **Out.** A marble that leaves the channel (lands outside it, or misses the gap) is OUT. It falls under its zone's g to the ground.
- **Baking.** The race is baked into keyframes on **every frame** for all 8 marbles, the camera and the position-tower tags. Playback and rendering are therefore deterministic and need no handlers. The finishing order, podium, standings table, OUT pop-ups and speed read-out are all built from the baked result.

**Faked or tuned (stated openly):**
- **Rolling losses.** On the track the loss is `(c_rr + c_v·v²) × normal load` (0.01 and 0.004 s²/m²). The v² term is a "speed-dependent rolling drag": it stands in for track roughness and gives each slope a cruising speed. It is *not* applied in the air, so airborne motion is pure ballistics.
- **Track design.** Slopes, the hairpin lip and the zone lengths were hand-tuned so the leader's zone times match the beat sheet.
- **Spin.** The marbles do not carry real angular momentum (spin is cosmetic).
- **Scale.** The marbles are 3 cm marbles scaled ×10 (r = 0.30 m). Gravity is kept at the real values, so 1 m of world drop takes the real planet fall time.
- **Not used.** No Bullet rigid bodies and no Curve→bevel objects are used. The track mesh is swept from the same centre line and profile the physics uses, so what you see is exactly what the marbles collide with.
- **Visual-only effects.** Sky colour and stars follow the leader's zone. The slow-mo replay is the same baked data re-sampled at ×0.38.
- **Emoji.** Emoji (👇 ❌ 🥇) render as monochrome outlines through Blender 5.x's font fallback. On a build that shows boxes, set `use_emoji: False`.

## Beat sheet vs what the default race (seed 3) does

| Beat | Brief | Baked race (leader, video s) |
|---|---|---|
| Hook | 8 marbles on the gate, "PICK YOUR MARBLE 👇", 3-2-1 | 0–2 s, top-down shot of the numbered grid, slow dolly |
| Start | gate drops, "AND THEY'RE OFF" | gate drops at 2.0 s |
| Earth | pack bunches, chicane bumping | 2–15.8 s; S-chicane, 30 cm step-down |
| Moon | floaty arcs, wide turn, shuffle | 15.8–30.2 s; 5 humps launch long arcs; leader rides high in the 125° turn |
| Jupiter | banked hairpin, too fast → "❌ OUT" | 30.2–42.0 s; **#8 (leading) flies over the 38° lip at 33.4 s → OUT**; overhead cut-away |
| Pluto | gap jump, ~1.8 s hang per metre | 42.0–60.3 s; 1.0 m drop gap; side cut-away with a 1 m ruler; caption "#7 hang time 1.82 s" |
| Sun | straight sprint, glued, speed read-out | 60.3–68.0 s; leader speed 16 → 23 km/h; 3 cm step = 15 ms airborne |
| Finish | photo finish, slow-mo replay, podium + standings, "Next race…" | #7 68.05 s, #2 +0.21, #1 +0.37 → replay ×0.38, podium 2-1-3, table incl. DNF |

Other seeds give other winners and 0–3 Jupiter DNFs. Zone timing stays within about ±2 s of the beats (seeds 1–12 were tested).

## Verification (printed every run; `assert` fails the run if a check is off)

```
-- measured vertical acceleration while airborne (from the baked motion)
   EARTH    target    9.81  measured    9.810 m/s²  (0.00%)  741 airborne runs | per-frame keys: 9.810
   MOON     target    1.62  measured    1.620 m/s²  (0.00%)  616 airborne runs | per-frame keys: 1.620
   JUPITER  target   24.79  measured   24.790 m/s²  (0.00%)  473 airborne runs | per-frame keys: 24.790
   PLUTO    target    0.62  measured    0.620 m/s²  (0.00%)  801 airborne runs | per-frame keys: 0.620
   SUN      target  274.00  measured  274.000 m/s²  (0.00%)   14 airborne runs (the 3 cm step)
   ASSERT OK: every zone's measured g is within 3% of the planet value
-- 2-zone boundary test (marble flying MOON -> JUPITER)
   frame 11 MOON 1.620 | frame 12 MOON 10.743 (straddles the line) | frame 13 JUPITER 24.645 | frame 14 JUPITER 24.790
-- free fall from 1 m: Pluto 1.796 s · Moon 1.111 · Mars 0.734 · Earth 0.451 · Jupiter 0.284 · Sun 0.085
-- FINISHING ORDER  P1 #7 68.05 s · P2 #2 +0.21 · P3 #1 +0.37 · #4 · #3 · #6 · #5 · DNF #8 (Jupiter)
-- leader timing: Moon 15.8, Jupiter 30.2, Pluto 42.0, Sun 60.3, finish 68.0  [beats 15/30/42/60/~68]
```

The script also prints every marble's zone-entry times. The airborne g comes from the second difference of the baked z positions, using only sub-steps with no track or marble contact. It is exact because the integrator is semi-implicit Euler with a constant g inside a zone.

## The corner fact (√(μ·g·r))

Grip on a flat curve is the friction force μ·m·g. It has to supply the centripetal force m·v²/r, so the top speed is **v_max = √(μ·g·r)**. Mass cancels, and only gravity changes between planets.
- Jupiter: √(24.79 / 9.81) = **1.59× Earth**
- Moon: √(1.62 / 9.81) = **0.41× Earth**
- Sun: 5.3×

In this sim the hairpin's curved walls play the role of μ. A marble rides up the wall to the angle where tan θ = v²/(g·r), so higher g keeps it lower on the wall. On Jupiter only the fastest marbles (≳ 5 m/s on entry) top the 38° lip. The same corner on Earth would hold only about 1/1.6 of that speed.

## Render time

- **Physics bake:** about 4 s. **Scene build + keyframing:** about 20 s.
- **Eevee:** I could not test it here (headless container, no GPU/EGL). On a typical desktop GPU, expect about 0.4–1 s/frame for `--preview` (about 15–35 min for 2,250 frames) and about 1.5–3 s/frame for `--render` at 64 samples (about 1–2 h).
- **Cycles CPU (what I could test):** 270×480 at 16 samples took about 4 s/frame on 4 cores.

## Known limitations

- The marbles rotate but have no real spin, so there is no curling off walls.
- Marbles that are OUT only collide with the flat ground, not with lower track sections. The hairpin's outside is clear, so this never shows in the default race.
- The rolling-drag term is a tuning device, described above. Real marble losses are smaller, and a real track would need different slopes.
- Reordering `zone_order` moves each planet's features with it (the hairpin stays on Jupiter, and so on), but the pacing is then no longer tuned to the beat sheet.
- Some in-world arch signs pass close to the chase camera for a few frames.
