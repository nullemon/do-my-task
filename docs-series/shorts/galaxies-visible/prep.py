"""Galaxy sprites for "What If Galaxies Were Bright Enough to See?".
Every sprite is resampled into ONE common frame: north up, east left (the sky seen from below), SS x the on-screen
pixel scale, so the renderer only has to roll, place and scale it by 1/SS. On-screen scale: gnomonic lens with
f = F_PX px per radian (PXD = F_PX * pi / 180 px per degree), so each galaxy keeps its TRUE angular size.
  m31  NASA/JPL-Caltech GALEX (PIA15416, via unit511/space-wallpapers). Registered with an exact 3-point affine
       (nucleus, M32, M110 measured in the image -> their real RA/Dec), which fixes scale, rotation and handedness.
  m33  NASA/JPL-Caltech GALEX (PIA03033), north up; scaled so the disc spans its 70.8' D25 diameter.
  m51  X-ray NASA/CXC; UV NASA/JPL-Caltech; optical NASA/ESA/STScI/AURA; IR NASA/JPL-Caltech/Univ. of Ariz. (PIA10200),
       north up (checked: NGC 5195 sits 4.4' N, 15 deg E of the nucleus); true-size sprite + a magnified loupe sprite.
  lmc, smc  procedural lookalikes (no whole-galaxy colour image was reachable): real sizes, PAs and the real offsets
       of the bar, 30 Doradus (Tarantula), N11, N44, N159/N160, NGC 346, the SMC Wing and 47 Tucanae.
  core the Milky Way's central bulge from the star-dates/nebula-sky galactic canvas (mwsky.py), true scale.
  moon a full Moon (Solar System Scope 8k map, CC BY 4.0) at its 0.52 deg size for the x MOON comparisons.
Usage: /home/user/ttsenv/bin/python prep.py   -> SCR/sprites.npz"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import lib.core  # noqa: F401
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, lum, fbm2, smooth, bbcolor

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-galaxies-visible"
DL = os.path.join(SCR, "dl")
MOONTEX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/sss/8k_moon.jpg"
F_PX = 6000.0
PXD = F_PX * math.pi / 180.0                     # 104.7 screen px per degree
SS = 2.0                                         # sprites are stored at 2x the screen scale
K = PXD * SS                                     # sprite px per degree

M31 = (10.68471, 41.26875); M32 = (10.67425, 40.86517); M110 = (10.09208, 41.68528)


def tan_off(ra, dec, ra0, dec0):
    """gnomonic offsets (E, N) in degrees of (ra, dec) about (ra0, dec0)"""
    a, d, a0, d0 = map(math.radians, (ra, dec, ra0, dec0))
    c = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    E = math.cos(d) * math.sin(a - a0) / c
    N = (math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / c
    return math.degrees(E), math.degrees(N)


def load(p):
    return srgb_to_lin(np.asarray(Image.open(p).convert("RGB"), f32) / 255.0)


def blacklevel(img, pct):
    b = np.percentile(img.reshape(-1, 3), pct, axis=0); return np.maximum(img - b, 0)


def vivid(img, sat, con=1.0):
    y = lum(img)[..., None]
    if con != 1.0:
        mu = float(np.percentile(y, 99.0)) * 0.3 + 1e-4; img = img * (np.maximum(y, 1e-6) / mu) ** (con - 1) ; y = lum(img)[..., None]
    return np.maximum(y + (img - y) * sat, 0).astype(f32)


def ell_mask(h, w, cx, cy, a, b, pa_screen, seed, soft=0.5, rough=0.10):
    """soft noisy ellipse; a, b semi-axes in px; pa_screen = angle of the major axis on the sprite (rad, from +x)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    dx, dy = xx - cx, yy - cy; c, s = math.cos(pa_screen), math.sin(pa_screen)
    u = (dx * c + dy * s) / a; v = (-dx * s + dy * c) / b
    n = cv2.resize(fbm2((64, 64), seed, 2.4), (w, h), interpolation=cv2.INTER_CUBIC)
    r = np.sqrt(u * u + v * v) * (1 + rough * n)
    return smooth(1.0, soft, r).astype(f32)


def pa_dir(pa_deg):
    """direction of position angle pa (N through E) in sprite coords (x right = west, y down = south)"""
    p = math.radians(pa_deg); return -math.sin(p), -math.cos(p)


