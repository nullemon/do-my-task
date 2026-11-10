"""FRIDAY THE 13TH, 2029 - frame compositor (numpy + OpenCV + PIL). Every shot is a function of film time.

Usage: python3 comp.py T0 T1            -> $SCR/seg/seg_<frame0>.mp4 (x264 crf 14, silent)
       python3 comp.py --png t1 t2 ...  -> $SCR/chk/f_<t>.jpg stills
"""
import os, sys, math, subprocess, time, functools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import *
import timeline as TL
import ground

S = TL.START
TXT = (232, 236, 242); DIM = (170, 180, 195); AMB = (255, 200, 120); COOL = (150, 205, 255); RED = (255, 120, 95); YEL = (255, 214, 80)
SUN_AST = norm([-0.72, 0.60, 0.34])                       # camera-space sun that matches the asteroid sprite lighting
_cache = {}


def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]


def body_M(Rcam, gm):
    """camera-space normal -> Earth body frame, for a camera with axes Rcam in the equatorial frame"""
    return rot_axis((0, 0, 1), -gm) @ Rcam.T


def art_M(lon_c, lat_c, roll=0.0):
    """artistic Earth orientation: body point (lon_c, lat_c) faces the viewer, north up (then rolled)"""
    c = TL.lonlat(lon_c, lat_c, 0.0); R = look_at(c * 10, (0, 0, 0))
    if roll: R = rot_axis((0, 0, 1), math.radians(roll)) @ R
    return R.T


def sky(key, R, fov, **kw):
    return cached(("sky", key), lambda: render_sky(R, (W / 2) / math.tan(math.radians(fov) / 2), **kw))


def caption(T, lines, t, a, b, x=120, y=900, size=25, col=TXT, gap=1.62, anchor="l", stagger=0.0, wt="L"):
    for i, s in enumerate(lines):
        al = win(t, a + i * stagger, b, 0.9, 0.7)
        T.put((x, y + i * size * gap), s, size, al, col=col if i == 0 or not isinstance(col, list) else col, anchor=anchor, wt=wt)


def tag(T, x, y, s, al, col=TXT, size=20, dx=26, dy=-34, anchor="l"):
    """small label with a thin leader line from (x, y)"""
    if al <= 0.004: return
    T.line((x + dx * 0.25, y + dy * 0.25), (x + dx, y + dy), al * 0.7, col)
    T.put((x + dx + (8 if anchor == "l" else -8), y + dy - size * 0.75), s, size, al, col=col, anchor=anchor)


# ================================================================================================= satellites / ring helpers
RNG = np.random.default_rng(29)
SAT_LON = np.sort(RNG.uniform(0, 2 * np.pi, 420)); SAT_B = RNG.uniform(0.35, 1.0, 420) ** 1.5; SAT_PH = RNG.uniform(0, 6.28, 420)


def ring_art(img, cx, cy, R, M, t, gain=1.0, line=0.22, n=720, front_only=False):
    """GEO ring around an 'artistic' Earth (orthographic): M body<-camera so camera = M.T @ body"""
    a = np.linspace(0, 2 * np.pi, n + 1); rr = TL.R_GEO / TL.RE * R
    pb = np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], 1) @ M           # (body vec) @ M = M.T @ body -> camera
    x = cx + rr * pb[:, 0]; y = cy - rr * pb[:, 1]; z = pb[:, 2]
    hid = (z < 0) & ((x - cx) ** 2 + (y - cy) ** 2 < R * R)
    L = Lines(); xx = np.where(hid, np.nan, x)
    L.poly(xx, y, a=255, th=1); L.add_to(img, np.array(COOL) / 255, gain=line * gain, glow=0.8)
    ps = np.stack([np.cos(SAT_LON), np.sin(SAT_LON), np.zeros_like(SAT_LON)], 1) @ M
    sx = cx + rr * ps[:, 0]; sy = cy - rr * ps[:, 1]
    for i in range(len(sx)):
        if ps[i, 2] < 0 and (sx[i] - cx) ** 2 + (sy[i] - cy) ** 2 < R * R: continue
        if -5 < sx[i] < W + 5 and -5 < sy[i] < H + 5:
            tw = 0.75 + 0.25 * math.sin(t * 1.7 + SAT_PH[i])
            add_glint(img, sx[i], sy[i], SAT_B[i] * tw * 0.9 * gain, (0.85, 0.93, 1.0), sig=0.9 + 0.5 * SAT_B[i])


def ring_phys(img, cam, gm, t, gain=1.0, line=0.22, label=None):
    a = np.linspace(0, 2 * np.pi, 721)
    P = np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], 1) * TL.R_GEO
    x, y, d = cam.proj(P); ex, ey, eR, ed = cam.sphere((0, 0, 0), TL.RE)
    hid = (d > ed) & ((x - ex) ** 2 + (y - ey) ** 2 < eR * eR)
    L = Lines(); L.poly(np.where(hid, np.nan, x), y, th=1); L.add_to(img, np.array(COOL) / 255, gain=line * gain, glow=0.8)
    lo = SAT_LON + gm
    Ps = np.stack([np.cos(lo), np.sin(lo), np.zeros_like(lo)], 1) * TL.R_GEO
    sx, sy, sd = cam.proj(Ps)
    for i in range(len(sx)):
        if not np.isfinite(sx[i]) or (sd[i] > ed and (sx[i] - ex) ** 2 + (sy[i] - ey) ** 2 < eR * eR): continue
        if -5 < sx[i] < W + 5 and -5 < sy[i] < H + 5:
            tw = 0.75 + 0.25 * math.sin(t * 1.7 + SAT_PH[i])
            add_glint(img, sx[i], sy[i], SAT_B[i] * tw * 0.9 * gain, (0.85, 0.93, 1.0), sig=0.9 + 0.4 * SAT_B[i])


def path_phys(img, cam, tau0, tau1, col, gain=1.0, dash=None, n=260, th=1, fade_tail=False):
    taus = np.linspace(tau0, tau1, n); P = np.array([TL.apophis(x) for x in taus])
    x, y, d = cam.proj(P); ex, ey, eR, ed = cam.sphere((0, 0, 0), TL.RE)
    hid = (d > ed) & ((x - ex) ** 2 + (y - ey) ** 2 < eR * eR)
    L = Lines(); L.poly(np.where(hid, np.nan, x), y, th=th, dash=dash)
    if fade_tail:
        # brightness ramps along the trail: draw mask by param
        m = np.zeros((H, W), F32); xi = np.clip(np.nan_to_num(x, nan=-9).astype(int), 0, W - 1); yi = np.clip(np.nan_to_num(y, nan=-9).astype(int), 0, H - 1)
        m[yi, xi] = np.linspace(0.05, 1, n) ** 1.5; m = cv2.dilate(m, np.ones((9, 9), np.uint8)); m = cv2.GaussianBlur(m, (0, 0), 3)
        L.add_to(img, np.array(col) / 255, gain=gain, glow=0.9, mask=np.clip(m * 1.4, 0, 1))
    else:
        L.add_to(img, np.array(col) / 255, gain=gain, glow=0.7)


def apo_point(img, cam, tau, amp=1.6, sig=1.5, streak=7):
    p = TL.apophis(tau); x, y, d = cam.proj(p[None]); ex, ey, eR, ed = cam.sphere((0, 0, 0), TL.RE)
    x, y = float(x[0]), float(y[0])
    if d[0] > ed and (x - ex) ** 2 + (y - ey) ** 2 < eR * eR: return x, y, False
    add_glint(img, x, y, amp, (1.0, 0.86, 0.62), sig=sig, streak=streak)
    add_glint(img, x, y, amp * 0.25, (1.0, 0.7, 0.4), sig=sig * 5)
    return x, y, True


