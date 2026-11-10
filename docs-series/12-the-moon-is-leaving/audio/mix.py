"""THE MOON IS LEAVING — voice placement (locked timeline), processing, music bed, ducking, loudness, SRT.
Adapted from andromeda-doc/audio/mix.py (same voice chain, same synthesis helpers).
Inputs : $SCR/vo_raw/<key>.wav + meta.json (gen_voice.py), ../timeline.py (START times)
Outputs: $SCR/audio/{voice_48k,bed_48k,mix_apophis}.wav, placement.json, ../the-moon-is-leaving.srt
Run    : /home/user/ttsenv/bin/python mix.py
"""
import os, sys, json, subprocess, re
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, resample_poly, fftconvolve
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import timeline as TL
SR = 48000
DUR = TL.DUR
N = int(SR * DUR)
rng = np.random.default_rng(7)
VO = os.path.join(TL.SCR, "vo_raw")
AOUT = os.path.join(TL.SCR, "audio"); os.makedirs(AOUT, exist_ok=True)
def P(*a): return os.path.join(AOUT, *a)

def place_lines():
    meta = json.load(open(os.path.join(VO, "meta.json")))
    out = []
    for l in meta["lines"]:
        s = TL.START[l["key"]]
        out.append(dict(l, start=s, end=round(s + l["dur"], 3), tempo=1.0))
    for a, b in zip(out, out[1:]):
        assert b["start"] - a["end"] >= 0.55, (a["key"], b["key"], b["start"] - a["end"])
    return meta, out

def load_clip(key):
    x, sr = sf.read(os.path.join(VO, f"{key}.wav")); assert sr == 24000
    return resample_poly(x, 2, 1)

def build_voice(placement):
    dry = np.zeros(N)
    for l in placement:
        x = load_clip(l["key"]); s = int(round(l["start"] * SR))
        dry[s:s + len(x)] += x[: N - s]
    dry = sosfilt(butter(4, 70, "high", fs=SR, output="sos"), dry)
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    sf.write(P("voice_dry.wav"), dry, SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", P("voice_dry.wav"), "-af",
                    "equalizer=f=250:t=q:w=1.0:g=-1.5,equalizer=f=3500:t=q:w=1.2:g=1.0,"
                    "acompressor=threshold=-22dB:ratio=3:attack=8:release=180:knee=6:makeup=4",
                    "-c:a", "pcm_f32le", P("voice_comp.wav")], check=True)
    v, _ = sf.read(P("voice_comp.wav"))
    ir = room_ir()
    wet = np.stack([fftconvolve(v, ir[:, c])[:N] for c in range(2)], axis=1)
    voice = v[:, None] * np.array([[1.0, 1.0]]) + 0.16 * wet
    os.remove(P("voice_dry.wav")); os.remove(P("voice_comp.wav"))
    return voice

def room_ir(length=0.9, rt60=0.55, seed=5):
    n = int(SR * length)
    t = np.arange(n) / SR
    r = np.random.default_rng(seed)
    env = np.exp(-6.91 * t / rt60)
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = r.standard_normal(n)
        noise = sosfilt(butter(2, [250, 6000], "band", fs=SR, output="sos"), noise)
        ir[:, c] = noise * env
    ir[: int(0.012 * SR)] = 0          # pre-delay
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    return ir


# ------------------------------------------------------------------------------------------- bed
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sustain_curve=None):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na > 0:
        e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))
    if nr > 0:
        e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e


def add(buf, t0, sig):
    s = int(t0 * SR)
    e = min(N, s + len(sig))
    buf[s:e] += sig[: e - s]


def pad_note(midi, t0, t1, amp, a=6.0, r=7.0, bright=0.5, nh=6, seed=0):
    """Warm detuned additive pad note, stereo, with slow 'filter' (harmonic tilt) movement."""
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    r_ = np.random.default_rng(seed + int(midi * 100) + int(t0 * 10))
    f = mtof(midi)
    out = np.zeros((n, 2))
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / r_.uniform(9, 17) + r_.uniform(0, 6.28))
    for h in range(1, nh + 1):
        if f * h > 9000:
            break
        tilt = (1.0 / h ** 1.6) * (bright * lfo + (1 - bright * lfo) * (1.0 / h)) if h > 1 else 1.0
        for c, det in enumerate((-1, 1)):
            cents = det * r_.uniform(3, 7)
            fh = f * h * 2 ** (cents / 1200)
            ph = r_.uniform(0, 6.28)
            out[:, c] += tilt * np.sin(2 * np.pi * fh * t + ph + 0.0015 * h * np.sin(2 * np.pi * 0.21 * t))
    return out * (amp * env_adsr(n, a, r))[:, None]


