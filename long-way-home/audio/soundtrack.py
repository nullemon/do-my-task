# Original score + sound design for Episode 1, synthesized from scratch (no samples, no licensing).
# Writes out/music.wav, out/sfx.wav, out/mix.wav (48 kHz stereo float -> 24-bit via ffmpeg later).
import numpy as np, wave, os, sys

SR = 48000
DUR = 60.0
N = int(SR * DUR)
rs = np.random.RandomState(7)
OUT = os.path.join(os.path.dirname(__file__), '..', 'out')

def bus():
    return np.zeros((2, N))
MUS, SFX, AMB = bus(), bus(), bus()

def add(b, t0, sig, pan=0.0, gain=1.0):
    """Mix mono or stereo sig into bus b at time t0 (s). pan -1..1 (equal power)."""
    i0 = int(round(t0 * SR))
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4
        sig = np.vstack([sig * np.cos(a), sig * np.sin(a)]) * np.sqrt(2)
    n = sig.shape[1]
    s0, s1 = max(0, i0), min(N, i0 + n)
    if s1 <= s0: return
    b[:, s0:s1] += gain * sig[:, s0 - i0:s1 - i0]

def tt(n): return np.arange(n) / SR
def env_ad(n, a, d):  # attack / exp decay (seconds)
    t = tt(n); return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
def fades(x, fi=0.01, fo=0.05):
    n = x.shape[-1]; e = np.ones(n)
    a, b = min(n, int(fi * SR)), min(n, int(fo * SR))
    if a: e[:a] = np.linspace(0, 1, a)
    if b: e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b))
    return x * e

def fft_filter(x, lo=None, hi=None, tilt=0.0, peak=None):
    """Zero-phase spectral filter: smooth highpass lo, lowpass hi (Hz), tilt dB/oct, optional peak=(f,gain_db,Q)."""
    n = x.shape[-1]
    X = np.fft.rfft(x, axis=-1)
    f = np.fft.rfftfreq(n, 1 / SR); f[0] = 1e-3
    g = np.ones_like(f)
    if lo: g *= 1 / np.sqrt(1 + (lo / f) ** 4)
    if hi: g *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if tilt: g *= (f / 1000.0) ** (tilt / 6.02)
    if peak:
        pf, pg, q = peak
        g *= 1 + (10 ** (pg / 20) - 1) * np.exp(-0.5 * (np.log2(f / pf) * q) ** 2)
    return np.fft.irfft(X * g, n=n, axis=-1)

def noise(n, ch=1):
    return rs.randn(ch, n) if ch > 1 else rs.randn(n)

def midi(name):
    names = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    k = names[name[0]]; i = 1
    if name[1] in '#b': k += 1 if name[1] == '#' else -1; i = 2
    return 12 * (int(name[i:]) + 1) + k
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

# ---------------------------------------------------------------- instruments
def piano(name, dur, vel=0.6):
    f = hz(midi(name)) if isinstance(name, str) else name
    ring = min(dur + 1.8, 7.0)
    n = int(ring * SR); t = tt(n)
    T0 = np.clip(3.2 * (261.6 / f) ** 0.5, 0.7, 8.0)
    out = np.zeros(n)
    B = 0.0003
    for k in range(1, 16):
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > 15000: break
        amp = vel ** (0.3 + 0.18 * k) / k ** 1.2
        tk = T0 / (1 + 0.45 * (k - 1))
        e = 0.65 * np.exp(-t / (tk * 0.22)) + 0.35 * np.exp(-t / tk)
        out += amp * e * np.sin(2 * np.pi * fk * t + rs.rand() * 6.28)
        # slight detuned string pair for chorus shimmer
        if k <= 4: out += 0.35 * amp * e * np.sin(2 * np.pi * fk * 1.0009 * t + rs.rand() * 6.28)
    out *= np.minimum(1, t / 0.004)
    out *= np.where(t < dur, 1, np.exp(-(t - dur) / 0.35))
    h = int(0.03 * SR)
    hn = fft_filter(rs.randn(h), lo=800, hi=6000) * np.exp(-tt(h) / 0.006) * 0.08 * vel
    out[:h] += hn
    return fades(out * 0.25, 0.001, 0.05)

