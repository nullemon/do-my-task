"""Sound for "The Dinosaur-Killer Asteroid, Seen From the Ground", locked to the picture events in short.py:
park ambience (birds, light breeze) + bright pad -> the new star: a thin rising whine -> atmospheric entry: plasma roar
panning toward the impact, whine climbing -> FLASH: everything cuts to near silence (light arrives first) with only a
high ringing shimmer -> the seismic waves arrive: a massive delayed boom + long ground rumble (x2) -> ejecta re-entry:
meteor-shower crackle, sizzles and whooshes for the big ones, then fire crackle -> the dust wall: a rising roar ->
the AIR BLAST (sound travels slowest): the biggest boom + wind roar with gusts -> impact winter: near silence, cold wind,
a low drone -> golden riser -> warm hit, major pad and the birds again (loops).
Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/asteroid-ground.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); t = np.arange(N) / SR
R = np.random.default_rng(66)


def noise2(n=N): return np.stack([R.standard_normal(n), R.standard_normal(n)], 1)
def at(x, t0):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(len(x), N - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    return out
def E(pts): return A.env(N, pts)[:, None]


def birds():
    out = np.zeros((N, 2))
    for t0 in list(R.uniform(0.2, S.T_ENTRY - 0.5, 9)) + list(R.uniform(S.T_BACK + 0.4, S.DUR - 0.6, 7)):
        for k in range(R.integers(2, 5)):
            n = int(R.uniform(0.05, 0.12) * SR); tt = np.arange(n) / SR
            f0 = R.uniform(2800, 4800); f = f0 * (1 + 0.25 * np.sin(2 * np.pi * R.uniform(15, 40) * tt)) * (1 + R.uniform(-0.3, 0.3) * tt / tt[-1])
            x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / tt[-1]) ** 2 * 0.05
            pan = R.uniform(0.15, 0.85)
            out += at(np.stack([x * (1 - pan), x * pan], 1), t0 + k * R.uniform(0.09, 0.16))
    breeze = A.bp(noise2(), 300, 2500) * 0.015 * (0.7 + 0.3 * np.sin(2 * np.pi * 0.13 * t))[:, None]
    return out + breeze * E([(0, 1), (S.T_ENTRY, 1), (S.T_IMP, 0), (S.T_BACK, 0), (S.T_BACK + 0.5, 1), (S.DUR, 1)])


def approach():
    """thin whine from the new star rising into the plasma roar of entry; cut dead at the flash"""
    a, b = int(S.T_STAR * SR), int(S.T_IMP * SR); n = b - a; u = np.linspace(0, 1, n)
    f = 420 * (2600 / 420) ** (u ** 2.2); ph = 2 * np.pi * np.cumsum(f) / SR
    whine = (np.sin(ph) + 0.25 * np.sin(2.01 * ph)) * (0.02 + 0.20 * u ** 2.5)
    x = np.zeros(N); x[a:b] = whine
    out = np.stack([x * 0.9, x], 1)
    roar = A.lp(noise2(), 900, 2) * 1.2 + A.bp(noise2(), 1500, 6000) * 0.25
    pan = np.clip((t - S.T_ENTRY) / (S.T_IMP - S.T_ENTRY), 0, 1)               # sweeps right -> centre
    roar[:, 0] *= 0.4 + 0.5 * pan; roar[:, 1] *= 1.0 - 0.3 * pan
    out += roar * E([(0, 0), (S.T_ENTRY - 0.3, 0), (S.T_ENTRY + 1.0, 0.25), (S.T_IMP - 0.05, 0.9), (S.T_IMP, 0), (S.DUR, 0)])
    out += A.riser(N, S.T_IMP - 1.4, S.T_IMP, seed=2) * 0.6
    # the flash: a high ringing shimmer in near silence
    out += A.shimmer(N, S.T_IMP, S.T_IMP + 3.2, seed=7, gain=0.6) * E([(0, 0), (S.T_IMP, 1), (S.T_IMP + 3.4, 0), (S.DUR, 0)])
    n = int(1.2 * SR); tt = np.arange(n) / SR; ring = np.sin(2 * np.pi * 3100 * tt) * np.exp(-tt / 0.5) * 0.05
    out += at(np.stack([ring, ring], 1), S.T_IMP)
    # the fireball climbing: a distant low swell (felt more than heard)
    out += A.lp(noise2(), 120, 2) * 1.0 * E([(0, 0), (S.T_IMP + 0.8, 0), (S.T_IMP + 3, 0.5), (S.T_JOLT - 0.1, 0.8), (S.T_JOLT, 0), (S.DUR, 0)])
    return out


def quake():
    out = A.thump(N, S.T_JOLT, 1.8) + A.hit(N, S.T_JOLT + 0.01, gain=0.9, root=32.7) + A.thump(N, S.T_JOLT2, 1.0)
    rum = A.lp(noise2(), 90, 3) * 3.0 * (1 + 0.5 * np.sin(2 * np.pi * 6.5 * t) * np.sin(2 * np.pi * 1.3 * t))[:, None]
    out += rum * E([(0, 0), (S.T_JOLT - 0.05, 0), (S.T_JOLT + 0.1, 1.0), (S.T_JOLT2 + 0.6, 0.8), (S.T_EJ0 + 0.8, 0.15), (S.T_EJ0 + 2, 0), (S.DUR, 0)])
    # debris rattle
    cr = (R.uniform(0, 1, N) < 0.004).astype(float) * R.standard_normal(N)
    cr = A.bp(cr, 400, 4000) * 0.8
    out += np.stack([cr, np.roll(cr, 517)], 1) * E([(0, 0), (S.T_JOLT, 0), (S.T_JOLT + 0.1, 1), (S.T_JOLT + 2.2, 0), (S.DUR, 0)])
    return out


def ejecta():
    """meteor-shower crackle + sizzle, whooshes for the big ones, then fire crackle"""
    e = E([(0, 0), (S.T_EJ0, 0), (S.T_EJ0 + 1.0, 0.6), (S.T_RED, 1.0), (S.T_HITS - 0.2, 1.0), (S.T_HITS + 0.4, 0), (S.DUR, 0)])
    cr = (R.uniform(0, 1, N) < 0.010).astype(float) * R.standard_normal(N)
    cr = A.bp(cr, 1200, 9000) * 1.2 + A.hp(R.standard_normal(N), 4500) * 0.02
    out = np.stack([cr, np.roll(cr, 311)], 1) * e * 0.5
    out += A.bp(noise2(), 2500, 9000) * 0.03 * e * (1 + 0.4 * np.sin(2 * np.pi * 9 * t))[:, None]
    m = S.Scene.__dict__  # noqa: F841
    sc_met = MET
    W = 1080.0
    for i in np.nonzero(sc_met["big"])[0]:
        t0 = sc_met["ts"][i]
        if t0 > S.T_HITS: continue
        dur = sc_met["life"][i] + 0.3; n = int(dur * SR); tt = np.arange(n) / SR; u = tt / dur
        f = 3000 * (300 / 3000) ** u
        x = A.bp(R.standard_normal(n), 300, 4000) * np.sin(np.pi * u) ** 2 * 0.25 + np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) ** 3 * 0.04
        pan = float(np.clip(sc_met["x0"][i] / W, 0.05, 0.95))
        out += at(np.stack([x * (1 - pan), x * pan], 1), t0)
    fire = (R.uniform(0, 1, N) < 0.006).astype(float) * R.standard_normal(N)
    fire = A.bp(fire, 600, 6000) * 1.4 + A.lp(R.standard_normal(N), 300) * 0.25
    out += np.stack([fire, np.roll(fire, 911)], 1) * E([(0, 0), (S.T_FIRE - 0.3, 0), (S.T_FIRE + 1.0, 0.8), (S.T_HITS, 0.8), (S.T_HITS + 0.8, 0), (S.DUR, 0)])
    return out


def blast():
    roar = A.lp(noise2(), 400, 2) * 1.6
    out = roar * E([(0, 0), (S.T_BL0, 0), (S.T_HITS - 0.05, 1.0), (S.T_HITS, 0.3), (S.DUR, 0)])
    out += A.riser(N, S.T_HITS - 1.4, S.T_HITS, seed=11) * 0.6
    out += A.thump(N, S.T_HITS, 2.2) + A.hit(N, S.T_HITS + 0.01, gain=1.1, root=27.5)
    gust = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * t) * np.sin(2 * np.pi * 0.11 * t + 1)
    wind = (A.bp(noise2(), 150, 1600) * 1.4 + A.bp(noise2(), 1500, 5000) * 0.25) * gust[:, None]
    out += wind * E([(0, 0), (S.T_HITS - 0.05, 0), (S.T_HITS + 0.15, 1.3), (S.T_SOOT + 0.5, 0.5), (S.T_SOOT + 2.0, 0.12), (S.T_WO0, 0.10),
                     (S.T_BACK, 0), (S.DUR, 0)])
    return out


NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)
CHORDS = {"D": (38, 50, 57, 62, 66, 69), "Bm": (35, 47, 54, 59, 62, 66), "G": (43, 50, 55, 59, 62, 67), "Dm": (38, 50, 57, 62, 65, 69),
          "Bb": (34, 46, 53, 58, 62, 65), "Gm": (43, 50, 55, 58, 62, 67), "A": (45, 52, 57, 61, 64, 69), "Cm": (36, 48, 55, 60, 63, 67),
          "Dsus": (38, 50, 57, 62, 67, 69)}


def pad():
    seq = [("D", 0.0), ("Bm", S.LN["appr"]["start"] - 0.3), ("Gm", S.T_ENTRY), ("Dm", S.T_IMP + 1.5), ("Bb", S.T_JOLT), ("Gm", S.T_EJ0),
           ("A", S.T_FIRE), ("Dm", S.T_HITS), ("Cm", S.T_SOOT + 1.5), ("Dsus", S.T_BACK), ("D", S.T_BACK + 2.2)]
    out = np.zeros((N, 2))
    for i, (ch, t0) in enumerate(seq):
        t1 = seq[i + 1][1] if i + 1 < len(seq) else S.DUR
        a, b = int(max(0, t0 - 0.4) * SR), min(N, int((t1 + 0.8) * SR))
        tt = np.arange(b - a) / SR
        xf = np.clip(tt / 0.8, 0, 1) * np.clip(((b - a) / SR - tt) / 0.8, 0, 1)
        seg = np.zeros((b - a, 2))
        for j, m in enumerate(CHORDS[ch]):
            f = NOTE(m)
            for c in range(2):
                det = 1 + (0.003 if c else -0.003) * (1 + j % 2)
                v = sum(np.sin(2 * np.pi * f * det * k * tt + R.uniform(0, 6.28)) / k ** 1.3 for k in range(1, 6))
                seg[:, c] += v * (0.9 if j < 2 else 0.6)
        out[a:b] += seg * xf[:, None]
    out = A.lp(out, 2400, 2) * 0.045
    pulse = (0.55 + 0.45 * np.cos(2 * np.pi * t * (96 / 60) * 2) ** 8)
    drive = A.env(N, [(0, 0), (S.T_ENTRY, 0), (S.T_ENTRY + 0.5, 1), (S.T_IMP, 1), (S.T_IMP + 0.01, 0), (S.T_EJ0, 0), (S.T_EJ0 + 0.6, 1),
                      (S.T_HITS, 1), (S.T_HITS + 0.2, 0), (S.DUR, 0)])
    sw = A.env(N, [(0, 0.6), (S.T_ENTRY, 0.8), (S.T_IMP - 0.02, 1.0), (S.T_IMP, 0.0), (S.T_IMP + 1.6, 0.0), (S.T_JOLT, 0.7), (S.T_EJ0, 0.9),
                   (S.T_HITS, 1.0), (S.T_HITS + 0.3, 0.3), (S.T_SOOT + 1.5, 0.45), (S.T_WO0, 0.5), (S.T_BACK, 1.0), (S.DUR - 0.3, 0.8), (S.DUR, 0)])
    return out * (sw * (1 - 0.5 * drive + 0.5 * drive * pulse))[:, None]


def ending():
    out = A.riser(N, S.T_WO0 - 0.4, S.T_BACK, seed=21) * 1.0 + A.hit(N, S.T_BACK, gain=0.5, root=73.4)
    out += A.shimmer(N, S.T_BACK, S.DUR - 0.2, seed=22, gain=0.25)
    return out


MET = None


def main():
    global MET
    MET = S.Scene(True).met
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    drone = A.drone(N, root=36.7, seed=4, bright=0.15) * E([(0, 0), (S.T_IMP + 1, 0), (S.T_JOLT, 0.6), (S.T_HITS, 0.8), (S.T_SOOT + 1, 1.0),
                                                              (S.T_WO0, 1.0), (S.T_BACK, 0), (S.DUR, 0)])
    bed = birds() + approach() + quake() * 0.9 + ejecta() + blast() * 0.9 + pad() * 1.8 + drone + ending() * 0.8
    bed = A.duck(bed, voice, depth=0.40)
    mix = voice * 1.0 + bed * 0.75
    mix *= np.clip((S.DUR - t) / 0.30, 0, 1)[:, None] * np.clip(t / 0.05, 0, 1)[:, None]
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "asteroid-ground.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
