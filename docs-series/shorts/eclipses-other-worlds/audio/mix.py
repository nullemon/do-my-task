"""Sound for "What Eclipses Look Like on Other Worlds": REDO v3 voice chain; a pad (detuned saw strings + soft brass)
that changes chord with every world; whoosh + sub thump + shimmer bloom at every swap; a darkening drone into
totality with a bright 'diamond ring' chime; dusty wind on Mars; a deep red-ring swell on the Moon; a low rumble for
Jupiter and a chime as the Sun vanishes; airy shimmer for Saturn's rings and a sonar ping for the Earth dot; white-out
riser and a hit back to the beach. Ducked, two-pass loudnorm -14 LUFS / -1 dBTP (+ limiter headroom), SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib import v3_redo_q5 as V3
from lib.v3_kit import finalize

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR
CHORDS = {"earth": (110.0, (0, 7, 12, 16, 19), 1400, 0.8), "tot": (98.0, (0, 7, 12, 15, 22), 700, 0.9),
          "mars": (103.8, (0, 7, 12, 15, 19), 1100, 0.85), "moon": (87.3, (0, 7, 12, 15, 19, 22), 900, 1.0),
          "io": (82.4, (0, 7, 12, 14, 19), 800, 1.05), "sat": (130.8, (0, 7, 12, 16, 19, 23, 26), 2600, 1.15),
          "day": (110.0, (0, 7, 12, 16, 19, 24), 2200, 0.9)}


def saw(f, n, seed):
    r = np.random.default_rng(seed); ph = r.uniform(0, 1)
    vib = 1 + 0.003 * np.sin(2 * np.pi * r.uniform(4.5, 5.5) * np.arange(n) / SR + r.uniform(0, 6))
    return 2 * ((ph + np.cumsum(f * vib) / SR) % 1.0) - 1


def strings(root, iv, cut, seed):
    x = np.zeros((N, 2)); r = np.random.default_rng(seed)
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        for c in range(2):
            for v in range(2):
                x[:, c] += saw(f * (1 + r.uniform(-0.004, 0.004)), N, seed * 31 + k * 7 + c * 3 + v) * (0.5 if k == 0 else 0.32)
    x = A.lp(x, cut, 2)
    brass = A.lp(sum(saw(root * 2 ** (s / 12), N, seed + 500 + s) * 0.25 for s in (0, 7, 12)), cut * 0.6, 2)
    return (x + brass[:, None] * 0.6) * 0.025


def whoosh(t1, dur=0.6, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    f = 900 * (60 / 900) ** u; out[a:b] += (np.sin(2 * np.pi * np.cumsum(f) / SR) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bell(t0, f, gain=0.3, dec=0.6):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(3 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * m * u) * np.exp(-u / (dec / m ** 0.5)) * w for m, w in ((1, 1.0), (2.0, 0.45), (2.76, 0.3), (5.4, 0.12)))
    out[a:a + n] = (s * np.minimum(u / 0.003, 1))[:, None] * gain
    return out


def ping(t0, f=1760.0, gain=0.25):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(1.4 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * u) * np.exp(-u / 0.25) * np.minimum(u / 0.004, 1)
    out[a:a + n] = s[:, None] * gain
    return out


def noise_bed(lo, hi, seed):
    r = np.random.default_rng(seed); return np.stack([A.bp(r.standard_normal(N), lo, hi) for _ in range(2)], 1)


def seg_env(a, b, fi=0.5, fo=0.4):
    return A.env(N, [(0, 0), (max(a, 0), 0), (a + fi, 1), (max(b - fo, a + fi + 0.01), 1), (b, 0), (S.DUR + 1, 0)])[:, None]


def main():
    voice = V3.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    T = S.T_SW
    seq = [(0.0, "earth"), (S.T_C2 - 0.3, "tot"), (T["mars"], "mars"), (T["moon"], "moon"), (T["io"], "io"), (T["sat"], "sat"), (S.T_BACK, "day")]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, cut, lev = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.3, 1), (te - 0.4, 1.1), (te - 0.02, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.4, 1.1), (te - 0.02, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.4, 1), (S.DUR - 0.5, 1), (S.DUR, 0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        if k == "day": continue
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55) + A.thump(N, ts, 1.1 if k in ("io", "sat") else 0.85)
        bed += A.shimmer(N, ts + 0.02, min(ts + 1.6, S.DUR - 0.1), seed=50 + i, gain=1.0) * A.env(N, [(0, 0), (ts, 0), (ts + 0.05, 1), (ts + 1.6, 0), (S.DUR, 0)])[:, None] * 0.3
    # Earth: a darkening low swell as the Moon slides in, diamond-ring chime, totality hush
    bed += A.drone(N, 49.0, seed=3, bright=0.2) * (seg_env(S.T_M0, T["mars"], 1.5, 0.4) * 0.8)
    bed += bell(S.T_C2 - 0.1, 1568.0, 0.18, 1.2) + bell(S.T_C2 - 0.08, 2093.0, 0.10, 1.0)
    bed += A.thump(N, S.T_C2, 0.6)
    # Mars: dusty wind + Phobos pings
    bed += noise_bed(200, 1500, 61) * (1 + 0.5 * np.sin(2 * np.pi * 0.3 * tt))[:, None] * seg_env(T["mars"], T["moon"]) * 0.25
    for j, tp in enumerate(np.arange(S.wt("mars", "PHOBOS"), T["moon"] - 0.4, 1 / 1.3)): bed += ping(tp, 1760.0 if j % 2 == 0 else 2093.0, 0.15)
    bed += bell(S.wt("mars_c", "BITE"), 1318.5, 0.12, 0.8)
    # Moon: red-ring swell
    bed += A.drone(N, 43.65, seed=7, bright=0.3) * seg_env(T["moon"], T["io"], 0.8, 0.4) * 0.9
    bed += A.riser(N, S.T_RED - 0.8, S.T_RED, seed=71) * 0.35 + bell(S.T_RED, 1046.5, 0.12, 1.5)
    # Io: Jupiter rumble, chime as the Sun vanishes
    bed += noise_bed(30, 160, 62) * (1 + 0.4 * np.sin(2 * np.pi * 0.5 * tt))[:, None] * seg_env(T["io"], T["sat"]) * 1.2
    bed += A.riser(N, S.T_SWALLOW - 1.0, S.T_SWALLOW, seed=72) * 0.45 + bell(S.T_SWALLOW, 1760.0, 0.15, 1.6) + A.thump(N, S.T_SWALLOW, 0.8)
    # Saturn: ring shimmer, swell on "light up", sonar ping for the Earth dot
    bed += A.shimmer(N, T["sat"] + 0.3, S.T_WO0, seed=81, gain=0.22)
    bed += A.riser(N, S.T_LIGHT - 0.7, S.T_LIGHT + 0.05, seed=73) * 0.35
    for j, tp in enumerate(np.arange(S.T_DOT, S.T_WO0 - 0.3, 1 / 1.1)): bed += ping(tp, 2349.0 if j % 2 == 0 else 1760.0, 0.14)
    bed += bell(S.wt("sat_d", "US"), 1568.0, 0.15, 1.8)
    # white-out back to the beach
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.1 + A.hit(N, S.T_BACK, gain=0.45, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav"); sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    finalize(raw, os.path.join(OUT, "mix.wav")); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    A.write_srt(os.path.join(HERE, "..", "out", "eclipses-other-worlds.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
