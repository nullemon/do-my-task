"""Sound for "What If Earth Spun Faster?" -- BATCH4 clean mix ONLY (lib/mix_clean via lib/b4_kit): the clean voice
(clean_voice: no pitch shift, no echo / reverb), the module's soft pad (key D) and its gentle whoosh at each swap
(-26 dB re the voice peak since the 15 Nov module update). Nothing else is added. Also writes the SRT and prints the bed-vs-mix margin.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/earth-spins-faster.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import short as S
from narration import LINES, pieces
from lib import audio as A
from lib.b4_kit import make_mix

if __name__ == "__main__":
    r = make_mix(S.PL, os.path.join(S.SCR, "vo"), S.DUR, [ts for ts, k in S.SWAPS], "D", os.path.join(S.SCR, "audio", "mix.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    A.write_srt(os.path.join(HERE, "..", "out", "earth-spins-faster.srt"), S.PL, lambda k: pc[k])
    open(os.path.join(S.SCR, "audio", "mix_check.txt"), "w").write(repr(r))
    print("ok", S.DUR, r)
