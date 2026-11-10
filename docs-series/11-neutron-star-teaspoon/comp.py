"""ONE TEASPOON OF A NEUTRON STAR - frame compositor (numpy + OpenCV + PIL). Every shot is a function of film time.
The same file renders 16:9 (default) and the 9:16 recomposition (NS_VERT=1): hv(h, v) picks the layout value.

Usage: python3 comp.py T0 T1            -> $SCR/seg[_v]/seg_<frame0>.mp4 (x264 crf 14, silent)
       python3 comp.py --png t1 t2 ...  -> $SCR/chk/[v]f_<t>.jpg stills
"""
import os, sys, math, subprocess, time, functools, json, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ns import *
import timeline as TL

S = TL.START
TXT = (232, 236, 242); DIM = (176, 186, 200); AMB = (255, 200, 120); COOL = (150, 205, 255); RED = (255, 120, 95); YEL = (255, 214, 80)
_cache = {}


def hv(h, v): return v if VERT else h


def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]


def art_M(lon_c, lat_c, roll=0.0):
    """Earth orientation: body point (lon_c, lat_c) faces the viewer, north up (then rolled). Returns body <- camera."""
    lo, la = math.radians(lon_c), math.radians(lat_c)
    c = np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)]); R = look_at(c * 10, (0, 0, 0))
    if roll: R = rot_axis((0, 0, 1), math.radians(roll)) @ R
    return R.T


def star_M(phase, chi=35.0, incl=20.0, roll=12.0):
    """spinning star with an inclined magnetic axis. Returns (body<-camera, camera<-body); body z = magnetic axis"""
    P = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
    Sm = rot_axis((0, 0, 1), math.radians(roll)) @ rot_axis((1, 0, 0), math.radians(incl)) @ P
    Mc = Sm @ rot_axis((0, 0, 1), phase) @ rot_axis((0, 1, 0), math.radians(chi))
    return Mc.T, Mc


# ================================================================================================= type helpers
def cap(T, t, a, b, lines, y, x=None, size=None, col=TXT, anchor=None, gap=1.5, wt="L", stagger=0.3):
    x = hv(120, W / 2) if x is None else x; anchor = anchor or hv("l", "c"); size = size or hv(30, 40)
    for i, s in enumerate(lines):
        T.put((x, y + i * size * gap), s, size, win(t, a + i * stagger, b, 0.8, 0.6), col=col, anchor=anchor, wt=wt)


def note(T, t, a, b, s, col=DIM, top=False):
    """small note (what is to scale / illustrative). top=True: in the dark sky (for shots whose lower part is the bright Earth)"""
    if isinstance(s, str): s = [s]
    for i, ln in enumerate(s):
        if top: xy = hv((W - 120, 60 + i * 30), (W / 2, 1352 - (len(s) - 1 - i) * 36)); anc = hv("r", "c")
        else: xy = (hv(120, W / 2), hv(1012, 1486) - (len(s) - 1 - i) * hv(30, 36)); anc = hv("l", "c")
        T.put(xy, ln, hv(19, 24), win(t, a, b, 0.8, 0.6) * 0.95, col=col, anchor=anc, wt="R")


def banner(T, t, a, b, s, col=AMB):
    """persistent top label for hypotheticals"""
    al = win(t, a, b, 0.8, 0.6); y = hv(64, 252); x = hv(120, W / 2); size = hv(22, 28)
    T.put((x, y), s, size, al, col=col, anchor=hv("l", "c"), wt="M")
    w = text_w(s, size, size * 0.16, "M"); x0 = x if not VERT else x - w / 2
    T.line((x0, y + size * 1.55), (x0 + w, y + size * 1.55), al * 0.8, col)


def tag(T, x, y, s, al, col=TXT, size=None, dx=26, dy=-34, anchor="l"):
    size = size or hv(19, 24)
    if al <= 0.004: return
    T.line((x + dx * 0.25, y + dy * 0.25), (x + dx, y + dy), al * 0.7, col)
    T.put((x + dx + (8 if anchor == "l" else -8), y + dy - size * 0.75), s, size, al, col=col, anchor=anchor, wt="R")


def glare(img, x, y, amp, s=1.0, col=(0.72, 0.86, 1.0)):
    add_glint(img, x, y, 3.0 * amp, col, sig=9 * s); add_glint(img, x, y, 1.6 * amp, col, sig=30 * s)
    for ang in (60, 120):
        k = cv2.getRotationMatrix2D((x, y), ang, 1.0); tmp = np.zeros((161, 161, 3), F32)
    add_glint(img, x, y, 0.5 * amp, (0.55, 0.75, 1.0), sig=2.0 * s, streak=40 * s)
    add_glint(img, x, y, 0.30 * amp, (0.4, 0.6, 1.0), sig=85 * s)
    add_glint(img, x, y, 0.9 * amp, (0.5, 0.72, 1.0), sig=2.6 * s, streak=95 * s)


# ================================================================================================= sprites
_avail = {}


def _frames(name):
    if name not in _avail or len(_avail[name]) < 80:
        _avail[name] = sorted(int(os.path.basename(f)[2:5]) for f in glob.glob(f"{SCR}/spr/{name}/f_*.png"))
    return _avail[name]


@functools.lru_cache(maxsize=10)
def spr_frame(name, i):
    a = cv2.imread(f"{SCR}/spr/{name}/f_{i:03d}.png", cv2.IMREAD_UNCHANGED).astype(F32) / 65535
    a = a[..., [2, 1, 0, 3]]; a[..., :3] *= a[..., 3:4]
    return a


def spr_at(name, u, n=80):
    """sprite at fraction u of the rendered move, blending between the nearest rendered frames"""
    fr = _frames(name)
    if not fr: return spr_at("spoon_on", u) if name == "spoon_off" else np.zeros((1200, 1200, 4), F32)
    x = min(max(u, 0.0), 1.0) * (n - 1)
    lo = max([f for f in fr if f <= x] or [fr[0]]); hi = min([f for f in fr if f >= x] or [fr[-1]])
    if hi == lo: return spr_frame(name, lo)
    f = (x - lo) / (hi - lo)
    return spr_frame(name, lo) * (1 - f) + spr_frame(name, hi) * f


@functools.lru_cache(None)
def _bead():
    d = json.load(open(SCR + "/spr/spoon_on/bead.json")); return np.array([d[str(i)] for i in range(80)])


def spoon(img, u, bx, by, scale, angle=0.0, bead=1.0, gain=1.0, alpha=1.0):
    """spoon sprite placed so that the bead sits at (bx, by)"""
    spr = spr_at("spoon_off", u) if bead <= 0.002 else (spr_at("spoon_on", u) if bead >= 0.998 else spr_at("spoon_off", u) * (1 - bead) + spr_at("spoon_on", u) * bead)
    x = min(max(u, 0.0), 1.0) * 79; i = int(min(math.floor(x), 78)); p = _bead()[i] * (1 - (x - i)) + _bead()[i + 1] * (x - i)
    Mx = cv2.getRotationMatrix2D((0, 0), angle, scale); o = Mx[:, :2] @ np.array([p[0] - 900, p[1] - 600])
    put_sprite(img, spr, bx - o[0], by - o[1], scale, angle, gain, alpha)


# ================================================================================================= shared plates
def earth_plate(t, key, apex=None, lon0=15.0, night=0.0, exposure=1.0):
    """star field + the Earth's limb across the bottom of the frame (orthographic sphere, slowly turning)"""
    R = 2400.0; apex = hv(770, 1420) if apex is None else apex
    skyb = cached(("sky", key), lambda: render_sky(look_at((0, 0, 0), norm([0.5, 0.8, 0.33])), FL(46), gain=0.9, mw_gain=1.6))
    img = skyb.copy()
    draw_earth(img, W / 2, apex + R, R, art_M(lon0 + 0.12 * t, -38, roll=-6), norm([-0.35, 0.55, 0.75]), t=t, night_gain=night, exposure=exposure)
    return img


