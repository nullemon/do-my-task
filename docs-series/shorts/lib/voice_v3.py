"""REDO v3 voice (REDO_V3.md): Kokoro style = 0.7 am_michael + 0.3 am_onyx, speed 0.86, en-us, one TTS call per phrase,
word timings via lib/voice.py's timed model (wrapped, lib/voice.py unchanged).
Usage: from lib.voice_v3 import generate; generate(LINES, out_dir)"""
from . import voice as V

SPEED = 0.86


def style():
    V.make_timed_model()
    from kokoro_onnx import Kokoro
    k = Kokoro(V.TIMED, "/home/user/tts-models/voices-v1.0.bin")
    return 0.7 * k.get_voice_style("am_michael") + 0.3 * k.get_voice_style("am_onyx")


def generate(LINES, out, speed=SPEED):
    V.generate(LINES, out, speed, voice=style())
