"""WHAT IF EARTH SPUN FASTER? -- one locked tripod shot of the desert (01_desert.png) on the equator, looking ESE
(azimuth 135 deg) in December. BATCH4 swap format: each spin-up swaps in with a tinted flash + chromatic shockwave,
the dunes are relit by the racing day / night cycle, readouts at the top, big orange one-word captions.
  24 h (calm morning, the Sun creeping up) -> 12 h (the Sun shoots up, the first night: star trails)
  -> 6 h (day-night every few seconds, sand starts to blow) -> 2 h (day and night flicker, howling sand haze)
  -> 84 min (the breakup limit: sand at the equator floats up off the dunes) -> white-out -> 24 h (loops)
The sky is real spherical astronomy: the Sun (dec -23.44 deg) and ~2,600 stars are placed by hour angle for latitude 0
and projected through the lens (f = 1,100 px), so star trails and the Sun's path are true. Star trails are drawn as a
fixed ~2.6 s 'exposure' of the sky behind us; the sky itself (day / twilight / night) is instantaneous.
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info | stills 1.0,9.5 | segs
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, kf, bbcolor, splat
from lib.foreground import Foreground
from lib.sky import sun_disc, lens_flare
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-earth-spins-faster"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/01_desert.png"
FPS = 30
LEAD, TAIL = 0.25, 1.40
F_PX = 1100.0                     # ~83 deg vertical field on 1920 px
HZ = 1215.0                       # the true horizon (elevation 0) in frame px: behind the far dune crests
AZ_CAM = math.radians(135.0)
DEC_SUN = math.radians(-23.44)
CAP_Y = 1520
RO_Y = (318, 398, 450)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ science
GM, R_EQ = 3.986004e14, 6378.137e3
G0 = GM / R_EQ ** 2
T_BREAK = 2 * math.pi * math.sqrt(R_EQ ** 3 / GM)                       # s: centrifugal = gravity at the equator (~84.5 min)


def eq_speed_kmh(T_s): return 2 * math.pi * R_EQ / T_s * 3.6
def weight_loss(T_s): return (2 * math.pi / T_s) ** 2 * R_EQ / G0        # fraction of g cancelled at the equator
def bulge_km(T_s): return 21.4 * (86164.0 / T_s) ** 2                      # linear (small-spin) scaling of today's 21.4 km


# ------------------------------------------------------------------------------------------------ stages
# P: on-screen length of one day (s); tilt: stage colour; wind: blowing sand
STAGES = {
    "now": dict(T=24 * 3600, P=240.0, name="TODAY · 24-HOUR DAY", l2="EQUATOR SPINS AT 1,670 KM/H", l3="YOU WEIGH 0.3% LESS THERE",
                tc=(255, 230, 170), wind=0.0, fl=(1.0, 0.95, 0.8)),
    "h12": dict(T=12 * 3600, P=10.0, name="12-HOUR DAY", l2="EQUATOR: 3,340 KM/H", l3="WEIGHT AT THE EQUATOR −1.4%",
                tc=(255, 205, 130), wind=0.15, fl=(1.0, 0.85, 0.55)),
    "h6": dict(T=6 * 3600, P=5.0, name="6-HOUR DAY", l2="EQUATOR: 6,680 KM/H", l3="BULGE ~340 KM · WEIGHT −5.5%",
               tc=(150, 215, 255), wind=0.40, fl=(0.6, 0.85, 1.0)),
    "h2": dict(T=2 * 3600, P=1.8, name="2-HOUR DAY", l2="EQUATOR: 20,000 KM/H", l3="WEIGHT AT THE EQUATOR −50%",
               tc=(255, 160, 90), wind=0.80, fl=(1.0, 0.65, 0.35)),
    "brk": dict(T=T_BREAK, P=1.25, name="84-MINUTE DAY", l2="EQUATOR: 28,500 KM/H = ORBITAL SPEED", l3="WEIGHT AT THE EQUATOR: ZERO",
                tc=(255, 120, 80), wind=1.0, fl=(1.0, 0.5, 0.35)),
}
STAGES["end"] = STAGES["now"]

T_SW = {"h12": LN["h12"]["start"] - 0.06, "h6": LN["h6"]["start"] - 0.06, "h2": LN["h2"]["start"] - 0.06, "brk": LN["brk"]["start"] - 0.06}
T_BACK = LN["end"]["start"] - 0.10
T_WO0 = T_BACK - 0.80
SWAPS = [(T_SW[k], k) for k in ("h12", "h6", "h2", "brk")] + [(T_BACK, "end")]
T_FLOAT = wt("brk_b", "EQUATOR") - 0.3                                   # the sand starts to float
PULSES = [wt("hook", "FASTER"), wt("now", "24 HOURS"), wt("h12", "12 HOURS"), wt("h12_b", "RACES"), wt("h6", "6 HOURS"), wt("h6_b", "OCEANS"),
          wt("h2", "2 HOURS"), wt("h2_b", "FLICKER"), wt("h2_c", "HOWL"), wt("h2_c", "BULGES"), wt("brk", "84 MINUTES"), wt("brk_b", "NOTHING"),
          wt("brk_c", "APART"), wt("end", "24 HOURS")]


def stage_at(t):
    cur, t0 = "now", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    return cur, t0


# angular rate (rad / screen s), ramped over 0.6 s at each swap; integrated once into a table
_tt = np.arange(0, DUR + 1, 1 / 240.0)
def _omega(t):
    keys = [(0.0, 2 * math.pi / STAGES["now"]["P"])]
    for ts, k in SWAPS[:-1]:
        keys += [(ts, keys[-1][1]), (ts + 0.6, 2 * math.pi / STAGES[k]["P"])]
    return kf(t, keys)
_om = np.array([_omega(x) for x in _tt])
_ph = np.concatenate([[0], np.cumsum((_om[1:] + _om[:-1]) / 2) / 240.0])
H0 = math.radians(-79.0)                                                  # the Sun ~10 deg up at t = 0


def hour_angle(t):
    """the Sun's hour angle (rad). After the white-out the clock is reset to the opening (seamless loop)."""
    if t >= T_BACK:
        return H0 + (t - T_BACK - (DUR - T_BACK)) * 2 * math.pi / STAGES["now"]["P"]   # ends exactly at H0
    return H0 + float(np.interp(t, _tt, _ph))


