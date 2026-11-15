"""Mux picture + clean mix + soft subtitles -> out/earth-spins-faster-short.mp4 (9:16 only): AAC 192k, no -shortest; the AAC true
peak is checked on the final mp4 (trimmed if above -1.5 dBTP) and LUFS / dBTP are printed (lib/b4_kit.encode).
Run: /home/user/ttsenv/bin/python encode.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, "..")]
from lib.b4_kit import encode
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-earth-spins-faster"
if __name__ == "__main__":
    encode(os.path.join(SCR, "video_vert.mp4"), os.path.join(SCR, "audio", "mix.wav"), os.path.join(HERE, "out", "earth-spins-faster.srt"),
           os.path.join(HERE, "out", "earth-spins-faster-short.mp4"))