def musicbox(name, vel=0.6):
    f = hz(midi(name))
    n = int(2.2 * SR); t = tt(n)
    parts = [(1, 1.0, 1.4), (2.0, 0.25, 0.6), (3.95, 0.13, 0.35), (5.4, 0.07, 0.2), (8.9, 0.04, 0.1)]
    out = sum(a * np.exp(-t / d) * np.sin(2 * np.pi * f * r * t) for r, a, d in parts)
    out *= np.minimum(1, t / 0.0015)
    return fades(out * 0.18 * vel, 0.0005, 0.1)

def pad(names, dur, gain=0.5, att=1.2, rel=1.6, bright=1800):
    n = int((dur + rel) * SR); t = tt(n)
    env = np.minimum(1, t / att) * np.where(t < dur, 1, np.exp(-(t - dur) / (rel / 3)))
    out = np.zeros((2, n))
    for name in names:
        f0 = hz(midi(name))
        for v, (det, pan) in enumerate([(-0.004, -0.6), (0.0, 0.0), (0.0045, 0.6)]):
            vib = 1 + 0.0018 * np.sin(2 * np.pi * (4.8 + v * 0.3) * t + v)
            ph = 2 * np.pi * np.cumsum(f0 * (1 + det) * vib) / SR
            s = np.zeros(n)
            for k in range(1, 18):
                if f0 * k > 9000: break
                s += np.sin(k * ph) / k * np.exp(-k * f0 / bright)
            a = (pan + 1) * np.pi / 4
            out[0] += s * np.cos(a); out[1] += s * np.sin(a)
    return out * env * gain * 0.06 / max(1, len(names) ** 0.5)

# ---------------------------------------------------------------- reverb
def make_ir(T60, pre=0.02, damp=5000, er=True):
    n = int(T60 * SR); t = tt(n)
    env = 10 ** (-3 * t / T60)
    ir = rs.randn(2, n) * env
    ir = fft_filter(ir, lo=120, hi=damp)
    late = np.concatenate([np.zeros((2, int(pre * SR))), ir], axis=1)
    if er:
        for d, g in [(0.011, 0.5), (0.019, 0.4), (0.027, 0.33), (0.041, 0.25), (0.053, 0.2)]:
            i = int(d * SR); late[0, i] += g * rs.choice([-1, 1]); late[1, i + 37] += g * rs.choice([-1, 1])
    return late / np.sqrt((late ** 2).sum() / 2)

def convolve(x, ir, wet):
    n = x.shape[1] + ir.shape[1]
    nf = 1 << (n - 1).bit_length()
    y = np.zeros_like(x)
    for c in range(2):
        Y = np.fft.irfft(np.fft.rfft(x[c], nf) * np.fft.rfft(ir[c], nf), nf)[:x.shape[1]]
        y[c] = Y
    return x * (1 - wet * 0.5) + y * wet

# ---------------------------------------------------------------- music
BEAT = 60 / 70.0

def arp(chord, t0, beats, vel=0.42, pattern=(0, 1, 2, 3, 4, 3, 2, 1), step=0.5, hold=1.6):
    k = 0; t = 0.0
    while t < beats - 1e-6:
        note = chord[pattern[k % len(pattern)]]
        add(MUS, t0 + t * BEAT, piano(note, hold, vel * (0.85 + 0.15 * (k % 4 == 0))), pan=-0.35 + 0.7 * pattern[k % len(pattern)] / 4)
        k += 1; t += step

def melody(notes, t0, vel=0.62, inst='piano', octave=0):
    t = 0.0
    for name, b in notes:
        if name:
            nm = name[:-1] + str(int(name[-1]) + octave)
            if inst == 'piano': add(MUS, t0 + t * BEAT, piano(nm, b * BEAT + 0.25, vel), pan=0.1)
            else: add(MUS, t0 + t * BEAT, musicbox(nm, vel), pan=0.15)
        t += b

