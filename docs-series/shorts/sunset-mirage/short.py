"""WHEN YOU SEE THE SUN TOUCH THE HORIZON, IT'S ALREADY GONE -- vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the user's valley plate (B_valley.png) at sunset.
The visible Sun is rendered THROUGH a refraction model: every pixel's apparent altitude a (arcmin above the ridge) is
mapped to a true altitude h = a - R(a) (Bennett 1982 standard refraction), and the true, round, limb-darkened disc is
sampled there. That gives the real lift (34.5' at the horizon, more than the Sun's 32' width) and the real squash
(lower limb lifted more than the upper) for free. Angular scale: K px per arcminute (Sun radius = 16' = 16 K px).
  hook: golden sunset, the Sun's lower edge touches the ridge
  reveal: the TRUE Sun as a dashed hologram ghost below the horizon, X-ray cutaway through the mountains
  how: rainbow air layers (denser = brighter toward the ground), curved glowing ray paths ghost -> camera
  squash: oval + stepped "Etruscan vase" mirage edge, then a big GREEN FLASH on the last sliver
  bonus: +4-6 min of daylight; myth-bust: the 8-min light delay does not shift the Sun's direction (aberration ~20")
  end: "was a mirage" -> white-out -> the Sun pops back to its start position (loops)
Built on docs-series/shorts/lib (read-only). Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py info                   timeline + refraction numbers
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, kf, fbm2, lum
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S8-sunset-mirage"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.35

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
NFR = int(round(DUR * FPS))
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------- refraction (arcmin)
def refr(a):
    """standard refraction (Bennett 1982, 10 C, 1010 hPa) for APPARENT altitude a [arcmin] -> arcmin"""
    ad = np.maximum(np.asarray(a, np.float64) / 60.0, -0.9)
    return 1.0 / np.tan(np.radians(ad + 7.31 / (ad + 4.4)))


def apparent(h):
    """apparent altitude [arcmin] of a point at true altitude h [arcmin] (fixed-point iteration)"""
    a = h + 34.0
    for _ in range(40): a = h + float(refr(a))
    return a


SEMI = 16.0                                            # solar semi-diameter [arcmin] (15.8'-16.3' over the year)
R_HOR = float(refr(0.0))                               # 34.5' at the horizon
HC_TOUCH = -R_HOR + SEMI                               # lower limb apparently ON the horizon -> true centre -18.5'
HC_GONE = -R_HOR - SEMI                                # upper limb apparently on the horizon (= "sunset", -50.5')
HC_START = (30.0 - float(refr(30.0))) + SEMI           # start: lower limb 30' above the ridge (apparent)
A_TOP_TOUCH = apparent(HC_TOUCH + SEMI)                # apparent upper limb when the lower limb touches
SQUASH = A_TOP_TOUCH / (2 * SEMI)                      # apparent height / width
R_TOP_TOUCH = float(refr(A_TOP_TOUCH))

# ------------------------------------------------------------------------------------------------- timeline
T_TOUCH = wt("hook", "THERE") + 0.15
T_REVEAL = wt("reveal", "REAL") - 0.08
T_SET = wt("reveal", "SET")
T_HOW = LN["how"]["start"]
T_BENDS = wt("how", "BENDS"); T_DENSER = wt("how", "DENSER"); T_CURVES = wt("how", "CURVES"); T_LIFT = wt("how", "LIFTING")
T_SQ = LN["squash"]["start"]; T_SQW = wt("squash", "SQUASHING"); T_OVAL = wt("squash", "OVAL")
T_LAST = wt("squash", "LAST"); T_GF = wt("squash", "GREEN")
T_BONUS = LN["bonus"]["start"]; T_MIN = wt("bonus", "MINUTES")
T_MYTH = LN["myth"]["start"]; T_MYTHW = wt("myth", "MYTH")
T_END = LN["end"]["start"]; T_MIRAGE = wt("end", "MIRAGE")
T_POP = min(T_MIRAGE + 0.55, DUR - 0.85)               # white-out peak -> the Sun is back at its start position


def sun_hc(t):
    """true altitude of the Sun's centre [arcmin]"""
    if t >= T_POP: return HC_START
    return kf(t, [(0.0, HC_START), (T_TOUCH, HC_TOUCH), (T_SQ + 0.3, HC_TOUCH - 1.2), (T_OVAL + 0.2, HC_TOUCH - 10.0),
                  (T_LAST, -44.5), (T_GF, -48.2), (T_GF + 0.5, -51.0), (T_POP - 0.02, -66.0)])


def green_amt(t):
    return ramp(t, T_GF - 0.30, T_GF + 0.06) * math.exp(-max(0.0, t - (T_GF + 0.18)) / 0.55)


def green_wash(t):
    """the wide green wash (halo, ground tint, ring) fades fast so the sliver stays the star"""
    return ramp(t, T_GF - 0.30, T_GF + 0.06) * math.exp(-max(0.0, t - (T_GF + 0.10)) / 0.30)


def white_level(t):
    return ramp(t, T_POP - 0.75, T_POP) ** 2.2 if t < T_POP else math.exp(-(t - T_POP) / 0.13)


CYAN, GOLD, GREEN, MAGENTA, ORANGE, WHITE = ((0.30, 0.85, 1.0), (1.0, 0.70, 0.22), (0.10, 1.0, 0.25), (1.0, 0.30, 0.80),
                                             (1.0, 0.45, 0.10), (1.0, 0.95, 0.90))
