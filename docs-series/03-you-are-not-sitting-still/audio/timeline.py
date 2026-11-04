"""Lock the timeline to the measured voice clips. Writes timeline.json (line starts/ends + scene windows)."""
import json, os
from narration import LINES
HERE = os.path.dirname(os.path.abspath(__file__))
S = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still"
TOTAL, T0, TRANS, TAIL = 270.0, 0.6, 5.0, 10.0
m = json.load(open(f"{S}/vo_raw/meta.json"))
dur = sum(m[l]["dur"] for l, *_ in LINES)
ntrans = sum(1 for i in range(1, len(LINES)) if LINES[i][1] != LINES[i-1][1])
intra = sum(p for i, (l, sc, p, t) in enumerate(LINES) if i > 0 and LINES[i-1][1] == sc)
k = (TOTAL - T0 - dur - ntrans * TRANS - TAIL) / intra
t = T0; out = []; scenes = {}
for i, (l, sc, p, txt) in enumerate(LINES):
    if i > 0:
        t += TRANS if LINES[i-1][1] != sc else p * k
    d = m[l]["dur"]
    out.append(dict(id=l, scene=sc, start=round(t, 3), end=round(t + d, 3), dur=round(d, 3), text=txt))
    t += d
# scene windows: a new scene's visuals begin 2.0 s before its first line (i.e. inside the transition pause)
order = []
for o in out:
    if o["scene"] not in scenes:
        scenes[o["scene"]] = [max(0.0, o["start"] - 2.0 if order else 0.0), None]; order.append(o["scene"])
for a, b in zip(order, order[1:]):
    scenes[a][1] = scenes[b][0]
scenes[order[-1]][1] = TOTAL
json.dump(dict(total=TOTAL, pause_scale=round(k, 3), lines=out, scenes=scenes, order=order),
          open(os.path.join(HERE, "timeline.json"), "w"), indent=1)
print("pause scale", round(k, 3), "end of last line", out[-1]["end"])
for o in out: print(f"{o['id']} {o['scene']:6s} {o['start']:7.2f}-{o['end']:7.2f}  {o['text'][:60]}")
for s in order: print(s, scenes[s], round(scenes[s][1]-scenes[s][0],2))
