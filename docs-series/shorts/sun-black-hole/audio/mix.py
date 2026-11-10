"""Sound for the Short: voice chain + sound design locked to the picture events in short.py, ducking, -14 LUFS, SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/sun-black-hole.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR)


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    t = np.arange(N) / SR
    # 1. warm daytime pad (cut at the blackout)
    day = A.drone(N, root=55.0, seed=1, bright=0.30) * A.env(N, [(0, 0), (0.6, 0.8), (S.T_OUT - 0.05, 1.0), (S.T_OUT, 0.0), (S.DUR, 0)])[:, None]
    # 2. clock ticks from "right now" to the last light, accelerating; riser into the blackout
    tk = A.ticks(N, S.T_NOW, S.T_OUT - 0.1, rate=3.0, gain=0.10, accel=2.2)
    rs = A.riser(N, S.T_OUT - 2.6, S.T_OUT, seed=2) * 0.8
    # 3. the Sun goes out: sub thump, then near-silence, then a cold, dark drone
    th = A.thump(N, S.T_OUT, 1.2)
    cold = A.drone(N, root=36.7, seed=4, bright=0.18) * A.env(N, [(0, 0), (S.T_OUT + 1.2, 0), (S.T_OUT + 5.0, 0.75), (S.T_COLD, 0.9), (S.DUR - 1.2, 1.0), (S.DUR, 0)])[:, None]
    # 4. telescope: soft air swell as the eyepiece opens
    sw = A.riser(N, S.T_SC0 - 0.9, S.T_SC0 + 0.15, seed=6) * 0.35
    # 5. frost: icy shimmer from "cold" to the end
    sh = A.shimmer(N, S.T_COLD - 0.3, S.DUR - 0.3, seed=5, gain=0.16) * A.env(N, [(0, 1), (S.DUR - 1.0, 1), (S.DUR, 0)])[:, None]
    # 6. final low hit on the last word
    hi = A.hit(N, S.T_LAST + 0.30, gain=0.55, root=41.2)
    bed = day * 0.9 + tk + rs + th * 0.9 + cold * 0.8 + sw + sh + hi * 0.8
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    fade = np.clip((S.DUR - t) / 0.4, 0, 1)[:, None]
    mix *= fade
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "sun-black-hole.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