def drone(t0, t1, amp, base=38):  # D2 = 38
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for c in range(2):
        ph = np.random.default_rng(c + 7).uniform(0, 6.28, 6)
        f = mtof(base)
        sig = (np.sin(2 * np.pi * f * t + ph[0])
               + 0.55 * np.sin(2 * np.pi * f * 2 * 1.0007 * t + ph[1])
               + 0.35 * np.sin(2 * np.pi * mtof(base + 7) * (1.0004 if c else 0.9996) * t + ph[2])
               + 0.18 * np.sin(2 * np.pi * f * 3 * t + ph[3])
               + 0.10 * np.sin(2 * np.pi * f * 4 * 1.0011 * t + ph[4]))
        breathe = 0.8 + 0.2 * np.sin(2 * np.pi * t / 23.0 + ph[5])
        out[:, c] = sig * breathe
    return out * amp


def sub_swell(tc, amp, rise=7.0, fall=6.0, f=36.71):
    """Sub swell peaking at tc (chapter transition)."""
    n = int((rise + fall) * SR)
    t = np.arange(n) / SR
    env = np.where(t < rise, (t / rise) ** 2.2, np.exp(-(t - rise) / (fall / 3.2)))
    fm = f * (1 + 0.01 * np.exp(-((t - rise) ** 2) / 2))
    ph = 2 * np.pi * np.cumsum(fm) / SR
    sig = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
    # soft noise "air" rising into the transition
    noise = sosfilt(butter(2, [80, 900], "band", fs=SR, output="sos"), rng.standard_normal(n)) * 0.08
    s = (sig + noise * (t < rise)) * env * amp
    add_buf = np.stack([s, s], axis=1)
    return tc - rise, add_buf


def choir(t0, t1, notes, amp, vowel=(730, 1090, 2440), seed=3):
    """Formant-shaped additive 'aah' voices with vibrato — choir-like shimmer."""
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    r_ = np.random.default_rng(seed)
    for m in notes:
        for voice in range(3):
            f0 = mtof(m) * 2 ** (r_.uniform(-8, 8) / 1200)
            vib = 1 + 0.004 * np.sin(2 * np.pi * r_.uniform(4.6, 5.6) * t + r_.uniform(0, 6.28)) \
                * np.clip(t / 3.0, 0, 1)
            ph = 2 * np.pi * np.cumsum(f0 * vib) / SR
            pan = r_.uniform(0.15, 0.85)
            sig = np.zeros(n)
            for h in range(1, 40):
                fh = f0 * h
                if fh > 8000:
                    break
                w = sum(g * np.exp(-((fh - F) / bw) ** 2) for F, bw, g in
                        zip(vowel, (110, 140, 220), (1.0, 0.55, 0.25))) + 0.02 / h
                sig += w * np.sin(h * ph + r_.uniform(0, 6.28))
            sw = 0.6 + 0.4 * np.sin(2 * np.pi * t / r_.uniform(5, 11) + r_.uniform(0, 6.28))
            out[:, 0] += sig * sw * np.sqrt(1 - pan)
            out[:, 1] += sig * sw * np.sqrt(pan)
    out /= np.abs(out).max() + 1e-9
    return out * (amp * env_adsr(n, 3.5, 5.0))[:, None]


