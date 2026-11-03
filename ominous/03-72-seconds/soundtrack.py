"""
OMINOUS #3 - 72 SECONDS : procedural soundtrack (numpy only) -> soundtrack.wav, 48 kHz stereo.

Layers
  - wind / radio-hiss bed (filtered noise, slow swells)
  - low drone (detuned saws through a soft low-pass) + sub-bass swells
  - a faint 1420 MHz nod: a pure tone "hydrogen line" shimmer that rises with the printout
  - soft pulses on each text beat, line-printer ticks while the printout scrolls
  - the circle: a single resonant ping
  - desk scene: room tone, 60 Hz mains hum, paper rustles
  - searches: soft repeating "sonar" pings; NOTHING: everything drops away
  - demolition: a slow descending sub; ending: wide pad, rising hiss, static,
    silence, one 1420 Hz blip, static, hard cut.
Beat times (seconds) match the 55 s TIMELINE in script.py
(S3 beats = v1 time + 5.75 s).
"""
import numpy as np
import wave, os

SR = 48000
DUR = 55.0
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


END = 54.6  # hard cut
SH = 5.75   # S3 shift

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
bed_env = env([(0, 0.6), (0.4, 1.0), (8.25, 1.0), (8.32, 0.12), (14.25, 0.12), (14.32, 0.45), (21.65, 0.45), (22.2, 1.0),
               (37.2, 1.0), (37.5, 0.35), (38.5, 0.35), (39.0, 1.0), (44.5, 0.9), (49.0, 1.0), (52.8, 1.25), (END, 1.25)])

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
drone_env = env([(0, 0.0), (0.25, 0.75), (4.5, 0.85), (8.25, 0.95), (8.32, 0.35), (14.25, 0.45), (14.35, 1.0),
                 (18.35, 1.15), (21.7, 0.9), (25.4, 1.0), (31.4, 1.05), (37.2, 1.0), (37.45, 0.15), (38.45, 0.15),
                 (38.6, 1.0), (44.4, 0.9), (44.6, 0.7), (52.8, 1.0), (53.3, 0.0), (END, 0.0)])

# ---------------- sub swells (sine 36.7 Hz ~ D1) under key beats
sub = np.sin(2 * np.pi * 36.7 * t) + 0.5 * np.sin(2 * np.pi * 73.4 * t) + 0.18 * np.sin(2 * np.pi * 110.1 * t)
sub_env = np.zeros(N)
for c, rise, fall, a in [(0.0, 0.05, 4.0, 0.8), (5.0, 1.0, 3.0, 0.6), (12.85 + SH, 1.5, 3.5, 1.0),
                         (16.4 + SH, 0.6, 3.0, 0.8), (25.4, 0.6, 3.0, 0.7), (31.5, 0.6, 3.0, 0.7),
                         (38.6, 0.3, 4.5, 1.0), (45.4, 1.2, 3.5, 0.7), (49.6, 1.5, 3.0, 0.7)]:
    x = t - c
    e = np.where(x < 0, np.exp(np.minimum(x, 0) / rise) * (x > -4 * rise), np.exp(-np.maximum(x, 0) / fall))
    sub_env += a * e
sub *= sub_env

# ---------------- hydrogen-line shimmer (stylised: 1420 Hz, a nod to 1420 MHz)
sh = np.zeros(N)
for f0, ph in [(1420.0, 0.0), (1421.3, 1.0), (710.0, 2.0)]:
    sh += np.sin(2 * np.pi * f0 * t + ph)
sh *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.31 * t)
sh_env = env([(0, 0), (14.6, 0), (18.35, 0.5), (18.75, 1.0), (21.65, 0.6), (23.2, 0.0), (26.85, 0.0), (27.0, 1.3), (30.5, 0.8), (31.4, 0.0), (DUR, 0)])
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
for at, g in [(0.0, 0.9), (0.9, 0.55), (5.0, 0.6), (8.3, 0.4), (14.3, 0.75), (16.4 + SH, 0.8), (25.4, 0.7), (31.5, 0.7), (37.3, 0.9), (38.6, 0.6), (44.5, 0.5), (49.6, 0.6)]:
    hits += hit(at, g)

# ---------------- printer ticks while printout scrolls (8.3 - 12.6), decelerating
ticks = np.zeros(N)
tick_src = bp_fft(rng.standard_normal(N), 2600, 2.5)
tick_src /= np.max(np.abs(tick_src))
tt = 8.35 + SH
while tt < 12.6 + SH:
    i0 = int(tt * SR)
    L = int(0.018 * SR)
    seg = tick_src[i0:i0 + L] * np.exp(-np.arange(L) / (0.004 * SR))
    ticks[i0:i0 + L] += seg * 0.8
    prog = (tt - 8.3 - SH) / 4.3
    tt += 0.045 + 0.30 * prog ** 2.0

