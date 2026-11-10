"""Locked timeline for "WHAT SUNSET LOOKS LIKE ON EVERY PLANET" (seconds, 24 fps).
Voice line starts = measured Kokoro durations (vo_raw/meta.json) + the pause before each line (GAP), snapped to 0.25 s.
SHOTS = one landscape per world; a shot starts LEAD seconds before its first line (the world's title card) and runs to the next."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world"
GAP = [("hook1", 0.6), ("hook2", 1.2), ("earth1", 3.6), ("earth2", 1.2), ("mars1", 3.2), ("mars2", 1.2), ("merc1", 3.2), ("merc2", 1.2),
       ("venus1", 3.2), ("venus2", 1.2), ("jup", 3.2), ("sat", 3.2), ("ura", 3.2), ("titan1", 3.2), ("titan2", 1.2), ("pluto1", 3.2),
       ("pluto2", 1.2), ("kep", 3.2), ("end1", 3.4), ("end2", 1.6)]
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
LEAD = 2.4
_first = [("mars0", "hook1"), ("intro", "hook2"), ("earth", "earth1"), ("mars", "mars1"), ("mercury", "merc1"), ("venus", "venus1"), ("jupiter", "jup"),
          ("saturn", "sat"), ("uranus", "ura"), ("titan", "titan1"), ("pluto", "pluto1"), ("kepler", "kep"), ("recap", "end1"), ("earth2", "end2")]
SHOTS = []
for i, (name, key) in enumerate(_first):
    t0 = 0.0 if i == 0 else (END["hook1"] + 0.5 if name == "intro" else (START[key] - 0.9 if name == "earth2" else START[key] - LEAD))
    SHOTS.append([name, round(t0 * FPS) / FPS, None])
for a, b in zip(SHOTS, SHOTS[1:]): a[2] = b[1]
SHOTS[-1][2] = DUR
SH = {n: (a, b) for n, a, b in SHOTS}
if __name__ == "__main__":
    for k in START: print(f"{k:7s} {START[k]:7.2f} -> {END[k]:7.2f}")
    for s in SHOTS: print(s)
    print("DUR", DUR, NFR)
