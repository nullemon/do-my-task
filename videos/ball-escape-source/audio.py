"""Soundtrack for the ring-escape short, synthesized from the simulation's own
event list (meta.json from render.js): one rising note per bounce, a glassy
shatter per ring, a chord on the final escape.   python3 audio.py meta.json out.wav"""
import json, sys, wave
import numpy as np
m = json.load(open(sys.argv[1])); D = m["DUR"]; SR = 44100; N = int(SR * D)
L = np.zeros(N); R = np.zeros(N); rng = np.random.default_rng(3)

def add(sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N: return
    sig = sig[:N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2); R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)

def tt(d): return np.arange(int(d * SR)) / SR

def mallet(f, d=0.9, bright=0.35):
    x = tt(d)
    return (np.sin(2*np.pi*f*x) * np.exp(-x*5) + bright*np.sin(2*np.pi*f*4*x) * np.exp(-x*22)
            + 0.2*np.sin(2*np.pi*f*2*x) * np.exp(-x*9)) * np.minimum(1, x/0.003)

def lp(x, k):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y

SCALE = [0, 2, 4, 7, 9]                      # major pentatonic: every bounce sounds "right"
ROOT = [220.0, 261.63, 329.63, 392.0]        # each ring starts higher: A3, C4, E4, G4
count = {0: 0, 1: 0, 2: 0, 3: 0}
for e in m["events"]:
    t, k, pan = e["t"], e["k"], float(np.clip(e["x"], -1, 1)) * 0.6
    if e["type"] == "bounce":
        n = count[k]; count[k] += 1
        f = ROOT[k] * 2 ** ((SCALE[n % 5] + 12 * (n // 5)) / 12)
        add(mallet(f), t, pan, 0.30)
        add(np.sin(2*np.pi*70*tt(0.09)) * np.exp(-tt(0.09)*40), t, 0, 0.30)          # soft thump
    else:
        last = k == 3
        d = 1.6 if last else 0.9
        x = tt(d); nz = rng.standard_normal(len(x))
        add((nz - lp(nz, 0.5)) * np.exp(-x * (5 if last else 9)), t, 0, 0.16 if last else 0.11)   # glass shatter
        chord = [0, 4, 7, 12] + ([16, 19, 24] if last else [])
        for j, st in enumerate(chord):
            add(mallet(ROOT[k] * 2 * 2 ** (st / 12), 1.8 if last else 1.1, 0.5), t + j * (0.035 if last else 0.03),
                (j % 2) * 0.6 - 0.3, 0.16 if last else 0.13)
        add(np.sin(2*np.pi*np.cumsum(np.linspace(110, 42, len(tt(0.5))))/SR) * np.exp(-tt(0.5)*6), t, 0, 0.6 if last else 0.3)

# quiet rising pad for tension, dropped at the final escape
tend = [e["t"] for e in m["events"] if e["type"] == "break"][-1]
t = np.arange(N) / SR
pad = sum(np.sin(2*np.pi*f*t + i) for i, f in enumerate((55, 82.4, 110, 164.8))) * 0.012
pad *= np.clip(t / 1.0, 0, 1) * (0.5 + 0.5 * t / tend) * (t < tend)
L += pad; R += pad

st = np.stack([L, R], 1); st = np.tanh(st * 1.4) / 1.4
st *= 10 ** (-1.5 / 20) / np.abs(st).max()
f = int(0.25 * SR); st[-f:] *= np.linspace(1, 0, f)[:, None]; st[:int(.01*SR)] *= np.linspace(0, 1, int(.01*SR))[:, None]
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())
print("audio ok")
