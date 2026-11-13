"""python lib/mix.py <code>  -> work/voice.wav (polished narration+real audio), work/mix.m4a (-14 LUFS, TP -1.5)
Music sits ~18 dB under the voice, rises a little on chapter cards, drops to almost nothing under real audio."""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_case, FF, LIB
import numpy as np, soundfile as sf
SR = 48000
POLISH = ("highpass=f=70,equalizer=f=160:t=q:w=1:g=2,equalizer=f=9000:t=q:w=1:g=1.5,"
          "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2dB")

def load(path, t0=None, t1=None):
    cmd = [FF, "-loglevel", "error"] + (["-ss", str(t0), "-to", str(t1)] if t0 is not None else []) + ["-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, dtype=np.float32).astype(np.float64)
def rms(x):
    y = x[np.abs(x) > 0.01]; return float(np.sqrt(np.mean(y ** 2))) if len(y) else 1e-6

def main(code):
    cfg, scr = load_case(code); W = cfg.WORK
    tl = json.load(open(os.path.join(W, "timeline.json"), encoding="utf-8")); D = tl["dur"]; N = int(D * SR) + SR // 10
    voice = np.zeros(N); real = np.zeros(N); gain = np.full(N, -18.0)   # music level in dB relative to voice
    nr = []
    for n in tl["narr"]:
        a = load(os.path.join(W, n["file"])); s = int(n["at"] * SR); voice[s:s + len(a)] += a[:N - s]; nr.append(rms(a))
    ref = float(np.median(nr))
    for sp in tl["spans"]:
        if sp.get("chapter"): gain[int(sp["t0"] * SR):int(sp["t1"] * SR)] = -11.0
    gain[:int(0.3 * SR)] = -18.0
    for c in tl["clips"]:
        a = load(cfg.SRC[c["src"]], c["t0"], c["t1"]); f = int(0.08 * SR)
        a[:f] *= np.linspace(0, 1, f); a[-f:] *= np.linspace(1, 0, f)
        a *= ref / rms(a) * c.get("gain", 1.05)
        s = int(c["at"] * SR); real[s:s + len(a)] += a[:N - s]
        gain[max(0, s - int(0.3 * SR)): s + len(a) + int(0.3 * SR)] = -34.0
    # polish narration (gentle chain), keep real audio untouched
    sf.write(os.path.join(W, "voice_raw.wav"), voice.astype(np.float32), SR)
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", os.path.join(W, "voice_raw.wav"), "-af", POLISH, os.path.join(W, "voice_pol.wav")], check=True)
    v, _ = sf.read(os.path.join(W, "voice_pol.wav")); v = v[:N] if v.ndim == 1 else v[:N, 0]
    v = np.pad(v, (0, N - len(v))); v *= ref / max(rms(v), 1e-6)
    vox = v + real
    # music
    mus_f = os.path.join(W, "music.wav")
    if not os.path.exists(mus_f) or sf.info(mus_f).duration < D:
        subprocess.run([sys.executable, os.path.join(LIB, "music.py"), str(D + 1), mus_f], check=True)
    m = load(mus_f); m = np.pad(m, (0, max(0, N - len(m))))[:N]
    k = int(0.4 * SR); g = np.convolve(np.pad(gain, (k, k), mode="edge"), np.ones(k) / k, mode="same")[k:-k]
    mus = m / max(rms(m), 1e-6) * ref * 10 ** (g / 20)
    end = int((D - 3.0) * SR); mus[end:] *= np.linspace(1, 0, N - end) ** 1.5
    mix = vox + mus; mix = np.stack([mix, mix], 1); mix /= max(1.0, np.abs(mix).max() / 0.98)
    raw = os.path.join(W, "mix_raw.wav"); sf.write(raw, mix.astype(np.float32), SR)
    # two-pass loudnorm to -14 LUFS / -1.5 dBTP
    r = subprocess.run([FF, "-hide_banner", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(r[r.rfind("{"):r.rfind("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", raw, "-af", ln + ",aresample=48000", "-c:a", "aac", "-b:a", "192k", os.path.join(W, "mix.m4a")], check=True)
    print(f"mix done: {D:.1f}s  (input {j['input_i']} LUFS -> -14)")

if __name__ == "__main__": main(sys.argv[1])
