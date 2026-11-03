"""
CH2 "FALLING" - texture generator (numpy only, run once).

Writes 16-bit sRGB PNGs to the shared texture cache with a "ch2_" prefix:
  ch2_mw.png       4096^2  face-on barred spiral (the Milky Way, seen from outside)
  ch2_m31.png      4096^2  face-on Andromeda (tight arms + 10 kpc star-forming ring)
  ch2_m33.png      1024^2  Triangulum (flocculent, blue)
  ch2_lmc.png      1024^2  Large Magellanic Cloud (offset bar, irregular)
  ch2_space.png    4096^2  TILEABLE deep-space star field (intergalactic: sparse stars + far galaxies)
  ch2_plate.png    3840x2160  stylised 1912 glass-plate negative of M31 (sepia, scratches, dust)
  ch2_spec.png     4096x256   continuum spectrum strip (colour x vertical profile)
  ch2_specgrey.png 4096x256   same strip as it would sit on a plate (sepia, monochrome)
  ch2_lines.png    4096x8     absorption-line transmission mask (sampled with a moving offset)

Usage:  /home/user/bpyenv/bin/python gen_textures.py [outdir]
"""
import os
import sys
import zlib
import struct
import time
import numpy as np

OUT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else \
    "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures"
os.makedirs(OUT, exist_ok=True)
F32 = np.float32


# ---------------------------------------------------------------- io
def to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def write_png16(path, img):
    """img float HxWx3 (linear 0..1) -> 16-bit sRGB PNG (Blender decodes sRGB by default)."""
    h, w = img.shape[:2]
    a = (to_srgb(img) * 65535.0 + 0.5).astype(">u2")
    raw = np.zeros((h, 1 + w * 6), dtype=np.uint8)
    raw[:, 1:] = a.reshape(h, w * 3).view(np.uint8)
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw.tobytes(), 6)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote", path, img.shape, f"max={img.max():.3f}", flush=True)


# ---------------------------------------------------------------- helpers
def blur(img, sigma):
    """periodic gaussian blur via FFT (2D or HxWxC)."""
    if sigma <= 0:
        return img
    h, w = img.shape[:2]
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (kx * kx + ky * ky)).astype(F32)
    if img.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(img) * g, s=(h, w)).astype(F32)
    return np.stack([blur(img[..., c], sigma) for c in range(img.shape[2])], -1)


