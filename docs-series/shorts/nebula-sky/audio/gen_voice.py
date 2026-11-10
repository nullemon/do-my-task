"""Voice: Kokoro am_michael with real word timings. Wraps lib/voice.py (not edited): Kokoro's phonemizer fuses some
function-word pairs into one phoneme word ("in the" -> "ɪnðə", "was the" -> "wʌzðə"), which made lib.voice fall back to
proportional timing. Here such pairs are merged for alignment and the fused span is split by letter count.
Run: /home/user/ttsenv/bin/python audio/gen_voice.py [speed]"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
from narration import LINES
from lib import voice as V
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S16-nebula-sky"
FUSE2 = {"the", "a", "one", "one?"}


def groups_of(timing):
    gs, cur = [], []
    for tm in timing:
        if tm.phoneme == " ":
            if cur: gs.append(cur); cur = []
        else: cur.append(tm)
    if cur: gs.append(cur)
    out = []
    for g in gs:
        ph = [p for p in g if p.phoneme not in ",.?!;:—…\"'"]
        if ph: out.append((ph[0].start, ph[-1].end))
    return out


def align(spans, words):
    """words: spoken words. Merge (x, the/a) pairs left to right until counts match, then split merged spans."""
    units = [[w] for w in words]
    i = 0
    while len(units) > len(spans) and i < len(units) - 1:
        if units[i + 1][0].lower().strip(".,?!") in FUSE2 and len(units[i]) == 1:
            units[i] = units[i] + units.pop(i + 1)
        i += 1
    if len(units) != len(spans): return None
    out = []
    for u, (a, b) in zip(units, spans):
        L = [len(w) for w in u]; c = np.concatenate([[0], np.cumsum(L)]) / sum(L) * (b - a) + a
        out += [(c[k], c[k + 1]) for k in range(len(u))]
    return out


def generate(speed, voice="am_michael"):
    V.make_timed_model()
    from kokoro_onnx import Kokoro
    k = Kokoro(V.TIMED, "/home/user/tts-models/voices-v1.0.bin")
    out = os.path.join(SCR, "vo"); os.makedirs(out, exist_ok=True)
    meta = []
    for key, text, pause in LINES:
        a, sr, tim = k.create_timed(V.spoken(text), voice=voice, speed=speed, lang="en-us")
        env = np.abs(a); idx = np.where(env > 0.01 * env.max())[0]
        s0 = max(0, idx[0] - int(0.02 * sr)); s1 = min(len(a), idx[-1] + int(0.08 * sr)); a = a[s0:s1]; off = s0 / sr
        sf.write(os.path.join(out, f"{key}.wav"), a, sr)
        toks = V.tokens(text); sw = [w for _, ws in toks for w in ws]
        spans = align(groups_of(tim), sw)
        if spans is None: raise SystemExit(f"alignment failed for {key}: {len(groups_of(tim))} vs {len(sw)}")
        spans = [(max(0.0, x - off), max(0.0, y - off)) for x, y in spans]
        words, i = [], 0
        for cap, ws in toks:
            seg = spans[i:i + len(ws)]; i += len(ws)
            c = V.caption_word(cap) if len(ws) == 1 and cap == ws[0] else cap
            words.append(dict(cap=c, t0=round(seg[0][0], 3), t1=round(seg[-1][1], 3)))
        meta.append(dict(key=key, dur=round(len(a) / sr, 3), pause=pause, words=words))
        print(f"{key:6s} {len(a)/sr:5.2f}s  " + " ".join(f"{w['cap']}@{w['t0']:.2f}" for w in words), flush=True)
    json.dump(dict(speed=speed, sr=24000, lines=meta), open(os.path.join(out, "words.json"), "w"), indent=1)
    print("speech total", round(sum(m["dur"] + m["pause"] for m in meta), 2))


if __name__ == "__main__":
    generate(float(sys.argv[1]) if len(sys.argv) > 1 else 1.05)
