"""Generate each narration line with Kokoro (offline ONNX), voice am_michael @0.94 (series voice)."""
import sys, os, json, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from narration import LINES, tts_text, PHONEME_FIXES
from kokoro_onnx import Kokoro
voice, speed = "am_michael", 0.94
OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us/vo_raw"
os.makedirs(OUT, exist_ok=True)
only = set(sys.argv[1:])
k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
mp = os.path.join(OUT, "meta.json")
meta = json.load(open(mp)) if os.path.exists(mp) else {}
for key, text in LINES:
    if only and key not in only and key in meta: continue
    ph = k.tokenizer.phonemize(tts_text(text), "en-us")
    for a, b in PHONEME_FIXES.items(): ph = ph.replace(a, b)
    s, sr = k.create(ph, voice=voice, speed=speed, lang="en-us", is_phonemes=True)
    a = np.abs(s); thr = 0.01 * a.max(); idx = np.where(a > thr)[0]
    s = s[max(0, idx[0] - int(0.02*sr)): min(len(s), idx[-1] + int(0.08*sr))]
    sf.write(os.path.join(OUT, f"{key}.wav"), s, sr)
    meta[key] = dict(dur=len(s)/sr, text=text, ph=ph)
    print(f"{key:8s} {len(s)/sr:6.2f}  {ph[:90]}")
json.dump(meta, open(mp, "w"), indent=1)
print("total speech", sum(m["dur"] for m in meta.values()))
