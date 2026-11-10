"""EVERY STAR YOU SEE IS A DATE — vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the user's valley plate (B_valley.png), facing south from 47 deg N.
  dusk     golden-hour valley under a pink/orange afterglow; Sirius already shining; fast fall to a deep blue/purple night;
           real stars (HYG v4.1, V < 7) switch on one by one, brightest first, each bright one with a sparkle
  labels   named stars at their real positions get a glowing ring, a ring burst, a leader line and a big glowing year
           (2026 - distance in ly): Sirius 2017, Betelgeuse 1400s, Arcturus 1989, Vega 2001, Deneb Roman Empire,
           Andromeda 2.5 million years ago (big procedural galaxy at its real place and orientation)
  motion   the real celestial sphere turns about the real pole all the time (sidereal time is keyframed: a stylised
           time-lapse), with whooshing sweeps between beats; the vivid Milky Way (mw.py look) turns with it
  swirl    "time machine": the sky spins fast, star trails go rainbow, hundreds of tiny years appear next to real stars
  myth     a pulse wave runs over the sky, every star flares ("almost none are dead"); factual lifetime labels
  end      the sky completes a full turn back to the opening dusk sky (loops)
Built on docs-series/shorts/lib (read-only). Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from scipy.interpolate import PchipInterpolator
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, font, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import eq_vec, eq2hor, lens_for, hdir, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S5-star-dates"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
YEAR_NOW = 2026

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]

# ------------------------------------------------------------------------------------------------- timeline
T_DUSK0, T_DUSK1 = 0.10, 3.0                           # afterglow -> night
T_LOOP = DUR - 1.25                                    # the dusk comes back for the loop
T_SWIRL0 = LN["swirl"]["start"] - 0.35
T_SWIRL1 = LN["myth"]["start"] + 0.25
T_WAVE = wt("myth", "NONE") - 0.1                      # "almost none of them are dead" -> pulse wave
T_LIFE, T_LIGHT = wt("myth", "STARS"), wt("myth", "THIS")
L0 = 5.55                                              # opening sidereal time (h): Sirius + Orion over the valley
LST_KEYS = [
    (0.0, L0),
    (LN["title"]["start"] - 0.05, L0 + 0.55),          # slow drift through the hook
    (LN["list"]["start"] - 0.15, 15.55),               # sweep: winter sky -> spring/summer sky (Arcturus + Vega)
    (LN["list"]["end"] + 0.1, 16.75),
    (LN["deneb"]["start"] - 0.1, 18.95),               # Deneb
    (LN["deneb"]["end"] + 0.2, 19.7),
    (LN["m31"]["start"] - 0.05, 22.95),                # Andromeda
    (T_SWIRL0, 24.1),
    (T_SWIRL1, 27.2),                                  # time-machine swirl
    (LN["end"]["start"], 28.7),
    (DUR, L0 + 24.0),                                  # full turn: back to the opening sky (loop)
]
_lst = PchipInterpolator([k[0] for k in LST_KEYS], [k[1] for k in LST_KEYS])
def LST(t): return float(_lst(min(max(t, 0.0), DUR)))

# named stars: (key, RA deg, Dec deg, colour, name line, big line, sub line, t_name, t_big, t_end)
CYAN, GOLD, AMBER, ICE, VIOLET, PINK = (0.35, 0.85, 1.0), (1.0, 0.55, 0.15), (1.0, 0.72, 0.25), (0.55, 0.75, 1.0), (0.75, 0.45, 1.0), (1.0, 0.40, 0.80)
LABELS = [
    ("sirius", 101.287, -16.716, CYAN, "SIRIUS · 8.6 LY", "2017", None, wt("hook", "STAR"), wt("hook", "2017"), LN["title"]["start"] + 1.0),
    ("betel", 88.793, 7.407, GOLD, "BETELGEUSE · ~550 LY", "1400s", None, wt("hook", "ONE"), wt("hook", "BEFORE"), LN["title"]["start"] + 1.0),
    ("arct", 213.915, 19.182, AMBER, "ARCTURUS · 37 LY", "1989", None, wt("list", "ARCTURUS"), wt("list", "1989"), wt("list", "VEGA") + 0.35),
    ("vega", 279.235, 38.784, ICE, "VEGA · 25 LY", "2001", None, wt("list", "VEGA"), wt("list", "2001"), LN["deneb"]["start"] + 0.2),
    ("deneb", 310.358, 45.280, VIOLET, "DENEB · ~1,500–2,600 LY", "ROMAN EMPIRE", "ROUGHLY", wt("deneb", "DENEB"), wt("deneb", "ROMAN"), LN["m31"]["start"] + 0.3),
    ("m31", 10.685, 41.269, PINK, "ANDROMEDA GALAXY · 2.5 MILLION LY", "2.5 MILLION", "YEARS AGO · BEFORE MODERN HUMANS", wt("m31", "ANDROMEDA"), wt("m31", "2.5"), T_SWIRL0 + 0.9),
]
M31_PA = 35.0                                          # position angle of the major axis (deg, N through E)


def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def bv_temp(ci):
    return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


def year_str(ly):
    y = int(round(YEAR_NOW - ly))
    return f"{y}" if y >= 1 else f"{1 - y} BC"


# ------------------------------------------------------------------------------------------------- text layers
_gl = {}
def glow_text(txt, size, col, wt="Black", maxw=None):
    """big glowing label text -> (rgba uint8, glow float rgb 0..1). White-hot fill, coloured edge, coloured halo."""
    k = (txt, int(size), col, wt, maxw)
    if k in _gl: return _gl[k]
    f = font(size, wt, True); w = f.getlength(txt)
    if maxw and w > maxw: f = font(int(size * maxw / w), wt, True); w = f.getlength(txt)
    asc, desc = f.getmetrics(); pad = int(f.size * 0.55) + 4
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
    # soft dark backing so the label reads over bright sky
    sh = cv2.GaussianBlur(a_s, (0, 0), f.size * 0.10)
    _gl[k] = (rgba.astype(np.uint8), glow.astype(f32), sh.astype(f32))
    return _gl[k]


def put_glow(dst, layer, cx, cy, alpha, glow_k=0.9):
    rgba, glow, sh = layer
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


_tiny = {}
def tiny_layer(txt, size, col):
    k = (txt, size, col)
    if k not in _tiny:
        f = font(size, "Bold", True); w = f.getlength(txt); asc, desc = f.getmetrics(); pad = int(size * 0.35)
        Wd, Hd = int(w + 2 * pad), int(asc + desc + 2 * pad)
        m = Image.new("L", (Wd, Hd), 0); ImageDraw.Draw(m).text((pad, pad), txt, font=f, fill=255)
        sh = m.filter(ImageFilter.GaussianBlur(size * 0.18))
        out = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
        out.paste((0, 0, 0, 255), (0, 0), sh.point(lambda v: int(v * 0.75)))
        out.paste(tuple(int(c) for c in col) + (255,), (0, 0), m)
        _tiny[k] = np.asarray(out)
    return _tiny[k]


# ------------------------------------------------------------------------------------------------- galaxy sprite
def m31_sprite(S=640, seed=31):
    """face-on spiral (bulge, log-spiral arms, dust lanes, pink HII knots, halo), then inclined (axis ratio 0.30).
    Major axis along x; rho = 1 at 0.40 S from the centre."""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S].astype(f32)
    u = (xx - S / 2) / (0.40 * S); v = (yy - S / 2) / (0.40 * S) / 0.30          # de-project the inclined disc
    rho = np.sqrt(u * u + v * v) + 1e-4; phi = np.arctan2(v, u)
    k = 1 / math.tan(math.radians(14))
    arm = (0.5 + 0.5 * np.cos(2 * (phi - np.log(rho) * k))) ** 2.2
    lane = (0.5 + 0.5 * np.cos(2 * (phi - np.log(rho) * k) + 2.3)) ** 8 * smooth(0.12, 0.3, rho) * smooth(1.15, 0.7, rho)
    n = cv2.resize(fbm2((128, 128), seed, 2.2), (S, S), interpolation=cv2.INTER_CUBIC)
    disk = np.exp(-rho / 0.30) * (0.35 + 0.9 * arm) * np.clip(1 + 0.35 * n, 0.3, 2) * smooth(1.35, 0.9, rho)
    bulge = np.exp(-rho / 0.045) * 7.0 + np.exp(-rho / 0.13) * 1.6
    w = np.clip(rho / 0.7, 0, 1)[..., None]
    dcol = np.array([1.0, 0.78, 0.50], f32) * (1 - w) + np.array([0.55, 0.70, 1.0], f32) * w
    img = disk[..., None] * dcol * (1 - 0.75 * lane[..., None]) + bulge[..., None] * np.array([1.0, 0.85, 0.62], f32)
    # HII regions along the arms
    acc = np.zeros((S, S), f32)
    for _ in range(260):
        rr = r.uniform(0.35, 1.05); ph = r.uniform(0, 2 * np.pi)
        ph = ph - (ph % np.pi) + np.log(rr) * k + r.normal(0, 0.12)          # on an arm
        x = S / 2 + 0.40 * S * rr * math.cos(ph); y = S / 2 + 0.40 * S * rr * math.sin(ph) * 0.30
        if 0 <= int(x) < S and 0 <= int(y) < S: acc[int(y), int(x)] += r.uniform(0.3, 1.0)
    acc = cv2.GaussianBlur(acc, (0, 0), 1.2) * 6
    img += acc[..., None] * np.array([1.0, 0.35, 0.65], f32)
    halo = np.exp(-np.sqrt(u * u + (v * 0.30 / 0.55) ** 2) / 0.55)
    img += (halo * 0.20)[..., None] * np.array([0.55, 0.45, 1.0], f32)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    edge = smooth(S / 2, S / 2 - 30, np.sqrt((xx - S / 2) ** 2 + ((yy - S / 2) * 1.6) ** 2))
    return (img * edge[..., None]).astype(f32)


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = Layout(vertical); L = self.L; W, H = L.W, L.H
        self.fg = Foreground(FG_PATH, L, hz_frac=0.80)
        self.hz = self.fg.horizon
        self.lens = lens_for(vertical, self.hz)
        L.cap_y = 1495 if vertical else 948
        if not vertical: L.cap_size = 104
        self.caps = Captions(L, WORDS, emphasis={"STAR", "2017", "COLUMBUS", "DATE", "1989", "2001", "ROMAN", "EMPIRE", "ANDROMEDA",
                                                 "2.5", "MILLION", "HUMANS", "TIME", "MACHINE", "DEAD", "BILLIONS", "CENTURIES", "BACK"})
        self.rays = self.lens.rays(1)                                          # (H, W, 3) horizon directions per pixel
        alt = np.arcsin(np.clip(self.rays[..., 2], -1, 1))
        self.alt = alt.astype(f32)
        e = np.clip(alt / (np.pi / 2), 0, 1)
        # night sky: rich deep blue -> violet overhead, teal-blue glow at the horizon (never black)
        k = np.exp(-e / 0.28)[..., None]
        zen = np.array([0.020, 0.012, 0.085], f32); hor = np.array([0.040, 0.060, 0.230], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.40) / 0.22) ** 2)[..., None] * np.array([0.020, 0.004, 0.035], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        night *= (1 + 0.06 * n)[..., None]
        self.night = night.astype(f32)
        # afterglow: the Sun just set in the WSW (az 250, 6 deg down)
        sun = hdir(250.0, -6.0)
        ang = np.degrees(np.arccos(np.clip(self.rays @ sun.astype(f32), -1, 1)))
        glow = np.exp(-e / 0.10)[..., None] * (0.35 + 0.65 * np.exp(-(ang / 55) ** 2))[..., None] * np.array([1.0, 0.40, 0.14], f32) * 1.1
        glow += np.exp(-e / 0.30)[..., None] * np.array([0.55, 0.22, 0.50], f32) * 0.35
        glow += np.array([0.06, 0.09, 0.34], f32) * (1 - 0.3 * e[..., None])
        self.dusk = glow.astype(f32)
        self.above = smooth(-0.01, 0.05, alt).astype(f32)                     # below-horizon mask for stars
        # foreground states
        fg = self.fg; f = fg.flat; y = lum(f)[..., None]
        self.fg_night = ((f * 0.40 + y * 0.60) * np.array([0.21, 0.21, 0.52], f32) * 1.15).astype(f32)
        self.fg_dusk = (fg.rgb * np.array([0.62, 0.42, 0.48], f32)).astype(f32)
        self.a = fg.a[..., None]
        # catalogue
        z = np.load(os.path.join(SCR, "stars.npz"))
        self.sv = eq_vec(z["ra"], z["dec"]).astype(np.float64)
        mag = z["mag"]; self.mag = mag
        self.flux = (2.2 * 10 ** (-0.4 * 0.80 * mag)).astype(f32)
        T = np.clip(bv_temp(np.clip(z["ci"], -0.4, 2.0)), 2600, 30000)
        cols = np.stack([bbcolor(x) for x in T]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = yv[:, None] + (cols - yv[:, None]) * 1.7                       # vivid star colours
        cols = np.clip(cols, 0.02, None); cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.th = np.clip((mag + 1.5) / 8.0, 0, 1) ** 0.9 * 0.85                # darkness at which each star switches on
        self.ph = np.random.default_rng(3).uniform(0, 1000, len(mag)).astype(f32)
        self.bright = np.where(mag < 4.6)[0]
        # tiny year labels for the swirl: reasonably well-measured, bright stars
        ly = z["ly"]; names = z["name"]
        tiny = np.where((mag < 4.4) & (ly > 4) & (ly < 2500))[0]
        self.tiny = tiny
        self.tiny_txt = [year_str(ly[i]) for i in tiny]
        rr = np.random.default_rng(9); self.tiny_t = rr.uniform(0, 1, len(tiny)).astype(f32)
        self.tiny_size = 23 if vertical else 21
        self.lab_eq = {lb[0]: eq_vec(lb[1], lb[2]) for lb in LABELS}
        self.mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        self.gal = m31_sprite()
        self.xx = None

    # ----------------------------------------------------------------------------------------------- helpers
    def proj(self, v, lst):
        h = v @ eq2hor(lst).T
        x, y, ok = self.lens.project(h)
        return x, y, ok & (h[..., 2] > -0.02), h[..., 2]

    def dusk_level(self, t):
        return max(1.0 - ramp(t, T_DUSK0, T_DUSK1), ramp(t, T_LOOP, DUR))

    def mw_layer(self, lst):
        M = EQ2GAL @ eq2hor(lst).T                                              # horizon -> galactic
        g = self.rays @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        return cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def stars_layer(self, t, dark, swirl, wave):
        """all catalogue stars, with motion trails (multi-sampled sidereal time); rainbow trails in the swirl"""
        L = self.L; W, H = L.W, L.H
        acc = np.zeros((H + 2, W + 2, 3), f32)
        l1 = LST(t)
        shutter = 1 / 60 + 0.30 * swirl
        l0 = LST(t - shutter)
        speed_px = abs(l1 - l0) * 15 * 14                                       # rough px moved during the shutter
        on = np.clip((dark - self.th) / 0.06, 0, 1)
        spark = np.where(self.mag < 2.6, 1 + 5.0 * np.exp(-np.maximum(dark - self.th, 0) / 0.035) * (dark > self.th), 1.0)
        vis = np.where(on > 0)[0]
        if len(vis) == 0: return acc[:H, :W]
        nt = np.sin(t * 13.1 + self.ph[vis]) * 0.5 + np.sin(t * 23.7 + self.ph[vis] * 1.7) * 0.3 + np.sin(t * 37.3 + self.ph[vis] * 2.3) * 0.2
        K = int(np.clip(speed_px / 1.6, 1, 40))
        for k in range(K):
            u = (k + 0.5) / K
            lst = l0 + (l1 - l0) * u
            x, y, ok, z = self.proj(self.sv[vis], lst)
            sel = ok & (x > -3) & (x < W + 3) & (y > -3) & (y < H + 3) & (z > 0)
            if not sel.any(): continue
            idx = vis[sel]; xs = x[sel]; ys = y[sel]; zz = z[sel]
            ext = np.clip(zz / 0.12, 0, 1) ** 0.7
            sig = np.clip(0.10 + 0.35 * np.exp(-zz / 0.15), 0.08, 0.6)
            tw = np.exp(sig * nt[sel] * 1.6 - 0.5 * sig * sig)
            fl = self.flux[idx] * on[idx] * spark[idx] * ext * tw / K
            if K > 1: fl = fl * (0.35 + 1.3 * u)                               # comet-like trails: bright head
            col = self.scol[idx]
            if swirl > 0.01 and K > 1:
                pc = palette((u * 0.9 + t * 0.35 + xs / W * 0.3) % 1.0)
                col = col * (1 - 0.85 * swirl) + pc * 1.6 * 0.85 * swirl
            if wave is not None:
                d = np.sqrt((xs - W / 2) ** 2 + (ys - H * 1.05) ** 2)
                fl = fl * (1 + 4.0 * np.exp(-((d - wave) / 70) ** 2)) * np.where(d < wave, 1.35, 1.0)
            val = (fl[:, None] * col).astype(f32)
            x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int); fx = (xs - x0)[:, None]; fy = (ys - y0)[:, None]
            for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
                np.add.at(acc, (np.clip(y0 + dy, 0, H + 1), np.clip(x0 + dx, 0, W + 1)), val * wg)
        acc = acc[:H, :W]
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = acc * (acc.max(2, keepdims=True) > 0.6)
        st += cv2.GaussianBlur(big, (0, 0), 2.0) * 1.5 + cv2.GaussianBlur(big, (0, 0), 7.0) * 1.3
        return st

    def galaxy(self, img, t, lst, dark):
        """Andromeda at its real place and orientation; grows to a hero size while it is the subject"""
        lb = [l for l in LABELS if l[0] == "m31"][0]
        e = self.lab_eq["m31"]
        x, y, ok, z = self.proj(e, lst)
        if not ok or z < 0.02: return None
        ra, de = math.radians(lb[1]), math.radians(lb[2])
        north = np.array([-math.sin(de) * math.cos(ra), -math.sin(de) * math.sin(ra), math.cos(de)])
        east = np.array([-math.sin(ra), math.cos(ra), 0.0])
        pa = math.radians(M31_PA); dd = math.radians(1.0)
        e2 = e + dd * (math.cos(pa) * north + math.sin(pa) * east); e2 /= np.linalg.norm(e2)
        x2, y2, _, _ = self.proj(e2, lst)
        pxdeg = math.hypot(x2 - x, y2 - y); ang = math.atan2(y2 - y, x2 - x)
        hero = 1.0 + 4.6 * ramp(t, lb[7] - 0.15, lb[7] + 1.1) - 3.0 * ramp(t, T_SWIRL0 + 0.5, T_SWIRL1)
        Lpx = 3.2 * pxdeg * hero                                               # 3.2 deg major axis (x hero)
        S = self.gal.shape[0]; sc = Lpx / (0.80 * S)
        R = int(Lpx * 0.75) + 8; H, W = img.shape[:2]
        x0, y0 = int(x) - R, int(y) - R; x1, y1 = int(x) + R, int(y) + R
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if xb <= xa or yb <= ya: return (x, y, Lpx)
        ca, sa = math.cos(ang) * sc, math.sin(ang) * sc
        M = np.array([[ca, -sa, x - xa - (ca * S / 2 - sa * S / 2)], [sa, ca, y - ya - (sa * S / 2 + ca * S / 2)]], np.float64)
        patch = cv2.warpAffine(self.gal, M, (xb - xa, yb - ya), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        gain = (0.08 + 0.10 * ramp(t, lb[7] - 0.2, lb[7] + 0.8)) * dark * (1 + 0.08 * math.sin(t * 2.2))
        img[ya:yb, xa:xb] += patch * gain * np.clip(z / 0.1, 0, 1)
        return (x, y, Lpx)

    # ----------------------------------------------------------------------------------------------- label FX (HDR)
    def label_state(self, lb, t, lst):
        key = lb[0]
        x, y, ok, z = self.proj(self.lab_eq[key], lst)
        return float(x), float(y), bool(ok and z > 0.02)

    def label_side(self, x, y):
        L = self.L
        side = 1 if x < L.W * 0.52 else -1
        below = y < (560 if L.vertical else 330)
        return side, below

    def label_fx(self, fx, t, lst, gal):
        """rings, ring bursts, flares, leader lines into the HDR layer; returns display-space label jobs"""
        L = self.L; W, H = L.W, L.H; jobs = []
        sc = 1.0 if L.vertical else 0.85
        for lb in LABELS:
            key, col = lb[0], np.array(lb[3], f32)
            tn, tb, te = lb[7], lb[8], lb[9]
            if not (tn - 0.05 <= t <= te + 0.5): continue
            x, y, ok = self.label_state(lb, t, lst)
            if not ok: continue
            a = ramp(t, tn - 0.05, tn + 0.12) * (1 - ramp(t, te, te + 0.45))
            if a <= 0.003: continue
            rr = (gal[2] * 0.42 if (key == "m31" and gal) else 26 * sc)
            pulse = 1 + 0.15 * math.sin(t * 6.0)
            # ring + inner flare
            cv2.circle(fx, (int(x * 4), int(y * 4)), int(rr * 4 * pulse), tuple(float(c) for c in col * 5.0 * a), max(2, int(2.2 * sc)), cv2.LINE_AA, 2)
            for tp, big in ((tn, 1.0), (tb, 1.5)):                               # ring bursts at the name and at the year
                u = t - tp
                if 0 <= u < 0.9:
                    R = rr + (60 + 380 * big * sc) * (u / 0.9) ** 0.55
                    k = (1 - u / 0.9) ** 1.6 * 3.5 * big
                    for ch, off in ((0, 7), (1, 0), (2, -7)):
                        c = [0.0, 0.0, 0.0]; c[ch] = float(k * (0.6 + 0.8 * col[ch]))
                        cv2.circle(fx, (int(x * 4), int(y * 4)), int((R + off) * 4), tuple(c), max(2, int(5 * (1 - u))), cv2.LINE_AA, 2)
                    fl = math.exp(-u / 0.12) * 30 * big
                    splat(fx, x, y, 140, lambda d, dx, dy: ((np.exp(-d / 3) * fl + np.exp(-d / 18) * fl * 0.12))[..., None] * (col * 0.6 + 0.4)
                          + ((np.exp(-np.abs(dy) / 1.6) * np.exp(-np.abs(dx) / 70) + np.exp(-np.abs(dx) / 1.6) * np.exp(-np.abs(dy) / 70)) * fl * 0.08)[..., None] * col)
            # leader line, drawn out over 0.25 s
            side, below = self.label_side(x, y)
            ox, oy = 125 * sc * side, (130 if below else -120) * sc
            if key == "m31" and gal: ox, oy = ox + side * rr * 0.6, oy + (rr * 0.5 if below else -rr * 0.5)
            ax, ay = x + ox, y + oy
            dl = math.hypot(ox, oy); p = ease((t - tn) / 0.28)
            sx0, sy0 = x + ox / dl * (rr + 6), y + oy / dl * (rr + 6)
            ex, ey = sx0 + (ax - sx0) * p, sy0 + (ay - sy0) * p
            cv2.line(fx, (int(sx0 * 4), int(sy0 * 4)), (int(ex * 4), int(ey * 4)), tuple(float(c) for c in col * 2.6 * a), 2, cv2.LINE_AA, 2)
            hx2 = ex + side * 90 * sc * p
            cv2.line(fx, (int(ex * 4), int(ey * 4)), (int(hx2 * 4), int(ey * 4)), tuple(float(c) for c in col * 2.6 * a), 2, cv2.LINE_AA, 2)
            jobs.append((lb, ax, ay, side, below, a, p))
        return jobs

    def draw_labels(self, out, t, jobs):
        L = self.L; W, H = L.W, L.H; v = L.vertical
        ys = 118 if v else 100; ns = 34 if v else 30; maxw = 560 if v else 640
        for lb, ax, ay, side, below, a, p in jobs:
            col = tuple(int(c * 255) for c in np.clip(np.array(lb[3]) * 0.85 + 0.15, 0, 1))
            tn, tb = lb[7], lb[8]
            # name line sits on the horizontal leader; big text under it
            nx = ax + side * 6
            ny = ay - ns * 0.85
            tw = font(ns, "Bold", True).getlength(lb[4]) * 1.12
            nx = min(max(nx, 40 + (0 if side > 0 else tw)), W - 40 - (tw if side > 0 else 0))
            hud_text(out, lb[4], nx, ny, ns, "Bold", (240, 244, 255), a * ease((t - tn) / 0.25), 0.10, display=True, anchor="l" if side > 0 else "r")
            u = t - tb
            if u < -0.03: continue
            s = 1.0 + 0.30 * math.exp(-max(u, 0) / 0.07) * (u < 0.4)
            s = round(min(s, 1.3) * 20) / 20
            lay = glow_text(lb[5], int(ys * s), lb[3], "Black", int(maxw * s))
            w = lay[0].shape[1]; pad = 0
            cx = ax + side * (w / 2 - int(ys * s * 0.5))
            cx = min(max(cx, w / 2 - ys * 0.4), W - w / 2 + ys * 0.4)
            cy = ay + ys * 0.62
            al = a * min(1.0, (u + 0.03) / 0.08)
            put_glow(out, lay, cx, cy, al)
            if lb[6]:
                hud_text(out, lb[6], cx, cy + ys * 0.75, int(ns * 0.85), "Bold", col, al * ease((u - 0.25) / 0.3), 0.12, display=True)

    # ----------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        D = self.dusk_level(t); dark = 1 - D
        lst = LST(t)
        swirl = ramp(t, T_SWIRL0 - 0.2, T_SWIRL0 + 0.6) * (1 - ramp(t, T_SWIRL1 - 0.6, T_SWIRL1 + 0.4))
        wave = (t - T_WAVE) * 1500.0 if T_WAVE <= t <= T_WAVE + 2.2 else None
        sky = self.night * (1 - D) + self.dusk * D
        # Milky Way (blurred along the motion while the sky sweeps)
        sp = abs(LST(t) - LST(t - 1 / 30)) * 15 * 30                           # deg / s
        nmw = 1 if sp < 8 else 3
        mw = sum(self.mw_layer(LST(t - k / (30.0 * nmw))) for k in range(nmw)) / nmw
        sky = sky + mw * (6.5 * dark ** 1.5) * self.above[..., None] * (1 + 0.6 * swirl)
        sky = sky + self.stars_layer(t, dark, swirl, wave) * self.above[..., None]
        gal = self.galaxy(sky, t, lst, dark)
        # swirl vortex glow: colour wash spinning about the (off-frame) celestial pole
        if swirl > 0.01:
            pole = self.lens.project(hdir(0.0, 47.0)[None])[:2]
            px, py = float(pole[0][0]), float(pole[1][0])
            if self.xx is None:
                self.yy, self.xx = np.mgrid[0:H:2, 0:W:2].astype(f32)
            th = np.arctan2(self.yy - py, self.xx - px); rr = np.sqrt((self.xx - px) ** 2 + (self.yy - py) ** 2)
            band = (0.5 + 0.5 * np.sin(6 * th - 0.012 * rr + t * 9.0)) ** 3
            wash = palette((th / (2 * np.pi) * 2 + rr / 1400 + t * 0.4) % 1.0) * (band * np.exp(-((rr - H * 0.9) / (H * 0.9)) ** 2))[..., None]
            wash = cv2.resize(wash, (W, H), interpolation=cv2.INTER_LINEAR)
            sky = sky + wash * 0.10 * swirl * self.above[..., None]
        # pulse wave ring ("alive")
        if wave is not None:
            if self.xx is None:
                self.yy, self.xx = np.mgrid[0:H:2, 0:W:2].astype(f32)
            d = np.sqrt((self.xx - W / 2) ** 2 + (self.yy - H * 1.05) ** 2)
            rng = np.exp(-((d - wave) / 40) ** 2) * math.exp(-(t - T_WAVE) / 1.6)
            ring = palette((d / 900 + t) % 1.0) * rng[..., None] * 0.45
            sky = sky + cv2.resize(ring, (W, H), interpolation=cv2.INTER_LINEAR) * self.above[..., None]
        # labels (HDR part)
        fx = np.zeros((H, W, 3), f32)
        jobs = self.label_fx(fx, t, lst, gal)
        sky = sky + fx + cv2.GaussianBlur(fx, (0, 0), 3.0) * 1.2
        # foreground: dusk -> night; tinted by the sky and by label flashes
        fgc = self.fg_night * (1 - D) + self.fg_dusk * D
        flash = sum(math.exp(-max(t - lb[8], 0) / 0.35) * (t >= lb[8]) for lb in LABELS) + sum(math.exp(-max(t - lb[7], 0) / 0.3) * (t >= lb[7]) * 0.5 for lb in LABELS)
        if flash > 0.01:
            c = sum(np.array(lb[3], f32) * math.exp(-max(t - lb[8], 0) / 0.35) * (t >= lb[8]) for lb in LABELS) + 1e-6
            fgc = fgc + self.fg.flat * (c / max(c.max(), 1e-6)) * 0.10 * min(flash, 1.5)
        if swirl > 0: fgc = fgc + self.fg.flat * palette((t * 0.6) % 1.0) * 0.05 * swirl
        img = sky * (1 - self.a) + fgc * self.a
        img = bloom(img, 0.9 + 0.4 * swirl)
        out = tonemap(img, 1.25)
        out = self.grade(out)
        out = finish(out, t, grain=0.010, vignette=0.16)
        self.overlay(out, t, lst, jobs)
        return out

    def grade(self, out):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * 1.22
        return np.clip(out + np.array([0.010, 0.008, 0.022], f32) * (1 - out), 0, 1)

    # ----------------------------------------------------------------------------------------------- overlay
    def overlay(self, out, t, lst, jobs):
        L = self.L; W, H = L.W, L.H
        # tiny years (swirl -> start of the myth beat), fading as the "alive" wave passes
        a0 = T_SWIRL0 + 0.3
        if a0 - 0.1 < t < T_WAVE + 2.4:
            x, y, ok, z = self.proj(self.sv[self.tiny], lst)
            appear = a0 + self.tiny_t * 1.4
            for i in np.where(ok & (z > 0.05) & (x > 20) & (x < W - 90) & (y > 40) & (y < self.hz - 40))[0]:
                a = min(1.0, max(0.0, (t - appear[i]) / 0.25))
                if T_WAVE <= t:
                    d = math.hypot(x[i] - W / 2, y[i] - H * 1.05)
                    if d < (t - T_WAVE) * 1500: a *= 0.0
                if a <= 0.02: continue
                c = np.clip(self.scol[self.tiny[i]] * 0.6 + 0.55, 0, 1) * 255
                composite(out, tiny_layer(self.tiny_txt[i], self.tiny_size, tuple(c)), x[i] + 10 + len(self.tiny_txt[i]) * self.tiny_size * 0.3, y[i] - self.tiny_size * 0.55, a * 0.95)
        self.draw_labels(out, t, jobs)
        # factual lifetime labels (myth beat)
        v = L.vertical
        y1 = (300 if v else 120); fs = 34 if v else 30
        for txt, big, tt, col, yy in (("STAR LIFETIMES", "MILLIONS–BILLIONS OF YEARS", T_LIFE, (0.45, 1.0, 0.55), y1),
                                      ("THIS STARLIGHT", "MOSTLY CENTURIES OLD", T_LIGHT, (1.0, 0.75, 0.30), y1 + (210 if v else 170))):
            a = ramp(t, tt - 0.05, tt + 0.2) * (1 - ramp(t, LN["end"]["start"] - 0.2, LN["end"]["start"] + 0.2))
            if a > 0.01:
                hud_text(out, txt, W / 2, yy, fs, "Bold", (235, 240, 255), a, 0.18, display=True)
                put_glow(out, glow_text(big, 76 if v else 72, col, "Black", 960 if v else 1300), W / 2, yy + (88 if v else 80), a)
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


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR); [print(l["key"], l["start"], l["end"]) for l in PL]; sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
