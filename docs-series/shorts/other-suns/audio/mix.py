"""Sound for "What If Other Stars Replaced Our Sun?": voice chain, a chord pad that changes key and colour with each star,
a whoosh + implosion sweep + sub thump at every swap, an icy shimmer for the frozen Proxima world, a sizzle for Sirius,
a steam roar for Rigel, a boiling rumble inside Betelgeuse, a white-out riser and a hit as the Sun returns. Ducked under
the voice, two-pass loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/other-suns.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per star: (root Hz, intervals in semitones, brightness)
CHORDS = {"sun": (220.0, (0, 4, 7, 12, 16), 0.5), "prox": (146.8, (0, 3, 7, 10), 0.15), "sir": (329.6, (0, 4, 7, 11, 14, 19), 0.9),
          "arc": (174.6, (0, 4, 7, 9, 12), 0.45), "rig": (246.9, (0, 7, 12, 16, 19, 24), 1.0), "bet": (65.4, (0, 3, 7, 12, 15), 0.25)}


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
    """filtered-noise swell sweeping left->right into t1, plus a falling 'implosion' tone"""
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    pan = u
    out[a:b, 0] = nz * (1 - 0.6 * pan); out[a:b, 1] = nz * (0.4 + 0.6 * pan)
    f = 900 * (60 / 900) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bloom_swell(t0, seed, gain=0.4):
    """the new star blooms in: bright shimmer burst + reversed noise tail"""
    sh = A.shimmer(N, t0, min(t0 + 1.6, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + 1.6, 0), (S.DUR, 0)])[:, None] * gain


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    sw = S.SWAPS
    seq = [(0.0, "sun")] + [(ts, "sun" if k == "sun2" else k) for ts, k in sw]
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
        bed += A.thump(N, ts, 0.9 if k != "sun2" else 1.3)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35 if k != "sun2" else 0.6)
    # Proxima: icy shimmer as Earth freezes
    bed += A.shimmer(N, S.T_FREEZE, S.T_SW["sir"] - 0.3, seed=61, gain=0.20)
    # Sirius: sizzling boil
    r = np.random.default_rng(62)
    sizz = np.stack([A.hp(r.standard_normal(N), 3500) for _ in range(2)], 1) * (1 + 0.6 * np.sin(2 * np.pi * 11 * tt))[:, None]
    bed += sizz * 0.05 * A.env(N, [(0, 0), (S.T_BOIL - 0.3, 0), (S.T_BOIL + 0.6, 1), (S.T_SW["arc"] - 0.1, 1), (S.T_SW["arc"], 0), (S.DUR, 0)])[:, None]
    # Rigel: steam roar on "vaporized"
    roar = np.stack([A.bp(r.standard_normal(N), 150, 2500) for _ in range(2)], 1)
    bed += roar * 0.22 * A.env(N, [(0, 0), (S.T_VAPOR - 0.2, 0), (S.T_VAPOR + 0.8, 1), (S.T_SW["bet"] - 0.1, 0.8), (S.T_SW["bet"], 0), (S.DUR, 0)])[:, None]
    bed += A.riser(N, S.T_VAPOR - 0.4, S.T_VAPOR + 0.55, seed=63) * 0.6
    # Betelgeuse: boiling rumble swelling until we are inside, white-out riser, hit as the Sun returns
    rum = np.stack([A.lp(r.standard_normal(N), 180, 2) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 2.3 * tt) * np.sin(2 * np.pi * 0.7 * tt))[:, None]
    bed += rum * 0.9 * A.env(N, [(0, 0), (S.T_BET0, 0), (S.T_BET0 + 0.5, 0.4), (S.T_INSIDE, 1.2), (S.T_SUNBACK - 0.05, 1.4), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
    bed += A.drone(N, root=32.7, seed=64, bright=0.2) * 1.2 * A.env(N, [(0, 0), (S.T_BET0, 0), (S.T_INSIDE, 1), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_SUNBACK, seed=65) * 1.2
    bed += A.hit(N, S.T_SUNBACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "other-suns.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
