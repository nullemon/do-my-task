"""BATCH4 kit (../BATCH4.md): clean, voice-first sound + mux for the batch-4 Shorts. New module; nothing else in lib/
is changed.
  generate(LINES, out_dir)            Kokoro 0.7 am_michael + 0.3 am_onyx @ 0.86, one TTS call per phrase, word timings
                                      (lib.v3_kit.generate, unchanged)
  dry_voice(PL, vo_dir, N)            the phrases placed on the timeline, mono 48 kHz, NO post chain (no pitch, no echo)
  make_mix(PL, vo_dir, dur, swaps, key, out_wav)
                                      lib.mix_clean: clean_voice(dry) -> mix(voice, dur, swaps, key). Nothing else is added.
                                      Also measures the music + whoosh bed alone (voice muted) against the full mix.
  encode(video, wav, srt, out_mp4)    mux, AAC 192k, soft subtitles, no -shortest; measures LUFS / dBTP on the final mp4
"""
import os, re, subprocess
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from . import mix_clean as MC

SR = 48000


def generate(LINES, out):
    from .v3_kit import generate as g
    g(LINES, out)


def dry_voice(PL, vo_dir, N):
    dry = np.zeros(N)
    for l in PL:
        x, sr = sf.read(os.path.join(vo_dir, f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(0, N - s)]
    return dry / (np.abs(dry).max() + 1e-9) * 0.7


def lufs(x):
    """integrated loudness (LUFS) + true peak (dBTP) of a float array via ffmpeg ebur128"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.wav"); sf.write(p, x, SR, subtype="FLOAT")
        return measure(p)


def measure(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    return I, tp


def bed_check(voice, dur_s, swaps, key):
    """the same stages as mix_clean.mix() before its loudness normaliser: -> (LUFS full, LUFS bed alone, difference).
    The normaliser is a common gain on both, so the difference is the bed-vs-mix margin."""
    n = int(round(dur_s * SR)); v = np.zeros(n); v[: min(n, len(voice))] = voice[:n]
    v = v / (np.sqrt(np.mean(v[np.abs(v) > 1e-4] ** 2)) + 1e-9) * 0.1
    pad = MC._ff(MC._pad(n, key), "lowpass=f=1800,highpass=f=80"); pad = pad.mean(1) if pad.ndim > 1 else pad
    pad = pad[:n] / (np.sqrt(np.mean(pad ** 2)) + 1e-9) * 0.1 * 10 ** (-26 / 20)
    from scipy.signal import fftconvolve
    env = fftconvolve((np.abs(v) > 0.01).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    pad *= 10 ** (-8 * np.clip(env * 4, 0, 1) / 20)
    wh = np.zeros(n)
    if swaps:
        w = MC._ff(MC._whoosh(n, swaps), "bandpass=f=1800:w=2500,lowpass=f=6000"); w = w.mean(1) if w.ndim > 1 else w
        wh = w[:n] / (np.abs(w).max() + 1e-9) * (np.abs(v).max() * 10 ** (-26 / 20))   # as mix_clean (15 Nov update)
    full = np.stack([v + pad + wh, v + pad * 0.96 + wh], 1); bed = np.stack([pad + wh, pad * 0.96 + wh], 1)
    If, _ = lufs(full); Ib, _ = lufs(bed)
    return If, Ib, If - Ib


def make_mix(PL, vo_dir, dur, swaps, key, out_wav):
    N = int(round(dur * SR))
    v = MC.clean_voice(dry_voice(PL, vo_dir, N))
    y = MC.mix(v, dur, swaps=list(swaps), key=key)
    t = np.arange(len(y)) / SR                                          # 30 ms in, 0.35 s out (no click at the loop point)
    y = y * (np.clip(t / 0.03, 0, 1) * np.clip((dur - t) / 0.35, 0, 1))[:, None]
    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    sf.write(out_wav, y.astype(np.float32), SR, subtype="FLOAT")
    If, Ib, d = bed_check(v, dur, swaps, key)
    I, tp = measure(out_wav)
    print(f"mix {I:.1f} LUFS {tp:.1f} dBTP | bed alone {Ib:.1f} vs full {If:.1f} (pre-norm) -> bed is {d:.1f} dB under the mix")
    return dict(I=I, tp=tp, bed_db=d)


def encode(video, wav, srt, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    def run(gain_db):
        af = f"volume={gain_db:.2f}dB" if gain_db else "anull"
        subprocess.run(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-i", srt, "-map", "0:v", "-map", "1:a",
                        "-map", "2:s", "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-c:s", "mov_text",
                        "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", out], check=True)
        return measure(out)
    g = 0.0; I, tp = run(g)
    while tp > -1.5 and g > -1.5:                                       # AAC overshoot: trim the gain until <= -1.5 dBTP
        g -= max(0.2, tp + 1.5 + 0.1); I, tp = run(g)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out], capture_output=True, text=True)
    d = float(r.stdout.strip())
    print(f"final {out}: {d:.2f} s, {I:.1f} LUFS, {tp:.1f} dBTP (trim {g:.1f} dB)")
    return dict(dur=d, I=I, tp=tp)
