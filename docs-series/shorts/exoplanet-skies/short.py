"""THE SKIES OF EARTH-LIKE EXOPLANETS -- one locked tripod shot of the farm (06_farm_field_barn): "if this farm were on...".
Our Sun is swapped for each planet's star, drawn at its TRUE angular size as seen from that planet, through one fixed
telephoto lens (f = 5000 px, ~22 deg vertical field of view), with the wheat, barn, silo and oak relit in that star's
colour and (eye-adapted) brightness.
  Earth -> Proxima b (red dwarf 3.2x wider, dim red day, flares) -> TRAPPIST-1e (salmon star 4x wider, sister planets
  as discs in the daytime sky) -> Kepler-16b (two suns) -> Kepler-186f (dim orange-red sun, dark crops)
  -> Kepler-452b (slightly bigger, brighter Sun) -> white-out -> Earth (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py segs                    restart-safe segment render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5            stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py info
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, fbm2, lum, splat, noise1, bbcolor
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-exoplanet-skies"
BG = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/06_farm_field_barn.png"
FPS = 30
LEAD, TAIL = 0.25, 1.30
F_PX = 5000.0                    # one lens for every world: true angular sizes
R_SUN = F_PX * math.tan(math.radians(0.533 / 2))       # our Sun from Earth: 23.3 px
C = (705.0, 560.0)               # the star's place in the sky (clear, above the barn, right of the oak)

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]


def ang_r(R_sun, a_au): return F_PX * math.tan(math.atan(R_sun * 0.00465047 / a_au))   # star radius (R_sun) seen from a (au)


def moon_like_r(R_km, d_km): return F_PX * math.tan(math.asin(R_km / d_km))


# ------------------------------------------------------------------------------------------------ the worlds
# R/a: stellar radius (R_sun) / planet orbit (au) -> apparent size; T: stellar Teff (K). Look: sky zen/hor (linear),
# star disc brightness, foreground light (gain = eye-adapted visible light, tint), readout lines.
W_ = [
    dict(key="earth", R=1.0, a=1.0, T=5772, planet="EARTH", stype="G2V YELLOW DWARF", ly="8 LIGHT-MINUTES", fact="OUR SUN · 0.53° WIDE",
         tc=(255, 236, 170), zen=(0.012, 0.075, 0.42), hor=(0.30, 0.50, 0.85), surf=40.0, glow=1.0, gain=1.0, tint=(1.0, 0.98, 0.95),
         flat=0.0, amb=(0.03, 0.05, 0.09), beams="rainbow", bI=0.85, spots=0.0, crop=0.0, expo=1.0),
    dict(key="prox", R=0.1542, a=0.04857, T=3042, planet="PROXIMA B", stype="M5.5 RED DWARF", ly="4.2 LIGHT-YEARS", fact="SUN 3.2× WIDER · A FLARE STAR",
         tc=(255, 120, 90), zen=(0.030, 0.007, 0.020), hor=(0.20, 0.045, 0.035), surf=1.6, glow=0.55, gain=0.15, tint=(1.0, 0.36, 0.16),
         flat=0.35, amb=(0.030, 0.012, 0.018), beams=[(1.0, 0.15, 0.06), (0.9, 0.08, 0.40), (1.0, 0.40, 0.08)], bI=0.55, spots=1.0, crop=0.0, expo=1.15),
    dict(key="trap", R=0.1192, a=0.02925, T=2566, planet="TRAPPIST-1E", stype="M8 ULTRACOOL DWARF", ly="40 LIGHT-YEARS", fact="SUN 4× WIDER · NEIGHBOURS ~MOON-SIZED",
         tc=(255, 160, 130), zen=(0.050, 0.020, 0.032), hor=(0.27, 0.105, 0.075), surf=1.3, glow=0.6, gain=0.16, tint=(1.0, 0.45, 0.30),
         flat=0.35, amb=(0.035, 0.018, 0.022), beams=[(1.0, 0.45, 0.35), (1.0, 0.65, 0.50), (0.85, 0.30, 0.55), (1.0, 0.30, 0.15)], bI=0.6, spots=0.6, crop=0.0, expo=1.15),
    dict(key="k16", R=0.6489, a=0.7048, T=4450, planet="KEPLER-16B", stype="K + M DWARF PAIR", ly="245 LIGHT-YEARS", fact="A COLD GAS GIANT · THE REAL TATOOINE",
         tc=(255, 200, 120), zen=(0.030, 0.060, 0.26), hor=(0.42, 0.36, 0.38), surf=7.0, glow=1.0, gain=0.75, tint=(1.0, 0.78, 0.55),
         flat=0.0, amb=(0.03, 0.04, 0.07), beams=[(1.0, 0.70, 0.30), (1.0, 0.35, 0.15), (0.5, 0.65, 1.0), (1.0, 0.90, 0.6)], bI=0.75, spots=0.0, crop=0.0, expo=1.0),
    dict(key="k186", R=0.523, a=0.432, T=3755, planet="KEPLER-186F", stype="M1 RED DWARF", ly="580 LIGHT-YEARS", fact="NOON ≈ OUR HOUR BEFORE SUNSET",
         tc=(255, 150, 90), zen=(0.050, 0.035, 0.10), hor=(0.42, 0.17, 0.08), surf=1.8, glow=0.8, gain=0.36, tint=(1.0, 0.55, 0.28),
         flat=0.2, amb=(0.035, 0.022, 0.030), beams=[(1.0, 0.45, 0.12), (1.0, 0.25, 0.10), (0.7, 0.30, 0.55), (1.0, 0.65, 0.30)], bI=0.6, spots=0.3, crop=1.0, expo=1.05),
    dict(key="k452", R=1.11, a=1.046, T=5757, planet="KEPLER-452B", stype="G2 YELLOW DWARF", ly="1,800 LIGHT-YEARS", fact="ITS SUN: 1.5 BILLION YEARS OLDER",
         tc=(255, 230, 160), zen=(0.014, 0.080, 0.44), hor=(0.36, 0.54, 0.86), surf=46.0, glow=1.25, gain=1.12, tint=(1.0, 0.97, 0.90),
         flat=0.0, amb=(0.035, 0.055, 0.095), beams=[(1.0, 0.85, 0.40), (1.0, 0.60, 0.20), (0.6, 0.85, 1.0), (1.0, 0.95, 0.75)], bI=1.0, spots=0.0, crop=0.0, expo=0.95),
]
for w in W_: w["Rp"] = ang_r(w["R"], w["a"])
WK = {w["key"]: w for w in W_}
# Kepler-16B (the M dwarf companion, 0.226 R_sun) drawn beside A, at a mid-orbit separation
K16B = dict(R=0.2262, T=3311, Rp=ang_r(0.2262, 0.7048), off=(-150.0, -70.0))
# TRAPPIST-1 neighbours seen from e near closest approach: (R km, distance km, screen pos, albedo colour)
AU = 1.496e8
TRAP_PL = [("d", 0.788 * 6371, (0.02925 - 0.02227) * AU * 1.05, (420.0, 330.0), (0.85, 0.80, 0.75)),
           ("f", 1.045 * 6371, (0.03849 - 0.02925) * AU * 1.05, (905.0, 300.0), (0.80, 0.88, 1.0)),
           ("c", 1.097 * 6371, (0.02925 - 0.01580) * AU * 1.15, (300.0, 560.0), (0.90, 0.75, 0.62)),
           ("g", 1.129 * 6371, (0.04683 - 0.02925) * AU * 1.1, (540.0, 820.0), (0.75, 0.85, 0.95))]

T_SW = {k: LN[k]["start"] - 0.06 for k in ("prox", "trap", "k16", "k186", "k452")}
T_BACK = LN["end_b"]["start"] - 0.08
T_WO0 = T_BACK - 0.70
ORDER = ["earth", "prox", "trap", "k16", "k186", "k452"]
SWAPS = [(T_SW[k], k) for k in ORDER[1:]] + [(T_BACK, "earth2")]
COLLAPSE, BLOOM = 0.42, 0.65
FLARES = [wt("prox_c", "FLARES") - 0.05, wt("prox_c", "FLARES") + 0.95, T_SW["prox"] + 1.6]
T_NEIGH = wt("trap_c", "NEIGHBOUR") - 0.1
T_DARK = wt("k186_c", "PLANTS") - 0.2
PULSES = [wt("hook_b", "WORLD"), wt("prox_b", "RED"), wt("prox_b", "WIDER"), wt("trap_b", "SUN"), wt("trap_c", "SKY"), wt("k16_b", "SUNS"),
          wt("k186_b", "GOLDEN"), wt("k186_c", "DARK"), wt("k452_b", "COUSIN"), wt("k452_c", "BRIGHTER")]


def star_at(t):
    cur, t0 = "earth", -10.0
    for ts, k in SWAPS:
        if t >= ts: cur, t0 = ("earth" if k == "earth2" else k), ts
    nxt = [ts for ts, k in SWAPS if ts > t]
    return cur, t0, (nxt[0] if nxt else 1e9)


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w):
    if isinstance(a, (tuple, list)): return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


def pal_list(cols, x):
    Cc = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return Cc[i] * (1 - fr) + Cc[i + 1] * fr


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def star_col(T):
    c = bbcolor(T); return c / c.max()


NUM = ("zen", "hor", "glow", "gain", "tint", "flat", "amb", "bI", "crop", "expo")


class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(True); W, H = L.W, L.H
        self.fg = fg = Foreground(BG, L, hz_frac=0.70)
        self.hz = float(fg.horizon)
        hw, hh = W // 2, H // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.dx = xx - C[0]; self.dy = yy - C[1]
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3; self.phi = np.arctan2(self.dy, self.dx)
        self.el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.k_hor = np.exp(-self.el / 0.33)[..., None].astype(f32)
        yyf, xxf = np.mgrid[0:H, 0:W].astype(f32); self.xx, self.yy = xxf, yyf
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 7 + r.uniform(-0.25, 0.25), w=r.uniform(0.15, 0.26), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        a = fg.a
        self.a_hard = np.clip(a / 0.9, 0, 1).astype(f32)
        sh = np.zeros_like(a); sh[10:] = a[:-10]
        self.rim = cv2.GaussianBlur(np.clip(a - sh, 0, 1), (0, 0), 3.0) * a
        self.rim_soft = cv2.GaussianBlur(np.clip(a - np.roll(a, 40, 0), 0, 1), (0, 0), 14.0) * a
        # the wheat: everything below the fence line (frame y ~1345 on), the crop recolour mask
        Y = lum(fg.rgb)
        self.wheat = (smooth(1330, 1380, self.yy) * a).astype(f32)
        self.wheat_y = (Y / max(float(np.percentile(Y[self.wheat > 0.5], 70)), 1e-3)).astype(f32)
        self.spot_tex = fbm2((256, 256), 33, 2.6)
        self.gran = fbm2((256, 256), 34, 1.2)
        emph = {"IMAGINE", "WORLD", "PROXIMA B", "RED", "THREE", "WIDER", "FLARES", "TRAPPIST-1E", "SALMON-PINK", "NEIGHBOUR", "SKY",
                "KEPLER-16B", "TWO", "SUNS", "KEPLER-186F", "GOLDEN", "DARK", "KEPLER-452B", "COUSIN", "BRIGHTER", "HOME", "1,800"}
        self.caps = Captions(L, WORDS, emphasis=emph)
        L.cap_y = 1010

    def up(self, a): return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def mix_params(self, t):
        cur, t0, t1 = star_at(t)
        prev = None
        for i, (ts, k) in enumerate(SWAPS):
            if ts == t0: prev = "earth" if i == 0 else SWAPS[i - 1][1]
        B = WK[cur]
        if prev is None: w, A = 1.0, B
        else: w = ramp(t, t0 - 0.12, t0 + 0.55); A = WK["earth" if prev == "earth2" else prev]
        P = {k: lerp(A[k], B[k], w) for k in NUM}
        if cur == "k186": P["crop"] = ramp(t, T_DARK, T_DARK + 1.2)
        P["beamsA"], P["beamsB"], P["bw"] = A["beams"], B["beams"], w
        return P, cur, t0, t1

    def beams_layer(self, t, P, col_u):
        twist = 2.4 * ease(col_u) ** 1.3
        spin = 0.06 * t + 1.4 * col_u ** 2
        phi = self.phi + twist * np.log(self.d / 30.0)
        reach = 1300 * (1 - 0.7 * ease(col_u)); dd = self.d
        rad = (1 - np.exp(-(dd + 6) / 40)) * (np.exp(-dd / reach) * 0.9 + 0.12 * np.exp(-dd / (reach * 2.2)))
        if col_u > 0: rad = rad * (1 + 0.8 * col_u * (np.sin(dd / 22 + 38 * t) * 0.5 + 0.5) ** 2)
        acc = np.zeros(self.dx.shape + (3,), f32)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            I = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.3) % 1.0
            def colof(bs): return palette(x) if bs == "rainbow" else pal_list(bs, x)
            w = P["bw"]
            c = colof(P["beamsB"]) if w >= 1 else colof(P["beamsA"]) * (1 - w) + colof(P["beamsB"]) * w
            acc += c * (g * I)[..., None]
        return acc * rad[..., None] * 0.30 * P["bI"]

    def sky(self, t, P, col_u, scol):
        sky = np.array(P["zen"], f32) * (1 - self.k_hor) + np.array(P["hor"], f32) * self.k_hor
        aure = np.exp(-self.d / 50) * 0.8 + np.exp(-self.d / 230) * 0.14 + np.exp(-self.d / 700) * 0.05
        sky = sky + (aure * P["glow"])[..., None] * (0.35 + 0.65 * scol)
        return sky, self.beams_layer(t, P, col_u)

    def star(self, img, x, y, r, T, surf, spots, I, t, flare=0.0):
        """limb-darkened disc with starspots / granulation, glow, chromatic spikes"""
        H, W = img.shape[:2]
        sc = star_col(T)
        pad = r * 2.5 + 260
        x0, x1, y0, y1 = max(0, int(x - pad)), min(W, int(x + pad)), max(0, int(y - pad)), min(H, int(y + pad))
        dx = self.xx[y0:y1, x0:x1] + 0.5 - x; dy = self.yy[y0:y1, x0:x1] + 0.5 - y
        d = np.sqrt(dx * dx + dy * dy) + 1e-3
        mu = np.sqrt(np.clip(1 - (d / max(r, 0.6)) ** 2, 0, 1))
        disc = smooth(r + 0.8, r - 0.8, d)
        u = 0.75 if T < 4000 else 0.6
        ld = 1 - u * (1 - mu)
        tx = ((dx / max(r, 1) * 60 + t * 2) % 256).astype(f32); ty = ((dy / max(r, 1) * 60) % 256).astype(f32)
        sp = cv2.remap(self.spot_tex, tx, ty, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        gr = cv2.remap(self.gran, (tx * 2.5) % 256, (ty * 2.5) % 256, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        tex = (1 - spots * 0.55 * smooth(0.9, 1.6, sp)) * (1 + 0.06 * gr)
        reg = img[y0:y1, x0:x1]
        dc = sc ** (2.2 if T < 5000 else 1.0)                                   # cool stars: deep, saturated disc colour
        col = dc * (1 - flare * 0.5) + np.array([0.85, 0.9, 1.0], f32) * flare * 0.5
        reg += (disc * ld * tex * surf * I * (1 + 3 * flare))[..., None] * col
        dd = np.maximum(d - r, 0)
        g = (np.exp(-dd / (0.08 * r + 3)) * 2.0 + np.exp(-dd / (0.5 * r + 22)) * 0.55 + np.exp(-dd / (r + 90)) * 0.12) * (d > r - 1)
        g = g * smooth(pad, pad * 0.7, d)
        reg += (g * I * (0.25 + surf / 60) * (1 + 4 * flare))[..., None] * (0.3 + 0.7 * dc) * (1 + 0.08 * math.sin(t * 2.3))
        if flare > 0.01:                                                       # flare: a bright ribbon + loop on the limb
            ang = np.arctan2(dy, dx)
            dda = (ang - 2.3 + np.pi) % (2 * np.pi) - np.pi
            loop = np.exp(-(dda / 0.25) ** 2) * np.exp(-np.abs(d - r * 1.06) / (0.04 * r + 1)) * 8 * flare
            reg += loop[..., None] * np.array([1.0, 0.85, 0.95], f32)
        for k in range(6):                                                     # chromatic diffraction spikes
            a = k * math.pi / 3 + 0.26
            al = dx * math.cos(a) + dy * math.sin(a); pp = np.abs(-dx * math.sin(a) + dy * math.cos(a))
            base = np.exp(-pp / (1.6 + 0.01 * r)) * (al > r * 0.8)
            for c, Lk in ((0, 1.0), (1, 0.82), (2, 0.66)):
                reg[..., c] += base * np.exp(-np.maximum(al - r, 0) / ((150 + 0.6 * r) * Lk)) * 1.2 * I * (0.4 + 0.6 * sc[c]) * min(surf / 20, 1.0)
        img[y0:y1, x0:x1] = reg

    def planet_disc(self, img, x, y, r, alb, sun_xy, I):
        """a sister planet lit by the star (phase from the star's direction)"""
        def fn(d, dx, dy):
            mu = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
            nx, ny = dx / r, dy / r
            lx, ly = sun_xy[0] - x, sun_xy[1] - y; ln = math.hypot(lx, ly) + 1e-6
            lz = 0.35                                                          # star partly behind -> gibbous / crescent mix
            L_ = np.array([lx / ln * (1 - lz * lz) ** 0.5, ly / ln * (1 - lz * lz) ** 0.5, lz])
            ndl = np.clip(nx * L_[0] + ny * L_[1] + mu * L_[2], 0, 1)
            disc = smooth(r + 0.7, r - 0.7, d)
            band = 1 + 0.08 * np.sin(dy / r * 9 + dx / r * 2)
            v = disc * (ndl ** 0.8 * band * 0.55 + 0.03)
            halo = np.exp(-np.maximum(d - r, 0) / 2.0) * 0.06 * (d > r)
            return (v + halo)[..., None] * np.array(alb, f32) * I
        splat(img, x, y, r + 12, fn)

    def relight(self, P, light, scol, t):
        fg = self.fg
        base = fg.rgb * (1 - P["flat"]) + fg.flat * P["flat"]
        tint = np.array(P["tint"], f32)
        out = base * tint * P["gain"] + fg.flat * np.array(P["amb"], f32)
        out += (self.rim * 0.9 + self.rim_soft * 0.25)[..., None] * (0.4 + 0.6 * scol) * P["gain"] * 0.08
        if P["crop"] > 0:                                                       # Kepler-186f: dark, red-tinted crops
            k = (P["crop"] * self.wheat)[..., None]
            dark = (self.wheat_y[..., None] ** 1.2) * np.array([0.07, 0.010, 0.014], f32) * P["gain"] * 1.6 + out * 0.15
            out = out * (1 - k) + dark * k
        return out * light

    def frame(self, t):
        L = self.L; fg = self.fg
        P, cur, t0, t1 = self.mix_params(t)
        S = WK[cur]
        pulse = 1 + 0.06 * math.sin(2 * math.pi * t / 1.6) + sum(0.45 * math.exp(-((t - tp) / 0.20) ** 2) for tp in PULSES)
        u_in = (t - t0) / BLOOM
        sc = back_out(u_in) if t0 > 0 else 1.0
        col_u = 0.0 if t1 > 1e8 else max(0.0, 1 - (t1 - t) / COLLAPSE)
        I_mul = pulse * (0.4 + 0.6 * min(max(u_in * 3, 0), 1) if t0 > 0 else pulse)
        if col_u > 0:
            if col_u < 0.45: sc *= 1 + 0.30 * ease(col_u / 0.45)
            else: v = (col_u - 0.45) / 0.55; sc *= 1.30 * (1 - ease(v) ** 0.7) + 0.02
            I_mul *= 1 + 3 * col_u ** 2
        flare = sum(math.exp(-max(t - tf, 0) / 0.45) * ramp(t, tf - 0.06, tf) for tf in FLARES if t > tf - 0.06) if cur == "prox" else 0.0
        scol = star_col(S["T"])
        sky, bm = self.sky(t, P, col_u, scol)
        img = self.up(sky * (1 - 0.3 * col_u) * (1 + 0.6 * flare) + bm * (1 + 0.6 * col_u))
        cx, cy = C
        if cur == "trap":                                                      # the sister planets
            for j, (nm, Rk, dk, (px, py), alb) in enumerate(TRAP_PL):
                a_ = ramp(t, T_NEIGH + 0.18 * j, T_NEIGH + 0.18 * j + 0.4) * (1 - col_u)
                if a_ <= 0: continue
                rp = moon_like_r(Rk, dk) * back_out((t - T_NEIGH - 0.18 * j) / 0.5)
                self.planet_disc(img, px, py, max(rp, 0.5), alb, C, 0.9 * a_ * min(pulse, 1.4))
        if cur == "k16":
            bx, by = cx + K16B["off"][0] * sc, cy + K16B["off"][1] * sc
            self.star(img, bx, by, K16B["Rp"] * sc, K16B["T"], 3.0, 0.4, I_mul, t)
        self.star(img, cx, cy, S["Rp"] * sc, S["T"], S["surf"], S["spots"], I_mul, t, flare)
        sky_img = img
        light = (1.0 + 0.10 * (pulse - 1) - 0.2 * col_u) * (1 + 1.2 * flare)
        fgc = self.relight(P, light, scol, t) + self.up(bm) * 0.05 * fg.a[..., None]
        a = self.a_hard[..., None]
        img = sky_img * (1 - a) + fgc * a
        for ts, k in SWAPS:
            u = t - ts
            if -0.05 < u < 1.4 and k != "earth2":
                fc = 0.4 + 0.6 * star_col(WK[k]["T"])
                img += (2.8 * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * fc
                self.shock(img, cx, cy, u, fc)
        if T_WO0 < t < T_BACK:
            v = ease((t - T_WO0) / (T_BACK - T_WO0)); img = img + (30 * v ** 2.5) * np.array([1.0, 0.95, 0.88], f32)
        if T_BACK <= t < T_BACK + 0.6:
            img = img + 30 * math.exp(-(t - T_BACK) / 0.10) * np.array([1.0, 0.95, 0.88], f32)
            self.shock(img, cx, cy, t - T_BACK, np.array([1.0, 0.9, 0.7], f32))
        img = self.chroma_bloom(img, 1.0)
        out = tonemap(img, P["expo"])
        out = self.chroma(out)
        out = finish(out, t, grain=0.008, vignette=0.14)
        self.overlay(out, t, cur, t0)
        return out

    def shock(self, img, cx, cy, u, col):
        R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * 2.0 * math.exp(-max(u, 0) / 0.55) * (0.6 + 0.4 * col[ch])

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.L.W, self.L.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def overlay(self, out, t, cur, t0):
        L = self.L; W = L.W; S = WK[cur]
        x, ys = W / 2, (1190, 1268, 1322, 1372)
        a = ramp(t, max(t0, 0.25) + 0.15, max(t0, 0.25) + 0.45)
        nxt = [ts for ts, k in SWAPS if ts > t]
        if nxt: a *= 1 - ramp(t, nxt[0] - 0.35, nxt[0] - 0.15)
        if cur == "earth" and t > T_BACK: a = ramp(t, T_BACK + 0.6, T_BACK + 0.9)
        if T_WO0 < t < T_BACK: a = 0.0
        if a > 0.01:
            dy = (1 - a) * 18
            rgba, _ = word_layer(S["planet"], int(L.hud_size * 1.30), W * 0.9, fill=S["tc"])
            composite(out, rgba, x, ys[0] + dy, a)
            hud_text(out, S["stype"], x, ys[1] + dy, int(L.hud_size * 0.56), "Black", (255, 255, 255), a, 0.08, display=True)
            hud_text(out, S["ly"], x, ys[2] + dy, int(L.hud_size * 0.50), "Black", (255, 225, 170), a, 0.08, display=True)
            hud_text(out, S["fact"], x, ys[3] + dy, int(L.hud_size * 0.44), "Bold", (235, 240, 250), a, 0.10, display=True)
        self.caps.draw(out, t)


def save_png(im, path):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR)
        for w in W_: print(f"{w['key']:6s} r={w['Rp']:6.1f}px  {w['Rp'] / R_SUN:5.2f}x Sun  {2 * math.degrees(math.atan(w['Rp'] / F_PX)):.3f} deg")
        print("K16B", round(K16B["Rp"], 1), round(K16B["Rp"] / R_SUN, 2))
        for nm, Rk, dk, _, _ in TRAP_PL: print("trappist", nm, round(2 * math.degrees(math.asin(Rk / dk)), 3), "deg", round(moon_like_r(Rk, dk), 1), "px")
        print({k: round(v, 2) for k, v in T_SW.items()}, "back", T_BACK); sys.exit()
    if sys.argv[1] == "segs":
        from lib.v3_redo_q5 import render_segments
        render_segments(sys.modules[__name__]); sys.exit()
    sc = Scene(True); d = os.path.join(SCR, "stills"); os.makedirs(d, exist_ok=True)
    for t in [float(x) for x in sys.argv[2].split(",")]:
        t0 = time.time(); save_png(sc.frame(t), os.path.join(d, f"vert_{t:05.2f}.png")); print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
