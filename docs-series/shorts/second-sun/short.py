"""WHAT IF EARTH HAD A SECOND SUN? -- one locked tripod shot of the park (A2_park), VFX spectacle style.
The sky swaps between real binary-star systems, each seen from where a planet could really orbit:
  * Earth-equivalent orbit (the planet gets the same total starlight Earth does) for Alpha Centauri A, Sirius A,
    Algol (circling the whole triple) and W Ursae Majoris;
  * the real planet's orbit for Kepler-16 (Kepler-16b, 0.705 au, 31 % of Earth's sunlight).
Every disc is drawn at its true angular size through the plate's own lens (f = 1148 px, ~80 deg vertical FOV); the
eclipsing Algol pair and the contact binary also get a magnifier loupe. The park is relit by every star separately:
coloured light, ground-plane shadows per star (double shadows), sky tint mixed from both stars.
  Sun -> Alpha Cen (day, then a night lit by B) -> Sirius -> Kepler-16 double sunset -> Algol eclipse -> W UMa -> white-out -> Sun
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert                    full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5            stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2      re-render only those time ranges
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, kf, noise1, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-second-sun"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
# SOURCE px of A2_park.png (941x1672), as measured for ../betelgeuse-tonight: lamp heads + pole bases, lawn plane
LAMPS_SRC = [(193, 1198, 1325), (666, 1207, 1322), (816, 1113, 1323)]
LAWN_SRC = 1324
VAN_SRC = 1300
F_SRC = 1000.0
CAM_H = 1.3
FPS = 30
LEAD, TAIL = 0.25, 1.20
RSUN_AU = 0.00465047

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t1" if end else "t0"]


# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["sun", "acen", "sir", "kep", "alg", "wuma"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
T_SUNBACK = LN["end"]["start"] - 0.10
T_WO0 = T_SUNBACK - 0.85
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "sun2")]
COLLAPSE, BLOOM = 0.40, 0.60
T_NIGHT0 = wt("acen", "SOME") - 0.45; T_NIGHT1 = T_NIGHT0 + 0.8            # Alpha Cen A sets, B lights the night
K0, K1 = T_SW["kep"], T_SW["alg"]
T_DSUN = wt("kep", "SUNSET"); T_DSHAD = wt("kep", "SHADOWS")
A0, A1 = T_SW["alg"], T_SW["wuma"]
T_ECL0 = wt("alg", "ECLIPSES") - 0.25; T_ECLM = wt("alg", "DAYLIGHT") + 0.05
W0 = T_SW["wuma"]
PULSES = [wt("hook", "SECOND"), wt("acen", "HUNDREDS"), wt("acen", "DARK"), wt("sir", "BLAZE"), wt("sir", "DWARF"), wt("sir", "EARTH'S"),
          T_DSUN, T_DSHAD, wt("alg", "DEMON"), wt("alg", "2.87"), wt("wuma", "TOUCHING"), wt("end", "SINGLE")]


def star_at(t):
    cur, t0 = "sun", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("sun" if k == "sun2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def prev_of(t0):
    for i, (ts, k) in enumerate(SWAPS):
        if ts == t0: return "sun" if i == 0 else ("sun" if SWAPS[i - 1][1] == "sun2" else SWAPS[i - 1][1])
    return None


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w):
    if isinstance(a, (tuple, list)): return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


# ------------------------------------------------------------------------------------------------ colour helpers
_T = np.linspace(1500, 30000, 1024)
BB_LUT = np.stack([bbcolor(x) for x in _T]).astype(f32)
def bb_vec(T):
    i = np.clip((np.asarray(T) - 1500) / (30000 - 1500) * 1023, 0, 1023).astype(np.int32); return BB_LUT[i]


def vivid(c, k=1.4):
    c = np.asarray(c, f32); y = float(lum(c)); return (np.clip(y + (c - y) * k, 0.0, None) / max(y, 1e-4)).astype(f32)


def palette(x):
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (np.asarray(x, f32)[..., None] - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (np.asarray(x) % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


SUN_C = bbcolor(5772.0)
def light_col(T):
    """colour of a star's light, luminance 1 (a little more saturated than physical, for the grade)"""
    return vivid(bbcolor(T), 1.35)


def redden(c, X):
    """atmospheric extinction colour at airmass X (Rayleigh + aerosol, per channel optical depth)"""
    return (np.asarray(c, f32) * np.exp(-np.array([0.075, 0.13, 0.28], f32) * X)).astype(f32)


def airmass(alt_deg):
    h = max(alt_deg, -0.5)
    return 1.0 / (math.sin(math.radians(h)) + 0.50572 * (h + 6.07995) ** -1.6364)        # Kasten & Young 1989


# ------------------------------------------------------------------------------------------------ the systems
# true angular sizes (deg) -> radius px through the plate lens
F_PX = F_SRC * (1080 / 941)
def rpx(ang_deg): return F_PX * math.tan(math.radians(ang_deg / 2))
ANG = dict(sun=0.533, acenA=0.529, sirA=0.181, kepA=0.491, kepB=0.171)
# Algol (Baron et al. 2012): a = 0.0618 au = 13.29 R_sun, i = 98.7 deg, q = 0.221; planet at 14.1 au (circling the triple)
ALG = dict(a=13.29, i=math.radians(98.7), q=0.70 / 3.17, RA=2.73, RB=3.48, TA=12550.0, TB=4500.0, d_au=14.1)
# W UMa: P = 0.3336 d, M = 1.19 + 0.57 M_sun -> a = 2.44 R_sun; R = 1.08, 0.78 R_sun; i ~ 86 deg; planet at 1.54 au
WUM = dict(a=2.44, i=math.radians(86.0), q=0.57 / 1.19, R1=1.08, R2=0.78, T=6200.0, d_au=1.54)
def px_per_rsun(d_au): return F_PX * RSUN_AU / d_au

POS = dict(sun=(598.0, 600.0), acenA=(598.0, 600.0), acenB=(490.0, 660.0), sirA=(598.0, 600.0), sirB=(930.0, 520.0),
           pair=(590.0, 640.0))
LOUPE = dict(cx=790.0, cy=1168.0, R=196.0)

BEAMS = {
    "sun": "rainbow",
    "acenA": [(1.0, 0.80, 0.30), (1.0, 0.62, 0.18), (0.55, 0.95, 1.0), (1.0, 0.92, 0.55)],
    "acenB": [(1.0, 0.42, 0.08), (1.0, 0.62, 0.20), (1.0, 0.30, 0.25), (1.0, 0.75, 0.30)],
    "sirA": [(0.30, 0.70, 1.0), (0.75, 0.45, 1.0), (0.85, 0.95, 1.0), (0.20, 1.0, 0.95)],
    "kepA": [(1.0, 0.45, 0.08), (1.0, 0.70, 0.22), (1.0, 0.30, 0.35), (1.0, 0.55, 0.10)],
    "kepB": [(1.0, 0.20, 0.10), (1.0, 0.35, 0.45), (0.95, 0.40, 0.08)],
    "alg": [(0.40, 0.75, 1.0), (0.65, 0.50, 1.0), (1.0, 0.65, 0.25), (0.30, 1.0, 0.95)],
    "wuma": [(1.0, 0.95, 0.65), (0.45, 0.95, 1.0), (1.0, 0.55, 0.85), (1.0, 0.80, 0.35)],
}

