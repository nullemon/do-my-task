"""Bake the stylised Lituya Bay heightfields + twilight-lit textures (numpy only).
Outputs in SCR/terrain/:
  {main,patch}_h.npy      mesh heights (float32)  main: 1536^2 over x[-10,10] y[-4,16] km ; patch: Gilbert Inlet close-up
  {main,patch}_forest.png  emission texture BEFORE the wave (twilight lighting baked in)
  {main,patch}_strip.png   emission texture AFTER: trimline zone stripped to soil/rock, fresh slide scar
Usage: python3 gen_terrain.py [main|patch|preview]"""
import os, sys, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world as Wd
from world import sst, noise, fbm

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay"
OUT = os.path.join(SCR, "terrain"); os.makedirs(OUT, exist_ok=True)
REG = {"main": (-10.0, 10.0, -4.0, 16.0, 1536, 4096),
       "patch": (-4.4, 0.6, 8.4, 13.4, 1024, 4096),
       "far": (-40.0, 40.0, -6.0, 56.0, 1024, 4096)}

# twilight light: sun ~1 deg below the horizon at azimuth ~319 deg (computed for 06:15 UTC 10 Jul 1958 at 58.65N).
# In map frame (+y = azimuth 45 deg) that is ~274 deg from +y, i.e. towards -x.
_az = np.radians(319 - 45)
GLOW = np.array([np.sin(_az), np.cos(_az), 0.0]); GLOW[2] = 0.16; GLOW /= np.linalg.norm(GLOW)
AMB = np.array([0.30, 0.40, 0.66])        # blue sky dome
WARM = np.array([0.95, 0.62, 0.48])       # afterglow


def grid(reg, n):
    x0, x1, y0, y1 = REG[reg][:4]
    xs = np.linspace(x0, x1, n, dtype=np.float32); ys = np.linspace(y0, y1, n, dtype=np.float32)
    return np.meshgrid(xs, ys)  # row = y


def boxblur(a, r):
    if r < 1: return a
    from numpy.lib.stride_tricks import sliding_window_view  # noqa
    c = np.cumsum(np.pad(a, ((r, r), (0, 0)), mode="edge"), 0, dtype=np.float64)
    c = np.vstack([np.zeros((1, c.shape[1])), c]); a = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
    c = np.cumsum(np.pad(a, ((0, 0), (r, r)), mode="edge"), 1, dtype=np.float64)
    c = np.hstack([np.zeros((c.shape[0], 1)), c]); a = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return a.astype(np.float32)


def gblur(a, r):
    rr = max(1, int(r / 1.7))
    for _ in range(3): a = boxblur(a, rr)
    return a


