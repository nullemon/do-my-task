"""Voice for this Short (REDO v3): Kokoro 0.7 am_michael + 0.3 am_onyx @ 0.86, one call per line, word timings.
Run: /home/user/ttsenv/bin/python audio/gen_voice.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, "..", "..")]
from narration import LINES
from lib.v3 import generate_v3
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/V3-star-clusters"
if __name__ == "__main__":
    generate_v3(LINES, os.path.join(SCR, "vo"))
