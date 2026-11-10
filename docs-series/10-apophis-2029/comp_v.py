"""FRIDAY THE 13TH, 2029 - 9:16 recomposition (1080x1920). Same shots, timings, renderers and assets as comp.py, but every
shot is re-framed for a vertical frame (hero object in the central column, cameras re-aimed or rolled where a crop would
lose the subject) and all type is re-laid: centred, larger, stacked, inside the safe area (clear of the top 12 % and the
bottom 20 %, where phone UI sits).

Usage: APO_VERT=1 python3 comp_v.py T0 T1            -> $SCR/seg_v/seg_<frame0>.mp4
       APO_VERT=1 python3 comp_v.py --png t1 t2 ...  -> $SCR/chk/v_<t>.jpg
"""
import os, sys, math, subprocess, time
os.environ["APO_VERT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import *
import timeline as TL
import comp as C
import ground_v
from ground_v import cput
from comp import TXT, DIM, AMB, COOL, RED, YEL, SUN_AST, cached, body_M, art_M, tag, ring_art, ring_phys, path_phys, apo_point

assert (W, H) == (1080, 1920)
CX = W / 2
TOP = 250            # first line of the safe area (top 12 % = 230 px)
BOT = 1536           # last line of the safe area (bottom 20 %)


def sky(key, R, fov, **kw):
    return cached(("vsky", key), lambda: render_sky(R, FL(fov), **kw))


def foot(T, y, s, a):
    """small-print scale note, placed directly under the header"""
    return cput(T, y, s, 16, a * 0.7, col=DIM, maxw=900)


# ================================================================================================= shots
def shot_hook(t, lt):
    EX, EY, ER = 740, 560, 165
    M = art_M(-18, 33, roll=-24)
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.35, 0.90, 0.25])), FL(54), gain=0.9).copy()
        draw_earth(im, EX, EY, ER, M, SUN_AST, night_gain=1.4)
        return im
    img = cached("vhook_bg", bg).copy()
    ring_art(img, EX, EY, ER, M, t, gain=1.0, line=0.26)
    best = None
    for azd in range(-180, 180, 6):                           # a pass point (5.96 Earth radii out) that lands inside the frame
        az = math.radians(azd); pb = np.array([math.cos(az), math.sin(az), 0.28]) * (TL.RP / TL.RE) * ER
        pc = M.T @ pb; mx, my = EX + pc[0], EY - pc[1]
        if 140 < mx < 960 and 330 < my < 800 and pc[2] > 0 and (best is None or mx < best[0]): best = (mx, my)
    mx, my = best
    T = Text()
    al = win(t, 1.6, 16.8, 1.0, 1.0)
    if al > 0:
        L = Lines(); hy_ = math.hypot(mx - EX, my - EY)
        L.seg(EX + (mx - EX) * (ER + 5) / hy_, EY + (my - EY) * (ER + 5) / hy_, mx, my)
        L.add_to(img, np.array(YEL) / 255, gain=0.75 * al, glow=0.6)
        add_glint(img, mx, my, 1.3 * al, (1.0, 0.86, 0.6), sig=1.6, streak=6)
    u = t / 22.4
    put_sprite(img, ast_at(t * 24), lerp(500, 560, u), lerp(1010, 960, u), lerp(0.62, 0.57, u), angle=-8 + t * 0.25, gain=1.0, alpha=1 - ss(17.4, 19.4, t))
    y = cput(T, TOP, "FRIDAY · 13 APRIL 2029", 34, win(t, 0.2, 17.2, 0.6))
    foot(T, y + 6, "ASTEROID 99942 APOPHIS · ARTIST'S MODEL · FOREGROUND NOT TO SCALE WITH THE EARTH", win(t, 1.5, 17.0))
    a1 = win(t, 1.3, 9.6, 0.8, 0.7)
    cput(T, 1262, "32,000 KM", 138, a1, col=YEL, wt="XL", track=6)
    cput(T, 1436, "ABOVE THE SURFACE · INSIDE THE RING OF GEOSTATIONARY SATELLITES", 28, win(t, 2.4, 9.6))
    a2 = win(t, 10.3, 17.2, 0.9, 0.7)
    cput(T, 1272, "IT WILL MISS.", 112, a2, wt="T", track=8)
    cput(T, 1436, "IMPACT RULED OUT FOR AT LEAST 100 YEARS", 28, win(t, 11.6, 17.2))
    tag(T, mx, my, "CLOSEST APPROACH", win(t, 2.6, 16.8), col=YEL, size=19, dx=30, dy=-40)
    a3 = win(t, 18.0, 22.4, 1.1, 0.6)
    y = cput(T, 1020, "FRIDAY THE 13TH, 2029", 96, a3, wt="T", track=18, gap=1.25)
    cput(T, y + 30, "AN ASTEROID WILL PASS CLOSER THAN OUR SATELLITES", 28, win(t, 18.9, 22.4, 1.0, 0.6), col=AMB)
    return T.add_to(bloom(img))


