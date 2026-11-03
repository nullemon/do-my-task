"""
OMINOUS #2 - ROGUE : procedural soundtrack (pure Python + numpy).
Writes soundtrack.wav (48 kHz, 16-bit stereo, 24 s) next to this file.

Beats are synced to script.py BEATS:
  0.0  hook        -> drone already present, ice shimmer
  4.3  "NO SUN."   -> soft sub hit + shimmer
  8.2  "NO DAY."   -> soft sub hit + shimmer
 12.3  "BILLIONS"  -> deeper hit
 17.8  "COMING"    -> deepest hit, sub swell keeps rising (planet looms)
 22.6  black       -> hard cut to silence
"""
import os
import wave
import numpy as np

SR = 48000
DUR = 24.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(2)

HITS = [(4.3, 0.55), (8.2, 0.6), (12.3, 0.8), (17.8, 1.0)]
CUT = 22.6


def smooth(a, b, x):
    y = np.clip((x - a) / (b - a), 0, 1)
    return y * y * (3 - 2 * y)


def fft_filter(x, lo=None, hi=None, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def osc(freq, phase=0.0):
    return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(freq, t.shape)) / SR + phase)


# ---------------------------------------------------------------- drone
def drone():
    L = np.zeros(N)
    R = np.zeros(N)
    # E1 / B1 / E2 with slow beating detune pairs; a minor-second ghost (F) creeps in late
    voices = [(41.2, 0.55), (61.74, 0.32), (82.41, 0.22), (123.47, 0.08), (164.8, 0.04)]
    for i, (f0, a) in enumerate(voices):
        for d, pan in ((-0.12, 0.3), (0.13, 0.7)):
            lfo = 0.75 + 0.25 * np.sin(2 * np.pi * (0.05 + 0.017 * i) * t + i)
            s = osc(f0 + d + 0.04 * np.sin(2 * np.pi * 0.07 * t + i), rng.uniform(0, 6.28)) * a * lfo
            L += s * (1 - pan)
            R += s * pan
    ghost = osc(87.31) * 0.06 * smooth(10, 20, t)   # F2 against E: unease rising
    L += ghost
    R += ghost
    env = smooth(0.0, 0.25, t) * (0.7 + 0.3 * smooth(0, 18, t))
    return L * env, R * env


# ---------------------------------------------------------------- space hiss
def hiss():
    out = []
    for _ in range(2):
        n = rng.standard_normal(N)
        n = fft_filter(n, lo=180, hi=900, order=2)
        n /= np.abs(n).max()
        sweep = 0.5 + 0.5 * np.sin(2 * np.pi * 0.045 * t + rng.uniform(0, 6))
        out.append(n * (0.010 + 0.014 * sweep))
    return out


# ---------------------------------------------------------------- sub swell (planet approach)
def sub():
    a = 0.05 + 0.6 * smooth(6, 22.5, t) ** 2.2
    f = 31.0 + 4.0 * smooth(6, 22.5, t)
    s = osc(f) * a
    s += osc(2 * f) * a * 0.12
    return s


# ---------------------------------------------------------------- hits
def boom(t0, amp):
    s = np.zeros(N)
    i0 = int(t0 * SR)
    n = min(N - i0, int(4.0 * SR))
    tt = np.arange(n) / SR
    f = 34 + 26 * np.exp(-tt * 6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = (1 - np.exp(-tt / 0.012)) * np.exp(-tt / 1.1) * (1 - smooth(tt[-1] * 0.6, tt[-1], tt))
    body = np.sin(ph) * env
    # soft felt transient (lowpassed noise click)
    nz = rng.standard_normal(n) * np.exp(-tt / 0.03)
    nz = fft_filter(np.pad(nz, (0, 0)), hi=400) * 0.25
    s[i0:i0 + n] = (body + nz) * amp
    return s


def shimmer(t0, amp, base=1318.5):
    """Glassy ice partials: inharmonic, slow attack, long decay."""
    L = np.zeros(N)
    R = np.zeros(N)
    i0 = int(t0 * SR)
    n = min(N - i0, int(7.0 * SR))
    tt = np.arange(n) / SR
    ratios = [1.0, 1.498, 2.0, 2.756, 3.01]
    for k, r in enumerate(ratios):
        f = base * r * (1 + rng.uniform(-0.002, 0.002))
        env = (1 - np.exp(-tt / 0.08)) * np.exp(-tt / (2.4 / (1 + 0.4 * k))) * (1 - smooth(tt[-1] * 0.5, tt[-1], tt))
        trem = 1 + 0.15 * np.sin(2 * np.pi * (3 + k) * tt)
        s = np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) * env * trem * amp / (1 + k)
        pan = 0.2 + 0.6 * (k % 2)
        L[i0:i0 + n] += s * (1 - pan)
        R[i0:i0 + n] += s * pan
    return L, R


def reverb(x, seconds=3.8, seed=0):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    tt = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-tt * 6.9 / seconds)
    ir = fft_filter(ir, hi=3500)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    return y


def main():
    L, R = drone()
    hL, hR = hiss()
    L += hL
    R += hR
    s = sub()
    L += s
    R += s
    hitL = np.zeros(N)
    hitR = np.zeros(N)
    shL = np.zeros(N)
    shR = np.zeros(N)
    a, b = shimmer(0.05, 0.05, 1318.5)
    shL += a
    shR += b
    notes = [1174.7, 1318.5, 987.8, 1046.5]
    for (t0, amp), nb in zip(HITS, notes):
        bm = boom(t0, 0.55 * amp)
        hitL += bm
        hitR += bm
        a, b = shimmer(t0 + 0.02, 0.035 * (0.6 + 0.4 * amp), nb)
        shL += a
        shR += b
    # dry hits + wet shimmer/drone
    L = L * 0.5 + hitL + shL * 0.4 + reverb(shL + 0.25 * hitL, 4.5, 1) * 0.9 + reverb(L, 3.0, 3) * 0.15
    R = R * 0.5 + hitR + shR * 0.4 + reverb(shR + 0.25 * hitR, 4.5, 2) * 0.9 + reverb(R, 3.0, 4) * 0.15
    # gentle master lowpass, the cut, normalise, soft clip
    L = fft_filter(L, hi=6000, lo=22)
    R = fft_filter(R, hi=6000, lo=22)
    cut = 1 - smooth(CUT - 0.03, CUT, t)
    L *= cut
    R *= cut
    st = np.stack([L, R], 1)
    st /= np.abs(st).max() / 0.9
    st = np.tanh(st * 1.1) / np.tanh(1.1) * 0.89
    st[t >= CUT] = 0.0
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    print("wrote", out, f"{DUR:.1f}s")


if __name__ == "__main__":
    main()
