"""ONE LIGHT-DAY FROM HOME - numpy/PIL compositor for the whole film.
Every frame is built in linear light (procedural sky + Blender plates + analytic planets), bloomed, tone-mapped,
captioned and piped into x264 per segment.
Usage: python3 comp.py <t0> <t1>          -> SCR/seg/seg_<frame0>.mp4   (skips if it exists)
       python3 comp.py still <t> [<t>...]  -> SCR/chk/still_<t>.png
"""
import os, sys, math, json, time
import numpy as np
from PIL import Image
from lib import *
import timeline as TL
import sky as SKY
import planets as PL

FONT_EXL = FONT_XL
WHITE = (0.93, 0.92, 0.88)
DIM = (0.62, 0.64, 0.68)
_sky = None


def sky():
    global _sky
    if _sky is None: _sky = SKY.Sky()
    return _sky


class SkyPlate:
    """sky rendered once on an oversized canvas; per-frame subpixel crops give slow drifts for free"""
    def __init__(self, R, fov, margin=1.25, mw=1.0, stars=1.0):
        self.m = margin; w, h = int(W * margin) // 2 * 2, int(H * margin) // 2 * 2
        f = (W / 2) / math.tan(math.radians(fov) / 2); fov_big = 2 * math.degrees(math.atan((w / 2) / f))
        lin = sky().render(R, fov_big, mw_gain=mw, star_gain=stars, size=(w, h))
        self.w, self.h = w, h
        self.ch = [Image.fromarray(np.ascontiguousarray(lin[..., c], np.float32), "F") for c in range(3)]

    def crop(self, dx=0.0, dy=0.0, zoom=1.0):
        cw, chh = W / zoom, H / zoom
        x0 = (self.w - cw) / 2 + dx; y0 = (self.h - chh) / 2 + dy
        x0 = max(0.0, min(x0, self.w - cw - 1e-3)); y0 = max(0.0, min(y0, self.h - chh - 1e-3))
        box = (x0, y0, min(x0 + cw, self.w), min(y0 + chh, self.h))
        return np.maximum(np.stack([np.asarray(c.resize((W, H), Image.BICUBIC, box=box)) for c in self.ch], -1), 0)


def camjson(name):
    j = json.load(open(os.path.join(PL_DIR, name, "cam.json")))
    fr = j["frames"][0] if "frames" in j else j
    return np.array(fr["R"]), fr.get("lens", j.get("lens")), np.array(fr.get("loc", [0, 0, 0])), np.array(j.get("sun", [0, 0, 1]))


PL_DIR = PL
PL_DIR = os.path.join(SCR, "plates")


def fov_of(lens):
    return 2 * math.degrees(math.atan(18.0 / lens))


def project(R, lens, loc, p, pw, ph):
    """world point (or direction if loc is None) -> pixel coords in a plate of size pw x ph"""
    d = np.asarray(p, float) - (loc if loc is not None else 0)
    c = R.T @ d; f = (pw / 2) / (18.0 / lens)
    return pw / 2 + f * c[0] / (-c[2]), ph / 2 - f * c[1] / (-c[2])


def finish(lin, exposure=1.0, bl=0.55, br=14, thresh=0.0):
    return tonemap(bloom(lin, bl, br, thresh), exposure)


_plates = {}
def plate(name, **kw):
    if name not in _plates:
        _plates[name] = Plate(os.path.join(PL_DIR, name, "0000.png"), **kw)
    return _plates[name]


def cap(disp, t, t0, t1, main, sub=None, y=None, size=30, shade=True, col=WHITE, subcol=None):
    op = fade(t, t0, t1)
    if op <= 0: return
    y = H * 0.868 if y is None else y
    if shade: shade_rect(disp, W / 2 - 720, y - 70, W / 2 + 720, y + (95 if sub else 60), 0.42 * op, soft=70)
    draw_text(disp, main, W / 2, y, size, op, col=col, font=FONT_L, tracking=0.26)
    if sub: draw_text(disp, sub, W / 2, y + size * 1.4, int(size * 0.56), op * 0.85, tracking=0.32, col=subcol or DIM)


def note(disp, s, op=1.0, x=64, y=H - 44, anchor="l"):
    draw_text(disp, s, x, y, 13, op * 0.62, tracking=0.30, col=DIM, anchor=anchor)


# =============================================================================================== shots
class Shot:
    def __init__(self, t0, t1): self.t0, self.t1 = t0, t1


class Hero(Shot):
    def setup(self):
        self.pa = plate("plate_heroA"); self.pb = plate("plate_heroB")
        self.sa = SkyPlate(SKY.look_at_dir(SKY.gal_dir(30, 21), 28), 48, mw=0.55)
        self.sb = SkyPlate(SKY.look_at_dir(SKY.gal_dir(-22, -13), -32), 48, mw=0.55)

    def frame(self, t):
        if not hasattr(self, "pa"): self.setup()
        xa, xb = 13.0, 14.8
        wA = 1 - ss(xa, xb, t); out = np.zeros((H, W, 3), np.float32)
        if wA > 0:
            u = t / xb
            lin = self.sa.crop(-90 + 150 * u, 30 - 40 * u)
            rgb, al = self.pa.place(0.6 * (1.02 + 0.13 * u), W / 2 + 95 - 50 * u, H / 2 - 50 + 14 * u)
            over(lin, rgb, al, 0.95)
            out += finish(lin, 1.15, bl=0.5, thresh=0.35) * wA
        if wA < 1:
            u = (t - xa) / (self.t1 - xa)
            lin = self.sb.crop(80 - 140 * u, -20 + 50 * u)
            rgb, al = self.pb.place(0.6 * (1.0 + 0.10 * u), W / 2 + 20 + 60 * u, H / 2 - 60 - 16 * u)
            over(lin, rgb, al, 0.95)
            out += finish(lin, 1.15, bl=0.5, thresh=0.35) * (1 - wA)
        disp = out * ss(0.0, 1.6, t)
        # hook captions
        op = fade(t, 0.5, 8.0, 0.5, 0.7)
        if op > 0:
            shade_rect(disp, 60, 760, 1150, 1010, 0.45 * op, 80)
            draw_text(disp, "VOYAGER 1", 120, 836, 62, op, font=FONT_EXL, tracking=0.34, anchor="l")
            draw_text(disp, "THE MOST DISTANT OBJECT HUMANS HAVE EVER BUILT", 124, 904, 19, op * 0.9, tracking=0.30, anchor="l", col=DIM)
            op2 = fade(t, 2.0, 8.0, 0.6, 0.7)
            draw_text(disp, "ABOUT TO BE", 124, 952, 19, op2 * 0.9, tracking=0.30, anchor="l", col=DIM)
            draw_text(disp, "ONE LIGHT-DAY FROM EARTH", 330, 951, 24, op2, tracking=0.28, anchor="l", col=YEL)
        op = fade(t, 9.2, 20.2, 0.6, 0.7)
        if op > 0:
            shade_rect(disp, 60, 760, 1250, 1020, 0.45 * op, 80)
            draw_text(disp, "18 NOVEMBER 2026", 120, 836, 56, op, font=FONT_EXL, tracking=0.30, anchor="l", col=YEL)
            op2 = fade(t, 15.0, 20.2, 0.6, 0.7)
            draw_text(disp, "25.9 BILLION KM FROM EARTH  ·  LIGHT TRAVEL TIME 24 HOURS", 124, 904, 19, op2 * 0.95, tracking=0.30, anchor="l")
            draw_text(disp, "DATE AS PROJECTED BY NASA / JPL", 124, 946, 14, op * 0.8, tracking=0.32, anchor="l", col=DIM)
        op = fade(t, 20.6, 25.3, 0.9, 0.8)
        if op > 0:
            disp *= (1 - 0.45 * op)
            draw_text(disp, "ONE LIGHT-DAY FROM HOME", W / 2, H / 2 - 14, 64, op, font=FONT_EXL, tracking=0.46)
            line(disp, W / 2 - 120, H / 2 + 52, W / 2 + 120, H / 2 + 52, op * 0.5)
            draw_text(disp, "VOYAGER 1  ·  1977 – 2026", W / 2, H / 2 + 92, 20, op * 0.85, tracking=0.5, col=DIM)
        return disp


def small_body(tex, R, light, **kw):
    n = int(R * 2.6) // 2 * 2
    rgb, al = PL.render_planet((n, n), R, tex, light, ss_=3, **kw)
    return Plate(arrays=(rgb, al), pad=8)


