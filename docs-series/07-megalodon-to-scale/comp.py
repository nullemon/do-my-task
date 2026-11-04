"""MEGALODON TO SCALE - numpy/PIL compositor (system python3: numpy + PIL).

Builds every frame from
  * the locked timeline (timeline.py): orthographic camera (frame width W in metres), actors' paths, light level,
  * Blender swim-cycle sprite loops (blender/animals.py -> $SCR/sprites/<species>/f_###.png + meta.json with px-per-metre),
  * a procedural open-ocean background: depth gradient, pre-baked god-ray textures, three parallax layers of marine snow,
    sprite shadows on the light shafts, diver bubbles,
  * true-scale overlays: labels + leader lines, scale bar, school-bus outline, vertebral column, growth-band inset,
    fossil-record timeline, uncertainty ghosts (dashed outlines) and captions in thin widely spaced Inter Light caps.
Everything is placed in METRES and converted with px_per_m = 1920 / W, so every animal is at true relative scale.

Usage: python3 comp.py SEG_START SEG_END [--png FRAME ...]   (seconds; writes $SCR/seg/seg_<start>.mp4, x264 crf 14)
"""
import os, sys, math, json, functools, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import timeline as TL

W_PX, H_PX, FPS = 1920, 1080, TL.FPS
SCR = TL.SCR; SPR = os.path.join(SCR, "sprites"); SEG = os.path.join(SCR, "seg"); TEX = os.path.join(SCR, "tex")
FONT_L = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
FONT_XL = "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf"
TXT = (232, 238, 240)
ACC = (150, 214, 232)          # cool accent
WARM = (255, 178, 120)
S = TL.START


def ss(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0); return t * t * (3 - 2 * t)


def win(t, a, b, fi=0.8, fo=0.8):
    """visibility window with fades"""
    return ss(a, a + fi, t) * (1 - ss(b - fo, b, t))


# ------------------------------------------------------------------------------------------ float blur (box x3 ~ gaussian)
def _box(a, r, axis):
    if r < 1: return a
    n = a.shape[axis]
    pad = [(0, 0)] * a.ndim; pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float32)
    hi = [slice(None)] * a.ndim; lo = [slice(None)] * a.ndim
    hi[axis] = slice(2 * r + 1, 2 * r + 1 + n); lo[axis] = slice(0, n)
    return (c[tuple(hi)] - c[tuple(lo)]) / (2 * r + 1)


def fblur(a, sigma):
    r = max(1, int(round(sigma * 0.8)))
    for _ in range(3):
        a = _box(_box(a, r, 0), r, 1)
    return a


# ------------------------------------------------------------------------------------------ fonts / text
@functools.lru_cache(None)
def font(size, light=True):
    return ImageFont.truetype(FONT_L if light else FONT_XL, size)


def text_w(s, size, track, light=True):
    f = font(size, light)
    return sum(f.getlength(ch) for ch in s) + track * max(0, len(s) - 1)


def draw_text(d, xy, s, size, alpha, col=TXT, track=None, anchor="l", light=True):
    if alpha <= 0.003 or not s: return
    track = size * 0.18 if track is None else track
    f = font(size, light)
    w = text_w(s, size, track, light)
    x, y = xy
    if anchor == "c": x -= w / 2
    elif anchor == "r": x -= w
    a = int(255 * min(1, alpha))
    for ch in s:
        d.text((x, y), ch, font=f, fill=col + (a,))
        x += f.getlength(ch) + track


# ------------------------------------------------------------------------------------------ background
def bake_textures():
    os.makedirs(TEX, exist_ok=True)
    fn = os.path.join(TEX, "rays.npy")
    if os.path.exists(fn): return
    rng = np.random.default_rng(7)
    Wt, Ht = 2880, H_PX
    yy, xx = np.mgrid[0:Ht, 0:Wt].astype(np.float32)
    out = []
    for layer in range(2):
        acc = np.zeros((Ht, Wt), np.float32)
        src_y = -900.0
        for k in range(70 if layer == 0 else 46):
            x0 = rng.uniform(-200, Wt + 200)
            ang = math.atan2(1.0, 0.0)
            # ray through (x0, 0) from a source far above: direction mostly downward with slight fan
            sx = Wt / 2 + (x0 - Wt / 2) * 0.62
            dx = x0 - sx; dy = 0 - src_y
            nrm = math.hypot(dx, dy); dx /= nrm; dy /= nrm
            # perpendicular distance of each pixel to the ray line
            px = xx - x0; py = yy - 0
            dist = np.abs(px * dy - py * dx)
            width = rng.uniform(6, 60) * (1 + yy / Ht * 1.2)
            inten = rng.uniform(0.25, 1.0) * np.exp(-(dist / width) ** 2)
            inten *= np.exp(-yy / (Ht * rng.uniform(0.35, 0.8)))
            acc += inten.astype(np.float32)
        acc /= acc.max()
        out.append(acc.astype(np.float16))
    np.save(fn, np.stack(out))
    # marine snow particles: (layer, x in [0,1), y in [0,1), size, brightness, drift phase)
    pts = []
    for layer, n in ((0, 900), (1, 520), (2, 110)):
        for _ in range(n):
            pts.append((layer, rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.6, 1.4), rng.uniform(0.3, 1.0), rng.uniform(0, 6.28)))
    np.save(os.path.join(TEX, "snow.npy"), np.array(pts, np.float32))


@functools.lru_cache(None)
def textures():
    bake_textures()
    return np.load(os.path.join(TEX, "rays.npy")).astype(np.float32), np.load(os.path.join(TEX, "snow.npy"))


