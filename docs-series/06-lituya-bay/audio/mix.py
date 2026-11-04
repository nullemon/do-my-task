"""06 'The 524-metre wave' - voice placement/processing, fjord sound design, music bed, ducking,
loudness (-14 LUFS, <= -1 dBTP) and SRT.   Run: /home/user/ttsenv/bin/python mix.py
Inputs : SCR/vo_raw/line_XX.wav (Kokoro 24 kHz), placement.json (from timeline.py)
Outputs: SCR/voice_48k.wav, SCR/bed_48k.wav, SCR/mix.wav, ../lituya-bay.srt"""
import os, json, subprocess, re
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, resample_poly, oaconvolve as fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
PLACE = json.load(open(os.path.join(HERE, "placement.json")))
SR = 48000
DUR = PLACE["dur"]
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)
L = PLACE["lines"]
SH = PLACE["shots"]


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def env(points):
    a = np.array(points, float)
    return np.interp(T, a[:, 0], a[:, 1])


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(buf, t0, sig):
    s = int(t0 * SR); e = min(N, s + len(sig))
    if e > s:
        buf[s:e] += sig[: e - s]


def adsr(n, a, r):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))
    if nr: e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e


def pad_note(midi, t0, t1, amp, a=5.0, r=6.0, bright=0.5, nh=7, seed=0, glide=None):
    n = int((t1 - t0) * SR); t = np.arange(n) / SR
    r_ = np.random.default_rng(seed + int(midi * 100) + int(t0 * 10))
    f = mtof(midi)
    fcurve = np.ones(n) if glide is None else 2 ** (np.interp(t, glide[0], glide[1]) / 12)
    out = np.zeros((n, 2))
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / r_.uniform(9, 17) + r_.uniform(0, 6.28))
    for h in range(1, nh + 1):
        if f * h > 9000: break
        tilt = (1.0 / h ** 1.6) * (bright * lfo + (1 - bright * lfo) / h) if h > 1 else 1.0
        for c, det in enumerate((-1, 1)):
            fh = f * h * 2 ** (det * r_.uniform(3, 7) / 1200)
            ph = 2 * np.pi * np.cumsum(fh * fcurve) / SR + r_.uniform(0, 6.28)
            out[:, c] += tilt * np.sin(ph)
    return out * (amp * adsr(n, a, r))[:, None]


def chord(buf, t0, t1, notes, amp, bright=0.4, a=5, r=6, seed=0):
    for j, m in enumerate(notes):
        add(buf, t0, pad_note(m, t0, t1, amp * (1.0 if m < 60 else 0.7), a, r, bright, seed=seed * 10 + j))


