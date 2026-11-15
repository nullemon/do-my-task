"""WHAT IF EARTH STOPPED SPINNING? -- one locked tripod shot of the farm (06_farm_field_barn), swap format (BATCH4).
  a normal day -> SUDDEN STOP (the air keeps moving: dust storm, wheat flattened, oak bent) -> SLOW STOP (the Sun freezes:
  a six-month day) -> THE LONG NIGHT (six months of stars, aurora, frost) -> THE OCEANS MOVE (a globe in the sky: the
  oceans drain from the equator to the poles) -> white-out -> the normal day (loops)
Sky lens f = 1300 px (true 0.53 deg Sun). Every swap: tinted flash, chromatic shockwave, the farm relit.
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py segs              restart-safe segment render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5      stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1, srgb_to_lin
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions
from lib.post import tonemap, finish
from lib.audio import place
from lib.swapfx_b4 import Beams, FX, readout, back_out, lerp

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-earth-stops-spinning"
BG = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/06_farm_field_barn.png"
GLB = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/dl_globe/package/example/img"
THX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/threex.planets/images"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_SKY = 1300.0
R_SUN = F_SKY * math.tan(math.radians(0.533 / 2))          # 6.0 px
SUN_DAY = (790.0, 470.0)
SUN_FROZEN = (760.0, 560.0)
GLOBE = (690.0, 625.0); R_GLOBE = 210.0
MUSIC_KEY = "D"

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


T_SW = {k: LN[k]["start"] - 0.06 for k in ("stop", "slow", "night", "sea")}
T_BACK = LN["end_b"]["start"] - 0.08
T_WO0 = T_BACK - 0.70
SWAPS = [(T_SW[k], k) for k in ("stop", "slow", "night", "sea")] + [(T_BACK, "day2")]
SWAP_TIMES = [ts for ts, _ in SWAPS]
T_FLAT = wt("stop_d", "FLATTENED") - 0.1
T_FREEZE = wt("slow_b", "FREEZES")
T_FROST = wt("night_b", "FROST") - 0.2
T_DRAIN = wt("sea", "OCEANS")
T_DRAIN1 = LN["sea_b"]["end"] + 0.2
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook_b", "SPINNING"), wt("day", "EAST"), wt("stop_b", "AIR"), wt("stop_c", "1,600"), T_FLAT, wt("slow_b", "SUN"),
          wt("slow_c", "MONTHS"), wt("night_b", "STARS"), wt("sea", "OCEANS"), wt("sea_b", "POLES")]

# ------------------------------------------------------------------------------------------------ looks
LOOK = {
    "day": dict(zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), gain=1.0, tint=(1.0, 0.98, 0.95), flat=0.0, amb=(0.03, 0.05, 0.09),
                night=0.0, beams="rainbow", bI=0.55, expo=1.0, dust=0.0, bleach=0.0),
    "stop": dict(zen=(0.17, 0.10, 0.045), hor=(0.62, 0.40, 0.19), gain=0.55, tint=(1.0, 0.80, 0.56), flat=0.35, amb=(0.07, 0.05, 0.03),
                 night=0.0, beams=[(1.0, 0.6, 0.25), (1.0, 0.8, 0.45), (0.9, 0.45, 0.2)], bI=0.25, expo=1.0, dust=1.0, bleach=0.0),
    "slow": dict(zen=(0.26, 0.22, 0.20), hor=(1.0, 0.68, 0.36), gain=1.40, tint=(1.0, 0.84, 0.60), flat=0.0, amb=(0.07, 0.05, 0.03),
                 night=0.0, beams=[(1.0, 0.95, 0.7), (1.0, 0.7, 0.3), (0.7, 0.9, 1.0), (1.0, 0.85, 0.5)], bI=0.9, expo=0.92, dust=0.0, bleach=1.0),
    "night": dict(zen=(0.004, 0.011, 0.050), hor=(0.020, 0.038, 0.095), gain=0.0, tint=(1, 1, 1), flat=1.0, amb=(0, 0, 0),
                  night=1.0, beams=[(0.2, 1.0, 0.5), (0.3, 0.6, 1.0), (0.8, 0.2, 0.7)], bI=0.18, expo=1.1, dust=0.0, bleach=0.0),
    "sea": dict(zen=(0.006, 0.014, 0.060), hor=(0.026, 0.045, 0.11), gain=0.0, tint=(1, 1, 1), flat=1.0, amb=(0, 0, 0),
                night=1.0, beams=[(0.2, 0.55, 1.0), (0.3, 0.9, 1.0), (0.6, 0.4, 1.0)], bI=0.35, expo=1.08, dust=0.0, bleach=0.0),
}
LOOK["day2"] = LOOK["day"]
NUM = ("zen", "hor", "gain", "tint", "flat", "amb", "night", "bI", "expo", "dust", "bleach")
RO = {"day": ("EARTH TODAY", "1 DAY = 24 HOURS", "THIS FARM (40°N) MOVES EAST AT 1,280 KM/H", (255, 225, 140)),
      "stop": ("SUDDEN STOP", "WINDS UP TO 1,670 KM/H", "3× THE FASTEST TORNADO WIND EVER MEASURED", (255, 170, 90)),
      "slow": ("SLOW STOP", "1 DAY = 1 YEAR", "THE SUN WOULD RISE IN THE WEST", (255, 236, 150)),
      "night": ("THE LONG NIGHT", "6 MONTHS OF DARKNESS", "THE NIGHT SIDE FREEZES", (150, 255, 190)),
      "sea": ("THE OCEANS MOVE", "EQUATORIAL BULGE: 21 KM", "TWO POLAR OCEANS · ONE BELT OF LAND", (120, 190, 255))}
FC = {"stop": (1.0, 0.70, 0.40), "slow": (1.0, 0.95, 0.75), "night": (0.45, 1.0, 0.65), "sea": (0.45, 0.70, 1.0)}


def scene_at(t):
    cur, t0 = "day", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def sun_path(u):
    """the Sun's apparent arc as the spin winds down (u 0 -> 1): it climbs from low in the east and stops high"""
    ang = math.radians(-48) * (1 - u) ** 1.6
    return SUN_FROZEN[0] + 560 * math.sin(ang), SUN_FROZEN[1] + 560 * (1 - math.cos(ang)) * 1.5