CH = {  # chord tones low->high (for arpeggios)
    'Am': ['A2', 'E3', 'A3', 'C4', 'E4'], 'F': ['F2', 'C3', 'F3', 'A3', 'C4'], 'C': ['C3', 'G3', 'C4', 'E4', 'G4'],
    'G': ['G2', 'D3', 'G3', 'B3', 'D4'], 'Dm': ['D3', 'A3', 'D4', 'F4', 'A4'], 'E': ['E2', 'B2', 'E3', 'G#3', 'B3'],
    'Em': ['E2', 'B2', 'E3', 'G3', 'B3'],
}
M1 = [('E5', 1), ('D5', 0.5), ('C5', 0.5), ('A4', 2)]
M2 = [('C5', 1), ('D5', 0.5), ('E5', 0.5), ('G5', 1), ('E5', 1)]
M3 = [('D5', 1), ('C5', 0.5), ('A4', 0.5), ('G4', 2)]

def compose():
    # 0-3: the hook. low drone, two lonely notes
    add(MUS, 0.0, pad(['A1', 'E2', 'A2'], 3.0, gain=0.9, att=0.4, rel=1.0, bright=700))
    add(MUS, 0.35, piano('A5', 2.0, 0.45), pan=0.2)
    add(MUS, 1.55, piano('E5', 1.6, 0.38), pan=-0.1)
    # 3-9: flashback. music box over warm piano
    for i, ch in enumerate(['Am', 'F', 'C', 'G']):
        arp(CH[ch], 3.0 + i * 2 * BEAT, 2, vel=0.30)
    melody(M1 + M2, 3.0, vel=0.9, inst='box', octave=1)
    add(MUS, 3.0, pad(['A3', 'C4', 'E4'], 5.6, gain=0.35, att=1.5, bright=1500))
    # 9-16: kitchen. sparse, low, sad
    for t0, ch, d in [(9.0, ['D2', 'A2', 'F3', 'A3'], 2.0), (11.0, ['C2', 'A2', 'E3', 'A3'], 1.4), (12.4, ['F1', 'F2', 'C3', 'A3'], 1.6), (14.0, ['E1', 'E2', 'B2', 'G#3'], 1.4)]:
        for k, nm in enumerate(ch): add(MUS, t0 + k * 0.06, piano(nm, d, 0.42), pan=-0.2 + k * 0.12)
    add(MUS, 9.0, pad(['D3', 'F3', 'A3'], 3.2, gain=0.4, att=1.4, bright=900))
    add(MUS, 12.4, pad(['F2', 'C3', 'A3'], 1.5, gain=0.4, att=1.0, bright=900))
    add(MUS, 14.0, pad(['E2', 'B2', 'G#3'], 1.8, gain=0.5, att=0.8, bright=1000))
    add(MUS, 15.4, piano('A4', 1.0, 0.35))
    # 16-23: the drive. bittersweet theme
    for i, ch in enumerate(['F', 'C', 'G', 'Am']):
        arp(CH[ch], 16.0 + i * 2 * BEAT, 2, vel=0.38)
    melody(M2 + M3, 16.0, vel=0.6)
    add(MUS, 22.86, piano('A2', 0.8, 0.3), pan=-0.3); add(MUS, 22.86, piano('C5', 0.5, 0.28), pan=0.2)
    add(MUS, 16.0, pad(['F3', 'A3', 'C4'], 6.4, gain=0.45, att=2.0, bright=1600))
    # the throw: one last note, then silence
    add(MUS, 23.22, piano('E6', 0.6, 0.3), pan=0.4)
    # 29-36: dread drone, then the ball phrase
    add(MUS, 29.0, pad(['A1', 'E2'], 6.0, gain=0.9, att=2.5, rel=2.0, bright=500))
    melody([('E5', 0.7), ('D5', 0.5), ('C5', 0.6), ('A4', 2.5)], 33.9, vel=0.5)
    add(MUS, 33.9, piano('A2', 2.6, 0.35), pan=-0.3)
    # 36-43: all night. slow chords, rising
    for i, (ch, low) in enumerate([(['A3', 'C4', 'E4'], 'A1'), (['F3', 'A3', 'C4'], 'F1'), (['D3', 'F3', 'A3'], 'D2'), (['E3', 'G#3', 'B3'], 'E1')]):
        t0 = 36.0 + i * 1.4
        add(MUS, t0, pad(ch + [low], 1.6 if i < 3 else 2.4, gain=0.55 + i * 0.12, att=0.6, rel=1.2, bright=1200 + i * 200))
        add(MUS, t0, piano(low[:-1] + str(int(low[-1]) + 1), 1.4, 0.5), pan=-0.2)
    for i, nm in enumerate(['A4', 'C5', 'D5', 'E5']):
        add(MUS, 36.7 + i * 1.4, piano(nm, 1.2, 0.36), pan=0.2)
    # 43-52: home. tender, then hope when the light comes on
    add(MUS, 43.0, pad(['A2', 'E3', 'C4'], 3.0, gain=0.4, att=1.6, bright=1100))
    melody(M1, 43.7, vel=0.42)
    for t0, ch in [(43.0, 'Am'), (45.5, 'F'), (46.4, 'C'), (48.6, 'G')]:
        arp(CH[ch], t0, 2 if t0 != 46.4 else 2.5, vel=0.26)
    melody(M2, 46.4, vel=0.5)
    add(MUS, 46.4, pad(['C3', 'G3', 'E4'], 4.0, gain=0.45, att=1.5, bright=1500))
    add(MUS, 50.6, pad(['F3', 'A3', 'C4', 'G4'], 2.2, gain=0.6, att=0.3, rel=1.5, bright=2200))
    for i, nm in enumerate(['C6', 'G5', 'A5', 'E6']):
        add(MUS, 50.6 + i * 0.14, musicbox(nm, 0.7), pan=-0.4 + i * 0.25)
    # 52-60: dawn. full theme, swell to the title, end suspended
    for i, ch in enumerate(['F', 'C', 'G', 'Am']):
        arp(CH[ch], 52.0 + i * 2 * BEAT, 2, vel=0.4 + i * 0.03)
    melody(M2 + M3, 52.0, vel=0.62)
    add(MUS, 52.0, pad(['F3', 'A3', 'C4'], 3.4, gain=0.5, att=2.0, bright=1600))
    add(MUS, 55.4, pad(['G3', 'B3', 'D4'], 1.8, gain=0.6, att=1.0, bright=1800))
    add(MUS, 57.0, pad(['C3', 'G3', 'C4', 'E4', 'G4'], 2.4, gain=0.9, att=0.25, rel=1.6, bright=2600))
    for k, nm in enumerate(['C2', 'C3', 'G3', 'E4', 'C5', 'G5']):
        add(MUS, 57.0 + k * 0.05, piano(nm, 2.6, 0.62), pan=-0.4 + k * 0.16)
    add(MUS, 58.0, piano('E6', 1.9, 0.42), pan=0.3)
    add(MUS, 58.0, musicbox('E6', 0.6), pan=-0.3)
    add(MUS, 58.55, piano('D6', 1.4, 0.3), pan=0.25)

