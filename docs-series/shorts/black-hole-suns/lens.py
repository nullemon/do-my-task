"""Schwarzschild ray tracing for a camera at radius r_obs (units of the Schwarzschild radius Rs = 1).
Extends the point-lens idea of ../sun-black-hole/short_vfx.py (lens_swirl) to exact null geodesics.

Photon orbit in its own plane: u = 1/r, d^2u/dphi^2 = -u + 1.5 u^2. A static observer at r_obs sees a ray at angle alpha
from the direction to the hole with impact parameter b = r sin(alpha) / sqrt(1 - 1/r), so the initial slope is
du/dphi = u sqrt(1 - u) cot(alpha). Each ray is traced backwards from the camera until it escapes (u -> 0) or crosses the
horizon (u -> 1). Results per alpha (1-D tables, shared by every pixel with the same alpha):
  * alpha_sky = pi - phi_inf: the sky direction it came from, measured from the hole's direction in the same plane
    (negative = it went round the far side; magnitudes > pi = extra windings, i.e. the higher-order images)
  * U(alpha, phi): the orbit, used to find where the ray crosses the accretion-disk plane (k = 0, 1, 2 crossings).
Doppler + gravitational shift of the disk light: g = sqrt(1-1/r_e)/sqrt(1-1/r_o) / (gamma (1 - beta . k_hat)),
Keplerian speed seen by a static observer beta = sqrt(1 / (2 (r - 1))), observed intensity ~ g^4 (bolometric).
Shadow edge (critical impact parameter b_c = 3 sqrt(3)/2): sin(alpha_c) = b_c sqrt(1 - 1/r_obs) / r_obs (Synge 1966).
"""
import math
import numpy as np
from scipy.ndimage import map_coordinates

f32 = np.float32
BC = 1.5 * math.sqrt(3.0)


def alpha_shadow(r_obs):
    s = BC * math.sqrt(max(1 - 1 / r_obs, 0)) / r_obs
    a = math.asin(min(s, 1.0))
    return a if r_obs >= 1.5 else math.pi - a       # inside the photon sphere the shadow covers more than half the sky


