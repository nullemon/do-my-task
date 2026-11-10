"""Sound for "When You See the Sun Touch the Horizon, It's Already Gone": voice chain, a warm golden-hour chord pad that
darkens to a dusk chord after the green flash, a soft whoosh + sub thump at every flash/shockwave, a hologram hum and
data blips while the ghost Sun is shown, airy rising tones for the bending rays, a wobbling "mirage" tone during the
Etruscan-vase squash, a bright bell chord + shimmer + boom for the green flash, clock ticks for the extra minutes,
a glitch sweep for the myth-bust, and a riser into the white-out with an impact when the Sun pops back (loop).
Ducked under the voice, two-pass loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/sunset-mirage.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR


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


def whoosh(t1, dur=0.5, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = max(0, int((t1 - dur) * SR)), int(t1 * SR); n = b - a
    if n <= 0: return out
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    return out * gain


def tone(t0, t1, f0, f1, gain, wob=0.0, wf=6.0):
    """sine glide f0 -> f1 with a soft envelope, optional vibrato (mirage wobble)"""
    out = np.zeros((N, 2)); a, b = int(t0 * SR), min(N, int(t1 * SR)); n = b - a
    if n <= 0: return out
    u = np.linspace(0, 1, n); f = f0 * (f1 / f0) ** u * (1 + wob * np.sin(2 * np.pi * wf * u * (t1 - t0)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.sin(np.pi * u) ** 1.5 * gain
    out[a:b] = np.stack([x, x], 1)
    return out


def blips(t0, t1, rate, seed, gain):
    out = np.zeros((N, 2)); r = np.random.default_rng(seed); t = t0
    while t < t1:
        n = int(0.05 * SR); s = int(t * SR)
        if s + n < N:
            k = np.arange(n) / SR; f = r.choice([1760, 2093, 2637, 3136])
            x = np.sin(2 * np.pi * f * k) * np.exp(-k / 0.012) * gain; p = r.uniform(0.2, 0.8)
            out[s:s + n, 0] += x * (1 - p); out[s:s + n, 1] += x * p
        t += r.exponential(1 / rate)
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    gold = chord(220.0, (0, 4, 7, 11, 14), 0.55, 10)          # A maj9: golden hour
    dusk = chord(174.6, (0, 3, 7, 10, 14), 0.40, 11)          # F min9: after sunset
    t_d = S.T_GF + 0.6
    bed = gold * A.env(N, [(0, 1), (t_d - 0.5, 1), (t_d + 0.8, 0), (S.T_POP - 0.01, 0), (S.T_POP + 0.2, 1), (S.DUR, 1)])[:, None]
    bed += dusk * A.env(N, [(0, 0), (t_d - 0.3, 0), (t_d + 0.9, 1), (S.T_POP - 0.1, 1), (S.T_POP, 0), (S.DUR, 0)])[:, None]
    bed += A.drone(N, root=55.0, seed=12, bright=0.25) * 0.8
    for i, (te, col, strength) in enumerate(S.EVENTS):
        bed += whoosh(te, 0.45, seed=40 + i, gain=0.35 * strength)
        bed += A.thump(N, te, 0.5 * strength)
    # ghost reveal: hologram hum + data blips while the true Sun is shown
    hum = np.stack([np.sin(2 * np.pi * 110 * tt) * 0.5 + np.sin(2 * np.pi * 165.5 * tt) * 0.3 + np.sin(2 * np.pi * 220.7 * tt) * 0.2] * 2, 1)
    hum *= (1 + 0.4 * np.sin(2 * np.pi * 7 * tt))[:, None]
    bed += hum * 0.05 * A.env(N, [(0, 0), (S.T_REVEAL, 0), (S.T_REVEAL + 0.3, 1), (S.T_GF + 0.5, 1), (S.T_GF + 1.2, 0),
                                  (S.T_END, 0), (S.T_END + 0.5, 0.7), (S.T_POP, 0.7), (S.T_POP + 0.05, 0), (S.DUR, 0)])[:, None]
    bed += blips(S.T_REVEAL + 0.2, S.T_SQ, 2.5, 21, 0.10) + blips(S.T_END + 0.3, S.T_POP - 0.2, 3.0, 22, 0.08)
    bed += A.shimmer(N, S.T_REVEAL, S.T_REVEAL + 1.8, seed=23, gain=0.35)
    # how: rising airy tones for the bending rays, a gentle sweep as the layers thicken
    for k, (tb, f0) in enumerate(((S.T_BENDS, 330), (S.T_CURVES, 392), (S.T_LIFT, 440))):
        bed += tone(tb - 0.1, tb + 1.6, f0, f0 * 1.5, 0.05) + tone(tb, tb + 1.6, f0 * 2, f0 * 3, 0.02)
    bed += A.shimmer(N, S.T_DENSER - 0.1, S.T_DENSER + 1.4, seed=24, gain=0.25)
    # squash: wobbling mirage tone, then the green flash (bell chord + shimmer + boom)
    bed += tone(S.T_SQW - 0.3, S.T_GF - 0.1, 196, 147, 0.06, wob=0.03, wf=5.5)
    bed += A.riser(N, S.T_LAST - 0.6, S.T_GF + 0.05, seed=25) * 0.7
    tg = S.T_GF + 0.05
    for f, g in ((659.3, 0.12), (987.8, 0.09), (1318.5, 0.07), (1975.5, 0.05), (2637.0, 0.035)):
        bed += tone(tg, tg + 2.6, f, f * 1.002, g)
    bed += A.shimmer(N, tg, tg + 2.2, seed=26, gain=0.55)
    bed += A.hit(N, tg, gain=0.45, root=82.4)
    # bonus: clock ticks for the extra minutes
    bed += A.ticks(N, S.T_MIN - 0.2, S.T_MYTH - 0.2, rate=4.0, gain=0.10)
    # myth: glitchy downward sweep
    bed += tone(S.T_MYTHW - 0.1, S.T_MYTHW + 0.7, 1200, 180, 0.05, wob=0.15, wf=18)
    # end: riser into the white-out, impact as the Sun pops back
    bed += A.riser(N, S.T_POP - 1.6, S.T_POP, seed=27) * 1.0
    bed += A.hit(N, S.T_POP, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.6
    mix *= np.clip((S.DUR - tt) / 0.25, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "sunset-mirage.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
