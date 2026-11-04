"""06 'THE 524-METRE WAVE' - numpy compositor. Every shot is composited per frame from the Blender plates
(or drawn as a diagram) and piped straight into x264 (crf 14) as a segment.  Usage: python3 shots.py SHOT [SHOT...]"""
import sys, os, math
import numpy as np
from common import *          # noqa
from fx import *              # noqa
import world as Wd

SH = PLACE["shots"]
DUR = PLACE["dur"]
T_TITLE = 18.2
SHOTS = {}       # name -> (t0, t1, fn)


def shot(name, t0, t1):
    def deco(fn):
        SHOTS[name] = (t0, t1, fn); return fn
    return deco


def fade_edges(disp, t, t0, t1, fin=0.45, fout=0.45):
    a = 1.0
    if fin: a *= ss(t0, t0 + fin, t)
    if fout: a *= 1 - ss(t1 - fout, t1, t)
    if a < 1: disp *= a
    return disp


def to_frame(disp):
    return to8(disp)


_PLATES = {}


def plate(name, strip=True):
    if name not in _PLATES:
        _PLATES[name] = Plate(name, strip=strip)
    return _PLATES[name]


def move(P, t, t0, t1, z0, z1, c0, c1):
    """Slow eased push/pan on a plate. c = (fx, fy) fraction of the plate."""
    k = ss(t0, t1, t) * 0.7 + 0.3 * (t - t0) / (t1 - t0)
    z = lerp(z0, z1, k)
    cx = lerp(c0[0], c1[0], k) * P.wp; cy = lerp(c0[1], c1[1], k) * P.hp
    return z, cx, cy


def screen_pt(P, world_pts, z, cx, cy):
    u, v, d = P.cam.project(world_pts)
    cx, cy = clamp_center((P.hp, P.wp), z, cx, cy)
    sx, sy = plate_to_screen(u, v, z, cx, cy, P.wp)
    return sx, sy, d


def px_per_m(P, d, z):
    f = P.cam.lens / 36.0 * P.wp
    return f / d * (W / (P.wp / z))


def label(disp, vec, x, y, txt, sub=None, op=1.0, side="r", size=22, lead=60, col=(225, 230, 235)):
    """Thin leader line from a point + text."""
    if op <= 0.003: return
    dx = lead if side == "r" else -lead
    vec.line([(x, y), (x + dx * 0.35, y - 22), (x + dx, y - 22)], col=col, width=1.2, alpha=0.85 * op)
    vec.circle(x, y, 3.0, fill=col, outline=None, alpha=op)
    anchor = "l" if side == "r" else "r"
    draw_text(disp, txt, x + dx + (8 if side == "r" else -8), y - 22, size, op, anchor=anchor, tracking=0.22)
    if sub:
        draw_text(disp, sub, x + dx + (8 if side == "r" else -8), y + 6, int(size * 0.7), op * 0.8, anchor=anchor, tracking=0.25)


# =================================================================== O1  open: wide twilight establishing
@shot("O1", 0.0, T_TITLE)
def o1(t):
    P = plate("wide", strip=False)
    z, cx, cy = move(P, t, 0, T_TITLE, 1.25, 1.5, (0.5, 0.52), (0.48, 0.5))
    img = crop3(P.forest, z, cx, cy)
    d = finish(img)
    caption(d, t, 2.2, 8.4, "LITUYA BAY  ·  ALASKA", "SUMMER 1958", size=28)
    # title
    op = ss(15.2, 16.4, t)
    if op > 0:
        d *= (1 - 0.35 * op)
        draw_text(d, "THE 524-METRE WAVE", W / 2, H * 0.46, 64, op, font=FONT_XL, tracking=0.32)
        draw_text(d, "LITUYA BAY  ·  9 JULY 1958", W / 2, H * 0.46 + 70, 22, op * 0.85, tracking=0.4)
    fade_edges(d, t, 0, T_TITLE, fin=1.6, fout=0.6)
    return to_frame(d)


# =================================================================== M1  map (top-down plate)
WORLD_LBL = {
    "gulf": (-2600, -2600), "spit": (-450, 0), "cen": (450, 4800), "gil": (-2300, 11320), "cri": (2300, 11050),
    "lgl": (-4700, 13600), "cgl": (4800, 13600), "slide": (-1650, 11900), "spur": (-1500, 9850),
    "edrie": (780, 1600), "badger": (-620, 1050), "sunmore": (-430, 1320),
}


def map_base(t, t0, t1, z0=1.0, z1=1.08, c0=(0.5, 0.5), c1=(0.52, 0.48), tint=1.0, wc=None):
    P = plate("top", strip=True)
    if wc is not None:
        u, v, _ = P.cam.project([[wc[0], wc[1], 0.0]])
        c0 = c1 = (float(u[0]) / P.wp, float(v[0]) / P.hp)
    z, cx, cy = move(P, t, t0, t1, z0, z1, c0, c1)
    img = crop3(P.forest, z, cx, cy)
    d = finish(img * tint, exposure=1.7)
    return P, d, z, cx, cy


def wpt(P, key, z, cx, cy, zz=0.0):
    x, y = WORLD_LBL[key]
    sx, sy, _ = screen_pt(P, [[x, y, zz]], z, cx, cy)
    return float(sx[0]), float(sy[0])


def north_arrow(vec, d, x, y, op):
    """The map plate is drawn with real north up."""
    L = 30
    vec.line([(x, y + L), (x, y - L)], width=1.4, alpha=op)
    vec.poly([(x, y - L - 4), (x - 6, y - L + 10), (x + 6, y - L + 10)], alpha=op)
    draw_text(d, "N", x, y - L - 24, 18, op)


def scale_bar(P, vec, d, z, op, x=W - 330, y=H - 110, km=2):
    s = W / (P.wp / z) * P.wp / P.cam.oscale       # screen px per metre
    L = km * 1000 * s
    vec.line([(x, y), (x + L, y)], width=1.4, alpha=op)
    vec.line([(x, y - 6), (x, y + 6)], width=1.4, alpha=op); vec.line([(x + L, y - 6), (x + L, y + 6)], width=1.4, alpha=op)
    draw_text(d, f"{km} km", x + L / 2, y - 18, 16, op)


