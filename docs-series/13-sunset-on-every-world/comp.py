"""Compositor for 13 'Sunset on every world': every shot, locked to the voice (timeline.py).
Each world = one Blender plate (blender/world.py) lit here with that world's Sun and sky: sky gradient and glow as functions of
direction, Sun disc at its true apparent size for a fixed 24-degree lens, haze by distance, analytic seas, rings, stars, HUD.
  python3 comp.py still <t> [<t> ...]      -> SCR/chk/f_<t>.jpg        (VERT=1 for the 9:16 layout)
  python3 comp.py <t0> <t1>                -> SCR/seg/seg_<frame>.mp4  (silent x264 CRF 14)
"""
import subprocess
from lib import *
import timeline as TL
FPS = TL.FPS; S_, E_ = TL.START, TL.END
os.makedirs(f"{SCR}/chk", exist_ok=True)
_pl = {}
def plate(w):
    if w not in _pl:
        if len(_pl) >= 2: _pl.pop(next(iter(_pl)))
        _pl[w] = Plate(w)
    return _pl[w]
def mixa(a, b, t): return a * (1 - t[..., None]) + b * t[..., None]
def ang(EL, AZ, se, sa): return np.hypot((AZ - sa) * np.cos(np.radians(np.clip(EL, -5, 30))), EL - se)
def ground(pl, sunc, glowc, ambc):
    return pl.A_sun * np.asarray(sunc, f32) + pl.A_glow * np.asarray(glowc, f32) + pl.A_amb * np.asarray(ambc, f32)
def hazed(L, pl, hcol, dh, power=1.0, floor=0.0):
    T = np.exp(-(pl.dist / dh) ** power)[..., None] * (1 - floor); return L * T + hcol * (1 - T)
def compose(pl, sky, L):
    return sky * (1 - pl.alpha) + L * pl.alpha
def sunvis(pl, x, y, r):
    """fraction of the Sun's disc that the landscape leaves uncovered (drives the direct light)"""
    R = max(int(r), 2); x0, x1, y0, y1 = int(x - R), int(x + R + 1), int(y - R), int(y + R + 1)
    if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H: return 1.0 if y1 <= 0 else 0.0
    a = pl.alpha[max(y0, 0):min(y1, H), max(x0, 0):min(x1, W), 0]
    return float(1 - a.mean()) if a.size else 1.0
def horizon_sky(pl, skyfn, el=0.35):
    """sky colour just above the horizon in each column: the colour distance fades into"""
    return skyfn(np.full((1, W), el, f32), pl.AZ[int(pl.yh) - 2:int(pl.yh) - 1, :])
def sky_half(pl, skyfn):
    return up(skyfn(pl.ELh, pl.AZh))