def fnoise(n, beta, rng, kmin=1.0, w=None):
    """power-law (fBm-like) periodic noise, normalised to mean 0 std 1."""
    w = w or n
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.rfftfreq(w)[None, :] * w
    k = np.sqrt(kx * kx + ky * ky)
    amp = np.where(k < kmin, 0.0, (k + 1e-9) ** (-beta / 2))
    ph = rng.standard_normal((n, w // 2 + 1)) + 1j * rng.standard_normal((n, w // 2 + 1))
    f = np.fft.irfft2(ph * amp, s=(n, w)).astype(F32)
    f -= f.mean()
    f /= f.std() + 1e-9
    return f


def sstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def splat(shape, ys, xs, vals, wrap=False):
    img = np.zeros(shape, F32)
    h, w = shape
    yi = np.floor(ys).astype(int)
    xi = np.floor(xs).astype(int)
    fy = (ys - yi).astype(F32)
    fx = (xs - xi).astype(F32)
    for dy, wy in ((0, 1 - fy), (1, fy)):
        for dx, wx in ((0, 1 - fx), (1, fx)):
            yy, xx = yi + dy, xi + dx
            if wrap:
                yy %= h
                xx %= w
                ok = np.ones_like(yy, bool)
            else:
                ok = (yy >= 0) & (yy < h) & (xx >= 0) & (xx < w)
            np.add.at(img, (yy[ok], xx[ok]), (vals * wy * wx)[ok])
    return img


def sample_density(dens, n, rng):
    """draw n pixel positions with probability proportional to dens."""
    p = dens.ravel().astype(np.float64)
    p = np.maximum(p, 0)
    p /= p.sum()
    idx = rng.choice(p.size, size=n, p=p)
    ys, xs = np.divmod(idx, dens.shape[1])
    return ys + rng.random(n), xs + rng.random(n)


def col(c):
    return np.array(c, F32)[None, None, :]


# ---------------------------------------------------------------- spiral galaxy
def spiral(N, seed, *, arms, pitch, r0, r_end, arm_w, bar=None, ring=None, ring2=None,
           bulge_r=0.05, bulge_amp=1.0, disk_h=0.16, n_young=40000, n_hii=5000, n_old=60000,
           dust=1.0, edge=0.92, young_col=(0.60, 0.74, 1.0), old_col=(1.0, 0.84, 0.64),
           bulge_col=(1.0, 0.78, 0.52), gain=1.0, arm_amp=0.40):
    rng = np.random.default_rng(seed)
    t0 = time.time()
    ax = (np.arange(N, dtype=F32) + 0.5) / N * 2 - 1
    x, y = np.meshgrid(ax, -ax)
    r = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)
    lnr = np.log(np.maximum(r, 1e-3) / r0)
    k = 1.0 / np.tan(np.radians(pitch))
    big = fnoise(N, 4.0, rng, 1)
    big2 = fnoise(N, 3.6, rng, 2)
    mid = fnoise(N, 2.6, rng, 4)
    fine = fnoise(N, 2.3, rng, 12)
    taper = 1 - sstep(r, edge * 0.70, edge)
    armsum = np.zeros((N, N), F32)
    lane = np.zeros((N, N), F32)
    for (phi0, amp) in arms:
        ths = phi0 + lnr * k + 0.16 * big + 0.07 * big2
        d = (th - ths + np.pi) % (2 * np.pi) - np.pi
        w = arm_w * (0.7 + 1.1 * r)
        dist = d * r
        on = sstep(r, r0 * 0.8, r0 * 1.4) * (1 - sstep(r, r_end * 0.6, r_end))
        prof = np.exp(-(dist / w) ** 2) + 0.35 * np.exp(-(dist / (w * 2.6)) ** 2)
        armsum += amp * prof * on
        # dust lane hugs the inner (concave) edge of each arm
        dl = dist + 0.85 * w + 0.25 * w * mid
        lane += amp * np.exp(-(dl / (w * 0.65)) ** 2) * on
        # feathers/spurs: short dusty filaments leaving the arm at a steep angle
        sp = (th - (phi0 + lnr * k * 0.35) * 1.0) * 9.0
        spur = (0.5 + 0.5 * np.cos(sp + 3 * big2)) ** 8 * np.exp(-((dist - 1.8 * w) / (1.6 * w)) ** 2)
        lane += 0.45 * amp * spur * on
    if ring is not None:
        rr, rw, ra = ring
        rmod = rr + 0.015 * big + 0.008 * big2
        armsum += ra * (np.exp(-((r - rmod) / rw) ** 2) + 0.3 * np.exp(-((r - rmod) / (rw * 2.5)) ** 2))
        lane += 0.9 * ra * np.exp(-((r - rmod + rw * 0.9) / (rw * 0.45)) ** 2)
    if ring2 is not None:
        rr, rw, ra = ring2
        rmod = rr + 0.025 * big
        armsum += ra * np.exp(-((r - rmod) / rw) ** 2)
        lane += 0.5 * ra * np.exp(-((r - rmod + rw * 0.7) / (rw * 0.45)) ** 2)
    # break arms into star-forming complexes
    seg = sstep(big2 * 0.8 + mid * 0.6, -1.0, 1.0)
    clump = (0.12 + 0.88 * seg ** 1.5) * (0.55 + 0.45 * sstep(fine, -1.2, 1.2))
    armc = armsum * clump
    disk = np.exp(-r / disk_h) * taper
    bulge = bulge_amp * (np.exp(-(r / bulge_r) ** 0.85) + 0.18 * np.exp(-r / (bulge_r * 3.5)))
    if bar is not None:
        ang, L, q, amp = bar
        ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        xb = x * ca + y * sa
        yb = -x * sa + y * ca
        bulge += amp * np.exp(-((xb / L) ** 2 + (yb / (L * q)) ** 2) ** 1.2)
        # dust lanes along the leading edges of the bar
        for s in (1, -1):
            lane += 0.25 * np.exp(-(((yb - s * L * q * 0.9 - s * 0.15 * xb) / 0.012) ** 2)) * \
                np.exp(-(xb / L) ** 2) * sstep(np.abs(xb), 0.03, 0.08)
    # ----- smooth light
    old = disk * (0.75 + 0.25 * sstep(mid, -1.5, 1.5)) * (0.65 + 0.9 * armsum)
    young = armc * np.exp(-r / (disk_h * 2.6)) * taper * arm_amp
    img = col(old_col) * old[..., None] * 0.9 + col(young_col) * young[..., None]
    img += col(bulge_col) * bulge[..., None]
    halo = 0.012 * np.exp(-r / 0.30) * (1 - sstep(r, 0.6, 1.0))
    img += col((0.78, 0.74, 0.88)) * halo[..., None]
    # ----- point sources
    sc = N / 4096.0
    dens = disk + 2 * bulge * (r > 0.03)
    ys, xs = sample_density(dens, n_old, rng)
    v = (rng.pareto(2.5, n_old) + 1) * 0.05
    pts = splat((N, N), ys, xs, v.astype(F32))
    img += col((1.0, 0.86, 0.70)) * blur(pts, 0.8 * sc)[..., None]
    dens = (armc ** 1.6) * taper * (r > r0 * 0.7)
    ys, xs = sample_density(dens, n_young, rng)
    v = (rng.pareto(1.7, n_young) + 1) * 0.45
    pts = splat((N, N), ys, xs, v.astype(F32))
    img += col((0.66, 0.78, 1.0)) * (blur(pts, 0.85 * sc) + 0.25 * blur(pts, 2.5 * sc))[..., None]
    dens = (armc ** 2.4) * taper
    ys, xs = sample_density(dens + 1e-9, n_hii, rng)
    v = (rng.pareto(1.5, n_hii) + 1) * 0.5
    pts = splat((N, N), ys, xs, v.astype(F32))
    img += col((1.0, 0.36, 0.58)) * (blur(pts, 1.2 * sc) + 0.35 * blur(pts, 3.5 * sc))[..., None]
    # ----- dust: lanes + flocculent filaments, patchy
    dmask = lane * (0.08 + 0.92 * sstep(mid + 0.8 * big2 + 0.4 * fine, -0.6, 1.2))
    dmask += 0.35 * sstep(fine + 0.6 * mid, 0.9, 2.2) * sstep(r, 0.08, 0.2) * taper
    dmask *= sstep(r, 0.03, 0.10) * (1 - sstep(r, edge * 0.65, edge * 0.95))
    tau = dust * 2.2 * dmask
    att = np.stack([np.exp(-tau * 0.70), np.exp(-tau * 0.88), np.exp(-tau * 1.15)], -1)
    img *= att
    img = blur(img, 0.55 * sc) * gain
    img = 1 - np.exp(-img * 1.6)
    img *= (1 - sstep(r, edge * 0.90, edge * 1.06))[..., None]
    print(f"  spiral seed {seed} {time.time() - t0:.1f}s", flush=True)
    return img.astype(F32), r


def irregular(N, seed, kind):
    rng = np.random.default_rng(seed)
    ax = (np.arange(N, dtype=F32) + 0.5) / N * 2 - 1
    x, y = np.meshgrid(ax, -ax)
    r = np.sqrt(x * x + y * y)
    big = fnoise(N, 3.2, rng, 2)
    mid = fnoise(N, 2.2, rng, 3)
    if kind == "lmc":
        xb = x * 0.94 + y * 0.34 + 0.12
        yb = -x * 0.34 + y * 0.94 + 0.05
        bar = np.exp(-((xb / 0.30) ** 2 + (yb / 0.09) ** 2))
        body = np.exp(-(r / 0.30) ** 1.2) * (0.6 + 0.4 * sstep(big, -1, 1.2))
        lum = 0.9 * bar + 0.55 * body
        sf = sstep(mid + 0.6 * big, 0.7, 2.0) * np.exp(-r / 0.4)
        # 30 Doradus: one bright pink knot near the bar end
        sf += 1.4 * np.exp(-(((x - 0.24) ** 2 + (y - 0.14) ** 2) / 0.003))
        img = col((0.85, 0.85, 0.95)) * lum[..., None] + col((1.0, 0.45, 0.65)) * blur(sf.astype(F32), 4) [..., None] * 0.25
        n = 9000
    else:  # m33: flocculent spiral
        th = np.arctan2(y, x)
        ths = np.log(np.maximum(r, 1e-3) / 0.08) * 2.3 + 0.35 * big
        d = (th - ths + np.pi) % np.pi - np.pi / 2
        arm = np.exp(-(d * r / (0.05 + 0.08 * r)) ** 2) * sstep(r, 0.05, 0.12)
        arm *= 0.4 + 0.6 * sstep(mid, -0.6, 1.3)
        disk = np.exp(-r / 0.22)
        lum = disk * (0.35 + 0.9 * arm) + 0.9 * np.exp(-(r / 0.03))
        sf = arm * sstep(mid, 0.2, 1.6) * disk * 3
        img = col((0.72, 0.80, 1.0)) * lum[..., None] + col((1.0, 0.45, 0.70)) * sf[..., None] * 0.5
        img += col((1.0, 0.85, 0.65)) * (0.6 * np.exp(-(r / 0.03)))[..., None]
        n = 12000
    dens = np.clip(img.mean(-1), 0, None) * (r < 0.8)
    ys, xs = sample_density(dens, n, rng)
    v = (rng.pareto(1.8, n) + 1) * 0.10
    pts = blur(splat((N, N), ys, xs, v.astype(F32)), 0.9)
    img += col((0.80, 0.86, 1.0)) * pts[..., None]
    img *= (1 - sstep(r, 0.55, 0.92))[..., None]
    img = 1 - np.exp(-blur(img, 0.6) * 1.1)
    return img.astype(F32)


# ---------------------------------------------------------------- deep space (tileable)
def space(N, seed):
    rng = np.random.default_rng(seed)
    img = np.zeros((N, N, 3), F32)
    # stars: power-law brightness, mostly faint
    n = 26000
    ys, xs = rng.random(n) * N, rng.random(n) * N
    b = (rng.pareto(1.35, n) + 1) * 0.020
    b = np.minimum(b, 3.0)
    tcol = rng.random(n)
    warm = np.array([1.0, 0.84, 0.68], F32)
    cool = np.array([0.72, 0.80, 1.0], F32)
    for lo, hi, sig in ((0, 0.08, 0.75), (0.08, 0.4, 0.95), (0.4, 99, 1.15)):
        m = (b >= lo) & (b < hi)
        for c in range(3):
            cv = (warm[c] * (1 - tcol[m]) + cool[c] * tcol[m]).astype(F32)
            img[..., c] += blur(splat((N, N), ys[m], xs[m], (b[m] * cv).astype(F32), wrap=True), sig)
    # soft halo on the brightest
    m = b > 0.35
    hal = blur(splat((N, N), ys[m], xs[m], b[m].astype(F32), wrap=True), 5.0) * 0.5
    img += col((0.80, 0.80, 1.0)) * hal[..., None]
    # distant galaxies: tiny tilted ellipses
    gal = np.zeros((N, N), F32)
    yy, xx = np.mgrid[-6:7, -6:7].astype(F32)
    for i in range(900):
        cy, cx = rng.integers(0, N, 2)
        a = rng.uniform(0.8, 3.2)
        q = rng.uniform(0.25, 1.0)
        pa = rng.uniform(0, np.pi)
        u = xx * np.cos(pa) + yy * np.sin(pa)
        v = -xx * np.sin(pa) + yy * np.cos(pa)
        s = np.exp(-((u / a) ** 2 + (v / (a * q)) ** 2)) * rng.uniform(0.01, 0.07) * (rng.random() ** 2 * 3 + 0.3)
        Y = (np.arange(cy - 6, cy + 7) % N)[:, None]
        X = (np.arange(cx - 6, cx + 7) % N)[None, :]
        gal[Y, X] += s
    img += col((1.0, 0.90, 0.78)) * gal[..., None]
    # extremely faint violet cosmic haze, so the black never looks digital
    hz = sstep(fnoise(N, 3.6, rng, 1), -0.5, 2.5)
    img += col((0.30, 0.26, 0.55)) * (hz * 0.006)[..., None]
    return np.clip(img, 0, 1)


# ---------------------------------------------------------------- 1912 plate
def plate(m31_face, W=3840, H=2160, seed=19):
    rng = np.random.default_rng(seed)
    N = m31_face.shape[0]
    lum_face = m31_face.mean(-1)
    # view the face-on disk at 77 deg inclination, PA ~ 38 deg in frame
    inc = np.radians(77.0)
    pa = np.radians(-32.0)
    ys = (np.arange(H, dtype=F32) - H / 2) / (H * 0.5)
    xs = (np.arange(W, dtype=F32) - W / 2) / (H * 0.5)
    X, Y = np.meshgrid(xs, -ys)
    cx, cy = 0.04, 0.0
    Xr = (X - cx) * np.cos(pa) + (Y - cy) * np.sin(pa)
    Yr = -(X - cx) * np.sin(pa) + (Y - cy) * np.cos(pa)
    scale = 1.05                      # disk radius (texture units) -> plate units
    u = Xr / scale
    v = Yr / (scale * np.cos(inc))
    inside = (np.abs(u) < 1) & (np.abs(v) < 1)
    iu = np.clip(((u + 1) / 2 * N).astype(int), 0, N - 1)
    iv = np.clip(((1 - v) / 2 * N).astype(int), 0, N - 1)
    lum = np.where(inside, lum_face[iv, iu], 0.0).astype(F32)
    # projected light piles up along the line of sight: compensate
    lum = lum / np.cos(inc) * 0.5
    # near-side dust looks darker on inclined disks
    lum *= np.where(Yr < 0, 1.0, 1.0)
    rr = np.sqrt(Xr ** 2 + Yr ** 2)
    lum += 2.2 * np.exp(-(rr / 0.035) ** 0.9) + 0.5 * np.exp(-rr / 0.12)    # round bulge
    # satellites: M32 (compact) and M110 (diffuse elliptical)
    def blob(px, py, a, q, ang, amp, n=1.0):
        ca, sa = np.cos(ang), np.sin(ang)
        uu = (X - px) * ca + (Y - py) * sa
        vv = -(X - px) * sa + (Y - py) * ca
        return amp * np.exp(-(np.sqrt((uu / a) ** 2 + (vv / (a * q)) ** 2)) ** n)
    lum += blob(cx + 0.06, cy - 0.17, 0.020, 0.8, 0.3, 1.2, 0.8)
    lum += blob(cx - 0.26, cy + 0.33, 0.085, 0.5, -0.45, 0.22, 2.0)
    lum = blur(lum, 2.6)
    # field stars (a photographic plate records many): dark dots with halation
    n = 7000
    sy_, sx_ = rng.random(n) * H, rng.random(n) * W
    sb = np.minimum((rng.pareto(1.15, n) + 1) * 0.6, 60)
    st = splat((H, W), sy_, sx_, sb.astype(F32))
    stars = blur(st, 1.5) + 0.25 * blur(st, 3.5) + 0.04 * blur(st, 9.0)
    expo = lum * 1.1 + stars
    # density of a negative, with fog, grain and uneven development
    rngn = fnoise(H, 3.0, rng, 1, w=W)
    grain = blur(rng.standard_normal((H, W)).astype(F32), 0.9)
    D = 0.16 + 1.55 * (1 - np.exp(-expo * 1.3)) + 0.04 * rngn + 0.06 * grain
    # scratches in the emulsion: let light straight through (bright on the negative)
    scr = np.zeros((H, W), F32)
    for i in range(26):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        ang = rng.uniform(0, np.pi) if i % 3 else rng.normal(1.45, 0.08)
        L = rng.uniform(150, 1600)
        curv = rng.normal(0, 0.0004)
        t = np.linspace(0, L, int(L * 1.5))
        px = x0 + t * np.cos(ang + curv * t)
        py = y0 + t * np.sin(ang + curv * t)
        a = rng.uniform(0.5, 1.4) * (0.4 + 0.6 * np.sin(t / rng.uniform(20, 120)) ** 2)
        scr += splat((H, W), py, px, a.astype(F32))
    scr = np.clip(blur(scr, 0.6), 0, 1)
    D = D * (1 - 0.85 * scr)
    # dust specks (dark) and pinholes (bright)
    for sign, cnt in ((1, 900), (-1, 260)):
        py, px = rng.random(cnt) * H, rng.random(cnt) * W
        a = (rng.pareto(1.5, cnt) + 1) * 0.25
        sp = blur(splat((H, W), py, px, a.astype(F32)), rng.uniform(0.7, 1.4))
        D = D + sign * np.clip(sp, 0, 1.2) * (0.8 if sign > 0 else 0.6)
    # a dried tide-line and gentle density fall-off at the corners
    tide = np.exp(-((np.sqrt(((X + 1.25) / 1.1) ** 2 + ((Y + 0.9) / 0.8) ** 2) - 0.9) / 0.006) ** 2)
    D += 0.03 * tide * (0.5 + 0.5 * sstep(rngn, -1, 1))
    T = np.power(10.0, -np.clip(D, 0, 3)).astype(F32)
    # backlight: warm, slightly uneven lightbox; corner falloff
    vig = 1 - 0.55 * sstep(np.sqrt((X / 1.85) ** 2 + (Y / 1.05) ** 2), 0.55, 1.2)
    light = vig * (0.92 + 0.08 * sstep(rngn, -1.5, 1.5))
    # emulsion edge: plate border with chipped emulsion
    ex = np.minimum(np.minimum(X + W / H, W / H - X), np.minimum(Y + 1, 1 - Y))
    chip = 0.012 * fnoise(H, 2.0, rng, 4, w=W)
    edge = sstep(ex + chip, 0.035, 0.05)
    out = (light * (edge * T + (1 - edge) * 0.86))
    out *= sstep(ex, 0.0, 0.012)    # glass edge -> black lightbox mask
    sepia = col((1.0, 0.80, 0.55))
    paper = out[..., None]
    img = sepia * paper ** 1.1 * 0.95 + col((0.06, 0.04, 0.02)) * paper
    return np.clip(img * 0.92, 0, 1).astype(F32)


# ---------------------------------------------------------------- spectrum
LAM0, LAM1 = 380.0, 700.0
LINES = [  # (nm, depth, width nm) integrated old-population absorption features
    (393.37, 0.82, 1.2), (396.85, 0.78, 1.2), (410.17, 0.35, 0.9), (430.8, 0.45, 1.2),
    (434.05, 0.30, 0.8), (438.4, 0.18, 0.6), (486.13, 0.32, 0.9), (517.3, 0.40, 1.4),
    (527.0, 0.20, 0.8), (589.3, 0.45, 1.1), (656.28, 0.30, 1.0),
]


def wl_rgb(l):
    """approximate visible wavelength -> linear rgb, gently desaturated."""
    r = np.interp(l, [380, 410, 440, 490, 510, 580, 645, 700], [0.35, 0.45, 0.0, 0.0, 0.0, 1.0, 1.0, 0.55])
    g = np.interp(l, [380, 440, 490, 510, 580, 645, 700], [0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0])
    b = np.interp(l, [380, 410, 440, 490, 510, 700], [0.45, 0.8, 1.0, 1.0, 0.0, 0.0])
    c = np.stack([r, g, b], -1)
    c = c * 0.42 + 0.58 * c.mean(-1, keepdims=True)
    return c ** 2.0 * 0.62


def spectrum(W=4096, H=256, seed=5):
    rng = np.random.default_rng(seed)
    lam = LAM0 + (np.arange(W) + 0.5) / W * (LAM1 - LAM0)
    cont = 0.55 + 0.45 * sstep(lam, 385, 520) - 0.15 * sstep(lam, 600, 700)    # old stars: weak in the blue
    ends = sstep(lam, LAM0, 400) * (1 - sstep(lam, 670, LAM1))
    rgb = wl_rgb(lam) * (cont * (0.25 + 0.75 * ends))[:, None]
    v = (np.arange(H) + 0.5) / H * 2 - 1
    prof = np.exp(-(np.abs(v) / 0.55) ** 8)
    streak = 1 + 0.05 * blur(rng.standard_normal((H, W)).astype(F32), 1.2)
    img = rgb[None, :, :] * prof[:, None, None] * streak[..., None]
    grey = img.mean(-1, keepdims=True) * 1.5
    plate_grey = col((1.0, 0.80, 0.55)) * grey
    tm = np.ones(W, F32)
    for l0, dpt, w in LINES:
        tm *= 1 - min(0.95, dpt * 1.15) * np.exp(-((lam - l0) / (w * 1.6)) ** 2)
    lines = np.repeat(tm[None, :], 8, 0)
    return np.clip(img * 1.4, 0, 1), np.clip(plate_grey, 0, 1), np.repeat(lines[..., None], 3, -1)


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    def want(k):
        return only is None or k in only
    T = time.time()
    m31 = None
    if want("mw"):
        mw, _ = spiral(4096, 11, arms=[(0.0, 1.0), (np.pi, 1.0), (np.pi / 2, 0.55), (3 * np.pi / 2, 0.55)],
                       pitch=13.0, r0=0.20, r_end=0.95, arm_w=0.042, bar=(28.0, 0.21, 0.36, 0.55),
                       bulge_r=0.035, bulge_amp=1.0, disk_h=0.17, dust=1.0, gain=1.0)
        write_png16(os.path.join(OUT, "ch2_mw.png"), mw)
    if want("m31") or want("plate"):
        m31, _ = spiral(4096, 31, arms=[(0.4, 1.0), (0.4 + np.pi, 0.9)], pitch=9.0, r0=0.24, r_end=0.95,
                        arm_w=0.030, ring=(0.46, 0.032, 0.95), ring2=(0.68, 0.045, 0.40),
                        bulge_r=0.045, bulge_amp=1.4, disk_h=0.19, dust=1.3, n_young=40000,
                        young_col=(0.64, 0.76, 1.0), gain=1.0)
        if want("m31"):
            write_png16(os.path.join(OUT, "ch2_m31.png"), m31)
    if want("m33"):
        write_png16(os.path.join(OUT, "ch2_m33.png"), irregular(1024, 33, "m33"))
    if want("lmc"):
        write_png16(os.path.join(OUT, "ch2_lmc.png"), irregular(1024, 50, "lmc"))
    if want("space"):
        write_png16(os.path.join(OUT, "ch2_space.png"), space(4096, 7))
    if want("plate"):
        write_png16(os.path.join(OUT, "ch2_plate.png"), plate(m31))
    if want("spec"):
        sp, gr, ln = spectrum()
        write_png16(os.path.join(OUT, "ch2_spec.png"), sp)
        write_png16(os.path.join(OUT, "ch2_specgrey.png"), gr)
        write_png16(os.path.join(OUT, "ch2_lines.png"), ln)
    print(f"done {time.time() - T:.1f}s")
