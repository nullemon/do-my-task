"""WHAT IF BETELGEUSE EXPLODED TONIGHT? -- one LOCKED tripod shot of the park (A2_park.png), VFX spectacle style.
The real night sky (HYG v4.1 stars, true RA/Dec and B-V colours, latitude 52 N, facing south) with Orion over the park.
  hook (orange Betelgeuse, label) -> neutrino alert (ripples, neutrino streaks, phone-style alert)
  -> the explosion (white-out flash, blue-white point, chromatic spikes, rainbow beams, shockwave, god rays, the park lit
     blue-white with sharp shadows cast by one point) -> daylight (blue sky, the supernova still blazing)
  -> months of fading (blue-white -> orange-red, month counter) -> Orion without its shoulder -> safe (distance readout)
  -> twist: the light left in the 1400s; Betelgeuse pulses back, a light front rolls towards us; ends on the opening frame.
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
from lib.core import f32, Layout, ramp, smooth, ease, splat, lum, fbm2, bbcolor, noise1
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite, font
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import eq_vec, eq2hor, lens_for, hdir, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S9-betelgeuse"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
# SOURCE px of A2_park.png (941x1672) (as measured for ../gamma-ray-eyes): street-lamp heads + pole bases
LAMPS_SRC = [(193, 1198, 1325), (666, 1207, 1322), (816, 1113, 1323)]
LAWN_SRC = 1324          # far edge of the lawn (source row)
VAN_SRC = 1300           # vanishing line of the lawn plane (source row), slightly above the far edge
F_SRC = 1000.0           # plate focal length (source px), camera height 1.3 m
CAM_H = 1.3
SH_EL = 19.0            # light elevation used for the shadows (deg, stylised low: long shadows)
LAMP_EL = 7.0           # the far lamp posts get an even lower one so their thin shadows reach across the lawn
FPS = 30
LEAD, TAIL = 0.25, 1.30
LST0 = 5.55              # local sidereal time (h): Orion just east of the meridian, upright, due south
YEAR_NOW = 2026

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t1" if end else "t0"]

# ------------------------------------------------------------------------------------------------- timeline
T_LABEL = wt("hook", "BETELGEUSE") - 0.05
T_NEUT = LN["neut"]["start"]
T_ALERT = wt("neut", "NEUTRINOS") - 0.08
RIPPLES = [wt("neut", "WARNING"), wt("neut", "NEUTRINOS"), wt("neut", "HOURS"), wt("neut", "LIGHT"), wt("neut", "ALARM")]
T_STREAK0, T_STREAK1 = wt("neut", "NEUTRINOS") - 0.2, LN["boom"]["start"] + 0.6
T_FLARE0 = LN["boom"]["start"]                       # "Then Orion's shoulder ..." the star swells
T_IGN = wt("boom", "IGNITES") - 0.04                 # detonation
T_MOON = wt("boom", "MOON")
T_SHADOW = wt("boom", "CASTING")
T_DAY = LN["day"]["start"] - 0.12                    # cut to daylight
T_NIGHT = LN["fade"]["start"] - 0.10                 # back to night for the months of fading
T_FADE1 = wt("fade", "ORION") - 0.15                 # gone
T_GONE = wt("fade", "SHOULDER")
T_SAFE = LN["safe"]["start"]
T_550 = wt("twist", "550")
T_BACK = wt("twist", "SO") - 0.05                    # pulse back to tonight's sky
T_FRONT = wt("twist", "THE", 0) - 0.1               # the light front rolls towards us
T_END = DUR

# Orion stick figure (HYG proper names)
ORION = ["Betelgeuse", "Bellatrix", "Meissa", "Alnitak", "Alnilam", "Mintaka", "Saiph", "Rigel"]
ORION_LINES = [("Betelgeuse", "Meissa"), ("Meissa", "Bellatrix"), ("Betelgeuse", "Bellatrix"), ("Betelgeuse", "Alnitak"),
               ("Bellatrix", "Mintaka"), ("Mintaka", "Alnilam"), ("Alnilam", "Alnitak"), ("Alnitak", "Saiph"), ("Mintaka", "Rigel")]


def lines_alpha(t):
    a = ramp(t, 0.45, 1.1) * (1 - ramp(t, T_NEUT + 0.6, T_NEUT + 1.4))                 # hook: show the hunter
    a = max(a, ramp(t, wt("fade", "ORION") - 0.1, wt("fade", "ORION") + 0.3) * (1 - ramp(t, T_BACK - 0.1, T_BACK + 0.35)))
    return a


def sn_state(t):
    """-> (intensity of the supernova point [relative], colour temperature K, flare 0..1 for spikes/beams)"""
    if t < T_FLARE0: return 0.0, 3600.0, 0.0
    if t < T_IGN:
        u = (t - T_FLARE0) / (T_IGN - T_FLARE0); return 0.02 * u ** 3, 3600.0 + 6000 * u ** 2, 0.0
    if t < T_NIGHT:
        u = t - T_IGN
        I = 1.0 + 1.8 * math.exp(-u / 0.35) + 0.25 * math.exp(-((t - T_MOON) / 0.25) ** 2)
        return I, 16000.0 - 2000 * ramp(t, T_IGN + 1.0, T_NIGHT), 1.0
    if t < T_FADE1 + 0.35:
        u = ramp(t, T_NIGHT + 0.1, T_FADE1)                                             # "months": linear in time
        I = 0.75 * math.exp(-3.2 * u ** 1.25) * (1 - ramp(t, T_FADE1 - 0.1, T_FADE1 + 0.35))
        return I, 13000.0 * (2700 / 13000) ** (u ** 0.55), 1.0 - 0.75 * u
    return 0.0, 3600.0, 0.0


def betel_state(t):
    """the ordinary red supergiant: brightness multiplier (0 while gone)"""
    if t < T_IGN: return 1.0 + 0.5 * sum(math.exp(-((t - r) / 0.12) ** 2) for r in RIPPLES) * ramp(t, T_NEUT, T_NEUT + 0.3)
    if t < T_BACK: return 0.0
    return ramp(t, T_BACK, T_BACK + 0.15) * (1 + 1.5 * math.exp(-max(t - T_BACK, 0) / 0.5))


def day_level(t):
    return ramp(t, T_DAY - 0.02, T_DAY + 0.10) * (1 - ramp(t, T_NIGHT - 0.05, T_NIGHT + 0.45))


def month_of(t):
    return int(np.clip(1 + 11 * (t - T_NIGHT - 0.1) / (T_FADE1 - T_NIGHT - 0.1), 1, 12))


# ------------------------------------------------------------------------------------------------- helpers
def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (np.asarray(x) % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def bv_temp(ci):
    return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


def vivid(c, k=1.4):
    c = np.asarray(c, f32); y = float(lum(c)); return np.clip(y + (c - y) * k, 0.0, None) / max(y, 1e-4)


_gl = {}
def glow_text(txt, size, col, wt="Black", maxw=None):
    """(from ../star-dates) big glowing label text -> (rgba uint8, glow float rgb 0..1, backing, width)"""
    k = (txt, int(size), col, wt, maxw)
    if k in _gl: return _gl[k]
    f = font(size, wt, True); w = f.getlength(txt)
    if maxw and w > maxw: f = font(int(size * maxw / w), wt, True); w = f.getlength(txt)
    asc, desc = f.getmetrics(); pad = int(f.size * 1.3) + 4
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


_card = {}
def alert_card(w, h, sc):
    """phone-notification style card: dark glass, rounded, glowing rim, radiating icon, two text lines -> RGBA uint8"""
    if (w, h) in _card: return _card[(w, h)]
    S = 2; W2, H2 = w * S, h * S; pad = int(40 * sc) * S
    im = Image.new("RGBA", (W2 + 2 * pad, H2 + 2 * pad), (0, 0, 0, 0))
    glow = Image.new("L", im.size, 0); ImageDraw.Draw(glow).rounded_rectangle((pad, pad, pad + W2, pad + H2), radius=int(46 * sc) * S, outline=255, width=int(10 * sc) * S)
    glow = glow.filter(ImageFilter.GaussianBlur(18 * sc * S))
    im.paste((90, 200, 255, 255), (0, 0), glow.point(lambda v: int(v * 0.9)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + W2, pad + H2), radius=int(46 * sc) * S, fill=(14, 18, 44, 222), outline=(140, 215, 255, 255), width=int(3 * sc) * S)
    # icon: radiating rings in a circle
    r = int(h * 0.30) * S; cx, cy = pad + int(h * 0.50) * S, pad + H2 // 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 120, 40, 255))
    for k, rr in enumerate((0.25, 0.50, 0.75)):
        q = int(r * rr); d.ellipse((cx - q, cy - q, cx + q, cy + q), outline=(255, 245, 230, 255), width=max(2, int(4 * sc) * S))
    d.ellipse((cx - S * 5, cy - S * 5, cx + S * 5, cy + S * 5), fill=(255, 255, 255, 255))
    tx = cx + r + int(26 * sc) * S
    f1 = font(int(h * 0.30) * S, "Black", True); f2 = font(int(h * 0.20) * S, "Bold", True); f3 = font(int(h * 0.15) * S, "SemiBold", True)
    d.text((tx, pad + int(h * 0.17) * S), "NEUTRINO ALERT", font=f1, fill=(255, 255, 255, 255))
    d.text((tx, pad + int(h * 0.56) * S), "HOURS BEFORE THE LIGHT", font=f2, fill=(150, 220, 255, 255))
    d.text((pad + W2 - int(26 * sc) * S, pad + int(h * 0.19) * S), "now", font=f3, fill=(180, 190, 220, 255), anchor="ra")
    im = im.resize((im.size[0] // S, im.size[1] // S), Image.LANCZOS)
    _card[(w, h)] = np.asarray(im)
    return _card[(w, h)]


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.W, self.H = W, H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.80 if vertical else 0.66)
        self.hz = fg.horizon
        self.hy = VAN_SRC * fg.s + fg.oy + 8                              # true horizon (behind the hedge)
        self.lens = lens_for(vertical, self.hy)
        if vertical: L.cap_y = 1100
        else: L.cap_y = 610; L.cap_size = 100
        self.caps = Captions(L, WORDS, emphasis={"BETELGEUSE", "TONIGHT", "NEUTRINOS", "ALARM", "IGNITES", "MOON", "SHADOWS",
                                                 "DAYLIGHT", "WEEKS", "BLUE-WHITE", "ORANGE-RED", "FOREVER", "SAFE", "550",
                                                 "ALREADY", "HAPPENED", "YET"})
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(f32)
        self.a = fg.a[..., None]
        # ---- real sky
        rays = self.lens.rays(1); alt = np.arcsin(np.clip(rays[..., 2], -1, 1)); e = np.clip(alt / (np.pi / 2), 0, 1)
        k = np.exp(-e / 0.28)[..., None]
        zen = np.array([0.016, 0.011, 0.085], f32); hor = np.array([0.036, 0.050, 0.215], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.40) / 0.22) ** 2)[..., None] * np.array([0.020, 0.003, 0.036], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        # daylight: Rayleigh-ish gradient, the Sun high behind the camera (morning, east-south-east)
        kd = np.exp(-e / 0.16)[..., None]
        self.daysky = ((np.array([0.020, 0.105, 0.52], f32) * (1 - kd) + np.array([0.36, 0.56, 0.86], f32) * kd)
                       * (1 + 0.30 * np.exp(-e / 0.05))[..., None]).astype(f32)
        cir = cv2.resize(np.clip(fbm2((256, 512), 92, 2.4) * 0.5 + 0.3, 0, 1) ** 1.8, (W, H), interpolation=cv2.INTER_CUBIC)
        self.cirrus = (cir * smooth(-0.02, 0.15, alt) * 0.10).astype(f32)
        self.above = smooth(-0.01, 0.04, alt).astype(f32)[..., None]
        # Milky Way (fixed sidereal time -> one static layer), same recipe as ../star-dates
        mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        M = EQ2GAL @ eq2hor(LST0).T
        g = rays @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        self.mw = (cv2.remap(mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * 6.0 * self.above).astype(f32)
        self.ag_src = fbm2((128, 256), 77, 2.2)
        self.ag_band = (np.exp(-e / 0.10) * smooth(-0.01, 0.02, alt)).astype(f32)
        del rays
        # ---- catalogue stars (static positions; twinkle per frame)
        z = np.load(os.path.join(SCR, "stars.npz"))
        v = eq_vec(z["ra"], z["dec"]) @ eq2hor(LST0).T
        x, y, ok = self.lens.project(v)
        sel = ok & (v[:, 2] > 0) & (x > -4) & (x < W + 4) & (y > -4) & (y < H + 4)
        names = z["name"]; self.named = {}
        for nm in ORION + ["Sirius", "Aldebaran", "Procyon"]:
            i = np.where(names == nm)[0]
            if len(i): self.named[nm] = (float(x[i[0]]), float(y[i[0]]))
        bi = np.where(names == "Betelgeuse")[0][0]
        sel[bi] = False                                                     # drawn separately
        self.C = self.named["Betelgeuse"]
        self.sx, self.sy = x[sel].astype(f32), y[sel].astype(f32); mag = z["mag"][sel]; self.smag = mag
        self.sz = v[sel, 2].astype(f32)
        self.sflux = (4.5 * 10 ** (-0.4 * 0.90 * mag)).astype(f32)
        T = np.clip(bv_temp(np.clip(z["ci"][sel], -0.4, 2.0)), 2600, 30000)
        cols = np.stack([bbcolor(tt) for tt in T]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = yv[:, None] + (cols - yv[:, None]) * 1.7
        cols = np.clip(cols, 0.02, None); cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.sph = np.random.default_rng(3).uniform(0, 1000, len(mag)).astype(f32)
        self.glint = np.where(mag < 1.6)[0]
        self.betel_col = vivid(bbcolor(3600.0), 1.6)
        # ---- geometry around the supernova (fixed point on screen)
        cx, cy = self.C
        self.dx, self.dy = self.xx - cx, self.yy - cy
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3
        self.phi = np.arctan2(self.dy, self.dx)
        hw, hh = W // 2, H // 2
        self.hd = cv2.resize(self.d, (hw, hh), interpolation=cv2.INTER_AREA); self.hphi = cv2.resize(self.phi, (hw, hh), interpolation=cv2.INTER_NEAREST)
        self.halo = [np.exp(-self.d / r).astype(f32) for r in (6.0, 40.0, 180.0, 700.0)]
        self.spikes = self._spikes()
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 9 + r.uniform(-0.2, 0.2), w=r.uniform(0.10, 0.20), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(9)]
        # neutrino streaks
        n = 700; rr = np.random.default_rng(17)
        self.nu = dict(th=rr.uniform(0, 2 * np.pi, n), t0=rr.uniform(0, 1, n), per=rr.uniform(0.7, 1.3, n), hue=rr.uniform(0, 1, n),
                       I=rr.uniform(0.3, 1.0, n) ** 2)
        # ---- foreground states
        f = fg.flat; yl = lum(f)[..., None]
        self.fg_night = ((f * 0.40 + yl * 0.60) * np.array([0.22, 0.22, 0.52], f32) * 1.25).astype(f32)
        self.fg_day = (fg.rgb * np.array([0.98, 1.0, 1.04], f32)).astype(f32)
        self.lit_alb = np.clip(f * 0.40 + yl * 0.60, 0, 1).astype(f32)
        self.shadow, self.lawn, self.fill = self._shadows()
        a2 = fg.a; sh = np.zeros_like(a2); sh[8:] = a2[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a2 - sh, 0, 1), (0, 0), 3.0) * a2).astype(f32)
        self.lamps = [(lx * fg.s, ly * fg.s + fg.oy, by * fg.s + fg.oy) for lx, ly, by in LAMPS_SRC]
        fg.lamps = self.lamps
        self.airx = None

    # -------------------------------------------------------------------------------------------- precomputation
    def _spikes(self):
        """8 diffraction spikes (4 long + 4 short) about the supernova; sparse (indices, perpendicular profile, along)"""
        out = []; W, H = self.W, self.H
        for k in range(8):
            a = k * math.pi / 4 + math.radians(12)
            al = self.dx * math.cos(a) + self.dy * math.sin(a); pp = -self.dx * math.sin(a) + self.dy * math.cos(a)
            wdt = 2.2 if k % 2 == 0 else 1.5
            m = (np.abs(pp) < 26) & (al > 0)
            idx = np.flatnonzero(m)
            out.append(dict(idx=idx, pp=pp.ravel()[idx].astype(f32), al=al.ravel()[idx].astype(f32), w=wdt, long=(k % 2 == 0)))
        return out

    def _shadows(self):
        """clean ground-plane shadows cast by the supernova point: the conifer (a serrated spear), the three lamp posts
        (thin strips ending in the lamp head) and the big tree's trunk. Lawn plane Z = f h / (y - y_v); each object is a
        vertical profile (height, half-width) standing at its ground contact; every point at height z lands on the lawn
        z * cot(el) further from the light (towards the camera), then is projected back into the plate. Light azimuth from
        the star's screen x; elevation SH_EL (stylised low, so the shadows run long). Crisp at the base, softening further
        out. Built in SOURCE px at 4x, then warped like the plate."""
        im = np.asarray(Image.open(FG_PATH).convert("RGBA"), f32) / 255.0
        a = im[..., 3]; sh_, sw_ = a.shape
        cxs = sw_ / 2
        xs = self.C[0] / self.fg.s
        az = math.atan((xs - cxs) / F_SRC)
        yy, xx = np.mgrid[0:sh_, 0:sw_].astype(f32)
        lawn = (a > 0.5) & (yy > LAWN_SRC) & ~((xx < 52) & (yy < 1392))
        occ = (a > 0.5) & ~lawn
        kk = 1 / math.tan(math.radians(SH_EL)); sa, ca = math.sin(az), math.cos(az)
        Q = 4; P = np.zeros((sh_ * Q, sw_ * Q), np.uint8)
        def scr(X, Z): return cxs + F_SRC * X / Z, VAN_SRC + F_SRC * CAM_H / Z
        def cast(xb, yb, ztop_px, prof, n=300, kk=kk):
            """object standing at source (xb, yb); its top at source row ztop_px; prof(u) -> half-width [m] at height u"""
            Zb = F_SRC * CAM_H / (yb - VAN_SRC); Xb = (xb - cxs) * Zb / F_SRC; Hh = (yb - ztop_px) * Zb / F_SRC
            L, R = [], []
            for u in np.linspace(0, 1, n):
                X = Xb - Hh * u * kk * sa; Z = Zb - Hh * u * kk * ca
                if Z < 0.4: break
                w = prof(u)
                xl, yl = scr(X - w * ca, Z + w * sa); xr, yr = scr(X + w * ca, Z - w * sa)
                L.append((xl * Q, yl * Q)); R.append((xr * Q, yr * Q))
            if len(L) > 1:
                poly = np.array(L + R[::-1], np.float64)
                poly = np.clip(poly, -1e5, 1e5).astype(np.int32)
                cv2.fillPoly(P, [poly], 255, cv2.LINE_AA)
        # conifer: tiered, serrated cone (source: base x 470, y 1318; top y 950)
        rng = np.random.default_rng(4); jit = rng.uniform(0.85, 1.15, 64)
        def conifer(u):
            if u < 0.06: return 0.35                                                   # trunk
            v = (u - 0.06) / 0.94; tier = (v * 9) % 1.0
            return 4.2 * (1 - v) ** 1.1 * (0.72 + 0.28 * tier) * jit[int(v * 63)] + 0.05
        cast(470, 1318, 950, conifer, 500)
        for lx, ly, by in LAMPS_SRC:                                                   # lamp posts + heads
            cast(lx, by, ly, lambda u: 0.80 if u > 0.94 else 0.42, 600, 1 / math.tan(math.radians(LAMP_EL)))
        cast(22, 1384, 1050, lambda u: 0.55, 200)                                     # big tree trunk
        Ms = cv2.resize(P.astype(f32) / 255, (sw_, sh_), interpolation=cv2.INTER_AREA)
        Mb = cv2.GaussianBlur(Ms, (0, 0), 3.0)
        w = 0.7 * np.clip((yy - LAWN_SRC) / 300.0, 0, 1) ** 0.8                            # soften away from the bases
        S = (Ms * (1 - w) + Mb * w) * lawn
        Lm = cv2.GaussianBlur(lawn.astype(f32), (0, 0), 0.7)
        fill = occ.astype(f32)                                                  # foliage / house / hedges: backlit
        fg = self.fg; M = np.array([[fg.s, 0, 0], [0, fg.s, fg.oy]], np.float64)
        def warp(m):
            o = cv2.warpAffine(m, M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            if not self.L.vertical:
                yb = int(math.floor(sh_ * fg.s + fg.oy)) - 2
                if yb < self.H: o[yb:] = o[yb - 1:yb]
            return o.astype(f32)
        return warp(S), warp(Lm), warp(fill)

    # -------------------------------------------------------------------------------------------- layers
    def stars_layer(self, t, glare, day):
        W, H = self.W, self.H
        acc = np.zeros((H + 2, W + 2, 3), f32)
        nt = np.sin(t * 13.1 + self.sph) * 0.5 + np.sin(t * 23.7 + self.sph * 1.7) * 0.3 + np.sin(t * 37.3 + self.sph * 2.3) * 0.2
        sig = np.clip(0.10 + 0.35 * np.exp(-self.sz / 0.15), 0.08, 0.6)
        tw = np.exp(sig * nt * 1.6 - 0.5 * sig * sig)
        ext = np.clip(self.sz / 0.12, 0, 1) ** 0.7
        # glare of the supernova / daylight swallows the faint stars
        lim = 7.0 - 5.5 * glare - 9.0 * day
        vis = np.clip((lim - self.smag) / 0.8, 0, 1)
        fl = self.sflux * tw * ext * vis
        m = fl > 1e-4
        xs, ys = self.sx[m], self.sy[m]; val = (fl[m, None] * self.scol[m]).astype(f32)
        x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int); fx = (xs - x0)[:, None]; fy = (ys - y0)[:, None]
        for oy, ox, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, (np.clip(y0 + oy, 0, H + 1), np.clip(x0 + ox, 0, W + 1)), val * wg)
        acc = acc[:H, :W]
        for j in self.glint:
            if vis[j] <= 0: continue
            g = self.sflux[j] * 0.05 * vis[j] * (1 + 0.3 * math.sin(t * 5 + self.sph[j])); c = self.scol[j] * 0.6 + 0.4
            splat(acc, self.sx[j], self.sy[j], 50, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 14) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 14)) * g)[..., None] * c)
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = acc * (acc.max(2, keepdims=True) > 0.35)
        st += cv2.GaussianBlur(big, (0, 0), 2.2) * 2.2 + cv2.GaussianBlur(big, (0, 0), 8.0) * 2.0
        return st

    def betelgeuse(self, img, t, k):
        """the red supergiant as it is tonight: a bright orange star with a warm halo, gently breathing"""
        if k <= 0: return
        cx, cy = self.C; c = self.betel_col
        br = k * (1 + 0.08 * math.sin(t * 2.1) + 0.05 * math.sin(t * 7.3))
        g = 0.6 + 0.4 * k
        splat(img, cx, cy, 260, lambda d, dx, dy: (
            (np.exp(-(d / 1.6) ** 2) * 9.0 + np.exp(-d / 5.0) * 1.3 + np.exp(-d / 22) * 0.20 * g + np.exp(-d / 80) * 0.05 * g) * br
            + (np.exp(-np.abs(dy) / 0.9) * np.exp(-np.abs(dx) / 30) + np.exp(-np.abs(dx) / 0.9) * np.exp(-np.abs(dy) / 30)) * 0.35 * br)[..., None] * c)

    def beams_layer(self, t, I, col_list):
        """rainbow / coloured light beams fanning out of the point (half res)"""
        d, phi = self.hd, self.hphi
        acc = np.zeros(d.shape + (3,), f32)
        spin = 0.05 * (t - T_IGN)
        rad = (1 - np.exp(-(d + 4) / 25)) * (np.exp(-d / 1100) * 0.9 + 0.12)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            gg = np.exp(-(dp / wd) ** 2 * 1.6)
            Ib = b["I"] * (0.70 + 0.30 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.30 + t * 0.05) % 1.0
            acc += pal_list(col_list, x) * (gg * Ib)[..., None]
        return acc * rad[..., None] * 0.45 * I

    def supernova(self, img, t, I, T, flare):
        """the point: HDR core, multi-scale halo, chromatic 8-blade spikes"""
        if I <= 0: return
        c = vivid(bbcolor(T), 1.5)
        cw = c * 0.45 + 0.55
        h0, h1, h2, h3 = self.halo
        pul = 1 + 0.06 * math.sin(t * 3.1) + 0.04 * math.sin(t * 8.7)
        img += ((h0 * 60.0 + h1 * 4.0) * I * pul)[..., None] * cw + ((h2 * 0.4 + h3 * 0.04) * I * (0.5 + 0.5 * flare))[..., None] * c
        flat = img.reshape(-1, 3)
        Ls = (380 + 1300 * flare) * min(I, 1.6) ** 0.5
        for s in self.spikes:
            L = Ls * (1.0 if s["long"] else 0.45) * pul
            base = np.exp(-np.abs(s["pp"]) / s["w"]) * 3.2 * I
            for ch, Lk, off in ((0, 1.0, 1.2), (1, 0.84, 0.0), (2, 0.70, -1.2)):            # red reaches furthest + lateral split
                prof = np.exp(-np.abs(s["pp"] - off) / s["w"]) / np.maximum(np.exp(-np.abs(s["pp"]) / s["w"]), 1e-9)
                flat[s["idx"], ch] += base * prof * np.exp(-s["al"] / (L * Lk)) * (0.45 + 0.55 * c[ch])
            if s["long"] and flare > 0.1:                                                   # rainbow dispersion along the long spikes
                pc = palette((s["al"] / 520.0 - t * 0.15) % 1.0)
                flat[s["idx"]] += (np.exp(-np.abs(s["pp"]) / (s["w"] * 4)) * np.exp(-s["al"] / (L * 1.4)) * 0.45 * I * flare)[:, None] * pc * smooth(60, 260, s["al"])[:, None]

    def shockwave(self, t, t0, R1=2600, dur=1.7, k=2.4):
        u = t - t0
        if not (0 <= u < dur): return None
        R = R1 * (u / dur) ** 0.62; wdt = 10 + 40 * u
        d = self.hd * 2
        ring = np.zeros(d.shape + (3,), f32)
        for ch, off in ((0, 16), (1, 0), (2, -16)):
            ring[..., ch] = np.exp(-((d - R - off) / wdt) ** 2)
        ring += palette((d / 700 - t * 0.6) % 1.0) * np.exp(-((d - R + 70) / (wdt * 3)) ** 2)[..., None] * 0.5
        return ring * k * math.exp(-u / (dur * 0.45))

    def neutrino_streaks(self, t, amt):
        """radial streaks rushing out of the star towards us (through sky, trees and ground alike)"""
        W, H = self.W, self.H; hw, hh = W // 2, H // 2
        lay = np.zeros((hh, hw, 3), f32)
        n = self.nu; cx, cy = self.C[0] / 2, self.C[1] / 2
        age = ((t / n["per"]) + n["t0"]) % 1.0
        r0 = 6 * np.exp(5.6 * age); r1 = 6 * np.exp(5.6 * np.maximum(age - 0.05, 0))
        c, s = np.cos(n["th"]), np.sin(n["th"])
        cols = palette((n["hue"] * 0.35 + 0.48) % 1.0) * 0.6 + np.array([0.3, 0.5, 1.0], f32) * 0.4
        I = n["I"] * np.sin(np.pi * age) ** 1.5 * amt
        for i in np.where(I > 0.02)[0]:
            p0 = (int((cx + c[i] * r1[i]) * 4), int((cy + s[i] * r1[i]) * 4)); p1 = (int((cx + c[i] * r0[i]) * 4), int((cy + s[i] * r0[i]) * 4))
            cv2.line(lay, p0, p1, tuple(float(v) for v in cols[i] * I[i] * 1.6), 1, cv2.LINE_AA, 2)
        lay = lay + cv2.GaussianBlur(lay, (0, 0), 2.5) * 1.5
        return cv2.resize(lay, (W, H), interpolation=cv2.INTER_LINEAR)

    def ripple(self, img, t):
        """faint refractive ripples (neutrino 'pings') running out from the star across sky and park"""
        tot = np.zeros(self.hd.shape, f32); edge = np.zeros_like(tot)
        for tr in RIPPLES:
            u = t - tr
            if 0 <= u < 1.6:
                R = 1500 * u ** 0.8; d = self.hd * 2
                env = np.exp(-((d - R) / 120) ** 2) * math.exp(-u / 0.9)
                tot += np.sin((d - R) / 18) * env
                edge += np.exp(-((d - R) / 10) ** 2) * math.exp(-u / 0.7)
        if not tot.any(): return img, None
        W, H = self.W, self.H
        D = cv2.resize(tot, (W, H), interpolation=cv2.INTER_LINEAR) * 5.0
        mx = self.xx + D * np.cos(self.phi); my = self.yy + D * np.sin(self.phi)
        img = cv2.remap(img, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        e = cv2.resize(edge, (W, H), interpolation=cv2.INTER_LINEAR)
        return img, e[..., None] * np.array([0.25, 0.55, 1.0], f32) * 0.35

    def god_rays(self, img, amt):
        """radial blur of the bright sky about the star, occluded by the plate"""
        W, H = self.W, self.H; q = 4
        sm = cv2.resize(img * (1 - self.a), (W // q, H // q), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 0.6, 0)
        cx, cy = self.C[0] / q, self.C[1] / q
        acc = sm.copy()
        for k in range(6):
            s = 1.0 - 0.12 / (2 ** (k * 0.5))
            M = np.float32([[s, 0, (1 - s) * cx], [0, s, (1 - s) * cy]])
            acc = (acc + cv2.warpAffine(acc, M, (W // q, H // q), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)) * 0.5
            acc = acc * 1.6
        return cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * amt * 0.25

    # -------------------------------------------------------------------------------------------- foreground
    def foreground(self, t, I, T, day):
        fg = self.fg
        base = self.fg_night
        lamp_on = (1 - day) * (1 - 0.6 * min(I, 1.0))
        if I > 0:
            c = vivid(bbcolor(T), 1.3); c = c / max(c.max(), 1e-4)
            Lk = min(I, 1.4) * 2.2
            lit = self.lit_alb * c * Lk * (1 - 0.78 * self.shadow)[..., None] * self.lawn[..., None]
            back = self.lit_alb * c * Lk * 0.10 * self.fill[..., None]                       # backlit foliage: faint fill
            rim = self.rim[..., None] * c * Lk * 0.40
            base = base + lit + back + rim
        out = base
        if lamp_on > 0.01: out = fg.lamps_light(out, lamp_on * 1.4, t)
        if day > 0: out = out * (1 - day) + self.fg_day * day
        return out

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        W, H = self.W, self.H
        I, T, flare = sn_state(t)
        day = day_level(t)
        bk = betel_state(t)
        # ---- sky
        sky = self.night * (1 + 0.10 * math.sin(t * 0.7))
        sky = sky + self.mw * (1 - 0.55 * min(I, 1.0))
        sky = sky + self.airglow_layer(t)
        if I > 0:                                                         # the supernova lights the night sky: blue-violet glow
            c = vivid(bbcolor(T), 1.4)
            sky = sky * (1 + 0.25 * min(I, 1.5)) + (self.halo[3] * 0.07 * min(I, 1.5))[..., None] * (c * 0.5 + np.array([0.1, 0.15, 0.5], f32))
        sky = sky + self.stars_layer(t, min(I, 1.0) * 0.6, day) * self.above
        if day > 0:
            dsk = self.daysky + self.cirrus[..., None] * np.array([1.0, 1.0, 1.05], f32)
            sky = sky * (1 - day) + dsk * day
        self.betelgeuse(sky, t, bk * (1 - day))
        if flare > 0 and I > 0:
            cl = [(0.55, 0.75, 1.0), (0.85, 0.45, 1.0), (0.30, 1.0, 0.95), (1.0, 0.55, 0.85), (0.6, 0.95, 1.0)]
            if T < 8000:
                w = ramp(T, 7000, 3500)
                cl = [tuple(np.array(a) * (1 - w) + np.array(b) * w) for a, b in zip(cl, [(1.0, 0.45, 0.10), (1.0, 0.25, 0.25), (1.0, 0.70, 0.20), (1.0, 0.35, 0.50), (1.0, 0.55, 0.15)])]
            bm = self.beams_layer(t, flare * min(I, 1.3) * (1 - 0.55 * day), cl)
            sky = sky + cv2.resize(bm, (W, H), interpolation=cv2.INTER_LINEAR)
        # ---- foreground
        fgc = self.foreground(t, I * (1 - day), T, day)
        img = sky * (1 - self.a) + fgc * self.a
        # ---- the point itself (over the sky; nothing occludes it)
        self.supernova(img, t, I * (1.0 if day <= 0 else 1 - 0.35 * day), T, flare)
        # ---- flare build-up + detonation flash, shockwaves
        if T_FLARE0 <= t < T_IGN:
            u = (t - T_FLARE0) / (T_IGN - T_FLARE0)
            img += (self.halo[1] * 3 * u ** 3 + self.halo[2] * 0.4 * u ** 4)[..., None] * np.array([0.9, 0.9, 1.0], f32)
        for t0, R1, k in ((T_IGN, 2700, 2.6), (T_IGN + 0.35, 2300, 1.3), (T_MOON - 0.05, 2200, 1.4), (T_BACK, 2000, 1.2)):
            ring = self.shockwave(t, t0, R1, 1.7, k)
            if ring is not None:
                if t0 == T_BACK: ring = ring * np.array([1.0, 0.6, 0.35], f32)
                img += cv2.resize(ring, (W, H), interpolation=cv2.INTER_LINEAR)
        if t >= T_IGN - 0.03:
            u = t - T_IGN
            img += 9.0 * math.exp(-max(u, 0) / 0.10) * ease((u + 0.03) / 0.03) * np.array([0.85, 0.92, 1.0], f32)
        for tc, k in ((T_DAY, 2.5), (T_NIGHT, 1.2)):                     # cuts: quick flashes
            u = t - tc
            if -0.05 < u < 0.6: img += k * math.exp(-max(u, 0) / 0.07) * ease((u + 0.05) / 0.05)
        if abs(t - T_BACK) < 0.8:                                        # pulse back to tonight
            u = t - T_BACK
            img += 1.5 * math.exp(-max(u, 0) / 0.09) * ease((u + 0.05) / 0.05) * np.array([1.0, 0.75, 0.55], f32)
        # light front rolling towards us (twist)
        if T_FRONT <= t < T_END - 0.35:
            u = (t - T_FRONT) / (T_END - 0.35 - T_FRONT)
            R = 20 + 2600 * u ** 1.6; wdt = 5 + 60 * u
            d = self.hd * 2
            ring = np.zeros(d.shape + (3,), f32)
            for ch, off in ((0, 14 + 30 * u), (1, 0), (2, -14 - 30 * u)):
                ring[..., ch] = np.exp(-((d - R - off) / wdt) ** 2)
            ring += palette((d / 600 - t * 0.5) % 1.0) * np.exp(-((d - R + 60 * (1 + u)) / (wdt * 2.0)) ** 2)[..., None] * 0.35
            ring += np.exp(-((d - R * 0.82) / (wdt * 0.8)) ** 2)[..., None] * np.array([1.0, 0.55, 0.25], f32) * 0.35
            img += cv2.resize(ring, (W, H), interpolation=cv2.INTER_LINEAR) * 1.6 * (1 - u) ** 1.2 * ramp(t, T_FRONT, T_FRONT + 0.2)
        # ---- neutrinos
        if T_NEUT <= t < T_IGN + 0.5:
            img, edge = self.ripple(img, t)
            if edge is not None: img += edge
            amt = ramp(t, T_STREAK0, T_STREAK0 + 0.5) * (1 - ramp(t, T_STREAK1 - 0.4, T_STREAK1))
            if amt > 0.01: img += self.neutrino_streaks(t, amt * 0.35)
        # ---- god rays
        if I > 0.05:
            img += self.god_rays(img, min(I, 1.5) * (1 - 0.7 * day)) * (1 - 0.75 * self.a)
        img = self.chroma_bloom(img, 0.85 - 0.15 * min(I, 1.0))
        expo = 1.25 * (1 - 0.15 * day) / (1 + 0.20 * min(I, 2.0) * (1 - day))
        out = tonemap(img, expo)
        out = self.grade(out, day)
        out = self.chroma(out)
        out = finish(out, t, grain=0.009, vignette=0.15)
        self.overlay(out, t)
        return out

    def airglow_layer(self, t):
        """slowly drifting airglow bands low over the hedge (green + magenta), keeps the night sky alive"""
        if self.airx is None:
            q = 4; W, H = self.W, self.H
            self.airx = np.mgrid[0:H // q, 0:W // q].astype(f32)[::-1] * q
            self.agb = cv2.resize(self.ag_band, (W // q, H // q), interpolation=cv2.INTER_AREA)
        xx, yy = self.airx
        u = (xx * 0.05 + t * 2.0) % 256; v = (yy * 0.08) % 128
        n1 = cv2.remap(self.ag_src, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        n2 = cv2.remap(self.ag_src, ((xx * 0.03 - t * 1.4 + 90) % 256).astype(f32), ((yy * 0.05 + 40) % 128).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        g = np.clip(0.5 + 0.7 * n1, 0, 1)[..., None] * np.array([0.02, 0.09, 0.05], f32) + np.clip(0.5 + 0.7 * n2, 0, 1)[..., None] * np.array([0.07, 0.015, 0.06], f32)
        g = g * self.agb[..., None]
        return cv2.resize(g, (self.W, self.H), interpolation=cv2.INTER_LINEAR)

    def grade(self, out, day):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * (1.22 - 0.1 * day)
        return np.clip(out + np.array([0.010, 0.008, 0.022], f32) * (1 - out) * (1 - day), 0, 1)

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
        W, H = self.W, self.H
        o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    # -------------------------------------------------------------------------------------------- overlay (sRGB)
    def readout(self, out, t, t0, t1, big, l2, l3=None, col=(255, 146, 16), size=1.0):
        L = self.L; W = L.W
        a = ramp(t, t0, t0 + 0.25) * (1 - ramp(t, t1 - 0.25, t1))
        if a <= 0.01: return
        if L.vertical: x, ys = W / 2, (1290, 1372, 1428)
        else: x, ys = W / 2, (770, 845, 895)
        dy = (1 - a) * 18
        pop = 1 + 0.25 * math.exp(-max(t - t0, 0) / 0.08) * (t - t0 < 0.4)
        sz = int(L.hud_size * 1.45 * size * min(pop, 1.25))
        rgba, _ = word_layer(big, sz, W * 0.9 if L.vertical else 1100, fill=col)
        composite(out, rgba, x, ys[0] + dy, a)
        if l2: hud_text(out, l2, x, ys[1] + dy, int(L.hud_size * 0.62), "Black", (255, 255, 255), a, 0.08, display=True)
        if l3: hud_text(out, l3, x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (235, 240, 250), a, 0.10, display=True)

    def star_label(self, out, t):
        """hook: leader line + BETELGEUSE · 550 LY (and the empty-shoulder marker at the end of the fade)"""
        L = self.L; v = L.vertical; cx, cy = self.C
        a = ramp(t, T_LABEL, T_LABEL + 0.2) * (1 - ramp(t, T_NEUT + 0.2, T_NEUT + 0.6))
        if a > 0.01:
            p = ease((t - T_LABEL) / 0.3)
            col = (255, 150, 60)
            ex, ey = cx + (85 if v else 80) * p, cy - (95 if v else 70) * p
            ov = out.copy()
            cv2.circle(ov, (int(cx * 4), int(cy * 4)), int(30 * 4 * (1 + 0.08 * math.sin(t * 6))), (1.0, 0.62, 0.3), 2, cv2.LINE_AA, 2)
            sx0, sy0 = cx + 22, cy - 16
            cv2.line(ov, (int(sx0 * 4), int(sy0 * 4)), (int(ex * 4), int(ey * 4)), (1.0, 0.7, 0.4), 2, cv2.LINE_AA, 2)
            hx = ex + (330 if v else 280) * p
            cv2.line(ov, (int(ex * 4), int(ey * 4)), (int(hx * 4), int(ey * 4)), (1.0, 0.7, 0.4), 2, cv2.LINE_AA, 2)
            out[:] = out * (1 - a) + ov * a
            lay = glow_text("BETELGEUSE", 64 if v else 54, (1.0, 0.55, 0.18), "Black", 400)
            put_glow(out, lay, ex + 6 + lay[3] / 2, ey - (42 if v else 36), a * ease((t - T_LABEL - 0.1) / 0.2))
            hud_text(out, "550 LY · RED SUPERGIANT", ex + 8, ey + (28 if v else 24), 28 if v else 25, "Bold", (255, 225, 200), a * ease((t - T_LABEL - 0.25) / 0.25), 0.08, display=True, anchor="l")
        # the empty shoulder
        a2 = ramp(t, T_GONE - 0.1, T_GONE + 0.2) * (1 - ramp(t, T_BACK - 0.2, T_BACK))
        if a2 > 0.01:
            ov = out.copy()
            r = int(34 * 4 * (1 + 0.1 * math.sin(t * 5)))
            for k in range(16):
                a0 = k * 22.5 + t * 40
                cv2.ellipse(ov, (int(cx * 4), int(cy * 4)), (r, r), 0, a0, a0 + 12, (1.0, 0.45, 0.3), 3, cv2.LINE_AA, 2)
            out[:] = out * (1 - a2) + ov * a2

    def orion_lines(self, out, t):
        a = lines_alpha(t)
        if a <= 0.01: return
        gone = t > T_FADE1 and t < T_BACK
        ov = out.copy()
        for p, q in ORION_LINES:
            if p not in self.named or q not in self.named: continue
            (x0, y0), (x1, y1) = self.named[p], self.named[q]
            dl = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / dl, (y1 - y0) / dl
            g = 18
            ax, ay, bx, by = x0 + ux * g, y0 + uy * g, x1 - ux * g, y1 - uy * g
            col = (0.55, 0.75, 1.0)
            if gone and "Betelgeuse" in (p, q):                                     # the broken lines into the empty shoulder
                if p == "Betelgeuse": ax, ay, bx, by = bx, by, ax, ay
                n = 7
                for k in range(n):
                    if k % 2: continue
                    u0, u1 = k / n, (k + 1) / n
                    cv2.line(ov, (int((ax + (bx - ax) * u0) * 4), int((ay + (by - ay) * u0) * 4)), (int((ax + (bx - ax) * u1) * 4), int((ay + (by - ay) * u1) * 4)),
                             (1.0, 0.45, 0.30), 2, cv2.LINE_AA, 2)
                continue
            cv2.line(ov, (int(ax * 4), int(ay * 4)), (int(bx * 4), int(by * 4)), col, 2, cv2.LINE_AA, 2)
        out[:] = out * (1 - 0.65 * a) + ov * 0.65 * a

    def alert(self, out, t):
        a = ramp(t, T_ALERT, T_ALERT + 0.12) * (1 - ramp(t, LN["boom"]["start"] - 0.2, LN["boom"]["start"] + 0.1))
        if a <= 0.01: return
        L = self.L; v = L.vertical
        w, h = (900, 150) if v else (840, 130)
        card = alert_card(w, h, 1.0)
        u = t - T_ALERT
        drop = (1 - ease(u / 0.22)) * -160 + 10 * math.sin(min(u, 0.6) * 18) * math.exp(-u / 0.12)
        y = (330 if v else 120) + drop
        shake = 3 * math.sin(t * 70) * math.exp(-max(t - T_ALERT, 0) / 0.25)
        composite(out, card, L.W / 2 + shake, y, a)

    def overlay(self, out, t):
        self.orion_lines(out, t)
        self.star_label(out, t)
        self.alert(out, t)
        # readouts (factual)
        self.readout(out, t, T_IGN + 0.45, T_DAY - 0.05, "MAGNITUDE ≈ −11", "AS BRIGHT AS A HALF-TO-FULL MOON", "ALL OF IT FROM ONE POINT", (150, 205, 255))
        self.readout(out, t, T_DAY + 0.35, T_NIGHT - 0.05, "VISIBLE IN DAYLIGHT", "FOR WEEKS TO MONTHS", None, (120, 200, 255))
        if T_NIGHT + 0.15 < t < T_FADE1 + 0.25:
            m = month_of(t)
            self.readout(out, t, T_NIGHT + 0.15, T_FADE1 + 0.25, f"MONTH {m}", "FADING · BLUE-WHITE → ORANGE-RED", None, (255, 150, 60), 1.15)
        self.readout(out, t, T_GONE - 0.15, T_SAFE + 0.05, "GONE FOR GOOD", "ORION LOSES ITS SHOULDER", "LEFT BEHIND: A NEUTRON STAR (MOST LIKELY)", (255, 120, 70))
        self.readout(out, t, T_SAFE + 0.25, T_550 - 0.1, "550 LIGHT-YEARS", "DANGER ZONE: WITHIN ~50 LY", "WE'RE MORE THAN 10× FARTHER", (130, 255, 170))
        self.readout(out, t, T_550 + 0.05, T_FRONT, "THE 1400s", "WHEN THE LIGHT WE SEE TONIGHT LEFT", None, (255, 170, 60), 1.15)
        self.caps.draw(out, t)


# ------------------------------------------------------------------------------------------------- render
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
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.W, sc.H, FPS, crf=17)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(vertical, ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render"""
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.W, sc.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=17)
    for i in range(int(round(DUR * FPS))):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "frames", int(round(DUR * FPS)))
        for k in ("T_LABEL", "T_NEUT", "T_ALERT", "T_FLARE0", "T_IGN", "T_MOON", "T_DAY", "T_NIGHT", "T_FADE1", "T_GONE", "T_SAFE", "T_550", "T_BACK", "T_FRONT"):
            print(f"  {k:9s} {globals()[k]:.2f}")
        for vert in (True, False):
            sc = Scene(vert); print("vert" if vert else "wide", "horizon", round(sc.hz), "hy", round(sc.hy), {k: (round(x), round(y)) for k, (x, y) in sc.named.items()})
        sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
