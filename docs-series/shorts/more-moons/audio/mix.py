"""Sound for "What If Earth Had More Moons?": the v3 voice chain; an orchestral pad (detuned, filtered saw strings + a
soft brass fifth) that changes chord with every moon set; a whoosh + implosion sweep + sub thump + shimmer bloom at every
swap; a Doppler whoosh for the racing Phobos-like moon and sonar pings for its pointer; a dark swell under the
eclipses; an icy shimmer for the Saturn swarm; rising bell pops as all the moons arrive; a rolling water / tide rumble
when the tides turn chaotic; a white-out riser and low hit; a soft chime when the lost companion merges into the Moon.
Ducked under the voice, then gain + oversampled limiter (lib/v3_kit.finalize) to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/more-moons.srt"""
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

CHORDS = {"moon": (110.0, (0, 7, 12, 16, 19), 900, 0.8), "two": (123.5, (0, 7, 12, 16, 19, 23), 1300, 0.85),
          "mars": (103.8, (0, 7, 14, 19), 650, 0.6), "jup": (98.0, (0, 7, 12, 15, 19, 22), 1700, 1.0),
          "sat": (130.8, (0, 7, 12, 14, 19, 26), 2400, 0.95), "all": (110.0, (0, 7, 12, 16, 19, 24, 28), 3400, 1.25),
          "end": (110.0, (0, 7, 12, 16, 19), 900, 0.8)}


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
    for s in (0, 7, 12): brass += saw(root * 2 ** (s / 12), N, seed + 500 + s) * 0.25
    return (x + A.lp(brass, cut * 0.6, 2)[:, None] * 0.6) * 0.025


def whoosh(t1, dur=0.6, seed=0, gain=1.0, pan_lr=True):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); a = max(a, 0); n = b - a
    if n <= 0: return out
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * ((1 - 0.6 * u) if pan_lr else 1); out[a:b, 1] = nz * ((0.4 + 0.6 * u) if pan_lr else 1)
    f = 900 * (60 / 900) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bloom_swell(t0, seed, gain=0.4):
    sh = A.shimmer(N, t0, min(t0 + 1.6, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + 1.6, 0), (S.DUR, 0)])[:, None] * gain


def ping(t0, f=1760.0, gain=0.3, pan=0.5):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(1.4 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * u) * np.exp(-u / 0.25) * np.minimum(u / 0.004, 1) + 0.35 * np.sin(2 * np.pi * f * 2.01 * u) * np.exp(-u / 0.08)
    out[a:a + n, 0] = s * (1 - pan) * 2; out[a:a + n, 1] = s * pan * 2
    return out * gain


def pluck(t0, f, gain=0.3):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(1.2 * SR), N - a)
    if n <= 0: return out
    u = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * m * u) * np.exp(-u / (0.35 / m)) * w for m, w in ((1, 1.0), (2.0, 0.5), (3.01, 0.25), (4.2, 0.15)))
    out[a:a + n] = (s * np.minimum(u / 0.003, 1))[:, None] * gain
    return out


def doppler_pass(t0, t1, gain=0.3):
    """the Phobos-like moon's pass: a filtered noise 'jet' panned left -> right with a pitch drop at mid-pass"""
    out = np.zeros((N, 2)); a, b = int(t0 * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(91); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 300, 2500)
    e = np.exp(-((u - 0.5) / 0.28) ** 2)
    f = 420 * (1 + 0.25 * np.tanh((0.5 - u) * 6)); tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    s = (nz * 0.7 + tone) * e
    out[a:b, 0] = s * (1 - u); out[a:b, 1] = s * u
    return out * gain


def main():
    voice = V3.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "moon")] + [(ts, k) for ts, k in S.SWAPS]
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
        bed += A.thump(N, ts, 1.2 if k in ("jup", "all") else 0.9)
        bed += bloom_swell(ts + 0.02, 50 + i, 0.35)
    bed += A.shimmer(N, 0.3, S.T_SW["two"] - 0.3, seed=61, gain=0.08)
    # Mars-style: the pass + pointer pings
    bed += doppler_pass(S.T_PHO0, S.T_PHO1, 0.35)
    for j, tp in enumerate(np.arange(S.T_SW["mars"] + 0.5, S.T_SW["jup"] - 0.3, 1 / 1.3)):
        bed += ping(tp, 1760.0 if j % 2 == 0 else 2093.0, 0.16, 0.5 + 0.25 * (-1) ** j)
    # Jupiter-style: a dark swell under the eclipse
    te = S.wt("jup_b", "ECLIPSING")
    r = np.random.default_rng(62)
    dark = np.stack([A.lp(r.standard_normal(N), 110, 2) for _ in range(2)], 1)
    bed += dark * 1.2 * A.env(N, [(0, 0), (te - 1.2, 0), (te, 1), (te + 1.8, 0.6), (S.T_SW["sat"] - 0.2, 0), (S.DUR, 0)])[:, None]
    bed += A.riser(N, S.T_SW["jup"] - 0.9, S.T_SW["jup"], seed=66) * 0.4
    # Saturn swarm: icy shimmer + sparkle ticks
    bed += A.shimmer(N, S.T_SW["sat"] + 0.2, S.T_SW["all"] - 0.3, seed=71, gain=0.20)
    # finale pops
    for j, k in enumerate(S.POP_ORDER):
        bed += pluck(S.T_POP[k], 523.25 * 2 ** ((0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36, 38)[j] / 12), 0.07)
        if j % 3 == 0: bed += A.thump(N, S.T_POP[k], 0.35)
    # chaotic tides: rolling water rumble + sloshing swell
    wv = np.stack([A.bp(r.standard_normal(N), 80, 600) for _ in range(2)], 1) * (1 + 0.8 * np.sin(2 * np.pi * 0.48 * tt))[:, None]
    slosh = np.stack([A.bp(r.standard_normal(N), 1200, 6000) for _ in range(2)], 1) * np.clip(np.sin(2 * np.pi * 0.48 * tt + 0.6), 0, 1)[:, None] ** 3
    ce = A.env(N, [(0, 0), (S.T_CHAOS0, 0), (S.T_CHAOS1, 1), (S.T_WO0, 1), (S.T_BACK, 0), (S.DUR, 0)])[:, None]
    bed += (wv * 1.0 + slosh * 0.12) * ce
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.1
    bed += A.hit(N, S.T_BACK, gain=0.45, root=55.0)
    # the merge: a soft low chime
    bed += pluck(S.T_MERGE1 - 0.12, 220.0, 0.12) + pluck(S.T_MERGE1 - 0.12, 329.6, 0.08) + A.thump(N, S.T_MERGE1 - 0.12, 0.5)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    finalize(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "more-moons.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
