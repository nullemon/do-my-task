"""WHAT IF EARTH WERE SOMEWHERE ELSE IN THE GALAXY? -- one LOCKED shot of the user's mountain observatory
(07_mountain_observatory.png) at night; the sky swaps between Earth's possible "addresses", each with a flash, a
chromatic shockwave that reveals the new sky inside its ring, coloured light beams, a relit summit and a readout.
  today  the real sky: HYG v4.1 stars (V < 6.5) at 34 deg N + the vivid Milky Way band (star-dates mwsky.py)
  gc     inside the galaxy's nuclear star cluster, 1 pc (3.3 ly) from Sgr A* (star-clusters population synthesis:
         ~1.5 million stars within 3 ly; ~12,700 brighter than Sirius; total starlight ~20 full Moons)
  arm    inside a giant star-forming region of a spiral arm (Carina-like): pink H-alpha clouds, dust pillars, young
         blue O/B clusters
  halo   30,000 ly above the galactic centre: the whole face-on Milky Way (NASA/JPL-Caltech/R. Hurt PIA10748),
         projected physically (R = h tan theta), ~118 deg across
  void   the Bootes Void: no stars, a faint airglow, six faint galaxies
  -> white-out -> today (loops)
The sky turns about the real pole all the time (a stylised time-lapse, re-based under the white-out so it loops).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py stills 1.0,9.5       -> SCR/stills/<t>.png
  /home/user/ttsenv/bin/python short.py seg                  restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place
from skygeo import eq_vec, eq2hor, hdir, Lens, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-galaxy-address"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/07_mountain_observatory.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
FL, ALT0 = 540.0, 60.0                    # stereographic lens: f (px), centre altitude (deg), facing south
H_LY = 30000.0                            # height above the galactic centre in the halo scene
MW_LY = 120000.0                          # width of the PIA10748 image in light-years (disc ~100,000 ly)
P_PL = 2048; PPD_PL = P_PL / 2 / 110.0    # plate frame (prep.py)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for l in PL if l["key"].startswith(key) for w in l["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ timeline
T_SW = dict(gc=wt("gc", "GALACTIC") - 0.12, arm=wt("arm", "STELLAR") - 0.12, halo=wt("halo", "RISE") - 0.12,
            void=wt("void", "BOÖTES") - 0.12)
T_BACK = LN["end"]["start"] + 0.02                   # white-out peak -> today again
T_WO0 = T_BACK - 0.80
SWAPS = [(T_SW[k], k) for k in ("gc", "arm", "halo", "void")] + [(T_BACK, "today")]
PULSES = [wt("gc", "MILLIONS"), wt("gc", "DARK"), wt("arm", "GLOWING"), wt("arm", "BLUE"), wt("halo", "30,000"),
          wt("halo", "WHOLE"), wt("halo", "HANGS"), wt("void", "NO"), wt("void", "FAINT"), wt("end", "SEAT")]
T_VOIDGAL = wt("void", "FAINT")
REVEAL = 1.15
L0, LRATE = 19.30, 0.050                             # sidereal time (h) at t = 0, stylised time-lapse rate (h/s)
def LST(t): return L0 + LRATE * (t if t < T_BACK else t - DUR - 1 / FPS)


def scene_at(t):
    cur, t0, prev = "today", -10.0, "today"
    for i, (ts, k) in enumerate(SWAPS):
        if t >= ts: cur, t0, prev = k, ts, (SWAPS[i - 1][1] if i > 0 else "today")
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


def t_mid(key):
    if key == "today": return 0.0
    i = [k for _, k in SWAPS].index(key); return (SWAPS[i][0] + SWAPS[i + 1][0]) / 2


# ------------------------------------------------------------------------------------------------ scenes
# az/alt: the direction of the scene's centre (core / plate centre) at mid-scene; zen/hor: night-sky gradient (linear);
# lc / I: light cast on the summit; beams: palette of the light rays; expo: tone-map exposure
SC = {
    "today": dict(name="HOME · THE ORION SPUR", tc=(170, 205, 255), l=["26,000 LY FROM THE GALACTIC CENTRE", "~5,000 STARS VISIBLE BY EYE", "THE MILKY WAY: A FAINT BAND"],
                  az=180, alt=40, zen=(0.010, 0.011, 0.070), hor=(0.034, 0.046, 0.185), lc=(0.55, 0.65, 1.0), I=0.10,
                  beams=[(0.45, 0.65, 1.0), (0.8, 0.6, 1.0)], bI=0.0, expo=1.15),
    "gc": dict(name="GALACTIC CENTRE", tc=(255, 215, 140), l=["~1.5 MILLION STARS WITHIN 3 LY", "~12,700 OUTSHINE SIRIUS", "NIGHT SKY ≈ 20 FULL MOONS"],
               az=185, alt=47, zen=(0.050, 0.032, 0.045), hor=(0.20, 0.12, 0.09), lc=(1.0, 0.80, 0.52), I=1.0,
               beams=[(1.0, 0.85, 0.5), (0.5, 0.75, 1.0), (1.0, 0.45, 0.75), (1.0, 0.65, 0.2)], bI=1.0, expo=0.55),
    "arm": dict(name="INSIDE A STELLAR NURSERY", tc=(255, 140, 200), l=["A SPIRAL ARM · LIKE THE CARINA NEBULA", "~250 LY OF GLOWING GAS", "STARS ONLY A FEW MILLION YEARS OLD"],
                az=178, alt=50, zen=(0.012, 0.004, 0.030), hor=(0.05, 0.015, 0.06), lc=(1.0, 0.48, 0.78), I=0.55,
                beams=[(1.0, 0.35, 0.65), (0.35, 0.85, 1.0), (1.0, 0.6, 0.85), (0.6, 0.5, 1.0)], bI=0.5, expo=0.95),
    "halo": dict(name="ABOVE THE GALACTIC DISK", tc=(185, 215, 255), l=["30,000 LY UP", "THE DISK SPANS ~120° OF SKY", "100,000 LY ACROSS"],
                 az=180, alt=70, zen=(0.008, 0.010, 0.060), hor=(0.030, 0.040, 0.150), lc=(0.85, 0.85, 1.0), I=0.55,
                 beams=[(0.6, 0.75, 1.0), (1.0, 0.85, 0.6), (0.8, 0.6, 1.0), (0.4, 0.9, 1.0)], bI=0.7, expo=0.95),
    "void": dict(name="THE BOÖTES VOID", tc=(150, 230, 210), l=["~330 MILLION LY ACROSS", "~60 GALAXIES KNOWN INSIDE", "NAKED-EYE STARS: 0"],
                 az=180, alt=50, zen=(0.0035, 0.0050, 0.020), hor=(0.010, 0.024, 0.040), lc=(0.40, 0.60, 0.65), I=0.035,
                 beams=[(0.3, 0.8, 0.7), (0.4, 0.5, 1.0)], bI=0.10, expo=1.35),
}
VOIDGAL = [(0.22, 0.07, 0, 24, 0.9), (0.78, 0.29, 1, 16, 0.7), (0.60, 0.40, 2, 20, 0.6), (0.27, 0.62, 3, 14, 0.5),
           (0.84, 0.60, 4, 18, 0.5), (0.45, 0.13, 5, 12, 0.45)]          # (x/W, y/H, sprite, size px, gain)


def back_out(u, s=2.0):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return a + (b - a) * w


def pal_list(cols, x):
    C = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def rot_to(target):
    """3x3 R with R @ (0,0,1) = target (unit)"""
    z = target / np.linalg.norm(target)
    a = np.array([0.0, 0.0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    x = np.cross(a, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.stack([x, y, z], 1)


def bv_temp(ci): return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


_T = np.linspace(1500, 45000, 1024)
BB = np.stack([bbcolor(x) for x in _T]).astype(f32)
def star_rgb(T, sat=1.7):
    c = BB[np.clip(((np.asarray(T) - 1500) / (45000 - 1500) * 1023).astype(np.int32), 0, 1023)]
    y = c @ np.array([0.2126, 0.7152, 0.0722], f32)
    c = y[:, None] + (c - y[:, None]) * sat
    c = np.clip(c, 0.02, None); c /= (c @ np.array([0.2126, 0.7152, 0.0722], f32))[:, None]
    return c.astype(f32)


def disp_flux(V): return (4.0 * 10 ** (-0.4 * 0.80 * V)).astype(f32)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.97)
        self.hz = float(fg.horizon)
        self.lens = Lens(W, H, 180.0, ALT0, FL, self.hz + 10)
        L.cap_y = 1010
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        hy, hx = np.mgrid[0:H // 2, 0:W // 2].astype(f32) * 2 + 1.0; self.hx, self.hy = hx, hy
        self.rays = self.lens.rays(1); self.rays_h = self.lens.rays(2)
        alt = np.arcsin(np.clip(self.rays[..., 2], -1, 1)).astype(f32); self.alt = alt
        self.e = e = np.clip(alt / (np.pi / 2), 0, 1)
        self.above = smooth(-0.01, 0.04, alt).astype(f32)[..., None]
        self.nz = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.nights = {k: self.night_grad(S) for k, S in SC.items()}
        self.airgrad = (0.35 + 0.65 * np.exp(-e / 0.35)).astype(f32)
        # airglow (void): brightest ~10-15 deg up (van Rhijn), green 557.7 nm low, faint red above
        altd = np.degrees(alt)
        ag = np.exp(-((altd - 12) / 10) ** 2) * (1 + 0.25 * cv2.resize(fbm2((64, 64), 77, 2.5), (W, H), interpolation=cv2.INTER_CUBIC))
        self.airglow = (ag[..., None] * np.array([0.010, 0.030, 0.016], f32) + np.exp(-((altd - 35) / 18) ** 2)[..., None] * np.array([0.010, 0.004, 0.006], f32)).astype(f32)
        # ---- data
        self.mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        z = np.load(os.path.join(SCR, "stars.npz"))
        keep = z["mag"] < 6.5
        self.ph_rng = np.random.default_rng(3)
        self.sets = {}
        self.sets["today"] = self.mkset(eq_vec(z["ra"][keep], z["dec"][keep]), z["mag"][keep],
                                        star_rgb(np.clip(bv_temp(np.clip(z["ci"][keep], -0.4, 2.0)), 2600, 30000)))
        pl = np.load(os.path.join(SCR, "plates.npz"))
        self.mwimg = pl["mw"].astype(f32); self.neb = pl["neb"].astype(f32); self.voidspr = pl["void"]
        self.ns = {k: pl["ns_" + k] for k in ("th", "ph", "V", "T")}
        self.cent = {k: eq2hor(LST(t_mid(k))).T @ hdir(SC[k]["az"], SC[k]["alt"]) for k in SC}      # scene centres (eq frame)
        self.Rc = {k: rot_to(self.cent[k]) for k in SC}
        self.load_gc(); self.load_arm(); self.load_halo()
        self._dn = (fbm2((512, 512), 91, 2.8), fbm2((512, 512), 92, 2.2))
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 9 + r.uniform(-0.2, 0.2), w=r.uniform(0.10, 0.20), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(9)]
        # ---- summit: night base, lit albedo, rim; sky-facing factor
        a = fg.a; self.a = a[..., None]
        f = fg.flat; y = lum(f)[..., None]
        self.base = ((f * 0.35 + y * 0.65) * np.array([0.30, 0.36, 0.75], f32) * 0.10).astype(f32)
        self.alb = np.clip(f * 0.8 + y * 0.2, 0, 1).astype(f32)
        sk = np.clip((self.hz + 150 - yy) / (self.hz + 150 - fg.skyline.min()), 0, 1)
        self.skyfac = (0.40 + 0.60 * sk)[..., None].astype(f32)
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a)[..., None].astype(f32)
        emph = {"IMAGINE", "EARTH", "ADDRESS", "GALACTIC", "CENTRE.", "MILLIONS", "DARK", "NURSERY", "GLOWING", "BLUE", "RISE",
                "30,000", "WHOLE", "MILKY", "HANGS", "BOÖTES", "VOID", "NO", "FAINT", "HOME", "SEAT", "NEVER", "GALAXIES"}
        self.caps = Captions(L, WORDS, emphasis=emph)

    def night_grad(self, S):
        e = self.e; k = np.exp(-e / 0.30)[..., None]
        n = np.array(S["zen"], f32) * (1 - k) + np.array(S["hor"], f32) * k
        n = n + np.exp(-((e - 0.45) / 0.22) ** 2)[..., None] * np.array(S["zen"], f32) * np.array([0.6, 0.15, 0.4], f32)
        return (n * (1 + 0.06 * self.nz)[..., None]).astype(f32)

    def mkset(self, d, V, col):
        V = np.asarray(V, f32); o = np.argsort(V)
        return dict(d=np.asarray(d, np.float64)[o], V=V[o], col=col[o], fd=disp_flux(V[o]), ph=self.ph_rng.uniform(0, 1000, len(V)).astype(f32))

    # -------------------------------------------------------------------------------------------- data per scene
    def load_gc(self):
        z = np.load(os.path.join(SCR, "cl_nsc.npz"))
        R = self.Rc["gc"]; sel = z["V"] < -0.8
        self.sets["gc"] = self.mkset(z["dirs"][sel].astype(np.float64) @ R.T, z["V"][sel], star_rgb(z["T"][sel]))
        fm = z["faint"].astype(f32); MH, MW_ = fm.shape
        u = z["dirs"][~sel]; fl = 10 ** (-0.4 * z["V"][~sel].astype(np.float64))
        ra = np.degrees(np.arctan2(u[:, 1], u[:, 0])) % 360.0; dec = np.degrees(np.arcsin(np.clip(u[:, 2], -1, 1)))
        xi = np.clip((ra / 360 * MW_).astype(int), 0, MW_ - 1); yi = np.clip(((90 - dec) / 180 * MH).astype(int), 0, MH - 1)
        pix_sr = (2 * np.pi / MW_) * (np.pi / MH) * np.cos(np.radians(90 - (yi + 0.5) / MH * 180))
        fm += np.bincount(yi * MW_ + xi, weights=fl / pix_sr, minlength=MH * MW_).reshape(MH, MW_).astype(f32)
        self.gc_faint = cv2.GaussianBlur(fm, (0, 0), 3.5)
        print("gc points", len(self.sets["gc"]["V"]))

    def load_arm(self):
        th, ph = np.radians(self.ns["th"].astype(np.float64)), self.ns["ph"].astype(np.float64)
        loc = np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], 1)
        self.sets["arm"] = self.mkset(loc @ self.Rc["arm"].T, self.ns["V"], star_rgb(self.ns["T"]))

    def load_halo(self):
        r = np.random.default_rng(17); n = 140
        d = r.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        V = r.uniform(2.5, 6.5, n); T = np.where(r.uniform(0, 1, n) < 0.8, r.uniform(3800, 5200, n), r.uniform(6000, 9000, n))   # old halo giants
        self.sets["halo"] = self.mkset(d, V, star_rgb(T))
        # globular clusters: fuzzy balls (local frame offsets in degrees around the galaxy direction, spread over the sky)
        self.globs = [(r.uniform(-75, 75), r.uniform(-75, 75), r.uniform(0.25, 0.6)) for _ in range(14)]

    # -------------------------------------------------------------------------------------------- geometry
    def M(self, lst): return eq2hor(lst)                                     # eq -> horizon

    def proj(self, d, lst):
        h = d @ self.M(lst).T; x, y, ok = self.lens.project(h); return x, y, ok, h[..., 2]

    def local(self, key, lst, half=False):
        """theta (deg), phi of every pixel in scene `key`'s local frame"""
        K = (self.M(lst) @ self.Rc[key]).astype(f32)
        g = (self.rays_h if half else self.rays) @ K
        th = np.degrees(np.arccos(np.clip(g[..., 2], -1, 1))); ph = np.arctan2(g[..., 1], g[..., 0])
        return th.astype(f32), ph.astype(f32)

    def screen_of(self, key, lst):
        x, y, ok, z = self.proj(self.cent[key][None], lst); return float(x[0]), float(y[0])

    # -------------------------------------------------------------------------------------------- stars
    def stars_layer(self, s, t, lst, gain=1.0, spark=1.0, hp=0.85, pop=1.0, ng=28, gth=6.0, gpop=None):
        gpop = pop if gpop is None else gpop
        L = self.L; W, H = L.W, L.H
        h = s["d"] @ self.M(lst).T
        vis = np.where(h[:, 2] > -0.01)[0]; h = h[vis]
        x, y, ok = self.lens.project(h)
        sel = ok & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
        idx = vis[sel]; x = x[sel]; y = y[sel]; zz = h[sel, 2]
        ph = s["ph"][idx]
        nt = np.sin(t * 13.1 + ph) * 0.5 + np.sin(t * 23.7 + ph * 1.7) * 0.3 + np.sin(t * 37.3 + ph * 2.3) * 0.2
        sig = np.clip(0.10 + 0.35 * np.exp(-zz / 0.15), 0.08, 0.6) * spark
        tw = np.exp(sig * nt * 1.6 - 0.5 * sig * sig)
        ext = np.clip(zz / 0.12, 0, 1) ** 0.7
        fd = s["fd"][idx] * tw * ext * gain
        core = np.minimum(fd, 5.0); col = s["col"][idx]
        acc = np.zeros(((H + 2) * (W + 2), 3), f32)
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = x - x0; fy = y - y0
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            li = np.clip(y0 + dy, 0, H + 1) * (W + 2) + np.clip(x0 + dx, 0, W + 1); w_ = core * wg
            for c in range(3): acc[:, c] += np.bincount(li, weights=w_ * col[:, c], minlength=(H + 2) * (W + 2)).astype(f32)
        acc = acc.reshape(H + 2, W + 2, 3)[:H, :W]
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = fd > 2.0
        if big.any():
            q = 4; hq, wq = H // q, W // q
            hb = np.zeros((hq * wq, 3), f32)
            xi = np.clip((x[big] / q).astype(np.int64), 0, wq - 1); yi = np.clip((y[big] / q).astype(np.int64), 0, hq - 1)
            ex = (fd[big] - 1.2) ** hp * pop
            for c in range(3): hb[:, c] = np.bincount(yi * wq + xi, weights=ex * col[big, c], minlength=hq * wq)
            hb = hb.reshape(hq, wq, 3)
            halo = cv2.GaussianBlur(hb, (0, 0), 0.8) * 0.30 + cv2.GaussianBlur(hb, (0, 0), 2.5) * 0.050 + cv2.GaussianBlur(hb, (0, 0), 8.0) * 0.008
            st += cv2.resize(halo, (W, H), interpolation=cv2.INTER_LINEAR)
        for j in list(np.argsort(-fd)[:ng]):
            g = fd[j]
            if g < gth: continue
            c = col[j] * 0.85 + 0.15
            Lk = min((6 + 7 * math.log(g / 6 + 1) ** 1.2) * gpop ** 0.5, 46.0)
            a = min(g, 150.0) ** 0.8 * 0.06 * gpop * (1 + 0.25 * math.sin(t * 5 + ph[j]))
            splat(st, x[j], y[j], int(Lk * 4) + 6, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / Lk) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / Lk)) * a)[..., None] * c)
        return st

    # -------------------------------------------------------------------------------------------- skies
    def sky_today(self, t, lst):
        Mg = EQ2GAL @ self.M(lst).T
        g = self.rays_h @ Mg.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        mw = cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        sky = self.nights["today"] + self.up(mw) * 5.0
        return sky + self.stars_layer(self.sets["today"], t, lst)

    def dust(self, cx, cy, t):
        n1, n2 = self._dn
        a = math.radians(-22); x = self.hx - cx; y = self.hy - cy
        u = x * math.cos(a) + y * math.sin(a); v = -x * math.sin(a) + y * math.cos(a)
        mu = ((u * 0.45 + t * 3.0) % 512).astype(f32); mv = ((v * 0.45) % 512).astype(f32)
        w1 = cv2.remap(n1, mu, mv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        w2 = cv2.remap(n2, mu, ((v * 0.9) % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        vv = v + 70 * w1
        lanes = (np.exp(-((vv - 40) / 55) ** 2) * 1.0 + np.exp(-((vv + 170) / 35) ** 2) * 0.8
                 + np.exp(-((vv - 290) / 40) ** 2) * 0.7) * np.clip(0.55 + 0.45 * w2, 0, 1)
        lanes += np.clip(w2 - 0.9, 0, 1) * 0.5 * np.exp(-np.abs(v) / 500)
        return np.clip(1 - 0.93 * lanes, 0.05, 1).astype(f32)

    def sky_gc(self, t, lst):
        W, H = self.L.W, self.L.H
        Kq = (self.M(lst) @ self.Rc["gc"]).astype(f32)
        g = self.rays_h @ Kq                                                  # cluster frame of clusters.py (core = +z)
        MH, MW_ = self.gc_faint.shape
        ra = np.degrees(np.arctan2(g[..., 1], g[..., 0])) % 360.0; dec = np.degrees(np.arcsin(np.clip(g[..., 2], -1, 1)))
        fl = cv2.remap(self.gc_faint, (ra / 360 * MW_ - 0.5).astype(f32), ((90 - dec) / 180 * MH - 0.5).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        half = ((np.maximum(fl, 0) / 100.0) ** 0.6 * 0.05 * 0.55)[..., None] * np.array([1.0, 0.60, 0.30], f32)
        cx, cy = self.screen_of("gc", lst)
        tr = self.dust(cx, cy, t)
        sky = self.nights["gc"] + (self.airgrad * 0.45 * 0.05)[..., None] * np.array([0.75, 0.55, 0.55], f32)
        sky = sky + self.up(half * tr[..., None])
        st = self.stars_layer(self.sets["gc"], t, lst, spark=0.9, hp=0.30, pop=1.0, ng=70, gth=12.0, gpop=2.2)
        return sky + st * self.up(np.maximum(tr, 0.35))[..., None]

    def sky_arm(self, t, lst):
        th, ph = self.local("arm", lst)
        u = P_PL / 2 + th * PPD_PL * np.cos(ph); v = P_PL / 2 + th * PPD_PL * np.sin(ph)
        neb = cv2.remap(self.neb, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        y = lum(neb)[..., None]; neb = np.maximum(y + (neb - y) * 1.25, 0)
        sky = self.nights["arm"] + neb * 3.2 + (self.airgrad * 0.012)[..., None] * np.array([0.8, 0.4, 0.7], f32)
        return sky + self.stars_layer(self.sets["arm"], t, lst, hp=0.6, ng=40, gth=8.0, gpop=1.6)

    def sky_halo(self, t, lst):
        th, ph = self.local("halo", lst)
        thr = np.radians(np.minimum(th, 89.0))
        R = H_LY * np.tan(thr)                                               # ly from the galactic centre in the disk
        k = self.mwimg.shape[0] / MW_LY
        rot = math.radians(28.0) + 0.012 * t                                 # a slow, stylised turn
        u = self.mwimg.shape[1] / 2 + R * k * np.cos(ph + rot); v = self.mwimg.shape[0] / 2 + R * k * np.sin(ph + rot)
        gal = cv2.remap(self.mwimg, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        path = np.minimum(1.0 / np.maximum(np.cos(thr), 1e-3), 3.0) ** 0.5 * smooth(89, 80, th)   # optically thin disk: brighter when seen obliquely
        sky = self.nights["halo"] + gal * (path * 0.55)[..., None]
        # faint glow of the stellar halo around the disk
        sky += (np.exp(-th / 55.0) * 0.010)[..., None] * np.array([0.8, 0.75, 1.0], f32)
        st = self.stars_layer(self.sets["halo"], t, lst)
        for gx, gy, gs in self.globs:                                        # globular clusters
            thg = math.hypot(gx, gy); phg = math.atan2(gy, gx)
            loc = np.array([math.sin(math.radians(thg)) * math.cos(phg), math.sin(math.radians(thg)) * math.sin(phg), math.cos(math.radians(thg))])
            x, y_, ok, z = self.proj((self.Rc["halo"] @ loc)[None], lst)
            if ok[0] and z[0] > 0.03 and 0 < x[0] < self.L.W and 0 < y_[0] < self.L.H:
                splat(st, x[0], y_[0], 18, lambda d, dx, dy: (np.exp(-d / (1.6 * gs + 0.6)) * 0.35 * gs)[..., None] * np.array([1.0, 0.88, 0.7], f32))
        return sky + st

    def sky_void(self, t, lst):
        W, H = self.L.W, self.L.H
        sky = self.nights["void"] + self.airglow * (1 + 0.08 * math.sin(t * 0.7))
        dx = LRATE * 15 * FL * math.pi / 180 * (t - T_SW["void"]) * 0.9            # drift with the turning sky
        for i, (fx, fy, k, sz, gn) in enumerate(VOIDGAL):
            spr = self.voidspr[k]; s = sz / spr.shape[0]
            x = fx * W + dx; y = fy * H
            M = cv2.getRotationMatrix2D((spr.shape[1] / 2, spr.shape[0] / 2), 15 * i, s)
            M[0, 2] += x - spr.shape[1] / 2; M[1, 2] += y - spr.shape[0] / 2
            sky += cv2.warpAffine(spr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) * gn
        return sky

    def sky(self, key, t, lst):
        s = getattr(self, "sky_" + key)(t, lst)
        return s * self.above + self.nights[key] * (1 - self.above)

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- light rays
    def rays_fx(self, t, P, Q, w, cx, cy, I):
        if I <= 0.005: return 0.0
        dx, dy = self.hx - cx, self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx) + 0.25 * np.log(d / 30.0)
        rad = (1 - np.exp(-(d + 6) / 60)) * (np.exp(-d / 1400) * 0.9 + 0.1)
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + 0.05 * t * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = 0.6 * b["w"] * (1 + 0.3 * math.sin(t * 0.8 * b["sp"] + b["ph"]))
            gg = np.exp(-(dp / wd) ** 2 * 1.6) * b["I"] * (0.7 + 0.3 * math.sin(t * 1.2 * b["sp"] + 2 * b["ph"]))
            x = (b["hue"] + dp / wd * 0.25) % 1.0
            c = pal_list(Q["beams"], x) if w >= 1 else pal_list(P["beams"], x) * (1 - w) + pal_list(Q["beams"], x) * w
            acc += c * gg[..., None]
        return acc * (rad * I * 0.30)[..., None]

    # -------------------------------------------------------------------------------------------- frame
    def centre_px(self, key, lst):
        if key in ("today", "void"): return (540.0, 700.0)
        return self.screen_of(key, lst)

    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        lst = LST(t)
        cur, prev, t0, t1 = scene_at(t)
        P, Q = SC[prev], SC[cur]
        u = t - t0
        w = ramp(t, t0 - 0.05, t0 + 0.6) if t0 > 0 else 1.0
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.7) + sum(0.30 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        cx, cy = self.centre_px(cur, lst)
        # ---- sky: the new sky inside the expanding shockwave, the old one outside
        sky = self.sky(cur, t, lst)
        if 0 <= u < REVEAL and t0 > 0:
            old = self.sky(prev, t, lst)
            Rr = 2400 * (u / 1.4) ** 0.6
            dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
            m = smooth(Rr + 50, Rr - 50, dd)[..., None]
            sky = old * (1 - m) + sky * m
        # scene breathing (light pulses on the key words)
        sky = self.nights[cur] + (sky - self.nights[cur]) * (0.92 + 0.08 * pulse)
        # ---- light rays + aura from the scene centre
        bI = Q["bI"] * (0.55 + 0.45 * ramp(u, 0, 0.6)) * (1 + 0.6 * math.exp(-max(u, 0) / 0.5)) if cur != "today" else 0.0
        if cur != "today":
            lay = self.rays_fx(t, P, Q, w, cx, cy, bI * 0.6)
            dx, dy = self.hx - cx, self.hy - cy; d = np.sqrt(dx * dx + dy * dy)
            lay = lay + (np.exp(-d / 420) * 0.05 * Q["I"])[..., None] * np.array(Q["lc"], f32)
            sky = sky + self.up(lay * pulse) * self.above
        # ---- summit relit by the sky
        lw = (Q["I"] * w + P["I"] * (1 - w)) * (0.9 + 0.1 * pulse)
        lcol = np.array(Q["lc"], f32) * w + np.array(P["lc"], f32) * (1 - w)
        fgc = self.base * (0.8 + 2.0 * lw) + self.alb * self.skyfac * lcol * lw * 0.55 + self.rim * lcol * (0.25 + 1.2 * lw) * 0.5
        if cur == "void" and w > 0.5: fgc = fgc + self.alb * self.skyfac * np.array([0.30, 0.55, 0.40], f32) * 0.012   # airglow on the rocks
        img = sky * (1 - self.a) + fgc * self.a
        # ---- swap flash + chromatic shockwave ring
        for ts, k in SWAPS:
            uu = t - ts
            if -0.05 < uu < 1.4:
                fc = 0.45 + 0.55 * np.array(SC[k]["lc"], f32) / max(SC[k]["lc"])
                img += (2.0 * math.exp(-max(uu, 0) / 0.09) * ease((uu + 0.05) / 0.05)) * fc
                if k == "today": continue
                pc = self.centre_px(k, LST(ts))
                Rr = 2400 * (max(uu, 0) / 1.4) ** 0.6; wdt = 18 + 60 * uu
                dd = np.sqrt((self.hx - pc[0]) ** 2 + (self.hy - pc[1]) ** 2)
                ring = np.zeros(dd.shape + (3,), f32)
                for ch, off in ((0, 12), (1, 0), (2, -12)):
                    ring[..., ch] = np.exp(-((dd - Rr - off) / wdt) ** 2) * 2.0 * math.exp(-max(uu, 0) / 0.55)
                img += self.up(ring)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (24 * v ** 2.5) * np.array([1.0, 0.94, 0.88], f32)
        img = self.chroma_bloom(img)
        out = tonemap(img, lerp(P["expo"], Q["expo"], w))
        y_ = out.mean(2, keepdims=True); out = np.clip(y_ + (out - y_) * 1.22, 0, 1)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0, t1, lst)
        return out

    def chroma_bloom(self, img):
        img = bloom(img, 0.5)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.25

    def chroma(self, out):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0, t1, lst):
        L = self.L; W = L.W
        Q = SC[cur]
        if cur == "today":
            a = ramp(t, 0.6, 0.95) * (1 - ramp(t, T_SW["gc"] - 0.4, T_SW["gc"] - 0.15)) if t < T_SW["gc"] else ramp(t, T_BACK + 0.35, T_BACK + 0.7)
        else:
            a = ramp(t, t0 + 0.15, t0 + 0.45) * (1 - ramp(t, t1 - 0.35, t1 - 0.15)) * (1 - ramp(t, T_WO0, T_WO0 + 0.3))
        if a > 0.01:
            x, ys = W / 2, (262, 338, 386, 432); dy = (1 - a) * 18
            rgba, _ = word_layer(Q["name"], int(L.hud_size * 1.1), W * 0.9, fill=Q["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            cols = ((255, 222, 120), (255, 255, 255), (200, 225, 255))
            for j, line in enumerate(Q["l"]):
                hud_text(out, line, x, ys[j + 1] + dy, int(L.hud_size * 0.52), "Black", cols[j], a, 0.05, display=True)
        if cur == "void":                                                   # point out the faint galaxies
            ag = ramp(t, T_VOIDGAL - 0.1, T_VOIDGAL + 0.3) * (1 - ramp(t, T_WO0 - 0.2, T_WO0 + 0.1))
            if ag > 0.01:
                dx = LRATE * 15 * FL * math.pi / 180 * (t - T_SW["void"]) * 0.9
                ov = np.zeros_like(out[..., 0])
                for i, (fx, fy, k, sz, gn) in enumerate(VOIDGAL):
                    ai = ramp(t, T_VOIDGAL + 0.08 * i, T_VOIDGAL + 0.08 * i + 0.25)
                    pr = sz * 1.3 + 10 + 2 * math.sin(t * 4 + i)
                    cv2.circle(ov, (int((fx * W + dx) * 4), int(fy * L.H * 4)), int(pr * 4), float(ai), 2, cv2.LINE_AA, shift=2)
                ov = cv2.GaussianBlur(ov, (0, 0), 0.6) * ag * 0.75
                out[:] = out * (1 - ov[..., None]) + ov[..., None] * np.array([0.75, 1.0, 0.92], f32)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "info":
        print("DUR", DUR, {k: round(v, 2) for k, v in T_SW.items()}, "wo", round(T_WO0, 2), "back", round(T_BACK, 2))
        print("halo disk angular diameter", round(2 * math.degrees(math.atan(50000 / H_LY)), 1), "deg")
        sys.exit()
    if sys.argv[1] == "stills":
        sc = Scene(True); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in [float(x) for x in sys.argv[2].split(",")]:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
