"""
OMINOUS #10 - THE SKY THAT'S COMING : procedural soundtrack (pure Python + numpy).
Writes soundtrack.wav (48 kHz, 16-bit stereo, 52 s) synced to the video timeline in script.py.

  python soundtrack.py
"""
import os
import wave
import numpy as np

SR = 48000
DUR = 52.0
T_CUT = 51.25                     # hard cut to black/silence (matches script.py)
# text beats (t_in) from script.py
BEATS = [0.35, 5.1, 10.0, 15.0, 20.4, 25.4, 31.3, 38.6, 45.3, 48.7]
BIG = {0.35: 1.0, 20.4: 0.9, 25.4: 1.0, 38.6: 0.9, 48.7: 1.2}

N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(10)


def env(t0, t1, a=0.0, b=1.0):
    """smooth 0->1 ramp between t0 and t1, scaled from a to b"""
    x = np.clip((t - t0) / (t1 - t0), 0, 1)
    x = x * x * (3 - 2 * x)
    return a + (b - a) * x


def lowpass_fft(x, fc, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))
    return np.fft.irfft(X, len(x))


def bandpass_fft(x, f0, q=2.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= np.exp(-0.5 * (np.log2(np.maximum(f, 1) / f0) * q) ** 2)
    return np.fft.irfft(X, len(x))


def tone(freq, harmonics=8, bright=0.55, detune=0.0, phase=0.0):
    out = np.zeros(N)
    for h in range(1, harmonics + 1):
        amp = bright ** (h - 1) / h ** 0.5
        out += amp * np.sin(2 * np.pi * freq * h * (1 + detune) * t + phase * h)
    return out


# ---------------------------------------------------------------- drone
# root D (36.7 Hz / 73.4 Hz), fifth A; during the collision a minor 2nd and tritone creep in
intensity = (env(0, 6, 0.35, 0.6) * env(15, 25, 1.0, 1.35) * env(25, 31, 1.0, 1.35)
             * env(38, 44, 1.0, 0.8) * env(45, 51, 1.0, 0.6))
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t) * np.sin(2 * np.pi * 0.031 * t + 1)

L = np.zeros(N)
R = np.zeros(N)
voices = [
    (73.42, 1.0, 0, 52, 0.0),      # D2
    (110.0, 0.55, 0, 52, 0.0),     # A2
    (146.83, 0.30, 4, 52, 0.0),    # D3
    (77.78, 0.38, 24, 38.5, 0.0),  # Eb2 - minor 2nd: tension during the collision
    (103.83, 0.30, 28, 38.5, 0.0), # Ab2 - tritone
    (174.61, 0.22, 38, 47, 0.0),   # F3  - minor third: the dark resolution (Milkomeda)
]
for f, a, t0, t1, _ in voices:
    g = env(t0, t0 + 4) * (1 - env(t1 - 3, t1))
    for side, det, ph in ((0, -0.0025, 0.0), (1, 0.0025, 1.3)):
        v = tone(f, 7, 0.5, det, ph) * a * g
        if side == 0:
            L += v
        else:
            R += v
L *= intensity * lfo
R *= intensity * lfo
L = lowpass_fft(L, 700)
R = lowpass_fft(R, 700)

# --------------------------------------------------------- cosmic wind (filtered noise)
wind_g = 0.10 * env(0, 4) + 0.25 * env(22, 30) - 0.2 * env(40, 48)
for ch, seed in ((0, 1), (1, 2)):
    nz = np.random.default_rng(seed).standard_normal(N)
    w = bandpass_fft(nz, 380, 1.2) * 0.6 + bandpass_fft(nz, 1400, 1.6) * 0.15
    w *= (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * t + seed)) * np.maximum(wind_g, 0)
    if ch == 0:
        L += w * 0.5
    else:
        R += w * 0.5

# ------------------------------------------------------------ sub-bass swells
sub = np.zeros(N)
for t0, length, f in ((0.0, 9.0, 36.7), (19.0, 7.0, 36.7), (24.5, 8.0, 34.6), (37.5, 8.0, 36.7)):
    x = np.clip((t - t0) / length, 0, 1)
    g = np.sin(np.pi * x) ** 2
    sub += np.sin(2 * np.pi * f * t) * g
L += sub * 0.35
R += sub * 0.35

# ---------------------------------------- starburst shimmer (31-38 s): faint high partials
sh = np.zeros(N)
for i, f in enumerate((1174.7, 1318.5, 1760.0, 2349.3, 2637.0)):
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * (0.3 + 0.17 * i) * t + i)
    sh += np.sin(2 * np.pi * f * t + i) * trem / (i + 1.5)
sh *= env(30.5, 34) * (1 - env(37, 42)) * 0.035
L += sh
R += np.roll(sh, 900)

# ------------------------------------------------------------------- hits on beats
def hit(t0, big=0.6):
    x = t - t0
    m = x >= 0
    out = np.zeros(N)
    xx = x[m]
    f = 38 + 50 * np.exp(-xx * 9)                       # pitch drop
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-xx * (1.6 / big))
    nz = rng.standard_normal(m.sum()) * np.exp(-xx * 14) * 0.25
    out[m] = body + nz
    return out


hits = np.zeros(N)
for b in BEATS:
    hits += hit(b, BIG.get(b, 0.55)) * (0.55 if b in BIG else 0.28)
hits = lowpass_fft(hits, 900)
L += hits
R += hits

# ------------------------------------------------------------------- reverb (FFT conv)
def reverb(x, secs=3.2, mix=0.28, seed=5):
    n = int(SR * secs)
    ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-np.arange(n) / SR * 2.2)
    ir = lowpass_fft(np.pad(ir, (0, N - n)), 3000)[:n]
    ir /= np.sqrt(np.sum(ir ** 2))
    m = 1 << int(np.ceil(np.log2(N + n)))
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:N]
    return x * (1 - mix) + y * mix


L = reverb(L, seed=5)
R = reverb(R, seed=6)

# ------------------------------------------------------------- master, fades, hard cut
fade_in = np.clip(t / 1.5, 0, 1)
master = fade_in.copy()
master[t >= T_CUT] = 0.0
# 15 ms de-click at the cut
k = int(0.015 * SR)
ic = int(T_CUT * SR)
master[ic - k:ic] *= np.linspace(1, 0, k)
L *= master
R *= master

peak = max(np.abs(L).max(), np.abs(R).max())
L = np.tanh(L / peak * 1.1) / np.tanh(1.1) * 0.89
R = np.tanh(R / peak * 1.1) / np.tanh(1.1) * 0.89

out = np.stack([L, R], axis=1)
pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", path, f"{DUR}s")