class LightTimes(Shot):
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(75, 24), 12), 55, mw=0.8)
        sh = PL.earth_shader(); L = PL.nrm((0.55, 0.3, 0.78)); sh.half = PL.nrm(L + np.array([0, 0, 1.0]))
        rgb, al = PL.render_planet((900, H), 520, None, L, axis=PL.nrm((0.25, 0.92, 0.3)), lon0=math.radians(20), shade=sh,
                                   atmo=((0.30, 0.55, 1.0), 10, 1.3), centre=(-150, 590))
        self.earth = (rgb, al)
        self.moon = small_body(PL.cached("moon", PL.moon_tex), 26, (0.6, 0.3, 0.74), limb=0.9)
        self.nep = small_body(PL.cached("neptune", PL.neptune_tex), 34, (-0.6, 0.3, 0.74), limb=0.5, atmo=((0.3, 0.5, 1.0), 3, 0.5))
        self.voy = plate("plate_fly")
        self.nodes = [(640, "THE MOON", "1.3 SECONDS", 27.9), (985, "THE SUN", "8 MINUTES", 30.3), (1335, "NEPTUNE", "≈ 4 HOURS", 33.0),
                      (1700, "VOYAGER 1", "24 HOURS", 35.6)]
        self.keys_t = [26.2, 27.9, 30.3, 33.0, 35.6]; self.keys_x = [372, 640, 985, 1335, 1700]

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0); Y = 590
        lin = self.sk.crop(-60 + 120 * u, 10)
        px = float(np.interp(t, self.keys_t, self.keys_x))
        # beam: faint guide + bright travelled part + pulse head
        xs = np.arange(372, 1700, dtype=np.float32)
        g = np.exp(-((np.arange(H, dtype=np.float32) - Y) / 1.3) ** 2)[:, None]
        trav = np.clip((px - xs) / 3, 0, 1) * (0.25 + 0.75 * np.exp(-(px - xs) / 260.0))
        lin[:, 372:1700] += (g * (0.05 + 0.9 * trav[None, :]))[..., None] * np.array([1.0, 0.9, 0.6], np.float32)
        if t > 26.2:
            glow_dot(lin, px, Y, 6.0 * (1 - ss(35.6, 36.6, t) * 0.7), 3.0, (1.0, 0.92, 0.7)); glow_dot(lin, px, Y, 0.6, 22.0, (1.0, 0.85, 0.55))
        # Sun
        s_on = ss(29.0, 30.6, t)
        flare(lin, 985, Y, 0.55 * (0.35 + 0.65 * s_on), 0.55, streak=0.25, ghosts=False)
        # Earth, Moon, Neptune, Voyager
        lin[:, :900] = lin[:, :900] * (1 - self.earth[1])[..., None] + self.earth[0] * 1.15
        for (pl_, x, yoff, k) in ((self.moon, 640, 0, 0), (self.nep, 1335, 0, 2)):
            a = 0.35 + 0.65 * ss(self.nodes[k][3] - 0.8, self.nodes[k][3] + 0.3, t)
            rgb, al = pl_.place(1.0, x, Y + yoff); over(lin, rgb * a, al)
        a = 0.3 + 0.7 * ss(34.6, 35.9, t)
        rgb, al = self.voy.place(0.21, 1700 + 8, Y - 6); over(lin, rgb * a * 1.4, al)
        disp = finish(lin, 1.1)
        for (x, name, tm, tk) in self.nodes:
            op = ss(tk - 0.5, tk + 0.5, t) * (1 - ss(self.t1 - 1.0, self.t1, t))
            draw_text(disp, name, x, Y - 110, 17, 0.35 + 0.65 * op, tracking=0.34, col=DIM)
            line(disp, x, Y - 92, x, Y - 62, 0.25 + 0.3 * op)
            draw_text(disp, tm, x, Y + 106, 30, op, font=FONT_EXL, tracking=0.2, col=YEL if x == 1700 else WHITE)
        draw_text(disp, "EARTH", 250, 960, 17, 0.8, tracking=0.34, col=DIM)
        cap(disp, t, 26.4, self.t1 - 0.3, "HOW LONG LIGHT TAKES FROM EARTH", y=150, size=26, shade=False)
        note(disp, "DISTANCES NOT TO SCALE  ·  NEPTUNE'S LIGHT-TIME VARIES AROUND 4 HOURS", fade(t, 27, self.t1))
        return disp


def planet_point(axis, lon0, q, lat_deg, lon_deg):
    """view-space unit-radius position of a (lat, lon) point for render_planet's conventions"""
    a = PL.nrm(axis); e1 = PL.nrm(np.cross([0.0, 1.0, 0.03], a)); e1 = PL.nrm(np.cross(a, np.cross(e1, a))); e2 = np.cross(a, e1)
    la, lo = math.radians(lat_deg), math.radians(lon_deg) - lon0
    return math.cos(la) * math.sin(lo) * e1 + math.cos(la) * math.cos(lo) * e2 + math.sin(la) * q * a


def lon0_facing(axis, lon_deg, lat_deg=0.0):
    """lon0 such that longitude lon_deg faces the viewer as much as possible"""
    best = max(np.linspace(-math.pi, math.pi, 721), key=lambda l0: planet_point(axis, l0, 1.0, lat_deg, lon_deg)[2])
    return best


