"""Analytic planet renderer (numpy): oblate ellipsoid + optional rings, procedural or Blue Marble textures.
View space: x right, y up, z towards the viewer (orthographic).  Everything is our own render."""
import os, math
import numpy as np
from PIL import Image
from lib import TEX, blur
from sky import _noise

GLOBE = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/dl_globe/package/example"


def nrm(v):
    v = np.asarray(v, np.float64); return v / np.linalg.norm(v)


def samp(t, lat, lon):
    h, w = t.shape[:2]
    x = ((lon / (2 * np.pi) + 0.5) % 1.0) * w - 0.5; y = np.clip((0.5 - lat / np.pi) * h - 0.5, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32); fx = (x - x0).astype(np.float32); fy = (y - y0).astype(np.float32)
    x0 %= w; x1 = (x0 + 1) % w
    if t.ndim == 3: fx = fx[..., None]; fy = fy[..., None]
    a = t[y0, x0] * (1 - fx) + t[y0, x1] * fx; b = t[y0 + 1, x0] * (1 - fx) + t[y0 + 1, x1] * fx
    return a * (1 - fy) + b * fy


def cached(name, fn):
    p = os.path.join(TEX, name + ".npy")
    if os.path.exists(p): return np.load(p).astype(np.float32)
    a = fn(); np.save(p, a.astype(np.float16)); return a.astype(np.float32)


def _profile(lat_deg, pts):
    xs = np.array([p[0] for p in pts], np.float32); cs = np.array([p[1] for p in pts], np.float32)
    return np.stack([np.interp(lat_deg, xs, cs[:, c]) for c in range(3)], -1)


# ------------------------------------------------------------------------------------------------ textures
def _hn(shape, beta, seed, aniso=1.0, kmin=1.5):
    """noise stretched along longitude (x) by `aniso`"""
    return np.ascontiguousarray(_noise((shape[1], shape[0]), beta, seed, aniso=aniso, kmin=kmin).T)


def _warp(img, dx, dy):
    """backward warp (bilinear, wraps in x) of an equirect image by a pixel displacement field"""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x = xx + dx; y = np.clip(yy + dy, 0, h - 1.001)
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x0 %= w; x1 = (x0 + 1) % w
    return (img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x1] * fx) * fy


