"""Lock the timeline to the measured voice: line starts = previous end + pause*F (first pause fixed).
Also defines the descent: the camera depth at the start of each keyed line (so a depth is reached
exactly when the narrator names it). Writes placement.json (lines, depth keys) for visuals + mix."""
import json, os
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/05-mariana-trench"
HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 352.0
LAST_END = 343.5          # last word ends here; title card + silence after
# line index -> camera depth (m) at the moment that line starts
DEPTH_AT_LINE = {0: 0.0, 1: 0.0, 2: 0.05, 3: 13, 4: 22, 5: 40, 6: 68, 7: 200, 8: 253, 9: 330, 10: 420,
                 11: 545, 12: 828, 13: 950, 14: 1075, 15: 1200, 16: 1340, 17: 1440, 18: 1610, 19: 1770,
                 20: 1985, 21: 2020, 22: 2150, 23: 3800, 24: 4000, 25: 4550, 26: 4850, 27: 6000, 28: 6250,
                 29: 8000, 30: 8420, 31: 9000, 32: 9800, 33: 10150, 34: 10935}
meta = json.load(open(os.path.join(SCR, "vo_raw", "meta.json")))
L = meta["lines"]
speech = sum(l["dur"] for l in L)
p0 = 0.6
F = (LAST_END - speech - p0) / (sum(l["pause"] for l in L) - L[0]["pause"])
t = 0.0; out = []
for i, l in enumerate(L):
    t += p0 if i == 0 else l["pause"] * F
    out.append(dict(l, start=round(t, 3), end=round(t + l["dur"], 3)))
    t += l["dur"]
keys = [(0.0, 0.0)] + [(out[i]["start"], d) for i, d in sorted(DEPTH_AT_LINE.items())]
print("pause factor", round(F, 3), "speech", round(speech, 1))
for l in out: print(f"{l['i']:02d} {l['shot']:8s} {l['start']:7.2f}-{l['end']:7.2f}  {DEPTH_AT_LINE.get(l['i'],''):>6}  {l['text'][:55]}")
json.dump(dict(voice=meta["voice"], speed=meta["speed"], dur=DUR, pause_factor=F, depth_keys=keys, lines=out),
          open(os.path.join(HERE, "placement.json"), "w"), indent=1)