class Launch(Shot):
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(140, 35), -20), 50, mw=0.7)
        ax = PL.nrm((-0.28, 0.9, 0.34)); self.ax = ax; self.R = 700.0
        self.l0 = lon0_facing(ax, -62.0, 20.0)
        sh = PL.earth_shader(); L = PL.nrm((-0.62, 0.38, 0.69)); sh.half = PL.nrm(L + np.array([0, 0, 1.0]))
        n = 1640
        rgb, al = PL.render_planet((n, n), self.R, None, L, axis=ax, lon0=self.l0, shade=sh, atmo=((0.30, 0.55, 1.0), 11, 1.35), ss_=2)
        self.earth = Plate(arrays=(rgb, al), pad=8)
        self.fl = planet_point(ax, self.l0, 1.0, 28.5, -80.6)

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0); ue = u * u * (3 - 2 * u)
        sc = 1.0 - 0.30 * ue; cx = 1080 + 140 * ue; cy = 640 + 60 * ue
        lin = self.sk.crop(40 * u, -30 * u)
        rgb, al = self.earth.place(sc, cx, cy); over(lin, rgb * 1.15, al)
        # launch trajectory: a thin arc leaving Florida, heading east then out, with a bright head
        fx = cx + self.fl[0] * self.R * sc; fy = cy - self.fl[1] * self.R * sc
        s = ss(39.2, 49.5, t)
        ex, ey = cx + 1.25 * self.R * sc, cy - 1.15 * self.R * sc
        mx, my = fx + 420 * sc, fy - 40 * sc
        ts = np.linspace(0, s, 220, dtype=np.float32)
        bx = (1 - ts) ** 2 * fx + 2 * ts * (1 - ts) * mx + ts ** 2 * ex; by = (1 - ts) ** 2 * fy + 2 * ts * (1 - ts) * my + ts ** 2 * ey
        acc = Acc(); wgt = 0.5 * np.exp(-(s - ts) * 5.0) + 0.08
        for k in range(4):
            acc.add(bx + (k % 2) * 0.5, by + (k // 2) * 0.5, wgt * 0.5, np.array([1.0, 0.85, 0.6], np.float32))
        lin += acc.image()
        if s > 0: glow_dot(lin, bx[-1], by[-1], 5.0, 2.2, (1.0, 0.9, 0.7)); glow_dot(lin, bx[-1], by[-1], 0.5, 14.0, (1.0, 0.8, 0.5))
        disp = finish(lin, 1.05)
        if 39.0 < t < 46:
            op = fade(t, 39.0, 46.0)
            ring(disp, fx, fy, 16, op * 0.8, wdt=1.2); line(disp, fx - 22, fy + 16, fx - 110, fy + 80, op * 0.5)
            draw_text(disp, "CAPE CANAVERAL", fx - 118, fy + 96, 15, op * 0.9, tracking=0.32, anchor="r")
        cap(disp, t, 39.0, 49.6, "5 SEPTEMBER 1977", "TITAN IIIE–CENTAUR ROCKET  ·  PRIMARY MISSION PLANNED FOR FIVE YEARS", size=40)
        note(disp, "EARTH: NASA BLUE MARBLE TEXTURES, OUR OWN RENDER  ·  TRAJECTORY SCHEMATIC", fade(t, 40, self.t1))
        return disp


class Jupiter(Shot):
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(200, -30), 10), 45, mw=0.6)
        ax = PL.nrm((0.10, 0.95, -0.30)); L = PL.nrm((-0.80, 0.22, 0.56)); self.L = L
        l0 = lon0_facing(ax, -35.0 + 16.0, -21.5)
        tex = PL.cached("jupiter", PL.jupiter_tex)
        rgb, al = PL.render_planet((2100, 1840), 880, tex, L, axis=ax, lon0=l0, q=0.935, limb=0.5, atmo=((0.95, 0.8, 0.6), 7, 0.10), ss_=2, term=0.09)
        self.jup = Plate(arrays=(rgb, al), pad=8)
        self.io = small_body(PL.cached("io", PL.io_tex), 64, L, limb=0.85)
        self.voy = plate("plate_fly")

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0)
        lin = self.sk.crop(-50 + 100 * u, 0)
        rgb, al = self.jup.place(0.90 + 0.06 * u, 1270 - 40 * u, 560 + 10 * u); over(lin, rgb * 0.92, al)
        ix, iy = 430 + 170 * u, 300 + 26 * u
        # Io's plume: a faint bluish umbrella on the limb (drawn before the disc so it rises from behind the limb)
        pa = math.radians(152); pxp = ix + math.cos(pa) * 66; pyp = iy - math.sin(pa) * 66
        pulse = 0.85 + 0.15 * math.sin(t * 2.1)
        for k, (d, sg, am) in enumerate(((2, 5, 0.9), (9, 8, 0.5), (17, 11, 0.25))):
            glow_dot(lin, pxp + math.cos(pa) * d, pyp - math.sin(pa) * d, am * pulse * 0.5, sg, (0.55, 0.7, 1.0))
        rgb, al = self.io.place(1.0, ix, iy); over(lin, rgb * 1.2, al)
        vx, vy = 250 + 620 * u, 900 - 150 * u
        rgb, al = self.voy.place(0.20 + 0.03 * u, vx, vy); over(lin, rgb * 1.5, al)
        disp = finish(lin, 1.0, bl=0.45)
        op = fade(t, 55.0, self.t1 - 0.4)
        line(disp, ix - 20, iy - 78, ix - 60, iy - 130, op * 0.5)
        draw_text(disp, "IO", ix - 66, iy - 150, 17, op, tracking=0.4, anchor="r")
        draw_text(disp, "VOLCANIC PLUME", ix - 66, iy - 124, 12, op * 0.8, tracking=0.32, anchor="r", col=DIM)
        cap(disp, t, 51.0, self.t1 - 0.3, "JUPITER  ·  5 MARCH 1979", "ERUPTIONS ON IO: THE FIRST ACTIVE VOLCANOES SEEN BEYOND EARTH", size=38)
        note(disp, "OUR OWN RENDER  ·  PROCEDURAL CLOUD TEXTURES  ·  SIZES AND SPACING NOT TO SCALE", fade(t, 52, self.t1))
        return disp