# ---------------------------------------------------------------- sound effects
def rain_bed(intensity_fn, gain=1.0):
    """Stereo rain: shaped noise + droplets, intensity_fn(t) -> 0..1 over the whole film."""
    nz = rs.randn(2, N)
    hiss = fft_filter(nz, lo=400, hi=9000, tilt=-1.5, peak=(3500, 3, 1.0))
    body = fft_filter(rs.randn(2, N), lo=80, hi=700) * 0.5
    t = tt(N)
    I = intensity_fn(t)
    bed = (hiss * 0.06 + body * 0.05) * I
    # droplets
    drops = np.zeros((2, N))
    nd = int(220 * DUR)
    times = rs.rand(nd) * DUR
    for tm in times:
        i = int(tm * SR)
        if i >= N - 2000: continue
        if rs.rand() > intensity_fn(np.array([tm]))[0]: continue
        f = 1800 + rs.rand() * 6000
        n = int(0.012 * SR)
        d = np.sin(2 * np.pi * f * tt(n) * (1 - tt(n) * 8)) * np.exp(-tt(n) / 0.0025)
        c = rs.randint(2)
        drops[c, i:i + n] += d * (0.02 + rs.rand() * 0.04)
    return (bed + drops) * gain

def thunder(t0, big=1.0, crack=True):
    n = int(5.0 * SR); t = tt(n)
    w = rs.randn(2, n)
    brown = np.cumsum(w, axis=1); brown -= brown.mean(axis=1, keepdims=True)
    rumble = fft_filter(brown, lo=25, hi=160)
    rumble /= np.abs(rumble).max() + 1e-9
    mod = 0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 0.7 * t + 1)) * (0.5 + 0.5 * np.sin(2 * np.pi * 1.9 * t))
    env = np.minimum(1, t / 0.08) * np.exp(-t / 1.6) * mod
    out = rumble * env * 0.55 * big
    if crack:
        m = int(0.35 * SR)
        cr = fft_filter(rs.randn(2, m), lo=300, hi=7000) * np.exp(-tt(m) / 0.06)
        cr /= np.abs(cr).max()
        out[:, :m] += cr * 0.45 * big
    add(SFX, t0, fades(out, 0.002, 0.5))

