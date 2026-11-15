"""Sound for this Short, BATCH4 clean-audio rules: lib/mix_clean.py ONLY (clean_voice + mix: the soft pad and its gentle
whoosh at each swap; nothing else), plus the SRT. Also the BATCH4 listen-check: the loudness of the music+whoosh bed alone
(voice muted) vs the full mix, measured on the same stems mix_clean builds (same gains, before the common loudnorm).
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, SCR/audio/bed_check.txt, ../out/<name>.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
from scipy.signal import resample_poly, fftconvolve
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib import mix_clean as MC
from lib.v3_kit import measure

NAME = os.path.basename(os.path.dirname(HERE))
KEY = "D"
OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = MC.SR


def dry_voice(N):
    dry = np.zeros(N)
    for l in S.PL:
        x, sr = sf.read(os.path.join(S.SCR, "vo", f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(N - s, 0)]
    return dry / (np.abs(dry).max() + 1e-9) * 0.7


def stems(voice, dur_s, swaps, key):
    """the exact voice / bed stems of mix_clean.mix (15 Nov update: fftconvolve ducking, whoosh -26 dB) before its loudnorm
    (copied arithmetic, for the bed check only)"""
    n = int(round(dur_s * SR)); v = np.zeros(n); v[: min(n, len(voice))] = voice[:n]
    v = v / (np.sqrt(np.mean(v[np.abs(v) > 1e-4] ** 2)) + 1e-9) * 0.1
    pad = MC._ff(MC._pad(n, key), "lowpass=f=1800,highpass=f=80"); pad = pad.mean(1) if pad.ndim > 1 else pad
    pad = pad[:n] / (np.sqrt(np.mean(pad ** 2)) + 1e-9) * 0.1 * 10 ** (-26 / 20)
    env = fftconvolve((np.abs(v) > 0.01).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    pad *= 10 ** (-8 * np.clip(env * 4, 0, 1) / 20)
    w = MC._ff(MC._whoosh(n, swaps), "bandpass=f=1800:w=2500,lowpass=f=6000"); w = w.mean(1) if w.ndim > 1 else w
    wh = w[:n] / (np.abs(w).max() + 1e-9) * (np.abs(v).max() * 10 ** (-26 / 20))
    return np.stack([v, v], 1), np.stack([pad + wh, pad * 0.96 + wh], 1)


def main():
    N = int(round(S.DUR * SR)); tt = np.arange(N) / SR
    v = MC.clean_voice(dry_voice(N))
    swaps = [ts for ts, _ in S.SWAPS]
    out = MC.mix(v, S.DUR, swaps=swaps, key=KEY)
    out = out * (np.clip((S.DUR - tt) / 0.4, 0, 1) * np.clip(tt / 0.03, 0, 1))[:, None]       # click-free ends only
    p = os.path.join(OUT, "mix.wav"); sf.write(p, out.astype(np.float32), SR, subtype="FLOAT")
    I, tp = measure(p); print(f"mix.wav {I:.1f} LUFS, {tp:.1f} dBTP")
    # ---- bed check (voice muted), same stems / gains as mix_clean
    vs, bed = stems(v, S.DUR, swaps, KEY)
    sf.write(os.path.join(OUT, "_full.wav"), (vs + bed).astype(np.float32), SR, subtype="FLOAT")
    sf.write(os.path.join(OUT, "_bed.wav"), bed.astype(np.float32), SR, subtype="FLOAT")
    If, _ = measure(os.path.join(OUT, "_full.wav")); Ib, tb = measure(os.path.join(OUT, "_bed.wav"))
    os.remove(os.path.join(OUT, "_full.wav")); os.remove(os.path.join(OUT, "_bed.wav"))
    msg = f"bed alone {Ib - If:+.1f} dB vs full mix (integrated LUFS; bed {Ib:.1f}, full {If:.1f} before the common loudnorm); bed sample peak {tb:.1f} dBFS"
    print(msg); open(os.path.join(OUT, "bed_check.txt"), "w").write(msg + "\n")
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", f"{NAME}.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