class Saturn(Shot):
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(-60, 22), -15), 45, mw=0.7)
        L = PL.nrm((-0.72, 0.30, 0.62)); self.L = L
        tex = PL.cached("saturn", PL.saturn_tex)
        rgb, al = PL.render_planet((2300, 1300), 330, tex, L, axis=PL.nrm((0.20, 0.87, 0.45)), q=0.902, limb=0.5,
                                   rings=dict(profile=PL.ring_profile(), gain=0.8), atmo=((0.9, 0.8, 0.6), 4, 0.05), ss_=3)
        self.sat = Plate(arrays=(rgb, al), pad=8)
        ttex = np.ones((64, 128, 3), np.float32) * np.array([0.80, 0.52, 0.18], np.float32)
        self.titan = small_body(ttex, 52, L, limb=0.6, atmo=((1.0, 0.62, 0.25), 5, 0.9), term=0.25)
        self.voy = plate("plate_fly")
        # schematic path: in from the left, past Titan, then bending up and out of the ring plane
        P = np.array([[-80, 930], [330, 835], [600, 700], [820, 470], [930, 200], [960, -60]], np.float32)
        ts = np.linspace(0, 1, 400); k = len(P) - 1
        def bez(tt):
            pts = P.copy()
            for r in range(k):
                pts = pts[:-1] * (1 - tt) + pts[1:] * tt
            return pts[0]
        self.path = np.array([bez(x) for x in ts])

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0)
        lin = self.sk.crop(60 - 120 * u, 20 * u)
        rgb, al = self.sat.place(0.86 + 0.07 * u, 1150 - 30 * u, 520); over(lin, rgb * 1.15, al)
        tx, ty = 470 - 60 * u, 770 + 16 * u
        rgb, al = self.titan.place(1.0, tx, ty); over(lin, rgb * 1.15, al)
        s = ss(63.5, 77.0, t) ** 0.9; n = max(2, int(s * 399))
        pth = self.path[:n + 1] - np.array([60 * u, -16 * u]) * np.clip(1 - np.arange(n + 1) / 180, 0, 1)[:, None]
        acc = Acc(); idx = np.arange(n + 1)
        acc.add(pth[:, 0], pth[:, 1], (0.45 + 1.2 * np.exp(-(n - idx) / 60.0)) * ((idx // 4) % 2 == 0), np.array([1.0, 0.9, 0.65], np.float32))
        lin += acc.image()
        hx, hy = pth[-1]
        rgb, al = self.voy.place(0.17, hx, hy); over(lin, rgb * 1.5, al)
        disp = finish(lin, 1.0, bl=0.4)
        op = fade(t, 66.0, self.t1 - 0.4)
        line(disp, tx - 40, ty + 44, tx - 80, ty + 84, op * 0.5)
        draw_text(disp, "TITAN", tx - 86, ty + 100, 17, op, tracking=0.4, anchor="r")
        cap(disp, t, 63.6, self.t1 - 0.3, "SATURN  ·  12 NOVEMBER 1980", "THE TITAN FLYBY SENT VOYAGER 1 UP AND OUT OF THE PLANE OF THE PLANETS", size=38)
        note(disp, "OUR OWN RENDER  ·  PATH SCHEMATIC  ·  SIZES AND SPACING NOT TO SCALE", fade(t, 64, self.t1))
        return disp


class PaleBlueDot(Shot):
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(95, -40), 8), 40, mw=0.5, stars=0.8)
        # reconstruction plate (our own): scattered-light rays in a dark, grainy narrow-angle frame, with a sub-pixel pale dot
        pw, ph = 2400, 1350; r = np.random.default_rng(1990)
        yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
        ang = math.radians(15.0); ca, sa = math.cos(ang), math.sin(ang)
        uu = (xx - pw / 2) * ca + (yy - ph / 2) * sa; vv = -(xx - pw / 2) * sa + (yy - ph / 2) * ca
        img = np.zeros((ph, pw, 3), np.float32) + np.array([0.0012, 0.0013, 0.0018], np.float32)
        streak = 1 + 0.10 * np.interp(uu, np.linspace(-1500, 1500, 900), r.standard_normal(900)).astype(np.float32)
        fall = np.exp((-(vv + 700) / 1500.0)).clip(0, 3) * 0.6
        for (u0, wd, colr, am) in ((-520, 150, (0.55, 0.32, 0.12), 0.050), (-110, 90, (0.25, 0.42, 0.22), 0.034), (330, 62, (0.70, 0.42, 0.20), 0.085),
                                   (690, 130, (0.45, 0.18, 0.10), 0.040), (1010, 70, (0.30, 0.32, 0.50), 0.03)):
            prof = np.exp(-np.abs((uu - u0) / wd) ** 2.6)
            img += (prof * streak * fall * am)[..., None] * np.array(colr, np.float32)
        img *= (1 + 0.5 * r.standard_normal((ph, pw, 1)).astype(np.float32) * 0.5).clip(0.2, 2)        # sensor noise
        img += np.abs(r.standard_normal((ph, pw, 3)).astype(np.float32)) * 0.0016
        self.dot = (pw / 2 + 330 * ca - 60 * (-sa) + 0, ph / 2 + 330 * sa + (-60) * ca)                 # inside the bright ray
        dx, dy = self.dot
        g = np.exp(-((xx - dx) ** 2 + (yy - dy) ** 2) / (2 * 1.25 ** 2))
        img += g[..., None] * np.array([0.42, 0.56, 0.80], np.float32) * 0.5
        self.rec = [Image.fromarray(np.ascontiguousarray(img[..., c], np.float32), "F") for c in range(3)]; self.pw, self.ph = pw, ph

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        ta = 86.2; tb = 88.0
        wA = 1 - ss(ta, tb, t); out = np.zeros((H, W, 3), np.float32)
        sx, sy = 1130.0, 500.0
        ang = math.radians(-14); ex, ey = math.cos(ang), math.sin(ang)
        pls = (("VENUS", 46, 0.5, (1.0, 0.95, 0.8)), ("EARTH", -72, 0.45, (0.6, 0.75, 1.0)), ("JUPITER", 118, 0.5, (1.0, 0.9, 0.75)),
               ("SATURN", -205, 0.38, (1.0, 0.9, 0.7)), ("URANUS", 345, 0.2, (0.7, 0.95, 1.0)), ("NEPTUNE", -520, 0.16, (0.6, 0.75, 1.0)))
        if wA > 0:
            u = (t - self.t0) / (tb - self.t0)
            z = 1.0 + 0.10 * u + 0.5 * ss(ta - 0.6, tb, t) ** 2
            lin = self.sk.crop(0, 0, 1.0)
            flare(lin, sx, sy, 1.3, 1.0, spikes=6, rot=0.2, streak=0.6)
            for (nm, d, am, colr) in pls:
                glow_dot(lin, sx + ex * d, sy + ey * d, am * 2.2, 1.3, colr)
            disp = finish(lin, 1.0)
            op = fade(t, 80.0, tb, 1.0, 1.2)
            for k, (nm, d, am, colr) in enumerate(pls):
                x, y = sx + ex * d, sy + ey * d
                e = nm == "EARTH"; o2 = op * (1.0 if e else 0.75)
                for (a0, b0, a1, b1) in ((-15, -15, 15, -15), (15, -15, 15, 15), (15, 15, -15, 15), (-15, 15, -15, -15)):
                    line(disp, x + a0, y + b0, x + a1, y + b1, o2 * 0.8, col=YEL if e else WHITE, wdt=1.0)
                up = (k % 2 == 0)
                line(disp, x, y + (-16 if up else 16), x, y + (-60 if up else 60) - (0 if not e else 0), o2 * 0.4)
                draw_text(disp, nm, x, y + (-76 if up else 76), 13, o2, tracking=0.34, col=YEL if e else DIM)
            draw_text(disp, "THE SUN", sx, sy - 150, 14, op * 0.8, tracking=0.34, col=DIM)
            cap(disp, t, 78.6, tb, "14 FEBRUARY 1990", "LOOKING BACK FROM 6 BILLION KM  ·  60 FRAMES  ·  SIX PLANETS: THE “FAMILY PORTRAIT”", size=38)
            note(disp, "SCHEMATIC VIEW  ·  PLANET SPACING ILLUSTRATIVE", fade(t, 79, tb))
            if z != 1.0:                                                    # push in towards Earth's frame
                ex0, ey0 = sx + ex * (-72), sy + ey * (-72)
                im = Image.fromarray(to8(disp)); cw, chh = W / z, H / z
                cxp = ex0 + (W / 2 - ex0) * (1 / z) ** 0.5; cyp = ey0 + (H / 2 - ey0) * (1 / z) ** 0.5
                x0 = max(0.0, min(cxp - cw / 2, W - cw - 1e-3)); y0 = max(0.0, min(cyp - chh / 2, H - chh - 1e-3))
                disp = (np.asarray(im.resize((W, H), Image.BICUBIC, box=(x0, y0, min(x0 + cw, W), min(y0 + chh, H))), np.float32) / 255.0) ** 2.2
                disp = disp ** (1 / 2.2) if False else disp
                out += disp * wA
            else:
                out += disp * wA
        if wA < 1:
            u = (t - ta) / (104.5 - ta); ue = min(max(u, 0), 1); ue = ue * ue * (3 - 2 * ue)
            sc = 0.82 * (2.6 / 0.82) ** ue                                   # output px per plate px
            dx, dy = self.dot
            # keep the dot drifting from its natural position towards the right-centre of frame
            tx_ = (W / 2 + (dx - self.pw / 2) * 0.82) * (1 - ue) + (W * 0.56) * ue; ty_ = (H / 2 + (dy - self.ph / 2) * 0.82) * (1 - ue) + (H * 0.47) * ue
            x0 = max(0.0, min(dx - tx_ / sc, self.pw - W / sc - 1e-3)); y0 = max(0.0, min(dy - ty_ / sc, self.ph - H / sc - 1e-3))
            tx_ = (dx - x0) * sc; ty_ = (dy - y0) * sc
            box = (x0, y0, min(x0 + W / sc, self.pw), min(y0 + H / sc, self.ph))
            lin = np.maximum(np.stack([np.asarray(c.resize((W, H), Image.BICUBIC, box=box)) for c in self.rec], -1), 0)
            disp = tonemap(bloom(lin * 6.5, 0.35, 10), 1.0)
            off = 1 - ss(102.6, 104.4, t)                                    # cameras off
            disp = disp * off
            op = fade(t, 88.5, 103.0)
            draw_text(disp, "RECONSTRUCTION", 110, 96, 20, op, tracking=0.36, anchor="l")
            draw_text(disp, "OUR OWN RENDER OF THE VIEW  ·  NOT THE NASA PHOTOGRAPH", 112, 132, 13, op * 0.8, tracking=0.32, anchor="l", col=DIM)
            o2 = fade(t, 90.5, 103.0)
            ring(disp, tx_, ty_, 30, o2 * 0.9, col=YEL, wdt=1.2)
            line(disp, tx_ + 24, ty_ - 24, tx_ + 96, ty_ - 96, o2 * 0.6, col=YEL)
            draw_text(disp, "EARTH", tx_ + 106, ty_ - 112, 22, o2, tracking=0.36, anchor="l", col=YEL)
            draw_text(disp, "0.12 OF ONE PIXEL IN THE ORIGINAL IMAGE", tx_ + 108, ty_ - 82, 13, o2 * 0.85, tracking=0.3, anchor="l", col=DIM)
            cap(disp, t, 88.6, 93.8, "6 BILLION KM FROM HOME", "THE COLOURED BANDS ARE SUNLIGHT SCATTERED INSIDE THE CAMERA", size=34)
            o3 = fade(t, 95.0, 102.2, 0.8, 0.8)
            if o3 > 0:
                shade_rect(disp, W / 2 - 760, 880, W / 2 + 760, 1040, 0.4 * o3, 70)
                draw_text(disp, "“A MOTE OF DUST, SUSPENDED IN A SUNBEAM”", W / 2, 940, 30, o3, tracking=0.26)
                draw_text(disp, "CARL SAGAN, PALE BLUE DOT (1994)", W / 2, 986, 15, o3 * 0.85, tracking=0.34, col=DIM)
            o4 = fade(t, 102.4, 106.3, 0.8, 0.8)
            draw_text(disp, "CAMERAS SWITCHED OFF  ·  34 MINUTES LATER", W / 2, H / 2, 24, o4, tracking=0.4, col=DIM)
            out += disp * (1 - wA)
        return out


class Helio(Shot):
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(10, 40), 0), 55, mw=0.55, stars=0.7)
        self.cx, self.cy, self.b = 660.0, 610.0, 300.0
        yy, xx = np.mgrid[0:H // 2, 0:W // 2].astype(np.float32) * 2
        X = xx - self.cx; Y = yy - self.cy; r = np.hypot(X, Y) + 1e-3
        th = np.arctan2(np.abs(Y), -X)                                        # angle from the downstream (-x) axis
        rb = self.b * (np.pi - th) / np.maximum(np.sin(th), 1e-3); rb = np.where(th < 1e-3, 1e6, rb)
        s = r / rb
        n = SKY._noise((H // 2, W // 2), 2.4, 5, kmin=3); n2 = SKY._noise((H // 2, W // 2), 2.0, 6, kmin=8)
        inner = np.clip(1 - s / 0.74, 0, 1)
        sheath = np.exp(-((s - 0.87) / 0.10) ** 2) * (0.75 + 0.35 * n + 0.2 * n2).clip(0.2, 2)
        rim = np.exp(-((s - 1.0) / 0.018) ** 2) + 0.35 * np.exp(-((s - 1.03) / 0.07) ** 2) * (s > 1)
        ts = np.exp(-((s - 0.74) / 0.012) ** 2)
        bow = np.exp(-((s - 1.25) / 0.16) ** 2) * (s > 1) * np.clip(X / 900 + 0.75, 0, 1)
        g = (inner[..., None] ** 1.5 * np.array([0.10, 0.075, 0.045]) * (1 / (0.15 + r / 260))[..., None] * 0.6
             + sheath[..., None] * np.array([0.050, 0.035, 0.085]) + rim[..., None] * np.array([0.10, 0.16, 0.34])
             + ts[..., None] * np.array([0.10, 0.08, 0.05]) + bow[..., None] * np.array([0.012, 0.020, 0.05]))
        g = g.astype(np.float32)
        self.glow = np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(g[..., c], np.float32), "F").resize((W, H), Image.BICUBIC)) for c in range(3)], -1)
        # particles: solar wind (source) and interstellar gas (uniform flow) in a Rankine half-body field, pre-simulated
        r_ = np.random.default_rng(3); NF = int((self.t1 - self.t0) * FPS) + 2; N1, N2 = 2600, 3600
        U = 2.4; m = U * self.b
        def vel(p):
            rr2 = (p ** 2).sum(1, keepdims=True) + 25.0
            return np.array([-U, 0.0]) + m * p / rr2
        p1 = r_.normal(0, 1, (N1, 2)); p1 = p1 / np.linalg.norm(p1, axis=1, keepdims=True) * r_.uniform(5, 500, (N1, 1))
        p2 = np.stack([r_.uniform(-900, 1500, N2), r_.uniform(-800, 800, N2)], 1)
        tr1 = np.zeros((NF, N1, 2), np.float32); tr2 = np.zeros((NF, N2, 2), np.float32)
        for k in range(-200, NF):
            v1 = vel(p1); sp = np.linalg.norm(v1, axis=1, keepdims=True)
            p1 = p1 + v1 * np.clip(3.2 / (sp + 1e-6), 0, 1.6) * np.where((p1 ** 2).sum(1, keepdims=True) < (0.72 * self.b) ** 2, 1.6, 0.55)
            dead = (p1[:, 0] < -760) | (np.abs(p1[:, 1]) > 700) | (r_.random(N1) < 0.004)
            nn = int(dead.sum())
            if nn:
                a = r_.uniform(0, 2 * np.pi, nn); p1[dead] = np.stack([np.cos(a), np.sin(a)], 1) * r_.uniform(4, 30, (nn, 1))
            p2 = p2 + vel(p2) * 0.75
            dead = p2[:, 0] < -900
            nn = int(dead.sum())
            if nn: p2[dead] = np.stack([r_.uniform(1350, 1500, nn), r_.uniform(-800, 800, nn)], 1)
            if k >= 0: tr1[k] = p1; tr2[k] = p2
        self.tr1, self.tr2 = tr1, tr2
        self.voy = plate("plate_fly")
        self.vdir = np.array([math.cos(math.radians(30)), -math.sin(math.radians(30))])
        self.rcross = self.b * (math.pi / 6) / 0.5

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0); k = min(int((t - self.t0) * FPS), len(self.tr1) - 2)
        lin = self.sk.crop(30 * u, 0) * 0.8 + self.glow * (0.9 + 0.1 * math.sin(t * 0.7))
        acc = Acc()
        for tr, colr, wg in ((self.tr1, np.array([1.0, 0.82, 0.5], np.float32), 0.10), (self.tr2, np.array([0.45, 0.65, 1.0], np.float32), 0.09)):
            a = tr[k]; b = tr[k + 1]
            for f in (0.0, 0.33, 0.66, 1.0):
                for g in (0.0, -1.5, -3.0):
                    q = a + (b - a) * (f + g)
                    acc.add(q[:, 0] + self.cx, q[:, 1] + self.cy, wg * (1.0 + g / 4.0), colr)
        lin += acc.image()
        flare(lin, self.cx, self.cy, 0.5, 0.55, streak=0.2, ghosts=False)
        # Voyager 1 on its way out
        rv = float(np.interp(t, [106.5, 113.6, 124.0], [215, self.rcross, 372]))
        vx, vy = self.cx + self.vdir[0] * rv, self.cy + self.vdir[1] * rv
        ts = np.linspace(40, rv, 200, dtype=np.float32)
        acc = Acc(); acc.add(self.cx + self.vdir[0] * ts, self.cy + self.vdir[1] * ts, 0.25, np.array([1.0, 0.85, 0.4], np.float32)); lin += acc.image()
        fl = math.exp(-((t - 113.6) / 0.8) ** 2)
        glow_dot(lin, vx, vy, 2.5 + 6 * fl, 2.2, (1.0, 0.9, 0.6)); glow_dot(lin, vx, vy, 0.3 + 1.0 * fl, 16, (1.0, 0.85, 0.5))
        disp = finish(lin, 1.25, bl=0.6, br=16)
        op = fade(t, 107.5, self.t1 - 0.4)
        draw_text(disp, "VOYAGER 1", vx + 26, vy - 22, 15, op, tracking=0.34, anchor="l", col=YEL)
        draw_text(disp, "THE SUN", self.cx, self.cy + 60, 13, op * 0.8, tracking=0.34, col=DIM)
        draw_text(disp, "SOLAR WIND", self.cx - 150, self.cy - 120, 14, op * 0.8, tracking=0.36, col=(0.95, 0.85, 0.65))
        o2 = fade(t, 109.5, self.t1 - 0.4)
        draw_text(disp, "TERMINATION SHOCK", self.cx + 30, self.cy + 262, 12, o2 * 0.75, tracking=0.34, col=DIM)
        draw_text(disp, "HELIOPAUSE", self.cx + 372, self.cy + 150, 16, o2, tracking=0.38, anchor="l", col=(0.7, 0.82, 1.0))
        draw_text(disp, "INTERSTELLAR GAS", 1500, 300, 15, o2 * 0.9, tracking=0.38, col=(0.6, 0.75, 1.0))
        line(disp, 1640, 330, 1380, 330, o2 * 0.5, col=(0.6, 0.75, 1.0)); line(disp, 1380, 330, 1394, 323, o2 * 0.5, col=(0.6, 0.75, 1.0)); line(disp, 1380, 330, 1394, 337, o2 * 0.5, col=(0.6, 0.75, 1.0))
        cap(disp, t, 111.8, self.t1 - 0.3, "25 AUGUST 2012  ·  ABOUT 121 TIMES THE EARTH–SUN DISTANCE", "THE FIRST HUMAN-MADE OBJECT IN INTERSTELLAR SPACE", size=30)
        note(disp, "SCHEMATIC  ·  THE TRUE SHAPE OF THE HELIOSPHERE IS UNCERTAIN  ·  VOYAGER IS STILL FAR INSIDE THE OORT CLOUD", fade(t, 108, self.t1))
        return disp


