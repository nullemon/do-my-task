"""BATCH4 clean sound for this Short: the voice placed per line (lib.v3_kit word timings), polished ONLY with
lib.mix_clean.clean_voice (no pitch shift, no echo), then lib.mix_clean.mix: its soft pad + gentle whoosh at the swaps.
Nothing else is added. Also writes the SRT and checks the bed (pad + whoosh, voice muted) against the full mix.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/<name>.srt"""
import os, sys, re, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib import mix_clean as MC

NAME = os.path.basename(os.path.dirname(HERE))
KEY = os.environ.get("KEY", "D")
OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = MC.SR


def lufs(x):
    p = os.path.join(OUT, "_m.wav"); sf.write(p, x.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    os.remove(p); return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


def dry_voice(N):
    dry = np.zeros(N)
    for l in S.PL:
        x, sr = sf.read(os.path.join(S.SCR, "vo", f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(N - s, 0)]
    return dry / (np.abs(dry).max() + 1e-9) * 0.7


def main():
    N = int(round(S.DUR * SR))
    swaps = [ts for ts, _ in S.SWAPS]
    v = MC.clean_voice(dry_voice(N))
    y = MC.mix(v, S.DUR, swaps=swaps, key=KEY)
    sf.write(os.path.join(OUT, "mix.wav"), y.astype(np.float32), SR, subtype="FLOAT")
    # bed check: the same mix with the voice muted, at the same gain as the full mix. mix() normalises the voice and
    # loudnorms the sum, so reproduce its internals pre-normalisation and compare the bed alone with the full sum.
    vv = np.zeros(N); vv[: len(v)] = v[:N]
    vv = vv / (np.sqrt(np.mean(vv[np.abs(vv) > 1e-4] ** 2)) + 1e-9) * 0.1
    pad = MC._ff(MC._pad(N, KEY), "lowpass=f=1800,highpass=f=80"); pad = pad.mean(1) if pad.ndim > 1 else pad
    pad = pad[:N] / (np.sqrt(np.mean(pad ** 2)) + 1e-9) * 0.1 * 10 ** (-26 / 20)
    env = np.convolve((np.abs(vv) > 0.01).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    pad *= 10 ** (-8 * np.clip(env * 4, 0, 1) / 20)
    w = MC._ff(MC._whoosh(N, swaps), "bandpass=f=1800:w=2500,lowpass=f=6000"); w = w.mean(1) if w.ndim > 1 else w
    wh = w[:N] / (np.abs(w).max() + 1e-9) * (np.abs(vv).max() * 10 ** (-15 / 20))
    Lf, Lb = lufs(np.stack([vv + pad + wh] * 2, 1)), lufs(np.stack([pad + wh] * 2, 1))
    msg = f"bed (voice muted) {Lb - Lf:+.1f} dB vs full mix  (full {Lf:.1f}, bed {Lb:.1f} LUFS pre-norm)"
    open(os.path.join(OUT, "bedcheck.txt"), "w").write(msg + "\n"); print(msg)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    A.write_srt(os.path.join(HERE, "..", "out", f"{NAME}.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR, "mix", A.SR if False else "", os.path.join(OUT, "mix.wav"))


if __name__ == "__main__":
    main()