# ================================================================================================= shots
def shot_hook(t, lt):
    def bg():
        Rs = look_at((0, 0, 0), norm([0.35, 0.90, 0.25]))
        im = render_sky(Rs, (W / 2) / math.tan(math.radians(27)), gain=0.9).copy()
        draw_earth(im, EX, EY, ER, M, SUN_AST, night_gain=1.4)
        return im
    EX, EY, ER = 1385, 430, 150
    M = art_M(-18, 33, roll=-24)
    img = cached("hook_bg", bg).copy()
    ring_art(img, EX, EY, ER, M, t, gain=1.0, line=0.26)
    # tiny true-direction marker: where Apophis crosses, on the ring plane side toward us
    az = math.radians(-58); pb = np.array([math.cos(az), math.sin(az), 0.28]) * (TL.RP / TL.RE) * ER
    pc = M.T @ pb; mx, my = EX + pc[0], EY - pc[1]
    T = Text()
    al = win(t, 1.6, 16.8, 1.0, 1.0)
    if al > 0:
        L = Lines(); L.seg(EX + (mx - EX) * (ER + 5) / math.hypot(mx - EX, my - EY), EY + (my - EY) * (ER + 5) / math.hypot(mx - EX, my - EY), mx, my)
        L.add_to(img, np.array(YEL) / 255, gain=0.75 * al, glow=0.6)
        add_glint(img, mx, my, 1.3 * al, (1.0, 0.86, 0.6), sig=1.6, streak=6)
    # foreground asteroid
    k = ss(0, 22.4, t)
    ax = lerp(470, 640, t / 22.4); ay = lerp(640, 560, t / 22.4); sc = lerp(0.74, 0.66, t / 22.4)
    dim = 1 - 0.55 * ss(17.2, 19.0, t)
    put_sprite(img, ast_at(t * 24), ax, ay, sc, angle=-8 + t * 0.25, gain=1.0, alpha=1 - ss(17.4, 19.4, t))
    # type
    T.put((120, 96), "FRIDAY · 13 APRIL 2029", 27, win(t, 0.2, 17.2, 0.6), col=TXT)
    a1 = win(t, 1.3, 9.6, 0.8, 0.7)
    T.put((1080, 742), "32,000 KM", 118, a1, col=YEL, wt="XL", track=6)
    T.put((1086, 880), "ABOVE THE SURFACE  ·  INSIDE THE RING", 23, win(t, 2.4, 9.6))
    T.put((1086, 918), "OF GEOSTATIONARY SATELLITES", 23, win(t, 2.7, 9.6))
    T.put((60, 1030), "ASTEROID 99942 APOPHIS  ·  ARTIST'S MODEL  ·  FOREGROUND NOT TO SCALE WITH THE EARTH", 15, win(t, 1.5, 17.0) * 0.7, col=DIM)
    a2 = win(t, 10.3, 17.2, 0.9, 0.7)
    T.put((1080, 760), "IT WILL MISS.", 92, a2, col=TXT, wt="T", track=8)
    T.put((1086, 880), "IMPACT RULED OUT FOR AT LEAST 100 YEARS", 23, win(t, 11.6, 17.2))
    tag(T, mx, my, "APOPHIS · CLOSEST APPROACH", win(t, 2.6, 16.8), col=YEL, size=17, dx=-40, dy=46, anchor="r")
    a3 = win(t, 18.0, 22.4, 1.1, 0.6)
    T.put((W / 2, 660), "FRIDAY THE 13TH, 2029", 86, a3, wt="T", track=22, anchor="c")
    T.put((W / 2, 786), "AN ASTEROID WILL PASS CLOSER THAN OUR SATELLITES", 25, win(t, 18.9, 22.4, 1.0, 0.6), anchor="c", col=AMB)
    return T.add_to(bloom(img))


