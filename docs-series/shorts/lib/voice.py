"""Kokoro TTS (am_michael) per line WITH phoneme timings -> word timings for one-word captions (shared by all Shorts).
The stock kokoro-v1.0.onnx does not export durations; make_timed_model() appends the duration predictor's
rounded output (/encoder/Clip_output_0) as an extra graph output named "duration", which kokoro_onnx then uses.
Usage: from lib.voice import generate; generate(LINES, out_dir, speed)   (LINES markup: see narration.py of a Short)
Out  : out_dir/<key>.wav (24 kHz) + out_dir/words.json  [{key, start, dur, words:[{cap, t0, t1}]}] (line-relative)
"""
import sys, os, json, re
import numpy as np, soundfile as sf
from .core import COMMON
TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")
TIMED = os.path.join(COMMON, "kokoro-timed.onnx")


def tokens(text):
    """markup {CAPTION|spoken words} -> list of (caption, [spoken words])"""
    out = []
    for m in TOK.finditer(text):
        if m.group(4): out.append((m.group(4), [m.group(4)]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3); out.append((m.group(1), ws))
    return out


def spoken(text): return " ".join(w for _, ws in tokens(text) for w in ws)
def caption_word(w): return re.sub(r"[.,?!:;]+$", "", w.strip()).upper()


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


def generate(LINES, out, speed=1.0, voice="am_michael"):
    make_timed_model()
    from kokoro_onnx import Kokoro
    k = Kokoro(TIMED, "/home/user/tts-models/voices-v1.0.bin")
    os.makedirs(out, exist_ok=True)
    meta = []
    for key, text, pause in LINES:
        sp = spoken(text)
        a, sr, tim = k.create_timed(sp, voice=voice, speed=speed, lang="en-us")
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

