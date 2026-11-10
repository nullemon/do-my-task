"""SRT from the locked placement: one cue per sentence (long sentences split at a comma), time shared by character count,
at most two lines of about 42 characters."""
import json, re, os, textwrap
HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "placement.json")))["lines"]
def ts(t): h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60; return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"
cues = []
for l in P:
    parts = []
    for sent in re.split(r"(?<=[.!?:])\s+", l["text"].strip()):
        while len(sent) > 84:
            cut = max((m.end() for m in re.finditer(r",\s", sent[:84])), default=None) or sent.rfind(" ", 0, 84) + 1
            parts.append(sent[:cut].strip()); sent = sent[cut:]
        parts.append(sent.strip())
    merged = []
    for p in parts:                                   # glue very short fragments to a neighbour
        if merged and len(merged[-1]) + len(p) + 1 <= 60 and (len(p) < 22 or len(merged[-1]) < 22): merged[-1] += " " + p
        else: merged.append(p)
    tot = sum(len(p) for p in merged); t = l["start"]
    for p in merged:
        d = (l["end"] - l["start"]) * len(p) / tot; cues.append((t, t + d, p)); t += d
out = []
for i, (a, b, txt) in enumerate(cues, 1):
    b = min(b + 0.35, cues[i][0] - 0.04) if i < len(cues) else b + 0.5
    lines = textwrap.wrap(txt, 42) if len(txt) > 42 else [txt]
    if len(lines) > 2: lines = textwrap.wrap(txt, (len(txt) + 3) // 2 + 2)
    out.append(f"{i}\n{ts(a)} --> {ts(b)}\n" + "\n".join(lines) + "\n")
open(os.path.join(os.path.dirname(HERE), "sunset-on-every-world.srt"), "w").write("\n".join(out)); print("cues", len(cues), "max line", max(len(x) for c in out for x in c.split("\n")[2:]))