@shot("M1", T_TITLE, SH["night"])
def m1(t):
    t0, t1 = T_TITLE, SH["night"]
    P, d, z, cx, cy = map_base(t, t0, t1)
    vec = Vec()
    o = lambda a: ss(a, a + 0.8, t)
    l2, l3, l4 = LS(2), LS(3), LS(4)
    label(d, vec, *wpt(P, "gulf", z, cx, cy), "GULF OF ALASKA", op=o(l2 + 0.5), side="l", size=20)
    label(d, vec, *wpt(P, "spit", z, cx, cy), "LA CHAUSSÉE SPIT", op=o(l2 + 6.5), side="l", size=20)
    label(d, vec, *wpt(P, "cen", z, cx, cy), "CENOTAPH ISLAND", op=o(l2 + 3.5), side="r", size=20)
    # Fairweather Fault along the crossbar
    of = o(l3 + 3.0)
    if of > 0:
        kx = np.array([-6.0, -4.5, -3.15, -1.5, 0.55, 1.9, 3.4, 5.2]) * 1000
        ky = np.array([12.8, 12.2, 11.65, 10.95, 10.45, 10.8, 11.25, 11.9]) * 1000
        tt_ = np.linspace(0, 1, 60); kk = np.linspace(0, 1, len(kx))
        xs = np.interp(tt_, kk, kx); ys = np.interp(tt_, kk, ky)
        sx, sy, _ = screen_pt(P, np.stack([xs, ys, np.zeros_like(xs)], -1), z, cx, cy)
        n = int(len(xs) * ss(l3 + 3.0, l3 + 6.0, t)) + 1
        vec.dashed(list(zip(sx[:n], sy[:n])), col=(240, 160, 110), width=1.6, alpha=of, dash=14, gap=9)
        ex, ey = float(sx[14]), float(sy[14])
        draw_text(d, "FAIRWEATHER FAULT", ex - 40, ey + 10, 18, of, col=srgb((0.95, 0.7, 0.55)), anchor="r")
        draw_text(d, "plate boundary  ·  Pacific / North American", ex - 40, ey + 34, 13, of * 0.8, anchor="r")
    label(d, vec, *wpt(P, "gil", z, cx, cy), "GILBERT INLET", op=o(l3 + 1.0), side="l", size=20)
    label(d, vec, *wpt(P, "cri", z, cx, cy), "CRILLON INLET", op=o(l3 + 1.6), side="r", size=20)
    label(d, vec, *wpt(P, "lgl", z, cx, cy), "LITUYA GLACIER", op=o(l4), side="l", size=18)
    label(d, vec, *wpt(P, "cgl", z, cx, cy), "NORTH CRILLON GLACIER", op=o(l4 + 0.6), side="l", size=18)
    north_arrow(vec, d, 120, 140, o(t0 + 1.0))
    scale_bar(P, vec, d, z, o(t0 + 1.0))
    vec.comp(d)
    draw_text(d, "STYLISED TERRAIN  ·  NOT TO SURVEY", W - 230, H - 60, 13, o(t0 + 1.0) * 0.6)
    fade_edges(d, t, t0, t1, fin=0.8, fout=0.5)
    return to_frame(d)


# =================================================================== N1  night: boats at anchor near the entrance
BOATS = {"edrie": (720, 1650, 13.0, 0.0), "badger": (-480, 1450, 14.0, 0.6), "sunmore": (-280, 1700, 13.0, 1.7)}


def draw_boats(P, d, t, z, cx, cy, lift=None, alpha=1.0, names=None, name_op=0.0, only=None):
    """True-scale boat silhouettes on the water (dark, faint rim from the sky glow) + reflection."""
    vec = Vec()
    for k, (bx, by, bl, ph) in BOATS.items():
        if only and k not in only:
            continue
        dz = 0.35 * math.sin(t * 1.1 + ph)
        roll = 0.03 * math.sin(t * 0.8 + ph * 2)
        if lift is not None:
            dz += lift.get(k, 0.0)
        sx, sy, dd = screen_pt(P, [[bx, by, 0.0]], z, cx, cy)
        s = px_per_m(P, float(dd[0]), z)
        x0, y0 = float(sx[0]), float(sy[0]) - dz * s
        for part in boat(bl):
            pts = [(x0 + (px * math.cos(roll) - py * math.sin(roll)) * s, y0 - (px * math.sin(roll) + py * math.cos(roll)) * s)
                   for px, py in part]
            vec.poly(pts, fill=(9, 11, 15), alpha=alpha)
            # reflection
            rp = [(px_, y0 + (y0 - py_) * 0.9 + 2) for px_, py_ in pts]
            vec.poly(rp, fill=(9, 11, 15), alpha=alpha * 0.35)
        if names and name_op > 0 and k in names:
            nm, sub = names[k]
            vec.line([(x0, y0 - 12 * s), (x0, y0 - 12 * s - 60)], width=1.0, alpha=0.7 * name_op)
            draw_text(d, nm, x0, y0 - 12 * s - 82, 20, name_op, tracking=0.3)
            draw_text(d, sub, x0, y0 - 12 * s - 106, 14, name_op * 0.8, tracking=0.25)
    vec.comp(d)


@shot("N1", SH["night"], SH["quake"])
def n1(t):
    t0, t1 = SH["night"], SH["quake"]
    P = plate("night", strip=False)
    z, cx, cy = move(P, t, t0, t1, 1.0, 1.12, (0.5, 0.52), (0.5, 0.55))
    img = crop3(P.forest, z, cx, cy)
    d = finish(img)
    names = {"edrie": ("EDRIE", "Howard Ulrich & son"), "badger": ("BADGER", "Bill & Vivian Swanson"),
             "sunmore": ("SUNMORE", "Orville & Mickey Wagner")}
    no = ss(LS(6), LS(6) + 0.8, t) * (1 - ss(t1 - 1.2, t1 - 0.4, t))
    draw_boats(P, d, t, z, cx, cy, names=names, name_op=no)
    caption(d, t, t0 + 1.0, LS(6) - 0.4, "9 JULY 1958  ·  AFTER 10 PM", "the sun had set only minutes earlier", size=26)
    fade_edges(d, t, t0, t1, fin=0.8, fout=0.4)
    return to_frame(d)


# =================================================================== Q1  quake (aerial, shaking)
@shot("Q1", SH["quake"], SH["slide"])
def q1(t):
    t0, t1 = SH["quake"], SH["slide"]
    P = plate("wide2", strip=False)
    z, cx, cy = move(P, t, t0, t1, 1.0, 1.1, (0.5, 0.5), (0.48, 0.47))
    tq = LS(7) + 2.6
    sx, sy = shake(t, tq, t1 + 4, 14.0, 1)
    img = crop3(P.forest, z, cx + sx, cy + sy)
    if t > tq:
        # slight motion blur while shaking
        img = 0.6 * img + 0.4 * np.roll(img, int(3 * math.sin(t * 40)), axis=0)
    d = finish(img)
    caption(d, t, LS(7) + 2.8, t1 - 0.2, "MAGNITUDE 7.8  ·  FAIRWEATHER FAULT", "about 10:15 pm local time", size=28)
    fade_edges(d, t, t0, t1, fin=0.4, fout=0.25)
    return to_frame(d)


# =================================================================== S1/G1 slide + impact + surge across the inlet (gilbert plate)
T_IMP = SH["surge"]
RATE = 3.2            # event seconds per screen second during the surge (compressed for the film)
T_SLIDE0 = LS(8) + 3.8


def tau_of(t):
    return (t - T_IMP) * RATE


class Splash:
    def __init__(self, n=9000):
        r = np.random.default_rng(11)
        ang = r.uniform(-np.pi, np.pi, n)
        # thrown mostly away from the slide (towards -y, the spur) and upward
        bias = np.array([0.0, -1.0])
        sp = r.uniform(20, 90, n) * (0.6 + 0.4 * r.random(n))
        dirx = np.cos(ang) * 0.6 + bias[0]; diry = np.sin(ang) * 0.6 + bias[1] * 0.7
        nn = np.hypot(dirx, diry) + 1e-6
        self.vx = sp * dirx / nn * 0.9; self.vy = sp * diry / nn * 0.9
        self.vz = r.uniform(40, 140, n) * r.random(n) ** 0.35
        self.p0 = np.array([Wd.IMPACT[0] * 1000, Wd.IMPACT[1] * 1000 + 180, 0.0])
        self.p0x = self.p0[0] + r.normal(0, 220, n); self.p0y = self.p0[1] + r.normal(0, 120, n)
        self.w = r.uniform(0.3, 1.0, n)

    def draw(self, P, tau, z, cx, cy):
        if tau <= 0 or tau > 40:
            return None
        tt = tau
        drag = np.exp(-tt / 9.0)
        x = self.p0x + self.vx * 9.0 * (1 - drag)
        y = self.p0y + self.vy * 9.0 * (1 - drag)
        zz = np.maximum(self.vz * tt - 4.9 * tt * tt * 0.55, 0)
        alive = (zz > 0) | (tt < 2)
        sx, sy, dd = screen_pt(P, np.stack([x, y, zz], -1), z, cx, cy)
        acc = Acc()
        fade = np.exp(-tt / 16.0) * self.w * alive
        acc.add(sx, sy, fade, np.array([1.0, 1.0, 1.0]))
        im = acc.image()[..., 0]
        im = blur(im, 2.0) * 1.2 + blur(im, 9.0) * 3.0
        return np.clip(im, 0, 6)


