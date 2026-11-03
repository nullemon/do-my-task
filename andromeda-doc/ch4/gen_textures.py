"""
CH4 "MILKOMEDA" - texture generator (numpy only, no scipy/PIL).

Bakes every heavy sky element once into 8-bit sRGB PNGs so the Blender scene is
just one emission plane that samples these images (fast on CPU Cycles).

  /home/user/bpyenv/bin/python gen_textures.py [--only name,name] [--preview]

Textures (prefix ch4_), all "linear light" values encoded sRGB, 0..1:
  ch4_stars.png   screen-space star field, 720 px per screen half-height unit
  ch4_mw.png      Milky Way band seen from inside (dust rift, star clouds, bulge)
  ch4_m31.png     Andromeda face-on (the shader inclines / twists it)
  ch4_tails.png   two tidal tails (star streams with pink tidal-dwarf knots)
  ch4_burst.png   whole-sky starburst: H-alpha gas, knots, blue clusters; alpha = dust
  ch4_ell.png     Milkomeda: smooth Sersic n=4 elliptical with interleaved shells
"""
import os
import sys
import time
import zlib
import struct
import numpy as np

OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures"
F32 = np.float32


# ----------------------------------------------------------------------------- io
def srgb_enc(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def save_png(path, rgb, alpha=None, seed=0):
    """rgb: (H,W,3) linear 0..1, row 0 = top. Dithered 8-bit sRGB."""
    h, w, _ = rgb.shape
    rng = np.random.default_rng(seed + 991)
    chans = [rgb[..., i] for i in range(3)] + ([alpha] if alpha is not None else [])
    planes = []
    for i, c in enumerate(chans):
        e = srgb_enc(c) if i < 3 else np.clip(c, 0, 1)
        e = e * 255.0 + rng.random((h, w), dtype=F32) - 0.5      # TPDF-ish dither vs banding
        planes.append(np.clip(np.rint(e), 0, 255).astype(np.uint8))
    arr = np.stack(planes, -1)
    nch = arr.shape[2]
    raw = np.zeros((h, 1 + w * nch), np.uint8)
    raw[:, 1:] = arr.reshape(h, w * nch)
    data = zlib.compress(raw.tobytes(), 6)

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ct = 6 if nch == 4 else 2
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0)) \
        + chunk(b"IDAT", data) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print(f"  wrote {path} {w}x{h} {len(png) / 1e6:.1f} MB", flush=True)


# ----------------------------------------------------------------------------- maths
def sstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fnoise(h, w, beta=2.0, seed=0, kmin=2.0):
    """zero-mean unit-std noise with power spectrum ~ k^-beta (periodic)."""
    rng = np.random.default_rng(seed)
    wn = rng.standard_normal((h, w)).astype(F32)
    F = np.fft.rfft2(wn)
    fy = np.fft.fftfreq(h)[:, None] * h
    fx = np.fft.rfftfreq(w)[None, :] * w
    s = max(h, w)
    k = np.sqrt((fx * s / w) ** 2 + (fy * s / h) ** 2)
    amp = np.power(np.maximum(k, kmin), -beta / 2.0).astype(F32)
    amp[0, 0] = 0
    n = np.fft.irfft2(F * amp, s=(h, w)).astype(F32)
    n -= n.mean()
    n /= n.std() + 1e-9
    return n


def blur(img, sigma):
    """periodic gaussian blur via FFT; img (H,W) or (H,W,C)."""
    if sigma <= 0:
        return img
    if img.ndim == 3:
        return np.stack([blur(img[..., i], sigma) for i in range(img.shape[2])], -1)
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2)).astype(F32)
    return np.fft.irfft2(np.fft.rfft2(img) * g, s=(h, w)).astype(F32)


def bilinear(img, px, py):
    """sample img (H,W) at float pixel coords (periodic)."""
    h, w = img.shape
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx = (px - x0).astype(F32)
    fy = (py - y0).astype(F32)
    x0 %= w
    y0 %= h
    x1 = (x0 + 1) % w
    y1 = (y0 + 1) % h
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy)
            + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def upsample(img, h, w):
    sh, sw = img.shape
    py = (np.arange(h, dtype=F32) + 0.5) * sh / h - 0.5
    px = (np.arange(w, dtype=F32) + 0.5) * sw / w - 0.5
    PX, PY = np.meshgrid(px, py)
    return bilinear(img, PX, PY)


