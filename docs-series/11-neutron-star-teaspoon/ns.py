"""Renderers specific to "ONE TEASPOON OF A NEUTRON STAR" (numpy + OpenCV), on top of lib.py.

  * neutron star: procedural crust map (fracture network, granulation, hot polar caps), drawn as a sphere whose surface
    mapping includes gravitational light bending (Beloborodov 2002 approximation: 1 - cos(alpha) = (1 - cos(psi)) (1 - rs/R)),
    so more than half of the surface is visible; weak-field lensing of the background sky (deflection 2 rs / b);
    dipole field lines; hollow-cone pulsar beams integrated along the line of sight,
  * supergiant star, layered filament "explosion" renderer (supernova, teaspoon blast, kilonova),
  * cut-away sphere (Earth interior, neutron-star interior),
  * the New York relief map from real elevation tiles, drawn in perspective.
"""
import os, sys, math, functools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import *
from lib import _grid

U_NS = 0.345            # rs / R for 1.4 solar masses and R = 12 km  (rs = 4.13 km)


# ------------------------------------------------------------------------------------------------ noise
def fbm2(n, beta, seed, lo=1.0, hi=None):
    """periodic 2D noise with power spectrum k^-beta, zero mean, unit std (FFT synthesis)"""
    r = np.random.default_rng(seed)
    kx = np.fft.fftfreq(n)[None, :] * n; ky = np.fft.fftfreq(n)[:, None] * n; k = np.sqrt(kx * kx + ky * ky); k[0, 0] = 1
    amp = k ** (-beta / 2.0); amp[k < lo] = 0
    if hi: amp *= np.exp(-(k / hi) ** 2)
    f = np.fft.ifft2(amp * np.exp(2j * np.pi * r.uniform(0, 1, (n, n)))).real
    return ((f - f.mean()) / f.std()).astype(F32)


def sphere_fbm(dirs, scale, octs, seed, H=0.75, nw=14, ridged=False):
    """fractal noise continuous on the sphere (sum of random plane waves in 3D)"""
    r = np.random.default_rng(seed); out = np.zeros(dirs.shape[:-1], F32); amp = 1.0; f = scale; tot = 0
    for o in range(octs):
        acc = np.zeros(dirs.shape[:-1], F32)
        for _ in range(nw):
            k = r.standard_normal(3); k = (k / np.linalg.norm(k) * f * r.uniform(0.75, 1.3)).astype(F32)
            acc += np.cos(dirs[..., 0] * k[0] + dirs[..., 1] * k[1] + dirs[..., 2] * k[2] + F32(r.uniform(0, 6.28)))
        acc /= math.sqrt(nw / 2)
        out += amp * ((1 - np.abs(acc) / 1.2) if ridged else acc); tot += amp; amp *= 2 ** (-H); f *= 2.03
    return out / tot


def _eqdirs(Wm, Hm):
    lon = ((np.arange(Wm, dtype=F32) + 0.5) / Wm - 0.5) * 2 * np.pi; lat = (0.5 - (np.arange(Hm, dtype=F32) + 0.5) / Hm) * np.pi
    LON, LAT = np.meshgrid(lon, lat)
    return np.stack([np.cos(LAT) * np.cos(LON), np.cos(LAT) * np.sin(LON), np.sin(LAT)], -1), LAT, LON


def voronoi(dirs, n, seed):
    """cellular noise on the sphere: (F1, F2 - F1, cell id), distances in units of the mean cell spacing"""
    from scipy.spatial import cKDTree
    r = np.random.default_rng(seed); p = r.standard_normal((n, 3)); p /= np.linalg.norm(p, axis=1, keepdims=True)
    dd, ii = cKDTree(p).query(dirs.reshape(-1, 3), k=2, workers=2)
    sp = math.sqrt(4 * math.pi / n)
    return (dd[:, 0] / sp).reshape(dirs.shape[:-1]).astype(F32), ((dd[:, 1] - dd[:, 0]) / sp).reshape(dirs.shape[:-1]).astype(F32), ii[:, 0].reshape(dirs.shape[:-1])


