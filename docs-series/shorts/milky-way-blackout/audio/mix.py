"""Sound for the Short, locked to the picture events in short.py: city hum + traffic -> quake rumble, rattles and brown-out
buzz -> transformer pops as the lamps die -> silence -> crickets + wind -> an emotional pad that swells with the Milky Way
-> the city hum powers back up at the end. Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/milky-way-blackout.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); t = np.arange(N) / SR
R = np.random.default_rng(2024)


def noise2(n=N): return np.stack([R.standard_normal(n), R.standard_normal(n)], 1)
def at(x, t0, n_out=N):
    """place a (n,2) clip at time t0 into a full-length buffer"""
    out = np.zeros((n_out, 2)); a = int(t0 * SR); n = min(len(x), n_out - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    return out


def city_bed():
    """mains hum (60 Hz, as in LA) + distant traffic + an occasional car pass"""
    hum = sum(g * np.sin(2 * np.pi * 60 * k * t + k) for k, g in ((1, 0.5), (2, 0.35), (3, 0.18), (5, 0.06)))
    hum = np.stack([hum, hum * 0.95], 1) * 0.05
    traffic = A.lp(noise2(), 380, 2) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t))[:, None] * 0.35
    cars = np.zeros((N, 2))
    for tc, pan in ((1.6, 0.3), (5.2, 0.7), (8.0, 0.4), (33.6, 0.6)):
        n = int(3.0 * SR); u = np.linspace(-1, 1, n); e = np.exp(-(u / 0.35) ** 2)
        x = A.bp(R.standard_normal(n), 200, 1800) * e * 0.18
        cars += at(np.stack([x * (1 - pan), x * pan], 1) * 2, tc - 1.5)
    return hum, traffic + cars


def quake():
    a = S.T_HIT - 1.1; b = S.T_SHAKE1 + 2.0
    e = A.env(N, [(0, 0), (a, 0), (S.T_HIT - 0.1, 0.5), (S.T_HIT + 0.05, 1.0), (S.T_HIT + 0.7, 0.8), (b, 0), (S.DUR, 0)])
    rumble = A.lp(noise2(), 70, 4) * 4.0 + A.lp(noise2(), 160, 2) * 0.6
    sub = np.sin(2 * np.pi * (24 + 6 * np.sin(2 * np.pi * 0.7 * t)) * t)[:, None] * 0.5
    x = (rumble + sub) * e[:, None]
    # rattles: windows, shelves, glass: dense random clicks in a band, following the shake
    rat = np.zeros(N); er = A.env(N, [(0, 0), (S.T_HIT - 0.05, 0), (S.T_HIT + 0.1, 1), (S.T_SHAKE1 + 0.4, 0), (S.DUR, 0)])
    idx = np.where(R.uniform(0, 1, N) < 0.004 * er)[0]
    rat[idx] = R.standard_normal(len(idx))
    rat = A.bp(rat, 1500, 6000) * 2.5 + A.bp(rat, 300, 900) * 1.5
    return x + np.stack([rat, np.roll(rat, 240)], 1) * 0.5 + A.thump(N, S.T_HIT - 0.02, 0.9)


def buzz_and_pops():
    """brown-out buzz (120 Hz, crackling) while the lights flicker; a transformer pop as each lamp dies; one big
    distant transformer flash-boom on the first wave"""
    saw = sum(np.sin(2 * np.pi * 120 * k * t) / k for k in range(1, 12))
    crack = (R.uniform(0, 1, N) < 0.002).astype(float) * R.standard_normal(N)
    flick = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 7.3 * t) + np.sin(2 * np.pi * 3.1 * t))
    e = A.env(N, [(0, 0), (S.T_HIT - 0.1, 0), (S.T_HIT + 0.2, 0.8), (S.T_OFF1 - 0.2, 1.0), (S.T_OFF1 + 0.05, 0), (S.DUR, 0)])
    bz = (saw * 0.25 * flick + A.hp(crack, 2500) * 1.2) * e
    out = np.stack([bz, bz], 1) * 0.35
    for i, tl in enumerate(S.LAMP_OFF + [S.T_OFF0 + 0.05]):
        big = i == len(S.LAMP_OFF)
        n = int(0.6 * SR); tt = np.arange(n) / SR
        arc = A.hp(R.standard_normal(n), 2000) * np.exp(-tt / (0.012 if not big else 0.03)) * (0.8 if not big else 1.2)
        tail = np.sin(2 * np.pi * 120 * tt) * np.exp(-tt / 0.08) * 0.2
        pan = R.uniform(0.25, 0.75)
        out += at(np.stack([(arc + tail) * (1 - pan), (arc + tail) * pan], 1) * (1.6 if not big else 1.0), tl - 0.01)
        if big: out += A.thump(N, tl, 0.55)
    # the hum dies with a power-down glide on the last wave
    return out


def power_hum(hum):
    """mains hum: fades + glides down at the blackout, powers up again with a clunk at the end"""
    g = A.env(N, [(0, 1), (S.T_OFF0, 1), (S.T_OFF1, 0.5), (S.T_OFF1 + 0.35, 0), (S.T_RET0 + 0.2, 0), (S.T_RET0 + 1.2, 0.8), (S.DUR, 1)])
    down = np.zeros(N); a, b = int((S.T_OFF1 - 0.3) * SR), int((S.T_OFF1 + 0.6) * SR)
    u = np.linspace(0, 1, b - a); f = 60 * (1 - 0.6 * u); ph = 2 * np.pi * np.cumsum(f) / SR
    down[a:b] = (np.sin(ph) + 0.5 * np.sin(2 * ph)) * (1 - u) * 0.05
    return hum * g[:, None] + np.stack([down, down], 1) + A.thump(N, S.T_RET0 + 0.25, 0.25)


def crickets():
    out = np.zeros((N, 2))
    for k in range(7):
        f0 = R.uniform(4100, 4900); per = R.uniform(0.55, 1.1); syl = R.integers(2, 5); pan = R.uniform(0.1, 0.9)
        g = R.uniform(0.25, 1.0) * 0.05; tt = R.uniform(0, per) + S.T_DRAIN0
        while tt < S.DUR:
            for s_ in range(syl):
                n = int(0.018 * SR); x = np.arange(n) / SR
                c = np.sin(2 * np.pi * f0 * x) * np.sin(np.pi * x / x[-1]) ** 2 * g
                out += at(np.stack([c * (1 - pan), c * pan], 1) * 2, tt + s_ * 0.032)
            tt += per * R.uniform(0.9, 1.1)
    e = A.env(N, [(0, 0), (S.T_DRAIN0 + 0.8, 0), (S.T_DRAIN1 + 1.0, 1), (S.T_RET0 + 0.5, 1), (S.DUR - 0.2, 0.25), (S.DUR, 0)])
    return out * e[:, None]


def wind():
    w = A.lp(noise2(), 520, 2) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.09 * t + 1))[:, None] + A.bp(noise2(), 900, 2500) * 0.08
    e = A.env(N, [(0, 0), (S.T_DRAIN0 + 0.4, 0), (S.T_DRAIN1, 0.6), (S.T_MW1, 0.8), (S.T_RET0, 0.8), (S.DUR, 0.3)])
    return w * e[:, None] * 0.35


NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)
CHORDS = {"D": (50, 57, 62, 66, 69, 76), "Bm": (47, 54, 59, 62, 66, 73), "G": (43, 50, 55, 59, 62, 69), "A": (45, 52, 57, 61, 64, 71), "Dsus": (50, 57, 62, 67, 69, 76)}


def pad():
    """warm, slowly evolving pad (detuned soft saws, low-passed), chord changes follow the narration"""
    seq = [("D", S.T_MW0 - 0.6), ("Bm", S.LN["cloud"]["start"] + 1.5), ("G", S.LN["twist"]["start"]), ("A", S.LN["fact"]["start"] + 1.0),
           ("Dsus", S.LN["end"]["start"]), ("D", S.LN["end"]["start"] + 1.4)]
    out = np.zeros((N, 2))
    for i, (ch, t0) in enumerate(seq):
        t1 = seq[i + 1][1] if i + 1 < len(seq) else S.DUR
        a, b = int(max(0, t0 - 0.8) * SR), min(N, int((t1 + 1.2) * SR))
        tt = np.arange(b - a) / SR
        xf = np.clip(tt / 1.6, 0, 1) * np.clip(((b - a) / SR - tt) / 1.4, 0, 1)
        seg = np.zeros((b - a, 2))
        for j, m in enumerate(CHORDS[ch]):
            f = NOTE(m)
            for c in range(2):
                det = 1 + (0.0025 if c else -0.0025) * (1 + j % 2)
                v = sum(np.sin(2 * np.pi * f * det * k * tt + R.uniform(0, 6.28)) / k ** 1.4 for k in range(1, 6))
                seg[:, c] += v * (0.9 if j < 2 else 0.6) * (1 + 0.15 * np.sin(2 * np.pi * 0.2 * tt + j))
        out[a:b] += seg * xf[:, None]
    out = A.lp(out, 1800, 2) * 0.05
    sw = A.env(N, [(0, 0), (S.T_MW0 - 0.6, 0), (S.T_MW1 + 1.5, 1.0), (S.LN["fact"]["end"], 1.0), (S.T_RET0 + 0.5, 1.1), (S.DUR - 0.2, 0.5), (S.DUR, 0)])
    return out * sw[:, None]


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    hum, traffic = city_bed()
    tr_e = A.env(N, [(0, 1), (S.T_HIT, 1), (S.T_OFF1, 0.5), (S.T_DRAIN0 + 0.6, 0), (S.T_RET0 + 0.6, 0), (S.DUR, 0.7)])
    bed = (power_hum(hum) + traffic * tr_e[:, None] + quake() * 0.9 + buzz_and_pops() + crickets() + wind() + pad() * 1.7
           + A.shimmer(N, S.T_MW0 + 0.2, S.T_MW1 + 3.0, seed=7, gain=0.08)
           + A.riser(N, S.T_STARS - 1.2, S.T_MW0 + 0.3, seed=9) * 0.12
           + A.hit(N, S.T_MW0 + 0.25, gain=0.30, root=36.7))
    bed = A.duck(bed, voice, depth=0.40)
    mix = voice * 1.0 + bed * 0.75
    mix *= np.clip((S.DUR - t) / 0.35, 0, 1)[:, None] * np.clip(t / 0.05, 0, 1)[:, None]
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "milky-way-blackout.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
