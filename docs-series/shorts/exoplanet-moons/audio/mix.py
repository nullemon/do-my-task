"""Sound for "What If Strange Exoplanets Replaced Our Moon?": voice chain; an orchestral-ish pad (detuned, filtered saw
"strings" + a soft brass-like fifth layer) whose chord changes with every planet; a whoosh + sub boom + shimmer at every
swap; per-planet colour: lava crackle (55 Cancri e), a glassy wind-chime hiss (HD 189733 b), a rising tearing drone
(WASP-12 b), a hollow low drone with the bed thinned out (TrES-2 b), a sunrise swell into a roaring bright hum
(KELT-9 b); a white-out riser and a low hit as our Moon returns. Ducked under the voice, two-pass loudnorm to
-14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/exoplanet-moons.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per body: (root Hz, intervals, filter cutoff Hz, level)
CHORDS = {"moon": (110.0, (0, 7, 12, 16, 19), 900, 0.8), "cnc": (103.8, (0, 7, 12, 15, 19), 1200, 0.85),
          "hd": (123.5, (0, 7, 12, 14, 19, 23), 1700, 0.95), "wasp": (98.0, (0, 6, 12, 15, 18), 1500, 1.0),
          "tres": (82.4, (0, 7, 12, 15), 600, 0.75), "kelt": (130.8, (0, 7, 12, 16, 19, 24, 28), 3400, 1.25)}


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


def span(k):
    i = [t for t, kk in S.SWAPS].index(S.T_SW[k]); return S.T_SW[k], S.SWAPS[i + 1][0]


def crackle(t0, t1, seed=70):
    """lava: sparse pops and crackles over a low bubbling rumble"""
    out = np.zeros((N, 2)); r = np.random.default_rng(seed)
    for _ in range(int((t1 - t0) * 26)):
        tg = r.uniform(t0, t1); n = int(r.uniform(0.004, 0.02) * SR); s = int(tg * SR)
        if s + n >= N: continue
        g = A.hp(r.standard_normal(n), 1200) * np.exp(-np.arange(n) / (n / 4)) * r.uniform(0.2, 1.0) ** 2
        pan = r.uniform(0.2, 0.8); out[s:s + n, 0] += g * (1 - pan); out[s:s + n, 1] += g * pan
    bub = A.lp(r.standard_normal(N), 120, 2) * (1 + 0.8 * np.sin(2 * np.pi * 1.7 * tt) * np.sin(2 * np.pi * 0.43 * tt))
    out += (bub * 1.5)[:, None]
    return out * A.env(N, [(0, 0), (t0, 0), (t0 + 0.3, 1), (t1 - 0.3, 1), (t1, 0), (S.DUR, 0)])[:, None]


def glass_wind(t0, t1, seed=71):
    """HD 189733 b: sideways glass rain: a fast panning band-passed wind + tinkling glassy grains"""
    out = np.zeros((N, 2)); r = np.random.default_rng(seed)
    w = A.bp(r.standard_normal(N), 900, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * tt))
    pan = 0.5 + 0.45 * np.sin(2 * np.pi * 0.35 * tt)
    out[:, 0] += w * (1 - pan) * 0.5; out[:, 1] += w * pan * 0.5
    out += A.shimmer(N, t0, t1, seed=seed + 1, gain=1.6)
    return out * A.env(N, [(0, 0), (t0, 0), (t0 + 0.4, 1), (t1 - 0.3, 1), (t1, 0), (S.DUR, 0)])[:, None]


def tearing(t0, t1, seed=72):
    """WASP-12 b: a slow rising, wavering low tone + streaming noise (gas pulled away)"""
    n = N; f = 55 * 2 ** (np.clip((tt - t0) / max(t1 - t0, 1e-3), 0, 1) * 0.6)
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.01 * np.sin(2 * np.pi * 5 * tt))) / SR
    tone = (np.sin(ph) + 0.5 * np.sin(2 * ph + 0.3) + 0.25 * np.sin(3 * ph)) * 0.35
    r = np.random.default_rng(seed)
    st = A.bp(r.standard_normal(n), 250, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.3 * tt) ** 2) * 0.6
    out = np.stack([tone + st, tone + np.roll(st, 900)], 1)
    return out * A.env(N, [(0, 0), (t0, 0), (t0 + 0.5, 1), (t1 - 0.3, 1.2), (t1, 0), (S.DUR, 0)])[:, None]


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
        if k == "kelt": e = e * A.env(N, [(0, 0.35), (S.T_KELT, 0.35), (S.T_RISEN, 1.0), (S.DUR, 1.0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        big = k in ("wasp", "kelt", "moon2")
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.3 if big else 0.9)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35 if k != "moon2" else 0.6)
    bed += A.shimmer(N, 0.3, S.T_SW["cnc"] - 0.3, seed=61, gain=0.10)                       # moonlight sparkle
    bed += crackle(*span("cnc")) * 0.35
    bed += glass_wind(*span("hd")) * 0.30
    bed += tearing(*span("wasp")) * 0.45
    t0, t1 = span("tres")
    bed += A.drone(N, root=41.2, seed=73, bright=0.05) * 1.4 * A.env(N, [(0, 0), (t0, 0), (t0 + 0.4, 1), (t1 - 0.2, 1), (t1, 0), (S.DUR, 0)])[:, None]
    # KELT-9 b: sunrise swell into a roaring bright hum
    tk, tb = S.T_KELT, S.T_BACK
    bed += A.riser(N, tk + 0.2, S.T_RISEN, seed=74) * 0.6
    roar = A.drone(N, root=65.4, seed=75, bright=0.6) * 1.6
    r = np.random.default_rng(76)
    roar += np.stack([A.lp(r.standard_normal(N), 700, 2) for _ in range(2)], 1) * 0.8
    bed += roar * A.env(N, [(0, 0), (tk, 0), (S.T_RISEN, 0.9), (tb - 0.05, 1.3), (tb, 0), (S.DUR, 0)])[:, None]
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
    A.write_srt(os.path.join(HERE, "..", "out", "exoplanet-moons.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
