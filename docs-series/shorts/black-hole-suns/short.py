"""WHAT IF BLACK HOLES REPLACED OUR SUN? -- one locked tripod shot of the park (A_park), "swap" format (like ../other-suns).
The Sun is swapped, one after another, for black holes placed at 1 au, seen through a ~90 deg vertical-FOV lens
(f = 960 px, level camera, principal point on the horizon row). Every black hole is ray traced in exact Schwarzschild
geometry (lens.py) at its true size, and the park is relit by its light.
  Sun -> 1-Sun-mass hole (invisible, dark sky, pointer ring on the 1.4' lensing ring) -> Cygnus X-1 (+ blue supergiant
  companion, accretion stream, glowing disk point) -> Sgr A* (24 deg shadow, EHT-orange ring, lensed sky)
  -> M87* (we are inside the horizon: lensed tunnel) -> TON 618 (giant hole, quasar disk, swallows the view)
  -> white-out -> Sun (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert                 full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5         stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2   re-render only those time ranges
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.sky import StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
import lens

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-black-hole-suns"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A_park.png"
LAMPS = [(630, 1185, 1336), (845, 1095, 1342)]       # A_park lamp (head x, head y, pole base y) in SOURCE px (as in other-suns)
FPS = 30
LEAD, TAIL = 0.25, 1.00
F_PX = 960.0
RSUN_AU = 0.00465047

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ physics (README)
# Rs = 2GM/c^2 = 2.953 km per solar mass. 1 au = 1.496e8 km. Observer radius r_obs = 1 au / Rs.
RS_KM = 2.9533
AU_KM = 1.495978707e8
def r_obs_of(M): return AU_KM / (RS_KM * M)
R_SGR = r_obs_of(4.297e6)                             # 11.79 Rs -> shadow 24.3 deg across (Synge, static observer)
COMP_R = 22.3                                         # HDE 226868 radius [R_sun] (Miller-Jones et al. 2021) -> 11.9 deg
COMP_T = 31000.0

def rad_px(R):
    x = R * RSUN_AU
    return F_PX * math.tan(math.asin(min(x, 0.999)))


# ------------------------------------------------------------------------------------------------ scenes
# zen/hor: atmosphere colours (linear); beams: list of colours or "rainbow"; bI beam intensity; fg grade: gain, tint,
# flat (shadow flattening), amb (ambient from the sky colour), night (0..1 blend to the night grade), lamps; fc flash colour
SC = [
    dict(key="sun", name="THE SUN", l2="1× SUN'S MASS", l3="NO HORIZON · 1.4 MILLION KM WIDE", tc=(255, 236, 170),
         zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), beams="rainbow", bI=1.0, gain=1.0, tint=(1.0, 0.98, 0.95),
         flat=0.0, amb=0.10, night=0.0, lamps=0.0, expo=1.0, fc=(1.0, 0.95, 0.85)),
    dict(key="one", name="1-SUN-MASS BLACK HOLE", l2="1× SUN'S MASS", l3="HORIZON: 3 KM RADIUS", tc=(200, 215, 255),
         zen=(0.010, 0.014, 0.085), hor=(0.030, 0.050, 0.21), beams=[(0.35, 0.25, 1.0), (0.55, 0.30, 1.0), (0.25, 0.5, 1.0)], bI=0.10,
         gain=0.0, tint=(1, 1, 1), flat=1.0, amb=0.0, night=1.0, lamps=1.0, expo=1.15, fc=(0.75, 0.70, 1.0)),
    dict(key="cyg", name="CYGNUS X-1", l2="21× SUN'S MASS", l3="HORIZON: 62 KM RADIUS", l4="1 YEAR → 11 WEEKS", tc=(150, 200, 255),
         zen=(0.04, 0.17, 1.05), hor=(0.62, 0.85, 1.45), beams=[(0.3, 0.7, 1.0), (0.75, 0.4, 1.0), (0.85, 0.95, 1.0), (0.2, 1.0, 0.95)], bI=1.3,
         gain=1.75, tint=(0.70, 0.88, 1.35), flat=0.05, amb=0.15, night=0.0, lamps=0.0, expo=0.95, fc=(0.7, 0.85, 1.0)),
    dict(key="sgr", name="SAGITTARIUS A*", l2="4.3 MILLION × SUN'S MASS", l3="HORIZON: 12.7 MILLION KM RADIUS", l4="SHADOW: 24° ACROSS", tc=(255, 160, 70),
         zen=(0.040, 0.016, 0.050), hor=(0.36, 0.13, 0.05), beams=[(1.0, 0.45, 0.06), (1.0, 0.20, 0.10), (1.0, 0.70, 0.20), (0.9, 0.2, 0.5)], bI=0.75,
         gain=0.55, tint=(1.0, 0.50, 0.17), flat=0.45, amb=0.30, night=0.25, lamps=0.6, expo=1.05, fc=(1.0, 0.6, 0.25)),
    dict(key="m87", name="M87*", l2="6.5 BILLION × SUN'S MASS", l3="HORIZON: 128 AU RADIUS", l4="WE'RE INSIDE IT", tc=(215, 140, 255),
         zen=(0.05, 0.010, 0.13), hor=(0.30, 0.05, 0.42), beams=[(0.7, 0.2, 1.0), (0.3, 0.6, 1.0), (1.0, 0.2, 0.8), (0.5, 0.3, 1.0)], bI=0.9,
         gain=0.50, tint=(0.62, 0.32, 1.0), flat=0.5, amb=0.35, night=0.3, lamps=0.5, expo=1.05, fc=(0.8, 0.5, 1.0)),
    dict(key="ton", name="TON 618", l2="40–66 BILLION × SUN'S MASS", l3="HORIZON: 800–1,300 AU RADIUS", tc=(255, 200, 110),
         zen=(0.12, 0.06, 0.06), hor=(0.95, 0.55, 0.25), beams=[(1.0, 0.75, 0.35), (1.0, 0.95, 0.75), (1.0, 0.45, 0.12), (0.9, 0.55, 0.9)], bI=1.1,
         gain=1.15, tint=(1.0, 0.72, 0.42), flat=0.25, amb=0.25, night=0.0, lamps=0.0, expo=0.85, fc=(1.0, 0.85, 0.6)),
]
SK = {s["key"]: s for s in SC}

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {k: LN[k]["start"] - 0.06 for k in ("one", "cyg", "sgr", "m87", "ton")}
T_SUNBACK = LN["end"]["start"] - 0.10
T_WO0 = T_SUNBACK - 0.80
T_SWAL = wt("ton", "SWALLOW") - 0.1
ORDER = ["sun", "one", "cyg", "sgr", "m87", "ton"]
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "sun2")]
PULSES = [wt("hook", "REPLACED"), wt("one", "6 KM"), wt("one", "DARK"), wt("cyg", "21"), wt("cyg", "WEEKS"), wt("sgr", "4 MILLION"),
          wt("sgr", "24°"), wt("m87", "6.5 BILLION"), wt("m87", "NEPTUNE"), wt("m87", "INSIDE"), wt("ton", "66 BILLION"), wt("end", "KIND")]
M87_R0, M87_R1 = 1.06, 1.004                           # tunnel: camera radius (Rs) at the start / end of the M87* beat
TON_R = 9.0                                            # TON 618 view: camera at 6 Rs (snapshot; the real 1 au is inside)


def scene_at(t):
    cur, t0 = "sun", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("sun" if k == "sun2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def prev_of(t0):
    for i, (ts, k) in enumerate(SWAPS):
        if ts == t0: return "sun" if i == 0 else ("sun" if SWAPS[i - 1][1] == "sun2" else SWAPS[i - 1][1])
    return None


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


# ------------------------------------------------------------------------------------------------ helpers
_T = np.linspace(1000, 40000, 1024)
BB_LUT = np.stack([bbcolor(x) for x in _T]).astype(f32)
def bb_vec(T):
    i = np.clip((T - 1000) / (40000 - 1000) * 1023, 0, 1023).astype(np.int32); return BB_LUT[i]


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def afmhot(x):
    x = np.clip(x, 0, 1.6)
    return np.stack([np.clip(2 * x, 0, 1.6), np.clip(2 * x - 0.5, 0, 1.4), np.clip(2 * x - 1.0, 0, 1.2)], -1).astype(f32) ** 2.2


def rotm(axis, ang):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def align(u, v):
    """rotation taking unit u to unit v"""
    u = np.asarray(u, float) / np.linalg.norm(u); v = np.asarray(v, float) / np.linalg.norm(v)
    ax = np.cross(u, v); s = np.linalg.norm(ax)
    if s < 1e-9: return np.eye(3)
    return rotm(ax, math.atan2(s, float(u @ v)))


def splat_pts(H, W, x, y, val):
    acc = np.zeros((H + 2, W + 2, 3), f32)
    ok = (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
    x, y, val = x[ok], y[ok], val[ok]
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); ux = (x - x0)[:, None]; uy = (y - y0)[:, None]
    for dy, dx, wg in ((0, 0, (1 - ux) * (1 - uy)), (0, 1, ux * (1 - uy)), (1, 0, (1 - ux) * uy), (1, 1, ux * uy)):
        np.add.at(acc, (np.clip(y0 + dy, 0, H + 1), np.clip(x0 + dx, 0, W + 1)), (val * wg).astype(f32))
    return acc[:H, :W]


class Cells:
    """animated Worley cells on the unit sphere (granulation of the supergiant) -- from ../other-suns"""
    def __init__(self, n, seed):
        r = np.random.default_rng(seed); p = r.standard_normal((n, 3)); self.p0 = p / np.linalg.norm(p, axis=1, keepdims=True)
        self.w = r.uniform(0.3, 1.0, (n, 3)); self.ph = r.uniform(0, 6.283, (n, 3))
        self.br = r.uniform(0.55, 1.35, n).astype(f32); self.bph = r.uniform(0, 6.283, n); self.bw = r.uniform(0.6, 1.6, n)
        self.cell = math.sqrt(4 * math.pi / n)

    def eval(self, v, t, speed=1.0, lw=0.22):
        p = self.p0 + 0.30 * self.cell * np.sin(speed * t * self.w + self.ph)
        p /= np.linalg.norm(p, axis=1, keepdims=True)
        d, i = cKDTree(p).query(v, k=2, workers=2)
        lane = smooth(0.0, lw * self.cell, d[:, 1] - d[:, 0]).astype(f32)
        b = self.br[i[:, 0]] * (1 + 0.28 * np.sin(1.7 * speed * t * self.bw[i[:, 0]] + self.bph[i[:, 0]]))
        core = np.clip(1.15 - 0.6 * (d[:, 0] / self.cell) ** 2, 0.4, 1.2)
        return lane, (b * core).astype(f32)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True, f_px=F_PX, C=None):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.f = f_px
        self.fg = fg = Foreground(FG_PATH, L, lamps=LAMPS, hz_frac=0.68)
        self.hz = float(fg.horizon)
        self.py = 900.0 if vertical else 480.0                              # principal point row (camera tilted ~25 deg up)
        self.C = C or ((540.0, 600.0) if vertical else (1200.0, 330.0))
        self.Hs = min(H, int(self.hz + 60) // 2 * 2)                       # sky rows computed
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        # half-res grid (gradients, beams)
        hw, hh = W // 2, H // 2
        hy, hx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = hx, hy
        self.dx = hx - self.C[0]; self.dy = hy - self.C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        el = np.clip((self.hz - hy) / self.hz, 0, 1)
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        # camera rays (full res, sky rows) and the direction of the hole
        self.dirs = self.ray(xx[:self.Hs], yy[:self.Hs]).reshape(-1, 3)
        self.dirs_h = self.ray(hx[:self.Hs // 2], hy[:self.Hs // 2]).reshape(-1, 3)
        self.Fd = self.ray(np.array(self.C[0] - 0.5, f32), np.array(self.C[1] - 0.5, f32)).reshape(3)
        # star sky (procedural plate of ../lib/sky.py used as an equirectangular celestial sphere)
        ss = StarSky()
        self.plate = ss.plate.astype(f32) * 1.0
        self.PW, self.PH = self.plate.shape[1], self.plate.shape[0]
        pv = self.plate_vec(ss.bx, ss.by); self.bvec, self.bflux, self.bcol = pv, ss.bf * 1.0, ss.bc * 1.0
        self.bph = np.random.default_rng(43).uniform(0, 1000, len(ss.bx)).astype(f32)
        p0 = self.plate_vec(np.array([self.PW * 0.535]), np.array([self.PH * 0.42]))[0]           # Milky Way core region
        self.Rb = align(p0, self.Fd) @ rotm(p0, math.radians(30))
        self.sky_axis = np.array([-0.35, -0.85, 0.40])                                                # "celestial pole"
        # beams
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # textures
        dt = fbm2((256, 1024), 31, 2.6) * 0.45 + fbm2((256, 1024), 32, 1.8) * 0.20
        self.disk_tex = np.clip(cv2.GaussianBlur(dt, (0, 0), sigmaX=1.2, sigmaY=4.0) * 1.6 + 0.85, 0.12, 2.2).astype(f32)
        self.swirl = np.clip(fbm2((256, 512), 77, 2.2) * 0.5 + 0.5, 0, 1.5).astype(f32)
        self.cells = (Cells(40, 101), Cells(1200, 201))
        self.prom = [fbm2((8, 1024), 61 + i, 1.6)[0] for i in range(2)]
        # foreground prep
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        f = fg.flat; y = lum(f)[..., None]
        self.fg_night = ((f * 0.35 + y * 0.65) * np.array([0.19, 0.22, 0.48], f32)).astype(f32)
        emph = {"SMALL", "6 KM", "DARK", "FOREVER", "21", "WEEKS", "4 MILLION", "24°", "6.5 BILLION", "NEPTUNE", "INSIDE",
                "66 BILLION", "SWALLOW", "KIND", "X-1", "A*", "M87*", "TON 618"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010 if vertical else 590
        self._views = {}

    # -------------------------------------------------------------------------------------------- geometry
    def ray(self, x, y):
        v = np.stack([(x + 0.5 - self.L.W / 2) / self.f, (y + 0.5 - self.py) / self.f, np.ones_like(x)], -1)
        return (v / np.linalg.norm(v, axis=-1, keepdims=True)).astype(f32)

    def proj(self, d):
        """unit directions (N, 3) -> pixel x, y (front hemisphere only)"""
        z = np.maximum(d[:, 2], 1e-4)
        return d[:, 0] / z * self.f + self.L.W / 2 - 0.5, d[:, 1] / z * self.f + self.py - 0.5, d[:, 2] > 0.05

    def plate_vec(self, x, y):
        lon = (x / self.PW - 0.5) * 2 * np.pi; lat = (0.5 - y / self.PH) * np.pi
        return np.stack([np.cos(lat) * np.sin(lon), -np.sin(lat), np.cos(lat) * np.cos(lon)], -1)

    def sky_rot(self, t):
        return rotm(self.sky_axis, math.radians(1.6) * t) @ self.Rb             # plate -> world

    def disk_normal(self, F, incl, roll):
        F = np.asarray(F, float); X = -F
        up = np.array([0.0, -1.0, 0.0]); U = up - (up @ X) * X; U /= np.linalg.norm(U)
        n = math.cos(math.radians(incl)) * X + math.sin(math.radians(incl)) * U
        return (rotm(X, math.radians(roll)) @ n).astype(f32)

    # -------------------------------------------------------------------------------------------- star sky
    def plate_sample(self, dirs, t, shape):
        R = self.sky_rot(t)
        p = dirs @ R.astype(f32)                                                 # world -> plate (R^T d)
        lon = np.arctan2(p[:, 0], p[:, 2]); lat = np.arcsin(np.clip(-p[:, 1], -1, 1))
        u = ((lon / (2 * np.pi) + 0.5) * self.PW).astype(f32).reshape(shape); v = ((0.5 - lat / np.pi) * self.PH).astype(f32).reshape(shape)
        return cv2.remap(self.plate, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def bright_stars(self, t, view=None, gain=1.0, bl=1.0):
        """bright stars as point sources; with a view: every lensed image (orders 1-3) with its magnification"""
        W, Hs = self.L.W, self.Hs
        s = (self.bvec @ self.sky_rot(t).T).astype(f32)
        fl = self.bflux * (1 + 0.25 * np.sin(t * 9.1 + self.bph) * np.sin(t * 5.3 + self.bph * 1.7))
        if view is None:
            x, y, ok = self.proj(s); val = (fl[:, None] * self.bcol)[ok]
            acc = splat_pts(Hs, W, x[ok], y[ok], val)
        else:
            tr, F = view["tr"], view["F"]
            cb = np.clip(s @ F, -1, 1); beta = np.arccos(cb)
            Ts = s - cb[:, None] * F[None]; Ts /= np.maximum(np.linalg.norm(Ts, axis=1, keepdims=True), 1e-7)
            al, ask = view["al"], view["ask"]; da = view["dadsky"]
            xs, ys, vs = [], [], []
            for target, sgn in ((beta, 1), (-beta, -1), (beta - 2 * np.pi, 1), (-beta - 2 * np.pi, -1)):
                ok = (target >= ask[0]) & (target <= ask[-1])
                a = np.interp(target, ask, al); mu = np.abs(np.sin(a) / np.maximum(np.abs(np.sin(beta)), 1e-4) * np.interp(target, ask, da))
                mu = np.minimum(mu, 60.0)
                d = np.cos(a)[:, None] * F[None] + np.sin(a)[:, None] * Ts * sgn
                x, y, ok2 = self.proj(d.astype(f32)); ok &= ok2
                xs.append(x[ok]); ys.append(y[ok]); vs.append((fl * mu)[ok, None] * self.bcol[ok])
            acc = splat_pts(Hs, W, np.concatenate(xs), np.concatenate(ys), np.concatenate(vs))
        st = cv2.GaussianBlur(acc, (0, 0), 0.65) * 2.6
        big = acc * (acc.max(2, keepdims=True) > 2.0)
        st += (cv2.GaussianBlur(big, (0, 0), 1.6) * 1.6 + cv2.GaussianBlur(big, (0, 0), 5.0) * 1.2) * bl
        return st * gain

    # -------------------------------------------------------------------------------------------- black-hole views
    def get_view(self, key, r_obs=None, half=False):
        ck = (key, r_obs, half)
        if ck in self._views: return self._views[ck]
        if key == "sgr": r, incl, roll, rin, rout, F = R_SGR, 32.0, -14.0, 1.6, 4.6, self.Fd
        elif key == "ton": r, incl, roll, rin, rout, F = TON_R, 84.0, -9.0, 3.0, 6.5, self.Fd
        else: r, incl, roll, rin, rout, F = r_obs, 70.0, 20.0, 2.2, 12.0, -self.Fd              # m87: looking outward
        dirs = self.dirs_h if half else self.dirs
        amax = math.radians(80) if key != "m87" else math.pi - 1e-3
        tr = lens.Tracer(r, a_max=amax, n=1800 if half else 2600, dphi=0.005 if half else 0.004)
        n = self.disk_normal(F, incl, roll)
        V = lens.View(tr, dirs, F, n, rin, rout, kmax=3)
        e = tr.esc; al = tr.alpha[e]; ask = tr.alpha_sky[e]; o = np.argsort(ask); al, ask = al[o], ask[o]
        da = np.gradient(al, ask) if len(al) > 2 else np.ones_like(al)
        v = dict(tr=tr, V=V, F=np.asarray(F, f32), al=al, ask=ask, dadsky=np.abs(da), rin=rin, rout=rout,
                 shape=((self.Hs // 2, self.L.W // 2) if half else (self.Hs, self.L.W)), ac=tr.alpha_c)
        if key != "m87" or not half: self._views[ck] = v
        return v

    def disk_layers(self, v, t, mode, I0=1.0):
        """front-to-back composite of the disk crossings -> (emission HxWx3, transmission HxW)"""
        V = v["V"]; h, w = v["shape"]; N = h * w; rin, rout = v["rin"], v["rout"]
        em = np.zeros((N, 3), f32); tr = np.ones(N, f32)
        for hit in V.hits:                                            # k = 0, 1, 2 (nearest first)
            sel, r, psi, g = hit["sel"], hit["r"], hit["psi"], hit["g"]
            om = 0.55 * (np.maximum(r, rin) / rin) ** -1.5
            u = (((psi - om * t * (1 if mode != "m87" else 2.5)) / (2 * np.pi)) % 1.0) * 1024
            vv = np.clip((r - rin) / (rout - rin), 0, 1) * 255
            tex = map_tex(self.disk_tex, u, vv)
            if mode == "sgr":
                prof = (rin / r) ** 2.0 * smooth(rin, rin + 0.6, r) * smooth(rout, rout - 1.6, r)
                I = prof * tex * np.clip(g, 0.05, 3) ** 2.2
                col = afmhot(I * 0.6) * 2.6
                a = np.clip(prof * tex * 0.7, 0, 0.85)
            elif mode == "ton":
                Fr = (r ** -3) * (1 - np.sqrt(3.0 / np.maximum(r, 3.0))); Fr = Fr / 0.00366
                prof = np.clip(Fr, 0, 1.2) * smooth(rout, rout - 0.6, r) * smooth(rin, rin + 0.12, r)
                Tm = 9000.0 * np.maximum(prof, 0.02) ** 0.25 * g
                col = bb_vec(Tm) * (0.55 + 0.45 * np.array([1.0, 0.85, 0.65], f32))
                I = (0.15 + prof) * tex * np.clip(g, 0.05, 3) ** 3 * 1.3
                col = col * I[:, None]
                a = np.clip((0.35 + prof) * tex * 0.9, 0, 0.97)
            else:                                                     # m87 tunnel rings
                prof = (rin / r) ** 1.5 * smooth(rin, rin + 0.5, r) * smooth(rout, rout - 4, r)
                x = (0.78 + 0.25 * np.log(np.clip(g, 0.05, 20)) + 0.1 * tex) % 1.0
                col = pal_list([(0.75, 0.25, 1.0), (1.0, 0.25, 0.75), (0.35, 0.55, 1.0), (1.0, 0.6, 0.9)], x) * (prof * tex * np.clip(g, 0.1, 6) ** 2 * 2.5)[:, None]
                a = np.clip(prof * tex * 0.6, 0, 0.8)
            em[sel] += tr[sel, None] * a[:, None] * col * I0
            tr[sel] *= 1 - a
        return em.reshape(h, w, 3), tr.reshape(h, w)

    def bh_sky(self, key, t, r_obs=None):
        """lensed sky + disk for sgr / ton (full res) and m87 (half res, per-frame camera radius)"""
        half = key == "m87"
        v = self.get_view(key, r_obs, half)
        h, w = v["shape"]; V = v["V"]
        sky = self.plate_sample(V.sky_dir, t, (h, w)) * V.esc.reshape(h, w)[..., None]
        sky = sky * (0.55 if key != "m87" else 1.0)
        if not half:
            sky += self.bright_stars(t, v, gain=0.9)
        em, trn = self.disk_layers(v, t, key)
        out = em + sky * trn[..., None]
        if key == "sgr":                                               # EHT-like softness on the emission, keep a sharp core
            out = out * 0.6 + cv2.GaussianBlur(out, (0, 0), 3.5) * 0.55
        return out, v

    # -------------------------------------------------------------------------------------------- sky helpers
    def atmos(self, A, B, w):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        return zen * (1 - self.k_hor) + hor * self.k_hor

    def beams_layer(self, t, S, R0, twist=0.0, I=1.0):
        if S["bI"] <= 0: return 0.0
        phi = self.phi + twist * np.log(self.d / 30.0)
        spin = 0.06 * t
        reach = 1500 + 1.2 * R0
        dd = np.maximum(self.d - R0, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        acc = np.zeros(self.dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"])) * (1 + 0.6 * min(R0, 400) / 400)
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            Ib = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.32) % 1.0 if b["rainbow"] else np.full(dp.shape, b["hue"], f32)
            c = palette(x) if S["beams"] == "rainbow" else pal_list(S["beams"], x)
            acc += c * (g * Ib)[..., None]
        return acc * rad[..., None] * 0.38 * S["bI"] * I

    def up(self, a, H=None):
        return cv2.resize(a, (self.L.W, H or self.L.H), interpolation=cv2.INTER_LINEAR)

    def place_sky(self, img, sky):
        """add a full-res sky-rows layer (Hs x W) into the full frame"""
        img[:self.Hs] += sky

    # -------------------------------------------------------------------------------------------- stars (discs)
    def sun_disc(self, img, t, I=1.0, Rp=None):
        cx, cy = self.C; Rp = Rp or rad_px(1.0); sc = bbcolor(5772)
        def fn(d, dx, dy):
            mu = np.sqrt(np.clip(1 - (d / Rp) ** 2, 0, 1)); inside = smooth(Rp + 0.9, Rp - 0.9, d)
            v = (inside * (1 - 0.6 * (1 - mu)) * 40.0)[..., None] * (0.25 + 0.75 * sc)
            dd = np.maximum(d - Rp, 0)
            g = (np.exp(-dd / 3.3) * 2.2 + np.exp(-dd / 23.6) * 0.55 + np.exp(-dd / 94.0) * 0.12) * (d > Rp - 1)
            v += (g * (1 + 0.08 * math.sin(t * 2.3)))[..., None] * (0.3 + 0.7 * sc)
            for k in range(6):
                a = k * math.pi / 3 + 0.26 + 0.03 * math.sin(t * 0.5)
                al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
                base = np.exp(-pp / 1.65) * (al > Rp * 0.8)
                for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                    v[..., c] += base * np.exp(-np.maximum(al - Rp, 0) / (143 * Lk)) * 2.2 * 0.6 * (0.52 + 0.48 * sc[c])
            return v * I
        splat(img, cx, cy, 700, fn)

    def companion(self, img, t, P, I=1.0):
        """HDE 226868, the blue supergiant feeding Cygnus X-1: limb-darkened disc with granulation, prominences, glow"""
        cx, cy = P; Rp = rad_px(COMP_R); H, W = img.shape[:2]; sc = bbcolor(COMP_T)
        pad = Rp * 1.6 + 300
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; ang = np.arctan2(dy, dx); reg = img[y0:y1, x0:x1]
        # tidal distortion: elongated towards the hole (it fills its Roche lobe)
        tid = 1 + 0.06 * np.cos(ang - self.comp_ang) ** 2 + 0.02 * math.sin(t * 1.3)
        Re = Rp * tid
        m = d < Re + 2; ys, xs = np.nonzero(m[::2, ::2])
        small = np.zeros(m[::2, ::2].shape + (3,), f32)
        if len(ys):
            px = dx[::2, ::2][ys, xs] / Re[::2, ::2][ys, xs]; py = dy[::2, ::2][ys, xs] / Re[::2, ::2][ys, xs]
            mu = np.sqrt(np.clip(1 - px * px - py * py, 0, 1)); v = np.stack([px, py, mu], -1)
            c, s_ = math.cos(0.05 * t), math.sin(0.05 * t); v = np.stack([v[:, 0] * c + v[:, 2] * s_, v[:, 1], -v[:, 0] * s_ + v[:, 2] * c], -1)
            lb, bb = self.cells[0].eval(v, t, 0.9, 0.55); lf, bf = self.cells[1].eval(v, t, 1.4, 0.45)
            tex = (0.6 + 0.4 * lb) * (1 + (bb - 1) * 0.5) * (0.8 + 0.2 * lf * bf)
            ld = (1 - 0.45 * (1 - mu))
            Tl = COMP_T * (0.85 + 0.17 * np.clip(tex, 0, 1.3))
            small[ys, xs] = bb_vec(Tl) * (tex * ld)[:, None] * 6.0 * I
        surf = cv2.resize(small, (d.shape[1], d.shape[0]), interpolation=cv2.INTER_LINEAR)
        edge = smooth(Re + 1.0, Re - 1.0, d)
        reg *= (1 - edge)[..., None]; reg += surf * edge[..., None]
        th = (ang / (2 * np.pi) + 0.5) * 1024
        n1 = np.interp((th + t * 9) % 1024, np.arange(1024), self.prom[0]); n2 = np.interp((th * 3 - t * 23) % 1024, np.arange(1024), self.prom[1])
        hgt = Rp * (0.010 + 0.06 * np.clip(n1 * 0.7 + n2 * 0.5, 0, None) ** 1.6) + 2
        reg += (np.exp(-(d - Re) / hgt) * (d > Re))[..., None] * (0.5 + 0.5 * sc) * 3.0 * I
        dd = np.maximum(d - Re, 0)
        g = (np.exp(-dd / (0.06 * Rp + 3)) * 2.2 + np.exp(-dd / (0.35 * Rp + 22)) * 0.6 + np.exp(-dd / (Rp + 90)) * 0.15) * (d > Re - 1)
        reg += (g * 1.8 * I)[..., None] * (0.3 + 0.7 * sc)
        for k in range(6):
            a = k * math.pi / 3 + 0.26 + 0.03 * math.sin(t * 0.5)
            al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
            base = np.exp(-pp / (1.6 + 0.012 * Rp)) * (al > Re * 0.8)
            for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                reg[..., c] += base * np.exp(-np.maximum(al - Rp, 0) / ((140 + 0.6 * Rp) * Lk)) * 1.2 * I * (0.5 + 0.5 * sc[c])
        img[y0:y1, x0:x1] = reg

    def stream(self, img, t, P, I=1.0):
        """accretion stream from the supergiant's inner (L1) point spiralling into the small disk round Cygnus X-1"""
        cx, cy = self.C; px, py = P; Rp = rad_px(COMP_R)
        ang0 = self.comp_ang + math.pi                                     # from the star towards the hole
        L1 = np.array([px + math.cos(ang0) * Rp * 1.02, py + math.sin(ang0) * Rp * 1.02])
        Dv = np.array([cx, cy]) - L1; dist = np.linalg.norm(Dv)
        s = np.linspace(0, 1, 900)
        # Bezier-like curve with a swing (Coriolis) then a final quarter-turn into the disk
        nrm = np.array([-Dv[1], Dv[0]]) / dist
        pts = L1[None] + Dv[None] * (s ** 0.9)[:, None] + nrm[None] * (np.sin(np.pi * s) * dist * 0.28 * (1 - s) ** 0.3)[:, None]
        acc = np.zeros((self.Hs, self.L.W), f32)
        flow = 0.55 + 0.45 * np.sin(s * 38 - t * 9.0) * np.sin(s * 11 - t * 4.1)
        wv = 1.2 + 4.5 * (1 - s) ** 1.5
        val = flow * (0.4 + 1.2 * s ** 2)
        xi = np.clip(pts[:, 0], 0, self.L.W - 1); yi = np.clip(pts[:, 1], 0, self.Hs - 1)
        np.add.at(acc, (yi.astype(int), xi.astype(int)), val * 0.6)
        lay = cv2.GaussianBlur(acc, (0, 0), 2.2) * 6 + cv2.GaussianBlur(acc, (0, 0), 7) * 6 + cv2.GaussianBlur(acc, (0, 0), 18) * 4
        col = np.array([0.55, 0.75, 1.0], f32)
        img[:self.Hs] += lay[..., None] * col * I

    def disk_point(self, img, t, I=1.0):
        """the glowing accretion disk of Cygnus X-1: a few px at 1 au -- tilted ellipse, Doppler-bright side, hot core"""
        cx, cy = self.C
        def fn(d, dx, dy):
            a = math.radians(-12); xr = dx * math.cos(a) + dy * math.sin(a); yr = -dx * math.sin(a) + dy * math.cos(a)
            e = np.sqrt(xr ** 2 + (yr / 0.32) ** 2)
            ring = np.exp(-((e - 5.0) / 2.6) ** 2) * (1.0 + 0.8 * np.clip(-xr / 7, -1, 1)) * (1 + 0.2 * math.sin(t * 6))
            core = np.exp(-(d / 1.6) ** 2) * 14
            glow = np.exp(-d / 9) * 1.4 + np.exp(-d / 40) * 0.25
            return (ring * 9)[..., None] * np.array([0.85, 0.9, 1.0], f32) + (core + glow)[..., None] * np.array([0.8, 0.88, 1.0], f32)
        splat(img, cx, cy, 260, lambda d, dx, dy: fn(d, dx, dy) * I)

    # -------------------------------------------------------------------------------------------- tunnel (inside M87*)
    def tunnel(self, t, k_in):
        u = min(max((t - T_SW["m87"]) / (T_SW["ton"] - T_SW["m87"]), 0), 1)
        r_obs = M87_R0 * (M87_R1 / M87_R0) ** (ease(u) * 0.75 + 0.25 * u)
        layer, v = self.bh_sky("m87", t, r_obs)
        h, w = v["shape"]
        lay = self.up(layer, self.Hs)
        lay *= np.array([0.85, 0.95, 1.35], f32) * (1.0 / math.sqrt(max(1 - 1 / max(r_obs, 1.0001), 1e-3))) ** 0.5   # blueshifted window
        # warped walls: spiralling violet streaks + rings rushing outward around the window (artistic)
        ac = v["ac"]; win = self.f * math.tan(min(math.pi - ac, 1.45))
        d = self.d[:self.Hs // 2]; ph = self.phi[:self.Hs // 2]
        ld = np.log(np.maximum(d, 1.0) / max(win, 20.0))
        uu = ((ph / (2 * np.pi) + 0.25 * ld - 0.07 * t) % 1.0) * 512; vv = ((ld * 60 - t * 90) % 256)
        sw = cv2.remap(self.swirl, uu.astype(f32), vv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        rings = 0.5 + 0.5 * np.sin(ld * 14 - t * 7.5)
        wall = (np.clip(sw * 1.4 - 0.25, 0, 2) ** 1.5 * (0.5 + 0.9 * rings ** 3)) * np.exp(-np.maximum(ld, 0) * 0.7) * smooth(-0.05, 0.15, ld) * 1.6
        col = pal_list([(0.55, 0.15, 1.0), (1.0, 0.2, 0.75), (0.25, 0.45, 1.0), (0.8, 0.3, 1.0)], (0.12 * ld + 0.05 * t + ph / (2 * np.pi)) % 1.0)
        walls = self.up(wall[..., None] * col * 0.55, self.Hs)
        rim = self.up((np.exp(-np.abs(d - win) / (6 + 0.03 * win)) * 2.2)[..., None] * np.array([0.9, 0.75, 1.0], f32), self.Hs)
        return (lay + walls + rim) * k_in, win

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, A, B, w, light, extra=0.0):
        fg = self.fg
        def one(S):
            if S["night"] >= 1: return self.fg_night * 1.0
            base = fg.rgb * (1 - S["flat"]) + fg.flat * S["flat"]
            tint = np.array(S["tint"], f32)
            sky_amb = (np.array(S["zen"], f32) * 0.5 + np.array(S["hor"], f32) * 0.5)
            out = base * tint * S["gain"] + fg.flat * sky_amb * S["amb"]
            out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * tint * S["gain"] * 0.6 * fg.flat.mean()
            if S["night"] > 0: out = out * (1 - S["night"]) + self.fg_night * S["night"] + out * S["night"] * 0.6
            return out
        fa = one(A) if w < 1 else None
        fb = one(B)
        fgc = fb if fa is None else fa * (1 - w) + fb * w
        return fgc * light

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t, overlay=True):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        cur, t0, t1 = scene_at(t)
        prev = prev_of(t0)
        w = ramp(t, t0 - 0.10, t0 + 0.55) if prev else 1.0
        A = SK[prev] if prev else SK[cur]; B = SK[cur]; S = B
        pulse = 1 + 0.08 * math.sin(2 * math.pi * t / 1.6) + sum(0.55 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = min(max((t - t0) / 0.6, 0.0), 1.0) if t0 > 0 else 1.0
        g_in = 1 - (1 - u_in) ** 3
        pre = 1 + 2.0 * ramp(t, t1 - 0.35, t1) if t1 < 1e8 else 1.0           # anticipation before each swap
        atm = self.atmos(A, B, w)
        img = self.up(atm)
        R0 = 0.0; twist = 0.0; light = 1.0
        if cur == "sun":
            self.sun_disc(img, t, pulse * pre * g_in)
            R0 = 4.4
        elif cur == "one":
            sky = self.plate_sample(self.dirs, t, (self.Hs, W)) * 0.55 + self.bright_stars(t, None, 1.0)
            self.place_sky(img, sky * g_in)
            R0 = 30.0
        elif cur == "cyg":
            P = (self.C[0] + 205.0, self.C[1] - 120.0) if L.vertical else (self.C[0] + 230.0, self.C[1] - 60.0)
            self.comp_ang = math.atan2(self.C[1] - P[1], self.C[0] - P[0]) + math.pi
            sky = self.plate_sample(self.dirs, t, (self.Hs, W)) * 0.25
            self.place_sky(img, sky)
            self.companion(img, t, P, pulse * pre * (0.3 + 0.7 * g_in))
            self.stream(img, t, P, pulse * g_in)
            self.disk_point(img, t, pulse * pre * g_in)
            R0 = rad_px(COMP_R)
        elif cur in ("sgr", "ton"):
            lay, v = self.bh_sky(cur, t)
            k = pulse * pre * (0.25 + 0.75 * g_in)
            if cur == "ton" and t > T_SWAL:                                      # falling in: the shadow swallows the view
                z = math.exp(math.log(7.0) * ease((t - T_SWAL) / (T_SUNBACK - T_SWAL)) ** 1.4)
                M = cv2.getRotationMatrix2D(self.C, 25 * ease((t - T_SWAL) / (T_SUNBACK - T_SWAL)), z)
                lay = cv2.warpAffine(lay, M, (W, self.Hs), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            self.place_sky(img, lay * k)
            R0 = self.f * math.tan(v["ac"]) * 0.98
        elif cur == "m87":
            lay, win = self.tunnel(t, pulse * pre * (0.3 + 0.7 * g_in))
            self.place_sky(img, lay)
            R0 = min(win, 900.0); twist = 1.8
        swal = ramp(t, T_SWAL, T_SUNBACK - 0.3) if cur == "ton" else 0.0
        bm = self.beams_layer(t, S, R0, twist, pulse * pre * g_in * (1 - 0.8 * swal))
        if not isinstance(bm, float):
            bmu = self.up(bm)
            if cur in ("sgr", "ton"): bmu[:self.Hs] *= self.cmask(cur)[..., None]
            img += bmu
        # ---- foreground
        light = 1.0 + 0.12 * (pulse - 1)
        fgc = self.relight(A, B, w, light * (1 - 0.6 * swal))
        if not isinstance(bm, float): fgc = fgc + bmu * 0.05 * fg.a[..., None]
        lamp_on = lerp(A["lamps"], B["lamps"], w)
        if lamp_on > 0: fgc = fg.lamps_light(fgc, lamp_on * 2.2, t)
        if cur == "ton":
            fgc = fgc * (1 - 0.6 * swal) + fg.flat * np.array([0.10, 0.03, 0.16], f32) * swal
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.12 < u < 1.4:
                NS = SK["sun" if k == "sun2" else k]; fc = np.array(NS["fc"], f32)
                img += (3.2 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.12) / 0.12)) * fc
                if u > 0:
                    R = 2400 * (u / 1.4) ** 0.6; wdt = 18 + 60 * u
                    dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                    for ch, off in ((0, 10), (1, 0), (2, -10)):
                        img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-u / 0.55)
        if T_WO0 < t < T_SUNBACK:
            v_ = ease((t - T_WO0) / (T_SUNBACK - T_WO0))
            dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
            Rw = 40 + 2600 * v_ ** 1.5
            img += (np.exp(-np.maximum(dd - Rw, 0) / (100 + 500 * v_)) * (2 + 25 * v_))[..., None] * np.array([1.0, 0.9, 0.95], f32)
            img += (30 * v_ ** 2.5) * np.array([1.0, 0.94, 0.88], f32)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, lerp(A["expo"], B["expo"], w))
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        if overlay: self.overlay(out, t, cur, t0)
        return out

    def cmask(self, key):
        """1 outside the shadow, 0 inside (half-res) so the beams start at the shadow edge"""
        k = ("cm", key)
        if k not in self._views:
            v = self.get_view(key); R = self.f * math.tan(v["ac"])
            self._views[k] = smooth(R * 0.98, R * 1.25, self.d[:self.Hs // 2]).astype(f32)
        return self.up(self._views[k], self.Hs)

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

    def pointer(self, out, t, x, y, R, label, a, col=(255, 255, 255), below=0):
        """thin rotating dashed ring + label (drawn on the sRGB frame)"""
        if a <= 0.01: return
        H, W = out.shape[:2]
        x0, x1, y0, y1 = max(0, int(x - R - 8)), min(W, int(x + R + 8)), max(0, int(y - R - 8)), min(H, int(y + R + 8))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - x; dy = self.yy[y0:y1, x0:x1] + 0.5 - y
        d = np.sqrt(dx * dx + dy * dy); ang = np.arctan2(dy, dx)
        Rr = R * (1 + 0.05 * math.sin(t * 4))
        dash = (np.sin(ang * 12 + t * 2.0) > -0.2).astype(f32)
        m = np.clip(1.8 - np.abs(d - Rr), 0, 1) * dash
        for k in range(4):                                                         # ticks pointing inward
            aa = k * math.pi / 2 + t * 0.5
            al = dx * math.cos(aa) + dy * math.sin(aa); pp = np.abs(-dx * math.sin(aa) + dy * math.cos(aa))
            m = np.maximum(m, np.clip(1.6 - pp, 0, 1) * (al > Rr * 1.12) * (al < Rr * 1.12 + 16))
        m = (m * a)[..., None]
        out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - m) + np.array(col, f32) / 255 * m
        if label: hud_text(out, label, x, y + (Rr + 40) * below - (Rr + 34) * (1 - below), int(self.L.hud_size * 0.42), "Bold", col, a, 0.14, display=True)

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W
        S = SK[cur]
        if L.vertical: x, ys = W / 2, (1205, 1290, 1350, 1408)
        else: x, ys = 470, (800, 875, 930, 980)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "sun" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.9, T_SUNBACK + 1.2)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if cur == "ton": a *= 1 - ramp(t, T_SWAL + 0.6, T_SWAL + 1.0)
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(S["name"]) < 12 else 1.05))
            rgba, _ = word_layer(S["name"], big, W * 0.92 if L.vertical else 820, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.60), "Black", (255, 255, 255), a, 0.06, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (235, 240, 250), a, 0.08, display=True)
            if S.get("l4"):
                a4 = a * (ramp(t, wt("cyg", "YEAR") - 0.2, wt("cyg", "YEAR") + 0.1) if cur == "cyg" else 1.0)
                hud_text(out, S["l4"], x, ys[3] + dy, int(L.hud_size * 0.46), "Black", S["tc"], a4, 0.08, display=True)
        if cur == "one":
            ap = ramp(t, T_SW["one"] + 0.5, T_SW["one"] + 0.9) * (1 - ramp(t, T_SW["cyg"] - 0.3, T_SW["cyg"] - 0.1))
            self.pointer(out, t, self.C[0], self.C[1], 40, "LENSING RING · 1.4′ WIDE", ap, (210, 220, 255))
        if cur == "cyg":
            ap = ramp(t, T_SW["cyg"] + 0.5, T_SW["cyg"] + 0.9) * (1 - ramp(t, T_SW["sgr"] - 0.3, T_SW["sgr"] - 0.1))
            self.pointer(out, t, self.C[0], self.C[1], 34, "BLACK HOLE + DISK", ap, (200, 230, 255), below=1)
        self.caps.draw(out, t)


def map_tex(tex, u, v):
    """bilinear wrap-around lookup of a 2-D texture at (u, v) (any length)"""
    h, w = tex.shape
    x0 = np.floor(u).astype(np.int64); y0 = np.floor(v).astype(np.int64); fx = (u - x0).astype(f32); fy = (v - y0).astype(f32)
    x0 %= w; y0 %= h; x1 = (x0 + 1) % w; y1 = (y0 + 1) % h
    return (tex[y0, x0] * (1 - fx) * (1 - fy) + tex[y0, x1] * fx * (1 - fy) + tex[y1, x0] * (1 - fx) * fy + tex[y1, x1] * fx * fy).astype(f32)


def save_png(im, path):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            save_png(im, os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
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
        print("DUR", DUR, "r_sgr", round(R_SGR, 3), "shadow deg", round(2 * math.degrees(lens.alpha_shadow(R_SGR)), 2),
              "shadow px", round(F_PX * math.tan(lens.alpha_shadow(R_SGR)), 1), "comp px", round(rad_px(COMP_R), 1))
        print({k: round(v, 2) for k, v in T_SW.items()}, "swal", round(T_SWAL, 2), "sunback", round(T_SUNBACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