# flash + chromatic shockwave events: (time, colour, strength)
EVENTS = [(T_TOUCH - 0.05, GOLD, 0.6), (T_REVEAL, CYAN, 1.2), (T_BENDS, MAGENTA, 0.8), (T_OVAL, ORANGE, 0.8),
          (T_GF + 0.30, GREEN, 0.9), (T_MIN, GOLD, 0.9), (T_MYTHW, MAGENTA, 1.0), (T_POP, WHITE, 1.4)]


def fmt_readouts():
    return dict(
        refr=(T_REVEAL + 0.85, T_SQ + 0.15, [("REFRACTION ≈ 0.57°", (120, 230, 255)), ("MORE THAN THE SUN'S WIDTH (0.53°)", None),
                                            ("34′ OF BENDING RIGHT AT THE HORIZON", None)]),
        squash=(T_OVAL - 0.35, T_GF - 0.20, [(f"SQUASHED ≈ {round(100 * (1 - SQUASH))}%", (255, 160, 60)),
                                             ("THE LOWER EDGE IS LIFTED MORE", None),
                                             (f"{R_HOR:.0f}′ AT THE BOTTOM · {R_TOP_TOUCH:.0f}′ AT THE TOP", None)]),
        green=(T_GF - 0.05, T_BONUS - 0.05, [("GREEN FLASH", (90, 255, 120)), ("GREEN BENDS SLIGHTLY MORE THAN RED", None),
                                             ("LASTS ~1–2 S · NEEDS A CLEAR, SHARP HORIZON", None)]),
        bonus=(T_MIN - 0.25, T_MYTH - 0.05, [("+4–6 MIN", (255, 200, 70)), ("OF DAYLIGHT, EVERY DAY", None),
                                             ("SUNRISE ~2–3 MIN EARLIER · SUNSET ~2–3 MIN LATER", None)]),
        myth=(T_MYTH + 0.35, T_END - 0.05, [("MYTH BUSTED", (255, 90, 200)), ("8 MIN 19 S LIGHT DELAY ≠ A 2° SHIFT", None),
                                           ("REAL DIRECTION SHIFT: ~20″ (ABERRATION)", None)]),
    )