_SPL = None


def gilbert_frame(t, t0, t1, zoom):
    global _SPL
    P = plate("gilbert")
    z, cx, cy = zoom
    tau = tau_of(t)
    sxs, sys_ = shake(t, LS(7), T_SLIDE0 + 9.0, 7.0, 3)
    cx += sxs; cy += sys_
    if tau < 0:
        # the slide: scar revealed from the top down as the rock mass falls (tau from -T to 0)
        Tf = (T_IMP - T_SLIDE0) * 1.0
        k = np.clip((t - T_SLIDE0) / Tf, 0, 1)
        zf = 940 * (1 - k ** 1.6)
        chans = [P.forest[..., c] for c in range(3)] + [P.strip[..., c] for c in range(3)] + [P.Z, P.sm]
        C, (cx, cy) = P.crop(chans, z, cx, cy)
        fo = np.stack(C[:3], -1); st = np.stack(C[3:6], -1); Z, sm = C[6], C[7]
        gone = sm * sst(zf - 15, zf + 15, Z) * (k > 0)
        img = fo * (1 - gone[..., None]) + st * gone[..., None]
        # rolling dust at the front of the falling mass and a cloud that lingers above
        band = sm * np.exp(-((Z - zf) / 70.0) ** 2) * (k > 0) * (k < 1.02)
        cloud = sm * sst(zf - 30, zf + 200, Z) * k
        C2, _ = P.crop([P.X, P.Y], z, cx, cy)
        tex = np.clip(0.55 + 0.6 * Wd.noise(C2[0] / 1000.0, C2[1] / 1000.0 + 0.00002 * (t - T_SLIDE0) * 1000, 0.03, 95), 0, 1.5)
        dust = down4(np.ascontiguousarray(((band * 1.2 + cloud * 0.3) * tex).astype(np.float32)))
        dust = blur(dust, 3)
        img = img * (1 - 0.5 * np.clip(up4(dust), 0, 1))[..., None] + up4(dust)[..., None] * np.array([0.20, 0.19, 0.18], np.float32)
        return img, (z, cx, cy), P
    img, info = surge_layer(P, tau, z, cx, cy)
    cx, cy = info["cx"], info["cy"]
    if _SPL is None:
        _SPL = Splash()
    sp = _SPL.draw(P, tau, z, cx, cy)
    if sp is not None:
        img += sp[..., None] * np.array([0.30, 0.33, 0.38], np.float32)
    # lingering slide dust above the scar
    C, _ = P.crop([P.sm], z, cx, cy)
    dust = down4(np.ascontiguousarray(C[0])); dust = blur(dust, 7)
    img += up4(dust)[..., None] * np.array([0.10, 0.105, 0.11], np.float32) * math.exp(-max(tau, 0) / 60)
    return img, (z, cx, cy), P


@shot("S1", SH["slide"], SH["surge"])
def s1(t):
    t0, t1 = SH["slide"], SH["surge"]
    P = plate("gilbert")
    zoom = move(P, t, t0, t1 + 6.7, 1.0, 1.22, (0.5, 0.5), (0.56, 0.46))
    img, _, _ = gilbert_frame(t, t0, t1, zoom)
    d = finish(img)
    caption(d, t, LS(9), LS(9) + 7.6, "ABOUT 30 MILLION m³ OF ROCK", "falling from up to ~900 m into Gilbert Inlet", size=28)
    vec = Vec()
    o = ss(LS(8) + 1.0, LS(8) + 2.0, t) * (1 - ss(LS(9) - 0.8, LS(9), t))
    if o > 0:
        sx, sy, _ = screen_pt(P, [[Wd.SLIDE_C[0] * 1000, Wd.SLIDE_C[1] * 1000, 600]], *zoom)
        label(d, vec, float(sx[0]), float(sy[0]), "GILBERT INLET", "the slide wall", op=o, side="r", size=20)
    vec.comp(d)
    fade_edges(d, t, t0, t1, fin=0.25, fout=0)
    return to_frame(d)


T_G1_END = LS(11) - 0.5


@shot("G1", SH["surge"], T_G1_END)
def g1(t):
    t0, t1 = SH["surge"], T_G1_END
    P = plate("gilbert")
    zoom = move(P, t, SH["slide"], t1, 1.0, 1.22, (0.5, 0.5), (0.56, 0.46))
    img, _, _ = gilbert_frame(t, t0, t1, zoom)
    # impact flash of spray
    fl = math.exp(-max(t - t0, 0) / 0.5) * 0.25
    d = finish(img * (1 + fl))
    fade_edges(d, t, t0, t1, fin=0, fout=0.3)
    return to_frame(d)


# =================================================================== U1  the surge climbs the spur (spur plate)
@shot("U1", T_G1_END, SH["scale"])
def u1(t):
    t0, t1 = T_G1_END, SH["scale"]
    P = plate("spur")
    z, cx, cy = move(P, t, t0, t1, 1.0, 1.08, (0.5, 0.5), (0.5, 0.47))
    tau = tau_of(t)
    img, info = surge_layer(P, tau, z, cx, cy)
    d = finish(img)
    # elevation counter tracks the highest wet pixel reached
    f, wet, Z = info["f"], info["wet"], info["Z"]
    reached = (f > 0) & (wet > 0.5)
    zmax = float(Z[reached].max()) if reached.any() else 0.0
    zmax = min(zmax * (RUNUP_SCALE), 524.0) if zmax > 0 else 0.0
    oc = ss(t0 + 0.4, t0 + 1.2, t) * (1 - ss(t1 - 1.2, t1 - 0.4, t))
    if oc > 0 and zmax > 1:
        draw_text(d, f"{int(round(zmax)):d} m", W - 250, 150, 54, oc, font=FONT_XL, tracking=0.12)
        draw_text(d, "WATER HEIGHT ABOVE SEA LEVEL", W - 250, 200, 14, oc * 0.8)
    caption(d, t, LE(11) - 1.0, t1 - 0.3, "RUN-UP  524 m  ·  1,720 ft", "the highest wave run-up ever recorded", size=30)
    fade_edges(d, t, t0, t1, fin=0.3, fout=0.5)
    return to_frame(d)


RUNUP_SCALE = 1.0     # the stylised terrain's highest wet point is 523.9 m


