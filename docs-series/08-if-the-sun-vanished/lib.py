"""Shared numpy/cv2 rendering library for 08 'If the Sun vanished right now'.
Everything works in LINEAR light (float32, HDR) and is tone-mapped once at the end (finish()).
 - sky plate: procedural star field (power-law magnitudes, black-body colours) + structured Milky Way
 - analytic sphere renderer with real texture maps: Earth (Blue Marble day, night lights, moving clouds + cloud shadows,
   ocean glint, relief bump, layered limb scattering, terminator colour, frost), Moon (map + crater bump), gas giants, Saturn rings
 - procedural Sun (granulation, limb darkening, spots, corona streamers, prominences)
 - bloom / tone-map / thin Inter typography
"""
import os, sys, math
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/08-if-the-sun-vanished"
sys.path.insert(0, os.path.join(SCR, "pylib"))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
cv2.setNumThreads(2)
VERT = os.environ.get("VERT") == "1"          # 9:16 recomposition (1080x1920)
W, H = (1080, 1920) if VERT else (1920, 1080)
G = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/dl_globe/package/example"
TP = os.path.join(SCR, "dl/px/threex.planets/images")
CACHE = os.path.join(SCR, "cache"); os.makedirs(CACHE, exist_ok=True)
f32 = np.float32


def lin(x): return np.power(np.clip(x, 0, 1), 2.2, dtype=f32) if x.dtype == f32 else np.power(np.clip(x, 0, 1), 2.2).astype(f32)
def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def norm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def ease(t): t = min(max(t, 0.0), 1.0); return t * t * (3 - 2 * t)
def ramp(t, a, b): return ease((t - a) / (b - a))
def kf(t, keys):
    """piecewise smoothstep keyframes [(t, v), ...] (v scalar or tuple)"""
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u


def fbm2(shape, seed, beta=2.0, lo=0.0):
    """spectral noise, periodic, normalised to mean 0 std 1"""
    h, w = shape; r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None] * h; fx = np.fft.rfftfreq(w)[None, :] * w
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    amp = f ** (-beta / 2.0); amp[0, 0] = 0
    if lo: amp[f < lo] = 0
    z = np.fft.irfft2(amp * np.exp(1j * r.uniform(0, 2 * np.pi, amp.shape)), s=(h, w))
    return ((z - z.mean()) / z.std()).astype(f32)


def bbcolor(T):
    """approximate linear RGB of a black body (normalised to max 1)"""
    t = T / 100.0
    r = 255 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    c = np.clip(np.array([r, g, b]) / 255.0, 0, 1) ** 2.2
    return c / c.max()


# ------------------------------------------------------------------------------------------------ sky plate
SKW, SKH = 4096, 2304
def build_sky():
    p = os.path.join(CACHE, "sky.npy")
    if os.path.exists(p): return np.load(p)
    r = np.random.default_rng(42)
    yy, xx = np.mgrid[0:SKH, 0:SKW].astype(f32)
    # Milky Way: a band crossing the plate diagonally
    ang = math.radians(-24); cx0, cy0 = SKW * 0.5, SKH * 0.46
    along = ((xx - cx0) * math.cos(ang) + (yy - cy0) * math.sin(ang)) / SKW
    across = (-(xx - cx0) * math.sin(ang) + (yy - cy0) * math.cos(ang)) / SKH
    n1 = fbm2((SKH, SKW), 1, 2.6); n2 = fbm2((SKH, SKW), 2, 2.0); n3 = fbm2((SKH, SKW), 3, 1.5); n4 = fbm2((SKH, SKW), 4, 2.9)
    warp = across + 0.035 * n4 + 0.012 * n1
    width = 0.105 * (1 + 0.9 * np.exp(-((along - 0.12) / 0.16) ** 2))           # bulge towards the galactic centre
    band = np.exp(-(warp / width) ** 2) * (0.55 + 0.75 * np.exp(-((along - 0.12) / 0.3) ** 2))
    halo = np.exp(-np.abs(warp) / 0.33) * 0.07
    clouds = np.clip(0.7 + 0.42 * n1 + 0.2 * n2, 0.08, 2.2)
    # dust lanes: ridged dark filaments hugging the mid-plane
    dust = np.clip(1.25 - np.abs(n1 * 0.9 + n2 * 0.5 + 0.2) * 1.25, 0, 1) ** 1.6 * np.exp(-((warp + 0.008) / (width * 0.5)) ** 2)
    dust += np.clip(n4 * 0.6 + n2 * 0.5 - 0.35, 0, 1) * np.exp(-(warp / (width * 0.85)) ** 2) * 0.9
    dust = np.clip(dust, 0, 1)
    glow = (band * clouds + halo) * (1 - 0.86 * dust)
    warm = np.exp(-((along - 0.12) / 0.2) ** 2) * np.exp(-(warp / (width * 0.9)) ** 2)
    colc = np.array([0.60, 0.72, 1.0], f32)[None, None] * (1 - warm[..., None]) + np.array([1.0, 0.80, 0.55], f32)[None, None] * warm[..., None]
    sky = glow[..., None] * colc * 0.11
    sky += (np.clip(dust - 0.25, 0, 1) * band)[..., None] * np.array([0.012, 0.006, 0.003], f32) * 1.5   # reddened edges
    # unresolved star clouds: fine grain multiplied into the band
    grain = np.clip(n3 * 0.5 + 0.5, 0, 2) ** 2
    sky *= (0.72 + 0.42 * grain)[..., None]
    sky += np.array([0.0012, 0.0015, 0.0024], f32)                                  # sky floor
    # stars: N(>flux) ~ flux^-1.05 ; density follows the band
    dens = 0.22 + 2.6 * band * (1 - 0.8 * dust) + halo * 3
    nst = 150000
    pdf = dens.ravel().astype(np.float64); pdf /= pdf.sum()
    idx = r.choice(SKW * SKH, nst, p=pdf)
    sy = idx // SKW + r.uniform(0, 1, nst); sx = idx % SKW + r.uniform(0, 1, nst)
    flux = 0.0075 * r.uniform(0, 1, nst) ** (-1 / 1.05); flux = np.minimum(flux, 60)
    temps = np.clip(r.lognormal(np.log(5600), 0.38, nst), 2800, 22000)
    cols = np.stack([bbcolor(T) for T in np.linspace(2800, 22000, 64)])
    sc_ = cols[np.clip(((temps - 2800) / (22000 - 2800) * 63).astype(int), 0, 63)]
    sc_ = 0.45 + 0.55 * sc_                                                          # desaturate (eye/camera)
    acc = np.zeros((SKH + 2, SKW + 2, 3), f32)
    x0 = np.floor(sx).astype(int); y0 = np.floor(sy).astype(int); fx = (sx - x0)[:, None]; fy = (sy - y0)[:, None]
    val = (flux[:, None] * sc_).astype(f32)
    x0 = np.clip(x0, 0, SKW); y0 = np.clip(y0, 0, SKH)
    for dy, dx, wgt in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(acc, (y0 + dy, x0 + dx), val * wgt)
    acc = acc[:SKH, :SKW]
    stars = cv2.GaussianBlur(acc, (0, 0), 0.62) * 2.6
    big = acc * (acc.max(2, keepdims=True) > 2.5)
    stars += cv2.GaussianBlur(big, (0, 0), 1.8) * 2.5 + cv2.GaussianBlur(big, (0, 0), 6.0) * 2.5
    sky = (sky + stars).astype(np.float16)
    np.save(p, sky); return sky

