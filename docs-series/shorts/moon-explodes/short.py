"""WHAT IF THE MOON EXPLODED? -- one locked tripod shot of the calm lake and pier (03_calm_lake_wooden_pier.png) at night.
BATCH4 swap format (other-suns / more-moons): every beat swaps in with a tinted flash + chromatic shockwave, the pier and
shore are relit for the new sky, readouts at the top, big orange one-word captions. The lake mirrors the rendered sky
(lake.py, copied unchanged from ../more-moons: water mask + the photo's own tree / post reflections kept).
  our full Moon -> a flash: white-hot, glowing cracks -> it breaks into glowing fragments + a dust cloud
  -> over days the debris spreads along the Moon's orbit into a ring (a band arcing up out of the far trees)
  -> some debris falls: meteor showers streak across the sky ("the hard rain"), mirrored in the lake
  -> a bright, settled ring arcing over the lake -> white-out -> our Moon again (loops)
Lens: telephoto, f = 14,000 px (the frame is ~4.4 deg wide), so the Moon keeps its true 0.52 deg (r = 63 px).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py stills 1.0,9.5          -> SCR/stills/<t>.png
  /home/user/ttsenv/bin/python short.py segs                   restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, kf, bbcolor
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place
import moons as MO
from moons import Body, pole_vec
import lake

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-moon-explodes"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/03_calm_lake_wooden_pier.png"
FPS = 30
LEAD, TAIL = 0.25, 1.40
F_SKY = 1400.0                    # star field / horizon geometry (as more-moons)
F_TELE = 14000.0                  # disc sizes (true angular size at this focal length)
CAP_Y = 1470                      # captions sit on the pier deck; the sky stays clear
RO_Y = (318, 398, 450)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


# ------------------------------------------------------------------------------------------------ science
R_MOON, D_MOON, R_E = 1737.4, 384400.0, 6371.0
G, M_MOON = 6.674e-11, 7.342e22
E_BIND = 3 * G * M_MOON ** 2 / (5 * R_MOON * 1e3)                       # J, uniform sphere: ~1.24e29
SUN_ON_EARTH = 1361.0 * math.pi * (R_E * 1e3) ** 2                      # W intercepted by Earth: ~1.74e17
ELEV = 3.0
D_OBS = math.sqrt(D_MOON ** 2 - (R_E * math.cos(math.radians(ELEV))) ** 2) - R_E * math.sin(math.radians(ELEV))
RP = F_TELE * math.tan(math.asin(R_MOON / D_OBS))                         # Moon radius on screen, px (~63)
MX, MY = 880.0, 1000.0

PHASE = math.radians(2.5)
U_SH = np.array([0.45, -0.89]); U_SH = U_SH / np.linalg.norm(U_SH)
MO.set_sun([-math.sin(PHASE) * U_SH[0], -math.sin(PHASE) * U_SH[1], -math.cos(PHASE)])

# ------------------------------------------------------------------------------------------------ the ring arc
def circ3(p1, p2, p3):
    (x1, y1), (x2, y2), (x3, y3) = p1, p2, p3
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1) + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
    uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3) + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
    return ux, uy, math.hypot(x1 - ux, y1 - uy)


ARC_CX, ARC_CY, ARC_R = circ3((1200.0, 1235.0), (MX, MY), (-140.0, 470.0))   # rises from behind the far trees, arcs up-left
TH_M = math.atan2(MY - ARC_CY, MX - ARC_CX)
ARC_SGN = 1.0 if math.atan2(470.0 - ARC_CY, -140.0 - ARC_CX) > TH_M else -1.0   # +s runs towards the upper-left end


def arc_pt(s, q):
    th = TH_M + ARC_SGN * s / ARC_R
    return ARC_CX + (ARC_R + q) * np.cos(th), ARC_CY + (ARC_R + q) * np.sin(th)


# ------------------------------------------------------------------------------------------------ timeline
T_FLASH = wt("flash", "FLASH") - 0.04
T_SPLIT = wt("crack", "CRACKS") + 0.10
T_RING = LN["ring"]["start"] - 0.06
T_RINGDONE = wt("ring_b", "EARTH") + 0.2
T_RAIN = LN["rain"]["start"] - 0.06
T_FINAL = LN["final"]["start"] - 0.06
T_BACK = LN["end"]["start"] - 0.10
T_WO0 = T_BACK - 0.80
SWAPS = [(T_FLASH, "boom"), (T_RING, "ring"), (T_RAIN, "rain"), (T_FINAL, "final"), (T_BACK, "end")]
PULSES = [wt("hook", "EXPLODED"), wt("moon", "CALM"), wt("crack", "GLOWING"), wt("ring_b", "RING"), wt("rain", "FALL"),
          wt("rain_b", "METEORS"), wt("rain_c", "RAIN"), wt("final", "BRIGHT"), wt("tide", "ECLIPSES"), wt("end_b", "PIECE")]

SET = {
    "moon": dict(name="OUR MOON", l2="3,474 KM WIDE · 0.52°", l3="384,400 KM AWAY", tc=(235, 240, 255),
                 glow=(0.60, 0.68, 0.90), tint=(0.75, 0.85, 1.10), gain=0.10, fl=(0.9, 0.9, 1.0)),
    "boom": dict(name="SHATTERED", l2="ENERGY NEEDED: 1.2 × 10²⁹ J", l3="~22,000 YEARS OF EARTH'S SUNLIGHT", tc=(255, 170, 90),
                 glow=(1.0, 0.62, 0.30), tint=(1.15, 0.80, 0.55), gain=0.16, fl=(1.0, 0.85, 0.6)),
    "ring": dict(name="A NEW RING", l2="SPREADING ALONG THE MOON'S ORBIT", l3="2.4 MILLION KM AROUND", tc=(200, 225, 255),
                 glow=(0.70, 0.78, 1.0), tint=(0.80, 0.88, 1.10), gain=0.13, fl=(0.8, 0.9, 1.0)),
    "rain": dict(name="THE HARD RAIN", l2="METEOR SHOWERS FOR YEARS", l3="DEBRIS HITS AT ~11 KM/S", tc=(255, 190, 120),
                 glow=(1.0, 0.80, 0.55), tint=(1.0, 0.88, 0.75), gain=0.14, fl=(1.0, 0.85, 0.65)),
    "final": dict(name="RING SKY", l2="NO MORE ECLIPSES", l3="TIDES ~1/3 AS HIGH", tc=(225, 235, 255),
                  glow=(0.78, 0.84, 1.0), tint=(0.85, 0.90, 1.10), gain=0.19, fl=(0.85, 0.9, 1.0)),
    "end": None,
}
SET["end"] = SET["moon"]


def set_at(t):
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def blast(t):   # chunk / dust separation 0 -> ~1 (fast at first, then coasting)
    if t < T_SPLIT: return 0.0
    u = t - T_SPLIT
    return 1 - math.exp(-u / 1.3) + 0.03 * u


def spread(t):  # debris spread along the orbit 0 -> 1
    if t >= T_BACK: return 0.0
    return ramp(t, T_RING + 0.15, T_RINGDONE) ** 1.2


def heat(t):    # glowing-hot fragments: flash -> cooling over the crack beat
    if t < T_FLASH or t >= T_RING + 1.5: return 0.0
    return ramp(t, T_FLASH - 0.02, T_FLASH + 0.25) * (1 - ramp(t, T_SPLIT + 1.0, T_RING + 1.5))


def cracks(t):  # crack lines over the white-hot disc
    return ramp(t, T_FLASH + 0.15, T_SPLIT) if t < T_BACK else 0.0


# ------------------------------------------------------------------------------------------------ debris
_r = np.random.default_rng(2024)
ND = 7000
D_S = np.concatenate([_r.uniform(-1500, 560, ND - 1500), _r.normal(0, 260, 1500)]).astype(f32)   # along the orbit (px)
D_Q = (_r.standard_t(4, ND) * 26).astype(f32)                                                     # across the band
D_Q = np.clip(D_Q, -200, 200)
_ang = _r.uniform(0, 2 * np.pi, ND); _mag = RP * 3.4 * _r.uniform(0, 1, ND) ** 1.3
D_B = np.stack([np.cos(_ang) * _mag * 1.25, np.sin(_ang) * _mag * 0.85], 1).astype(f32)          # blast offsets
D_F = (0.04 * _r.uniform(0, 1, ND) ** (-0.85)).clip(0, 3.0).astype(f32)                          # brightness
D_C = (np.array([0.92, 0.94, 1.0], f32) * _r.uniform(0.85, 1.15, (ND, 1)).astype(f32)
       * np.array([1.0, 0.97, 0.92], f32) ** _r.uniform(-1, 1, (ND, 1)).astype(f32))
D_PH = _r.uniform(0, 6.28, ND).astype(f32)

# meteors: a Poisson stream; the rate follows the beats (rain -> years -> hard rain; a few in the ring sky)
RAD = arc_pt(-650.0, 0.0)                                                 # radiant on the ring, upper left


def met_rate(t):
    if t >= T_WO0: return 0.0
    return kf(t, [(0, 0.0), (T_RAIN + 0.3, 0.0), (T_RAIN + 1.2, 2.5), (wt("rain_b", "METEORS"), 5.0), (wt("rain_b", "YEARS"), 9.0),
                  (wt("rain_c", "RAIN"), 16.0), (T_FINAL - 0.3, 14.0), (T_FINAL + 0.8, 1.6), (T_WO0, 1.6)])


METEORS = []
_m = np.random.default_rng(99); tt = 0.0
while tt < DUR:
    tt += _m.exponential(1 / 18.0)
    if _m.uniform() < met_rate(tt) / 18.0:
        fire = _m.uniform() < 0.10
        ang = math.atan2(_m.uniform(400, 1250) - RAD[1], _m.uniform(-100, 1180) - RAD[0])
        r0 = _m.uniform(150, 1100)
        x0, y0 = RAD[0] + r0 * math.cos(ang), RAD[1] + r0 * math.sin(ang)
        L = _m.uniform(220, 600) * (1.5 if fire else 1.0)
        METEORS.append(dict(t0=tt, d=_m.uniform(0.35, 0.8) * (1.4 if fire else 1.0), x0=x0, y0=y0, dx=math.cos(ang) * L, dy=math.sin(ang) * L,
                            I=_m.uniform(0.6, 1.6) * (5.0 if fire else 1.0), fire=fire,
                            col=np.array([0.75, 1.0, 0.85] if _m.uniform() < 0.5 else [1.0, 0.92, 0.80], f32)))


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.84)
        self.water, self.occ, self.YM = lake.load(SCR)
        self.cam = SkyCam(W, H, self.YM, F_SKY)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        e = np.maximum(np.degrees(np.arctan2(self.YM - yy, F_SKY)), 0).astype(f32)
        nz = np.array([0.0060, 0.012, 0.046], f32)                     # deep blue night, never black
        self.night_sky = (nz * (0.8 + 0.2 * np.exp(-e / 25))[..., None] + np.array([0.012, 0.018, 0.044], f32) * np.exp(-e / 9)[..., None]
                          + np.array([0.014, 0.014, 0.020], f32) * np.exp(-e / 3)[..., None]).astype(f32)
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.YM - yyf, F_SKY)), 0.25)
        X = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        self.ext = (np.exp(-X[:, None] * np.array([0.06, 0.09, 0.17], f32)[None, :])[:, None, :] * np.ones((1, W, 1), f32)).astype(f32)
        yy2, xx2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xx2, yy2
        # ring coordinates (full res): along-arc s and across-arc q
        th = np.arctan2(yy2 - ARC_CY, xx2 - ARC_CX)
        self.rs = (ARC_SGN * (th - TH_M) * ARC_R).astype(f32); self.rq = (np.sqrt((xx2 - ARC_CX) ** 2 + (yy2 - ARC_CY) ** 2) - ARC_R).astype(f32)
        n1 = fbm2((64, 2048), 7, 1.8)
        self.ring_n = n1                                                # clumps along the band
        # the Moon: rendered once, then cut into fragments
        self.moon = Body("moon", "8k_moon.jpg", RP, pole_vec(-12, 4), model="rock", surf=1.15, detail=0.0,
                         prep=lambda t: t / max(float((t @ np.array([0.2126, 0.7152, 0.0722], f32)).mean()), 1e-4))
        self._fragments()
        # foreground prep: skyline rim light, water geometry (as more-moons)
        a = fg.a; sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        y0 = int(self.YM); self.wy0 = y0
        ys = yy2[y0:]; xs = xx2[y0:]
        h = ys - self.YM + 6.0
        self.w_h = h; self.w_xs = xs; self.w_ys = ys
        self.w_X = (xs - 540) / h; self.w_Z = 600.0 / h
        self.w_R = (0.86 - 0.42 * np.clip((ys - self.YM) / 574, 0, 1) ** 0.7).astype(f32)
        self.ripn = [fbm2((256, 512), 61, 2.3), fbm2((256, 512), 62, 2.0)]
        pine = ((xs < 175) & (ys < 1640)).astype(f32)
        self.w_amp_mask = (1 - 0.85 * cv2.GaussianBlur(pine, (0, 0), 12)).astype(f32)
        self.caps = Captions(L, WORDS, emphasis={"MOON", "EXPLODED", "CALM", "FLASH", "CRACKS", "GLOWING", "PIECES", "DAYS", "SPREAD",
                                                  "RING", "EARTH", "FALL", "METEORS", "YEARS", "HARD", "RAIN", "BRIGHT", "AGES",
                                                  "ECLIPSES", "TIDES", "TONIGHT", "GLAD", "ONE", "PIECE"})
        L.cap_y = CAP_Y

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- the Moon + fragments
    def _fragments(self):
        pad = int(RP * 0.25) + 8; S = int(2 * RP) + 2 * pad
        x0, y0 = int(MX) - S // 2, int(MY) - S // 2
        canvas = np.zeros((S, S, 3), f32)
        box = self.moon.render(canvas, MX - x0, MY - y0, 0.0, I=1.0, scale=1.0, ext=self.ext[y0:y0 + S, x0:x0 + S])
        bx0, bx1, by0, by1, cov = box
        cv_ = np.zeros((S, S), f32); cv_[by0:by1, bx0:bx1] = cov
        self.p_rad, self.p_cov, self.p_x0, self.p_y0, self.p_S = canvas, cv_, x0, y0, S
        r = np.random.default_rng(31)
        K = 22; seeds = []
        while len(seeds) < K:
            u, v = r.uniform(-1, 1, 2)
            if u * u + v * v < 0.92: seeds.append((S / 2 + u * RP, S / 2 + v * RP))
        seeds = np.array(seeds, f32)
        yy, xx = np.mgrid[0:S, 0:S].astype(f32)
        wx = xx + fbm2((S, S), 41, 2.2) * RP * 0.07; wy = yy + fbm2((S, S), 42, 2.2) * RP * 0.07   # jagged crack lines
        d = (wx[..., None] - seeds[:, 0]) ** 2 + (wy[..., None] - seeds[:, 1]) ** 2
        lab = d.argmin(-1)
        edge = np.zeros((S, S), f32)
        edge[:-1] += lab[:-1] != lab[1:]; edge[:, :-1] += lab[:, :-1] != lab[:, 1:]
        edge = np.clip(edge, 0, 1) * (self.p_cov > 0.5)
        self.p_edge = cv2.GaussianBlur(edge, (0, 0), 0.9) * 1.6
        self.p_edge_glow = cv2.GaussianBlur(edge, (0, 0), 3.0) * 3.0
        self.frags = []
        for k in range(K):
            m = (lab == k).astype(f32) * self.p_cov
            if m.sum() < 4: continue
            ys_, xs_ = np.nonzero(m > 0.01)
            cx, cy = float((xs_ * m[ys_, xs_]).sum() / m[ys_, xs_].sum()), float((ys_ * m[ys_, xs_]).sum() / m[ys_, xs_].sum())
            inner = cv2.erode((lab == k).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(f32)
            rim = np.clip(m - inner * self.p_cov, 0, 1)
            rim = cv2.GaussianBlur(rim, (0, 0), 1.2) * m
            dx, dy = cx - S / 2, cy - S / 2; dn = math.hypot(dx, dy) + 1e-3
            sp = r.uniform(0.7, 1.3)
            self.frags.append(dict(m=m, rim=rim, cx=cx, cy=cy, x0=int(xs_.min()), x1=int(xs_.max()) + 1, y0=int(ys_.min()), y1=int(ys_.max()) + 1,
                                   v=np.array([dx * 1.25, dy * 0.85], f32) * 2.6 * sp + r.normal(0, RP * 0.35, 2).astype(f32),
                                   w=r.uniform(-0.5, 0.5), s=float(r.uniform(-900, 420)), q=float(r.normal(0, 22))))

    def draw_moon(self, img, I, hot, crk):
        S, x0, y0 = self.p_S, self.p_x0, self.p_y0
        rad = self.p_rad * I
        if hot > 0:                                                    # white-hot surface after the blast
            rad = rad * (1 + 0.5 * hot * (1 - 0.8 * crk)) * np.array([1.0, 0.9, 0.8], f32) + self.p_cov[..., None] * np.array([1.0, 0.62, 0.30], f32) * (hot * 0.6 * (1 - 0.9 * crk))
        if crk > 0:
            rad = rad * (1 - 0.35 * crk) * (1 - 0.8 * np.clip(self.p_edge_glow * 0.5 * crk, 0, 1))[..., None] \
                + (self.p_edge * crk)[..., None] * np.array([7.0, 2.0, 0.30], f32)
        reg = img[y0:y0 + S, x0:x0 + S]
        img[y0:y0 + S, x0:x0 + S] = reg * (1 - self.p_cov[..., None]) + rad
        if crk > 0:
            img[y0:y0 + S, x0:x0 + S] += (self.p_edge_glow * crk * 0.25)[..., None] * np.array([1.0, 0.45, 0.12], f32)

    def draw_frags(self, img, t, I, hot):
        b = blast(t); sp = spread(t); S = self.p_S
        H, W = img.shape[:2]
        shrink = 1 - 0.72 * ease(sp)
        for f in self.frags:
            dx, dy = f["v"] * b * (1 - sp)
            tx, ty = arc_pt(f["s"], f["q"])
            px = MX + (f["cx"] - S / 2) * (1 - sp) + dx + sp * (float(tx) - MX)
            py = MY + (f["cy"] - S / 2) * (1 - sp) + dy + sp * (float(ty) - MY)
            ang = f["w"] * (t - T_SPLIT) if t > T_SPLIT else 0.0
            sc = shrink
            rot = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]], f32) * sc
            # source crop
            m = f["m"][f["y0"]:f["y1"], f["x0"]:f["x1"]]
            col = self.p_rad[f["y0"]:f["y1"], f["x0"]:f["x1"]] * I * (f["m"] / np.maximum(self.p_cov, 1e-4))[f["y0"]:f["y1"], f["x0"]:f["x1"], None]
            if hot > 0:
                col = col * (1 - 0.35 * hot) + m[..., None] * np.array([0.9, 0.35, 0.08], f32) * (hot ** 2 * 0.35)
                col = col + f["rim"][f["y0"]:f["y1"], f["x0"]:f["x1"], None] * np.array([5.0, 1.7, 0.30], f32) * hot
            lc = np.array([f["cx"] - f["x0"], f["cy"] - f["y0"]], f32)
            hh, ww = m.shape; rr = int(math.hypot(hh, ww) * sc / 2) + 3
            X0, Y0 = int(px) - rr, int(py) - rr; X1, Y1 = X0 + 2 * rr, Y0 + 2 * rr
            if X1 <= 0 or Y1 <= 0 or X0 >= W or Y0 >= H: continue
            M = np.zeros((2, 3), np.float32); M[:, :2] = rot; M[:, 2] = np.array([px - X0, py - Y0], f32) - rot @ lc
            cw = cv2.warpAffine(col, M, (2 * rr, 2 * rr), flags=cv2.INTER_LINEAR, borderValue=0)
            mw = cv2.warpAffine(m, M, (2 * rr, 2 * rr), flags=cv2.INTER_LINEAR, borderValue=0)
            xa, ya, xb, yb = max(X0, 0), max(Y0, 0), min(X1, W), min(Y1, H)
            cw = cw[ya - Y0:yb - Y0, xa - X0:xb - X0]; mw = mw[ya - Y0:yb - Y0, xa - X0:xb - X0]
            img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - mw[..., None]) + cw * (0.85 + 0.15 * (1 - sp))

    def debris(self, t, hot, I):
        """dust + rubble: blast cloud -> spread along the orbit; splatted points (two size classes)"""
        b = blast(t); sp = spread(t)
        if b <= 0: return None
        H, W = self.L.H, self.L.W
        tx, ty = arc_pt(D_S, D_Q)
        e = (1 - sp)
        x = MX + D_B[:, 0] * b * e + sp * (tx - MX)
        y = MY + D_B[:, 1] * b * e + sp * (ty - MY)
        vis = ramp(t, T_SPLIT - 0.05, T_SPLIT + 0.6)
        # brightness: hot glow early (orange -> red as it cools), then reflected sunlight
        Tk = 1200 + 2600 * hot
        hotc = bbcolor(Tk) * (2.5 * hot ** 1.5)
        cold = (0.35 + 0.65 * ease(sp)) * I
        tw = 0.85 + 0.15 * np.sin(t * 3.0 + D_PH)
        col = (D_C * cold + hotc[None, :] * (D_F[:, None] > 0.1)) * (D_F * tw * vis)[:, None]
        sel = (x > -3) & (x < W + 3) & (y > -3) & (y < H + 3)
        x, y, col = x[sel], y[sel], col[sel]; big = D_F[sel] > 0.35
        out = np.zeros((H + 2, W + 2, 3), f32)
        outb = np.zeros((H + 2, W + 2, 3), f32)
        for acc, s_ in ((out, ~big), (outb, big)):
            xx, yy, cc = x[s_], y[s_], col[s_]
            x0 = np.floor(xx).astype(int); y0 = np.floor(yy).astype(int); ux = (xx - x0)[:, None]; uy = (yy - y0)[:, None]
            for dy, dx, wgt in ((0, 0, (1 - ux) * (1 - uy)), (0, 1, ux * (1 - uy)), (1, 0, (1 - ux) * uy), (1, 1, ux * uy)):
                np.add.at(acc, (np.clip(y0 + dy, 0, H + 1), np.clip(x0 + dx, 0, W + 1)), cc * wgt)
        d = cv2.GaussianBlur(out[:H, :W], (0, 0), 0.6) * 2.2 + cv2.GaussianBlur(outb[:H, :W], (0, 0), 1.3) * 3.0
        return d

    def ring_glow(self, t, amt):
        """diffuse band of fine dust along the orbit, clumpy along its length"""
        if amt <= 0.003: return 0.0
        sp = spread(t)
        sig = 20 + 34 * sp
        n = self.ring_n; u = ((self.rs + 1600) / 2200 * 2047) % 2047
        cl = cv2.remap(n, u.astype(f32), np.full_like(u, 20 + 10 * math.sin(t * 0.2)).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        ext = smooth(-1500 * sp - 60, -1500 * sp + 200, self.rs) * (1 - smooth(560 * sp + 60, 560 * sp + 300, self.rs)) if sp < 0.999 else 1.0
        g = (np.exp(-(self.rq / (sig * 0.35)) ** 2) * 0.9 * (0.75 + 0.25 * cl) + np.exp(-(self.rq / sig) ** 2) * 0.7 * (0.9 + 0.1 * cl)
             + np.exp(-(self.rq / (sig * 3.2)) ** 2) * 0.2) * ext
        return (g * amt)[..., None] * np.array([0.80, 0.82, 0.90], f32)

    def meteors(self, t):
        H, W = self.L.H, self.L.W
        acc = np.zeros((H + 2, W + 2, 3), f32); light = 0.0
        xs, ys, cs = [], [], []
        for m in METEORS:
            u = (t - m["t0"]) / m["d"]
            if u < 0 or u > 1.35: continue
            head = min(u, 1.0)
            fl = math.sin(math.pi * min(u, 1.0)) ** 0.7 if u <= 1 else 0.0          # brightens then burns out
            tail = 0.32
            k = np.linspace(0, 1, 48, dtype=f32)
            pos = head - tail * k
            ok = pos >= 0
            a = (1 - k) ** 1.5 * fl * m["I"] * 2.2
            if u > 1: a = a * max(0.0, 1 - (u - 1) / 0.35) * 0.4                    # fading persistent train
            px = m["x0"] + m["dx"] * pos; py = m["y0"] + m["dy"] * pos
            c = np.where((k < 0.08)[:, None], np.array([1.0, 1.0, 1.0], f32), m["col"][None, :])
            xs.append(px[ok]); ys.append(py[ok]); cs.append(c[ok] * a[ok, None])
            if m["fire"]: light += fl * 0.06
        if not xs: return None, 0.0
        x = np.concatenate(xs); y = np.concatenate(ys); c = np.concatenate(cs)
        sel = (x > -2) & (x < W + 2) & (y > -2) & (y < H + 2); x, y, c = x[sel], y[sel], c[sel]
        x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); ux = (x - x0)[:, None]; uy = (y - y0)[:, None]
        for dy, dx, wgt in ((0, 0, (1 - ux) * (1 - uy)), (0, 1, ux * (1 - uy)), (1, 0, (1 - ux) * uy), (1, 1, ux * uy)):
            np.add.at(acc, (np.clip(y0 + dy, 0, H + 1), np.clip(x0 + dx, 0, W + 1)), c * wgt)
        a = acc[:H, :W]
        return cv2.GaussianBlur(a, (0, 0), 0.8) * 2.4 + cv2.GaussianBlur(a, (0, 0), 3.0) * 1.6, light

    def shock(self, img, cx, cy, u, col, size=1.0, decay=0.55):
        R = 2400 * size * (max(u, 0) / 1.4) ** 0.6; wdt = (18 + 60 * u) * size
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off * size) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / decay) * (0.6 + 0.4 * col[ch])

    # -------------------------------------------------------------------------------------------- foreground + lake
    def relight(self, A, B, w, light):
        fg = self.fg
        night = fg.flat * 0.75 + fg.rgb * 0.25
        def one(S):
            g = S["gain"]
            key = (fg.rgb * 0.45 + fg.flat * 0.55) * np.array(S["tint"], f32) * g
            out = night * np.array([0.22, 0.32, 0.62], f32) * 0.10 + key
            out += (self.rim * 0.9)[..., None] * np.array(S["glow"], f32) * (0.03 + g * 0.8) * 0.35
            return out
        fb = one(B); fgc = fb if w >= 1 else one(A) * (1 - w) + fb * w
        return fgc * light

    def lake(self, img, skyimg, fgc, t):
        """calm water: the photo's own tree / post reflections (relit) + the rendered sky mirrored about the shoreline,
        slight perspective ripples (from more-moons, chaos = 0)"""
        y0 = self.wy0; h = self.w_h
        amp = 6.0 * self.w_amp_mask
        n1, n2 = self.ripn
        u = (self.w_X * 150) % 512; v = (self.w_Z * 300 + t * 9) % 256
        u2 = (self.w_X * 110 + t * 4) % 512; v2 = (self.w_Z * 180 - t * 6) % 256
        r1 = cv2.remap(n1, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        r2 = cv2.remap(n2, u2.astype(f32), v2.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        dy = (r1 * 0.75 + r2 * 0.45) * amp * (h / 574)
        dx = (r2 * 0.6 - r1 * 0.2) * amp * 0.18 * (h / 574)
        mx = (self.w_xs + dx).astype(f32); my = (2 * self.YM - self.w_ys + dy).astype(f32)
        refl = cv2.remap(skyimg, mx, np.clip(my, 0, self.YM), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=0.9, sigmaY=1.6)
        Wm = self.water[y0:]; occ = self.occ[y0:]
        px = (self.w_xs + dx * 0.6).astype(f32); py = (self.w_ys + dy * 0.35).astype(f32)
        pw = cv2.remap(np.ascontiguousarray(fgc[y0:] * (Wm * occ)[..., None]), px, py - y0, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        ow = cv2.remap(np.ascontiguousarray(Wm * occ), px, py - y0, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        water = pw * 0.95 + refl * ((1 - np.clip(ow, 0, 1)) * self.w_R)[..., None] + np.array([0.002, 0.004, 0.007], f32)
        sl = np.abs(r1 - np.roll(r1, 2, 0))
        water += refl * (np.clip(sl - 0.75, 0, None) * 0.3 * (h / 574) ** 0.5)[..., None]
        img[y0:] = img[y0:] * (1 - Wm[..., None]) + water * Wm[..., None]

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        cur, t0, t1 = set_at(t)
        prev = [k for ts, k in SWAPS if ts < t0]
        A = SET[prev[-1]] if prev else SET["moon"]; B = SET[cur]
        w = ramp(t, t0 - 0.10, t0 + 0.55) if t0 > 0 else 1.0
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.6) + sum(0.30 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        moon_on = cur in ("moon", "end") or (cur == "boom" and t < T_SPLIT)
        sp = spread(t); hot = heat(t)
        ring_amt = 0.0
        if cur in ("ring", "rain", "final"):
            ring_amt = 0.08 * ease(sp) * (1.0 if cur != "final" else 1.0 + 1.2 * ramp(t, T_FINAL, T_FINAL + 1.2))
        # ---- sky: night blue + glow around the Moon / debris core + stars
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32)
        dx = self.hx - MX; dy = self.hy - MY; d = np.sqrt(dx * dx + dy * dy)
        core = 1.0 if moon_on else (1 - 0.8 * ease(sp))
        aure = (np.exp(-np.maximum(d - RP, 0) / 70) * 0.25 + np.exp(-np.maximum(d - RP, 0) / 300) * 0.05) * core * (0.8 + 0.2 * pulse)
        aure = aure * (1 + 0.5 * hot)
        sky = self.night_sky * (1 + 0.6 * ring_amt / 0.05 * 0.35) + aure[..., None] * gcol
        img = self.up(sky)
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.14, star_gain=1.1, cx=2000, cy=900, rot=6.0)
        img += st * (np.exp(-self.up(aure) * 5) * (1 - 0.35 * min(ring_amt / 0.08, 1)))[..., None] * 0.9
        # ---- the ring dust, debris, fragments, the Moon
        if ring_amt > 0: img += self.ring_glow(t, ring_amt * pulse ** 0.5)
        I = 1.0 * pulse
        if moon_on:
            self.draw_moon(img, I * (1 + 1.5 * hot), hot, cracks(t))
        else:
            dbr = self.debris(t, hot, 1.0 + 0.8 * ramp(t, T_FINAL, T_FINAL + 1.2) * (cur == "final"))
            if dbr is not None: img += dbr
            if sp < 0.999: self.draw_frags(img, t, I, hot)
        met, mlight = self.meteors(t)
        if met is not None: img += met
        img = img * self.ext ** 0.3
        skyimg = img.copy()
        # ---- foreground + lake (relit for the new sky)
        light = 1.0 + 0.10 * (pulse - 1) + 1.0 * hot + mlight + (ring_amt * 4 if cur == "final" else ring_amt * 2)
        fgc = self.relight(A, B, w, light)
        a = self.fg.a[..., None]
        img = img * (1 - a) + fgc * a
        self.lake(img, skyimg, fgc, t)
        # ---- swap flashes + chromatic shockwaves
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "end":
                fc = np.array(SET[k]["fl"], f32)
                big = 2.0 if k == "boom" else 1.0
                img += (3.0 * big * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, MX, MY, u, fc, size=1.0 if k != "boom" else 1.3)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([0.95, 0.95, 1.0], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.95, 0.95, 1.0], f32)
            self.shock(img, MX, MY, t - T_BACK, np.array([0.8, 0.85, 1.0], f32))
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.0)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.12)
        self.overlay(out, t, cur, t0)
        return out

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0); acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W; S = SET[cur]
        x = W / 2; ys = RO_Y
        start = LN["moon"]["start"] if cur == "moon" else (LN["end"]["start"] if cur == "end" else t0)
        a = ramp(t, start + 0.15, start + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "end": a *= 1 - ramp(t, DUR - 0.9, DUR - 0.4)
        if a > 0.01:
            dy = (1 - a) * 18
            big = int(L.hud_size * (1.35 if len(S["name"]) < 12 else 1.15))
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (235, 240, 250), a, 0.10, display=True)
        self.caps.draw(out, t)


def run_stills(ts):
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in ts:
        t0 = time.time(); im = sc.frame(t)
        Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{t:05.2f}.png"))
        print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "Moon r px", round(RP, 1), "d_obs", round(D_OBS), "E_bind %.3g J" % E_BIND,
              "= %.0f years of Earth's sunlight" % (E_BIND / SUN_ON_EARTH / 3.156e7), "orbit %.3g km" % (2 * math.pi * D_MOON))
        print("swaps", [(round(a, 2), k) for a, k in SWAPS], "meteors", len(METEORS), "arc", round(ARC_CX), round(ARC_CY), round(ARC_R)); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    if sys.argv[1] == "stills":
        run_stills([float(x) for x in sys.argv[2].split(",")])
