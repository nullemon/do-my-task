"""Sound for "Everything That Happens in Space While You Watch This Short", locked to the picture events in short.py.
Music: a warm pad and a plucked arpeggio at 75 BPM (one beat = the Sun's 0.8 s pulse), soft counter ticks that grow
busier as counters stack up. Events: a whoosh, bell and sub thump for every new counter card; sub pulses on the Sun's fusion
beats; swishes for bright meteors; a wind/rumble bed that follows the speed lines' actual drive; a shimmer for star
births; distant booms for supernova flashes (a burst on "explode"); a warm swell for the sunlight wavefronts; a riser into
the end white-out, and the same white flash at t = 0 gets the impact, so the loop lands on a hit.
Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/while-you-watch.srt"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(round(S.NFR / S.FPS * SR)); t = np.arange(N) / SR
R = np.random.default_rng(2026)
NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)
BEAT = 0.8


def at(x, t0):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(len(x), N - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    return out


def pan2(x, p): return np.stack([x * (1 - p), x * p], 1) * 2 ** 0.5


CH = {"F": (41, 48, 53, 57, 60, 65), "Dm": (38, 45, 50, 53, 57, 62), "Bb": (46, 53, 58, 62, 65, 70), "C": (48, 55, 60, 64, 67, 72),
      "Gm": (43, 50, 55, 58, 62, 67), "Csus": (48, 55, 60, 65, 67, 72), "Fadd9": (41, 48, 53, 57, 60, 67)}
LNS = S.LN
SEQ = [("F", 0.0), ("Dm", LNS["orbit"]["start"]), ("Bb", LNS["sun"]["start"]), ("C", LNS["dust"]["start"]), ("Gm", LNS["gal"]["start"]),
       ("Bb", S.T_CMB), ("Dm", LNS["stars"]["start"]), ("C", S.T_SN), ("Bb", LNS["light"]["start"]), ("Csus", S.T_END), ("C", S.T_WO)]


def chord_at(tt):
    c = SEQ[0][0]
    for k, t0 in SEQ:
        if tt >= t0: c = k
    return CH[c]


def pad():
    out = np.zeros((N, 2))
    for i, (k, t0) in enumerate(SEQ):
        t1 = SEQ[i + 1][1] if i + 1 < len(SEQ) else S.DUR + 1
        e = A.env(N, [(0, 0), (max(t0 - 0.15, 0), 0), (t0 + 0.25, 1), (t1 - 0.05, 1), (t1 + 0.35, 0), (S.DUR + 2, 0)])
        if i == 0: e = A.env(N, [(0, 1), (t1 - 0.05, 1), (t1 + 0.35, 0), (S.DUR + 2, 0)])
        x = np.zeros((N, 2))
        for j, m in enumerate(CH[k]):
            f = NOTE(m); a = 0.45 if j == 0 else 0.25
            for c in range(2):
                det = 1 + R.uniform(-0.0025, 0.0025)
                x[:, c] += a * np.sin(2 * np.pi * f * det * t + R.uniform(0, 6.28)) * (1 + 0.2 * np.sin(2 * np.pi * R.uniform(0.1, 0.3) * t))
        out += x * e[:, None]
    air = np.stack([A.bp(R.standard_normal(N), 1200, 6000) for _ in range(2)], 1) * 0.04
    return (A.lp(out, 2400) + air) * 0.05


def pluck(f, dur=0.9, bright=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = sum(p * np.sin(2 * np.pi * f * m * tt) * np.exp(-tt / (d / m ** 0.5)) for m, p, d in ((1, 1.0, 0.45), (2, 0.5 * bright, 0.30), (3, 0.25 * bright, 0.2), (4, 0.12 * bright, 0.15)))
    return x * (1 - np.exp(-tt / 0.003))


def arpeggio():
    out = np.zeros((N, 2)); step = BEAT / 4; k = 0; tt = 0.2
    pat = [0, 2, 3, 4, 5, 4, 3, 2]
    while tt < S.DUR:
        dens = 0.35 + 0.65 * S.ramp(tt, 5.0, 12.0)
        if k % 2 == 0 or R.uniform() < dens:
            ch = chord_at(tt); m = ch[pat[k % 8]] + 12
            g = (0.55 if k % 4 == 0 else 0.32) * (0.6 + 0.4 * S.ramp(tt, 2, 10))
            out += at(pan2(pluck(NOTE(m), 0.8, 0.8), 0.3 + 0.4 * ((k * 3) % 8) / 7) * g, tt)
        tt += step; k += 1
    return out * 0.06


def bass():
    """sub pulse on every Sun beat (t = 0.2 + 0.8 k), much stronger in the fusion beat"""
    out = np.zeros((N, 2)); tt = 0.2
    while tt < S.DUR:
        sb = S.ramp(tt, S.T_SUN - 0.2, S.T_SUN + 0.4) * (1 - 0.7 * S.ramp(tt, S.T_DUST, S.T_DUST + 1.0))
        root = NOTE(chord_at(tt)[0] - 12)
        n = int(0.7 * SR); x = np.arange(n) / SR
        f = root * (1 + 0.8 * np.exp(-x / 0.03)); ph = 2 * np.pi * np.cumsum(f) / SR
        y = np.sin(ph) * np.exp(-x / 0.25) * (0.18 + 0.75 * sb) * (0.5 + 0.5 * S.ramp(tt, 1, 6))
        out += at(np.stack([y, y], 1), tt)
        tt += BEAT
    return out


def card(t0, i, col):
    """whoosh into the card, bright bell chord on the hit, sub thump"""
    out = np.zeros((N, 2)); d = 0.45; a = int((t0 - d) * SR); n = int(d * SR)
    if a > 0:
        u = np.linspace(0, 1, n); nz = A.bp(R.standard_normal(n), 500, 6000) * u ** 2.4
        out[a:a + n] += np.stack([nz * (1 - 0.6 * u), nz * (0.4 + 0.6 * u)], 1) * 0.5
    ch = chord_at(t0 + 0.05)
    for j, m in enumerate((ch[2] + 24, ch[3] + 24, ch[4] + 24)):
        out += at(pan2(pluck(NOTE(m), 2.0, 0.5), 0.3 + 0.2 * j) * 0.22, t0 + 0.012 * j)
    out += A.thump(N, t0, 0.55)
    return out


def swish(t0, dur, pan, seed):
    out = np.zeros((N, 2)); n = int(dur * SR); a = int(t0 * SR)
    if a + n >= N: return out
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 2500, 9000) * np.sin(np.pi * u) ** 2 * (1 - u) ** 0.5
    out[a:a + n] = pan2(nz, pan)
    return out


def boom(t0, size, pan, seed):
    out = np.zeros((N, 2)); n = int(2.2 * SR); a = int(t0 * SR); n = min(n, N - a)
    if n <= 0: return out
    r = np.random.default_rng(seed); x = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(45 + 60 * np.exp(-x / 0.05)) / SR) * np.exp(-x / 0.5)
    crack = A.bp(r.standard_normal(n), 300, 3000) * np.exp(-x / 0.25) * 0.5
    y = (body + crack) * size
    out[a:a + n] = pan2(A.lp(y, 1800), pan)
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    sc = S.Scene(True)
    bed = pad() + arpeggio() + bass()
    # counter ticks: a quiet clock that gets busier as more counters are running
    for i, c in enumerate(S.COUNTERS):
        bed += A.ticks(N, c[1] + 0.3, S.DUR, rate=3.0 + 0.6 * i, gain=0.020 + 0.002 * i)
    for i, c in enumerate(S.COUNTERS):
        if c[1] > 0.6: bed += card(c[1], i, c[5])
    bed += card(S.T_END, 8, S.CYAN) * 0.8
    # meteors (only the bright ones get a swish)
    for k, m in enumerate(sc.meteors):
        if m["t0"] < S.DUR - 0.5 and (m["I"] > 1.05 or S.T_DUST <= m["t0"] <= S.T_DUST + 3.5):
            bed += swish(m["t0"], m["dur"] * 1.1, float(np.clip(m["x"] / 1080, 0.1, 0.9)), 300 + k) * (0.10 * m["I"])
    # speed lines: wind roar following the drive
    drive = np.interp(t, S._ts, [S.speed_drive(x) for x in S._ts])
    wind = np.stack([A.bp(R.standard_normal(N), 150, 3000) for _ in range(2)], 1)
    hiss = np.stack([A.bp(R.standard_normal(N), 3000, 9000) for _ in range(2)], 1)
    bed += (wind * 0.16 + hiss * 0.05) * np.clip(drive, 0, 2)[:, None] ** 1.3
    bed += A.riser(N, S.T_CMB - 0.9, S.T_CMB + 0.05, seed=71) * 0.5
    # star births: shimmer
    bed += A.shimmer(N, S.T_STARS - 0.6, S.T_STARS + 4.0, seed=72, gain=0.30)
    bed += A.shimmer(N, 12.0, S.T_STARS - 0.6, seed=73, gain=0.08)
    # supernovae: distant booms
    for k, (ts, gi, _, _) in enumerate(sc.sne):
        if 0 < ts < S.DUR - 0.3:
            big = ts >= S.T_EXPLODE - 0.2 and ts < S.T_EXPLODE + 0.8
            bed += boom(ts, 0.35 if big else 0.18, float(np.clip(sc.gals[gi]["x"] / 1080, 0.1, 0.9)), 500 + k)
    # sunlight: warm swell + light wavefront chimes
    bed += A.shimmer(N, S.T_LIGHT, S.T_END + 1.0, seed=74, gain=0.18)
    sw = A.env(N, [(0, 0), (S.T_LIGHT - 0.2, 0), (S.T_LIGHT + 0.8, 1), (S.T_END + 1.5, 0.6), (S.DUR, 0.3)])
    bed += A.drone(N, root=NOTE(46 - 12), seed=75, bright=0.4) * 0.6 * sw[:, None]
    # end: riser into the white-out; the loop's impact sits at t = 0 (the white flash fading in the first frame)
    bed += A.riser(N, S.T_WO - 1.2, S.DUR, seed=76) * 0.9
    bed += A.thump(N, 0.0, 0.8)
    bed += A.shimmer(N, 0.0, 1.6, seed=77, gain=0.25) * A.env(N, [(0, 1), (1.6, 0), (S.DUR, 0)])[:, None]
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.62
    mix *= np.clip((N / SR - t) / 0.02, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "while-you-watch.srt"), S.PL, lambda k: pc[k])
    print("ok", N / SR)


if __name__ == "__main__":
    main()
