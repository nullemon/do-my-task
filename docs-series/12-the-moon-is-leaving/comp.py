"""THE MOON IS LEAVING - frame compositor (numpy + OpenCV + PIL). Every shot is a function of film time, laid out for
16:9 (default) or 9:16 (MOON_VERT=1).
Usage: python3 comp.py T0 T1            -> $SCR/seg[_v]/seg_<frame0>.mp4 (x264 crf 14, silent)
       python3 comp.py --png t1 t2 ...  -> $SCR/chk/f[_v]_<t>.jpg stills"""
import os, sys, math, subprocess, time, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import *
from lib import _grid
from fx import *
import timeline as TL

S = TL.START; V = VERT
TXT = (232, 236, 242); DIM = (176, 186, 200); AMB = (255, 200, 120); COOL = (150, 205, 255); RED = (255, 120, 95); YEL = (255, 214, 80); GRN = (120, 255, 150)
SHOT = {n: (a, b) for n, a, b in TL.SHOTS}


def lonlat(lon, lat):
    lo, la = math.radians(lon), math.radians(lat); return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])


def art_M(lon_c, lat_c, roll=0.0):
    R = look_at(lonlat(lon_c, lat_c) * 10, (0, 0, 0))
    if roll: R = rot_axis((0, 0, 1), math.radians(roll)) @ R
    return R.T


def sky(key, R, fov, **kw):
    return cached(("sky", key), lambda: render_sky(R, FL(fov), **kw))


def put(T, s, al, h, v, col=TXT, wt="L", track=None):
    """h / v = (x, y, size[, anchor]) for the 16:9 / 9:16 layout"""
    p = v if V else h
    if p is None or p[2] <= 0: return
    T.put((p[0], p[1]), s, p[2], al, col=col, anchor=p[3] if len(p) > 3 else ("c" if V else "l"), wt=wt, track=track)


def foot(T, s, al, y=None):
    """small honest-labelling line: bottom right in 16:9; centred, wrapped, inside the safe area in 9:16"""
    if al <= 0.004: return
    if not V:
        T.put((W - 60, 1034 if y is None else y), s, 16, al * 0.85, col=DIM, anchor="r"); return
    parts = s.split("  ·  "); lines = [""]
    for p in parts:
        cand = (lines[-1] + "  ·  " + p) if lines[-1] else p
        if text_w(cand, 19, 19 * 0.16) > W - 110 and lines[-1]: lines.append(p)
        else: lines[-1] = cand
    y0 = (1508 if y is None else y) - (len(lines) - 1) * 30
    for i, l in enumerate(lines): T.put((W / 2, y0 + i * 30), l, 19, al * 0.9, col=DIM, anchor="c")


def layer(key, fn):
    """cache a full-frame float image"""
    return cached(("layer", key), fn)


def zoom(img, s, cx=None, cy=None):
    if abs(s - 1) < 1e-4: return img
    cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    M = np.array([[s, 0, cx - s * cx], [0, s, cy - s * cy]], F32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def vign_dark(img, y0, y1, amt):
    """darken a horizontal band softly (text backing over busy imagery)"""
    yy = np.arange(H, dtype=F32); m = np.clip((yy - y0) / 60, 0, 1) * np.clip((y1 - yy) / 60, 0, 1)
    img *= (1 - amt * m)[:, None, None]


SUN_A = norm([0.62, 0.30, 0.55])              # the key light used for the Earth-Moon hero shots (camera space)
SKY_R = look_at((0, 0, 0), norm([0.35, 0.90, 0.25]))
M_NEAR = art_M(0, 0)


# ================================================================================================= 1 hook
def _pair(key, t, u, moon_p, earth_p0, earth_p1, moon_M, earth_lon, sky_gain=0.9, es=0.0):
    """big Moon (cached) + small Earth drifting from earth_p0 to earth_p1 (x, y, R)"""
    def bg(): return render_sky(SKY_R if key != "leave" else rot_axis((0, 1, 0), 1.3) @ SKY_R, FL(54), gain=sky_gain, mw_gain=1.3)
    def ml():
        im = np.zeros((H, W, 3), F32); draw_moon(im, moon_p[0], moon_p[1], moon_p[2], moon_M, SUN_A, earthshine=es)
        a = np.zeros((H, W, 3), F32); a[:] = 0
        yy, xx = np.mgrid[0:H, 0:W].astype(F32); al = np.clip(moon_p[2] - np.hypot(xx - moon_p[0], yy - moon_p[1]) + 0.5, 0, 1)
        return im, al
    img = layer(key + "_bg", bg).copy()
    ex, ey, er = [lerp(a, b, u) for a, b in zip(earth_p0, earth_p1)]
    draw_earth(img, ex, ey, er, art_M(earth_lon + t * 0.5, 18, roll=-18), SUN_A, t=t, night_gain=1.3)
    mim, mal = layer(key + "_moon", ml)
    s = 1.0 + 0.045 * u
    if s != 1.0:
        mim = zoom(mim, s, moon_p[0], moon_p[1]); mal = zoom(mal, s, moon_p[0], moon_p[1])
    img = img * (1 - mal[..., None]) + mim
    return img, (ex, ey, er)


def shot_hook(t, lt):
    u = lt / 23.6; us = ss(0, 1, u) * 0.5 + u * 0.5
    if not V: mp = (610, 590, 430); e0 = (1480, 330, 128); e1 = (1590, 262, 92)
    else: mp = (500, 950, 365); e0 = (810, 500, 104); e1 = (880, 455, 78)
    img, (ex, ey, er) = _pair("hook", t, us, mp, e0, e1, art_M(-12, 6, roll=14), -30)
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "THE MOON", win(t, 0.3, 18.6, 0.6), (120, 96, 27), (W / 2, 250, 30))
    a1 = win(t, 1.1, 9.8, 0.7, 0.7)
    put(T, "3.8 CM", a1, (1060, 640, 150), None, col=YEL, wt="XL", track=8)
    if V: T.put((W / 2, 1335), "3.8 CM A YEAR", 96, a1, col=YEL, wt="XL", track=5, anchor="c")
    put(T, "A YEAR", a1, (1066, 808, 62), (W / 2, 1586, 0), col=YEL, wt="L", track=18)
    if V: T.put((W / 2, 1462), "FARTHER FROM THE EARTH, EVERY YEAR", 24, win(t, 1.7, 9.8, 0.7), anchor="c")
    else:
        T.put((1066, 900), "FARTHER FROM THE EARTH, EVERY YEAR", 25, win(t, 1.7, 9.8, 0.7))
        T.put((1066, 940), "ABOUT THE SPEED YOUR FINGERNAILS GROW", 21, win(t, 5.6, 9.8, 0.7), col=DIM)
    if V: T.put((W / 2, 1504), "ABOUT THE SPEED YOUR FINGERNAILS GROW", 20, win(t, 5.6, 9.8, 0.7), col=DIM, anchor="c")
    a2 = win(t, 10.6, 18.6, 0.9, 0.7)
    if not V:
        T.put((1066, 690), "THE LAST TOTAL", 64, a2, wt="T", track=9); T.put((1066, 774), "ECLIPSE IS COMING", 64, a2, wt="T", track=9)
        T.put((1066, 884), "MEASURED WITH LASERS  ·  LEAVING FOR 4 BILLION YEARS", 21, win(t, 11.8, 18.6), col=AMB)
    else:
        T.put((W / 2, 1320), "THE LAST TOTAL", 56, a2, wt="L", track=8, anchor="c"); T.put((W / 2, 1396), "ECLIPSE IS COMING", 56, a2, wt="L", track=8, anchor="c")
        T.put((W / 2, 1492), "LEAVING FOR 4 BILLION YEARS", 23, win(t, 11.8, 18.6), col=AMB, anchor="c")
    foot(T, "NOT TO SCALE  ·  MOON: NASA LRO IMAGERY + LASER ALTIMETRY  ·  EARTH: NASA BLUE MARBLE", win(t, 1.5, 18.6) , y=(1040 if not V else 330))
    a3 = win(t, 19.4, 23.6, 1.0, 0.6)
    if a3 > 0:
        img *= (1 - 0.45 * a3)
        put(T, "THE MOON IS LEAVING", a3, (W / 2, 470, 88, "c"), (W / 2, 1340, 62, "c"), wt="T" if not V else "L", track=22 if not V else 10)
        put(T, "3.8 CENTIMETRES EVERY YEAR", win(t, 20.2, 23.6, 1.0, 0.6), (W / 2, 598, 25, "c"), (W / 2, 1440, 25, "c"), col=AMB)
    return T.add_to(img)


# ================================================================================================= 2 reflector
SITES = [("APOLLO 11", "1969", 23.47, 0.67), ("APOLLO 14", "1971", -17.47, -3.64), ("APOLLO 15", "1971", 3.63, 26.13),
         ("LUNOKHOD 1", "1970", -35.0, 38.32), ("LUNOKHOD 2", "1973", 30.92, 25.85)]


def _refl_view(u, close=False):
    P = plate("reflector")
    if not V:
        s = lerp(0.90, 0.96, u) if not close else lerp(1.25, 1.36, u); pc = (1080, lerp(1140, 1160, u)) if not close else (1030, 1210)
    else:
        s = lerp(1.0, 1.07, u) if not close else lerp(1.45, 1.58, u); pc = (1010, 1075) if not close else (1010, 1255)
    return P, pc, s