class Record(Shot):
    def setup(self):
        self.pa = plate("plate_record"); self.pb = plate("plate_cover")
        self.sa = SkyPlate(SKY.look_at_dir(SKY.gal_dir(-40, 20), 30), 40, mw=0.7)
        self.sb = SkyPlate(SKY.look_at_dir(SKY.gal_dir(5, -8), -20), 24, mw=0.55)

    def frame(self, t):
        if not hasattr(self, "pa"): self.setup()
        xa, xb = 133.4, 135.2
        wA = 1 - ss(xa, xb, t); out = np.zeros((H, W, 3), np.float32)
        sA = W / self.pa.w; sB = W / self.pb.w
        if wA > 0:
            u = (t - self.t0) / (xb - self.t0)
            lin = self.sa.crop(-60 + 90 * u, 20 * u)
            rgb, al = self.pa.place(sA * (1.0 + 0.22 * u), W / 2 + 60 * u, H / 2 - 120 * u); over(lin, rgb, al, 1.3)
            out += finish(lin, 1.2, bl=0.5) * wA
        if wA < 1:
            u = (t - xa) / (self.t1 - xa)
            lin = self.sb.crop(40 - 80 * u, 0)
            rgb, al = self.pb.place(sB * (1.03 + 0.09 * u), W / 2 - 150 + 50 * u, H / 2 + 6 * u); over(lin, rgb, al, 1.25)
            out += finish(lin, 1.15, bl=0.5) * (1 - wA)
        disp = out
        cap(disp, t, 125.2, 133.2, "THE GOLDEN RECORD", "GOLD-PLATED COPPER  ·  30 CM ACROSS  ·  MOUNTED ON THE SIDE OF THE SPACECRAFT", size=36)
        items = (("115", "IMAGES", 135.4), ("55", "LANGUAGES OF GREETING", 138.2), ("SOUNDS", "SURF · THUNDER · BIRDSONG · WHALES", 140.9), ("90 MIN", "OF MUSIC · BACH TO CHUCK BERRY", 144.3))
        op_all = 1 - ss(self.t1 - 0.9, self.t1 - 0.2, t)
        if t > 135.0:
            shade_rect(disp, 1180, 250, 1930, 850, 0.5 * ss(135.0, 136.0, t) * op_all, 90)
        for k, (a, b, tk) in enumerate(items):
            op = ss(tk, tk + 0.7, t) * op_all; y = 360 + k * 118
            draw_text(disp, a, 1290, y, 50, op, font=FONT_EXL, tracking=0.12, anchor="l", col=YEL)
            draw_text(disp, b, 1292, y + 50, 15, op * 0.9, tracking=0.30, anchor="l")
        note(disp, "OUR OWN MODEL  ·  COVER DIAGRAM STYLISED, NOT A COPY OF THE REAL ENGRAVING", fade(t, 125, self.t1))
        return disp