def sparkles(t0, t1, notes, density, amp, seed=11):
    """Glassy bell pings — stars igniting."""
    n = int((t1 - t0) * SR)
    out = np.zeros((n, 2))
    r_ = np.random.default_rng(seed)
    k = int(density * (t1 - t0))
    for _ in range(k):
        s = r_.integers(0, n - SR)
        L = int(SR * r_.uniform(1.5, 3.5))
        L = min(L, n - s)
        tt = np.arange(L) / SR
        f = mtof(r_.choice(notes))
        e = np.exp(-tt / r_.uniform(0.4, 1.0)) * np.clip(tt / 0.004, 0, 1)
        sig = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3)) * e
        g = r_.uniform(0.3, 1.0)
        pan = r_.uniform(0.1, 0.9)
        out[s:s + L, 0] += sig * g * np.sqrt(1 - pan)
        out[s:s + L, 1] += sig * g * np.sqrt(pan)
    # density envelope swells in the middle of the window
    tt = np.arange(n) / SR
    shape = np.sin(np.pi * np.clip(tt / (t1 - t0), 0, 1)) ** 0.8
    return out * shape[:, None] * amp


def air_noise(t0, t1, amp, lo=2000, hi=9000, seed=2):
    n = int((t1 - t0) * SR)
    r_ = np.random.default_rng(seed)
    x = r_.standard_normal((n, 2))
    sos = butter(2, [lo, hi], "band", fs=SR, output="sos")
    x = sosfilt(sos, x, axis=0)
    t = np.arange(n) / SR
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * t / 13.0)
    return x * (mod * env_adsr(n, 6, 6) * amp)[:, None]



def tick(amp, f=1800.0, dec=0.035, seed=0):
    """Soft clock tick: short filtered click + tiny pitched body."""
    n = int(0.25 * SR); t = np.arange(n) / SR
    r_ = np.random.default_rng(seed)
    click = sosfilt(butter(2, [1200, 6000], "band", fs=SR, output="sos"), r_.standard_normal(n)) * np.exp(-t / 0.006)
    body = np.sin(2 * np.pi * f * t) * np.exp(-t / dec) * 0.5 + np.sin(2 * np.pi * f * 0.5 * t) * np.exp(-t / (dec * 2)) * 0.3
    s = (click * 0.6 + body) * amp
    return np.stack([s, s], 1)

def thud(amp, f=42.0, dec=0.9):
    n = int(3.0 * SR); t = np.arange(n) / SR
    fm = f * (1 + 0.6 * np.exp(-t / 0.05))
    ph = 2 * np.pi * np.cumsum(fm) / SR
    s = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.exp(-t / dec) * np.clip(t / 0.004, 0, 1) * amp
    return np.stack([s, s], 1)

def riser(t0, t1, amp, f0=60, f1=420, seed=5):
    """Filtered-noise + rising tone swell (tension)."""
    n = int((t1 - t0) * SR); t = np.arange(n) / SR; u = t / (t1 - t0)
    r_ = np.random.default_rng(seed)
    noise = r_.standard_normal((n, 2))
    lo = sosfilt(butter(2, [150, 1500], "band", fs=SR, output="sos"), noise, axis=0)
    hi = sosfilt(butter(2, [1500, 8000], "band", fs=SR, output="sos"), noise, axis=0)
    nz = lo * (1 - u)[:, None] ** 0.5 + hi * (u ** 2)[:, None]
    f = f0 * (f1 / f0) ** (u ** 1.6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.4 * np.sin(1.5 * ph + 0.3) + 0.25 * np.sin(2.01 * ph))
    env = (u ** 2.2)
    return (0.5 * nz + np.stack([tone, tone * 0.98], 1) * 0.6) * (env * amp)[:, None]

def roar(t0, t1, amp, seed=8):
    """Deep rumbling roar for the plunge."""
    n = int((t1 - t0) * SR); t = np.arange(n) / SR; u = t / (t1 - t0)
    r_ = np.random.default_rng(seed)
    x = r_.standard_normal((n, 2))
    x = sosfilt(butter(2, [25, 260], "band", fs=SR, output="sos"), x, axis=0)
    mod = 0.7 + 0.3 * np.sin(2 * np.pi * (0.7 + 3 * u) * t)[:, None]
    return x * mod * (u ** 1.8 * amp)[:, None]

