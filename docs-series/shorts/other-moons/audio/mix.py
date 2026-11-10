"""Sound for "What If Other Moons Replaced Our Moon?": voice chain; an orchestral pad (detuned, filtered saw "strings"
plus a soft brass fifth) that changes chord with every moon; a whoosh + implosion sweep + sub thump + shimmer bloom at
every swap; sonar pings for Phobos's pointer ring; an icy crystal shimmer for Europa; a volcanic rumble and eruption hiss
for Io; a low hazy wind for Titan; a big open chord for Ganymede; seven rising "pops" as all the moons arrive; a
white-out riser and a low hit as our lone Moon returns. Ducked under the voice, two-pass loudnorm to -14 LUFS /
-1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/other-moons.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per moon: (root Hz, intervals, filter cutoff Hz, level)
CHORDS = {"moon": (110.0, (0, 7, 12, 16, 19), 900, 0.8), "pho": (103.8, (0, 7, 14, 19), 600, 0.55),
          "eur": (130.8, (0, 7, 12, 14, 19, 26), 2200, 0.85), "io": (116.5, (0, 7, 12, 15, 19), 1600, 0.95),
          "tit": (98.0, (0, 7, 12, 15, 22), 1100, 0.95), "gan": (146.8, (0, 7, 12, 16, 19, 24), 2600, 1.05),
          "all": (110.0, (0, 7, 12, 16, 19, 24, 28), 3400, 1.25)}


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


def ping(t0, f=1760.0, gain=0.3, pan=0.5):
    """sonar ping: sine with a fast attack, long ring and a little echo"""
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(1.4 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * u) * np.exp(-u / 0.25) * np.minimum(u / 0.004, 1)
    s += 0.35 * np.sin(2 * np.pi * f * 2.01 * u) * np.exp(-u / 0.08)
    out[a:a + n, 0] = s * (1 - pan) * 2; out[a:a + n, 1] = s * pan * 2
    e = int(0.23 * SR)
    if a + e + n <= N: out[a + e:a + e + n] += out[a:a + n][:, ::-1] * 0.35
    return out * gain


def pluck(t0, f, gain=0.3):
    """bright bell-like pop for each moon arriving in the finale"""
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(1.2 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * m * u) * np.exp(-u / (0.35 / m)) * w for m, w in ((1, 1.0), (2.0, 0.5), (3.01, 0.25), (4.2, 0.15)))
    s *= np.minimum(u / 0.003, 1)
    out[a:a + n] = s[:, None] * gain
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "moon")] + [(ts, "moon" if k == "moon2" else k) for ts, k in S.SWAPS]
    seq.insert(len(seq) - 1, (S.T_ALL, "all"))
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, cut, lev = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.3, 1), (te - 0.4, 1.1), (te - 0.02, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.4, 1.1), (te - 0.02, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.4, 1), (S.DUR - 0.5, 1), (S.DUR, 0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        if k == "moon2": continue
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.2 if k == "gan" else 0.9)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35)
    bed += A.shimmer(N, 0.3, S.T_SW["pho"] - 0.3, seed=61, gain=0.10)                      # moonlight sparkle
    # Phobos: sonar pings with the pointer ring
    tw = S.wt("pho", "WHERE")
    for j, tp in enumerate(np.arange(tw, S.T_SW["eur"] - 0.3, 1 / 1.3)):
        bed += ping(tp, 1760.0 if j % 2 == 0 else 2093.0, 0.22, 0.5 + 0.2 * (-1) ** j)
    # Europa: icy crystal shimmer
    bed += A.shimmer(N, S.T_SW["eur"] + 0.2, S.T_SW["io"] - 0.3, seed=71, gain=0.22)
    # Io: volcanic rumble + eruption hiss bursts
    r = np.random.default_rng(62)
    rum = np.stack([A.lp(r.standard_normal(N), 140, 2) for _ in range(2)], 1) * (1 + 0.5 * np.sin(2 * np.pi * 2.3 * tt))[:, None]
    bed += rum * 0.9 * A.env(N, [(0, 0), (S.T_SW["io"], 0), (S.T_SW["io"] + 0.6, 1), (S.T_SW["tit"] - 0.3, 1), (S.T_SW["tit"], 0), (S.DUR, 0)])[:, None]
    hiss = np.stack([A.bp(r.standard_normal(N), 2500, 9000) for _ in range(2)], 1)
    pulses = sum(np.exp(-((tt - tp) / 0.25) ** 2) for tp in np.arange(S.T_SW["io"] + 0.7, S.T_SW["tit"] - 0.3, 0.9))
    bed += hiss * (0.06 * pulses)[:, None]
    # Titan: a low hazy wind
    wind = np.stack([A.bp(r.standard_normal(N), 150, 900) for _ in range(2)], 1) * (1 + 0.6 * np.sin(2 * np.pi * 0.4 * tt[:, None] + np.array([0, 1.3])))
    bed += wind * 0.35 * A.env(N, [(0, 0), (S.T_SW["tit"], 0), (S.T_SW["tit"] + 0.8, 1), (S.T_SW["gan"] - 0.3, 1), (S.T_SW["gan"], 0), (S.DUR, 0)])[:, None]
    # Ganymede: riser into the swap
    bed += A.riser(N, S.T_SW["gan"] - 0.9, S.T_SW["gan"], seed=66) * 0.5
    # the finale: a rising pop per moon
    for j, k in enumerate(S.POP_ORDER):
        bed += pluck(S.T_POP[k], 523.25 * 2 ** ((0, 2, 4, 7, 9, 12, 14)[j] / 12), 0.10)
        bed += A.thump(N, S.T_POP[k], 0.45)
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
    A.write_srt(os.path.join(HERE, "..", "out", "other-moons.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
