"""WHAT THEY SEE OF US (adapted from the Andromeda film's mix.py) — voice placement, processing, ambient bed, ducking, loudness, SRT.

Inputs : vo_raw/line_XX.wav + vo_raw/meta.json (from gen_voice.py, Kokoro TTS 24 kHz mono)
Outputs: voice_48k.wav, bed_48k.wav, mix_premaster.wav, andromeda_mix.wav (-14 LUFS, -1 dBTP),
         placement.json, ../andromeda.srt
Run    : /home/user/ttsenv/bin/python mix.py
"""
import os, json, subprocess, re
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, resample_poly, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.dirname(HERE)
WORK = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us"
VO = os.path.join(WORK, "vo_raw")
TL = json.load(open(os.path.join(DOC, "timeline.json")))
SR = 48000
DUR = TL["dur"]
N = int(round(SR * DUR))
rng = np.random.default_rng(31)


def P(*a):
    return os.path.join(WORK, *a)


def place_lines():
    """placement is locked by timeline.py (measured clip durations + chosen pauses); no tempo changes."""
    out = [dict(l, i=l["key"], tempo=1.0) for l in TL["lines"]]
    for a, b in zip(out, out[1:]):
        assert b["start"] - a["end"] >= 0.6 - 1e-6, (a["key"], b["key"])
    return dict(voice="am_michael", speed=0.94), out


def load_clip(key, tempo):
    x, sr = sf.read(os.path.join(VO, f"{key}.wav"))
    assert sr == 24000
    return resample_poly(x, 2, 1)


def room_ir(length=0.9, rt60=0.55, seed=5):
    n = int(SR * length)
    t = np.arange(n) / SR
    r = np.random.default_rng(seed)
    env = np.exp(-6.91 * t / rt60)
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = r.standard_normal(n)
        noise = sosfilt(butter(2, [250, 6000], "band", fs=SR, output="sos"), noise)
        ir[:, c] = noise * env
    ir[: int(0.012 * SR)] = 0          # pre-delay
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    return ir


def build_voice(placement):
    dry = np.zeros(N)
    for l in placement:
        x = load_clip(l["i"], l["tempo"])
        s = int(round(l["start"] * SR))
        dry[s:s + len(x)] += x[: N - s]
    dry = sosfilt(butter(4, 70, "high", fs=SR, output="sos"), dry)
    # gentle presence + de-mud
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    sf.write(P("voice_dry.wav"), dry, SR, subtype="FLOAT")
    # gentle compression in ffmpeg (3:1, slow-ish), slight warmth EQ
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", P("voice_dry.wav"), "-af",
                    "equalizer=f=250:t=q:w=1.0:g=-1.5,equalizer=f=3500:t=q:w=1.2:g=1.0,"
                    "acompressor=threshold=-22dB:ratio=3:attack=8:release=180:knee=6:makeup=4",
                    "-c:a", "pcm_f32le", P("voice_comp.wav")], check=True)
    v, _ = sf.read(P("voice_comp.wav"))
    ir = room_ir()
    wet = np.stack([fftconvolve(v, ir[:, c])[:N] for c in range(2)], axis=1)
    voice = v[:, None] * np.array([[1.0, 1.0]]) + 0.16 * wet
    os.remove(P("voice_dry.wav")); os.remove(P("voice_comp.wav"))
    return voice


# ------------------------------------------------------------------------------------------- bed
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sustain_curve=None):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na > 0:
        e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))
    if nr > 0:
        e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e


def add(buf, t0, sig):
    s = int(t0 * SR)
    if s < 0:
        sig = sig[-s:]; s = 0
    e = min(N, s + len(sig))
    buf[s:e] += sig[: e - s]


def pad_note(midi, t0, t1, amp, a=6.0, r=7.0, bright=0.5, nh=6, seed=0):
    """Warm detuned additive pad note, stereo, with slow 'filter' (harmonic tilt) movement."""
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    r_ = np.random.default_rng(seed + int(midi * 100) + int(t0 * 10))
    f = mtof(midi)
    out = np.zeros((n, 2))
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / r_.uniform(9, 17) + r_.uniform(0, 6.28))
    for h in range(1, nh + 1):
        if f * h > 9000:
            break
        tilt = (1.0 / h ** 1.6) * (bright * lfo + (1 - bright * lfo) * (1.0 / h)) if h > 1 else 1.0
        for c, det in enumerate((-1, 1)):
            cents = det * r_.uniform(3, 7)
            fh = f * h * 2 ** (cents / 1200)
            ph = r_.uniform(0, 6.28)
            out[:, c] += tilt * np.sin(2 * np.pi * fh * t + ph + 0.0015 * h * np.sin(2 * np.pi * 0.21 * t))
    return out * (amp * env_adsr(n, a, r))[:, None]


