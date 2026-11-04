"""04 'The Big Bang is on your TV' - voice placement/processing, TV sound design, music bed, ducking,
loudness (-14 LUFS, <= -1 dBTP) and SRT.   Run: /home/user/ttsenv/bin/python mix.py
Inputs : SCR/vo_raw/line_XX.wav (Kokoro 24 kHz), placement.json (from timeline.py)
Outputs: SCR/voice_48k.wav, SCR/bed_48k.wav, SCR/mix.wav, ../bigbang-tv.srt"""
import os, json, subprocess, re
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, resample_poly, oaconvolve as fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv"
PLACE = json.load(open(os.path.join(HERE, "placement.json")))
SR = 48000
DUR = PLACE["dur"]
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)
L = PLACE["lines"]
SH = PLACE["shots"]
T_OFF = L[26]["end"] + 3.2


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


# ----------------------------------------------------------------------------- TV sound design
def tv_sfx():
    """Analog-TV hiss (stereo-ish, slightly crackly), 15.7 kHz line whine, the power-off click."""
    lev = env([(0, 0.0), (0.05, 1.0), (SH["push"], 1.0), (38.6, 1.2), (41.5, 0.0),
               (119.0, 0.0), (120.0, 0.55), (SH["horn"] - 0.5, 0.55), (SH["horn"], 0.0),
               (148.0, 0.0), (148.6, 0.35), (155.0, 0.35), (155.6, 0.0),
               (SH["return"], 0.0), (SH["return"] + 0.8, 1.0), (T_OFF, 1.0), (T_OFF + 0.12, 0.0), (DUR, 0)])
    lev = (lev * 0.065).astype(np.float32)
    common = rng.standard_normal(N, dtype=np.float32) * 0.8
    crack = ((rng.random(N) < 0.0009) * rng.standard_normal(N)).astype(np.float32) * 3.0
    crack = bp(crack, 800, 6000).astype(np.float32)
    lp = butter(1, 2500, "low", fs=SR, output="sos")
    out = np.zeros((N, 2), np.float32)
    for c in range(2):
        h = bp(rng.standard_normal(N, dtype=np.float32) * 0.6 + common, 180, 9000).astype(np.float32)
        h = (sosfilt(lp, h) * 1.4 + h * 0.35).astype(np.float32) + crack
        out[:, c] = h * lev
        del h
    # flyback whine (very quiet) whenever the TV is on screen
    wl = env([(0, 0), (0.05, 1), (37.5, 1), (38.5, 0), (119.0, 0), (119.8, 0.7), (SH["horn"] - 0.4, 0.7), (SH["horn"], 0),
              (SH["return"], 0), (SH["return"] + 0.8, 1), (T_OFF + 0.05, 1), (T_OFF + 0.45, 0), (DUR, 0)])
    out += (np.sin(2 * np.pi * 15734 * T) * wl * 0.0035).astype(np.float32)[:, None]
    # power-off: switch click + low thump + crackle of the collapsing raster
    n = int(0.6 * SR); t = np.arange(n) / SR
    click = bp(rng.standard_normal(n), 1500, 9000) * np.exp(-t / 0.004) * 1.2
    thump = np.sin(2 * np.pi * (70 - 30 * t) * t) * np.exp(-t / 0.09) * 0.5
    zap = np.sin(2 * np.pi * np.cumsum(9000 * np.exp(-t / 0.05) + 300) / SR) * np.exp(-t / 0.08) * 0.05
    sfx = click + thump + zap
    add(out, T_OFF, np.stack([sfx, sfx * 0.95], 1))
    return out