def buzz(t0, dur, f=120, amp=0.01, flick=None):
    n = int(dur * SR); t = tt(n)
    s = sum(np.sin(2 * np.pi * f * k * t) / k ** 0.8 for k in range(1, 9))
    if flick is not None: s *= flick(t + t0)
    add(AMB, t0, fades(s * amp, 0.05, 0.08))

def click(t0, f=2500, dec=0.004, amp=0.15, pan=0.0, low=0.0):
    n = int(0.08 * SR); t = tt(n)
    s = fft_filter(rs.randn(n), lo=f * 0.5, hi=f * 2) * np.exp(-t / dec)
    if low: s += low * np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.03)
    add(SFX, t0, fades(s * amp / (np.abs(s).max() + 1e-9), 0.0005, 0.01), pan)

def thump(t0, f=70, dec=0.12, amp=0.5, pan=0.0):
    n = int(0.5 * SR); t = tt(n)
    s = np.sin(2 * np.pi * f * t * (1 - 0.3 * t)) * np.exp(-t / dec)
    s += fft_filter(rs.randn(n), lo=200, hi=2500) * np.exp(-t / 0.012) * 0.25
    add(SFX, t0, fades(s * amp, 0.001, 0.05), pan)

def whoosh(t0, dur, f0=500, f1=2500, amp=0.15, pan0=0.0, pan1=0.0):
    n = int(dur * SR); t = tt(n)
    base = rs.randn(n)
    lo = fft_filter(base, lo=f0 * 0.5, hi=f0 * 1.5); hi = fft_filter(base, lo=f1 * 0.5, hi=f1 * 1.5)
    k = t / dur
    env = np.sin(np.pi * k) ** 2
    s = (lo * (1 - k) + hi * k) * env
    s /= np.abs(s).max() + 1e-9
    a = ((pan0 + (pan1 - pan0) * k) + 1) * np.pi / 4
    st = np.vstack([s * np.cos(a), s * np.sin(a)]) * np.sqrt(2) * amp
    add(SFX, t0, st)

def chirp_bird(t0, amp=0.03, pan=0.0):
    k = rs.randint(3, 7); f0 = 2800 + rs.rand() * 2200
    for j in range(k):
        n = int((0.04 + rs.rand() * 0.05) * SR); t = tt(n)
        fs = f0 * (1 + 0.35 * np.sin(np.pi * t / t[-1]) * (1 if j % 2 else -0.6))
        ph = 2 * np.pi * np.cumsum(fs) / SR
        s = np.sin(ph) * np.sin(np.pi * t / t[-1]) ** 2
        add(AMB, t0 + j * (0.07 + rs.rand() * 0.04), s * amp, pan)

def crickets(t0, t1, amp=0.006):
    for c in range(4):
        f = 4200 + c * 330; rate = 0.75 + c * 0.13; pan = -0.7 + c * 0.45
        t = t0 + rs.rand() * rate
        while t < t1:
            for p in range(3):
                n = int(0.018 * SR); tt_ = tt(n)
                s = np.sin(2 * np.pi * f * tt_) * np.sin(np.pi * tt_ / tt_[-1])
                add(AMB, t + p * 0.032, s * amp, pan)
            t += rate * (0.9 + rs.rand() * 0.2)

def jingle(t0, amp=0.02, pan=0.0):
    f = 2300 + rs.rand() * 1400
    n = int(0.3 * SR); t = tt(n)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in [(1, 1, 0.12), (2.76, 0.5, 0.06), (5.4, 0.25, 0.03)])
    add(SFX, t0, fades(s * amp, 0.0005, 0.05), pan)

def paw(t0, amp=0.02, pan=0.0, bright=2500):
    n = int(0.05 * SR); t = tt(n)
    s = fft_filter(rs.randn(n), lo=300, hi=bright) * np.exp(-t / 0.008)
    add(SFX, t0, s * amp / (np.abs(s).max() + 1e-9), pan)