@functools.lru_cache(None)
def ns_tex(kind="ns"):
    """equirect RGB emission map in the star's magnetic frame (z = magnetic axis)"""
    fn = f"{TEX}/tex_{kind}8.npy"
    if os.path.exists(fn): return np.load(fn)
    Wm, Hm = (5120, 2560) if kind == "ns" else (3072, 1536)
    d, LAT, LON = _eqdirs(Wm, Hm)
    if kind in ("ns", "mag"):
        # incandescent crust: plates (cellular noise at three scales) with hair-line fractures, fine granulation, hot polar caps
        warp = np.stack([sphere_fbm(d, 5.0, 5, 11 + i, nw=20, H=0.6) for i in range(3)], -1) * 0.11
        dw = d + warp; dw /= np.linalg.norm(dw, axis=-1, keepdims=True)
        warp2 = np.stack([sphere_fbm(d, 30.0, 3, 31 + i, nw=20) for i in range(3)], -1) * 0.008
        dw2 = dw + warp2; dw2 /= np.linalg.norm(dw2, axis=-1, keepdims=True)
        rr_ = np.random.default_rng(5)
        f1a, ea, ia = voronoi(dw, 520, 1); f1b, eb, ib = voronoi(dw2, 5200, 2); f1c, ec, ic = voronoi(dw2, 60000, 3)
        ta = rr_.uniform(-1, 1, 520)[ia]; tb = rr_.uniform(-1, 1, 5200)[ib]; tc = rr_.uniform(-1, 1, 60000)[ic]
        big = sphere_fbm(dw, 2.0, 4, 1, nw=24); gran = sphere_fbm(d, 420.0, 2, 4, H=0.5, nw=60)
        crA = np.exp(-(ea / 0.035) ** 2); crB = np.exp(-(eb / 0.055) ** 2); crC = np.exp(-(ec / 0.10) ** 2)
        seamA = np.exp(-(ea / 0.16) ** 2)                                  # heat glowing along the big plate boundaries
        colat = np.pi / 2 - np.abs(LAT)
        cap = np.exp(-(colat / 0.22) ** 2); ring = np.exp(-((colat - 0.40) / 0.08) ** 2)
        strie = (0.5 + 0.5 * np.cos(LON * 60 + 6 * big)) * np.exp(-(colat / 0.8) ** 2)
        T = 0.70 + 0.12 * big + 0.04 * ta + 0.06 * tb + 0.05 * tc + 0.035 * gran - 0.08 * np.clip(f1b - 0.25, 0, 1) \
            + 0.09 * seamA + 0.26 * crA + 0.26 * crB * (0.5 + 0.5 * seamA + 0.3 * (tb > 0.3)) + 0.12 * crC \
            + 1.0 * cap + 0.14 * ring * (0.5 + 0.5 * strie) + 0.07 * strie
        T = np.clip(T, 0.05, 3)
        if kind == "ns":
            c0, c1, c2 = np.array([0.10, 0.30, 0.95], F32), np.array([0.50, 0.76, 1.0], F32), np.array([1.0, 1.0, 1.0], F32)
        else:
            c0, c1, c2 = np.array([0.40, 0.14, 0.90], F32), np.array([0.78, 0.58, 1.0], F32), np.array([1.0, 0.97, 1.0], F32)
        t1 = np.clip((T - 0.35) / 0.55, 0, 1)[..., None]; t2 = np.clip((T - 0.90) / 0.55, 0, 1)[..., None]
        rgb = (c0 + (c1 - c0) * t1) * (1 - t2) + c2 * t2
        rgb = rgb * (0.10 + 1.02 * T[..., None])
    else:                                                                # red supergiant: a few enormous convection cells
        warp = np.stack([sphere_fbm(d, 2.5, 6, 21 + i, nw=24, H=0.55) for i in range(3)], -1) * 0.30
        dw = d + warp; dw /= np.linalg.norm(dw, axis=-1, keepdims=True)
        f1, e1, i1 = voronoi(dw, 34, 7); f2, e2, i2 = voronoi(dw, 420, 8)
        rr_ = np.random.default_rng(9); t1c = rr_.uniform(-1, 1, 34)[i1]
        soft = sphere_fbm(dw, 3.0, 5, 5, H=0.9, nw=30); gran = sphere_fbm(d, 60.0, 4, 7, H=0.6, nw=40)
        lanes = np.exp(-(e1 / 0.30)); lanes2 = np.exp(-(e2 / 0.22))
        T = np.clip(0.92 + 0.16 * t1c + 0.30 * soft - 0.42 * lanes - 0.10 * lanes2 * (1 - lanes) + 0.25 * np.clip(0.45 - f1, 0, 1) + 0.07 * gran, 0.2, 2)
        c0, c1, c2 = np.array([0.70, 0.10, 0.015], F32), np.array([1.0, 0.48, 0.11], F32), np.array([1.0, 0.93, 0.68], F32)
        t1 = np.clip(T / 0.7, 0, 1)[..., None]; t2 = np.clip((T - 0.7) / 0.6, 0, 1)[..., None]
        rgb = ((c0 + (c1 - c0) * t1) * (1 - t2) + c2 * t2) * (0.40 + 0.85 * T[..., None])
    os.makedirs(TEX, exist_ok=True); np.save(fn, rgb.astype(F32)); return rgb.astype(F32)


