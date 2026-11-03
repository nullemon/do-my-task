"""
OMINOUS #5 - NO FLOOR : procedural soundtrack (pure Python + numpy).
Writes soundtrack.wav (48 kHz, stereo, 16-bit) next to this file.

Layers
  * upper-atmosphere wind: filtered noise whose brightness closes down as the
    pressure rises (the world gets thicker and more muffled)
  * drone: detuned low partials on A (55 Hz) that sag slowly flat as we sink
  * sub-bass swells under each text beat
  * soft "hits" (felt-mallet sine + low thump) on every text beat
  * distant thunder: low noise rumbles a fraction of a second after each
    lightning flash in the video
  * hard cut to silence at the end (on "NO FLOOR." fading out)
Run:  python soundtrack.py
"""
import os, wave
import numpy as np

SR = 48000
DUR = 28.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(55)

# beats taken from script.py timeline (seconds)
TEXT_BEATS = [0.12, 3.9, 8.6, 13.3, 17.9]
BIG_BEATS = [21.6, 24.2, 26.3]
FLASHES = [11.6, 12.9, 13.6, 14.8, 15.3, 16.4, 17.1, 18.0, 19.2, 20.3, 21.9, 23.6, 25.1, 26.8]
END_CUT = 27.75


def smooth(a, b, x):
    y = np.clip((x - a) / (b - a), 0, 1)
    return y * y * (3 - 2 * y)


def onepole_lp(x, fc):
    """One-pole low-pass with (optionally time-varying) cutoff fc (Hz)."""
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # ~1.3M steps, a couple of seconds
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def fft_band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    w = smooth(lo * 0.7, lo, f) * (1 - smooth(hi, hi * 1.4, f))
    return np.fft.irfft(X * w, n=len(x))


def norm(x):
    return x / (np.max(np.abs(x)) + 1e-12)


# ---------------------------------------------------------------- wind
depth = smooth(0, 26, t)                      # 0 = cloud tops, 1 = deep
wind_src = rng.normal(size=N)
cut = 1100 * (1 - depth) ** 2 + 80            # Hz: closes from ~1.2 kHz to ~80 Hz
wind = onepole_lp(onepole_lp(onepole_lp(wind_src, cut), cut), cut)
gust = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1.0) * np.sin(2 * np.pi * 0.047 * t)
wind = norm(wind) * gust * (0.42 * (1 - 0.6 * depth)) * smooth(0, 0.8, t)

# ---------------------------------------------------------------- drone
f0 = 55.0 * 2 ** (-depth * 3 / 12)            # sags three semitones over the fall
phase = 2 * np.pi * np.cumsum(f0) / SR
drone = np.zeros(N)
for mult, amp, det in [(1, 1.0, 0.0), (1, 0.7, 0.21), (1.5, 0.35, -0.13), (2, 0.55, 0.17), (3, 0.40, 0.05), (4.02, 0.28, 0.0), (5, 0.16, -0.07), (6, 0.10, 0.11)]:
    drone += amp * np.sin(mult * phase + 2 * np.pi * det * t * mult)
# slow beating / breathing
drone *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
drone = onepole_lp(drone, 1400)
drone = norm(drone) * 0.30 * smooth(0, 2.5, t) * (0.8 + 0.4 * depth)

# ---------------------------------------------------------------- pressure whine
# a thin, glassy high tone that creeps in once we pass the probe's last signal
wph = 2 * np.pi * np.cumsum(660.0 * 2 ** (-0.6 * smooth(17, 28, t) / 12) * (1 + 0.003 * np.sin(2 * np.pi * 5.1 * t))) / SR
whine = (np.sin(wph) + 0.4 * np.sin(1.5 * wph + 0.3)) * smooth(16.5, 23.0, t) * 0.035

# ---------------------------------------------------------------- sub swells
sub = np.zeros(N)
for b in TEXT_BEATS + BIG_BEATS:
    e = smooth(b - 1.2, b, t) * np.exp(-np.clip(t - b, 0, None) / 2.4)
    sub += e * np.sin(2 * np.pi * 36.7 * t)
sub = sub * 0.22

# ---------------------------------------------------------------- hits
hits = np.zeros(N)
for i, b in enumerate(TEXT_BEATS + BIG_BEATS):
    big = b in BIG_BEATS
    tt = t - b
    m = tt >= 0
    env = np.where(m, np.exp(-np.clip(tt, 0, None) / (2.8 if big else 1.6)), 0) * smooth(0, 0.008, tt)
    pitch = 110.0 if big else 220.0
    tone = np.sin(2 * np.pi * pitch * tt) + 0.35 * np.sin(2 * np.pi * pitch * 2.01 * tt) * np.exp(-np.clip(tt, 0, None) * 3)
    thump = np.sin(2 * np.pi * (48 + 40 * np.exp(-np.clip(tt, 0, None) * 25)) * tt) * np.exp(-np.clip(tt, 0, None) * 6)
    hits += env * (0.11 * tone) + np.where(m, 0.30 * thump, 0) * (1.3 if big else 0.8)

# ---------------------------------------------------------------- thunder
thunder_src = fft_band(rng.normal(size=N), 25, 220)
thunder = np.zeros(N)
for k, f in enumerate(FLASHES):
    d = f + rng.uniform(0.25, 0.9)
    tt = t - d
    deep = f > 19.5
    env = smooth(0, 0.08, tt) * np.exp(-np.clip(tt, 0, None) / (1.6 if not deep else 2.6))
    roll = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(3, 7) * tt) ** 2
    thunder += env * roll * (0.9 if not deep else 0.55)
thunder = norm(thunder_src) * thunder * 0.55

# ---------------------------------------------------------------- mix
mix = wind + drone + whine + sub + hits + thunder
mix *= 1 - smooth(END_CUT - 0.05, END_CUT, t)       # silence at the cut
mix = np.tanh(mix * 1.1) / np.tanh(1.1)             # gentle soft clip
mix = norm(mix) * 0.85

# subtle stereo: decorrelated wind + tiny delay on the drone
L = mix + 0.06 * norm(fft_band(rng.normal(size=N), 200, 1200)) * (1 - depth) * 0.3
R = np.roll(mix, int(0.011 * SR))
R[: int(0.011 * SR)] = 0
st = np.stack([L, R], axis=1)
st = st / (np.max(np.abs(st)) + 1e-9) * 0.89
# 10 ms fades at the edges to avoid clicks
fade = int(0.01 * SR)
st[:fade] *= np.linspace(0, 1, fade)[:, None]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
print("wrote", out, f"{DUR:.1f}s")