def shot_disc(t, lt):
    fov = 34
    Rs = look_at((0, 0, 0), norm([0.47, -0.61, 0.64]))                 # toward the summer Milky Way (Cygnus / Lyra region)
    base = sky("disc", Rs, fov, gain=1.35, mw_gain=2.3, mag_lim=11.5)
    dx = lt * 1.6; Mx = np.float32([[1.03, 0, -dx - 30], [0, 1.03, -16]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    T = Text()
    # the moving dot (first found), then lost, then found again elsewhere
    a1 = win(t, 24.2, 32.4, 1.0, 1.6)
    px = 1180 - (t - 24) * 9.5 - dx; py = 470 + (t - 24) * 4.2
    if a1 > 0:
        add_glint(img, px, py, 0.9 * a1, (1.0, 0.9, 0.75), sig=1.1)
        L = Lines(); L.circle(px, py, 26, a=255); L.seg(px + 34, py, px + 60, py); L.seg(px - 34, py, px - 60, py); L.seg(px, py - 34, px, py - 60); L.seg(px, py + 34, px, py + 60)
        L.add_to(img, np.array(AMB) / 255, gain=0.8 * a1, glow=0.5)
        tag(T, px + 20, py - 20, "2004 MN4", a1, col=AMB, size=19)
    caption(T, ["19 JUNE 2004  ·  KITT PEAK, ARIZONA", "ROY TUCKER  ·  DAVID THOLEN  ·  FABRIZIO BERNARDI"], t, 23.6, 33.2, y=890, stagger=0.9)
    T.put((120, 975), "OBSERVED FOR TWO NIGHTS, THEN LOST", 21, win(t, 29.6, 33.2), col=DIM)
    a2 = win(t, 34.2, 39.8, 0.9, 0.8)
    qx = 760 - (t - 34) * 13 - dx * 0.2; qy = 610 - (t - 34) * 5
    if a2 > 0:
        add_glint(img, qx, qy, 1.1 * a2, (1.0, 0.9, 0.75), sig=1.2)
        L = Lines(); L.circle(qx, qy, 26); L.seg(qx + 34, qy, qx + 60, qy); L.seg(qx - 34, qy, qx - 60, qy); L.seg(qx, qy - 34, qx, qy - 60); L.seg(qx, qy + 34, qx, qy + 60)
        L.add_to(img, np.array(AMB) / 255, gain=0.8 * a2, glow=0.5)
    caption(T, ["18 DECEMBER 2004  ·  FOUND AGAIN", "SIDING SPRING, AUSTRALIA"], t, 34.2, 39.8, y=890, stagger=0.8)
    T.put((W - 60, 1030), "ILLUSTRATION  ·  REAL STAR POSITIONS, NOT THE ACTUAL DISCOVERY FIELD", 15, win(t, 23.4, 39.4) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img, 0.8, 0.4))


# ---- the "range of possible positions" shot (scare + relief) -----------------------------------------------------------
BAND_RNG = np.random.default_rng(4); BAND_U = BAND_RNG.standard_normal(2600); BAND_V = BAND_RNG.standard_normal(2600); BAND_B = BAND_RNG.uniform(0.3, 1, 2600)


def _band_cam():
    n = np.cross(TL.P_HAT, TL.Q_HAT); pp = np.cross(n, TL.P_HAT); th = math.radians(19)
    for sgn in (1, -1):
        c = Cam(n * 2.2e6, 0.5 * TL.RP * TL.P_HAT + 2500 * pp * sgn, 2.66, up=math.sin(th) * TL.P_HAT + sgn * math.cos(th) * pp)
        x, y, _ = c.proj(np.array([[0, 0, 0], TL.RP * TL.P_HAT]))
        if x[1] > x[0] and y[1] < y[0]: break
    c.ox, c.oy = 150.0, -150.0
    return c


def _band_state(t):
    """(half-length px, offset of the band centre from Earth along the line, as a fraction of the way to the true pass point)"""
    keys = [(0, 760, 0.30), (66.8, 760, 0.30), (69.0, 420, 0.62), (72.0, 420, 0.62), (74.0, 170, 0.90), (77.0, 170, 0.90), (79.0, 46, 0.985),
            (88.0, 46, 0.985), (90.5, 2.5, 1.0), (999, 2.5, 1.0)]
    ts = [k[0] for k in keys]; i = max(0, min(len(keys) - 2, int(np.searchsorted(ts, t, side="right") - 1))); a, b = keys[i], keys[i + 1]
    u = ss(a[0], b[0], t)
    return a[1] * (b[1] / a[1]) ** u, lerp(a[2], b[2], u)


def _band_shot(t):
    cam = _band_cam()
    def bg():
        im = render_sky(cam.R, (W / 2) / math.tan(math.radians(24)), gain=0.8, mw_gain=1.4).copy()
        ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
        draw_earth(im, ex, ey, eR, body_M(cam.R, TL.GMST0), cam.R @ TL.SUN, night_gain=1.3)
        return im
    img = cached("band_bg", bg).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    px, py, _ = cam.proj(TL.apophis(0.0)[None]); px, py = float(px[0]), float(py[0])
    d = np.array([px - ex, py - ey]); dist = np.linalg.norm(d); d /= dist; nrm = np.array([-d[1], d[0]])
    L, frac = _band_state(t)
    c = np.array([ex, ey]) + d * dist * frac
    wv = max(1.2, min(7.0, L * 0.012))
    pts = c[None] + BAND_U[:, None] * L * d[None] + BAND_V[:, None] * wv * nrm[None]
    lay = np.zeros((H, W), F32)
    ok = (pts[:, 0] > 1) & (pts[:, 0] < W - 2) & (pts[:, 1] > 1) & (pts[:, 1] < H - 2) & ((pts[:, 0] - ex) ** 2 + (pts[:, 1] - ey) ** 2 > (eR * 0.0) ** 2)
    np.add.at(lay, (pts[ok, 1].astype(int), pts[ok, 0].astype(int)), BAND_B[ok])
    dens = min(3.0, 760.0 / max(L, 30)) ** 0.55
    lay = cv2.GaussianBlur(lay, (0, 0), 1.0) * 1.5 + cv2.GaussianBlur(lay, (0, 0), 5) * 0.9 + cv2.GaussianBlur(lay, (0, 0), 16) * 0.5
    band_a = 1 - ss(89.5, 91.5, t)
    img += lay[..., None] * np.array([1.0, 0.72, 0.36], F32) * (1.1 / dens ** 0.2) * band_a * ss(40.4, 42.5, t)
    return img, cam, (ex, ey, eR), (px, py), d, dist, c, L


TORINO = [(255, 255, 255)] + [(110, 200, 120)] + [(245, 215, 90)] * 3 + [(245, 160, 70)] * 3 + [(235, 85, 70)] * 3


def shot_scare(t, lt):
    img, cam, (ex, ey, eR), (px, py), d, dist, c, L = _band_shot(t)
    T = Text()
    T.put((120, 96), "LATE DECEMBER 2004", 27, win(t, 40.0, 58.4))
    tag(T, ex + d[0] * 250 - d[1] * 4, ey + d[1] * 250, "RANGE OF POSSIBLE POSITIONS ON 13 APRIL 2029", win(t, 41.5, 58.2), col=AMB, size=19, dx=40, dy=-70)
    tag(T, ex - eR * 0.7, ey - eR * 0.7, "EARTH", win(t, 41.0, 58.2), col=COOL, size=19, dx=-46, dy=-50, anchor="r")
    # probability
    a = win(t, 42.2, 58.4, 1.0, 0.7)
    p = lerp(0.3, 2.7, ss(42.2, 47.2, t))
    T.put((120, 742), "CHANCE OF IMPACT ON 13 APRIL 2029", 22, a, col=DIM)
    T.put((114, 772), f"{p:.1f} %", 120, a, col=YEL, wt="T", track=4)
    T.put((480, 842), "1 IN 37", 34, win(t, 50.6, 58.4), wt="L")
    T.put((480, 890), "PEAK ESTIMATE · 27 DEC 2004", 18, win(t, 51.2, 58.4), col=DIM)
    # Torino scale
    a = win(t, 52.6, 58.4, 0.9, 0.7)
    x0, y0, cw = 1130, 880, 56
    T.put((x0, y0 - 52), "TORINO IMPACT HAZARD SCALE", 20, a, col=DIM)
    for i in range(11):
        on = (i == 4)
        col = TORINO[i]
        T.d.rectangle((x0 + i * cw, y0, x0 + i * cw + cw - 6, y0 + (16 if on else 6)), fill=col + (int(255 * a * (1.0 if on else 0.55)),)); T.used = True
        T.put((x0 + i * cw + (cw - 6) / 2, y0 + 26), str(i), 18 if not on else 24, a * (1 if on else 0.6), anchor="c", col=TXT if not on else YEL, track=0)
    T.put((x0, y0 + 70), "LEVEL 4  ·  THE HIGHEST RATING EVER GIVEN", 22, win(t, 54.0, 58.4), col=YEL)
    T.put((W - 60, 1030), "SCHEMATIC  ·  EARTH AND DISTANCES TO SCALE", 15, win(t, 40.4, 58.2) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img))


def shot_relief(t, lt):
    img, cam, (ex, ey, eR), (px, py), d, dist, c, L = _band_shot(t)
    T = Text()
    # after the radar fix: the actual path
    ar = ss(89.5, 92.0, t)
    if ar > 0:
        path_phys(img, cam, -9, 9, AMB, gain=0.55 * ar, n=300)
        add_glint(img, px, py, 1.5 * ar, (1.0, 0.86, 0.62), sig=1.6, streak=7)
        tag(T, px, py, "APOPHIS · 13 APRIL 2029", win(t, 90.5, 94.8), col=AMB, size=19, dx=34, dy=-44)
        tag(T, (ex + px) / 2, (ey + py) / 2, "≈ 38,000 KM FROM EARTH'S CENTRE", win(t, 91.2, 94.8), col=DIM, size=17, dx=30, dy=60)
        Ls = Lines(); Ls.seg(ex + d[0] * (eR + 6), ey + d[1] * (eR + 6), px - d[0] * 8, py - d[1] * 8); Ls.add_to(img, (0.6, 0.65, 0.72), gain=0.35 * ar, glow=0.3)
    tag(T, ex - eR * 0.7, ey - eR * 0.7, "EARTH", win(t, 64.4, 94.8), col=COOL, size=19, dx=-46, dy=-50, anchor="r")
    tag(T, c[0], c[1], "POSSIBLE POSITIONS", win(t, 65.0, 89.5), col=AMB, size=19, dx=40, dy=-70)
    T.put((120, 96), "EVERY OBSERVATION NARROWS THE RANGE", 27, win(t, 66.0, 80.8))
    T.put((120, 96), "MARCH 2021  ·  RADAR", 27, win(t, 82.6, 94.6))
    p = 2.7 * (1 - ss(73.2, 75.0, t))
    a = win(t, 64.2, 80.8, 0.4, 0.8)
    T.put((120, 742), "CHANCE OF IMPACT ON 13 APRIL 2029", 22, a, col=DIM)
    T.put((114, 772), f"{p:.1f} %" if p > 0.05 else "0", 120, a, col=YEL if p > 0.05 else TXT, wt="T", track=4)
    T.put((120, 925), "27 DEC 2004  ·  OVERLOOKED IMAGES FROM MARCH 2004 EXTEND THE ORBIT ARC", 20, win(t, 72.6, 80.8), col=DIM)
    T.put((120, 960), "2029 IMPACT RULED OUT", 24, win(t, 76.6, 80.8), col=TXT)
    caption(T, ["2036  ·  RULED OUT IN 2013", "2068  ·  RULED OUT IN MARCH 2021"], t, 82.0, 94.6, y=770, size=24, stagger=1.3, col=DIM)
    T.put((120, 868), "GOLDSTONE + GREEN BANK RADAR", 22, win(t, 85.6, 94.6), col=DIM)
    T.put((120, 912), "NO IMPACT RISK FOR AT LEAST 100 YEARS", 34, win(t, 89.6, 94.6), col=TXT)
    T.put((W - 60, 1030), "SCHEMATIC  ·  EARTH AND DISTANCES TO SCALE", 15, win(t, 64.4, 94.4) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img))


