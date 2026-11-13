"""WHAT IF OUR MOON WAS AS BIG AS OTHER MOONS ARE TO THEIR PLANETS? -- one locked tripod shot of the park (A_park),
dusk into night. Our Moon is re-sized so that it has the SAME diameter ratio to Earth that a famous moon has to its own
planet (Phobos/Mars, Ganymede/Jupiter, Titan/Saturn, Triton/Neptune, Charon/Pluto), kept at its real distance
(384,400 km) and drawn at its true angular size theta = 2 asin(R/d) through one fixed telephoto lens (f = 24,000 px,
4.6 deg vertical field of view), so all discs keep their exact relative sizes. Each version wears that moon's map.
Every swap: the old disc swells and implodes, a flash + chromatic shockwave, the new one blooms in; the park is relit
by its moonlight (proportional to the disc's area: a tiny moon -> a dark night, lamps up, stars out). The tiny ones get
a pointer ring, a dashed ghost outline of today's Moon and a zoom loupe. The Charon-ratio Moon (1.9x) rises over the
park. A white-out returns to today's Moon at dusk (loops).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert                    full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5            stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2      re-render only those time ranges
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
from moons import Body, pole_vec, SUN

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-moon-ratios"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A_park.png"
MT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/moons"
CHARON_TEX = os.path.join(SCR, "dl", "charon", "spayly.jpg")
FPS = 30
LEAD, TAIL = 0.25, 1.00
F_PX = 24000.0           # telephoto for the discs (4.6 deg vertical field of view)
F_SKY = 1400.0           # sky gradient / extinction / star field (stylised dusk dome)
D_KM = 384400.0
R_EARTH = 6371.0
R_MOON = 1737.4
LAMPS = [(630, 1185, 1336), (845, 1095, 1342)]       # A_park lamp (head x, head y, pole base y) in SOURCE px

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_px(R): return F_PX * math.tan(math.asin(R / D_KM))
def ang_deg(R): return 2 * math.degrees(math.asin(R / D_KM))
def sig(x, n=2):
    """n significant figures, thousands separators"""
    if x >= 10: p = 10 ** (int(math.floor(math.log10(x))) - n + 1); return f"{round(x / p) * p:,.0f}"
    d = max(n - 1 - int(math.floor(math.log10(x))), 0)
    return f"{x:.{d}f}"


# ------------------------------------------------------------------------------------------------ the moons
# Mean radii (km), NASA/JPL planetary fact sheets: moon / its planet. Our Moon gets the same ratio to Earth.
BODIES = [
    dict(key="moon", moon="OUR MOON", planet="EARTH", Rs=1737.4, Rpl=6371.0, tc=(235, 240, 255),
         glow=(0.60, 0.68, 0.90), beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.14, corona=1.0,
         tint=(0.75, 0.85, 1.10), lamps=0.30, night=0.0, skyl=0.0, stars=0.55),
    dict(key="pho", moon="PHOBOS", planet="MARS", Rs=11.08, Rpl=3389.5, tc=(255, 170, 120),
         glow=(1.0, 0.70, 0.45), beams=[(1.0, 0.55, 0.30), (0.35, 0.60, 1.0), (0.70, 0.40, 1.0)], bI=0.07, corona=0.0,
         tint=(0.55, 0.65, 1.0), lamps=1.0, night=1.0, skyl=0.0, stars=1.45),
    dict(key="gan", moon="GANYMEDE", planet="JUPITER", Rs=2634.1, Rpl=69911.0, tc=(215, 190, 255),
         glow=(0.85, 0.80, 1.0), beams=[(0.75, 0.55, 1.0), (0.40, 0.90, 1.0), (1.0, 0.80, 0.55), (0.95, 0.45, 0.95)], bI=0.10,
         corona=0.0, tint=(0.80, 0.80, 1.15), lamps=0.95, night=1.0, skyl=0.02, stars=1.35),
    dict(key="tit", moon="TITAN", planet="SATURN", Rs=2574.7, Rpl=58232.0, tc=(255, 160, 60),
         glow=(1.0, 0.48, 0.10), beams=[(1.0, 0.55, 0.12), (1.0, 0.35, 0.08), (1.0, 0.75, 0.30), (0.95, 0.40, 0.30)], bI=0.12,
         corona=0.0, tint=(1.20, 0.75, 0.45), lamps=0.95, night=1.0, skyl=0.03, stars=1.3),
    dict(key="tri", moon="TRITON", planet="NEPTUNE", Rs=1353.4, Rpl=24622.0, tc=(255, 185, 205),
         glow=(1.0, 0.72, 0.82), beams=[(1.0, 0.55, 0.70), (0.40, 0.70, 1.0), (0.85, 0.55, 1.0), (0.45, 1.0, 0.90)], bI=0.13,
         corona=0.0, tint=(0.95, 0.82, 1.05), lamps=0.9, night=1.0, skyl=0.04, stars=1.25),
    dict(key="cha", moon="CHARON", planet="PLUTO", Rs=606.0, Rpl=1188.3, tc=(255, 200, 150),
         glow=(0.95, 0.80, 0.85), beams=[(1.0, 0.45, 0.30), (0.85, 0.50, 1.0), (0.40, 0.85, 1.0), (1.0, 0.85, 0.45), (1.0, 0.40, 0.65)],
         bI=0.48, corona=0.9, tint=(0.90, 0.88, 1.10), lamps=0.12, night=1.0, skyl=0.85, stars=0.45),
]
for b in BODIES:
    b["ratio"] = b["Rs"] / b["Rpl"]
    b["R"] = b["ratio"] * R_EARTH                         # our Moon's new radius (km)
    b["D"] = 2 * b["R"]; b["x"] = b["R"] / R_MOON; b["ang"] = ang_deg(b["R"]); b["Rp"] = rad_px(b["R"])
    b["gain"] = 0.10 * max(b["x"] ** 2, 1e-4) ** 0.3     # park moonlight (proportional to the disc area, compressed)
    b["l1"] = f"RATIO OF {b['moon'] if b['key'] != 'moon' else 'MOON'} TO {b['planet']}"
    b["l2"] = sig(b["ratio"])
    b["l3"] = f"OUR MOON WOULD BE {sig(b['D'])} KM" if b["key"] != "moon" else "OUR MOON: 3,475 KM WIDE"
    b["l4"] = (f"{sig(b['x'])}× TODAY'S SIZE · {sig(b['ang'])}°" if b["key"] != "moon" else "1× TODAY'S SIZE · 0.52°")
BK = {b["key"]: b for b in BODIES}
BK["cha"]["gain"] *= 1.6
BK["cha"]["l4"] = f"{BK['cha']['x']:.1f}× TODAY'S SIZE · {BK['cha']['ang']:.2f}°"
BK["end"] = dict(BK["moon"], key="end", l3="BIGGEST MOON OF ANY PLANET", l4="FOR ITS PLANET'S SIZE")
SMALL = ("pho", "gan", "tit", "tri")

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {"pho": LN["pho"]["start"] - 0.06, "gan": LN["gan"]["start"] - 0.06, "tit": LN["tit"]["start"] - 0.06,
        "tri": LN["tri"]["start"] - 0.06, "cha": wt("cha", "CHARON") - 0.12}
T_BACK = wt("end_b", "OURS") - 0.12               # white-out peak -> today's Moon is back
T_WO0 = T_BACK - 0.70
T_RISE = 2.6                                     # the Charon-ratio Moon rises over the park
T_GHOST_C = wt("cha_b", "NEARLY") - 0.1          # ghost of today's Moon inside the big one
T_DOUBLE = wt("cha_c", "DOUBLE")
SWAPS = [(T_SW[k], k) for k in ("pho", "gan", "tit", "tri", "cha")] + [(T_BACK, "end")]
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook", "HUGE"), wt("hook_b", "MOONS"), wt("moon", "27%"), wt("pho", "42 KM"), wt("pho_b", "BARELY"),
          wt("gan", "DOT"), wt("tit", "SPARK"), wt("tri", "5×"), wt("cha", "HALF"), wt("cha_b", "TWICE"), T_DOUBLE,
          wt("end", "DWARF"), wt("end_b", "BIGGEST")]
LOUPE_C, LOUPE_R = (835.0, 255.0), 150


def body_at(t):
    """-> (current key, swap time of current body, next swap time)"""
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
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
def _norm(t): return t / max(float(lum(t).mean()), 1e-4)
def _sat(t, s): y = lum(t)[..., None]; return np.clip(y + (t - y) * s, 0, None)
def prep_moon(t): return _norm(t)
def prep_pho(t): return _norm(_norm(t) * np.array([1.0, 0.86, 0.74], f32))
def prep_gan(t): return _norm(_sat(_norm(t), 1.35) * np.array([1.02, 0.98, 0.95], f32))
def prep_tri(t): return _norm(_sat(_norm(t), 1.2) * np.array([1.04, 0.93, 0.90], f32))


def prep_titan(t):
    """the visible body is haze: uniform orange with only a faint hint of the 938 nm surface map (as ../other-moons)"""
    g = _norm(t).mean(2)
    g = 1 + 0.10 * (cv2.GaussianBlur(g, (0, 0), 3) - 1)
    lat = np.linspace(90, -90, g.shape[0], dtype=f32)[:, None]
    g = g * (1 - 0.22 * smooth(35, 75, lat)) * (1 + 0.05 * np.cos(np.radians(lat) * 6))
    return _norm(np.array([1.0, 0.36, 0.06], f32) * g[..., None])


def prep_charon(t):
    """New Horizons enhanced-colour Charon map: the south (polar night in 2015, never imaged) is black in the map.
    Fill it with the northern terrain mirrored across the equator and shifted 180 deg, desaturated to Charon's grey
    (no second red cap), feathered at the seam. Colour kept slightly muted (the map is enhanced colour)."""
    H, W = t.shape[:2]
    y = lum(t)
    valid = (cv2.GaussianBlur((y > 0.012).astype(f32), (0, 0), 1.5) > 0.98).astype(f32)
    valid[: H // 3] = 1.0                                                  # the north is all imaged
    fill = np.roll(t[::-1], W // 2, axis=1)
    fy = lum(fill)[..., None]; fill = fy * np.array([0.98, 0.98, 1.0], f32)
    fill = cv2.GaussianBlur(fill, (0, 0), 1.0)
    wv = cv2.GaussianBlur(valid, (0, 0), max(H / 200, 2))[..., None]
    wv = np.clip((wv - 0.5) * 2.5 + 0.5, 0, 1)
    out = t * wv + fill * (1 - wv) * float(np.median(y[valid > 0.5]) / max(np.median(fy[..., 0]), 1e-4))
    return _norm(_sat(out, 0.85))


TEXS = dict(moon=("8k_moon.jpg", prep_moon, dict(model="rock", surf=1.15, detail=0.0, pole=pole_vec(-12, 4))),
            pho=(os.path.join(SCR, "dl", "phobos", "spayly.jpg"), prep_pho, dict(model="rock", surf=0.85, detail=0.03, pole=pole_vec(-8, 6), seed=10,
                                                                          lon0=2 * math.pi * (0.345 - 0.5))),
            gan=(f"{MT}/ganymede-2048.jpg", prep_gan, dict(model="rock", surf=0.85, detail=0.03, pole=pole_vec(-10, 8), seed=14,
                                                            lon0=2 * math.pi * (0.58 - 0.5), spin=0.02)),
            tit=(f"{MT}/titan-2048.jpg", prep_titan, dict(model="giant", k=0.72, surf=0.60, detail=0.02, pole=pole_vec(8, 10), seed=13,
                                                         lon0=2 * math.pi * (0.42 - 0.5), spin=0.02, haze=(0.30, 0.13, 0.03))),
            tri=(f"{MT}/triton-2048.jpg", prep_tri, dict(model="rock", surf=1.05, detail=0.03, pole=pole_vec(-20, -38), seed=16, spin=0.02)),
            cha=(CHARON_TEX, prep_charon, dict(model="rock", surf=1.05, detail=0.02, pole=pole_vec(-8, 28), seed=17, spin=0.008)))


def make_body(k, Rp):
    tex, prep, kw = TEXS[k]; kw = dict(kw); pole = kw.pop("pole")
    return Body(k, tex, Rp, pole, prep=prep, **kw)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        assert vertical, "9:16 only"
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=LAMPS, hz_frac=0.68)
        self.hz = float(fg.horizon)
        self.C = (600.0, 545.0)
        self.RISE0 = (690.0, self.hz + 300.0)
        self.cam = SkyCam(W, H, self.hz, F_SKY)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.maximum(np.degrees(np.arctan2(self.hz - yy, F_SKY)), 0).astype(f32)
        xr = xx / W
        # dusk (blue hour) sky
        zen = np.array([0.014, 0.036, 0.135], f32)
        sky = zen * (0.62 + 0.38 * np.exp(-e / 28))[..., None]
        sky += np.array([0.06, 0.08, 0.17], f32) * np.exp(-e / 11)[..., None]
        belt = np.exp(-((e - 9.0) / 6.0) ** 2) * (0.55 + 0.45 * xr)                           # Belt of Venus
        sky += np.array([0.17, 0.070, 0.095], f32) * belt[..., None]
        shadow = np.exp(-e / 3.2)
        sky = sky * (1 - 0.30 * shadow)[..., None] + np.array([0.025, 0.040, 0.085], f32) * shadow[..., None]
        self.blue_sky = sky.astype(f32)
        # night: never pitch black, deep blue with a faint horizon glow
        nsky = np.array([0.005, 0.011, 0.040], f32) * (0.75 + 0.25 * np.exp(-e / 25))[..., None]
        nsky += np.array([0.014, 0.020, 0.044], f32) * np.exp(-e / 7)[..., None]
        self.night_sky = nsky.astype(f32)
        # scattered moonlight (a big bright Moon): Rayleigh blue, brighter low down
        self.moon_sky = (np.array([0.018, 0.045, 0.130], f32) * (0.7 + 0.3 * np.exp(-e / 15))[..., None]
                         + np.array([0.020, 0.035, 0.060], f32) * np.exp(-e / 6)[..., None]).astype(f32)
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.hz - yyf, F_SKY)), 0.25)
        X = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        tau = np.array([0.06, 0.09, 0.17], f32)
        self.ext = np.exp(-X[:, None] * tau[None, :])[:, None, :].astype(f32) * np.ones((1, W, 1), f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # the discs at true size + the loupe versions (same maps, magnified)
        self.body = {k: make_body(k, BK[k]["Rp"]) for k in BK if k != "end"}
        self.body["end"] = self.body["moon"]
        self.RZ = LOUPE_R * 0.62
        self.zoom = {k: make_body(k, self.RZ) for k in SMALL}
        # loupe background stars
        rl = np.random.default_rng(9); n = 2 * LOUPE_R
        ls = np.zeros((n, n, 3), f32)
        for _ in range(70):
            x_, y_ = rl.integers(0, n, 2); ls[y_, x_] = rl.uniform(0.2, 1.5) * np.array([0.85, 0.9, 1.0], f32)
        self.loupe_stars = cv2.GaussianBlur(ls, (0, 0), 0.7) * 3
        # foreground prep: rim light on the skyline
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        yyf2, xxf2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf2, yyf2
        self.fa = np.where(fg.a > 0.9, 1.0, fg.a)[..., None].astype(f32)
        emph = {"HUGE", "EARTH", "MOONS", "27%", "PHOBOS", "MARS", "42 KM", "BARELY", "VISIBLE", "GANYMEDE", "JUPITER", "TINY",
                "DOT", "TITAN", "SATURN", "ORANGE", "SPARK", "TRITON", "NEPTUNE", "5×", "SMALLER", "CHARON", "HALF", "PLUTO",
                "TWICE", "DOUBLE", "WORLD", "DWARF", "BIGGEST", "SIZE", "OURS"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        cur, t0, t1 = body_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "moon" if i == 0 else SWAPS[i - 1][1]
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        if cur == "cha": w = ramp(t, t0 - 0.1, t0 + T_RISE * 0.8)
        A = BK[prev] if prev else BK[cur]; B = BK[cur]
        return A, B, w, cur, t0, t1

    def pos(self, cur, t, t0):
        if cur != "cha": return self.C
        u = min(max((t - t0) / T_RISE, 0), 1); u = 1 - (1 - u) ** 2.2
        return (self.RISE0[0] + (self.C[0] - self.RISE0[0]) * u, self.RISE0[1] + (self.C[1] - self.RISE0[1]) * u)

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, cx, cy, col_u, bright, night, skyl):
        sky = self.blue_sky * (1 - night) + self.night_sky * night + self.moon_sky * skyl * bright
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32)
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - Rp, 0)
        gl = 0.55 + 0.8 * min(Rp / 108.0, 2.0) ** 0.6
        aure = (np.exp(-dd / (25 + 0.45 * Rp)) * 0.30 + np.exp(-dd / (160 + 1.2 * Rp)) * 0.06) * gl * (0.6 + 0.4 * bright)
        sky = sky + aure[..., None] * gcol
        cor = lerp(A["corona"], B["corona"], w)
        if cor > 0.01:                                                       # iridescent corona (thin cloud)
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
    def relight(self, A, B, w, light, night, rise):
        fg = self.fg
        amb = np.array([0.22, 0.32, 0.62], f32) * (0.12 * (1 - night) + 0.045 * night)    # skylight: dusk -> night
        nite = fg.flat * 0.75 + fg.rgb * 0.25
        def one(S):
            g = S["gain"] * (rise if S["key"] == "cha" else 1.0)
            key = (fg.rgb * 0.50 + fg.flat * 0.50) * np.array(S["tint"], f32) * g
            out = nite * amb + key
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
        band = smooth(hz - 60, hz + 10, sy) * (1 - smooth(hz + 60, hz + 240, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.4 - 0.3, 0, 1), (0, 0), 5)
        return self.up(m * band * a)[..., None] * np.array(col, f32)

    # -------------------------------------------------------------------------------------------- effects
    def titan_haze(self, img, cx, cy, R, t, amt):
        """Titan's thick orange haze envelope + the thin blue detached haze layer (as ../other-moons)"""
        if amt <= 0: return
        sd = np.array([SUN[0], SUN[1]], f32); sd = sd / np.linalg.norm(sd)
        def fn(d, dx, dy):
            lit = 0.55 + 0.45 * np.clip((dx * sd[0] + dy * sd[1]) / (d + 1e-3), -1, 1)
            o = np.maximum(d - R, 0)
            env = (np.exp(-o / (0.06 * R)) * 1.3 + np.exp(-o / (0.30 * R)) * 0.30) * smooth(R * 0.97, R * 1.005, d)
            blue = np.exp(-((d - R * 1.045) / max(0.010 * R, 0.6)) ** 2) * 0.8
            breathe = 1 + 0.08 * math.sin(t * 2.1)
            return ((env * lit * breathe)[..., None] * np.array([1.0, 0.45, 0.10], f32) + (blue * lit)[..., None] * np.array([0.30, 0.55, 1.0], f32)) * amt
        splat(img, cx, cy, R * 2.2 + 4, fn)

    def speck(self, img, x, y, t, I):
        """the Phobos-ratio Moon: 1.3 px radius -- a twinkling sparkle on top of its tiny disc"""
        tw = 0.8 + 0.2 * math.sin(t * 11) + 0.1 * math.sin(t * 23)
        def fn(d, dx, dy):
            sp = (np.exp(-np.abs(dx) / 0.9) * np.exp(-np.abs(dy) / 8) + np.exp(-np.abs(dy) / 0.9) * np.exp(-np.abs(dx) / 8))
            return (sp * 0.9 + np.exp(-d / 2.0) * 0.8)[..., None] * np.array([1.0, 0.88, 0.76], f32) * I * tw
        splat(img, x, y, 34, fn)

    def pointer(self, img, x, y, Rp, t, amt, col):
        """glowing pointer ring round a tiny disc: ring, four rotating brackets, an outgoing sonar ping"""
        if amt <= 0: return
        r0 = Rp + 30 + 4 * math.sin(t * 5)
        ping = ((t * 1.1) % 1.0)
        def fn(d, dx, dy):
            ring = np.exp(-((d - r0) / 2.4) ** 2) * 2.2
            ang = np.arctan2(dy, dx) - t * 1.6
            br = np.exp(-((d - r0 - 20) / 2.8) ** 2) * (np.cos(ang * 4) > 0.55) * 2.6
            pg = np.exp(-((d - (r0 + 10 + 150 * ping)) / 3.2) ** 2) * (1 - ping) ** 1.5 * 1.8
            halo = np.exp(-np.abs(d - r0) / 14) * 0.25
            return (ring + br + pg + halo)[..., None] * col * amt
        splat(img, x, y, r0 + 180, fn)

    def ghost(self, img, x, y, t, amt, R=None, col=(0.85, 0.90, 1.0), dark=0.0):
        """dashed outline of today's Moon at its true size (for comparison)"""
        if amt <= 0: return
        R = R or BK["moon"]["Rp"]
        def fn(d, dx, dy):
            ang = np.arctan2(dy, dx)
            dash = smooth(-0.15, 0.15, np.cos(ang * 36 - t * 0.9))
            line = np.exp(-((d - R) / 1.7) ** 2) * dash * 1.4 + np.exp(-np.abs(d - R) / 9) * 0.10
            return line[..., None] * np.array(col, f32) * amt
        if dark > 0:
            x0, x1, y0, y1 = int(x - R - 8), int(x + R + 9), int(y - R - 8), int(y + R + 9)
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32) + 0.5
            dd = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
            dash = smooth(-0.15, 0.15, np.cos(np.arctan2(yy - y, xx - x) * 36 - t * 0.9))
            img[y0:y1, x0:x1] *= (1 - dark * np.exp(-((dd - R) / 3.2) ** 2) * (0.5 + 0.5 * dash))[..., None]
        splat(img, x, y, R + 40, fn)

    def loupe(self, img, t, k, amt, I, bgc, tw):
        """circular zoom inset (top right): the tiny disc, magnified, with a rotating rainbow rim + a leader line"""
        if amt <= 0.01: return
        lx, ly = LOUPE_C; r = LOUPE_R; pad = 28; n = 2 * (r + pad); c = r + pad
        x0, y0 = int(lx - c), int(ly - c)
        patch = np.ones((n, n, 3), f32) * np.array(bgc, f32)
        patch[pad:pad + 2 * r, pad:pad + 2 * r] += self.loupe_stars * 0.5
        sc = back_out(tw) if tw < 1 else 1.0
        if k == "tit": self.titan_haze(patch, c, c, self.RZ * sc, t, I * 0.8)
        self.zoom[k].render(patch, c, c, t, I=I, scale=max(sc, 0.02))
        yy, xx = np.mgrid[0:n, 0:n].astype(f32) + 0.5
        dx, dy = xx - c, yy - c; d = np.sqrt(dx * dx + dy * dy)
        m = np.clip(r - 3 - d, 0, 1)[..., None] * amt
        rim_x = np.arctan2(dy, dx) / (2 * np.pi) + 0.25 * t
        rim = (np.exp(-((d - r + 3) / 2.6) ** 2) * 2.4 + np.exp(-np.abs(d - r + 3) / 8) * 0.35 * smooth(r + pad - 2, r + 4, d))[..., None] \
            * (0.35 + palette(rim_x)) * amt
        reg = img[y0:y0 + n, x0:x0 + n]
        img[y0:y0 + n, x0:x0 + n] = reg * (1 - m) + patch * m + rim
        # leader line: from the pointer ring towards the loupe
        cx, cy = self.C
        vx, vy = lx - cx, ly - cy; L_ = math.hypot(vx, vy); ux, uy = vx / L_, vy / L_
        a0 = BK["moon"]["Rp"] + 12; a1 = L_ - r - 6
        def fn(dd, ddx, ddy):
            s = ddx * ux + ddy * uy; p = np.abs(-ddx * uy + ddy * ux)
            inside = smooth(a0, a0 + 10, s) * smooth(a1, a1 - 10, s)
            flow = 0.55 + 0.45 * np.cos(s / 9.0 - t * 9)
            return (np.exp(-(p / 1.3) ** 2) * inside * flow * 1.4)[..., None] * np.array([0.6, 0.95, 1.0], f32) * amt
        splat(img, cx, cy, L_, fn)

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
        g_in = back_out(u_in) if t0 > 0 and cur not in ("cha", "end") else 1.0
        nxt_k = [k for ts, k in SWAPS if ts > t]
        col_u = 0.0 if (t1 > 1e8 or (nxt_k and nxt_k[0] in ("cha", "end"))) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        scale = g_in
        I_mul = 1 + 0.25 * (pulse - 1)
        if t0 > 0 and cur not in ("cha", "end"): I_mul *= 0.4 + 0.6 * min(max(u_in * 3, 0), 1)
        if col_u > 0:                                                         # old disc: swell, then implode to a point
            if col_u < 0.45: scale *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; scale *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        cx, cy = self.pos(cur, t, t0)
        Rp = S["Rp"] * scale
        rise = 0.25 + 0.75 * smooth(self.hz + 120, self.C[1] + 150, cy) if cur == "cha" else 1.0
        night = lerp(A["night"], B["night"], w)
        if cur == "moon": night = 0.0
        night = min(night, 1.0)
        skyl = lerp(A["skyl"], B["skyl"], w) * (rise if cur == "cha" else 1.0)
        bright = 1 + 0.5 * (pulse - 1)
        sky, bm, aure = self.sky(t, A, B, w, max(Rp, 1.0), cx, cy, col_u, bright, night, skyl)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        sg = lerp(A["stars"], B["stars"], w) * (0.45 + 0.55 * night) if cur != "moon" else BK["moon"]["stars"] * 0.6
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.14, star_gain=1.1, cx=2000, cy=900, rot=6.0)
        img += st * (sg * np.exp(-self.up(aure) * 5))[..., None] * 0.9
        # ---- the disc
        bd = self.body[cur]
        if cur == "tit": self.titan_haze(img, cx, cy, Rp, t, min(I_mul, 2.5) * 0.9)
        bd.render(img, cx, cy, t, I=I_mul, scale=scale, ext=self.ext)
        if cur == "pho": self.speck(img, cx, cy, t, I_mul * (1 - col_u))
        # ---- comparison aids for the tiny ones: ghost of today's Moon, pointer ring, loupe
        if cur in SMALL:
            ga = ramp(t, t0 + 0.35, t0 + 0.8) * (1 - col_u * 0.8) if cur == "pho" else (1 - col_u * 0.8)
            self.ghost(img, cx, cy, t, 0.55 * ga)
            pc = np.array([0.35, 1.0, 0.85], f32) * 0.6 + np.array(S["glow"], f32) * 0.4
            pa = ramp(t, t0 + 0.15, t0 + 0.45) * (1 - col_u)
            if cur == "pho": pa *= 1 + 0.6 * math.exp(-((t - wt("pho_b", "BARELY")) / 0.25) ** 2)
            self.pointer(img, cx, cy, Rp, t, pa, pc)
        la = (ramp(t, T_SW["pho"] + 0.5, T_SW["pho"] + 0.9) if cur in SMALL else 0.0) * (1 - ramp(t, T_SW["cha"] - 0.35, T_SW["cha"] - 0.05))
        if la > 0.01:
            tw = (t - (T_SW["pho"] + 0.5)) / 0.6 if cur == "pho" else (t - t0) / 0.55
            bgc = np.array([0.006, 0.012, 0.040], f32) * (1 + 2 * night)
            self.loupe(img, t, cur, la, 1.0 + 0.3 * (pulse - 1), bgc, tw)
        if cur == "cha":                                                      # the ghost of today's Moon inside the big one
            gc = ramp(t, T_GHOST_C, T_GHOST_C + 0.35) * (1 - ramp(t, T_SW["cha"] + 99, 1e9)) * (1 - ramp(t, wt("end", "PLUTO'S"), wt("end", "PLUTO'S") + 0.4))
            if gc > 0: self.ghost(img, cx, cy, t, 2.2 * gc, col=(0.45, 0.95, 1.0), dark=0.75 * gc)
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        if cur == "cha": light *= 1 + 0.25 * math.exp(-((t - T_DOUBLE) / 0.35) ** 2)
        fgc = self.relight(A, B, w, light, night, rise)
        fgc = fgc + self.up(bm) * 0.06 * fg.a[..., None]
        lc = np.array(lerp(A["glow"], B["glow"], w), f32)
        fgc = fgc + self.ground_mist(t, 0.05 + 0.25 * lerp(A["gain"], B["gain"], w), lc * 0.4) * fg.a[..., None]
        fgc = fg.lamps_light(fgc, lerp(A["lamps"], B["lamps"], w) * 0.9, t)
        a = self.fa                                                           # plate in front (opaque where alpha > 0.9)
        img = img * (1 - a) + fgc * a
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                if k == "end": continue                                       # the white-out does this one
                NS = BK[k]
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(NS["glow"])
                fI = 3.0 if k != "cha" else 3.6
                img += (fI * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, *(self.C if k != "cha" else (cx, self.hz)), u, fc, size=1.0 if k != "cha" else 1.3)
        if cur == "cha":
            u = t - T_DOUBLE
            if -0.05 < u < 1.4:
                fc = np.array([0.95, 0.75, 1.0], f32)
                img += (1.4 * math.exp(-max(u, 0) / 0.10) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, cx, cy, u, fc, size=1.2)
        # ---- final white-out -> today's Moon at dusk
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([0.95, 0.95, 1.0], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.95, 0.95, 1.0], f32)
            self.shock(img, cx, cy, t - T_BACK, np.array([0.8, 0.85, 1.0], f32))
        img = self.chroma_bloom(img, 1.0)
        expo = 1.0 / (1 + 0.20 * min(skyl, 1.5))
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.12)
        self.overlay(out, t, cur, t0, la)
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

    def overlay(self, out, t, cur, t0, la=0.0):
        L = self.L; W = L.W
        S = BK[cur]
        x, ys = W / 2, (1160, 1240, 1318, 1368)
        a = ramp(t, max(t0, LN["moon"]["start"] - 0.2) + 0.15, max(t0, LN["moon"]["start"] - 0.2) + 0.45)
        if cur == "cha": a = ramp(t, t0 + 0.9, t0 + 1.2)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "end": a = ramp(t, T_BACK + 0.5, T_BACK + 0.8) * (1 - ramp(t, DUR - 0.7, DUR - 0.2))
        if T_WO0 < t < T_BACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            hud_text(out, S["l1"], x, ys[0] + dy, int(L.hud_size * 0.50), "Black", (235, 240, 250), a, 0.10, display=True)
            rgba, _ = word_layer(S["l2"], int(L.hud_size * 1.55), W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[1] + dy, a)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.56), "Black", (255, 226, 150), a, 0.06, display=True)
            hud_text(out, S["l4"], x, ys[3] + dy, int(L.hud_size * 0.48), "Bold", (190, 230, 255), a, 0.08, display=True)
        if la > 0.01 and cur in SMALL:                                        # loupe labels
            lx, ly = LOUPE_C
            z = self.RZ / S["Rp"]
            hud_text(out, f"ZOOM ×{z:.0f}", lx, ly + LOUPE_R + 26, int(L.hud_size * 0.42), "Black", (150, 240, 255), la, 0.10, display=True)
        if cur in SMALL:                                                      # ghost label
            ga = ramp(t, t0 + 0.4, t0 + 0.8) if cur == "pho" else 1.0
            nxt_ = [ts for ts, k in SWAPS if ts > t]
            if nxt_ and nxt_[0] == T_SW["cha"]: ga *= 1 - ramp(t, nxt_[0] - 0.35, nxt_[0] - 0.1)
            cx, cy = self.C
            hud_text(out, "TODAY'S MOON", cx, cy + BK["moon"]["Rp"] + 24, int(L.hud_size * 0.34), "Bold", (200, 215, 240), 0.8 * ga, 0.12, display=True)
        if cur == "cha":
            gc = ramp(t, T_GHOST_C + 0.1, T_GHOST_C + 0.45) * (1 - ramp(t, wt("end", "PLUTO'S"), wt("end", "PLUTO'S") + 0.4))
            if gc > 0.01:
                cx, cy = self.C
                hud_text(out, "TODAY'S MOON", cx, cy + BK["moon"]["Rp"] - 26, int(L.hud_size * 0.42), "Black", (150, 245, 255), gc, 0.10, display=True)
        self.caps.draw(out, t)


def run(stills=None):
    sc = Scene(True); tag = "vert"
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


def patch(ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render"""
    import subprocess
    sc = Scene(True); tag = "vert"
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
        for b in BODIES:
            print(f"{b['key']:5s} ratio={b['ratio']:.5f}  D={b['D']:8.1f} km  x{b['x']:.4f}  {b['ang']:.4f}deg  Rp={b['Rp']:7.2f}px  gain={b['gain']:.4f}"
                  f"  | {b['l1']} | {b['l2']} | {b['l3']} | {b['l4']}")
        print({k: round(v, 2) for k, v in T_SW.items()}, "ghostC", round(T_GHOST_C, 2), "double", round(T_DOUBLE, 2),
              "wo", round(T_WO0, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch([tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(st)
