"""WHAT THEY SEE OF US - pre-baked textures (numpy + PIL, run once with system python3).

  earth_rgba.png   Blender Earth still + soft numpy atmosphere halo
  moon_rgba.png    Blender Moon still (copied)
  sky_in.png       the distant sky beyond Earth while we are inside the Milky Way (stars + faint band)
  sky_out.png      intergalactic sky: sparse faint galaxies
  orion.png        Orion Nebula sprite (RGBA, additive)
  mw.png / m31.png / lmc.png   galaxy textures re-used (downsampled) from the series' Andromeda film
"""
import os, math
import numpy as np
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None

W = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us/tex"
AND = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda/textures"
rng = np.random.default_rng(2026)


def fnoise(h, w, octaves=6, base=4, seed=0, persist=0.55):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        gh, gw = max(2, int(base * 2 ** o * h / max(h, w))), max(2, int(base * 2 ** o * w / max(h, w)))
        g = r.random((gh, gw)).astype(np.float32)
        im = Image.fromarray(g, "F").resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(im); tot += amp; amp *= persist
    return out / tot


def save(a, name, mode=None):
    a = np.clip(a, 0, 1)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode).save(os.path.join(W, name))


def earth():
    im = np.asarray(Image.open(os.path.join(W, "earth.png")).convert("RGBA")).astype(np.float32) / 255
    h, w = im.shape[:2]
    a = im[..., 3]
    ys, xs = np.nonzero(a > 0.5)
    cx, cy = xs.mean(), ys.mean(); R = (xs.max() - xs.min()) / 2
    pad = int(R * 0.12)
    H = h + 2 * pad
    out = np.zeros((H, H, 4), np.float32)
    out[pad:pad + h, pad:pad + w] = im
    yy, xx = np.mgrid[0:H, 0:H].astype(np.float32)
    rr = np.hypot(xx - (cx + pad), yy - (cy + pad)) / R
    # slight contrast / saturation lift of the Blue Marble render
    rgb = out[..., :3]
    rgb = np.clip((rgb - 0.01) * 1.25, 0, 1) ** 0.92
    # limb haze inside the disc + glow outside
    inner = np.clip((rr - 0.80) / 0.2, 0, 1) ** 2.2 * (rr <= 1.0)
    haze = np.array([0.38, 0.62, 1.0], np.float32)
    rgb = rgb * (1 - 0.55 * inner[..., None]) + haze * 0.55 * inner[..., None]
    outer = np.exp(-np.clip(rr - 1.0, 0, None) / 0.022) * (rr > 1.0)
    al = np.maximum(out[..., 3], outer * 0.85)
    rgb = np.where((rr > 1.0)[..., None], haze * 1.0, rgb)
    res = np.dstack([rgb, al])
    save(res, "earth_rgba.png", "RGBA")
    m = Image.open(os.path.join(W, "moon.png")).convert("RGBA"); m.save(os.path.join(W, "moon_rgba.png"))


def sky_in():
    Hh, Ww = 1080, 1920
    img = np.zeros((Hh, Ww, 3), np.float32)
    yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
    # faint Milky Way band, tilted, with dust lanes
    ang = math.radians(-24)
    dist = (-(xx - 960) * math.sin(ang) + (yy - 540) * math.cos(ang))
    band = np.exp(-(dist / 260) ** 2)
    n1 = fnoise(Hh, Ww, 7, 5, 1); n2 = fnoise(Hh, Ww, 7, 8, 2)
    glow = band * (0.35 + 0.9 * n1 ** 2)
    dust = np.clip((n2 - 0.48) * 4, 0, 1) * np.exp(-(dist / 120) ** 2)
    glow *= 1 - 0.7 * dust
    img += glow[..., None] * np.array([0.095, 0.090, 0.098])
    img += (np.exp(-(dist / 700) ** 2) * 0.012)[..., None] * np.array([0.55, 0.6, 1.0])
    # stars: denser in the band
    n = 9000
    px = rng.uniform(0, Ww, n * 3); py = rng.uniform(0, Hh, n * 3)
    dd = (-(px - 960) * math.sin(ang) + (py - 540) * math.cos(ang))
    keep = rng.random(n * 3) < (0.25 + 0.75 * np.exp(-(dd / 300) ** 2))
    px, py = px[keep][:n], py[keep][:n]
    mag = rng.pareto(1.6, len(px)) * 0.05 + 0.02
    mag = np.clip(mag, 0, 0.9)
    temp = rng.random(len(px))
    col = np.where(temp[:, None] < 0.25, [0.75, 0.85, 1.0], np.where(temp[:, None] < 0.8, [1, 0.97, 0.93], [1, 0.82, 0.62]))
    for x, y, m, c in zip(px, py, mag, col):
        ix, iy = int(x), int(y)
        sz = 1 if m < 0.25 else 2
        x0, x1, y0, y1 = max(0, ix - sz), min(Ww, ix + sz + 1), max(0, iy - sz), min(Hh, iy + sz + 1)
        gx, gy = np.mgrid[y0:y1, x0:x1]
        g = np.exp(-((gx - y) ** 2 + (gy - x) ** 2) / (0.45 + 0.6 * m))
        img[y0:y1, x0:x1] += g[..., None] * m * np.array(c)
    save(img, "sky_in.png")


