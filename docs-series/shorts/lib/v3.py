"""REDO v3 helpers (see ../REDO_V3.md). New module: lib/voice.py and lib/audio.py are used unchanged.
- generate_v3(LINES, out_dir): Kokoro, voice style 0.7 am_michael + 0.3 am_onyx (blended vectors), speed 0.86, en-us,
  one TTS call per line, real word timings via lib.voice.generate (timed model) -> out_dir/<key>.wav + words.json
- build_voice_v3(placement, vo_dir, N, tmp): place the lines, apply the v3 post chain (pitch-only, timings stay valid)
- render_segments(frame_fn, W, H, fps, dur, seg_dir, final): segment-wise render (restart-safe) + concat
"""
import os, subprocess
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

SPEED = 0.86
POST = ("aresample=48000,rubberband=pitch=0.944:formant=preserved,highpass=f=60,equalizer=f=140:t=q:w=1:g=2.5,"
        "equalizer=f=3200:t=q:w=1.2:g=1.5,equalizer=f=7000:t=q:w=1:g=-1.5,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,aecho=0.85:0.5:35|65:0.12|0.07")


def style():
    from kokoro_onnx import Kokoro
    k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
    return (0.7 * k.get_voice_style("am_michael") + 0.3 * k.get_voice_style("am_onyx")).astype(np.float32)


def generate_v3(LINES, out):
    from .voice import generate
    generate(LINES, out, SPEED, voice=style())


def build_voice_v3(placement, vo_dir, N, tmp, SR=48000):
    dry = np.zeros(N)
    for l in placement:
        x, sr = sf.read(os.path.join(vo_dir, f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(N - s, 0)]
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    a, b = os.path.join(tmp, "v3d.wav"), os.path.join(tmp, "v3c.wav")
    sf.write(a, dry, SR, subtype="FLOAT")
    subprocess.run(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-i", a, "-af", POST, "-ar", str(SR), "-ac", "1",
                    "-c:a", "pcm_f32le", b], check=True)
    v, _ = sf.read(b); os.remove(a); os.remove(b)
    v = v[:N] if len(v) >= N else np.pad(v, (0, N - len(v)))
    return v[:, None] * np.ones((1, 2))


def render_segments(frame_fn, W, H, fps, dur, seg_dir, final, seg_s=6.0, crf=17):
    """render [0, dur) in segments of seg_s seconds; finished segments are kept (restart-safe); concat -> final"""
    from .post import Encoder
    import time
    os.makedirs(seg_dir, exist_ok=True)
    n = int(round(dur * fps)); step = int(round(seg_s * fps)); parts = []
    for k, f0 in enumerate(range(0, n, step)):
        f1 = min(f0 + step, n); p = os.path.join(seg_dir, f"seg_{k:03d}_{f0}_{f1}.mp4"); parts.append(p)
        if os.path.exists(p): continue
        tmp = p + ".part.mp4"; enc = Encoder(tmp, W, H, fps, crf=crf); t0 = time.time()
        for i in range(f0, f1): enc.write(frame_fn(i / fps))
        enc.close(); os.replace(tmp, p)
        print(f"segment {k} frames {f0}-{f1}/{n}  {time.time() - t0:.0f}s", flush=True)
    lst = os.path.join(seg_dir, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    "-movflags", "+faststart", final], check=True)
    print("done", final)


def _measure(path):
    import json
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rfind("{"):]); return float(js["input_i"]), float(js["input_tp"])


def finalize(raw, out, I=-14.0, TP=-1.0):
    """gain to the target loudness + 4x-oversampled peak limiter, iterated -> 48 kHz 16-bit. The limiter sits 1 dB under TP
    so the AAC encode still stays under TP."""
    g = 0.0
    for _ in range(6):
        i0, _tp = _measure(raw) if g == 0.0 else (None, None)
        if g == 0.0: g = I - i0
        af = (f"volume={g:.2f}dB,aresample=192000,alimiter=limit={10 ** ((TP - 1.0) / 20):.4f}:attack=2:release=60:level=false,"
              "aresample=48000")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-c:a", "pcm_s16le", out], check=True)
        i1, tp1 = _measure(out)
        print(f"  finalize: gain {g:+.2f} dB -> {i1:.2f} LUFS, {tp1:.2f} dBTP", flush=True)
        if abs(i1 - I) <= 0.1 and tp1 <= TP + 0.05: return
        g += 1.7 * (I - i1)
