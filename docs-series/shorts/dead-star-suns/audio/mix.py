"""Sound for "What If Dead Stars Replaced Our Sun?": voice chain, a chord pad that changes key and colour per object,
a whoosh + implosion sweep + sub thump + bloom shimmer at every swap, an icy shimmer as Earth freezes, a sonar
"ping" + click at every pulsar flash, a riser and a huge hit for the magnetar flare, a deep cold drone for the black
dwarf, a white-out riser and a hit as the Sun returns. Ducked under the voice, two-pass loudnorm to -14 LUFS / -1 dBTP,
plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/dead-star-suns.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

CHORDS = {"sun": (220.0, (0, 4, 7, 12, 16), 0.5), "wd": (293.7, (0, 4, 7, 11, 14, 19), 0.9), "ns": (174.6, (0, 3, 7, 10, 14), 0.45),
          "psr": (196.0, (0, 5, 7, 12, 17), 0.6), "mag": (155.6, (0, 1, 6, 10, 13), 0.55), "bd": (110.0, (0, 3, 7, 15), 0.2)}


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


def ping(t0, gain=0.4):
    """pulsar pulse: a sharp click and a short bright sonar ping with a falling tail"""
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(0.9 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    f = 1760 * (1 - 0.25 * (1 - np.exp(-u / 0.15))); ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-u / 0.18) * 0.6 + np.sin(ph * 0.5) * np.exp(-u / 0.3) * 0.4
    x += A.hp(np.random.default_rng(7).standard_normal(n), 3000) * np.exp(-u / 0.004) * 0.8
    out[a:a + n] = np.stack([x * 0.9, x], 1) * gain
    return out


def bloom_swell(t0, seed, gain=0.4):
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
        if i == 0: e = A.env(N, [(0, 0), (0.3, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 0.4, 1), (S.DUR, 0)])
        bed += chord(root, iv, br, 10 + i) * e[:, None]
    for i, (ts, k) in enumerate(sw):
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 0.9 if k != "sun2" else 1.3)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35 if k != "sun2" else 0.6)
    bed += A.shimmer(N, S.T_FREEZE, S.T_SW["ns"] - 0.2, seed=61, gain=0.22)                     # Earth freezes
    ts_ = np.arange(S.T_SW["psr"], S.T_SW["mag"] - 0.1, 0.01); fl = np.array([S.psr_flash(x) for x in ts_])
    for i in range(1, len(fl) - 1):                                                             # pulsar: a ping per pulse
        if fl[i] > fl[i - 1] and fl[i] >= fl[i + 1] and fl[i] > 0.3: bed += ping(ts_[i], 0.45)
    bed += A.riser(N, S.T_FLARE - 1.3, S.T_FLARE, seed=64) * 0.8                                # magnetar flare
    bed += A.thump(N, S.T_FLARE, 1.6) + A.hit(N, S.T_FLARE, gain=0.55, root=41.2)
    bed += A.shimmer(N, S.T_FLARE + 0.1, S.T_SW["bd"] - 0.3, seed=66, gain=0.15)
    bed += A.drone(N, root=32.7, seed=63, bright=0.08) * 0.9 * A.env(N, [(0, 0), (S.T_SW["bd"], 0), (S.T_SW["bd"] + 0.8, 1), (S.T_WO0, 1), (S.T_SUNBACK, 0), (S.DUR, 0)])[:, None]
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
    A.write_srt(os.path.join(HERE, "..", "out", "dead-star-suns.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