def whale_call(t0, dur, f0, f1, amp, seed=1):
    """distant baleen-whale-like moan: slow pitch glide, formant-ish harmonics, heavy lowpass + long reverb later"""
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    f = f0 * (f1 / f0) ** (np.sin(np.pi * u * 0.5) ** 1.3)
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 5.2 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(ph) + 0.45 * np.sin(2 * ph + 0.3) + 0.2 * np.sin(3 * ph + 1.1)
    sig = sosfilt(butter(2, 900, "low", fs=SR, output="sos"), sig)
    env = np.sin(np.pi * u) ** 1.5
    s_ = sig * env * amp
    r_ = np.random.default_rng(seed); pan = r_.uniform(0.25, 0.75)
    return np.stack([s_ * np.sqrt(1 - pan), s_ * np.sqrt(pan)], 1)


def ocean_noise(t0, t1, amp, seed=3):
    """deep underwater ambience: low rumbling filtered noise with slow surges"""
    n = int((t1 - t0) * SR); t = np.arange(n) / SR
    x = np.random.default_rng(seed).standard_normal((n, 2))
    lo = sosfilt(butter(2, [30, 220], "band", fs=SR, output="sos"), x, axis=0)
    hi = sosfilt(butter(2, [900, 3200], "band", fs=SR, output="sos"), x, axis=0) * 0.12
    mod = (0.7 + 0.3 * np.sin(2 * np.pi * t / 11.0))[:, None]
    return (lo + hi) * mod * amp


def bubbles(t0, t1, amp, rate=0.7, seed=9):
    """sparse soft bubble blips (diver's exhaust), every few seconds"""
    n = int((t1 - t0) * SR); out = np.zeros((n, 2)); r_ = np.random.default_rng(seed)
    tt = 0.0
    while tt < (t1 - t0) - 2:
        for k in range(r_.integers(3, 9)):
            s0 = int((tt + k * r_.uniform(0.03, 0.09)) * SR); L = int(0.05 * SR)
            if s0 + L >= n: break
            x = np.arange(L) / SR
            f = r_.uniform(500, 1400) * (1 + 3 * x)
            b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.012) * r_.uniform(0.3, 1)
            out[s0:s0 + L] += b[:, None] * np.array([0.8, 1.0]) * amp
        tt += r_.uniform(3.5, 6.0) / rate
    return out


