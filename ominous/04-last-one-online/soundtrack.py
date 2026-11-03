"""
OMINOUS #4 -- LAST ONE ONLINE : soundtrack
Pure Python + numpy. Writes soundtrack.wav (48 kHz, 16-bit stereo) next to this file.

Layers
  * low drone (E1 / B1 / E2, slowly beating, soft-saturated)
  * dark space "air" (FFT-filtered noise, slowly breathing)
  * mains hum (50 Hz + harmonics) whose level follows how many lights are still on;
    it crackles and drops out as the grid fails
  * sub-bass swell building under the blackout
  * soft low hits on each text beat
  * a quiet ping on every blink of the last light
  * at the moment the last light dies: everything cuts, one deep hit, reverb tail, silence
Timing mirrors the CONFIG in script.py.
"""
import os, wave
import numpy as np

SR = 48000
DURATION = 24.0
WAVE_START, WAVE_END = 2.2, 16.8
BLINK_START, BLINK_PERIOD, LAST_OUT = 16.2, 1.1, 21.6
TEXT_BEATS = [0.25, 5.2, 10.0, 17.4]

rng = np.random.default_rng(4)
N = int(SR * DURATION)
t = np.arange(N) / SR


def smoothstep(a, b, x):
    y = np.clip((x - a) / (b - a), 0, 1)
    return y * y * (3 - 2 * y)


def fft_filter(x, lo=None, hi=None, slope=2.0):
    """Gentle band filter in the frequency domain (soft Butterworth-like magnitudes)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR) + 1e-6
    g = np.ones_like(f)
    if hi is not None:
        g *= 1 / np.sqrt(1 + (f / hi) ** (2 * slope))
    if lo is not None:
        g *= 1 / np.sqrt(1 + (lo / f) ** (2 * slope))
    return np.fft.irfft(X * g, len(x))


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-9)


def reverb(x, seconds=3.2, damp_hz=2500):
    n = int(SR * seconds)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir = fft_filter(ir, lo=80, hi=damp_hz)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)
    return y[: len(x)]


# grid alive fraction (same easing as the picture)
x = smoothstep(WAVE_START, WAVE_END, t)
x = 0.55 * x + 0.45 * x ** 1.6
alive = np.clip(1.0 - x * 1.05, 0, 1)
end_cut = 1.0 - smoothstep(LAST_OUT - 0.02, LAST_OUT + 0.05, t)

# --- drone ------------------------------------------------------------------
drone = np.zeros(N)
for f0, a, det in ((41.2, 1.0, 0.11), (61.74, 0.55, 0.07), (82.41, 0.35, 0.13), (123.5, 0.10, 0.05)):
    ph1 = 2 * np.pi * f0 * t
    ph2 = 2 * np.pi * (f0 + det) * t + 1.3
    drone += a * (np.sin(ph1) + 0.8 * np.sin(ph2))
drone = np.tanh(0.6 * drone) * (0.75 + 0.25 * np.sin(2 * np.pi * t / 9.0))
drone *= smoothstep(0.0, 2.0, t) * (1 - 0.35 * smoothstep(14, 21, t))
drone = fft_filter(drone, hi=380)

# --- space air ------------------------------------------------------------------
air = fft_filter(rng.standard_normal(N), lo=60, hi=520, slope=1.5)
air = norm(air) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 6.5 + 1.0) ** 2)
air *= smoothstep(0, 3, t)

# --- mains hum: the sound of the grid ------------------------------------------
hum = np.zeros(N)
for k, a in ((1, 1.0), (2, 0.55), (3, 0.30), (4, 0.16), (6, 0.08), (8, 0.04)):
    hum += a * np.sin(2 * np.pi * 50 * k * t + k)
hum = fft_filter(hum, hi=700)
# dropouts / crackle while failing: block-wise random gating
blk = int(SR * 0.045)
gates = (rng.random(N // blk + 1) > (0.55 * smoothstep(WAVE_START, WAVE_END, np.arange(N // blk + 1) * blk / SR) *
                                    (1 - smoothstep(WAVE_END, WAVE_END + 1, np.arange(N // blk + 1) * blk / SR)))).astype(float)
gate = np.repeat(gates, blk)[:N]
gate = np.convolve(gate, np.ones(240) / 240, mode="same")
hum *= alive ** 1.3 * gate * smoothstep(0.0, 1.0, t)

# --- sub swell ----------------------------------------------------------------------
sub_env = smoothstep(3, 15.5, t) * (1 - smoothstep(16.0, 18.5, t)) + 0.35 * smoothstep(18.5, 21.0, t)
sub = np.sin(2 * np.pi * (28 + 3 * smoothstep(3, 15.5, t)) * t) * sub_env

# --- hits ---------------------------------------------------------------------------
def hit(at, amp=1.0, f_hi=78, f_lo=38, dur=2.2):
    y = np.zeros(N)
    i0 = int(at * SR)
    n = min(int(dur * SR), N - i0)
    tt = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-tt * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = (1 - np.exp(-tt * 120)) * np.exp(-tt * 2.2)
    body = np.sin(ph) * env
    nz = fft_filter(rng.standard_normal(n), lo=40, hi=900) * np.exp(-tt * 10) * 0.25
    y[i0:i0 + n] = amp * (body + norm(nz) * 0.18)
    return y

hits = sum(hit(b, 0.8) for b in TEXT_BEATS)

# --- blink pings ------------------------------------------------------------------
ping = np.zeros(N)
k = 0
while True:
    at = BLINK_START + k * BLINK_PERIOD
    if at >= LAST_OUT:
        break
    i0 = int(at * SR)
    n = int(0.9 * SR)
    tt = np.arange(n) / SR
    env = (1 - np.exp(-tt * 300)) * np.exp(-tt * 7)
    s = (np.sin(2 * np.pi * 659.3 * tt) + 0.35 * np.sin(2 * np.pi * 329.6 * tt)) * env
    ping[i0:i0 + n] += s[: N - i0] * (0.75 + 0.25 * (k % 2))
    k += 1

final = hit(LAST_OUT, 0.8, f_hi=60, f_lo=30, dur=3.0)

# --- mix ---------------------------------------------------------------------------
dry = (0.50 * drone + 0.10 * air + 0.075 * hum + 0.40 * sub) * end_cut + 0.55 * hits * end_cut
dry_ping = 0.16 * ping
wet = reverb(dry * 0.6 + dry_ping * 2.0 + final * 0.5, 3.4)
mixL = dry + dry_ping + final + 0.35 * wet
# stereo: decorrelated air & reverb
air2 = norm(fft_filter(rng.standard_normal(N), lo=60, hi=520, slope=1.5)) * smoothstep(0, 3, t)
mixR = mixL + 0.06 * (air2 - air) * end_cut
mixR = 0.98 * mixR

out = np.stack([mixL, mixR], 1)
out *= 1 - smoothstep(DURATION - 1.6, DURATION - 0.3, t)[:, None]   # silence before the cut
out *= smoothstep(0, 0.02, t)[:, None]
out = np.tanh(out / (np.max(np.abs(out)) + 1e-9) * 1.3) / np.tanh(1.3) * 0.89

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype("<i2").tobytes())
print("wrote", path, "%.1fs" % DURATION)
