"""Soundtrack for the pause game: a click per card (pitched by rarity), a driving pulse, a sparkle on LEGENDARY.
python3 audio.py meta.json out.wav"""
import json, sys, wave
import numpy as np
m = json.load(open(sys.argv[1])); D = m["DUR"]; SR = 44100; N = int(SR * D)
x = np.arange(N) / SR; S = np.zeros(N)
def add(sig, at, g=1.0):
    i = int(at * SR); sig = sig[:N - i] * g; S[i:i + len(sig)] += sig
def tt(d): return np.arange(int(d * SR)) / SR
PITCH = {"common": 700, "rare": 940, "epic": 1250, "cursed": 330, "legendary": 1760}
for c in m["cards"]:
    if c["tier"] == "legendary":
        for j, st in enumerate((0, 4, 7, 12, 16)):
            y = tt(.5); add(np.sin(2*np.pi*1046.5*2**(st/12)*y) * np.exp(-y*9), c["t"] + j*.018, .16)
    else:
        y = tt(.05); add(np.sin(2*np.pi*PITCH[c["tier"]]*y) * np.exp(-y*90), c["t"], .22)
bpm = 150; beat = 60 / bpm; k = 0
while k * beat < D:                                                # kick + offbeat hat; 10 s = 25 beats, so it loops cleanly
    y = tt(.18); add(np.sin(2*np.pi*np.cumsum(np.linspace(150, 48, len(y)))/SR) * np.exp(-y*18), k*beat, .55)
    y = tt(.04); h = np.random.default_rng(k).standard_normal(len(y)); add((h - np.convolve(h, np.ones(8)/8, 'same')) * np.exp(-y*120), k*beat + beat/2, .12)
    k += 1
S += np.sin(2*np.pi*55*x) * (.5 + .5*np.sign(np.sin(2*np.pi*(bpm/60)*2*x))) * .06
S = np.tanh(S * 1.5) / 1.5; S *= 10**(-1.5/20) / np.abs(S).max()
f = int(.01*SR); S[-f:] *= np.linspace(1, 0, f); S[:f] *= np.linspace(0, 1, f)
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.stack([S, S], 1) * 32767).astype("<i2").tobytes())
print("audio ok")
