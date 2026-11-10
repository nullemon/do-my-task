"""Compositor for 08 'IF THE SUN VANISHED RIGHT NOW' (numpy + cv2, linear HDR -> bloom -> tonemap -> thin type).
  python3 comp.py <t0> <t1>          render seconds [t0, t1) to SCR/seg/seg_<frame>.mp4 (silent x264 crf 14)
  python3 comp.py still <t> [<t>..]  write SCR/chk/f_<t>.jpg
Shots (all locked to the voice, timeline.py):
  SUN close-up -> vanishes -> EARTH (still lit) -> LAKE by day -> DIAGRAM (last light / gravity front) -> LAKE goes dark
  -> DIAGRAM (straight line) -> MOON -> night LAKE + planets -> JUPITER, SATURN -> stars -> LAKE (cold, frost) -> EARTH freezing
  -> under the ICE -> VENTS -> LAKE (air snowing out) -> frozen EARTH adrift -> SUNRISE from orbit -> SUN -> LAKE by day.
"""
import sys, os, json, math, subprocess
from lib import *
import timeline as TL
S, E, FPS, DUR = TL.START, TL.END, TL.FPS, TL.DUR
YEL = (255, 208, 64); WHT = (236, 240, 248); DIM = (170, 180, 196)
TV = 2.35                      # film time at which the Sun vanishes (T = 0)
T_DARK = 53.9                  # film time at which T + 00:08:20 is reached in the 'dark' shot


# ------------------------------------------------------------------------------------------------ overlays
def fade(t, a, b, fi=0.6, fo=0.6):
    if t < a or t > b: return 0.0
    return min(1.0, (t - a) / fi if fi > 0 else 1, (b - t) / fo if fo > 0 else 1)

def clock(ov, value, a=1.0, label="TIME SINCE THE SUN VANISHED", col=WHT):
    if a <= 0: return
    ov.text(96, 70, label, size=13, wt="Regular", col=DIM, a=a * 0.9, track=0.32)
    f = font(84, "Light"); adv = f.getlength("0") + 0.06 * f.size; x = 96 * 2
    for ch in value:                                  # tabular figures: fixed advance for digits
        wch = f.getlength(ch); cell = adv if ch.isdigit() else (wch + 0.10 * f.size if ch != " " else 0.32 * f.size)
        if ch != " ":
            ov.text((x + (cell - wch) / 2) / 2, 92, ch, size=42, wt="Light", col=col, a=a, track=0)
        x += cell

def hms(sec): return "T + " + clock_str(sec)

def caption(ov, t, a, b, main, sub=None, y=928, x=96, size=27, col=WHT, anchor="l", sub_col=DIM):
    al = fade(t, a, b)
    if al <= 0: return
    ov.text(x, y, main, size=size, wt="Light", col=col, a=al, track=0.24, anchor=anchor)
    if sub: ov.text(x, y + size * 1.75, sub, size=15, wt="Regular", col=sub_col, a=al * 0.92, track=0.26, anchor=anchor)

def note(ov, t, a, b, txt, x=W - 96, y=1010):
    al = fade(t, a, b)
    if al > 0: ov.text(x, y, txt, size=12, wt="Regular", col=DIM, a=al * 0.8, track=0.28, anchor="r")


# ------------------------------------------------------------------------------------------------ LAND (lake + mountains plate)
PW, PH = 2304, 1296
PF = 26.0 / 36.0 * PW                       # focal length in plate px
PYH = PH / 2 + 0.06 * 36.0 / (36.0 * PH / PW) * PH   # horizon row (camera is level, lens shift 0.06)
SUN_AZ, SUN_EL = math.radians(-22.0), math.radians(15.0)
SUN_DIR = np.array([math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)])
def plate_xy(az, el):
    d = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
    return PW / 2 + d[0] / d[1] * PF, PYH - d[2] / d[1] * PF

