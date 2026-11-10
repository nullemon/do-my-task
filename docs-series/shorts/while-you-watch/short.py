"""EVERYTHING THAT HAPPENS IN SPACE WHILE YOU WATCH THIS SHORT -- vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the user's valley plate (B_valley.png), facing WSW (az 245) from 34 deg N on a
November evening, golden hour -> dusk. The real sky (HYG stars, the vivid Milky Way with its core low in the SW) turns
slowly about the real pole while the stylised big Sun sinks onto the ridge.
Live counters tick for the Short's real elapsed time (value = rate x t, t = frame time from 0):
  orbit (29.78 km/s), hydrogen fused (600 Mt/s), meteoric dust (~0.5 kg/s), galactic orbit (230 km/s),
  motion vs the CMB (370 km/s), stars born (~5,000/s), supernovae (~30/s), sunlight that left at 0:00 (c).
Each counter pops in as a big featured card (flash + chromatic shockwave), then flies into the stack at the top.
Sky VFX: pulsing Sun with rainbow beams and fusion rings, the ecliptic with flowing chevrons, meteors, speed lines
radiating from the real direction of our galactic motion (Cygnus), star-birth sparkles along the Milky Way, supernova
flashes in distant galaxies, golden light wavefronts; white-out at the end = white-out at the start (loops).
Built on docs-series/shorts/lib (read-only). Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
  /home/user/ttsenv/bin/python short.py info                   timeline + counter end values
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image, ImageDraw
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, font
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import eq_vec, eq2hor, Lens, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S12-while-you-watch"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.15
AZ0 = 245.0                                            # camera azimuth: WSW, where the November Sun sets at 34 N

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
NFR = int(round(DUR * FPS))
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]

# ------------------------------------------------------------------------------------------------- rates (README)
V_ORBIT = 29.78            # km/s   Earth's mean orbital speed
H_FUSED = 6.0e8            # t/s    hydrogen fused in the Sun (L / (0.0071 c^2) = 6.0e11 kg/s)
E_MASS = 4.26e6            # t/s    mass converted to energy (L / c^2 = 3.828e26 / 8.988e16 kg/s)
DUST = 0.5                 # kg/s   meteoric material reaching Earth (~43 t/day; estimates 5-40 kt/yr)
V_GAL = 230.0              # km/s   Sun's orbital speed around the Galactic centre
V_CMB = 370.0              # km/s   Sun's speed relative to the CMB (369.8 km/s)
STARS = 5000.0             # /s     stars born in the observable universe (order of magnitude)
SN = 30.0                  # /s     supernovae in the observable universe (order of magnitude)
C_KM = 299792.458          # km/s
AU_S = 499.005             # s      light time Sun -> Earth (1 au / c)

# ------------------------------------------------------------------------------------------------- timeline
T_ORB = 0.45                                           # the orbit counter is there from the start (hook)
T_SUN = wt("sun", "FUSES") - 0.1
T_DUST = wt("dust", "½ KILO") - 0.15
T_GAL = wt("gal", "GALAXY") - 0.1
T_CMB = wt("gal", "COSMOS") - 0.1
T_STARS = wt("stars", "THOUSANDS") - 0.1
T_SN = wt("stars", "30") - 0.1
T_EXPLODE = wt("stars", "EXPLODE")
T_LIGHT = wt("light", "SUNLIGHT") - 0.1
T_END = LN["end"]["start"] - 0.05
T_WO = DUR - 0.80                                      # white-out ramp into the loop point

CYAN, GOLD, GREEN, VIOLET, MAGENTA, PINK, ICE, SUNY = ((0.30, 0.85, 1.0), (1.0, 0.70, 0.20), (0.40, 1.0, 0.45), (0.68, 0.50, 1.0),
                                                       (1.0, 0.35, 0.85), (1.0, 0.50, 0.70), (0.60, 0.82, 1.0), (1.0, 0.88, 0.35))


def fmt_int(x): return f"{int(x):,}"


# key, appear time, label, value(t), featured sub-line, colour
COUNTERS = [
    ("orbit", T_ORB, "EARTH'S ORBIT · 29.8 KM/S", lambda t: f"{fmt_int(V_ORBIT * t)} KM", "YOU'VE TRAVELLED AROUND THE SUN", CYAN),
    ("sun", T_SUN, "HYDROGEN FUSED BY THE SUN", lambda t: f"{H_FUSED * t / 1e9:.2f} BN TONNES",
     "~600 MILLION T/S · 4.3 MILLION T/S BECOME ENERGY", GOLD),
    ("dust", T_DUST, "SPACE DUST LANDED · ~0.5 KG/S", lambda t: f"≈ {DUST * t:.1f} KG", "TINY METEORS, ALL OVER EARTH", GREEN),
    ("gal", T_GAL, "AROUND THE GALAXY · 230 KM/S", lambda t: f"{fmt_int(V_GAL * t)} KM", "OUR SOLAR SYSTEM'S ORBIT", VIOLET),
    ("cmb", T_CMB, "THROUGH THE COSMOS · 370 KM/S", lambda t: f"{fmt_int(V_CMB * t)} KM", "RELATIVE TO THE BIG BANG'S AFTERGLOW", MAGENTA),
    ("stars", T_STARS, "STARS BORN · ~5,000/S", lambda t: f"≈ {fmt_int(round(STARS * t, -3))}", "ACROSS THE OBSERVABLE UNIVERSE", PINK),
    ("sn", T_SN, "STARS EXPLODED · ~30/S", lambda t: f"≈ {fmt_int(round(SN * t, -1))}", "SUPERNOVAE IN DISTANT GALAXIES", ICE),
    ("light", T_LIGHT, "SUNLIGHT FROM 0:00 · ON ITS WAY", lambda t: f"{C_KM * t / 1e6:.1f}M KM · {100 * t / AU_S:.0f}%",
     "THE TRIP TAKES 8 MIN 19 S", SUNY),
]
FEAT_END = {c[0]: (COUNTERS[i + 1][1] if i + 1 < len(COUNTERS) else T_END) for i, c in enumerate(COUNTERS)}
FLY = 0.35
MAXROWS = 5
ROWLAB = dict(orbit="EARTH'S ORBIT", sun="SUN: H FUSED", dust="SPACE DUST", gal="AROUND GALAXY", cmb="THROUGH COSMOS",
              stars="STARS BORN", sn="SUPERNOVAE", light="SUNLIGHT SENT")
APPEAR = [c[1] for c in COUNTERS]


def white_level(t):
    """loop flash: white-out into the last frame, the same white decaying from the first frame"""
    a = ramp(t, T_WO, DUR - 1.0 / FPS) ** 2.2
    b = math.exp(-t / 0.10) if t < 0.6 else 0.0
    return max(a, b)


def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def bv_temp(ci): return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


# speed-line drive: S(t) and its integral (distance travelled by the streaks)
def speed_drive(t):
    s = 0.0
    s += ramp(t, T_GAL - 0.6, T_GAL + 0.5) * (1 - 0.65 * ramp(t, T_CMB + 2.2, T_CMB + 4.0))
    s += 1.0 * ramp(t, T_CMB - 0.2, T_CMB + 0.4) * (1 - ramp(t, T_CMB + 1.6, T_CMB + 3.5))
    s += 1.2 * ramp(t, T_WO - 0.6, DUR)
    return s
_ts = np.arange(0, DUR + 0.5, 1 / 240.0)
_S_CUM = np.cumsum([speed_drive(x) for x in _ts]) / 240.0
def speed_dist(t): return float(np.interp(t, _ts, _S_CUM))


# ------------------------------------------------------------------------------------------------- galaxy sprite
def spiral_sprite(S=160, seed=31, incl=0.45):
    """small spiral galaxy (bulge, log-spiral arms, dust lanes, pink knots), inclined; major axis along x"""
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S].astype(f32)
    u = (xx - S / 2) / (0.40 * S); v = (yy - S / 2) / (0.40 * S) / incl
    rho = np.sqrt(u * u + v * v) + 1e-4; phi = np.arctan2(v, u)
    k = 1 / math.tan(math.radians(r.uniform(12, 22)))
    arm = (0.5 + 0.5 * np.cos(2 * (phi - np.log(rho) * k))) ** 2.2
    n = cv2.resize(fbm2((64, 64), seed, 2.2), (S, S), interpolation=cv2.INTER_CUBIC)
    disk = np.exp(-rho / 0.32) * (0.30 + 1.0 * arm) * np.clip(1 + 0.35 * n, 0.3, 2) * smooth(1.3, 0.85, rho)
    bulge = np.exp(-rho / 0.05) * 6.0 + np.exp(-rho / 0.14) * 1.4
    w = np.clip(rho / 0.7, 0, 1)[..., None]
    dcol = np.array([1.0, 0.78, 0.50], f32) * (1 - w) + np.array([0.50, 0.70, 1.0], f32) * w
    img = disk[..., None] * dcol + bulge[..., None] * np.array([1.0, 0.85, 0.62], f32)
    acc = np.zeros((S, S), f32)
    for _ in range(90):
        rr = r.uniform(0.35, 1.0); ph = r.uniform(0, 2 * np.pi); ph = ph - (ph % np.pi) + np.log(rr) * k + r.normal(0, 0.12)
        x = S / 2 + 0.40 * S * rr * math.cos(ph); y = S / 2 + 0.40 * S * rr * math.sin(ph) * incl
        if 0 <= int(x) < S and 0 <= int(y) < S: acc[int(y), int(x)] += r.uniform(0.3, 1.0)
    img += (cv2.GaussianBlur(acc, (0, 0), 1.0) * 5)[..., None] * np.array([1.0, 0.35, 0.65], f32)
    img = cv2.GaussianBlur(img, (0, 0), 0.7)
    edge = smooth(S / 2, S / 2 - 12, np.sqrt((xx - S / 2) ** 2 + ((yy - S / 2) * 1.5) ** 2))
    return (img * edge[..., None]).astype(f32)


# ------------------------------------------------------------------------------------------------- text
def text_img(txt, size, wt="Black"):
    """-> (alpha mask float, width) with tabular figures (digits don't jitter while counting)"""
    f = font(size, wt, True)
    w = f.getlength(txt, features=["tnum"]); asc, desc = f.getmetrics(); pad = int(size * 0.9) + 4
    m = Image.new("L", (int(w + 2 * pad), int(asc + desc + 2 * pad)), 0)
    ImageDraw.Draw(m).text((pad, pad), txt, font=f, fill=255, features=["tnum"])
    return np.asarray(m, f32) / 255.0, w, pad


def glow_put(dst, txt, cx, cy, size, col, alpha, anchor="c", wt="Black", white=0.55, glow=1.0, track=0.0, crisp=False):
    """glowing coloured text on the sRGB frame: soft dark backing, coloured halo, white-hot fill with a coloured edge"""
    if alpha <= 0.003: return
    if track > 0: txt = " ".join(txt)
    m, w, pad = text_img(txt, size, wt)
    h, W_ = m.shape
    if anchor == "l": cx = cx + w / 2
    elif anchor == "r": cx = cx - w / 2
    x0, y0 = int(round(cx - W_ / 2)), int(round(cy - h / 2))
    H, Wd = dst.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(Wd, x0 + W_), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    col = np.array(col, f32)
    ms = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=max(1, int(size * 0.035)))
    sh = cv2.GaussianBlur(ms, (0, 0), size * 0.12)
    halo = cv2.GaussianBlur(ms, (0, 0), size * 0.18) * 0.8 + cv2.GaussianBlur(ms, (0, 0), size * 0.5) * 0.45
    reg = dst[ya:yb, xa:xb]
    reg *= (1 - 0.55 * sh[sl] * alpha)[..., None]
    reg += halo[sl][..., None] * col * 0.75 * glow * alpha
    fill = col * (1 - white) + white
    a_e = ms[sl][..., None] * alpha; a_f = m[sl][..., None] * alpha
    reg[:] = reg * (1 - a_e) + col * 0.85 * a_e
    reg[:] = reg * (1 - a_f) + fill * a_f
    dst[ya:yb, xa:xb] = np.clip(reg, 0, 1)
    return w


