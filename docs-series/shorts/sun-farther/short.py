"""WHAT IF EARTH MOVED FARTHER FROM THE SUN? -- one locked tripod shot of the snowy village (02_snowy_mountain_village),
BATCH3 swap format. Earth is moved, step by step, away from the Sun; the Sun is drawn at its TRUE angular size through a
~65 deg vertical-FOV lens (f = 1500 px). The sky dims step by step (never black), stars come out, frost and ice creep over
the village and in from the frame edges, the air freezes and snows down at Neptune's distance, and the lit chalet
windows stay warm islands throughout. White-out back to the warm village (loops).
  1 au -> 1.52 au (Mars) -> 5.2 au (Jupiter) -> 9.5 au (Saturn) -> 30 au (Neptune) -> ~2,000 au (Oort cloud) -> 1 au
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5             stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py seg                      restart-safe segment render -> SCR/video_vert.mp4
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, kf, lum, fbm2, bbcolor
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-sun-farther"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/02_snowy_mountain_village.png"
FPS = 30
LEAD, TAIL = 0.25, 0.90
F_PX = 1500.0
RSUN_AU = 0.00465047

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}


def wt(key, cap, n=0):
    ws = [w for l in PL if l["key"] == key or l["key"].startswith(key + "_") for w in l["words"] if w["cap"] == cap]
    return ws[n]["t0"]


def rad_px(d): return F_PX * math.tan(math.asin(min(RSUN_AU / d, 0.999)))
def ang_deg(d): return 2 * math.degrees(math.asin(min(RSUN_AU / d, 1.0)))


# d [au]; sky zenith / horizon (linear); beams; sun surface brightness (perceived, eye-adapted), glow, spikes;
# foreground: gain, tint, ambient; star visibility; exposure; window boost
STAGES = [
    dict(key="now", d=1.0, name="TODAY · 1 AU", l2="0.53° WIDE · 100% SUNLIGHT", l3="AVERAGE 15 °C", tc=(255, 225, 150),
         zen=(0.018, 0.085, 0.42), hor=(0.62, 0.55, 0.55), beams="rainbow", bI=1.0, surf=40.0, glow=1.0, spikes=0.6,
         gain=2.3, tint=(1.18, 1.0, 0.82), amb=0.0, stars=0.0, expo=1.0, win=1.0, fl=(1.0, 0.92, 0.78)),
    dict(key="mars", d=1.524, name="MARS'S ORBIT", l2="1.52 AU · 0.35° WIDE", l3="43% OF THE LIGHT · ENDLESS WINTER", tc=(200, 230, 255),
         zen=(0.020, 0.075, 0.34), hor=(0.42, 0.50, 0.62), beams=[(0.6, 0.85, 1.0), (0.85, 0.95, 1.0), (0.5, 0.7, 1.0), (0.9, 0.9, 1.0)],
         bI=0.6, surf=3.2, glow=0.14, spikes=0.10, gain=1.55, tint=(0.95, 1.0, 1.08), amb=0.0, stars=0.0, expo=1.05, win=1.1, fl=(0.85, 0.92, 1.0)),
    dict(key="jup", d=5.203, name="JUPITER'S ORBIT", l2="5.2 AU · 0.1° WIDE", l3="1/27 OF THE LIGHT", tc=(190, 215, 255),
         zen=(0.010, 0.030, 0.13), hor=(0.10, 0.13, 0.20), beams=[(0.5, 0.7, 1.0), (0.7, 0.6, 1.0), (0.6, 0.9, 1.0)],
         bI=0.5, surf=60.0, glow=0.75, spikes=0.95, gain=0.80, tint=(0.80, 0.92, 1.15), amb=0.0, stars=0.05, expo=1.25, win=1.35, fl=(0.8, 0.88, 1.0)),
    dict(key="sat", d=9.537, name="SATURN'S ORBIT", l2="9.5 AU · 0.06° WIDE", l3="1/90 OF THE LIGHT", tc=(180, 205, 255),
         zen=(0.006, 0.015, 0.075), hor=(0.04, 0.06, 0.12), beams=[(0.5, 0.65, 1.0), (0.7, 0.55, 1.0), (0.55, 0.85, 1.0)],
         bI=0.38, surf=60.0, glow=0.6, spikes=1.05, gain=0.48, tint=(0.72, 0.88, 1.2), amb=0.0, stars=0.25, expo=1.3, win=1.6, fl=(0.75, 0.85, 1.0)),
    dict(key="nep", d=30.07, name="NEPTUNE'S ORBIT", l2="30 AU · 1/900 OF THE LIGHT", l3="~450× THE FULL MOON · THE AIR FREEZES", tc=(150, 200, 255),
         zen=(0.0032, 0.0075, 0.040), hor=(0.016, 0.026, 0.065), beams=[(0.45, 0.6, 1.0), (0.6, 0.8, 1.0), (0.8, 0.6, 1.0)],
         bI=0.30, surf=50.0, glow=0.5, spikes=1.15, gain=0.28, tint=(0.62, 0.82, 1.25), amb=0.0, stars=0.7, expo=1.3, win=1.9, fl=(0.7, 0.85, 1.0)),
    dict(key="oort", d=2000.0, name="THE OORT CLOUD", l2="~2,000 AU · 1/4,000,000 OF THE LIGHT", l3="STILL THE BRIGHTEST STAR", tc=(170, 190, 255),
         zen=(0.0024, 0.0050, 0.030), hor=(0.010, 0.016, 0.045), beams=[(0.5, 0.6, 1.0), (0.8, 0.6, 1.0)],
         bI=0.10, surf=14.0, glow=0.18, spikes=0.28, gain=0.17, tint=(0.58, 0.78, 1.3), amb=0.0, stars=1.0, expo=1.3, win=2.0, fl=(0.7, 0.8, 1.0)),
]
for s in STAGES: s["Rp"] = rad_px(s["d"])
SK = {s["key"]: s for s in STAGES}

ORDER = ["now", "mars", "jup", "sat", "nep", "oort"]
T_SW = {k: LN[k]["start"] - 0.06 for k in ORDER[1:]}
COLLAPSE, BLOOM = 0.42, 0.65
T_WINTER = wt("mars", "WINTER")
T_FREEZE = wt("nep", "AIR")
T_SUNBACK = LN["end"]["start"] - 0.10
T_WO0 = T_SUNBACK - 0.85
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_SUNBACK, "now2")]
PULSES = [wt("hook", "SUN"), wt("mars", "HALF"), wt("mars", "ENDS"), wt("jup", "TINY"), wt("jup", "STORMY"), wt("sat", "90×"),
          wt("nep", "BRILLIANT"), wt("nep", "SNOW"), wt("oort", "OORT"), wt("oort", "STAR"), wt("end", "EARTH")]


def fx_keys():
    s = T_SW
    return dict(
        frost=[(0, 0.0), (s["mars"], 0.0), (T_WINTER - 0.3, 0.15), (T_WINTER + 1.5, 0.35), (s["jup"] + 0.8, 0.5), (s["sat"] + 0.8, 0.68),
               (s["nep"] + 0.8, 0.82), (T_FREEZE + 1.5, 0.95), (s["oort"] + 1.0, 1.0)],
        edge=[(0, 0.0), (T_WINTER - 0.3, 0.0), (T_WINTER + 1.8, 0.25), (s["jup"] + 1.0, 0.4), (s["sat"] + 1.0, 0.55),
              (s["nep"] + 1.0, 0.72), (T_FREEZE + 2.0, 0.9), (s["oort"] + 1.0, 1.0)],
        snow=[(0, 0.0), (T_FREEZE - 0.2, 0.0), (T_FREEZE + 1.4, 1.0), (s["oort"] + 0.3, 1.0), (s["oort"] + 2.8, 0.15)],
        cold=[(0, 0.0), (s["mars"], 0.0), (s["mars"] + 0.6, 0.3), (s["jup"] + 0.6, 0.55), (s["sat"] + 0.6, 0.7), (s["nep"] + 0.6, 0.85), (s["oort"] + 0.6, 1.0)],
    )


FX = fx_keys()
def fx(name, t): return 0.0 if t >= T_SUNBACK else kf(t, FX[name])


def stage_at(t):
    cur, t0 = "now", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("now" if k == "now2" else k), ts
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


class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(FG_PATH, L, lamps=[], hz_frac=0.68)
        self.hz = float(fg.horizon)
        self.C = (650.0, 640.0)
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.dx = xx - self.C[0]; self.dy = yy - self.C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        sky_bot = 1150.0                                            # the sky reaches down to the ridge behind the chalets
        el = np.clip((sky_bot - yy) / sky_bot, 0, 1)
        self.k_hor = np.exp(-el / 0.30)[..., None].astype(f32)
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           rainbow=bool(i % 3 != 2), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        self.cam = SkyCam(W, H, sky_bot, F_PX)
        self.stars = StarSky(42)
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        a = fg.a
        # lit windows / porch lamps: warm, bright pixels of the plate (they keep glowing whatever the Sun does)
        src = np.clip(fg.rgb, 0, 1) ** (1 / 2.2)
        rr, bb = src[..., 0], src[..., 2]
        win = np.clip((rr - 0.45) / 0.25, 0, 1) * np.clip((rr / (bb + 0.02) - 1.5) / 0.8, 0, 1) * a
        self.win = cv2.GaussianBlur(win, (0, 0), 0.7).astype(f32)
        self.win_rgb = (fg.rgb * self.win[..., None]).astype(f32)
        spill = cv2.GaussianBlur(self.win, (0, 0), 30) + cv2.GaussianBlur(self.win, (0, 0), 90) * 0.6
        self.spill = (spill / max(spill.max(), 1e-4) * a).astype(f32)
        self.base = (fg.rgb * (1 - self.win[..., None])).astype(f32)
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        # frost on the scene: creeping front (bottom first and the tops of things), blue-white crystalline, glints
        nl = cv2.resize(fbm2((128, 128), 21, 2.6), (W, H), interpolation=cv2.INTER_CUBIC)
        self.frost_field = (0.62 * (1 - yyf / H) + 0.08 * nl).astype(f32)
        Y = lum(fg.rgb)
        self.frost_cover = (a * (1 - self.win) * (0.55 + 0.45 * smooth(0.0, 0.08, Y))).astype(f32)
        # window-pane frost growing in from the frame edges: feathery dendritic texture
        e = np.minimum(np.minimum(xxf, W - 1 - xxf), np.minimum(yyf, H - 1 - yyf) * 0.8)
        ang = np.arctan2(yyf - H / 2, xxf - W / 2)
        n1 = cv2.resize(fbm2((256, 256), 501, 2.2), (W, H), interpolation=cv2.INTER_CUBIC)
        n2 = cv2.resize(fbm2((512, 512), 502, 1.4), (W, H), interpolation=cv2.INTER_CUBIC)
        self.edge_field = (e / 170.0 + 0.30 * n1 + 0.12 * n2).astype(f32)
        fine = fbm2((H, W), 503, 0.7)
        streak = np.zeros((H, W), f32)
        for an in (20, 80, 140):
            k_ = cv2.getRotationMatrix2D((10, 10), an, 1.0); ker = np.zeros((21, 21), f32); ker[10, :] = 1
            ker = cv2.warpAffine(ker, k_, (21, 21)); ker /= ker.sum()
            streak += np.abs(cv2.filter2D(fine, -1, ker))
        self.feather = np.clip(streak / streak.mean() * 0.6, 0, 2.5).astype(f32)
        # snow (the atmosphere freezing out): 3 depth layers
        sr = np.random.default_rng(13); n = 1400
        self.sn = dict(x=sr.uniform(0, W, n), y0=sr.uniform(0, 1, n), z=sr.uniform(0, 1, n) ** 1.5, ph=sr.uniform(0, 6.28, n),
                       sw=sr.uniform(8, 40, n), fr=sr.uniform(0.3, 1.1, n))
        emph = {"SUN", "HALF", "WINTER", "ENDS", "TINY", "STORMY", "90×", "BRILLIANT", "STAR", "FREEZES", "SNOW", "OORT", "MANY",
                "EARTH", "IMAGINE", "AWAY", "NEPTUNE"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def mix_params(self, t):
        cur, t0, t1 = stage_at(t)
        prev = None
        for idx, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "now" if idx == 0 else ("now" if SWAPS[idx - 1][1] == "now2" else SWAPS[idx - 1][1])
        w = ramp(t, t0 - 0.12, t0 + 0.75) if prev else 1.0
        A = SK[prev] if prev else SK[cur]; B = SK[cur]
        return A, B, w, cur, t0, t1

    def sky(self, t, A, B, w, Rp, col_u):
        zen = np.array(lerp(A["zen"], B["zen"], w), f32); hor = np.array(lerp(A["hor"], B["hor"], w), f32)
        sky = zen * (1 - self.k_hor) + hor * self.k_hor
        gl = lerp(A["glow"], B["glow"], w); fl = np.array(lerp(A["fl"], B["fl"], w), f32)
        bright = (np.array(A["zen"]).sum() * (1 - w) + np.array(B["zen"]).sum() * w) / 0.59
        dd = np.maximum(self.d - Rp, 0)
        aure = np.exp(-dd / 45) * 0.9 + np.exp(-dd / 220) * 0.12
        sky = sky + (aure * gl * (0.25 + 0.75 * min(bright, 1.0)))[..., None] * fl
        sa = lerp(A["stars"], B["stars"], w)
        st = None
        if sa > 0.001:
            st = self.stars.render(self.cam, t, gain=1.0, twinkle=0.8, air=0.6, plate_gain=0.55 * sa, star_gain=1.4 * sa, rot=0.6 * t / DUR)
        return sky, self.beams_layer(t, A, B, w, col_u), st

    def beams_layer(self, t, A, B, w, col_u):
        Rp = 4.0
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = self.phi + twist * np.log(self.d / 30.0)
        reach = 1500 * (1 - 0.7 * ease(col_u))
        dd = np.maximum(self.d - Rp, 0)
        rad = (1 - np.exp(-(dd + 6) / 35)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(self.d / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(self.dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.32) % 1.0 if b["rainbow"] else np.full(dp.shape, b["hue"], f32)
            def colof(S): return palette(x) if S["beams"] == "rainbow" else pal_list(S["beams"], x)
            c = colof(A) * (1 - w) + colof(B) * w if w < 1 else colof(B)
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.38 * lerp(A["bI"], B["bI"], w)

    def draw_sun(self, img, t, S, Rp, I_mul, wob, hot, glow, spikes, surf):
        """limb-darkened disc at its true size (a point once it is below a pixel), corona glow, chromatic spikes"""
        cx, cy = self.C; H, W = img.shape[:2]
        sc = bbcolor(5772 * (1 + hot))
        pad = 520
        x0, x1, y0, y1 = max(0, int(cx - pad)), min(W, int(cx + pad)), max(0, int(cy - pad)), min(H, int(cy + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        ang = np.arctan2(dy, dx)
        reg = img[y0:y1, x0:x1]
        Re = Rp * (1 + wob * (0.07 * np.sin(3 * ang + 9 * t) + 0.05 * np.sin(5 * ang - 13 * t)))
        if Rp > 1.2:
            inside = smooth(Re + 0.9, Re - 0.9, d); mu = np.sqrt(np.clip(1 - (d / Rp) ** 2, 0, 1))
            reg += (inside * (1 - 0.6 * (1 - mu)) * surf * I_mul)[..., None] * (0.25 + 0.75 * sc)
        else:                                                            # unresolved: a point of the same total light
            reg += (np.exp(-(d / 1.0) ** 2) * surf * I_mul * max(Rp / 1.2, 0.35))[..., None] * (0.25 + 0.75 * sc)
        dd = np.maximum(d - Re, 0)
        g = (np.exp(-dd / 3.5) * 2.2 + np.exp(-dd / 24) * 0.55 + np.exp(-dd / 95) * 0.12)
        reg += (g * glow * I_mul * 0.75)[..., None] * (0.3 + 0.7 * sc)
        if spikes > 0:
            for k in range(6):
                a = k * math.pi / 3 + 0.26 + 0.03 * math.sin(t * 0.5)
                al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
                base = np.exp(-pp / 1.6) * (al > 0)
                for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                    reg[..., c] += base * np.exp(-al / (150 * Lk)) * 2.2 * spikes * I_mul * (0.4 + 0.6 * sc[c])
        img[y0:y1, x0:x1] = reg

    def relight(self, A, B, w, light, t):
        fg = self.fg
        def one(S):
            out = self.base * np.array(S["tint"], f32) * S["gain"]
            sky_amb = np.array(S["zen"], f32) * 0.5 + np.array(S["hor"], f32) * 0.5
            out += (self.rim * 0.9)[..., None] * sky_amb * 0.6 * fg.flat.mean()
            return out
        fb = one(B)
        out = (fb if w >= 1 else one(A) * (1 - w) + fb * w) * light
        wl = lerp(A["win"], B["win"], w) * (1 + 0.025 * math.sin(t * 7.3) + 0.015 * math.sin(t * 13.1))
        out += self.win_rgb * 1.8 * wl                                  # windows: constant warm light, they never dim
        out += self.spill[..., None] * np.array([1.0, 0.55, 0.22], f32) * 0.045 * wl   # warm light spilling on the snow
        return out

    def frost(self, img, amount, t):
        if amount <= 0: return img
        thr = amount * 1.35 - 0.25
        m = smooth(-0.08, 0.08, thr - self.frost_field) * self.frost_cover
        m = cv2.GaussianBlur(m, (0, 0), 1.5)
        y = lum(img)[..., None]
        tex = (np.clip(self.fg.crystal, 0.9, 1.25) * np.clip(self.fg.hf, 0.85, 1.4) ** 0.9)[..., None]
        ice = (y * 1.25 + 0.012) * tex * np.array([0.72, 0.88, 1.3], f32)
        out = img * (1 - m[..., None] * 0.8) + ice * m[..., None] * 0.8
        g = self.fg.glint_xy; mg = m[g[:, 1], g[:, 0]]
        tw = np.clip(np.sin(t * self.fg.glint_fr * 6.283 + self.fg.glint_ph), 0, 1) ** 10
        val = mg * tw * self.fg.glint_sz * 0.9
        sel = val > 1e-4
        if sel.any():
            H, W = img.shape[:2]
            lay = np.zeros((H, W), f32); np.add.at(lay, (g[sel, 1], g[sel, 0]), val[sel])
            lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 4 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 2
            out = out + lay[..., None] * np.array([0.85, 0.93, 1.0], f32)
        return out.astype(f32)

    def edge_frost(self, img, amount, t):
        """ice ferns growing in from the frame edges (frosted window pane), lit by the scene and the windows"""
        if amount <= 0: return img
        m = smooth(amount * 0.95 + 0.05, amount * 0.95 - 0.25, self.edge_field)
        m = m * np.clip(0.35 + 0.65 * self.feather, 0, 1.6)
        m = np.clip(m, 0, 1)
        y = cv2.GaussianBlur(lum(img), (0, 0), 25)[..., None]
        col = (0.01 + y * 0.55) * np.array([0.75, 0.9, 1.3], f32) * (0.6 + 0.7 * self.feather[..., None])
        return img * (1 - m[..., None] * 0.6) + col * m[..., None] * 0.8

    def snow(self, img, amt, t):
        if amt <= 0: return img
        W, H = self.L.W, self.L.H; s = self.sn
        sp = 60 + 260 * s["z"]
        y = (s["y0"] * (H + 100) + sp * t) % (H + 100) - 50
        x = (s["x"] + s["sw"] * np.sin(t * s["fr"] + s["ph"])) % W
        lay = np.zeros((H // 2, W // 2), f32)
        xi = np.clip((x / 2).astype(int), 0, W // 2 - 1); yi = np.clip((y / 2).astype(int), 0, H // 2 - 1)
        np.add.at(lay, (yi, xi), (0.25 + 0.75 * s["z"]) * amt)
        lay = cv2.GaussianBlur(lay, (0, 0), 1.0) * 3.2 + cv2.GaussianBlur(lay, (0, 0), 3.0) * 2.0
        y_ = lum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA))
        lit = cv2.resize(cv2.GaussianBlur(y_, (0, 0), 6), (W, H)) * 2.5 + 0.08
        return img + (self.up(lay) * lit)[..., None] * np.array([0.85, 0.92, 1.1], f32)

    def frame(self, t):
        fg = self.fg
        A, B, w, cur, t0, t1 = self.mix_params(t)
        S = SK[cur]
        pulse = 1 + 0.10 * math.sin(2 * math.pi * t / 1.6) + sum(0.6 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        g_in = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        Rp = S["Rp"] * g_in
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        hot = 0.0; wob = 0.0
        if col_u > 0:
            if col_u < 0.45: Rp *= 1 + 0.35 * ease(col_u / 0.45); wob = col_u / 0.45
            else: v = (col_u - 0.45) / 0.55; Rp *= 1.35 * (1 - ease(v) ** 0.7) + 0.02; wob = 1 - v
            I_mul *= 1 + 5 * col_u ** 2; hot = 0.15 * col_u
        sky, bm, st = self.sky(t, A, B, w, Rp, col_u)
        img = self.up(sky * (1 - 0.3 * col_u) + bm * (1 + 0.6 * col_u))
        if st is not None: img = img + st
        self.draw_sun(img, t, S, max(Rp, 0.05), I_mul, wob, hot, S["glow"], S["spikes"], S["surf"])
        light = 1.0 + 0.10 * (pulse - 1) - 0.2 * col_u
        fgc = self.relight(A, B, w, light, t)
        fgc = fgc + self.up(bm) * 0.03 * fg.a[..., None]
        fr = fx("frost", t)
        if fr > 0: fgc = self.frost(fgc, fr, t)
        a = fg.a[..., None]
        img = img * (1 - a) + fgc * a
        img = self.snow(img, fx("snow", t), t)
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4:
                NS = SK["now" if k == "now2" else k]
                fc = 0.4 + 0.6 * np.array(NS["fl"], f32)
                img += (2.6 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
                dd = np.sqrt((self.xx - self.C[0]) ** 2 + (self.yy - self.C[1]) ** 2)
                for ch, off in ((0, 10), (1, 0), (2, -10)):
                    img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 1.6 * math.exp(-max(u, 0) / 0.55)
        img = self.edge_frost(img, fx("edge", t), t)
        if T_WO0 < t < T_SUNBACK:
            v = ease((t - T_WO0) / (T_SUNBACK - T_WO0))
            img = img + (30 * v ** 2.5) * np.array([1.0, 0.93, 0.85], f32)
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, lerp(A["expo"], B["expo"], w))
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        if cur in ("mars", "jup"):
            self.today_ring(out, t, ramp(t, t0 + 0.5, t0 + 0.9) * (1 - ramp(t, t1 - 0.5, t1 - 0.3)))
        self.overlay(out, t, cur, t0)
        return out

    def today_ring(self, out, t, a):
        """faint dashed ring at today's true solar size (0.53 deg) around the shrunken Sun, for comparison"""
        if a <= 0.01: return
        cx, cy = self.C; R = SK["now"]["Rp"] + 1.0
        x0, y0 = int(cx - R - 4), int(cy - R - 4); x1, y1 = int(cx + R + 5), int(cy + R + 5)
        dx = self.xx[y0:y1, x0:x1] + 0.5 - cx; dy = self.yy[y0:y1, x0:x1] + 0.5 - cy
        d = np.sqrt(dx * dx + dy * dy); ang = np.arctan2(dy, dx)
        dash = (np.sin(ang * 8 + t * 1.5) > -0.1).astype(f32)
        ring = np.clip(1.0 - np.abs(d - R) / 0.9, 0, 1) * dash * a
        reg = out[y0:y1, x0:x1]
        reg += ring[..., None] * (np.array([1.0, 1.0, 1.0], f32) - reg) * 0.8
        out[y0:y1, x0:x1] = reg

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
        S = SK[cur]
        x, ys = W / 2, (300, 385, 440)                                    # readout in the upper sky (keeps the chalets clear)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "now" and t > T_SUNBACK: a = ramp(t, T_SUNBACK + 0.9, T_SUNBACK + 1.2)
        if T_WO0 < t < T_SUNBACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            rgba, _ = word_layer(S["name"], int(L.hud_size * 1.4), W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["l2"], x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["l3"], x, ys[2] + dy, int(L.hud_size * 0.46), "Bold", (232, 240, 255), a, 0.10, display=True)
        self.caps.draw(out, t)


def save(im, p): Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR); [print(s["key"], s["d"], "au", round(s["Rp"], 3), "px", round(ang_deg(s["d"]), 4), "deg") for s in STAGES]
        print({k: round(v, 2) for k, v in T_SW.items()}, "winter", round(T_WINTER, 2), "freeze", round(T_FREEZE, 2), "sunback", round(T_SUNBACK, 2)); sys.exit()
    if sys.argv[1] == "seg":
        from lib.v3_kit import render; render(sys.modules[__name__]); sys.exit()
    sc = Scene(); os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); im = sc.frame(t)
        save(im, os.path.join(SCR, "stills", f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
