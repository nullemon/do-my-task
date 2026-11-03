"""
CH3 "THE SKY CHANGES" - texture generator (numpy only, run once).

Writes 8-bit PNGs to the shared texture cache (prefix ch3_):
  ch3_m31_L0..L4.png  Andromeda, pre-inclined (~72 deg), 8192x3072 -> 512x192 LODs
  ch3_stars.png       alt-az star field, 26 px/deg (yaw -180..180, pitch -20..90)
  ch3_mw.png          Milky Way band in galactic (l,b) coordinates, 12 px/deg
  ch3_meta.json       encoding constants + Milky Way orientation (read by script.py)

All maps store sRGB(L / Lmax) (dithered 8-bit); Blender loads them as sRGB (free decode)
and the shader multiplies by Lmax.
  ch3_atmo.png        512x2 LUT over sin(altitude): top row extinction, bottom row airglow*50

Run:  /home/user/bpyenv/bin/python gen_textures.py [--only m31|stars|mw] [--preview]
"""
import os
import sys
import json
import math
import time
import zlib
import struct

import numpy as np

OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures"
os.makedirs(OUT, exist_ok=True)
ARGS = sys.argv[1:]
ONLY = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
RNG = np.random.default_rng(31)

# ---------------------------------------------------------------------------
# Shared constants (script.py reads them back from ch3_meta.json)
# ---------------------------------------------------------------------------
M31_W, M31_H = 8192, 3072          # texture covers X in [-1,1], Y in [-0.375,0.375]
M31_COSI = 0.30                    # cos(inclination)  -> ~72.5 deg
M31_LMAX = 4.0
STAR_LMAX = 4.0
MW_LMAX = 0.8
STAR_PMIN, STAR_PMAX = -20.0, 90.0
MW_BMAX = 45.0


def sdir(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])


# Milky Way orientation in the alt-az frame of the ridge (yaw 0 = camera forward, +X = right).
# Galactic centre sits low on the left horizon; the band climbs up and over toward the zenith.
GC = sdir(-50.0, -3.0)
QB = sdir(-14.0, 78.0)
GZ = np.cross(GC, QB); GZ /= np.linalg.norm(GZ)
GX = GC / np.linalg.norm(GC)
GY = np.cross(GZ, GX)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def write_png(path, arr):
    """arr: HxWxC uint8 (row 0 = top). Minimal PNG writer (zlib)."""
    h, w, c = arr.shape
    ctype = {1: 0, 3: 2, 4: 6}[c]
    raw = np.zeros((h, 1 + w * c), np.uint8)
    raw[:, 1:] = arr.reshape(h, w * c)
    comp = zlib.compress(raw.tobytes(), 6)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0)))
        f.write(chunk(b"IDAT", comp))
        f.write(chunk(b"IEND", b""))


def srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0.0031308), 1 / 2.4) - 0.055)


def encode(L, lmax, rng=RNG):
    """8-bit sRGB of L/lmax (Blender decodes for free with the sRGB colourspace), dithered."""
    s = srgb(np.clip(L / lmax, 0.0, 1.0)).astype(np.float32)
    s = s * 255.0 + rng.random(s.shape, dtype=np.float32) - 0.5
    return np.clip(np.rint(s), 0, 255).astype(np.uint8)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def fft_field(shape, beta, kmin=1.0, kmax=None, seed=0):
    """Gaussian random field with power ~ k^-beta (periodic), unit std, float32."""
    rng = np.random.default_rng(seed)
    h, w = shape
    wn = rng.standard_normal(shape).astype(np.float32)
    F = np.fft.rfft2(wn)
    m = max(h, w)                                  # isotropic in pixel space
    ky = np.fft.fftfreq(h)[:, None] * m
    kx = np.fft.rfftfreq(w)[None, :] * m
    k = np.sqrt(kx * kx + ky * ky)
    k[0, 0] = 1.0
    amp = k ** (-beta / 2.0)
    amp[k < kmin] = 0.0
    if kmax is not None:
        amp *= np.exp(-(k / kmax) ** 2)
    F *= amp
    f = np.fft.irfft2(F, s=shape).astype(np.float32)
    f -= f.mean()
    f /= f.std() + 1e-9
    return f