# =================================================================== SC1 scale silhouettes against the stripped spur
@shot("SC1", SH["scale"], SH["runup"])
def sc1(t):
    t0, t1 = SH["scale"], SH["runup"]
    P = plate("spur")
    z, cx, cy = move(P, t, t0, t1, 1.08, 1.0, (0.5, 0.47), (0.5, 0.5))
    cxx, cyy = clamp_center((P.hp, P.wp), z, cx, cy)
    img = crop3(P.after(), z, cxx, cyy)
    d = finish(img)
    # reference point: the run-up maximum on the slope; silhouettes stand at sea level at the same distance
    pk = np.array([[-1534.0, 9719.0, 524.0]])
    u, v, dep = P.cam.project(pk)
    D = float(dep[0])
    s = px_per_m(P, D, z)
    base_world = pk.copy(); base_world[0, 2] = 0
    bx, by, _ = screen_pt(P, base_world, z, cxx, cyy)
    bx, by = float(bx[0]), float(by[0])
    vec = Vec()
    oe = ss(LS(13) + 1.0, LS(13) + 2.5, t)
    oes = ss(LS(13) + 5.5, LS(13) + 7.0, t)
    ol = ss(LS(14) + 0.2, LS(14) + 1.4, t)
    ex = bx - 330
    out, arch = eiffel()
    pts = [(ex + x * s, by - y * s) for x, y in out]
    vec.poly(pts, fill=(200, 210, 225), alpha=0.22 * oe, outline=(225, 232, 240), width=1.2)
    vec.poly([(ex + x * s, by - y * s) for x, y in arch], fill=(0, 0, 0), alpha=0.0)
    sx_ = bx + 120
    vec.poly([(sx_ + x * s, by - y * s) for x, y in esb()], fill=(200, 210, 225), alpha=0.22 * oes,
             outline=(225, 232, 240), width=1.2)
    # 524 m line
    y524 = by - 524 * s
    vec.dashed([(bx - 560, y524), (bx + 420, y524)], col=(240, 170, 120), width=1.6, alpha=ol, dash=12, gap=8)
    vec.line([(bx - 560, by), (bx + 420, by)], width=1.0, alpha=0.5 * max(oe, oes))
    vec.comp(d)
    draw_text(d, "EIFFEL TOWER", ex, by - 330 * s - 44, 18, oe)
    draw_text(d, "330 m", ex, by - 330 * s - 20, 15, oe * 0.85)
    draw_text(d, "EMPIRE STATE BUILDING", sx_, by - 443 * s - 44, 18, oes)
    draw_text(d, "443 m with antenna", sx_, by - 443 * s - 20, 15, oes * 0.85)
    draw_text(d, "RUN-UP  524 m", bx + 430, y524, 20, ol, col=srgb((0.95, 0.72, 0.55)), anchor="l")
    draw_text(d, "SEA LEVEL", bx + 430, by, 13, max(oe, oes) * 0.6, anchor="l")
    caption(d, t, t1 - 6.0, t1 - 0.3, "TRUE SCALE", "silhouettes drawn at the distance of the run-up maximum", size=24)
    fade_edges(d, t, t0, t1, fin=0.5, fout=0.6)
    return to_frame(d)


# =================================================================== diagrams
BG_TOP = np.array([0.010, 0.014, 0.024], np.float32); BG_BOT = np.array([0.004, 0.006, 0.010], np.float32)


def bg():
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    return np.broadcast_to(BG_TOP * (1 - g) + BG_BOT * g, (H, W, 3)).copy()


WATER_C = (95, 150, 200); WARM_C = (240, 165, 115); LINE_C = (215, 222, 232); ROCK_C = (70, 66, 62)


@shot("RU", SH["runup"], SH["ocean"])
def ru(t):
    """Cross-section of Gilbert Inlet: slide (right) -> wave (~150 m) -> run-up 524 m on the spur (left)."""
    t0, t1 = SH["runup"], SH["ocean"]
    d = bg(); vec = Vec()
    o = lambda a, b=0.9: ss(a, a + b, t)
    # geometry: x in metres across the inlet (0 = spur shore, 1300 = slide shore), y in metres
    X0, Y0, S = 600, 880, 0.56          # screen origin (sea level at spur shore) and px/m (vertical = horizontal)
    P = lambda x, y: (X0 + x * S, Y0 - y * S)
    spur = [(-1100, 800), (-900, 760), (-700, 640), (-520, 560), (-350, 430), (-200, 260), (-80, 110), (0, 0)]
    floor = [(0, 0), (120, -120), (600, -160), (1100, -130), (1300, 0)]
    wall = [(1300, 0), (1380, 300), (1480, 620), (1560, 900), (1700, 1000), (2700, 1100)]
    land = spur + floor[1:] + wall[1:] + [(2700, -400), (-1100, -400)]
    vec.poly([P(*p) for p in land], fill=ROCK_C, alpha=0.9 * o(t0 + 0.2))
    vec.line([P(*p) for p in spur + floor[1:] + wall[1:]], col=LINE_C, width=1.4, alpha=o(t0 + 0.2))
    # water at rest
    wl = [P(0, 0), P(1300, 0), P(1300, -130), P(1100, -130), P(600, -160), P(120, -120)]
    vec.poly(wl, fill=WATER_C, alpha=0.35 * o(t0 + 0.2))
    # the wave: crest ~150 m approaching the spur, then the run-up tongue to 524 m
    k = ss(LS(15) + 0.5, LS(15) + 4.0, t)
    xc = 1150 - 1000 * k
    xs = np.linspace(0, 1300, 120)
    hw = 150 * np.exp(-((xs - xc) / 170) ** 2) * o(LS(15) + 0.5)
    vec.poly([P(x, h) for x, h in zip(xs, hw)] + [P(1300, 0), P(0, 0)], fill=WATER_C, alpha=0.7 * o(LS(15) + 0.5))
    ku = ss(LS(15) + 3.6, LS(15) + 6.5, t)
    if ku > 0:
        # tongue up the slope (follows the spur profile up to the run-up height)
        sp = np.array(spur[::-1])
        hmax = 524 * ku
        pts = []
        for i in range(len(sp) - 1):
            (xa, ya), (xb, yb) = sp[i], sp[i + 1]
            for u in np.linspace(0, 1, 12):
                x = xa + (xb - xa) * u; y = ya + (yb - ya) * u
                if y <= hmax: pts.append((x, y))
        top = [(x + 14 * (1 - y / max(hmax, 1)), y + 6) for x, y in pts]
        poly = [P(x, y) for x, y in pts] + [P(x + 40 + 0.05 * (hmax - y), y) for x, y in pts[::-1]]
        vec.poly(poly, fill=WATER_C, alpha=0.75)
    # annotations
    oa = o(LS(15) + 6.0)
    y524 = Y0 - 524 * S
    vec.dashed([(X0 - 1100 * S, y524), (X0 + 1500 * S, y524)], col=WARM_C, width=1.5, alpha=oa)
    ob = o(LS(16) + 1.5)
    y150 = Y0 - 150 * S
    vec.dashed([(X0 + 100 * S, y150), (X0 + 1300 * S, y150)], col=WATER_C, width=1.5, alpha=ob)
    vec.line([(X0 - 1100 * S, Y0), (X0 + 1300 * S, Y0)], col=LINE_C, width=1.0, alpha=0.6 * o(t0 + 0.2))
    vec.comp(d)
    draw_text(d, "RUN-UP  524 m", X0 + 650 * S, y524 - 58, 26, oa, col=srgb((0.95, 0.72, 0.55)))
    draw_text(d, "how high the water reached on land, above sea level", X0 + 650 * S, y524 - 26, 15, oa * 0.8)
    draw_text(d, "WAVE  ~150 m", X0 + 560 * S, y150 - 58, 24, ob, col=srgb((0.6, 0.78, 0.95)))
    draw_text(d, "height of the wave itself where it struck the slope  ·  laboratory-model estimate", X0 + 560 * S, y150 - 28, 14, ob * 0.8)
    draw_text(d, "SEA LEVEL", X0 + 700 * S, Y0 + 22, 13, o(t0 + 0.2) * 0.6)
    draw_text(d, "SPUR", P(-750, 700)[0], P(-750, 700)[1] - 50, 15, o(t0 + 0.5) * 0.7)
    draw_text(d, "SLIDE WALL", P(1560, 960)[0], P(1560, 960)[1] - 30, 15, o(t0 + 0.5) * 0.7)
    draw_text(d, "GILBERT INLET  ·  SCHEMATIC CROSS-SECTION", W / 2, 90, 18, o(t0 + 0.3) * 0.8, tracking=0.35)
    fade_edges(d, t, t0, t1, fin=0.6, fout=0.6)
    return to_frame(d)


