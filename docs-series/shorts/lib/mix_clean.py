"""Clean, voice-first mix for Shorts (USER RULE 15 Nov: the old mixes had far too much music and SFX).

Use THIS for every new Short instead of the per-Short busy mixes.

    from lib.mix_clean import clean_voice, mix
    v = clean_voice(dry_mono_48k)                  # gentle polish only, no echo or reverb
    out = mix(v, dur_s, swaps=[t1, t2, ...], key="D")
    # write out (stereo 48 kHz) and mux; it is already at -14 LUFS, -1.5 dBTP

What it does:
- Voice: highpass 70 Hz, light de-mud, gentle compression, slight presence. No echo, no pitch tricks.
- Music: one soft, slow, warm pad (two sustained chords, low-passed). About 26 dB under the voice and
  ducked a further 8 dB while speech is present.
- Swaps: an optional soft airy whoosh (0.7 s), at least 15 dB under the voice. Nothing else: no booms,
  rumbles, risers or crackles.
"""
import subprocess, tempfile, os
import numpy as np, soundfile as sf

SR = 48000
VOICE_CHAIN = ("highpass=f=70,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1.2:g=1.5,"
               "acompressor=threshold=-22dB:ratio=2.2:attack=8:release=160:makeup=2")
CHORDS = {"D": [(146.83, 220.0, 293.66, 369.99), (130.81, 196.0, 261.63, 329.63)],
          "A": [(110.0, 164.81, 220.0, 277.18), (123.47, 185.0, 246.94, 293.66)]}


def _ff(x, af):
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a.wav"), os.path.join(d, "b.wav")
        sf.write(a, x, SR, subtype="FLOAT")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-af", af, "-ar", str(SR), "-c:a", "pcm_f32le", b], check=True)
        y, _ = sf.read(b)
    return y


def clean_voice(dry):
    """dry: mono float at 48 kHz. Returns the polished mono voice (same length)."""
    y = _ff(dry, VOICE_CHAIN)
    if y.ndim > 1: y = y.mean(1)
    return y[: len(dry)] if len(y) >= len(dry) else np.pad(y, (0, len(dry) - len(y)))


def _pad(n, key):
    t = np.arange(n) / SR; out = np.zeros(n)
    seq = CHORDS.get(key, CHORDS["D"]); seg = 8.0
    for i, s0 in enumerate(np.arange(0, n / SR, seg)):
        ch = seq[i % len(seq)]
        w = np.clip((t - s0) / 2.5, 0, 1) * np.clip((s0 + seg + 2.5 - t) / 2.5, 0, 1)   # 2.5 s crossfades
        for k, f in enumerate(ch):
            out += w * (np.sin(2 * np.pi * f * t + k) + 0.25 * np.sin(2 * np.pi * 2 * f * t)) / (k + 1.5)
    out *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t)                                      # slow breathing
    return out


def _whoosh(n, at):
    rng = np.random.default_rng(7); out = np.zeros(n); L = int(0.7 * SR)
    env = np.sin(np.linspace(0, np.pi, L)) ** 2
    for t0 in at:
        s = int((t0 - 0.35) * SR)
        if s < 0 or s + L > n: continue
        out[s:s + L] += rng.standard_normal(L) * env
    return out


def mix(voice, dur_s, swaps=(), key="D"):
    """voice: mono polished voice at 48 kHz. Returns stereo (N,2) at -14 LUFS / -1.5 dBTP."""
    n = int(round(dur_s * SR)); v = np.zeros(n); v[: min(n, len(voice))] = voice[:n]
    v = v / (np.sqrt(np.mean(v[np.abs(v) > 1e-4] ** 2)) + 1e-9) * 0.1                  # speech RMS ~ -20 dBFS
    pad = _ff(_pad(n, key), "lowpass=f=1800,highpass=f=80")
    pad = pad.mean(1) if pad.ndim > 1 else pad
    pad = pad[:n] / (np.sqrt(np.mean(pad ** 2)) + 1e-9) * 0.1 * 10 ** (-26 / 20)        # -26 dB re speech
    env = np.convolve((np.abs(v) > 0.01).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    duck = 10 ** (-8 * np.clip(env * 4, 0, 1) / 20)
    pad *= duck
    wh = np.zeros(n)
    if swaps:
        w = _ff(_whoosh(n, swaps), "bandpass=f=1800:w=2500,lowpass=f=6000")
        w = w.mean(1) if w.ndim > 1 else w
        pk = np.abs(w).max() + 1e-9; wh = w[:n] / pk * (np.abs(v).max() * 10 ** (-15 / 20))
    st = np.stack([v + pad + wh, v + pad * 0.96 + wh], 1)
    y = _ff(st, "loudnorm=I=-14:TP=-2:LRA=7,alimiter=limit=0.79:level=disabled")
    return y[:n]