def build_bed():
    """Calm, slightly ominous bed in D minor: low drone, slow pads, air, glassy pings (laser echoes / stars), sub swells at
    the reveals, soft clock ticks as the day lengthens, a restrained riser into totality, choir shimmer on the corona and the payoff."""
    bed = np.zeros((N, 2))
    D2 = 38
    dr = drone(0, DUR - 0.2, 0.11, D2)
    t = np.arange(len(dr)) / SR
    e = np.interp(t, [0, 4, 19, 24, 40, 60, 96, 113, 145, 161, 172, 189, 203, 211, 241, 261, 277, 284, 293, 297],
                     [0, 0.9, 1.1, 0.85, 0.9, 0.85, 0.9, 0.9, 1.2, 1.1, 0.85, 0.95, 1.25, 0.9, 1.1, 0.9, 1.0, 1.1, 0.6, 0])
    add(bed, 0, dr * e[:, None])
    chords = [  # (t0, t1, notes, amp, brightness)
        (0.5, 21, [50, 57, 62, 65], 0.028, 0.3),           # Dm (hook)
        (19, 26, [46, 53, 58, 62, 65], 0.032, 0.4),        # Bb (title)
        (24, 42, [43, 50, 58, 62], 0.024, 0.3),            # Gm (reflectors)
        (40, 62, [41, 48, 57, 60, 65], 0.026, 0.4),        # F (laser)
        (60, 76, [50, 57, 62, 64], 0.024, 0.3),            # Dm add9 (tides)
        (74, 97, [46, 53, 58, 62], 0.024, 0.3),            # Bb
        (96, 115, [45, 52, 57, 60, 64], 0.026, 0.4),       # Am (days)
        (113, 133, [43, 50, 55, 58, 62], 0.026, 0.35),     # Gm (run it backwards)
        (131, 147, [41, 48, 55, 60, 64], 0.026, 0.4),      # Fmaj7 (coral)
        (145, 163, [38, 45, 50, 53, 56], 0.030, 0.25),     # Dm b5 colour (impact)
        (161, 174, [46, 53, 60, 62, 65], 0.030, 0.45),     # Bbmaj9 (ancient moon)
        (172, 191, [43, 50, 58, 62], 0.024, 0.3),          # Gm (coincidence)
        (189, 204, [45, 52, 57, 61, 64], 0.028, 0.45),     # A (approach to totality)
        (202, 213, [38, 45, 50, 57, 62, 66], 0.036, 0.45), # D major (corona)
        (211, 224, [46, 53, 58, 62], 0.024, 0.3),          # Bb (annular)
        (222, 243, [43, 50, 55, 58, 62], 0.026, 0.35),     # Gm (future)
        (241, 263, [45, 52, 57, 60, 64], 0.028, 0.4),      # Am (far future)
        (261, 279, [41, 48, 57, 60, 65], 0.030, 0.45),     # F (window)
        (277, 286, [43, 50, 58, 62], 0.024, 0.3),          # Gm
        (284, 297.5, [38, 45, 50, 57, 62, 66], 0.036, 0.4),  # D major resolve
    ]
    for k, (a, b, notes, amp, br) in enumerate(chords):
        for j, m in enumerate(notes):
            add(bed, a, pad_note(m, a, b, amp * (1.0 if m < 60 else 0.75), a=4.0, r=5.0, bright=br, seed=k * 10 + j))
    for tc, amp in ((1.4, 0.16), (20.0, 0.26), (60.4, 0.18), (113.5, 0.16), (151.5, 0.30), (161.6, 0.22), (203.2, 0.30), (222.5, 0.16), (247.0, 0.20), (262.0, 0.18), (284.0, 0.26)):
        s0, sw = sub_swell(tc, amp, rise=5.0, fall=7.0, f=36.71); add(bed, max(0.0, s0), sw if s0 >= 0 else sw[int(-s0 * SR):])
    add(bed, 196.0, riser(196.0, 203.2, 0.030, f0=55, f1=220))
    add(bed, 0, air_noise(0, DUR - 0.5, 0.008))
    for (a, b, dens, amp) in ((24, 59, 0.45, 0.012), (161, 172, 0.5, 0.012), (203, 221, 0.5, 0.012), (277, 296, 0.5, 0.013)):
        add(bed, a, sparkles(a, b, [74, 77, 81, 84, 86, 89], dens, amp, seed=int(a)))
    for tt in (41.5, 44.2, 46.9, 49.6):                    # laser pulse out ... echo back 2.5 s later (soft pings)
        add(bed, tt, tick(0.05, f=2349.0, dec=0.12, seed=1)); add(bed, tt + 2.56, tick(0.022, f=2349.0, dec=0.25, seed=2))
    for k in range(12):                                    # slow clock under the lengthening day
        add(bed, 97.0 + k * 1.2, tick(0.022, f=1400.0, dec=0.03, seed=k))
    add(bed, 151.5, thud(0.16, f=40.0, dec=1.4))           # the giant impact (distant)
    add(bed, 202, choir(202, 212, [50, 57, 62, 66], 0.024, vowel=(350, 700, 2400), seed=8))
    add(bed, 261, choir(261, 277, [53, 60, 65], 0.018, vowel=(350, 700, 2400), seed=7))
    add(bed, 284, choir(284, 296.5, [50, 57, 62, 66], 0.024, vowel=(350, 700, 2400), seed=9))
    n_ir = int(4.5 * SR); tt = np.arange(n_ir) / SR
    ir = np.stack([sosfilt(butter(2, [90, 5000], "band", fs=SR, output="sos"),
                           np.random.default_rng(c + 40).standard_normal(n_ir)) for c in range(2)], axis=1)
    ir *= np.exp(-6.91 * tt / 4.0)[:, None]; ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    wet = np.stack([fftconvolve(bed[:, c], ir[:, c])[:N] for c in range(2)], axis=1)
    bed = 0.6 * bed + 0.6 * wet
    bed = sosfilt(butter(2, 26, "high", fs=SR, output="sos"), bed, axis=0)
    g = np.interp(np.arange(N) / SR, [0, 0.5, DUR - 2.5, DUR - 0.3, DUR], [0, 1, 1, 0, 0])
    return bed * g[:, None]

