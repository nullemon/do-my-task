"""Soundtrack for the cup-shuffle short, synthesized from meta.json (render.js meta).
python3 audio.py meta.json out.wav"""
import json, sys, wave
import numpy as np
m = json.load(open(sys.argv[1])); D = m["DUR"]; T = m["T"]; SR = 44100; N = int(SR * D)
L = np.zeros(N); R = np.zeros(N); rng = np.random.default_rng(5)
def add(sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    sig = sig[:N - i] * gain
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2); R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)
def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, k):
    kk = np.broadcast_to(np.asarray(k, float), x.shape); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += kk[i] * (x[i] - acc); y[i] = acc
    return y
def bell(f, d=1.2, dec=4.0):
    x = tt(d); return (np.sin(2*np.pi*f*x) + .35*np.sin(2*np.pi*f*2.01*x)*np.exp(-x*6) + .2*np.sin(2*np.pi*f*3*x)*np.exp(-x*12)) * np.exp(-x*dec) * np.minimum(1, x/.003)
def thunk(g=1.0):
    x = tt(.16); return (np.sin(2*np.pi*np.cumsum(np.linspace(170, 70, len(x)))/SR) * np.exp(-x*26) + lp(rng.standard_normal(len(x)), .3)*np.exp(-x*60)*.5) * g

# intro: text pop, cups land
add(bell(660, .5, 9), 0.05, 0, .12)
for i, p in enumerate((-.5, 0, .5)): add(thunk(), T["land"] + i*.012, p, .55)
# shuffle: one whoosh per swap (shorter + brighter as it speeds up) and a soft slide-stop
for s in m["swaps"]:
    d = s["d"]; x = tt(d); e = np.sin(np.pi*x/d)**1.6
    w = lp(rng.standard_normal(len(x)), .05 + (.12 + .25*(.66-d))*e) * e
    add(w, s["t"], s["x"]*.7, .75)
    add(thunk(.35), s["t"] + d - .02, s["x"]*.7, .5)
# tension pulse that speeds up with the shuffle
t = np.arange(N) / SR
ph = np.cumsum(np.interp(t, [T["shuffle"], T["ask"]], [2.2, 7.0])) / SR
pulse = (np.sin(2*np.pi*ph) > .6) * np.sin(2*np.pi*98*t) * .055 * ((t > T["shuffle"]) & (t < T["ask"] - .1))
pulse = lp(pulse, .2); L += pulse; R += pulse
# "which cup?": three ticks then the reveal chord
add(bell(880, .4, 10), T["ask"], 0, .16)
for i in range(3): add(bell(1320, .12, 30), T["ask"] + .3 + i*.27, 0, .12)
for j, st in enumerate((0, 4, 7, 12)): add(bell(523.25 * 2**(st/12), 1.4, 3.2), T["reveal"] + .1 + j*.045, (j % 2)*.5 - .25, .16)
add(thunk(.6), T["reveal"] + .08, 0, .5)
# twist: "wait, what?" - two questioning notes + riser
add(bell(392, .6, 5), T["twist"], -.2, .16); add(bell(466.16, .9, 3.5), T["twist"] + .2, .2, .18)
x = tt(.5); add(lp(rng.standard_normal(len(x)), np.linspace(.02, .4, len(x))) * (x/.5)**2, T["twist"] - .45, 0, .3)
for j, p in enumerate((-.4, .4)): add(bell(784 * (1.26 if j else 1), .5, 7), T["twist"] + .62 + j*.1, p, .1)

st = np.stack([L, R], 1); st = np.tanh(st * 1.5) / 1.5
st *= 10 ** (-1.5 / 20) / np.abs(st).max()
f = int(.12 * SR); st[-f:] *= np.linspace(1, 0, f)[:, None]
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype("<i2").tobytes())
print("audio ok")
