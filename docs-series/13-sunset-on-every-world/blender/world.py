"""Blender (bpy 5.1.2, Cycles CPU) landscape plates for 13 'Sunset on every world'.
One square telephoto plate (24 deg field, 2160 px) per world, looking at the point where the Sun sets. Each world has its
own height field (numpy), its own rock / ice / cloud geometry and its own albedo. The plate is rendered as separable passes
so the compositor can light it with that world's Sun and sky:
  beauty : white material, three lights in three colour channels  R = sun (hard, real angular size)
                                                                   G = horizon glow (wide soft source around the sunset point; second sun for Kepler-16)
                                                                   B = uniform sky dome
  albedo : base colour as emission        normal : shading normal as emission        depth : log view distance (R), material flag (G)
Usage: world.py -- <world> <pass> <spp>     ->  SCR/plates/<world>_<pass>.png  (16 bit, Raw)
"""
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
WORLD, PASS, SPP = argv[0], argv[1], int(argv[2])
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world"
OUT = os.environ.get("PLATES", os.path.join(SCR, "plates")); os.makedirs(OUT, exist_ok=True)
RES = int(os.environ.get("RES", 2160))
FOV = 24.0
HORIZ = 0.60                       # horizon at this fraction of the plate height from the top
f32 = np.float32
rng = np.random.default_rng(abs(hash(WORLD)) % 1000 if False else sum(map(ord, WORLD)))

# ------------------------------------------------------------------------------------------------ noise helpers
def fbm2(n, seed, beta=2.0, lo=0.0):
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None] * n; fx = np.fft.rfftfreq(n)[None, :] * n
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    amp = f ** (-beta); amp[0, 0] = 0          # beta = amplitude exponent: 2 is smooth, 1.6 rough
    if lo: amp[f < lo] = 0
    z = np.fft.irfft2(amp * np.exp(1j * r.uniform(0, 2 * np.pi, amp.shape)), s=(n, n))
    return ((z - z.mean()) / z.std()).astype(f32)
_tiles = {}
def tile(seed, beta=2.0, lo=0.0):
    k = (seed, beta, lo)
    if k not in _tiles: _tiles[k] = fbm2(1024, seed, beta, lo)
    return _tiles[k]
def samp(T, x, y, L):
    n = T.shape[0]; u = (x / L * n) % n; v = (y / L * n) % n
    i = np.floor(u).astype(np.int32); j = np.floor(v).astype(np.int32); fu = (u - i).astype(f32); fv = (v - j).astype(f32)
    i %= n; j %= n; i1 = (i + 1) % n; j1 = (j + 1) % n
    return (T[j, i] * (1 - fu) + T[j, i1] * fu) * (1 - fv) + (T[j1, i] * (1 - fu) + T[j1, i1] * fu) * fv
