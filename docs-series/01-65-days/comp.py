"""
65 DAYS — numpy/PIL compositor. Builds every frame of the film from:
  * the exact radial free-fall solution (physics/fall.py) via the locked timeline (timeline.py),
  * Blender plates: land_near / land_far silhouettes, orbit Earth still, moon-shot Earth/Moon stills, dive frames,
  * pre-baked textures (granulation tiles, sun low-frequency map).
Each shot is encoded to its own silent segment (x264 CRF 14), no grain (grain + vignette are added at final assembly).

Usage: python3 comp.py SHOT [--frames a,b,c --png DIR]      (system python3: numpy + PIL)
"""
import os, sys, math, functools, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "physics"))
import timeline as TL
import fall as FL

W, H = 1920, 1080
FPS = TL.FPS
SCR = TL.SCR
FR = SCR + "/frames"
TEX = SCR + "/tex"
SEG = SCR + "/segments"
FONT_L = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
FONT_XL = "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf"
TEXT_COL = (236, 232, 226)
HOT = (255, 196, 140)

# landscape camera (must match blender/shots.py)
F_PX = 960 / math.tan(math.radians(20.0))
HOR_Y = 713
SUN_AZ = math.degrees(math.atan((1190 - 960) / F_PX))   # Sun centre azimuth (screen x = 1190)

def F32(v): return np.array(v, np.float32)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def smooth(a): a = clamp(a); return a * a * (3 - 2 * a)
def lerp(a, b, t): return a + (b - a) * t
def window(t, a, b, fi=0.6, fo=0.6): return smooth((t - a) / fi) * (1 - smooth((t - (b - fo)) / fo))

def state(sim):
    s = FL.state(np.array([max(0.0, min(sim, TL.T_IMPACT_D)) * 86400.0]))
    return {k: float(v[0]) for k, v in s.items()}

# ---------------------------------------------------------------- text
@functools.lru_cache(maxsize=512)
def font(path, size): return ImageFont.truetype(path, size)

@functools.lru_cache(maxsize=2048)
def text_img(s, size, track=0.18, thin=False, col=TEXT_COL):
    f = font(FONT_XL if thin else FONT_L, size)
    widths = [f.getlength(c) for c in s]
    sp = size * track
    tw = int(sum(widths) + sp * max(0, len(s) - 1)) + 8
    asc, desc = f.getmetrics()
    im = Image.new("L", (tw, asc + desc + 8), 0)
    d = ImageDraw.Draw(im)
    x = 4
    for c, w in zip(s, widths):
        d.text((x, 4), c, font=f, fill=255); x += w + sp
    rgba = Image.new("RGBA", im.size, col + (0,)); rgba.putalpha(im)
    return rgba

def put_text(base, s, size, x, y, alpha=1.0, anchor="l", track=0.18, thin=False, col=TEXT_COL, shadow=True):
    if alpha <= 0.003: return
    im = text_img(s, size, track, thin, col)
    if anchor == "c": x = x - im.width // 2
    elif anchor == "r": x = x - im.width
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.55 * alpha)))
        sh = sh.filter(ImageFilter.GaussianBlur(3))
        base.alpha_composite(sh, (int(x) + 1, int(y) + 2))
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(im, (int(x), int(y)))

def caption(base, s, alpha, y=930, size=30, sub=None):
    """Lower-third key-number caption, thin + wide tracking."""
    put_text(base, s, size, W // 2, y, alpha, "c", 0.28)
    if sub: put_text(base, sub, 19, W // 2, y + size + 16, alpha * 0.8, "c", 0.30)

def fmt_int(v): return f"{int(round(v)):,}"

# ---------------------------------------------------------------- shared geometry (landscape)
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
DX = (XX - 960) / F_PX; DZ = (HOR_Y - YY) / F_PX
NRM = np.sqrt(DX * DX + 1 + DZ * DZ)
DIRX, DIRY, DIRZ = DX / NRM, 1 / NRM, DZ / NRM
EL = np.degrees(np.arcsin(DIRZ))                    # elevation of each pixel's ray
AZ = np.degrees(np.arctan(DX))

def load_rgba(p):
    a = np.asarray(Image.open(p).convert("RGBA")).astype(np.float32) / 255.0
    return a

@functools.lru_cache(maxsize=1)
def land_layers():
    near = load_rgba(FR + "/land_near/f_0001.png")[..., 3]
    far = load_rgba(FR + "/land_far/f_0001.png")[..., 3]
    return near, far

@functools.lru_cache(maxsize=1)
def gran_mips():
    out = []
    for k in "ab":
        g = np.load(f"{TEX}/gran_{k}.npy").astype(np.float32)
        lv = [g]
        while lv[-1].shape[0] > 64:
            a = lv[-1]; lv.append(0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]))
        out.append(lv)
    return out

@functools.lru_cache(maxsize=1)
def sunlow(): return np.load(f"{TEX}/sunlow.npy")

def bilinear_wrap(img, u, v):
    n, m = img.shape
    u = u % m; v = v % n
    xf = np.floor(u); yf = np.floor(v)
    fx = u - xf; fy = v - yf
    x0 = xf.astype(np.int32) % m; y0 = yf.astype(np.int32) % n
    x1 = (x0 + 1) % m; y1 = (y0 + 1) % n
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)

def bilinear_clamp(img, u, v):
    n, m = img.shape
    u = np.clip(u, 0, m - 1.001); v = np.clip(v, 0, n - 1.001)
    x0 = u.astype(np.int32); y0 = v.astype(np.int32); fx = u - x0; fy = v - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)

def granulation(u, v, gpx, t):
    """u,v: disk coords in units of R; gpx: screen pixels per granule. Returns modulation (mean 1)."""
    res = np.ones_like(u)
    if gpx < 0.6: return res
    mips = gran_mips()
    w = smooth((gpx - 0.6) / 1.6)
    acc = 0
    for i, (cells, rot) in enumerate(((160, 0.0), (136, 0.9))):
        lv = mips[i]
        # tile px per granule at level 0 = 2048/cells; screen step (tile px per screen px) = (2048/cells)/gpx
        step = (2048.0 / cells) / max(gpx, 1e-3)
        L = int(clamp(math.floor(math.log2(max(step, 1.0))), 0, len(lv) - 1))
        sc = 2048.0 / (2 ** L) / cells * 696.0       # tile px per R at level L
        cr, sr = math.cos(rot), math.sin(rot)
        uu = (u * cr - v * sr) * sc + 37.0 * i + t * 0.02
        vv = (u * sr + v * cr) * sc + 11.0 * i
        acc = acc + bilinear_wrap(lv[L], uu, vv)
    g = acc / 2.0
    g = g ** 1.6; g = g / max(1e-6, float(g.mean()))
    return 1 + w * (g - 1)

