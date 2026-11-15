"""Clean sound (BATCH4 rules): the voice (lib.mix_clean.clean_voice: no echo, no reverb, no pitch shift) over the
module's soft pad, with its gentle whoosh at each swap -- nothing else. lib.mix_clean.mix -> -14 LUFS / -1.5 dBTP.
Also measures the music+whoosh bed alone (voice muted, same gains as inside mix()) against the full mix, and writes the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py"""
import os, sys, re, subprocess, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
from scipy.signal import resample_poly, fftconvolve
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib import mix_clean as MC

NAME = os.path.basename(os.path.dirname(HERE))
OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = MC.SR
KEY = getattr(S, "MUSIC_KEY", "D")



def lufs(x):
    p = os.path.join(OUT, "_m.wav"); sf.write(p, x.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    os.remove(p)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])


def dry_track(N):
    dry = np.zeros(N)
    for l in S.PL:
        x, sr = sf.read(os.path.join(S.SCR, "vo", f"{l['key']}.wav")); x = resample_poly(x, SR // 8000, sr // 8000)
        s = int(round(l["start"] * SR)); dry[s:s + len(x)] += x[: max(0, N - s)]
    return dry / (np.abs(dry).max() + 1e-9) * 0.7


def bed_stems(voice, dur, swaps):
    """the same stems and gains mix_clean.mix() builds, before its final loudnorm/limiter"""
    n = int(round(dur * SR)); v = np.zeros(n); v[: min(n, len(voice))] = voice[:n]
    v = v / (np.sqrt(np.mean(v[np.abs(v) > 1e-4] ** 2)) + 1e-9) * 0.1
    pad = MC._ff(MC._pad(n, KEY), "lowpass=f=1800,highpass=f=80"); pad = pad.mean(1) if pad.ndim > 1 else pad
    pad = pad[:n] / (np.sqrt(np.mean(pad ** 2)) + 1e-9) * 0.1 * 10 ** (-26 / 20)
    env = fftconvolve((np.abs(v) > 0.01).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
    pad *= 10 ** (-8 * np.clip(env * 4, 0, 1) / 20)
    wh = np.zeros(n)
    if swaps:
        w = MC._ff(MC._whoosh(n, swaps), "bandpass=f=1800:w=2500,lowpass=f=6000"); w = w.mean(1) if w.ndim > 1 else w
        wh = w[:n] / (np.abs(w).max() + 1e-9) * (np.abs(v).max() * 10 ** (-26 / 20))
    full = np.stack([v + pad + wh, v + pad * 0.96 + wh], 1); bed = np.stack([pad + wh, pad * 0.96 + wh], 1)
    return full, bed, v, wh


def main():
    N = int(round(S.DUR * SR))
    voice = MC.clean_voice(dry_track(N))
    swaps = list(S.SWAP_TIMES)                     # mix_clean's gentle whoosh (-26 dB re the voice peak) at each swap
    out = MC.mix(voice, S.DUR, swaps=swaps, key=KEY)
    sf.write(os.path.join(OUT, "mix.wav"), out.astype(np.float32), SR, subtype="FLOAT")
    full, bed, v, wh = bed_stems(voice, S.DUR, swaps)
    If, _ = lufs(full); Ib, _ = lufs(bed)
    pk_v = 20 * np.log10(np.abs(v).max()); pk_w = 20 * np.log10(np.abs(wh).max() + 1e-12) if np.abs(wh).max() > 0 else -200.0
    Io, tpo = lufs(out)
    res = dict(full_mix_lufs=If, bed_alone_lufs=Ib, bed_below_mix_db=round(If - Ib, 1), whoosh_peak_below_voice_peak_db=round(pk_v - pk_w, 1),
               final_wav_lufs=Io, final_wav_tp=tpo)
    json.dump(res, open(os.path.join(OUT, "levels.json"), "w"), indent=1); print(res)
    assert If - Ib >= 20, "bed too loud"
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    A.write_srt(os.path.join(HERE, "..", "out", f"{NAME}.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