@functools.lru_cache(maxsize=8)
def ns_tex_blur(kind, bw):
    """texture smeared along longitude (rotational motion blur), bw in texels"""
    t = ns_tex(kind)
    if bw < 2: return t
    k = int(bw) | 1; pad = np.concatenate([t[:, -k:], t, t[:, :k]], 1)
    return cv2.blur(pad, (k, 1))[:, k:-k]


def draw_star(img, cx, cy, Rapp, M, u=U_NS, kind="ns", gain=1.0, blur=0, limb=0.55, halo=1.0, halo_col=(0.35, 0.6, 1.0), alpha=1.0, grid=0.0, horizon=0.0):
    """Sphere of apparent radius Rapp px. M: body <- camera (camera x right, y up, z to viewer).
    u = rs/R sets the light bending (0 = none); returns nothing, composites into img."""
    hs = max(2.0, Rapp * (0.075 if kind == 'rsg' else 0.042))
    g = _grid(cx, cy, Rapp, hs * 8 + 6)
    if g is None: return
    x0, y0, x1, y1, uu, vv = g
    rho = np.sqrt(uu * uu + vv * vv); ca = np.sqrt(np.clip(1 - rho * rho, 0, 1))
    cpsi = np.clip(1 - (1 - ca) / (1 - u), -1, 1); spsi = np.sqrt(1 - cpsi * cpsi)
    rs_ = np.maximum(rho, 1e-6); nx = spsi * uu / rs_; ny = spsi * vv / rs_; nz = cpsi
    Mf = M.astype(F32)
    bx = nx * Mf[0, 0] + ny * Mf[0, 1] + nz * Mf[0, 2]; by = nx * Mf[1, 0] + ny * Mf[1, 1] + nz * Mf[1, 2]; bz = nx * Mf[2, 0] + ny * Mf[2, 1] + nz * Mf[2, 2]
    lat = np.arcsin(np.clip(bz, -1, 1)); lon = np.arctan2(by, bx)
    t = ns_tex_blur(kind, int(blur)) if blur else ns_tex(kind)
    surf = samp(t, lat, lon) * ((1 - limb) + limb * ca ** 0.7)[..., None] * gain
    if kind == "rsg":
        surf = surf * (0.45 + 0.55 * ca ** 0.5)[..., None]
    if grid > 0:                                    # graticule every 15 degrees (shows how the far side is pulled into view)
        wl = 0.011; dla = np.abs((lat / math.radians(15) + 0.5) % 1.0 - 0.5) * math.radians(15); dlo = np.abs((lon / math.radians(15) + 0.5) % 1.0 - 0.5) * math.radians(15) * np.cos(lat)
        gl = np.maximum(np.exp(-(dla / wl) ** 2), np.exp(-(dlo / wl) ** 2))
        surf = surf * (1 - 0.5 * grid * gl[..., None]) + (gl * grid)[..., None] * np.array([0.75, 0.95, 1.0], F32) * 0.9
    if horizon > 0:                                 # where the limb would be without light bending (psi = 90 deg)
        hl = np.exp(-(cpsi / 0.02) ** 2) * horizon
        surf = surf * (1 - hl[..., None]) + hl[..., None] * np.array([1.0, 0.72, 0.25], F32) * 1.2
    hpx = np.clip((rho - 1) * Rapp, 0, None)
    hal = (np.exp(-hpx / hs) * 0.9 + np.exp(-hpx / (hs * 4)) * 0.22 + np.exp(-hpx / (hs * 14)) * 0.05) * halo * gain * np.clip(1 - hpx / (hs * 8), 0, 1) ** 1.5
    a = np.clip((1 - rho) * Rapp + 0.5, 0, 1)[..., None] * alpha
    if kind == 'rsg':                                # no sharp edge: the photosphere of a supergiant is diffuse
        a = (np.clip((1 - rho) / 0.09, 0, 1) ** 1.2)[..., None] * alpha
        hal = (np.exp(-np.clip(rho - 0.93, 0, None) * Rapp / (hs * 2.2)) * 0.42 + np.exp(-np.clip(rho - 0.93, 0, None) * Rapp / (hs * 7)) * 0.10) * halo * gain * np.clip(1 - hpx / (hs * 8), 0, 1) ** 1.5
    else:
        surf = surf + (np.exp(-((1 - rho) * Rapp / (hs * 0.8))) * 0.55 * gain * halo)[..., None] * np.array([0.6, 0.8, 1.0], F32)   # bright rim of hot atmosphere
    reg = img[y0:y1, x0:x1]
    reg[:] = reg * (1 - a) + surf * a + (hal * (1 - a[..., 0]) * alpha)[..., None] * np.array(halo_col, F32)


