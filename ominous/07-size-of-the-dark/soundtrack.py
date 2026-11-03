"""
OMINOUS #7 - SIZE OF THE DARK : procedural soundtrack (pure Python + numpy)
Writes soundtrack.wav (48 kHz, 16-bit stereo) synced to script.py's timeline:
  - a low drone that thickens and rises with every new planet
  - a rising swell into each reveal and a sub-bass hit when the planet lands
  - near-silence for the pan through the void between the stars
  - soft high tones on the hook and on "WE ARE HERE.", then silence.
Run:  python soundtrack.py
"""
import os
import wave
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "soundtrack.wav")
rng = np.random.default_rng(7)

# ---- timeline (must mirror TIMING in script.py) ----
TIMING = [("mercury", 0.0, 3.2), ("mars", 1.2, 1.5), ("venus", 1.2, 1.5), ("earth", 1.2, 1.7),
          ("neptune", 1.5, 1.7), ("uranus", 1.2, 1.5), ("saturn", 1.7, 2.1), ("jupiter", 1.7, 1.9),
          ("tres4", 3.0, 1.8), ("kelt9", 1.6, 2.2), ("hatp67", 1.8, 2.5)]
FINAL_TRANS, FINAL_HOLD, FADE_OUT, TAIL = 2.4, 3.2, 1.2, 0.3
SEG = []
t = 0.0
for k, tr, hold in TIMING:
    SEG.append(dict(key=k, t0=t, ta=t + tr, tl=t + tr + hold))
    t += tr + hold
T_FINAL0 = t
T_FINAL_ARR = t + FINAL_TRANS
T_FADE0 = T_FINAL_ARR + FINAL_HOLD
T_END = T_FADE0 + FADE_OUT + TAIL
N = int(T_END * SR)
tt = np.arange(N) / SR
VOID = [s for s in SEG if s["key"] == "tres4"][0]


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def env_ramp(t0, t1):
    return smooth((tt - t0) / max(1e-6, t1 - t0))


def fft_filter(x, lo=None, hi=None, slope=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi:
        g *= 1 / (1 + (f / hi) ** (2 * slope))
    if lo:
        g *= 1 / (1 + (lo / np.maximum(f, 1e-3)) ** (2 * slope))
    return np.fft.irfft(X * g, len(x))


def osc(freq, phase=0.0, detune_lfo=0.0, lfo_rate=0.05):
    """sine with slow pitch wander; freq may be an array."""
    f = freq * (1 + detune_lfo * np.sin(2 * np.pi * lfo_rate * tt + phase))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


# ---- stage: 0 .. 10 , smooth rise through the reveals ----
stage = np.zeros(N)
for i, s in enumerate(SEG):
    stage += env_ramp(s["t0"], s["ta"] + 0.5) * (1.0 if i > 0 else 0.0)
growth = stage / 10.0                                 # 0 -> 1

void_dip = 1 - 0.85 * (env_ramp(VOID["t0"] - 0.2, VOID["t0"] + 0.8) * (1 - env_ramp(VOID["ta"] - 0.9, VOID["ta"] - 0.05)))
master = env_ramp(0.0, 2.0) * (1 - env_ramp(T_FADE0, T_FADE0 + FADE_OUT))
master[tt > T_END - TAIL] = 0.0

L = np.zeros(N)
R = np.zeros(N)

# ---- drone: A minor-ish, grows from a thin hum into a dissonant wall ----
root = 55.0 * (1 + 0.035 * growth)                    # creeps upward as planets grow
partials = [(1.0, 1.0, 0.0), (2.0, 0.45, 0.0), (3.0, 0.22, 0.25), (1.5, 0.30, 0.35),
            (4.0, 0.10, 0.5), (0.5, 0.55, 0.6), (1.0595, 0.18, 0.75), (2.119, 0.10, 0.85)]
for j, (mul, amp, appear) in enumerate(partials):
    gate = smooth((growth - appear) / 0.2) if appear > 0 else np.ones(N)
    for side, ph in ((0, 0.0), (1, 1.3)):
        sig = osc(root * mul * (1 + (0.0015 if side else -0.0015)), phase=ph + j, detune_lfo=0.002, lfo_rate=0.03 + 0.01 * j)
        a = amp * gate * (0.35 + 0.65 * growth)
        if side == 0:
            L += sig * a
        else:
            R += sig * a
# slow beating tremolo
trem = 0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * tt)
L *= trem * void_dip
R *= trem * void_dip

# filtered noise "air" bed (dark), opens up with growth
air = fft_filter(rng.standard_normal(N), lo=60, hi=420)
air2 = fft_filter(rng.standard_normal(N), lo=60, hi=420)
air_g = 0.35 * (0.3 + growth) * void_dip
L += air * air_g / np.std(air) * 0.25
R += air2 * air_g / np.std(air2) * 0.25