def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def bezier(p0, p1, p2, p3, n=90):
    u = np.linspace(0, 1, n)[:, None]
    return ((1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u * u * p2 + u ** 3 * p3).astype(np.float64)


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H
        self.V = vertical
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.70)
        self.K = 6.25 if vertical else 5.0                 # px per arcminute
        self.R = SEMI * self.K
        self.sx = 540.0 if vertical else 1250.0
        c = int(self.sx); r = int(self.R)
        self.yh = float(np.min(fg.skyline[c - r:c + r]))  # the horizon line = ridge top under the Sun
        self.cam = np.array([self.sx, H + 70.0]) if vertical else np.array([self.sx - 60, H + 90.0])
        self.BH = 760.0 if vertical else 470.0             # height of the air-layer stack above the ridge
        if vertical: L.cap_y = 1010
        else: L.cap_y = 175; L.cap_size = 104
        self.caps = Captions(L, WORDS, emphasis={"SUN", "REALLY", "REAL", "SET", "BELOW", "RIDGE", "BENDS", "DENSER", "CURVES",
                                                 "WIDTH", "OVAL", "GREEN", "MINUTES", "LONGER", "8-MINUTE", "MYTH", "MIRAGE"})
        self.ro = fmt_readouts()
        # grids
        hh, hw = H // 2, W // 2
        self.hy, self.hx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(f32)
        e = np.clip((self.yh - self.hy) / self.yh, 0, 1); self.e = e
        # sky palettes (linear), half res
        def sky_of(zen, mid, hor, wh):
            b = np.array(zen, f32) + (np.array(mid, f32) - np.array(zen, f32)) * smooth(0.80, 0.18, e)[..., None]
            k = np.exp(-e / wh)[..., None]
            return (b * (1 - k) + np.array(hor, f32) * k).astype(f32)
        n = cv2.resize(fbm2((64, 64), 7, 3.0), (hw, hh), interpolation=cv2.INTER_CUBIC)[..., None]
        self.gold = sky_of((0.035, 0.06, 0.30), (0.62, 0.13, 0.42), (1.25, 0.24, 0.03), 0.12) * (1 + 0.04 * n)
        self.dusk = sky_of((0.03, 0.05, 0.24), (0.32, 0.08, 0.42), (1.20, 0.30, 0.06), 0.09) * (1 + 0.04 * n)
        # foreground prep
        a = fg.a; self.a = a[..., None]
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a
        near = np.exp(-np.abs(self.xx - self.sx) / (520 if vertical else 800)) * (0.35 + 0.65 * np.exp(-np.maximum(self.yy - self.yh, 0) / 260))
        self.rim = (rim * (0.4 + 0.6 * near)).astype(f32)
        self.fg_gold = (fg.rgb * np.array([1.06, 0.97, 0.86], f32) + fg.flat * np.array([0.06, 0.03, 0.05], f32)).astype(f32)
        self.fg_dusk = (fg.flat * np.array([0.30, 0.25, 0.46], f32) + fg.rgb * np.array([0.18, 0.11, 0.08], f32)).astype(f32)
        Y = lum(fg.rgb) ** 0.5
        gx = cv2.Sobel(Y, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Y, cv2.CV_32F, 0, 1, ksize=3)
        E = np.sqrt(gx * gx + gy * gy); E = np.clip(E / np.percentile(E[a > 0.5], 97), 0, 1.5)
        E = np.maximum(E, cv2.GaussianBlur(np.clip(a - np.roll(a, 3, 0), 0, 1), (0, 0), 1.0) * 2)   # ridge outlines
        self.edges = cv2.GaussianBlur(E, (0, 0), 0.7).astype(f32)
        # beams
        r = np.random.default_rng(5)
        self.beams = [dict(a=-np.pi / 2 + (i - 4) * 0.33 + r.uniform(-0.1, 0.1), w=r.uniform(0.07, 0.13), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(9)]
        # golden motes
        n = 170
        self.mote = dict(x=r.uniform(0, W, n), y0=r.uniform(0, 1, n), sp=r.uniform(0.010, 0.035, n), ph=r.uniform(0, 6.28, n),
                         sz=r.uniform(0.3, 1.0, n) ** 2, wob=r.uniform(8, 30, n))
        self.shim = fbm2((256, 256), 81, 2.0)

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def ypx(self, alt): return self.yh - self.K * alt  # arcmin -> screen y

    # ----------------------------------------------------------------------------------------------- state
    def state(self, t):
        hc = sun_hc(t)
        sv = smooth(HC_GONE - 0.5, HC_TOUCH, hc)               # how much of the disc is visible (approx.)
        a_top = apparent(hc + SEMI); a_bot = apparent(hc - SEMI)
        app_c = 0.5 * (max(a_top, 0) + max(a_bot, 0)) if a_top > 0 else 0.0
        gf = green_amt(t)
        dusk = ramp(t, T_GF + 0.2, T_GF + 3.2) * (t < T_POP)
        g_vis = (ramp(t, T_REVEAL - 0.05, T_REVEAL + 0.30) * (1 - ramp(t, T_GF + 0.5, T_GF + 1.3))
                 + 0.85 * ramp(t, T_END + 0.05, T_END + 0.5) * (1 - ramp(t, T_POP - 0.25, T_POP)))
        g_pop = 1 + 0.35 * math.exp(-max(0, t - T_REVEAL) / 0.12) * (t > T_REVEAL) * (t < T_REVEAL + 1)
        rays = (ramp(t, T_BENDS - 0.25, T_BENDS + 0.5) * (1 - ramp(t, T_SQ + 0.3, T_SQ + 1.3))
                + 0.7 * ramp(t, T_END + 0.2, T_END + 0.8) * (1 - ramp(t, T_POP - 0.2, T_POP)))
        bands = (ramp(t, T_HOW - 0.3, T_HOW + 0.4) * (1 - 0.55 * ramp(t, T_SQ + 0.5, T_SQ + 1.5)) * (1 - ramp(t, T_GF + 0.6, T_GF + 1.6))
                 + 0.75 * ramp(t, T_END, T_END + 0.6) * (1 - ramp(t, T_POP - 0.2, T_POP)))
        dens = ramp(t, T_DENSER - 0.15, T_DENSER + 0.5)
        etr = ramp(t, T_SQW - 0.4, T_OVAL + 0.2) * (1 - ramp(t, T_GF + 0.2, T_GF + 0.7))
        disp = 0.012 + 0.05 * ramp(t, T_SQ, T_LAST)
        lift = ramp(t, T_LIFT - 0.1, T_LIFT + 0.3) * (1 - ramp(t, T_SQ - 0.2, T_SQ + 0.2))
        arrow = ramp(t, T_SET - 0.1, T_SET + 0.4) * (1 - ramp(t, T_SQ + 0.2, T_SQ + 0.8))
        return dict(hc=hc, sv=sv, a_top=a_top, a_bot=a_bot, app_c=app_c, gf=gf, dusk=dusk, g_vis=min(g_vis, 1.0), g_pop=g_pop,
                    rays=min(rays, 1.0), bands=min(bands, 1.0), dens=dens, etr=etr, disp=disp, lift=lift, arrow=arrow)

    # ----------------------------------------------------------------------------------------------- sky
    def sky(self, t, s, pulse):
        dusk, gf, sv = s["dusk"], s["gf"], s["sv"]
        sky = self.gold * (1 - dusk) + self.dusk * dusk
        # glow centre: the visible Sun, or the set point below the ridge
        cx = self.sx; cy = self.ypx(s["app_c"]) if s["a_top"] > 0 else self.yh + 40
        dx = self.hx - cx; dy = self.hy - cy; d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - self.R, 0)
        gl = (np.exp(-dd / 35) * 0.75 + np.exp(-dd / 200) * 0.28 + np.exp(-dd / 800) * 0.07) * (0.45 + 0.55 * sv) * pulse
        gw = green_wash(t)
        gcol = np.array([1.0, 0.30, 0.05], f32) * (1 - gw) + np.array([0.12, 1.0, 0.30], f32) * gw
        sky = sky + gl[..., None] * gcol * (1 + 0.6 * gf)
        # rainbow beams (crepuscular after sunset)
        phi = np.arctan2(dy, dx)
        rad = (1 - np.exp(-(dd + 4) / 30)) * (np.exp(-dd / 1000) * 0.9 + 0.12 * np.exp(-dd / 2400))
        acc = np.zeros(dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + 0.10 * math.sin(0.25 * t * b["sp"] + b["ph"])
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.3 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.65 + 0.35 * math.sin(t * 1.4 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.30 + 0.03 * t) % 1.0
            acc += (palette(x) * 0.80 + np.array([1.0, 0.55, 0.2], f32) * 0.20) * (g * I)[..., None]
        bI = (0.38 + 0.30 * sv + 0.22 * dusk) * pulse * (1 + 1.5 * gf)
        acc = acc * (1 - gf) + lum(acc)[..., None] * np.array([0.12, 1.0, 0.30], f32) * gf
        sky = sky + acc * rad[..., None] * bI
        # air layers
        if s["bands"] > 0.01: sky = sky + self.air_bands(t, s, self.hx, self.hy)
        return sky

    def air_bands(self, t, s, xs, ys, below=False):
        """rainbow-tinted refraction layers: denser (thinner spacing, brighter) towards the ground"""
        Nb = 9
        z = (self.yh - ys) / self.BH
        zc = np.clip(z, 0, 1) if not below else np.clip(-z, 0, 0.6)
        u = Nb * zc ** 0.6
        u = u + 0.22 * np.sin(xs / 170.0 + 0.8 * t + u * 1.3) + 0.10 * np.sin(xs / 61.0 - 1.3 * t)
        fr = u - np.floor(u); dl = np.minimum(fr, 1 - fr)
        line = np.exp(-(dl / 0.055) ** 2)
        hue = (np.floor(u) / Nb * 0.85 + 0.04 * t) % 1.0
        dn = s["dens"]
        wgt = (1 - np.clip(zc, 0, 1)) ** (1.0 + 1.5 * dn) * (0.5 + 1.6 * dn) if not below else np.ones_like(zc) * (0.5 + 1.2 * dn)
        top = smooth(1.0, 0.85, z) if not below else 1.0
        c = palette(hue)
        out = c * ((line * 0.9 + 0.14) * wgt * top)[..., None]
        if not below: out = out * smooth(-0.002, 0.01, z)[..., None]
        return out * 0.95 * s["bands"]

    # ----------------------------------------------------------------------------------------------- the refracted Sun
    def sun_disc(self, img, t, s, pulse):
        if s["a_top"] < -1.0: return
        K, R, sx = self.K, self.R, self.sx
        x0, x1 = int(sx - R * 1.4), int(sx + R * 1.4) + 1
        y0 = max(0, int(self.ypx(s["a_top"] + 6))); y1 = int(self.yh + 2)
        if y1 <= y0: return
        yy = self.yy[y0:y1, x0:x1] + 0.5; xx = self.xx[y0:y1, x0:x1] + 0.5
        a = (self.yh - yy) / K
        etr = s["etr"]
        P = 4.2
        st = etr * 0.92 * P / (2 * np.pi) * np.sin(2 * np.pi * a / P + 0.9 * t)       # stepped inversion layers
        xw = xx - sx + etr * 3.0 * np.sin(2 * np.pi * a / (2 * P) + 2.3 * t) + 0.8 * np.sin(a * 1.7 + 9 * t)
        hc = s["hc"]; disp = s["disp"]
        Ra = refr(a).astype(f32)
        col0 = np.array([1.0, 0.25, 0.03], f32)
        out = np.zeros(yy.shape + (3,), f32); cov = np.zeros(yy.shape, f32)
        for c, dk in ((0, -1.0), (1, 0.0), (2, 1.0)):
            h = a - Ra * (1 + disp * dk) + st
            q = np.sqrt((xw / R) ** 2 + ((h - hc) / SEMI) ** 2)
            inside = smooth(1 + 1.3 / R, 1 - 1.3 / R, q)
            mu = np.sqrt(np.clip(1 - q * q, 0, 1))
            redden = np.clip(0.80 + 0.20 * (h - hc + SEMI) / (2 * SEMI), 0.6, 1.0) ** (c * 1.5)
            cov = np.maximum(cov, inside)
            out[..., c] = inside * (1 - (0.45, 0.62, 0.80)[c] * (1 - mu)) * col0[c] * redden
        if s["gf"] > 0:                                        # the last sliver turns emerald
            g = s["gf"]; y = out.max(-1, keepdims=True)
            out = out * (1 - g) + y * np.array([0.04, 1.0, 0.20], f32) * g * 1.1
        # top-limb green rim from the dispersion (G lifted more than R)
        out[..., 1] += np.clip(out[..., 1] - out[..., 0], 0, None) * 1.5
        I = 4.2 * (0.6 + 0.4 * s["sv"]) * pulse
        clip = smooth(self.yh + 0.5, self.yh - 1.0, yy)[..., None]
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - 0.88 * cov[..., None] * clip) + out * I * clip

    def shimmer(self, img, t, amp):
        y0 = max(0, int(self.yh - 380)); y1 = int(self.yh + 4)
        H, W = img.shape[:2]
        xs = self.xx[y0:y1]; ys = self.yy[y0:y1]
        n = cv2.remap(self.shim, ((xs * 0.15) % 256).astype(f32), ((ys * 0.5 + t * 40) % 256).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = smooth(self.yh - 380, self.yh - 20, ys) * amp
        img[y0:y1] = cv2.remap(np.ascontiguousarray(img[y0:y1]), (xs + n * k).astype(f32), (ys - y0 + n * k * 0.25).astype(f32),
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return img

    # ----------------------------------------------------------------------------------------------- graphics
    def ghost_xy(self, s): return self.sx, self.ypx(s["hc"])

    def cutaway(self, img, t, s):
        """X-ray window through the mountains around the true Sun"""
        gv = s["g_vis"]
        if gv < 0.01: return img, None
        gx, gy = self.ghost_xy(s); R = self.R * s["g_pop"]
        rx, ry = 2.05 * R, 1.55 * R
        x0, x1 = max(0, int(gx - rx - 30)), min(self.L.W, int(gx + rx + 30)); y0, y1 = max(0, int(gy - ry - 30)), min(self.L.H, int(gy + ry + 30))
        xx = self.xx[y0:y1, x0:x1]; yy = self.yy[y0:y1, x0:x1]
        q = np.sqrt(((xx - gx) / rx) ** 2 + ((yy - gy) / ry) ** 2)
        open_ = ease(min(1.0, gv * 1.3))
        m = smooth(1.0, 0.96, q / max(open_, 0.02)) * self.a[y0:y1, x0:x1, 0] * gv
        reg = img[y0:y1, x0:x1]
        scan = 0.75 + 0.25 * np.sin(yy * 0.9 - t * 25) ** 2
        holo = np.array([0.006, 0.012, 0.045], f32) + self.edges[y0:y1, x0:x1, None] * np.array([0.10, 0.55, 1.0], f32) * 0.45 * scan[..., None]
        holo = holo + np.exp(-np.maximum(yy - self.yh, 0) / 140)[..., None] * np.array([0.9, 0.25, 0.06], f32) * 0.25
        holo = holo + self.air_bands(t, s, xx, yy, below=True) * 0.8
        # the true Sun itself: a dim orange orb behind the mountains
        d = np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2)
        mu = np.sqrt(np.clip(1 - (d / R) ** 2, 0, 1))
        orb = smooth(R + 1.5, R - 1.5, d) * (0.35 + 0.65 * mu)
        holo = holo + orb[..., None] * np.array([1.0, 0.30, 0.05], f32) * 1.5 * (0.8 + 0.2 * scan[..., None])
        holo = holo + np.exp(-np.maximum(d - R, 0) / 30)[..., None] * np.array([1.0, 0.35, 0.1], f32) * 0.35 * (d > R)[..., None]
        reg[:] = reg * (1 - m[..., None]) + holo * m[..., None]
        # rim of the window
        rim = np.exp(-((q - open_) / 0.012) ** 2) * self.a[y0:y1, x0:x1, 0] * gv
        reg += rim[..., None] * np.array([0.25, 0.85, 1.4], f32) * 1.0
        img[y0:y1, x0:x1] = reg
        return img, (gx, gy, R)

    def ghost_ring(self, fx, t, s, g):
        """dashed glowing ring + crosshair ticks at the true position (drawn on the half-res fx buffer, x4 subpixel)"""
        gx, gy, R = g; gv = s["g_vis"]
        S = 8
        cxi, cyi = int(gx / 2 * S), int(gy / 2 * S)
        n = 28
        for k in range(n):
            a0 = 2 * np.pi * k / n + 0.35 * t; a1 = a0 + 2 * np.pi / n * 0.55
            cv2.ellipse(fx, (cxi, cyi), (int(R / 2 * S), int(R / 2 * S)), 0, math.degrees(a0), math.degrees(a1),
                        (0.5 * gv * 2, 1.0 * gv * 2, 1.3 * gv * 2), 2, cv2.LINE_AA, 3)
        for k in range(4):
            a = k * np.pi / 2 + 0.25 * np.pi
            p0 = (int((gx + math.cos(a) * (R + 10)) / 2 * S), int((gy + math.sin(a) * (R + 10)) / 2 * S))
            p1 = (int((gx + math.cos(a) * (R + 34)) / 2 * S), int((gy + math.sin(a) * (R + 34)) / 2 * S))
            cv2.line(fx, p0, p1, (0.6 * gv * 3, 1.0 * gv * 3, 1.25 * gv * 3), 2, cv2.LINE_AA, 3)
        cv2.circle(fx, (cxi, cyi), int(3 * S / 2), (gv * 2, gv * 2, gv * 2), -1, cv2.LINE_AA, 3)

    def horizon_line(self, fx, t, amt):
        if amt < 0.01: return
        W = self.L.W; y = int(self.yh / 2 * 8)
        per = 26.0; off = (t * 30) % per
        x = -per + off
        while x < W:
            cv2.line(fx, (int(x / 2 * 8), y), (int((x + per * 0.55) / 2 * 8), y), (1.6 * amt, 1.4 * amt, 1.2 * amt), 1, cv2.LINE_AA, 3)
            x += per

    def lift_arrow(self, fx, s, amt):
        if amt < 0.01 or s["a_top"] <= 0: return
        S = 8; x = self.sx + self.R + 70
        ya = self.ypx(s["app_c"]); yg = self.ypx(s["hc"])
        col = (1.0 * amt * 2.2, 0.85 * amt * 2.2, 0.35 * amt * 2.2)
        p = lambda X, Y: (int(X / 2 * S), int(Y / 2 * S))
        cv2.line(fx, p(x, ya + 6), p(x, yg - 6), col, 2, cv2.LINE_AA, 3)
        for yv, sg in ((ya, 1), (yg, -1)):
            cv2.line(fx, p(x, yv), p(x - 12, yv + 16 * sg), col, 2, cv2.LINE_AA, 3); cv2.line(fx, p(x, yv), p(x + 12, yv + 16 * sg), col, 2, cv2.LINE_AA, 3)
        cv2.line(fx, p(x - 8, ya), p(self.sx + 8, ya), tuple(c * 0.5 for c in col), 1, cv2.LINE_AA, 3)
        cv2.line(fx, p(x - 8, yg), p(self.sx + self.R + 40, yg), tuple(c * 0.5 for c in col), 1, cv2.LINE_AA, 3)

    def rays(self, fx, t, s):
        """glowing curved ray paths from the true Sun, over the ridge, bending down into the camera"""
        amt = s["rays"]
        if amt < 0.01: return
        gx, gy = self.ghost_xy(s)
        A = np.array([self.sx, self.ypx(max(s["app_c"], 8.0))])
        S = 8; n = 9
        grow = ramp(amt, 0, 1)
        for i in range(n):
            f = (i - (n - 1) / 2) / ((n - 1) / 2)
            p0 = np.array([gx + f * self.R * 0.75, gy - math.sqrt(max(0.0, 1 - f * f)) * self.R * 0.5])
            cam = self.cam + np.array([f * 30, 0])
            hgt = (self.yh - gy) - (140 + 90 * (1 - abs(f))) * (1 if self.V else 0.62)
            p1 = p0 + np.array([f * self.R * 2.6, hgt * 1.35])
            p2 = np.array([cam[0] + f * self.R * 2.2, A[1] + self.R * 0.4])
            pts = bezier(p0, p1, p2, cam, 120)
            m = max(2, int(len(pts) * min(1.0, grow * 1.2)))
            col = palette((i / n * 0.9 + 0.05 * t) % 1.0).reshape(3) * 0.6 + 0.4
            I = 1.1 * amt
            cv2.polylines(fx, [np.round(pts[:m] / 2 * S).astype(np.int32)], False, tuple(float(c * I) for c in col), 2, cv2.LINE_AA, 3)
            for k in range(3):                                   # light pulses travelling ghost -> camera
                u = (t * 0.55 + i * 0.137 + k / 3) % 1.0
                j = int(u * (len(pts) - 1))
                if j < m:
                    cv2.circle(fx, tuple(np.round(pts[j] / 2 * S).astype(int)), int(5 * S / 2), tuple(float(c * I * 2.2) for c in col), -1, cv2.LINE_AA, 3)
        # line of sight: camera -> apparent Sun -> beyond (dashed, flowing outwards)
        cam = self.cam; dvec = A - cam; L = np.linalg.norm(dvec); dvec /= L
        per = 34.0; off = (t * 60) % per; d0 = L * 0.30 + off
        while d0 < L * 1.45:
            pa = cam + dvec * d0; pb = cam + dvec * (d0 + per * 0.5)
            cv2.line(fx, tuple(np.round(pa / 2 * S).astype(int)), tuple(np.round(pb / 2 * S).astype(int)), (1.3 * amt, 1.2 * amt, 1.0 * amt), 2, cv2.LINE_AA, 3)
            d0 += per

    def lift_ghost(self, img, t, s):
        """on 'lifting': translucent chromatic copies of the disc slide from the true position up to the image"""
        amt = s["lift"]
        if amt < 0.01: return
        yg = self.ypx(s["hc"]); ya = self.ypx(s["app_c"])
        for k in range(3):
            u = ((t - T_LIFT) * 0.9 + k / 3) % 1.0
            y = yg + (ya - yg) * ease(u)
            a = amt * math.sin(math.pi * u) * 0.9
            for c, off in ((0, 6), (1, 0), (2, -6)):
                cy = y + off
                x0, x1 = int(self.sx - self.R - 20), int(self.sx + self.R + 20); y0, y1 = max(0, int(cy - self.R - 20)), int(cy + self.R + 20)
                d = np.sqrt((self.xx[y0:y1, x0:x1] - self.sx) ** 2 + (self.yy[y0:y1, x0:x1] - cy) ** 2)
                ring = np.exp(-((d - self.R) / 3.0) ** 2) * 1.5 + smooth(self.R, self.R - 2, d) * 0.15
                img[y0:y1, x0:x1, c] += ring * a * (1.0, 0.8, 1.2)[c]

    def motes(self, t, amt):
        W, H = self.L.W, self.L.H; m = self.mote
        y = H * (1.02 - ((m["y0"] + m["sp"] * t) % 1.0) * 1.04)
        x = m["x"] + m["wob"] * np.sin(t * 0.7 + m["ph"]) + 25 * np.sin(y / 260 + m["ph"])
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        tw = 0.55 + 0.45 * np.sin(t * 3 + m["ph"] * 3)
        np.add.at(lay, (yi, xi), m["sz"] * tw * amt)
        return self.up(cv2.GaussianBlur(lay, (0, 0), 1.0) * 6 + cv2.GaussianBlur(lay, (0, 0), 4.0) * 5)[..., None] * np.array([1.0, 0.72, 0.30], f32)

    def day_dial(self, fx, t, amt):
        """bonus beat: two stopwatch rings sweeping round the set point (the extra minutes)"""
        if amt < 0.01: return
        S = 8; cx, cy = int(self.sx / 2 * S), int((self.yh - 20) / 2 * S)
        u = t - T_MIN
        for k, (Rr, col, sp) in enumerate(((self.R * 2.2, (1.0, 0.75, 0.25), 1.0), (self.R * 3.0, (1.0, 0.45, 0.7), 0.7))):
            sweep = 360 * min(1.0, max(0.0, u + 0.3) * 0.5 * sp) * amt
            c3 = tuple(float(v * 2.2 * amt) for v in col)
            cv2.ellipse(fx, (cx, cy), (int(Rr / 2 * S), int(Rr / 2 * S)), -90, 0, sweep, c3, 3, cv2.LINE_AA, 3)
            for j in range(12):
                a = math.radians(j * 30 - 90); r0, r1 = Rr - 10, Rr + 10
                cv2.line(fx, (int(cx + math.cos(a) * r0 / 2 * S), int(cy + math.sin(a) * r0 / 2 * S)),
                         (int(cx + math.cos(a) * r1 / 2 * S), int(cy + math.sin(a) * r1 / 2 * S)), tuple(c * 0.6 for c in c3), 1, cv2.LINE_AA, 3)
            a = math.radians(sweep - 90)
            cv2.circle(fx, (int(cx + math.cos(a) * Rr / 2 * S), int(cy + math.sin(a) * Rr / 2 * S)), int(6 * S / 2), tuple(c * 1.5 for c in c3), -1, cv2.LINE_AA, 3)

    def wavefronts(self, fx, t, amt):
        """myth beat: sunlight wavefronts (8 min 19 s in flight) rolling out of the set point"""
        if amt < 0.01: return
        S = 8; cx, cy = int(self.sx / 2 * S), int((self.yh + 30) / 2 * S)
        for k in range(10):
            tb = T_MYTH - 0.3 + k * 0.42; u = t - tb
            if not (0 <= u < 2.4): continue
            Rr = 60 + 1500 * (u / 2.4) ** 0.8; a = (1 - u / 2.4) ** 1.5 * 2.6 * amt
            col = (1.0, 0.75, 0.30) if k % 2 == 0 else (1.0, 0.35, 0.85)
            cv2.ellipse(fx, (cx, cy), (int(Rr / 2 * S), int(Rr / 2 * S * 0.8)), 0, 180, 360, tuple(float(c * a) for c in col), 3, cv2.LINE_AA, 3)

    # ----------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        s = self.state(t)
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.7)
        sky = self.sky(t, s, pulse)
        img = self.up(sky)
        self.sun_disc(img, t, s, pulse)
        img = self.shimmer(img, t, 1.2 + 2.5 * s["etr"])
        # foreground
        dusk, gf = s["dusk"], s["gf"]
        fgc = self.fg_gold * (1 - dusk) + self.fg_dusk * dusk
        fgc = fgc * (0.88 + 0.12 * s["sv"] + 0.04 * (pulse - 1))
        rimc = np.array([1.0, 0.55, 0.18], f32) * (0.25 + 0.95 * s["sv"]) * (1 - gf) + np.array([0.3, 1.0, 0.45], f32) * (gf + 2.0 * green_wash(t))
        fgc = fgc + self.rim[..., None] * rimc * (1 - 0.55 * dusk)
        fgc = fgc + self.fg.flat * np.array([0.2, 0.9, 0.35], f32) * 0.12 * green_wash(t)
        img = img * (1 - self.a) + fgc * self.a
        img, g = self.cutaway(img, t, s)
        # graphics
        fx = np.zeros((H // 2, W // 2, 3), f32)
        if g is not None: self.ghost_ring(fx, t, s, g)
        self.horizon_line(fx, t, max(s["g_vis"] * 0.8, 0.0))
        self.lift_arrow(fx, s, s["arrow"] * s["g_vis"])
        self.rays(fx, t, s)
        self.day_dial(fx, t, ramp(t, T_MIN - 0.3, T_MIN + 0.2) * (1 - ramp(t, T_MYTH - 0.2, T_MYTH + 0.3)))
        self.wavefronts(fx, t, ramp(t, T_MYTH - 0.2, T_MYTH + 0.3) * (1 - ramp(t, T_END - 0.3, T_END + 0.2)))
        img += self.up(fx + cv2.GaussianBlur(fx, (0, 0), 2.0) * 1.2 + cv2.GaussianBlur(fx, (0, 0), 8.0) * 0.8)
        self.lift_ghost(img, t, s)
        # green flash: emerald burst + anamorphic streak along the horizon
        if gf > 0.005:
            dx = self.hx - self.sx; dy = self.hy - (self.yh - 4)
            d = np.sqrt(dx * dx + dy * dy)
            gw = green_wash(t) / max(gf, 1e-3)
            burst = np.exp(-d / 30) * 0.12 + np.exp(-d / 150) * 0.45 + (np.exp(-d / 420) * 0.30 + np.exp(-d / 1100) * 0.10) * gw
            streak = np.exp(-(dy / 3.0) ** 2) * np.exp(-np.abs(dx) / 900) * 0.9 + np.exp(-(dy / 16.0) ** 2) * np.exp(-np.abs(dx) / 500) * 0.5 * gw
            ph = np.arctan2(dy, dx)
            for k in range(8):                                   # starburst spikes, slowly turning
                a = k * np.pi / 4 + 0.15 + 0.4 * (t - T_GF)
                dp = (ph - a + np.pi) % (2 * np.pi) - np.pi
                burst = burst + np.exp(-(dp * d / (3.0 + 0.004 * d)) ** 2) * np.exp(-d / (520 if k % 2 == 0 else 300)) * 1.1
            img += self.up((burst + streak)[..., None] * np.array([0.08, 1.0, 0.25], f32) * gf)
        img += self.motes(t, 0.7 + 0.3 * (1 - dusk)) * (1 - 0.6 * dusk)
        # flashes + chromatic shockwaves
        for te, col, strength in EVENTS:
            u = t - te
            if -0.03 < u < 1.4:
                col = np.array(col, f32)
                img += (0.08 if col[1] > 0.9 and col[0] < 0.2 else 0.35) * strength * math.exp(-max(u, 0) / 0.09) * ease((u + 0.03) / 0.03) * (0.12 + 0.88 * col)
                Rr = 2300 * (max(u, 0) / 1.4) ** 0.6; wdt = 14 + 50 * u
                dd = np.sqrt((self.hx - self.sx) ** 2 + (self.hy - self.yh) ** 2)
                ring = np.zeros(dd.shape + (3,), f32)
                dk = 0.25 if col[1] > 0.9 and col[0] < 0.2 else 0.5           # the green ring clears quickly
                for ch, off in ((0, 12), (1, 0), (2, -12)):
                    ring[..., ch] = np.exp(-((dd - Rr - off) / wdt) ** 2) * 1.5 * strength * math.exp(-max(u, 0) / dk) * (0.5 + 0.5 * col[ch])
                img += self.up(ring)
        wl = white_level(t)
        if wl > 0.001: img = img + (26 * wl ** 1.5) * np.array([1.0, 0.94, 0.86], f32)
        img = self.chroma_bloom(img)
        out = tonemap(img, 1.0)
        out = self.grade(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, s)
        return out

    def chroma_bloom(self, img):
        img = bloom(img, 0.9)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, sg in ((0, 24), (1, 18), (2, 13)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), sg)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.30

    def grade(self, out):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * 1.28
        return np.clip(out + np.array([0.010, 0.004, 0.022], f32) * (1 - out), 0, 1)

    # ----------------------------------------------------------------------------------------------- text
    def overlay(self, out, t, s):
        L = self.L; W = L.W
        # labels on the graphics
        gv = s["g_vis"] * (1 - ramp(t, T_SQ + 0.6, T_SQ + 1.2)) if t < T_END else s["g_vis"]
        if gv > 0.02:
            gx, gy = self.ghost_xy(s)
            off = self.R + (175 if self.V else 190)
            hud_text(out, "REAL POSITION", gx + off, gy - 6, 30 if self.V else 26, "Black", (140, 235, 255), gv, 0.10, display=True)
            if s["a_top"] > 0:
                hud_text(out, "WHAT YOU SEE", self.sx - off, self.ypx(s["app_c"]) - 6, 30 if self.V else 26, "Black", (255, 205, 110), gv, 0.10, display=True)
            hud_text(out, "HORIZON", (95 if self.V else 640), self.yh - 30, 22, "Bold", (255, 240, 220), gv * 0.9, 0.18, display=True)
        if s["arrow"] * s["g_vis"] > 0.02 and s["a_top"] > 0:
            yv = 0.5 * (self.ypx(s["app_c"]) + self.ypx(s["hc"]))
            hud_text(out, "0.57°", self.sx + self.R + 70 + (62 if self.V else 58), yv - 8, 30 if self.V else 26, "Black", (255, 220, 120), s["arrow"] * s["g_vis"], 0.04, display=True)
        # readouts
        x, ys = (W / 2, (330, 425, 480)) if self.V else (760, (330, 410, 460))
        for key, (ta, tb, lines) in self.ro.items():
            a = ramp(t, ta, ta + 0.25) * (1 - ramp(t, tb - 0.2, tb))
            if a < 0.01: continue
            dy = (1 - a) * 20
            pop = 1 + 0.10 * math.exp(-max(0, t - ta) / 0.08)
            big, col = lines[0]
            rgba, _ = word_layer(big, (96 if self.V else 84), (W * 0.9 if self.V else 900), fill=col, scale=pop)
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, lines[1][0], x, ys[1] + dy, 38 if self.V else 33, "Black", (255, 255, 255), a, 0.05, display=True)
            hud_text(out, lines[2][0], x, ys[2] + dy, 27 if self.V else 25, "Bold", (235, 240, 250), a, 0.06, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            save(im, os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=16)
    t0 = time.time()
    for i in range(NFR):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{NFR}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(vertical, ranges):
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=16)
    for i in range(NFR):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "frames", NFR)
        print(f"R(0) = {R_HOR:.2f}'  HC_TOUCH {HC_TOUCH:.2f}'  HC_GONE {HC_GONE:.2f}'  HC_START {HC_START:.2f}'")
        print(f"at touch: apparent top {A_TOP_TOUCH:.2f}'  R(top) {R_TOP_TOUCH:.2f}'  squash {SQUASH:.3f}  true top {HC_TOUCH + SEMI:.2f}'")
        for k in ("T_TOUCH", "T_REVEAL", "T_SET", "T_HOW", "T_BENDS", "T_DENSER", "T_LIFT", "T_SQ", "T_OVAL", "T_LAST", "T_GF", "T_BONUS", "T_MIN", "T_MYTH", "T_END", "T_MIRAGE", "T_POP"):
            print(k, round(globals()[k], 2))
        sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
