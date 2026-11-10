"""WHAT IF OTHER MOONS REPLACED OUR MOON? -- one locked tripod shot of the park (A2_park) at blue hour.
Our Moon is swapped, one after another, for other moons placed at the Moon's distance (384,400 km), each drawn at its
true angular size theta = 2 asin(R/d). The lens is a long telephoto, f = 16,000 px (the classic "giant moon behind the
tree" shot), so every disc keeps its true angular size relative to the others and to the Moon. Every swap: the old
moon swells and implodes, a tinted flash + chromatic shockwave, the new moon blooms in, and the park is relit.
  Moon -> Phobos (a speck, pointer ring) -> Europa -> Io (plumes) -> Titan (haze) -> Ganymede (+ all of them at once)
  -> white flash -> Moon (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5           stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from moons import Body, pole_vec, small_moon, SUN

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S14-other-moons"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
MT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/moons"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 16000.0           # telephoto: discs
F_SKY = 1400.0           # sky gradient / extinction / star field (stylised blue-hour dome)
D_KM = 384400.0
R_MOON = 1737.4
LAMPS = [(191, 1196, 1325), (665, 1209, 1322), (817, 1114, 1322)]       # A2_park lamp heads (source px)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_px(R): return F_PX * math.tan(math.asin(R / D_KM))
def ang_deg(R): return 2 * math.degrees(math.asin(R / D_KM))


# ------------------------------------------------------------------------------------------------ the moons
# R: mean radius (km; IAU / NASA fact sheets). Visual: sky tint (zenith / horizon, linear), glow colour, beam palette,
# park light (tint, gain), star visibility, readout colour.
BODIES = [
    dict(key="moon", name="OUR MOON", R=1737.4, l2="1× MOON'S SIZE", l3="0.52° WIDE", tc=(235, 240, 255),
         zen=(0.0, 0.0, 0.0), hor=(0.0, 0.0, 0.0), glow=(0.60, 0.68, 0.90), gl=1.0,
         beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.12, corona=1.0,
         tint=(0.75, 0.85, 1.10), gain=0.10, stars=1.0, lamps=0.35),
    dict(key="pho", name="PHOBOS", R=11.08, l2="0.006× MOON'S SIZE", l3="0.003° WIDE", tc=(255, 170, 120),
         zen=(0.0, 0.0, 0.004), hor=(0.0, 0.0, 0.0), glow=(1.0, 0.70, 0.45), gl=0.0,
         beams=[(0.30, 1.0, 0.80), (0.35, 0.60, 1.0), (0.70, 0.40, 1.0)], bI=0.05, corona=0.0,
         tint=(0.55, 0.65, 1.0), gain=0.008, stars=1.45, lamps=1.0),
    dict(key="eur", name="EUROPA", R=1560.8, l2="0.9× MOON'S SIZE", l3="0.47° WIDE", tc=(170, 230, 255),
         zen=(0.0, 0.010, 0.030), hor=(0.010, 0.030, 0.050), glow=(0.60, 0.88, 1.0), gl=1.25,
         beams=[(0.45, 0.90, 1.0), (0.85, 0.95, 1.0), (0.40, 0.65, 1.0), (0.75, 0.70, 1.0)], bI=0.22, corona=1.2,
         tint=(0.70, 0.92, 1.25), gain=0.25, stars=0.8, lamps=0.25),
    dict(key="io", name="IO", R=1821.6, l2="1.05× MOON'S SIZE", l3="0.54° WIDE", tc=(255, 225, 90),
         zen=(0.010, 0.006, 0.0), hor=(0.08, 0.035, 0.0), glow=(1.0, 0.75, 0.20), gl=0.9,
         beams=[(1.0, 0.85, 0.20), (1.0, 0.50, 0.10), (0.95, 1.0, 0.35), (1.0, 0.35, 0.15)], bI=0.24, corona=0.6,
         tint=(1.25, 0.95, 0.45), gain=0.23, stars=0.8, lamps=0.25),
    dict(key="tit", name="TITAN", R=2574.7, l2="1.48× MOON'S SIZE", l3="0.77° WIDE", tc=(255, 160, 60),
         zen=(0.015, 0.004, 0.0), hor=(0.11, 0.030, 0.0), glow=(1.0, 0.48, 0.10), gl=1.0,
         beams=[(1.0, 0.55, 0.12), (1.0, 0.35, 0.08), (1.0, 0.75, 0.30), (0.95, 0.40, 0.30)], bI=0.24, corona=0.0,
         tint=(1.30, 0.65, 0.30), gain=0.21, stars=0.8, lamps=0.3),
    dict(key="gan", name="GANYMEDE", R=2634.1, l2="1.52× MOON'S SIZE", l3="0.79° WIDE", tc=(215, 190, 255),
         zen=(0.006, 0.004, 0.020), hor=(0.04, 0.03, 0.05), glow=(0.85, 0.80, 1.0), gl=1.2,
         beams=[(0.75, 0.55, 1.0), (0.40, 0.90, 1.0), (1.0, 0.80, 0.55), (0.95, 0.45, 0.95)], bI=0.26, corona=0.8,
         tint=(0.95, 0.88, 1.20), gain=0.27, stars=0.75, lamps=0.25),
    dict(key="all", name="", R=2634.1, l2="", l3="", tc=(255, 255, 255),
         zen=(0.012, 0.008, 0.022), hor=(0.08, 0.04, 0.05), glow=(1.0, 0.80, 0.85), gl=1.5,
         beams=[(1.0, 0.55, 0.15), (0.45, 0.90, 1.0), (1.0, 0.90, 0.25), (0.80, 0.50, 1.0), (1.0, 0.40, 0.60), (0.40, 1.0, 0.70)],
         bI=0.40, corona=0.6, tint=(1.05, 0.90, 0.95), gain=0.50, stars=0.6, lamps=0.2),
]
EXTRA = [dict(key="tri", name="TRITON", R=1353.4), dict(key="cal", name="CALLISTO", R=2410.3)]
for b in BODIES + EXTRA: b["Rp"] = rad_px(b["R"])
BK = {b["key"]: b for b in BODIES + EXTRA}

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {"pho": wt("pho", "PHOBOS") - 0.10, "eur": LN["eur"]["start"] - 0.06, "io": LN["io"]["start"] - 0.06,
        "tit": LN["tit"]["start"] - 0.06, "gan": LN["gan"]["start"] - 0.06}
T_ALL = LN["all"]["start"] - 0.06
T_BACK = LN["end"]["start"] - 0.08                  # white-out peak -> our lone Moon is back
T_WO0 = T_BACK - 0.70
T_SPECK = wt("pho", "SPECK")
SWAPS = [(T_SW[k], k) for k in ("pho", "eur", "io", "tit", "gan")] + [(T_BACK, "moon2")]
COLLAPSE, BLOOM = 0.42, 0.65
# the finale: the others pop in one by one around Ganymede (order, then 0.17 s apart)
POP_ORDER = ["moon", "eur", "io", "tri", "cal", "tit", "pho"]
T_POP = {k: T_ALL + 0.10 + 0.17 * i for i, k in enumerate(POP_ORDER)}
PULSES = [wt("hook", "MOONS"), wt("moon", "SCALE"), T_SPECK, wt("eur", "ICE"), wt("io", "VOLCANOES"), wt("tit", "HAZE"),
          wt("gan", "BIGGEST"), wt("gan", "MERCURY"), wt("all", "ONCE"), wt("end", "BIGGEST")]


def body_at(t):
    """-> (current key, swap time of current body, next swap time)"""
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("moon" if k == "moon2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


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


# ------------------------------------------------------------------------------------------------ albedo-map prep
def _norm(t):
    return t / max(float(lum(t).mean()), 1e-4)


def _sat(t, s):
    y = lum(t)[..., None]; return np.clip(y + (t - y) * s, 0, None)


def prep_moon(t): return _norm(t)


def prep_europa(t):
    """grayscale USGS mosaic -> water-ice white with reddish-brown lineae and chaos terrain"""
    g = _norm(t).mean(2)
    lo = cv2.GaussianBlur(g, (0, 0), 6)
    dark = np.clip((lo - g) * 3.0 + (1 - lo) * 1.2, 0, 1)
    ice = np.array([0.93, 0.96, 1.0], f32); brown = np.array([0.78, 0.42, 0.24], f32)
    col = ice * (1 - dark[..., None]) + brown * dark[..., None]
    return _norm(col * g[..., None])


def prep_io(t):
    t = _norm(t); y = lum(t)[..., None]
    c = (t - y) * np.array([1.6, 0.35, 1.0], f32)                     # keep the reds / whites, drop the map's green cast
    t = np.clip(y * np.array([1.0, 0.63, 0.19], f32) + c, 0.005, None)   # sulfur-yellow base
    return _norm(t)


def prep_titan(t):
    """the visible body is haze: uniform orange with only a faint hint of the 938 nm surface map"""
    g = _norm(t).mean(2)
    g = 1 + 0.10 * (cv2.GaussianBlur(g, (0, 0), 3) - 1)
    lat = np.linspace(90, -90, g.shape[0], dtype=f32)[:, None]
    g = g * (1 - 0.22 * smooth(35, 75, lat)) * (1 + 0.05 * np.cos(np.radians(lat) * 6))   # darker northern polar hood, faint bands
    col = np.array([1.0, 0.36, 0.06], f32)
    return _norm(col * g[..., None])


def prep_gan(t): return _norm(_sat(_norm(t), 1.35) * np.array([1.02, 0.98, 0.95], f32))
def prep_cal(t): return _norm(_norm(t) * np.array([1.0, 0.88, 0.74], f32))
def prep_tri(t): return _norm(_sat(_norm(t), 1.2) * np.array([1.04, 0.93, 0.90], f32))


# ------------------------------------------------------------------------------------------------ layouts
# single-moon position, the finale positions (Ganymede stays at C), Phobos's speck
POS_V = dict(C=(700.0, 560.0), all={"gan": (700, 560), "tit": (800, 255), "io": (430, 330), "moon": (955, 445),
             "eur": (505, 625), "cal": (905, 800), "tri": (575, 110), "pho": (640, 850)})
POS_W = dict(C=(1280.0, 330.0), all={"gan": (1280, 330), "tit": (1640, 250), "io": (950, 210), "moon": (1580, 560),
             "eur": (960, 440), "cal": (1800, 700), "tri": (1150, 90), "pho": (1440, 640)})


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.vertical = vertical
        self.fg = fg = Foreground(FG_PATH, L, lamps=LAMPS, hz_frac=0.84)
        self.hz = float(fg.horizon)
        P = POS_V if vertical else POS_W
        self.C = P["C"]; self.PA = P["all"]
        self.cam = SkyCam(W, H, self.hz, F_SKY)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.el = np.degrees(np.arctan2(self.hz - yy, F_SKY)).astype(f32)
        e = np.maximum(self.el, 0)
        xr = xx / W
        zen = np.array([0.016, 0.040, 0.150], f32)
        sky = zen * (0.62 + 0.38 * np.exp(-e / 28))[..., None]
        sky += np.array([0.06, 0.085, 0.18], f32) * np.exp(-e / 11)[..., None]
        belt = np.exp(-((e - 9.0) / 6.0) ** 2) * (0.55 + 0.45 * xr)                        # Belt of Venus
        sky += np.array([0.17, 0.070, 0.095], f32) * belt[..., None]
        shadow = np.exp(-e / 3.2)                                                          # Earth's shadow band
        sky = sky * (1 - 0.30 * shadow)[..., None] + np.array([0.025, 0.040, 0.085], f32) * shadow[..., None]
        self.base_sky = sky.astype(f32)
        self.k_hor = np.exp(-e / 14)[..., None].astype(f32)
        # mild atmospheric extinction (elevations of the stylised dome)
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.hz - yyf, F_SKY)), 0.25)
        X = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        tau = np.array([0.06, 0.09, 0.17], f32)
        self.ext = np.exp(-X[:, None] * tau[None, :])[:, None, :].astype(f32) * np.ones((1, W, 1), f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        bp = BK
        self.body = {
            "moon": Body("moon", "8k_moon.jpg", bp["moon"]["Rp"], pole_vec(-12, 4), model="rock", surf=1.15, detail=0.0, prep=prep_moon),
            "eur": Body("eur", f"{MT}/europa-2048.jpg", bp["eur"]["Rp"], pole_vec(10, 6), model="rock", surf=1.30, lon0=2 * math.pi * 0.18,
                        detail=0.03, spin=0.02, rim=(0.10, 0.20, 0.35), prep=prep_europa, seed=11),
            "io": Body("io", f"{MT}/io-2048.jpg", bp["io"]["Rp"], pole_vec(-6, 5), model="rock", surf=0.62, lon0=2 * math.pi * (0.25 - 0.5),
                       detail=0.03, spin=0.0, rim=(0.30, 0.25, 0.08), prep=prep_io, seed=12),
            "tit": Body("tit", f"{MT}/titan-2048.jpg", bp["tit"]["Rp"], pole_vec(8, 10), model="giant", k=0.72, surf=0.46,
                        lon0=2 * math.pi * (0.42 - 0.5), spin=0.02, haze=(0.30, 0.13, 0.03), rim=(0.9, 0.45, 0.12), detail=0.02,
                        prep=prep_titan, seed=13),
            "gan": Body("gan", f"{MT}/ganymede-2048.jpg", bp["gan"]["Rp"], pole_vec(-10, 8), model="rock", surf=0.72,
                        lon0=2 * math.pi * (0.58 - 0.5), spin=0.02, detail=0.03, rim=(0.15, 0.15, 0.25), prep=prep_gan, seed=14),
            "cal": Body("cal", f"{MT}/callisto-2048.jpg", bp["cal"]["Rp"], pole_vec(14, 5), model="rock", surf=0.75,
                        lon0=2 * math.pi * (0.25 - 0.5), spin=0.02, detail=0.03, prep=prep_cal, seed=15),
            "tri": Body("tri", f"{MT}/triton-2048.jpg", bp["tri"]["Rp"], pole_vec(-20, -38), model="rock", surf=0.95,
                        lon0=0.0, spin=0.02, detail=0.03, prep=prep_tri, seed=16),
        }
        # foreground prep: rim light on the skyline
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        yyf2, xxf2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf2, yyf2
        # Io plume particles (ballistic, in units of Io's radius)
        pr = np.random.default_rng(21); n = 900
        self.pl = dict(th=pr.normal(0, 0.42, n), v=pr.uniform(0.75, 1.0, n), ph=pr.uniform(0, 1, n), sz=pr.uniform(0.3, 1.0, n),
                       which=(pr.uniform(0, 1, n) < 0.72).astype(int))
        # glints on the ice of Europa / sparkles
        emph = {"MOONS", "MOON", "PHOBOS", "SPECK", "BARELY", "EUROPA", "ICE", "IO", "VOLCANOES", "TITAN", "1.5×", "HAZE",
                "GANYMEDE", "BIGGEST", "MERCURY", "ALL", "ONCE", "PLANET"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010 if vertical else 600

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        cur, t0, t1 = body_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "moon" if i == 0 else SWAPS[i - 1][1]
        if prev == "gan": prev = "all"
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = BK[prev] if prev else BK[cur]; B = BK[cur]
        if cur == "gan" and t > T_ALL:                                      # the finale: blend Ganymede -> "all"
            A, B, w = BK["gan"], BK["all"], ramp(t, T_ALL, T_POP["pho"] + 0.3)
        return A, B, w, cur, t0, t1

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, cx, cy, col_u, bright):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32) * bright; hor = np.array(lerp(A["hor"], B["hor"], w), f32) * bright
        sky = self.base_sky + zen * (1 - self.k_hor) + hor * self.k_hor
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32); gl = lerp(A["gl"], B["gl"], w)
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - Rp, 0)
        aure = (np.exp(-dd / (30 + 0.6 * Rp)) * 0.30 + np.exp(-dd / (200 + 1.5 * Rp)) * 0.06) * gl * (0.6 + 0.4 * bright)
        sky = sky + aure[..., None] * gcol
        cor = lerp(A["corona"], B["corona"], w)                              # iridescent corona (moonlight in thin cloud)
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
        bI = lerp(A["bI"], B["bI"], w)
        return acc * rad[..., None] * 0.30 * bI

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, A, B, w, light):
        fg = self.fg
        amb_col = np.array([0.22, 0.32, 0.62], f32) * 0.13                       # blue-hour skylight
        night = fg.flat * 0.75 + fg.rgb * 0.25
        def one(S):
            g = S["gain"]
            key = (fg.rgb * 0.45 + fg.flat * 0.55) * np.array(S["tint"], f32) * g
            out = night * amb_col + key
            rc = np.array(S["glow"], f32)
            out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * rc * (0.03 + g * 0.8) * 0.35
            return out
        fb = one(B)
        fgc = fb if w >= 1 else one(A) * (1 - w) + fb * w
        return fgc * light

    def ground_mist(self, t, a, col):
        hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.30 + t * 10) % 512; mv = (sy * 1.1 + t * 3) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 60, hz + 10, sy) * (1 - smooth(hz + 60, hz + 220, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.4 - 0.3, 0, 1), (0, 0), 5)
        return self.up(m * band * a)[..., None] * np.array(col, f32)

    # -------------------------------------------------------------------------------------------- special effects
    def io_plumes(self, img, cx, cy, R, t, amt):
        """two volcanic plumes on Io's limb (Pele-like umbrella ~0.2 R high, a smaller one opposite) + glowing hot spots"""
        if amt <= 0: return
        p = self.pl
        vents = [(math.radians(-128), 1.0), (math.radians(18), 0.55)]          # screen angle of the vent (y down), size
        xs, ys, vals, cols = [], [], [], []
        for k, (ang, s) in enumerate(vents):
            sel = p["which"] == (0 if k == 0 else 1)
            th, v, ph, sz = p["th"][sel], p["v"][sel], p["ph"][sel], p["sz"][sel]
            g = 1.0
            vmax = math.sqrt(2 * g * 0.28 * s)                                  # apex ~0.22 R (x size)
            vv = v * vmax
            Tf = 2 * vv * np.cos(th) / g
            tau = (t * 0.55 + ph) % 1.0
            st = tau * Tf
            h = vv * np.cos(th) * st - 0.5 * g * st * st
            x = vv * np.sin(th) * st
            nx, ny = math.cos(ang), math.sin(ang)                              # outward normal
            px = cx + R * ((1 + h) * nx - x * ny); py = cy + R * ((1 + h) * ny + x * nx)
            xs.append(px); ys.append(py)
            vals.append(sz * (1 - tau) ** 0.7 * (0.6 + 0.4 * np.sin(t * 9 + ph * 40)) * s)
            hot = np.clip(1 - tau * 2.2, 0, 1)[:, None]
            cols.append(np.array([1.0, 0.80, 0.35], f32) * (1 - hot) + np.array([1.0, 0.95, 0.75], f32) * hot)
        xs = np.concatenate(xs); ys = np.concatenate(ys); vals = np.concatenate(vals); cols = np.concatenate(cols)
        pad = int(R * 0.6) + 20
        x0, y0 = int(cx - R - pad), int(cy - R - pad); x1, y1 = int(cx + R + pad), int(cy + R + pad)
        H, W = img.shape[:2]
        x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1c <= x0c or y1c <= y0c: return
        lay = np.zeros((y1 - y0, x1 - x0, 3), f32)
        xi = np.clip((xs - x0).astype(int), 0, x1 - x0 - 1); yi = np.clip((ys - y0).astype(int), 0, y1 - y0 - 1)
        np.add.at(lay, (yi, xi), (vals[:, None] * cols).astype(f32))
        lay = cv2.GaussianBlur(lay, (0, 0), 0.7) * 2.0 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 1.5 + cv2.GaussianBlur(lay, (0, 0), 7) * 0.8
        # bluish scattering canopy (Pele's plume glows blue-white in sunlight) + hot vent glow
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
        for ang, s in vents:
            vx, vy = cx + R * math.cos(ang), cy + R * math.sin(ang)
            ax, ay = cx + R * (1 + 0.20 * s) * math.cos(ang), cy + R * (1 + 0.16 * s) * math.sin(ang)
            dv = np.sqrt((xx - vx) ** 2 + (yy - vy) ** 2); da = np.sqrt((xx - ax) ** 2 + (yy - ay) ** 2)
            shell = np.exp(-((dv - R * 0.28 * s) / (R * 0.045)) ** 2) * smooth(R * 0.98, R * 1.04, np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2))
            lay += (shell * 1.6 * s)[..., None] * np.array([0.35, 0.55, 1.0], f32) * (0.8 + 0.2 * math.sin(t * 3 + s))
            lay += (np.exp(-dv / (R * 0.03)) * 1.2 * s + np.exp(-da / (R * 0.12)) * 0.6 * s)[..., None] * np.array([1.0, 0.55, 0.15], f32)
        img[y0c:y1c, x0c:x1c] += lay[y0c - y0:y1c - y0, x0c - x0:x1c - x0] * amt * 0.65
        # lava hot spots on the disc (flickering)
        for i, (u, v) in enumerate([(-0.45, 0.30), (0.10, -0.35), (0.38, 0.42), (-0.15, 0.62), (0.55, -0.05), (-0.62, -0.25)]):
            fl = 0.7 + 0.3 * noise1(t, 70 + i, 3.0)
            splat(img, cx + u * R, cy + v * R, 10, lambda d, dx, dy: (np.exp(-d / 1.2) * 2.5 + np.exp(-d / 3.5) * 0.3)[..., None]
                  * np.array([1.0, 0.30, 0.05], f32) * fl * amt)

    def titan_haze(self, img, cx, cy, R, t, amt):
        """Titan's thick atmosphere: an orange haze envelope beyond the limb and the thin blue detached haze layer"""
        if amt <= 0: return
        sd = np.array([SUN[0], SUN[1]], f32); sd = sd / np.linalg.norm(sd)
        def fn(d, dx, dy):
            lit = 0.55 + 0.45 * np.clip((dx * sd[0] + dy * sd[1]) / (d + 1e-3), -1, 1)
            o = np.maximum(d - R, 0)
            env = (np.exp(-o / (0.06 * R)) * 1.3 + np.exp(-o / (0.30 * R)) * 0.30) * smooth(R * 0.97, R * 1.005, d)
            blue = np.exp(-((d - R * 1.045) / (0.010 * R)) ** 2) * 0.8
            breathe = 1 + 0.08 * math.sin(t * 2.1)
            return ((env * lit * breathe)[..., None] * np.array([1.0, 0.45, 0.10], f32) + (blue * lit)[..., None] * np.array([0.30, 0.55, 1.0], f32)) * amt
        splat(img, cx, cy, R * 2.2, fn)

    def aurora(self, img, cx, cy, R, t, amt):
        """Ganymede's auroral ovals (it has its own magnetic field), two thin glowing rings round its poles"""
        if amt <= 0: return
        def fn(d, dx, dy):
            out = 0
            for sgn in (-1, 1):
                ey = sgn * 0.80 * R                                         # oval centre (pole region, seen nearly edge-on)
                u = dx / (0.62 * R); v = (dy - ey) / (0.16 * R)
                rr = np.sqrt(u * u + v * v)
                ring = np.exp(-((rr - 1) / 0.10) ** 2)
                front = np.where(v * sgn < 0, 1.0, (d > R) * 1.0)               # far half hidden behind the disc
                out = out + ring * front * (0.8 + 0.2 * np.sin(np.arctan2(v, u) * 5 - t * 4))
            return out[..., None] * np.array([0.35, 1.0, 0.75], f32) * amt
        splat(img, cx, cy, R * 1.4, fn)

    def pointer(self, img, x, y, t, amt):
        """glowing pointer ring round Phobos's speck: ring, four rotating brackets, an outgoing ping"""
        if amt <= 0: return
        col = np.array([0.35, 1.0, 0.85], f32)
        r0 = 46 + 4 * math.sin(t * 5)
        ping = ((t * 1.3) % 1.0)
        def fn(d, dx, dy):
            ring = np.exp(-((d - r0) / 2.2) ** 2) * 2.2
            ang = np.arctan2(dy, dx) - t * 1.6
            br = np.exp(-((d - r0 - 18) / 2.6) ** 2) * (np.cos(ang * 4) > 0.55) * 2.5
            pg = np.exp(-((d - (r0 + 10 + 120 * ping)) / 3.0) ** 2) * (1 - ping) ** 1.5 * 1.8
            halo = np.exp(-np.abs(d - r0) / 14) * 0.25
            return (ring + br + pg + halo)[..., None] * col * amt
        splat(img, x, y, r0 + 150, fn)

    def speck(self, img, x, y, t, I):
        """Phobos itself: 0.46 px radius -- a sparkle, not a disc"""
        tw = 0.8 + 0.2 * math.sin(t * 11) + 0.1 * math.sin(t * 23)
        small_moon(img, x, y, rad_px(11.08), np.array([1.0, 0.85, 0.72], f32) * 3.0, I=I * tw)
        def fn(d, dx, dy):
            sp = (np.exp(-np.abs(dx) / 0.9) * np.exp(-np.abs(dy) / 7) + np.exp(-np.abs(dy) / 0.9) * np.exp(-np.abs(dx) / 7))
            return (sp * 1.6 + np.exp(-d / 1.2) * 4)[..., None] * np.array([1.0, 0.85, 0.72], f32) * I * tw
        splat(img, x, y, 30, fn)

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = BK[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        final = t1 >= T_BACK - 1e-6 and t < T_BACK and cur == "gan"
        col_u = 0.0 if (t1 > 1e8 or final) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        scale = g_in
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        if col_u > 0:                                                         # old moon: swell, then implode to a point
            if col_u < 0.45: scale *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; scale *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        cx, cy = self.C
        Rp = S["Rp"] * scale if cur != "pho" else 3.0
        bright = 1 + 0.5 * (pulse - 1)
        sky, bm, aure = self.sky(t, A, B, w, Rp, cx, cy, col_u, bright)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        sg = lerp(A["stars"], B["stars"], w)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.14, star_gain=1.1, cx=2000, cy=900, rot=6.0)
        img += st * (sg * np.exp(-self.up(aure) * 5))[..., None] * 0.9
        # ---- the moon(s)
        allu = ramp(t, T_ALL, T_ALL + 0.3) if cur == "gan" else 0.0
        if cur == "pho":
            self.speck(img, cx, cy, t, I_mul)
            pa = ramp(t, wt("pho", "WHERE") - 0.1, wt("pho", "WHERE") + 0.25) * (1 - col_u)
            self.pointer(img, cx, cy, t, pa * (1 + 0.6 * math.exp(-((t - T_SPECK) / 0.25) ** 2)))
        else:
            bd = self.body[cur]
            if cur == "tit": self.titan_haze(img, cx, cy, Rp, t, min(I_mul, 2.5) * 0.9)
            bd.render(img, cx, cy, t, I=I_mul, scale=scale, ext=self.ext)
            if cur == "io": self.io_plumes(img, cx, cy, Rp, t, ramp(t, t0 + 0.2, t0 + 0.8) * (1 - col_u) * min(pulse, 1.6))
            if cur == "gan": self.aurora(img, cx, cy, Rp, t, 0.7 * ramp(t, t0 + 0.4, t0 + 1.2) * (1 - 0.5 * allu))
        if cur == "gan" and t > T_ALL:                                        # the finale: all of them at once
            for k in POP_ORDER:
                tp = T_POP[k]
                if t < tp - 0.02: continue
                u = (t - tp) / 0.45; sc = back_out(u)
                px, py = self.PA[k]
                ip = pulse * (0.5 + 0.5 * min(u * 3, 1))
                if k == "pho": self.speck(img, px, py, t, ip); continue
                if k == "tit": self.titan_haze(img, px, py, BK[k]["Rp"] * sc, t, 0.8 * ip)
                self.body[k].render(img, px, py, t, I=ip, scale=sc, ext=self.ext)
                if k == "io": self.io_plumes(img, px, py, BK[k]["Rp"] * sc, t, ramp(t, tp + 0.2, tp + 0.6))
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(A, B, w, light)
        fgc = fgc + self.up(bm) * 0.06 * fg.a[..., None]
        lc = np.array(lerp(A["glow"], B["glow"], w), f32)
        fgc = fgc + self.ground_mist(t, 0.05 + 0.25 * lerp(A["gain"], B["gain"], w), lc * 0.4) * fg.a[..., None]
        fgc = fg.lamps_light(fgc, lerp(A["lamps"], B["lamps"], w) * 0.9, t)
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = BK["moon" if k == "moon2" else k]
                if k == "moon2": continue                                   # the white-out does this one
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(max(NS["glow"]), 1e-3)
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, cx, cy, u, fc)
        if cur == "gan" and t > T_ALL:
            for k in POP_ORDER:
                u = t - T_POP[k]
                if -0.03 < u < 0.5:
                    fc = np.array({"moon": (0.8, 0.85, 1.0), "eur": (0.6, 0.9, 1.0), "io": (1.0, 0.9, 0.3), "tri": (1.0, 0.7, 0.8),
                                   "cal": (0.9, 0.8, 0.7), "tit": (1.0, 0.55, 0.15), "pho": (0.4, 1.0, 0.8)}[k], f32)
                    img += 0.8 * math.exp(-max(u, 0) / 0.07) * ease((u + 0.03) / 0.03) * fc
                    self.shock(img, *self.PA[k], u * 2.4, fc, size=0.55, decay=0.30)     # passes in ~0.5 s
        # ---- final white-out -> our lone Moon
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([0.95, 0.95, 1.0], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.95, 0.95, 1.0], f32)
            self.shock(img, cx, cy, t - T_BACK, np.array([0.8, 0.85, 1.0], f32))
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.0)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.12)
        self.overlay(out, t, cur, t0)
        return out

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)):
            acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.L.W, self.L.H
        o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W
        S = BK[cur]
        if L.vertical: x, ys = W / 2, (1190, 1272, 1330)
        else: x, ys = 440, (790, 865, 920)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "moon" and t > T_BACK: a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if cur == "gan": a *= 1 - ramp(t, T_ALL - 0.2, T_ALL + 0.05)
        if T_WO0 < t < T_BACK: a = 0.0
        if a > 0.01 and S["name"]:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(S["name"]) < 12 else 1.15))
            rgba, _ = word_layer(S["name"], big, W * 0.9 if L.vertical else 760, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.62), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (235, 240, 250), a, 0.10, display=True)
        # finale: a small name under every moon
        if cur == "gan" and T_ALL < t < T_WO0 + 0.2:
            fa = 1 - ramp(t, T_WO0 - 0.1, T_WO0 + 0.2)
            for k in ["gan"] + POP_ORDER:
                la = fa * (ramp(t, T_POP[k] + 0.15, T_POP[k] + 0.4) if k != "gan" else ramp(t, T_ALL, T_ALL + 0.3))
                if la < 0.01: continue
                px, py = self.PA[k]
                r = BK[k]["Rp"] if k != "pho" else 0
                nm = {"moon": "MOON", "eur": "EUROPA", "io": "IO", "tri": "TRITON", "cal": "CALLISTO", "tit": "TITAN",
                      "gan": "GANYMEDE", "pho": "PHOBOS"}[k]
                hud_text(out, nm, px, py + r + 14 + (8 if k == "pho" else 0), int(L.hud_size * 0.40), "Black", (255, 255, 255), la, 0.12, display=True)
        self.caps.draw(out, t)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(vertical, ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render"""
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=16)
    for i in range(int(round(DUR * FPS))):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR)
        for b in BODIES + EXTRA:
            if b["key"] != "all": print(b["key"], round(b["Rp"], 2), "px", round(ang_deg(b["R"]), 4), "deg", round(b["R"] / R_MOON, 4), "x Moon")
        print({k: round(v, 2) for k, v in T_SW.items()}, "all", round(T_ALL, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
