# python lib/music.py <seconds> <out.wav>
# Gentle, warm piano + pad, original composition, generated from scratch (no samples).
import numpy as np, soundfile as sf, sys
SR = 44100
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 300
OUT = sys.argv[2] if len(sys.argv) > 2 else "music.wav"
bpm = 68; beat = 60 / bpm; bar = 4 * beat
rng = np.random.default_rng(7)
N = int((dur + 4) * SR)
L = np.zeros(N); R = np.zeros(N)
def midi(m): return 440 * 2 ** ((m - 69) / 12)
def piano(f, length, vel):
    n = int(length * SR); t = np.arange(n) / SR
    env = np.exp(-t * (2.2 + f / 900)) * (1 - np.exp(-t * 400))
    sig = sum(a * np.sin(2 * np.pi * f * h * t * (1 + 0.0004 * h * h)) for h, a in [(1, 1), (2, .45), (3, .18), (4, .1), (5, .05)])
    return vel * env * sig
def pad(freqs, length):
    n = int(length * SR); t = np.arange(n) / SR
    env = np.minimum(1, t / 1.8) * np.minimum(1, (length - t) / 1.8)
    s = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.12):
            s += np.sin(2 * np.pi * (f + det) * t) + 0.25 * np.sin(2 * np.pi * 2 * (f + det) * t)
    return 0.05 * env * s / len(freqs)
# F major warm progression: F - C/E - Dm - Bb  |  F - C - Bb - C
prog = [[53, 57, 60], [52, 55, 60], [50, 53, 57], [46, 50, 53], [53, 57, 60], [48, 52, 55], [46, 50, 53], [48, 52, 55]]
t = 0.0; i = 0
while t < dur + 2:
    ch = prog[i % len(prog)]
    section = min(1.0, 0.55 + 0.45 * np.sin(np.pi * min(1, t / dur)))   # gentle arc
    p = pad([midi(m) for m in ch] + [midi(ch[0] - 12)], bar * 2 + 2)
    a = min(int(t * SR), N - 1); L[a:a + len(p)] += p[:N - a]; R[a:a + len(p)] += p[:N - a]
    # bass
    b = piano(midi(ch[0] - 12), 4, 0.22); L[a:a+len(b)] += b[:N-a]; R[a:a+len(b)] += b[:N-a]
    # arpeggio (8ths), soft, humanized
    pat = [0, 1, 2, 1, 2, 3, 2, 1] * 2
    notes = ch + [ch[0] + 12]
    for k, idx in enumerate(pat):
        tt = t + k * beat / 2 + rng.normal(0, 0.008)
        vel = (0.10 + 0.03 * (k % 4 == 0)) * section * (0.9 + 0.2 * rng.random())
        nte = piano(midi(notes[idx] + 12), 2.5, vel)
        s0 = int(tt * SR); pan = 0.5 + 0.25 * np.sin(k)
        if s0 >= N: continue
        L[s0:s0+len(nte)] += nte[:N-s0] * (1 - pan) * 1.4; R[s0:s0+len(nte)] += nte[:N-s0] * pan * 1.4
    # occasional melody note
    if i % 2 == 1:
        m = ch[2] + 12 + [0, 2, -1, 4][i % 4]
        nte = piano(midi(m + 12), 3.5, 0.12 * section)
        s0 = min(int((t + 2 * beat) * SR), N - 1); L[s0:s0+len(nte)] += nte[:N-s0]; R[s0:s0+len(nte)] += nte[:N-s0]
    t += bar * 2; i += 1
# reverb: exponentially decaying noise IR
ir_n = int(2.8 * SR); ir_t = np.arange(ir_n) / SR
def verb(x, seed):
    ir = np.random.default_rng(seed).normal(0, 1, ir_n) * np.exp(-ir_t * 2.3); ir /= np.sqrt((ir ** 2).sum())
    n = len(x) + ir_n; F = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[:len(x)]
L = 0.75 * L + 0.35 * verb(L, 1); R = 0.75 * R + 0.35 * verb(R, 2)
st = np.stack([L, R], 1)[: int(dur * SR)]
fade = int(3 * SR); st[:fade] *= np.linspace(0, 1, fade)[:, None]; st[-int(5*SR):] *= np.linspace(1, 0, int(5*SR))[:, None]
st /= np.abs(st).max() / 0.8
sf.write(OUT, st.astype(np.float32), SR)
print("music", st.shape[0] / SR, "s")