def shot_disc(t, lt):
    Rs = look_at((0, 0, 0), norm([0.47, -0.61, 0.64]))
    base = sky("disc", Rs, 34, gain=1.35, mw_gain=2.3, mag_lim=11.5)
    dx = lt * 1.2; Mx = np.float32([[1.03, 0, -dx - 16], [0, 1.03, -30]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    T = Text()
    def reticle(px, py, a):
        add_glint(img, px, py, 1.0 * a, (1.0, 0.9, 0.75), sig=1.2)
        L = Lines(); L.circle(px, py, 30)
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)): L.seg(px + sx * 40, py + sy * 40, px + sx * 70, py + sy * 70)
        L.add_to(img, np.array(AMB) / 255, gain=0.8 * a, glow=0.5)
    a1 = win(t, 24.2, 32.4, 1.0, 1.6)
    px = 660 - (t - 24) * 7 - dx; py = 720 + (t - 24) * 5
    if a1 > 0:
        reticle(px, py, a1); tag(T, px + 22, py - 22, "2004 MN4", a1, col=AMB, size=22)
    y = cput(T, 1240, "19 JUNE 2004 · KITT PEAK, ARIZONA", 30, win(t, 23.6, 33.2))
    y = cput(T, y + 8, "ROY TUCKER · DAVID THOLEN · FABRIZIO BERNARDI", 26, win(t, 24.5, 33.2))
    cput(T, y + 14, "OBSERVED FOR TWO NIGHTS, THEN LOST", 24, win(t, 29.6, 33.2), col=DIM)
    a2 = win(t, 34.2, 39.8, 0.9, 0.8)
    qx = 470 - (t - 34) * 9; qy = 1000 - (t - 34) * 6
    if a2 > 0: reticle(qx, qy, a2)
    y = cput(T, 1240, "18 DECEMBER 2004 · FOUND AGAIN", 30, win(t, 34.2, 39.8))
    cput(T, y + 8, "SIDING SPRING, AUSTRALIA", 26, win(t, 35.0, 39.8))
    foot(T, TOP, "ILLUSTRATION · REAL STAR POSITIONS, NOT THE ACTUAL DISCOVERY FIELD", win(t, 23.4, 39.4))
    return T.add_to(bloom(img, 0.8, 0.4))


def _band_cam():
    n = np.cross(TL.P_HAT, TL.Q_HAT); pp = np.cross(n, TL.P_HAT); th = math.radians(68)
    for sgn in (1, -1):
        c = Cam(n * 2.2e6, 0.5 * TL.RP * TL.P_HAT, 2.66, up=math.sin(th) * TL.P_HAT + sgn * math.cos(th) * pp)
        x, y, _ = c.proj(np.array([[0, 0, 0], TL.RP * TL.P_HAT]))
        if x[1] > x[0] and y[1] < y[0]: break
    c.ox, c.oy = -6.0, -281.0
    return c


def _band_shot(t):
    cam = _band_cam()
    def bg():
        im = render_sky(cam.R, FL(24), gain=0.8, mw_gain=1.4).copy()
        ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
        draw_earth(im, ex, ey, eR, body_M(cam.R, TL.GMST0), cam.R @ TL.SUN, night_gain=1.3)
        return im
    img = cached("vband_bg", bg).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    px, py, _ = cam.proj(TL.apophis(0.0)[None]); px, py = float(px[0]), float(py[0])
    d = np.array([px - ex, py - ey]); dist = np.linalg.norm(d); d /= dist; nrm = np.array([-d[1], d[0]])
    L, frac = C._band_state(t)
    c = np.array([ex, ey]) + d * dist * frac
    wv = max(1.2, min(7.0, L * 0.012))
    pts = c[None] + C.BAND_U[:, None] * L * d[None] + C.BAND_V[:, None] * wv * nrm[None]
    lay = np.zeros((H, W), F32)
    ok = (pts[:, 0] > 1) & (pts[:, 0] < W - 2) & (pts[:, 1] > 1) & (pts[:, 1] < H - 2)
    np.add.at(lay, (pts[ok, 1].astype(int), pts[ok, 0].astype(int)), C.BAND_B[ok])
    dens = min(3.0, 760.0 / max(L, 30)) ** 0.55
    lay = cv2.GaussianBlur(lay, (0, 0), 1.0) * 1.5 + cv2.GaussianBlur(lay, (0, 0), 5) * 0.9 + cv2.GaussianBlur(lay, (0, 0), 16) * 0.5
    img += lay[..., None] * np.array([1.0, 0.72, 0.36], F32) * (1.1 / dens ** 0.2) * (1 - ss(89.5, 91.5, t)) * ss(40.4, 42.5, t)
    return img, cam, (ex, ey, eR), (px, py), d, dist, c, L


def shot_scare(t, lt):
    img, cam, (ex, ey, eR), (px, py), d, dist, c, L = _band_shot(t)
    T = Text()
    y = cput(T, TOP, "LATE DECEMBER 2004", 34, win(t, 40.0, 58.4))
    foot(T, y + 6, "SCHEMATIC · EARTH AND DISTANCES TO SCALE", win(t, 40.4, 58.2))
    tag(T, ex + d[0] * 300, ey + d[1] * 300, "POSSIBLE POSITIONS", win(t, 41.5, 58.2), col=AMB, size=21, dx=40, dy=30)
    tag(T, ex + d[0] * 300 + 58, ey + d[1] * 300 + 58, "ON 13 APRIL 2029", win(t, 41.5, 58.2), col=AMB, size=21, dx=0.01, dy=0.01)
    tag(T, ex - eR * 0.7, ey - eR * 0.7, "EARTH", win(t, 41.0, 58.2), col=COOL, size=21, dx=-40, dy=-44, anchor="r")
    a = win(t, 42.2, 58.4, 1.0, 0.7)
    p = lerp(0.3, 2.7, ss(42.2, 47.2, t))
    cput(T, 1164, "CHANCE OF IMPACT ON 13 APRIL 2029", 24, a, col=DIM)
    cput(T, 1196, f"{p:.1f} %", 128, a, col=YEL, wt="T", track=4)
    cput(T, 1344, "1 IN 37 · PEAK ESTIMATE, 27 DEC 2004", 26, win(t, 50.6, 58.4))
    a = win(t, 52.6, 58.4, 0.9, 0.7)
    cw = 78; x0 = CX - 11 * cw / 2 + 3; y0 = 1440
    cput(T, y0 - 44, "TORINO IMPACT HAZARD SCALE", 21, a, col=DIM)
    for i in range(11):
        on = (i == 4); col = C.TORINO[i]
        T.d.rectangle((x0 + i * cw, y0, x0 + i * cw + cw - 6, y0 + (18 if on else 7)), fill=col + (int(255 * a * (1.0 if on else 0.55)),)); T.used = True
        T.put((x0 + i * cw + (cw - 6) / 2, y0 + 26), str(i), 20 if not on else 26, a * (1 if on else 0.6), anchor="c", col=TXT if not on else YEL, track=0)
    cput(T, y0 + 66, "LEVEL 4 · THE HIGHEST RATING EVER GIVEN", 23, win(t, 54.0, 58.4), col=YEL)
    return T.add_to(bloom(img))