def step(t0, amp=0.06, pan=0.0):  # shoe on gravel
    n = int(0.16 * SR); t = tt(n)
    g = rs.randn(n) * (rs.rand(n) > 0.82)
    s = fft_filter(g, lo=700, hi=5000) * np.exp(-t / 0.04)
    s += fft_filter(rs.randn(n), lo=60, hi=300) * np.exp(-t / 0.02) * 0.6
    add(SFX, t0, s * amp / (np.abs(s).max() + 1e-9), pan)

def engine(t0, dur, rpm_fn, amp_fn, pan_fn, lp_fn=None):
    n = int(dur * SR); t = tt(n)
    f = rpm_fn(t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = sum(np.sin(k * ph + k) / k for k in range(1, 9))
    s += fft_filter(rs.randn(n), lo=40, hi=400) * 0.5
    s *= 1 + 0.25 * np.sin(ph * 0.5)
    dark = fft_filter(s, hi=250)
    if lp_fn is not None:
        k = lp_fn(t); s = s * (1 - k) + dark * k
    s *= amp_fn(t)
    p = pan_fn(t); a = (p + 1) * np.pi / 4
    add(SFX, t0, fades(np.vstack([s * np.cos(a), s * np.sin(a)]) * np.sqrt(2), 0.05, 0.3))

def sfx():
    t = tt(N)
    def rain_I(x):
        x = np.asarray(x, float)
        r = np.zeros_like(x)
        r += 0.85 * (x < 3.0) * np.clip((3.15 - x) / 0.3, 0, 1)
        r += 0.22 * ((x >= 8.8) & (x < 16.2)) * np.clip((x - 8.8) / 0.6, 0, 1) * np.clip((16.3 - x) / 0.4, 0, 1)
        r += np.where((x >= 36.0) & (x < 43.3), np.clip((x - 37.4) / 2.6, 0, 1) * 0.95, 0)
        r += np.where((x >= 42.8) & (x < 52.4), np.clip((x - 42.8) / 0.4, 0, 1) * 0.9 * np.clip((52.4 - x) / 0.8, 0, 1), 0)
        return r
    add(AMB, 0, rain_bed(rain_I, 1.5))
    # S1: neon buzz, departing car, distant thunder
    buzz(0, 3.1, amp=0.012, flick=lambda x: 0.6 + 0.4 * np.sin(x * 37) * np.sin(x * 11))
    engine(0, 3.2, lambda x: 38 + 6 * x, lambda x: 0.10 * np.exp(-x / 1.2), lambda x: 0.1 - 0.05 * x, lambda x: np.clip(x / 2, 0, 1))
    thunder(1.1, 0.45, crack=False)
    # flash into the flashback
    whoosh(2.5, 0.75, 800, 6000, 0.08)
    n = int(1.8 * SR); add(SFX, 2.95, fades(sum(np.sin(2 * np.pi * f * tt(n)) * np.exp(-tt(n) / 0.9) for f in [1568, 2093, 2637]) * 0.02, 0.01, 0.2))
    # S2: nursery room tone, morning street
    add(AMB, 3.0, fades(fft_filter(rs.randn(2, int(3.4 * SR)), lo=100, hi=900) * 0.006, 0.3, 0.4))
    for k in range(9): chirp_bird(6.3 + k * 0.33 + rs.rand() * 0.2, 0.018 + rs.rand() * 0.012, -0.8 + rs.rand() * 1.6)
    engine(6.6, 2.6, lambda x: 28 + 0 * x, lambda x: 0.035 * np.minimum(1, x / 0.8), lambda x: 0.6 + 0 * x, lambda x: 0.7 + 0 * x)
    for k in range(int(2.8 * 1.9 * 2)): paw(6.3 + k / (1.9 * 4) * 2, 0.008, 0.2, 1800)
    # S3: kitchen
    add(AMB, 9.0, fades(sum(np.sin(2 * np.pi * f * tt(int(7.2 * SR))) / i for i, f in enumerate([60, 120, 180], 1)) * 0.004, 0.6, 0.4))
    for k in range(7): click(9.25 + k, f=3000 if k % 2 else 2200, dec=0.003, amp=0.09, pan=-0.5)
    n = int(1.1 * SR); br = fft_filter(rs.randn(n), lo=250, hi=1600) * np.sin(np.pi * tt(n) / tt(n)[-1]) ** 2
    add(SFX, 10.5, br * 0.035, 0.1)
    whoosh(12.3, 0.45, 1800, 5000, 0.05, 0.3, -0.1)
    for k in range(18): paw(13.1 + k * 0.05 + rs.rand() * 0.01, 0.015, 0.0, 6000)
    # S4: the drive
    add(AMB, 16.0, fades(fft_filter(rs.randn(2, int(6.3 * SR)), lo=40, hi=500) * 0.05 + fft_filter(rs.randn(2, int(6.3 * SR)), lo=800, hi=4000) * 0.012, 0.35, 0.3))
    engine(16.0, 6.3, lambda x: 46 + 2 * np.sin(x), lambda x: 0.05 + 0 * x, lambda x: 0 * x, lambda x: 0.6 + 0 * x)
    for tp in [16.94, 18.26, 19.58, 20.9]: whoosh(tp - 0.2, 0.4, 300, 1500, 0.05, 0.6, -0.6)
    for k in range(40):  # happy panting
        tp = 16.3 + k * 0.14; n = int(0.08 * SR)
        add(SFX, tp, fft_filter(rs.randn(n), lo=600, hi=3000) * np.sin(np.pi * tt(n) / tt(n)[-1]) * 0.012, -0.3)
    # S5a: dusk, the throw
    crickets(22.0, 37.5, 0.005)
    buzz(22.0, 4.2, f=120, amp=0.003)
    for k in range(10): jingle(22.05 + k * 0.11, 0.012, -0.1)
    whoosh(23.12, 0.35, 900, 3000, 0.09, 0.0, 0.5)
    for k in range(10): paw(23.35 + k * 0.17, 0.02 * (1 - k / 12), 0.2 + k * 0.05); jingle(23.35 + k * 0.34, 0.01 * (1 - k / 10), 0.3)
    add(SFX, 24.0, fades(fft_filter(rs.randn(2, int(1.5 * SR)), lo=1500, hi=7000) * 0.012, 0.2, 0.6))
    for k in range(3): step(25.25 + k * 0.56, 0.05, -0.2 - k * 0.1)
    # S5b: the car leaves
    thump(26.5, 75, 0.1, 0.55, -0.2); click(26.52, 2000, 0.006, 0.12, -0.2)
    engine(26.95, 0.55, lambda x: 9 + 6 * np.sin(x * 40) ** 2, lambda x: 0.12 + 0 * x, lambda x: -0.2 + 0 * x)
    engine(27.4, 3.0, lambda x: np.where(x < 0.2, 30, 30 + 22 * np.clip((x - 0.2) / 1.2, 0, 1)), lambda x: 0.13 * np.where(x < 1.0, 1, np.exp(-(x - 1.0) / 0.8)), lambda x: -0.2 - 0.6 * np.clip(x / 2.2, 0, 1), lambda x: np.clip((x - 0.6) / 1.6, 0, 1))
    add(SFX, 27.6, fades(fft_filter(rs.randn(int(1.4 * SR)) * (rs.rand(int(1.4 * SR)) > 0.7), lo=500, hi=4000) * 0.03, 0.05, 0.5), -0.4)
    jingle(28.8, 0.004, 0.5); jingle(28.95, 0.003, 0.5)
    # S6: back with the ball
    buzz(30.0, 6.0, f=120, amp=0.004)
    for k in range(20):
        if 30.2 + k * 0.11 > 32.4: break
        paw(30.2 + k * 0.11, 0.025 + k * 0.001, 0.4 - k * 0.02); jingle(30.2 + k * 0.22, 0.016 + k * 0.0008, 0.35)
    jingle(33.02, 0.016, 0.0); jingle(33.1, 0.012, 0.1); jingle(33.36, 0.014, -0.1)
    for tb, a in [(33.97, 0.35), (34.23, 0.22), (34.39, 0.12)]:
        n = int(0.15 * SR); tq = tt(n)
        s = np.sin(2 * np.pi * 420 * tq * (1 - 0.6 * tq)) * np.exp(-tq / 0.025) + fft_filter(rs.randn(n), lo=600, hi=3000) * np.exp(-tq / 0.006) * 0.4
        add(SFX, tb, s * a * 1.0, 0.1)
    n = int(1.0 * SR); roll = fft_filter(rs.randn(n), lo=200, hi=1200) * np.exp(-tt(n) / 0.35) * (1 + 0.5 * np.sin(2 * np.pi * 9 * tt(n)))
    add(SFX, 34.45, fades(roll * 0.03, 0.02, 0.2), 0.25)
    # S7: the long night
    for k in range(9):
        tp = 36.2 + k * 0.55 + rs.rand() * 0.2
        whoosh(tp, 0.7, 250, 1400, 0.06 * (1 - k / 11), rs.choice([-0.8, 0.8]), rs.choice([-0.8, 0.8]))
    thump(39.4, 55, 0.08, 0.25, -0.5); click(39.42, 1500, 0.01, 0.08, -0.5)
    buzz(36.0, 3.4, f=120, amp=0.004)
    thump(40.2, 60, 0.07, 0.18, -0.4)
    buzz(40.85, 0.42, f=120, amp=0.012, flick=lambda x: (np.sin(x * 140) > 0).astype(float))
    click(41.25, 1800, 0.01, 0.1, -0.6)
    thunder(41.55, 1.4, crack=True)
    add(AMB, 38.0, fades(fft_filter(rs.randn(2, int(5.5 * SR)), lo=60, hi=500) * 0.03, 1.5, 0.6))
    # S8: home in the rain
    for k in range(int(9 * 3)):
        tp = 43.1 + k * 0.33 + rs.rand() * 0.1
        n = int(0.05 * SR); s = np.sin(2 * np.pi * (900 + rs.rand() * 500) * tt(n)) * np.exp(-tt(n) / 0.012)
        add(SFX, tp, s * 0.01, -0.5)
    thunder(44.6, 0.5, crack=False)
    click(50.55, 2600, 0.003, 0.25, 0.25, low=0.3)
    buzz(50.55, 0.4, f=120, amp=0.01, flick=lambda x: (np.sin(x * 90) > 0).astype(float))
    buzz(50.95, 1.6, f=120, amp=0.0025)
    # S10: dawn
    add(AMB, 51.6, fades(fft_filter(rs.randn(2, int(8.4 * SR)), lo=100, hi=1200) * 0.012, 1.0, 1.0))
    for k in range(16): chirp_bird(52.2 + k * 0.48 + rs.rand() * 0.3, 0.02 + rs.rand() * 0.012, -0.9 + rs.rand() * 1.8)
    jingle(52.8, 0.012, 0.0); jingle(53.1, 0.01, 0.05); jingle(53.85, 0.016, 0.1)
    for k in range(20):
        tp = 54.35 + k * 0.28
        paw(tp, 0.012 * np.exp(-k / 8), 0.0, 1800)
        if k % 2 == 0: jingle(tp, 0.009 * np.exp(-k / 7), 0.0)

compose()
sfx()

# ---------------------------------------------------------------- mix
mus = convolve(MUS, make_ir(3.2, 0.03, 4500), 0.55)
fx = convolve(SFX, make_ir(1.4, 0.01, 6000), 0.25)
amb = AMB

def norm_peak(x, p=0.9):
    m = np.abs(x).max(); return x * (p / m) if m > 0 else x

def master(x):
    x = fft_filter(x, lo=38)                 # nothing a phone can play lives down here
    x = x - 0.45 * fft_filter(x, hi=140)     # ~-5 dB low shelf: clears mud, piano reads clearer
    x = np.tanh(x * 1.2) / 1.2
    return x

music_mix = master(mus * 1.0)
sfx_mix = master(fx + amb)
full = master(mus * 0.72 + fx + amb)

def write(path, x):
    x = np.clip(x, -1, 1)
    y = (x.T * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
    print(path, 'peak', np.abs(x).max().round(3), 'rms', np.sqrt((x ** 2).mean()).round(4))

os.makedirs(OUT, exist_ok=True)
write(os.path.join(OUT, 'mix.wav'), full)
write(os.path.join(OUT, 'sfx_only.wav'), sfx_mix)
write(os.path.join(OUT, 'music_only.wav'), music_mix)