class Signal(Shot):
    def setup(self):
        self.p = plate("plate_sig"); R, lens, loc, sun = camjson("plate_sig")
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(110, 28), 6), fov_of(lens), mw=0.6)
        self.sun_px = project(R, lens, None, sun, self.p.w, self.p.h)
        self.feed_px = project(R, lens, loc, (0, 0, 1.9), self.p.w, self.p.h)

    def frame(self, t):
        if not hasattr(self, "p"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0); s0 = W / self.p.w
        sc = s0 * (1.0 + 0.08 * u); cx = W / 2 + 10 * u; cy = H / 2 + 8 * u
        def tp(p): return (cx + (p[0] - self.p.w / 2) * sc, cy + (p[1] - self.p.h / 2) * sc)
        sx, sy = tp(self.sun_px); fx, fy = tp(self.feed_px)
        lin = self.sk.crop(-30 * u, 10 * u)
        flare(lin, sx, sy, 1.5, 0.9, spikes=6, rot=0.35, streak=0.7)
        rgb, al = self.p.place(sc, cx, cy); over(lin, rgb, al, 1.25)
        disp = finish(lin, 1.15, bl=0.6)
        # radio waves leaving the dish towards the inner solar system
        dirx, diry = sx - fx, sy - fy; Ld = math.hypot(dirx, diry); a_dir = math.atan2(diry, dirx)
        op = fade(t, 150.6, self.t1 - 0.5, 1.0, 0.8)
        for k in range(14):
            s = ((t * 0.11 + k / 14.0) % 1.0)
            ring(disp, fx, fy, 30 + s * Ld * 0.95, op * 0.5 * (1 - s) ** 1.5, col=(0.6, 0.8, 1.0), wdt=1.1, a0=a_dir - 0.23, a1=a_dir + 0.23)
        o2 = fade(t, 152.0, self.t1 - 0.5)
        line(disp, sx + 18, sy - 18, sx + 90, sy - 90, o2 * 0.5)
        draw_text(disp, "THE SUN", sx + 98, sy - 108, 16, o2, tracking=0.36, anchor="l")
        draw_text(disp, "EARTH IS LOST IN ITS GLARE, A THIRD OF A DEGREE AWAY AT MOST", sx + 100, sy - 82, 12, o2 * 0.8, tracking=0.3, anchor="l", col=DIM)
        cap(disp, t, 153.6, self.t1 - 0.3, "TRANSMITTER POWER  ≈ 23 WATTS", "ABOUT THE SAME AS A REFRIGERATOR LIGHT BULB", size=36)
        note(disp, "OUR OWN MODEL  ·  LIGHTING THEATRICAL: REAL SUNLIGHT HERE IS ABOUT 30,000 TIMES WEAKER THAN AT EARTH", fade(t, 151, self.t1))
        return disp


class DSN(Shot):
    def setup(self):
        self.p = plate("plate_dsn"); j = json.load(open(os.path.join(PL_DIR, "plate_dsn", "cam.json")))
        self.sk = SkyPlate(np.array(j["R"]) if False else SKY.look_at_dir(SKY.gal_dir(-12, 9), 52), fov_of(j["lens"]), margin=1.3, mw=1.0)
        yy = np.arange(H, dtype=np.float32)[:, None]
        self.hglow = (np.exp(-np.clip(900 - yy, 0, None) / 150.0) * 0.05)[..., None] * np.array([0.9, 0.6, 0.35], np.float32) \
            + (np.exp(-np.clip(900 - yy, 0, None) / 420.0) * 0.02)[..., None] * np.array([0.35, 0.5, 0.9], np.float32)

    def frame(self, t):
        if not hasattr(self, "p"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0); s0 = W / self.p.w
        lin = self.sk.crop(-140 + 240 * u, 60 - 90 * u) + self.hglow
        sc = s0 * (1.0 + 0.09 * u)
        rgb, al = self.p.place(sc, W / 2 - 30 * u, H / 2 + 44 * u, 0.5, 0.5); over(lin, rgb, al, 1.2)
        disp = finish(lin, 1.2, bl=0.55)
        cap(disp, t, 163.8, 169.8, "RECEIVED POWER: FAR BELOW 10⁻¹⁸ WATT", "LESS THAN A BILLIONTH OF A BILLIONTH OF A WATT", size=32)
        cap(disp, t, 170.2, 177.0, "DEEP SPACE NETWORK  ·  70-METRE DISHES", "GOLDSTONE, CALIFORNIA   ·   MADRID, SPAIN   ·   CANBERRA, AUSTRALIA", size=32)
        op = fade(t, 177.3, self.t1 - 0.3)
        if op > 0:
            cap(disp, t, 177.3, self.t1 - 0.3, "160 BITS PER SECOND", f"BITS RECEIVED WHILE THIS CAPTION HAS BEEN ON SCREEN:  {int(max(0, t - 177.3) * 160):,}", size=36, col=YEL, subcol=WHITE)
        note(disp, "OUR OWN STYLISED MODEL OF A 70 M ANTENNA  ·  NOT A SPECIFIC STATION", fade(t, 164, self.t1))
        return disp


INSTR = (("IMAGING CAMERAS", "1990"), ("INFRARED SPECTROMETER", "1998"), ("PHOTOPOLARIMETER", "1980"), ("ULTRAVIOLET SPECTROMETER", "2016"),
         ("PLASMA SCIENCE", "2007"), ("PLANETARY RADIO ASTRONOMY", "2008"), ("COSMIC RAY SUBSYSTEM", "2025"), ("LOW-ENERGY CHARGED PARTICLES", "2026"),
         ("MAGNETOMETER", None), ("PLASMA WAVE SUBSYSTEM", None))