# ------------------------------------------------------------------------------------- ducking
def movavg(x, w):
    """Centred moving average via cumsum (O(N)), same length as x."""
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    h = w // 2
    i0 = np.clip(np.arange(len(x)) - h, 0, len(x)); i1 = np.clip(np.arange(len(x)) - h + w, 0, len(x))
    return (c[i1] - c[i0]) / w

def duck_gain(voice, depth_db=8.0):
    mono = np.abs(voice).mean(axis=1)
    # RMS envelope over 50 ms
    win = int(0.05 * SR)
    rms = np.sqrt(np.maximum(movavg(mono ** 2, win), 0))
    active = (rms > 0.01 * rms.max()).astype(float)
    # hold over short intra-sentence pauses (0.35 s), then smooth: fast-ish attack, slow release
    hold = int(0.35 * SR)
    active = movavg(active, hold) > 0
    g_db = -depth_db * active.astype(float)
    # look-ahead / smoothing: zero-phase low-pass (~1.2 Hz) => ~150 ms attack before speech, ~400 ms release
    sos = butter(1, 1.2, "low", fs=SR, output="sos")
    g_db = sosfiltfilt(sos, g_db)
    return 10 ** (g_db / 20)


# ----------------------------------------------------------------------------------------- SRT
def fmt_ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text, width=44):
    if len(text) <= width:
        return text
    words = text.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a, b)
    return best[1] + "\n" + best[2]


def split_cue(text):
    """Very long lines become two cues split at a strong punctuation mark."""
    if len(text) <= 90:
        return [text]
    for sep in ("; ", ": ", " — ", ". "):
        if sep in text:
            a, b = text.split(sep, 1)
            a = a + sep.rstrip()
            return [a.strip(), b.strip()]
    return [text]


def write_srt(placement, path):
    cues = []
    for i, l in enumerate(placement):
        nxt = placement[i + 1]["start"] if i + 1 < len(placement) else DUR
        end = min(l["end"] + 0.5, nxt - 0.12)
        parts = split_cue(l["text"])
        if len(parts) == 1:
            cues.append((l["start"], end, parts[0]))
        else:
            tot = sum(len(p) for p in parts)
            t = l["start"]
            for p in parts:
                d = (l["end"] - l["start"]) * len(p) / tot
                e = t + d if p is not parts[-1] else end
                cues.append((t, e, p))
                t = e
    with open(path, "w", encoding="utf-8") as f:
        for k, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{k}\n{fmt_ts(a)} --> {fmt_ts(b)}\n{wrap(txt)}\n\n")
    return cues



def main():
    meta, placement = place_lines()
    json.dump(dict(voice=meta["voice"], speed=meta["speed"], lines=placement), open(os.path.join(HERE, "placement.json"), "w"), indent=1)
    if "--reuse" in sys.argv and os.path.exists(P("voice_48k.wav")) and os.path.exists(P("bed_48k.wav")):
        voice, _ = sf.read(P("voice_48k.wav")); bed, _ = sf.read(P("bed_48k.wav"))
    else:
        voice = build_voice(placement)
        sf.write(P("voice_48k.wav"), voice.astype(np.float32), SR, subtype="FLOAT")
        bed = build_bed()
        sf.write(P("bed_48k.wav"), bed.astype(np.float32), SR, subtype="FLOAT")
    g = duck_gain(voice, depth_db=7.0)
    voice_n = voice / np.abs(voice).max() * 0.5
    bed_n = bed / (np.abs(bed).max() + 1e-9) * 0.30
    mix = voice_n + bed_n * g[:, None]
    mix = mix / np.abs(mix).max() * 0.7
    sf.write(P("mix_premaster.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", P("mix_premaster.wav"), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:"
          f"linear=true:print_format=summary,aresample=48000,alimiter=limit=0.84:attack=5:release=80:level=false")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", P("mix_premaster.wav"), "-af", af,
                    "-t", str(DUR), "-ar", "48000", "-c:a", "pcm_s24le", P("mix_moon.wav")], check=True)
    cues = write_srt(placement, os.path.join(os.path.dirname(HERE), "the-moon-is-leaving.srt"))
    print("SRT cues:", len(cues))

if __name__ == "__main__":
    main()
