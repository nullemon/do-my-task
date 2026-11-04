"""Kokoro TTS for every narration line (same voice as the series: am_michael, speed 0.94).
Usage: /home/user/ttsenv/bin/python gen_voice.py [only_index ...]"""
import sys, os, json, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from narration import LINES, tts_text, PHONEME_FIXES
from kokoro_onnx import Kokoro
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
out = os.path.join(SCR, "vo_raw"); os.makedirs(out, exist_ok=True)
voice, speed, lang = "am_michael", 0.94, "en-us"
only = [int(a) for a in sys.argv[1:]]
k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
for i, (shot, pause, text) in enumerate(LINES):
    fn = os.path.join(out, f"line_{i:02d}.wav")
    if only and i not in only:
        continue
    ph = k.tokenizer.phonemize(tts_text(text), lang)
    for a, b in PHONEME_FIXES.items():
        ph = ph.replace(a, b)
    s, sr = k.create(ph, voice=voice, speed=speed, lang=lang, is_phonemes=True)
    a = np.abs(s); thr = 0.01 * a.max(); idx = np.where(a > thr)[0]
    s = s[max(0, idx[0] - int(0.02 * sr)): min(len(s), idx[-1] + int(0.08 * sr))]
    sf.write(fn, s, sr)
    print(f"{i:02d} {shot:8s} {len(s)/sr:5.2f}s  {ph[:70]}")
# durations of all clips
meta = []
for i, (shot, pause, text) in enumerate(LINES):
    x, sr = sf.read(os.path.join(out, f"line_{i:02d}.wav"))
    meta.append(dict(i=i, shot=shot, pause=pause, dur=round(len(x) / sr, 3), text=text))
json.dump(dict(voice=voice, speed=speed, lines=meta), open(os.path.join(out, "meta.json"), "w"), indent=1)
print("total speech", round(sum(m["dur"] for m in meta), 2), "pauses", round(sum(m["pause"] for m in meta), 2))
