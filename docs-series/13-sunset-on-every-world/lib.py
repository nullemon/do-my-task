"""Shared numpy/cv2 library for 13 'Sunset on every world'.  Linear light (float32, HDR), tone-mapped once at the end.
 - Plate: loads the Blender passes of one world (beauty = sun / glow / dome in R / G / B, albedo, normal, log depth + flag),
   crops them for 16:9 or 9:16 and exposes per-pixel elevation / azimuth so skies are functions of direction
 - sun discs, glows, cirrus, stars, Saturn's rings as seen from the cloud tops, analytic sea (waves, Fresnel, glitter)
 - bloom / tone-map / thin Inter typography / HUD (helpers shared with film 08)
"""
import os, sys, math
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world"
sys.path.insert(0, os.path.join(SCR, "pylib"))
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
cv2.setNumThreads(2)
VERT = os.environ.get("VERT") == "1"          # 9:16 recomposition (1080x1920)
W, H = (1080, 1920) if VERT else (1920, 1080)
def hv(h, v): return v if VERT else h
f32 = np.float32
FOV = 24.0; HORIZ = 0.60                      # must match blender/world.py
HY = hv(0.63, 0.60)                           # horizon row as a fraction of the output frame height


def lin(x): return np.power(np.clip(x, 0, 1), 2.2, dtype=f32) if x.dtype == f32 else np.power(np.clip(x, 0, 1), 2.2).astype(f32)
def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def norm(v): v = np.asarray(v, float); return v / np.linalg.norm(v)
def ease(t): t = min(max(t, 0.0), 1.0); return t * t * (3 - 2 * t)
def ramp(t, a, b): return ease((t - a) / (b - a))
def kf(t, keys):
    """piecewise smoothstep keyframes [(t, v), ...] (v scalar or tuple)"""
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / (t1 - t0))
            if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u


def fbm2(shape, seed, beta=2.0, lo=0.0):
    """spectral noise, periodic, normalised to mean 0 std 1"""
    h, w = shape; r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None] * h; fx = np.fft.rfftfreq(w)[None, :] * w
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    amp = f ** (-beta / 2.0); amp[0, 0] = 0
    if lo: amp[f < lo] = 0
    z = np.fft.irfft2(amp * np.exp(1j * r.uniform(0, 2 * np.pi, amp.shape)), s=(h, w))
    return ((z - z.mean()) / z.std()).astype(f32)

def bloom(img, amt=1.0, thr=0.0):
    """multi-scale glow of the HDR frame (energy-conserving-ish)"""
    src = np.maximum(img - thr, 0) if thr else img
    small = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    acc = np.zeros_like(small)
    for s, wg in ((1.6, 0.30), (5, 0.24), (16, 0.20), (48, 0.16)):
        acc += cv2.GaussianBlur(small, (0, 0), s) * wg
    return img + cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR) * amt * 0.5