def ns_scene(key, cx, cy, Rapp, Mb, fov=40.0, sky_dir=(0.25, -0.93, -0.25), u=U_NS, kind="ns", drift=(0.0, 0.0), gain=1.0, lines=0.0, beam=0.0,
             blur=0, lens=1.0, Mc=None, twist=0.0, shells=(1.8, 2.6, 3.8, 5.6, 8.5), naz=10, lcol=(0.45, 0.75, 1.0), grid=0.0, horizon=0.0,
             halo_col=(0.35, 0.6, 1.0), mw=2.2, bhalf=0.16, sky_gain=1.0, halo=1.0):
    f = FL(fov); m = 900
    skyc = cached(("skyL", key), lambda: render_sky(look_at((0, 0, 0), norm(sky_dir)), f, gain=1.0, mw_gain=mw, size=(W + 2 * m, H + 2 * m)))
    k = lens_k(Rapp, f, max(u, 1e-4)) * lens
    img = lens_sky(skyc, cx, cy, k, off=(m + drift[0], m + drift[1])) * sky_gain
    Rtrue = Rapp * math.sqrt(1 - u)
    if Mc is None: Mc = Mb.T
    if beam > 0:
        b = beams(cx, cy, Rtrue, Mc @ np.array([0, 0, 1.0]), half=bhalf, occ=Rapp / Rtrue)
        img += b[..., None] * np.array([0.50, 0.72, 1.0], F32) * beam + (b ** 2)[..., None] * np.array([0.5, 0.5, 0.6], F32) * beam * 0.35
    if lines > 0: field_lines(img, cx, cy, Rtrue, Rapp, Mc, gain=lines, twist=twist, shells=shells, naz=naz, col=lcol)
    draw_star(img, cx, cy, Rapp, Mb, u=u, kind=kind, gain=gain, blur=blur, grid=grid, horizon=horizon, halo_col=halo_col, halo=halo)
    return img


SN_COLS = [(0.62, 0.82, 1.0), (0.30, 0.85, 0.78), (1.0, 0.60, 0.25), (1.0, 0.32, 0.12), (0.85, 0.22, 0.18), (0.45, 0.38, 0.95)]
BLUE_COLS = [(0.70, 0.86, 1.0), (0.45, 0.70, 1.0), (0.55, 0.60, 1.0), (0.75, 0.80, 1.0), (0.40, 0.55, 1.0), (0.9, 0.9, 1.0)]
RED_COLS = [(1.0, 0.42, 0.20), (0.95, 0.22, 0.14), (1.0, 0.55, 0.25), (0.85, 0.16, 0.22), (0.75, 0.20, 0.45), (1.0, 0.70, 0.40)]
FIRE_COLS = [(0.85, 0.92, 1.0), (1.0, 0.85, 0.55), (1.0, 0.55, 0.20), (1.0, 0.35, 0.12), (0.9, 0.25, 0.10), (1.0, 0.75, 0.45)]


# ================================================================================================= 1  hook
def spoon_pose():
    """(bead x, bead y, scale, angle) of the hero spoon over the Earth plate"""
    return hv((600, 520, 0.96, 0.0), (330, 930, 0.82, 52.0))


def shot_hook(t, lt):
    img = earth_plate(t, "hook")
    bx, by, sc, ang = spoon_pose(); u = lt / 21.6 * 0.55
    bx += lt * hv(2.2, 0.8); by -= lt * hv(0.9, 1.6)
    b = ss(2.5, 3.9, t)
    spoon(img, u, bx, by, sc, ang, bead=b)
    fl = 1 + 0.05 * math.sin(t * 9.0) + 0.03 * math.sin(t * 23.0)
    glare(img, bx, by - 6 * sc, 0.55 * b * fl, s=hv(1.0, 1.0))
    img = bloom(img, 0.72, 0.6)
    T = Text()
    T.put(hv((116, 96), (W / 2, 250)), "1 TEASPOON", hv(92, 96), win(t, 0.9, 8.9, 0.7, 0.7), anchor=hv("l", "c"), wt="XL", track=hv(12, 9))
    T.put(hv((122, 214), (W / 2, 372)), "5 mL OF NEUTRON-STAR MATTER", hv(27, 30), win(t, 2.8, 8.9, 0.8, 0.7), col=COOL, anchor=hv("l", "c"))
    T.put(hv((122, 264), (W / 2, 426)), "≈ A MOUNTAIN", hv(40, 46), win(t, 6.3, 8.9, 0.7, 0.7), col=YEL, anchor=hv("l", "c"), wt="R")
    T.put(hv((118, 110), (W / 2, 260)), "BILLIONS OF TONNES", hv(54, 60), win(t, 10.0, 17.4, 0.7, 0.7), anchor=hv("l", "c"), wt="XL")
    cap(T, t, 12.0, 14.2, hv(["MORE THAN EVERY HUMAN ALIVE, COMBINED"], ["MORE THAN EVERY HUMAN", "ALIVE, COMBINED"]), hv(196, 356), x=hv(122, W / 2), size=hv(26, 32), col=COOL)
    cap(T, t, 14.6, 20.9, hv(["SO WHAT WOULD IT DO, IF YOU BROUGHT IT HOME?"], ["SO WHAT WOULD IT DO,", "IF YOU BROUGHT IT HOME?"]), hv(196, 1200), x=hv(122, W / 2), size=hv(30, 38))
    note(T, t, 1.5, 20.9, "ILLUSTRATION · BEAD AND EARTH NOT TO SCALE", top=True)
    return T.add_to(img)


# ================================================================================================= 2  title
def shot_title(t, lt):
    Mb, Mc = star_M(0.5 + 0.05 * lt, chi=28, incl=24, roll=-14)
    R = hv(250, 240) * (1 + 0.012 * lt)
    img = ns_scene("title", W / 2, hv(480, 760), R, Mb, Mc=Mc, lines=0.20, beam=0.30, drift=(lt * 5, lt * 1.5))
    img = bloom(img, 0.7, 0.75)
    T = Text(); a = win(t, 22.2, 26.5, 0.8, 0.6)
    T.put((W / 2, hv(866, 1210)), "ONE TEASPOON", hv(64, 70), a, anchor="c", wt="XL", track=hv(16, 10))
    T.put((W / 2, hv(952, 1310)), "OF A NEUTRON STAR", hv(34, 42), a, anchor="c", col=COOL, track=hv(12, 8))
    return T.add_to(img)


# ================================================================================================= 3-4  giant star -> supernova
def rsg_sky():
    return cached(("sky", "rsg"), lambda: render_sky(look_at((0, 0, 0), norm([-0.6, 0.5, 0.62])), FL(50), gain=0.7, mw_gain=1.2))


def rsg_base(t, cx, cy, R, gain=1.0):
    img = rsg_sky().copy()
    cor = cached(("expl", "cor"), lambda: expl_layers(5, kind="ball"))
    draw_expl(img, cor, cx, cy, R * 1.55, [(1.0, 0.42, 0.12)] * 6, [0.10 * gain, 0.08 * gain, 0.07 * gain, 0, 0, 0], rot=t * 0.35)
    add_glint(img, cx, cy, 0.20 * gain, (1.0, 0.45, 0.15), sig=R * 0.85)
    Mb = rot_axis((0, 1, 0), 0.012 * t) @ rot_axis((1, 0, 0), -0.4)
    draw_star(img, cx, cy, R, Mb, u=0.0, kind="rsg", gain=1.25 * gain, limb=0.6, halo_col=(1.0, 0.40, 0.12), halo=1.5)
    return img


def shot_giant(t, lt):
    R = hv(380, 400) * (1 + 0.010 * lt); cx, cy = hv((W * 0.60, 520), (W / 2, 780))
    img = bloom(rsg_base(t, cx, cy, R), 0.75, 0.7)
    T = Text()
    cap(T, t, 27.4, 33.6, hv(["A MASSIVE STAR", "AT LEAST 8 × THE MASS OF THE SUN"], ["A MASSIVE STAR", "AT LEAST 8 × THE SUN'S MASS"]), hv(880, 1300))
    cap(T, t, 34.4, 39.8, hv(["ITS CORE FILLS WITH IRON", "FUSING IRON RELEASES NO ENERGY"], ["ITS CORE FILLS WITH IRON", "FUSING IRON RELEASES", "NO ENERGY"]), hv(880, 1280))
    note(T, t, 27.6, 39.8, "ILLUSTRATION OF A RED SUPERGIANT")
    return T.add_to(img)