def bilinear(field, u, v):
    """sample periodic field at fractional texel coords (u along axis1, v along axis0)."""
    h, w = field.shape
    u0 = np.floor(u).astype(np.int64); v0 = np.floor(v).astype(np.int64)
    fu = (u - u0).astype(np.float32); fv = (v - v0).astype(np.float32)
    u0 %= w; v0 %= h
    u1 = (u0 + 1) % w; v1 = (v0 + 1) % h
    a = field[v0, u0] * (1 - fu) + field[v0, u1] * fu
    b = field[v1, u0] * (1 - fu) + field[v1, u1] * fu
    return a * (1 - fv) + b * fv


def hash01(ix, iy, seed):
    h = (ix.astype(np.uint64) * np.uint64(374761393) + iy.astype(np.uint64) * np.uint64(668265263)
         + np.uint64(seed) * np.uint64(2246822519)) & np.uint64(0xFFFFFFFF)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
    h = h ^ (h >> np.uint64(16))
    return (h.astype(np.float64) / 4294967296.0).astype(np.float32)


def cell_points(X, Y, cell, seed, radius_px_rng, prob, jit=0.72):
    """Sparse round blobs: one candidate per square cell (in X,Y units).
    Returns (intensity 0..1, random value per blob) at each pixel. prob: array or float."""
    cx = np.floor(X / cell); cy = np.floor(Y / cell)
    ix = cx.astype(np.int64); iy = cy.astype(np.int64)
    rx = hash01(ix, iy, seed); ry = hash01(ix, iy, seed + 17)
    rk = hash01(ix, iy, seed + 33); rb = hash01(ix, iy, seed + 51)
    rr = hash01(ix, iy, seed + 71)
    rad = radius_px_rng[0] + (radius_px_rng[1] - radius_px_rng[0]) * rr ** 2
    px = (cx + 0.5 + (rx - 0.5) * jit) * cell
    py = (cy + 0.5 + (ry - 0.5) * jit) * cell
    d2 = ((X - px) ** 2 + (Y - py) ** 2) / (rad * rad)
    blob = np.exp(-d2) * (rk < prob)
    return blob.astype(np.float32), rb


def downsample2(a):
    h, w = a.shape[:2]
    return 0.25 * (a[0:h:2, 0:w:2] + a[1:h:2, 0:w:2] + a[0:h:2, 1:w:2] + a[1:h:2, 1:w:2])