# ----------------------------------------------------------------------------- voice
def build_voice():
    dry = np.zeros(N)
    for l in L:
        x, sr = sf.read(os.path.join(SCR, "vo_raw", f"line_{l['i']:02d}.wav"))
        x = resample_poly(x, 2, 1)
        s = int(round(l["start"] * SR))
        dry[s:s + len(x)] += x[: N - s]
    dry = sosfilt(butter(4, 70, "high", fs=SR, output="sos"), dry)
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    sf.write(os.path.join(SCR, "vd.wav"), dry, SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(SCR, "vd.wav"), "-af",
                    "equalizer=f=250:t=q:w=1.0:g=-1.5,equalizer=f=3500:t=q:w=1.2:g=1.0,"
                    "acompressor=threshold=-22dB:ratio=3:attack=8:release=180:knee=6:makeup=4",
                    "-c:a", "pcm_f32le", os.path.join(SCR, "vc.wav")], check=True)
    v, _ = sf.read(os.path.join(SCR, "vc.wav"))
    n = int(0.9 * SR); t = np.arange(n) / SR
    ir = np.stack([bp(np.random.default_rng(5 + c).standard_normal(n), 250, 6000) * np.exp(-6.91 * t / 0.55)
                   for c in range(2)], 1)
    ir[: int(0.012 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([fftconvolve(v, ir[:, c])[:N] for c in range(2)], 1)
    os.remove(os.path.join(SCR, "vd.wav")); os.remove(os.path.join(SCR, "vc.wav"))
    return v[:, None] * np.ones((1, 2)) + 0.16 * wet


# ----------------------------------------------------------------------------- sound design (fjord)
def noise_bp(n, lo, hi, seed, order=2):
    return bp(np.random.default_rng(seed).standard_normal(n).astype(np.float32), lo, hi, order)


def brown(n, seed):
    x = np.cumsum(np.random.default_rng(seed).standard_normal(n)).astype(np.float64)
    x = sosfilt(butter(1, 15, "high", fs=SR, output="sos"), x)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def sfx():
    out = np.zeros((N, 2), np.float32)
    # ambient: soft wind + water lapping, present in all fjord shots, dipped under diagrams
    amb_lev = env([(0, 0), (1.5, 1), (SH["runup"] - 0.5, 1), (SH["runup"] + 1, 0.25), (SH["bay"] - 1, 0.25),
                   (SH["bay"], 1), (SH["science"], 1), (SH["science"] + 1, 0.3), (SH["end"] - 1, 0.3), (SH["end"] + 1, 1),
                   (DUR - 3, 1), (DUR, 0)]).astype(np.float32)
    for c in range(2):
        w = noise_bp(N, 150, 1200, 100 + c)
        g = 0.5 + 0.5 * np.sin(2 * np.pi * T / (7.3 + c) + c) * np.sin(2 * np.pi * T / 17.0)
        lap = noise_bp(N, 300, 2500, 110 + c) * (0.5 + 0.5 * np.sin(2 * np.pi * T / (2.9 + 0.4 * c))) ** 3
        out[:, c] += (w * (0.010 + 0.010 * g) + lap * 0.006).astype(np.float32) * amb_lev
    # earthquake: sub rumble + grinding, ~14 s
    tq = L[7]["start"] - 0.6
    n = int(16 * SR); t = np.arange(n) / SR
    e = np.where(t < 2, t / 2, np.exp(-(t - 2) / 6.0))
    rum = brown(n, 120) * 0.9 + noise_bp(n, 25, 90, 121) * 3.0
    rum = rum * e * (0.7 + 0.3 * np.sin(2 * np.pi * 1.7 * t) ** 2)
    sub = np.sin(2 * np.pi * (31 + 3 * np.sin(2 * np.pi * 0.3 * t)) * t) * e * 0.35
    cr = noise_bp(n, 600, 4000, 122) * (np.random.default_rng(123).random(n) < 0.003) * 6 * e
    q = (rum * 0.18 + sub + bp(cr, 600, 4000) * 0.05).astype(np.float32)
    add(out, tq, np.stack([q, q * 0.92], 1))
    # rockslide: roar swelling while the wall comes down, then the impact boom
    ts0, ts1 = L[9]["start"] - 1.0, SH["surge"] + 0.3
    n = int((ts1 - ts0 + 6) * SR); t = np.arange(n) / SR; d = ts1 - ts0
    e = np.clip(t / d, 0, 1) ** 1.5 * np.where(t < d, 1, np.exp(-(t - d) / 1.5))
    roar = (brown(n, 130) * 0.6 + noise_bp(n, 80, 1800, 131) * 2.2) * e
    add(out, ts0, np.stack([roar * 0.11, bp(roar, 60, 1600) * 0.11], 1).astype(np.float32))
    n = int(7 * SR); t = np.arange(n) / SR
    boom = (np.sin(2 * np.pi * (48 * np.exp(-t / 1.2) + 22) * t) * np.exp(-t / 1.6) * 0.55 +
            noise_bp(n, 40, 600, 132) * np.exp(-t / 1.0) * 1.5)
    add(out, ts1, np.stack([boom, boom], 1).astype(np.float32) * 0.5)
    # surge up the slope: long wash roar
    tw0 = SH["surge"] + 0.5
    n = int(26 * SR); t = np.arange(n) / SR
    e = np.where(t < 1.2, t / 1.2, np.exp(-(t - 1.2) / 7.0))
    wash = np.stack([noise_bp(n, 120, 5000, 140 + c) * 1.2 + brown(n, 142 + c) * 0.5 for c in range(2)], 1)
    add(out, tw0, (wash * (e * 0.09)[:, None]).astype(np.float32))
    # the wave racing down the bay and hitting the boats
    tb0, tb1 = SH["bay"] + 1.0, L[21]["start"] + 0.8
    n = int((tb1 - tb0 + 14) * SR); t = np.arange(n) / SR; d = tb1 - tb0
    e = np.where(t < d, (t / d) ** 2.2, np.exp(-(t - d) / 4.5))
    wv = np.stack([noise_bp(n, 70, 4500, 150 + c) * 1.1 + brown(n, 152 + c) * 0.7 for c in range(2)], 1)
    add(out, tb0, (wv * (e * 0.10)[:, None]).astype(np.float32))
    # distant crack for the snapped chain
    n = int(0.5 * SR); t = np.arange(n) / SR
    k = noise_bp(n, 900, 6000, 160) * np.exp(-t / 0.03) * 0.3
    add(out, L[21]["start"] + 1.4, np.stack([k, k * 0.8], 1).astype(np.float32))
    return out


# ----------------------------------------------------------------------------- music bed
def build_bed():
    bed = np.zeros((N, 2), np.float32)
    s = lambda k: SH[k]
    # open / map: cold, wide, D minor colours
    chord(bed, 0.3, 20, [38, 50, 57, 64], 0.026, 0.25, a=3)           # Dm(add9)
    chord(bed, 17, 33, [34, 46, 53, 62], 0.026, 0.3)                  # Bb
    chord(bed, 30, 47, [36, 48, 55, 62, 67], 0.026, 0.3)              # C(sus)
    chord(bed, 44, 72, [38, 50, 57, 62, 65], 0.024, 0.25, r=4)         # Dm - the calm night
    # quake -> slide: drone + rising cluster
    chord(bed, 70, 96, [26, 38, 45], 0.030, 0.2, a=4, r=2)             # low D drone
    for j, (m, g) in enumerate(((62, 1), (63, 2), (69, 1))):
        add(bed, 78, pad_note(m, 78, 96, 0.010, a=8, r=1.5, bright=0.6, seed=70 + j,
                              glide=([0, 17.5], [0, g])))
    # surge: big minor swell, then scale (awe)
    chord(bed, s("surge") + 0.5, 121, [26, 38, 50, 53, 57, 62], 0.034, 0.55, a=2.5, r=5)
    chord(bed, 118, 140, [34, 46, 53, 58, 62, 65], 0.028, 0.45)        # Bb
    # explainer: lighter, curious
    chord(bed, 137, 162, [41, 53, 57, 60, 64], 0.022, 0.35)            # Fmaj7
    chord(bed, 159, 185, [36, 48, 55, 60, 64], 0.022, 0.35)            # C
    # the wave down the bay -> boats: tension
    chord(bed, 183, 214, [26, 38, 45, 51], 0.028, 0.35, a=3)            # D + b9 colour
    chord(bed, 211, 233, [31, 43, 50, 58], 0.026, 0.3)                  # Gm
    # aftermath / science
    chord(bed, 231, 258, [34, 46, 53, 57, 62], 0.022, 0.3)              # Bbmaj7
    chord(bed, 255, 278, [41, 48, 57, 60, 65], 0.022, 0.35)             # F
    # risk: ominous again
    chord(bed, 276, 300, [38, 45, 50, 53], 0.026, 0.3)
    chord(bed, 297, 315, [34, 41, 50, 53, 58], 0.026, 0.3)
    # end: slow resolution
    chord(bed, 313, DUR, [38, 50, 57, 62, 65, 69], 0.026, 0.4, a=4, r=7)
    for tc, amp in ((s("quake"), 0.15), (s("surge"), 0.18), (s("bay"), 0.14), (s("risk"), 0.10), (s("end"), 0.10)):
        n = int(12 * SR); t = np.arange(n) / SR
        e = np.where(t < 6, (t / 6) ** 2.2, np.exp(-(t - 6) / 1.8))
        sb = np.sin(2 * np.pi * 36.7 * t) * e * amp
        add(bed, tc - 6, np.stack([sb, sb], 1))
    n = int(4.5 * SR); tt = np.arange(n) / SR
    ir = np.stack([bp(np.random.default_rng(40 + c).standard_normal(n), 120, 7000) for c in range(2)], 1)
    ir *= np.exp(-6.91 * tt / 4.0)[:, None]; ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    ir = ir.astype(np.float32)
    for c in range(2):
        bed[:, c] = 0.65 * bed[:, c] + 0.55 * fftconvolve(bed[:, c], ir[:, c])[:N]
    bed = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), bed, axis=0)
    gate = env([(0, 0), (0.3, 1), (DUR - 4, 1), (DUR - 0.3, 0), (DUR, 0)])
    return bed * gate[:, None]


