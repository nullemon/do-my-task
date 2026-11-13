import json, re, sys
sys.path.insert(0, ".")
from script import SEG, TITLE

from cfg import SRC, PHOTOS
CARD = 2.6      # chapter card length
GAP = 0.55      # pause after each narration block
LEAD = 0.5

tts = {o["i"]: o for o in json.load(open("tts/tts.json"))}

def chunk_words(sents):
    """caption chunks with per-word times (proportional to characters inside each sentence)"""
    chunks = []
    for (s0, s1, text) in sents:
        words = text.replace("...", "…").split()
        w = [len(x) + 1.5 for x in words]; tot = sum(w); t = s0; wt = []
        for x, ww in zip(words, w):
            d = (s1 - s0) * ww / tot; wt.append((x, t, t + d)); t += d
        cur = []
        for j, (x, a, b) in enumerate(wt):
            cur.append((x, a, b))
            ln = sum(len(y[0]) + 1 for y in cur)
            if len(cur) >= 3 or ln >= 16 or re.search(r"[.,!?:;…]$", x):
                chunks.append(cur); cur = []
        if cur: chunks.append(cur)
    return chunks

def build():
    t = LEAD
    spans, narr, clips, caps, overlays = [], [], [], [], []
    for i, s in enumerate(SEG):
        if s["kind"] == "chapter":
            spans.append(dict(t0=t, t1=t + CARD, vis=("CHAPTER", s["n"], s["text"], ""), seg=i))
            t += CARD
        elif s["kind"] == "sound":
            d = s["t1"] - s["t0"]
            spans.append(dict(t0=t, t1=t + d + 0.5, vis=(s["src"], s["t0"] - 0.25, s["crop"], s["credit"]), seg=i, sound=True))
            clips.append(dict(src=SRC[s["src"]], at=t + 0.25, t0=s["t0"], t1=s["t1"]))
            for a, b, txt in s["subs"]:
                caps.append(dict(t0=t + 0.25 + a, t1=t + 0.25 + b, quote=txt, speaker=s["speaker"]))
            t += d + 0.5 + 0.2
        else:
            info = tts[i]; d = info["dur"]
            narr.append(dict(file=f"tts/seg{i:02d}.wav", at=t))
            for ch in chunk_words(info["sents"]):
                caps.append(dict(t0=t + ch[0][1], t1=t + ch[-1][2], words=[(w, t + a, t + b) for w, a, b in ch]))
            total = d + GAP
            vis = s["vis"]; n = len(vis)
            # split by sentence boundaries when possible
            bounds = [t]
            if n > 1:
                ends = [t + e for (_, e, _) in info["sents"]]
                for k in range(1, n):
                    target = t + total * k / n
                    cand = min(ends[:-1] or [target], key=lambda e: abs(e - target)) if len(ends) > 1 else target
                    if abs(cand - target) > total / (2 * n): cand = target
                    bounds.append(max(bounds[-1] + 1.2, cand + 0.15))
            bounds.append(t + total)
            for k, v in enumerate(vis):
                spans.append(dict(t0=bounds[k], t1=bounds[k + 1], vis=v, seg=i))
            if s.get("place"): overlays.append(dict(kind="place", t0=t + 0.2, t1=t + min(total, 4.2), text=s["place"]))
            if s.get("title"): overlays.append(dict(kind="title", t0=t, t1=t + total, text=TITLE))
            t += total
    # extend last span for an end tail
    spans[-1]["t1"] += 1.5
    return dict(spans=spans, narr=narr, clips=clips, caps=caps, overlays=overlays, dur=spans[-1]["t1"])

if __name__ == "__main__":
    tl = build()
    json.dump(tl, open("timeline.json", "w"), indent=1)
    print("duration", round(tl["dur"], 1), "s;", len(tl["spans"]), "spans;", len(tl["caps"]), "captions")
    for s in tl["spans"]:
        print(f"{s['t0']:6.1f}-{s['t1']:6.1f}  {s['vis'][0]:8s} {str(s['vis'][1])[:10]:10s}")
