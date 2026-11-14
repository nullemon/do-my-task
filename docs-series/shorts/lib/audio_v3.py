"""REDO v3 voice track: place the per-phrase wavs, then the v3 post chain (pitch-only, so word timings stay valid).
build_voice() has the same signature as lib.audio.build_voice and returns an (N, 2) array at 48 kHz."""
import os, subprocess
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from .audio import SR, hp

CHAIN = ("aresample=48000,rubberband=pitch=0.944:formant=preserved,highpass=f=60,equalizer=f=140:t=q:w=1:g=2.5,"
         "equalizer=f=3200:t=q:w=1.2:g=1.5,equalizer=f=7000:t=q:w=1:g=-1.5,"
         "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150,aecho=0.85:0.5:35|65:0.12|0.07")


def build_voice(placement, vo_dir, N, tmp):
    dry = np.zeros(N)
    for l in placement:
        x, sr = sf.read(os.path.join(vo_dir, f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(0, N - s)]
    dry = hp(dry, 40, 2); dry = dry / (np.abs(dry).max() + 1e-9) * 0.7
    a, b = os.path.join(tmp, "vd.wav"), os.path.join(tmp, "vc.wav")
    sf.write(a, dry, SR, subtype="FLOAT")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a, "-af", CHAIN, "-c:a", "pcm_f32le", b], check=True)
    v, _ = sf.read(b); os.remove(a); os.remove(b)
    if v.ndim > 1: v = v.mean(1)
    v = v[:N] if len(v) >= N else np.pad(v, (0, N - len(v)))
    v = v / (np.abs(v).max() + 1e-9) * 0.7
    return v[:, None] * np.ones((1, 2))
