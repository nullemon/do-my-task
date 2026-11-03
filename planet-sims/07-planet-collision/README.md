# 07 · Planet collision (Theia → Moon), SPH

A NASA/Durham-style giant-impact video. Two glowing molten planets collide,
stretch into arms and a spiral tail, splash debris, re-collapse into one
molten ball, and leave a debris disc with a moonlet clump on a wide orbit.

| file | what |
|---|---|
| `collision_sim.py` | the simulation (plain Python + numpy/scipy/numba). Writes the frame cache. |
| `requirements.txt` | `numpy scipy numba` |
| `collision_preview_render.py` | simple Blender preview renderer (glowing spheres + glare). Verification tool. |
| `collision_render.py` | final volumetric look-dev renderer (made by a second agent; same cache). |
| `preview/` | Cycles preview stills |

## Run

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python collision_sim.py                         # theia, CONFIG defaults
venv/bin/python collision_sim.py --scenario theia --n 200000 --hours 24
venv/bin/python collision_sim.py --list                  # presets
venv/bin/python collision_sim.py --bench 50000,200000    # seconds per step on your PC
```
Output: `./cache/<run>/meta.json` + `frame_00000.npz …` (one frame every
`out_every_min` simulated minutes, default 2 → 721 frames for 24 h). Relaxed
planets are cached in `./cache/_bodies/` and reused. Ctrl-C any time: re-running
the same command **resumes** from `cache/<run>/checkpoint.npz` (`--fresh` restarts).

Blender (4.2 – 5.x), preview renderer:
```bash
blender -b -P collision_preview_render.py -- --preview --cache cache/theia   # stills -> preview/
blender -b -P collision_preview_render.py -- --render  --cache cache/theia   # all frames -> renders/collision/
```
or open it in the Scripting tab, set `CACHE_DIR`, Run, press play (a
`frame_change_pre` handler streams the cache; `--render` sets every frame
explicitly before rendering it, so headless renders never repeat frame 1).

### Cache format (shared with the look-dev renderer)
`meta.json`: scenario, n_particles, frame_count, fps_hint, length_unit_km=6371,
time_unit_hours (sim hours per frame), materials {0 earth_core, 1 earth_mantle,
2 impactor_core, 3 impactor_mantle}, bodies, impact (speed, angle, contact time),
temp_mapping. Each `frame_#####.npz`: `pos` (N,3) f32 Earth radii, COM frame ·
`vel` f16 km/s · `u` f32 J/kg · `temp` f32 0..1 (log T between T_cold=2000 K and
T_hot=30000 K, fixed for all frames) · `T_K` rough temperature · `rho` kg/m³ ·
`h` smoothing length (R_E) · `mat` u8 · `absorbed` u8. Particle order is fixed.

## CONFIG knobs (collision_sim.py)
`scenario`, `variant`, `n_particles`, `hours`, `out_every_min`, `n_neighbours`
(60), `theta` (Barnes-Hut 0.6), `courant`, `av_alpha/beta`, `mantle_material`
(granite | basalt), `T_initial_K`, `T_cold_K/T_hot_K`, `relax_time`,
`start_sep_contact`. Preview renderer: `TIME_KEYS` (video s → sim h, default
slow motion around the impact), `VIEW_KEYS` (zoom), `CAM_TILT_DEG`,
`CAM_DRIFT_DEG`, `RADIUS_FACTOR`, `EMISSION`, `GLOW`, `CAPTION`, `ENGINE`.

## Scenarios (real masses, radii come out of the relaxed EOS)
| preset | bodies | impact |
|---|---|---|
| `theia` (default) | proto-Earth 0.90 M⊕ (30 % iron) + Theia 0.10 M⊕ (Mars-like) | v = v_esc ≈ 9.7 km/s, 45° |
| `moon_hits_earth` | Earth 1 M⊕ + Moon 0.0123 M⊕ | v_esc ≈ 11 km/s, 30° |
| `mars_vs_earth` | Earth + Mars 0.107 M⊕ | 1.1 v_esc, 40° |
| `two_earths` | Earth + Earth | v_esc, 35° |
| `earth_into_jupiter` | Earth (SPH) falling into Jupiter (317.8 M⊕, R 11.21 R⊕, fixed softened sphere) from 80 R⊕, periapsis 0.6 R_J → tidal stretching, then swallowed | parabolic |
| `speed_series --variant 0..4` | Theia pair at (v/v_esc, angle) = (1,45) (1.4,45) (2,45) (1,20) (1,65) | |

Only `theia` has been run here. The others need nothing but
`--scenario NAME` (each relaxes its own bodies first, a few minutes at 50k).

RESULTS_PLACEHOLDER