def _ast_bg(key, d, fov=30, mw=1.6, gain=0.85):
    return sky(key, look_at((0, 0, 0), norm(d)), fov, gain=gain, mw_gain=mw)


def shot_name(t, lt):
    img = _ast_bg("name", [0.6, -0.55, -0.4]).copy()
    u = lt / 6.0
    put_sprite(img, ast_at(160 + lt * 24), lerp(1010, 960, u), lerp(500, 520, u), lerp(0.98, 1.05, u), angle=4, gain=1.05)
    T = Text()
    T.put((120, 820), "99942 APOPHIS", 76, win(t, 59.2, 64.4, 0.9, 0.6), wt="T", track=18)
    T.put((124, 930), "NAMED IN 2005 FOR THE EGYPTIAN SERPENT OF CHAOS", 23, win(t, 60.2, 64.4, 0.9, 0.6), col=AMB)
    return T.add_to(bloom(img))


def _tower():
    a = cv2.imread(SCR + "/spr/tower.png", cv2.IMREAD_UNCHANGED).astype(F32) / 255; a = a[..., [2, 1, 0, 3]]; a[..., :3] *= a[..., 3:4]
    return a                                         # 0.2 m per px


def shot_size(t, lt):
    img = _ast_bg("size", [-0.3, 0.2, -0.93], mw=1.2).copy()
    z = ss(109.8, 113.2, t)                               # pull back for the tower
    sc = lerp(1.02, 0.60, z); mpp = 0.4 / sc
    ax = lerp(1080, 1130, z) - lt * 2.0 * (1 - z); ay = lerp(520, 500, z)
    ang = 0.0
    put_sprite(img, ast_at(lt * 24), ax, ay, sc, angle=ang, gain=1.05)
    T = Text()
    # tower: 0.2 m/px sprite
    at_ = ss(110.6, 113.0, t) * (1 - ss(116.2, 117.0, t) * 0)
    if at_ > 0:
        tw = cached("tower", _tower); ts = 0.2 / mpp
        base_y = ay + 165 / mpp                            # tower base level a little below the asteroid's centre
        tcx = 430; tcy = base_y - (331 / 2) / mpp + (2000 / 2 - (209 + 1654 / 2)) * ts
        put_sprite(img, tw, tcx, tcy, ts, gain=1.25, alpha=at_)
        ytop = base_y - 330 / mpp
        T.line((tcx - 210, ytop), (tcx - 210, base_y), at_ * 0.8); T.line((tcx - 222, ytop), (tcx - 198, ytop), at_ * 0.8); T.line((tcx - 222, base_y), (tcx - 198, base_y), at_ * 0.8)
        T.put((tcx - 230, (ytop + base_y) / 2 - 12), "330 M", 24, at_, anchor="r")
        T.put((tcx, base_y + 26), "EIFFEL TOWER", 22, at_, anchor="c")
        T.put((ax, base_y + 26), "APOPHIS  ·  ≈ 340 M MEAN DIAMETER", 22, at_, anchor="c", col=AMB)
        x0 = 800; T.line((x0, base_y + 100), (x0 + 100 / mpp, base_y + 100), at_ * 0.9); T.line((x0, base_y + 94), (x0, base_y + 106), at_ * 0.9); T.line((x0 + 100 / mpp, base_y + 94), (x0 + 100 / mpp, base_y + 106), at_ * 0.9)
        T.put((x0 + 100 / mpp + 16, base_y + 89), "100 M  ·  SAME SCALE", 18, at_, col=DIM)
    b = 110.0
    T.put((120, 150), "≈ 340 M", 92, win(t, 97.6, b, 0.9, 0.7), wt="T", track=6, col=YEL)
    T.put((126, 268), "MEAN DIAMETER (RADAR: 340 ± 40 M)", 21, win(t, 98.2, b), col=DIM)
    T.put((126, 330), "STONY  ·  ELONGATED", 24, win(t, 100.6, b))
    T.put((126, 372), "POSSIBLY TWO LOBES IN CONTACT", 24, win(t, 102.6, b))
    T.put((126, 414), "TUMBLING  ·  ≈ 30.6 HOURS PER TURN", 24, win(t, 105.4, b))
    T.put((60, 1030), "ARTIST'S MODEL GUIDED BY RADAR  ·  THE REAL SURFACE HAS NEVER BEEN SEEN UP CLOSE", 15, win(t, 95.0, 116.6) * 0.7, col=DIM)
    return T.add_to(bloom(img))


# ---- true-scale Earth system ---------------------------------------------------------------------------------------------
def _geo_dir():
    # camera direction: 24 deg above the equatorial plane, on the evening side so day and night are both visible
    h = rot_axis((0, 0, 1), math.radians(-22)) @ norm(np.array([TL.P_HAT[0], TL.P_HAT[1], 0.0])); e = math.radians(52)
    return math.cos(e) * h + math.sin(e) * np.array([0, 0, 1.0])


GEO_FOV = 30.0


def _geo_cam(dist):
    e = _geo_dir() * dist
    return Cam(e, (0, 0, 0), GEO_FOV)


def _sys_frame(cam, gm, t, sky_key, ring=1.0, night=1.3, sky_gain=1.25):
    img = sky(sky_key, cam.R, GEO_FOV, gain=sky_gain, mw_gain=1.8).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    draw_earth(img, ex, ey, eR, body_M(cam.R, gm), cam.R @ TL.SUN, t=t, night_gain=night)
    if ring > 0: ring_phys(img, cam, gm, t, gain=ring)
    return img, (ex, ey, eR)


D_NEAR, D_FAR = 62000.0, 272000.0


def shot_geo(t, lt):
    u = ss(121.0, 128.5, t)
    dist = D_NEAR * (D_FAR / D_NEAR) ** u
    cam = _geo_cam(dist)
    img, (ex, ey, eR) = _sys_frame(cam, TL.GMST0 - TL.OMEGA * 6, t, "geo", ring=ss(122.5, 126.0, t))
    T = Text()
    tag(T, ex - eR * 0.72, ey - eR * 0.72, "EARTH  ·  12,742 KM ACROSS", win(t, 119.4, 124.0), col=COOL, size=21, dx=-50, dy=-50, anchor="r")
    ga = np.linspace(0, 2 * np.pi, 90); gx, gy, _ = cam.proj(np.stack([TL.R_GEO * np.cos(ga), TL.R_GEO * np.sin(ga), 0 * ga], 1)); gi = int(np.argmax(gx - gy))
    a = win(t, 125.4, 132.6)
    tag(T, float(gx[gi]), float(gy[gi]), "GEOSTATIONARY RING", a, col=COOL, size=22, dx=40, dy=-50)
    T.put((120, 84), "35,786 KM", 76, win(t, 126.0, 132.6, 0.9, 0.7), wt="T", track=6, col=COOL)
    T.put((126, 182), "ABOVE THE EQUATOR  ·  TELEVISION, WEATHER, COMMUNICATIONS", 21, win(t, 127.0, 132.6), col=DIM)
    T.put((W - 60, 1030), "TRUE SCALE  ·  EACH GLINT STANDS FOR A SATELLITE (POSITIONS ILLUSTRATIVE)", 15, win(t, 124.0, 132.4) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img))


