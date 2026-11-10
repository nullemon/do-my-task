"""YOUR NIGHT SKY IN 1 MILLION YEARS -- vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the user's park plate (A2_park.png: big tree, conifer, house, street lamps) at night.
The sky is the real HYG v4.1 sky (catalog.py): every star moves on a straight line in 3D with its real proper motion,
radial velocity and distance, so positions AND magnitudes change (approaching stars brighten, receding ones fade).
The Earth's daily turning is frozen; only stellar motion shows. A big glowing counter runs YEAR 2026 -> 1,291,xxx.
  hook    the Big Dipper (glowing stick figure) over the park, YEAR 2026
  ff      fast-forward starts: every star streaks; Barnard's Star shoots across the sky (passes ~3.8 ly from us ~11,700 AD)
  dip     velocity arrows: 5 Ursa Major Moving Group stars move together, Dubhe + Alkaid go their own way; the lines
          stretch like rubber bands and snap ("broken")
  orion   sweep to Orion (250,000 -> 1,000,000 AD): the shoulders drift apart and snap, Sirius moves off and fades
  gj      sweep to Gliese 710: it brightens to mag -3 and streaks across as it passes ~10,500 au from the Sun (1.29 Myr)
  end     back to the Dipper's place: the 7 Dipper stars' million-year paths fan out over the sky ("temporary"); then a
          rewind to 2026 (everything races back), the Dipper re-forms with a flash = first frame (loops)
Views: each featured region is shown with a fixed sky orientation; between them the celestial sphere swings along the
shortest rotation (a stylised sweep -- the camera itself never moves).
Built on docs-series/shorts/lib (read-only). Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image, ImageDraw
from scipy.interpolate import PchipInterpolator
from lib.core import f32, Layout, ramp, smooth, ease, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, font
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import Lens, view_R, slerp_R, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S10-sky-1myr"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
LAMPS_SRC = [(193, 1198, 1325), (666, 1207, 1322), (816, 1113, 1323)]   # SOURCE px (as measured for ../gamma-ray-eyes)
FPS = 30
LEAD = 0.25
YEAR_NOW = 2026
T_PERI = 1.29e6                                          # Gliese 710 closest approach (yr from now, Gaia DR3)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t1" if end else "t0"]

# ------------------------------------------------------------------------------------------------- timeline
T_FF0 = LN["ff"]["start"] - 0.05                         # counter starts on "Every star is moving"
T_SW2 = LN["orion"]["start"] - 0.50                      # sweep Dipper -> Orion
T_SW3 = LN["gj"]["start"] - 0.25                         # sweep Orion -> Gliese 710
T_SW4 = LN["end"]["start"] - 0.55                        # sweep back to the Dipper's place
SWEEP = 0.95
T_RW0 = wt("end", "TEMPORARY") + 0.42                    # rewind to 2026
T_RW1 = T_RW0 + 1.15
DUR = round(T_RW1 + 0.75, 2)
T_BROKEN = wt("dip", "BROKEN")
T_APART = wt("orion", "APART")
T_DIP_LBL = wt("hook", "BIG")

E_KEYS_A = [(0.0, 0.0), (T_FF0, 0.0), (wt("ff", "BARNARD'S"), 3500.0), (wt("ff", "FASTEST"), 9000.0),
            (LN["ff"]["end"] + 0.1, 24000.0), (wt("dip", "TOGETHER"), 38000.0), (wt("dip", "DUBHE"), 58000.0),
            (wt("dip", "100,000"), 100000.0), (T_BROKEN, 150000.0), (T_SW2, 180000.0), (T_SW2 + SWEEP, 255000.0),
            (T_APART, 480000.0), (T_SW3 + 0.05, 1000000.0)]
D_KEYS = [(T_SW3 + 0.05, T_PERI - 1000000.0), (wt("gj", "MILLION"), 40000.0), (wt("gj", "GLIESE 710"), 4000.0),
          (wt("gj", "SKIMS"), 2400.0), (wt("gj", "SUN"), 1800.0), (wt("gj", "BRIGHTER"), 1350.0), (LN["gj"]["end"], 1150.0),
          (T_RW0, 1100.0)]
_ea = PchipInterpolator([k[0] for k in E_KEYS_A], [math.log10(k[1] + 300.0) for k in E_KEYS_A])
_ed = PchipInterpolator([k[0] for k in D_KEYS], [math.log10(k[1]) for k in D_KEYS])
E_RW_END = T_PERI - 1100.0


def E_of(t):
    """years after 2026 shown at video time t"""
    if t <= T_FF0: return 0.0
    if t < E_KEYS_A[-1][0]: return max(0.0, 10 ** float(_ea(t)) - 300.0)
    if t < T_RW0: return T_PERI - 10 ** float(_ed(min(t, T_RW0)))
    if t < T_RW1:                                          # rewind: log-fast back to 0
        u = ease((t - T_RW0) / (T_RW1 - T_RW0))
        return max(0.0, 10 ** ((1 - u) * math.log10(E_RW_END + 300.0) + u * math.log10(300.0)) - 300.0)
    return 0.0


def shutter(t):
    """motion-trail length (video seconds)"""
    s = 1 / 60 + 0.16 * ramp(t, T_FF0, T_FF0 + 1.0) + 0.08 * ramp(t, LN["dip"]["start"], LN["dip"]["start"] + 1)
    s -= 0.10 * ramp(t, T_SW4 + SWEEP, T_SW4 + SWEEP + 0.4)
    s += 0.22 * ramp(t, T_RW0 - 0.1, T_RW0 + 0.2) * (1 - ramp(t, T_RW1 - 0.15, T_RW1))
    return max(s * (1 - ramp(t, T_RW1 - 0.1, T_RW1)), 1 / 60)


# featured stars (HIP)
HIPS = dict(dubhe=54061, merak=53910, phecda=58001, megrez=59774, alioth=62956, mizar=65378, alkaid=67301,
            bet=27989, bel=25336, mint=25930, alnil=26311, alnit=26727, saiph=27366, rigel=24436, meissa=26207,
            sirius=32349, barn=87937, gj=89825)
GROUP = ("merak", "phecda", "megrez", "alioth", "mizar")            # Ursa Major Moving Group (Collinder 285 core)
DIP = [("dubhe", "merak"), ("merak", "phecda"), ("phecda", "megrez"), ("megrez", "dubhe"), ("megrez", "alioth"),
       ("alioth", "mizar"), ("mizar", "alkaid")]
ORI = [("meissa", "bet"), ("meissa", "bel"), ("bet", "alnit"), ("bel", "mint"), ("mint", "alnil"), ("alnil", "alnit"),
       ("alnit", "saiph"), ("mint", "rigel")]
SNAPS = {("megrez", "dubhe"): T_BROKEN - 0.05, ("dubhe", "merak"): T_BROKEN + 0.10, ("mizar", "alkaid"): T_BROKEN + 0.25,
         ("bet", "alnit"): T_APART - 0.05, ("bel", "mint"): T_APART + 0.12}
CYAN, ORANGE_C, MAG_C, GOLD, VIOLET, RED, ICE = ((0.30, 0.85, 1.0), (1.0, 0.52, 0.12), (1.0, 0.30, 0.80), (1.0, 0.75, 0.25),
                                                  (0.70, 0.45, 1.0), (1.0, 0.25, 0.20), (0.60, 0.80, 1.0))


def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def bv_temp(ci):
    return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


def fmt_int(n): return f"{int(round(n)):,}"


def win(d, rad): return np.clip(1 - (d / rad) ** 2, 0, 1) ** 2          # smooth splat edge (no square cut-offs)


# ------------------------------------------------------------------------------------------------- glowing text
_gl = {}
def glow_text(txt, size, col, wt="Black", maxw=None):
    """big glowing text -> (rgba uint8, glow rgb, dark backing, width). White-hot fill, coloured edge + halo."""
    k = (txt, int(size), col, wt, maxw)
    if k in _gl: return _gl[k]
    f = font(size, wt, True); w = f.getlength(txt)
    if maxw and w > maxw: f = font(int(size * maxw / w), wt, True); w = f.getlength(txt)
    asc, desc = f.getmetrics(); pad = int(f.size * 1.0) + 4
    Wd, Hd = int(w + 2 * pad), int(asc + desc + 2 * pad)
    sw = max(2, int(f.size * 0.045))
    m = Image.new("L", (Wd, Hd), 0); ImageDraw.Draw(m).text((pad, pad), txt, font=f, fill=255)
    ms = Image.new("L", (Wd, Hd), 0); ImageDraw.Draw(ms).text((pad, pad), txt, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    c255 = np.array(col, f32) * 255
    rgba = np.zeros((Hd, Wd, 4), f32)
    a_s = np.asarray(ms, f32) / 255; a_f = np.asarray(m, f32) / 255
    grad = np.linspace(1.0, 0.0, Hd)[:, None, None]
    fill = (np.array([255, 255, 255], f32) * 0.62 + c255 * 0.38) * (0.85 + 0.15 * grad) + c255 * 0.10 * (1 - grad)
    rgba[..., :3] = c255 * (1 - a_f[..., None]) + np.clip(fill, 0, 255) * a_f[..., None]
    rgba[..., 3] = a_s * 255
    halo = cv2.GaussianBlur(a_s, (0, 0), f.size * 0.16) * 0.9 + cv2.GaussianBlur(a_s, (0, 0), f.size * 0.45) * 0.6
    glow = halo[..., None] * np.array(col, f32)
    sh = cv2.GaussianBlur(a_s, (0, 0), f.size * 0.10)
    if len(_gl) > 600: _gl.clear()
    _gl[k] = (rgba.astype(np.uint8), glow.astype(f32), sh.astype(f32), w)
    return _gl[k]


def put_glow(dst, layer, cx, cy, alpha, glow_k=0.9):
    rgba, glow, sh, _ = layer
    h, w = rgba.shape[:2]; H, W = dst.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya or alpha <= 0.003: return
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    reg = dst[ya:yb, xa:xb]
    reg *= (1 - 0.45 * sh[sl] * alpha)[..., None]
    reg += glow[sl] * glow_k * alpha
    a = rgba[sl][..., 3:].astype(f32) / 255 * alpha
    dst[ya:yb, xa:xb] = np.clip(reg * (1 - a) + rgba[sl][..., :3].astype(f32) / 255 * a, 0, 1)


def put_glow_digits(dst, txt, size, col, cx, cy, alpha):
    """tabular placement for the counter: every glyph cached, fixed advance -> digits don't jitter"""
    adv = size * 0.62; comma = size * 0.30
    widths = [comma if c == "," else adv for c in txt]
    x = cx - sum(widths) / 2
    for c, w in zip(txt, widths):
        put_glow(dst, glow_text(c, size, col), x + w / 2, cy, alpha, glow_k=0.8)
        x += w


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H
        self.v = vertical
        self.fg = Foreground(FG_PATH, L, lamps=LAMPS_SRC, hz_frac=0.84)
        self.hz = self.fg.horizon
        f = 1320.0 if vertical else 1100.0                                   # 9:16: a longer lens (bigger Dipper on phones)
        self.lens = Lens(W, H, 180.0, 50.0, f, self.hz + 10)
        self.sc = 1.0 if vertical else 0.9
        if vertical:
            L.cap_y = 1330
            self.counter_xy = (W / 2, 315)
            V = [(660, 1150, 12.3 * 15, 56.0, 6.0), (720, 830, 5.6 * 15, 0.0, 0.0), (720, 960, 221.0, -1.1, -72.0)]
        else:
            L.cap_y = 880; L.cap_size = 100
            self.counter_xy = (520, 175)
            V = [(1330, 690, 12.3 * 15, 56.0, 38.0), (1400, 450, 5.6 * 15, 0.0, 0.0), (1250, 680, 221.0, -1.1, -80.0)]
        self.views = [view_R(self.lens, *v) for v in V]
        self.mx = int(0.07 * W)
        self.caps = Captions(L, WORDS, emphasis={"FIXED", "BIG", "DIPPER", "MOVING", "BARNARD'S", "FASTEST", "FAMILY", "DUBHE",
                                                 "ALKAID", "100,000", "BROKEN", "ORION'S", "APART", "FADE", "1.3", "MILLION",
                                                 "GLIESE 710", "BLAZING", "TEMPORARY"})
        self.rays = self.lens.rays(1)
        alt = np.arcsin(np.clip(self.rays[..., 2], -1, 1)).astype(f32)
        e = np.clip(alt / (np.pi / 2), 0, 1)
        k = np.exp(-e / 0.28)[..., None]
        zen = np.array([0.011, 0.008, 0.068], f32); hor = np.array([0.030, 0.040, 0.190], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.40) / 0.22) ** 2)[..., None] * np.array([0.020, 0.003, 0.034], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        self.above = smooth(-0.01, 0.05, alt).astype(f32)[..., None]
        yy = np.arange(H, dtype=f32)[:, None] * np.ones((1, W), f32)
        self.above = np.minimum(self.above, smooth(self.hz + 30, self.hz - 40, yy)[..., None]).astype(f32)
        fg = self.fg; fl = fg.flat; y = lum(fl)[..., None]
        self.fg_night = ((fl * 0.40 + y * 0.60) * np.array([0.17, 0.18, 0.46], f32) * 0.85).astype(f32)
        self.a = fg.a[..., None]
        # catalogue
        z = np.load(os.path.join(SCR, "moving.npz"))
        self.pos = z["pos"].astype(np.float64); self.vel = z["vel"].astype(np.float64); self.absm = z["absm"]
        T = np.clip(bv_temp(np.clip(z["ci"], -0.4, 2.0)), 2600, 30000)
        cols = np.stack([bbcolor(x) for x in T]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = yv[:, None] + (cols - yv[:, None]) * 1.7
        cols = np.clip(cols, 0.02, None); cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.ph = np.random.default_rng(3).uniform(0, 1000, len(self.absm)).astype(f32)
        hip = list(z["hip"]); self.ix = {k: hip.index(h) for k, h in HIPS.items()}
        self.special = np.array([self.ix["barn"], self.ix["gj"]])
        self.mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        self._mwc = (None, None)
        self.xx = None
        # reference (2026) lengths of the stick-figure lines
        u0 = self.dirs_of(np.arange(len(self.absm)), 0.0)[0]
        self.L0 = {s: float(np.arccos(np.clip(u0[self.ix[s[0]]] @ u0[self.ix[s[1]]], -1, 1))) for s in DIP + ORI}

    # ----------------------------------------------------------------------------------------------- geometry
    def dirs_of(self, idx, E):
        p = self.pos[idx] + self.vel[idx] * E
        d = np.linalg.norm(p, axis=-1)
        return p / d[..., None], self.absm[idx] + 5 * np.log10(d / 10)

    def R_of(self, t):
        V1, V2, V3 = self.views
        if t < T_SW2: return V1
        if t < T_SW2 + SWEEP: return slerp_R(V1, V2, ease((t - T_SW2) / SWEEP))
        if t < T_SW3: return V2
        if t < T_SW3 + SWEEP: return slerp_R(V2, V3, ease((t - T_SW3) / SWEEP))
        if t < T_SW4: return V3
        if t < T_SW4 + SWEEP: return slerp_R(V3, V1, ease((t - T_SW4) / SWEEP))
        return V1

    def proj(self, u, R):
        h = u @ R.T
        x, y, ok = self.lens.project(h)
        return x, y, ok

    def star_xy(self, key, t, E=None):
        E = E_of(t) if E is None else E
        u, m = self.dirs_of(np.array([self.ix[key]]), E)
        x, y, ok = self.proj(u, self.R_of(t))
        return float(x[0]), float(y[0]), bool(ok[0]), float(m[0])

    def view_w(self, t, which):
        """visibility weight of view 1/2/3 at time t (0..1)"""
        if which == 1: return max(1 - ramp(t, T_SW2, T_SW2 + 0.5), ramp(t, T_SW4 + 0.5, T_SW4 + SWEEP))
        if which == 2: return ramp(t, T_SW2 + 0.4, T_SW2 + SWEEP) * (1 - ramp(t, T_SW3, T_SW3 + 0.5))
        return ramp(t, T_SW3 + 0.4, T_SW3 + SWEEP) * (1 - ramp(t, T_SW4, T_SW4 + 0.5))

    # ----------------------------------------------------------------------------------------------- layers
    def mw_layer(self, R):
        key = R.round(7).tobytes()
        if self._mwc[0] == key: return self._mwc[1]
        M = EQ2GAL @ R.T
        g = self.rays @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        out = cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        self._mwc = (key, out)
        return out

    def stars_layer(self, t, rewind):
        """every star, multi-sampled over the shutter in (years, sky orientation): glowing streaks with bright heads"""
        L = self.L; W, H = L.W, L.H
        sh = shutter(t)
        N = len(self.absm); allidx = np.arange(N)
        u1, m1 = self.dirs_of(allidx, E_of(t))
        vis = np.where(m1 < 7.3)[0]
        vis = vis[~np.isin(vis, self.special)]
        bright = vis[m1[vis] < 5.4]
        R1 = self.R_of(t); R0 = self.R_of(t - sh); E0 = E_of(t - sh)
        ua, _ = self.dirs_of(bright, E0)
        xa, ya, _ = self.proj(ua, R0); xb, yb, okb = self.proj(u1[bright], R1)
        m_ = okb & (xb > 0) & (xb < W) & (yb > 0) & (yb < H)
        disp = float(np.percentile(np.hypot(xb - xa, yb - ya)[m_], 92)) if m_.sum() > 5 else 0.0
        K = int(np.clip(disp / 1.3, 1, 64))
        XS, YS, VS = [], [], []
        for k in range(K):
            u = (k + 1.0) / K
            tk = t - sh * (1 - u)
            idx = vis if k == K - 1 else bright
            if k == K - 1: uu, mm = u1[idx], m1[idx]
            else: uu, mm = self.dirs_of(idx, E_of(tk))
            x, y, ok = self.proj(uu, self.R_of(tk))
            sel = ok & (x > -2) & (x < W + 2) & (y > -2) & (y < H + 2)
            idx, x, y, mm = idx[sel], x[sel], y[sel], mm[sel]
            fl = 4.5 * 10 ** (-0.4 * 0.90 * np.minimum(mm, 9)) * smooth(7.3, 6.2, mm)
            nt = np.sin(t * 13.1 + self.ph[idx]) * 0.5 + np.sin(t * 23.7 + self.ph[idx] * 1.7) * 0.3
            fl = fl * np.exp(0.22 * nt)
            col = self.scol[idx]
            if K > 1:
                fl = fl * ((0.20 + 1.4 * u ** 1.5) * (2.6 / K ** 0.5) if k < K - 1 else 1.25)
                if k < K - 1:                                                  # trails pick up a little time-colour
                    if rewind > 0:
                        pc = palette((u * 0.8 + t * 0.9 + x / W * 0.4) % 1.0)
                        col = col * (1 - 0.8 * rewind) + pc * 1.5 * 0.8 * rewind
                    else:
                        col = col * 0.75 + np.array([0.45, 0.55, 1.0], f32) * 0.35
            XS.append(x); YS.append(y); VS.append(fl[:, None] * col)
        x = np.concatenate(XS); y = np.concatenate(YS); val = np.concatenate(VS).astype(np.float64)
        acc = np.zeros(((H + 2) * (W + 2), 3))
        x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            fi = np.clip(y0 + dy + 1, 0, H + 1) * (W + 2) + np.clip(x0 + dx + 1, 0, W + 1)
            v = val * wg
            for c in range(3): acc[:, c] += np.bincount(fi, v[:, c], minlength=(H + 2) * (W + 2))
        acc = acc.reshape(H + 2, W + 2, 3)[1:H + 1, 1:W + 1].astype(f32)
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = acc * (acc.max(2, keepdims=True) > 0.35)
        st += cv2.GaussianBlur(big, (0, 0), 2.2) * 2.2 + cv2.GaussianBlur(big, (0, 0), 8.0) * 2.0
        # 4-point glints on the brightest heads
        hb = vis[m1[vis] < 1.0]
        if len(hb):
            x, y, ok = self.proj(u1[hb], R1)
            for j in np.where(ok & (x > 0) & (x < W) & (y > 0) & (y < H))[0]:
                g = 4.5 * 10 ** (-0.4 * 0.9 * m1[hb[j]]) * 0.05 * (1 + 0.3 * math.sin(t * 5 + self.ph[hb[j]]))
                c = self.scol[hb[j]] * 0.6 + 0.4
                splat(st, x[j], y[j], 60, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 16) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 16)) * g * win(d, 60))[..., None] * c)
        return st

    # ----------------------------------------------------------------------------------------------- featured FX
    def line4(self, fx, p, q, col, th):
        cv2.line(fx, (int(p[0] * 4), int(p[1] * 4)), (int(q[0] * 4), int(q[1] * 4)), tuple(float(c) for c in col), max(1, int(th)), cv2.LINE_AA, 2)

    def poly4(self, fx, pts, col, th):
        P = (np.asarray(pts) * 4).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(fx, [P], False, tuple(float(c) for c in col), max(1, int(th)), cv2.LINE_AA, 2)

    def burst(self, fx, x, y, u, col, big=1.0):
        """ring burst + flare, u = seconds since the event"""
        if not (0 <= u < 0.75): return
        sc = self.sc
        R = 12 + 150 * big * sc * (u / 0.75) ** 0.55
        k = (1 - u / 0.75) ** 1.8 * 3.0 * big
        for ch, off in ((0, 6), (1, 0), (2, -6)):
            c = [0.0, 0.0, 0.0]; c[ch] = float(k * (0.6 + 0.8 * col[ch]))
            cv2.circle(fx, (int(x * 4), int(y * 4)), int((R + off) * 4), tuple(c), max(2, int(5 * (1 - u))), cv2.LINE_AA, 2)
        fl = math.exp(-u / 0.12) * 22 * big
        col = np.array(col, f32)
        splat(fx, x, y, 160, lambda d, dx, dy: ((np.exp(-d / 3) * fl + np.exp(-d / 16) * fl * 0.12) * win(d, 160))[..., None] * (col * 0.6 + 0.4)
              + ((np.exp(-np.abs(dy) / 1.6) * np.exp(-np.abs(dx) / 60) + np.exp(-np.abs(dx) / 1.6) * np.exp(-np.abs(dy) / 60)) * fl * 0.08 * win(d, 160))[..., None] * col)

    def figure(self, fx, t, segs, base_col, alpha, labels):
        """rubber-band stick figure: tension colour + vibration, snaps at SNAPS times (halves recoil, sparks)"""
        E = E_of(t); R = self.R_of(t)
        keys = sorted({k for s in segs for k in s})
        idx = np.array([self.ix[k] for k in keys])
        u, _ = self.dirs_of(idx, E)
        x, y, ok = self.proj(u, R)
        P = {k: (x[i], y[i], ok[i], u[i]) for i, k in enumerate(keys)}
        relink = ramp(t, T_RW1 - 0.05, T_RW1 + 0.05)
        for s in segs:
            a, b = P[s[0]], P[s[1]]
            if not (a[2] and b[2]): continue
            Lc = float(np.arccos(np.clip(a[3] @ b[3], -1, 1)))
            st = Lc / self.L0[s]
            ts = SNAPS.get(s)
            tension = float(np.clip(abs(st - 1) / 0.30, 0, 1))
            if ts is not None: tension = max(tension, ramp(t, ts - 1.0, ts) * 0.9)
            col = np.array(base_col, f32)
            hot = np.array([1.0, 0.35, 0.75], f32) * (1 - tension) + np.array([1.0, 0.9, 0.95], f32) * tension
            col = col * (1 - tension) + hot * tension
            th = 2.6 * self.sc / max(st, 0.6) ** 0.5 + 0.6
            gain = 3.2 * alpha
            p0, p1 = np.array(a[:2]), np.array(b[:2])
            d = p1 - p0; Ld = np.hypot(*d) + 1e-6; nrm = np.array([-d[1], d[0]]) / Ld
            snapped = ts is not None and ts <= t and not (t >= T_RW1 - 0.05)
            if not snapped:
                amp = 7.0 * self.sc * tension * math.sin(t * 38.0 + hash(s) % 7)
                ss = np.linspace(0, 1, 14)
                pts = p0[None] + d[None] * ss[:, None] + nrm[None] * (amp * np.sin(np.pi * ss))[:, None]
                g = gain * (1 + 2.5 * relink * math.exp(-max(t - T_RW1, 0) / 0.3))
                self.poly4(fx, pts, col * g, th)
                bead = (t * 0.9 + (hash(s) % 97) / 97.0) % 1.0                   # energy bead running along the line
                bp = p0 + d * bead + nrm * amp * math.sin(np.pi * bead)
                splat(fx, bp[0], bp[1], 34, lambda dd, dx, dy: ((np.exp(-dd / 2.2) * 5.0 + np.exp(-dd / 8) * 0.6) * win(dd, 34))[..., None] * (col * 0.5 + 0.5) * g * math.sin(np.pi * bead))
            else:
                u_ = t - ts                                                    # recoil: halves fly back with a decaying wobble
                if u_ < 1.2:
                    r = 0.5 * (1 - math.exp(-u_ / 0.10)) + 0.04 * math.sin(u_ * 30) * math.exp(-u_ / 0.2)
                    fade = math.exp(-u_ / 0.45)
                    for end, sgn in ((p0, 1), (p1, -1)):
                        ss = np.linspace(0, 1, 10)
                        lenf = max(0.5 - r, 0.0)
                        base = end[None] + sgn * d[None] * (ss * lenf)[:, None]
                        wob = 9 * self.sc * math.exp(-u_ / 0.25) * np.sin(np.pi * ss * 2 + u_ * 40)
                        self.poly4(fx, base + nrm[None] * wob[:, None], col * gain * fade, th)
                    mid = (p0 + p1) / 2
                    self.burst(fx, mid[0], mid[1], u_, (1.0, 0.55, 0.85), 0.8)
                    if u_ < 0.5:                                               # spark spray
                        rr = np.random.default_rng(hash(s) % 1000)
                        for _ in range(16):
                            ang = rr.uniform(0, 2 * np.pi); sp = rr.uniform(80, 260) * self.sc
                            q = mid + np.array([math.cos(ang), math.sin(ang)]) * sp * u_ ** 0.7
                            q2 = mid + np.array([math.cos(ang), math.sin(ang)]) * sp * max(u_ - 0.05, 0) ** 0.7
                            self.line4(fx, q2, q, np.array([1.0, 0.7, 0.4], f32) * 6 * (1 - u_ / 0.5), 2)
        return P

    def path(self, key, E0, E1, R, n=60):
        Es = np.linspace(E0, E1, n)
        i = self.ix[key]
        p = self.pos[i][None] + self.vel[i][None] * Es[:, None]
        u = p / np.linalg.norm(p, axis=1)[:, None]
        x, y, ok = self.proj(u, R)
        return np.stack([x, y], 1), ok

    def draw_path(self, fx, pts, ok, col, gain, th=2.0, taper=True):
        n = len(pts)
        for i in range(n - 1):
            if not (ok[i] and ok[i + 1]): continue
            if abs(pts[i + 1][0] - pts[i][0]) > 2000 or abs(pts[i + 1][1] - pts[i][1]) > 2000: continue
            w = ((i + 1) / n) ** 1.3 if taper else 1.0
            self.line4(fx, pts[i], pts[i + 1], np.array(col, f32) * gain * (0.15 + 0.85 * w), th)

    def arrow(self, fx, p, q, col, g, th=3):
        d = np.array(q) - np.array(p); L = np.hypot(*d)
        if L < 8: return
        self.line4(fx, p, q, np.array(col, f32) * g, th)
        u = d / L; n = np.array([-u[1], u[0]]); hs = min(22 * self.sc, L * 0.45)
        for s in (1, -1):
            self.line4(fx, q, np.array(q) - u * hs + s * n * hs * 0.55, np.array(col, f32) * g, th)

    def ring(self, fx, x, y, r, col, g, th=2):
        cv2.circle(fx, (int(x * 4), int(y * 4)), int(r * 4), tuple(float(c) for c in np.array(col, f32) * g), max(1, int(th)), cv2.LINE_AA, 2)

    def feature_fx(self, fx, t):
        """all hero-object graphics into the HDR layer; returns display-space label jobs"""
        jobs = []; sc = self.sc
        E = E_of(t); R = self.R_of(t)
        w1, w2, w3 = self.view_w(t, 1), self.view_w(t, 2), self.view_w(t, 3)
        pulse = 1 + 0.15 * math.sin(t * 6.0)
        end_seg = t >= T_SW4 + 0.3
        # ---- Big Dipper
        if w1 > 0.01:
            a_lines = w1 * (1 - 0.75 * ramp(t, T_SW4, T_SW4 + 0.6) * (1 - ramp(t, T_RW1 - 0.1, T_RW1)))
            P = self.figure(fx, t, DIP, ICE, a_lines * (1 + 0.8 * math.exp(-max(t - T_DIP_LBL, 0) / 0.6) * (t >= T_DIP_LBL)), jobs)
            # 2026 ghost outline while broken (end beat)
            if end_seg and t < T_RW1:
                g = ramp(t, T_SW4 + 0.3, T_SW4 + 1.0) * (1 - ramp(t, T_RW0, T_RW0 + 0.3))
                u0, _ = self.dirs_of(np.array([self.ix[k] for k in ("dubhe", "merak", "phecda", "megrez", "alioth", "mizar", "alkaid")]), 0.0)
                gx, gy, gok = self.proj(u0, R)
                G = dict(zip(("dubhe", "merak", "phecda", "megrez", "alioth", "mizar", "alkaid"), zip(gx, gy)))
                for s in DIP:
                    p, q = np.array(G[s[0]]), np.array(G[s[1]])
                    for k in range(8):                                         # dashed
                        a_, b_ = k / 8, (k + 0.55) / 8
                        self.line4(fx, p + (q - p) * a_, p + (q - p) * b_, np.array([0.7, 0.75, 1.0]) * 0.9 * g, 2)
                for k in G: self.ring(fx, G[k][0], G[k][1], 9 * sc, (0.7, 0.75, 1.0), 0.8 * g)
            for k in ("dubhe", "merak", "phecda", "megrez", "alioth", "mizar", "alkaid"):
                x, y, ok, _ = P[k]
                if not ok: continue
                grp = k in GROUP
                col = CYAN if grp else ORANGE_C
                emph = ramp(t, wt("dip", "FIVE") - 0.1, wt("dip", "FIVE") + 0.2) if grp else ramp(t, wt("dip", "DUBHE") - 0.1, wt("dip", "DUBHE") + 0.2)
                emph *= 1 - ramp(t, T_SW2 - 0.3, T_SW2)
                g = a_lines * (0.6 + 1.6 * emph)
                self.ring(fx, x, y, (14 + 6 * emph) * sc * pulse, col, g, 2)
                # history trail of this star since the counter started
                if T_FF0 < t < T_SW2 + 0.3 or end_seg:
                    E0 = 0.0
                    pts, okk = self.path(k, E0, E, R, 50 if not end_seg else 120)
                    gg = (0.55 if not end_seg else 1.6 * ramp(t, T_SW4 + 0.5, T_SW4 + 1.3)) * w1
                    self.draw_path(fx, pts, okk, col, gg, (1.5 if not end_seg else 2.5) * sc)
                # velocity arrows (the next 60,000 years of motion)
                aa = ramp(t, wt("dip", "FIVE") - 0.2, wt("dip", "FIVE") + 0.4) * (1 - ramp(t, wt("dip", "100,000") - 0.3, wt("dip", "100,000") + 0.2))
                if aa > 0.01:
                    u_now, _ = self.dirs_of(np.array([self.ix[k]]), E)
                    u_fut, _ = self.dirs_of(np.array([self.ix[k]]), E + 60000 * ease((t - wt("dip", "FIVE") + 0.2) / 0.8))
                    x2, y2, _ = self.proj(u_fut, R)
                    self.arrow(fx, (x, y), (float(x2[0]), float(y2[0])), col, 3.0 * aa, 3)
            # labels
            if t >= T_DIP_LBL - 0.05 and w1 > 0.5 and not end_seg:
                xs = [P[k][0] for k in P]; ys = [P[k][1] for k in P]
                cx, cy = float(np.mean(xs)), float(min(ys))
                a = ramp(t, T_DIP_LBL - 0.05, T_DIP_LBL + 0.2) * (1 - ramp(t, T_FF0 + 1.0, T_FF0 + 1.6))
                if a > 0.01: jobs.append(("big", "BIG DIPPER", cx, cy - 70 * sc, ICE, a))
                for k in ("dubhe", "merak", "phecda", "megrez", "alioth", "mizar", "alkaid"):
                    if t - T_DIP_LBL < 0.75: self.burst(fx, P[k][0], P[k][1], t - T_DIP_LBL - 0.04 * "dubhe merak phecda megrez alioth mizar alkaid".split().index(k), ICE, 0.6)
                tg = wt("dip", "FIVE"); a = ramp(t, tg - 0.05, tg + 0.2) * (1 - ramp(t, T_BROKEN + 0.6, T_BROKEN + 1.0))
                if a > 0.01:
                    gx = float(np.mean([P[k][0] for k in GROUP])); gy = float(max(P[k][1] for k in GROUP))
                    jobs.append(("tag2u", ("URSA MAJOR MOVING GROUP", "5 STARS · SAME MOTION"), gx, float(min(P[k][1] for k in P)) - 60 * sc, CYAN, a))
                    if t - tg < 0.75:
                        for k in GROUP: self.burst(fx, P[k][0], P[k][1], t - tg, CYAN, 0.5)
                td = wt("dip", "DUBHE"); ta = wt("dip", "ALKAID")
                for k, tt in (("dubhe", td), ("alkaid", ta)):
                    a = ramp(t, tt - 0.05, tt + 0.2) * (1 - ramp(t, T_SW2 - 0.4, T_SW2))
                    if a > 0.01:
                        jobs.append(("name", k.upper(), P[k][0], P[k][1], ORANGE_C, a))
                        self.burst(fx, P[k][0], P[k][1], t - tt, ORANGE_C, 0.8)
        # ---- Barnard's Star: comet-like streak (boosted: V ~ 8.5-9.5, a telescope star)
        tb0 = wt("ff", "BARNARD'S") - 0.6
        if tb0 < t < T_SW2 + 0.2:
            pts, okk = self.path("barn", max(0.0, E - 9000), E, R, 70)
            a = ramp(t, tb0, tb0 + 0.4) * (1 - ramp(t, LN["dip"]["start"] - 0.2, LN["dip"]["start"] + 0.6)) * w1
            if a > 0.01:
                self.draw_path(fx, pts, okk, (1.0, 0.35, 0.25), 3.5 * a, 4 * sc)
                self.draw_path(fx, pts, okk, (1.0, 0.85, 0.7), 2.0 * a, 1.5)
                x, y = pts[-1]
                if okk[-1]:
                    splat(fx, x, y, 110, lambda d, dx, dy: ((np.exp(-d / 2.5) * 30 + np.exp(-d / 14) * 2.0) * win(d, 110))[..., None] * np.array([1.0, 0.45, 0.30], f32) * a)
                    self.ring(fx, x, y, 22 * sc * pulse, RED, 2.5 * a, 2)
                    tl = wt("ff", "BARNARD'S")
                    self.burst(fx, x, y, t - tl, RED, 0.9)
                    jobs.append(("tag2", ("BARNARD'S STAR", "FASTEST STAR · 10.4″/YR"), x, y, RED, a * ramp(t, tl - 0.05, tl + 0.2)))
        # ---- Orion + Sirius
        if w2 > 0.01:
            P = self.figure(fx, t, ORI, GOLD, w2, jobs)
            for k in ("bet", "bel", "meissa", "mint", "alnil", "alnit", "saiph", "rigel"):
                x, y, ok, _ = P[k]
                if not ok: continue
                hero = k in ("bet", "bel")
                col = MAG_C if hero else GOLD
                emph = ramp(t, wt("orion", "SHOULDERS") - 0.1, wt("orion", "SHOULDERS") + 0.2) if hero else 0
                self.ring(fx, x, y, (12 + 6 * emph) * sc * pulse, col, w2 * (0.6 + 1.6 * emph), 2)
                if hero:
                    pts, okk = self.path(k, 0.0, E, R, 40)
                    self.draw_path(fx, pts, okk, col, 1.5 * w2, 2.5 * sc)
                    self.burst(fx, x, y, t - wt("orion", "SHOULDERS"), MAG_C, 0.7)
            a = w2 * ramp(t, T_SW2 + 0.6, T_SW2 + 1.0)
            if a > 0.01:
                xs = [P[k][0] for k in P]; ys = [P[k][1] for k in P]
                jobs.append(("big", "ORION", float(np.mean(xs)), float(min(ys)), GOLD, a))
                for k, nm in (("bet", "BETELGEUSE"), ("bel", "BELLATRIX")):
                    tt = wt("orion", "SHOULDERS")
                    aa = a * ramp(t, tt - 0.05, tt + 0.2)
                    if aa > 0.01: jobs.append(("name", nm, P[k][0], P[k][1], MAG_C, aa))
            x, y, ok, m = self.star_xy("sirius", t, E)
            if ok and w2 > 0.01:
                pts, okk = self.path("sirius", max(255000.0, E - 300000), E, R, 40)
                self.draw_path(fx, pts, okk, ICE, 1.5 * w2, 2.5 * sc)
                ts = wt("orion", "STARS")
                aa = w2 * ramp(t, ts - 0.1, ts + 0.2)
                self.ring(fx, x, y, 16 * sc * pulse, ICE, (0.5 + 1.5 * aa) * w2, 2)
                if aa > 0.01:
                    self.burst(fx, x, y, t - ts, ICE, 0.7)
                    jobs.append(("tag2", ("SIRIUS", f"MAG {m:+.1f}".replace("+", "+").replace("-", "−")), x, y, ICE, aa))
        # ---- Gliese 710: brightens to mag -3 and streaks past the Sun
        if w3 > 0.01 or (T_SW3 < t < T_SW4 + SWEEP):
            x, y, ok, m = self.star_xy("gj", t, E)
            if ok:
                pts, okk = self.path("gj", max(E - 25000, 1.0e6), E, R, 90)
                fl = 10 ** (-0.4 * (m - 1.0))                                   # 1 at mag +1, ~19 at mag -3.2
                a = max(w3, 0.3 * (t < T_SW4 + SWEEP))
                self.draw_path(fx, pts, okk, (1.0, 0.55, 0.20), (0.6 + 0.5 * min(fl, 6)) * a, 5 * sc)
                self.draw_path(fx, pts, okk, (1.0, 0.95, 0.85), (0.4 + 0.3 * min(fl, 6)) * a, 1.5)
                gcol = np.array([1.0, 0.70, 0.42], f32)
                sp = fl * (1 + 0.06 * math.sin(t * 17))
                rad = 640 * sc
                splat(fx, x, y, rad, lambda d, dx, dy: ((np.exp(-d / 3.0) * 12 * sp + np.exp(-d / 18) * 1.2 * sp + np.exp(-d / 90) * 0.12 * sp) * np.clip(1 - (d / rad) ** 2, 0, 1) ** 2)[..., None] * gcol * a
                      + ((np.exp(-np.abs(dy) / 2.0) * np.exp(-np.abs(dx) / 160) + np.exp(-np.abs(dx) / 2.0) * np.exp(-np.abs(dy) / 160)) * 0.35 * sp * np.clip(1 - (d / rad) ** 2, 0, 1))[..., None] * np.array([1.0, 0.8, 0.6], f32) * a)
                if fl > 1.5:                                                    # rainbow halo ring
                    for ch, off in ((0, 8), (1, 0), (2, -8)):
                        c = [0.0, 0.0, 0.0]; c[ch] = float(0.25 * min(fl, 20) ** 0.6 * a)
                        cv2.circle(fx, (int(x * 4), int(y * 4)), int((95 * sc + off) * 4 * pulse), tuple(c), 3, cv2.LINE_AA, 2)
                tg = wt("gj", "GLIESE 710")
                self.burst(fx, x, y, t - tg, (1.0, 0.6, 0.3), 1.3)
                self.burst(fx, x, y, t - wt("gj", "BLAZING"), (1.0, 0.8, 0.5), 1.6)
                aa = w3 * ramp(t, tg - 0.05, tg + 0.2)
                if aa > 0.01:
                    dist_au = float(np.linalg.norm(self.pos[self.ix["gj"]] + self.vel[self.ix["gj"]] * E)) * 206265
                    jobs.append(("tag3", ("GLIESE 710", f"MAG {m:+.1f}".replace("-", "−"), f"{fmt_int(round(dist_au, -2))} AU FROM THE SUN"), x, y, (1.0, 0.62, 0.25), aa))
            self.gj_light = (min(10 ** (-0.4 * (m + 1.0)), 8.0) * w3) if ok else 0.0
        else:
            self.gj_light = 0.0
        return jobs

    # ----------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        E = E_of(t); R = self.R_of(t)
        rewind = ramp(t, T_RW0 - 0.05, T_RW0 + 0.15) * (1 - ramp(t, T_RW1 - 0.1, T_RW1))
        flash = math.exp(-max(t - T_RW1, 0) / 0.18) * (t >= T_RW1 - 0.02)
        ffk = ramp(t, T_FF0, T_FF0 + 1.5)
        sky = self.night.copy()
        # a slow time-colour drift while the years fly by (always deep blue / violet)
        if ffk > 0:
            hue = 0.5 + 0.5 * math.sin(t * 0.55)
            sky += (np.array([0.020, 0.000, 0.030], f32) * hue + np.array([0.000, 0.012, 0.022], f32) * (1 - hue)) * ffk * (1 - 0.6 * (1 - self.above / max(self.above.max(), 1e-6)))
        nmw = 3 if (T_SW2 < t < T_SW2 + SWEEP or T_SW3 < t < T_SW3 + SWEEP or T_SW4 < t < T_SW4 + SWEEP) else 1
        mw = sum(self.mw_layer(self.R_of(t - k / (30.0 * nmw))) for k in range(nmw)) / nmw
        sky = sky + mw * 6.0 * self.above
        sky = sky + self.stars_layer(t, rewind) * self.above
        fx = np.zeros((H, W, 3), f32)
        jobs = self.feature_fx(fx, t)
        sky = sky + (fx + cv2.GaussianBlur(fx, (0, 0), 3.0) * 1.2) * self.above
        # rewind vortex: rainbow rings rushing inward
        if rewind > 0.01:
            if self.xx is None: self.yy, self.xx = np.mgrid[0:H:2, 0:W:2].astype(f32)
            cx, cy = self.views[0][0, 0] * 0 + W * 0.65, H * 0.48
            rr = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2); th = np.arctan2(self.yy - cy, self.xx - cx)
            band = (0.5 + 0.5 * np.sin(0.035 * rr + t * 40 + 3 * th)) ** 4
            wash = palette((rr / 900 - t * 1.5) % 1.0) * band[..., None] * 0.16 * rewind
            sky = sky + cv2.resize(wash, (W, H), interpolation=cv2.INTER_LINEAR) * self.above
        if flash > 0.01:
            sky = sky + np.array([0.9, 0.85, 1.0], f32) * flash * 1.6 * self.above
        # foreground: night, lamps on, lit by GJ 710 / the flash
        fgc = self.fg.lamps_light(self.fg_night, 1.0, t)
        if self.gj_light > 0.01:
            fgc = fgc + self.fg.flat * np.array([0.80, 0.84, 1.0], f32) * 0.0045 * min(self.gj_light, 6.0)   # faint silver tint only
        if flash > 0.01: fgc = fgc + self.fg.flat * 0.25 * flash
        if rewind > 0.01: fgc = fgc + self.fg.flat * palette((t * 1.5) % 1.0) * 0.05 * rewind
        img = sky * (1 - self.a) + fgc * self.a
        img = bloom(img, 0.95 + 0.4 * rewind)
        out = tonemap(img, 1.25)
        y = out.mean(2, keepdims=True); out = np.clip(y + (out - y) * 1.22 + np.array([0.010, 0.008, 0.022], f32) * (1 - out), 0, 1)
        out = finish(out, t, grain=0.010, vignette=0.16)
        self.overlay(out, t, E, jobs)
        return out

    # ----------------------------------------------------------------------------------------------- overlay
    def place_tag(self, x, y, wid, hgt, below=True):
        """keep a label block inside the margins and off the counter / caption rows"""
        L = self.L; W = L.W
        top = self.counter_xy[1] + (95 if self.v else 80)
        b0, b1 = L.cap_y - L.cap_size * 0.8, L.cap_y + L.cap_size * 0.8
        cy = y + (hgt * 0.5 + 34 * self.sc) * (1 if below else -1)
        if cy + hgt / 2 > b0 and cy - hgt / 2 < b1: cy = y - hgt * 0.5 - 34 * self.sc
        if cy - hgt / 2 < top: cy = y + hgt * 0.5 + 34 * self.sc
        if self.v is False and abs(x - self.counter_xy[0]) < 450 and cy - hgt / 2 < top: cy = top + hgt / 2
        cx = min(max(x, self.mx + wid / 2), W - self.mx - wid / 2)
        return cx, cy

    def overlay(self, out, t, E, jobs):
        L = self.L; W, H = L.W, L.H; v = self.v; sc = self.sc
        for kind, txt, x, y, col, a in jobs:
            if not (-20 < x < W + 20 and 0 < y < self.hz - 10): continue
            c255 = tuple(int(c * 255) for c in np.clip(np.array(col) * 0.75 + 0.25, 0, 1))
            if kind == "big":
                lay = glow_text(txt, int(76 * sc), col)
                cx, cy = self.place_tag(x, y, lay[3], 76 * sc, below=False)
                put_glow(out, lay, cx, cy, a, glow_k=0.6)
            elif kind == "name":
                ns = int(36 * sc); tw = font(ns, "Bold", True).getlength(txt) * 1.12
                cx, cy = self.place_tag(x, y, tw, ns * 1.2, below=y < H * 0.5)
                hud_text(out, txt, cx, cy - ns * 0.3, ns, "Bold", c255, a, 0.10, display=True)
            elif kind in ("tag2", "tag3", "tag2u"):
                ls = list(txt)
                hs = int(46 * sc); ss = int(30 * sc)
                lay = glow_text(ls[0], hs, col, "Black", int(W * 0.8))
                wid = max(lay[3], max(font(ss, "Bold", True).getlength(s) * 1.12 for s in ls[1:]))
                hgt = hs * 1.1 + ss * 1.35 * (len(ls) - 1)
                if kind == "tag3":                                              # beside the blaze, off its glare
                    side = -1 if x > W * 0.5 else 1
                    cx = min(max(x + side * (wid / 2 + 150 * sc), self.mx + wid / 2), W - self.mx - wid / 2); cy = y + 190 * sc
                    if cy + hgt / 2 > L.cap_y - L.cap_size * 0.8: cy = y - 200 * sc
                else:
                    cx, cy = self.place_tag(x, y, wid, hgt, below=y < H * 0.45 and kind != "tag2u")
                y0 = cy - hgt / 2 + hs * 0.55
                put_glow(out, lay, cx, y0, a, glow_k=0.6)
                for j, s in enumerate(ls[1:]):
                    hud_text(out, s, cx, y0 + hs * 0.62 + ss * 1.35 * j, ss, "Bold", (240, 244, 255), a, 0.10, display=True)
        # year counter
        cx, cy = self.counter_xy
        year = YEAR_NOW + E
        ys = int(124 if v else 104)
        speed = abs(E_of(t + 0.05) - E_of(t - 0.05)) / 0.1
        col = tuple(float(c) for c in np.clip(palette((0.58 + 0.25 * math.log10(1 + speed) / 5.5) % 1.0) * 1.1 + 0.15, 0, 1))
        if t > T_RW1 - 0.1 or t < T_FF0: col = (0.45, 0.80, 1.0)
        col = tuple(round(c * 40) / 40 for c in col)                            # quantised: glyph cache stays small
        hud_text(out, "YEAR", cx, cy - ys * 0.95, int(34 * sc), "Bold", (230, 236, 255), 1.0, 0.45, display=True)
        put_glow_digits(out, fmt_int(year) if year >= 10000 else str(int(round(year))), ys, col, cx, cy, 1.0)
        if speed > 50:
            sp = float(f"{speed:.2g}")
            hud_text(out, f"{fmt_int(sp)} YEARS PER SECOND" if t < T_RW0 else "REWIND", cx, cy + ys * 0.80, int(28 * sc), "Bold",
                     (200, 215, 255), min(1.0, speed / 400), 0.14, display=True)
        self.caps.draw(out, t)


# ------------------------------------------------------------------------------------------------- run
def save(im, p):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=17)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0, "DUR", DUR)


def patch(vertical, t_from):
    """re-render frames with t >= t_from, copying the earlier ones from the existing render"""
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=17)
    for i in range(int(round(DUR * FPS))):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if t >= t_from or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
        if i % 60 == 0: print("patch", i, flush=True)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", float(sys.argv[3])); sys.exit()
    if sys.argv[1] == "info":
        print("DUR", DUR); [print(l["key"], l["start"], l["end"]) for l in PL]
        for tt in np.arange(0, DUR, 0.5): print(f"{tt:5.2f}  E={E_of(tt):12.0f}  sh={shutter(tt):.3f}")
        sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
