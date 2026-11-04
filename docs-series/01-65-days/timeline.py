"""Locked timeline for "65 DAYS" (seconds, 24 fps). Voice line starts are fixed here; every visual reads this.
Story time ('sim', in days since Earth stopped) is a piecewise-linear function of video time."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "physics"))
FPS = 24
DUR = 266.0
NFR = int(DUR * FPS)
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/01-65-days"

START = {  # voice line key -> start time (s)
 "hook1": 1.5, "hook2": 6.6, "setup1": 15.0, "setup2": 26.0,
 "day1": 37.5, "day1b": 42.4, "day10": 51.0, "seasons": 59.2, "day30": 66.0, "day30b": 72.6,
 "accel1": 84.0, "accel2": 91.2, "venus": 100.0, "venusb": 107.6, "mercury": 115.0,
 "moon": 125.0, "flips": 137.5, "hours13": 151.0, "hours8": 161.0, "oceans": 168.0,
 "hour1": 182.0, "granules": 188.0, "tides": 199.0, "impact": 205.5,
 "after": 223.0, "end1": 231.0, "end2": 238.3, "end3": 246.5,
}
# shots: (name, t0, t1)
SHOTS = [
 ("open",     0.0,  14.5),   # dusk landscape today + title
 ("orbit",   14.5,  36.5),   # Blender S1: Earth in orbit, stops
 ("landA",   36.5,  82.5),   # days 1..33
 ("diagram", 82.5,  98.5),   # side diagram of the straight fall
 ("landB",   98.5, 124.0),   # days 40..58 (Venus, Mercury)
 ("moon",   124.0, 136.0),   # Blender S2: Earth + Moon backlit by the Sun
 ("landC",  136.0, 197.0),   # day flips -> final hours sky
 ("dive",   197.0, 219.5),   # Blender S3: plunge to the photosphere -> white
 ("black",  219.5, 229.5),   # white -> black, "after"
 ("orbitdg",229.5, 253.0),   # orbit = falling and missing
 ("title",  253.0, 266.0),
]
T_IMPACT_D = 64.56010   # days, Earth's surface touches the photosphere (physics/fall.py)
H = 1/24.0
# (video_s, sim_days)
SIM_KEYS = [
 (0.0, -0.40), (34.0, -0.02), (36.5, 0.15), (49.2, 0.97), (51.0, 9.30), (57.0, 10.40), (60.0, 18.0), (66.0, 29.30), (82.5, 33.6),
 (98.5, 39.6), (100.0, 41.16), (115.0, 56.0), (116.2, 56.99), (124.0, 57.9),
 (136.0, 59.0), (140.5, 60.0), (142.3, 62.0), (144.6, 63.0), (151.0, 64.0),
 (161.0, T_IMPACT_D - 8*H), (168.0, T_IMPACT_D - 5*H), (182.0, T_IMPACT_D - 1*H),
 (188.0, T_IMPACT_D - 0.5*H), (197.0, T_IMPACT_D - 12/1440), (218.0, T_IMPACT_D),
]
def sim_of(t):
    xs, ys = zip(*SIM_KEYS)
    return float(np.interp(t, xs, ys))
def shot_of(t):
    for n, a, b in SHOTS:
        if a <= t < b: return n, a, b
    return SHOTS[-1]
if __name__ == "__main__":
    meta = json.load(open(os.path.join(SCR, "vo_raw", "meta.json")))
    keys = list(START)
    for i, m in enumerate(meta["lines"]):
        s = START[m["key"]]; e = s + m["dur"]
        nxt = START[keys[i+1]] if i + 1 < len(keys) else DUR
        print(f"{m['key']:9s} {s:7.2f} - {e:7.2f}  gap {nxt-e:5.2f}  sim {sim_of(s):7.3f}  shot {shot_of(s)[0]}")
        assert nxt - e >= 0.6, m["key"]