_sky = None
def sky_view(cx, cy, scale=1.0, rot=0.0, w=W, h=H):
    """sample the sky plate: (cx, cy) plate pixel at the frame centre, scale = plate px per frame px, rot degrees"""
    global _sky
    if _sky is None: _sky = build_sky().astype(f32)
    M = cv2.getRotationMatrix2D((0, 0), rot, scale)
    M[0, 2] = cx - (M[0, 0] * w / 2 + M[0, 1] * h / 2); M[1, 2] = cy - (M[1, 0] * w / 2 + M[1, 1] * h / 2)
    return cv2.warpAffine(_sky, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_WRAP)


# ------------------------------------------------------------------------------------------------ textures
_tex = {}
def tex(name):
    if name in _tex: return _tex[name]
    def ld(p, mode="RGB"): return np.asarray(Image.open(p).convert(mode), f32) / 255
    if name == "day": t = lin(ld(G + "/img/earth-blue-marble.jpg"))
    elif name == "night": t = lin(ld(G + "/img/earth-night.jpg"))
    elif name == "water":
        t = cv2.resize(ld(G + "/img/earth-water.png", "L"), (4096, 2048), interpolation=cv2.INTER_CUBIC)
    elif name == "topo":
        t = cv2.resize(ld(G + "/img/earth-topology.png", "L"), (4096, 2048), interpolation=cv2.INTER_CUBIC)
    elif name == "topograd":
        z = cv2.GaussianBlur(tex("topo"), (0, 0), 1.0)
        t = np.stack([np.roll(z, -1, 1) - np.roll(z, 1, 1), np.roll(z, -1, 0) - np.roll(z, 1, 0)], -1)
    elif name == "cloud":
        t = np.asarray(Image.open(G + "/clouds/clouds.png").convert("RGBA"), f32)[..., 3] / 255
    elif name == "freeze":            # order in which the surface whitens (0 = first): land & high latitudes first
        h, w = 1024, 2048
        lat = np.abs(np.linspace(90, -90, h))[:, None] / 90
        wat = cv2.resize(tex("water"), (w, h), interpolation=cv2.INTER_AREA)
        topo = cv2.resize(tex("topo"), (w, h), interpolation=cv2.INTER_AREA)
        n = fbm2((h, w), 77, 2.2)
        t = np.clip(0.62 - 0.42 * lat + 0.30 * wat - 0.35 * topo + 0.10 * n, 0, 1).astype(f32)
    elif name == "icefx":             # frozen-ocean detail: albedo mottling + dark fracture lines (leads)
        a = fbm2((2048, 4096), 81, 1.7); b = fbm2((2048, 4096), 82, 1.5); c = fbm2((2048, 4096), 83, 2.3)
        cr = np.clip(1 - np.abs(b) / 0.05, 0, 1) * np.clip(c * 0.8 + 0.5, 0, 1) + 0.6 * np.clip(1 - np.abs(a + 0.3 * b) / 0.03, 0, 1)
        t = np.stack([np.clip(0.5 + 0.35 * a + 0.25 * c, 0, 1.3), np.clip(cv2.GaussianBlur(cr, (0, 0), 0.7), 0, 1)], -1).astype(f32)
    elif name == "moon": t = lin(ld(TP + "/moonmap1k.jpg", "L"))
    elif name == "moongrad":
        z = ld(TP + "/moonbump1k.jpg", "L"); z = cv2.resize(z, (4000, 2000), interpolation=cv2.INTER_CUBIC)
        r = np.random.default_rng(5); c = np.zeros((2000, 4000), f32)          # extra small craters (procedural) for close framing
        for _ in range(9000):
            x, y = r.integers(0, 4000), r.integers(60, 1940); s = int(r.pareto(2.2) * 2 + 2)
            if s > 26: continue
            yy, xx = np.mgrid[-2 * s:2 * s + 1, -2 * s:2 * s + 1]; d = np.hypot(xx, yy) / s
            prof = np.where(d < 1, (d * d - 1) * 0.6, 0) + 0.35 * np.exp(-((d - 1.05) / 0.22) ** 2)
            ys = slice(max(0, y - 2 * s), min(2000, y + 2 * s + 1)); xs = (np.arange(x - 2 * s, x + 2 * s + 1)) % 4000
            pr = prof[(ys.start - (y - 2 * s)):(ys.stop - (y - 2 * s))]
            c[ys.start:ys.stop, xs] += (pr * s * 0.0022).astype(f32)
        z = z + c + 0.004 * fbm2((2000, 4000), 9, 1.4)
        t = np.stack([np.roll(z, -1, 1) - np.roll(z, 1, 1), np.roll(z, -1, 0) - np.roll(z, 1, 0)], -1)
    elif name == "jupiter": t = lin(ld(TP + "/jupitermap.jpg"))
    elif name == "saturn": t = lin(ld(TP + "/saturnmap.jpg"))
    elif name == "ring":
        c = lin(ld(TP + "/saturnringcolor.jpg")); a = np.asarray(Image.open(TP + "/saturnringpattern.gif").convert("L"), f32) / 255
        t = (c.mean(0) if c.shape[1] > c.shape[0] else c.mean(1), a.mean(0) if a.shape[1] > a.shape[0] else a.mean(1))
    _tex[name] = t; return t


