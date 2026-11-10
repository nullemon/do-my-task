"""Locked timeline for "IF THE SUN VANISHED RIGHT NOW" (seconds, 24 fps).
Voice line starts = measured Kokoro durations (vo_raw/meta.json) + the pause before each line (GAP), snapped to 0.25 s."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/08-if-the-sun-vanished"
GAP = [("hook1", 0.75), ("hook2", 1.0), ("still", 4.5), ("grav", 1.6), ("dark", 2.6), ("line", 3.2), ("moon", 2.0),
       ("plan1", 2.2), ("plan2", 1.2), ("stars", 2.2), ("photo", 3.0), ("cold1", 1.6), ("cold2", 1.3), ("human", 1.8),
       ("ocean", 2.6), ("vents", 1.8), ("air1", 2.8), ("air2", 1.3), ("floor", 2.2), ("drift", 3.2), ("real1", 4.0),
       ("real2", 1.4), ("end", 2.0)]
TAIL = 7.0
_lock = os.path.join(HERE, "audio", "locked_starts.json")
if os.path.exists(_lock):
    _d = json.load(open(_lock)); START, DURS, DUR = _d["start"], _d["dur"], _d["total"]
else:
    _m = {l["key"]: l["dur"] for l in json.load(open(os.path.join(SCR, "vo_raw", "meta.json")))["lines"]}
    START, DURS, t = {}, {}, 0.0
    for k, g in GAP:
        s = round((t + g) * 4) / 4; START[k] = s; DURS[k] = _m[k]; t = s + _m[k]
    DUR = float(round(t + TAIL))
    json.dump(dict(start=START, dur=DURS, total=DUR), open(_lock, "w"), indent=1)
END = {k: START[k] + DURS[k] for k in START}
NFR = int(round(DUR * FPS))
if __name__ == "__main__":
    for k in START: print(f"{k:6s} {START[k]:7.2f} -> {END[k]:7.2f}")
    print("DUR", DUR, NFR)