def bake(reg):
    x0, x1, y0, y1, nm, nt = REG[reg]
    # ---------------- mesh heights
    X, Y = grid(reg, nm)
    F = Wd.fields(X, Y)
    np.save(os.path.join(OUT, f"{reg}_h.npy"), F["h"])
    del X, Y, F
    # ---------------- texture-resolution fields
    X, Y = grid(reg, nt)
    F = Wd.fields(X, Y); h = F["h"]; dw = F["dw"]; gm = F["gm"]
    px = (x1 - x0) * 1000.0 / (nt - 1)                               # metres per texel
    gy, gx = np.gradient(h, px)
    nrm = np.stack([-gx, -gy, np.ones_like(h)], -1); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    slope = 1 - nrm[..., 2]                                          # 0 flat .. 1 vertical
    # cheap sky-visibility: how far below the local blurred surface a texel sits
    ao = np.ones_like(h)
    for rm, k in ((60, 0.5), (220, 0.35), (700, 0.25)):
        r = max(1, int(rm / px))
        b = gblur(h, r)
        ao -= k * np.clip((b - h) / (rm * 0.9), 0, 1)
    ao = np.clip(ao, 0.25, 1)
    # ---------------- albedo
    rng_n = fbm(X, Y, 0.35, 4, 60)
    treeline = 700 + 150 * noise(X, Y, 1.0, 61)
    snowline = 1350 + 250 * noise(X, Y, 1.4, 62) + 700 * slope ** 2
    crowns = noise(X, Y, 0.006, 63, beta=1.2) if px < 3 else noise(X, Y, 0.02, 63, beta=1.6)
    forest_c = np.array([0.020, 0.036, 0.024]) * (0.75 + 0.35 * crowns[..., None]) * (0.85 + 0.25 * rng_n[..., None])
    meadow_c = np.array([0.055, 0.060, 0.040]) * (0.8 + 0.3 * rng_n[..., None])
    rock_c = np.array([0.085, 0.080, 0.076]) * (0.75 + 0.35 * fbm(X, Y, 0.08, 4, 64)[..., None])
    snow_c = np.array([0.80, 0.83, 0.88])
    beach_c = np.array([0.13, 0.12, 0.10])
    # glacier: flow-aligned streaks (stretched noise) + crevasse bands
    gl = np.array([0.55, 0.64, 0.72]) * (0.85 + 0.12 * noise(X * 4, Y * 0.6, 0.05, 65)[..., None])
    gl = gl * (1 - 0.35 * sst(0.6, 1.4, noise(X * 6, Y * 1.0, 0.05, 66))[..., None])
    alt = h
    fz = sst(treeline + 60, treeline - 60, alt) * sst(0.72, 0.55, slope)        # forest where low & not cliff
    rz = np.clip(sst(0.55, 0.75, slope) + sst(treeline, treeline + 500, alt) * 0.45, 0, 1)                                                  # cliffs -> rock
    alb = meadow_c * (1 - fz[..., None]) + forest_c * fz[..., None]
    alb = alb * (1 - rz[..., None]) + rock_c * rz[..., None]
    sz = sst(snowline - 80, snowline + 160, alt) * sst(0.85, 0.65, slope)
    alb = alb * (1 - sz[..., None]) + snow_c * sz[..., None]
    shore = sst(0.035, 0.0, dw) * (dw >= 0)
    alb = alb * (1 - shore[..., None]) + beach_c * shore[..., None]
    alb = alb * (1 - gm[..., None]) + gl * gm[..., None]
    alb = np.where((dw < 0)[..., None], np.array([0.01, 0.015, 0.02]), alb)
    # ---------------- AFTER albedo: trimline zone stripped
    R = Wd.runup(X, Y)
    wetlim = Wd.wet_limit(X, Y)
    wet = (h < R) & (dw >= 0) & (dw < wetlim) & (gm < 0.5)
    edge = sst(0.0, 18.0, R - h) * sst(0.0, 0.03, wetlim - dw)                    # soft lower edge of trimline
    ang = np.arctan2(Y - Wd.IMPACT[1], X - Wd.IMPACT[0]); rad = np.hypot(X - Wd.IMPACT[0], Y - Wd.IMPACT[1])
    streak = noise(ang * 30.0, rad * 0.8, 0.05, 70)                               # scour streaks radial from impact
    soil_c = np.array([0.105, 0.090, 0.074]) * (0.8 + 0.25 * streak[..., None]) * (0.85 + 0.3 * fbm(X, Y, 0.05, 3, 71)[..., None])
    bare = np.array([0.12, 0.115, 0.11]) * (0.8 + 0.3 * streak[..., None])
    scour = sst(120, 300, R - h + 40 * noise(X, Y, 0.1, 72))[..., None]          # deeper in the zone: bare rock
    strip_c = soil_c * (1 - scour) + bare * scour
    # fallen-log debris near the trimline (lighter speckle)
    logs = (sst(0.4, 1.4, noise(X, Y, 0.012, 73, beta=1.0)) * sst(60, 0, np.abs(R - h - 25)))[..., None]
    strip_c = strip_c * (1 - 0.4 * logs) + np.array([0.16, 0.14, 0.11]) * 0.4 * logs
    m = (wet * edge)[..., None]
    alb2 = alb * (1 - m) + strip_c * m
    sm = Wd.slide_mask(X, Y, h)[..., None]
    alb2 = alb2 * (1 - sm) + np.array([0.19, 0.175, 0.16]) * (0.8 + 0.3 * fbm(X, Y, 0.03, 3, 74)[..., None]) * sm
    # ---------------- lighting (baked)
    ndg = np.clip(nrm @ GLOW, 0, 1)
    # broad horizon shadowing for the glow: compare height to the terrain towards the glow (-x) direction
    shadow = np.ones_like(h)
    step = max(1, int(150 / px))
    hs = h.copy()
    for k in range(1, 18):
        sh = np.roll(h, k * step, axis=1)  # samples towards -x
        sh[:, :k * step] = h[:, :1]
        rise = (sh - h) / (k * step * px)
        shadow = np.minimum(shadow, np.clip(1 - (rise - 0.16) * 4.0, 0.15, 1))
    light = (AMB[None, None, :] * (ao * (0.55 + 0.45 * nrm[..., 2]))[..., None] +
             WARM[None, None, :] * (0.85 * ndg * shadow)[..., None])
    # water texels are not seen (water plane covers them), keep them dark
    for name, a in (("forest", alb), ("strip", alb2)):
        rad_ = a * light
        img = np.clip(rad_ / 1.25, 0, 1) ** (1 / 2.2)
        Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, f"{reg}_{name}.png"))
    print(reg, "baked", nt, "px", round(px, 2), "m/texel")


def preview():
    X, Y = grid("main", 640)
    F = Wd.fields(X, Y)
    h = F["h"]
    img = np.clip((h + 50) / 2500, 0, 1)
    rgb = np.stack([img, img, img], -1)
    rgb[F["dw"] < 0] = [0.1, 0.2, 0.5]
    R = Wd.runup(X, Y)
    wet = (h < R) & (F["dw"] >= 0) & (F["dw"] < Wd.wet_limit(X, Y))
    rgb[wet] = rgb[wet] * 0.5 + np.array([0.6, 0.3, 0.1]) * 0.5
    rgb[F["gm"] > 0.5] = [0.8, 0.9, 1.0]
    Image.fromarray((rgb[::-1] * 255).astype(np.uint8)).save(os.path.join(OUT, "preview_map.png"))
    print("h range", h.min(), h.max(), "spur", Wd.fields(np.array([Wd.SPUR[0]]), np.array([Wd.SPUR[1]]))["h"])


if __name__ == "__main__":
    for a in sys.argv[1:] or ["preview"]:
        preview() if a == "preview" else bake(a)