def shot_moon(t, lt):
    # camera beyond the Moon, looking back past it toward the Earth: true distances, true sizes
    md = norm(0.94 * TL.SUN + 0.30 * norm(np.cross([0, 0, 1], TL.SUN)) + np.array([0, 0, 0.09]))
    mpos = md * TL.R_MOON
    c0 = Cam(mpos + md * 30000.0, (0, 0, 0), 19.0)
    eye = mpos + md * 30000.0 + c0.R[0] * (5020 - lt * 55) + c0.R[1] * 2090
    cam = Cam(eye, (0, 0, 0), 19.0); cam.ox, cam.oy = 330.0, -140.0
    side = c0.R[0]
    img = sky("moon", cam.R, 19.0, gain=1.0, mw_gain=1.6).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    gm = TL.GMST0
    draw_earth(img, ex, ey, eR, body_M(cam.R, gm), cam.R @ TL.SUN, night_gain=1.2)
    ring_phys(img, cam, gm, t, gain=0.8, line=0.2)
    mx, my, mR, _ = cam.sphere(mpos, 1737.4)
    sunc = norm(np.array([0.80, 0.45, 0.40]))        # artistic: raking light so the relief reads
    draw_moon(img, mx, my, mR, rot_axis((0, 0, 1), 2.4) @ rot_axis((1, 0, 0), 1.2) @ cam.R.T, sunc, exposure=0.8)
    T = Text()
    tag(T, ex, ey - eR - 6, "EARTH", win(t, 132.9, 137.6), col=COOL, size=20, dx=30, dy=-46)
    T.put((1180, 800), "384,400 KM", 76, win(t, 133.4, 137.6, 0.8, 0.6), wt="T", track=6)
    T.put((1186, 898), "THE MOON'S AVERAGE DISTANCE", 21, win(t, 134.0, 137.6), col=DIM)
    T.put((60, 1030), "TRUE SIZES AND DISTANCES  ·  MOON POSITION AND LIGHTING ILLUSTRATIVE", 15, win(t, 132.8, 137.4) * 0.7, col=DIM)
    return T.add_to(bloom(img))


def _tau_pass(t):
    """film time -> hours from closest approach in the pass shot (slows through closest approach)"""
    keys = [(137.0, -7.0), (146.5, -0.9), (149.0, -0.05), (153.0, 0.25), (160.6, 5.0)]
    ts = [k[0] for k in keys]; t = min(max(t, ts[0]), ts[-1]); i = max(0, min(len(keys) - 2, int(np.searchsorted(ts, t, side="right") - 1))); a, b = keys[i], keys[i + 1]
    return lerp(a[1], b[1], (t - a[0]) / (b[0] - a[0]))


def _clock(tau):
    m = int(round(21 * 60 + 46 + tau * 60)); day = 13 + (m // 1440); m %= 1440
    return f"{day} APR 2029  ·  {m // 60:02d}:{m % 60:02d} UTC"


def shot_pass(t, lt):
    tau = _tau_pass(t); gm = TL.GMST0 + TL.OMEGA * tau
    cam = _geo_cam(D_FAR)
    img, (ex, ey, eR) = _sys_frame(cam, gm, t, "geo")
    path_phys(img, cam, tau, 9.0, AMB, gain=0.16, dash=3, n=300)
    path_phys(img, cam, max(-9.0, tau - 4.5), tau, AMB, gain=0.85, n=220, fade_tail=True)
    x, y, vis = apo_point(img, cam, tau, amp=1.8, sig=1.6, streak=8)
    pa = TL.apophis(tau); fx, fy, _ = cam.proj(np.array([[pa[0], pa[1], 0.0]]))
    Ls = Lines(); Ls.poly(np.linspace(x, float(fx[0]), 40), np.linspace(y, float(fy[0]), 40), dash=2); Ls.circle(float(fx[0]), float(fy[0]), 3)
    Ls.add_to(img, np.array(AMB) / 255, gain=0.45, glow=0.3)
    T = Text()
    tag(T, x, y, "APOPHIS", win(t, 138.4, 160.4), col=AMB, size=20, dx=30, dy=-40)
    r = np.linalg.norm(TL.apophis(tau)); alt = r - 6378
    T.put((120, 96), _clock(tau), 27, win(t, 137.6, 160.2))
    a = win(t, 139.0, 152.0)
    T.put((120, 800), "HEIGHT ABOVE THE SURFACE", 20, a, col=DIM)
    T.put((116, 828), f"{int(round(alt, -2)):,} KM", 76, a, wt="T", track=5, col=YEL)
    T.put((720, 800), "SPEED", 20, a, col=DIM)
    T.put((716, 828), f"{TL.speed(tau):.1f} KM/S", 76, a, wt="T", track=5)
    cx_, cy_, _ = cam.proj(TL.apophis(0.0)[None]); cx_, cy_ = float(cx_[0]), float(cy_[0])
    ac = win(t, 149.2, 160.2)
    if ac > 0:
        Ls = Lines(); dd = np.array([cx_ - ex, cy_ - ey]); n_ = np.linalg.norm(dd); dd /= n_
        Ls.seg(ex + dd[0] * (eR + 4), ey + dd[1] * (eR + 4), cx_ - dd[0] * 6, cy_ - dd[1] * 6); Ls.add_to(img, np.array(YEL) / 255, gain=0.6 * ac, glow=0.5)
        T.put(((ex + cx_) / 2 + 16, (ey + cy_) / 2 + 8), "≈ 32,000 KM", 22, ac, col=YEL)
    ga = np.linspace(0, 2 * np.pi, 90); gx, gy, _ = cam.proj(np.stack([TL.R_GEO * np.cos(ga), TL.R_GEO * np.sin(ga), 0 * ga], 1)); gi = int(np.argmax(gx - gy))
    tag(T, float(gx[gi]), float(gy[gi]), "GEOSTATIONARY RING · 35,786 KM", win(t, 143.0, 160.2), col=COOL, size=18, dx=40, dy=-50)
    T.put((120, 940), "CLOSER THAN THE SATELLITE RING  ·  ABOUT ONE TENTH OF THE WAY TO THE MOON", 22, win(t, 146.4, 152.0), col=TXT)
    T.put((120, 150), "IT PASSES NORTH OF THE RING'S PLANE, NOT THROUGH THE SATELLITES", 20, win(t, 147.6, 160.2), col=DIM)
    caption(T, ["THIS CLOSE, THIS LARGE:", "ROUGHLY ONCE IN SEVERAL THOUSAND YEARS"], t, 152.8, 160.2, y=880, size=27, stagger=0.7)
    T.put((W - 60, 1030), "TRUE SCALE  ·  PATH RECONSTRUCTED FROM PUBLISHED FLYBY VALUES (APPROXIMATE)  ·  TIME-LAPSE", 15, win(t, 138.0, 160.0) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img))


NIGHT_TAU = -0.92


def _night_cam():
    return Cam(norm(TL.apophis(NIGHT_TAU)) * 64000.0, (0, 0, 0), 20.0)


