"""Lit + self-luminous exoplanet discs for "What If Strange Exoplanets Replaced Our Moon?" (linear HDR, numpy / cv2).

The sphere core is copied from ../planets-as-moon/planets.py (true 3-D oblate sphere, one orthographic ray per pixel,
2x supersampled in its bounding box, analytic limb anti-aliasing, Lommel-Seeliger / Minnaert shading, limb haze and a
thin lit rim). Added here:
  - procedural equirectangular albedo + EMISSION maps (nobody has imaged these worlds; the maps follow what is known:
    lava-crack crust, cobalt-blue streaky bands, a dark cloud deck, a stellar-like boiling photosphere)
  - a self-luminous term (thermal glow), weighted towards the day side, with its own limb darkening and its own drift
  - a per-body Sun direction (phase), so a body can be full, gibbous or a thin crescent
  - an egg / tidal shape (WASP-12 b): screen-space stretch along an axis and a taper towards the L1 tip
Geometry: camera x right, y down, z forward (away from the viewer).
"""
import math, os
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, fbm2, smooth, bbcolor

TEX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/sss"
SUN0 = np.array([-0.22, 0.10, -0.97]); SUN0 = SUN0 / np.linalg.norm(SUN0)       # Sun below the horizon, behind the camera


def load_lin(name, size=None):
    im = Image.open(os.path.join(TEX, name)).convert("RGB")
    a = np.asarray(im, f32) / 255.0
    if size and size[0] < a.shape[1]: a = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
    return srgb_to_lin(a)


def frame_of(pole):
    Y = np.asarray(pole, float); Y = Y / np.linalg.norm(Y)
    v = np.array([0.0, 0.0, -1.0])
    X = np.cross(Y, v); X = X / np.linalg.norm(X); Z = np.cross(X, Y)
    return np.stack([X, Y, Z])


def pole_vec(roll_deg, tip_deg):
    r, b = math.radians(roll_deg), math.radians(tip_deg)
    return np.array([math.sin(r) * math.cos(b), -math.cos(r) * math.cos(b), -math.sin(b)])


def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)


# ------------------------------------------------------------------------------------------------ procedural maps
def _lat_grid(h, w):
    lat = (0.5 - (np.arange(h, dtype=f32) + 0.5) / h) * np.pi
    return np.repeat(lat[:, None], w, 1)