def sample(t, lat, lon, interp=cv2.INTER_LINEAR):
    h, w = t.shape[:2]
    mx = ((lon / (2 * np.pi) + 0.5) % 1.0 * w).astype(f32); my = ((0.5 - lat / np.pi) * (h - 1)).astype(f32)
    return cv2.remap(t, mx, my, interp, borderMode=cv2.BORDER_WRAP)


def rot_y(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rot_x(a): c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def rot_z(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


class Geo:
    """orthographic sphere geometry inside its bounding box (clipped to the frame)"""
    def __init__(s, cx, cy, R, body, pad=0.0, w=W, h=H):
        P = int(R * pad) + 3
        s.x0 = max(0, int(cx - R) - P); s.x1 = min(w, int(cx + R) + P + 1); s.y0 = max(0, int(cy - R) - P); s.y1 = min(h, int(cy + R) + P + 1)
        s.ok = s.x1 > s.x0 and s.y1 > s.y0
        if not s.ok: return
        ys, xs = np.mgrid[s.y0:s.y1, s.x0:s.x1].astype(f32)
        s.u = (xs + 0.5 - cx) / R; s.v = -(ys + 0.5 - cy) / R
        s.rr = s.u * s.u + s.v * s.v; s.r = np.sqrt(s.rr)
        s.z = np.sqrt(np.clip(1 - s.rr, 0, 1))
        s.R = R; s.body = body
        s.alpha = np.clip((1 - s.r) * R + 0.5, 0, 1)
        # limb pixels sample the texture just inside the edge
        k = np.where(s.r > 0.9985, 0.9985 / np.maximum(s.r, 1e-6), 1.0).astype(f32)
        uu, vv = s.u * k, s.v * k; zz = np.sqrt(np.clip(1 - uu * uu - vv * vv, 0, 1))
        B = np.asarray(body, f32)        # view <- body ; body coords = B^T n
        bx = B[0, 0] * uu + B[1, 0] * vv + B[2, 0] * zz
        by = B[0, 1] * uu + B[1, 1] * vv + B[2, 1] * zz
        bz = B[0, 2] * uu + B[1, 2] * vv + B[2, 2] * zz
        s.lat = np.arcsin(np.clip(by, -1, 1)); s.lon = np.arctan2(bx, bz)
        s.n = (uu, vv, zz)
    def dot(s, L): return s.n[0] * f32(L[0]) + s.n[1] * f32(L[1]) + s.n[2] * f32(L[2])
    def tangent_basis(s):
        """east/north unit vectors in view space"""
        B = np.asarray(s.body, f32); cl, sl = np.cos(s.lon), np.sin(s.lon); cla, sla = np.cos(s.lat), np.sin(s.lat)
        eb = (cl, np.zeros_like(cl), -sl); nb = (-sla * sl, cla, -sla * cl)
        E = tuple(B[i, 0] * eb[0] + B[i, 1] * eb[1] + B[i, 2] * eb[2] for i in range(3))
        Nn = tuple(B[i, 0] * nb[0] + B[i, 1] * nb[1] + B[i, 2] * nb[2] for i in range(3))
        return E, Nn


def put(dst, g, rgb, alpha):
    sl = (slice(g.y0, g.y1), slice(g.x0, g.x1)); a = alpha[..., None]
    dst[sl] = dst[sl] * (1 - a) + rgb * a
def addto(dst, g, rgb):
    dst[g.y0:g.y1, g.x0:g.x1] += rgb


RAY = np.array([0.20, 0.42, 1.0], f32)          # Rayleigh-ish scattering colour
def earth(dst, cx, cy, R, lon0, L, sun=1.0, tilt=23.4, tip=12.0, cloud_t=0.0, amb=0.0, frost=0.0, lights=1.0, cloud_amt=1.0,
          atmo=1.0, veg=1.0, expo=1.0, lights_day=0.0, amb_dir=(-0.5, 0.45, 0.74)):
    """Earth, orthographic. lon0: sub-observer longitude (rad). L: unit vector to the Sun in view space.
    sun: sunlight (0 = gone). amb: faint uniform 'starlight' so the dark globe stays readable. frost: 0..1 surface freeze.
    lights_day: 0..1 city lights switched on across the (former) day side too."""
    body = rot_z(math.radians(-tilt)) @ rot_x(math.radians(tip)) @ rot_y(-lon0)
    g = Geo(cx, cy, R, body, pad=0.10)
    if not g.ok: return
    L = norm(L); ndl = g.dot(L)
    day = sample(tex("day"), g.lat, g.lon, cv2.INTER_CUBIC if R > 500 else cv2.INTER_LINEAR)
    wat = sample(tex("water"), g.lat, g.lon)
    # relief bump from topology
    gr = sample(tex("topograd"), g.lat, g.lon)
    E, Nn = g.tangent_basis(); kb = 26.0
    ndl_b = ndl - kb * (gr[..., 0] * (E[0] * L[0] + E[1] * L[1] + E[2] * L[2]) - gr[..., 1] * (Nn[0] * L[0] + Nn[1] * L[1] + Nn[2] * L[2]))
    if veg < 1:                                   # vegetation dying: green land drifts to dry brown
        gness = np.clip((day[..., 1] - 0.5 * (day[..., 0] + day[..., 2])) * 14, 0, 1)[..., None] * (1 - veg)
        dead = day.mean(2, keepdims=True) * np.array([1.25, 1.0, 0.62], f32)
        day = day * (1 - gness) + dead * gness
    # clouds: layer drifts relative to the ground; differential drift by latitude
    cl_lon = g.lon - cloud_t * (0.6 + 0.4 * np.cos(g.lat * 2))
    cl = sample(tex("cloud"), g.lat, cl_lon) * cloud_amt
    # cloud shadows: sample the cloud deck displaced towards the Sun (parallax of a thin layer above the ground)
    le = E[0] * L[0] + E[1] * L[1] + E[2] * L[2]; ln = Nn[0] * L[0] + Nn[1] * L[1] + Nn[2] * L[2]
    sh_k = 0.006 / np.maximum(ndl, 0.12)
    cls = sample(tex("cloud"), g.lat + ln * sh_k, cl_lon + le * sh_k / np.maximum(np.cos(g.lat), 0.2)) * cloud_amt
    shadow = 1 - 0.55 * cls * (1 - cl)
    # frost / ice
    if frost > 0:
        fo = sample(tex("freeze"), g.lat, g.lon)
        ice = smooth(fo - 0.06, fo + 0.06, f32(frost * 1.15))
        tone = sample(tex("topo"), g.lat, g.lon)
        fxv = sample(tex("icefx"), g.lat, g.lon)
        icec = (np.array([0.60, 0.69, 0.80], f32) + 0.30 * tone[..., None]) * (0.62 + 0.5 * day.mean(2, keepdims=True) ** 0.3) * (0.72 + 0.5 * fxv[..., 0:1])
        icec = icec * (1 - 0.55 * fxv[..., 1:2]) + np.array([0.10, 0.22, 0.36], f32) * 0.55 * fxv[..., 1:2]
        day = day * (1 - ice[..., None]) + icec * ice[..., None]
        wat = wat * (1 - ice)
    # sunlight colour after its path through the air (warm near the terminator)
    mu = np.clip(ndl, 0, 1)
    path = 1.0 / (mu + 0.06)
    trans = np.exp(-np.multiply.outer(path, np.array([0.035, 0.085, 0.20], f32) * atmo))
    wrap = smooth(-0.10, 0.16, ndl)
    lam = np.clip(ndl_b, 0, 1) * wrap
    surf = day * (lam * shadow)[..., None] * trans * 1.25
    # ocean glint + broad sheen
    Hh = norm(L + np.array([0, 0, 1.0])); ndh = np.clip(g.dot(Hh), 0, 1)
    surf += (wat * (ndh ** 300 * 1.1 + ndh ** 36 * 0.07) * wrap * (1 - cl) * shadow)[..., None] * np.array([1.0, 0.93, 0.80], f32) * trans
    # clouds lit by the same reddened light, self-shaded a little by density
    clc = (cl ** 0.75 * (np.clip(ndl, 0, 1) * 0.92 + 0.08) * wrap)[..., None] * trans * 1.05
    surf = surf * (1 - cl[..., None] * 0.92) + clc
    # atmosphere over the disc: Rayleigh haze growing to the limb, lit by the Sun
    zz = np.maximum(g.z, 0.02); air = (1 - np.exp(-0.10 * atmo / zz))
    surf = surf * (1 - 0.55 * air[..., None] * RAY) + (air * smooth(-0.18, 0.25, ndl) * 0.62)[..., None] * RAY * np.exp(-np.multiply.outer(1 / (mu + 0.12), np.array([0.01, 0.03, 0.09], f32)))
    surf *= sun
    # night side: city lights (+ a little cloud glow), starlight ambient
    if lights > 0:
        nl = sample(tex("night"), g.lat, g.lon, cv2.INTER_CUBIC if R > 500 else cv2.INTER_LINEAR)
        dark = 1 - smooth(-0.12, 0.10, ndl) * min(1.0, sun * 1.0) * (1 - lights_day)
        lum = np.clip(nl[..., 0] - 0.012, 0, 1)
        surf += (lum * dark * (1 - 0.75 * cl) * 3.2 * lights)[..., None] * np.array([1.0, 0.62, 0.26], f32)
    if amb > 0:
        base = day * 0.8 + 0.02 + (cl * 0.5)[..., None]
        La = norm(amb_dir); nda = g.dot(La) - kb * 1.6 * (gr[..., 0] * (E[0] * La[0] + E[1] * La[1] + E[2] * La[2]) - gr[..., 1] * (Nn[0] * La[0] + Nn[1] * La[1] + Nn[2] * La[2]))
        surf += base * amb * np.array([0.55, 0.70, 1.0], f32) * (0.22 + 1.05 * np.clip(nda, 0, 1) ** 0.8 * smooth(-0.1, 0.25, g.dot(La)))[..., None]
    put(dst, g, surf * expo, g.alpha)
    # limb glow outside (and just inside) the disc: two layers
    if atmo > 0 and sun > 0:
        hgt = (g.r - 1) * R
        sc1, sc2 = max(1.6, R * 0.007), max(5.0, R * 0.03)
        lim = (g.u * L[0] + g.v * L[1]) / np.maximum(g.r, 1e-3)              # sun-facing-ness of this limb point
        lz = lim * np.sqrt(max(1e-6, 1 - L[2] ** 2)) / max(1e-6, math.hypot(L[0], L[1])) if abs(L[2]) < 0.999 else lim
        illum = smooth(-0.35, 0.35, lim * math.hypot(L[0], L[1]) + 0.0) if abs(L[2]) < 0.999 else 1.0
        back = 1 + 3.0 * max(0.0, -L[2]) ** 2                                 # forward scattering when the Sun is behind
        outer = np.where(hgt > 0, np.exp(-hgt / sc1) * 1.0 + np.exp(-hgt / sc2) * 0.16, 0)
        glow = (outer * illum * atmo * sun * back * 0.9)[..., None] * RAY
        twil = np.exp(-((lim * math.hypot(L[0], L[1])) / 0.16) ** 2) if abs(L[2]) < 0.999 else 0.0
        glow += (outer * twil * atmo * sun * 0.35)[..., None] * np.array([1.0, 0.42, 0.12], f32)
        addto(dst, g, glow * expo)
    return g


def moon(dst, cx, cy, R, L, sun=1.0, lon0=0.0, amb=0.0, earthshine=0.0):
    g = Geo(cx, cy, R, rot_z(math.radians(8)) @ rot_y(-lon0))
    if not g.ok: return
    L = norm(L); alb = sample(tex("moon"), g.lat, g.lon, cv2.INTER_CUBIC)
    gr = sample(tex("moongrad"), g.lat, g.lon, cv2.INTER_CUBIC)
    E, Nn = g.tangent_basis(); kb = 6.0
    ndl = g.dot(L) - kb * (gr[..., 0] * (E[0] * L[0] + E[1] * L[1] + E[2] * L[2]) - gr[..., 1] * (Nn[0] * L[0] + Nn[1] * L[1] + Nn[2] * L[2]))
    mu0 = np.clip(ndl, 0, 1); mu = np.maximum(g.z, 0.02)
    ls = 2 * mu0 / (mu0 + mu) * smooth(-0.02, 0.04, g.dot(L))                 # Lommel-Seeliger: flat, limb-bright full Moon
    c = (alb * 1.9 + 0.02)[..., None] * np.array([1.0, 0.97, 0.92], f32)
    out = c * (ls * sun * 0.5)[..., None] + c * (amb + earthshine) * np.array([0.55, 0.7, 1.0], f32)
    put(dst, g, out, g.alpha); return g


def gas_giant(dst, name, cx, cy, R, L, sun=1.0, lon0=0.0, tilt=3.0, tip=3.0, oblate=1.0, amb=0.0, ring=False, ring_sun=None):
    """Jupiter / Saturn with texture + fine procedural band turbulence, Minnaert limb darkening; optional rings with shadow"""
    body = rot_z(math.radians(tilt)) @ rot_x(math.radians(tip)) @ rot_y(-lon0)
    L = norm(L); ring_sun = sun if ring_sun is None else ring_sun
    Rr = [1.24, 2.27]                                                        # Saturn ring inner/outer radius (planet radii)
    pole = body @ np.array([0, 1.0, 0])
    def rings(front):
        x0 = max(0, int(cx - R * 2.4)); x1 = min(W, int(cx + R * 2.4)); y0 = max(0, int(cy - R * 2.4)); y1 = min(H, int(cy + R * 2.4))
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(f32); u = (xs + .5 - cx) / R; v = -(ys + .5 - cy) / R
        # ray (u, v, z) hits the ring plane where p . pole = 0  ->  z = -(u px + v py) / pz
        zp = -(u * pole[0] + v * pole[1]) / pole[2]
        rad = np.sqrt(u * u + v * v + zp * zp)
        colr, alr = tex("ring"); k = np.clip((rad - Rr[0]) / (Rr[1] - Rr[0]), 0, 1)
        ii = k * (len(alr) - 1); a = np.interp(ii, np.arange(len(alr)), alr).astype(f32) * ((rad > Rr[0]) & (rad < Rr[1]))
        jj = k * (colr.shape[0] - 1); c = np.stack([np.interp(jj, np.arange(colr.shape[0]), colr[:, i]) for i in range(3)], -1).astype(f32)
        fine = 0.8 + 0.2 * np.sin(rad * 240) * np.sin(rad * 91 + 1.3)
        a = np.clip(a * 1.15, 0, 1) * fine
        # planet shadow on the rings: point p is shadowed if the ray p + s L hits the sphere
        pL = u * L[0] + v * L[1] + zp * L[2]; d2 = rad * rad - pL * pL
        shad = 1 - smooth(1.02, 0.96, np.sqrt(np.maximum(d2, 0))) * (pL < 0)
        infront = zp > 0
        hidden = (~infront) & ((u * u + (v / oblate) ** 2) < 1)
        sel = (infront if front else ~infront) & ~hidden
        lit = c * (a * shad * ring_sun * 1.5 * abs(float(pole @ L)) ** 0.5 + a * amb)[..., None]
        sl = (slice(y0, y1), slice(x0, x1)); al = (a * sel)[..., None] * 0.92
        dst[sl] = dst[sl] * (1 - al) + lit * sel[..., None]
    if ring: rings(False)
    g = Geo(cx, cy / 1.0, R, body)
    if not g.ok: return
    if oblate != 1.0:                                                         # squash vertically (screen-space, fine for small tilt)
        g = Geo(cx, cy, R, body); g.v = g.v / oblate
        g.rr = g.u * g.u + g.v * g.v; g.r = np.sqrt(g.rr); g.z = np.sqrt(np.clip(1 - g.rr, 0, 1)); g.alpha = np.clip((1 - g.r) * R * oblate + 0.5, 0, 1)
        k = np.where(g.r > 0.998, 0.998 / np.maximum(g.r, 1e-6), 1.0).astype(f32); uu, vv = g.u * k, g.v * k; zz = np.sqrt(np.clip(1 - uu * uu - vv * vv, 0, 1))
        B = np.asarray(body, f32)
        bx = B[0, 0] * uu + B[1, 0] * vv + B[2, 0] * zz; by = B[0, 1] * uu + B[1, 1] * vv + B[2, 1] * zz; bz = B[0, 2] * uu + B[1, 2] * vv + B[2, 2] * zz
        g.lat = np.arcsin(np.clip(by, -1, 1)); g.lon = np.arctan2(bx, bz); g.n = (uu, vv, zz)
    t = tex(name)
    # fine turbulence: warp the lookup with band-aligned noise so the 1k map does not look soft
    key = "turb_" + name
    if key not in _tex:
        n = fbm2((1024, 2048), 31, 1.9); n = cv2.GaussianBlur(n, (0, 0), sigmaX=6, sigmaY=0.8); _tex[key] = (n / n.std()).astype(f32)
        d = fbm2((1024, 2048), 32, 1.2); d = cv2.GaussianBlur(d, (0, 0), sigmaX=3.5, sigmaY=0.6); _tex[key + "d"] = (d / d.std()).astype(f32)
    tb = sample(_tex[key], g.lat, g.lon); td = sample(_tex[key + "d"], g.lat, g.lon)
    alb = sample(t, g.lat + tb * 0.004, g.lon + tb * 0.02, cv2.INTER_CUBIC) * (1 + 0.07 * td)[..., None]
    ndl = g.dot(L); mu0 = np.clip(ndl, 0, 1); mu = np.maximum(g.z, 0.0)
    minn = (mu0 ** 0.95) * (mu ** 0.35) * smooth(-0.02, 0.10, ndl)
    limbc = np.exp(-np.multiply.outer(1 / (mu + 0.25) - 0.8, np.array([0.02, 0.06, 0.12], f32)))
    out = alb * minn[..., None] * limbc * sun * 1.5
    if ring:                                                                  # ring shadow on the globe
        E_ = None
        # point n on the sphere is shadowed by the ring if n + s L crosses the ring plane within the ring radii
        nx, ny, nz_ = g.n; npole = nx * pole[0] + ny * pole[1] + nz_ * pole[2]; lp = float(pole @ L)
        s_ = -npole / (lp if abs(lp) > 1e-4 else 1e-4)
        px, py, pz = nx + s_ * L[0], ny + s_ * L[1], nz_ + s_ * L[2]; rad = np.sqrt(px * px + py * py + pz * pz)
        colr, alr = tex("ring"); k = np.clip((rad - Rr[0]) / (Rr[1] - Rr[0]), 0, 1)
        a = np.interp(k * (len(alr) - 1), np.arange(len(alr)), alr).astype(f32) * ((rad > Rr[0]) & (rad < Rr[1]) & (s_ > 0))
        out *= (1 - 0.8 * a)[..., None]
    out += alb * amb * np.array([0.6, 0.72, 1.0], f32) * (0.3 + 0.7 * mu[..., None])
    put(dst, g, out, g.alpha)
    if ring: rings(True)
    return g


# ------------------------------------------------------------------------------------------------ Sun
_sun = {}
def sun_disc(dst, cx, cy, R, t, power=1.0, corona=1.0):
    """Photosphere with drifting granulation, limb darkening, faculae, spots; chromosphere rim, prominences, structured corona.
    Values are strongly HDR (the bloom/tonemap turn it into a glaring star)."""
    if not _sun:
        _sun["g1"] = fbm2((1024, 2048), 11, 0.6, lo=40); _sun["g2"] = fbm2((1024, 2048), 12, 1.6, lo=6)
        _sun["g3"] = fbm2((1024, 2048), 13, 2.4); sp = lin(np.asarray(Image.open(TP + "/sunmap.jpg").convert("L"), f32)[..., None] / 255)[..., 0]
        _sun["spots"] = cv2.resize(sp, (2048, 1024), interpolation=cv2.INTER_CUBIC)
        _sun["ray"] = fbm2((512, 2048), 14, 2.7)        # corona: angle (x) vs radius (y)
        _sun["ray2"] = fbm2((64, 4096), 15, 2.2)
    pad = 2.6 if corona > 0 else 0.1
    g = Geo(cx, cy, R, rot_z(math.radians(7)) @ rot_x(math.radians(5)) @ rot_y(-0.012 * t), pad=pad)
    if not g.ok: return
    mu = g.z
    gran = sample(_sun["g1"], g.lat, g.lon + 0.0006 * t) * 0.5 + sample(_sun["g1"], g.lat + 0.3, g.lon * 1.0 - 0.0009 * t + 1.0) * 0.5
    meso = sample(_sun["g2"], g.lat, g.lon + 0.002 * t); big = sample(_sun["g3"], g.lat, g.lon)
    spots = sample(_sun["spots"], g.lat, g.lon, cv2.INTER_CUBIC)
    inten = 1 + 0.22 * gran * (0.4 + 0.6 * mu) + 0.10 * meso + 0.07 * big
    fac = np.clip(meso * 0.6 + big * 0.5 - 0.55, 0, 1) * (1 - mu) * 1.6            # faculae brighten near the limb
    inten = inten * (0.25 + 0.75 * np.clip(spots / 0.72, 0, 1) ** 1.6) + fac
    ld = np.stack([1 - c * (1 - mu) - 0.18 * (1 - mu) ** 2 for c in (0.42, 0.62, 0.80)], -1)      # wavelength-dependent limb darkening
    col = np.array([1.0, 0.60, 0.22], f32)
    disc = (inten[..., None] ** 1.5 * ld * col * 1.55 * power).astype(f32)
    # outside the limb
    ang = np.arctan2(g.v, g.u); h = np.maximum(g.r - 1, 0)
    if corona > 0:
        ax = ((ang / (2 * np.pi) + 0.5) * 2048).astype(f32)
        ry = np.clip(h / 2.6, 0, 1) * 511
        st1 = cv2.remap(_sun["ray"], ax, (ry * 0.25 + 3 * math.sin(t * 0.05)).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        st2 = cv2.remap(_sun["ray2"], ax * 2, (ry * 0.02 + 8).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        stream = np.clip(0.8 + 0.6 * st1 + 0.3 * st2, 0.05, 3) ** 1.6
        fall = 0.9 * np.exp(-h / 0.045) + 0.16 / (1 + (h / 0.13) ** 2.4) + 0.012 / (1 + (h / 0.7) ** 2.0)
        cor = (fall * (0.35 + 0.65 * stream * np.clip(h / 0.08, 0, 1)) * (g.r >= 1))[..., None] * np.array([1.0, 0.74, 0.46], f32) * 1.1 * corona * power
        # chromosphere + a few prominences (arched, clumpy)
        prom = np.zeros_like(h)
        for a0, hh, ww, sd in ((0.62, 0.075, 0.06, 1), (2.45, 0.11, 0.045, 2), (-1.9, 0.05, 0.09, 3), (-0.55, 0.035, 0.05, 4), (3.9 - 2 * np.pi, 0.06, 0.035, 5)):
            da = (ang - a0 + np.pi) % (2 * np.pi) - np.pi
            arch = np.exp(-((h - hh * (1 - (da / ww) ** 2).clip(0, 1) ** 0.5 * (0.9 + 0.1 * math.sin(t * 0.3 + sd))) / (0.012 + 0.2 * hh)) ** 2) * (np.abs(da) < ww * 1.05)
            prom += arch * (0.55 + 0.45 * np.clip(st1 * 0.8 + 0.5, 0, 1.4))
        chrom = np.exp(-h / 0.008) * (g.r >= 1)
        cor += ((prom * 0.9 + chrom * 1.6) * (g.r >= 1))[..., None] * np.array([1.0, 0.20, 0.08], f32) * 1.6 * power
        addto(dst, g, cor.astype(f32))
    put(dst, g, disc, g.alpha)
    return g


# ------------------------------------------------------------------------------------------------ finishing
def bloom(img, amt=1.0, thr=0.0):
    """multi-scale glow of the HDR frame (energy-conserving-ish)"""
    src = np.maximum(img - thr, 0) if thr else img
    small = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(small)
    for s, wg in ((1.6, 0.30), (5, 0.24), (16, 0.20), (48, 0.16)):
        acc += cv2.GaussianBlur(small, (0, 0), s) * wg
    return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * amt * 0.5


def anamorphic(img, thr=2.0, amt=0.05):
    """subtle horizontal lens streak from very bright sources"""
    s = cv2.resize(np.maximum(img - thr, 0), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    s = cv2.blur(cv2.blur(s, (181, 1)), (121, 1)); s = cv2.GaussianBlur(s, (0, 0), sigmaX=1, sigmaY=1.2)
    return img + cv2.resize(s, (W, H)) * amt * np.array([0.55, 0.75, 1.0], f32)


def tonemap(img, expo=1.0):
    """filmic shoulder, per channel with slight desaturation of highlights; returns sRGB float 0..1"""
    x = np.maximum(img * expo, 0)
    lum = x @ np.array([0.2126, 0.7152, 0.0722], f32)
    k = np.clip((lum - 0.8) / 6.0, 0, 0.75)[..., None]
    x = x * (1 - k) + lum[..., None] * k
    y = 1 - np.exp(-x * 1.15)
    y = y * (1 + 0.12 * y * (1 - y) * 4 * 0.0)
    return np.power(y, 1 / 2.2, dtype=f32)


_fonts = {}
def font(sz, wt="Light", display=False):
    k = (sz, wt, display)
    if k not in _fonts:
        fam = "InterDisplay" if display else "Inter"
        _fonts[k] = ImageFont.truetype(f"/usr/share/fonts/opentype/inter/{fam}-{wt}.otf", sz)
    return _fonts[k]


def text_w(s, f, track=0.0):
    return sum(f.getlength(ch) for ch in s) + track * f.size * max(0, len(s) - 1)


class _Overlay:
    """text / thin-line overlay drawn with PIL at 2x and composited (sRGB space) with per-item alpha"""
    def __init__(s, h=None, yoff=0):
        s.h = H if h is None else h; s.yoff = yoff
        s.im = Image.new("RGBA", (W * 2, s.h * 2), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.im); s.used = False
    def text(s, x, y, txt, size=30, wt="Light", col=(235, 240, 248), a=1.0, track=0.22, anchor="l", display=False, shadow=True):
        if a <= 0.003 or not txt: return 0
        s.used = True
        f = font(int(size * 2), wt, display); tw = text_w(txt, f, track)
        x0 = x * 2 - (tw / 2 if anchor == "m" else tw if anchor == "r" else 0); y0 = (y - s.yoff) * 2
        if shadow:
            sh = Image.new("RGBA", s.im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh); xx = x0
            for ch in txt:
                ds.text((xx, y0), ch, font=f, fill=(0, 0, 0, int(215 * a))); xx += f.getlength(ch) + track * f.size
            bb = (max(0, int(x0 - 40)), max(0, int(y0 - 40)), min(W * 2, int(x0 + tw + 40)), min(s.h * 2, int(y0 + f.size * 1.4 + 40)))
            if bb[2] > bb[0] and bb[3] > bb[1]:
                from PIL import ImageFilter
                reg = sh.crop(bb).filter(ImageFilter.GaussianBlur(9)); s.im.alpha_composite(reg, (bb[0], bb[1]))
        lay = Image.new("RGBA", (int(tw + 8), int(f.size * 1.5)), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay); xx = 2
        for ch in txt:
            dl.text((xx, 0), ch, font=f, fill=(*col, int(255 * min(1, a)))); xx += f.getlength(ch) + track * f.size
        s.im.alpha_composite(lay, (max(0, int(x0 - 2)), max(0, int(y0))))
        return tw / 2
    def line(s, pts, col=(235, 240, 248), a=1.0, width=1.5, dash=None):
        if a <= 0.003: return
        s.used = True; c = (*col, int(255 * min(1, a))); w = max(1, int(round(width * 2)))
        pts = [(p[0] * 2, p[1] * 2) for p in pts]
        if dash is None: s.d.line(pts, fill=c, width=w, joint="curve"); return
        on, off = dash; acc = 0.0; draw = True; seg = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            L = math.hypot(q[0] - p[0], q[1] - p[1]); pos = 0.0
            while pos < L:
                lim = (on if draw else off) * 2 - acc; step = min(lim, L - pos); pos += step; acc += step
                pt = (p[0] + (q[0] - p[0]) * pos / L, p[1] + (q[1] - p[1]) * pos / L)
                if draw: seg.append(pt)
                if acc >= (on if draw else off) * 2 - 1e-6:
                    if draw and len(seg) > 1: s.d.line(seg, fill=c, width=w)
                    draw = not draw; acc = 0.0; seg = [pt]
        if draw and len(seg) > 1: s.d.line(seg, fill=c, width=w)
    def circle(s, x, y, r, col=(235, 240, 248), a=1.0, width=1.5, fill=None):
        if a <= 0.003: return
        s.used = True
        s.d.ellipse((2 * (x - r), 2 * (y - r), 2 * (x + r), 2 * (y + r)), outline=(*col, int(255 * a)), width=max(1, int(width * 2)), fill=fill)
    def apply(s, srgb):
        if not s.used: return srgb
        o = np.asarray(s.im.resize((W, H), Image.LANCZOS), f32) / 255
        a = o[..., 3:4]
        return srgb * (1 - a) + o[..., :3] * a



class Overlay:
    """records draw calls; identical consecutive frames reuse the rendered layer (text is static most of the time)"""
    _key = None; _lay = None
    def __init__(s): s.ops = []; s.dyn = []          # dyn: fast-changing text (the clock), drawn in its own small strip
    def text(s, x, y, txt, size=30, wt="Light", col=(235, 240, 248), a=1.0, track=0.22, anchor="l", display=False, shadow=True, dyn=False):
        if a <= 0.003 or not txt: return 0
        (s.dyn if dyn else s.ops).append(("text", round(x, 1), round(y, 1), txt, size, wt, tuple(col), round(a, 3), track, anchor, display, shadow)); return 0
    def line(s, pts, col=(235, 240, 248), a=1.0, width=1.5, dash=None):
        if a > 0.003: s.ops.append(("line", tuple((round(p[0], 1), round(p[1], 1)) for p in pts), tuple(col), round(a, 3), width, dash))
    def circle(s, x, y, r, col=(235, 240, 248), a=1.0, width=1.5, fill=None):
        if a > 0.003: s.ops.append(("circle", round(x, 1), round(y, 1), r, tuple(col), round(a, 3), width, fill))
    _dkey = None; _dlay = None
    def apply(s, srgb):
        if s.ops:
            key = tuple(s.ops)
            if key != Overlay._key:
                o = _Overlay()
                for op in s.ops:
                    if op[0] == "text": o.text(*op[1:])
                    elif op[0] == "line": o.line(list(op[1]), *op[2:])
                    else: o.circle(*op[1:])
                Overlay._lay = np.asarray(o.im.resize((W, H), Image.LANCZOS), f32) / 255; Overlay._key = key
            o = Overlay._lay; a = o[..., 3:4]
            srgb = srgb * (1 - a) + o[..., :3] * a
        if s.dyn:
            y0 = max(0, int(min(op[2] for op in s.dyn)) - 30); hh = min(H - y0, 150); key = tuple(s.dyn)
            if key != Overlay._dkey:
                o = _Overlay(h=hh, yoff=y0)
                for op in s.dyn: o.text(*op[1:])
                Overlay._dlay = np.asarray(o.im.resize((W, hh), Image.LANCZOS), f32) / 255; Overlay._dkey = key
            o = Overlay._dlay; a = o[..., 3:4]
            srgb[y0:y0 + hh] = srgb[y0:y0 + hh] * (1 - a) + o[..., :3] * a
        return srgb

def clock_str(sec):
    sec = int(sec); return f"{sec // 3600:02d}:{sec // 60 % 60:02d}:{sec % 60:02d}"