# ----------------------------------------------------------------------------- music bed
def build_bed():
    bed = np.zeros((N, 2), np.float32)
    # A: room (nostalgic) - F major colours, soft and warm
    chord(bed, 0.5, 13, [41, 53, 57, 64], 0.026, 0.25, a=4)            # Fmaj7
    chord(bed, 10, 23, [45, 52, 55, 60], 0.026, 0.25)                 # Am7
    chord(bed, 20, 32, [38, 50, 57, 64, 65], 0.026, 0.3)              # Dm9
    chord(bed, 29, 41, [46, 53, 57, 62, 65], 0.028, 0.4)              # Bbmaj7 -> into the static
    # B: the plasma - wider, higher, a lift at recombination
    chord(bed, 39, 56, [41, 48, 57, 60, 67], 0.030, 0.5)              # F(add9)
    chord(bed, 52, 66, [43, 50, 59, 62, 67], 0.030, 0.5)              # G (lydian lift)
    chord(bed, 63.5, 80, [45, 52, 61, 64, 69, 73], 0.034, 0.65, a=2.5)  # A major - light breaks free
    # C: stretching - one long chord whose top voices glide down as the light is stretched
    for j, (m, g) in enumerate(((69, -5), (73, -9), (76, -12))):
        add(bed, 78, pad_note(m, 78, 102, 0.02, a=3, r=6, bright=0.6, seed=50 + j,
                              glide=([0, L[10]["start"] - 78, L[10]["end"] - 78 + 1, 24], [0, 0, g, g])))
    chord(bed, 78, 102, [38, 45, 50], 0.028, 0.3)                       # D drone
    chord(bed, 99, 113, [38, 50, 57, 64], 0.026, 0.3)                    # Dm(add9) - cold, everywhere
    chord(bed, 109, 126, [43, 50, 58, 62], 0.026, 0.3)                   # Gm
    # D: Holmdel - calm, curious
    chord(bed, 125, 141, [41, 53, 57, 60, 64], 0.026, 0.35)             # Fmaj7
    chord(bed, 138, 152, [45, 52, 57, 60], 0.026, 0.35)                 # Am
    chord(bed, 149, 166, [46, 53, 58, 62], 0.026, 0.35)                 # Bb
    chord(bed, 163, 178, [43, 50, 58, 62, 65], 0.026, 0.4)              # Gm7
    chord(bed, 175, 194, [48, 55, 60, 64, 67], 0.030, 0.5)              # C (Nobel, warm)
    # E: the sky map - big, slow bloom up to "Us."
    chord(bed, 192, 207, [41, 48, 57, 60, 64, 69], 0.030, 0.5)
    chord(bed, 204, 218, [38, 50, 57, 62, 65, 69], 0.030, 0.55)
    chord(bed, 215, 231, [46, 53, 62, 65, 69, 72], 0.034, 0.7)
    # F: return - sparse, nostalgic
    chord(bed, 228, 246, [41, 53, 57, 64], 0.024, 0.25)
    chord(bed, 243, 256, [45, 52, 55, 60], 0.022, 0.25, r=4)
    # G: after the click - a single low, warm chord under the last lines, resolving with the title
    chord(bed, 255.5, 270, [41, 48, 57, 60, 64], 0.026, 0.3, a=3, r=6)
    # low sub swells at the big transitions
    for tc, amp in ((40.0, 0.16), (66.0, 0.14), (SH["horn"], 0.10), (SH["map"], 0.12), (227.2, 0.14)):
        n = int(12 * SR); t = np.arange(n) / SR
        e = np.where(t < 6, (t / 6) ** 2.2, np.exp(-(t - 6) / 1.8))
        s = np.sin(2 * np.pi * 36.7 * t) * e * amp
        add(bed, tc - 6, np.stack([s, s], 1))
    # shimmer for 'light breaks free' and the map
    for t0, t1, amp in ((64, 76, 0.012), (204, 228, 0.012)):
        n = int((t1 - t0) * SR); x = bp(np.random.default_rng(int(t0)).standard_normal((n, 2)), 4000, 11000)
        add(bed, t0, x * adsr(n, 4, 5)[:, None] * amp)
    # hall reverb
    n = int(4.5 * SR); tt = np.arange(n) / SR
    ir = np.stack([bp(np.random.default_rng(40 + c).standard_normal(n), 120, 7000) for c in range(2)], 1)
    ir *= np.exp(-6.91 * tt / 4.0)[:, None]; ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    ir = ir.astype(np.float32)
    for c in range(2):
        bed[:, c] = 0.65 * bed[:, c] + 0.55 * fftconvolve(bed[:, c], ir[:, c])[:N]
    bed = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), bed, axis=0)
    # the click: everything drops out for a beat, then the last chord
    gate = env([(0, 1), (T_OFF - 0.02, 1), (T_OFF + 0.05, 0.25), (255.5, 0.25), (257, 1), (268.0, 1), (269.7, 0), (DUR, 0)])
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
    sfx = tv_sfx()
    bed = build_bed()
    sf.write(vp, voice, SR, subtype="FLOAT")
    g = duck_gain(voice)
    v = voice / np.abs(voice).max() * 0.5
    b = bed / (np.abs(bed).max() + 1e-9) * 0.24
    fx_g = 1 - (1 - g) * 0.6          # hiss ducks a bit less than the music
    mix = v + b * g[:, None] + sfx * fx_g[:, None]
    sf.write(os.path.join(SCR, "bed_48k.wav"), (b + sfx).astype(np.float32), SR, subtype="FLOAT")
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
    print("SRT cues:", write_srt(os.path.join(os.path.dirname(HERE), "bigbang-tv.srt")))


if __name__ == "__main__":
    main()