# ------------------------------------------------------------------------------------------------ geometry
FWD = np.array([math.sin(AZ_CAM), math.cos(AZ_CAM), 0.0])                 # (East, North, Up)
RIGHT = np.array([math.cos(AZ_CAM), -math.sin(AZ_CAM), 0.0])
UP = np.array([0.0, 0.0, 1.0])


def eq_to_enu(H, dec):
    """latitude 0: hour angle H (west +), declination -> (E, N, U)"""
    cd = np.cos(dec)
    return np.stack([-cd * np.sin(H), np.sin(dec) * np.ones_like(H), cd * np.cos(H)], -1)


def project(v):
    z = v @ FWD; x = 540 + F_PX * (v @ RIGHT) / np.maximum(z, 1e-6); y = HZ - F_PX * (v @ UP) / np.maximum(z, 1e-6)
    return x, y, z > 0.05


def sun_vec(t): return eq_to_enu(np.array(hour_angle(t)), np.array(DEC_SUN))


def sun_el(t): return math.degrees(math.asin(float(np.clip(sun_vec(t)[2], -1, 1))))


def dayness(t): return float(smooth(-7.0, 6.0, sun_el(t)))


# star catalogue: ~2,600 stars, uniform on the sphere, a steep magnitude distribution; black-body colours
_r = np.random.default_rng(7)
NS = 2600
_z = _r.uniform(-1, 1, NS); ST_DEC = np.arcsin(_z).astype(f32); ST_RA = _r.uniform(0, 2 * np.pi, NS).astype(f32)
ST_F = (0.06 * _r.uniform(0, 1, NS) ** (-1 / 1.25)).clip(0, 9).astype(f32)
_T = np.clip(_r.lognormal(np.log(6000), 0.35, NS), 3000, 20000)
ST_C = np.stack([bbcolor(float(T)) for T in _T]).astype(f32) * 0.6 + 0.4