class Power(Shot):
    def setup(self):
        self.p = plate("plate_rtg")
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(60, -25), 15), 34, mw=0.6)
        order = sorted([i for i, (n, y) in enumerate(INSTR) if y], key=lambda i: INSTR[i][1])
        self.toff = {i: 190.3 + k * 0.62 for k, i in enumerate(order)}

    def frame(self, t):
        if not hasattr(self, "p"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0); s0 = W / self.p.w
        lin = self.sk.crop(50 - 100 * u, -10)
        dim = 1.0 - 0.25 * ss(190, 200, t)
        rgb, al = self.p.place(s0 * (1.0 + 0.10 * u), W / 2 - 60 - 50 * u, H / 2 + 30 * u); over(lin, rgb, al, 1.25 * dim)
        disp = finish(lin, 1.15, bl=0.5)
        op_all = fade(t, 184.2, self.t1 - 0.3, 0.8, 0.8)
        shade_rect(disp, 1090, 150, 1930, 800, 0.55 * op_all, 90)
        draw_text(disp, "TEN SCIENCE INSTRUMENTS", 1180, 226, 17, op_all, tracking=0.38, anchor="l", col=DIM)
        line(disp, 1180, 252, 1820, 252, op_all * 0.35)
        for i, (nm, yr) in enumerate(INSTR):
            y = 292 + i * 46; op = op_all * ss(184.6 + i * 0.12, 185.4 + i * 0.12, t)
            if yr:
                off = ss(self.toff[i], self.toff[i] + 0.5, t)
                draw_text(disp, nm, 1180, y, 17, op * (1 - 0.62 * off), tracking=0.26, anchor="l")
                draw_text(disp, "OFF  " + yr, 1820, y, 14, op * off * 0.75, tracking=0.3, anchor="r", col=DIM)
            else:
                on = ss(195.6, 196.6, t)
                draw_text(disp, nm, 1180, y, 17, op, tracking=0.26, anchor="l", col=tuple(np.array(WHITE) * (1 - on) + np.array(YEL) * on))
                draw_text(disp, "ON", 1820, y, 14, op * on, tracking=0.3, anchor="r", col=YEL)
        cap(disp, t, 184.0, 198.4, "POWER: THE HEAT OF DECAYING PLUTONIUM-238", "THREE GENERATORS  ·  ABOUT 4 WATTS LESS EVERY YEAR", size=28, y=H * 0.885)
        # command / reply light-time strip
        o2 = fade(t, 204.8, self.t1 - 0.3)
        if o2 > 0:
            xa, xb, y = 420.0, 1500.0, 930.0
            shade_rect(disp, 260, 850, 1660, 1040, 0.5 * o2, 70)
            line(disp, xa, y, xb, y, o2 * 0.4)
            ring(disp, xa, y, 7, o2, wdt=1.4); ring(disp, xb, y, 7, o2, wdt=1.4, col=YEL)
            draw_text(disp, "EARTH", xa - 24, y, 15, o2, tracking=0.34, anchor="r"); draw_text(disp, "VOYAGER 1", xb + 24, y, 15, o2, tracking=0.34, anchor="l", col=YEL)
            s = (t - 205.4) / 3.3
            if 0 <= s <= 1:
                x = xa + (xb - xa) * s; line(disp, max(xa, x - 90), y, x, y, o2, col=YEL, wdt=2.2)
                draw_text(disp, "COMMAND  ·  24 HOURS", (xa + xb) / 2, y - 36, 15, o2, tracking=0.34)
            elif 1 < s <= 2:
                x = xb - (xb - xa) * (s - 1); line(disp, x, y, min(xb, x + 90), y, o2, col=(0.6, 0.8, 1.0), wdt=2.2)
                draw_text(disp, "REPLY  ·  24 HOURS", (xa + xb) / 2, y - 36, 15, o2, tracking=0.34)
            elif s > 2:
                draw_text(disp, "ROUND TRIP  ·  ABOUT TWO DAYS", (xa + xb) / 2, y - 36, 15, o2, tracking=0.34, col=YEL)
        cap(disp, t, 199.6, 204.6, "2026: ONE MORE INSTRUMENT SWITCHED OFF", "AND THE POWER SYSTEM RECONFIGURED TO DELAY THE NEXT SHUTDOWN", size=28, y=H * 0.885)
        note(disp, "INSTRUMENT STATUS: NASA / JPL VOYAGER 1 STATUS, 2026", fade(t, 185, self.t1), x=1180, y=778)
        return disp


class Scale(Shot):
    LD_PER_LY = 365.25
    def setup(self):
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(-30, 6), 18), 60, mw=0.5)
        self.voy = plate("plate_fly")

    def frame(self, t):
        if not hasattr(self, "sk"): self.setup()
        u = (t - self.t0) / (self.t1 - self.t0)
        x0, Y = 250.0, 640.0
        zt = ss(226.3, 236.3, t)
        ppl = 1150.0 * (0.94 / 1150.0) ** zt                                 # pixels per light-day
        X = lambda d: x0 + d * ppl
        lin = self.sk.crop(-80 + 160 * u, 20 - 30 * u) * (0.75 + 0.25 * zt)
        # axis glow
        xe = min(W + 10, X(1596 if zt > 0 else 1.0))
        xs = np.arange(int(x0), int(min(W, xe)), dtype=np.float32)
        g = np.exp(-((np.arange(H, dtype=np.float32) - Y) / 1.2) ** 2)[:, None]
        lin[:, int(x0):int(x0) + len(xs)] += (g * 0.16)[..., None] * np.array([0.8, 0.85, 1.0], np.float32)
        # the travelled light-day (yellow)
        x1 = X(1.0); xs2 = np.arange(int(x0), int(min(W, max(x1, x0 + 1.5))) + 1, dtype=np.float32)
        lin[:, int(x0):int(x0) + len(xs2)] += (np.exp(-((np.arange(H, dtype=np.float32) - Y) / 1.6) ** 2)[:, None] * 1.2)[..., None] * np.array([1.0, 0.8, 0.3], np.float32)
        flare(lin, x0, Y, 0.55, 0.5 + 0.1 * (1 - zt), streak=0.2, ghosts=False)
        if x1 < W + 200 and zt < 0.6:
            rgb, al = self.voy.place(0.24 * (1 - zt) + 0.02, x1 + 10, Y - 8); over(lin, rgb * 1.5 * (1 - ss(0.3, 0.6, zt)), al * (1 - ss(0.3, 0.6, zt)))
        # Alpha Centauri
        xa = X(4.37 * self.LD_PER_LY); xp = X(4.246 * self.LD_PER_LY)
        if xa < W + 300:
            a = ss(0.75, 1.0, zt)
            flare(lin, xa, Y, 0.9 * a + 0.05, 0.6, col=(1.0, 0.93, 0.75), streak=0.3, ghosts=False)
            glow_dot(lin, xa + 5, Y - 2, 2.0 * a, 1.5, (1.0, 0.8, 0.55)); glow_dot(lin, xp, Y + 26, 1.4 * a, 1.3, (1.0, 0.45, 0.3))
        disp = finish(lin, 1.1)
        fo = 1 - ss(self.t1 - 0.9, self.t1 - 0.2, t)
        # phase A labels
        oa = fade(t, 215.0, 227.2)
        if oa > 0:
            draw_text(disp, "THE SUN", x0, Y + 70, 14, oa * 0.9, tracking=0.34, col=DIM)
            for d, nm in ((0.173, "NEPTUNE'S ORBIT"), (0.70, "HELIOPAUSE")):
                line(disp, X(d), Y - 12, X(d), Y + 12, oa * 0.6); draw_text(disp, nm, X(d), Y + 40, 12, oa * 0.75, tracking=0.3, col=DIM)
            ob = fade(t, 221.0, 227.2)
            line(disp, x0, Y - 60, x1, Y - 60, ob * 0.8, col=YEL); line(disp, x0, Y - 72, x0, Y - 48, ob * 0.8, col=YEL); line(disp, x1, Y - 72, x1, Y - 48, ob * 0.8, col=YEL)
            draw_text(disp, "1 LIGHT-DAY", (x0 + x1) / 2, Y - 108, 44, ob, font=FONT_EXL, tracking=0.3, col=YEL)
            draw_text(disp, "VOYAGER 1", x1 + 10, Y + 82, 14, oa * 0.9, tracking=0.34, col=DIM)
            o1 = fade(t, 216.8, 227.2); o2 = fade(t, 218.8, 227.2)
            draw_text(disp, "49 YEARS", 420, 300, 54, o1, font=FONT_EXL, tracking=0.2, anchor="l")
            draw_text(disp, "IN FLIGHT SINCE 1977", 424, 352, 14, o1 * 0.85, tracking=0.32, anchor="l", col=DIM)
            draw_text(disp, "17 KM / S", 900, 300, 54, o2, font=FONT_EXL, tracking=0.2, anchor="l")
            draw_text(disp, "ABOUT 61,000 KM/H RELATIVE TO THE SUN", 904, 352, 14, o2 * 0.85, tracking=0.32, anchor="l", col=DIM)
        # zoom-out ticks
        if zt > 0:
            for d, nm in ((10, "10 LIGHT-DAYS"), (100, "100 LIGHT-DAYS"), (365.25, "1 LIGHT-YEAR"), (730.5, "2"), (1095.75, "3"), (1461, "4 LIGHT-YEARS")):
                x = X(d)
                if x0 + 60 < x < W - 40:
                    o = fo * np.clip((x - x0 - 60) / 120, 0, 1) * (1.0 if d >= 365 else float(np.clip((W - x) / 500, 0, 1)) * (1 - ss(0.75, 0.95, zt)))
                    line(disp, x, Y - 10, x, Y + 10, o * 0.7); draw_text(disp, nm, x, Y + 38, 13, o * 0.85, tracking=0.3, col=DIM)
            oc = fade(t, 226.6, 236.6, 0.5, 0.6)
            draw_text(disp, f"WIDTH OF THIS VIEW:  {int(round((W - x0) / ppl)):,} LIGHT-DAYS", W / 2, 150, 20, oc, tracking=0.36)
        od = ss(236.0, 237.2, t) * fo
        if od > 0:
            draw_text(disp, "ALPHA CENTAURI", xa, Y - 120, 18, od, tracking=0.36)
            draw_text(disp, "4.37 LIGHT-YEARS", xa, Y - 92, 13, od * 0.85, tracking=0.32, col=DIM)
            draw_text(disp, "PROXIMA  ·  4.25", xp - 6, Y + 62, 12, od * 0.85, tracking=0.3, col=(1.0, 0.6, 0.5))
            line(disp, x0, Y - 22, x0, Y - 150, od * 0.6, col=YEL)
            draw_text(disp, "VOYAGER 1 SO FAR: 1 LIGHT-DAY", x0 - 40, Y - 196, 15, od, tracking=0.32, anchor="l", col=YEL)
            draw_text(disp, "LESS THAN ONE PIXEL AT THIS SCALE", x0 - 40, Y - 170, 12, od * 0.8, tracking=0.3, anchor="l", col=DIM)
        oe = fade(t, 232.5, 240.8)
        if oe > 0:
            shade_rect(disp, 380, 780, 1540, 1010, 0.4 * oe, 70)
            draw_text(disp, "MORE THAN 1,500 LIGHT-DAYS", W / 2, 850, 36, oe, font=FONT_EXL, tracking=0.3)
            o2 = fade(t, 235.6, 240.8)
            draw_text(disp, "AT VOYAGER'S SPEED:  ABOUT 75,000 YEARS", W / 2, 918, 24, o2, tracking=0.32, col=YEL)
        # phase C: where it is really going
        og = fade(t, 241.0, self.t1 - 0.2, 0.9, 0.8)
        if og > 0:
            s = ss(241.2, 245.5, t); ang = math.radians(25); Lp = 2.27 * self.LD_PER_LY * ppl
            ex, ey = x0 + math.cos(ang) * Lp * s, Y - math.sin(ang) * Lp * s
            n = int(Lp * s / 12)
            for k in range(n):
                a = k / max(n, 1)
                if k % 2 == 0: line(disp, x0 + (ex - x0) * a, Y + (ey - Y) * a, x0 + (ex - x0) * (a + 0.5 / max(n, 1)), Y + (ey - Y) * (a + 0.5 / max(n, 1)), og * 0.9, col=YEL, wdt=1.4)
            ring(disp, ex, ey, 6, og, col=YEL, wdt=1.4)
            o3 = fade(t, 245.3, self.t1 - 0.2)
            draw_text(disp, "VOYAGER 1 IN ABOUT 40,000 YEARS", ex - 30, ey - 34, 14, o3, tracking=0.32, anchor="r", col=YEL)
            gx, gy = ex + 1.6 * self.LD_PER_LY * ppl * math.cos(math.radians(-18)), ey + 1.6 * self.LD_PER_LY * ppl * math.sin(math.radians(-18)) * -1
            gy = ey - 150
            gx = ex + math.sqrt(max((1.6 * self.LD_PER_LY * ppl) ** 2 - 150 ** 2, 0))
            ring(disp, gx, gy, 3.5, o3, col=(1.0, 0.6, 0.45), wdt=3.5)
            nseg = 24
            for k in range(0, nseg, 2):
                line(disp, ex + (gx - ex) * k / nseg, ey + (gy - ey) * k / nseg, ex + (gx - ex) * (k + 1) / nseg, ey + (gy - ey) * (k + 1) / nseg, o3 * 0.55)
            draw_text(disp, "≈ 1.6 LIGHT-YEARS", (ex + gx) / 2, (ey + gy) / 2 + 30, 12, o3 * 0.85, tracking=0.3, col=DIM)
            draw_text(disp, "GLIESE 445", gx + 20, gy - 8, 16, o3, tracking=0.36, anchor="l")
            draw_text(disp, "A DIM RED DWARF, ITSELF DRIFTING TOWARDS US", gx + 20, gy + 18, 11, o3 * 0.8, tracking=0.28, anchor="l", col=DIM)
        note(disp, "SCHEMATIC  ·  DIRECTIONS FLATTENED ONTO THE SCREEN  ·  DISTANCES ALONG EACH LINE TO SCALE", fade(t, 227, self.t1))
        return disp