def shot_relief(t, lt):
    img, cam, (ex, ey, eR), (px, py), d, dist, c, L = _band_shot(t)
    T = Text()
    ar = ss(89.5, 92.0, t)
    if ar > 0:
        path_phys(img, cam, -9, 9, AMB, gain=0.55 * ar, n=300)
        add_glint(img, px, py, 1.5 * ar, (1.0, 0.86, 0.62), sig=1.6, streak=7)
        tag(T, px, py, "APOPHIS · 13 APRIL 2029", win(t, 90.5, 94.8), col=AMB, size=21, dx=-34, dy=44, anchor="r")
        tag(T, (ex + px) / 2, (ey + py) / 2, "≈ 38,000 KM FROM EARTH'S CENTRE", win(t, 91.2, 94.8), col=DIM, size=18, dx=30, dy=40)
        Ls = Lines(); Ls.seg(ex + d[0] * (eR + 6), ey + d[1] * (eR + 6), px - d[0] * 8, py - d[1] * 8); Ls.add_to(img, (0.6, 0.65, 0.72), gain=0.35 * ar, glow=0.3)
    tag(T, ex - eR * 0.7, ey - eR * 0.7, "EARTH", win(t, 64.4, 94.8), col=COOL, size=21, dx=-40, dy=-44, anchor="r")
    tag(T, c[0], c[1], "POSSIBLE POSITIONS", win(t, 65.0, 89.5), col=AMB, size=21, dx=40, dy=30)
    y = cput(T, TOP, "EVERY OBSERVATION NARROWS THE RANGE", 32, win(t, 66.0, 80.8))
    foot(T, y + 6, "SCHEMATIC · EARTH AND DISTANCES TO SCALE", win(t, 66.0, 80.6))
    y = cput(T, TOP, "MARCH 2021 · RADAR", 34, win(t, 82.6, 94.6))
    foot(T, y + 6, "SCHEMATIC · EARTH AND DISTANCES TO SCALE", win(t, 82.6, 89.6))
    p = 2.7 * (1 - ss(73.2, 75.0, t))
    a = win(t, 64.2, 80.8, 0.4, 0.8)
    cput(T, 1164, "CHANCE OF IMPACT ON 13 APRIL 2029", 24, a, col=DIM)
    cput(T, 1196, f"{p:.1f} %" if p > 0.05 else "0", 128, a, col=YEL if p > 0.05 else TXT, wt="T", track=4)
    y = cput(T, 1350, "27 DEC 2004 · OVERLOOKED IMAGES FROM MARCH 2004 EXTEND THE ORBIT ARC", 22, win(t, 72.6, 80.8), col=DIM)
    cput(T, y + 16, "2029 IMPACT RULED OUT", 34, win(t, 76.6, 80.8))
    y = cput(T, 1180, "2036 · RULED OUT IN 2013", 28, win(t, 82.0, 94.6), col=DIM)
    y = cput(T, y + 4, "2068 · RULED OUT IN MARCH 2021", 28, win(t, 83.3, 94.6), col=DIM)
    y = cput(T, y + 22, "GOLDSTONE + GREEN BANK RADAR", 24, win(t, 85.6, 94.6), col=DIM)
    cput(T, y + 26, "NO IMPACT RISK FOR AT LEAST 100 YEARS", 44, win(t, 89.6, 94.6), gap=1.3)
    return T.add_to(bloom(img))


def _ast_bg(key, d, mw=1.6, gain=0.85):
    return sky(key, look_at((0, 0, 0), norm(d)), 30, gain=gain, mw_gain=mw)


def shot_name(t, lt):
    img = _ast_bg("name", [0.6, -0.55, -0.4]).copy()
    u = lt / 6.0
    put_sprite(img, ast_at(160 + lt * 24), lerp(560, 540, u), lerp(760, 780, u), lerp(0.88, 0.94, u), angle=56, gain=1.05)
    T = Text()
    y = cput(T, 1330, "99942 APOPHIS", 88, win(t, 59.2, 64.4, 0.9, 0.6), wt="T", track=12)
    cput(T, y + 6, "NAMED IN 2005 FOR THE EGYPTIAN SERPENT OF CHAOS", 26, win(t, 60.2, 64.4, 0.9, 0.6), col=AMB)
    return T.add_to(bloom(img))