@functools.lru_cache(maxsize=1)
def sea_tex(n=1024, seed=3):
    r = np.random.default_rng(seed)
    w = r.standard_normal((n, n)).astype(np.float32)
    F = np.fft.rfft2(w)
    ky = np.fft.fftfreq(n)[:, None] * n; kx = np.fft.rfftfreq(n)[None, :] * n
    k = np.sqrt((kx * 5.0) ** 2 + (ky * 0.8) ** 2) + 1e-3       # features elongated horizontally
    f = np.fft.irfft2(F * np.exp(-(np.log(k / 90.0)) ** 2 / 0.5), s=(n, n)).astype(np.float32)
    f = (f - f.mean()) / f.std()
    return f

def sea_glints(t, dep):
    """Short horizontal sparkles on the swell, perspective-compressed toward the horizon."""
    tex = sea_tex()
    rows = dep.shape[0]
    z = 1.0 / np.tan(np.radians(dep[:, 960:961] + 0.02))          # distance-like per row
    xs = (np.arange(W, dtype=np.float32)[None, :] - 960) / F_PX
    u = xs * z * 22.0 + t * 3.0
    v = np.log(z) * 210.0 + t * 7.0 + np.zeros_like(u)
    a = bilinear_wrap(tex, u, v)
    b = bilinear_wrap(tex, u * 1.7 + 300, v * 1.3 - t * 11.0)
    g = np.clip(0.55 * a + 0.45 * b - 0.9, 0, None) ** 2 * 1.6
    far = np.clip(dep[:, :] / 0.35, 0, 1)                         # fade to average sheen at the horizon
    return g * far + (1 - far) * 0.35

# ---------------------------------------------------------------- landscape frame
def sky_colors(heat):
    Z = F32(lerp_v((0.030, 0.075, 0.24), (0.40, 0.36, 0.30), heat ** 0.8))
    Hc = F32(lerp_v((1.05, 0.50, 0.20), (1.30, 0.98, 0.66), heat))
    return Z, Hc

def lerp_v(a, b, t): return tuple(lerp(x, y, t) for x, y in zip(a, b))

@functools.lru_cache(maxsize=8)
def gamma_map(sx, sy, sz):
    cosg = np.clip(DIRX * sx + DIRY * sy + DIRZ * sz, -1, 1)
    return np.degrees(np.arccos(cosg)).astype(np.float32)

