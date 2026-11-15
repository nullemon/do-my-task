"""WHAT IF A BLACK HOLE PASSED THROUGH THE SOLAR SYSTEM? -- one locked tripod shot of the city at night
(04_city_street_at_night; the sky is a narrow strip up the middle), swap format (BATCH4).
A 10 M_sun stellar black hole drifts through at 50 km/s. At its true size it is invisible (59 km across), so the sky strip
carries a TELESCOPE VIEW: a circular inset centred on the hole, in which background stars are lensed by exact
Schwarzschild ray tracing (../black-hole-suns/lens.py, via lensmap.py). The Einstein ring grows as the hole closes in.
  city night -> the hole (stars bend) -> it crosses Neptune's orbit -> past the Sun (it glows: accreted solar-wind gas)
  -> Earth's orbit stretched -> it recedes -> white-out -> city night (the odds; loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py segs | vert 1.0,9.5 | info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from scipy.spatial import cKDTree
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1, bbcolor
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text
from lib.post import tonemap, finish
from lib.audio import place
from lib.swapfx_b4 import Beams, FX, readout, back_out, lerp
import lensmap

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-black-hole-flyby"
BG = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/04_city_street_at_night.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 1150.0                     # the plate's lens (as in rogue-planet): ~80 deg vertical
YH = 1366.0                       # eye level (the street's vanishing point)
INS = (560.0, 665.0); RI = 205; IM = 34   # telescope inset: centre, radius (px)
MUSIC_KEY = "A"
RS_KM, AU_KM = 2.9533 * 10.0, 1.495978707e8

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


ORDER = ["bh", "nep", "sun", "earth", "gone"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER}
T_BACK = LN["end"]["start"] - 0.08
T_WO0 = T_BACK - 0.70
SWAPS = [(T_SW[k], k) for k in ORDER] + [(T_BACK, "city2")]
SWAP_TIMES = [ts for ts, _ in SWAPS]
T_BEND = wt("bh_d", "BEND")
T_GLOW = wt("sun_b", "GLOWING")
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook", "BLACK"), wt("bh", "TEN"), wt("bh_b", "SIXTY"), T_BEND, wt("nep", "NEPTUNE'S"), wt("nep_b", "WOBBLE"),
          wt("sun", "SUN"), wt("sun_b", "GAS"), wt("earth_b", "STRETCHED"), wt("earth_b", "FLUNG"), wt("gone", "GONE")]

# distance hole -> Earth (AU), from the N-body run in science.py (b = 4 AU, closest 1.65 AU to the Sun, 0.75 AU to Earth)
D_KEYS = [(0.0, 80.0), (T_SW["bh"], 60.0), (T_SW["nep"] - 0.01, 33.0), (T_SW["nep"], 31.0), (T_SW["sun"] - 0.01, 21.0),
          (T_SW["sun"], 1.6), (T_SW["earth"] - 0.01, 1.05), (T_SW["earth"], 0.95), (T_SW["gone"] - 0.01, 0.75), (T_SW["gone"], 0.9),
          (T_BACK, 3.5)]


def dist_au(t):
    return float(np.interp(t, [k for k, _ in D_KEYS], [v for _, v in D_KEYS]))


def theta_E(t):
    """Einstein angle (arcmin) for a source at infinity: sqrt(2 Rs / D)"""
    return math.degrees(math.sqrt(2 * RS_KM / (dist_au(t) * AU_KM))) * 60


FOVN = 1.75                      # inset field radius in Einstein radii: the ring sits at 57 % of the inset radius
SHADOW = 0.20                     # drawn shadow radius (theta_E units); a liberty, see README
PATH_V = 0.55                     # the hole's motion across the background (theta_E per second, time-compressed)


def fov(t):
    """inset field radius (arcmin)"""
    return FOVN * theta_E(t)


# ------------------------------------------------------------------------------------------------ looks
LOOK = {
    "city": dict(zen=(0.006, 0.009, 0.034), tint=(1.0, 1.0, 1.0), rimk=0.0, glow=(0.6, 0.5, 1.0), beams=[(0.5, 0.4, 1.0)], bI=0.0, ins=0.0, acc=0.0),
    "bh": dict(zen=(0.012, 0.008, 0.050), tint=(0.75, 0.55, 1.0), rimk=0.6, glow=(0.6, 0.4, 1.0),
               beams=[(0.55, 0.30, 1.0), (0.30, 0.45, 1.0), (0.85, 0.35, 1.0), (0.4, 0.8, 1.0)], bI=0.7, ins=1.0, acc=0.0),
    "nep": dict(zen=(0.006, 0.014, 0.060), tint=(0.45, 0.65, 1.0), rimk=0.6, glow=(0.35, 0.55, 1.0),
                beams=[(0.25, 0.45, 1.0), (0.30, 0.85, 1.0), (0.55, 0.45, 1.0), (0.2, 0.6, 0.9)], bI=0.7, ins=1.0, acc=0.0),
    "sun": dict(zen=(0.022, 0.012, 0.030), tint=(1.0, 0.62, 0.30), rimk=0.9, glow=(1.0, 0.62, 0.30),
                beams=[(1.0, 0.55, 0.20), (1.0, 0.80, 0.45), (1.0, 0.35, 0.25), (0.9, 0.5, 0.8)], bI=0.9, ins=1.0, acc=1.0),
    "earth": dict(zen=(0.030, 0.008, 0.022), tint=(1.0, 0.35, 0.25), rimk=1.1, glow=(1.0, 0.35, 0.30),
                  beams=[(1.0, 0.25, 0.20), (1.0, 0.55, 0.25), (0.9, 0.25, 0.6), (1.0, 0.8, 0.5)], bI=1.0, ins=1.0, acc=1.3),
    "gone": dict(zen=(0.010, 0.008, 0.042), tint=(0.6, 0.45, 1.0), rimk=0.4, glow=(0.6, 0.45, 1.0),
                 beams=[(0.5, 0.35, 1.0), (0.35, 0.5, 1.0)], bI=0.35, ins=1.0, acc=0.4),
}
LOOK["city2"] = LOOK["city"]
NUM = ("zen", "tint", "rimk", "glow", "bI", "acc")
RO = {"bh": ("STELLAR BLACK HOLE", "10× THE SUN'S MASS · 59 KM WIDE", None, (200, 160, 255)),
      "nep": ("NEPTUNE'S ORBIT", "30 AU FROM THE SUN", "ITS PULL ON NEPTUNE: UP TO 90× THE SUN'S", (130, 180, 255)),
      "sun": ("PAST THE SUN", "CLOSEST: 1.65 AU", "SOLAR-WIND GAS FALLS IN · IT COULD OUTSHINE VENUS", (255, 175, 90)),
      "earth": ("EARTH'S ORBIT", "1 AU → 0.56–3.4 AU", "A SLIGHTLY CLOSER PASS EJECTS EARTH", (255, 120, 100)),
      "gone": ("IT'S GONE", "50 KM/S · BACK TO INTERSTELLAR SPACE", None, (200, 170, 255)),
      "city2": ("THE ODDS", "~1 IN 250,000 OVER THE SUN'S LIFE", "~100 MILLION BLACK HOLES IN OUR GALAXY", (255, 210, 120))}
FC = {"bh": (0.7, 0.5, 1.0), "nep": (0.45, 0.65, 1.0), "sun": (1.0, 0.7, 0.4), "earth": (1.0, 0.45, 0.35), "gone": (0.7, 0.6, 1.0)}


def scene_at(t):
    cur, t0 = "city", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(BG, L, hz_frac=0.84)
        self.fx = FX(W, H); self.beams = Beams(W, H, seed=9)
        self.cam = SkyCam(W, H, YH, F_PX); self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.e = np.maximum(np.degrees(np.arctan2(YH - yy, F_PX)), 0).astype(f32)
        self.xx, self.yy = self.fx.xx, self.fx.yy
        a = fg.a
        self.a_hard = np.clip(a / 0.9, 0, 1).astype(f32)
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 4.0) * a
        self.up_w = (np.clip(1 - self.yy / 1300, 0, 1) ** 0.8 * a).astype(f32)
        Y = lum(fg.rgb)
        gloss = np.clip(cv2.GaussianBlur(Y, (0, 0), 3) * 6, 0.2, 1.0)
        self.wet = (smooth(YH + 20, YH + 90, self.yy) * gloss * a).astype(f32)
        # ---- the telescope inset: lens table + a dense star field in units of the Einstein angle (source plane)
        self.lx, self.ly = lensmap.table()
        r = np.random.default_rng(21)
        n = 50000                                                           # ~110 stars per theta_E^2 (a rich Milky Way field)
        self.sp = np.stack([r.uniform(-4, 36, n), r.uniform(-5.5, 5.5, n)], 1).astype(f32)
        self.sf = (0.11 * r.uniform(0, 1, n) ** (-1 / 1.1)).clip(0, 30).astype(f32)
        T = np.clip(r.lognormal(np.log(5600), 0.40, n), 3000, 22000)
        self.sc = np.stack([bbcolor(x) for x in T]).astype(f32) * 0.55 + 0.45
        tt = np.linspace(0, DUR + 1, 2000); rate = np.array([PATH_V for x in tt])
        self.path_t = tt; self.path_x = np.concatenate([[0], np.cumsum(rate[1:] * np.diff(tt))]).astype(f32)
        # a bright star placed so the hole slides right over it on "BEND": a full Einstein ring
        px = float(np.interp(T_BEND + 0.15, tt, self.path_x))
        self.sp = np.vstack([self.sp, [[px, 0.025]]]).astype(f32)
        self.sf = np.append(self.sf, 40.0).astype(f32); self.sc = np.vstack([self.sc, [[1.0, 0.95, 1.0]]]).astype(f32)
        self.tree = cKDTree(self.sp)
        self.glow_tex = cv2.resize(fbm2((64, 64), 23, 2.2), (512, 512), interpolation=cv2.INTER_CUBIC)
        self.swirl_tex = cv2.GaussianBlur(fbm2((256, 256), 24, 1.8), (0, 0), 1.2)
        g = np.mgrid[-RI - IM:RI + IM, -RI - IM:RI + IM].astype(f32) + 0.5
        self.iy, self.ix = g[0], g[1]
        self.ir = np.sqrt(self.ix ** 2 + self.iy ** 2)
        emph = {"BLACK", "HOLE", "TEN", "SIXTY", "BEND", "NEPTUNE'S", "WOBBLE", "SUN", "STOLEN", "GAS", "EARTH'S", "STRETCHED", "FLUNG",
                "GONE", "ZERO", "HUNDRED", "MILLION"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1150

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def params(self, t):
        cur, t0, t1 = scene_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "city" if i == 0 else SWAPS[i - 1][1]
        B = LOOK[cur]
        if prev is None: w, A = 1.0, B
        else: w = ramp(t, t0 - 0.12, t0 + 0.55); A = LOOK[prev]
        P = {k: lerp(A[k], B[k], w) for k in NUM}
        P["beams"] = B["beams"] if w > 0.5 else A["beams"]
        return P, cur, t0, t1

    # -------------------------------------------------------------------------------------------- the inset
    def inset(self, t, I, scale, acc):
        """telescope view centred on the hole, in units of theta_E: inverse ray shooting through the traced lens table
        (lensmap.py <- ../black-hole-suns/lens.py), analytic star sources (KD-tree), lensed Milky Way glow"""
        k = FOVN / (RI * scale + 1e-6)                                                # theta_E per inset px
        th = self.ir * k + 1e-6
        y = np.interp(th, self.lx, self.ly)                                           # signed source radius (theta_E)
        bx = self.ix * k / th * y; by = self.iy * k / th * y
        p0 = float(np.interp(t, self.path_t, self.path_x))
        src = np.stack([bx.ravel() + p0, by.ravel() + 0.15 * math.sin(t * 0.07)], 1)
        sig = max(0.9 * k, 0.004)                                                     # seeing: ~0.9 px in the image
        d, idx = self.tree.query(src, k=4, distance_upper_bound=4 * sig)
        ok = np.isfinite(d)
        idx = np.where(ok, idx, 0); w = np.exp(-0.5 * (np.where(ok, d, 9e9) / sig) ** 2) * ok
        img = np.einsum("nk,nkc->nc", w * self.sf[idx], self.sc[idx]).reshape(self.ix.shape + (3,)).astype(f32)
        gx = ((bx + p0) * 40 % 512).astype(f32); gy = ((by + 9) * 40 % 512).astype(f32)
        gl = cv2.remap(self.glow_tex, gx, gy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        img += (0.010 + 0.008 * np.clip(gl, -1, 3))[..., None] * np.array([0.60, 0.62, 1.0], f32)
        rn = th
        # accretion: captured solar-wind gas swirling in (orange inside, violet outside); Bondi radius ~0.09 AU ~ 2 theta_E
        if acc > 0:
            ang = np.arctan2(self.iy, self.ix)
            u = ((ang / (2 * np.pi) * 256 * 2 + 70 * np.log(rn + 0.05) - t * 26) % 256).astype(f32)
            v = ((40 * np.log(rn + 0.05) + t * 3) % 256).astype(f32)
            sw = cv2.remap(self.swirl_tex, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            env = np.exp(-np.maximum(rn - SHADOW, 0) / 0.32) * smooth(SHADOW * 0.95, SHADOW * 1.25, rn)
            arms = np.clip(0.55 + 0.45 * sw, 0, 2) ** 2
            cmix = smooth(0.25, 0.75, rn)[..., None]
            col = np.array([1.0, 0.52, 0.18], f32) * (1 - cmix) + np.array([0.62, 0.30, 1.0], f32) * cmix
            img += (env * arms * 0.9 * acc)[..., None] * col
        # the shadow (drawn ~0.2 theta_E so it reads; true size ~0.001 theta_E) with a thin photon ring
        img *= smooth(SHADOW * 0.93, SHADOW * 1.02, rn)[..., None]
        img += (np.exp(-np.abs(rn - SHADOW * 1.03) / 0.008) * 0.9)[..., None] * np.array([1.0, 0.85, 0.75], f32) * (0.4 + 0.6 * min(acc, 1.0) + 0.3)
        return img * I

    def place_inset(self, img, t, I, scale, acc, tint):
        if scale < 0.02: return
        R = RI * scale
        ins = self.inset(t, I, scale, acc)
        cx, cy = INS; x0, y0 = int(cx) - RI - IM, int(cy) - RI - IM
        circ = smooth(R + 1.0, R - 1.0, self.ir)[..., None]
        reg = img[y0:y0 + 2 * (RI + IM), x0:x0 + 2 * (RI + IM)]
        rimc = (np.exp(-np.abs(self.ir - R) / 1.6) * 1.6 + np.exp(-np.abs(self.ir - R) / 10) * 0.25)[..., None] * np.array(tint, f32) * I
        ticks = ((np.abs(self.ix) < 1.2) | (np.abs(self.iy) < 1.2)) * (self.ir > R * 0.80) * (self.ir < R * 0.93)
        img[y0:y0 + 2 * (RI + IM), x0:x0 + 2 * (RI + IM)] = reg * (1 - circ * 0.97) + ins * circ + rimc + (ticks * 0.25 * scale)[..., None] * np.array(tint, f32)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        P, cur, t0, t1 = self.params(t)
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        col_u = 0.0 if (t1 > 1e8 or t1 >= T_BACK - 1e-6) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        # inset size: blooms in at the first swap, shrinks shut as the hole leaves
        s_in = 0.0
        if T_SW["bh"] <= t < T_BACK:
            s_in = back_out((t - T_SW["bh"]) / 0.8) * (1 - 0.35 * ramp(t, T_SW["gone"] + 0.3, T_BACK - 0.2))
            s_in *= 1 + 0.03 * (pulse - 1)
        acc = P["acc"] * ramp(t, T_GLOW - 0.4, T_GLOW + 0.3) * (1 + 0.6 * (pulse - 1)) if t > T_SW["sun"] else 0.0
        acc *= 1 - ramp(t, T_SW["gone"] + 0.2, T_BACK - 0.3)
        # ---- sky
        zen = np.array(P["zen"], f32)
        sky = zen * (0.75 + 0.25 * np.exp(-self.e / 30))[..., None]
        sky += np.array([0.050, 0.026, 0.020], f32) * np.exp(-self.e / 10)[..., None]
        sky += np.array([0.020, 0.012, 0.040], f32) * np.exp(-self.e / 22)[..., None]
        if s_in > 0:
            dd = np.maximum(np.sqrt((self.hx - INS[0]) ** 2 + (self.hy - INS[1]) ** 2) - RI * s_in, 0)
            sky += (np.exp(-dd / 90) * 0.06 + np.exp(-dd / 400) * 0.02)[..., None] * np.array(P["glow"], f32) * (0.5 + 0.5 * pulse)
        bm = self.beams.layer(t, INS, P["beams"], P["bI"] * pulse, col_u, reach=1100.0) if P["bI"] > 0.01 else 0.0
        img = self.up(sky + bm)
        img += self.stars.render(self.cam, t, gain=1.0, twinkle=1.4, plate_gain=0.10, star_gain=1.0, cx=1500, cy=700, rot=-8.0) * 0.9
        tint = np.array(P["tint"], f32)
        self.place_inset(img, t, 1.0 + 0.2 * (pulse - 1), s_in * (1 - 0.6 * ease(col_u)), acc, 0.5 + 0.5 * tint)
        if acc > 0:                                                    # the glow lights the sky strip a little
            splat(img, INS[0], INS[1], 600, lambda d, dx, dy: (np.exp(-d / 120) * 0.05 * acc)[..., None] * np.array([1.0, 0.75, 0.5], f32))
        sky_img = img
        # ---- city: relit by the beat's light on the upper facades and edges
        base = fg.rgb * 1.05
        base = base + (fg.flat * self.up_w[..., None] * 0.10 + self.rim[..., None] * 0.25) * tint * P["rimk"] * (0.8 + 0.4 * (pulse - 1))
        base = base + (fg.flat * self.up_w[..., None] * 0.06) * np.array([1.0, 0.75, 0.5], f32) * acc
        # wet street mirrors the sky (rough lobe), as in rogue-planet
        y0 = int(YH); ys = self.yy[y0:]; xs = self.xx[y0:]
        sy = np.clip(YH - (ys - YH) * 1.6, 0, YH - 1).astype(f32)
        sm = cv2.GaussianBlur(cv2.resize(sky_img, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), sigmaX=2, sigmaY=12)
        refl = cv2.remap(sm, (xs / 2).astype(f32), (sy / 2).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        base[y0:] += refl * (0.30 * self.wet[y0:])[..., None]
        if P["bI"] > 0.01: base = base + self.up(bm) * 0.04 * fg.a[..., None]
        a = self.a_hard[..., None]
        img = sky_img * (1 - a) + base * a
        # ---- swaps
        for ts, k in SWAPS:
            if k == "city2": continue
            u = t - ts; fc = np.array(FC[k], f32)
            self.fx.flash(img, u, fc, k=2.2); self.fx.shock(img, *INS, u, fc)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([0.92, 0.90, 1.0], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([0.92, 0.90, 1.0], f32)
            self.fx.shock(img, *INS, t - T_BACK, np.array([0.8, 0.8, 1.0], f32))
        img = self.fx.chroma_bloom(img, 1.0)
        out = tonemap(img, 1.0)
        out = self.fx.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0, s_in)
        return out

    def overlay(self, out, t, cur, t0, s_in):
        if cur != "city":
            a = ramp(t, t0 + 0.15, t0 + 0.45)
            nxt = [ts for ts, k in SWAPS if ts > t]
            if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
            if cur == "city2": a *= 1 - ramp(t, DUR - 0.9, DUR - 0.4)                     # gone again before the loop point
            if T_WO0 < t < T_BACK: a = 0.0
            name, l2, l3, tc = RO[cur]
            if cur == "bh": l3 = f"EINSTEIN RING {2 * theta_E(t):.1f}′ ACROSS"
            readout(out, self.L, a, name, l2, l3, tc)
        if s_in > 0.6 and cur != "city2":                                           # the inset's own label: zoom vs the plate
            zoom = RI / math.radians(fov(t) / 60) / F_PX
            hud_text(out, f"TELESCOPE ×{int(round(zoom, -1))}", INS[0], INS[1] + RI + 26, int(self.L.hud_size * 0.40), "Bold",
                     (220, 225, 255), min(1.0, (s_in - 0.6) * 3), 0.14, display=True)
        self.caps.draw(out, t)


def save_png(im, path):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, {k: round(v, 2) for k, v in T_SW.items()}, "back", round(T_BACK, 2), "bend", round(T_BEND, 2))
        for tt in (T_SW["bh"] + 1, T_BEND, T_SW["nep"] + 1, T_SW["sun"] + 1, T_SW["earth"] + 1.5):
            print(f"t={tt:.1f} D={dist_au(tt):.2f} AU thE={theta_E(tt):.2f}' fov={fov(tt):.2f}'"); sys.exit() if False else None
        sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    sc = Scene(True); d = os.path.join(SCR, "stills"); os.makedirs(d, exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); save_png(sc.frame(t), os.path.join(d, f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
