import json, subprocess, numpy as np, soundfile as sf
SR = 48000
tl = json.load(open("timeline.json")); D = tl["dur"]
N = int((D + 0.5) * SR)
def load(path, t0=None, t1=None):
    cmd = ["ffmpeg", "-loglevel", "error"] + (["-ss", str(t0), "-to", str(t1)] if t0 is not None else []) + ["-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32).astype(np.float64)
rms = lambda x: np.sqrt(np.mean(x[np.abs(x) > 0.01] ** 2)) if np.any(np.abs(x) > 0.01) else 1e-6
voice = np.zeros(N); duck = np.full(N, 0.55)      # music gain envelope target
nr = []
for n in tl["narr"]:
    a = load(n["file"]); s = int(n["at"] * SR); voice[s:s + len(a)] += a[:N - s]; nr.append(rms(a))
    duck[max(0, s - int(0.25 * SR)): s + len(a) + int(0.35 * SR)] = 0.24
ref = np.median(nr)
for c in tl["clips"]:
    a = load(c["src"], c["t0"], c["t1"]); f = int(0.06 * SR)
    a[:f] *= np.linspace(0, 1, f); a[-f:] *= np.linspace(1, 0, f)
    a *= ref / rms(a) * 1.05
    s = int(c["at"] * SR); voice[s:s + len(a)] += a[:N - s]
    duck[max(0, s - int(0.3 * SR)): s + len(a) + int(0.3 * SR)] = 0.05
# smooth envelope (~0.35 s)
k = int(0.35 * SR); ker = np.ones(k) / k
duck = np.convolve(np.pad(duck, (k, k), mode="edge"), ker, mode="same")[k:-k]
m, msr = sf.read("music.wav")
m = load("music.wav") if msr != SR else m.mean(1)
mus = np.zeros(N); mus[:min(N, len(m))] = m[:N]
end = int((D - 3.5) * SR); mus[end:] *= np.linspace(1, 0, N - end) ** 1.5
mix = voice + 0.55 * mus * duck
mix = np.stack([mix, mix], 1); mix /= max(1.0, np.abs(mix).max() / 0.95)
sf.write("mix_raw.wav", mix.astype(np.float32), SR)
print("mixed", N / SR, "s; narration rms", ref)
