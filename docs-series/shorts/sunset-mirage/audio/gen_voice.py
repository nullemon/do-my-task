"""Voice: Kokoro am_michael @ 1.05 with word timings (lib/voice.py).
Run: /home/user/ttsenv/bin/python audio/gen_voice.py [speed]"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, "..", "..")]
from narration import LINES
from lib.voice import generate
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S8-sunset-mirage"
if __name__ == "__main__":
    generate(LINES, os.path.join(SCR, "vo"), float(sys.argv[1]) if len(sys.argv) > 1 else 1.05)
