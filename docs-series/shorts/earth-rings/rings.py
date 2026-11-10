"""Earth's rings seen from the ground: geometry, radial profile, photometry (linear HDR, numpy / cv2).

Geometry (Earth frame, km): z = Earth's axis (north), x = towards the observer's meridian, y = east.
Observer at latitude phi: O = R_E (cos phi, 0, sin phi). Local frame: up U, north N, east E.
The ring plane is z = 0 (the celestial equator). Every sky pixel's ray d is intersected with that plane:
s = -O_z / d_z, P = O + s d, r = |P|.  The sky camera is a locked STEREOGRAPHIC lens (great circles -> circular arcs,
so the celestial equator reads as a true arch), with its horizon row on the foreground's horizon.

Radial profile: Solar System Scope's 8k Saturn ring texture (CC BY 4.0; 8192 px, C ring to F ring), copied from
planets-as-moon, re-mapped piecewise onto Earth radii (C 7,000-9,500 km, B 9,500-19,000, Cassini division
19,000-21,500, A 21,500-28,000, F ~29,300) plus synthetic faint D, G and a broad diffuse E-like halo to 80,000 km.
Alpha -> normal optical depth tau = -ln(1 - alpha); fine ringlets from 1-D noise; pre-filtered mip levels so the
profile is box-filtered to each pixel's radial footprint (no moire, no shimmer with the locked camera).

Photometry per pixel: single scattering (Chandrasekhar) for the lit face, diffuse transmission for the unlit face,
Henyey-Greenstein phase = back-scattering ice + forward-scattering dust (fraction per ring), a diffuse multiple-scattering /
Earthshine term, Earth's shadow cylinder (penumbra + reddened refracted-light fringe), atmospheric extinction (Kasten-Young).
The rings never block the sky's airlight (the atmosphere is in front of them); they block stars behind them.
"""
import math, os
import numpy as np, cv2
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from lib.core import f32, smooth

RE = 6371.0
TEX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/sss/8k_saturn_ring_alpha.png"
R0, R1, DR = 6600.0, 82000.0, 4.0
NLEV = 11
# Earth km  <-  Saturn texture px  (C inner, B inner, B outer, A inner, A outer, texture end)
KM_KNOTS = [7000.0, 9500.0, 19000.0, 21500.0, 28000.0, 29800.0]
PX_KNOTS = [434.0, 2465.0, 5480.0, 5999.0, 7710.0, 8192.0]
RING_ZONES = dict(C=(7000, 9500), B=(9500, 19000), Cassini=(19000, 21500), A=(21500, 28000), F=(29300, 29300), E=(30000, 80000))


