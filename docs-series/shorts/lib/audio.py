"""Audio for Shorts: place voice lines, voice chain (HPF, EQ, compression, small room), sound-design primitives
(drone, riser, sub thump, clock ticks, icy shimmer, low hit), ducking, two-pass loudnorm to -14 LUFS / -1 dBTP, SRT.
"""
import os, json, subprocess, math
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly, fftconvolve

SR = 48000


def place(words_json, lead=0.25):
    """-> list of lines with absolute start/end and absolute word times"""
    meta = json.load(open(words_json))
    t = lead; out = []
    for l in meta["lines"]:
        ws = [dict(w, t0=round(w["t0"] + t, 3), t1=round(w["t1"] + t, 3)) for w in l["words"]]
        out.append(dict(key=l["key"], start=round(t, 3), end=round(t + l["dur"], 3), words=ws))
        t += l["dur"] + l["pause"]
    return out


def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x, axis=0)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], "band", fs=SR, output="sos"), x, axis=0)


def room_ir(length=0.9, rt60=0.5, seed=5):
    n = int(SR * length); t = np.arange(n) / SR; r = np.random.default_rng(seed)
    ir = np.stack([bp(r.standard_normal(n), 250, 6000) * np.exp(-6.91 * t / rt60) for _ in range(2)], 1)
    ir[: int(0.012 * SR)] = 0
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def build_voice(placement, vo_dir, N, tmp):
    dry = np.zeros(N)
    for l in placement:
        x, sr = sf.read(os.path.join(vo_dir, f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: N - s]
    dry = hp(dry, 70, 4); dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    a, b = os.path.join(tmp, "vd.wav"), os.path.join(tmp, "vc.wav")
    sf.write(a, dry, SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-af",
                    "equalizer=f=220:t=q:w=1.0:g=-1.5,equalizer=f=3200:t=q:w=1.2:g=1.5,equalizer=f=110:t=q:w=0.8:g=1.0,"
                    "acompressor=threshold=-22dB:ratio=3:attack=6:release=160:knee=6:makeup=4", "-c:a", "pcm_f32le", b], check=True)
    v, _ = sf.read(b); os.remove(a); os.remove(b)
    v = v[:N] if len(v) >= N else np.pad(v, (0, N - len(v)))
    ir = room_ir()
    wet = np.stack([fftconvolve(v, ir[:, c])[:N] for c in range(2)], 1)
    return v[:, None] * np.ones((1, 2)) + 0.10 * wet


# ----------------------------------------------------------------------------- sound design primitives (stereo)
def env(N, pts):
    """piecewise-linear envelope from [(t_sec, gain), ...]"""
    t = np.arange(N) / SR; ts, gs = zip(*pts); return np.interp(t, ts, gs)


def drone(N, root=43.65, seed=1, bright=0.25):
    """slowly beating low pad: detuned partials + filtered noise air"""
    t = np.arange(N) / SR; r = np.random.default_rng(seed); out = np.zeros((N, 2))
    for k, (mult, amp) in enumerate(((1, 1.0), (1.5, 0.35), (2, 0.45), (3, 0.16), (4, 0.10 * bright * 3), (6, 0.04 * bright * 3))):
        for c in range(2):
            det = 1 + r.uniform(-0.003, 0.003)
            lfo = 1 + 0.25 * np.sin(2 * np.pi * r.uniform(0.03, 0.09) * t + r.uniform(0, 6.28))
            out[:, c] += amp * lfo * np.sin(2 * np.pi * root * mult * det * t + r.uniform(0, 6.28))
    air = np.stack([bp(r.standard_normal(N), 300, 1800) for _ in range(2)], 1) * 0.10
    return (out * 0.18 + air * bright)


def riser(N, t0, t1, seed=2):
    """noise + rising tone swell ending at t1 (cut hard)"""
    out = np.zeros((N, 2)); a, b = int(t0 * SR), int(t1 * SR); n = b - a
    if n <= 0: return out
    u = np.linspace(0, 1, n); r = np.random.default_rng(seed)
    nz = np.stack([r.standard_normal(n) for _ in range(2)], 1)
    nz = bp(nz, 800, 6000) * (u ** 2.5)[:, None] * 0.35
    f = 110 * 2 ** (u * 2.0); ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.4 * np.sin(2 * ph)) * (u ** 3) * 0.25
    out[a:b] = nz + tone[:, None]
    return out


def thump(N, t0, size=1.0):
    """sub-bass impact: 70->28 Hz sine sweep + click + low noise tail"""
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(3.5 * SR), N - a)
    if n <= 0: return out
    t = np.arange(n) / SR
    f = 28 + 48 * np.exp(-t / 0.09); ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.9) * 1.0
    click = hp(np.random.default_rng(3).standard_normal(n), 1500) * np.exp(-t / 0.006) * 0.25
    tail = lp(np.random.default_rng(4).standard_normal(n), 200) * np.exp(-t / 1.2) * 0.4
    x = (body + click + tail) * size
    out[a:a + n] = np.stack([x, x * 0.97], 1)
    return out


