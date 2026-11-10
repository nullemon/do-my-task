"""Naked-eye scene: a night landscape under the real sky of 13 April 2029, ~21:46 UTC, seen from about 40 deg N in western
Europe (stars from the d3-celestial catalogue placed with the correct sidereal time), with Apophis as a moving point.
The landscape is a procedural plate (layered ridges, conifers, a valley town, mist). The asteroid's path across the stars is
illustrative: the real path depends strongly on where you stand (parallax of several degrees)."""
import math
from lib import *
import timeline as TL

LAT = math.radians(40.0); LST = math.radians(11.07 * 15)
Z = np.array([math.cos(LAT) * math.cos(LST), math.cos(LAT) * math.sin(LST), math.sin(LAT)])
N = np.array([-math.sin(LAT) * math.cos(LST), -math.sin(LAT) * math.sin(LST), math.cos(LAT)])
E = np.array([-math.sin(LST), math.cos(LST), 0.0])
TXT = (232, 236, 242); DIM = (170, 180, 195); AMB = (255, 200, 120); YEL = (255, 214, 80)
VIEWS = {1: dict(az=247, alt=19.5, fov=76, seed=3), 2: dict(az=318, alt=21, fov=70, seed=8), 3: dict(az=247, alt=19.5, fov=76, seed=3)}
STARS = {"SIRIUS": (101.29, -16.72), "PROCYON": (114.83, 5.22), "BETELGEUSE": (88.79, 7.41), "CASTOR": (113.65, 31.89), "POLLUX": (116.33, 28.03),
         "REGULUS": (152.09, 11.97), "CAPELLA": (79.17, 46.0), "ALDEBARAN": (68.98, 16.51), "POLARIS": (37.95, 89.26), "DUBHE": (165.93, 61.75)}
_c = {}


def altaz_dir(az, alt):
    a, h = math.radians(az), math.radians(alt)
    return math.cos(h) * (math.cos(a) * N + math.sin(a) * E) + math.sin(h) * Z


def view_R(v):
    return look_at((0, 0, 0), altaz_dir(v["az"], v["alt"]), up=Z)


def _ridge(rng, n, base, amp, f0, octs=6, H_=0.55):
    x = np.arange(n) / n; y = np.zeros(n); a = 1.0
    for o in range(octs):
        f = f0 * 2 ** o; ph = rng.uniform(0, 6.28, 3)
        y += a * (np.sin(2 * np.pi * f * x + ph[0]) + 0.5 * np.sin(2 * np.pi * f * 1.73 * x + ph[1]) + 0.3 * np.sin(2 * np.pi * f * 2.9 * x + ph[2]))
        a *= H_
    return base + amp * y / 1.8


def _pine(d, x, yb, h, rng, col):
    """conifer silhouette: trunk + jagged drooping tiers"""
    w = h * rng.uniform(0.16, 0.24); n = int(max(5, h / 9)); lean = rng.uniform(-0.03, 0.03) * h
    d.rectangle((x - max(1, h * 0.012), yb - h * 0.25, x + max(1, h * 0.012), yb + 2), fill=col)
    for i in range(n):
        u = i / (n - 1); y0 = yb - h * (0.14 + 0.86 * u); tw = w * (1 - u) ** 0.85 * rng.uniform(0.75, 1.15) + h * 0.008
        cx = x + lean * u; drop = h * 0.075 * rng.uniform(0.7, 1.3)
        pts = [(cx, y0 - drop * 0.9)]
        k = int(max(3, tw / 3))
        for j in range(k + 1):
            v = j / k; xx = cx + tw * v; yy = y0 + drop * v ** 1.4 + rng.uniform(-1, 1) * drop * 0.25
            pts.append((xx, yy)); pts.append((xx - tw / k * 0.45, yy - drop * 0.38 * rng.uniform(0.4, 1.0)))
        pts.append((cx, y0 + drop * 0.25))
        pr = [(2 * cx - px, py + rng.uniform(-1, 1) * drop * 0.12) for px, py in pts[::-1]]
        d.polygon(pts + pr, fill=col)