def lens_sky(sky, cx, cy, k, off=(0.0, 0.0), out_size=None):
    """weak-field lensing remap: a pixel at radius r from (cx, cy) shows the unlensed sky at radius r - k / r.
    sky: unlensed image on a canvas that may be larger than the frame; off = position of the frame's (0,0) in it."""
    w, h = out_size or (W, H)
    xs = np.arange(w, dtype=F32) + 0.5 - cx; ys = np.arange(h, dtype=F32) + 0.5 - cy
    X, Y = np.meshgrid(xs, ys); r2 = np.maximum(X * X + Y * Y, 4.0); fct = 1 - k / r2
    return cv2.remap(sky, (cx + X * fct + off[0]).astype(F32), (cy + Y * fct + off[1]).astype(F32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def lens_k(Rapp, f, u=U_NS):
    """k (px^2) for a star of apparent radius Rapp px seen with focal length f px"""
    return 2.0 * f * u * Rapp * math.sqrt(1 - u)


def field_lines(img, cx, cy, Rtrue, Rocc, Mc, shells=(1.8, 2.6, 3.8, 5.6, 8.5), naz=10, col=(0.45, 0.75, 1.0), gain=0.5, twist=0.0, phase=0.0, th=1, glow=0.7, flow=None):
    """dipole field lines r = L sin^2(theta) in the magnetic frame; Mc: camera <- magnetic frame. Rocc = occluding disc radius (px)."""
    Lf = Lines(); Lb = Lines()
    th_ = np.linspace(0, np.pi, 260)
    for L in shells:
        t0 = math.asin(1 / math.sqrt(L)); tt = t0 + (np.pi - 2 * t0) * (0.5 - 0.5 * np.cos(th_))
        r = L * np.sin(tt) ** 2
        for j in range(naz):
            az = phase + 2 * np.pi * (j + 0.37 * (L % 1.0)) / naz + twist * np.sin(tt) ** 2 * (1.0 / L)
            P = np.stack([r * np.sin(tt) * np.cos(az), r * np.sin(tt) * np.sin(az), r * np.cos(tt)], 1) @ Mc.T
            x = cx + Rtrue * P[:, 0]; y = cy - Rtrue * P[:, 1]
            hid = (P[:, 2] < 0) & ((x - cx) ** 2 + (y - cy) ** 2 < Rocc * Rocc)
            front = P[:, 2] >= 0
            a0 = 255 * min(1.0, 1.25 / L ** 0.45)
            xf = np.where(front & ~hid, x, np.nan); xb = np.where(~front & ~hid, x, np.nan)
            Lf.poly(xf, y, a=a0, th=th); Lb.poly(xb, y, a=a0 * 0.55, th=th)
    Lb.add_to(img, col, gain=gain * 0.8, glow=glow); Lf.add_to(img, col, gain=gain, glow=glow)


def beams(cx, cy, Rtrue, axis, size=None, length=9.0, half=0.16, hollow=0.5, gain=1.0, seed=0, ds=3, occ=1.0):
    """two opposite emission cones along `axis` (unit, camera space), integrated along the line of sight (orthographic).
    Returns a single-channel float image (h, w)."""
    w, h = size or (W, H); ws, hs_ = w // ds, h // ds
    xs = ((np.arange(ws, dtype=F32) + 0.5) * ds - cx) / Rtrue; ys = -((np.arange(hs_, dtype=F32) + 0.5) * ds - cy) / Rtrue
    X, Y = np.meshgrid(xs, ys); a = np.asarray(axis, F32)
    out = np.zeros((hs_, ws), F32); nz = 30; zs = np.linspace(-length, length, nz).astype(F32); dz = zs[1] - zs[0]
    inside = X * X + Y * Y < occ * occ
    for z in zs:
        s = X * a[0] + Y * a[1] + z * a[2]; r2 = X * X + Y * Y + z * z
        d2 = np.maximum(r2 - s * s, 0); sa = np.abs(s) + 0.05
        tn = np.sqrt(d2) / sa
        dens = np.exp(-((tn - hollow * half) / (half * 0.55)) ** 2) + 0.55 * np.exp(-(tn / (half * 0.35)) ** 2)
        dens *= (1 / (1 + (sa / 2.2) ** 1.7)) * np.clip((np.sqrt(r2) - 1.0) / 0.15, 0, 1) * np.exp(-(sa / (length * 0.8)) ** 4)
        if z < 0: dens = np.where(inside, 0, dens)
        out += dens
    out *= dz * gain
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)


# ------------------------------------------------------------------------------------------------ explosions
@functools.lru_cache(None)
def expl_layers(seed, n=6, size=1280, kind="sn"):
    """n single-channel layers of filamentary shell structure (unit disc = the shock radius)"""
    fn = f"{TEX}/expl2_{kind}_{seed}_{n}_{size}.npy"
    if os.path.exists(fn): return np.load(fn)
    c = (np.arange(size, dtype=F32) + 0.5) / size * 2.3 - 1.15; X, Y = np.meshgrid(c, c); rho = np.sqrt(X * X + Y * Y); phi = np.arctan2(Y, X)
    out = []
    for i in range(n):
        a = fbm2(size, 2.6, seed * 31 + i * 7 + 1, lo=3); b = fbm2(size, 2.2, seed * 31 + i * 7 + 2, lo=6); cnoise = fbm2(size, 3.0, seed * 31 + i * 7 + 3, lo=2)
        fil = np.clip(1 - np.abs(a) / 0.55, 0, 1) ** 5 + 0.6 * np.clip(1 - np.abs(b) / 0.45, 0, 1) ** 7
        # radial fingers (Rayleigh-Taylor like): noise sampled in (angle, log radius)
        fmap_x = ((phi / (2 * np.pi) + 0.5) * size * (2 + i % 3)) % size; fmap_y = (np.log(np.maximum(rho, 0.02)) * size * 0.11 + i * 97) % size
        fing = cv2.remap(fbm2(size, 2.0, seed * 31 + i * 7 + 4, lo=5), fmap_x.astype(F32), fmap_y.astype(F32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        fing = np.clip(0.5 + 0.6 * fing, 0, 1.6)
        edge = 1.0 + 0.045 * cv2.remap(fbm2(size, 3.6, seed * 31 + i * 7 + 5, lo=1, hi=14), ((phi / (2 * np.pi) + 0.5) * size).astype(F32), np.full_like(fmap_x, 5.0), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        rr = rho / edge
        if kind == "sn":
            r0 = 1.0 - 0.13 * i; wdt = 0.07 + 0.035 * i
            env = np.exp(-((rr - r0) / wdt) ** 2) * (1.0 if i < 2 else 0.8) + (0.20 * np.clip(1 - rr / max(r0, 0.2), 0, 1) ** 0.6 if i >= 2 else 0)
            lay = env * (0.25 + 1.5 * fil * fing + 0.35 * np.clip(cnoise + 0.4, 0, 2))
            if i == 0: lay = np.exp(-((rr - 1.0) / 0.022) ** 2) * (0.7 + 0.5 * fing) + 0.5 * lay      # thin outer shock
        else:                                                           # "ball": turbulent filled cloud (kilonova / blast)
            r0 = 1.0 - 0.10 * i
            env = np.clip(1 - (rr / r0) ** 2, 0, 1) ** 0.55 * (0.45 + 0.55 * np.exp(-((rr - 0.8 * r0) / (0.22 * r0)) ** 2))
            lay = env * (0.30 + 1.2 * fil * fing + 0.55 * np.clip(cnoise * 0.8 + 0.5, 0, 2) ** 2)
        lay *= np.clip((1.12 - rho) / 0.05, 0, 1)
        out.append(lay.astype(F32))
    out = np.stack(out); np.save(fn, out); return out


def draw_expl(img, layers, cx, cy, Rpx, cols, gains, rot=0.0, spread=0.0, squash=1.0):
    """additively composite the layers scaled so that the unit disc has radius Rpx. cols: list of RGB; gains: per-layer."""
    n, size = layers.shape[0], layers.shape[1]
    for i in range(n):
        if gains[i] <= 0.002: continue
        s = Rpx * (1 + spread * i) / (size / 2.3); ang = rot * (1 + 0.35 * i) * (1 if i % 2 == 0 else -1) + i * 47.0
        Mx = cv2.getRotationMatrix2D((size / 2, size / 2), ang, s); Mx[0, 2] += cx - size / 2; Mx[1, 2] += cy - size / 2
        if squash != 1.0: Mx[1, :2] *= squash; Mx[1, 2] = cy + (Mx[1, 2] - cy) * squash
        o = cv2.warpAffine(layers[i], Mx, (W, H), flags=cv2.INTER_LINEAR if s > 0.5 else cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        img += o[..., None] * (np.array(cols[i], F32) * gains[i])


# ------------------------------------------------------------------------------------------------ cut-away
def draw_cutaway(img, bg, cx, cy, R, ang_deg, face_fn, tilt_deg=0.0):
    """Remove the half of a sphere in front of a plane through its centre. The plane contains the screen's vertical axis (rotated by
    tilt) and its normal makes ang_deg with the line of sight. img already holds the full sphere; bg is the frame without it.
    face_fn(q (..,3 in units of R, camera space), r) -> RGB for points of the cut face. Returns mask of the face."""
    g = _grid(cx, cy, R, 3)
    if g is None: return None
    x0, y0, x1, y1, u, v = g
    a = math.radians(ang_deg); n = np.array([math.sin(a), 0.0, math.cos(a)], F32)
    if tilt_deg: n = (rot_axis((0, 0, 1), math.radians(tilt_deg)) @ n).astype(F32)
    rr = u * u + v * v; zf = np.sqrt(np.clip(1 - rr, 0, 1))
    removed = (n[0] * u + n[1] * v + n[2] * zf > 0) & (rr < 1)
    zp = -(n[0] * u + n[1] * v) / n[2]
    rq = np.sqrt(rr + zp * zp); face = removed & (rq <= 1)
    q = np.stack([u, v, zp], -1)
    col = face_fn(q, rq)
    edge = np.clip((1 - rq) * R + 0.5, 0, 1) * np.clip((1 - np.sqrt(rr)) * R + 0.5, 0, 1)
    reg = img[y0:y1, x0:x1]; bgr = bg[y0:y1, x0:x1]
    reg[removed] = bgr[removed]
    fm = (face * edge)[..., None]
    reg[:] = reg * (1 - fm) + col * fm
    full = np.zeros((H, W), F32); full[y0:y1, x0:x1] = face * edge
    return full


@functools.lru_cache(None)
def _face_noise():
    return fbm2(1024, 2.4, 77, lo=2), fbm2(1024, 2.0, 78, lo=4), fbm2(1024, 3.0, 79, lo=1)


def _fn(q, k, sc, off=(0, 0)):
    n = _face_noise()[k]
    return cv2.remap(n, ((q[..., 0] * sc + 0.5 + off[0]) * 1024 % 1024).astype(F32), ((q[..., 1] * sc + 0.3 * q[..., 2] * sc + 0.5 + off[1]) * 1024 % 1024).astype(F32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def earth_face(t=0.0):
    """Earth interior colours (radii in fractions of 6371 km: inner core 0.192, outer core 0.546, 660-km boundary 0.895, crust ~0.994)"""
    def f(q, r):
        n1 = _fn(q, 0, 0.9, (0.01 * t, 0)); n2 = _fn(q, 1, 2.2, (0, 0.006 * t)); n3 = _fn(q, 2, 0.5)
        col = np.zeros(q.shape, F32)
        ic = r < 0.192; oc = (r >= 0.192) & (r < 0.546); lm = (r >= 0.546) & (r < 0.895); um = (r >= 0.895) & (r < 0.992); cr = r >= 0.992
        col[ic] = (np.array([1.0, 0.93, 0.66], F32) * (1.25 - 0.9 * r[ic] / 0.192 * 0.25 + 0.05 * n2[ic])[..., None])
        swirl = 0.5 + 0.5 * np.sin(40 * r + 3.0 * n1 + 1.5 * n3)
        col[oc] = (np.array([1.0, 0.50, 0.10], F32) * (0.62 + 0.25 * swirl[oc] + 0.10 * n2[oc])[..., None] + np.array([0.3, 0.2, 0.0], F32) * np.clip(1 - (r[oc] - 0.192) / 0.12, 0, 1)[..., None])
        conv = 0.5 + 0.5 * np.sin(9 * np.arctan2(q[..., 1], q[..., 0] + 1e-6) + 5 * n3 + 14 * r)
        col[lm] = np.array([0.62, 0.13, 0.04], F32) * (0.50 + 0.30 * conv[lm] + 0.16 * n1[lm] + 0.10 * n2[lm])[..., None]
        col[um] = np.array([0.80, 0.30, 0.08], F32) * (0.50 + 0.2 * conv[um] + 0.2 * n2[um])[..., None]
        col[cr] = np.array([0.35, 0.30, 0.27], F32)
        for rb, wdt, g in ((0.192, 0.004, 0.5), (0.546, 0.005, 0.6), (0.895, 0.003, 0.25)):
            col += (np.exp(-((r - rb) / wdt) ** 2) * g)[..., None] * np.array([1.0, 0.8, 0.5], F32)
        return np.clip(col, 0, 3)
    return f


def ns_face():
    """neutron-star interior (fractions of R = 12 km): outer crust ~0.4 km, inner crust ~0.8 km, outer core, inner core (unknown)"""
    def f(q, r):
        n1 = _fn(q, 0, 1.1); n2 = _fn(q, 1, 3.0); n3 = _fn(q, 2, 0.6)
        col = np.zeros(q.shape, F32)
        ic = r < 0.42; oc = (r >= 0.42) & (r < 0.90); icr = (r >= 0.90) & (r < 0.967); ocr = r >= 0.967
        col[ic] = np.array([0.95, 0.30, 0.75], F32) * (0.45 + 0.45 * (1 - r[ic] / 0.42) + 0.10 * n1[ic])[..., None] + np.array([0.6, 0.6, 0.9], F32) * (np.clip(1 - r[ic] / 0.2, 0, 1) ** 2 * 0.5)[..., None]
        sw = 0.5 + 0.5 * np.sin(55 * r + 3.5 * n1 + 2 * n3)
        col[oc] = np.array([0.16, 0.24, 0.95], F32) * (0.34 + 0.22 * sw[oc] + 0.14 * n2[oc] + 0.10 * n1[oc] + 0.9 * (0.9 - r[oc]))[..., None] + np.array([0.25, 0.1, 0.5], F32) * (np.clip(1 - (r[oc] - 0.42) / 0.2, 0, 1) ** 2 * 0.5)[..., None]
        lat_ = 0.5 + 0.5 * np.sin(q[..., 0] * 240 + 2 * n2) * np.sin(q[..., 1] * 240)
        col[icr] = np.array([0.25, 0.55, 1.0], F32) * (0.55 + 0.25 * lat_[icr] + 0.15 * n2[icr])[..., None]
        col[ocr] = np.array([0.75, 0.9, 1.0], F32) * (0.9 + 0.25 * n2[ocr])[..., None]
        for rb, wdt, g in ((0.42, 0.006, 0.35), (0.90, 0.004, 0.7), (0.967, 0.003, 0.7)):
            col += (np.exp(-((r - rb) / wdt) ** 2) * g)[..., None] * np.array([0.7, 0.85, 1.0], F32)
        return np.clip(col, 0, 3)
    return f


# ------------------------------------------------------------------------------------------------ New York relief map
NYC_X0, NYC_Y0, NYC_Z = 1197, 1530, 12
M_PER_PX = 156543.03392 * math.cos(math.radians(40.75)) / 2 ** NYC_Z      # ~28.95 m


def ll2px(lat, lon):
    n = 2 ** NYC_Z; x = (lon + 180) / 360 * n; y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return (x - NYC_X0) * 256, (y - NYC_Y0) * 256


MAN = ll2px(40.776, -73.972)            # map pixel of mid-Manhattan = ground origin


def ground_km(lat, lon):
    """ground coordinates (km east, km north) relative to mid-Manhattan"""
    x, y = ll2px(lat, lon); return (x - MAN[0]) * M_PER_PX / 1000, -(y - MAN[1]) * M_PER_PX / 1000


@functools.lru_cache(None)
def nyc_map():
    """pre-shaded top-down map (RGB float), water mask and elevation; real elevation (Mapzen/AWS terrain tiles, zoom 12)"""
    fn = TEX + "/nyc_map2.npy"
    if os.path.exists(fn): return np.load(fn), np.load(TEX + "/nyc_water2.npy")
    E = np.load(TEX + "/nyc_elev.npy")
    wraw = (cv2.GaussianBlur((E < 1.5).astype(F32), (0, 0), 1.5) > 0.5).astype(np.uint8)
    # drop small land specks inside water and small water specks inside land
    nl, lab, st, _ = cv2.connectedComponentsWithStats(1 - wraw, connectivity=4)
    small = np.isin(lab, np.where(st[:, cv2.CC_STAT_AREA] < 1300)[0]); wraw[small] = 1
    nl, lab, st, _ = cv2.connectedComponentsWithStats(wraw, connectivity=4)
    small = np.isin(lab, np.where(st[:, cv2.CC_STAT_AREA] < 500)[0]); wraw[small] = 0
    water = cv2.GaussianBlur(wraw.astype(F32), (0, 0), 1.0)
    El = np.clip(E, 0, None); Es = cv2.GaussianBlur(El, (0, 0), 1.2)
    gx = cv2.Sobel(Es, cv2.CV_32F, 1, 0, ksize=3) / (8 * M_PER_PX); gy = cv2.Sobel(Es, cv2.CV_32F, 0, 1, ksize=3) / (8 * M_PER_PX)
    ex = 9.0; nrm = 1 / np.sqrt(1 + (ex * gx) ** 2 + (ex * gy) ** 2)
    lx, ly, lz = norm([-0.6, -0.55, 0.58])                    # light from the north-west (image coords: y down)
    shade = np.clip((-ex * gx * lx - ex * gy * ly + lz) * nrm, 0, 1.6)
    # hypsometric tint: dark slate lowlands -> warm grey ridges
    tnt = np.clip(Es / 320.0, 0, 1)[..., None] ** 0.7
    land = (np.array([0.105, 0.125, 0.150], F32) * (1 - tnt) + np.array([0.30, 0.27, 0.23], F32) * tnt) * (0.35 + 0.95 * shade[..., None])
    # fine real detail from the lidar-derived surface (roads, blocks, runways): high-pass of the elevation
    hp = E - cv2.GaussianBlur(E, (0, 0), 2.5); land += (np.clip(hp, -3, 3) / 3)[..., None] * 0.035 * (1 - water[..., None])
    # contour lines every 20 m (and bolder every 100 m)
    def contour(step, wd):
        ph = Es / step; d = np.abs(ph - np.round(ph)) * step; gm = np.sqrt(gx * gx + gy * gy) * M_PER_PX + 1e-4
        return np.clip(1 - d / (gm * wd), 0, 1) * (Es > 6)
    land += (contour(20.0, 0.9) * 0.10 + contour(100.0, 1.4) * 0.16)[..., None] * np.array([0.75, 0.85, 1.0], F32)
    dist = cv2.distanceTransform((water > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    sea = np.array([0.012, 0.030, 0.062], F32) * (1.25 - 0.55 * np.clip(dist / 260, 0, 1))[..., None]
    sea = sea + (np.exp(-dist / 5.0) * 0.07)[..., None] * np.array([0.5, 0.8, 1.0], F32)        # shoal glow at the shore
    rgb = land * (1 - water[..., None]) + sea * water[..., None]
    coast = np.clip(1 - np.abs(water - 0.5) / 0.38, 0, 1); rgb += coast[..., None] * np.array([0.42, 0.62, 0.80], F32) * 0.30
    np.save(fn, rgb.astype(F32)); np.save(TEX + "/nyc_water2.npy", water.astype(F32))
    return rgb.astype(F32), water.astype(F32)


def ground_view(cam, tex_img, lit=None, ss_=2, haze=(0.02, 0.035, 0.06), haze_km=160.0):
    """perspective view of the ground plane z = 0 (x east, y north, km; origin mid-Manhattan) textured with the map"""
    Wc, Hc = W * ss_, H * ss_
    # homography from map pixels to screen through 4 ground points
    pts_g = np.array([[-30, -30, 0], [30, -30, 0], [30, 30, 0], [-30, 30, 0]], float)
    sx, sy, d = cam.proj(pts_g)
    src = np.stack([MAN[0] + pts_g[:, 0] * 1000 / M_PER_PX, MAN[1] - pts_g[:, 1] * 1000 / M_PER_PX], 1).astype(F32)
    dst = np.stack([sx * ss_, sy * ss_], 1).astype(F32)
    Hm = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(tex_img, Hm, (Wc, Hc), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if ss_ > 1: out = cv2.resize(out, (W, H), interpolation=cv2.INTER_AREA)
    if out.ndim == 2: out = out[..., None]
    # distance haze + horizon mask
    xs = (np.arange(W, dtype=F32) + 0.5 - W / 2 - cam.ox) / cam.f; ys = -(np.arange(H, dtype=F32) + 0.5 - H / 2 - cam.oy) / cam.f
    X, Y = np.meshgrid(xs, ys); Rm = cam.R.astype(F32)
    dz = X * Rm[0, 2] + Y * Rm[1, 2] - Rm[2, 2]; nrm = np.sqrt(X * X + Y * Y + 1)
    tgr = np.where(dz < -1e-4, -cam.eye[2] / np.minimum(dz, -1e-4), 1e9) * nrm
    hz = 1 - np.exp(-tgr / haze_km); hz = np.clip(hz, 0, 1)[..., None]
    grd = (dz < 0)[..., None]
    return out * (1 - hz) * grd + np.array(haze, F32) * hz * grd, grd[..., 0], tgr