def deposit(h, w, px, py, wts):
    """bilinear deposit of point weights into an (H,W) image."""
    ok = (px >= 0) & (px < w - 1) & (py >= 0) & (py < h - 1)
    px, py, wts = px[ok], py[ok], wts[ok]
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx = px - x0
    fy = py - y0
    img = np.zeros(h * w, np.float64)
    for dx, dy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                       (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        img += np.bincount((y0 + dy) * w + (x0 + dx), weights=wts * ww, minlength=h * w)
    return img.reshape(h, w).astype(F32)


def splat_stars(h, w, px, py, flux, cols, sigma=0.8, halo=0.0, halo_sigma=4.0):
    """stars as gaussians: flux per star, cols (N,3). returns (H,W,3)."""
    out = np.zeros((h, w, 3), F32)
    for c in range(3):
        d = deposit(h, w, px, py, flux * cols[:, c])
        img = blur(d, sigma) if sigma > 0 else d
        if halo > 0:
            img = img + blur(d, halo_sigma) * halo
        out[..., c] = img
    return out


def star_colours(n, rng, warm=0.0):
    """random stellar colours (blue-white to orange), roughly a field mix."""
    t = rng.random(n)
    t = np.clip(t + warm, 0, 1)
    blue = np.array([0.70, 0.80, 1.00])
    white = np.array([1.00, 0.97, 0.94])
    orange = np.array([1.00, 0.76, 0.52])
    c = np.where(t[:, None] < 0.35, blue + (white - blue) * (t[:, None] / 0.35),
                 white + (orange - white) * ((t[:, None] - 0.35) / 0.65))
    return c.astype(F32)


def pareto_flux(n, rng, alpha=1.35, fmin=1.0, fmax=400.0):
    u = rng.random(n)
    f = fmin * np.power(1 - u, -1.0 / alpha)
    return np.minimum(f, fmax).astype(F32)


def grid(h, w, x0, x1, y0, y1):
    """pixel-centre coordinates; row 0 = top (y1)."""
    xs = x0 + (np.arange(w, dtype=F32) + 0.5) * (x1 - x0) / w
    ys = y1 - (np.arange(h, dtype=F32) + 0.5) * (y1 - y0) / h
    return np.meshgrid(xs, ys)


def to_px(x, y, h, w, x0, x1, y0, y1):
    return (x - x0) / (x1 - x0) * w - 0.5, (y1 - y) / (y1 - y0) * h - 0.5


def fbm_up(h, w, base, beta, seed):
    """cheap large-scale noise: compute at /4 res and upsample."""
    n = fnoise(max(64, h // base), max(64, w // base), beta, seed)
    return upsample(n, h, w)


# ----------------------------------------------------------------------------- textures
def tex_stars():
    # covers x in [-2.4, 2.4], y in [-1.5, 1.966] screen half-height units, 720 px / unit
    W, H = 3456, 2496
    rng = np.random.default_rng(11)
    n = 52000
    px = rng.random(n) * W
    py = rng.random(n) * H
    flux = pareto_flux(n, rng, 1.25, 1.0, 900.0)
    cols = star_colours(n, rng)
    img = splat_stars(H, W, px, py, flux * 0.010, cols, sigma=0.85, halo=0.05, halo_sigma=3.0)
    # brightest stars: a soft glow so they read as stars, not dots
    br = flux > 150
    img += splat_stars(H, W, px[br], py[br], flux[br] * 0.00035, cols[br], sigma=7.0)
    # faint unresolved background
    hz = fbm_up(H, W, 8, 2.6, 3)
    img += (0.0016 * np.clip(hz * 0.5 + 0.6, 0, 2))[..., None] * np.array([0.7, 0.7, 0.9], F32)
    save_png(os.path.join(OUT, "ch4_stars.png"), img, seed=1)


def tex_mw():
    # band along x: x in [-4.8,4.8], y in [-1,1]; bulge (galactic centre) at x=0
    W, H = 6144, 1280
    X0, X1, Y0, Y1 = -4.8, 4.8, -1.0, 1.0
    X, Y = grid(H, W, X0, X1, Y0, Y1)
    rng = np.random.default_rng(21)
    n1 = fbm_up(H, W, 4, 2.2, 5)
    n2 = fnoise(H, W, 1.7, 6)
    yw = Y + 0.035 * fbm_up(H, W, 8, 3.0, 7)
    width = 0.13 + 0.05 * np.exp(-(X / 1.2) ** 2)
    band = np.exp(-(yw / width) ** 2) * (1.0 - sstep(np.abs(X), 3.6, 4.7))
    bulge = np.exp(-((X / 0.55) ** 2 + (yw / 0.20) ** 2))
    clouds = np.exp(0.55 * n1 + 0.25 * n2)
    lum = band * clouds * (0.35 + 0.9 * np.exp(-(X / 1.6) ** 2)) + bulge * 1.4
    # dust: the Great Rift + filaments
    dn = fbm_up(H, W, 2, 1.9, 8)
    rift = np.exp(-((yw - 0.012 + 0.02 * dn) / (0.035 + 0.02 * np.exp(-(X / 1.0) ** 2))) ** 2)
    fil = sstep(fnoise(H, W, 1.8, 9) + 0.6 * dn, 0.2, 1.4) * np.exp(-(yw / 0.22) ** 2)
    dust = np.clip(blur(rift * sstep(dn, -0.9, 0.4) * 0.9 + fil * 0.45, 3.0), 0, 0.92)
    trans = 1.0 - dust
    col = (lum[..., None] * np.array([0.78, 0.78, 0.98], F32) * (1 - bulge[..., None])
           + lum[..., None] * bulge[..., None] * np.array([1.0, 0.80, 0.56], F32))
    col *= trans[..., None]
    # resolved stars, density follows the band
    nst = 420000
    sx = rng.random(nst) * (X1 - X0) + X0
    sy = rng.standard_normal(nst) * 0.16
    keep = rng.random(nst) < (np.exp(-(sx / 2.4) ** 2) * 0.7 + 0.3)
    sx, sy = sx[keep], sy[keep]
    px, py = to_px(sx, sy, H, W, X0, X1, Y0, Y1)
    fl = pareto_flux(len(sx), rng, 1.5, 1.0, 120.0)
    tr = bilinear(trans, px, py)
    stars = splat_stars(H, W, px, py, fl * tr * 0.020, star_colours(len(sx), rng, 0.1), sigma=0.8)
    # a few pink emission nebulae along the plane
    nn = 70
    nx = rng.uniform(-3.5, 3.5, nn)
    ny = rng.standard_normal(nn) * 0.06
    px, py = to_px(nx, ny, H, W, X0, X1, Y0, Y1)
    neb = deposit(H, W, px, py, rng.uniform(0.5, 2.5, nn))
    neb = blur(neb, 5) * 9.0 + blur(neb, 14) * 4.0
    col += neb[..., None] * np.array([1.0, 0.30, 0.50], F32) * 0.6
    col = col * 0.30 + stars
    m = np.percentile(col[..., 1], 99.95)
    col /= max(m, 1e-6) * 1.05
    save_png(os.path.join(OUT, "ch4_mw.png"), col, seed=2)


def tex_m31():
    N = 4096
    X, Y = grid(N, N, -1, 1, -1, 1)
    r = np.sqrt(X * X + Y * Y) + 1e-5
    th = np.arctan2(Y, X)
    rng = np.random.default_rng(31)
    lo = fbm_up(N, N, 8, 3.2, 13)
    lo2 = fbm_up(N, N, 4, 2.6, 14)
    k = 2.0 / np.tan(np.radians(12.0))
    phase = 2 * th - k * np.log(r) + 0.9 * lo
    arm = np.power(0.5 + 0.5 * np.cos(phase), 3.0)
    armzone = sstep(r, 0.10, 0.26) * (1 - sstep(r, 0.80, 0.97))
    ring = 0.55 + 0.8 * np.exp(-((r - 0.55) / 0.15) ** 2)
    disk = np.exp(-r / 0.23) * (1 - sstep(r, 0.80, 1.0))
    outer = np.exp(-r / 0.40) * (1 - sstep(r, 0.85, 1.0)) * 0.10
    clump = np.exp(0.45 * fbm_up(N, N, 2, 2.4, 15))
    armlum = disk * (0.035 + arm * ring * armzone * 1.1 * clump) + outer * (0.5 + 0.5 * arm)
    armlum += disk * 0.5 * np.exp(-(r / 0.16) ** 2)          # smooth inner disk
    bulge = np.exp(-np.power(r / 0.010, 0.5) * 2.0) * 5.0 + np.exp(-(r / 0.085) ** 1.4) * 0.6
    # dust lanes on the inner edge of the arms: continuous, softly broken
    dl = np.power(0.5 + 0.5 * np.cos(phase + 0.75), 9.0)
    dn = sstep(0.7 * fnoise(N, N, 2.2, 16) + 0.9 * lo2, -0.9, 0.7)
    dust = dl * dn * sstep(r, 0.07, 0.20) * (1 - sstep(r, 0.66, 0.86)) * 0.90
    wisp = sstep(fnoise(N, N, 2.0, 17) * 0.8 + 0.5 * lo2, 0.7, 1.8) * sstep(r, 0.08, 0.25) * (1 - sstep(r, 0.5, 0.75))
    dust = np.clip(blur(dust + wisp * 0.45, 2.0), 0, 0.92)
    tr = 1.0 - dust
    blue = np.array([0.72, 0.80, 1.00], F32)
    warm = np.array([1.00, 0.84, 0.62], F32)
    mixw = sstep(r, 0.08, 0.40)[..., None]
    col = armlum[..., None] * (warm * (1 - mixw) + blue * mixw) + bulge[..., None] * warm
    col *= tr[..., None]
    col /= np.percentile(col[..., 1][(r > 0.15) & (r < 0.8)], 99.5) / 0.22
    sl = np.zeros_like(col)
    # star clouds / OB associations + HII knots, along the arms
    pts = 700000
    ux = rng.uniform(-0.92, 0.92, pts)
    uy = rng.uniform(-0.92, 0.92, pts)
    px, py = to_px(ux, uy, N, N, -1, 1, -1, 1)
    af = arm * ring * armzone * disk
    a = bilinear(af, px, py) / af.max()
    t = bilinear(tr, px, py)
    keep = rng.random(pts) < np.clip(a * 1.6, 0, 1) * 0.6
    nk = int(keep.sum())
    fl = pareto_flux(nk, rng, 1.5, 1.0, 80.0) * t[keep]
    sl += splat_stars(N, N, px[keep], py[keep], fl, star_colours(nk, rng, -0.2), 0.85)
    hii = keep & (rng.random(pts) < 0.025)
    d = deposit(N, N, px[hii], py[hii], (t[hii] * rng.uniform(0.3, 1.0, hii.sum())).astype(F32))
    hk = blur(d, 1.4) * 0.8 + blur(d, 4) * 1.6
    col += (hk / np.percentile(hk[hk > 1e-6], 99.5) * 0.35)[..., None] * np.array([1.0, 0.36, 0.58], F32)
    # smooth disk population (resolved grain)
    gp = 900000
    rr = np.abs(rng.standard_normal(gp) * 0.30)
    aa = rng.random(gp) * 2 * np.pi
    px, py = to_px(rr * np.cos(aa), rr * np.sin(aa), N, N, -1, 1, -1, 1)
    sl += splat_stars(N, N, px, py, pareto_flux(gp, rng, 2.0, 1.0, 20.0) * bilinear(tr, px, py) * 0.2,
                      star_colours(gp, rng, 0.25), 0.8)
    sl /= np.percentile(sl[..., 1][(r > 0.15) & (r < 0.8)], 99.9) / 0.4
    col += sl
    save_png(os.path.join(OUT, "ch4_m31.png"), col, seed=3)


def tex_tails():
    """two tidal tails leaving the merger in an S (Antennae-like). coords +-1. Mostly diffuse light."""
    N = 4096
    rng = np.random.default_rng(41)
    diffuse = np.zeros((N, N), F32)
    knots = np.zeros((N, N), F32)
    stars = np.zeros((N, N, 3), F32)
    cl = fnoise(512, 512, 2.0, 40)
    for side, a0, turn, r0, rmax in ((1, 0.15, 1.9, 0.12, 0.84), (-1, np.pi + 0.15, 1.7, 0.12, 0.78)):
        npnt = 1600000
        t = rng.random(npnt)
        ang = a0 + side * turn * (t + 0.35 * t * t)
        rad = r0 + rmax * t
        wid = 0.020 + 0.075 * t
        off = rng.standard_normal(npnt) * wid
        off2 = rng.standard_normal(npnt) * wid * 0.6
        x = (rad + off) * np.cos(ang) - off2 * np.sin(ang)
        y = ((rad + off) * np.sin(ang) + off2 * np.cos(ang)) * 0.8
        px, py = to_px(x, y, N, N, -1, 1, -1, 1)
        c = np.exp(0.8 * bilinear(cl, px / 6 + side * 100, py / 6))
        wts = c * sstep(t, 0.0, 0.25) * (1 - sstep(t, 0.5, 1.0) * 0.9)
        diffuse += deposit(N, N, px, py, wts.astype(F32))
        sel = rng.random(npnt) < 0.012
        ns = int(sel.sum())
        stars += splat_stars(N, N, px[sel], py[sel], pareto_flux(ns, rng, 1.6, 1, 40) * wts[sel],
                             star_colours(ns, rng, -0.1), 0.85)
        kn = (rng.random(npnt) < 0.0004 * c) & (t > 0.15)
        knots += deposit(N, N, px[kn], py[kn], rng.uniform(0.3, 1.0, kn.sum()).astype(F32))
    dif = blur(diffuse, 5.0) + blur(diffuse, 20) * 0.9 + blur(diffuse, 60) * 0.6
    dif /= np.percentile(dif, 99.9)
    col = dif[..., None] * np.array([0.74, 0.78, 1.0], F32) * 0.55
    stars /= np.percentile(stars[..., 1][stars[..., 1] > 0], 99.5) * 1.5
    col += stars * 0.15
    kk = blur(knots, 1.8) + blur(knots, 6) * 0.8
    kk /= max(np.percentile(kk[kk > 1e-6], 99.8), 1e-6)
    col += kk[..., None] * np.array([1.0, 0.34, 0.56], F32) * 0.5
    save_png(os.path.join(OUT, "ch4_tails.png"), col, seed=4)


def spiral_band(dx, dy, r, th, r0, phi0, tanp, w, r_in, r_out, lo):
    """log-spiral arc segment: 1 on the arm ridge. returns (band, signed offset)."""
    lr = np.log(np.maximum(r, 1e-3) / r0)
    ph = th - phi0 - lr / tanp + 0.35 * lo
    ph = np.angle(np.exp(1j * ph))                     # wrap to -pi..pi
    off = ph * r * np.sin(np.arctan(tanp))             # ~perpendicular distance
    band = np.exp(-(off / w) ** 2)
    band *= sstep(r, r_in * 0.7, r_in) * (1 - sstep(r, r_out * 0.75, r_out))
    return band, off


def tex_burst():
    """whole-sky starburst. x in [-2.6, 2.6], y in [-1.625, 1.625]; swirl centre (0, 0.25).
    Arcs of starlight with pink H-alpha complexes strung along them like beads, blue young
    clusters, dark dust lanes on their inner edges. RGB = light, A = dust opacity."""
    W, H = 4096, 2560
    X0, X1, Y0, Y1 = -2.6, 2.6, -1.625, 1.625
    X, Y = grid(H, W, X0, X1, Y0, Y1)
    rng = np.random.default_rng(51)
    cx, cy = 0.0, 0.25
    lo = fbm_up(H, W, 8, 3.0, 52)
    lo2 = fbm_up(H, W, 8, 3.0, 53)
    dx = X - cx + 0.06 * lo2
    dy = (Y - cy) / 0.75 + 0.06 * lo
    r = np.sqrt(dx * dx + dy * dy) + 1e-4
    th = np.arctan2(dy, dx)
    arcs = [  # r0, phi0, tan(pitch), width, r_in, r_out, weight
        (0.5, 0.0, 0.30, 0.10, 0.15, 2.6, 1.0),
        (0.5, np.pi, 0.30, 0.10, 0.15, 2.4, 1.0),
        (0.9, 1.9, 0.24, 0.07, 0.45, 2.0, 0.7),
        (0.8, -1.3, 0.22, 0.06, 0.40, 1.7, 0.6),
        (1.3, 2.9, 0.35, 0.09, 0.8, 2.8, 0.55),
    ]
    light = np.zeros_like(X)
    ridge = np.zeros_like(X)
    dust = np.zeros_like(X)
    for r0, p0, tp, w, ri, ro, wt in arcs:
        b, off = spiral_band(dx, dy, r, th, r0, p0, tp, 0.65 * w * (1 + 0.6 * r), ri, ro, lo)
        light += b * wt
        ridge += np.power(b, 3.0) * wt
        bd, _ = spiral_band(dx, dy, r, th, r0, p0 - 0.22, tp, w * 0.35 * (1 + 0.5 * r), ri, ro * 0.8, lo)
        dust += bd * wt
    core_glow = np.exp(-(r / 0.35) ** 2) * 0.25
    env = 1 - sstep(np.maximum(np.abs(X) / 2.6, np.abs(Y) / 1.625), 0.82, 1.0)
    clump = np.exp(0.6 * fnoise(H, W, 2.2, 54) + 0.3 * fnoise(H, W, 1.6, 55))
    light = (light * clump + core_glow) * env
    ridge *= env
    dfil = sstep(fnoise(H, W, 2.0, 56) + 0.6 * lo, -0.8, 0.9)
    dust = np.clip(blur(dust * dfil, 1.5) * 0.85, 0, 0.88) * env
    trans = 1 - dust
    col = blur(light, 3)[..., None] * np.array([0.80, 0.80, 0.95], F32) * 0.045
    col += blur(light, 40)[..., None] * np.array([1.0, 0.45, 0.65], F32) * 0.05
    gasd = blur(ridge * clump, 6)
    col += (gasd / np.percentile(gasd, 99.7))[..., None] * np.array([1.0, 0.24, 0.46], F32) * 0.16
    # H-alpha complexes: hierarchical clusters along the arc ridges
    ncand = 60000
    cxs = rng.uniform(X0, X1, ncand)
    cys = rng.uniform(Y0, Y1, ncand)
    cpx, cpy = to_px(cxs, cys, H, W, X0, X1, Y0, Y1)
    pr = bilinear(ridge * clump, cpx, cpy)
    pr /= np.percentile(pr, 99.9)
    ok = rng.random(ncand) < np.clip(pr, 0, 1) ** 1.3 * 0.8
    cxs, cys = cxs[ok], cys[ok]
    nc = len(cxs)
    nb = rng.integers(2, 22, nc)
    spread = np.repeat(rng.uniform(0.006, 0.04, nc), nb)
    bx = np.repeat(cxs, nb) + rng.standard_normal(nb.sum()) * spread
    by = np.repeat(cys, nb) + rng.standard_normal(nb.sum()) * spread
    bpx, bpy = to_px(bx, by, H, W, X0, X1, Y0, Y1)
    bw = pareto_flux(len(bx), rng, 1.3, 1.0, 60.0) * bilinear(trans, bpx, bpy)
    kd = deposit(H, W, bpx, bpy, bw.astype(F32))
    knot = blur(kd, 1.1) * 1.0 + blur(kd, 2.8) * 1.6 + blur(kd, 7) * 2.0 + blur(kd, 20) * 2.5
    knot /= np.percentile(knot[knot > 1e-6], 99.6)
    ha = np.array([1.0, 0.24, 0.46], F32)
    col += knot[..., None] * ha * 0.8
    core = blur(kd, 0.8)
    col += (core / max(np.percentile(core[core > 1e-6], 99.6), 1e-6))[..., None] * np.array([1.0, 0.88, 0.95], F32) * 0.35
    # young blue clusters near the complexes
    nbl = len(bx) // 2
    ix = rng.integers(0, len(bx), nbl)
    sx = bx[ix] + rng.standard_normal(nbl) * 0.04
    sy = by[ix] + rng.standard_normal(nbl) * 0.04
    spx, spy = to_px(sx, sy, H, W, X0, X1, Y0, Y1)
    col += splat_stars(H, W, spx, spy, pareto_flux(nbl, rng, 1.3, 1.0, 200.0) * 0.010, star_colours(nbl, rng, -0.35),
                       0.85, halo=0.08, halo_sigma=4.0)
    # resolved stars of the two disks along the arcs
    nf = 500000
    fx = rng.uniform(X0, X1, nf)
    fy = rng.uniform(Y0, Y1, nf)
    fpx, fpy = to_px(fx, fy, H, W, X0, X1, Y0, Y1)
    lm = bilinear(light, fpx, fpy)
    keep = rng.random(nf) < np.clip(lm / np.percentile(light, 99.5), 0, 1)
    col += splat_stars(H, W, fpx[keep], fpy[keep], pareto_flux(int(keep.sum()), rng, 1.8, 1.0, 30.0) * 0.006,
                       star_colours(int(keep.sum()), rng, 0.1), 0.8)
    col *= (0.12 + 0.88 * trans)[..., None]
    save_png(os.path.join(OUT, "ch4_burst.png"), col, alpha=dust, seed=5)


def tex_ell():
    N = 4096
    X, Y = grid(N, N, -1, 1, -1, 1)
    r = np.sqrt(X * X + Y * Y) + 1e-5
    th = np.arctan2(Y, X)
    rng = np.random.default_rng(61)
    re = 0.20
    ser = np.exp(-7.67 * (np.power(r / re, 0.25) - 1))           # Sersic n=4, 1 at r=re
    base = ser / 12.7                                            # 1.0 at r ~ 0.04
    # faint interleaved shells (radial-merger signature): sharp outer edge, soft inside
    sh = np.zeros_like(r)
    for rk, side, wd, amp in ((0.30, 0.0, 0.75, 1.0), (0.37, np.pi + 0.2, 0.8, 0.9), (0.46, 0.35, 0.7, 0.8),
                              (0.56, np.pi - 0.25, 0.65, 0.7), (0.67, 0.15, 0.6, 0.55), (0.79, np.pi + 0.4, 0.55, 0.4)):
        dth = np.angle(np.exp(1j * (th - side)))
        ang = np.exp(-(dth / wd) ** 2)
        inner = np.where(r < rk, np.exp(-(rk - r) / 0.06), 0.0) * (1 - sstep(r, rk - 0.002, rk + 0.012))
        sh += inner * ang * amp
    plume = fbm_up(N, N, 8, 3.0, 62)
    lum = base * (1 + 0.10 * sh * np.exp(0.3 * plume)) + 0.0002 * sh
    lum *= 1 - sstep(r, 0.45, 0.97)
    lum *= (1 + 0.04 * fnoise(N, N, 1.4, 63))
    mixc = sstep(r, 0.0, 0.6)[..., None]
    warm = np.array([1.0, 0.86, 0.68], F32)
    cool = np.array([0.82, 0.80, 0.98], F32)
    col = lum[..., None] * (warm * (1 - mixc) + cool * mixc)
    # globular clusters / bright halo giants
    ng = 7000
    rr = np.abs(rng.standard_normal(ng)) * 0.30 + 0.03
    aa = rng.random(ng) * 2 * np.pi
    px, py = to_px(rr * np.cos(aa), rr * np.sin(aa), N, N, -1, 1, -1, 1)
    col += splat_stars(N, N, px, py, pareto_flux(ng, rng, 1.5, 1, 30) * 0.0020, star_colours(ng, rng, 0.2), 0.9)
    col = np.minimum(col, 1.0)
    save_png(os.path.join(OUT, "ch4_ell.png"), col, seed=6)


ALL = dict(stars=tex_stars, mw=tex_mw, m31=tex_m31, tails=tex_tails, burst=tex_burst, ell=tex_ell)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    names = list(ALL)
    if "--only" in args:
        names = args[args.index("--only") + 1].split(",")
    for nme in names:
        t0 = time.time()
        print("texture", nme, flush=True)
        ALL[nme]()
        print(f"  {time.time() - t0:.1f}s", flush=True)
