import re, json, sys, numpy as np, soundfile as sf
sys.path.insert(0, ".")
from script import SEG
from kokoro_onnx import Kokoro
k = Kokoro("/home/claude/tts/kokoro-v1.0.onnx", "/home/claude/tts/voices-v1.0.bin")
SR = 24000
def sentences(t):
    parts = re.split(r"(?<=[.!?])\s+", t.strip())
    return [p for p in parts if p]
out = []
import os; os.makedirs("tts", exist_ok=True)
for i, s in enumerate(SEG):
    if s["kind"] != "narr": continue
    pieces, sent_t = [], []
    t = 0.0
    for sen in sentences(s["text"]):
        spoken = sen.replace("...", ",")
        a, sr = k.create(spoken, voice="af_heart", speed=0.92, lang="en-us")
        # trim leading/trailing near-silence
        thr = 0.01; nz = np.where(np.abs(a) > thr)[0]
        if len(nz): a = a[max(0, nz[0]-240): nz[-1]+480]
        gap = 0.5 if sen.endswith("...") or "..." in sen else 0.3
        sent_t.append((t, t + len(a)/SR, sen))
        pieces += [a, np.zeros(int(gap*SR), dtype=a.dtype)]
        t += len(a)/SR + gap
    audio = np.concatenate(pieces[:-1])
    sf.write(f"tts/seg{i:02d}.wav", audio, SR)
    out.append(dict(i=i, dur=len(audio)/SR, sents=sent_t))
    print(i, f"{len(audio)/SR:5.1f}s", s["text"][:60])
json.dump(out, open("tts/tts.json", "w"), indent=1)
print("total narration", sum(o["dur"] for o in out))