@shot("OC", SH["ocean"], SH["bay"])
def oc(t):
    """Left: ocean tsunami (sea-floor uplift, long low wave). Right: landslide splash in a closed bay."""
    t0, t1 = SH["ocean"], SH["bay"]
    d = bg(); vec = Vec()
    o = lambda a, b=0.9: ss(a, a + b, t)
    # left panel
    ol = o(t0 + 0.3)
    lx0, lx1, ly = 110, 900, 600
    vec.line([(lx0, ly), (lx1, ly)], col=LINE_C, width=1.0, alpha=0.5 * ol)
    vec.poly([(lx0, ly + 260), (lx1, ly + 260), (lx1, ly + 330), (lx0, ly + 330)], fill=ROCK_C, alpha=0.8 * ol)
    vec.poly([(lx0, ly), (lx1, ly), (lx1, ly + 260), (lx0, ly + 260)], fill=WATER_C, alpha=0.18 * ol)
    kt = (t - (t0 + 1.5)) / 6.0
    up = ss(t0 + 1.0, t0 + 2.0, t)
    vec.poly([(450, ly + 260), (560, ly + 260 - 14 * up), (680, ly + 260)], fill=WARM_C, alpha=0.8 * ol)
    xs = np.linspace(lx0, lx1, 200)
    if kt > 0:
        c1 = 560 + 300 * (kt % 1.0); c2 = 560 - 300 * (kt % 1.0)
        yy = ly - 9 * (np.exp(-((xs - c1) / 110) ** 2) + np.exp(-((xs - c2) / 110) ** 2)) * ol
    else:
        yy = np.full_like(xs, ly)
    vec.line(list(zip(xs, yy)), col=WATER_C, width=2.2, alpha=ol)
    # right panel
    orr = o(LS(18) - 0.5)
    rx0, rx1, ry = 1020, 1810, 600
    land = [(rx0, ry - 280), (rx0 + 120, ry - 60), (rx0 + 170, ry), (rx1 - 170, ry), (rx1 - 120, ry - 60), (rx1, ry - 330),
            (rx1, ry + 330), (rx0, ry + 330)]
    vec.poly([(rx0, ry - 280), (rx0 + 120, ry - 60), (rx0 + 150, ry + 120), (rx1 - 150, ry + 120), (rx1 - 120, ry - 60),
              (rx1, ry - 330), (rx1, ry + 330), (rx0, ry + 330)], fill=ROCK_C, alpha=0.8 * orr)
    vec.poly([(rx0 + 120, ry - 60 + 60), (rx0 + 150, ry + 120), (rx1 - 150, ry + 120), (rx1 - 120, ry)], fill=WATER_C, alpha=0.18 * orr)
    ks = ss(LS(18) + 0.5, LS(18) + 3.0, t)
    # slide block from the right wall
    bxp = rx1 - 120 - 60 * ks; byp = ry - 260 + 250 * ks
    vec.poly([(bxp, byp), (bxp + 70, byp - 30), (bxp + 90, byp + 40), (bxp + 10, byp + 60)], fill=(150, 140, 130), alpha=orr)
    ksp = ss(LS(18) + 2.6, LS(18) + 5.5, t)
    xs = np.linspace(rx0 + 130, rx1 - 130, 160)
    cpos = rx1 - 200 - 480 * ksp
    yy = ry - 95 * np.exp(-((xs - cpos) / 70) ** 2) * (ksp > 0) * (1 - 0.3 * ksp)
    vec.line(list(zip(xs, yy)), col=WATER_C, width=2.2, alpha=orr)
    kup = ss(LS(18) + 4.8, LS(18) + 6.4, t)
    if kup > 0:
        vec.line([(rx0 + 160, ry - 5), (rx0 + 120 - 60 * kup * 0.4, ry - 60 - 160 * kup)], col=WATER_C, width=5, alpha=orr)
    vec.comp(d)
    draw_text(d, "OCEAN TSUNAMI", (lx0 + lx1) / 2, 250, 24, ol)
    draw_text(d, "earthquake lifts the sea floor  ·  long, low wave  ·  can cross an ocean", (lx0 + lx1) / 2, 290, 14, ol * 0.8)
    draw_text(d, "(not to scale)", (lx0 + lx1) / 2, ly + 380, 12, ol * 0.6)
    draw_text(d, "LITUYA BAY 1958", (rx0 + rx1) / 2, 250, 24, orr, col=srgb((0.95, 0.72, 0.55)))
    draw_text(d, "landslide into a narrow, enclosed bay  ·  a giant splash", (rx0 + rx1) / 2, 290, 14, orr * 0.8)
    draw_text(d, "catastrophic inside  ·  weakened fast outside", (rx0 + rx1) / 2, 314, 14, orr * 0.8)
    fade_edges(d, t, t0, t1, fin=0.6, fout=0.5)
    return to_frame(d)


# =================================================================== BY  the wave runs down the bay (aerial)
BY_T0 = SH["bay"]
BY_TAU0, BY_TAU1 = 58.0, 215.0


@shot("BY", SH["bay"], SH["boats"])
def by(t):
    t0, t1 = SH["bay"], SH["boats"]
    P = plate("wide2")
    z, cx, cy = move(P, t, t0, t1, 1.12, 1.3, (0.5, 0.48), (0.5, 0.52))
    tau = lerp(BY_TAU0, BY_TAU1, (t - t0) / (t1 - t0))
    img, info = surge_layer(P, tau, z, cx, cy, foam_gain=1.3)
    d = finish(img)
    caption(d, t, LS(19) + 1.5, t1 - 0.3, "STILL TENS OF METRES HIGH", "speed estimates over 150 km/h", size=28)
    fade_edges(d, t, t0, t1, fin=0.6, fout=0.4)
    return to_frame(d)


# =================================================================== B1  the wave reaches the Edrie (entrance plate)
B1_T1 = LS(22) - 0.6
B1_TAU0, B1_RATE = 215.0, 2.6


def front_y_km(tau):
    return 10.3 - (tau - 53.5) / 22.2