# sand grains for the breakup beat (frame px on the dune surface, below the crests)
NG = 5000
G_SEED = _r.uniform(0, 1, (NG, 4)).astype(f32)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.68)
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        d = (RIGHT[None, None, :] * (xx - 540)[..., None] + UP * (HZ - yy)[..., None] + FWD * F_PX).astype(f32)
        self.dirs = d / np.linalg.norm(d, axis=-1, keepdims=True)
        self.el = np.degrees(np.arcsin(np.clip(self.dirs[..., 2], -1, 1))).astype(f32)
        yy2, xx2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx2, yy2
        self.dust_n = [fbm2((256, 512), 51, 2.2), fbm2((256, 512), 52, 1.8)]
        # where the dunes are (grain emitters): opaque foreground, weighted towards the crests and the lit slopes
        a = fg.a
        ys, xs = np.nonzero(a[1180:1900] > 0.9); ys = ys + 1180
        r = np.random.default_rng(3); pick = r.choice(len(ys), NG, replace=True)
        self.gx, self.gy = xs[pick].astype(f32), ys[pick].astype(f32)
        sh = np.zeros_like(a); sh[8:] = a[:-8]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.caps = Captions(L, WORDS, emphasis={"EARTH", "FASTER", "24 HOURS", "12 HOURS", "RACES", "SUN", "6 HOURS", "OCEANS", "RUSH",
                                                  "EQUATOR", "2 HOURS", "FLICKER", "NIGHT", "WINDS", "HOWL", "BULGES", "84 MINUTES",
                                                  "NOTHING", "APART", "RIGHT"})
        L.cap_y = CAP_Y

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, sv):
        es = math.degrees(math.asin(float(np.clip(sv[2], -1, 1))))
        D = float(smooth(-7.0, 6.0, es)); tw = float(math.exp(-((es + 1.5) / 5.5) ** 2))   # day / twilight
        cosg = np.clip(self.dirs @ sv.astype(f32), -1, 1)
        gam = np.degrees(np.arccos(cosg))
        e = np.maximum(self.el, 0)
        zen = np.array([0.018, 0.085, 0.46], f32); hor = np.array([0.25, 0.45, 0.82], f32)
        k = np.exp(-e / 14.0)[..., None]
        day = (zen * (1 - k) + hor * k) * (1 + 0.15 * (1 + cosg ** 2)[..., None])
        day = day + np.array([1.0, 0.85, 0.6], f32) * (np.exp(-gam / 5.0) * 0.8 + np.exp(-gam / 20.0) * 0.08)[..., None]
        day = day * (0.35 + 0.65 * smooth(-2, 25, es))
        # twilight: orange band on the Sun's side, blue-violet above, Belt of Venus opposite
        az_side = (0.5 + 0.5 * cosg)
        tw_col = (np.array([1.0, 0.36, 0.08], f32) * (np.exp(-e / 7.0) * az_side ** 1.5)[..., None] * 1.3
                  + np.array([0.75, 0.18, 0.35], f32) * (np.exp(-((e - 14) / 9) ** 2))[..., None] * 0.45
                  + np.array([0.12, 0.10, 0.40], f32) * np.exp(-e / 40.0)[..., None] * 0.35)
        night = np.array([0.006, 0.013, 0.048], f32) * (0.8 + 0.2 * np.exp(-e / 25))[..., None] \
            + np.array([0.012, 0.018, 0.040], f32) * np.exp(-e / 9)[..., None]
        sky = night * (1 - D) + day * D + tw_col * tw
        return sky.astype(f32), D, tw, es

    def trails(self, t, D_now, img):
        """star trails: a long exposure of the sky behind us (up to 2.6 s or 300 deg of turn, whichever is shorter), drawn
        as polylines in 4 age slices (older = fainter), each slice weighted by how dark the sky was then"""
        W, H = self.L.W, self.L.H
        om = _omega(t); win = min(2.6, math.radians(300) / om)
        if t < T_SW["h12"]: win = min(win, 0.15)                               # calm opening: crisp points
        K = int(np.clip(math.degrees(om * win) * 1.2, 4, 240))
        ts = t - win * np.linspace(0, 1, K)
        Hs = np.array([hour_angle(x) for x in ts])
        dk = np.array([1 - dayness(x) for x in ts])
        if dk.max() < 0.02: return
        sel = ST_F > 0.11                                                      # the brighter ~1,300 stars
        HH = Hs[:, None] + ST_RA[None, sel]
        v = eq_to_enu(HH, ST_DEC[None, sel])
        x, y, ok = project(v)
        ok &= (x > -400) & (x < W + 400) & (y > -600) & (y < HZ + 30)
        el = np.maximum(v[..., 2], 0.0); ext = np.exp(-0.25 / (el + 0.06))
        F = ST_F[sel]; C = ST_C[sel]
        acc = np.zeros((H, W, 3), f32)
        slices = np.array_split(np.arange(K), 4) if K >= 8 else [np.arange(K)]
        for si, idx in enumerate(slices):
            age = 1 - si / max(len(slices), 1)
            dsl = float(dk[idx].mean()) * age ** 1.2
            if dsl < 0.01: continue
            lo, hi = idx[0], min(idx[-1] + 2, K)
            for bi, (f0, f1) in enumerate(((0.11, 0.25), (0.25, 0.6), (0.6, 1.5), (1.5, 99))):
                pick = np.nonzero((F >= f0) & (F < f1))[0]
                lines = []
                for j in pick:
                    oj = ok[lo:hi, j]
                    if oj.sum() < 1: continue
                    pts = np.stack([x[lo:hi, j], y[lo:hi, j]], 1)[oj]
                    if len(pts) == 1: pts = np.concatenate([pts, pts + 0.6])
                    lines.append((pts * 4).astype(np.int32))
                if not lines: continue
                val = min((f0 + f1) / 2, 3.0) * 0.55 * dsl
                col = tuple(float(c) for c in (np.array([0.85, 0.92, 1.0]) * val))
                cv2.polylines(acc, lines, False, col, 1 + (bi >= 2), lineType=cv2.LINE_8, shift=2)
        acc = acc * ext.mean() if False else acc
        img += (cv2.GaussianBlur(acc, (0, 0), 0.6) * 1.3 + cv2.GaussianBlur(acc, (0, 0), 2.5) * 0.5) * (1 - D_now) ** 2

    def sun_arc(self, img, t, D_now):
        """the racing Sun leaves a glowing golden arc (a long exposure of its path) once the days get short"""
        om = _omega(t)
        amt = float(smooth(2 * math.pi / 12.0, 2 * math.pi / 3.0, om))
        if amt <= 0.01 or t >= T_BACK: return
        win = min(0.45 * 2 * math.pi / om, 1.2); K = 90
        ts = t - win * np.linspace(0, 1, K)
        v = np.stack([sun_vec(x) for x in ts]); x, y, ok = project(v)
        ok &= v[:, 2] > -0.05
        if ok.sum() < 2: return
        H, W = self.L.H, self.L.W
        acc = np.zeros((H, W, 3), f32)
        pts = np.stack([x, y], 1)
        for k in range(K - 1):
            if not (ok[k] and ok[k + 1]): continue
            a = (1 - k / K) ** 1.5
            p0 = tuple(int(c * 4) for c in pts[k]); p1 = tuple(int(c * 4) for c in pts[k + 1])
            cv2.line(acc, p0, p1, (6.0 * a, 4.2 * a, 1.6 * a), 3, lineType=cv2.LINE_8, shift=2)
        img += (cv2.GaussianBlur(acc, (0, 0), 1.2) + cv2.GaussianBlur(acc, (0, 0), 8) * 0.6 + cv2.GaussianBlur(acc, (0, 0), 30) * 0.4) * amt

    def sun(self, img, t, pulse):
        """the Sun at its true 0.53 deg; motion-blurred along its path over a half-frame shutter"""
        n = 7; pts = []
        for j in range(n):
            v = sun_vec(t - j / (FPS * 2 * (n - 1)))
            x, y, ok = project(v[None])
            if ok[0]: pts.append((float(x[0]), float(y[0])))
        if not pts: return None
        r = F_PX * math.tan(math.radians(0.2666))
        for x, y in pts:
            if -300 < x < 1380 and -300 < y < HZ + 60:
                sun_disc(img, x, y, r, power=pulse / n)
        x, y = pts[0]
        if -200 < x < 1280 and -200 < y < HZ: lens_flare(img, x, y, power=0.8)
        return pts[0]

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, D, tw, es, sv, stage, wind):
        fg = self.fg
        day = fg.rgb * (0.55 + 0.75 * smooth(-2, 30, es))
        warm = fg.rgb * np.array([1.0, 0.62, 0.38], f32) * 0.55
        night = fg.night(0.075)
        out = night * (1 - D) + day * D + warm * tw * 0.5
        side = 0.5 + 0.5 * float(sv[0] * RIGHT[0] + sv[1] * RIGHT[1])      # crest rim light from the Sun's side
        out += (self.rim * (0.25 * D + 0.4 * tw))[..., None] * np.array([1.0, 0.75, 0.45], f32) * side
        return out

    def dust(self, img, t, wind, D, tw):
        """wind-blown sand haze low over the dunes, streaming left -> right faster as the winds grow"""
        if wind <= 0.01: return
        n1, n2 = self.dust_n; H, W = self.L.H, self.L.W
        y0 = 950; ys = self.yy[y0:]; xs = self.xx[y0:]
        u = ((xs * 0.12 - t * (40 + 220 * wind)) % 512).astype(f32); v = ((ys * 1.6 + 8 * np.sin(xs * 0.008 + t * 2)) * 0.5 % 256).astype(f32)
        a = cv2.remap(n1, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        b = cv2.remap(n2, (u * 2.3) % 512, (v * 1.7) % 256, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        dens = np.clip(0.55 * a + 0.35 * b - 0.15, 0, 1.2) * smooth(1080, 1260, ys) * (1 - 0.6 * smooth(1450, 1900, ys)) * wind * 0.45
        col = np.array([0.95, 0.62, 0.32], f32) * (0.05 + 0.85 * D) + np.array([1.0, 0.45, 0.15], f32) * tw * 0.4
        img[y0:] = img[y0:] * (1 - dens[..., None] * 0.6) + dens[..., None] * col

    def grains(self, img, t, D, tw):
        """the breakup limit: at the equator nothing holds the sand down any more -- grains drift up off the dunes"""
        if t < T_FLOAT or t >= T_WO0 + 0.5: return
        u = t - T_FLOAT; H, W = self.L.H, self.L.W
        st = G_SEED[:, 0] * 2.5
        age = np.maximum(u - st, 0)
        up_ = age ** 1.5 * (40 + 110 * G_SEED[:, 1])
        x = self.gx + age * (80 + 120 * G_SEED[:, 2]) + 6 * np.sin(age * 3 + G_SEED[:, 3] * 6)
        y = self.gy - up_
        a = smooth(0, 0.4, age) * (1 - smooth(5.5, 7.5, age)) * (0.5 + 0.8 * G_SEED[:, 3])
        sel = (age > 0) & (x > 0) & (x < W - 1) & (y > 0) & (y < H - 1)
        x, y, a = x[sel], y[sel], a[sel]
        col = (np.array([1.0, 0.78, 0.5], f32) * (0.25 + 1.4 * D + 0.6 * tw))
        acc = np.zeros((H + 1, W + 1), f32)
        x0 = x.astype(int); y0 = y.astype(int); fx = x - x0; fy = y - y0
        for dy, dx, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, (y0 + dy, x0 + dx), a * wg)
        acc = cv2.GaussianBlur(acc[:H, :W], (0, 0), 1.0) * 6.0 + cv2.GaussianBlur(acc[:H, :W], (0, 0), 5) * 2.0
        img += acc[..., None] * col

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        cur, t0 = stage_at(t)
        S = STAGES[cur]
        prev = [k for ts, k in SWAPS if ts < t0]
        A = STAGES[prev[-1]] if prev else STAGES["now"]
        w = ramp(t, t0 - 0.1, t0 + 0.8) if t0 > 0 else 1.0
        wind = lerp(A["wind"], S["wind"], w) if cur != "end" else 0.0
        if T_WO0 < t < T_BACK: wind *= 1 - ease((t - T_WO0) / 0.8)
        pulse = 1 + sum(0.25 * math.exp(-((t - tp) / 0.2) ** 2) for tp in PULSES)
        sv = sun_vec(t)
        sky, D, tw, es = self.sky(t, sv)
        img = self.up(sky)
        self.trails(t, D, img)
        self.sun_arc(img, t, D)
        self.sun(img, t, 1.0)
        # ---- foreground
        fgc = self.relight(D, tw, es, sv, cur, wind) * (1 + 0.08 * (pulse - 1))
        a = self.fg.a[..., None]
        img = img * (1 - a) + fgc * a
        self.dust(img, t, wind, D, tw)
        self.grains(img, t, D, tw)
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "end":
                fc = np.array(STAGES[k]["fl"], f32)
                img += (2.2 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, 540, 760, u, fc)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.9], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([1.0, 0.95, 0.9], f32)
            self.shock(img, 540, 760, t - T_BACK, np.array([1.0, 0.9, 0.8], f32))
        img = bloom(img, 0.8)
        out = tonemap(img, 1.0)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
        return out

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W; S = STAGES[cur]
        x = W / 2; ys = RO_Y
        start = LN["now"]["start"] if cur == "now" else (LN["end"]["start"] if cur == "end" else t0)
        a = ramp(t, start + 0.15, start + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "end": a *= 1 - ramp(t, DUR - 0.9, DUR - 0.4)
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.35 if len(S["name"]) < 14 else 1.1))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (240, 242, 250), a, 0.10, display=True)
        self.caps.draw(out, t)


def lerp(a, b, w): return a + (b - a) * w


def run_stills(ts):
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in ts:
        t0 = time.time(); im = sc.frame(t)
        Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{t:05.2f}.png"))
        print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "breakup period %.1f min = %.3f h" % (T_BREAK / 60, T_BREAK / 3600))
        for k in ("now", "h12", "h6", "h2", "brk"):
            T = STAGES[k]["T"]
            print(f"{k:4s} {T / 3600:6.2f} h  eq speed {eq_speed_kmh(T):8,.0f} km/h  weight -{weight_loss(T) * 100:5.1f}%  bulge(lin) {bulge_km(T):7.0f} km")
        print("swaps", [(round(a, 2), k) for a, k in SWAPS], "float", round(T_FLOAT, 2))
        for x in (0, 3, 7, T_SW["h12"] + 1, T_SW["h12"] + 4): print("t", round(x, 2), "sun el", round(sun_el(x), 1))
        sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "stills":
        run_stills([float(x) for x in sys.argv[2].split(",")])
