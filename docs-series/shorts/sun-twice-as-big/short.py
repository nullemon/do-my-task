"""WHAT IF THE SUN WERE BIGGER? -- one locked tripod shot of the park (A_park), BATCH3/4 swap format.
The Sun stays at 1 au and keeps its surface temperature (5,772 K), only its radius grows: 1x -> 2x -> 5x -> 10x. It is
drawn at its TRUE angular size through a ~31.5 deg vertical-FOV lens (f = 3400 px): 0.53, 1.07, 2.67, 5.33 deg. Luminosity
scales as R^2 (Stefan-Boltzmann at fixed T): 4x, 25x, 100x the light. The park is relit: the sky bleaches towards
white and shadows harden (2x), the grass browns and steams (5x), the air shimmers and steam pours off a scorched, brown
park under a white sky (10x). White-out back to today's Sun (loops). Surface: other-suns / sun-closer (animated Worley
supergranulation + granulation, limb darkening, sunspots, prominences, corona, chromatic spikes).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py stills 1.0,9.5       -> SCR/stills/<t>.png
  /home/user/ttsenv/bin/python short.py seg                  restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from lib.core import f32, Layout, ramp, smooth, ease, kf, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-sun-twice-as-big"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A_park.png"
FPS = 30
LEAD, TAIL = 0.25, 1.00
F_PX = 3400.0                                         # ~31.5 deg vertical FOV on 1920 px (a long lens: the 10x Sun ~316 px across)
RSUN_AU = 0.00465047                                  # R_sun / 1 au


PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for l in PL if l["key"] == key or (l["key"].startswith(key) and l["key"][len(key):].isalpha()) for w in l["words"] if w["cap"] == cap]
    return ws[n]["t0"]


def rad_px(R): return F_PX * math.tan(math.asin(min(R * RSUN_AU, 0.999)))
def ang_deg(R): return 2 * math.degrees(math.asin(min(R * RSUN_AU, 1.0)))


HOT_RAMP = [(0.0, (0.6, 0.20, 0.02)), (0.35, (1.4, 0.65, 0.10)), (0.7, (2.6, 1.55, 0.35)), (1.0, (3.8, 2.6, 0.9)), (1.4, (5.2, 4.4, 2.6))]   # white-gold
SUN_RAMP = [(0.0, (0.45, 0.10, 0.015)), (0.35, (1.5, 0.55, 0.08)), (0.7, (2.9, 1.55, 0.40)), (1.0, (4.2, 2.9, 1.15)), (1.4, (5.6, 4.7, 2.9))]


def ramp_col(rmp, v):
    xs = np.array([p[0] for p in rmp], f32); cs = np.array([p[1] for p in rmp], f32)
    return np.stack([np.interp(v, xs, cs[:, c]) for c in range(3)], -1).astype(f32)


# ------------------------------------------------------------------------------------------------ the stages
# R: radius (R_sun) at 1 au, T fixed -> L = R^2. Visual: sky zenith/horizon (linear), beams, surface brightness, glow,
# park grade (gain, tint, hc = shadow hardening exponent, amb = sky ambient), exposure, flash colour.
STAGES = [
    dict(key="now", R=1.0, name="TODAY'S SUN", l2="0.53° WIDE · 1× THE LIGHT", l3="SURFACE 5,772 K", tc=(255, 236, 170),
         zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), beams="rainbow", bI=1.0, surf=40.0, glow=1.0, spikes=0.6,
         gain=1.0, tint=(1.0, 0.98, 0.95), hc=0.0, amb=0.10, expo=1.0, fl=(1.0, 0.95, 0.85), bl=1.0),
    dict(key="x2", R=2.0, name="SUN × 2", l2="1.07° WIDE · 4× THE LIGHT", l3="MORE SUNLIGHT THAN VENUS GETS", tc=(255, 240, 200),
         zen=(0.16, 0.30, 0.80), hor=(0.80, 0.88, 1.02), beams=[(0.9, 0.95, 1.0), (1.0, 0.92, 0.7), (0.7, 0.85, 1.0), (1.0, 1.0, 0.9)], bI=1.0,
         surf=2.2, glow=0.75, spikes=0.35, cells=22, fine=420, gain=1.55, tint=(1.0, 0.99, 0.96), hc=0.30, amb=0.12, expo=0.92, fl=(1.0, 0.97, 0.9), bl=1.0),
    dict(key="x5", R=5.0, name="SUN × 5", l2="2.67° WIDE · 25× THE LIGHT", l3="~25 KW ON EVERY SQUARE METRE", tc=(255, 222, 150),
         zen=(0.36, 0.56, 1.02), hor=(1.10, 1.12, 1.15), beams=[(1.0, 0.95, 0.8), (1.0, 0.85, 0.55), (1.0, 1.0, 0.95), (0.9, 0.9, 1.0)], bI=1.1,
         surf=1.05, glow=1.6, spikes=0.35, cells=40, hot=0.8, fine=1600, gain=1.95, tint=(1.0, 0.95, 0.86), hc=0.42, amb=0.14, expo=0.70, fl=(1.0, 0.93, 0.8), bl=0.8),
    dict(key="x10", R=10.0, name="SUN × 10", l2="5.33° WIDE · 100× THE LIGHT", l3="OCEANS BOIL · EARTH ≥ 500 °C", tc=(255, 195, 110),
         zen=(0.42, 0.60, 1.05), hor=(1.20, 1.18, 1.16), beams=[(1.0, 0.9, 0.7), (1.0, 0.8, 0.5), (1.0, 1.0, 0.95), (1.0, 0.7, 0.4)], bI=1.2,
         surf=1.0, glow=1.9, spikes=0.35, cells=60, hot=1.0, fine=3200, gain=2.40, tint=(1.0, 0.90, 0.76), hc=0.68, amb=0.16, expo=0.60, fl=(1.0, 0.88, 0.7), bl=0.7),
]
for s in STAGES: s["Rp"] = rad_px(s["R"])
SK = {s["key"]: s for s in STAGES}

# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["now", "x2", "x5", "x10"]
T_SW = dict(x2=wt("x2", "2×") - 0.12, x5=wt("x5", "25×") - 0.12, x10=wt("x10", "100×") - 0.12)
COLLAPSE, BLOOM = 0.42, 0.65
T_WHITE = wt("x2b", "WHITE"); T_SHARP = wt("x2c", "SHARP")
T_BROWN = wt("x5b", "BROWN"); T_STEAM = wt("x5c", "STEAM")
T_SHIM = wt("x10b", "SHIMMERS"); T_BOIL = wt("x10c", "BOIL"); T_VENUS = wt("x10d", "VENUS")
T_SUNBACK = LN["end"]["start"] - 0.10
T_WO0 = T_SUNBACK - 0.85
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "now2")]
PULSES = [wt("hook", "BIGGER"), wt("x2", "2×"), wt("x2a", "VENUS"), wt("x2b", "WHITE"), wt("x2c", "SHARP"), wt("x5", "25×"),
          wt("x5b", "BROWN"), wt("x5c", "STEAM"), wt("x10", "100×"), wt("x10c", "BOIL"), wt("x10d", "VENUS"), wt("end3", "RIGHT")]


def stage_at(t):
    cur, t0 = "now", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("now" if k == "now2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


FX = dict(   # effect amounts as keyframes on the word timings (all cut to 0 at the white-out peak)
    brown=[(0, 0.0), (T_BROWN - 0.3, 0.0), (T_BROWN + 1.4, 0.65), (T_SW["x10"], 0.70), (T_SW["x10"] + 1.0, 0.95), (T_BOIL, 1.0)],
    scorch=[(0, 0.0), (T_SW["x10"], 0.0), (T_SW["x10"] + 1.6, 0.55), (T_BOIL + 1.0, 1.0)],
    park=[(0, 0.0), (T_SW["x10"], 0.0), (T_SW["x10"] + 0.8, 2.0), (T_SHIM - 0.2, 2.5), (T_SHIM + 0.8, 5.0)],
    steam=[(0, 0.0), (T_STEAM - 0.3, 0.0), (T_STEAM + 1.0, 0.55), (T_SW["x10"], 0.6), (T_SW["x10"] + 0.8, 0.8), (T_BOIL - 0.2, 0.8), (T_BOIL + 1.0, 1.1)],
    shim=[(0, 0.0), (T_SW["x2"], 0.0), (T_SW["x2"] + 0.8, 0.5), (T_SW["x5"], 0.6), (T_SW["x5"] + 0.8, 1.5), (T_SW["x10"], 1.7), (T_SHIM - 0.2, 2.2), (T_SHIM + 0.8, 4.0)],
)


def fx(name, t):
    if t >= T_SUNBACK: return 0.0
    return kf(t, FX[name])


# ------------------------------------------------------------------------------------------------ helpers (sun-closer)
def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


_WN = [fbm2((128, 256), 90 + i, 2.6) for i in range(3)]


def warp(v, amp, t):
    from scipy.ndimage import map_coordinates
    lon = np.arctan2(v[:, 0], v[:, 2]); lat = np.arcsin(np.clip(v[:, 1], -1, 1))
    u = (lon / (2 * np.pi) + 0.5) * 256 + t * 1.5; w = (lat / np.pi + 0.5) * 127
    off = np.stack([map_coordinates(n, [w, u % 256], order=1, mode="grid-wrap") for n in _WN], -1)
    v = v + amp * off
    return v / np.linalg.norm(v, axis=1, keepdims=True)


class Cells:
    """animated Worley cells on the unit sphere (supergranulation / granulation)"""
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


def roty(v, a):
    c, s = math.cos(a), math.sin(a)
    return np.stack([v[..., 0] * c + v[..., 2] * s, v[..., 1], -v[..., 0] * s + v[..., 2] * c], -1)


def rotx(v, a):
    c, s = math.cos(a), math.sin(a)
    return np.stack([v[..., 0], v[..., 1] * c - v[..., 2] * s, v[..., 1] * s + v[..., 2] * c], -1)


SPOTS = []
for lat, lon, rr in ((0.30, -0.5, 0.050), (0.26, -0.38, 0.030), (-0.22, 0.35, 0.042), (-0.25, 0.47, 0.024), (0.12, 1.2, 0.035)):
    SPOTS.append((np.array([math.cos(lat) * math.sin(lon), -math.sin(lat), math.cos(lat) * math.cos(lon)], f32), rr))


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.68)
        self.hz = float(fg.horizon)
        self.C = (600.0, 650.0)
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.dx = xx - self.C[0]; self.dy = yy - self.C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        self.cells = {s["key"]: (Cells(s["cells"], 100 + i), Cells(s["fine"], 200 + i)) for i, s in enumerate(STAGES) if s.get("cells")}
        self.prom = [fbm2((8, 1024), 61 + i, 1.6)[0] for i in range(3)]
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        self.shim = fbm2((256, 256), 81, 2.0)
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        # ---- vegetation masks on the plate: grass (ground, green) and foliage (green above the ground)
        rgb = fg.rgb
        gdom = smooth(1.02, 1.25, rgb[..., 1] / np.maximum(rgb[..., 0], 1e-4)) * smooth(0.9, 1.2, rgb[..., 1] / np.maximum(rgb[..., 2], 1e-4))
        veg = cv2.GaussianBlur((gdom * a).astype(f32), (0, 0), 0.8)
        self.grass = (veg * fg.ground).astype(f32); self.leaf = (veg * (1 - fg.ground)).astype(f32)
        Y = lum(rgb)[..., None]
        self.brown = (Y * np.array([1.55, 1.05, 0.52], f32) * (0.85 + 0.3 * np.clip(fg.hf, 0.6, 1.4)[..., None])).astype(f32)   # dry straw / dead leaves
        self.scorch = (Y * np.array([0.22, 0.14, 0.09], f32) + 0.004).astype(f32)                 # charred, near-black
        pn = cv2.resize(fbm2((160, 90), 151, 2.4), (W, H), interpolation=cv2.INTER_CUBIC)
        self.patch = smooth(-0.35, 0.55, pn + 0.25 * (np.clip(fg.hf, 0.6, 1.4) - 1)).astype(f32)   # where the lawn chars first
        emph = {"SUN", "BIGGER", "HOT", "WIDER", "2×", "VENUS", "WHITE", "SHADOW", "SHARP", "25×", "LIGHT", "GRASS", "BROWN", "STEAM",
                "100×", "AIR", "SHIMMERS", "OCEANS", "BOIL", "AWAY", "EARTH", "NORMAL", "SMALL", "RIGHT", "IMAGINE"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def mix_params(self, t):
        cur, t0, t1 = stage_at(t)
        prev = None
        for idx, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "now" if idx == 0 else ("now" if SWAPS[idx - 1][1] == "now2" else SWAPS[idx - 1][1])
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = SK[prev] if prev else SK[cur]; B = SK[cur]
        return A, B, w, cur, t0, t1

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, col_u, whiten):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        y = lum(sky)[..., None]; sky = sky + (y * 1.05 - sky) * whiten                  # bleaching towards white
        sc = bbcolor(5772)
        gl = lerp(A["glow"], B["glow"], w)
        dd = np.maximum(self.d - Rp, 0)
        hot = lerp(A.get("hot", 0.0), B.get("hot", 0.0), w)
        aure = np.exp(-dd / (45 + 0.3 * Rp)) * 0.9 + np.exp(-dd / (220 + 0.8 * Rp)) * (0.12 + 0.25 * whiten) + np.exp(-dd / (240 + 1.2 * Rp)) * 0.6 * hot
        sky = sky + (aure * gl)[..., None] * (0.35 + 0.65 * sc) * np.array(lerp(A["fl"], B["fl"], w), f32)
        return sky, self.beams_layer(t, A, B, w, Rp, col_u)

    def beams_layer(self, t, A, B, w, Rp, col_u):
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = self.phi + twist * np.log(self.d / 30.0)
        reach = (1500 + 1.2 * Rp) * (1 - 0.7 * ease(col_u))
        dd = np.maximum(self.d - Rp, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(self.d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(self.dx.shape + (3,), f32)
        for b in self.beams:
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
        return acc * rad[..., None] * 0.38 * lerp(A["bI"], B["bI"], w)

    # -------------------------------------------------------------------------------------------- the Sun (sun-closer)
    def draw_sun(self, img, t, S, Rp, I_mul=1.0, wob=0.0, hot=0.0):
        cx, cy = self.C; H, W = img.shape[:2]
        sc = bbcolor(5772 * (1 + hot))
        pad = Rp * 1.6 + 380
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        ang = np.arctan2(dy, dx)
        reg = img[y0:y1, x0:x1]
        Re = Rp * (1 + wob * (0.07 * np.sin(3 * ang + 9 * t) + 0.05 * np.sin(5 * ang - 13 * t) + 0.03 * np.sin(8 * ang + 21 * t)))
        Rd = max(Rp, 1.1); u_ld = 0.6
        small_disc = Rp < 4 or not S.get("cells")
        if small_disc:
            inside = smooth(Re + 0.9, Re - 0.9, d) if Rp > 1.5 else np.exp(-(d / 1.1) ** 2)
            area = min((Rp / Rd) ** 2, 1.0)
            mu = np.sqrt(np.clip(1 - (d / Rd) ** 2, 0, 1))
            ld = (1 - u_ld * (1 - mu)) if Rp > 1.5 else 1.0
            reg += (inside * ld * S["surf"] * area * I_mul)[..., None] * (0.25 + 0.75 * sc)
        else:
            m = d < Re + 2
            ys, xs = np.nonzero(m)
            surf = np.zeros(d.shape[:2] + (3,), f32)
            if len(ys):
                px = dx[ys, xs] / Rd; py = dy[ys, xs] / Rd
                r2 = np.clip(px * px + py * py, 0, 1); mu = np.sqrt(1 - r2)
                v = rotx(roty(np.stack([px, py, mu], -1), 0.03 * t + 0.4), 0.25)
                big, fine = self.cells[S["key"]]
                lb, bb = big.eval(v, t, 0.7, 0.55)
                lf, bf = fine.eval(v, t, 1.3, 0.45)
                tex = (0.55 + 0.45 * lb) * (1 + (bb - 1) * 0.5) * (0.62 + 0.38 * lf * bf)
                spot = np.zeros(len(ys), f32)
                for c, rr in SPOTS:
                    dang = np.arccos(np.clip(v @ c, -1, 1))
                    spot = np.maximum(spot, smooth(rr * 1.9, rr * 1.2, dang) * 0.55 + smooth(rr * 1.0, rr * 0.6, dang) * 0.4)
                ld = (1 - u_ld * (1 - mu)) * (0.55 + 0.45 * mu)
                val = tex * ld * (1 - spot)
                col = ramp_col(HOT_RAMP if S.get("hot") else SUN_RAMP, val * (1 + hot)) * np.clip(1.0 - 0.9 * spot, 0.1, 1)[:, None]
                surf[ys, xs] = col * S["surf"] * I_mul
            edge = smooth(Re + 1.0, Re - 1.0, d)
            reg *= (1 - edge)[..., None]
            reg += surf * edge[..., None]
            th = (ang / (2 * np.pi) + 0.5) * 1024
            n1 = np.interp((th + t * 9) % 1024, np.arange(1024), self.prom[0]); n2 = np.interp((th * 3 - t * 23) % 1024, np.arange(1024), self.prom[1])
            hgt = Rp * (0.010 + 0.085 * np.clip(n1 * 0.7 + n2 * 0.5, 0, None) ** 1.6) + 2
            fl = np.exp(-(d - Re) / hgt) * (d > Re)
            reg += fl[..., None] * np.array([1.0, 0.32, 0.12], f32) * S["surf"] * 1.6 * I_mul
            if S.get("hot"):                                                # corona streamers (white, radial, slowly turning)
                n3 = np.interp((th * 2 + t * 4) % 1024, np.arange(1024), self.prom[2]); n4 = np.interp((th * 5 - t * 6) % 1024, np.arange(1024), self.prom[0])
                ray = np.clip(0.55 + 0.6 * n3 + 0.35 * n4, 0, None) ** 2.5
                strm = ray * np.exp(-np.maximum(d - Re, 0) / (0.9 * Rp)) * (d > Re - 1)
                reg += (strm * 0.9 * S["hot"] * I_mul)[..., None] * np.array([1.0, 0.97, 0.9], f32)
        dd = np.maximum(d - Re, 0)
        g = (np.exp(-dd / (0.06 * Rp + 3)) * 2.2 + np.exp(-dd / (0.35 * Rp + 22)) * 0.55 + np.exp(-dd / (Rp + 90)) * 0.12) * (d > Re - 1)
        if small_disc: g = g * (0.6 + 0.3 * S["surf"] / 40)
        reg += (g * S["glow"] * I_mul)[..., None] * (0.3 + 0.7 * sc) * np.array(S["fl"], f32) * (1 + 0.08 * math.sin(t * 2.3))
        if S["spikes"] > 0:
            for k in range(6):
                a = k * math.pi / 3 + 0.26 + 0.03 * math.sin(t * 0.5)
                al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
                base = np.exp(-pp / (1.6 + 0.012 * Rp)) * (al > Re * 0.8)
                for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                    reg[..., c] += base * np.exp(-np.maximum(al - Re, 0) / ((140 + 0.6 * Rp) * Lk)) * 2.2 * S["spikes"] * I_mul * (0.4 + 0.6 * sc[c])
        img[y0:y1, x0:x1] = reg

    # -------------------------------------------------------------------------------------------- park
    def relight(self, A, B, w, light, brown, scorch):
        fg = self.fg
        base0 = fg.rgb
        if brown > 0:                                                    # grass (and later the leaves) dry out
            gm = (self.grass * brown + self.leaf * smooth(0.6, 1.0, brown) * 0.8)[..., None]
            base0 = base0 * (1 - gm) + self.brown * gm
        if scorch > 0:
            sm = (self.grass * np.clip(scorch * 1.6 * self.patch - 0.15 * (1 - scorch), 0, 1) * 0.92)[..., None]; base0 = base0 * (1 - sm) + self.scorch * sm
        def one(S):
            base = base0
            if S["hc"] > 0: base = base * np.clip(lum(base)[..., None] / 0.18, 0.05, 6) ** S["hc"]   # harder shadows, hotter highlights
            sky_amb = np.array(S["zen"], f32) * 0.5 + np.array(S["hor"], f32) * 0.5
            out = base * np.array(S["tint"], f32) * S["gain"] + fg.flat * sky_amb * S["amb"]
            out += (self.rim * 0.9)[..., None] * bbcolor(5772) * np.array(S["fl"], f32) * S["gain"] * 0.5 * fg.flat.mean()
            return out
        fb = one(B)
        return (fb if w >= 1 else one(A) * (1 - w) + fb * w) * light

    def haze(self, t, a, col, rise=60.0):
        H = self.L.H; hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.45 + t * 14) % 512; mv = (sy * 0.6 + t * rise) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 560, hz - 40, sy) * (1 - 0.6 * smooth(hz + 60, H, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.3 - 0.25, 0, 1), (0, 0), 6)
        return self.up(m * band * a)[..., None] * np.array(col, f32)

    def sun_haze(self, img, t, Rp, amp):
        """heat-haze shimmer in a ring around the Sun"""
        cx, cy = self.C; R = int(Rp * 2.8 + 120)
        x0, x1, y0, y1 = max(0, int(cx - R)), min(self.L.W, int(cx + R)), max(0, int(cy - R)), min(self.L.H, int(cy + R))
        xx, yy = self.xx[y0:y1, x0:x1], self.yy[y0:y1, x0:x1]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        k = smooth(Rp * 0.9, Rp * 1.15, d) * smooth(R, R * 0.6, d) * amp
        n = cv2.remap(self.shim, ((xx * 0.2) % 256).astype(f32), ((yy * 0.2 + t * 30) % 256).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        img[y0:y1, x0:x1] = cv2.remap(img, (xx + n * k).astype(f32), (yy + n * k * 0.7).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return img

    def park_heat(self, img, t, amp):
        """wavering heat distortion over the whole park (stronger near the ground, rising)"""
        u = (self.xx * 0.08) % 256; v = (self.yy * 0.10 + t * 24) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = smooth(self.hz - 900, self.hz + 200, self.yy) * amp
        return cv2.remap(img, (self.xx + n * k * 1.2).astype(f32), (self.yy + n * k * 0.5).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def shimmer(self, img, amp, t):
        if amp <= 0: return img
        u = (self.xx * 0.12) % 256; v = (self.yy * 0.12 + t * 16) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = smooth(self.hz - 700, self.hz + 30, self.yy) * (1 - 0.6 * smooth(self.hz + 30, self.L.H, self.yy)) * amp
        return cv2.remap(img, (self.xx + n * k).astype(f32), (self.yy + n * k * 0.6).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = SK[cur]
        pulse = 1 + 0.10 * math.sin(2 * math.pi * t / 1.6) + sum(0.6 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        Rp = S["Rp"] * g_in
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        hot = 0.0; wob = 0.0
        if col_u > 0:                                                          # old Sun: swell-wobble, then implode
            if col_u < 0.45: Rp *= 1 + 0.35 * ease(col_u / 0.45); wob = col_u / 0.45
            else: v = (col_u - 0.45) / 0.55; Rp *= 1.35 * (1 - ease(v) ** 0.7) + 0.02; wob = 1 - v
            I_mul *= 1 + 5 * col_u ** 2; hot = 0.15 * col_u
        whiten = 0.0
        if cur == "x2": whiten = 0.35 * ramp(t, T_WHITE - 0.3, T_WHITE + 0.9)
        elif cur in ("x5", "x10"): whiten = 0.12
        sky, bm = self.sky(t, A, B, w, min(Rp, 900), col_u, whiten)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u) * (1 - 0.5 * whiten))
        self.draw_sun(img, t, S, max(Rp, 0.3), I_mul, wob, hot)
        # ---- park
        light = 1.0 + 0.12 * (pulse - 1) - 0.2 * col_u
        hard = ramp(t, T_SHARP - 0.3, T_SHARP + 0.7) if cur == "x2" else 1.0
        Bh = dict(B, hc=B["hc"] * (0.4 + 0.6 * hard))
        fgc = self.relight(A, Bh, w, light, fx("brown", t), fx("scorch", t))
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        st = fx("steam", t)
        if st > 0:
            img += self.haze(t, 0.55 * st, (0.95, 0.97, 1.0), rise=110)
            img += self.haze(t + 13, 0.25 * st, (0.9, 0.92, 0.95), rise=150)
        img = self.shimmer(img, fx("shim", t), t)
        hz_sun = lerp(A.get("hot", 0.0), B.get("hot", 0.0), w) * (1 if t < T_SUNBACK else 0)
        if hz_sun > 0: img = self.sun_haze(img, t, Rp, 3.5 * hz_sun)
        pk = fx("park", t)
        if pk > 0: img = self.park_heat(img, t, pk)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = SK["now" if k == "now2" else k]
                img += (3.2 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * (0.4 + 0.6 * np.array(NS["fl"], f32))
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        if T_WO0 < t < T_SUNBACK:
            v = ease((t - T_WO0) / (T_SUNBACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.92, 0.85], f32)
        img = self.chroma_bloom(img, lerp(A["bl"], B["bl"], w) + 0.6 * max(0.0, ramp(t, T_WO0, T_SUNBACK)) * (t < T_SUNBACK))
        out = tonemap(img, lerp(A["expo"], B["expo"], w))
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        if cur != "now" and t0 > 0:
            self.today_ring(out, t, ramp(t, t0 + 0.5, t0 + 0.9) * (1 - ramp(t, t1 - 0.5, t1 - 0.3) if t1 < 1e8 else 1.0) * (1 - ramp(t, T_WO0 - 0.6, T_WO0)))
        self.overlay(out, t, cur, t0)
        return out

    def today_ring(self, out, t, a):
        """faint dashed ring at today's true solar size (0.53 deg) on the Sun, for comparison"""
        if a <= 0.01: return
        cx, cy = self.C; R = SK["now"]["Rp"] + 1.0
        x0, y0 = int(cx - R - 4), int(cy - R - 4); x1, y1 = int(cx + R + 5), int(cy + R + 5)
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy); ang = np.arctan2(dy, dx)
        dash = (np.sin(ang * 8 + t * 1.5) > -0.1).astype(f32)
        ring = np.clip(1.0 - np.abs(d - R) / 0.9, 0, 1) * dash * a
        halo = np.clip(1.0 - np.abs(d - R) / 2.2, 0, 1) * dash * a * 0.55
        reg = out[y0:y1, x0:x1]
        reg *= (1 - halo)[..., None]
        reg += ring[..., None] * (np.array([1.0, 1.0, 1.0], f32) - reg) * 0.95
        out[y0:y1, x0:x1] = reg

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W
        S = SK[cur]
        x, ys = W / 2, (262, 350, 410)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "now" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.9, T_SUNBACK + 1.2)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            rgba, _ = word_layer(S["name"], int(L.hud_size * 1.3), W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            for line, sz, col, yy in ((S["l2"], 0.62, (255, 255, 255), ys[1]), (S["l3"], 0.52, (255, 232, 190), ys[2])):   # stroked: legible on a white sky
                rgba, _ = word_layer(line, int(L.hud_size * sz), W * 0.92, fill=col); composite(out, rgba, x, yy + dy, a)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR); [print(s["key"], s["R"], "R_sun", round(s["Rp"], 2), "px", round(ang_deg(s["R"]), 3), "deg", s["R"] ** 2, "x light") for s in STAGES]
        print({k: round(v, 2) for k, v in T_SW.items()}, "sunback", round(T_SUNBACK, 2)); sys.exit()
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