YY = (np.arange(H_PX, dtype=np.float32) / H_PX)[:, None]
TOP = np.array([0.075, 0.30, 0.40], np.float32)        # linear-ish display colours (0..1)
MID = np.array([0.020, 0.115, 0.180], np.float32)
BOT = np.array([0.004, 0.022, 0.045], np.float32)
RAYC = np.array([0.55, 0.85, 0.92], np.float32)


def water_col(y01, depth_shift=0.0):
    """water colour at screen-row fraction y01 (0 top); depth_shift>0 darkens (deeper)"""
    t = np.clip(y01 * 1.0 + depth_shift, 0, 1.6)
    c = np.where(t[..., None] < 0.5, TOP + (MID - TOP) * (t[..., None] / 0.5),
                 MID + (BOT - MID) * np.clip((t[..., None] - 0.5) / 0.6, 0, 1))
    return c


def background(t, Wm, cx, cy, occl):
    rays, _ = textures()
    # vertical gradient depends on camera depth a little (looking deeper when cy is low / zoomed out)
    shift = -0.012 * cy + 0.06 * math.log(Wm / 16.0)
    bg = np.broadcast_to(water_col(YY[:, 0] + shift * 0 + shift)[:, None, :], (H_PX, W_PX, 3)).copy()
    # god rays: two layers sliding slowly + breathing; parallax with camera x
    o1 = int((t * 9.0 + cx * 4.0) % 960); o2 = int((-t * 6.0 + cx * 2.5) % 960)
    r = rays[0][:, o1:o1 + W_PX] * (0.65 + 0.35 * math.sin(t * 0.21)) + rays[1][:, o2:o2 + W_PX] * (0.6 + 0.4 * math.sin(t * 0.17 + 2))
    r *= (1 - occl)
    bg += r[..., None] * RAYC[None, None, :] * 0.16
    return bg


