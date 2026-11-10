"""Sound for "What If Betelgeuse Exploded Tonight?": voice chain; a dark night pad that brightens into a huge major chord
at the explosion; soft sonar pings for the neutrino ripples, a phone-style notification chime for the alert and a fizz
of neutrino streaks; riser -> white-out boom (sub thump + low hit + noise blast + glassy shimmer tail) at detonation;
a second swell on "Moon"; whooshes on the cuts to day and back to night; birdsong-ish chirps in daylight; a slow
descending pad with soft ticks for each month of fading; a riser and pulse back to tonight's sky; a whoosh as the
light front rolls towards us; the pad ends on the opening chord so the Short loops. Ducked under the voice, two-pass
loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/betelgeuse-tonight.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(round(S.DUR * SR)); tt = np.arange(N) / SR


def chord(root, iv, bright, seed, gain=0.05):
    r = np.random.default_rng(seed); x = np.zeros((N, 2))
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        a = (0.5 if k == 0 else 0.30) * (1 if f < 600 else bright)
        for c in range(2):
            det = 1 + r.uniform(-0.002, 0.002)
            x[:, c] += a * np.sin(2 * np.pi * f * det * tt + r.uniform(0, 6.28)) * (1 + 0.25 * np.sin(2 * np.pi * r.uniform(0.1, 0.3) * tt))
    air = np.stack([A.bp(r.standard_normal(N), 1500, 7000) for _ in range(2)], 1) * 0.05 * bright
    return (x + air) * gain


def blip(t0, f, dur=0.5, gain=0.2, pan=0.5):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(dur * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * u) * np.exp(-u / (dur * 0.3)) * np.clip(u / 0.004, 0, 1)
    out[a:a + n, 0] = s * (1 - pan) * 2 * gain; out[a:a + n, 1] = s * pan * 2 * gain
    return out


def whoosh(t1, dur=0.6, seed=0, gain=1.0, rev=False):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    e = u ** 2.2 if not rev else (1 - u) ** 1.5
    nz = A.bp(r.standard_normal(n), 400, 6000) * e
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    return out * gain


def blast(t0, dur=3.5, seed=7, gain=1.0):
    """detonation: broadband noise burst with a long darkening tail"""
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(dur * SR), N - a)
    r = np.random.default_rng(seed); u = np.arange(n) / SR
    for c in range(2):
        x = r.standard_normal(n)
        lo = A.lp(x, 400, 2) * np.exp(-u / 1.2); hi = A.hp(x, 2500, 2) * np.exp(-u / 0.25)
        out[a:a + n, c] = (lo * 2.0 + A.bp(x, 400, 2500) * np.exp(-u / 0.5) * 0.8 + hi * 0.5) * np.clip(u / 0.003, 0, 1)
    return out * gain


def chirps(t0, t1, seed=9, gain=0.05):
    """birdsong-ish: short rising/falling sine sweeps scattered in daylight"""
    out = np.zeros((N, 2)); r = np.random.default_rng(seed); t = t0
    while t < t1 - 0.3:
        f0 = r.uniform(2600, 4200); k = r.integers(2, 5); pan = r.uniform(0.15, 0.85)
        for j in range(k):
            a = int((t + j * 0.09) * SR); n = int(0.07 * SR)
            u = np.arange(n) / SR; f = f0 * (1 + r.choice([-1, 1]) * 0.35 * u / 0.07)
            s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u / 0.07) ** 2
            out[a:a + n, 0] += s * (1 - pan); out[a:a + n, 1] += s * pan
        t += r.uniform(0.35, 0.9)
    return out * gain


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    bed = np.zeros((N, 2))
    # ---- harmonic bed: night (A minor-ish, dark) -> explosion (bright E major) -> day -> fade (descending) -> night again
    night = chord(110.0, (0, 3, 7, 10, 14), 0.30, 11)
    boom = chord(164.8, (0, 4, 7, 11, 12, 16, 19), 1.0, 12, 0.06)
    day = chord(196.0, (0, 4, 7, 12, 14, 19), 0.8, 13)
    fade = chord(146.8, (0, 3, 7, 10), 0.4, 14) * (1 - 0.5 * np.clip((tt - S.T_NIGHT) / (S.T_FADE1 - S.T_NIGHT), 0, 1))[:, None]
    calm = chord(130.8, (0, 7, 12, 16), 0.35, 15)
    bed += night * A.env(N, [(0, 0.8), (0.4, 1), (S.T_FLARE0, 1), (S.T_IGN, 0.3), (S.T_IGN + 0.2, 0), (S.T_BACK - 0.1, 0), (S.T_BACK + 0.4, 1), (S.DUR, 1)])[:, None]
    bed += boom * A.env(N, [(0, 0), (S.T_IGN, 0), (S.T_IGN + 0.15, 1.2), (S.T_DAY - 0.3, 1), (S.T_DAY, 0), (S.DUR, 0)])[:, None]
    bed += day * A.env(N, [(0, 0), (S.T_DAY, 0), (S.T_DAY + 0.15, 1), (S.T_NIGHT - 0.2, 1), (S.T_NIGHT, 0), (S.DUR, 0)])[:, None]
    bed += fade * A.env(N, [(0, 0), (S.T_NIGHT, 0), (S.T_NIGHT + 0.3, 1), (S.T_SAFE, 0.8), (S.T_SAFE + 0.5, 0), (S.DUR, 0)])[:, None]
    bed += calm * A.env(N, [(0, 0), (S.T_SAFE, 0), (S.T_SAFE + 0.6, 1), (S.T_BACK - 0.2, 0.9), (S.T_BACK, 0), (S.DUR, 0)])[:, None]
    bed += A.drone(N, root=55.0, seed=21, bright=0.2) * 0.6 * A.env(N, [(0, 1), (S.T_IGN, 1), (S.T_IGN + 1, 0.4), (S.DUR - 2, 0.8), (S.DUR, 1)])[:, None]
    # ---- neutrino beat: sonar pings, alert chime, fizz
    for i, tr in enumerate(S.RIPPLES):
        bed += blip(tr, 880.0 * (1.0 if i % 2 == 0 else 1.25), 1.2, 0.10, 0.3 + 0.1 * i)
        bed += blip(tr + 0.18, 1320.0, 0.8, 0.04, 0.7)
    for k, (dt, f) in enumerate(((0.0, 1318.5), (0.13, 1760.0), (0.42, 1318.5), (0.55, 1760.0))):  # notification chime x2
        bed += blip(S.T_ALERT + dt, f, 0.45, 0.16, 0.5) + blip(S.T_ALERT + dt, f * 2, 0.25, 0.04, 0.5)
    r = np.random.default_rng(31)
    fizz = np.stack([A.hp(r.standard_normal(N), 5000) for _ in range(2)], 1) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * tt))[:, None]
    bed += fizz * 0.025 * A.env(N, [(0, 0), (S.T_STREAK0, 0), (S.T_STREAK0 + 0.5, 1), (S.T_STREAK1 - 0.4, 1), (S.T_STREAK1, 0), (S.DUR, 0)])[:, None]
    # ---- detonation
    bed += A.riser(N, S.T_FLARE0 - 0.2, S.T_IGN, seed=41) * 1.3
    bed += blast(S.T_IGN, 4.0, 42, 0.55)
    bed += A.thump(N, S.T_IGN, 1.8)
    bed += A.hit(N, S.T_IGN, gain=0.7, root=41.2)
    bed += A.shimmer(N, S.T_IGN + 0.05, S.T_DAY - 0.2, seed=43, gain=0.18)
    bed += A.thump(N, S.T_MOON - 0.05, 0.8) + whoosh(S.T_MOON, 0.5, 44, 0.4)
    bed += A.shimmer(N, S.T_SHADOW, S.T_SHADOW + 1.2, seed=45, gain=0.12)
    # ---- cuts
    bed += whoosh(S.T_DAY, 0.55, 51, 0.7) + A.thump(N, S.T_DAY, 0.7)
    bed += chirps(S.T_DAY + 0.3, S.T_NIGHT - 0.1, 52, 0.035)
    bed += whoosh(S.T_NIGHT, 0.55, 53, 0.6) + A.thump(N, S.T_NIGHT, 0.6)
    # ---- months of fading: soft ticks as the counter changes; a low swell when the shoulder is gone
    last = None
    for i in range(int(S.T_NIGHT * 30), int((S.T_FADE1 + 0.2) * 30)):
        m = S.month_of(i / 30)
        if m != last:
            bed += blip(i / 30, 1046.5 * 2 ** (-(m - 1) / 24), 0.25, 0.06, 0.5 + 0.2 * (-1) ** m); last = m
    bed += A.hit(N, S.T_GONE - 0.1, gain=0.35, root=49.0)
    # ---- twist: riser into the pulse back, light front whoosh
    bed += A.riser(N, S.T_BACK - 1.2, S.T_BACK, seed=61) * 0.9
    bed += A.thump(N, S.T_BACK, 1.2) + A.shimmer(N, S.T_BACK, S.T_BACK + 1.4, seed=62, gain=0.15)
    bed += whoosh(S.T_FRONT + 1.6, 1.6, 63, 0.5) + whoosh(S.T_FRONT + 2.8, 1.2, 64, 0.35, rev=True)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.25, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "betelgeuse-tonight.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
