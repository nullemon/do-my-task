"""REDO v3 kit (../REDO_V3.md) used by comet-close, galaxies-visible, solar-storm, betelgeuse-tonight.
New module; lib/voice.py and lib/audio.py are used unchanged.
- generate(LINES, out_dir): Kokoro style 0.7 am_michael + 0.3 am_onyx (blended vectors), speed 0.86, en-us, one TTS
  call per line, real word timings via lib.voice.generate (timed model) -> out_dir/<key>.wav + words.json
- build_voice(placement, vo_dir, N, tmp): place the lines, v3 post chain (pitch-only), re-aligned to the dry track
  (guards against any filter latency) -> (N, 2) at 48 kHz
- render(short_module, seg_s=5): restart-safe segment render (SCR/segs) + concat -> SCR/video_vert.mp4
"""
import os, subprocess, time
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

SPEED = 0.86
SR = 48000
POST = ("aresample=48000,rubberband=pitch=0.944:formant=preserved,highpass=f=60,equalizer=f=140:t=q:w=1:g=2.5,"
        "equalizer=f=3200:t=q:w=1.2:g=1.5,equalizer=f=7000:t=q:w=1:g=-1.5,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,aecho=0.85:0.5:35|65:0.12|0.07")


def style():
    v = np.load("/home/user/tts-models/voices-v1.0.bin")
    return (0.7 * v["am_michael"] + 0.3 * v["am_onyx"]).astype(np.float32)


def generate(LINES, out, speed=SPEED):
    from .voice import generate as gen
    gen(LINES, out, speed, voice=style())


def build_voice(placement, vo_dir, N, tmp):
    pad = SR                                                     # room for the echo tail, trimmed below
    dry = np.zeros(N + pad)
    for l in placement:
        x, sr = sf.read(os.path.join(vo_dir, f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(len(dry) - s, 0)]
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    a, b = os.path.join(tmp, "v3k_d.wav"), os.path.join(tmp, "v3k_c.wav")
    sf.write(a, dry, SR, subtype="FLOAT")
    subprocess.run(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-i", a, "-af", POST, "-ar", str(SR), "-ac", "1",
                    "-c:a", "pcm_f32le", b], check=True)
    v, _ = sf.read(b); os.remove(a); os.remove(b)
    if v.ndim > 1: v = v.mean(1)
    k = 240; n = min(len(v), len(dry)) // k                       # envelope cross-correlation, 5 ms steps, 0..200 ms
    E1 = np.abs(dry[: n * k]).reshape(n, k).mean(1); E2 = np.abs(v[: n * k]).reshape(n, k).mean(1)
    lag = max(range(0, 41), key=lambda L: float(np.dot(E1[: n - L], E2[L:n])))
    if lag: v = v[lag * k:]
    print(f"voice post-chain lag {lag * k / SR * 1000:.0f} ms (removed)")
    v = v[:N] if len(v) >= N else np.pad(v, (0, N - len(v)))
    return v[:, None] * np.ones((1, 2))


def nframes(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets", "-of", "csv=p=0", p], capture_output=True, text=True)
    try: return int(r.stdout.strip())
    except ValueError: return -1


def render(S, seg_s=5.0, crf=16):
    """S: the Short's module (SCR, DUR, FPS, Scene). Finished segments are kept; a restart redoes one segment."""
    from .post import Encoder
    seg_dir = os.path.join(S.SCR, "segs"); os.makedirs(seg_dir, exist_ok=True)
    n = int(round(S.DUR * S.FPS)); step = int(round(seg_s * S.FPS)); parts = []; sc = None; T0 = time.time()
    for k, f0 in enumerate(range(0, n, step)):
        f1 = min(f0 + step, n); p = os.path.join(seg_dir, f"seg_{k:03d}_{f0}_{f1}.mp4"); parts.append(p)
        if os.path.exists(p) and nframes(p) == f1 - f0: continue
        if sc is None: sc = S.Scene()
        tmp = p + ".part.mp4"; enc = Encoder(tmp, sc.W, sc.H, S.FPS, crf=crf)
        for i in range(f0, f1): enc.write(sc.frame(i / S.FPS))
        enc.close(); os.replace(tmp, p)
        print(f"segment {k} frames {f0}-{f1}/{n}  {time.time() - T0:.0f}s", flush=True)
    lst = os.path.join(seg_dir, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    out = os.path.join(S.SCR, "video_vert.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", out], check=True)
    print("video", out, "frames", nframes(out), "expected", n, flush=True)


def measure(p):
    """-> (integrated LUFS, true peak dBTP) via ebur128"""
    import re
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    return I, tp


def finalize(raw, out, I=-14.0, TP=-1.0):
    """two-pass loudnorm (lib.audio.loudnorm); if the true peak still exceeds TP, an oversampled limiter at TP-0.9 dB"""
    from .audio import loudnorm
    loudnorm(raw, out, I, TP); li, tp = measure(out)
    if tp > TP:
        tmp = out + ".lim.wav"; os.replace(out, tmp)
        lim = 10 ** ((TP - 0.9) / 20)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", f"aresample=192000,alimiter=limit={lim:.4f}:level=false:attack=1:release=60,"
                        "aresample=48000", "-c:a", "pcm_s16le", out], check=True); os.remove(tmp)
        li, tp = measure(out)
    print(f"final mix {li:.1f} LUFS, {tp:.1f} dBTP")