def jupiter_tex(Nw=4096):
    Nh = Nw // 2; ppd = Nw / 360.0
    lon = (np.arange(Nw, dtype=np.float32) + 0.5) / Nw * 360 - 180; lat = 90 - (np.arange(Nh, dtype=np.float32) + 0.5) / Nh * 180
    LON, LAT = np.meshgrid(lon, lat)
    cream = (0.86, 0.80, 0.68); white = (0.93, 0.90, 0.82); belt = (0.56, 0.36, 0.22); dbelt = (0.42, 0.26, 0.17)
    tan = (0.74, 0.62, 0.46); polar = (0.46, 0.43, 0.40); ochre = (0.78, 0.60, 0.38); blue = (0.46, 0.50, 0.58)
    pts = [(-90, polar), (-68, polar), (-60, (0.56, 0.50, 0.44)), (-54, tan), (-50, (0.6, 0.5, 0.4)), (-46, cream), (-42, tan), (-38, (0.62, 0.46, 0.33)),
           (-35, tan), (-31, cream), (-26, white), (-22, ochre), (-19, belt), (-16.5, dbelt), (-14, (0.62, 0.42, 0.27)), (-12, dbelt), (-9.5, belt),
           (-7.5, ochre), (-5.5, white), (-2, cream), (0, (0.80, 0.72, 0.58)), (2.5, white), (5.5, cream), (7.2, blue), (8.5, dbelt), (11, belt),
           (13, (0.5, 0.31, 0.2)), (16, dbelt), (18.5, ochre), (21, white), (25, cream), (28, (0.66, 0.5, 0.36)), (30, (0.58, 0.42, 0.3)), (32, tan),
           (36, cream), (40, (0.64, 0.52, 0.42)), (44, tan), (48, (0.6, 0.52, 0.45)), (53, (0.56, 0.50, 0.45)), (60, (0.5, 0.46, 0.42)), (66, polar), (90, polar)]
    sh = (Nh, Nw)
    n1 = _hn(sh, 2.0, 31, aniso=7.0, kmin=6); n3 = _hn(sh, 1.5, 33, aniso=22.0, kmin=10); n3b = _hn(sh, 1.2, 36, aniso=9.0, kmin=40)
    psi1 = _noise(sh, 3.0, 37, kmin=24); psi2 = _noise(sh, 2.6, 38, kmin=70); n5 = _noise(sh, 1.6, 35, kmin=20)
    edges = sum(np.exp(-((LAT - e) / 2.2) ** 2) for e in (-21, -8, 7.5, 19, -34, 30, 42, -44, -12, 13))
    turb = 0.30 + 1.0 * np.clip(edges, 0, 1.3) + 0.9 * np.clip((np.abs(LAT) - 46) / 16, 0, 1)
    g_lon, g_lat, ga, gb = -35.0, -21.5, 10.5, 5.6
    dl = ((LON - g_lon + 180) % 360 - 180); rho = np.sqrt((dl / ga) ** 2 + ((LAT - g_lat) / gb) ** 2)
    wake = np.exp(-((LAT + 15) / 5) ** 2) * np.clip(dl / 8, 0, 1) * np.exp(-np.clip(dl, 0, None) / 60)
    turb = turb * (1 + 2.5 * wake)
    # base: banded profile with gentle waviness, bent around the Great Red Spot
    bend = 4.4 * np.exp(-(rho / 1.5) ** 2) * np.tanh((LAT - g_lat) / 2.2)
    col = _profile(LAT + 0.3 * turb * n1 + bend, pts)
    col *= (1 + 0.07 * n3 + 0.05 * n3b)[..., None]
    # festoons: blue-grey plumes trailing from the NEB south edge into the equatorial zone
    ph = np.radians(LON * 14 + 50 * n1)
    fest = np.exp(-((LAT - 5.5 + 2.0 * np.sin(ph)) / 1.3) ** 2) * np.clip(np.sin(ph * 0.5) ** 8, 0, 1) + 0.6 * np.exp(-((LAT - 7.3) / 0.9) ** 2) * np.clip(np.sin(ph) * 0.5 + 0.5, 0, 1)
    col = col * (1 - 0.45 * np.clip(fest, 0, 1)[..., None]) + 0.45 * np.clip(fest, 0, 1)[..., None] * np.array(blue, np.float32) * 0.8
    # spots before the eddy warp so the flow wraps them
    ang = np.arctan2((LAT - g_lat) / gb, dl / ga)
    spiral = 0.5 + 0.5 * np.sin(rho * 13 - ang * 2 + 1.5 * n5)
    grs = np.array([0.70, 0.33, 0.21], np.float32) * (0.80 + 0.25 * spiral)[..., None] * (0.86 + 0.3 * np.clip(1 - rho * 1.5, 0, 1))[..., None]
    collar = np.exp(-((rho - 1.2) / 0.15) ** 2)[..., None] * 0.6
    col = col * (1 - collar) + collar * np.array([0.92, 0.88, 0.78], np.float32)
    m = np.clip((1.0 - rho) / 0.10, 0, 1)[..., None]; col = col * (1 - m) + grs * m
    r = np.random.default_rng(8); calm = np.clip((rho - 0.95) / 0.7, 0, 1)
    for k in range(9):
        l0 = r.uniform(-180, 180); b0 = -33 + r.normal(0, 0.6); a0 = r.uniform(1.6, 3.0)
        rr = np.sqrt((((LON - l0 + 180) % 360 - 180) / a0) ** 2 + ((LAT - b0) / (a0 * 0.66)) ** 2)
        mm = np.clip((1 - rr) / 0.35, 0, 1)[..., None] * 0.92; col = col * (1 - mm) + mm * np.array([0.93, 0.91, 0.85], np.float32)
        mm = np.exp(-((rr - 1.3) / 0.22) ** 2)[..., None] * 0.35; col = col * (1 - mm) + mm * np.array([0.48, 0.34, 0.26], np.float32)
        calm = calm * np.clip(rr / 1.6, 0, 1)
    for k in range(7):
        l0 = r.uniform(-180, 180); b0 = 16.8 + r.normal(0, 0.4); a0 = r.uniform(2.5, 4.5)
        rr = np.sqrt((((LON - l0 + 180) % 360 - 180) / a0) ** 2 + ((LAT - b0) / (a0 * 0.28)) ** 2)
        mm = np.clip((1 - rr) / 0.5, 0, 1)[..., None] * 0.75; col = col * (1 - mm) + mm * np.array([0.27, 0.15, 0.10], np.float32)
    # eddies: advect the picture twice along the curl of a stream function (large swirls, then small ones);
    # zonal jets are added to the stream function so that eddies are sheared along the band edges
    def curl(psi, amp):
        dpy = (np.roll(psi, -1, 0) - np.roll(psi, 1, 0)) * 0.5; dpx = (np.roll(psi, -1, 1) - np.roll(psi, 1, 1)) * 0.5
        sc = amp / (np.abs(np.stack([dpx, dpy])).mean() + 1e-9)
        return dpy * sc, -dpx * sc
    tw = (turb * calm).astype(np.float32)
    psi0 = blur(_noise(sh, 4.0, 40, kmin=30), 7); psi2b = blur(_noise(sh, 4.0, 41, kmin=90), 3)
    ux, uy = curl(psi0, 3.0)
    for it in range(10):                                    # many small steps along a smooth flow -> curls, not fuzz
        col = _warp(col, ux * tw, uy * tw * 0.8)
    ux, uy = curl(psi2b, 1.5)
    for it in range(6):
        col = _warp(col, ux * tw, uy * tw)
    # fine cloud texture and polar mottling
    col *= (1 + 0.035 * n5 * np.clip(turb, 0, 2))[..., None]
    pm = np.clip((np.abs(LAT) - 50) / 14, 0, 1)
    pn = _noise(sh, 2.6, 39, kmin=30)
    col *= (1 + 0.10 * pm * pn)[..., None]
    return np.clip(col, 0, 1) ** 1.12


