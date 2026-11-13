"""python lib/tts.py <code>   ->  cases/<code>/work/tts/segNN.wav + tts.json (word timings from faster-whisper)
One Kokoro call per paragraph (natural flow). Pronunciation fixes from cfg.PRON apply to the TTS text only;
captions keep the script spelling (whisper words are aligned back onto the script words)."""
import os, sys, re, json, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_case, MODELS
import numpy as np, soundfile as sf

VOICE, SPEED, SR = "af_heart", 0.93, 24000

def spoken(text, pron):
    t = text.replace("…", ",").replace("...", ",").replace("—", ", ").replace("–", " to ")
    for k, v in sorted(pron.items(), key=lambda kv: -len(kv[0])):
        t = re.sub(r"(?<!\w)" + re.escape(k) + r"(?!\w)", v, t)
    return t

norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower().replace("ō", "o").replace("ū", "u"))

def align(script_words, wh):
    """map whisper (word, t0, t1) onto script words; interpolate gaps"""
    a = [norm(w) for w in script_words]; b = [norm(w[0]) for w in wh]
    T = [None] * len(script_words)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size): T[blk.a + k] = (wh[blk.b + k][1], wh[blk.b + k][2])
    # fill unmatched runs between anchors proportionally to characters
    end = wh[-1][2] if wh else 1.0
    i = 0
    while i < len(T):
        if T[i] is None:
            j = i
            while j < len(T) and T[j] is None: j += 1
            t0 = T[i - 1][1] if i > 0 else (wh[0][1] if wh else 0.0)
            t1 = T[j][0] if j < len(T) else end
            ch = [len(script_words[k]) + 1 for k in range(i, j)]; tot = sum(ch); t = t0
            for k, c in zip(range(i, j), ch):
                d = (t1 - t0) * c / tot; T[k] = (t, t + d); t += d
            i = j
        else: i += 1
    return [(w, round(s, 3), round(e, 3)) for w, (s, e) in zip(script_words, T)]

def main(code):
    cfg, scr = load_case(code)
    out = os.path.join(cfg.WORK, "tts"); os.makedirs(out, exist_ok=True)
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    from faster_whisper import WhisperModel
    try: wm = WhisperModel("small.en", device="cuda", compute_type="float16"); wm.transcribe(np.zeros(16000, np.float32))
    except Exception: wm = WhisperModel("small.en", device="cpu", compute_type="int8")
    pron = getattr(cfg, "PRON", {})
    old = {}
    jp = os.path.join(out, "tts.json")
    if os.path.exists(jp): old = {o["i"]: o for o in json.load(open(jp))}
    res = []
    for i, s in enumerate(scr.SEG):
        if s["kind"] != "narr": continue
        wav = os.path.join(out, f"seg{i:02d}.wav"); sp = spoken(s["text"], pron)
        if i in old and old[i].get("spoken") == sp and os.path.exists(wav) and not os.environ.get("FORCE") and not os.environ.get("REALIGN"):
            res.append(old[i]); continue
        if os.environ.get("REALIGN") and os.path.exists(wav):
            a, sr = sf.read(wav)
        else:
            a, sr = k.create(sp, voice=VOICE, speed=getattr(cfg, "SPEED", SPEED), lang="en-us")
            nz = np.where(np.abs(a) > 0.008)[0]
            if len(nz): a = a[max(0, nz[0] - 200): nz[-1] + 1200]
            sf.write(wav, a, sr)
        a16 = np.interp(np.arange(0, len(a), sr / 16000), np.arange(len(a)), a).astype(np.float32)
        segs, _ = wm.transcribe(a16, word_timestamps=True, language="en", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        wh = [(w.word.strip(), w.start, w.end) for sg in segs for w in sg.words]
        words = align(s["text"].replace("…", "… ").split(), wh)
        res.append(dict(i=i, dur=round(len(a) / sr, 3), spoken=sp, words=words, heard=" ".join(w[0] for w in wh)))
        print(f"{i:02d} {len(a)/sr:5.1f}s  {s['text'][:70]}", flush=True)
    json.dump(res, open(jp, "w"), indent=1, ensure_ascii=False)
    tot = sum(o["dur"] for o in res); print(f"narration {tot:.1f}s, {sum(len(o['words']) for o in res)} words")

if __name__ == "__main__":
    main(sys.argv[1])
