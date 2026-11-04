"""Lock the timeline to the measured voice: line starts = previous end + pause*F (first pause fixed).
Writes placement.json (line timings + shot boundaries) used by both the visuals and the mix."""
import json, os
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 336.0
LAST_END = 328.5          # last word ends here; title card + silence after
meta = json.load(open(os.path.join(SCR, "vo_raw", "meta.json")))
L = meta["lines"]
speech = sum(l["dur"] for l in L)
p0 = 0.8
F = (LAST_END - speech - p0) / (sum(l["pause"] for l in L) - L[0]["pause"])
t = 0.0; out = []
for i, l in enumerate(L):
    t += p0 if i == 0 else l["pause"] * F
    out.append(dict(l, start=round(t, 3), end=round(t + l["dur"], 3)))
    t += l["dur"]
shots = {}
for i, l in enumerate(out):
    s = l["shot"]
    if s not in shots:
        prev_end = out[i - 1]["end"] if i else 0.0
        # cut/transition point: 40% into the preceding pause
        shots[s] = round(prev_end + 0.4 * (l["start"] - prev_end), 3) if i else 0.0
print("pause factor", round(F, 3))
for l in out: print(f"{l['i']:02d} {l['shot']:8s} {l['start']:7.2f}-{l['end']:7.2f}  {l['text'][:60]}")
print(shots)
json.dump(dict(voice=meta["voice"], speed=meta["speed"], dur=DUR, pause_factor=F, shots=shots, lines=out),
          open(os.path.join(HERE, "placement.json"), "w"), indent=1)