def saturn_tex(Nw=2048):
    Nh = Nw // 2
    lon = (np.arange(Nw, dtype=np.float32) + 0.5) / Nw * 360 - 180; lat = 90 - (np.arange(Nh, dtype=np.float32) + 0.5) / Nh * 180
    LON, LAT = np.meshgrid(lon, lat)
    a = (0.86, 0.76, 0.56); b = (0.78, 0.66, 0.45); c = (0.90, 0.82, 0.64); d = (0.70, 0.62, 0.48); p = (0.56, 0.58, 0.56)
    pts = [(-90, p), (-72, (0.62, 0.62, 0.56)), (-60, d), (-50, b), (-42, a), (-34, b), (-27, c), (-20, a), (-13, b), (-6, c), (0, (0.93, 0.85, 0.66)),
           (6, c), (12, b), (18, a), (25, c), (32, b), (40, a), (48, b), (58, d), (70, (0.62, 0.62, 0.56)), (90, p)]
    n1 = _hn((Nh, Nw), 2.6, 41, aniso=9.0); n3 = _hn((Nh, Nw), 1.6, 43, aniso=24.0); n1d = _noise((Nh, 8), 1.0, 44)[:, :1]
    col = _profile(LAT + 0.8 * n1 + 1.2 * n1d, pts)
    col *= (1 + 0.035 * n3 + 0.03 * n1d)[..., None]
    return np.clip(col, 0, 1)


