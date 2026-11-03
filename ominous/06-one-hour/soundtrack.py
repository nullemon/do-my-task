"""
OMINOUS #6 - ONE HOUR : procedural soundtrack (pure Python + numpy)
Writes soundtrack.wav (48 kHz, 16-bit stereo) synced to script.py's timeline.

  * low drone (A1 + fifth + octave, slow beating) that sinks slightly in pitch
    as the craft descends; a dark filtered "wind" bed
  * sub-bass swells on every text beat, a soft deep hit on the hook and finale
  * HERE: one quiet tick per second (it never changes speed)
  * HOME: ticks that accelerate with the dilation factor until they smear into
    a thin, rising golden shimmer; it collapses as the ship turns away
  * cut to silence in the last half-second (the video cuts to black)
Run:  python soundtrack.py
"""
import math
import os
import wave

import numpy as np

SR = 48000
DUR = 26.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(6)

# --- timeline (must match script.py) ---------------------------------------
T_CLOCK0 = 3.6
T_RAMP = (4.2, 19.0)
FINAL_FACTOR = 61000.0
BEATS = [0.0, T_CLOCK0, 6.4, 11.2, 16.2, 22.7, 23.4]
T_TURN = (20.6, 24.2)
T_CUT = 25.62


def smooth(a, b, x):
    s = np.clip((x - a) / (b - a), 0, 1)
    return s * s * (3 - 2 * s)


def smoother(a, b, x):
    s = np.clip((x - a) / (b - a), 0, 1)
    return s * s * s * (s * (s * 6 - 15) + 10)


def factor(x):
    return np.exp(np.log(FINAL_FACTOR) * smoother(T_RAMP[0], T_RAMP[1], x))


