"""Generate each narration line with Kokoro (offline ONNX). Usage: python gen_voice.py VOICE SPEED"""
import sys, os, json, numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narration import LINES, tts_text, PHONEME_FIXES
from kokoro_onnx import Kokoro
voice = sys.argv[1] if len(sys.argv) > 1 else "am_michael"
speed = float(sys.argv[2]) if len(sys.argv) > 2 else 0.94
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vo_raw"); os.makedirs(out, exist_ok=True)
k = Kokoro("/home/user/tts-models/kokoro-v1.0.onnx", "/home/user/tts-models/voices-v1.0.bin")
lang = "en-gb" if voice.startswith("b") else "en-us"
meta = []
for i, (ch, off, text) in enumerate(LINES):
    ph = k.tokenizer.phonemize(tts_text(text), lang)
    for a, b in PHONEME_FIXES.items():
        ph = ph.replace(a, b)
    s, sr = k.create(ph, voice=voice, speed=speed, lang=lang, is_phonemes=True, sentence_pause=0.4)
    # trim leading/trailing near-silence
    a = np.abs(s); thr = 0.01 * a.max(); idx = np.where(a > thr)[0]
    s = s[max(0, idx[0] - int(0.02*sr)): min(len(s), idx[-1] + int(0.08*sr))]
    fn = os.path.join(out, f"line_{i:02d}.wav"); sf.write(fn, s, sr)
    meta.append(dict(i=i, ch=ch, off=off, start=(ch-1)*60+off, dur=len(s)/sr, text=text))
    print(f"{i:02d} ch{ch} {off:5.1f} dur {len(s)/sr:5.2f}  {text[:60]}")
json.dump(dict(voice=voice, speed=speed, sr=sr, lines=meta), open(os.path.join(out, "meta.json"), "w"), indent=1)