def io_tex(Nw=1024):
    Nh = Nw // 2
    n1 = _noise((Nh, Nw), 2.4, 51); n2 = _noise((Nh, Nw), 1.6, 52); n3 = _noise((Nh, Nw), 3.0, 53)
    base = np.array([0.86, 0.74, 0.34], np.float32) * (1 + 0.12 * n2)[..., None]
    wht = np.clip(n1 * 0.8 + 0.2, 0, 1)[..., None]; col = base * (1 - 0.5 * wht) + 0.5 * wht * np.array([0.93, 0.90, 0.74], np.float32)
    org = np.clip(n3 * 0.9 - 0.3, 0, 1)[..., None]; col = col * (1 - 0.6 * org) + 0.6 * org * np.array([0.80, 0.42, 0.16], np.float32)
    lat = np.linspace(90, -90, Nh, dtype=np.float32)[:, None]
    pol = np.clip((np.abs(lat) - 50) / 30, 0, 1)[..., None]; col = col * (1 - 0.45 * pol) + 0.45 * pol * np.array([0.5, 0.33, 0.2], np.float32)
    r = np.random.default_rng(5); yy, xx = np.mgrid[0:Nh, 0:Nw].astype(np.float32)
    for k in range(70):                                         # dark calderas with red/pale haloes
        x0, y0, s0 = r.uniform(0, Nw), r.uniform(Nh * 0.12, Nh * 0.88), r.uniform(1.5, 6)
        d2 = (((xx - x0 + Nw / 2) % Nw - Nw / 2) ** 2 + (yy - y0) ** 2) / (s0 * s0)
        halo = np.exp(-d2 / 14)[..., None] * r.uniform(0.1, 0.5)
        col = col * (1 - halo) + halo * (np.array([0.75, 0.3, 0.12], np.float32) if r.random() < 0.5 else np.array([0.95, 0.93, 0.8], np.float32))
        col *= (1 - 0.92 * np.exp(-d2))[..., None]
    return np.clip(col, 0, 1)


def moon_tex(Nw=1024):
    Nh = Nw // 2
    n1 = _noise((Nh, Nw), 2.6, 61); n2 = _noise((Nh, Nw), 1.4, 62)
    alb = 0.42 + 0.05 * n2 - 0.16 * np.clip(n1 * 0.9 + 0.2, 0, 1)
    return np.clip(np.stack([alb, alb * 0.98, alb * 0.94], -1), 0, 1)


def neptune_tex(Nw=1024):
    Nh = Nw // 2
    n1 = _hn((Nh, Nw), 2.6, 71, aniso=8.0); lat = np.linspace(90, -90, Nh, dtype=np.float32)[:, None]
    v = 1 + 0.06 * n1 + 0.05 * np.sin(np.radians(lat * 7))
    return np.clip(np.array([0.22, 0.40, 0.86], np.float32) * v[..., None], 0, 1)


def ring_profile(n=4096):
    """optical depth and colour vs radius (in Saturn equatorial radii, 1.0 .. 2.4). Main features only + fine structure."""
    r = np.linspace(1.0, 2.4, n, dtype=np.float32); tau = np.zeros(n, np.float32)
    rg = np.random.default_rng(77)
    fine = sum(np.interp(r, np.linspace(1, 2.4, m), rg.standard_normal(m)) * a for m, a in ((40, 0.35), (160, 0.3), (700, 0.25), (2400, 0.2)))
    def band(a, b, t): return np.where((r >= a) & (r < b), t, 0)
    tau += band(1.110, 1.236, 0.004)                                       # D (barely there)
    tau += band(1.239, 1.527, 0.10) * (1 + 0.45 * fine).clip(0.2, 3)       # C
    tau += band(1.527, 1.951, 1.6) * (1 + 0.5 * fine).clip(0.35, 3) * np.interp(r, [1.527, 1.64, 1.75, 1.951], [0.6, 0.75, 1.3, 1.4])   # B
    tau += band(1.951, 2.027, 0.10) * (1 + 0.5 * fine).clip(0.1, 3)        # Cassini division
    tau += band(2.027, 2.269, 0.55) * (1 + 0.3 * fine).clip(0.4, 2)        # A
    tau *= 1 - np.exp(-((r - 2.214) / 0.0035) ** 2)                        # Encke gap
    tau *= 1 - np.exp(-((r - 2.263) / 0.0015) ** 2)                        # Keeler gap
    tau += 0.08 * np.exp(-((r - 2.326) / 0.0025) ** 2)                     # F ring
    col = np.stack([np.interp(r, [1.2, 1.5, 1.6, 1.95, 2.03, 2.27], c) for c in ([0.52, 0.56, 0.86, 0.90, 0.80, 0.78], [0.46, 0.50, 0.76, 0.80, 0.74, 0.72],
                                                                                 [0.40, 0.42, 0.58, 0.64, 0.64, 0.64])], -1).astype(np.float32)
    col *= (1 + 0.06 * fine)[:, None]
    return r, tau, col


