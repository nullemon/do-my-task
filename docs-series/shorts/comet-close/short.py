"""WHAT IF COMETS PASSED AS CLOSE AS THE MOON? -- one locked tripod shot of the park (A2_park) at night, VFX "swap" format.
The Moon is swapped, one after another, for famous comets placed at the Moon's distance (384,400 km). Every head is
drawn through the plate's own lens (f = 1148 px, the ground-plane fit of ../betelgeuse-tonight): the nucleus is a
sub-pixel speck (shown in a magnifier), the coma has its true angular size (Halley: 100,000 km -> 14.8 deg), and the
tails, 10^7-10^8 km long, run off the frame (at lunar distance they would reach the anti-sun point: horizon to horizon).
Every swap: the old object swells and implodes, a tinted flash + chromatic shockwave + beams, the new comet blooms in
and its tails shoot out; the park is relit by the comet (soft shadows for Hale-Bopp and McNaught).
  Moon -> Halley -> Hale-Bopp -> NEOWISE -> 67P -> McNaught -> white-out -> Moon (loops)
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
from lib.core import f32, Layout, ramp, smooth, ease, noise1, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from comets import comet_field, nucleus_loupe

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-comet-close"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
# SOURCE px of A2_park.png (941x1672), as measured for ../betelgeuse-tonight: lamp heads + pole bases, lawn plane
LAMPS_SRC = [(193, 1198, 1325), (666, 1207, 1322), (816, 1113, 1323)]
LAWN_SRC = 1324
VAN_SRC = 1300
F_SRC = 1000.0
CAM_H = 1.3
FPS = 30
LEAD, TAIL = 0.25, 0.90
F_PX = F_SRC * (1080 / 941)                                                # 1147.7 px
HY = VAN_SRC * (1080 / 941) + (1920 - 1672 * (1080 / 941)) + 8           # true horizon row in the vertical frame
D_KM = 384400.0

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t1" if end else "t0"]


def px_of_km(km):
    """apparent radius (px) of something km across, at lunar distance, through the plate lens"""
    return F_PX * math.tan(math.atan(km / 2 / D_KM))
def deg_of_km(km): return 2 * math.degrees(math.atan(km / 2 / D_KM))


# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["moon", "halley", "hb", "neo", "duck", "mcn"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
T_BACK = LN["end"]["start"] - 0.10
T_WO0 = T_BACK - 0.80
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_BACK, "moon2")]
COLLAPSE, BLOOM = 0.42, 0.65
T_LOUPE_H = (wt("halley", "NUCLEUS") - 0.25, wt("halley", "BUT") + 0.1)
T_LOUPE_D = (T_SW["duck"] + 0.45, T_SW["mcn"] - 0.30)
OUTBURSTS = [wt("duck", "67P") + 0.55, wt("duck", "SPITTING"), wt("duck", "JETS") + 0.25]
PULSES = [wt("hook", "COMET"), wt("hook", "MOON"), wt("halley", "COMA"), wt("halley", "15°"), wt("halley", "SKY"), wt("hb", "GIANT"),
          wt("hb", "SHADOWS"), wt("neo", "GOLDEN"), wt("neo", "SODIUM"), wt("duck", "JETS"), wt("mcn", "BRIGHTEST"), wt("mcn", "STRIPED"),
          wt("mcn", "ENTIRE"), wt("end", "SNOWBALLS"), wt("end", "MILLIONS")]


def obj_at(t):
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("moon" if k == "moon2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def prev_of(t0):
    for i, (ts, k) in enumerate(SWAPS):
        if ts == t0: return "moon" if i == 0 else ("moon" if SWAPS[i - 1][1] == "moon2" else SWAPS[i - 1][1])
    return None


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w):
    if isinstance(a, (tuple, list)): return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


def palette(x):
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (np.asarray(x, f32)[..., None] - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (np.asarray(x) % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def alt_of(y): return math.degrees(math.atan((HY - y) / F_PX))


# ------------------------------------------------------------------------------------------------ the comets
# Rc: coma radius px from the true coma size at 384,400 km. theta: anti-sun direction on screen (deg, y down).
COMETS = {
    "halley": dict(head=(770.0, 700.0), theta=-124.0, Rc=px_of_km(100000), Ic=1.70, core=1.0,
                   Ii=1.25, iw=10.0, disc_T=5.5, disc_ph=1.0,
                   Id=0.95, side=1, bend=0.75, fan=(0.03, 0.40), r0=900, striae=0.25, nstr=4, skew=0.6, inner=0.3,
                   dcol=(1.0, 0.86, 0.60)),
    "hb": dict(head=(640.0, 760.0), theta=-102.0, Rc=px_of_km(300000), Ic=1.30, core=1.4, shells=0.70, hood=1.9,
               Ii=1.35, iw=18.0, disc_T=7.0, disc_ph=2.5,
               Id=1.55, side=1, bend=0.55, fan=(0.10, 0.75), r0=1100, striae=0.18, nstr=6, skew=0.5, inner=0.0,
               Ina=0.25, na_off=10, dcol=(1.0, 0.90, 0.70)),
    "neo": dict(head=(860.0, 1130.0), theta=-98.0, Rc=px_of_km(50000), Ic=0.85, core=1.2,
                Ii=0.75, iw=5.0, disc_T=6.5, disc_ph=0.5,
                Id=1.80, side=-1, bend=0.50, fan=(0.04, 0.30), r0=1300, striae=0.30, nstr=7, skew=1.2, inner=0.0,
                Ina=0.65, na_off=7, dcol=(1.0, 0.70, 0.34)),
    "duck": dict(head=(720.0, 700.0), theta=-84.0, Rc=px_of_km(20000), Ic=1.1, core=0.8,
                 Ii=0.35, iw=3.0, disc_T=9.0, disc_ph=3.0,
                 Id=0.45, side=1, bend=0.12, fan=(0.00, 0.22), r0=600, striae=0.0, nstr=0, dcol=(1.0, 0.88, 0.66)),
    "mcn": dict(head=(905.0, 1285.0), theta=-112.0, Rc=px_of_km(80000), Ic=1.4, core=1.6,
                Ii=0.45, iw=7.0, disc_T=8.0, disc_ph=1.5,
                Id=1.6, side=1, bend=0.10, fan=(-0.10, 1.30), r0=2600, striae=0.55, nstr=13, skew=2.6, inner=0.4,
                dcol=(1.0, 0.72, 0.40)),
}
MOON = dict(head=(720.0, 640.0), Rp=F_PX * math.tan(math.radians(0.518 / 2)))

# per object: sky tint (zen / hor additive), glow, beams palette + strength, park light (E, colour, shadows), exposure
LOOK = {
    "moon": dict(zen=(0.0, 0.0, 0.0), hor=(0.0, 0.0, 0.0), E=0.10, lcol=(0.70, 0.82, 1.10), sh=0.0, bI=0.10, expo=1.0, stars=1.0,
                 beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], glow=(0.55, 0.62, 0.80)),
    "halley": dict(zen=(0.0, 0.012, 0.012), hor=(0.0, 0.020, 0.025), E=0.22, lcol=(0.45, 1.0, 0.75), sh=0.0, bI=0.45, expo=1.0, stars=0.9,
                   beams=[(0.25, 1.0, 0.55), (0.25, 0.55, 1.0), (0.55, 1.0, 0.95), (1.0, 0.85, 0.55)], glow=(0.3, 1.0, 0.55)),
    "hb": dict(zen=(0.006, 0.030, 0.050), hor=(0.010, 0.045, 0.060), E=0.95, lcol=(0.55, 1.0, 0.80), sh=0.85, bI=0.75, expo=0.95, stars=0.55,
               beams=[(0.25, 1.0, 0.55), (0.20, 0.50, 1.0), (0.95, 0.95, 0.75), (0.40, 0.95, 1.0)], glow=(0.35, 1.0, 0.6)),
    "neo": dict(zen=(0.020, 0.012, 0.004), hor=(0.060, 0.034, 0.010), E=0.50, lcol=(1.0, 0.80, 0.45), sh=0.5, bI=0.6, expo=1.0, stars=0.75,
                beams=[(1.0, 0.72, 0.30), (1.0, 0.55, 0.15), (0.35, 0.60, 1.0), (1.0, 0.90, 0.55)], glow=(1.0, 0.75, 0.40)),
    "duck": dict(zen=(0.0, 0.004, 0.004), hor=(0.0, 0.008, 0.008), E=0.08, lcol=(0.55, 1.0, 0.8), sh=0.0, bI=0.35, expo=1.0, stars=1.0,
                 beams=[(0.30, 1.0, 0.60), (0.85, 1.0, 1.0), (0.35, 0.70, 1.0)], glow=(0.4, 1.0, 0.65)),
    "mcn": dict(zen=(0.050, 0.040, 0.026), hor=(0.110, 0.080, 0.040), E=1.6, lcol=(1.0, 0.86, 0.62), sh=0.9, bI=0.8, expo=0.85, stars=0.30,
                beams=[(1.0, 0.85, 0.50), (1.0, 0.65, 0.30), (0.95, 0.95, 0.80), (0.50, 1.0, 0.70)], glow=(1.0, 0.85, 0.55)),
}

INFO = {
    "moon": dict(name="OUR MOON", l2="384,400 KM AWAY", l3="0.52° WIDE", l4="", tc=(225, 235, 255)),
    "halley": dict(name="HALLEY'S COMET", l2="NUCLEUS 15 × 8 KM · 0.002°", l3="ION TAIL 100+ MILLION KM", l4="COMA 100,000 KM = 15° WIDE", tc=(130, 255, 170)),
    "hb": dict(name="HALE-BOPP", l2="NUCLEUS ~60 KM", l3="TAILS 100+ MILLION KM", l4="~4× BRIGHTER THAN THE FULL MOON", tc=(150, 240, 255)),
    "neo": dict(name="NEOWISE", l2="NUCLEUS ~5 KM", l3="TAILS TENS OF MILLIONS OF KM", l4="BLUE ION · GOLDEN DUST · SODIUM TAIL", tc=(255, 205, 110)),
    "duck": dict(name="67P/CHURYUMOV–GERASIMENKO", l2="NUCLEUS 4.3 × 4.1 KM", l3="JETS · OUTBURSTS", l4="THE RUBBER-DUCK COMET", tc=(150, 255, 200)),
    "mcn": dict(name="McNAUGHT", l2="NUCLEUS ~3 KM", l3="ION TAIL 260+ MILLION KM", l4="BRIGHTEST COMET IN 40 YEARS", tc=(255, 215, 130)),
}


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H; self.W, self.H = W, H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[(lx, ly, by) for lx, ly, by in LAMPS_SRC], hz_frac=0.84)
        self.hz = HY
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.clip((HY - yy) / HY, 0, 1); self.e = e
        self.k_hor = np.exp(-e / 0.30)[..., None].astype(f32)
        # deep-blue night sky (never black): zenith -> horizon, faint airglow band, a little light-dome on the horizon
        zen = np.array([0.010, 0.022, 0.085], f32); hor = np.array([0.030, 0.050, 0.140], f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        sky += np.array([0.012, 0.020, 0.010], f32) * np.exp(-((e - 0.12) / 0.07) ** 2)[..., None]
        sky += np.array([0.040, 0.030, 0.040], f32) * np.exp(-e / 0.05)[..., None]
        sky *= (1 + 0.10 * fbm2((hh, hw), 21, 3.0))[..., None]
        self.base_sky = sky.astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        # stars (half res) + a faint Milky Way band
        n = 1500; sr = np.random.default_rng(12)
        self.ns = dict(x=sr.uniform(0, hw, n), y=sr.uniform(0, hh * 0.80, n), m=sr.uniform(0, 1, n) ** 3.2, ph=sr.uniform(0, 6.28, n),
                       c=np.stack([bbcolor(T) for T in sr.uniform(3500, 12000, n)]))
        mw = np.exp(-(((xx - 200) * 0.8 + (yy - 600) * 0.6) / 150) ** 2) * np.clip(0.6 + 0.5 * fbm2((hh, hw), 33, 2.2), 0, 2)
        self.mw = (mw * (1 - self.k_hor[..., 0]))[..., None] * np.array([0.020, 0.022, 0.035], f32)
        # foreground prep
        a = fg.a
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a).astype(f32)
        self.alb = np.clip(fg.flat, 0, 1).astype(f32)
        self._shadow_src()
        self.shcache = {}
        rs = np.random.default_rng(31); ls = np.zeros((440, 440, 3), f32)
        for _ in range(140):
            x_, y_ = rs.integers(0, 440, 2); ls[y_, x_] += bbcolor(float(rs.uniform(3500, 15000))) * float(rs.uniform(0.2, 1.0) ** 3) * 2.0
        self.loupe_stars = cv2.GaussianBlur(ls, (0, 0), 0.6)
        self.cache = {}
        self.caps = Captions(L, WORDS, emphasis={"COMET", "MOON", "HALLEY'S", "POTATO", "15", "GREEN", "COMA", "15°", "SKY", "HALE-BOPP",
                                                 "GIANT", "60", "SHADOWS", "NEOWISE", "GOLDEN", "SODIUM", "67P", "RUBBER-DUCK", "JETS",
                                                 "MCNAUGHT", "BRIGHTEST", "STRIPED", "ENTIRE", "SNOWBALLS", "MILLIONS"})
        L.cap_y = 960; L.cap_maxw = 760

    def up(self, a): return cv2.resize(a, (self.W, self.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- shadows (from ../second-sun)
    def _shadow_src(self):
        im = np.asarray(Image.open(FG_PATH).convert("RGBA"), f32) / 255.0
        a = im[..., 3]; self.sh_, self.sw_ = a.shape
        yy, xx = np.mgrid[0:self.sh_, 0:self.sw_].astype(f32)
        self.lawn_src = (a > 0.5) & (yy > LAWN_SRC) & ~((xx < 52) & (yy < 1392))
        self.syy = yy
        fg = self.fg; self.M = np.array([[fg.s, 0, 0], [0, fg.s, fg.oy]], np.float64)
        self.lawn = self.warp(cv2.GaussianBlur(self.lawn_src.astype(f32), (0, 0), 0.7))
        cols = []
        for xs_ in range(2, self.sw_ - 1, 2):
            if 395 <= xs_ <= 545 or xs_ < 140: continue
            y = LAWN_SRC - 3
            if a[y, xs_] < 0.5: continue
            while y > LAWN_SRC - 170 and a[y - 1, xs_] > 0.5: y -= 1
            if LAWN_SRC - y > 6: cols.append((xs_, float(y)))
        self.tl_cols = cols

    def warp(self, m):
        return cv2.warpAffine(m, self.M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(f32)

    def shadow(self, x_frame, el):
        key = (int(round(x_frame / 6)), int(round(el * 2)))
        if key in self.shcache: return self.shcache[key]
        xs = key[0] * 6 / self.fg.s; el = key[1] / 2
        sh_, sw_ = self.sh_, self.sw_; cxs = sw_ / 2
        az = math.atan((xs - cxs) / F_SRC)
        kk = 1 / math.tan(math.radians(el)); kl = kk
        sa, ca = math.sin(az), math.cos(az)
        Q = 4; P = np.zeros((sh_ * Q, sw_ * Q), np.uint8)
        def scr(X, Z): return cxs + F_SRC * X / Z, VAN_SRC + F_SRC * CAM_H / Z
        def cast(xb, yb, ztop_px, prof, n=300, kk=kk):
            Zb = F_SRC * CAM_H / (yb - VAN_SRC); Xb = (xb - cxs) * Zb / F_SRC; Hh = (yb - ztop_px) * Zb / F_SRC
            Lp, Rp = [], []
            for u in np.linspace(0, 1, n):
                X = Xb - Hh * u * kk * sa; Z = Zb - Hh * u * kk * ca
                if Z < 0.4: break
                w = prof(u)
                xl, yl = scr(X - w * ca, Z + w * sa); xr, yr = scr(X + w * ca, Z - w * sa)
                Lp.append((xl * Q, yl * Q)); Rp.append((xr * Q, yr * Q))
            if len(Lp) > 1:
                poly = np.clip(np.array(Lp + Rp[::-1], np.float64), -1e5, 1e5).astype(np.int32)
                cv2.fillPoly(P, [poly], 255, cv2.LINE_AA)
        rng = np.random.default_rng(4); jit = rng.uniform(0.85, 1.15, 64)
        def conifer(u):
            if u < 0.06: return 0.35
            v = (u - 0.06) / 0.94; tier = (v * 9) % 1.0
            return 4.2 * (1 - v) ** 1.1 * (0.72 + 0.28 * tier) * jit[int(v * 63)] + 0.05
        cast(470, 1318, 950, conifer, 500)
        for lx, ly, by in LAMPS_SRC:
            cast(lx, by, ly, lambda u: 0.42, 600, kl)
        cast(22, 1384, 1050, lambda u: 0.55, 200)
        for xs_, top in self.tl_cols:
            cast(xs_, LAWN_SRC, top, lambda u: 0.11, 40)
        Ms = cv2.resize(P.astype(f32) / 255, (sw_, sh_), interpolation=cv2.INTER_AREA)
        Mb = cv2.GaussianBlur(Ms, (0, 0), 5.0)                                     # extended source -> softer edges
        w = 0.8 * np.clip((self.syy - LAWN_SRC) / 250.0, 0, 1) ** 0.8
        S = (Ms * (1 - w) + Mb * w) * self.lawn_src
        out = self.warp(S)
        if len(self.shcache) > 20: self.shcache.pop(next(iter(self.shcache)))
        self.shcache[key] = out
        return out

    # -------------------------------------------------------------------------------------------- sky pieces
    def beams_layer(self, t, Lk, w_b, cx, cy, col_u, bI):
        dx = self.hx - cx; dy = self.hy - cy; d = np.sqrt(dx * dx + dy * dy) + 1e-3
        phi0 = np.arctan2(dy, dx)
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = phi0 + twist * np.log(d / 30.0)
        reach = 1100 * (1 - 0.7 * ease(col_u))
        rad = (1 - np.exp(-(d + 6) / 35)) * (np.exp(-d / reach) * 0.9 + 0.12 * np.exp(-d / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.25) % 1.0
            acc += pal_list(Lk["beams"], x) * (g * I)[..., None]
        return acc * rad[..., None] * 0.30 * bI

    def night_stars(self, t, amt):
        s = self.ns; lay = np.zeros(self.hx.shape + (3,), f32)
        xi = s["x"].astype(int); yi = s["y"].astype(int)
        tw = 0.75 + 0.25 * np.sin(t * 5 + s["ph"])
        np.add.at(lay, (yi, xi), (s["c"] * (s["m"] * tw * amt * 1.2)[:, None]).astype(f32))
        return cv2.GaussianBlur(lay, (0, 0), 0.6) * 3 + self.mw * amt

    def moon(self, img, t, I=1.0, scale=1.0):
        cx, cy = MOON["head"]; Rp = MOON["Rp"] * scale
        H, W = img.shape[:2]; pad = 260
        x0, x1, y0, y1 = int(cx - pad), int(cx + pad), int(cy - pad), int(cy + pad)
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        inside = smooth(Rp + 0.8, Rp - 0.8, d)
        mare = 0.80 + 0.20 * np.sin(dx * 0.9 + 1) * np.cos(dy * 1.1 - 0.5)
        reg = img[y0:y1, x0:x1]
        reg += (inside * mare * 9.0 * I)[..., None] * np.array([1.0, 0.97, 0.92], f32)
        dd = np.maximum(d - Rp, 0)
        g = np.exp(-dd / 4) * 1.2 + np.exp(-dd / 25) * 0.28 + np.exp(-dd / 120) * 0.06
        reg += (g * I)[..., None] * np.array([0.80, 0.85, 1.0], f32)
        x = (d - Rp) / 30.0 - 0.15 * t                                              # faint iridescent corona
        ring = np.exp(-np.maximum(d - Rp, 0) / 80) * smooth(Rp + 6, Rp + 24, d)
        reg += palette(x) * (ring * 0.05 * I)[..., None]

    def comet_sky(self, key, t, sc, grow, I):
        """half-res comet field (cached per frame time)"""
        return comet_field(COMETS[key], self.hx, self.hy, t, sc, grow, I)

    # -------------------------------------------------------------------------------------------- loupe
    def loupe(self, img, t, kind, alpha, head, outb):
        if alpha <= 0.01: return
        cx, cy, R0 = 800.0, 1255.0, 175.0
        R = R0 * (0.55 + 0.45 * back_out(alpha, 1.6))
        H, W = img.shape[:2]
        r = int(R) + 8; x0, y0 = int(cx) - r, int(cy) - r
        g = np.arange(2 * r) + 0.5 - r
        XX, YY = np.meshgrid(g, g); rr = np.hypot(XX, YY)
        inside = smooth(R + 0.8, R - 0.8, rr)[..., None]
        C = COMETS[kind]; th = math.radians(C["theta"])
        sun = (-math.cos(th), -math.sin(th))
        base = np.array([0.004, 0.010, 0.020], f32) + self.loupe_stars[:2 * r, :2 * r] * 0.6
        patch = base + nucleus_loupe("halley" if kind == "halley" else "duck", r, R, t, sun, jets=1.0, outburst=outb)
        ring = np.exp(-((rr - R) / 2.4) ** 2)[..., None] * np.array([1.4, 1.7, 1.45], f32) + \
            (np.exp(-np.maximum(rr - R, 0) / 14) * (rr > R) * 0.22)[..., None] * np.array([0.7, 1.0, 0.85], f32)
        reg = img[y0:y0 + 2 * r, x0:x0 + 2 * r]
        reg[:] = reg * (1 - inside * alpha) + patch * inside * alpha + ring * alpha
        sx, sy = head; dx, dy = cx - sx, cy - sy; D = math.hypot(dx, dy)
        if D > R + 5:
            m = np.zeros((H, W), f32); base_a = math.atan2(dy, dx); off = math.asin(R / D)
            for sgn in (-1, 1):
                a = base_a + sgn * off; Lt = math.sqrt(D * D - R * R)
                ex, ey = sx + Lt * math.cos(a), sy + Lt * math.sin(a)
                bx, by = sx + 16 * math.cos(a), sy + 16 * math.sin(a)
                cv2.line(m, (int(bx * 4), int(by * 4)), (int(ex * 4), int(ey * 4)), 1.0, 2, cv2.LINE_AA, shift=2)
            cv2.circle(m, (int(sx * 4), int(sy * 4)), int(16 * 4), 1.0, 2, cv2.LINE_AA, shift=2)
            m = cv2.GaussianBlur(m, (0, 0), 0.8)
            img += (m * alpha * 1.0)[..., None] * np.array([0.85, 1.0, 0.9], f32)
        self.loupe_lab = (cx, cy + R + 34, "NUCLEUS · 15 KM" if kind == "halley" else "NUCLEUS · 4 KM", alpha)

    # -------------------------------------------------------------------------------------------- park
    def relight(self, t, Lk, w_l, head, amb_col, I_l):
        """Lk: list of (look, weight). Comet light from the head (soft shadows), plus the sky ambient + lamps."""
        fg = self.fg; lawn = self.lawn[..., None]
        direct_l = np.zeros((self.H, self.W, 3), f32); direct_o = np.zeros(3, f32); rimc = np.zeros(3, f32)
        for (Lw, wgt), hd in zip(Lk, head):
            E = Lw["E"] * wgt * I_l
            if E < 1e-3: continue
            c = np.array(Lw["lcol"], f32) * E
            if Lw["sh"] > 0 and hd[1] < HY - 20:
                S = self.shadow(hd[0], max(alt_of(hd[1]), 6.0))
                direct_l += c * (1 - 0.9 * Lw["sh"] * S)[..., None]
            else:
                direct_l += c
            direct_o += c * 0.5; rimc += c
        out = self.alb * (amb_col * 0.75 + direct_l * lawn + direct_o * (1 - lawn))
        out = out + self.rim[..., None] * (rimc * 0.45 + amb_col * 0.6)
        out = fg.lamps_light(out, 0.9, t)
        return np.maximum(out, 0)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        W, H = self.W, self.H; fg = self.fg; self.loupe_lab = None
        cur, t0, t1 = obj_at(t)
        prev = prev_of(t0)
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = LOOK[prev] if prev else LOOK[cur]; B = LOOK[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        scale = g_in; I_mul = pulse * ((0.4 + 0.6 * min(max(u_in * 3, 0), 1)) if t0 > 0 else 1.0)
        if col_u > 0:
            if col_u < 0.45: scale *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; scale *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 2 * col_u ** 2
        grow = 1.0 if cur == "moon" else ramp(t, t0 + 0.05, t0 + 1.6)
        if col_u > 0.45: grow *= 1 - ease((col_u - 0.45) / 0.55)
        head = MOON["head"] if cur == "moon" else COMETS[cur]["head"]
        # ---- sky
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        bright = 1 + 0.4 * (pulse - 1)
        sky = self.base_sky + (zen * (1 - self.k_hor) + hor * self.k_hor) * bright
        stars = lerp(A["stars"], B["stars"], w)
        sky = sky + self.night_stars(t, stars)
        bfade = (min(max(u_in * 2, 0), 1) * (0.35 + 0.65 * math.exp(-max(t - t0, 0) / 1.4))) if t0 > 0 else 1.0
        bm = self.beams_layer(t, B, 1.0, head[0], head[1], col_u, B["bI"] * bfade)
        if cur != "moon":
            cf = self.comet_sky(cur, t, max(scale, 0.02), grow, I_mul)
            if cur == "duck":                                                       # outbursts: expanding shells of fresh dust
                for tb in OUTBURSTS:
                    u = t - tb
                    if 0 < u < 2.5:
                        hx, hy = head; dd = np.sqrt((self.hx - hx) ** 2 + (self.hy - hy) ** 2)
                        Rb = 12 + 120 * u ** 0.7
                        th = math.radians(COMETS["duck"]["theta"])                  # brighter on the sunward side
                        cs = -((self.hx - hx) * math.cos(th) + (self.hy - hy) * math.sin(th)) / (dd + 1e-3)
                        shl = np.exp(-((dd - Rb * 0.7) / (10 + 30 * u)) ** 2) * math.exp(-u / 0.8) * 0.9 * (0.35 + 0.65 * np.clip(cs, 0, 1) ** 1.5) \
                            + np.exp(-dd / (8 + 20 * u)) * math.exp(-u / 0.4) * 2.0
                        cf = cf + shl[..., None] * np.array([0.85, 1.0, 0.80], f32)
            sky = sky + cf
        # ambient light for the park, from the sky the park actually sees (upper sky + horizon)
        amb_col = sky[: sky.shape[0] // 2].reshape(-1, 3).mean(0) * 0.6 + sky[int(sky.shape[0] * 0.70)].mean(0) * 0.4
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        if cur == "moon": self.moon(img, t, I_mul * (1.0 if t0 < 0 else min(1.0, 0.3 + u_in)), max(scale, 0.05))
        # ---- park
        light = 1.0 + 0.12 * (pulse - 1) - 0.25 * col_u
        heads = [MOON["head"] if prev in (None, "moon") else COMETS[prev]["head"], head]
        I_l = (0.3 + 0.7 * grow) if cur != "moon" else 1.0
        fgc = self.relight(t, [(A, 1 - w if prev else 0.0), (B, w)], 1.0, heads, amb_col * 2.2, I_l) * light
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- nucleus loupes (Halley, 67P)
        if cur == "halley":
            la = ramp(t, T_LOUPE_H[0], T_LOUPE_H[0] + 0.35) * (1 - ramp(t, T_LOUPE_H[1] - 0.3, T_LOUPE_H[1]))
            self.loupe(img, t, "halley", la, head, 0.0)
        if cur == "duck":
            la = ramp(t, T_LOUPE_D[0], T_LOUPE_D[0] + 0.35) * (1 - ramp(t, T_LOUPE_D[1] - 0.3, T_LOUPE_D[1]))
            ob = 0.0
            for tb in OUTBURSTS:
                if 0 < t - tb < 1.6: ob = (t - tb) / 1.6
            self.loupe(img, t, "duck", la, head, ob)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                ks = "moon" if k == "moon2" else k
                fc = 0.4 + 0.6 * np.array(LOOK[ks]["glow"], f32) / max(LOOK[ks]["glow"])
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                pcx, pcy = MOON["head"] if ks == "moon" else COMETS[ks]["head"]
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - pcx) ** 2 + (self.yy - pcy) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([0.95, 1.0, 0.97], f32)
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
        W, H = self.W, self.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W
        I = INFO[cur]
        x, ys = W / 2, (270, 352, 404, 452)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "moon" and t > T_BACK: a = ramp(t, T_BACK + 0.9, T_BACK + 1.2) * (1 - ramp(t, DUR - 0.6, DUR - 0.2))
        if cur == "moon" and t < 1.0: a = ramp(t, 0.35, 0.7)
        if T_WO0 < t < T_BACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            n = I["name"]
            big = int(L.hud_size * (1.45 if len(n) < 12 else (1.15 if len(n) < 18 else 0.80)))
            rgba, _ = word_layer(n, big, W * 0.94, fill=I["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, I["l2"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.06, display=True)
            hud_text(out, I["l3"], x, ys[2] + dy, int(L.hud_size * 0.50), "Black", (235, 242, 255), a, 0.06, display=True)
            if I["l4"]:
                hud_text(out, I["l4"], x, ys[3] + dy, int(L.hud_size * 0.46), "Bold", tuple(min(255, int(c * 0.6 + 110)) for c in I["tc"]), a, 0.08, display=True)
        if self.loupe_lab and self.loupe_lab[3] > 0.05:
            lx, ly, lt, la = self.loupe_lab
            hud_text(out, lt, lx, ly, 34, "Black", (200, 255, 215), la, 0.08, display=True)
        self.caps.draw(out, t)


def save(im, p):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(stills=None):
    sc = Scene(); tag = "vert"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            save(im, os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.W, sc.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(ranges):
    import subprocess
    sc = Scene(); tag = "vert"
    W, H = sc.W, sc.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
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
        print("DUR", DUR, "HY", round(HY, 1), "F_PX", round(F_PX, 1), "moon r px", round(MOON["Rp"], 2))
        print({k: round(v, 2) for k, v in T_SW.items()}, "back", round(T_BACK, 2), "loupes", T_LOUPE_H, T_LOUPE_D)
        for k, km in (("halley coma", 100000), ("hb coma", 300000), ("neo coma", 50000), ("67P coma", 20000), ("mcn coma", 80000),
                      ("halley nucleus", 15.3), ("hb nucleus", 60), ("67P nucleus", 4.3), ("mcn nucleus", 3.2)):
            print(f"{k:16s} {km:>9} km -> {deg_of_km(km):.4f} deg, r = {px_of_km(km):.3f} px")
        sys.exit()
    if sys.argv[1] == "patch":
        patch([tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(st)