def shot_sn(t, lt):
    zo = ss(45.5, 51.0, t)
    R0 = hv(380, 400) * (1 + 0.010 * 13.4) * lerp(1.0, 0.42, zo); cx, cy = hv((W * 0.60, 520), (W / 2, 780))
    cx = lerp(cx, W / 2, zo); cy = lerp(cy, hv(520, 800), zo)
    tb = 50.2                                              # shock breaks out of the star
    tau = t - tb
    dim = 1 - 0.45 * ss(40.4, 43.5, t)
    star_a = 1 - ss(0.0, 1.6, tau)
    img = rsg_base(t, cx, cy, R0, gain=dim * star_a + 0.001) if star_a > 0.004 else rsg_sky().copy()
    # the collapsing core, seen as a glow shrinking to a point inside the star
    c = ss(42.3, 47.6, t)
    if t < tb + 1.5:
        g = (0.25 + 1.6 * c) * ss(41.5, 43.0, t) * (1 - ss(0.2, 1.5, tau))
        add_glint(img, cx, cy, g, (1.0, 0.86, 0.62), sig=lerp(R0 * 0.34, 5.0, c ** 0.7))
        if c >= 1: glare(img, cx, cy, 0.5 * ss(47.6, 48.4, t) * (1 - ss(0.0, 1.2, tau)), s=1.4, col=(0.8, 0.9, 1.0))
    if tau > -1.4:                                         # light of the shock climbing through the envelope, then the flash
        pre = ss(-1.4, 0.0, tau) * (1 - ss(0.0, 2.2, tau))
        add_glint(img, cx, cy, 2.4 * pre, (1.0, 0.93, 0.82), sig=R0 * lerp(0.35, 0.9, ss(-1.4, 0, tau)))
    if tau > 0:
        Rs = R0 * (0.8 + 2.1 * (1 - math.exp(-tau / 3.0)))
        L = cached(("expl", "sn"), lambda: expl_layers(1))
        k = ss(0.0, 0.8, tau) * (0.55 + 0.9 * math.exp(-tau / 3.0))
        draw_expl(img, L, cx, cy, Rs, SN_COLS, [1.5 * k, 0.9 * k, 0.8 * k, 0.6 * k, 0.45 * k, 0.3 * k], rot=tau * 0.5, squash=0.94)
        add_glint(img, cx, cy, 3.0 * math.exp(-tau / 0.9), (1.0, 0.96, 0.9), sig=R0 * 1.2)
        glare(img, cx, cy, 0.5 * ss(1.5, 4.5, tau), s=0.8)                 # what is left at the centre
    img = bloom(img, 0.7, 0.8)
    if tau > 0: img += np.array([1.0, 0.97, 0.92], F32) * 0.9 * math.exp(-tau / 0.45)
    T = Text()
    cap(T, t, 42.0, 49.6, hv(["CORE COLLAPSE", "LESS THAN ONE SECOND"], ["CORE COLLAPSE", "LESS THAN ONE SECOND"]), hv(880, 1300))
    cap(T, t, 45.4, 49.6, ["THOUSANDS OF KM  →  ≈ 20 KM"], hv(980, 1436), size=hv(24, 30), col=COOL)
    T.put(hv((120, 900), (W / 2, 1330)), "SUPERNOVA", hv(60, 68), win(t, 52.6, 57.4, 0.8, 0.6), anchor=hv("l", "c"), wt="XL", track=hv(14, 10))
    note(T, t, 42.0, 57.4, "ILLUSTRATION · TIME COMPRESSED")
    return T.add_to(img)


# ================================================================================================= 5  to scale over New York
H_STAR = 17.0; R_STAR = 12.5


@functools.lru_cache(None)
def nyc_lit():
    rgb, water = nyc_map()
    yy, xx = np.mgrid[0:rgb.shape[0], 0:rgb.shape[1]].astype(F32)
    d2 = ((xx - MAN[0]) ** 2 + (yy - MAN[1]) ** 2) * (M_PER_PX / 1000) ** 2
    Lm = H_STAR ** 3 / (d2 + H_STAR ** 2) ** 1.5
    lit = rgb * (0.50 + 5.0 * Lm[..., None] * np.array([0.72, 0.90, 1.25], F32))
    lit += (water * Lm ** 2)[..., None] * np.array([0.10, 0.20, 0.36], F32) * 0.6
    return np.ascontiguousarray(lit.astype(F32)), np.ascontiguousarray(water)


PLACES = [("MANHATTAN", 40.790, -73.962, 1), ("BROOKLYN", 40.640, -73.950, 1), ("QUEENS", 40.735, -73.800, 1), ("THE BRONX", 40.855, -73.865, 1),
          ("STATEN ISLAND", 40.580, -74.150, 1), ("NEWARK", 40.735, -74.185, 1), ("HUDSON RIVER", 40.98, -73.90, 0), ("LONG ISLAND SOUND", 40.93, -73.62, 0),
          ("ATLANTIC OCEAN", 40.46, -73.80, 0), ("JFK AIRPORT", 40.645, -73.785, 1)]


def shot_city(t, lt):
    e = ss(0.0, 17.0, lt); e2 = ss(0.0, 9.0, lt)
    eye = np.array([lerp(-20, -34, e), lerp(-58, -96, e), lerp(26, 60, e)])
    cam = Cam(eye, (0.0, lerp(0, 6, e), lerp(hv(15, 10), hv(7.5, 2.0), e2)), 44.0)
    lit, water = nyc_lit()
    g, grd, dist = ground_view(cam, lit)
    skyb = cached(("sky", "city"), lambda: render_sky(look_at((0, 0, 0), norm([0.3, 0.9, 0.3])), FL(44), gain=0.7, mw_gain=1.3))
    img = skyb * (1 - grd[..., None]) * 0.8 + g
    sx, sy, rp, dd = cam.sphere((0, 0, H_STAR), R_STAR)
    # reflection of the star in the water
    mx, my, mr, _ = cam.sphere((0, 0, -H_STAR), R_STAR)
    wm, _, _ = ground_view(cam, water, ss_=1, haze_km=1e9)
    refl = np.zeros_like(img); add_glint(refl, mx, my, 0.55, (0.55, 0.78, 1.0), sig=mr * 0.75); add_glint(refl, mx, my, 0.22, (0.5, 0.7, 1.0), sig=mr * 2.2)
    img += refl * wm[..., :1]
    add_glint(img, sx, sy, 0.16, (0.45, 0.68, 1.0), sig=rp * 2.6)
    Mb, Mc = star_M(0.3 + 0.05 * lt, chi=24, incl=10, roll=-10)
    draw_star(img, sx, sy, rp, Mb, u=U_NS, gain=1.05)
    img = bloom(img, 0.72, 0.7)
    T = Text(); Lw = Lines()
    a1 = win(t, 61.2, 74.4, 0.9, 0.6)
    for name, la, lo, land in PLACES:
        gx, gy = ground_km(la, lo); px, py, pd = cam.proj(np.array([[gx, gy, 0.0]])); px, py = float(px[0]), float(py[0])
        if not (60 < px < W - 60 and hv(120, 260) < py < hv(H - 110, 1500)): continue
        if (px - sx) ** 2 + (py - sy) ** 2 < (rp + 30) ** 2: continue
        s_ = hv(18, 22)
        T.put((px, py - s_ * 0.6), name, s_, a1 * (0.95 if land else 0.75), col=TXT if land else COOL, anchor="c", wt="R")
    # Manhattan's length on the ground (Battery to Inwood, 21.6 km), drawn in the Hudson
    a2 = win(t, 65.6, 74.4, 0.8, 0.6)
    if a2 > 0.004:
        A = np.array(ground_km(40.701, -74.016)); B = np.array(ground_km(40.876, -73.925)); dvec = (B - A) / np.linalg.norm(B - A); nvec = np.array([-dvec[1], dvec[0]])
        off = nvec * 3.4
        pts = np.array([[*(A + off), 0], [*(B + off), 0], [*(A + off - nvec * 0.7), 0], [*(A + off + nvec * 0.7), 0], [*(B + off - nvec * 0.7), 0], [*(B + off + nvec * 0.7), 0]])
        px, py, _ = cam.proj(pts)
        Lw.seg(px[0], py[0], px[1], py[1], 255 * a2, 2); Lw.seg(px[2], py[2], px[3], py[3], 255 * a2, 2); Lw.seg(px[4], py[4], px[5], py[5], 255 * a2, 2)
        T.put((px[0] - 14, py[0] - hv(4, 6)), hv("MANHATTAN: 21.6 KM LONG", "MANHATTAN: 21.6 KM"), hv(20, 24), a2, col=AMB, anchor="r", wt="R")
    a3 = win(t, 63.4, 74.4, 0.8, 0.6)
    if a3 > 0.004:
        yb = sy - rp - hv(34, 40); Lc = Lines()
        Lc.seg(sx - rp, yb, sx + rp, yb, 255 * a3, 2); Lc.seg(sx - rp, yb - 9, sx - rp, yb + 9, 255 * a3, 2); Lc.seg(sx + rp, yb - 9, sx + rp, yb + 9, 255 * a3, 2)
        Lc.add_to(img, (0.75, 0.9, 1.0), gain=0.9, glow=0.3)
        T.put((sx, yb - hv(40, 50)), "≈ 25 KM", hv(28, 34), a3, anchor="c", wt="R")
    Lw.add_to(img, (1.0, 0.78, 0.45), gain=1.0, glow=0.3)
    cap(T, t, 58.6, 64.6, ["A NEUTRON STAR"], hv(880, 1330), size=hv(44, 50), wt="XL")
    cap(T, t, 70.2, 74.4, hv(["MORE MASS THAN THE ENTIRE SUN"], ["MORE MASS THAN", "THE ENTIRE SUN"]), hv(880, 1300), size=hv(34, 42))
    cap(T, t, 71.4, 74.4, ["TYPICALLY ≈ 1.4 SOLAR MASSES"], hv(940, 1440), size=hv(22, 28), col=COOL)
    note(T, t, 60.8, 74.4, hv("STAR AND MAP TO THE SAME SCALE · REAL ELEVATION DATA, RELIEF EXAGGERATED · A THOUGHT PICTURE: IT COULD NOT EXIST HERE",
                             ["STAR AND MAP TO THE SAME SCALE", "REAL ELEVATION DATA · RELIEF EXAGGERATED"]))
    return T.add_to(img)


