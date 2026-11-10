"""A detailed Milky Way band built directly in frame coordinates (the camera is locked, so it is computed once).
The lib StarSky plate is tuned for a wide field; at this framing its band filled the whole sky like a cloud deck.
Here: a band with a bulging warm core, multi-scale star clouds, a dark rift plus filamentary dust, a soft halo,
blue-white outer arms, and ~150k faint stars concentrated in the bright clouds (avoiding the dust). Linear radiance.
"""
import math
import numpy as np, cv2
from lib.core import f32, fbm2, bbcolor


def _noise(H, W, seed, beta, scale=1):
    h, w = max(64, H // scale), max(64, W // scale)
    n = fbm2((h, w), seed, beta)
    return cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC) if scale > 1 else n


def milky_way(W, H, core, ang_deg, s=1.0, seed=5, n_stars=150000, gain=1.0, vivid=False):
    """core: frame (x, y) of the galactic centre; ang_deg: band direction, degrees above the +x axis (towards up-right)."""
    cx, cy = core
    a = math.radians(ang_deg); dx, dy = math.cos(a), -math.sin(a)
    yy, xx = np.mgrid[0:H, 0:W].astype(f32)
    u = (xx - cx) * dx + (yy - cy) * dy                       # along the band (+ = away from the core, up the sky)
    v = -(xx - cx) * dy + (yy - cy) * dx                      # across
    nW = _noise(H, W, seed + 1, 3.2, 4)                       # very large: band meander
    nA = _noise(H, W, seed + 2, 2.5, 2)                       # star clouds
    nB = _noise(H, W, seed + 3, 1.7)                          # fine mottling
    nC = _noise(H, W, seed + 4, 2.8, 2)                       # rift edge
    nD = _noise(H, W, seed + 5, 2.3, 2)                       # filaments
    nE = _noise(H, W, seed + 6, 2.0)
    vw = v + 30 * s * nW + 8 * s * nA
    coreb = np.exp(-(u / (230 * s)) ** 2)
    w = s * (110 + 120 * coreb) * (1 + 0.12 * nW)
    band = np.exp(-(vw / w) ** 2)
    halo = np.exp(-np.abs(vw) / (w * 2.6)) * 0.22
    A = 0.35 + 1.8 * coreb + 0.35 * np.exp(-np.maximum(u, 0) / (1400 * s))
    clouds = np.clip(0.60 + 0.55 * nA + 0.12 * nB, 0.06, 2.4)
    # dust: the Great Rift (offset, wandering), filaments (ridged noise), and mottled patches
    rift_c = 0.18 * w + 14 * s * nC
    rift = np.exp(-((vw - rift_c) / (0.20 * w * (1 + 0.35 * nA))) ** 2) * np.clip(0.55 + 0.45 * nC, 0, 1) * (u > -260 * s)
    ridge = 1 - np.abs(nD)
    fil = np.clip((ridge - 0.72) / 0.28, 0, 1) ** 1.5 * np.exp(-(vw / (w * 1.1)) ** 2)
    patches = np.clip(nE * 0.5 + nA * 0.4 - 0.45, 0, 1) * np.exp(-(vw / (w * 0.9)) ** 2)
    dust = np.clip(rift * 0.90 + fil * 0.75 + patches * 0.8, 0, 0.96)
    glow = (band * clouds + halo) * (1 - dust) * A
    warm = np.exp(-(u / ((480 if vivid else 330) * s)) ** 2) * np.exp(-(vw / (w * 1.3)) ** 2)
    if vivid:
        # stylised, saturated palette: gold core with pink fringes, teal / violet nebula tints in the arms
        nT = _noise(H, W, seed + 7, 3.0, 4)
        teal = np.clip(0.5 + 0.9 * nT, 0, 1)[..., None]
        arm = np.array([0.30, 0.80, 1.00], f32) * teal + np.array([0.70, 0.42, 1.00], f32) * (1 - teal)
        core_col = np.array([1.00, 0.60, 0.20], f32)
        pinkz = np.clip(np.exp(-(u / (420 * s)) ** 2) * (np.abs(vw) / w) * 1.4, 0, 1)[..., None]
        core_col = core_col * (1 - pinkz) + np.array([1.0, 0.40, 0.70], f32) * pinkz
        col = arm * (1 - warm[..., None]) + core_col * warm[..., None]
        neb = np.clip(nA * 0.7 + nT * 0.5, 0, 1.5) * np.exp(-(vw / (w * 2.2)) ** 2) * 0.22
        img = glow[..., None] * col + neb[..., None] * arm * 0.5
        ha = np.clip(nB * 0.6 + nA * 0.5 - 0.6, 0, 1) * band * 0.6
        img += ha[..., None] * np.array([1.0, 0.25, 0.55], f32) * glow[..., None]
        img *= (1 + 1.0 * warm)[..., None]
        img = cv2.GaussianBlur(img, (0, 0), 1.0) * 0.95 + cv2.GaussianBlur(img, (0, 0), 14) * 0.45 + cv2.GaussianBlur(img, (0, 0), 60) * 0.22
    else:
        col = np.array([0.66, 0.78, 1.0], f32) * (1 - warm[..., None]) + np.array([1.0, 0.76, 0.48], f32) * warm[..., None]
        ha = np.clip(nB * 0.6 + nA * 0.5 - 0.9, 0, 1) * band * 0.25
        img = glow[..., None] * col + ha[..., None] * np.array([1.0, 0.35, 0.45], f32) * glow[..., None]
        img = cv2.GaussianBlur(img, (0, 0), 1.3) * 0.75 + cv2.GaussianBlur(img, (0, 0), 16) * 0.55
    img *= 0.020
    # faint stars, concentrated in the bright clouds
    r = np.random.default_rng(seed)
    dens = (0.25 + 4.0 * band * clouds * (1 - dust) * (0.5 + A) + 0.6 * halo).astype(np.float64)
    p = dens.ravel() / dens.sum()
    idx = r.choice(W * H, n_stars, p=p)
    sx = idx % W + r.uniform(0, 1, n_stars); sy = idx // W + r.uniform(0, 1, n_stars)
    flux = 0.0016 * r.uniform(0, 1, n_stars) ** (-1 / 1.1); flux = np.minimum(flux, 0.15)
    temps = np.clip(r.lognormal(np.log(5800), 0.35, n_stars), 3000, 20000)
    lut = np.stack([0.5 + 0.5 * bbcolor(T) for T in np.linspace(3000, 20000, 48)])
    c = lut[np.clip(((temps - 3000) / 17000 * 47).astype(int), 0, 47)]
    acc = np.zeros((H + 1, W + 1, 3), f32)
    x0 = np.floor(sx).astype(int); y0 = np.floor(sy).astype(int); fx = (sx - x0)[:, None]; fy = (sy - y0)[:, None]
    val = (flux[:, None] * c).astype(f32)
    for oy, ox, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(acc, (y0 + oy, x0 + ox), val * wg)
    stars = cv2.GaussianBlur(acc[:H, :W], (0, 0), 0.55) * 3.0
    return ((img + stars) * gain).astype(f32), band.astype(f32)