# ---------------------------------------------------------------------------
# Andromeda
# ---------------------------------------------------------------------------
def gen_m31():
    t0 = time.time()
    N = 4096                                  # face-on fields cover x,y in [-1.1, 1.1]
    FS = 1.1
    print("m31: fields ...", flush=True)
    f_warp = fft_field((N, N), 3.2, 1.5, 40, seed=1)      # arm phase wobble
    f_clump = fft_field((N, N), 2.2, 4, 600, seed=2)      # star clouds along arms
    f_dust = fft_field((N, N), 2.4, 6, 260, seed=3)       # lane feathering (phase jitter)
    f_dust2 = fft_field((N, N), 2.6, 3, 200, seed=4)      # patchy dust
    f_sf = fft_field((N, N), 2.4, 3, 400, seed=5)         # star-forming intensity
    f_fine = fft_field((N, N), 1.8, 40, 1400, seed=6)     # fine stellar grain
    print(f"m31: fields done {time.time()-t0:.1f}s", flush=True)

    W, H = M31_W, M31_H
    L = np.zeros((H, W, 3), np.float32)
    CH = 256
    xs = (np.arange(W, dtype=np.float32) + 0.5) / W * 2.0 - 1.0
    ymax = 0.375
    for r0 in range(0, H, CH):
        rows = np.arange(r0, min(H, r0 + CH), dtype=np.float32)
        Yv = ymax - (rows + 0.5) / H * 2 * ymax            # row 0 = top (+Y)
        X, Y = np.meshgrid(xs, Yv)
        x = X
        y = Y / M31_COSI                                     # de-projected disk coords
        r = np.sqrt(x * x + y * y)
        th = np.arctan2(y, x)
        fu = (x / FS * 0.5 + 0.5) * N
        fv = (y / FS * 0.5 + 0.5) * N
        warp = bilinear(f_warp, fu, fv)
        clump = bilinear(f_clump, fu, fv)
        dn = bilinear(f_dust, fu, fv)
        dn2 = bilinear(f_dust2, fu, fv)
        sf = bilinear(f_sf, fu, fv)
        fine = bilinear(f_fine, fu, fv)

        lnr = np.log(r + 0.004)
        # tightly wound two-arm spiral (M31-like ~10 deg pitch) with wobble
        k = 2.0 / math.tan(math.radians(10.5))
        phase = 2.0 * th - k * lnr + warp * 1.25 + 0.6 * np.sin(3 * th + 1.3) * smoothstep(0.3, 0.9, r)
        arm = ((1 + np.cos(phase)) * 0.5) ** 3.5
        # the famous ~10 kpc "ring of fire" + a faint inner ring
        ring = np.exp(-((r - 0.56 - 0.025 * warp) / 0.055) ** 2) + 0.45 * np.exp(-((r - 0.26 - 0.015 * warp) / 0.035) ** 2)
        armenv = smoothstep(0.10, 0.30, r) * (1 - smoothstep(0.62, 0.96, r))
        armtot = np.clip(arm * 0.85 + ring * 0.75 * (0.55 + 0.45 * arm), 0, 1.4) * armenv
        armtot *= np.clip(0.55 + 0.45 * clump, 0.05, 1.6)     # break arms into segments

        # old stellar disk
        disk = np.exp(-r / 0.23) * (1 - smoothstep(0.55, 1.0, r)) + 0.10 * np.exp(-r / 0.36) * (1 - smoothstep(0.6, 1.0, r))
        cl = np.clip(1.0 + 0.12 * clump + 0.05 * fine, 0.4, 2.0)
        old = disk * cl * 0.55 * (0.35 + 0.65 * np.exp(-r / 0.30))
        young = armtot * (0.17 + 0.07 * np.clip(sf, -1, 2)) * (0.45 + 1.2 * np.exp(-r / 0.45)) * np.clip(1 + 0.18 * fine, 0.3, 2)

        # dust: lanes on the inner edge of arms + along the rings, filamentary
        dphase = phase + 0.95 + 0.55 * dn                                 # feathered, wispy lanes
        dlane = ((1 + np.cos(dphase)) * 0.5) ** 9
        rj = r + 0.012 * dn
        dring = np.exp(-((rj - 0.535 - 0.025 * warp) / 0.026) ** 2) + 0.6 * np.exp(-((rj - 0.245) / 0.02) ** 2)
        patchy = smoothstep(0.2, 1.6, dn2)
        denv = smoothstep(0.07, 0.18, r) * (1 - smoothstep(0.50, 0.86, r))
        tau = (2.3 * dlane + 1.7 * dring + 0.45 * patchy) * denv
        tau = tau * np.clip(0.55 + 0.45 * dn2 + 0.25 * dn, 0.1, 1.8)
        near = smoothstep(-0.05, 0.12, y)                                # +Y half is the near side
        tau_eff = tau * (0.75 + 0.55 * near)
        att_disk = np.exp(-np.minimum(tau_eff, 2.0) * 0.75)

        # projected (round-ish) bulge, not de-projected
        rb = np.sqrt(X * X + (Y / 0.60) ** 2)
        bulge = 7.0 * np.exp(-rb / 0.0045) + 2.4 * np.exp(-rb / 0.018) + 0.95 * np.exp(-rb / 0.06) + 0.22 * np.exp(-rb / 0.15)
        att_bulge = np.exp(-np.minimum(tau * near * 1.25, 2.2))                          # dust silhouetted against the bulge
        halo = 0.018 * np.exp(-np.sqrt(X * X + (Y / 0.45) ** 2) / 0.26) * (1 - smoothstep(0.18, 0.34, np.abs(Y))) * (1 - smoothstep(0.6, 0.92, np.abs(X)))

        # HII regions / OB associations (projected, round)
        armw = np.clip(armtot, 0, 1)
        p_knot = np.clip(armw * 1.2 * (0.5 + 0.5 * np.clip(sf, -1, 2)), 0, 0.95)
        k1, kr1 = cell_points(X, Y, 0.0034, 11, (0.00028, 0.0007), p_knot, jit=0.5)
        k2, kr2 = cell_points(X, Y, 0.0105, 23, (0.0006, 0.0019), p_knot * 0.8, jit=0.3)
        k3, _ = cell_points(X, Y, 0.0016, 37, (0.00016, 0.00032), np.clip(armw * 0.6 + disk * 0.25, 0, 0.7))
        att_k = np.exp(-np.minimum(tau_eff, 2.0) * 0.45)

        def col(c):
            return np.array(c, np.float32)[None, None, :]

        c_bulge = col((1.00, 0.80, 0.56))
        c_old = col((1.00, 0.91, 0.80))
        c_young = col((0.60, 0.74, 1.00))
        c_hii = col((1.00, 0.36, 0.52))
        c_ob = col((0.72, 0.84, 1.00))
        c_halo = col((0.70, 0.72, 0.95))

        # inner disk warmer, outer bluer
        warm = smoothstep(0.55, 0.05, r)[..., None]
        c_oldm = c_old * (0.6 + 0.4 * warm) + col((0.86, 0.88, 1.0)) * (0.4 - 0.4 * warm)
        out = (c_oldm * (old * att_disk)[..., None]
               + c_young * (young * att_disk)[..., None]
               + c_bulge * (bulge * att_bulge)[..., None]
               + c_halo * halo[..., None])
        hii = (k2 * (0.35 + 0.65 * kr2) * 0.33 + k1 * (0.3 + 0.7 * kr1) * 0.55) * att_k
        out += c_hii * hii[..., None] * (0.7 + 0.6 * armenv[..., None])
        out += c_ob * (k3 * 0.22 * att_k)[..., None]
        # soft pink nebular glow along the ring
        out += c_hii * (0.035 * ring * armenv * np.clip(0.4 + 0.6 * sf, 0, 2) * att_disk)[..., None]

        # satellites: M32 (compact, just below the core) and M110 (diffuse, outside the disk)
        d32 = np.sqrt((X - 0.055) ** 2 + ((Y + 0.165) / 0.85) ** 2)
        out += col((1.0, 0.85, 0.66)) * (1.6 * np.exp(-d32 / 0.0028) + 0.35 * np.exp(-d32 / 0.010))[..., None]
        ca, sa = math.cos(0.5), math.sin(0.5)
        dx, dy = X + 0.33, Y - 0.235
        u_ = dx * ca + dy * sa; v_ = -dx * sa + dy * ca
        d110 = np.sqrt(u_ ** 2 + (v_ / 0.5) ** 2)
        out += col((1.0, 0.88, 0.72)) * ((0.11 * np.exp(-(d110 / 0.03) ** 0.8) + 0.25 * np.exp(-d110 / 0.004)) * (1 - smoothstep(0.30, 0.355, Y)))[..., None]

        # fade to zero at the texture borders
        edge = (1 - smoothstep(0.93, 1.0, np.abs(X))) * (1 - smoothstep(0.34, 0.375, np.abs(Y)))
        out *= edge[..., None]
        L[r0:r0 + len(rows)] = out
        print(f"m31: rows {r0}/{H} {time.time()-t0:.1f}s", flush=True)

    del f_warp, f_clump, f_dust, f_dust2, f_sf, f_fine
    lev = L
    for i in range(5):
        write_png(os.path.join(OUT, f"ch3_m31_L{i}.png"), encode(lev, M31_LMAX))
        print(f"m31: L{i} {lev.shape[1]}x{lev.shape[0]}", flush=True)
        if i < 4:
            lev = downsample2(lev)
    print(f"m31 done {time.time()-t0:.1f}s")


