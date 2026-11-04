"""05 'Falling into the Mariana Trench' - voice placement/processing, underwater sound design, numpy music bed,
ducking, loudness (-14 LUFS, <= -1 dBTP) and SRT.   Run: /home/user/ttsenv/bin/python mix.py
Inputs : SCR/vo_raw/line_XX.wav (Kokoro 24 kHz), placement.json (from timeline.py)
Outputs: SCR/voice_48k.wav, SCR/mix.wav, ../mariana-trench.srt"""
import os, json, subprocess, re, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, resample_poly, oaconvolve as fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/05-mariana-trench"
PLACE = json.load(open(os.path.join(HERE, "placement.json")))
SR = 48000
DUR = PLACE["dur"]
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)
L = PLACE["lines"]
LS = lambda i: L[i]["start"]
LE = lambda i: L[i]["end"]
# depth profile (same keys as the picture), for depth-driven sound
KEYS = sorted({round(a, 3): b for a, b in PLACE["depth_keys"]}.items()) + [(DUR, 10935.0)]
DEPTH = np.interp(T[::480], [k[0] for k in KEYS], [k[1] for k in KEYS])
DEPTH = np.interp(T, T[::480], DEPTH)
T_LAMPOFF = LE(43) + 0.6


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def env(points):
    a = np.array(points, float)
    return np.interp(T, a[:, 0], a[:, 1])


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(buf, t0, sig):
    s = int(t0 * SR); e = min(N, s + len(sig))
    if s < 0:
        sig = sig[-s:]; s = 0
    if e > s:
        buf[s:e] += sig[: e - s]


def adsr(n, a, r):
    e = np.ones(n); na, nr = min(n // 2, int(a * SR)), min(n // 2, int(r * SR))
    if na: e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))
    if nr: e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e


def pad_note(midi, t0, t1, amp, a=5.0, r=6.0, bright=0.5, nh=7, seed=0):
    n = int((t1 - t0) * SR); t = np.arange(n) / SR
    r_ = np.random.default_rng(seed + int(midi * 100) + int(t0 * 10))
    f = mtof(midi)
    out = np.zeros((n, 2))
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / r_.uniform(9, 17) + r_.uniform(0, 6.28))
    for h in range(1, nh + 1):
        if f * h > 7000: break
        tilt = (1.0 / h ** 1.7) * (bright * lfo + (1 - bright * lfo) / h) if h > 1 else 1.0
        for c, det in enumerate((-1, 1)):
            fh = f * h * 2 ** (det * r_.uniform(3, 7) / 1200)
            out[:, c] += tilt * np.sin(2 * np.pi * fh * t + r_.uniform(0, 6.28))
    return out * (amp * adsr(n, a, r))[:, None]


