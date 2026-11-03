# 05 · Gravity synced to music

A warm living room (sofa, sideboard, floor lamp, pendant, rug, window glow) with **38 active rigid bodies**:
books, mugs, balls, cushions, vinyl records, a speaker, two plants, a pouf and even the coffee table.
The script analyses a song and drives gravity with it:

| music | gravity | HUD |
|---|---|---|
| quiet | 0.62 m/s² **upwards** (Pluto, reversed), then a gentle sink, so things drift up and hover | `PLUTO 0.62 m/s²` · FLOATING / DRIFTING |
| loud, sustained | down, easing towards 9.81 (Earth) | `MARS 3.71`, `EARTH 9.81` … |
| each strong beat | Jupiter, 24.79 m/s² down, for 7 frames | `JUPITER 24.79 m/s²` · BEAT! |
| the big drop (a hard hit after ≥1.5 s without hits) | Sun, 274 m/s² down, for 4 frames | `SUN 274.0 m/s²` · BEAT DROP! |

The song goes into the Video Sequencer as a sound strip, so playback (AV-sync) and the MP4 have the music.
The camera pushes in slowly and shakes on hits.

## Run
- **In Blender (4.2 – 5.x):** Scripting tab → open `gravity_music_sync.py` → set `AUDIO_PATH` → Run. It builds the `05_GravitySync` scene, bakes the physics and prints the analysis. Then press play. Running it again replaces the scene.
- **Headless:** `blender -b -P gravity_music_sync.py -- --render [--audio song.wav] [--seconds 25] [--engine CYCLES]`
- **Preview stills:** `blender -b -P gravity_music_sync.py -- --preview` gives 5 Cycles stills at 270x480 in `renders/gravity_music_sync/preview/`.
- **No audio set:** the script writes a 20 s demo track, `gms_demo_track.wav`, next to itself and uses that. The track goes: pad → hit → pad + soft riser → DROP → five half-time kicks → pad outro.
- **MP3:** Blender's built-in decoder (audaspace) loads MP3, FLAC and OGG for both the analysis and the sequencer. This was tested with MP3. If it fails, convert with `ffmpeg -i song.mp3 -ac 2 -ar 44100 song.wav`. Use `AUDIO_OFFSET_S` to start at the chorus.

Output: `renders/gravity_music_sync/05_GravitySync/gravity_music_sync.mp4` (H.264 + AAC). If FFmpeg is missing, you get PNG frames instead.

## CONFIG knobs
- **Audio and timing:** `AUDIO_PATH`, `AUDIO_OFFSET_S`, `SECONDS`, `FPS`, `RESOLUTION`, `ENGINE` (EEVEE/CYCLES).
- **Planet levels:** `QUIET_PLANET`, `LOUD_PLANET`, `BEAT_PLANET`, `DROP_PLANET`, `HUD_PLANETS`.
- **Loudness mapping:** `QUIET_LEVEL` and `LOUD_LEVEL`, plus `DYNAMIC_RANGE_DB` (how far below the loudest part counts as "quiet").
- **Beat detection:** `ONSET_SENSITIVITY`, `MIN_BEAT_GAP_S` and `MIN_ONSET_FRACTION` control which onsets count as hits. `DROP_STRENGTH` and `DROP_AFTER_GAP_S` decide which hits get Sun gravity.
- **Hit and float timing:** `BEAT_HOLD_FRAMES`, `DROP_HOLD_FRAMES`, `SETTLE_FRAMES`, `FLOAT_PERIOD_S`, `FLOAT_SINK`.
- **Physics and camera:** `SUBSTEPS`/`SOLVER_ITERATIONS` (30/30), `LINEAR_DAMPING`, `TURBULENCE`, `CAMERA_SHAKE`, `PUSH_IN`.

If a song makes everything Sun or nothing float, adjust `DROP_STRENGTH` and `DYNAMIC_RANGE_DB` first.

## How it works / real vs. faked
- **Analysis (numpy only):**
  - Loudness: an RMS envelope per video frame, with fast attack and 0.12 s release.
  - Hits: log-spectral flux with the kick band (<180 Hz) weighted ×3, an adaptive threshold (local mean + k·std) and a minimum gap. A hit's strength is the bass energy in the 120 ms after it.
- **Gravity:** the script keys `scene.gravity` on every frame. A test confirmed that the Bullet rigid-body solver reads the animated gravity during the bake, so no force-field trick is needed. A weak turbulence field, keyed to the quiet parts, adds drift.
- **Real:** all gravity magnitudes are real planet values, and the rigid-body motion is fully simulated and baked.
- **Faked or artistic:**
  - Gravity pointing *up* in quiet parts is not physical, and neither is switching planets mid-song.
  - Linear damping of 0.45 stands in for "air" so the floating stays gentle.
  - An invisible glass wall plus the ceiling keep everything inside the room.
  - The sofa, sideboard and lamp are static colliders.

## Measured (demo track, preview run)
Hits found: 4.48 s, 10.99 s (Sun), 12.39, 13.43, 14.49, 15.53 and 16.59 s. That is all 7 hits in the demo track and no false ones.

| time | mean height | gravity |
|---|---|---|
| 0.0 s | 0.42 m | +0.62 (float) |
| 2.8 s | 2.07 m | −0.22 (drift) |
| 4.47 s → +6 frames | 1.83 → 1.19 m | −24.79 Jupiter |
| 4.8 s | 0.65 m | −9.4 |
| 7.8 s | 1.26 m | float |
| 11.00 s → +3 frames | 1.16 → 0.24 m | **−274 Sun** |
| 13.4 s / 13.6 s | 0.26 / 0.18 m | float hop / Jupiter |
| 19.6 s | 0.73 m | float outro |

Between kicks, objects only hop about 8 cm, because the kicks are just 1 s apart. All objects stayed inside the room.

## Render time (estimates)
- **Bake:** about 4 s for 600 frames.
- **Eevee, 1080x1920:** about 1–3 s per frame on a GPU, so 10–30 min for 20 s.
- **Cycles, 96 samples:** about 20–60 s per frame on a GPU, and several hours on a CPU.
- **`--preview`:** about 1.5 min on 4 CPU cores.

## Preview
`preview/01_float…` (floating), `02_before_drop`, `03_after_drop` (Sun slam), `04_float_between_kicks`, `05_outro_float`.
