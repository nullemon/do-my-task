"""Sound for "What If Our Moon Was as Big as Other Moons Are to Their Planets?": voice chain; an orchestral pad (detuned,
filtered saw "strings" plus a soft brass fifth) per moon -- thin, high and quiet for the tiny ones, darkest for Phobos,
then a huge widening chord for Charon; a whoosh + implosion sweep + sub thump + shimmer bloom at every swap; a sonar
ping on each tiny moon's pointer ring; a long riser into the Charon moonrise with a big hit, a second hit on "double
world"; a white-out riser and a low hit as today's Moon returns. Ducked under the voice, two-pass loudnorm to
-14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/moon-ratios.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per moon: (root Hz, intervals, filter cutoff Hz, level)
CHORDS = {"moon": (110.0, (0, 7, 12, 16, 19), 1000, 0.85), "pho": (98.0, (0, 7, 12, 15), 600, 0.55),
          "gan": (103.8, (0, 7, 12, 15, 19), 800, 0.6), "tit": (110.0, (0, 7, 12, 15, 19), 900, 0.65),
          "tri": (116.5, (0, 7, 12, 15, 19, 22), 1000, 0.7), "cha": (130.8, (0, 7, 12, 16, 19, 24, 28), 3000, 1.2),
          "end": (110.0, (0, 7, 12, 16, 19, 24), 1200, 0.85)}


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


def ping(t0, f=1760.0, gain=0.12, pan=0.6):
    """sonar ping: a bright sine with a soft echo"""
    out = np.zeros((N, 2))
    for k, (dt, g) in enumerate(((0.0, 1.0), (0.32, 0.35), (0.64, 0.12))):
        a = int((t0 + dt) * SR); n = int(0.9 * SR)
        if a + n >= N: break
        x = np.sin(2 * np.pi * f * np.arange(n) / SR) * np.exp(-np.arange(n) / SR / 0.22) * g * gain
        out[a:a + n, 0] += x * (1 - pan) * 2; out[a:a + n, 1] += x * pan * 2
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "moon")] + list(S.SWAPS)
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, cut, lev = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.3, 1), (te - 0.4, 1.1), (te - 0.02, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.4, 1.1), (te - 0.02, 0), (S.DUR + 1, 0)])
        if k == "cha": e = A.env(N, [(0, 0), (ts - 0.05, 0), (ts + 1.8, 1), (te - 0.4, 1.15), (te - 0.02, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.4, 1), (S.DUR - 0.5, 1), (S.DUR, 0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        if k == "end": continue
        big = k == "cha"
        bed += whoosh(ts, 0.55 if not big else 1.2, seed=40 + i, gain=0.55 if not big else 0.8)
        bed += A.thump(N, ts, 0.8 if not big else 1.6)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.30 if not big else 0.5)
    for k in S.SMALL:                                                   # sonar pings on the pointer rings
        t0 = S.T_SW[k] + 0.3
        bed += ping(t0, {"pho": 2093.0, "gan": 1760.0, "tit": 1568.0, "tri": 1975.5}[k], 0.10)
    bed += ping(S.wt("pho_b", "BARELY"), 2637.0, 0.07, 0.4)
    bed += A.shimmer(N, 0.3, S.T_SW["pho"] - 0.3, seed=61, gain=0.10)        # moonlight sparkle
    # Charon: a long riser into the moonrise, a big hit, then "double world"
    bed += A.riser(N, S.T_SW["cha"] - 1.6, S.T_SW["cha"], seed=66) * 0.7
    bed += A.hit(N, S.T_SW["cha"], gain=0.45, root=41.2)
    bed += A.shimmer(N, S.T_SW["cha"] + 0.3, S.T_WO0, seed=71, gain=0.16)
    bed += A.thump(N, S.T_DOUBLE, 1.2)
    bed += A.hit(N, S.T_DOUBLE, gain=0.30, root=55.0)
    bed += bloom_swell(S.T_DOUBLE, 72, 0.40)
    # white-out -> today's Moon
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.1
    bed += A.hit(N, S.T_BACK, gain=0.45, root=55.0)
    bed += A.shimmer(N, S.T_BACK + 0.3, S.DUR - 0.2, seed=73, gain=0.08)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "moon-ratios.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