class Profile:
    def __init__(self):
        tex = np.asarray(Image.open(TEX).convert("RGBA"), f32).mean(0) / 255.0           # (8192, 4)
        self.r = r = np.arange(R0, R1, DR, dtype=np.float64)
        n = len(r)
        px = np.interp(r, KM_KNOTS, PX_KNOTS, left=-1, right=-1)
        ok = (px >= 0) & (px < 8191)
        pi = np.clip(px, 0, 8191)
        def samp(c): return np.interp(pi, np.arange(8192), tex[:, c])
        a = np.where(ok, samp(3), 0.0)
        rgb = np.stack([samp(c) for c in range(3)], -1)
        rng = np.random.default_rng(3)
        # fine ringlets (8-80 km), only inside the dense rings
        wn = rng.standard_normal(n); F = np.fft.rfft(wn); fq = np.fft.rfftfreq(n, DR)
        F *= np.where(fq > 1 / 90, np.maximum(fq, 1e-9) ** -0.35, 0) * (fq < 1 / 7); ring_n = np.fft.irfft(F, n); ring_n /= ring_n.std()
        dense = ((r > 7000) & (r < 19000)) | ((r > 21500) & (r < 28000))
        tau = -np.log(1 - np.clip(a, 0, 0.985))
        tau = tau * np.where(dense, np.clip(1 + 0.32 * ring_n, 0.35, 2.0), 1.0)
        # synthetic faint rings (visual optical depths, boosted from the real faint-ring values so they read)
        tau += 0.020 * ((r > 6700) & (r < 7000))                                            # D
        tau += 0.060 * np.exp(-((r - 33500) / 650) ** 2)                                    # G
        E = 0.030 * np.exp(-((r - 44000) / 13000) ** 2) * smooth(30000, 34000, r) * (1 - smooth(70000, 80000, r))
        E = E * (1 + 0.25 * np.sin(r / 2300.0) * np.sin(r / 5100.0))                        # faint banding in the halo
        tau += E
        dust = np.full(n, 0.10)
        dust = np.where((r > 7000) & (r < 9500), 0.30, dust)
        dust = np.where((r > 19000) & (r < 21500), 0.40, dust)
        dust = np.where(r > 28000, 0.90, dust); dust = np.where(r < 7000, 0.9, dust)
        alb = np.clip(rgb / 0.45, 0, 1.6) * 0.55 * np.array([1.10, 0.96, 0.82])            # Saturn-tan, gold-peach
        haloc = np.array([0.55, 0.62, 0.78])
        w = (r > 28000)[:, None] * 1.0
        alb = alb * (1 - w) + haloc * w
        # boost radial contrast (ringlet albedo + density variations) so structure reads even where the ring is opaque
        lm = alb.mean(1)
        rel = lm / np.maximum(gaussian_filter1d(lm, 40, mode="nearest"), 1e-3)
        trel = np.clip(tau / np.maximum(gaussian_filter1d(tau, 40, mode="nearest"), 1e-3), 0.2, 3.0)
        con = np.clip(rel, 0.3, 3.0) ** 1.8 * np.where(dense, trel ** 0.45 * np.clip(1 + 0.22 * ring_n, 0.5, 1.6), 1.0)
        alb = alb * con[:, None]
        self.tau, self.alb, self.dust = tau, alb, dust
        # mip levels: Gaussian sigma 0.5 * 2^k samples
        self.L_tau = np.stack([gaussian_filter1d(tau, 0.5 * 2 ** k, mode="nearest") for k in range(NLEV)]).astype(f32)
        self.L_alb = np.stack([gaussian_filter1d(alb * tau[:, None], 0.5 * 2 ** k, axis=0, mode="nearest") for k in range(NLEV)]).astype(f32)
        self.L_dust = np.stack([gaussian_filter1d(dust * tau, 0.5 * 2 ** k, mode="nearest") for k in range(NLEV)]).astype(f32)

    def sample(self, r, lev):
        """filtered (tau, albedo rgb, dust) at radius r [km] with mip level lev (float)"""
        n = self.L_tau.shape[1]
        i = np.clip((r - R0) / DR, 0, n - 1.001); i0 = i.astype(np.int64); fi = (i - i0).astype(f32)
        l = np.clip(lev, 0, NLEV - 1.001); l0 = l.astype(np.int64); fl = (l - l0).astype(f32)
        def g(T):
            def at(L):
                a = T[L, i0]; b = T[L, i0 + 1]
                return a * (1 - fi[:, None] if a.ndim > 1 else 1 - fi) + b * (fi[:, None] if a.ndim > 1 else fi)
            A, B = at(l0), at(l0 + 1)
            return A * (1 - fl[:, None] if A.ndim > 1 else 1 - fl) + B * (fl[:, None] if A.ndim > 1 else fl)
        tau = g(self.L_tau); ta = np.maximum(tau, 1e-6)
        alb = g(self.L_alb) / ta[:, None]; dust = g(self.L_dust) / ta
        return tau.astype(f32), np.clip(alb, 0, 2).astype(f32), np.clip(dust, 0, 1).astype(f32)

    def tau_soft(self, r, lev=3.0):
        return self.sample(np.atleast_1d(np.asarray(r, np.float64)), np.full(np.size(r), lev))[0]