# ------------------------------------------------------------------------------------------------ M31 (GALEX)
def m31():
    img = load(os.path.join(DL, "sw", "4K", "andromeda_4K.png"))
    # measured in the 4K image (blurred peaks): nucleus, M32, M110
    P = np.array([[1733, 1110], [1184, 1028], [2199, 1819]], np.float64)
    Q = np.array([tan_off(*M31, *M31), tan_off(*M32, *M31), tan_off(*M110, *M31)], np.float64)
    # sprite frame: x = -E * K + cx, y = -N * K + cy
    w, h = 1000, 1000; cx, cy = w / 2, h / 2
    D = np.stack([-Q[:, 0] * K + cx, -Q[:, 1] * K + cy], 1)
    A = cv2.getAffineTransform(P.astype(f32), D.astype(f32))
    det = A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0]
    print("m31 affine scale", math.sqrt(abs(det)), "det sign", np.sign(det), "rot deg", math.degrees(math.atan2(A[1, 0], A[0, 0])))
    img = blacklevel(img, 25)
    big = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT)
    valid = cv2.warpAffine(np.ones(img.shape[:2], f32), A, (w, h), flags=cv2.INTER_LINEAR)
    valid = cv2.GaussianBlur(cv2.erode(valid, np.ones((5, 5), np.uint8)), (0, 0), 6)
    ax, ay = pa_dir(35.0); pa_s = math.atan2(ay, ax)
    m = ell_mask(h, w, cx, cy, 1.62 * K, 0.52 * K, pa_s, 31, 0.45, 0.06)
    big = vivid(big * (m * valid)[..., None], 2.6, 1.15)
    # the faint outer disc beyond the UV image (D25 = 3.17 x 1.0 deg): a soft exponential glow on the same axis
    yy, xx = np.mgrid[0:h, 0:w].astype(f32); dx, dy = xx - cx, yy - cy
    u = (dx * math.cos(pa_s) + dy * math.sin(pa_s)) / K; v = (-dx * math.sin(pa_s) + dy * math.cos(pa_s)) / K
    r = np.sqrt(u * u + (v / 0.31) ** 2)
    outer = (np.exp(-r / 0.55) * smooth(1.75, 1.3, r) * 0.24)[..., None] * np.array([0.55, 0.70, 1.0], f32)
    bul = (np.exp(-np.sqrt(u * u + (v / 0.6) ** 2) / 0.08) * 1.3 + np.exp(-np.sqrt(u * u + (v / 0.5) ** 2) / 0.25) * 0.25)[..., None] * np.array([1.0, 0.74, 0.34], f32)
    out = big + outer + bul
    return out, (cx, cy), np.maximum(m * valid, smooth(1.75, 1.2, r))


# ------------------------------------------------------------------------------------------------ M33 (GALEX)
def m33():
    img = load(os.path.join(DL, "nasa", "PIA03033.orig.jpg"))
    img = blacklevel(img, 30)
    pxam = 34.6                                                   # image px per arcmin (disc = 70.8' D25)
    k = K / 60.0 / pxam
    h0, w0 = img.shape[:2]; c0 = (1447, 1456)
    w = h = int(round(1.5 * K)); cx, cy = w / 2, h / 2
    A = np.float32([[k, 0, cx - k * c0[0]], [0, k, cy - k * c0[1]]])
    out = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_AREA)
    ax, ay = pa_dir(23.0)
    m = ell_mask(h, w, cx, cy, 0.66 * K, 0.42 * K, math.atan2(ay, ax), 33, 0.5, 0.08)
    out = vivid(out * m[..., None], 2.6, 1.12)
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    out += ((np.exp(-np.hypot(xx - cx, yy - cy) / (0.05 * K)) * 0.6 + np.exp(-np.hypot(xx - cx, yy - cy) / (0.35 * K)) * 0.05) * m)[..., None] * np.array([1.0, 0.80, 0.5], f32)
    return out, (cx, cy), m


