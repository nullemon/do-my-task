"""WHAT IF OTHER STARS REPLACED OUR SUN? -- one locked tripod shot of the park (A_park), VFX spectacle style.
Our Sun is swapped, one after another, for other stars placed at 1 au, each drawn at its true angular size through a
~90 deg vertical-FOV lens (f = 960 px), with the park relit and graded by that star's light.
  Sun -> Proxima Centauri -> Sirius A -> Arcturus -> Rigel -> Betelgeuse (swells until we are inside it) -> white-out -> Sun (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5           stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S4-other-suns"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A_park.png"
LAMPS = [(630, 1185, 1336), (845, 1095, 1342)]       # lamp (head x, head y, pole base y) in SOURCE px
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 960.0                                          # 90 deg vertical FOV on 1920 px (same px scale in 16:9)
RSUN_AU = 0.00465047                                  # R_sun / 1 au

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_px(R):
    """apparent radius in px of a star of radius R (solar radii) at 1 au: full geometry, gnomonic lens"""
    x = R * RSUN_AU
    if x >= 0.999: return 1e5
    return F_PX * math.tan(math.asin(x))


def ang_deg(R): return 2 * math.degrees(math.asin(min(R * RSUN_AU, 1.0)))


ARC_RAMP = [(0.0, (0.30, 0.05, 0.01)), (0.35, (1.1, 0.30, 0.04)), (0.7, (2.4, 1.05, 0.20)), (1.0, (3.6, 2.0, 0.6)), (1.4, (5.0, 3.6, 1.8))]
BET_RAMP = [(0.0, (0.25, 0.02, 0.005)), (0.35, (1.2, 0.18, 0.02)), (0.7, (2.5, 0.70, 0.10)), (1.0, (3.6, 1.45, 0.35)), (1.4, (5.0, 3.0, 1.4))]
def ramp_col(rmp, v):
    xs = np.array([p[0] for p in rmp], f32); cs = np.array([p[1] for p in rmp], f32)
    return np.stack([np.interp(v, xs, cs[:, c]) for c in range(3)], -1).astype(f32)


# ------------------------------------------------------------------------------------------------ the stars
# R: radius [R_sun], T: effective temperature [K] (sources in README). Visual params: sky zenith/horizon (linear),
# beam colours, surface brightness, foreground grade (gain, tint, flat fraction, ambient), exposure.
STARS = [
    dict(key="sun", name="THE SUN", R=1.0, T=5772, l2="1× SUN'S SIZE", l3="5,800 K · 0.53° WIDE", tc=(255, 236, 170),
         zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), beams="rainbow", bI=1.0, surf=40.0, gain=1.0, tint=(1.0, 0.98, 0.95),
         flat=0.0, amb=0.10, expo=1.0, cells=0, fine=0, u=0.6, glow=1.0, spikes=0.6, sat=1.0, con=1.0, hc=0.0),
    dict(key="prox", name="PROXIMA CENTAURI", R=0.1542, T=3042, l2="0.15× SUN'S SIZE", l3="3,000 K · 0.08° WIDE", tc=(255, 120, 90),
         zen=(0.045, 0.010, 0.085), hor=(0.42, 0.075, 0.055), beams=[(1.0, 0.10, 0.05), (0.9, 0.05, 0.45), (1.0, 0.35, 0.05)], bI=0.45,
         surf=3.0, gain=0.10, tint=(1.0, 0.30, 0.13), flat=0.55, amb=0.05, expo=1.25, cells=0, fine=0, u=0.8, glow=0.9, spikes=0.12, sat=1.4, con=1.0, hc=0.0),
    dict(key="sir", name="SIRIUS A", R=1.711, T=9940, l2="1.7× SUN'S SIZE", l3="9,900 K · 0.9° WIDE", tc=(175, 215, 255),
         zen=(0.07, 0.24, 1.30), hor=(0.85, 1.00, 1.45), beams=[(0.3, 0.7, 1.0), (0.75, 0.4, 1.0), (0.85, 0.95, 1.0), (0.2, 1.0, 0.95)], bI=1.35,
         surf=70.0, gain=1.9, tint=(0.70, 0.88, 1.35), flat=0.0, amb=0.15, expo=0.95, cells=0, fine=0, u=0.45, glow=2.2, spikes=1.3, sat=1.0, con=1.0, hc=0.25),
    dict(key="arc", name="ARCTURUS", R=25.4, T=4286, l2="25× SUN'S SIZE", l3="4,300 K · 13.6° WIDE", tc=(255, 175, 80),
         zen=(0.26, 0.085, 0.035), hor=(1.0, 0.50, 0.15), beams=[(1.0, 0.55, 0.08), (1.0, 0.85, 0.30), (1.0, 0.25, 0.30), (1.0, 0.40, 0.05)], bI=1.0,
         ramp=ARC_RAMP, surf=0.9, gain=1.25, tint=(1.0, 0.52, 0.18), flat=0.15, amb=0.20, expo=1.0, cells=46, fine=1400, u=0.75, glow=1.0, spikes=0.5, sat=1.6, con=1.0, hc=0.0),
    dict(key="rig", name="RIGEL", R=78.9, T=12100, l2="79× SUN'S SIZE", l3="12,100 K · 43° WIDE", tc=(160, 205, 255),
         zen=(0.04, 0.22, 1.50), hor=(0.55, 0.85, 1.70), beams=[(0.4, 0.75, 1.0), (0.6, 0.45, 1.0), (0.9, 0.97, 1.0), (0.25, 0.95, 1.0)], bI=1.6,
         surf=3.2, gain=2.2, tint=(0.62, 0.85, 1.45), flat=0.25, amb=0.30, expo=0.9, cells=70, fine=2600, u=0.40, glow=1.6, spikes=0.6, sat=1.5, con=0.55, hc=0.2),
    dict(key="bet", name="BETELGEUSE", R=764.0, T=3600, l2="~700–1,000× SUN'S SIZE", l3="3,600 K · WE'RE INSIDE IT", tc=(255, 125, 60),
         zen=(0.40, 0.07, 0.02), hor=(1.2, 0.35, 0.06), beams=[(1.0, 0.30, 0.04), (1.0, 0.60, 0.10), (0.9, 0.10, 0.10)], bI=0.8,
         ramp=BET_RAMP, surf=0.85, gain=0.85, tint=(1.0, 0.36, 0.09), flat=0.45, amb=0.45, expo=1.0, cells=16, fine=900, u=0.85, glow=1.0, spikes=0.0, sat=1.7, con=1.0, hc=0.0),
]
for s in STARS: s["Rp"] = rad_px(s["R"])
SK = {s["key"]: s for s in STARS}

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {k: LN[k]["start"] - 0.06 for k in ("prox", "sir", "arc", "rig", "bet")}     # swap moments (new star blooms in)
COLLAPSE, BLOOM = 0.42, 0.65
T_FREEZE = wt("prox", "FREEZES") - 0.4
T_BOIL = wt("sir", "OCEANS")
T_VAPOR = wt("rig", "EARTH", 0) + 0.1
T_BET0 = T_SW["bet"]
T_INSIDE = wt("bet", "WE'D") - 0.15                 # disc has swallowed the whole sky
T_SUNBACK = LN["end"]["start"] - 0.10               # white-out peak -> our Sun is back
T_WO0 = T_SUNBACK - 0.85
ORDER = ["sun", "prox", "sir", "arc", "rig", "bet"]
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "sun2")]
PULSES = [wt("hook", "REPLACED"), wt("prox", "15%"), wt("sir", "25×"), wt("arc", "25×"), wt("arc", "13°"), wt("rig", "79×"),
          wt("rig", "VAPORIZED"), wt("bet", "700×"), wt("bet", "MARS"), wt("end", "SUN")]


def star_at(t):
    """-> (current key, swap time of current star, next swap time)"""
    cur, t0 = "sun", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("sun" if k == "sun2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


# ------------------------------------------------------------------------------------------------ helpers
_T = np.linspace(1500, 20000, 512)
BB_LUT = np.stack([bbcolor(x) for x in _T]).astype(f32)
def bb_vec(T):
    i = np.clip((T - 1500) / (20000 - 1500) * 511, 0, 511).astype(np.int32); return BB_LUT[i]


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    """cyclic interpolation through a list of colours, x in [0,1)"""
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


class Cells:
    """animated Worley cells on the unit sphere (convection cells / granulation)"""
    def __init__(self, n, seed):
        r = np.random.default_rng(seed); p = r.standard_normal((n, 3)); self.p0 = p / np.linalg.norm(p, axis=1, keepdims=True)
        self.w = r.uniform(0.3, 1.0, (n, 3)); self.ph = r.uniform(0, 6.283, (n, 3))
        self.br = r.uniform(0.55, 1.35, n).astype(f32); self.bph = r.uniform(0, 6.283, n); self.bw = r.uniform(0.6, 1.6, n)
        self.cell = math.sqrt(4 * math.pi / n)

    def eval(self, v, t, speed=1.0, lw=0.22):
        v = warp(v, self.cell * 0.55, t * speed)
        p = self.p0 + 0.30 * self.cell * np.sin(speed * t * self.w + self.ph)
        p /= np.linalg.norm(p, axis=1, keepdims=True)
        d, i = cKDTree(p).query(v, k=2, workers=2)
        F1, F2 = d[:, 0], d[:, 1]
        lane = smooth(0.0, lw * self.cell, F2 - F1).astype(f32)
        b = self.br[i[:, 0]] * (1 + 0.28 * np.sin(1.7 * speed * t * self.bw[i[:, 0]] + self.bph[i[:, 0]]))
        core = np.clip(1.15 - 0.6 * (F1 / self.cell) ** 2, 0.4, 1.2)
        return lane, (b * core).astype(f32)


_WN = [fbm2((128, 256), 90 + i, 2.6) for i in range(3)]
def warp(v, amp, t):
    """domain warp of unit vectors by equirect noise (organic, non-polygonal cell edges)"""
    from scipy.ndimage import map_coordinates
    lon = np.arctan2(v[:, 0], v[:, 2]); lat = np.arcsin(np.clip(v[:, 1], -1, 1))
    u = (lon / (2 * np.pi) + 0.5) * 256 + t * 1.5; w = (lat / np.pi + 0.5) * 127
    off = np.stack([map_coordinates(n, [w, u % 256], order=1, mode="grid-wrap") for n in _WN], -1)
    v = v + amp * off
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def roty(v, a):
    c, s = math.cos(a), math.sin(a)
    return np.stack([v[..., 0] * c + v[..., 2] * s, v[..., 1], -v[..., 0] * s + v[..., 2] * c], -1)


def rotx(v, a):
    c, s = math.cos(a), math.sin(a)
    return np.stack([v[..., 0], v[..., 1] * c - v[..., 2] * s, v[..., 1] * s + v[..., 2] * c], -1)


PLASMA = np.array([(0.00, (0.12, 0.006, 0.004)), (0.30, (0.60, 0.05, 0.010)), (0.60, (1.40, 0.22, 0.03)),
                   (0.85, (2.30, 0.62, 0.10)), (1.10, (3.4, 1.4, 0.35)), (1.6, (5.0, 3.2, 1.6))], dtype=object)
_PX = np.array([p[0] for p in PLASMA], f32); _PC = np.array([p[1] for p in PLASMA], f32)
def plasma_col(v):
    v = np.clip(v, 0, 1.6)
    return np.stack([np.interp(v, _PX, _PC[:, c]) for c in range(3)], -1).astype(f32)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=LAMPS, hz_frac=0.68)
        self.hz = float(fg.horizon)
        self.C = (540.0, 560.0) if vertical else (1290.0, 392.0)
        # half-res sky grid
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.dx = xx - self.C[0]; self.dy = yy - self.C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        # view directions (inside Betelgeuse)
        v = np.stack([(xx - W / 2) / F_PX, (yy - self.hz) / F_PX - 0.0, np.ones_like(xx)], -1)
        self.vdir = (v / np.linalg.norm(v, axis=-1, keepdims=True)).reshape(-1, 3).astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # surfaces
        self.cells = {s["key"]: (Cells(s["cells"], 100 + i), Cells(s["fine"], 200 + i)) for i, s in enumerate(STARS) if s["cells"]}
        self.plasma_cells = (Cells(28, 301), Cells(420, 302), Cells(3000, 303))
        self.prom = [fbm2((8, 1024), 61 + i, 1.6)[0] for i in range(3)]
        self.flow = fbm2((256, 512), 71, 2.2)
        # foreground prep
        a = fg.a
        yyf0 = np.mgrid[0:H, 0:W][0].astype(f32)
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        nl = cv2.resize(fbm2((128, 128), 21, 2.6), (W, H), interpolation=cv2.INTER_CUBIC)
        self.frost_field = (0.62 * (1 - yyf0 / H) + 0.05 * nl).astype(f32)      # smooth creeping front, no alpha-edge holes
        self.shim = fbm2((256, 256), 81, 2.0)
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        er = np.random.default_rng(9); n = 420
        self.emb = dict(x=er.uniform(0, W, n), y0=er.uniform(0, 1, n), sp=er.uniform(0.07, 0.22, n), ph=er.uniform(0, 6.28, n),
                        sz=er.uniform(0.3, 1.0, n) ** 2, wob=er.uniform(5, 30, n))
        emph = {"15%", "25×", "13°", "79×", "700×", "VAPORIZED", "INSIDE", "FREEZES", "BOIL", "SMALL", "STAR", "SUN"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        if vertical: L.cap_y = 1010
        else: L.cap_y = 590

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        """blend weights between the previous and current star for sky / grade (crossfade around each swap)"""
        cur, t0, t1 = star_at(t)
        prev = None
        for ts, k in SWAPS:
            if ts == t0: idx = SWAPS.index((ts, k)); prev = "sun" if idx == 0 else ("sun" if SWAPS[idx - 1][1] == "sun2" else SWAPS[idx - 1][1])
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = SK[prev] if prev else SK[cur]; B = SK[cur]
        # anticipation: during the collapse of the current star, nothing changes yet
        return A, B, w, cur, t0, t1

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, col_u):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        sc = bb_vec(np.array(lerp(A["T"], B["T"], w)))
        gl = lerp(A["glow"], B["glow"], w)
        dd = np.maximum(self.d - Rp, 0)
        aure = np.exp(-dd / (45 + 0.3 * Rp)) * 0.9 + np.exp(-dd / (220 + 0.8 * Rp)) * 0.10
        sky = sky + (aure * gl)[..., None] * (0.35 + 0.65 * sc)
        bm = self.beams_layer(t, A, B, w, Rp, col_u)
        return sky, bm

    def beams_layer(self, t, A, B, w, Rp, col_u):
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = self.phi + twist * np.log(self.d / 30.0)
        reach = (1500 + 1.2 * Rp) * (1 - 0.7 * ease(col_u))
        dd = np.maximum(self.d - Rp, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(self.d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(self.dx.shape + (3,), f32)
        for bi, b in enumerate(self.beams):
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"])) * (1 + 0.6 * min(Rp, 400) / 400)
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.32) % 1.0 if b["rainbow"] else np.full(dp.shape, b["hue"], f32)
            def colof(S):
                if S["beams"] == "rainbow": return palette(x)
                return pal_list(S["beams"], x)
            c = colof(A) * (1 - w) + colof(B) * w if w < 1 else colof(B)
            acc += c * (g * I)[..., None]
        bI = lerp(A["bI"], B["bI"], w)
        return acc * rad[..., None] * 0.38 * bI

    # -------------------------------------------------------------------------------------------- star
    def draw_star(self, img, t, S, Rp, I_mul=1.0, wob=0.0, hot=0.0):
        """disc at Rp px: limb darkening, convection cells + granulation, prominences, corona glow, chromatic spikes"""
        cx, cy = self.C; H, W = img.shape[:2]
        T = S["T"] * (1 + hot)
        sc = bbcolor(T)
        pad = Rp * 1.6 + 380
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        ang = np.arctan2(dy, dx)
        reg = img[y0:y1, x0:x1]
        Re = Rp * (1 + wob * (0.07 * np.sin(3 * ang + 9 * t) + 0.05 * np.sin(5 * ang - 13 * t) + 0.03 * np.sin(8 * ang + 21 * t)))
        Rd = max(Rp, 1.1)
        if Rp < 12:                                                           # small disc (Sun, Proxima, Sirius)
            inside = smooth(Re + 0.9, Re - 0.9, d) if Rp > 1.5 else np.exp(-(d / 1.1) ** 2)
            area = min((Rp / Rd) ** 2, 1.0)
            mu = np.sqrt(np.clip(1 - (d / Rd) ** 2, 0, 1))
            ld = (1 - S["u"] * (1 - mu)) if Rp > 1.5 else 1.0
            reg += (inside * ld * S["surf"] * area * I_mul)[..., None] * (0.25 + 0.75 * sc) * np.array([1, 1, 1], f32)
        else:
            m = d < Re + 2
            ys, xs = np.nonzero(m[::2, ::2])
            surf = np.zeros(d.shape[:2] + (3,), f32)
            if len(ys):
                px = dx[::2, ::2][ys, xs] / Rd; py = dy[::2, ::2][ys, xs] / Rd
                r2 = np.clip(px * px + py * py, 0, 1); mu = np.sqrt(1 - r2)
                v = np.stack([px, py, mu], -1)
                v = rotx(roty(v, 0.05 * t + 0.7), 0.35)
                big, fine = self.cells[S["key"]]
                lb, bb = big.eval(v, t, 0.9, 0.55)
                lf, bf = fine.eval(v, t, 1.4, 0.45)
                cc = S["con"]
                tex = (1 - 0.65 * cc + 0.65 * cc * lb) * (1 + (bb - 1) * cc) * (0.72 + 0.28 * lf * bf)
                ld = (1 - S["u"] * (1 - mu)) * (0.55 + 0.45 * mu)
                val = tex * ld
                Tl = T * (0.80 + 0.22 * np.clip(tex, 0, 1.3)) * (0.86 + 0.14 * mu)
                col = bb_vec(Tl)
                y = lum(col)[..., None]; col = y + (col - y) * S["sat"]
                small = np.zeros(m[::2, ::2].shape + (3,), f32)
                if S.get("ramp") is not None:
                    col = ramp_col(S["ramp"], val * (1 + hot)); val = np.ones_like(val)
                small[ys, xs] = col * val[:, None] * S["surf"] * I_mul
                surf = cv2.resize(small, (d.shape[1], d.shape[0]), interpolation=cv2.INTER_LINEAR)
            edge = smooth(Re + 1.0, Re - 1.0, d)
            reg *= (1 - edge)[..., None]
            reg += surf * edge[..., None]
            # prominences / flame tongues on the limb
            th = (ang / (2 * np.pi) + 0.5) * 1024
            n1 = np.interp((th + t * 9) % 1024, np.arange(1024), self.prom[0]); n2 = np.interp((th * 3 - t * 23) % 1024, np.arange(1024), self.prom[1])
            hgt = Rp * (0.010 + 0.075 * np.clip(n1 * 0.7 + n2 * 0.5, 0, None) ** 1.6) + 2
            out_ = d > Re
            fl = np.exp(-(d - Re) / hgt) * out_
            pc = np.array([1.0, 0.30, 0.22], f32) * 0.5 + sc * 0.5
            reg += fl[..., None] * pc * S["surf"] * 0.55 * I_mul
        # corona + glow (all stars)
        dd = np.maximum(d - Re, 0)
        g = (np.exp(-dd / (0.06 * Rp + 3)) * 2.2 + np.exp(-dd / (0.35 * Rp + 22)) * 0.55 + np.exp(-dd / (Rp + 90)) * 0.12) * (d > Re - 1)
        if Rp < 12: g = g * (0.6 + 0.3 * S["surf"] / 40)
        reg += (g * S["glow"] * I_mul)[..., None] * (0.3 + 0.7 * sc) * (1 + 0.08 * math.sin(t * 2.3))
        # chromatic diffraction spikes
        if S["spikes"] > 0:
            for k in range(6):
                a = k * math.pi / 3 + 0.26 + 0.03 * math.sin(t * 0.5)
                al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
                base = np.exp(-pp / (1.6 + 0.012 * Rp)) * (al > Re * 0.8)
                for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                    reg[..., c] += base * np.exp(-np.maximum(al - Re, 0) / ((140 + 0.6 * Rp) * Lk)) * 2.2 * S["spikes"] * I_mul * (0.4 * min(S["spikes"] * 2, 1) + (1 - 0.4 * min(S["spikes"] * 2, 1)) * sc[c])
        img[y0:y1, x0:x1] = reg

    # -------------------------------------------------------------------------------------------- inside Betelgeuse
    def plasma(self, t):
        hh, hw = self.dx.shape
        v = rotx(roty(self.vdir, 0.025 * t), 0.08 * math.sin(0.2 * t))
        a, b, c = self.plasma_cells
        la, ba = a.eval(v, t, 0.8, 0.5); lb, bb = b.eval(v, t, 1.3, 0.45); lc, bc = c.eval(v, t, 2.0, 0.4)
        val = (0.25 + 0.75 * la) * ba * (0.55 + 0.45 * lb * bb) * (0.8 + 0.2 * lc * bc)
        val = val.reshape(hh, hw)
        fu = (self.hx * 0.35 + t * 22) % 512; fv = (self.hy * 0.35 - t * 30 + 30 * np.sin(self.hx / 260 + t * 0.4)) % 256
        flo = cv2.remap(self.flow, fu.astype(f32), fv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        val = val * (0.85 + 0.25 * flo)
        return plasma_col(val * 0.78) * 0.9

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, t, A, B, w, light):
        fg = self.fg
        def one(S):
            base = fg.rgb * (1 - S["flat"]) + fg.flat * S["flat"]
            if S["hc"] > 0: base = base * np.clip(lum(base)[..., None] / 0.18, 0.05, 6) ** S["hc"]
            tint = np.array(S["tint"], f32)
            sky_amb = (np.array(S["zen"], f32) * 0.5 + np.array(S["hor"], f32) * 0.5)
            out = base * tint * S["gain"] + fg.flat * sky_amb * S["amb"]
            rc = bbcolor(S["T"]) * (0.4 + 0.6 * tint)
            out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * rc * S["gain"] * 0.6 * fg.flat.mean()
            return out
        fa = one(A) if w < 1 else None
        fb = one(B)
        fgc = fb if fa is None else fa * (1 - w) + fb * w
        return fgc * light

    def frost_clean(self, img, amount, t):
        """clean bright blue-white crystalline frost: a creeping front from the near lawn, colour independent of the
        (dark, shadowed) plate underneath so there are no dark specks; sparkling glints"""
        fg = self.fg
        thr = amount * 1.35 - 0.25
        m = smooth(-0.08, 0.08, thr - self.frost_field) * np.maximum(fg.frost_cover, fg.ground)
        m = cv2.GaussianBlur(m, (0, 0), 1.5) * (0.7 + 0.3 * smooth(0.0, 1.0, amount))
        tex = np.clip(fg.crystal, 0.9, 1.25) * np.clip(fg.hf, 0.85, 1.35) ** 0.8
        fcol = (0.10 * tex)[..., None] * np.array([0.74, 0.88, 1.25], f32)
        out = img * (1 - m[..., None]) + np.maximum(img, fcol) * m[..., None]
        g = fg.glint_xy; mg = m[g[:, 1], g[:, 0]]
        tw = np.clip(np.sin(t * fg.glint_fr * 6.283 + fg.glint_ph), 0, 1) ** 10
        val = mg * tw * fg.glint_sz * 1.4
        sel = val > 1e-4
        if sel.any():
            H, W = img.shape[:2]
            lay = np.zeros((H, W), f32); np.add.at(lay, (g[sel, 1], g[sel, 0]), val[sel])
            lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 4 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 2
            out = out + lay[..., None] * np.array([0.85, 0.92, 1.0], f32)
        return out.astype(f32)

    def haze(self, t, a, col, rise=60.0):
        W, H = self.L.W, self.L.H; hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.45 + t * 14) % 512; mv = (sy * 0.6 + t * rise) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 520, hz - 40, sy) * (1 - 0.75 * smooth(hz + 40, H, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.3 - 0.25, 0, 1), (0, 0), 6)
        return self.up(m * band * a)[..., None] * np.array(col, f32)

    def embers(self, t, amt):
        W, H = self.L.W, self.L.H; e = self.emb
        y = H * (1.05 - ((e["y0"] + e["sp"] * t) % 1.0) * 1.1)
        x = e["x"] + e["wob"] * np.sin(t * 1.3 + e["ph"]) + 40 * np.sin(y / 300 + e["ph"])
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        tw = 0.6 + 0.4 * np.sin(t * 7 + e["ph"] * 3)
        np.add.at(lay, (yi, xi), e["sz"] * tw * amt)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.9) * 12 + cv2.GaussianBlur(lay, (0, 0), 4.0) * 6
        return self.up(lay)[..., None] * np.array([1.0, 0.45, 0.10], f32)

    def shimmer(self, img, amp, t):
        if amp <= 0: return img
        H, W = img.shape[:2]
        u = (self.xx * 0.12) % 256; v = (self.yy * 0.12 + t * 14) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = smooth(self.hz - 600, self.hz + 50, self.yy) * amp
        return cv2.remap(img, (self.xx + n * k).astype(f32), (self.yy + n * k * 0.6).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = SK[cur]
        pulse = 1 + 0.10 * math.sin(2 * math.pi * t / 1.6) + sum(0.6 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        # ---- current star size: bloom-in after its swap, collapse before the next swap
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        Rp = S["Rp"]
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        hot = 0.0
        if cur == "bet":                                                   # swells from Rigel-size until we are inside it
            gs = ease((t - T_BET0) / (T_INSIDE - T_BET0))
            Rp = 430 * math.exp(math.log(2600 / 430) * gs ** 1.6) * g_in
        else:
            Rp = Rp * g_in
        wob = 0.0
        if col_u > 0 and cur != "bet":                                     # old star: swell-wobble, then implode to a point
            if col_u < 0.45: Rp *= 1 + 0.35 * ease(col_u / 0.45); wob = col_u / 0.45
            else: v = (col_u - 0.45) / 0.55; Rp *= 1.35 * (1 - ease(v) ** 0.7) + 0.02; wob = 1 - v
            I_mul *= 1 + 5 * col_u ** 2; hot = 0.15 * col_u
        inside = smooth(1700, 2500, Rp) if cur == "bet" else 0.0
        sky, bm = self.sky(t, A, B, w, min(Rp, 900), col_u)
        if inside > 0:
            pl = self.plasma(t)
            sky = sky * (1 - inside) + pl * inside; bm = bm * (1 - inside)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        if inside < 0.999:
            Iv = I_mul * (1 - inside)
            self.draw_star(img, t, S, max(Rp, 0.3), Iv, wob, hot)
        # ---- foreground
        light = 1.0 + 0.12 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(t, A, B, w, light)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        if cur == "prox" or (A["key"] == "prox" and w < 1):
            kp = (1.0 if cur == "prox" else 1 - w)
            fr = ramp(t, T_FREEZE, T_FREEZE + 1.6) if cur == "prox" else 1.0
            if fr > 0: fgc = self.frost_clean(fgc, fr * kp, t)
            fgc = fg.lamps_light(fgc, kp * ramp(t, T_SW["prox"] + 0.8, T_SW["prox"] + 1.4) * 2.2, t)
        if cur == "bet": fgc = fgc * (1 + 0.6 * inside)
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # heat haze, steam, embers
        sh_amp = 0.0
        if cur == "sir": sh_amp = 1.5 * ramp(t, T_BOIL - 0.3, T_BOIL + 0.6)
        if cur == "rig": sh_amp = 2.0 + 3.0 * ramp(t, T_VAPOR, T_VAPOR + 1.0)
        if cur == "bet": sh_amp = 2.5 + 2.5 * inside
        if cur == "sir": img += self.haze(t, 0.35 * ramp(t, T_BOIL - 0.2, T_BOIL + 1.0), (0.5, 0.65, 0.9), rise=90)
        if cur == "rig":
            vap = ramp(t, T_VAPOR, T_VAPOR + 1.2)
            img += self.haze(t, 0.5 + 1.6 * vap, (1.2, 1.4, 1.8), rise=140)
            img = img * (1 + 1.2 * vap * a) + a * vap * np.array([0.9, 1.1, 1.5], f32) * 0.8
        if cur == "bet":
            img += self.haze(t, 0.5 + 0.6 * inside, (1.2, 0.30, 0.05), rise=110)
            img += self.embers(t, 0.4 + 0.6 * inside)
        img = self.shimmer(img, sh_amp, t)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = SK["sun" if k == "sun2" else k]
                fc = (0.4 + 0.6 * bbcolor(NS["T"]))
                img += (3.2 * math.exp(-max(u, 0) / 0.08) * (ease((u + 0.05) / 0.05))) * fc
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        # ---- final white-out (inside Betelgeuse -> our Sun is back)
        if T_WO0 < t < T_SUNBACK:
            v = ease((t - T_WO0) / (T_SUNBACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.92, 0.85], f32)
        img = self.chroma_bloom(img, 1.0)
        expo = lerp(A["expo"], B["expo"], w)
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        self.overlay(out, t, cur, t0)
        return out

    def chroma_bloom(self, img, amt):
        """bloom with slightly different radii per channel (red widest) -> chromatic halos"""
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
        S = SK[cur]
        # readout: name, size, temperature; slides in after each swap
        if L.vertical: x, ys = W / 2, (1205, 1290, 1350)
        else: x, ys = 470, (800, 875, 930)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "sun" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.9, T_SUNBACK + 1.2)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(S["name"]) < 12 else 1.15))
            rgba, _ = word_layer(S["name"], big, W * 0.9 if L.vertical else 820, fill=S["tc"])
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
        print("DUR", DUR); [print(s["key"], round(s["Rp"], 2), "px", round(ang_deg(s["R"]), 2), "deg") for s in STARS]
        print({k: round(v, 2) for k, v in T_SW.items()}, "inside", round(T_INSIDE, 2), "sunback", round(T_SUNBACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
