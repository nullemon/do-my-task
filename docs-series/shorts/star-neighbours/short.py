"""WHAT IF FAMOUS STARS WERE OUR NEAREST NEIGHBOUR? -- one LOCKED tripod shot of the city at night (C_city.png),
VFX spectacle "swap" format. The real southern sky (HYG v4.1, latitude 34 S, facing south-east, the Southern Cross and the
Pointers over the skyline). Alpha Centauri (4.37 ly) is swapped, one after another, for famous stars placed at the SAME
distance and the SAME point of the sky: brightness from m = M + 5 log10(d / 10 pc), d = 1.34 pc. Each swap: the old star
implodes, a tinted flash, a chromatic shockwave, beams; the new star blooms in. Its light relights the city (rim light,
lit roofs, crisp shadows on the roofs and the street), the sky brightens with scattered starlight and the faint stars
wash out.
  Alpha Centauri -> Sirius -> Vega -> Betelgeuse -> Rigel -> Deneb -> Eta Carinae -> its 1843 eruption (twilight)
  -> white-out -> Alpha Centauri (loops)
Usage (one heavy process, under nice):
  /home/user/ttsenv/bin/python short.py info
  /home/user/ttsenv/bin/python short.py vert                     full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5             stills -> SCR/stills/vert_<t>.png
  /home/user/ttsenv/bin/python short.py patch vert 3.9:5.2       re-render only those time ranges
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image, ImageDraw
from lib.core import f32, Layout, ramp, smooth, ease, splat, lum, fbm2, bbcolor, lin_to_srgb, srgb_to_lin
from lib.foreground import Foreground
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skygeo import eq_vec, eq2hor, Lens, EQ2GAL
from mwsky import canvas, WL, HB, PXD

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-star-neighbours"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/C_city.png"
LAMPS_SRC = [(575, 1496), (703, 1449), (819, 1456), (470, 1386), (237, 1303)]       # street-lamp heads (as in ../solar-storm)
FPS = 30
LEAD, TAIL = 0.25, 1.05
LST0 = 10.85                     # local sidereal time (h): Alpha Centauri 45 deg up in the south-east, Crux above it
HY = 1430.0                      # true horizon row (behind the far skyline)
F_LENS = 930.0
AZ0, ALT0 = 162.778, 34.250      # camera: puts Alpha Centauri at (330, 660)
D_PC = 4.37 / 3.26156
DMOD = 5 * math.log10(D_PC / 10)                 # -4.365
M_MOON = -12.7

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t1" if end else "t0"]


# ------------------------------------------------------------------------------------------------- the stars
# key, name, absolute V magnitude M (None: apparent m given), apparent m at 1.34 pc, colour temperature (K), readout
def app(M): return M + DMOD
STARS = [
    dict(key="ac", name="ALPHA CENTAURI", m=-0.27, T=5600.0,
         l2="MAGNITUDE −0.27 · 4.37 LIGHT-YEARS", l3="OUR NEAREST NEIGHBOUR"),
    dict(key="sir", name="SIRIUS", M=1.42, T=9940.0, l2="MAGNITUDE −2.9 · 12× BRIGHTER THAN NOW", l3="AS BRIGHT AS JUPITER"),
    dict(key="vega", name="VEGA", M=0.58, T=9600.0, l2="MAGNITUDE −3.8 · 26× BRIGHTER THAN NOW", l3="STILL A POINT · 0.02″ WIDE"),
    dict(key="bet", name="BETELGEUSE", M=-5.85, T=3600.0, l2="MAGNITUDE −10.2 · 9,500× BRIGHTER", l3="170× BRIGHTER THAN VENUS"),
    dict(key="rig", name="RIGEL", M=-7.84, T=12100.0, l2="MAGNITUDE −12.2 · 0.6× THE FULL MOON", l3="FROM A POINT 0.5″ WIDE"),
    dict(key="den", name="DENEB", M=-8.4, T=8500.0, l2="MAGNITUDE −12.8 · 1.1× THE FULL MOON", l3="AS BRIGHT AS THE FULL MOON"),
    dict(key="eta", name="ETA CARINAE", M=-8.6, T=22000.0, l2="MAGNITUDE −13.0 · 1.3× THE FULL MOON", l3="5 MILLION × THE SUN'S POWER"),
    dict(key="eru", name="1843 ERUPTION", M=-14.0, T=6500.0, l2="MAGNITUDE −18.4 · 180× THE FULL MOON", l3="17 MILLION × BRIGHTER THAN NOW"),
]
for s in STARS:
    if "M" in s: s["m"] = app(s["M"])
SK = {s["key"]: s for s in STARS}

# ------------------------------------------------------------------------------------------------- timeline
T_LABEL = wt("now", "ALPHA") - 0.05
T_SW = {"sir": wt("sir", "SIRIUS") - 0.10, "vega": wt("vega", "VEGA") - 0.08, "bet": wt("bet", "BETELGEUSE") - 0.08,
        "rig": wt("rig", "RIGEL") - 0.08, "den": wt("den", "DENEB") - 0.08, "eta": wt("eta", "ETA") - 0.08}
T_ERU0 = wt("eta", "1843") - 0.05                       # the eruption builds ...
T_ERU = wt("eta", "OUTBURST") - 0.03                    # ... and bursts
T_TWI = wt("eta2", "NIGHT")                              # the sky goes to twilight
T_WO0 = wt("eta2", "TWILIGHT") + 0.15                    # white-out builds through "twilight"
T_BACK = LN["end"]["start"] - 0.02                      # snap back to Alpha Centauri
SEQ = [(0.0, "ac")] + [(T_SW[k], k) for k in ("sir", "vega", "bet", "rig", "den", "eta")] + [(T_ERU, "eru"), (T_BACK, "ac")]
T_SHADOW = wt("bet2", "SHADOWS")


def mag_to_E(m):
    """display illuminance of the city / sky (0..1): log of the flux relative to the full Moon"""
    lv = -0.4 * (m - M_MOON)
    return float(np.clip((lv + 1.8) / 4.0, 0, 1))


def q_of(m):
    """display 'size' of the glare: linear in magnitude (log flux)"""
    return float(np.clip((-m + 1.0) / 19.4, 0, 1))


def cur_state(t):
    """-> dict(m, T, q, E, I (core gain), key, ts (swap time), flash)"""
    i = max(j for j, (ts, k) in enumerate(SEQ) if t >= ts)
    ts, k = SEQ[i]; s = SK[k]
    nxt = SEQ[i + 1][0] if i + 1 < len(SEQ) else 1e9
    m, T = s["m"], s["T"]
    if k == "eta" and t > T_ERU0:                                   # Eta Carinae swells into the 1843 eruption
        u = ramp(t, T_ERU0, T_ERU)
        m = s["m"] + (SK["eru"]["m"] - s["m"]) * 0.25 * u ** 2; T = s["T"] + (8000 - s["T"]) * u
    if k == "eru":
        u = ramp(t, T_ERU, T_ERU + 1.2)
        T = 9000 + (s["T"] - 9000) * u
    # implosion before the next swap (not into the eruption, which grows)
    imp = 0.0
    if k != "eta" and nxt < 1e8: imp = ramp(t, nxt - 0.30, nxt)
    if k == "eru": imp = 0.0
    u = t - ts
    bloom_k = 1 + (1.6 * math.exp(-u / 0.30) if i > 0 else 0.0)
    q = q_of(m); E = mag_to_E(m)
    if k == "eru": E = E * (0.72 + 0.28 * ramp(t, T_TWI - 0.3, T_TWI + 0.6))
    I = (1 - 0.85 * imp) * bloom_k * (1 + 0.3 * math.sin(t * 2.3) * 0.1)
    # the city light follows with a short attack, and sinks during the implosion
    att = ramp(u, 0.0, 0.45) if i > 0 else 1.0
    if i > 0:
        pm = SK[SEQ[i - 1][1]]["m"] if SEQ[i - 1][1] != "eta" else SK["eta"]["m"]
        Ep = mag_to_E(pm) if k != "eru" else mag_to_E(SK["eta"]["m"])
        E = Ep * (1 - att) + E * att
    E *= (1 - 0.6 * imp)
    return dict(m=m, T=T, q=q * (1 - 0.5 * imp), E=E, I=I, key=k, ts=ts, i=i, imp=imp)


def whiteout(t):
    return ramp(t, T_WO0, T_BACK) ** 1.6 * (1 - ramp(t, T_BACK, T_BACK + 0.55))


# ------------------------------------------------------------------------------------------------- helpers
def palette(x):
    x = np.asarray(x, f32)[..., None]
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


def pal_list(cols, x):
    C = np.array(cols + [cols[0]], f32); n = len(cols)
    p = (np.asarray(x) % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return C[i] * (1 - fr) + C[i + 1] * fr


def bv_temp(ci):
    return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


def vivid(c, k=1.4):
    c = np.asarray(c, f32); y = float(lum(c)); return np.clip(y + (c - y) * k, 0.0, None) / max(y, 1e-4)


def star_col(T, k=1.5):
    return vivid(bbcolor(T), k)


def shift(m, dx, dy):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(m, M, (m.shape[1], m.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def poly_mask(shape, pts, Q=4):
    m = np.zeros((shape[0] * Q, shape[1] * Q), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts, np.float64) * Q).astype(np.int32)], 255, cv2.LINE_AA)
    return cv2.resize(m.astype(f32) / 255, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


# ------------------------------------------------------------------------------------------------- city
class City:
    """Light decomposition of the dusk plate (as ../solar-storm City): D (lights off) + window light + lamp light,
    a night grade, and the star's light: directional rim/top light (march towards the star until the sky), lit roofs and
    the street with crisp cast shadows (left-roof plant room, parapet, street trees, lamp posts)."""
    def __init__(self, fg, L, star_xy):
        self.fg = fg; W, H = L.W, L.H; s, oy = fg.s, fg.oy
        P = fg.rgb; a = fg.a
        sr = lin_to_srgb(P); R, G, B = sr[..., 0], sr[..., 1], sr[..., 2]
        Y = 0.2126 * R + 0.7152 * G + 0.0722 * B
        Ym = cv2.GaussianBlur(Y * a, (0, 0), 4.0 * s) / np.maximum(cv2.GaussianBlur(a, (0, 0), 4.0 * s), 1e-3)
        warm = (R - B > 0.10) & (R > 0.40)
        peak = (Y - Ym > 0.045) | (Y > 0.62)
        win = (warm & peak & (a > 0.9)).astype(np.uint8)
        win = cv2.morphologyEx(win, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        self.lamps = [(x * s, y * s + oy) for x, y in LAMPS_SRC]
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        Gs = []
        for lx, ly in self.lamps:
            dy = yy - ly; ry = np.where(dy > 0, 150 * s, 60 * s)
            Gs.append(np.exp(-((xx - lx) / (95 * s)) ** 2 - (dy / ry) ** 2))
        gsum = np.stack(Gs).sum(0)
        chroma = np.clip(((R - B) / np.maximum(R + G + B, 1e-3) - 0.08) / 0.25, 0, 1)
        glow = cv2.GaussianBlur(np.clip(gsum * 1.3, 0, 1) * chroma * a, (0, 0), 1.2)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(win, 8)
        near = gsum[np.clip(cent[:, 1].astype(int), 0, H - 1), np.clip(cent[:, 0].astype(int), 0, W - 1)]
        is_lamp = (near > 0.35) & (stats[:, cv2.CC_STAT_AREA] < 4000); is_lamp[0] = False
        winmask = (lab > 0) & ~is_lamp[lab]
        Wm = cv2.GaussianBlur(cv2.dilate(winmask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(f32), (0, 0), 0.7)
        Wm = np.clip(Wm * 1.4, 0, 1) * a
        self.label = cv2.dilate((lab * winmask).astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
        self.n = n; self.ph = np.random.default_rng(3).uniform(0, 100, n).astype(f32)
        u8 = (np.clip(sr, 0, 1) * 255 + 0.5).astype(np.uint8)
        im = cv2.inpaint(u8, cv2.dilate(winmask.astype(np.uint8), np.ones((5, 5), np.uint8)), 5, cv2.INPAINT_TELEA)
        dark_glass = srgb_to_lin(im.astype(f32) / 255) * np.array([0.30, 0.33, 0.40], f32)
        Yl = lum(P)[..., None]
        D = P * (1 - Wm[..., None]) + dark_glass * Wm[..., None]
        g3 = glow[..., None]
        D = D * (1 - g3) + np.minimum(D, Yl * 0.30 * np.array([0.85, 0.92, 1.10], f32)) * g3
        heads = np.zeros((H, W), f32)
        for lx, ly in self.lamps: heads += np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * (7 * s) ** 2))
        heads = np.clip(heads * 1.5, 0, 1) * a
        D = D * (1 - heads[..., None]) + np.minimum(D, Yl * 0.15) * heads[..., None]
        self.D = D.astype(f32)
        self.Lw = (np.maximum(P - D, 0) * Wm[..., None] * (1 - g3)).astype(f32)
        self.Lg = (np.maximum(P - D, 0) * np.maximum(g3, heads[..., None])).astype(f32)
        Yd = lum(D)[..., None]
        self.night = ((D * 0.30 + Yd * 0.70) * np.array([0.55, 0.72, 1.20], f32) * 0.11).astype(f32)
        self.alb = (D / (Yd * 2.2 + 0.03)).astype(f32) * a[..., None]
        self.alb = np.clip(self.alb, 0, 1.6)
        # ---- directional light from the star: march towards it (screen) until the sky
        sx, sy = star_xy
        cx, cy = W * 0.5, H * 0.75
        ux, uy = sx - cx, sy - cy; nn = math.hypot(ux, uy); ux, uy = ux / nn, uy / nn
        ds = np.full((H, W), 400.0, f32); open_ = a < 0.5
        aa = a.copy()
        for k in list(range(1, 40)) + list(range(40, 400, 6)):
            sh_ = shift(aa, -ux * k, -uy * k)                       # value at p + k u
            hit = (sh_ < 0.5) & (ds > 399)
            ds[hit] = k
        self.rim = (np.exp(-ds / 7.0) * a).astype(f32)
        self.open = (np.exp(-ds / 140.0) * a).astype(f32)
        self.top = smooth(H, fg.horizon - 260 * s, yy).astype(f32)
        # ---- surfaces lit by the star (SOURCE px polygons) and their cast shadows
        Hs, Ws = int(round(1672)), 941
        def S2O(m):
            M = np.array([[s, 0, 0], [0, s, oy]], np.float64)
            return cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(f32)
        shp = (Hs, Ws)
        roofL = poly_mask(shp, [(0, 1303), (312, 1306), (386, 1326), (386, 1350), (110, 1350), (110, 1392), (0, 1388)])
        plant = poly_mask(shp, [(166, 1311), (312, 1309), (312, 1340), (166, 1344)])
        roofN = poly_mask(shp, [(578, 1598), (872, 1467), (941, 1462), (941, 1652), (675, 1607)])
        box = poly_mask(shp, [(866, 1517), (941, 1512), (941, 1642), (866, 1632)])
        street = poly_mask(shp, [(497, 1600), (520, 1548), (640, 1505), (760, 1462), (845, 1432), (870, 1440), (740, 1520), (640, 1585), (600, 1610)])
        # light comes from the star's azimuth: on the ground, shadows run away from the point below the star
        vx, vy = sx / s, HY / s
        def smear(m, ln, base, n=24):
            dx, dy = base[0] - vx, base[1] - vy; d = math.hypot(dx, dy); dx, dy = dx / d, dy / d
            acc = np.zeros_like(m)
            for j in range(n + 1):
                acc = np.maximum(acc, shift(m, dx * ln * j / n, dy * ln * j / n))
            return acc
        shL = smear(plant, 46, (240, 1330)) * roofL * (1 - plant)
        lip = poly_mask(shp, [(578, 1594), (872, 1463), (941, 1458), (941, 1466), (874, 1472), (580, 1602)])
        shN = np.clip(smear(lip, 14, (720, 1530)) * roofN * (1 - lip) + smear(box, 120, (900, 1630)) * roofN * (1 - box), 0, 1)
        # street trees (green, dark, opaque) and the lamp posts
        sra = np.asarray(Image.open(FG_PATH).convert("RGBA"), f32) / 255
        r_, g_, b_ = sra[..., 0], sra[..., 1], sra[..., 2]
        tree = ((g_ > r_ * 0.85) & (g_ > b_ * 1.05) & (sra[..., 3] > 0.5)).astype(f32)
        tree = cv2.morphologyEx(tree, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) * (1 - street)
        posts = np.zeros(shp, f32)
        for (hx, hy_), by in (((575, 1496), 1592), ((703, 1449), 1532)):
            cv2.line(posts, (int(hx), int(hy_)), (int(hx - 2), int(by)), 1.0, 3, cv2.LINE_AA)
        shS = np.clip(smear(tree, 40, (600, 1540)) + smear(posts, 70, (600, 1580)), 0, 1) * street
        def soft(m): return cv2.GaussianBlur(m, (0, 0), 0.8)
        # the three tall towers throw long shadows away from the star onto the lower roofs and blocks in front of them
        towers = np.clip(poly_mask(shp, [(8, 1112), (170, 1112), (172, 1300), (8, 1300)])
                         + poly_mask(shp, [(606, 962), (730, 975), (732, 1268), (606, 1268)])
                         + poly_mask(shp, [(812, 1082), (925, 1088), (928, 1268), (812, 1268)]), 0, 1)
        midroof = poly_mask(shp, [(455, 1262), (941, 1258), (941, 1284), (455, 1288)])
        tsh = np.zeros(shp, f32)
        for bx, by, ln in ((90, 1300, 150), (668, 1268, 260), (870, 1268, 200)):
            dx, dy = bx - vx, by - vy; d = math.hypot(dx, dy); dx, dy = dx / d, max(dy / d, 0.35)
            m = towers * (np.abs(np.arange(Ws)[None, :] - bx) < 90)
            acc = np.zeros(shp, f32)
            for j in range(0, 41):
                acc = np.maximum(acc, shift(m, dx * ln * j / 40, dy * ln * j / 40) * (1 - 0.35 * j / 40))
            tsh = np.maximum(tsh, acc)
        tsh = cv2.GaussianBlur(tsh * (1 - towers) * (sra_a := (np.asarray(Image.open(FG_PATH).convert("RGBA"))[..., 3] > 127).astype(f32)), (0, 0), 2.0)
        self.tshadow = S2O(np.clip(tsh, 0, 1)).astype(f32)
        self.surf = S2O(np.clip(roofL * 0.9 + roofN * 1.0 + street * 0.85 + midroof * 0.9, 0, 1)).astype(f32)
        self.shadow = S2O(soft(np.clip(shL + shN + shS, 0, 1))).astype(f32)
        self.treeO = S2O(tree)
        self.yy = yy

    def render(self, t, E, c, amb_col, tw, beat=0, tb=10.0):
        """E: star illuminance (0..1), c: star colour, amb_col: scattered skylight colour, tw: twilight level
        beat: index of the current star; tb: time since its swap (windows switch as people react to the new star)"""
        def state(b):
            b = 0 if b >= 8 else b                                          # the final beat matches the opening (loop)
            return (np.random.default_rng(100 + b).uniform(0, 1, self.n) < 0.80 + 0.025 * b).astype(f32)
        on = state(beat)
        if beat > 0:
            prev = state(beat - 1)
            delay = np.random.default_rng(200 + beat).uniform(0.2, 2.0, self.n)
            on = np.where(tb < delay, prev, on)
        on *= 0.92 + 0.08 * np.sin(t * 1.3 + self.ph)                       # windows breathe a little
        on[0] = 0
        wmap = on[self.label][..., None]
        img = self.night + self.Lw * wmap * 1.25 + self.Lg * 1.15
        if E > 0:
            lit = (self.surf * (1 - 0.88 * self.shadow) * 1.1 + self.rim * 1.6 + self.open * 0.35 * (0.4 + 0.6 * self.top))
            lit = lit * (1 - 0.8 * self.tshadow * smooth(0.12, 0.3, E))
            img = img + self.alb * c * (E * 4.0) * lit[..., None] + self.D * c * (E * 0.9)
        if tw > 0:                                                         # scattered skylight on everything
            img = img + self.alb * amb_col * (0.30 * tw) * (0.5 + 0.5 * self.top)[..., None]
        return img.astype(f32)


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        assert vertical, "9:16 only"
        self.L = L = Layout(True); W, H = L.W, L.H; self.W, self.H = W, H
        self.fg = fg = Foreground(FG_PATH, L, hz_frac=0.70)
        self.lens = Lens(W, H, AZ0, ALT0, F_LENS, HY)
        L.cap_y = 960
        self.caps = Captions(L, WORDS, emphasis={"BRIGHTEST", "NEIGHBOUR", "ALPHA", "CENTAURI", "SIRIUS", "JUPITER", "VEGA", "DOT",
                                                 "BETELGEUSE", "HUNDRED", "VENUS", "SHADOWS", "RIGEL", "BLUE-WHITE", "MOON",
                                                 "POINT", "DENEB", "ETA", "CARINAE", "MILLION", "1843", "OUTBURST", "MOONS",
                                                 "TWILIGHT", "LUCKY", "SMALL"})
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(f32)
        self.a = fg.a[..., None]
        rays = self.lens.rays(1); alt = np.arcsin(np.clip(rays[..., 2], -1, 1)); e = np.clip(alt / (np.pi / 2), 0, 1)
        self.e = e.astype(f32)
        k = np.exp(-e / 0.25)[..., None]
        zen = np.array([0.006, 0.010, 0.050], f32); hor = np.array([0.030, 0.036, 0.115], f32)
        night = zen * (1 - k) + hor * k
        night += np.exp(-e / 0.06)[..., None] * np.array([0.075, 0.040, 0.030], f32)      # city light dome
        night += np.exp(-((e - 0.40) / 0.22) ** 2)[..., None] * np.array([0.010, 0.002, 0.020], f32)
        n = cv2.resize(fbm2((96, 96), 61, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        self.night = (night * (1 + 0.06 * n)[..., None]).astype(f32)
        # twilight sky lit by the star: Rayleigh blue gradient, brighter low down
        kd = np.exp(-e / 0.20)[..., None]
        self.twi = ((np.array([0.012, 0.055, 0.36], f32) * (1 - kd) + np.array([0.10, 0.22, 0.58], f32) * kd)).astype(f32)
        self.above = smooth(-0.01, 0.04, alt).astype(f32)[..., None]
        mw = canvas(os.path.join(SCR, "mw_gal.npz"))
        M = EQ2GAL @ eq2hor(LST0).T
        g = rays @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = (WL / 2 + np.degrees(l) * PXD) % WL; my = HB / 2 - np.degrees(b) * PXD
        self.mw = (cv2.remap(mw, mx.astype(f32), my.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP) * 3.2
                   * self.above * smooth(0.02, 0.25, e)[..., None]).astype(f32)
        self.ag_src = fbm2((128, 256), 77, 2.2)
        self.ag_band = (np.exp(-e / 0.10) * smooth(-0.01, 0.02, alt)).astype(f32)
        del rays
        # ---- catalogue stars
        z = np.load(os.path.join(SCR, "stars.npz"))
        v = eq_vec(z["ra"], z["dec"]) @ eq2hor(LST0).T
        x, y, ok = self.lens.project(v)
        sel = ok & (v[:, 2] > 0) & (x > -4) & (x < W + 4) & (y > -4) & (y < H + 4)
        names = z["name"]
        ia = np.where(names == "Rigil Kentaurus")[0][0]
        self.C = (float(x[ia]), float(y[ia]))
        near = np.hypot(x - x[ia], y - y[ia]) < 2.0                         # Alpha Cen A + B: drawn as the hero star
        sel &= ~near
        self.named = {nm: (float(x[i]), float(y[i])) for nm in ("Hadar", "Acrux", "Mimosa", "Gacrux") for i in np.where(names == nm)[0][:1]}
        self.sx, self.sy = x[sel].astype(f32), y[sel].astype(f32); mag = z["mag"][sel]; self.smag = mag
        self.sz = v[sel, 2].astype(f32)
        self.sflux = (4.5 * 10 ** (-0.4 * 0.90 * mag)).astype(f32)
        T = np.clip(bv_temp(np.clip(z["ci"][sel], -0.4, 2.0)), 2600, 30000)
        cols = np.stack([bbcolor(tt) for tt in T]); yv = cols @ np.array([0.2126, 0.7152, 0.0722])
        cols = yv[:, None] + (cols - yv[:, None]) * 1.7
        cols = np.clip(cols, 0.02, None); cols /= (cols @ np.array([0.2126, 0.7152, 0.0722]))[:, None]
        self.scol = cols.astype(f32)
        self.sph = np.random.default_rng(3).uniform(0, 1000, len(mag)).astype(f32)
        self.sd = np.hypot(self.sx - self.C[0], self.sy - self.C[1]).astype(f32)
        self.glint = np.where(mag < 1.6)[0]
        # ---- geometry around the hero star
        cx, cy = self.C
        self.dx, self.dy = self.xx - cx, self.yy - cy
        self.d = np.sqrt(self.dx ** 2 + self.dy ** 2) + 1e-3
        self.phi = np.arctan2(self.dy, self.dx)
        hw, hh = W // 2, H // 2
        self.hd = cv2.resize(self.d, (hw, hh), interpolation=cv2.INTER_AREA); self.hphi = cv2.resize(self.phi, (hw, hh), interpolation=cv2.INTER_NEAREST)
        self.spikes = self._spikes()
        r = np.random.default_rng(5)
        self.beams = [dict(a=i * 2 * np.pi / 10 + r.uniform(-0.2, 0.2), w=r.uniform(0.08, 0.17), I=r.uniform(0.7, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(10)]
        self.homunculus = self._homunculus()
        self.city = City(fg, L, self.C)
        self.airx = None

    # -------------------------------------------------------------------------------------------- precomputation
    def _spikes(self):
        out = []
        for k in range(8):
            a = k * math.pi / 4 + math.radians(9)
            al = self.dx * math.cos(a) + self.dy * math.sin(a); pp = -self.dx * math.sin(a) + self.dy * math.cos(a)
            wdt = 2.3 if k % 2 == 0 else 1.5
            m = (np.abs(pp) < 30) & (al > 0)
            idx = np.flatnonzero(m)
            out.append(dict(idx=idx, pp=pp.ravel()[idx].astype(f32), al=al.ravel()[idx].astype(f32), w=wdt, long=(k % 2 == 0)))
        return out

    def _homunculus(self):
        """Eta Carinae's bipolar dusty nebula: ~0.2 pc long -> ~8.5 deg across from 1.34 pc (~140 px)"""
        L = 2 * F_LENS * math.tan(math.radians(8.5 / 2)) / 2           # half length (px)
        pa = math.radians(-50)
        u = (self.dx * math.cos(pa) + self.dy * math.sin(pa)) / L; v = (-self.dx * math.sin(pa) + self.dy * math.cos(pa)) / L
        lobe = np.zeros_like(u)
        for sgn in (1, -1):
            uu = sgn * u
            r = np.sqrt(((uu - 0.52) / 0.50) ** 2 + (v / 0.36) ** 2)
            shell = np.exp(-((r - 0.82) / 0.20) ** 2) + 0.45 * np.exp(-(r / 0.7) ** 2)
            lobe += shell * (uu > -0.02)
        skirt = np.exp(-(u / 0.07) ** 2) * np.exp(-(np.abs(v) / 0.55) ** 2) * 0.5
        n = cv2.resize(fbm2((128, 128), 9, 2.2), (self.W, self.H), interpolation=cv2.INTER_CUBIC)
        neb = (lobe * (0.75 + 0.5 * n) + skirt) * np.exp(-(np.hypot(u, v) / 1.6) ** 4)
        col = np.array([1.0, 0.55, 0.38], f32)
        return (neb[..., None] * col).astype(f32)

    # -------------------------------------------------------------------------------------------- layers
    def stars_layer(self, t, E, q):
        W, H = self.W, self.H
        acc = np.zeros((H + 2, W + 2, 3), f32)
        nt = np.sin(t * 13.1 + self.sph) * 0.5 + np.sin(t * 23.7 + self.sph * 1.7) * 0.3 + np.sin(t * 37.3 + self.sph * 2.3) * 0.2
        sig = np.clip(0.10 + 0.35 * np.exp(-self.sz / 0.15), 0.08, 0.6)
        tw = np.exp(sig * nt * 1.6 - 0.5 * sig * sig)
        ext = np.clip(self.sz / 0.12, 0, 1) ** 0.7
        lim = 6.8 - 9.0 * E                                                   # scattered starlight washes out the faint stars
        lim_loc = lim - 3.0 * q * np.exp(-self.sd / (60 + 500 * q))          # and the glare around the star
        vis = np.clip((lim_loc - self.smag) / 0.8, 0, 1)
        fl = self.sflux * tw * ext * vis
        m = fl > 1e-4
        xs, ys = self.sx[m], self.sy[m]; val = (fl[m, None] * self.scol[m]).astype(f32)
        x0 = np.floor(xs).astype(int); y0 = np.floor(ys).astype(int); fx = (xs - x0)[:, None]; fy = (ys - y0)[:, None]
        for oy, ox, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(acc, (np.clip(y0 + oy, 0, H + 1), np.clip(x0 + ox, 0, W + 1)), val * wg)
        acc = acc[:H, :W]
        for j in self.glint:
            if vis[j] <= 0: continue
            g = self.sflux[j] * 0.05 * vis[j] * (1 + 0.3 * math.sin(t * 5 + self.sph[j])); c = self.scol[j] * 0.6 + 0.4
            splat(acc, self.sx[j], self.sy[j], 50, lambda d, dx, dy: ((np.exp(-np.abs(dy) / 0.8) * np.exp(-np.abs(dx) / 14) + np.exp(-np.abs(dx) / 0.8) * np.exp(-np.abs(dy) / 14)) * g)[..., None] * c)
        st = cv2.GaussianBlur(acc, (0, 0), 0.7) * 2.4
        big = acc * (acc.max(2, keepdims=True) > 0.35)
        st += cv2.GaussianBlur(big, (0, 0), 2.2) * 2.2 + cv2.GaussianBlur(big, (0, 0), 8.0) * 2.0
        return st

    def beams_layer(self, t, I, col_list):
        d, phi = self.hd, self.hphi
        acc = np.zeros(d.shape + (3,), f32)
        spin = 0.05 * t
        rad = (1 - np.exp(-(d + 4) / 25)) * (np.exp(-d / 1100) * 0.9 + 0.12)
        for b in self.beams:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            gg = np.exp(-(dp / wd) ** 2 * 1.6)
            Ib = b["I"] * (0.70 + 0.30 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.30 + t * 0.05) % 1.0
            acc += pal_list(col_list, x) * (gg * Ib)[..., None]
        return acc * rad[..., None] * 0.45 * I

    def hero(self, img, t, st):
        """the star: HDR core, halo scaled by magnitude, chromatic 8-blade spikes (length ~ magnitude)"""
        q, I = st["q"], st["I"]
        if I <= 0.01: return
        c = star_col(st["T"]); cw = c * 0.45 + 0.55
        pul = 1 + 0.05 * math.sin(t * 3.1) + 0.03 * math.sin(t * 8.7) + 0.04 * math.sin(t * 17.3) * (1 - q)
        d = self.d
        core = 2.5 + 60 * q ** 1.3
        r1 = 3.0 + 14 * q; r2 = 14 + 160 * q ** 1.2; r3 = 60 + 900 * q ** 1.5
        h = (np.exp(-(d / 1.8) ** 2) * core + np.exp(-d / r1) * (0.8 + 5 * q) + np.exp(-d / r2) * (0.05 + 0.55 * q ** 1.5)) * I * pul
        img += h[..., None] * cw
        img += (np.exp(-d / r3) * (0.01 + 0.10 * q ** 2) * I)[..., None] * c
        flat = img.reshape(-1, 3)
        Ls = (110 + 75 * max(-st["m"], 0)) * min(I, 1.8) ** 0.5
        amp = (0.35 + 3.0 * q) * I
        for s in self.spikes:
            L = Ls * (1.0 if s["long"] else 0.42) * pul
            base = np.exp(-np.abs(s["pp"]) / s["w"]) * amp
            for ch, Lk, off in ((0, 1.0, 1.2), (1, 0.84, 0.0), (2, 0.70, -1.2)):
                prof = np.exp(-np.abs(s["pp"] - off) / s["w"]) / np.maximum(np.exp(-np.abs(s["pp"]) / s["w"]), 1e-9)
                flat[s["idx"], ch] += base * prof * np.exp(-s["al"] / (L * Lk)) * (0.45 + 0.55 * c[ch])
            if s["long"] and q > 0.15:
                pc = palette((s["al"] / 520.0 - t * 0.15) % 1.0)
                flat[s["idx"]] += (np.exp(-np.abs(s["pp"]) / (s["w"] * 4)) * np.exp(-s["al"] / (L * 1.4)) * 0.40 * I * q)[:, None] * pc * smooth(40, 220, s["al"])[:, None]

    def shockwave(self, t, t0, R1=2600, dur=1.6, k=2.2):
        u = t - t0
        if not (0 <= u < dur): return None
        R = R1 * (u / dur) ** 0.62; wdt = 10 + 40 * u
        d = self.hd * 2
        ring = np.zeros(d.shape + (3,), f32)
        for ch, off in ((0, 16), (1, 0), (2, -16)):
            ring[..., ch] = np.exp(-((d - R - off) / wdt) ** 2)
        ring += palette((d / 700 - t * 0.6) % 1.0) * np.exp(-((d - R + 70) / (wdt * 3)) ** 2)[..., None] * 0.5
        return ring * k * math.exp(-u / (dur * 0.45))

    def god_rays(self, img, amt):
        W, H = self.W, self.H; q = 4
        sm = cv2.resize(img * (1 - self.a), (W // q, H // q), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 0.6, 0)
        cx, cy = self.C[0] / q, self.C[1] / q
        acc = sm.copy()
        for k in range(6):
            s = 1.0 - 0.12 / (2 ** (k * 0.5))
            M = np.float32([[s, 0, (1 - s) * cx], [0, s, (1 - s) * cy]])
            acc = (acc + cv2.warpAffine(acc, M, (W // q, H // q), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)) * 0.5
            acc = acc * 1.6
        return cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * amt * 0.25

    def airglow_layer(self, t):
        if self.airx is None:
            q = 4; W, H = self.W, self.H
            self.airx = np.mgrid[0:H // q, 0:W // q].astype(f32)[::-1] * q
            self.agb = cv2.resize(self.ag_band, (W // q, H // q), interpolation=cv2.INTER_AREA)
        xx, yy = self.airx
        u = (xx * 0.05 + t * 2.0) % 256; v = (yy * 0.08) % 128
        n1 = cv2.remap(self.ag_src, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        n2 = cv2.remap(self.ag_src, ((xx * 0.03 - t * 1.4 + 90) % 256).astype(f32), ((yy * 0.05 + 40) % 128).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        g = np.clip(0.5 + 0.7 * n1, 0, 1)[..., None] * np.array([0.02, 0.07, 0.05], f32) + np.clip(0.5 + 0.7 * n2, 0, 1)[..., None] * np.array([0.06, 0.015, 0.06], f32)
        g = g * self.agb[..., None]
        return cv2.resize(g, (self.W, self.H), interpolation=cv2.INTER_LINEAR)

    # -------------------------------------------------------------------------------------------- frame
    def frame(self, t):
        W, H = self.W, self.H
        st = cur_state(t)
        E, q, T = st["E"], st["q"], st["T"]
        c = star_col(T)
        tw = E ** 1.5                                                        # scattered-light sky level
        # ---- sky
        sky = self.night * (1 + 0.08 * math.sin(t * 0.7))
        sky = sky + self.mw * (1 - 0.95 * min(E * 1.6, 1.0))
        sky = sky + self.airglow_layer(t) * (1 - tw)
        if tw > 0:
            amb = self.twi * (0.75 + 0.25 * c / max(c.max(), 1e-3))
            sky = sky + amb * (tw * 1.0)
        if E > 0:                                                           # forward-scattering aureole, tinted by the star
            sky = sky + (np.exp(-self.d / (150 + 520 * q)) * (0.55 * E + 0.12 * tw))[..., None] * (c * 0.85 + 0.15)
        sky = sky + self.stars_layer(t, E, q) * self.above
        if st["key"] == "eta":                                               # the Homunculus nebula around Eta Carinae
            a = ramp(t, st["ts"], st["ts"] + 0.6) * (1 - ramp(t, T_ERU0, T_ERU))
            sky = sky + self.homunculus * (0.35 * a * (1 + 0.05 * math.sin(t * 2)))
        if st["key"] == "eru":
            a = ramp(t, T_ERU + 0.5, T_ERU + 1.5) * (1 - ramp(t, T_WO0, T_BACK))
            sky = sky + self.homunculus * (0.6 * a)
        # beams: a burst at every swap, and a steady fan for the brilliant ones
        u = t - st["ts"]
        bl = (0.9 * math.exp(-u / 1.0) if st["i"] > 0 else 0.0) + 0.55 * smooth(0.40, 0.75, q)
        if bl > 0.02:
            if T < 7000:
                cl = [(1.0, 0.45, 0.12), (1.0, 0.25, 0.30), (1.0, 0.70, 0.20), (1.0, 0.40, 0.55), (1.0, 0.60, 0.15)]
            else:
                cl = [(0.55, 0.75, 1.0), (0.85, 0.45, 1.0), (0.30, 1.0, 0.95), (1.0, 0.55, 0.85), (0.6, 0.95, 1.0)]
            bm = self.beams_layer(t, bl * (0.5 + q), cl)
            sky = sky + cv2.resize(bm, (W, H), interpolation=cv2.INTER_LINEAR)
        # ---- city
        amb_col = (self.twi[200, 540] * 2.0).astype(f32)
        cityimg = self.city.render(t, E, c / max(c.max(), 1e-3), amb_col, tw, st['i'], t - st['ts'])
        img = sky * (1 - self.a) + cityimg * self.a
        # ---- the star
        self.hero(img, t, st)
        # ---- swap flashes, shockwaves
        for ts, k in SEQ[1:]:
            uu = t - ts
            if -0.05 < uu < 1.8:
                ck = star_col(SK[k]["T"])
                big = 1.6 if k in ("eru",) else (0.6 if k in ("ac",) else 1.0)
                fl = math.exp(-max(uu, 0) / 0.10) * ease((uu + 0.05) / 0.05)
                img += (fl * big * (np.exp(-self.d / 220) * 3.0 + 0.25))[..., None] * (ck * 0.5 + 0.5)
                ring = self.shockwave(t, ts, 2700 if k == "eru" else 2400, 1.6, 2.2 * big)
                if ring is not None: img += cv2.resize(ring * (ck * 0.35 + 0.65), (W, H), interpolation=cv2.INTER_LINEAR)
        if T_ERU0 <= t < T_ERU:                                               # Eta Carinae swells before it bursts
            uu = (t - T_ERU0) / (T_ERU - T_ERU0)
            img += (np.exp(-self.d / 60) * 3 * uu ** 3 + np.exp(-self.d / 300) * 0.4 * uu ** 4)[..., None] * np.array([1.0, 0.95, 0.9], f32)
        if q > 0.3:
            img += self.god_rays(img, min((q - 0.3) * 2.5, 1.5)) * (1 - 0.8 * self.a)
        wo = whiteout(t)
        if wo > 0: img = img * (1 - wo) + (img + 6.0) * wo
        img = self.chroma_bloom(img, 0.75 + 0.25 * q)
        expo = 1.30 / (1 + 1.1 * tw)
        out = tonemap(img, expo)
        out = self.grade(out, tw)
        out = self.chroma(out)
        out = finish(out, t, grain=0.009, vignette=0.15)
        self.overlay(out, t, st)
        return out

    def grade(self, out, tw):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * 1.20
        return np.clip(out + np.array([0.010, 0.008, 0.022], f32) * (1 - out) * (1 - tw), 0, 1)

    def chroma_bloom(self, img, amt):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        sm = np.maximum(sm - 1.0, 0)
        acc = np.empty_like(sm)
        for ch, s in ((0, 26), (1, 20), (2, 15)):
            acc[..., ch] = cv2.GaussianBlur(sm[..., ch], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.W, self.H
        o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    # -------------------------------------------------------------------------------------------- overlay (sRGB)
    def readout(self, out, t, t0, t1, big, l2, l3, col):
        L = self.L; W = L.W
        a = ramp(t, t0, t0 + 0.22) * (1 - ramp(t, t1 - 0.2, t1))
        if a <= 0.01: return
        x, ys = W / 2, (318, 404, 462)
        dy = (1 - a) * -18
        pop = 1 + 0.25 * math.exp(-max(t - t0, 0) / 0.08) * (t - t0 < 0.4)
        sz = int(L.hud_size * 1.45 * min(pop, 1.25))
        rgba, _ = word_layer(big, sz, W * 0.9, fill=col)
        composite(out, rgba, x, ys[0] + dy, a)
        if l2: hud_text(out, l2, x, ys[1] + dy, int(L.hud_size * 0.58), "Black", (255, 255, 255), a, 0.06, display=True)
        if l3: hud_text(out, l3, x, ys[2] + dy, int(L.hud_size * 0.50), "Bold", (255, 214, 120), a, 0.08, display=True)

    def marker(self, out, t):
        """hook: ring + leader line to the star (Alpha Centauri, with the Pointers and the Southern Cross)"""
        a = ramp(t, 0.35, 0.8) * (1 - ramp(t, T_SW["sir"] - 0.4, T_SW["sir"] - 0.1))
        if a <= 0.01: return
        cx, cy = self.C
        ov = out.copy()
        r = int(34 * 4 * (1 + 0.08 * math.sin(t * 5)))
        for k in range(12):
            a0 = k * 30 + t * 30
            cv2.ellipse(ov, (int(cx * 4), int(cy * 4)), (r, r), 0, a0, a0 + 18, (1.0, 0.75, 0.40), 2, cv2.LINE_AA, 2)
        # Southern Cross stick figure, faint
        cr = [("Acrux", "Gacrux"), ("Mimosa", "Crux_d")]
        if all(k in self.named for k in ("Acrux", "Gacrux")):
            (x0, y0), (x1, y1) = self.named["Acrux"], self.named["Gacrux"]
            cv2.line(ov, (int(x0 * 4), int(y0 * 4)), (int(x1 * 4), int(y1 * 4)), (0.55, 0.75, 1.0), 2, cv2.LINE_AA, 2)
        out[:] = out * (1 - 0.8 * a) + ov * 0.8 * a

    def overlay(self, out, t, st):
        self.marker(out, t)
        for j, (ts, k) in enumerate(SEQ[:-1]):
            s = SK[k]; t1 = SEQ[j + 1][0] - (0.12 if SEQ[j + 1][1] != "eru" else 0.05)
            t0 = (T_LABEL if k == "ac" else ts + 0.25)
            col = tuple(int(v) for v in np.clip(lin_to_srgb(np.clip(star_col(s["T"], 1.8) / max(star_col(s["T"], 1.8).max(), 1e-3), 0, 1)) * 255, 60, 255))
            if k == "eru": col = (255, 200, 90); t1 = T_WO0 + 0.2
            self.readout(out, t, t0, t1, s["name"], s["l2"], s["l3"], col)
        self.caps.draw(out, t)


# ------------------------------------------------------------------------------------------------- render
def save(im, p):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(stills=None):
    sc = Scene(True); tag = "vert"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.W, sc.H, FPS, crf=17)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


def patch(ranges):
    import subprocess
    sc = Scene(True); tag = "vert"
    W, H = sc.W, sc.H; src = os.path.join(SCR, f"video_{tag}.mp4"); old = src.replace(".mp4", "_prev.mp4")
    os.replace(src, old)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", old, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = Encoder(src, W, H, FPS, crf=17)
    for i in range(int(round(DUR * FPS))):
        buf = dec.stdout.read(W * H * 3); t = i / FPS
        if any(a <= t <= b for a, b in ranges) or len(buf) < W * H * 3: enc.write(sc.frame(t))
        else: enc.p.stdin.write(buf)
    enc.close(); dec.wait(); os.remove(old); print("patched")


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print("DUR", DUR, "frames", int(round(DUR * FPS)), "DMOD", round(DMOD, 3))
        for s in STARS: print(f"  {s['key']:5s} m={s['m']:7.2f} E={mag_to_E(s['m']):.2f} q={q_of(s['m']):.2f} x_moon={10 ** (-0.4 * (s['m'] - M_MOON)):.3f}")
        print({k: round(v, 2) for k, v in T_SW.items()}, "eru0", round(T_ERU0, 2), "eru", round(T_ERU, 2), "wo", round(T_WO0, 2), "back", round(T_BACK, 2))
        sys.exit()
    if sys.argv[1] == "patch":
        patch([tuple(float(v) for v in r.split(":")) for r in sys.argv[3].split(",")]); sys.exit()
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(st)