INFO = {
    "sun": dict(name="OUR SUN", l2="ONE STAR · 5,800 K", l3="SINGLE", tc=(255, 226, 150)),
    "acen": dict(name="ALPHA CENTAURI", l2="G2 5,800 K  +  K1 5,300 K", l3="B: 140–1,400× THE FULL MOON", tc=(255, 196, 110)),
    "sir": dict(name="SIRIUS", l2="A1 9,900 K  +  WHITE DWARF 25,000 K", l3="B: SUN'S MASS · EARTH-SIZED", tc=(170, 214, 255)),
    "kep": dict(name="KEPLER-16", l2="K 4,450 K  +  M 3,300 K", l3="REAL PLANET · 229-DAY YEAR", tc=(255, 150, 80)),
    "alg": dict(name="ALGOL", l2="B8 12,500 K  +  K 4,500 K", l3="ECLIPSE EVERY 2.87 DAYS", tc=(185, 205, 255)),
    "wuma": dict(name="W URSAE MAJORIS", l2="F 6,200 K  +  F 6,200 K · TOUCHING", l3="ONE ORBIT EVERY 8 HOURS", tc=(255, 235, 170)),
}


# ------------------------------------------------------------------------------------------------ binary geometry
def algol_phase(t):
    """orbital phase (rad, 0 = primary eclipse) during the Algol beat (time-compressed)"""
    return math.radians(kf(t, [(A0, -52.0), (T_ECL0, -30.0), (T_ECLM, -1.5), (T_ECLM + 0.35, 1.5), (A1 - 0.2, 34.0), (A1 + 1.0, 45.0)]))


def wuma_phase(t): return 2 * math.pi * (t - W0) / 5.0 + 1.35


def sky_xy(r, phi, inc):
    """position of a body at orbital radius r (towards the companion = +), phase phi -> (sky x, sky y, depth to viewer)"""
    return r * math.sin(phi), r * math.cos(phi) * math.cos(inc), r * math.cos(phi) * math.sin(inc)


def algol_bodies(phi):
    A = ALG; rA = A["a"] * A["q"] / (1 + A["q"]); rB = A["a"] / (1 + A["q"])
    xb, yb, zb = sky_xy(rB, phi, A["i"]); xa, ya, za = -xb * rA / rB, -yb * rA / rB, -zb * rA / rB
    return (xa, ya, za), (xb, yb, zb)


SURF_B_REL = 0.10                                   # Algol B surface brightness relative to A (V band, compressed)
def binary_field(kind, phi, X, Y):
    """surface brightness map (relative, A/primary centre = 1) and colour index field on sky-plane coords X, Y [R_sun]
    -> (val, T) arrays; val = 0 outside the stars"""
    if kind == "alg":
        (xa, ya, za), (xb, yb, zb) = algol_bodies(phi)
        out = np.zeros_like(X); T = np.full_like(X, ALG["TA"])
        bodies = [(xa, ya, za, ALG["RA"], 1.0, ALG["TA"], 0.55), (xb, yb, zb, ALG["RB"], SURF_B_REL, ALG["TB"], 0.75)]
        for x, y, z, R, s, Tb, u in sorted(bodies, key=lambda b: b[2]):          # far body first, near body paints over
            r2 = ((X - x) ** 2 + (Y - y) ** 2) / (R * R)
            m = r2 < 1
            mu = np.sqrt(np.clip(1 - r2, 0, 1))
            out = np.where(m, s * (1 - u * (1 - mu)), out); T = np.where(m, Tb * (0.88 + 0.12 * mu), T)
        return out.astype(f32), T.astype(f32)
    W = WUM
    r1 = W["a"] * W["q"] / (1 + W["q"]); r2_ = W["a"] / (1 + W["q"])
    x2, y2, z2 = sky_xy(r2_, phi, W["i"]); x1, y1, z1 = -x2 * r1 / r2_, -y2 * r1 / r2_, -z2 * r1 / r2_
    ax = np.array([x2 - x1, y2 - y1]); pl = np.hypot(*ax); fs = pl / W["a"]; ax = ax / max(pl, 1e-6)
    def sd(x, y, R):
        dx, dy = X - x, Y - y; al = dx * ax[0] + dy * ax[1]; pp = -dx * ax[1] + dy * ax[0]
        e = 1 + 0.22 * fs                                                       # tidal elongation along the axis
        return np.sqrt((al / e) ** 2 + pp ** 2) - R
    s1, s2 = sd(x1, y1, W["R1"]), sd(x2, y2, W["R2"])
    k = 0.30 * fs + 0.02
    u_ = -k * np.log(np.exp(-s1 / k) + np.exp(-s2 / k))                         # smooth union (the shared envelope)
    near1 = (z1 >= z2)
    sf, Rf = (s1, W["R1"]) if near1 else (s2, W["R2"])
    sb, Rb = (s2, W["R2"]) if near1 else (s1, W["R1"])
    use_f = sf < 0.05 * Rf
    sdl = np.where(use_f, sf, np.minimum(u_, sb)); Rl = np.where(use_f, Rf, Rb)
    sdl = np.minimum(sdl, u_ + 0.0)
    rr = np.clip(1 + sdl / Rl, 0, 1); mu = np.sqrt(1 - rr * rr)
    neck = np.exp(-(np.minimum(s1, s2) / (0.25 * W["R2"])) ** 2) * (np.minimum(s1, s2) > -0.05)
    val = (1 - 0.75 * (1 - mu)) * (0.45 + 0.55 * mu) * (1 - 0.25 * neck * fs) * (u_ < 0)
    T = W["T"] * (0.9 + 0.1 * mu) * (1 - 0.04 * neck)
    return val.astype(f32), T.astype(f32)


_flux_cache = {}
def binary_flux(kind, phi):
    """total flux relative to maximum light, from the same field (cached on a 1/2-deg phase grid)"""
    key = (kind, round(math.degrees(phi) * 2) / 2)
    if key not in _flux_cache:
        g = np.linspace(-17, 17, 340) if kind == "alg" else np.linspace(-3.4, 3.4, 300)
        X, Y = np.meshgrid(g, g); X, Y = X.astype(f32), Y.astype(f32)
        v, _ = binary_field(kind, math.radians(key[1]), X, Y)
        _flux_cache[key] = float(v.sum())
    if (kind, "max") not in _flux_cache:
        _flux_cache[(kind, "max")] = max(binary_flux_raw(kind, math.radians(p)) for p in (90.0, -90.0))
    return _flux_cache[key] / _flux_cache[(kind, "max")]


def binary_flux_raw(kind, phi):
    g = np.linspace(-17, 17, 340) if kind == "alg" else np.linspace(-3.4, 3.4, 300)
    X, Y = np.meshgrid(g, g)
    v, _ = binary_field(kind, phi, X.astype(f32), Y.astype(f32)); return float(v.sum())


# ------------------------------------------------------------------------------------------------ per-system state
HY = VAN_SRC * (1080 / 941) + (1920 - 1672 * (1080 / 941)) + 8           # true horizon row in the vertical frame
def alt_of(y): return math.degrees(math.atan((HY - y) / F_PX))


