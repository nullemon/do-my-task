"""The vivid Milky Way of ../milky-way-blackout/mw.py (the look the user liked), rebuilt on an all-sky canvas in GALACTIC
coordinates so it can turn with the real sky: x = galactic longitude (l = 0 at the centre column, wraps), y = latitude.
Same recipe (band meander, star clouds, rift + filaments, gold/pink core, teal/violet arms, Ha knots, faint star dust),
copied and adapted here; mw.py itself is untouched. Linear radiance, cached in SCR."""
import os, math
import numpy as np, cv2
from lib.core import f32, fbm2, bbcolor

WL, HB = 4096, 1536                       # 360 deg x 135 deg (b = +-67.5)
PXD = WL / 360.0


def canvas(cache, seed=5, n_stars=260000):
    if os.path.exists(cache):
        return np.load(cache)["mw"].astype(f32)
    s = 0.95
    yy, xx = np.mgrid[0:HB, 0:WL].astype(f32)
    u = xx - WL / 2                        # along the band (px), 0 = galactic centre
    v = yy - HB / 2                        # across
    au = np.abs(u)
    def nz(sd, beta): return fbm2((HB, WL), seed + sd, beta)
    nW, nA, nB, nC, nD, nE, nT = nz(1, 3.2), nz(2, 2.5), nz(3, 1.7), nz(4, 2.8), nz(5, 2.3), nz(6, 2.0), nz(7, 3.0)
    vw = v + 30 * s * nW + 8 * s * nA
    coreb = np.exp(-(u / (200 * s)) ** 2)
    w = s * (95 + 110 * coreb) * (1 + 0.12 * nW)
    band = np.exp(-(vw / w) ** 2)
    halo = np.exp(-np.abs(vw) / (w * 2.6)) * 0.22
    A = 0.45 + 1.8 * coreb + 0.30 * np.exp(-au / (1100 * s))
    clouds = np.clip(0.60 + 0.55 * nA + 0.12 * nB, 0.06, 2.4)
    rift_c = 0.18 * w + 14 * s * nC
    rift_on = np.clip((1500 - u) / 300, 0, 1) * np.clip((u + 300) / 200, 0, 1)        # Great Rift: core -> Cygnus side
    rift = np.exp(-((vw - rift_c) / (0.20 * w * (1 + 0.35 * nA))) ** 2) * np.clip(0.55 + 0.45 * nC, 0, 1) * rift_on
    ridge = 1 - np.abs(nD)
    fil = np.clip((ridge - 0.72) / 0.28, 0, 1) ** 1.5 * np.exp(-(vw / (w * 1.1)) ** 2)
    patches = np.clip(nE * 0.5 + nA * 0.4 - 0.45, 0, 1) * np.exp(-(vw / (w * 0.9)) ** 2)
    dust = np.clip(rift * 0.90 + fil * 0.75 + patches * 0.8, 0, 0.96)
    glow = (band * clouds + halo) * (1 - dust) * A
    warm = np.exp(-(u / (420 * s)) ** 2) * np.exp(-(vw / (w * 1.3)) ** 2)
    teal = np.clip(0.5 + 0.9 * nT, 0, 1)[..., None]
    arm = np.array([0.30, 0.80, 1.00], f32) * teal + np.array([0.70, 0.42, 1.00], f32) * (1 - teal)
    core_col = np.array([1.00, 0.60, 0.20], f32)
    pinkz = np.clip(np.exp(-(u / (380 * s)) ** 2) * (np.abs(vw) / w) * 1.4, 0, 1)[..., None]
    core_col = core_col * (1 - pinkz) + np.array([1.0, 0.40, 0.70], f32) * pinkz
    col = arm * (1 - warm[..., None]) + core_col * warm[..., None]
    neb = np.clip(nA * 0.7 + nT * 0.5, 0, 1.5) * np.exp(-(vw / (w * 2.2)) ** 2) * 0.22
    img = glow[..., None] * col + neb[..., None] * arm * 0.5
    ha = np.clip(nB * 0.6 + nA * 0.5 - 0.6, 0, 1) * band * 0.6
    img += ha[..., None] * np.array([1.0, 0.25, 0.55], f32) * glow[..., None]
    img *= (1 + 1.0 * warm)[..., None]
    img = cv2.GaussianBlur(img, (0, 0), 1.0) * 0.95 + cv2.GaussianBlur(img, (0, 0), 14) * 0.45 + cv2.GaussianBlur(img, (0, 0), 60) * 0.22
    img *= 0.020
    r = np.random.default_rng(seed)
    dens = (0.25 + 4.0 * band * clouds * (1 - dust) * (0.5 + A) + 0.6 * halo).astype(np.float64)
    p = dens.ravel() / dens.sum()
    idx = r.choice(WL * HB, n_stars, p=p)
    sx = idx % WL + r.uniform(0, 1, n_stars); sy = idx // WL + r.uniform(0, 1, n_stars)
    flux = 0.0016 * r.uniform(0, 1, n_stars) ** (-1 / 1.1); flux = np.minimum(flux, 0.06)
    temps = np.clip(r.lognormal(np.log(5800), 0.35, n_stars), 3000, 20000)
    lut = np.stack([0.5 + 0.5 * bbcolor(T) for T in np.linspace(3000, 20000, 48)])
    c = lut[np.clip(((temps - 3000) / 17000 * 47).astype(int), 0, 47)]
    acc = np.zeros((HB + 1, WL + 1, 3), f32)
    x0 = np.floor(sx).astype(int); y0 = np.floor(sy).astype(int); fx = (sx - x0)[:, None]; fy = (sy - y0)[:, None]
    val = (flux[:, None] * c).astype(f32)
    for oy, ox, wg in ((0, 0, (1 - fx) * (1 - fy)), (0, 1, fx * (1 - fy)), (1, 0, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(acc, (y0 + oy, (x0 + ox) % WL), val * wg)
    stars = cv2.GaussianBlur(acc[:HB, :WL], (0, 0), 0.55) * 3.0
    out = (img + stars).astype(f32)
    # fade out towards the canvas top/bottom edges (|b| > 60 deg: nothing there anyway)
    out *= np.clip((HB / 2 - np.abs(v)) / 80, 0, 1)[..., None]
    np.savez(cache, mw=out.astype(np.float16))
    return out