def load_lin(path, size=None):
    a = np.asarray(Image.open(path).convert("RGB"), f32) / 255.0
    if size: a = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
    return srgb_to_lin(a)


def wind(t):
    """0..~1.3 storm strength (sudden-stop beat only)"""
    if not (T_SW["stop"] - 0.05 < t < T_SW["slow"] + 0.1): return 0.0
    return ramp(t, T_SW["stop"], T_SW["stop"] + 0.9) * (1 + 0.35 * ramp(t, T_FLAT, T_FLAT + 0.5)) * (1 - ramp(t, T_SW["slow"] - 0.3, T_SW["slow"] + 0.05))


class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(BG, L)
        self.hz = float(fg.horizon)
        self.fx = FX(W, H); self.beams = Beams(W, H)
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        self.cam = SkyCam(W, H, self.hz, F_SKY); self.stars = StarSky()
        self.xx, self.yy = self.fx.xx, self.fx.yy
        a = fg.a
        self.a_hard = np.clip(a / 0.9, 0, 1).astype(f32)
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.wheat = (smooth(1320, 1380, self.yy) * a).astype(f32)
        self.night_fg = fg.night(1.0)
        # wind warp masks: the field (bends + flattens), the oak (sways); barn and silo stay rigid
        self.m_field = smooth(1345, 1425, self.yy).astype(f32)
        self.m_oak = ((self.xx < 560) * smooth(1250, 950, self.yy)).astype(f32)
        self.gust = fbm2((256, 512), 61, 2.2)
        self.dust_tex = cv2.GaussianBlur(fbm2((512, 1024), 62, 2.0), (0, 0), sigmaX=6, sigmaY=0.8)
        self.dust_tex = (self.dust_tex / self.dust_tex.std()).astype(f32)
        r = np.random.default_rng(8)
        self.deb = dict(x=r.uniform(0, 1, 160), y=r.uniform(0.05, 0.95, 160), v=r.uniform(0.7, 1.4, 160), s=r.uniform(0.5, 1.5, 160))
        # aurora ray texture (half res)
        rt = cv2.GaussianBlur(fbm2((64, 1024), 71, 1.6), (0, 0), sigmaX=0.6, sigmaY=6)
        self.ray = ((rt - rt.min()) / (rt.max() - rt.min())).astype(f32)
        self.prep_globe()
        emph = {"EARTH", "SPINNING", "EAST", "NOTHING", "SUDDENLY", "AIR", "1,600", "FLATTENED", "SLOWLY", "SUN", "FREEZES", "SIX",
                "MONTHS", "NIGHT", "STARS", "FROST", "OCEANS", "POLES", "TONIGHT", "GLAD"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1390

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- the globe
    def prep_globe(self):
        """Blue Marble (NASA, via three-globe) + its water mask; 2x supersampled sphere with a soft atmosphere rim"""
        TW, TH = 2048, 1024
        self.g_alb = load_lin(os.path.join(GLB, "earth-blue-marble.jpg"), (TW, TH))
        wm = np.asarray(Image.open(os.path.join(GLB, "earth-water.png")).convert("L"), f32) / 255.0
        self.g_ocean = np.clip(cv2.resize(wm, (TW, TH), interpolation=cv2.INTER_CUBIC), 0, 1)
        lat = (0.5 - (np.arange(TH) + 0.5) / TH) * 180.0
        n = cv2.resize(fbm2((128, 256), 81, 2.4), (TW, TH), interpolation=cv2.INTER_CUBIC)
        nf = cv2.resize(fbm2((512, 1024), 82, 1.6), (TW, TH), interpolation=cv2.INTER_CUBIC)
        # no spin -> no equatorial bulge for the water: two polar oceans, one equatorial belt of land (Fraczek 2010, ESRI)
        edge = 38.0 + 6.0 * n
        self.g_new = smooth(-1.5, 1.5, np.abs(lat)[:, None] - edge).astype(f32)
        self.g_seabed = (np.array([0.22, 0.15, 0.085], f32) * (0.8 + 0.18 * n[..., None] + 0.10 * nf[..., None])).astype(f32)
        self.g_water = np.array([0.010, 0.045, 0.16], f32)
        self.g_tw, self.g_th = TW, TH
        pad = int(R_GLOBE * 1.25); self.gpad = pad
        ys, xs = np.mgrid[-pad:pad:0.5, -pad:pad:0.5].astype(f32) + 0.25
        self.g_dx, self.g_dy = xs, ys

    def globe(self, img, t, I, m, scale):
        R = R_GLOBE * scale
        if R < 2: return
        cx, cy = GLOBE; pad = self.gpad; TW, TH = self.g_tw, self.g_th
        u = self.g_dx / R; v = self.g_dy / R; rr = u * u + v * v; r1 = np.sqrt(rr)
        z = np.sqrt(np.clip(1 - rr, 0, 1))
        tilt = math.radians(20)                                            # north pole tipped towards the viewer
        yy_ = -v * math.cos(tilt) + z * math.sin(tilt); zz = v * math.sin(tilt) + z * math.cos(tilt)
        lat = np.arcsin(np.clip(yy_, -1, 1)); lon = np.arctan2(u, zz) + 0.06 * t - 0.4
        mx = ((lon / (2 * np.pi) + 0.5) % 1.0 * TW).astype(f32); my = np.clip((0.5 - lat / np.pi) * TH - 0.5, 0, TH - 1).astype(f32)
        alb = cv2.remap(self.g_alb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        oc = cv2.remap(self.g_ocean, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        nw = cv2.remap(self.g_new, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        sb = cv2.remap(self.g_seabed, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        # the water front moves from the old oceans to the poles: the sea floor drains first, then the polar seas fill
        drain = oc * (1 - nw) * ease(m * 1.4)
        fill = nw * (1 - oc) * ease(m * 1.4 - 0.4)
        water = np.clip(oc - drain + fill, 0, 1)[..., None]
        land = alb * (1 - oc[..., None]) + sb * oc[..., None]
        wcol = alb * oc[..., None] + self.g_water * (1 - oc[..., None])            # keep the real ocean colour where it was
        col = land * (1 - water) + wcol * water
        L_ = np.array([-0.70, -0.30, 0.65]); L_ /= np.linalg.norm(L_)
        ndl = u * L_[0] + v * L_[1] + z * L_[2]
        lit = smooth(-0.10, 0.22, ndl) * np.clip(ndl + 0.08, 0, 1) ** 0.6
        disc = np.clip((1 - r1) * R * 2 + 0.5, 0, 1)
        rad = col * (lit * 1.5 + 0.015)[..., None]
        sunside = smooth(-0.35, 0.45, (u * L_[0] + v * L_[1]) / (r1 + 1e-6) * 0.8 + 0.2)
        limb = (1 - z) ** 3 * sunside * (r1 < 1)                                 # blue limb haze inside the disc
        halo = np.exp(-np.maximum(r1 - 1, 0) * R / 9.0) * (r1 >= 1) * sunside       # thin glowing shell outside
        atm = np.array([0.30, 0.55, 1.0], f32)
        rad = rad * disc[..., None] + (limb * 0.45 * disc + halo * 0.55)[..., None] * atm
        cov = disc
        sz = (2 * pad, 2 * pad)
        rad = cv2.resize(rad, sz, interpolation=cv2.INTER_AREA); cov = cv2.resize(cov, sz, interpolation=cv2.INTER_AREA)
        y0, x0 = int(cy) - pad, int(cx) - pad
        reg = img[y0:y0 + 2 * pad, x0:x0 + 2 * pad]
        img[y0:y0 + 2 * pad, x0:x0 + 2 * pad] = reg * (1 - cov[..., None]) + rad * I

    # -------------------------------------------------------------------------------------------- pieces
    def params(self, t):
        cur, t0, t1 = scene_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "day" if i == 0 else SWAPS[i - 1][1]
        B = LOOK[cur]
        if prev is None: w, A = 1.0, B
        else: w = ramp(t, t0 - 0.12, t0 + 0.55); A = LOOK[prev]
        P = {k: lerp(A[k], B[k], w) for k in NUM}
        P["beamsA"], P["beamsB"], P["bw"] = A["beams"], B["beams"], w
        return P, cur, t0, t1

    def sun(self, img, x, y, I, glow=1.0):
        r = R_SUN
        def fn(d, dx, dy):
            disc = smooth(r + 0.7, r - 0.7, d) * (1 - 0.5 * (1 - np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))))
            g = (np.exp(-d / 6) * 6 + np.exp(-d / 30) * 1.2 + np.exp(-d / 120) * 0.25) * glow
            return (disc * 60 + g * (d > r - 1))[..., None] * np.array([1.0, 0.93, 0.80], f32) * I
        splat(img, x, y, 420, fn)

    def aurora(self, t, I):
        """green curtains with red tops, folding slowly (half res)"""
        x, y = self.hx, self.hy
        fold = x + 70 * np.sin(x * 0.005 + t * 0.25) + 30 * np.sin(x * 0.013 - t * 0.4)
        base = 780 + 70 * np.sin(fold * 0.004 + 1.0) - 0.08 * (x - 540)
        h = base - y
        u = ((fold * 0.9 + t * 14) % 1024).astype(f32); vv = np.clip(h / 900 * 63, 0, 63).astype(f32)
        rays = cv2.remap(self.ray, u, vv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        body = smooth(-25, 25, h) * (np.exp(-np.maximum(h, 0) / 170)) * (0.35 + 1.1 * rays ** 2)
        top = smooth(-25, 25, h) * np.exp(-np.maximum(h - 120, 0) / 330) * smooth(60, 260, h) * (0.3 + 0.8 * rays)
        band = 0.55 + 0.45 * np.sin(x * 0.0045 - t * 0.2)
        return ((body * band)[..., None] * np.array([0.05, 0.55, 0.22], f32) + (top * band)[..., None] * np.array([0.30, 0.03, 0.16], f32)) * I

    def wind_warp(self, fgc, a, t, s):
        """bend + flatten the wheat, sway the oak (rgb and alpha remapped together), then streak it"""
        g = cv2.remap(self.gust, ((self.xx * 0.25 - t * 220) % 512).astype(f32), ((self.yy * 0.12) % 256).astype(f32), cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_WRAP)
        k = s * (0.75 + 0.25 * g)
        yf = np.clip((self.yy - 1300) / 620, 0, 1)
        dx = self.m_field * k * (34 + 30 * (1 - yf)) + self.m_oak * k * 70 * smooth(1250, 600, self.yy) * (1 + 0.15 * math.sin(t * 7))
        dy = self.m_field * k * 26 * np.sin(np.pi * yf) ** 0.8
        mx = self.xx - dx; my = self.yy - dy
        fgc = cv2.remap(fgc, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        a = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        ker = np.zeros((1, 45), f32); ker[0, :] = 1 / 45
        bl = cv2.filter2D(fgc, -1, ker)
        mm = (np.clip(self.m_field + self.m_oak * 0.6, 0, 1) * min(s, 1.0) * 0.8)[..., None]
        return fgc * (1 - mm) + bl * mm, a

    def wilt(self, fgc, a, t, k):
        """the long day bakes the farm: the wheat heads droop, heat shimmer low over the field"""
        yf = np.clip((self.yy - 1300) / 620, 0, 1)
        dy = self.m_field * k * 30 * np.sin(np.pi * yf) ** 0.8
        sh = smooth(1150, 1250, self.yy) * smooth(1450, 1320, self.yy) * 1.6 * k
        dx = sh * np.sin(self.yy * 0.21 + t * 11.0) + self.m_field * k * 6 * np.sin(self.xx * 0.02)
        mx = self.xx - dx; my = self.yy - dy
        return cv2.remap(fgc, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), \
            cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def dust(self, t, s):
        """horizontally streaming dust sheets + flying debris, in front of everything (full res mask)"""
        u = ((self.hx * 0.45 - t * 700) % 1024).astype(f32); v = ((self.hy * 0.25) % 512).astype(f32)
        n1 = cv2.remap(self.dust_tex, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        n2 = cv2.remap(self.dust_tex, ((self.hx * 0.9 - t * 1500) % 1024).astype(f32), ((self.hy * 0.6 + 200) % 512).astype(f32),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        dens = np.clip(0.30 + 0.22 * n1 + 0.12 * n2, 0, 1) * s
        dens = dens * (0.55 + 0.45 * np.exp(-np.abs(self.hy - self.hz) / 400))
        lay = np.zeros(self.hx.shape, f32); W = self.L.W; H = self.L.H
        d = self.deb
        for i in range(len(d["x"])):
            x = ((d["x"][i] + t * 1.1 * d["v"][i]) % 1.2 - 0.1) * W / 2; y = d["y"][i] * H / 2 + 6 * math.sin(t * 9 + i)
            L_ = 14 * d["v"][i] * s
            cv2.line(lay, (int(x - L_), int(y)), (int(x), int(y + 1)), float(0.8 * d["s"][i] * s), max(1, int(d["s"][i] * 1.2)), cv2.LINE_AA)
        return self.up(dens), self.up(lay)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        P, cur, t0, t1 = self.params(t)
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        sc = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if (t1 > 1e8 or t1 >= T_BACK - 1e-6) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        sw = wind(t)
        # ---- sky
        sky = np.array(P["zen"], f32) * (1 - self.k_hor) + np.array(P["hor"], f32) * self.k_hor
        sky = sky * (1 + 0.04 * (pulse - 1))
        nI = P["night"]
        if cur in ("day", "day2", "slow") or (cur == "stop" and t < t0 + 0.6):
            if cur == "slow":
                u = ease(min(max((t - t0) / (T_FREEZE + 0.2 - t0), 0), 1))     # sweeps up fast, slows, stops on "freezes"
                sx, sy = sun_path(u)
            else: sx, sy = SUN_DAY
            self.sun_xy = (sx, sy)
            dd = np.sqrt((self.hx - sx) ** 2 + (self.hy - sy) ** 2)
            aure = np.exp(-dd / 60) * 0.7 + np.exp(-dd / 260) * 0.12 + np.exp(-dd / 800) * 0.05
            sky = sky + (aure * (1.8 if cur == "slow" else 1.0) * (1 - P["dust"]))[..., None] * np.array([1.0, 0.92, 0.78], f32)
        else: self.sun_xy = SUN_DAY
        bc = self.sun_xy if cur in ("day", "day2", "slow", "stop") else (GLOBE if cur == "sea" else (560.0, 560.0))
        bm = self.beams.layer(t, bc, P["beamsB"] if P["bw"] >= 1 else P["beamsA"], P["bI"] * pulse, col_u)
        if nI > 0:
            sky = sky + self.aurora(t, 1.0 * ramp(t, T_SW["night"] + 0.3, T_SW["night"] + 1.6) * (0.55 if cur == "sea" else 1.0)) * nI
        img = self.up(sky + bm)
        if nI > 0:
            img = img + self.stars.render(self.cam, t, rot=t * 0.15, gain=1.0, plate_gain=0.55) * nI
        if cur in ("day", "day2", "slow"):
            self.sun(img, *self.sun_xy, (1.0 + 0.3 * (pulse - 1)) * (1.4 if cur == "slow" else 1.0))
        if cur == "sea":
            m = ramp(t, T_DRAIN, T_DRAIN1)
            self.globe(img, t, 1.0 * (1 + 0.15 * (pulse - 1)), m, sc * (1 - 0.95 * ease(col_u)))
        if cur == "slow":                                       # time-lapse ghosts of the Sun's arc, stalling to a stop
            u = ease(min(max((t - t0) / (T_FREEZE + 0.2 - t0), 0), 1))
            fade = 0.35 + 0.65 * (1 - ramp(t, T_FREEZE + 0.6, T_FREEZE + 2.5))
            for j in range(16):
                uj = (j / 16) ** 0.55
                if uj >= u - 0.02: break
                gx, gy = sun_path(uj)
                self.sun(img, gx, gy, 0.16 * (0.35 + 0.65 * j / 16) * fade, glow=0.6)
        # ---- foreground
        light = 1.0 + 0.08 * (pulse - 1) - 0.2 * col_u
        base = fg.rgb * (1 - P["flat"]) + fg.flat * P["flat"]
        day = base * np.array(P["tint"], f32) * P["gain"] + fg.flat * np.array(P["amb"], f32)
        if P["bleach"] > 0:                                     # sun-baked, bleached wheat
            yv = lum(day)[..., None]
            k = (P["bleach"] * self.wheat * ramp(t, T_SW["slow"] + 0.5, T_SW["slow"] + 4.5))[..., None]
            day = day * (1 - 0.7 * k) + (yv * np.array([1.05, 0.78, 0.45], f32)) * 0.7 * k      # baked, browning wheat
        day = day + (self.rim * 0.08 * P["gain"])[..., None]
        fgc = day * (1 - nI)
        if nI > 0:
            ng = self.night_fg * 0.085
            if cur in ("night", "sea"):
                ng = fg.frost(ng, ramp(t, T_FROST - 0.3, T_FROST + 2.5) if cur == "night" else 1.0, t, level=0.085)
            aur = np.array([0.05, 0.30, 0.14], f32) * 0.02 * ramp(t, T_SW["night"] + 0.3, T_SW["night"] + 1.6)
            fgc = fgc + (ng + fg.flat * aur) * nI
        fgc = fgc * light + self.up(bm) * 0.04 * fg.a[..., None]
        a = self.a_hard
        if sw > 0.01: fgc, a = self.wind_warp(fgc, a, t, sw)
        wl = P["bleach"] * ramp(t, T_SW["slow"] + 0.8, T_SW["night"] - 0.5) if cur == "slow" else 0.0
        if wl > 0.01: fgc, a = self.wilt(fgc, a, t, wl)
        a = a[..., None]
        img = img * (1 - a) + fgc * a
        if sw > 0.01:
            dens, deb = self.dust(t, sw)
            dcol = np.array([0.42, 0.29, 0.16], f32) * P["gain"] * 1.4
            img = img * (1 - 0.75 * dens[..., None]) + dcol * dens[..., None] * 0.9 + deb[..., None] * np.array([0.06, 0.04, 0.025], f32) \
                - deb[..., None] * img * 0.6
            img = np.maximum(img, 0)
        # ---- swaps
        for ts, k in SWAPS:
            if k == "day2": continue
            u = t - ts
            fc = np.array(FC[k], f32); cx, cy = (GLOBE if k == "sea" else SUN_DAY if k in ("stop", "slow") else (560.0, 560.0))
            self.fx.flash(img, u, fc); self.fx.shock(img, cx, cy, u, fc)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([1.0, 0.95, 0.88], f32)
            self.fx.shock(img, *SUN_DAY, t - T_BACK, np.array([1.0, 0.9, 0.7], f32))
        img = self.fx.chroma_bloom(img, 1.0)
        out = tonemap(img, P["expo"])
        if sw > 0.3:                                           # the tripod is buffeted (a couple of px)
            M = np.float32([[1, 0, 2.5 * sw * noise1(t, 3, 11.0, 2)], [0, 1, 2.0 * sw * noise1(t, 4, 13.0, 2)]])
            out = cv2.warpAffine(out, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        out = self.fx.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
        return out

    def overlay(self, out, t, cur, t0):
        key = "day" if cur == "day2" else cur
        if cur == "day": t0 = 0.0
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "day2": a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if T_WO0 < t < T_BACK: a = 0.0
        name, l2, l3, tc = RO[key]
        if cur == "slow" and t > T_FREEZE + 0.3:                 # the day counter: the Sun stays put
            n = 1 + int(179 * ramp(t, T_FREEZE + 0.3, T_SW["night"] - 0.6) ** 1.3)
            l2, l3 = f"DAY {n} · SUN STILL HERE", "1 DAY = 1 YEAR · IT WOULD RISE IN THE WEST"
        readout(out, self.L, a, name, l2, l3, tc)
        self.caps.draw(out, t)


def save_png(im, path):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "R_SUN", round(R_SUN, 2), {k: round(v, 2) for k, v in T_SW.items()}, "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    sc = Scene(True); d = os.path.join(SCR, "stills"); os.makedirs(d, exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); save_png(sc.frame(t), os.path.join(d, f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
