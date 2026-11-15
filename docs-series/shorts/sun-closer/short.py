"""WHAT IF EARTH MOVED CLOSER TO THE SUN? -- one locked tripod shot of the desert (01_desert), BATCH3 swap format.
Earth is moved, one step after another, closer to the Sun; the Sun is drawn at its TRUE angular size for each distance
through a ~65 deg vertical-FOV lens (f = 1500 px), and the dunes are relit: heat shimmer -> steam haze -> bleached sky and
red-glowing sand -> glass sheen -> molten lava under a Sun 27 deg wide. White-out back to today's Sun (loops).
  1 au -> 0.72 au (Venus) -> 0.39 au (Mercury) -> 0.1 au -> 0.02 au (hot-Jupiter distance) -> white-out -> 1 au
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info                     timeline + sizes
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5             stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py seg                      restart-safe segment render (SCR/segs) -> SCR/video_vert.mp4
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

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-sun-closer"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/01_desert.png"
FPS = 30
LEAD, TAIL = 0.25, 0.90
F_PX = 1500.0                                         # 65 deg vertical FOV on 1920 px (about the photo's own lens)
RSUN_AU = 0.00465047                                  # R_sun / 1 au

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for l in PL if l["key"] == key or l["key"].startswith(key + "_") for w in l["words"] if w["cap"] == cap]
    return ws[n]["t0"]


def rad_px(d):
    """apparent radius in px of the Sun seen from d au: full geometry, gnomonic lens"""
    return F_PX * math.tan(math.asin(min(RSUN_AU / d, 0.999)))


def ang_deg(d): return 2 * math.degrees(math.asin(min(RSUN_AU / d, 1.0)))


SUN_RAMP = [(0.0, (0.45, 0.10, 0.015)), (0.35, (1.5, 0.55, 0.08)), (0.7, (2.9, 1.55, 0.40)), (1.0, (4.2, 2.9, 1.15)), (1.4, (5.6, 4.7, 2.9))]


def ramp_col(rmp, v):
    xs = np.array([p[0] for p in rmp], f32); cs = np.array([p[1] for p in rmp], f32)
    return np.stack([np.interp(v, xs, cs[:, c]) for c in range(3)], -1).astype(f32)


# ------------------------------------------------------------------------------------------------ the stages
# d: Earth-Sun distance [au]. Visual params: sky zenith/horizon (linear), beam colours, sun surface brightness, glow,
# foreground grade (gain, tint, flattened-shadow fraction, ambient), exposure, flash colour.
STAGES = [
    dict(key="now", d=1.0, name="TODAY · 1 AU", l2="0.53° WIDE · 1× SUNLIGHT", l3="AVERAGE 15 °C", tc=(255, 236, 170),
         zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), beams="rainbow", bI=1.0, surf=40.0, glow=1.0, spikes=0.6,
         gain=1.0, tint=(1.0, 0.98, 0.95), flat=0.0, amb=0.10, expo=1.0, fl=(1.0, 0.95, 0.85)),
    dict(key="ven", d=0.723, name="VENUS'S ORBIT", l2="0.72 AU · 1.4× WIDER", l3="1.9× SUNLIGHT · RUNAWAY GREENHOUSE", tc=(255, 225, 150),
         zen=(0.07, 0.20, 0.62), hor=(0.80, 0.86, 0.98), beams=[(0.85, 0.95, 1.0), (1.0, 0.85, 0.45), (0.55, 0.85, 1.0), (1.0, 0.95, 0.75)],
         bI=1.0, surf=1.35, glow=0.42, spikes=0.12, cells=24, fine=500, gain=1.18, tint=(1.0, 0.97, 0.92), flat=0.12, amb=0.22, expo=0.95, fl=(1.0, 0.97, 0.9)),
    dict(key="mer", d=0.387, name="MERCURY'S ORBIT", l2="0.39 AU · 2.6× WIDER", l3="6.7× SUNLIGHT · ROCKS GLOW", tc=(255, 205, 120),
         zen=(0.42, 0.46, 0.62), hor=(1.35, 1.22, 1.00), beams=[(1.0, 0.92, 0.65), (1.0, 0.75, 0.35), (1.0, 1.0, 0.9), (1.0, 0.6, 0.3)],
         bI=1.1, surf=1.35, glow=0.48, spikes=0.12, cells=30, fine=800, gain=1.10, tint=(1.04, 0.90, 0.76), flat=0.25, amb=0.25, expo=0.85, fl=(1.0, 0.9, 0.7)),
    dict(key="p01", d=0.1, name="0.1 AU", l2="5.3° WIDE · 10× WIDER", l3="100× SUNLIGHT · SAND MELTS", tc=(255, 175, 80),
         zen=(0.50, 0.30, 0.13), hor=(1.45, 0.88, 0.36), beams=[(1.0, 0.65, 0.15), (1.0, 0.85, 0.40), (1.0, 0.40, 0.10), (1.0, 0.95, 0.6)],
         bI=1.2, surf=1.2, glow=1.8, spikes=0.5, gain=0.62, tint=(1.0, 0.64, 0.40), flat=0.35, amb=0.18, expo=0.88, fl=(1.0, 0.75, 0.4),
         cells=46, fine=1600),
    dict(key="skim", d=0.02, name="0.02 AU · HOT-JUPITER ORBIT", l2="27° WIDE · 50× WIDER", l3="2,500× SUNLIGHT", tc=(255, 140, 60),
         zen=(0.26, 0.050, 0.012), hor=(1.25, 0.36, 0.07), beams=[(1.0, 0.35, 0.05), (1.0, 0.60, 0.12), (1.0, 0.85, 0.35), (0.95, 0.20, 0.10)],
         bI=0.9, surf=0.62, glow=0.9, spikes=0.0, gain=0.45, tint=(1.0, 0.42, 0.20), flat=0.45, amb=0.25, expo=0.95, fl=(1.0, 0.6, 0.3),
         cells=70, fine=3200),
]
for s in STAGES: s["Rp"] = rad_px(s["d"]); s["T"] = 5772
for k, b in (('now', 1.0), ('ven', 1.0), ('mer', 0.95), ('p01', 0.7), ('skim', 0.42)): [s for s in STAGES if s['key'] == k][0]['bl'] = b
SK = {s["key"]: s for s in STAGES}

# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["now", "ven", "mer", "p01", "skim"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
COLLAPSE, BLOOM = 0.42, 0.65
T_BOIL = wt("ven", "OCEANS")
T_GLOW = wt("mer", "GLOW") - 0.2
T_GLASS = wt("p01", "MELTS")
T_LAVA = wt("skim", "DESERT")
T_SUNBACK = LN["end"]["start"] - 0.10
T_WO0 = T_SUNBACK - 0.85
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "now2")]
PULSES = [wt("hook", "SUN"), wt("ven", "2×"), wt("ven", "BOIL"), wt("mer", "~7×"), wt("mer", "GLOW"), wt("p01", "100×"),
          wt("p01", "GLASS"), wt("skim", "SKIM"), wt("skim", "50×"), wt("skim", "LAVA"), wt("end", "PLACE")]


def stage_at(t):
    cur, t0 = "now", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("now" if k == "now2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def fx_keys():
    """effect amounts as keyframes on the word timings (all cut to 0 under the white-out)"""
    s = T_SW
    return dict(
        shim=[(0, 0.0), (s["ven"], 0.0), (s["ven"] + 0.5, 1.2), (T_BOIL, 1.4), (T_BOIL + 1.0, 2.4), (s["mer"], 2.6), (s["mer"] + 0.6, 3.4),
              (s["p01"], 3.6), (s["p01"] + 0.6, 4.4), (s["skim"], 4.6), (s["skim"] + 0.8, 5.5)],
        steam=[(0, 0.0), (T_BOIL - 0.3, 0.0), (T_BOIL + 1.2, 1.0), (s["mer"] - 0.1, 1.0), (s["mer"] + 0.6, 0.45), (s["p01"], 0.3), (s["p01"] + 0.6, 0.0)],
        glow=[(0, 0.0), (T_GLOW - 0.3, 0.0), (T_GLOW + 1.0, 0.6), (s["p01"] - 0.1, 0.65), (s["p01"] + 0.6, 0.75), (s["skim"], 0.8), (s["skim"] + 0.8, 0.5), (T_LAVA + 1.0, 0.3)],
        glowT=[(0, 900.0), (T_GLOW, 900.0), (s["p01"], 1000.0), (s["p01"] + 0.6, 1350.0), (s["skim"] + 0.6, 1700.0)],
        char=[(0, 0.0), (T_GLOW - 0.4, 0.0), (T_GLOW + 1.2, 0.6), (s["p01"] + 0.5, 1.0)],
        glass=[(0, 0.0), (T_GLASS - 0.2, 0.0), (T_GLASS + 1.3, 1.0), (s["skim"], 1.0), (s["skim"] + 0.6, 0.6)],
        lava=[(0, 0.0), (s["skim"], 0.0), (s["skim"] + 0.7, 0.45), (T_LAVA - 0.2, 0.55), (T_LAVA + 1.2, 1.0)],
        smoke=[(0, 0.0), (s["p01"], 0.0), (T_GLASS, 0.0), (s["skim"], 0.2), (s["skim"] + 0.5, 0.7), (T_LAVA + 1.0, 1.0)],
    )


FX = fx_keys()


def fx(name, t):
    if t >= T_SUNBACK: return 0.0
    return kf(t, FX[name])


# ------------------------------------------------------------------------------------------------ helpers
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


# sunspot groups on the sphere (unit vectors, umbra radius in rad)
_sr = np.random.default_rng(77)
SPOTS = []
for lat, lon, rr in ((0.30, -0.5, 0.050), (0.26, -0.38, 0.030), (-0.22, 0.35, 0.042), (-0.25, 0.47, 0.024), (0.12, 1.2, 0.035)):
    SPOTS.append((np.array([math.cos(lat) * math.sin(lon), -math.sin(lat), math.cos(lat) * math.cos(lon)], f32), rr))

LAVA = [(0.0, (0.01, 0.002, 0.001)), (0.30, (0.12, 0.012, 0.003)), (0.55, (0.9, 0.10, 0.012)), (0.8, (2.8, 0.75, 0.07)), (1.0, (4.4, 1.9, 0.35)), (1.3, (6.0, 4.0, 1.6))]


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.68)
        self.hz = float(fg.horizon)
        self.C = (540.0, 540.0)
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
        er = np.random.default_rng(9); n = 520
        self.emb = dict(x=er.uniform(0, W, n), y0=er.uniform(0, 1, n), sp=er.uniform(0.07, 0.22, n), ph=er.uniform(0, 6.28, n),
                        sz=er.uniform(0.3, 1.0, n) ** 2, wob=er.uniform(5, 30, n))
        # ---- ground-plane coordinates (perspective-correct texture space on the dunes)
        gy = np.maximum(yyf - self.hz, 0) + 18.0
        self.gu = ((xxf - W / 2) / gy * 90.0).astype(f32)                      # X = (x - cx) h / gy
        self.gv = (F_PX * 90.0 / gy * 0.5).astype(f32)                         # Z = f h / gy (x0.5: squash, the dunes are not flat)
        self.gnear = smooth(0, 90, yyf - self.hz).astype(f32) * a              # fades the pattern out near the horizon (no aliasing)
        self.lavaN = [fbm2((512, 512), 300 + i, b) for i, b in enumerate((2.2, 1.6, 2.8))]
        # ripple crests of the real sand (photo high-pass) -> where the sand glows first
        crest = np.clip((fg.hf - 0.97) * 4.0, 0, 1)
        self.crest = cv2.GaussianBlur(crest, (0, 0), 1.2).astype(f32)
        Y = lum(fg.rgb)
        # vegetation (the bushes): low-saturation / greenish pixels on the plate
        rgb = fg.rgb
        sat = (rgb.max(2) - rgb.min(2)) / np.maximum(rgb.max(2), 1e-4)
        veg = smooth(0.62, 0.45, sat) * smooth(0.95, 1.15, rgb[..., 1] / np.maximum(rgb[..., 0], 1e-4) + 0.25) * a
        self.veg = cv2.GaussianBlur(np.clip(veg * 1.4, 0, 1), (0, 0), 1.0).astype(f32)
        self.Y = Y
        # glitter noise for the glass / molten sheen
        self.glit = fbm2((512, 512), 401, 0.6)
        emph = {"SUN", "2×", "BOIL", "~7×", "GLOW", "RED", "100×", "GLASS", "SKIM", "50×", "LAVA", "PLACE", "IMAGINE", "CLOSER",
                "JUPITERS", "VENUS'S", "MERCURY'S"}
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
    def sky(self, t, A, B, w, Rp, col_u):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        sc = bbcolor(5772)
        gl = lerp(A["glow"], B["glow"], w)
        dd = np.maximum(self.d - Rp, 0)
        aure = np.exp(-dd / (45 + 0.3 * Rp)) * 0.9 + np.exp(-dd / (220 + 0.8 * Rp)) * 0.12
        warmc = np.array(lerp(A["fl"], B["fl"], w), f32)
        sky = sky + (aure * gl)[..., None] * (0.35 + 0.65 * sc) * warmc
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

    # -------------------------------------------------------------------------------------------- the Sun
    def draw_sun(self, img, t, S, Rp, I_mul=1.0, wob=0.0, hot=0.0):
        """small: blinding limb-darkened disc; large: granulation + supergranulation cells, sunspots, prominences, corona"""
        cx, cy = self.C; H, W = img.shape[:2]
        sc = bbcolor(5772 * (1 + hot))
        pad = Rp * 1.6 + 380
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        ang = np.arctan2(dy, dx)
        reg = img[y0:y1, x0:x1]
        Re = Rp * (1 + wob * (0.07 * np.sin(3 * ang + 9 * t) + 0.05 * np.sin(5 * ang - 13 * t) + 0.03 * np.sin(8 * ang + 21 * t)))
        Rd = max(Rp, 1.1)
        u_ld = 0.6
        small_disc = Rp < 4 or not S.get("cells")
        if small_disc:
            inside = smooth(Re + 0.9, Re - 0.9, d) if Rp > 1.5 else np.exp(-(d / 1.1) ** 2)
            area = min((Rp / Rd) ** 2, 1.0)
            mu = np.sqrt(np.clip(1 - (d / Rd) ** 2, 0, 1))
            ld = (1 - u_ld * (1 - mu)) if Rp > 1.5 else 1.0
            reg += (inside * ld * S["surf"] * area * I_mul)[..., None] * (0.25 + 0.75 * sc)
        else:
            m = d < Re + 2
            st = 1 if Rp < 40 else 2                                        # full-res texture for the small discs
            ys, xs = np.nonzero(m[::st, ::st])
            surf = np.zeros(d.shape[:2] + (3,), f32)
            if len(ys):
                px = dx[::st, ::st][ys, xs] / Rd; py = dy[::st, ::st][ys, xs] / Rd
                r2 = np.clip(px * px + py * py, 0, 1); mu = np.sqrt(1 - r2)
                v = np.stack([px, py, mu], -1)
                v = rotx(roty(v, 0.03 * t + 0.4), 0.25)
                big, fine = self.cells[S["key"]]
                lb, bb = big.eval(v, t, 0.7, 0.55)
                lf, bf = fine.eval(v, t, 1.3, 0.45)
                tex = (0.55 + 0.45 * lb) * (1 + (bb - 1) * 0.5) * (0.62 + 0.38 * lf * bf)
                spot = np.zeros(len(ys), f32)
                for c, rr in SPOTS:
                    ca = np.clip(v @ c, -1, 1); dang = np.arccos(ca)
                    spot = np.maximum(spot, smooth(rr * 1.9, rr * 1.2, dang) * 0.55 + smooth(rr * 1.0, rr * 0.6, dang) * 0.4)
                ld = (1 - u_ld * (1 - mu)) * (0.55 + 0.45 * mu)
                val = tex * ld * (1 - spot)
                fac = np.clip(1.0 - 0.9 * spot, 0.1, 1)
                col = ramp_col(SUN_RAMP, val * (1 + hot)) * fac[:, None]
                small = np.zeros(m[::st, ::st].shape + (3,), f32)
                small[ys, xs] = col * S["surf"] * I_mul
                surf = cv2.resize(small, (d.shape[1], d.shape[0]), interpolation=cv2.INTER_LINEAR)
            edge = smooth(Re + 1.0, Re - 1.0, d)
            reg *= (1 - edge)[..., None]
            reg += surf * edge[..., None]
            th = (ang / (2 * np.pi) + 0.5) * 1024
            n1 = np.interp((th + t * 9) % 1024, np.arange(1024), self.prom[0]); n2 = np.interp((th * 3 - t * 23) % 1024, np.arange(1024), self.prom[1])
            hgt = Rp * (0.010 + 0.085 * np.clip(n1 * 0.7 + n2 * 0.5, 0, None) ** 1.6) + 2
            fl = np.exp(-(d - Re) / hgt) * (d > Re)
            pc = np.array([1.0, 0.32, 0.12], f32)
            reg += fl[..., None] * pc * S["surf"] * 1.6 * I_mul
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

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, A, B, w, light):
        fg = self.fg
        def one(S):
            base = fg.rgb * (1 - S["flat"]) + fg.flat * S["flat"]
            tint = np.array(S["tint"], f32)
            sky_amb = np.array(S["zen"], f32) * 0.5 + np.array(S["hor"], f32) * 0.5
            out = base * tint * S["gain"] + fg.flat * sky_amb * S["amb"]
            out += (self.rim * 0.9)[..., None] * bbcolor(5772) * np.array(S["fl"], f32) * S["gain"] * 0.5 * fg.flat.mean()
            return out
        fb = one(B)
        return (fb if w >= 1 else one(A) * (1 - w) + fb * w) * light

    def ground_tex(self, t, k, speed_v=0.0, speed_u=0.0, su=1.0, sv=1.0):
        u = (self.gu * su + speed_u * t) % 512; v = (self.gv * sv + speed_v * t) % 512
        return cv2.remap(self.lavaN[k], u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def molten(self, fgc, t, glow, glowT, char, glass, lava, refl_src):
        """sand: scorched + glowing crests -> glass sheen (sky/sun reflection, glitter path) -> lava flow"""
        a = self.fg.a; gm = self.fg.ground * a; H, W = fgc.shape[:2]
        out = fgc
        if char > 0:                                                    # bushes wither and char
            v = self.veg[..., None] * char
            out = out * (1 - v * 0.92) + v * 0.01 * np.array([0.6, 0.3, 0.2], f32)
        if glow > 0:
            out = out * (1 - 0.85 * glow * gm)[..., None]               # the sand darkens / scorches as its glow takes over
            gc = bbcolor(glowT) * (0.6 + 1.2 * smooth(900, 1700, glowT))
            n = self.ground_tex(t, 1, 0.0, 0.0, 0.6, 0.6) * 0.5 + 0.5
            pat = (0.12 + 0.88 * self.crest ** 1.5) * (0.5 + 0.8 * n) * (0.4 + 0.6 * self.gnear)
            em = (glow * pat * gm)[..., None] * gc * 2.4
            em = em + cv2.GaussianBlur(em, (0, 0), 6) * 0.5
            vv = self.veg[..., None] * smooth(0.5, 1.0, char)
            em = em + vv * glow * bbcolor(1200) * 0.6 * (0.6 + 0.4 * n[..., None])   # charred bushes smoulder
            out = out + em
        if glass > 0:                                                   # molten glass sheen: reflection of the sky and the Sun
            dn = (self.ground_tex(t, 0, -40.0, 6.0, 1.6, 1.6) * 7.0 + self.ground_tex(t, 2, -25.0, -4.0, 3.0, 3.0) * 3.0)
            k = smooth(0, 700, self.yy - self.hz)
            my = (2 * self.hz - self.yy + dn * (1 + 3 * k)).astype(f32)
            mx = (self.xx + dn * 0.6 * (1 + 2 * k)).astype(f32)
            refl = cv2.remap(refl_src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            refl = cv2.GaussianBlur(refl, (0, 0), 2.0)
            out = out * (1 - 0.55 * glass * gm)[..., None]                   # glass is darker and glossy
            fres = (0.35 + 0.55 * np.exp(-(self.yy - self.hz) / 160.0)) * gm * glass
            out = out * (1 - fres[..., None] * 0.85) + refl * fres[..., None] * 0.75
            # glitter path under the Sun
            gl = cv2.remap(self.glit, ((self.xx * 0.9) % 512).astype(f32), ((self.gv * 0.8 - t * 30) % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            spark = np.clip(gl * 0.8 - 0.9, 0, None) ** 2 * 5.0
            wpath = 30 + 0.30 * np.maximum(self.yy - self.hz, 0)
            path = np.exp(-((self.xx - self.C[0]) / wpath) ** 2) * gm * glass
            spec = (glass * gm * self.crest ** 2 * (0.35 + 0.65 * np.clip(gl * 0.5 + 0.5, 0, 1)) * (0.3 + 0.7 * self.gnear))[..., None]
            out = out + spec * np.array([2.2, 1.5, 0.8], f32)                 # glossy highlights on the glassy ripple crests
            out = out + (path * (0.10 + spark) * (0.4 + 0.6 * self.gnear))[..., None] * np.array([1.4, 0.9, 0.5], f32) * 0.6
        if lava > 0:                                                    # flowing lava: dark crust plates, glowing cracks
            n0 = self.ground_tex(t, 0, -14.0, 3.0, 0.32, 0.32); n1 = self.ground_tex(t, 1, -22.0, -4.0, 0.9, 0.9)
            ridge = (1 - np.abs(n0 * 0.8 + n1 * 0.3)) ** 5
            heat = np.clip(0.18 + 0.85 * ridge + 0.12 * n1 + 0.10 * self.crest, 0, 1.2)
            heat = heat * (0.55 + 0.45 * self.gnear) + 0.42 * (1 - self.gnear)
            lav = ramp_col(LAVA, heat) * (0.42 + 0.05 * math.sin(t * 3.1))
            m = (lava * gm)[..., None]
            out = out * (1 - m * 0.9) + lav * m
        return out

    def haze(self, t, a, col, rise=60.0):
        H = self.L.H; hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.45 + t * 14) % 512; mv = (sy * 0.6 + t * rise) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 560, hz - 40, sy) * (1 - 0.75 * smooth(hz + 40, H, sy))
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
        if cur == "skim": Rp *= 1 + 0.012 * math.sin(t * 1.7)                  # the giant Sun breathes slightly
        if col_u > 0:                                                          # old Sun: swell-wobble, then implode to a point
            if col_u < 0.45: Rp *= 1 + 0.35 * ease(col_u / 0.45); wob = col_u / 0.45
            else: v = (col_u - 0.45) / 0.55; Rp *= 1.35 * (1 - ease(v) ** 0.7) + 0.02; wob = 1 - v
            I_mul *= 1 + 5 * col_u ** 2; hot = 0.15 * col_u
        sky, bm = self.sky(t, A, B, w, min(Rp, 900), col_u)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        self.draw_sun(img, t, S, max(Rp, 0.3), I_mul, wob, hot)
        # ---- foreground
        light = 1.0 + 0.12 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(A, B, w, light)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        glow, glass, lava = fx("glow", t), fx("glass", t), fx("lava", t)
        if glow > 0 or glass > 0 or lava > 0 or fx("char", t) > 0:
            fgc = self.molten(fgc, t, glow, fx("glowT", t), fx("char", t), glass, lava, img)
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        st = fx("steam", t)
        if st > 0: img += self.haze(t, 0.55 * st, (0.85, 0.9, 1.0), rise=90)
        sm = fx("smoke", t)
        if sm > 0:
            img += self.haze(t + 7, 0.45 * sm, (1.3, 0.45, 0.10), rise=120)
            img += self.embers(t, 0.5 * sm + 0.5 * lava)
        img = self.shimmer(img, fx("shim", t), t)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = SK["now" if k == "now2" else k]
                fc = 0.4 + 0.6 * np.array(NS["fl"], f32)
                img += (3.2 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        # ---- final white-out (giant Sun -> today's Sun)
        if T_WO0 < t < T_SUNBACK:
            v = ease((t - T_WO0) / (T_SUNBACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.92, 0.85], f32)
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
        reg *= (1 - halo)[..., None]                                     # dark outline so it reads on the bright disc
        reg += ring[..., None] * (np.array([1.0, 1.0, 1.0], f32) - reg) * 0.95
        out[y0:y1, x0:x1] = reg

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
        S = SK[cur]
        x, ys = W / 2, (1205, 1290, 1350)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "now" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.9, T_SUNBACK + 1.2)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(S["name"]) < 14 else 1.0))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.62), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (250, 240, 228), a, 0.10, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR); [print(s["key"], s["d"], "au", round(s["Rp"], 2), "px", round(ang_deg(s["d"]), 3), "deg") for s in STAGES]
        print({k: round(v, 2) for k, v in T_SW.items()}, "boil", round(T_BOIL, 2), "glow", round(T_GLOW, 2), "glass", round(T_GLASS, 2),
              "lava", round(T_LAVA, 2), "sunback", round(T_SUNBACK, 2)); sys.exit()
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); im = sc.frame(t)
        save(im, os.path.join(SCR, "stills", f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