def ticks(N, t0, t1, rate=4.0, gain=0.12, accel=1.0):
    """clock ticks between t0 and t1 (rate per second, optionally accelerating)"""
    out = np.zeros((N, 2)); tt = t0; k = 0; r = np.random.default_rng(9)
    tk = np.arange(int(0.03 * SR)) / SR
    click = (np.sin(2 * np.pi * 3200 * tk) * 0.6 + hp(r.standard_normal(len(tk)), 2000) * 0.5) * np.exp(-tk / 0.004)
    while tt < t1:
        a = int(tt * SR)
        if a + len(click) < N:
            pan = 0.6 if k % 2 else 0.4
            g = gain * (0.85 if k % 2 else 1.0)
            out[a:a + len(click), 0] += click * g * (1 - pan) * 2; out[a:a + len(click), 1] += click * g * pan * 2
        u = (tt - t0) / max(t1 - t0, 1e-3)
        tt += 1.0 / (rate * (1 + (accel - 1) * u)); k += 1
    return out


def shimmer(N, t0, t1, seed=5, gain=0.12):
    """icy shimmer: random high bell grains (inharmonic partials) + airy high noise, fading in"""
    out = np.zeros((N, 2)); r = np.random.default_rng(seed)
    a, b = int(t0 * SR), min(N, int(t1 * SR))
    nz = np.stack([hp(r.standard_normal(b - a), 6000) for _ in range(2)], 1)
    u = np.linspace(0, 1, b - a)[:, None]
    out[a:b] += nz * 0.04 * np.clip(u * 3, 0, 1) * (1 - np.clip((u - 0.92) / 0.08, 0, 1))
    n_gr = int((t1 - t0) * 9)
    for _ in range(n_gr):
        tg = r.uniform(t0, t1); f0 = r.choice([2093, 2349, 2637, 3136, 3520, 4186, 4699]) * r.uniform(0.997, 1.003)
        n = int(1.4 * SR); s = int(tg * SR)
        if s + n >= N: continue
        tt = np.arange(n) / SR
        g = sum(p * np.sin(2 * np.pi * f0 * m * tt) for m, p in ((1, 1), (2.76, 0.4), (5.4, 0.2))) * np.exp(-tt / r.uniform(0.25, 0.6))
        g *= (1 - np.exp(-tt / 0.002)) * r.uniform(0.3, 1.0) * ((tg - t0) / (t1 - t0) * 0.7 + 0.3)
        pan = r.uniform(0.15, 0.85)
        out[s:s + n, 0] += g * (1 - pan); out[s:s + n, 1] += g * pan
    return out * gain


def hit(N, t0, gain=0.5, root=55.0):
    """deep tonal 'boom' with long reverb tail (ending accent)"""
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(int(6 * SR), N - a)
    if n <= 0: return out
    t = np.arange(n) / SR
    x = sum(p * np.sin(2 * np.pi * root * m * t) * np.exp(-t / d) for m, p, d in ((1, 1.0, 2.5), (2, 0.4, 1.6), (3, 0.2, 1.0), (4.2, 0.1, 0.6)))
    x *= (1 - np.exp(-t / 0.004)) * gain
    ir = room_ir(3.0, 2.5, 8)
    w = np.stack([fftconvolve(x, ir[:, c])[:n] for c in range(2)], 1)
    out[a:a + n] = x[:, None] * 0.7 + w * 0.6
    return out


def duck(bed, voice, depth=0.5, att=0.03, rel=0.35):
    e = np.abs(voice).max(1); e = lp(e, 8, 1); e = e / (e.max() + 1e-9)
    g = 1 - depth * np.clip(e * 3, 0, 1)
    return bed * g[:, None]


def loudnorm(inp, out, I=-14.0, TP=-1.0):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", inp, "-af", f"loudnorm=I={I}:TP={TP}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rfind("{"):])
    af = (f"loudnorm=I={I}:TP={TP}:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
          f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", inp, "-af", af + ",aresample=48000", "-c:a", "pcm_s16le", out], check=True)


def srt_time(s):
    ms = int(round(s * 1000)); return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path, placement, pieces_of, max_words=7):
    """subtitle chunks of <= max_words pieces, split at punctuation, timed from word timings.
    pieces_of(key) -> list of subtitle strings aligned 1:1 with that line's caption words"""
    items = []
    for l in placement:
        pcs = pieces_of(l["key"]); ws = l["words"]; assert len(pcs) == len(ws), l["key"]
        cur = []
        for i, w in enumerate(pcs):
            cur.append(i)
            if len(cur) >= max_words or (w[-1] in ".?!" and len(cur) >= 2) or (w[-1] == "," and len(cur) >= 4) or i == len(pcs) - 1:
                items.append((ws[cur[0]]["t0"], ws[cur[-1]]["t1"] + 0.15, " ".join(pcs[j] for j in cur))); cur = []
    with open(path, "w") as f:
        for k, (a, b, s) in enumerate(items, 1):
            b = min(b, items[k][0] - 0.02) if k < len(items) else b
            f.write(f"{k}\n{srt_time(a)} --> {srt_time(b)}\n{s}\n\n")