def spectral_filter(x, lo=None, hi=None, order=2):
    """Zero-phase smooth band filter by FFT (Butterworth-shaped magnitude)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = np.ones_like(f)
    if hi:
        H *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    if lo:
        H *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    return np.fft.irfft(X * H, len(x))


def osc(freq_curve, phase0=0.0):
    ph = 2 * np.pi * np.cumsum(freq_curve) / SR + phase0
    return np.sin(ph)


# --- drone -------------------------------------------------------------------
descent = smooth(3.0, 24.0, t)
base = 55.0 * (1 - 0.06 * descent)                 # sinks ~ a semitone
drone = np.zeros(N)
for mult, amp, det in [(1, 0.55, 0.0), (1, 0.35, 0.18), (1.5, 0.22, -0.11), (2, 0.26, 0.07), (3, 0.12, 0.0), (4, 0.06, 0.13)]:
    drone += amp * osc(base * mult + det, rng.uniform(0, 6.28))
drone *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
drone = spectral_filter(drone, hi=420)
drone_env = smooth(0.0, 0.25, t) * (0.55 + 0.45 * descent)

wind = spectral_filter(rng.standard_normal(N), lo=60, hi=380, order=2)
wind /= np.abs(wind).max()
wind *= 0.35 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.045 * t + 1.0)) * (0.5 + 0.5 * descent)

# --- sub swells & hits ---------------------------------------------------------
sub = np.zeros(N)
for i, b in enumerate(BEATS):
    big = b in (0.0, 22.7)
    dur = 3.2 if big else 2.4
    env = np.where(t >= b, np.exp(-(t - b) / (1.1 if big else 0.8)), 0.0) * smooth(b, b + 0.06, t)
    f0 = 41.0 if big else 46.0
    sweep = f0 * (1 + 0.5 * np.exp(-np.clip(t - b, 0, None) / 0.08))
    sub += (0.95 if big else 0.55) * env * osc(sweep)
    # soft felt "hit": low-passed noise thump
    nb = rng.standard_normal(N) * np.where(t >= b, np.exp(-(t - b) / 0.05), 0.0)
    sub += (0.35 if big else 0.18) * spectral_filter(nb, hi=180)
    _ = dur

# --- HERE ticks (1 per second) -----------------------------------------------------
clock_vis = smooth(T_CLOCK0, T_CLOCK0 + 0.8, t) * (1 - smooth(21.9, 22.7, t))


def tick_kernel(freq, dec, n=1400):
    k = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * k) * np.exp(-k / dec)
    s += 0.4 * rng.standard_normal(n) * np.exp(-k / (dec * 0.3))
    return s


here = np.zeros(N)
kh = tick_kernel(1900, 0.006)
tt = T_CLOCK0
while tt < 22.7:
    i = int(tt * SR)
    seg = kh[: N - i]
    here[i:i + len(seg)] += seg * (0.9 if int(round(tt - T_CLOCK0)) % 2 == 0 else 0.7)
    tt += 1.0
here = spectral_filter(here, lo=600, hi=5000) * 0.22

# --- HOME ticks -> shimmer -----------------------------------------------------------
fac = factor(t)
rate = np.minimum(fac, 28.0)
rate = np.where(t >= T_CLOCK0, rate, 0.0)
phase = np.cumsum(rate) / SR
ticks_idx = np.nonzero(np.diff(np.floor(phase)) > 0)[0]
home = np.zeros(N)
kg = tick_kernel(2600, 0.004, 900)
for i in ticks_idx:
    seg = kg[: N - i]
    home[i:i + len(seg)] += seg
tick_fade = 1 - smooth(12.0, 16.0, t)              # ticks smear away into the tone
home = spectral_filter(home, lo=900, hi=7000) * 0.15 * tick_fade

lf = np.log10(np.maximum(fac, 1.0))               # 0 .. 4.79
tone_amp = smooth(1.6, 4.4, lf) * (1 - smooth(T_TURN[0] + 0.5, T_TURN[1] - 0.3, t))
pitch = 196.0 * 2 ** (0.62 * np.clip(lf - 1.5, 0, None))   # G3 -> ~800 Hz
shimmer = np.zeros(N)
for mult, amp in [(1, 0.5), (2.003, 0.25), (3.01, 0.10), (1.498, 0.18)]:
    shimmer += amp * osc(pitch * mult, rng.uniform(0, 6.28))
shimmer *= 0.7 + 0.3 * np.sin(2 * np.pi * (4 + 6 * smooth(10, 20, t)) * t)   # flutter speeds up
grain = spectral_filter(rng.standard_normal(N), lo=2500, hi=9000)
grain /= np.abs(grain).max()
shimmer = shimmer * 0.09 * tone_amp + grain * 0.025 * tone_amp

# --- ending: the ship turns away; a long low exhale ----------------------------------
exhale = spectral_filter(rng.standard_normal(N), lo=40, hi=220) * smooth(20.8, 23.0, t) * (1 - smooth(23.5, 25.6, t))
exhale = exhale / np.abs(exhale).max() * 0.18

# --- mix ----------------------------------------------------------------------------
dry = 0.42 * drone * drone_env + wind * 0.5 + sub * 0.55 + here + home + shimmer + exhale


def reverb(x, secs=2.8, mix=0.28, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    k = np.arange(n) / SR
    L = r.standard_normal(n) * np.exp(-k / (secs / 6.0))
    R = r.standard_normal(n) * np.exp(-k / (secs / 6.0))
    L = spectral_filter(L, hi=3500); R = spectral_filter(R, hi=3500)
    L /= np.sqrt((L ** 2).sum()); R /= np.sqrt((R ** 2).sum())
    m = 1 << int(np.ceil(np.log2(len(x) + n)))
    X = np.fft.rfft(x, m)
    wl = np.fft.irfft(X * np.fft.rfft(L, m), m)[: len(x)]
    wr = np.fft.irfft(X * np.fft.rfft(R, m), m)[: len(x)]
    return x * (1 - mix) + wl * mix * 3, x * (1 - mix) + wr * mix * 3


left, right = reverb(dry)
# slow stereo width on the shimmer for space
pan = 0.5 + 0.35 * np.sin(2 * np.pi * 0.11 * t)
left += shimmer * 0.3 * (1 - pan)
right += shimmer * 0.3 * pan

master = smooth(0.0, 0.02, t) * (1 - smooth(T_CUT - 0.12, T_CUT, t))
left *= master
right *= master
st = np.stack([left, right], 1)
st = np.tanh(st / np.abs(st).max() * 1.15) / np.tanh(1.15) * 0.84     # gentle soft clip, ~-1.5 dBFS
pcm = (st * 32767).astype(np.int16)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out, "%.1fs" % DUR)
