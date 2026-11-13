"""WHAT IF DEAD STARS REPLACED OUR SUN? -- one locked tripod shot of the park (A2_park), VFX spectacle style.
Stellar remnants placed where the Sun is (1 au), each at its true angular size and true visible brightness, the park
relit (and the eye-adapted exposure set) for each:
  Sun -> white dwarf (Sirius B-like, deep-blue twilight, frost) -> neutron star (starry noon, lensing)
      -> pulsar (lighthouse beams, slowed) -> magnetar (field lines, giant flare) -> black dwarf (frozen, dark)
      -> white-out -> Sun (loops)
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
from lib.sky import StarSky, SkyCam

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-dead-star-suns"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
# SOURCE px of A2_park.png (941x1672), as measured for ../betelgeuse-tonight: lamp heads + pole bases, lawn plane
LAMPS_SRC = [(193, 1198, 1325), (666, 1207, 1322), (816, 1113, 1323)]
LAWN_SRC = 1324
VAN_SRC = 1300
F_SRC = 1000.0
CAM_H = 1.3
FPS = 30
LEAD, TAIL = 0.25, 0.95

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    """time of the n-th caption word `cap` within a beat (all lines whose key is `key` or starts with `key_`)"""
    ws = [w for l in PL if l["key"] == key or l["key"].startswith(key + "_") for w in l["words"] if w["cap"] == cap]
    return ws[n]["t1" if end else "t0"]


# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["sun", "wd", "ns", "psr", "mag", "bd"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
T_SUNBACK = LN["end"]["start"] - 0.10
T_WO0 = T_SUNBACK - 0.85
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "sun2")]
COLLAPSE, BLOOM = 0.40, 0.60
T_DIM0 = wt("wd", "DAYLIGHT") - 0.1; T_DIM1 = wt("wd", "TWILIGHT", end=True)     # white dwarf: day fades to twilight
T_FREEZE = wt("wd", "FREEZES") - 0.25
T_NIGHT = wt("ns", "NOON")                                                        # neutron star: noon -> night
T_FLARE = wt("mag", "FLARE") - 0.05                                               # magnetar giant flare
T_STRIP = wt("mag", "STRIP")
PULSES = [wt("hook", "DIES"), wt("hook", "SUN"), wt("wd", "MASS"), wt("wd", "SIZE"), wt("wd", "FREEZES"), wt("ns", "NIGHT"),
          wt("psr", "700"), wt("mag", "MAGNETAR"), wt("bd", "DARK"), wt("bd", "ENOUGH"), wt("end", "DWARF")]


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




# ------------------------------------------------------------------------------------------------ the objects
F_PX = F_SRC * (1080 / 941)                                                # plate lens, ~80 deg vertical FOV
def rpx(ang_deg): return F_PX * math.tan(math.radians(ang_deg / 2))
ANG = dict(sun=0.533, wd=0.00447, ns=9.2e-6)                               # deg at 1 au: 1.39e6 km, 11,700 km, 24 km
POS = (598.0, 600.0)
HY = VAN_SRC * (1080 / 941) + (1920 - 1672 * (1080 / 941)) + 8           # true horizon row in the vertical frame
LOUPE = dict(cx=790.0, cy=1168.0, R=196.0)
THETA_E = 78.0                                                             # drawn Einstein radius, px (true: 48" = 0.27 px)

BEAMS = {
    "sun": "rainbow",
    "wd": [(0.55, 0.80, 1.0), (0.70, 0.55, 1.0), (0.85, 0.95, 1.0), (0.30, 0.95, 1.0)],
    "ns": [(0.55, 0.70, 1.0), (0.80, 0.60, 1.0), (0.40, 0.95, 1.0)],
    "mag": [(0.85, 0.45, 1.0), (0.55, 0.40, 1.0), (1.0, 0.55, 0.95), (0.45, 0.85, 1.0)],
}

INFO = {
    "sun": dict(name="OUR SUN", l2="1 SUN'S MASS · 1.4 MILLION KM WIDE", l3="ALIVE · 5,800 K", tc=(255, 226, 150)),
    "wd": dict(name="WHITE DWARF", l2="SUN'S MASS · EARTH'S SIZE", l3="1/400 OF OUR DAYLIGHT · EARTH −170 °C", tc=(175, 215, 255)),
    "ns": dict(name="NEUTRON STAR", l2="1.4 SUNS · 24 KM WIDE", l3="A TEASPOON: 2 BILLION TONNES", tc=(160, 190, 255)),
    "psr": dict(name="PULSAR", l2="A SPINNING NEUTRON STAR", l3="UP TO 716 TURNS PER SECOND", tc=(120, 235, 255)),
    "mag": dict(name="MAGNETAR", l2="FIELD ~1,000 TRILLION × EARTH'S", l3="2004 FLARE: FELT ACROSS THE GALAXY", tc=(215, 150, 255)),
    "bd": dict(name="BLACK DWARF", l2="SUN'S MASS · EARTH'S SIZE · COLD", l3="UNIVERSE: 13.8 BILLION YRS · NOT ENOUGH", tc=(200, 210, 235)),
    "sun_end": dict(name="OUR SUN", l2="1.4 MILLION KM WIDE · ALIVE", l3="WHITE DWARF IN ~8 BILLION YEARS", tc=(255, 226, 150)),
}

# ---- pulsar: beam axis at alpha from the spin axis; the spin axis is also alpha from the line of sight, so one beam
#      sweeps across us once per turn (a pulse). Screen coords: x right, y down, z towards the viewer.
PSR_ALPHA = math.radians(52.0)
PSR_REV = 0.55                                                             # turns per second as shown (real: 1-716 /s)
_b = math.radians(-62.0)
PSR_AX = np.array([math.sin(PSR_ALPHA) * math.cos(_b), math.sin(PSR_ALPHA) * math.sin(_b), math.cos(PSR_ALPHA)])
_e1 = np.cross(PSR_AX, [0.0, 0.0, 1.0]); _e1 /= np.linalg.norm(_e1); _e2 = np.cross(PSR_AX, _e1)
def psr_beams(t):
    """-> [(screen angle, projected length 0..1, z towards viewer)] for the two opposite beams"""
    w = 2 * math.pi * PSR_REV * (t - T_SW["psr"]) + 2.2
    b = PSR_AX * math.cos(PSR_ALPHA) + math.sin(PSR_ALPHA) * (_e1 * math.cos(w) + _e2 * math.sin(w))
    out = []
    for s in (1, -1):
        v = b * s; out.append((math.atan2(v[1], v[0]), math.hypot(v[0], v[1]), v[2]))
    return out


def psr_flash(t):
    if t < T_SW["psr"] - 0.2: return 0.0
    z = psr_beams(t)[0][2]
    return math.exp(-(1 - z) / 0.012)


# ---- magnetar: dipole field, magnetic axis 28 deg from the spin axis, real-time spin (SGR 1806-20: P = 7.56 s)
MAG_P = 7.56
def mag_axes(t):
    sp = np.array([0.18, -0.97, 0.12]); sp /= np.linalg.norm(sp)
    a = np.cross(sp, [0.0, 0.0, 1.0]); a /= np.linalg.norm(a); bb = np.cross(sp, a)
    w = 2 * math.pi * (t - T_SW["mag"]) / MAG_P + 0.6; tl = math.radians(28)
    m = sp * math.cos(tl) + math.sin(tl) * (a * math.cos(w) + bb * math.sin(w))
    e1 = np.cross(m, [0.0, 0.0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(m, e1)
    return m, e1, e2


def back_end():
    return INFO["sun_end"]


# per-beat sky + grade. zen/hor: sky (linear); low: optional horizon band; tint/con/sat: park grade; stars: starfield
G = {
    "sun": dict(zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), low=None, tint=(1.0, 1.0, 1.0), con=1.0, sat=1.0, stars=0.0, halo=0.0),
    "wd_day": dict(zen=(0.000, 0.16, 0.62), hor=(0.45, 0.85, 1.30), low=None, tint=(0.74, 0.92, 1.35), con=1.30, sat=1.10, stars=0.0, halo=1.0),
    "wd": dict(zen=(0.003, 0.008, 0.060), hor=(0.035, 0.070, 0.210), low=(0.06, 0.09, 0.26), tint=(0.50, 0.68, 1.30), con=1.05, sat=0.55, stars=0.75, halo=1.2),
    "night": dict(zen=(0.004, 0.009, 0.040), hor=(0.030, 0.052, 0.125), low=(0.05, 0.07, 0.16), tint=(0.55, 0.70, 1.25), con=1.05, sat=1.0, stars=1.0, halo=0.5),
    "psr": dict(zen=(0.008, 0.007, 0.050), hor=(0.040, 0.050, 0.150), low=(0.06, 0.07, 0.19), tint=(0.62, 0.74, 1.25), con=1.05, sat=1.05, stars=1.0, halo=0.6),
    "mag": dict(zen=(0.018, 0.004, 0.055), hor=(0.110, 0.030, 0.180), low=(0.17, 0.05, 0.24), tint=(0.85, 0.62, 1.30), con=1.08, sat=1.15, stars=0.85, halo=1.0),
    "mag_fl": dict(zen=(0.14, 0.015, 0.42), hor=(0.50, 0.10, 0.80), low=(0.65, 0.18, 0.90), tint=(1.10, 0.85, 1.40), con=1.15, sat=1.2, stars=0.0, halo=2.0),
    "bd": dict(zen=(0.003, 0.007, 0.036), hor=(0.020, 0.036, 0.100), low=(0.03, 0.05, 0.13), tint=(0.50, 0.66, 1.25), con=1.05, sat=0.9, stars=1.0, halo=0.0),
}
def gmix(a, b, w):
    return {k: (None if a[k] is None and b[k] is None else lerp(a[k] if a[k] is not None else b["hor"], b[k] if b[k] is not None else a["hor"], w))
            for k in a}


def state(key, t):
    """lights (for sky + park), draws, sky/grade, lamps, exposure, frost, loupe, pointer, special layers"""
    x, y = POS
    S = dict(lights=[], draws=[], grade=G["sun"], lamps=0.0, expo=1.0, loupe=None, amb=0.30, frost=0.0, pointer=None,
             lens=0.0, psr=0.0, field=0.0, flare=0.0)
    if key == "sun":
        S["lights"] = [dict(x=x, y=y, T=5772.0, E=1.0, beams="sun", bI=1.0, el=16.0)]
        S["draws"] = [dict(kind="disc", x=x, y=y, Rp=rpx(ANG["sun"]), T=5772.0, surf=40.0, glow=1.0, spikes=0.6, u=0.6)]
    elif key == "wd":
        # true visible light: 1/400 of the Sun's (M_V 11.3 vs 4.8): ~250 lux, a cold dim twilight from the swap on,
        # deepening further on "Daylight fades to twilight"
        n = 0.75 * ramp(t, T_SW["wd"], T_SW["wd"] + 1.1) + 0.25 * ramp(t, T_DIM0, T_DIM1)
        S["grade"] = gmix(G["wd_day"], G["wd"], n)
        S["lights"] = [dict(x=x, y=y, T=25000.0, E=1.0 * (1 - n) + 0.10 * n, beams="wd", bI=1.5 - 0.6 * n, el=16.0, halo=1.2)]
        S["draws"] = [dict(kind="disc", x=x, y=y, Rp=rpx(ANG["wd"]), T=25000.0, surf=60.0, glow=2.6 - 0.6 * n, spikes=1.8 - 0.4 * n, u=0.5)]
        S["amb"] = 0.20 - 0.08 * n; S["expo"] = 0.95 + 0.45 * n
        lo = ramp(t, T_SW["wd"] + 0.8, T_SW["wd"] + 2.2)                     # lamps flicker on in the gloom
        S["lamps"] = 0.85 * lo * (1.0 if lo > 0.97 else (0.5 + 0.5 * (noise1(t, 78, 13.0) > -0.1)))
        S["frost"] = ramp(t, T_FREEZE, T_FREEZE + 2.2)
        S["loupe"] = dict(kind="wd", star=(x, y))
    elif key == "ns":
        # a young neutron star in visible light: ~mag -11 from 1 au (RX J1856.5-3754 scaled), a point, no daylight
        n = ramp(t, T_NIGHT - 0.4, T_NIGHT + 0.6)
        S["grade"] = gmix(G["wd"], G["night"], n)
        S["lights"] = [dict(x=x, y=y, T=60000.0, E=0.16 * (1 - n) + 0.004 * n, col=np.array([0.80, 0.88, 1.15], f32), beams="ns",
                            bI=0.55, el=16.0, halo=0.6)]
        S["draws"] = [dict(kind="disc", x=x, y=y, Rp=0.3, T=60000.0, col=np.array([0.80, 0.88, 1.15], f32), surf=30.0, glow=0.6,
                           spikes=0.25, u=0.5)]
        S["amb"] = 0.14 * (1 - n) + 0.10 * n; S["expo"] = 1.5 + 0.2 * n; S["lamps"] = 0.85 + 0.15 * n
        S["frost"] = 1.0; S["pointer"] = (x, y); S["lens"] = 1.0
    elif key == "psr":
        fl = psr_flash(t)
        S["grade"] = G["psr"]
        S["lights"] = [dict(x=x, y=y, T=40000.0, E=0.004 + 0.28 * fl, col=np.array([0.70, 0.92, 1.25], f32), bI=0.0, el=16.0, halo=1.0)]
        S["draws"] = [dict(kind="disc", x=x, y=y, Rp=0.3, T=40000.0, col=np.array([0.75, 0.92, 1.2], f32), surf=30.0 + 200 * fl,
                           glow=0.9 + 1.6 * fl, spikes=0.6 + 1.6 * fl, u=0.5)]
        S["amb"] = 0.10; S["expo"] = 1.7; S["lamps"] = 1.0; S["frost"] = 1.0; S["psr"] = 1.0; S["flash"] = fl
    elif key == "mag":
        u = t - T_FLARE
        fl = 0.0 if u < 0 else math.exp(-u / 1.4)                          # the giant flare and its afterglow
        S["grade"] = gmix(G["mag"], G["mag_fl"], min(fl * 1.3, 1.0))
        S["lights"] = [dict(x=x, y=y, T=30000.0, E=0.006 + 0.8 * fl, col=np.array([0.95, 0.60, 1.40], f32), beams="mag",
                            bI=0.35 + 1.4 * fl, el=16.0, halo=1.2)]
        S["draws"] = [dict(kind="disc", x=x, y=y, Rp=0.3, T=30000.0, col=np.array([0.92, 0.75, 1.25], f32), surf=40.0 + 300 * fl,
                           glow=1.4 + 4.0 * fl, spikes=0.8 + 2.0 * fl, u=0.5)]
        S["amb"] = 0.12; S["expo"] = 1.6 - 0.7 * fl; S["lamps"] = 0.0 if u > 0.04 else 1.0                          # the flare knocks the lamps out
        S["frost"] = 1.0; S["field"] = 1.0; S["flare"] = fl
    elif key == "bd":
        S["grade"] = G["bd"]
        S["lights"] = [dict(x=x, y=y, T=3000.0, E=0.0, bI=0.0, el=16.0)]
        S["draws"] = [dict(kind="black", x=x, y=y)]
        S["amb"] = 0.10; S["expo"] = 1.75; S["lamps"] = 0.0; S["frost"] = 1.0; S["pointer"] = (x, y)
    return S


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.W, self.H = W, H
        self.fg = fg = Foreground(FG_PATH, L, lamps=list(LAMPS_SRC), hz_frac=0.84)
        self.hz = HY
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.clip((HY - yy) / HY, 0, 1)
        self.e = e
        self.k_hor = np.exp(-e / 0.33)[..., None].astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        # real-looking starfield (procedural Milky Way plate of ../lib/sky.py)
        self.cam = SkyCam(W, H, HY, F_PX)
        self.ss = StarSky()
        # lens maps around the neutron star (point lens, source at infinity: beta = theta - thetaE^2 / theta)
        x0, y0 = POS; R = 300; self.lw = (int(x0) - R, int(y0) - R, 2 * R)
        g = np.arange(2 * R, dtype=f32) + 0.5 - R
        LX, LY = np.meshgrid(g + (int(x0) - x0), g + (int(y0) - y0))
        r2 = LX * LX + LY * LY; rr = np.sqrt(r2) + 1e-3
        taper = smooth(R * 0.98, R * 0.55, rr)                               # fade the warp out before the window edge
        k = 1 - THETA_E ** 2 / np.maximum(r2, 4.0) * taper
        self.lmap = ((x0 + LX * k).astype(f32), (y0 + LY * k).astype(f32))
        self.lring = (np.exp(-((rr - THETA_E) / 1.6) ** 2) * 0.16 + np.exp(-((rr - THETA_E) / 10) ** 2) * 0.03).astype(f32)
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
        self.curtain = np.clip(fbm2((256, 256), 71, 2.2) * 0.6 + 0.5, 0, 2).astype(f32)
        self.shcache = {}
        self.caps = Captions(L, WORDS, emphasis={"DIES", "DEAD", "SUN", "WHITE", "DWARF", "EARTH'S", "TWILIGHT", "FREEZES", "NEUTRON",
                                                 "NIGHT", "PULSAR", "BEAMS", "700", "SECOND", "MAGNETAR", "FLARE", "STRIP", "ATMOSPHERE",
                                                 "BLACK", "COLD", "DARK", "NONE", "ENOUGH", "UNIVERSE"})
        L.cap_y = 880

    # -------------------------------------------------------------------------------------------- night sky
    def starfield(self, t, amt, lens=0.0):
        """full-res starfield radiance (slow drift so the lensed arcs move); lensed around the neutron star"""
        if amt <= 0.01: return None
        st = self.ss.render(self.cam, t, cx=self.ss.plate.shape[1] * 0.47, cy=self.ss.plate.shape[0] * 0.43, rot=-18.0 + 0.35 * t,
                            gain=1.0, twinkle=0.6, plate_gain=0.75, star_gain=1.2)
        if lens > 0.01:
            x0, y0, n = self.lw
            win = cv2.remap(st, self.lmap[0], self.lmap[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            win = win + (self.lring * (0.6 + 0.4 * math.sin(t * 3)))[..., None] * np.array([0.55, 0.70, 1.0], f32)
            reg = st[y0:y0 + n, x0:x0 + n]
            reg[:] = reg * (1 - lens) + win * lens
        return st * amt

    # -------------------------------------------------------------------------------------------- pulsar beams
    def psr_layer(self, t, amt):
        """two lighthouse beams from the pulsar (half-res HDR), slowed down; the near beam brightens as it sweeps at us"""
        x0, y0 = POS; dx = self.hx - x0; dy = self.hy - y0; d = np.sqrt(dx * dx + dy * dy) + 1e-3; ph = np.arctan2(dy, dx)
        acc = np.zeros(d.shape + (3,), f32)
        for i, (ang, ln, z) in enumerate(psr_beams(t)):
            dp = (ph - ang + np.pi) % (2 * np.pi) - np.pi
            open_ = 0.075 + 0.12 * (1 - ln) ** 2 + 0.03 * max(z, 0)               # foreshortened cone looks wider
            core = np.exp(-(dp / (open_ * 0.35)) ** 2); halo = np.exp(-(dp / open_) ** 2)
            reach = 120 + 1900 * ln ** 1.5
            rad = np.exp(-d / reach) * (1 - np.exp(-d / 20))
            fl = 1 + 3.0 * max(z, 0) ** 6
            c_core = np.array([0.75, 0.95, 1.25], f32); c_halo = np.array([0.35, 0.55, 1.25], f32) if i == 0 else np.array([0.75, 0.35, 1.20], f32)
            wav = 0.8 + 0.2 * np.sin(d / 18 - t * 30)                             # streaming texture along the beam
            acc += (core * rad * wav * 3.0 * fl)[..., None] * c_core + (halo * rad * 1.6 * fl)[..., None] * c_halo
        return acc * amt

    # -------------------------------------------------------------------------------------------- magnetar field
    def field_layer(self, t, amt, flare):
        """glowing dipole field lines (3-D, spinning with the real 7.56 s period) + particles streaming along them"""
        x0, y0 = POS; hw, hh = self.W // 2, self.H // 2
        m, e1, e2 = mag_axes(t)
        lines = np.zeros((hh, hw), f32); dots = np.zeros((hh, hw), f32); hot = np.zeros((hh, hw), f32)
        th = np.linspace(0.05, math.pi - 0.05, 90)
        boost = 1 + 0.8 * flare
        for li, Lr in enumerate((60, 105, 165, 245, 345, 470, 620)):
            Lr = Lr * (1 + 0.25 * flare)
            for k in range(8):
                ph = k * math.pi / 4 + 0.2 * li
                r = Lr * np.sin(th) ** 2
                P = (np.outer(r * np.sin(th) * math.cos(ph), e1) + np.outer(r * np.sin(th) * math.sin(ph), e2) + np.outer(r * np.cos(th), m))
                sx = (x0 + P[:, 0]) / 2; sy = (y0 + P[:, 1]) / 2
                front = 0.55 + 0.45 * np.clip(P[:, 2] / (Lr + 1e-3) * 2 + 0.5, 0, 1)
                pts = np.stack([sx * 8, sy * 8], 1).astype(np.int32)
                tgt = lines if li < 5 else hot
                for j in range(len(pts) - 1):
                    if 0 < sy[j] < hh * 0.62 or 0 < sy[j + 1] < hh * 0.62:
                        cv2.line(tgt, tuple(map(int, pts[j])), tuple(map(int, pts[j + 1])), float(front[j]), 1, cv2.LINE_AA, shift=3)
                # particles streaming pole to pole
                for q in range(3):
                    u = ((t * 0.35 + q / 3 + k * 0.13 + li * 0.07) % 1.0)
                    j = int(u * (len(th) - 1))
                    if 0 < sy[j] < hh * 0.62 and 0 < sx[j] < hw:
                        dots[int(sy[j]), int(sx[j])] += 1.0 * front[j]
        col_in = np.array([0.55, 0.45, 1.25], f32); col_out = np.array([1.10, 0.40, 1.00], f32); col_d = np.array([0.75, 0.95, 1.25], f32)
        out = (cv2.GaussianBlur(lines, (0, 0), 0.7) * 1.4 + cv2.GaussianBlur(lines, (0, 0), 4.0) * 0.9)[..., None] * col_in
        out += (cv2.GaussianBlur(hot, (0, 0), 0.7) * 1.2 + cv2.GaussianBlur(hot, (0, 0), 5.0) * 0.8)[..., None] * col_out
        out += (cv2.GaussianBlur(dots, (0, 0), 1.0) * 6 + cv2.GaussianBlur(dots, (0, 0), 3.5) * 2)[..., None] * col_d
        fade = np.clip((HY / 2 - self.hy) / 40, 0, 1)[..., None]
        return out * amt * boost * 1.1 * fade

    # -------------------------------------------------------------------------------------------- loupe
    def loupe_content(self, t, lp, r, R):
        """white dwarf and Earth side by side at the same scale (R_WD = 5,840 km, R_Earth = 6,371 km)"""
        g = np.arange(2 * r) + 0.5 - r
        XX, YY = np.meshgrid(g, g); XX, YY = XX.astype(f32), YY.astype(f32)
        k = R / LOUPE["R"]
        pk = 46.0 * k / 5844.0
        rb, re_ = 5844.0 * pk, 6371.0 * pk
        bx, ex = -0.42 * R, 0.42 * R
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
        lit = np.clip(-u * 0.9 + z * 0.45, 0, 1)
        col += (ins * lit)[..., None] * alb * 4.0 * (0.3 + 0.7 * cB) + (ins * np.exp(-((1 - z) / 0.08) ** 2) * lit * 0.4)[..., None] * np.array([0.3, 0.55, 1.0], f32)
        return col

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
        mixk = lambda k: lerp(Sp[k], Sc[k], w) if Sp else Sc[k]
        lights = [dict(l, E=l["E"] * w, bI=l["bI"] * w) for l in Sc["lights"]]
        if Sp: lights += [dict(l, E=l["E"] * (1 - w), bI=0.0) for l in Sp["lights"]]
        g = gmix(Sp["grade"], Sc["grade"], w) if Sp else Sc["grade"]
        amb, expo, lamps, frost = mixk("amb"), mixk("expo"), mixk("lamps"), mixk("frost")
        lens, psr, field, flare = Sc["lens"] * w, Sc["psr"] * w, Sc["field"] * w, Sc["flare"]
        # ---- sky
        sky, bm = self.sky(t, lights, g)
        bm = bm * (1 + 0.6 * col_u)
        if psr > 0.01: bm = bm + self.psr_layer(t, psr) * (1 - 0.7 * col_u)
        if field > 0.01: bm = bm + self.field_layer(t, field * (1 - 0.6 * col_u), flare)
        if flare > 0.01:                                                   # the atmosphere lit and blown off, violet curtains
            u = t - T_FLARE
            cy = (np.arange(H // 2, dtype=f32)[:, None] * 2 / 256.0 + u * 0.9) % 1.0
            cur_ = self.curtain[(cy * 255).astype(int), (np.arange(W // 2)[None, :] * 2 % 256)]
            vv = np.clip((HY - self.hy) / HY, 0, 1)
            bm = bm + (cur_ ** 2 * vv * flare * 1.0)[..., None] * np.array([0.80, 0.18, 1.30], f32)
        img = self.up(sky * (1 - 0.3 * col_u) + bm)
        st = self.starfield(t, g["stars"], lens)
        if st is not None: img = img + st
        amb_col = (sky[: sky.shape[0] // 2].reshape(-1, 3).mean(0) * 0.5 + sky[int(sky.shape[0] * 0.65)].mean(0) * 0.5)
        amb_col = amb_col / max(float(lum(amb_col)), 1e-4) * min(float(lum(amb_col)) * 3.0, 1.0)
        amb_col = np.maximum(amb_col, np.array([0.02, 0.03, 0.08], f32))
        # ---- the object (bloom in after the swap, implode before the next)
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        Rmul = g_in; wob = 0.0; hot = 0.0
        if col_u > 0:
            if col_u < 0.45: Rmul *= 1 + 0.35 * ease(col_u / 0.45); wob = col_u / 0.45
            else: v = (col_u - 0.45) / 0.55; Rmul *= 1.35 * (1 - ease(v) ** 0.7) + 0.02; wob = 1 - v
            I_mul *= 1 + 4 * col_u ** 2; hot = 0.15 * col_u
        for D in Sc["draws"]:
            if D["kind"] == "disc":
                self.draw_disc(img, t, dict(D, Rp=max(D["Rp"] * Rmul, 0.03)), I_mul, wob, hot)
            elif D["kind"] == "black":                                     # the black dwarf: a dark point hiding the stars
                d = np.sqrt((self.xx[560:640, 558:638] + 0.5 - D["x"]) ** 2 + (self.yy[560:640, 558:638] + 0.5 - D["y"]) ** 2)
                Rb = 6.0 * min(max(u_in, 0), 1) ** 0.5
                img[560:640, 558:638] *= (1 - smooth(Rb + 1.0, Rb - 1.0, d))[..., None]
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(t, lights, amb_col, amb, 0.0, g) * light
        if frost > 0.01:                                                   # frost on the lawn (light touch on the trees)
            fr = fg.frost(fgc, frost, t, level=0.35); m = (self.lawn * 0.85 + 0.15)[..., None]
            fgc = fgc * (1 - m) + fr * m
        if lamps > 0.01: fgc = fg.lamps_light(fgc, lamps * 1.4, t)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        # ---- loupe (white dwarf vs Earth)
        if Sc.get("loupe"):
            la = ramp(t, wt("wd", "SUN'S") - 0.1, wt("wd", "SUN'S") + 0.3) * (1 - ramp(t, T_DIM0 + 0.2, T_DIM0 + 0.5))
            bgc = sky[int(min(LOUPE["cy"], 1200) / 2), int(LOUPE["cx"] / 2)]
            self.loupe(img, t, Sc["loupe"], la, bgc)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                ks = "sun" if k == "sun2" else k
                L0 = state(ks, ts + 0.01)["lights"][0]
                fc = (0.4 + 0.6 * bbcolor(max(L0["T"], 6000.0)))
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * (ease((u + 0.05) / 0.05))) * fc
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - L0["x"]) ** 2 + (self.yy - L0["y"]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        # ---- magnetar giant flare: white-violet chromatic flash + double shockwave
        u = t - T_FLARE
        if cur == "mag" and -0.05 < u < 2.0:
            img += (16.0 * math.exp(-max(u, 0) / 0.07) * ease((u + 0.05) / 0.05) + 0.5 * math.exp(-max(u, 0) / 0.35)) * np.array([1.0, 0.82, 1.25], f32)
            dd = np.sqrt((self.xx - POS[0]) ** 2 + (self.yy - POS[1]) ** 2)
            for k_, (sp, cc) in enumerate(((3000, (1.2, 0.5, 1.6)), (1700, (0.5, 0.9, 1.6)))):
                R = sp * (max(u, 0) / 2.0) ** 0.55; wdt = 25 + 70 * u
                for ch, off in ((0, 14), (1, 0), (2, -14)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 3.0 * cc[ch] * math.exp(-max(u, 0) / 0.7)
        # ---- pulsar: each pass of the beam across us flashes the whole frame (cyan-white)
        if psr > 0.01:
            img += (Sc.get("flash", 0.0) * 0.30 * psr) * np.array([0.6, 0.85, 1.2], f32)
        if T_WO0 < t < T_SUNBACK:
            v = ease((t - T_WO0) / (T_SUNBACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.16)
        self.overlay(out, t, cur, t0, Sc)
        return out

    def overlay(self, out, t, cur, t0, Sc):
        L = self.L; W = L.W
        I = INFO["sun_end"] if (cur == "sun" and t > T_SUNBACK) else INFO[cur]
        x, ys = W / 2, (300, 384, 440)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "sun" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.5, T_SUNBACK + 0.8) * (1 - ramp(t, DUR - 0.5, DUR - 0.15))
        if cur == "sun" and t < 1.0: a = ramp(t, 0.35, 0.7)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.45 if len(I["name"]) < 12 else 1.25))
            rgba, _ = word_layer(I["name"], big, W * 0.92, fill=I["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, I["l2"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.06, display=True)
            hud_text(out, I["l3"], x, ys[2] + dy, int(L.hud_size * 0.48), "Bold", (235, 240, 250), a, 0.08, display=True)
        if Sc.get("loupe"):
            la = ramp(t, wt("wd", "SUN'S") + 0.1, wt("wd", "SUN'S") + 0.4) * (1 - ramp(t, T_DIM0 + 0.2, T_DIM0 + 0.5))
            if la > 0.01:
                cx, cy, R = LOUPE["cx"], LOUPE["cy"], LOUPE["R"]
                hud_text(out, "WHITE DWARF", cx - 0.42 * R, cy + 0.42 * R, 23, "Black", (200, 225, 255), la, 0.06, display=True)
                hud_text(out, "EARTH", cx + 0.42 * R, cy + 0.42 * R, 23, "Black", (170, 220, 255), la, 0.08, display=True)
        if Sc.get("pointer"):
            pa = ramp(t, t0 + 0.4, t0 + 0.7) * (1 - ramp(t, (nxt[0] if nxt else 1e9) - 0.35, (nxt[0] if nxt else 1e9) - 0.15))
            if pa > 0.01:
                px, py = Sc["pointer"]; pr = (THETA_E + 22 if cur == "ns" else 30) + 4 * math.sin(t * 5)
                ov = np.zeros_like(out[..., 0])
                cv2.circle(ov, (int(px * 4), int(py * 4)), int(pr * 4), 1.0, 2, cv2.LINE_AA, shift=2)
                for k in range(4):                                         # four short ticks pointing in
                    an = k * math.pi / 2 + math.pi / 4
                    p0 = (int((px + math.cos(an) * (pr + 6)) * 4), int((py + math.sin(an) * (pr + 6)) * 4))
                    p1 = (int((px + math.cos(an) * (pr + 22)) * 4), int((py + math.sin(an) * (pr + 22)) * 4))
                    cv2.line(ov, p0, p1, 1.0, 3, cv2.LINE_AA, shift=2)
                ov = cv2.GaussianBlur(ov, (0, 0), 0.6)
                col = np.array([0.85, 0.95, 1.0], f32)
                out[:] = out * (1 - ov[..., None] * pa * 0.9) + ov[..., None] * pa * 0.9 * col
        self.caps.draw(out, t)

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
        print({k: round(v, 2) for k, v in T_SW.items()}, "dim", round(T_DIM0, 2), round(T_DIM1, 2), "freeze", round(T_FREEZE, 2),
              "night", round(T_NIGHT, 2), "flare", round(T_FLARE, 2), "wo", round(T_WO0, 2), "sunback", round(T_SUNBACK, 2))
        for k, v in ANG.items(): print(k, v, "deg ->", round(rpx(v), 4), "px")
        sys.exit()
    if sys.argv[1] == "patch":
        patch(True, [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(True, st)