@shot("B1", SH["boats"], B1_T1)
def b1(t):
    t0, t1 = SH["boats"], B1_T1
    P = plate("entrance", strip=False)
    z, cx, cy = move(P, t, t0, t1, 1.05, 1.14, (0.5, 0.55), (0.5, 0.5))
    tau = B1_TAU0 + (t - t0) * B1_RATE
    img, info = surge_layer(P, tau, z, cx, cy, foam_gain=1.2, band_gain=0.2)
    Y, wat = info["Y"], info["wat"]
    cxx, cyy = info["cx"], info["cy"]
    yf = front_y_km(tau) * 1000.0
    # the wave face: for every column, the screen row where the water reaches the front, extruded upward by Hw
    Hw = 32.0
    rows = np.arange(H)[:, None]
    behind = (wat > 0.5) & (Y > yf)
    infront = (wat > 0.5) & (Y <= yf)
    # first water row in front of the front (closest to the horizon)
    has = infront.any(0)
    rf = np.where(has, np.argmax(infront, 0), H)
    # distance at the front row -> pixel height of the wall
    cam = P.cam.M[:3, 3]
    dist = np.maximum(yf - cam[1], 30.0)
    s = px_per_m(P, dist, z)
    hpx = Hw * s
    top = rf - hpx
    xx = np.arange(W, dtype=np.float32)
    def ridge1d(seed, n=7, base=900.0, drift=0.0):
        r = np.random.default_rng(seed); out = np.zeros(W, np.float32)
        for k in range(n):
            wl = base / (1.7 ** k); out += r.uniform(0.5, 1.0) / (1.4 ** k) * np.sin(2 * np.pi * xx / wl + r.uniform(0, 6.3) + drift * (k + 1))
        return out / 2.2
    wob = 0.10 * hpx * ridge1d(1, drift=0.08 * tau)
    top = top + wob
    face = (rows >= top[None, :]) & (rows < rf[None, :]) & has[None, :] & (dist < 9000)
    fy = np.clip((rows - top[None, :]) / max(float(hpx), 1.0), 0, 1)
    cn = np.clip(0.75 + 0.35 * ridge1d(2, drift=0.15 * tau), 0.2, 1.2)[None, :]
    facecol = np.array([0.016, 0.024, 0.032], np.float32)[None, None] * (0.6 + 0.8 * fy[..., None])
    crest = (np.exp(-(fy / 0.16) ** 2) * cn)[..., None] * np.array([0.36, 0.41, 0.48], np.float32)
    streak = (0.5 + 0.5 * np.sin(rows / 3.0 + xx[None, :] * 0.0 + tau * 2.0)) * 0.0
    col = facecol + crest
    img = np.where(face[..., None], col, img)
    # spray above the crest
    sp = np.zeros((H, W), np.float32)
    band = (rows >= top[None, :] - hpx * 0.45) & (rows < top[None, :] + 0.1 * hpx) & has[None, :] & (dist < 9000)
    sp[band] = 1.0
    sp = up4(blur(down4(sp), 5)) * cn
    img += sp[..., None] * np.array([0.22, 0.25, 0.30], np.float32)
    # whiteout when the wave reaches the camera
    wo = sst(cam[1] + 150, cam[1] - 40, yf)
    d = finish(img)
    # boats: lifted as the front passes
    lift = {}
    gone = 0.0
    bx_, by_, bl, ph = BOATS["edrie"]
    ahead = yf - by_                       # metres the front still has to travel to reach the Edrie
    lift["edrie"] = Hw * 0.9 * float(np.clip(1 - ahead / 160.0, 0, 1)) if ahead < 160 else 0.0
    gone = float(np.clip(-ahead / 25.0, 0, 1))      # once the crest has passed, the boat is hidden behind the wave
    if gone < 1:
        draw_boats(P, d, t, z, cxx, cyy, lift=lift, alpha=1.0 - gone, only=("edrie",))
    d = d * (1 - wo) + np.array([0.10, 0.12, 0.14], np.float32) * wo
    caption(d, t, t0 + 0.6, LS(21) - 0.5, "THE EDRIE", "Howard Ulrich and his son, near the south shore", size=24)
    fade_edges(d, t, t0, t1, fin=0.4, fout=0.5)
    return to_frame(d)


# =================================================================== B2  what happened to the boats (map)
@shot("B2", B1_T1, SH["miller"])
def b2(t):
    t0, t1 = B1_T1, SH["miller"]
    P, d, z, cx, cy = map_base(t, t0, t1, 3.2, 3.4, tint=0.8, wc=(0, 500))
    vec = Vec()
    o = lambda a, b=0.8: ss(a, a + b, t)
    pt = lambda xy: tuple(float(v[0]) for v in screen_pt(P, [[xy[0], xy[1], 0]], z, cx, cy)[:2])
    WC = WATER_C
    # Edrie: thrown toward the shore, swept back (survived)
    e0 = pt((720, 1650)); e1 = pt((1100, 1800)); e2 = pt((620, 1550))
    oe = o(t0 + 0.2)
    vec.circle(*e0, 5, fill=LINE_C, outline=None, alpha=oe)
    vec.line([e0, e1], col=WC, width=1.5, alpha=oe); vec.line([e1, e2], col=WC, width=1.5, alpha=oe)
    # Badger: over the spit, out to sea, sank (crew escaped in a skiff)
    ob = o(LS(22) + 0.3)
    b0 = pt((-480, 1450)); b1_ = pt((-700, 200)); b2_ = pt((-760, -900))
    vec.circle(*b0, 5, fill=LINE_C, outline=None, alpha=ob)
    k = ss(LS(22) + 0.3, LS(22) + 3.0, t)
    pts = [b0, b1_, b2_]
    vec.line([b0, (b0[0] + (b1_[0] - b0[0]) * min(1, k * 2), b0[1] + (b1_[1] - b0[1]) * min(1, k * 2))], col=WC, width=1.5, alpha=ob)
    if k > 0.5:
        kk = (k - 0.5) * 2
        vec.line([b1_, (b1_[0] + (b2_[0] - b1_[0]) * kk, b1_[1] + (b2_[1] - b1_[1]) * kk)], col=WC, width=1.5, alpha=ob)
    # Sunmore: lost near the entrance
    os_ = o(LS(23) + 0.2)
    s0 = pt((-280, 1700)); s1 = pt((-80, 150))
    vec.circle(*s0, 5, fill=LINE_C, outline=None, alpha=os_)
    vec.dashed([s0, s1], col=(200, 200, 205), width=1.2, alpha=os_ * 0.8)
    vec.comp(d)
    draw_text(d, "EDRIE", e1[0] + 20, e1[1] - 20, 20, oe, anchor="l")
    draw_text(d, "Howard Ulrich & son  ·  survived", e1[0] + 20, e1[1] + 6, 14, oe * 0.85, anchor="l")
    draw_text(d, "BADGER", b2_[0] - 20, b2_[1] - 20, 20, ob, anchor="r")
    draw_text(d, "carried over the spit · sank · the Swansons survived", b2_[0] - 20, b2_[1] + 6, 14, ob * 0.85, anchor="r")
    draw_text(d, "SUNMORE", s1[0] + 20, s1[1] + 30, 20, os_, anchor="l")
    draw_text(d, "Orville & Mickey Wagner  ·  lost", s1[0] + 20, s1[1] + 56, 14, os_ * 0.85, anchor="l")
    draw_text(d, "ENTRANCE OF LITUYA BAY  ·  SCHEMATIC", W / 2, 70, 15, o(t0) * 0.7)
    fade_edges(d, t, t0, t1, fin=0.5, fout=0.6)
    return to_frame(d)


_MI_LV = None