def shot_night(t, lt):
    cam = _night_cam()
    def bg():
        im = render_sky(cam.R, cam.f, gain=1.0).copy()
        ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
        draw_earth(im, ex, ey, eR, body_M(cam.R, TL.GMST0 + TL.OMEGA * NIGHT_TAU), cam.R @ TL.SUN, night_gain=1.5)
        return im
    base = cached("night_bg", bg)
    s = 1.0 + 0.05 * (lt / 15.0); Mx = np.float32([[s, 0, (1 - s) * 1100], [0, s, (1 - s) * 330]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR)
    tau = lerp(-1.035, -0.80, (t - 160.2) / 14.8)
    # Apophis is between the camera and the Earth here: a point of light sliding over the night side
    def scr(q):
        x, y, _ = cam.proj(np.array([TL.apophis(q)])); return float(x[0]) * s + Mx[0, 2], float(y[0]) * s + Mx[1, 2]
    x, y = scr(tau)
    m = np.zeros((H, W), F32); prev = None
    for i in range(60):
        q = scr(tau - 0.05 * (1 - i / 59))
        if prev is not None: cv2.line(m, (int(prev[0]), int(prev[1])), (int(q[0]), int(q[1])), float((i / 59) ** 2), 1, cv2.LINE_AA)
        prev = q
    img += cv2.GaussianBlur(m, (0, 0), 1.2)[..., None] * np.array([1.0, 0.8, 0.5], F32) * 0.7
    add_glint(img, x, y, 2.0, (1.0, 0.88, 0.66), sig=1.8, streak=10); add_glint(img, x, y, 0.3, (1.0, 0.7, 0.4), sig=9)
    T = Text()
    tag(T, x, y, "APOPHIS", win(t, 160.8, 175.0), col=AMB, size=20, dx=34, dy=-30)
    T.put((120, 96), "THE EVENING OF 13 APRIL 2029", 27, win(t, 160.6, 175.0))
    T.put((120, 770), "VISIBLE WITHOUT A TELESCOPE", 22, win(t, 162.6, 175.0), col=DIM)
    T.put((116, 800), "EUROPE  ·  AFRICA  ·  WESTERN ASIA", 50, win(t, 165.2, 175.0, 0.9, 0.7), wt="XL", track=7)
    T.put((120, 888), "ABOUT 2 BILLION PEOPLE", 34, win(t, 168.8, 175.0), col=YEL)
    T.put((120, 946), "GIVEN A CLEAR, DARK SKY", 21, win(t, 170.6, 175.0), col=DIM)
    T.put((W - 60, 1030), "ABOUT AN HOUR BEFORE CLOSEST APPROACH  ·  CITY LIGHTS: NASA  ·  PATH APPROXIMATE  ·  TIME-LAPSE", 15, win(t, 160.6, 174.8) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img, 0.7, 0.5))


def shot_ground(t, lt, which):
    return ground.frame(t, lt, which)


# ---- heliocentric orbit diagram ------------------------------------------------------------------------------------------
def _ellipse(a, e, w, n=400):
    f = np.linspace(0, 2 * np.pi, n + 1); r = a * (1 - e * e) / (1 + e * np.cos(f))
    return np.stack([r * np.cos(f + w), r * np.sin(f + w), np.zeros_like(f)], 1)


def _kepler_pos(a, e, w, f0, dt_years):
    """position after dt (years) starting at true anomaly f0"""
    E0 = 2 * math.atan2(math.sqrt(1 - e) * math.sin(f0 / 2), math.sqrt(1 + e) * math.cos(f0 / 2)); M0 = E0 - e * math.sin(E0)
    M = M0 + 2 * math.pi * dt_years / a ** 1.5; E = M
    for _ in range(30): E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    f = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2)); r = a * (1 - e * math.cos(E))
    return np.array([r * math.cos(f + w), r * math.sin(f + w), 0.0])


def shot_orbit(t, lt):
    AU = 1.0
    cam = Cam(np.array([0.35, -2.9, 2.35]), (0.12, -0.05, 0), 40.0)
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.2, 0.9, -0.4])), cam.f * 0.9, gain=0.8, mw_gain=2.0).copy()
        sx, sy, _ = cam.proj(np.zeros((1, 3))); sx, sy = float(sx[0]), float(sy[0])
        yy, xx = np.mgrid[0:H, 0:W].astype(F32); r = np.hypot(xx - sx, (yy - sy) * 1.0)
        glow = np.exp(-r / 16) * 3.0 + np.exp(-r / 70) * 0.55 + np.exp(-r / 300) * 0.14
        streak = np.exp(-np.abs(yy - sy) / 2.2) * np.exp(-np.abs(xx - sx) / 420) * 0.5
        im += (glow + streak)[..., None] * np.array([1.0, 0.86, 0.62], F32)
        return im
    img = cached("orbit_bg", bg).copy()
    enc = np.array([-1.003, 0.0, 0.0])                         # encounter point (Earth on 13 April), drawn toward the viewer's left
    th_e = math.pi
    a0, e0, f0 = 0.9224, 0.1912, math.radians(-126.7); w0 = th_e - f0
    a1, e1, f1 = 1.103, 0.189, math.radians(-71.4); w1 = th_e - f1
    yr = lerp(-0.42, 0.50, ss(195.2, 210.2, t) * 0.5 + 0.5 * (lt / 16.0))     # years from the encounter
    k_after = ss(200.6, 203.0, t)
    def draw(P, col, gain, dash=None, th=1):
        x, y, _ = cam.proj(P); L = Lines(); L.poly(x, y, th=th, dash=dash); L.add_to(img, np.array(col) / 255, gain=gain, glow=0.7)
    draw(_ellipse(0.723, 0.007, 0), DIM, 0.10); draw(_ellipse(1.524, 0.093, 5.0), DIM, 0.09)
    draw(_ellipse(1.0, 0.0167, 1.8), COOL, 0.55)
    draw(_ellipse(a0, e0, w0), AMB, lerp(0.7, 0.28, k_after), dash=None if k_after < 0.5 else 4)
    if k_after > 0: draw(_ellipse(a1, e1, w1), (255, 244, 225), 0.8 * k_after)
    pe = _kepler_pos(1.0, 0.0167, 1.8, th_e - 1.8, yr)
    pa = _kepler_pos(a0, e0, w0, f0, yr) if yr < 0 else _kepler_pos(a1, e1, w1, f1, yr)
    xe, ye, _ = cam.proj(pe[None]); xa, ya, _ = cam.proj(pa[None]); xe, ye, xa, ya = float(xe[0]), float(ye[0]), float(xa[0]), float(ya[0])
    add_glint(img, xe, ye, 1.6, (0.55, 0.78, 1.0), sig=2.2, streak=5)
    add_glint(img, xa, ya, 1.3, (1.0, 0.86, 0.62), sig=1.6, streak=5)
    fl = math.exp(-((yr) / 0.012) ** 2)
    if fl > 0.02: add_glint(img, xe, ye, 2.0 * fl, (1, 1, 1), sig=5, streak=22)
    T = Text()
    tag(T, xe, ye, "EARTH", win(t, 195.0, 210.4), col=COOL, size=19, dx=-30, dy=40, anchor="r")
    tag(T, xa, ya, "APOPHIS", win(t, 195.0, 210.4), col=AMB, size=19, dx=28, dy=-36)
    sx, sy, _ = cam.proj(np.zeros((1, 3))); T.put((float(sx[0]) + 34, float(sy[0]) + 20), "SUN", 18, win(t, 195.0, 210.4) * 0.8, col=DIM)
    for (a_, e_, w_, lab) in ((0.723, 0.007, 0, "VENUS"), (1.524, 0.093, 5.0, "MARS")):
        p = _ellipse(a_, e_, w_, 8)[1 if lab == "VENUS" else 7]; x, y, _ = cam.proj(p[None]); T.put((float(x[0]) + 10, float(y[0]) - 8), lab, 14, win(t, 195.0, 210.4) * 0.55, col=DIM)
    a = win(t, 196.4, 210.4)
    T.put((120, 780), "BEFORE", 20, a, col=AMB); T.put((120, 812), "ATEN-CLASS ORBIT", 30, a); T.put((120, 860), "ONE LAP OF THE SUN ≈ 0.9 YEARS", 21, a, col=DIM)
    a = win(t, 202.4, 210.4)
    T.put((720, 780), "AFTER", 20, a, col=(255, 244, 225)); T.put((720, 812), "APOLLO-CLASS ORBIT", 30, a); T.put((720, 860), "ONE LAP OF THE SUN ≈ 1.2 YEARS", 21, a, col=DIM)
    T.put((120, 96), "13 APRIL 2029  ·  EARTH'S GRAVITY BENDS THE PATH BY ROUGHLY 27°", 27, win(t, 197.6, 210.4))
    T.put((W - 60, 1030), "ORBIT SIZES AND SHAPES TO SCALE  ·  ORIENTATION SCHEMATIC  ·  SUN AND PLANETS NOT TO SCALE", 15, win(t, 195.0, 210.2) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img, 0.8, 0.5))