def anamorphic(img, thr=2.0, amt=0.05):
    """subtle horizontal lens streak from very bright sources"""
    s = cv2.resize(np.maximum(img - thr, 0), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    s = cv2.blur(cv2.blur(s, (181, 1)), (121, 1)); s = cv2.GaussianBlur(s, (0, 0), sigmaX=1, sigmaY=1.2)
    return img + cv2.resize(s, (W, H)) * amt * np.array([0.55, 0.75, 1.0], f32)


def tonemap(img, expo=1.0):
    """filmic shoulder, per channel with slight desaturation of highlights; returns sRGB float 0..1"""
    x = np.maximum(img * expo, 0)
    lum = x @ np.array([0.2126, 0.7152, 0.0722], f32)
    k = np.clip((lum - 0.8) / 6.0, 0, 0.75)[..., None]
    x = x * (1 - k) + lum[..., None] * k
    y = 1 - np.exp(-x * 1.15)
    y = y * (1 + 0.12 * y * (1 - y) * 4 * 0.0)
    return np.power(y, 1 / 2.2, dtype=f32)


_fonts = {}
def font(sz, wt="Light", display=False):
    k = (sz, wt, display)
    if k not in _fonts:
        fam = "InterDisplay" if display else "Inter"
        _fonts[k] = ImageFont.truetype(f"/usr/share/fonts/opentype/inter/{fam}-{wt}.otf", sz)
    return _fonts[k]


def text_w(s, f, track=0.0):
    return sum(f.getlength(ch) for ch in s) + track * f.size * max(0, len(s) - 1)


class _Overlay:
    """text / thin-line overlay drawn with PIL at 2x and composited (sRGB space) with per-item alpha"""
    def __init__(s, h=None, yoff=0):
        s.h = H if h is None else h; s.yoff = yoff
        s.im = Image.new("RGBA", (W * 2, s.h * 2), (0, 0, 0, 0)); s.d = ImageDraw.Draw(s.im); s.used = False
    def text(s, x, y, txt, size=30, wt="Light", col=(235, 240, 248), a=1.0, track=0.22, anchor="l", display=False, shadow=True):
        if a <= 0.003 or not txt: return 0
        s.used = True
        f = font(int(size * 2), wt, display); tw = text_w(txt, f, track)
        x0 = x * 2 - (tw / 2 if anchor == "m" else tw if anchor == "r" else 0); y0 = (y - s.yoff) * 2
        if shadow:
            sh = Image.new("RGBA", s.im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh); xx = x0
            for ch in txt:
                ds.text((xx, y0), ch, font=f, fill=(0, 0, 0, int(215 * a))); xx += f.getlength(ch) + track * f.size
            bb = (max(0, int(x0 - 40)), max(0, int(y0 - 40)), min(W * 2, int(x0 + tw + 40)), min(s.h * 2, int(y0 + f.size * 1.4 + 40)))
            if bb[2] > bb[0] and bb[3] > bb[1]:
                from PIL import ImageFilter
                reg = sh.crop(bb).filter(ImageFilter.GaussianBlur(9)); s.im.alpha_composite(reg, (bb[0], bb[1]))
        lay = Image.new("RGBA", (int(tw + 8), int(f.size * 1.5)), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay); xx = 2
        for ch in txt:
            dl.text((xx, 0), ch, font=f, fill=(*col, int(255 * min(1, a)))); xx += f.getlength(ch) + track * f.size
        s.im.alpha_composite(lay, (max(0, int(x0 - 2)), max(0, int(y0))))
        return tw / 2
    def line(s, pts, col=(235, 240, 248), a=1.0, width=1.5, dash=None):
        if a <= 0.003: return
        s.used = True; c = (*col, int(255 * min(1, a))); w = max(1, int(round(width * 2)))
        pts = [(p[0] * 2, p[1] * 2) for p in pts]
        if dash is None: s.d.line(pts, fill=c, width=w, joint="curve"); return
        on, off = dash; acc = 0.0; draw = True; seg = [pts[0]]
        for p, q in zip(pts, pts[1:]):
            L = math.hypot(q[0] - p[0], q[1] - p[1]); pos = 0.0
            while pos < L:
                lim = (on if draw else off) * 2 - acc; step = min(lim, L - pos); pos += step; acc += step
                pt = (p[0] + (q[0] - p[0]) * pos / L, p[1] + (q[1] - p[1]) * pos / L)
                if draw: seg.append(pt)
                if acc >= (on if draw else off) * 2 - 1e-6:
                    if draw and len(seg) > 1: s.d.line(seg, fill=c, width=w)
                    draw = not draw; acc = 0.0; seg = [pt]
        if draw and len(seg) > 1: s.d.line(seg, fill=c, width=w)
    def circle(s, x, y, r, col=(235, 240, 248), a=1.0, width=1.5, fill=None):
        if a <= 0.003: return
        s.used = True
        s.d.ellipse((2 * (x - r), 2 * (y - r), 2 * (x + r), 2 * (y + r)), outline=(*col, int(255 * a)), width=max(1, int(width * 2)), fill=fill)
    def apply(s, srgb):
        if not s.used: return srgb
        o = np.asarray(s.im.resize((W, H), Image.LANCZOS), f32) / 255
        a = o[..., 3:4]
        return srgb * (1 - a) + o[..., :3] * a



class Overlay:
    """records draw calls; identical consecutive frames reuse the rendered layer (text is static most of the time)"""
    _key = None; _lay = None
    def __init__(s): s.ops = []; s.dyn = []          # dyn: fast-changing text (the clock), drawn in its own small strip
    def text(s, x, y, txt, size=30, wt="Light", col=(235, 240, 248), a=1.0, track=0.22, anchor="l", display=False, shadow=True, dyn=False):
        if a <= 0.003 or not txt: return 0
        (s.dyn if dyn else s.ops).append(("text", round(x, 1), round(y, 1), txt, size, wt, tuple(col), round(a, 3), track, anchor, display, shadow)); return 0
    def line(s, pts, col=(235, 240, 248), a=1.0, width=1.5, dash=None):
        if a > 0.003: s.ops.append(("line", tuple((round(p[0], 1), round(p[1], 1)) for p in pts), tuple(col), round(a, 3), width, dash))
    def circle(s, x, y, r, col=(235, 240, 248), a=1.0, width=1.5, fill=None):
        if a > 0.003: s.ops.append(("circle", round(x, 1), round(y, 1), r, tuple(col), round(a, 3), width, fill))
    _dkey = None; _dlay = None
    def apply(s, srgb):
        if s.ops:
            key = tuple(s.ops)
            if key != Overlay._key:
                o = _Overlay()
                for op in s.ops:
                    if op[0] == "text": o.text(*op[1:])
                    elif op[0] == "line": o.line(list(op[1]), *op[2:])
                    else: o.circle(*op[1:])
                Overlay._lay = np.asarray(o.im.resize((W, H), Image.LANCZOS), f32) / 255; Overlay._key = key
            o = Overlay._lay; a = o[..., 3:4]
            srgb = srgb * (1 - a) + o[..., :3] * a
        if s.dyn:
            y0 = max(0, int(min(op[2] for op in s.dyn)) - 30); hh = min(H - y0, 150); key = tuple(s.dyn)
            if key != Overlay._dkey:
                o = _Overlay(h=hh, yoff=y0)
                for op in s.dyn: o.text(*op[1:])
                Overlay._dlay = np.asarray(o.im.resize((W, hh), Image.LANCZOS), f32) / 255; Overlay._dkey = key
            o = Overlay._dlay; a = o[..., 3:4]
            srgb[y0:y0 + hh] = srgb[y0:y0 + hh] * (1 - a) + o[..., :3] * a
        return srgb


# ------------------------------------------------------------------------------------------------ plates
import json
def _png(path):
    a = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    assert a is not None, path
    a = a.astype(f32) / (65535.0 if a.dtype == np.uint16 else 255.0)
    return np.concatenate([a[..., 2::-1], a[..., 3:]], -1)

class Plate:
    """one world's Blender passes, cropped for the current aspect ratio and resized to the output frame"""
    def __init__(s, world, pdir=None):
        pdir = pdir or os.environ.get("PLATES", os.path.join(SCR, "plates")); s.world = world
        m = json.load(open(os.path.join(pdir, f"{world}_meta.json"))); s.camh, s.dmax = m["camh"], m["dmax"]; s.meta = m
        P = {k: _png(os.path.join(pdir, f"{world}_{k}.png")) for k in ("beauty", "albedo", "normal", "depth")}
        R = P["beauty"].shape[0]; cw = R * 9 / 16
        if VERT: x0, x1, y0, y1 = (R - cw) / 2, (R + cw) / 2, 0, R
        else: y0 = HORIZ * R - HY * cw; x0, x1, y1 = 0, R, y0 + cw
        x0, x1, y0, y1 = int(round(x0)), int(round(x1)), int(round(y0)), int(round(y1))
        def crop(a): return cv2.resize(a[y0:y1, x0:x1], (W, H), interpolation=cv2.INTER_AREA)
        b = crop(P["beauty"]); s.alpha = b[..., 3:4].copy(); s.sun, s.glow, s.amb = b[..., 0], b[..., 1], b[..., 2]
        s.alb = crop(P["albedo"])[..., :3]; n = crop(P["normal"])[..., :3] * 2 - 1; s.nrm = n / np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-4)
        d = crop(P["depth"]); s.dist = s.camh * (np.exp(d[..., 0] * math.log(1 + s.dmax / s.camh)) - 1); s.flag = d[..., 1]
        s.f = (R / 2) / math.tan(math.radians(FOV / 2)) * (W / (x1 - x0)); s.yh = HY * H; s.cx = W / 2
        s.ppd = s.f * math.radians(1.0)
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        s.AZ = np.degrees(np.arctan((xx - s.cx) / s.f)); s.EL = np.degrees(np.arctan((s.yh - yy) / s.f * np.cos(np.radians(s.AZ))))
        s.xx, s.yy = xx, yy
    def xy(s, el, az):
        """pixel position of a sky direction (degrees)"""
        x = s.cx + s.f * math.tan(math.radians(az)); y = s.yh - s.f * math.tan(math.radians(el)) / math.cos(math.radians(az)); return x, y