# ------------------------------------------------------------------------------------------------ renderer
def render_planet(size, R, tex, light, axis=(0, 1, 0), lon0=0.0, q=1.0, centre=None, rings=None, atmo=None, limb=0.75,
                  shade=None, ss_=2, ambient=0.004, term=0.06):
    """size=(w,h) px; R planet equatorial radius in px; light = direction TO the sun (view space); axis = spin axis (view space);
    q = polar/equatorial radius ratio. rings = dict(profile=(r,tau,col), gain=..). atmo = (rgb, thickness_px, strength).
    Returns premultiplied linear rgb and alpha (supersampled ss_ x)."""
    w, h = size; S = ss_; cw, ch = (centre if centre else (w / 2, h / 2))
    if w * h * S * S > 3.0e6 and h > 64:                                    # render in strips to bound memory
        nstrip = int(math.ceil(w * h * S * S / 2.5e6)); hs = int(math.ceil(h / nstrip)); outs = []
        for y0 in range(0, h, hs):
            outs.append(render_planet((w, min(hs, h - y0)), R, tex, light, axis=axis, lon0=lon0, q=q, centre=(cw, ch - y0), rings=rings,
                                      atmo=atmo, limb=limb, shade=shade, ss_=ss_, ambient=ambient, term=term))
        return np.concatenate([o[0] for o in outs], 0), np.concatenate([o[1] for o in outs], 0)
    xs = ((np.arange(w * S, dtype=np.float32) + 0.5) / S - cw) / R; ys = -((np.arange(h * S, dtype=np.float32) + 0.5) / S - ch) / R
    X, Y = np.meshgrid(xs, ys)
    a = nrm(axis); e1 = nrm(np.cross([0.0, 1.0, 0.03], a) if abs(a[1]) < 0.999 else [1.0, 0, 0]); e1 = nrm(np.cross(a, np.cross(e1, a))); e2 = np.cross(a, e1)
    L = nrm(light)
    # planet frame, scaled so the ellipsoid is a unit sphere: p = (o.e1, o.e2, o.a / q)
    o1 = X * e1[0] + Y * e1[1]; o2 = X * e2[0] + Y * e2[1]; o3 = (X * a[0] + Y * a[1]) / q
    d = np.array([-e1[2], -e2[2], -a[2] / q])                                # view direction (0,0,-1) in the planet frame
    Ls = np.array([L @ e1, L @ e2, (L @ a) / q])
    dd = d @ d; bq = o1 * d[0] + o2 * d[1] + o3 * d[2]; cq = o1 * o1 + o2 * o2 + o3 * o3 - 1
    disc = bq * bq - dd * cq; hit = disc > 0
    tt = (-bq - np.sqrt(np.maximum(disc, 0))) / dd
    h1 = o1 + tt * d[0]; h2 = o2 + tt * d[1]; h3 = o3 + tt * d[2]
    n_true = np.stack([h1[..., None] * e1 + h2[..., None] * e2 + (h3 / q)[..., None] * a][0:1], 0)[0]
    n_true /= np.linalg.norm(n_true, axis=-1, keepdims=True) + 1e-9
    ndl = n_true @ L; mu = np.clip(n_true[..., 2], 0, 1)
    lat = np.arcsin(np.clip(h3, -1, 1)); lon = np.arctan2(h1, h2) + lon0
    rgb = np.zeros((h * S, w * S, 3), np.float32); alpha = np.zeros((h * S, w * S), np.float32)
    m = hit
    lit = np.clip((ndl[m] + term) / (1 + term), 0, 1) ** 0.9 * np.clip((ndl[m] + term) / (2.5 * term), 0, 1)
    if shade is not None:
        surf = shade(lat[m], lon[m], ndl[m], n_true[m], lit)
    else:
        surf = samp(tex, lat[m], lon[m]) * (lit * (limb + (1 - limb) * mu[m] ** 0.6))[:, None]
    # ring shadow on the globe
    if rings is not None:
        rr_, tau_, col_ = rings["profile"]
        s_ = np.where(np.abs(Ls[2]) > 1e-5, -h3[m] / Ls[2], -1)
        px_ = h1[m] + s_ * Ls[0]; py_ = h2[m] + s_ * Ls[1]; rad = np.hypot(px_, py_)
        tr = np.exp(-np.interp(rad, rr_, tau_, left=0, right=0) / max(abs(float(Ls[2] * q)), 0.08) * 0.8)
        surf *= np.where(s_ > 0, tr, 1.0)[:, None]
    surf += ambient * samp(tex, lat[m], lon[m]) if shade is None else 0
    if atmo is not None:
        acol, athick, astr = atmo
        fres = (1 - mu[m]) ** 3.0
        surf += np.asarray(acol, np.float32) * (fres * np.clip(ndl[m] + 0.3, 0, 1) * astr)[:, None]
    rgb[m] = surf; alpha[m] = 1.0
    if atmo is not None:                                                     # outer halo (thin limb glow on the lit side)
        acol, athick, astr = atmo
        rr2 = np.sqrt(np.maximum(cq + 1, 0))                                 # approx distance from centre in radii (spherical approx)
        rpix = np.sqrt(X * X + (Y) ** 2)
        dirl = np.clip(((X * L[0] + Y * L[1]) / np.maximum(rpix, 1e-3)) * 0.65 + 0.5, 0, 1)
        edge = np.maximum(-disc / (dd + 1e-9), 0)                            # ~ (impact^2 - 1)
        halo = np.where(~hit, np.exp(-np.sqrt(edge) * R / (athick * 2.2)) * 0.0 + np.exp(-edge * R / athick * 0.5), 0) * dirl * astr * 0.8
        rgb += halo[..., None] * np.asarray(acol, np.float32) * (~hit)[..., None]
        alpha = np.maximum(alpha, np.clip(halo * 0.6, 0, 1) * (~hit))
    if rings is not None:
        rr_, tau_, col_ = rings["profile"]; gain = rings.get("gain", 1.0)
        tpl = np.where(np.abs(d[2]) > 1e-6, -o3 / d[2], -1e9)                # ray parameter at the ring plane
        p1 = o1 + tpl * d[0]; p2 = o2 + tpl * d[1]; rad = np.hypot(p1, p2)
        infront = (~hit) | (tpl < tt)
        tau = np.interp(rad, rr_, tau_, left=0, right=0)
        mu_v = max(abs(float(a[2])), 0.05); mu_s = max(abs(float(L @ a)), 0.05)
        a_r = 1 - np.exp(-tau / mu_v)
        same_side = (a[2] * (L @ a)) > 0
        refl = (1 - np.exp(-tau * (1 / mu_v + 1 / mu_s))) * mu_s / (mu_s + mu_v) if same_side else np.exp(-tau / mu_s) * (1 - np.exp(-tau / mu_v)) * 0.6
        # planet shadow on the rings
        bs = p1 * Ls[0] + p2 * Ls[1]; cs = p1 * p1 + p2 * p2 - 1; ds = bs * bs - (Ls @ Ls) * cs
        sh = (ds > 0) & (bs < 0)
        soft = np.clip(1 - np.clip(ds, 0, None) / 0.004, 0, 1)
        refl = refl * np.where(sh, soft * 0.9 + 0.02, 1.0)
        cr = np.stack([np.interp(rad, rr_, col_[:, c]) for c in range(3)], -1) * (refl * gain * 1.9)[..., None]
        a_r = np.where(infront, a_r, 0.0)
        rgb = rgb * (1 - a_r)[..., None] + cr * (a_r > 0)[..., None] * infront[..., None]
        alpha = alpha * (1 - a_r) + a_r
    if S > 1:
        rgb = rgb.reshape(h, S, w, S, 3).mean(axis=(1, 3)); alpha = alpha.reshape(h, S, w, S).mean(axis=(1, 3))
    return rgb.astype(np.float32), alpha.astype(np.float32)