# ---------------- the circle: resonant ping (two partials) at 12.85
ping = np.zeros(N)
x = t - (12.85 + SH)
m = x >= 0
for f0, a, d in [(880.0, 0.5, 1.8), (1320.0, 0.25, 1.2), (440.0, 0.35, 2.6)]:
    ping[m] += a * np.sin(2 * np.pi * f0 * x[m]) * np.exp(-x[m] / d) * (1 - np.exp(-x[m] * 200))

# ---------------- ending: static burst 24.6-25.5, blip at 25.0, cut at END
static = rng.standard_normal(N)
static = bp_fft(static, 3000, 0.7)
static /= np.max(np.abs(static))
crackle = (rng.random(N) < 0.002) * rng.standard_normal(N) * 3
st_env = env([(0, 0), (52.7, 0), (52.85, 1.0), (53.25, 0.8), (53.35, 0.0), (54.2, 0.0), (54.27, 1.0), (END, 0.9), (END + 0.001, 0), (DUR, 0)])
static = (static + lp_fft(crackle, 5000)) * st_env
blip = np.zeros(N)
x = t - 53.76
m = (x >= 0) & (x < 0.5)
blip[m] = np.sin(2 * np.pi * 1420.0 * x[m]) * np.exp(-x[m] * 7) * (1 - np.exp(-x[m] * 800))

# ---------------- desk (S2): room tone, mains hum, paper rustle
room = np.zeros(N)
dm = (t >= 8.3) & (t < 14.3)
hum = 0.6 * np.sin(2 * np.pi * 60 * t) + 0.3 * np.sin(2 * np.pi * 120 * t) + 0.12 * np.sin(2 * np.pi * 180 * t)
rust_src = bp_fft(rng.standard_normal(N), 3200, 0.9)
rust_src /= np.max(np.abs(rust_src))
rustle = np.zeros(N)
for c, d in [(8.9, 0.5), (10.6, 0.35), (12.4, 0.6)]:
    xx = t - c
    e = np.clip(xx / 0.08, 0, 1) * np.exp(-np.clip(xx, 0, None) / d) * (xx >= 0)
    rustle += rust_src * e * (0.6 + 0.4 * np.sin(2 * np.pi * 13 * xx))
desk_env = env([(0, 0), (8.28, 0), (8.32, 1), (14.25, 1), (14.29, 0), (DUR, 0)])
room = (0.5 * hum + 0.8 * rustle) * desk_env

# ---------------- searches (S5): soft repeating pings, like sweeps that return nothing
pings = np.zeros(N)
for c in [31.9, 33.1, 34.3, 35.5, 36.7]:
    x = t - c
    m = x >= 0
    pings[m] += np.sin(2 * np.pi * 659.3 * x[m]) * np.exp(-x[m] / 0.9) * (1 - np.exp(-x[m] * 300))
    pings[m] += 0.4 * np.sin(2 * np.pi * 988.0 * x[m]) * np.exp(-x[m] / 0.5)

# ---------------- demolition (S6): a slow descending sub-tone
x = t - 40.4
m = (x >= 0) & (t < 44.5)
fdesc = 98.0 * np.exp(-x[m] * 0.18)
desc = np.zeros(N)
desc[m] = np.sin(2 * np.pi * np.cumsum(fdesc) / SR) * np.clip(x[m] / 1.0, 0, 1) * np.clip((44.5 - t[m]) / 0.8, 0, 1)

# ---------------- final listening (S7): a wide, high, cold pad
pad = np.zeros(N)
for f0 in [220.0, 220.6, 329.6, 330.3, 440.0, 493.9]:
    pad += np.sin(2 * np.pi * f0 * t + rng.random() * 6)
pad *= env([(0, 0), (44.5, 0), (47.5, 0.7), (51.5, 1.0), (52.8, 1.0), (53.3, 0.0), (DUR, 0)])

# ---------------- mix
L = (0.17 * wind + 0.03 * hiss) * bed_env + 0.30 * drone * drone_env + 0.24 * sub \
    + 0.045 * sh + 0.45 * hits + 0.10 * ticks + 0.11 * ping + 0.16 * static + 0.32 * blip \
    + 0.05 * room + 0.05 * pings + 0.25 * desc + 0.02 * pad
R = (0.17 * windR + 0.03 * np.roll(hiss, 977)) * bed_env + 0.30 * np.roll(drone, 240) * drone_env + 0.24 * sub \
    + 0.045 * np.roll(sh, 300) + 0.45 * hits + 0.10 * np.roll(ticks, 90) + 0.11 * np.roll(ping, 160) \
    + 0.16 * np.roll(static, 50) + 0.32 * blip \
    + 0.05 * np.roll(room, 200) + 0.05 * np.roll(pings, 700) + 0.25 * desc + 0.02 * np.roll(pad, 400)

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