def drone(t0, t1, amp, base=38):  # D2 = 38
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for c in range(2):
        ph = np.random.default_rng(c + 7).uniform(0, 6.28, 6)
        f = mtof(base)
        sig = (np.sin(2 * np.pi * f * t + ph[0])
               + 0.55 * np.sin(2 * np.pi * f * 2 * 1.0007 * t + ph[1])
               + 0.35 * np.sin(2 * np.pi * mtof(base + 7) * (1.0004 if c else 0.9996) * t + ph[2])
               + 0.18 * np.sin(2 * np.pi * f * 3 * t + ph[3])
               + 0.10 * np.sin(2 * np.pi * f * 4 * 1.0011 * t + ph[4]))
        breathe = 0.8 + 0.2 * np.sin(2 * np.pi * t / 23.0 + ph[5])
        out[:, c] = sig * breathe
    return out * amp


def sub_swell(tc, amp, rise=7.0, fall=6.0, f=36.71):
    """Sub swell peaking at tc (chapter transition)."""
    n = int((rise + fall) * SR)
    t = np.arange(n) / SR
    env = np.where(t < rise, (t / rise) ** 2.2, np.exp(-(t - rise) / (fall / 3.2)))
    fm = f * (1 + 0.01 * np.exp(-((t - rise) ** 2) / 2))
    ph = 2 * np.pi * np.cumsum(fm) / SR
    sig = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
    # soft noise "air" rising into the transition
    noise = sosfilt(butter(2, [80, 900], "band", fs=SR, output="sos"), rng.standard_normal(n)) * 0.08
    s = (sig + noise * (t < rise)) * env * amp
    add_buf = np.stack([s, s], axis=1)
    return tc - rise, add_buf


def choir(t0, t1, notes, amp, vowel=(730, 1090, 2440), seed=3):
    """Formant-shaped additive 'aah' voices with vibrato — choir-like shimmer."""
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    r_ = np.random.default_rng(seed)
    for m in notes:
        for voice in range(3):
            f0 = mtof(m) * 2 ** (r_.uniform(-8, 8) / 1200)
            vib = 1 + 0.004 * np.sin(2 * np.pi * r_.uniform(4.6, 5.6) * t + r_.uniform(0, 6.28)) \
                * np.clip(t / 3.0, 0, 1)
            ph = 2 * np.pi * np.cumsum(f0 * vib) / SR
            pan = r_.uniform(0.15, 0.85)
            sig = np.zeros(n)
            for h in range(1, 40):
                fh = f0 * h
                if fh > 8000:
                    break
                w = sum(g * np.exp(-((fh - F) / bw) ** 2) for F, bw, g in
                        zip(vowel, (110, 140, 220), (1.0, 0.55, 0.25))) + 0.02 / h
                sig += w * np.sin(h * ph + r_.uniform(0, 6.28))
            sw = 0.6 + 0.4 * np.sin(2 * np.pi * t / r_.uniform(5, 11) + r_.uniform(0, 6.28))
            out[:, 0] += sig * sw * np.sqrt(1 - pan)
            out[:, 1] += sig * sw * np.sqrt(pan)
    out /= np.abs(out).max() + 1e-9
    return out * (amp * env_adsr(n, 3.5, 5.0))[:, None]