def shot_tides(t, lt):
    EX, EY, ER = 560, 600, 345
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([-0.7, 0.3, 0.64])), (W / 2) / math.tan(math.radians(27)), gain=0.8).copy()
        draw_earth(im, EX, EY, ER, art_M(-28, 20, roll=14), SUN_AST, night_gain=1.4)
        return im
    base = cached("tides_bg", bg)
    Mx = np.float32([[1, 0, lt * 2.2 - 14], [0, 1, lt * 0.6]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    u = lt / 12.4
    put_sprite(img, ast_at(200 + lt * 24), lerp(1500, 1340, u), lerp(470, 520, u), lerp(0.60, 0.68, u), angle=-12 + lt * 0.5, gain=1.05)
    T = Text()
    T.put((120, 96), "CLOSEST APPROACH  ·  EARTH SPANS ABOUT 19° OF ITS SKY", 27, win(t, 211.0, 222.8))
    caption(T, ["THE TUMBLE MAY SPEED UP OR SLOW DOWN", "SMALL LANDSLIDES ARE POSSIBLE  ·  NOT CERTAIN", "IT PASSES TOO FAR OUT TO BE PULLED APART"], t, 212.6, 222.8, x=1010, y=830, size=23, stagger=2.2)
    T.put((60, 1030), "EARTH AT ITS TRUE APPARENT SIZE FROM 38,000 KM  ·  ASTEROID ENLARGED", 15, win(t, 210.8, 222.6) * 0.7, col=DIM)
    return T.add_to(bloom(img))


def _craft(name):
    a = cv2.imread(f"{SCR}/spr/{name}.png", cv2.IMREAD_UNCHANGED).astype(F32) / 255; a = a[..., [2, 1, 0, 3]]; a[..., :3] *= a[..., 3:4]
    return a


def shot_miss(t, lt):
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.1, -0.6, -0.79])), (W / 2) / math.tan(math.radians(26)), gain=0.85, mw_gain=1.8).copy()
        draw_earth(im, 1640, 215, 46, art_M(-40, 10, roll=-30), SUN_AST, night_gain=1.3)
        return im
    img = cached("miss_bg", bg).copy()
    u = lt / 32.0
    k2 = ss(236.9, 237.9, t)
    if k2 < 1: put_sprite(img, ast_at(lt * 24), lerp(640, 600, lt / 15.0), lerp(600, 580, lt / 15.0), lerp(0.58, 0.62, lt / 15.0), angle=10 - lt * 0.2, gain=1.05, alpha=1 - k2)
    if k2 > 0:
        l2 = t - 237.0; put_sprite(img, ast_at(110 + l2 * 24), lerp(520, 600, l2 / 17.8), lerp(560, 600, l2 / 17.8), lerp(0.66, 0.60, l2 / 17.8), angle=-14 + l2 * 0.2, gain=1.05, alpha=k2)
    T = Text()
    a1 = win(t, 223.0, 237.6, 1.2, 1.0); a2 = win(t, 237.2, 254.8, 1.2, 0.8)
    if a1 > 0:
        cx_, cy_ = lerp(1330, 1290, (t - 223) / 14.6), lerp(470, 452, (t - 223) / 14.6)
        put_sprite(img, cached("apex", lambda: _craft("apex")), cx_, cy_, 0.52, angle=-6 + (t - 223) * 0.3, gain=1.05, alpha=a1)
        T.put((1010, 740), "OSIRIS-APEX", 60, a1, wt="T", track=10)
        T.put((1014, 822), "NASA  ·  FORMERLY OSIRIS-REX (BENNU SAMPLE RETURN)", 20, win(t, 224.4, 237.4), col=AMB)
        T.put((1014, 866), "ALREADY EN ROUTE  ·  RENDEZVOUS PLANNED AFTER THE FLYBY", 20, win(t, 229.0, 237.4))
        T.put((1014, 902), "FUNDING IS REVIEWED YEAR BY YEAR", 20, win(t, 233.2, 237.4), col=DIM)
    if a2 > 0:
        cx_, cy_ = lerp(1360, 1300, (t - 237.2) / 17.6), lerp(430, 455, (t - 237.2) / 17.6)
        put_sprite(img, cached("ramses", lambda: _craft("ramses")), cx_, cy_, 0.62, angle=8 - (t - 237.2) * 0.25, gain=1.05, alpha=a2)
        ac = win(t, 246.5, 254.8)
        for k, (ox, oy) in enumerate(((-230, 150), (-150, 205))):
            add_glint(img, cx_ + ox - (t - 246) * 3 * (k + 1), cy_ + oy + (t - 246) * 2, 0.9 * ac, (1.0, 0.95, 0.85), sig=1.3, streak=3)
        tag(T, cx_ - 230 - (t - 246) * 3, cy_ + 150 + (t - 246) * 2, "TWO CUBESATS", ac, col=DIM, size=16, dx=-30, dy=36, anchor="r")
        T.put((1010, 740), "RAMSES", 60, a2, wt="T", track=10)
        T.put((1014, 822), "EUROPEAN SPACE AGENCY, WITH JAPAN  ·  APPROVED NOV 2025", 20, win(t, 238.4, 254.6), col=AMB)
        T.put((1014, 866), "LAUNCH PLANNED FOR SPRING 2028  ·  ARRIVAL ≈ FEB 2029", 20, win(t, 243.0, 254.6))
        T.put((1014, 902), "JAPAN'S DESTINY+ IS ALSO PLANNED TO FLY PAST", 20, win(t, 250.2, 254.6), col=DIM)
    T.put((60, 1030), "SPACECRAFT MODELS SIMPLIFIED  ·  NOT TO SCALE WITH THE ASTEROID  ·  PLANS AS OF LATE 2026", 15, win(t, 223.0, 254.6) * 0.7, col=DIM)
    return T.add_to(bloom(img))