def sky_out():
    Hh, Ww = 1080, 1920
    img = np.zeros((Hh, Ww, 3), np.float32)
    n = 420
    for i in range(n):
        x, y = rng.uniform(0, Ww), rng.uniform(0, Hh)
        a = rng.uniform(0.6, 3.2) * (1 if rng.random() > 0.08 else 3)
        e = rng.uniform(0.25, 1.0); th = rng.uniform(0, math.pi)
        b = rng.uniform(0.04, 0.16)
        r = int(a * 5) + 2
        x0, x1, y0, y1 = max(0, int(x) - r), min(Ww, int(x) + r + 1), max(0, int(y) - r), min(Hh, int(y) + r + 1)
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = gx - x, gy - y
        u = dx * math.cos(th) + dy * math.sin(th); v = -dx * math.sin(th) + dy * math.cos(th)
        g = np.exp(-np.sqrt((u / a) ** 2 + (v / (a * e)) ** 2) * 2.2)
        c = np.array([1.0, 0.9, 0.78]) if rng.random() < 0.6 else np.array([0.8, 0.85, 1.0])
        img[y0:y1, x0:x1] += g[..., None] * b * c
    # a few faint foreground stars of our own galaxy
    for i in range(500):
        x, y = int(rng.uniform(0, Ww)), int(rng.uniform(0, Hh))
        img[y, x] += rng.uniform(0.03, 0.12)
    save(img, "sky_out.png")


def orion():
    S = 900
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S - 0.5
    n1 = fnoise(S, S, 7, 3, 11); n2 = fnoise(S, S, 7, 5, 12); n3 = fnoise(S, S, 6, 9, 13)
    warp_x = xx + 0.12 * (n2 - 0.5); warp_y = yy + 0.12 * (n3 - 0.5)
    r = np.sqrt((warp_x / 0.95) ** 2 + (warp_y / 0.8) ** 2)
    env = np.exp(-(r / 0.2) ** 2)
    core = np.exp(-(np.hypot(xx + 0.02, yy - 0.03) / 0.05) ** 2)
    neb = env * (0.25 + 1.1 * np.clip(n1 - 0.25, 0, 1) ** 1.6)
    dark = np.clip((n3 - 0.55) * 5, 0, 1) * np.exp(-(np.hypot(xx - 0.06, yy + 0.08) / 0.18) ** 2)
    neb *= 1 - 0.75 * dark
    pink = np.array([1.0, 0.36, 0.52]); teal = np.array([0.35, 0.75, 0.85]); white = np.array([1, 0.95, 0.9])
    mixc = np.clip(r / 0.25, 0, 1)[..., None]
    rgb = neb[..., None] * (teal * (1 - mixc) + pink * mixc) * 2.4 + core[..., None] * white * 0.55
    save(rgb, "orion.png")


def galaxies():
    for src, dst, size in (("ch2_mw.png", "mw.png", 2048), ("ch2_m31.png", "m31.png", 1024), ("ch2_lmc.png", "lmc.png", 512)):
        Image.open(os.path.join(AND, src)).convert("RGB").resize((size, size), Image.LANCZOS).save(os.path.join(W, dst))


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["earth", "sky_in", "sky_out", "orion", "galaxies"]
    for w in which:
        globals()[w](); print("done", w)
