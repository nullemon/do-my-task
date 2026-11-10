"""Render primitives for "FRIDAY THE 13TH, 2029" (numpy + OpenCV + PIL, float32 linear-ish display colour 0..1).

  * sphere renderer for the Earth (Blue Marble day map, night lights, drifting clouds with shadows, relief shading from an
    elevation map, ocean glint, layered limb scattering) and the Moon (albedo + bump relief),
  * real star field (d3-celestial stars to mag 8 + a faint synthetic population below that) and a Milky Way built from
    the d3-celestial brightness contours with procedural dust structure,
  * thin anti-aliased 3D lines / glints, text in Inter Light, bloom.
World frame in the physical shots = equatorial (z = Earth's north pole, x = RA 0), km.
"""
import os, sys, json, math, functools
SP = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad"
SCR = SP + "/series/10-apophis-2029"
sys.path.insert(0, SCR + "/pylib")
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
cv2.setNumThreads(1)
W, H, FPS = 1920, 1080, 24
G = SP + "/dl_globe/package/example"
DL = SCR + "/dl"
TEX = SCR + "/tex"
F32 = np.float32


def ss(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0); return t * t * (3 - 2 * t)


def win(t, a, b, fi=0.8, fo=0.8):
    return ss(a, a + fi, t) * (1 - ss(b - fo, b, t))


def lerp(a, b, u): return a + (b - a) * u
def norm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)


def rot_axis(axis, ang):
    a = norm(axis); c, s = math.cos(ang), math.sin(ang); x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def look_at(eye, target, up=(0, 0, 1)):
    """rows = camera axes in world coords: x right, y up, z toward the viewer (camera looks along -z)"""
    f = norm(np.asarray(target, float) - np.asarray(eye, float)); r = norm(np.cross(f, up)); u = np.cross(r, f)
    return np.stack([r, u, -f])


class Cam:
    def __init__(self, eye, target, fov_deg, up=(0, 0, 1), roll=0.0):
        self.eye = np.asarray(eye, float); self.R = look_at(eye, target, up)
        if roll: self.R = rot_axis((0, 0, 1), roll) @ self.R
        self.f = (W / 2) / math.tan(math.radians(fov_deg) / 2); self.ox = 0.0; self.oy = 0.0

    def proj(self, P):
        """world points (N,3) -> x, y (px), depth (>0 in front)"""
        q = (np.asarray(P, float) - self.eye) @ self.R.T
        d = -q[..., 2]; dd = np.where(d > 1e-9, d, np.nan)
        return W / 2 + self.ox + self.f * q[..., 0] / dd, H / 2 + self.oy - self.f * q[..., 1] / dd, d

    def sphere(self, c, r):
        x, y, d = self.proj(np.asarray(c, float)[None]); return float(x[0]), float(y[0]), float(self.f * r / d[0]), float(d[0])

    def dirs(self, D):
        """world directions (N,3) -> px for objects at infinity"""
        q = np.asarray(D, float) @ self.R.T; d = -q[:, 2]; ok = d > 0.05; dd = np.where(ok, d, 1)
        return W / 2 + self.f * q[:, 0] / dd, H / 2 - self.f * q[:, 1] / dd, ok


# ------------------------------------------------------------------------------------------------ textures
@functools.lru_cache(None)
def tex(name):
    if name == "day": a = cv2.imread(G + "/img/earth-blue-marble.jpg")[..., ::-1]
    elif name == "night": a = cv2.imread(G + "/img/earth-night.jpg")[..., ::-1]
    elif name == "water":
        a = cv2.imread(DL + "/earth/water_4k.png", cv2.IMREAD_UNCHANGED); a = a[..., 0] if a.ndim == 3 else a
    elif name == "cloud": a = np.asarray(Image.open(G + "/clouds/clouds.png").convert("RGBA"))[..., 3]
    elif name == "elev": a = cv2.imread(DL + "/earth/elev_bump_4k.jpg", 0)
    elif name == "moon": a = cv2.imread(DL + "/moon/moonmap1k.jpg")[..., ::-1]
    elif name == "moonbump": a = cv2.imread(DL + "/moon/moonbump1k.jpg", 0)
    a = np.ascontiguousarray(a).astype(F32) / 255
    if name == "day": a = a ** 1.08
    if name in ("elev", "moonbump"):
        # east/north slopes (per texel), pre-blurred a little
        a = cv2.GaussianBlur(a, (0, 0), 0.8 if name == 'elev' else 1.1)
        gx = (np.roll(a, -1, 1) - np.roll(a, 1, 1)); gy = np.zeros_like(a); gy[1:-1] = a[:-2] - a[2:]
        a = np.dstack([gx, gy, a])
    return a


