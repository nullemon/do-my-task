"""Locked timeline for "MEGALODON TO SCALE" (seconds, 24 fps).
Voice line starts are fixed here (measured Kokoro durations, see audio/placement.json); every visual reads this.
World units are metres; the diver hovers at the origin; +y is up. The camera is orthographic: (W = frame width in m, cx, cy)."""
import os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
DUR = 316.0
NFR = int(round(DUR * FPS))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/07-megalodon-to-scale"

START = {'hook1': 1.25, 'hook2': 6.5, 'diver': 15.5, 'bull': 27.0, 'gw1': 33.75, 'gw2': 41.75, 'bus': 50.25, 'ws': 53.75,
         'orca': 67.75, 'hump': 76.25, 'megA': 84.25, 'megB': 90.75, 'teeth': 106.5, 'est1': 115.25, 'est2': 124.25,
         'age': 135.5, 'est3': 145.0, 'best': 159.25, 'ceil': 169.0, 'time': 185.75, 'bite': 195.75, 'warm': 205.5,
         'ext': 220.5, 'myth': 238.25, 'twist': 258.5, 'blue': 264.0, 'peru': 274.0, 'end1': 291.25, 'end2': 295.75,
         'end3': 301.75}

# camera keys: (t, W, cx, cy) eased (smoothstep) between consecutive keys
CAM = [
    (0.0, 16.0, 0.0, 3.0), (12.0, 16.0, 0.0, 3.0),
    (16.5, 6.0, 0.35, 0.3), (24.5, 6.0, 0.35, 0.3),
    (28.5, 9.5, 1.6, 0.6), (32.0, 9.5, 1.6, 0.6),
    (36.0, 15.0, 3.0, 0.0), (48.0, 15.0, 3.0, 0.0),
    (52.0, 24.0, 5.0, 1.8), (55.0, 26.0, 6.0, 2.0), (66.0, 27.0, 6.5, 1.5),
    (70.0, 28.0, 7.0, 1.2), (77.0, 34.0, 9.0, 2.5), (83.0, 34.0, 9.0, 2.5),
    (93.0, 38.0, 7.0, 2.0), (236.0, 38.0, 7.0, 2.0), (256.0, 40.0, 7.0, 1.5),
    (267.0, 84.0, 16.0, -3.0), (287.0, 84.0, 16.0, -3.0),
    (294.0, 30.0, 2.0, 2.5), (DUR, 30.0, 2.0, 2.5),
]

# global light level (1 = normal) - fade in, dim for "it is gone", fade to darkness at the end
LIGHT = [(0, 0.0), (3.0, 0.75), (13.0, 0.85), (16.0, 1.0), (236.0, 1.0), (241.0, 0.62), (255.0, 0.62), (262.0, 1.0),
         (300.5, 1.0), (311.0, 0.0), (DUR, 0.0)]


def _ease(keys, t, n):
    ts = [k[0] for k in keys]
    if t <= ts[0]: return keys[0][1:1 + n]
    if t >= ts[-1]: return keys[-1][1:1 + n]
    i = int(np.searchsorted(ts, t, side="right") - 1)
    a, b = keys[i], keys[i + 1]
    u = (t - a[0]) / (b[0] - a[0]); u = u * u * (3 - 2 * u)
    return tuple(a[1 + j] + (b[1 + j] - a[1 + j]) * u for j in range(n))


def cam(t):
    W, cx, cy = _ease(CAM, t, 3)
    # the log-width is what is eased visually: interpolate W geometrically inside each segment
    ts = [k[0] for k in CAM]
    if ts[0] < t < ts[-1]:
        i = int(np.searchsorted(ts, t, side="right") - 1); a, b = CAM[i], CAM[i + 1]
        u = (t - a[0]) / (b[0] - a[0]); u = u * u * (3 - 2 * u)
        W = a[1] * (b[1] / a[1]) ** u
    return W, cx, cy


def light(t):
    return float(np.interp(t, [k[0] for k in LIGHT], [k[1] for k in LIGHT]))


def xpath(keys, t):
    """keys: list of (t, x) with smooth (Catmull-like via smoothstep on velocity) - piecewise linear is fine for glides."""
    return float(np.interp(t, [k[0] for k in keys], [k[1] for k in keys]))