def half(a): return cv2.resize(a, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
def up(a): return cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
def C(*c): return np.array(c, f32)

def sun_disc(img, x, y, r, col, limb=0.55, squash=1.0, tint_bottom=None):
    """add a limb-darkened disc (HDR colour). Sub-pixel suns become a small Gaussian of the same total energy."""
    if r < 1.6:
        s = 0.9; e = (r / s) ** 2 / 2.0; R = 6
    else: R = int(r + 3)
    x0, x1, y0, y1 = int(x) - R, int(x) + R + 1, int(y) - R, int(y) + R + 1
    X0, X1, Y0, Y1 = max(x0, 0), min(x1, W), max(y0, 0), min(y1, H)
    if X0 >= X1 or Y0 >= Y1: return
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(f32); dx = xx - x; dy = (yy - y) / squash; d = np.sqrt(dx * dx + dy * dy)
    if r < 1.6: img[Y0:Y1, X0:X1] += (np.exp(-d * d / (2 * s * s)) * e)[..., None] * col; return
    a = np.clip(r - d + 0.5, 0, 1); mu = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1)); I = (1 - limb * (1 - mu))
    c = np.asarray(col, f32)[None, None, :] * I[..., None]
    if tint_bottom is not None:
        k = np.clip((dy / r + 1) / 2, 0, 1)[..., None]; c = c * (1 - k + k * np.asarray(tint_bottom, f32))
    img[Y0:Y1, X0:X1] = img[Y0:Y1, X0:X1] * (1 - a[..., None]) + c * a[..., None]

