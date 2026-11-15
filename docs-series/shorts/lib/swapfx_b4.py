"""Swap-format effects shared by the BATCH4 Shorts (new module; copied from exoplanet-skies / eclipses-other-worlds,
nothing in lib/ is edited): beams around an object, swap flash + chromatic shockwave, chromatic bloom, lateral CA,
top-of-frame readouts (NAME / line 2 / line 3), back-out easing, palette helpers.
"""
import math
import numpy as np, cv2
from .core import f32, ease, ramp
from .post import bloom
from .text import word_layer, composite, hud_text


def back_out(u, s=2.2):
    u = min(max(u, 0.0), 1.0) - 1; return 1 + u * u * ((s + 1) * u + s)


def lerp(a, b, w):
    if isinstance(a, (tuple, list)): return tuple(x + (y - x) * w for x, y in zip(a, b))
    return a + (b - a) * w


def pal_list(cols, x):
    Cc = np.array(list(cols) + [cols[0]], f32); n = len(cols)
    p = (x % 1.0) * n; i = np.floor(p).astype(np.int32); fr = (p - i)[..., None]
    return Cc[i] * (1 - fr) + Cc[i + 1] * fr


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


class Beams:
    """slowly turning coloured light beams radiating from a point, on a half-res grid (W/2 x H/2)"""
    def __init__(self, W, H, n=7, seed=5):
        hw, hh = W // 2, H // 2
        self.yy, self.xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        r = np.random.default_rng(seed)
        self.b = [dict(a=i * 2 * np.pi / n + r.uniform(-0.25, 0.25), w=r.uniform(0.15, 0.26), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                       ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(n)]

    def layer(self, t, c, cols, I, col_u=0.0, reach=1300.0):
        dx = self.xx - c[0]; dy = self.yy - c[1]
        d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi0 = np.arctan2(dy, dx)
        twist = 2.4 * ease(col_u) ** 1.3; spin = 0.06 * t + 1.4 * col_u ** 2
        phi = phi0 + twist * np.log(d / 30.0)
        reach = reach * (1 - 0.7 * ease(col_u))
        rad = (1 - np.exp(-(d + 6) / 40)) * (np.exp(-d / reach) * 0.9 + 0.12 * np.exp(-d / (reach * 2.2)))
        acc = np.zeros(d.shape + (3,), f32)
        for b in self.b:
            a = b["a"] + spin * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            wd = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / wd) ** 2 * 1.6)
            Ib = b["I"] * (0.72 + 0.28 * math.sin(t * 1.3 * b["sp"] + b["ph"] * 2))
            x = (b["hue"] + dp / wd * 0.3) % 1.0
            colr = palette(x) if cols == "rainbow" else pal_list(cols, x)
            acc += colr * (g * Ib)[..., None]
        return acc * rad[..., None] * 0.30 * I


class FX:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.yy, self.xx = np.mgrid[0:H, 0:W].astype(f32)

    def flash(self, img, u, col, k=2.6):
        if -0.05 < u < 1.4: img += (k * math.exp(-max(u, 0) / 0.08) * ease((u + 0.05) / 0.05)) * np.asarray(col, f32)

    def shock(self, img, cx, cy, u, col, k=2.0):
        if not (-0.05 < u < 1.4): return
        R = 2400 * (max(u, 0) / 1.4) ** 0.6; wdt = 18 + 60 * u
        dd = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        for ch, off in ((0, 10), (1, 0), (2, -10)):
            img[..., ch] += np.exp(-((dd - R - off) / wdt) ** 2) * k * math.exp(-max(u, 0) / 0.55) * (0.6 + 0.4 * col[ch])

    def chroma_bloom(self, img, amt=1.0):
        img = bloom(img, 0.85 * amt)
        H, W = img.shape[:2]
        sm = np.maximum(cv2.resize(img, (W // 8, H // 8), interpolation=cv2.INTER_AREA) - 1.0, 0)
        acc = np.empty_like(sm)
        for c, s in ((0, 26), (1, 20), (2, 15)): acc[..., c] = cv2.GaussianBlur(sm[..., c], (0, 0), s)
        return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * 0.35 * amt

    def chroma(self, out):
        W, H = self.W, self.H; o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o


def readout(out, L, a, name, l2, l3, tc, y0=262):
    """bold readout block at the TOP of the frame (BATCH4): NAME / line 2 / line 3"""
    if a <= 0.01: return
    W = L.W; x = W / 2; dy = (1 - a) * -16
    rgba, _ = word_layer(name, int(L.hud_size * 1.25), W * 0.9, fill=tc)
    composite(out, rgba, x, y0 + dy, a)
    hud_text(out, l2, x, y0 + 80 + dy, int(L.hud_size * 0.60), "Black", (255, 255, 255), a, 0.08, display=True)
    if l3: hud_text(out, l3, x, y0 + 136 + dy, int(L.hud_size * 0.44), "Bold", (235, 240, 250), a, 0.10, display=True)
