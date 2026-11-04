"""Stylised Lituya Bay world model (shared by the terrain baker, the Blender scene and the compositor).

Map frame: x, y in km. +y runs up-bay (entrance -> head), which in reality points roughly NE (azimuth ~45 deg),
so the real north-west (Gilbert Inlet, the twilight glow) is towards -x.  This is a STYLISED terrain built from
distance fields + noise, sized after the real bay (not survey data):
  * main bay ~11 km from the entrance to the T, 2-3 km wide, entrance ~0.5 km wide between low forested foreland
  * Cenotaph Island ~4.8 km inside the mouth
  * crossbar of the T = Gilbert Inlet (-x) and Crillon Inlet (+x) along the Fairweather Fault trench,
    each fed by a tidewater glacier
  * the 1958 slide on the NE (here: +y) wall of Gilbert Inlet, max ~900 m altitude,
    run-up maximum 524 m on the spur opposite (south side of Gilbert Inlet)
All heights in metres."""
import numpy as np

HERE_SEED = 1958

# ------------------------------------------------------------------ noise tiles (periodic, cached)
_TILES = {}


def _tile(seed, beta, n=1024):
    key = (seed, beta, n)
    if key not in _TILES:
        r = np.random.default_rng(seed)
        wn = r.standard_normal((n, n)).astype(np.float32)
        f = np.fft.fftfreq(n) * n
        kx, ky = np.meshgrid(f, f)
        k = np.sqrt(kx ** 2 + ky ** 2)
        amp = np.where(k < 1.5, 0, (k + 1e-6) ** (-beta / 2))
        o = np.real(np.fft.ifft2(np.fft.fft2(wn) * amp)).astype(np.float32)
        _TILES[key] = (o - o.mean()) / o.std()
    return _TILES[key]


def _samp(tex, u, v):
    h, w = tex.shape
    x = u * w; y = v * h
    x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
    fx = (x - x0).astype(np.float32); fy = (y - y0).astype(np.float32)
    x0 %= w; y0 %= h; x1 = (x0 + 1) % w; y1 = (y0 + 1) % h
    a = tex[y0, x0]; b = tex[y0, x1]; c = tex[y1, x0]; d = tex[y1, x1]
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


def noise(x, y, scale_km, seed=0, beta=2.8):
    """Smooth gaussian-ish noise (unit std) with features ~scale_km."""
    t = _tile(seed, beta)
    return _samp(t, x / (scale_km * 16.0) + 0.37 * seed, y / (scale_km * 16.0) + 0.61 * seed)


def fbm(x, y, s0, octs=5, seed=0, gain=0.5, ridged=False):
    acc = 0.0; a = 1.0; tot = 0.0; s = s0
    for o in range(octs):
        n = noise(x, y, s, seed + 11 * o, beta=3.0)
        if ridged:
            n = 1.0 - np.abs(n) * 0.9
        acc = acc + a * n; tot += a; a *= gain; s *= 0.5
    return acc / tot