_EARTH = {}
def earth_shader(lon_shift_clouds=0.0):
    if not _EARTH:
        def tex(p, mode="RGB"): return np.asarray(Image.open(p).convert(mode), np.float32) / 255
        _EARTH["day"] = tex(GLOBE + "/img/earth-blue-marble.jpg") ** 2.2
        _EARTH["night"] = tex(GLOBE + "/img/earth-night.jpg")
        _EARTH["water"] = tex(GLOBE + "/img/earth-water.png", "L")
        _EARTH["cloud"] = np.asarray(Image.open(GLOBE + "/clouds/clouds.png").convert("RGBA"), np.float32)[..., 3] / 255
    E = _EARTH

    def shade(lat, lon, ndl, n, lit):
        day = samp(E["day"], lat, lon); wat = samp(E["water"], lat, lon); cl = np.clip(samp(E["cloud"], lat, lon + lon_shift_clouds) * 1.05, 0, 1)
        ngt = samp(E["night"], lat, lon)
        surf = day * 1.25 * lit[:, None]
        Lh = shade.half; ndh = np.clip(n @ Lh, 0, 1)
        surf += np.array([1.0, 0.92, 0.8], np.float32) * (wat * (ndh ** 400 * 0.22 + ndh ** 40 * 0.04) * lit)[:, None]
        # cloud shadows (cheap: darken by clouds sampled slightly towards the sun) + clouds
        surf *= (1 - 0.35 * np.clip(samp(E["cloud"], lat, lon + lon_shift_clouds + 0.006), 0, 1))[:, None]
        surf = surf * (1 - cl[:, None] * 0.93) + (cl * lit)[:, None] * np.array([0.95, 0.96, 1.0], np.float32)
        surf += np.array([0.9, 0.35, 0.12], np.float32) * (np.exp(-((ndl - 0.02) / 0.05) ** 2) * 0.012)[:, None]      # terminator warmth
        dark = np.clip((-ndl + 0.02) / 0.2, 0, 1)
        surf += np.array([1.0, 0.7, 0.35], np.float32) * (np.clip(ngt.mean(1) - 0.05, 0, 1) * dark * (1 - cl * 0.7) * 0.5)[:, None]
        return surf
    return shade


