"""WHAT THEY SEE OF US - master timeline.

Locks everything to the measured narration: line start times, the camera's log-distance s(t)
(s = log10(distance from Earth in light-years)), every labelled object (its true distance, the
direction it sits in, label text, vignette), caption cards and the end card.
Writes timeline.json, used by comp.py (pictures) and audio/mix.py (sound).

Geometry (same in comp.py and blender/bg_loop.py): Earth at the origin, the camera at (0,0,D) looking
back at Earth (down -z), horizontal FOV 50 deg. An object at true distance d in direction
(theta, phi) sits at d*(sin t cos p, sin t sin p, cos t); it slides in from the frame edge once the
camera is past it, and drifts toward Earth at the centre as we keep receding.
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
VO = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us/vo_raw/meta.json"
FPS = 24
NOW = 2026.84                       # early November 2026
LS = 1.0 / (365.25 * 86400)         # one light-second in light-years
KM = LS / 299792.458                # one km in light-years
AU = 149597870.7 * KM

meta = json.load(open(VO))
ORDER = ["hook", "light", "chase", "moon", "sun", "dot", "proxima", "sirius", "vega", "arct", "caph",
         "radio", "dubhe", "polaris", "betel", "orion", "deneb", "vycma", "twist", "gc", "lmc", "m31",
         "dino", "end1", "end2"]
# pause AFTER each line (s)
GAP = dict(hook=1.9, light=1.2, chase=1.7, moon=1.3, sun=1.5, dot=2.2, proxima=1.6, sirius=1.5, vega=1.7,
           arct=2.4, caph=2.0, radio=2.0, dubhe=1.8, polaris=1.8, betel=1.8, orion=1.6, deneb=1.8,
           vycma=2.4, twist=2.2, gc=1.9, lmc=1.7, m31=2.4, dino=3.0, end1=1.4, end2=0.0)
T0 = 0.7
TAIL = 8.0                          # end card after the last word

lines, t = [], T0
for k in ORDER:
    d = meta[k]["dur"]
    lines.append(dict(key=k, start=round(t, 3), end=round(t + d, 3), dur=round(d, 3), text=meta[k]["text"]))
    t += d + GAP[k]
DUR = math.ceil((lines[-1]["end"] + TAIL) * FPS) / FPS
L = {l["key"]: l for l in lines}

# Subtitle text (digits where the TTS needed words)
SUB = {
 "hook": "Somewhere out there, right now, it is still 1990.",
 "moon": "The Moon sees Earth as it was 1.3 seconds ago.",
 "sun": "The Sun, 8 minutes and 20 seconds ago.",
 "proxima": "Proxima Centauri, our nearest star, 4.2 light-years away, sees the summer of 2022. The James Webb telescope has just opened its eyes.",
 "sirius": "Sirius, the brightest star in our night sky: early 2018.",
 "vega": "Vega, 25 light-years: late 2001. The space station has had people aboard for about a year.",
 "arct": "Arcturus, 37 light-years. And here is something strange. Arcturus is seeing Earth from early 1990, around the very month Voyager turned back and photographed that pale blue dot.",
 "caph": "Caph, in Cassiopeia, 55 light-years: 1972. The last year anyone walked on the Moon.",
 "radio": "Around 100 light-years, we cross the edge of something: our first radio broadcasts, from the 1920s. Beyond this line, no one could have heard us. And even inside it, our signals are almost certainly far too faint to pick out.",
 "dubhe": "Dubhe, in the Big Dipper, 123 light-years. Give or take a couple of years, the first aeroplane is lifting off a beach in North Carolina.",
 "polaris": "Polaris, the North Star, about 446 light-years: around 1580. Ships are crossing oceans, steering by this very star. No one has ever looked through a telescope.",
 "betel": "Betelgeuse, roughly 550 light-years, though that distance is uncertain by a hundred or so. It sees the 1400s, or the 1500s. Cathedrals, and the first printing presses.",
 "orion": "The Orion Nebula, about 1,300 light-years: around the year 700. Maya cities are at their height.",
 "deneb": "Deneb is a mystery. It might be 1,400 light-years away, or 2,600. Either way, it sees the classical world. Rome rising, or Rome falling.",
 "vycma": "VY Canis Majoris, about 3,900 light-years. The Great Pyramid is already centuries old. And on an island in the Arctic, the last woolly mammoths are still alive.",
 "gc": "27,000 light-years: the heart of our galaxy. Earth is in an ice age. Glaciers bury much of the northern continents, and mammoths roam the plains below them.",
 "lmc": "The Large Magellanic Cloud, 160,000 light-years. Our species is young, and lives almost entirely in Africa.",
 "m31": "And Andromeda, 2.5 million light-years away, sees an Earth with no humans at all. Only our distant ancestors, shaping some of the first stone tools.",
 "dino": "66 million light-years out, the asteroid is still falling.",
}
for l in lines:
    l["sub"] = SUB.get(l["key"], l["text"])

# ------------------------------------------------------------------------------------- objects
# kind: body (Earth/Moon/Sun), star, nebula, galaxy.  col = sprite colour.  big = glow scale.
# label: (name, distance line, "sees" line).  vig: vignette id + caption.  line: narration key.
def star(key, name, d, th, ph, col, dist_txt, sees_txt, line=None, vig=None, cap=None, big=1.0,
         minor=False, kind="star", note=None):
    return dict(key=key, name=name, d=d, th=th, ph=ph, col=col, dist=dist_txt, sees=sees_txt, line=line,
                vig=vig, cap=cap, big=big, minor=minor, kind=kind, note=note)

BLUE, WHITE, YEL, ORA, RED = (0.70, 0.80, 1.0), (1.0, 0.98, 0.95), (1.0, 0.92, 0.78), (1.0, 0.78, 0.55), (1.0, 0.62, 0.42)
OBJ = [
 star("moon", "THE MOON", 384400 * KM, 4.0, 205, WHITE, "1.3 LIGHT-SECONDS", "1.3 SECONDS AGO", "moon", kind="moon"),
 star("sun", "THE SUN", AU, 88.0, 180, YEL, "8.3 LIGHT-MINUTES", "8 MIN 20 S AGO", "sun", kind="sun", big=1.0),
 star("proxima", "PROXIMA CENTAURI", 4.2465, 9, 172, RED, "4.25 LIGHT-YEARS", "2022", "proxima", "jwst",
      "JWST'S FIRST IMAGES  ·  JULY 2022", big=0.9),
 star("acen", "ALPHA CENTAURI A·B", 4.37, 14, 150, YEL, "4.37 LY", "2022", minor=True),
 star("barnard", "BARNARD'S STAR", 5.96, 12, 40, RED, "5.96 LY", "LATE 2020", minor=True),
 star("wolf", "WOLF 359", 7.86, 11, 250, RED, "7.86 LY", "2019", minor=True),
 star("sirius", "SIRIUS", 8.60, 9, -12, BLUE, "8.6 LIGHT-YEARS", "EARLY 2018", "sirius", big=1.5),
 star("altair", "ALTAIR", 16.73, 10, 120, WHITE, "16.7 LY", "2010", minor=True),
 star("vega", "VEGA", 25.04, 9, 188, BLUE, "25 LIGHT-YEARS", "LATE 2001", "vega", "iss",
      "THE SPACE STATION  ·  CREWED SINCE NOV 2000", big=1.3),
 star("fomal", "FOMALHAUT", 25.13, 13, 300, WHITE, "25.1 LY", "2001", minor=True),
 star("pollux", "POLLUX", 33.78, 12, 60, ORA, "33.8 LY", "1993", minor=True),
 star("arct", "ARCTURUS", 36.7, 9, 8, ORA, "36.7 ± 0.2 LIGHT-YEARS", "EARLY 1990", "arct", "voyager",
      "VOYAGER 1 LOOKS BACK  ·  14 FEB 1990", big=1.4),
 star("capella", "CAPELLA", 42.9, 12, 215, YEL, "42.9 LY", "1984", minor=True),
 star("castor", "CASTOR", 51.5, 11, 110, WHITE, "≈ 51 LY", "≈ 1975", minor=True),
 star("caph", "CAPH", 54.7, 8, 175, WHITE, "54.7 ± 0.3 LIGHT-YEARS", "1972", "caph", "apollo",
      "APOLLO 16 & 17  ·  1972", big=1.1),
 star("aldeb", "ALDEBARAN", 65.3, 12, 320, ORA, "65 LY", "≈ 1961", minor=True),
 star("regulus", "REGULUS", 79.3, 12, 140, BLUE, "79 LY", "≈ 1947", minor=True),
 star("dubhe", "DUBHE", 123.0, 7, 185, ORA, "123 ± 2 LIGHT-YEARS", "≈ 1904", "dubhe", "flyer",
      "FIRST POWERED FLIGHT  ·  DEC 1903", big=1.2),
 star("spica", "SPICA", 250, 10, 60, BLUE, "≈ 250 LY", "≈ 1775", minor=True),
 star("canopus", "CANOPUS", 310, 9, 240, WHITE, "≈ 310 LY", "≈ 1715", minor=True),
 star("polaris", "POLARIS", 446, 4.5, 0, YEL, "446 ± 1 LIGHT-YEARS", "≈ 1580", "polaris", "ship",
      "THE AGE OF SAIL  ·  NO TELESCOPE UNTIL 1608", big=1.3),
 star("betel", "BETELGEUSE", 548, 4.5, 178, RED, "≈ 550 LIGHT-YEARS  (500–650?)", "≈ 1400s–1500s", "betel",
      "cathedral", "GOTHIC CATHEDRALS  ·  PRINTING PRESS c. 1450", big=1.7),
 star("rigel", "RIGEL", 860, 9, 300, BLUE, "≈ 860 LY", "≈ 1160", minor=True),
 star("orion", "ORION NEBULA", 1344, 5, 10, (1.0, 0.55, 0.75), "≈ 1,300–1,350 LIGHT-YEARS", "≈ AD 700", "orion",
      "maya", "CLASSIC MAYA CITIES  ·  c. AD 700", kind="nebula", big=1.0),
 star("deneb", "DENEB", 2600, 4.5, 190, BLUE, "1,400 – 2,600 LIGHT-YEARS ?", "≈ 600 BC – AD 600", "deneb", "rome",
      "THE CLASSICAL WORLD  ·  ROME", big=1.6, note="DISTANCE VERY UNCERTAIN"),
 star("vycma", "VY CANIS MAJORIS", 3900, 5, 20, RED, "≈ 3,900 LIGHT-YEARS (±400)", "≈ 1900 BC", "vycma", "pyramid",
      "GIZA, BUILT c. 2560 BC  ·  WRANGEL ISLAND MAMMOTHS", big=1.5),
 star("gc", "GALACTIC CENTRE", 27000, 70, 12, YEL, "≈ 27,000 LIGHT-YEARS", "≈ 25,000 BC", "gc", "ice",
      "THE LAST GLACIAL MAXIMUM", kind="gc"),
 star("lmc", "LARGE MAGELLANIC CLOUD", 162000, 16, 222, WHITE, "≈ 160,000 LIGHT-YEARS", "≈ 160,000 YEARS AGO", "lmc",
      "savanna", "HOMO SAPIENS  ·  STILL ALMOST ONLY IN AFRICA", kind="lmc"),
 star("m31", "ANDROMEDA GALAXY", 2.5e6, 8, 30, WHITE, "≈ 2.5 MILLION LIGHT-YEARS", "≈ 2.5 MILLION YEARS AGO", "m31",
      "tools", "NO HUMANS YET  ·  EARLY HOMININ STONE TOOLS", kind="m31"),
]
OBJD = {o["key"]: o for o in OBJ}
DINO_R = 66.0e6

HFOV = math.radians(50.0)
FOC = 960.0 / math.tan(HFOV / 2)


def D_at_alpha(o, alpha_deg):
    th = math.radians(o["th"])
    return o["d"] * math.cos(th) + o["d"] * math.sin(th) / math.tan(math.radians(alpha_deg))


# ------------------------------------------------------------------------- camera keyframes (t, D)
K = []
def key(t, D): K.append((t, math.log10(D)))

arc = OBJD["arct"]
# cold open on Arcturus (flash-forward), slow drift
key(0.0, D_at_alpha(arc, 17.5)); key(L["hook"]["end"] + 1.6, D_at_alpha(arc, 14.5))
COLD_END = L["hook"]["end"] + 1.6
# Earth close-up from the 'light' line, pull back through 'chase'
key(COLD_END + 0.001, 0.110 * LS)
key(L["light"]["end"], 0.150 * LS)
key(L["chase"]["start"] + 2.5, 0.28 * LS)
moon = OBJD["moon"]
key(L["moon"]["start"] - 0.2, D_at_alpha(moon, 21))
key(L["moon"]["end"] + 0.7, D_at_alpha(moon, 7))
sun = OBJD["sun"]
key(L["sun"]["start"] - 0.2, D_at_alpha(sun, 21))
key(L["sun"]["end"] + 0.8, D_at_alpha(sun, 9))
key(L["dot"]["start"] + 0.3, 6.0e9 * KM)
key(L["dot"]["end"], 2.6e10 * KM)
for k in ["proxima", "sirius", "vega", "arct", "caph"]:
    o = OBJD[k]; l = L[k]
    key(l["start"] - 0.25, D_at_alpha(o, 21))
    key(l["end"] + GAP[k] * 0.4, D_at_alpha(o, 9.5))
# radio bubble edge (R = 106 ly) crossed ~45% into the line
key(L["radio"]["start"], 101.0); key(L["radio"]["start"] + 5.0, 106.0); key(L["radio"]["end"] + 0.5, 114.0)
for k in ["dubhe", "polaris", "betel", "orion", "deneb", "vycma"]:
    o = OBJD[k]; l = L[k]
    key(l["start"] - 0.25, D_at_alpha(o, 21))
    key(l["end"] + GAP[k] * 0.4, D_at_alpha(o, 11 if k in ("polaris", "betel") else 9.5))
# the honest twist: rise up out of the galactic disc
key(L["twist"]["start"] + 3, 7.0e3); key(L["twist"]["end"], 3.6e4)
for k in ["gc", "lmc", "m31"]:
    o = OBJD[k]; l = L[k]
    key(l["start"] - 0.25, D_at_alpha(o, 20 if k != "gc" else 21))
    key(l["end"] + GAP[k] * 0.4, D_at_alpha(o, 12 if k != "gc" else 14))
key(L["dino"]["start"] - 0.4, 5.4e7)       # cross the 66-million-light-year shell during the line
key(L["dino"]["start"] + 1.6, 6.6e7)
key(L["dino"]["end"] + 2.0, 1.6e8)
key(L["end1"]["start"] + 2.0, 2.6e8)
key(DUR, 6.0e8)

K.sort()
tk = np.array([k[0] for k in K]); sk = np.array([k[1] for k in K])
for i in range(1, len(K)):
    if not (tk[i] > tk[i - 1]):
        raise SystemExit(f"keyframes not increasing in time at {i}: {K[i-1]} {K[i]}")
    if not (sk[i] > sk[i - 1]) and not (abs(tk[i] - COLD_END) < 0.01):
        raise SystemExit(f"camera not receding at t={tk[i]:.2f}: s {sk[i-1]:.3f} -> {sk[i]:.3f}")


def pchip(x, y, xq):
    """Monotone cubic (Fritsch-Carlson) interpolation; segments are independent at the cold-open cut."""
    h = np.diff(x); dlt = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(y) - 1):
        if dlt[i - 1] * dlt[i] <= 0: m[i] = 0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dlt[i - 1] + w2 / dlt[i])
    m[0] = dlt[0]; m[-1] = dlt[-1]
    i = np.clip(np.searchsorted(x, xq) - 1, 0, len(x) - 2)
    tt = (xq - x[i]) / h[i]
    h00 = 2 * tt**3 - 3 * tt**2 + 1; h10 = tt**3 - 2 * tt**2 + tt; h01 = -2 * tt**3 + 3 * tt**2; h11 = tt**3 - tt**2
    return h00 * y[i] + h10 * h[i] * m[i] + h01 * y[i + 1] + h11 * h[i] * m[i + 1]


NF = int(round(DUR * FPS))
tf = np.arange(NF) / FPS
# cold open and the main flight are interpolated separately
cut = np.searchsorted(tk, COLD_END + 0.0005)
s = np.empty(NF)
m0 = tf < COLD_END
s[m0] = pchip(tk[:cut], sk[:cut], tf[m0])
s[~m0] = pchip(tk[cut:], sk[cut:], tf[~m0])

# ------------------------------------------------------------------------- object show windows
for o in OBJ:
    if o["line"]:
        l = L[o["line"]]
        nxt = lines[ORDER.index(o["line"]) + 1]["start"] if o["line"] != ORDER[-1] else DUR
        o["show"] = [l["start"] - 0.5, nxt - 0.35]
cold = dict(OBJD["arct"]); cold["show"] = [0.25, COLD_END - 0.35]

CARDS = [  # (t0, t1, text, sub)  small caption cards
 (L["light"]["start"] + 4.8, L["light"]["end"] + 0.9, "LIGHT: 299,792 KM EVERY SECOND", ""),
 (L["twist"]["start"] + 3.6, L["twist"]["end"] + 1.6, "TELESCOPE", ""),     # drawn as a diagram in comp.py
]
out = dict(fps=FPS, dur=DUR, nframes=NF, now=NOW, ls=LS, km=KM, au=AU, hfov=HFOV, foc=FOC,
           lines=lines, order=ORDER, obj=OBJ, cold=cold, cold_end=COLD_END, s=s.round(6).tolist(),
           keys=K, cards=CARDS, dino_r=DINO_R, radio_r=106.0,
           title=[lines[-1]["end"] + 1.6, DUR])
json.dump(out, open(os.path.join(HERE, "timeline.json"), "w"), indent=0)
if __name__ == "__main__":
    print(f"duration {DUR:.2f} s, {NF} frames")
    for l in lines:
        print(f"{l['key']:8s} {l['start']:7.2f} - {l['end']:7.2f}   s@start={s[int(l['start']*FPS)]:+.2f}")
