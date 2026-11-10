"""WHAT IF PLANETS REPLACED OUR MOON? -- one locked tripod shot of the mountain valley (B_valley) at blue hour.
Our Moon is swapped, one after another, for planets placed at the Moon's distance (384,400 km), each drawn at its true
angular size theta = 2 asin(R/d) through a gnomonic lens with f = 1400 px (69 deg vertical FOV on the 1920 px frame;
the 16:9 cut keeps the same pixel scale). Every swap: the old body swells and implodes, a tinted flash + chromatic
shockwave, the new body blooms in, and the valley is relit by its light.
  Moon -> Mars -> Neptune -> Uranus -> Saturn -> Jupiter (rises over the mountains, + Galilean moons) -> white flash -> Moon
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
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from planets import Body, pole_vec, small_moon, SUN

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S11-planets-as-moon"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 1400.0
D_KM = 384400.0
R_MOON = 1737.4

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_px(R): return F_PX * math.tan(math.asin(R / D_KM))
def ang_deg(R): return 2 * math.degrees(math.asin(R / D_KM))


# ------------------------------------------------------------------------------------------------ the bodies
# R: equatorial radius (km). Visual: sky tint (zenith / horizon, linear, added to blue hour), glow colour, beam palette,
# valley light (tint, gain), star visibility, exposure, readout colour.
BODIES = [
    dict(key="moon", name="OUR MOON", R=1737.4, l2="1× MOON'S SIZE", l3="0.52° WIDE", tc=(235, 240, 255),
         zen=(0.0, 0.0, 0.0), hor=(0.0, 0.0, 0.0), glow=(0.55, 0.62, 0.80), gl=1.6,
         beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.28, corona=1.0,
         tint=(0.75, 0.85, 1.10), gain=0.05, stars=1.0, expo=1.0),
    dict(key="mars", name="MARS", R=3389.5, l2="2× MOON'S SIZE", l3="1.0° WIDE", tc=(255, 130, 80),
         zen=(0.010, 0.0, 0.0), hor=(0.06, 0.012, 0.0), glow=(1.0, 0.38, 0.16), gl=1.6,
         beams=[(1.0, 0.30, 0.08), (1.0, 0.55, 0.15), (0.9, 0.15, 0.25)], bI=0.45, corona=1.0,
         tint=(1.0, 0.55, 0.35), gain=0.06, stars=1.0, expo=1.0),
    dict(key="nep", name="NEPTUNE", R=24764.0, l2="14× MOON'S SIZE", l3="7.4° WIDE", tc=(110, 160, 255),
         zen=(0.0, 0.006, 0.05), hor=(0.0, 0.02, 0.08), glow=(0.25, 0.45, 1.0), gl=0.9,
         beams=[(0.20, 0.35, 1.0), (0.45, 0.30, 1.0), (0.20, 0.75, 1.0), (0.6, 0.5, 1.0)], bI=0.6, corona=0.0,
         tint=(0.40, 0.60, 1.30), gain=0.16, stars=0.85, expo=1.0),
    dict(key="ura", name="URANUS", R=25559.0, l2="15× MOON'S SIZE", l3="7.6° WIDE", tc=(140, 240, 240),
         zen=(0.0, 0.02, 0.03), hor=(0.0, 0.05, 0.05), glow=(0.40, 0.95, 1.0), gl=0.9,
         beams=[(0.30, 1.0, 0.95), (0.55, 0.95, 1.0), (0.30, 0.70, 1.0), (0.6, 1.0, 0.8)], bI=0.6, corona=0.0,
         tint=(0.55, 0.95, 1.15), gain=0.18, stars=0.85, expo=1.0),
    dict(key="sat", name="SATURN", R=60268.0, l2="35× MOON'S SIZE", l3="18° WIDE · RINGS 40°", tc=(255, 215, 140),
         zen=(0.008, 0.006, 0.0), hor=(0.09, 0.05, 0.012), glow=(1.0, 0.85, 0.55), gl=0.6,
         beams=[(1.0, 0.80, 0.40), (1.0, 0.60, 0.25), (1.0, 0.92, 0.65), (0.9, 0.5, 0.5)], bI=0.55, corona=0.0,
         tint=(1.10, 0.95, 0.70), gain=0.40, stars=0.55, expo=0.95),
    dict(key="jup", name="JUPITER", R=71492.0, l2="41× MOON'S SIZE", l3="21° WIDE", tc=(255, 190, 120),
         zen=(0.012, 0.010, 0.006), hor=(0.12, 0.06, 0.02), glow=(1.0, 0.78, 0.50), gl=0.6,
         beams=[(1.0, 0.70, 0.35), (1.0, 0.45, 0.20), (1.0, 0.88, 0.60), (0.95, 0.35, 0.30)], bI=0.6, corona=0.0,
         tint=(1.15, 0.92, 0.68), gain=0.80, stars=0.35, expo=0.92),
]
for b in BODIES: b["Rp"] = rad_px(b["R"])
BK = {b["key"]: b for b in BODIES}

# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["moon", "mars", "nep", "ura", "sat", "jup"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[2:]}
T_SW["mars"] = LN["mars"]["start"] - 0.06
T_BACK = LN["end"]["start"] - 0.10                   # white-out peak -> our Moon is back
T_WO0 = T_BACK - 0.75
T_TEAR = wt("tide", "TEAR"); T_VIEW = wt("tide", "VIEW")
T_JUP = T_SW["jup"]; T_RISEN = wt("jup", "VALLEY")
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_BACK, "moon2")]
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook", "PLANETS"), wt("moon", "SCALE"), wt("mars", "TWICE"), wt("nep", "14×"), wt("ura", "RINGS"), wt("sat", "40°"),
          wt("jup", "41×"), wt("jup", "VALLEY"), wt("jup", "MOONS"), wt("tide", "VIEW"), wt("end", "COSY")]


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


# Galilean moons: (name, offset along Jupiter's equator in units of Jupiter's apparent radius, perpendicular offset,
# radius km, distance from Earth km (approximate placement for these apparent separations), colour)
GALILEAN = [("Io", -1.30, 0.03, 1821.6, 790000, (1.0, 0.85, 0.45)), ("Europa", 1.45, -0.02, 1560.8, 820000, (0.95, 0.92, 0.88)),
            ("Ganymede", -1.80, -0.05, 2634.1, 1250000, (0.85, 0.80, 0.75)), ("Callisto", 1.95, 0.06, 2410.3, 2050000, (0.70, 0.65, 0.60))]


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.vertical = vertical
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.70)
        self.hz = float(fg.horizon)
        self.C = (540.0, 640.0) if vertical else (1310.0, 330.0)
        # Jupiter rises from behind the ridge (start -> end of its rise)
        self.J0 = (455.0, 1335.0) if vertical else (1225.0, 790.0)
        self.cam = SkyCam(W, H, self.hz, F_PX)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.el = np.degrees(np.arctan2(self.hz - yy, F_PX)).astype(f32)                     # elevation (deg), half res
        e = np.maximum(self.el, 0)
        xr = xx / W
        zen = np.array([0.010, 0.030, 0.115], f32)
        sky = zen * (0.62 + 0.38 * np.exp(-e / 28))[..., None]
        sky += np.array([0.05, 0.075, 0.16], f32) * np.exp(-e / 11)[..., None]
        belt = np.exp(-((e - 8.5) / 5.5) ** 2) * (0.55 + 0.45 * xr)                           # Belt of Venus (anti-twilight arch)
        sky += np.array([0.15, 0.065, 0.085], f32) * belt[..., None]
        shadow = np.exp(-e / 3.2)                                                            # Earth's shadow, a blue-grey band
        sky = sky * (1 - 0.30 * shadow)[..., None] + np.array([0.02, 0.035, 0.075], f32) * shadow[..., None]
        self.base_sky = sky.astype(f32)
        self.k_hor = np.exp(-e / 14)[..., None].astype(f32)
        # atmospheric extinction (full res): Kasten-Young airmass, Rayleigh + aerosol optical depths
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.hz - yyf, F_PX)), 0.25)
        X = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        tau = np.array([0.06, 0.09, 0.17], f32)
        self.ext = np.exp(-X[:, None] * tau[None, :])[:, None, :].astype(f32) * np.ones((1, W, 1), f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # bodies
        bp = BK
        self.body = {
            "moon": Body("moon", "8k_moon.jpg", bp["moon"]["Rp"], pole_vec(-12, 4), model="rock", surf=2.6, detail=0.0, spin=0.0),
            "mars": Body("mars", "8k_mars.jpg", bp["mars"]["Rp"], pole_vec(-15, 18), model="rock", surf=2.4, lon0=math.radians(-70),
                         rim=(0.4, 0.15, 0.06), detail=0.02, spin=0.05),
            "nep": Body("nep", "2k_neptune.jpg", bp["nep"]["Rp"], pole_vec(18, 22), surf=1.45, lon0=math.radians(10), spin=0.06,
                        haze=(0.03, 0.07, 0.22), rim=(0.10, 0.22, 0.75), detail=0.06, sat=1.15, seed=3),
            "ura": Body("ura", "2k_uranus.jpg", bp["ura"]["Rp"], [-0.62, -0.30, -0.72], surf=1.35, spin=0.05,
                        haze=(0.05, 0.13, 0.15), rim=(0.15, 0.40, 0.45), rings="uranus", detail=0.05, sat=1.1, seed=4),
            "sat": Body("sat", "8k_saturn.jpg", bp["sat"]["Rp"], pole_vec(-14, 24), q=0.902, spin=0.03, surf=1.35, sat=1.2, gamma=1.1,
                        haze=(0.05, 0.04, 0.02), rim=(0.25, 0.20, 0.10), rings="saturn", detail=0.04, seed=5),
            "jup": Body("jup", "8k_jupiter.jpg", bp["jup"]["Rp"], pole_vec(-8, 3), q=0.935, spin=0.035, lon0=math.radians(-47) + 0.45,
                        winds=0.025, surf=1.40, sat=1.35, gamma=1.15, haze=(0.06, 0.05, 0.035), rim=(0.30, 0.26, 0.18), detail=0.05, seed=6),
        }
        # foreground prep (as in other-suns: rim light on the skyline)
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        self.shim = fbm2((256, 256), 81, 2.0)
        yyf2, xxf2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf2, yyf2
        er = np.random.default_rng(9); n = 380
        self.emb = dict(x=er.uniform(0, W, n), y0=er.uniform(0, 1, n), sp=er.uniform(0.06, 0.20, n), ph=er.uniform(0, 6.28, n),
                        sz=er.uniform(0.3, 1.0, n) ** 2, wob=er.uniform(5, 30, n))
        emph = {"PLANETS", "MOON", "TWICE", "14×", "40°", "41×", "JUPITER", "VALLEY", "TEAR", "VIEW", "COSY", "SATURN", "MARS",
                "NEPTUNE", "URANUS", "RINGS"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010 if vertical else 600

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        cur, t0, t1 = body_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "moon" if i == 0 else ("moon" if SWAPS[i - 1][1] == "moon2" else SWAPS[i - 1][1])
        if cur == "mars" and t0 == T_SW["mars"]: prev = "moon"
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = BK[prev] if prev else BK[cur]; B = BK[cur]
        return A, B, w, cur, t0, t1

    def pos(self, cur, t):
        """centre of the current body; Jupiter rises (diagonally, ease-out) from behind the ridge"""
        if cur != "jup": return self.C
        u = ease((t - T_JUP) / (T_RISEN + 0.6 - T_JUP)) ** 0.8
        u2 = 1 - (1 - min(max((t - T_JUP) / (T_RISEN + 0.6 - T_JUP), 0), 1)) ** 2.2
        u = 0.5 * u + 0.5 * u2
        drift = max(t - (T_RISEN + 0.6), 0) * 6.0                                       # keeps creeping up afterwards
        return (self.J0[0] + (self.C[0] - self.J0[0]) * u + drift * 0.15, self.J0[1] + (self.C[1] - self.J0[1]) * u - drift)

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, cx, cy, col_u, bright):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32) * bright; hor = np.array(lerp(A["hor"], B["hor"], w), f32) * bright
        sky = self.base_sky + zen * (1 - self.k_hor) + hor * self.k_hor
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32); gl = lerp(A["gl"], B["gl"], w)
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - Rp, 0)
        aure = (np.exp(-dd / (40 + 0.25 * Rp)) * 0.35 + np.exp(-dd / (180 + 0.6 * Rp)) * 0.05) * gl * (0.6 + 0.4 * bright)
        sky = sky + aure[..., None] * gcol
        # iridescent corona around the small bright bodies (Moon, Mars)
        cor = lerp(A["corona"], B["corona"], w)
        if cor > 0.01:
            x = (d - Rp) / 34.0 - 0.15 * t
            ring = np.exp(-np.maximum(d - Rp, 0) / 85) * smooth(Rp + 6, Rp + 26, d)
            sky = sky + palette(x) * (ring * 0.05 * cor)[..., None]
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
    def relight(self, A, B, w, light, jfac):
        fg = self.fg
        amb_col = np.array([0.22, 0.32, 0.62], f32) * 0.11                       # blue-hour skylight
        night = fg.flat * 0.75 + fg.rgb * 0.25
        def one(S):
            g = S["gain"] * (jfac if S["key"] == "jup" else 1.0)
            key = (fg.rgb * 0.45 + fg.flat * 0.55) * np.array(S["tint"], f32) * g
            out = night * amb_col + key
            rc = np.array(S["glow"], f32)
            out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * rc * (0.04 + g * 0.6) * 0.35
            return out
        fb = one(B)
        fgc = fb if w >= 1 else one(A) * (1 - w) + fb * w
        return fgc * light

    def valley_mist(self, t, a, col):
        H = self.L.H; hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.30 + t * 10) % 512; mv = (sy * 1.1 + t * 3) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 30, hz + 25, sy) * (1 - smooth(hz + 90, hz + 260, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.4 - 0.3, 0, 1), (0, 0), 5)
        return self.up(m * band * a)[..., None] * np.array(col, f32)

    def dust(self, t, amt):
        W, H = self.L.W, self.L.H; e = self.emb
        y = H * (1.05 - ((e["y0"] + e["sp"] * t) % 1.0) * 0.75)
        x = e["x"] + e["wob"] * np.sin(t * 1.3 + e["ph"]) + 40 * np.sin(y / 300 + e["ph"])
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        tw = 0.6 + 0.4 * np.sin(t * 7 + e["ph"] * 3)
        np.add.at(lay, (yi, xi), e["sz"] * tw * amt)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.9) * 8 + cv2.GaussianBlur(lay, (0, 0), 4.0) * 4
        return self.up(lay)[..., None] * np.array([1.0, 0.55, 0.22], f32)

    def shimmer(self, img, amp, t, mask):
        if amp <= 0: return img
        u = (self.xx * 0.10 + t * 40) % 256; v = (self.yy * 0.10 + t * 25) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = mask * amp
        return cv2.remap(img, (self.xx + n * k).astype(f32), (self.yy + n * k * 0.7).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = BK[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.45 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        scale = g_in
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        if col_u > 0:                                                         # old body: swell, then implode to a point
            if col_u < 0.45: scale *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; scale *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        cx, cy = self.pos(cur, t)
        Rp = S["Rp"] * scale
        # how much of Jupiter is up (valley light grows as it rises)
        jfac = 1.0
        if cur == "jup": jfac = 0.45 + 0.55 * smooth(self.hz + 120, self.C[1], cy)
        bright = jfac * (1 + 0.5 * (pulse - 1))
        sky, bm, aure = self.sky(t, A, B, w, Rp, cx / 2 if False else cx, cy, col_u, bright)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        # stars (fade with the planet-shine)
        sg = lerp(A["stars"], B["stars"], w)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.12, star_gain=1.0, cx=2000, cy=900, rot=6.0)
        img += st * (sg * np.exp(-self.up(aure) * 6))[..., None] * 0.9
        # the body (atmospheric extinction near the horizon)
        bd = self.body[cur]
        bd.render(img, cx, cy, t, I=I_mul, scale=scale, ext=self.ext)
        if cur == "jup" and col_u < 0.9:                                        # Galilean moons along the equator
            Rj = S["Rp"]; ex, ey = math.cos(math.radians(-8)), math.sin(math.radians(-8))
            a_m = smooth(T_JUP + 0.3, T_JUP + 1.0, t) * (1 - col_u)
            for i, (nm, al, pe, Rk, dk, col) in enumerate(GALILEAN):
                al2 = al + 0.012 * (t - T_JUP) * (1 if i % 2 else -1)
                mx = cx + (al2 * ex - pe * ey) * Rj; my = cy + (al2 * ey + pe * ex) * Rj
                r = F_PX * Rk / dk
                small_moon(img, mx, my, r, np.array(col, f32) * 2.2, I=a_m * pulse, ext=self.ext)
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(A, B, w, light, jfac)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        lc = np.array(lerp(A["glow"], B["glow"], w), f32)
        fgc = fgc + self.valley_mist(t, 0.06 + 0.15 * lerp(A["gain"], B["gain"], w) * jfac, lc * 0.5) * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # tides: the ground trembles, dust rises, the sky flushes red ("Jupiter would tear Earth apart")
        tear = 0.0
        if cur == "jup":
            tear = ramp(t, T_TEAR - 0.3, T_TEAR + 0.4) * (1 - ramp(t, T_VIEW - 0.6, T_VIEW + 0.3))
            if tear > 0:
                img += self.dust(t, tear)
                img = img + (tear * 0.10 * (1 - a) * self.up(self.k_hor)[..., None] + tear * 0.06 * a) * np.array([1.0, 0.25, 0.08], f32)
                img = self.shimmer(img, 3.0 * tear, t, fg.a)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = BK["moon" if k == "moon2" else k]
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(NS["glow"])
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                pcx, pcy = self.pos("moon" if k == "moon2" else k, ts + 0.01)
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - pcx) ** 2 + (self.yy - pcy) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        # ---- final white-out (Jupiter -> our little Moon is back)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([0.95, 0.95, 1.0], f32)
        img = self.chroma_bloom(img, 1.0)
        expo = lerp(A["expo"], B["expo"], w)
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
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
        else: x, ys = 440, (810, 885, 940)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "moon" and t > T_BACK: a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "jup": a *= smooth(1060, 930, self.pos(cur, t)[1])
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(S["name"]) < 12 else 1.15))
            rgba, _ = word_layer(S["name"], big, W * 0.9 if L.vertical else 760, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.62), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (235, 240, 250), a, 0.10, display=True)
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
        print("DUR", DUR); [print(b["key"], round(b["Rp"], 2), "px", round(ang_deg(b["R"]), 2), "deg", round(b["R"] / R_MOON, 2), "x Moon") for b in BODIES]
        print({k: round(v, 2) for k, v in T_SW.items()}, "tear", round(T_TEAR, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
