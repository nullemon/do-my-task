"""THE NIGHT ANDROMEDA HITS US -- one LOCKED shot of the user's suburban backyard (08_suburban_backyard.png) at night, string
lights glowing. A time-lapse of the sky over billions of years as Andromeda approaches; each beat swaps in with a flash,
a chromatic shockwave that reveals the new sky inside its ring, coloured light beams, a relit yard, a readout and a big
glowing YEAR counter.
  today  the real sky (HYG v4.1, V < 6.5, 40 deg N) + the Milky Way band; Andromeda as a faint smudge, 3.17 deg (6 full Moons)
  g2     +2 Gyr: ~500 kpc away, ~5 deg (~10 full Moons)
  g3     +3.75 Gyr: ~85 kpc, the bright disc ~29 deg, outer disc + tidal tails far beyond
  g4     first close pass (~4 Gyr): both galaxies torn and twisted, a starburst of pink nebulae + blue young stars
  g5     "Milkomeda" (~7 Gyr): a giant elliptical glow over the whole sky
  -> white-out -> today (loops)
Andromeda = NASA/JPL-Caltech GALEX PIA15416, at its TRUE angular size for each distance (stereographic lens, f = FL px/rad),
placed at its real sky position and orientation. Distances: a radial two-body infall (770 kpc, -110 km/s, 2e12 Msun)
up to 3 Gyr, then the van der Marel et al. (2012) approach to the first pericentre (~31 kpc at ~3.9 Gyr).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info | stills 1.0,9.5 | seg
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path)
import numpy as np, cv2
from PIL import Image, ImageDraw
from lib.core import f32, Layout, ramp, smooth, ease, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite, font
from lib.post import bloom, tonemap, finish
from lib.audio import place
import skygeo
skygeo.LAT = 40.0
from skygeo import eq_vec, eq2hor, hdir, Lens, EQ2GAL
from mwsky import canvas, WL, HB, PXD as CPXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-andromeda-collision"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/08_suburban_backyard.png"
NEB = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-galaxy-address/plates.npz"
FPS = 30
LEAD, TAIL = 0.25, 1.30
FL = 1100.0; PXDEG = FL * math.pi / 180          # px per degree near the lens centre (19.2)
M31 = (10.68471, 41.26875); M31_ALT = 40.0; D25 = 3.17
MOON_PX = 0.52 * PXDEG
LRATE = 0.004                                    # slow stylised sky drift (h/s)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for l in PL if l["key"].startswith(key) for w in l["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ timeline
T_SW = dict(g2=wt("g2", "TWO") - 0.12, g3=wt("g3", "THEN") - 0.12, g4=wt("g4", "COLLIDE") - 0.12, g5=wt("g5", "ONE") - 0.12)
T_BACK = LN["end"]["start"] - 0.05
T_WO0 = T_BACK - 0.80
SWAPS = [(T_SW[k], k) for k in ("g2", "g3", "g4", "g5")] + [(T_BACK, "today")]
T_MOONS = wt("hook2", "6") - 0.05
T_MOONS1 = LN["hook3"]["start"] + 0.6
PULSES = [wt("hook", "SMUDGE"), wt("hook2", "ANDROMEDA"), wt("g2b", "10"), wt("g3", "LOOMS"), wt("g4b", "CRASHES"), wt("g4b", "IGNITE"),
          wt("g5", "MILKOMEDA"), wt("g5b", "DYING"), wt("end2", "COIN")]
REVEAL = 1.15
# years (Gyr) at each beat and the slow creep while it is on screen (Gyr/s): the time-lapse keeps running
YRS = dict(today=(0.0, 0.0), g2=(2.0, 0.04), g3=(3.75, 0.012), g4=(3.95, 0.03), g5=(7.0, 0.06))
R_TAB = [(0.0, 770), (1.0, 650), (2.0, 500), (3.0, 290), (3.5, 170), (3.75, 85), (3.9, 31), (4.2, 31)]   # kpc


def r_of(Y): return float(np.interp(Y, [a for a, _ in R_TAB], [b for _, b in R_TAB]))


def scene_at(t):
    cur, t0, prev = "today", -10.0, "today"
    for i, (ts, k) in enumerate(SWAPS):
        if t >= ts: cur, t0, prev = k, ts, (SWAPS[i - 1][1] if i > 0 else "today")
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, prev, t0, (nxt[0] if nxt else 1e9)


def years(t):
    cur, prev, t0, t1 = scene_at(t)
    y0, cr = YRS[cur]; Y = y0 + cr * max(t - t0, 0)
    if cur == "today": return 0.0, 0.0
    yp = YRS[prev][0] + YRS[prev][1] * max(t0 - (dict(SWAPS_INV).get(prev, 0.0)), 0)
    shown = yp + (Y - yp) * ease(min(max((t - t0) / 0.7, 0), 1))       # the counter spins up to the new value
    return Y, shown


SWAPS_INV = [(k, ts) for ts, k in SWAPS]

SC = {
    "today": dict(name="ANDROMEDA (M31)", tc=(170, 205, 255), l=["2.5 MILLION LY AWAY", "6 FULL MOONS WIDE", "APPROACHING AT ~110 KM/S"],
                  zen=(0.009, 0.011, 0.065), hor=(0.040, 0.050, 0.170), lc=(0.55, 0.65, 1.0), I=0.10, beams=[(0.45, 0.65, 1.0)], bI=0.0, expo=1.15),
    "g2": dict(name="CLOSER", tc=(175, 210, 255), l=["~1.6 MILLION LY AWAY", "~10 FULL MOONS WIDE", "~1.6× TODAY'S SIZE"],
               zen=(0.010, 0.011, 0.070), hor=(0.042, 0.050, 0.175), lc=(0.6, 0.7, 1.0), I=0.25,
               beams=[(0.45, 0.65, 1.0), (1.0, 0.8, 0.45), (0.75, 0.5, 1.0)], bI=0.35, expo=1.1),
    "g3": dict(name="LOOMING", tc=(190, 220, 255), l=["~280,000 LY AWAY", "~55 FULL MOONS WIDE", "TIDAL TAILS FORMING"],
               zen=(0.014, 0.014, 0.080), hor=(0.050, 0.056, 0.190), lc=(0.75, 0.8, 1.0), I=0.55,
               beams=[(0.45, 0.65, 1.0), (1.0, 0.85, 0.6), (0.6, 0.5, 1.0), (0.35, 0.95, 1.0)], bI=0.5, expo=1.0),
    "g4": dict(name="FIRST CLOSE PASS", tc=(255, 140, 200), l=["GAS COLLIDES: A STARBURST", "STAR-ON-STAR HITS: ALMOST NONE", "IF IT HAPPENS AT ALL"],
               zen=(0.030, 0.010, 0.060), hor=(0.10, 0.03, 0.12), lc=(1.0, 0.55, 0.85), I=0.85,
               beams=[(1.0, 0.35, 0.65), (0.4, 0.75, 1.0), (1.0, 0.75, 0.5), (0.7, 0.4, 1.0)], bI=0.7, expo=0.9),
    "g5": dict(name="MILKOMEDA", tc=(255, 215, 140), l=["ONE GIANT ELLIPTICAL GALAXY", "OUR SUN: BECOMING A RED GIANT", "IF THE MERGER HAPPENS"],
               zen=(0.030, 0.020, 0.030), hor=(0.10, 0.06, 0.06), lc=(1.0, 0.80, 0.55), I=0.8,
               beams=[(1.0, 0.8, 0.45), (1.0, 0.55, 0.3), (0.8, 0.6, 1.0)], bI=0.6, expo=0.85),
}
END = dict(name="WILL IT HAPPEN?", tc=(255, 222, 120), l=["2025 SIMULATIONS (SAWALA ET AL.):", "~50% CHANCE OF A MERGER", "IN THE NEXT 10 BILLION YEARS"])


def back_out(u, s=2.0):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


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


# ------------------------------------------------------------------------------------------------ glowing text (star-dates)
_gl = {}
def glow_text(txt, size, col, wt_="Black"):
    k = (txt, int(size), col, wt_)
    if k in _gl: return _gl[k]
    f = font(size, wt_, True); w = f.getlength(txt)
    if w > 1000: f = font(int(size * 1000 / w), wt_, True); w = f.getlength(txt)
    asc, desc = f.getmetrics(); pad = int(f.size * 1.0) + 4
    Wd, Hd = int(w + 2 * pad), int(asc + desc + 2 * pad); sw = max(2, int(f.size * 0.05))
    m = Image.new("L", (Wd, Hd), 0); ImageDraw.Draw(m).text((pad, pad), txt, font=f, fill=255)
    ms = Image.new("L", (Wd, Hd), 0); ImageDraw.Draw(ms).text((pad, pad), txt, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    c255 = np.array(col, f32); col = c255 / 255.0                           # col given as 0..255
    a_s = np.asarray(ms, f32) / 255; a_f = np.asarray(m, f32) / 255
    grad = np.linspace(1.0, 0.0, Hd)[:, None, None]
    fill = (np.array([255, 255, 255], f32) * 0.62 + c255 * 0.38) * (0.85 + 0.15 * grad) + c255 * 0.10 * (1 - grad)
    rgba = np.zeros((Hd, Wd, 4), f32)
    rgba[..., :3] = c255 * (1 - a_f[..., None]) + np.clip(fill, 0, 255) * a_f[..., None]; rgba[..., 3] = a_s * 255
    glow = (cv2.GaussianBlur(a_s, (0, 0), f.size * 0.16) * 0.9 + cv2.GaussianBlur(a_s, (0, 0), f.size * 0.45) * 0.6)[..., None] * np.array(col, f32)
    sh = cv2.GaussianBlur(a_s, (0, 0), f.size * 0.10)
    _gl[k] = (rgba.astype(np.uint8), glow.astype(f32), sh.astype(f32)); return _gl[k]


def put_glow(dst, layer, cx, cy, alpha, glow_k=0.9):
    rgba, glow, sh = layer
    h, w = rgba.shape[:2]; H, W = dst.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya or alpha <= 0.003: return
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    reg = dst[ya:yb, xa:xb]
    reg *= (1 - 0.5 * sh[sl] * alpha)[..., None]; reg += glow[sl] * glow_k * alpha
    a = rgba[sl][..., 3:].astype(f32) / 255 * alpha
    dst[ya:yb, xa:xb] = np.clip(reg * (1 - a) + rgba[sl][..., :3].astype(f32) / 255 * a, 0, 1)


def fmt_years(Y):
    if Y < 0.005: return "2026"
    return f"+{Y:.2f} BILLION"


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.97)
        self.hz = float(fg.horizon)
        # sidereal time at which M31 stands at M31_ALT in the east (rising); the lens is centred on it
        best = None
        for lst in np.arange(12.0, 24.0, 0.01):
            h = eq2hor(lst) @ eq_vec(*M31); alt = math.degrees(math.asin(h[2])); az = math.degrees(math.atan2(h[0], h[1])) % 360
            if az < 180 and (best is None or abs(alt - M31_ALT) < best[0]): best = (abs(alt - M31_ALT), lst, az, alt)
        self.L0, az, alt = best[1], best[2], best[3]
        self.lens = Lens(W, H, az, alt, FL, self.hz + 10)
        print(f"LST0 {self.L0:.2f} h, M31 az {az:.1f} alt {alt:.1f}")
        L.cap_y = 1010
        yy, xx = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx, yy
        hy, hx = np.mgrid[0:H // 2, 0:W // 2].astype(f32) * 2 + 1.0; self.hx, self.hy = hx, hy
        self.rays = self.lens.rays(1); self.rays_h = self.lens.rays(2)
        alt_ = np.arcsin(np.clip(self.rays[..., 2], -1, 1)).astype(f32)
        self.e = np.clip(alt_ / (np.pi / 2), 0, 1)
        self.above = smooth(-0.01, 0.04, alt_).astype(f32)[..., None]
        self.nz = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.nights = {k: self.night_grad(S) for k, S in SC.items()}
        self.mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        z = np.load(os.path.join(SCR, "stars.npz")); keep = z["mag"] < 6.5
        V = z["mag"][keep]; o = np.argsort(V)
        self.hyg = dict(d=eq_vec(z["ra"][keep], z["dec"][keep])[o], V=V[o], fd=disp_flux(V[o]),
                        col=star_rgb(np.clip(bv_temp(np.clip(z["ci"][keep], -0.4, 2.0)), 2600, 30000))[o],
                        ph=np.random.default_rng(3).uniform(0, 1000, len(V)).astype(f32))
        m = np.load(os.path.join(SCR, "m31.npz"))
        img = m["img"].astype(f32); self.K = float(m["K"]); self.mc = m["c"].astype(np.float64)
        self.pyr = [img]
        for _ in range(5): self.pyr.append(cv2.pyrDown(self.pyr[-1]))
        self.neb = np.load(NEB)["neb"].astype(f32)
        r = np.random.default_rng(23)
        n = 900; self.yb = dict(x=r.uniform(0, W, n).astype(f32), y=(r.uniform(0, 1, n) ** 1.3 * (self.hz - 40)).astype(f32),
                                fd=(r.pareto(1.6, n) * 0.5 + 0.2).astype(f32), ph=r.uniform(0, 100, n).astype(f32))
        r2 = np.random.default_rng(29); n2 = 2600
        self.old = dict(x=r2.uniform(0, W, n2).astype(f32), y=r2.uniform(0, H, n2).astype(f32), fd=(r2.pareto(2.2, n2) * 0.3 + 0.08).astype(f32),
                        ph=r2.uniform(0, 100, n2).astype(f32))
        self.tw = (fbm2((512, 512), 41, 2.6), fbm2((512, 512), 42, 2.6))
        rr = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 9 + rr.uniform(-0.2, 0.2), w=rr.uniform(0.10, 0.20), I=rr.uniform(0.7, 1.2), hue=rr.uniform(0, 1),
                           ph=rr.uniform(0, 6.28), sp=rr.uniform(0.6, 1.4)) for i in range(9)]
        # ---- yard: night base, lit albedo, rim; the string lights and the window
        a = fg.a; self.a = a[..., None]
        rgb = fg.rgb; f = fg.flat; y = lum(f)[..., None]
        mxc = rgb.max(2); warm = rgb[..., 0] - rgb[..., 2]
        win = (smooth(0.30, 0.75, mxc) * smooth(0.05, 0.20, warm) * (yy > 1100)).astype(f32)
        self.win = win
        self.lights = (rgb * win[..., None] * 3.0 + win[..., None] * np.array([0.30, 0.14, 0.03], f32)).astype(f32)
        glow = cv2.GaussianBlur(win, (0, 0), 6) * 0.5 + cv2.GaussianBlur(win, (0, 0), 25) * 0.6
        self.lglow = (glow[..., None] * np.array([1.0, 0.55, 0.20], f32) * 0.35).astype(f32)
        self.base = ((f * 0.35 + y * 0.65) * np.array([0.30, 0.36, 0.75], f32) * 0.12 * (1 - win[..., None])).astype(f32)
        self.alb = np.clip(f * 0.8 + y * 0.2, 0, 1).astype(f32) * (1 - win[..., None])
        sk = np.clip((self.hz + 150 - yy) / (self.hz + 150 - fg.skyline.min()), 0, 1)
        self.skyfac = (0.40 + 0.60 * sk)[..., None].astype(f32)
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a)[..., None].astype(f32)
        emph = {"SMUDGE", "ANDROMEDA", "6", "HEADING", "TWO", "BILLION", "10", "LOOMS", "SKY", "COLLIDE", "CRASHES", "IGNITE",
                "EVERYWHERE", "NEVER", "MILKOMEDA", "GIANT", "DYING", "HAPPEN", "COIN", "FLIP"}
        self.caps = Captions(L, WORDS, emphasis=emph)

    def night_grad(self, S):
        e = self.e; k = np.exp(-e / 0.30)[..., None]
        n = np.array(S["zen"], f32) * (1 - k) + np.array(S["hor"], f32) * k
        n = n + np.exp(-e / 0.10)[..., None] * np.array([0.03, 0.018, 0.012], f32)                   # suburban light dome
        return (n * (1 + 0.06 * self.nz)[..., None]).astype(f32)

    def LST(self, t): return self.L0 + LRATE * (t if t < T_BACK else t - DUR - 1 / FPS)
    def M(self, lst): return eq2hor(lst)
    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- M31 geometry on screen
    def m31_frame(self, lst):
        """screen position of the nucleus and screen unit vectors of sky east / north at it (px per degree)"""
        ra, de = map(math.radians, M31); e0 = eq_vec(*M31)
        north = np.array([-math.sin(de) * math.cos(ra), -math.sin(de) * math.sin(ra), math.cos(de)])
        east = np.array([-math.sin(ra), math.cos(ra), 0.0]); dd = math.radians(0.2)
        pts = np.stack([e0, e0 + dd * east, e0 + dd * north]); pts /= np.linalg.norm(pts, axis=1, keepdims=True)
        x, y, _ = self.lens.project(pts @ self.M(lst).T)
        E = np.array([x[1] - x[0], y[1] - y[0]]) / 0.2; N = np.array([x[2] - x[0], y[2] - y[0]]) / 0.2
        return float(x[0]), float(y[0]), E, N

    def m31_draw(self, lst, scale, gain, swirl=0.0, t=0.0):
        """draw the GALEX sprite at `scale` x its true size today; returns HDR layer (full res)"""
        W, H = self.L.W, self.L.H
        x0, y0, E, N = self.m31_frame(lst)
        k = scale / self.K                                         # screen px per sprite px (per degree ratio)
        lev = 0
        while lev < len(self.pyr) - 1 and k * PXDEG * 2 ** (lev + 1) < 1.1: lev += 1
        img = self.pyr[lev]; f = 2 ** lev
        # sprite x = west (-east), y = south (-north)
        A = np.array([[-E[0], -N[0]], [-E[1], -N[1]]]) * k * f
        c = self.mc / f
        Mx = np.float32([[A[0, 0], A[0, 1], x0 - (A[0, 0] * c[0] + A[0, 1] * c[1])], [A[1, 0], A[1, 1], y0 - (A[1, 0] * c[0] + A[1, 1] * c[1])]])
        out = cv2.warpAffine(img, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if swirl > 0:                                              # tidal twist about the nucleus (stronger inside)
            dx, dy = self.xx - x0, self.yy - y0; d = np.sqrt(dx * dx + dy * dy) + 1e-3
            R0 = D25 * PXDEG * scale * 0.5
            ang = swirl * 1.3 * np.exp(-d / (R0 * 0.9)) + 0.05 * math.sin(t * 0.5)
            ca, sa = np.cos(ang), np.sin(ang)
            sx = x0 + dx * ca - dy * sa * 1.15; sy = y0 + dx * sa * 0.85 + dy * ca
            out = cv2.remap(out, sx.astype(f32), sy.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        # outer stellar disc + halo (camera view), on the same axis
        ax = np.array([-math.sin(math.radians(35)), -math.cos(math.radians(35))])          # PA 35 deg in sprite axes
        maj = A @ ax; maj /= np.linalg.norm(maj)
        dx, dy = self.hx - x0, self.hy - y0
        u = (dx * maj[0] + dy * maj[1]) / (PXDEG * scale); v = (-dx * maj[1] + dy * maj[0]) / (PXDEG * scale)
        rr = np.sqrt(u * u + (v / 0.35) ** 2); rh = np.sqrt(u * u + v * v)
        outer = (np.exp(-rr / 1.0) * 0.16 + np.exp(-rh / 2.2) * 0.03)[..., None] * np.array([0.55, 0.68, 1.0], f32)
        return (out + self.up(outer)) * gain, (x0, y0, maj)

    def tails(self, x0, y0, maj, scale, I, t):
        """two curved tidal tails from the disc ends (half res)"""
        acc = np.zeros(self.hx.shape, f32)
        L = D25 * PXDEG * scale
        for sgn in (-1, 1):
            pts = []
            for s in np.linspace(0.45, 2.2, 60):
                a = sgn * (s * 0.9)
                d = np.array([maj[0] * math.cos(a) - maj[1] * math.sin(a), maj[0] * math.sin(a) + maj[1] * math.cos(a)]) * sgn
                pts.append((x0 + d[0] * L * s * 0.7, y0 + d[1] * L * s * 0.7, s))
            for (px, py, s) in pts[::2]:
                acc += np.exp(-((self.hx - px) ** 2 + (self.hy - py) ** 2) / (2 * (L * 0.06 * (0.6 + s)) ** 2)) * (1.2 - 0.45 * s)
        n = cv2.remap(self.tw[0], (self.hx * 0.3 % 512).astype(f32), (self.hy * 0.3 % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        return (np.clip(acc, 0, 3) * (0.7 + 0.3 * n) * 0.10 * I)[..., None] * np.array([0.6, 0.72, 1.0], f32)

    # -------------------------------------------------------------------------------------------- base layers
    def mw_layer(self, lst, warp=0.0, gain=5.0, t=0.0):
        Mg = EQ2GAL @ self.M(lst).T
        g = self.rays_h @ Mg.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        if warp > 0:                                              # the Milky Way's disc bends and flares
            b = b + warp * (0.25 * np.sin(2 * l + 0.3 * t) + 0.12 * np.sin(3 * l + 1.0))
        mx = (WL / 2 + np.degrees(l) * CPXD) % WL; my = HB / 2 - np.degrees(b) * CPXD
        return self.up(cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)) * gain

    def stars_layer(self, t, lst, gain=1.0):
        L = self.L; W, H = L.W, L.H; s = self.hyg
        h = s["d"] @ self.M(lst).T
        vis = np.where(h[:, 2] > -0.01)[0]; h = h[vis]
        x, y, ok = self.lens.project(h)
        sel = ok & (x > -2) & (x < W + 1) & (y > -2) & (y < H + 1)
        idx = vis[sel]; x = x[sel]; y = y[sel]; zz = h[sel, 2]
        ph = s["ph"][idx]
        nt = np.sin(t * 13.1 + ph) * 0.5 + np.sin(t * 23.7 + ph * 1.7) * 0.3 + np.sin(t * 37.3 + ph * 2.3) * 0.2
        sig = np.clip(0.10 + 0.35 * np.exp(-zz / 0.15), 0.08, 0.6)
        fd = s["fd"][idx] * np.exp(sig * nt * 1.6 - 0.5 * sig * sig) * np.clip(zz / 0.12, 0, 1) ** 0.7 * gain
        return self.splat_pts(x, y, fd, s["col"][idx], t, ph)

    def splat_pts(self, x, y, fd, col, t, ph, ng=20, gth=6.0):
        W, H = self.L.W, self.L.H
        core = np.minimum(fd, 5.0)
        acc = np.zeros(((H + 2) * (W + 2), 3), f32)
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64); fx = x - x0; fy = y - y0
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            li = np.clip(y0 + dy, 0, H + 1) * (W + 2) + np.clip(x0 + dx, 0, W + 1); w_ = core * wg
            for c in range(3): acc[:, c] += np.bincount(li, weights=w_ * col[:, c], minlength=(H + 2) * (W + 2)).astype(f32)
        acc = acc.reshape(H + 2, W + 2, 3)[:H, :W]
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = acc * (acc.max(2, keepdims=True) > 0.35)
        st += cv2.GaussianBlur(big, (0, 0), 2.2) * 1.6
        for j in list(np.argsort(-fd)[:ng]):
            g = fd[j]
            if g < gth: continue
            c = col[j] * 0.85 + 0.15; Lk = min(6 + 7 * math.log(g / 6 + 1) ** 1.2, 40.0)
            a = min(g, 150.0) ** 0.8 * 0.06 * (1 + 0.25 * math.sin(t * 5 + ph[j]))
            splat(st, x[j], y[j], int(Lk * 4) + 6, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / Lk) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / Lk)) * a)[..., None] * c)
        return st

    def starburst(self, t, I):
        """pink H II regions + blue young stars across the sky (screen space, drifting)"""
        W, H = self.L.W, self.L.H
        u = ((self.xx * 0.9 + 300 + t * 6) % 2048).astype(f32); v = ((self.yy * 0.9 + 200) % 2048).astype(f32)
        neb = cv2.remap(self.neb, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * 3.0
        b = self.yb; x = (b["x"] + t * 4) % W
        col = np.tile(np.array([[0.55, 0.75, 1.0]], f32), (len(x), 1))
        tw = 1 + 0.3 * np.sin(t * 9 + b["ph"])
        return neb * I + self.splat_pts(x, b["y"], b["fd"] * tw * 6 * I, col, t, b["ph"], ng=25, gth=4.0)

    def milkomeda(self, t, I):
        W, H = self.L.W, self.L.H
        cx, cy = 540.0, 640.0
        a = math.radians(-24 + 1.5 * math.sin(t * 0.2))
        dx, dy = self.hx - cx, self.hy - cy
        u = (dx * math.cos(a) + dy * math.sin(a)) / 760; v = (-dx * math.sin(a) + dy * math.cos(a)) / (760 * 0.68)
        r = np.sqrt(u * u + v * v) + 1e-4
        sb = np.exp(-7.67 * (r ** 0.25 - 1)) * 0.07                    # de Vaucouleurs r^1/4 profile
        sb = np.minimum(sb, 3.0)
        col = np.array([1.0, 0.80, 0.55], f32) * (1 - np.clip(r, 0, 1)[..., None] * 0.25) + np.array([0.3, 0.3, 0.45], f32) * np.clip(r - 0.5, 0, 1)[..., None] * 0.3
        n = cv2.remap(self.tw[1], (self.hx * 0.25 % 512).astype(f32), (self.hy * 0.25 % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        dust = 1 - 0.35 * np.clip(n - 0.6, 0, 1) * np.exp(-r / 0.8)                          # fading remnant dust
        glow = self.up((sb * dust)[..., None] * col) * I
        o = self.old; tw = 1 + 0.25 * np.sin(t * 8 + o["ph"])
        cc = np.tile(np.array([[1.0, 0.82, 0.62]], f32), (len(o["x"]), 1))
        return glow + self.splat_pts(o["x"], o["y"], o["fd"] * tw * 3 * I, cc, t, o["ph"], ng=8, gth=3.0)

    # -------------------------------------------------------------------------------------------- sky of a scene
    def sky(self, key, t, lst):
        Y, _ = years(t) if scene_at(t)[0] == key else (YRS[key][0], 0)
        S = SC[key]; sky = self.nights[key].copy(); info = None
        if key in ("today", "g2", "g3"):
            sky += self.mw_layer(lst, gain=5.0 if key != "g3" else 6.5) + self.stars_layer(t, lst)
            sc = 770.0 / r_of(Y if key != "today" else 0.0)
            gain = {"today": 0.30, "g2": 1.2, "g3": 1.5}[key] * (1 + 0.03 * math.sin(t * 1.3))
            g, info = self.m31_draw(lst, sc, gain, swirl=0.25 if key == "g3" else 0.0, t=t)
            if key == "today":                                       # the eye view: a small faint smudge
                g = cv2.GaussianBlur(g, (0, 0), 1.5) * np.array([0.85, 0.9, 1.0], f32)
            sky += g
            if key == "g3": sky += self.up(self.tails(*info, sc, 1.0, t))
        elif key == "g4":
            sky += self.mw_layer(lst, warp=0.6, gain=7.0, t=t) + self.stars_layer(t, lst, 0.7)
            g, info = self.m31_draw(lst, 770.0 / 31.0, 1.2, swirl=1.0, t=t)
            sky += g + self.up(self.tails(*info, 770 / 31.0 * 0.5, 2.2, t)) + self.starburst(t, 1.0)
        elif key == "g5":
            sky += self.mw_layer(lst, warp=0.0, gain=0.6) + self.stars_layer(t, lst, 0.5) + self.milkomeda(t, 1.0)
        return sky * self.above + self.nights[key] * (1 - self.above), info

    def rays_fx(self, t, P, Q, w, cx, cy, I):
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
    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        lst = self.LST(t)
        cur, prev, t0, t1 = scene_at(t)
        P, Q = SC[prev], SC[cur]
        u = t - t0
        w = ramp(t, t0 - 0.05, t0 + 0.6) if t0 > 0 else 1.0
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.7) + sum(0.30 * math.exp(-((t - tp) / 0.22) ** 2) for tp in PULSES)
        cx, cy = self.m31_frame(lst)[:2]
        if cur == "g5": cx, cy = 540.0, 640.0
        sky, info = self.sky(cur, t, lst)
        if 0 <= u < REVEAL and t0 > 0:
            old, _ = self.sky(prev, t, lst)
            Rr = 2400 * (u / 1.4) ** 0.6
            dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
            m = smooth(Rr + 50, Rr - 50, dd)[..., None]
            sky = old * (1 - m) + sky * m
        sky = self.nights[cur] + (sky - self.nights[cur]) * (0.92 + 0.08 * pulse)
        if cur == "today" and t < T_SW["g2"]:
            self.hook_fx(sky, t, cx, cy, lst)
        if cur != "today":
            bI = Q["bI"] * (0.55 + 0.45 * ramp(u, 0, 0.6)) * (1 + 0.6 * math.exp(-max(u, 0) / 0.5))
            lay = self.rays_fx(t, P, Q, w, cx, cy, bI * 0.6)
            d = np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2)
            lay = lay + (np.exp(-d / 420) * 0.05 * Q["I"])[..., None] * np.array(Q["lc"], f32)
            sky = sky + self.up(lay * pulse) * self.above
        # ---- yard relit by the sky; string lights + window always on
        lw = (Q["I"] * w + P["I"] * (1 - w)) * (0.9 + 0.1 * pulse)
        lcol = np.array(Q["lc"], f32) * w + np.array(P["lc"], f32) * (1 - w)
        fgc = self.base * (0.8 + 2.0 * lw) + self.alb * self.skyfac * lcol * lw * 0.5 + self.rim * lcol * (0.25 + 1.2 * lw) * 0.5
        fl = 1 + 0.05 * math.sin(t * 7.3) + 0.03 * math.sin(t * 13.1)
        fgc = fgc + self.lights * fl
        img = sky * (1 - self.a) + fgc * self.a + self.lglow * fl
        for ts, k in SWAPS:
            uu = t - ts
            if -0.05 < uu < 1.4:
                fc = 0.45 + 0.55 * np.array(SC[k]["lc"], f32) / max(SC[k]["lc"])
                img += (2.0 * math.exp(-max(uu, 0) / 0.09) * ease((uu + 0.05) / 0.05)) * fc
                if k == "today": continue
                pc = (540.0, 640.0) if k == "g5" else self.m31_frame(self.LST(ts))[:2]
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
        self.overlay(out, t, cur, t0, t1, lst, cx, cy)
        return out

    def hook_fx(self, sky, t, cx, cy, lst):
        """six real-size full Moons laid along Andromeda's length while '6 full Moons' is said"""
        if not (T_MOONS - 0.1 < t < T_MOONS1 + 0.6): return
        x0, y0, E, N = self.m31_frame(lst)
        pa = math.radians(35); d = np.array([math.sin(pa) * E[0] + math.cos(pa) * N[0], math.sin(pa) * E[1] + math.cos(pa) * N[1]])
        d /= np.linalg.norm(d)
        fo = 1 - ramp(t, T_MOONS1 + 0.1, T_MOONS1 + 0.5)
        for i in range(6):
            off = (i - 2.5) * MOON_PX
            a = ramp(t, T_MOONS + 0.12 * i, T_MOONS + 0.12 * i + 0.15) * fo
            if a <= 0.01: continue
            mx, my = x0 + d[0] * off, y0 + d[1] * off
            splat(sky, mx, my, 40, lambda dd, dx, dy: (np.clip(MOON_PX / 2 - dd + 0.5, 0, 1) * 1.6 * a + np.exp(-np.maximum(dd - MOON_PX / 2, 0) / 6) * 0.12 * a)[..., None] * np.array([0.95, 0.95, 1.0], f32))

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

    def overlay(self, out, t, cur, t0, t1, lst, cx, cy):
        L = self.L; W = L.W
        # ---- the YEAR counter (always on)
        Y, shown = years(t)
        if cur == "today": shown = 0.0
        wo = 1 - ramp(t, T_WO0, T_WO0 + 0.3) + ramp(t, T_BACK, T_BACK + 0.3)
        put_glow(out, glow_text("YEAR" if shown < 0.005 else "YEARS FROM NOW", 42, (200, 225, 255)), W / 2, 192, 0.95 * min(wo, 1), 0.35)
        put_glow(out, glow_text(fmt_years(shown), 104, (255, 190, 90) if shown > 0.005 else (170, 210, 255)), W / 2, 270, min(wo, 1), 0.5)
        # ---- readout
        Q = END if (cur == "today" and t >= T_BACK) else SC[cur]
        if cur == "today":
            a = ramp(t, 0.5, 0.85) * (1 - ramp(t, T_SW["g2"] - 0.4, T_SW["g2"] - 0.15)) if t < T_SW["g2"] else ramp(t, T_BACK + 0.4, T_BACK + 0.75)
        else:
            a = ramp(t, t0 + 0.15, t0 + 0.45) * (1 - ramp(t, t1 - 0.35, t1 - 0.15)) * (1 - ramp(t, T_WO0, T_WO0 + 0.3))
        if a > 0.01:
            x, ys = W / 2, (372, 430, 470, 510); dy = (1 - a) * 18
            rgba, _ = word_layer(Q["name"], int(L.hud_size * 0.95), W * 0.9, fill=Q["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            cols = ((255, 222, 120), (255, 255, 255), (200, 225, 255))
            for j, line in enumerate(Q["l"]):
                hud_text(out, line, x, ys[j + 1] + dy, int(L.hud_size * 0.50), "Black", cols[j], a, 0.05, display=True)
        # ---- pointer ring + label on the smudge (opening and loop ending)
        if cur == "today":
            ar = ramp(t, 0.2, 0.5) * (1 - ramp(t, T_SW["g2"] - 0.5, T_SW["g2"] - 0.2)) if t < T_SW["g2"] else ramp(t, T_BACK + 0.4, T_BACK + 0.8)
            if ar > 0.01:
                pr = 52 + 3 * math.sin(t * 5); ov = np.zeros_like(out[..., 0])
                cv2.circle(ov, (int(cx * 4), int(cy * 4)), int(pr * 4), 1.0, 2, cv2.LINE_AA, shift=2)
                ov = cv2.GaussianBlur(ov, (0, 0), 0.6) * ar
                out[:] = out * (1 - ov[..., None] * 0.9) + ov[..., None] * 0.9 * np.array([0.85, 0.95, 1.0], f32)
                am = ramp(t, T_MOONS + 0.75, T_MOONS + 0.95) * (1 - ramp(t, T_MOONS1 + 0.1, T_MOONS1 + 0.5))
                if am > 0.01: hud_text(out, "6 FULL MOONS", cx, cy + 78, 34, "Black", (255, 222, 120), am, 0.08, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "info":
        print("DUR", DUR, {k: round(v, 2) for k, v in T_SW.items()}, "wo", round(T_WO0, 2), "back", round(T_BACK, 2))
        for Y in (0, 2.0, 3.75, 3.9):
            r = r_of(Y); print(f"Y {Y}: {r} kpc = {r * 3261.56 / 1e6:.2f} Mly; bright disc {2 * math.degrees(math.atan(21.7 / r)):.1f} deg = "
                               f"{2 * math.degrees(math.atan(21.7 / r)) / 0.52:.0f} full Moons")
        sys.exit()
    if sys.argv[1] == "stills":
        sc = Scene(True); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in [float(x) for x in sys.argv[2].split(",")]:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
