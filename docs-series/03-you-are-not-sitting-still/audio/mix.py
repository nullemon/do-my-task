"""03 You Are Not Sitting Still (adapted from andromeda-doc/audio/mix.py) — voice placement, processing, ambient bed, ducking, loudness, SRT.

Inputs : vo_raw/line_XX.wav + vo_raw/meta.json (from gen_voice.py, Kokoro TTS 24 kHz mono)
Outputs (scratchpad audio/): voice_48k.wav, bed_48k.wav, mix_premaster.wav, mix.wav (-14 LUFS, <= -1 dBTP);
         placement.json, ../you-are-not-sitting-still.srt
Run    : /home/user/ttsenv/bin/python mix.py
"""
import os, json, subprocess, re
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt, resample_poly, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 270.0
S = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still"
VO = S + "/vo_raw"
AOUT = S + "/audio"
os.makedirs(AOUT, exist_ok=True)
N = int(SR * DUR)
rng = np.random.default_rng(31)
MIN_GAP = 0.6       # seconds of silence required between consecutive lines
MAX_TEMPO = 1.08
MAX_NUDGE = 1.0


def P(*a):
    return os.path.join(HERE, *a)


# ----------------------------------------------------------------------------------------- voice
def place_lines():
    """Timeline is already locked to the measured clips by timeline.py (no tempo changes, no nudges)."""
    tl = json.load(open(P("timeline.json")))
    meta = json.load(open(os.path.join(VO, "meta.json")))
    out = []
    for l in tl["lines"]:
        out.append(dict(id=l["id"], start=l["start"], end=l["end"], dur=l["dur"], text=l["text"], tempo=1.0))
    for x, y in zip(out, out[1:]):
        assert y["start"] - x["end"] >= MIN_GAP - 1e-6, (x, y)
    return dict(voice="am_michael", speed=0.94), out


def load_clip(lid, tempo):
    x, sr = sf.read(os.path.join(VO, lid + ".wav"))
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
        x = load_clip(l["id"], l["tempo"])
        s = int(round(l["start"] * SR))
        dry[s:s + len(x)] += x[: N - s]
    dry = sosfilt(butter(4, 70, "high", fs=SR, output="sos"), dry)
    # gentle presence + de-mud
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    sf.write(os.path.join(AOUT, "voice_dry.wav"), dry, SR, subtype="FLOAT")
    # gentle compression in ffmpeg (3:1, slow-ish), slight warmth EQ
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(AOUT, "voice_dry.wav"), "-af",
                    "equalizer=f=250:t=q:w=1.0:g=-1.5,equalizer=f=3500:t=q:w=1.2:g=1.0,"
                    "acompressor=threshold=-22dB:ratio=3:attack=8:release=180:knee=6:makeup=4",
                    "-c:a", "pcm_f32le", os.path.join(AOUT, "voice_comp.wav")], check=True)
    v, _ = sf.read(os.path.join(AOUT, "voice_comp.wav"))
    ir = room_ir()
    wet = np.stack([fftconvolve(v, ir[:, c])[:N] for c in range(2)], axis=1)
    voice = v[:, None] * np.array([[1.0, 1.0]]) + 0.16 * wet
    os.remove(os.path.join(AOUT, "voice_dry.wav")); os.remove(os.path.join(AOUT, "voice_comp.wav"))
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
    """Ambient bed for 03: intimate in the room, one more layer for every level we pull back through."""
    bed = np.zeros((N, 2))
    sc = json.load(open(P("timeline.json")))["scenes"]
    R, E, O, HX, G, C, WY, EN = (sc[k][0] for k in ("room", "earth", "orbit", "helix", "galaxy", "cosmos", "why", "end"))
    D2 = 38
    dr = drone(0, 269.5, 0.10, D2)
    t = np.arange(len(dr)) / SR
    e = np.interp(t, [0, 6, WY - 2, WY + 2, EN, 262, 269.5], [0, 1, 1.15, 0.55, 0.7, 0.9, 0])
    add(bed, 0, dr * e[:, None])
    chords = [  # (t0, t1, notes, amp, brightness)
        (0.5, E + 3, [57, 64, 69], 0.022, 0.2),               # room: thin A3 E4 A4 (Dm colour without the root yet)
        (8, E + 3, [50, 62], 0.020, 0.2),                     # D3 D4 enters under "well over a million"
        (E - 1, E + 18, [50, 57, 62, 65], 0.030, 0.35),       # Earth: Dm
        (E + 14, O + 3, [46, 53, 62, 65, 69], 0.030, 0.4),    # Bbmaj7
        (O - 1, HX + 4, [41, 53, 57, 60, 65], 0.032, 0.45),   # orbit: F (opening up)
        (HX, HX + 20, [48, 55, 60, 64, 67], 0.032, 0.5),      # helix: C add9-ish (C3 G3 C4 E4 G4)
        (HX + 16, G + 3, [46, 53, 60, 62, 69], 0.032, 0.5),   # Bb(add9)
        (G - 1, G + 22, [43, 50, 58, 62, 69], 0.034, 0.5),    # galaxy: Gm9
        (G + 18, C + 3, [39, 51, 58, 62, 67], 0.034, 0.45),   # Ebmaj7
        (C - 1, C + 24, [46, 53, 58, 62, 65, 72], 0.034, 0.55),  # cosmos: Bb wide
        (C + 20, C + 40, [44, 51, 60, 63, 67, 72], 0.034, 0.5),  # Ab add9 — vast, unresolved
        (C + 36, WY + 3, [45, 52, 61, 64, 69], 0.032, 0.4),   # A (dominant) — we are moving
        (WY - 1, WY + 22, [50, 57, 64, 65], 0.024, 0.25),     # why: intimate Dm(add9)
        (WY + 18, EN + 3, [46, 57, 62, 65], 0.024, 0.25),     # Bb/D
        (EN - 1, 262.0, [43, 50, 58, 62, 67], 0.028, 0.3),    # end: Gm(add9) under the count
        (256.0, 269.5, [38, 50, 57, 62, 66, 69], 0.032, 0.35),  # D major lift: "never been still"
    ]
    for k, (a, b, notes, amp, br) in enumerate(chords):
        for j, m in enumerate(notes):
            add(bed, a, pad_note(m, a, b, amp * (1.0 if m < 60 else 0.75), a=4.5, r=6.0, bright=br, seed=k * 10 + j))
    # gentle "layer per level": a high shimmer that thickens with each level of the pull-back
    add(bed, 0, air_noise(0, 120, 0.008))
    add(bed, 120, air_noise(120, 205, 0.012, seed=4))
    add(bed, C + 6, choir(C + 6, WY + 2, [62, 69, 74, 77], 0.045))
    add(bed, G + 4, sparkles(G + 4, G + 34, [74, 77, 81, 86], 0.6, 0.010))
    # sub swells at each pull-back
    for tc, amp in ((E, 0.16), (O, 0.17), (G, 0.20), (C, 0.24), (EN, 0.14)):
        s0, sw = sub_swell(tc, amp)
        add(bed, s0, sw)
    # --- big hall reverb on the bed
    n_ir = int(4.5 * SR)
    tt = np.arange(n_ir) / SR
    ir = np.stack([sosfilt(butter(2, [120, 7000], "band", fs=SR, output="sos"),
                           np.random.default_rng(c + 40).standard_normal(n_ir)) for c in range(2)], axis=1)
    ir *= np.exp(-6.91 * tt / 4.0)[:, None]
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    wet = np.stack([fftconvolve(bed[:, c], ir[:, c])[:N] for c in range(2)], axis=1)
    bed = 0.65 * bed + 0.55 * wet
    bed = sosfilt(butter(2, 28, "high", fs=SR, output="sos"), bed, axis=0)

    # hard silence tail: fade to zero by 239.6
    fade = np.interp(np.arange(N) / SR, [0, 266.0, 269.6, 270], [1, 1, 0, 0])
    bed *= fade[:, None]
    return bed


