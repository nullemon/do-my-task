"""Sound for "What If a Rogue Planet Passed Earth?": the v3 voice chain; a dark orchestral pad (detuned, filtered saw
strings + a low brass fifth) that changes chord with every distance and sinks lower as the planet nears; a city
room tone (distant traffic, rain drips on the wet street); a whoosh + implosion sweep + sub thump + shimmer bloom at every
swap; sonar pings for the blinking star and the speck; low rolling thunder for the lightning flashes; an earthquake
rumble with electrical buzz / crackle as the city lights flicker; a deep Doppler drone for the flyby; a white-out riser
and a low hit back into the normal night. Ducked under the voice, then gain + oversampled limiter (lib/v3_kit.finalize)
to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/rogue-planet.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib import v3_redo_q5 as V3
from lib.v3_kit import finalize

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR
r = np.random.default_rng(62)

CHORDS = {"night": (98.0, (0, 7, 12, 15, 19), 700, 0.7), "hook": (92.5, (0, 7, 12, 15, 22), 800, 0.8),
          "nep": (103.8, (0, 7, 14, 19), 900, 0.7), "mars": (87.3, (0, 7, 12, 15, 18), 750, 0.8),
          "moon": (73.4, (0, 7, 12, 13, 19), 1100, 1.0), "close": (65.4, (0, 6, 12, 13, 18, 24), 1500, 1.2),
          "odds": (98.0, (0, 7, 12, 15, 19), 700, 0.7)}


def saw(f, n, seed):
    q = np.random.default_rng(seed); ph = q.uniform(0, 1)
    vib = 1 + 0.003 * np.sin(2 * np.pi * q.uniform(4.5, 5.5) * np.arange(n) / SR + q.uniform(0, 6))
    return 2 * ((ph + np.cumsum(f * vib) / SR) % 1.0) - 1


def strings(root, iv, cut, seed):
    x = np.zeros((N, 2)); q = np.random.default_rng(seed)
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        for c in range(2):
            for v in range(2):
                x[:, c] += saw(f * (1 + q.uniform(-0.004, 0.004)), N, seed * 31 + k * 7 + c * 3 + v) * (0.5 if k == 0 else 0.32)
    x = A.lp(x, cut, 2)
    brass = sum(saw(root * 2 ** (s / 12) / 2, N, seed + 500 + s) * 0.25 for s in (0, 7))
    return (x + A.lp(brass, cut * 0.5, 2)[:, None] * 0.7) * 0.025


def whoosh(t1, dur=0.6, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = max(int((t1 - dur) * SR), 0), int(t1 * SR); n = b - a
    if n <= 0: return out
    q = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(q.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    out[a:b] += (np.sin(2 * np.pi * np.cumsum(900 * (60 / 900) ** u) / SR) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def ping(t0, f=1760.0, gain=0.3, pan=0.5):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(1.4 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * u) * np.exp(-u / 0.25) * np.minimum(u / 0.004, 1) + 0.35 * np.sin(2 * np.pi * f * 2.01 * u) * np.exp(-u / 0.08)
    out[a:a + n, 0] = s * (1 - pan) * 2; out[a:a + n, 1] = s * pan * 2
    return out * gain


def thunder(t0, gain=0.5, seed=0):
    """distant rolling thunder: low-passed noise bursts with a slow decay (a few seconds), slightly delayed"""
    out = np.zeros((N, 2)); a = int((t0 + 0.25) * SR); n = min(int(3.0 * SR), N - a)
    if n <= 0: return out
    q = np.random.default_rng(seed); u = np.arange(n) / SR
    env = np.minimum(u / 0.08, 1) * np.exp(-u / 0.9) * (1 + 0.6 * np.abs(np.sin(u * q.uniform(5, 9))))
    for c in range(2): out[a:a + n, c] = A.lp(q.standard_normal(n), 180, 2) * env
    return out * gain


def main():
    voice = V3.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "night")] + [(ts, k) for ts, k in S.SWAPS]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, cut, lev = CHORDS[k]
        e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.3, 1), (te - 0.4, 1.1), (te - 0.02, 0.0), (S.DUR + 1, 0)])
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.4, 1.1), (te - 0.02, 0), (S.DUR + 1, 0)])
        if i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.4, 1), (S.DUR - 0.5, 1), (S.DUR, 0)])
        bed += strings(root, iv, cut, 10 + i) * (e * lev)[:, None]
    # city room tone: distant traffic + drips
    traffic = np.stack([A.bp(r.standard_normal(N), 60, 400) for _ in range(2)], 1) * 0.35
    drips = np.zeros((N, 2))
    for tp in np.cumsum(r.exponential(0.35, int(S.DUR / 0.3))):
        if tp >= S.DUR - 0.2: break
        drips += ping(tp, r.uniform(2500, 4200), 0.015, r.uniform(0.2, 0.8))
    bed += traffic * 0.5 + drips
    for i, (ts, k) in enumerate(S.SWAPS):
        if k == "odds": continue
        bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 1.3 if k in ("moon", "close") else 0.9)
        bed += A.shimmer(N, ts + 0.02, min(ts + 1.6, S.DUR - 0.1), seed=50 + i, gain=1.0) * \
            A.env(N, [(0, 0), (ts, 0), (ts + 0.05, 1), (ts + 1.6, 0), (S.DUR, 0)])[:, None] * 0.25
    for j, tp in enumerate(np.arange(S.T_SW["nep"] + 0.4, S.T_SW["moon"] - 0.3, 1 / 1.3)):
        bed += ping(tp, 1568.0 if j % 2 == 0 else 1760.0, 0.14, 0.5 + 0.25 * (-1) ** j)
    bed += ping(S.T_BLINK + 0.05, 880.0, 0.3)
    bed += ping(S.T_END_BLINK + 0.1, 880.0, 0.25)
    # the dark disc: a low sub drone that swells as it nears
    sub = np.sin(2 * np.pi * 36.7 * tt + 0.3 * np.sin(2 * np.pi * 0.2 * tt))
    bed += (sub * 0.20 * A.env(N, [(0, 0), (S.T_SW["moon"], 0), (S.T_SW["moon"] + 0.5, 0.7), (S.T_SW["close"], 1.0), (S.T_PASS1, 0.6),
                                  (S.T_WO0, 0), (S.DUR, 0)]))[:, None]
    # lightning -> thunder (use the same schedule as the picture)
    rr = np.random.default_rng(17); t = S.T_LIT0; k = 0
    while t < S.T_PASS1:
        rate = 1.6 if t < S.T_SW["close"] else 3.2
        t += rr.exponential(1 / rate); rr.uniform(0, 2 * np.pi); rr.uniform(0, 0.85); rr.choice([-0.35, -0.12, 0.18, 0.42]); rr.normal(0, 0.04)
        rr.uniform(0.10, 0.28); I = rr.uniform(0.6, 1.4); rr.integers(1, 4)
        if t < S.T_PASS1: bed += thunder(t, 0.22 * I, seed=200 + k); k += 1
    # earthquake: rumble + electrical buzz / crackle while the lights flicker
    qe = A.env(N, [(0, 0), (S.T_QUAKE0, 0), (S.T_QUAKE0 + 0.5, 1), (S.T_QUAKE1 - 0.8, 1), (S.T_QUAKE1, 0), (S.DUR, 0)])
    rum = np.stack([A.lp(r.standard_normal(N), 90, 2) for _ in range(2)], 1) * (1 + 0.6 * np.sin(2 * np.pi * 3.1 * tt))[:, None]
    buzz = np.sign(np.sin(2 * np.pi * 120 * tt)) * 0.3 * (np.sin(2 * np.pi * 23 * tt) > 0)
    crack = A.bp(r.standard_normal(N), 2000, 8000) * (r.uniform(0, 1, N) > 0.9993) * 6
    bed += (rum * 1.6 + (A.bp(buzz, 100, 3000) * 0.10 + crack * 0.12)[:, None]) * qe[:, None]
    # the flyby: a deep Doppler drone sliding down and panning away
    u = np.clip((tt - S.T_PASS0) / (S.T_PASS1 - S.T_PASS0), 0, 1)
    f = 70 * (1 + 0.35 * np.tanh((0.4 - u) * 5))
    drone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    de = A.env(N, [(0, 0), (S.T_PASS0, 0), (S.T_PASS0 + 0.6, 1), (S.T_PASS1, 0.5), (S.T_WO0, 0), (S.DUR, 0)])
    bed += np.stack([drone * (1 - 0.5 * u), drone * (0.5 + 0.5 * u)], 1) * (0.18 * de)[:, None]
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.1
    bed += A.hit(N, S.T_BACK, gain=0.45, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    finalize(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "rogue-planet.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
