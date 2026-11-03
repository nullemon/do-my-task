"""
OMINOUS #3 - 72 SECONDS : procedural soundtrack (numpy only) -> soundtrack.wav, 48 kHz stereo.

Layers
  - wind / radio-hiss bed (filtered noise, slow swells)
  - low drone (detuned saws through a soft low-pass) + sub-bass swells
  - a faint 1420 MHz nod: a pure tone "hydrogen line" shimmer that rises with the printout
  - soft pulses on each text beat, line-printer ticks while the printout scrolls
  - the circle: a single resonant ping; at the end: static burst, one blip, then silence.
Beat times (seconds) match script.py.
"""
import numpy as np
import wave, os

SR = 48000
DUR = 26.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(1977)




def lp_fft(x, fc, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = 1 / (1 + (f / fc) ** (2 * order))
    return np.fft.irfft(X * np.sqrt(H), len(x))


def bp_fft(x, f0, q):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    bw = f0 / q
    H = np.exp(-0.5 * ((f - f0) / bw) ** 2)
    return np.fft.irfft(X * H, len(x))


def env(points):
    """piecewise-linear envelope from [(time, value), ...]"""
    ts, vs = zip(*points)
    return np.interp(t, ts, vs)


def smooth(x, sec):
    k = max(1, int(sec * SR))
    c = np.cumsum(np.insert(x, 0, 0.0))
    y = (c[k:] - c[:-k]) / k
    return np.concatenate([np.full(k - 1, y[0]), y])


END = 25.6  # hard cut

# ---------------- wind / hiss bed
w = rng.standard_normal(N)
wind = lp_fft(w, 380, 2)
gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.07 * t + 1.0) * np.sin(2 * np.pi * 0.023 * t)
wind *= gust
wind /= np.max(np.abs(wind))
windR = lp_fft(rng.standard_normal(N), 380, 2) * gust
windR /= np.max(np.abs(windR))
hiss = bp_fft(rng.standard_normal(N), 4200, 1.2)
hiss /= np.max(np.abs(hiss))
bed_env = env([(0, 0.6), (0.4, 1.0), (8.3, 1.0), (8.5, 0.45), (15.9, 0.45), (16.5, 1.0), (24.6, 1.0), (END, 1.0)])

# ---------------- drone: A1 (55 Hz) with fifth + minor ninth colour
def saw(freq, phase=0.0):
    ph = (freq * t + phase) % 1.0
    return 2 * ph - 1


drone = np.zeros(N)
for f0, amp in [(55.0, 1.0), (55.0 * 1.0035, 0.8), (54.8, 0.7), (82.4, 0.35), (82.6, 0.3), (110.2, 0.18), (116.5, 0.06)]:
    drone += amp * saw(f0, rng.random())
drone = lp_fft(drone, 480, 2)
# slow filter-like movement via amplitude of a brighter copy
bright = lp_fft(saw(110.0) + saw(110.4, 0.3) + 0.5 * saw(164.8, 0.6), 900, 2)
mov = 0.5 + 0.5 * np.sin(2 * np.pi * t / 13.0 - 1.2)
drone = drone / np.max(np.abs(drone)) + 0.12 * mov * bright / np.max(np.abs(bright))
drone_env = env([(0, 0.0), (0.25, 0.75), (4.5, 0.85), (8.3, 1.0), (12.6, 1.15), (16.0, 0.9),
                 (19.6, 1.0), (22.3, 0.75), (24.6, 0.9), (END, 0.9)])

# ---------------- sub swells (sine 36.7 Hz ~ D1) under key beats
sub = np.sin(2 * np.pi * 36.7 * t) + 0.5 * np.sin(2 * np.pi * 73.4 * t) + 0.18 * np.sin(2 * np.pi * 110.1 * t)
sub_env = np.zeros(N)
for c, rise, fall, a in [(0.0, 0.05, 4.0, 0.8), (5.0, 1.0, 3.0, 0.6), (12.85, 1.5, 3.5, 1.0),
                         (16.4, 0.6, 3.0, 0.8), (19.6, 0.8, 2.8, 0.9), (22.6, 1.0, 2.5, 0.7)]:
    x = t - c
    e = np.where(x < 0, np.exp(x / rise) * (x > -4 * rise), np.exp(-x / fall))
    sub_env += a * e
sub *= sub_env

# ---------------- hydrogen-line shimmer (stylised: 1420 Hz, a nod to 1420 MHz)
sh = np.zeros(N)
for f0, ph in [(1420.0, 0.0), (1421.3, 1.0), (710.0, 2.0)]:
    sh += np.sin(2 * np.pi * f0 * t + ph)
