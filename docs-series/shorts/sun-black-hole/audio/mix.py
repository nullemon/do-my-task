"""Sound for the Short: voice chain + sound design locked to the picture events in short.py, ducking, -14 LUFS, SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py [locked]  -> SCR/audio/mix.wav | mix_locked.wav, ../out/sun-black-hole.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR)


def main(locked=False):
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
    # 7. cut-aways: the Sun's roar in the telescope shots, an implosion whine into the flash, soft whooshes into space
    r = np.random.default_rng(12)
    roar = np.stack([A.lp(r.standard_normal(N), 260, 2) for _ in range(2)], 1) * 0.5
    if locked:   # one locked shot: no cut-away roar, the rumble only builds while the Sun swells and implodes
        roar *= A.env(N, [(0, 0), (S.T_CUT_COLLAPSE, 0), (S.T_CUT_COLLAPSE + 0.8, 0.6), (S.T_OUT - 0.1, 1.6), (S.T_OUT, 0), (S.DUR, 0)])[:, None]
    else:
        roar *= A.env(N, [(0, 0), (S.T_CUT_SUN, 0), (S.T_CUT_SUN + 0.05, 1), (S.T_CUT_PARK1 - 0.05, 1), (S.T_CUT_PARK1, 0),
                          (S.T_CUT_COLLAPSE, 0), (S.T_CUT_COLLAPSE + 0.05, 1), (S.T_OUT - 0.1, 1.6), (S.T_OUT, 0), (S.DUR, 0)])[:, None]
    imp = A.riser(N, S.T_COL0, S.T_OUT - 0.02, seed=13) * 1.1
    wh = 0 if locked else sum(A.riser(N, c - 0.45, c + 0.02, seed=20 + i) * 0.30 for i, c in enumerate((S.T_CUT_ORBIT, S.T_CUT_FREEZE, S.T_CUT_END)))
    if locked: sw = sw * 0                                   # no telescope inset in the locked version
    bed = day * 0.9 + tk + rs * 0.5 + th * 0.9 + cold * 0.8 + sw + sh + hi * 0.8 + roar * 0.6 + imp + wh
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    fade = np.clip((S.DUR - t) / 0.4, 0, 1)[:, None]
    mix *= fade
    sf.write(os.path.join(OUT, "mix_raw.wav"), mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(os.path.join(OUT, "mix_raw.wav"), os.path.join(OUT, "mix_locked.wav" if locked else "mix.wav"), -14.0, -1.0)
    os.remove(os.path.join(OUT, "mix_raw.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "sun-black-hole.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main(locked=len(sys.argv) > 1 and sys.argv[1] == "locked")