def N(seed, x, y, L, beta=2.0, lo=0.0): return samp(tile(seed, beta, lo), x, y, L)
_rt = np.random.default_rng(99).random((3, 65536)).astype(f32)
def cell(x, y, L, seed=0):
    """jittered-grid Voronoi: returns F1, F2 (in metres) and a random id per cell"""
    gx = x / L; gy = y / L; ix = np.floor(gx).astype(np.int64); iy = np.floor(gy).astype(np.int64)
    F1 = np.full(gx.shape, 9.0, f32); F2 = F1.copy(); ID = np.zeros(gx.shape, f32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx = ix + dx; cy = iy + dy; h = (cx * 7919 + cy * 104729 + seed * 31337) & 65535
            d = np.hypot(gx - (cx + _rt[0][h]), gy - (cy + _rt[1][h])).astype(f32)
            new1 = d < F1
            F2 = np.where(new1, F1, np.minimum(F2, d)); ID = np.where(new1, _rt[2][h], ID); F1 = np.where(new1, d, F1)
    return F1 * L, F2 * L, ID
def sm(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def mixc(c0, c1, t): return np.asarray(c0, f32) * (1 - t[..., None]) + np.asarray(c1, f32) * t[..., None]
def craters(X, Y, Z, n, ymin, ymax, amin, amax, seed, half=13.5, depth=0.2, rim=0.045, fresh=None):
    """stamp n bowl craters; angular radius log-uniform between amin and amax degrees (so every scale is seen on screen)"""
    r = np.random.default_rng(seed); out = []
    for _ in range(n):
        y = math.exp(r.uniform(math.log(ymin), math.log(ymax))); x = y * math.tan(math.radians(r.uniform(-half, half)))
        R = y * math.radians(math.exp(r.uniform(math.log(amin), math.log(amax))))
        m = (np.abs(X - x) < 3.2 * R) & (np.abs(Y - y) < 3.2 * R)
        if not m.any(): continue
        q = np.hypot(X[m] - x, Y[m] - y) / R
        age = r.uniform(0.35, 1.0)
        prof = np.where(q < 1, -depth + (depth + rim) * q ** 2.3, rim * np.clip(q, 1, None) ** -3.2 * (1 - sm(2.4, 3.2, q)))
        Z[m] += (prof * R * age).astype(f32); out.append((x, y, R, age))
    return out

# ------------------------------------------------------------------------------------------------ world recipes
# each returns: height(X, Y) -> Z, colour(X, Y, Z) ; plus parameters
P = dict(camh=1.8, y1=350.0, yfar=9000.0, n_near=1000, n_mid=600, far=None, sun_el=4.0, sun_ang=0.53, glow_el=10.0, glow_ang=60.0,
         cloud=False, bump=(0.9, 0.05), rough_tex=(9.0, 0.8), second_sun=None)
ROCKS = []        # (count, ymin, ymax, smin, smax, kind, sink, colour_lo, colour_hi, dust)
HOOK = {}

def w_mars():
    P.update(camh=1.9, y1=260, yfar=4200, far=(4200, 16000, 700), sun_ang=0.35)
    def height(X, Y):
        Z = 0.9 * N(1, X, Y, 900, 2.3) + 0.22 * N(2, X, Y, 90, 2.1) + 0.035 * N(3, X, Y, 9, 2.0) + 0.006 * N(4, X, Y, 0.9, 1.8)
        # wind ripples: warped sawtooth, crests across the view; fade where they would alias
        ph = (Y + 0.55 * N(5, X, Y, 30, 2.4) * 3 + 0.25 * X) / 2.3
        saw = (ph - np.floor(ph)); rip = np.where(saw < 0.72, saw / 0.72, (1 - saw) / 0.28) ** 1.3
        Z += 0.13 * rip * sm(220, 40, Y) * (0.35 + 0.65 * sm(-0.6, 0.6, N(6, X, Y, 60, 2.2) + 0.4))
        ph2 = (Y * 0.94 + 0.3 * X + N(5, X, Y, 4, 2.2) * 0.25) / 0.16
        Z += 0.006 * np.sin(2 * np.pi * ph2) * sm(40, 12, Y)
        # low mesas and buttes in the middle distance, the crater rim on the horizon
        me = sm(0.35, 0.75, N(7, X, Y, 2600, 2.0) * 0.6 + 0.25 * N(8, X, Y, 500, 2.0)) * sm(500, 1500, Y)
        Z += me * (26 + 6 * N(9, X, Y, 300, 1.8)) * sm(700, 2500, Y)
        rim = 1 - np.abs(N(10, X, Y, 9000, 2.0)) * 0.9
        Z += sm(4500, 9000, Y) * (150 * np.clip(rim, 0, 2) ** 1.6 + 60 * (1 - np.abs(N(11, X, Y, 1800, 1.9))) + 14 * N(12, X, Y, 400, 1.8)) * sm(16500, 12000, Y)
        return Z
    def colour(X, Y, Z):
        soil = np.array([0.50, 0.245, 0.11]); dark = np.array([0.30, 0.15, 0.085]); pale = np.array([0.62, 0.36, 0.19])
        t = sm(-1, 1, N(13, X, Y, 40, 2.0) + 0.6 * N(14, X, Y, 3, 1.8))
        c = mixc(dark, soil, t); c = mixc(c, pale, sm(0.3, 1.6, N(15, X, Y, 300, 2.2)))
        strata = 0.88 + 0.12 * np.sin(Z * 0.9 + 2 * N(16, X, Y, 900, 2.0)); c *= np.where(Z > 6, strata, 1)[..., None]
        return c * (0.9 + 0.1 * N(17, X, Y, 0.6, 1.6))[..., None]
    ROCKS.extend([(1500, 9, 420, 0.03, 0.55, "angular", 0.25, (0.085, 0.05, 0.04), (0.24, 0.13, 0.085), (0.5, 0.25, 0.115)),
                  (3000, 9, 70, 0.012, 0.07, "angular", 0.3, (0.085, 0.05, 0.04), (0.26, 0.14, 0.09), (0.5, 0.25, 0.115)),
                  (26, 14, 120, 0.5, 1.5, "angular", 0.3, (0.085, 0.05, 0.04), (0.22, 0.12, 0.08), (0.5, 0.25, 0.115))])
    return height, colour

def w_mercury():
    P.update(camh=9.0, y1=1200, yfar=5000, n_mid=400, far=(5000, 14000, 500), sun_ang=1.7, sun_el=3.2, bump=(1.0, 0.06), rough_tex=(5.0, 0.5))
    st = {}
    def height(X, Y):
        Z = 2.0 * N(21, X, Y, 1500, 2.4) + 0.25 * N(22, X, Y, 60, 2.2) + 0.03 * N(23, X, Y, 5, 2.0) + 0.007 * N(24, X, Y, 0.6, 1.9)
        Z = Z.astype(f32)
        craters(X, Y, Z, 22, 150, 4500, 1.5, 6.0, 5, depth=0.15)
        st["mid"] = craters(X, Y, Z, 300, 45, 5000, 0.2, 1.5, 6, depth=0.18)
        craters(X, Y, Z, 1800, 45, 1500, 0.03, 0.2, 7, depth=0.2)
        # a lobate scarp / crater wall on the horizon
        Z += sm(5200, 8500, Y) * (260 * np.clip(1 - np.abs(N(25, X, Y, 12000, 2.0)) * 0.8, 0, 2) ** 1.4 + 55 * (1 - np.abs(N(26, X, Y, 1500, 1.9))) + 10 * N(27, X, Y, 300, 1.8)) * sm(14500, 11000, Y)
        return Z
    def colour(X, Y, Z):
        a = np.array([0.20, 0.185, 0.17]); b = np.array([0.30, 0.285, 0.265]); br = np.array([0.42, 0.40, 0.38])
        c = mixc(a, b, sm(-1.2, 1.2, N(28, X, Y, 80, 2.1) + 0.5 * N(29, X, Y, 2, 1.7)))
        ray = np.zeros(X.shape, f32)
        for (x, y, R, age) in st.get("mid", [])[::7]:
            q = np.hypot(X - x, Y - y) / R
            ray = np.maximum(ray, np.exp(-((q - 1.1) / 1.6) ** 2) * (0.5 + 0.5 * np.sin(np.arctan2(Y - y, X - x) * 9 + x) ** 2) * (age > 0.8))
        return mixc(c, br, np.clip(ray, 0, 1) * 0.6) * (0.9 + 0.1 * N(30, X, Y, 0.5, 1.6))[..., None]
    ROCKS.extend([(2600, 46, 900, 0.10, 1.6, "angular", 0.3, (0.10, 0.095, 0.09), (0.30, 0.28, 0.26), None),
                  (22, 55, 300, 1.5, 4.0, "angular", 0.3, (0.10, 0.095, 0.09), (0.27, 0.25, 0.235), None)])
    return height, colour

def w_venus():
    P.update(camh=1.5, y1=240, yfar=7000, far=(7000, 26000, 500), sun_ang=40.0, sun_el=14.0, glow_el=16, glow_ang=70, bump=(1.2, 0.035), rough_tex=(14.0, 1.3))
    def height(X, Y):
        Z = 3.5 * N(41, X, Y, 2400, 2.5) + 0.12 * N(42, X, Y, 30, 2.2)
        # platy basalt: three scales of cracked slabs, each slab tilted and stepped a little
        for (L, amp, s) in ((6.0, 0.10, 1), (1.7, 0.05, 2), (0.45, 0.02, 3)):
            F1, F2, ID = cell(X + 0.3 * L * N(43 + s, X, Y, L * 4, 2.0), Y + 0.3 * L * N(46 + s, X, Y, L * 4, 2.0), L, s)
            fade = sm(L * 330, L * 110, Y)
            Z += fade * (amp * (ID - 0.5) * 2 + amp * 0.7 * (ID - 0.5) * (X % L) / L - amp * 1.6 * (1 - sm(0.0, 0.07 * L, F2 - F1)))
        Z += 0.012 * N(49, X, Y, 0.5, 1.7)
        Z += sm(3000, 9000, Y) * (420 * np.clip(N(50, X, Y, 30000, 2.6) * 0.5 + 0.5, 0, 2) ** 1.5 + 30 * N(51, X, Y, 3000, 2.2)) * sm(26500, 20000, Y)   # a shield volcano
        return Z
    def colour(X, Y, Z):
        slab = np.array([0.36, 0.33, 0.30]); dark = np.array([0.16, 0.145, 0.13]); soil = np.array([0.10, 0.09, 0.08])
        F1, F2, ID = cell(X + 0.3 * 1.7 * N(45, X, Y, 6.8, 2.0), Y + 0.3 * 1.7 * N(48, X, Y, 6.8, 2.0), 1.7, 2)
        c = mixc(dark, slab, np.clip(ID * 0.8 + 0.3 * N(52, X, Y, 12, 2.0) + 0.3, 0, 1))
        c = mixc(c, soil, (1 - sm(0.0, 0.12, F2 - F1)) * sm(400, 100, Y) * 0.85)
        c = mixc(c, soil, sm(0.2, 1.2, N(53, X, Y, 25, 2.2)) * 0.7)
        return c * (0.88 + 0.12 * N(54, X, Y, 0.4, 1.6))[..., None]
    ROCKS.extend([(1500, 7, 200, 0.03, 0.35, "slab", 0.3, (0.12, 0.11, 0.10), (0.34, 0.31, 0.28), None)])
    return height, colour

def w_titan():
    P.update(camh=2.2, y1=200, yfar=1500, n_mid=300, sun_ang=30.0, sun_el=6.0, glow_el=7, glow_ang=45, bump=(0.5, 0.02), rough_tex=(20.0, 2.0))
    def shore(X, Y): return 42 + 1.5 * X + 5 * N(61, X, Y * 0 + 3.0, 160, 2.3) + 1.6 * N(62, X, Y * 0 + 7.0, 22, 2.1)      # distance of the waterline
    def height(X, Y):
        d = shore(X, Y) - Y                       # > 0 on the beach
        Z = np.clip(d, -40, 60) * 0.022 + 0.03 * N(63, X, Y, 12, 2.2) + 0.006 * N(64, X, Y, 0.8, 1.8) - 0.02
        Z += 0.015 * np.sin((d + 1.5 * N(65, X, Y, 9, 2.0)) * 2.4) * sm(0.2, 3, d) * sm(14, 6, d)      # strand lines left by a falling sea
        # far side of the bay: low rounded hills, only on the left
        Z += sm(700, 1300, Y) * sm(0.15, -0.5, X / np.maximum(Y, 1) * 4 + 0.35 * N(66, X, Y, 4000, 2.0)) * (14 + 10 * N(67, X, Y, 700, 2.2) + 3 * N(68, X, Y, 120, 2.0))
        return Z
    def colour(X, Y, Z):
        d = shore(X, Y) - Y
        dry = np.array([0.40, 0.25, 0.11]); wet = np.array([0.10, 0.06, 0.03]); pale = np.array([0.55, 0.38, 0.19])
        c = mixc(wet, dry, sm(0.3, 4.5, d + 0.8 * N(69, X, Y, 5, 2.0))); c = mixc(c, pale, sm(0.4, 1.5, N(70, X, Y, 14, 2.0)) * sm(3, 8, d) * 0.6)
        return c * (0.9 + 0.1 * N(71, X, Y, 0.3, 1.6))[..., None]
    ROCKS.extend([(6500, 10, 80, 0.025, 0.17, "round", 0.3, (0.20, 0.13, 0.07), (0.62, 0.45, 0.25), None),
                  (90, 10, 60, 0.15, 0.45, "round", 0.3, (0.3, 0.2, 0.1), (0.62, 0.45, 0.25), None)])
    HOOK["sea"] = 0.0; HOOK["rock_ok"] = lambda x, y: (42 + 1.5 * x) - y > -4.0
    return height, colour

def w_pluto():
    P.update(camh=2.0, y1=320, yfar=9000, far=(9000, 42000, 950), sun_ang=0.02, sun_el=3.5, bump=(0.7, 0.04), rough_tex=(7.0, 0.5))
    def height(X, Y):
        Z = 1.2 * N(81, X, Y, 2500, 2.4) + 0.10 * N(82, X, Y, 40, 2.2)
        # nitrogen-ice plain: sublimation pits in rows, shallow troughs between convection cells
        F1, F2, ID = cell(X, Y * 0.6, 9.0, 4); pit = sm(3.2, 0.6, F1) * sm(0.3, 0.6, ID)
        Z -= 0.55 * pit * sm(1500, 300, Y)
        F1b, F2b, IDb = cell(X + 0.6 * N(83, X, Y, 8, 2.0), Y * 0.7, 1.5, 5)
        Z -= 0.10 * sm(0.5, 0.1, F1b) * sm(200, 60, Y) * sm(0.2, 0.5, IDb)
        Fa, Fb, _ = cell(X + 300 * N(84, X, Y, 6000, 2.0), Y + 300 * N(85, X, Y, 6000, 2.0), 2600, 6)
        Z -= 5.0 * (1 - sm(0, 90, Fb - Fa)) + 1.2 * (1 - sm(0, 260, Fb - Fa))
        # scalloped wind / sublimation texture
        Z += 0.035 * np.abs(N(86, X, Y * 0.5, 2.2, 2.0)) * sm(120, 30, Y) + 0.004 * N(87, X, Y, 0.4, 1.7)
        # water-ice mountains: jumbled angular blocks kilometres high
        mt = sm(9500, 17000, Y) * sm(42500, 36000, Y)
        r1 = 1 - np.abs(N(88, X, Y, 14000, 1.9)); r2 = 1 - np.abs(N(89, X, Y, 3500, 1.8)); r3 = 1 - np.abs(N(90, X, Y, 800, 1.7))
        Fc, Fd, IDc = cell(X + 400 * N(91, X, Y, 5000, 2.0), Y, 3200, 8)
        blocks = (0.35 + IDc) * sm(0, 500, Fd - Fc)
        Z += mt * np.clip(0.2 + 0.8 * N(92, X, Y, 30000, 2.2) + 0.5, 0.15, 2) * (1500 * np.clip(r1, 0, 1) ** 1.5 * (0.5 + 0.7 * blocks) + 520 * r2 * r1 + 110 * r3 * r1 + 25 * N(93, X, Y, 150, 1.8))
        return Z
    def colour(X, Y, Z):
        n2 = np.array([0.80, 0.76, 0.70]); cream = np.array([0.74, 0.62, 0.50]); red = np.array([0.36, 0.17, 0.10]); h2o = np.array([0.62, 0.64, 0.68])
        c = mixc(n2, cream, sm(-0.5, 1.5, N(94, X, Y, 600, 2.2) + 0.4 * N(95, X, Y, 6, 1.9)))
        mt = sm(9500, 13000, Y)
        rock = mixc(red, h2o, sm(150, 1300, Z + 300 * N(96, X, Y, 4000, 2.0)))
        rock = mixc(rock, n2, sm(1500, 2600, Z + 400 * N(97, X, Y, 2500, 2.0)) * 0.8)     # methane / nitrogen frost on the summits
        c = mixc(c, rock, mt * sm(15, 120, Z))
        return c * (0.92 + 0.08 * N(98, X, Y, 0.5, 1.6))[..., None]
    ROCKS.extend([(700, 10, 500, 0.05, 0.7, "angular", 0.35, (0.50, 0.53, 0.60), (0.80, 0.82, 0.86), None),
                  (14, 18, 160, 0.7, 2.2, "angular", 0.3, (0.50, 0.53, 0.60), (0.78, 0.80, 0.85), None)])
    return height, colour

def w_kepler():
    P.update(camh=1.8, y1=300, yfar=6000, far=(6000, 20000, 500), sun_ang=0.49, sun_el=3.4, bump=(0.8, 0.03), rough_tex=(10.0, 0.9),
             second_sun=dict(el=2.2, az=-2.3, ang=0.17))
    def height(X, Y):
        Z = 0.5 * N(101, X, Y, 1200, 2.4) + 0.03 * N(102, X, Y, 15, 2.1)
        for (L, amp, s) in ((7.0, 0.11, 11), (1.4, 0.035, 12)):                 # dried, cracked playa: raised polygon rims, sunken cracks
            F1, F2, ID = cell(X + 0.25 * L * N(103 + s, X, Y, L * 3, 2.0), Y + 0.25 * L * N(105 + s, X, Y, L * 3, 2.0), L, s)
            e = F2 - F1; fade = sm(L * 300, L * 90, Y)
            Z += fade * (amp * 0.6 * sm(0.30 * L, 0.06 * L, e) - amp * 2.2 * sm(0.035 * L, 0.0, e))
        Z += 0.004 * N(107, X, Y, 0.3, 1.7)
        mesa = sm(0.25, 0.5, N(108, X, Y, 9000, 2.0) * 0.5 + 0.3 * N(109, X, Y, 1500, 1.9)) * sm(5500, 8000, Y) * sm(20500, 17000, Y)
        Z += mesa * (330 + 60 * N(110, X, Y, 2500, 2.0)) + sm(5500, 8000, Y) * 30 * (1 - np.abs(N(111, X, Y, 1200, 1.9))) * sm(20500, 17000, Y)
        return Z
    def colour(X, Y, Z):
        a = np.array([0.50, 0.44, 0.40]); b = np.array([0.66, 0.60, 0.55]); crack = np.array([0.12, 0.10, 0.10]); red = np.array([0.36, 0.20, 0.15])
        F1, F2, ID = cell(X + 0.25 * 7 * N(114, X, Y, 21, 2.0), Y + 0.25 * 7 * N(116, X, Y, 21, 2.0), 7.0, 11)
        c = mixc(a, b, np.clip(ID * 0.7 + 0.3 * N(112, X, Y, 60, 2.0) + 0.2, 0, 1)); c = mixc(c, crack, sm(0.3, 0.0, F2 - F1) * sm(900, 300, Y) * 0.8)
        strata = 0.8 + 0.2 * np.sin(Z * 0.07 + 2 * N(113, X, Y, 3000, 2.0))
        c = mixc(c, red * strata[..., None], sm(8, 40, Z))
        return c * (0.92 + 0.08 * N(117, X, Y, 0.4, 1.6))[..., None]
    ROCKS.extend([(900, 9, 300, 0.03, 0.4, "angular", 0.3, (0.10, 0.08, 0.08), (0.30, 0.22, 0.19), None),
                  (34, 25, 420, 2.2, 7.5, "spire", 0.1, (0.16, 0.10, 0.09), (0.36, 0.22, 0.17), None)])
    return height, colour

def w_earth():
    # the sea itself is shaded analytically in the compositor (waves, Fresnel, glitter); Blender provides the wet rock reef and sea stacks
    P.update(camh=3.0, y1=300, yfar=900, n_mid=200, sun_ang=0.53, sun_el=3.0, bump=(1.0, 0.05), rough_tex=(8.0, 0.8))
    def lump(X, Y, x, y, rx, ry): return np.exp(-(((X - x) / rx) ** 2 + ((Y - y) / ry) ** 2) ** 1.5)
    def height(X, Y):
        # wave-cut rock platform at the lower corners: flat-topped, stepped along bedding planes, with tide pools
        reef = lump(X, Y, -5.2, 19, 3.6, 7) + lump(X, Y, 6.4, 24, 3.4, 9) + lump(X, Y, -11, 42, 5, 14) * 0.9 + lump(X, Y, 14, 58, 6, 18) * 0.8
        reef = np.clip(reef + 0.18 * N(121, X, Y, 6, 1.9) * (reef > 0.02), 0, 1.2)
        step = np.floor(reef * 3.2 + 0.4 * N(122, X, Y, 7, 2.0)) / 3.2
        top = 0.75 * sm(0.0, 0.25, reef) * (0.35 + 0.65 * np.clip(step, 0, 1)) + 0.05 * N(123, X, Y, 1.2, 1.8) + 0.012 * N(124, X, Y, 0.2, 1.7)
        return -1.2 + sm(0.02, 0.2, reef) * 1.25 + top * sm(0.05, 0.3, reef)
    def colour(X, Y, Z):
        a = np.array([0.05, 0.045, 0.04]); b = np.array([0.14, 0.12, 0.10]); weed = np.array([0.05, 0.07, 0.03])
        c = mixc(a, b, sm(-1, 1, N(124, X, Y, 1.5, 1.9) + 0.5 * N(125, X, Y, 12, 2.0)))
        return mixc(c, weed, sm(0.45, 0.05, Z) * 0.7 * sm(-0.5, 0.5, N(126, X, Y, 4, 2.0)))
    ROCKS.extend([(6, 260, 900, 9, 20, "stack", 0.0, (0.04, 0.035, 0.03), (0.13, 0.11, 0.09), None),
                  (90, 12, 70, 0.12, 0.55, "boulder", 0.4, (0.04, 0.035, 0.03), (0.14, 0.12, 0.10), None)])
    HOOK["sea"] = 0.0; HOOK["rock_ok"] = lambda x, y: (y > 120 and abs(x / y) > 0.05) or (y < 80 and abs(x / y) > 0.14)
    return height, colour

def clouds(kind):
    """cloud-top 'terrain' for the giant planets. Units are metres; the camera floats a few km above the deck.
    Clouds are as tall as they are wide: cauliflower billows (|noise| at four scales) on convective towers and a stratiform floor."""
    def billow(X, Y, seeds, Ls, amps, squash=1.0):
        out = 0
        for sd, L, a in zip(seeds, Ls, amps): out = out + a * np.abs(N(sd, X * squash, Y, L, 1.75))
        return out
    def w():
        if kind == "jupiter":
            P.update(camh=4500.0, y1=6e5, yfar=2.6e6, n_near=1300, n_mid=450, cloud=True, sun_ang=0.102, sun_el=5.0, glow_el=13, bump=(0.5, 120.0), rough_tex=(0.004, 0.0006))
            def height(X, Y):
                cov = N(134, X, Y, 2.4e5, 2.1) + 0.45 * N(135, X, Y, 6e4, 1.9)                      # where convection breaks through
                tow = sm(0.25, 1.25, cov) ** 0.6; anv = sm(1.2, 1.9, cov)
                bil = billow(X, Y, (131, 132, 133, 130), (3.6e4, 1.1e4, 3200, 900), (2600, 1100, 380, 110))
                floor = -5200 + 0.35 * bil + 900 * N(136, X * 0.2, Y, 2.5e5, 2.2)
                top = -1200 + tow * (6500 + 2500 * N(137, X, Y, 1.2e5, 2.0)) + bil * (0.35 + 0.65 * tow) - anv * 0.5 * bil
                Z = np.maximum(floor, floor + (top - floor) * tow)
                return np.minimum(Z, P["camh"] - 600 + 3200 * sm(4e4, 2.5e5, Y)) * sm(1.0e4, 2.6e4, Y) + (-5200) * (1 - sm(1.0e4, 2.6e4, Y))
            def colour(X, Y, Z):
                cream = np.array([0.88, 0.82, 0.70]); och = np.array([0.74, 0.54, 0.34]); rust = np.array([0.52, 0.30, 0.19]); wh = np.array([0.96, 0.95, 0.92])
                band = N(138, X * 0.05, Y, 6e5, 2.2)
                c = mixc(cream, och, sm(-0.6, 0.8, band + 0.3 * N(139, X, Y, 5e4, 2.0))); c = mixc(c, rust, sm(0.6, 1.8, band) * 0.8)
                return mixc(c, wh, sm(-2500, 2500, Z))
            return height, colour
        if kind == "saturn":
            P.update(camh=3800.0, y1=6e5, yfar=3.2e6, n_near=1300, n_mid=450, cloud=True, sun_ang=0.055, sun_el=5.0, glow_el=13, bump=(0.4, 100.0), rough_tex=(0.003, 0.0005))
            def height(X, Y):
                # ammonia-ice haze deck: long soft rolls stretched east-west, with low cumulus heads pushing through here and there
                rolls = billow(X, Y, (141, 142, 143), (5.5e4, 1.4e4, 3500), (2300, 800, 230), squash=0.35)
                cov = sm(0.5, 1.5, N(145, X, Y, 3.0e5, 2.1) + 0.4 * N(146, X, Y, 5e4, 1.9)) ** 0.7
                heads = cov * (3800 + billow(X, Y, (147, 148, 149), (2.2e4, 6000, 1500), (2400, 800, 220)))
                Z = -4600 + rolls + heads + 1200 * N(144, X * 0.2, Y, 5e5, 2.3)
                return np.minimum(Z, P["camh"] - 600 + 3000 * sm(4e4, 2.5e5, Y)) * sm(1.0e4, 2.4e4, Y) + (-4600) * (1 - sm(1.0e4, 2.4e4, Y))
            def colour(X, Y, Z):
                gold = np.array([0.84, 0.72, 0.48]); pale = np.array([0.93, 0.87, 0.72]); tan = np.array([0.68, 0.54, 0.36])
                c = mixc(gold, tan, sm(-0.5, 1.2, N(150, X * 0.05, Y, 7e5, 2.2))); return mixc(c, pale, sm(-3500, 500, Z))
            return height, colour
        P.update(camh=3200.0, y1=6e5, yfar=3.0e6, n_near=1300, n_mid=450, cloud=True, sun_ang=0.028, sun_el=4.5, glow_el=12, bump=(0.35, 80.0), rough_tex=(0.003, 0.0005))
        def height(X, Y):
            # methane-ice cloud field: closed convection cells (a mackerel sky seen from above) over smooth haze, in streets
            F1, F2, ID = cell(X + 3000 * N(151, X, Y, 4e4, 2.0), Y + 3000 * N(152, X, Y, 4e4, 2.0), 9000, 21)
            dome = np.sqrt(np.clip(sm(0.0, 3800, F2 - F1), 0, 1)) * (0.45 + 0.55 * ID)
            cov = sm(-0.5, 0.5, N(153, X * 0.3, Y, 3.5e5, 2.2) + 0.3 * N(158, X, Y, 6e4, 2.0))
            Z = -3600 + cov * (2600 * dome + 500 * np.abs(N(154, X, Y, 2600, 1.8)) + 150 * np.abs(N(159, X, Y, 700, 1.7))) + 700 * N(155, X, Y, 8e5, 2.4) + 250 * N(156, X * 0.3, Y, 3e4, 2.1)
            return Z * sm(1.0e4, 2.2e4, Y) + (-3600) * (1 - sm(1.0e4, 2.2e4, Y))
        def colour(X, Y, Z):
            teal = np.array([0.52, 0.80, 0.82]); deep = np.array([0.30, 0.62, 0.70]); wh = np.array([0.88, 0.96, 0.97])
            c = mixc(deep, teal, sm(-1, 1, N(157, X, Y, 6e5, 2.3))); return mixc(c, wh, sm(-3300, -1500, Z))
        return height, colour
    return w

RECIPE = dict(mars=w_mars, mercury=w_mercury, venus=w_venus, titan=w_titan, pluto=w_pluto, kepler=w_kepler, earth=w_earth,
              jupiter=clouds("jupiter"), saturn=clouds("saturn"), uranus=clouds("uranus"))
height, colour = RECIPE[WORLD]()
CAMH = P["camh"]

# ------------------------------------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = SPP
sc.cycles.use_denoising = PASS == "beauty"; sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 2; sc.cycles.diffuse_bounces = 0; sc.cycles.glossy_bounces = 0; sc.cycles.transmission_bounces = 1
sc.cycles.transparent_max_bounces = 2; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.view_settings.view_transform = "Raw"; sc.view_settings.look = "None"
sc.render.film_transparent = True; sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"; sc.cycles.filter_width = 1.5
sc.render.image_settings.media_type = "IMAGE"; sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"; sc.render.image_settings.color_depth = "16"; sc.render.image_settings.compression = 30
sc.render.resolution_x = sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
sc.render.threads_mode = "FIXED"; sc.render.threads = int(os.environ.get("THREADS", 2))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0, 0, 1, 1); bg.inputs[1].default_value = 0.85 if PASS == "beauty" else 0.0
def link(ob): sc.collection.objects.link(ob); return ob

# ---- fan grid: rows uniform in screen angle near the camera, then logarithmic, then (optionally) a dense far patch
half = math.radians(13.6); NU = int(os.environ.get("NU", 1200))
bot = math.atan(math.tan(math.radians(FOV / 2)) * (2 * (1 - HORIZ) + 0.06))          # depression angle of the bottom edge (+ margin)
a1 = math.atan(CAMH / P["y1"])
rows = [CAMH / np.tan(np.linspace(bot, a1, P["n_near"], endpoint=False))]
rows.append(np.exp(np.linspace(math.log(P["y1"]), math.log(P["yfar"]), P["n_mid"], endpoint=P["far"] is None)))
if P["far"]: rows.append(np.linspace(P["far"][0], P["far"][1], P["far"][2]))
YR = np.concatenate(rows).astype(np.float64); NV = len(YR)
TH = np.tan(np.linspace(-half, half, NU))
X = (YR[:, None] * TH[None, :]); Y = np.broadcast_to(YR[:, None], X.shape).copy()
Z = height(X, Y).astype(np.float64)
z0 = float(height(np.zeros((1, 1)), np.full((1, 1), YR[0])).ravel()[0])
col = np.clip(colour(X, Y, Z), 0, 1)
print(WORLD, "grid", NU, NV, "z range", Z.min(), Z.max(), "ynear", YR[0], flush=True)

def make_mesh(name, X, Y, Z, col, smooth=True):
    nv, nu = X.shape
    me = bpy.data.meshes.new(name)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).astype(np.float32)
    idx = np.arange(nv * nu, dtype=np.int32).reshape(nv, nu)
    faces = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me.vertices.add(nv * nu); me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(faces.size); me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(len(faces)); me.polygons.foreach_set("loop_start", np.arange(0, faces.size, 4, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(len(faces), 4, np.int32))
    me.update()
    me.polygons.foreach_set("use_smooth", np.full(len(faces), smooth, bool))
    rgba = np.concatenate([col.reshape(-1, 3), np.ones((nv * nu, 1))], 1).astype(np.float32)
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT"); ca.data.foreach_set("color", rgba.ravel())
    return link(bpy.data.objects.new(name, me))
terr = make_mesh("terrain", X, Y, Z, col)

# ------------------------------------------------------------------------------------------------ materials
DMAX = (P["far"][1] if P["far"] else P["yfar"]) * 1.3
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True; t = m.node_tree
    for n in list(t.nodes): t.nodes.remove(n)
    return m, t, t.nodes.new("ShaderNodeOutputMaterial")
def emit(t, out, sock):
    em = t.nodes.new("ShaderNodeEmission"); t.links.new(sock, em.inputs[0]); t.links.new(em.outputs[0], out.inputs[0])
def depth_nodes(t, out, flag):
    cd = t.nodes.new("ShaderNodeCameraData")
    a = t.nodes.new("ShaderNodeMath"); a.operation = "DIVIDE"; a.inputs[1].default_value = CAMH; t.links.new(cd.outputs["View Distance"], a.inputs[0])
    b = t.nodes.new("ShaderNodeMath"); b.operation = "ADD"; b.inputs[1].default_value = 1.0; t.links.new(a.outputs[0], b.inputs[0])
    c = t.nodes.new("ShaderNodeMath"); c.operation = "LOGARITHM"; c.inputs[1].default_value = math.e; t.links.new(b.outputs[0], c.inputs[0])
    d = t.nodes.new("ShaderNodeMath"); d.operation = "DIVIDE"; d.inputs[1].default_value = math.log(1 + DMAX / CAMH); t.links.new(c.outputs[0], d.inputs[0])
    cmb = t.nodes.new("ShaderNodeCombineColor"); t.links.new(d.outputs[0], cmb.inputs[0]); cmb.inputs[1].default_value = flag; cmb.inputs[2].default_value = 0
    emit(t, out, cmb.outputs[0])
def normal_nodes(t, out):
    g = t.nodes.new("ShaderNodeNewGeometry"); v = t.nodes.new("ShaderNodeVectorMath"); v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = (0.5, 0.5, 0.5); v.inputs[2].default_value = (0.5, 0.5, 0.5); t.links.new(g.outputs["Normal"], v.inputs[0]); emit(t, out, v.outputs[0])
def bump_nodes(t, coords="Object", scale=(9.0, 0.8), strength=0.9, dist=0.05, fade=True):
    tc = t.nodes.new("ShaderNodeTexCoord")
    n1 = t.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = scale[0]; n1.inputs["Detail"].default_value = 8; n1.inputs["Roughness"].default_value = 0.65
    n2 = t.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = scale[1]; n2.inputs["Detail"].default_value = 10; n2.inputs["Roughness"].default_value = 0.6
    t.links.new(tc.outputs[coords], n1.inputs["Vector"]); t.links.new(tc.outputs[coords], n2.inputs["Vector"])
    b1 = t.nodes.new("ShaderNodeBump"); b1.inputs["Distance"].default_value = dist; t.links.new(n1.outputs[0], b1.inputs["Height"])
    b2 = t.nodes.new("ShaderNodeBump"); b2.inputs["Distance"].default_value = dist * 8; b2.inputs["Strength"].default_value = strength * 0.8
    t.links.new(n2.outputs[0], b2.inputs["Height"]); t.links.new(b1.outputs[0], b2.inputs["Normal"])
    if fade:      # the fine layer fades out with distance (it would only alias)
        cd = t.nodes.new("ShaderNodeCameraData"); mr = t.nodes.new("ShaderNodeMapRange")
        mr.inputs[1].default_value = 20 * CAMH; mr.inputs[2].default_value = 150 * CAMH; mr.inputs[3].default_value = strength; mr.inputs[4].default_value = 0.0
        t.links.new(cd.outputs["View Distance"], mr.inputs[0]); t.links.new(mr.outputs[0], b1.inputs["Strength"])
    else: b1.inputs["Strength"].default_value = strength
    return b2.outputs[0]
def white_shader(t, out, normal, cloud=False):
    d = t.nodes.new("ShaderNodeBsdfDiffuse"); d.inputs["Color"].default_value = (1, 1, 1, 1); t.links.new(normal, d.inputs["Normal"])
    if not cloud: t.links.new(d.outputs[0], out.inputs[0]); return
    tr = t.nodes.new("ShaderNodeBsdfTranslucent"); tr.inputs["Color"].default_value = (1, 1, 1, 1); t.links.new(normal, tr.inputs["Normal"])
    mx = t.nodes.new("ShaderNodeMixShader"); mx.inputs[0].default_value = 0.42; t.links.new(d.outputs[0], mx.inputs[1]); t.links.new(tr.outputs[0], mx.inputs[2])
    t.links.new(mx.outputs[0], out.inputs[0])

def terrain_mat():
    m, t, out = new_mat("terrain")
    if PASS == "beauty":
        white_shader(t, out, bump_nodes(t, "Object", P["rough_tex"], P["bump"][0], P["bump"][1]), P["cloud"])
    elif PASS == "albedo":
        vc = t.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
        tc = t.nodes.new("ShaderNodeTexCoord"); n = t.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = P["rough_tex"][0] * 0.6; n.inputs["Detail"].default_value = 10; n.inputs["Roughness"].default_value = 0.7
        t.links.new(tc.outputs["Object"], n.inputs["Vector"])
        cd = t.nodes.new("ShaderNodeCameraData"); mr = t.nodes.new("ShaderNodeMapRange")       # mottling 0.72..1.25 near, flat far away
        mr.inputs[1].default_value = 20 * CAMH; mr.inputs[2].default_value = 200 * CAMH; mr.inputs[3].default_value = 1.0; mr.inputs[4].default_value = 0.0
        t.links.new(cd.outputs["View Distance"], mr.inputs[0])
        a = t.nodes.new("ShaderNodeMath"); a.operation = "MULTIPLY_ADD"; a.inputs[1].default_value = 0.9; a.inputs[2].default_value = -0.45; t.links.new(n.outputs[0], a.inputs[0])
        b = t.nodes.new("ShaderNodeMath"); b.operation = "MULTIPLY_ADD"; b.inputs[2].default_value = 1.0; t.links.new(a.outputs[0], b.inputs[0]); t.links.new(mr.outputs[0], b.inputs[1])
        mul = t.nodes.new("ShaderNodeVectorMath"); mul.operation = "SCALE"; t.links.new(vc.outputs["Color"], mul.inputs[0]); t.links.new(b.outputs[0], mul.inputs["Scale"])
        emit(t, out, mul.outputs[0])
    elif PASS == "normal": normal_nodes(t, out)
    else: depth_nodes(t, out, 0.0)
    return m
terr.data.materials.append(terrain_mat())

def rock_mat(name, lo, hi, dust, flag=0.5):
    m, t, out = new_mat(name)
    if PASS == "beauty":
        white_shader(t, out, bump_nodes(t, "Object", (7.0, 1.6), 0.9, 0.06, fade=False))
    elif PASS == "albedo":
        tc = t.nodes.new("ShaderNodeTexCoord"); n = t.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.5; n.inputs["Detail"].default_value = 10; n.inputs["Roughness"].default_value = 0.7
        oi = t.nodes.new("ShaderNodeObjectInfo"); ad = t.nodes.new("ShaderNodeVectorMath"); ad.operation = "ADD"
        t.links.new(tc.outputs["Object"], ad.inputs[0]); t.links.new(oi.outputs["Random"], ad.inputs[1]); t.links.new(ad.outputs[0], n.inputs["Vector"])
        mx0 = t.nodes.new("ShaderNodeMath"); mx0.operation = "MULTIPLY_ADD"; mx0.inputs[1].default_value = 0.7; t.links.new(n.outputs[0], mx0.inputs[0])
        r0 = t.nodes.new("ShaderNodeMath"); r0.operation = "MULTIPLY_ADD"; r0.inputs[1].default_value = 0.5; r0.inputs[2].default_value = -0.1; t.links.new(oi.outputs["Random"], r0.inputs[0]); t.links.new(r0.outputs[0], mx0.inputs[2])
        ramp = t.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.2; ramp.color_ramp.elements[0].color = (*lo, 1); ramp.color_ramp.elements[1].position = 0.8; ramp.color_ramp.elements[1].color = (*hi, 1)
        t.links.new(mx0.outputs[0], ramp.inputs[0]); sock = ramp.outputs[0]
        if dust is not None:                      # dust settles on up-facing surfaces
            g = t.nodes.new("ShaderNodeNewGeometry"); sx = t.nodes.new("ShaderNodeSeparateXYZ"); t.links.new(g.outputs["Normal"], sx.inputs[0])
            mr = t.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.35; mr.inputs[2].default_value = 0.95; mr.inputs[3].default_value = 0.0; mr.inputs[4].default_value = 0.55
            t.links.new(sx.outputs["Z"], mr.inputs[0])
            mx = t.nodes.new("ShaderNodeMixRGB"); mx.inputs[2].default_value = (*dust, 1); t.links.new(mr.outputs[0], mx.inputs[0]); t.links.new(sock, mx.inputs[1]); sock = mx.outputs[0]
        emit(t, out, sock)
    elif PASS == "normal": normal_nodes(t, out)
    else: depth_nodes(t, out, flag)
    return m

# ------------------------------------------------------------------------------------------------ rocks
def stack_mesh(name, seed):
    """sea stack: a jointed column with bedding ledges, a wave notch at the foot and a broken top (unit radius, height ~2-3)"""
    r = np.random.default_rng(seed); nt, nh, ncap = 260, 300, 26
    th = np.linspace(0, 2 * np.pi, nt, endpoint=False); hh = np.linspace(0, 1, nh)
    k = r.integers(6, 9); phi = np.sort(r.uniform(0, 2 * np.pi, k)); dd = r.uniform(0.62, 1.0, k)
    prof = np.min(dd[None, :] / np.maximum(np.cos(th[:, None] - phi[None, :]), 0.08), axis=1); prof = np.minimum(prof, 1.25)
    def n1(x, f, sd):
        rr = np.random.default_rng(sd); o = np.zeros_like(x)
        for j in range(6): o += np.sin(x * f * (j + 1) * rr.uniform(0.7, 1.3) + rr.uniform(0, 6.28)) / (j + 1)
        return o
    Hh = r.uniform(2.2, 3.4); lean = r.uniform(-0.12, 0.12)
    T, Hg = np.meshgrid(th, hh)
    bed = Hg * r.uniform(15, 22) + 0.5 * np.sin(T * 2 + seed) + 0.25 * n1(T, 1.0, seed + 1)[None, :] if False else Hg * r.uniform(15, 22) + 0.5 * np.sin(T * 2 + seed)
    ledge = (bed - np.floor(bed)); ledge = np.where(ledge < 0.82, 0.0, -1.0) + 0.35 * (np.floor(bed) % 3 == 0)
    joints = n1(T, 5.0, seed + 2) * 0.035 + (np.abs(np.sin(T * r.integers(5, 9) + n1(Hg, 3.0, seed + 3))) < 0.08) * -0.05
    taper = 1 - 0.30 * Hg ** 1.6 + 0.10 * np.sin(Hg * 5 + seed)
    notch = 1 - 0.16 * np.exp(-((Hg - 0.05) / 0.035) ** 2) + 0.25 * np.exp(-Hg / 0.02)
    rad = prof[None, :] * taper * notch * (1 + 0.045 * ledge + joints + 0.02 * n1(T * 3 + Hg * 40, 1.0, seed + 4))
    ztop = Hh * (1 + 0.10 * n1(th, 1.0, seed + 5) + 0.05 * (np.abs(n1(th, 3.0, seed + 6)) > 0.6))
    Zs = Hg * ztop[None, :]
    Xs = rad * np.cos(T) + lean * Zs; Ys = rad * np.sin(T)
    rings = [np.stack([Xs, Ys, Zs], -1)]
    cap = []
    for j in range(1, ncap + 1):
        q = 1 - j / ncap
        cap.append(np.stack([Xs[-1] * q + lean * ztop.mean() * (1 - q) * 0, Ys[-1] * q, Zs[-1] + (1 - q) ** 2 * 0.05 * Hh * (1 + 0.5 * n1(th * 2 + j, 1.0, seed + 7))], -1))
    V = np.concatenate([rings[0], np.stack(cap, 0)], 0); nv = V.shape[0]
    idx = np.arange(nv * nt, dtype=np.int32).reshape(nv, nt); nx = np.roll(idx, -1, axis=1)
    faces = np.stack([idx[:-1].ravel(), nx[:-1].ravel(), nx[1:].ravel(), idx[1:].ravel()], 1)
    me = bpy.data.meshes.new(name); me.vertices.add(nv * nt); me.vertices.foreach_set("co", V.reshape(-1, 3).astype(np.float32).ravel())
    me.loops.add(faces.size); me.loops.foreach_set("vertex_index", faces.ravel()); me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.arange(0, faces.size, 4, dtype=np.int32)); me.polygons.foreach_set("loop_total", np.full(len(faces), 4, np.int32)); me.update()
    me.polygons.foreach_set("use_smooth", np.full(len(faces), True, bool))
    return me

