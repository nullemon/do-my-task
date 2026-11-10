"""Sound for "Every Star You See Is a Date", locked to the picture events in short.py: a warm evolving pad + plucked
arpeggio (music), a soft afterglow shimmer as the stars switch on, a bell chime + ring-burst whoosh on every label, a sub
hit for Andromeda, whooshes that follow the sky's actual turning speed, a riser + shimmer into the time-machine swirl, a
pulse thump for the "alive" wave. Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/star-dates.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); t = np.arange(N) / SR
R = np.random.default_rng(2026)
NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)


def at(x, t0):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(len(x), N - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    return out


def pan2(x, p): return np.stack([x * (1 - p), x * p], 1) * 2 ** 0.5


# chord plan (MIDI): D - Bm - G - A ... -> lift (E) in the swirl -> D at the end
CH = {"D": (50, 57, 62, 66, 69, 74), "Bm": (47, 54, 59, 62, 66, 71), "G": (43, 50, 55, 59, 62, 67), "A": (45, 52, 57, 61, 64, 69),
      "Em": (52, 59, 64, 67, 71, 76), "Dsus": (50, 57, 62, 67, 69, 74)}
SEQ = [("D", 0.0), ("Bm", S.LN["title"]["start"]), ("G", S.LN["list"]["start"]), ("A", S.LN["deneb"]["start"]),
       ("Bm", S.LN["m31"]["start"]), ("Em", S.T_SWIRL0), ("G", S.LN["myth"]["start"] + 0.3), ("A", S.T_LIGHT - 0.2),
       ("Dsus", S.LN["end"]["start"]), ("D", S.LN["end"]["start"] + 1.4)]


def chord_at(tt):
    c = SEQ[0][0]
    for k, t0 in SEQ:
        if tt >= t0: c = k
    return CH[c]


def pad():
    out = np.zeros((N, 2))
    for i, (ch, t0) in enumerate(SEQ):
        t1 = SEQ[i + 1][1] if i + 1 < len(SEQ) else S.DUR
        a, b = int(max(0, t0 - 0.5) * SR), min(N, int((t1 + 0.9) * SR))
        tt = np.arange(b - a) / SR
        xf = np.clip(tt / 0.9, 0, 1) * np.clip(((b - a) / SR - tt) / 0.9, 0, 1)
        if i == 0: xf = np.clip(((b - a) / SR - tt) / 0.9, 0, 1)
        seg = np.zeros((b - a, 2))
        for j, m in enumerate(CH[ch]):
            f = NOTE(m)
            for c in range(2):
                det = 1 + (0.003 if c else -0.003) * (1 + j % 2)
                v = sum(np.sin(2 * np.pi * f * det * k * tt + R.uniform(0, 6.28)) / k ** 1.5 for k in range(1, 6))
                seg[:, c] += v * (0.9 if j < 2 else 0.55) * (1 + 0.2 * np.sin(2 * np.pi * 0.25 * tt + j))
        out[a:b] += seg * xf[:, None]
    out = A.lp(out, 2200, 2) * 0.045
    sw = A.env(N, [(0, 0.8), (S.T_SWIRL0 - 1.0, 0.9), (S.T_SWIRL0 + 0.5, 1.4), (S.T_SWIRL1, 1.1), (S.LN["end"]["start"], 1.0), (S.DUR, 0.8)])
    return out * sw[:, None]


def pluck(f, dur=0.5, bright=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = sum((0.6 ** (k - 1)) * bright ** (k - 1) * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt * (3 + 2.5 * k)) for k in range(1, 6))
    return x * (1 - np.exp(-tt / 0.002))


def arp():
    """bright plucked 8ths (108 bpm) cycling the chord tones an octave up; drops out around the big beats"""
    out = np.zeros((N, 2)); step = 60 / 108 / 2; tt = S.LN["hook"]["start"] + 0.6; k = 0
    pat = (0, 2, 4, 5, 3, 4, 2, 1)
    while tt < S.DUR - 0.4:
        ch = chord_at(tt); m = ch[pat[k % 8] % len(ch)] + 12
        g = 0.10 * (0.8 if k % 2 else 1.0)
        if S.T_SWIRL0 - 0.2 < tt < S.T_SWIRL1: g *= 1.3
        out += at(pan2(pluck(NOTE(m), 0.6), 0.3 + 0.4 * ((k * 3) % 5) / 4), tt) * g
        tt += step; k += 1
    e = A.env(N, [(0, 0), (S.LN["hook"]["start"] + 0.5, 0.3), (S.LN["title"]["start"], 0.8), (S.LN["end"]["start"], 0.8), (S.DUR - 0.2, 0.2), (S.DUR, 0)])
    return A.lp(out, 6000, 2) * e[:, None]


def chime(t0, root, big=1.0, p=0.5):
    n = int(2.2 * SR); tt = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * NOTE(root) * m * tt) * np.exp(-tt / d) for m, a, d in ((1, 1.0, 1.2), (2.0, 0.5, 0.8), (2.76, 0.35, 0.5), (4.07, 0.2, 0.3), (5.4, 0.12, 0.2)))
    x *= (1 - np.exp(-tt / 0.002)) * 0.22 * big
    return at(pan2(x, p), t0)


def whoosh(t0, dur=0.6, g=0.3, f0=400, f1=4000):
    n = int(dur * SR); u = np.linspace(0, 1, n)
    x = R.standard_normal(n)
    y = np.zeros(n); seg = 8
    for i in range(seg):
        a, b = i * n // seg, (i + 1) * n // seg
        fc = f0 * (f1 / f0) ** (i / seg)
        y[a:b] = A.bp(x, fc * 0.7, min(fc * 1.4, 20000))[a:b]
    e = np.sin(np.pi * u) ** 2
    return at(np.stack([y * e, np.roll(y, 300) * e], 1) * g, t0)


def sky_wind():
    """noise whoosh whose level follows the sky's turning speed (deg/s)"""
    fr = np.arange(0, S.DUR, 1 / 30)
    sp = np.array([abs(S.LST(x + 1 / 30) - S.LST(x)) * 15 * 30 for x in fr])
    g = np.interp(t, fr, np.clip(sp / 80, 0, 1) ** 1.2)
    g = A.lp(g, 4, 1)
    nz = np.stack([R.standard_normal(N), R.standard_normal(N)], 1)
    lo = A.bp(nz, 250, 1200); hi = A.bp(nz, 1800, 7000)
    return (lo * 0.5 + hi * 0.25 * g[:, None]) * g[:, None] * 0.55


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    fx = np.zeros((N, 2))
    fx += A.shimmer(N, 0.05, S.T_DUSK1 + 0.8, seed=3, gain=0.10)                    # stars switching on
    fx += A.riser(N, 0.0, 0.5, seed=4) * 0.0
    roots = {"sirius": 81, "betel": 74, "arct": 76, "vega": 83, "deneb": 79, "m31": 86}
    for i, lb in enumerate(S.LABELS):
        key, tn, tb = lb[0], lb[7], lb[8]
        p = 0.35 + 0.3 * (i % 3) / 2
        fx += chime(tn - 0.01, roots[key], 0.8, p) + whoosh(tn - 0.05, 0.45, 0.10, 2000, 9000)
        fx += chime(tb - 0.01, roots[key] + 7, 1.2, 1 - p) + chime(tb + 0.12, roots[key] + 12, 0.6, p)
        fx += whoosh(tb - 0.12, 0.7, 0.20, 300, 6000) + A.thump(N, tb, 0.25 if key != "m31" else 0.7)
        if key == "m31": fx += A.hit(N, tb, gain=0.35, root=36.7)
    fx += A.riser(N, S.T_SWIRL0 - 1.6, S.T_SWIRL0 + 0.2, seed=9) * 0.20 + A.shimmer(N, S.T_SWIRL0, S.T_SWIRL1 + 1.5, seed=7, gain=0.14)
    fx += A.hit(N, S.T_SWIRL0 + 0.2, gain=0.25, root=41.2)
    fx += A.thump(N, S.T_WAVE, 0.6) + A.thump(N, S.T_WAVE + 0.42, 0.35) + whoosh(S.T_WAVE, 1.6, 0.22, 200, 5000)
    fx += chime(S.T_LIFE, 78, 0.7, 0.4) + chime(S.T_LIGHT, 81, 0.7, 0.6)
    fx += A.shimmer(N, S.T_LOOP - 0.5, S.DUR, seed=11, gain=0.07)
    music = pad() * 1.6 + arp()
    bed = A.duck(music + sky_wind(), voice, depth=0.45) + A.duck(fx, voice, depth=0.2)
    mix = voice * 1.0 + bed * 0.8
    mix *= np.clip((S.DUR - t) / 0.25, 0, 1)[:, None] * np.clip(t / 0.03, 0, 1)[:, None]
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "star-dates.srt"), S.PL, lambda k: pc[k], max_words=9)
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