# ---------------------------------------------------------------------------
# Stars (alt-az equirect)
# ---------------------------------------------------------------------------
def star_catalogue():
    rng = np.random.default_rng(7)
    n_target = 100000
    # sample uniform on the sphere above pitch -20, then thin by galactic latitude weighting
    n0 = n_target * 3
    z = rng.uniform(math.sin(math.radians(STAR_PMIN)), 1.0, n0)
    az = rng.uniform(-math.pi, math.pi, n0)
    cz = np.sqrt(1 - z * z)
    d = np.stack([np.sin(az) * cz, np.cos(az) * cz, z], 1)
    b = np.arcsin(np.clip(d @ GZ, -1, 1))
    w = (1 + 2.2 * np.exp(-np.abs(np.degrees(b)) / 12.0)) / 3.2
    keep = rng.random(n0) < w
    d = d[keep][:n_target]
    n = len(d)
    # magnitudes: N(<m) ~ 10^(0.45 m), m in [-0.5, 6.8]
    u = rng.random(n)
    a = 0.45 * math.log(10)
    m0, m1 = -0.5, 6.8
    m = np.log(np.exp(a * m0) + u * (np.exp(a * m1) - np.exp(a * m0))) / a
    peak = 3.6 * 10 ** (-0.4 * (m - 0.0))
    # colours
    t = rng.random(n)
    pal = np.array([(0.70, 0.80, 1.00), (0.86, 0.90, 1.00), (1.00, 1.00, 1.00), (1.00, 0.93, 0.82), (1.00, 0.80, 0.60)], np.float32)
    idx = np.searchsorted(np.array([0.12, 0.35, 0.65, 0.88]), t)
    col = pal[idx] * (0.9 + 0.2 * rng.random((n, 1)))
    yaw = np.degrees(np.arctan2(d[:, 0], d[:, 1]))
    pitch = np.degrees(np.arcsin(np.clip(d[:, 2], -1, 1)))
    # ultra-faint dust of stars
    nf = 260000
    z = rng.uniform(math.sin(math.radians(STAR_PMIN)), 1.0, nf)
    az = rng.uniform(-math.pi, math.pi, nf)
    cz = np.sqrt(1 - z * z)
    df = np.stack([np.sin(az) * cz, np.cos(az) * cz, z], 1)
    bf = np.arcsin(np.clip(df @ GZ, -1, 1))
    kf = rng.random(nf) < (0.25 + 0.75 * np.exp(-np.abs(np.degrees(bf)) / 9.0))
    df = df[kf]
    yawf = np.degrees(np.arctan2(df[:, 0], df[:, 1]))
    pitchf = np.degrees(np.arcsin(np.clip(df[:, 2], -1, 1)))
    peakf = 0.006 + 0.012 * rng.random(len(df)) ** 2
    colf = pal[rng.integers(1, 4, len(df))]
    return (np.concatenate([yaw, yawf]), np.concatenate([pitch, pitchf]),
            np.concatenate([peak, peakf]), np.concatenate([col, colf]))