def base_rock(name, seed, kind):
    r = np.random.default_rng(seed)
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=5 if kind in ("stack", "spire") else 4, radius=1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    v = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", v); d = v.reshape(-1, 3); d /= np.linalg.norm(d, axis=1, keepdims=True)
    def lumps(k, f):
        out = np.zeros(len(d))
        for _ in range(k):
            kv = r.normal(size=3) * f; out += np.sin(d @ kv + r.uniform(0, 6.28))
        return out / math.sqrt(k)
    if kind in ("angular", "slab", "stack", "spire", "boulder"):
        npl = dict(angular=16, slab=12, stack=26, spire=22, boulder=30)[kind]
        nn = r.normal(size=(npl, 3)); nn /= np.linalg.norm(nn, axis=1, keepdims=True); dd = r.uniform(0.55, 0.98, npl)
        if kind == "boulder": dd = r.uniform(0.8, 1.0, npl)
        rad = np.min(dd[None, :] / np.maximum(d @ nn.T, 0.04), axis=1); rad = np.minimum(rad, 1.25)
        rad = rad * (1 + (0.035 if kind != "boulder" else 0.06) * lumps(8, 5.0) + 0.012 * lumps(10, 16.0))
        p = d * rad[:, None]
        if kind == "slab": p[:, 2] *= r.uniform(0.16, 0.3)
        elif kind == "stack":                      # sea stack: tall, undercut at the waterline, ledges
            h = (p[:, 2] + 1) / 2; p[:, 0] *= 0.42 * (1.05 - 0.45 * h + 0.10 * np.sin(h * 19 + seed)); p[:, 1] *= 0.5 * (1.05 - 0.45 * h + 0.08 * np.sin(h * 23)); p[:, 2] = h * 1.5
            p[:, 0] += 0.10 * np.sin(h * 2.5 + seed)
        elif kind == "spire":
            h = np.clip((p[:, 2] + 1) / 2, 0, 1); taper = (1 - h) ** 0.75 * 0.36 + 0.03; p[:, 0] *= taper * (1 + 0.25 * np.sin(h * 14 + seed)); p[:, 1] *= taper * (1 + 0.25 * np.sin(h * 11 + 2 * seed)); p[:, 2] = h * 2.6
        else: p[:, 2] *= r.uniform(0.55, 0.9); p[:, 0] *= r.uniform(0.8, 1.3)
        smooth = kind == "boulder"
    else:
        rad = 1 + 0.10 * lumps(5, 1.6) + 0.02 * lumps(8, 6.0)
        p = d * rad[:, None]; p[:, 2] *= r.uniform(0.5, 0.8); p[:, 0] *= r.uniform(0.85, 1.35); smooth = True
    me.vertices.foreach_set("co", p.astype(np.float32).ravel()); me.update()
    me.polygons.foreach_set("use_smooth", np.full(len(me.polygons), smooth, bool))
    return me

