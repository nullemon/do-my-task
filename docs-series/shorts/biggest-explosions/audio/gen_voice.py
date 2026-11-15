"""BATCH4 voice: Kokoro 0.7 am_michael + 0.3 am_onyx (blended style), speed 0.86, one TTS call per phrase, word timings
(lib/v3_kit.generate). Run: /home/user/ttsenv/bin/python audio/gen_voice.py"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, "..", "..")]
from narration import LINES
from lib.v3_kit import generate
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-biggest-explosions"
if __name__ == "__main__":
    generate(LINES, os.path.join(SCR, "vo"))