def gen_stars(ppd, name, flux_scale):
    t0 = time.time()
    yaw, pitch, peak, col = star_catalogue()
    W = int(round(360 * ppd))
    H = int(round((STAR_PMAX - STAR_PMIN) * ppd))
    img = np.zeros((H * W, 3), np.float32)
    up = (yaw + 180.0) * ppd
    vp = (STAR_PMAX - pitch) * ppd
    cosp = np.maximum(np.cos(np.radians(pitch)), 0.06)
    peak = peak * flux_scale

    def splat(sel, sig, amp):
        if not np.any(sel):
            return
        su = sig / cosp[sel]
        kv = int(math.ceil(sig * 3.2))
        u = up[sel]; v = vp[sel]; a = amp[sel]; c = col[sel]
        # group by u half-width to keep kernels small
        kus = np.ceil(su * 3.2).astype(int)
        for ku in np.unique(kus):
            g = kus == ku
            ug, vg, ag, cg, sg = u[g], v[g], a[g], c[g], su[g]
            ui0 = np.floor(ug).astype(np.int64); vi0 = np.floor(vg).astype(np.int64)
            for dv in range(-kv, kv + 1):
                vi = vi0 + dv
                wv = np.exp(-0.5 * ((vi + 0.5 - vg) / sig) ** 2)
                okv = (vi >= 0) & (vi < H)
                for du in range(-ku, ku + 1):
                    ui = (ui0 + du) % W
                    w = wv * np.exp(-0.5 * ((ui0 + du + 0.5 - ug) / sg) ** 2) * ag
                    ok = okv & (w > 1e-5)
                    if not np.any(ok):
                        continue
                    flat = vi[ok] * W + ui[ok]
                    for ch in range(3):
                        np.add.at(img[:, ch], flat, w[ok] * cg[ok, ch])

    allsel = pitch < 88.5
    splat(allsel, 0.62, peak)
    bright = allsel & (peak > 0.25)
    splat(bright, 2.2, peak * 0.035)
    vb = allsel & (peak > 0.9)
    splat(vb, 6.0, peak * 0.006)
    img = img.reshape(H, W, 3)
    write_png(os.path.join(OUT, name), encode(img, STAR_LMAX))
    print(f"stars {name} {W}x{H} {time.time()-t0:.1f}s", flush=True)