def sst(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ geometry
BAY = [(0.0, -0.6, 0.24), (0.02, 0.35, 0.26), (0.15, 1.1, 1.05), (0.35, 3.0, 1.45), (0.25, 5.8, 1.55),
       (0.25, 8.3, 1.15), (0.55, 10.4, 0.8)]
GILBERT = [(0.55, 10.45, 0.80), (-1.5, 10.95, 0.66), (-3.15, 11.65, 0.60)]
CRILLON = [(0.55, 10.45, 0.80), (1.9, 10.8, 0.62), (3.4, 11.25, 0.55)]
LITUYA_GL = [(-3.35, 11.7, 0.62), (-4.4, 12.9, 0.78), (-5.2, 14.6, 0.95), (-5.7, 17.0, 1.1), (-6.0, 20.0, 1.2)]
CRILLON_GL = [(3.6, 11.3, 0.55), (4.5, 12.9, 0.7), (5.0, 15.0, 0.85), (5.4, 18.0, 1.0)]
CENOTAPH = (0.45, 4.8, 0.62)
IMPACT = (-1.62, 11.12)          # where the slide hits the water (north half of Gilbert Inlet)
SLIDE_C = (-1.65, 11.85)          # centre of the slide scar on the +y wall
SPUR = (-1.5, 9.72)             # run-up maximum (524 m) on the spur opposite
RUNUP_MAX = 524.0


def _polyline_sdf(x, y, pts):
    """Signed distance (km) to a variable-width capsule chain; also returns along-track distance (km)."""
    best = np.full(np.shape(x), 1e9, np.float32); along = np.zeros(np.shape(x), np.float32)
    acc = 0.0
    for (x0, y0, w0), (x1, y1, w1) in zip(pts[:-1], pts[1:]):
        dx, dy = x1 - x0, y1 - y0; L2 = dx * dx + dy * dy; L = np.sqrt(L2)
        t = np.clip(((x - x0) * dx + (y - y0) * dy) / L2, 0, 1)
        px = x0 + t * dx; py = y0 + t * dy
        d = np.sqrt((x - px) ** 2 + (y - py) ** 2) - (w0 + (w1 - w0) * t)
        m = d < best
        best = np.where(m, d, best); along = np.where(m, acc + t * L, along)
        acc += L
    return best.astype(np.float32), along.astype(np.float32)


def water_sdf(x, y):
    wig = 0.035 * noise(x, y, 0.25, 3) + 0.06 * noise(x, y, 1.0, 4)
    d1, _ = _polyline_sdf(x, y, BAY)
    d2, _ = _polyline_sdf(x, y, GILBERT)
    d3, _ = _polyline_sdf(x, y, CRILLON)
    coast = -0.35 + 0.12 * noise(x, y * 0 + 0.0, 1.6, 5) + 0.02 * x   # outer coast, ocean at y < coast
    d4 = (y - coast)
    d = np.minimum(np.minimum(d1, d2), np.minimum(d3, d4)) + wig
    # Cenotaph Island (land inside the bay)
    di = np.sqrt((x - CENOTAPH[0]) ** 2 + ((y - CENOTAPH[1]) / 1.25) ** 2) - CENOTAPH[2] + 0.05 * noise(x, y, 0.2, 6)
    d = np.maximum(d, -di)
    return d.astype(np.float32)


def glacier_sdf(x, y):
    a, ta = _polyline_sdf(x, y, LITUYA_GL)
    b, tb = _polyline_sdf(x, y, CRILLON_GL)
    wig = 0.05 * noise(x, y, 0.5, 9)
    d = np.minimum(a, b) + wig
    t = np.where(a < b, ta, tb)
    return d.astype(np.float32), t.astype(np.float32)


def amplitude(y):
    return 40 + 1050 * sst(1.2, 8.8, y) + 1100 * sst(10.5, 18.0, y) + 1500 * sst(16.0, 32.0, y)


def fields(x, y):
    """Returns dict with h (m), water sdf, glacier sdf/mask, rock/snow helpers for points (km)."""
    x = np.asarray(x, np.float32); y = np.asarray(y, np.float32)
    dw = water_sdf(x, y)
    dg, tg = glacier_sdf(x, y)
    zg = 42 + 95 * tg ** 1.05 + 4 * noise(x, y, 0.3, 21)           # glacier surface
    r = np.maximum(np.minimum(dw, np.maximum(dg, 0) + 0.0), 0)
    rr = np.maximum(dw, 0)
    rg = np.maximum(dg, 0)
    A = amplitude(y) + 650 * np.exp(-((x + 2.0) ** 2 + (y - 9.1) ** 2) / 0.9)
    L = 0.85 + 0.5 * (1 - sst(0.5, 6.5, y)) - 0.25 * sst(6.5, 9.5, y) + 0.25 * sst(9.5, 10.8, y)
    big = fbm(x, y, 3.0, 3, 1)
    ridg = fbm(x, y, 2.0, 3, 2, gain=0.30, ridged=True)
    ramp_w = 1 - np.exp(-rr / L)
    ramp_g = 1 - np.exp(-rg / (L * 1.2))
    ramp = np.minimum(ramp_w, ramp_g)
    mount = A * ramp ** 0.95 * (0.82 + 0.22 * big + 0.26 * (ridg - 0.55))
    mount += 7 * fbm(x, y, 0.15, 3, 7) * ramp + 2.5 * noise(x, y, 0.06, 8)
    # glacier valley floors lift surrounding land
    near_g = np.exp(-rg / 1.0)
    base = zg * near_g
    land = np.maximum(base + mount, 2.0 + 6 * ramp_w)
    # foreland / spit: low and flat near the outer coast
    fore = 1 - sst(0.6, 2.2, y)
    land = land * (1 - 0.35 * fore) + fore * (8 + 25 * sst(0.0, 0.8, rr)) * 0.35
    # glacier surface (only on land side)
    gm = sst(0.06, -0.06, dg) * (dw > 0)
    h = land * (1 - gm) + np.maximum(zg, land * 0.0) * gm
    # water
    depth = -(8 + 210 * sst(0.0, 0.7, -dw) * sst(0.3, 3.0, y))
    h = np.where(dw < 0, np.minimum(depth, h * 0 - 1), h)
    # Cenotaph Island dome
    di = np.sqrt((x - CENOTAPH[0]) ** 2 + ((y - CENOTAPH[1]) / 1.25) ** 2)
    isl = 95 * np.exp(-(di / 0.45) ** 3) + 10 * noise(x, y, 0.1, 30)
    h = np.where((dw >= 0) & (di < 0.8), np.maximum(h, isl), h)
    # shoreline shelf so the land meets the water gently
    h = np.where((dw >= 0) & (dw < 0.04), np.minimum(h, 2 + dw / 0.04 * np.maximum(h, 2)), h)
    return dict(h=h.astype(np.float32), dw=dw, dg=dg, gm=gm.astype(np.float32), A=A)


def runup(x, y):
    """Max elevation (m) the 1958 water reached at map point (stylised after Miller 1960 trimline map)."""
    d_sp = np.sqrt((x - SPUR[0]) ** 2 + ((y - SPUR[1]) * 1.15) ** 2)
    d_im = np.sqrt((x - IMPACT[0]) ** 2 + (y - IMPACT[1]) ** 2)
    head = 150 * np.exp(-np.maximum(d_im - 0.6, 0) / 2.2)
    bay = 28 + 110 * sst(1.0, 10.0, y) ** 1.6
    hot = (RUNUP_MAX - 150) * np.exp(-(d_sp / 0.7) ** 2.2)
    R = np.maximum(head, bay) + hot * (y < 10.6)
    R += 8 * noise(x, y, 0.15, 40) + 4 * noise(x, y, 0.04, 41)
    return np.minimum(R, RUNUP_MAX).astype(np.float32)


def wet_limit(x, y):
    """How far inland (km from shore) the water can reach."""
    d_sp = np.sqrt((x - SPUR[0]) ** 2 + (y - SPUR[1]) ** 2)
    return 0.35 + 0.9 * np.exp(-(d_sp / 0.8) ** 2)


def arrival(x, y, h):
    """Event-time (s after impact) when the water reaches a map point at elevation h (stylised kinematics)."""
    d_im = np.sqrt((x - IMPACT[0]) ** 2 + (y - IMPACT[1]) ** 2) * 1000.0
    t_h = d_im / 55.0
    # down-bay travel: along y towards the entrance at ~45 m/s once out of the head
    down = np.maximum(10.3 - y, 0) * 1000.0 / 45.0
    inbay = (y < 10.3 + 0.1 * noise(x, y, 0.2, 44)) & (x > -0.95 + 0.15 * noise(x, y, 0.2, 45))                 # main bay (down-bay travel); the spur keeps the direct path
    t = np.where(inbay, np.maximum(53.5 + down, t_h), t_h)
    climb = np.maximum(h, 0) / 22.0
    return (t + climb).astype(np.float32)


def slide_mask(x, y, h):
    """1 inside the 1958 slide scar (on the +y wall of Gilbert Inlet, from the waterline to ~900 m)."""
    dx = (x - SLIDE_C[0]) / 0.5
    m = sst(1.0, 0.8, np.abs(dx) + 0.12 * noise(x, y, 0.15, 50)) * sst(930, 880, h) * sst(-2, 6, h)
    m *= (y > 11.2)
    return m.astype(np.float32)
