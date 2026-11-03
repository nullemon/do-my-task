# 03 · Can it clear the canyon?

The same car drives off the same ramp at the same speed over a 22 m canyon, once per planet. Gravity decides who wins:

| Planet | g (m/s²) | Range | Airtime | Result |
|---|---|---|---|---|
| Pluto | 0.62 | 328 m | 17.0 s | **LOST IN SPACE 🚀**: climbs out of the top of the frame |
| Moon | 1.62 | 129 m | 6.7 s | **LOST IN SPACE 🚀**: sails off frame, 9.9 m up at peak |
| Mars | 3.71 | 59 m | 3.1 s | **OVERSHOT ✗**: flies over the 20 m landing mesa and drops into the abyss behind it |
| Earth | 9.81 | 25.2 m | 1.3 s | **CLEARED ✓**: lands 3 m past the rim, suspension bounce, brakes to a stop |
| Jupiter | 24.79 | 12.1 m | 0.6 s | **FELL SHORT ✗**: nose hits the far wall 6.2 m below the rim, falls 28 m to the floor |
| Sun | 274 | – | – | **CRUSHED**: at 28 g it is flattened at the foot of the ramp and grinds to a halt in 1.3 m |

**The numbers.** The launch is 20 m/s (72 km/h) off a 15° ramp with a 1.6 m lip, over a 22 m gap with a 20 m mesa on the far side. The range is `vx·t` with `t = (vz + √(vz² + 2gH)) / g`. I chose these values so that Earth *just* makes it (3 m to spare) and each planet ends up in a different category. One extra category, **OVERSHOT**, is for Mars: it misses the mesa but isn't a space flight. The verdict comes from the maths, so changing the values in CONFIG changes the outcomes. The Sun is a special case: v² < 2gH, so the car couldn't even climb a 1.6 m ramp. Running the script prints this table, and it also prints the measured simulation values next to the exact predictions.

## Run
- In Blender: Scripting tab → open `canyon_jump_planets.py` → ▶. You get scenes `03_Pluto` … `03_Sun`. Switch scenes and press play. Re-running the script replaces everything it made (all names start with `CJ_`).
- `blender -b -P canyon_jump_planets.py -- --preview` renders 8 low-res Cycles stills to `renders/canyon-jump/preview/`.
- `blender -b -P canyon_jump_planets.py -- --render` renders every planet to `renders/canyon-jump/NN_Planet/frame_####.png`.

## CONFIG knobs
- `PLANETS`, `GRAVITY`
- `LAUNCH_SPEED`, `RAMP_ANGLE_DEG`, `RAMP_HEIGHT`, `GAP`, `LANDING_LENGTH`, `CANYON_DEPTH`
- `CRUSH_G`: the gravity above which the car is crushed
- `SPACE_AIRTIME`: a miss with more airtime than this counts as LOST IN SPACE
- `LAUNCH_TIME`
- `CAR_MODEL_PATH`: your own `.glb/.gltf/.fbx/.blend` car, which replaces the procedural one
- `CAR_MODEL_FORWARD`: which axis the nose points along
- `CAR_MODEL_LENGTH`: the car is rescaled to this length
- `CAR_WHEEL_KEYWORDS`: objects with these words in their names spin as wheels
- `CAR_COLOR`
- `FPS`, `SECONDS` (8), `RESOLUTION` (1080×1920), `ENGINE` (EEVEE/CYCLES), samples, `MOTION_BLUR`, `OUTPUT_DIR`, `HOOK_TEXT`

## Real vs faked
- **Real:** the flight is exact ballistic motion under each planet's real gravity. It is not rigid-body physics. The script integrates it deterministically, keyframes it on every frame, and it matches the closed form to within 1 cm. The landing, wall-hit and floor-hit points come from that same trajectory. The Sun's 0.9·g friction slide is also real.
- **Faked (artistic):**
  - The in-air pitch: the nose follows the trajectory with a lag.
  - The roll wobble.
  - The suspension bounce on landing, which is a damped spring.
  - The brake distance on Earth.
  - The Jupiter and Sun crushing. A lattice with shape keys `Squash`/`Pancake` handles sag, bottoming out, the slight squash after the wall and floor hits, and the Sun pancake. On the Sun, the car physically couldn't even support itself; the drama of collapsing at the ramp is staged.
  - The camera shake.
- **Imported cars:** they are normalised and get the same lattice. Their wheels only spin if their object names match the keywords. I tested this with an exported glb.

## Render time
- Preview: about 15–25 s per still at 270×480 with 24 samples, about 2 min in total on 4 CPU cores.
- Full Eevee render: 6 × 240 frames at 1080×1920. Expect roughly 0.5–2 s per frame on a GPU, so about 15–45 min for all planets.
- Cycles: about 20–60 s per frame on a GPU.

`preview/` contains a key-moment still per planet, plus the end cards for Earth and the Sun.