rock_ok = HOOK.get("rock_ok", lambda x, y: True)
for gi, (cnt, ymin, ymax, smin, smax, kind, sink, lo, hi, dust) in enumerate(ROCKS):
    bases = [stack_mesh(f"r{gi}_{k}", 100 * gi + k + 7) if kind == "stack" else base_rock(f"r{gi}_{k}", 100 * gi + k + 7, kind) for k in range(7)]
    mat = rock_mat(f"rock{gi}", lo, hi, dust)
    for b in bases: b.materials.append(mat)
    M = cnt * 12
    ys = np.exp(rng.uniform(math.log(ymin), math.log(ymax), M)) if kind != "stack" else rng.uniform(ymin, ymax, M)
    xs = ys * np.tan(np.radians(rng.uniform(-13, 13, M)))
    ss = smin * (1 - rng.random(M) * (1 - (smin / smax) ** 1.6)) ** (-1 / 1.6)          # power-law sizes
    zs = height(xs[:, None], ys[:, None]).ravel()
    placed = 0
    for x, y, s, z in zip(xs, ys, ss, zs):
        if placed >= cnt: break
        if s / y < 0.0006 or not rock_ok(x, y): continue
        if kind == "stack": z = -0.3
        tall = kind in ("stack", "spire")
        o = bpy.data.objects.new(f"rk{gi}_{placed}", bases[placed % 7]); o.location = (x, y, z - sink * s * 0.5)
        o.scale = (s, s, s); o.rotation_euler = (rng.uniform(-0.05, 0.05) if tall else rng.uniform(-0.25, 0.25), 0 if tall else rng.uniform(-0.25, 0.25), rng.uniform(0, 6.28))
        link(o); placed += 1
    print("rocks", kind, placed, flush=True)

