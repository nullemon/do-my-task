"""Sound for "What If Earth Were Somewhere Else in the Galaxy?": v3 voice chain; a soft mountain-wind bed; a chord pad
that changes key and colour with each address; a riser into the first swap; whoosh + sub thump + bloom shimmer at every
swap; a huge drone under the face-on Milky Way; an almost silent, eerie void; white-out riser and a deep hit back home.
Ducked under the voice, loudnorm to -14 LUFS / -1 dBTP (lib.v3_kit.finalize), plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/galaxy-address.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib.v3_kit import build_voice, finalize

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per scene: (root Hz, intervals in semitones, brightness)
CHORDS = {"today": (110.0, (0, 7, 12, 14, 19), 0.35), "gc": (130.8, (0, 4, 7, 11, 14, 19), 1.0), "arm": (146.8, (0, 3, 7, 10, 14), 0.8),
          "halo": (98.0, (0, 4, 7, 11, 12, 16, 19), 0.9), "void": (73.4, (0, 7, 13), 0.12)}


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
    voice = build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)             # REDO v3 voice post chain
    seq = [(0.0, "today")] + [(ts, k) for ts, k in S.SWAPS]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, br = CHORDS[k]
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        elif i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 0.4, 1), (S.DUR, 0)])
        else: e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0.0), (S.DUR + 1, 0)])
        bed += chord(root, iv, br, 10 + i) * e[:, None] * (1.25 if k == "halo" else 1.0)
    # mountain wind, always there (quieter in the void)
    r = np.random.default_rng(5)
    wind = np.stack([A.bp(r.standard_normal(N), 150, 1200) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 0.11 * tt) * np.sin(2 * np.pi * 0.037 * tt + 1))[:, None]
    bed += wind * 0.06 * A.env(N, [(0, 1), (S.T_SW["void"], 1), (S.T_SW["void"] + 0.5, 0.35), (S.T_BACK, 0.35), (S.T_BACK + 0.2, 1), (S.DUR, 1)])[:, None]
    bed += A.riser(N, S.T_SW["gc"] - 1.6, S.T_SW["gc"], seed=21) * 1.0
    for i, (ts, k) in enumerate(S.SWAPS):
        if k != "today": bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.3 if k in ("halo", "today") else 0.9)
        if k not in ("today", "void"): bed += bloom_swell(ts + 0.02, 50 + i, 0.45 if k == "halo" else 0.32)
    bed += A.drone(N, root=43.65, seed=64, bright=0.35) * 1.1 * A.env(N, [(0, 0), (S.T_SW["halo"], 0), (S.T_SW["halo"] + 0.6, 1), (S.T_SW["void"] - 0.05, 1.2), (S.T_SW["void"], 0), (S.DUR, 0)])[:, None]
    for i in range(6): bed += plink(S.T_VOIDGAL + 0.08 * i, 660 * 2 ** ([0, 3, 7, 10, 14, 17][i] / 12), 0.10)
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.2
    bed += A.hit(N, S.T_BACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    finalize(raw, os.path.join(OUT, "mix.wav")); os.remove(raw)              # v3: loudnorm + true-peak guard
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "galaxy-address.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