def shot_size(t, lt):
    img = _ast_bg("size", [-0.3, 0.2, -0.93], mw=1.2).copy()
    z = ss(109.8, 113.2, t)
    sc = lerp(0.62, 0.50, z); mpp = 0.4 / sc
    ax = 540 - lt * 0.8 * (1 - z) + 8; ay = lerp(680, 560, z)
    put_sprite(img, ast_at(lt * 24), ax, ay, sc, gain=1.05)
    T = Text()
    at_ = ss(110.6, 113.0, t)
    if at_ > 0:
        tw = cached("tower", C._tower); ts = 0.2 / mpp
        base_y = 1392; tcx = 560
        tcy = base_y - (331 / 2) / mpp + (2000 / 2 - (209 + 1654 / 2)) * ts
        put_sprite(img, tw, tcx, tcy, ts, gain=1.25, alpha=at_)
        ytop = base_y - 330 / mpp; bx = tcx - 190
        T.line((bx, ytop), (bx, base_y), at_ * 0.8); T.line((bx - 12, ytop), (bx + 12, ytop), at_ * 0.8); T.line((bx - 12, base_y), (bx + 12, base_y), at_ * 0.8)
        T.put((bx - 20, (ytop + base_y) / 2 - 14), "330 M", 28, at_, anchor="r")
        cput(T, 830, "APOPHIS · ≈ 340 M MEAN DIAMETER", 25, at_, col=AMB)
        cput(T, base_y + 22, "EIFFEL TOWER", 25, at_)
        x0 = CX - 50 / mpp; ys = base_y + 92
        T.line((x0, ys), (x0 + 100 / mpp, ys), at_ * 0.9); T.line((x0, ys - 6), (x0, ys + 6), at_ * 0.9); T.line((x0 + 100 / mpp, ys - 6), (x0 + 100 / mpp, ys + 6), at_ * 0.9)
        cput(T, ys + 12, "100 M · SAME SCALE", 19, at_, col=DIM)
    b = 110.0
    cput(T, 1090, "≈ 340 M", 116, win(t, 97.6, b, 0.9, 0.7), wt="T", track=6, col=YEL)
    y = cput(T, 1232, "MEAN DIAMETER (RADAR: 340 ± 40 M)", 23, win(t, 98.2, b), col=DIM)
    y = cput(T, y + 18, "STONY · ELONGATED", 28, win(t, 100.6, b))
    y = cput(T, y + 4, "POSSIBLY TWO LOBES IN CONTACT", 28, win(t, 102.6, b))
    cput(T, y + 4, "TUMBLING · ≈ 30.6 HOURS PER TURN", 28, win(t, 105.4, b))
    foot(T, TOP, "ARTIST'S MODEL GUIDED BY RADAR · THE REAL SURFACE HAS NEVER BEEN SEEN UP CLOSE", win(t, 95.0, 116.6))
    return T.add_to(bloom(img))


# ---- true-scale Earth system: the ring's long axis is turned upright for the vertical frame ---------------------------------
GEO_FOV = 30.0
GEO_ROLL = math.radians(80)
D_NEAR, D_FAR = 62000.0, 240000.0


def _geo_dir():
    h = rot_axis((0, 0, 1), math.radians(-22)) @ norm(np.array([TL.P_HAT[0], TL.P_HAT[1], 0.0])); e = math.radians(36)
    return math.cos(e) * h + math.sin(e) * np.array([0, 0, 1.0])


def _geo_cam(dist):
    c = Cam(_geo_dir() * dist, (0, 0, 0), GEO_FOV, roll=GEO_ROLL); c.oy = -60.0
    return c


def _sys_frame(cam, gm, t, sky_key, ring=1.0, night=1.3, sky_gain=1.25):
    img = sky(sky_key, cam.R, GEO_FOV, gain=sky_gain, mw_gain=1.8).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    draw_earth(img, ex, ey, eR, body_M(cam.R, gm), cam.R @ TL.SUN, t=t, night_gain=night)
    if ring > 0: ring_phys(img, cam, gm, t, gain=ring)
    return img, (ex, ey, eR)


def _ring_pt(cam, key):
    ga = np.linspace(0, 2 * np.pi, 120); gx, gy, _ = cam.proj(np.stack([TL.R_GEO * np.cos(ga), TL.R_GEO * np.sin(ga), 0 * ga], 1))
    gi = int(np.argmax(key(gx, gy))); return float(gx[gi]), float(gy[gi])


def shot_geo(t, lt):
    u = ss(121.0, 128.5, t)
    cam = _geo_cam(D_NEAR * (D_FAR / D_NEAR) ** u)
    img, (ex, ey, eR) = _sys_frame(cam, TL.GMST0 - TL.OMEGA * 6, t, "geo", ring=ss(122.5, 126.0, t))
    T = Text()
    cput(T, 1400, "EARTH · 12,742 KM ACROSS", 28, win(t, 119.4, 124.0), col=COOL)
    gx, gy = _ring_pt(cam, lambda x, y: -x - 0.4 * y)
    tag(T, gx, gy, "GEOSTATIONARY RING", win(t, 125.4, 132.6), col=COOL, size=22, dx=30, dy=-46)
    y = cput(T, 1290, "35,786 KM", 96, win(t, 126.0, 132.6, 0.9, 0.7), wt="T", track=6, col=COOL)
    cput(T, y + 4, "ABOVE THE EQUATOR · TELEVISION, WEATHER, COMMUNICATIONS", 24, win(t, 127.0, 132.6), col=DIM)
    foot(T, TOP, "TRUE SCALE · EACH GLINT STANDS FOR A SATELLITE (POSITIONS ILLUSTRATIVE)", win(t, 124.0, 132.4))
    return T.add_to(bloom(img))


def shot_moon(t, lt):
    md = norm(0.94 * TL.SUN + 0.30 * norm(np.cross([0, 0, 1], TL.SUN)) + np.array([0, 0, 0.09]))
    mpos = md * TL.R_MOON
    c0 = Cam(mpos + md * 30000.0, (0, 0, 0), 19.0, zoom=0.8)
    eye = mpos + md * 30000.0 + c0.R[0] * (1500 - lt * 40) + c0.R[1] * 5300
    cam = Cam(eye, (0, 0, 0), 19.0, zoom=0.8); cam.ox, cam.oy = 0.0, -390.0
    img = sky("moon", cam.R, 19.0 / 0.8, gain=1.0, mw_gain=1.6).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    draw_earth(img, ex, ey, eR, body_M(cam.R, TL.GMST0), cam.R @ TL.SUN, night_gain=1.2)
    ring_phys(img, cam, TL.GMST0, t, gain=0.8, line=0.2)
    mx, my, mR, _ = cam.sphere(mpos, 1737.4)
    draw_moon(img, mx, my, mR, rot_axis((0, 0, 1), 2.4) @ rot_axis((1, 0, 0), 1.2) @ cam.R.T, norm(np.array([0.80, 0.45, 0.40])), exposure=0.8)
    T = Text()
    tag(T, ex, ey - eR - 6, "EARTH", win(t, 132.9, 137.6), col=COOL, size=22, dx=30, dy=-46)
    y = cput(T, 770, "384,400 KM", 104, win(t, 133.4, 137.6, 0.8, 0.6), wt="T", track=6)
    cput(T, y + 4, "THE MOON'S AVERAGE DISTANCE", 26, win(t, 134.0, 137.6), col=DIM)
    foot(T, TOP, "TRUE SIZES AND DISTANCES · MOON POSITION AND LIGHTING ILLUSTRATIVE", win(t, 132.8, 137.4))
    return T.add_to(bloom(img))