def _warp(n, ux, uy, amt):
    h, w = n.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(f32)
    return cv2.remap(n, (xx + ux * amt) % w, np.clip(yy + uy * amt, 0, h - 1), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def _sphere_xyz(h, w):
    lat = (0.5 - (np.arange(h) + 0.5) / h) * np.pi; lon = ((np.arange(w) + 0.5) / w - 0.5) * 2 * np.pi
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    return np.stack([np.cos(la) * np.sin(lo), np.sin(la), np.cos(la) * np.cos(lo)], -1)


def _plate_edges(xyz, n, seed, jitter):
    """distance to the nearest Voronoi plate boundary on the sphere (F2 - F1, radians-ish)"""
    from scipy.spatial import cKDTree
    r = np.random.default_rng(seed)
    p = r.standard_normal((n, 3)); p /= np.linalg.norm(p, axis=1, keepdims=True)
    q = xyz + jitter; q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    d, _ = cKDTree(p).query(q.reshape(-1, 3), k=2)
    return (d[:, 1] - d[:, 0]).reshape(xyz.shape[:2]).astype(f32)


def map_lava(h=1024, w=2048, seed=11):
    """55 Cancri e: dark basaltic crust broken into plates by glowing cracks (Voronoi plate edges, warped), with a
    few molten seas. -> albedo (linear), emission (linear, peak ~1)"""
    xyz = _sphere_xyz(h, w)
    a = fbm2((h, w), seed, 2.6); b = fbm2((h, w), seed + 1, 2.0)
    jit = np.stack([fbm2((h, w), seed + 7 + i, 2.4) for i in range(3)], -1) * 0.035
    e1 = _plate_edges(xyz, 90, seed, jit)
    e2 = _plate_edges(xyz, 900, seed + 1, jit * 0.6)
    lat = np.arcsin(np.clip(xyz[..., 1], -1, 1)); sc = 1 / np.maximum(np.cos(lat), 0.2)   # keep widths even in lon
    core = np.exp(-(e1 / 0.006) ** 2) + 0.55 * np.exp(-(e2 / 0.0035) ** 2)
    halo = np.exp(-(e1 / 0.035) ** 2) + 0.35 * np.exp(-(e2 / 0.012) ** 2)
    core = cv2.GaussianBlur(core.astype(f32), (0, 0), 0.7)
    sea = smooth(1.05, 1.7, a)                                           # a few molten seas
    crust = np.clip(0.5 + 0.2 * b + 0.12 * fbm2((h, w), seed + 12, 1.4), 0.1, 1)
    alb = np.stack([crust * 0.060, crust * 0.050, crust * 0.046], -1) * (1 - 0.8 * sea[..., None]) * (1 - 0.6 * np.clip(halo, 0, 1)[..., None])
    yel = np.array([1.0, 0.62, 0.16], f32); org = np.array([1.0, 0.30, 0.04], f32); red = np.array([0.55, 0.06, 0.01], f32)
    flick = 0.75 + 0.25 * smooth(-1.5, 1.5, fbm2((h, w), seed + 6, 2.2))
    em = (np.clip(core, 0, 1.2)[..., None] * yel * 1.4 + np.clip(halo, 0, 1.2)[..., None] * red * 0.6) * flick[..., None]
    em = em + sea[..., None] * (org * 0.9 + yel * 0.35 * smooth(0.0, 1.5, b)[..., None])
    return alb.astype(f32), em.astype(f32)


def map_cobalt(h=1024, w=2048, seed=21):
    """HD 189733 b: deep cobalt-blue banded clouds with long wind streaks (silicate haze). -> albedo"""
    lat = _lat_grid(h, w)
    n = fbm2((h, w), seed, 2.2)
    streak = cv2.GaussianBlur(fbm2((h, w), seed + 1, 1.2), (0, 0), sigmaX=22, sigmaY=0.9); streak /= streak.std() + 1e-6
    fine = cv2.GaussianBlur(fbm2((h, w), seed + 2, 1.0), (0, 0), sigmaX=8, sigmaY=0.5); fine /= fine.std() + 1e-6
    wy = cv2.GaussianBlur(fbm2((h, w), seed + 3, 2.5), (0, 0), sigmaX=10, sigmaY=2)
    bands = (np.sin(lat * 9.0 + 0.6 * wy + 0.25 * n) * 0.5 + 0.5) ** 1.5
    bands2 = np.sin(lat * 23.0 + 0.9 * wy) * 0.5 + 0.5
    v = 0.50 * bands + 0.18 * bands2 + 0.16 * streak + 0.08 * fine
    v = (v - v.min()) / (v.max() - v.min())
    deep = srgb_to_lin(np.array([0.03, 0.10, 0.42], f32)); mid = srgb_to_lin(np.array([0.10, 0.30, 0.80], f32))
    pale = srgb_to_lin(np.array([0.48, 0.70, 1.00], f32))
    v3 = v[..., None]
    col = deep * (1 - smooth(0.0, 0.55, v3)) + mid * smooth(0.0, 0.55, v3)
    col = col * (1 - smooth(0.6, 1.0, v3)) + pale * smooth(0.6, 1.0, v3)
    col = col * (0.82 + 0.18 * np.cos(lat)[..., None] ** 0.5)                 # darker hazy poles
    return (col * 0.85).astype(f32)


def map_sparkle(h=512, w=1024, seed=23, n=700):
    """glass-rain glints: sparse streaks (emission), drifted fast in longitude at render time"""
    r = np.random.default_rng(seed)
    m = np.zeros((h, w), f32)
    ys = (np.arcsin(r.uniform(-0.95, 0.95, n)) / np.pi + 0.5) * h; xs = r.uniform(0, w, n)
    np.add.at(m, (np.clip(ys.astype(int), 0, h - 1), xs.astype(int) % w), r.uniform(0.3, 1.0, n) ** 3)
    m = cv2.GaussianBlur(m, (0, 0), sigmaX=6.0, sigmaY=0.35) * 40
    return np.stack([m * 0.55, m * 0.80, m * 1.0], -1).astype(f32)


def map_wasp(h=1024, w=2048, seed=31):
    """WASP-12 b: a very dark hot giant (one of the least reflective planets measured), ~2,600 K on its day side:
    charcoal-maroon cloud belts + a deep red-orange thermal glow, brightest in the belts. -> albedo, emission"""
    lat = _lat_grid(h, w)
    n = fbm2((h, w), seed, 2.3)
    st = cv2.GaussianBlur(fbm2((h, w), seed + 1, 1.3), (0, 0), sigmaX=10, sigmaY=1.5); st /= st.std() + 1e-6
    wv = cv2.GaussianBlur(fbm2((h, w), seed + 2, 2.4), (0, 0), sigmaX=6, sigmaY=2)
    bands = (np.sin(lat * 8.0 + 0.8 * wv + 0.3 * n) * 0.5 + 0.5) ** 2
    v = np.clip(0.65 * bands + 0.22 * st * 0.5 + 0.15 * n * 0.4 + 0.12, 0, 1)
    alb = np.stack([0.05 + 0.04 * v, 0.03 + 0.02 * v, 0.03 + 0.015 * v], -1)
    deep = np.array([0.70, 0.07, 0.02], f32); hot = np.array([1.0, 0.42, 0.08], f32)
    em = deep[None, None] * (1 - v[..., None]) + hot * v[..., None]
    em = em * (0.15 + 0.85 * v[..., None] ** 1.3) * (0.8 + 0.2 * smooth(-1.5, 1.5, n)[..., None])
    return alb.astype(f32), em.astype(f32)


def map_coal(h=1024, w=2048, seed=41):
    """TrES-2 b: almost black (geometric albedo ~1 %); faint dull-red thermal glow (T ~1,500 K) -> albedo, emission"""
    lat = _lat_grid(h, w)
    n = fbm2((h, w), seed, 2.2)
    st = cv2.GaussianBlur(fbm2((h, w), seed + 1, 1.2), (0, 0), sigmaX=14, sigmaY=1.0); st /= st.std() + 1e-6
    v = np.clip(0.5 + 0.18 * np.sin(lat * 8 + 0.4 * n) + 0.12 * st, 0, 1)
    alb = np.stack([0.010 * v + 0.004, 0.008 * v + 0.003, 0.008 * v + 0.003], -1)
    em = bbcolor(1500.0) * (0.5 + 0.5 * v[..., None]) * (0.7 + 0.3 * smooth(-1.5, 1.5, fbm2((h, w), seed + 2, 2.6))[..., None])
    return alb.astype(f32), em.astype(f32)


def map_kelt(h=1024, w=2048, seed=51):
    """KELT-9 b: ~4,600 K day side, star-like: boiling convective cells and hot spots. -> albedo (~0), emission"""
    g = cv2.GaussianBlur(fbm2((h, w), seed, 1.6, lo=16), (0, 0), 1.5)          # convective cells
    g = g / (g.std() + 1e-6)
    g2 = fbm2((h, w), seed + 3, 2.4, lo=3)                                      # large hot / cool regions
    v = 0.78 + 0.07 * g + 0.10 * g2
    T = 4600 + 900 * (v - 0.78) / 0.2
    col = np.stack([bbcolor(float(x)) for x in np.linspace(3400, 5800, 49)])        # LUT
    idx = np.clip((T - 3400) / 2400 * 48, 0, 48)
    i0 = np.floor(idx).astype(int); i1 = np.minimum(i0 + 1, 48); fr = (idx - i0)[..., None]
    c = col[i0] * (1 - fr) + col[i1] * fr
    em = c * np.clip(v, 0.3, 1.3)[..., None] ** 3.0
    y = em.mean(-1, keepdims=True); em = np.clip(y + (em - y) * 1.5, 0, None)
    return np.zeros_like(em, dtype=f32) + 0.02, em.astype(f32)


# ------------------------------------------------------------------------------------------------ the body
class Body:
    def __init__(self, key, Rp, pole, tex=None, alb=None, emis=None, q=1.0, spin=0.0, lon0=0.0, model="giant", k=0.85,
                 surf=1.0, haze=(0, 0, 0), rim=(0, 0, 0), winds=0.0, detail=0.05, ss=2, sun=None, emis_day=0.6,
                 emis_ld=0.6, emis_spin=None, emis_winds=None, emis2=None, emis2_spin=0.0, night=0.035, emis_limb=None,
                 stretch=None, seed=1):
        self.key, self.Rp, self.q, self.spin, self.lon0 = key, Rp, q, spin, lon0
        self.model, self.k, self.surf, self.winds, self.ss = model, k, surf, winds, ss
        self.haze, self.rim = np.array(haze, f32), np.array(rim, f32)
        self.M = frame_of(pole)
        self.sun = unit(SUN0 if sun is None else sun)
        self.emis_day, self.emis_ld, self.night = emis_day, emis_ld, night
        self.emis_spin = spin if emis_spin is None else emis_spin
        self.emis_winds = winds if emis_winds is None else emis_winds
        self.emis2, self.emis2_spin = emis2, emis2_spin
        self.emis_limb = None if emis_limb is None else np.array(emis_limb, f32)
        self.stretch = stretch                                              # (angle_deg, long_factor, taper)
        if tex is not None:
            want = int(min(2 * math.pi * Rp * ss * 1.3, 8192)); want = max(want, 256)
            alb = load_lin(tex, (want, want // 2))
        self.tex = alb.astype(f32)
        self.emis = None if emis is None else emis.astype(f32)
        h, w = self.tex.shape[:2]
        n = fbm2((min(h, 1024), min(w, 2048)), 300 + seed, 1.5)
        if model == "giant":
            n = cv2.GaussianBlur(n, (0, 0), sigmaX=5, sigmaY=0.6); n = n / (n.std() + 1e-6)
        self.det = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC) * detail

    def ellipsoid_hit(self, o, d):
        q = self.q
        os_ = o.copy(); os_[..., 1] /= q; ds = d.copy(); ds[..., 1] /= q
        a = (ds * ds).sum(-1); b = (os_ * ds).sum(-1); c = (os_ * os_).sum(-1) - 1
        disc = b * b - a * c
        tt = (-b - np.sqrt(np.maximum(disc, 0))) / a
        reff = np.sqrt(np.maximum(1 - disc / a, 0))
        return disc > 0, tt, reff

    def _sample(self, tex, lon, lat):
        th, tw_ = tex.shape[:2]
        mx = ((lon / (2 * np.pi) + 0.5) % 1.0 * tw_).astype(f32); my = np.clip((0.5 - lat / np.pi) * th - 0.5, 0, th - 1).astype(f32)
        return cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP), mx, my

    def _lon(self, lon, lat, t, spin, winds):
        lon = lon + self.lon0 - spin * t
        if winds:
            lon = lon - winds * t * (np.sin(lat * 7.0) * 0.6 + np.sin(lat * 13.0 + 0.7) * 0.4) * np.cos(lat)
        return lon

    def extent(self, scale=1.0):
        st = self.stretch[1] if self.stretch else 1.0
        return self.Rp * scale * st

    def render(self, img, cx, cy, t, I=1.0, scale=1.0, ext=None, light=(1, 1, 1), E=1.0, extra_pad=0):
        """add the body into img (HxWx3 linear) centred at (cx, cy); E scales the emission. -> (x0, x1, y0, y1, cov)"""
        R = self.Rp * scale
        if R < 0.2: return
        H, W = img.shape[:2]
        outer = R * (self.stretch[1] * (1 + self.stretch[2]) if self.stretch else 1.0)
        pad = outer * 1.02 + 6 + R * 0.06 + extra_pad
        x0, x1 = int(max(0, math.floor(cx - pad))), int(min(W, math.ceil(cx + pad)))
        y0, y1 = int(max(0, math.floor(cy - pad))), int(min(H, math.ceil(cy + pad)))
        if x1 <= x0 or y1 <= y0: return
        ss = self.ss if R > 1.5 else 4
        ys, xs = np.mgrid[0:(y1 - y0) * ss, 0:(x1 - x0) * ss].astype(f32)
        u = ((xs + 0.5) / ss + x0 - cx) / R; w = ((ys + 0.5) / ss + y0 - cy) / R
        if self.stretch:                                                     # egg: stretch along `ang`, taper to the tip
            ang, lf, tp = self.stretch; ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            a_ = (u * ca + w * sa) / lf; b_ = -u * sa + w * ca
            b_ = b_ / np.maximum(1 - tp * a_ - 0.25 * tp * a_ * a_, 0.05)
            u, w = a_ * ca - b_ * sa, a_ * sa + b_ * ca
            tipw = smooth(-0.9, 1.0, a_)
        M = self.M.astype(f32)
        o = np.stack([u, w, np.full_like(u, -10.0)], -1) @ M.T
        d = M[:, 2]
        dd = np.broadcast_to(d, o.shape)
        _, tt, reff = self.ellipsoid_hit(o, dd)
        cov0 = np.clip((1 - reff) * R * ss + 0.5, 0, 1).astype(f32)
        hit = cov0 > 0
        h = o + tt[..., None] * d
        s = (M @ self.sun).astype(f32)
        rad = np.zeros(u.shape + (3,), f32); cov = np.zeros(u.shape, f32)
        if hit.any():
            n_ = h.copy(); n_[..., 1] /= self.q * self.q
            n_ /= np.linalg.norm(n_, axis=-1, keepdims=True) + 1e-9
            mu = np.clip(-(n_ @ d), 0.0, 1.0); mu0 = n_ @ s
            hs = h.copy(); hs[..., 1] /= self.q
            hs /= np.linalg.norm(hs, axis=-1, keepdims=True) + 1e-9
            lat = np.arcsin(np.clip(hs[..., 1], -1, 1)); lon0 = np.arctan2(hs[..., 0], hs[..., 2])
            lon = self._lon(lon0, lat, t, self.spin, self.winds)
            alb, mx, my = self._sample(self.tex, lon, lat)
            tw_, th = self.tex.shape[1], self.tex.shape[0]
            dt = cv2.remap(self.det, mx * self.det.shape[1] / tw_, my * self.det.shape[0] / th, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            alb = alb * (1 + dt)[..., None]
            if self.model == "rock":
                m0 = np.maximum(mu0, 0)
                f = 2 * m0 / (m0 + np.maximum(mu, 0.02)) * smooth(-0.02, 0.06, mu0)
            else:
                m0 = np.clip(mu0 + 0.04, 0, 1) / 1.04
                f = (m0 ** self.k) * np.maximum(mu, 0.05) ** (self.k - 1) * smooth(-0.12, 0.20, mu0)
                f = f + self.night * (1 - smooth(-0.1, 0.15, mu0)) * mu ** 0.5
            col = alb * f[..., None]
            if self.haze.any():
                col = col + self.haze * ((1 - mu) ** 2.2 * smooth(-0.15, 0.4, mu0))[..., None]
            col = col * self.surf
            if self.emis is not None and E > 0:                               # thermal glow (independent of the Sun)
                lon_e = self._lon(lon0, lat, t, self.emis_spin, self.emis_winds)
                em, _, _ = self._sample(self.emis, lon_e, lat)
                dayw = (1 - self.emis_day) + self.emis_day * smooth(-0.35, 0.7, mu0)
                if self.stretch: dayw = dayw * (0.35 + 1.1 * tipw)
                ld = (1 - self.emis_ld) + self.emis_ld * mu ** 0.7
                em = em * (dayw * ld * E)[..., None]
                if self.emis_limb is not None: em = em * np.maximum(mu, 0.02)[..., None] ** self.emis_limb
                col = col + em
            if self.emis2 is not None and E > 0:                              # fast-moving glints (glass rain)
                lon2 = self._lon(lon0, lat, t, self.emis2_spin, 0.0)
                e2, _, _ = self._sample(self.emis2, lon2, lat)
                col = col + e2 * (smooth(-0.1, 0.4, mu0) * mu ** 0.5 * E)[..., None]
            cov = cov0
            rad = col * cov[..., None]
        if self.rim.any():                                                   # thin lit atmosphere rim, sunward side
            sd = np.array([self.sun[0], self.sun[1]], f32); sn = np.linalg.norm(sd)
            sd = sd / sn if sn > 1e-6 else np.array([0, -1], f32)
            rr = np.sqrt(u * u + w * w)
            back = max(0.0, float(self.sun[2]))                               # Sun behind the planet -> rim all round
            lit = np.clip((u * sd[0] + w * sd[1]) / (rr + 1e-6) * 1.3 - 0.05, 0, 1) ** 1.5 * (1 - back) + back * 0.6
            rim = np.exp(-np.maximum(reff - 1.0, 0) * R / max(1.2, 0.010 * R)) * lit * (1 - cov0)
            rad = rad + (rim * (1 - cov))[..., None] * self.rim
        if ss > 1:
            sz = (x1 - x0, y1 - y0)
            rad = cv2.resize(rad, sz, interpolation=cv2.INTER_AREA); cov = cv2.resize(cov, sz, interpolation=cv2.INTER_AREA)
        rad = rad * np.array(light, f32) * I
        if ext is not None: rad = rad * ext[y0:y1, x0:x1]
        reg = img[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = reg * (1 - cov[..., None]) + rad
        return (x0, x1, y0, y1, cov)