def movavg(x, win):
    c = np.concatenate([[0.0], np.cumsum(x, dtype=np.float64)])
    h = win // 2
    i0 = np.clip(np.arange(len(x)) - h, 0, len(x)); i1 = np.clip(np.arange(len(x)) + win - h, 0, len(x))
    return (c[i1] - c[i0]) / win


def duck_gain(voice, depth_db=8.0):
    mono = np.abs(voice).mean(1).astype(np.float64)
    rms = np.sqrt(movavg(mono ** 2, int(0.05 * SR)))
    act = movavg((rms > 0.01 * rms.max()).astype(float), int(0.35 * SR)) > 0
    g = sosfiltfilt(butter(1, 1.2, "low", fs=SR, output="sos"), -depth_db * act.astype(float))
    return (10 ** (g / 20)).astype(np.float32)


# ----------------------------------------------------------------------------- SRT
def fmt(t):
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text, width=44):
    if len(text) <= width: return text
    w = text.split(); best = None
    for k in range(1, len(w)):
        a, b = " ".join(w[:k]), " ".join(w[k:]); sc = max(len(a), len(b))
        if best is None or sc < best[0]: best = (sc, a, b)
    return best[1] + "\n" + best[2]


def split_cue(text):
    if len(text) <= 88: return [text]
    for sep in (". ", ": ", "; ", ", "):
        if sep in text:
            i = text.find(sep, len(text) // 3)
            if i < 0: i = text.find(sep)
            return [text[:i + 1].strip(), text[i + 2:].strip()]
    return [text]


def write_srt(path):
    cues = []
    for i, l in enumerate(L):
        nxt = L[i + 1]["start"] if i + 1 < len(L) else DUR
        end = min(l["end"] + 0.5, nxt - 0.12)
        parts = split_cue(l["text"])
        tot = sum(len(p) for p in parts); t = l["start"]
        for k, p in enumerate(parts):
            e = t + (l["end"] - l["start"]) * len(p) / tot if k < len(parts) - 1 else end
            cues.append((t, e, p)); t = e
    with open(path, "w", encoding="utf-8") as f:
        for k, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{k}\n{fmt(a)} --> {fmt(b)}\n{wrap(txt)}\n\n")
    return len(cues)


def main():
    vp = os.path.join(SCR, "voice_48k.wav")
    if os.path.exists(vp) and os.path.getmtime(vp) > os.path.getmtime(os.path.join(HERE, "placement.json")):
        voice = sf.read(vp, dtype="float32")[0]
    else:
        voice = build_voice().astype(np.float32)
    fx = sfx()
    bed = build_bed()
    sf.write(vp, voice, SR, subtype="FLOAT")
    g = duck_gain(voice)
    v = voice / np.abs(voice).max() * 0.5
    b = bed / (np.abs(bed).max() + 1e-9) * 0.24
    fx_g = 1 - (1 - g) * 0.5          # effects duck less than the music
    mix = v + b * g[:, None] + fx * fx_g[:, None]
    sf.write(os.path.join(SCR, "bed_48k.wav"), (b + fx).astype(np.float32), SR, subtype="FLOAT")
    mix = mix / np.abs(mix).max() * 0.7
    pre = os.path.join(SCR, "mix_pre.wav")
    sf.write(pre, mix.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:"
          f"linear=true:print_format=summary,aresample=48000,alimiter=limit=0.84:attack=5:release=80:level=false")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", af, "-t", str(DUR), "-ar", "48000",
                    "-c:a", "pcm_s24le", os.path.join(SCR, "mix.wav")], check=True)
    os.remove(pre)
    print("SRT cues:", write_srt(os.path.join(os.path.dirname(HERE), "lituya-bay.srt")))


if __name__ == "__main__":
    main()
