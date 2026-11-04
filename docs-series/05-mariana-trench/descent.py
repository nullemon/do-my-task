"""05 'Falling into the Mariana Trench' - numpy compositor for the whole film (one continuous descent).
Every frame is built in linear light and piped straight into x264 per segment (no PNG sequences on disk).
Usage: python3 descent.py <seg_index> [<seg_index> ...]     (segments of SEG_LEN seconds; skip existing)
       python3 descent.py still <t> [<t> ...]                (writes SCR/stills/t_XXX.png for checking)"""
import os, sys, math, time
import numpy as np
from PIL import Image
from common import *
import creatures as C

DUR = PLACE["dur"]
NF = int(round(DUR * FPS))
SEG_LEN = 24.0
rng0 = np.random.default_rng(1)
FOCAL = 900.0
FONT_EXL = FONT_XL


# ------------------------------------------------------------------------------------------ descent profile
def pchip(xk, yk):
    xk = np.asarray(xk, float); yk = np.asarray(yk, float)
    h = np.diff(xk); dl = np.diff(yk) / h
    m = np.zeros_like(yk)
    for i in range(1, len(xk) - 1):
        if dl[i - 1] * dl[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])
    m[0] = 0.0; m[-1] = 0.0

    def f(x):
        x = np.asarray(x, float)
        i = np.clip(np.searchsorted(xk, x) - 1, 0, len(xk) - 2)
        t = (x - xk[i]) / h[i]
        t = np.clip(t, 0, 1)
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1; h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2; h11 = t ** 3 - t ** 2
        return h00 * yk[i] + h10 * h[i] * m[i] + h01 * yk[i + 1] + h11 * h[i] * m[i + 1]
    return f


KEYS = [tuple(k) for k in PLACE["depth_keys"]]
BOTTOM = 10935.0
KEYS = sorted({round(a, 3): b for a, b in KEYS}.items()) + [(DUR, BOTTOM)]
DEPTH = pchip([k[0] for k in KEYS], [k[1] for k in KEYS])
TT = np.arange(0, DUR + 1, 1 / (FPS * 4))
DD = DEPTH(TT)
VV = np.gradient(DD, TT)
VIS = 0.22 + 0.9 * np.maximum(VV, 0) ** 0.35
VIS = np.where(TT > LS(34) + 2.0, 0.08 + 0.14 * np.exp(-(TT - LS(34) - 2.0) / 2.0), VIS)
CAMY = np.concatenate([[0], np.cumsum(VIS[1:] * np.diff(TT))])


def depth(t):
    return float(np.interp(t, TT, DD))


def speed(t):
    return float(np.interp(t, TT, VV))


def camy(t):
    return float(np.interp(t, TT, CAMY))


def t_at_depth(d):
    i = np.searchsorted(DD, d)
    return float(TT[min(i, len(TT) - 1)])


# ------------------------------------------------------------------------------------------ physics for the HUD
def pressure_bar(d):
    """Absolute pressure: UNESCO (Saunders-Fofonoff) depth<->pressure relation at 11.4 N, inverted numerically."""
    if d <= 0:
        return 1.013
    x = math.sin(math.radians(11.37)) ** 2
    lo, hi = 0.0, 13000.0
    for _ in range(40):
        p = 0.5 * (lo + hi)
        g = 9.780318 * (1 + (5.2788e-3 + 2.36e-5 * x) * x) + 1.092e-6 * p
        z = (((-1.82e-15 * p + 2.279e-10) * p - 2.2512e-5) * p + 9.72659) * p / g
        lo, hi = (p, hi) if z < d else (lo, p)
    return lo / 10 + 1.013


TPROF = np.array([(0, 29.0), (50, 28.6), (100, 26.5), (150, 22.5), (200, 17.5), (300, 11.0), (500, 7.4), (800, 5.0),
                  (1000, 4.3), (1500, 2.9), (2000, 2.2), (3000, 1.65), (4000, 1.5), (5000, 1.6), (6000, 1.75),
                  (8000, 2.0), (10000, 2.3), (10935, 2.45)])


def temp_c(d):
    return float(np.interp(d, TPROF[:, 0], TPROF[:, 1]))


def sunlight_pct(d):
    return 100.0 * math.exp(-d / 43.4)      # Kd ~ 0.023 /m: 1 % at ~200 m (very clear open ocean)


def fmt_light(d):
    if d < 0.3:
        return "100 %"
    p = sunlight_pct(d)
    if d >= 1000:
        return "NONE"
    if p >= 10: return f"{p:.0f} %"
    if p >= 1: return f"{p:.1f} %"
    ex = int(math.floor(math.log10(p)))
    return f"{p / 10 ** ex:.0f} × 10^{ex} %".replace("^-", "⁻").replace("⁻1", "⁻¹").replace("⁻2", "⁻²").replace("⁻3", "⁻³") \
        .replace("⁻4", "⁻⁴").replace("⁻5", "⁻⁵").replace("⁻6", "⁻⁶").replace("⁻7", "⁻⁷").replace("⁻8", "⁻⁸").replace("⁻9", "⁻⁹")


# ------------------------------------------------------------------------------------------ textures
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
YN = YY / H
h4, w4 = H // 4, W // 4
y4, x4 = np.mgrid[0:h4, 0:w4].astype(np.float32)
RAY_ANG = np.arctan2((x4 * 4 - (W * 0.62)), (y4 * 4 + 1500.0)).astype(np.float32)
NOISE = periodic_noise(512, 2.4, 5)
NOISE2 = periodic_noise(512, 3.0, 9)
CLOUD = periodic_noise(1024, 3.2, 12)
RADIAL = np.exp(-(((XX - W / 2) / (W * 0.42)) ** 2 + ((YY - H * 0.52) / (H * 0.55)) ** 2)).astype(np.float32)