# =================================================================== MI  Miller's trimline (after plate, archival-photo look)
@shot("MI", SH["miller"], SH["science"])
def mi(t):
    t0, t1 = SH["miller"], SH["science"]
    P = plate("after")
    z, cx, cy = move(P, t, t0, t1, 1.0, 1.15, (0.5, 0.5), (0.47, 0.52))
    cxx, cyy = clamp_center((P.hp, P.wp), z, cx, cy)
    img = crop3(P.after(churn=0.0), z, cxx, cyy)
    info = dict(cx=cxx, cy=cyy)
    # daylight-ish B&W print look: lift, desaturate, warm paper, soft vignette, grain
    lum = (img * np.array([0.3, 0.55, 0.15], np.float32)).sum(-1)
    global _MI_LV
    if _MI_LV is None:
        _MI_LV = (float(np.percentile(lum, 3)), float(np.percentile(lum, 99.7)))
    lo, hi = _MI_LV
    dd = np.clip((lum - lo) / (hi - lo), 0, 1) ** 0.5
    paper = np.array([0.93, 0.88, 0.78], np.float32)
    rng = np.random.default_rng(int(t * 24))
    gr = rng.normal(0, 0.025, (H // 2, W // 2)).astype(np.float32).repeat(2, 0).repeat(2, 1)
    ph = np.clip(dd + gr, 0, 1)[..., None] * paper
    ph = ph ** 2.2
    # print border
    yy, xx = np.mgrid[0:H, 0:W]
    m = 46
    inside = (xx > m) & (xx < W - m) & (yy > m) & (yy < H - m)
    vig = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    d = np.where(inside[..., None], ph * vig[..., None], np.array([0.012, 0.012, 0.012], np.float32))
    vec = Vec()
    ol = ss(LS(24) + 7.0, LS(24) + 8.2, t)
    pk = screen_pt(P, [[-1534, 9719, 524]], z, info["cx"], info["cy"])
    label(d, vec, float(pk[0][0]), float(pk[1][0]), "TRIMLINE", "forest above · bare ground below", op=ol, side="l",
          size=20, col=(250, 245, 235))
    vec.comp(d)
    caption(d, t, t0 + 1.0, LS(25) - 0.3, "RECONSTRUCTION", "after D. J. Miller, USGS Professional Paper 354-C (1960)", size=22)
    caption(d, t, LS(25) + 0.3, t1 - 0.3, "AT LEAST FOUR GIANT WAVES", "in a little more than a century (Miller, 1960)", size=24)
    fade_edges(d, t, t0, t1, fin=0.7, fout=0.6)
    return to_frame(d)


# =================================================================== SCI lab model + simulations
@shot("SCI", SH["science"], SH["risk"])
def sci(t):
    t0, t1 = SH["science"], SH["risk"]
    d = bg(); vec = Vec()
    o = lambda a, b=0.9: ss(a, a + b, t)
    # glass flume
    fx0, fx1, fy0, fy1 = 260, 1660, 330, 800
    of = o(t0 + 0.3)
    vec.line([(fx0, fy0), (fx0, fy1), (fx1, fy1), (fx1, fy0)], col=LINE_C, width=1.4, alpha=of)
    # slope (spur) on the left, ramp (slide) on the right
    vec.poly([(fx0, fy1), (fx0, fy0 + 40), (fx0 + 330, fy1 - 70), (fx0 + 380, fy1)], fill=ROCK_C, alpha=0.9 * of)
    vec.poly([(fx1, fy0 + 10), (fx1, fy1), (fx1 - 260, fy1), (fx1 - 200, fy1 - 160)], fill=ROCK_C, alpha=0.9 * of)
    wl = fy1 - 140
    ks = ss(LS(26) + 4.0, LS(26) + 6.0, t)
    kw = ss(LS(26) + 5.5, LS(26) + 9.5, t)
    xs = np.linspace(fx0 + 330 - 60, fx1 - 210, 200)
    cpos = fx1 - 260 - 900 * kw
    yy = wl - 95 * np.exp(-((xs - cpos) / 90) ** 2) * (kw > 0)
    vec.poly(list(zip(xs, yy)) + [(fx1 - 210, fy1), (fx0 + 380, fy1)], fill=WATER_C, alpha=0.5 * of)
    vec.line(list(zip(xs, yy)), col=WATER_C, width=2, alpha=of)
    # granular slide (dots) running down the ramp
    if ks > 0:
        r = np.random.default_rng(5)
        n = 160
        u = np.clip(ks * 1.3 - r.random(n) * 0.3, 0, 1)
        px_ = fx1 - 30 - 190 * u + r.normal(0, 10, n); py_ = fy0 + 30 + 300 * u + r.normal(0, 10, n)
        for a, b in zip(px_, py_):
            vec.circle(a, b, 3, fill=(170, 160, 150), outline=None, alpha=of)
    kr = ss(LS(26) + 8.8, LS(26) + 10.5, t)
    if kr > 0:
        vec.line([(fx0 + 300, wl + 20), (fx0 + 300 - 250 * kr, wl - 230 * kr)], col=WATER_C, width=6, alpha=of)
        vec.dashed([(fx0 - 30, wl - 235), (fx0 + 520, wl - 235)], col=WARM_C, width=1.4, alpha=kr)
    vec.comp(d)
    draw_text(d, "LABORATORY MODEL OF GILBERT INLET  ·  SCALE 1 : 675", W / 2, 200, 22, of)
    draw_text(d, "Fritz, Hager & Minor, 2001  (ETH Zurich)", W / 2, 236, 14, of * 0.8)
    draw_text(d, "MODEL RUN-UP MATCHED THE TRIMLINE", fx0 + 560, wl - 235, 16, kr, col=srgb((0.95, 0.72, 0.55)), anchor="l")
    osim = o(LS(27) - 0.2)
    draw_text(d, "NUMERICAL SIMULATIONS", W / 2, 900, 18, osim)
    draw_text(d, "e.g. Weiss et al. 2009  ·  González-Vida et al. 2019  ·  Franco et al. 2020", W / 2, 934, 14, osim * 0.8)
    fade_edges(d, t, t0, t1, fin=0.6, fout=0.6)
    return to_frame(d)


# =================================================================== RK1 glacier retreat -> unsupported slope
RK_SPLIT = LS(29) - 0.6


@shot("RK1", SH["risk"], RK_SPLIT)
def rk1(t):
    t0, t1 = SH["risk"], RK_SPLIT
    d = bg(); vec = Vec()
    o = lambda a, b=0.9: ss(a, a + b, t)
    oo = o(t0 + 0.3)
    # valley cross-section: steep wall on the right, glacier filling the valley, thinning over time
    vx0, vx1, vy = 420, 1500, 860
    wallL = [(vx0, 300), (vx0 + 120, 560), (vx0 + 260, 800), (vx0 + 400, vy)]
    wallR = [(vx1 - 400, vy), (vx1 - 250, 760), (vx1 - 140, 520), (vx1 - 40, 280), (vx1, 260)]
    vec.poly(wallL + wallR + [(vx1, 980), (vx0, 980)], fill=ROCK_C, alpha=0.9 * oo)
    k = ss(LS(28) + 3.5, LS(28) + 7.5, t)
    gtop = lerp(470, 760, k)
    def xat(wall, y):
        ys = [p[1] for p in wall]; xs_ = [p[0] for p in wall]
        order = np.argsort(ys)
        return float(np.interp(y, np.array(ys)[order], np.array(xs_)[order]))
    def glacier(gt):
        pts = [(xat(wallL, gt), gt)] + [p for p in wallL if p[1] > gt] + [p for p in wallR if p[1] > gt] + [(xat(wallR, gt), gt)]
        return pts
    # former (thicker) glacier surface, dashed
    g0 = glacier(470)
    vec.dashed([g0[0], g0[-1]], col=(200, 215, 230), width=1.2, alpha=0.6 * oo * k)
    pts = glacier(gtop)
    vec.poly(pts, fill=(200, 215, 230), alpha=0.75 * oo)
    # unstable block on the right wall + crack
    ob = o(LS(28) + 5.5)
    blk = [(vx1 - 230, 560), (vx1 - 150, 520), (vx1 - 120, 640), (vx1 - 210, 700)]
    vec.poly(blk, fill=(120, 105, 95), alpha=ob)
    vec.dashed([(vx1 - 150, 515), (vx1 - 100, 640), (vx1 - 170, 720)], col=WARM_C, width=1.5, alpha=ob)
    vec.comp(d)
    draw_text(d, "GLACIER THINS AND RETREATS", W / 2, 180, 22, oo)
    draw_text(d, "steep valley walls can lose their support", W / 2, 214, 14, oo * 0.8)
    draw_text(d, "UNSTABLE SLOPE", vx1 - 60, 580, 15, ob, col=srgb((0.95, 0.72, 0.55)), anchor="l")
    draw_text(d, "(schematic)", W / 2, 1010, 12, oo * 0.6)
    draw_text(d, "FORMER ICE SURFACE", W / 2, 450, 13, oo * 0.7 * k)
    fade_edges(d, t, t0, t1, fin=0.6, fout=0.4)
    return to_frame(d)


# =================================================================== RK2 run-up bars
@shot("RK2", RK_SPLIT, SH["end"])
def rk2(t):
    t0, t1 = RK_SPLIT, SH["end"]
    d = bg(); vec = Vec()
    o = lambda a, b=0.9: ss(a, a + b, t)
    base = 900; S = 1.25     # px per metre
    bars = [("LITUYA BAY", "Alaska · 1958", 524, False, t0 + 0.2),
            ("TAAN FIORD", "Alaska · 2015", 193, False, LS(29) + 2.0),
            ("BARRY ARM", "Alaska · modelled worst case (USGS 2021)", 500, True, LS(30) + 6.0)]
    xs = [520, 960, 1400]
    vec.line([(300, base), (1620, base)], col=LINE_C, width=1.0, alpha=0.6 * o(t0))
    for (nm, sub, h, model, ta), x in zip(bars, xs):
        k = ss(ta, ta + 2.0, t)
        hh = h * S * k
        if model:
            for yy in np.arange(base, base - hh, -14):
                vec.line([(x - 70, yy), (x + 70, max(yy - 14, base - hh))], col=WARM_C, width=1.2, alpha=0.8 * o(ta))
            vec.line([(x - 70, base - hh), (x + 70, base - hh)], col=WARM_C, width=1.5, alpha=o(ta))
            vec.dashed([(x - 70, base - hh), (x - 70, base)], col=WARM_C, width=1.2, alpha=o(ta))
            vec.dashed([(x + 70, base - hh), (x + 70, base)], col=WARM_C, width=1.2, alpha=o(ta))
        else:
            vec.poly([(x - 70, base), (x - 70, base - hh), (x + 70, base - hh), (x + 70, base)],
                     fill=WATER_C if nm != "LITUYA BAY" else WARM_C, alpha=0.75 * o(ta))
    vec.comp(d)
    for (nm, sub, h, model, ta), x in zip(bars, xs):
        k = ss(ta, ta + 2.0, t); op = o(ta)
        val = f"{'> ' if model else ''}{int(round(h * k))} m"
        draw_text(d, val, x, base - h * S * k - 34, 30, op, font=FONT_XL, tracking=0.1)
        draw_text(d, nm, x, base + 40, 18, op)
        draw_text(d, sub, x, base + 66, 13, op * 0.8)
    draw_text(d, "MAXIMUM RUN-UP", W / 2, 120, 20, o(t0))
    draw_text(d, "Barry Arm: slope of hundreds of millions of m³ above the fjord · monitored", W / 2, 1010, 13, o(LS(30) + 3.0) * 0.75)
    fade_edges(d, t, t0, t1, fin=0.6, fout=0.8)
    return to_frame(d)


# =================================================================== E1 end: the forest grew back, the line remains
@shot("E1", SH["end"], DUR)
def e1(t):
    t0, t1 = SH["end"], DUR
    P = plate("spur")
    z, cx, cy = move(P, t, t0, t1, 1.0, 1.14, (0.5, 0.5), (0.5, 0.47))
    C, (cxx, cyy) = P.crop([P.forest[..., 0], P.forest[..., 1], P.forest[..., 2], P.wet, P.X, P.Y], z, cx, cy)
    fo = np.stack(C[:3], -1); wet = C[3]
    # regrown (younger, lighter, more uniform) forest below the old trimline
    young = fo * np.array([1.45, 1.85, 1.30], np.float32)
    img = fo * (1 - wet[..., None]) + young * wet[..., None]
    d = finish(img)
    vec = Vec()
    ol = ss(LS(31) + 3.0, LS(31) + 4.5, t) * (1 - ss(LS(33) + 2.5, LS(33) + 3.5, t))
    pk = screen_pt(P, [[-1534, 9719, 524]], z, cxx, cyy)
    label(d, vec, float(pk[0][0]), float(pk[1][0]), "524 m", None, op=ol, side="r", size=22)
    vec.comp(d)
    op = ss(LS(33) + 3.0, LS(33) + 4.2, t)
    if op > 0:
        d *= (1 - 0.45 * op)
        draw_text(d, "THE 524-METRE WAVE", W / 2, H * 0.45, 60, op, font=FONT_XL, tracking=0.32)
        draw_text(d, "LITUYA BAY, ALASKA  ·  9 JULY 1958", W / 2, H * 0.45 + 66, 20, op * 0.85, tracking=0.4)
    fade_edges(d, t, t0, t1, fin=0.8, fout=1.6)
    return to_frame(d)


# ===================================================================
ORDER = ["O1", "M1", "N1", "Q1", "S1", "G1", "U1", "SC1", "RU", "OC", "BY", "B1", "B2", "MI", "SCI", "RK1", "RK2", "E1"]


def frames_of(name):
    t0, t1, _ = SHOTS[name]
    return int(round(t0 * FPS)), int(round(t1 * FPS))


def render(name, only=None):
    t0, t1, fn = SHOTS[name]
    f0, f1 = frames_of(name)
    if only is not None:
        from PIL import Image
        for tt in only:
            Image.fromarray(fn(tt)).save(os.path.join(SCR, "prev", f"{name}_{tt:.2f}.png"))
        return
    w = Writer(name, crf=14)
    for f in range(f0, f1):
        w.write(fn((f + 0.5) / FPS))
    n = w.close()
    print(name, "frames", n)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "still":
        nm = a[1]; render(nm, [float(x) for x in a[2:]])
    else:
        force = "--force" in a
        for nm in [x for x in a if x != "--force"]:
            if not force and os.path.exists(os.path.join(SEG, nm + ".mp4")):
                print("skip", nm); continue
            render(nm)
