"""
OMINOUS #1 - THE LAST SUNSET : procedural soundtrack (pure Python + numpy).
Writes soundtrack.wav (48 kHz, 16-bit stereo, 27.0 s) next to this file.

Layers
  * low drone on D (36.7 / 55 / 73.4 Hz, detuned pairs -> slow beating) that
    sags very slightly in pitch as the universe runs down
  * a faint high 'starlight' shimmer that thins out as the stars die (5-20 s)
  * sub-bass swells rising into each text beat, soft low thumps on the beats
  * dark wind (filtered brown noise)
  * a deep hit at the sunset (21.6 s), long decay, one last low tone under the
    final line, then a hard cut to silence at 26.6 s
Timing mirrors TEXT_BEATS / T_SUNSET in script.py.
"""
import os
import wave
import numpy as np

SR = 48000
DUR = 27.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(11)

BEATS = [0.10, 5.4, 10.4, 15.4]     # text beats
T_SUNSET = 21.6
T_BLACK = 23.2
T_END_TEXT = 23.5
T_CUT = 26.6


def sstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def lowpass_fft(x, fc, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = 1 / np.sqrt(1 + (f / fc) ** (2 * order))
    return np.fft.irfft(X * H, len(x))


def bandpass_fft(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = (1 / np.sqrt(1 + (f / hi) ** 4)) * (1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4))
    return np.fft.irfft(X * H, len(x))


def osc(freq_curve, phase0=0.0):
    ph = 2 * np.pi * np.cumsum(freq_curve) / SR + phase0
    return np.sin(ph)


# ---------------------------------------------------------------- drone ----
# pitch sags by ~60 cents over the piece (the universe running down)
sag = 2 ** (-0.6 / 12 * sstep(4.0, T_SUNSET, t))
drone = np.zeros(N)
for f0, amp in [(36.71, 0.55), (55.0, 0.38), (73.42, 0.22), (110.0, 0.07), (146.8, 0.035)]:
    for det in (-0.13, 0.11):
        lfo = 0.75 + 0.25 * np.sin(2 * np.pi * (0.05 + 0.03 * rng.random()) * t + rng.random() * 6.28)
        drone += amp * lfo * osc(f0 * sag + det, rng.random() * 6.28)
# soft saturation for warmth, then keep it dark
drone = np.tanh(drone * 0.8)
drone = lowpass_fft(drone, 600)
drone_env = (0.55 + 0.45 * sstep(0.0, 1.2, t)) * (0.85 + 0.35 * sstep(6, T_SUNSET, t))
drone_env *= 1 - 0.75 * sstep(T_SUNSET + 0.3, T_BLACK + 0.8, t)

# -------------------------------------------------------------- shimmer ----
shim = np.zeros(N)
partials = [587.3, 880.0, 1174.7, 1318.5, 1760.0, 2349.3]
for i, f in enumerate(partials):
    am = np.clip(np.sin(2 * np.pi * (0.07 + 0.05 * rng.random()) * t + rng.random() * 6.28), 0, 1) ** 3
    # higher (bluer) partials die first, like the hot stars
    die = 1 - sstep(5.0 + i * 0.4, 11.0 + i * 0.2, t) if i >= 2 else 1 - sstep(12.0, 20.0, t)
    shim += (0.05 / (1 + i * 0.4)) * am * die * osc(f * (1 + 0.0007 * np.sin(t * 0.3 + i)))
shim *= sstep(0.0, 2.0, t)

# ------------------------------------------------------------------ wind ---
wn = np.cumsum(rng.standard_normal(N))
wn -= np.convolve(wn, np.ones(4801) / 4801, mode="same")      # remove drift
wn = bandpass_fft(wn, 60, 500)
wn /= np.max(np.abs(wn)) + 1e-9
wind_env = 0.09 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t) ** 2) * sstep(0, 2.5, t) * (1 - sstep(T_SUNSET, T_BLACK + 1.0, t))
wind = wn * wind_env

# ---------------------------------------------------------- swells & hits --
sub = np.zeros(N)
hits = np.zeros(N)


def add_hit(t0, depth=1.0, decay=1.6):
    m = t >= t0
    tt = t[m] - t0
    f = 34 + 40 * np.exp(-tt * 9)                       # pitch drop
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / decay) * (1 - np.exp(-tt * 300))
    nz = rng.standard_normal(m.sum()) * np.exp(-tt / 0.18)
    hits[m] += depth * (0.85 * body + 0.05 * nz)


def add_swell(t_peak, length=3.0, amp=0.5, f=30.87):
    env = sstep(t_peak - length, t_peak, t) * (1 - sstep(t_peak, t_peak + 1.8, t))
    sub[:] += amp * env ** 2 * np.sin(2 * np.pi * f * t)


for i, b in enumerate(BEATS):
    if b > 1:
        add_swell(b, 3.2, 0.32 + 0.06 * i)
    add_hit(b + 0.05, 0.40 + 0.08 * i)

# sunset: the big one
add_swell(T_SUNSET, 5.0, 0.6, 27.5)
add_hit(T_SUNSET, 0.95, 3.2)
# final line: one low tone held under the text, cut dead at T_CUT
last = 0.22 * sstep(T_END_TEXT - 0.3, T_END_TEXT + 1.5, t) * osc(36.71 * 2 ** (-0.6 / 12) * np.ones(N))
last += 0.025 * sstep(T_END_TEXT, T_END_TEXT + 2.0, t) * osc(293.66 * 2 ** (-0.6 / 12) * np.ones(N)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t))
add_hit(T_END_TEXT + 0.05, 0.45, 2.0)

# ------------------------------------------------------------------- mix ---
dry = drone * drone_env * 0.55 + shim + wind + sub * 0.7 + hits * 0.8 + last


def reverb(x, seconds=3.2, seed=0):
    r = np.random.default_rng(seed)
    n = int(SR * seconds)
    tt = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-tt / (seconds / 6.9) * 1.0)
    ir = lowpass_fft(ir, 2500)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)]
    return y


wetL = reverb(dry, seed=1)
wetR = reverb(dry, seed=2)
L = dry + 0.45 * wetL
R = dry + 0.45 * wetR
# slight stereo width on the shimmer
L += 0.3 * np.roll(shim, 240)
R += 0.3 * np.roll(shim, -240)

st = np.stack([L, R], axis=1)
# hard cut at the end (2 ms ramp to avoid a click), silence after
cut = 1 - sstep(T_CUT, T_CUT + 0.002, t)
st *= cut[:, None]
# gentle fade-in from the loop point (3 ms) to avoid a click
st *= sstep(0, 0.003, t)[:, None]

peak = np.max(np.abs(st)) + 1e-9
st = st / peak * 0.89
st = np.tanh(st * 1.15) / np.tanh(1.15) * 0.89       # soft knee, never harsh

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out, f"{DUR}s")