def sparkles(t0, t1, notes, density, amp, seed=11):
    """Glassy bell pings — stars igniting."""
    n = int((t1 - t0) * SR)
    out = np.zeros((n, 2))
    r_ = np.random.default_rng(seed)
    k = int(density * (t1 - t0))
    for _ in range(k):
        s = r_.integers(0, n - SR)
        L = int(SR * r_.uniform(1.5, 3.5))
        L = min(L, n - s)
        tt = np.arange(L) / SR
        f = mtof(r_.choice(notes))
        e = np.exp(-tt / r_.uniform(0.4, 1.0)) * np.clip(tt / 0.004, 0, 1)
        sig = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3)) * e
        g = r_.uniform(0.3, 1.0)
        pan = r_.uniform(0.1, 0.9)
        out[s:s + L, 0] += sig * g * np.sqrt(1 - pan)
        out[s:s + L, 1] += sig * g * np.sqrt(pan)
    # density envelope swells in the middle of the window
    tt = np.arange(n) / SR
    shape = np.sin(np.pi * np.clip(tt / (t1 - t0), 0, 1)) ** 0.8
    return out * shape[:, None] * amp


def air_noise(t0, t1, amp, lo=2000, hi=9000, seed=2):
    n = int((t1 - t0) * SR)
    r_ = np.random.default_rng(seed)
    x = r_.standard_normal((n, 2))
    sos = butter(2, [lo, hi], "band", fs=SR, output="sos")
    x = sosfilt(sos, x, axis=0)
    t = np.arange(n) / SR
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * t / 13.0)
    return x * (mod * env_adsr(n, 6, 6) * amp)[:, None]