# actors: sprite, drawn length (m), lane y (m), nose-x keys, alpha keys, facing (-1 = swims to -x), style, haze
ACTORS = [
    dict(id="tease", sprite="mega", L=16.4, y=7.6, x=[(0, 11.6), (16, -26.8)], a=[(0, 1), (15, 1), (16.5, 0)], face=-1, style="solid", haze=0.12, blur=3),
    dict(id="diver", sprite="diver", L=2.45, y=0.0, x=[(0, -0.0), (DUR, 0.0)], a=[(0, 1), (DUR, 1)], face=1, style="solid", haze=0.18),
    dict(id="bull", sprite="bull", L=3.3, y=1.75, x=[(24, 7.9), (46, -11.9)], a=[(24, 1), (44, 1), (46, 0)], face=-1, style="solid", haze=0.26),
    dict(id="gw", sprite="gw", L=6.0, y=-2.5, x=[(30, 12.0), (58, -16.0)], a=[(30, 1), (56, 1), (58, 0)], face=-1, style="solid", haze=0.28),
    dict(id="ws", sprite="whaleshark", L=12.0, y=5.4, x=[(52, 21.5), (66, -3.5), (90, -30.0)], a=[(52, 1), (88, 1), (90, 0)], face=-1, style="solid", haze=0.36),
    dict(id="orca", sprite="orca", L=8.0, y=-3.3, x=[(62, 24.2), (92, -23.8)], a=[(62, 1), (90, 1), (92, 0)], face=-1, style="solid", haze=0.3),
    dict(id="hump", sprite="humpback", L=15.0, y=8.6, x=[(71, 27.3), (110, -23.4)], a=[(71, 1), (100, 1), (106, 0)], face=-1, style="solid", haze=0.42),
    # megalodon, 'classic' great-white-shaped (the old picture): arrives, holds, morphs (est3) into the slender form
    dict(id="megc", sprite="gw", L=16.0, y=2.6, x=[(84, 27.0), (88, 18.0), (92, 9.5), (96, 3.5), (100, -0.8), (104, -1.8), (218, -2.6)],
         a=[(84, 1), (146.5, 1), (152.5, 0)], face=-1, style="solid", haze=0.3),
    dict(id="megs", sprite="mega", L=16.4, y=2.6, x=[(100, -0.8), (104, -1.8), (218, -2.6), (222, -4.5), (226, -8.5), (232, -15.5), (240, -25.5)],
         a=[(146.5, 0), (152.5, 1), (238, 1), (240, 0)], face=-1, style="solid", haze=0.3),
    # great white returning as the competitor
    dict(id="gw2", sprite="gw", L=6.0, y=-2.8, x=[(229, 26.5), (252, -8.0), (262, -30.0)], a=[(229, 1), (256, 1), (260, 0)], face=-1, style="solid", haze=0.3),
    # twist: extinct giants as ghosts, the living blue whale solid
    dict(id="megghost", sprite="mega", L=16.4, y=3.0, x=[(256, -3.0), (290, -5.0)], a=[(258, 0), (262, 1), (287, 1), (290, 0)], face=-1, style="ghost", haze=0.0),
    dict(id="blue", sprite="blue", L=29.9, y=-10.0, x=[(258, 66.0), (266, 30.0), (272, 4.0), (277, -6.0), (286, -9.0), (292, -32.0), (296, -62.0)],
         a=[(258, 1), (293, 1), (296, 0)], face=-1, style="solid", haze=0.42),
    dict(id="peru", sprite="perucetus", L=17.0, y=12.5, x=[(272, 2.0), (290, 0.0)], a=[(274.5, 0), (277.5, 1), (287, 1), (290, 0)], face=-1, style="ghost", haze=0.0, static=True),
    # the ending pass: megalodon over the diver, into the dark
    dict(id="megend", sprite="mega", L=16.4, y=4.2, x=[(288.5, 21.0), (316, -34.0)], a=[(288.5, 1), (DUR, 1)], face=-1, style="solid", haze=0.3),
]


def actor_x(a, t): return xpath(a["x"], t)
def actor_alpha(a, t): return float(np.interp(t, [k[0] for k in a["a"]], [k[1] for k in a["a"]], left=0.0, right=0.0)) if a["a"] else 0.0


if __name__ == "__main__":
    pl = json.load(open(os.path.join(HERE, "audio", "placement.json")))["lines"] if os.path.exists(os.path.join(HERE, "audio", "placement.json")) else None
    for t in (0, 10, 16, 30, 40, 60, 80, 95, 150, 200, 265, 280, 300, 310):
        print(t, [round(v, 2) for v in cam(t)], round(light(t), 2))