SKYLINE = None                                                             # set by Scene (frame skyline row per column)
def disc_vis(x, y, R):
    """fraction of a disc above the park's skyline (the hedge / roofs hide a setting sun)"""
    if SKYLINE is None: return 1.0
    sy = float(SKYLINE[int(np.clip(round(x), 0, len(SKYLINE) - 1))])
    return float(smooth(sy + R, sy - R, y))


def kepler_pos(t):
    u = (t - K0)
    ya = kf(t, [(K0 - 1, 1120.0), (K0, 1120.0), (T_DSUN, 1228.0), (T_DSHAD + 0.2, 1256.0), (K1, 1298.0), (K1 + 2, 1330.0)])
    yb = kf(t, [(K0 - 1, 1000.0), (K0, 1000.0), (T_DSUN, 1098.0), (T_DSHAD + 0.2, 1128.0), (K1, 1200.0), (K1 + 2, 1240.0)])
    return (606.0 + 2 * u, ya), (468.0 + 2 * u, yb)


# per-beat sky + grade. zen/hor: sky at full light (linear); low: optional horizon band; tint/con/sat: park grade
G = {
    "sun": dict(zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), low=None, tint=(1.0, 1.0, 1.0), con=1.0, sat=1.0, stars=0.0, halo=0.0),
    "acen_d": dict(zen=(0.025, 0.080, 0.33), hor=(0.95, 0.66, 0.30), low=(1.25, 0.70, 0.22), tint=(1.16, 0.96, 0.70), con=1.08, sat=1.15, stars=0.0, halo=0.3),
    "acen_n": dict(zen=(0.022, 0.016, 0.060), hor=(0.30, 0.115, 0.040), low=(0.42, 0.15, 0.04), tint=(1.0, 0.62, 0.32), con=1.05, sat=1.1, stars=1.0, halo=0.7),
    "sir": dict(zen=(0.000, 0.20, 0.60), hor=(0.50, 0.95, 1.30), low=None, tint=(0.76, 0.94, 1.32), con=1.30, sat=1.15, stars=0.0, halo=0.9),
    "kep": dict(zen=(0.050, 0.020, 0.085), hor=(0.80, 0.17, 0.05), low=(2.1, 0.62, 0.08), tint=(1.25, 0.72, 0.42), con=1.12, sat=1.25, stars=0.25, halo=1.0),
    "alg": dict(zen=(0.006, 0.090, 0.55), hor=(0.42, 0.62, 1.05), low=None, tint=(0.88, 0.96, 1.18), con=1.12, sat=1.05, stars=0.0, halo=0.5),
    "alg_dusk": dict(zen=(0.010, 0.010, 0.060), hor=(0.20, 0.10, 0.20), low=(0.32, 0.12, 0.10), tint=(0.62, 0.70, 1.15), con=1.0, sat=0.9, stars=1.0, halo=0.3),
    "wuma": dict(zen=(0.16, 0.050, 0.48), hor=(1.00, 0.78, 1.20), low=(1.25, 1.05, 1.35), tint=(1.06, 0.92, 1.20), con=1.10, sat=1.1, stars=0.0, halo=1.3),
}
def gmix(a, b, w):
    return {k: (None if a[k] is None and b[k] is None else lerp(a[k] if a[k] is not None else b["hor"], b[k] if b[k] is not None else a["hor"], w))
            for k in a}


