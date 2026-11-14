"""REDO v3 voice helpers (../REDO_V3.md) used by moon-ratios, sunset-mirage, while-you-watch, other-moons, gamma-ray-eyes.
New module; lib/voice.py and lib/audio.py are used unchanged.
  generate(LINES, out_dir): Kokoro style 0.7 am_michael + 0.3 am_onyx (blended vectors), speed 0.86, en-us, one TTS call
      per line, real word timings via lib.voice.generate (timed model) -> out_dir/<key>.wav + words.json
  build_voice(placement, vo_dir, N, tmp): place the lines, v3 post chain (pitch-only, so the timings stay valid),
      re-aligned to the dry track against any filter latency -> (N, 2) at 48 kHz
"""
import os, subprocess
import numpy as np, soundfile as sf
from scipy.signal import resample_poly, fftconvolve
from . import voice as V

SPEED = 0.86
SR = 48000
POST = ("aresample=48000,rubberband=pitch=0.944:formant=preserved,highpass=f=60,equalizer=f=140:t=q:w=1:g=2.5,"
        "equalizer=f=3200:t=q:w=1.2:g=1.5,equalizer=f=7000:t=q:w=1:g=-1.5,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,aecho=0.85:0.5:35|65:0.12|0.07")


def style():
    from kokoro_onnx import Kokoro
    k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
    return (0.7 * k.get_voice_style("am_michael") + 0.3 * k.get_voice_style("am_onyx")).astype(np.float32)


def generate(LINES, out, speed=SPEED):
    V.generate(LINES, out, speed, voice=style())


def build_voice(placement, vo_dir, N, tmp):
    dry = np.zeros(N)
    for l in placement:
        x, sr = sf.read(os.path.join(vo_dir, f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(0, N - s)]
    dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    a, b = os.path.join(tmp, "q5vd.wav"), os.path.join(tmp, "q5vc.wav")
    sf.write(a, dry, SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-af", POST, "-c:a", "pcm_f32le", b], check=True)
    v, _ = sf.read(b); os.remove(a); os.remove(b)
    if v.ndim > 1: v = v.mean(1)
    n = min(len(v), len(dry), SR * 20)
    ev, ed = np.abs(v[:n:8]), np.abs(dry[:n:8])
    c = fftconvolve(ev - ev.mean(), (ed - ed.mean())[::-1], "full")
    lag = (int(np.argmax(c)) - (len(ed) - 1)) * 8
    print("voice post-chain lag", lag, "samples", flush=True)
    if 0 < lag < SR // 5: v = v[lag:]
    v = v[:N] if len(v) >= N else np.pad(v, (0, N - len(v)))
    return v[:, None] * np.ones((1, 2))


def render_segments(S, chunk=150, scene=None):
    """restart-safe render of a Short module S (needs SCR, DUR, FPS, Scene(True).frame(t)): SCR/segs/seg_<a>_<b>.mp4,
    each finalised on its own (finished ones are skipped on a re-run), then concatenated -> SCR/video_vert.mp4"""
    import time
    from .post import Encoder
    n = int(round(S.DUR * S.FPS)); d = os.path.join(S.SCR, "segs"); os.makedirs(d, exist_ok=True)
    sc = scene; lst = []
    for a in range(0, n, chunk):
        b = min(a + chunk, n); f = os.path.join(d, f"seg_{a:05d}_{b:05d}.mp4"); lst.append(f)
        if os.path.exists(f): continue
        sc = sc or S.Scene(True); tmp = f + ".part.mp4"; t0 = time.time()
        enc = Encoder(tmp, sc.L.W, sc.L.H, S.FPS, crf=16)
        for i in range(a, b): enc.write(sc.frame(i / S.FPS))
        enc.close(); os.replace(tmp, f); print(f"seg {a}-{b}/{n} {time.time() - t0:.0f}s", flush=True)
    with open(os.path.join(d, "list.txt"), "w") as fh:
        for f in lst: fh.write(f"file '{f}'\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(d, "list.txt"), "-c", "copy",
                    os.path.join(S.SCR, "video_vert.mp4")], check=True)
    print("done", n, flush=True)
