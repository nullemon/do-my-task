"""Sound for "What If Comets Passed as Close as the Moon?": voice chain; a filtered saw-string pad that steps up in key
and opens its filter with every comet; a whoosh + implosion sweep + sub boom at every swap and a bright shimmer as each
comet blooms in; an airy hiss (solar-wind 'tail' noise) under the tails, a crackle-pop for each 67P outburst, a big
swell for McNaught; a white-out riser and a low hit as the Moon returns. Ducked under the voice, two-pass loudnorm to
-14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/comet-close.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per body: (root Hz, intervals, filter cutoff Hz, level) -- steps upward, opening up towards Jupiter
CHORDS = {"moon": (110.0, (0, 7, 12, 16, 19), 900, 0.8), "halley": (116.5, (0, 7, 12, 14, 19), 1300, 0.9),
          "hb": (130.8, (0, 7, 12, 16, 19, 23), 1800, 1.0), "neo": (146.8, (0, 7, 12, 16, 21), 1700, 0.95),
          "duck": (138.6, (0, 5, 12, 17), 1200, 0.85), "mcn": (98.0, (0, 7, 12, 16, 19, 24, 28), 3200, 1.25)}


def saw(f, n, seed):
    r = np.random.default_rng(seed); ph = r.uniform(0, 1)
    vib = 1 + 0.003 * np.sin(2 * np.pi * r.uniform(4.5, 5.5) * np.arange(n) / SR + r.uniform(0, 6))
    p = (ph + np.cumsum(f * vib) / SR) % 1.0
    return 2 * p - 1


def strings(root, iv, cut, seed):
    x = np.zeros((N, 2)); r = np.random.default_rng(seed)
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        for c in range(2):
            for v in range(2):
                x[:, c] += saw(f * (1 + r.uniform(-0.004, 0.004)), N, seed * 31 + k * 7 + c * 3 + v) * (0.5 if k == 0 else 0.32)
    x = A.lp(x, cut, 2)
    brass = np.zeros(N)
    for s in (0, 7, 12):
        brass += saw(root * 2 ** (s / 12), N, seed + 500 + s) * 0.25
    brass = A.lp(brass, cut * 0.6, 2)
    return (x + brass[:, None] * 0.6) * 0.025


def whoosh(t1, dur=0.6, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    f = 900 * (60 / 900) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bloom_swell(t0, seed, gain=0.4):
    sh = A.shimmer(N, t0, min(t0 + 1.6, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + 1.6, 0), (S.DUR, 0)])[:, None] * gain


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "moon")] + [(ts, "moon" if k == "moon2" else k) for ts, k in S.SWAPS]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, cut, lev = CHORDS[k]
        if i == len(seq) - 1: root, iv, cut, lev = 110.0, (0, 7, 12, 16, 19), 900, 0.7
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.3, 1), (te - 0.4, 1.1), (te - 0.02, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.4, 1.1), (te - 0.02, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.4, 1), (S.DUR - 0.5, 1), (S.DUR, 0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        big = k in ("hb", "mcn")
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.3 if big or k == "moon2" else 0.9)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35 if k != "moon2" else 0.6)
    bed += A.shimmer(N, 0.3, S.T_SW["halley"] - 0.3, seed=61, gain=0.10)                    # moonlight sparkle
    r = np.random.default_rng(62)
    hiss = np.stack([A.bp(r.standard_normal(N), 2500, 9000) for _ in range(2)], 1) * (1 + 0.4 * np.sin(2 * np.pi * 0.23 * tt))[:, None]
    bed += hiss * 0.05 * A.env(N, [(0, 0), (S.T_SW["halley"], 0), (S.T_SW["halley"] + 1.5, 1), (S.T_BACK - 0.05, 1.3), (S.T_BACK, 0), (S.DUR, 0)])[:, None]
    for i, tb in enumerate(S.OUTBURSTS):                                                    # 67P outbursts
        bed += A.thump(N, tb, 0.6) + A.shimmer(N, tb, tb + 1.0, seed=70 + i, gain=0.25) * A.env(N, [(0, 0), (tb, 0), (tb + 0.03, 1), (tb + 1.0, 0), (S.DUR, 0)])[:, None]
    tm = S.T_SW["mcn"]
    hum = A.drone(N, root=36.7, seed=64, bright=0.25) * 1.4
    bed += hum * A.env(N, [(0, 0), (tm, 0), (tm + 1.5, 0.9), (S.T_BACK - 0.05, 1.4), (S.T_BACK, 0), (S.DUR, 0)])[:, None]
    bed += A.riser(N, tm - 0.9, tm, seed=66) * 0.6
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.1
    bed += A.hit(N, S.T_BACK, gain=0.45, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "comet-close.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