class Tracer:
    def __init__(self, r_obs, a_max=math.radians(80), n=2600, dphi=0.004, phi_max=4.2 * math.pi):
        self.r_obs = r_obs; u0 = 1.0 / r_obs
        ac = alpha_shadow(r_obs); self.alpha_c = ac
        lo, hi = 1e-4, min(a_max, math.pi - 1e-4)
        base = np.linspace(lo, hi, n)
        near = ac + np.sign(np.linspace(-1, 1, n)) * np.geomspace(1e-7, 0.05, n // 2).repeat(2)[:n] if lo < ac < hi else np.array([])
        al = np.unique(np.clip(np.concatenate([base, near]), lo, hi)).astype(np.float64)
        self.alpha = al
        N = len(al); S = int(phi_max / dphi) + 1; self.dphi = dphi; self.S = S
        u = np.full(N, u0); w = u0 * math.sqrt(1 - u0) / np.tan(al)
        U = np.zeros((N, S), f32); U[:, 0] = u
        live = np.ones(N, bool); cap = np.zeros(N, bool); esc = np.zeros(N, bool)
        phi_end = np.full(N, phi_max); peri = np.full(N, phi_max)
        f = lambda u, w: (w, -u + 1.5 * u * u)
        prev_w = w.copy()
        for j in range(1, S):
            k1u, k1w = f(u, w); k2u, k2w = f(u + 0.5 * dphi * k1u, w + 0.5 * dphi * k1w)
            k3u, k3w = f(u + 0.5 * dphi * k2u, w + 0.5 * dphi * k2w); k4u, k4w = f(u + dphi * k3u, w + dphi * k3w)
            un = u + dphi / 6 * (k1u + 2 * k2u + 2 * k3u + k4u); wn = w + dphi / 6 * (k1w + 2 * k2w + 2 * k3w + k4w)
            # escape: u crosses 0
            e = live & (un <= 0)
            if e.any():
                fr = u[e] / (u[e] - un[e]); phi_end[e] = (j - 1 + fr) * dphi; esc[e] = True; live[e] = False
            c = live & (un >= 1.0)
            if c.any():
                fr = (1 - u[c]) / (un[c] - u[c]); phi_end[c] = (j - 1 + fr) * dphi; cap[c] = True; live[c] = False
            tp = live & (np.sign(wn) != np.sign(w)) & (peri >= phi_max)     # first turning point (peri- or apoapsis)
            peri[tp] = j * dphi
            u = np.where(live, un, np.where(cap, 1.0, 0.0)); w = np.where(live, wn, 0.0)
            U[:, j] = u
            if not live.any():
                U[:, j + 1:] = U[:, j:j + 1]; break
        self.U, self.phi_end, self.esc, self.cap, self.peri = U, phi_end, esc, cap, peri
        self.alpha_sky = np.where(esc, math.pi - phi_end, np.nan)
        # initial direction sign: rays with alpha > 90 deg start outward (u decreasing) -> no periapsis before
        self.w0pos = al < math.pi / 2

    # -------------------------------------------------------------------------------------------- per-pixel
    def index(self, a):
        return np.interp(a, self.alpha, np.arange(len(self.alpha))).astype(f32)

    def lookup(self, a):
        """-> escaped mask (float 0..1), alpha_sky, phi_end for pixel angles a"""
        i = self.index(a)
        esc = map_coordinates(self.esc.astype(f32), [i], order=1)
        ask = np.interp(a, self.alpha[self.esc], self.alpha_sky[self.esc]) if self.esc.any() else np.zeros_like(a)
        pe = map_coordinates(self.phi_end.astype(f32), [i], order=1)
        return esc.astype(f32), ask.astype(f32), pe.astype(f32), i

    def u_at(self, i, phi):
        return map_coordinates(self.U, [i, phi / self.dphi], order=1, mode="nearest").astype(f32)

    def peri_at(self, i):
        return map_coordinates(self.peri.astype(f32), [i], order=0)


class View:
    """All per-pixel geometry for one black hole seen by one camera (static parts cached).
    dirs: (N, 3) unit view directions of the pixels; F: unit direction to the hole; n: disk normal (unit)."""
    def __init__(self, tr, dirs, F, n, r_in, r_out, kmax=3):
        self.tr = tr; F = np.asarray(F, f32); n = np.asarray(n, f32)
        ca = np.clip(dirs @ F, -1, 1); a = np.arccos(ca).astype(f32)
        T = dirs - ca[:, None] * F[None]; tn = np.linalg.norm(T, axis=1, keepdims=True)
        T = np.where(tn > 1e-7, T / np.maximum(tn, 1e-7), np.array([0, -1, 0], f32)).astype(f32)
        esc, ask, pe, idx = tr.lookup(a)
        self.esc = esc
        self.sky_dir = (np.cos(ask)[:, None] * F[None] + np.sin(ask)[:, None] * T).astype(f32)
        X = -F                                                      # hole -> camera
        A = float(n @ X); B = T @ n
        phi1 = np.mod(np.arctan2(-A, B), math.pi); phi1 = np.where(phi1 < 1e-4, phi1 + math.pi, phi1)
        # in-disk basis
        e1 = X - (X @ n) * n; e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
        peri = tr.peri_at(idx)
        uo = 1.0 / tr.r_obs
        self.hits = []
        for k in range(kmax):
            ph = phi1 + k * math.pi
            ok = ph < pe
            if not ok.any(): break
            u = tr.u_at(idx, np.where(ok, ph, 0))
            r = 1.0 / np.maximum(u, 1e-6)
            ok &= (r >= r_in) & (r <= r_out)
            if not ok.any(): continue
            sel = np.nonzero(ok)[0]
            phs, rs, us = ph[sel], r[sel], u[sel]
            p = np.cos(phs)[:, None] * X[None] + np.sin(phs)[:, None] * T[sel]
            psi = np.arctan2(p @ e2, p @ e1).astype(f32)
            # photon direction of travel (towards the camera) in the static frame at the emitter
            ib = (np.sin(a[sel]) * tr.r_obs / math.sqrt(max(1 - uo, 1e-9))) ** -2
            w2 = np.maximum(ib - us * us * (1 - us), 0); wabs = np.sqrt(w2)
            s0 = np.where(tr.w0pos[np.clip(np.round(idx[sel]).astype(int), 0, len(tr.alpha) - 1)], 1.0, -1.0)
            w = wabs * s0 * np.where(phs < peri[sel], 1.0, -1.0)
            drdphi = -w / (us * us)
            phat = -np.sin(phs)[:, None] * X[None] + np.cos(phs)[:, None] * T[sel]
            kb = (drdphi / np.sqrt(np.maximum(1 - us, 1e-6)))[:, None] * p + rs[:, None] * phat     # backward ray tangent
            kh = -kb / np.linalg.norm(kb, axis=1, keepdims=True)
            vdir = np.cross(n[None], p); vdir /= np.linalg.norm(vdir, axis=1, keepdims=True)
            beta = np.sqrt(0.5 / np.maximum(rs - 1, 0.05)); beta = np.minimum(beta, 0.95)
            gam = 1 / np.sqrt(1 - beta ** 2)
            g = np.sqrt(np.maximum(1 - us, 1e-4)) / math.sqrt(max(1 - uo, 1e-4)) / (gam * (1 - beta * np.sum(vdir * kh, 1)))
            self.hits.append(dict(sel=sel, r=rs.astype(f32), psi=psi, g=g.astype(f32), k=k))