# ================================================================================================= 6  inside (density)
def shot_dens(t, lt):
    R = hv(390, 400) * (1 + 0.006 * lt); cx, cy = hv((620, 520), (W / 2, 730)); ang = 50.0
    Mb, Mc = star_M(0.8 + 0.01 * lt, chi=20, incl=14, roll=-18)
    f = FL(40); m = 900
    skyc = cached(("skyL", "dens"), lambda: render_sky(look_at((0, 0, 0), norm([-0.5, -0.6, 0.6])), f, gain=0.9, mw_gain=1.8, size=(W + 2 * m, H + 2 * m)))
    bg = np.ascontiguousarray(skyc[m:m + H, m:m + W]) * 0.8
    img = bg.copy(); draw_star(img, cx, cy, R, Mb, u=0.0, gain=1.0)
    bg2 = bg.copy(); add_glint(bg2, cx, cy, 0.10, (0.4, 0.6, 1.0), sig=R * 0.9)
    draw_cutaway(img, bg2, cx, cy, R, ang, ns_face())
    img = bloom(img, 0.72, 0.6)
    T = Text(); ca = math.cos(math.radians(ang))
    labs = [(0.985, 52, "OUTER CRUST", "NUCLEI AND ELECTRONS · FROM ≈ 10⁹ kg/m³", (190, 230, 255)),
            (0.935, 24, "INNER CRUST", "NEUTRONS START TO LEAK OUT OF NUCLEI", (120, 175, 255)),
            (0.66, 2, "OUTER CORE", "MOSTLY NEUTRONS · DENSER THAN AN ATOMIC NUCLEUS", (110, 130, 255)),
            (0.20, -20, "INNER CORE", "UNKNOWN · PERHAPS ≈ 10¹⁸ kg/m³", (255, 140, 215))]
    for i, (r, th, a_, b_, col) in enumerate(labs):
        al = win(t, 83.6 + 0.7 * i, 92.2, 0.8, 0.6)
        if al <= 0.004: continue
        px = cx + R * r * ca * math.cos(math.radians(th)); py = cy - R * r * math.sin(math.radians(th))
        if VERT:
            ly = 1180 + i * 74; T.line((px, py), (px, py), 0, col)
            T.line((150, ly + 8), (150, ly + 52), al, col, width=4)
            T.put((172, ly), a_, 28, al, col=col, wt="R"); T.put((172, ly + 36), b_ if len(b_) < 44 else b_.split(" · ")[0], 20, al, col=DIM, wt="R")
        else:
            lx = 1120; ly = 250 + i * 120
            T.line((px, py), (lx - 16, ly + 16), al * 0.7, col); T.line((lx - 16, ly + 16), (lx - 4, ly + 16), al * 0.7, col)
            T.put((lx, ly), a_, 26, al, col=col, wt="R"); T.put((lx, ly + 40), b_, 19, al, col=DIM, wt="R")
    cap(T, t, 76.2, 82.6, hv(["AN ORDINARY ATOM IS ALMOST ALL EMPTY SPACE"], ["AN ORDINARY ATOM IS", "ALMOST ALL EMPTY SPACE"]), hv(930, 1190), size=hv(30, 38))
    cap(T, t, 82.9, 92.2, hv(["HERE, THAT SPACE IS CRUSHED OUT"], [""]), hv(930, 1190), size=hv(30, 38))
    note(T, t, 76.4, 92.2, hv("CUTAWAY ILLUSTRATION · LAYER THICKNESSES APPROXIMATE (CRUST ≈ 1 KM OF A 12 KM RADIUS)", "CUTAWAY ILLUSTRATION · THICKNESSES APPROXIMATE"))
    return T.add_to(img)


# ================================================================================================= 7  the mass of a teaspoon
def shot_mass(t, lt):
    skyb = cached(("sky", "mass"), lambda: render_sky(look_at((0, 0, 0), norm([-0.2, 0.7, 0.68])), FL(46), gain=0.7, mw_gain=1.5))
    img = skyb.copy()
    bx, by, sc, ang = hv((1210 + lt * 2.0, 560 - lt * 0.8, 1.22, -8.0), (330, 560 - lt * 1.2, 0.90, 50.0))
    spoon(img, 0.25 + lt / 16.8 * 0.4, bx, by, sc, ang, bead=1.0)
    glare(img, bx, by - 6 * sc, 0.6 * (1 + 0.05 * math.sin(t * 9)), s=1.2)
    img = bloom(img, 0.72, 0.6)
    T = Text()
    x0 = hv(120, 110); y0 = hv(180, 990); bw = hv(620, 860); rh = hv(98, 62)
    T.put((x0, y0 - hv(82, 64)), "5 mL OF NEUTRON-STAR MATTER", hv(30, 30), win(t, 93.2, 109.0, 0.8, 0.6), col=TXT, wt="R")
    rows = [("CRUST, NEAR THE SURFACE", "≈ 5 TONNES", 5e3, 96.0, COOL), ("AVERAGE THROUGH THE STAR", "≈ 2 BILLION TONNES", 1.9e9, 99.4, YEL),
            ("DEEP IN THE CORE", "≈ 5 BILLION TONNES, OR MORE", 5e9, 104.4, YEL),
            ("GREAT PYRAMID OF GIZA", "≈ 6 MILLION TONNES", 6e6, 100.6, DIM), ("EVERY HUMAN ALIVE", "≈ 0.5 BILLION TONNES", 0.5e9, 101.2, DIM),
            ("ONE CUBIC KILOMETRE OF GRANITE", "≈ 2.7 BILLION TONNES", 2.7e9, 101.8, DIM)]
    for i, (a_, b_, val, ta, col) in enumerate(rows):
        al = win(t, ta, 109.0, 0.8, 0.6); y = y0 + i * rh + (hv(26, 14) if i >= 3 else 0)
        if al <= 0.004: continue
        T.put((x0, y), a_, hv(21, 22), al, col=TXT if i < 3 else DIM, wt="R")
        T.put((x0 + bw, y), b_, hv(21, 22), al, col=col, anchor="r", wt="R")
        wbar = max(2.0, bw * val / 5e9 * ss(ta, ta + 1.2, t))
        T.line((x0, y + hv(46, 38)), (x0 + bw, y + hv(46, 38)), al * 0.25, DIM, width=1)
        T.line((x0, y + hv(46, 38)), (x0 + wbar, y + hv(46, 38)), al, col if i < 3 else (200, 208, 220), width=hv(5, 5))
    note(T, t, 96.0, 109.0, hv("BARS TO SCALE · MEAN FOR 1.4 SOLAR MASSES AND A 12 KM RADIUS · SEE SOURCES", "BARS TO SCALE · MEAN FOR 1.4 SUNS, 12 KM RADIUS"))
    return T.add_to(img)