def crisp_put(dst, txt, cx, cy, size, col, alpha, anchor="c", wt="Black"):
    """solid, readable counter text: saturated fill with a light top gradient, dark outline, soft drop shadow and only
    a subtle coloured outer halo (like the orange captions)"""
    if alpha <= 0.003: return
    m, w, pad = text_img(txt, size, wt)
    h, W_ = m.shape
    if anchor == "l": cx = cx + w / 2
    elif anchor == "r": cx = cx - w / 2
    x0, y0 = int(round(cx - W_ / 2)), int(round(cy - h / 2))
    H, Wd = dst.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(Wd, x0 + W_), min(H, y0 + h)
    if xb <= xa or yb <= ya: return
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    col = np.array(col, f32)
    sw = max(2, int(round(size * 0.075)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * sw + 1, 2 * sw + 1))
    ms = cv2.dilate(m, k)
    off = max(1, int(size * 0.05))
    shd = np.zeros_like(ms); shd[off:, off // 2:] = ms[:-off, :ms.shape[1] - off // 2]
    shd = cv2.GaussianBlur(shd, (0, 0), size * 0.10)
    halo = cv2.GaussianBlur(ms, (0, 0), size * 0.30)
    reg = dst[ya:yb, xa:xb]
    reg += halo[sl][..., None] * col * 0.28 * alpha
    reg *= (1 - 0.70 * shd[sl] * alpha)[..., None]
    a_e = ms[sl][..., None] * alpha
    reg[:] = reg * (1 - a_e) + np.array([0.06, 0.04, 0.10], f32) * a_e
    gy = np.linspace(1.0, 0.0, h, dtype=f32)[sl[0]][:, None, None]
    fill = np.clip(col * (0.88 + 0.12 * gy) + (1 - col) * 0.22 * gy, 0, 1)
    a_f = m[sl][..., None] * alpha
    reg[:] = reg * (1 - a_f) + fill * a_f
    dst[ya:yb, xa:xb] = np.clip(reg, 0, 1)
    return w


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.84)
        self.hz = fg.horizon
        self.lens = Lens(1080, 1920, AZ0, 56.0, 700.0, self.hz + 10) if vertical else Lens(1920, 1080, AZ0, 52.0, 560.0, self.hz + 10)
        if vertical: L.cap_y = 1010
        else: L.cap_y = 780; L.cap_size = 100
        self.caps = Captions(L, WORDS, emphasis={"35", "1,000 KM", "MOVING", "30 KM", "600 MILLION", "HYDROGEN", "½ KILO", "DUST",
                                                 "GALAXY", "230 KM", "COSMOS", "370", "THOUSANDS", "30", "EXPLODE", "SUNLIGHT",
                                                 "PLAY", "HERE"})
        self.rays = self.lens.rays(1)
        alt = np.arcsin(np.clip(self.rays[..., 2], -1, 1)).astype(f32)
        self.alt = alt
        e = np.clip(alt / (np.pi / 2), 0, 1); self.e = e
        self.above = smooth(-0.01, 0.04, alt).astype(f32)[..., None]
        hh, hw = H // 2, W // 2
        self.hy, self.hx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(f32)
        # --- the Sun: real azimuth ~245 deg; altitude sinks from ~5.3 deg to sit half behind the ridge at the end
        col = int(np.clip(W / 2, 0, W - 1))
        ridge_y = float(np.min(fg.skyline[col - 40:col + 40]))
        self.sun_r = 34.0 if vertical else 28.0
        self.sun_y0 = ridge_y - (190 if vertical else 150); self.sun_y1 = ridge_y + 2
        self.sun_x = self.lens.project(self.hdir(AZ0, 3.0)[None])[0][0]
        # --- sky base colours (linear)
        k = np.exp(-e / 0.28)[..., None]
        zen = np.array([0.010, 0.010, 0.080], f32); hor = np.array([0.030, 0.045, 0.210], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-((e - 0.40) / 0.22) ** 2)[..., None] * np.array([0.020, 0.003, 0.040], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        kg = np.exp(-e / 0.20)[..., None]
        self.gold = (np.array([0.10, 0.20, 0.55], f32) * (1 - kg) + np.array([1.25, 0.62, 0.22], f32) * kg).astype(f32)
        self.dusk = (np.array([0.035, 0.050, 0.24], f32) * (1 - 0.4 * e[..., None]) + np.exp(-e / 0.10)[..., None] * np.array([1.0, 0.36, 0.12], f32) * 0.9
                     + np.exp(-e / 0.30)[..., None] * np.array([0.55, 0.14, 0.42], f32) * 0.35).astype(f32)
        # --- stars (HYG v4.1 V < 7, via star-dates' catalogue)
        z = np.load(os.path.join(SCR, "stars.npz"))
        sel = z["mag"] < 6.5
        self.sv = eq_vec(z["ra"][sel], z["dec"][sel]).astype(np.float64)
        mag = z["mag"][sel]; self.mag = mag
        self.flux = (4.0 * 10 ** (-0.4 * 0.90 * mag)).astype(f32)
        T = np.clip(bv_temp(np.clip(z["ci"][sel], -0.4, 2.0)), 2600, 30000)
        cols = np.stack([bbcolor(x) for x in T]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = yv[:, None] + (cols - yv[:, None]) * 1.7; cols = np.clip(cols, 0.02, None)
        cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.th = (np.clip((mag + 1.5) / 8.0, 0, 1) ** 0.9 * 0.8).astype(f32)
        self.ph = np.random.default_rng(3).uniform(0, 1000, len(mag)).astype(f32)
        self.glint = np.where(mag < 1.4)[0]
        self.mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        # --- ecliptic (obliquity 23.44 deg); Sun's ecliptic longitude on 10 Nov ~ 228 deg
        lam = np.radians(np.arange(0, 360, 0.25)); eps = math.radians(23.44)
        self.ecl = np.stack([np.cos(lam), np.sin(lam) * math.cos(eps), np.sin(lam) * math.sin(eps)], -1)
        self.ecl_lam = np.degrees(lam)
        # --- direction of our galactic motion: l = 90, b = 0 (Cygnus)
        GAL2EQ = EQ2GAL.T
        self.apex = GAL2EQ @ np.array([0.0, 1.0, 0.0])
        rng = np.random.default_rng(11)
        n = 300
        self.sl = dict(th=rng.uniform(0, 2 * np.pi, n), ph=rng.uniform(0, 1, n), v=rng.uniform(0.35, 1.0, n), hue=rng.uniform(0, 1, n),
                       w=rng.uniform(0.6, 1.0, n))
        # --- meteors (sporadic): Poisson schedule, rate rises with the dust beat
        self.meteors = []
        t = 0.6
        while t < DUR + 1:
            rate = 0.5 + 3.0 * ramp(t, T_DUST - 0.5, T_DUST + 0.6) * (1 - 0.35 * ramp(t, T_DUST + 3.5, T_DUST + 5)) + 1.0 * ramp(t, T_END - 1, T_END)
            t += rng.exponential(1 / rate)
            ang = rng.uniform(math.radians(200), math.radians(340)) if rng.uniform() < 0.8 else rng.uniform(0, 2 * np.pi)
            self.meteors.append(dict(t0=t, x=rng.uniform(0.05, 0.95) * W, y=rng.uniform(0.04, 0.55) * self.hz, ang=ang,
                                     L=rng.uniform(180, 520) * (1 if vertical else 0.8), dur=rng.uniform(0.35, 0.8),
                                     col=[(0.4, 1.0, 0.5), (1.0, 0.6, 0.2), (0.4, 0.8, 1.0), (1.0, 0.4, 0.9), (0.9, 1.0, 0.5)][rng.integers(5)],
                                     I=rng.uniform(0.6, 1.4)))
        # --- star-birth sparkles along the Milky Way (galactic b ~ N(0, 6 deg))
        self.spark = []
        t = 8.0
        while t < DUR + 1:
            rate = 1.5 + 6 * ramp(t, 14, 22) + 40 * ramp(t, T_STARS - 0.3, T_STARS + 0.6) * (1 - 0.55 * ramp(t, T_STARS + 3, T_STARS + 5))
            t += rng.exponential(1 / rate)
            l = math.radians(rng.uniform(-110, 140)); b = math.radians(rng.normal(0, 5.5))
            g = np.array([math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b)])
            self.spark.append(dict(t0=t, v=GAL2EQ @ g, sz=rng.uniform(10, 34) * (1 if vertical else 0.85), life=rng.uniform(0.6, 1.2),
                                   col=[(1.0, 0.45, 0.75), (0.4, 0.85, 1.0), (0.75, 0.5, 1.0), (1.0, 0.8, 0.4), (0.9, 0.95, 1.0)][rng.integers(5)]))
        # --- distant galaxies (fixed on the sky, chosen in screen space at the mid sidereal time)
        lm = self.lst(DUR / 2); Minv = eq2hor(lm)                              # horizon = M @ eq  ->  eq = M.T @ horizon
        self.gal_spr = [spiral_sprite(160, 40 + i, rng.uniform(0.3, 0.8)) for i in range(4)]
        self.gals = []
        tries = 0
        while len(self.gals) < 18 and tries < 2000:
            tries += 1
            x = rng.uniform(0.08, 0.92) * W; y = rng.uniform(0.05, 0.72) * self.hz
            if vertical and 280 < y < 720 and tries < 1500: continue          # keep them off the counter stack
            if any(math.hypot(x - g["x"], y - g["y"]) < (170 if vertical else 200) for g in self.gals): continue
            h = self.rays[int(y), int(x)].astype(np.float64)
            self.gals.append(dict(x=x, y=y, v=Minv.T @ h, spr=rng.integers(4), size=rng.uniform(60, 120) * (1 if vertical else 0.9),
                                  rot=rng.uniform(0, 180), I=rng.uniform(0.5, 1.0)))
        # supernova schedule: sparse, then a burst on "explode", then steady
        self.sne = []
        t = T_STARS - 1.5
        while t < DUR + 1:
            rate = 1.0 + 1.5 * ramp(t, T_SN, T_SN + 0.5)
            t += rng.exponential(1 / rate); self.sne.append((t, int(rng.integers(len(self.gals))), rng.uniform(-0.3, 0.3), rng.uniform(-0.2, 0.2)))
        for k in range(9): self.sne.append((T_EXPLODE - 0.05 + k * 0.07 + rng.uniform(0, 0.05), int(rng.integers(len(self.gals))), rng.uniform(-0.3, 0.3), rng.uniform(-0.2, 0.2)))
        # --- beams around the Sun
        self.beams = [dict(a=i * 2 * np.pi / 9 + rng.uniform(-0.2, 0.2), w=rng.uniform(0.10, 0.20), I=rng.uniform(0.7, 1.2), hue=rng.uniform(0, 1),
                           ph=rng.uniform(0, 6.28), sp=rng.uniform(0.6, 1.4)) for i in range(9)]
        # --- foreground states
        f = fg.flat; y = (f @ np.array([0.2126, 0.7152, 0.0722], f32))[..., None]
        self.fg_gold = (fg.rgb * np.array([1.05, 0.92, 0.78], f32)).astype(f32)
        self.fg_dusk = (fg.rgb * np.array([0.55, 0.38, 0.46], f32)).astype(f32)
        self.fg_night = ((f * 0.55 + y * 0.45) * np.array([0.22, 0.20, 0.50], f32) * 1.0).astype(f32)
        a = fg.a; sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = (cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 2.5) * a).astype(f32)
        self.a = a[..., None]
        # --- layout of the counter stack
        if vertical:
            self.lay = dict(clock=(W / 2, 258, 34), x0=56, x1=W - 56, y0=330, dy=68, ls=36, vs=58,
                            fx=W / 2, fly=692, fvy=772, fsy=845, fls=36, fvs=104, fss=30, fmaxw=W - 110)
        else:
            self.lay = dict(clock=(430, 52, 28), x0=56, x1=800, y0=112, dy=58, ls=29, vs=46,
                            fx=1390, fly=300, fvy=380, fsy=452, fls=32, fvs=92, fss=26, fmaxw=860)

    # ----------------------------------------------------------------------------------------------- geometry
    @staticmethod
    def hdir(az, alt):
        az, alt = math.radians(az), math.radians(alt)
        return np.array([math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)])

    @staticmethod
    def lst(t):
        """sidereal time: November dusk at 34 N (Sun RA 15.0 h); a gentle ~32x time-lapse drift"""
        return 19.75 + 0.45 * min(max(t, 0.0), DUR) / DUR

    def proj(self, v, lst):
        h = v @ eq2hor(lst).T
        x, y, ok = self.lens.project(h)
        return x, y, ok & (h[..., 2] > -0.02), h[..., 2]

    def sun_pos(self, t):
        u = min(max(t / DUR, 0), 1)
        return self.sun_x, self.sun_y0 + (self.sun_y1 - self.sun_y0) * (u ** 1.25)

    # ----------------------------------------------------------------------------------------------- layers
    def mw_layer(self, lst):
        M = EQ2GAL @ eq2hor(lst).T
        g = self.rays @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        return cv2.remap(self.mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def stars_layer(self, t, dark, lst):
        L = self.L; W, H = L.W, L.H
        acc = np.zeros((H + 2, W + 2, 3), f32)
        on = np.clip((dark - self.th) / 0.08, 0, 1)
        vis = np.where(on > 0)[0]
        if len(vis) == 0: return acc[:H, :W]
        x, y, ok, z = self.proj(self.sv[vis], lst)
        sel = ok & (x > 0) & (x < W - 1) & (y > 0) & (y < H - 1) & (z > 0)
        idx = vis[sel]; xs = x[sel]; ys = y[sel]; zz = z[sel]
        nt = np.sin(t * 13.1 + self.ph[idx]) * 0.5 + np.sin(t * 23.7 + self.ph[idx] * 1.7) * 0.3
        sig = np.clip(0.10 + 0.35 * np.exp(-zz / 0.15), 0.08, 0.6)
        fl = self.flux[idx] * on[idx] * np.clip(zz / 0.10, 0, 1) * np.exp(sig * nt * 1.6)
        val = (fl[:, None] * self.scol[idx]).astype(f32)
        x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int); fx = (xs - x0)[:, None]; fy = (ys - y0)[:, None]
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, (y0 + dy, x0 + dx), val * wg)
        acc = acc[:H, :W]
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = acc * (acc.max(2, keepdims=True) > 0.3)
        st += cv2.GaussianBlur(big, (0, 0), 2.2) * 2.0 + cv2.GaussianBlur(big, (0, 0), 7.0) * 1.6
        return st

    def ecliptic(self, fx, t, lst, amt):
        if amt <= 0.01: return
        x, y, ok, z = self.proj(self.ecl, lst)
        H, W = fx.shape[:2]
        lam = self.ecl_lam
        # chevrons flow along the ecliptic towards (and past) the Sun: the way Earth is heading
        ph = ((lam + 26.0 * t) % 9.0) / 9.0
        bump = np.exp(-((ph - 0.5) / 0.10) ** 2)
        m = ok & (z > 0.005) & (x > -50) & (x < W + 50) & (y > -50) & (y < H + 50)
        pts = np.where(m)[0]
        for i in pts[::2]:
            I = (0.25 + 1.8 * bump[i]) * amt
            c = tuple(float(v) for v in np.array(CYAN, f32) * I)
            cv2.circle(fx, (int(x[i] * 4), int(y[i] * 4)), int(4 + 7 * bump[i]), c, -1, cv2.LINE_AA, 2)

    def speed_lines(self, t, lst, drive, col_mix):
        """streaks radiating from the direction we move in (galactic l = 90 deg, Cygnus); half-res HDR layer"""
        H2, W2 = self.hy.shape
        lay = np.zeros((H2, W2, 3), f32)
        if drive <= 0.01: return lay
        ax, ay, ok, z = self.proj(self.apex, lst)
        ax, ay = float(ax) / 2, float(ay) / 2
        s = self.sl; d = speed_dist(t)
        rmin, rmax = 25.0, 1500.0
        u = (s["ph"] + d * 0.55 * s["v"]) % 1.0
        r = rmin * (rmax / rmin) ** u
        ln = r * (0.10 + 0.30 * min(drive, 2.0)) * s["w"]
        a = np.clip(u / 0.15, 0, 1) * np.clip((1 - u) / 0.1, 0, 1) * drive
        for i in range(len(r)):
            if a[i] < 0.01: continue
            c0, s0 = math.cos(s["th"][i]), math.sin(s["th"][i])
            p1 = (ax + c0 * r[i], ay + s0 * r[i]); p0 = (ax + c0 * (r[i] - ln[i]), ay + s0 * (r[i] - ln[i]))
            hue = (s["hue"][i] * 0.35 + 0.55 + 0.25 * col_mix + t * 0.05) % 1.0
            c = palette(hue) * 1.3 + 0.25
            col = tuple(float(v) for v in c * a[i] * 0.9)
            cv2.line(lay, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), col, 1 + int(2 * u[i]), cv2.LINE_AA, 2)
        return lay

    def galaxies(self, img, fx, t, lst, vis):
        H, W = img.shape[:2]
        pos = []
        for g in self.gals:
            x, y, ok, z = self.proj(g["v"], lst); x, y = float(x), float(y)
            pos.append((x, y))
            if vis <= 0.01 or not ok or z < 0.05: continue
            spr = self.gal_spr[g["spr"]]; S = spr.shape[0]; sc = g["size"] / (0.8 * S)
            R = int(g["size"] * 0.6) + 4
            xa, ya, xb, yb = max(0, int(x) - R), max(0, int(y) - R), min(W, int(x) + R), min(H, int(y) + R)
            if xb <= xa or yb <= ya: continue
            ang = math.radians(g["rot"]); ca, sa = math.cos(ang) * sc, math.sin(ang) * sc
            M = np.array([[ca, -sa, x - xa - (ca * S / 2 - sa * S / 2)], [sa, ca, y - ya - (sa * S / 2 + ca * S / 2)]], np.float64)
            patch = cv2.warpAffine(spr, M, (xb - xa, yb - ya), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            img[ya:yb, xa:xb] += patch * (0.65 * g["I"] * vis)
        # supernova flashes
        for (ts, gi, ox, oy) in self.sne:
            u = t - ts
            if not (0 <= u < 1.6): continue
            g = self.gals[gi]; x, y = pos[gi]
            if not (0 < x < W and 0 < y < self.hz - 10): continue
            x += ox * g["size"]; y += oy * g["size"]
            k = 1.0 if ts < T_EXPLODE - 0.2 else 1.35
            fl = (22 * math.exp(-u / 0.10) + 4 * math.exp(-u / 0.7)) * k
            col = np.array([0.75, 0.88, 1.0], f32)
            def fn(d, dx, dy):
                core = np.exp(-d / 2.2) * fl + np.exp(-d / 12) * fl * 0.10
                sp = (np.exp(-np.abs(dy) / 1.3) * np.exp(-np.abs(dx) / 55) + np.exp(-np.abs(dx) / 1.3) * np.exp(-np.abs(dy) / 55)) * fl * 0.10
                return (core + sp)[..., None] * col
            from lib.core import splat
            splat(img, x, y, 120, fn)
            Rr = 6 + 150 * (u / 1.6) ** 0.55 * (1.3 if k > 1 else 1.0)
            for ch, off in ((0, 5), (1, 0), (2, -5)):
                c = [0.0, 0.0, 0.0]; c[ch] = float(3.0 * k * (1 - u / 1.6) ** 1.6)
                cv2.circle(fx, (int(x * 4), int(y * 4)), int((Rr + off) * 4), tuple(c), max(2, int(4 * (1 - u / 1.6)) + 1), cv2.LINE_AA, 2)

    def sparkles(self, fx, t, lst, vis):
        if vis <= 0.01: return
        H, W = fx.shape[:2]
        act = [s for s in self.spark if 0 <= t - s["t0"] < s["life"]]
        if not act: return
        V = np.array([s["v"] for s in act]); x, y, ok, z = self.proj(V, lst)
        for j, s in enumerate(act):
            if not ok[j] or z[j] < 0.03 or not (0 < x[j] < W and 0 < y[j] < self.hz): continue
            u = (t - s["t0"]) / s["life"]
            I = min(1.0, u / 0.07) * (1 - u) ** 1.5 * vis * 3.2
            c = np.array(s["col"], f32); L = s["sz"] * (0.6 + 0.6 * u)
            X, Y = int(x[j] * 4), int(y[j] * 4)
            col = tuple(float(v) for v in c * I)
            cv2.line(fx, (X - int(L * 4), Y), (X + int(L * 4), Y), col, 2, cv2.LINE_AA, 2)
            cv2.line(fx, (X, Y - int(L * 4)), (X, Y + int(L * 4)), col, 2, cv2.LINE_AA, 2)
            cv2.circle(fx, (X, Y), int(3 * 4), tuple(float(v) for v in (c * 0.5 + 0.5) * I * 2.5), -1, cv2.LINE_AA, 2)
            if u > 0.05:
                cv2.circle(fx, (X, Y), int((6 + 34 * u) * 4), tuple(float(v) for v in c * I * 0.5), 2, cv2.LINE_AA, 2)

    def meteor_layer(self, fx, t, vis):
        for m in self.meteors:
            u = (t - m["t0"]) / m["dur"]
            if not (0 <= u < 1.25): continue
            head = min(u, 1.0)
            ca, sa = math.cos(m["ang"]), math.sin(m["ang"])
            hx, hy = m["x"] + ca * m["L"] * head, m["y"] - sa * m["L"] * head
            if hy > self.fg.skyline[int(min(max(hx, 0), self.L.W - 1))] - 4: continue
            fade = (1 - max(u - 1, 0) / 0.25) * math.sin(math.pi * min(head, 1) * 0.5 + 0.3) * m["I"] * vis
            tail = m["L"] * min(head, 0.55)
            c = np.array(m["col"], f32)
            for k in range(10):
                a0, a1 = k / 10, (k + 1) / 10
                p0 = (hx - ca * tail * a1, hy + sa * tail * a1); p1 = (hx - ca * tail * a0, hy + sa * tail * a0)
                I = fade * (1 - a0) ** 1.6 * 2.2
                col = tuple(float(v) for v in (c * 0.7 + 0.3 * (1 - a0)) * I)
                cv2.line(fx, (int(p0[0] * 4), int(p0[1] * 4)), (int(p1[0] * 4), int(p1[1] * 4)), col, 2 if k > 2 else 3, cv2.LINE_AA, 2)
            if u <= 1.0:
                cv2.circle(fx, (int(hx * 4), int(hy * 4)), 10, tuple(float(v) for v in (c * 0.4 + 0.6) * fade * 6), -1, cv2.LINE_AA, 2)

    def sun(self, img, t, pulse, rings_amt, light_amt):
        """big stylised setting Sun: limb-darkened disc, glow, rainbow-tinted beams, fusion rings"""
        H, W = img.shape[:2]
        sx, sy = self.sun_pos(t); R = self.sun_r
        # beams on the half-res grid
        dx = self.hx - sx; dy = self.hy - sy; d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx)
        acc = np.zeros(dx.shape + (3,), f32)
        dd = np.maximum(d - R, 0)
        rad = (1 - np.exp(-(dd + 4) / 30)) * (np.exp(-dd / (900 + 500 * light_amt)) * 0.9 + 0.12 * np.exp(-dd / 2200))
        for b in self.beams:
            a = b["a"] + 0.07 * t * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.7 + 0.3 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.30) % 1.0
            acc += (palette(x) * 0.6 + np.array([1.0, 0.7, 0.3], f32) * 0.4) * (g * I)[..., None]
        beams = acc * rad[..., None] * 0.24 * (0.8 + 0.4 * pulse + 1.2 * light_amt)
        glow = (np.exp(-dd / 50) * 1.3 + np.exp(-dd / 220) * 0.35 + np.exp(-dd / 700) * 0.05)[..., None] * np.array([1.0, 0.62, 0.25], f32) * pulse
        lay = cv2.resize(beams + glow, (W, H), interpolation=cv2.INTER_LINEAR)
        img += lay * self.above
        # the disc (full res, local window)
        pad = int(R + 30)
        x0, x1, y0, y1 = max(0, int(sx - pad)), min(W, int(sx + pad)), max(0, int(sy - pad)), min(H, int(sy + pad))
        ddx = self.xx[y0:y1, x0:x1] + 0.5 - sx; ddy = self.yy[y0:y1, x0:x1] + 0.5 - sy
        r = np.sqrt(ddx ** 2 + ddy ** 2)
        mu = np.sqrt(np.clip(1 - (r / R) ** 2, 0, 1))
        inside = smooth(R + 1, R - 1, r)
        flatten = 1 + 0.10 * (ddy / R)                             # a hint of reddening towards the lower limb
        disc = (inside * (0.45 + 0.55 * mu))[..., None] * np.array([1.0, 0.55, 0.18], f32) * np.stack([np.ones_like(r), 1 / flatten, 1 / flatten ** 2], -1)
        img[y0:y1, x0:x1] += disc * 9.0 * pulse
        # fusion rings: each pulse beat sends out a chromatic ring
        if rings_amt > 0.01:
            fx = np.zeros((H // 2, W // 2, 3), f32)
            per = 0.8
            for k in range(4):
                tb = (math.floor(t / per) - k) * per
                u = t - tb
                if u < 0: continue
                Rr = R + (60 + 1200 * rings_amt) * (u / 3.2) ** 0.7
                a = math.exp(-u / 0.9) * rings_amt * 2.2
                for ch, off in ((0, 7), (1, 0), (2, -7)):
                    c = [0.0, 0.0, 0.0]; c[ch] = float(a * (1.0, 0.75, 0.45)[ch])
                    cv2.circle(fx, (int(sx * 2), int(sy * 2)), int((Rr + off) * 2), tuple(c), max(2, int(6 * math.exp(-u))), cv2.LINE_AA, 2)
            fx = cv2.GaussianBlur(fx, (0, 0), 1.5) * 1.5 + cv2.GaussianBlur(fx, (0, 0), 6) * 1.2
            img += cv2.resize(fx, (W, H), interpolation=cv2.INTER_LINEAR) * self.above
        # golden light wavefronts (the sunlight beat)
        if light_amt > 0.01:
            fx = np.zeros((H // 2, W // 2, 3), f32)
            for k in range(6):
                tb = T_LIGHT + 0.15 + k * 0.55
                u = t - tb
                if not (0 <= u < 2.2): continue
                Rr = R + 1500 * (u / 2.2) ** 0.8
                a = (1 - u / 2.2) ** 1.5 * 3.0 * light_amt
                cv2.circle(fx, (int(sx * 2), int(sy * 2)), int(Rr * 2), (a * 1.0, a * 0.80, a * 0.35), 6, cv2.LINE_AA, 1)
            fx = cv2.GaussianBlur(fx, (0, 0), 2.0) * 1.4 + cv2.GaussianBlur(fx, (0, 0), 9) * 1.4
            img += cv2.resize(fx, (W, H), interpolation=cv2.INTER_LINEAR)

    # ----------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        lst = self.lst(t)
        g2d = ramp(t, 1.0, 13.0); d2n = ramp(t, 9.0, 24.0)
        dark = 0.12 + 0.88 * ramp(t, 2.5, 20.0)
        sky = self.gold * (1 - g2d) + self.dusk * g2d
        sky = sky * (1 - 0.82 * d2n) + self.night * d2n + self.dusk * 0.12 * d2n * np.exp(-self.e / 0.12)[..., None]
        # Milky Way and stars
        mwv = ramp(t, 6.0, 22.0)
        sky = sky + self.mw_layer(lst) * (9.0 * mwv ** 1.5) * self.above * (1 + 0.25 * ramp(t, T_STARS, T_STARS + 1) * (1 - ramp(t, T_STARS + 4, T_STARS + 6)))
        sky = sky + self.stars_layer(t, dark, lst) * self.above
        # VFX layers
        fx = np.zeros((H, W, 3), f32)
        ecl = ramp(t, 1.4, 2.6) * (1 - 0.75 * ramp(t, T_SUN + 0.5, T_DUST))
        self.ecliptic(fx, t, lst, ecl)
        galv = ramp(t, 16.0, T_STARS)
        self.galaxies(sky, fx, t, lst, galv)
        self.sparkles(fx, t, lst, ramp(t, 9.0, 14.0))
        self.meteor_layer(fx, t, 0.5 + 0.5 * ramp(t, 3, 12))
        drive = speed_drive(t)
        sl = self.speed_lines(t, lst, drive, ramp(t, T_CMB - 0.2, T_CMB + 0.5))
        sky = sky + cv2.resize(sl + cv2.GaussianBlur(sl, (0, 0), 3.0) * 1.0, (W, H), interpolation=cv2.INTER_LINEAR) * self.above
        sky = sky + (fx + cv2.GaussianBlur(fx, (0, 0), 2.5) * 1.3 + cv2.GaussianBlur(fx, (0, 0), 9) * 0.6) * self.above
        # the Sun
        sun_beat = ramp(t, T_SUN - 0.2, T_SUN + 0.4) * (1 - 0.7 * ramp(t, T_DUST, T_DUST + 1.0))
        beat = max(0.0, math.sin(2 * math.pi * t / 0.8)) ** 6
        pulse = 1 + (0.12 + 0.55 * sun_beat) * beat
        light_amt = ramp(t, T_LIGHT - 0.1, T_LIGHT + 0.5) * (1 - 0.6 * ramp(t, T_END + 0.6, T_END + 1.6))
        self.sun(sky, t, pulse, 0.25 + 0.75 * sun_beat, light_amt)
        # foreground: golden -> dusk -> blue-violet night; backlit rim from the Sun; tinted by flashes
        fgc = self.fg_gold * (1 - g2d) + self.fg_dusk * g2d
        fgc = fgc * (1 - 0.85 * d2n) + self.fg_night * 0.85 * d2n
        sx, sy = self.sun_pos(t)
        rimc = np.array([1.0, 0.62, 0.25], f32) * (0.9 + 0.5 * (pulse - 1) + 0.5 * light_amt)
        fgc = fgc + self.rim[..., None] * rimc * 0.35
        fgc = fgc + self.fg.flat * np.array([1.0, 0.70, 0.35], f32) * (0.10 * light_amt + 0.04 * (pulse - 1))
        fgc = fgc + self.fg.flat * np.array([0.55, 0.40, 1.0], f32) * 0.05 * min(drive, 1.5)
        img = sky * (1 - self.a) + fgc * self.a
        # new-counter flash + chromatic shockwave
        for i, (key, ta, *_rest) in enumerate(COUNTERS):
            u = t - ta
            if -0.03 < u < 1.3 and ta > 0.6:
                col = np.array(COUNTERS[i][5], f32)
                img += 0.9 * math.exp(-max(u, 0) / 0.09) * ease((u + 0.03) / 0.03) * (0.4 + 0.6 * col)
                Rr = 2200 * (max(u, 0) / 1.3) ** 0.6; wdt = 14 + 50 * u
                cx, cy = (W / 2, self.lay["fvy"]) if L.vertical else (self.lay["fx"], self.lay["fvy"])
                dd = np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2)
                ring = np.zeros(dd.shape + (3,), f32)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    ring[..., ch] = np.exp(-((dd - Rr - off) / wdt) ** 2) * 1.6 * math.exp(-max(u, 0) / 0.5)
                img += cv2.resize(ring, (W, H), interpolation=cv2.INTER_LINEAR)
        wl = white_level(t)
        if wl > 0: img = img + (28 * wl ** 1.5) * np.array([1.0, 0.94, 0.86], f32)
        img = self.chroma_bloom(img)
        out = tonemap(img, 1.15)
        out = self.grade(out)
        out = finish(out, t, grain=0.009, vignette=0.14)
        self.overlay(out, t)
        return out

    def chroma_bloom(self, img):
        img = bloom(img, 0.9)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 24), (1, 18), (2, 13)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.30

    def grade(self, out):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * 1.18
        return np.clip(out + np.array([0.008, 0.006, 0.020], f32) * (1 - out), 0, 1)

    # ----------------------------------------------------------------------------------------------- overlay
    def overlay(self, out, t):
        L = self.L; W, H = L.W, L.H; ly = self.lay; v = L.vertical
        wl = white_level(t); vis_all = 1.0 - 0.85 * wl
        # stack state: rows already in (fractional while flying); only the latest MAXROWS stay, older ones slide out the top
        s_in = sum(ease((t - FEAT_END[c[0]]) / FLY) for c in COUNTERS if t >= FEAT_END[c[0]])
        off = max(0.0, s_in - MAXROWS)
        if s_in > 0:
            n = min(s_in, MAXROWS)
            y0 = ly["y0"] - ly["dy"] * 0.62; y1 = ly["y0"] + ly["dy"] * (n - 0.38)
            yy = np.arange(H, dtype=f32)[:, None]
            band = smooth(y0 - 50, y0 + 25, yy) * smooth(y1 + 50, y1 - 25, yy) * min(1.0, s_in * 2)
            if not v: band = band * smooth(ly["x1"] + 110, ly["x1"] + 25, np.arange(W, dtype=f32)[None, :])
            out *= (1 - 0.55 * band * vis_all)[..., None]
            out += (band * 0.025 * vis_all)[..., None] * np.array([0.25, 0.20, 0.55], f32)
        # clock
        cx, cy, cs = ly["clock"]
        crisp_put(out, f"YOU'VE BEEN WATCHING {t:4.1f} S", cx, cy, cs, (0.97, 0.97, 1.0), vis_all * ramp(t, 0.15, 0.45), wt="Bold")
        WHITE = (0.97, 0.97, 1.0)
        for i, (key, ta, lab, val, sub, col) in enumerate(COUNTERS):
            if t < ta - 0.02: continue
            te = FEAT_END[key]
            slot = i - off
            ry = ly["y0"] + ly["dy"] * slot
            ra = float(np.clip(1 + slot / 0.6, 0, 1)) * vis_all                 # fades as it slides out the top
            vtxt = val(t)
            if t < te:                                                 # featured card
                age = t - ta
                d0 = 0.16 if ta > 0.6 else -0.02                       # let the outgoing value clear the spot first
                a = min(1.0, max(0.0, (age - d0) / 0.10)) * vis_all
                pop = 1 + 0.22 * math.exp(-max(age - d0, 0) / 0.08)
                crisp_put(out, lab, ly["fx"], ly["fly"], ly["fls"], WHITE, a, wt="Black")
                w = text_img(vtxt, int(ly["fvs"]), "Black")[1]
                vs = ly["fvs"] * min(1.0, ly["fmaxw"] / max(w, 1))
                crisp_put(out, vtxt, ly["fx"], ly["fvy"], int(vs * pop), col, a)
                crisp_put(out, sub, ly["fx"], ly["fsy"], ly["fss"], tuple(c * 0.55 + 0.45 for c in col), a * ramp(age, 0.25, 0.5), wt="Bold")
            else:                                                       # flying into / sitting in the stack
                x = min(max((t - te) / FLY, 0.0), 1.0)
                u = ease(x); up = 1 - (1 - x) ** 3                         # fast ease-out: leaves the featured spot quickly
                if ra <= 0.003: continue
                if x < 1:
                    w = text_img(vtxt, int(ly["vs"]), "Black")[1]
                    rx = ly["x1"] - w / 2
                    fvs = ly["fvs"] * min(1.0, ly["fmaxw"] / max(text_img(vtxt, int(ly["fvs"]), "Black")[1], 1))
                    size = int(fvs + (ly["vs"] - fvs) * up)
                    crisp_put(out, vtxt, ly["fx"] + (rx - ly["fx"]) * up, ly["fvy"] + (ry - ly["fvy"]) * up, size, col, ra)
                    crisp_put(out, ROWLAB[key], ly["x0"], ry, ly["ls"], WHITE, u * ra, anchor="l", wt="Black")
                else:
                    hl = 0.0
                    if key == "orbit" and t > 1000 / V_ORBIT: hl = math.exp(-(t - 1000 / V_ORBIT) / 0.5)
                    crisp_put(out, ROWLAB[key], ly["x0"], ry, ly["ls"], WHITE, ra, anchor="l", wt="Black")
                    crisp_put(out, vtxt, ly["x1"], ry, int(ly["vs"] * (1 + 0.35 * hl)), col, ra, anchor="r")
        # finale: "right here" -> how far you went, big
        if t >= T_END:
            age = t - T_END; a = min(1.0, max(0.0, (age - 0.16) / 0.10)) * vis_all
            crisp_put(out, "WHILE YOU WATCHED, YOU TRAVELLED", ly["fx"], ly["fly"], ly["fls"], WHITE, a, wt="Black")
            vt = f"{fmt_int(V_ORBIT * t)} KM"
            crisp_put(out, vt, ly["fx"], ly["fvy"], int(ly["fvs"] * (1 + 0.2 * math.exp(-age / 0.08))), CYAN, a)
            crisp_put(out, f"+ {fmt_int(V_CMB * t)} KM THROUGH THE COSMOS", ly["fx"], ly["fsy"], ly["fss"], (0.92, 0.65, 1.0), a * ramp(age, 0.3, 0.6), wt="Bold")
        self.caps.draw(out, t)


# ------------------------------------------------------------------------------------------------- run
def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        for t in stills:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=17)
    t0 = time.time()
    for i in range(NFR):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{NFR}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0, "DUR", DUR)


def patch(vertical, ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render (from other-suns)"""
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["nice", "-n", "10", "ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=17); k = 0
    for i in range(NFR):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t)); k += 1
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched", k, "frames")


TRANSITIONS = ",".join(f"{te - 0.05:.2f}:{te + FLY + 0.05:.2f}" for te in sorted(set(FEAT_END.values())))


if __name__ == "__main__":
    if sys.argv[1] == "patch":
        rng = sys.argv[3] if len(sys.argv) > 3 else TRANSITIONS
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in rng.split(",")]); sys.exit()
    if sys.argv[1] == "info":
        print("DUR", DUR, "frames", NFR)
        for l in PL: print(f"{l['key']:6s} {l['start']:6.2f} {l['end']:6.2f}")
        tl = (NFR - 1) / FPS
        for c in COUNTERS: print(f"{c[0]:6s} appears {c[1]:5.2f}  at 35 s: {c[3](35.0):>22s}   last frame ({tl:.2f} s): {c[3](tl)}")
        sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
