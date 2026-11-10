"""Kokoro TTS (am_michael) per line WITH phoneme timings -> word timings for one-word captions.
The stock kokoro-v1.0.onnx does not export durations; make_timed_model() appends the duration predictor's
rounded output (/encoder/Clip_output_0) as an extra graph output named "duration", which kokoro_onnx then uses.
Usage: /home/user/ttsenv/bin/python gen_voice.py [SPEED]
Out  : $SCR/vo/<key>.wav (24 kHz) + $SCR/vo/words.json  [{key, start, dur, words:[{cap, t0, t1}]}] (line-relative)
"""
import sys, os, json, re
import numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S1-sun-black-hole"
sys.path.insert(0, os.path.join(SCR, "pylib"))
from narration import LINES, tokens, spoken, caption_word
TIMED = os.path.join(SCR, "kokoro-timed.onnx")


def make_timed_model():
    if os.path.exists(TIMED): return
    import onnx
    from onnx import helper, TensorProto
    m = onnx.load("/home/user/tts-models/kokoro-v1.0.onnx")
    m.graph.node.append(helper.make_node("Cast", ["/encoder/Clip_output_0"], ["duration"], to=TensorProto.INT64))
    m.graph.output.append(helper.make_tensor_value_info("duration", TensorProto.INT64, None))
    onnx.save(m, TIMED)


def word_spans(timing, nwords):
    """group phoneme timings into words at space tokens; drop punctuation-only groups"""
    groups, cur = [], []
    for tm in timing:
        if tm.phoneme == " ":
            if cur: groups.append(cur); cur = []
        else:
            cur.append(tm)
    if cur: groups.append(cur)
    groups = [g for g in groups if any(re.match(r"\w", p.phoneme) or p.phoneme not in ",.?!;:—…\"'" for p in g)]
    spans = []
    for g in groups:
        ph = [p for p in g if p.phoneme not in ",.?!;:—…"]
        if ph: spans.append((ph[0].start, ph[-1].end))
    if len(spans) != nwords:
        print(f"  WARNING: {len(spans)} phoneme words vs {nwords} text words", flush=True)
        return None
    return spans


def main():
    speed = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    make_timed_model()
    from kokoro_onnx import Kokoro
    k = Kokoro(TIMED, "/home/user/tts-models/voices-v1.0.bin")
    out = os.path.join(SCR, "vo"); os.makedirs(out, exist_ok=True)
    meta = []
    for key, text, pause in LINES:
        sp = spoken(text)
        a, sr, tim = k.create_timed(sp, voice="am_michael", speed=speed, lang="en-us")
        # trim to the voiced span, keep timings consistent
        env = np.abs(a); thr = 0.01 * env.max(); idx = np.where(env > thr)[0]
        s0 = max(0, idx[0] - int(0.02 * sr)); s1 = min(len(a), idx[-1] + int(0.08 * sr))
        a = a[s0:s1]; off = s0 / sr
        sf.write(os.path.join(out, f"{key}.wav"), a, sr)
        toks = tokens(text)
        nwords = sum(len(ws) for _, ws in toks)
        spans = word_spans(tim, nwords)
        if spans is None:                                   # proportional fallback by letters
            L = [len(w) + 2 for _, ws in toks for w in ws]; c = np.concatenate([[0], np.cumsum(L)]) / sum(L) * (len(a) / sr)
            spans = [(c[i], c[i + 1]) for i in range(nwords)]
        else:
            spans = [(max(0.0, x - off), max(0.0, y - off)) for x, y in spans]
        words, i = [], 0
        for cap, ws in toks:
            seg = spans[i:i + len(ws)]; i += len(ws)
            c = caption_word(cap) if len(ws) == 1 and cap == ws[0] else cap
            words.append(dict(cap=c, t0=round(seg[0][0], 3), t1=round(seg[-1][1], 3)))
        meta.append(dict(key=key, dur=round(len(a) / sr, 3), pause=pause, words=words))
        print(f"{key:6s} {len(a)/sr:5.2f}s  " + " ".join(f"{w['cap']}@{w['t0']:.2f}" for w in words), flush=True)
    json.dump(dict(speed=speed, sr=24000, lines=meta), open(os.path.join(out, "words.json"), "w"), indent=1)
    print("speech total", round(sum(m["dur"] + m["pause"] for m in meta), 2))


if __name__ == "__main__":
    main()