# ================================================================================================= 8  gravity and light bending
def shot_grav(t, lt):
    e = ss(123.4, 128.0, t)
    Rt_wide = hv(250, 270)                                   # true-radius scale (px) in the wide view
    dip = ss(129.2, 130.2, t) * (1 - ss(131.6, 133.4, t))    # light bending switched off, then on again
    u = U_NS * (1 - dip)
    Rapp = lerp(1350.0, Rt_wide / math.sqrt(1 - u), e)
    cx = W / 2; cy = lerp(H + hv(830, 560), hv(500, 760), e)
    Mb, Mc = star_M(1.9 + 0.035 * lt, chi=30, incl=18, roll=10)
    gr = ss(128.4, 129.4, t)
    img = ns_scene("grav", cx, cy, Rapp, Mb, Mc=Mc, u=u, drift=(lt * 4, 0), grid=0.75 * gr, horizon=gr, lines=0.0)
    img = bloom(img, 0.74, 0.6)
    T = Text()
    cap(T, t, 110.4, 124.0, hv(["SURFACE GRAVITY", "≈ 100 BILLION × EARTH'S"], ["SURFACE GRAVITY", "≈ 100 BILLION × EARTH'S"]), hv(120, 300), size=hv(34, 42))
    cap(T, t, 116.0, 124.0, hv(["A ONE-METRE DROP:", "≈ 1 MICROSECOND · IMPACT AT MORE THAN 1,000 KM/S"], ["A ONE-METRE DROP:", "≈ 1 MICROSECOND", "IMPACT > 1,000 KM/S"]), hv(250, 470), size=hv(24, 30), col=COOL)
    cap(T, t, 125.3, 129.2, hv(["ESCAPE VELOCITY", "MORE THAN ½ THE SPEED OF LIGHT"], ["ESCAPE VELOCITY", "> ½ THE SPEED OF LIGHT"]), hv(860, 1270), size=hv(34, 42))
    a_off = win(t, 129.6, 131.7, 0.5, 0.5); a_on = win(t, 132.2, 136.2, 0.6, 0.6)
    cap(T, t, 129.6, 131.7, hv(["WITHOUT LIGHT BENDING", "WE WOULD SEE HALF OF THE SURFACE"], ["WITHOUT LIGHT BENDING:", "HALF OF THE SURFACE"]), hv(860, 1270), size=hv(30, 38), stagger=0.0)
    cap(T, t, 132.2, 136.2, hv(["WITH IT: ROUGHLY THREE QUARTERS", "THE FAR SIDE IS PULLED INTO VIEW"], ["WITH IT: ROUGHLY", "THREE QUARTERS"]), hv(860, 1270), size=hv(30, 38), stagger=0.0)
    T.put(hv((W - 120, 880), (W / 2, 1400)), "AMBER LINE: THE EDGE WITHOUT BENDING", hv(19, 24), win(t, 132.4, 136.2, 0.6, 0.6), col=AMB, anchor=hv("r", "c"), wt="R")
    note(T, t, 110.6, 136.2, hv("COMPUTED FOR 1.4 SOLAR MASSES AND A 12 KM RADIUS · SURFACE DETAIL IS AN ARTIST'S IMPRESSION", "1.4 SOLAR MASSES, 12 KM RADIUS · ARTIST'S IMPRESSION"))
    return T.add_to(img)


# ================================================================================================= 9  pulsar
def spin_phase(t):
    lt = t - 136.6
    return 2 * math.pi * (0.22 * lt + 0.5 * 0.022 * lt * lt)       # 0.22 -> ~0.68 turns per second


def pulse_signal(tt):
    """radio intensity for a distant observer lying on the cone swept by the magnetic axis"""
    ph = spin_phase(tt) / (2 * math.pi)
    d = (ph + 0.5) % 1.0 - 0.5
    return math.exp(-(d / 0.035) ** 2)


def shot_pulsar(t, lt):
    ph = spin_phase(t); w = (0.22 + 0.022 * lt)
    Mb, Mc = star_M(ph, chi=38, incl=18, roll=14)
    R = hv(215, 215) * (1 + 0.004 * lt); cx, cy = W / 2, hv(470, 800)
    img = ns_scene("pulsar", cx, cy, R, Mb, Mc=Mc, lines=0.22, beam=0.95, blur=int(w * 60), drift=(lt * 3, lt), bhalf=0.15)
    img = bloom(img, 0.72, 0.75)
    T = Text()
    T.put(hv((120, 150), (W / 2, 260)), "PULSAR", hv(60, 68), win(t, 144.6, 157.2, 0.8, 0.6), anchor=hv("l", "c"), wt="XL", track=hv(14, 10))
    cap(T, t, 148.0, 157.2, hv(["FASTEST KNOWN: PSR J1748−2446ad", "716 ROTATIONS EVERY SECOND"], ["FASTEST KNOWN:", "PSR J1748−2446ad", "716 ROTATIONS A SECOND"]), hv(250, 370), size=hv(26, 32), col=TXT)
    cap(T, t, 152.6, 157.2, hv(["EQUATOR ≈ 24 % OF THE SPEED OF LIGHT"], ["EQUATOR ≈ 24 % OF LIGHT SPEED"]), hv(340, 528), size=hv(22, 28), col=COOL)
    # pulse trace
    al = win(t, 139.5, 157.2, 0.8, 0.6)
    if al > 0.004:
        x0, x1 = hv((1250, 1800), (140, 940)); yb = hv(900, 1380); n = 400; span = 5.0
        Lt = Lines(); xs = np.linspace(x0, x1, n); ts_ = t - span + span * (np.arange(n) / (n - 1))
        ys = yb - np.array([pulse_signal(q) if q > 137.0 else 0.0 for q in ts_]) * hv(70, 90)
        Lt.poly(xs, ys, a=255 * al, th=2); Lt.seg(x0, yb + 12, x1, yb + 12, 80 * al, 1)
        Lt.add_to(img, (0.6, 0.85, 1.0), gain=1.0, glow=0.6)
        T.put((x0, yb + 24), hv("RADIO SIGNAL AT A DISTANT TELESCOPE", "SIGNAL AT A DISTANT TELESCOPE"), hv(18, 22), al, col=DIM, wt="R")
    note(T, t, 138.0, 157.2, hv("ILLUSTRATION · ROTATION SHOWN ABOUT A THOUSAND TIMES SLOWER THAN THE RECORD HOLDER", "ILLUSTRATION · SPIN SHOWN ≈ 1,000 × SLOWER"))
    return T.add_to(img)


# ================================================================================================= 10  magnetar
def shot_magnetar(t, lt):
    ph = spin_phase(157.6) + 0.5 * lt
    Mb, Mc = star_M(ph, chi=38, incl=18, roll=14)
    R = hv(215, 215) * (1 + 0.004 * 21 + 0.008 * lt); cx, cy = W / 2, hv(470, 800)
    fl = 1 + 0.10 * math.sin(t * 5.1) * math.sin(t * 1.3)
    img = ns_scene("pulsar", cx, cy, R, Mb, Mc=Mc, kind="mag", lines=0.42 * fl, beam=0.0, drift=(21 * 3 + lt * 3, 21 + lt), twist=2.4 + 0.4 * math.sin(t * 0.7),
                   shells=(1.5, 1.9, 2.5, 3.3, 4.4, 6.0, 8.5), naz=16, lcol=(0.80, 0.55, 1.0), halo_col=(0.65, 0.40, 1.0), gain=1.05)
    img = bloom(img, 0.70, 0.85)
    T = Text()
    T.put(hv((120, 150), (W / 2, 260)), "MAGNETAR", hv(60, 68), win(t, 158.6, 168.6, 0.8, 0.6), anchor=hv("l", "c"), wt="XL", track=hv(14, 10))
    cap(T, t, 161.4, 168.6, hv(["MAGNETIC FIELD ≈ A THOUSAND TRILLION × EARTH'S", "THE STRONGEST MAGNETS KNOWN"], ["MAGNETIC FIELD ≈", "A THOUSAND TRILLION", "× EARTH'S"]), hv(880, 1250), size=hv(28, 36))
    note(T, t, 158.8, 168.6, hv("ILLUSTRATION · FIELD LINES ARE SCHEMATIC · UP TO ROUGHLY 10¹⁵ GAUSS", "ILLUSTRATION · FIELD LINES SCHEMATIC"))
    return T.add_to(img)


