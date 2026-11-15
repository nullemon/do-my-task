"""WHAT IF EARTH HAD MORE MOONS? -- one locked tripod shot of the calm lake and pier (03_calm_lake_wooden_pier.png), from
dusk into night. The sky swaps between moon sets, each moon on a plausible orbit at its TRUE angular size (science.py):
  our Moon -> two Moons (2:1 resonance) -> Mars-style (a Phobos-like moon racing across, Deimos-like specks)
  -> Jupiter-style (Io / Europa / Ganymede / Callisto scaled so Ganymede sits at the Moon's distance; transits, shadows)
  -> Saturn-style (Titan at the Moon's distance, the mid-sized moons, dozens of moonlets, a faint ring arc)
  -> all of them at once (the lake turns choppy) -> white-out -> our Moon + a small companion that merges into it -> loops
Every swap: the old set swells and implodes, a tinted flash + chromatic shockwave + beams, the new set blooms in, and the
lake is relit. The lake mirrors the rendered sky (lake.py: water mask + the photo's own tree/post reflections kept),
with slight perspective ripples and darkening.
Lens: a long telephoto, f = 10,000 px (the frame is ~6.2 deg wide), so every disc keeps its true angular size; the moons
sit low over the far shore, where their reflections land on the open water right of the pier.
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py stills 1.0,9.5          -> SCR/stills/<t>.png
  /home/user/ttsenv/bin/python short.py segs                   restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1, srgb_to_lin
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place
import moons as MO
from moons import Body, pole_vec, small_moon
import science as SC
import lake

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-more-moons"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/03_calm_lake_wooden_pier.png"
MT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/moons"
FPS = 30
LEAD, TAIL = 0.25, 1.40
F_SKY = 1400.0
CAP_Y = 1470                      # captions sit on the pier deck; the sky is kept for the moons
RO_Y = (318, 398, 450)            # readout rows (name / line 2 / line 3)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ Sun / phase
PHASE = math.radians(2.5)                         # the moons sit near opposition (rising at dusk opposite the set Sun)
U_SH = np.array([0.45, -0.89]); U_SH = U_SH / np.linalg.norm(U_SH)   # screen direction shadows are thrown (up-right)
MO.set_sun([-math.sin(PHASE) * U_SH[0], -math.sin(PHASE) * U_SH[1], -math.cos(PHASE)])
SUN_ANG = math.radians(0.2666)                    # the Sun's angular radius (penumbra)

# ------------------------------------------------------------------------------------------------ the moons
# key: (R km, geocentric a km, texture, model/look). Radii in px are the true angular sizes at f = 10,000 px.
G, S_ = SC.GAL, SC.SAT
MOONS = {
    "moon": dict(R=SC.R_MOON, a=SC.D_MOON, name="MOON"),
    "moon2": dict(R=SC.R_MOON, a=SC.A_TWO, name="MOON 2"),
    "pho": dict(R=SC.PHOBOS_R, a=SC.PHOBOS_A, name="PHOBOS-LIKE"),
    "dei": dict(R=SC.DEIMOS_R, a=SC.DEIMOS_A, name="DEIMOS-LIKE"),
    "io": dict(R=G["io"][0], a=G["io"][2] * SC.K_JUP, name="IO"),
    "eur": dict(R=G["eur"][0], a=G["eur"][2] * SC.K_JUP, name="EUROPA"),
    "gan": dict(R=G["gan"][0], a=G["gan"][2] * SC.K_JUP, name="GANYMEDE"),
    "cal": dict(R=G["cal"][0], a=G["cal"][2] * SC.K_JUP, name="CALLISTO"),
    "tit": dict(R=S_["tit"][0], a=S_["tit"][2] * SC.K_SAT, name="TITAN"),
    "rhe": dict(R=S_["rhe"][0], a=S_["rhe"][2] * SC.K_SAT, name="RHEA"),
    "dio": dict(R=S_["dio"][0], a=S_["dio"][2] * SC.K_SAT, name="DIONE"),
    "tet": dict(R=S_["tet"][0], a=S_["tet"][2] * SC.K_SAT, name="TETHYS"),
    "enc": dict(R=S_["enc"][0], a=S_["enc"][2] * SC.K_SAT, name="ENCELADUS"),
    "mim": dict(R=S_["mim"][0], a=S_["mim"][2] * SC.K_SAT, name="MIMAS"),
    "jan": dict(R=S_["jan"][0], a=S_["jan"][2] * SC.K_SAT, name="JANUS"),
    "epi": dict(R=S_["epi"][0], a=S_["epi"][2] * SC.K_SAT, name="EPIMETHEUS"),
    "pro": dict(R=S_["pro"][0], a=S_["pro"][2] * SC.K_SAT, name="PROMETHEUS"),
    "pnd": dict(R=S_["pan"][0], a=S_["pan"][2] * SC.K_SAT, name="PANDORA"),
    "hyp": dict(R=S_["hyp"][0], a=S_["hyp"][2] * SC.K_SAT, name="HYPERION"),
    "comp": dict(R=SC.R_MOON / 3, a=SC.D_MOON, name="COMPANION"),
}
for k, m in MOONS.items():
    m["Rp"] = SC.rad_px(m["R"], m["a"]); m["d"] = SC.d_obs(m["a"])
DISC = {"moon", "moon2", "pho", "io", "eur", "gan", "cal", "tit", "rhe", "dio", "tet", "enc", "mim", "comp"}   # textured spheres

# moonlets for the Saturn swarm: 26 small moons (r 0.35-3.5 px: 4-40 km bodies at 40,000-470,000 km)
_r = np.random.default_rng(77)
MOONLETS = []
while len(MOONLETS) < 26:
    x, y = _r.uniform(40, 1040), _r.uniform(500, 1200)
    if 560 < x < 760 and y < 560: continue
    MOONLETS.append((float(x), float(y), float(_r.uniform(0.35, 1.0) ** 1.6 * 3.0 + 0.35), float(_r.uniform(0, 6.28))))

# ------------------------------------------------------------------------------------------------ the sets
POS = {
    "moon": {"moon": (870, 1075)},
    "two": {"moon": (870, 1075), "moon2": (196, 1092)},
    "mars": {"dei": [(330, 700), (770, 560)]},
    "jup": {"gan": (650, 830), "cal": (200, 600)},          # Io and Europa move (jup_pos)
    "sat": {"tit": (912, 1062), "tet": (380, 820), "dio": (655, 690), "rhe": (205, 1035), "enc": (560, 1075),
            "mim": (985, 770), "jan": (300, 565), "epi": (830, 525), "pro": (505, 925), "pnd": (745, 940), "hyp": (625, 540)},
    "all": {"moon": (870, 1075), "moon2": (930, 915), "io": (300, 1000), "gan": (620, 800), "eur": (470, 1150),
            "cal": (160, 610), "tit": (840, 650), "tet": (395, 640), "dio": (1005, 560), "rhe": (575, 545), "enc": (705, 1010),
            "mim": (150, 830), "jan": (745, 505), "epi": (455, 500), "pro": (560, 960), "pnd": (965, 760), "hyp": (300, 520),
            "dei": [(250, 760), (930, 1010)]},
    "end": {"moon": (870, 1075)},
}
SET = {
    "moon": dict(name="OUR MOON", l2="0.52° WIDE", l3="384,400 KM AWAY", tc=(235, 240, 255), main="moon",
                 glow=(0.60, 0.68, 0.90), gl=1.0, beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.12,
                 corona=1.0, tint=(0.75, 0.85, 1.10), gain=0.10, stars=1.0),
    "two": dict(name="TWO MOONS", l2="2ND MOON: 0.33° WIDE", l3="610,000 KM · 2:1 RESONANCE", tc=(200, 225, 255), main="moon2",
                glow=(0.62, 0.72, 1.0), gl=1.2, beams=[(0.45, 0.75, 1.0), (0.85, 0.65, 1.0), (0.40, 1.0, 0.90), (0.75, 0.85, 1.0)],
                bI=0.20, corona=1.1, tint=(0.75, 0.88, 1.15), gain=0.13, stars=1.0),
    "mars": dict(name="MARS-STYLE", l2="PHOBOS-LIKE: 0.07° WIDE", l3="ONE ORBIT EVERY 7.8 HOURS", tc=(255, 170, 120), main="pho",
                 glow=(1.0, 0.62, 0.40), gl=0.0, beams=[(1.0, 0.45, 0.25), (0.35, 0.60, 1.0), (1.0, 0.70, 0.35), (0.80, 0.40, 1.0)],
                 bI=0.10, corona=0.0, tint=(0.55, 0.65, 1.0), gain=0.012, stars=1.5),
    "jup": dict(name="JUPITER-STYLE", l2="IO 1.38° · GANYMEDE 0.79° WIDE", l3="IO'S TIDES: 20× THE MOON'S", tc=(255, 215, 120), main="gan",
                glow=(1.0, 0.82, 0.50), gl=1.2, beams=[(1.0, 0.85, 0.25), (1.0, 0.55, 0.15), (0.55, 0.85, 1.0), (0.95, 0.60, 0.95)],
                bI=0.24, corona=0.7, tint=(1.15, 0.98, 0.70), gain=0.32, stars=0.75),
    "sat": dict(name="SATURN-STYLE", l2="TITAN 0.77° WIDE", l3="DOZENS OF MOONS + A RING", tc=(255, 200, 140), main="tit",
                glow=(1.0, 0.70, 0.40), gl=1.0, beams=[(1.0, 0.70, 0.30), (0.95, 0.90, 0.60), (0.55, 0.80, 1.0), (1.0, 0.50, 0.25)],
                bI=0.22, corona=0.5, tint=(1.10, 0.90, 0.70), gain=0.24, stars=0.8),
    "all": dict(name="ALL AT ONCE", l2="46 MOONS + A RING", l3="TIDES UP TO 30× TODAY'S", tc=(255, 230, 200), main="gan",
                glow=(1.0, 0.82, 0.80), gl=1.5, beams=[(1.0, 0.55, 0.15), (0.45, 0.90, 1.0), (1.0, 0.90, 0.25), (0.80, 0.50, 1.0),
                                                       (1.0, 0.40, 0.60), (0.40, 1.0, 0.70)],
                bI=0.38, corona=0.6, tint=(1.05, 0.92, 0.95), gain=0.55, stars=0.6),
    "end": dict(name="A LOST MOON?", l2="~1,200 KM WIDE", l3="MAY HAVE MERGED INTO OUR MOON", tc=(235, 240, 255), main="moon",
                glow=(0.60, 0.68, 0.90), gl=1.0, beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.12,
                corona=1.0, tint=(0.75, 0.85, 1.10), gain=0.10, stars=1.0),
}

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {"two": wt("two", "SECOND") - 0.08, "mars": wt("mars", "MARS-STYLE") - 0.08, "jup": wt("jup", "JUPITER'S") - 0.08,
        "sat": wt("sat", "SATURN") - 0.08, "all": LN["all"]["start"] - 0.06}
T_BACK = LN["end_b"]["start"] - 0.10                 # white-out peak -> dusk, our Moon + its lost companion
T_WO0 = T_BACK - 0.80
SWAPS = [(T_SW[k], k) for k in ("two", "mars", "jup", "sat", "all")] + [(T_BACK, "end")]
COLLAPSE, BLOOM = 0.42, 0.65
T_CHAOS0, T_CHAOS1 = LN["phys"]["start"], wt("phys", "CHAOTIC") + 0.4
T_MERGE0, T_MERGE1 = wt("end_c", "MERGED") - 0.25, wt("end_c", "ONE") + 0.05
T_NIGHT0, T_NIGHT1 = 3.0, T_SW["mars"] + 0.6
PULSES = [wt("hook", "MOONS"), wt("moon", "ONE"), wt("two_b", "REFLECTIONS"), wt("mars_b", "RACES"), wt("jup_b", "ECLIPSING"),
          wt("sat_b", "DOZENS"), wt("sat_b", "RING"), wt("all", "ONCE"), wt("phys", "CHAOTIC"), wt("phys_b", "COLLIDE"),
          wt("end_b", "TWO"), wt("end_c", "ONE")]
# the Mars-style set: the Phobos-like moon races across the low sky (left -> right, rising), one pass per set
T_PHO0, T_PHO1 = T_SW["mars"] + 0.25, T_SW["jup"] - 0.2
# the finale: everything pops in, staggered
POP_ORDER = ["moon", "moon2", "io", "eur", "cal", "tit", "tet", "dio", "rhe", "enc", "mim", "jan", "epi", "pro", "pnd", "hyp", "dei"]
T_POP = {k: T_SW["all"] + 0.06 + 0.075 * i for i, k in enumerate(POP_ORDER)}


def set_at(t):
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def prev_of(k):
    ks = ["moon"] + [k_ for _, k_ in SWAPS]
    return ks[ks.index(k) - 1] if ks.index(k) > 0 else None


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def pho_pos(t):
    """the Phobos-like moon: a fast pass across the low sky (rises over the left shore, climbs to the right)"""
    u = (t - T_PHO0) / (T_PHO1 - T_PHO0)
    x = -40 + 1160 * u; y = 1210 - 470 * u + 160 * (u - 0.5) ** 2 * 4 * 0 - 120 * math.sin(math.pi * u) * 0.0
    return x, y, u


def jup_pos(t):
    """Io sweeps right below Ganymede (its shadow crosses Ganymede, then it occults Europa); Europa drifts left"""
    u = (t - T_SW["jup"]) / max(T_SW["sat"] - T_SW["jup"], 1e-3)
    io = (95 + 760 * u, 1062 - 18 * u)
    eur = (845 - 60 * u, 1012)
    return {"io": io, "eur": eur}


# ------------------------------------------------------------------------------------------------ albedo-map prep
def _norm(t): return t / max(float(lum(t).mean()), 1e-4)
def _sat(t, s):
    y = lum(t)[..., None]; return np.clip(y + (t - y) * s, 0, None)


def prep_moon(t): return _norm(t)
def prep_europa(t):
    g = _norm(t).mean(2); lo = cv2.GaussianBlur(g, (0, 0), 6)
    dark = np.clip((lo - g) * 3.0 + (1 - lo) * 1.2, 0, 1)
    col = np.array([0.93, 0.96, 1.0], f32) * (1 - dark[..., None]) + np.array([0.78, 0.42, 0.24], f32) * dark[..., None]
    return _norm(col * g[..., None])
def prep_io(t):
    t = _norm(t); y = lum(t)[..., None]; c = (t - y) * np.array([1.6, 0.35, 1.0], f32)
    return _norm(np.clip(y * np.array([1.0, 0.63, 0.19], f32) + c, 0.005, None))
def prep_titan(t):
    g = _norm(t).mean(2); g = 1 + 0.10 * (cv2.GaussianBlur(g, (0, 0), 3) - 1)
    lat = np.linspace(90, -90, g.shape[0], dtype=f32)[:, None]
    g = g * (1 - 0.22 * smooth(35, 75, lat)) * (1 + 0.05 * np.cos(np.radians(lat) * 6))
    return _norm(np.array([1.0, 0.36, 0.06], f32) * g[..., None])
def prep_gan(t): return _norm(_sat(_norm(t), 1.35) * np.array([1.02, 0.98, 0.95], f32))
def prep_cal(t): return _norm(_norm(t) * np.array([1.0, 0.88, 0.74], f32))
def prep_ice(t): return _norm(_sat(_norm(t), 0.6) * np.array([0.98, 0.99, 1.0], f32))


def phobos_tex():
    """no Phobos map in the cache: a procedural dark-grey, heavily cratered regolith with a big Stickney-like crater and
    grooves (albedo ~0.07, slightly red); written once to SCR"""
    p = os.path.join(SCR, "phobos_proc.png")
    if os.path.exists(p): return p
    h, w = 256, 512
    lat = np.linspace(90, -90, h)[:, None] * np.ones((1, w)); lon = np.linspace(-180, 180, w)[None, :] * np.ones((h, 1))
    g = 0.55 + 0.10 * fbm2((h, w), 5, 2.2)
    r = np.random.default_rng(3)
    for _ in range(140):
        la, lo_, rad = r.uniform(-80, 80), r.uniform(-180, 180), r.uniform(2, 9) ** 1.2
        d = np.hypot((lon - lo_ + 180) % 360 - 180, lat - la)
        g = g - 0.10 * np.exp(-((d - rad * 0.0) / rad) ** 2) + 0.06 * np.exp(-((d - rad) / (rad * 0.25)) ** 2)
    d = np.hypot((lon + 60 + 180) % 360 - 180, lat - 0)
    g = g - 0.22 * np.exp(-(d / 22) ** 2) + 0.12 * np.exp(-((d - 24) / 4) ** 2)
    g = g * (1 - 0.06 * (np.sin(np.radians(lat) * 40) > 0.6))
    col = np.clip(g, 0.05, 1)[..., None] * np.array([1.0, 0.90, 0.82])
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(p)
    return p


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.84)
        self.water, occ, self.YM = lake.load(SCR)
        self.occ = occ
        self.cam = SkyCam(W, H, self.YM, F_SKY)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.maximum(np.degrees(np.arctan2(self.YM - yy, F_SKY)), 0).astype(f32)
        xr = xx / W
        # dusk (blue hour, Belt of Venus over the lake, Earth's shadow band) and night (deep blue, never black)
        zen = np.array([0.016, 0.040, 0.150], f32)
        sky = zen * (0.62 + 0.38 * np.exp(-e / 28))[..., None]
        sky += np.array([0.06, 0.085, 0.18], f32) * np.exp(-e / 11)[..., None]
        belt = np.exp(-((e - 9.0) / 6.0) ** 2) * (0.55 + 0.45 * xr)
        sky += np.array([0.17, 0.070, 0.095], f32) * belt[..., None]
        shadow = np.exp(-e / 3.2)
        self.dusk_sky = (sky * (1 - 0.30 * shadow)[..., None] + np.array([0.025, 0.040, 0.085], f32) * shadow[..., None]).astype(f32)
        nz = np.array([0.0045, 0.010, 0.040], f32)
        self.night_sky = (nz * (0.8 + 0.2 * np.exp(-e / 25))[..., None] + np.array([0.010, 0.016, 0.040], f32) * np.exp(-e / 9)[..., None]
                          + np.array([0.012, 0.012, 0.018], f32) * np.exp(-e / 3)[..., None]).astype(f32)
        self.k_hor = np.exp(-e / 14)[..., None].astype(f32)
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.YM - yyf, F_SKY)), 0.25)
        X = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        self.ext = (np.exp(-X[:, None] * np.array([0.06, 0.09, 0.17], f32)[None, :])[:, None, :] * np.ones((1, W, 1), f32)).astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        M = MOONS
        self.body = {
            "moon": Body("moon", "8k_moon.jpg", M["moon"]["Rp"], pole_vec(-12, 4), model="rock", surf=1.15, detail=0.0, prep=prep_moon),
            "moon2": Body("moon2", "8k_moon.jpg", M["moon2"]["Rp"], pole_vec(20, 6), model="rock", surf=1.20, detail=0.0, lon0=math.pi,
                          prep=prep_moon),
            "comp": Body("comp", "8k_moon.jpg", M["comp"]["Rp"], pole_vec(-30, 10), model="rock", surf=1.1, detail=0.0, lon0=2.0,
                         prep=prep_moon),
            "pho": Body("pho", phobos_tex(), M["pho"]["Rp"] * 1.12, pole_vec(68, 10), q=0.74, model="rock", surf=1.0, detail=0.02, ss=4,
                        seed=31, prep=prep_moon),
            "io": Body("io", f"{MT}/io-2048.jpg", M["io"]["Rp"], pole_vec(-6, 5), model="rock", surf=0.62, lon0=-math.pi / 2, detail=0.03,
                       prep=prep_io, seed=12),
            "eur": Body("eur", f"{MT}/europa-2048.jpg", M["eur"]["Rp"], pole_vec(10, 6), model="rock", surf=1.30, lon0=2 * math.pi * 0.18,
                        detail=0.03, prep=prep_europa, seed=11),
            "gan": Body("gan", f"{MT}/ganymede-2048.jpg", M["gan"]["Rp"], pole_vec(-10, 8), model="rock", surf=0.72, lon0=2 * math.pi * 0.08,
                        detail=0.03, prep=prep_gan, seed=14),
            "cal": Body("cal", f"{MT}/callisto-2048.jpg", M["cal"]["Rp"], pole_vec(14, 5), model="rock", surf=0.75, lon0=-math.pi / 2,
                        detail=0.03, prep=prep_cal, seed=15),
            "tit": Body("tit", f"{MT}/titan-2048.jpg", M["tit"]["Rp"], pole_vec(8, 10), model="giant", k=0.72, surf=0.46, lon0=-0.5,
                        haze=(0.30, 0.13, 0.03), rim=(0.9, 0.45, 0.12), detail=0.02, prep=prep_titan, seed=13),
            "rhe": Body("rhe", f"{MT}/rhea-1024.jpg", M["rhe"]["Rp"], pole_vec(5, 8), model="rock", surf=1.05, detail=0.02, prep=prep_ice, seed=21),
            "dio": Body("dio", f"{MT}/dione-1024.jpg", M["dio"]["Rp"], pole_vec(-8, 4), model="rock", surf=1.10, detail=0.02, prep=prep_ice, seed=22),
            "tet": Body("tet", f"{MT}/tethys-1024.jpg", M["tet"]["Rp"], pole_vec(12, 6), model="rock", surf=1.20, detail=0.02, prep=prep_ice, seed=23),
            "enc": Body("enc", f"{MT}/enceladus-1024.jpg", M["enc"]["Rp"], pole_vec(-4, 12), model="rock", surf=1.55, detail=0.02, prep=prep_ice,
                        seed=24),
            "mim": Body("mim", f"{MT}/mimas-1024.jpg", M["mim"]["Rp"], pole_vec(6, 3), model="rock", surf=1.05, detail=0.02, lon0=-1.2,
                        prep=prep_ice, seed=25),
        }
        # foreground prep: skyline rim light, water geometry
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        yy2, xx2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx2, yy2
        y0 = int(self.YM); self.wy0 = y0
        ys = yy2[y0:]; xs = xx2[y0:]
        h = ys - self.YM + 6.0
        self.w_h = h; self.w_xs = xs; self.w_ys = ys
        self.w_X = (xs - 540) / h; self.w_Z = 600.0 / h                       # water-plane coordinates (perspective)
        self.w_R = (0.86 - 0.42 * np.clip((ys - self.YM) / 574, 0, 1) ** 0.7).astype(f32)   # Fresnel-ish reflectance
        self.ripn = [fbm2((256, 512), 61, 2.3), fbm2((256, 512), 62, 2.0)]
        pine = ((xs < 175) & (ys < 1640)).astype(f32)
        self.w_amp_mask = (1 - 0.85 * cv2.GaussianBlur(pine, (0, 0), 12)).astype(f32)
        # Saturn ring arc: a faint narrow arc low across the sky (radial profile from the Saturn ring strip)
        self.ring = self._ring()
        self.caps = Captions(L, WORDS, emphasis={"MOONS", "ONE", "SECOND", "REFLECTIONS", "MARS-STYLE", "TINY", "RACES", "JUPITER'S",
                                                  "GIANTS", "ECLIPSING", "SATURN", "SWARM", "DOZENS", "RING", "ALL", "ONCE", "CHAOTIC",
                                                  "COLLIDE", "TWO", "MERGED", "MORE", "EARTH"})
        L.cap_y = CAP_Y

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def _ring(self):
        W, H = self.L.W, self.L.H
        cx, cy, R = -900.0, 3450.0, 3300.0
        d = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2) if hasattr(self, "xx") else None
        rr = (d - R)                                                          # px across the band (negative = inside)
        prof = np.asarray(Image.open(os.path.join(MO.TEX, "8k_saturn_ring_alpha.png")).convert("RGBA"), f32).mean(0) / 255.0
        al = np.clip(prof[:, 3] * 1.05, 0, 1); n = len(al)
        wband = 34.0
        u = (rr + wband / 2) / wband
        i = np.clip(u * (n - 1), 0, n - 1).astype(np.int32)
        a = al[i] * ((u > 0) & (u < 1))
        a = cv2.GaussianBlur(a.astype(f32), (0, 0), 0.6)
        along = np.clip((self.xx + 40) / 1160, 0, 1)
        a = a * (0.35 + 0.65 * np.sin(np.pi * along) ** 0.5)                # fades towards the ends of the arc
        col = np.array([0.95, 0.88, 0.76], f32)
        return (a[..., None] * col).astype(f32)

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        cur, t0, t1 = set_at(t)
        prev = prev_of(cur) if t0 > 0 else None
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = SET[prev] if prev else SET[cur]; B = SET[cur]
        return A, B, w, cur, t0, t1

    def dusk(self, t):
        if t >= T_BACK: return 1.0
        return 1.0 - ramp(t, T_NIGHT0, T_NIGHT1)

    def chaos(self, t): return ramp(t, T_CHAOS0, T_CHAOS1) * (1 - ramp(t, T_WO0, T_BACK))

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, cx, cy, col_u, bright, dk):
        base = self.night_sky + (self.dusk_sky - self.night_sky) * dk
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32); gl = lerp(A["gl"], B["gl"], w)
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - Rp, 0)
        aure = (np.exp(-dd / (30 + 0.6 * Rp)) * 0.30 + np.exp(-dd / (200 + 1.5 * Rp)) * 0.06) * gl * (0.6 + 0.4 * bright)
        sky = base + aure[..., None] * gcol * (0.5 + 0.5 * (1 - dk))
        cor = lerp(A["corona"], B["corona"], w)
        if cor > 0.01:
            x = (d - Rp) / 40.0 - 0.15 * t
            ring = np.exp(-np.maximum(d - Rp, 0) / (90 + Rp)) * smooth(Rp + 6, Rp + 40, d)
            sky = sky + palette(x) * (ring * 0.06 * cor)[..., None]
        bm = self.beams_layer(t, A, B, w, Rp, d, np.arctan2(dy, dx), col_u)
        return sky, bm, aure

    def beams_layer(self, t, A, B, w, Rp, d, phi0, col_u):
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = phi0 + twist * np.log(d / 30.0)
        reach = (900 + 1.0 * Rp) * (1 - 0.7 * ease(col_u))
        dd = np.maximum(d - Rp, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"])) * (1 + 0.5 * min(Rp, 300) / 300)
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.25) % 1.0
            c = pal_list(A["beams"], x) * (1 - w) + pal_list(B["beams"], x) * w if w < 1 else pal_list(B["beams"], x)
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.30 * lerp(A["bI"], B["bI"], w)

    # -------------------------------------------------------------------------------------------- the bodies of a set
    def layout(self, k, t):
        """-> list of (key, x, y) for set k at time t (Phobos / Io / Europa move)"""
        P = POS[k]; out = []
        for key, v in P.items():
            if key == "dei":
                out += [("dei", x, y) for x, y in v]
            else:
                out.append((key, float(v[0]), float(v[1])))
        if k == "mars":
            x, y, u = pho_pos(t); out.append(("pho", x, y))
        if k == "jup":
            jp = jup_pos(t); out += [("io", *jp["io"]), ("eur", *jp["eur"])]
        if k == "all":
            x, y, u = pho_pos(T_PHO0 + ((t - T_SW["all"] + 0.6) * 0.42) % 1.0 * (T_PHO1 - T_PHO0)); out.append(("pho", x, y))
        if k == "end":
            if t < T_MERGE1:
                u = ramp(t, T_MERGE0, T_MERGE1)
                mx, my = P["moon"]
                out.append(("comp", mx - 170 + 175 * ease(u) ** 1.4, my - 70 + 70 * ease(u) ** 1.4))
        out.sort(key=lambda e: -MOONS[e[0]]["d"])                      # far -> near
        return out

    def draw_set(self, img, k, t, scale_fn, I_mul, show_pointers=True):
        items = self.layout(k, t)
        boxes = {}
        for i, (key, x, y) in enumerate(items):
            sc = scale_fn(i)
            if sc <= 0.01: continue
            m = MOONS[key]
            if key == "dei":
                tw = 0.85 + 0.15 * math.sin(t * 9 + x)
                small_moon(img, x, y, SC.rad_px(SC.DEIMOS_R, SC.DEIMOS_A) * sc, np.array([1.0, 0.88, 0.75], f32) * 2.4, I=I_mul * tw, ext=self.ext)
                continue
            if key == "hyp" or key in ("jan", "epi", "pro", "pnd"):
                small_moon(img, x, y, m["Rp"] * sc, np.array([0.92, 0.94, 1.0], f32) * (1.6 if key != "hyp" else 2.2), I=I_mul, ext=self.ext)
                continue
            if key == "comp" and k == "end":
                # behind the Moon as it merges: hidden where the Moon's disc covers it (drawn first, Moon on top)
                pass
            bd = self.body[key]
            before = img.copy() if key in ("gan", "eur") and k in ("jup", "all") else None
            if key == "tit": self.titan_haze(img, x, y, m["Rp"] * sc, t, min(I_mul, 2.5) * 0.9)
            box = bd.render(img, x, y, t, I=I_mul, scale=sc, ext=self.ext)
            if key == "pho" and k in ("mars", "all"):
                self.trail(img, k, t, I_mul)
            if before is not None and box is not None:
                self.cast_shadows(img, before, box, key, x, y, items, k, t)
            boxes[key] = (x, y)
        if k == "sat" or k == "all":
            for j, (x, y, r, ph) in enumerate(MOONLETS):
                sc = scale_fn(len(items) + j % 6)
                if sc <= 0.01: continue
                small_moon(img, x, y, r * sc * 0.55, np.array([0.90, 0.92, 1.0], f32) * 1.8, I=I_mul * (0.8 + 0.2 * math.sin(t * 3 + ph)), ext=self.ext)
        return items

    def cast_shadows(self, img, before, box, key, x, y, items, k, t):
        """shadows of nearer moons (rendered later) on this moon; true geometry with the 2.5 deg phase angle and the Sun's
        angular radius (umbra / penumbra)"""
        x0, x1, y0, y1, cov = box
        dB = MOONS[key]["d"]
        f = np.ones((y1 - y0, x1 - x0), f32)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
        hit = False
        for k2, xa, ya in items:
            if k2 not in ("io", "eur") or k2 == key or MOONS[k2]["d"] >= dB: continue
            dA = MOONS[k2]["d"]; RA = MOONS[k2]["R"]; gap = dB - dA
            off = gap / dB * SC.F_PX * math.tan(PHASE)
            sx, sy = xa + off * U_SH[0], ya + off * U_SH[1]
            ru = (RA - gap * math.tan(SUN_ANG)) / dB * SC.F_PX; rp = (RA + gap * math.tan(SUN_ANG)) / dB * SC.F_PX
            dd = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
            if dd.min() > rp: continue
            hit = True
            v = np.clip((dd - ru) / max(rp - ru, 1e-3), 0, 1)
            f = f * (0.025 + 0.975 * (v * v * (3 - 2 * v)))
        if not hit: return
        reg_b = before[y0:y1, x0:x1]; reg_a = img[y0:y1, x0:x1]
        contrib = reg_a - reg_b * (1 - cov[..., None])
        img[y0:y1, x0:x1] = reg_b * (1 - cov[..., None]) + contrib * f[..., None]

    def trail(self, img, k, t, I):
        """a faint motion streak behind the racing Phobos-like moon"""
        for j in range(1, 14):
            if k == "mars": x, y, u = pho_pos(t - j * 0.022)
            else: x, y, u = pho_pos(T_PHO0 + ((t - j * 0.022 - T_SW["all"] + 0.6) * 0.42) % 1.0 * (T_PHO1 - T_PHO0))
            a = (1 - j / 14) ** 2 * 0.22 * I
            splat(img, x, y, 8, lambda d, dx, dy, a=a: (np.exp(-d / 2.2) * a)[..., None] * np.array([1.0, 0.8, 0.6], f32))

    def titan_haze(self, img, cx, cy, R, t, amt):
        if amt <= 0: return
        sd = np.array([MO.SUN[0], MO.SUN[1]], f32); sd = sd / (np.linalg.norm(sd) + 1e-9)
        def fn(d, dx, dy):
            lit = 0.55 + 0.45 * np.clip((dx * sd[0] + dy * sd[1]) / (d + 1e-3), -1, 1)
            o = np.maximum(d - R, 0)
            env = (np.exp(-o / (0.06 * R)) * 1.3 + np.exp(-o / (0.30 * R)) * 0.30) * smooth(R * 0.97, R * 1.005, d)
            blue = np.exp(-((d - R * 1.045) / (0.010 * R)) ** 2) * 0.8
            return ((env * lit)[..., None] * np.array([1.0, 0.45, 0.10], f32) + (blue * lit)[..., None] * np.array([0.30, 0.55, 1.0], f32)) * amt
        splat(img, cx, cy, R * 2.2, fn)

    def pointer(self, img, x, y, t, amt, col=(0.35, 1.0, 0.85), r0=34):
        if amt <= 0: return
        col = np.array(col, f32); r0 = r0 + 3 * math.sin(t * 5); ping = (t * 1.3) % 1.0
        def fn(d, dx, dy):
            ring = np.exp(-((d - r0) / 2.0) ** 2) * 1.8
            ang = np.arctan2(dy, dx) - t * 1.6
            br = np.exp(-((d - r0 - 14) / 2.4) ** 2) * (np.cos(ang * 4) > 0.55) * 2.0
            pg = np.exp(-((d - (r0 + 8 + 90 * ping)) / 3.0) ** 2) * (1 - ping) ** 1.5 * 1.4
            return (ring + br + pg)[..., None] * col * amt
        splat(img, x, y, r0 + 110, fn)

    def ring_arc(self, img, amt, I):
        if amt <= 0.005: return
        img += self.ring * (amt * 0.11 * I)

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    # -------------------------------------------------------------------------------------------- foreground + lake
    def relight(self, A, B, w, light, dk):
        fg = self.fg
        night = fg.flat * 0.75 + fg.rgb * 0.25
        dusk = fg.rgb * np.array([0.46, 0.44, 0.52], f32) * 0.30 + fg.flat * np.array([0.10, 0.13, 0.22], f32) * 0.25
        def one(S):
            g = S["gain"]
            key = (fg.rgb * 0.45 + fg.flat * 0.55) * np.array(S["tint"], f32) * g
            out = night * np.array([0.22, 0.32, 0.62], f32) * 0.10 + key
            out += (self.rim * 0.9)[..., None] * np.array(S["glow"], f32) * (0.03 + g * 0.8) * 0.35
            return out
        fb = one(B); fgc = fb if w >= 1 else one(A) * (1 - w) + fb * w
        return (fgc * (1 - 0.55 * dk) + dusk * dk) * light

    def lake(self, img, skyimg, fgc, t, chaos):
        """the water: the photo's own tree / post / pine reflections (relit) + the rendered sky mirrored about the
        shoreline, both rippled (perspective ripple field, stronger near the camera and when the tides turn chaotic)"""
        y0 = self.wy0; H, W = self.L.H, self.L.W
        h = self.w_h
        amp = (6.0 + 18.0 * chaos) * self.w_amp_mask
        sp = 1.0 + 2.5 * chaos
        n1, n2 = self.ripn
        u = (self.w_X * 150 + 0.0) % 512; v = (self.w_Z * 300 + t * 9 * sp) % 256
        u2 = (self.w_X * 110 + t * 4 * sp) % 512; v2 = (self.w_Z * 180 - t * 6 * sp) % 256
        r1 = cv2.remap(n1, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        r2 = cv2.remap(n2, u2.astype(f32), v2.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        sw = 1.0 + 0.0 * chaos
        dy = (r1 * 0.75 + r2 * 0.45) * amp * (h / 574) ** 1.0 * sw
        dx = (r2 * 0.6 - r1 * 0.2) * amp * 0.18 * (h / 574)
        if chaos > 0:                                                         # long swell rolling towards the camera
            dy = dy + chaos * 9 * np.sin(self.w_Z * 2.2 - t * 3.0)[...] * (h / 574) * self.w_amp_mask
        mx = (self.w_xs + dx).astype(f32); my = (2 * self.YM - self.w_ys + dy).astype(f32)
        refl = cv2.remap(skyimg, mx, np.clip(my, 0, self.YM), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=0.9, sigmaY=1.6)            # a calm lake softens its reflection a little
        Wm = self.water[y0:]; occ = self.occ[y0:]
        # the photo's reflections (trees, posts): displaced a little, sampled premultiplied by the water mask
        px = (self.w_xs + dx * 0.6).astype(f32); py = (self.w_ys + dy * 0.35).astype(f32)
        pw = cv2.remap(np.ascontiguousarray(fgc[y0:] * (Wm * occ)[..., None]), px, py - y0, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        ow = cv2.remap(np.ascontiguousarray(Wm * occ), px, py - y0, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        R = self.w_R * (1 - 0.15 * chaos)
        water = pw * 0.95 + refl * ((1 - np.clip(ow, 0, 1)) * R)[..., None] + np.array([0.002, 0.004, 0.007], f32)
        # glitter on the ripples where they catch the moonlight (needs ripple slope + a bright source above)
        sl = np.abs(r1 - np.roll(r1, 2, 0))
        glit = np.clip(sl - 0.75, 0, None) * (0.5 + 6 * chaos)
        water += refl * (glit * 0.6 * (h / 574) ** 0.5)[..., None]
        img[y0:] = img[y0:] * (1 - Wm[..., None]) + water * Wm[..., None]

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = SET[cur]; dk = self.dusk(t); ch = self.chaos(t)
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        col_u = 0.0 if (t1 > 1e8 or t1 >= T_BACK - 1e-6 and cur == "all") else max(0.0, 1 - (t1 - t) / COLLAPSE)
        items = self.layout(cur, t)
        mk = S["main"] if any(e[0] == S["main"] for e in items) else items[0][0]
        cx, cy = next((x, y) for k_, x, y in items if k_ == mk)
        if cur == "all": cx, cy = 600.0, 880.0
        Rp = MOONS[mk]["Rp"] if mk != "pho" else 6.0
        bright = 1 + 0.5 * (pulse - 1)
        sky, bm, aure = self.sky(t, A, B, w, Rp, cx, cy, col_u, bright, dk)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        sg = lerp(A["stars"], B["stars"], w) * (1 - 0.85 * dk)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.14, star_gain=1.1, cx=2000, cy=900, rot=6.0)
        img += st * (sg * np.exp(-self.up(aure) * 5))[..., None] * 0.9
        # ---- the moons (staggered bloom-in; swell + implode before the next swap)
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        def scale_fn(i):
            if t0 > 0:
                if cur == "all":
                    return 1.0
                s = back_out((t - t0 - 0.06 * i) / BLOOM) if t - t0 - 0.06 * i > 0 else 0.0
            else: s = 1.0
            if col_u > 0:
                if col_u < 0.45: s *= 1 + 0.30 * ease(col_u / 0.45)
                else: v = (col_u - 0.45) / 0.55; s *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            return s
        Im = I_mul * (1 + 3 * col_u ** 2)
        if cur == "all":
            self.draw_all(img, t, Im, ch)
        else:
            if cur == "end": self.draw_end(img, t, Im)
            else: self.draw_set(img, cur, t, scale_fn, Im)
        if cur == "sat": self.ring_arc(img, ramp(t, t0 + 0.3, t0 + 1.3) * (1 - col_u), pulse)
        if cur == "mars":
            pa = ramp(t, t0 + 0.4, t0 + 0.8) * (1 - col_u)
            x, y, u = pho_pos(t)
            self.pointer(img, x, y, t, pa * 0.7 * (1 - ramp(u, 0.92, 1.0)), r0=26)
            for (dx_, dy_) in POS["mars"]["dei"]:
                self.pointer(img, dx_, dy_, t + 0.4, pa * 0.55, col=(1.0, 0.75, 0.45), r0=22)
        skyimg = img.copy()
        # ---- foreground + the lake
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(A, B, w, light, dk)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        self.lake(img, skyimg, fgc, t, ch)
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "end":
                NS = SET[k]
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(max(NS["glow"]), 1e-3)
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                its = self.layout(k, ts + 0.01); m_ = NS["main"]
                sx, sy = next(((x, y) for k_, x, y in its if k_ == m_), (600.0, 880.0))
                if k == "all": sx, sy = 600.0, 880.0
                self.shock(img, sx, sy, u, fc)
        if cur == "all":
            for k in POP_ORDER:
                u = t - T_POP[k]
                if -0.03 < u < 0.5:
                    p = POS["all"][k]; p = p[0] if k == "dei" else p
                    fc = np.array((0.8, 0.85, 1.0), f32)
                    img += 0.5 * math.exp(-max(u, 0) / 0.07) * ease((u + 0.03) / 0.03) * fc
                    self.shock(img, p[0], p[1], u * 2.4, fc, size=0.5, decay=0.30)
        # ---- white-out -> dusk, our Moon and its lost companion
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([0.95, 0.95, 1.0], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.95, 0.95, 1.0], f32)
            self.shock(img, 870, 1075, t - T_BACK, np.array([0.8, 0.85, 1.0], f32))
        if T_MERGE1 - 0.15 < t < T_MERGE1 + 1.2:                              # the merge: a soft glow on the Moon's far limb
            u = t - (T_MERGE1 - 0.15)
            img += 1.2 * math.exp(-u / 0.25) * ease(u / 0.12) * np.array([1.0, 0.9, 0.8], f32)
            self.shock(img, 870, 1075, u, np.array([0.9, 0.9, 1.0], f32), size=0.6, decay=0.4)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.0)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.12)
        self.overlay(out, t, cur, t0)
        return out

    def draw_all(self, img, t, I, ch):
        """the finale: every set at once; each body pops in on its own beat; a small jitter grows with the chaos"""
        items = self.layout("all", t)
        def sfn(i):
            k = items[i][0] if i < len(items) else "jan"
            tp = T_POP.get(k, T_POP["hyp"]) if k != "pho" else T_POP["moon"]
            u = (t - tp) / 0.45
            return back_out(u) if u > 0 else 0.0
        # chaos: the moons drift off their neat places a little (perturbed orbits)
        if ch > 0:
            P0 = {k: v for k, v in POS["all"].items()}
            for k, v in POS["all"].items():
                if k == "dei": continue
                j = 6 * ch
                POS["all"][k] = (v[0] + j * noise1(t, hash(k) % 97, 0.7), v[1] + j * noise1(t, hash(k) % 89 + 5, 0.6))
            self.draw_set(img, "all", t, sfn, I)
            POS["all"].update(P0)
        else:
            self.draw_set(img, "all", t, sfn, I)
        self.ring_arc(img, ramp(t, T_SW["all"] + 0.5, T_SW["all"] + 1.2), 1.0)

    def draw_end(self, img, t, I):
        """our Moon at dusk with a small companion (a third of its width) drifting behind it -> merged"""
        items = self.layout("end", t)
        mx, my = POS["end"]["moon"]
        for k, x, y in items:
            if k == "comp":
                u = ramp(t, T_MERGE0, T_MERGE1)
                a = 1 - ramp(t, T_MERGE1 - 0.15, T_MERGE1)
                self.body["comp"].render(img, x, y, t, I=I * a, scale=1.0, ext=self.ext)
        self.body["moon"].render(img, mx, my, t, I=I, scale=1.0, ext=self.ext)

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0); acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W; S = SET[cur]
        x = W / 2; ys = RO_Y
        start = LN["moon"]["start"] if cur == "moon" else (LN["end_b"]["start"] if cur == "end" else t0)
        a = ramp(t, start + 0.15, start + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "end": a *= 1 - ramp(t, DUR - 0.9, DUR - 0.4)
        if a > 0.01 and S["name"]:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.35 if len(S["name"]) < 12 else 1.15))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            l3 = S["l3"]
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, l3, x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (235, 240, 250), a, 0.10, display=True)
        self.caps.draw(out, t)


def run_stills(ts):
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in ts:
        t0 = time.time(); im = sc.frame(t)
        Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{t:05.2f}.png"))
        print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR)
        for k, m in MOONS.items(): print(f"{k:6s} r = {m['Rp']:7.2f} px  {SC.ang_deg(m['R'], m['a']):.4f} deg  d_obs {m['d']:,.0f} km")
        print({k: round(v, 2) for k, v in T_SW.items()}, "back", round(T_BACK, 2), "merge", round(T_MERGE0, 2), round(T_MERGE1, 2)); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "stills":
        run_stills([float(x) for x in sys.argv[2].split(",")])