class End(Shot):
    def setup(self):
        self.p = plate("plate_end")
        self.sk = SkyPlate(SKY.look_at_dir(SKY.gal_dir(12, -6), 38), 52, margin=1.3, mw=1.05)

    def frame(self, t):
        if not hasattr(self, "p"): self.setup()
        u = (t - self.t0) / (284.0 - self.t0); u = min(u, 1.0)
        s0 = W / self.p.w
        sc = s0 * 1.05 * (0.085 / 1.05) ** (u ** 0.85)
        cx = 900 + 300 * u ** 0.8; cy = 560 - 150 * u ** 0.8
        lin = self.sk.crop(-150 + 260 * u, 70 - 120 * u)
        rgb, al = self.p.place(sc, cx, cy, 0.47, 0.52)
        over(lin, rgb, al, 1.25 * (1.0 - 0.55 * ss(0.2, 1.0, u)))
        disp = finish(lin, 1.15, bl=0.55)
        cap(disp, t, 263.2, 271.6, "THE GOLDEN RECORD", "EXPECTED TO REMAIN PLAYABLE FOR ABOUT A BILLION YEARS", size=30)
        op = fade(t, 274.3, 285.6, 1.0, 1.4)
        if op > 0:
            disp *= (1 - 0.25 * op)
            draw_text(disp, "ONE LIGHT-DAY FROM HOME", W / 2, 850, 46, op, font=FONT_EXL, tracking=0.46)
            draw_text(disp, "AND STILL GOING", W / 2, 912, 18, op * fade(t, 276.0, 285.6, 1.0, 1.4), tracking=0.6, col=YEL)
        disp *= (1 - ss(284.4, 287.4, t)) * ss(self.t0 - 1, self.t0 + 0.5, t)
        return disp


CLS = dict(hero=Hero, light=LightTimes, launch=Launch, jupiter=Jupiter, saturn=Saturn, pbd=PaleBlueDot, helio=Helio, record=Record,
           signal=Signal, dsn=DSN, power=Power, scale=Scale, end=End)
SHOTS = [CLS[n](a, b) for n, a, b in TL.SHOTS]
XF = TL.XF


def frame(t):
    out = None
    for i, s in enumerate(SHOTS):
        a = s.t0 - XF / 2 if i > 0 else -1; b = s.t1 + XF / 2 if i < len(SHOTS) - 1 else 1e9
        if a <= t < b:
            w = 1.0
            if i > 0: w *= ss(s.t0 - XF / 2, s.t0 + XF / 2, t)
            if i < len(SHOTS) - 1: w *= 1 - ss(s.t1 - XF / 2, s.t1 + XF / 2, t)
            if w <= 0.001: continue
            f = s.frame(t) * w
            out = f if out is None else out + f
    return out if out is not None else np.zeros((H, W, 3), np.float32)


if __name__ == "__main__":
    if sys.argv[1] == "still":
        os.makedirs(os.path.join(SCR, "chk"), exist_ok=True)
        for a in sys.argv[2:]:
            t0 = time.time(); f = frame(float(a))
            Image.fromarray(to8(f)).save(os.path.join(SCR, "chk", f"still_{float(a):06.1f}.png")); print(a, round(time.time() - t0, 2), flush=True)
    else:
        t0, t1 = float(sys.argv[1]), float(sys.argv[2]); f0, f1 = int(round(t0 * FPS)), int(round(t1 * FPS))
        name = f"seg_{f0:05d}"
        if os.path.exists(os.path.join(SEG, name + ".mp4")):
            print("exists", name); sys.exit(0)
        wr = Writer(name); st = time.time()
        for fi in range(f0, f1):
            wr.write(to8(frame(fi / FPS)))
            if (fi - f0) % 48 == 0: print(name, fi - f0, "/", f1 - f0, round(time.time() - st), "s", flush=True)
        wr.close(); print("done", name, round(time.time() - st), "s")