sh *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.31 * t)
sh_env = env([(0, 0), (9.0, 0), (12.6, 0.5), (13.0, 1.0), (15.9, 0.6), (17.5, 0.0), (DUR, 0)])
sh *= sh_env

# ---------------- beat hits: soft low thump + airy tail
def hit(at, gain=1.0, pitch=48.0):
    x = t - at
    m = x >= 0
    out = np.zeros(N)
    xm = x[m]
    f = pitch * (1 + 0.6 * np.exp(-xm * 18))
    phase = 2 * np.pi * np.cumsum(f) / SR
    out[m] = np.sin(phase) * np.exp(-xm * 2.2) * (1 - np.exp(-xm * 300))
    return gain * out


hits = np.zeros(N)
for at, g in [(0.0, 0.9), (0.9, 0.55), (5.0, 0.6), (8.3, 0.75), (16.4, 0.8), (19.6, 0.9), (22.6, 0.6)]:
    hits += hit(at, g)

# ---------------- printer ticks while printout scrolls (8.3 - 12.6), decelerating
ticks = np.zeros(N)
tick_src = bp_fft(rng.standard_normal(N), 2600, 2.5)
tick_src /= np.max(np.abs(tick_src))
tt = 8.35
while tt < 12.6:
    i0 = int(tt * SR)
    L = int(0.018 * SR)
    seg = tick_src[i0:i0 + L] * np.exp(-np.arange(L) / (0.004 * SR))
    ticks[i0:i0 + L] += seg * 0.8
    prog = (tt - 8.3) / 4.3
    tt += 0.045 + 0.30 * prog ** 2.0

# ---------------- the circle: resonant ping (two partials) at 12.85
ping = np.zeros(N)
x = t - 12.85
m = x >= 0
for f0, a, d in [(880.0, 0.5, 1.8), (1320.0, 0.25, 1.2), (440.0, 0.35, 2.6)]:
    ping[m] += a * np.sin(2 * np.pi * f0 * x[m]) * np.exp(-x[m] / d) * (1 - np.exp(-x[m] * 200))

# ---------------- ending: static burst 24.6-25.5, blip at 25.0, cut at END
static = rng.standard_normal(N)
static = bp_fft(static, 3000, 0.7)
static /= np.max(np.abs(static))
crackle = (rng.random(N) < 0.002) * rng.standard_normal(N) * 3
st_env = env([(0, 0), (24.5, 0), (24.65, 1.0), (24.95, 0.8), (25.0, 0.15), (25.35, 0.5), (25.55, 0.9), (END, 0.9), (END + 0.001, 0), (DUR, 0)])
static = (static + lp_fft(crackle, 5000)) * st_env
blip = np.zeros(N)
x = t - 25.0
m = (x >= 0) & (x < 0.4)
blip[m] = np.sin(2 * np.pi * 1420.0 * x[m]) * np.exp(-x[m] * 9) * (1 - np.exp(-x[m] * 800))

# ---------------- mix
L = (0.17 * wind + 0.03 * hiss) * bed_env + 0.30 * drone * drone_env + 0.24 * sub \
    + 0.045 * sh + 0.45 * hits + 0.10 * ticks + 0.11 * ping + 0.16 * static + 0.32 * blip
R = (0.17 * windR + 0.03 * np.roll(hiss, 977)) * bed_env + 0.30 * np.roll(drone, 240) * drone_env + 0.24 * sub \
    + 0.045 * np.roll(sh, 300) + 0.45 * hits + 0.10 * np.roll(ticks, 90) + 0.11 * np.roll(ping, 160) \
    + 0.16 * np.roll(static, 50) + 0.32 * blip

# simple stereo "room": short decaying echoes
for d, g in [(0.083, 0.22), (0.131, 0.16), (0.197, 0.11)]:
    k = int(d * SR)
    L[k:] += g * R[:-k] * 0.6
    R[k:] += g * L[:-k] * 0.6

mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.4) / 1.4          # gentle saturation
# hard cut + silence at the end
mix[int(END * SR):] = 0
fade_in = np.minimum(1, t / 0.02)[:, None]
mix *= fade_in
mix *= 0.89 / np.max(np.abs(mix))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundtrack.wav")
pcm = (mix * 32767).astype(np.int16)
with wave.open(out, "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())
print("wrote", out, pcm.shape[0] / SR, "s")
