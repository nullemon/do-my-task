"""WHAT ECLIPSES LOOK LIKE ON OTHER WORLDS -- one locked tripod shot of the tropical beach (05_tropical_beach), daytime.
The Sun is eclipsed by a different body on each world, every disc at its TRUE angular size as seen from that world,
through one fixed telephoto lens (f = 2700 px, ~39 deg vertical field of view). The beach stays the stage; its light,
shadows and the reflecting shallows change with each sky.
  Earth (the Moon slides in -> totality, corona) -> Mars (Phobos transit, a bite) -> the Moon (Earth's red ring)
  -> Io (Jupiter swallows the Sun) -> behind Saturn (Cassini 2013, backlit rings, Earth a dot) -> white-out -> sunny beach
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py segs                    restart-safe segment render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5            stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1, srgb_to_lin, bbcolor
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-eclipses-other-worlds"
BG = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/05_tropical_beach.png"
SSS = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/sss"
THX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/threex.planets/images"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 2700.0                       # one lens for every world: true angular sizes
F_SKY = 1400.0                      # stylised sky dome (gradient / star field)
C = (330.0, 540.0)                  # where our Sun sits (clear sky, left of the palm crown)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_deg(deg): return F_PX * math.tan(math.radians(deg / 2))           # apparent radius (px) of a disc `deg` wide
def rad_sph(R, d): return F_PX * math.tan(math.asin(R / d))                # sphere of radius R seen from distance d


# ------------------------------------------------------------------------------------------------ true sizes
R_SUN_E = rad_deg(0.533)                 # the Sun from Earth (1 au)
R_MOON = rad_deg(0.550)                  # the Moon near perigee (0.49-0.56 deg) -> just covers the Sun
R_SUN_M = rad_deg(0.533 / 1.524)         # the Sun from Mars: 0.35 deg
PHO_A, PHO_B = rad_deg(0.258), rad_deg(0.210)   # Phobos 27 x 22 km seen from ~6,000 km
R_EARTH_L = rad_sph(6371.0, 384400.0 - 1737.4)  # Earth from the Moon's near side: 1.9 deg
R_JUP = rad_sph(71492.0, 421700.0 - 1821.6)     # Jupiter from Io's sub-Jovian point: 19.6 deg (equatorial)
Q_JUP = 66854.0 / 71492.0
R_SUN_J = rad_deg(0.533 / 5.204)         # 0.10 deg
D_CAS = 1.2e6                            # Cassini - Saturn, 19 July 2013 (km)
K_SAT = F_PX / D_CAS                     # px per km at Saturn
R_SAT = rad_sph(60268.0, D_CAS); Q_SAT = 54364.0 / 60268.0
SAT_ROLL = math.radians(-14.0); SAT_TILT = math.radians(17.0)          # ring plane roll on screen, opening angle
J_DIR = np.array([0.5523, 0.8337])       # Jupiter's centre lies down-right of the Sun's position (the Sun sits on its limb)
J_C = (C[0] + J_DIR[0] * R_JUP, C[1] + J_DIR[1] * R_JUP)
EARTH_DOT = (C[0] - 190.0, C[1] + 168.0)

# ------------------------------------------------------------------------------------------------ timeline
T_SW = {"mars": LN["mars"]["start"] - 0.06, "moon": LN["moon"]["start"] - 0.06, "io": LN["io"]["start"] - 0.06,
        "sat": LN["sat"]["start"] - 0.06}
T_BACK = LN["end_b"]["start"] - 0.10                 # white-out peak -> the sunny beach is back
T_WO0 = T_BACK - 0.75
SWAPS = [(T_SW[k], k) for k in ("mars", "moon", "io", "sat")] + [(T_BACK, "day")]
COLLAPSE, BLOOM = 0.42, 0.65
# Earth: the Moon slides in (ease-out) and reaches second contact at "PERFECT"
T_M0 = wt("earth", "MOON") - 0.35
T_C2 = wt("earth_b", "PERFECT") + 0.05
_UC = 1 - (max(R_MOON - R_SUN_E, 0.05) / (1.15 * (R_SUN_E + R_MOON))) ** (1 / 3)
T_M1 = T_M0 + (T_C2 - T_M0) / _UC
# Mars: Phobos crosses the disc, mid-transit on "BITE"
T_P0 = T_SW["mars"] + 0.55; T_PM = wt("mars_c", "BITE") + 0.05; T_P1 = 2 * T_PM - T_P0
# the Moon: Earth's ring brightens on "RED"
T_RED = wt("moon_c", "RED")
# Io: the Sun slides behind Jupiter's limb on "SWALLOWS"
T_J0 = T_SW["io"] + 0.35; T_SWALLOW = wt("io_b", "SWALLOWS") + 0.25
# Saturn
T_LIGHT = wt("sat_b", "LIGHT"); T_DOT = wt("sat_c", "TINY") - 0.1
PULSES = [wt("hook_b", "DARK"), wt("earth_b", "FIT"), wt("mars", "PHOBOS"), wt("mars_c", "BITE"), T_RED, wt("moon_d", "SUNRISE"),
          wt("moon_d", "SUNSET"), wt("io_b", "WHOLE"), T_LIGHT, wt("sat_d", "US"), wt("end_b", "BEACH")]


def scene_at(t):
    cur, t0 = "earth", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w):
    if isinstance(a, (tuple, list)): return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


def pal_list(cols, x):
    Cc = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return Cc[i] * (1 - fr) + Cc[i + 1] * fr


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def circ_overlap(r1, r2, d):
    """area of the intersection of two discs"""
    if d >= r1 + r2: return 0.0
    if d <= abs(r1 - r2): return math.pi * min(r1, r2) ** 2
    a = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1)) + r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    return a - 0.5 * math.sqrt(max((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2), 0))


def moon_off(t):
    """Moon centre offset (px, +x = right) from the Sun's centre: slides in from the right, eases into totality"""
    u = min(max((t - T_M0) / (T_M1 - T_M0), 0.0), 1.0)
    return 1.15 * (R_SUN_E + R_MOON) * (1 - u) ** 3


def earth_vis(t):
    o = moon_off(t)
    return 1 - circ_overlap(R_SUN_E, R_MOON, o) / (math.pi * R_SUN_E ** 2)


# ------------------------------------------------------------------------------------------------ looks
# sky zen/hor (linear, display-referred), sun aureole, beams, foreground light (key gain, tint, flat, ambient colour),
# star visibility, readout
DAY = dict(zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), glow=1.0, gcol=(1.0, 0.93, 0.80), beams="rainbow", bI=0.85,
           gain=1.0, tint=(1.0, 0.98, 0.95), flat=0.0, amb=(0.03, 0.05, 0.09), rim=0.0, rcol=(1, 1, 1), stars=0.0, hglow=0.0)
