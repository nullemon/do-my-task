"""WHAT THEY SEE OF US - 'Earth at that time' vignettes: small, quiet silhouette illustrations.
Pure PIL vector drawing (drawn at 2x and downsampled), duotone sky gradients + dark silhouettes and a
single glowing accent. No people, no likenesses. Run: python3 vignettes.py  ->  tex/vig_<id>.png
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us/tex"
VW, VH = 520, 300
SS = 2
W, H = VW * SS, VH * SS
SIL = (8, 10, 18)


def grad(top, bot, mid=None, midpos=0.6):
    t = np.linspace(0, 1, H)[:, None]
    top, bot = np.array(top, float), np.array(bot, float)
    if mid is None:
        g = top + (bot - top) * t
    else:
        mid = np.array(mid, float)
        g = np.where(t < midpos, top + (mid - top) * (t / midpos), mid + (bot - mid) * ((t - midpos) / (1 - midpos)))
    g = np.repeat(g[:, None, :], W, axis=1).reshape(H, W, 3)
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).convert("RGBA")


def P(pts):
    return [(x * W, y * H) for x, y in pts]


def glow(img, xy, r, col, strength=1.0):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x, y = xy[0] * W, xy[1] * H
    for k in range(12, 0, -1):
        rr = r * SS * k / 4
        a = int(255 * strength * (0.5 / k) ** 1.2)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col + (a,))
    lay = lay.filter(ImageFilter.GaussianBlur(r * SS))
    img.alpha_composite(lay)
    d2 = ImageDraw.Draw(img)
    d2.ellipse([x - r * SS * 0.6, y - r * SS * 0.6, x + r * SS * 0.6, y + r * SS * 0.6], fill=(255, 250, 240, 255))


def stars(img, n, seed=1, ymax=0.7, bright=180):
    r = np.random.default_rng(seed); d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(0, H * ymax)
        s = r.uniform(0.6, 1.8) * SS / 2
        a = int(r.uniform(0.3, 1) * bright)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 255, 255, a))


def mammoth(d, x, y, s, col=SIL, flip=False):
    """Woolly mammoth silhouette; (x,y) = feet baseline centre, s = height in unit H."""
    body = [(-0.55, 0.0), (-0.52, -0.38), (-0.6, -0.55), (-0.5, -0.78), (-0.2, -0.92), (0.1, -1.0),
            (0.32, -0.98), (0.5, -0.9), (0.62, -0.75), (0.66, -0.55), (0.7, -0.35), (0.72, -0.1),
            (0.64, 0.05), (0.6, -0.25), (0.55, -0.4), (0.48, -0.35), (0.44, 0.0), (0.3, 0.0), (0.3, -0.3),
            (-0.05, -0.32), (-0.08, 0.0), (-0.22, 0.0), (-0.25, -0.3), (-0.38, -0.3), (-0.4, 0.0)]
    f = -1 if flip else 1
    pts = [(x * W + f * bx * s * H, y * H + by * s * H) for bx, by in body]
    d.polygon(pts, fill=col)
    # tusk
    tx, ty = x * W + f * 0.62 * s * H, y * H - 0.42 * s * H
    bb = [tx - 0.08 * s * H if not flip else tx - 0.42 * s * H, ty - 0.05 * s * H,
          tx + 0.42 * s * H if not flip else tx + 0.08 * s * H, ty + 0.4 * s * H]
    d.arc(bb, 200 if not flip else -40, 340 if not flip else 100 + 60, fill=(220, 214, 196, 255), width=max(2, int(0.035 * s * H)))
    # woolly fringe
    for i in range(18):
        bx = -0.5 + i * 0.065
        d.line([(x * W + f * bx * s * H, y * H - 0.35 * s * H), (x * W + f * (bx + 0.01) * s * H, y * H - 0.22 * s * H)], fill=col, width=int(0.03 * s * H))


def frame(img):
    img = img.resize((VW, VH), Image.LANCZOS)
    # soft vignette + thin border
    a = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:VH, 0:VW]
    v = 1 - 0.35 * (((xx - VW / 2) / (VW / 2)) ** 2 + ((yy - VH / 2) / (VH / 2)) ** 2) / 2
    a[..., :3] *= v[..., None]
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, VW - 1, VH - 1], outline=(230, 225, 210, 150), width=1)
    return img


def v_jwst():
    img = grad((4, 6, 14), (14, 12, 30)); stars(img, 120, 3, 1.0)
    d = ImageDraw.Draw(img)
    # sunshield (layered kite)
    for k, c in enumerate([(70, 60, 95), (95, 85, 120), (125, 112, 150)]):
        o = 0.012 * k
        d.polygon(P([(0.2 + o, 0.86 - o), (0.5, 0.74 - o), (0.8 - o, 0.86 - o), (0.5, 0.97 - o)]), fill=c + (255,))
    # hexagonal primary: 18 segments
    cx, cy, r = 0.5 * W, 0.42 * H, 0.062 * H
    hexes = []
    for q in range(-2, 3):
        for rr_ in range(-2, 3):
            s_ = -q - rr_
            if max(abs(q), abs(rr_), abs(s_)) <= 2 and not (q == 0 and rr_ == 0):
                if max(abs(q), abs(rr_), abs(s_)) == 2 and (abs(q) == 2 and abs(rr_) == 0 or False):
                    pass
                hexes.append((q, rr_))
    hexes = [h for h in hexes if not (abs(h[0]) == 2 and h[1] == 0) and not (abs(h[0]) == 0 and abs(h[1]) == 2)][:18]
    for q, rr_ in hexes:
        x = cx + r * 1.75 * (q + rr_ / 2); y = cy + r * 1.52 * rr_
        pts = [(x + r * math.cos(math.radians(60 * i + 30)), y + r * math.sin(math.radians(60 * i + 30))) for i in range(6)]
        d.polygon(pts, fill=(214, 170, 72, 255), outline=(120, 86, 30, 255))
        d.polygon([(px * 0.5 + x * 0.5, py * 0.5 + y * 0.5) for px, py in pts[:3]] + [(x, y)], fill=(240, 205, 120, 255))
    # secondary mirror struts
    d.line([(cx - 0.17 * W, cy + 0.2 * H), (cx, cy - 0.28 * H)], fill=(40, 40, 50, 255), width=5)
    d.line([(cx + 0.17 * W, cy + 0.2 * H), (cx, cy - 0.28 * H)], fill=(40, 40, 50, 255), width=5)
    d.ellipse([cx - 10, cy - 0.28 * H - 10, cx + 10, cy - 0.28 * H + 10], fill=(200, 170, 90, 255))
    return frame(img)


def v_iss():
    img = grad((2, 3, 10), (6, 10, 30)); stars(img, 90, 4, 0.6)
    d = ImageDraw.Draw(img)
    # Earth limb
    d.ellipse([-0.4 * W, 0.62 * H, 1.4 * W, 2.2 * H], fill=(20, 60, 130, 255))
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    dl.ellipse([-0.42 * W, 0.6 * H, 1.42 * W, 2.22 * H], outline=(120, 190, 255, 200), width=14)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10))); d = ImageDraw.Draw(img)
    cx, cy = 0.5 * W, 0.36 * H
    d.line([(cx - 0.25 * W, cy), (cx + 0.25 * W, cy)], fill=(190, 190, 200, 255), width=6)        # truss
    for sx in (-1, 1):
        for k in (0.16, 0.23):
            x = cx + sx * k * W
            d.rectangle([x - 0.025 * W, cy - 0.16 * H, x + 0.025 * W, cy - 0.015 * H], fill=(170, 120, 40, 255), outline=(90, 60, 20, 255))
            d.rectangle([x - 0.025 * W, cy + 0.015 * H, x + 0.025 * W, cy + 0.16 * H], fill=(170, 120, 40, 255), outline=(90, 60, 20, 255))
    d.rounded_rectangle([cx - 0.09 * W, cy - 0.025 * H, cx + 0.09 * W, cy + 0.025 * H], 10, fill=(215, 215, 222, 255))
    d.rounded_rectangle([cx - 0.02 * W, cy - 0.08 * H, cx + 0.02 * W, cy + 0.08 * H], 8, fill=(200, 200, 210, 255))
    return frame(img)


def v_voyager():
    img = grad((1, 2, 6), (4, 4, 12)); stars(img, 60, 5, 1.0, 120)
    d = ImageDraw.Draw(img)
    # faint scattered sunbeams, a pale blue dot sitting in one (as in the 1990 photo)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for x0, a in ((0.66, 60), (0.74, 35), (0.79, 50)):
        dl.polygon(P([(x0, 0), (x0 + 0.035, 0), (x0 + 0.075, 1), (x0 + 0.03, 1)]), fill=(210, 160, 120, a))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6))); d = ImageDraw.Draw(img)
    d.ellipse([0.705 * W - 3, 0.62 * H - 3, 0.705 * W + 3, 0.62 * H + 3], fill=(170, 205, 255, 255))
    # Voyager seen from behind, turned toward the dot
    cx, cy = 0.3 * W, 0.45 * H
    d.line([(cx, cy), (cx - 0.24 * W, cy + 0.34 * H)], fill=(150, 150, 150, 255), width=3)        # magnetometer boom
    d.line([(cx, cy + 0.05 * H), (cx + 0.12 * W, cy + 0.3 * H)], fill=(120, 120, 120, 255), width=5)  # RTG boom
    for k in range(3):
        d.ellipse([cx + 0.1 * W + k * 9, cy + 0.26 * H + k * 14, cx + 0.12 * W + k * 9 + 12, cy + 0.29 * H + k * 14], fill=(90, 90, 95, 255))
    d.polygon(P([(0.27, 0.48), (0.33, 0.48), (0.34, 0.56), (0.26, 0.56)]), fill=(60, 55, 50, 255))   # bus
    d.ellipse([cx - 0.1 * W, cy - 0.2 * H, cx + 0.1 * W, cy + 0.12 * H], fill=(225, 225, 220, 255), outline=(120, 120, 120, 255), width=3)
    d.ellipse([cx - 0.07 * W, cy - 0.15 * H, cx + 0.07 * W, cy + 0.07 * H], outline=(180, 180, 175, 255), width=2)
    d.line([(cx, cy - 0.04 * H), (cx + 0.03 * W, cy - 0.12 * H)], fill=(120, 120, 120, 255), width=3)
    return frame(img)


def v_apollo():
    img = grad((0, 0, 0), (4, 4, 6))
    d = ImageDraw.Draw(img)
    # Earth in the black sky (half lit)
    ex, ey, er = 0.74 * W, 0.24 * H, 0.08 * H
    d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=(30, 80, 165, 255))
    d.ellipse([ex + er * 0.05, ey - er * 0.55, ex + er * 0.75, ey - er * 0.05], fill=(225, 230, 240, 255))
    d.ellipse([ex + er * 0.2, ey + er * 0.2, ex + er * 0.7, ey + er * 0.55], fill=(150, 130, 90, 255))
    d.pieslice([ex - er - 1, ey - er - 1, ex + er + 1, ey + er + 1], 90, 270, fill=(6, 7, 12, 255))
    # lunar surface
    r = np.random.default_rng(9)
    surf = [(0, 0.72)] + [(x, 0.72 + 0.02 * math.sin(x * 9) + 0.01 * r.random()) for x in np.linspace(0, 1, 40)] + [(1, 1), (0, 1)]
    d.polygon(P(surf), fill=(120, 118, 112, 255))
    for _ in range(14):
        x, y, s = r.uniform(0, 1), r.uniform(0.77, 0.97), r.uniform(0.01, 0.04)
        d.ellipse(P([(x - s, y - s * 0.3), (x + s, y + s * 0.3)]), fill=(95, 93, 88, 255))
    # lunar module
    cx, by = 0.38, 0.8
    d.polygon(P([(cx - 0.09, by - 0.14), (cx + 0.09, by - 0.14), (cx + 0.1, by - 0.08), (cx - 0.1, by - 0.08)]), fill=(185, 150, 60, 255))
    for sx in (-1, 1):
        d.line(P([(cx + sx * 0.08, by - 0.09), (cx + sx * 0.15, by + 0.01)]), fill=(160, 160, 160, 255), width=5)
        d.line(P([(cx + sx * 0.15 - 0.02, by + 0.012), (cx + sx * 0.15 + 0.02, by + 0.012)]), fill=(160, 160, 160, 255), width=6)
    d.polygon(P([(cx - 0.07, by - 0.14), (cx - 0.06, by - 0.27), (cx + 0.02, by - 0.31), (cx + 0.07, by - 0.25), (cx + 0.07, by - 0.14)]), fill=(200, 200, 196, 255))
    d.polygon(P([(cx - 0.03, by - 0.24), (cx + 0.01, by - 0.26), (cx + 0.01, by - 0.2), (cx - 0.03, by - 0.19)]), fill=(30, 30, 35, 255))
    # boot prints
    for i in range(9):
        x = 0.52 + i * 0.045; y = 0.86 + 0.01 * (i % 2)
        d.ellipse(P([(x, y), (x + 0.018, y + 0.012)]), fill=(80, 78, 74, 255))
    return frame(img)


def v_radio():
    img = grad((5, 8, 22), (22, 26, 52)); stars(img, 70, 6, 0.6)
    d = ImageDraw.Draw(img)
    cx, top, by = 0.5, 0.22, 0.86
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    for k in range(1, 7):
        rr = k * 0.075
        dl.arc([cx * W - rr * W, top * H - rr * W, cx * W + rr * W, top * H + rr * W], 200, 340, fill=(170, 200, 255, int(200 / k ** 0.6)), width=4)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5))); d = ImageDraw.Draw(img)
    # lattice mast
    d.line(P([(cx - 0.06, by), (cx, top)]), fill=SIL + (255,), width=5)
    d.line(P([(cx + 0.06, by), (cx, top)]), fill=SIL + (255,), width=5)
    for i in range(12):
        f0, f1 = i / 12, (i + 1) / 12
        y0, y1 = by - (by - top) * f0, by - (by - top) * f1
        w0, w1 = 0.06 * (1 - f0), 0.06 * (1 - f1)
        d.line(P([(cx - w0, y0), (cx + w1, y1)]), fill=SIL + (255,), width=2)
        d.line(P([(cx + w0, y0), (cx - w1, y1)]), fill=SIL + (255,), width=2)
    d.polygon(P([(0, 0.84), (0.3, 0.82), (0.6, 0.85), (1, 0.83), (1, 1), (0, 1)]), fill=SIL + (255,))
    glow(img, (cx, top), 4, (255, 90, 80), 0.9)
    return frame(img)


def v_flyer():
    img = grad((120, 150, 190), (235, 205, 170), (190, 190, 205), 0.55)
    d = ImageDraw.Draw(img)
    d.polygon(P([(0, 0.8), (0.2, 0.76), (0.45, 0.79), (0.7, 0.74), (1, 0.78), (1, 1), (0, 1)]), fill=(196, 168, 128, 255))
    d.polygon(P([(0, 0.88), (0.35, 0.85), (0.7, 0.9), (1, 0.87), (1, 1), (0, 1)]), fill=(170, 140, 102, 255))
    # biplane (Wright Flyer-like): two long wings, front elevator, rear rudder, struts
    c = (30, 30, 36, 255)
    x0, y0 = 0.3, 0.42
    for dy in (0, 0.14):
        d.polygon(P([(x0, y0 + dy), (x0 + 0.42, y0 + dy - 0.03), (x0 + 0.42, y0 + dy - 0.015), (x0, y0 + dy + 0.015)]), fill=c)
    for k in range(7):
        x = x0 + 0.02 + k * 0.065
        d.line(P([(x, y0 + 0.005 - k * 0.004), (x, y0 + 0.14 - k * 0.004)]), fill=c, width=2)
    d.line(P([(x0 - 0.02, y0 + 0.065), (x0 - 0.13, y0 + 0.08)]), fill=c, width=2)
    d.polygon(P([(x0 - 0.2, y0 + 0.05), (x0 - 0.1, y0 + 0.045), (x0 - 0.1, y0 + 0.06), (x0 - 0.2, y0 + 0.065)]), fill=c)
    d.polygon(P([(x0 - 0.2, y0 + 0.1), (x0 - 0.1, y0 + 0.095), (x0 - 0.1, y0 + 0.11), (x0 - 0.2, y0 + 0.115)]), fill=c)
    d.line(P([(x0 + 0.42, y0 + 0.04), (x0 + 0.53, y0 + 0.03)]), fill=c, width=2)
    d.polygon(P([(x0 + 0.52, y0 - 0.01), (x0 + 0.545, y0 - 0.01), (x0 + 0.545, y0 + 0.09), (x0 + 0.52, y0 + 0.09)]), fill=c)
    # its little shadow on the sand
    d.ellipse(P([(0.35, 0.83), (0.62, 0.845)]), fill=(150, 122, 90, 255))
    return frame(img)


def v_ship():
    img = grad((6, 10, 28), (60, 50, 70), (24, 30, 60), 0.6); stars(img, 110, 7, 0.55)
    d = ImageDraw.Draw(img)
    d.rectangle(P([(0, 0.72), (1, 1)]), fill=(10, 16, 30, 255))
    for i in range(30):
        y = 0.74 + i * 0.009
        d.line(P([(0.05 + (i * 0.137) % 0.6, y), (0.15 + (i * 0.137) % 0.6, y)]), fill=(60, 70, 100, 120), width=1)
    glow(img, (0.78, 0.14), 5, (255, 240, 200), 1.0)
    # galleon: hull + three masts with square sails
    c = SIL + (255,)
    d.polygon(P([(0.18, 0.66), (0.62, 0.66), (0.66, 0.6), (0.6, 0.73), (0.25, 0.74), (0.14, 0.6)]), fill=c)
    d.polygon(P([(0.14, 0.6), (0.24, 0.56), (0.26, 0.66), (0.16, 0.66)]), fill=c)
    for mx, h in ((0.28, 0.38), (0.4, 0.46), (0.52, 0.34)):
        d.line(P([(mx, 0.66), (mx, 0.66 - h)]), fill=c, width=4)
        for k, (sw, sy, sh) in enumerate(((0.07, 0.66 - h * 0.85, h * 0.22), (0.085, 0.66 - h * 0.58, h * 0.28))):
            d.polygon(P([(mx - sw, sy), (mx + sw, sy), (mx + sw * 1.1, sy + sh), (mx - sw * 1.1, sy + sh)]), fill=(28, 30, 44, 255))
    d.line(P([(0.62, 0.62), (0.75, 0.52)]), fill=c, width=3)
    d.polygon(P([(0.6, 0.6), (0.73, 0.53), (0.66, 0.62)]), fill=(28, 30, 44, 255))
    return frame(img)


def v_cathedral():
    img = grad((40, 30, 70), (215, 120, 80), (140, 70, 90), 0.6)
    d = ImageDraw.Draw(img)
    c = SIL + (255,)
    d.rectangle(P([(0, 0.9), (1, 1)]), fill=c)
    base, cx = 0.9, 0.5
    for sx in (-1, 1):   # twin towers with spires and pinnacles
        tx = cx + sx * 0.13
        d.rectangle(P([(tx - 0.055, 0.34), (tx + 0.055, base)]), fill=c)
        d.polygon(P([(tx - 0.05, 0.345), (tx, 0.05), (tx + 0.05, 0.345)]), fill=c)
        for px in (tx - 0.055, tx + 0.055):
            d.polygon(P([(px - 0.012, 0.36), (px, 0.25), (px + 0.012, 0.36)]), fill=c)
        for k in range(3):
            wy = 0.42 + k * 0.13
            d.polygon(P([(tx - 0.015, wy + 0.08), (tx - 0.015, wy + 0.025), (tx, wy), (tx + 0.015, wy + 0.025), (tx + 0.015, wy + 0.08)]), fill=(90, 55, 55, 255))
    d.rectangle(P([(cx - 0.075, 0.45), (cx + 0.075, base)]), fill=c)
    d.polygon(P([(cx - 0.075, 0.455), (cx, 0.36), (cx + 0.075, 0.455)]), fill=c)
    for sx in (-1, 1):   # side aisles with sloping roofs
        x0, x1 = (cx + 0.185, cx + 0.42) if sx > 0 else (cx - 0.42, cx - 0.185)
        d.rectangle(P([(x0, 0.66), (x1, base)]), fill=c)
        d.polygon(P([(x0, 0.665), (x1, 0.665), ((x0 + x1) / 2, 0.6)]), fill=c)
        for k in range(4):
            wx = x0 + 0.03 + k * 0.055
            d.polygon(P([(wx, 0.84), (wx, 0.74), (wx + 0.012, 0.72), (wx + 0.024, 0.74), (wx + 0.024, 0.84)]), fill=(90, 55, 55, 255))
    # glowing rose window + portal
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    rx, ry, rr = cx * W, 0.55 * H, 0.05 * H
    dl.ellipse([rx - rr, ry - rr, rx + rr, ry + rr], fill=(255, 190, 110, 255))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6))); img.alpha_composite(lay)
    d = ImageDraw.Draw(img)
    for i in range(8):
        a = i * math.pi / 4
        d.line([(rx, ry), (rx + rr * math.cos(a), ry + rr * math.sin(a))], fill=c, width=3)
    d.ellipse([rx - rr * 0.3, ry - rr * 0.3, rx + rr * 0.3, ry + rr * 0.3], fill=c)
    d.polygon(P([(cx - 0.03, base), (cx - 0.03, 0.76), (cx, 0.71), (cx + 0.03, 0.76), (cx + 0.03, base)]), fill=(120, 70, 50, 255))
    return frame(img)


def v_maya():
    img = grad((40, 60, 70), (230, 170, 110), (150, 140, 110), 0.55)
    d = ImageDraw.Draw(img)
    glow(img, (0.78, 0.52), 6, (255, 200, 140), 0.8)
    d = ImageDraw.Draw(img)
    c = SIL + (255,)
    # stepped temple (Tikal Temple I-like): nine steep tiers + roof comb
    base, cx = 0.84, 0.42
    for i in range(9):
        w = 0.15 - i * 0.012
        y0 = base - i * 0.055
        d.rectangle(P([(cx - w, y0 - 0.052), (cx + w, y0)]), fill=c)
    d.rectangle(P([(cx - 0.022, 0.84 - 0.5), (cx + 0.022, base)]), fill=(18, 20, 26, 255))     # stairway
    d.rectangle(P([(cx - 0.05, 0.2), (cx + 0.05, 0.345)]), fill=c)
    d.rectangle(P([(cx - 0.035, 0.1), (cx + 0.035, 0.2)]), fill=c)
    # jungle canopy
    r = np.random.default_rng(12)
    for _ in range(70):
        x = r.uniform(-0.05, 1.05); y = r.uniform(0.74, 0.92); s = r.uniform(0.03, 0.07)
        if abs(x - cx) < 0.12 and y < 0.8: continue
        d.ellipse(P([(x - s, y - s * 0.8), (x + s, y + s * 0.8)]), fill=(12, 18, 16, 255))
    d.rectangle(P([(0, 0.88), (1, 1)]), fill=(12, 18, 16, 255))
    # a second, smaller temple far right
    for i in range(6):
        w = 0.06 - i * 0.008; y0 = 0.82 - i * 0.03
        d.rectangle(P([(0.82 - w, y0 - 0.03), (0.82 + w, y0)]), fill=(30, 34, 40, 255))
    return frame(img)


def v_rome():
    img = grad((60, 40, 70), (240, 160, 90), (190, 110, 90), 0.58)
    glow(img, (0.2, 0.62), 9, (255, 210, 150), 0.9)
    d = ImageDraw.Draw(img)
    c = SIL + (255,)
    d.rectangle(P([(0, 0.88), (1, 1)]), fill=c)
    # two-tier aqueduct
    top1, top2, base = 0.42, 0.62, 0.88
    d.rectangle(P([(0.0, top1), (1.0, top1 + 0.04)]), fill=c)
    d.rectangle(P([(0.0, top2), (1.0, top2 + 0.035)]), fill=c)
    n = 6
    for i in range(n + 1):
        x = i / n
        d.rectangle(P([(x - 0.025, top2), (x + 0.025, base)]), fill=c)
    for i in range(n):
        x0, x1 = i / n + 0.025, (i + 1) / n - 0.025
        d.pieslice(P([(x0, top2 + 0.035 - 0.0), (x1, top2 + 0.035 + (x1 - x0) * W / H)]), 180, 360, fill=c)
    m = 12
    for i in range(m + 1):
        x = i / m
        d.rectangle(P([(x - 0.012, top1), (x + 0.012, top2)]), fill=c)
    # re-cut arches (sky through them) for the lower tier
    for i in range(n):
        x0, x1 = i / n + 0.025, (i + 1) / n - 0.025
        arch_top = top2 + 0.035 + 0.02
        d.rectangle(P([(x0, arch_top + (x1 - x0) * W / H / 2), (x1, base)]), fill=(0, 0, 0, 0))
    # cypresses
    for x, h in ((0.86, 0.3), (0.92, 0.36), (0.1, 0.25)):
        d.ellipse(P([(x - 0.018, base - h), (x + 0.018, base + 0.02)]), fill=c)
    return frame(Image.alpha_composite(grad((60, 40, 70), (240, 160, 90), (190, 110, 90), 0.58), img))


def v_pyramid():
    img = grad((50, 40, 80), (230, 150, 90), (170, 110, 100), 0.6)
    d = ImageDraw.Draw(img)
    glow(img, (0.3, 0.6), 6, (255, 210, 150), 0.8)
    d = ImageDraw.Draw(img)
    # Giza (left 60%)
    d.polygon(P([(0, 0.82), (0.6, 0.8), (0.6, 1), (0, 1)]), fill=(70, 46, 40, 255))
    for cx, w, h, col in ((0.12, 0.1, 0.2, (70, 48, 44)), (0.42, 0.16, 0.34, (40, 28, 30)), (0.26, 0.13, 0.28, (52, 36, 36))):
        d.polygon(P([(cx - w, 0.82), (cx, 0.82 - h), (cx + w, 0.82)]), fill=col + (255,))
        d.polygon(P([(cx, 0.82 - h), (cx + w, 0.82), (cx + w * 0.25, 0.82)]), fill=tuple(int(v * 0.7) for v in col) + (255,))
    # Arctic (right 40%): pale twilight tundra + mammoths
    arc = grad((70, 90, 130), (190, 200, 215))
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).rectangle(P([(0.62, 0), (1, 1)]), fill=255)
    img.paste(arc, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.polygon(P([(0.62, 0.8), (0.8, 0.78), (1, 0.8), (1, 1), (0.62, 1)]), fill=(215, 222, 230, 255))
    mammoth(d, 0.78, 0.84, 0.2, (20, 22, 30, 255))
    mammoth(d, 0.92, 0.83, 0.13, (35, 38, 48, 255), flip=True)
    d.line(P([(0.61, 0), (0.61, 1)]), fill=(230, 225, 210, 200), width=2)
    return frame(img)


def v_ice():
    img = grad((120, 150, 185), (225, 232, 240), (180, 200, 220), 0.5)
    d = ImageDraw.Draw(img)
    # glacier wall
    r = np.random.default_rng(21)
    pts = [(0, 0.55)] + [(x, 0.36 + 0.06 * r.random() + 0.08 * math.sin(x * 5)) for x in np.linspace(0, 1, 26)] + [(1, 0.7), (0, 0.7)]
    d.polygon(P(pts), fill=(205, 222, 240, 255))
    for x in np.linspace(0.03, 0.97, 22):
        d.line(P([(x, 0.42 + 0.05 * r.random()), (x + 0.01, 0.68)]), fill=(160, 185, 215, 255), width=3)
    d.polygon(P([(0, 0.68), (1, 0.66), (1, 1), (0, 1)]), fill=(236, 240, 246, 255))
    for x, s, f in ((0.24, 0.24, False), (0.5, 0.19, False), (0.72, 0.15, True), (0.85, 0.11, False)):
        mammoth(d, x, 0.84 + s * 0.3 - 0.07, s, (26, 28, 38, 255), flip=f)
    return frame(img)


def acacia(d, x, y, s, c):
    d.line(P([(x, y), (x - 0.01, y - 0.18 * s)]), fill=c, width=int(9 * s))
    d.line(P([(x - 0.01, y - 0.18 * s), (x - 0.08 * s, y - 0.3 * s)]), fill=c, width=int(6 * s))
    d.line(P([(x - 0.01, y - 0.18 * s), (x + 0.07 * s, y - 0.31 * s)]), fill=c, width=int(6 * s))
    d.ellipse(P([(x - 0.2 * s, y - 0.4 * s), (x + 0.2 * s, y - 0.3 * s)]), fill=c)


def v_savanna():
    img = grad((80, 60, 90), (245, 160, 70), (220, 110, 70), 0.62)
    glow(img, (0.62, 0.68), 14, (255, 220, 150), 1.0)
    d = ImageDraw.Draw(img)
    c = SIL + (255,)
    d.polygon(P([(0, 0.78), (0.4, 0.76), (1, 0.79), (1, 1), (0, 1)]), fill=c)
    acacia(d, 0.25, 0.8, 1.0, c); acacia(d, 0.82, 0.78, 0.7, c)
    r = np.random.default_rng(3)
    for _ in range(140):
        x = r.uniform(0, 1); d.line(P([(x, 0.8), (x + r.uniform(-0.01, 0.01), 0.76 - r.uniform(0, 0.03))]), fill=c, width=2)
    return frame(img)


def v_tools():
    img = grad((70, 70, 100), (235, 180, 120), (180, 130, 110), 0.6)
    d = ImageDraw.Draw(img)
    c = SIL + (255,)
    d.polygon(P([(0, 0.62), (0.5, 0.6), (1, 0.63), (1, 1), (0, 1)]), fill=(52, 40, 38, 255))
    acacia(d, 0.82, 0.62, 0.6, (30, 26, 30, 255))
    # knapped stone core + flakes, lit from the left
    core = [(0.3, 0.86), (0.24, 0.74), (0.27, 0.6), (0.36, 0.52), (0.45, 0.55), (0.52, 0.66), (0.5, 0.8), (0.42, 0.88)]
    d.polygon(P(core), fill=(120, 104, 92, 255))
    facets = [[(0.27, 0.6), (0.36, 0.52), (0.38, 0.66)], [(0.36, 0.52), (0.45, 0.55), (0.38, 0.66)],
              [(0.45, 0.55), (0.52, 0.66), (0.4, 0.72)], [(0.24, 0.74), (0.27, 0.6), (0.38, 0.66), (0.33, 0.78)],
              [(0.52, 0.66), (0.5, 0.8), (0.4, 0.72)], [(0.3, 0.86), (0.33, 0.78), (0.42, 0.88)]]
    for k, f in enumerate(facets):
        g = 150 + (k * 23) % 60
        d.polygon(P(f), fill=(g, int(g * 0.88), int(g * 0.78), 255), outline=(70, 60, 54, 255))
    for x, y in ((0.62, 0.84), (0.68, 0.9), (0.58, 0.92)):
        d.polygon(P([(x, y), (x + 0.04, y - 0.015), (x + 0.05, y + 0.01), (x + 0.01, y + 0.02)]), fill=(150, 132, 116, 255))
    return frame(img)


def v_dino():
    img = grad((30, 20, 40), (230, 120, 70), (140, 60, 60), 0.6)
    d = ImageDraw.Draw(img)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    dl.line(P([(0.95, 0.02), (0.62, 0.32)]), fill=(255, 220, 170, 160), width=16)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(img)
    d.line(P([(0.9, 0.065), (0.63, 0.31)]), fill=(255, 240, 220, 255), width=5)
    glow(img, (0.625, 0.315), 4, (255, 230, 190), 1.0)
    d = ImageDraw.Draw(img)
    c = SIL + (255,)
    d.polygon(P([(0, 0.82), (0.5, 0.8), (1, 0.84), (1, 1), (0, 1)]), fill=c)
    # sauropod
    body = [(0.18, 0.8), (0.2, 0.68), (0.28, 0.62), (0.4, 0.62), (0.46, 0.66), (0.5, 0.56), (0.54, 0.42), (0.56, 0.36),
            (0.6, 0.35), (0.6, 0.38), (0.565, 0.4), (0.53, 0.58), (0.49, 0.72), (0.47, 0.8), (0.44, 0.8), (0.43, 0.72),
            (0.33, 0.73), (0.32, 0.8), (0.29, 0.8), (0.28, 0.73), (0.2, 0.72), (0.08, 0.79), (0.02, 0.8)]
    d.polygon(P(body), fill=c)
    # tree ferns / conifers
    for x, h in ((0.8, 0.3), (0.88, 0.22), (0.7, 0.16)):
        d.line(P([(x, 0.83), (x, 0.83 - h)]), fill=c, width=5)
        for k in range(6):
            a = -math.pi / 2 + (k - 2.5) * 0.45
            d.line(P([(x, 0.83 - h), (x + 0.07 * math.cos(a) * 1.4, 0.83 - h + 0.07 * math.sin(a) * W / H * 0.5 + 0.04)]), fill=c, width=4)
    return frame(img)


ALL = dict(jwst=v_jwst, iss=v_iss, voyager=v_voyager, apollo=v_apollo, radio=v_radio, flyer=v_flyer, ship=v_ship,
           cathedral=v_cathedral, maya=v_maya, rome=v_rome, pyramid=v_pyramid, ice=v_ice, savanna=v_savanna,
           tools=v_tools, dino=v_dino)

if __name__ == "__main__":
    import sys
    keys = sys.argv[1:] or list(ALL)
    for k in keys:
        ALL[k]().convert("RGB").save(os.path.join(OUT, f"vig_{k}.png"))
    # contact sheet
    ims = [Image.open(os.path.join(OUT, f"vig_{k}.png")) for k in ALL]
    sheet = Image.new("RGB", (VW * 4 + 50, (VH + 10) * 4), (30, 30, 30))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % 4) * (VW + 10), (i // 4) * (VH + 10)))
    sheet.save(os.path.join(OUT, "..", "vig_sheet.png"))