def build_bed():
    """A-minor world. Cold open -> warm Earth -> nearby stars -> the radio-bubble crossing ->
    deep history (darker) -> the honest twist (sparse) -> the galaxy (wide choir) -> Andromeda ->
    the 66-million-light-year shell -> an open, hopeful A(add9) ending; silent under the last frames."""
    Lt = {l["key"]: l["start"] for l in TL["lines"]}
    bed = np.zeros((N, 2))
    A1 = 33
    end_t = TL["title"][1]
    dr = drone(0, end_t - 0.4, 0.10, A1 + 12)
    t = np.arange(len(dr)) / SR
    e = np.interp(t, [0, 5, Lt["light"], Lt["light"] + 4, Lt["twist"], Lt["twist"] + 3, Lt["gc"] - 1, Lt["gc"] + 3,
                      end_t - 7, end_t - 1.0, end_t - 0.4],
                  [0, 0.8, 0.8, 1.0, 1.0, 0.55, 0.55, 1.1, 1.0, 0.25, 0])
    add(bed, 0, dr * e[:, None])
    # chords: (t0, t1, notes, amp, brightness)
    C = [
        (0.0, 8.5, [57, 64, 71], 0.026, 0.35),                       # Am(add9) shimmer: cold open
        (Lt["light"] - 1, Lt["chase"] + 2, [53, 60, 64, 69], 0.030, 0.45),   # Fmaj7 - Earth
        (Lt["chase"] - 1, Lt["moon"] + 3, [48, 55, 64, 67], 0.030, 0.5),     # C
        (Lt["moon"] + 1, Lt["dot"] + 1, [50, 57, 60, 65], 0.030, 0.4),       # Dm7
        (Lt["dot"] - 1, Lt["proxima"] + 3, [45, 52, 60, 64], 0.030, 0.35),   # Am - lost in the glare
        (Lt["proxima"] + 1, Lt["vega"] + 1, [53, 57, 64, 69], 0.032, 0.5),   # Fmaj7
        (Lt["vega"] - 1, Lt["arct"] + 2, [43, 55, 62, 67], 0.032, 0.5),      # G
        (Lt["arct"], Lt["caph"] + 1, [52, 59, 64, 67, 71], 0.032, 0.55),     # Em(add9) - the Voyager echo
        (Lt["caph"] - 1, Lt["radio"] + 1, [45, 57, 60, 64], 0.030, 0.4),     # Am
        (Lt["radio"] - 0.5, Lt["dubhe"] + 1, [46, 53, 60, 65], 0.030, 0.3),  # Bb(add9) - the bubble edge, tense
        (Lt["dubhe"], Lt["polaris"] + 2, [50, 57, 62, 65], 0.030, 0.35),     # Dm
        (Lt["polaris"], Lt["betel"] + 2, [46, 53, 62, 65], 0.030, 0.35),     # Bb
        (Lt["betel"], Lt["orion"] + 1, [41, 53, 60, 65], 0.030, 0.4),        # F
        (Lt["orion"] - 0.5, Lt["deneb"] + 2, [48, 55, 64, 67], 0.030, 0.45), # C
        (Lt["deneb"], Lt["vycma"] + 2, [45, 52, 60, 64], 0.030, 0.35),       # Am
        (Lt["vycma"], Lt["twist"] + 2, [50, 57, 60, 65], 0.030, 0.3),        # Dm7
        (Lt["twist"] + 1, Lt["gc"] + 0.5, [45, 52, 59, 64], 0.022, 0.2),     # Asus2, sparse - the twist
        (Lt["gc"] - 1.0, Lt["lmc"] + 1, [41, 53, 60, 64, 71], 0.036, 0.6),   # Fmaj7(#11) - the galaxy
        (Lt["lmc"], Lt["m31"] + 1, [48, 55, 64, 67, 72], 0.034, 0.55),       # C
        (Lt["m31"], Lt["dino"] + 1, [45, 52, 60, 64], 0.032, 0.35),          # Am
        (Lt["dino"] - 0.5, Lt["end1"] + 1, [44, 51, 60, 63], 0.030, 0.25),   # Ab(+C) - the asteroid, dark
        (Lt["end1"] - 0.5, Lt["end2"] + 2.5, [41, 53, 57, 64, 69], 0.032, 0.45),  # Fmaj7
        (Lt["end2"] - 0.5, end_t - 0.6, [33, 45, 52, 59, 61, 64], 0.032, 0.35),   # A(add9) - open ending
    ]
    for k, (a_, b_, notes, amp, br) in enumerate(C):
        for j, m in enumerate(notes):
            add(bed, a_, pad_note(m, a_, b_, amp * (1.0 if m < 60 else 0.75), a=4.0, r=5.5, bright=br, seed=k * 10 + j))
    # radio-bubble crossing: beating cluster + sub swell at the crossing (~5 s into the line)
    rx = Lt["radio"] + 5.0
    add(bed, Lt["radio"], pad_note(75, Lt["radio"], rx + 6, 0.009, a=4, r=5, bright=0.2, seed=91))
    add(bed, Lt["radio"] + 1, pad_note(75.2, Lt["radio"] + 1, rx + 6, 0.008, a=4, r=5, bright=0.2, seed=92))
    for tc, amp in ((rx, 0.20), (Lt["gc"] + 0.3, 0.20), (Lt["dino"] + 1.6, 0.26), (Lt["light"] - 0.3, 0.15)):
        s0, sw = sub_swell(tc, amp); add(bed, s0, sw)
    # high air throughout, softer in the twist
    add(bed, 0, air_noise(0, DUR - 1, 0.009))
    # Arcturus callback sparkles + galaxy choir + low choir in deep history
    add(bed, Lt["arct"], sparkles(Lt["arct"], Lt["arct"] + 12, [76, 79, 83, 86, 88], 2.0, 0.022, seed=5))
    add(bed, Lt["gc"] - 1.5, choir(Lt["gc"] - 1.5, Lt["lmc"] + 2, [64, 69, 71, 76], 0.06))
    add(bed, Lt["gc"] - 1, sparkles(Lt["gc"] - 1, Lt["gc"] + 12, [76, 81, 83, 88, 91], 4.0, 0.025, seed=13))
    add(bed, Lt["orion"], choir(Lt["orion"], Lt["vycma"] + 6, [45, 52, 57], 0.03, vowel=(350, 700, 2400), seed=8))
    add(bed, Lt["end2"] - 1, choir(Lt["end2"] - 1, end_t - 0.8, [57, 64, 69, 71], 0.045, seed=21))
    s0, sw = sub_swell(TL["title"][0] + 1.5, 0.16, rise=4.0, fall=3.0); add(bed, s0, sw)
    # hall reverb
    n_ir = int(4.5 * SR); tt = np.arange(n_ir) / SR
    ir = np.stack([sosfilt(butter(2, [120, 7000], "band", fs=SR, output="sos"),
                           np.random.default_rng(c + 40).standard_normal(n_ir)) for c in range(2)], axis=1)
    ir *= np.exp(-6.91 * tt / 4.0)[:, None]; ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    wet = np.stack([fftconvolve(bed[:, c], ir[:, c])[:N] for c in range(2)], axis=1)
    bed = 0.65 * bed + 0.55 * wet
    bed = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), bed, axis=0)
    fade = np.interp(np.arange(N) / SR, [0, DUR - 3.5, DUR - 0.4, DUR], [1, 1, 0, 0])
    return bed * fade[:, None]