def land_frame(t, sim, sun_el=6.0, blink=0.0):
    st = state(sim)
    x = st["x"]; flux = 1.0 / (x * x)
    alpha = math.asin(min(1.0, 6.957e8 / (x * 1.495978707e11)))     # angular radius (rad)
    a_deg = math.degrees(alpha)
    heat = smooth(math.log(flux) / math.log(60.0)) if flux > 1 else 0.0
    late = smooth((a_deg - 2.0) / 10.0)                               # disk becomes "filtered" & textured
    # Sun centre elevation: rises a little as the disk swells so we keep seeing it
    e_c = sun_el + 0.35 * max(0.0, a_deg - 6.0)
    sx = math.cos(math.radians(e_c)) * math.sin(math.radians(SUN_AZ))
    sy = math.cos(math.radians(e_c)) * math.cos(math.radians(SUN_AZ))
    sz = math.sin(math.radians(e_c))
    gam = gamma_map(round(sx, 6), round(sy, 6), round(sz, 6))         # angle from Sun centre (deg), cached
    Z, Hc = sky_colors(heat)
    el = np.maximum(EL[:, 960], 0.0)
    wv = np.exp(-el / lerp(6.0, 16.0, heat))[:, None, None]
    sky = np.broadcast_to(Z * (1 - wv) + Hc * wv, (H, W, 3))
    # aureole / glow around the Sun, grows with flux & size
    sun_col = F32(lerp_v((1.0, 0.80, 0.55), (1.0, 0.86, 0.66), heat))
    g_rel = np.maximum(gam[::2, ::2] - a_deg, 0.0)
    glow = (0.55 * np.exp(-g_rel / (1.2 + 0.25 * a_deg)) + 0.22 * np.exp(-g_rel / (7.0 + 0.8 * a_deg))) * (flux ** 0.35)
    glow *= (1 - 0.6 * late)
    boost = 1 + 0.6 * heat * np.exp(-g_rel / 30.0)
    glow = np.repeat(np.repeat(glow, 2, 0), 2, 1); boost = np.repeat(np.repeat(boost, 2, 0), 2, 1)
    sky = sky * boost[..., None] + glow[..., None] * sun_col
    img = sky.astype(np.float32)
    # sea below the horizon
    sea_rows = slice(HOR_Y, H)
    dep = np.maximum(-EL[sea_rows], 1e-3)
    fres = 0.18 + 0.55 * np.exp(-dep / 1.2)
    sea = (Hc * 0.55 + Z * 0.45)[None, None, :] * fres[..., None] * lerp(1.0, 1.25, heat)
    # glitter path: wave texture compressed toward the horizon
    wave = sea_glints(t, dep)
    daz = AZ[sea_rows] - SUN_AZ
    pw = 0.8 + 0.8 * a_deg + 2.5 * heat
    path = np.exp(-(daz / pw) ** 2) * np.exp(-dep / (6.0 + 2 * a_deg))
    sea += (path * wave * (2.2 + 0.6 * flux ** 0.5))[..., None] * sun_col * (1 - 0.5 * late)
    sea += (np.exp(-(daz / (pw * 2.5)) ** 2) * np.exp(-dep / 3.0) * 0.25 * flux ** 0.3)[..., None] * sun_col
    img[sea_rows] = sea
    # Sun disk (exact sphere: mu = sqrt(1 - (sin g / sin a)^2))
    a_px = math.tan(alpha) * F_PX
    cx = 960 + F_PX * math.tan(math.radians(SUN_AZ)); cy = HOR_Y - F_PX * math.tan(math.radians(e_c)) / math.cos(math.radians(SUN_AZ))
    pad = 3
    if a_deg < 70:
        x0 = int(max(0, cx - a_px * 1.25 - pad)); x1 = int(min(W, cx + a_px * 1.25 + pad))
        y0 = int(max(0, cy - a_px * 1.25 - pad)); y1 = int(min(H, cy + a_px * 1.25 + pad))
    else:
        x0, x1, y0, y1 = 0, W, 0, H
    if x1 > x0 and y1 > y0:
        gb = np.radians(gam[y0:y1, x0:x1])
        rr = np.sin(gb) / math.sin(alpha)                       # 0 centre .. 1 limb (projected radius / R)
        inside = rr < 1.0
        # anti-aliased edge (in pixels)
        edge_px = (1.0 - rr) * a_px
        cov = np.clip(edge_px + 0.5, 0, 1) * (gb < math.pi / 2)
        mu = np.sqrt(np.clip(1 - rr * rr, 0, 1))
        limb = 1 - 0.62 * (1 - mu) - 0.12 * (1 - mu) ** 2
        # surface coords on the visible hemisphere (orthographic disk coords, units of R)
        ang = np.arctan2(-(YY[y0:y1, x0:x1] - cy), XX[y0:y1, x0:x1] - cx)
        rR = 1.0 / math.sin(alpha)                               # r / R
        rho = (rR * np.cos(gb) - np.sqrt(np.clip(1 - (rR * np.sin(gb)) ** 2, 0, 1))) * np.sin(gb)
        rho = np.where(inside, rho, rr)                          # true hit-point offset from the axis (units of R)
        u = rho * np.cos(ang); v = rho * np.sin(ang)
        lowm = bilinear_clamp(sunlow(), (u * 0.5 + 0.5) * 1023, (0.5 - v * 0.5) * 1023)
        lowm = 1 + (lowm - 1) * smooth((a_px - 60) / 300)
        gpx = F_PX / 696.0 / max(rR - 1.0, 1e-3)               # px per ~1000 km granule at the disk centre
        gran = granulation(u, v, gpx, t)
        gran = 1 + (gran - 1) * lerp(1.0, 1.5, late)
        I = limb * lowm * gran
        bright = lerp(40.0, 1.4, late)
        col_hot = F32((1.0, 0.95, 0.88)); col_filt = F32((1.0, 0.33, 0.035))
        # filtered look: colour ramp from deep orange lanes to yellow-white centres
        Ic = I[..., None]
        filt = col_filt * Ic + F32((0.0, 0.42, 0.30)) * np.clip(Ic - 0.85, 0, None) ** 1.3
        disk = col_hot * Ic * bright * (1 - late) + filt * bright * late
        reg = img[y0:y1, x0:x1]
        c3 = cov[..., None]
        # chromosphere rim / corona hint just outside the limb (late)
        rim = np.exp(-np.clip(rr - 1, 0, None) * a_px / (3 + 0.01 * a_px)) * (rr >= 1) * late
        reg = reg * (1 - c3) + disk * c3 + (rim[..., None] * F32((1.0, 0.35, 0.12)) * 1.2)
        img[y0:y1, x0:x1] = reg
    # steam / haze over the sea and lower sky (rough visual: oceans steaming, never boiling away)
    steam = smooth((flux - 2.0) / 12.0) * (1 - late)
    if steam > 0:
        r0, r1 = 430, 790
        E = EL[r0:r1]; X_ = XX[r0:r1]; Y_ = YY[r0:r1]
        band = np.exp(-np.maximum(E, 0) / 2.5) * np.clip((E + 1.5) / 1.0, 0, 1)
        nz = 0.5 + 0.5 * np.sin(X_ * 0.011 + t * 0.35 + np.sin(Y_ * 0.03 - t * 0.9) * 1.7) * np.sin(X_ * 0.004 - t * 0.21 + Y_ * 0.012)
        hz = (band * nz * steam * 0.65)[..., None]
        img[r0:r1] = img[r0:r1] * (1 - hz) + hz * (Hc * 0.95 * (1 - late) + F32((1.0, 0.55, 0.22)) * late)
    # land: far headland in haze, near silhouette black (with a faint warm rim when the Sun is huge)
    near, far = land_layers()
    far_col = (Hc * 0.42 + Z * 0.2) * lerp(1.0, 1.4, heat) * (1 - late) + F32((0.05, 0.016, 0.004)) * late
    fa = far[..., None] * 0.96
    img = img * (1 - fa) + fa * far_col
    na = near[..., None]
    near_col = F32((0.0025, 0.0022, 0.0022)) + F32((0.03, 0.009, 0.003)) * late
    img = img * (1 - na) + na * near_col
    # heat shimmer around the horizon
    sh = smooth((flux - 1.6) / 6.0)
    if sh > 0:
        rows = np.arange(560, 860)
        off = (np.sin(rows * 0.21 + t * 9.0) * 1.2 + np.sin(rows * 0.07 - t * 5.0) * 0.8) * sh * 1.6
        off *= np.exp(-np.abs(rows - HOR_Y) / 80.0)
        for r_, o in zip(rows, off.astype(np.int32)):
            if o > 0: img[r_, o:] = img[r_, :-o].copy()
            elif o < 0: img[r_, :o] = img[r_, -o:].copy()
    # exposure: the eye/camera adapts as the Sun brightens (keeps the frame readable), blink = night between days
    expo = 1.05 / (1 + 0.55 * math.log(max(flux, 1.0))) * (1 - 0.85 * blink)
    expo = lerp(expo, 0.95, late)
    return img, expo, dict(st=st, flux=flux, a_deg=a_deg, a_px=a_px, cx=cx, cy=cy, heat=heat, late=late)

def box1(a, r, axis):
    if r < 1: return a
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge"), axis=axis)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)

def gblur(a, sigma):
    r = max(1, int(round(sigma * 0.85)))
    for _ in range(3):
        a = box1(box1(a, r, 0), r, 1)
    return a

