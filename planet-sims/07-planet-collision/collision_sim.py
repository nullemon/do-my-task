#!/usr/bin/env python3
"""
PLANETARY COLLISION SPH  -  planet-sims / 07   (simulation half)
================================================================
A small but "proper" smoothed-particle-hydrodynamics giant-impact code in the
spirit of the NASA/Durham Moon-formation runs (Theia hits the proto-Earth):

  * equal-mass SPH particles, Wendland C2 kernel, adaptive smoothing lengths
    (support radius H_i = distance to the ~60th neighbour, scipy cKDTree)
  * symmetric pair forces with H_ij = (H_i+H_j)/2 (momentum conserving),
    Monaghan artificial viscosity with the Balsara shear switch
  * Tillotson equation of state with real tables for iron and granite/basalt
    (Melosh 1989 / Benz & Asphaug 1999), no-tension fluid (P >= 0)
  * self-gravity with a Barnes-Hut octree (numba, parallel, Plummer softening)
  * KDK leapfrog, global adaptive time step (CFL + acceleration criterion)
  * every body is first relaxed in isolation (damped, isentropic) and cached
  * resumable checkpoints, output frames in the shared cache contract

Run (needs numpy, scipy, numba - see requirements.txt):
    python collision_sim.py                         # CONFIG defaults (theia)
    python collision_sim.py --scenario theia --n 50000 --hours 24
    python collision_sim.py --scenario speed_series --variant 2
    python collision_sim.py --list                  # show presets
Output: <cache_dir>/<run_name>/meta.json + frame_00000.npz ...
Re-running the same command resumes from <run>/checkpoint.npz (use --fresh).
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

try:
    import numba
    from numba import njit, prange
except ImportError:  # pragma: no cover
    sys.exit("collision_sim.py needs numba:  pip install numpy scipy numba")
from scipy.spatial import cKDTree

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
CONFIG = dict(
    scenario="theia",        # theia | moon_hits_earth | mars_vs_earth | earth_into_jupiter | two_earths | speed_series
    variant=0,               # index into SPEED_SERIES for scenario "speed_series"
    n_particles=50000,       # total SPH particles (equal mass). 20k quick, 200k-1M = research-like
    hours=24.0,              # simulated hours after the start (approach + impact + disc)
    out_every_min=2.0,       # simulated minutes between cache frames (2 min -> 720 frames per 24 h)
    cache_dir=None,          # default: ./cache next to where you run it
    run_name=None,           # default: scenario (+ variant / N suffix)
    n_neighbours=60,         # SPH neighbour number
    h_max_factor=5.0,        # cap: H <= factor * median initial H (keeps far debris cheap)
    theta=0.6,               # Barnes-Hut opening angle
    soft_factor=0.5,         # gravitational softening = factor * median initial h (h = H/2)
    courant=0.35,
    av_alpha=1.5, av_beta=3.0,
    mantle_material="granite",   # granite | basalt
    T_initial_K=2000.0,      # initial temperature of all material (molten-ish surface)
    T_cold_K=2000.0, T_hot_K=30000.0,   # fixed temp normalisation (log scale) -> temp 0..1
    relax_time=10.0,         # code time units (~805 s each) of damped relaxation per body
    relax_check=2.0,         # undamped stability check after relaxation
    start_sep_contact=3.0,   # initial centre distance in units of (R_target + R_impactor)
    checkpoint_every=20,     # frames
    threads=0,               # 0 = numba default (all cores)
    neigh_every=4,           # rebuild kd-tree neighbour lists every n steps (distances refreshed each step)
    neigh_extra=10,          # extra candidates kept in the lists between rebuilds
)

# ---- physical constants / code units (G = 1, R_E = 1, M_E = 1) -------------
G_SI = 6.674e-11
R_E = 6.371e6               # m
M_E = 5.972e24              # kg
T_U = math.sqrt(R_E ** 3 / (G_SI * M_E))   # s  (~805.6 s)
V_U = R_E / T_U             # m/s (~7.91 km/s)
RHO_U = M_E / R_E ** 3      # kg/m^3
P_U = M_E / (R_E * T_U ** 2)   # Pa
U_U = V_U ** 2              # J/kg

# ---- Tillotson tables (SI) --------------------------------------------------
TILLOTSON = {
    #           rho0   A(Pa)    B(Pa)    E0(J/kg) Eiv     Ecv      a    b    alpha beta  cv(J/kg/K)
    "iron":    (7800., 1.28e11, 1.05e11, 9.5e6,  2.4e6,  8.67e6,  0.5, 1.5, 5.0, 5.0, 449.0),
    "granite": (2680., 1.80e10, 1.80e10, 1.6e7,  3.5e6,  1.8e7,   0.5, 1.3, 5.0, 5.0, 790.0),
    "basalt":  (2700., 2.67e10, 2.67e10, 4.87e8, 4.72e6, 1.82e7,  0.5, 1.5, 5.0, 5.0, 840.0),
}

# ---- bodies: mass [M_E], core mass fraction ---------------------------------
BODIES = {
    "proto_earth": dict(mass=0.90, core=0.30, label="proto-Earth"),
    "earth":       dict(mass=1.00, core=0.32, label="Earth"),
    "theia":       dict(mass=0.10, core=0.30, label="Theia"),
    "mars":        dict(mass=0.107, core=0.24, label="Mars"),
    "moon":        dict(mass=0.0123, core=0.02, label="Moon"),
}
JUPITER = dict(mass=317.8, radius=11.21, label="Jupiter")   # M_E, R_E (external potential)

# v_imp in units of the mutual escape speed, angle in degrees from head-on
SCENARIOS = {
    "theia":              dict(target="proto_earth", impactor="theia", v_rel=1.0, angle=45.0, hours=24.0),
    "moon_hits_earth":    dict(target="earth", impactor="moon", v_rel=1.0, angle=30.0, hours=6.0),
    "mars_vs_earth":      dict(target="earth", impactor="mars", v_rel=1.1, angle=40.0, hours=24.0),
    "two_earths":         dict(target="earth", impactor="earth", v_rel=1.0, angle=35.0, hours=24.0),
    "earth_into_jupiter": dict(target=None, impactor="earth", external="jupiter", start_dist=80.0,
                               periapsis=0.6, hours=10.0),
    "speed_series":       dict(target="proto_earth", impactor="theia", hours=24.0),
}
SPEED_SERIES = [  # (v / v_esc, angle)
    (1.0, 45.0), (1.4, 45.0), (2.0, 45.0), (1.0, 20.0), (1.0, 65.0),
]


# ============================================================================
# numba kernels
# ============================================================================
W_NORM = 21.0 / (2.0 * math.pi)


@njit(cache=True, fastmath=True, inline="always")
def _wendland(r, H):
    q = r / H
    if q >= 1.0:
        return 0.0
    t = 1.0 - q
    return W_NORM / (H * H * H) * t * t * t * t * (1.0 + 4.0 * q)


@njit(cache=True, fastmath=True, inline="always")
def _dwendland_over_r(r, H):
    # (dW/dr)/r  -- finite at r = 0
    q = r / H
    if q >= 1.0:
        return 0.0
    t = 1.0 - q
    return -20.0 * W_NORM / (H ** 5) * t * t * t


@njit(parallel=True, cache=True)
def refresh_lists(pos, idx, K):
    """Recompute distances of stored candidate lists, sort rows, return the K nearest."""
    N, C = idx.shape
    oi = np.empty((N, K), np.int64)
    od = np.empty((N, K))
    for i in prange(N):
        d = np.empty(C)
        for c in range(C):
            j = idx[i, c]
            dx = pos[i, 0] - pos[j, 0]
            dy = pos[i, 1] - pos[j, 1]
            dz = pos[i, 2] - pos[j, 2]
            d[c] = math.sqrt(dx * dx + dy * dy + dz * dz)
        o = np.argsort(d)
        for k in range(K):
            oi[i, k] = idx[i, o[k]]
            od[i, k] = d[o[k]]
    return oi, od


@njit(cache=True)
def build_csr(idx, dist, H):
    """Symmetric neighbour rows: row i = {j: r_ij < max(H_i, H_j)} (from kNN lists)."""
    N, K = idx.shape
    cnt = np.zeros(N + 1, np.int64)
    for i in range(N):
        for k in range(K):
            j = idx[i, k]
            r = dist[i, k]
            if r < H[i]:
                cnt[i + 1] += 1
                if r >= H[j]:
                    cnt[j + 1] += 1
    for i in range(N):
        cnt[i + 1] += cnt[i]
    nb = np.empty(cnt[N], np.int64)
    fill = cnt[:-1].copy()
    for i in range(N):
        for k in range(K):
            j = idx[i, k]
            r = dist[i, k]
            if r < H[i]:
                nb[fill[i]] = j
                fill[i] += 1
                if r >= H[j]:
                    nb[fill[j]] = i
                    fill[j] += 1
    return cnt, nb


@njit(parallel=True, cache=True, fastmath=True)
def sph_density(pos, vel, m, H, rowptr, nb):
    N = pos.shape[0]
    rho = np.empty(N)
    div = np.empty(N)
    curl = np.empty(N)
    for i in prange(N):
        Hi = H[i]
        s = m[i] * _wendland(0.0, Hi)
        dv = 0.0
        cx = 0.0
        cy = 0.0
        cz = 0.0
        for p in range(rowptr[i], rowptr[i + 1]):
            j = nb[p]
            dx = pos[i, 0] - pos[j, 0]
            dy = pos[i, 1] - pos[j, 1]
            dz = pos[i, 2] - pos[j, 2]
            r = math.sqrt(dx * dx + dy * dy + dz * dz)
            if r < Hi:
                s += m[j] * _wendland(r, Hi)
                g = m[j] * _dwendland_over_r(r, Hi)
                vx = vel[i, 0] - vel[j, 0]
                vy = vel[i, 1] - vel[j, 1]
                vz = vel[i, 2] - vel[j, 2]
                dv += g * (vx * dx + vy * dy + vz * dz)
                cx += g * (vy * dz - vz * dy)
                cy += g * (vz * dx - vx * dz)
                cz += g * (vx * dy - vy * dx)
        rho[i] = s
        div[i] = -dv / s
        curl[i] = math.sqrt(cx * cx + cy * cy + cz * cz) / s
    return rho, div, curl


@njit(parallel=True, cache=True, fastmath=True)
def tillotson(rho, u, mat_idx, tab):
    """tab rows: rho0 A B E0 Eiv Ecv a b alpha beta (code units). Returns P, c."""
    N = rho.shape[0]
    P = np.empty(N)
    c = np.empty(N)
    for i in prange(N):
        t = tab[mat_idx[i]]
        rho0, A, B, E0, Eiv, Ecv, a, b, al, be = t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8], t[9]
        r = rho[i]
        e = max(u[i], 0.0)
        eta = r / rho0
        mu = eta - 1.0
        w = e / (E0 * eta * eta) + 1.0
        Pc = (a + b / w) * r * e + A * mu + B * mu * mu
        if eta >= 1.0 or e <= Eiv:
            p = Pc
            if eta < 0.8 and eta < 1.0:      # cold, strongly expanded: cavitated, no tension
                p = 0.0
        else:
            z = 1.0 / eta - 1.0
            Pe = a * r * e + (b * r * e / w + A * mu * math.exp(-be * z)) * math.exp(-al * z * z)
            if e >= Ecv:
                p = Pe
            else:
                p = ((e - Eiv) * Pe + (Ecv - e) * Pc) / (Ecv - Eiv)
        if p < 0.0:
            p = 0.0
        P[i] = p
        k = A + 2.0 * B * max(mu, 0.0)
        c2 = max(k, 0.25 * A) / rho0 + (a + b) * e
        c[i] = math.sqrt(c2)
    return P, c


@njit(parallel=True, cache=True, fastmath=True)
def sph_forces(pos, vel, m, H, rho, P, c, bal, rowptr, nb, alpha, beta):
    N = pos.shape[0]
    acc = np.zeros((N, 3))
    du = np.zeros(N)
    vsig = np.zeros(N)
    for i in prange(N):
        Pi = P[i] / (rho[i] * rho[i])
        ax = 0.0
        ay = 0.0
        az = 0.0
        de = 0.0
        vs = c[i]
        for p in range(rowptr[i], rowptr[i + 1]):
            j = nb[p]
            Hij = 0.5 * (H[i] + H[j])
            dx = pos[i, 0] - pos[j, 0]
            dy = pos[i, 1] - pos[j, 1]
            dz = pos[i, 2] - pos[j, 2]
            r2 = dx * dx + dy * dy + dz * dz
            r = math.sqrt(r2)
            if r >= Hij:
                continue
            vx = vel[i, 0] - vel[j, 0]
            vy = vel[i, 1] - vel[j, 1]
            vz = vel[i, 2] - vel[j, 2]
            vr = vx * dx + vy * dy + vz * dz
            g = _dwendland_over_r(r, Hij)
            Pij = Pi + P[j] / (rho[j] * rho[j])
            visc = 0.0
            cij = 0.5 * (c[i] + c[j])
            if vr < 0.0:
                hij = 0.5 * Hij
                mu = hij * vr / (r2 + 0.01 * hij * hij)
                rhoij = 0.5 * (rho[i] + rho[j])
                visc = 0.5 * (bal[i] + bal[j]) * (-alpha * cij * mu + beta * mu * mu) / rhoij
                w = vr / max(r, 1e-12)
                s = c[i] + c[j] - 3.0 * w
                if s > vs:
                    vs = s
            f = m[j] * (Pij + visc) * g
            ax -= f * dx
            ay -= f * dy
            az -= f * dz
            de += m[j] * (Pi + 0.5 * visc) * g * vr
        acc[i, 0] = ax
        acc[i, 1] = ay
        acc[i, 2] = az
        du[i] = de
        vsig[i] = vs
    return acc, du, vsig


# ---------------------------------------------------------------- octree -----
@njit(cache=True, inline="always")
def _spread3(v):
    v = v & 0x1FFFFF
    v = (v | (v << 32)) & 0x1F00000000FFFF
    v = (v | (v << 16)) & 0x1F0000FF0000FF
    v = (v | (v << 8)) & 0x100F00F00F00F00F
    v = (v | (v << 4)) & 0x10C30C30C30C30C3
    v = (v | (v << 2)) & 0x1249249249249249
    return v


@njit(parallel=True, cache=True)
def morton_keys(pos, lo, size):
    N = pos.shape[0]
    keys = np.empty(N, np.int64)
    s = 2097151.0 / size
    for i in prange(N):
        ix = np.int64(min(max((pos[i, 0] - lo[0]) * s, 0.0), 2097151.0))
        iy = np.int64(min(max((pos[i, 1] - lo[1]) * s, 0.0), 2097151.0))
        iz = np.int64(min(max((pos[i, 2] - lo[2]) * s, 0.0), 2097151.0))
        keys[i] = (_spread3(ix) << 2) | (_spread3(iy) << 1) | _spread3(iz)
    return keys


@njit(cache=True)
def build_tree(keys, lo, size, leaf_size, max_nodes):
    """Pre-order linear octree over Morton-sorted particles. Returns n_nodes (or -1 if too small)."""
    N = keys.shape[0]
    nstart = np.empty(max_nodes, np.int64)
    nend = np.empty(max_nodes, np.int64)
    nlevel = np.empty(max_nodes, np.int64)
    ncen = np.empty((max_nodes, 3))
    nparent = np.empty(max_nodes, np.int64)
    st_s = np.empty(64 * 8, np.int64)
    st_e = np.empty(64 * 8, np.int64)
    st_l = np.empty(64 * 8, np.int64)
    st_p = np.empty(64 * 8, np.int64)
    st_c = np.empty((64 * 8, 3))
    sp = 0
    st_s[0] = 0
    st_e[0] = N
    st_l[0] = 0
    st_p[0] = -1
    st_c[0, 0] = lo[0] + 0.5 * size
    st_c[0, 1] = lo[1] + 0.5 * size
    st_c[0, 2] = lo[2] + 0.5 * size
    sp = 1
    n = 0
    bs = np.empty(9, np.int64)
    while sp > 0:
        sp -= 1
        s = st_s[sp]
        e = st_e[sp]
        L = st_l[sp]
        if n >= max_nodes:
            return -1, nstart, nend, nlevel, ncen, nparent
        nstart[n] = s
        nend[n] = e
        nlevel[n] = L
        nparent[n] = st_p[sp]
        cx = st_c[sp, 0]
        cy = st_c[sp, 1]
        cz = st_c[sp, 2]
        ncen[n, 0] = cx
        ncen[n, 1] = cy
        ncen[n, 2] = cz
        me = n
        n += 1
        if e - s <= leaf_size or L >= 20:
            continue
        shift = 3 * (20 - L)
        # boundaries of the 8 octants (keys sorted, prefix shared within the node)
        q = s
        for o in range(8):
            bs[o] = q
            while q < e and ((keys[q] >> shift) & 7) == o:
                q += 1
        bs[8] = e
        quarter = size / (2.0 ** (L + 2))
        for o in range(7, -1, -1):
            a = bs[o]
            b = bs[o + 1]
            if b > a:
                st_s[sp] = a
                st_e[sp] = b
                st_l[sp] = L + 1
                st_p[sp] = me
                st_c[sp, 0] = cx + (quarter if (o >> 2) & 1 else -quarter)
                st_c[sp, 1] = cy + (quarter if (o >> 1) & 1 else -quarter)
                st_c[sp, 2] = cz + (quarter if o & 1 else -quarter)
                sp += 1
    return n, nstart, nend, nlevel, ncen, nparent


@njit(cache=True)
def tree_moments(n, nstart, nend, nlevel, ncen, nparent, ps, ms, size):
    cm = np.zeros(ps.shape[0] + 1)
    cx = np.zeros((ps.shape[0] + 1, 3))
    for i in range(ps.shape[0]):
        cm[i + 1] = cm[i] + ms[i]
        for d in range(3):
            cx[i + 1, d] = cx[i, d] + ms[i] * ps[i, d]
    nmass = np.empty(n)
    ncom = np.empty((n, 3))
    nsize = np.empty(n)
    ndelta = np.empty(n)
    nnext = np.empty(n, np.int64)
    sub = np.ones(n, np.int64)
    leaf = np.ones(n, np.bool_)
    for k in range(n - 1, -1, -1):
        p = nparent[k]
        if p >= 0:
            sub[p] += sub[k]
            leaf[p] = False
    for k in range(n):
        s = nstart[k]
        e = nend[k]
        M = cm[e] - cm[s]
        nmass[k] = M
        dd = 0.0
        for d in range(3):
            v = (cx[e, d] - cx[s, d]) / M
            ncom[k, d] = v
            dd += (v - ncen[k, d]) ** 2
        nsize[k] = size / (2.0 ** nlevel[k])
        ndelta[k] = math.sqrt(dd)
        nnext[k] = k + sub[k]
    return nmass, ncom, nsize, ndelta, nnext, leaf


@njit(parallel=True, cache=True, fastmath=True)
def tree_walk(ps, ms, n, nstart, nend, nmass, ncom, nsize, ndelta, nnext, leaf, theta, eps2):
    N = ps.shape[0]
    acc = np.zeros((N, 3))
    phi = np.zeros(N)
    for i in prange(N):
        xi = ps[i, 0]
        yi = ps[i, 1]
        zi = ps[i, 2]
        ax = 0.0
        ay = 0.0
        az = 0.0
        ph = 0.0
        k = 0
        while k < n:
            dx = ncom[k, 0] - xi
            dy = ncom[k, 1] - yi
            dz = ncom[k, 2] - zi
            r2 = dx * dx + dy * dy + dz * dz
            d = math.sqrt(r2) - ndelta[k]
            if d > 0.0 and nsize[k] < theta * d:
                r2 += eps2
                ir = 1.0 / math.sqrt(r2)
                f = nmass[k] * ir * ir * ir
                ax += f * dx
                ay += f * dy
                az += f * dz
                ph -= nmass[k] * ir
                k = nnext[k]
                continue
            if leaf[k]:
                for j in range(nstart[k], nend[k]):
                    if j == i:
                        continue
                    dx = ps[j, 0] - xi
                    dy = ps[j, 1] - yi
                    dz = ps[j, 2] - zi
                    r2 = dx * dx + dy * dy + dz * dz + eps2
                    ir = 1.0 / math.sqrt(r2)
                    f = ms[j] * ir * ir * ir
                    ax += f * dx
                    ay += f * dy
                    az += f * dz
                    ph -= ms[j] * ir
                k = nnext[k]
            else:
                k += 1
        acc[i, 0] = ax
        acc[i, 1] = ay
        acc[i, 2] = az
        phi[i] = ph
    return acc, phi


def gravity(pos, m, theta, eps, leaf_size=8):
    lo = pos.min(axis=0)
    size = float((pos.max(axis=0) - lo).max()) * 1.0001 + 1e-9
    keys = morton_keys(pos, lo, size)
    order = np.argsort(keys, kind="stable")
    ks = keys[order]
    ps = np.ascontiguousarray(pos[order])
    ms = np.ascontiguousarray(m[order])
    max_nodes = max(4 * len(pos) // leaf_size * 8, 1024)
    while True:
        n, ns, ne, nl, nc, npar = build_tree(ks, lo, size, leaf_size, max_nodes)
        if n > 0:
            break
        max_nodes *= 2
    nm, ncom, nsz, nd, nnx, lf = tree_moments(n, ns, ne, nl, nc, npar, ps, ms, size)
    a_s, p_s = tree_walk(ps, ms, n, ns, ne, nm, ncom, nsz, nd, nnx, lf, theta, eps * eps)
    acc = np.empty_like(a_s)
    phi = np.empty_like(p_s)
    acc[order] = a_s
    phi[order] = p_s
    return acc, phi


# ============================================================================
# simulation state / physics driver
# ============================================================================
class Sim:
    def __init__(self, cfg, mat_tab_idx, tab, ext=None):
        self.cfg = cfg
        self.tab = tab                    # (n_mat, 10) code-unit Tillotson table
        self.mat_tab_idx = mat_tab_idx    # per contract material id -> table row
        self.ext = ext                    # external body (Jupiter) dict or None
        self.H0 = None
        self.eps = None
        self.timing = {}

    def _tic(self, k, t0):
        self.timing[k] = self.timing.get(k, 0.0) + time.perf_counter() - t0

    def forces(self, pos, vel, u, m, mat, active):
        """Return acc, du, H, rho, P, c, phi, dt_suggest (all arrays full length)."""
        cfg = self.cfg
        N = len(pos)
        ia = np.nonzero(active)[0]
        p = np.ascontiguousarray(pos[ia])
        v = np.ascontiguousarray(vel[ia])
        mm = np.ascontiguousarray(m[ia])
        uu = np.ascontiguousarray(u[ia])
        K = min(cfg["n_neighbours"], len(ia) - 1)
        t0 = time.perf_counter()
        self._ncall = getattr(self, "_ncall", 0) + 1
        cache = getattr(self, "_lists", None)
        if cache is None or cache[0] != len(ia) or self._ncall % cfg["neigh_every"] == 0:
            C = min(K + cfg["neigh_extra"], len(ia) - 1)
            tree = cKDTree(p)
            dist, idx = tree.query(p, k=C + 1, workers=-1)
            cand = np.ascontiguousarray(idx[:, 1:]).astype(np.int64)
            self._lists = (len(ia), cand)
            dist = np.ascontiguousarray(dist[:, 1:K + 1])
            idx = np.ascontiguousarray(cand[:, :K])
        else:
            idx, dist = refresh_lists(p, cache[1], K)
        Hk = dist[:, -1] * 1.0001
        if self.H0 is None:
            self.H0 = float(np.median(Hk))
            self.eps = cfg["soft_factor"] * 0.5 * self.H0
        H = np.minimum(Hk, cfg["h_max_factor"] * self.H0)
        self._tic("neigh", t0)
        t0 = time.perf_counter()
        rowptr, nb = build_csr(idx, dist, H)
        rho, div, curl = sph_density(p, v, mm, H, rowptr, nb)
        mi = self.mat_tab_idx[mat[ia]]
        P, c = tillotson(rho, uu, mi, self.tab)
        bal = np.abs(div) / (np.abs(div) + curl + 1e-4 * c / (0.5 * H))
        a_h, du_h, vsig = sph_forces(p, v, mm, H, rho, P, c, bal, rowptr, nb,
                                     cfg["av_alpha"], cfg["av_beta"])
        self._tic("sph", t0)
        t0 = time.perf_counter()
        a_g, phi = gravity(p, mm, cfg["theta"], self.eps)
        self._tic("grav", t0)
        a = a_h + a_g
        if self.ext is not None:
            ae, pe = ext_field(p, self.ext)
            a += ae
            phi = phi + pe
        h = 0.5 * H
        amag = np.sqrt((a * a).sum(1)) + 1e-30
        dt = min(cfg["courant"] * float(np.min(h / vsig)),
                 0.3 * float(np.min(np.sqrt(h / amag))))
        out = dict(acc=np.zeros((N, 3)), du=np.zeros(N), H=np.zeros(N), rho=np.zeros(N),
                   P=np.zeros(N), c=np.zeros(N), phi=np.zeros(N))
        out["acc"][ia] = a
        out["du"][ia] = du_h
        out["H"][ia] = H
        out["rho"][ia] = rho
        out["P"][ia] = P
        out["c"][ia] = c
        out["phi"][ia] = phi
        out["dt"] = dt
        return out


def ext_field(p, ext):
    """Softened Jupiter: uniform-density sphere potential."""
    M, R = ext["mass"], ext["radius"]
    r = np.sqrt((p * p).sum(1))
    inside = r < R
    a = np.empty_like(p)
    g = np.where(inside, M / R ** 3, M / np.maximum(r, 1e-9) ** 3)
    a = -p * g[:, None]
    phi = np.where(inside, -M * (3 * R * R - r * r) / (2 * R ** 3), -M / np.maximum(r, 1e-9))
    return a, phi


def code_tab(mantle):
    """Table rows for contract materials 0..3 -> unique EOS rows."""
    names = ["iron", mantle]
    rows = []
    for nm in names:
        r0, A, B, E0, Eiv, Ecv, a, b, al, be, cv = TILLOTSON[nm]
        rows.append([r0 / RHO_U, A / P_U, B / P_U, E0 / U_U, Eiv / U_U, Ecv / U_U, a, b, al, be])
    tab = np.array(rows, dtype=np.float64)
    mat_tab_idx = np.array([0, 1, 0, 1], dtype=np.int64)   # earth_core, earth_mantle, imp_core, imp_mantle
    cv = np.array([TILLOTSON["iron"][10], TILLOTSON[mantle][10]] * 2)   # J/kg/K per contract id
    return tab, mat_tab_idx, cv


# ============================================================================
# body construction + relaxation
# ============================================================================
def lattice_ball(n, r_in, r_out, rng):
    """~n points of a jittered cubic lattice inside the shell r_in < r < r_out (exactly n)."""
    vol = 4.0 / 3.0 * math.pi * (r_out ** 3 - r_in ** 3)
    d = (vol / n) ** (1.0 / 3.0)
    m = int(math.ceil(r_out / d)) + 2
    g = np.arange(-m, m + 1) * d
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    pts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1) + (rng.random(3) - 0.5) * d
    pts += (rng.random(pts.shape) - 0.5) * 0.15 * d
    r = np.sqrt((pts * pts).sum(1))
    pts = pts[r > r_in]
    r = r[r > r_in]
    o = np.argsort(r)
    pts = pts[o[:n]]
    # rescale radially so the outer radius matches
    rr = np.sqrt((pts * pts).sum(1))
    rmax = rr.max()
    pts *= ((r_in ** 3 + (rr ** 3 - r_in ** 3) * (r_out ** 3 - r_in ** 3) / max(rmax ** 3 - r_in ** 3, 1e-12))
            ** (1 / 3) / np.maximum(rr, 1e-12))[:, None]
    return pts


def make_body(name, n, cfg, rng):
    b = BODIES[name]
    M = b["mass"]
    nc = max(int(round(n * b["core"])), 8)
    nm = n - nc
    # starting guesses: compressed iron ~1.5 rho0, compressed rock ~1.35 rho0 (rescaled by mass)
    comp = 1.0 + 0.5 * min(M, 1.0) ** 0.6
    rho_c = TILLOTSON["iron"][0] * comp / RHO_U
    rho_m = TILLOTSON[cfg["mantle_material"]][0] * (1.0 + 0.35 * min(M, 1.0) ** 0.6) / RHO_U
    rc = (M * b["core"] / (4 / 3 * math.pi * rho_c)) ** (1 / 3)
    R = (rc ** 3 + M * (1 - b["core"]) / (4 / 3 * math.pi * rho_m)) ** (1 / 3)
    pc = lattice_ball(nc, 0.0, rc, rng)
    pm = lattice_ball(nm, rc, R, rng)
    pos = np.vstack([pc, pm])
    mat = np.concatenate([np.zeros(nc, np.uint8), np.ones(nm, np.uint8)])
    m = np.full(n, M / n)
    return pos, mat, m, R


def u_from_T(mat, T, cv):
    return cv[mat] * T / U_U


def relax_body(name, n, cfg, cache_root, mpp=None):
    """Damped, isentropic relaxation of one body in isolation. Cached on disk."""
    tag = f"relaxed_{name}_{n}_{cfg['mantle_material']}_k{cfg['n_neighbours']}.npz"
    fn = os.path.join(cache_root, "_bodies", tag)
    if os.path.exists(fn):
        d = np.load(fn)
        print(f"[relax] using cached {fn}")
        return {k: d[k] for k in d.files}
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    rng = np.random.default_rng(abs(hash(name)) % 2 ** 32)
    pos, mat, m, R0 = make_body(name, n, cfg, rng)
    tab, mti, cv = code_tab(cfg["mantle_material"])
    u = u_from_T(mat, cfg["T_initial_K"], cv)
    vel = np.zeros_like(pos)
    sim = Sim(cfg, mti, tab)
    act = np.ones(n, bool)
    f = sim.forces(pos, vel, u, m, mat, act)
    t = 0.0
    t_end = cfg["relax_time"] + cfg["relax_check"]
    tw = time.perf_counter()
    step = 0
    log = []
    while t < t_end:
        dt = min(f["dt"], 0.05)
        damped = t < cfg["relax_time"]
        vel += 0.5 * dt * f["acc"]
        pos += dt * vel
        f = sim.forces(pos, vel, u, m, mat, act)
        vel += 0.5 * dt * f["acc"]
        if damped:
            # strong damping early, weaker later (tau 0.15 -> 0.6 time units)
            tau = 0.15 + 0.45 * t / cfg["relax_time"]
            vel *= math.exp(-dt / tau)
            vel -= (vel * m[:, None]).sum(0) / m.sum()
        t += dt
        step += 1
        if step % 50 == 0 or t >= t_end:
            vr = math.sqrt((vel ** 2).sum(1).mean()) * V_U
            r = np.sqrt(((pos - pos.mean(0)) ** 2).sum(1))
            R99 = np.percentile(r, 99.0)
            log.append((t, vr, R99))
            print(f"[relax {name} N={n}] t={t:6.2f} {'damped' if damped else 'FREE  '} "
                  f"dt={dt:.4f} v_rms={vr:7.1f} m/s  R99={R99:.3f} R_E  ({time.perf_counter() - tw:.0f}s)")
    pos -= (pos * m[:, None]).sum(0) / m.sum()
    vel -= (vel * m[:, None]).sum(0) / m.sum()
    r = np.sqrt((pos ** 2).sum(1))
    R = float(np.percentile(r, 99.5))
    out = dict(pos=pos, vel=vel, u=u, m=m, mat=mat, R=np.array(R), log=np.array(log),
               rho=f["rho"], P=f["P"])
    np.savez(fn, **out)
    print(f"[relax] {name}: radius {R:.3f} R_E = {R * R_E / 1e3:.0f} km, "
          f"central P {f['P'].max() * P_U / 1e9:.0f} GPa, rho range "
          f"{f['rho'].min() * RHO_U:.0f}-{f['rho'].max() * RHO_U:.0f} kg/m3")
    return out


# ============================================================================
# scenario setup
# ============================================================================
def two_body_start(Mt, Mi, Rt, Ri, v_rel, angle_deg, sep_factor):
    mu = Mt + Mi
    rc = Rt + Ri
    vesc = math.sqrt(2 * mu / rc)
    v = v_rel * vesc
    th = math.radians(angle_deg)
    E = 0.5 * v * v - mu / rc
    L = rc * v * math.sin(th)
    d0 = sep_factor * rc
    v0 = math.sqrt(2 * (E + mu / d0))
    s0 = min(L / (d0 * v0), 1.0)
    c0 = math.sqrt(1 - s0 * s0)
    r_rel = np.array([d0, 0.0, 0.0])            # impactor relative to target
    v_rel_vec = np.array([-v0 * c0, v0 * s0, 0.0])
    # time to contact (numerical radial integration of the Kepler orbit)
    r = d0
    vr = -v0 * c0
    t = 0.0
    dtt = 1e-4
    while r > rc and t < 50:
        ar = -mu / r ** 2 + L * L / r ** 3
        vr += ar * dtt
        r += vr * dtt
        t += dtt
    return r_rel, v_rel_vec, vesc, t


def setup_scenario(cfg, cache_root):
    sc = SCENARIOS[cfg["scenario"]]
    N = cfg["n_particles"]
    tab, mti, cv = code_tab(cfg["mantle_material"])
    info = dict(scenario=cfg["scenario"])
    if sc.get("external") == "jupiter":
        b = relax_body(sc["impactor"], N, cfg, cache_root)
        pos, vel, u, m, mat = b["pos"].copy(), b["vel"].copy(), b["u"].copy(), b["m"].copy(), b["mat"].copy()
        MJ, RJ = JUPITER["mass"], JUPITER["radius"]
        q = sc["periapsis"] * RJ
        d0 = sc["start_dist"]
        # parabolic orbit with periapsis q (inside Jupiter -> impact after tidal stretching)
        L = math.sqrt(2 * MJ * q)
        v0 = math.sqrt(2 * MJ / d0)
        s0 = L / (d0 * v0)
        pos += np.array([d0, 0, 0])
        vel += np.array([-v0 * math.sqrt(1 - s0 * s0), v0 * s0, 0])
        ext = dict(mass=MJ, radius=RJ)
        info["bodies"] = [dict(name="Earth", role="impactor", mass_ME=BODIES["earth"]["mass"],
                               radius_RE=float(b["R"]), materials=[0, 1], n=int(N)),
                          dict(name="Jupiter", role="external_softened_sphere", mass_ME=MJ, radius_RE=RJ,
                               pos=[0.0, 0.0, 0.0], materials=[])]
        info["materials"] = {"0": "earth_core", "1": "earth_mantle", "2": "unused", "3": "unused"}
        info["notes"] = "Jupiter is a fixed softened sphere at the origin; Earth particles that enter it are absorbed (frozen, flag absorbed=1)."
        return pos, vel, u, m, mat, ext, info
    if cfg["scenario"] == "speed_series":
        v_rel, ang = SPEED_SERIES[cfg["variant"]]
    else:
        v_rel, ang = sc["v_rel"], sc["angle"]
    Mt = BODIES[sc["target"]]["mass"]
    Mi = BODIES[sc["impactor"]]["mass"]
    Mtot = Mt + Mi
    Ni = max(int(round(N * Mi / Mtot)), 200)
    Nt = N - Ni
    bt = relax_body(sc["target"], Nt, cfg, cache_root)
    bi = relax_body(sc["impactor"], Ni, cfg, cache_root)
    Rt, Ri = float(bt["R"]), float(bi["R"])
    r_rel, v_relv, vesc, t_contact = two_body_start(Mt, Mi, Rt, Ri, v_rel, ang, cfg["start_sep_contact"])
    pos = np.vstack([bt["pos"] - r_rel * Mi / Mtot, bi["pos"] + r_rel * Mt / Mtot])
    vel = np.vstack([bt["vel"] - v_relv * Mi / Mtot, bi["vel"] + v_relv * Mt / Mtot])
    u = np.concatenate([bt["u"], bi["u"]])
    m = np.concatenate([bt["m"], bi["m"]])
    mat = np.concatenate([bt["mat"], bi["mat"] + 2]).astype(np.uint8)
    info["impact"] = dict(v_imp_over_vesc=v_rel, angle_deg=ang,
                          v_esc_kms=vesc * V_U / 1e3, v_imp_kms=v_rel * vesc * V_U / 1e3,
                          time_to_contact_hours=t_contact * T_U / 3600)
    info["bodies"] = [dict(name=BODIES[sc["target"]]["label"], role="target", mass_ME=Mt, radius_RE=Rt,
                           n=int(Nt), materials=[0, 1]),
                      dict(name=BODIES[sc["impactor"]]["label"], role="impactor", mass_ME=Mi, radius_RE=Ri,
                           n=int(Ni), materials=[2, 3])]
    info["materials"] = {"0": "earth_core", "1": "earth_mantle", "2": "impactor_core", "3": "impactor_mantle"}
    print(f"[setup] {sc['target']} ({Nt}) + {sc['impactor']} ({Ni}); v_esc={vesc * V_U / 1e3:.2f} km/s, "
          f"v_imp={v_rel * vesc * V_U / 1e3:.2f} km/s, angle {ang:.0f} deg, contact in "
          f"{t_contact * T_U / 3600:.2f} h")
    return pos, vel, u, m, mat, None, info


# ============================================================================
# diagnostics
# ============================================================================
def analyse(pos, vel, m, mat, phi, rho, u, absorbed=None):
    """Bound / unbound / disc / planet mass fractions (Canup-style iterative estimate)."""
    act = np.ones(len(m), bool) if absorbed is None else ~absorbed
    p, v, mm, ph = pos[act], vel[act], m[act], phi[act]
    com = (p * mm[:, None]).sum(0) / mm.sum()
    vcm = (v * mm[:, None]).sum(0) / mm.sum()
    p = p - com
    v = v - vcm
    e = 0.5 * (v * v).sum(1) + ph
    unbound = e > 0
    # planet: start with dense particles near the potential minimum
    r = np.sqrt((p * p).sum(1))
    c0 = p[np.argmin(ph)]
    rp = np.sqrt(((p - c0) ** 2).sum(1))
    Rp = 1.0
    planet = (rp < Rp) & ~unbound
    for _ in range(10):
        Mp = mm[planet].sum()
        cp = (p[planet] * mm[planet, None]).sum(0) / Mp
        vp = (v[planet] * mm[planet, None]).sum(0) / Mp
        x = p - cp
        w = v - vp
        rr = np.sqrt((x * x).sum(1))
        # planet radius from mean density ~ 5.5 g/cc * (M)^(~0.25 compression) -> R ~ M^0.28
        Rp = max(Mp ** 0.28, 0.3)
        eps = 0.5 * (w * w).sum(1) - Mp / np.maximum(rr, 1e-6)
        Lv = np.cross(x, w)
        L2 = (Lv * Lv).sum(1)
        a = -Mp / (2 * np.minimum(eps, -1e-12))
        ecc = np.sqrt(np.maximum(1 + 2 * eps * L2 / Mp ** 2, 0))
        q = a * (1 - ecc)
        bound2 = (eps < 0) & ~unbound
        new_planet = (rr < Rp) | (bound2 & (q < Rp))
        if np.array_equal(new_planet, planet):
            break
        planet = new_planet
    disc = ~planet & ~unbound & bound2
    rest = ~planet & ~unbound & ~disc
    Mtot = mm.sum()
    Mmoon = disc.sum() and mm[disc].sum()
    # Lunar-mass estimate from disc angular momentum (Canup & Asphaug 2001/Ida et al.)
    Ld = np.sqrt(L2[disc]).sum() * (mm[disc].mean() if disc.any() else 0)
    aR = 2.9 * Rp
    M_moon_pred = (1.9 * Ld / (Mmoon * math.sqrt(Mp * aR)) - 1.1 - 1.9 * 0.05) * Mmoon if disc.any() else 0.0
    return dict(M_total=float(Mtot), planet=float(mm[planet].sum() / Mtot),
                disc=float(Mmoon / Mtot if disc.any() else 0.0), unbound=float(mm[unbound].sum() / Mtot),
                other=float(mm[rest].sum() / Mtot), planet_radius=float(Rp),
                disc_mass_lunar=float(Mmoon / 0.0123) if disc.any() else 0.0,
                moon_pred_lunar=float(max(M_moon_pred, 0) / 0.0123),
                impactor_frac_in_disc=float(mm[disc & (mat[act] >= 2)].sum() / max(Mmoon, 1e-30)) if disc.any() else 0.0,
                iron_frac_in_disc=float(mm[disc & ((mat[act] == 0) | (mat[act] == 2))].sum() / max(Mmoon, 1e-30)) if disc.any() else 0.0)


def energies(vel, m, u, phi, ext_phi_mask=None):
    ke = 0.5 * (m * (vel * vel).sum(1)).sum()
    ie = (m * u).sum()
    pe = 0.5 * (m * phi).sum()
    return ke, ie, pe


# ============================================================================
# output (shared cache contract)
# ============================================================================
def temp_norm(T_K, cfg):
    lo, hi = math.log(cfg["T_cold_K"]), math.log(cfg["T_hot_K"])
    return np.clip((np.log(np.maximum(T_K, 1.0)) - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def write_frame(path, pos, vel, u, rho, H, mat, cv, cfg, center, absorbed):
    T_K = cv[mat] * 0 + u * U_U / cv[mat]
    np.savez_compressed(
        path,
        pos=(pos - center).astype(np.float32),
        vel=(vel * V_U / 1e3).astype(np.float16),       # km/s
        u=(u * U_U).astype(np.float32),                  # J/kg
        temp=temp_norm(T_K, cfg),
        T_K=T_K.astype(np.float32),
        rho=(rho * RHO_U).astype(np.float32),            # kg/m^3
        h=(0.5 * H).astype(np.float32),                  # smoothing length h = H/2, Earth radii
        mat=mat.astype(np.uint8),
        absorbed=absorbed.astype(np.uint8),
    )


def retemp(rdir, cfg):
    """Re-write the normalised `temp` field of an existing cache with the CONFIG mapping."""
    files = sorted(f for f in os.listdir(rdir) if f.startswith("frame_") and f.endswith(".npz"))
    for fn in files:
        p = os.path.join(rdir, fn)
        z = dict(np.load(p))
        z["temp"] = temp_norm(z["T_K"], cfg)
        np.savez_compressed(p + ".tmp.npz", **z)
        os.replace(p + ".tmp.npz", p)
    mp = os.path.join(rdir, "meta.json")
    meta = json.load(open(mp))
    meta["temp_mapping"] = dict(T_cold_K=cfg["T_cold_K"], T_hot_K=cfg["T_hot_K"], scale="log")
    json.dump(meta, open(mp, "w"), indent=1)
    print(f"[retemp] {len(files)} frames in {rdir}")


def run(cfg):
    if cfg["threads"]:
        numba.set_num_threads(cfg["threads"])
    sc = SCENARIOS[cfg["scenario"]]
    if cfg.get("hours") is None:
        cfg["hours"] = sc["hours"]
    cache_root = cfg["cache_dir"] or os.path.join(os.getcwd(), "cache")
    name = cfg["run_name"] or (cfg["scenario"] + (f"_v{cfg['variant']}" if cfg["scenario"] == "speed_series" else ""))
    rdir = os.path.join(cache_root, name)
    os.makedirs(rdir, exist_ok=True)
    ck = os.path.join(rdir, "checkpoint.npz")
    tab, mti, cv = code_tab(cfg["mantle_material"])
    dt_out = cfg["out_every_min"] * 60.0 / T_U
    n_frames = int(round(cfg["hours"] * 3600.0 / T_U / dt_out)) + 1

    if os.path.exists(ck) and not cfg.get("fresh"):
        d = np.load(ck, allow_pickle=True)
        pos, vel, u, m, mat = d["pos"], d["vel"], d["u"], d["m"], d["mat"]
        absorbed = d["absorbed"]
        t, frame = float(d["t"]), int(d["frame"])
        info = json.loads(str(d["info"]))
        H0 = float(d["H0"])
        ext = info.get("_ext")
        print(f"[resume] {rdir} at t={t * T_U / 3600:.2f} h, next frame {frame}")
    else:
        pos, vel, u, m, mat, ext, info = setup_scenario(cfg, cache_root)
        info["_ext"] = ext
        absorbed = np.zeros(len(m), bool)
        t, frame, H0 = 0.0, 0, None
    N = len(m)
    sim = Sim(cfg, mti, tab, ext)
    if H0 is not None:
        sim.H0 = H0
        sim.eps = cfg["soft_factor"] * 0.5 * H0
    center = np.zeros(3) if ext is not None else (pos * m[:, None]).sum(0) / m.sum()

    meta = dict(scenario=cfg["scenario"], n_particles=int(N), frame_count=int(n_frames), fps_hint=30,
                length_unit_km=R_E / 1e3, time_unit_hours=dt_out * T_U / 3600.0,
                materials=info["materials"], bodies=info["bodies"],
                impact=info.get("impact"),
                fields=dict(pos="Earth radii, system-COM frame (Jupiter frame for earth_into_jupiter)",
                            vel="km/s float16", u="J/kg", temp="0..1 = log(T/T_cold)/log(T_hot/T_cold)",
                            T_K="rough temperature u/c_v (K)", rho="kg/m^3", h="smoothing length (Earth radii)",
                            mat="uint8 material id", absorbed="1 = swallowed by external body"),
                temp_mapping=dict(T_cold_K=cfg["T_cold_K"], T_hot_K=cfg["T_hot_K"], scale="log"),
                code_units=dict(time_s=T_U, velocity_m_s=V_U, length_m=R_E, mass_kg=M_E),
                sim=dict(eos="Tillotson iron + " + cfg["mantle_material"], kernel="Wendland C2",
                         n_neighbours=cfg["n_neighbours"], gravity="Barnes-Hut theta=%.2f" % cfg["theta"],
                         out_every_min=cfg["out_every_min"], hours=cfg["hours"]),
                notes=info.get("notes", ""), frames_written=frame)
    def save_meta(fw):
        meta["frames_written"] = int(fw)
        with open(os.path.join(rdir, "meta.json"), "w") as fh:
            json.dump(meta, fh, indent=1)
    save_meta(frame)
    print(f"[run] {name}: N={N}, {n_frames} frames every {cfg['out_every_min']} min "
          f"({cfg['hours']} h simulated), 1 code time unit = {T_U:.1f} s")

    f = sim.forces(pos, vel, u, m, mat, ~absorbed)
    E0 = None
    t_start = time.perf_counter()
    steps = 0
    t_next = frame * dt_out
    while frame < n_frames:
        # write frame(s) due at the current time
        if t >= t_next - 1e-12:
            write_frame(os.path.join(rdir, f"frame_{frame:05d}.npz"), pos, vel, u, f["rho"], f["H"],
                        mat, cv, cfg, center, absorbed)
            ke, ie, pe = energies(vel[~absorbed], m[~absorbed], u[~absorbed], f["phi"][~absorbed])
            Et = ke + ie + pe
            if E0 is None:
                E0 = Et
            el = time.perf_counter() - t_start
            msg = (f"[frame {frame:4d}/{n_frames}] t={t * T_U / 3600:6.2f} h  steps={steps:6d} "
                   f"dt={f['dt'] * T_U:5.1f}s  E/E0-1={(Et - E0) / abs(E0):+.4f}  "
                   f"T_max={np.max(u * U_U / cv[mat]):6.0f}K  wall={el:7.0f}s "
                   f"({el / max(steps, 1):.3f}s/step)")
            if frame % 15 == 0 or frame == n_frames - 1:
                an = analyse(pos, vel, m, mat, f["phi"], f["rho"], u, absorbed)
                msg += (f"\n      planet={an['planet']:.3f} disc={an['disc']:.4f} ({an['disc_mass_lunar']:.2f} M_moon, "
                        f"pred. moon {an['moon_pred_lunar']:.2f}) unbound={an['unbound']:.4f} "
                        f"mass={an['M_total']:.5f}  timing " +
                        " ".join(f"{k}={v / max(steps, 1):.3f}" for k, v in sim.timing.items()))
            print(msg, flush=True)
            frame += 1
            t_next = frame * dt_out
            if frame % cfg["checkpoint_every"] == 0 or frame == n_frames:
                info_s = json.dumps(info)
                np.savez(ck + ".tmp.npz", pos=pos, vel=vel, u=u, m=m, mat=mat, absorbed=absorbed,
                         t=t, frame=frame, info=info_s, H0=sim.H0)
                os.replace(ck + ".tmp.npz", ck)
                save_meta(frame)
            if frame >= n_frames:
                break
        dt = min(f["dt"], t_next - t)
        dt = max(dt, 1e-7)
        act = ~absorbed
        vel[act] += 0.5 * dt * f["acc"][act]
        u[act] = np.maximum(u[act] + 0.5 * dt * f["du"][act], 1e-6)
        pos[act] += dt * vel[act]
        vpred = vel.copy()
        upred = u.copy()
        vpred[act] += 0.5 * dt * f["acc"][act]
        upred[act] = np.maximum(u[act] + 0.5 * dt * f["du"][act], 1e-6)
        if ext is not None:
            r = np.sqrt((pos * pos).sum(1))
            newly = act & (r < ext["radius"])
            if newly.any():
                absorbed |= newly
                vel[newly] = 0.0
                vpred[newly] = 0.0
                act = ~absorbed
        f = sim.forces(pos, vpred, upred, m, mat, act)
        vel[act] += 0.5 * dt * f["acc"][act]
        u[act] = np.maximum(u[act] + 0.5 * dt * f["du"][act], 1e-6)
        t += dt
        steps += 1
    save_meta(frame)
    an = analyse(pos, vel, m, mat, f["phi"], f["rho"], u, absorbed)
    an["seconds_per_step"] = (time.perf_counter() - t_start) / max(steps, 1)
    an["steps"] = steps
    with open(os.path.join(rdir, "final_analysis.json"), "w") as fh:
        json.dump(an, fh, indent=1)
    print("[done]", json.dumps(an, indent=1))
    return rdir


def bench(ns, cfg):
    """Seconds per force evaluation (one step) for relaxed-like spheres of N particles."""
    tab, mti, cv = code_tab(cfg["mantle_material"])
    for n in ns:
        rng = np.random.default_rng(1)
        pos, mat, m, R = make_body("proto_earth", n, cfg, rng)
        u = u_from_T(mat, 2000.0, cv)
        vel = np.zeros_like(pos)
        sim = Sim(cfg, mti, tab)
        sim.forces(pos, vel, u, m, mat, np.ones(n, bool))   # JIT warm-up
        sim.timing = {}
        reps = 3 if n <= 300000 else 1
        t0 = time.perf_counter()
        for _ in range(reps):
            sim.forces(pos, vel, u, m, mat, np.ones(n, bool))
        dt = (time.perf_counter() - t0) / reps
        print(f"[bench] N={n:8d}: {dt:.3f} s/step  (" +
              " ".join(f"{k}={v / reps:.3f}" for k, v in sim.timing.items()) +
              f")  threads={numba.get_num_threads()}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario")
    ap.add_argument("--variant", type=int)
    ap.add_argument("--n", type=int, dest="n_particles")
    ap.add_argument("--hours", type=float)
    ap.add_argument("--out-min", type=float, dest="out_every_min")
    ap.add_argument("--cache-dir", dest="cache_dir")
    ap.add_argument("--run-name", dest="run_name")
    ap.add_argument("--relax-time", type=float, dest="relax_time")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--retemp", help="re-normalise temp in an existing run dir (after changing T_cold/T_hot)")
    ap.add_argument("--bench", type=str, help="comma list of N for timing, e.g. 50000,200000")
    a = ap.parse_args()
    cfg = dict(CONFIG)
    for k, v in vars(a).items():
        if v is not None and k in cfg:
            cfg[k] = v
    cfg["fresh"] = a.fresh
    if a.hours is None:
        cfg["hours"] = SCENARIOS[cfg["scenario"]]["hours"] if a.scenario else cfg["hours"]
    if a.list:
        for k, v in SCENARIOS.items():
            print(k, v)
        print("speed_series variants:", SPEED_SERIES)
        return
    if a.retemp:
        retemp(a.retemp, cfg)
        return
    if a.bench:
        bench([int(x) for x in a.bench.split(",")], cfg)
        return
    run(cfg)


if __name__ == "__main__":
    main()