def landscape(seed):
    """returns (rgb premultiplied, alpha, additive glow) at 1080p"""
    if seed in _c: return _c[seed]
    SS = 2; w, h = W * SS, H * SS; rng = np.random.default_rng(seed)
    hy = 930 * SS                                             # astronomical horizon row
    rgb = np.zeros((h, w, 3), F32); alpha = np.zeros((h, w), F32)
    yy = np.arange(h, dtype=F32)[:, None]
    def layer(ridge_y, col, haze_col, haze, tex_amp=0.0, trees=None, tree_h=(0, 0), tree_n=0, big=None):
        im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
        pts = [(i, float(ridge_y[i])) for i in range(0, w, 2)] + [(w, h), (0, h)]
        d.polygon(pts, fill=255)
        if tree_n:
            xs = rng.uniform(0, w, tree_n)
            for x in xs:
                dens = 0.5 + 0.5 * math.sin(x / w * 23 + seed) * math.sin(x / w * 7.3 + 1)
                if rng.uniform() > 0.35 + 0.65 * dens: continue
                _pine(d, x, float(ridge_y[int(min(w - 1, x))]) + 4 * SS, rng.uniform(*tree_h) * SS, rng, 255)
        if big:
            for (x, hh) in big: _pine(d, x * SS, float(ridge_y[int(min(w - 1, x * SS))]) + 30 * SS, hh * SS, rng, 255)
        m = np.asarray(im, F32) / 255
        m = cv2.GaussianBlur(m, (0, 0), 0.6)
        c = np.array(col, F32)[None, None] * np.ones((h, w, 1), F32)
        if tex_amp:
            nz = cv2.resize(rng.standard_normal((h // 6, w // 6)).astype(F32), (w, h), interpolation=cv2.INTER_CUBIC)
            c = c * (1 + tex_amp * nz[..., None])
        # distance haze: stronger at the base of each layer (valley mist)
        dep = np.clip((yy - ridge_y.min()) / (140 * SS), 0, 1)
        c = c * (1 - haze * dep[..., None]) + np.array(haze_col, F32) * (haze * dep[..., None])
        rgb[:] = rgb * (1 - m[..., None]) + c * m[..., None]; alpha[:] = alpha * (1 - m) + m
    x = np.arange(w)
    # far range (with a snow-dusted crest), two middle ranges with forest, valley, foreground
    r1 = _ridge(rng, w, hy - 78 * SS, 46 * SS, 1.3, 7, 0.58); r1 -= 30 * SS * np.exp(-((x - w * 0.70) / (w * 0.13)) ** 2) + 18 * SS * np.exp(-((x - w * 0.22) / (w * 0.09)) ** 2)
    layer(r1, (0.060, 0.074, 0.105), (0.105, 0.100, 0.110), 0.85, tex_amp=0.03)
    dpt = (yy - r1[None, :]) / SS                                  # depth below the crest, px
    nz = cv2.resize(rng.standard_normal((h // 30, w // 60)).astype(F32), (w, h), interpolation=cv2.INTER_CUBIC)
    snow = np.clip((r1.min() + 62 * SS - r1[None, :]) / (46 * SS), 0, 1) * np.clip(dpt / 1.5, 0, 1) * np.exp(-np.clip(dpt, 0, 200) / (9 + 7 * nz.clip(-1, 1)))
    rgb += (snow * np.clip(0.75 + 0.6 * nz, 0, 1))[..., None] * np.array([0.075, 0.088, 0.115], F32)
    r2 = _ridge(rng, w, hy - 26 * SS, 22 * SS, 2.1, 6, 0.55)
    layer(r2, (0.040, 0.050, 0.070), (0.110, 0.100, 0.100), 0.8, tex_amp=0.08, tree_n=900, tree_h=(5, 11))
    # town lights in the valley in front of r2
    glow = np.zeros((h, w, 3), F32)
    tx = w * (0.60 if seed == 3 else 0.36)
    for cl in range(9):
        cxl = tx + rng.normal(0, w * 0.085); n = int(rng.uniform(8, 60)) if cl else 110
        px = cxl + rng.normal(0, w * (0.012 if cl else 0.02), n); py = hy + 17 * SS + rng.normal(0, 3.5 * SS, n) + np.abs(px - cxl) * 0.03
        for i in range(n):
            xi, yi = int(px[i]), int(py[i])
            if 2 < xi < w - 3 and 2 < yi < h - 3:
                warm = rng.uniform(); b = rng.uniform(0.2, 1.0) ** 3 * 1.1
                glow[yi:yi + 1 + (b > 0.5), xi:xi + 1 + (b > 0.5)] += b * (np.array([1.0, 0.72, 0.38], F32) if warm > 0.2 else np.array([0.8, 0.9, 1.0], F32))
    r3 = _ridge(rng, w, hy + 34 * SS, 16 * SS, 1.7, 6, 0.6)
    lights = glow.copy()
    layer(r3, (0.022, 0.029, 0.042), (0.080, 0.072, 0.070), 0.65, tex_amp=0.12, tree_n=520, tree_h=(12, 26))
    # mask the lights by everything in front of them (r3 layer), keep glow spill
    m3 = (yy > r3[None, :] - 3 * SS).astype(F32)
    lights = lights * (1 - m3[..., None])
    # foreground slope with tall conifers framing the view
    r4 = _ridge(rng, w, hy + 118 * SS, 20 * SS, 0.9, 5, 0.55) + 46 * SS * ((x / w - 0.52) ** 2) * -6 + 30 * SS
    if seed == 3: big = [(70, 560), (190, 430), (300, 300), (385, 210), (1905, 500), (1790, 380), (1700, 250), (1610, 170), (1010, 60), (1060, 82), (920, 50)]
    else: big = [(1840, 590), (1730, 440), (1620, 320), (1530, 200), (60, 330), (150, 240), (640, 70), (700, 95), (760, 60)]
    layer(r4, (0.0065, 0.0085, 0.0125), (0.012, 0.014, 0.018), 0.3, tex_amp=0.2, tree_n=140, tree_h=(26, 60), big=big)
    # grass / scrub fringe on the foreground ridge
    im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
    for i in range(5200):
        xg = rng.uniform(0, w); yb = float(r4[int(xg)]) + 3 * SS; hh = rng.uniform(4, 15) * SS
        d.line([(xg, yb), (xg + rng.uniform(-0.5, 0.5) * hh, yb - hh)], fill=255, width=int(rng.integers(1, 3)))
    m = np.asarray(im, F32) / 255
    rgb[:] = rgb * (1 - m[..., None]) + np.array([0.0065, 0.0085, 0.0125], F32) * m[..., None]; alpha[:] = np.maximum(alpha, m)
    # mist bands in the valley
    mist = cv2.resize(rng.standard_normal((6, 40)).astype(F32), (w, h), interpolation=cv2.INTER_CUBIC)
    band = np.exp(-((yy - (hy + 22 * SS)) / (16 * SS)) ** 2) * np.clip(0.55 + 0.4 * mist, 0, 1) * (1 - m3 * 0.0)
    front = (yy > r4[None, :]).astype(F32)
    mist_a = band * 0.30 * (1 - front) * alpha
    rgb[:] = rgb * (1 - mist_a[..., None]) + np.array([0.075, 0.072, 0.078], F32) * mist_a[..., None]
    gl = cv2.GaussianBlur(lights, (0, 0), 0.9 * SS) * 5 + cv2.GaussianBlur(lights, (0, 0), 5 * SS) * 5 + cv2.GaussianBlur(lights, (0, 0), 40 * SS) * 22
    gl = gl * (1 - front[..., None] * 0.97)
    ds = lambda a: cv2.resize(a, (W, H), interpolation=cv2.INTER_AREA)
    _c[seed] = (ds(rgb * alpha[..., None] if False else rgb), ds(alpha), ds(gl), tx / SS)
    return _c[seed]


def sky_base(which):
    key = ("skyb", which)
    if key in _c: return _c[key]
    v = VIEWS[which]; R = view_R(v); f = (W / 2) / math.tan(math.radians(v["fov"]) / 2)
    st = render_sky(R, f, mag_lim=8.6, mag_min=4.2, gain=0.85, mw_gain=1.3)
    yy, xx = np.mgrid[0:H, 0:W].astype(F32)
    alt = np.degrees(np.arctan2(-(yy - H / 2) / f * math.cos(math.radians(v["alt"])) + math.sin(math.radians(v["alt"])), 1.0))  # rough altitude
    ext = np.exp(-0.16 / np.sin(np.radians(np.clip(alt, 0.8, 90)) + 0.035))
    _, _, _, tx = landscape(v["seed"])
    g = np.clip((alt + 2) / 55, 0, 1)
    bgc = lerp(np.array([0.085, 0.098, 0.130], F32), np.array([0.012, 0.017, 0.036], F32), (g ** 0.5)[..., None])
    dome = np.exp(-((xx - tx) / 520) ** 2) * np.exp(-np.clip(alt, 0, 90) / 9.0)
    bgc = bgc + dome[..., None] * np.array([0.13, 0.085, 0.04], F32)
    bgc += (np.exp(-np.clip(alt, 0, 90) / 14.0) * 0.012)[..., None] * np.array([0.5, 1.0, 0.6], F32)          # airglow
    _c[key] = (st * ext[..., None] + bgc, ext, R, f)
    return _c[key]


def frame(t, lt, which):
    v = VIEWS[which]
    base, ext, R, f = sky_base(which)
    img = base.copy()
    rs = np.random.default_rng(int(t * 24) // 2)
    br = render_sky(R, f, mag_lim=4.2, gain=1.1, mw_gain=0.0, twinkle=lambda n: (1 + 0.16 * rs.standard_normal(n)).clip(0.5, 1.6).astype(F32))
    img += br * ext[..., None]
    T = Text()
    # Apophis: an illustrative straight path across the field
    if which in (1, 3):
        u = (t - 175.0) / 19.4 * 0.62 if which == 1 else 0.50 + (t - 303.8) / 14.2 * 0.5
        p0, p1 = np.array([330.0, 610.0]), np.array([1650.0, 150.0])
        la, lb = (176.6, 194.6) if which == 1 else (304.4, 309.5)
    else:
        u = (t - 291.4) / 6.9 * 0.5 + 0.2; p0, p1 = np.array([1500.0, 640.0]), np.array([420.0, 200.0]); la, lb = 0, 0
    p = p0 + (p1 - p0) * u
    e = float(ext[int(np.clip(p[1], 0, H - 1)), int(np.clip(p[0], 0, W - 1))])
    amp = 1.25 * e
    # short trail (persistence, as in a long exposure)
    m = np.zeros((H, W), F32); q = p0 + (p1 - p0) * max(0, u - 0.035)
    cv2.line(m, (int(q[0]), int(q[1])), (int(p[0]), int(p[1])), 1.0, 1, cv2.LINE_AA)
    img += cv2.GaussianBlur(m, (0, 0), 1.0)[..., None] * np.array([1.0, 0.9, 0.72], F32) * 0.22 * e
    add_glint(img, p[0], p[1], amp, (1.0, 0.93, 0.80), sig=1.5, streak=4); add_glint(img, p[0], p[1], amp * 0.16, (1.0, 0.8, 0.55), sig=7)
    fg, al, gl, _ = landscape(v["seed"])
    img = img * (1 - al[..., None]) + fg * al[..., None] + gl * (0.92 + 0.08 * math.sin(t * 2.1))
    img = bloom(img, 0.6, 0.45)
    # labels
    if which in (1, 3):
        a_l = win(t, 177.2, 194.0) if which == 1 else win(t, 304.2, 309.0) * 0
        for nm, (ra, dec) in STARS.items():
            d = np.array([math.cos(math.radians(dec)) * math.cos(math.radians(ra)), math.cos(math.radians(dec)) * math.sin(math.radians(ra)), math.sin(math.radians(dec))])
            q = R @ d
            if -q[2] > 0.1:
                x = W / 2 + f * q[0] / -q[2]; y = H / 2 - f * q[1] / -q[2]
                if 40 < x < W - 160 and 40 < y < 860 and al[int(y), int(x)] < 0.1: T.put((x + 14, y + 8), nm, 13, a_l * 0.55, col=DIM, track=2.5)
    if which == 1:
        T.put((p[0] + 20, p[1] - 34), "APOPHIS", 19, win(t, 176.6, 194.2), col=AMB)
        T.put((120, 96), "WESTERN EUROPE  ·  13 APRIL 2029  ·  LATE EVENING", 27, win(t, 175.6, 194.2))
        T.put((120, 150), "MAGNITUDE ≈ 3  ·  ABOUT AS BRIGHT AS THE STARS OF THE LITTLE DIPPER", 21, win(t, 177.6, 187.6), col=DIM)
        T.put((120, 150), "AT ITS FASTEST: THE WIDTH OF THE FULL MOON IN UNDER A MINUTE", 21, win(t, 181.8 + 6.2, 194.2), col=DIM)
        T.put((W - 60, 1030), "REAL STAR POSITIONS FOR THE DATE  ·  ASTEROID PATH ILLUSTRATIVE (IT DEPENDS ON WHERE YOU STAND)  ·  TIME-LAPSE", 15, win(t, 175.6, 194.0) * 0.7, col=DIM, anchor="r")
    if which == 3:
        T.put((W / 2, 300), "13 APRIL 2029", 30, win(t, 305.0, 316.4, 1.0, 1.4), anchor="c", col=AMB, track=10)
        T.put((W / 2, 356), "LOOK UP.", 104, win(t, 308.2, 316.4, 1.2, 1.4), anchor="c", wt="T", track=26)
        T.put((W / 2, 1004), "VISUALISATION  ·  ASTEROID SHAPE IS AN ARTIST'S MODEL  ·  EARTH AND MOON IMAGERY: NASA", 15, win(t, 310.5, 316.6) * 0.7, anchor="c", col=DIM)
    return T.add_to(img)
