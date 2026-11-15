"""Sound for "What If Earth Moved Farther from the Sun?": REDO v3 voice chain; a chord pad that sinks in pitch and grows
colder and sparser with every step away; a whoosh + implosion sweep + sub thump at every swap and a bright shimmer as each
smaller Sun blooms in; icy wind that builds as winter sets in, crackling ice as the frost spreads, a soft hush of falling
snow when the air freezes, a vast, quiet starfield shimmer in the Oort cloud; a white-out riser and a warm hit as the
village comes home. Ducked under the voice, loudness-normalised to -14 LUFS / -1 dBTP (lib.v3_kit.finalize), plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/sun-farther.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib.v3_kit import build_voice, finalize

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per stage: (root Hz, intervals, brightness) -- warm major, then sinking, colder and emptier
CHORDS = {"now": (220.0, (0, 4, 7, 12, 16), 0.5), "mars": (196.0, (0, 7, 12, 14, 19), 0.45), "jup": (174.6, (0, 7, 12, 15), 0.4),
          "sat": (146.8, (0, 7, 12, 14), 0.35), "nep": (130.8, (0, 7, 14, 19), 0.3), "oort": (110.0, (0, 7, 19, 26), 0.35)}


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


def bloom_swell(t0, seed, gain=0.4):
    sh = A.shimmer(N, t0, min(t0 + 1.6, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + 1.6, 0), (S.DUR, 0)])[:, None] * gain


def crackle(t0, t1, rate, seed, gain):
    out = np.zeros((N, 2)); r = np.random.default_rng(seed)
    n = int((t1 - t0) * rate); k = np.arange(int(0.02 * SR)) / SR
    for _ in range(n):
        tc = r.uniform(t0, t1); s = int(tc * SR)
        if s + len(k) >= N: continue
        c = A.hp(r.standard_normal(len(k)), r.uniform(2500, 7000)) * np.exp(-k / r.uniform(0.002, 0.008)) * r.uniform(0.2, 1.0)
        p = r.uniform(0.1, 0.9); out[s:s + len(k), 0] += c * (1 - p); out[s:s + len(k), 1] += c * p
    return out * gain


def main():
    voice = build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    sw = S.SWAPS
    seq = [(0.0, "now")] + [(ts, "now" if k == "now2" else k) for ts, k in sw]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, br = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.5, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 0.4, 1), (S.DUR, 0)])
        bed += chord(root, iv, br, 10 + i) * e[:, None]
    for i, (ts, k) in enumerate(sw):
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.5)
        bed += A.thump(N, ts, 0.8 if k != "now2" else 1.2)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.30 if k != "now2" else 0.6)
    r = np.random.default_rng(62); T = S.T_SW
    # icy wind building as winter sets in
    wind = np.stack([A.bp(r.standard_normal(N), 250, 1800) for _ in range(2)], 1)
    wind *= (1 + 0.6 * np.sin(2 * np.pi * 0.13 * tt) * np.sin(2 * np.pi * 0.31 * tt + 1))[:, None]
    bed += wind * 0.10 * A.env(N, [(0, 0), (T["mars"], 0), (S.T_WINTER, 0.6), (T["jup"], 0.9), (T["nep"], 1.1), (T["oort"], 0.5), (S.T_SUNBACK - 0.05, 0.4), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
    # ice crackling as the frost spreads
    bed += crackle(S.T_WINTER - 0.2, S.T_SUNBACK - 0.3, 6, 63, 0.25)
    # the air freezes: soft hiss of falling snow + icy shimmer
    hush = np.stack([A.bp(r.standard_normal(N), 3000, 11000) for _ in range(2)], 1)
    bed += hush * 0.05 * A.env(N, [(0, 0), (S.T_FREEZE - 0.2, 0), (S.T_FREEZE + 1.2, 1), (T["oort"] + 2.5, 0.2), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
    bed += A.shimmer(N, S.T_FREEZE, T["oort"] - 0.2, seed=64, gain=0.16)
    # the Oort cloud: a vast, quiet starfield shimmer + very low drone
    bed += A.shimmer(N, T["oort"] + 0.3, S.T_SUNBACK - 0.2, seed=65, gain=0.12)
    bed += A.drone(N, root=41.2, seed=66, bright=0.15) * 0.9 * A.env(N, [(0, 0), (T["nep"], 0), (T["oort"], 1), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_SUNBACK, seed=67) * 1.1
    bed += A.hit(N, S.T_SUNBACK, gain=0.45, root=65.4)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    finalize(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "sun-farther.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