def bloom(img, amt=0.35):
    h, w = img.shape[:2]
    small = img[: h // 4 * 4, : w // 4 * 4].reshape(h // 4, 4, w // 4, 4, 3).mean(axis=(1, 3))
    br = np.clip(small - 0.9, 0, 20)
    out = 0.6 * gblur(br, 3) + 0.5 * gblur(br, 14)
    up = np.repeat(np.repeat(out, 4, 0), 4, 1)
    res = img.copy(); res[: up.shape[0], : up.shape[1]] += amt * up
    return res

SCRIM_HUD = np.exp(-((XX - 60) / 760.0) ** 2 - ((YY - 170) / 360.0) ** 2).astype(np.float32)
SCRIM_CAP = np.exp(-((XX - 960) / 900.0) ** 2 - ((YY - 965) / 120.0) ** 2).astype(np.float32)
def scrim(out):
    """Darken behind the HUD / captions in proportion to how bright the scene is there (keeps thin text legible)."""
    l1 = float(out[60:420, 60:600].mean()) / 255.0
    l2 = float(out[900:1010, 400:1520].mean()) / 255.0
    k = 1 - 0.55 * smooth((l1 - 0.30) / 0.45) * SCRIM_HUD - 0.45 * smooth((l2 - 0.30) / 0.45) * SCRIM_CAP
    return (out.astype(np.float32) * k[..., None]).astype(np.uint8)

def tonemap(img, expo):
    x = np.clip(img.astype(np.float32) * np.float32(expo * 1.25), 0, None)
    y = np.sqrt(1 - np.exp(-x)) ** np.float32(2 / 2.2)
    return (np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8)

# ---------------------------------------------------------------- HUD
def hud(base, t, sim, info, a=1.0, compare=True, temp=True):
    st = info["st"] if "st" in info else state(sim)
    if sim < TL.T_IMPACT_D - 13.44 / 24 + 1e-6 and sim < 64.0:
        day = int(math.floor(max(sim, 0.0))) + 1
        put_text(base, f"DAY {day}", 66, 92, 64, a, "l", 0.20, thin=True)
    else:
        rem = max(0.0, (TL.T_IMPACT_D - sim) * 24.0)
        hh = int(rem); mm = int((rem - hh) * 60); ss = int(((rem - hh) * 60 - mm) * 60)
        lab = f"{hh:02d}:{mm:02d}:{ss:02d}"
        put_text(base, lab, 66, 92, 64, a, "l", 0.16, thin=True)
        put_text(base, "LEFT", 22, 98, 150, a * 0.85, "l", 0.35)
    y = 170 if sim < 64.0 else 196
    dist = st["r_km"] / 1e6
    rows = [("DISTANCE TO SUN", f"{dist:,.1f} MILLION KM" if dist >= 10 else f"{st['r_km']:,.0f} KM"),
            ("SPEED", f"{st['v_kms']:,.1f} KM/S" if st["v_kms"] < 100 else f"{st['v_kms']:,.0f} KM/S"),
            ("SUNLIGHT", f"× {st['flux']:,.2f}" if st["flux"] < 10 else f"× {st['flux']:,.0f}"),
            ("SUN'S WIDTH", f"× {st['ang'] / 0.5329:,.2f}" if st["ang"] / 0.5329 < 10 else f"× {st['ang'] / 0.5329:,.1f}")]
    if temp:
        rows.append(("EST. AVERAGE TEMP*", f"{st['Tsurf'] - 273.15:,.0f} °C"))
    for k, (lab, val) in enumerate(rows):
        put_text(base, lab, 16, 98, y + k * 46, a * 0.70, "l", 0.32)
        put_text(base, val, 22, 98, y + k * 46 + 19, a * 0.95, "l", 0.14)
    if temp:
        put_text(base, "*ROUGH MODEL: INSTANT EQUILIBRIUM, TODAY'S 15 °C SCALED WITH SUNLIGHT", 13, 98, y + len(rows) * 46 + 6, a * 0.55, "l", 0.25)
    if compare:
        # size comparison: today's Sun outline vs now (×12 magnified)
        lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        cx, cy = W - 150, 140; r0 = 0.5329 / 2 * 12 * (60 / 6.4)
        r1 = r0 * st["ang"] / 0.5329
        if r1 < 130:
            d.ellipse((cx - r1, cy - r1, cx + r1, cy + r1), fill=(255, 214, 160, int(210 * a)))
            d.ellipse((cx - r0, cy - r0, cx + r0, cy + r0), outline=(255, 255, 255, int(200 * a)), width=2)
            base.alpha_composite(lay)
            put_text(base, "SUN NOW  ·  O = TODAY", 13, cx, cy + max(r1, 30) + 12, a * 0.6, "c", 0.25)

def mini_map(base, sim, a=1.0, x0=1400, y0=1036, L=420):
    """Small side diagram: straight fall line with Venus/Mercury orbit ticks; Earth dot at its true distance."""
    if a <= 0.01: return
    st = state(sim)
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sxp = x0 + L
    d.line((x0, y0, sxp, y0), fill=(255, 255, 255, int(70 * a)), width=1)
    for au, name in ((0.723, "VENUS"), (0.387, "MERCURY")):
        px = sxp - au * L
        d.line((px, y0 - 9, px, y0 + 9), fill=(255, 255, 255, int(120 * a)), width=1)
        put_text(base, name, 11, px, y0 + 14, a * 0.6, "c", 0.3, shadow=False)
    d.ellipse((sxp - 6, y0 - 6, sxp + 6, y0 + 6), fill=(255, 210, 150, int(255 * a)))
    put_text(base, "SUN", 11, sxp, y0 + 14, a * 0.6, "c", 0.3, shadow=False)
    ex = sxp - st["x"] * L
    d.ellipse((ex - 4, y0 - 4, ex + 4, y0 + 4), fill=(140, 190, 255, int(255 * a)))
    base.alpha_composite(lay)
    put_text(base, "1 AU", 11, x0, y0 + 14, a * 0.5, "c", 0.3, shadow=False)

# ---------------------------------------------------------------- captions per beat
def land_captions(base, t):
    S = TL.START
    caps = [
        (S["day1"] - 0.3, S["day1b"] + 6.8, "WE ARE FALLING", "≈ 0.5 KM/S AFTER ONE DAY · ORBITAL SPEED WAS 29.8 KM/S"),
        (S["day10"] + 0.5, S["day10"] + 7.4, "FALLEN ≈ 2.2 MILLION KM", "SUN ≈ 2% WIDER"),
        (S["seasons"], S["seasons"] + 5.2, "NO ORBIT · NO SEASONS", "THE SUN STAYS OVER THE SAME LATITUDE"),
        (S["day30"] + 0.3, S["day30"] + 6.4, "1 MONTH · 14% OF THE WAY", None),
        (S["accel2"] + 99, S["accel2"] + 99, "", None),
        (S["venus"] + 0.3, S["venus"] + 6.8, "CROSSING THE ORBIT OF VENUS", "DAY 42 · 0.72 AU FROM THE SUN · SUNLIGHT ≈ × 2"),
        (S["venusb"], S["venusb"] + 5.0, "OUTDOOR HEAT: DEADLY", "ROUGH ESTIMATE · AVERAGE ≈ 70 °C"),
        (S["mercury"] + 0.3, S["mercury"] + 7.8, "MERCURY'S ORBIT · DAY 57", "57 DAYS TO HERE · ONE WEEK LEFT"),
        (S["hours13"] + 0.2, S["hours13"] + 8.2, "64 DAYS GONE · ABOUT 13 HOURS LEFT", "≈ 150 KM/S"),
        (S["hours8"] + 0.2, S["hours8"] + 5.6, "SUN ≈ 19 × WIDER THAN TODAY", "10° ACROSS · SUNLIGHT ≈ × 350"),
        (S["oceans"] + 3.0, S["oceans"] + 11.8, "THE OCEANS ARE STILL HERE", "ALL SUNLIGHT ABSORBED IN THE WHOLE FALL ≈ ENOUGH TO BOIL THE TOP ~15 M"),
        (S["hour1"] + 0.2, S["hour1"] + 5.0, "SUN ≈ 70 × WIDER · 36° ACROSS", None),
        (S["granules"] + 1.0, S["granules"] + 8.4, "GRANULES · EACH ≈ 1,000 KM ACROSS", "CONVECTION CELLS OF THE PHOTOSPHERE"),
    ]
    for a, b, s, sub in caps:
        if a <= t <= b and s:
            caption(base, s, window(t, a, b, 0.7, 0.8), sub=sub)

# ---------------------------------------------------------------- shots
def sim_and_blink(t):
    sim = TL.sim_of(t)
    # brief "night" blink each time the day changes during the fast flips (landC)
    blink = 0.0
    if 136.0 <= t < 151.0:
        dt = 1 / 24.0
        s_prev = TL.sim_of(t - 0.12)
        if math.floor(s_prev) != math.floor(sim): blink = 0.8
    return sim, blink

def frame_land(t, shot):
    sim, blink = sim_and_blink(t)
    sun_el = 6.0
    if shot == "landA":
        sun_el = lerp(-0.8, 6.0, smooth((t - 36.5) / 4.5))       # day one: sunrise
    if shot == "open": sim = -0.4
    img, expo, info = land_frame(t, max(sim, 0.0), sun_el, blink)
    img = bloom(img, 0.30 + 0.3 * info["late"])
    out = tonemap(img, expo)
    if shot != "open":
        out = scrim(out)
    base = Image.fromarray(out).convert("RGBA")
    if shot == "open":
        a = smooth((t - 0.0) / 2.2)
        if t > 9.0:
            put_text(base, "65 DAYS", 120, W // 2, 380, window(t, 9.3, 14.3, 1.2, 1.0), "c", 0.42, thin=True)
            put_text(base, "IF EARTH STOPPED IN ITS ORBIT", 20, W // 2, 540, window(t, 10.2, 14.3, 1.2, 1.0) * 0.8, "c", 0.42)
        fade = 1 - a
    else:
        hud_a = smooth((t - 37.0) / 1.2) if shot == "landA" else smooth((t - TL.shot_of(t)[1]) / 0.6)
        late = info["late"]
        hud(base, t, sim, info, hud_a, compare=(info["a_deg"] < 1.2), temp=(sim < 64.0))
        mini_map(base, sim, hud_a * (1 - smooth((info["a_deg"] - 3) / 2)))
        land_captions(base, t)
        fade = 0.0
    fr = np.asarray(base.convert("RGB")).astype(np.float32)
    if shot == "open": fr *= (1 - fade)
    if shot == "landC" and t > 196.4: fr = fr * (1 - smooth((t - 196.4) / 0.6)) + 255 * 0.0
    return fr.astype(np.uint8)

@functools.lru_cache(maxsize=1)
def starfield(w=3200, h=1900, seed=5):
    r = np.random.default_rng(seed)
    img = np.zeros((h, w), np.float32)
    n = 2600
    xs = r.uniform(0, w, n); ys = r.uniform(0, h, n); fl = 0.08 + 0.9 * r.power(0.12, n) ** 0  # base
    fl = 0.05 + 1.4 * (1 - r.power(0.25, n)) ** 5
    for x, y, f in zip(xs, ys, fl):
        ix, iy = int(x), int(y); fx, fy = x - ix, y - iy
        if 1 <= ix < w - 2 and 1 <= iy < h - 2:
            img[iy, ix] += f * (1 - fx) * (1 - fy); img[iy, ix + 1] += f * fx * (1 - fy)
            img[iy + 1, ix] += f * (1 - fx) * fy; img[iy + 1, ix + 1] += f * fx * fy
    return img

def stars_crop(ox, oy, scale=1.0):
    sf = starfield()
    x0 = int(ox); y0 = int(oy)
    c = sf[y0:y0 + H, x0:x0 + W]
    return np.stack([c * 0.95, c * 0.97, c * 1.05], -1)

@functools.lru_cache(maxsize=4)
def still(p): return load_rgba(p)

def crop_zoom(arr, cx, cy, zoom, src_scale=1.5):
    """Crop a (2880x1620) float RGBA array around (cx,cy) (in source px) at zoom (1 = full frame) -> 1920x1080."""
    h, w = arr.shape[:2]
    cw, ch = w / zoom, h / zoom
    x0 = cx - cw / 2; y0 = cy - ch / 2
    im = Image.fromarray((np.clip(arr, 0, 1) * 65535).astype(np.uint16)[..., 0]) if False else None
    # per-channel float resize via PIL 'F'
    out = np.zeros((H, W, arr.shape[2]), np.float32)
    for c in range(arr.shape[2]):
        ch_ = Image.fromarray(arr[..., c].astype(np.float32), mode="F")
        out[..., c] = np.asarray(ch_.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.Resampling.BILINEAR), np.float32)
    return out

def frame_orbit(t):
    u = t - 14.5
    ts = 33.6 - 14.5
    # camera drift (orbital motion) decelerating to exactly zero at the stop; then a slow push in
    v0 = 26.0                                     # source px / s
    def pos(tt):
        n = 120; acc = 0.0
        for i in range(n):
            x = min(tt, ts) * (i + 0.5) / n
            acc += v0 * (1 - smooth((x - (ts - 3.0)) / 3.0)) * min(tt, ts) / n
        return acc
    px = pos(u)
    zoom = 1.0 + 0.06 * smooth((u - ts - 0.2) / 3.0)
    earth = still(FR + "/orbit/f_0001.png")
    e = crop_zoom(earth, 1440 - 160 + px * 1.0 - 250, 810, zoom * 1.0)
    st = stars_crop(200 + px * 0.25, 300, 1.0) * 0.55
    # Sun glare from off-frame left
    gl = (0.55 * np.exp(-(XX + 380) / 420.0) * np.exp(-((YY - 470) / 900.0) ** 2))[..., None] * F32((1.0, 0.86, 0.66))
    col = st * (1 - e[..., 3:4]) + e[..., :3] + gl
    col = col * smooth(u / 1.0)
    base = Image.fromarray((np.clip(col, 0, 1) ** 1.0 * 255).astype(np.uint8)).convert("RGBA")
    # orbital speed readout: 29.8 km/s, drops to 0 with the stop
    speed = 29.8 * (1 - smooth((u - (ts - 3.0)) / 3.0))
    a = window(t, 16.0, 36.3, 1.0, 0.8)
    put_text(base, "EARTH'S ORBITAL SPEED", 16, 98, 820, a * 0.7, "l", 0.32)
    put_text(base, f"{speed:4.1f} KM/S", 44, 98, 845, a, "l", 0.14, thin=True)
    caption(base, "A THOUGHT EXPERIMENT", window(t, 27.6, 32.2, 0.6, 0.8), y=930, sub="NOTHING COULD REALLY STOP A PLANET")
    fr = np.asarray(base.convert("RGB")).astype(np.float32)
    fr *= 1 - smooth((t - 35.9) / 0.6)
    return fr.astype(np.uint8)

def frame_moon(t):
    u = (t - 124.0) / 12.0
    earth = still(FR + "/moon_earth/f_0001.png"); moon = still(FR + "/moon_moon/f_0001.png")
    sim = TL.sim_of(t); st = state(sim)
    canvas = np.zeros((1620, 2880, 3), np.float32)
    sf = starfield()[:1620, :2880] * 0.35
    canvas += np.stack([sf, sf, sf * 1.08], -1)
    # the Sun: 1.4° disc at (2016, 583) in source px, with glare
    sx, sy = 2016.0, 583.5
    r_s = math.tan(math.radians(st["ang"] / 2)) * F_PX * 1.5 * (2667.0 / 2637.6)
    yy, xx = np.mgrid[0:1620, 0:2880].astype(np.float32)
    d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
    disk = np.clip(r_s - d + 0.5, 0, 1) * 30.0
    glare = 1.4 * np.exp(-np.maximum(d - r_s, 0) / 40.0) + 0.35 * np.exp(-np.maximum(d - r_s, 0) / 260.0)
    ang = np.arctan2(yy - sy, xx - sx)
    rays = (0.5 + 0.5 * np.cos(ang * 6 + 0.4)) ** 14 * np.exp(-np.maximum(d - r_s, 0) / 320.0) * 0.08
    canvas += (disk + glare + rays)[..., None] * F32((1.0, 0.86, 0.66))
    # Moon drifts slowly away from Earth (the Sun's tide pulling them apart)
    mdx, mdy = -30.0 * smooth(u), -10.0 * smooth(u)
    mo = np.roll(np.roll(moon, int(mdy), 0), int(mdx), 1)
    canvas = canvas * (1 - mo[..., 3:4]) + mo[..., :3] * 2.2
    canvas = canvas * (1 - earth[..., 3:4]) + earth[..., :3] * 1.15
    arr = np.concatenate([canvas, np.ones((1620, 2880, 1), np.float32)], -1)
    zoom = 1.0 + 0.07 * smooth(u)
    out = crop_zoom(arr, 1440 + 60 * u, 810, zoom)[..., :3]
    out = 1 - np.exp(-np.clip(out, 0, None) * 1.1)
    out = out ** (1 / 1.25)
    base = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    a = window(t, 124.4, 136.0, 0.8, 0.6)
    hud(base, t, sim, {"st": st}, a, compare=False, temp=False)
    caption(base, "EARTH AND MOON · FALLING TOGETHER", window(t, 125.5, 133.8, 0.8, 0.8), sub="THE SUN'S TIDES BEGIN TO PULL THEM APART")
    fr = np.asarray(base.convert("RGB")).astype(np.float32)
    fr *= smooth((t - 124.0) / 0.6) * (1 - smooth((t - 135.5) / 0.5))
    return fr.astype(np.uint8)

def frame_dive(t):
    f = int(round((t - 197.0) * FPS)) + 1
    f = min(f, 510)
    def ld(k): return np.asarray(Image.open(f"{FR}/dive/f_{k:04d}.png").convert("RGB")).astype(np.float32) / 255.0
    ex = lambda k: os.path.exists(f"{FR}/dive/f_{k:04d}.png")
    if ex(f): im = ld(f)
    elif ex(f - 1) and ex(f + 1): im = 0.5 * (ld(f - 1) + ld(f + 1))     # frames rendered at half rate: blend
    else:
        k = next(k for d in range(1, 600) for k in (f - d, f + d) if 1 <= k <= 510 and ex(k))
        im = ld(k)
    lin = im ** 2.2 * 1.6
    # shimmer / turbulence close in
    sim = TL.sim_of(t); st = state(sim)
    hgt = max(0.0, st["r_km"] - 6.957e5 - 6371)
    lin = bloom(lin * 1.0, 0.45)
    out = 1 - np.exp(-lin * 1.4)
    out = np.clip(out, 0, 1) ** (1 / 2.2)
    base = Image.fromarray((out * 255).astype(np.uint8)).convert("RGBA")
    a = window(t, 197.3, 217.8, 0.6, 0.4)
    rem = max(0.0, (TL.T_IMPACT_D - sim) * 86400.0)
    mm = int(rem // 60); ss = rem - mm * 60
    put_text(base, f"00:{mm:02d}:{ss:05.2f}", 66, 92, 64, a, "l", 0.12, thin=True)
    put_text(base, "LEFT", 22, 98, 150, a * 0.85, "l", 0.35)
    put_text(base, "ALTITUDE ABOVE THE SUN", 16, 98, 196, a * 0.7, "l", 0.32)
    put_text(base, f"{hgt:,.0f} KM", 22, 98, 215, a * 0.95, "l", 0.14)
    put_text(base, "SPEED", 16, 98, 242, a * 0.7, "l", 0.32)
    put_text(base, f"{st['v_kms']:,.0f} KM/S", 22, 98, 261, a * 0.95, "l", 0.14)
    S = TL.START
    caption(base, "THE SUN'S TIDES BEGIN TO STRETCH EARTH", window(t, S["tides"], S["tides"] + 5.0, 0.6, 0.6), sub="ROCHE LIMIT ≈ 1.5 SOLAR RADII · ~11 MINUTES LEFT")
    caption(base, "IMPACT ≈ 613 KM/S", window(t, S["impact"] + 0.3, S["impact"] + 6.8, 0.6, 0.6), sub="THE SUN'S ESCAPE SPEED ≈ 618 KM/S")
    caption(base, "EARTH'S WIDTH IN ≈ 20 SECONDS", window(t, S["impact"] + 7.0, 217.6, 0.5, 0.4))
    fr = np.asarray(base.convert("RGB")).astype(np.float32)
    # in from the landscape whiteness, out to white at impact
    fr = fr * smooth((t - 197.0) / 0.6) + 255 * (1 - smooth((t - 197.0) / 0.6)) * 0.0
    wv = smooth((t - 216.9) / 1.1)
    fr = fr * (1 - wv) + 255 * wv
    return fr.astype(np.uint8)

def frame_black(t):
    fr = np.full((H, W, 3), 255.0, np.float32)
    k = smooth((t - 219.5) / 2.4)
    fr *= (1 - k)
    base = Image.fromarray(fr.astype(np.uint8)).convert("RGBA")
    S = TL.START
    caption(base, "EARTH ≈ 1/333,000 OF THE SUN'S MASS", window(t, S["after"] + 2.2, S["after"] + 6.4, 0.8, 0.8), y=520)
    return np.asarray(base.convert("RGB"))

def frame_orbitdg(t):
    """An orbit is a fall that keeps missing: Earth circling, gravity arrow toward the Sun, velocity tangent."""
    S2 = 2
    im = Image.new("RGB", (W * S2, H * S2), (2, 3, 6))
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = 960 * S2, 540 * S2; R = 360 * S2
    a_in = window(t, 229.5, 253.5, 1.5, 1.2)
    # Sun glow
    for k in range(12, 0, -1):
        rr = (14 + k * 4) * S2
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 190, 120, int(4 * a_in)))
    d.ellipse((cx - 16 * S2, cy - 16 * S2, cx + 16 * S2, cy + 16 * S2), fill=(255, 226, 180, int(255 * a_in)))
    # orbit path
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(255, 255, 255, int(40 * a_in)), width=S2)
    th = math.radians(200) - (t - 229.5) * 0.11
    ex, ey = cx + R * math.cos(th), cy + R * math.sin(th)
    # trail
    for k in range(60):
        t2 = th + k * 0.012
        a2 = int(140 * a_in * (1 - k / 60))
        x1, y1 = cx + R * math.cos(t2), cy + R * math.sin(t2)
        x2, y2 = cx + R * math.cos(t2 + 0.012), cy + R * math.sin(t2 + 0.012)
        d.line((x1, y1, x2, y2), fill=(140, 190, 255, a2), width=3 * S2)
    S = TL.START
    # straight-line fall (what we just watched) shown as a dashed line to the Sun
    af = a_in * window(t, 229.8, S["end2"] + 1.5, 1.0, 1.0)
    n = 40
    for k in range(0, n, 2):
        u0, u1 = k / n, (k + 1) / n
        d.line((lerp(ex, cx, u0), lerp(ey, cy, u0), lerp(ex, cx, u1), lerp(ey, cy, u1)), fill=(255, 200, 150, int(110 * af)), width=S2)
    # velocity arrow (tangent) and gravity arrow (toward Sun)
    av = a_in * smooth((t - S["end2"]) / 1.0)
    tx, ty = math.sin(th), -math.cos(th)
    L = 150 * S2
    d.line((ex, ey, ex + tx * L, ey + ty * L), fill=(200, 225, 255, int(220 * av)), width=2 * S2)
    hx, hy = ex + tx * L, ey + ty * L
    for s_ in (-1, 1):
        d.line((hx, hy, hx - tx * 16 * S2 + s_ * ty * 9 * S2, hy - ty * 16 * S2 - s_ * tx * 9 * S2), fill=(200, 225, 255, int(220 * av)), width=2 * S2)
    gx, gy = (cx - ex) / R, (cy - ey) / R
    Lg = 95 * S2
    ag = a_in * smooth((t - (S["end1"] + 3.0)) / 1.0)
    d.line((ex, ey, ex + gx * Lg, ey + gy * Lg), fill=(255, 200, 150, int(220 * ag)), width=2 * S2)
    hx, hy = ex + gx * Lg, ey + gy * Lg
    for s_ in (-1, 1):
        d.line((hx, hy, hx - gx * 16 * S2 + s_ * gy * 9 * S2, hy - gy * 16 * S2 - s_ * gx * 9 * S2), fill=(255, 200, 150, int(220 * ag)), width=2 * S2)
    d.ellipse((ex - 9 * S2, ey - 9 * S2, ex + 9 * S2, ey + 9 * S2), fill=(150, 200, 255, int(255 * a_in)))
    im = im.resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")
    put_text(im, "FALLING", 18, int(ex / S2 + gx * Lg / S2) + 14, int(ey / S2 + gy * Lg / S2) - 12, ag * 0.85, "l", 0.35)
    put_text(im, "MOVING SIDEWAYS · 29.8 KM/S", 18, int(ex / S2 + tx * L / S2) + 16, int(ey / S2 + ty * L / S2) - 10, av * 0.85, "l", 0.30)
    put_text(im, "FALLING FOR 4.5 BILLION YEARS · AND MISSING", 24, W // 2, 960, window(t, S["end3"] + 0.6, 253.3, 1.0, 1.0) * 0.9, "c", 0.32)
    return np.asarray(im.convert("RGB"))

def frame_title(t):
    base = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    a = window(t, 253.4, 264.0, 1.6, 2.2)
    put_text(base, "65 DAYS", 120, W // 2, 420, a, "c", 0.42, thin=True)
    put_text(base, "A THOUGHT EXPERIMENT · RADIAL FREE FALL FROM 1 AU = 64.6 DAYS", 17, W // 2, 590, a * 0.65, "c", 0.30)
    return np.asarray(base.convert("RGB"))

def frame_diagram(t):
    S2 = 2
    im = Image.new("RGB", (W * S2, H * S2), (3, 4, 8))
    d = ImageDraw.Draw(im, "RGBA")
    a_in = window(t, 82.5, 98.5, 0.8, 0.8)
    X0, X1, Y = 200, 1640, 560                     # 1 AU = 1440 px
    sxp = X1
    def X(au): return sxp - au * (X1 - X0)
    # orbits as arcs around the Sun
    for au, name, col in ((1.0, "EARTH'S ORBIT", (140, 190, 255)), (0.723, "VENUS", (255, 230, 190)), (0.387, "MERCURY", (220, 220, 220))):
        R = au * (X1 - X0) * S2
        box = (sxp * S2 - R, Y * S2 - R, sxp * S2 + R, Y * S2 + R)
        d.arc(box, 150, 210, fill=col + (int(70 * a_in),), width=S2)
    # the Sun (true scale radius 6.7 px) + glow
    for k in range(10, 0, -1):
        rr = (7 + k * 3.2) * S2
        d.ellipse((sxp * S2 - rr, Y * S2 - rr, sxp * S2 + rr, Y * S2 + rr), fill=(255, 190, 120, int(5 * a_in)))
    rs = 6.7 * S2
    d.ellipse((sxp * S2 - rs, Y * S2 - rs, sxp * S2 + rs, Y * S2 + rs), fill=(255, 226, 180, int(255 * a_in)))
    d.line((X0 * S2, Y * S2, sxp * S2, Y * S2), fill=(255, 255, 255, int(60 * a_in)), width=S2)
    # Earth runs the whole fall, linear in time, so the spacing of day ticks shows the acceleration
    u = clamp((t - 84.0) / 11.5)
    simd = u * TL.T_IMPACT_D
    for dd in range(1, 65):
        if dd > simd: break
        x = X(state(dd)["x"])
        big = dd % 10 == 0 or dd in (42, 57, 64)
        hgt = 16 if big else 8
        d.line((x * S2, (Y - hgt) * S2, x * S2, (Y + hgt) * S2), fill=(255, 255, 255, int((170 if big else 90) * a_in)), width=S2)
    ex = X(state(simd)["x"])
    d.ellipse(((ex - 7) * S2, (Y - 7) * S2, (ex + 7) * S2, (Y + 7) * S2), fill=(150, 200, 255, int(255 * a_in)))
    S = TL.START
    # half-distance brackets
    ab1 = a_in * smooth((t - (S["accel2"] + 0.2)) / 0.8); ab2 = a_in * smooth((t - (S["accel2"] + 2.9)) / 0.8)
    xm = X(0.5)
    for (xa, xb, aa) in ((X0, xm, ab1), (xm, sxp, ab2)):
        d.line((xa * S2, (Y - 70) * S2, xb * S2, (Y - 70) * S2), fill=(255, 255, 255, int(120 * aa)), width=S2)
        for xx in (xa, xb): d.line((xx * S2, (Y - 80) * S2, xx * S2, (Y - 60) * S2), fill=(255, 255, 255, int(120 * aa)), width=S2)
    im = im.resize((W, H), Image.Resampling.LANCZOS).convert("RGBA")
    put_text(im, "FIRST HALF: 53 DAYS", 24, int((X0 + xm) / 2), Y - 120, ab1, "c", 0.30)
    put_text(im, "SECOND HALF: 11.7 DAYS", 24, int((xm + sxp) / 2), Y - 120, ab2, "c", 0.30)
    for dd, lab in ((30, "DAY 30"), (42, "42 · VENUS"), (57, "57 · MERCURY"), (64, "64")):
        if dd <= simd:
            x = X(state(dd)["x"])
            put_text(im, lab, 14, int(x), Y + 30, a_in * 0.75, "c", 0.25)
    put_text(im, "1 AU · DAY 0", 14, X0, Y - 44, a_in * 0.6, "c", 0.25)
    put_text(im, "SUN (TO SCALE)", 14, sxp, Y - 50, a_in * 0.6, "c", 0.25)
    put_text(im, "ONE TICK PER DAY", 16, W // 2, 860, a_in * 0.6 * smooth((t - 85) / 1), "c", 0.35)
    put_text(im, "GRAVITY GROWS AS 1 / DISTANCE²", 22, W // 2, 220, window(t, S["accel1"] + 2.5, S["accel2"] - 0.2, 0.7, 0.7) * 0.9, "c", 0.30)
    return np.asarray(im.convert("RGB"))

def frame(t):
    name, a, b = TL.shot_of(t)
    if name in ("open", "landA", "landB", "landC"): return frame_land(t, name)
    if name == "orbit": return frame_orbit(t)
    if name == "moon": return frame_moon(t)
    if name == "diagram": return frame_diagram(t)
    if name == "dive": return frame_dive(t)
    if name == "black": return frame_black(t)
    if name == "orbitdg": return frame_orbitdg(t)
    return frame_title(t)

def shot_range(name):
    for n, a, b in TL.SHOTS:
        if n == name: return int(round(a * FPS)), int(round(b * FPS))
    raise KeyError(name)

def encode(name):
    f0, f1 = shot_range(name)
    os.makedirs(SEG, exist_ok=True)
    out = f"{SEG}/{name}.mp4"
    if os.path.exists(out): print("exists", out); return
    tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(f0, f1):
        fr = frame(i / FPS)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
        if (i - f0) % 48 == 0:
            print(f"[{name}] {i - f0}/{f1 - f0}  {(time.time() - t0) / max(1, i - f0 + 1):.2f}s/f", flush=True)
    p.stdin.close(); p.wait()
    os.replace(tmp, out)
    print(f"[{name}] done {f1 - f0} frames in {time.time() - t0:.0f}s", flush=True)

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--frames" in args:
        ts = [float(v) for v in args[args.index("--frames") + 1].split(",")]
        od = args[args.index("--png") + 1] if "--png" in args else SCR + "/stills"
        os.makedirs(od, exist_ok=True)
        for tt in ts:
            t0 = time.time(); fr = frame(tt)
            Image.fromarray(fr).save(f"{od}/t_{tt:07.2f}.png"); print(f"t={tt} {time.time() - t0:.2f}s", flush=True)
    else:
        for name in args: encode(name)
