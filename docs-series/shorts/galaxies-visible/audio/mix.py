"""Sound for "What If Galaxies Were Bright Enough to See?": voice chain; a soft city-night bed (distant traffic hum);
a chord pad that changes key and colour with each galaxy; six bell plinks as the six full Moons line up; a riser on
"what if your eyes could"; whoosh + sub thump + bloom shimmer at every swap; a huge drone for the all-at-once finale;
white-out riser and a deep hit back into the plain city night. Ducked under the voice, two-pass loudnorm to
-14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/galaxies-visible.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per scene: (root Hz, intervals in semitones, brightness)
CHORDS = {"night": (110.0, (0, 7, 12, 14, 19), 0.25), "m31": (130.8, (0, 4, 7, 11, 14, 19), 0.8), "m33": (164.8, (0, 4, 7, 9, 14), 0.9),
          "mc": (98.0, (0, 7, 12, 15, 19, 22), 0.7), "m51": (146.8, (0, 5, 7, 12, 17), 0.75), "all": (87.3, (0, 4, 7, 11, 12, 16, 19), 1.0)}


def chord(root, iv, bright, seed):
    r = np.random.default_rng(seed); x = np.zeros((N, 2))
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        a = (0.5 if k == 0 else 0.28) * (1 if f < 600 else bright)
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
    f = 900 * (60 / 900) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bloom_swell(t0, seed, gain=0.4):
    sh = A.shimmer(N, t0, min(t0 + 1.6, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + 1.6, 0), (S.DUR, 0)])[:, None] * gain


def plink(t0, f, gain=0.25):
    out = np.zeros((N, 2)); n = int(1.2 * SR); k = np.arange(n) / SR; a = int(t0 * SR)
    x = (np.sin(2 * np.pi * f * k) + 0.4 * np.sin(2 * np.pi * 2.76 * f * k) * np.exp(-k / 0.08)) * np.exp(-k / 0.35)
    m = min(n, N - a); out[a:a + m] += x[:m, None]
    return out * gain


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "night")] + [(ts, k) for ts, k in S.SWAPS]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, br = CHORDS[k]
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        elif i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 0.4, 1), (S.DUR, 0)])
        else: e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0.0), (S.DUR + 1, 0)])
        bed += chord(root, iv, br, 10 + i) * e[:, None] * (1.3 if k == "all" else 1.0)
    # city ambience: distant traffic hum, always there
    r = np.random.default_rng(5)
    city = np.stack([A.bp(r.standard_normal(N), 70, 600) for _ in range(2)], 1) * (1 + 0.3 * np.sin(2 * np.pi * 0.07 * tt))[:, None]
    bed += city * 0.10
    # six full Moons line up (one plink each, rising)
    for i in range(6): bed += plink(S.T_MOONS + 0.12 * i, 880 * 2 ** ([0, 2, 4, 7, 9, 12][i] / 12), 0.22)
    # "what if your eyes could" -> riser into Andromeda
    bed += A.riser(N, S.T_CAN, S.T_SW["m31"], seed=21) * 1.0
    for i, (ts, k) in enumerate(S.SWAPS):
        if k != "night": bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.3 if k in ("all", "night") else 0.9)
        if k != "night": bed += bloom_swell(ts + 0.02, 50 + i, 0.45 if k == "all" else 0.32)
    # finale: a big airy drone while everything is up
    bed += A.drone(N, root=43.65, seed=64, bright=0.35) * 1.1 * A.env(N, [(0, 0), (S.T_SW["all"], 0), (S.T_SW["all"] + 0.6, 1), (S.T_BACK - 0.05, 1.2), (S.T_BACK, 0), (S.DUR, 0)])[:, None]
    # white-out back to the plain city night (loops)
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.2
    bed += A.hit(N, S.T_BACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "galaxies-visible.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
