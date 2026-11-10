"""Kokoro TTS per line (same voice as the series: am_michael, speed 0.94). Usage: python gen_voice.py [VOICE] [SPEED]"""
import sys, os, json, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from narration import LINES, tts_text, PHONEME_FIXES
from kokoro_onnx import Kokoro
voice = sys.argv[1] if len(sys.argv) > 1 else "am_michael"
speed = float(sys.argv[2]) if len(sys.argv) > 2 else 0.94
OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day/vo_raw"
os.makedirs(OUT, exist_ok=True)
k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
meta = []
only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
old = {m["key"]: m for m in json.load(open(os.path.join(OUT, "meta.json")))["lines"]} if (only and os.path.exists(os.path.join(OUT, "meta.json"))) else {}
for i, (key, text) in enumerate(LINES):
    fn = os.path.join(OUT, f"{key}.wav")
    if only is not None and key not in only and key in old:
        meta.append(old[key]); continue
    ph = k.tokenizer.phonemize(tts_text(text), "en-us")
    for a, b in PHONEME_FIXES.items(): ph = ph.replace(a, b)
    s, sr = k.create(ph, voice=voice, speed=speed, lang="en-us", is_phonemes=True)
    a = np.abs(s); thr = 0.01 * a.max(); idx = np.where(a > thr)[0]
    s = s[max(0, idx[0] - int(0.02*sr)): min(len(s), idx[-1] + int(0.08*sr))]
    sf.write(fn, s, sr)
    meta.append(dict(i=i, key=key, dur=len(s)/sr, text=text))
    print(f"{i:02d} {key:9s} {len(s)/sr:5.2f}s  {text[:60]}", flush=True)
json.dump(dict(voice=voice, speed=speed, sr=24000, lines=meta), open(os.path.join(OUT, "meta.json"), "w"), indent=1)
print("total speech", sum(m["dur"] for m in meta))
