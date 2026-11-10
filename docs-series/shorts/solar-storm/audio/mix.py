"""Sound for the Short, locked to the picture events in short.py:
dusk city bed (50 Hz mains hum, traffic) -> flare: riser + whoosh + boom (x2) -> 17.6 h ticks -> shock-front whoosh ->
ERUPTION: big hit, then the aurora: shimmering bell grains, crackle/hiss, a pulsing minor pad -> telegraph sparks ->
grid failure: brown-out buzz, transformer arcs + booms, lamp pops, the hum powers down -> near silence (aurora only) ->
digital glitches (phones / GPS) -> low hits on the cost -> the 2012 "miss" whoosh -> lights and hum power back up.
Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py (S2's mix.py was the template).
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/solar-storm.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); t = np.arange(N) / SR
R = np.random.default_rng(1859)


def noise2(n=N): return np.stack([R.standard_normal(n), R.standard_normal(n)], 1)
def at(x, t0, n_out=N):
    out = np.zeros((n_out, 2)); a = int(t0 * SR); n = min(len(x), n_out - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    return out


def city_bed():
    hum = sum(g * np.sin(2 * np.pi * 50 * k * t + k) for k, g in ((1, 0.5), (2, 0.35), (3, 0.18), (5, 0.06)))
    hum = np.stack([hum, hum * 0.95], 1) * 0.05
    traffic = A.lp(noise2(), 380, 2) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t))[:, None] * 0.35
    cars = np.zeros((N, 2))
    for tc, pan in ((1.4, 0.3), (6.0, 0.7), (16.5, 0.4), (36.6, 0.6)):
        n = int(3.0 * SR); u = np.linspace(-1, 1, n); e = np.exp(-(u / 0.35) ** 2)
        x = A.bp(R.standard_normal(n), 200, 1800) * e * 0.18
        cars += at(np.stack([x * (1 - pan), x * pan], 1) * 2, tc - 1.5)
    return hum, traffic + cars


def whoosh(t0, dur=1.6, f0=4000, f1=300, gain=1.0, pan=0.5):
    """filtered-noise swoosh, band sweeping f0 -> f1 (block-wise filtering)"""
    n = int(dur * SR); x = R.standard_normal(n); out = np.zeros(n); blk = 2048
    for i in range(0, n, blk):
        u = i / n; fc = f0 * (f1 / f0) ** u
        out[i:i + blk] = A.bp(x[i:i + blk + 0], max(60, fc * 0.6), min(20000, fc * 1.6))[:len(out[i:i + blk])]
    u = np.linspace(0, 1, n); e = np.sin(np.pi * np.clip(u * 1.1, 0, 1)) ** 2 * np.exp(-u * 1.5)
    y = out * e * gain
    return at(np.stack([y * (1.2 - pan), y * (0.2 + pan)], 1) * 0.9, t0)


def flare_fx():
    out = A.riser(N, S.T_FIRE - 1.3, S.T_FIRE, seed=11) * 0.5 + A.thump(N, S.T_FIRE, 1.0) + A.hit(N, S.T_FIRE + 0.02, gain=0.45, root=41.2)
    out += whoosh(S.T_FIRE, 2.4, 6000, 200, 1.4)
    out += A.riser(N, S.T_FLARE2 - 0.8, S.T_FLARE2, seed=12) * 0.35 + A.thump(N, S.T_FLARE2, 0.6) + whoosh(S.T_FLARE2, 1.8, 5000, 300, 0.9, 0.4)
    out += A.ticks(N, S.T_CNT0, S.T_CNT1, rate=6.0, gain=0.10, accel=2.5)
    out += whoosh(S.T_HIT - 0.15, 1.8, 2500, 120, 1.6, 0.55) + A.thump(N, S.T_HIT + 0.05, 0.5)
    out += A.riser(N, S.T_ERUPT - 1.2, S.T_ERUPT, seed=13) * 0.55 + A.thump(N, S.T_ERUPT, 1.2) + A.hit(N, S.T_ERUPT + 0.02, gain=0.6, root=36.7)
    return out


def aurora_fx():
    """shimmer grains + crackle/hiss (the reported 'aurora sounds'), following the aurora level"""
    e = A.env(N, [(0, 0), (S.T_CNT0, 0), (S.T_HIT, 0.25), (S.T_ERUPT, 1.0), (S.T_FADE0, 1.0), (S.T_FADE1, 0.0), (S.DUR, 0)])
    sh = A.shimmer(N, S.T_HIT, S.T_FADE1, seed=21, gain=0.16)
    crack = (R.uniform(0, 1, N) < 0.0025).astype(float) * R.standard_normal(N)
    crack = A.bp(crack, 1500, 9000) * 1.5 + A.hp(R.standard_normal(N), 5000) * 0.012
    fl = 0.6 + 0.4 * np.sin(2 * np.pi * 0.6 * t) * np.sin(2 * np.pi * 0.23 * t + 1)
    cr = np.stack([crack, np.roll(crack, 311)], 1) * (fl * e)[:, None] * 0.35
    # telegraph sparks on "sparked"
    sp = np.zeros((N, 2))
    ts = S.wt("aurora", "SPARKED")
    for k in range(7):
        n = int(0.25 * SR); tt = np.arange(n) / SR
        z = A.bp(R.standard_normal(n), 1200, 9000) * np.exp(-tt / 0.03) + np.sign(np.sin(2 * np.pi * 120 * tt)) * np.exp(-tt / 0.05) * 0.2
        pan = R.uniform(0.2, 0.8)
        sp += at(np.stack([z * (1 - pan), z * pan], 1) * 0.9, ts + k * 0.09 + R.uniform(0, 0.05))
    return sh * e[:, None] + cr + sp


def grid_fx():
    """brown-out buzz, transformer arcs + booms, lamp pops (pattern from S2)"""
    saw = sum(np.sin(2 * np.pi * 100 * k * t) / k for k in range(1, 12))
    crack = (R.uniform(0, 1, N) < 0.002).astype(float) * R.standard_normal(N)
    flick = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 7.3 * t) + np.sin(2 * np.pi * 3.1 * t))
    e = A.env(N, [(0, 0), (S.T_GRID + 0.6, 0), (S.T_TRANS, 0.7), (S.T_OFF1 - 0.2, 1.0), (S.T_OFF1 + 0.05, 0), (S.DUR, 0)])
    bz = (saw * 0.25 * flick + A.hp(crack, 2500) * 1.2) * e
    out = np.stack([bz, bz], 1) * 0.35
    for i, tl in enumerate(S.LAMP_OFF):
        n = int(0.6 * SR); tt = np.arange(n) / SR
        arc = A.hp(R.standard_normal(n), 2000) * np.exp(-tt / 0.012) * 0.8
        tail = np.sin(2 * np.pi * 100 * tt) * np.exp(-tt / 0.08) * 0.2
        pan = R.uniform(0.25, 0.75)
        out += at(np.stack([(arc + tail) * (1 - pan), (arc + tail) * pan], 1) * 1.6, tl - 0.01)
    for k, tf in enumerate(S.FLASH_T):
        n = int(0.7 * SR); tt = np.arange(n) / SR
        zap = A.bp(R.standard_normal(n), 900, 7000) * (np.exp(-tt / 0.05) + 0.5 * np.exp(-((tt - 0.22) / 0.04) ** 2)) * 1.4
        zap += np.sign(np.sin(2 * np.pi * 100 * tt)) * np.exp(-tt / 0.12) * 0.25
        pan = S.FLASH_X[k]
        out += at(np.stack([zap * (1 - pan), zap * pan], 1) * 1.6, tf - 0.01) + A.thump(N, tf + 0.03, 0.5)
    return out


def power_hum(hum):
    g = A.env(N, [(0, 1), (S.T_OFF0, 1), (S.T_OFF1, 0.5), (S.T_OFF1 + 0.35, 0), (S.T_RET0 + 0.1, 0), (S.T_RET0 + 1.2, 0.8), (S.DUR, 1)])
    down = np.zeros(N); a, b = int((S.T_OFF1 - 0.3) * SR), int((S.T_OFF1 + 0.8) * SR)
    u = np.linspace(0, 1, b - a); f = 50 * (1 - 0.65 * u); ph = 2 * np.pi * np.cumsum(f) / SR
    down[a:b] = (np.sin(ph) + 0.5 * np.sin(2 * ph)) * (1 - u) * 0.07
    up = np.zeros(N); a, b = int((S.T_RET0 + 0.1) * SR), int((S.T_RET0 + 1.3) * SR)
    u = np.linspace(0, 1, b - a); f = 50 * (0.4 + 0.6 * u); ph = 2 * np.pi * np.cumsum(f) / SR
    up[a:b] = (np.sin(ph) + 0.5 * np.sin(2 * ph)) * u * (1 - u) * 0.12
    return hum * g[:, None] + np.stack([down + up, down + up], 1) + A.thump(N, S.T_RET0 + 0.15, 0.25)


def glitches():
    out = np.zeros((N, 2))
    for t0, pan in ((S.T_PH, 0.3), (S.T_GPS, 0.7)):
        for k in range(10):
            n = int(R.uniform(0.02, 0.07) * SR); tt = np.arange(n) / SR
            f = R.choice([880, 1320, 1760, 2640, 440])
            x = np.sign(np.sin(2 * np.pi * f * tt)) * 0.25
            x = np.round(x * 4) / 4 * np.exp(-tt / 0.05)
            out += at(np.stack([x * (1 - pan), x * pan], 1), t0 + k * 0.045 + R.uniform(0, 0.03))
        n = int(0.5 * SR); tt = np.arange(n) / SR                         # falling "disconnect" tone
        f = 1400 * np.exp(-tt / 0.15) + 200; ph = 2 * np.pi * np.cumsum(f) / SR
        x = np.sin(ph) * np.exp(-tt / 0.2) * 0.25
        out += at(np.stack([x * (1 - pan), x * pan], 1), t0 + 0.5)
    return out


def cost_fx():
    out = A.hit(N, S.wt("cost", "TRILLIONS"), gain=0.45, root=32.7) + A.thump(N, S.wt("cost", "TRILLIONS"), 0.6)
    out += A.riser(N, S.T_2012 - 0.6, S.wt("cost", "MISSED"), seed=31) * 0.3
    out += whoosh(S.wt("cost", "MISSED") - 0.1, 2.0, 3000, 150, 1.4, 0.2) + whoosh(S.wt("cost", "MISSED") + 0.4, 1.6, 1500, 120, 0.9, 0.8)
    out += A.hit(N, S.wt("end", "WHEN"), gain=0.35, root=36.7)
    return out


NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)
CHORDS = {"Dm": (38, 50, 57, 62, 65, 69), "Bb": (34, 46, 53, 58, 62, 65), "F": (41, 48, 53, 57, 60, 65), "C": (36, 48, 55, 60, 64, 67),
          "Gm": (43, 50, 55, 58, 62, 67), "A": (45, 52, 57, 61, 64, 69), "Dsus": (38, 50, 57, 62, 67, 69)}


def pad():
    seq = [("Dm", 0.0), ("Bb", S.T_FLARE2 - 0.3), ("Gm", S.T_CNT0), ("A", S.T_HIT - 0.4), ("Dm", S.T_ERUPT), ("Bb", S.LN["aurora"]["start"] + 3.3),
           ("F", S.LN["aurora"]["start"] + 6.0), ("C", S.T_GRID), ("A", S.T_TRANS), ("Dm", S.T_COST), ("Bb", S.T_2012), ("Gm", S.LN["end"]["start"] - 0.4),
           ("Dsus", S.T_RET0), ("Dm", S.DUR - 1.2)]
    out = np.zeros((N, 2))
    for i, (ch, t0) in enumerate(seq):
        t1 = seq[i + 1][1] if i + 1 < len(seq) else S.DUR
        a, b = int(max(0, t0 - 0.5) * SR), min(N, int((t1 + 0.9) * SR))
        tt = np.arange(b - a) / SR
        xf = np.clip(tt / 0.9, 0, 1) * np.clip(((b - a) / SR - tt) / 0.9, 0, 1)
        seg = np.zeros((b - a, 2))
        for j, m in enumerate(CHORDS[ch]):
            f = NOTE(m)
            for c in range(2):
                det = 1 + (0.003 if c else -0.003) * (1 + j % 2)
                v = sum(np.sin(2 * np.pi * f * det * k * tt + R.uniform(0, 6.28)) / k ** 1.3 for k in range(1, 6))
                seg[:, c] += v * (0.9 if j < 2 else 0.6)
        out[a:b] += seg * xf[:, None]
    out = A.lp(out, 2200, 2) * 0.045
    # driving pulse (8ths at 100 bpm) during the storm, a gap of near silence after the blackout
    pulse = (0.55 + 0.45 * np.cos(2 * np.pi * t * (100 / 60) * 2) ** 8)
    drive = A.env(N, [(0, 0), (S.T_ERUPT, 0), (S.T_ERUPT + 0.4, 1), (S.T_OFF1, 1), (S.T_OFF1 + 0.3, 0), (S.T_COST, 0), (S.T_COST + 0.5, 0.6), (S.LN["end"]["start"], 0), (S.DUR, 0)])
    sw = A.env(N, [(0, 0.35), (S.T_FIRE, 0.6), (S.T_ERUPT, 1.0), (S.T_OFF1, 1.0), (S.T_OFF1 + 0.4, 0.15), (S.T_PH + 0.8, 0.15),
                   (S.T_COST + 0.4, 0.9), (S.LN["end"]["start"], 1.0), (S.DUR - 0.3, 0.6), (S.DUR, 0)])
    return out * (sw * (1 - 0.6 * drive + 0.6 * drive * pulse))[:, None]


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    hum, traffic = city_bed()
    tr_e = A.env(N, [(0, 1), (S.T_ERUPT, 0.8), (S.T_OFF1, 0.5), (S.T_OFF1 + 0.4, 0), (S.T_RET0 + 0.4, 0), (S.DUR, 0.8)])
    bed = (power_hum(hum) + traffic * tr_e[:, None] + flare_fx() * 0.8 + aurora_fx() + grid_fx() + glitches() * 0.8 + cost_fx() * 0.8
           + pad() * 1.8 + A.drone(N, root=36.7, seed=4, bright=0.2) * A.env(N, [(0, 0), (S.T_HIT, 0), (S.T_ERUPT, 0.5), (S.T_FADE1, 0.3), (S.DUR, 0)])[:, None])
    bed = A.duck(bed, voice, depth=0.40)
    mix = voice * 1.0 + bed * 0.75
    mix *= np.clip((S.DUR - t) / 0.30, 0, 1)[:, None] * np.clip(t / 0.05, 0, 1)[:, None]
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "solar-storm.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