def shot_pass(t, lt):
    tau = C._tau_pass(t); gm = TL.GMST0 + TL.OMEGA * tau
    cam = _geo_cam(D_FAR)
    img, (ex, ey, eR) = _sys_frame(cam, gm, t, "geo")
    path_phys(img, cam, tau, 9.0, AMB, gain=0.16, dash=3, n=300)
    path_phys(img, cam, max(-9.0, tau - 4.5), tau, AMB, gain=0.85, n=220, fade_tail=True)
    x, y, vis = apo_point(img, cam, tau, amp=1.9, sig=1.7, streak=8)
    pa = TL.apophis(tau); fx, fy, _ = cam.proj(np.array([[pa[0], pa[1], 0.0]]))
    Ls = Lines(); Ls.poly(np.linspace(x, float(fx[0]), 40), np.linspace(y, float(fy[0]), 40), dash=2); Ls.circle(float(fx[0]), float(fy[0]), 3)
    Ls.add_to(img, np.array(AMB) / 255, gain=0.45, glow=0.3)
    T = Text()
    if 20 < x < W - 20 and 20 < y < H: tag(T, x, y, "APOPHIS", win(t, 138.4, 160.4), col=AMB, size=22, dx=28, dy=-38, anchor="l" if x < 760 else "r")
    r = np.linalg.norm(TL.apophis(tau)); alt = r - 6378
    yh = cput(T, TOP, C._clock(tau), 32, win(t, 137.6, 160.2))
    yh = foot(T, yh + 6, "TRUE SCALE · PATH RECONSTRUCTED FROM PUBLISHED FLYBY VALUES (APPROXIMATE) · TIME-LAPSE", win(t, 138.0, 160.0))
    cput(T, yh + 22, "IT PASSES NORTH OF THE RING'S PLANE, NOT THROUGH THE SATELLITES", 21, win(t, 147.6, 160.2), col=DIM)
    a = win(t, 139.0, 152.0)
    cput(T, 1262, "HEIGHT ABOVE THE SURFACE", 22, a, col=DIM)
    cput(T, 1290, f"{int(round(alt, -2)):,} KM", 92, a, wt="T", track=5, col=YEL)
    cput(T, 1408, f"SPEED  {TL.speed(tau):.1f} KM/S", 34, a)
    cx_, cy_, _ = cam.proj(TL.apophis(0.0)[None]); cx_, cy_ = float(cx_[0]), float(cy_[0])
    ac = win(t, 149.2, 160.2)
    if ac > 0:
        Ls = Lines(); dd = np.array([cx_ - ex, cy_ - ey]); n_ = np.linalg.norm(dd); dd /= n_
        Ls.seg(ex + dd[0] * (eR + 4), ey + dd[1] * (eR + 4), cx_ - dd[0] * 6, cy_ - dd[1] * 6); Ls.add_to(img, np.array(YEL) / 255, gain=0.6 * ac, glow=0.5)
        T.put(((ex + cx_) / 2 + 16, (ey + cy_) / 2 + 10), "≈ 32,000 KM", 24, ac, col=YEL)
    gx, gy = _ring_pt(cam, lambda x_, y_: -x_ - 0.4 * y_)
    tag(T, gx, gy, "GEOSTATIONARY RING", win(t, 143.0, 160.2), col=COOL, size=19, dx=30, dy=-46)
    cput(T, 1470, "CLOSER THAN THE SATELLITE RING · A TENTH OF THE WAY TO THE MOON", 22, win(t, 146.4, 152.0))
    y2 = cput(T, 1290, "THIS CLOSE, THIS LARGE:", 30, win(t, 152.8, 160.2))
    cput(T, y2 + 6, "ROUGHLY ONCE IN SEVERAL THOUSAND YEARS", 30, win(t, 153.5, 160.2))
    return T.add_to(bloom(img))


