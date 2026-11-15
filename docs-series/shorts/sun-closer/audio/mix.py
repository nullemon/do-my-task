"""Sound for "What If Earth Moved Closer to the Sun?": REDO v3 voice chain; a chord pad that climbs in pitch and tension
with every step closer; a whoosh + implosion sweep + sub thump at every swap and a bright shimmer as each new Sun blooms in;
a steam hiss when the oceans boil, a dry crackle as the rocks glow, a glassy ring as the sand melts, a deep lava rumble and
bubbling at the finale; a white-out riser and a low hit as today's Sun returns. Ducked under the voice, loudness-normalised
to -14 LUFS / -1 dBTP (lib.v3_kit.finalize), plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/sun-closer.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib.v3_kit import build_voice, finalize

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per stage: (root Hz, intervals in semitones, brightness) -- climbing, more tense each step
CHORDS = {"now": (220.0, (0, 4, 7, 12, 16), 0.5), "ven": (233.1, (0, 5, 7, 12, 17), 0.65), "mer": (246.9, (0, 3, 7, 10, 15), 0.8),
          "p01": (261.6, (0, 3, 6, 10, 15), 0.95), "skim": (65.4, (0, 1, 7, 12, 13, 19), 0.6)}


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
    """dry random clicks (heat-cracking rock / bubbling)"""
    out = np.zeros((N, 2)); r = np.random.default_rng(seed)
    n = int((t1 - t0) * rate); k = np.arange(int(0.012 * SR)) / SR
    for _ in range(n):
        tc = r.uniform(t0, t1); s = int(tc * SR)
        if s + len(k) >= N: continue
        c = A.hp(r.standard_normal(len(k)), r.uniform(1500, 5000)) * np.exp(-k / r.uniform(0.001, 0.004)) * r.uniform(0.2, 1.0)
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
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 0.9 if k != "skim" else 1.4)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35 if k != "now2" else 0.6)
    r = np.random.default_rng(62)
    T = S.T_SW
    # oceans boil: steam hiss
    hiss = np.stack([A.bp(r.standard_normal(N), 2500, 9000) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 7 * tt))[:, None]
    bed += hiss * 0.07 * A.env(N, [(0, 0), (S.T_BOIL - 0.3, 0), (S.T_BOIL + 0.8, 1), (T["mer"] - 0.1, 1), (T["mer"] + 0.5, 0.3), (T["p01"], 0), (S.DUR, 0)])[:, None]
    # rocks glow: crackle + low heat drone
    bed += crackle(S.T_GLOW - 0.2, T["p01"] - 0.1, 35, 63, 0.35)
    bed += A.drone(N, root=55.0, seed=64, bright=0.3) * 0.6 * A.env(N, [(0, 0), (S.T_GLOW - 0.3, 0), (S.T_GLOW + 1.0, 1), (T["skim"], 1), (T["skim"] + 0.3, 0), (S.DUR, 0)])[:, None]
    # sand melts into glass: glassy ring
    bed += A.shimmer(N, S.T_GLASS, T["skim"] - 0.2, seed=65, gain=0.22)
    # lava: deep rumble + bubbling, swelling until the white-out
    rum = np.stack([A.lp(r.standard_normal(N), 160, 2) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 2.1 * tt) * np.sin(2 * np.pi * 0.6 * tt))[:, None]
    bed += rum * 0.9 * A.env(N, [(0, 0), (T["skim"], 0), (T["skim"] + 0.5, 0.5), (S.T_LAVA, 0.9), (S.T_SUNBACK - 0.05, 1.4), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
    bed += crackle(T["skim"] + 0.3, S.T_SUNBACK - 0.1, 18, 66, 0.5)
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_SUNBACK, seed=67) * 1.2
    bed += A.hit(N, S.T_SUNBACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    finalize(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "sun-closer.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