# ------------------------------------------------------------------------------------- ducking
def movsum(x, w):
    """centred moving sum (same length) via cumsum — O(N), replaces np.convolve(x, ones(w), 'same')."""
    c = np.concatenate([[0.0], np.cumsum(x)])
    i = np.arange(len(x))
    lo = np.clip(i - w // 2, 0, len(x)); hi = np.clip(i - w // 2 + w, 0, len(x))
    return c[hi] - c[lo]


def duck_gain(voice, depth_db=8.0):
    mono = np.abs(voice).mean(axis=1)
    # RMS envelope over 50 ms
    win = int(0.05 * SR)
    rms = np.sqrt(np.maximum(movsum(mono ** 2, win) / win, 0))
    active = (rms > 0.01 * rms.max()).astype(float)
    # hold over short intra-sentence pauses (0.35 s), then smooth: fast-ish attack, slow release
    hold = int(0.35 * SR)
    active = movsum(active, hold) > 0.5
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
        parts = split_cue(l["text"])
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
    json.dump(dict(voice=meta["voice"], speed=meta["speed"], lines=placement), open(P("placement.json"), "w"), indent=1)
    if os.environ.get("REUSE_STEMS") and os.path.exists(os.path.join(AOUT, "bed_48k.wav")):
        voice, _ = sf.read(os.path.join(AOUT, "voice_48k.wav")); bed, _ = sf.read(os.path.join(AOUT, "bed_48k.wav"))
    else:
        voice = build_voice(placement)
        sf.write(os.path.join(AOUT, "voice_48k.wav"), voice.astype(np.float32), SR, subtype="FLOAT")
        bed = build_bed()
        sf.write(os.path.join(AOUT, "bed_48k.wav"), bed.astype(np.float32), SR, subtype="FLOAT")
    g = duck_gain(voice)
    voice_n = voice / np.abs(voice).max() * 0.5
    bed_n = bed / (np.abs(bed).max() + 1e-9) * 0.26
    mix = voice_n + bed_n * g[:, None]
    mix = mix / np.abs(mix).max() * 0.7
    pre = os.path.join(AOUT, "mix_premaster.wav")
    sf.write(pre, mix.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:"
          f"linear=true:print_format=summary,aresample=48000,alimiter=limit=0.84:attack=5:release=80:level=false")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af", af, "-t", str(DUR), "-ar", "48000",
                    "-c:a", "pcm_s24le", os.path.join(AOUT, "mix.wav")], check=True)
    cues = write_srt(placement, os.path.join(os.path.dirname(HERE), "you-are-not-sitting-still.srt"))
    print("SRT cues:", len(cues))


if __name__ == "__main__":
    main()