# ------------------------------------------------------------------------------------------------ HUD
# last field: basis of each reconstruction (kept for the README; no longer drawn on screen, by the series rule against disclaimer captions)
INFO = dict(
    earth=("EARTH", "1.00", "8.3 LIGHT-MINUTES", "ONE DAY  24 H", "COMPUTER-GENERATED LIKE THE OTHERS, FOR A FAIR COMPARISON"),
    mars=("MARS", "0.66", "12.7 LIGHT-MINUTES", "ONE DAY  24 H 40 MIN", "ARTIST'S RECONSTRUCTION BASED ON ROVER SUNSET IMAGES (SPIRIT, CURIOSITY, PERSEVERANCE)"),
    mercury=("MERCURY", "2.1 - 3.3", "3.2 LIGHT-MINUTES", "ONE DAY  176 EARTH DAYS", "ARTIST'S RECONSTRUCTION BASED ON MESSENGER IMAGING AND MERCURY'S ORBIT"),
    venus=("VENUS", "1.38", "6.0 LIGHT-MINUTES", "ONE DAY  117 EARTH DAYS", "ARTIST'S RECONSTRUCTION BASED ON VENERA 13 AND 14 SURFACE PANORAMAS"),
    jupiter=("JUPITER", "0.19", "43 LIGHT-MINUTES", "ONE DAY  9 H 56 MIN", "ARTIST'S RECONSTRUCTION BASED ON JUNO AND GALILEO DATA.  SKY COLOURS ARE AN INFORMED GUESS"),
    saturn=("SATURN", "0.10", "80 LIGHT-MINUTES", "ONE DAY  ABOUT 10 H 33 MIN", "ARTIST'S RECONSTRUCTION BASED ON CASSINI DATA AND RING GEOMETRY"),
    uranus=("URANUS", "0.05", "2.7 LIGHT-HOURS", "ONE YEAR  84 EARTH YEARS", "ARTIST'S RECONSTRUCTION BASED ON VOYAGER 2 DATA AND URANUS'S 98-DEGREE TILT"),
    titan=("TITAN", "0.10", "80 LIGHT-MINUTES", "ONE DAY  16 EARTH DAYS", "ARTIST'S RECONSTRUCTION BASED ON HUYGENS SURFACE IMAGES AND CASSINI RADAR OF THE SEAS"),
    pluto=("PLUTO", "0.03", "5.5 LIGHT-HOURS", "ONE DAY  6.4 EARTH DAYS", "ARTIST'S RECONSTRUCTION BASED ON NEW HORIZONS IMAGES OF SPUTNIK PLANITIA"),
    kepler=("KEPLER-16 b", "0.9 + 0.3", "ABOUT 245 LIGHT-YEARS", "TWO SUNS, ONE ORBIT EVERY 41 DAYS", "IMAGINED MOON OF A REAL GAS GIANT.  ARTIST'S IMPRESSION BASED ON KEPLER DATA"),
)
def scrim(y, x0, y0, x1, y1, a=0.42, soft=90):
    """darken a soft-edged box so thin type stays readable over bright sky"""
    if a <= 0.004: return y
    key = (int(x0), int(y0), int(x1), int(y1), soft)
    if key not in scrim.c:
        if len(scrim.c) > 12: scrim.c.clear()
        m = np.zeros((H // 8, W // 8), f32); m[max(0, key[1] // 8):key[3] // 8, max(0, key[0] // 8):key[2] // 8] = 1
        scrim.c[key] = cv2.resize(cv2.GaussianBlur(m, (0, 0), soft / 8), (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    return y * (1 - a * scrim.c[key])
scrim.c = {}
def hud(ov, w, a, speed="TIME-LAPSE", extra=None):
    """world name, Sun's apparent size (number + to-scale icon against Earth's), distance in light-time, day length, credit line"""
    if a <= 0.004: return []
    name, size, dist, day, credit = INFO[w]
    if not VERT:
        x, y = 96, 92
        ov.text(x, y, name, size=58, wt="ExtraLight", a=a, track=0.34, display=True)
        ov.line([(x, y + 84), (x + 420, y + 84)], a=0.5 * a, width=1.0)
        ov.text(x, y + 100, "SUN'S APPARENT SIZE", size=17, a=0.8 * a, track=0.26); ov.text(x + 330, y + 96, size + " x", size=23, wt="Regular", col=(255, 214, 120), a=a, track=0.1); ov.text(x + 330 + 16 * len(size) + 44, y + 100, "EARTH'S", size=17, a=0.8 * a, track=0.26)
        ov.text(x, y + 134, "DISTANCE FROM EARTH" if w == "kepler" else "DISTANCE FROM THE SUN", size=17, a=0.8 * a, track=0.26); ov.text(x + 330, y + 134, dist, size=17, wt="Regular", a=a, track=0.2)
        ov.text(x, y + 168, day, size=17, a=0.8 * a, track=0.26)
        return [(40, 40, 760, 320, 0.30 * a)]
    x, y = 70, int(H * 0.125)
    ov.text(x, y, name, size=76, wt="ExtraLight", a=a, track=0.3, display=True)
    ov.line([(x, y + 108), (W - 70, y + 108)], a=0.5 * a, width=1.2)
    ov.text(x, y + 128, "SUN'S APPARENT SIZE", size=24, a=0.85 * a, track=0.22); ov.text(x + 400, y + 122, size + " x", size=32, wt="Regular", col=(255, 214, 120), a=a, track=0.1); ov.text(x + 400 + 23 * len(size) + 60, y + 128, "EARTH'S", size=24, a=0.85 * a, track=0.22)
    ov.text(x, y + 174, "DISTANCE FROM EARTH" if w == "kepler" else "DISTANCE", size=24, a=0.85 * a, track=0.22); ov.text(x + 400, y + 174, dist.replace("ABOUT ", ""), size=24, wt="Regular", a=a, track=0.16)
    ov.text(x, y + 220, day, size=24, a=0.85 * a, track=0.22)
    return [(0, y - 60, W, y + 290, 0.26 * a)]
def caption(ov, txt, a, sub=None, y=None):
    """one fact line, low centre (16:9) or above the credit (9:16)"""
    if a <= 0.004: return []
    if not VERT:
        yy = y or H - 150; ov.text(W / 2, yy, txt, size=27, a=a, track=0.26, anchor="m")
        if sub: ov.text(W / 2, yy + 44, sub, size=18, wt="Regular", a=0.92 * a, track=0.26, anchor="m")
        return [(W / 2 - 16 * max(len(txt), len(sub or "")) - 40, yy - 16, W / 2 + 16 * max(len(txt), len(sub or "")) + 40, yy + (78 if sub else 46), 0.5 * a)]
    yy = y or H * 0.80 - 190
    lines = [txt] if len(txt) <= 30 else None
    if lines is None:
        ws = txt.split(" "); l1 = []
        while ws and len(" ".join(l1 + [ws[0]])) <= max(len(txt) // 2 + 3, 18): l1.append(ws.pop(0))
        lines = [" ".join(l1), " ".join(ws)]; yy -= 48
    for i, l in enumerate(lines): ov.text(W / 2, yy + 48 * i, l, size=33, a=a, track=0.2, anchor="m")
    if sub:
        subs = [sub] if len(sub) <= 44 else None
        if subs is None:
            ws = sub.split(" "); l1 = []
            while ws and len(" ".join(l1 + [ws[0]])) <= len(sub) // 2 + 4: l1.append(ws.pop(0))
            subs = [" ".join(l1), " ".join(ws)]
        for i, l in enumerate(subs): ov.text(W / 2, yy + 48 * len(lines) + 6 + 32 * i, l, size=21, wt="Regular", a=0.92 * a, track=0.18, anchor="m")
    return [(0, yy - 20, W, yy + 48 * len(lines) + (84 if sub else 16), 0.5 * a)]
def fade(t, a, b, fi=0.8, fo=0.8): return ease((t - a) / fi) * (1 - ease((t - (b - fo)) / fo))

# ------------------------------------------------------------------------------------------------ MARS
def sky_mars(se, sa, k=1.0):
    def f(EL, AZ):
        e = np.maximum(EL, 0)
        base = mixa(C(0.40, 0.255, 0.135), C(0.115, 0.075, 0.048), 1 - np.exp(-e / 6.0))
        base = base * (1 - 0.55 * np.exp(-e / 1.0))[..., None]                        # dust murk hugging the horizon
        psi2 = np.hypot((AZ - sa) * 1.25, (EL - se) * 0.8)                       # the glow is a little taller than wide
        g = C(0.13, 0.38, 1.0) * (1.45 * np.exp(-psi2 / 1.7) + 0.36 * np.exp(-psi2 / 5.0))[..., None] + C(0.62, 0.82, 1.0) * (0.9 * np.exp(-psi2 / 0.42))[..., None]
        g = g * (1 - 0.75 * np.exp(-e / 0.8))[..., None]
        return (base * (0.4 + 0.6 * k) + g * k)
    return f
def sh_mars(tl, u, ov, se0=2.6, se1=0.15):
    pl = plate("mars"); se = se0 + (se1 - se0) * u; sa = 0.0
    dimk = float(np.clip((se + 0.9) / 2.2, 0.0, 1.0)) ** 0.8                    # dust dims the Sun well before it reaches the horizon
    fn = sky_mars(se, sa, 0.35 + 0.65 * dimk)
    sky = sky_half(pl, fn)
    x, y = pl.xy(se, sa); r = 0.66 * 0.2665 * pl.ppd
    sun_disc(sky, x, y, r, C(1.0, 0.98, 0.96) * 9 * dimk, limb=0.4)
    vis = sunvis(pl, x, y, r) * dimk
    L = ground(pl, C(0.95, 0.93, 1.0) * 6.5 * vis, C(0.50, 0.56, 0.80) * 1.5 * (0.4 + 0.6 * dimk), C(0.50, 0.33, 0.20) * 0.20 * (0.55 + 0.45 * dimk))
    L = hazed(L, pl, horizon_sky(pl, fn, 0.5), 9000.0)
    return compose(pl, sky, L), 1.3

def skyline(pl, az=0.0):
    """elevation (deg) of the landscape's silhouette in the column at azimuth az"""
    x = int(np.clip(pl.cx + pl.f * math.tan(math.radians(az)), 0, W - 1)); col = pl.alpha[:, x, 0]; y = int(np.argmax(col > 0.5))
    return math.degrees(math.atan((pl.yh - y) / pl.f))

# ------------------------------------------------------------------------------------------------ EARTH
def sky_earth(se, sa, clouds=None):
    k = float(np.clip((se + 1.6) / 4.0, 0, 1)); gk = float(np.clip((se + 2.0) / 2.0, 0.15, 1))
    def f(EL, AZ, with_clouds=False):
        e = np.maximum(EL, 0); psi = ang(EL, AZ, se, sa); daz = np.abs(AZ - sa)
        top = C(0.085, 0.15, 0.34) * (0.45 + 0.55 * k); mid = C(0.95, 0.47, 0.19); low = C(1.0, 0.27, 0.06)
        g1 = np.exp(-e / 7.5) * (0.55 + 0.45 * np.exp(-daz / 16)); g2 = np.exp(-e / 1.8) * (0.5 + 0.5 * np.exp(-daz / 10))
        base = top[None, None] * (1 - g1[..., None]) + mid * (g1 * 0.62)[..., None]
        base = base * (1 - 0.55 * g2[..., None]) + low * (0.62 * g2)[..., None]
        glow = C(1.0, 0.50, 0.15) * (1.25 * np.exp(-psi / 2.6))[..., None] + C(1.0, 0.78, 0.45) * (1.9 * np.exp(-psi / 0.75))[..., None]
        out = (base + glow * gk) * (0.5 + 0.5 * k)
        if with_clouds and clouds is not None:
            dens, edge = clouds
            lit = C(1.0, 0.40, 0.17) * (0.55 + 1.3 * np.exp(-psi / 7.0))[..., None] * (0.35 + 0.65 * gk) + C(1.0, 0.75, 0.4) * (0.9 * np.exp(-psi / 2.2) * gk)[..., None]
            body = C(0.15, 0.115, 0.17) * (0.5 + 0.5 * k)
            col = body[None, None] * (1 - edge[..., None]) + lit * edge[..., None]
            out = out * (1 - dens[..., None] * 0.9) + col * dens[..., None]
        return out
    return f
_cl = {}
def earth_clouds(pl, t):
    """two decks of streaky cloud in perspective; `edge` marks thin parts and undersides that catch the low Sun"""
    EL, AZ = pl.ELh, pl.AZh
    a = cloud_layer(EL, AZ, 11, 7.0, 26.0, du=0.002 * t, beta=1.75) + 0.45 * cloud_layer(EL, AZ, 12, 1.6, 6.0, du=0.004 * t, beta=1.5)
    b = cloud_layer(EL, AZ, 13, 16.0, 60.0, du=0.001 * t, beta=1.8)
    d = smooth(0.25, 1.5, a + 0.5 * b) * smooth(0.5, 2.0, EL) * (1 - 0.6 * smooth(6.0, 10.0, EL))
    edge = np.clip(1.25 - d * 1.05, 0, 1) * (0.55 + 0.45 * smooth(-0.6, 0.8, 0.45 * cloud_layer(EL, AZ, 12, 1.6, 6.0, du=0.004 * t, beta=1.5)))
    return d.astype(f32), edge.astype(f32)
def sh_earth(tl, u, ov, se0=2.3, se1=-0.25):
    pl = plate("earth"); se = se0 + (se1 - se0) * u; sa = 0.0
    cl = earth_clouds(pl, tl); fn = sky_earth(se, sa, cl)
    sky = up(fn(pl.ELh, pl.AZh, True)); sky0 = sky.copy()
    red = float(np.clip(se / 2.5, 0, 1)); sunc = C(1.0, 0.36 + 0.34 * red, 0.07 + 0.25 * red) * (7 + 6 * red)
    x, y = pl.xy(se, sa); r = 0.2665 * pl.ppd; sq = 1 - 0.13 * math.exp(-max(se, 0) / 0.8)
    sun_disc(sky, x, y, r, sunc, limb=0.45, squash=sq, tint_bottom=C(0.92, 0.72, 0.6))
    cover = float(np.clip((se + 0.2665) / 0.533, 0, 1)); vis = cover * (1 - 0.0)
    rock_a = pl.alpha[..., 0] * (1 - smooth(0.72, 0.97, pl.flag))
    water = sea(pl, sky0, tl, sunc * 110 * cover, se, sa, 0.2665, deep=C(0.020, 0.030, 0.045) * (0.5 + 0.5 * red), amp=1.0, refl_alpha=rock_a)
    L = ground(pl, sunc * 0.6 * vis, C(1.0, 0.5, 0.2) * 1.3 * (0.4 + 0.6 * red), C(0.20, 0.20, 0.34) * 0.5)
    L = L * 0.7 + pl.alb * (np.clip(pl.nrm[..., 2:3], 0, 1) ** 3) * C(1.0, 0.5, 0.25) * 0.5          # wet rock: a little sky sheen on up-facing faces
    hz = horizon_sky(pl, fn, 0.3)
    L = hazed(L, pl, hz, 5000.0)
    water = water * np.exp(-pl.dist / 30000.0)[..., None] + hz * (1 - np.exp(-pl.dist / 30000.0))[..., None]
    fl = smooth(0.72, 0.97, pl.flag)[..., None]; L = L * (1 - fl) + water * fl
    return compose(pl, sky, L), 1.25

# ------------------------------------------------------------------------------------------------ MERCURY
def corona(pl, se, sa, gain):
    psi = np.hypot((pl.AZ - sa) * 1.5, pl.EL - se); th = np.arctan2(pl.EL - se, pl.AZ - sa)
    st = 0.75 + 0.25 * np.sin(th * 7 + 1.0) * np.sin(th * 3 + 0.5)
    return (gain * (0.5 * np.exp(-psi / 0.5) + 0.10 * np.exp(-psi / 2.0) * st + 0.035 * np.exp(-psi / 6.0)))[..., None] * C(1.0, 0.93, 0.82)
def sh_mercury(tl, u, ov):
    pl = plate("mercury"); sa = 0.0; sl = skyline(pl, 0.0); R = 3.25 * 0.2665
    se = sl + kf(u, [(0, 2.6), (0.40, 1.15), (0.60, -R - 0.12), (0.68, -R - 0.14), (0.80, -R + 0.55), (0.86, -R + 0.55), (1.0, -R - 0.6)])
    x, y = pl.xy(se, sa); r = R * pl.ppd; vis = float(np.clip((se - sl + R) / (2 * R), 0, 1))
    sky = stars(5) * (0.15 + 0.85 * (1 - vis)) + corona(pl, se, sa, 0.10 + 0.45 * (1 - vis))
    sun_disc(sky, x, y, r, C(1.0, 0.97, 0.9) * 22, limb=0.62)
    L = ground(pl, C(1.0, 0.97, 0.92) * 5.5 * vis, C(1.0, 0.95, 0.85) * 0.5 * vis + 0.01, C(0.9, 0.9, 1.0) * (0.015 + 0.10 * vis))
    return compose(pl, sky, L), -1.3

# ------------------------------------------------------------------------------------------------ VENUS
def sh_venus(tl, u, ov):
    pl = plate("venus"); k = 1.0 - 0.72 * ease(u)
    def fn(EL, AZ):
        e = np.maximum(EL, 0); psi = np.hypot(AZ * 0.8, EL - 5.0)
        base = mixa(C(0.66, 0.25, 0.035), C(0.34, 0.115, 0.016), 1 - np.exp(-e / 9.0))
        base = base * (1 + 0.35 * np.exp(-(psi / 8.0) ** 2))[..., None]
        base = base * (1 - 0.30 * np.exp(-e / 1.4))[..., None] + C(0.36, 0.125, 0.018) * (0.30 * np.exp(-e / 1.4))[..., None]
        return base * k
    sky = sky_half(pl, fn)
    m = cloud_layer(pl.ELh, pl.AZh, 21, 9.0, 30.0, du=0.0015 * tl, beta=2.0, elmin=0.6)
    sky = sky * up(1 + 0.10 * m)[..., None]
    L = ground(pl, C(1.0, 0.42, 0.08) * 1.1 * k, C(1.0, 0.40, 0.08) * 1.2 * k, C(1.0, 0.38, 0.07) * 0.55 * k)
    L = hazed(L, pl, horizon_sky(pl, fn, 0.6), 5200.0)
    img = compose(pl, sky, L)
    # dense air: slow shimmer near the ground
    sh = tsample(tile(31, 1.3), pl.xx / 420.0 + 0.02 * tl, pl.yy / 90.0 - 0.05 * tl) * np.exp(-((pl.yy - pl.yh) / 70.0) ** 2) * 1.6
    return cv2.remap(img, pl.xx, (pl.yy + sh).astype(f32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), 1.15

# ------------------------------------------------------------------------------------------------ giant planets (cloud tops)
def cloud_ground(pl, sunc, glowc, ambc, fn, dh, sss=0.0):
    if not getattr(pl, "soft", False):            # let the far end of the deck dissolve into the sky instead of ending on an edge
        pl.alpha = pl.alpha * (1 - smooth(0.40 * pl.dmax, 0.68 * pl.dmax, pl.dist))[..., None]; pl.soft = True
    L = ground(pl, sunc, glowc, ambc)
    return hazed(L, pl, horizon_sky(pl, fn, 0.25), dh)
def sh_jupiter(tl, u, ov):
    pl = plate("jupiter"); a, b = TL.SH["jupiter"]; sl = skyline(pl, 0.0); r_deg = 0.192 * 0.2665
    se = sl - r_deg + 0.0098 * ((b - a) - 1.6 - tl); sa = 0.0                       # real time: 36 deg/hour
    def fn(EL, AZ):
        e = np.maximum(EL, 0); psi = ang(EL, AZ, se, sa); daz = np.abs(AZ - sa)
        base = mixa(C(0.80, 0.52, 0.30), C(0.035, 0.07, 0.20), 1 - np.exp(-e / 4.2))
        base = base * (0.65 + 0.35 * np.exp(-daz / 12))[..., None]
        band = np.exp(-e / 1.1) * np.exp(-daz / 9.0)
        base = base + C(1.0, 0.42, 0.14) * (0.55 * band)[..., None]
        glow = C(1.0, 0.66, 0.36) * (0.9 * np.exp(-psi / 1.1))[..., None] + C(1.0, 0.9, 0.75) * (2.2 * np.exp(-psi / 0.22))[..., None]
        return base * 0.85 + glow
    sky = sky_half(pl, fn)
    EL, AZ = pl.ELh, pl.AZh
    ci = smooth(0.5, 1.6, cloud_layer(EL, AZ, 41, 9.0, 80.0, du=0.004 * tl, beta=1.7) + 0.4 * cloud_layer(EL, AZ, 42, 2.0, 20.0, du=0.008 * tl, beta=1.5)) * smooth(0.3, 1.5, EL)
    psi_h = ang(EL, AZ, se, sa)
    sky = sky * up(1 - 0.45 * ci)[..., None] + up(ci * (0.25 + 1.2 * np.exp(-psi_h / 5.0)))[..., None] * C(1.0, 0.55, 0.32) * 0.55
    x, y = pl.xy(se, sa); r = r_deg * pl.ppd
    sun_disc(sky, x, y, r, C(1.0, 0.95, 0.85) * 60, limb=0.3)
    vis = sunvis(pl, x, y, r + 1)
    L = cloud_ground(pl, C(1.0, 0.62, 0.32) * 5.0 * (0.25 + 0.75 * vis), C(1.0, 0.55, 0.30) * 1.6, C(0.34, 0.36, 0.52) * 0.34, fn, 8.0e5)
    return compose(pl, sky, L), 1.2
def sh_saturn(tl, u, ov):
    pl = plate("saturn"); off = hv(-8.0, -5.4); sa = -off; se = 2.3 - 1.9 * u
    def fn(EL, AZ):
        e = np.maximum(EL, 0); psi = ang(EL, AZ, se, sa)
        base = mixa(C(0.86, 0.66, 0.36), C(0.03, 0.05, 0.12), 1 - np.exp(-e / 3.6))
        base = base + C(1.0, 0.6, 0.25) * (0.35 * np.exp(-e / 1.2))[..., None]
        glow = C(1.0, 0.78, 0.45) * (0.8 * np.exp(-psi / 1.4))[..., None] + C(1.0, 0.92, 0.8) * (2.0 * np.exp(-psi / 0.18))[..., None]
        return base * 0.8 + glow
    sky = sky_half(pl, fn)
    if not hasattr(pl, "ring"):
        # the ring arc is drawn as a wider-angle view of the sky (k x the lens) from mid-northern latitude, looking south-west, so it
        # reads as a thin bright band arching across the sky and down towards the sunset rather than as near-vertical streaks
        k_, lat_, roff_ = float(os.environ.get("RK", hv(4.0, 4.0))), float(os.environ.get("RLAT", hv(47.0, 47.0))), float(os.environ.get("ROFF", hv(-70.0, -70.0)))
        rc, ra = rings(pl.EL * k_, pl.AZ * k_, lat_, 2.0, roff_)
        ext = (1 - np.exp(-np.maximum(pl.EL, 0) / 2.2)) ** 1.3                     # the rings sink into the haze near the horizon
        pl.ring = (rc * (C(1.0, 0.90, 0.74) * 1.45), (ra * ext)[..., None])
    ringL, aa = pl.ring; sky = sky * (1 - aa * 0.9) + ringL * aa * (0.75 + 0.25 * float(np.clip(se / 2.3, 0, 1)))
    x, y = pl.xy(se, sa); r = 0.104 * 0.2665 * pl.ppd
    sun_disc(sky, x, y, r, C(1.0, 0.95, 0.85) * 150, limb=0.3)
    vis = sunvis(pl, x, y, r + 1)
    L = cloud_ground(pl, C(1.0, 0.70, 0.38) * 4.5 * vis, C(1.0, 0.66, 0.36) * 1.5, C(0.40, 0.40, 0.50) * 0.33, fn, 9.0e5)
    return compose(pl, sky, L), 1.2
def sh_uranus(tl, u, ov):
    pl = plate("uranus"); sl = skyline(pl, 0.0); wdt = hv(8.0, 4.6)
    sa = -wdt + 2 * wdt * u; se = sl + 0.75 - 0.95 * min(u / 0.70, 1.25) ** 1.3
    def fn(EL, AZ):
        e = np.maximum(EL, 0); psi = ang(EL, AZ, se, sa)
        # deeper, more saturated gradient: pale cyan haze only in a thin layer at the horizon, deep ocean blue above
        base = mixa(C(0.40, 0.72, 0.74), C(0.006, 0.035, 0.085), 1 - np.exp(-e / 1.9))
        base = base * (0.62 + 0.38 * np.exp(-np.abs(AZ - sa) / 14.0))[..., None]        # the sky darkens away from the Sun
        base = base + C(0.9, 0.8, 0.5) * (0.20 * np.exp(-e / 0.7) * np.exp(-np.abs(AZ - sa) / 6.0))[..., None]
        glow = C(0.62, 0.95, 0.92) * (0.75 * np.exp(-psi / 1.0))[..., None] + C(1.0, 1.0, 0.95) * (1.8 * np.exp(-psi / 0.14))[..., None]
        return base * 0.75 + glow
    sky = sky_half(pl, fn)
    x, y = pl.xy(se, sa); r = 0.052 * 0.2665 * pl.ppd
    sun_disc(sky, x, y, max(r, 1.7), C(1.0, 1.0, 0.95) * 90, limb=0.2)
    vis = sunvis(pl, x, y, 2)
    # the Sun travels sideways here, so the directional part of the light is computed from the normal pass for the current azimuth
    sd = np.array([math.sin(math.radians(sa)) * 0.95, math.cos(math.radians(sa)) * 0.95, 0.31], f32)
    # low grazing light: lit cloud flanks against deep blue shadowed troughs (contrast and depth instead of a flat teal deck)
    pl.A_glow = pl.alb * ((0.012 + 2.4 * np.clip((pl.nrm * sd).sum(-1) - 0.05, 0, 1) ** 1.1 + 0.05 * np.clip(pl.nrm[..., 2], 0, 1) ** 8) * (0.2 + 0.8 * pl.amb ** 2) * (0.35 + 0.65 * np.exp(-np.abs(pl.AZ - sa) / 7.0)))[..., None]
    L = cloud_ground(pl, C(0.9, 1.0, 0.95) * 0.0, C(0.80, 0.97, 0.90) * 3.4 * (0.45 + 0.55 * vis), C(0.03, 0.14, 0.34) * 0.10, fn, 9.0e5)
    return compose(pl, sky, L), 1.2

# ------------------------------------------------------------------------------------------------ TITAN
def sh_titan(tl, u, ov):
    pl = plate("titan"); se = 3.2 - 3.4 * u; sa = 0.0; k = 1.0 - 0.55 * ease(u)
    def fn(EL, AZ):
        e = np.maximum(EL, 0); psi = np.hypot((AZ - sa) * 0.9, EL - max(se, 0.3))
        base = mixa(C(0.50, 0.215, 0.04), C(0.15, 0.058, 0.012), 1 - np.exp(-e / 7.0))
        base = base * (1 - 0.35 * np.exp(-e / 1.2))[..., None]
        glow = C(1.0, 0.50, 0.12) * (0.62 * np.exp(-(psi / 3.6) ** 1.3) + 0.5 * np.exp(-(psi / 1.3) ** 1.5))[..., None]
        return (base + glow * (0.35 + 0.65 * float(np.clip((se + 1.0) / 3.0, 0, 1)))) * k
    sky = sky_half(pl, fn)
    m = cloud_layer(pl.ELh, pl.AZh, 51, 12.0, 60.0, du=0.001 * tl, beta=2.0, elmin=0.6); sky = sky * up(1 + 0.07 * m)[..., None]
    water = sea(pl, sky, tl, C(1.0, 0.56, 0.16) * 0.0, se, sa, 1.5, deep=C(0.010, 0.005, 0.002), amp=0.10, wind=0.6, chop=0.25, speed=0.35, refl_alpha=pl.alpha[..., 0] * (1 - smooth(0.72, 0.97, pl.flag)))
    L = ground(pl, C(1.0, 0.55, 0.16) * 0.9 * k, C(1.0, 0.55, 0.16) * 1.3 * k, C(0.9, 0.42, 0.10) * 0.55 * k)
    hz = horizon_sky(pl, fn, 0.5)
    L = hazed(L, pl, hz, 6500.0); T = np.exp(-pl.dist / 9000.0)[..., None]; water = water * T + hz * (1 - T)
    fl = smooth(0.72, 0.97, pl.flag)[..., None]; L = L * (1 - fl) + water * fl
    return compose(pl, sky, L), 1.2

# ------------------------------------------------------------------------------------------------ PLUTO
def star_sun(img, x, y, gain=1.0, col=C(1.0, 0.98, 0.95)):
    """the Sun as a point: tight core, soft glare, thin diffraction spikes"""
    R = 260; X0, X1, Y0, Y1 = max(int(x) - R, 0), min(int(x) + R, W), max(int(y) - R, 0), min(int(y) + R, H)
    if X0 >= X1 or Y0 >= Y1: return
    yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(f32); dx = xx - x; dy = yy - y; d2 = dx * dx + dy * dy; d = np.sqrt(d2)
    v = 60 * np.exp(-d2 / (2 * 1.5 ** 2)) + 2.2 * np.exp(-d / 5.0) + 0.30 * np.exp(-d / 26.0)
    for th in (0.0, math.pi / 2, math.pi / 4, -math.pi / 4):
        c, s_ = math.cos(th), math.sin(th); al = np.abs(dx * c + dy * s_); ac = np.abs(-dx * s_ + dy * c)
        v += (1.5 if th in (0.0, math.pi / 2) else 0.35) * np.exp(-ac * ac / 1.6) * np.exp(-al / (70.0 if th in (0.0, math.pi / 2) else 30.0))
    img[Y0:Y1, X0:X1] += (v * gain)[..., None] * col
def sh_pluto(tl, u, ov):
    pl = plate("pluto"); sl = skyline(pl, 0.0); se = sl + 2.3 - 2.25 * u; sa = 0.0
    def fn(EL, AZ):
        e = np.maximum(EL, 0); psi = ang(EL, AZ, se, sa)
        strat = np.interp(np.clip(e, 0, 8) / 8.0, np.linspace(0, 1, 1024), tile(61, 1.0, lo=5, hi=50)[0])       # irregular thin layers
        lay = 1 + 0.30 * strat * np.exp(-e / 3.0)
        h = (0.50 * np.exp(-e / 1.1) + 0.11 * np.exp(-e / 4.0)) * lay * (0.20 + 1.4 * np.exp(-psi / 3.2) + 2.2 * np.exp(-psi / 0.9))
        return h[..., None] * C(0.20, 0.42, 1.0)
    sky = sky_half(pl, fn) + stars(9) * 0.55
    x, y = pl.xy(se, sa); vis = sunvis(pl, x, y, 2)
    if vis > 0.01: star_sun(sky, x, y, vis)
    L = ground(pl, C(1.0, 0.98, 0.95) * 5.0 * vis, C(0.4, 0.6, 1.0) * 0.25, C(0.35, 0.5, 0.9) * 0.045)
    L = hazed(L, pl, horizon_sky(pl, fn, 0.3) * 0.6, 150000.0)
    return compose(pl, sky, L), 1.3

# ------------------------------------------------------------------------------------------------ KEPLER-16 (imagined moon)
def sh_kepler(tl, u, ov):
    pl = plate("kepler"); s2 = pl.meta["second_sun"]; drop = 3.3 * u
    seA = 3.3 - drop; saA = 0.6; seB = seA - 0.45; saB = saA + s2["az"]
    colA = bbcolor(4450) ** 1.7; colB = bbcolor(3300) ** 1.5          # pushed towards orange / red so the two stars read differently after tone-mapping
    def fn(EL, AZ):
        e = np.maximum(EL, 0); pA = ang(EL, AZ, seA, saA); pB = ang(EL, AZ, seB, saB)
        base = mixa(C(0.62, 0.30, 0.22), C(0.045, 0.04, 0.10), 1 - np.exp(-e / 5.0))
        base = base + C(1.0, 0.45, 0.16) * (0.4 * np.exp(-e / 1.3))[..., None]
        g = colA * (0.8 * np.exp(-pA / 2.0) + 0.9 * np.exp(-pA / 0.6))[..., None] + colB * (0.30 * np.exp(-pB / 1.2) + 0.5 * np.exp(-pB / 0.3))[..., None]
        return base * 0.8 + g
    sky = sky_half(pl, fn) + stars(13, mw=False) * 0.12 * up(smooth(3.0, 8.0, half(pl.EL)))[..., None]
    xA, yA = pl.xy(seA, saA); rA = 0.92 * 0.2665 * pl.ppd; xB, yB = pl.xy(seB, saB); rB = 0.32 * 0.2665 * pl.ppd
    sun_disc(sky, xB, yB, rB, colB * 4.2 + C(0.5, 0.2, 0.1), limb=0.4); sun_disc(sky, xA, yA, rA, colA * 3.0 + C(1.2, 0.9, 0.6), limb=0.4)
    vA = sunvis(pl, xA, yA, rA); vB = sunvis(pl, xB, yB, rB)
    L = ground(pl, colA * 5.5 * vA, colB * 2.0 * vB, C(0.42, 0.30, 0.40) * 0.30)
    L = hazed(L, pl, horizon_sky(pl, fn, 0.4), 30000.0)
    return compose(pl, sky, L), 1.25

WFN = dict(earth=sh_earth, mars=sh_mars, mercury=sh_mercury, venus=sh_venus, jupiter=sh_jupiter, saturn=sh_saturn, uranus=sh_uranus, titan=sh_titan, pluto=sh_pluto, kepler=sh_kepler)
def finish(img, expo, ov, scr=()):
    if expo < 0: y = tonemap(bloom(img, 0.55), -expo)                 # airless worlds: tighter glare, no lens streak
    else: y = tonemap(anamorphic(bloom(img), thr=3.0, amt=0.03), expo)
    for (x0, y0, x1, y1, a) in scr: y = scrim(y, x0, y0, x1, y1, a)
    for o in (ov if isinstance(ov, (list, tuple)) else [ov]): y = o.apply(y)
    return y
def zoom(img, z, cx=None, cy=None):
    if abs(z - 1) < 1e-4: return img
    cx = W / 2 if cx is None else cx; cy = HY * H if cy is None else cy
    M = np.array([[z, 0, cx * (1 - z)], [0, z, cy * (1 - z)]], f32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

# captions: (start, end, text, sub)
def _c(k0, d0, k1, d1, txt, sub=None): return (S_[k0] + d0, (E_[k1] if d1 is not None else S_[k1]) + (d1 or 0), txt, sub)
CAPS = dict(
    earth=[_c("earth1", 1.5, "earth1", 0.9, "THE SUN: HALF A DEGREE WIDE", "IT TAKES ABOUT TWO MINUTES TO SLIP BELOW THE HORIZON"),
           _c("earth2", 2.5, "earth2", 0.6, "RAYLEIGH SCATTERING", "AIR SCATTERS BLUE LIGHT AWAY.  RED IS WHAT REMAINS")],
    mars=[_c("mars1", 5.5, "mars1", 0.8, "AIR PRESSURE: LESS THAN 1% OF EARTH'S", "BUT FULL OF FINE RUST-COLOURED DUST"),
          _c("mars2", 1.0, "mars2", 0.8, "BUTTERSCOTCH SKY, BLUE SUNSET", "THE DUST SCATTERS BLUE LIGHT FORWARD, AROUND THE SUN")],
    mercury=[_c("merc1", 1.0, "merc1", 0.6, "ALMOST NO AIR.  NO COLOUR.  A BLACK SKY", "THE SUN: UP TO 3.3 TIMES WIDER THAN FROM EARTH"),
             _c("merc2", 7.0, "merc2", 1.2, "NEAR PERIHELION THE SUN CAN SET TWICE", "SEEN ONLY FROM SOME LONGITUDES")],
    venus=[_c("venus1", 5.0, "venus1", 0.6, "THE SUN'S DISC IS NEVER SEEN FROM THE SURFACE", "DAYLIGHT IS A DIM ORANGE OVERCAST"),
           _c("venus2", 3.0, "venus2", 1.0, "SUNRISE TO SUNRISE: 117 EARTH DAYS", "VENUS SPINS BACKWARDS.  THE SUN WOULD RISE IN THE WEST")],
    jupiter=[_c("jup", 6.5, "jup", -7.5, "27 TIMES FAINTER THAN ON EARTH", "THE SUN IS ONE FIFTH AS WIDE"),
             _c("jup", 17.0, "jup", 1.6, "THE DISC SETS IN ABOUT 10 SECONDS", "SHOWN IN REAL TIME")],
    saturn=[_c("sat", 5.0, "sat", 1.6, "THE RINGS, SEEN FROM THE CLOUD TOPS", "WATER ICE, FROM DUST GRAINS TO BOULDERS")],
    uranus=[_c("ura", 4.5, "ura", -8.5, "NEAR A POLE: 42 YEARS OF DAYLIGHT, THEN 42 OF NIGHT", "THE SUN CIRCLES THE SKY ONCE EVERY 17 HOURS"),
            (S_["ura"] + 16.0, E_["ura"] - 6.6, "THE DISC SETS WITHIN DAYS", "THE TWILIGHT CAN LINGER FOR YEARS"),
            (E_["ura"] - 5.6, E_["ura"] + 1.5, "NEPTUNE: THE SUN IS 1/30 THE WIDTH", "ABOUT FOUR LIGHT-HOURS FROM THE SUN")],
    titan=[_c("titan1", 7.5, "titan1", 0.8, "DAYLIGHT ABOUT 1,000 TIMES DIMMER THAN ON EARTH", "MEASURED BY THE HUYGENS LANDER IN 2005"),
           _c("titan2", 0.8, "titan2", 0.8, "THE HAZE PASSES RED LIGHT AND BLOCKS BLUE", "THE SUN NEVER SHOWS A CLEAN EDGE")],
    pluto=[_c("pluto1", 4.5, "pluto1", 0.8, "THE SUN IS A POINT OF LIGHT", "YET ABOUT 250 TIMES BRIGHTER THAN OUR FULL MOON"),
           _c("pluto2", 5.5, "pluto2", 1.0, "BLUE HAZE, LAYER UPON LAYER", "SEEN BY NEW HORIZONS IN 2015")],
    kepler=[_c("kep", 3.5, "kep", 0.8, "TWO SUNS: AN ORANGE DWARF AND A RED DWARF", "KEPLER-16 b ITSELF IS A GAS GIANT, 245 LIGHT-YEARS AWAY")],
)
SPEED = dict(jupiter="REAL TIME")
def world_shot(w, t, shot=None, se=None):
    """one frame of a world's shot: picture, slow push-in, HUD, captions. Returns sRGB float."""
    a, b = TL.SH[shot or w]; tl = t - a; u = float(np.clip(tl / (b - a), 0, 1)); ov = Overlay()
    img, ex = WFN[w](tl, u, ov) if se is None else WFN[w](tl + 40, u, ov, *se)
    img = zoom(img, 1.0 + 0.045 * u)
    scr = []; ovs = []
    if shot is None:
        k = fade(t, a + 0.5, b - 0.2, 1.0, 0.7); o = Overlay(); o.gain = k; ovs.append(o)
        scr += [(x0, y0, x1, y1, al * k) for (x0, y0, x1, y1, al) in hud(o, w, 1.0, SPEED.get(w, "TIME-LAPSE"))]
        for (c0, c1, txt, sub) in CAPS.get(w, []):
            k = fade(t, c0, c1, 0.7, 0.7)
            if k > 0.004:
                o = Overlay(); o.gain = k; ovs.append(o); scr += [(x0, y0, x1, y1, al * k) for (x0, y0, x1, y1, al) in caption(o, txt, 1.0, sub)]
    return img, ex, ovs, scr

# ---- cached stills of every world (for the opening montage and the recap grid)
_st = {}
def still(w, u=0.45):
    if w not in _st:
        fnm = f"{SCR}/cache/still_{w}_{hv('h', 'v')}.png"; os.makedirs(f"{SCR}/cache", exist_ok=True)
        if not os.path.exists(fnm):
            a, b = TL.SH[w]; img, ex = WFN[w]((b - a) * u, u, Overlay()); y = finish(img, ex, Overlay())
            cv2.imwrite(fnm, (np.clip(y, 0, 1) * 65535).astype(np.uint16)[..., ::-1])
        _st[w] = cv2.imread(fnm, cv2.IMREAD_UNCHANGED)[..., ::-1].astype(f32) / 65535
    return _st[w]
MONT = ["saturn", "mercury", "titan", "pluto", "jupiter"]
def sh_mars0(t):
    a, b = TL.SH["mars0"]; ov = Overlay(); u = (t - a) / (b - a)
    img, ex = sh_mars(t, u, ov, 1.9, 1.35); img = zoom(img, 1.0 + 0.05 * u); y = finish(img, ex, ov)
    ov = Overlay(); k = fade(t, 0.25, b - 0.1, 0.5, 0.6)
    if not VERT:
        ov.text(W / 2, 150, "MARS SUNSETS ARE BLUE", size=84, wt="Light", a=k, track=0.2, anchor="m", display=True)
        ov.text(W / 2, 268, "PHOTOGRAPHED BY NASA'S ROVERS", size=20, a=0.9 * fade(t, 1.6, b - 0.1, 0.6, 0.6), track=0.3, anchor="m")
        y = scrim(y, 200, 110, W - 200, 320, 0.25 * k)
    else:
        ov.text(W / 2, H * 0.15, "MARS SUNSETS", size=92, wt="Light", a=k, track=0.14, anchor="m", display=True); ov.text(W / 2, H * 0.15 + 120, "ARE BLUE", size=92, wt="Light", a=k, track=0.14, anchor="m", display=True)
        k2 = 0.9 * fade(t, 1.6, b - 0.1, 0.6, 0.6); ov.text(W / 2, H * 0.15 + 270, "PHOTOGRAPHED BY NASA'S ROVERS", size=24, a=k2, track=0.24, anchor="m")
        y = scrim(y, 0, H * 0.12, W, H * 0.15 + 360, 0.25 * k)
    return ov.apply(y)
def sh_intro(t):
    a, b = TL.SH["intro"]; n = len(MONT); d = (b - a) / n; i = min(int((t - a) / d), n - 1); tl = (t - a) - i * d
    def pic(j, tt): return zoom(still(MONT[j]), 1.02 + 0.035 * tt / d)
    y = pic(i, tl)
    if tl < 0.5 and i > 0: k = ease(tl / 0.5); y = pic(i - 1, tl + d) * (1 - k) + y * k
    ov = Overlay(); k = fade(t, a + 0.6, b - 0.1, 0.8, 0.6)
    if not VERT:
        ov.text(W / 2, H / 2 - 150, "SUNSET ON EVERY WORLD", size=66, wt="ExtraLight", a=k, track=0.34, anchor="m", display=True)
        ov.text(W / 2, H / 2 - 50, "ONE MOMENT.  ONE LENS.  TEN HORIZONS", size=20, a=0.9 * k, track=0.36, anchor="m")
        ov.text(96, H - 80, INFO[MONT[i]][0], size=20, a=0.9 * fade(tl, 0.3, d, 0.4, 0.4), track=0.4)
        y = scrim(y, 300, H / 2 - 200, W - 300, H / 2 + 10, 0.3 * k)
    else:
        ov.text(W / 2, H * 0.30, "SUNSET ON", size=80, wt="ExtraLight", a=k, track=0.26, anchor="m", display=True); ov.text(W / 2, H * 0.30 + 108, "EVERY WORLD", size=80, wt="ExtraLight", a=k, track=0.26, anchor="m", display=True)
        ov.text(W / 2, H * 0.30 + 250, "ONE MOMENT.  ONE LENS.  TEN HORIZONS", size=22, a=0.9 * k, track=0.26, anchor="m")
        ov.text(W / 2, H * 0.76, INFO[MONT[i]][0], size=26, a=0.9 * fade(tl, 0.3, d, 0.4, 0.4), track=0.4, anchor="m")
        y = scrim(y, 0, H * 0.27, W, H * 0.30 + 310, 0.3 * k)
    return ov.apply(y)
GRID = ["mars", "mercury", "venus", "jupiter", "saturn", "uranus", "titan", "pluto", "kepler"]
_grid = {}
def sh_recap(t):
    a, b = TL.SH["recap"]; u = (t - a) / (b - a)
    if "g" not in _grid:
        g = np.zeros((H, W, 3), f32); gap = hv(14, 12); mx, my0, my1 = hv(150, 40), hv(70, int(H * 0.13)), hv(170, int(H * 0.24))
        tw = (W - 2 * mx - 2 * gap) // 3; th = (H - my0 - my1 - 2 * gap) // 3; pos = []
        for i, w in enumerate(GRID):
            st = still(w); sc = max(tw / W, th / H); im = cv2.resize(st, (int(W * sc + 1), int(H * sc + 1)), interpolation=cv2.INTER_AREA)
            oy = int(np.clip(HY * im.shape[0] - th * 0.62, 0, im.shape[0] - th)); ox = (im.shape[1] - tw) // 2
            x0 = mx + (i % 3) * (tw + gap); y0 = my0 + (i // 3) * (th + gap); g[y0:y0 + th, x0:x0 + tw] = im[oy:oy + th, ox:ox + tw]; pos.append((x0, y0, tw, th))
        _grid["g"] = g; _grid["pos"] = pos
    y = _grid["g"].copy(); pos = _grid["pos"]
    for i, (x0, y0, tw, th) in enumerate(pos):
        k = ease((t - a - 0.25 - 0.22 * i) / 0.7); y[y0:y0 + th, x0:x0 + tw] *= k
    ov = Overlay()
    for i, (x0, y0, tw, th) in enumerate(pos):
        k = ease((t - a - 0.5 - 0.22 * i) / 0.7); ov.text(x0 + 14, y0 + th - hv(34, 40), INFO[GRID[i]][0], size=hv(16, 19), a=0.95 * k, track=0.3)
    k = fade(t, a + 0.4, b, 0.8, 0.5); k2 = fade(t, S_["end1"] + 3.5, b, 0.8, 0.5)
    if not VERT:
        ov.text(W / 2, H - 98, "NO HUMAN HAS EVER STOOD UNDER ANY OF THESE SKIES", size=28, a=k2, track=0.3, anchor="m")
    else:
        ov.text(W / 2, H * 0.76 + 14, "NO HUMAN HAS EVER STOOD", size=32, a=k2, track=0.22, anchor="m"); ov.text(W / 2, H * 0.76 + 60, "UNDER ANY OF THESE SKIES", size=32, a=k2, track=0.22, anchor="m")
    return ov.apply(zoom(y, 1.0 + 0.02 * u, W / 2, H / 2))
def sh_earth2(t):
    a, b = TL.SH["earth2"]; img, ex, ov, scr = world_shot("earth", t, "earth2", (0.75, -0.85)); y = finish(img, ex, ov)
    ov = Overlay(); k = fade(t, S_["end2"] + 2.6, E_["end2"] + 1.2, 0.8, 0.8); k2 = ease((t - (E_["end2"] + 1.6)) / 1.2)
    if not VERT:
        ov.text(W / 2, H - 170, "THE ONLY SUNSET ANYONE HAS WATCHED FROM THE GROUND", size=27, a=k, track=0.28, anchor="m")
        ov.text(W / 2, 200, "SUNSET ON EVERY WORLD", size=60, wt="ExtraLight", a=k2, track=0.36, anchor="m", display=True)
        ov.text(W / 2, 290, "EARTH", size=22, a=0.9 * k2, track=0.6, anchor="m")
        y = scrim(y, 200, H - 200, W - 200, H - 110, 0.3 * k)
    else:
        ov.text(W / 2, H * 0.72, "THE ONLY SUNSET ANYONE HAS", size=31, a=k, track=0.2, anchor="m"); ov.text(W / 2, H * 0.72 + 46, "WATCHED FROM THE GROUND", size=31, a=k, track=0.2, anchor="m")
        ov.text(W / 2, H * 0.20, "SUNSET ON", size=76, wt="ExtraLight", a=k2, track=0.26, anchor="m", display=True); ov.text(W / 2, H * 0.20 + 104, "EVERY WORLD", size=76, wt="ExtraLight", a=k2, track=0.26, anchor="m", display=True)
        ov.text(W / 2, H * 0.20 + 240, "EARTH", size=28, a=0.9 * k2, track=0.6, anchor="m")
        y = scrim(y, 0, H * 0.70, W, H * 0.72 + 100, 0.3 * k)
    y = ov.apply(y)
    return y * (1 - ease((t - (b - 2.2)) / 1.9))
def shot_srgb(name, t):
    if name == "mars0": return sh_mars0(t)
    if name == "intro": return sh_intro(t)
    if name == "recap": return sh_recap(t)
    if name == "earth2": return sh_earth2(t)
    img, ex, ov, scr = world_shot(name, t); return finish(img, ex, ov, scr)
XF = 0.9
def frame(t):
    i = max(k for k, sh in enumerate(TL.SHOTS) if sh[1] <= t + 1e-6); name, t0, t1 = TL.SHOTS[i]
    y = shot_srgb(name, t)
    if i > 0 and t < t0 + XF:
        k = ease((t - t0) / XF); y = shot_srgb(TL.SHOTS[i - 1][0], t) * (1 - k) + y * k
    if t < 0.4: y = y * (t / 0.4)
    return (np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8)

def test_world(w, u):
    a, b = TL.SH[w]; return frame(a + (b - a) * u)
if __name__ == "__main__":
    if sys.argv[1] == "world":
        for u in sys.argv[3:]:
            cv2.imwrite(f"{SCR}/chk/{hv('w', 'wv')}_{sys.argv[2]}_{u}.jpg", test_world(sys.argv[2], float(u))[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92]); print("wrote", u)
    elif sys.argv[1] == "still":
        for a_ in sys.argv[2:]:
            t = float(a_); cv2.imwrite(f"{SCR}/chk/{hv('f', 'v')}_{t:07.2f}.jpg", frame(t)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 93]); print("wrote", t, flush=True)
    elif sys.argv[1] == "stills":
        for w in GRID + ["earth"]: still(w); print("still", w, flush=True)
    else:
        a, b = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(a * FPS)), int(round(b * FPS))
        sd = f"{SCR}/{hv('seg', 'seg_v')}"; os.makedirs(sd, exist_ok=True); out = f"{sd}/seg_{f0:05d}.mp4"
        if os.path.exists(out): print("exists", out); sys.exit(0)
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p", "-threads", "2", out + ".part.mp4"], stdin=subprocess.PIPE)
        import time; T0 = time.time()
        # Slow shots are rendered every 2nd or 3rd frame and the frames between are linear blends; the sea, the opening,
        # every cross-fade and Uranus (where the Sun travels sideways) are rendered at a higher rate.
        def step(t):
            i = max(k for k, sh in enumerate(TL.SHOTS) if sh[1] <= t + 1e-6); name, t0, t1 = TL.SHOTS[i]
            if t < t0 + XF + 0.1 or t > t1 - 0.15 or t < 1.0: return 1
            if name in ("uranus",): return 1
            if name in ("earth", "earth2", "titan", "mars0", "recap"): return 2
            return 3
        f = f0; cur = frame(f / FPS); nrender = 1
        while f < f1:
            st = step(f / FPS)
            if st > 1 and (f + st >= f1 or any(step((f + j) / FPS) < st for j in range(1, st + 1))): st = 1
            p.stdin.write(cur.tobytes())
            if f + 1 >= f1: break
            nxt = frame((f + st) / FPS); nrender += 1
            for j in range(1, st): p.stdin.write(cv2.addWeighted(cur, 1 - j / st, nxt, j / st, 0).tobytes())
            f += st; cur = nxt
            if nrender % 24 == 0: print(f"{f} ({f - f0}/{f1 - f0}) rendered {nrender} {time.time() - T0:.0f}s", flush=True)
        p.stdin.close(); p.wait(); os.rename(out + ".part.mp4", out); print("done", out, f"{time.time() - T0:.0f}s")
