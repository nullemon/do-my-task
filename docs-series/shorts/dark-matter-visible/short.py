"""WHAT IF YOU COULD SEE DARK MATTER? -- one LOCKED shot of the user's mountain observatory (07_mountain_observatory.png)
at night. The real sky (HYG v4.1 stars, V < 6.5, at 34 deg N + the vivid Milky Way band of galaxy-address) stays; at each
swap (flash + chromatic shockwave revealing the new layer inside its ring, beams, relit summit, readout) another layer of
dark matter becomes visible, all fixed to the turning sky in galactic coordinates (prep.py):
  today   the normal Milky Way
  halo    the halo: NFW line-of-sight column from the Sun's position (brightest towards the galactic centre), soft purple
          volumetric wisps, slowly flowing
  clumps  + subhalos: hundreds of small cores (static canvas) and ~40 big clumps drifting slowly across the sky
  web     + the cosmic web: filaments and knots across the whole sky
  stream  + the dark-matter "wind": particles streaming at us from Cygnus (the direction of the Sun's orbit), with a
          random velocity dispersion; purple glints flicker on the summit
  -> white-out -> today (loops; the sidereal drift is re-based under the white-out)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py stills 1.0,9.5       -> SCR/stills/<t>.png
  /home/user/ttsenv/bin/python short.py seg                  restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time
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

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-dark-matter-visible"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/07_mountain_observatory.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
FL, ALT0 = 540.0, 60.0                    # stereographic lens: f (px), centre altitude (deg), facing south

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for l in PL if l["key"].startswith(key) for w in l["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ timeline
T_SW = dict(halo=wt("halo", "GHOSTLY") - 0.12, clumps=wt("clumps", "LUMPY") - 0.12, web=wt("web", "COSMIC") - 0.12,
            stream=wt("stream2", "FLOWING") - 0.12)
T_BACK = LN["end2"]["start"] + 0.02                  # white-out peak -> the normal sky again
T_WO0 = T_BACK - 0.80
ORDER = ["halo", "clumps", "web", "stream"]
SWAPS = [(T_SW[k], k) for k in ORDER] + [(T_BACK, "today")]
PULSES = [wt("hook", "DARK"), wt("halo", "SWALLOWS"), wt("halo2", "5×"), wt("halo2", "UNIVERSE"), wt("clumps2", "THOUSANDS"),
          wt("clumps2", "DRIFTING"), wt("web2", "THREADS"), wt("web2", "WHOLE"), wt("stream2", "YOU"), wt("stream3", "BILLIONS"),
          wt("stream3", "SECOND"), wt("end2", "LEFT")]
REVEAL = 1.15
L0, LRATE = 19.30, 0.050                             # sidereal time (h) at t = 0, stylised time-lapse rate (h/s)
def LST(t): return L0 + LRATE * (t if t < T_BACK else t - DUR - 1 / FPS)


def scene_at(t):
    cur, t0, prev = "today", -10.0, "today"
    for i, (ts, k) in enumerate(SWAPS):
        if t >= ts: cur, t0, prev = k, ts, (SWAPS[i - 1][1] if i > 0 else "today")
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


# ------------------------------------------------------------------------------------------------ scenes
# dm: visible amount of each dark-matter layer; lc / I: light cast on the summit; beams: palette of the light rays
SC = {
    "today": dict(name="THE MILKY WAY TONIGHT", tc=(170, 205, 255), l=["100–400 BILLION STARS", "PLUS GAS AND DUST", "ALL OF IT: NORMAL MATTER"],
                  dm=dict(halo=0, clumps=0, web=0, stream=0), lc=(0.55, 0.65, 1.0), I=0.10, beams=[(0.45, 0.65, 1.0), (0.8, 0.6, 1.0)], bI=0.0, expo=1.15),
    "halo": dict(name="THE DARK MATTER HALO", tc=(205, 160, 255), l=["~1 TRILLION SUNS OF MASS", "OVER A MILLION LIGHT-YEARS ACROSS", "DARK : NORMAL MATTER ≈ 5.4 : 1"],
                 dm=dict(halo=1.0, clumps=0, web=0, stream=0), lc=(0.62, 0.42, 1.0), I=0.42,
                 beams=[(0.65, 0.35, 1.0), (0.45, 0.45, 1.0), (0.9, 0.55, 1.0), (0.55, 0.25, 0.9)], bI=0.22, expo=1.05),
    "clumps": dict(name="SUBHALOS", tc=(225, 150, 255), l=["THOUSANDS IN SIMULATIONS", "~60 KNOWN DWARF GALAXIES LIVE IN THEM", "MOST MAY HOLD NO STARS AT ALL"],
                   dm=dict(halo=0.75, clumps=1.0, web=0, stream=0), lc=(0.72, 0.42, 1.0), I=0.50,
                   beams=[(0.85, 0.4, 1.0), (0.55, 0.35, 1.0), (1.0, 0.55, 0.9), (0.6, 0.5, 1.0)], bI=0.22, expo=1.05),
    "web": dict(name="THE COSMIC WEB", tc=(170, 175, 255), l=["THREADS 100s OF MILLIONS OF LY LONG", "~85% OF ALL MATTER IS DARK", "GALAXIES GROW WHERE THREADS MEET"],
                dm=dict(halo=0.55, clumps=0.45, web=1.0, stream=0), lc=(0.55, 0.50, 1.0), I=0.55,
                beams=[(0.5, 0.55, 1.0), (0.8, 0.45, 1.0), (0.4, 0.75, 1.0), (0.95, 0.6, 1.0)], bI=0.25, expo=1.0),
    "stream": dict(name="THE DARK MATTER WIND", tc=(215, 170, 255), l=["~230 KM/S, BLOWING FROM CYGNUS", "~1 PROTON-MASS IN EVERY 3 CM³", "IF WIMPS: ~1 BILLION A SECOND THROUGH YOU"],
                   dm=dict(halo=0.55, clumps=0.35, web=0.40, stream=1.0), lc=(0.70, 0.48, 1.0), I=0.55,
                   beams=[(0.75, 0.45, 1.0), (0.5, 0.6, 1.0), (1.0, 0.7, 1.0), (0.6, 0.35, 1.0)], bI=0.25, expo=1.0),
}
C_HALO = (np.array([0.50, 0.20, 1.00], f32), np.array([0.85, 0.70, 1.00], f32), np.array([0.30, 0.75, 1.00], f32))   # violet core, lavender-white centre, cyan outer veil / edge
HALO_EDGE = 42.0                          # deg from the GC: the soft edge of the dense inner halo (stylised, README)
C_CLUMP = (np.array([0.62, 0.22, 1.00], f32), np.array([0.95, 0.80, 1.00], f32))
C_WEB = (np.array([0.62, 0.36, 1.00], f32), np.array([0.32, 0.62, 1.00], f32), np.array([0.98, 0.90, 1.00], f32))   # near violet, far cyan-blue, knots white


def lerp(a, b, w): return a + (b - a) * w


def pal_list(cols, x):
    C = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


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
        alt = np.arcsin(np.clip(self.rays[..., 2], -1, 1)).astype(f32)
        self.e = e = np.clip(alt / (np.pi / 2), 0, 1)
        self.above = smooth(-0.01, 0.04, alt).astype(f32)[..., None]
        self.above_h = cv2.resize(self.above[..., 0], (W // 2, H // 2), interpolation=cv2.INTER_AREA)[..., None]
        self.nz = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        k = np.exp(-e / 0.30)[..., None]
        zen, hor = np.array((0.0035, 0.0055, 0.024), f32), np.array((0.012, 0.022, 0.075), f32)
        n = zen * (1 - k) + hor * k
        self.night = (n * (1 + 0.06 * self.nz)[..., None]).astype(f32)
        # ---- data
        mw = canvas(os.path.join(SCR, "mw_gal.npz")); y = lum(mw)[..., None]
        self.mw = (y + (mw - y) * 0.55) * np.array([0.92, 0.97, 1.08], f32)          # a neutral, star-white band (no violet)
        dm = np.load(os.path.join(SCR, "dm.npz"))
        self.dm = {k: dm[k].astype(f32) for k in ("J", "wisp", "clumps", "webN", "webF")}
        z = np.load(os.path.join(SCR, "stars.npz")); keep = z["mag"] < 6.5
        self.ph_rng = np.random.default_rng(3)
        self.stars = self.mkset(eq_vec(z["ra"][keep], z["dec"][keep]), z["mag"][keep],
                                star_rgb(np.clip(bv_temp(np.clip(z["ci"][keep], -0.4, 2.0)), 2600, 30000)))
        self._dn = (fbm2((512, 512), 91, 2.8), fbm2((512, 512), 92, 2.2))
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 9 + r.uniform(-0.2, 0.2), w=r.uniform(0.10, 0.20), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(9)]
        # ---- drifting big clumps (galactic unit vectors, rotation axes, angular sizes)
        n = 40
        g = r.normal(size=(n, 3)); g /= np.linalg.norm(g, axis=1, keepdims=True)
        ax = r.normal(size=(n, 3)); ax -= (ax * g).sum(1, keepdims=True) * g; ax /= np.linalg.norm(ax, axis=1, keepdims=True)
        self.cl = dict(g=g, ax=ax, w=r.uniform(0.25, 0.9, n) * np.radians(1.0), sz=np.clip(1.2 * r.uniform(0, 1, n) ** -0.5, 1.2, 7.0),
                       gain=r.uniform(0.7, 1.2, n), ph=r.uniform(0, 6.28, n))
        # ---- dark-matter wind: particles in a periodic box around the observer (equatorial frame)
        apex = EQ2GAL.T @ np.array([0.0, 1.0, 0.0])                          # l = 90, b = 0 (towards Cygnus)
        self.apex = apex / np.linalg.norm(apex)
        npart = 2600
        self.pp = r.uniform(-1, 1, (npart, 3)); self.pv = -self.apex[None] * 0.60 + r.normal(size=(npart, 3)) * 0.05
        sw = np.cross(self.apex, [0.0, 0.0, 1.0]); self.swirl = sw / np.linalg.norm(sw)           # gentle common curl
        self.pb = r.uniform(0.5, 1.0, npart); self.pc = r.uniform(0, 1, npart)
        # ---- summit: night base, lit albedo, rim; sky-facing factor; glint points
        a = fg.a; self.a = a[..., None]
        f = fg.flat; y = lum(f)[..., None]
        self.base = ((f * 0.35 + y * 0.65) * np.array([0.30, 0.36, 0.75], f32) * 0.10).astype(f32)
        self.alb = np.clip(f * 0.8 + y * 0.2, 0, 1).astype(f32)
        sk = np.clip((self.hz + 150 - yy) / (self.hz + 150 - fg.skyline.min()), 0, 1)
        self.skyfac = (0.40 + 0.60 * sk)[..., None].astype(f32)
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a)[..., None].astype(f32)
        cand = np.flatnonzero((a > 0.95).ravel()); pick = r.choice(cand, 1400, replace=False)
        self.gl = dict(x=pick % W, y=pick // W, fr=r.uniform(2.0, 7.0, 1400), ph=r.uniform(0, 6.28, 1400), sz=r.uniform(0.3, 1.0, 1400) ** 2)
        emph = {"DARK", "MATTER", "GHOSTLY", "GLOW", "SWALLOWS", "5×", "ATOMS", "UNIVERSE", "LUMPY", "THOUSANDS", "CLUMPS", "COSMIC",
                "WEB", "THREADS", "WHOLE", "SKY", "STRANGEST", "FLOWING", "YOU", "BILLIONS", "SECOND", "BLINK", "GONE", "NEVER", "LEFT"}
        self.caps = Captions(L, WORDS, emphasis=emph)

    def mkset(self, d, V, col):
        V = np.asarray(V, f32); o = np.argsort(V)
        return dict(d=np.asarray(d, np.float64)[o], V=V[o], col=col[o], fd=disp_flux(V[o]), ph=self.ph_rng.uniform(0, 1000, len(V)).astype(f32))

    def M(self, lst): return eq2hor(lst)
    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- stars (galaxy-address)
    def stars_layer(self, s, t, lst):
        L = self.L; W, H = L.W, L.H
        h = s["d"] @ self.M(lst).T
        vis = np.where(h[:, 2] > -0.01)[0]; h = h[vis]
        x, y, ok = self.lens.project(h)
        sel = ok & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
        idx = vis[sel]; x = x[sel]; y = y[sel]; zz = h[sel, 2]
        ph = s["ph"][idx]
        nt = np.sin(t * 13.1 + ph) * 0.5 + np.sin(t * 23.7 + ph * 1.7) * 0.3 + np.sin(t * 37.3 + ph * 2.3) * 0.2
        sig = np.clip(0.10 + 0.35 * np.exp(-zz / 0.15), 0.08, 0.6)
        tw = np.exp(sig * nt * 1.6 - 0.5 * sig * sig)
        fd = s["fd"][idx] * tw * np.clip(zz / 0.12, 0, 1) ** 0.7
        core = np.minimum(fd, 5.0); col = s["col"][idx]
        acc = np.zeros(((H + 2) * (W + 2), 3), f32)
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = x - x0; fy = y - y0
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            li = np.clip(y0 + dy, 0, H + 1) * (W + 2) + np.clip(x0 + dx, 0, W + 1); w_ = core * wg
            for c in range(3): acc[:, c] += np.bincount(li, weights=w_ * col[:, c], minlength=(H + 2) * (W + 2)).astype(f32)
        st = cv2.GaussianBlur(acc.reshape(H + 2, W + 2, 3)[:H, :W], (0, 0), 0.7) * 2.4
        big = fd > 2.0
        if big.any():
            q = 4; hq, wq = H // q, W // q
            hb = np.zeros((hq * wq, 3), f32)
            xi = np.clip((x[big] / q).astype(np.int64), 0, wq - 1); yi = np.clip((y[big] / q).astype(np.int64), 0, hq - 1)
            ex = (fd[big] - 1.2) ** 0.85
            for c in range(3): hb[:, c] = np.bincount(yi * wq + xi, weights=ex * col[big, c], minlength=hq * wq)
            hb = hb.reshape(hq, wq, 3)
            st += cv2.resize(cv2.GaussianBlur(hb, (0, 0), 0.8) * 0.30 + cv2.GaussianBlur(hb, (0, 0), 2.5) * 0.050, (W, H), interpolation=cv2.INTER_LINEAR)
        for j in list(np.argsort(-fd)[:28]):
            g = fd[j]
            if g < 6.0: continue
            c = col[j] * 0.85 + 0.15
            Lk = min(6 + 7 * math.log(g / 6 + 1) ** 1.2, 46.0)
            a = min(g, 150.0) ** 0.8 * 0.06 * (1 + 0.25 * math.sin(t * 5 + ph[j]))
            splat(st, x[j], y[j], int(Lk * 4) + 6, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / Lk) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / Lk)) * a)[..., None] * c)
        return st

    # -------------------------------------------------------------------------------------------- base sky
    def galcoords(self, lst):
        Mg = EQ2GAL @ self.M(lst).T
        g = self.rays_h @ Mg.T.astype(f32)
        l = np.degrees(np.arctan2(g[..., 1], g[..., 0])); b = np.degrees(np.arcsin(np.clip(g[..., 2], -1, 1)))
        return l, b, Mg

    def sky_base(self, t, lst, l, b):
        mx = (WL / 2 + l * PXD) % WL; my = HB / 2 - b * PXD
        mw = cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        return self.night + self.up(mw) * 5.0 + self.stars_layer(self.stars, t, lst)

    # -------------------------------------------------------------------------------------------- dark matter (half res)
    def flow(self, t, sc, vx, vy, k=0):
        n = self._dn[k]
        return cv2.remap(n, ((self.hx * sc + t * vx) % 512).astype(f32), ((self.hy * sc + t * vy) % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def canv(self, key, l, b):
        c = self.dm[key]; Hc, Wc = c.shape
        return cv2.remap(c, ((Wc / 2 + l * Wc / 360.0) % Wc).astype(f32), (Hc / 2 - b * Hc / 180.0).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def dm_layer(self, dmw, t, lst, l, b, Mg):
        """linear radiance (half res) of the dark-matter layers with amounts dmw"""
        out = np.zeros(self.hx.shape + (3,), f32)
        if dmw["halo"] > 0:
            J = self.canv("J", l, b); wisp = self.canv("wisp", l, b)
            fl = np.clip(0.80 + 0.28 * self.flow(t, 0.30, 7.0, 2.5, 0) + 0.12 * self.flow(t, 0.75, -11.0, 4.0, 1), 0.45, 1.5)   # slow flow
            wv = wisp * fl
            psi = np.degrees(np.arccos(np.clip(np.cos(np.radians(b)) * np.cos(np.radians(l)), -1, 1)))      # angle from the GC
            edge = HALO_EDGE + 3.0 * (wisp - 1.0)
            inner = smooth(edge + 6, edge - 6, psi)
            rim = np.exp(-((psi - edge) / 5.0) ** 2) * np.clip(wv, 0.3, 1.6)
            outer = (J ** 0.5) * wv * 0.012
            core = inner * (J ** 0.75) * wv * 0.020
            col_core = C_HALO[0] * (1 - np.clip(J / 10, 0, 1))[..., None] + C_HALO[1] * np.clip(J / 10, 0, 1)[..., None]
            out += (outer[..., None] * C_HALO[2] + core[..., None] * col_core + (rim * 0.045)[..., None] * C_HALO[2]) * dmw["halo"]
        if dmw["clumps"] > 0:
            c = self.canv("clumps", l, b)
            m = np.clip(c / 1.2, 0, 1)[..., None]
            lay = cv2.GaussianBlur(c, (0, 0), 2.0)[..., None] * (C_CLUMP[0] * (1 - m) + C_CLUMP[1] * m) * 0.18
            lay += self.drift_clumps(t, lst, Mg)
            out += lay * dmw["clumps"]
        if dmw["web"] > 0:
            wn = self.canv("webN", l, b); wf = self.canv("webF", l, b)
            mn = np.clip(wn / 4.0, 0, 1)[..., None]
            near = wn[..., None] * (C_WEB[0] * (1 - mn) + C_WEB[2] * mn)
            far = wf[..., None] * C_WEB[1] * 0.55
            out += (near + far) * 0.040 * (0.94 + 0.06 * math.sin(t * 1.3)) * dmw["web"]
        if dmw["stream"] > 0:
            out += self.wind(t, lst) * dmw["stream"]
        return out

    def drift_clumps(self, t, lst, Mg):
        """~40 big subhalos drifting slowly over the sky (Rodrigues rotation of each about its own axis)"""
        lay = np.zeros(self.hx.shape + (3,), f32)
        c = self.cl; a = (c["w"] * t)[:, None]
        g = c["g"] * np.cos(a) + np.cross(c["ax"], c["g"]) * np.sin(a)
        h = g @ Mg                                                           # galactic -> horizon (Mg: eq->gal composed)
        x, y, ok = self.lens.project(h)
        for i in range(len(g)):
            if not ok[i] or h[i, 2] < -0.05: continue
            xs, ys = x[i] / 2, y[i] / 2
            Rp = c["sz"][i] * math.pi / 180 * FL / 2 * 2.0                    # half-res px (stereographic ~ f / unit at centre)
            if xs < -6 * Rp or xs > self.hx.shape[1] + 6 * Rp or ys < -6 * Rp or ys > self.hx.shape[0] + 6 * Rp: continue
            gn = c["gain"][i] * (1 + 0.15 * math.sin(t * 0.9 + c["ph"][i]))
            def f(d, dx, dy, Rp=Rp, gn=gn):
                p = 0.8 / (1 + (d / Rp) ** 2) * np.exp(-d / (3.2 * Rp)) + 0.35 * np.exp(-(d / (0.6 * Rp)) ** 2)
                m = np.clip(p * 1.6, 0, 1)[..., None]
                return (p * gn * 0.30)[..., None] * (C_CLUMP[0] * (1 - m) + C_CLUMP[1] * m)
            splat(lay, xs, ys, int(8 * Rp) + 4, f)
        return lay

    def wind(self, t, lst):
        """particles in a periodic box flowing at us from Cygnus with a gentle common curl; each streak is a 4-point
        polyline over the last 1/10 s (slightly curved), with a soft glow; brighter when close"""
        Hh, Wh = self.hx.shape
        lay = np.zeros((Hh, Wh), f32)
        M = self.M(lst); pts = []
        for dt in (0.0, 0.033, 0.066, 0.10):
            tt = t - dt
            p = self.pp + self.pv * tt * 0.45 + self.swirl[None] * 0.10 * np.sin(tt * 1.1 + self.pc[:, None] * 6.28)
            p = (p + 1) % 2 - 1
            r = np.linalg.norm(p, axis=1) + 1e-6
            h = (p / r[:, None]) @ M.T
            x, y, ok = self.lens.project(h); pts.append((x / 2, y / 2, ok & (h[:, 2] > -0.05), r))
        r0 = pts[0][3]
        good = np.all([q[2] for q in pts], 0) & (r0 > 0.05) & (np.abs(pts[0][3] - pts[-1][3]) < 0.3)
        good &= np.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 220
        br = self.pb * np.clip(0.05 / (r0 ** 2 + 0.006), 0.15, 6.0)
        for i in np.flatnonzero(good):
            poly = np.array([[int(q[0][i] * 4), int(q[1][i] * 4)] for q in pts], np.int32)
            cv2.polylines(lay, [poly], False, float(br[i]), 1, cv2.LINE_AA, shift=2)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.7) + cv2.GaussianBlur(lay, (0, 0), 2.5) * 0.7 + cv2.GaussianBlur(lay, (0, 0), 8.0) * 0.5
        hue = np.clip(0.5 + 0.5 * self.flow(t, 0.2, 4.0, -3.0, 0), 0, 1)[..., None]
        return lay[..., None] * (np.array([0.78, 0.48, 1.00], f32) * (1 - hue) + np.array([0.45, 0.78, 1.00], f32) * hue) * 2.0

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
        if key == "stream":
            x, y, ok = self.lens.project((self.apex @ self.M(lst).T)[None]); return float(x[0]), float(y[0])
        if key in ("halo", "clumps"):                                         # the halo is densest towards the galactic centre
            gc = EQ2GAL.T @ np.array([1.0, 0.0, 0.0])
            x, y, ok = self.lens.project((gc @ self.M(lst).T)[None]); return float(x[0]), float(min(y[0], self.hz - 160))
        return (540.0, 640.0)

    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        lst = LST(t)
        cur, prev, t0, t1 = scene_at(t)
        P, Q = SC[prev], SC[cur]
        u = t - t0
        w = ramp(t, t0 - 0.05, t0 + 0.6) if t0 > 0 else 1.0
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.7) + sum(0.30 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        cx, cy = self.centre_px(cur, lst)
        l, b, Mg = self.galcoords(lst)
        sky = self.sky_base(t, lst, l, b)
        # ---- dark matter: the new layers inside the expanding shockwave, the old ones outside
        dmh = self.dm_layer(Q["dm"], t, lst, l, b, Mg) if cur != "today" else None
        if 0 <= u < REVEAL and t0 > 0 and prev != "today":
            old = self.dm_layer(P["dm"], t, lst, l, b, Mg)
            Rr = 2400 * (u / 1.4) ** 0.6
            dd = np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2)
            m = smooth(Rr + 50, Rr - 50, dd)[..., None]
            dmh = old * (1 - m) + (dmh if dmh is not None else 0.0) * m
        elif 0 <= u < REVEAL and t0 > 0 and dmh is not None:
            Rr = 2400 * (u / 1.4) ** 0.6
            dd = np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2)
            dmh = dmh * smooth(Rr + 50, Rr - 50, dd)[..., None]
        if dmh is not None:
            dmh = dmh * (0.92 + 0.08 * pulse)
            bI = Q["bI"] * (0.55 + 0.45 * ramp(u, 0, 0.6)) * (1 + 0.6 * math.exp(-max(u, 0) / 0.5))
            dmh = dmh + self.rays_fx(t, P, Q, w, cx, cy, bI * 0.6) * pulse
            sky = sky + self.up(dmh) * self.above
        # ---- summit relit by the (dark-matter) sky
        lw = (Q["I"] * w + P["I"] * (1 - w)) * (0.9 + 0.1 * pulse)
        lcol = np.array(Q["lc"], f32) * w + np.array(P["lc"], f32) * (1 - w)
        fgc = self.base * (0.8 + 2.0 * lw) + self.alb * self.skyfac * lcol * lw * 0.55 + self.rim * lcol * (0.25 + 1.2 * lw) * 0.5
        if cur == "stream": fgc = fgc + self.glints(t, ramp(u, 0.2, 1.0) * (1 - ramp(t, T_WO0 - 0.2, T_WO0 + 0.2)))
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
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (24 * v ** 2.5) * np.array([0.95, 0.90, 1.0], f32)
        img = self.chroma_bloom(img)
        out = tonemap(img, lerp(P["expo"], Q["expo"], w))
        y_ = out.mean(2, keepdims=True); out = np.clip(y_ + (out - y_) * 1.22, 0, 1)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0, t1)
        return out

    def glints(self, t, amt):
        """purple glints flickering on the rocks: the summit lit by the passing wind (a light layer on the plate)"""
        if amt <= 0.01: return 0.0
        g = self.gl; H, W = self.L.H, self.L.W
        val = np.clip(np.sin(t * g["fr"] * 6.283 + g["ph"]), 0, 1) ** 12 * g["sz"] * amt
        lay = np.zeros((H, W), f32); np.add.at(lay, (g["y"], g["x"]), val.astype(f32))
        lay = cv2.GaussianBlur(lay, (0, 0), 0.9) * 2.0 + cv2.GaussianBlur(lay, (0, 0), 3.0) * 1.2
        return lay[..., None] * np.array([0.75, 0.50, 1.0], f32) * self.a

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

    def overlay(self, out, t, cur, t0, t1):
        L = self.L; W = L.W
        Q = SC[cur]
        if cur == "today":
            a = ramp(t, 0.6, 0.95) * (1 - ramp(t, T_SW["halo"] - 0.4, T_SW["halo"] - 0.15)) if t < T_SW["halo"] else ramp(t, T_BACK + 0.35, T_BACK + 0.7)
        else:
            a = ramp(t, t0 + 0.15, t0 + 0.45) * (1 - ramp(t, t1 - 0.35, t1 - 0.15)) * (1 - ramp(t, T_WO0, T_WO0 + 0.3))
        if a > 0.01:
            x, ys = W / 2, (262, 338, 386, 432); dy = (1 - a) * 18
            rgba, _ = word_layer(Q["name"], int(L.hud_size * 1.1), W * 0.9, fill=Q["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            cols = ((255, 222, 120), (255, 255, 255), (220, 205, 255))
            for j, line in enumerate(Q["l"]):
                hud_text(out, line, x, ys[j + 1] + dy, int(L.hud_size * 0.52), "Black", cols[j], a, 0.05, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "info":
        print("DUR", DUR, {k: round(v, 2) for k, v in T_SW.items()}, "wo", round(T_WO0, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "stills":
        sc = Scene(True); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in [float(x) for x in sys.argv[2].split(",")]:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
