"""WHAT IF THE MOON GOT CLOSER? -- one locked tripod shot of the mountain valley (B_valley), blue hour into night.
The Moon is swapped in at closer and closer distances (384,400 -> 200,000 -> 100,000 -> 50,000 -> 20,000 km -> the
Roche limit, ~18,400 km), always at its true angular size theta = 2 asin(R/d) through one fixed lens (f = 4000 px,
27 deg vertical field of view on the 1920 px frame), so the discs keep their exact relative sizes. Every swap: the old
Moon swells and implodes, a flash + chromatic shockwave, the new Moon blooms in, and the valley is relit by its light
(moonlight grows as 1/d^2). Tides (1/d^3) are shown by readouts, valley haze surges and a ground tremble; no water is drawn.
At the Roche limit the Moon cracks, breaks into fragments that shear along its orbit and spread into a glowing ring.
A white-out returns to today's small Moon (loops).
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
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, noise1, splat
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from moon import Moon, pole_vec, night_mask

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-moon-closer"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.00
F_PX = 4000.0            # the lens for the Moon discs (27 deg vertical FOV)
F_SKY = 1400.0           # sky gradient / extinction / star field (stylised blue-hour dome)
D0 = 384400.0
R_MOON = 1737.4
ROCHE_KM = 2.44 * 6371.0 * (5.514 / 3.344) ** (1 / 3)        # fluid Roche limit, Moon around Earth: 18,365 km
TIDE0_M = 0.535                                              # equilibrium lunar tide range today: 1.5 (m/M)(R/d)^3 R

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def ang_deg(d): return 2 * math.degrees(math.asin(R_MOON / d))
def rad_px(d): return F_PX * math.tan(math.asin(R_MOON / d))
def sig2(x):
    """2 significant figures, thousands separators"""
    p = 10 ** max(int(math.floor(math.log10(x))) - 1, 0); v = round(x / p) * p
    return f"{v:,.0f}" if v >= 10 else f"{x:.1f}".rstrip("0").rstrip(".")


# ------------------------------------------------------------------------------------------------ the stages
# Visual: sky tint, glow colour, beam palette, readout colour. Light levels are derived from d.
STAGES = [
    dict(key="today", d=D0, tc=(235, 240, 255), glow=(0.60, 0.68, 0.90),
         beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.10, corona=1.0),
    dict(key="d200", d=200000.0, tc=(150, 215, 255), glow=(0.55, 0.75, 1.0),
         beams=[(0.40, 0.80, 1.0), (0.60, 0.55, 1.0), (0.35, 1.0, 0.85)], bI=0.16, corona=1.0),
    dict(key="d100", d=100000.0, tc=(120, 255, 220), glow=(0.50, 0.95, 0.95),
         beams=[(0.30, 1.0, 0.80), (0.35, 0.65, 1.0), (0.70, 0.45, 1.0), (0.45, 1.0, 1.0)], bI=0.24, corona=0.7),
    dict(key="d50", d=50000.0, tc=(255, 200, 120), glow=(0.95, 0.85, 0.75),
         beams=[(1.0, 0.65, 0.30), (0.85, 0.45, 1.0), (0.40, 0.75, 1.0), (1.0, 0.45, 0.55)], bI=0.34, corona=0.4),
    dict(key="d20", d=20000.0, tc=(255, 150, 120), glow=(1.0, 0.90, 0.85),
         beams=[(1.0, 0.55, 0.35), (0.65, 0.45, 1.0), (0.35, 0.85, 1.0), (1.0, 0.85, 0.40), (1.0, 0.40, 0.70)], bI=0.48, corona=0.0),
    dict(key="roche", d=ROCHE_KM, tc=(255, 120, 90), glow=(1.0, 0.80, 0.60),
         beams=[(1.0, 0.45, 0.20), (1.0, 0.85, 0.35), (0.85, 0.35, 1.0), (0.35, 0.80, 1.0), (1.0, 0.35, 0.55)], bI=0.62, corona=0.0),
]
for s in STAGES:
    d = s["d"]; s["Rp"] = rad_px(d); s["ang"] = ang_deg(d)
    s["x"] = s["ang"] / ang_deg(D0); s["tide"] = (D0 / d) ** 3; s["M"] = (D0 / d) ** 2      # size, tidal force, moonlight
    tm = TIDE0_M * s["tide"]
    s["tide_txt"] = f"OCEAN TIDE ≈ {sig2(tm / 1000)} KM" if tm >= 1000 else f"OCEAN TIDE ≈ {sig2(tm)} M"
    s["name"] = f"{d:,.0f} KM"
    s["l2"] = f"{sig2(s['x'])}× TODAY'S SIZE · {s['ang']:.2g}° WIDE" if s["key"] != "today" else "TODAY · 0.52° WIDE"
    s["l3"] = f"TIDES {(round(s['tide']) if s['tide'] < 100 else sig2(s['tide']))}× STRONGER" if s["key"] != "today" else "TIDES 1×"
    s["l4"] = s["tide_txt"]
    s["gain"] = 0.05 * s["M"] ** 0.56                                  # valley moonlight (compressed from M)
    s["skyl"] = (s["M"] ** 0.5 - 1) / 19.0                             # scattered moonlight in the sky
    s["es"] = min(0.006 * (D0 / d) ** 1.1, 0.16)                     # earthshine on the night side
BK = {s["key"]: s for s in STAGES}
BK["roche"].update(name="ROCHE LIMIT", l2=f"≈ 18,000 KM · {sig2(BK['roche']['x'])}× TODAY'S SIZE",
                   l3=f"TIDES {sig2(BK['roche']['tide'])}× STRONGER", l4="EARTH'S GRAVITY TEARS IT APART")
BK["roche"]["gain"] *= 1.15
END = dict(BK["today"], key="end", name="384,400 KM", l2="DRIFTING AWAY", l3="+3.8 CM EVERY YEAR", l4="")
BK["end"] = END
ORDER = ["today", "d200", "d100", "d50", "d20", "roche"]

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
T_BACK = wt("end", "DRIFTING") - 0.15             # white-out peak -> today's Moon is back
T_WO0 = T_BACK - 0.70
T_RISE0, T_RISE1 = T_SW["d20"], T_SW["d20"] + 2.8
T_CRACK = wt("roche", "ROCHE") - 0.15
T_RIP = wt("roche_b", "RIPS") - 0.05
T_RING = wt("roche_b", "RING")
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_BACK, "end")]
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook_b", "CLOSER"), wt("today", "TODAY"), wt("d200", "TWICE"), wt("d200_b", "7×"), wt("d100", "57×"), wt("d100_b", "INLAND"),
          wt("d50", "50,000"), wt("d50_b", "QUAKES"), wt("d50_b", "DETAIL"), wt("d20_b", "HIGH"), wt("roche", "ROCHE"),
          wt("end", "AWAY")]
QUAKES = [(wt("d50_b", "QUAKES"), 1.0), (wt("d50_b", "VOLCANOES"), 0.8), (wt("d20_b", "TIDES"), 0.9), (wt("d20_b", "HIGH"), 1.0),
          (T_CRACK, 1.0), (T_RIP, 1.6), (T_RING, 1.0)]


def body_at(t):
    """-> (current key, swap time of current stage, next swap time)"""
    cur, t0 = "today", -10.0
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


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        assert vertical, "9:16 only"
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.70)
        self.hz = float(fg.horizon)
        self.C = (540.0, 600.0)
        self.RISE0 = (540.0, self.hz + 90.0)                      # the 20,000 km Moon rises from behind the ridge
        self.cam = SkyCam(W, H, self.hz, F_SKY)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.maximum(np.degrees(np.arctan2(self.hz - yy, F_SKY)), 0).astype(f32)
        xr = xx / W
        # blue hour (twilight) sky
        zen = np.array([0.010, 0.030, 0.115], f32)
        sky = zen * (0.62 + 0.38 * np.exp(-e / 28))[..., None]
        sky += np.array([0.05, 0.075, 0.16], f32) * np.exp(-e / 11)[..., None]
        belt = np.exp(-((e - 8.5) / 5.5) ** 2) * (0.55 + 0.45 * xr)                           # Belt of Venus
        sky += np.array([0.15, 0.065, 0.085], f32) * belt[..., None]
        shadow = np.exp(-e / 3.2)                                                            # Earth's shadow band
        sky = sky * (1 - 0.30 * shadow)[..., None] + np.array([0.02, 0.035, 0.075], f32) * shadow[..., None]
        self.blue_sky = sky.astype(f32)
        # night (never pitch black: deep blue with a faint horizon glow)
        nsky = np.array([0.004, 0.009, 0.034], f32) * (0.75 + 0.25 * np.exp(-e / 25))[..., None]
        nsky += np.array([0.012, 0.018, 0.040], f32) * np.exp(-e / 7)[..., None]
        self.night_sky = nsky.astype(f32)
        # scattered moonlight: a Rayleigh-blue sky, brighter low down
        self.moon_sky = (np.array([0.018, 0.045, 0.130], f32) * (0.7 + 0.3 * np.exp(-e / 15))[..., None]
                         + np.array([0.020, 0.035, 0.060], f32) * np.exp(-e / 6)[..., None]).astype(f32)
        self.k_hor = np.exp(-e / 14)[..., None].astype(f32)
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.hz - yyf, F_SKY)), 0.25)
        X = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        tau = np.array([0.06, 0.09, 0.17], f32)
        self.ext = np.exp(-X[:, None] * tau[None, :])[:, None, :].astype(f32) * np.ones((1, W, 1), f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # the Moon: one renderer per apparent size (map pre-filtered to the on-screen scale)
        pole = pole_vec(-12, 4); lon0 = 0.0
        self.big = Moon(BK["roche"]["Rp"], pole, lon0, surf=1.0)
        self.moon = {k: Moon(BK[k]["Rp"], pole, lon0, surf=1.0) for k in ("today", "d200", "d100", "d50")}
        self.moon["d20"] = self.big; self.moon["roche"] = self.big; self.moon["end"] = self.moon["today"]
        # foreground prep: rim light on the skyline
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        self.shim = fbm2((256, 256), 81, 2.0)
        yyf2, xxf2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf2, yyf2
        self._fragments()
        emph = {"MOON", "CLOSER", "SCALE", "200,000", "TWICE", "7×", "100,000", "57×", "INLAND", "50,000", "450×", "QUAKES",
                "VOLCANOES", "CRATER", "DETAIL", "20,000", "KILOMETERS", "HIGH", "TODAY", "18,000", "ROCHE", "RIPS", "RING",
                "3.8 CM", "AWAY"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1040

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- the break-up
    def _fragments(self):
        """Voronoi fragments of the Roche-limit disc + the orbit arc they spread along + dust"""
        R = BK["roche"]["Rp"]; self.R_big = R
        r = np.random.default_rng(77)
        seeds = [(0.0, 0.0)]
        for ring, n in ((0.38, 7), (0.68, 12), (0.92, 16)):
            for i in range(n):
                a = 2 * math.pi * (i + r.uniform(-0.3, 0.3)) / n + ring * 3
                rr = ring * R * r.uniform(0.85, 1.12)
                seeds.append((rr * math.cos(a), rr * math.sin(a)))
        self.seeds = np.array(seeds, f32)
        n = int(math.ceil(R * 1.02 + 4)); self.fr_half = n
        ys, xs = np.mgrid[-n:n, -n:n].astype(f32) + 0.5
        # jittered boundaries: warp the lookup with noise (rough, rocky crack lines)
        nz1 = cv2.resize(fbm2((128, 128), 91, 2.2), (2 * n, 2 * n), interpolation=cv2.INTER_CUBIC)
        nz2 = cv2.resize(fbm2((128, 128), 92, 2.2), (2 * n, 2 * n), interpolation=cv2.INTER_CUBIC)
        xw, yw = xs + nz1 * 14, ys + nz2 * 14
        d2 = (xw[..., None] - self.seeds[:, 0]) ** 2 + (yw[..., None] - self.seeds[:, 1]) ** 2
        lab = d2.argmin(-1).astype(np.int32)
        self.lab = lab
        edge = np.zeros(lab.shape, f32)
        edge[:, 1:] += lab[:, 1:] != lab[:, :-1]; edge[1:, :] += lab[1:, :] != lab[:-1, :]
        self.crack = cv2.GaussianBlur(np.clip(edge, 0, 1), (0, 0), 1.2) * 1.6
        self.frag = []
        for k in range(len(seeds)):
            m = (lab == k)
            if not m.any(): continue
            yy_, xx_ = np.nonzero(m)
            y0, y1, x0, x1 = yy_.min(), yy_.max() + 1, xx_.min(), xx_.max() + 1
            mk = m[y0:y1, x0:x1].astype(f32)
            er = cv2.erode(mk, np.ones((5, 5), np.uint8))
            rim = np.clip(mk - er, 0, 1)
            cx, cy = xx_.mean() - n + 0.5, yy_.mean() - n + 0.5
            self.frag.append(dict(k=k, box=(y0, y1, x0, x1), m=cv2.GaussianBlur(mk, (0, 0), 0.6), rim=cv2.GaussianBlur(rim, (0, 0), 1.0),
                                  c=(cx, cy), rnd=r.uniform(-1, 1), spin=r.uniform(-0.25, 0.25)))
        # orbit arc (screen circle through the Moon's centre, rising left -> right)
        C = self.C
        self.A = np.array([C[0] + 330.0, C[1] + 1480.0]); self.Ra = float(np.hypot(*(np.array(C) - self.A)))
        v = np.array(C) - self.A; self.phm = math.atan2(v[1], v[0])
        self.Nv = v / self.Ra                                       # outward normal at the Moon
        self.Tv = np.array([-self.Nv[1], self.Nv[0]])               # tangent (+ = towards the right)
        if self.Tv[0] < 0: self.Tv = -self.Tv
        for f in self.frag:
            o = np.array(f["c"]); f["a"] = float(o @ self.Tv); f["b"] = float(o @ self.Nv)
        # dust: each grain trails a parent fragment
        nd = 16000
        self.dust = dict(p=r.integers(0, len(self.frag), nd), lam=r.uniform(0, 1, nd) ** 0.7, ja=r.normal(0, 1, nd),
                         jb=r.normal(0, 1, nd), sz=r.uniform(0.2, 1.0, nd) ** 2, hue=r.uniform(0, 1, nd), ph=r.uniform(0, 6.28, nd))
        rp = np.convolve(r.standard_normal(4000), np.ones(5) / 5, "same") + 0.6 * np.convolve(r.standard_normal(4000), np.ones(29) / 29, "same") * 3
        self.ring_prof = np.clip(0.75 + 0.45 * rp, 0.05, 1.6).astype(f32)                 # index: (r + 2000) half-res px
        # half-res arc coordinates for the ring band
        dx, dy = self.hx - self.A[0], self.hy - self.A[1]
        self.arc_r = np.sqrt(dx * dx + dy * dy) - self.Ra                       # + outward
        ph = np.arctan2(dy, dx) - self.phm
        ph = (ph + np.pi) % (2 * np.pi) - np.pi
        self.arc_s = ph * self.Ra * self._sgn()                                # along-arc distance (+ along Tv)

    def frag_motion(self, f, tau):
        """fragment centre (screen), rotation (deg), scale at time tau after the break"""
        u = max(tau, 0.0)
        g = u ** 1.55
        R = self.R_big
        da = (f["a"] / R) * 380 * g + (f["b"] / R) * -220 * g + f["rnd"] * 120 * g
        e = ease(u / 2.6)
        b = f["b"] * (1 - 0.72 * e) + f["rnd"] * 18 * e
        a = f["a"] + da
        phi = self.phm + a / self.Ra * self._sgn()
        rr = self.Ra + b
        x = self.A[0] + rr * math.cos(phi); y = self.A[1] + rr * math.sin(phi)
        rot = math.degrees(phi - self.phm) + math.degrees(f["spin"] * u)
        sc = 1 - 0.45 * ease(u / 3.0)
        return x, y, -rot, sc, a, b

    def _sgn(self):
        # +arc_s runs with increasing screen angle (clockwise in y-down) if the tangent points that way
        t_ccw = np.array([-math.sin(self.phm), math.cos(self.phm)])
        return 1.0 if t_ccw @ self.Tv > 0 else -1.0

    def roche(self, img, t, cx, cy, scale, I, es, heat):
        """the Moon at the Roche limit: glowing cracks, then fragments shearing along the orbit"""
        H, W = img.shape[:2]
        n = self.fr_half
        p = self.big.patch(cx, cy, t, I, scale, es)
        x0, x1, y0, y1, rad, cov = p
        # resample the patch onto the fragment grid (centred, same pixel scale)
        g = np.zeros((2 * n, 2 * n, 3), f32); gc = np.zeros((2 * n, 2 * n), f32)
        ox, oy = int(round(cx)) - n, int(round(cy)) - n
        sx0, sy0 = max(x0, ox), max(y0, oy); sx1, sy1 = min(x1, ox + 2 * n), min(y1, oy + 2 * n)
        g[sy0 - oy:sy1 - oy, sx0 - ox:sx1 - ox] = rad[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
        gc[sy0 - oy:sy1 - oy, sx0 - ox:sx1 - ox] = cov[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0]
        tau = t - T_RIP
        hot = np.array([1.0, 0.42, 0.10], f32); white = np.array([1.0, 0.85, 0.60], f32)
        fl = 0.8 + 0.2 * noise1(t, 5, 6.0)
        if tau < 0:                                                         # glowing cracks spreading over the disc
            cr = self.crack * gc
            reach = ramp(t, T_CRACK, T_RIP) * 1.25
            rr = np.sqrt((np.arange(2 * n)[None, :] - n) ** 2 + (np.arange(2 * n)[:, None] - n) ** 2) / self.R_big
            cr = cr * smooth(reach, reach - 0.25, rr)
            glow = cv2.GaussianBlur(cr, (0, 0), 6) * 0.9
            emis = (cr * 3.5 * heat * fl)[..., None] * white + (glow * 2.2 * heat * fl)[..., None] * hot
            g = g * (1 - 0.6 * np.clip(cr * heat, 0, 1))[..., None] + emis
            self._paste(img, g, gc, ox, oy)
            return
        # fragments (each warped into a small destination box)
        heat2 = math.exp(-tau / 1.1) * 1.0 + 0.15
        for f in self.frag:
            fy0, fy1, fx0, fx1 = f["box"]
            m = f["m"] * gc[fy0:fy1, fx0:fx1]
            src = np.concatenate([g[fy0:fy1, fx0:fx1] * f["m"][..., None] + (f["rim"] * heat2 * 2.4 * fl)[..., None] * hot * m[..., None]
                                  , m[..., None]], 2)
            x, y, rot, sc, _, _ = self.frag_motion(f, tau)
            scx, scy = f["c"][0] + n - fx0, f["c"][1] + n - fy0                 # fragment centre in its crop
            hw = max(fx1 - fx0, fy1 - fy0) * sc * 0.75 + 4
            dx0, dy0 = int(x - hw), int(y - hw); dw = int(2 * hw) + 2
            if dx0 > W or dy0 > H or dx0 + dw < 0 or dy0 + dw < 0: continue
            M = cv2.getRotationMatrix2D((scx, scy), rot, sc)
            M[0, 2] += (x - dx0) - scx; M[1, 2] += (y - dy0) - scy
            out = cv2.warpAffine(src, M, (dw, dw), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            a = np.clip(out[..., 3:], 0, 1)
            X0, Y0, X1, Y1 = max(dx0, 0), max(dy0, 0), min(dx0 + dw, W), min(dy0 + dw, H)
            if X1 <= X0 or Y1 <= Y0: continue
            o = out[Y0 - dy0:Y1 - dy0, X0 - dx0:X1 - dx0]; aa = a[Y0 - dy0:Y1 - dy0, X0 - dx0:X1 - dx0]
            img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - aa) + o[..., :3]

    def _paste(self, img, g, gc, ox, oy):
        H, W = img.shape[:2]; n2 = g.shape[0]
        X0, Y0, X1, Y1 = max(ox, 0), max(oy, 0), min(ox + n2, W), min(oy + n2, H)
        gg = g[Y0 - oy:Y1 - oy, X0 - ox:X1 - ox]; cc = gc[Y0 - oy:Y1 - oy, X0 - ox:X1 - ox]
        img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - cc[..., None]) + gg

    def ring_dust(self, t):
        """dust trailing the fragments + the glowing band of the forming ring (half-res layer)"""
        tau = t - T_RIP
        hw, hh = self.L.W // 2, self.L.H // 2
        if tau <= 0: return (np.zeros((hh, hw, 3), f32), np.zeros((hh, hw, 3), f32)), 0.0
        D = self.dust; fr = self.frag
        fa = np.array([self.frag_motion(f, tau)[4] for f in fr]); fb = np.array([self.frag_motion(f, tau)[5] for f in fr])
        a0 = np.array([f["a"] for f in fr])
        p = D["p"]
        a = a0[p] + (fa[p] - a0[p]) * D["lam"] + D["ja"] * (12 + 45 * tau)
        b = fb[p] + D["jb"] * (10 + 30 * min(tau, 2.0))
        phi = self.phm + a / self.Ra * self._sgn()
        rr = self.Ra + b
        x = self.A[0] + rr * np.cos(phi); y = self.A[1] + rr * np.sin(phi)
        lay = np.zeros((hh, hw, 3), f32)
        sel = (x > 0) & (x < self.L.W - 1) & (y > 0) & (y < self.L.H - 1)
        tw = 0.7 + 0.3 * np.sin(t * 9 + D["ph"])
        col = 0.65 + 0.35 * palette(D["hue"] * 0.6 + 0.05 + 0.02 * t)
        v = (D["sz"] * tw * ramp(tau, 0.0, 0.5))[:, None] * col
        np.add.at(lay, ((y[sel] / 2).astype(int), (x[sel] / 2).astype(int)), v[sel].astype(f32))
        lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 2.2 + cv2.GaussianBlur(lay, (0, 0), 3.5) * 1.6 + cv2.GaussianBlur(lay, (0, 0), 12) * 1.2
        # the band: grows along the arc with the spreading fragments, flattens into a ringed sheet
        ext = max(np.abs(fa).max(), 1.0) * 1.05 + 200
        if t > T_RING: ext += (t - T_RING) * 3000
        wdt = 230 * (1 - 0.70 * ease(tau / 2.4)) + 30
        r_ = self.arc_r * 1.0
        along = smooth(ext, ext * 0.55, np.abs(self.arc_s))
        prof = np.exp(-(r_ / wdt) ** 2)
        ri = np.clip((r_ / 2 + 2000).astype(np.int32), 0, 3999)
        rings = self.ring_prof[ri]              # ringlets
        lvl = ramp(tau, 0.1, 1.2) * (0.5 + 0.5 * ramp(t, T_RING - 0.2, T_RING + 0.4))
        hue = palette(self.arc_s / 1600.0 - 0.08 * t + r_ / 900.0)
        edge = np.exp(-((np.abs(r_) - wdt * 0.9) / (wdt * 0.25)) ** 2)                 # prismatic edges
        band = (prof * rings * along * lvl)[..., None] * np.array([1.0, 0.86, 0.66], f32) * 0.55 \
            + (edge * along * lvl * 0.22)[..., None] * hue
        halo = (np.exp(-np.abs(r_) / (wdt * 2.5)) * along * lvl * 0.05)[..., None] * np.array([0.9, 0.75, 1.0], f32)
        return (lay * 0.6 + band + halo, lay * 0.4), lvl

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        cur, t0, t1 = body_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "today" if i == 0 else SWAPS[i - 1][1]
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = BK[prev] if prev else BK[cur]; B = BK[cur]
        if cur == "end": A, w = BK["roche"], 1.0
        return A, B, w, cur, t0, t1

    def pos(self, cur, t):
        if cur != "d20": return self.C
        u = min(max((t - T_RISE0) / (T_RISE1 - T_RISE0), 0), 1)
        u = 1 - (1 - u) ** 1.7
        return (self.RISE0[0] + (self.C[0] - self.RISE0[0]) * u, self.RISE0[1] + (self.C[1] - self.RISE0[1]) * u)

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, cx, cy, col_u, bright, night, skyl, ringl):
        sky = self.blue_sky * (1 - night) + self.night_sky * night + self.moon_sky * skyl * bright
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32)
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - Rp, 0)
        gl = 0.8 + 0.6 * min(skyl, 1.2)
        aure = (np.exp(-dd / (30 + 0.30 * Rp)) * 0.30 + np.exp(-dd / (200 + 0.8 * Rp)) * 0.06) * gl * (0.6 + 0.4 * bright) * (1 - ringl)
        sky = sky + aure[..., None] * gcol
        cor = lerp(A["corona"], B["corona"], w)
        if cor > 0.01:                                                       # iridescent corona (thin cloud)
            x = (d - Rp) / 34.0 - 0.15 * t
            ring = np.exp(-np.maximum(d - Rp, 0) / (85 + Rp)) * smooth(Rp + 6, Rp + 30, d)
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
    def relight(self, A, B, w, light, rise, night):
        fg = self.fg
        amb = np.array([0.22, 0.32, 0.62], f32) * (0.11 * (1 - night) + 0.05 * night)    # skylight: blue hour -> night
        nite = fg.flat * 0.75 + fg.rgb * 0.25
        def one(S):
            g = S["gain"] * (rise if S["key"] == "d20" else 1.0)
            moonc = np.array([0.80, 0.88, 1.08], f32)                       # moonlight: sunlight, slightly blue-shifted by eye
            key = (fg.rgb * 0.55 + fg.flat * 0.45) * moonc * g
            out = nite * amb + key
            rc = np.array(S["glow"], f32)
            out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * rc * (0.04 + g * 0.5) * 0.35
            return out
        fb = one(B)
        fgc = fb if w >= 1 else one(A) * (1 - w) + fb * w
        return fgc * light

    def valley_mist(self, t, a, col, speed, surge):
        """drifting valley haze + tidal 'surges' (bright haze fronts that sweep across the valley floor)"""
        hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.30 + t * 10 * speed) % 512; mv = (sy * 1.1 + t * 3 * speed) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 40, hz + 25, sy) * (1 - smooth(hz + 110, hz + 300 + 120 * surge, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.4 - 0.3, 0, 1), (0, 0), 5)
        out = m * band * a
        if surge > 0:                                                         # fronts sweeping left -> right
            per = 2.6
            ph = ((t * speed * 0.55) % per) / per
            xf = -300 + ph * (self.L.W + 600)
            front = np.exp(-((sx - xf) / 160) ** 2) + 0.6 * np.exp(-((sx - xf + 520) / 260) ** 2)
            out = out + (0.5 + 0.5 * m) * band * front * surge
        return self.up(out)[..., None] * np.array(col, f32)

    def shimmer(self, img, amp, t, mask):
        if amp <= 0: return img
        u = (self.xx * 0.10 + t * 60) % 256; v = (self.yy * 0.10 + t * 37) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = mask * amp
        return cv2.remap(img, (self.xx + n * k).astype(f32), (self.yy + n * k * 0.7).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def lava(self, img, cx, cy, R, t, amt):
        """volcanic hot spots + faint vents on the Moon's night side (tidal heating)"""
        if amt <= 0: return
        for i, (u, v) in enumerate([(-0.82, -0.30), (-0.70, 0.18), (-0.55, -0.66), (-0.90, 0.02), (-0.40, -0.84), (-0.62, 0.55),
                                    (-0.30, -0.92), (-0.85, 0.40)]):
            if night_mask(u, v) < 0.05: continue
            fl = 0.65 + 0.35 * noise1(t, 40 + i, 3.0)
            s = max(R / 380.0, 0.25)
            splat(img, cx + u * R, cy + v * R, 40 * s + 6, lambda d, dx, dy: (np.exp(-d / (1.3 * s + 0.4)) * 3.0 + np.exp(-d / (6 * s + 1)) * 0.35)[..., None]
                  * np.array([1.0, 0.35, 0.06], f32) * fl * amt)

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = BK[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        nxt_k = [k for ts, k in SWAPS if ts > t]
        col_u = 0.0 if (t1 > 1e8 or (nxt_k and nxt_k[0] in ("roche", "end"))) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        scale = g_in
        I_mul = 1 + 0.25 * (pulse - 1)
        if t0 > 0: I_mul *= 0.4 + 0.6 * min(max(u_in * 3, 0), 1)
        if col_u > 0:                                                         # old Moon: swell, then implode to a point
            if col_u < 0.45: scale *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; scale *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        if cur == "roche":                                                    # from 20,000 km: creeps in, no implosion
            scale = (BK["d20"]["Rp"] + (S["Rp"] - BK["d20"]["Rp"]) * ease((t - t0) / 0.7)) / S["Rp"]
        if cur == "d20": scale *= BK["d20"]["Rp"] / self.big.Rp
        cx, cy = self.pos(cur, t)
        Rp = self.big.Rp * scale if cur in ("d20", "roche") else S["Rp"] * scale
        rise = 0.35 + 0.65 * smooth(self.hz + 60, self.C[1] + 120, cy) if cur == "d20" else 1.0
        night = ramp(t, 0.5, T_SW["d50"] + 0.5) * (0.0 if cur == "end" else 1.0) + (ramp(t, T_BACK, T_BACK + 0.01) * 0.0)
        if cur == "end": night = 0.0
        skyl = lerp(A["skyl"], B["skyl"], w) * (rise if cur == "d20" else 1.0)
        ring_img, ringl = (self.ring_dust(t) if cur == "roche" else (None, 0.0))
        skyl = skyl * (1 - 0.45 * ringl) + 0.15 * ringl
        bright = 1 + 0.5 * (pulse - 1)
        sky, bm, aure = self.sky(t, A, B, w, Rp, cx, cy, col_u, bright, night, skyl, ringl)
        if cur == "roche": bm = bm * (1 - 0.5 * ringl)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        sg = math.exp(-2.2 * skyl) * (0.35 + 0.65 * ramp(t, 0.3, T_SW["d100"]) if cur != "end" else 0.5)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.14, star_gain=1.1, cx=2000, cy=900, rot=6.0)
        img += st * (sg * np.exp(-self.up(aure) * 5))[..., None] * 0.9
        # ---- the Moon
        es = lerp(A["es"], B["es"], w) if cur not in ("d20", "roche") else B["es"]
        if cur == "roche":
            heat = ramp(t, T_CRACK - 0.1, T_RIP) * (1 + 0.5 * math.exp(-((t - T_RIP) / 0.15) ** 2))
            img += self.up(ring_img[0])
            self.roche(img, t, cx, cy, scale, I_mul, es, heat)
            img += self.up(ring_img[1])
            if t < T_RIP + 0.4: self.lava(img, cx, cy, Rp, t, 1.0 - ramp(t, T_RIP, T_RIP + 0.4))
        else:
            bd = self.moon[cur]
            bd.render(img, cx, cy, t, I=I_mul, scale=scale, es=es, ext=self.ext)
            if cur in ("d50", "d20"):
                self.lava(img, cx, cy, Rp, t, ramp(t, wt("d50_b", "VOLCANOES") - 0.2, wt("d50_b", "VOLCANOES") + 0.4) * (1 - col_u) * (0.7 + 0.3 * pulse))
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        if cur == "roche": light *= 1 + 0.4 * ringl + 0.4 * math.exp(-max(t - T_RIP, 0) / 0.5) * (t > T_RIP)
        fgc = self.relight(A, B, w, light, rise, night)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        lc = np.array(lerp(A["glow"], B["glow"], w), f32)
        tide = math.log10(max(lerp(A["tide"], B["tide"], w), 1.0))           # 0 .. 4
        mist_a = 0.05 + 0.04 * tide + 0.12 * lerp(A["gain"], B["gain"], w) * rise
        surge = 0.0 if cur in ("today", "end") else min(0.15 + 0.22 * tide, 1.0)
        fgc = fgc + self.valley_mist(t, mist_a, lc * 0.6, 1 + 0.6 * tide, surge * mist_a * 2.2) * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ground tremble (tides / quakes): a shimmer of the plate, strongest on the quake beats
        trem = 0.0 if cur in ("today", "end", "d200", "d100") else {"d50": 0.8, "d20": 1.4, "roche": 2.0}[cur]
        trem += sum(2.5 * s * math.exp(-max(t - tq, -0.05) / 0.45) * (t > tq - 0.05) for tq, s in QUAKES)
        if trem > 0.05 and cur not in ("today", "end"): img = self.shimmer(img, trem, t, fg.a)
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                if k == "end": continue                                       # the white-out does this one
                NS = BK[k]
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(NS["glow"])
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                pcx, pcy = self.pos(k, ts + 0.01)
                self.shock(img, pcx, pcy, u, fc)
        if cur == "roche":
            for tb, size, fc in ((T_RIP, 1.3, np.array([1.0, 0.6, 0.3], f32)), (T_RING, 1.6, np.array([0.8, 0.7, 1.0], f32))):
                u = t - tb
                if -0.05 < u < 1.4:
                    img += (2.2 * math.exp(-max(u, 0) / 0.10) * ease((u + 0.05) / 0.05)) * fc
                    self.shock(img, cx, cy, u, fc, size=size)
        # ---- final white-out -> today's Moon
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([0.95, 0.95, 1.0], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.95, 0.95, 1.0], f32)
            self.shock(img, cx, cy, t - T_BACK, np.array([0.8, 0.85, 1.0], f32))
        img = self.chroma_bloom(img, 1.0)
        expo = 1.0 / (1 + 0.25 * min(skyl, 1.5))                              # the camera stops down as the night brightens
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
        x, ys = W / 2, (1215, 1297, 1352, 1402)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "end": a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "roche": a *= 1 - ramp(t, T_WO0 - 0.3, T_WO0)
        if a > 0.01:
            dy = (1 - a) * 18
            rgba, _ = word_layer(S["name"], int(L.hud_size * 1.45), W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.06, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.56), "Black", (255, 226, 150) if cur != "end" else (255, 255, 255), a, 0.06, display=True)
            if S["l4"]: hud_text(out, S["l4"], x, ys[3] + dy, int(L.hud_size * 0.46), "Bold", (190, 230, 255), a, 0.08, display=True)
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
        print("DUR", DUR, "roche km", round(ROCHE_KM))
        for s in STAGES:
            print(f"{s['key']:6s} d={s['d']:9,.0f}  Rp={s['Rp']:6.1f}px  {s['ang']:.3f}deg  x{s['x']:.2f}  tides x{s['tide']:.1f}  "
                  f"moonlight x{s['M']:.0f}  | {s['name']} | {s['l2']} | {s['l3']} | {s['l4']}")
        print({k: round(v, 2) for k, v in T_SW.items()}, "crack", round(T_CRACK, 2), "rip", round(T_RIP, 2), "ring", round(T_RING, 2),
              "wo", round(T_WO0, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch([tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(st)