# ---------------------------------------------------------------------------
# Milky Way (galactic l,b)
# ---------------------------------------------------------------------------
def gen_mw():
    t0 = time.time()
    ppd = 20
    W, H = 360 * ppd, int(2 * MW_BMAX * ppd)
    l = (np.arange(W, dtype=np.float32) + 0.5) / ppd - 180.0
    b = MW_BMAX - (np.arange(H, dtype=np.float32) + 0.5) / ppd
    Lg, Bg = np.meshgrid(l, b)
    f1 = fft_field((H, W), 3.0, 12, 1400, seed=41)
    f2 = fft_field((H, W), 2.3, 32, 1300, seed=42)
    f3 = fft_field((H, W), 3.0, 4, 240, seed=43)
    f4 = fft_field((H, W), 1.6, 120, 4000, seed=44)
    h = 3.2 + 3.0 * np.exp(-(Lg / 35.0) ** 2)
    along = 0.30 + 0.85 * np.exp(-(Lg / 48.0) ** 2) + 0.22 * np.exp(-((np.abs(Lg) - 80) / 25.0) ** 2)
    disk = np.exp(-np.abs(Bg - 0.6 * f3) / h) * along
    clouds = np.clip(0.35 + 0.95 * smoothstep(-0.6, 1.8, f1) + 0.10 * f4, 0.1, 2.2)
    bulge = 1.5 * np.exp(-((Lg / 11.0) ** 2 + (Bg / 7.5) ** 2)) + 0.6 * np.exp(-((Lg / 4.0) ** 2 + (Bg / 3.0) ** 2))
    brift = 1.0 + 1.6 * f3
    fil = np.clip(1.0 - np.abs(f2) * 0.7, 0, 1) ** 2
    rift = 2.4 * np.exp(-((Bg - brift) / (1.5 + 0.7 * np.abs(f1))) ** 2) * (0.35 + 0.9 * fil) * np.exp(-(Lg / 75.0) ** 2 * 0.6)
    patch = 0.9 * smoothstep(0.0, 1.4, f1) * (0.5 + 0.5 * smoothstep(-0.5, 1.0, f2)) * np.exp(-np.abs(Bg) / 5.0)
    tau = rift + patch
    lum = (disk * clouds + bulge) * np.exp(-tau)
    lum *= 1 - smoothstep(MW_BMAX - 8, MW_BMAX, np.abs(Bg))
    warm = np.exp(-((Lg / 30.0) ** 2 + (Bg / 12.0) ** 2))[..., None]
    c_n = np.array((0.80, 0.83, 1.00), np.float32)[None, None]
    c_w = np.array((1.00, 0.84, 0.64), np.float32)[None, None]
    c = c_n * (1 - warm) + c_w * warm
    out = c * lum[..., None] * 0.16
    # unresolved-star grain: many tiny faint points following the band light
    rng = np.random.default_rng(45)
    n = 900000
    pu = rng.integers(0, W, n); pv = rng.integers(0, H, n)
    keep = rng.random(n) < np.clip(lum[pv, pu] / 1.2, 0, 1)
    pu, pv = pu[keep], pv[keep]
    amp = (0.02 + 0.10 * rng.random(len(pu)) ** 3).astype(np.float32)
    grain = np.zeros((H, W), np.float32)
    np.add.at(grain, (pv, pu), amp)
    out += np.array((0.85, 0.88, 1.0), np.float32)[None, None] * grain[..., None]
    # faint reddish emission nebulae along the plane
    neb = smoothstep(0.9, 2.2, f4 + 0.6 * f1) * np.exp(-np.abs(Bg) / 2.5) * 0.02
    out += np.array((1.0, 0.35, 0.5), np.float32)[None, None] * neb[..., None]
    # alpha = dust opacity of our own galaxy's plane (dims Andromeda where the band crosses it)
    opac = (1 - np.exp(-0.8 * tau)) * np.exp(-np.abs(Bg) / 6.0)
    a8 = np.clip(np.rint(opac * 255 + RNG.random(opac.shape) - 0.5), 0, 255).astype(np.uint8)
    write_png(os.path.join(OUT, "ch3_mw.png"), np.concatenate([encode(out, MW_LMAX), a8[..., None]], 2))
    print(f"mw {W}x{H} {time.time()-t0:.1f}s", flush=True)