def samp(t, lat, lon):
    h, w = t.shape[:2]
    mx = (((lon / (2 * np.pi) + 0.5) % 1.0) * w - 0.5).astype(F32); my = ((0.5 - lat / np.pi) * h - 0.5).astype(F32)
    return cv2.remap(t, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def _grid(cx, cy, R, margin):
    x0 = int(max(0, math.floor(cx - R - margin))); x1 = int(min(W, math.ceil(cx + R + margin)))
    y0 = int(max(0, math.floor(cy - R - margin))); y1 = int(min(H, math.ceil(cy + R + margin)))
    if x1 <= x0 or y1 <= y0: return None
    xs = (np.arange(x0, x1, dtype=F32) + 0.5 - cx) / R; ys = -(np.arange(y0, y1, dtype=F32) + 0.5 - cy) / R
    u, v = np.meshgrid(xs, ys)
    return x0, y0, x1, y1, u, v


def draw_earth(img, cx, cy, R, M, sun, t=0.0, clouds=1.0, night_gain=1.0, exposure=1.0, atmo=1.0):
    """Composite the Earth into img (H,W,3 float). M: 3x3, body = M @ camera-space normal (camera x right, y up, z to viewer).
    sun: unit vector to the Sun in camera space. t drifts the clouds."""
    hs = max(1.6, R * 0.016)                                   # scattering scale height in px (exaggerated ~1.5x)
    g = _grid(cx, cy, R, hs * 9 + 4)
    if g is None: return
    x0, y0, x1, y1, u, v = g
    rr = u * u + v * v; z = np.sqrt(np.clip(1 - rr, 0, 1)); inside = rr < 1
    sun = np.asarray(sun, F32)
    ndl = u * sun[0] + v * sun[1] + z * sun[2]
    Mf = M.astype(F32)
    bx = u * Mf[0, 0] + v * Mf[0, 1] + z * Mf[0, 2]; by = u * Mf[1, 0] + v * Mf[1, 1] + z * Mf[1, 2]; bz = u * Mf[2, 0] + v * Mf[2, 1] + z * Mf[2, 2]
    lat = np.arcsin(np.clip(bz, -1, 1)); lon = np.arctan2(by, bx)
    sb = Mf @ sun                                             # sun in body frame
    cl_, sl_ = np.cos(lon), np.sin(lon); cb_ = np.cos(lat); sb_ = bz
    se = -sl_ * sb[0] + cl_ * sb[1]                           # sun component toward local east / north
    sn = -sb_ * cl_ * sb[0] - sb_ * sl_ * sb[1] + cb_ * sb[2]
    day = samp(tex("day"), lat, lon); el = samp(tex("elev"), lat, lon); wat = samp(tex("water"), lat, lon)
    lit = np.clip(ndl, 0, 1); term = np.clip((ndl + 0.06) / 0.22, 0, 1); term = term * term * (3 - 2 * term)
    # relief shading (stronger toward the terminator)
    relief = np.clip(1 + 26.0 * (el[..., 0] * se + el[..., 1] * sn) / np.maximum(lit, 0.18), 0.35, 1.9)
    surf = day * (lit ** 0.85 * term * relief * 1.25)[..., None]
    # ocean glint (view = +z)
    hv = sun + np.array([0, 0, 1], F32); hv /= np.linalg.norm(hv)
    ndh = np.clip(u * hv[0] + v * hv[1] + z * hv[2], 0, 1)
    spec = wat * (ndh ** 90 * 0.9 + ndh ** 14 * 0.10) * term
    surf += spec[..., None] * np.array([1.0, 0.92, 0.78], F32)
    # clouds + their shadows (shadow = cloud map sampled a little toward the sun)
    dl = 0.0020 * t
    if clouds > 0:
        c = samp(tex("cloud"), lat, lon - dl) * clouds
        k = 0.012 / np.maximum(cb_, 0.2)
        c_sh = samp(tex("cloud"), lat + sn * 0.012, lon - dl + se * k) * clouds
        c_up = samp(tex("cloud"), lat + sn * 0.004, lon - dl + se * k * 0.33) * clouds
        surf *= (1 - 0.55 * np.clip(c_sh - c * 0.5, 0, 1) * (1 - c))[..., None]
        cshade = np.clip(1.0 - 1.6 * (c_up - c), 0.55, 1.35)        # self-shading: brighter on the sunward edge
        cw = (lit ** 0.75 * term * cshade * 1.12)
        ccol = cw[..., None] * np.array([1.0, 1.0, 1.02], F32)
        ccol = ccol * (1 - 0.35 * np.exp(-((ndl - 0.02) / 0.10) ** 2))[..., None] + \
            np.array([0.50, 0.26, 0.14], F32) * (np.exp(-((ndl - 0.05) / 0.07) ** 2) * 0.22 * c)[..., None]
        ca = np.clip(c * 1.15, 0, 1)[..., None]
        surf = surf * (1 - ca) + ccol * ca
    else:
        c = 0.0
    # warm terminator
    surf *= (1 - 0.45 * np.exp(-((ndl - 0.04) / 0.10) ** 2))[..., None] * np.array([1, 1, 1], F32) + \
        (0.45 * np.exp(-((ndl - 0.04) / 0.10) ** 2))[..., None] * np.array([1.0, 0.62, 0.42], F32)
    # night lights
    if night_gain > 0:
        nl = samp(tex("night"), lat, lon)
        lum = np.clip(nl[..., 0] - 0.16, 0, 1) ** 1.1 * 5.0
        dark = np.clip((-ndl + 0.02) / 0.16, 0, 1)
        surf += (lum * dark * (1 - 0.75 * c) * night_gain)[..., None] * np.array([1.0, 0.76, 0.44], F32)
        # faint moon/star-lit surface so the night side is not a black hole
        surf += nl * (0.16 * dark * (1 - 0.6 * c))[..., None] * np.array([0.5, 0.8, 1.15], F32)
    # atmosphere: in-scattering grows toward the limb; blue by day, thin orange line at the terminator
    path = 1.0 / np.maximum(z, 0.06)
    dayf = np.clip((ndl + 0.18) / 0.5, 0, 1)
    ins = (1 - np.exp(-0.085 * path)) * dayf * atmo
    surf = surf * (1 - 0.55 * ins[..., None]) + ins[..., None] * np.array([0.30, 0.52, 1.0], F32) * 0.95
    tw = np.exp(-((ndl + 0.02) / 0.09) ** 2) * (1 - np.exp(-0.06 * path)) * atmo
    surf += tw[..., None] * np.array([0.9, 0.36, 0.12], F32) * 0.55
    surf *= exposure
    # outside: layered halo
    r = np.sqrt(rr); hpx = np.clip((r - 1) * R, 0, None)
    dirl = np.clip((u * sun[0] + v * sun[1]) / np.maximum(r, 1e-3) * 1.0 + 0.35 + sun[2] * 0.3, 0, 1)
    twl = np.exp(-(((u * sun[0] + v * sun[1]) / np.maximum(r, 1e-3) + 0.03) / 0.14) ** 2)
    halo = (np.exp(-hpx / hs) * 0.85 + np.exp(-hpx / (hs * 3.5)) * 0.16)
    hcol = (halo * dirl)[..., None] * np.array([0.32, 0.56, 1.0], F32) + (halo * twl * 0.22)[..., None] * np.array([1.0, 0.42, 0.15], F32)
    hcol += (np.exp(-hpx / (hs * 0.6)) * 0.035)[..., None] * np.array([0.3, 0.8, 0.45], F32)       # faint airglow line
    hcol *= np.where(inside, 0, 1)[..., None] * atmo * exposure
    a = np.clip((1 - r) * R + 0.5, 0, 1)[..., None]
    reg = img[y0:y1, x0:x1]
    reg[:] = reg * (1 - a) + surf * a + hcol * (1 - a)


def draw_moon(img, cx, cy, R, M, sun, exposure=1.0):
    g = _grid(cx, cy, R, 2)
    if g is None: return
    x0, y0, x1, y1, u, v = g
    rr = u * u + v * v; z = np.sqrt(np.clip(1 - rr, 0, 1)); sun = np.asarray(sun, F32)
    ndl = u * sun[0] + v * sun[1] + z * sun[2]; Mf = M.astype(F32)
    bx = u * Mf[0, 0] + v * Mf[0, 1] + z * Mf[0, 2]; by = u * Mf[1, 0] + v * Mf[1, 1] + z * Mf[1, 2]; bz = u * Mf[2, 0] + v * Mf[2, 1] + z * Mf[2, 2]
    lat = np.arcsin(np.clip(bz, -1, 1)); lon = np.arctan2(by, bx); sb = Mf @ sun
    cl_, sl_ = np.cos(lon), np.sin(lon); cb_ = np.cos(lat)
    se = -sl_ * sb[0] + cl_ * sb[1]; sn = -bz * cl_ * sb[0] - bz * sl_ * sb[1] + cb_ * sb[2]
    alb = samp(tex("moon"), lat, lon); b = samp(tex("moonbump"), lat, lon)
    lit = np.clip(ndl, 0, 1)
    relief = np.clip(1 + 2.6 * (b[..., 0] * se + b[..., 1] * sn) / np.maximum(lit, 0.22), 0.15, 2.0)
    # lunar surface is nearly Lommel-Seeliger: little limb darkening
    ls = lit / np.maximum(lit + np.clip(z, 0.02, 1), 1e-3) * 2
    surf = alb ** 1.25 * (ls * relief * np.clip(ndl / 0.03, 0, 1))[..., None] * 1.1 * exposure
    a = np.clip((1 - np.sqrt(rr)) * R + 0.5, 0, 1)[..., None]
    reg = img[y0:y1, x0:x1]; reg[:] = reg * (1 - a) + surf * a


# ------------------------------------------------------------------------------------------------ sky
@functools.lru_cache(None)
def star_catalog():
    s = json.load(open(DL + "/package/data/stars.8.json"))["features"]
    ra = np.radians([f["geometry"]["coordinates"][0] for f in s]); dec = np.radians([f["geometry"]["coordinates"][1] for f in s])
    mag = np.array([f["properties"]["mag"] for f in s], float)
    bv = np.array([float(f["properties"]["bv"] or 0.6) if f["properties"]["bv"] not in ("", None) else 0.6 for f in s])
    # faint synthetic population 8..11.5 mag, denser toward the galactic plane
    rng = np.random.default_rng(3); n = 420000
    d = rng.standard_normal((n * 2, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    gp = norm([-0.8676, -0.1981, 0.4560])                      # north galactic pole (equatorial)
    b = np.arcsin(np.clip(d @ gp, -1, 1)); keep = rng.uniform(0, 1, n * 2) < (0.22 + 0.78 * np.exp(-np.abs(b) / 0.22))
    d = d[keep][:n]
    m2 = 8.0 + 3.5 * rng.uniform(0, 1, len(d)) ** 0.42
    D = np.concatenate([np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], 1), d])
    mag = np.concatenate([mag, m2]); bv = np.concatenate([bv, rng.normal(0.75, 0.35, len(d))])
    t = np.clip((bv + 0.3) / 1.9, 0, 1)[:, None]
    col = np.where(t < 0.45, lerp(np.array([0.72, 0.82, 1.0]), np.array([1.0, 0.98, 0.95]), t / 0.45),
                   lerp(np.array([1.0, 0.98, 0.95]), np.array([1.0, 0.70, 0.45]), (t - 0.45) / 0.55))
    return D, mag, col.astype(F32)


@functools.lru_cache(None)
def milkyway_map():
    """equirect (RA/Dec) brightness map of the Milky Way: analytic disc + bulge in galactic coordinates, with the Great
    Rift, the main star clouds and the Magellanic Clouds placed where they are, and fractal dust structure"""
    fn = TEX + "/mw2.npy"
    if os.path.exists(fn): return np.load(fn)
    Wm, Hm = 2880, 1440
    ra = ((np.arange(Wm, dtype=F32) + 0.5) / Wm - 0.5) * 2 * np.pi; dec = (0.5 - (np.arange(Hm, dtype=F32) + 0.5) / Hm) * np.pi
    RA, DEC = np.meshgrid(ra, dec)
    eq = np.stack([np.cos(DEC) * np.cos(RA), np.cos(DEC) * np.sin(RA), np.sin(DEC)], -1)
    Gm = np.array([[-0.0548755604, -0.8734370902, -0.4838350155], [0.4941094279, -0.4448296300, 0.7469822445], [-0.8676661490, -0.1980763734, 0.4559837762]], F32)
    g = eq @ Gm.T; l = np.degrees(np.arctan2(g[..., 1], g[..., 0])); b = np.degrees(np.arcsin(np.clip(g[..., 2], -1, 1)))
    rng = np.random.default_rng(5)
    def fbm3(scale, octs, seed):
        """fractal noise continuous on the sphere (sum of random plane waves in 3D)"""
        r = np.random.default_rng(seed); out = np.zeros((Hm, Wm), F32); amp = 1.0; f = scale; tot = 0
        for o in range(octs):
            for _ in range(18):
                k = r.standard_normal(3); k = k / np.linalg.norm(k) * f * r.uniform(0.7, 1.4)
                out += amp * np.cos(g[..., 0] * k[0] + g[..., 1] * k[1] + g[..., 2] * k[2] + r.uniform(0, 6.28))
            tot += amp * 4.2; amp *= 0.62; f *= 2
        return out / tot
    warp = fbm3(5, 5, 1) * 5.5
    bw = b + warp * (0.4 + 0.6 * np.exp(-(l / 90.0) ** 2))
    cl = np.cos(np.radians(l))
    h = 4.2 + 3.2 * np.exp(-(l / 40.0) ** 2)                                  # scale height in degrees, fatter near the centre
    disc = np.exp(-np.abs(bw) / h) * (0.34 + 0.66 * (0.5 + 0.5 * cl) ** 1.6)
    bulge = 1.5 * np.exp(-(l / 17.0) ** 2 - (bw / 8.5) ** 2)
    wide = 0.20 * np.exp(-np.abs(b) / 16.0) * (0.45 + 0.55 * (0.5 + 0.5 * cl))
    def blob(l0, b0, sl, sb, a_):
        dl = (l - l0 + 180) % 360 - 180; return a_ * np.exp(-(dl / sl) ** 2 - ((bw - b0) / sb) ** 2)
    clouds = blob(78, 1.5, 12, 4, 0.55) + blob(27, -2.5, 6, 3.5, 0.6) + blob(6, -4.5, 7, 3.5, 0.7) + blob(-73, -1, 9, 3, 0.55) + blob(-50, 0, 14, 3.5, 0.35) + blob(110, 0, 16, 3, 0.2)
    mw = disc + bulge + clouds
    # dust: the Great Rift (Cygnus -> Sagittarius) and general lanes hugging the plane
    dl0 = l - 30
    rift = np.exp(-(dl0 / 42.0) ** 2) * np.exp(-((bw - 1.8 - 2.0 * np.sin(np.radians(l * 3.0))) / 2.3) ** 2)
    lanes = np.clip(fbm3(14, 6, 2) * 2.6 + 0.25, 0, 1) * np.exp(-np.abs(bw) / 7.0)
    fil = np.clip(fbm3(30, 5, 3) * 3.0 + 0.1, 0, 1) * np.exp(-np.abs(bw) / 10.0)
    dust = np.clip(1 - 0.78 * rift - 0.62 * lanes - 0.25 * fil, 0.05, 1)
    grain = 1 + 0.55 * fbm3(60, 5, 4)
    mw = mw * dust * grain + wide
    # Magellanic Clouds
    def eqblob(ra0, dec0, sig, a_):
        c = np.array([math.cos(math.radians(dec0)) * math.cos(math.radians(ra0)), math.cos(math.radians(dec0)) * math.sin(math.radians(ra0)), math.sin(math.radians(dec0))], F32)
        ang = np.degrees(np.arccos(np.clip(eq @ c, -1, 1))); return a_ * np.exp(-(ang / sig) ** 2)
    mw += (eqblob(80.9, -69.8, 3.2, 0.75) + eqblob(13.2, -72.8, 1.6, 0.5)) * (1 + 0.5 * fbm3(50, 4, 6))
    mw = np.clip(mw, 0, None).astype(F32)
    os.makedirs(TEX, exist_ok=True); np.save(fn, mw); return mw


def render_sky(R, f, mag_lim=10.5, mag_min=-9.0, gain=1.0, mw_gain=1.0, size=(W, H), center=None, twinkle=None):
    """R: rows = camera axes in equatorial coords (x right, y up, z toward viewer). Returns float (h,w,3)."""
    w, h = size; cxp, cyp = center or (w / 2, h / 2)
    D, mag, col = star_catalog()
    sel = (mag < mag_lim) & (mag >= mag_min)
    q = D[sel] @ R.T; d = -q[:, 2]; ok = d > 0.1
    x = cxp + f * q[ok, 0] / d[ok]; y = cyp - f * q[ok, 1] / d[ok]
    inb = (x > -2) & (x < w + 1) & (y > -2) & (y < h + 1)
    x, y = x[inb], y[inb]; m = mag[sel][ok][inb]; c = col[sel][ok][inb]
    flux = (10 ** (-0.4 * (m - 6.2)) * gain).astype(F32)
    if twinkle is not None: flux = flux * twinkle(len(flux))
    img = np.zeros((h + 4, w + 4, 3), F32)
    xi = np.floor(x).astype(int); yi = np.floor(y).astype(int); fx = (x - xi).astype(F32); fy = (y - yi).astype(F32)
    for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(img, (yi + dy + 2, xi + dx + 2), c * (flux * wgt)[:, None])
    img = img[2:-2, 2:-2]
    core = cv2.GaussianBlur(img, (0, 0), 0.75) * 2.6
    glow = cv2.GaussianBlur(np.clip(img, 0, 60), (0, 0), 3.2) * 1.3 + cv2.GaussianBlur(np.clip(img - 1.5, 0, 60), (0, 0), 11) * 2.0
    out = core + glow
    out = 1 - np.exp(-out * 1.1)                              # soft shoulder so bright stars saturate gently
    if mw_gain > 0:
        mwm = milkyway_map(); Hm, Wm = mwm.shape
        xs = (np.arange(w, dtype=F32) + 0.5 - cxp) / f; ys = -(np.arange(h, dtype=F32) + 0.5 - cyp) / f
        u, v = np.meshgrid(xs, ys); nrm = 1 / np.sqrt(u * u + v * v + 1)
        Rf = R.astype(F32)
        wx = (u * Rf[0, 0] + v * Rf[1, 0] - Rf[2, 0]) * nrm; wy = (u * Rf[0, 1] + v * Rf[1, 1] - Rf[2, 1]) * nrm; wz = (u * Rf[0, 2] + v * Rf[1, 2] - Rf[2, 2]) * nrm
        ra = np.arctan2(wy, wx); dec = np.arcsin(np.clip(wz, -1, 1))
        mx = ((ra / (2 * np.pi) + 0.5) % 1.0 * Wm - 0.5).astype(F32); my = ((0.5 - dec / np.pi) * Hm - 0.5).astype(F32)
        mwv = cv2.remap(mwm, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        out += mwv[..., None] * np.array([0.060, 0.062, 0.078], F32) * mw_gain + (np.clip(mwv - 0.5, 0, 3) ** 1.5)[..., None] * np.array([0.085, 0.066, 0.045], F32) * mw_gain
    return out


# ------------------------------------------------------------------------------------------------ 2D helpers
def bloom(img, thr=0.75, gain=0.55):
    small = cv2.resize(np.clip(img - thr, 0, 4), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(small, (0, 0), 6) + 0.6 * cv2.GaussianBlur(small, (0, 0), 20)
    return img + cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * gain


def add_glint(img, x, y, amp, col=(1, 1, 1), sig=1.2, streak=0.0):
    """additive gaussian point (with optional horizontal lens streak)"""
    r = int(max(4, sig * 4 + streak * 3)); x0, y0 = int(round(x)) - r, int(round(y)) - r
    if x0 >= W or y0 >= H or x0 + 2 * r + 1 <= 0 or y0 + 2 * r + 1 <= 0: return
    xs = np.arange(x0, x0 + 2 * r + 1) - x; ys = np.arange(y0, y0 + 2 * r + 1) - y
    gx, gy = np.meshgrid(xs, ys); k = np.exp(-(gx * gx + gy * gy) / (2 * sig * sig))
    if streak > 0: k += 0.35 * np.exp(-(gx / (streak * 2.2)) ** 2 - (gy / (sig * 0.6)) ** 2) + 0.15 * np.exp(-(gy / (streak * 0.9)) ** 2 - (gx / (sig * 0.6)) ** 2)
    xa, xb = max(0, x0), min(W, x0 + 2 * r + 1); ya, yb = max(0, y0), min(H, y0 + 2 * r + 1)
    img[ya:yb, xa:xb] += (k[ya - y0:yb - y0, xa - x0:xb - x0] * amp)[..., None].astype(F32) * np.array(col, F32)


class Lines:
    """8-bit AA line layer (cv2) composited additively with a soft glow."""
    def __init__(self): self.l = np.zeros((H, W), np.uint8)
    def poly(self, x, y, a=255, th=1, closed=False, dash=None):
        ok = np.isfinite(x) & np.isfinite(y) & (np.abs(x) < 20000) & (np.abs(y) < 20000)
        pts = np.stack([x, y], 1) * 16
        segs = []; cur = []
        for i in range(len(x)):
            if ok[i] and (dash is None or (i // dash) % 2 == 0): cur.append(pts[i])
            else:
                if len(cur) > 1: segs.append(np.array(cur).round().astype(np.int32))
                cur = []
        if len(cur) > 1: segs.append(np.array(cur).round().astype(np.int32))
        cv2.polylines(self.l, segs, closed and dash is None and ok.all(), int(a), th, cv2.LINE_AA, 4)
    def seg(self, x0, y0, x1, y1, a=255, th=1):
        cv2.line(self.l, (int(round(x0 * 16)), int(round(y0 * 16))), (int(round(x1 * 16)), int(round(y1 * 16))), int(a), th, cv2.LINE_AA, 4)
    def circle(self, x, y, r, a=255, th=1):
        cv2.circle(self.l, (int(round(x * 16)), int(round(y * 16))), int(round(r * 16)), int(a), th, cv2.LINE_AA, 4)
    def add_to(self, img, col, gain=1.0, glow=0.5, mask=None):
        f = self.l.astype(F32) / 255
        if mask is not None: f = f * mask
        if glow > 0: f = f + glow * cv2.GaussianBlur(f, (0, 0), 3.5)
        img += f[..., None] * (np.array(col, F32) * gain)


FONT = {"L": "/usr/share/fonts/opentype/inter/Inter-Light.otf", "XL": "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
        "T": "/usr/share/fonts/opentype/inter/Inter-Thin.otf", "R": "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
        "M": "/usr/share/fonts/opentype/inter/Inter-Medium.otf"}


@functools.lru_cache(None)
def font(size, wt="L"): return ImageFont.truetype(FONT[wt], size)


def text_w(s, size, track, wt="L"):
    f = font(size, wt); return sum(f.getlength(ch) for ch in s) + track * max(0, len(s) - 1)


class Text:
    """RGBA overlay for all type in a frame; composited once (with a soft dark halo for legibility over imagery)."""
    def __init__(self): self.im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im); self.used = False
    def put(self, xy, s, size, alpha, col=(232, 236, 242), track=None, anchor="l", wt="L"):
        if alpha <= 0.004 or not s: return
        track = size * 0.16 if track is None else track
        f = font(size, wt); w = text_w(s, size, track, wt); x, y = xy
        if anchor == "c": x -= w / 2
        elif anchor == "r": x -= w
        a = int(255 * min(1, alpha)); self.used = True
        for ch in s:
            self.d.text((x, y), ch, font=f, fill=tuple(col) + (a,)); x += f.getlength(ch) + track
    def line(self, p0, p1, alpha, col=(232, 236, 242), width=1):
        if alpha <= 0.004: return
        self.d.line([p0, p1], fill=tuple(col) + (int(255 * min(1, alpha)),), width=width); self.used = True
    def add_to(self, img):
        if not self.used: return img
        a = np.asarray(self.im, F32) / 255; al = a[..., 3]
        sh = cv2.GaussianBlur(al, (0, 0), 7) * 0.55 + cv2.GaussianBlur(al, (0, 0), 22) * 0.35
        img *= (1 - np.clip(sh, 0, 0.6))[..., None]
        return img * (1 - al[..., None]) + a[..., :3] * al[..., None]


def put_sprite(img, spr, cx, cy, scale, angle=0.0, gain=1.0, alpha=1.0, tint=None):
    """spr: float RGBA premultiplied (h,w,4). Scale + rotate about its centre, composite over img."""
    h, w = spr.shape[:2]
    Mx = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale); Mx[0, 2] += cx - w / 2; Mx[1, 2] += cy - h / 2
    inter = cv2.INTER_AREA if scale < 0.6 else cv2.INTER_LINEAR
    if scale < 0.6:
        k = max(1, int(round(1 / scale))) ; s2 = cv2.resize(spr, (max(1, w // k), max(1, h // k)), interpolation=cv2.INTER_AREA)
        Mx = cv2.getRotationMatrix2D((s2.shape[1] / 2, s2.shape[0] / 2), angle, scale * k); Mx[0, 2] += cx - s2.shape[1] / 2; Mx[1, 2] += cy - s2.shape[0] / 2
        spr = s2
    o = cv2.warpAffine(spr, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    rgb = o[..., :3] * gain
    if tint is not None: rgb = rgb * np.array(tint, F32)
    a = o[..., 3:4] * alpha
    img *= (1 - a); img += rgb * alpha
    return o[..., 3] * alpha


N_AST = 540


@functools.lru_cache(maxsize=6)
def ast_frame(i):
    fn = f"{SCR}/spr/ast/f_{i:04d}.png"
    while not os.path.exists(fn) and i > 0:                  # preview fallback while the sequence is still rendering
        i -= 1; fn = f"{SCR}/spr/ast/f_{i:04d}.png"
    a = cv2.imread(fn, cv2.IMREAD_UNCHANGED).astype(F32) / 255
    if os.path.exists(fn + ".i"):                           # flow-interpolated frame: restore the acutance lost in blending
        rgb = a[..., :3]; a[..., :3] = np.clip(rgb + 0.20 * (rgb - cv2.GaussianBlur(rgb, (0, 0), 1.1)), 0, 1)
    a = a[..., [2, 1, 0, 3]]; a[..., :3] *= a[..., 3:4]
    return a


def ast_at(fi):
    """asteroid sprite at an (integer) frame index of the rendered tumble"""
    return ast_frame(int(min(max(round(fi), 0), N_AST - 1)))


def to8(img):
    return (np.clip(img, 0, 1) ** (1 / 1.0) * 255 + np.random.default_rng().uniform(0, 1, img.shape).astype(F32)).clip(0, 255).astype(np.uint8)
