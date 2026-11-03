"""
ANDROMEDA documentary - CH1 "THE SMUDGE" : texture + catalogue generator (numpy only).

Writes (prefix ch1_) into the shared texture cache:
  ch1_meta.json        sky geometry (observer, world<-equatorial matrix, plane definitions)
  ch1_stars.npz        star catalogue (world directions, magnitudes, colours) for the geometry star layer
  ch1_mw.png           Milky Way + unresolved-star glow, gnomonic plane covering the wide shot
  ch1_m31_hi.png       detailed M31 (+ M32, M110), 4096 px over 4.2 deg, gnomonic plane centred on M31
  ch1_m31_mid.png      2x box-downsampled
  ch1_m31_lo.png       4x box-downsampled ("long-exposure" smudge for the wide/medium shots)
  ch1_m31_eye.png      what the naked eye sees: only the faint core
  ch1_ring.png         anti-aliased ring (full-Moon outline overlay)

Run:  /home/user/bpyenv/bin/python gen_textures.py [--out DIR] [--preview DIR]
The sky is the real sky: lat 40 N, local sidereal time 19.0 h (a late-September evening ~21:00),
camera facing azimuth 46 deg (north-east). Bright stars are real (Yale BSC values, rounded); fainter
stars are random but follow realistic number counts and Milky Way density.
"""
import os
import sys
import json
import time
import zlib
import struct
import math
import numpy as np

OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures"
PREVIEW = None
if "--out" in sys.argv:
    OUT = sys.argv[sys.argv.index("--out") + 1]
if "--preview" in sys.argv:
    PREVIEW = sys.argv[sys.argv.index("--preview") + 1]
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
os.makedirs(OUT, exist_ok=True)

D2R = math.pi / 180.0
LAT = 40.0
LST = 19.0          # hours
AZ0 = 46.0          # world +Y points to this azimuth
RNG = np.random.default_rng(31)


# ---------------------------------------------------------------------------
# PNG IO (no PIL in the bpy env)
# ---------------------------------------------------------------------------
def write_png(path, img, bits=8):
    """img: float array HxWx3 in display (sRGB-encoded) 0..1."""
    img = np.clip(img, 0.0, 1.0)
    h, w, c = img.shape
    if bits == 16:
        a = (img * 65535.0 + 0.5).astype(">u2")
    else:
        # ordered-ish dither (random) to kill banding in the dark gradients
        a = np.clip(img * 255.0 + RNG.uniform(-0.5, 0.5, img.shape), 0, 255).round().astype(np.uint8)
    raw = np.zeros((h, w * c * (bits // 8) + 1), np.uint8)
    raw[:, 1:] = a.reshape(h, -1).view(np.uint8)
    data = zlib.compress(raw.tobytes(), 6)

    def chunk(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    ctype = 2 if c == 3 else 6
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, bits, ctype, 0, 0, 0))
    png += chunk(b"IDAT", data) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def srgb(x):
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def box_down(img, k):
    h, w = img.shape[:2]
    h2, w2 = h // k, w // k
    img = img[:h2 * k, :w2 * k]
    return img.reshape(h2, k, w2, k, -1).mean(axis=(1, 3))


def preview(name, lin, k):
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        write_png(os.path.join(PREVIEW, name), srgb(box_down(lin, k)))


def blur(img, sigma):
    """Gaussian blur via FFT (periodic edges, fine for padded black borders)."""
    if sigma <= 0:
        return img
    h, w = img.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (fx * fx + fy * fy)).astype(np.float32)
    if img.ndim == 2:
        return np.fft.irfft2(np.fft.rfft2(img) * g, s=(h, w)).astype(np.float32)
    return np.stack([np.fft.irfft2(np.fft.rfft2(img[..., i]) * g, s=(h, w)) for i in range(img.shape[2])], -1).astype(np.float32)


# ---------------------------------------------------------------------------
# Sky geometry
# ---------------------------------------------------------------------------
def altaz(ra_h, dec):
    H = (LST - np.asarray(ra_h)) * 15 * D2R
    de = np.asarray(dec) * D2R
    la = LAT * D2R
    alt = np.arcsin(np.sin(de) * np.sin(la) + np.cos(de) * np.cos(la) * np.cos(H))
    az = np.arctan2(-np.cos(de) * np.sin(H), np.sin(de) * np.cos(la) - np.cos(de) * np.sin(la) * np.cos(H))
    return alt, az


def world_from_altaz(alt, az):
    d = az - AZ0 * D2R
    return np.stack([np.sin(d) * np.cos(alt), np.cos(d) * np.cos(alt), np.sin(alt)], -1)


def world_from_radec(ra_h, dec):
    return world_from_altaz(*altaz(ra_h, dec))


# world <- equatorial (rotation, built from the basis vectors)
W_EQ = np.stack([world_from_radec(0.0, 0.0), world_from_radec(6.0, 0.0), world_from_radec(0.0, 90.0)], -1)
EQ_W = W_EQ.T
GAL_EQ = np.array([[-0.0548755604, -0.8734370902, -0.4838350155],
                   [0.4941094279, -0.4448296300, 0.7469822445],
                   [-0.8676661490, -0.1980763734, 0.4559837762]])
GAL_W = GAL_EQ @ EQ_W


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def plane_basis(c, up_hint=np.array([0, 0, 1.0])):
    c = unit(np.asarray(c, float))
    u = unit(up_hint - np.dot(up_hint, c) * c)
    r = np.cross(c, u)            # camera-style: right = forward x up
    return c, r, u


def plane_dirs(c, r, u, tx, ty, W, H):
    xs = ((np.arange(W) + 0.5) / W * 2 - 1) * tx
    ys = (1 - (np.arange(H) + 0.5) / H * 2) * ty
    X, Y = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32))
    d = c[None, None, :] + X[..., None] * r[None, None, :] + Y[..., None] * u[None, None, :]
    return unit(d.astype(np.float32)), X, Y


M31_DIR = world_from_radec(0.71231, 41.2692)
M32_DIR = world_from_radec(0.71161, 40.8653)
M110_DIR = world_from_radec(0.67281, 41.6853)
NCP = world_from_radec(0.0, 90.0)


def sky_north_east(c):
    n = unit(NCP - np.dot(NCP, c) * c)
    e = np.cross(n, c)        # east is to the LEFT of north when looking out
    return n, e