def local_frame(phi):
    p = math.radians(phi)
    U = np.array([math.cos(p), 0, math.sin(p)]); N = np.array([-math.sin(p), 0, math.cos(p)]); E = np.array([0.0, 1.0, 0.0])
    return U, N, E


def sun_vec(dec, H):
    d, h = math.radians(dec), math.radians(H)
    return np.array([math.cos(d) * math.cos(h), -math.cos(d) * math.sin(h), math.sin(d)])


def alt_az(v, phi):
    U, N, E = local_frame(phi)
    return math.degrees(math.asin(float(v @ U))), math.degrees(math.atan2(float(v @ E), float(v @ N))) % 360


def ring_alt_meridian(r, phi):
    """altitude (deg) of ring radius r seen due south (on the meridian) from latitude phi"""
    p = math.radians(phi)
    return math.degrees(math.atan2(r * math.cos(p) - RE, r * math.sin(p)))


def stereo_dirs(W, H, hz, f, az, phi, xs, ys):
    """Earth-frame unit view vectors for pixel centres (xs, ys) of a stereographic camera facing azimuth az"""
    U, N, E = local_frame(phi)
    a = math.radians(az)
    fwd = math.cos(a) * N + math.sin(a) * E
    right = math.cos(a + math.pi / 2) * N + math.sin(a + math.pi / 2) * E
    u = (xs - W / 2) / f; v = (hz - ys) / f
    rho = np.sqrt(u * u + v * v) + 1e-9
    th = 2 * np.arctan(rho / 2)
    st = np.sin(th) / rho; ct = np.cos(th)
    d = ct[..., None] * fwd + (st * u)[..., None] * right + (st * v)[..., None] * U
    return d.astype(f32)


def airmass(alt_deg):
    a = np.maximum(alt_deg, 0.0)
    return 1.0 / (np.sin(np.radians(a)) + 0.50572 * (a + 6.07995) ** -1.6364)


TAU_ATM = np.array([0.075, 0.125, 0.25], f32)