TOT = dict(zen=(0.004, 0.010, 0.042), hor=(0.045, 0.030, 0.040), glow=0.0, gcol=(0.8, 0.85, 1.0),
           beams=[(0.85, 0.90, 1.0), (0.55, 0.65, 1.0), (0.80, 0.60, 1.0), (1.0, 0.95, 0.9)], bI=0.45,
           gain=0.0, tint=(1, 1, 1), flat=0.75, amb=(0.050, 0.060, 0.120), rim=0.35, rcol=(0.85, 0.88, 1.0), stars=0.30, hglow=1.0)
MARS = dict(zen=(0.20, 0.115, 0.060), hor=(0.50, 0.33, 0.19), glow=0.9, gcol=(0.45, 0.62, 1.0),
            beams=[(1.0, 0.70, 0.40), (0.45, 0.65, 1.0), (1.0, 0.50, 0.28), (0.9, 0.85, 0.7)], bI=0.55,
            gain=0.55, tint=(1.0, 0.82, 0.62), flat=0.2, amb=(0.10, 0.065, 0.040), rim=0.0, rcol=(1, 0.8, 0.6), stars=0.0, hglow=0.0)
MOON = dict(zen=(0.0035, 0.0045, 0.016), hor=(0.008, 0.008, 0.022), glow=0.0, gcol=(1.0, 0.3, 0.12),
            beams=[(1.0, 0.25, 0.10), (1.0, 0.45, 0.15), (0.9, 0.15, 0.35), (1.0, 0.65, 0.35)], bI=0.55,
            gain=0.10, tint=(1.0, 0.26, 0.10), flat=0.75, amb=(0.020, 0.018, 0.040), rim=0.9, rcol=(1.0, 0.35, 0.15), stars=1.0, hglow=0.0)
IO_PRE = dict(zen=(0.0030, 0.0045, 0.017), hor=(0.007, 0.008, 0.022), glow=0.55, gcol=(1.0, 0.95, 0.85),
              beams=[(1.0, 0.80, 0.35), (1.0, 0.95, 0.70), (0.45, 0.80, 1.0), (1.0, 0.55, 0.20)], bI=0.6,
              gain=0.42, tint=(1.0, 0.97, 0.92), flat=0.0, amb=(0.010, 0.012, 0.025), rim=0.0, rcol=(1, 0.9, 0.7), stars=0.7, hglow=0.0)
IO = dict(IO_PRE, glow=0.0, gcol=(1.0, 0.75, 0.40), gain=0.075, tint=(1.0, 0.62, 0.28), flat=0.75,
          amb=(0.016, 0.016, 0.034), rim=0.9, rcol=(1.0, 0.72, 0.38), stars=1.0)
SAT = dict(zen=(0.0030, 0.0045, 0.017), hor=(0.007, 0.009, 0.024), glow=0.0, gcol=(0.75, 0.85, 1.0),
           beams=[(1.0, 0.82, 0.50), (0.45, 0.85, 1.0), (0.75, 0.55, 1.0), (1.0, 0.95, 0.80)], bI=0.6,
           gain=0.07, tint=(0.80, 0.88, 1.10), flat=0.75, amb=(0.016, 0.018, 0.038), rim=0.9, rcol=(0.80, 0.88, 1.0), stars=1.0, hglow=0.0)
NUM = ("zen", "hor", "glow", "gcol", "bI", "gain", "tint", "flat", "amb", "rim", "rcol", "stars", "hglow")


def mixd(A, B, w):
    out = {k: lerp(A[k], B[k], w) for k in NUM}
    out["beamsA"], out["beamsB"], out["bw"] = A["beams"], B["beams"], w
    return out


RO = {
    "earth": ("FROM EARTH", "MOON 0.55° · SUN 0.53°", "TOTALITY: UP TO 7½ MINUTES", (255, 236, 190)),
    "mars": ("FROM MARS", "PHOBOS ~0.2° · SUN 0.35°", "TRANSIT: UNDER A MINUTE", (255, 180, 120)),
    "moon": ("FROM THE MOON", "EARTH 1.9° · SUN 0.53°", "TOTALITY CAN LAST HOURS", (255, 120, 90)),
    "io": ("FROM IO", "JUPITER 19.6° · SUN 0.10°", "AN ECLIPSE EVERY 42 HOURS", (255, 205, 120)),
    "sat": ("BEHIND SATURN", "CASSINI · 19 JULY 2013", "EARTH: 1.44 BILLION KM AWAY", (170, 215, 255)),
}

# water of the shallows: polygon in SOURCE px (horizon -> shoreline), feathered
WATER_POLY = [(0, 1158), (30, 1160), (200, 1172), (420, 1180), (520, 1198), (600, 1225), (650, 1260), (675, 1295), (665, 1325),
              (610, 1355), (500, 1388), (400, 1418), (300, 1443), (200, 1468), (100, 1492), (0, 1512)]