_tiles = {}
def tile(seed, beta=1.7, n=1024, lo=0.0, hi=0.0):
    k = (seed, beta, n, lo, hi)
    if k not in _tiles:
        r = np.random.default_rng(seed); fy = np.fft.fftfreq(n)[:, None] * n; fx = np.fft.rfftfreq(n)[None, :] * n
        f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1; amp = f ** (-beta); amp[0, 0] = 0
        if lo: amp[f < lo] = 0
        if hi: amp *= np.exp(-(f / hi) ** 4)
        z = np.fft.irfft2(amp * np.exp(1j * r.uniform(0, 2 * np.pi, amp.shape)), s=(n, n)); _tiles[k] = ((z - z.mean()) / z.std()).astype(f32)
    return _tiles[k]
_gt = {}
def _grad_tile(seed):
    if seed not in _gt:
        Tn = tile(seed, 1.3, lo=4, hi=36); gy, gx = np.gradient(Tn); _gt[seed] = ((gx / gx.std()).astype(f32), (gy / gy.std()).astype(f32))
    return _gt[seed]
def tsample(T, u, v):
    """periodic bilinear lookup; u, v in tile units"""
    n = T.shape[0]; return cv2.remap(T, ((u % 1.0) * n).astype(f32), ((v % 1.0) * n).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

def cloud_layer(EL, AZ, seed, lx, ly, du=0.0, dv=0.0, beta=1.6, elmin=0.25):
    """noise on a horizontal layer overhead seen in perspective (distance ~ 1/tan(el)): streaks that pile up towards the horizon"""
    d = 1.0 / np.tan(np.radians(np.maximum(EL, elmin))); x = d * np.tan(np.radians(AZ))
    return tsample(tile(seed, beta), x / lx + du, d / ly + dv)

_stars = {}
def stars(seed=5, n=2600, mw=True):
    k = (seed, n, W, H)
    if k not in _stars:
        r = np.random.default_rng(seed); img = np.zeros((H, W, 3), f32)
        xs = r.uniform(0, W, n); ys = r.uniform(0, H, n); fl = 0.02 * (1 - r.random(n)) ** (-1 / 1.1); fl = np.minimum(fl, 9)
        T = r.uniform(3200, 11000, n)
        for x, y, f_, t in zip(xs, ys, fl, T):
            c = bbcolor(t) * f_; xi, yi = int(x), int(y)
            if 1 <= xi < W - 2 and 1 <= yi < H - 2:
                fx, fy = x - xi, y - yi
                for dy, wy in ((0, 1 - fy), (1, fy)):
                    for dx, wx in ((0, 1 - fx), (1, fx)): img[yi + dy, xi + dx] += c * wx * wy
        img = img + cv2.GaussianBlur(img, (0, 0), 1.2) * 0.6
        if mw:
            yy, xx = np.mgrid[0:H, 0:W].astype(f32); u = (xx * 0.5 + yy * 0.86) / max(W, H); band = np.exp(-((u - 0.55) / 0.16) ** 2)
            cl = np.clip(0.6 + 0.5 * cv2.resize(tile(seed + 1, 1.5), (W, H)), 0, 2) * np.clip(1 + 0.6 * cv2.resize(tile(seed + 2, 1.2), (W, H)), 0.1, 2)
            img += (band * cl)[..., None] * C(0.020, 0.021, 0.026)
        _stars[k] = img
    return _stars[k]

def bbcolor(T):
    t = T / 100.0
    r = 255 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    c = np.clip(np.array([r, g, b]) / 255.0, 0, 1) ** 2.2
    return (c / c.max()).astype(f32)

# ------------------------------------------------------------------------------------------------ analytic sea
def sea(pl, skyfn, t, sunL, sun_el, sun_az, sun_r_deg, deep=C(0.004, 0.012, 0.02), amp=1.0, wind=1.0, chop=1.0, speed=1.0, refl_alpha=None, sparkle=1.0):
    """flat sea / lake seen from height pl.camh: three bands of travelling waves, Fresnel reflection of the sky function, sun glitter
    with the correct energy (unresolved waves widen the glitter path), reflections of the rocks. Returns RGB for the whole frame."""
    el = np.minimum(pl.EL, -0.012).astype(np.float64); az = pl.AZ.astype(np.float64); ta = np.tan(np.radians(-el)); y = pl.camh / ta; x = y * np.tan(np.radians(az))
    foot = pl.camh / (np.sin(np.radians(-el)) ** 2 * pl.f)                      # metres of water per pixel row
    sx = np.zeros(y.shape, f32); sy = np.zeros(y.shape, f32); var = np.zeros(y.shape, f32) + (0.02 * chop) ** 2
    for k, (L, a, vx, vy, st) in enumerate(((140.0, 0.045, 0.3, -2.2, 0.3), (23.0, 0.07, -0.25, -1.1, 0.45), (4.1, 0.085, 0.15, -0.5, 0.7), (0.7, 0.085, 0.05, -0.22, 1.0))):
        gx, gy = _grad_tile(300 + k)
        u = x * st / L + vx * t * speed / L; v = y / L + vy * t * speed / L
        wres = smooth(0.5, 1.6, L / 80.0 / np.maximum(foot, 1e-4)).astype(f32)   # 1 where the band is resolved by the pixel grid
        a_ = a * amp * (wind if k >= 2 else 1.0)
        sx += tsample(gx, u, v) * a_ * st * wres; sy += tsample(gy, u, v) * a_ * wres; var += (a_ ** 2) * (1 - wres ** 2)
    el = el.astype(f32); az = az.astype(f32)
    n = np.stack([-sx, -sy, np.ones_like(sx)], -1); n /= np.linalg.norm(n, axis=2, keepdims=True)
    ce = np.cos(np.radians(el)); v = np.stack([np.sin(np.radians(az)) * ce, np.cos(np.radians(az)) * ce, np.sin(np.radians(el))], -1)
    vn = (v * n).sum(-1, keepdims=True); r = v - 2 * vn * n
    rz = np.clip(r[..., 2], 0.002, 1); rel = np.degrees(np.arcsin(rz)); raz = np.degrees(np.arctan2(r[..., 0], r[..., 1]))
    F = 0.02 + 0.98 * (1 - np.clip(-vn[..., 0], 0, 1)) ** 5
    sig = np.sqrt(var)
    blur_el = rel + np.degrees(sig) * 0.8                                         # rough water reflects sky from slightly higher up
    refl = skyfn(blur_el, raz)
    if refl_alpha is not None:                                                    # rocks mirrored about the horizon, smeared by the waves
        my = (2 * pl.yh - pl.yy - sy * pl.f * 1.2).astype(f32); mx = (pl.xx + sx * pl.f * 1.2).astype(f32)
        ra = cv2.remap(refl_alpha, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        refl = refl * (1 - 0.92 * ra[..., None])
    else: ra = 0
    # sun glitter (Cox-Munk style): probability that a facet has the slope that mirrors the Sun into the lens
    se, sa = math.radians(sun_el), math.radians(sun_az); S = np.array([math.sin(sa) * math.cos(se), math.cos(sa) * math.cos(se), math.sin(se)], f32)
    hvec = S[None, None, :] - v; hvec /= np.linalg.norm(hvec, axis=2, keepdims=True); hz = np.maximum(hvec[..., 2], 0.05)
    zx = -hvec[..., 0] / hz; zy = -hvec[..., 1] / hz; rs = math.radians(sun_r_deg)
    s2 = var + (rs / 2) ** 2 + 2e-5
    p = np.exp(-((zx - sx) ** 2 + (zy - sy) ** 2) / (2 * s2)) / (2 * math.pi * s2)
    glit = p * (math.pi * rs * rs) / (4 * np.maximum(-v[..., 2], 0.004) * hz ** 4)
    Fh = 0.02 + 0.98 * (1 - np.clip((hvec * S).sum(-1), 0, 1)) ** 5
    spk = tsample(tile(390, 0.35), pl.xx / 700.0 + 0.371 * t * 3, pl.yy / 260.0 + 0.613 * t * 3)          # unresolved facets: sparkle
    glit = np.minimum(glit * Fh * np.exp(1.5 * spk - 0.9) * sparkle + glit * Fh * (1 - sparkle), 0.03) / np.maximum(F, 1e-3)
    out = deep[None, None, :] * (1 - F[..., None]) + refl * F[..., None] + (glit * F * (1 - ra))[..., None] * np.asarray(sunL, f32)
    return out

# ------------------------------------------------------------------------------------------------ Saturn's rings from the cloud tops
def ring_profile(r):
    """optical depth-ish brightness of the main rings vs radius in Saturn radii (D, C, B, Cassini division, A with Encke gap, F)"""
    t = np.zeros_like(r)
    def band(a, b, v, e=0.006): return v * smooth(a - e, a + e, r) * (1 - smooth(b - e, b + e, r))
    t += band(1.239, 1.526, 0.16) + band(1.526, 1.950, 1.0) + band(1.950, 2.025, 0.10) + band(2.025, 2.269, 0.62) + band(2.320, 2.332, 0.25, 0.003)
    t *= 1 - 0.9 * band(2.212, 2.219, 1.0, 0.002)
    n = tile(77, 1.1, lo=3, hi=60)[0]; fine = np.interp((r * 2.0) % 1.0, np.linspace(0, 1, 1024), n); n2 = tile(78, 0.8, lo=20, hi=120)[0]; fine2 = np.interp((r * 3.0) % 1.0, np.linspace(0, 1, 1024), n2)
    return np.clip(t * (1 + 0.30 * fine + 0.10 * fine2), 0, 1.6), fine

def rings(EL, AZ, lat, sun_dec, view_az_offset=0.0):
    """rings seen from latitude `lat` (deg, north) at the cloud tops, for a view centred `view_az_offset` degrees from the point
    where the Sun sets. Returns (brightness rgb, alpha)."""
    ph = math.radians(lat); dl = math.radians(sun_dec)
    A0 = 2 * math.pi - math.acos(min(1.0, math.sin(dl) / math.cos(ph))) + math.radians(view_az_offset)       # azimuth from north through east
    A = A0 + np.radians(AZ); e = np.radians(EL); ce = np.cos(e)
    dE, dN, dU = ce * np.sin(A), ce * np.cos(A), np.sin(e)
    Dx = -math.sin(ph) * dN + math.cos(ph) * dU; Dy = dE; Dz = math.cos(ph) * dN + math.sin(ph) * dU
    Px, Pz = math.cos(ph), math.sin(ph)
    s_ = np.where(Dz < -1e-5, -Pz / np.minimum(Dz, -1e-5), -1.0)
    hx = Px + s_ * Dx; hy = s_ * Dy; r = np.hypot(hx, hy)
    tau, fine = ring_profile(r.astype(f32)); tau = np.where(s_ > 0, tau, 0)
    slant = np.clip(0.25 / np.maximum(-Dz, 0.02), 1, 9)                           # grazing sight lines look through more ring
    alpha = 1 - np.exp(-tau * 1.1 * slant)
    # Saturn's shadow on the rings (anti-sunward side)
    As = 2 * math.pi - math.acos(min(1.0, math.sin(dl) / math.cos(ph)))
    sE, sN = math.sin(As), math.cos(As); Sx = -math.sin(ph) * sN; Sy = sE; Sz = math.cos(ph) * sN
    along = hx * Sx + hy * Sy; perp2 = hx * hx + hy * hy - along * along
    lit = 1 - (along < 0) * (perp2 < 1.0)
    col = np.stack([0.98 + 0.02 * fine, 0.90 + 0.04 * fine, 0.74 + 0.08 * fine], -1).astype(f32)
    col = col * (0.55 + 0.45 * np.clip(tau, 0, 1))[..., None]
    return col * lit[..., None], alpha.astype(f32)