# ---------------------------------------------------------------------------
# 3-D value noise on the sphere (so every texture agrees on the same sky)
# ---------------------------------------------------------------------------
def _hash3(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = h.astype(np.uint32)
    h ^= h >> 13
    h *= np.uint32(0x5bd1e995)
    h ^= h >> 15
    return (h & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF)


def vnoise3(p, seed=0):
    f = np.floor(p)
    t = p - f
    t = t * t * (3 - 2 * t)
    i = f.astype(np.int64)
    out = 0.0
    for dx in (0, 1):
        wx = t[..., 0] if dx else 1 - t[..., 0]
        for dy in (0, 1):
            wy = t[..., 1] if dy else 1 - t[..., 1]
            for dz in (0, 1):
                wz = t[..., 2] if dz else 1 - t[..., 2]
                out = out + wx * wy * wz * _hash3(i[..., 0] + dx, i[..., 1] + dy, i[..., 2] + dz, seed)
    return out


def _rot(seed):
    r = np.random.default_rng(1000 + seed)
    q, _ = np.linalg.qr(r.normal(size=(3, 3)))
    return q.astype(np.float32)


def fbm3(p, octaves=5, seed=0, lac=2.03, gain=0.52):
    v = 0.0
    a = 1.0
    norm = 0.0
    for o in range(octaves):
        # random rotation per octave hides the lattice of the value noise
        v = v + a * vnoise3((p @ _rot(seed * 31 + o)) * (lac ** o) + o * 17.13, seed + o)
        norm += a
        a *= gain
    return v / norm


# ---------------------------------------------------------------------------
# Milky Way model as a function of world direction
# ---------------------------------------------------------------------------
def gal_lb(dirs):
    g = dirs @ GAL_W.T
    l = np.arctan2(g[..., 1], g[..., 0])
    b = np.arcsin(np.clip(g[..., 2], -1, 1))
    return g, l, b


def mw_model(dirs):
    g, l, b = gal_lb(dirs)
    ld = np.degrees(l) % 360.0
    bd = np.degrees(b)
    # anisotropic coordinates: structures stretched along the galactic plane
    pa = np.stack([g[..., 0] * 1.0, g[..., 1] * 1.0, g[..., 2] * 1.7], -1)
    n1 = fbm3(pa * 5.0, 6, 3)
    n2 = fbm3(pa * 13.0 + 3.3, 6, 11)
    n3 = fbm3(pa * 30.0 + 7.7, 5, 21)
    warp = (fbm3(pa * 2.0 + 1.1, 3, 5) - 0.5) * 7.0
    base = 0.42 + 0.58 * np.exp(-((ld - 78.0) / 38.0) ** 2) + 0.10 * np.exp(-((ld - 125.0) / 20.0) ** 2)
    bw = 4.6 + 2.2 * n1
    bb = bd - warp * 0.45
    band = np.exp(-0.5 * (bb / bw) ** 2)
    broad = np.exp(-0.5 * (bd / 16.0) ** 2)
    clouds = np.clip((n1 - 0.38) * 2.2, 0, 1) ** 1.5 * 0.9 + np.clip((n2 - 0.45) * 2.5, 0, 1) * 0.5
    lum = base * (band * (0.30 + clouds) + 0.09 * broad)
    lum = lum * (0.75 + 0.5 * n3)
    # dust: dark lanes concentrated near the plane, filamentary
    dl = np.clip((n2 - 0.50) * 3.4, 0, 1) ** 1.2 * np.exp(-0.5 * (bb / (bw * 0.75)) ** 2)
    lane = np.exp(-0.5 * ((bb + 0.6) / 1.4) ** 2) * np.clip((n1 - 0.30) * 2.0, 0, 1)
    tau = 1.6 * dl + 1.1 * lane + 0.6 * np.clip((n3 - 0.55) * 3.0, 0, 1) * band
    trans = np.exp(-tau)
    warm = np.array([1.0, 0.86, 0.70], np.float32)
    cool = np.array([0.80, 0.86, 1.0], np.float32)
    mixw = np.clip(clouds * 0.9, 0, 1)[..., None]
    col = (warm * mixw + cool * (1 - mixw)) * (lum * trans)[..., None]
    # HII regions (faint red, as in long exposures): Heart & Soul, California, NGC 7000 area, IC 1396
    for l0, b0, s, a in ((134.7, 0.9, 1.6, 1.0), (137.2, 0.9, 1.3, 0.8), (160.6, -12.1, 2.0, 0.55),
                         (85.6, -0.9, 2.4, 1.0), (99.3, 3.7, 1.8, 0.7), (110.9, 0.1, 1.2, 0.4)):
        dl_ = ((ld - l0 + 180) % 360 - 180) * np.cos(np.radians(b0))
        r2 = (dl_ ** 2 + (bd - b0) ** 2) / s ** 2
        neb = a * np.exp(-0.5 * r2) * (0.4 + 0.9 * np.clip((n3 - 0.35) * 2.0, 0, 1))
        col = col + neb[..., None] * np.array([1.0, 0.30, 0.42], np.float32) * 0.035
    # atmospheric extinction toward the horizon
    alt = np.arcsin(np.clip(dirs[..., 2], -1, 1))
    sa = np.sin(np.maximum(alt, 0.005))
    ext = np.exp(-0.32 * (1.0 / (sa + 0.025 * np.exp(-11 * sa)) - 1.0))
    col = col * (0.64 * ext)[..., None]
    return col.astype(np.float32), lum * trans


# ---------------------------------------------------------------------------
# Bright-star catalogue (RA h, Dec deg, V, B-V) - real stars, rounded values
# ---------------------------------------------------------------------------
BRIGHT = [
    # Andromeda
    (0.1398, 29.09, 2.06, -0.11), (1.1622, 35.62, 2.05, 1.58), (2.0650, 42.33, 2.10, 1.37), (0.6556, 30.86, 3.27, 1.28),
    (0.6425, 29.31, 4.37, 0.87), (0.7889, 24.27, 4.06, 1.10), (0.9533, 23.42, 4.40, 0.94), (0.2847, 38.68, 4.61, 0.06),
    (23.6356, 43.27, 4.29, -0.10), (23.6733, 44.33, 4.14, -0.07), (23.6261, 46.46, 3.82, 1.01), (0.9461, 38.50, 3.87, 0.13),
    (0.8303, 41.08, 4.53, -0.15), (23.0319, 42.33, 3.62, -0.09), (0.6147, 33.72, 4.36, -0.14), (0.3036, 36.79, 4.52, 0.05),
    (1.1583, 47.24, 4.25, -0.07), (23.7742, 46.42, 4.95, 1.10), (1.4614, 45.41, 4.83, 0.42), (1.6331, 48.63, 3.59, 1.28),
    (1.6500, 44.39, 4.98, 0.90), (1.6739, 40.58, 4.94, -0.07), (1.6114, 41.41, 4.10, 0.54), (1.3700, 45.53, 4.88, 1.08),
    (2.1442, 37.86, 4.82, 0.13), (2.2083, 47.38, 5.30, 0.0), (0.4867, 24.27, 5.0, 0.9), (0.4006, 31.0, 5.2, 0.4),
    # Cassiopeia
    (0.6750, 56.54, 2.24, 1.17), (0.1531, 59.15, 2.28, 0.34), (0.9450, 60.72, 2.47, -0.15), (1.4303, 60.24, 2.68, 0.13),
    (1.9067, 63.67, 3.37, -0.15), (0.8183, 57.82, 3.44, 0.57), (0.6164, 53.90, 3.66, -0.20), (0.5550, 62.93, 4.16, 0.14),
    (1.1853, 55.15, 4.33, 0.17), (2.4861, 67.40, 4.52, 0.12), (23.9067, 57.50, 4.54, 1.22), (23.7792, 58.65, 4.87, 1.10),
    (2.0569, 72.42, 3.95, 0.0), (2.0300, 70.90, 4.5, 0.1), (1.2000, 68.1, 4.7, 0.0),
    # Perseus
    (3.4053, 49.86, 1.79, 0.48), (3.1361, 40.96, 2.12, -0.05), (3.0797, 53.51, 2.93, 0.70), (3.7153, 47.79, 3.01, -0.13),
    (3.9644, 40.01, 2.89, -0.18), (3.9022, 31.88, 2.85, 0.12), (2.8450, 55.90, 3.76, 1.68), (3.0861, 38.84, 3.39, 1.65),
    (3.1581, 44.86, 3.80, 0.98), (3.1514, 49.61, 4.05, 0.60), (2.9058, 52.76, 3.95, 0.74), (2.7378, 49.23, 4.12, 0.49),
    (3.7536, 42.58, 3.77, 0.42), (3.7378, 32.29, 3.83, 0.05), (3.9831, 35.79, 4.04, 0.01), (4.2481, 48.41, 4.14, 0.95),
    (4.1078, 50.35, 4.29, 0.0), (4.1442, 47.71, 4.04, -0.03), (1.7283, 50.69, 4.07, -0.04), (3.6086, 48.19, 4.31, -0.06),
    (3.5108, 47.99, 4.36, 1.35), (3.3, 49.5, 5.0, 0.0), (3.45, 49.2, 5.2, -0.05), (3.36, 48.6, 5.5, 0.1),
    # Triangulum, Aries, Pisces
    (1.8847, 29.58, 3.41, 0.49), (2.1592, 34.99, 3.00, 0.14), (2.2886, 33.85, 4.01, 0.02), (2.2856, 34.22, 4.87, 0.6),
    (2.1197, 23.46, 2.00, 1.15), (1.9106, 20.81, 2.64, 0.13), (1.8922, 19.29, 3.9, -0.05), (2.8333, 27.26, 3.63, -0.10),
    (1.5247, 15.35, 3.62, 0.97), (2.6, 21.3, 4.6, 0.2),
    # Pegasus
    (23.0794, 15.21, 2.49, -0.04), (23.0628, 28.08, 2.42, 1.67), (0.2206, 15.18, 2.83, -0.23), (22.7167, 30.22, 2.94, 0.86),
    (22.8333, 24.60, 3.48, 0.93), (22.7753, 23.57, 3.95, 1.07), (22.6967, 29.31, 4.79, 0.0), (22.1667, 33.18, 4.29, 0.46),
    (22.6911, 10.83, 3.40, -0.09), (21.7364, 9.88, 2.38, 1.53), (22.1167, 25.35, 3.77, 0.44), (21.7442, 25.65, 4.13, 0.43),
    (23.4183, 23.40, 4.40, 0.61), (23.3450, 23.74, 4.60, 0.17), (23.8728, 19.12, 5.08, 1.6), (23.9667, 25.14, 4.66, 1.6),
    # Lacerta
    (22.5217, 50.28, 3.77, 0.01), (22.3925, 52.23, 4.43, 1.02), (22.2661, 37.75, 4.13, 1.46), (22.4922, 47.71, 4.36, 1.68),
    (22.4083, 49.48, 4.57, 0.09), (22.5083, 43.12, 4.51, -0.09), (22.3417, 46.54, 4.57, -0.11), (22.6917, 44.28, 4.46, 1.33),
    # Cepheus
    (21.3097, 62.59, 2.45, 0.22), (21.4778, 70.56, 3.23, -0.22), (23.6558, 77.63, 3.21, 1.03), (22.1808, 58.20, 3.35, 1.57),
    (22.8278, 66.20, 3.52, 1.05), (22.4861, 58.42, 4.07, 0.6), (20.7547, 61.84, 3.41, 0.92), (21.7250, 58.78, 4.08, 2.35),
    (22.2508, 57.04, 4.18, 0.28), (20.4967, 63.0, 4.21, 0.0),
    # Cygnus, Lyra
    (20.6906, 45.28, 1.25, 0.09), (20.3703, 40.26, 2.23, 0.67), (20.7703, 33.97, 2.48, 1.03), (19.7497, 45.13, 2.87, -0.03),
    (19.5122, 27.96, 3.08, 1.13), (21.2156, 30.23, 3.21, 0.99), (21.0839, 43.93, 3.72, 1.65), (19.4950, 51.73, 3.79, 0.14),
    (19.2850, 53.37, 3.80, 0.96), (20.9525, 41.17, 3.94, 0.02), (21.2481, 38.05, 3.72, 0.39), (19.9383, 35.08, 3.89, 1.02),
    (18.6156, 38.78, 0.03, 0.0), (18.8347, 33.36, 3.52, 0.0), (18.9822, 32.69, 3.25, -0.05),
    # Auriga, Camelopardalis, Ursa Minor, Draco
    (5.2781, 46.00, 0.08, 0.80), (5.9922, 44.95, 1.90, 0.08), (5.0328, 43.82, 2.99, 0.54), (5.0408, 41.08, 3.75, 1.22),
    (5.1086, 41.23, 3.17, -0.18), (4.9500, 33.17, 2.69, 1.53), (5.9922, 54.28, 3.72, 1.0), (5.9953, 37.21, 2.62, -0.08),
    (5.0569, 60.44, 4.03, 0.92), (4.9008, 66.34, 4.29, 0.03), (3.4842, 59.94, 4.21, 0.0), (4.9572, 53.75, 4.47, 0.0),
    (2.5303, 89.26, 1.98, 0.60), (14.845, 74.16, 2.08, 1.47), (15.345, 71.83, 3.05, 0.0), (17.507, 52.30, 2.79, 0.98),
    (17.943, 51.49, 2.24, 1.52), (19.209, 67.66, 3.07, 1.0), (18.351, 72.73, 3.57, 0.5),
    # Taurus / Pleiades (only visible if above the horizon)
    (3.7914, 24.11, 2.87, -0.09), (3.8192, 24.05, 3.62, -0.08), (3.7478, 24.11, 3.70, -0.11), (3.7636, 24.37, 3.87, -0.07),
    (3.7722, 23.95, 4.18, -0.06), (3.7536, 24.47, 4.30, -0.11),
]


def bv_to_rgb(bv):
    """approximate star colour from B-V (linear RGB, normalised to max=1), desaturated a little"""
    bv = np.clip(bv, -0.35, 2.2)
    t = 4600 * (1 / (0.92 * bv + 1.7) + 1 / (0.92 * bv + 0.62))   # Ballesteros
    t = np.clip(t, 2500, 30000) / 100.0
    r = np.where(t <= 66, 1.0, np.clip(1.292936 * (t - 60) ** -0.1332, 0, 1))
    g = np.where(t <= 66, np.clip(0.390082 * np.log(t) - 0.631841, 0, 1), np.clip(1.129891 * (t - 60) ** -0.0755, 0, 1))
    b = np.where(t >= 66, 1.0, np.where(t <= 19, 0.0, np.clip(0.543207 * np.log(t - 10) - 1.196254, 0, 1)))
    rgb = np.stack([r, g, b], -1) ** 2.2
    rgb = rgb / rgb.max(-1, keepdims=True)
    return 0.68 * rgb + 0.32          # keep colours subtle like a real photo


def random_dirs_cone(center, radius_deg, n):
    """uniform random directions within a cone"""
    c = unit(center)
    cosr = math.cos(math.radians(radius_deg))
    z = RNG.uniform(cosr, 1.0, n)
    ph = RNG.uniform(0, 2 * math.pi, n)
    s = np.sqrt(1 - z * z)
    a = unit(np.cross(c, [0.3, 0.1, 0.95]))
    b = np.cross(c, a)
    return unit(z[:, None] * c + s[:, None] * (np.cos(ph)[:, None] * a + np.sin(ph)[:, None] * b))


def counts_per_sqdeg(m):
    """cumulative star counts N(<m) per sq deg at intermediate galactic latitude"""
    return 1.0 * 10 ** (0.43 * (m - 8.0))


def faint_stars(center, radius, m0, m1, dens_boost=1.0):
    area = 2 * math.pi * (1 - math.cos(math.radians(radius))) * (180 / math.pi) ** 2
    nexp = (counts_per_sqdeg(m1) - counts_per_sqdeg(m0)) * area * dens_boost
    nmax = int(nexp * 3.2)
    d = random_dirs_cone(center, radius, nmax)
    # density: galactic latitude + Milky Way star clouds
    _, l, b = gal_lb(d)
    _, lum = mw_model(d)
    dens = 0.55 + 1.9 * np.exp(-0.5 * (np.degrees(b) / 11.0) ** 2) + 4.0 * np.clip(lum, 0, 0.6)
    keep = RNG.uniform(0, 1, nmax) < dens / 3.2
    d = d[keep]
    n = len(d)
    # magnitudes from the counts law: N ~ 10^(0.43 m)
    u = RNG.uniform(0, 1, n)
    a0, a1 = 10 ** (0.43 * m0), 10 ** (0.43 * m1)
    m = np.log10(a0 + u * (a1 - a0)) / 0.43
    bv = np.clip(RNG.normal(0.75, 0.38, n), -0.25, 1.9)
    return d, m, bv


def build_catalog():
    ra = np.array([s[0] for s in BRIGHT]); dec = np.array([s[1] for s in BRIGHT])
    d_b = world_from_radec(ra, dec)
    m_b = np.array([s[2] for s in BRIGHT]); bv_b = np.array([s[3] for s in BRIGHT])
    parts = [(d_b, m_b, bv_b)]
    wide_c = world_from_altaz(np.radians(30.0), np.radians(50.0))
    parts.append(faint_stars(wide_c, 62.0, 5.6, 9.8))
    # double cluster h & chi Persei
    for ra0, de0 in ((2.3197, 57.13), (2.3711, 57.14)):
        c = world_from_radec(ra0, de0)
        n = 22
        dd = random_dirs_cone(c, 0.30, n)
        mm = 7.2 + RNG.exponential(1.1, n)
        parts.append((dd, np.minimum(mm, 10.5), np.clip(RNG.normal(0.2, 0.5, n), -0.2, 1.8)))
    # deeper stars toward M31 (revealed as we zoom, like a longer exposure / bigger lens)
    parts.append(faint_stars(M31_DIR, 24.0, 9.8, 11.2))
    parts.append(faint_stars(M31_DIR, 14.0, 11.2, 13.2))
    parts.append(faint_stars(M31_DIR, 6.0, 13.2, 15.4))
    d = np.concatenate([p[0] for p in parts]).astype(np.float32)
    m = np.concatenate([p[1] for p in parts]).astype(np.float32)
    bv = np.concatenate([p[2] for p in parts]).astype(np.float32)
    # keep only stars above the horizon; atmospheric extinction near the horizon
    alt = np.degrees(np.arcsin(np.clip(d[:, 2], -1, 1)))
    keep = alt > -1.0
    d, m, bv, alt = d[keep], m[keep], bv[keep], alt[keep]
    sa = np.sin(np.radians(np.maximum(alt, 0.3)))
    airmass = 1.0 / (sa + 0.025 * np.exp(-11 * sa))
    m = m + 0.25 * (airmass - 1.0)
    col = bv_to_rgb(bv).astype(np.float32)
    print(f"stars: {len(m)}  (V<6: {(m < 6).sum()}, V<9: {(m < 9).sum()})")
    np.savez_compressed(os.path.join(OUT, "ch1_stars.npz"), dirs=d, mag=m, col=col)


# ---------------------------------------------------------------------------
# Milky Way plane
# ---------------------------------------------------------------------------
MW_PLANE = dict(alt=24.0, az=50.0, tx=math.tan(math.radians(50)), ty=math.tan(math.radians(38)), W=3300, H=2280)


def sky_gradient(dirs):
    z = np.maximum(dirs[..., 2], 0.0)[..., None]
    return (np.array([0.0019, 0.0024, 0.0042], np.float32) + np.array([0.0062, 0.0086, 0.0080], np.float32) * np.exp(-z / 0.13)
            + np.array([0.0075, 0.0072, 0.0062], np.float32) * np.exp(-z / 0.035)).astype(np.float32)


def build_mw():
    p = MW_PLANE
    c, r, u = plane_basis(world_from_altaz(np.radians(p["alt"]), np.radians(p["az"])))
    t0 = time.time()
    step = 285
    dirs, X, Y = plane_dirs(c, r, u, p["tx"], p["ty"], p["W"], p["H"])
    out = np.zeros((p["H"], p["W"], 3), np.float32)
    for y0 in range(0, p["H"], step):
        col, _ = mw_model(dirs[y0:y0 + step])
        out[y0:y0 + step] = col
    print(f"mw model {time.time() - t0:.1f}s")
    # unresolved faint stars (mag 9-12.5) as a fine granular texture following the band
    nstar = 260000
    xs = RNG.uniform(-1, 1, nstar); ys = RNG.uniform(-1, 1, nstar)
    sd = unit(c[None] + (xs * p["tx"])[:, None] * r[None] + (ys * p["ty"])[:, None] * u[None])
    _, lum = mw_model(sd.astype(np.float32))
    _, l, b = gal_lb(sd)
    dens = 0.15 + 0.8 * np.exp(-0.5 * (np.degrees(b) / 10.0) ** 2) + 6.0 * np.clip(lum, 0, 0.5)
    # keep the zoom target clean: magnified texture-stars would look like soft blobs there
    dens *= smoothstep(14.0, 22.0, np.degrees(np.arccos(np.clip(sd @ M31_DIR, -1, 1))))
    keep = RNG.uniform(0, 1, nstar) < dens / 3.8
    px = ((xs[keep] + 1) / 2 * p["W"]).astype(int).clip(0, p["W"] - 1)
    py = ((1 - ys[keep]) / 2 * p["H"]).astype(int).clip(0, p["H"] - 1)
    fl = RNG.uniform(0.004, 0.022, keep.sum()) * RNG.exponential(1.0, keep.sum())
    acc = np.zeros((p["H"], p["W"]), np.float32)
    np.add.at(acc, (py, px), fl)
    acc = blur(acc, 0.7)
    out += acc[..., None] * np.array([0.92, 0.94, 1.0], np.float32)
    # night-sky background (zenith dark, airglow toward the horizon) baked in, so the renderer
    # needs a single texture lookup for the whole wide sky
    out += sky_gradient(dirs)
    # the naked-eye smudge of M31, projected from the galaxy frame into this plane
    eye = np.load(os.path.join(OUT, "ch1_m31_eye.npy")).astype(np.float32)
    gc, gr, gu = galaxy_plane()
    w_ = dirs @ gc
    gxd = np.degrees((dirs @ gr) / np.maximum(w_, 1e-4))
    gyd = np.degrees((dirs @ gu) / np.maximum(w_, 1e-4))
    eh, ew = eye.shape[:2]
    fx = (gxd / GAL_W_DEG + 0.5) * ew - 0.5
    fy = (0.5 - gyd / GAL_H_DEG) * eh - 0.5
    ok = (w_ > 0.5) & (fx >= 0) & (fx < ew - 1) & (fy >= 0) & (fy < eh - 1)
    x0 = np.floor(fx[ok]).astype(int); y0 = np.floor(fy[ok]).astype(int)
    ax_ = (fx[ok] - x0)[:, None]; ay_ = (fy[ok] - y0)[:, None]
    smp = ((eye[y0, x0] * (1 - ax_) + eye[y0, x0 + 1] * ax_) * (1 - ay_) +
           (eye[y0 + 1, x0] * (1 - ax_) + eye[y0 + 1, x0 + 1] * ax_) * ay_)
    out[ok] += smp
    # mean sky level around M31 (ring 2-5 deg) -> constant background for the zoomed-in shots
    ang = np.degrees(np.arccos(np.clip(dirs @ M31_DIR, -1, 1)))
    ring = (ang > 2.0) & (ang < 5.0)
    p["bg_m31"] = out[ring].mean(axis=0).tolist()
    p["c"], p["r"], p["u"] = c.tolist(), r.tolist(), u.tolist()
    write_png(os.path.join(OUT, "ch1_mw.png"), srgb(out), bits=16)
    preview("mw_prev.png", out, 3)


# ---------------------------------------------------------------------------
# Andromeda (M31) + M32 + M110
# ---------------------------------------------------------------------------
GAL_W_DEG, GAL_H_DEG = 4.2, 2.4
GAL_W_PX, GAL_H_PX = 4096, 2340
KPC_PER_DEG = 770.0 * D2R            # 13.44 kpc per degree at 770 kpc
INC = math.radians(75.5)


def periodic_noise(n, slope, seed):
    rng = np.random.default_rng(seed)
    w = rng.normal(0, 1, (n, n)).astype(np.float32)
    f = np.fft.rfft2(w)
    ky = np.fft.fftfreq(n)[:, None]
    kx = np.fft.rfftfreq(n)[None, :]
    k = np.sqrt(kx * kx + ky * ky)
    k[0, 0] = 1.0
    f *= (k ** (-slope / 2.0)).astype(np.float32)
    f[0, 0] = 0
    out = np.fft.irfft2(f, s=(n, n)).astype(np.float32)
    out = (out - out.mean()) / out.std()
    return out


def sample(grid, x, y):
    """bilinear periodic sample; x,y in grid pixel units"""
    n = grid.shape[0]
    x0 = np.floor(x); y0 = np.floor(y)
    fx = (x - x0).astype(np.float32); fy = (y - y0).astype(np.float32)
    x0 = x0.astype(np.int64) % n; y0 = y0.astype(np.int64) % n
    x1 = (x0 + 1) % n; y1 = (y0 + 1) % n
    return ((grid[y0, x0] * (1 - fx) + grid[y0, x1] * fx) * (1 - fy) +
            (grid[y1, x0] * (1 - fx) + grid[y1, x1] * fx) * fy)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def galaxy_plane():
    c = M31_DIR
    n, e = sky_north_east(c)
    pa_nw = math.radians(38.0 - 90.0)
    u = unit(math.cos(pa_nw) * n + math.sin(pa_nw) * e)     # minor axis, toward NW (near side)
    r = np.cross(c, u)                                      # major axis (toward SW)
    return c, r, u


def proj(c, r, u, d):
    d = np.asarray(d)
    return np.degrees(np.dot(d, r) / np.dot(d, c)), np.degrees(np.dot(d, u) / np.dot(d, c))


def build_galaxy():
    t0 = time.time()
    c, r, u = galaxy_plane()
    W, H = GAL_W_PX, GAL_H_PX
    xs = ((np.arange(W) + 0.5) / W - 0.5) * GAL_W_DEG
    ys = (0.5 - (np.arange(H) + 0.5) / H) * GAL_H_DEG
    X, Y = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32))   # deg; X toward SW, Y toward NW
    pxdeg = W / GAL_W_DEG
    # disk-plane coordinates (kpc). Y>0 is the near side.
    xd = X * KPC_PER_DEG
    yd = Y * KPC_PER_DEG / math.cos(INC)
    rd = np.sqrt(xd * xd + yd * yd)
    th = np.arctan2(yd, xd)
    # noise fields in the disk plane (periodic grids, 60 kpc period, sampled at several scales)
    N = 2048
    nA = periodic_noise(N, 2.2, 1)       # large-scale structure
    nB = periodic_noise(N, 2.0, 2)       # small-scale clumps
    nC = periodic_noise(N, 0.6, 3)       # near-white: stellar granularity / filaments
    kp = N / 60.0                        # grid px per kpc
    gx, gy = xd * kp + N / 2, yd * kp + N / 2
    # anti-aliased sampling: low-pass each grid to the texture's pixel footprint (anisotropic,
    # the deprojected y axis is stretched by 1/cos(i)), otherwise the noise aliases into speckle
    stx = kp * KPC_PER_DEG * GAL_W_DEG / W
    sty = stx / math.cos(INC)

    def lp(grid, s):
        n_ = grid.shape[0]
        fy = np.fft.fftfreq(n_)[:, None]
        fx = np.fft.rfftfreq(n_)[None, :]
        sx_, sy_ = 0.55 * s * stx, 0.55 * s * sty
        g = np.exp(-2 * math.pi ** 2 * ((sx_ * fx) ** 2 + (sy_ * fy) ** 2)).astype(np.float32)
        return np.fft.irfft2(np.fft.rfft2(grid) * g, s=grid.shape).astype(np.float32)

    def samp(grid, s, ox, oy):
        return sample(lp(grid, s), gx * s + ox, gy * s + oy)

    A = samp(nA, 1.0, 0, 0)
    A2 = samp(nA, 2.3, 311, 97)
    B = samp(nB, 1.0, 50, 900)
    B2 = samp(nB, 2.7, 1200, 400)
    Cn = samp(nC, 1.6, 0, 0)
    print(f"  noise {time.time() - t0:.1f}s")

    # --- spiral / ring pattern (M31: tightly wound arms + the 10 kpc ring) ---
    pitch = math.radians(8.5)
    lnr = np.log(np.maximum(rd, 0.2))
    phase = 2 * (th - lnr / math.tan(pitch)) + 1.3 * A + 0.6 * A2
    arm = (0.5 + 0.5 * np.cos(phase)) ** 3.0
    # the 10 kpc ring is off-centre and slightly elliptical in M31
    rr_ = np.sqrt((xd - 0.8) ** 2 + ((yd + 0.5) * 1.08) ** 2)
    ring10 = np.exp(-0.5 * ((rr_ - 10.5 - 1.0 * A - 0.8 * np.cos(th * 3 + 1.0)) / 1.9) ** 2)
    ring15 = np.exp(-0.5 * ((rd - 15.0 - 1.2 * A2 - 0.9 * np.sin(th * 2 + 0.3)) / 1.8) ** 2)
    ring5 = np.exp(-0.5 * ((rd - 5.2 - 0.5 * A) / 1.1) ** 2)
    rings = 0.9 * ring10 + 0.55 * ring15 + 0.35 * ring5
    armlike = np.clip(0.55 * arm + 0.75 * rings * (0.55 + 0.45 * arm), 0, 1.6)

    # --- stellar disk ---
    disk = np.exp(-rd / 5.6) * (1 - 0.85 * smoothstep(14.0, 30.0, rd)) * (0.55 + 0.45 * smoothstep(1.0, 6.0, rd))
    thick = np.exp(-np.sqrt(xd ** 2 + (Y * KPC_PER_DEG / 0.42) ** 2) / 6.5) * (1 - smoothstep(18.0, 30.0, rd * 0.9))
    gran = np.exp(0.03 * Cn + 0.05 * B2 + 0.15 * A2)
    young = np.clip(blur(armlike, 0.8), 0, None) * disk ** 0.6 * smoothstep(3.0, 8.0, rd) * (1 - smoothstep(17.0, 26.0, rd)) * (0.25 + 1.3 * smoothstep(-0.7, 1.4, B)) * gran
    young = np.clip(blur(young, 1.8), 0, None)
    old_disk = disk * (0.85 + 0.25 * armlike) * np.exp(0.03 * Cn + 0.08 * B)

    # --- bulge (slightly boxy, axis ratio ~0.62, misaligned a few degrees) ---
    rot = math.radians(-6.0)
    Xb = (X * math.cos(rot) - Y * math.sin(rot)) * KPC_PER_DEG
    Yb = (X * math.sin(rot) + Y * math.cos(rot)) * KPC_PER_DEG / 0.62
    rb = (np.abs(Xb) ** 2.2 + np.abs(Yb) ** 2.2) ** (1 / 2.2)
    bulge = np.exp(-7.67 * ((rb / 1.0) ** (1 / 2.2) - 1))           # sersic n=2.2, Re=1 kpc
    rn = np.sqrt((X * KPC_PER_DEG) ** 2 + (Y * KPC_PER_DEG / 0.8) ** 2)
    nucleus = np.exp(-0.5 * (rn / 0.035) ** 2) * 40 + np.exp(-0.5 * (rn / 0.12) ** 2) * 6
    halo = np.exp(-np.sqrt((X * KPC_PER_DEG) ** 2 + (Y * KPC_PER_DEG / 0.55) ** 2) / 9.0)
    rbo = np.sqrt((X * KPC_PER_DEG) ** 2 + (Y * KPC_PER_DEG / 0.58) ** 2)
    outer_bulge = np.exp(-rbo / 1.6)

    # --- dust: lanes on the inner edges of the arms/rings + filaments ---
    dphase = phase + 0.75
    darm = (0.5 + 0.5 * np.cos(dphase)) ** 4.0
    dring = (np.exp(-0.5 * ((rd - 9.6 - 0.6 * A) / 0.9) ** 2) + 0.7 * np.exp(-0.5 * ((rd - 13.9 - 0.8 * A2) / 0.85) ** 2)
             + 0.6 * np.exp(-0.5 * ((rd - 4.7 - 0.4 * A) / 0.6) ** 2) + 0.35 * np.exp(-0.5 * ((rd - 7.2 - 0.5 * A2) / 0.7) ** 2))
    fil = np.clip(0.75 + 0.45 * B + 0.12 * Cn, 0, 2.0)
    rr_d = np.sqrt((xd - 0.8) ** 2 + ((yd + 0.5) * 1.08) ** 2)
    dring = (np.exp(-0.5 * ((rr_d - 9.4 - 1.0 * A - 0.8 * np.cos(th * 3 + 1.0)) / 0.95) ** 2)
             + 0.8 * np.exp(-0.5 * ((rd - 13.9 - 1.2 * A2 - 0.9 * np.sin(th * 2 + 0.3)) / 0.9) ** 2)
             + 0.7 * np.exp(-0.5 * ((rd - 4.6 - 0.5 * A) / 0.55) ** 2) + 0.45 * np.exp(-0.5 * ((rd - 7.0 - 0.6 * A2) / 0.7) ** 2)
             + 0.4 * np.exp(-0.5 * ((rd - 2.9 - 0.3 * A) / 0.35) ** 2))
    A3 = samp(nA, 3.1, 77, 501)
    A4 = samp(nA, 6.3, 900, 13)
    wisps = smoothstep(0.72, 0.96, 1 - np.abs(A3) * 0.9) * (0.6 + 0.4 * smoothstep(0.6, 0.95, 1 - np.abs(A4)))
    wisps += 0.5 * smoothstep(0.80, 0.97, 1 - np.abs(A4))
    lane_mask = np.clip(0.30 + 0.9 * darm + 1.4 * dring, 0, 2.0)
    fil = np.clip(0.80 + 0.25 * B + 0.05 * Cn, 0.3, 1.6)
    dust = (0.45 * darm + 1.0 * dring * (0.55 + 0.45 * darm)) * fil + 0.55 * wisps * lane_mask
    dust *= smoothstep(1.8, 3.2, rd) * (1 - smoothstep(16.5, 22.0, rd))
    tau = np.clip(blur(2.9 * dust, 1.1), 0, None)
    near = smoothstep(-0.02, 0.10, Y)        # near side (NW): dust silhouetted against the bulge
    tau_bulge = tau * (0.25 + 1.6 * near)
    redden = np.array([0.78, 0.92, 1.18], np.float32)

    # --- star-forming knots (blue clusters) and HII regions (pink) along the arms ---
    knots = np.zeros((H, W, 3), np.float32)
    w_arm = (young / (young.max() + 1e-6)).ravel()
    w_arm = w_arm / w_arm.sum()
    for count, sig, colr, amp in ((22000, 0.8, (0.55, 0.70, 1.0), 0.022),
                                  (4000, 1.3, (0.65, 0.78, 1.0), 0.040),
                                  (1500, 1.1, (1.0, 0.36, 0.55), 0.045),
                                  (350, 2.2, (1.0, 0.45, 0.62), 0.055)):
        idx = RNG.choice(W * H, size=count, p=w_arm)
        acc = np.zeros((H, W), np.float32)
        np.add.at(acc, (idx // W, idx % W), amp * RNG.exponential(1.0, count).astype(np.float32))
        acc = blur(acc, sig) * (2 * math.pi * sig * sig)
        knots += acc[..., None] * np.array(colr, np.float32)
    # NGC 206: the great star cloud in the SW disk
    ngc206 = (X, Y)
    sx, sy = 0.62, -0.10
    n206 = np.exp(-0.5 * (((X - sx) / 0.035) ** 2 + ((Y - sy) / 0.018) ** 2)) * (0.6 + 0.5 * np.clip(B2, -1, 2))
    knots += n206[..., None] * np.array([0.6, 0.72, 1.0], np.float32) * 0.020
    # globular clusters / bright resolved giants of M31 (tiny warm dots)
    ngc = 2200
    idx = RNG.choice(W * H, size=ngc, p=((disk * 0.5 + bulge * 0.2 + halo * 0.05).ravel() / (disk * 0.5 + bulge * 0.2 + halo * 0.05).sum()))
    acc = np.zeros((H, W), np.float32)
    np.add.at(acc, (idx // W, idx % W), 0.03 * RNG.exponential(1.0, ngc).astype(np.float32))
    knots += blur(acc, 0.8)[..., None] * np.array([1.0, 0.9, 0.75], np.float32) * 5.0

    # --- satellites ---
    mx, my = proj(c, r, u, M32_DIR)
    hx, hy = proj(c, r, u, M110_DIR)
    print(f"  M32 at ({mx:.3f},{my:.3f}) deg, M110 at ({hx:.3f},{hy:.3f}) deg")
    r32 = np.sqrt((X - mx) ** 2 + ((Y - my) / 0.8) ** 2) * 60.0       # arcmin
    m32 = (np.exp(-7.67 * ((np.maximum(r32, 0.02) / 0.45) ** 0.25 - 1)) * 0.22 + np.exp(-0.5 * (r32 / 0.05) ** 2) * 14.0
           + np.exp(-r32 / 1.3) * 0.6)
    # M110: PA 170 on the sky; express in the plane frame
    n_, e_ = sky_north_east(M110_DIR)
    ax = unit(math.cos(math.radians(170)) * n_ + math.sin(math.radians(170)) * e_)
    ang = math.atan2(np.dot(ax, u), np.dot(ax, r))
    dx, dy = X - hx, Y - hy
    a1 = (dx * math.cos(ang) + dy * math.sin(ang)) * 60
    a2 = (-dx * math.sin(ang) + dy * math.cos(ang)) * 60 / 0.5
    r110 = np.sqrt(a1 ** 2 + a2 ** 2)
    m110 = np.exp(-r110 / 2.2) * 0.9 + np.exp(-0.5 * (r110 / 0.25) ** 2) * 0.8

    print(f"  components {time.time() - t0:.1f}s")
    # --- compose (linear, arbitrary units) ---
    col_bulge = np.array([1.0, 0.80, 0.56], np.float32)
    col_old = np.array([1.0, 0.88, 0.72], np.float32)
    col_young = np.array([0.52, 0.68, 1.0], np.float32)
    col_halo = np.array([0.85, 0.85, 0.95], np.float32)
    Lb = (bulge * 2.2 + nucleus + outer_bulge * 0.9)[..., None] * col_bulge
    Lb = Lb * np.exp(-tau_bulge[..., None] * redden)
    Ld = (old_disk * 1.2)[..., None] * col_old + (young * 0.78)[..., None] * col_young
    Ld = Ld * np.exp(-(0.45 + 0.75 * near)[..., None] * tau[..., None] * redden)
    Lh = (halo * 0.05 + thick * 0.10)[..., None] * col_halo
    Lk = knots * np.exp(-0.5 * tau[..., None] * redden)[..., :]
    Lsat = (m32 * 1.0)[..., None] * np.array([1.0, 0.86, 0.68], np.float32) + (m110 * 0.30)[..., None] * np.array([1.0, 0.90, 0.76], np.float32)
    lin = Lb + Ld + Lh + Lk + Lsat
    lin = blur(lin, 0.55)
    np.save(os.path.join(OUT, "ch1_m31_linear.npy"), lin.astype(np.float16))
    print(f"  composed {time.time() - t0:.1f}s, max {lin.max():.1f}, p50 {np.percentile(lin, 50):.4f}")
    return lin


def tone_galaxy(lin, soft=0.03, white=30.0, gain=1.0, sat=1.3):
    """asinh stretch on luminance (colour preserving), as in astrophotography"""
    L = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    s = np.arcsinh(L / soft) / np.arcsinh(white / soft)
    s = np.clip(s, 0, None)
    f = s / np.maximum(L, 1e-9)
    out = lin * f[..., None]
    # saturation
    Lo = out @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    out = Lo[..., None] + (out - Lo[..., None]) * sat
    out = np.clip(out, 0, None) * gain
    # soft shoulder toward white
    out = 1 - np.exp(-out * 1.3)
    out = out / (1 - math.exp(-1.3))
    return np.clip(out, 0, 1)


def edge_fade(img, frac=0.04):
    h, w = img.shape[:2]
    fx = smoothstep(0, frac, np.minimum(np.arange(w) / w, 1 - np.arange(w) / w))
    fy = smoothstep(0, frac * w / h, np.minimum(np.arange(h) / h, 1 - np.arange(h) / h))
    return img * (fy[:, None] * fx[None, :])[..., None]


def save_galaxy(lin):
    disp = tone_galaxy(lin)
    # the display texture is used additively in a linear renderer: store display-linear values
    # (sRGB-encoded in the PNG; Blender decodes back to these linear values)
    disp_lin = disp ** 2.2 * 0.95
    disp_lin = edge_fade(disp_lin, 0.035)
    write_png(os.path.join(OUT, "ch1_m31_hi.png"), srgb(disp_lin))
    mid = box_down(disp_lin, 2)
    write_png(os.path.join(OUT, "ch1_m31_mid.png"), srgb(mid))
    lo = box_down(disp_lin, 4)
    write_png(os.path.join(OUT, "ch1_m31_lo.png"), srgb(lo))
    # naked eye: heavily blurred, only the bright inner region survives
    L = box_down(lin, 4)
    lum = L @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    ref = lum.max()
    # what the dark-adapted eye picks up: the bright core and a little of the inner disk, all soft
    eye = np.clip(lum / ref, 0, 1) ** 0.22
    eye = blur(eye, 9.0)
    eye = np.clip((eye - 0.10) / 0.90, 0, 1) ** 1.5 * 0.42
    eye_rgb = eye[..., None] * np.array([0.92, 0.92, 0.98], np.float32)
    eye_rgb = edge_fade(eye_rgb, 0.05)
    write_png(os.path.join(OUT, "ch1_m31_eye.png"), srgb(eye_rgb))
    np.save(os.path.join(OUT, "ch1_m31_eye.npy"), eye_rgb.astype(np.float32))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        write_png(os.path.join(PREVIEW, "m31_prev.png"), srgb(box_down(disp_lin, 3)))
        h, w = disp_lin.shape[:2]
        write_png(os.path.join(PREVIEW, "m31_crop.png"), srgb(disp_lin[h // 2 - 540:h // 2 + 540, w // 2 - 960:w // 2 + 960]))
        write_png(os.path.join(PREVIEW, "m31_crop2.png"), srgb(disp_lin[h // 2 - 700:h // 2 + 380, w // 2 + 100:w // 2 + 2020]))
        write_png(os.path.join(PREVIEW, "m31_eye.png"), srgb(eye_rgb))


def build_ring():
    n = 1024
    y, x = (np.mgrid[0:n, 0:n] + 0.5) / n * 2 - 1
    rr = np.sqrt(x * x + y * y)
    width = 0.012                                 # relative to radius 1 (radius = 0.96 in texture)
    ring = np.exp(-0.5 * ((rr - 0.96) / width) ** 2)
    fill = (rr < 0.96) * 0.06
    img = np.stack([ring * 0.95 + fill * 0.9, ring * 0.92 + fill * 0.88, ring * 1.0 + fill], -1)
    write_png(os.path.join(OUT, "ch1_ring.png"), srgb(img))


def main():
    t0 = time.time()
    if ONLY is None or "cat" in ONLY:
        build_catalog()
    if ONLY is None or "gal" in ONLY:
        lin = build_galaxy()
        save_galaxy(lin)
    elif "tone" in ONLY:
        lin = np.load(os.path.join(OUT, "ch1_m31_linear.npy")).astype(np.float32)
        save_galaxy(lin)
    if ONLY is None or "mw" in ONLY:
        build_mw()
    else:
        c, r, u = plane_basis(world_from_altaz(np.radians(MW_PLANE["alt"]), np.radians(MW_PLANE["az"])))
        MW_PLANE["c"], MW_PLANE["r"], MW_PLANE["u"] = c.tolist(), r.tolist(), u.tolist()
        old = json.load(open(os.path.join(OUT, "ch1_meta.json")))
        MW_PLANE["bg_m31"] = old["mw_plane"].get("bg_m31", [0.002, 0.0025, 0.004])
    if ONLY is None or "ring" in ONLY:
        build_ring()
    gc, gr, gu = galaxy_plane()
    meta = dict(
        lat=LAT, lst=LST, az0=AZ0,
        world_from_eq=W_EQ.tolist(),
        m31=M31_DIR.tolist(), m32=M32_DIR.tolist(), m110=M110_DIR.tolist(),
        mw_plane=dict(c=MW_PLANE["c"], r=MW_PLANE["r"], u=MW_PLANE["u"], tx=MW_PLANE["tx"], ty=MW_PLANE["ty"],
                      bg_m31=MW_PLANE["bg_m31"]),
        gal_plane=dict(c=gc.tolist(), r=gr.tolist(), u=gu.tolist(),
                       tx=math.tan(math.radians(GAL_W_DEG / 2)), ty=math.tan(math.radians(GAL_H_DEG / 2))),
        # Andromeda constellation figure + the classic star-hop Mirach -> mu -> nu -> M31
        lines=[[(0.1398, 29.09), (0.6556, 30.86)], [(0.6556, 30.86), (1.1622, 35.62)], [(1.1622, 35.62), (2.0650, 42.33)],
               [(1.1622, 35.62), (0.9461, 38.50)], [(0.9461, 38.50), (0.8303, 41.08)]],
        line_world=[],
    )
    for a, b in meta["lines"]:
        meta["line_world"].append([world_from_radec(*a).tolist(), world_from_radec(*b).tolist()])
    with open(os.path.join(OUT, "ch1_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