# ------------------------------------------------------------------------------------- ducking
def duck_gain(voice, depth_db=8.0):
    mono = np.abs(voice).mean(axis=1)
    # RMS envelope over 50 ms
    win = int(0.05 * SR)
    def movavg(x, w):   # O(N) moving average (centred), replaces np.convolve(..., "same")
        c = np.concatenate([[0.0], np.cumsum(x)])
        lo = np.clip(np.arange(len(x)) - w // 2, 0, len(x)); hi = np.clip(lo + w, 0, len(x))
        return (c[hi] - c[lo]) / w
    rms = np.sqrt(np.maximum(movavg(mono ** 2, win), 0))
    active = (rms > 0.01 * rms.max()).astype(float)
    # hold over short intra-sentence pauses (0.35 s), then smooth: fast-ish attack, slow release
    hold = int(0.35 * SR)
    active = movavg(active, hold) > 0
    g_db = -depth_db * active.astype(float)
    # look-ahead / smoothing: zero-phase low-pass (~1.2 Hz) => ~150 ms attack before speech, ~400 ms release
    sos = butter(1, 1.2, "low", fs=SR, output="sos")
    g_db = sosfiltfilt(sos, g_db)
    return 10 ** (g_db / 20)


# ----------------------------------------------------------------------------------------- SRT
def fmt_ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text, width=44):
    if len(text) <= width:
        return text
    words = text.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, a, b)
    return best[1] + "\n" + best[2]


def split_cue(text):
    """Very long lines become two cues split at a strong punctuation mark."""
    if len(text) <= 90:
        return [text]
    for sep in ("; ", ": ", " — ", ". "):
        if sep in text:
            a, b = text.split(sep, 1)
            a = a + sep.rstrip()
            return [a.strip(), b.strip()]
    return [text]


def write_srt(placement, path):
    cues = []
    for i, l in enumerate(placement):
        nxt = placement[i + 1]["start"] if i + 1 < len(placement) else DUR
        end = min(l["end"] + 0.5, nxt - 0.12)
        parts = split_cue(l["sub"])
        if len(parts) == 1:
            cues.append((l["start"], end, parts[0]))
        else:
            tot = sum(len(p) for p in parts)
            t = l["start"]
            for p in parts:
                d = (l["end"] - l["start"]) * len(p) / tot
                e = t + d if p is not parts[-1] else end
                cues.append((t, e, p))
                t = e
    with open(path, "w", encoding="utf-8") as f:
        for k, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{k}\n{fmt_ts(a)} --> {fmt_ts(b)}\n{wrap(txt)}\n\n")
    return cues


# ---------------------------------------------------------------------------------------- main
def main():
    meta, placement = place_lines()
    json.dump(dict(voice=meta["voice"], speed=meta["speed"], lines=placement), open(os.path.join(HERE, "placement.json"), "w"), indent=1)
    import sys
    if "--reuse" in sys.argv and os.path.exists(P("voice_48k.wav")) and os.path.exists(P("bed_48k.wav")):
        voice, _ = sf.read(P("voice_48k.wav")); bed, _ = sf.read(P("bed_48k.wav"))
    else:
        voice = build_voice(placement)
        sf.write(P("voice_48k.wav"), voice.astype(np.float32), SR, subtype="FLOAT")
        bed = build_bed()
        sf.write(P("bed_48k.wav"), bed.astype(np.float32), SR, subtype="FLOAT")
    g = duck_gain(voice)
    voice_n = voice / np.abs(voice).max() * 0.5
    bed_n = bed / (np.abs(bed).max() + 1e-9) * 0.27
    mix = voice_n + bed_n * g[:, None]
    mix = mix / np.abs(mix).max() * 0.7
    sf.write(P("mix_premaster.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", P("mix_premaster.wav"), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    js = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:"
          f"linear=true:print_format=summary,aresample=48000,alimiter=limit=0.84:attack=5:release=80:level=false")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", P("mix_premaster.wav"), "-af", af,
                    "-t", f"{DUR}", "-ar", "48000", "-c:a", "pcm_s24le", P("what-they-see-of-us_mix.wav")], check=True)
    cues = write_srt(placement, os.path.join(DOC, "what-they-see-of-us.srt"))
    print("SRT cues:", len(cues))


if __name__ == "__main__":
    main()
