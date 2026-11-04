"""Kokoro TTS (offline ONNX), voice am_michael @ 0.94 — one clip per line. Usage: python gen_voice.py [ids...]"""
import sys, os, json, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narration import LINES, tts_text, PHONEME_FIXES
from kokoro_onnx import Kokoro
VOICE, SPEED = "am_michael", 0.94
out = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still/vo_raw"; os.makedirs(out, exist_ok=True)
k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
only = set(sys.argv[1:])
mp = os.path.join(out, "meta.json")
meta = json.load(open(mp)) if os.path.exists(mp) else {}
for lid, scene, pause, text in LINES:
    if only and lid not in only and lid in meta: continue
    ph = k.tokenizer.phonemize(tts_text(text), "en-us")
    for a, b in PHONEME_FIXES.items(): ph = ph.replace(a, b)
    s, sr = k.create(ph, voice=VOICE, speed=SPEED, lang="en-us", is_phonemes=True)
    a = np.abs(s); thr = 0.01 * a.max(); idx = np.where(a > thr)[0]
    s = s[max(0, idx[0] - int(0.02*sr)): min(len(s), idx[-1] + int(0.08*sr))]
    sf.write(os.path.join(out, lid + ".wav"), s, sr)
    meta[lid] = dict(dur=len(s)/sr, sr=sr, text=text, ph=ph)
    print(f"{lid} {len(s)/sr:5.2f}s  {text[:70]}", flush=True)
json.dump(meta, open(mp, "w"), indent=1)
