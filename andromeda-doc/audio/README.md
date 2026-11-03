# Andromeda — sound, subtitles and final assembly

## Voice-over
- **TTS:** Kokoro-82M (v1.0) via `kokoro-onnx` 0.6.1, running fully offline on CPU (ONNX Runtime).
  Model files `kokoro-v1.0.onnx` + `voices-v1.0.bin` downloaded once from the GitHub release
  `thewh1teagle/kokoro-onnx/model-files-v1.0` into `/home/user/tts-models/`. Venv: `/home/user/ttsenv`.
- **Voice:** `am_michael` (American male, median F0 ≈ 120 Hz), speed 0.94 for a calm documentary pace.
  Auditioned: am_michael, am_onyx, am_fenrir, bm_george, bm_lewis, bm_fable, af_heart, bf_emma.
- Pronunciation fixes: "1912" → "nineteen twelve"; Slipher → "SLY-fer"; Milkomeda forced to
  /mɪlkˈɑːmɪdə/ (milk-OM-eh-da, like Andromeda) — espeak's default was "MILK-oh-mda".
- Each line of PLAN.md is its own clip (`vo_raw/line_XX.wav`) placed at chapter start + offset.
  Only one adjustment was needed: line 13 (CH2 37.5 s, the long Hubble/Gaia sentence) is sped up
  ×1.010 to keep ≥ 0.6 s before "So let's follow…" at 50.0 s. No line was moved; nothing overlaps.
  Final timings: `placement.json`.
- Processing: 70 Hz high-pass, light EQ, 3:1 compression (ffmpeg `acompressor`), short room reverb (16 % wet).

## Music / sound bed (numpy, 48 kHz stereo, 240 s)
Additive detuned pads + low drone in D (D minor world), 4.5 s hall reverb.
- CH1: drone fades in from silence, open Dm(add9) → Dm → Bbmaj7, high air.
- CH2: darker (Gm, Bb, Ab colour for the uncertainty), dominant A into CH3.
- CH3: wider, brighter Dm → Bbmaj7 → F → Gm, a slow beating cluster as the Milky Way warps.
- Sub swells (≈37 Hz) peaking at 1:00, 2:00, 3:00.
- CH4 0–20 s: formant "aah" choir shimmer (D major/lydian colour) + glassy sparkle pings for the starburst.
- CH4 20–56 s: dark resolution Bb → Gm7 → low Dm, low "oo" choir under Milkomeda.
- Title card 3:56–4:00: final low swell decays; the bed is fully silent from 3:59.6.
- Bed is sidechain-ducked 8 dB under the voice (look-ahead, ~150 ms attack, ~400 ms release).

## Master
`andromeda_mix.wav` — 48 kHz / 24-bit stereo, 240.0 s, two-pass `loudnorm` (linear) → **−14 LUFS
integrated, true peak ≈ −1.4 dBTP**. Stems: `voice_48k.wav`, `bed_48k.wav`.

## Subtitles
`../andromeda.srt` — generated from the actual placed narration timings (long lines split into two cues,
≤ 44 chars per row). Also muxed into both MP4s as a soft (off-by-default) English `mov_text` track.

## Final assembly — `assemble.sh`
Waits until `ch1..ch4.mp4` each probe as 60.0 s / 1440 frames and their size is stable, concatenates them
(stream copy, 240 s), adds a subtle vignette + fine temporal luma grain, muxes the mix and writes:
- `../andromeda-1080p.mp4` — 1920×1080, 24 fps, x264 CRF 18 (preset slow), AAC 256 kb/s, +faststart.
- `../andromeda-4k.mp4` — **3840×2160 lanczos UPSCALE of the 1080p render** (not native 4K detail),
  x264 CRF 20 preset medium, AAC 256 kb/s, +faststart.

Rebuild everything:
```
/home/user/ttsenv/bin/python gen_voice.py am_michael 0.94   # voice clips
/home/user/ttsenv/bin/python mix.py                          # bed, ducking, loudness, SRT
setsid nohup bash assemble.sh > assemble.log 2>&1 < /dev/null &
```