# ---- void shimmer: thin high tones in the dark between stars ----
vg = env_ramp(VOID["t0"], VOID["t0"] + 1.0) * (1 - env_ramp(VOID["ta"] - 0.6, VOID["ta"]))
for f, a in ((1318.5, 0.020), (1975.5, 0.012), (1396.9, 0.010)):
    L += osc(f, 0.3, 0.003, 0.2) * a * vg
    R += osc(f * 1.002, 1.1, 0.003, 0.17) * a * vg

# ---- swells into each reveal (reverse-swell filtered noise + rising sine) ----
for i, s in enumerate(SEG[1:], start=1):
    t0, ta = s["t0"], s["ta"]
    seg = (tt >= t0 - 0.2) & (tt < ta + 0.2)
    idx = np.where(seg)[0]
    if len(idx) == 0:
        continue
    x = (tt[idx] - t0) / (ta - t0)
    e = np.clip(x, 0, 1) ** 2.2 * (tt[idx] < ta)
    n = rng.standard_normal(len(idx))
    n = fft_filter(n, lo=80, hi=500 + 1200 * i / 10)
    n /= np.std(n) + 1e-9
    k = 0.05 + 0.06 * i / 10
    L[idx] += n * e * k
    R[idx] += np.roll(n, 113) * e * k

# ---- sub-bass hits as each planet lands ----
def hit(t_at, strength, f0=48.0, f1=27.0, decay=2.4):
    i0 = int(t_at * SR)
    n = min(N - i0, int(decay * 3 * SR))
    if n <= 0:
        return
    tl = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tl / 0.18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR)
    env = (1 - np.exp(-tl / 0.006)) * np.exp(-tl / decay)
    thud = fft_filter(rng.standard_normal(n), hi=140) * np.exp(-tl / 0.09)
    thud /= np.max(np.abs(thud)) + 1e-9
    sig = (body * env + 0.25 * thud) * strength
    L[i0:i0 + n] += sig
    R[i0:i0 + n] += sig

for i, s in enumerate(SEG):
    if i == 0:
        hit(0.35, 0.35, 44, 30, 2.0)
        continue
    strength = 0.38 + 0.42 * (i / 10)
    if s["key"] == "hatp67":
        strength = 1.0
    hit(s["ta"] - 0.12, strength, 50 if i < 8 else 56, 26 if i < 8 else 23, 2.0 + 1.2 * i / 10)

# ---- soft tones on text beats ----
def tone(t_at, f, amp, decay=2.5):
    i0 = int(t_at * SR)
    n = min(N - i0, int(decay * 4 * SR))
    tl = np.arange(n) / SR
    env = (1 - np.exp(-tl / 0.03)) * np.exp(-tl / decay)
    sig = (np.sin(2 * np.pi * f * tl) + 0.3 * np.sin(2 * np.pi * f * 2.0 * tl + 0.5) * np.exp(-tl / 0.6)) * env * amp
    L[i0:i0 + n] += sig
    R[i0:i0 + n] += np.roll(sig, 240)

tone(0.6, 440.0, 0.035)
tone(1.0, 659.3, 0.025)
tone(VOID["t0"] + 0.3, 523.3, 0.03, 3.0)
tone(T_FINAL_ARR + 0.5, 880.0, 0.04, 2.8)
tone(T_FINAL_ARR + 0.5, 1318.5, 0.015, 2.8)

# final: drone gets pulled away -> nearly silent under "WE ARE HERE."
final_dip = 1 - 0.65 * env_ramp(T_FINAL_ARR - 0.5, T_FINAL_ARR + 1.5)
L *= final_dip
R *= final_dip

# ---- simple reverb (FFT convolution with a dark decaying tail) ----
def reverb(x, seconds=3.2, mix=0.28, seed=1):
    r = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR / (seconds / 5))
    ir = fft_filter(ir, hi=2500)
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    return x * (1 - mix) + y * mix * 1.4

L = reverb(L, seed=1)
R = reverb(R, seed=2)
# gentle overall lowpass to keep it soft
L = fft_filter(L, hi=5000, slope=1)
R = fft_filter(R, hi=5000, slope=1)
L *= master
R *= master
# soft clip + normalise
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
L = np.tanh(1.2 * L / peak) / np.tanh(1.2) * 0.89
R = np.tanh(1.2 * R / peak) / np.tanh(1.2) * 0.89
stereo = np.stack([L, R], axis=1)
pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {OUT}  {T_END:.2f}s")
