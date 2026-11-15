"""THE SKY FROM OTHER MOONS -- one locked tripod shot of the tropical beach (05_tropical_beach), swap format (BATCH4).
The beach stays the stage; its sky becomes the sky above each moon, with the giant planet at its TRUE angular size as seen
from that moon's surface (sub-planet point), all through one fixed lens (f = 1700 px, 59 deg vertical field of view):
  Earth (our Moon, 0.52 deg) -> Europa (Jupiter 12.3 deg) -> Titan (orange haze, then above it: Saturn 5.7 deg, rings
  almost edge-on) -> Triton (Neptune 8.0 deg) -> Charon (Pluto 7.2 deg, fixed in the sky) -> Phobos (Mars 42.5 deg)
  -> white-out -> Earth (loops)
Planet maps and the Saturn ring profile come from ../planets-as-moon (planets.py, copied with a per-body Sun direction).
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py segs | vert 1.0,9.5 | info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions
from lib.post import tonemap, finish
from lib.audio import place
from lib.swapfx_b4 import Beams, FX, readout, back_out, lerp
from planets import Body, pole_vec

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-moons-sky-views"
BG = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/05_tropical_beach.png"
PLUTO = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/pluto/pluto_map.jpg"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 1700.0
MUSIC_KEY = "D"
PC = (395.0, 640.0)                       # where each planet hangs (clear sky, left of the palms)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_sph(R, d): return F_PX * math.tan(math.asin(R / d))
def deg_sph(R, d): return 2 * math.degrees(math.asin(R / d))


# planet radius (equatorial, km) and distance from the moon's sub-planet surface point (orbit radius - moon radius, km)
GEOM = {"moon": (1737.4, 384400.0), "eur": (71492.0, 671100.0 - 1560.8), "tit": (60268.0, 1221870.0 - 2574.7),
        "tri": (24764.0, 354759.0 - 1353.4), "cha": (1188.3, 19596.0 - 606.0), "pho": (3396.2, 9376.0 - 13.0)}
RPX = {k: rad_sph(*v) for k, v in GEOM.items()}
DEG = {k: deg_sph(*v) for k, v in GEOM.items()}
A_RING_OUT = 136775.0

ORDER = ["eur", "tit", "tri", "cha", "pho"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER}
T_BACK = LN["end"]["start"] - 0.08
T_WO0 = T_BACK - 0.70
SWAPS = [(T_SW[k], k) for k in ORDER] + [(T_BACK, "home2")]
SWAP_TIMES = [ts for ts, _ in SWAPS]
T_RISE = wt("tit_c", "RISE")
T_THERE = wt("tit_c", "THERE")
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook", "MOON"), wt("hook_b", "UP"), wt("eur_b", "JUPITER"), wt("eur_c", "24×"), wt("tit_b", "HAZE"), T_THERE,
          wt("tit_c", "RINGS"), wt("tri_b", "NEPTUNE"), wt("tri_b", "BLUE"), wt("cha_b", "PLUTO"), wt("cha_b", "NEVER"),
          wt("pho_b", "MARS"), wt("pho_c", "80×"), wt("end_b", "TINY"), wt("end_c", "OURS")]

# ------------------------------------------------------------------------------------------------ looks
# sky zen/hor (linear), stars, beach light: gain, tint (planet-shine colour), flat (shadow flattening), ambient
LOOK = {
    "home": dict(zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), stars=0.0, gain=1.0, tint=(1.0, 0.98, 0.95), flat=0.0,
                 amb=(0.03, 0.05, 0.09), beams="rainbow", bI=0.35, expo=1.0),
    "eur": dict(zen=(0.004, 0.006, 0.026), hor=(0.030, 0.028, 0.050), stars=1.0, gain=0.22, tint=(1.0, 0.80, 0.60), flat=0.55,
                amb=(0.012, 0.010, 0.012), beams=[(1.0, 0.70, 0.35), (1.0, 0.45, 0.20), (1.0, 0.88, 0.60), (0.95, 0.35, 0.30)], bI=0.55, expo=1.05),
    "tit": dict(zen=(0.11, 0.055, 0.012), hor=(0.36, 0.19, 0.05), stars=0.0, gain=0.16, tint=(1.0, 0.55, 0.20), flat=0.8,
                amb=(0.03, 0.015, 0.004), beams=[(1.0, 0.6, 0.2), (1.0, 0.8, 0.45), (0.9, 0.45, 0.15)], bI=0.35, expo=1.1),
    "tri": dict(zen=(0.003, 0.006, 0.030), hor=(0.010, 0.022, 0.065), stars=1.0, gain=0.12, tint=(0.45, 0.65, 1.15), flat=0.7,
                amb=(0.006, 0.010, 0.022), beams=[(0.20, 0.35, 1.0), (0.45, 0.30, 1.0), (0.20, 0.75, 1.0), (0.6, 0.5, 1.0)], bI=0.55, expo=1.1),
    "cha": dict(zen=(0.004, 0.005, 0.022), hor=(0.020, 0.020, 0.040), stars=1.0, gain=0.09, tint=(0.95, 0.85, 0.75), flat=0.75,
                amb=(0.008, 0.008, 0.012), beams=[(0.95, 0.85, 0.7), (0.7, 0.75, 1.0), (1.0, 0.7, 0.5)], bI=0.45, expo=1.1),
    "pho": dict(zen=(0.006, 0.004, 0.020), hor=(0.045, 0.020, 0.025), stars=0.8, gain=0.40, tint=(1.0, 0.55, 0.32), flat=0.4,
                amb=(0.030, 0.014, 0.010), beams=[(1.0, 0.40, 0.15), (1.0, 0.60, 0.25), (0.9, 0.25, 0.20)], bI=0.6, expo=1.0),
}
LOOK["home2"] = LOOK["home"]
NUM = ("zen", "hor", "stars", "gain", "tint", "flat", "amb", "bI", "expo")
ABOVE = dict(zen=(0.004, 0.005, 0.020), hor=(0.20, 0.10, 0.025))       # Titan: above the haze (the haze is a glowing band below)
RO = {"home": ("FROM EARTH", f"OUR MOON: {DEG['moon']:.2f}° WIDE", "A PEA HELD AT ARM'S LENGTH", (235, 240, 255)),
      "eur": ("FROM EUROPA", f"JUPITER: {DEG['eur']:.1f}° WIDE", "24× OUR MOON · 670,000 KM AWAY", (255, 190, 120)),
      "tit": ("FROM TITAN", "SATURN: HIDDEN BY HAZE", "THICK ORANGE SMOG · 1.5× EARTH'S AIR PRESSURE", (255, 175, 80)),
      "tit2": ("ABOVE TITAN'S HAZE", f"SATURN: {DEG['tit']:.1f}° WIDE", "RINGS ALMOST EDGE-ON · 12.8° ACROSS", (255, 215, 140)),
      "tri": ("FROM TRITON", f"NEPTUNE: {DEG['tri']:.1f}° WIDE", "15× OUR MOON · TRITON ORBITS BACKWARDS", (120, 170, 255)),
      "cha": ("FROM CHARON", f"PLUTO: {DEG['cha']:.1f}° WIDE", "BOTH TIDALLY LOCKED: PLUTO NEVER MOVES", (235, 215, 190)),
      "pho": ("FROM PHOBOS", f"MARS: {DEG['pho']:.1f}° WIDE", "82× OUR MOON · ONLY 6,000 KM ABOVE MARS", (255, 130, 80))}
FC = {"eur": (1.0, 0.75, 0.45), "tit": (1.0, 0.6, 0.25), "tri": (0.45, 0.65, 1.0), "cha": (0.95, 0.85, 0.75), "pho": (1.0, 0.45, 0.25)}
# the Sun's direction in the camera frame (x right, y down, z away) for each planet's phase
SUNDIR = {"moon": (0.5, -0.4, -0.75), "eur": (0.62, -0.22, -0.75), "tit": (-0.55, -0.45, -0.70), "tri": (0.35, -0.30, -0.88),
          "cha": (-0.70, -0.10, -0.70), "pho": (0.55, -0.30, -0.78)}
POS = {"moon": (430.0, 560.0), "eur": PC, "tit": (405.0, 640.0), "tri": PC, "cha": PC, "pho": (450.0, 760.0)}

# water of the shallows: polygon in SOURCE px (from eclipses-other-worlds), feathered
WATER_POLY = [(0, 1158), (30, 1160), (200, 1172), (420, 1180), (520, 1198), (600, 1225), (650, 1260), (675, 1295), (665, 1325),
              (610, 1355), (500, 1388), (400, 1418), (300, 1443), (200, 1468), (100, 1492), (0, 1512)]


def scene_at(t):
    cur, t0 = "home", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = k, ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(BG, L)
        self.hz = float(fg.horizon)
        self.fx = FX(W, H); self.beams = Beams(W, H, seed=11)
        self.cam = SkyCam(W, H, self.hz, F_PX); self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.k_hor = np.exp(-el / 0.33)[..., None].astype(f32)
        self.k_band = np.exp(-el / 0.10)[..., None].astype(f32)
        self.xx, self.yy = self.fx.xx, self.fx.yy
        a = fg.a
        self.a_hard = np.clip(a / 0.9, 0, 1).astype(f32)
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        s = fg.s
        poly = np.array([[x * s, y * s + fg.oy] for x, y in WATER_POLY], np.float32)
        wm = np.zeros((H, W), np.uint8); cv2.fillPoly(wm, [np.round(poly * 4).astype(np.int32)], 255, shift=2)
        wm = cv2.GaussianBlur(wm.astype(f32) / 255, (0, 0), 3.0)
        self.water = (wm * (self.yy > self.hz - 2)).astype(f32)
        ys = np.where(self.water.max(1) > 0.01)[0]; xs = np.where(self.water.max(0) > 0.01)[0]
        self.wy0, self.wy1, self.wx1 = int(ys.min()), int(ys.max()) + 1, int(xs.max()) + 1
        wy = self.yy[self.wy0:self.wy1, :self.wx1]
        depth = np.clip((wy - self.hz) / (self.wy1 - self.hz), 0, 1)
        self.fres = (0.55 - 0.40 * depth ** 0.7).astype(f32)
        self.wnoise = fbm2((256, 512), 77, 2.4)
        pluto = PLUTO if os.path.exists(PLUTO) else \
            "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/threex.planets/images/plutomap1k.jpg"
        self.bodies = {
            "moon": Body("moon", "8k_moon.jpg", RPX["moon"], pole_vec(-12, 4), model="rock", surf=5.0, detail=0.0, ss=4),
            "eur": Body("eur", "8k_jupiter.jpg", RPX["eur"], pole_vec(-8, 3), q=0.935, spin=0.035, lon0=math.radians(-47) + 0.45,
                        winds=0.025, surf=1.40, sat=1.35, gamma=1.15, haze=(0.06, 0.05, 0.035), rim=(0.30, 0.26, 0.18), detail=0.05, seed=6),
            "tit": Body("tit", "8k_saturn.jpg", RPX["tit"], pole_vec(-6, 0.35), q=0.902, spin=0.03, surf=1.35, sat=1.2, gamma=1.1,
                        haze=(0.05, 0.04, 0.02), rim=(0.25, 0.20, 0.10), rings="saturn", detail=0.04, seed=5),
            "tri": Body("tri", "2k_neptune.jpg", RPX["tri"], pole_vec(18, 22), surf=1.45, lon0=math.radians(10), spin=0.06,
                        haze=(0.03, 0.07, 0.22), rim=(0.10, 0.22, 0.75), detail=0.06, sat=1.15, seed=3),
            "cha": Body("cha", pluto, RPX["cha"], pole_vec(-30, 10), model="rock", surf=1.6, lon0=math.radians(180), detail=0.02,
                        rim=(0.10, 0.12, 0.20), seed=7),
            "pho": Body("pho", "8k_mars.jpg", RPX["pho"], pole_vec(-15, 18), q=0.9941, model="rock", surf=1.4, lon0=math.radians(-70),
                        rim=(0.4, 0.15, 0.06), detail=0.02, spin=0.01),
        }
        emph = {"MOON", "UP", "EUROPA", "JUPITER", "24×", "TITAN", "SATURN", "HAZE", "RINGS", "TRITON", "NEPTUNE", "BLUE", "CHARON",
                "PLUTO", "NEVER", "PHOBOS", "MARS", "80×", "HOME", "TINY", "OURS"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1440

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def params(self, t):
        cur, t0, t1 = scene_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "home" if i == 0 else SWAPS[i - 1][1]
        B = dict(LOOK[cur])
        if cur == "tit":                                                       # rising above the haze
            r = ramp(t, T_RISE + 0.2, T_THERE + 0.2)
            B["zen"] = lerp(B["zen"], ABOVE["zen"], r); B["hor"] = lerp(B["hor"], ABOVE["hor"], r); B["stars"] = 0.8 * r
            B["gain"] = lerp(0.16, 0.20, r); B["tint"] = lerp((1.0, 0.55, 0.20), (1.0, 0.82, 0.55), r); B["bI"] = 0.35 + 0.25 * r
        if prev is None: w, A = 1.0, B
        else: w = ramp(t, t0 - 0.12, t0 + 0.55); A = LOOK[prev]
        P = {k: lerp(A[k], B[k], w) for k in NUM}
        P["beams"] = B["beams"] if w > 0.5 else A["beams"]
        return P, cur, t0, t1

    def water_reflect(self, sky_img, fgc, t):
        """mirror the rendered sky into the shallows: slight slow ripple, softened, darkened; Fresnel-weighted (calm)"""
        y0, y1, x1 = self.wy0, self.wy1, self.wx1
        ys = self.yy[y0:y1, :x1]; xs = self.xx[y0:y1, :x1]
        nu = cv2.remap(self.wnoise, ((xs * 0.6 + t * 5) % 512).astype(f32), ((ys * 2.2 + t * 2.5) % 256).astype(f32), cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_WRAP)
        depth = np.clip((ys - self.hz) / (y1 - self.hz), 0, 1)
        my = 2 * self.hz - ys + nu * (0.6 + 2.0 * depth)
        mx = xs + nu * (0.5 + 1.2 * depth)
        refl = cv2.remap(sky_img, mx.astype(f32), np.clip(my, 0, self.hz - 1).astype(f32), cv2.INTER_LINEAR)
        refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=1.2, sigmaY=2.5)
        R = self.fres[..., None] * self.water[y0:y1, :x1][..., None]
        base = fgc[y0:y1, :x1]
        fgc[y0:y1, :x1] = base * (1 - R * 0.85) + refl * R * 0.80

    def frame(self, t):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        P, cur, t0, t1 = self.params(t)
        key = "moon" if cur in ("home", "home2") else cur
        pulse = 1 + 0.05 * math.sin(2 * math.pi * t / 1.6) + sum(0.40 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        sc = back_out((t - t0) / BLOOM) if t0 > 0 else 1.0
        col_u = 0.0 if (t1 > 1e8 or t1 >= T_BACK - 1e-6) else max(0.0, 1 - (t1 - t) / COLLAPSE)
        if col_u > 0:
            if col_u < 0.45: sc *= 1 + 0.25 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; sc *= 1.25 * (1 - ease(v) ** 0.7) + 0.02
        cx, cy = POS[key]
        # ---- sky
        sky = np.array(P["zen"], f32) * (1 - self.k_hor) + np.array(P["hor"], f32) * self.k_hor
        if cur == "tit":                                                          # the haze: a glowing orange band near the horizon
            r = ramp(t, T_RISE + 0.2, T_THERE + 0.2)
            sky = sky + self.k_band * np.array([0.30, 0.14, 0.03], f32) * r
        if key == "moon":
            dd = np.sqrt((self.hx - 900) ** 2 + (self.hy + 300) ** 2)                 # sunlight from up-right, off frame
            sky = sky + (np.exp(-dd / 900) * 0.25)[..., None] * np.array([1.0, 0.92, 0.80], f32)
        bm = self.beams.layer(t, (cx, cy), P["beams"], P["bI"] * pulse, col_u, reach=1100.0)
        img = self.up(sky + bm)
        if P["stars"] > 0.01:
            img += self.stars.render(self.cam, t, rot=4.0, gain=1.0, plate_gain=0.35, twinkle=0.0, air=0.0) * P["stars"]
        # ---- the planet
        vis = 1.0
        if cur == "tit": vis = ramp(t, T_RISE + 0.3, T_THERE + 0.1)
        I = (1.0 + 0.25 * (pulse - 1)) * vis
        if key == "moon": I *= 0.35                                                 # a daytime Moon, washed by blue sky
        if I > 0.01 and sc > 0.01:
            self.bodies[key].render(img, cx, cy, t, I=I, scale=sc, sun=SUNDIR[key])
            if cur == "tit" and vis < 1:                                           # still partly veiled by the thinning haze
                pass
        sky_img = img
        # ---- the beach, relit by the planet-shine / distant Sun
        light = 1.0 + 0.08 * (pulse - 1) - 0.2 * col_u
        base = fg.rgb * (1 - P["flat"]) + fg.flat * P["flat"]
        fgc = base * np.array(P["tint"], f32) * P["gain"] + fg.flat * np.array(P["amb"], f32)
        fgc = fgc + (self.rim * 0.06 * P["gain"])[..., None] * np.array(P["tint"], f32)
        fgc = fgc * light + self.up(bm) * 0.03 * fg.a[..., None]
        self.water_reflect(sky_img, fgc, t)
        a = self.a_hard[..., None]
        img = sky_img * (1 - a) + fgc * a
        # ---- swaps
        for ts, k in SWAPS:
            if k == "home2": continue
            u = t - ts; fc = np.array(FC[k], f32)
            self.fx.flash(img, u, fc, k=2.4); self.fx.shock(img, *POS[k], u, fc)
        if cur == "tit":                                                            # break through the haze: a soft flash
            u = t - (T_RISE + 0.2)
            if -0.05 < u < 1.0: img += 1.2 * math.exp(-max(u, 0) / 0.15) * ease((u + 0.05) / 0.05) * np.array([1.0, 0.75, 0.45], f32)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([1.0, 0.95, 0.88], f32)
            self.fx.shock(img, *POS["moon"], t - T_BACK, np.array([1.0, 0.9, 0.7], f32))
        img = self.fx.chroma_bloom(img, 1.0)
        out = tonemap(img, P["expo"])
        out = self.fx.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
        return out

    def overlay(self, out, t, cur, t0):
        key = "home" if cur == "home2" else cur
        if cur == "home": t0 = 0.0
        if cur == "tit" and t > T_RISE + 0.2: key, t0 = "tit2", T_RISE + 0.2
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if cur == "tit" and t < T_RISE + 0.2: nxt = [T_RISE + 0.2] + nxt
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "home2": a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if T_WO0 < t < T_BACK: a = 0.0
        name, l2, l3, tc = RO[key]
        readout(out, self.L, a, name, l2, l3, tc)
        self.caps.draw(out, t)


def save_png(im, path):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, {k: round(v, 2) for k, v in T_SW.items()}, "back", round(T_BACK, 2), "rise", round(T_RISE, 2))
        for k in GEOM: print(f"{k:5s} {DEG[k]:6.2f} deg  r={RPX[k]:6.1f} px  ({DEG[k] / DEG['moon']:.1f}x our Moon)")
        print("Saturn A ring outer edge", round(deg_sph(A_RING_OUT, GEOM["tit"][1]), 2), "deg")
        sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    sc = Scene(True); d = os.path.join(SCR, "stills"); os.makedirs(d, exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); save_png(sc.frame(t), os.path.join(d, f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