def state(key, t):
    """lights (for sky + park), star draw ops, sky/grade, lamps, exposure, loupe"""
    S = dict(lights=[], draws=[], grade=G["sun"], lamps=0.0, expo=1.0, loupe=None, amb=0.30, labels=[], lv=1.0)
    if key == "sun":
        x, y = POS["sun"]
        S["lights"] = [dict(x=x, y=y, T=5772.0, E=1.0, beams="sun", bI=1.0, el=16.0)]
        S["draws"] = [dict(kind="disc", x=x, y=y, Rp=rpx(ANG["sun"]), T=5772.0, surf=40.0, glow=1.0, spikes=0.6, u=0.6)]
    elif key == "acen":
        (xa, ya), (xb, yb) = POS["acenA"], POS["acenB"]
        n = ramp(t, T_NIGHT0, T_NIGHT1)
        S["grade"] = gmix(G["acen_d"], G["acen_n"], n)
        # B's real share of the daylight is 1/250-1/2500; its daytime shadow is drawn at 0.22 (README: liberty)
        S["lights"] = [dict(x=xa, y=ya, T=5790.0, E=1.0 * (1 - n), beams="acenA", bI=1.0, el=14.0),
                       dict(x=xb, y=yb, T=5260.0, E=0.004 * (1 - n) + 0.42 * n, Esh=0.50 * (1 - n) + 0.42 * n, col=vivid(bbcolor(5260.0), 1.6),
                            beams="acenB", bI=0.25 + 0.85 * n, el=13.0)]
        S["draws"] = [dict(kind="disc", x=xa, y=ya, Rp=rpx(ANG["acenA"]), T=5790.0, surf=40.0 * (1 - n), glow=1.0 * (1 - n), spikes=0.6 * (1 - n), u=0.6),
                      dict(kind="disc", x=xb, y=yb, Rp=0.6, T=4600.0, col=vivid(bbcolor(5260.0), 2.2), surf=30.0, glow=0.9 + 1.0 * n, spikes=0.5 + 0.6 * n, u=0.6)]
        S["lamps"] = n; S["expo"] = 1.0 + 0.30 * n; S["amb"] = 0.24 * (1 - n) + 0.14 * n
        S["labels"] = [("A", xa, ya, 1 - n), ("B", xb, yb, 1.0)]
    elif key == "sir":
        (xa, ya), (xb, yb) = POS["sirA"], POS["sirB"]
        S["grade"] = G["sir"]
        S["lights"] = [dict(x=xa, y=ya, T=9940.0, E=1.15, beams="sirA", bI=1.5, el=14.0)]
        S["draws"] = [dict(kind="disc", x=xa, y=ya, Rp=rpx(ANG["sirA"]), T=9940.0, surf=170.0, glow=2.4, spikes=1.6, u=0.45),
                      dict(kind="disc", x=xb, y=yb, Rp=0.45, T=25000.0, surf=14.0, glow=0.55, spikes=0.5, u=0.5)]
        S["amb"] = 0.20; S["expo"] = 0.92
        S["labels"] = [("A", xa, ya, 1.0), ("B", xb, yb, 1.0)]
        S["loupe"] = dict(kind="sirb", star=(xb, yb))
    elif key == "kep":
        (xa, ya), (xb, yb) = kepler_pos(t)
        alA, alB = alt_of(ya), alt_of(yb); XA, XB = airmass(alA), airmass(alB)
        tA = 10 ** (-0.4 * 0.21 * XA); tB = 10 ** (-0.4 * 0.21 * XB)
        RA, RB = rpx(ANG["kepA"]), rpx(ANG["kepB"])
        visA, visB = disc_vis(xa, ya, RA), disc_vis(xb, yb, RB)
        EA = 0.963 * 0.31 * tA * visA; EB = 0.037 * 0.31 * tB * 6.0 * visB        # B: x6 (README: liberty)
        gain = 2.6 * (0.963 * 0.31 * tA + EB) ** -0.75                          # eye adaptation (keeps the A:B ratio)
        EA, EB = EA * gain, EB * gain
        cA = redden(bbcolor(4450.0), XA * 0.40); cB = redden(bbcolor(3311.0), XB * 0.55) * np.array([1.0, 0.55, 1.6], f32)   # B tinted crimson-pink
        S["grade"] = gmix(G["sun"], G["kep"], ramp(t, K0 - 0.2, T_DSUN - 0.6))
        S["lights"] = [dict(x=xa, y=ya, T=4450.0, E=EA, col=cA, beams="kepA", bI=1.25, el=max(alA, 9.0), halo=1.0),
                       dict(x=xb, y=yb, T=3311.0, E=EB, Esh=max(EB, 0.75 * EA), col=cB, beams="kepB", bI=1.0, el=max(alB, 11.0), halo=1.0)]
        S["draws"] = [dict(kind="disc", x=xa, y=ya, Rp=RA, T=4450.0, col=cA, surf=34.0 * max(tA, 0.08), glow=2.0, spikes=0.5, u=0.7),
                      dict(kind="disc", x=xb, y=yb, Rp=RB, T=3311.0, col=cB, surf=34.0 * max(tB, 0.1), glow=1.8, spikes=0.45, u=0.75)]
        S["lamps"] = ramp(t, T_DSUN - 0.5, T_DSUN + 1.0) * 0.8; S["amb"] = 0.06; S["expo"] = 1.05
        S["labels"] = [("A", xa, ya, visA), ("B", xb, yb, visB)]
    elif key == "alg":
        x, y = POS["pair"]
        phi = algol_phase(t); fl = binary_flux("alg", phi)
        dk = float(np.clip((1 - fl) / (1 - 0.324), 0, 1)) ** 0.8                 # 0 out of eclipse, 1 at minimum light
        S["grade"] = gmix(G["alg"], G["alg_dusk"], dk); S["lv"] = 1.0
        S["lights"] = [dict(x=x, y=y, T=11800.0 * fl + 4500 * (1 - fl) if fl < 0.98 else 11800.0, E=fl, beams="alg", bI=1.2 * (0.35 + 0.65 * fl), el=14.0)]
        S["draws"] = [dict(kind="alg", x=x, y=y, phi=phi, scale=px_per_rsun(ALG["d_au"]), surf=95.0, glow=1.6 * fl, spikes=1.0 * fl, T=11800.0)]
        S["loupe"] = dict(kind="alg", phi=phi, scale=LOUPE["R"] / 14.0, star=(x, y))
        fl_on = smooth(0.35, 0.7, dk)
        S["lamps"] = fl_on * (0.55 + 0.45 * (noise1(t, 77, 11.0) > -0.2 if fl_on < 0.95 else 1.0))
        S["amb"] = 0.26; S["expo"] = 0.95 + 0.6 * dk; S["dim"] = fl
    elif key == "wuma":
        x, y = POS["pair"]
        phi = wuma_phase(t); fl = binary_flux("wuma", phi)
        S["grade"] = G["wuma"]
        S["lights"] = [dict(x=x, y=y, T=6200.0, E=fl, col=np.array([1.0, 0.90, 1.12], f32), beams="wuma", bI=1.3, el=14.0, halo=1.3)]
        S["draws"] = [dict(kind="wuma", x=x, y=y, phi=phi, scale=px_per_rsun(WUM["d_au"]), surf=42.0, glow=1.6 * fl, spikes=0.9, T=6200.0)]
        S["loupe"] = dict(kind="wuma", phi=phi, scale=LOUPE["R"] / 2.75, star=(x, y))
        S["amb"] = 0.26; S["expo"] = 0.95
    return S


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.W, self.H = W, H
        lamps = [(lx, ly, by) for lx, ly, by in LAMPS_SRC]
        self.fg = fg = Foreground(FG_PATH, L, lamps=lamps, hz_frac=0.84)
        self.hz = HY
        global SKYLINE
        SKYLINE = fg.skyline.copy()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.clip((HY - yy) / HY, 0, 1)
        self.e = e
        self.k_hor = np.exp(-e / 0.33)[..., None].astype(f32)
        self.k_low = np.exp(-e / 0.10)[..., None].astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        # night stars (Alpha Cen night)
        n = 1100; sr = np.random.default_rng(12)
        self.ns = dict(x=sr.uniform(0, hw, n), y=sr.uniform(0, hh * 0.78, n), m=sr.uniform(0, 1, n) ** 3, ph=sr.uniform(0, 6.28, n),
                       c=np.stack([bbcolor(T) for T in sr.uniform(3500, 12000, n)]))
        # foreground prep
        a = fg.a
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a).astype(f32)
        self.alb = np.clip(fg.flat, 0, 1).astype(f32)
        self._shadow_src()
        rs = np.random.default_rng(31); ls = np.zeros((440, 440, 3), f32)
        for _ in range(160):
            x_, y_ = rs.integers(0, 440, 2); ls[y_, x_] += bbcolor(float(rs.uniform(3500, 15000))) * float(rs.uniform(0.2, 1.0) ** 3) * 2.5
        self.loupe_stars = cv2.GaussianBlur(ls, (0, 0), 0.6)
        et = np.stack([fbm2((128, 256), 51, 2.4), fbm2((128, 256), 52, 2.8)], -1)
        self.earth_tex = np.clip(et * 0.22 + 0.4, 0, 1).astype(f32)
        self.shcache = {}
        self.caps = Captions(L, WORDS, emphasis={"SECOND", "SUN", "HUNDREDS", "DARK", "BLAZE", "DWARF", "EARTH'S", "KEPLER-16b",
                                                 "SUNSET", "SHADOWS", "DEMON", "2.87", "ECLIPSES", "FADES", "TOUCHING", "ATMOSPHERE",
                                                 "PARTNER", "SINGLE"})
        L.cap_y = 880

    def up(self, a): return cv2.resize(a, (self.W, self.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- shadows
    def _shadow_src(self):
        im = np.asarray(Image.open(FG_PATH).convert("RGBA"), f32) / 255.0
        a = im[..., 3]; self.sh_, self.sw_ = a.shape
        yy, xx = np.mgrid[0:self.sh_, 0:self.sw_].astype(f32)
        self.lawn_src = (a > 0.5) & (yy > LAWN_SRC) & ~((xx < 52) & (yy < 1392))
        self.syy = yy
        fg = self.fg; self.M = np.array([[fg.s, 0, 0], [0, fg.s, fg.oy]], np.float64)
        self.lawn = self.warp(cv2.GaussianBlur(self.lawn_src.astype(f32), (0, 0), 0.7))
        # treeline profile: for each column, the solid run straight up from the far lawn edge (capped; the conifer and
        # the big tree have their own casters)
        cols = []
        for xs_ in range(2, self.sw_ - 1, 2):
            if 395 <= xs_ <= 545 or xs_ < 140: continue
            y = LAWN_SRC - 3
            if a[y, xs_] < 0.5: continue
            while y > LAWN_SRC - 170 and a[y - 1, xs_] > 0.5: y -= 1
            if LAWN_SRC - y > 6: cols.append((xs_, float(y)))
        self.tl_cols = cols

    def warp(self, m):
        return cv2.warpAffine(m, self.M, (self.W, self.H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(f32)

    def shadow(self, x_frame, el):
        """ground-plane shadow mask (frame px) of the conifer, the 3 lamp posts and the big trunk for a light at screen
        column x_frame (-> azimuth) and elevation el (deg). Copied from ../betelgeuse-tonight (_shadows), parametrised."""
        key = (int(round(x_frame / 6)), int(round(el * 2)))
        if key in self.shcache: return self.shcache[key]
        xs = key[0] * 6 / self.fg.s; el = key[1] / 2
        sh_, sw_ = self.sh_, self.sw_; cxs = sw_ / 2
        az = math.atan((xs - cxs) / F_SRC)
        kk = 1 / math.tan(math.radians(el)); kl = kk
        sa, ca = math.sin(az), math.cos(az)
        Q = 4; P = np.zeros((sh_ * Q, sw_ * Q), np.uint8)
        def scr(X, Z): return cxs + F_SRC * X / Z, VAN_SRC + F_SRC * CAM_H / Z
        def cast(xb, yb, ztop_px, prof, n=300, kk=kk):
            Zb = F_SRC * CAM_H / (yb - VAN_SRC); Xb = (xb - cxs) * Zb / F_SRC; Hh = (yb - ztop_px) * Zb / F_SRC
            Lp, Rp = [], []
            for u in np.linspace(0, 1, n):
                X = Xb - Hh * u * kk * sa; Z = Zb - Hh * u * kk * ca
                if Z < 0.4: break
                w = prof(u)
                xl, yl = scr(X - w * ca, Z + w * sa); xr, yr = scr(X + w * ca, Z - w * sa)
                Lp.append((xl * Q, yl * Q)); Rp.append((xr * Q, yr * Q))
            if len(Lp) > 1:
                poly = np.clip(np.array(Lp + Rp[::-1], np.float64), -1e5, 1e5).astype(np.int32)
                cv2.fillPoly(P, [poly], 255, cv2.LINE_AA)
        rng = np.random.default_rng(4); jit = rng.uniform(0.85, 1.15, 64)
        def conifer(u):
            if u < 0.06: return 0.35
            v = (u - 0.06) / 0.94; tier = (v * 9) % 1.0
            return 4.2 * (1 - v) ** 1.1 * (0.72 + 0.28 * tier) * jit[int(v * 63)] + 0.05
        cast(470, 1318, 950, conifer, 500)
        for lx, ly, by in LAMPS_SRC:
            cast(lx, by, ly, lambda u: 0.42, 600, kl)
        cast(22, 1384, 1050, lambda u: 0.55, 200)
        for xs_, top in self.tl_cols:                                                    # hedge / bush / tree line
            cast(xs_, LAWN_SRC, top, lambda u: 0.11, 40)
        Ms = cv2.resize(P.astype(f32) / 255, (sw_, sh_), interpolation=cv2.INTER_AREA)
        Mb = cv2.GaussianBlur(Ms, (0, 0), 3.0)
        w = 0.7 * np.clip((self.syy - LAWN_SRC) / 300.0, 0, 1) ** 0.8
        S = (Ms * (1 - w) + Mb * w) * self.lawn_src
        out = self.warp(S)
        if len(self.shcache) > 60: self.shcache.pop(next(iter(self.shcache)))
        self.shcache[key] = out
        return out

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, lights, g, lv=1.0):
        tot = sum(l["E"] for l in lights) + 1e-6
        def lc(l):
            c = l["col"] if "col" in l else bbcolor(l["T"]); return np.asarray(c, f32) / max(float(lum(c)), 1e-4)
        cm = sum(l["E"] * lc(l) for l in lights) / tot
        rel = np.clip(cm / (SUN_C / float(lum(SUN_C))), 0.3, 3.0) ** 0.5                   # tint of the mixed starlight
        rel = rel / max(float(lum(rel)), 1e-4)
        zen, hor = np.array(g["zen"], f32), np.array(g["hor"], f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        if g["low"] is not None:
            kl_ = np.exp(-self.e / 0.15)[..., None]
            sky = sky * (1 - kl_) + np.array(g["low"], f32) * kl_
        sky = sky * rel * lv
        bm = np.zeros_like(sky)
        for l in lights:
            if l["E"] < 1e-3 and l.get("bI", 0) < 0.05: continue
            dx = self.hx - l["x"]; dy = self.hy - l["y"]; d = np.sqrt(dx * dx + dy * dy) + 1e-3
            c = lc(l)
            Ea = min(l["E"], 1.2) ** 0.6
            hk = g["halo"] * l.get("halo", 0.6)
            aure = np.exp(-d / 45) * 0.9 + np.exp(-d / 220) * 0.12 + hk * (np.exp(-d / 110) * 0.6 + np.exp(-d / 420) * 0.18)
            sky += (aure * Ea)[..., None] * (0.25 + 0.75 * c)
            if l.get("beams"):
                bm += self.beams_layer(t, l, d, np.arctan2(dy, dx))
        return sky, bm

    def beams_layer(self, t, l, d, phi0, col_u=0.0):
        spin = 2 * math.pi * t / DUR * 0.6 + sum(map(ord, l["beams"])) % 7
        phi = phi0 + 0.0
        reach = 1500.0
        rad = (1 - np.exp(-(d + 6) / 35)) * (np.exp(-d / reach) * 0.9 + 0.12 * np.exp(-d / (reach * 2.2)))
        acc = np.zeros(d.shape + (3,), f32)
        pal = BEAMS[l["beams"]]
        for b in self.beams:
            a = b["a"] + spin * b["sp"] * 0.3
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(2 * math.pi * t / DUR * 4 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(2 * math.pi * t / DUR * 6 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.32) % 1.0 if b["rainbow"] else np.full(dp.shape, b["hue"], f32)
            c = palette(x) if pal == "rainbow" else pal_list(pal, x)
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.38 * l["bI"] * min(1.0, l["E"] ** 0.3 + 0.25)

    def night_stars(self, t, amt):
        if amt <= 0.01: return None
        s = self.ns; lay = np.zeros(self.hx.shape + (3,), f32)
        xi = s["x"].astype(int); yi = s["y"].astype(int)
        tw = 0.75 + 0.25 * np.sin(t * 5 + s["ph"])
        np.add.at(lay, (yi, xi), (s["c"] * (s["m"] * tw * amt * 0.9)[:, None]).astype(f32))
        lay = cv2.GaussianBlur(lay, (0, 0), 0.6) * 3
        return lay

    # -------------------------------------------------------------------------------------------- stars
    def draw_disc(self, img, t, S, I_mul=1.0, wob=0.0, hot=0.0, Rmul=1.0):
        """small limb-darkened HDR disc + corona glow + chromatic 6-blade spikes (from ../other-suns)"""
        cx, cy = S["x"], S["y"]; H, W = img.shape[:2]
        Rp = S["Rp"] * Rmul
        sc = S.get("col", bbcolor(S["T"] * (1 + hot)))
        sc = np.asarray(sc, f32) / max(float(np.max(sc)), 1e-4)
        pad = int(Rp * 1.6 + 420)
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        if x1 <= x0 or y1 <= y0: return
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; ang = np.arctan2(dy, dx)
        reg = img[y0:y1, x0:x1]
        Re = Rp * (1 + wob * (0.07 * np.sin(3 * ang + 9 * t) + 0.05 * np.sin(5 * ang - 13 * t)))
        Rd = max(Rp, 1.1)
        inside = smooth(Re + 0.9, Re - 0.9, d) if Rp > 1.5 else np.exp(-(d / 1.1) ** 2)
        area = min((Rp / Rd) ** 2, 1.0)
        mu = np.sqrt(np.clip(1 - (d / Rd) ** 2, 0, 1))
        ld = (1 - S["u"] * (1 - mu)) if Rp > 1.5 else 1.0
        occ = S.get("occ")
        if occ is not None: inside = inside * occ[y0:y1, x0:x1]
        reg += (inside * ld * S["surf"] * area * I_mul)[..., None] * (0.25 + 0.75 * sc)
        dd = np.maximum(d - Re, 0)
        g = (np.exp(-dd / (0.06 * Rp + 3)) * 2.2 + np.exp(-dd / (0.35 * Rp + 22)) * 0.55 + np.exp(-dd / (Rp + 90)) * 0.12) * (d > Re - 1)
        g = g * (0.6 + 0.3 * min(S["surf"], 150) / 40)
        if occ is not None: g = g * (0.15 + 0.85 * occ[y0:y1, x0:x1])
        reg += (g * S["glow"] * I_mul)[..., None] * (0.3 + 0.7 * sc) * (1 + 0.08 * math.sin(t * 2.3))
        self.spikes(reg, dx, dy, Re, S["spikes"] * I_mul, sc, t)
        img[y0:y1, x0:x1] = reg

    def spikes(self, reg, dx, dy, Re, amt, sc, t):
        if amt <= 0.01: return
        for k in range(6):
            a = k * math.pi / 3 + 0.26 + 0.03 * math.sin(t * 0.5)
            al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
            base = np.exp(-pp / 1.7) * (al > Re * 0.8)
            for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                reg[..., c] += base * np.exp(-np.maximum(al - Re, 0) / (150 * Lk)) * 2.2 * amt * (0.4 + 0.6 * sc[c])

    def draw_pair(self, img, t, S, I_mul=1.0, Rmul=1.0):
        """an unresolved / barely resolved binary in the main view: true geometry, 6x supersampled, plus glow"""
        cx, cy = S["x"], S["y"]; sc_ = S["scale"] * Rmul; ss = 6; half = 14
        g = (np.arange(2 * half * ss) + 0.5) / ss - half
        X, Y = np.meshgrid(g / max(sc_, 1e-3), g / max(sc_, 1e-3))
        v, T = binary_field(S["kind"], S["phi"], X.astype(f32), Y.astype(f32))
        col = bb_vec(T) * v[..., None]
        col = cv2.resize(col, (2 * half, 2 * half), interpolation=cv2.INTER_AREA)
        x0, y0 = int(round(cx)) - half, int(round(cy)) - half
        img[y0:y0 + 2 * half, x0:x0 + 2 * half] += col * S["surf"] * I_mul
        pad = 420; H, W = img.shape[:2]
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        if S["kind"] == "wuma":                                                   # elongated glow along the projected axis
            ax = math.sin(S["phi"]); ay = math.cos(S["phi"]) * math.cos(WUM["i"]); n = math.hypot(ax, ay) + 1e-6
            al = (dx * ax + dy * ay) / n; pp = (-dx * ay + dy * ax) / n
            d = np.sqrt((al / (1 + 0.9 * n)) ** 2 + pp ** 2) + 1e-3
        else:
            d = np.sqrt(dx * dx + dy * dy) + 1e-3
        Re = 2.5 * Rmul
        dd = np.maximum(d - Re, 0); sc = bbcolor(S["T"])
        gl = np.exp(-dd / 3.5) * 2.2 + np.exp(-dd / 22) * 0.55 + np.exp(-dd / 90) * 0.12
        reg = img[y0:y1, x0:x1]
        reg += (gl * S["glow"] * I_mul * 1.2)[..., None] * (0.3 + 0.7 * sc)
        self.spikes(reg, dx, dy, Re, S["spikes"] * I_mul, sc, t)

    # -------------------------------------------------------------------------------------------- loupe
    def loupe_content(self, t, lp, r, R):
        """HDR content of the magnifier (2r x 2r): true shapes from the same geometry as the main view"""
        g = np.arange(2 * r) + 0.5 - r
        XX, YY = np.meshgrid(g, g); XX, YY = XX.astype(f32), YY.astype(f32)
        k = R / LOUPE["R"]
        if lp["kind"] == "sirb":
            # Sirius B and Earth side by side at the same scale (R_B = 5,840 km, R_Earth = 6,371 km)
            pk = 46.0 * k / 5844.0
            rb, re_ = 5844.0 * pk, 6371.0 * pk
            bx, ex = -0.36 * R, 0.36 * R
            d = np.hypot(XX - bx, YY); mu = np.sqrt(np.clip(1 - (d / rb) ** 2, 0, 1))
            inside = smooth(rb + 0.8, rb - 0.8, d)
            cB = bbcolor(25000.0)
            col = (inside * (1 - 0.45 * (1 - mu)) * (5.0 + 0.4 * math.sin(t * 6)))[..., None] * (0.35 + 0.65 * cB)
            dd = np.maximum(d - rb, 0)
            col += ((np.exp(-dd / 6) * 1.6 + np.exp(-dd / 30) * 0.45 + np.exp(-dd / 110) * 0.10) * (1 + 0.1 * math.sin(t * 9)))[..., None] * (0.3 + 0.7 * cB)
            de = np.hypot(XX - ex, YY); ins = smooth(re_ + 0.8, re_ - 0.8, de)
            u = ((XX - ex) / re_); v = (YY / re_); z = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
            lon = (np.arctan2(u, z) / np.pi * 0.5 + 0.5 + t * 0.03) % 1.0; lat = np.clip(v * 0.5 + 0.5, 0, 0.999)
            tex = self.earth_tex[(lat * 127).astype(int), (lon * 255).astype(int)]
            land = smooth(0.25, 0.45, tex[..., 0]); cloud = smooth(0.55, 0.85, tex[..., 1])
            alb = np.array([0.02, 0.07, 0.30], f32) * (1 - land[..., None]) + np.array([0.10, 0.16, 0.05], f32) * land[..., None]
            alb = alb * (1 - cloud[..., None]) + 0.75 * cloud[..., None]
            lit = np.clip(-u * 0.9 + z * 0.45, 0, 1)                                    # lit from Sirius B's side
            col += (ins * lit)[..., None] * alb * 4.0 * (0.3 + 0.7 * cB) + (ins * np.exp(-((1 - z) / 0.08) ** 2) * lit * 0.4)[..., None] * np.array([0.3, 0.55, 1.0], f32)
            return col
        ss = 2; gs = (np.arange(2 * r * ss) + 0.5) / ss - r
        X, Y = np.meshgrid(gs / lp["scale"] / k, gs / lp["scale"] / k)
        v, T = binary_field(lp["kind"], lp["phi"], X.astype(f32), Y.astype(f32))
        if lp["kind"] == "wuma":
            rim = np.clip(1 - v / 0.95, 0, 1) * (v > 0)
            col = bb_vec(T) * v[..., None] * (1 - 0.45 * rim[..., None]) + (rim * v)[..., None] * np.array([0.55, 0.35, 1.0], f32)
        else:
            col = bb_vec(T) * v[..., None]
        col = cv2.resize(col.astype(f32), (2 * r, 2 * r), interpolation=cv2.INTER_AREA)
        surf = 6.0 if lp["kind"] == "alg" else 1.3
        out = col * surf
        glow = cv2.GaussianBlur(col, (0, 0), 7) * 1.2 + cv2.GaussianBlur(col, (0, 0), 26) * 0.9
        rr = np.hypot(XX, YY) / R; th = np.arctan2(YY, XX)
        if lp["kind"] == "wuma":                                                   # shared envelope + L2 outflow spiral
            ax = math.sin(lp["phi"]); ay = math.cos(lp["phi"]) * math.cos(WUM["i"])
            al = (XX * ax + YY * ay) / (math.hypot(ax, ay) + 1e-6); pp = (-XX * ay + YY * ax) / (math.hypot(ax, ay) + 1e-6)
            env = np.exp(-((al / (R * (0.42 + 0.2 * math.hypot(ax, ay)))) ** 2 + (pp / (R * 0.30)) ** 2) * 1.6)
            sw = np.exp(-((np.sin(2 * (th - lp["phi"]) + 7 * rr) + 1) * 2.2)) * np.exp(-((rr - 0.66) / 0.24) ** 2)
            out += (env * 0.9)[..., None] * np.array([0.9, 0.75, 1.25], f32) + (sw * 0.55)[..., None] * np.array([1.0, 0.70, 1.15], f32)
        else:                                                                      # Algol: B -> A gas stream (Roche-lobe overflow)
            (xa, ya, za), (xb, yb, zb) = algol_bodies(lp["phi"])
            sc = lp["scale"] * k
            P0 = np.array([xb, yb]) + (np.array([xa, ya]) - np.array([xb, yb])) * (ALG["RB"] / ALG["a"])
            P1 = np.array([xa, ya]); n = 60
            pts = [(P0 + (P1 - P0) * u + np.array([-(P1 - P0)[1], (P1 - P0)[0]]) * 0.25 * math.sin(math.pi * u)) * sc for u in np.linspace(0, 1, n)]
            m = np.zeros((2 * r, 2 * r), f32)
            for (x0_, y0_), (x1_, y1_) in zip(pts, pts[1:]):
                cv2.line(m, (int((x0_ + r) * 4), int((y0_ + r) * 4)), (int((x1_ + r) * 4), int((y1_ + r) * 4)), 1.0, 5, cv2.LINE_AA, shift=2)
            flick = 0.8 + 0.2 * math.sin(t * 7)
            m = cv2.GaussianBlur(m, (0, 0), 2.5) * flick
            front = 1.0 if zb < za else 0.6
            out += (m * 0.9 * front)[..., None] * np.array([1.0, 0.55, 0.25], f32)
        return out + glow * surf * 0.30

    def loupe(self, img, t, lp, alpha, bg):
        """big magnifier inset (deep-space backdrop, true shapes, glowing ring) + leader lines from the star"""
        if alpha <= 0.01: return
        cx, cy, R = LOUPE["cx"], LOUPE["cy"], LOUPE["R"] * (0.55 + 0.45 * back_out(alpha, 1.6))
        H, W = img.shape[:2]
        r = int(R) + 8; x0, y0 = int(cx) - r, int(cy) - r
        g = np.arange(2 * r) + 0.5 - r
        XX, YY = np.meshgrid(g, g); rr = np.hypot(XX, YY)
        inside = smooth(R + 0.8, R - 0.8, rr)[..., None]
        base = np.asarray(bg, f32) * 0.10 + np.array([0.004, 0.006, 0.018], f32) + (np.exp(-rr / R * 1.3) * 0.03)[..., None] * np.asarray(bg, f32) / max(float(lum(np.asarray(bg, f32))), 1e-3)
        st = self.loupe_stars[:2 * r, :2 * r]
        patch = base + st + self.loupe_content(t, lp, r, R)
        ring = np.exp(-((rr - R) / 2.4) ** 2)[..., None] * np.array([1.7, 1.55, 1.35], f32) + (np.exp(-np.maximum(rr - R, 0) / 14) * (rr > R) * 0.22)[..., None] * np.array([1.0, 0.85, 1.0], f32)
        reg = img[y0:y0 + 2 * r, x0:x0 + 2 * r]
        reg[:] = reg * (1 - inside * alpha) + patch * inside * alpha + ring * alpha
        sx, sy = lp["star"]; dx, dy = cx - sx, cy - sy; D = math.hypot(dx, dy)
        if D > R + 5:
            m = np.zeros((H, W), f32); base_a = math.atan2(dy, dx); off = math.asin(R / D)
            for sgn in (-1, 1):
                a = base_a + sgn * off; Lt = math.sqrt(D * D - R * R)
                ex, ey = sx + Lt * math.cos(a), sy + Lt * math.sin(a)
                bx, by = sx + 18 * math.cos(a), sy + 18 * math.sin(a)
                cv2.line(m, (int(bx * 4), int(by * 4)), (int(ex * 4), int(ey * 4)), 1.0, 2, cv2.LINE_AA, shift=2)
            m = cv2.GaussianBlur(m, (0, 0), 0.8)
            img += (m * alpha * 1.1)[..., None] * np.array([1.0, 0.95, 0.88], f32)
            ring2 = np.zeros((H, W), f32)
            cv2.circle(ring2, (int(sx * 4), int(sy * 4)), int(18 * 4), 1.0, 2, cv2.LINE_AA, shift=2)
            img += (cv2.GaussianBlur(ring2, (0, 0), 0.8) * alpha)[..., None] * np.array([1.0, 0.95, 0.88], f32)

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, t, lights, amb_col, amb, lamps, g):
        fg = self.fg; lawn = self.lawn[..., None]
        direct_l = np.zeros((self.H, self.W, 3), f32); direct_o = np.zeros(3, f32); rimc = np.zeros(3, f32)
        Emax = max([l.get("Esh", l["E"]) for l in lights] + [1e-6])
        for l in lights:
            E = l.get("Esh", l["E"])
            if E < 2e-3: continue
            c = (l["col"] / max(float(lum(l["col"])), 1e-4)) if "col" in l else light_col(l["T"])
            c = vivid(c, 1.25) * E
            if E > 0.04 * Emax and l["y"] < self.hz + 30:
                S = self.shadow(l["x"], l.get("el", 20.0))
                direct_l += c * (1 - 0.97 * S)[..., None]
            else:
                direct_l += c
            direct_o += c * 0.50; rimc += c
        out = self.alb * (amb_col * amb + direct_l * lawn + direct_o * (1 - lawn))
        out = out + self.rim[..., None] * rimc * 0.35
        out = out * np.array(g["tint"], f32)
        if g["con"] != 1.0 or g["sat"] != 1.0:
            y = lum(out)[..., None]
            out = (y + (out - y) * g["sat"]) * np.clip(y / 0.12, 0.05, 8) ** (g["con"] - 1)
        if lamps > 0.01: out = fg.lamps_light(out, lamps * 1.4, t)
        return np.maximum(out, 0)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        W, H = self.W, self.H; fg = self.fg
        cur, t0, t1 = star_at(t)
        prev = prev_of(t0)
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        Sc = state(cur, t)
        Sp = state(prev, t) if (prev and w < 1) else None
        pulse = 1 + 0.08 * math.sin(2 * math.pi * t / 1.6) + sum(0.5 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        # lights: crossfade old -> new
        lights = [dict(l, E=l["E"] * w, bI=l["bI"] * w) for l in Sc["lights"]]
        if Sp: lights += [dict(l, E=l["E"] * (1 - w), bI=l["bI"] * (1 - w) * 0.0) for l in Sp["lights"]]
        g = gmix(Sp["grade"], Sc["grade"], w) if Sp else Sc["grade"]
        amb = lerp(Sp["amb"], Sc["amb"], w) if Sp else Sc["amb"]
        expo = lerp(Sp["expo"], Sc["expo"], w) if Sp else Sc["expo"]
        lamps = lerp(Sp["lamps"], Sc["lamps"], w) if Sp else Sc["lamps"]
        # ---- sky
        sky, bm = self.sky(t, lights, g)
        bm = bm * (1 + 0.6 * col_u)
        ns = self.night_stars(t, g["stars"] * (1.0 if cur != "kep" else ramp(t, T_DSUN, K1)))
        if ns is not None: sky = sky + ns
        img = self.up(sky * (1 - 0.3 * col_u) + bm)
        amb_col = (sky[: sky.shape[0] // 2].reshape(-1, 3).mean(0) * 0.5 + sky[int(sky.shape[0] * 0.65)].mean(0) * 0.5)
        amb_col = amb_col / max(float(lum(amb_col)), 1e-4) * min(float(lum(amb_col)) * 3.0, 1.0)
        # ---- stars of the current system (bloom in after the swap, implode before the next)
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        Rmul = g_in; wob = 0.0; hot = 0.0
        if col_u > 0:
            if col_u < 0.45: Rmul *= 1 + 0.35 * ease(col_u / 0.45); wob = col_u / 0.45
            else: v = (col_u - 0.45) / 0.55; Rmul *= 1.35 * (1 - ease(v) ** 0.7) + 0.02; wob = 1 - v
            I_mul *= 1 + 4 * col_u ** 2; hot = 0.15 * col_u
        for D in Sc["draws"]:
            if D["kind"] == "disc":
                if D["surf"] <= 0 and D["glow"] <= 0.01: continue
                self.draw_disc(img, t, dict(D, Rp=max(D["Rp"] * Rmul, 0.3)), I_mul, wob, hot)
            else:
                self.draw_pair(img, t, D, I_mul, Rmul)
        # occlude stars behind the park (the sky is drawn under the plate)
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(t, lights, amb_col, amb, lamps, g) * light
        fgc = fgc + self.up(bm) * 0.04 * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- loupe (Algol / W UMa)
        if Sc.get("loupe"):
            la = ramp(t, t0 + 0.35, t0 + 0.75) * (1 - ramp(t, t1 - 0.45, t1 - 0.2))
            bgc = sky[int(min(LOUPE["cy"], 1200) / 2), int(LOUPE["cx"] / 2)]
            self.loupe(img, t, Sc["loupe"], la, bgc)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                ks = "sun" if k == "sun2" else k
                L0 = state(ks, ts + 0.01)["lights"][0]
                fc = (0.4 + 0.6 * bbcolor(L0["T"]))
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * (ease((u + 0.05) / 0.05))) * fc
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - L0["x"]) ** 2 + (self.yy - L0["y"]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        if T_WO0 < t < T_SUNBACK:
            v = ease((t - T_WO0) / (T_SUNBACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        self.overlay(out, t, cur, t0, Sc)
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
        W, H = self.W, self.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0, Sc):
        L = self.L; W = L.W
        I = INFO[cur]
        x, ys = W / 2, (300, 384, 440)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "sun" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.9, T_SUNBACK + 1.2) * (1 - ramp(t, DUR - 0.6, DUR - 0.2))
        if cur == "sun" and t < 1.0: a = ramp(t, 0.35, 0.7)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(I["name"]) < 12 else 1.12))
            rgba, _ = word_layer(I["name"], big, W * 0.92, fill=I["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, I["l2"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.06, display=True)
            hud_text(out, I["l3"], x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (235, 240, 250), a, 0.08, display=True)
            for lab, lx, ly, la in Sc.get("labels", []):
                if la > 0.05 and ly < 1420:
                    hud_text(out, lab, lx + 26, ly - 30, 34, "Black", (255, 255, 255), a * la, 0.0, display=True)
        lp = Sc.get("loupe")
        if lp and lp["kind"] == "sirb":
            t1 = star_at(t)[2]
            la = ramp(t, t0 + 0.55, t0 + 0.9) * (1 - ramp(t, t1 - 0.45, t1 - 0.2))
            if la > 0.01:
                cx, cy, R = LOUPE["cx"], LOUPE["cy"], LOUPE["R"]
                hud_text(out, "SIRIUS B", cx - 0.36 * R, cy + 0.42 * R, 30, "Black", (200, 225, 255), la, 0.08, display=True)
                hud_text(out, "EARTH", cx + 0.36 * R, cy + 0.42 * R, 30, "Black", (170, 220, 255), la, 0.08, display=True)
        if Sc.get("pointer") and a > 0.01:
            px, py = Sc["pointer"]; pr = 26 + 4 * math.sin(t * 5)
            ov = np.zeros_like(out[..., 0])
            cv2.circle(ov, (int(px * 4), int(py * 4)), int(pr * 4), 1.0, 2, cv2.LINE_AA, shift=2)
            ov = cv2.GaussianBlur(ov, (0, 0), 0.6)
            out[:] = out * (1 - ov[..., None] * a * 0.9) + ov[..., None] * a * 0.9 * np.array([0.85, 0.95, 1.0], f32)
        self.caps.draw(out, t)


def save(im, p):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            save(im, os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.W, sc.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(vertical, ranges):
    import subprocess
    sc = Scene(vertical); tag = "vert"
    W, H = sc.W, sc.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
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
        print("DUR", DUR, "HY", round(HY, 1), "F_PX", round(F_PX, 1))
        print({k: round(v, 2) for k, v in T_SW.items()}, "night", round(T_NIGHT0, 2), "sunback", round(T_SUNBACK, 2))
        for k, v in ANG.items(): print(k, v, "deg ->", round(rpx(v), 2), "px")
        print("algol px/Rsun", round(px_per_rsun(ALG["d_au"]), 3), "wuma px/Rsun", round(px_per_rsun(WUM["d_au"]), 3))
        for p in (-50, -30, -15, -5, 0, 15, 30): print("algol phase", p, round(binary_flux("alg", math.radians(p)), 3))
        for p in (0, 45, 90, 135, 180): print("wuma phase", p, round(binary_flux("wuma", math.radians(p)), 3))
        for tt in (K0, T_DSUN, T_DSHAD, K1):
            (xa, ya), (xb, yb) = kepler_pos(tt); print("kep t", round(tt, 2), "altA", round(alt_of(ya), 2), "altB", round(alt_of(yb), 2),
                                                       "XA", round(airmass(alt_of(ya)), 1), "XB", round(airmass(alt_of(yb)), 1))
        sys.exit()
    if sys.argv[1] == "patch":
        patch(True, [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(True, st)
