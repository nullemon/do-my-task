"""Sound for "What If the Moon Got Closer?": voice chain; an orchestral pad (detuned, filtered saw "strings" plus a soft
brass fifth) that climbs a step with every closer Moon; a whoosh + implosion sweep + sub thump + shimmer bloom at every
swap; a tidal rumble that grows with the tides (1/d^3, on a log scale) and breathes in slow surges; quake thumps;
cracking and grinding as the Moon reaches the Roche limit, a huge boom as it breaks, a debris hiss and a bright
shimmer as the ring forms; a white-out riser and a low hit as today's Moon returns. Ducked under the voice, two-pass
loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/moon-closer.srt"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per stage: (root Hz, intervals, filter cutoff Hz, level) -- climbing, darker, then huge
CHORDS = {"today": (110.0, (0, 7, 12, 16, 19), 900, 0.8), "d200": (116.5, (0, 7, 12, 15, 19), 1100, 0.85),
          "d100": (123.5, (0, 7, 12, 15, 19, 22), 1400, 0.9), "d50": (130.8, (0, 7, 12, 15, 18, 24), 1700, 0.95),
          "d20": (138.6, (0, 7, 12, 14, 19, 24), 2100, 1.05), "roche": (146.8, (0, 7, 12, 16, 19, 24, 28), 3200, 1.2),
          "end": (110.0, (0, 7, 12, 16, 19, 24), 1200, 0.85)}


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


def crackle(t0, t1, rate0, rate1, seed, gain=0.3):
    """rock cracking: random sharp clicks + short band-passed bursts, rate rising from rate0 to rate1 per second"""
    out = np.zeros((N, 2)); r = np.random.default_rng(seed); t = t0
    while t < t1:
        u = (t - t0) / (t1 - t0); a = int(t * SR); n = int(r.uniform(0.01, 0.08) * SR)
        if a + n >= N: break
        x = A.bp(r.standard_normal(n), r.uniform(300, 900), r.uniform(2500, 7000)) * np.exp(-np.arange(n) / SR / r.uniform(0.004, 0.02))
        pan = r.uniform(0.2, 0.8); g = gain * r.uniform(0.3, 1.0) * (0.4 + 0.6 * u)
        out[a:a + n, 0] += x * g * (1 - pan) * 2; out[a:a + n, 1] += x * g * pan * 2
        t += r.exponential(1 / (rate0 + (rate1 - rate0) * u))
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "today")] + list(S.SWAPS)
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, cut, lev = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.3, 1), (te - 0.4, 1.1), (te - 0.02, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.4, 1.1), (te - 0.02, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.4, 1), (S.DUR - 0.5, 1), (S.DUR, 0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    for i, (ts, k) in enumerate(S.SWAPS):
        if k == "end": continue
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 0.8 + 0.15 * i)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.30)
    bed += A.shimmer(N, 0.3, S.T_SW["d200"] - 0.3, seed=61, gain=0.10)                    # moonlight sparkle
    # tidal rumble: grows with log10(tide factor), breathing in slow surges
    r = np.random.default_rng(62)
    lvl = np.zeros(N)
    for ts, k in [(0.0, "today")] + list(S.SWAPS):
        kk = "today" if k == "end" else k
        lvl = np.where(tt >= ts, math.log10(max(S.BK[kk]["tide"], 1.0)) / 4.0, lvl)
    lvl = A.lp(lvl, 1.5, 1)
    rum = np.stack([A.lp(r.standard_normal(N), 110, 2) for _ in range(2)], 1)
    surge = 0.65 + 0.35 * np.sin(2 * np.pi * tt / 2.6 * (1 + 1.5 * lvl))
    bed += rum * (2.2 * lvl ** 1.3 * surge)[:, None]
    wash = np.stack([A.bp(r.standard_normal(N), 250, 1800) for _ in range(2)], 1)            # surf-like surge wash
    bed += wash * (0.10 * lvl * np.clip(np.sin(2 * np.pi * tt / 2.6 * (1 + 1.5 * lvl)), 0, 1) ** 2)[:, None]
    for tq, s in S.QUAKES:
        bed += A.thump(N, tq, 0.55 * s)
    # Roche limit: cracking, grinding, the break, debris, the ring
    bed += crackle(S.T_CRACK - 0.2, S.T_RIP + 0.6, 4, 40, 70, 0.22)
    grind = np.stack([A.bp(r.standard_normal(N), 60, 400) for _ in range(2)], 1)
    bed += grind * (1.2 * A.env(N, [(0, 0), (S.T_CRACK - 0.2, 0), (S.T_RIP, 1), (S.T_RIP + 0.3, 0.2), (S.T_BACK, 0), (S.DUR, 0)]))[:, None]
    bed += A.riser(N, S.T_RIP - 0.8, S.T_RIP, seed=67) * 0.6
    bed += A.thump(N, S.T_RIP, 1.8)
    bed += A.hit(N, S.T_RIP, gain=0.40, root=41.2)
    deb = np.stack([A.bp(r.standard_normal(N), 1500, 9000) for _ in range(2)], 1)
    bed += deb * (0.10 * A.env(N, [(0, 0), (S.T_RIP, 0), (S.T_RIP + 0.08, 1), (S.T_RING + 0.5, 0.5), (S.T_WO0, 0.2), (S.T_BACK, 0), (S.DUR, 0)]))[:, None]
    bed += A.shimmer(N, S.T_RING - 0.3, S.T_WO0 + 0.2, seed=71, gain=0.30)
    bed += bloom_swell(S.T_RING, 72, 0.45)
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.1
    bed += A.hit(N, S.T_BACK, gain=0.45, root=55.0)
    bed += A.shimmer(N, S.T_BACK + 0.3, S.DUR - 0.2, seed=73, gain=0.08)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "moon-closer.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