def load_lin(path, size=None):
    a = np.asarray(Image.open(path).convert("RGB"), f32) / 255.0
    if size: a = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
    return srgb_to_lin(a)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(BG, L, hz_frac=0.70)
        self.hz = float(fg.horizon)
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.dx = xx - C[0]; self.dy = yy - C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.el = el
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        self.cam = SkyCam(W, H, self.hz, F_SKY)
        self.stars = StarSky()
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.15, 0.26), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # ---- foreground: rim light, water mask + reflection geometry
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        s = fg.s
        poly = np.array([[x * s, y * s + fg.oy] for x, y in WATER_POLY], np.float32)
        wm = np.zeros((H, W), np.uint8); cv2.fillPoly(wm, [np.round(poly * 4).astype(np.int32)], 255, shift=2)
        wm = cv2.GaussianBlur(wm.astype(f32) / 255, (0, 0), 3.0)
        self.water = (wm * (self.yy > self.hz - 2)).astype(f32)
        ys = np.where(self.water.max(1) > 0.01)[0]; xs = np.where(self.water.max(0) > 0.01)[0]
        self.wy0, self.wy1, self.wx1 = int(ys.min()), int(ys.max()) + 1, int(xs.max()) + 1
        wy = self.yy[self.wy0:self.wy1, :self.wx1]
        depth = np.clip((wy - self.hz) / (self.wy1 - self.hz), 0, 1)
        self.fres = (0.55 - 0.40 * depth ** 0.7).astype(f32)                       # grazing (far) water reflects more
        self.wnoise = fbm2((256, 512), 77, 2.4)
        # ---- bodies
        self.prep_corona()
        self.prep_earth()
        self.prep_jupiter()
        self.prep_saturn()
        emph = {"IMAGINE", "DARK", "EARTH", "MOON", "PERFECT", "FIT", "MARS", "PHOBOS", "BITE", "RED", "SUNRISE", "SUNSET", "ONCE",
                "IO", "JUPITER", "WHOLE", "SATURN", "RINGS", "LIGHT", "DOT", "US", "BEACH", "SMALL"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- prep
    def prep_corona(self):
        r = np.random.default_rng(31)
        th = np.linspace(-np.pi, np.pi, 2048, endpoint=False)
        prof = 0.30 + 0.0 * th
        for c, w, a in ((0.15, 0.30, 1.0), (np.pi + 0.10, 0.28, 0.9), (0.75, 0.16, 0.45), (-2.6, 0.20, 0.5), (2.2, 0.12, 0.35), (-0.55, 0.12, 0.4)):
            dd = (th - c + np.pi) % (2 * np.pi) - np.pi; prof = prof + a * np.exp(-(dd / w) ** 2)    # equatorial streamers
        for c in (-np.pi / 2 - 0.15, np.pi / 2 - 0.15):                                             # polar plumes (fine)
            dd = (th - c + np.pi) % (2 * np.pi) - np.pi; prof = prof + 0.25 * np.exp(-(dd / 0.45) ** 2) * (0.6 + 0.4 * np.cos(dd * 40))
        fine = np.convolve(r.standard_normal(2048 * 3), np.ones(5) / 5, "same")[2048:4096]
        self.cor_prof = (prof * (1 + 0.25 * fine)).astype(f32)
        self.cor_fine = np.convolve(r.standard_normal(2048 * 3), np.ones(3) / 3, "same")[2048:4096].astype(f32)
        self.prom = [(r.uniform(-np.pi, np.pi), r.uniform(0.04, 0.09), r.uniform(0.05, 0.12)) for _ in range(5)]

    def prep_earth(self):
        """Earth's night side seen from the Moon: dark disc, city lights on the land (orthographic, 2x SS)"""
        R = R_EARTH_L; n = int(R * 2 + 6) * 2
        g = (np.arange(n, dtype=f32) + 0.5) / n * (2 * R + 6) - (R + 3)
        X, Y = np.meshgrid(g, g); rr = np.sqrt(X * X + Y * Y) / R
        inside = rr < 1
        z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
        tilt = math.radians(20)
        px, py, pz = X / R, Y / R, z
        y2 = py * math.cos(tilt) - pz * math.sin(tilt); z2 = py * math.sin(tilt) + pz * math.cos(tilt)
        lat = np.arcsin(np.clip(-y2, -1, 1)); lon = np.arctan2(px, z2) + math.radians(-30)        # night side over Africa/Europe
        spec = np.asarray(Image.open(os.path.join(THX, "earthspec1k.jpg")).convert("L"), f32) / 255
        hh, ww = spec.shape
        u = ((lon / (2 * np.pi) + 0.5) % 1.0) * (ww - 1); v = (0.5 - lat / np.pi) * (hh - 1)
        land = 1 - cv2.remap(spec, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR)
        r2 = np.random.default_rng(8)
        dots = (r2.uniform(0, 1, X.shape) < 0.035).astype(f32) * r2.uniform(0.2, 1, X.shape) ** 2
        cities = cv2.GaussianBlur(dots * np.clip(land * 1.4 - 0.2, 0, 1) * (np.abs(lat) < 1.1), (0, 0), 0.6) * z ** 0.5
        tex = (cities[..., None] * np.array([1.0, 0.72, 0.38], f32) * 0.06 + np.array([0.0012, 0.0016, 0.0035], f32) * z[..., None])
        tex = cv2.resize(tex * inside[..., None], (n // 2, n // 2), interpolation=cv2.INTER_AREA)
        m = cv2.resize(smooth(1.0, 0.985, rr).astype(f32), (n // 2, n // 2), interpolation=cv2.INTER_AREA)
        self.earth_tex, self.earth_m = tex.astype(f32), m.astype(f32)

    def prep_jupiter(self):
        """Jupiter's night side from Io: dark, faint bands (moon-lit), oblate; static full-frame layers"""
        W, H = self.L.W, self.L.H
        roll = math.radians(18.0); cr, sr = math.cos(roll), math.sin(roll)
        dx = self.xx + 0.5 - J_C[0]; dy = self.yy + 0.5 - J_C[1]
        u = (dx * cr + dy * sr) / R_JUP; v = (-dx * sr + dy * cr) / (R_JUP * Q_JUP)
        rr = np.sqrt(u * u + v * v)
        self.j_rr = rr.astype(f32)
        self.j_m = smooth(1.0 + 1.2 / R_JUP, 1.0 - 1.2 / R_JUP, rr).astype(f32)
        z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
        lat = np.arcsin(np.clip(v, -1, 1)); lon = np.arcsin(np.clip(u / np.maximum(np.cos(lat), 1e-3), -1, 1)) * 0.5
        tex = load_lin(os.path.join(SSS, "8k_jupiter.jpg"), (2048, 1024))
        tu = ((lon / (2 * np.pi) + 0.35) % 1.0) * 2047; tv = (0.5 - lat / np.pi) * 1023
        jt = cv2.remap(tex, tu.astype(f32), tv.astype(f32), cv2.INTER_LINEAR)
        self.j_tex = (jt * (0.25 + 0.75 * z[..., None]) * self.j_m[..., None]).astype(f32)
        self.j_ang = np.arctan2(dy, dx).astype(f32)
        self.j_v = v.astype(f32); self.j_u = u.astype(f32)
        self.j_bbox = (max(0, int(J_C[0] - R_JUP - 60)), min(W, int(J_C[0] + R_JUP + 60)), max(0, int(J_C[1] - R_JUP - 60)), min(H, int(J_C[1] + R_JUP + 60)))
        r = np.random.default_rng(12)
        self.lightning = [(r.uniform(-0.75, 0.75), r.uniform(-0.65, 0.55), r.uniform(0, 30), r.uniform(0.7, 1.6)) for _ in range(9)]

    def prep_saturn(self):
        """Cassini's 2013 view: Saturn backlit, the Sun hidden behind it. Rings from the real radial profile; brightness
        in forward-scattered light ~ tau exp(-tau) (dense B ring dark, thin C / Cassini division / A / F / G / E bright)"""
        W, H = self.L.W, self.L.H
        cr, sr = math.cos(SAT_ROLL), math.sin(SAT_ROLL)
        x0, x1, y0, y1 = 0, W, 0, int(min(H, C[1] + 520))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - C[0]; dy = self.yy[y0:y1, x0:x1] + 0.5 - C[1]
        u = dx * cr + dy * sr; v = -dx * sr + dy * cr                       # u along the ring major axis
        rp = np.sqrt((u / R_SAT) ** 2 + (v / (R_SAT * Q_SAT)) ** 2)
        self.s_box = (x0, x1, y0, y1)
        self.s_m = smooth(1.0 + 1.0 / R_SAT, 1.0 - 1.0 / R_SAT, rp).astype(f32)
        self.s_rp = rp.astype(f32)
        z = np.sqrt(np.clip(1 - rp * rp, 0, 1))
        lat = np.arcsin(np.clip(v / (R_SAT * Q_SAT), -1, 1))
        tex = load_lin(os.path.join(SSS, "8k_saturn.jpg"), (1024, 512))
        tv = (0.5 - lat / np.pi) * 511; tu = ((np.arcsin(np.clip(u / R_SAT / np.maximum(np.cos(lat), 1e-3), -1, 1)) / (2 * np.pi) + 0.5) % 1) * 1023
        st = cv2.remap(tex, tu.astype(f32), tv.astype(f32), cv2.INTER_LINEAR)
        # ringshine: the night side lit from below (the rings' lit side faces the southern hemisphere here)
        rs = np.clip(0.35 + 0.65 * (v / (R_SAT * Q_SAT)), 0, 1) ** 1.5
        self.s_tex = (st * (0.3 + 0.7 * z[..., None]) * rs[..., None] * self.s_m[..., None]).astype(f32)
        # ring plane: screen (u, v) -> ring radius (km); near half (v > 0) passes in front of the globe
        rr_px = np.sqrt(u * u + (v / math.sin(SAT_TILT)) ** 2)
        rkm = rr_px / K_SAT
        prof = np.asarray(Image.open(os.path.join(SSS, "8k_saturn_ring_alpha.png")).convert("RGBA"), f32).mean(0) / 255.0
        RING_KM0, RING_KMPX = 74658.0 - 434 * 8.537, 8.537
        idx = (rkm - RING_KM0) / RING_KMPX
        al = np.interp(idx, np.arange(len(prof)), prof[:, 3], left=0, right=0)
        col = np.interp(idx, np.arange(len(prof)), prof[:, 0], left=0, right=0)
        tau = -np.log(np.clip(1 - al * 0.98, 0.02, 1)) / math.sin(SAT_TILT) * 0.35
        fwd = tau * np.exp(-tau * 1.15)                                     # forward-scattered brightness
        main = fwd * (0.6 + 0.4 * col / max(col.max(), 1e-3))
        Fr = np.exp(-((rkm - 140220) / 600) ** 2) * 1.6                   # F ring (dusty, narrow)
        Gr = np.exp(-((rkm - 168000) / 3500) ** 2) * 0.55                  # G ring
        Er = np.exp(-((rkm - 238000) / 55000) ** 2) * 0.22 + np.exp(-((rkm - 330000) / 120000) ** 2) * 0.06   # E ring
        self.r_main = main.astype(f32); self.r_dust = (Fr + Gr).astype(f32); self.r_E = Er.astype(f32)
        self.r_opac = np.clip(al * 0.95, 0, 0.95).astype(f32)
        self.r_front = (v > 0).astype(f32)
        self.r_shadow = (1 - self.s_m * self.r_front).astype(f32)          # near rings over the globe sit in its shadow
        self.s_ang = np.arctan2(v, u).astype(f32)

    # -------------------------------------------------------------------------------------------- params
    def look(self, key, t):
        if key == "earth":
            k = 1 - earth_vis(t) ** 0.35
            k = max(k, ramp(t, T_C2 - 0.15, T_C2 + 0.25))
            return mixd(DAY, TOT, k)
        if key == "io": return mixd(IO_PRE, IO, self.io_hidden(t))
        return mixd(*({"mars": (MARS, MARS), "moon": (MOON, MOON), "sat": (SAT, SAT), "day": (DAY, DAY)}[key]), 1.0)

    def io_hidden(self, t):
        return ramp(t, T_SWALLOW - 0.35, T_SWALLOW + 0.15)

    def mix_params(self, t):
        cur, t0, t1 = scene_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "earth" if i == 0 else SWAPS[i - 1][1]
        B = self.look(cur, t)
        if prev is None: return B, cur, t0, t1
        w = ramp(t, t0 - 0.12, t0 + 0.55)
        if w >= 1: return B, cur, t0, t1
        A = self.look(prev, t0 - 0.13)
        out = {k: lerp(A[k], B[k], w) for k in NUM}
        out["beamsA"], out["beamsB"], out["bw"] = A["beamsB"], B["beamsB"], w
        return out, cur, t0, t1

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, P, col_u, vis):
        zen = np.array(P["zen"], f32); hor = np.array(P["hor"], f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        if P["hglow"] > 0:                                                # totality: sunset glow all round the horizon
            band = np.exp(-self.el / 0.07)[..., None]
            sky = sky + band * np.array([0.11, 0.050, 0.018], f32) * P["hglow"]
        gl = P["glow"] * vis
        if gl > 0.001:
            gc = np.array(P["gcol"], f32)
            aure = np.exp(-self.d / 40) * 0.9 + np.exp(-self.d / 200) * 0.14 + np.exp(-self.d / 700) * 0.05
            sky = sky + (aure * gl)[..., None] * gc
        sky = sky + self.beams_layer(t, P, col_u)
        return sky

    def beams_layer(self, t, P, col_u):
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = self.phi + twist * np.log(self.d / 30.0)
        reach = 1300 * (1 - 0.7 * ease(col_u))
        dd = self.d
        rad = (1 - np.exp(-(dd + 6) / 40)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(dd / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(self.dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.3) % 1.0
            def colof(bs): return palette(x) if bs == "rainbow" else pal_list(bs, x)
            w = P["bw"]
            c = colof(P["beamsB"]) if w >= 1 else colof(P["beamsA"]) * (1 - w) + colof(P["beamsB"]) * w
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.30 * P["bI"]

    # -------------------------------------------------------------------------------------------- bodies
    def sun(self, img, x, y, r, I, col=(1.0, 0.95, 0.86), occ=None, pad=40, glare=1.0):
        """limb-darkened HDR disc; occ(dx, dy) -> coverage 0..1 (dx, dy relative to the Sun centre). Returns the visible fraction"""
        H, W = img.shape[:2]
        R = r + pad
        x0, x1, y0, y1 = max(0, int(x - R)), min(W, int(x + R) + 1), max(0, int(y - R)), min(H, int(y + R) + 1)
        if x1 <= x0 or y1 <= y0: return 0.0
        dx = self.xx[y0:y1, x0:x1] + 0.5 - x; dy = self.yy[y0:y1, x0:x1] + 0.5 - y
        d = np.sqrt(dx * dx + dy * dy)
        mu = np.sqrt(np.clip(1 - (d / max(r, 0.6)) ** 2, 0, 1))
        disc = smooth(r + 0.7, r - 0.7, d) if r > 1.2 else np.exp(-(d / 0.9) ** 2) * min(r / 0.9, 1.0) ** 2
        ld = 0.35 + 0.65 * mu ** 0.8
        v = disc * ld
        cov = occ(dx, dy) if occ is not None else 0.0
        vis_px = v * (1 - cov)
        frac = float(vis_px.sum() / max(v.sum(), 1e-6))
        c = np.array(col, f32)
        img[y0:y1, x0:x1] += (vis_px * 60.0 * I)[..., None] * c
        if glare > 0 and frac > 1e-4:
            g = (np.exp(-d / (r * 1.3 + 1.5)) * 3.5 + np.exp(-d / (r * 4 + 6)) * 0.5) * (1 - 0.95 * cov) * frac ** 0.6 * glare * I
            img[y0:y1, x0:x1] += g[..., None] * c
        return frac

    def corona(self, img, x, y, R, amt, t):
        if amt <= 0: return
        n = len(self.cor_prof)
        def fn(d, dx, dy):
            ang = np.arctan2(dy, dx)
            i = ((ang / (2 * np.pi) + 0.5) * n).astype(np.int32) % n
            q = np.maximum(d / R, 1.0)
            prof = self.cor_prof[i]
            k = (q ** -2.6) * (0.55 + 0.9 * prof) * (1 + 0.20 * self.cor_fine[(i * 3) % n])
            k = k * np.exp(-(q - 1) / (2.2 + 4.0 * prof))
            inner = q ** -7 * 1.6
            v = (k * 2.4 + inner) * smooth(R - 0.6, R + 0.8, d) * (1 + 0.06 * math.sin(t * 2.0))
            col = np.array([1.0, 0.97, 0.94], f32)[None, None] * np.ones_like(v)[..., None]
            out = v[..., None] * col
            for (pa, pw, ph) in self.prom:                                   # pink prominences on the limb
                dd = (ang - pa + np.pi) % (2 * np.pi) - np.pi
                pr = np.exp(-(dd / pw) ** 2) * np.exp(-np.maximum(d - R, 0) / (R * ph)) * smooth(R - 0.4, R + 0.4, d)
                out += pr[..., None] * np.array([1.0, 0.16, 0.30], f32) * 2.5
            return out * amt
        splat(img, x, y, R * 9, fn)

    def phobos(self, img, x, y, sc, t):
        """occluder function for the Sun + (outside the disc) an almost invisible dark potato"""
        rot = 0.6 + 0.08 * t
        cr, sr = math.cos(rot), math.sin(rot)
        a, b = PHO_A * sc, PHO_B * sc
        def occ_at(px, py):                                                  # px, py relative to the Phobos centre
            u = px * cr + py * sr; v = -px * sr + py * cr
            th = np.arctan2(v / b, u / a)
            rr = np.sqrt((u / a) ** 2 + (v / b) ** 2)
            edge = 1 + 0.07 * np.sin(3 * th + 0.5) + 0.05 * np.sin(5 * th + 1.7) - 0.10 * np.exp(-((th - 2.4) / 0.35) ** 2)   # Stickney dent
            return smooth(1.0 + 0.6 / a, 1.0 - 0.6 / a, rr / edge)
        return occ_at

    def earth_ring(self, img, x, y, R, I, t, sdir):
        """Earth from the Moon, Sun just behind: night disc (city lights) + refracted sunlight in a thin red ring,
        a turquoise ozone fringe, and a soft glow"""
        tex, m = self.earth_tex, self.earth_m
        if abs(R - R_EARTH_L) > 0.5:
            n = max(int(round(tex.shape[0] * R / R_EARTH_L)), 4)
            tex = cv2.resize(tex, (n, n), interpolation=cv2.INTER_AREA); m = cv2.resize(m, (n, n), interpolation=cv2.INTER_AREA)
        h = tex.shape[0]; X0, Y0 = int(round(x - h / 2)), int(round(y - h / 2))
        H, W = img.shape[:2]
        xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X0 + h), min(H, Y0 + h)
        if xb > xa and yb > ya:
            mm = m[ya - Y0:yb - Y0, xa - X0:xb - X0][..., None]
            img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - mm) + tex[ya - Y0:yb - Y0, xa - X0:xb - X0] * min(I, 2.0)
        def fn(d, dx, dy):
            ang = np.arctan2(dy, dx)
            dd = (ang - sdir + np.pi) % (2 * np.pi) - np.pi
            k = 0.40 + 0.60 * np.exp(-(dd / 1.3) ** 2) + 0.08 * np.sin(ang * 7 + t * 0.8)
            o = d - R
            core = np.exp(-((o - 0.5) / 0.75) ** 2) * 9.0
            red = core[..., None] * np.array([1.0, 0.22, 0.06], f32) + (np.exp(-((o - 0.2) / 0.5) ** 2) * 3.0)[..., None] * np.array([1.0, 0.05, 0.02], f32)
            blue = (np.exp(-((o - 2.0) / 0.7) ** 2) * 1.2)[..., None] * np.array([0.25, 0.75, 1.0], f32)
            halo = (np.exp(-np.maximum(o, 0) / 5.0) * 0.9 + np.exp(-np.maximum(o, 0) / 22.0) * 0.18)[..., None] * np.array([1.0, 0.30, 0.10], f32)
            return (red + blue + halo) * (k * I * (o > -1.0))[..., None]
        splat(img, x, y, R + 90, fn)

    def jupiter(self, img, t, sc, I_ring, sun_xy, hidden, glow_amt):
        x0, x1, y0, y1 = self.j_bbox
        reg = img[y0:y1, x0:x1]
        if sc < 0.999:                                                       # bloom-in / implode: scale about C
            M = np.float32([[sc, 0, (1 - sc) * C[0]], [0, sc, (1 - sc) * C[1]]])
            Wf, Hf = self.L.W, self.L.H
            m = cv2.warpAffine(self.j_m, M, (Wf, Hf))[y0:y1, x0:x1]; tex = cv2.warpAffine(self.j_tex, M, (Wf, Hf))[y0:y1, x0:x1]
            rr = cv2.warpAffine(self.j_rr, M, (Wf, Hf), borderValue=9)[y0:y1, x0:x1]; ang = cv2.warpAffine(self.j_ang, M, (Wf, Hf))[y0:y1, x0:x1]
            jv = cv2.warpAffine(self.j_v, M, (Wf, Hf))[y0:y1, x0:x1]; ju = cv2.warpAffine(self.j_u, M, (Wf, Hf))[y0:y1, x0:x1]
            Rj = R_JUP * sc
        else:
            m = self.j_m[y0:y1, x0:x1]; tex = self.j_tex[y0:y1, x0:x1]; rr = self.j_rr[y0:y1, x0:x1]; ang = self.j_ang[y0:y1, x0:x1]
            jv = self.j_v[y0:y1, x0:x1]; ju = self.j_u[y0:y1, x0:x1]; Rj = R_JUP
        reg *= (1 - m)[..., None]
        reg += tex * 0.006 * m[..., None]
        # lightning in the night-side storms + a faint auroral oval at the north pole
        for i, (lu, lv, ph, sz) in enumerate(self.lightning):
            fl = max(0.0, math.sin(t * (2.3 + 0.37 * i) + ph)) ** 40 * (1 + 2 * max(0.0, math.sin(t * 17 + i)) ** 8)
            if fl < 0.02: continue
            d2 = (ju - lu) ** 2 + (jv - lv) ** 2
            reg += (np.exp(-d2 / (0.0009 * sz)) * fl * 0.5 * m)[..., None] * np.array([0.75, 0.85, 1.0], f32)
        au = np.exp(-(((ju + 0.05) / 0.22) ** 2 + ((jv + 0.90) / 0.05) ** 2)) * (0.7 + 0.3 * math.sin(t * 1.7))
        reg += (au * m * 0.05)[..., None] * np.array([1.0, 0.35, 0.65], f32)
        # the ring of sunlight through the upper atmosphere (strongest towards the Sun)
        sdir = math.atan2(sun_xy[1] - J_C[1], sun_xy[0] - J_C[0])
        dd = (ang - sdir + np.pi) % (2 * np.pi) - np.pi
        spread = 0.25 + 1.4 * hidden
        k = np.exp(-(dd / spread) ** 2) * (0.6 + 0.4 * hidden) + 0.10 + 0.35 * hidden
        o = (rr - 1) * Rj
        core = np.exp(-((o - 0.4) / 0.9) ** 2) * 5.0
        haze = np.exp(-np.maximum(o, 0) / 4.0) * 1.0 * (o > -1.2) + np.exp(-np.maximum(o, 0) / 30.0) * 0.12 * (o > -1.2)
        ringc = core[..., None] * np.array([1.0, 0.86, 0.60], f32) + haze[..., None] * np.array([1.0, 0.70, 0.40], f32)
        ringc += (np.exp(-((o - 2.6) / 1.2) ** 2) * 0.8)[..., None] * np.array([0.45, 0.70, 1.0], f32)
        reg += ringc * (k * I_ring)[..., None]
        # glare where the Sun slips behind the limb
        if glow_amt > 0:
            ds = np.sqrt((self.xx[y0:y1, x0:x1] - sun_xy[0]) ** 2 + (self.yy[y0:y1, x0:x1] - sun_xy[1]) ** 2)
            reg += ((np.exp(-ds / 10) * 3.0 + np.exp(-ds / 60) * 0.5) * glow_amt * (o > -2))[..., None] * np.array([1.0, 0.93, 0.80], f32)
        img[y0:y1, x0:x1] = reg
        return m

    def saturn(self, img, t, sc, ring_gain, sky_E):
        x0, x1, y0, y1 = self.s_box
        if sc < 0.999:
            Wf, Hh = x1 - x0, y1 - y0
            M = np.float32([[sc, 0, (1 - sc) * (C[0] - x0)], [0, sc, (1 - sc) * (C[1] - y0)]])
            wa = lambda a, bv=0: cv2.warpAffine(a, M, (Wf, Hh), borderValue=bv)
            m, tex, main, dust, E, op, fr, shd, ang, rp = (wa(self.s_m), wa(self.s_tex), wa(self.r_main), wa(self.r_dust), wa(self.r_E),
                                                           wa(self.r_opac), wa(self.r_front), wa(self.r_shadow, 1), wa(self.s_ang), wa(self.s_rp, 9))
            Rs = R_SAT * sc
        else:
            m, tex, main, dust, E, op, fr, shd, ang, rp = (self.s_m, self.s_tex, self.r_main, self.r_dust, self.r_E, self.r_opac,
                                                           self.r_front, self.r_shadow, self.s_ang, self.s_rp)
            Rs = R_SAT
        reg = img[y0:y1, x0:x1]
        g = ring_gain
        ringcol = np.array([1.0, 0.90, 0.74], f32)
        # far rings (behind the globe) -> globe -> near rings
        back = (1 - fr)
        reg *= (1 - op * back * 0.6)[..., None]
        reg += ((main * 1.6 + dust * 1.0) * back * (1 - m) * g)[..., None] * ringcol
        reg *= (1 - m)[..., None]
        reg += tex * 0.020 * (0.6 + 0.4 * g) * m[..., None]
        o = (rp - 1) * Rs                                                    # backlit atmosphere: thin bright limb
        limb = (np.exp(-((o - 0.5) / 0.8) ** 2) * 2.4 + np.exp(-np.maximum(o, 0) / 6) * 0.45 * (o > -1)) * (0.75 + 0.25 * np.cos(ang + 1.2))
        reg += (limb * (0.6 + 0.4 * g))[..., None] * np.array([1.0, 0.88, 0.70], f32)
        reg *= (1 - op * fr * 0.85)[..., None]
        reg += ((main * 1.6 + dust * 1.0) * fr * shd * g)[..., None] * ringcol
        reg += (E * g * sky_E)[..., None] * np.array([0.55, 0.75, 1.0], f32)
        img[y0:y1, x0:x1] = reg

    def earth_dot(self, img, t, amt, ptr):
        x, y = EARTH_DOT
        tw = 0.9 + 0.1 * math.sin(t * 9)
        def fn(d, dx, dy):
            sp = (np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 6) + np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 6))
            return (np.exp(-d / 0.9) * 5 + sp * 0.9)[..., None] * np.array([0.55, 0.78, 1.0], f32) * amt * tw
        splat(img, x, y, 24, fn)
        if ptr > 0:
            col = np.array([0.35, 1.0, 0.85], f32); r0 = 40 + 4 * math.sin(t * 5); ping = (t * 1.3) % 1.0
            def pf(d, dx, dy):
                ring = np.exp(-((d - r0) / 2.0) ** 2) * 2.0
                a = np.arctan2(dy, dx) - t * 1.6
                br = np.exp(-((d - r0 - 16) / 2.4) ** 2) * (np.cos(a * 4) > 0.55) * 2.2
                pg = np.exp(-((d - (r0 + 10 + 110 * ping)) / 3.0) ** 2) * (1 - ping) ** 1.5 * 1.6
                return (ring + br + pg)[..., None] * col * ptr
            splat(img, x, y, r0 + 140, pf)

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, P, light):
        fg = self.fg
        base = fg.rgb * (1 - P["flat"]) + fg.flat * P["flat"]
        out = base * np.array(P["tint"], f32) * P["gain"] + fg.flat * np.array(P["amb"], f32)
        if P["rim"] > 0:
            out += (self.rim * 0.9 + self.rim_soft * 0.3)[..., None] * np.array(P["rcol"], f32) * P["rim"] * 0.06
        return out * light

    def water_reflect(self, sky_img, fgc, t, dim):
        """mirror the rendered sky into the shallows: slight slow ripple, softened, darkened; Fresnel-weighted"""
        y0, y1, x1 = self.wy0, self.wy1, self.wx1
        ys = self.yy[y0:y1, :x1]; xs = self.xx[y0:y1, :x1]
        nu = cv2.remap(self.wnoise, ((xs * 0.6 + t * 6) % 512).astype(f32), ((ys * 2.2 + t * 3) % 256).astype(f32), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_WRAP)
        depth = np.clip((ys - self.hz) / (y1 - self.hz), 0, 1)
        my = 2 * self.hz - ys + nu * (0.8 + 2.5 * depth)
        mx = xs + nu * (0.6 + 1.5 * depth)
        refl = cv2.remap(sky_img, mx.astype(f32), np.clip(my, 0, self.hz - 1).astype(f32), cv2.INTER_LINEAR)
        refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=1.2, sigmaY=2.5)
        wm = self.water[y0:y1, :x1][..., None]
        R = self.fres[..., None] * wm
        base = fgc[y0:y1, :x1]
        fgc[y0:y1, :x1] = base * (1 - R * 0.85) + refl * R * 0.80 * dim

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        P, cur, t0, t1 = self.mix_params(t)
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.45 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        sc = back_out(u_in) if t0 > 0 else 1.0
        final = cur == "day" or t1 >= T_BACK - 1e-6 and cur == "sat"
        col_u = 0.0 if (t1 > 1e8 or final) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        if col_u > 0:
            if col_u < 0.45: sc *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; sc *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        cx, cy = C
        # ---- visible-sun fraction (drives the sky glare)
        vis = 1.0
        if cur == "earth": vis = earth_vis(t)
        if cur == "io": vis = 1 - self.io_hidden(t)
        if cur in ("moon", "sat"): vis = 0.0
        sky = self.sky(t, P, col_u, vis)
        img = self.up(sky * (1 - 0.3 * col_u))
        if P["stars"] > 0.01:
            st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.2, plate_gain=0.16, star_gain=1.0, cx=1500, cy=1100, rot=-8.0)
            img += st * P["stars"]
        # ---- the eclipse
        if cur in ("earth", "day"):
            mo = moon_off(t) * sc if cur == "earth" else 1e9
            rs, rm = R_SUN_E * sc, R_MOON * sc
            occ = (lambda dx, dy: smooth(rm + 0.6, rm - 0.6, np.sqrt((dx - mo) ** 2 + (dy - mo * 0.10) ** 2))) if cur == "earth" else None
            if cur == "earth":
                tot = ramp(t, T_C2 - 0.35, T_C2 + 0.6)
                self.corona(img, cx, cy, rs, tot * min(I_mul, 1.8), t)
                # the Moon: invisible against the bright sky, a black disc in totality
                if tot > 0:
                    mx0, my0 = int(cx + mo - rm - 3), int(cy + mo * 0.10 - rm - 3)
                    reg = img[my0:my0 + int(2 * rm + 7), mx0:mx0 + int(2 * rm + 7)]
                    ddm = np.sqrt((self.xx[my0:my0 + reg.shape[0], mx0:mx0 + reg.shape[1]] + 0.5 - cx - mo) ** 2
                                  + (self.yy[my0:my0 + reg.shape[0], mx0:mx0 + reg.shape[1]] + 0.5 - cy - mo * 0.10) ** 2)
                    reg *= (1 - 0.93 * tot * smooth(rm + 0.6, rm - 0.6, ddm))[..., None]
            frac = self.sun(img, cx, cy, rs, I_mul * (1.0 if cur == "earth" else 1.0), occ=occ, pad=60)
            if cur == "earth":
                # Moon disc: black (only shows where it covers the Sun / corona); diamond ring at second contact
                dia = math.exp(-((t - (T_C2 - 0.10)) / 0.17) ** 2) if t < T_C2 + 0.4 else 0.0
                if dia > 0.01:
                    bx, by = cx - rs * 0.98, cy - rs * 0.12
                    splat(img, bx, by, 260, lambda d, dx, dy: ((np.exp(-d / 1.6) * 40 + np.exp(-d / 9) * 4 + np.exp(-d / 45) * 0.6) * dia)[..., None]
                          * np.array([1.0, 0.97, 0.92], f32))
                    for kk in range(6):
                        a = kk * math.pi / 3 + 0.3
                        splat(img, bx, by, 240, lambda d, dx, dy, a=a: (np.exp(-np.abs(-dx * math.sin(a) + dy * math.cos(a)) / 1.3) * np.exp(-d / 90)
                                                                       * (dx * math.cos(a) + dy * math.sin(a) > 0) * 2.5 * dia)[..., None] * np.array([1.0, 0.95, 0.88], f32))
        elif cur == "mars":
            rs = R_SUN_M * sc
            u = (t - T_P0) / (T_P1 - T_P0)
            px = (-1 + 2 * u) * (rs + PHO_A * 1.3 + 2); py = -0.22 * rs + (-1 + 2 * u) * 0.25 * rs
            occf = self.phobos(img, 0, 0, sc, t)
            self.sun(img, cx, cy, rs, I_mul * 0.85, col=(0.95, 0.96, 1.0), occ=lambda dx, dy: occf(dx - px, dy - py), pad=50)
            # pointer brackets round the transit
            pa = ramp(t, wt("mars", "PHOBOS") - 0.1, wt("mars", "PHOBOS") + 0.3) * (1 - col_u)
            if pa > 0:
                colp = np.array([0.35, 1.0, 0.85], f32); r0 = 44 + 3 * math.sin(t * 5)
                splat(img, cx, cy, r0 + 30, lambda d, dx, dy: ((np.exp(-((d - r0) / 2.0) ** 2) * 1.6 + np.exp(-((d - r0 - 15) / 2.3) ** 2)
                                                                * (np.cos((np.arctan2(dy, dx) - t * 1.4) * 4) > 0.55) * 2.0) * pa)[..., None] * colp)
        elif cur == "moon":
            R = R_EARTH_L * sc
            ex, ey = cx, cy
            I_r = (0.55 + 0.45 * ramp(t, T_RED - 0.6, T_RED + 0.2)) * I_mul
            # a last diamond flash as the Sun slips fully behind Earth (just after the swap)
            self.earth_ring(img, ex, ey, R, I_r, t, sdir=math.radians(150))
            self.corona(img, ex, ey, R, 0.10 * ramp(t, t0 + 0.2, t0 + 1.0), t)
        elif cur == "io":
            hid = self.io_hidden(t)
            # the Sun slides towards C and behind the limb
            uu = ease((t - T_J0) / (T_SWALLOW - T_J0))
            dist = R_JUP + (R_SUN_J * 3 + 26) * (1 - uu) - R_SUN_J * 1.6 * ramp(t, T_SWALLOW, T_SWALLOW + 1.5)
            sxy = (J_C[0] - J_DIR[0] * dist, J_C[1] - J_DIR[1] * dist)
            sxy_s = (C[0] + (sxy[0] - C[0]) * sc, C[1] + (sxy[1] - C[1]) * sc)
            jm = self.jupiter(img, t, sc, (0.30 + 0.9 * hid) * I_mul, sxy_s, hid, 0.6 * math.exp(-((t - T_SWALLOW + 0.15) / 0.25) ** 2))
            rj = R_JUP * sc; jc = (C[0] + (J_C[0] - C[0]) * sc, C[1] + (J_C[1] - C[1]) * sc)
            def occj(dx, dy):
                X = sxy_s[0] + dx - jc[0]; Y = sxy_s[1] + dy - jc[1]
                return smooth(rj + 0.6, rj - 0.6, np.sqrt(X * X + Y * Y))
            self.sun(img, sxy_s[0], sxy_s[1], max(R_SUN_J * sc, 0.4), I_mul * 1.4, col=(1.0, 0.96, 0.90), occ=occj, pad=40, glare=1.5)
        elif cur == "sat":
            g = (0.55 + 0.45 * ramp(t, T_LIGHT - 0.3, T_LIGHT + 0.4)) * min(I_mul, 2.2)
            self.saturn(img, t, sc, g, 1.0)
            ea = ramp(t, t0 + 0.8, t0 + 1.4) * (1 - col_u)
            self.earth_dot(img, t, ea * (1 + 1.2 * math.exp(-((t - wt("sat_d", "US")) / 0.3) ** 2)), ramp(t, T_DOT - 0.1, T_DOT + 0.3) * (1 - ramp(t, T_WO0 - 0.3, T_WO0)))
        sky_img = img
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(P, light)
        bmf = self.up(self.beams_layer(t, P, col_u))
        fgc = fgc + bmf * 0.05 * fg.a[..., None]
        self.water_reflect(sky_img, fgc, t, 1.0)
        a = fg.a[..., None]
        img = sky_img * (1 - a) + fgc * a
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "day":
                fc = np.array({"mars": (1.0, 0.75, 0.5), "moon": (1.0, 0.45, 0.3), "io": (1.0, 0.85, 0.55), "sat": (0.7, 0.85, 1.0)}[k], f32)
                img += (2.6 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, cx, cy, u, fc)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([1.0, 0.95, 0.88], f32)
            self.shock(img, cx, cy, t - T_BACK, np.array([1.0, 0.9, 0.7], f32))
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.0)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
        return out

    def shock(self, img, cx, cy, u, col):
        R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55) * (0.6 + 0.4 * col[ch])

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
        key = cur
        if cur == "earth": t0 = LN["earth"]["start"]
        if cur == "day" or (cur == "earth" and t < LN["earth"]["start"] + 0.1): key = None
        x, ys = W / 2, (1215, 1300, 1358)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if T_WO0 < t: a *= 1 - ramp(t, T_WO0 - 0.2, T_WO0 + 0.1)
        if key and a > 0.01:
            name, l2, l3, tc = RO[key]
            dy = (1 - a) * 18
            rgba, _ = word_layer(name, int(L.hud_size * 1.30), W * 0.9, fill=tc)
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, l2, x, ys[1] + dy, int(L.hud_size * 0.60), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, l3, x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (235, 240, 250), a, 0.10, display=True)
        if cur == "sat":
            la = ramp(t, T_DOT + 0.2, T_DOT + 0.5) * (1 - ramp(t, T_WO0 - 0.3, T_WO0))
            if la > 0.01: hud_text(out, "EARTH", EARTH_DOT[0], EARTH_DOT[1] + 64, int(L.hud_size * 0.42), "Black", (190, 255, 235), la, 0.14, display=True)
        self.caps.draw(out, t)


def save_png(im, path):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def run_stills(ts):
    sc = Scene(True); d = os.path.join(SCR, "stills"); os.makedirs(d, exist_ok=True)
    for t in ts:
        t0 = time.time(); im = sc.frame(t); save_png(im, os.path.join(d, f"vert_{t:05.2f}.png"))
        print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "hz?")
        for k, v in dict(R_SUN_E=R_SUN_E, R_MOON=R_MOON, R_SUN_M=R_SUN_M, PHO_A=PHO_A, PHO_B=PHO_B, R_EARTH_L=R_EARTH_L, R_JUP=R_JUP,
                         R_SUN_J=R_SUN_J, R_SAT=R_SAT, A_RING=136775 * K_SAT).items():
            print(f"{k:10s} {v:8.2f} px  = {2 * math.degrees(math.atan(v / F_PX)):.3f} deg")
        print({k: round(v, 2) for k, v in T_SW.items()}, "C2", round(T_C2, 2), "swallow", round(T_SWALLOW, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    run_stills([float(x) for x in sys.argv[2].split(",")])