def snow(t, Wm, cx, cy):
    """marine snow, three parallax layers (far layers react less to zoom/pan). Returns additive luminance (H,W)."""
    _, P = textures()
    buf = np.zeros((H_PX // 2, W_PX // 2), np.float32)
    near = np.zeros((H_PX // 4, W_PX // 4), np.float32)
    for layer, zeta, per, bright in ((0, 0.10, 1.6, 0.35), (1, 0.25, 1.4, 0.55), (2, 0.45, 1.25, 0.6)):
        m = P[:, 0] == layer; Q = P[m]
        s = (16.0 / Wm) ** zeta
        Pw = W_PX * per; Ph = H_PX * per
        drift_x = t * (4 + layer * 6) + cx * (1920 / 38.0) * (0.05 + 0.25 * layer)
        drift_y = -t * (5 + 7 * layer) - cy * (1920 / 38.0) * (0.05 + 0.25 * layer)
        x = ((Q[:, 1] * Pw + drift_x + 6 * np.sin(t * 0.5 + Q[:, 5])) % Pw - Pw / 2) * s + W_PX / 2
        y = ((Q[:, 2] * Ph - drift_y + 4 * np.cos(t * 0.4 + Q[:, 5])) % Ph - Ph / 2) * s + H_PX / 2
        b = Q[:, 4] * bright * (0.5 + 0.5 * (1 - y / H_PX))
        if layer < 2:
            ix = (x / 2).astype(int); iy = (y / 2).astype(int)
            ok = (ix >= 0) & (ix < W_PX // 2) & (iy >= 0) & (iy < H_PX // 2)
            np.add.at(buf, (iy[ok], ix[ok]), b[ok] * (0.6 if layer == 0 else 1.0))
        else:
            ix = (x / 4).astype(int); iy = (y / 4).astype(int)
            ok = (ix >= 0) & (ix < W_PX // 4) & (iy >= 0) & (iy < H_PX // 4)
            np.add.at(near, (iy[ok], ix[ok]), b[ok] * 3.0)
    a = np.asarray(Image.fromarray(buf, "F").resize((W_PX, H_PX), Image.BILINEAR))
    nb = np.asarray(Image.fromarray(fblur(near, 1.0), "F").resize((W_PX, H_PX), Image.BICUBIC))
    return a * 0.9 + np.clip(nb, 0, None) * 0.9


# ------------------------------------------------------------------------------------------ sprites
@functools.lru_cache(None)
def meta(sp):
    return json.load(open(os.path.join(SPR, sp, "meta.json")))


@functools.lru_cache(maxsize=96)
def sprite_frame(sp, f):
    return Image.open(os.path.join(SPR, sp, f"f_{f:03d}.png")).convert("RGBA")


def to_px(x, y, Wm, cx, cy):
    k = W_PX / Wm
    return W_PX / 2 + (x - cx) * k, H_PX / 2 - (y - cy) * k


def place_sprite(sp, frame, L, x_nose, y_axis, face, Wm, cx, cy):
    """Return (rgba float array premultiplied (h,w,4), x0, y0) of the sprite transformed to screen at true scale."""
    m = meta(sp)
    im = sprite_frame(sp, frame)
    k = (W_PX / Wm) / m["ppm"] * (L / m["L"])          # sprite px -> screen px
    if face < 0: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    nose_sx = m["nose_px"][0] if face > 0 else m["res"][0] - m["nose_px"][0]
    ax_sy = m["axis_py"]
    X, Y = to_px(x_nose, y_axis, Wm, cx, cy)
    # screen position of sprite pixel (0,0)
    ox = X - nose_sx * k; oy = Y - ax_sy * k
    # pre-reduce big downscales
    red = 1
    while k * red * 2 < 0.55 and min(im.size) > 64 * red * 2: red *= 2
    if red > 1:
        im = im.reduce(red); k *= red
    w = int(math.ceil(im.size[0] * k)) + 2; h = int(math.ceil(im.size[1] * k)) + 2
    x0 = int(math.floor(ox)); y0 = int(math.floor(oy)); fx = ox - x0; fy = oy - y0
    if x0 > W_PX or y0 > H_PX or x0 + w < 0 or y0 + h < 0: return None
    # crop the output window to the screen (+margin) to save work on huge sprites
    cx0 = max(0, -x0 - 4); cy0 = max(0, -y0 - 4)
    cw = min(w, W_PX - x0 + 4) - cx0; ch = min(h, H_PX - y0 + 4) - cy0
    if cw <= 0 or ch <= 0: return None
    inv = 1.0 / k
    out = im.transform((cw, ch), Image.AFFINE, data=(inv, 0, (cx0 - fx) * inv, 0, inv, (cy0 - fy) * inv), resample=Image.BILINEAR)
    a = np.asarray(out, np.float32) / 255.0
    rgb = a[..., :3] ** 2.2 * a[..., 3:4]          # sprite PNGs are display-referred -> roughly linear, premultiplied
    return np.concatenate([rgb, a[..., 3:4]], -1), x0 + cx0, y0 + cy0


def composite(dst, src, x0, y0, opacity=1.0, haze=0.0, light=1.0, tint=None, blur=0):
    h, w = src.shape[:2]
    X0, Y0 = max(0, x0), max(0, y0); X1, Y1 = min(W_PX, x0 + w), min(H_PX, y0 + h)
    if X1 <= X0 or Y1 <= Y0: return
    s = src[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    if blur:
        s = fblur(s, blur)
    a = s[..., 3:4] * opacity
    rgb = s[..., :3] * opacity * light
    if tint is not None:
        rgb = rgb * (1 - tint[1]) + tint[0][None, None, :] * a * tint[1] * light
    if haze > 0:
        wc = water_col(YY[Y0:Y1, 0])[:, None, :] * light
        rgb = rgb * (1 - haze) + wc * a * haze
    dst[Y0:Y1, X0:X1] = dst[Y0:Y1, X0:X1] * (1 - a) + rgb


def ghost(dst, src, x0, y0, opacity, col=(0.75, 0.88, 0.95), fill=0.08, dash=True, ovl=None):
    """uncertainty ghost: faint fill + dashed outline from the sprite alpha"""
    h, w = src.shape[:2]
    al = src[..., 3]
    A = Image.fromarray((np.clip(al, 0, 1) * 255).astype(np.uint8), "L")
    er = np.asarray(A.filter(ImageFilter.MinFilter(3)), np.float32) / 255.0
    edge = np.clip(al - er, 0, 1)
    if dash:
        xx = np.arange(w)[None, :] + x0; yy = np.arange(h)[:, None] + y0
        pat = ((np.floor((xx + yy * 0.35) / 7.0) % 2) == 0).astype(np.float32)
        edge = edge * pat
    a = np.clip(edge * 0.9 + al * fill, 0, 1) * opacity
    rgb = np.array(col, np.float32)[None, None, :] * a[..., None]
    composite(dst, np.concatenate([rgb, a[..., None]], -1), x0, y0)


# ------------------------------------------------------------------------------------------ overlays (PIL RGBA layer)
def nice_len(Wm):
    for L in (0.5, 1, 2, 5, 10, 20, 50):
        if L * W_PX / Wm >= 110: return L
    return 50


def scale_bar(d, t, Wm, alpha):
    if alpha <= 0: return
    L = nice_len(Wm); px = L * W_PX / Wm
    x0, y0 = 96, 1000
    a = int(200 * alpha)
    d.line([(x0, y0), (x0 + px, y0)], fill=TXT + (a,), width=2)
    for xx in (x0, x0 + px): d.line([(xx, y0 - 9), (xx, y0 + 9)], fill=TXT + (a,), width=2)
    lab = f"{L:g} M"
    draw_text(d, (x0 + px + 18, y0 - 11), lab, 18, alpha * 0.85)
    draw_text(d, (x0, y0 + 20), "TRUE RELATIVE SCALE", 13, alpha * 0.5, track=4.5)


def label(d, anchor_xy, text1, text2, alpha, side=1, dy=-70, dx=40, size=24):
    if alpha <= 0.01: return
    x, y = anchor_xy
    a = int(170 * alpha)
    x2, y2 = x + dx * side, y + dy
    d.line([(x, y), (x2, y2)], fill=TXT + (a,), width=1)
    d.line([(x2, y2), (x2 + 26 * side, y2)], fill=TXT + (a,), width=1)
    tx = x2 + 34 * side
    anch = "l" if side > 0 else "r"
    draw_text(d, (tx, y2 - size * 0.72), text1, size, alpha, anchor=anch)
    if text2:
        draw_text(d, (tx, y2 + size * 0.45), text2, int(size * 0.62), alpha * 0.75, col=ACC, anchor=anch, track=size * 0.14)


def caption(d, lines, alpha, y=880, size=30):
    for i, (txt, sz, col) in enumerate(lines):
        draw_text(d, (W_PX / 2, y + i * (size * 1.25)), txt, sz or size, alpha, col=col or TXT, anchor="c")


def bus_outline(d, x_left, y_bottom, Wm, cx, cy, alpha):
    """US school bus side outline, 12.0 m x 3.2 m (schematic), drawn in metres."""
    if alpha <= 0: return
    def P(x, y): return to_px(x_left + x, y_bottom + y, Wm, cx, cy)
    a = int(210 * alpha); c = (255, 214, 120, a)
    body = [P(0.0, 0.45), P(0.0, 2.6), P(0.25, 3.0), P(11.7, 3.05), P(12.0, 2.8), P(12.0, 0.45)]
    d.line(body + [body[0]], fill=c, width=2)
    for i in range(9):
        x = 1.2 + i * 1.12
        d.rectangle([P(x, 2.65), P(x + 0.85, 1.75)], outline=c, width=1)
    d.rectangle([P(11.0, 2.65), P(11.85, 1.6)], outline=c, width=1)   # windshield side
    for xw in (2.3, 9.6):
        X, Y = P(xw, 0.45); r = 0.5 * W_PX / Wm
        d.ellipse([X - r, Y - r, X + r, Y + r], outline=c, width=2)
    d.line([P(0.0, 1.25), P(12.0, 1.25)], fill=(255, 214, 120, int(a * 0.5)), width=1)


def vertebral_column(d, x_start, x_end, y, Wm, cx, cy, alpha, n=141):
    if alpha <= 0: return
    k = W_PX / Wm
    step = (x_end - x_start) / n
    a = int(235 * alpha)
    for i in range(n):
        u = i / (n - 1)
        hgt = (0.155 * (0.9 + 0.25 * math.sin(math.pi * min(1, u * 1.3))) * (1 - 0.45 * u))   # centrum diameter ~15.5 cm max
        x = x_start + (i + 0.5) * step
        X, Y = to_px(x, y, Wm, cx, cy)
        hw = max(0.6, step * k * 0.36); hh = max(1.5, hgt * k * 1.0)
        d.rectangle([X - hw, Y - hh, X + hw, Y + hh], fill=(236, 230, 214, a))


def vertebra_inset(d, t, alpha, cxy=(1560, 330), r=150):
    if alpha <= 0: return
    a = int(230 * alpha)
    X, Y = cxy
    d.ellipse([X - r - 6, Y - r - 6, X + r + 6, Y + r + 6], outline=TXT + (int(a * 0.5),), width=1)
    nshow = int(np.clip((t - S["age"] - 0.8) / 4.5, 0, 1) * 46)
    for i in range(46):
        rr = r * (0.10 + 0.9 * (1 - (1 - (i + 1) / 46) ** 1.25))
        col = (236, 226, 204, a if i < nshow else int(a * 0.15))
        d.ellipse([X - rr, Y - rr, X + rr, Y + rr], outline=col, width=1)
    draw_text(d, (X, Y + r + 22), f"{max(nshow, 0):d} GROWTH BANDS", 20, alpha, anchor="c")
    draw_text(d, (X, Y + r + 52), "≈ 46 YEARS OLD · SHIMADA ET AL. 2021", 14, alpha * 0.75, col=ACC, anchor="c", track=3)


def tooth_inset(d, t, alpha, cxy=(1500, 300), s_px=1.6):
    """18 cm tooth vs an adult hand (~19 cm), both at the same (inset) scale: s_px pixels per mm"""
    if alpha <= 0: return
    a = int(235 * alpha)
    X, Y = cxy
    # megalodon upper anterior tooth: triangular crown + root, slant height 180 mm, width ~ 130 mm
    H = 180 * s_px; Wt = 128 * s_px
    crown = [(X - Wt / 2, Y + H * 0.30), (X - Wt * 0.08, Y - H * 0.62), (X, Y - H * 0.70), (X + Wt * 0.08, Y - H * 0.62), (X + Wt / 2, Y + H * 0.30)]
    root = [(X - Wt / 2, Y + H * 0.30), (X - Wt * 0.46, Y + H * 0.30 + 6), (X - Wt * 0.32, Y + H * 0.30 + H * 0.06),
            (X, Y + H * 0.30 + H * 0.02), (X + Wt * 0.32, Y + H * 0.30 + H * 0.06), (X + Wt * 0.46, Y + H * 0.30 + 6), (X + Wt / 2, Y + H * 0.30)]
    d.polygon(crown, fill=(206, 196, 172, int(a * 0.85)))
    d.polygon(root, fill=(120, 104, 86, int(a * 0.9)))
    d.line([(X - Wt * 0.45, Y + H * 0.25), (X + Wt * 0.45, Y + H * 0.25)], fill=(150, 132, 108, int(a * 0.7)), width=3)
    # hand outline (palm + fingers), 190 mm wrist-to-fingertip, to the left of the tooth
    hx = X - Wt / 2 - 150; hy = Y + H * 0.34
    pal_w = 84 * s_px; pal_h = 100 * s_px
    c = TXT + (int(a * 0.75),)
    d.rounded_rectangle([hx - pal_w / 2, hy - pal_h, hx + pal_w / 2, hy], radius=14, outline=c, width=2)
    for i, (fl, off) in enumerate(((78, -0.36), (90, -0.12), (86, 0.12), (68, 0.35))):
        fx = hx + off * pal_w; fw = 9 * s_px
        d.rounded_rectangle([fx - fw, hy - pal_h - fl * s_px, fx + fw, hy - pal_h + 6], radius=int(fw), outline=c, width=2)
    d.rounded_rectangle([hx + pal_w / 2 - 10, hy - pal_h * 0.62, hx + pal_w / 2 + 52, hy - pal_h * 0.40], radius=12, outline=c, width=2)
    draw_text(d, (X, Y + H * 0.42 + 26), "≈ 18 CM", 24, alpha, anchor="c")
    draw_text(d, (X, Y + H * 0.42 + 60), "LARGEST TEETH (SLANT HEIGHT)", 13, alpha * 0.75, col=ACC, anchor="c", track=3.5)
    draw_text(d, (hx, Y + H * 0.42 + 26), "ADULT HAND", 15, alpha * 0.8, anchor="c", track=3.5)


def fossil_timeline(d, t, alpha, mode="range"):
    if alpha <= 0: return
    a = int(220 * alpha)
    x0, x1, y = 260, 1660, 960       # 25 Ma -> today
    def X(ma): return x0 + (25 - ma) / 25 * (x1 - x0)
    d.line([(x0, y), (x1, y)], fill=TXT + (int(a * 0.6),), width=1)
    for ma in (25, 20, 15, 10, 5, 0):
        d.line([(X(ma), y - 6), (X(ma), y + 6)], fill=TXT + (int(a * 0.6),), width=1)
        draw_text(d, (X(ma), y + 16), ("TODAY" if ma == 0 else f"{ma} MA"), 13, alpha * 0.6, anchor="c", track=3)
    if mode == "range":
        u = ss(S["time"] + 0.5, S["time"] + 4.0, t)
        xe = X(23) + (X(3.6) - X(23)) * u
        d.rectangle([X(23), y - 4, xe, y + 4], fill=WARM + (a,))
        draw_text(d, (X(23), y - 42), "≈ 23 MILLION YEARS AGO", 16, alpha * ss(S["time"], S["time"] + 1, t), anchor="c", track=3.5)
        draw_text(d, (X(3.6), y - 42), "≈ 3.6", 16, alpha * ss(S["time"] + 3.5, S["time"] + 4.5, t), anchor="c", track=3.5)
    else:
        rng = np.random.default_rng(5)
        mas = np.concatenate([rng.uniform(3.6, 23, 220), rng.uniform(3.6, 6, 30)])
        reveal = ss(S["myth"] + 6.0, S["myth"] + 10.5, t)
        for i, ma in enumerate(mas):
            if i / len(mas) > reveal: continue
            xx = X(ma); yy = y - 8 - rng.uniform(0, 26)
            d.polygon([(xx - 3, yy + 4), (xx, yy - 5), (xx + 3, yy + 4)], fill=(222, 210, 186, int(a * 0.8)))
        if reveal > 0.95:
            q = ss(S["myth"] + 10.6, S["myth"] + 12.0, t)
            d.line([(X(3.6), y - 46), (X(3.6), y + 4)], fill=WARM + (int(a * q),), width=2)
            draw_text(d, (X(3.6), y - 76), "LAST FOSSILS ≈ 3.6 MA", 15, alpha * q, col=WARM, anchor="c", track=3.5)
            draw_text(d, ((X(3.6) + X(0)) / 2, y - 34), "NOTHING", 14, alpha * q * 0.8, anchor="c", track=6)


# ------------------------------------------------------------------------------------------ frame
ACT = {a["id"]: a for a in TL.ACTORS}


def actor_screen_anchor(aid, t, Wm, cx, cy, frac=0.35, up=1.0):
    """screen point above an actor's back (for labels)"""
    a = ACT[aid]; x = TL.actor_x(a, t)
    xs = x + a["L"] * frac * (1 if a["face"] < 0 else -1)
    return to_px(xs, a["y"] + up, Wm, cx, cy)


def render_frame(fi):
    t = fi / FPS
    Wm, cx, cy = TL.cam(t)
    lt = TL.light(t)
    # ---- sprites (placed first so they can cast shadows into the light shafts)
    placed = []
    for a in TL.ACTORS:
        al = TL.actor_alpha(a, t)
        if al <= 0.002: continue
        m = meta(a["sprite"])
        f = 0 if a.get("static") else int((t * FPS + sum(map(ord, a["id"])) % 97) % m["frames"])
        r = place_sprite(a["sprite"], f, a["L"], TL.actor_x(a, t), a["y"], a["face"], Wm, cx, cy)
        if r is None: continue
        placed.append((a, al, r))
    occl = np.zeros((H_PX // 8, W_PX // 8), np.float32)
    for a, al, (src, x0, y0) in placed:
        if a["style"] != "solid": continue
        sm = Image.fromarray(np.ascontiguousarray(src[..., 3]), "F")
        w8 = max(1, src.shape[1] // 8); h8 = max(1, src.shape[0] // 8)
        sm = np.asarray(sm.resize((w8, h8), Image.BILINEAR))
        X0 = x0 // 8; Y0 = y0 // 8
        xa, ya = max(0, X0), max(0, Y0); xb, yb = min(W_PX // 8, X0 + w8), min(H_PX // 8, Y0 + h8)
        if xb > xa and yb > ya:
            occl[ya:yb, xa:xb] = np.maximum(occl[ya:yb, xa:xb], sm[ya - Y0:yb - Y0, xa - X0:xb - X0] * al)
    # shadow falls downward: running max with decay along y
    for yv in range(1, occl.shape[0]):
        occl[yv] = np.maximum(occl[yv], occl[yv - 1] * 0.985)
    occ = np.asarray(Image.fromarray(fblur(occl, 3.0), "F").resize((W_PX, H_PX), Image.BILINEAR))
    occ = np.clip(occ * 0.75, 0, 0.85)
    img = background(t, Wm, cx, cy, occ)
    img *= (1 - 0.35 * occ)[..., None]
    img += snow(t, Wm, cx, cy)[..., None] * np.array([0.30, 0.42, 0.46], np.float32)[None, None, :] * 0.35
    img *= lt
    # ---- actors
    for a, al, (src, x0, y0) in placed:
        if a["style"] == "ghost":
            ghost(img, src, x0, y0, al * lt ** 0.5 * 0.85)
            continue
        tint = None
        if a["id"] in ("megs", "megc"):
            wv = win(t, S["warm"] + 0.5, S["ext"] - 0.5, 1.5, 2.0)
            if wv > 0: tint = (np.array([0.55, 0.20, 0.06], np.float32), 0.22 * wv)
            xr = win(t, S["est2"] + 0.2, S["est3"] + 2.0, 1.0, 2.0)
            al = al * (1 - 0.62 * xr)
        composite(img, src, x0, y0, opacity=al, haze=a["haze"], light=lt, tint=tint, blur=a.get("blur", 0))
    # ---- ghost overlays that depend on narration
    # est1: the old great-white-scaled estimates 15 / 18 / 20 m (aligned at the snout)
    for k, (Lg, ts) in enumerate(((15.0, S["est1"] + 3.4), (18.0, S["est1"] + 4.6), (20.0, S["est1"] + 5.9))):
        al = ss(ts, ts + 0.6, t) * (1 - ss(S["est2"] - 0.5, S["est2"] + 0.8, t))
        if al > 0:
            xn = TL.actor_x(ACT["megc"], t)
            r = place_sprite("gw", 0, Lg, xn, ACT["megc"]["y"], -1, Wm, cx, cy)
            if r: ghost(img, r[0], r[1], r[2], al * 0.8, col=(1.0, 0.86, 0.62), fill=0.03)
    # ceil: slender ghosts at 20 and 24.3 m
    for Lg, ts in ((20.0, S["ceil"] + 2.0), (24.3, S["ceil"] + 3.6)):
        al = ss(ts, ts + 1.0, t) * (1 - ss(S["bite"] - 1.0, S["bite"] + 1.0, t))
        if al > 0:
            xn = TL.actor_x(ACT["megs"], t)
            r = place_sprite("mega", int(t * FPS) % meta("mega")["frames"], Lg, xn, ACT["megs"]["y"], -1, Wm, cx, cy)
            if r: ghost(img, r[0], r[1], r[2], al * (0.9 if Lg > 21 else 0.6), fill=0.06)
    # ---- to 8-bit, then PIL overlay layer
    out = np.clip(img, 0, 1) ** (1 / 2.2)
    base = Image.fromarray((out * 255 + np.random.default_rng(fi).uniform(0, 1, (H_PX, W_PX, 1))).clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    ov = Image.new("RGBA", (W_PX, H_PX), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    overlays(d, t, Wm, cx, cy, lt)
    base.alpha_composite(ov)
    return np.asarray(base.convert("RGB"))


def overlays(d, t, Wm, cx, cy, lt):
    # title
    ta = win(t, 11.6, 15.6, 1.2, 1.3)
    draw_text(d, (W_PX / 2, 486), "MEGALODON TO SCALE", 64, ta, anchor="c", track=24, light=False)
    draw_text(d, (W_PX / 2, 584), "EVERY ANIMAL DRAWN AT TRUE RELATIVE SIZE", 17, ta * 0.8, col=ACC, anchor="c", track=7)
    # scale bar (whenever there is a scene to measure)
    scale_bar(d, t, Wm, win(t, 15.8, 309.0, 1.0, 1.5) * (1 - 0.7 * win(t, S["time"] - 0.5, S["bite"] - 0.5, 1, 1)))
    # species labels
    def L(aid, a0, a1, t1, t2, frac=0.35, up=1.0, side=1, dy=-70, dx=40, size=24):
        al = win(t, a0, a1, 0.9, 1.2)
        if al > 0: label(d, actor_screen_anchor(aid, t, Wm, cx, cy, frac, up), t1, t2, al, side=side, dy=dy, dx=dx, size=size)
    dv = win(t, S["diver"] + 0.5, S["bull"] - 0.4, 1.0, 1.0)
    if dv > 0:
        X, Y = to_px(-0.8, 0.35, Wm, cx, cy)
        label(d, (X, Y), "DIVER", "≈ 1.8 M TALL · 2.4 M WITH FINS", dv, side=-1, dy=-90, dx=50)
    L("bull", S["bull"] - 0.2, S["gw1"] + 1.0, "BULL SHARK", "LARGE FEMALES ≈ 3.5 M · SHOWN 3.3 M", frac=0.3, up=0.45)
    L("gw", S["gw1"] - 0.2, S["bus"] - 0.6, "GREAT WHITE", "ADULTS 4 – 5 M · LARGEST RELIABLE ≈ 6 M · SHOWN 6 M", frac=0.4, up=-0.7, dy=80)
    ba = win(t, S["bus"] - 0.6, S["ws"] + 13.0, 1.0, 1.5)
    bus_outline(d, -3.5, ACT["ws"]["y"] - 1.6, Wm, cx, cy, ba * lt)
    if ba > 0:
        X, Y = to_px(-3.5, ACT["ws"]["y"] + 1.6, Wm, cx, cy)
        label(d, (X + 4, Y - 4), "SCHOOL BUS", "≈ 12 M", ba * win(t, S["bus"] - 0.6, S["ws"] - 0.2, 1.0, 0.8), side=-1, dy=-50, dx=30)
    L("ws", S["ws"] - 0.2, S["orca"] - 0.2, "WHALE SHARK", "BIG ADULTS ≈ 12 M · LARGEST RELIABLE ≈ 18.8 M (EST.)", frac=0.45, up=1.8)
    L("orca", S["orca"] - 0.2, S["hump"] + 1.5, "ORCA", "LARGE MALES ≈ 8 M", frac=0.35, up=-1.5, dy=80)
    L("hump", S["hump"] - 0.2, S["megA"] + 0.5, "HUMPBACK WHALE", "≈ 15 M · FLIPPERS ≈ ⅓ BODY LENGTH", frac=0.35, up=2.0, dy=-50)
    # megalodon
    ma = win(t, S["megA"] + 1.0, S["megB"] + 6.0, 1.5, 1.5)
    if ma > 0:
        label(d, actor_screen_anchor("megc", t, Wm, cx, cy, 0.3, 3.2), "MEGALODON", "OTODUS MEGALODON · AS IT IS OFTEN PICTURED", ma, dy=-60, size=28)
    # skeleton note
    caption(d, [("CARTILAGE SKELETON · RARELY FOSSILISES", 20, None), ("WHAT SURVIVES: TEETH · RARE VERTEBRAL COLUMNS", 16, ACC)],
            win(t, S["megB"] + 5.5, S["teeth"] - 0.3, 1.0, 1.0), y=905)
    tooth_inset(d, t, win(t, S["teeth"] + 0.5, S["est1"] + 0.2, 1.0, 1.0) * lt)
    # est1 labels
    for Lg, ts in ((15, S["est1"] + 3.4), (18, S["est1"] + 4.6), (20, S["est1"] + 5.9)):
        al = ss(ts, ts + 0.6, t) * (1 - ss(S["est2"] - 0.5, S["est2"] + 0.8, t))
        if al > 0:
            xn = TL.actor_x(ACT["megc"], t)
            X, Y = to_px(xn + Lg, ACT["megc"]["y"] + 0.3 + (Lg - 15) * 0.05, Wm, cx, cy)
            draw_text(d, (X + 14, Y - 12 - (Lg - 15) * 9), f"{Lg} M", 20, al, col=(255, 220, 160))
    caption(d, [("OLDER ESTIMATES: A GREAT WHITE, SCALED UP FROM TEETH", 20, None), ("≈ 15 – 20 M MAXIMUM (E.G. GOTTFRIED ET AL. 1996 · PIMIENTO & BALK 2015 · PEREZ ET AL. 2021)", 13, ACC)],
            win(t, S["est1"] + 0.5, S["est2"] - 0.2, 1.0, 1.0), y=905)
    # est2 vertebral column (11.1 m, 141 centra), from behind the head
    va = win(t, S["est2"] + 1.5, S["est3"] + 3.0, 1.5, 2.0)
    if va > 0:
        a = ACT["megc"]; xn = TL.actor_x(a, t)
        vertebral_column(d, xn + 2.1, xn + 2.1 + 11.1, a["y"] + 0.15, Wm, cx, cy, va * lt)
        X0, Y0 = to_px(xn + 2.1, a["y"] - 1.6, Wm, cx, cy); X1, _ = to_px(xn + 13.2, a["y"], Wm, cx, cy)
        d.line([(X0, Y0), (X1, Y0)], fill=TXT + (int(160 * va),), width=1)
        for xx in (X0, X1): d.line([(xx, Y0 - 6), (xx, Y0 + 6)], fill=TXT + (int(160 * va),), width=1)
        draw_text(d, ((X0 + X1) / 2, Y0 + 12), "141 VERTEBRAE · ≈ 11.1 M OF BACKBONE · ONE INDIVIDUAL, BELGIUM", 15, va, anchor="c", track=3.5)
    vertebra_inset(d, t, win(t, S["age"] + 0.2, S["est3"] + 0.5, 1.0, 1.2) * lt)
    caption(d, [("2024 · 2025: LONGER AND SLIMMER THAN A GREAT WHITE", 20, None), ("CLOSER IN SHAPE TO A LEMON SHARK (STERNES ET AL. 2024 · SHIMADA ET AL. 2025)", 13, ACC)],
            win(t, S["est3"] + 5.0, S["best"] - 0.3, 1.0, 1.0), y=905)
    ba = win(t, S["best"] + 0.3, S["ceil"] + 1.5, 1.2, 1.2)
    if ba > 0:
        a = ACT["megs"]; xn = TL.actor_x(a, t)
        X0, Y0 = to_px(xn, a["y"] - 2.8, Wm, cx, cy); X1, _ = to_px(xn + 16.4, a["y"], Wm, cx, cy)
        d.line([(X0, Y0), (X1, Y0)], fill=WARM + (int(200 * ba),), width=2)
        for xx in (X0, X1): d.line([(xx, Y0 - 8), (xx, Y0 + 8)], fill=WARM + (int(200 * ba),), width=2)
        draw_text(d, ((X0 + X1) / 2, Y0 + 14), "≈ 16 M · BEST-GROUNDED REAL INDIVIDUAL", 20, ba, anchor="c", col=WARM)
        draw_text(d, ((X0 + X1) / 2, Y0 + 44), "BELGIAN SPECIMEN, SLENDER RECONSTRUCTION · SHIMADA ET AL. 2025", 13, ba * 0.8, anchor="c", col=ACC, track=3.2)
    ca = win(t, S["ceil"] + 2.0, S["bite"] - 0.5, 1.2, 1.2)
    if ca > 0:
        a = ACT["megs"]; xn = TL.actor_x(a, t)
        for Lg, ts, txt in ((20.0, S["ceil"] + 2.0, "20 M"), (24.3, S["ceil"] + 3.6, "24.3 M · UPPER LIMIT")):
            q = ss(ts, ts + 1.0, t) * ca
            X, Y = to_px(xn + Lg, a["y"] + 1.0, Wm, cx, cy)
            draw_text(d, (X + 12, Y - 10 - (12 if Lg > 21 else 0)), txt, 17, q, col=(200, 230, 245))
        caption(d, [("MOST WERE SMALLER · ≈ 24 M IS THE LARGEST SIZE THE EVIDENCE CAN SUPPORT", 18, None),
                    ("FROM A 23 CM VERTEBRA, DENMARK · BODY SHAPE AND FINS REMAIN UNKNOWN", 13, ACC)],
                win(t, S["ceil"] + 7.0, S["bite"] - 0.5, 1.0, 1.0), y=905)
    # time span
    fossil_timeline(d, t, win(t, S["time"] - 0.3, S["bite"] - 0.4, 1.0, 1.0), "range")
    caption(d, [("COMPUTER MODEL · BITE FORCE ≈ 108,000 – 182,000 N", 20, None),
                ("≈ 11 – 18 TONNES-FORCE · WROE ET AL. 2008 · SCALED UP FROM A GREAT WHITE", 13, ACC)],
            win(t, S["bite"] + 0.5, S["warm"] - 0.2, 1.0, 1.0), y=905)
    caption(d, [("≈ 7 °C WARMER THAN THE WATER AROUND IT", 20, WARM),
                ("TOOTH-CHEMISTRY ESTIMATE · BODY ≈ 27 °C · PARTLY WARM-BLOODED · GRIFFITHS ET AL. 2023", 13, ACC)],
            win(t, S["warm"] + 3.0, S["ext"] - 0.5, 1.0, 1.0), y=905)
    # extinction hypotheses
    ea = win(t, S["ext"] + 1.8, S["myth"] - 0.3, 1.0, 1.2)
    if ea > 0:
        items = [("COOLING CLIMATE · FALLING SEA LEVELS · FEWER SHALLOW NURSERIES", S["ext"] + 2.0),
                 ("CHANGES IN ITS PREY (WHALES, SEALS)", S["ext"] + 7.6),
                 ("COMPETITION · THE GREAT WHITE (MCCORMACK ET AL. 2022)", S["ext"] + 10.8)]
        draw_text(d, (W_PX / 2, 838), "WHY IT VANISHED · LEADING HYPOTHESES, NOT SETTLED", 13, ea * 0.75, col=ACC, anchor="c", track=4)
        for i, (txt, ts) in enumerate(items):
            draw_text(d, (W_PX / 2, 872 + i * 38), txt, 19, ea * ss(ts, ts + 0.8, t), anchor="c")
    ga = win(t, S["ext"] + 13.6, S["myth"] - 0.5, 0.8, 1.0)
    if ga > 0: label(d, actor_screen_anchor("gw2", t, Wm, cx, cy, 0.4, 0.9), "GREAT WHITE", "≈ 6 M", ga, dy=-60)
    # myth
    my = win(t, S["myth"] + 0.5, S["twist"] - 0.4, 1.2, 1.2)
    fossil_timeline(d, t, my, "record")
    draw_text(d, (W_PX / 2, 300), "EXTINCT", 46, my * ss(S["myth"] + 0.3, S["myth"] + 1.5, t), anchor="c", track=20, light=False)
    draw_text(d, (W_PX / 2, 372), "NOT HIDING IN THE DEEP SEA", 17, my * ss(S["myth"] + 1.5, S["myth"] + 2.6, t) * 0.85, col=ACC, anchor="c", track=6)
    draw_text(d, (W_PX / 2, 1018), "TV SPECIALS CLAIMING IT SURVIVES (E.G. 2013) WERE FICTION", 14,
              my * ss(S["myth"] + 13.5, S["myth"] + 14.5, t) * 0.8, anchor="c", track=4)
    # twist: blue whale + perucetus
    L("blue", S["blue"] + 2.5, S["end1"] - 1.0, "BLUE WHALE", "UP TO ≈ 30 M · WELL OVER 100 TONNES · ALIVE TODAY", frac=0.42, up=1.6, dy=-60, size=26)
    xa = win(t, S["twist"] + 4.0, S["end1"] - 1.0, 1.2, 1.2)
    if xa > 0: label(d, actor_screen_anchor("megghost", t, Wm, cx, cy, 0.3, 1.6), "MEGALODON", "≈ 16 M (UP TO ≈ 24?) · EXTINCT", xa, dy=-40, size=20)
    pa = win(t, S["peru"] + 3.0, S["end1"] - 1.0, 1.2, 1.2)
    if pa > 0:
        label(d, actor_screen_anchor("peru", t, Wm, cx, cy, 0.3, 1.0), "PERUCETUS COLOSSUS · ≈ 39 MA", "≈ 17 M · PARTIAL SKELETON ONLY · SHAPE CONJECTURAL", pa, dy=-40, size=20)
        caption(d, [("2023 ESTIMATE: 85 – 340 TONNES (BIANUCCI ET AL.) · 2024 REVISION: ≈ 60 – 70 TONNES (MOTANI & PYENSON)", 15, None),
                    ("THE BLUE WHALE IS STILL THE HEAVIEST ANIMAL KNOWN", 18, WARM)],
                win(t, S["peru"] + 6.5, S["end1"] - 1.0, 1.0, 1.2), y=935)
    # end card
    ea = win(t, 309.6, TL.DUR + 1, 1.6, 0.1) * (1 - ss(314.8, 315.9, t))
    draw_text(d, (W_PX / 2, 492), "MEGALODON TO SCALE", 56, ea, anchor="c", track=22, light=False)
    draw_text(d, (W_PX / 2, 578), "OTODUS MEGALODON · ≈ 23 – 3.6 MILLION YEARS AGO", 16, ea * 0.75, col=ACC, anchor="c", track=6)


# ------------------------------------------------------------------------------------------ main
def main():
    args = sys.argv[1:]
    if args and args[0] == "--png":
        os.makedirs(os.path.join(SCR, "test"), exist_ok=True)
        for s_ in args[1:]:
            t = float(s_); fr = int(round(t * FPS))
            t0 = time.time(); im = render_frame(fr)
            Image.fromarray(im).save(os.path.join(SCR, "test", f"t_{t:07.2f}.png"))
            print(f"t={t} {time.time() - t0:.2f}s", flush=True)
        return
    a, b = float(args[0]), float(args[1])
    f0, f1 = int(round(a * FPS)), min(TL.NFR, int(round(b * FPS)))
    os.makedirs(SEG, exist_ok=True)
    out = os.path.join(SEG, f"seg_{f0:05d}.mp4")
    if os.path.exists(out): print("exists", out); return
    tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W_PX}x{H_PX}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    t0 = time.time()
    for fr in range(f0, f1):
        p.stdin.write(render_frame(fr).tobytes())
        if (fr - f0) % 48 == 0: print(f"frame {fr} ({(time.time() - t0) / max(1, fr - f0 + 1):.2f}s/f)", flush=True)
    p.stdin.close(); p.wait()
    os.rename(tmp, out)
    print("done", out, f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