if __name__ == "__main__":
    import sys, time
    from lib import SCR, tonemap, to8, bloom
    which = sys.argv[1:] or ["jupiter", "saturn", "earth", "io"]
    for wname in which:
        t0 = time.time()
        if wname == "jupiter":
            tex = cached("jupiter", jupiter_tex)
            rgb, al = render_planet((1920, 1080), 700, tex, (-0.75, 0.25, 0.6), axis=(0.12, 0.99, 0.08), lon0=math.radians(-150), q=0.935, limb=0.55,
                                    atmo=((0.9, 0.75, 0.55), 6, 0.10), centre=(1150, 600))
        elif wname == "saturn":
            tex = cached("saturn", saturn_tex)
            rgb, al = render_planet((1920, 1080), 300, tex, (-0.7, 0.32, 0.63), axis=nrm((0.22, 0.86, 0.46)), q=0.902, limb=0.55,
                                    rings=dict(profile=ring_profile()), atmo=((0.9, 0.8, 0.6), 4, 0.08))
        elif wname == "earth":
            sh = earth_shader(); L = nrm((-0.6, 0.35, 0.72)); sh.half = nrm(L + np.array([0, 0, 1.0]))
            rgb, al = render_planet((1920, 1080), 480, None, L, axis=nrm((0.2, 0.93, 0.3)), lon0=math.radians(-80 - 90), shade=sh,
                                    atmo=((0.30, 0.55, 1.0), 9, 1.3))
        elif wname == "io":
            tex = cached("io", io_tex)
            rgb, al = render_planet((1920, 1080), 400, tex, (-0.7, 0.2, 0.68), limb=0.8)
        print(wname, time.time() - t0)
        Image.fromarray(to8(tonemap(bloom(rgb, 0.3, 10), 1.6))).save(os.path.join(SCR, "chk", f"pl_{wname}.png"))
