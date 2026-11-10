"""Sound for the Short, locked to the picture events in short.py.
 visible : birdsong + light breeze + bright pad
 infrared: warm hum swelling as the lamps and house heat up, soft crackle
 radio   : band-limited static + heterodyne whistles (a radio tuning across the sky)
 micro   : the hiss of the CMB (a slice of old-TV static) + shimmer
 gamma   : deep drone, Geiger-counter clicks, cosmic-ray zips that hit the Moon, riser + hit on "blazes",
           a gamma-ray-burst zap + boom
 every switch: a stereo whoosh that follows the wipe + a soft thump; the snap back: reverse swell + white-out chime.
Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/gamma-ray-eyes.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); t = np.arange(N) / SR
R = np.random.default_rng(2026)
M0 = {m: ts for m, ts in S.SEQ[:-1]}                 # mode start times
T_IR, T_RA, T_MI, T_GA, T_END = S.SW["ir"], S.SW["radio"], S.SW["micro"], S.SW["gamma"], S.SW["vis2"]


def noise2(n=N): return np.stack([R.standard_normal(n), R.standard_normal(n)], 1)
def at(x, t0, n_out=N):
    out = np.zeros((n_out, 2)); a = int(t0 * SR); n = min(len(x), n_out - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    elif a < 0 and len(x) + a > 0: out[:min(len(x) + a, n_out)] = x[-a:-a + min(len(x) + a, n_out)]
    return out
def win(a, b, fi=0.25, fo=0.35):
    return A.env(N, [(0, 0), (max(a - fi, 0), 0), (a, 1), (b, 1), (b + fo, 0), (S.DUR + 1, 0)])


def whoosh(t0, dur=0.75, up=True, gain=1.0):
    n = int(dur * SR); u = np.linspace(0, 1, n)
    nz = np.stack([R.standard_normal(n), R.standard_normal(n)], 1)
    fc = 350 * (20 ** (u if up else 1 - u)) if up else 7000 * (0.05 ** u)
    out = np.zeros((n, 2))
    for f in (300, 450, 700, 1100, 1700, 2600, 4000, 6000, 9000):
        g = np.exp(-((np.log(f) - np.log(fc)) / 0.55) ** 2)
        out += A.bp(nz, f * 0.8, min(f * 1.25, 20000)) * g[:, None]
    e = np.sin(np.pi * u) ** 1.5 * (0.6 + 0.4 * u)
    pan = 0.15 + 0.7 * u                                      # follows the wipe (left -> right)
    out[:, 0] *= e * (1 - pan) * 2; out[:, 1] *= e * pan * 2
    return at(out * 0.9 * gain, t0)


def birds():
    out = np.zeros((N, 2))
    tt = 0.3
    while tt < S.DUR:
        f0 = R.uniform(2800, 4600); nsyl = R.integers(2, 6); pan = R.uniform(0.15, 0.85); g = R.uniform(0.3, 1.0)
        for k in range(nsyl):
            n = int(R.uniform(0.05, 0.11) * SR); x = np.arange(n) / SR; u = x / x[-1]
            f = f0 * (1 + 0.25 * np.sin(np.pi * u) * R.choice([-1, 1])) + 600 * u
            c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) ** 2 * g * 0.05
            out += at(np.stack([c * (1 - pan), c * pan], 1) * 2, tt + k * R.uniform(0.09, 0.15))
        tt += R.uniform(0.5, 1.4)
    e = A.env(N, [(0, 1), (T_IR, 1), (T_IR + 0.3, 0), (T_END + 0.3, 0), (T_END + 1.0, 1), (S.DUR, 1)])
    breeze = A.lp(noise2(), 700, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t))[:, None] * 0.12
    return (out + breeze) * e[:, None]


def ir_bed():
    hum = sum(g * np.sin(2 * np.pi * 55 * k * t + k) for k, g in ((1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12)))
    sw = A.env(N, [(0, 0), (T_IR + 0.2, 0), (T_IR + 1.8, 1), (T_RA, 1), (T_RA + 0.35, 0), (S.DUR, 0)])
    crack = (R.uniform(0, 1, N) < 0.0012).astype(float) * R.standard_normal(N)
    crack = A.bp(crack, 1500, 7000) * 1.5
    air = A.bp(noise2(), 200, 900) * 0.25
    return (np.stack([hum, hum * 0.97], 1) * 0.06 + np.stack([crack, np.roll(crack, 300)], 1) * 0.25 + air * 0.4) * sw[:, None]


def radio_bed():
    w = win(T_RA, T_MI, 0.1, 0.3)
    st = A.bp(noise2(), 900, 4500) * 0.30 * (0.7 + 0.3 * np.sin(2 * np.pi * 3.3 * t))[:, None]
    wh = np.zeros(N)
    for k in range(5):                                              # heterodyne whistles sweeping
        a, b = T_RA + 0.3 + k * 1.35, T_RA + 0.3 + k * 1.35 + 1.1
        ia, ib = int(a * SR), min(int(b * SR), N)
        if ib <= ia: continue
        u = np.linspace(0, 1, ib - ia); f = R.uniform(600, 1400) * 2 ** ((u - 0.5) * R.choice([-2.2, 2.2]))
        wh[ia:ib] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) ** 2 * 0.10
    pulsar = np.zeros(N); tt = T_RA + 0.2
    while tt < T_MI:                                                # a slow pulsar-like tick
        i = int(tt * SR); n = int(0.02 * SR)
        if i + n < N: pulsar[i:i + n] += np.sin(2 * np.pi * 900 * np.arange(n) / SR) * np.exp(-np.arange(n) / SR / 0.004) * 0.25
        tt += 0.714
    return (st + np.stack([wh, wh], 1) + np.stack([pulsar * 0.6, pulsar], 1)) * w[:, None]


def micro_bed():
    w = win(T_MI, T_GA, 0.1, 0.3)
    hiss = A.hp(noise2(), 2500) * 0.10 + A.bp(noise2(), 400, 2500) * 0.05
    return hiss * w[:, None] + A.shimmer(N, T_MI + 0.3, T_GA, seed=3, gain=0.10)


def gamma_bed():
    w = win(T_GA, T_END, 0.05, 0.15)
    sub = sum(g * np.sin(2 * np.pi * 36.7 * k * t + 0.3 * np.sin(2 * np.pi * 0.2 * t)) for k, g in ((1, 1.0), (1.5, 0.4), (2, 0.35), (3, 0.12)))
    drone = np.stack([sub, sub * 0.98], 1) * 0.10 + A.lp(noise2(), 300, 2) * 0.10
    # Geiger clicks: denser during the cosmic rays
    rate = A.env(N, [(0, 0), (T_GA, 6), (S.T_CR0, 10), (S.T_BLAZE, 40), (S.T_BLAZE + 1.2, 9), (T_END, 9), (T_END + 0.01, 0), (S.DUR, 0)])
    clicks = (R.uniform(0, 1, N) < rate / SR).astype(float)
    ck = np.convolve(clicks, np.exp(-np.arange(int(0.003 * SR)) / (0.0006 * SR)) * np.sign(np.sin(np.arange(int(0.003 * SR)) * 0.9)), "same")
    ck = A.hp(ck, 1200)
    pan = 0.5 + 0.4 * np.sin(np.arange(N) * 0.00011)
    out = drone * w[:, None] + np.stack([ck * (1 - pan), ck * pan], 1) * 0.35
    return out


def ray_zips(sc):
    out = np.zeros((N, 2))
    for r in sc.rays:
        d = r["fl"]; n = int((d + 0.08) * SR); x = np.arange(n) / SR; u = np.clip(x / d, 0, 1)
        f = 3500 * (0.25 ** u)
        z = np.sin(2 * np.pi * np.cumsum(f) / SR) * u ** 2 * (x < d) * 0.07
        z += A.hp(R.standard_normal(n), 3000) * np.exp(-np.maximum(x - d, 0) / 0.01) * (x >= d) * 0.25
        pan = 0.5 + 0.45 * np.cos(r["a"])
        out += at(np.stack([z * (1 - pan), z * pan], 1), r["ta"] - d)
    return out


def grb():
    n = int(1.2 * SR); x = np.arange(n) / SR
    zap = A.bp(R.standard_normal(n), 1500, 9000) * np.exp(-x / 0.06) * 1.2 + np.sin(2 * np.pi * 2400 * np.exp(-x / 0.15) * x) * np.exp(-x / 0.25) * 0.25
    return at(np.stack([zap * 0.35, zap * 0.9], 1), S.T_GRB) + A.thump(N, S.T_GRB + 0.02, 0.35)


NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)
CH = {"vis": (50, 57, 62, 66, 69, 74), "ir": (46, 53, 58, 62, 65, 70), "radio": (43, 50, 55, 59, 62, 67), "micro": (45, 52, 57, 61, 64, 69),
      "gamma": (41, 48, 53, 56, 60, 65), "end": (50, 57, 62, 66, 69, 76)}


def pad():
    seq = [("vis", 0.0), ("ir", T_IR), ("radio", T_RA), ("micro", T_MI), ("gamma", T_GA), ("end", T_END)]
    out = np.zeros((N, 2))
    for i, (ch, t0) in enumerate(seq):
        t1 = seq[i + 1][1] if i + 1 < len(seq) else S.DUR
        a, b = int(max(0, t0 - 0.15) * SR), min(N, int((t1 + 0.6) * SR))
        tt = np.arange(b - a) / SR
        xf = np.clip(tt / 0.25, 0, 1) * np.clip(((b - a) / SR - tt) / 0.5, 0, 1)
        seg = np.zeros((b - a, 2))
        for j, m in enumerate(CH[ch]):
            f = NOTE(m)
            for c in range(2):
                det = 1 + (0.003 if c else -0.003) * (1 + j % 2)
                v = sum(np.sin(2 * np.pi * f * det * k * tt + R.uniform(0, 6.28)) / k ** 1.3 for k in range(1, 6))
                seg[:, c] += v * (0.9 if j < 2 else 0.55)
        # rhythmic pulse (16ths at 112 bpm) for constant motion
        gate = 0.65 + 0.35 * (np.sin(2 * np.pi * (112 / 60 * 4) * (tt + t0)) > -0.2)
        out[a:b] += seg * (xf * gate)[:, None]
    out = A.lp(out, 2600, 2) * 0.045
    sw = A.env(N, [(0, 0.0), (0.05, 0.8), (S.DUR - 0.25, 1.0), (S.DUR, 0)])
    return out * sw[:, None]


def kick():
    """soft four-on-the-floor sub pulse from the radio switch to the end (energy), stops for the snap"""
    out = np.zeros((N, 2)); beat = 60 / 112
    tt = T_RA
    while tt < S.DUR - 0.3:
        if not (T_END - 0.3 < tt < T_END + 0.6):
            g = 0.16 if tt < T_GA else 0.24
            out += A.thump(N, tt, g) * 0.5
        tt += beat
    return A.lp(out, 140, 2)


def main():
    sc = S.Scene(True)
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    fx = np.zeros((N, 2))
    for k in ("ir", "radio", "micro", "gamma"):
        fx += whoosh(S.SW[k] - 0.12, 0.75, gain=1.0) + A.thump(N, S.SW[k] + 0.22, 0.30)
    fx += A.riser(N, T_GA - 2.2, T_GA + 0.05, seed=4) * 0.25 + A.hit(N, T_GA + 0.05, gain=0.30, root=41.2)
    fx += A.riser(N, S.T_CR0, S.T_BLAZE, seed=5) * 0.30 + A.hit(N, S.T_BLAZE, gain=0.55, root=36.7) + A.thump(N, S.T_BLAZE, 0.6)
    fx += ray_zips(sc) + grb()
    fx += A.riser(N, T_END - 1.0, T_END + 0.05, seed=6) * 0.22 + whoosh(T_END - 0.05, 0.5, up=False, gain=1.2)
    fx += A.shimmer(N, T_END + 0.05, S.DUR, seed=8, gain=0.12) + A.hit(N, T_END + 0.08, gain=0.22, root=73.4)
    bed = birds() + ir_bed() + radio_bed() + micro_bed() + gamma_bed() + pad() * 1.6 + kick()
    bed = A.duck(bed + fx * 0.6, voice, depth=0.35) + fx * 0.4
    mix = voice * 1.0 + bed * 0.80
    mix *= np.clip((S.DUR - t) / 0.20, 0, 1)[:, None] * np.clip(t / 0.03, 0, 1)[:, None]
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "gamma-ray-eyes.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