def chord(buf, t0, t1, notes, amp, bright=0.35, a=6, r=7, seed=0):
    for j, m in enumerate(notes):
        add(buf, t0, pad_note(m, t0, t1, amp * (1.0 if m < 55 else 0.6), a, r, bright, seed=seed * 10 + j))


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
    n = int(1.4 * SR); t = np.arange(n) / SR
    ir = np.stack([bp(np.random.default_rng(5 + c).standard_normal(n), 200, 5000) * np.exp(-6.91 * t / 1.1)
                   for c in range(2)], 1)
    ir[: int(0.015 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([fftconvolve(v, ir[:, c])[:N] for c in range(2)], 1)
    os.remove(os.path.join(SCR, "vd.wav")); os.remove(os.path.join(SCR, "vc.wav"))
    return v[:, None] * np.ones((1, 2)) + 0.13 * wet


# ----------------------------------------------------------------------------- sound design
def sfx():
    out = np.zeros((N, 2), np.float32)
    t_fall = LS(2) + 0.9
    # above water: wind + gentle wash (only while the camera is at the surface)
    wash_l = env([(0, 0), (0.6, 1), (t_fall - 0.3, 1), (t_fall + 0.2, 0), (DUR, 0)])
    for c in range(2):
        w = lp(rng.standard_normal(N).astype(np.float32), 1800)
        swell = 0.6 + 0.4 * np.sin(2 * np.pi * T / 4.3 + c) ** 2
        out[:, c] += (w * swell * wash_l * 0.10).astype(np.float32)
    # plunge: a splash + a rush of bubbles rising past
    n = int(3.5 * SR); t = np.arange(n) / SR
    spl = bp(rng.standard_normal(n), 300, 6000) * np.exp(-t / 0.18) * 0.5
    bub = np.zeros(n)
    for k in range(140):
        t0 = abs(rng.normal(0.4, 0.7)); f0 = rng.uniform(300, 1600); dd = rng.uniform(0.02, 0.07)
        s0 = int(t0 * SR); m = int(dd * SR)
        if s0 + m >= n: continue
        tt = np.arange(m) / SR
        bub[s0:s0 + m] += np.sin(2 * np.pi * (f0 * tt + f0 * 3 * tt ** 2)) * np.exp(-tt / (dd / 3)) * rng.uniform(0.05, 0.16)
    sp = spl + bub * np.exp(-t / 1.2)
    add(out, t_fall - 0.05, np.stack([sp, np.roll(sp, 90)], 1).astype(np.float32))
    # underwater bed: muffled low rumble, getting deeper/heavier with depth; quieter at the very bottom
    under = env([(0, 0), (t_fall - 0.2, 0), (t_fall + 0.6, 1), (T_LAMPOFF, 1), (T_LAMPOFF + 3, 0.5), (DUR, 0.0)])
    dk = np.clip(DEPTH / 10935.0, 0, 1)
    for c in range(2):
        x = rng.standard_normal(N).astype(np.float32)
        a = lp(x, 260, 2) * (0.9 + 0.2 * c)
        b = lp(x, 70, 2) * 2.5
        out[:, c] += ((a * (1 - 0.6 * dk) + b * (0.4 + 0.8 * dk)) * under * 0.14).astype(np.float32)
    # distant low groans in the hadal zone (the planet's crust; sparse, very low)
    for tg in (LS(28) + 3.0, LS(30) + 1.0, LS(31) + 7.0, LS(36) + 2.0):
        n = int(4.0 * SR); t = np.arange(n) / SR
        f = 48 + 10 * np.sin(2 * np.pi * t / 3.1)
        g = np.sin(2 * np.pi * np.cumsum(f) / SR) * adsr(n, 1.2, 2.2) * 0.10
        g += lp(rng.standard_normal(n), 120) * adsr(n, 1.0, 2.5) * 0.25
        add(out, tg, np.stack([g, g * 0.8], 1).astype(np.float32))
    # sperm whale clicks (echolocation): ~1-2 per second, sharp, band-limited
    t0, t1 = LS(20) - 0.8, LE(20) + 1.5
    tc = t0
    while tc < t1:
        n = int(0.02 * SR); t = np.arange(n) / SR
        k = bp(rng.standard_normal(n), 1500, 7000) * np.exp(-t / 0.002) * 0.22
        k += bp(rng.standard_normal(n), 400, 2000) * np.exp(-t / 0.003) * 0.2
        pan = 0.5 + 0.3 * np.sin(tc)
        g = np.sin(np.pi * (tc - t0) / (t1 - t0))
        add(out, tc, (np.stack([k * pan, k * (1 - pan)], 1) * g).astype(np.float32))
        tc += rng.uniform(0.5, 0.9)
    # soft glassy chimes for bioluminescence moments
    for tb, base in ((LS(10) + 1.0, 84), (LS(17) + 0.3, 88), (LS(18) + 0.5, 83), (LS(19) + 2.0, 86)):
        for j in range(5):
            n = int(2.5 * SR); t = np.arange(n) / SR
            f = mtof(base + [0, 7, 12, 3, 10][j])
            s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7) * 0.025
            add(out, tb + j * 0.35, np.stack([s * (j % 2), s * (1 - j % 2)], 1).astype(np.float32))
    # arrival on the floor: a soft muffled thump + silt hiss
    ta = LS(34) + 1.0
    n = int(4 * SR); t = np.arange(n) / SR
    th = np.sin(2 * np.pi * (55 - 15 * t) * t) * np.exp(-t / 0.35) * 0.35 + lp(rng.standard_normal(n), 900) * np.exp(-t / 1.5) * 0.10
    add(out, ta, np.stack([th, th], 1).astype(np.float32))
    # lamp off: a dull click
    n = int(0.5 * SR); t = np.arange(n) / SR
    ck = bp(rng.standard_normal(n), 600, 4000) * np.exp(-t / 0.006) * 0.25 + np.sin(2 * np.pi * 90 * t) * np.exp(-t / 0.05) * 0.2
    add(out, T_LAMPOFF, np.stack([ck, ck], 1).astype(np.float32))
    return out


# ----------------------------------------------------------------------------- music bed
def build_bed():
    bed = np.zeros((N, 2), np.float32)
    s1 = LS(3)
    # surface: open, airy, D dorian colour
    chord(bed, 0.3, 14, [50, 57, 62, 64, 69], 0.022, 0.45, a=4)
    chord(bed, 11, 28, [50, 57, 62, 66, 71], 0.024, 0.45)            # sunlit: D maj9-ish
    chord(bed, 25, 42, [47, 54, 59, 62, 66], 0.024, 0.4)             # Bm
    # twilight: cooling, minor
    chord(bed, 39, 58, [45, 52, 57, 60, 64], 0.024, 0.38)            # Am
    chord(bed, 55, 72, [43, 50, 55, 58, 62], 0.024, 0.36)            # Gm
    chord(bed, 69, 90, [41, 48, 53, 56, 60], 0.024, 0.34)            # Fm
    # night: darker, lower, sparse
    chord(bed, 87, 104, [38, 45, 50, 53], 0.026, 0.28, a=8)          # Dm (the light is gone)
    chord(bed, 100, 128, [36, 43, 48, 51, 55, 62], 0.022, 0.30)      # Cm(add9) - bioluminescence
    chord(bed, 124, 150, [34, 41, 46, 50, 53], 0.022, 0.30)          # Bb
    chord(bed, 146, 168, [33, 40, 45, 48, 52], 0.024, 0.28)          # Am low (Everest, Titanic)
    # abyss / hadal: drones, tritone shadows
    chord(bed, 164, 200, [31, 38, 43, 46], 0.026, 0.22, a=8)         # Gm low
    chord(bed, 195, 240, [29, 36, 41, 47], 0.026, 0.20, a=8)         # F + B (tritone colour)
    chord(bed, 236, 276, [28, 35, 40, 43, 50], 0.026, 0.24, a=8)     # Em low (the dives)
    # the floor: still, cold, one breath of warmth for the amphipods, then the comparison
    chord(bed, 273, 302, [26, 33, 38, 45], 0.026, 0.18, a=6)         # D
    chord(bed, 299, 314, [29, 36, 41, 45, 52], 0.022, 0.25)          # F(add9)
    chord(bed, 311, 336, [31, 38, 43, 47, 50, 57], 0.022, 0.28)      # G - wonder (Moon, space)
    chord(bed, 333, T_LAMPOFF + 1, [26, 33, 38, 41, 45], 0.024, 0.22, r=4)
    chord(bed, T_LAMPOFF + 1.0, DUR - 0.2, [26, 38, 45, 50, 57], 0.022, 0.25, a=3, r=5)   # title: open D
    # sub swells at zone changes
    for tc, amp in ((LS(2) + 1.0, 0.14), (LS(7), 0.10), (LS(13) + 2, 0.14), (LS(15), 0.12), (LS(23), 0.12), (LS(24), 0.10),
                    (LS(27), 0.14), (LS(34) + 1.0, 0.16)):
        n = int(12 * SR); t = np.arange(n) / SR
        e = np.where(t < 6, (t / 6) ** 2.2, np.exp(-(t - 6) / 2.0))
        s = np.sin(2 * np.pi * 34.6 * t) * e * amp
        add(bed, tc - 6, np.stack([s, s], 1))
    # reverb
    n = int(5.0 * SR); tt = np.arange(n) / SR
    ir = np.stack([bp(np.random.default_rng(40 + c).standard_normal(n), 100, 6000) for c in range(2)], 1)
    ir *= np.exp(-6.91 * tt / 4.5)[:, None]; ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    for c in range(2):
        bed[:, c] = 0.6 * bed[:, c] + 0.6 * fftconvolve(bed[:, c], ir[:, c].astype(np.float32))[:N]
    # darken the bed progressively with depth (low-pass sweeps down)
    dk = np.clip(DEPTH / 10935.0, 0, 1)
    bright = lp(bed, 5000); dark = lp(bed, 900)
    bed = bright * (1 - dk[:, None]) + dark * dk[:, None]
    bed = sosfilt(butter(2, 25, "high", fs=SR, output="sos"), bed, axis=0)
    gate = env([(0, 1), (T_LAMPOFF - 0.05, 1), (T_LAMPOFF + 0.1, 0.35), (T_LAMPOFF + 1.0, 1), (DUR - 1.6, 1), (DUR - 0.1, 0), (DUR, 0)])
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
            a, b = text[:i + 1].strip(), text[i + 2:].strip()
            return split_cue(a) + split_cue(b) if len(a) > 88 or len(b) > 88 else [a, b]
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
        sf.write(vp, voice, SR, subtype="FLOAT")
    fx = sfx()
    bed = build_bed()
    g = duck_gain(voice)
    v = voice / np.abs(voice).max() * 0.5
    b = bed / (np.abs(bed).max() + 1e-9) * 0.24
    fx_g = 1 - (1 - g) * 0.5
    mix = v + b * g[:, None] + fx * fx_g[:, None]
    mix = mix / np.abs(mix).max() * 0.7
    pre = os.path.join(SCR, "mix_pre.wav")
    sf.write(pre, mix.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af",
                        "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-2.0:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:"
          f"linear=true:print_format=summary,aresample=48000,alimiter=limit=0.79:attack=5:release=80:level=false")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", af, "-t", str(DUR), "-ar", "48000",
                    "-c:a", "pcm_s24le", os.path.join(SCR, "mix.wav")], check=True)
    os.remove(pre)
    print("SRT cues:", write_srt(os.path.join(os.path.dirname(HERE), "mariana-trench.srt")))


if __name__ == "__main__":
    main()