# ------------------------------------------------------------------------------------------------ M51 (composite)
def m51():
    img = load(os.path.join(DL, "nasa", "PIA10200.orig.jpg"))
    img = blacklevel(img, 20)
    pxam = 298.0                                                  # nucleus -> NGC 5195 = 1313 px = 4.4'
    nuc = (960, 1745)
    res = {}
    for key, ppa in (("m51", K / 60.0), ("m51L", 36.0)):          # true size (sprite px) / loupe (screen px per arcmin)
        k = ppa / pxam
        w = int(round(img.shape[1] * k)) + 8; h = int(round(img.shape[0] * k)) + 8
        cx, cy = nuc[0] * k + 4, nuc[1] * k + 4
        A = np.float32([[k, 0, 4], [0, k, 4]])
        o = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_AREA)
        yy, xx = np.mgrid[0:h, 0:w].astype(f32)
        fe = smooth(0, 0.06 * w, np.minimum(xx, w - 1 - xx)) * smooth(0, 0.06 * h, np.minimum(yy, h - 1 - yy))
        o = vivid(o * fe[..., None], 1.25, 1.05)
        res[key] = (o, (cx, cy), fe)
    return res


# ------------------------------------------------------------------------------------------------ procedural Magellanic Clouds
def starfield(h, w, dens, n, seed, temps=(3500, 16000)):
    r = np.random.default_rng(seed)
    p = dens.ravel().astype(np.float64); p /= p.sum()
    idx = r.choice(h * w, n, p=p)
    sx = idx % w + r.uniform(0, 1, n); sy = idx // w + r.uniform(0, 1, n)
    fl = 0.010 * r.uniform(0, 1, n) ** (-1 / 1.3); fl = np.minimum(fl, 0.5)
    T = np.exp(r.uniform(np.log(temps[0]), np.log(temps[1]), n))
    lut = np.stack([0.4 + 0.6 * bbcolor(t) for t in np.linspace(temps[0], temps[1], 32)])
    c = lut[np.clip(((T - temps[0]) / (temps[1] - temps[0]) * 31).astype(int), 0, 31)]
    acc = np.zeros((h + 1, w + 1, 3), f32)
    x0 = np.floor(sx).astype(int); y0 = np.floor(sy).astype(int)
    np.add.at(acc, (y0, x0), (fl[:, None] * c).astype(f32))
    return cv2.GaussianBlur(acc[:h, :w], (0, 0), 0.8) * 2.0


def knot(h, w, x, y, R, seed, col, I, core=None):
    """an HII region: filamentary pink glow of radius R px"""
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    d = np.hypot(xx - x, yy - y) / R
    n1 = cv2.resize(fbm2((128, 128), seed, 1.6), (w, h), interpolation=cv2.INTER_CUBIC)
    n2 = cv2.resize(fbm2((128, 128), seed + 1, 2.4), (w, h), interpolation=cv2.INTER_CUBIC)
    fil = np.clip(1 - np.abs(n1) * 1.8, 0, 1) ** 3
    g = np.exp(-d ** 2 * 1.4) * (0.35 + 0.65 * fil) * np.clip(1 + 0.4 * n2, 0.3, 2) + np.exp(-d / 0.18) * 0.5
    out = g[..., None] * np.array(col, f32) * I
    if core is not None: out += (np.exp(-d / 0.10) * I * 1.2)[..., None] * np.array(core, f32)
    return out


def knots_local(img, x, y, R, seed, col, I):
    """a small HII region drawn on a local patch only (cheap enough for dozens)"""
    h, w = img.shape[:2]; r = int(R * 3) + 2
    x0, x1, y0, y1 = max(0, int(x) - r), min(w, int(x) + r), max(0, int(y) - r), min(h, int(y) + r)
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
    d = np.hypot(xx - x, yy - y) / R
    n = cv2.resize(fbm2((32, 32), seed, 1.8), (x1 - x0, y1 - y0), interpolation=cv2.INTER_CUBIC)
    fil = np.clip(1 - np.abs(n) * 1.6, 0, 1) ** 2
    g = np.exp(-d ** 2 * 1.3) * (0.4 + 0.6 * fil) + np.exp(-d / 0.15) * 0.6
    img[y0:y1, x0:x1] += g[..., None] * np.array(col, f32) * I