def water_bg(d, t):
    c0 = np.array([0.020, 0.20, 0.34], np.float32)
    att = np.exp(-max(d, 0) / np.array([6.0, 95.0, 175.0], np.float32))
    base = c0 * att
    gs = 1.0 - 0.75 * ss(300, 1100, d)
    grad = (1 - gs) + gs * (0.45 + 1.25 * (1 - YN) ** 1.4)
    img = base[None, None, :] * grad[..., None]
    deep = ss(500, 1300, d)
    img += np.array([0.0005, 0.0009, 0.0020], np.float32) * deep
    # our own lamp scattering in the water (it comes on as the daylight fails)
    lam = lamp_level(d)
    if lam > 0:
        img += (RADIAL[..., None] * np.array([0.0035, 0.0048, 0.0065], np.float32) * lam)
    if d < 320:
        k = math.exp(-d / 55.0) * (1 - ss(150, 320, d))
        u = RAY_ANG * 9.0
        r = (0.5 + 0.5 * np.sin(u * 3.1 + t * 0.35 + 1.3 * np.sin(u * 0.7 - t * 0.2))) * \
            (0.5 + 0.5 * np.sin(u * 5.3 - t * 0.27 + 2.0 * np.sin(u * 1.3 + t * 0.11)))
        r = r ** 3 * (1 - y4 / h4) ** 1.2
        rays = up4(r.astype(np.float32))
        img += rays[..., None] * (np.array([0.10, 0.30, 0.38], np.float32) * k)[None, None, :]
    return img


def lamp_level(d):
    return ss(450, 1050, d)


# ------------------------------------------------------------------------------------------ surface (over/under)
def surface(img, t, d):
    """Half-submerged camera: sky + sea above a wavy waterline, the bright underside of the surface below it."""
    bob = 9 * math.sin(t * 0.9) + 4 * math.sin(t * 2.1 + 1)
    yw0 = H * 0.47 - d * 620 + bob
    if yw0 < -120:
        return img
    xs = np.arange(W, dtype=np.float32)
    yw = yw0 + 14 * np.sin(xs / 210 + t * 1.25) + 6 * np.sin(xs / 73 - t * 2.3) + 3 * np.sin(xs / 31 + t * 3.7)
    yh = yw0 - 34 - bob * 0.5           # horizon (slightly above the waterline: the camera is at the surface)
    # sky
    sky_t = np.clip((yh - YY) / 620.0, 0, 1)
    sky = (np.array([0.62, 0.55, 0.46], np.float32)[None, None] * (1 - sky_t[..., None]) ** 2.2 +
           np.array([0.07, 0.17, 0.42], np.float32)[None, None] * (1 - (1 - sky_t[..., None]) ** 2.2))
    cl = bilinear_wrap(CLOUD, XX * 0.35 + t * 6, YY * 1.6 + 200)
    sky *= (1 + 0.10 * np.clip(cl, -2, 2)[..., None] * (sky_t[..., None] < 0.7))
    sx, sy = W * 0.70, yh - 210
    rr = np.sqrt((XX - sx) ** 2 + (YY - sy) ** 2)
    sky += (np.exp(-rr / 160)[..., None] * np.array([1.4, 1.1, 0.7], np.float32) * 0.6 +
            (rr < 26)[..., None] * np.array([6.0, 5.4, 4.2], np.float32))
    # sea between horizon and waterline: darker blue with a glitter path under the sun
    sea_m = (YY > yh)
    gl = bilinear_wrap(NOISE, XX * 1.1 + t * 40, YY * 6.0 - t * 30)
    glit = np.clip(gl - 1.6, 0, None) * np.exp(-((XX - sx) / 260) ** 2) * 3.0
    sea = np.array([0.03, 0.08, 0.15], np.float32)[None, None] + glit[..., None] * np.array([1.0, 0.9, 0.7], np.float32)
    above = np.where(sea_m[..., None], sea, sky)
    m_above = (YY < yw[None, :])
    out = np.where(m_above[..., None], above, img)
    # underside of the surface: bright rippled band just below the waterline (Snell window / reflection)
    dy = YY - yw[None, :]
    rip = bilinear_wrap(NOISE2, XX * 0.9 + t * 25, dy * 2.2 + t * 10)
    band = np.exp(-np.clip(dy, 0, None) / 70.0) * (dy > 0) * (0.55 + 0.25 * rip)
    out += band[..., None] * np.array([0.10, 0.34, 0.42], np.float32)
    # the meniscus: a thin bright wobbling line + a soft dark lens edge
    men = np.exp(-(dy / 2.2) ** 2) * 0.9 + np.exp(-((dy + 7) / 6) ** 2) * 0.15
    out += men[..., None] * np.array([0.5, 0.7, 0.8], np.float32)
    return out


# ------------------------------------------------------------------------------------------ particles
NP = 3400
PX = rng0.uniform(-1, 1, NP).astype(np.float32)
PZ = (0.55 + 13.0 * rng0.random(NP) ** 1.6).astype(np.float32)
PY = rng0.uniform(0, 1, NP).astype(np.float32)
PB = rng0.uniform(0.3, 1.0, NP).astype(np.float32)
BIO = rng0.random(NP) < 0.12
BIO_PH = rng0.uniform(0, 100, NP).astype(np.float32)
BIO_RATE = rng0.uniform(0.15, 0.55, NP).astype(np.float32)
BIO_COL = np.where((rng0.random(NP) < 0.75)[:, None], np.array([[0.2, 0.6, 1.5]]), np.array([[0.25, 1.4, 0.9]])).astype(np.float32)