def srgb_dec(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(f32)

_land = {}
def land_plates():
    if _land: return _land
    P = os.path.join(SCR, "plates")
    def rd(n):
        im = cv2.imread(os.path.join(P, n), cv2.IMREAD_UNCHANGED).astype(f32) / 65535.0
        return im
    for var in ("rock", "snow"):
        for ps in ("sun", "amb"):
            fn = f"land_{var}_{ps}.png"
            if not os.path.exists(os.path.join(P, fn)): fn = f"land_rock_{ps}.png"; print("WARNING: snow plate missing, using rock")
            im = rd(fn); _land[f"{var}_{ps}"] = srgb_dec(im[..., 2::-1])
            if ps == "amb": _land[f"{var}_alpha"] = im[..., 3].copy()
        d = rd(f"land_{var}_depth.png")
        _land[f"{var}_depth"] = srgb_dec(d[..., 1]) * 200.0
        _land[f"{var}_lake"] = ((d[..., 2] < 0.5) & (d[..., 3] > 0.5)).astype(f32)    # R channel (BGR order -> index 2) flag: terrain 1, lake 0
    m = rd("land_rock_mirror.png"); _land["mirror"] = np.clip(m[..., 2] * m[..., 3], 0, 1)
    _land["ripple"] = fbm2((1024, 1024), 91, 1.6); _land["cirrus"] = np.clip(fbm2((1024, 2048), 92, 2.3) * 0.5 + 0.35, 0, 1) ** 1.6
    _land["mist"] = np.clip(fbm2((512, 2048), 93, 2.4) * 0.5 + 0.5, 0, 1); _land["dissolve"] = fbm2((PH, PW), 94, 2.2)
    return _land

def clampc(s, pcx, pcy):
    """keep the 1920x1080 window inside the plate"""
    s = min(s, PW / W, PH / H); hx, hy = W / 2 * s, H / 2 * s
    return s, min(max(pcx, hx), PW - hx), min(max(pcy, hy), PH - hy)

def warp(img, s, pcx, pcy, interp=cv2.INTER_LINEAR):
    M = np.array([[s, 0, pcx - s * W / 2], [0, s, pcy - s * H / 2]], np.float64)
    return cv2.warpAffine(img, M, (W, H), flags=interp | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)

_rng_p = np.random.default_rng(123)
_flakes = dict(x=_rng_p.uniform(0, 1, 9000), y=_rng_p.uniform(0, 1, 9000), z=_rng_p.uniform(0.15, 1.0, 9000) ** 1.5, ph=_rng_p.uniform(0, 6.28, 9000))

def particles(t, n, fall=0.05, sway=0.01, bright=0.3, size=1.0, seed_off=0, drift=0.0):
    """falling flakes, 3 depth groups; returns an additive HDR layer"""
    out = np.zeros((H, W), f32)
    for gi, (z0, z1, sig) in enumerate(((0.15, 0.4, 0.8), (0.4, 0.7, 1.3), (0.7, 1.01, 2.6))):
        sel = np.where((_flakes["z"][:n] >= z0) & (_flakes["z"][:n] < z1))[0]
        z = _flakes["z"][sel]
        x = (_flakes["x"][sel] + drift * t * z + sway * np.sin(t * 0.9 + _flakes["ph"][sel])) % 1.0 * (W + 40) - 20
        y = (_flakes["y"][sel] + fall * t * (0.5 + z)) % 1.0 * (H + 40) - 20
        lay = np.zeros((H, W), f32)
        xi = np.clip(x.astype(int), 0, W - 1); yi = np.clip(y.astype(int), 0, H - 1)
        np.add.at(lay, (yi, xi), (0.4 + 0.6 * z) * (0.6 + 0.4 * np.sin(t * 2.3 + _flakes["ph"][sel] * 3)))
        out += cv2.GaussianBlur(lay, (0, 0), sig * size) * (sig * size) ** 2 * 3.0
    return out * bright

def up(x): return cv2.resize(x, (W, H), interpolation=cv2.INTER_LINEAR)
def splat(img, fx, fy, rad, fn):
    """add fn(d) (HxWx3 patch) around (fx, fy) only"""
    x0, x1 = max(0, int(fx - rad)), min(W, int(fx + rad) + 1); y0, y1 = max(0, int(fy - rad)), min(H, int(fy + rad) + 1)
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
    img[y0:y1, x0:x1] += fn(np.sqrt((xx + 0.5 - fx) ** 2 + (yy + 0.5 - fy) ** 2))

def land(t, s=1.2, pcx=PW / 2, pcy=PH / 2, sun=1.0, night=0.0, moon=0.0, frost=0.0, mist=0.0, sky_rot=0.0, sky_c=(2250, 1180), sky_gain=1.0,
         planets=(), flakes=0.0, flake_n=4000, dead=0.0, sun_glare=1.0, air=1.0, sky_scale=0.95, haze_night=0.0, glitter=1.0):
    """sun: sunlight 0..1 (sky scattering, direct light). night: exposure of the star-lit scene (0..1).
    air: 1 = atmosphere present (blue sky by day, extinction near the horizon), 0 = airless. frost: 0..1 snow/ice cover.
    Smooth fields (sky colour, extinction, mist) are evaluated on a half-resolution grid and upsampled."""
    L = land_plates(); s, pcx, pcy = clampc(s, pcx, pcy)
    yy, xx = np.mgrid[0:H:2, 0:W:2].astype(f32); yy += 0.5; xx += 0.5          # half-res grid, in full-frame pixel units
    yr = np.arange(H, dtype=f32)[:, None]; xr = np.arange(W, dtype=f32)[None, :]
    xp = pcx + (xx + 0.5 - W / 2) * s; yp = pcy + (yy + 0.5 - H / 2) * s
    dxn = (xp - PW / 2) / PF; dzn = (PYH - yp) / PF
    inv = 1.0 / np.sqrt(dxn * dxn + 1 + dzn * dzn)
    el = np.arcsin(np.clip(dzn * inv, -1, 1)); elc = np.maximum(el, 0)
    cosg = np.clip((dxn * SUN_DIR[0] + SUN_DIR[1] + dzn * SUN_DIR[2]) * inv, -1, 1); gam = np.arccos(cosg)
    yh = (PYH - pcy) / s + H / 2                                         # horizon row in the frame
    ssx, ssy = plate_xy(SUN_AZ, SUN_EL); sfx = (ssx - pcx) / s + W / 2; sfy = (ssy - pcy) / s + H / 2; rs = 0.0046 * PF / s
    # ---------------- sky
    if night > 0:
        st = sky_view(sky_c[0], sky_c[1], sky_scale * s / 1.2, sky_rot)
        ext = up(1 - air * 0.75 * np.exp(-elc / 0.07))
        sky = st * (ext * (night * sky_gain * 3.4))[..., None]
    else: sky = np.zeros((H, W, 3), f32)
    for (az, e_, flux, col, a_) in planets:
        if a_ <= 0: continue
        px, py = plate_xy(math.radians(az), math.radians(e_)); fx = (px - pcx) / s + W / 2; fy = (py - pcy) / s + H / 2
        splat(sky, fx, fy, 40, lambda d: ((np.exp(-d * d / (2 * 1.3 ** 2)) + 0.05 * np.exp(-d / 5.0)) * flux * a_ * night * 22.0)[..., None] * np.array(col, f32))
    if moon > 0:
        splat(sky, sfx, sfy, rs * 80, lambda d: (np.clip(rs - d + 0.5, 0, 1) * 14.0 * moon + np.exp(-d / (rs * 5)) * 0.25 * moon * air + np.exp(-d / (rs * 22)) * 0.03 * moon * air)[..., None] * np.array([0.92, 0.95, 1.0], f32))
    horizon_col = np.array([0.62, 0.72, 0.86], f32)
    warm = None
    if sun > 0:
        zen = np.array([0.022, 0.085, 0.36], f32)
        k = np.exp(-elc / 0.20)[..., None]
        ray = (zen * (1 - k) + horizon_col * 0.62 * k) * air
        mie = (2.2 * np.exp(-gam / 0.022) + 0.75 * np.exp(-gam / 0.07) + 0.26 * np.exp(-gam / 0.2) + 0.07 * np.exp(-gam / 0.6))[..., None] * np.array([1.0, 0.86, 0.66], f32) * air * sun_glare
        u = np.arctan2(dxn, 1.0) / (elc + 0.16) * 0.030 + 0.02 / (elc + 0.16); v = 0.14 / (elc + 0.16)
        ci = cv2.remap(L["cirrus"], ((u * 2048 + t * 1.4) % 2048).astype(f32), ((v * 1024) % 1024).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        ci = np.clip(ci * 2.2 - 0.5, 0, 1) ** 1.3 * smooth(0.0, 0.10, el) * 0.30 * air
        cic = (np.array([0.95, 0.95, 1.0], f32) * 0.55 + np.array([1.0, 0.8, 0.55], f32) * np.exp(-gam / 0.3)[..., None] * 1.3)
        sky += up((ray * (1 - ci[..., None] * 0.6) + cic * ci[..., None] + mie) * sun)
        splat(sky, sfx, sfy, rs * 12, lambda d: (np.clip(rs - d + 0.5, 0, 1) * 90.0 * sun * sun_glare + (1 - air) * np.exp(-d / (rs * 3)) * 2 * sun)[..., None] * np.array([1.0, 0.93, 0.80], f32))
        warm = up(np.exp(-gam / 0.5))
    # ---------------- land light
    def lit(var):
        am = warp(L[f"{var}_amb"], s, pcx, pcy)
        c = np.zeros_like(am)
        if sun > 0 or moon > 0:
            sp = warp(L[f"{var}_sun"], s, pcx, pcy)
            if sun > 0: c += sp * (np.array([1.25, 1.08, 0.86], f32) * (sun * 1.9)) + am * (np.array([0.40, 0.56, 0.95], f32) * (0.62 * sun * (0.25 + 0.75 * air)))
            if moon > 0: c += sp * (np.array([0.62, 0.76, 1.0], f32) * (0.20 * moon)) + am * (np.array([0.5, 0.65, 1.0], f32) * (0.012 * moon))
        if night > 0: c += am * (np.array([0.46, 0.64, 1.0], f32) * ((0.42 if var == 'rock' else 0.20) * night))
        return c
    alpha = warp(L["rock_alpha"], s, pcx, pcy)
    depth = warp(L["rock_depth"], s, pcx, pcy)
    if frost >= 1: lc = lit("snow"); lake = warp(L["snow_lake"], s, pcx, pcy); fz = 1.0
    elif frost <= 0: lc = lit("rock"); lake = warp(L["rock_lake"], s, pcx, pcy); fz = 0.0
    else:
        dz = warp(L["dissolve"], s, pcx, pcy)
        fz = smooth(-0.5, 0.5, (frost * 3.4 - 1.2) - 0.6 * dz - 0.25 * np.clip(1 - depth / 60, 0, 1))
        lc = lit("rock") * (1 - fz[..., None]) + lit("snow") * fz[..., None]; lake = warp(L["rock_lake"], s, pcx, pcy)
    if dead > 0:                                                         # vegetation greens -> dry brown
        mean = lc.mean(2)
        gn = np.clip((lc[..., 1] - 0.5 * (lc[..., 0] + lc[..., 2])) / (mean + 1e-4) * 3.0, 0, 1)[..., None] * dead
        lc = lc * (1 - gn) + mean[..., None] * np.array([1.2, 0.98, 0.7], f32) * gn
    # ---------------- lake: Fresnel-weighted mirror (terrain reflection is in the render; the sky reflection is added here)
    below = np.clip(yr - yh, 0, None)                                     # (H,1)
    y_l = int(max(0, math.floor(yh)))                                    # first lake row
    if (np.isscalar(fz) and fz < 1) or not np.isscalar(fz):
        if y_l < H:
            bl = below[y_l:]; xs = xr
            fres = 0.03 + 0.97 * (1 - np.clip(bl * s / PF, 0, 1)) ** 5
            persp = 1.0 / (bl + 6.0)
            ru = (xs - W / 2) * persp * (2.6 * 1024 / 40); rv = np.broadcast_to(persp * (1024 * 9.0), ru.shape)
            n1 = cv2.remap(L["ripple"], ((ru + t * 9) % 1024).astype(f32), ((rv + t * 13) % 1024).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            n2 = cv2.remap(L["ripple"], ((ru * 2.3 - t * 17 + 300) % 1024).astype(f32), ((rv * 2.1 - t * 21) % 1024).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            amp = (1.5 + 0.045 * bl) / (s / 1.2)
            mx = (xs + (n1 + 0.6 * n2) * amp * 2.2).astype(f32); my = (2 * yh - yr[y_l:] + (n2 + 0.5 * n1) * amp * 1.3).astype(f32)
            refl = cv2.remap(sky, mx, np.clip(my, 0, H - 1), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            spark = np.clip(n1 * n2 * 1.2 + 0.2, 0, 3) ** 2
            refl = refl * (0.75 + 0.5 * glitter * spark[..., None] * np.clip(refl.max(2, keepdims=True) - 0.8, 0, 6) / 3)
            water_body = np.array([0.010, 0.030, 0.045], f32) * (sun * 1.0 + moon * 0.03 + night * 0.05)
            mir = warp(L["mirror"], s, pcx, pcy)[y_l:]
            sub = lc[y_l:]
            lake_rgb = (sub + refl * (1 - mir)[..., None]) * fres[..., None] + water_body * (1 - fres)[..., None]
            wm = (lake[y_l:] * (1 - (fz if np.isscalar(fz) else fz[y_l:])))[..., None]
            lc[y_l:] = sub * (1 - wm) + lake_rgb * wm
    # ---------------- aerial perspective + low mist
    hz = ((1 - np.exp(-depth / 1000.0)) * air)[..., None]
    if sun > 0: hcol = (horizon_col * 0.5 + np.array([1.0, 0.82, 0.6], f32) * warm[..., None] * 0.55) * sun
    else: hcol = np.array([0.5, 0.65, 1.0], f32) * (0.03 * moon + (0.004 + haze_night) * night)
    lc = lc * (1 - hz) + hcol * hz
    al = alpha[..., None]
    img = sky * (1 - al) + lc * al
    if mist > 0:
        mu_ = (xx / W * 900 + t * 5.0) % 2048; mv = ((yy - yh) * 1.4 + 256 + 30 * np.sin(xx / 300 + t * 0.05)) % 512
        mn = cv2.remap(L["mist"], mu_.astype(f32), mv.astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        d2 = depth[::2, ::2]
        band = np.exp(-((yy - (yh + 14 / s * 1.2)) / (38 / s * 1.2)) ** 2) * np.clip((d2 - 12) / 40, 0, 1) + 0.35 * np.exp(-((yy - (yh + 120 / s)) / (150 / s)) ** 2) * np.clip((yy - yh) / 40, 0, 1)
        md = up(np.clip(mn * 1.5 - 0.25, 0, 1) * band * mist)[..., None]
        mc = horizon_col * 0.6 * sun + np.array([0.52, 0.66, 1.0], f32) * (0.10 * moon + 0.028 * night)
        img = img * (1 - md * 0.85) + mc * md
    if flakes > 0:
        fl = particles(t, flake_n, fall=0.035, sway=0.006, bright=flakes, drift=0.004)
        img += fl[..., None] * (np.array([0.75, 0.86, 1.0], f32) * (0.5 * night + 0.5 * moon) + np.array([1, 1, 1], f32) * sun)
    return img, (s, pcx, pcy)


_scr = []
def scrim():
    """gentle darkening behind the clock (top-left) and the caption (bottom-left) for bright daylight plates"""
    if not _scr:
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        a = np.exp(-(((xx - 150) / 620) ** 2 + ((yy - 60) / 190) ** 2)) * 0.30 + np.exp(-(((xx - 300) / 900) ** 2 + ((yy - 990) / 170) ** 2)) * 0.50
        _scr.append((1 - a)[..., None])
    return _scr[0]

# ------------------------------------------------------------------------------------------------ shots
def sh_sun(t, ov):
    """0 - 3.3 s: the Sun, then nothing."""
    img = sky_view(1500, 700, 0.8, 8) * 0.9
    k = 1.0 if t < TV else 0.0
    R = 300 + 16 * t
    if k: sun_disc(img, 1010, 548, R, t * 6 + 40, power=1.0)
    else:
        a = math.exp(-(t - TV) / 0.09)                                   # afterimage: a few frames
        if a > 0.01:
            yy, xx = np.mgrid[0:H, 0:W].astype(f32); d = np.hypot(xx - 1010, yy - 548)
            img += (np.exp(-(d / (R * 1.02)) ** 8) * 0.035 * a)[..., None] * np.array([0.6, 0.75, 1.0], f32)
    clock(ov, hms(max(0, t - TV)), a=fade(t, TV + 0.05, 99, 0.3))
    return img, 1.0

EARTH_L = norm([-0.80, 0.26, 0.42])
def sh_earth1(t, ov):
    """3.1 - 18: the Earth, still fully lit. The thumbnail promise: 8 MIN 20 SEC."""
    u = (t - 3.0)
    img = sky_view(1300 + 6 * u, 1300, 0.85, 14) * 0.75
    R = 392 + 3.2 * u
    dim = 1 - 0.45 * ramp(t, 13.8, 15.0)
    earth(img, 1330 + 2.2 * u, 556, R, math.radians(12 + 1.1 * u), EARTH_L, cloud_t=0.004 * u, expo=1.0)
    img *= dim
    clock(ov, hms(t - TV))
    a = fade(t, 3.9, 13.4, 0.5, 0.8)
    if a > 0:
        x0 = 96; ov.text(x0, 392, "8 MIN 20 SEC", size=118, wt="ExtraLight", col=YEL, a=a, track=0.06, display=True)
        ov.text(x0 + 4, 548, "THEN EVERYTHING CHANGES", size=27, wt="Light", col=WHT, a=a * fade(t, 5.6, 99, 0.7), track=0.26)
        ov.text(x0 + 4, 606, "SUNLIGHT ALREADY ON ITS WAY KEEPS ARRIVING", size=15, wt="Regular", col=DIM, a=a * fade(t, 8.0, 99, 0.7), track=0.26)
    a = fade(t, 14.3, 18.0, 0.9, 0.01)
    if a > 0:
        ov.text(96, 430, "IF THE SUN VANISHED", size=58, wt="ExtraLight", col=WHT, a=a, track=0.16, display=True)
        ov.text(98, 524, "RIGHT NOW", size=58, wt="ExtraLight", col=YEL, a=a * fade(t, 15.1, 99, 0.8), track=0.16, display=True)
    return img, 1.0

def sh_land_day(t, ov):
    """18 - 31: the Sun still shines over the lake (real-time clock)."""
    u = (t - 18.0) / 13.0
    img, yh = land(t, s=1.165 - 0.07 * ease(u), pcx=PW / 2 - 40 * u, pcy=PH / 2 - 10 * u, sun=1.0, mist=0.0)
    img = np.power(np.maximum(img, 0), 1.16) * np.array([1.12, 1.06, 0.98], f32) * scrim()
    clock(ov, hms(t - TV))
    caption(ov, t, 22.6, 30.6, "THE SUNLIGHT YOU SEE LEFT THE SUN 8 MIN 20 SEC AGO", "149.6 MILLION KM  ·  AT 299,792 KM/S")
    return img, 1.12

# ---- solar-system diagram
AU = 470.0; TILT = math.radians(63); DCX, DCY = 960, 600
ORB = dict(mercury=(0.387, 2.3, 47.4, (0.75, 0.72, 0.68)), venus=(0.723, 3.9, 35.0, (1.0, 0.92, 0.75)), earth=(1.0, 5.45, 29.78, (0.45, 0.65, 1.0)), mars=(1.524, 0.75, 24.1, (1.0, 0.55, 0.35)))
def dproj(x, y, zoom=1.0, cx=DCX, cy=DCY):
    return cx + x * AU * zoom, cy - y * AU * zoom * math.cos(TILT)
def ring_pts(r, zoom=1.0, n=361, cx=DCX, cy=DCY, a0=0.0, a1=2 * math.pi):
    return [dproj(r * math.cos(a), r * math.sin(a), zoom, cx, cy) for a in np.linspace(a0, a1, n)]
def glow_lines(img, pts, col, wd=1, k=1.0):
    p = np.array(pts, np.float32).reshape(-1, 1, 2) * 16
    lay = np.zeros((H, W, 3), f32); cv2.polylines(lay, [p.astype(np.int32)], False, tuple(float(c) * k for c in col), wd, cv2.LINE_AA, shift=4); img += lay

LT = lambda au: au * 499.005                      # light time in seconds for a distance in AU
def sh_diag_a(t, ov):
    """31 - 48: the edge of the last light (and the last gravity) sweeping outward at c. Distances to scale."""
    Tc = kf(t, [(31.0, 28.6), (33.0, 40.0), (46.6, 478.0), (48.0, 494.1 - 0.0)])       # T (s) shown on the clock, time-lapse
    zoom = 1.0; cx, cy = DCX + 40, DCY - 10
    img = sky_view(2300, 1250, 0.9, 30) * 0.42
    rf = Tc / 499.005                                                    # front radius in AU
    yy, xx = np.mgrid[0:H, 0:W].astype(f32)
    px = (xx - cx) / (AU * zoom); py = -(yy - cy) / (AU * zoom * math.cos(TILT)); r = np.sqrt(px * px + py * py)
    # sunlight still filling space beyond the front (inverse-square-ish haze in the orbital plane), dark inside it
    lit = smooth(rf - 0.012, rf + 0.012, r)
    haze = lit * (0.035 / (r * r + 0.02) + 0.02 / (r + 0.1)) * np.exp(-((r - 1.2) / 1.6) ** 2 * 0.6)
    edge = np.exp(-((r - rf) / 0.014) ** 2) * 0.55 / (rf + 0.25) + np.exp(-np.clip(r - rf, 0, None) / 0.10) * lit * 0.10 / (rf + 0.25)
    img += (haze * 1.3 + edge * 1.6)[..., None] * np.array([1.0, 0.80, 0.50], f32)
    for name, (a, ang, v, col) in ORB.items():
        near = [0.18 + 0.30 * (0.5 - 0.5 * math.sin(th)) for th in np.linspace(0, 2 * math.pi, 361)]
        pts = ring_pts(a, zoom, cx=cx, cy=cy)
        for i in range(0, 360, 6):
            glow_lines(img, pts[i:i + 7], (0.5, 0.62, 0.85), 1, near[i] * 0.7)
        w_ = v / 149597.87 / a * 0.0                                     # orbital motion over 8 minutes is far below one pixel
        X, Y = a * math.cos(ang), a * math.sin(ang); sx, sy = dproj(X, Y, zoom, cx, cy)
        islit = 1.0 if a > rf else 0.0
        Lp = norm([-X, -Y * math.cos(TILT) + 0.0, 0.55])
        if name == "earth":
            earth(img, sx, sy, 15, 1.0, norm([-X, -Y * 0.5, 0.45]), sun=islit, amb=0.03, atmo=0.6)
        else:
            d = np.hypot(xx - sx, yy - sy); rp = {"mercury": 5.5, "venus": 8.5, "mars": 6.5}[name]
            nx = (xx - sx) / rp; ny = -(yy - sy) / rp; nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
            sh = np.clip(nx * Lp[0] + ny * Lp[1] + nz * Lp[2], 0, 1) * islit + 0.02
            img += (np.clip(rp - d + 0.5, 0, 1) * sh * 1.6)[..., None] * np.array(col, f32)
        lab = {"mercury": "MERCURY  ·  3 MIN 13 S", "venus": "VENUS  ·  6 MIN 1 S", "earth": "EARTH  ·  8 MIN 20 S", "mars": "MARS  ·  12 MIN 40 S"}[name]
        al = fade(t, 32.0, 48.5, 0.8, 0.01) * (1.0 if islit else 0.55)
        ov.text(sx + 22, sy - 26, lab, size=14, wt="Regular", col=WHT if islit else DIM, a=al, track=0.24)
    # where the Sun was
    sx, sy = dproj(0, 0, zoom, cx, cy)
    ov.circle(sx, sy, 9, col=DIM, a=0.7, width=1); ov.line([(sx - 4, sy), (sx + 4, sy)], col=DIM, a=0.7, width=1); ov.line([(sx, sy - 4), (sx, sy + 4)], col=DIM, a=0.7, width=1)
    ov.text(sx, sy + 22, "WHERE THE SUN WAS", size=12, wt="Regular", col=DIM, a=fade(t, 31.5, 48.5, 0.8, 0.01), track=0.28, anchor="m")
    ex, ey = dproj(rf * math.cos(2.2), rf * math.sin(2.2), zoom, cx, cy)
    ov.text(ex - 14, ey - 34, "LAST LIGHT", size=14, wt="Regular", col=YEL, a=fade(t, 33.0, 39.5, 0.8, 0.6) * (rf > 0.12), track=0.26, anchor="r")
    clock(ov, hms(Tc))
    caption(ov, t, 38.8, 47.6, "GRAVITY TRAVELS AT THE SPEED OF LIGHT TOO", "SO EARTH KEEPS ORBITING AN EMPTY POINT UNTIL THE SAME FRONT ARRIVES")
    note(ov, t, 32.5, 47.8, "DISTANCES TO SCALE  ·  PLANET SIZES ENLARGED")
    return img, 1.0

def sh_land_dark(t, ov):
    """48 - 59: real time up to 00:08:20, then the sky goes black."""
    Tc = 500.0 + (t - T_DARK)
    on = t < T_DARK
    u = (t - 48.0) / 11.0
    cam = dict(s=1.13 - 0.05 * ease(u), pcx=PW / 2 - 40 + 30 * u, pcy=PH / 2 - 10)
    if on:
        img, yh = land(t, sun=1.0, mist=0.0, **cam); ex = 1.12; img = np.power(np.maximum(img, 0), 1.16) * np.array([1.12, 1.06, 0.98], f32) * scrim()
    else:
        v = t - T_DARK
        adapt = 0.012 + 0.99 * (1 - math.exp(-v / 1.6)) ** 2          # the camera (and your eyes) opening up to starlight
        img, yh = land(t, sun=0.0, night=adapt, mist=0.25, sky_rot=-18, **cam); ex = 1.0
    clock(ov, hms(Tc), col=YEL if (0 <= t - T_DARK < 2.2) else WHT)
    
    return img, ex

def sh_front(t, ov):
    """55.3 - 59: slow-motion replay from space: the edge of the last light crossing the day side (really ~0.02 s)."""
    u = t - 55.3
    L = norm([-0.74, 0.20, 0.64]); cx, cy, R, lon0 = 1250 - 3 * u, 548, 430 + 3 * u, math.radians(8)
    img = sky_view(1500, 1250, 0.85, 14) * 0.7
    front = 1.03 - 1.25 * ramp(t, 55.7, 58.3)
    lit = img.copy(); drk = img.copy()
    earth(lit, cx, cy, R, lon0, L, cloud_t=0.02)
    earth(drk, cx, cy, R, lon0, L, sun=0.0, amb=0.05, lights=1.0, lights_day=0.0, cloud_t=0.02)
    yy, xx = np.mgrid[0:H, 0:W].astype(f32)
    uu = (xx - cx) / R; vv = -(yy - cy) / R; rr = uu * uu + vv * vv; z = np.sqrt(np.clip(1 - rr, 0, 1)); ndl = uu * L[0] + vv * L[1] + z * L[2]
    m = smooth(front - 0.012, front + 0.012, ndl)[..., None]; inside = (rr < 1.0)[..., None]
    planet = lit * (1 - m) + drk * m
    edge = np.exp(-((ndl - front) / 0.012) ** 2)[..., None] * inside * np.array([1.0, 0.75, 0.35], f32) * 0.9
    halo_keep = (1 - smooth(front - 0.2, front + 0.1, ndl)[..., None] * (~inside)) * (1.0 if front > -0.15 else 0.0)
    aa = np.clip((1 - np.sqrt(rr)) * R + 0.5, 0, 1)[..., None]
    img = (lit * halo_keep + img * (1 - halo_keep)) * (1 - aa) + planet * aa + edge * aa
    clock(ov, hms(500), col=YEL)
    caption(ov, t, 55.5, 58.9, "THE WHOLE DAY SIDE, AT ONCE", "SLOW MOTION  ·  IN REAL TIME THIS TAKES ≈ 0.02 SECONDS", y=880)
    return img, 1.0

def sh_diag_b(t, ov):
    """59 - 72: with the pull gone, every planet leaves along the tangent to its old orbit (time-lapse: days)."""
    days = kf(t, [(59.0, 0.0), (61.5, 0.4), (71.0, 46.0), (72.0, 48.0)])
    zoom = 1.0; cx, cy = DCX - 150, DCY + 60
    img = sky_view(2300, 1250, 0.9, 30) * 0.5
    yy, xx = np.mgrid[0:H, 0:W].astype(f32)
    for name, (a, ang, v, col) in ORB.items():
        pts = ring_pts(a, zoom, cx=cx, cy=cy)
        ov.line(pts, col=(150, 170, 205), a=0.85 if name == "earth" else 0.45, width=1.2, dash=(8, 7))
        dist = v * 86400 * days / 149597870.7                           # AU travelled in a straight line
        X0, Y0 = a * math.cos(ang), a * math.sin(ang); tx, ty = -math.sin(ang), math.cos(ang)
        X, Y = X0 + tx * dist, Y0 + ty * dist
        s0 = dproj(X0, Y0, zoom, cx, cy); s1 = dproj(X, Y, zoom, cx, cy)
        if dist > 0.002:
            glow_lines(img, [s0, s1], (0.55, 0.75, 1.0) if name == "earth" else (0.45, 0.5, 0.6), 2, 4.0 if name == "earth" else 1.4)
        if name == "earth":
            earth(img, s1[0], s1[1], 17, 1.0, norm([0, 0, 1]), sun=0.0, amb=0.9, lights=1.0, lights_day=1.0)
            al = fade(t, 60.5, 72.5, 0.8, 0.01)
            ov.text(s1[0] + 28, s1[1] - 34, "EARTH + MOON", size=16, wt="Regular", col=WHT, a=al, track=0.24)
            ov.text(s1[0] + 28, s1[1] - 8, "≈ 30 KM/S  ·  ≈ 107,000 KM/H", size=16, wt="Regular", col=YEL, a=al * fade(t, 64.5, 99, 0.8), track=0.2)
            ov.text(s0[0] - 16, s0[1] + 16, "FORMER ORBIT", size=12, wt="Regular", col=DIM, a=al * 0.9, track=0.28, anchor="r")
        else:
            d = np.hypot(xx - s1[0], yy - s1[1]); rp = {"mercury": 4.5, "venus": 7, "mars": 5.5}[name]
            img += (np.clip(rp - d + 0.5, 0, 1) * 0.30)[..., None] * np.array(col, f32)
            ov.text(s1[0] + 16, s1[1] - 22, name.upper(), size=12, wt="Regular", col=DIM, a=fade(t, 60.5, 72.5, 0.8, 0.01) * 0.85, track=0.26)
    sx, sy = dproj(0, 0, zoom, cx, cy)
    ov.circle(sx, sy, 9, col=DIM, a=0.6, width=1); ov.line([(sx - 4, sy), (sx + 4, sy)], col=DIM, a=0.6, width=1); ov.line([(sx, sy - 4), (sx, sy + 4)], col=DIM, a=0.6, width=1)
    if days < 1: clock(ov, hms(500 + days * 86400))
    else: clock(ov, f"DAY {int(days)}")
    caption(ov, t, 62.2, 71.3, "NO PULL, NO ORBIT:  A STRAIGHT LINE", "EACH PLANET LEAVES ALONG THE TANGENT, AT THE SPEED IT ALREADY HAD")
    note(ov, t, 60.5, 71.6, "DISTANCES TO SCALE  ·  PLANET SIZES ENLARGED  ·  TIME-LAPSE")
    return img, 1.0

T_MOON = 77.7
def sh_moon(t, ov):
    """72 - 80.5: the Moon, lit only by the Sun, fades about two seconds after the sky does."""
    u = t - 72.0
    Tc = 502.6 + (t - T_MOON)
    on = 1 - ramp(t, T_MOON, T_MOON + 0.35)
    img = sky_view(1650 + 3 * u, 1500, 0.8, -12) * (0.55 + 0.6 * (1 - on))
    moon(img, 1180 - 5 * u, 545, 372 + 3.0 * u, norm([-0.62, 0.22, 0.75]), sun=on, lon0=math.radians(-4 + 0.15 * u), amb=0.0035 * (1 - on) + 0.0006)
    clock(ov, hms(Tc))
    caption(ov, t, 73.2, 80.2, "MOONLIGHT IS REFLECTED SUNLIGHT", "A FULL MOON GOES DARK ≈ 2.6 S AFTER THE SKY  ·  OTHER PHASES SOONER", y=880)
    return img, 1.0

PLAN = [  # az, el (deg), flux, colour, name, film time it goes out, label
    (-8.0, 11.5, 9.0, (1.0, 0.97, 0.88), "VENUS", 92.3), (5.0, 15.0, 1.6, (1.0, 0.62, 0.38), "MARS", 93.7),
    (16.5, 18.6, 4.2, (1.0, 0.93, 0.80), "JUPITER", 999), (24.5, 20.6, 0.9, (1.0, 0.9, 0.68), "SATURN", 999)]
def sh_planets(t, ov):
    """80.5 - 94.3: night side; the planets still shine by sunlight that left before the Sun did."""
    u = (t - 80.5) / 13.8
    Tc = kf(t, [(80.5, 510.0), (82.0, 540.0), (94.3, 1900.0)])
    pl = [(az, el, fx, col, 1 - ramp(t, tout, tout + 0.5)) for (az, el, fx, col, nm, tout) in PLAN]
    s = 1.165 - 0.05 * ease(u); pcx, pcy = PW / 2 + 60 * u, PH / 2 - 30 - 20 * u
    img, (s, pcx, pcy) = land(t, s=s, pcx=pcx, pcy=pcy, sun=0, night=1.0, mist=0.5, sky_rot=-18 - 0.25 * (t - 80.5), planets=pl)
    a0 = fade(t, 81.6, 94.4, 0.9, 0.01)
    pts = []
    for (az, el, fx, col, nm, tout) in PLAN:
        px, py = plate_xy(math.radians(az), math.radians(el)); fx_, fy_ = (px - pcx) / s + W / 2, (py - pcy) / s + H / 2; pts.append((fx_, fy_))
        on = 1 - ramp(t, tout, tout + 0.5)
        ov.text(fx_ + 16, fy_ - 30, nm, size=13, wt="Regular", col=WHT if on > 0.5 else DIM, a=a0 * (0.35 + 0.65 * on), track=0.28)
        if on < 0.5: ov.circle(fx_, fy_, 7, col=DIM, a=a0 * 0.6, width=1)
    ext = [(pts[0][0] - 3 * (pts[1][0] - pts[0][0]), pts[0][1] - 3 * (pts[1][1] - pts[0][1]))] + pts + [(pts[-1][0] + 2 * (pts[-1][0] - pts[-2][0]), pts[-1][1] + 2 * (pts[-1][1] - pts[-2][1]))]
    clock(ov, hms(Tc))
    caption(ov, t, 83.0, 90.3, "THE PLANETS ONLY REFLECT SUNLIGHT", "THEIR LAST LIGHT IS STILL ON ITS WAY TO US")
    caption(ov, t, 91.3, 94.3, "VENUS, MARS:  DARK WITHIN ≈ 30 MIN", "EXACT TIMES DEPEND ON WHERE EACH PLANET IS", )
    return img, 1.0

def sh_jupiter(t, ov):
    """94.3 - 97.9: Jupiter keeps shining for more than an hour (70-87 min after our sky goes dark)."""
    u = t - 94.3; tout = 97.15
    Tc = kf(t, [(94.3, 4380.0), (tout, 5100.0), (97.9, 5106.0)])
    on = 1 - ramp(t, tout, tout + 0.3)
    img = sky_view(900 + 4 * u, 600, 0.8, 40) * 0.6
    gas_giant(img, "jupiter", 1150 - 6 * u, 540, 330 + 5 * u, norm([-0.45, 0.12, 0.88]), sun=on, lon0=1.2 + 0.05 * u, oblate=0.935, amb=0.0012)
    clock(ov, hms(Tc))
    caption(ov, t, 94.5, 97.9, "JUPITER:  MORE THAN AN HOUR", "≈ 70–87 MIN AFTER OUR SKY GOES DARK", y=880)
    return img, 1.0

def sh_saturn(t, ov):
    """97.9 - 101.6: Saturn, more than two hours (about 143-160 min after dark)."""
    u = t - 97.9; tout = 100.65
    Tc = kf(t, [(97.9, 9000.0), (tout, 9600.0), (101.6, 9606.0)])
    on = 1 - ramp(t, tout, tout + 0.4)
    img = sky_view(2900 - 4 * u, 800, 0.8, -30) * 0.6
    gas_giant(img, "saturn", 1100 + 5 * u, 540, 200 + 3 * u, norm([-0.5, 0.28, 0.82]), sun=on, lon0=0.4, oblate=0.902, tip=21, tilt=-9, ring=True, amb=0.0012)
    clock(ov, hms(Tc))
    caption(ov, t, 98.1, 101.6, "SATURN:  MORE THAN TWO HOURS", "≈ 2 H 25 MIN – 2 H 40 MIN AFTER DARK", y=880)
    return img, 1.0

def sh_stars(t, ov):
    """101.6 - 110.5: only the stars."""
    u = (t - 101.6) / 8.9
    img, yh = land(t, s=1.15 - 0.10 * ease(u), pcx=PW / 2 + 60 - 40 * u, pcy=PH / 2 - 50 - 40 * ease(u), sun=0, night=1.0, mist=0.5, sky_rot=-18 - 0.25 * (t - 80.5), sky_gain=1.0 + 0.25 * u)
    clock(ov, hms(kf(t, [(101.6, 9700.0), (110.5, 10800.0)])))
    caption(ov, t, 104.6, 109.9, "THE STARS ARE OTHER SUNS", "THE NEAREST IS 4.2 LIGHT-YEARS AWAY")
    return img, 1.0

def daystr(d):
    return f"DAY {int(d)}" if d < 365 else (f"YEAR {d / 365.25:.0f}")
def sh_cold_land(t, ov):
    """110.5 - 138: the same lake, days going by; plants stop, frost arrives."""
    u = (t - 110.5) / 27.5
    days = kf(t, [(110.5, 1.0), (129.0, 4.0), (138.0, 8.0)])
    fr = 0.62 * ramp(t, 126.5, 138.5)
    img, yh = land(t, s=1.165 - 0.10 * u, pcx=PW / 2 - 70 + 60 * u, pcy=PH / 2 + 20 - 20 * u, sun=0, night=1.25, mist=0.5 + 0.5 * ramp(t, 124, 136), sky_rot=-60 - 0.25 * (t - 110.5),
                   sky_c=(1900, 1250), frost=fr, dead=ramp(t, 113, 128), flakes=0.12 * ramp(t, 130, 137), flake_n=2500)
    img *= 1 - (1 - scrim()) * ramp(t, 128, 136)
    clock(ov, daystr(days))
    caption(ov, t, 112.0, 119.2, "PHOTOSYNTHESIS STOPS", "ON LAND AND IN THE SEA  ·  THE BASE OF ALMOST EVERY FOOD CHAIN")
    caption(ov, t, 120.4, 128.6, "SMALL PLANTS:  WEEKS.   LARGE TREES:  POSSIBLY YEARS", "ON STORED SUGAR  ·  IF THEY DID NOT FREEZE FIRST")
    caption(ov, t, 131.0, 137.6, "EARTH'S HEAT RADIATES AWAY INTO SPACE", "NOTHING REPLACES IT")
    note(ov, t, 111.5, 137.5, "NIGHT SCENES BRIGHTENED FOR VISIBILITY")
    return img, 1.0

def sh_globe_cold(t, ov):
    """138 - 167.5: the dark Earth freezing; temperatures are rough model estimates."""
    u = t - 138.0
    days = kf(t, [(138.0, 6.0), (143.0, 7.0), (147.5, 8.0), (156.0, 365.0), (167.5, 900.0)])
    fr = kf(t, [(138.0, 0.10), (147.0, 0.22), (156.5, 0.62), (167.5, 0.80)])
    li = kf(t, [(138.0, 1.0), (157.0, 0.85), (164.5, 0.07), (167.5, 0.05)])
    img = sky_view(2500 - 3 * u, 1050, 0.85, -35) * 0.8
    earth(img, 1260 - 2.0 * u, 548, 400 + 1.6 * u, math.radians(-95 + 0.8 * u), norm([-0.6, 0.3, 0.6]), sun=0.0, amb=0.075, frost=fr, lights=li, lights_day=1.0,
          cloud_amt=max(0.0, 1 - u / 22.0), cloud_t=0.004 * u, veg=0.0)
    clock(ov, daystr(days) if days < 360 else "YEAR 1" if days < 400 else f"YEAR {days / 365.25:.0f}")
    a = fade(t, 141.3, 156.6, 0.7, 0.8)
    if a > 0:
        ov.text(96, 372, "≈ 1 WEEK", size=17, wt="Regular", col=DIM, a=a, track=0.3)
        ov.text(96, 400, "BELOW 0 °C", size=54, wt="ExtraLight", col=WHT, a=a, track=0.08, display=True)
        ov.text(98, 474, "MOST QUOTED FIGURE:  ≈ −18 °C", size=15, wt="Regular", col=DIM, a=a * fade(t, 145.0, 99, 0.7), track=0.26)
        a2 = a * fade(t, 149.6, 99, 0.7)
        ov.text(96, 560, "≈ 1 YEAR", size=17, wt="Regular", col=DIM, a=a2, track=0.3)
        ov.text(96, 588, "≈ −70 °C", size=54, wt="ExtraLight", col=YEL, a=a2, track=0.08, display=True)
        ov.text(98, 662, "COLDER THAN A SOUTH POLE WINTER  (≈ −60 °C)", size=15, wt="Regular", col=DIM, a=a2 * fade(t, 152.6, 99, 0.7), track=0.26)
    caption(ov, t, 139.0, 156.6, "GLOBAL AVERAGE SURFACE TEMPERATURE", "ROUGH ESTIMATES  ·  SOURCES DISAGREE", y=250, size=17)
    caption(ov, t, 158.0, 166.6, "A FEW REFUGES:  NUCLEAR AND GEOTHERMAL HEAT", "ENERGY THAT NEVER CAME FROM THE SUN")
    note(ov, t, 139.0, 166.8, "DARK EARTH BRIGHTENED FOR VISIBILITY  ·  ICE COVER SCHEMATIC")
    return img, 1.0

_oc = {}
def ocean_plates():
    if _oc: return _oc
    P = os.path.join(SCR, "plates")
    for n in ("ice", "vent"):
        _oc[n] = srgb_dec(cv2.imread(f"{P}/{n}_rgb.png", cv2.IMREAD_UNCHANGED).astype(f32)[..., 2::-1] / 65535)
        _oc[n + "_d"] = srgb_dec(cv2.imread(f"{P}/{n}_depth.png", cv2.IMREAD_UNCHANGED).astype(f32)[..., 1] / 65535) * 60.0
    for n in ("ice", "vent"): _oc[n + "_d"][_oc[n + "_d"] < 0.05] = 60.0
    _oc["vj"] = json.load(open(f"{P}/vent.json"))
    _oc["smoke"] = np.clip(fbm2((1024, 1024), 201, 2.6) * 0.5 + 0.5, 0, 1); _oc["smoke2"] = np.clip(fbm2((1024, 1024), 202, 2.2) * 0.5 + 0.5, 0, 1)
    _oc["warp"] = fbm2((512, 512), 203, 2.2)
    return _oc

def water(rgb, depth, t, lamp=1.0, snow=0.25, k=(0.060, 0.022, 0.014)):
    """absorption + back-scatter by distance, drifting particles ('marine snow') at three depths"""
    tr = np.exp(-np.multiply.outer(depth, np.array(k, f32) * 2.0))
    img = rgb * tr * lamp + np.array([0.004, 0.016, 0.028], f32) * (1 - tr[..., 2:3]) * lamp
    fl = particles(t, 900, fall=-0.006, sway=0.004, bright=snow * 0.22, size=0.8, drift=0.006)
    img += fl[..., None] * np.array([0.75, 0.92, 1.0], f32) * lamp
    return img

def sh_ice(t, ov):
    """167.5 - 182.2: under the ice lid."""
    O = ocean_plates(); u = (t - 167.5) / 14.7
    s, pcx, pcy = clampc(1.165 - 0.14 * ease(u) - 0.02 * u, PW / 2 + 30 - 60 * u, PH / 2 - 60 + 90 * ease(u))
    rgb = warp(O["ice"], s, pcx, pcy); d = warp(O["ice_d"], s, pcx, pcy)
    yy, xx = np.mgrid[0:H, 0:W].astype(f32)
    sweep = 0.55 + 0.6 * np.exp(-(((xx - (700 + 500 * math.sin(t * 0.21))) / 900) ** 2 + ((yy - 430) / 620) ** 2))
    img = water(rgb * sweep[..., None] * 1.5, d, t, snow=0.22)
    clock(ov, "YEAR 10" if t < 175 else "YEAR 100" if t < 179 else "YEAR 1,000")
    caption(ov, t, 169.2, 175.0, "THE OCEAN FREEZES FROM THE TOP DOWN", "ICE FLOATS  ·  AND INSULATES THE WATER BELOW")
    caption(ov, t, 175.8, 181.9, "LIQUID FOR HUNDREDS OF THOUSANDS OF YEARS", "ONE ESTIMATE  ·  KEPT FROM FREEZING BY THE LID AND BY HEAT FROM BELOW")
    note(ov, t, 168.2, 182.0, "UNDERSIDE OF THE ICE  ·  LIT BY OUR OWN LAMP")
    return img, 1.0

def sh_vent(t, ov):
    """182.2 - 200.5: hydrothermal vents; chemosynthetic microbes."""
    O = ocean_plates(); u = (t - 182.2) / 18.3
    s, pcx, pcy = clampc(1.165 - 0.13 * ease(u) - 0.02 * u, PW / 2 - 50 + 70 * u, PH / 2 + 50 - 70 * ease(u))
    yy, xx = np.mgrid[0:H:2, 0:W:2].astype(f32)
    xp = pcx + (xx - W / 2) * s; yp = pcy + (yy - H / 2) * s
    # plumes: turbulent, widening columns rising from each chimney mouth (density field in plate space)
    dens = np.zeros(xx.shape, f32); shim = np.zeros(xx.shape, f32)
    for i, m in enumerate(O["vj"]["mouths"]):
        if m["r"] < 6: continue
        up = (m["y"] - yp); r0 = m["r"] * 1.2
        hgt = np.clip(up, 0, None)
        wdt = r0 * 0.9 + hgt * 0.13
        off = 26 * np.sin(hgt / 130.0 + t * 0.35 + i) * np.clip(hgt / 300, 0, 1) + hgt * 0.07
        lat = (xp - m["x"] - off) / wdt
        sc_ = 220.0 / max(m["r"], 8)
        n1 = cv2.remap(O["smoke"], (((xp - m["x"]) * sc_ * 0.012 + i * 137) % 1024).astype(f32), ((yp * sc_ * 0.008 + t * (14 + 2 * i)) % 1024).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        n2 = cv2.remap(O["smoke2"], (((xp - m["x"]) * sc_ * 0.035 + i * 61) % 1024).astype(f32), ((yp * sc_ * 0.025 + t * (30 + 3 * i)) % 1024).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        core = np.exp(-(lat * lat) * 1.6) * smooth(-r0 * 0.4, r0 * 0.6, up) * np.exp(-hgt / (m["r"] * 26))
        dd = core * np.clip(0.15 + 1.5 * n1 * (0.7 + 0.6 * n2), 0, 1.5)
        dens = np.maximum(dens, np.clip(dd, 0, 1)); shim = np.maximum(shim, np.exp(-(lat * lat) * 0.6) * (up > 0) * np.exp(-hgt / (m["r"] * 60)))
    dens = cv2.resize(dens, (W, H)); shim = cv2.resize(shim, (W, H)); yy, xx = np.mgrid[0:H, 0:W].astype(f32)
    xp = pcx + (xx - W / 2) * s; yp = pcy + (yy - H / 2) * s
    # heat shimmer: refract the plate around the plumes
    wn = cv2.remap(O["warp"], ((xx * 0.5 + t * 30) % 512).astype(f32), ((yy * 0.5 + t * 55) % 512).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    M = np.array([[s, 0, pcx - s * W / 2], [0, s, pcy - s * H / 2]])
    mx = (xp + wn * shim * 5.0).astype(f32); my = (yp + wn * shim * 3.0).astype(f32)
    rgb = cv2.remap(O["vent"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE); d = cv2.remap(O["vent_d"], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    sweep = 0.6 + 0.55 * np.exp(-(((xx - (880 + 380 * math.sin(t * 0.17 + 1))) / 800) ** 2 + ((yy - 520) / 600) ** 2))
    base = rgb * sweep[..., None] * 1.35
    lit_smoke = np.array([0.16, 0.16, 0.165], f32) * (0.5 + 0.8 * (1 - np.clip(dens, 0, 1)))[..., None] * sweep[..., None]
    a = np.clip(dens * 1.25, 0, 0.93)[..., None]
    base = base * (1 - a) + lit_smoke * a
    d = d * (1 - a[..., 0]) + 13.0 * a[..., 0]
    img = water(base, d, t, snow=0.30, k=(0.040, 0.020, 0.016))
    clock(ov, "YEAR 1,000" if t < 190 else "YEAR 10,000" if t < 195.5 else "YEAR 100,000")
    caption(ov, t, 186.6, 192.8, "HYDROTHERMAL VENTS", "MINERAL-RICH WATER, HEATED INSIDE THE PLANET")
    caption(ov, t, 193.4, 200.0, "MICROBES THAT LIVE ON CHEMICAL ENERGY", "CHEMOSYNTHESIS  ·  NO SUNLIGHT REQUIRED")
    note(ov, t, 183.0, 200.2, "ILLUSTRATIVE VENT FIELD  ·  LIT BY OUR OWN LAMP")
    return img, 1.0

def sh_air(t, ov):
    """200.5 - 241.5: the frozen lake; the air itself condenses and falls."""
    u = (t - 200.5) / 41.0
    air = 1 - 0.97 * ramp(t, 214.0, 236.0)
    fl = kf(t, [(200.5, 0.14), (211.0, 0.24), (215.0, 0.55), (226.0, 0.62), (233.0, 0.10), (238.0, 0.0)])
    if t < 212.0: s, pcx, pcy = 1.165 - 0.04 * (t - 200.5) / 11.5, PW / 2 + 40, PH / 2
    elif t < 227.6: v = (t - 212.0) / 15.6; s, pcx, pcy = 0.98 - 0.05 * v, PW / 2 - 260 + 50 * v, PH / 2 - 70 - 10 * v
    else: v = (t - 227.6) / 13.9; s, pcx, pcy = 1.165 - 0.05 * v, PW / 2 - 30 + 30 * v, PH / 2 - 20
    img, yh = land(t, s=s, pcx=pcx, pcy=pcy, sun=0, night=1.35, frost=1.0, mist=0.45 * air, sky_rot=-100 - 0.2 * (t - 200.5), sky_c=(2050, 1150),
                   flakes=fl, flake_n=6000, air=air, haze_night=0.006 * air, sky_gain=1.0 + 0.4 * (1 - air))
    img *= scrim()
    clock(ov, "DECADES ON" if t < 228.0 else "MILLIONS OF YEARS ON", label="TIME SINCE THE SUN VANISHED  ·  ESTIMATES VARY WIDELY")
    caption(ov, t, 204.0, 211.4, "THE AIR ITSELF BEGINS TO CONDENSE", "WHEN:  ESTIMATES RUN FROM DECADES TO FAR LONGER")
    caption(ov, t, 213.4, 220.4, "OXYGEN LIQUEFIES AT −183 °C", "AT NORMAL PRESSURE")
    caption(ov, t, 220.9, 227.2, "NITROGEN AT −196 °C", "THE ATMOSPHERE FALLS AS RAIN, THEN AS SNOW")
    caption(ov, t, 230.2, 240.2, "≈ −240 °C  ·  ABOUT 35 DEGREES ABOVE ABSOLUTE ZERO", "HELD THERE BY THE SLOW LEAK OF HEAT FROM EARTH'S INTERIOR", col=WHT)
    note(ov, t, 201.5, 240.5, "NIGHT SCENE BRIGHTENED FOR VISIBILITY")
    return img, 1.0

def sh_drift(t, ov):
    """241.5 - 252.6: a dark frozen world among the stars."""
    u = (t - 241.5) / 11.0
    img = sky_view(2050 + 30 * u, 1060 + 10 * u, 0.95, -24 + 2 * u) * (1.1 + 0.3 * u)
    R = 300 * (1 - 0.86 * ease(u)) + 10
    earth(img, 960 + 120 * ease(u), 540 - 20 * ease(u), R, math.radians(40 + 12 * u), norm([-0.5, 0.35, 0.7]), sun=0.0, amb=0.16, frost=1.0, lights=0.0, cloud_amt=0.0, atmo=0.0)
    img *= 1 - ramp(t, 250.2, 252.4)
    clock(ov, "MILLIONS OF YEARS ON", a=1 - ramp(t, 249.5, 251.0), label="TIME SINCE THE SUN VANISHED  ·  ESTIMATES VARY WIDELY")
    caption(ov, t, 243.6, 250.0, "A ROGUE PLANET", "STARLESS WORLDS LIKE THIS ARE THOUGHT TO BE COMMON IN THE GALAXY")
    return img, 1.0

def sh_sunrise(t, ov):
    """252.6 - 262.5: it cannot happen - the Sun rises over the limb, seen from orbit."""
    u = (t - 252.6) / 9.9
    img = sky_view(1500, 800, 0.8, 0) * 0.5 * (1 - 0.8 * ramp(t, 254.0, 257.0))
    cx, cy, R = 1010, 1610, 1150
    rise = ease((t - 253.2) / 8.5)
    ang = math.radians(101 - 5 * rise)                               # position angle of the Sun around the limb
    rad = R * (0.985 + 0.105 * rise)
    sx, sy = cx + rad * math.cos(ang), cy - rad * math.sin(ang)
    sun_disc(img, sx, sy, 15, t * 3, power=55.0, corona=0.0)
    yy, xx = np.mgrid[0:H, 0:W].astype(f32); d = np.hypot(xx - sx, yy - sy)
    Lv = norm([math.cos(ang) * 0.30, math.sin(ang) * 0.30, -0.92 + 0.10 * rise])
    earth(img, cx, cy, R, math.radians(-60 + 2 * u), Lv, cloud_t=0.002 * u, lights=1.0, expo=1.0)
    vis = smooth(R * 0.992, R * 1.012, rad)
    img += (vis * (2.2 * np.exp(-d / 26) + 0.55 * np.exp(-d / 110) + 0.10 * np.exp(-d / 420)))[..., None] * np.array([1.0, 0.88, 0.70], f32)
    img *= ramp(t, 252.6, 253.6)
    caption(ov, t, 254.2, 261.9, "NONE OF THIS WILL HAPPEN", "MASS AND ENERGY ARE CONSERVED  ·  A STAR CANNOT SIMPLY DISAPPEAR")
    return img, 1.0

def sh_sun2(t, ov):
    """262.5 - 270.8: the Sun, about half-way through its life."""
    u = t - 262.5
    img = sky_view(1500, 700, 0.8, 8) * 0.8
    sun_disc(img, 1240 - 6 * u, 540, 350 + 5 * u, t * 6, power=1.0)
    a = fade(t, 263.6, 270.6, 0.8, 0.6)
    ov.text(96, 388, "≈ 4.6 BILLION YEARS OLD", size=17, wt="Regular", col=DIM, a=a, track=0.3)
    ov.text(96, 420, "≈ 5 BILLION", size=84, wt="ExtraLight", col=YEL, a=a * fade(t, 265.6, 99, 0.7), track=0.06, display=True)
    ov.text(100, 532, "YEARS OF STEADY LIGHT STILL AHEAD", size=24, wt="Light", col=WHT, a=a * fade(t, 266.6, 99, 0.7), track=0.26)
    return img, 1.0

def sh_end(t, ov):
    """270.8 - 287: morning over the lake."""
    u = (t - 270.8) / 16.2
    img, yh = land(t, s=1.165 - 0.09 * ease(u), pcx=PW / 2 - 20 - 30 * u, pcy=PH / 2 - 10 - 10 * u, sun=1.0, mist=0.05)
    img = np.power(np.maximum(img, 0), 1.16) * np.array([1.12, 1.06, 0.98], f32) * scrim()
    k = 1 - ramp(t, 281.0, 285.6)
    caption(ov, t, 274.6, 280.4, "THIS LIGHT IS 8 MIN 20 SEC OLD", "AND IT IS STILL COMING")
    a = fade(t, 281.6, 287.5, 1.0, 0.01)
    if a > 0:
        ov.text(W / 2, 478, "IF THE SUN VANISHED RIGHT NOW", size=34, wt="Light", col=WHT, a=a, track=0.34, anchor="m")
        ov.text(W / 2, 548, "IT WON'T", size=17, wt="Regular", col=YEL, a=a * fade(t, 282.8, 99, 0.8), track=0.4, anchor="m")
    return img * k, 1.12


SHOTS = [  # start, function, cross-fade-in seconds
    (0.0, sh_sun, 0), (3.1, sh_earth1, 0.9), (18.0, sh_land_day, 0.8), (31.0, sh_diag_a, 1.0), (48.0, sh_land_dark, 0.8), (55.3, sh_front, 0.0), (59.0, sh_diag_b, 1.0),
    (72.0, sh_moon, 0.8), (80.5, sh_planets, 1.0), (94.3, sh_jupiter, 0.0), (97.9, sh_saturn, 0.0), (101.6, sh_stars, 0.0), (110.5, sh_cold_land, 1.2),
    (138.0, sh_globe_cold, 1.2), (167.5, sh_ice, 1.2), (182.2, sh_vent, 1.4), (200.5, sh_air, 1.4), (241.5, sh_drift, 1.4), (252.6, sh_sunrise, 0.0),
    (262.5, sh_sun2, 1.0), (270.8, sh_end, 1.2)]


def finish(img, expo, ov):
    y = tonemap(anamorphic(bloom(img), thr=3.0, amt=0.035), expo)
    y = ov.apply(y)
    return y

def frame(t):
    i = max(k for k, sh in enumerate(SHOTS) if sh[0] <= t + 1e-6)
    t0, fn, xf = SHOTS[i]
    ov = Overlay(); img, ex = fn(t, ov); y = finish(img, ex, ov)
    if xf > 0 and t < t0 + xf and i > 0:
        ov2 = Overlay(); img2, ex2 = SHOTS[i - 1][1](t, ov2); y2 = finish(img2, ex2, ov2)
        k = ease((t - t0) / xf); y = y2 * (1 - k) + y * k
    if t < 0.5: y = y * (t / 0.5)
    return (np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    if sys.argv[1] == "still":
        for a in sys.argv[2:]:
            t = float(a); fr = frame(t)
            cv2.imwrite(f"{SCR}/chk/f_{t:07.2f}.jpg", fr[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 93]); print("wrote", t, flush=True)
    else:
        a, b = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(a * FPS)), int(round(b * FPS))
        out = f"{SCR}/seg/seg_{f0:05d}.mp4"
        if os.path.exists(out): print("exists", out); sys.exit(0)
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p", "-threads", "2", out + ".part.mp4"], stdin=subprocess.PIPE)
        import time; T0 = time.time()
        # Slow shots are rendered every 2nd or 3rd frame and the frames between are linear blends (motion there is well under
        # a pixel per frame); anything with fast motion, particles or a hard event is rendered at the full rate.
        EVENTS = [TV, T_DARK, T_MOON, 92.3, 93.7, 97.15, 100.65] + [sh[0] for sh in SHOTS]
        def step(t):
            if any(-0.2 < t - e < 0.6 for e in EVENTS): return 1
            if t < 3.6 or 55.3 <= t < 59.0 or 128.0 <= t < 138.0 or 200.5 <= t < 241.5 or t > 280.5: return 1
            i = max(k for k, sh in enumerate(SHOTS) if sh[0] <= t + 1e-6); t0, fn, xf = SHOTS[i]
            if t < t0 + xf + 0.1: return 1
            return 3 if fn in (sh_earth1, sh_diag_a, sh_diag_b, sh_moon, sh_jupiter, sh_saturn, sh_globe_cold, sh_drift, sh_sun2) else 2
        f = f0; cur = frame(f / FPS); nrender = 1
        while f < f1:
            st = step(f / FPS)
            if st > 1 and (f + st >= f1 or any(step((f + j) / FPS) < st for j in range(1, st + 1))): st = 1
            p.stdin.write(cur.tobytes())
            if f + st >= f1 and st == 1 and f + 1 >= f1: break
            nxt = frame((f + st) / FPS); nrender += 1
            for j in range(1, st):
                w = j / st
                p.stdin.write(cv2.addWeighted(cur, 1 - w, nxt, w, 0).tobytes())
            f += st; cur = nxt
            if nrender % 24 == 0: print(f"{f} ({f - f0}/{f1 - f0}) rendered {nrender} {time.time() - T0:.0f}s", flush=True)
        p.stdin.close(); p.wait(); os.rename(out + ".part.mp4", out); print("done", out, f"{time.time() - T0:.0f}s")
