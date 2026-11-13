"""Sound for "What If We Lived Inside a Star Cluster?": voice chain, a chord pad that changes key and colour per sky
(quiet today -> airy blue Pleiades -> warm Hyades -> golden Omega Centauri -> huge galactic-centre chord), a whoosh + sub
thump + shimmer bloom at every swap, counter ticks as the "brighter than Sirius" readout counts up, a twinkle shimmer bed
that thickens with the star count, a white-out riser and a hit back to the quiet sky. Ducked under the voice, two-pass
loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/star-clusters.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

CHORDS = {"today": (220.0, (0, 7, 12, 16), 0.25), "pleiades": (261.6, (0, 4, 7, 11, 14, 19), 0.9),
          "hyades": (196.0, (0, 4, 7, 9, 12), 0.5), "omega": (174.6, (0, 4, 7, 11, 14, 16, 21), 0.75),
          "nsc": (130.8, (0, 7, 12, 16, 19, 24, 28), 1.0)}
DENS = {"today": 0.15, "pleiades": 0.35, "hyades": 0.3, "omega": 0.8, "nsc": 1.0}


def chord(root, iv, bright, seed):
    r = np.random.default_rng(seed); x = np.zeros((N, 2))
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        a = (0.5 if k == 0 else 0.30) * (1 if f < 600 else bright)
        for c in range(2):
            det = 1 + r.uniform(-0.002, 0.002)
            x[:, c] += a * np.sin(2 * np.pi * f * det * tt + r.uniform(0, 6.28)) * (1 + 0.25 * np.sin(2 * np.pi * r.uniform(0.1, 0.3) * tt))
    air = np.stack([A.bp(r.standard_normal(N), 1500, 7000) for _ in range(2)], 1) * 0.05 * bright
    return (x + air) * 0.05


def whoosh(t1, dur=0.6, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    f = 300 * (1800 / 300) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.25)[:, None]
    return out * gain


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "today")] + S.SWAPS
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR + 1
        root, iv, br = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0.0), (S.DUR + 2, 0)])
        if i == 0: e = A.env(N, [(0, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 2, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR + 2, 1)])
        bed += chord(root, iv, br, 10 + i) * e[:, None] * (1.0 + 0.6 * DENS[k])
        # twinkle shimmer: thicker with more stars
        bed += A.shimmer(N, ts + 0.1, min(te, S.DUR) - 0.05, seed=30 + i, gain=0.08 + 0.18 * DENS[k]) * e[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        if k == "today": continue
        bed += whoosh(ts, 0.6, seed=40 + i, gain=0.5 + 0.3 * DENS[k])
        bed += A.thump(N, ts, 0.9 + 0.6 * DENS[k])
        sh = A.shimmer(N, ts, min(ts + 1.6, S.DUR - 0.1), seed=50 + i, gain=1.0)
        bed += sh * A.env(N, [(0, 0), (ts, 0), (ts + 0.05, 1), (ts + 1.6, 0), (S.DUR, 0)])[:, None] * 0.35
        bed += A.ticks(N, ts + 0.3, ts + 1.2, rate=14.0, gain=0.07, accel=1.5)
    # target ring pings on "Now imagine..."
    bed += A.ticks(N, S.wt("hook", "NOW") - 0.05, S.T_SW["ple"] - 0.6, rate=1.1, gain=0.10)
    # galactic centre: deep drone under the blaze
    bed += A.drone(N, root=32.7, seed=64, bright=0.3) * 1.0 * A.env(N, [(0, 0), (S.T_SW["nsc"], 0), (S.T_SW["nsc"] + 0.4, 1), (S.T_BACK, 1), (S.T_BACK + 0.1, 0), (S.DUR + 1, 0)])[:, None]
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.2
    bed += A.hit(N, S.T_BACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.3, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "star-clusters.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
