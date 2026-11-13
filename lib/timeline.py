"""python lib/timeline.py <code>  ->  work/timeline.json (spans, narration placement, real-audio clips, captions, overlays)"""
import os, sys, json, re, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_case
CARD, GAP, LEAD = 2.8, 0.45, 0.25

def chunk(words, maxc=28):
    out, cur = [], []
    for w in words:
        cur.append(w); n = sum(len(x[0]) + 1 for x in cur)
        nxt_long = n >= maxc - 6
        if n >= maxc or re.search(r"[.!?…]$", w[0]) or (re.search(r"[,;:—]$", w[0]) and n >= 12) or (nxt_long and len(cur) >= 5):
            out.append(cur); cur = []
    if cur:
        if out and sum(len(x[0]) + 1 for x in cur) < 8 and sum(len(x[0]) + 1 for x in out[-1]) < maxc and not re.search(r"[.!?]$", out[-1][-1][0]):
            out[-1] += cur
        else: out.append(cur)
    return out

def find_word(words, key, after):
    key = re.sub(r"[^a-z0-9]", "", key.lower())
    for w, a, b in words:
        if a >= after - 0.05 and re.sub(r"[^a-z0-9]", "", w.lower().replace("ō", "o")).startswith(key): return a
    raise SystemExit(f"anchor word '{key}' not found after {after:.2f}s")

def build(cfg, scr):
    tts = {o["i"]: o for o in json.load(open(os.path.join(cfg.WORK, "tts", "tts.json")))}
    t = LEAD; spans, narr, clips, caps, overlays = [], [], [], [], []
    bg_prev = None
    for i, s in enumerate(scr.SEG):
        if s["kind"] == "chapter":
            spans.append(dict(t0=t, t1=t + CARD, shot=dict(L="chapter", n=s["n"], title=s["text"], bg=s.get("bg") or bg_prev), seg=i, chapter=True))
            t += CARD
        elif s["kind"] == "sound":
            d = s["t1"] - s["t0"]
            sh = copy.deepcopy(s["shot"]); sh["media"]["t_in"] = s["t0"] - 0.25; sh["media"]["t_out"] = s["t1"] + 0.25
            spans.append(dict(t0=t, t1=t + d + 0.5, shot=sh, seg=i, sound=True))
            clips.append(dict(src=s["src"], at=t + 0.25, t0=s["t0"], t1=s["t1"]))
            for a, b, txt in s["subs"]:
                caps.append(dict(t0=t + 0.25 + a, t1=t + 0.25 + b, quote=txt, speaker=s["speaker"]))
            t += d + 0.5 + 0.25
        else:
            info = tts[i]; d = info["dur"]
            words = [(w, t + a, t + b) for w, a, b in info["words"]]
            narr.append(dict(file=f"tts/seg{i:02d}.wav", at=t, dur=d))
            for ch in chunk(words):
                caps.append(dict(t0=ch[0][1], t1=ch[-1][2], words=ch))
            total = d + s.get("gap", GAP)
            vis = s["vis"]; n = len(vis)
            bounds = [t]
            ends = [b for w, a, b in words if re.search(r"[.!?…,]$", w)][:-1]
            for k in range(1, n):
                sh = vis[k]
                if isinstance(sh, dict) and sh.get("at"):
                    cand = find_word(words, sh["at"], bounds[-1] + 0.5) - 0.12
                else:
                    target = t + total * k / n
                    cand = min(ends, key=lambda e: abs(e - target)) + 0.12 if ends else target
                    if abs(cand - target) > total / (2 * n): cand = target
                bounds.append(max(bounds[-1] + 1.0, cand))
            bounds.append(t + total)
            for k, sh in enumerate(vis):
                sh = copy.deepcopy(sh); t0s = bounds[k]
                for p in sh.get("pops", []):
                    if isinstance(p["t"], str) and p["t"].startswith("@"): p["t"] = max(0.0, find_word(words, p["t"][1:], t0s) - t0s - 0.05)
                if sh.get("L") == "freeze" and isinstance(sh.get("at"), str): sh["at"] = max(0.3, find_word(words, sh["at"][1:], t0s) - t0s)
                spans.append(dict(t0=t0s, t1=bounds[k + 1], shot=sh, seg=i))
                m = sh.get("media") or sh.get("bg") or sh.get("top")
                if isinstance(m, dict) and m.get("m") == "photo": bg_prev = m
            if s.get("place"): overlays.append(dict(kind="place", t0=t + 0.2, t1=t + min(total, 4.5), text=s["place"]))
            if s.get("title"): overlays.append(dict(kind="title", t0=t, t1=t + total))
            t += total
    spans[-1]["t1"] += 1.2
    spans[0]["t0"] = 0.0
    for o in getattr(cfg, "HOOK", []):
        overlays.append(dict(kind="hook", t0=o[0], t1=o[1], lines=o[2]))
    hook_end = max([o[1] for o in getattr(cfg, "HOOK", [])] + [0])
    return dict(spans=spans, narr=narr, clips=clips, caps=caps, overlays=overlays, dur=spans[-1]["t1"], hook_end=hook_end)

if __name__ == "__main__":
    cfg, scr = load_case(sys.argv[1])
    tl = build(cfg, scr)
    json.dump(tl, open(os.path.join(cfg.WORK, "timeline.json"), "w"), indent=1, ensure_ascii=False)
    print(f"duration {tl['dur']:.1f}s ({tl['dur']/60:.2f} min); {len(tl['spans'])} spans; {len(tl['caps'])} caption chunks")
    for k, s in enumerate(tl["spans"]):
        sh = s["shot"]; m = sh.get("media") or sh.get("top") or {}
        print(f"{k:3d} {s['t0']:6.1f}-{s['t1']:6.1f} {sh['L']:8s} {m.get('key') or m.get('src') or sh.get('title') or sh.get('big') or ''}")