if "sea" in HOOK:
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, DMAX * 20, HOOK["sea"])); sea = bpy.context.active_object; sea.scale = (DMAX * 40, DMAX * 40, 1)
    m, t, out = new_mat("sea")
    if PASS == "beauty": white_shader(t, out, bump_nodes(t, "Object", (1.0, 0.2), 0.0, 0.01, fade=False))
    elif PASS == "albedo":
        rgb = t.nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (0, 0, 0, 1); emit(t, out, rgb.outputs[0])
    elif PASS == "normal": normal_nodes(t, out)
    else: depth_nodes(t, out, 1.0)
    sea.data.materials.append(m)

# ------------------------------------------------------------------------------------------------ lights + camera
def sun_lamp(name, colr, strength, el, az, ang):
    ld = bpy.data.lights.new(name, "SUN"); ld.energy = strength; ld.color = colr; ld.angle = math.radians(ang)
    so = link(bpy.data.objects.new(name, ld)); e, a = math.radians(el), math.radians(az)
    so.rotation_euler = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))).to_track_quat("Z", "Y").to_euler()
if PASS == "beauty":
    sun_lamp("sun", (1, 0, 0), 4.0, P["sun_el"], 0.0, P["sun_ang"])
    if P["second_sun"]: s2 = P["second_sun"]; sun_lamp("sun2", (0, 1, 0), 4.0, s2["el"], s2["az"], s2["ang"])
    else: sun_lamp("glow", (0, 1, 0), 2.0, P["glow_el"], 0.0, P["glow_ang"])
cd = bpy.data.cameras.new("cam"); cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36; cd.lens = 18 / math.tan(math.radians(FOV / 2))
cd.shift_y = HORIZ - 0.5; cd.clip_start = CAMH * 0.5; cd.clip_end = DMAX * 3
co = link(bpy.data.objects.new("cam", cd)); co.location = (0, 0, z0 + CAMH if not P["cloud"] and "sea" not in HOOK else CAMH); co.rotation_euler = (math.radians(90), 0, 0)
sc.camera = co
sc.render.filepath = os.path.join(OUT, f"{WORLD}_{PASS}.png")
bpy.ops.render.render(write_still=True)
print("done", sc.render.filepath, flush=True)
import json
json.dump(dict(camh=CAMH, dmax=DMAX, res=RES, sun_el=P["sun_el"], second_sun=P["second_sun"]), open(os.path.join(OUT, f"{WORLD}_meta.json"), "w"))