# ================================================================================================= 11  the honest answer
def shot_answer(t, lt):
    img = earth_plate(t, "hook", lon0=40.0)
    bx, by, sc, ang = spoon_pose(); u = 0.45 + lt / 29.2 * 0.5
    bx += 40 - lt * hv(1.6, 0.6); by += lt * hv(0.5, 0.9) - 20
    tb = 188.3; tau = t - tb
    pre = ss(185.6, tb, t)
    fl = 1 + 0.05 * math.sin(t * 9.0) + pre * 0.25 * math.sin(t * 31.0)
    sa = 1 - ss(0.0, 0.22, tau)
    if sa > 0.003: spoon(img, u, bx, by, sc, ang, bead=1.0, gain=1 + 1.2 * pre * ss(-0.4, 0, tau), alpha=sa)
    glare(img, bx, by - 6 * sc, (0.55 + 1.6 * pre ** 2) * fl * (1 - ss(0.3, 2.0, tau)) + 0.001, s=1.0 + 0.8 * pre)
    if tau > 0:
        L = cached(("expl", "blast"), lambda: expl_layers(2, kind="ball"))
        Rb = 40 + 3300 * (1 - math.exp(-tau / 2.6))
        k = (0.5 + 1.5 * math.exp(-tau / 1.2)) * (1 - 0.55 * ss(3.0, 9.5, tau))
        cols = [tuple(lerp(np.array(b_), np.array(f_), ss(0.3, 3.5, tau))) for b_, f_ in zip(BLUE_COLS, FIRE_COLS)]
        draw_expl(img, L, bx, by, Rb, cols, [1.1 * k, 0.9 * k, 0.8 * k, 0.7 * k, 0.6 * k, 0.5 * k], rot=tau * 2.0, spread=0.02)
        add_glint(img, bx, by, 2.4 * math.exp(-tau / 1.4), (1.0, 0.95, 0.85), sig=220 + 500 * tau)
    img = bloom(img, 0.72, 0.7)
    if tau > 0:
        img += np.array([0.95, 0.97, 1.0], F32) * 1.3 * math.exp(-tau / 0.55)
        img *= 1 - 0.25 * ss(4.0, 9.5, tau)
    T = Text()
    cap(T, t, 172.6, 180.6, ["YOU COULD NOT SCOOP IT."], hv(150, 262), x=hv(1000, W / 2), size=hv(44, 52), wt="XL")
    cap(T, t, 175.6, 180.6, hv(["IT IS ONLY THIS DENSE BECAUSE THE WEIGHT", "OF A WHOLE STAR IS PRESSING DOWN ON IT"], ["THIS DENSE ONLY BECAUSE", "THE WEIGHT OF A WHOLE STAR", "PRESSES DOWN ON IT"]), hv(236, 356), x=hv(1004, W / 2), size=hv(22, 28), col=COOL)
    cap(T, t, 182.0, 188.0, hv(["AWAY FROM THAT GRAVITY,", "NOTHING HOLDS IT TOGETHER"], ["AWAY FROM THAT GRAVITY,", "NOTHING HOLDS IT TOGETHER"]), hv(150, 262), x=hv(1000, W / 2), size=hv(30, 36))
    cap(T, t, 190.6, 197.8, hv(["IT EXPANDS · INSTANTLY · VIOLENTLY"], ["IT EXPANDS", "INSTANTLY · VIOLENTLY"]), hv(880, 1250), size=hv(34, 42))
    cap(T, t, 192.0, 197.8, hv(["ROUGH ESTIMATE: THE ENERGY OF HUNDREDS TO THOUSANDS OF DINOSAUR-KILLING IMPACTS"], ["ROUGH ESTIMATE: THE ENERGY OF", "HUNDREDS TO THOUSANDS OF", "DINOSAUR-KILLING IMPACTS"]), hv(940, 1380), size=hv(22, 26), col=AMB, wt="R", gap=1.4, stagger=0.0)
    banner(T, t, 181.8, 197.8, "WHAT PHYSICS SAYS WOULD REALLY HAPPEN · ORDER-OF-MAGNITUDE ONLY" if not VERT else "WHAT WOULD REALLY HAPPEN")
    note(T, t, 170.4, 188.0, "ILLUSTRATION · BEAD AND EARTH NOT TO SCALE", top=True)
    return T.add_to(img)


# ================================================================================================= 12  thought experiment A: it cannot be held
def shot_thoughtA(t, lt):
    img = earth_plate(t, "hook", lon0=75.0)
    bx, by, sc, ang = spoon_pose(); u = 0.15 + lt / 22.2 * 0.45
    bx += 30 + lt * hv(1.4, 0.5); by += -10 - lt * hv(0.5, 1.0)
    td = 216.3; tau = t - td
    present = 1 - ss(-0.05, 0.12, tau)
    spoon(img, u, bx, by, sc, ang + (2.5 * ss(0, 3, tau) if tau > 0 else 0), bead=present)
    fl = 1 + 0.05 * math.sin(t * 9.0)
    if tau <= 0:
        glare(img, bx, by - 6 * sc, 0.55 * fl)
    else:                                                    # the bead drops straight "down", toward the Earth
        y = by + 0.5 * 2100 * tau * tau; ylimb = hv(770, 1420) + 30
        if y < H + 200:
            Lf = Lines(); Lf.seg(bx, max(by, y - 60 - 700 * tau), bx, y, 255, 2); Lf.add_to(img, (0.6, 0.8, 1.0), gain=0.9 * (1 - ss(0.5, 1.2, tau)), glow=1.2)
            glare(img, bx, y, 0.5 * (1 - 0.6 * ss(0.3, 0.9, tau)), s=0.8)
        ti = math.sqrt(max(0.0, 2 * (ylimb + 120 - by) / 2100)); ta2 = tau - ti
        if ta2 > 0: add_glint(img, bx, ylimb + 120, 0.9 * math.exp(-ta2 / 0.5), (1.0, 0.85, 0.6), sig=26 + 60 * ta2)
    img = bloom(img, 0.72, 0.6)
    T = Text()
    banner(T, t, 198.8, 220.2, "THOUGHT EXPERIMENT · IF IT SOMEHOW STAYED COMPRESSED" if not VERT else "THOUGHT EXPERIMENT")
    cap(T, t, 203.2, 209.4, hv(["A BEAD ≈ 2 CM WIDE", "WEIGHING BILLIONS OF TONNES"], ["A BEAD ≈ 2 CM WIDE", "BILLIONS OF TONNES"]), hv(150, 340), x=hv(1000, W / 2), size=hv(34, 42))
    cap(T, t, 210.4, 216.0, hv(["WITHIN A FEW METRES OF IT,", "ITS GRAVITY BEATS THE EARTH'S"], ["WITHIN A FEW METRES,", "ITS GRAVITY BEATS", "THE EARTH'S"]), hv(150, 340), x=hv(1000, W / 2), size=hv(30, 38))
    cap(T, t, 211.6, 216.0, ["≈ 1 g AT 3–6 METRES"], hv(250, 520), x=hv(1004, W / 2), size=hv(22, 28), col=COOL)
    cap(T, t, 216.6, 220.0, ["NOTHING COULD HOLD IT UP"], hv(880, 1250), size=hv(34, 40))
    note(T, t, 199.0, 220.0, "NOT PHYSICALLY POSSIBLE · BEAD AND EARTH NOT TO SCALE", top=True)
    return T.add_to(img)


# ================================================================================================= 13  thought experiment B: through the Earth
def _unit_ll(lat, lon):
    la, lo = math.radians(lat), math.radians(lon); return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])


def nyc_up_M():
    up = _unit_ll(40.71, -74.0); left = _unit_ll(-42.0, -112.0); left = norm(left - (left @ up) * up); x = -left; z = np.cross(x, up)
    return np.stack([x, up, z], 1)                           # body <- camera


def sim_minutes(t):
    return float(np.interp(t, [223.6, 228.4, 230.6, 231.9, 233.2, 236.6], [0.0, 21.1, 42.2, 63.3, 84.4, 84.4 * 3.25]))


def shot_thoughtB(t, lt):
    R = hv(400, 430) * (1 + 0.004 * lt); cx, cy = hv((W * 0.44, 540), (W / 2, 800)); ang = 54.0
    skyb = cached(("sky", "thB"), lambda: render_sky(look_at((0, 0, 0), norm([0.7, -0.3, 0.64])), FL(46), gain=0.7, mw_gain=1.4))
    bg = skyb.copy(); img = bg.copy()
    M = nyc_up_M() @ rot_axis((0, 1, 0), math.radians(-12))
    draw_earth(img, cx, cy, R, M, norm([-0.75, 0.35, 0.56]), t=t, night_gain=1.2)
    draw_cutaway(img, bg, cx, cy, R, ang, earth_face(t))
    tm = sim_minutes(t); om = 2 * math.pi / 84.4
    pos = math.cos(om * tm)                                   # +1 = New York, -1 = antipode
    Lp = Lines(); Lp.seg(cx, cy - R, cx, cy + R, 70, 1)
    # glowing trail of the last few simulated minutes
    for k in range(1, 22):
        q0 = math.cos(om * max(0.0, tm - (k - 1) * 0.9)); q1 = math.cos(om * max(0.0, tm - k * 0.9))
        Lp.seg(cx, cy - R * q0, cx, cy - R * q1, 255 * (1 - k / 22) ** 1.5, 2)
    Lp.add_to(img, (0.65, 0.85, 1.0), gain=1.0, glow=1.0)
    glare(img, cx, cy - R * pos, 0.34, s=0.6)
    img = bloom(img, 0.74, 0.6)
    T = Text()
    banner(T, t, 220.8, 236.2, "THOUGHT EXPERIMENT · IF IT SOMEHOW STAYED COMPRESSED" if not VERT else "THOUGHT EXPERIMENT")
    a = win(t, 221.6, 236.2, 0.8, 0.6)
    tag(T, cx, cy - R, "NEW YORK", a, dx=hv(40, 30), dy=-30)
    tag(T, cx, cy + R, hv("FAR SIDE: INDIAN OCEAN, SOUTH-WEST OF AUSTRALIA", "FAR SIDE: INDIAN OCEAN"), a * ss(229.0, 230.0, t), dx=hv(40, 30), dy=hv(34, 40))
    rx = hv(1180, W / 2); ry = hv(330, 1290); anc = hv("l", "c")
    v = 7.9 * abs(math.sin(om * tm)); depth = 6371 * (1 - abs(pos))
    al = win(t, 223.4, 236.2, 0.8, 0.6)
    T.put((rx, ry), f"T + {int(tm):d} MIN", hv(52, 54), al, anchor=anc, wt="XL")
    T.put((rx, ry + hv(84, 78)), f"DEPTH {depth:,.0f} KM   ·   {v:.1f} KM/S", hv(22, 26), al, col=COOL, anchor=anc, wt="R")
    cap(T, t, 226.4, 231.0, hv(["THE CENTRE IN ABOUT 20 MINUTES"], ["THE CENTRE IN ≈ 20 MINUTES"]), ry + hv(150, 126), x=rx, size=hv(26, 30), anchor=anc)
    cap(T, t, 231.4, 236.2, hv(["THEN BACK · AGAIN AND AGAIN"], ["THEN BACK · AGAIN AND AGAIN"]), ry + hv(150, 126), x=rx, size=hv(26, 30), anchor=anc)
    note(T, t, 221.2, 236.2, hv("SIMPLE MODEL: UNIFORM-DENSITY EARTH, NO DRAG · THE ROCK IN ITS PATH HAS ABOUT A HUNDRED-THOUSANDTH OF ITS MASS", "UNIFORM-DENSITY EARTH, NO DRAG · BEAD ENLARGED"))
    return T.add_to(img)