def gen_atmo():
    """extinction (with reddening) and violet airglow as a function of sin(altitude)."""
    n = 512
    z = (np.arange(n) + 0.5) / n
    am = np.minimum(1.0 / (z + 0.045), 18.0)
    ext = np.stack([np.exp(-k * am) for k in (0.06, 0.10, 0.17)], 1)
    glow = (np.exp(-z / 0.13) * 0.010 + 0.0012)[:, None] * np.array([0.40, 0.36, 0.70])[None]
    img = np.stack([ext, glow * 50.0], 0).astype(np.float32)     # row 0 = top
    write_png(os.path.join(OUT, "ch3_atmo.png"), encode(img, 1.0, np.random.default_rng(1)))


def meta():
    m = dict(m31_w=M31_W, m31_h=M31_H, m31_cosi=M31_COSI, m31_lmax=M31_LMAX, star_lmax=STAR_LMAX,
             mw_lmax=MW_LMAX, star_pmin=STAR_PMIN, star_pmax=STAR_PMAX, mw_bmax=MW_BMAX,
             gx=GX.tolist(), gy=GY.tolist(), gz=GZ.tolist(), star_ppd=26)
    with open(os.path.join(OUT, "ch3_meta.json"), "w") as f:
        json.dump(m, f, indent=1)


if __name__ == "__main__":
    meta()
    if ONLY in (None, "mw"):
        gen_mw()
    if ONLY in (None, "stars"):
        gen_stars(26, "ch3_stars.png", 1.0)
    if ONLY in (None, "atmo"):
        gen_atmo()
    if ONLY in (None, "m31"):
        gen_m31()