class Geo:
    """static per-(latitude, camera) geometry: full-res ring hits (masked), half-res sky directions"""
    def __init__(self, prof, W, H, hz, f, az, phi):
        self.phi, self.az = phi, az
        self.O = RE * np.array([math.cos(math.radians(phi)), 0, math.sin(math.radians(phi))])
        self.U, self.N, self.E = local_frame(phi)
        # half-res sky directions
        hh, hw = H // 2, W // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.dh = stereo_dirs(W, H, hz, f, az, phi, xx, yy)
        self.alt_h = np.degrees(np.arcsin(np.clip(self.dh @ self.U.astype(f32), -1, 1))).astype(f32)
        # full-res ring hits
        yy, xx = np.mgrid[0:H, 0:W].astype(f32) + 0.5
        d = stereo_dirs(W, H, hz, f, az, phi, xx, yy)
        dz = d[..., 2]
        Oz = self.O[2]
        with np.errstate(divide="ignore", invalid="ignore"):
            s = -Oz / dz
        sky = yy < hz + 2
        P = self.O[None, None, :] + s[..., None] * d
        r = np.sqrt(P[..., 0] ** 2 + P[..., 1] ** 2)
        hit = sky & (s > 0) & np.isfinite(s) & (r > R0 + 10) & (r < R1 - 10)
        rr = np.where(hit, r, np.nan)
        # radial footprint (km per px) from neighbouring pixels
        gx = np.abs(np.diff(rr, axis=1, append=np.nan)); gx2 = np.abs(np.diff(rr, axis=1, prepend=np.nan))
        gy = np.abs(np.diff(rr, axis=0, append=np.nan)); gy2 = np.abs(np.diff(rr, axis=0, prepend=np.nan))
        st_ = np.stack([gx, gx2, gy, gy2]); fp = np.max(np.where(np.isfinite(st_), st_, -1), 0); fp = np.where(fp > 0, fp, np.nan)
        fp = np.where(np.isfinite(fp), fp, 2000.0)
        self.idx = np.flatnonzero(hit.ravel())
        m = hit.ravel()
        self.r = r.ravel()[m].astype(np.float64)
        self.P = P.reshape(-1, 3)[m][:, :2].astype(f32)
        self.d = d.reshape(-1, 3)[m].astype(f32)
        self.mu = np.maximum(np.abs(self.d[:, 2]), 1e-4).astype(f32)
        lev = np.log2(np.maximum(fp.ravel()[m] * 1.25 / DR, 1.0))
        self.tau, self.alb, self.dust = prof.sample(self.r, lev)
        self.lam = np.arctan2(self.P[:, 1], self.P[:, 0]).astype(f32)
        alt = np.degrees(np.arcsin(np.clip(self.d @ self.U.astype(f32), -1, 1)))
        self.ext = np.exp(-airmass(alt)[:, None] * TAU_ATM[None, :]).astype(f32)
        self.alt = alt.astype(f32)
        self.T = np.exp(-self.tau / self.mu).astype(f32)                   # direct transmission (stars behind)
        self.W, self.H = W, H
        self.ys = (self.idx // W).astype(np.int32); self.xs = (self.idx % W).astype(np.int32)
        rs = np.random.default_rng(int(phi * 100) + int(az))
        k = min(len(self.idx), 9000)
        self.glint = rs.choice(len(self.idx), k, replace=False) if k else np.zeros(0, int)
        self.glint_ph = rs.uniform(0, 6.283, k).astype(f32); self.glint_fr = rs.uniform(0.6, 2.6, k).astype(f32)

    # ------------------------------------------------------------------------------------------------
    def shade(self, sv, earthshine=0.03, diffuse=0.30):
        """ring radiance in units of I/F (per pixel, rgb) for sun vector sv; also Earth-shadow factor"""
        mu = self.mu; tau = self.tau
        mu0 = max(abs(float(sv[2])), 0.03)
        same = (float(sv[2]) * self.O[2] > 0) if abs(self.O[2]) > 1 else True
        c = np.clip(self.d @ sv.astype(f32), -1, 1)
        def hg(g): return (1 - g * g) / (1 + g * g - 2 * g * c) ** 1.5
        Pp = (1 - self.dust) * hg(-0.28) + self.dust * (0.25 * hg(0.80) + 0.05 * hg(0.97) * 0.2)
        Pp = Pp + self.dust * 0.15
        t1 = tau / mu; t0 = tau / mu0
        if same:
            I = 0.25 * Pp * mu0 / (mu + mu0) * (1 - np.exp(-(t1 + t0)))
        else:
            dm = mu0 - mu
            lim = t1 * np.exp(-t1)
            with np.errstate(divide="ignore", invalid="ignore"):
                ex = np.where(np.abs(dm) > 1e-3, mu0 / dm * (np.exp(-t0) - np.exp(-t1)), lim)
            I = 0.25 * Pp * np.maximum(ex, 0)
        # multiple scattering through thick ice (both faces) + Earthshine
        I = I + diffuse * 0.25 * (1 - np.exp(-t1)) * np.exp(-0.35 * tau) * (0.45 if not same else 0.25) + earthshine * (1 - np.exp(-t1))
        # Earth's shadow cylinder
        P3 = self.P
        tc = P3[:, 0] * sv[0] + P3[:, 1] * sv[1]
        perp = np.sqrt(np.maximum(self.r ** 2 - tc.astype(np.float64) ** 2, 0)).astype(f32)
        pen = 90 + 0.0047 * np.abs(tc)
        sh = np.where(tc > 0, 1.0, smooth(RE - pen, RE + pen, perp)).astype(f32)
        fringe = ((tc < 0) * (perp < RE + pen) * np.exp(-np.maximum(RE - perp, 0) / 380.0) * (1 - sh)).astype(f32)
        return I.astype(f32), sh, fringe