def shot_night(t, lt):
    cam = Cam(norm(TL.apophis(C.NIGHT_TAU)) * 64000.0, (0, 0, 0), 20.0, zoom=0.95); cam.oy = -70.0
    def bg():
        im = render_sky(cam.R, cam.f, gain=1.0).copy()
        ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
        draw_earth(im, ex, ey, eR, body_M(cam.R, TL.GMST0 + TL.OMEGA * C.NIGHT_TAU), cam.R @ TL.SUN, night_gain=1.5)
        return im
    base = cached("vnight_bg", bg)
    s = 1.0 + 0.05 * (lt / 15.0); Mx = np.float32([[s, 0, (1 - s) * 560], [0, s, (1 - s) * 700]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR)
    tau = lerp(-1.035, -0.80, (t - 160.2) / 14.8)
    def scr(q):
        x, y, _ = cam.proj(np.array([TL.apophis(q)])); return float(x[0]) * s + Mx[0, 2], float(y[0]) * s + Mx[1, 2]
    x, y = scr(tau)
    m = np.zeros((H, W), F32); prev = None
    for i in range(60):
        q = scr(tau - 0.05 * (1 - i / 59))
        if prev is not None: cv2.line(m, (int(prev[0]), int(prev[1])), (int(q[0]), int(q[1])), float((i / 59) ** 2), 1, cv2.LINE_AA)
        prev = q
    img += cv2.GaussianBlur(m, (0, 0), 1.2)[..., None] * np.array([1.0, 0.8, 0.5], F32) * 0.7
    add_glint(img, x, y, 2.0, (1.0, 0.88, 0.66), sig=1.9, streak=10); add_glint(img, x, y, 0.3, (1.0, 0.7, 0.4), sig=9)
    T = Text()
    tag(T, x, y, "APOPHIS", win(t, 160.8, 175.0), col=AMB, size=22, dx=34, dy=-30)
    yh = cput(T, TOP, "THE EVENING OF 13 APRIL 2029", 32, win(t, 160.6, 175.0))
    foot(T, yh + 6, "ABOUT AN HOUR BEFORE CLOSEST APPROACH · CITY LIGHTS: NASA · PATH APPROXIMATE · TIME-LAPSE", win(t, 160.6, 174.8))
    cput(T, 1236, "VISIBLE WITHOUT A TELESCOPE", 24, win(t, 162.6, 175.0), col=DIM)
    y2 = cput(T, 1276, "EUROPE · AFRICA · WESTERN ASIA", 52, win(t, 165.2, 175.0, 0.9, 0.7), wt="XL", track=7, gap=1.3)
    y2 = cput(T, y2 + 10, "ABOUT 2 BILLION PEOPLE", 38, win(t, 168.8, 175.0), col=YEL)
    cput(T, y2 + 6, "GIVEN A CLEAR, DARK SKY", 23, win(t, 170.6, 175.0), col=DIM)
    return T.add_to(bloom(img, 0.7, 0.5))


def shot_orbit(t, lt):
    cam = Cam(np.array([0.35, -2.9, 2.35]), (0.12, -0.05, 0), 40.0, roll=math.radians(90), zoom=0.80); cam.oy = -70.0
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.2, 0.9, -0.4])), cam.f * 0.9, gain=0.8, mw_gain=2.0).copy()
        sx, sy, _ = cam.proj(np.zeros((1, 3))); sx, sy = float(sx[0]), float(sy[0])
        yy, xx = np.mgrid[0:H, 0:W].astype(F32); r = np.hypot(xx - sx, yy - sy)
        glow = np.exp(-r / 16) * 3.0 + np.exp(-r / 70) * 0.55 + np.exp(-r / 300) * 0.14
        streak = np.exp(-np.abs(yy - sy) / 2.2) * np.exp(-np.abs(xx - sx) / 320) * 0.5
        im += (glow + streak)[..., None] * np.array([1.0, 0.86, 0.62], F32)
        return im
    img = cached("vorbit_bg", bg).copy()
    th_e = math.pi
    a0, e0, f0 = 0.9224, 0.1912, math.radians(-126.7); w0 = th_e - f0
    a1, e1, f1 = 1.103, 0.189, math.radians(-71.4); w1 = th_e - f1
    yr = lerp(-0.42, 0.50, ss(195.2, 210.2, t) * 0.5 + 0.5 * (lt / 16.0))
    k_after = ss(200.6, 203.0, t)
    def draw(P, col, gain, dash=None):
        x, y, _ = cam.proj(P); L = Lines(); L.poly(x, y, dash=dash); L.add_to(img, np.array(col) / 255, gain=gain, glow=0.7)
    draw(C._ellipse(0.723, 0.007, 0), DIM, 0.10); draw(C._ellipse(1.524, 0.093, 5.0), DIM, 0.09)
    draw(C._ellipse(1.0, 0.0167, 1.8), COOL, 0.55)
    draw(C._ellipse(a0, e0, w0), AMB, lerp(0.7, 0.28, k_after), dash=None if k_after < 0.5 else 4)
    if k_after > 0: draw(C._ellipse(a1, e1, w1), (255, 244, 225), 0.8 * k_after)
    pe = C._kepler_pos(1.0, 0.0167, 1.8, th_e - 1.8, yr)
    pa = C._kepler_pos(a0, e0, w0, f0, yr) if yr < 0 else C._kepler_pos(a1, e1, w1, f1, yr)
    xe, ye, _ = cam.proj(pe[None]); xa, ya, _ = cam.proj(pa[None]); xe, ye, xa, ya = float(xe[0]), float(ye[0]), float(xa[0]), float(ya[0])
    add_glint(img, xe, ye, 1.6, (0.55, 0.78, 1.0), sig=2.2, streak=5)
    add_glint(img, xa, ya, 1.3, (1.0, 0.86, 0.62), sig=1.6, streak=5)
    fl = math.exp(-(yr / 0.012) ** 2)
    if fl > 0.02: add_glint(img, xe, ye, 2.0 * fl, (1, 1, 1), sig=5, streak=22)
    T = Text()
    tag(T, xe, ye, "EARTH", win(t, 195.0, 210.4), col=COOL, size=21, dx=-30, dy=40, anchor="r" if xe > 200 else "l")
    tag(T, xa, ya, "APOPHIS", win(t, 195.0, 210.4), col=AMB, size=21, dx=28, dy=-36, anchor="l" if xa < 800 else "r")
    sx, sy, _ = cam.proj(np.zeros((1, 3))); T.put((float(sx[0]) + 34, float(sy[0]) + 22), "SUN", 19, win(t, 195.0, 210.4) * 0.8, col=DIM)
    yh = cput(T, TOP, "13 APRIL 2029 · EARTH'S GRAVITY BENDS THE PATH BY ROUGHLY 27°", 30, win(t, 197.6, 210.4))
    foot(T, yh + 6, "ORBIT SIZES AND SHAPES TO SCALE · ORIENTATION SCHEMATIC · SUN AND PLANETS NOT TO SCALE", win(t, 195.0, 210.2))
    a = win(t, 196.4, 210.4)
    cput(T, 1262, "BEFORE", 21, a, col=AMB); cput(T, 1292, "ATEN-CLASS ORBIT · ≈ 0.9 YEARS PER LAP", 27, a)
    a = win(t, 202.4, 210.4)
    cput(T, 1392, "AFTER", 21, a, col=(255, 244, 225)); cput(T, 1422, "APOLLO-CLASS ORBIT · ≈ 1.2 YEARS PER LAP", 27, a)
    return T.add_to(bloom(img, 0.8, 0.5))