def shot_hypo(t, lt):
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.5, 0.5, 0.7])), (W / 2) / math.tan(math.radians(26)), gain=0.7).copy()
        draw_earth(im, 1010, 1640, 1150, art_M(14, 34, roll=8), norm([-0.55, 0.62, 0.56]), night_gain=1.0)
        return im
    base = cached("hypo_bg", bg)
    Mx = np.float32([[1, 0, -lt * 1.6 + 18], [0, 1, lt * 0.5 - 4]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img[:, :] *= 0.86
    T = Text()
    a = win(t, 255.2, 278.2, 0.8, 0.8)
    T.put((W / 2, 70), "HYPOTHETICAL  ·  THIS WILL NOT HAPPEN", 30, a, col=RED, anchor="c", track=7, wt="R")
    T.line((W / 2 - 330, 122), (W / 2 + 330, 122), a * 0.6, col=RED)
    x0, y0 = 200, 250
    a1 = win(t, 261.0, 278.2)
    T.put((x0, y0), "ENERGY OF AN IMPACT BY AN ASTEROID THIS SIZE (ESTIMATE)", 21, a1, col=DIM)
    T.put((x0 - 4, y0 + 34), "≈ 1,000 MEGATONS", 84, a1, wt="T", track=5, col=YEL)
    T.put((x0, y0 + 142), "OF TNT", 24, a1)
    full = 1200.0; wbar = 1300
    g1 = ss(264.5, 267.5, t); a2 = win(t, 264.0, 278.2)
    by = y0 + 218
    T.d.rectangle((x0, by, x0 + wbar * g1 * a2 + 1, by + 5), fill=YEL + (int(235 * a2),)); T.used = True
    T.put((x0, by + 16), "APOPHIS-SIZE IMPACT  ·  ROUGHLY 1,000–1,200 MT", 18, a2, col=DIM)
    a3 = win(t, 266.8, 278.2)
    T.d.rectangle((x0, by + 62, x0 + wbar * 50 / full * a3, by + 67), fill=TXT + (int(235 * a3),))
    T.put((x0, by + 78), "LARGEST NUCLEAR TEST EVER (1961)  ·  50 MT", 18, a3, col=DIM)
    caption(T, ["ENOUGH TO DEVASTATE A WHOLE REGION", "NOT ENOUGH TO END CIVILISATION"], t, 272.4, 278.2, x=x0, y=by + 150, size=27, stagger=1.9)
    return T.add_to(bloom(img, 0.85, 0.35))


def shot_endpass(t, lt):
    cam = Cam(TL.lonlat(-12, 16) * 150000.0, (0, 0, 2000.0), 26.0)
    tau = lerp(-2.6, 0.55, ss(277.0, 292.5, t) * 0.35 + 0.65 * (lt / 13.0))
    gm = TL.GMST0 + TL.OMEGA * tau
    img = sky("endpass", cam.R, 26.0, gain=1.3, mw_gain=1.8).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    draw_earth(img, ex, ey, eR, body_M(cam.R, gm), cam.R @ TL.SUN, t=t, night_gain=1.5)
    ring_phys(img, cam, gm, t, gain=0.9)
    path_phys(img, cam, tau, 6.0, AMB, gain=0.14, dash=3, n=260)
    path_phys(img, cam, tau - 3.5, tau, AMB, gain=0.8, n=200, fade_tail=True)
    x, y, vis = apo_point(img, cam, tau, amp=1.9, sig=1.7, streak=9)
    T = Text()
    tag(T, x, y, "APOPHIS", win(t, 278.8, 291.6), col=AMB, size=20, dx=30, dy=-40)
    T.put((120, 96), _clock(tau), 27, win(t, 278.8, 291.4))
    T.put((120, 840), "PREDICTED CLOSEST APPROACH", 21, win(t, 284.0, 291.4), col=DIM)
    T.put((116, 868), "21:46 UTC", 76, win(t, 284.4, 291.4, 0.9, 0.7), wt="T", track=6, col=YEL)
    T.put((120, 966), "KNOWN YEARS IN ADVANCE  ·  UNCERTAINTY OF ONLY A FEW KILOMETRES", 20, win(t, 286.6, 291.4), col=DIM)
    T.put((W - 60, 1030), "TRUE SCALE  ·  PATH APPROXIMATE  ·  TIME-LAPSE", 15, win(t, 278.8, 291.2) * 0.7, col=DIM, anchor="r")
    return T.add_to(bloom(img))


def shot_rock(t, lt):
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.9, 0.1, 0.42])), (W / 2) / math.tan(math.radians(27)), gain=0.85, mw_gain=1.5).copy()
        draw_earth(im, 420, 300, 105, art_M(-60, 30, roll=18), SUN_AST, night_gain=1.4)
        return im
    img = cached("rock_bg", bg).copy()
    ring_art(img, 420, 300, 105, art_M(-60, 30, roll=18), t, gain=0.8, line=0.2)
    u = lt / 5.5
    put_sprite(img, ast_at(330 + lt * 24), lerp(1090, 1180, u), lerp(600, 560, u), lerp(0.92, 0.80, u), angle=-20 + lt * 0.4, gain=1.05)
    T = Text()
    T.put((120, 930), "A ROCK, ON A PATH WE WORKED OUT", 30, win(t, 299.0, 303.8, 0.8, 0.6))
    return T.add_to(bloom(img))


FUNCS = {"hook": shot_hook, "disc": shot_disc, "scare": shot_scare, "name": shot_name, "relief": shot_relief, "size": shot_size,
         "geo": shot_geo, "moon": shot_moon, "pass": shot_pass, "night": shot_night, "ground1": lambda t, lt: shot_ground(t, lt, 1),
         "orbit": shot_orbit, "tides": shot_tides, "miss": shot_miss, "hypo": shot_hypo, "endpass": shot_endpass,
         "ground2": lambda t, lt: shot_ground(t, lt, 2), "rock": shot_rock, "ground3": lambda t, lt: shot_ground(t, lt, 3)}


def frame(t):
    out = None
    for i, (name, a, b) in enumerate(TL.SHOTS):
        fa = a - TL.XF / 2 if i > 0 else a; fb = b + TL.XF / 2 if i < len(TL.SHOTS) - 1 else b
        if not (fa <= t < fb): continue
        w = 1.0
        if i > 0 and t < a + TL.XF / 2: w = ss(a - TL.XF / 2, a + TL.XF / 2, t)
        if i < len(TL.SHOTS) - 1 and t > b - TL.XF / 2: w = 1 - ss(b - TL.XF / 2, b + TL.XF / 2, t)
        if w <= 0.001: continue
        im = FUNCS[name](t, t - a)
        out = im * w if out is None else out + im * w
    g = ss(0.0, 0.9, t) * (1 - ss(TL.DUR - 2.6, TL.DUR - 0.4, t))
    return np.clip(out * g, 0, 1)


def main():
    if sys.argv[1] == "--png":
        os.makedirs(SCR + "/chk", exist_ok=True)
        for s in sys.argv[2:]:
            t0 = time.time(); im = frame(float(s))
            cv2.imwrite(f"{SCR}/chk/f_{float(s):06.1f}.jpg", to8(im)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 93]); print(s, round(time.time() - t0, 2), "s", flush=True)
        return
    t0, t1 = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    os.makedirs(SCR + "/seg", exist_ok=True); out = f"{SCR}/seg/seg_{f0:05d}.mp4"
    if os.path.exists(out): print("exists", out); return
    tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p", "-threads", "2", tmp], stdin=subprocess.PIPE)
    st = time.time()
    for f in range(f0, f1):
        p.stdin.write(to8(frame(f / FPS)).tobytes())
        if (f - f0) % 48 == 0: print(f"frame {f} ({f / FPS:.1f}s) {(time.time() - st) / max(1, f - f0):.2f} s/frame", flush=True)
    p.stdin.close(); p.wait(); os.replace(tmp, out); print("done", out, round(time.time() - st), "s")


if __name__ == "__main__":
    main()
