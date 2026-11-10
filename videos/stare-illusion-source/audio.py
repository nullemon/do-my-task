"""Soundtrack for the stare illusion: a soft tick each second, a slow riser, a pop at the flip.
python3 audio.py meta.json out.wav"""
import json, sys, wave
import numpy as np
m = json.load(open(sys.argv[1])); D = m["DUR"]; T = m["T"]; SR = 44100; N = int(SR * D)
x = np.arange(N) / SR; S = np.zeros(N)
def add(sig, at, g=1.0):
    i = int(at * SR); sig = sig[:N - i] * g; S[i:i + len(sig)] += sig
def tt(d): return np.arange(int(d * SR)) / SR
def bell(f, d, dec): y = tt(d); return (np.sin(2*np.pi*f*y) + .3*np.sin(2*np.pi*2*f*y)*np.exp(-y*8)) * np.exp(-y*dec) * np.minimum(1, y/.003)
add(bell(520, .5, 8), .02, .25); add(bell(780, .6, 7), .12, .2)                       # hook
n = int(T["flip"] - T["start"])
for i in range(n):                                                                    # one tick per second, rising
    add(bell(600 + i*45, .18, 22), T["start"] + i, .16 + .012*i)
ris = np.sin(2*np.pi*np.cumsum(np.interp(x, [T["start"], T["flip"]], [70, 140]))/SR) * .07 * np.clip((x - T["start"]) / (T["flip"] - T["start"]), 0, 1)**1.5 * (x < T["flip"])
S += ris
y = tt(.12); add(np.sin(2*np.pi*np.cumsum(np.linspace(900, 200, len(y)))/SR) * np.exp(-y*30), T["flip"], .6)   # pop
for j, st in enumerate((0, 7, 12, 16)): add(bell(392 * 2**(st/12), 2.0, 2.2), T["flip"] + .03 + j*.04, .14)
add(bell(660, .4, 9), T["hint"], .12)
S = np.tanh(S * 1.4) / 1.4; S *= 10**(-2/20) / np.abs(S).max(); f = int(.15*SR); S[-f:] *= np.linspace(1, 0, f)
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.stack([S, S], 1) * 32767).astype("<i2").tobytes())
print("audio ok")