def shot_tides(t, lt):
    EX, EY, ER = 520, 640, 335
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([-0.7, 0.3, 0.64])), FL(54), gain=0.8).copy()
        draw_earth(im, EX, EY, ER, art_M(-28, 20, roll=14), SUN_AST, night_gain=1.4)
        return im
    base = cached("vtides_bg", bg)
    Mx = np.float32([[1, 0, lt * 1.4 - 9], [0, 1, lt * 0.8 - 5]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    u = lt / 12.4
    put_sprite(img, ast_at(200 + lt * 24), lerp(640, 560, u), lerp(1130, 1100, u), lerp(0.54, 0.60, u), angle=-12 + lt * 0.5, gain=1.05)
    T = Text()
    yh = cput(T, TOP, "CLOSEST APPROACH · EARTH SPANS ABOUT 19° OF ITS SKY", 30, win(t, 211.0, 222.8))
    foot(T, yh + 6, "EARTH AT ITS TRUE APPARENT SIZE FROM 38,000 KM · ASTEROID ENLARGED", win(t, 210.8, 222.6))
    y = cput(T, 1400, "THE TUMBLE MAY SPEED UP OR SLOW DOWN", 25, win(t, 212.6, 222.8))
    y = cput(T, y + 6, "SMALL LANDSLIDES ARE POSSIBLE · NOT CERTAIN", 25, win(t, 214.8, 222.8))
    cput(T, y + 6, "IT PASSES TOO FAR OUT TO BE PULLED APART", 25, win(t, 217.0, 222.8))
    return T.add_to(bloom(img))


def shot_miss(t, lt):
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.1, -0.6, -0.79])), FL(52), gain=0.85, mw_gain=1.8).copy()
        draw_earth(im, 880, 400, 44, art_M(-40, 10, roll=-30), SUN_AST, night_gain=1.3)
        return im
    img = cached("vmiss_bg", bg).copy()
    k2 = ss(236.9, 237.9, t)
    if k2 < 1: put_sprite(img, ast_at(lt * 24), lerp(520, 500, lt / 15.0), lerp(1030, 1010, lt / 15.0), lerp(0.54, 0.57, lt / 15.0), angle=10 - lt * 0.2, gain=1.05, alpha=1 - k2)
    if k2 > 0:
        l2 = t - 237.0; put_sprite(img, ast_at(110 + l2 * 24), lerp(500, 540, l2 / 17.8), lerp(1000, 1030, l2 / 17.8), lerp(0.60, 0.56, l2 / 17.8), angle=-14 + l2 * 0.2, gain=1.05, alpha=k2)
    T = Text()
    foot(T, TOP, "SPACECRAFT MODELS SIMPLIFIED · NOT TO SCALE WITH THE ASTEROID · PLANS AS OF LATE 2026", win(t, 223.0, 254.6))
    a1 = win(t, 223.0, 237.6, 1.2, 1.0); a2 = win(t, 237.2, 254.8, 1.2, 0.8)
    if a1 > 0:
        cx_, cy_ = lerp(600, 560, (t - 223) / 14.6), lerp(580, 560, (t - 223) / 14.6)
        put_sprite(img, cached("apex", lambda: C._craft("apex")), cx_, cy_, 0.56, angle=-6 + (t - 223) * 0.3, gain=1.05, alpha=a1)
        y = cput(T, 1318, "OSIRIS-APEX", 70, a1, wt="T", track=10)
        y = cput(T, y + 2, "NASA · FORMERLY OSIRIS-REX", 23, win(t, 224.4, 237.4), col=AMB)
        y = cput(T, y + 4, "ALREADY EN ROUTE · RENDEZVOUS AFTER THE FLYBY", 23, win(t, 229.0, 237.4))
        cput(T, y + 4, "FUNDING IS REVIEWED YEAR BY YEAR", 23, win(t, 233.2, 237.4), col=DIM)
    if a2 > 0:
        cx_, cy_ = lerp(580, 540, (t - 237.2) / 17.6), lerp(540, 570, (t - 237.2) / 17.6)
        put_sprite(img, cached("ramses", lambda: C._craft("ramses")), cx_, cy_, 0.70, angle=8 - (t - 237.2) * 0.25, gain=1.05, alpha=a2)
        ac = win(t, 246.5, 254.8)
        for k, (ox, oy) in enumerate(((-200, 170), (-120, 225))):
            add_glint(img, cx_ + ox - (t - 246) * 3 * (k + 1), cy_ + oy + (t - 246) * 2, 0.9 * ac, (1.0, 0.95, 0.85), sig=1.4, streak=3)
        tag(T, cx_ - 120 - (t - 246) * 6, cy_ + 225 + (t - 246) * 2, "TWO CUBESATS", ac, col=DIM, size=18, dx=30, dy=36)
        y = cput(T, 1318, "RAMSES", 70, a2, wt="T", track=10)
        y = cput(T, y + 2, "ESA WITH JAPAN · APPROVED NOV 2025", 23, win(t, 238.4, 254.6), col=AMB)
        y = cput(T, y + 4, "LAUNCH SPRING 2028 · ARRIVAL ≈ FEB 2029", 23, win(t, 243.0, 254.6))
        cput(T, y + 4, "JAPAN'S DESTINY+ ALSO PLANS A FLY-PAST", 23, win(t, 250.2, 254.6), col=DIM)
    return T.add_to(bloom(img))


