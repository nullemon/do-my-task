"""Sound for "What If Black Holes Replaced Our Sun?": voice chain, a pad that changes key and colour per scene, a whoosh +
sub thump + shimmer at every swap, an empty sub-drone for the dark Sun-mass hole, a hissing stream for Cygnus X-1, a deep
rumble for Sgr A*, a falling, warping tunnel tone inside M87*, a roaring quasar and a swallow-riser for TON 618, and a hit
as the Sun returns. Ducked under the voice, two-pass loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/black-hole-suns.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR
CHORDS = {"sun": (220.0, (0, 4, 7, 12, 16), 0.5), "one": (110.0, (0, 7, 12), 0.08), "cyg": (293.7, (0, 4, 7, 11, 14, 19), 0.9),
          "sgr": (98.0, (0, 3, 7, 10, 15), 0.35), "m87": (138.6, (0, 1, 6, 7, 13), 0.4), "ton": (73.4, (0, 7, 12, 16, 19), 0.6)}


def chord(root, iv, bright, seed):
    r = np.random.default_rng(seed); x = np.zeros((N, 2))
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12); a = (0.5 if k == 0 else 0.30) * (1 if f < 600 else bright)
        for c in range(2):
            x[:, c] += a * np.sin(2 * np.pi * f * (1 + r.uniform(-0.002, 0.002)) * tt + r.uniform(0, 6.28)) * (1 + 0.25 * np.sin(2 * np.pi * r.uniform(0.1, 0.3) * tt))
    air = np.stack([A.bp(r.standard_normal(N), 1500, 7000) for _ in range(2)], 1) * 0.05 * bright
    return (x + air) * 0.05


def whoosh(t1, dur=0.6, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    f = 900 * (60 / 900) ** u; out[a:b] += (np.sin(2 * np.pi * np.cumsum(f) / SR) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def E(pts): return A.env(N, pts)[:, None]


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    sw = S.SWAPS
    seq = [(0.0, "sun")] + [(ts, "sun" if k == "sun2" else k) for ts, k in sw]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, br = CHORDS[k]
        if i == 0: e = E([(0, 0), (0.4, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        elif i == len(seq) - 1: e = E([(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 0.4, 1), (S.DUR, 0)])
        else: e = E([(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        bed += chord(root, iv, br, 10 + i) * e
    for i, (ts, k) in enumerate(sw):
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.0 if k != "sun2" else 1.3)
        sh = A.shimmer(N, ts, min(ts + 1.6, S.DUR - 0.1), seed=50 + i, gain=1.0)
        bed += sh * E([(0, 0), (ts, 0), (ts + 0.05, 1), (ts + 1.6, 0), (S.DUR, 0)]) * (0.3 if k != "sun2" else 0.6)
    T = S.T_SW; r = np.random.default_rng(7)
    # 1-Sun-mass hole: empty sub drone
    bed += A.drone(N, root=36.7, seed=61, bright=0.1) * 1.0 * E([(0, 0), (T["one"], 0), (T["one"] + 0.6, 1), (T["cyg"] - 0.1, 1), (T["cyg"], 0), (S.DUR, 0)])
    # Cygnus X-1: hissing accretion stream
    hiss = np.stack([A.bp(r.standard_normal(N), 2500, 9000) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 3 * tt))[:, None]
    bed += hiss * 0.06 * E([(0, 0), (T["cyg"], 0), (T["cyg"] + 0.5, 1), (T["sgr"] - 0.1, 1), (T["sgr"], 0), (S.DUR, 0)])
    # Sgr A*: deep rumble
    rum = np.stack([A.lp(r.standard_normal(N), 160, 2) for _ in range(2)], 1) * (1 + 0.4 * np.sin(2 * np.pi * 0.8 * tt))[:, None]
    bed += rum * 0.7 * E([(0, 0), (T["sgr"], 0), (T["sgr"] + 0.6, 1), (T["m87"] - 0.1, 1), (T["m87"], 0), (S.DUR, 0)])
    # M87*: falling, warping tunnel tone
    a, b = T["m87"], T["ton"]; u = np.clip((tt - a) / (b - a), 0, 1)
    f = 420 * (90 / 420) ** u * (1 + 0.04 * np.sin(2 * np.pi * 5 * tt)); ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.4 * np.sin(1.5 * ph + 0.3 * np.sin(2 * np.pi * 0.7 * tt)))
    bed += np.stack([tone, np.roll(tone, 400)], 1) * 0.10 * E([(0, 0), (a, 0), (a + 0.5, 1), (b - 0.1, 1), (b, 0), (S.DUR, 0)])
    bed += rum * 0.5 * E([(0, 0), (a, 0), (a + 0.5, 1), (b - 0.1, 1), (b, 0), (S.DUR, 0)])
    # TON 618: quasar roar, swallow riser, hit as the Sun returns
    roar = np.stack([A.bp(r.standard_normal(N), 80, 1800) for _ in range(2)], 1)
    bed += roar * 0.25 * E([(0, 0), (T["ton"], 0), (T["ton"] + 0.6, 0.8), (S.T_SWAL, 1), (S.T_SUNBACK - 0.05, 1.5), (S.T_SUNBACK, 0), (S.DUR, 0)])
    bed += A.drone(N, root=27.5, seed=64, bright=0.2) * 1.2 * E([(0, 0), (T["ton"], 0), (S.T_SWAL, 1), (S.T_SUNBACK, 0), (S.DUR, 0)])
    bed += A.riser(N, S.T_SWAL - 0.2, S.T_SUNBACK, seed=65) * 1.2
    bed += A.hit(N, S.T_SUNBACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    A.write_srt(os.path.join(HERE, "..", "out", "black-hole-suns.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