def particles(img, t, d, dt=1 / FPS, gain=1.0, floor_mode=0.0):
    cy = camy(t); cyp = camy(t - dt * 0.9)
    span = (H * 1.35) * PZ / FOCAL
    sx = W / 2 + PX * W * 0.7 * (1 + 0.15 * PZ / 13)
    yrel = ((PY * span - cy) % span) - span / 2
    sy = H / 2 + yrel * FOCAL / PZ
    dy_streak = (cy - cyp) * FOCAL / PZ          # pixels moved during the shutter
    sway = 6 * np.sin(t * 0.4 + PY * 20)
    sx = sx + sway / PZ
    if floor_mode > 0:     # at the bottom: gentle lateral drift (a weak current)
        sx = (sx + floor_mode * (t * 9.0) / PZ * 3) % (W + 200) - 100
    amb = 0.55 * math.exp(-max(d, 0) / 140.0)
    lam = lamp_level(d)
    r2 = ((sx - W / 2) / (W * 0.55)) ** 2 + ((sy - H * 0.5) / (H * 0.7)) ** 2
    lit = amb * (0.4 + 0.6 * np.exp(-PZ / 8)) + lam * 0.11 / (0.35 + PZ ** 1.4) * np.exp(-r2)
    wgt = lit * PB * gain
    col_amb = np.array([0.55, 0.85, 1.0], np.float32) if d < 400 else np.array([0.85, 0.9, 1.0], np.float32)
    near = PZ < 1.6
    acc = Acc(W, H)
    nst = np.clip(np.abs(dy_streak) / 2.0, 1, 24).astype(np.int32)
    far = ~near
    # streaks: sample along the motion
    for n in (1, 4, 12, 24):
        sel = far & (nst <= n) & (nst > (n // 3 if n > 1 else 0))
        if not sel.any():
            continue
        k = np.arange(n, dtype=np.float32) / max(1, n - 1) if n > 1 else np.zeros(1, np.float32)
        xs = np.repeat(sx[sel], n); ys = (sy[sel][:, None] + dy_streak[sel][:, None] * k[None, :]).ravel()
        ww = np.repeat(wgt[sel] / n, n)
        acc.add(xs, ys, ww, col_amb)
    out = img + blur(acc.image(), 0.8, 1) * 1.6
    # near particles: big soft out-of-focus discs at quarter resolution
    if near.any():
        a4 = Acc(w4, h4)
        n = 10
        k = np.arange(n, dtype=np.float32) / (n - 1)
        xs = np.repeat(sx[near] / 4, n); ys = ((sy[near][:, None] + dy_streak[near][:, None] * k[None, :]) / 4).ravel()
        a4.add(xs, ys, np.repeat(wgt[near] * 3.0 / n, n), col_amb)
        out += up4(blur(a4.image(), 2.2, 2))
    # bioluminescent sparks (only in the dark), fewer in the abyss and hadal zone
    bio_k = ss(250, 700, d) * (1 - 0.65 * ss(3500, 6500, d)) * gain
    if bio_k > 0.01:
        ph = (t * BIO_RATE + BIO_PH) % 1.0
        fl = np.exp(-ph * 9.0) * (ph < 0.6)
        sel = BIO & (fl > 0.02) & (sy > -20) & (sy < H + 20)
        if sel.any():
            ab = Acc(W, H)
            ab.add(sx[sel], sy[sel], fl[sel] * bio_k * 1.6 / (0.6 + PZ[sel] * 0.25), BIO_COL[sel])
            out += blur(ab.image(), 1.0, 1) * 2.0 + up4(blur(down4(ab.image()), 1.5)) * 3.0
    return out


# ------------------------------------------------------------------------------------------ scale markers
def marker_y(tm, t, v=230.0):
    return H * 0.5 + (tm - t) * v


def hline(disp, y, op, x0=60, x1=None, dash=(18, 10), col=(0.82, 0.86, 0.9)):
    x1 = W - 170 if x1 is None else x1
    yi = int(round(y))
    if yi < 1 or yi >= H - 1 or op <= 0.003:
        return
    xs = np.arange(x0, x1)
    m = ((xs - x0) % (dash[0] + dash[1])) < dash[0]
    fade = np.clip(np.minimum(xs - x0, x1 - xs) / 140.0, 0, 1)
    a = (m * fade * op)[None, :, None]
    disp[yi:yi + 1, x0:x1] = disp[yi:yi + 1, x0:x1] * (1 - a * 0.7) + np.array(col, np.float32) * a * 0.7


def polyline(disp, pts, op, col=(0.8, 0.86, 0.95), width=1.3):
    pts = np.asarray(pts)
    if op <= 0.003 or len(pts) < 2:
        return
    x0, y0, x1, y1 = C.bbox(pts, 4)
    if x1 < 0 or x0 > W or y1 < 0 or y0 > H:
        return
    cv = C.Canvas(max(-10, x0), max(-10, y0), min(W + 10, x1), min(H + 10, y1))
    cv.line(pts, width)
    C.comp(disp, cv, cv.alpha(), col, op=op)


MARKERS = [  # depth, main, sub
    (40, "40 M", "RECREATIONAL SCUBA LIMIT"),
    (200, "200 M", "END OF THE SUNLIGHT ZONE"),
    (253, "253 M", "DEEPEST BREATH-HOLD DIVE · HERBERT NITSCH, 2012 (NO-LIMITS, WEIGHTED SLED)"),
    (1000, "1,000 M", "LAST TRACES OF SUNLIGHT"),
    (2035, "≈ 2,000 M", "SPERM WHALE DIVES (DEEPEST MEASURED ≈ 2,035 M)"),
    (4000, "4,000 M", "THE ABYSS BEGINS"),
    (6000, "6,000 M", "THE HADAL ZONE BEGINS"),
    (6957, "≈ 6,960 M", "DEEPEST DUMBO OCTOPUS SEEN (JAVA TRENCH, 2020)"),
    (8336, "8,336 M", "DEEPEST FISH EVER FILMED (SNAILFISH, IZU–OGASAWARA TRENCH, 2022)"),
]
MARK_T = [(t_at_depth(d), d, a, b) for d, a, b in MARKERS]


def draw_markers(disp, t):
    for tm, d, a, b in MARK_T:
        if abs(t - tm) > 4.5:
            continue
        y = marker_y(tm, t)
        op = 1 - ss(0.30, 0.52, abs(y - H / 2) / H)
        hline(disp, y, op)
        draw_text(disp, a, 110, y - 26, 30, op, anchor="l", font=FONT_EXL, tracking=0.18)
        draw_text(disp, b, 112, y + 24, 16, op * 0.85, anchor="l", tracking=0.28)


def burj(disp, t):
    tm = t_at_depth(828.0)
    if abs(t - tm) > 6:
        return
    base = marker_y(tm, t, 190)
    op = (1 - ss(0.32, 0.55, abs(base - H / 2) / H)) * 0.75
    s = 2.0            # px per metre for the drawing
    cx = W * 0.64
    # stepped, tapering tower outline (generic supertall silhouette), base at the marker
    prof = [(0, 34), (120, 30), (200, 26), (300, 22), (380, 18), (460, 14), (540, 11), (600, 8), (640, 5.5), (700, 3), (828, 0.6)]
    L, R = [], []
    for i, (h, w) in enumerate(prof):
        y = base - h * s
        L.append((cx - w * s * 0.9, y)); R.append((cx + w * s * 0.55, y))
        if i + 1 < len(prof):
            y2 = base - prof[i + 1][0] * s
            L.append((cx - w * s * 0.9, y2)); R.append((cx + w * s * 0.55, y2))
    pts = L + [(cx, base - 828 * s)] + R[::-1]
    polyline(disp, pts, op, width=1.2)
    polyline(disp, [(cx - 220, base), (cx + 220, base)], op * 0.8, width=1.0)
    draw_text(disp, "828 M", cx + 120, base + 30, 30, op / 0.75, anchor="l", font=FONT_EXL, tracking=0.18)
    draw_text(disp, "BURJ KHALIFA, THE TALLEST BUILDING ON EARTH", cx + 122, base + 70, 16, op / 0.75 * 0.85, anchor="l")
    draw_text(disp, "STANDING HERE, ITS TIP WOULD JUST REACH THE SURFACE", cx + 122, base + 96, 14, op / 0.75 * 0.7, anchor="l")


EV_PROF = None


def everest(disp, t):
    """Ghost outline of an 8,849 m mountain standing on the trench floor: the summit at 2,086 m depth."""
    global EV_PROF
    tm = t_at_depth(2086.0)
    if t < tm - 7 or t > LS(23) - 0.5:
        return
    if EV_PROF is None:
        r = np.random.default_rng(4)
        h = np.linspace(0, 1500, 220)
        jag = np.cumsum(r.normal(0, 1, 220)); jag -= np.linspace(0, jag[-1], 220)
        EV_PROF = (h, h * 0.95 + 70 * np.sin(h / 160) + 12 * jag, h * 1.35 + 50 * np.sin(h / 120 + 1) + 9 * jag[::-1])
    hs, wl, wr = EV_PROF
    s = 1.0
    sy = marker_y(tm, t, 140)
    cx = W * 0.5
    op = ss(tm - 7, tm - 4.5, t) * (1 - ss(LS(23) - 2.5, LS(23) - 0.5, t)) * 0.6
    L = np.stack([cx - wl * s, sy + hs * s], 1); R = np.stack([cx + wr * s, sy + hs * s], 1)
    pts = np.concatenate([L[::-1], R], 0)
    pts = pts[(pts[:, 1] > -50) & (pts[:, 1] < H + 400)]
    polyline(disp, pts, op, col=(0.78, 0.84, 0.95), width=1.4)
    op2 = op / 0.6 * (1 - ss(0.28, 0.5, abs(sy - H / 2) / H))
    draw_text(disp, "8,849 M MOUNTAIN · SUMMIT AT 2,086 M", cx, sy - 80, 22, op2, tracking=0.26)
    draw_text(disp, "IF EVEREST STOOD ON THE FLOOR OF CHALLENGER DEEP", cx, sy - 48, 15, op2 * 0.8, tracking=0.3)


def titanic(disp, t):
    tm = t_at_depth(3800.0)
    if abs(t - tm) > 5:
        return
    base = marker_y(tm, t, 200)
    op = (1 - ss(0.30, 0.52, abs(base - H / 2) / H)) * 0.75
    cx = W * 0.60; s = 2.3
    # generic early-20th-century liner bow section resting on the seabed (simplified outline)
    hull = np.array([(-120, 0), (60, 0), (100, -6), (118, -22), (126, -40), (128, -52), (-120, -46)]) * s
    deck = np.array([(-120, -46), (-40, -47), (40, -49), (128, -52)]) * s
    house = np.array([(-110, -46), (-110, -62), (-30, -62), (-30, -55), (10, -55), (10, -47)]) * s
    funnel = np.array([(-80, -62), (-84, -90), (-66, -90), (-62, -62)]) * s
    mast = np.array([(70, -50), (66, -120)]) * s
    for p in (hull, deck, house, funnel, mast):
        polyline(disp, np.asarray(p) + (cx, base), op, width=1.2)
    xs = np.linspace(cx - 520, cx + 440, 60)
    polyline(disp, np.stack([xs, base + 3 + 4 * np.sin(xs / 50)], 1), op * 0.7, width=1.0)
    draw_text(disp, "3,800 M", cx - 300, base + 40, 30, op / 0.75, anchor="l", font=FONT_EXL, tracking=0.18)
    draw_text(disp, "WRECK OF THE TITANIC (NORTH ATLANTIC) · ONE THIRD OF THE WAY DOWN", cx - 298, base + 80, 16,
              op / 0.75 * 0.85, anchor="l")


# ------------------------------------------------------------------------------------------ HUD
def fmt_int(v):
    return f"{int(round(v)):,}"


def hud(disp, t, d, op):
    if op <= 0:
        return
    x = 92; y = 84
    rows = [("DEPTH", f"{fmt_int(max(0.0, d))} M"),
            ("PRESSURE", f"≈ {fmt_int(pressure_bar(max(0, d)))} BAR" if d > 30 else f"≈ {pressure_bar(max(0, d)):.1f} BAR"),
            ("WATER TEMPERATURE", f"≈ {temp_c(max(d, 0)):.1f} °C" if d > 900 else f"≈ {temp_c(max(d, 0)):.0f} °C"),
            ("SUNLIGHT", fmt_light(max(d, 0)))]
    for i, (k, v) in enumerate(rows):
        yy = y + i * 66
        draw_text(disp, k, x, yy, 13, op * 0.7, anchor="l", tracking=0.34)
        draw_text(disp, v, x, yy + 26, 24 if i else 30, op, anchor="l", font=FONT_EXL if i == 0 else FONT_L,
                  tracking=0.12)
    # depth gauge (linear 0 - 11,000 m)
    gx, g0, g1 = W - 110, 110, 960
    gy = lambda dd: g0 + (g1 - g0) * dd / 11000.0
    a = op * 0.5
    disp[g0:g1, gx:gx + 1] = disp[g0:g1, gx:gx + 1] * (1 - a) + 0.8 * a
    for km in range(0, 12):
        yy = int(gy(km * 1000))
        ln = 10 if km % 2 == 0 else 5
        disp[yy:yy + 1, gx - ln:gx] = disp[yy:yy + 1, gx - ln:gx] * (1 - a) + 0.8 * a
        if km % 2 == 0:
            draw_text(disp, f"{km}" if km else "0", gx + 18, yy, 12, op * 0.55, anchor="l", tracking=0.1)
    draw_text(disp, "KM", gx + 18, g1 + 22, 11, op * 0.45, anchor="l")
    for zd in (200, 1000, 4000, 6000):
        yy = int(gy(zd))
        disp[yy:yy + 1, gx - 3:gx + 6] = disp[yy:yy + 1, gx - 3:gx + 6] * (1 - a) + 0.9 * a
    zone = zone_name(d)
    yy = gy(min(max(d, 0), 11000))
    # current depth: small bright notch + zone name
    r = 4
    yi = int(round(yy))
    sl = disp[max(0, yi - r):yi + r + 1, gx - r:gx + r + 1]
    sl[:] = sl * (1 - op) + np.array([0.95, 0.96, 0.98], np.float32) * op
    draw_text(disp, zone, gx - 20, yy, 12, op * 0.8, anchor="r", tracking=0.3)
    # bottom marker
    yb = int(gy(BOTTOM))
    draw_text(disp, "10,935", gx + 18, yb + 18, 11, op * 0.45, anchor="l", tracking=0.1)
    # Everest bracket (after it is introduced)
    eo = op * ss(LS(21) + 2, LS(21) + 4, t) * 0.5
    if eo > 0.01:
        ye0, ye1 = int(gy(BOTTOM - 8849)), yb
        disp[ye0:ye1, gx + 7:gx + 8] = disp[ye0:ye1, gx + 7:gx + 8] * (1 - eo) + 0.85 * eo
        draw_text(disp, "EVEREST", gx + 18, (ye0 + ye1) / 2, 10, eo * 1.6, anchor="l", tracking=0.3)


def zone_name(d):
    if d < 200: return "SUNLIGHT ZONE"
    if d < 1000: return "TWILIGHT ZONE"
    if d < 4000: return "MIDNIGHT ZONE"
    if d < 6000: return "ABYSS"
    return "HADAL ZONE"


ZONES = [(3, "THE SUNLIGHT ZONE", "EPIPELAGIC · 0 – 200 M"), (7, "THE TWILIGHT ZONE", "MESOPELAGIC · 200 – 1,000 M"),
         (15, "THE MIDNIGHT ZONE", "BATHYPELAGIC · 1,000 – 4,000 M"), (24, "THE ABYSS", "ABYSSOPELAGIC · 4,000 – 6,000 M"),
         (27, "THE HADAL ZONE", "TRENCHES · DEEPER THAN 6,000 M")]


def zone_titles(disp, t):
    for li, a, b in ZONES:
        t0 = LS(li) - 0.3; t1 = t0 + 6.0
        op = ss(t0, t0 + 1.0, t) * (1 - ss(t1 - 1.2, t1, t))
        if op > 0:
            draw_text(disp, a, W / 2, 108, 34, op, font=FONT_EXL, tracking=0.42)
            draw_text(disp, b, W / 2, 150, 15, op * 0.8, tracking=0.38)


CAPS = [  # (line, dt0, dt1 after line end, main, sub)
    (1, 0.0, 2.0, "CHALLENGER DEEP · ≈ 10,935 M BELOW", "MARIANA TRENCH · WESTERN PACIFIC OCEAN"),
    (4, 0.2, 1.2, "+ ≈ 1 ATMOSPHERE EVERY 10 M", None),
    (6, 0.2, 1.2, "RED LIGHT IS ABSORBED WITHIN THE FIRST TENS OF METRES", None),
    (10, 0.5, 1.2, "LANTERNFISH (MYCTOPHIDAE)", "COUNTER-ILLUMINATION: BELLY LIGHTS ERASE THEIR SILHOUETTE"),
    (11, 0.5, 1.2, "GIANT SQUID (ARCHITEUTHIS)", "FIRST FILMED IN THE DEEP IN 2012 · ≈ 630 M, OFF JAPAN"),
    (15, 2.5, 1.0, "≈ 100 × SURFACE PRESSURE · ≈ 4 °C", None),
    (16, 0.3, 1.0, "≈ 3 IN 4 ANIMALS SEEN IN THE DEEP WATER COLUMN MAKE LIGHT", "SURVEY OFF CALIFORNIA, SURFACE TO 3,900 M (MARTINI & HADDOCK 2017)"),
    (17, 0.3, 1.0, "ATOLLA JELLYFISH", "'BURGLAR ALARM' DISPLAY · A HYPOTHESIS"),
    (18, 0.3, 1.0, "DEEP-SEA ANGLERFISH (FEMALE)", "LURE: A MODIFIED FIN SPINE HOLDING GLOWING BACTERIA"),
    (19, 0.3, 1.0, "GULPER EEL (EURYPHARYNX PELECANOIDES)", "LIGHT ORGAN AT THE TIP OF THE TAIL"),
    (20, 0.3, 1.0, "SPERM WHALE", "HUNTS SQUID ON ONE BREATH · MEASURED DIVES TO ≈ 2,000 M"),
    (26, 0.3, 1.0, "DUMBO OCTOPUS (GRIMPOTEUTHIS)", "SEEN DOWN TO ≈ 6,960 M"),
    (28, 0.3, 1.0, "SUBDUCTION", "THE PACIFIC PLATE SINKS BENEATH THE MARIANA PLATE"),
    (29, 0.5, 1.0, "HADAL SNAILFISH (PSEUDOLIPARIS)", "DEEPEST FISH FILMED: 8,336 M · IZU–OGASAWARA TRENCH, 2022"),
    (30, 0.3, 1.0, "PREDICTED DEPTH LIMIT FOR FISH: ≈ 8,200 – 8,400 M", "WHERE A PRESSURE-PROTECTING MOLECULE (TMAO) WOULD MAX OUT"),
    (31, 0.3, 0.5, "TRIESTE · 23 JANUARY 1960", "JACQUES PICCARD & DON WALSH · 20 MINUTES ON THE BOTTOM"),
    (32, 0.3, 0.6, "DEEPSEA CHALLENGER · 26 MARCH 2012", "JAMES CAMERON, SOLO"),
    (33, 0.3, 0.8, "LIMITING FACTOR · FROM 28 APRIL 2019", "VICTOR VESCOVO · 15 DIVES TO CHALLENGER DEEP BY 2022"),
    (34, 0.3, 1.5, "CHALLENGER DEEP · 10,935 M", "± ≈ 6 M (GREENAWAY ET AL. 2021) · OTHER RECENT SURVEYS ≈ 10,920 – 10,935 M"),
    (36, 0.3, 1.0, "≈ 1,100 BAR · MORE THAN 1 TONNE ON EVERY CM²", None),
    (37, 0.3, 1.0, "≈ 2.4 °C", None),
    (38, 0.6, 1.2, "SCAVENGING AMPHIPODS", "E.G. HIRONDELLEA GIGAS, COLLECTED IN CHALLENGER DEEP"),
    (40, 1.5, 0.5, "KATHY SULLIVAN", "SPACEWALK 1984 · CHALLENGER DEEP 2020"),
]


def captions(disp, t):
    for li, a, b, m, s in CAPS:
        t0 = LS(li) + a; t1 = LE(li) + b
        if t0 - 1 < t < t1 + 1:
            caption(disp, t, t0, t1, m, s, size=26)


# ------------------------------------------------------------------------------------------ creatures schedule
def scroll(t, tc, z, k=1.0):
    """Screen-y offset of an object at distance z that is centred in frame at time tc (we fall past it)."""
    return -(camy(t) - camy(tc)) * FOCAL / z * k


def fade(t, t0, t1, f=1.0):
    return ss(t0, t0 + f, t) * (1 - ss(t1 - f, t1, t))


LF = [(np.random.default_rng(i).uniform(-1, 1), np.random.default_rng(i + 50).uniform(-1, 1),
       np.random.default_rng(i + 99).uniform(3.0, 9.0)) for i in range(18)]


def creatures(img, t, d):
    lam = lamp_level(d)
    # lanternfish school (twilight zone): dark silhouettes against the faint blue, photophores glowing
    t0, t1 = LS(9) + 1.5, LE(10) + 3
    if t0 < t < t1:
        tc = LS(10) + 3.5
        bgc = np.array([0.020, 0.20, 0.34]) * np.exp(-d / np.array([6.0, 95.0, 175.0]))
        for i, (ux, uy, z) in enumerate(LF):
            x = W * 0.5 + ux * 700 + (t - tc) * 38 * (1 + 0.2 * uy) / z * 4
            y = H * 0.48 + uy * 260 + scroll(t, tc, z, 0.35)
            Lpx = 1100 / z
            C.lanternfish(img, t + i * 0.37, x, y, Lpx, facing=1, ang=0.05 * uy, body_col=tuple(bgc * 0.15),
                          rim=tuple(bgc * 0.5), glow=fade(t, t0, t1, 1.5) * 0.25, seed=i)
    # giant squid: a huge, dim silhouette crossing slowly (fins first)
    t0, t1 = LS(11) - 0.5, LE(11) + 2.5
    if t0 < t < t1:
        tc = LS(11) + 4.5
        x = W * 0.72 - (t - tc) * 55
        y = H * 0.56 + scroll(t, tc, 18, 0.25)
        bgc = np.array([0.020, 0.20, 0.34]) * np.exp(-d / np.array([6.0, 95.0, 175.0]))
        C.giant_squid(img, t, x, y, 640, body_col=tuple(bgc * 0.18), rim=tuple(bgc * 0.6), op=fade(t, t0, t1, 2.0))
    # Atolla
    t0, t1 = LS(17) - 0.8, LE(17) + 1.5
    if t0 < t < t1:
        tc = LS(17) + 5
        C.atolla(img, t, W * 0.60 + (t - tc) * 6, H * 0.47 + scroll(t, tc, 9, 0.22), 95, op=fade(t, t0, t1, 1.2))
    # anglerfish
    t0, t1 = LS(18) - 0.8, LE(18) + 1.0
    if t0 < t < t1:
        tc = LS(18) + 3.5
        C.anglerfish(img, t, W * 0.44 + (t - tc) * 5, H * 0.50 + scroll(t, tc, 9, 0.2), 380, op=fade(t, t0, t1, 1.0),
                     lure_gain=fade(t, t0, t1, 1.0))
    # gulper eel
    t0, t1 = LS(19) - 0.6, LE(19) + 1.2
    if t0 < t < t1:
        tc = LS(19) + 3.2
        C.gulper(img, t, W * 0.42 - (t - tc) * 30, H * 0.46 + scroll(t, tc, 10, 0.22), 900, op=fade(t, t0, t1, 1.0),
                 body_col=(0.004 + 0.01 * lam, 0.005 + 0.011 * lam, 0.007 + 0.013 * lam))
    # sperm whale: enormous, traced by disturbed sparks
    t0, t1 = LS(20) - 1.0, LE(20) + 1.8
    if t0 < t < t1:
        tc = LS(20) + 3.0
        C.sperm_whale(img, t, W * 0.48 + (t - tc) * 70, H * 0.55 + scroll(t, tc, 22, 0.25), 1500, op=fade(t, t0, t1, 1.5))
    # dumbo octopus
    t0, t1 = LS(26) - 0.8, LE(26) + 1.2
    if t0 < t < t1:
        tc = LS(26) + 3.5
        C.dumbo(img, t, W * 0.58 + (t - tc) * 8, H * 0.50 + scroll(t, tc, 6, 0.2), 150, light=0.55 * lam,
                op=fade(t, t0, t1, 1.2))
    # snailfish (three, pale)
    t0, t1 = LS(29) + 0.5, LE(30) - 2.0
    if t0 < t < t1:
        tc = (t0 + t1) / 2
        for i, (ox, oy, z, L) in enumerate(((-260, 30, 5.0, 230), (210, -120, 8.0, 150), (420, 140, 11.0, 110))):
            C.snailfish(img, t + i * 1.7, W * 0.5 + ox + (t - tc) * (14 - i * 4), H * 0.52 + oy + scroll(t, tc, z, 0.15), L,
                        facing=-1 if i == 1 else 1, light=0.75 * lam * (1.0 - 0.15 * i), op=fade(t, t0, t1, 1.5), seed=i)
    # a few amphipods drifting near the bottom (hadal, below ~9.5 km)
    if 9500 < d and t < LS(34) + 4:
        for i in range(6):
            r = np.random.default_rng(200 + i)
            tc = r.uniform(LS(32), LS(34))
            z = r.uniform(2, 6)
            x = r.uniform(200, W - 300) + math.sin(t * r.uniform(0.5, 1.5)) * 40
            y = H * 0.5 + scroll(t, tc, z, 0.5)
            if -50 < y < H + 50:
                C.amphipod(img, t, x, y, 70 / z * 3, ang=r.uniform(0, 6), light=0.6 * lam, seed=i)


# ------------------------------------------------------------------------------------------ vessels (Blender sprites)
_SPR = {}


def sprite(name):
    if name not in _SPR:
        im = Image.open(os.path.join(PL, f"vessel_{name}.png")).convert("RGBA")
        a = np.asarray(im, np.float32) / 255.0
        rgb = a[..., :3] ** 2.2
        _SPR[name] = (rgb, a[..., 3])
    return _SPR[name]


def put_sprite(img, name, cx, cy, wpx, op, gain):
    rgb, a = sprite(name)
    h, w = a.shape
    s = wpx / w
    nw, nh = int(w * s), int(h * s)
    rs = lambda ch: np.asarray(Image.fromarray(np.ascontiguousarray(ch), "F").resize((nw, nh), Image.BILINEAR))
    A = rs(a); RGB = np.stack([rs(rgb[..., c]) for c in range(3)], -1)
    x0, y0 = int(cx - nw / 2), int(cy - nh / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + nw), min(H, y0 + nh)
    if xb <= xa or yb <= ya:
        return
    al = A[ya - y0:yb - y0, xa - x0:xb - x0][..., None] * op
    reg = img[ya:yb, xa:xb]
    reg[:] = reg * (1 - al) + RGB[ya - y0:yb - y0, xa - x0:xb - x0] * gain * al


def vessels(img, t):
    for li, name, x, wpx in ((31, "trieste", W * 0.30, 760), (32, "challenger", W * 0.70, 520), (33, "limiting", W * 0.32, 560)):
        t0, t1 = LS(li) - 0.6, LE(li) + 0.8
        if t0 < t < t1:
            tc = (t0 + t1) / 2
            op = fade(t, t0, t1, 1.6) * 0.9
            y = H * 0.46 + (t - tc) * -12
            put_sprite(img, name, x + (t - tc) * 4, y, wpx, op, 0.12)


# ------------------------------------------------------------------------------------------ the floor
_PLATE = {}


def plate(v):
    if v not in _PLATE:
        im = np.asarray(Image.open(os.path.join(PL, f"floor_{v}.png")).convert("RGB"), np.float32) / 255.0
        lin = (im ** 2.2).astype(np.float32)
        _PLATE[v] = [np.ascontiguousarray(lin[..., c]) for c in range(3)]
    return _PLATE[v]


T_FLOOR0 = LS(34) - 3.5          # floor starts to appear in our light
T_ARRIVE = LS(34) + 1.0
T_B = LS(38) - 1.4                # cut to the close view (amphipods)
T_DIM = LS(39) - 0.4              # the comparison overlay
T_LAMPOFF = LE(43) + 0.6
T_TITLE = T_LAMPOFF + 0.8
AMPH = [dict(a0=np.random.default_rng(i).uniform(0, 6.28), r0=np.random.default_rng(i + 7).uniform(260, 900),
             sp=np.random.default_rng(i + 3).uniform(0.6, 1.4), L=np.random.default_rng(i + 11).uniform(34, 58))
        for i in range(22)]


def floor_frame(t):
    """Returns the linear floor image (or None) and its weight."""
    if t < T_FLOOR0:
        return None, 0.0
    if t < T_B:
        pA = plate("A")
        u = ss(T_FLOOR0, T_ARRIVE + 1.5, t)
        z = 1.0 + 0.12 * (1 - u) + 0.06 * ss(T_ARRIVE, T_B, t)
        cx = pA[0].shape[1] / 2
        cy = pA[0].shape[0] / 2 + (1 - u) * 520
        cx, cy = clamp_center(pA[0].shape, z, cx, cy)
        im = zoom_crop_ch(pA, z, cx, cy)
        expo = 0.15 + 0.85 * u
        k = ss(T_FLOOR0, T_ARRIVE, t)
        # it rises into view from below as the camera tilts down
        shift = int((1 - k) * H * 0.65)
        if shift > 0:
            im = np.concatenate([np.zeros((shift, W, 3), np.float32), im[:H - shift]], 0)
            im *= np.clip((YY - shift) / 260.0, 0, 1)[..., None]
        return im * expo * 0.85, k
    pB = plate("B")
    z = 1.0 + 0.05 * ss(T_B, T_LAMPOFF, t)
    cx, cy = clamp_center(pB[0].shape, z, pB[0].shape[1] / 2, pB[0].shape[0] / 2 + 40)
    im = zoom_crop_ch(pB, z, cx, cy)
    if t < T_B + 1.4:     # cross-dissolve from A
        pA = plate("A")
        ia = zoom_crop_ch(pA, 1.06, *clamp_center(pA[0].shape, 1.06, pA[0].shape[1] / 2, pA[0].shape[0] / 2))
        u = ss(T_B, T_B + 1.4, t)
        im = ia * 0.85 * (1 - u) + im * 0.9 * u
    else:
        im = im * 0.9
    return im, 1.0


def silt(img, t):
    """A soft cloud of silt kicked up by our arrival, slowly spreading and settling."""
    if not (T_ARRIVE - 0.5 < t < T_B + 3):
        return
    u = t - (T_ARRIVE - 0.5)
    a = np.exp(-u / 9.0) * ss(0, 1.5, u)
    n = bilinear_wrap(NOISE, XX * 0.35 + u * 8, YY * 0.5 - u * 3)
    cloud = np.clip(0.5 + 0.35 * n, 0, 1) * np.exp(-((YY - H * (0.86 - 0.012 * u)) / (220 + 25 * u)) ** 2) * \
        np.exp(-((XX - W / 2) / (500 + 60 * u)) ** 2)
    img[:] = img * (1 - 0.5 * a * cloud[..., None]) + cloud[..., None] * a * np.array([0.05, 0.048, 0.042], np.float32)


def food_and_amphipods(img, t):
    if t < T_B:
        return
    fx, fy = W * 0.52, H * 0.62
    # a pale lump of something that sank from above
    cv = C.Canvas(fx - 120, fy - 60, fx + 120, fy + 60)
    ang = np.linspace(0, 2 * np.pi, 50)
    rr = 1 + 0.12 * np.sin(ang * 3 + 1) + 0.07 * np.sin(ang * 7)
    cv.poly(np.stack([fx + np.cos(ang) * 95 * rr, fy + np.sin(ang) * 34 * rr], 1))
    a = cv.alpha()
    yy, xx = np.mgrid[cv.y0:cv.y0 + cv.h, cv.x0:cv.x0 + cv.w].astype(np.float32)
    sh = np.clip(1.2 - (yy - (fy - 34)) / 70.0, 0.3, 1.2)
    C.comp(img, cv, a, np.stack([0.20 * sh, 0.18 * sh, 0.15 * sh], -1))
    arrive = ss(T_B, LS(38) + 6, t)
    for i, p in enumerate(AMPH):
        r = p["r0"] * (1 - 0.82 * arrive * min(1.0, p["sp"])) + 30
        th = p["a0"] + 0.08 * math.sin(t * 0.7 * p["sp"] + i) + t * 0.03 * (1 if i % 2 else -1)
        x = fx + math.cos(th) * r * 1.4 + math.sin(t * 3 + i) * 4
        y = fy + math.sin(th) * r * 0.42 - (i % 4 == 0) * (80 + 40 * math.sin(t * 0.8 + i))
        op = ss(T_B + 0.3 + (i % 5) * 0.6, T_B + 1.5 + (i % 5) * 0.6, t)
        C.amphipod(img, t * p["sp"], x, y, p["L"], ang=th + math.pi / 2 + 0.6 * math.sin(t + i), light=1.0, op=op, seed=i)


def compare_overlay(disp, t):
    if t < T_DIM:
        return
    op_all = 1 - ss(LE(41) + 1.4, LE(41) + 2.6, t)
    if op_all <= 0:
        return
    rows = [(LS(39) + 0.4, "WALKED ON THE MOON", "12", "APOLLO 11 – 17 · 1969 – 1972"),
            (LS(40) + 0.0, "DESCENDED TO CHALLENGER DEEP", "DOZENS",
             "≈ 27 BY JULY 2022 IN ONE TALLY · CHINA REPORTS ≈ 30 MORE BELOW 10,000 M IN FENDOUZHE · COUNTS VARY"),
            (LS(41) + 0.2, "FLOWN TO SPACE", "≈ 780", "BY 2026 · DEFINITIONS VARY")]
    y0 = H * 0.30
    for i, (ts, a, b, c) in enumerate(rows):
        op = ss(ts, ts + 0.9, t) * op_all
        if op <= 0:
            continue
        y = y0 + i * 150
        draw_text(disp, a, W * 0.5 - 60, y, 20, op * 0.85, anchor="r", tracking=0.34)
        draw_text(disp, b, W * 0.5 + 0, y - 4, 46, op, anchor="l", font=FONT_EXL, tracking=0.12)
        draw_text(disp, c, W * 0.5, y + 48, 13, op * 0.65, tracking=0.26)
        if i == 0:   # twelve small dots
            for k in range(12):
                cx = W * 0.5 + 110 + k * 22; cy = y - 4
                o = op * ss(ts + 0.6 + k * 0.08, ts + 0.9 + k * 0.08, t)
                disp[int(cy) - 3:int(cy) + 4, int(cx) - 3:int(cx) + 4] = disp[int(cy) - 3:int(cy) + 4, int(cx) - 3:int(cx) + 4] * (1 - o) + 0.9 * o


# ------------------------------------------------------------------------------------------ frame
def frame(fi):
    t = fi / FPS
    d = depth(t)
    lin = water_bg(d, t)
    if d < 2.2 and t < LS(3):
        lin = surface(lin, t, d)
    fl, fk = floor_frame(t)
    if fl is not None:
        lin = lin * (1 - fk) + fl * fk + lin * fk * 0.0
        lin = lin + (RADIAL[..., None] * np.array([0.002, 0.0028, 0.0036], np.float32))
        silt(lin, t)
        food_and_amphipods(lin, t)
    lamp_gain = 1.0
    if t > T_DIM:
        lamp_gain = 1 - 0.62 * ss(T_DIM, T_DIM + 1.5, t)
        lamp_gain *= (1 - ss(T_LAMPOFF, T_LAMPOFF + 2.2, t))
        lin = lin * lamp_gain
    creatures(lin, t, d)
    vessels(lin, t)
    pg = 1.0 if fl is None else 0.55
    lin = particles(lin, t, d, gain=pg * (lamp_gain if t > T_DIM else 1.0), floor_mode=1.0 if t > T_ARRIVE else 0.0)
    lin = bloom(lin, 0.35, 16)
    # exposure: the deep scenes are pushed a little so that faint things read on a screen
    expo = 1.0 + 1.6 * ss(300, 1400, d)
    disp = tonemap(lin, 1.7 * expo)
    # final lone spark in the dark, then the title
    if t > T_LAMPOFF + 1.0:
        k = ss(T_LAMPOFF + 1.0, T_LAMPOFF + 1.6, t) * (1 - ss(T_LAMPOFF + 3.4, T_LAMPOFF + 4.6, t))
        r = np.sqrt((XX - W * 0.38) ** 2 + (YY - H * 0.58) ** 2)
        disp += (np.exp(-(r / 3.0) ** 2) * 0.8 + np.exp(-r / 14) * 0.12)[..., None] * np.array([0.3, 0.7, 1.0], np.float32) * k
    # overlays (display space)
    hop = ss(0.8, 2.6, t) * (1 - ss(T_DIM - 0.5, T_DIM + 0.8, t))
    hud(disp, t, d, hop * 0.9)
    zone_titles(disp, t)
    draw_markers(disp, t)
    burj(disp, t)
    everest(disp, t)
    titanic(disp, t)
    captions(disp, t)
    compare_overlay(disp, t)
    if t > T_TITLE:
        op = ss(T_TITLE, T_TITLE + 1.6, t) * (1 - ss(DUR - 1.8, DUR - 0.3, t))
        draw_text(disp, "FALLING INTO THE MARIANA TRENCH", W / 2, H * 0.47, 44, op, font=FONT_EXL, tracking=0.42)
        draw_text(disp, "CHALLENGER DEEP · 10,935 M", W / 2, H * 0.47 + 62, 16, op * 0.75, tracking=0.42)
    if t < 0.8:
        disp *= ss(0, 0.8, t)
    return to8(disp)


def render_segment(k):
    f0 = int(round(k * SEG_LEN * FPS)); f1 = min(NF, int(round((k + 1) * SEG_LEN * FPS)))
    name = f"s{k:02d}"
    if os.path.exists(os.path.join(SEG, name + ".mp4")):
        print("skip", name); return
    wr = Writer(name, crf=14)
    t0 = time.time()
    for fi in range(f0, f1):
        wr.write(frame(fi))
        if (fi - f0) % 96 == 0:
            print(name, fi, f"{(time.time() - t0) / max(1, fi - f0 + 1):.2f}s/f", flush=True)
    n = wr.close()
    print(name, "done", n, "frames", f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "still":
        od = os.path.join(SCR, "stills"); os.makedirs(od, exist_ok=True)
        for a in sys.argv[2:]:
            t = float(a); t0 = time.time()
            Image.fromarray(frame(int(round(t * FPS)))).save(os.path.join(od, f"t_{t:06.1f}.png"))
            print(a, f"{time.time() - t0:.2f}s", f"depth {depth(t):.0f}")
    else:
        for a in sys.argv[1:]:
            render_segment(int(a))