def shot_hypo(t, lt):
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.5, 0.5, 0.7])), FL(52), gain=0.7).copy()
        draw_earth(im, 560, 2440, 1150, art_M(16, -18, roll=6), norm([-0.55, 0.62, 0.56]), night_gain=1.0)
        return im
    base = cached("vhypo_bg", bg)
    Mx = np.float32([[1, 0, -lt * 1.2 + 14], [0, 1, lt * 0.5 - 4]])
    img = cv2.warpAffine(base, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img[:, :] *= 0.86
    T = Text()
    a = win(t, 255.2, 278.2, 0.8, 0.8)
    y = cput(T, TOP, "HYPOTHETICAL", 40, a, col=RED, track=9, wt="R")
    y = cput(T, y, "THIS WILL NOT HAPPEN", 34, a, col=RED, track=7, wt="R")
    T.line((CX - 300, y + 8), (CX + 300, y + 8), a * 0.6, col=RED)
    a1 = win(t, 261.0, 278.2)
    y = cput(T, 470, "ENERGY OF AN IMPACT BY AN ASTEROID THIS SIZE (ESTIMATE)", 23, a1, col=DIM)
    y = cput(T, y + 6, "≈ 1,000 MEGATONS", 92, a1, wt="T", track=4, col=YEL)
    y = cput(T, y - 4, "OF TNT", 28, a1)
    full = 1200.0; x0 = 90; wbar = 900; by = y + 50
    g1 = ss(264.5, 267.5, t); a2 = win(t, 264.0, 278.2)
    T.d.rectangle((x0, by, x0 + wbar * g1 * a2 + 1, by + 6), fill=YEL + (int(235 * a2),)); T.used = True
    T.put((x0, by + 18), "APOPHIS-SIZE IMPACT  ·  ROUGHLY 1,000–1,200 MT", 21, a2, col=DIM)
    a3 = win(t, 266.8, 278.2)
    T.d.rectangle((x0, by + 74, x0 + wbar * 50 / full * a3, by + 80), fill=TXT + (int(235 * a3),))
    T.put((x0, by + 92), "LARGEST NUCLEAR TEST EVER (1961)  ·  50 MT", 21, a3, col=DIM)
    y = cput(T, by + 190, "ENOUGH TO DEVASTATE A WHOLE REGION", 31, win(t, 272.4, 278.2))
    cput(T, y + 8, "NOT ENOUGH TO END CIVILISATION", 31, win(t, 274.3, 278.2))
    return T.add_to(bloom(img, 0.85, 0.35))


def shot_endpass(t, lt):
    cam = Cam(TL.lonlat(-12, 16) * 150000.0, (0, 0, 2000.0), 26.0, roll=math.radians(78), zoom=0.72); cam.oy = -80.0
    tau = lerp(-2.6, 0.55, ss(277.0, 292.5, t) * 0.35 + 0.65 * (lt / 13.0))
    gm = TL.GMST0 + TL.OMEGA * tau
    img = sky("endpass", cam.R, 26.0 / 0.72, gain=1.3, mw_gain=1.8).copy()
    ex, ey, eR, _ = cam.sphere((0, 0, 0), TL.RE)
    draw_earth(img, ex, ey, eR, body_M(cam.R, gm), cam.R @ TL.SUN, t=t, night_gain=1.5)
    ring_phys(img, cam, gm, t, gain=0.9)
    path_phys(img, cam, tau, 6.0, AMB, gain=0.14, dash=3, n=260)
    path_phys(img, cam, tau - 3.5, tau, AMB, gain=0.8, n=200, fade_tail=True)
    x, y, vis = apo_point(img, cam, tau, amp=1.9, sig=1.8, streak=9)
    T = Text()
    if 20 < x < W - 20 and 20 < y < H: tag(T, x, y, "APOPHIS", win(t, 278.8, 291.6), col=AMB, size=22, dx=30, dy=-40, anchor="l" if x < 760 else "r")
    yh = cput(T, TOP, C._clock(tau), 32, win(t, 278.8, 291.4))
    foot(T, yh + 6, "TRUE SCALE · PATH APPROXIMATE · TIME-LAPSE", win(t, 278.8, 291.2))
    cput(T, 1270, "PREDICTED CLOSEST APPROACH", 23, win(t, 284.0, 291.4), col=DIM)
    y2 = cput(T, 1300, "21:46 UTC", 100, win(t, 284.4, 291.4, 0.9, 0.7), wt="T", track=6, col=YEL)
    cput(T, y2 + 2, "KNOWN YEARS IN ADVANCE · UNCERTAINTY OF ONLY A FEW KILOMETRES", 22, win(t, 286.6, 291.4), col=DIM)
    return T.add_to(bloom(img))


def shot_rock(t, lt):
    M = art_M(-60, 30, roll=18)
    def bg():
        im = render_sky(look_at((0, 0, 0), norm([0.9, 0.1, 0.42])), FL(54), gain=0.85, mw_gain=1.5).copy()
        draw_earth(im, 330, 500, 100, M, SUN_AST, night_gain=1.4)
        return im
    img = cached("vrock_bg", bg).copy()
    ring_art(img, 330, 500, 100, M, t, gain=0.8, line=0.2)
    u = lt / 5.5
    put_sprite(img, ast_at(330 + lt * 24), lerp(540, 600, u), lerp(1010, 960, u), lerp(0.62, 0.55, u), angle=-20 + lt * 0.4, gain=1.05)
    T = Text()
    cput(T, 1380, "A ROCK, ON A PATH WE WORKED OUT", 36, win(t, 299.0, 303.8, 0.8, 0.6))
    return T.add_to(bloom(img))


FUNCS = {"hook": shot_hook, "disc": shot_disc, "scare": shot_scare, "name": shot_name, "relief": shot_relief, "size": shot_size,
         "geo": shot_geo, "moon": shot_moon, "pass": shot_pass, "night": shot_night, "ground1": lambda t, lt: ground_v.frame(t, lt, 1),
         "orbit": shot_orbit, "tides": shot_tides, "miss": shot_miss, "hypo": shot_hypo, "endpass": shot_endpass,
         "ground2": lambda t, lt: ground_v.frame(t, lt, 2), "rock": shot_rock, "ground3": lambda t, lt: ground_v.frame(t, lt, 3)}


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
        for s in sys.argv[2:]:
            t0 = time.time(); im = frame(float(s))
            cv2.imwrite(f"{SCR}/chk/v_{float(s):06.1f}.jpg", to8(im)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92]); print(s, round(time.time() - t0, 2), "s", flush=True)
        return
    t0, t1 = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    os.makedirs(SCR + "/seg_v", exist_ok=True); out = f"{SCR}/seg_v/seg_{f0:05d}.mp4"
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