# ================================================================================================= 14  inspiral and merger
T_MERGE = 259.9


def orbit(t):
    """separation (in star radii) and orbital phase for the last, slowed orbits: a ~ (tc - t)^(1/4)"""
    rem = max(T_MERGE - t, 0.02); a = 2.0 + 5.4 * (rem / 23.5) ** 0.25 - 2.0 * (0.02 / 23.5) ** 0.25
    ph = -0.60 * 2 * math.pi * 23.5 ** 0.375 * rem ** 0.625 * 1.6
    return a, ph


def shot_merger(t, lt):
    a, ph = orbit(t); zoom = 1 + 0.5 * ss(236.4, 259.9, t)
    Rp = hv(52, 56) * zoom; cx, cy = W / 2, hv(500, 800); inc = math.radians(62)
    f = FL(40); m = 300
    skyc = cached(("skyL", "merge"), lambda: render_sky(look_at((0, 0, 0), norm([0.6, 0.6, -0.5])), f, gain=1.0, mw_gain=2.0, size=(W + 2 * m, H + 2 * m)))
    # gravitational waves: a two-armed spiral of tiny radial displacements of the background (plus a faint glow)
    xs = np.arange(W, dtype=F32) + 0.5 - cx; ys = np.arange(H, dtype=F32) + 0.5 - cy; X, Y = np.meshgrid(xs, ys)
    Yd = Y / math.cos(inc) * 0.75 + Y * 0.25
    r = np.sqrt(X * X + Yd * Yd) + 1; th = np.arctan2(-Yd, X)
    amp = (5.0 + 16.0 * ss(250.0, 259.8, t)) * ss(237.0, 240.0, t)
    kr = 0.016 / zoom
    wave = np.sin(2 * (th - ph) + kr * r) * np.clip((r - a * Rp * 0.5) / (Rp * 2.5), 0, 1) * np.exp(-r / hv(1500, 1700))
    dsp = amp * wave
    img = cv2.remap(skyc, (X + cx + m + X / r * dsp).astype(F32), (Y + cy + m + Y / r * dsp).astype(F32), cv2.INTER_LINEAR)
    img += (np.clip(wave, 0, 1) ** 3 * amp / 21.0 * 0.11)[..., None] * np.array([0.45, 0.65, 1.0], F32)
    # the two stars
    stars = []
    for sgn in (1, -1):
        px = sgn * a / 2 * Rp * math.cos(ph); py = sgn * a / 2 * Rp * math.sin(ph); stars.append((py * math.sin(inc), cx + px, cy - py * math.cos(inc), sgn))
    heat = ss(256.0, 259.8, t)
    Lt = Lines()
    for sgn in (1, -1):                                       # faint trails along the orbit
        pa = ph - np.linspace(0, 1.6, 60); aa = a * (1 + 0.02 * np.linspace(0, 1, 60))
        Lt.poly(cx + sgn * aa / 2 * Rp * np.cos(pa), cy - sgn * aa / 2 * Rp * np.sin(pa) * math.cos(inc), a=120, th=1)
    Lt.add_to(img, (0.5, 0.75, 1.0), gain=0.25 + 0.5 * heat, glow=1.5)
    for z, sx, sy, sgn in sorted(stars):
        Mb, Mc = star_M(t * 0.9 * sgn + sgn, chi=25, incl=20, roll=20 * sgn)
        add_glint(img, sx, sy, 0.10 + 0.5 * heat, (0.5, 0.72, 1.0), sig=Rp * 2.0)
        draw_star(img, sx, sy, Rp, Mb, u=U_NS, gain=1.0 + 1.0 * heat, blur=6)
    fl = ss(259.2, 259.95, t)
    if fl > 0: glare(img, cx, cy, 2.5 * fl ** 2, s=2.0)
    img = bloom(img, 0.70, 0.8)
    T = Text()
    cap(T, t, 237.6, 247.8, hv(["TWO NEUTRON STARS IN ORBIT", "SPIRALLING TOGETHER OVER MILLIONS OF YEARS"], ["TWO NEUTRON STARS", "SPIRALLING TOGETHER", "OVER MILLIONS OF YEARS"]), hv(880, 1250))
    T.put(hv((120, 130), (W / 2, 250)), "17 AUGUST 2017", hv(52, 58), win(t, 249.4, 259.6, 0.8, 0.5), anchor=hv("l", "c"), wt="XL", track=hv(10, 8))
    cap(T, t, 251.0, 259.6, hv(["GRAVITATIONAL-WAVE SIGNAL GW170817"], ["GRAVITATIONAL WAVES:", "SIGNAL GW170817"]), hv(216, 340), size=hv(24, 30), col=COOL)
    cap(T, t, 255.0, 259.6, hv(["130 MILLION LIGHT-YEARS AWAY · GALAXY NGC 4993"], ["130 MILLION LIGHT-YEARS AWAY", "GALAXY NGC 4993"]), hv(900, 1290), size=hv(26, 32))
    note(T, t, 237.8, 259.6, hv("ILLUSTRATION · THE LAST ORBITS, GREATLY SLOWED · RIPPLES EXAGGERATED", "ILLUSTRATION · SLOWED · RIPPLES EXAGGERATED"))
    return T.add_to(img)


# ================================================================================================= 15  kilonova
def kilonova_img(t, tau, dimk=1.0, key="kilo"):
    cx, cy = W / 2, hv(500, 800)
    skyb = cached(("sky", key), lambda: render_sky(look_at((0, 0, 0), norm([0.6, 0.6, -0.5])), FL(40) * 1.5, gain=0.8, mw_gain=1.6))
    img = skyb.copy()
    Rk = hv(70, 70) + hv(470, 440) * (1 - math.exp(-tau / 7.0))
    L = cached(("expl", "kn"), lambda: expl_layers(3, kind="ball"))
    red = ss(2.5, 11.0, tau)
    cols = [tuple(lerp(np.array(b_), np.array(r_), red)) for b_, r_ in zip(BLUE_COLS, RED_COLS)]
    k = (0.55 + 1.3 * math.exp(-tau / 2.5)) * dimk
    draw_expl(img, L, cx, cy, Rk, cols, [1.0 * k, 0.9 * k, 0.85 * k, 0.8 * k, 0.7 * k, 0.6 * k], rot=tau * 1.2, spread=0.015, squash=0.86)
    jet = math.exp(-tau / 4.5) * ss(0.1, 0.8, tau) * dimk
    if jet > 0.01:
        ax = norm([0.22, 0.95, 0.20]); b = beams(cx, cy, 60.0, ax, half=0.07, hollow=0.0, length=16.0)
        img += b[..., None] * np.array([0.75, 0.80, 1.0], F32) * 1.1 * jet
    glare(img, cx, cy, (0.45 + 2.0 * math.exp(-tau / 1.0)) * dimk, s=1.2)
    return img, cx, cy, Rk


