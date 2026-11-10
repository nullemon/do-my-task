"""Sound for "What If Earth Had Rings Like Saturn?": voice chain, a chord pad that changes key and colour per beat
(warm golden major / glassy night / bright noon / pastel Oslo), a whoosh + sub thump + bloom swell at every flash,
an icy shimmer as the rings unfurl, a crystalline 'ring' bed (bell grains) while rings are up, night crickets and meteor
swishes, a wind bed for Oslo, a riser + low hit back to our ringless sky. Ducked under the voice, two-pass loudnorm to
-14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/earth-rings.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per beat: (root Hz, intervals in semitones, brightness)
CHORDS = {"pre": (196.0, (0, 4, 7, 12), 0.35), "ny": (196.0, (0, 4, 7, 11, 14, 19), 0.7), "night": (146.8, (0, 3, 7, 10, 14), 0.4),
          "eq": (261.6, (0, 4, 7, 12, 14, 19), 1.0), "oslo": (174.6, (0, 4, 7, 9, 14), 0.6), "end": (196.0, (0, 4, 7, 12), 0.4)}


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
    f = 900 * (60 / 900) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bloom_swell(t0, seed, gain=0.4, dur=1.6):
    sh = A.shimmer(N, t0, min(t0 + dur, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + dur, 0), (S.DUR, 0)])[:, None] * gain


def crickets(t0, t1, seed=7):
    out = np.zeros((N, 2)); r = np.random.default_rng(seed)
    for v in range(3):
        f = r.uniform(4200, 5200); rate = r.uniform(14, 18); pan = r.uniform(0.2, 0.8)
        a, b = int(t0 * SR), int(t1 * SR); x = tt[a:b]
        chirp = (np.sin(2 * np.pi * rate * x + v) > 0.3) * (np.sin(2 * np.pi * 0.9 * x + v * 2) > -0.2)
        s = np.sin(2 * np.pi * f * x) * A.lp(chirp.astype(float), 300) * 0.05
        out[a:b, 0] += s * (1 - pan); out[a:b, 1] += s * pan
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "pre"), (S.T_RINGS, "ny")] + [(S.T_SW[k], k) for k in ("night", "eq", "oslo", "end")]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, br = CHORDS[k]
        if i == 0: e = A.env(N, [(0, 0.6), (te - 0.1, 0.6), (te, 0), (S.DUR + 1, 0)])
        elif i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 1.0, 0.7), (S.DUR, 0.6)])     # ends where it began: loop
        else: e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0.0), (S.DUR + 1, 0)])
        bed += chord(root, iv, br, 10 + i) * e[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.0 if k != "end" else 1.3)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.45 if k == "ny" else 0.32)
    # rings up: soft crystalline grains (ice particles glinting)
    rings_env = A.env(N, [(0, 0), (S.T_RINGS, 0), (S.T_RINGS + 0.6, 1), (S.T_SW["end"] - 0.1, 1), (S.T_SW["end"], 0), (S.DUR, 0)])
    bed += A.shimmer(N, S.T_RINGS, S.T_SW["end"], seed=61, gain=0.10) * rings_env[:, None]
    # striping shadows: low swept pulses
    bed += A.riser(N, S.T_STRIPE - 0.5, S.T_STRIPE + 0.4, seed=62) * 0.35
    # night: crickets, meteor swishes
    bed += crickets(S.T_SW["night"] + 0.3, S.T_SW["eq"] - 0.1) * A.env(N, [(0, 0), (S.T_SW["night"], 0), (S.T_SW["night"] + 0.8, 1), (S.T_SW["eq"] - 0.3, 1), (S.T_SW["eq"], 0), (S.DUR, 0)])[:, None]
    r = np.random.default_rng(63)
    # equator: bright airy hiss + rising tone along the razor line
    air = np.stack([A.hp(r.standard_normal(N), 5000) for _ in range(2)], 1)
    bed += air * 0.03 * A.env(N, [(0, 0), (S.T_SW["eq"], 0), (S.T_SW["eq"] + 0.5, 1), (S.T_SW["oslo"] - 0.2, 1), (S.T_SW["oslo"], 0), (S.DUR, 0)])[:, None]
    # Oslo: wind
    wind = np.stack([A.bp(r.standard_normal(N), 200, 1200) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 0.23 * tt))[:, None]
    bed += wind * 0.10 * A.env(N, [(0, 0), (S.T_SW["oslo"], 0), (S.T_SW["oslo"] + 0.6, 1), (S.T_SW["end"] - 0.2, 1), (S.T_SW["end"], 0), (S.DUR, 0)])[:, None]
    bed += A.drone(N, root=43.65, seed=64, bright=0.2) * 0.8 * A.env(N, [(0, 0), (S.T_SW["oslo"], 0), (S.T_SW["oslo"] + 1, 1), (S.T_SW["end"], 0), (S.DUR, 0)])[:, None]
    bed += A.riser(N, S.T_SW["end"] - 0.9, S.T_SW["end"], seed=65) * 1.0
    bed += A.hit(N, S.T_SW["end"], gain=0.45, root=49.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.25, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "earth-rings.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