def shot_reflector(t, lt):
    u = lt / 16.0
    P, pc, s = _refl_view(u)
    fr = plate_view(P, pc[0], pc[1], s)
    img = np.zeros((H, W, 3), F32) + fr[..., :3] * 1.3
    img = bloom(img, 0.85, 0.35)
    # inset: the near side with the five reflector sites
    al = win(t, 26.4, 39.6, 1.0, 0.6)
    T = Text()
    if al > 0:
        ix, iy, ir = (1520, 335, 190) if not V else (W / 2, 570, 140)
        yy, xx = np.ogrid[0:H, 0:W]; img *= (1 - 0.55 * al * np.exp(-(np.clip(np.hypot(xx - ix, yy - iy) / ir - 1, 0, None) / 0.9) ** 2))[..., None]
        ins = np.zeros((H, W, 3), F32); draw_moon(ins, ix, iy, ir, M_NEAR, norm([0.25, 0.2, 0.94]), exposure=0.95, relief=0.45, detail=0.6)
        yy, xx = np.ogrid[0:H, 0:W]; m = np.clip(ir + 1.5 - np.hypot(xx - ix, yy - iy), 0, 1)[..., None] * al
        img = img * (1 - m) + ins * m
        L = Lines(); L.circle(ix, iy, ir + 5, 120, 1); L.add_to(img, (0.8, 0.85, 1.0), 0.5 * al, 0.3)
        for k, (nm, yr, lon, lat) in enumerate(SITES):
            a_k = win(t, 27.4 + 0.7 * k, 39.6, 0.6, 0.6)
            c = M_NEAR.T @ lonlat(lon, lat); x, y = ix + ir * c[0], iy - ir * c[1]
            add_glint(img, x, y, 1.6 * a_k, (1.0, 0.85, 0.35), sig=2.2)
            left = lon < 0
            dx = (-44 if left else 44) if k != 2 else 30; dy = (26, 40, -96, -40, -30)[k]
            T.line((x + dx * 0.2, y + dy * 0.2), (x + dx, y + dy), a_k * 0.8, YEL)
            T.put((x + dx + (-8 if left else 8), y + dy - 13), f"{nm} · {yr}", 18, a_k, col=TXT, anchor="r" if left else "l", wt="R", track=1.5)
    put(T, "RETROREFLECTORS ON THE MOON", win(t, 24.2, 39.6, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "LEFT BY THREE APOLLO CREWS AND TWO SOVIET ROVERS", win(t, 25.2, 39.6, 0.8), (120, 140, 20), (W / 2, 296, 19), col=AMB)
    put(T, "100 GLASS PRISMS  ·  EACH RETURNS LIGHT TO ITS SOURCE", win(t, 32.0, 39.6, 0.8), (120, 184, 20), (W / 2, 760, 20))
    if V: foot(T, "ILLUSTRATION  ·  3D MODEL AFTER THE APOLLO 11 ARRAY (LRRR)", win(t, 24.6, 39.6), y=370)
    else: T.put((120, 226), "ILLUSTRATION  ·  3D MODEL AFTER THE APOLLO 11 ARRAY (LRRR), NOT A PHOTOGRAPH", 16, win(t, 24.6, 39.6) * 0.9, col=DIM)
    return T.add_to(img)


# ================================================================================================= 3 observatory
def shot_obs(t, lt):
    u = lt / 12.8
    P = plate("observatory"); J = cached("obsj", lambda: json.load(open(SCR + "/plates/observatory.json")))
    if not V: s = lerp(0.90, 0.96, u); pc = (1180, 985); mpos = (1560, 170, 58)
    else: s = lerp(1.18, 1.26, u); pc = (1050, 1130); mpos = (850, 500, 62)
    def bg():
        Rs = rot_axis((1, 0, 0), 0.5) @ look_at((0, 0, 0), norm([-0.25, 0.75, -0.45]))
        im = render_sky(Rs, FL(60), gain=1.25, mw_gain=2.0)
        yy = np.arange(H, dtype=F32)[:, None, None] / H
        im = im * (1 - 0.5 * yy ** 2) + np.array([0.012, 0.022, 0.05], F32) * (0.35 + 1.6 * yy ** 1.6)       # airglow / moonlit haze toward the horizon
        # moonlight halo
        y_, x_ = np.mgrid[0:H, 0:W].astype(F32); d = np.hypot(x_ - mpos[0], y_ - mpos[1]) / mpos[2]
        im += (0.5 * np.exp(-d / 1.6) + 0.10 * np.exp(-d / 6.0))[..., None] * np.array([0.55, 0.68, 1.0], F32)
        draw_moon(im, mpos[0], mpos[1], mpos[2], art_M(4, -3, roll=-20), norm([0.45, 0.25, 0.86]), exposure=1.35)
        return im
    img = layer("obs_bg", bg).copy()
    fr = plate_view(P, pc[0], pc[1], s)
    gy0 = plate_pt((0, 1230), pc[0], pc[1], s)[1]; yy = np.arange(H, dtype=F32)
    fr = fr.copy(); fr[..., :3] *= (1 - 0.72 * np.clip((yy - gy0) / (260 * s), 0, 1))[:, None, None]
    ex, ey = plate_pt(J["exit"], pc[0], pc[1], s)
    # the beam: thin green column from the telescope to the Moon, with pulses running out
    mx, my = mpos[0] - mpos[2] * 0.25, mpos[1] + mpos[2] * 0.1
    al = win(t, 40.6, 52.4, 0.8, 0.5)
    beam = np.zeros((H, W), F32)
    n = 420; k = np.linspace(0, 1, n); bx = ex + (mx - ex) * k; by = ey + (my - ey) * k
    L = Lines(); L.poly(bx, by, 255, 2)
    core = L.l.astype(F32) / 255
    prof = np.zeros((H, W), F32)
    dist = ((np.mgrid[0:H, 0:W][1] - ex) * (mx - ex) + (np.mgrid[0:H, 0:W][0] - ey) * (my - ey)) / ((mx - ex) ** 2 + (my - ey) ** 2)
    pulse = 0.55 + 0.45 * (np.sin((dist * 9 - t * 3.0) * 2 * np.pi) > 0.86)
    fall = np.clip(1.15 - 0.75 * dist, 0.2, 1.2)
    beam = core * pulse * fall
    glow = cv2.GaussianBlur(beam, (0, 0), 2.2) * 2.4 + cv2.GaussianBlur(beam, (0, 0), 9) * 2.2 + cv2.GaussianBlur(core * fall, (0, 0), 30) * 1.2
    img += ((beam * 1.6 + glow) * al)[..., None] * np.array([0.25, 1.0, 0.42], F32)
    img = img * (1 - fr[..., 3:4]) + fr[..., :3] * 1.15
    add_glint(img, ex, ey, 2.0 * al, (0.4, 1.0, 0.55), sig=5, streak=10)
    add_glint(img, mx, my, 1.2 * al * (0.6 + 0.4 * math.sin(t * 7)), (0.4, 1.0, 0.55), sig=2.5)
    img = bloom(img, 0.8, 0.55)
    T = Text()
    put(T, "LUNAR LASER RANGING", win(t, 40.2, 52.4, 0.8), (120, 96, 27), (W / 2, 250, 27))
    put(T, "FIRE A PULSE.  TIME THE ECHO.", win(t, 41.0, 52.4, 0.8), (120, 140, 20), (W / 2, 296, 20), col=AMB)
    # round-trip timer, restarts with each pulse
    a_t = win(t, 44.3, 52.4, 0.7, 0.5)
    ph = ((t - 44.4) % 2.7); val = min(ph, 2.56)
    put(T, f"{val:4.2f} S", a_t, (120, 800, 92), (W / 2, 1310, 84), col=GRN, wt="XL", track=6)
    put(T, "ROUND TRIP  ·  ABOUT 2.5 SECONDS", a_t, (126, 912, 22), (W / 2, 1420, 21))
    put(T, "≈ 384,400 KM EACH WAY, ON AVERAGE", win(t, 46.0, 52.4, 0.7, 0.5), (126, 950, 20), (W / 2, 1462, 19), col=DIM)
    foot(T, "ILLUSTRATION  ·  BEAM BRIGHTENED, MOON ENLARGED  ·  STAR FIELD FROM A REAL CATALOGUE", win(t, 40.4, 52.4), y=(1034 if not V else 370))
    return T.add_to(img)


def shot_ret(t, lt):
    u = lt / 7.2
    P, pc, s = _refl_view(u, close=True)
    fr = plate_view(P, pc[0], pc[1], s); gl = plate_view(plate("reflector_glow"), pc[0], pc[1], s)
    img = np.zeros((H, W, 3), F32) + fr[..., :3] * 1.3
    g = gl[..., :3].max(-1)[..., None] * np.array([0.22, 1.0, 0.42], F32)
    k = 0.25 + 0.75 * max(0.0, math.sin((t - 52.9) * 2 * math.pi / 2.4)) ** 6
    a = win(t, 52.9, 59.6, 0.5, 0.5)
    img += (g * 0.16 + cv2.GaussianBlur(g, (0, 0), 4) * 0.30 + cv2.GaussianBlur(g, (0, 0), 30) * 0.32) * (k * a)
    img = bloom(img, 0.85, 0.4)
    if V: vign_dark(img, -100, 430, 0.55)
    T = Text()
    put(T, "ONLY A FEW PHOTONS RETURN PER PULSE", win(t, 53.0, 59.6, 0.7), (120, 96, 27), (W / 2, 250, 23))
    put(T, "ENOUGH TO TRACK THE DISTANCE TO MILLIMETRES", win(t, 54.6, 59.6, 0.7), (120, 140, 20), (W / 2, 296, 19), col=AMB)
    foot(T, "ILLUSTRATION  ·  THE RETURNING LIGHT IS FAR TOO FAINT TO SEE", win(t, 52.8, 59.6), y=(1034 if not V else 340))
    return T.add_to(img)


# ================================================================================================= 4 tides
def shot_tides(t, lt):
    a0, b0 = SHOT["tides"]
    if not V: ec = np.array([620.0, 560.0]); ER = 215; D = 900; th0 = math.radians(-9)
    else: ec = np.array([540.0, 640.0]); ER = 185; D = 640; th0 = math.radians(-97)
    MR = ER * 0.2727
    def bg(): return render_sky(rot_axis((0, 1, 0), 2.2) @ SKY_R, FL(50), gain=0.55, mw_gain=1.0)
    img = layer("tide_bg", bg).copy()
    # Moon creeps along its orbit (counter-clockwise seen from the north), Earth turns ~27x faster (time-lapse, not to rate)
    thm = th0 + math.radians(0.42) * (t - a0)
    md = np.array([math.cos(thm), -math.sin(thm)]); mc = ec + md * D
    lead = math.radians(24) * ss(S['tide2'] + 0.5, S['tide2'] + 6.5, t)          # bulge carried ahead of the Moon (exaggerated)
    thb = thm + lead
    # ocean bulge: soft blue ellipsoid hull behind the globe
    hull = np.zeros((H, W), np.uint8)
    ax = (int(ER * 1.30 * 16), int(ER * 1.035 * 16))
    cv2.ellipse(hull, (int(ec[0] * 16), int(ec[1] * 16)), ax, -math.degrees(thb), 0, 360, 255, -1, cv2.LINE_AA, 4)
    hf = hull.astype(F32) / 255; edge = hf - cv2.erode(hf, np.ones((3, 3), np.uint8))
    ha = win(t, S['tide1'] + 5.0, b0, 1.5, 0.6)
    inner = cv2.GaussianBlur(hf, (0, 0), 14)
    img += ((hf * (0.30 + 0.5 * (1 - inner) * 2.0)) * ha)[..., None] * np.array([0.10, 0.34, 0.85], F32)
    img += (cv2.GaussianBlur(edge, (0, 0), 1.2) * 1.5 * ha + cv2.GaussianBlur(hf, (0, 0), 22) * (1 - hf) * 0.5 * ha)[..., None] * np.array([0.35, 0.65, 1.0], F32)
    # Earth from above the north pole, rotating counter-clockwise
    sun_c = norm([0.45, 0.55, 0.7])
    Me = rot_axis((0, 0, 1), math.radians(-((t - a0) * 9.0) + 200)) @ art_M(0, 89.9).T; Me = Me.T if False else Me
    draw_earth(img, ec[0], ec[1], ER, (rot_axis((0, 0, 1), math.radians((t - a0) * 9.0 + 200)) @ np.linalg.inv(art_M(0, 89.9))).T if False else art_M(0, 89.9) @ rot_axis((0, 0, 1), math.radians(-(t - a0) * 9.0 - 200)), sun_c, t=t, night_gain=0, atmo=0.8, glint=0.25)
    Mm = art_M(0, 89.9) @ rot_axis((0, 0, 1), -thm + math.pi)
    draw_moon(img, mc[0], mc[1], MR, Mm, sun_c, exposure=1.05)
    L = Lines(); Ly = Lines(); Lr = Lines()
    # orbit (dashed) and the slowly widening path
    k = np.linspace(0, 2 * np.pi, 720); L.poly(ec[0] + D * np.cos(k), ec[1] - D * np.sin(k), 150, 1, dash=6)
    # Earth-Moon line and the bulge axis
    a_ax = win(t, S['tide1'] + 6.0, b0, 1.0, 0.6)
    bd = np.array([math.cos(thb), -math.sin(thb)])
    L.seg(*(ec + md * (ER * 1.02)), *(mc - md * (MR + 8)), int(90 * a_ax), 1)
    for sg in (-1, 1): Ly.seg(*(ec + sg * bd * ER * 1.02), *(ec + sg * bd * ER * 1.52), int(255 * a_ax * ss(S['tide2'], S['tide2'] + 3, t)), 2)
    # spin arrow (arc) around the Earth
    a_sp = win(t, S['tide2'] - 0.3, b0, 1.0, 0.6)
    k = np.linspace(thm + 0.9, thm + 2.1, 60); rr = ER * 1.72
    xs_, ys_ = ec[0] + rr * np.cos(k), ec[1] - rr * np.sin(k); L.poly(xs_, ys_, int(230 * a_sp), 2); arrow(L, xs_[-2], ys_[-2], xs_[-1], ys_[-1], int(230 * a_sp), 2, 15)
    # tide2: pull of the near bulge on the Moon (forward), Moon's motion
    a_f = win(t, S['tide2'] + 6.4, b0, 1.0, 0.6)
    tang = np.array([-math.sin(thm), -math.cos(thm)])            # direction of orbital motion on screen
    p0 = mc + tang * (MR + 12); arrow(Ly, *p0, *(p0 + tang * 120), int(255 * a_f), 2, 16)
    nb = ec + bd * ER * 1.30
    Ly.poly(np.linspace(nb[0], mc[0] - md[0] * (MR + 10), 80), np.linspace(nb[1], mc[1] - md[1] * (MR + 10), 80), int(190 * a_f), 1, dash=4)
    # tide3: Moon's pull back on the bulge (brake)
    a_b = win(t, S['tide3'] + 0.3, b0, 1.0, 0.6)
    tb = np.array([-math.sin(thb), -math.cos(thb)]); q0 = ec + bd * ER * 1.40 + tb * 10
    arrow(Lr, *q0, *(q0 - tb * 105), int(255 * a_b), 2, 16)
    L.add_to(img, (0.75, 0.82, 1.0), 0.8, 0.4); Ly.add_to(img, np.array(YEL) / 255, 1.0, 0.6); Lr.add_to(img, np.array(RED) / 255, 1.1, 0.6)
    img = bloom(img, 0.85, 0.4)
    T = Text()
    put(T, "WHY IT LEAVES: THE TIDES", win(t, a0 + 0.6, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    def lab(p, s_, al, col=TXT, size=20, anchor="c", dy=0):
        T.put((p[0], p[1] + dy), s_, size if not V else size + 1, al, col=col, anchor=anchor)
    lab(ec + bd * ER * 1.6 + np.array([0, -ER * 0.6]) if not V else ec + np.array([ER * 1.05, ER * 1.25]), "TIDAL BULGE", win(t, S['tide1'] + 6.0, b0, 0.8), COOL, anchor="c" if not V else "l")
    lab(ec - bd * ER * 1.75 + np.array([0, ER * 0.55]) if not V else ec + np.array([-ER * 1.05, -ER * 1.45]), "AND ANOTHER, OPPOSITE", win(t, S['tide1'] + 9.0, S['tide2'] + 2.0, 0.8), COOL, anchor="c" if not V else "r")
    lab(ec + np.array([-ER * 1.5, -ER * 1.72]) if not V else ec + np.array([-ER * 2.7, -ER * 1.1]), "EARTH TURNS ONCE A DAY", a_sp, TXT, anchor="l")
    lab(mc + np.array([0, MR + 34]) if not V else mc + np.array([0, MR + 30]), "THE MOON ORBITS ONCE IN 27 DAYS", win(t, S['tide2'] + 1.6, b0, 0.8), DIM, size=18)
    lab(mc + (np.array([-150, -MR - 190]) if not V else np.array([MR + 150, -40])), "PULLED FORWARD", a_f, YEL, anchor="c" if not V else "l")
    lab(mc + (np.array([-150, -MR - 160]) if not V else np.array([MR + 150, -10])), "→ A WIDER ORBIT", win(t, S['tide2'] + 9.0, b0, 0.8), YEL, anchor="c" if not V else "l")
    lab(ec + (np.array([ER * 1.35, ER * 0.95]) if not V else np.array([ER * 1.15, -ER * 1.6])), "PULLED BACK: THE SPIN SLOWS", a_b, RED, anchor="l" if not V else "c")
    put(T, "THE SPIN THE EARTH LOSES, THE MOON GAINS", win(t, S['tide3'] + 3.6, b0, 0.8), (120, 968, 23), (W / 2, 1440, 21), col=AMB)
    foot(T, "SCHEMATIC  ·  NOT TO SCALE  ·  BULGE AND ANGLE GREATLY EXAGGERATED (THE OPEN-OCEAN BULGE IS UNDER A METRE)", win(t, a0 + 1.0, b0))
    return T.add_to(img)


# ================================================================================================= 5 day / 6 past
def shot_day(t, lt):
    a0, b0 = SHOT["day"]; u = lt / (b0 - a0)
    if not V: ex, ey, ER = 1360, 620, 640
    else: ex, ey, ER = 540, 1660, 760
    def bg(): return render_sky(rot_axis((0, 1, 0), 0.8) @ SKY_R, FL(50), gain=0.7, mw_gain=1.2)
    img = layer("day_bg", bg).copy()
    draw_earth(img, ex, ey, ER, art_M(-20 + (t - a0) * 1.6, 28, roll=-23.4), norm([-0.72, 0.28, 0.62]), t=t, night_gain=1.5, glint=0.22)
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "THE DAY IS GETTING LONGER", win(t, a0 + 0.6, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    a1 = win(t, S['day1'] + 3.0, b0, 0.8)
    put(T, "+2.3", a1, (120, 330, 120), (W / 2, 350, 104), col=TXT, wt="XL", track=4)
    put(T, "MILLISECONDS PER CENTURY", a1, (126, 474, 22), (W / 2, 474, 21))
    put(T, "PREDICTED FROM THE TIDES ALONE", a1, (126, 510, 19), (W / 2, 508, 19), col=DIM)
    a2 = win(t, S['day1'] + 8.2, b0, 0.8)
    put(T, "+1.8", a2, (120, 610, 120), (W / 2, 590, 104), col=YEL, wt="XL", track=4)
    put(T, "MILLISECONDS PER CENTURY", a2, (126, 754, 22), (W / 2, 714, 21))
    put(T, "MEASURED  ·  ECLIPSE RECORDS, 720 BC TO AD 2015", a2, (126, 790, 19), (W / 2, 748, 19), col=DIM)
    put(T, "THE GAP: THE EARTH ITSELF IS CHANGING SHAPE", win(t, S['day1'] + 11.0, b0, 0.8), (126, 860, 19), (W / 2, 800, 19), col=AMB)
    foot(T, "STEPHENSON, MORRISON & HOHENKERK 2016  ·  EARTH: NASA BLUE MARBLE, CLOUDS, NIGHT LIGHTS", win(t, a0 + 1.0, b0), y=(1034 if not V else 872))
    return T.add_to(img)


def shot_past(t, lt):
    a0, b0 = SHOT["past"]
    if not V: ex, ey, ER = 1330, 560, 360
    else: ex, ey, ER = 540, 1080, 305
    def bg(): return render_sky(rot_axis((0, 1, 0), 1.6) @ SKY_R, FL(50), gain=0.7, mw_gain=1.2)
    img = layer("past_bg", bg).copy()
    k = ss(S['past1'] + 3.2, S['past1'] + 15.5, t)                   # rewind progress
    spin = -(t - a0) * 3.0 + 420 * (k * k * (3 - 2 * k)) + 140 * k      # runs backwards, fast, then settles
    draw_earth(img, ex, ey, ER, art_M(60 + spin, 22, roll=-23.4), norm([-0.55, 0.30, 0.78]), t=t * (1 - k) - 40 * k, night_gain=1.4, glint=0.3)
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "RUN THE CLOCK BACKWARDS", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    yrs = 70e6 * k ** 2.2; days = 365.25 + (372 - 365.25) * k ** 2.2; hrs = 8766.0 / days
    a1 = win(t, S['past1'] + 2.6, b0, 0.8)
    ys_ = f"{int(round(yrs / 1e5) * 1e5):,}" if yrs > 0 else "0"
    put(T, ys_, a1, (120, 300, 78), (W / 2, 330, 70), col=TXT, wt="XL", track=3)
    put(T, "YEARS AGO", a1, (126, 396, 22), (W / 2, 414, 21), col=DIM)
    put(T, f"{days:5.1f}" if k < 1 else "≈ 372", a1, (120, 500, 104), (W / 2, 480, 92), col=YEL, wt="XL", track=3)
    put(T, "DAYS IN A YEAR", a1, (126, 624, 22), (W / 2, 590, 21))
    hh = int(hrs); mm = int(round((hrs - hh) * 60))
    put(T, f"{hh} H {mm:02d} MIN", a1, (120, 720, 78), (W / 2, 1470, 60), col=TXT, wt="XL", track=3)
    put(T, "LENGTH OF ONE DAY", a1, (126, 816, 22), (W / 2, 1426, 21), col=DIM)
    put(T, "LATE CRETACEOUS  ·  FROM DAILY GROWTH LAYERS IN A FOSSIL SHELL", win(t, S['past1'] + 9.5, b0, 0.8), (126, 900, 19), (W / 2, 650, 0), col=AMB)
    if V: T.put((W / 2, 650), "LATE CRETACEOUS  ·  FROM A FOSSIL SHELL", 19, win(t, S['past1'] + 9.5, b0, 0.8), col=AMB, anchor="c")
    foot(T, "DE WINTER ET AL. 2020 (372 ± 8 DAYS)  ·  PRESENT-DAY GEOGRAPHY SHOWN  ·  THE YEAR ITSELF WAS THE SAME LENGTH", win(t, a0 + 1.0, b0), y=(1034 if not V else 730))
    return T.add_to(img)


def shot_coral(t, lt):
    a0, b0 = SHOT["coral"]; u = lt / (b0 - a0)
    P = plate("coral")
    if not V: s = lerp(0.89, 0.94, u); pc = (lerp(1070, 1085, u), lerp(1085, 1060, u))
    else: s = lerp(0.92, 1.0, u); pc = (960, lerp(1060, 1090, u))
    fr = plate_view(P, pc[0], pc[1], s)
    img = np.zeros((H, W, 3), F32) + fr[..., :3]
    vign_dark(img, -100, 340 if not V else 420, 0.55)
    if V: vign_dark(img, 1200, 1620, 0.6)
    else: img[-80:] *= np.linspace(1, 0.4, 80, dtype=F32)[:, None, None]
    img = bloom(img, 0.85, 0.3)
    T = Text()
    put(T, "ABOUT 400 MILLION YEARS AGO", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "DEVONIAN CORALS: A NEW GROWTH LINE EVERY DAY", win(t, a0 + 1.8, b0, 0.8), (120, 140, 20), (W / 2, 296, 19), col=AMB)
    a1 = win(t, S['past2'] + 4.6, b0, 0.8)
    put(T, "≈ 400", a1, (120, 210, 104), (W / 2, 1260, 96), col=YEL, wt="XL", track=3)
    put(T, "DAYS IN A YEAR", a1, (480, 268, 22), (W / 2, 1374, 21))
    put(T, "ONE DAY ≈ 21.9 HOURS", win(t, S['past2'] + 8.0, b0, 0.8), (480, 304, 20), (W / 2, 1414, 21), col=TXT)
    foot(T, "ILLUSTRATION OF A FOSSIL HORN CORAL (3D MODEL)  ·  COUNTS: J. W. WELLS, 1963  ·  ESTIMATES VARY BY SPECIMEN", win(t, a0 + 1.0, b0))
    return T.add_to(img)


# ================================================================================================= 8 origin / 9 ancient
_RNG = np.random.default_rng(21)
_DN = 90000
_DR = 1.25 + 2.3 * _RNG.uniform(0, 1, _DN) ** 0.8; _DA = _RNG.uniform(0, 2 * np.pi, _DN); _DZ = _RNG.normal(0, 0.035, _DN) * _DR; _DB = _RNG.uniform(0.2, 1, _DN) ** 3
_DH = _RNG.uniform(0, 1, _DN)


def shot_origin(t, lt):
    a0, b0 = SHOT["origin"]; ti = S['origin1'] + 6.3                  # impact moment ("struck the young Earth")
    if not V: ec = (820.0, 560.0); ER = 250.0
    else: ec = (540.0, 900.0); ER = 215.0
    def bg(): return render_sky(rot_axis((0, 1, 0), 2.9) @ SKY_R, FL(50), gain=0.7, mw_gain=1.4)
    img = layer("orig_bg", bg).copy()
    sunv = norm([-0.7, 0.2, 0.55])
    post = ss(ti - 0.1, ti + 0.6, t)
    Me = art_M(40 + (t - a0) * 2.0, 15, roll=-10)
    # debris disc behind the planet (after the impact)
    tilt = math.radians(74); ct, st = math.cos(tilt), math.sin(tilt)
    def disc(front):
        if post <= 0: return
        age = max(0.0, t - ti)
        y_, x_ = np.mgrid[0:H, 0:W].astype(F32); dx = (x_ - ec[0]) / ER; dy = (ec[1] - y_) / ER / math.cos(tilt)
        r = np.hypot(dx, dy); az = np.arctan2(dy, dx)
        N = cached("ringN", lambda: pnoise(2048, 256, 6, 24, 0.6, 31, aspect=0.5))
        om = 0.5 / np.maximum(r, 1.0) ** 1.5
        mxn = (((az - om * age) / (2 * np.pi)) % 1.0 * 2048).astype(F32); myn = np.clip((r - 1.0) / 2.8 * 255, 0, 255).astype(F32)
        n = cv2.remap(N, mxn, myn, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        bands = 0.8 + 0.2 * np.sin(r * 7 + 3 * n)
        grow = ss(2.5, 9.0, age)
        prof = np.clip((r - 1.12) / 0.25, 0, 1) * np.exp(-np.clip(r - 1.5, 0, None) / (0.40 + 0.35 * ss(0, 5, age))) * (1 - 0.75 * grow * np.exp(-((r - (2.9 if not V else 1.95)) / 0.42) ** 2))
        I = prof * bands * np.clip(0.55 + 1.3 * n, 0.05, 2.0) * (1.25 - 0.35 * ss(0, 9, age))
        m = (dy < 0) if front else ((dy >= 0) & (np.hypot(x_ - ec[0], y_ - ec[1]) > ER * 0.985))
        img[:] += heat_col(I * m * 0.95) * post
    disc(False)
    draw_molten(img, ec[0], ec[1], ER, Me, sunv, heat=0.85 + 1.4 * post * math.exp(-max(0, t - ti) / 9.0) + 0.35 * post, exposure=1.0)
    disc(True)
    # Theia approaching (before), the young Moon gathering in the disc (after)
    if t < ti + 0.2:
        k = min(max((t - a0) / (ti - a0), 0.0), 1.0)
        tx = lerp(ec[0] + ER * (4.2 if not V else 2.2), ec[0] + ER * 1.25, k ** 1.5); ty = lerp(ec[1] - ER * (1.6 if not V else 3.2), ec[1] - ER * 0.55, k ** 1.5)
        draw_molten(img, tx, ty, ER * 0.53, art_M(200 + t * 3, -20, roll=30), sunv, heat=0.55, exposure=1.1, rock=(0.13, 0.09, 0.075), haze=0.5)
    age = max(0.0, t - ti)
    if age > 3.6:
        g_ = ss(2.0, 8.5, age); am = 2.75 + 0.07 * age; mrad = 2.9 if not V else 1.95
        mx_ = ec[0] + ER * mrad * math.cos(am); my_ = ec[1] - ER * mrad * math.sin(am) * math.cos(tilt)
        if math.sin(am) > 0 or math.hypot(mx_ - ec[0], my_ - ec[1]) > ER:
            draw_molten(img, mx_, my_, ER * 0.27 * g_ ** 0.6, art_M(t * 5, 10), sunv, heat=1.25, exposure=0.8, haze=0.6)
    # impact flash
    fl = math.exp(-((t - ti) / 0.30) ** 2) * 2.2 + 0.7 * math.exp(-max(0, t - ti) / 1.6) * post
    if fl > 0.003:
        y_, x_ = np.mgrid[0:H, 0:W].astype(F32); d = np.hypot(x_ - (ec[0] + ER * 0.8), y_ - (ec[1] - ER * 0.35)) / ER
        img += (fl * (2.6 * np.exp(-(d / 0.7) ** 2) + 1.0 * np.exp(-d / 2.2)))[..., None] * np.array([1.0, 0.86, 0.62], F32)
    img = bloom(img, 0.7, 0.7)
    T = Text()
    put(T, "ABOUT 4.5 BILLION YEARS AGO", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "THE GIANT-IMPACT HYPOTHESIS", win(t, a0 + 1.8, b0, 0.8), (120, 140, 20), (W / 2, 296, 20), col=AMB)
    put(T, "A MARS-SIZED BODY STRIKES THE YOUNG EARTH", win(t, S['origin1'] + 4.4, ti + 2.6, 0.7), (120, 968, 22), (W / 2, 1360, 20))
    put(T, "THE DEBRIS GATHERS INTO THE MOON  ·  MORE THAN 10× CLOSER THAN TODAY", win(t, ti + 3.2, b0, 0.8), (120, 968, 22), None)
    if V:
        T.put((W / 2, 1340), "THE DEBRIS GATHERS INTO THE MOON", 20, win(t, ti + 3.2, b0, 0.8), anchor="c"); T.put((W / 2, 1376), "MORE THAN 10× CLOSER THAN TODAY", 20, win(t, ti + 3.2, b0, 0.8), anchor="c", col=YEL)
    foot(T, "ARTIST'S IMPRESSION  ·  NOT TO SCALE  ·  TIMESCALE COMPRESSED (THE MOON MAY HAVE TAKEN MONTHS TO YEARS TO FORM)", win(t, a0 + 1.0, b0))
    return T.add_to(img)


def shot_ancient(t, lt):
    a0, b0 = SHOT["ancient"]; u = lt / (b0 - a0)
    f = FL(16)
    if not V: yh = 800; mp = (lerp(1010, 990, u), lerp(455, 430, u), 395)
    else: yh = 1330; mp = (540, lerp(890, 860, u), 400)
    def skyl():
        Rs = rot_axis((0, 1, 0), 0.4) @ SKY_R
        im = render_sky(Rs, FL(30), gain=0.8, mw_gain=1.2)
        yy = (np.arange(H, dtype=F32)[:, None, None] - yh) / H
        haze = np.exp(-np.abs(yy) / 0.16)
        im = im * (1 - 0.92 * haze) + haze * np.array([0.42, 0.17, 0.07], F32) * 0.75 + np.exp(-np.abs(yy) / 0.035) * np.array([0.9, 0.42, 0.15], F32) * 0.35
        return im
    sk = layer("anc_sky", skyl).copy()
    def moonl():
        im = np.zeros((H, W, 3), F32)
        draw_moon(im, mp[0], 0 + (455 if not V else 890), mp[2], art_M(-8, -4, roll=28), norm([0.55, 0.42, 0.72]), exposure=1.25, tint=(1.0, 0.93, 0.82), glow=((1.0, 0.30, 0.06), 0.55), relief=1.3)
        yy, xx = np.mgrid[0:H, 0:W].astype(F32); al = np.clip(mp[2] - np.hypot(xx - mp[0], yy - (455 if not V else 890)) + 0.5, 0, 1)
        return im, al
    mim, mal = layer("anc_moon", moonl)
    dy = mp[1] - (455 if not V else 890); Mt = np.array([[1, 0, 0], [0, 1, dy]], F32)
    mim = cv2.warpAffine(mim, Mt, (W, H)); mal = cv2.warpAffine(mal, Mt, (W, H))
    # atmospheric reddening of the Moon toward the horizon
    yy = np.arange(H, dtype=F32)[:, None]; ext = np.clip((yy - (yh - 420)) / 420, 0, 1)
    mim = mim * (1 - ext[..., None] * np.array([0.25, 0.55, 0.8], F32))
    sk = sk * (1 - mal[..., None] * 0.97) + mim
    # halo
    y_, x_ = np.mgrid[0:H, 0:W].astype(F32); d = np.clip(np.hypot(x_ - mp[0], y_ - mp[1]) / mp[2] - 1, 0, None)
    sk += (0.22 * np.exp(-d / 0.25))[..., None] * np.array([1.0, 0.62, 0.36], F32) * (1 - mal[..., None])
    img = sea(sk * 1.0, yh, t, f, cxp=W / 2, base=(0.012, 0.010, 0.012), rough=1.0, speed=0.55, gain=1.25, horizon_col=(0.30, 0.13, 0.06))
    img = bloom(img, 0.75, 0.6)
    T = Text()
    put(T, "THE YOUNG MOON", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "MORE THAN 10× WIDER IN THE SKY THAN TODAY", win(t, a0 + 1.8, b0, 0.8), (120, 140, 20), (W / 2, 296, 19), col=AMB)
    # today's Moon at the same angular scale
    al = win(t, a0 + 4.0, b0, 0.8)
    tx, ty, tr = (1660, 250, 395 / 11.0) if not V else (935, 480, 400 / 11.0)
    if al > 0:
        tm = np.zeros((H, W, 3), F32); draw_moon(tm, tx, ty, tr, M_NEAR, norm([0.3, 0.3, 0.9]), exposure=1.1)
        img += tm * al
        T.put((tx, ty + tr + 16), "TODAY'S MOON", 16 if not V else 17, al, anchor="c"); T.put((tx, ty + tr + 40), "SAME SCALE", 15 if not V else 16, al, col=DIM, anchor="c")
    af = win(t, a0 + 1.0, b0)
    if V: foot(T, "ARTIST'S IMPRESSION  ·  THE EARLY SURFACE IS UNKNOWN (TODAY'S LUNAR MAP IS USED)  ·  THE FIRST SEAS CAME LATER, AS THE MOON RETREATED", af, y=400)
    else:
        T.put((120, 190), "ARTIST'S IMPRESSION  ·  EARLY SURFACE UNKNOWN", 16, af * 0.9, col=DIM); T.put((120, 216), "TODAY'S LUNAR MAP IS USED", 16, af * 0.9, col=DIM); T.put((120, 242), "THE FIRST SEAS CAME LATER", 16, af * 0.9, col=DIM)
    return T.add_to(img)


# ================================================================================================= 10 coincidence
def shot_coin(t, lt):
    a0, b0 = SHOT["coin"]
    def bg(): return render_sky(rot_axis((0, 1, 0), 3.6) @ SKY_R, FL(50), gain=0.5, mw_gain=0.9)
    img = layer("coin_bg", bg).copy()
    sp = sun_sprite()
    p1 = win(t, a0, S['ecl1'] + 6.0, 0.8, 0.8); p2 = win(t, S['ecl1'] + 5.6, S['ecl1'] + 10.6, 0.8, 0.8); p3 = win(t, S['ecl1'] + 10.2, b0 + 1, 0.8, 0.8)
    T = Text(); L = Lines()
    put(T, "A COINCIDENCE", win(t, a0 + 0.6, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    if p1 > 0:
        if not V: sx, sy, sr = 1250, 600, 400
        else: sx, sy, sr = 540, 850, 400
        lay = np.zeros((H, W, 3), F32); put_disc(lay, sp, sx, sy, sr * (1 + 0.02 * (t - a0) / 8)); 
        y_, x_ = np.mgrid[0:H, 0:W].astype(F32); d = np.clip(np.hypot(x_ - sx, y_ - sy) / sr - 1, 0, None)
        lay += (0.5 * np.exp(-d / 0.05) + 0.12 * np.exp(-d / 0.4))[..., None] * np.array([1.0, 0.55, 0.15], F32) * (d > 0)[..., None]
        img += lay * p1
        mx_, my_ = (sx - sr - 210, sy + 40) if not V else (250, sy + sr + 150)
        add_glint(img, mx_, my_, 1.4 * p1, (0.95, 0.95, 1.0), sig=0.85)
        L.circle(mx_, my_, 16, int(170 * p1), 1)
        al = win(t, S['ecl1'] + 1.6, S['ecl1'] + 6.0, 0.7, 0.8)
        T.put((mx_, my_ + 30) if not V else (mx_ + 34, my_ - 12), "THE MOON, TO SCALE" if not V else "THE MOON, TO SCALE  ·  3,474 KM", 18 if not V else 19, al, anchor="c" if not V else "l")
        if not V: T.put((mx_, my_ + 56), "3,474 KM", 16, al, col=DIM, anchor="c")
        put(T, "THE SUN  ·  1,392,000 KM ACROSS", al, (120, 470, 22), (W / 2, 330, 20), col=DIM)
        put(T, "400×", win(t, S['ecl1'] + 2.6, S['ecl1'] + 6.0, 0.6, 0.8), (120, 520, 130), (W / 2, 1300, 0), col=YEL, wt="XL", track=4)
        put(T, "WIDER", win(t, S['ecl1'] + 2.6, S['ecl1'] + 6.0, 0.6, 0.8), (126, 676, 30), None, col=YEL)
        if V: T.put((W / 2, sy + sr + 40), "400× WIDER", 60, win(t, S['ecl1'] + 2.6, S['ecl1'] + 6.0, 0.6, 0.8), col=YEL, anchor="c", wt="XL")
    if p2 > 0:
        # Earth - Moon - Sun distances to scale along one line (sizes not to scale)
        if not V: A = np.array([200.0, 640.0]); B = np.array([1690.0, 640.0])
        else: A = np.array([540.0, 1400.0]); B = np.array([540.0, 520.0])
        d = B - A; Mpt = A + d * 0.065
        L.seg(*A, *B, int(160 * p2), 1)
        lay = np.zeros((H, W, 3), F32); put_disc(lay, sp, B[0], B[1], 150)
        y_, x_ = np.mgrid[0:H, 0:W].astype(F32); dd = np.clip(np.hypot(x_ - B[0], y_ - B[1]) / 150 - 1, 0, None); lay += (0.5 * np.exp(-dd / 0.06) + 0.14 * np.exp(-dd / 0.6))[..., None] * np.array([1.0, 0.55, 0.15], F32) * (dd > 0)[..., None]; img += lay * p2
        e_ = np.zeros((H, W, 3), F32); draw_earth(e_, A[0], A[1], 34, art_M(20, 20), norm([0.4, 0.3, 0.85]), night_gain=0, atmo=0.8)
        draw_moon(e_, Mpt[0], Mpt[1], 9.3, M_NEAR, norm([0.4, 0.3, 0.85]), exposure=1.2); img += e_ * p2
        nrm = np.array([0.0, -1.0]) if not V else np.array([1.0, 0.0])
        L.seg(*(Mpt + nrm * 22), *(Mpt + nrm * 70), int(255 * p2), 1); add_glint(img, Mpt[0] + nrm[0] * 0, Mpt[1], 0.0, (1, 1, 1))
        if not V:
            T.put((A[0], A[1] + 54), "EARTH", 18, p2, anchor="c"); T.put((Mpt[0] + 10, Mpt[1] - 108), "MOON  ·  384,400 KM AWAY", 18, p2, anchor="l")
            T.put((B[0], B[1] + 180), "SUN  ·  149,600,000 KM AWAY", 18, p2, anchor="c")
            T.put((W / 2, 300), "≈ 400× FARTHER", 96, p2, col=YEL, wt="XL", anchor="c", track=5); T.put((W / 2, 420), "(389× ON AVERAGE)  ·  SCHEMATIC, NOT TO SCALE", 19, p2, col=DIM, anchor="c")
        else:
            T.put((A[0] + 56, A[1] - 12), "EARTH", 19, p2, anchor="l"); T.put((Mpt[0] + 84, Mpt[1] - 14), "MOON: 384,400 KM", 19, p2, anchor="l")
            T.put((B[0], B[1] + 170), "SUN: 149.6 MILLION KM", 19, p2, anchor="c")
            T.put((270, 860), "≈ 400×", 84, p2, col=YEL, wt="XL", anchor="c", track=3); T.put((270, 962), "FARTHER", 30, p2, col=YEL, anchor="c"); T.put((270, 1010), "(389× ON AVERAGE)", 18, p2, col=DIM, anchor="c"); T.put((270, 1040), "SCHEMATIC", 17, p2, col=DIM, anchor="c")
    if p3 > 0:
        if not V: c1 = (660, 560); c2 = (1260, 560); r = 215
        else: c1 = (540, 620); c2 = (540, 1130); r = 200
        lay = np.zeros((H, W, 3), F32); put_disc(lay, sp, c1[0], c1[1], r)
        draw_moon(lay, c2[0], c2[1], r * 0.972, M_NEAR, norm([0.2, 0.25, 0.94]), exposure=1.05)
        img += lay * p3
        T.put((c1[0], c1[1] + r + 26), "THE SUN  ·  0.53° WIDE", 21, p3, anchor="c"); T.put((c2[0], c2[1] + r + 26), "THE MOON  ·  0.52° WIDE", 21, p3, anchor="c")
        put(T, "IN OUR SKY, ALMOST EXACTLY THE SAME SIZE", p3, (W / 2, 900, 26, "c"), (W / 2, 1440, 21), col=AMB)
    L.add_to(img, (0.8, 0.86, 1.0), 0.9, 0.4)
    img = bloom(img, 0.85, 0.5)
    foot(T, "AVERAGE APPARENT SIZES  ·  THE SUN IS SHOWN AS THROUGH A SOLAR FILTER (SIMULATED SURFACE DETAIL)", win(t, a0 + 1.0, b0), y=(1034 if not V else 1508))
    return T.add_to(img)


# ================================================================================================= 11 eclipse / 12 annular / 13 future
def _ecl_stars():
    return layer("ecl_stars", lambda: render_sky(rot_axis((0, 1, 0), 4.4) @ SKY_R, FL(12), gain=0.5, mw_gain=0.0, mag_lim=7.5))


def _ecl_geo():
    return ((960, 520, 190) if not V else (540, 900, 200))


def shot_eclipse(t, lt):
    a0, b0 = SHOT["eclipse"]
    cx, cy, Rs = _ecl_geo()
    t2 = S['ecl2'] + 12.9                                         # second contact: "And then, the corona"
    # Moon centre offset (in Sun radii) along a slightly inclined chord; slows into totality
    ratio = 1.035
    tb0 = t2 - 6.2                                               # beads begin
    if t < t2 - 6.6: d = 0.045 + 0.5 * ((t2 - 6.6 - t) / 6.9) ** 1.5
    elif t < t2 - 3.1: d = lerp(0.045, 0.0345, (t - (t2 - 6.6)) / 3.5)
    elif t < t2: d = lerp(0.0345, 0.0222, ((t - (t2 - 3.1)) / 3.1) ** 1.3)
    else: d = 0.0222 * max(0.0, 1 - (t - t2) / 12.0)
    ang = math.radians(28)
    off = (d * Rs * math.cos(ang), -d * Rs * math.sin(ang))
    push = 1 + 0.10 * ss(t2, b0, t)
    img, F = eclipse(cx, cy, Rs, ratio, off, moon_M=art_M(0, 0, roll=20), stars=_ecl_stars(), cor_gain=1.15)
    img = zoom(img, push, cx, cy)
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "TOTAL SOLAR ECLIPSE", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "BAILY'S BEADS", win(t, t2 - 6.3, t2 - 3.0, 0.6, 0.5), (120, 940, 30), (W / 2, 1400, 28), col=TXT)
    put(T, "SUNLIGHT THROUGH LUNAR VALLEYS", win(t, t2 - 5.9, t2 - 3.0, 0.6, 0.5), (120, 986, 19), (W / 2, 1444, 19), col=DIM)
    put(T, "THE DIAMOND RING", win(t, t2 - 2.7, t2 - 0.1, 0.5, 0.4), (120, 940, 30), (W / 2, 1400, 28), col=TXT)
    put(T, "THE CORONA", win(t, t2 + 0.8, b0, 1.0, 0.6), (120, 940, 30), (W / 2, 1370, 28), col=TXT)
    put(T, "THE SUN'S OUTER ATMOSPHERE  ·  TOTALITY LASTS A FEW MINUTES AT MOST", win(t, t2 + 1.8, b0, 1.0, 0.6), (120, 986, 19), (W / 2, 1444, 0), col=DIM)
    if V: T.put((W / 2, 1414), "THE SUN'S OUTER ATMOSPHERE", 19, win(t, t2 + 1.8, b0, 1.0, 0.6), col=DIM, anchor="c")
    foot(T, "SIMULATION  ·  LUNAR LIMB RELIEF EXAGGERATED  ·  NEVER LOOK AT THE SUN WITHOUT PROPER ECLIPSE FILTERS (EXCEPT DURING TOTALITY)" if not V else "SIMULATION  ·  LIMB RELIEF EXAGGERATED  ·  NEVER LOOK AT THE SUN WITHOUT ECLIPSE FILTERS", win(t, a0 + 1.0, b0), y=(1040 if not V else 1508))
    return T.add_to(img)


def shot_annular(t, lt):
    a0, b0 = SHOT["annular"]
    cx, cy, Rs = ((1180, 540, 330) if not V else (540, 930, 340))
    def bg():
        im = np.zeros((H, W, 3), F32); put_disc(im, sun_sprite(), cx, cy, Rs, gain=1.3)
        return im
    img = layer("ann_bg", bg).copy()
    ratio = 0.94
    k = (t - (a0 + 7.0)) / 11.0
    mx_ = cx + Rs * 2.4 * k * 0.42; my_ = cy - Rs * 2.4 * k * 0.10
    yy, xx = np.ogrid[0:H, 0:W]; rm = np.hypot(xx - mx_, yy - my_); th = np.arctan2(-(yy - my_), xx - mx_ + 0 * yy)
    m = np.clip(Rs * ratio * (1 + limb_profile(th)) - rm + 0.5, 0, 1)
    img *= (1 - m[..., None])
    y_, x_ = np.mgrid[0:H, 0:W].astype(F32); d = np.clip(np.hypot(x_ - cx, y_ - cy) / Rs - 1, 0, None)
    img += (0.35 * np.exp(-d / 0.04) + 0.07 * np.exp(-d / 0.5))[..., None] * np.array([1.0, 0.5, 0.12], F32) * (d > 0)[..., None]
    img = bloom(img, 0.7, 0.75)
    T = Text()
    put(T, "ANNULAR ECLIPSE", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "THE “RING OF FIRE”", win(t, a0 + 1.8, b0, 0.8), (120, 140, 20), (W / 2, 296, 20), col=AMB)
    a1 = win(t, S['ecl3'] + 2.4, b0, 0.8)
    put(T, "THE MOON'S APPARENT WIDTH", a1, (120, 420, 20), (W / 2, 1380, 20), col=DIM)
    put(T, "29.4′ – 33.5′", a1, (120, 456, 58), (W / 2, 1412, 50), wt="XL", track=3)
    put(T, "THE SUN'S", a1, (120, 580, 20), None, col=DIM)
    put(T, "31.6′ – 32.7′", a1, (120, 616, 58), None, col=YEL, wt="XL", track=3)
    if V: T.put((W / 2, 1482), "THE SUN'S:  31.6′ – 32.7′", 22, a1, col=YEL, anchor="c")
    put(T, "RINGS ALREADY SLIGHTLY OUTNUMBER TOTAL ECLIPSES", win(t, S['ecl3'] + 5.4, b0, 0.8), (120, 740, 19), None, col=AMB)
    foot(T, "SIMULATED VIEW THROUGH A SOLAR FILTER  ·  ARCMINUTES (′) = SIXTIETHS OF A DEGREE", win(t, a0 + 1.0, b0), y=(1034 if not V else 380))
    return T.add_to(img)


def shot_future(t, lt):
    a0, b0 = SHOT["future"]
    cx, cy, Rs = _ecl_geo()
    if not V: cx = 1240
    k = ss(S['fut1'] + 3.2, S['fut1'] + 12.6, t)
    yrs = 600e6 * k
    ratio = 1.030 - 0.045 * k ** 1.15                               # largest (perigee) Moon shrinking past the Sun's size
    img, F = eclipse(cx, cy, Rs, ratio, (0.0, 0.0), moon_M=art_M(0, 0, roll=20), stars=_ecl_stars(), cor_gain=1.1, spikes=0.0, glare=0.55,
                     sky_day=(0.03, 0.045, 0.085))
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "AS THE MOON RETREATS", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    a1 = win(t, S['fut1'] + 2.4, b0, 0.8)
    put(T, "+" + f"{int(round(yrs / 1e6)) * 1000000:,}", a1, (120, 330, 78), (W / 2, 330, 64), wt="XL", track=3)
    put(T, "YEARS FROM NOW", a1, (126, 426, 22), (W / 2, 412, 21), col=DIM)
    put(T, f"+{yrs * 3.8e-5:,.0f} KM", a1, (120, 520, 78), (W / 2, 1290, 64), col=YEL, wt="XL", track=3)
    put(T, "FARTHER AWAY, AT TODAY'S RATE", a1, (126, 616, 22), (W / 2, 1372, 21), col=DIM)
    a2 = win(t, S['fut1'] + 11.6, b0, 0.9)
    put(T, "THE LAST TOTAL SOLAR ECLIPSE", a2, (120, 740, 30), (W / 2, 1430, 27), col=TXT)
    put(T, "AFTER IT: PARTIAL OR ANNULAR ONLY", a2, (120, 786, 20), (W / 2, 1474, 20), col=AMB)
    foot(T, "ROUGH ESTIMATE: ≈ 600 MILLION YEARS  ·  PUBLISHED FIGURES RANGE TO OVER A BILLION  ·  THE RECESSION RATE IS NOT CONSTANT", win(t, a0 + 1.0, b0), y=(1034 if not V else 540))
    return T.add_to(img)


# ================================================================================================= 14 far future
def shot_far(t, lt):
    a0, b0 = SHOT["far"]; u = lt / (b0 - a0)
    def bg(): return render_sky(rot_axis((0, 1, 0), 5.0) @ SKY_R, FL(50), gain=1.0, mw_gain=2.6)
    img = layer("far_bg", bg).copy()
    rg = ss(S['far1'] + 9.6, S['far1'] + 14.5, t)                    # the red giant rises
    if not V: E = np.array([150.0, 600.0]); ER = 27.0; dirn = np.array([1.0, 0.0]); gx, gy, gr = 2750 - 400 * rg, 1500, 1500
    else: E = np.array([540.0, 520.0]); ER = 15.5; dirn = np.array([0.0, 1.0]); gx, gy, gr = 540, 3350 - 520 * rg, 1500
    if rg > 0:
        lay = np.zeros((H, W, 3), F32); put_disc(lay, sun_sprite(3000, "giant"), gx, gy, gr)
        y_, x_ = np.mgrid[0:H, 0:W].astype(F32); d = np.clip(np.hypot(x_ - gx, y_ - gy) / gr - 1, 0, None)
        lay += (0.55 * np.exp(-d / 0.02) + 0.22 * np.exp(-d / 0.12))[..., None] * np.array([1.0, 0.30, 0.08], F32) * (d > 0)[..., None]
        img = img * (1 - 0.6 * rg) + lay * rg
    Mo = E + dirn * ER * 60.27
    sunv = norm([0.5, 0.4, 0.75]) if rg < 0.5 else norm([0.6, -0.5, 0.6]) if not V else norm([0.1, -0.8, 0.6])
    tint = lerp(np.ones(3), np.array([1.0, 0.55, 0.35]), rg)
    e_ = np.zeros((H, W, 3), F32); draw_earth(e_, E[0], E[1], ER, art_M(-60 + t * 2, 15, roll=-20), norm([0.5, 0.4, 0.75]), night_gain=0, atmo=0.7)
    draw_moon(e_, Mo[0], Mo[1], ER * 0.2727, M_NEAR, norm([0.5, 0.4, 0.75]), exposure=1.2)
    yy, xx = np.ogrid[0:H, 0:W]; msk = (np.clip(ER + 1 - np.hypot(xx - E[0], yy - E[1]), 0, 1) + np.clip(ER * 0.2727 + 1 - np.hypot(xx - Mo[0], yy - Mo[1]), 0, 1))[..., None]
    img = img * (1 - msk) + e_ * tint.astype(F32)
    L = Lines(); L.seg(*(E + dirn * (ER + 10)), *(Mo - dirn * (ER * 0.27 + 10)), 110, 1); L.add_to(img, (0.75, 0.82, 1.0), 0.8, 0.3)
    img = bloom(img, 0.8, 0.6)
    T = Text()
    put(T, "WILL THE MOON ESCAPE?", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "NO.", win(t, S['far1'] + 2.2, b0, 0.5), (120, 150, 92), (W / 2, 300, 80), col=YEL, wt="XL", track=6)
    if not V:
        T.put((E[0], E[1] + 52), "EARTH", 18, win(t, a0 + 1.4, b0), anchor="c"); T.put((Mo[0], Mo[1] + 34), "MOON", 18, win(t, a0 + 1.4, b0), anchor="c")
        T.put(((E[0] + Mo[0]) / 2, E[1] - 44), "384,400 KM  ·  SIZES AND DISTANCE TO SCALE", 18, win(t, a0 + 2.0, b0), col=DIM, anchor="c")
    else:
        T.put((E[0] + 40, E[1] - 12), "EARTH", 19, win(t, a0 + 1.4, b0), anchor="l"); T.put((Mo[0] + 30, Mo[1] - 12), "MOON", 19, win(t, a0 + 1.4, b0), anchor="l")
        T.put((E[0] + 40, (E[1] + Mo[1]) / 2 - 12), "384,400 KM  ·  TO SCALE", 19, win(t, a0 + 2.0, b0), col=DIM, anchor="l")
    a1 = win(t, S['far1'] + 6.6, b0, 0.8)
    put(T, "≈ 50 BILLION YEARS", a1, (120, 760, 52), (W / 2, 1010, 0), wt="XL", track=3)
    put(T, "FOR EARTH'S DAY TO MATCH THE MOON'S MONTH (ROUGH ESTIMATE)", a1, (124, 828, 19), None, col=DIM)
    a2 = win(t, S['far1'] + 10.6, b0, 0.8)
    put(T, "≈ 5 BILLION YEARS", a2, (120, 890, 52), None, col=RED, wt="XL", track=3)
    put(T, "UNTIL THE SUN SWELLS INTO A RED GIANT", a2, (124, 958, 19), None, col=DIM)
    if V:
        T.put((90, 760), "≈ 50 BILLION YEARS", 40, a1, wt="XL", anchor="l", track=2); T.put((92, 814), "FOR EARTH'S DAY TO", 18, a1, col=DIM, anchor="l"); T.put((92, 842), "MATCH THE MOON'S MONTH", 18, a1, col=DIM, anchor="l")
        T.put((90, 930), "≈ 5 BILLION YEARS", 40, a2, col=RED, wt="XL", anchor="l", track=2); T.put((92, 984), "UNTIL THE SUN SWELLS", 18, a2, col=DIM, anchor="l"); T.put((92, 1012), "INTO A RED GIANT", 18, a2, col=DIM, anchor="l")
    if V: foot(T, "EARTH, MOON AND THEIR SEPARATION TO SCALE  ·  RED GIANT: ARTIST'S IMPRESSION, NOT TO SCALE", win(t, a0 + 1.0, b0), y=440)
    else: T.put((120, 1034), "EARTH, MOON AND SEPARATION TO SCALE  ·  RED GIANT: ARTIST'S IMPRESSION", 16, win(t, a0 + 1.0, b0) * 0.9, col=DIM)
    return T.add_to(img)


# ================================================================================================= 15 window
def shot_window(t, lt):
    a0, b0 = SHOT["window"]
    cx, cy, Rs = ((1420, 330, 120) if not V else (540, 560, 150))
    def bg():
        im, F = eclipse(cx, cy, Rs, 1.03, (0.0, 0.0), moon_M=art_M(0, 0, roll=20), stars=_ecl_stars(), cor_gain=1.1)
        return bloom(im, 0.8, 0.5)
    img = layer("win_bg", bg) * (0.85 - 0.25 * ss(a0, a0 + 3, t))
    img = zoom(img, 1 + 0.04 * lt / (b0 - a0), cx, cy)
    # chart: apparent width of the Moon relative to the Sun, vs time
    if not V: X0, X1, Y0, Y1 = 170, 1750, 880, 560            # Y0 = ratio 0.8 (bottom), Y1 = ratio 1.6 (top)
    else: X0, X1, Y0, Y1 = 110, 990, 1420, 900
    T0, T1 = -4.5, 1.5; RA, RB = 0.8, 1.6
    def X(tt): return X0 + (X1 - X0) * (tt - T0) / (T1 - T0)
    def Y(r): return Y0 + (Y1 - Y0) * (np.clip(r, RA - 0.1, 3.4) - RA) / (RB - RA)
    tt = np.linspace(T0 + 0.02, T1, 500)
    dist = np.where(tt < 0, (np.clip(1 + tt / 4.56, 1e-4, None)) ** 0.42, 1 + tt * 3.8e-5 * 1e9 / 384400e0 / 1e0 * 1.0)     # schematic past; linear future (3.8 cm/yr)
    dist = np.where(tt < 0, dist, 1 + tt * 1e9 * 3.8e-5 / 384400.0)
    hi = 1.062 / dist; lo = 0.905 / dist
    rev = ss(a0 + 0.5, a0 + 3.6, t)
    n = max(2, int(len(tt) * rev))
    L = Lines(); Lb = Lines(); Ly = Lines()
    L.seg(X0, Y(1.0), X1, Y(1.0), 255, 1)
    top = RB + 0.12; hid = np.where(hi > top, np.nan, hi); lod = np.where(lo > top, np.nan, lo); hi = np.minimum(hi, top); lo = np.minimum(lo, top)
    Lb.poly(X(tt[:n]), Y(hid[:n]), 255, 2); Lb.poly(X(tt[:n]), Y(lod[:n]), 150, 1)
    Lb.l[:] = (Lb.l.astype(F32) * np.clip((np.arange(H, dtype=F32)[:, None] - (Y(top) + 6)) / 90.0, 0, 1)).astype(np.uint8)
    # band fill
    band = np.zeros((H, W), np.uint8)
    pts = np.concatenate([np.stack([X(tt[:n]), Y(hi[:n])], 1), np.stack([X(tt[:n]), Y(lo[:n])], 1)[::-1]]).astype(np.int32)
    cv2.fillPoly(band, [pts], 255, cv2.LINE_AA)
    bf = band.astype(F32) / 255
    xx = np.arange(W, dtype=F32)[None, :]; yy = np.arange(H, dtype=F32)[:, None]
    bf = bf * np.clip((yy - (Y(top) + 6)) / 90.0, 0, 1) * np.clip((X(tt[n - 1]) - xx) / 46.0, 0, 1) if rev < 1 else bf * np.clip((yy - (Y(top) + 6)) / 90.0, 0, 1)
    above = (yy < Y(1.0)).astype(F32)
    img = img * (1 - 0.35 * bf[..., None])
    img += (bf * above)[..., None] * np.array([0.30, 0.50, 0.95], F32) * 0.34 + (bf * (1 - above))[..., None] * np.array([1.0, 0.50, 0.12], F32) * 0.26
    aN = win(t, a0 + 4.6, b0, 0.8)
    Ly.seg(X(0), Y0 + 12, X(0), Y1 - 12, int(255 * aN), 1)
    t_end = (1.062 - 1) * 384400.0 / 3.8e-5 / 1e9
    aE = win(t, S['pay1'] + 8.0, b0, 0.8)
    Ly.seg(X(t_end), Y(1.0) - 46, X(t_end), Y(1.0) + 46, int(255 * aE), 2)
    L.add_to(img, (0.85, 0.9, 1.0), 0.75, 0.3); Lb.add_to(img, (0.55, 0.75, 1.0), 1.0, 0.5); Ly.add_to(img, np.array(YEL) / 255, 1.0, 0.5)
    T = Text()
    put(T, "THE WINDOW", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "THE MOON'S APPARENT WIDTH, COMPARED WITH THE SUN'S", win(t, a0 + 1.6, b0, 0.8), (120, 140, 20), (W / 2, 296, 0), col=AMB)
    if V: T.put((W / 2, 296), "THE MOON'S APPARENT WIDTH vs THE SUN'S", 19, win(t, a0 + 1.6, b0, 0.8), col=AMB, anchor="c")
    sz = 17 if not V else 18
    al = win(t, a0 + 2.0, b0, 0.8)
    T.put((X1 + 8 if not V else X0, Y(1.0) - 10 if not V else Y(1.0) + 10), "SUN" if not V else "= THE SUN'S WIDTH", sz, al, anchor="l")
    for tv, lb in ((-4, "4"), (-3, "3"), (-2, "2"), (-1, "1")):
        T.put((X(tv), Y0 + 20), lb + (" BILLION YEARS AGO" if tv == -4 and not V else " BN" if tv == -4 else ""), sz, al, col=DIM, anchor="c")
    T.put((X(1.0), Y0 + 20), "+1" + (" BILLION" if not V else " BN"), sz, al, col=DIM, anchor="c")
    T.put((X(0), Y1 - 44), "NOW", sz + 3, aN, col=YEL, anchor="c", wt="R")
    T.put((X(-4.4), Y(1.12)) if not V else (X(-4.4), Y(1.08)), "MOON WIDER THAN THE SUN:" if V else "MOON WIDER THAN THE SUN: TOTAL ECLIPSES POSSIBLE", sz, win(t, S['pay1'] + 2.4, b0, 0.8), col=COOL, anchor="l")
    if V: T.put((X(-4.4), Y(1.08) + 28), "TOTAL ECLIPSES POSSIBLE", sz, win(t, S['pay1'] + 2.4, b0, 0.8), col=COOL, anchor="l")
    T.put((X(-2.6), Y(1.5)), "↑ FAR LARGER AT FIRST", sz, 0 *  win(t, S['pay1'] + 2.4, b0, 0.8), col=COOL, anchor="c")
    T.put((X(1.5) if not V else X1, Y(0.86) + 6), "TOO SMALL: RINGS ONLY", sz, win(t, S['pay1'] + 6.2, b0, 0.8), col=AMB, anchor="r")
    T.put((X(t_end) + (14 if not V else -10), Y(1.0) - 78 if not V else Y(1.0) - 84), "LAST TOTAL ECLIPSE  ≈ +0.6 BN" if not V else "LAST TOTAL ≈ +0.6 BN", sz, aE, col=YEL, anchor="l" if not V else "r")
    foot(T, "SCHEMATIC  ·  BAND = THE MOON'S RANGE FROM FARTHEST TO NEAREST  ·  PAST CURVE ILLUSTRATIVE; FUTURE AT TODAY'S 3.8 CM / YEAR", win(t, a0 + 1.0, b0), y=(1034 if not V else 1508))
    return T.add_to(img)


# ================================================================================================= 16 leave / 17 shadow / 18 final
def shot_leave(t, lt):
    a0, b0 = SHOT["leave"]; u = lt / (b0 - a0)
    def bg(): return render_sky(rot_axis((0, 1, 0), 1.3) @ SKY_R, FL(54), gain=0.9, mw_gain=1.4)
    img = layer("leave_bg", bg).copy()
    if not V: ex, ey, ER = 420, 1180, 900; m0 = (1330, 360, 74); m1 = (1420, 310, 56)
    else: ex, ey, ER = 400, 2050, 900; m0 = (640, 620, 70); m1 = (720, 520, 52)
    mx_, my_, mr = [lerp(a, b, u) for a, b in zip(m0, m1)]
    sunv = norm([0.55, 0.45, 0.5])
    draw_moon(img, mx_, my_, mr, art_M(10, 0, roll=-15), sunv, exposure=1.15)
    draw_earth(img, ex, ey, ER, art_M(-70 + t * 0.8, 35, roll=20), sunv, t=t, night_gain=1.4, glint=0.18)
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "+3.8 CM", win(t, S['pay2'] + 1.0, b0, 0.6, 0.5), (1120, 560, 104), (W / 2, 860, 96), col=YEL, wt="XL", track=5)
    put(T, "THIS YEAR.  AND THE NEXT.", win(t, S['pay2'] + 2.6, b0, 0.6, 0.5), (1126, 684, 24), (W / 2, 980, 23))
    foot(T, "NOT TO SCALE", win(t, a0 + 0.6, b0), y=(1034 if not V else 300))
    return T.add_to(img)


def shot_shadow(t, lt):
    a0, b0 = SHOT["shadow"]; u = lt / (b0 - a0)
    def bg(): return render_sky(rot_axis((0, 1, 0), 0.2) @ SKY_R, FL(50), gain=0.7, mw_gain=1.2)
    img = layer("shadow_bg", bg).copy()
    if not V: ex, ey, ER = 960, 600, lerp(400, 440, u)
    else: ex, ey, ER = 540, 960, lerp(420, 455, u)
    sunv = norm([0.18, 0.22, 0.95])
    M = art_M(-96 + (t - a0) * 0.6, 30, roll=-12)
    draw_earth(img, ex, ey, ER, M, sunv, t=t, night_gain=0.6, glint=0.3)
    # the Moon's shadow: penumbra + small umbra, crossing slowly (the 8 April 2024 track over North America, approximate)
    k = (t - a0) / (b0 - a0)
    c = M.T @ lonlat(lerp(-108, -78, k), lerp(23, 42, k))
    g = _grid(ex, ey, ER, 2); x0, y0, x1, y1, uu, vv = g
    zz = np.sqrt(np.clip(1 - uu * uu - vv * vv, 0, 1)); ang = np.arccos(np.clip(uu * c[0] + vv * c[1] + zz * c[2], -1, 1))
    dark = 0.72 * np.exp(-(ang / 0.36) ** 2.4) + 0.27 * np.exp(-(ang / 0.06) ** 2)
    inside = (uu * uu + vv * vv < 1)
    img[y0:y1, x0:x1] *= (1 - dark * inside)[..., None]
    img = bloom(img, 0.8, 0.5)
    T = Text()
    put(T, "THE MOON'S SHADOW", win(t, a0 + 0.8, b0, 0.8), (120, 96, 27), (W / 2, 250, 26))
    put(T, "TOTALITY IS ONLY SEEN FROM INSIDE THE SMALL DARK CORE", win(t, a0 + 1.8, b0, 0.8), (120, 140, 20), (W / 2, 296, 0), col=AMB)
    if V: T.put((W / 2, 296), "TOTALITY: ONLY INSIDE THE DARK CORE", 19, win(t, a0 + 1.8, b0, 0.8), col=AMB, anchor="c")
    foot(T, "ILLUSTRATION  ·  SHADOW SIZE AND PATH APPROXIMATE (AFTER THE ECLIPSE OF 8 APRIL 2024)", win(t, a0 + 1.0, b0), y=(1034 if not V else 1508))
    return T.add_to(img)


def shot_final(t, lt):
    a0, b0 = SHOT["final"]; u = lt / (b0 - a0)
    cx, cy, Rs = ((960, 470, 150) if not V else (540, 800, 170))
    def bg():
        im, F = eclipse(cx, cy, Rs, 1.03, (0.0, 0.0), moon_M=art_M(0, 0, roll=20), stars=_ecl_stars(), cor_gain=1.15)
        return bloom(im, 0.8, 0.5)
    img = zoom(layer("final_bg", bg), 1 + 0.06 * u, cx, cy)
    T = Text()
    put(T, "IT WILL NOT ALWAYS BE THERE.", win(t, a0 + 0.6, b0 - 0.2, 1.0, 1.2), (W / 2, 800, 34, "c"), (W / 2, 1250, 29, "c"), wt="L")
    put(T, "THE MOON IS LEAVING", win(t, a0 + 1.6, b0 - 0.2, 1.0, 1.2), (W / 2, 868, 22, "c"), (W / 2, 1316, 22, "c"), col=AMB)
    put(T, "MOON: NASA LRO / LOLA  ·  EARTH: NASA BLUE MARBLE  ·  STARS: REAL CATALOGUE  ·  ECLIPSE AND CORONA SIMULATED", win(t, a0 + 2.2, b0 - 0.2, 1.0, 1.2) * 0.8, (W / 2, 1020, 15, "c"), None, col=DIM)
    if V:
        T.put((W / 2, 1440), "MOON: NASA LRO / LOLA  ·  EARTH: NASA BLUE MARBLE", 17, win(t, a0 + 2.2, b0 - 0.2, 1.0, 1.2) * 0.8, col=DIM, anchor="c")
        T.put((W / 2, 1468), "ECLIPSE AND CORONA SIMULATED", 17, win(t, a0 + 2.2, b0 - 0.2, 1.0, 1.2) * 0.8, col=DIM, anchor="c")
    return T.add_to(img)


FUNCS = {"hook": shot_hook, "reflector": shot_reflector, "obs": shot_obs, "ret": shot_ret, "tides": shot_tides, "day": shot_day, "past": shot_past,
         "coral": shot_coral, "origin": shot_origin, "ancient": shot_ancient, "coin": shot_coin, "eclipse": shot_eclipse, "annular": shot_annular,
         "future": shot_future, "far": shot_far, "window": shot_window, "leave": shot_leave, "shadow": shot_shadow, "final": shot_final}


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
    g = ss(0.0, 0.9, t) * (1 - ss(TL.DUR - 2.4, TL.DUR - 0.3, t))
    return np.clip(out * g, 0, 1)


def main():
    sfx = "_v" if V else ""
    if sys.argv[1] == "--png":
        os.makedirs(SCR + "/chk", exist_ok=True)
        for s in sys.argv[2:]:
            t0 = time.time(); im = frame(float(s))
            cv2.imwrite(f"{SCR}/chk/f{sfx}_{float(s):06.1f}.jpg", to8(im)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92]); print(s, round(time.time() - t0, 2), "s", flush=True)
        return
    t0, t1 = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    os.makedirs(SCR + "/seg" + sfx, exist_ok=True); out = f"{SCR}/seg{sfx}/seg_{f0:05d}.mp4"
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