def shot_kilonova(t, lt):
    tau = t - T_MERGE
    img, cx, cy, Rk = kilonova_img(t, max(tau, 0.0))
    img = bloom(img, 0.70, 0.8)
    img += np.array([0.95, 0.97, 1.0], F32) * 1.2 * math.exp(-max(tau, 0) / 0.6)
    T = Text()
    T.put(hv((120, 130), (W / 2, 250)), "KILONOVA", hv(60, 68), win(t, 261.6, 279.0, 0.8, 0.6), anchor=hv("l", "c"), wt="XL", track=hv(14, 10))
    cap(T, t, 266.0, 271.2, hv(["THIS TIME THE MATTER ESCAPES"], ["THIS TIME THE MATTER ESCAPES"]), hv(880, 1260), size=hv(30, 34))
    cap(T, t, 271.6, 279.0, hv(["BY SOME ESTIMATES: SEVERAL EARTH MASSES OF GOLD"], ["BY SOME ESTIMATES:", "SEVERAL EARTH MASSES OF GOLD"]), hv(880, 1280), size=hv(30, 34))
    # element tiles
    for i, (z, sym, name, col) in enumerate(((78, "Pt", "PLATINUM", (215, 225, 235)), (79, "Au", "GOLD", YEL))):
        al = win(t, 269.2 + 0.6 * i, 279.0, 0.8, 0.6)
        if al <= 0.004: continue
        s_ = hv(150, 170); x0 = hv(1470 + i * 180, W / 2 - 185 + i * 200); y0 = hv(150, 300)
        for (p0, p1) in (((x0, y0), (x0 + s_, y0)), ((x0 + s_, y0), (x0 + s_, y0 + s_)), ((x0 + s_, y0 + s_), (x0, y0 + s_)), ((x0, y0 + s_), (x0, y0))): T.line(p0, p1, al * 0.9, col)
        T.put((x0 + 12, y0 + 10), str(z), hv(20, 22), al, col=col, wt="R", track=1)
        T.put((x0 + s_ / 2, y0 + s_ * 0.24), sym, hv(62, 70), al, col=col, anchor="c", wt="L", track=2)
        T.put((x0 + s_ / 2, y0 + s_ * 0.76), name, hv(15, 17), al, col=col, anchor="c", wt="R", track=2)
    note(T, t, 262.0, 279.0, hv("ILLUSTRATION · COLOUR FADES FROM BLUE TO RED, AS OBSERVED OVER DAYS IN 2017 · HERE COMPRESSED", "ILLUSTRATION · BLUE TO RED, AS SEEN IN 2017"))
    return T.add_to(img)


# ================================================================================================= 16  gold
def ring_layer(img, u, cx, cy, sc, alpha=1.0):
    spr = spr_at("ring", u)
    put_sprite(img, spr, cx, cy, sc, 0.0, 1.0, alpha)


def shot_gold(t, lt):
    img, cx, cy, Rk = kilonova_img(t, t - T_MERGE, dimk=1 - 0.6 * ss(0, 4, lt))
    img *= 1 - 0.35 * ss(0, 4, lt)
    a = ss(0.3, 2.2, lt)
    add_glint(img, cx, cy, 0.25 * a, (1.0, 0.75, 0.35), sig=260)
    ring_layer(img, 0.1 + lt / 8.4 * 0.45, cx, cy, hv(0.62, 0.70) * (1 + 0.012 * lt), alpha=a)
    img = bloom(img, 0.72, 0.7)
    T = Text()
    cap(T, t, 280.0, 287.4, hv(["THE GOLD IN A WEDDING RING", "VERY LIKELY FORGED LIKE THIS"], ["THE GOLD IN A WEDDING RING", "VERY LIKELY FORGED LIKE THIS"]), hv(880, 1260), size=hv(32, 36))
    note(T, t, 280.2, 287.4, hv("NEUTRON-STAR MERGERS ARE THOUGHT TO BE A MAJOR SOURCE OF GOLD · OTHER SOURCES ARE STILL DEBATED", ["MERGERS: THOUGHT TO BE A MAJOR SOURCE", "OF GOLD · OTHER SOURCES DEBATED"]))
    return T.add_to(img)


# ================================================================================================= 17  one step from a black hole
def shot_end(t, lt):
    q = ss(293.8, 297.4, t)
    Mb, Mc = star_M(0.5 + 0.06 * lt, chi=28, incl=24, roll=-14)
    R = hv(230, 230) * (1 + 0.010 * lt) * (1 + 0.22 * q); cx, cy = W / 2, hv(470, 780)
    img = ns_scene("title", cx, cy, R, Mb, Mc=Mc, lines=0.20 * (1 - q), beam=0.28 * (1 - q), drift=(60 + lt * 5, 20 + lt * 1.5), gain=(1 - q) ** 1.5, lens=1 + 1.3 * q, halo=1 - q)
    if q > 0:
        Lr = Lines(); Lr.circle(cx, cy, R + 1.5, 255 * q, 2); Lr.add_to(img, (1.0, 0.9, 0.75), gain=0.55, glow=1.2)
    img = bloom(img, 0.7, 0.75)
    T = Text()
    cap(T, t, 289.0, 293.6, hv(["THE DENSEST MATTER WE CAN OBSERVE"], ["THE DENSEST MATTER", "WE CAN OBSERVE"]), hv(880, 1250), size=hv(34, 42))
    cap(T, t, 294.2, 298.5, hv(["A LITTLE MORE MASS:  A BLACK HOLE"], ["A LITTLE MORE MASS:", "A BLACK HOLE"]), hv(880, 1250), size=hv(34, 42))
    cap(T, t, 295.2, 298.5, hv(["THE LIMIT IS THOUGHT TO LIE AT ROUGHLY 2–3 SOLAR MASSES"], ["LIMIT: ROUGHLY 2–3 SOLAR MASSES"]), hv(942, 1400), size=hv(21, 26), col=COOL)
    note(T, t, 289.2, 298.5, "ILLUSTRATION")
    return T.add_to(img)


# ================================================================================================= 18  final
def shot_final(t, lt):
    w = ss(303.0, 304.6, t)
    img = None
    if w < 0.999:
        img = earth_plate(t, "hook", lon0=110.0)
        bx, by, sc, ang = spoon_pose(); spoon(img, 0.3 + lt * 0.02, bx + 30 + lt * 3, by - lt * 2, sc, ang, bead=0.0)
        img = bloom(img, 0.72, 0.5)
    if w > 0.001:
        skyb = cached(("sky", "fin"), lambda: render_sky(look_at((0, 0, 0), norm([0.25, -0.93, -0.25])), FL(46), gain=0.9, mw_gain=2.0))
        r = skyb.copy(); cx, cy = W / 2, hv(450, 760)
        add_glint(r, cx, cy, 0.16, (1.0, 0.72, 0.35), sig=300)
        ring_layer(r, 0.45 + (t - 303.0) * 0.05, cx, cy, hv(0.60, 0.70) * (1 + 0.008 * (t - 303.0)))
        r = bloom(r, 0.72, 0.7)
        img = r if img is None else img * (1 - w) + r * w
    T = Text()
    cap(T, t, 299.8, 303.2, hv(["YOU WERE NEVER GOING TO HOLD IT."], ["YOU WERE NEVER", "GOING TO HOLD IT."]), hv(150, 270), x=hv(1000, W / 2), size=hv(34, 42))
    cap(T, t, 304.6, 310.4, hv(["BUT YOU MAY ALREADY BE WEARING A LITTLE OF ONE."], ["BUT YOU MAY ALREADY BE", "WEARING A LITTLE OF ONE."]), hv(850, 1230), x=W / 2, anchor="c", size=hv(32, 38))
    a = win(t, 307.4, 312.2, 0.9, 0.9)
    T.put((W / 2, hv(950, 1400)), "ONE TEASPOON OF A NEUTRON STAR", hv(20, 24), a, col=COOL, anchor="c", wt="R", track=hv(6, 4))
    T.put((W / 2, hv(992, 1446)), "SOURCES AND METHODS IN THE DESCRIPTION", hv(16, 20), a * 0.9, col=DIM, anchor="c", wt="R", track=hv(4, 3))
    return T.add_to(img)


FUNCS = {"hook": shot_hook, "title": shot_title, "giant": shot_giant, "sn": shot_sn, "city": shot_city, "dens": shot_dens, "mass": shot_mass,
         "grav": shot_grav, "pulsar": shot_pulsar, "magnetar": shot_magnetar, "answer": shot_answer, "thoughtA": shot_thoughtA,
         "thoughtB": shot_thoughtB, "merger": shot_merger, "kilonova": shot_kilonova, "gold": shot_gold, "end": shot_end, "final": shot_final}


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
    g = ss(0.0, 0.7, t) * (1 - ss(TL.DUR - 2.6, TL.DUR - 0.4, t))
    return np.clip(out * g, 0, 1)


def main():
    pre = "v" if VERT else ""
    if sys.argv[1] == "--png":
        os.makedirs(SCR + "/chk", exist_ok=True)
        for s in sys.argv[2:]:
            t0 = time.time(); im = frame(float(s))
            cv2.imwrite(f"{SCR}/chk/{pre}f_{float(s):06.1f}.jpg", to8(im)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92]); print(s, round(time.time() - t0, 2), "s", flush=True)
        return
    t0, t1 = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    d = SCR + ("/seg_v" if VERT else "/seg"); os.makedirs(d, exist_ok=True); out = f"{d}/seg_{f0:05d}.mp4"
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
