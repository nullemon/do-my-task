"""WHAT IF STRANGE EXOPLANETS REPLACED OUR MOON? -- one locked tripod shot of the mountain valley (B_valley) at blue hour.
Our Moon is swapped, one after another, for famous exoplanets placed at the Moon's distance (384,400 km), each drawn at
its true angular size theta = 2 asin(R/d) through a gnomonic lens with f = 1400 px (69 deg vertical FOV on the 1920 px
frame, as in planets-as-moon). The bodies sit LOW, over the ridge, so the giants are partly hidden behind it.
Every swap: the old body swells and implodes, a tinted flash + chromatic shockwave, the new body blooms in, and the
valley is relit by its light.
  Moon -> 55 Cancri e (lava) -> HD 189733 b (cobalt, glass rain) -> WASP-12 b (egg + gas stream) -> TrES-2 b (black)
  -> KELT-9 b (rises over the ridge like a sunrise) -> white-out -> Moon
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py vert                   full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5           stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2     re-render only those time ranges
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, noise1
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
import exoplanets as X
from exoplanets import Body, pole_vec

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-exoplanet-moons"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/B_valley.png"
FPS = 30
LEAD, TAIL = 0.25, 1.20
F_PX = 1400.0
D_KM = 384400.0
R_MOON, R_E, R_J = 1737.4, 6371.0, 71492.0

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def rad_px(R): return F_PX * math.tan(math.asin(R / D_KM))
def ang_deg(R): return 2 * math.degrees(math.asin(R / D_KM))


# ------------------------------------------------------------------------------------------------ the bodies
# R: radius (km). Visual: sky tint (zenith / horizon, linear, added to blue hour), glow colour, beam palette, valley
# light (tint, gain), star visibility, exposure, readout colour, emission scale E, centre on screen (vertical).
BODIES = [
    dict(key="moon", name="OUR MOON", R=R_MOON, l2="1× MOON'S SIZE", l3="0.52° WIDE", tc=(235, 240, 255),
         zen=(0.0, 0.0, 0.0), hor=(0.0, 0.0, 0.0), glow=(0.55, 0.62, 0.80), gl=0.28,
         beams=[(0.55, 0.65, 1.0), (0.80, 0.55, 1.0), (0.45, 0.95, 1.0)], bI=0.09, corona=0.35,
         tint=(0.75, 0.85, 1.10), gain=0.05, stars=1.0, expo=1.0, E=0.0, C=(560.0, 1105.0)),
    dict(key="cnc", name="55 CANCRI e", R=1.88 * R_E, l2="7× MOON'S SIZE", l3="LAVA-OCEAN WORLD", tc=(255, 120, 50),
         zen=(0.012, 0.002, 0.0), hor=(0.10, 0.02, 0.004), glow=(1.0, 0.32, 0.06), gl=1.2,
         beams=[(1.0, 0.25, 0.04), (1.0, 0.55, 0.10), (0.95, 0.10, 0.15), (1.0, 0.75, 0.2)], bI=0.30, corona=1.0,
         tint=(1.0, 0.40, 0.18), gain=0.09, stars=0.95, expo=1.0, E=3.2, C=(540.0, 1115.0)),
    dict(key="hd", name="HD 189733 b", R=1.138 * R_J, l2="47× MOON'S SIZE", l3="IT RAINS GLASS", tc=(90, 150, 255),
         zen=(0.0, 0.010, 0.07), hor=(0.0, 0.03, 0.12), glow=(0.22, 0.42, 1.0), gl=0.9,
         beams=[(0.15, 0.30, 1.0), (0.40, 0.25, 1.0), (0.15, 0.70, 1.0), (0.55, 0.55, 1.0)], bI=0.6, corona=0.0,
         tint=(0.35, 0.55, 1.35), gain=0.30, stars=0.7, expo=1.0, E=1.0, C=(540.0, 1250.0)),
    dict(key="wasp", name="WASP-12 b", R=1.937 * R_J, l2="80× MOON'S SIZE", l3="BEING EATEN BY ITS STAR", tc=(255, 150, 70),
         zen=(0.02, 0.004, 0.012), hor=(0.10, 0.025, 0.02), glow=(1.0, 0.40, 0.12), gl=0.8,
         beams=[(1.0, 0.35, 0.10), (1.0, 0.20, 0.45), (1.0, 0.65, 0.20), (0.8, 0.25, 0.9)], bI=0.55, corona=0.0,
         tint=(1.05, 0.45, 0.25), gain=0.20, stars=0.6, expo=1.0, E=1.0, C=(600.0, 1335.0)),
    dict(key="tres", name="TrES-2 b", R=1.2 * R_J, l2="49× MOON'S SIZE", l3="DARKER THAN COAL", tc=(225, 90, 80),
         zen=(-0.004, -0.008, -0.03), hor=(0.0, -0.01, -0.03), glow=(0.55, 0.08, 0.05), gl=0.35,
         beams=[(0.55, 0.06, 0.08), (0.30, 0.10, 0.45), (0.50, 0.15, 0.10)], bI=0.22, corona=0.0,
         tint=(0.55, 0.40, 0.55), gain=0.02, stars=1.35, expo=1.05, E=0.020, C=(520.0, 1255.0)),
    dict(key="kelt", name="KELT-9 b", R=1.891 * R_J, l2="78× MOON'S SIZE", l3="4,300 °C", tc=(255, 215, 120),
         zen=(0.05, 0.09, 0.22), hor=(0.95, 0.45, 0.10), glow=(1.0, 0.70, 0.35), gl=1.6,
         beams=[(1.0, 0.85, 0.50), (1.0, 0.55, 0.20), (1.0, 0.95, 0.75), (1.0, 0.40, 0.30)], bI=0.9, corona=0.0,
         tint=(1.30, 0.85, 0.50), gain=1.5, stars=0.0, expo=0.75, E=9.0, C=(540.0, 1330.0)),
]
for b in BODIES: b["Rp"] = rad_px(b["R"])
BK = {b["key"]: b for b in BODIES}

# ------------------------------------------------------------------------------------------------ timeline
ORDER = ["moon", "cnc", "hd", "wasp", "tres", "kelt"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
T_BACK = LN["end"]["start"] - 0.10                   # white-out peak -> our Moon is back
T_WO0 = T_BACK - 0.75
T_KELT = T_SW["kelt"]; T_RISEN = wt("kelt", "4,300 °C") + 0.3
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_BACK, "moon2")]
COLLAPSE, BLOOM = 0.42, 0.65
PULSES = [wt("hook", "STRANGEST"), wt("moon", "MOON"), wt("cnc", "7×"), wt("cnc", "LAVA"), wt("hd", "47×"), wt("hd", "GLASS"),
          wt("wasp", "EGG"), wt("wasp", "EATS"), wt("tres", "COAL"), wt("tres", "STARS"), wt("kelt", "HOTTEST"),
          wt("kelt", "4,300 °C"), wt("kelt", "STARS"), wt("end", "THANKFULLY")]


def body_at(t):
    cur, t0 = "moon", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("moon" if k == "moon2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w): return tuple(x + (y - x) * w for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * w


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


WASP_ANG = -118.0                                      # screen direction of WASP-12 b's long axis (towards its star)
WASP_STRETCH = (WASP_ANG, 1.24, 0.20)


# ------------------------------------------------------------------------------------------------ scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H; self.vertical = vertical
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.70)
        fg.a[fg.a > 0.9] = 1.0                              # the plate is fully opaque: nothing in the sky bleeds through
        self.hz = float(fg.horizon)
        self.cam = SkyCam(W, H, self.hz, F_PX)
        self.stars = StarSky()
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hx, self.hy = xx, yy
        self.el = np.degrees(np.arctan2(self.hz - yy, F_PX)).astype(f32)
        e = np.maximum(self.el, 0)
        xr = xx / W
        zen = np.array([0.010, 0.030, 0.115], f32)
        sky = zen * (0.62 + 0.38 * np.exp(-e / 28))[..., None]
        sky += np.array([0.05, 0.075, 0.16], f32) * np.exp(-e / 11)[..., None]
        belt = np.exp(-((e - 8.5) / 5.5) ** 2) * (0.55 + 0.45 * (1 - xr))                     # Belt of Venus
        sky += np.array([0.15, 0.065, 0.085], f32) * belt[..., None]
        shadow = np.exp(-e / 3.2)
        sky = sky * (1 - 0.30 * shadow)[..., None] + np.array([0.02, 0.035, 0.075], f32) * shadow[..., None]
        self.base_sky = sky.astype(f32)
        self.k_hor = np.exp(-e / 14)[..., None].astype(f32)
        yyf = np.arange(H, dtype=f32)
        elf = np.maximum(np.degrees(np.arctan2(self.hz - yyf, F_PX)), 0.25)
        Xm = 1 / (np.sin(np.radians(elf)) + 0.50572 * (elf + 6.07995) ** -1.6364)
        tau = np.array([0.06, 0.09, 0.17], f32)
        self.ext = np.exp(-Xm[:, None] * tau[None, :])[:, None, :].astype(f32) * np.ones((1, W, 1), f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.14, 0.24), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        # ---- bodies (procedural maps, see exoplanets.py)
        la, le = X.map_lava(); co = X.map_cobalt(); sp = X.map_sparkle(); wa, we = X.map_wasp(); ca, ce = X.map_coal(); ka, ke = X.map_kelt()
        Z3 = np.zeros((4, 8, 3), f32)
        self.body = {
            "moon": Body("moon", BK["moon"]["Rp"], pole_vec(-12, 4), tex="8k_moon.jpg", model="rock", surf=9.0, detail=0.0),
            "cnc": Body("cnc", BK["cnc"]["Rp"], pole_vec(-15, 20), alb=la, emis=le, model="rock", surf=1.3, spin=0.045,
                        sun=(-0.80, 0.10, -0.55), emis_day=0.35, emis_ld=0.2, rim=(2.0, 0.45, 0.08), detail=0.0, ss=3, seed=2),
            "hd": Body("hd", BK["hd"]["Rp"], pole_vec(12, 18), alb=co, emis=Z3, emis2=sp, emis2_spin=0.30, winds=0.035, spin=0.05,
                       haze=(0.02, 0.06, 0.25), rim=(0.10, 0.25, 0.95), surf=1.7, detail=0.012, seed=3),
            "wasp": Body("wasp", BK["wasp"]["Rp"], pole_vec(WASP_ANG + 90 - 90, 8), alb=wa, emis=we, stretch=WASP_STRETCH,
                         emis_day=0.5, surf=0.6, spin=0.02, winds=0.02, rim=(1.2, 0.35, 0.08), haze=(0.04, 0.01, 0.0), detail=0.012, seed=4),
            "tres": Body("tres", BK["tres"]["Rp"], pole_vec(-6, 12), alb=ca, emis=ce, sun=(0.62, -0.42, 0.66), emis_day=0.3,
                         surf=4.0, night=0.0, rim=(0.55, 0.07, 0.03), spin=0.02, seed=5),
            "kelt": Body("kelt", BK["kelt"]["Rp"], pole_vec(-5, 6), alb=ka, emis=ke, emis_day=0.25, emis_ld=0.55, surf=0.0,
                         spin=0.015, winds=0.01, rim=(3.0, 1.6, 0.6), emis_limb=(0.45, 1.3, 2.6), seed=6),
        }
        # foreground prep: rim light on the skyline
        a = fg.a
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        self.mist = np.clip(fbm2((512, 512), 41, 2.6) * 0.5 + 0.45, 0, 1).astype(f32)
        self.shim = fbm2((256, 256), 81, 2.0)
        yyf2, xxf2 = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf2, yyf2
        # gas stream particles (WASP-12 b): position along the stream s, transverse offset, speed
        gr = np.random.default_rng(12); n = 9000
        self.gas = dict(s0=gr.uniform(0, 1, n), off=gr.standard_normal(n), v=gr.uniform(0.10, 0.22, n), b=gr.uniform(0.3, 1.0, n) ** 2,
                        ph=gr.uniform(0, 6.28, n))
        er = np.random.default_rng(9); n = 380
        self.emb = dict(x=er.uniform(0, W, n), y0=er.uniform(0, 1, n), sp=er.uniform(0.06, 0.20, n), ph=er.uniform(0, 6.28, n),
                        sz=er.uniform(0.3, 1.0, n) ** 2, wob=er.uniform(5, 30, n))
        emph = {"STRANGEST", "PLANETS", "MOON", "55 CANCRI e", "7×", "LAVA", "HD 189733 b", "47×", "COBALT", "GLASS", "SIDEWAYS",
                "WASP-12 b", "EGG", "EATS", "TrES-2 b", "COAL", "SHADOW", "KELT-9 b", "HOTTEST", "4,300 °C", "BORING", "THANKFULLY"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 960

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- params
    def mix_params(self, t):
        cur, t0, t1 = body_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "moon" if i == 0 else ("moon" if SWAPS[i - 1][1] == "moon2" else SWAPS[i - 1][1])
        w = ramp(t, t0 - 0.12, t0 + 0.55) if prev else 1.0
        A = BK[prev] if prev else BK[cur]; B = BK[cur]
        return A, B, w, cur, t0, t1

    def pos(self, cur, t):
        """centre of the current body; KELT-9 b rises from behind the ridge like a sun; TrES-2 b drifts slowly
        (so stars wink out at its edge)"""
        C = BK[cur]["C"]
        if cur == "tres": return (C[0] + 9.0 * (t - T_SW["tres"]), C[1] - 3.0 * (t - T_SW["tres"]))
        if cur == "wasp": return (C[0] - 4.0 * (t - T_SW["wasp"]), C[1] + 2.0 * (t - T_SW["wasp"]))
        if cur != "kelt": return C
        J0 = (520.0, 1980.0)
        v = min(max((t - T_KELT) / (T_RISEN - T_KELT), 0), 1)
        u = 0.5 * ease(v) ** 0.8 + 0.5 * (1 - (1 - v) ** 2.2)
        drift = max(t - T_RISEN, 0) * 7.0
        return (J0[0] + (C[0] - J0[0]) * u, J0[1] + (C[1] - J0[1]) * u - drift)

    # -------------------------------------------------------------------------------------------- sky
    def sky(self, t, A, B, w, Rp, cx, cy, col_u, bright):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32) * bright; hor = np.array(lerp(A["hor"], B["hor"], w), f32) * bright
        sky = np.maximum(self.base_sky + zen * (1 - self.k_hor) + hor * self.k_hor, 0.004)
        gcol = np.array(lerp(A["glow"], B["glow"], w), f32); gl = lerp(A["gl"], B["gl"], w)
        dx = self.hx - cx; dy = self.hy - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        dd = np.maximum(d - Rp, 0)
        aure = (np.exp(-dd / (40 + 0.25 * Rp)) * 0.35 + np.exp(-dd / (180 + 0.6 * Rp)) * 0.05) * gl * (0.6 + 0.4 * bright)
        sky = sky + aure[..., None] * gcol
        cor = lerp(A["corona"], B["corona"], w)
        if cor > 0.01:
            x = (d - Rp) / 34.0 - 0.15 * t
            ring = np.exp(-np.maximum(d - Rp, 0) / 85) * smooth(Rp + 6, Rp + 26, d)
            sky = sky + palette(x) * (ring * 0.05 * cor)[..., None]
        bm = self.beams_layer(t, A, B, w, Rp, d, np.arctan2(dy, dx), col_u)
        return sky, bm, aure

    def beams_layer(self, t, A, B, w, Rp, d, phi0, col_u):
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = phi0 + twist * np.log(d / 30.0)
        reach = (900 + 1.0 * Rp) * (1 - 0.7 * ease(col_u))
        dd = np.maximum(d - Rp, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"])) * (1 + 0.5 * min(Rp, 300) / 300)
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.25) % 1.0
            c = pal_list(A["beams"], x) * (1 - w) + pal_list(B["beams"], x) * w if w < 1 else pal_list(B["beams"], x)
            acc += c * (g * I)[..., None]
        bI = lerp(A["bI"], B["bI"], w)
        return acc * rad[..., None] * 0.30 * bI

    # -------------------------------------------------------------------------------------------- WASP-12 b gas stream
    def gas_stream(self, t, cx, cy, Rp, amt):
        """hot gas pulled off the L1 tip towards the (off-screen) star, trailing behind the orbit; glowing particles
        flowing outwards, splatted at half resolution and blurred at two scales"""
        W, H = self.L.W, self.L.H; g = self.gas
        ca, sa = math.cos(math.radians(WASP_ANG)), math.sin(math.radians(WASP_ANG))
        px, py = -sa, ca                                                     # perpendicular (towards lower right)
        tip = Rp * WASP_STRETCH[1] * 0.97
        Ls = 1500.0
        s = (g["s0"] + g["v"] * t) % 1.0
        along = tip + s * Ls
        curl = -(s ** 1.6) * 520 + 30 * np.sin(s * 9 - t * 2.0)               # bends away (Coriolis lag)
        wid = 10 + 110 * s ** 1.1
        off = g["off"] * wid + curl
        x = cx + ca * along + px * off; y = cy + sa * along + py * off
        fl = (0.55 + 0.45 * np.sin(s * 40 - t * 6 + g["ph"])) * g["b"] * np.exp(-s * 2.2) * smooth(0.0, 0.03, s)
        hw, hh = W // 2, H // 2
        lay = np.zeros((hh, hw), f32)
        xi = (x / 2).astype(int); yi = (y / 2).astype(int)
        ok = (xi >= 0) & (xi < hw) & (yi >= 0) & (yi < hh)
        np.add.at(lay, (yi[ok], xi[ok]), fl[ok])
        core = cv2.GaussianBlur(lay, (0, 0), 1.8) * 4.0
        glow = cv2.GaussianBlur(lay, (0, 0), 8.0) * 22.0 + cv2.GaussianBlur(lay, (0, 0), 28.0) * 40.0
        # colour: white-yellow core near the planet -> orange -> magenta (H-alpha-ish) far out
        dd = np.sqrt((self.hx - cx) ** 2 + (self.hy - cy) ** 2)
        fr = np.clip((dd - tip) / 900.0, 0, 1)[..., None]
        c_near = np.array([1.0, 0.55, 0.15], f32); c_far = np.array([1.0, 0.18, 0.40], f32)
        col = c_near * (1 - fr) + c_far * fr
        out = (core[..., None] * (col * 0.7 + 0.3) + glow[..., None] * col) * amt
        return self.up(out)

    # -------------------------------------------------------------------------------------------- foreground
    def relight(self, A, B, w, light, kfac):
        fg = self.fg
        amb_col = np.array([0.22, 0.32, 0.62], f32) * 0.11
        night = fg.flat * 0.75 + fg.rgb * 0.25
        def one(S):
            g = S["gain"] * (kfac if S["key"] == "kelt" else 1.0)
            key = (fg.rgb * 0.45 + fg.flat * 0.55) * np.array(S["tint"], f32) * g
            if S["key"] == "kelt": key = (fg.rgb * 0.75 + fg.flat * 0.25) * np.array(S["tint"], f32) * g
            out = night * amb_col * (0.6 if S["key"] == "tres" else 1.0) + key
            rc = np.array(S["glow"], f32)
            out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * rc * (0.04 + g * 0.6) * 0.35
            return out
        fb = one(B)
        fgc = fb if w >= 1 else one(A) * (1 - w) + fb * w
        return fgc * light

    def valley_mist(self, t, a, col):
        hz = self.hz
        sx, sy = self.xx[::2, ::2], self.yy[::2, ::2]
        mu = (sx * 0.30 + t * 10) % 512; mv = (sy * 1.1 + t * 3) % 512
        mn = cv2.remap(self.mist, mu.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        band = smooth(hz - 30, hz + 25, sy) * (1 - smooth(hz + 90, hz + 260, sy))
        m = cv2.GaussianBlur(np.clip(mn * 1.4 - 0.3, 0, 1), (0, 0), 5)
        return self.up(m * band * a)[..., None] * np.array(col, f32)

    def embers(self, t, amt, col):
        """rising sparks / heat motes"""
        W, H = self.L.W, self.L.H; e = self.emb
        y = H * (1.05 - ((e["y0"] + e["sp"] * t) % 1.0) * 0.75)
        x = e["x"] + e["wob"] * np.sin(t * 1.3 + e["ph"]) + 40 * np.sin(y / 300 + e["ph"])
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        tw = 0.6 + 0.4 * np.sin(t * 7 + e["ph"] * 3)
        np.add.at(lay, (yi, xi), e["sz"] * tw * amt)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.9) * 8 + cv2.GaussianBlur(lay, (0, 0), 4.0) * 4
        return self.up(lay)[..., None] * np.array(col, f32)

    def shimmer(self, img, amp, t, mask):
        if amp <= 0: return img
        u = (self.xx * 0.10 + t * 40) % 256; v = (self.yy * 0.10 + t * 25) % 256
        n = cv2.remap(self.shim, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        k = mask * amp
        return cv2.remap(img, (self.xx + n * k).astype(f32), (self.yy + n * k * 0.7).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = BK[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.45 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        scale = g_in
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        if col_u > 0:
            if col_u < 0.45: scale *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; scale *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        cx, cy = self.pos(cur, t)
        Rp = S["Rp"] * scale
        kfac = 1.0
        if cur == "kelt": kfac = 0.25 + 0.75 * smooth(self.hz + 250, S["C"][1], cy)
        bright = kfac * (1 + 0.5 * (pulse - 1))
        sky, bm, aure = self.sky(t, A, B, w, Rp, cx, cy, col_u, bright)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        sg = lerp(A["stars"], B["stars"], w)
        if sg > 0.01:
            st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.3, plate_gain=0.12, star_gain=1.0, cx=2000, cy=900, rot=6.0)
            img += st * (sg * np.exp(-self.up(aure) * 6))[..., None] * 0.9
        # WASP-12 b: gas stream behind/around the planet
        if cur == "wasp":
            img += self.gas_stream(t, cx, cy, Rp, (0.25 + 0.75 * min(max(u_in, 0), 1)) * (1 - col_u) * (1 + 0.3 * (pulse - 1)))
        # emission flicker
        E = S["E"] * (1 + 0.12 * noise1(t, 3, 2.5, 2)) * (1 + 0.6 * (pulse - 1))
        if cur == "kelt": E *= 0.6 + 0.4 * kfac
        bd = self.body[cur]
        bd.render(img, cx, cy, t, I=I_mul, scale=scale, ext=self.ext, E=E)
        # ---- foreground
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(A, B, w, light, kfac)
        fgc = fgc + self.up(bm) * 0.05 * fg.a[..., None]
        lc = np.array(lerp(A["glow"], B["glow"], w), f32)
        fgc = fgc + self.valley_mist(t, 0.06 + 0.15 * min(lerp(A["gain"], B["gain"], w), 1.0) * kfac, lc * 0.5) * fg.a[..., None]
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        if cur == "cnc":                                                      # sparks drifting up the valley
            img += self.embers(t, 0.35 * min(max(u_in, 0), 1) * (1 - col_u), (1.0, 0.45, 0.12))
        if cur == "kelt":                                                     # heat haze + motes as it blazes
            heat = smooth(T_RISEN - 1.5, T_RISEN, t) * (1 - col_u)
            img += self.embers(t, 0.5 * heat, (1.0, 0.75, 0.40))
            img = self.shimmer(img, 2.5 * heat, t, fg.a)
        # ---- swap flash + chromatic shockwave
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = BK["moon" if k == "moon2" else k]
                fc = 0.4 + 0.6 * np.array(NS["glow"], f32) / max(NS["glow"])
                img += (3.0 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                pcx, pcy = self.pos("moon" if k == "moon2" else k, ts + 0.01)
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - pcx) ** 2 + (self.yy - pcy) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.9], f32)
        img = self.chroma_bloom(img, 1.0 + (0.8 * kfac * w if cur == "kelt" else 0.0))
        expo = lerp(A["expo"], B["expo"], w)
        if cur == "kelt": expo = lerp(BK["tres"]["expo"], S["expo"], max(w, 0) * (0.3 + 0.7 * kfac))
        out = tonemap(img, expo)
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
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
        W, H = self.L.W, self.L.H
        o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        """readout at the top of the sky (the bodies sit low over the ridge): NAME / x MOON'S SIZE / weird fact"""
        L = self.L; W = L.W
        S = BK[cur]
        x, ys = W / 2, (330, 420, 482)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        if cur == "moon" and t < T_SW["cnc"]: a = ramp(t, wt("moon", "HERE'S") - 0.1, wt("moon", "HERE'S") + 0.2)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "moon" and t > T_BACK: a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if T_WO0 < t < T_BACK: a = 0.0
        if cur == "kelt": a *= smooth(1750, 1500, self.pos(cur, t)[1])
        if a > 0.01:
            dy = (1 - a) * -18
            big = int(L.hud_size * 1.45)
            rgba, _ = word_layer(S["name"], big, W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.66), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.52), "Black", tuple(min(255, int(c * 0.35 + 165)) for c in S["tc"]), a, 0.10, display=True)
        self.caps.draw(out, t)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(vertical, ranges):
    """re-render only frames inside `ranges` [(t0, t1)], copying the others from the existing render"""
    import subprocess
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    W, H = sc.L.W, sc.L.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
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
        print("DUR", DUR); [print(b["key"], round(b["R"]), "km", round(b["Rp"], 1), "px", round(ang_deg(b["R"]), 2), "deg", round(b["R"] / R_MOON, 1), "x Moon") for b in BODIES]
        print({k: round(v, 2) for k, v in T_SW.items()}, "risen", round(T_RISEN, 2), "back", round(T_BACK, 2)); sys.exit()
    if sys.argv[1] == "patch":
        patch(sys.argv[2] != "wide", [tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