def blue_knots(img, dens, n, seed, K_, rmin, rmax, I=0.8):
    """young-star clusters: compact blue-white knots, placed where the density is high"""
    h, w = img.shape[:2]; r = np.random.default_rng(seed)
    p = dens.ravel().astype(np.float64) ** 2; p /= p.sum()
    for idx in r.choice(h * w, n, p=p):
        x, y = idx % w, idx // w; R = r.uniform(rmin, rmax) * K_
        rr = int(R * 4) + 2; x0, x1, y0, y1 = max(0, x - rr), min(w, x + rr), max(0, y - rr), min(h, y + rr)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32); d = np.hypot(xx - x, yy - y) / R
        img[y0:y1, x0:x1] += (np.exp(-d * 1.6) * I * r.uniform(0.5, 1.2))[..., None] * np.array([0.55, 0.78, 1.0], f32)


def pink_knots(img, dens, n, seed, K_, rmin, rmax, I=0.6):
    h, w = img.shape[:2]; r = np.random.default_rng(seed)
    p = dens.ravel().astype(np.float64) ** 2; p /= p.sum()
    for j, idx in enumerate(r.choice(h * w, n, p=p)):
        knots_local(img, idx % w, idx // w, r.uniform(rmin, rmax) * K_, seed * 100 + j, (1.0, 0.22, 0.52), I * r.uniform(0.5, 1.2))


def lmc():
    # extent 10.75 x 9.17 deg; sprite 12 x 11 deg
    w, h = int(12.0 * K), int(11.0 * K); cx, cy = w / 2, h / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    E = -(xx - cx) / K; N = -(yy - cy) / K                         # degrees
    def nz(sd, beta, n=256): return cv2.resize(fbm2((n, n), sd, beta), (w, h), interpolation=cv2.INTER_CUBIC)
    nA, nB, nC, nK = nz(101, 2.6), nz(102, 2.7), nz(103, 3.2), nz(105, 2.0, 512)
    r = np.sqrt((E / 5.37) ** 2 + (N / 4.58) ** 2) * (1 + 0.10 * nC)
    disc = np.exp(-r * 1.9) * smooth(1.08, 0.70, r)
    # the off-centre bar: 4.2 x 1.1 deg at PA 115, centred SW of the disc centre
    bx, by = -0.35, -0.45; p = math.radians(115.0); ue, un = math.sin(p), math.cos(p)
    a = (E - bx) * ue + (N - by) * un; b = -(E - bx) * un + (N - by) * ue
    bar = np.exp(-(a / 2.1) ** 4 - (b / 0.55) ** 2) * (1 + 0.25 * nB)
    t = np.arctan2(N - 0.2, E - 0.0); rr = np.hypot(E, N - 0.2)
    arm = np.exp(-((rr - 2.9 - 0.4 * nA) / 0.75) ** 2) * smooth(-0.1, 0.9, np.sin(t)) * np.clip(0.6 + 0.6 * nB, 0, 1.6)
    clumps = np.clip(nK - 0.2, 0, 3) ** 1.5 * (disc > 0.03)                 # clumpy star clouds
    img = (disc * (0.25 + 0.6 * clumps) * 0.10)[..., None] * np.array([0.40, 0.62, 1.0], f32) \
        + (bar * 0.22)[..., None] * np.array([1.0, 0.82, 0.55], f32) + (arm * (0.3 + clumps) * 0.08)[..., None] * np.array([0.45, 0.72, 1.0], f32)
    dust = np.clip(np.abs(nC) - 1.1, 0, 1) * 0.7 * (disc > 0.05)
    img *= (1 - dust)[..., None]
    dens = (disc * (0.3 + 2.0 * clumps) + bar * 6.0 + arm * (1 + 2 * clumps) + 0.002) * (1 - dust)
    img += starfield(h, w, dens, 700000, 104) * 1.1                          # fine grainy star texture
    img += starfield(h, w, bar + 0.001, 160000, 106, temps=(3200, 6500)) * 1.0   # dense old-star bar
    blue_knots(img, arm * (0.3 + clumps) + disc * clumps * 0.4, 70, 107, K, 0.02, 0.06, 0.9)
    pink = (1.0, 0.22, 0.52)
    for (e, n, R, I, sd) in ((1.33, 0.66, 0.42, 1.6, 111), (1.40, -0.05, 0.22, 0.9, 112), (-2.56, 3.36, 0.30, 0.9, 113),
                             (0.0, 1.80, 0.26, 0.8, 114), (-1.3, 2.6, 0.16, 0.6, 115), (2.2, 1.6, 0.14, 0.5, 116), (-0.9, -1.6, 0.12, 0.5, 117)):
        img += knot(h, w, cx - e * K, cy - n * K, R * K, sd, pink, I * 0.9, core=(0.55, 1.0, 0.9) if sd == 111 else None)
    pink_knots(img, arm + disc * clumps * 0.5, 34, 118, K, 0.04, 0.12, 0.7)
    return vivid(img.astype(f32), 1.7), (cx, cy), np.clip(disc * 4, 0, 1)


def smc():
    w, h = int(7.8 * K), int(6.2 * K); cx, cy = w * 0.60, h / 2              # extra room to the west for 47 Tuc
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    E = -(xx - cx) / K; N = -(yy - cy) / K
    def nz(sd, beta, n=192): return cv2.resize(fbm2((n, n), sd, beta), (w, h), interpolation=cv2.INTER_CUBIC)
    nA, nB, nK = nz(201, 2.4), nz(202, 2.6), nz(205, 2.0, 384)
    p = math.radians(45.0); ue, un = math.sin(p), math.cos(p)
    a = E * ue + N * un; b = -E * un + N * ue
    r = np.sqrt((a / 2.66) ** 2 + (b / 1.54) ** 2) * (1 + 0.12 * nB)
    body = np.exp(-r * 2.4) * smooth(1.08, 0.7, r)
    bar = np.exp(-(a / 1.6) ** 2 - (b / 0.45) ** 2) * (1 + 0.3 * nA)
    wing = np.exp(-((E - 1.45) / 0.75) ** 2 - ((N + 0.55) / 0.45) ** 2) * np.clip(0.5 + 0.6 * nA, 0, 1.5)
    clumps = np.clip(nK - 0.2, 0, 3) ** 1.5 * (body > 0.03)
    img = (body * (0.3 + 0.6 * clumps) * 0.12)[..., None] * np.array([0.5, 0.7, 1.0], f32) + (bar * 0.20)[..., None] * np.array([0.95, 0.88, 0.8], f32) \
        + (wing * 0.07)[..., None] * np.array([0.5, 0.7, 1.0], f32)
    img += starfield(h, w, body * (0.3 + 2 * clumps) + bar * 5 + wing * (1 + clumps) + 0.002, 260000, 203) * 1.1
    blue_knots(img, wing + bar * clumps + body * clumps * 0.3, 30, 207, K, 0.02, 0.05, 0.9)
    img += knot(h, w, cx - 0.48 * K, cy - 0.65 * K, 0.22 * K, 211, (1.0, 0.22, 0.52), 1.0)        # NGC 346
    pink_knots(img, bar + wing + body * clumps * 0.4, 16, 212, K, 0.04, 0.10, 0.7)
    # 47 Tucanae (Milky Way globular, 2.3 deg W of the SMC, 0.5 deg across)
    tx, ty = cx + 2.19 * K, cy - 0.75 * K
    d = np.hypot(xx - tx, yy - ty) / K
    img += (np.exp(-d / 0.035) * 1.2 + np.exp(-d / 0.10) * 0.15)[..., None] * np.array([1.0, 0.9, 0.7], f32)
    return vivid(img.astype(f32), 1.7), (cx, cy), np.clip(body * 4, 0, 1)


# ------------------------------------------------------------------------------------------------ Milky Way core
def core():
    """the Milky Way's central bulge as a long exposure shows it (procedural at full screen resolution, true scale:
    bulge ~ 12 x 7 deg glow, the Great Rift dust lanes along the plane, Sagittarius star clouds, pink Lagoon/Trifid knots)"""
    w, h = int(24 * PXD), int(12 * PXD); cx, cy = w / 2, h / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    l = -(xx - cx) / PXD; b = -(yy - cy) / PXD
    def nz(sd, beta, n=384): return cv2.resize(fbm2((n // 2, n), sd, beta), (w, h), interpolation=cv2.INTER_CUBIC)
    nA, nB, nC, nD = nz(401, 2.8), nz(402, 2.6), nz(403, 3.0), nz(404, 2.3, 768)
    bw = 2.2 + 0.5 * nA
    band = np.exp(-((b - 0.3 * nA) / bw) ** 2) * np.exp(-(l / 13.0) ** 2)
    bulge = np.exp(-np.sqrt((l / 6.0) ** 2 + (b / 3.6) ** 2) * 1.6)
    clouds = np.clip(0.75 + 0.3 * nB + 0.08 * nD, 0.2, 1.8)
    ridge = 1 - np.abs(nD)
    lanes = np.clip((ridge - 0.80) / 0.2, 0, 1) ** 1.2 * np.exp(-((b + 0.4 - 0.6 * nC) / 1.4) ** 2)
    rift = np.exp(-((b - 0.2 - 0.5 * nC) / (0.45 + 0.15 * nA)) ** 2) * np.clip(0.5 + 0.5 * nC, 0, 1)
    dust = np.clip(lanes * 0.8 + rift * 0.75, 0, 0.93)
    gold = np.array([1.0, 0.60, 0.24], f32); pinkish = np.array([1.0, 0.55, 0.62], f32); teal = np.array([0.45, 0.7, 1.0], f32)
    warm = np.clip(bulge * 1.5, 0, 1)[..., None]
    col = gold * warm + (teal * 0.5 + pinkish * 0.5) * (1 - warm)
    img = ((band * clouds * 0.35 + bulge * 0.55 * clouds) * (1 - dust))[..., None] * col
    img += starfield(h, w, (band * clouds + bulge * 2) * (1 - dust) + 0.01, 420000, 405, temps=(3000, 9000)) * 0.7
    for (L_, B_, R_, sd) in ((6.0, -1.3, 0.55, 411), (7.0, -0.3, 0.30, 412), (15.0, -0.7, 0.35, 413), (-3.0, 1.0, 0.25, 414)):
        img += knot(h, w, cx - L_ * PXD, cy - B_ * PXD, R_ * PXD, sd, (1.0, 0.25, 0.5), 0.5)
    fe = smooth(1.0, 0.55, np.hypot((xx - cx) / (w / 2), (yy - cy) / (h / 2))).astype(f32)
    return vivid((img * fe[..., None]).astype(f32), 1.3), (cx, cy), fe


# ------------------------------------------------------------------------------------------------ Moon
def moon():
    tex = srgb_to_lin(np.asarray(Image.open(MOONTEX).convert("RGB").resize((2048, 1024), Image.LANCZOS), f32) / 255)
    D = int(round(0.52 * K)); n = D + 4; c = n / 2
    yy, xx = np.mgrid[0:n, 0:n].astype(f32) + 0.5
    x = (xx - c) / (D / 2); y = -(yy - c) / (D / 2); r2 = x * x + y * y
    z = np.sqrt(np.clip(1 - r2, 0, 1)); lat = np.arcsin(np.clip(y, -1, 1)); lon = np.arctan2(x, z)
    u = ((lon / (2 * np.pi) + 0.5) * 2048) % 2048; v = (0.5 - lat / np.pi) * 1024
    img = cv2.remap(tex, u.astype(f32), v.astype(f32), cv2.INTER_LINEAR) * (0.6 + 0.4 * z[..., None] ** 0.3)
    a = smooth(1.0 + 1.5 / D, 1.0 - 1.5 / D, np.sqrt(r2))
    return (img * a[..., None]).astype(f32), (c, c), a


def main():
    out = {}
    items = dict(m31=m31(), m33=m33(), lmc=lmc(), smc=smc(), core=core(), moon=moon())
    items.update(m51())
    for k, (img, (cx, cy), m) in items.items():
        wgt = m[..., None]
        light = (img * wgt).sum((0, 1)) / max(wgt.sum(), 1)
        out[k] = img.astype(np.float16); out[k + "_m"] = m.astype(np.float16); out[k + "_c"] = np.array([cx, cy], f32)
        out[k + "_light"] = light.astype(f32)
        print(k, img.shape[:2], "light", np.round(light, 3), "max", float(img.max()))
    np.savez(os.path.join(SCR, "sprites.npz"), **out)
    sheet = []
    for k in ("m31", "m33", "lmc", "smc", "m51L", "core"):
        im = items[k][0]; im = 1 - np.exp(-im * 4 / max(float(np.percentile(im, 99.5)), 1e-4))
        im = cv2.resize(im, (400, int(400 * im.shape[0] / im.shape[1])))
        im = cv2.copyMakeBorder(im, 0, max(0, 420 - im.shape[0]), 0, 0, cv2.BORDER_CONSTANT)[:420]
        sheet.append(im)
    Image.fromarray((np.clip(np.concatenate(sheet, 1), 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).save(os.path.join(SCR, "sprites_sheet.jpg"))


if __name__ == "__main__":
    main()
