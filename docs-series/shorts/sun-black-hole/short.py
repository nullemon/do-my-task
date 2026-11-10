"""WHAT IF THE SUN BECAME A BLACK HOLE? — vertical Short (and 16:9 recomposition), rendered with docs-series/shorts/lib.
Usage (always under nice, one heavy process at a time):
  /home/user/ttsenv/bin/python short.py vert            full render -> SCR/video_vert.mp4
  /home/user/ttsenv/bin/python short.py wide            16:9 render -> SCR/video_wide.mp4
  /home/user/ttsenv/bin/python short.py vert 1.0,9.5    stills at those times -> SCR/stills/vert_<t>.png
"""
import os, sys, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (sets up pylib path)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, kf, ramp, smooth, ease, noise1, splat, lum
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky, day_sky, sun_disc, lens_flare, LensSky
from lib import space as SP
from lib.text import Captions, hud_text, composite, font
from lib.post import camera, bloom, tonemap, finish, Encoder
from lib.audio import place

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S1-sun-black-hole"
FG_PATH = os.environ.get("FG", "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A_park.png")
LAMPS = [(630, 1185, 1336), (845, 1095, 1342)]      # lamp (head x, head y, pole base y) in SOURCE pixels of the PNG
FPS = 30
LEAD, TAIL = 0.25, 1.35

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]

T_NOW = wt("hook", "NOW")                            # the collapse happens "right now"
T_OUT = wt("out", "OUT") - 0.02                      # last sunlight arrives (T + 8:20)
T_SKY = LN["sky"]["start"]
T_ORB0, T_ORB1 = LN["orbit"]["start"] - 0.1, LN["bh"]["start"] + 0.2
T_BH = wt("bh", "6 KM")
T_SC0 = LN["scope"]["start"] - 0.55
T_COLD = wt("cold", "COLD")
T_WEEK, T_YEAR = wt("cold", "−18°C"), wt("cold", "−73°C")
T_END = LN["end"]["start"]
T_LAST = LN["end"]["words"][-1]["t0"]
T_SC1 = LN["cold"]["start"] - 0.02                   # inset closes as we cut to the freezing Earth
# shot list: the park is the anchor; cut-aways to the Sun (telescope) and to space
T_CUT_SUN = wt("hook", "BLACK") - 0.05
T_CUT_PARK1 = LN["delay"]["start"] - 0.05
T_CUT_COLLAPSE = LN["then"]["start"] - 0.05
T_COL0 = wt("then", "SUN") + 0.15                   # collapse starts
T_CUT_ORBIT = LN["orbit"]["start"] - 0.05
T_CUT_PARK3 = LN["bh"]["start"] - 0.05
T_CUT_FREEZE = LN["cold"]["start"] - 0.02
T_CUT_PARK4 = wt("cold", "IN", 1) - 0.06
T_CUT_END = LN["end"]["start"] - 0.05
SHOTS = [("park", 0.0), ("sun", T_CUT_SUN), ("park", T_CUT_PARK1), ("collapse", T_CUT_COLLAPSE), ("park", T_OUT),
         ("orbit", T_CUT_ORBIT), ("park", T_CUT_PARK3), ("freeze", T_CUT_FREEZE), ("park", T_CUT_PARK4), ("end", T_CUT_END)]
def shot_at(t):
    name, t0 = SHOTS[0]
    for n, a in SHOTS:
        if t >= a: name, t0 = n, a
    nxt = [a for n, a in SHOTS if a > t0]
    return name, t0, (nxt[0] if nxt else DUR)

# temperature model (rough published estimates, see README): global mean +15 C -> below -18 C in a week -> ~-73 C in a year
def temp_c(day):
    pts = [(0, 15.0), (1, 6.0), (3, -6.0), (7, -18.0), (30, -38.0), (100, -55.0), (365, -73.0)]
    x = math.log1p(max(day, 0)); xs = [math.log1p(d) for d, _ in pts]; ys = [v for _, v in pts]
    return float(np.interp(x, xs, ys))

def day_of(t):
    keys = [(T_COLD - 0.3, 0.0), (T_WEEK, 7.0), (T_YEAR, 365.0)]
    if t <= keys[0][0]: return 0.0
    if t >= keys[-1][0]: return 365.0
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if a <= t <= b:
            u = ease((t - a) / (b - a)); return math.expm1(math.log1p(va) + (math.log1p(vb) - math.log1p(va)) * u)


class Scene:
    def __init__(self, vertical=True):
        self.L = Layout(vertical); W, H = self.L.W, self.L.H
        self.fg = Foreground(FG_PATH, self.L, lamps=LAMPS, hz_frac=0.68)
        self.hz = self.fg.horizon
        self.f = 1150.0 if vertical else 1000.0
        self.cam = SkyCam(W, H, self.hz, self.f)
        self.stars = StarSky()
        if vertical:
            self.sun = (650.0, 395.0); self.inset_c = (W / 2, 612.0); self.inset_r = 340
        else:
            self.sun = (1330.0, 215.0); self.inset_c = (1440.0, 430.0); self.inset_r = 300
        self.sun_r = self.f * 0.00465
        self.caps = Captions(self.L, WORDS, emphasis={"OUT", "BLACK", "NOON", "UNCHANGED", "6 KM", "−18°C", "−73°C", "SEE", "8 MIN", "AND 20 SEC", "TWILIGHT"})
        thetaE = 41.0
        self.thetaE = thetaE
        # background behind the lens: a galaxy almost exactly behind it (-> Einstein ring), stars along the drift path
        self.lens = LensSky(half=150.0, res=0.1, n=110, seed=7, star_sig=0.45,
                            stars=[(-14.0, 7.0, 9.0, 9000.0), (10.0, -9.0, 7.0, 4500.0), (24.0, 16.0, 6.0, 6500.0), (-30.0, -18.0, 5.0, 3800.0)],
                            galaxies=[(0.0, 1.0, 2.6, 0.75, 20.0, 1.2, (1.0, 0.86, 0.66)), (0.0, 1.0, 9.0, 0.6, 20.0, 0.10, (0.9, 0.85, 0.8))])
        self.night_day = self.fg.night(1.0)
        self.day_fg = self.fg.day(1.0)

    # ----------------------------------------------------------------------------------------- state
    def st(self, t):
        s = {}
        s["sun"] = 1.0 if t < T_OUT else 0.0
        # camera exposure adaptation after the blackout: black, then the starlit scene fades up (eyes / auto-exposure)
        s["night"] = 0.0 if t < T_OUT else ease((t - T_OUT - 0.12) / 1.0) * (0.8 + 0.2 * ease((t - T_OUT - 1.2) / 2.5))
        s["lamps"] = 0.0
        for i, d in enumerate((2.0, 2.45)):
            u = t - T_OUT - d
            if u > 0: s["lamps"] = max(s["lamps"], min(1.0, u / 0.6) * (0.6 + 0.4 * (np.sin(u * 40) > -0.3 if u < 0.4 else 1)))
        s["frost"] = ramp(t, T_COLD - 0.2, T_WEEK + 0.4) * 0.55 + ramp(t, T_WEEK + 0.4, T_END + 1.0) * 0.45
        # zoom: slow push on the sun until it goes out; ease back; push on the black hole spot for the "6 km" beat
        z = 1.0 + 0.07 * ease((t - 0.0) / max(T_OUT, 1e-3)) if t < T_OUT else 1.07 - 0.07 * ease((t - T_OUT - 0.4) / 3.0)
        z += 0.06 * ramp(t, T_BH - 0.8, T_BH + 0.6) * (1 - ramp(t, T_SC1 - 0.2, T_SC1 + 1.0))
        z += 0.03 * ramp(t, T_END, DUR) * 0 - 0.025 * ramp(t, T_END, DUR)
        s["zoom"] = z
        s["inset"] = ramp(t, T_SC0, T_SC0 + 0.55) * (t < T_SC1)
        s["orbit"] = 0.0
        s["marker"] = ramp(t, T_CUT_PARK3 + 0.15, T_CUT_PARK3 + 0.5) * (1 - ramp(t, T_SC0, T_SC0 + 0.3))
        return s

    # ----------------------------------------------------------------------------------------- frame
    def frame(self, t):
        name, t0, t1 = shot_at(t)
        s = self.st(t); s["shot"] = name; s["t0"] = t0
        punch = 1 + 0.045 * math.exp(-(t - t0) / 0.10) if t0 > 0 else 1.0          # quick punch-in on every cut
        if name == "park":
            img = self.park(t, s, punch)
            bl, ex = (1.0 if s["sun"] > 0 else 0.6), (1.1 if s["sun"] > 0 else 1.0)
        else:
            img = getattr(self, "shot_" + name)(t, s, t0, t1)
            img = camera(img, t, punch, amp=0.6, seed=3)
            bl, ex = (0.45, 0.75) if name in ("sun", "collapse") else (0.8, 1.0)
        img = bloom(img, bl)
        out = tonemap(img, ex)
        out = finish(out, t)
        self.overlay(out, t, s)
        return out

    def park(self, t, s, punch):
        L = self.L; W, H = L.W, L.H; fg = self.fg
        sx, sy = self.sun
        img = np.zeros((H, W, 3), f32)
        if s["sun"] > 0:
            img += day_sky(self.cam, sx, sy, t, 1.0, cirrus=0.0)
            sun_disc(img, sx, sy, self.sun_r, 1.0)
        if s["night"] > 0:
            img += self.stars.render(self.cam, t, cx=2350, cy=1150, rot=-8 + t * 0.004, gain=1.0, twinkle=1.0, plate_gain=0.6)
        # foreground
        a = fg.a[..., None]
        if s["sun"] > 0:
            fgc = self.day_fg
        else:
            nl = 0.072
            fgc = self.night_day * nl
            fgc = fg.frost(fgc, s["frost"], t, level=nl * 1.4)
            fgc = fg.lamps_light(fgc, s["lamps"], t)
        img = img * (1 - a) + fgc * a
        if s["sun"] > 0:
            lens_flare(img, sx, sy, 1.0)
        # orbit diagram (not to scale) around the black hole's position
        if s["orbit"] > 0: self.orbit_diagram(img, t, s["orbit"])
        if s["marker"] > 0: self.marker(img, t, s["marker"])
        # exposure: day as shot; night scaled up to the adapted level
        expo = 1.0 if s["sun"] > 0 else max(s["night"], 0.0) * 1.0
        img = img * expo
        # camera move + handheld micro-motion (centre on the sun / black hole spot)
        img = camera(img, t, s["zoom"] * punch, sx, sy, amp=1.0, shake=(9.0 * math.exp(-(t - T_OUT) / 0.35) if t >= T_OUT else 0.0))
        if s["inset"] > 0: self.inset(img, t, s["inset"])
        return img

    # ----------------------------------------------------------------------------------------- cut-aways
    def shot_sun(self, t, s, t0, t1, collapse=False):
        """solar-telescope close-up: textured photosphere, prominences, corona"""
        W, H = self.L.W, self.L.H; v = self.L.vertical
        img = np.zeros((H, W, 3), f32)
        cx, cy = (W / 2, 0.43 * H) if v else (W / 2, H / 2)
        R0 = (0.36 * W if v else 0.30 * H) * (1 + 0.05 * (t - t0) / max(t1 - t0, 1e-3))
        img += SP.space_sky(self.stars, W, H, 1500, 1280, rot=10, scale=0.9, gain=0.25)
        if not collapse:
            SP.sun_disc(img, cx, cy, R0, t * 30, power=0.8, corona=0.45, col=(1.0, 0.50, 0.14), gran_amp=0.10)
            return img
        u = (t - T_COL0) / max(T_OUT - 0.10 - T_COL0, 1e-3)
        if u <= 0:
            SP.sun_disc(img, cx, cy, R0, t * 30, power=0.8, corona=0.45, col=(1.0, 0.50, 0.14), gran_amp=0.10); return img
        if u < 1:                                   # implosion (time-compressed): radius -> 0, surface brightens
            k = (1 - ease(u) ** 0.9) ** 1.6
            R = max(R0 * k, 1.5)
            pw = 0.8 * min((R0 / R) ** 0.6, 60.0)
            SP.sun_disc(img, cx, cy, R, t * 30, power=pw, corona=0.45 * max(0.0, 1 - u * 1.4), col=(1.0, 0.50, 0.14), gran_amp=0.10)
            # infalling glow streaks
            splat(img, cx, cy, R0 * 1.4, lambda d, dx, dy: (np.exp(-d / (R0 * 0.25 + 4)) * 0.6 * ease(u))[..., None] * np.array([1.0, 0.7, 0.4], f32))
            return img
        # last instant: a point flash, then nothing
        f = math.exp(-(t - (T_OUT - 0.10)) / 0.03)
        splat(img, cx, cy, W, lambda d, dx, dy: ((np.exp(-d / 3.0) * 400 + np.exp(-d / 40.0) * 12 + np.exp(-d / 300.0) * 1.2) * f)[..., None] * np.array([1.0, 0.92, 0.85], f32))
        return img

    def shot_collapse(self, t, s, t0, t1):
        return self.shot_sun(t, s, t0, t1, collapse=True)

    def _space_bg(self, t, cx=2060, cy=1280, rot=-32):
        W, H = self.L.W, self.L.H
        return SP.space_sky(self.stars, W, H, cx + 6 * t, cy, rot=rot, scale=0.85, gain=1.0, plate_gain=0.9)

    def _orbit_line(self, img, cx, cy, a, b, ang, alpha, front_only_behind=None):
        W, H = self.L.W, self.L.H; S = 4
        lay = np.zeros((H, W), np.uint8)
        cv2.ellipse(lay, (int(cx * S), int(cy * S)), (int(a * S), int(b * S)), ang, 0, 360, 255, 2, cv2.LINE_AA, 2)
        m = cv2.GaussianBlur(lay.astype(f32) / 255, (0, 0), 0.7)
        yy = np.arange(H, dtype=f32)[:, None]; far = 0.35 + 0.65 * smooth(cy - b, cy + b, yy)          # far side of the orbit dimmer
        m = m * far
        img += (m * alpha * 0.30)[..., None] * np.array([0.55, 0.78, 1.0], f32) + cv2.GaussianBlur(m, (0, 0), 6)[..., None] * alpha * 0.18 * np.array([0.3, 0.5, 1.0], f32)

    def _orbit_point(self, cx, cy, a, b, ang, ph):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        ex, ey = a * math.cos(ph), b * math.sin(ph)
        return cx + ex * ca - ey * sa, cy + ex * sa + ey * ca

    def space_layout(self):
        W, H = self.L.W, self.L.H
        if self.L.vertical: return dict(bh=(540.0, 640.0), a=470.0, b=290.0, ang=-6.0, earthR=210.0, thE=80.0)
        return dict(bh=(820.0, 380.0), a=640.0, b=230.0, ang=-4.0, earthR=170.0, thE=70.0)

    def shot_orbit(self, t, s, t0, t1):
        """Earth (no sunlight: city lights + faint fill) on its unchanged orbit around the black hole (enlarged, lensing the sky)"""
        W, H = self.L.W, self.L.H; Ly = self.space_layout(); u = (t - t0) / (t1 - t0)
        img = self._space_bg(t)
        bx, by = Ly["bh"]
        img = SP.lens_warp(img, bx, by, Ly["thE"], shadow=0.42)
        self._orbit_line(img, bx, by, Ly["a"], Ly["b"], Ly["ang"], 1.0)
        ph = 1.25 + 0.05 * u
        ex, ey = self._orbit_point(bx, by, Ly["a"], Ly["b"], Ly["ang"], ph)
        SP.earth(img, ex, ey, Ly["earthR"] * (1 + 0.04 * u), lon0=math.radians(-20 + 25 * (t - t0)), sun=0.0, amb=0.07, lights=1.0, rim=1.0, tip=18)
        self._space_geom = dict(bh=(bx, by), earth=(ex, ey, Ly["earthR"]))
        return img

    def shot_freeze(self, t, s, t0, t1):
        W, H = self.L.W, self.L.H; u = (t - t0) / (t1 - t0)
        img = self._space_bg(t, 1500, 1280, -32)
        cx, cy, R = (W / 2, 0.43 * H, 0.47 * W) if self.L.vertical else (W * 0.62, H * 0.52, 0.40 * H)
        fr = 0.12 + 0.55 * ease(u)
        SP.earth(img, cx, cy, R * (1 + 0.03 * u), lon0=math.radians(10 + 8 * (t - t0)), sun=0.0, amb=0.10, frost=fr, lights=1.0 - 0.25 * u,
                 cloud_amt=1.0 - 0.4 * u, rim=1.0, tip=28)
        return img

    def shot_end(self, t, s, t0, t1):
        """pull back from the frozen Earth: lights go out, the orbit and the black hole come into view"""
        W, H = self.L.W, self.L.H; Ly = self.space_layout(); u = (t - t0) / (t1 - t0)
        img = self._space_bg(t)
        bx, by = Ly["bh"]
        pull = ease(min(1.0, u / 0.75))
        thE = Ly["thE"] * (1 - 0.45 * ease((u - 0.65) / 0.35))
        img = SP.lens_warp(img, bx, by, thE * (0.3 + 0.7 * pull), shadow=0.42)
        self._orbit_line(img, bx, by, Ly["a"], Ly["b"], Ly["ang"], ramp(u, 0.25, 0.6))
        ex, ey = self._orbit_point(bx, by, Ly["a"], Ly["b"], Ly["ang"], 1.30 + 0.05 * u)
        c0 = (W / 2, 0.43 * H, 0.47 * W) if self.L.vertical else (W * 0.62, H * 0.52, 0.40 * H)
        cx = c0[0] + (ex - c0[0]) * pull; cy = c0[1] + (ey - c0[1]) * pull; R = c0[2] + (Ly["earthR"] * 0.8 - c0[2]) * pull
        lights = 1.0 - ease((t - T_CUT_END - 0.6) / 3.2)
        SP.earth(img, cx, cy, R, lon0=math.radians(30 + 8 * (t - t0)), sun=0.0, amb=0.10, frost=0.67 + 0.33 * ease(u), lights=0.75 * lights,
                 cloud_amt=0.6 - 0.3 * u, rim=1.0, tip=28 - 10 * pull)
        self._space_geom = dict(bh=(bx, by), earth=(cx, cy, R))
        return img

    def orbit_diagram(self, img, t, a):
        W, H = self.L.W, self.L.H; cx, cy = self.sun
        R = (300 if self.L.vertical else 330); b = R * 0.26
        lay = np.zeros((H, W), np.uint8)
        cv2.ellipse(lay, (int(cx * 4), int(cy * 4)), (int(R * 4), int(b * 4)), -8, 0, 360, 255, 4, cv2.LINE_AA, 2)
        m = cv2.GaussianBlur(lay.astype(f32) / 255, (0, 0), 0.6)
        img += (m * a * 0.9)[..., None] * np.array([0.55, 0.75, 1.0], f32) + cv2.GaussianBlur(m, (0, 0), 6)[..., None] * a * 0.5 * np.array([0.3, 0.5, 1.0], f32)
        ph = (t - T_ORB0) * 0.9 + 1.0
        ca, sa = math.cos(math.radians(-8)), math.sin(math.radians(-8))
        ex, ey = R * math.cos(ph), b * math.sin(ph)
        px, py = cx + ex * ca - ey * sa, cy + ex * sa + ey * ca
        splat(img, px, py, 60, lambda d, dx, dy: ((np.clip(6 - d, 0, 1) * 6 + np.exp(-d / 8) * 0.8) * a)[..., None] * np.array([0.45, 0.7, 1.0], f32))
        splat(img, cx, cy, 30, lambda d, dx, dy: (np.clip(1 - np.abs(d - 9) / 1.5, 0, 1) * 0.9 * a)[..., None] * np.array([1.0, 0.75, 0.45], f32))
        self._orbit_earth = (px, py)

    def marker(self, img, t, a):
        cx, cy = self.sun
        def fn(d, dx, dy):
            ring = np.clip(1 - np.abs(d - 22) / 1.4, 0, 1)
            gap = (np.abs(dx) < 3) | (np.abs(dy) < 3)
            tick = ((np.abs(dx) < 1.2) & (np.abs(dy) > 28) & (np.abs(dy) < 44)) | ((np.abs(dy) < 1.2) & (np.abs(dx) > 28) & (np.abs(dx) < 44))
            return ((ring * ~gap + tick) * 0.9 * a)[..., None] * np.array([1.0, 0.72, 0.4], f32)
        splat(img, cx, cy, 50, fn)

    def inset(self, img, t, a):
        """telescope view: point-lens lensing (exact map) of a slowly drifting background; grows out of the black hole's spot"""
        R = self.inset_r; size = 2 * R
        u = (t - T_SC0) / (T_SC1 - T_SC0)
        off = (-22 + 44 * u, 0.0)                                     # lens drifts across the background (time-lapse)
        v = self.lens.view(size, 180.0, self.thetaE, off, shadow=0.45, ss=2, seeing=0.7) * 7.0
        yy, xx = np.mgrid[0:size, 0:size].astype(f32)
        d = np.sqrt((xx + 0.5 - R) ** 2 + (yy + 0.5 - R) ** 2) / R
        mask = smooth(1.0, 0.985, d)
        v = v * (1 - 0.35 * d[..., None] ** 4)                         # eyepiece vignette
        # reticle: thin cross with a gap, ticks; scale bar for the Einstein ring diameter
        ret = (((np.abs(xx - R) < 0.8) | (np.abs(yy - R) < 0.8)) & (d > 0.62) & (d < 0.97)).astype(f32) * 0.05
        ringE = 0.0
        v += (ret + ringE)[..., None] * np.array([1.0, 0.6, 0.3], f32)
        rim = np.clip(1 - np.abs(d - 1.0) / 0.006, 0, 1)
        g = ease(a)
        cx0, cy0 = self.sun; cx1, cy1 = self.inset_c
        cx, cy = cx0 + (cx1 - cx0) * g, cy0 + (cy1 - cy0) * g
        sc = max(0.02, g)
        M = np.array([[sc, 0, cx - R * sc], [0, sc, cy - R * sc]], np.float64)
        Wd, Hd = self.L.W, self.L.H
        vw = cv2.warpAffine(v, M, (Wd, Hd), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        mw = cv2.warpAffine(mask, M, (Wd, Hd), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        rw = cv2.warpAffine(rim, M, (Wd, Hd), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        # darken the scene around the eyepiece a little
        yy2, xx2 = np.ogrid[0:Hd, 0:Wd]
        dd = np.sqrt((xx2 - cx) ** 2 + (yy2 - cy) ** 2) / (R * sc + 1)
        dim = 1 - 0.55 * a * smooth(3.5, 1.0, dd)
        img *= dim[..., None]
        img[:] = img * (1 - mw[..., None]) + vw * mw[..., None] + rw[..., None] * 0.6 * a * np.array([0.9, 0.95, 1.0], f32)
        self._inset_geom = (cx, cy, R * sc, a)

    # ----------------------------------------------------------------------------------------- 2D overlays (sRGB)
    def overlay(self, out, t, s):
        L = self.L; W = L.W; H_ = L.H
        cap_x = W / 2
        if not L.vertical and s["inset"] > 0.01: cap_x = 700
        L.cap_y = (1010 + 105 * ease(s["inset"] * 1.5)) if L.vertical else 560
        # clock: T + m:ss from the collapse to the last light
        if T_NOW - 0.1 < t < T_OUT + 1.6:
            u = min(max((t - T_NOW) / (T_OUT - T_NOW), 0.0), 1.0)
            sec = 500 * (u ** 1.6) if t < T_OUT else 500
            a = ramp(t, T_NOW - 0.1, T_NOW + 0.25) * (1 - ramp(t, T_OUT + 1.1, T_OUT + 1.6))
            col = (255, 255, 255) if t < T_OUT else (255, 120, 60)
            hud_text(out, f"T + {int(sec) // 60}:{int(sec) % 60:02d}", W / 2, L.hud_y, L.hud_size, "Bold", col, a, 0.04, display=True)
            hud_text(out, "SUNLIGHT STILL ON ITS WAY" if t < T_OUT else "LAST LIGHT ARRIVES", W / 2, L.hud_y + L.hud_size * 1.25, int(L.hud_size * 0.38), "SemiBold", (215, 225, 240), a * 0.9, 0.22)
        if s["marker"] > 0.01:
            cx, cy = self.cam_xy(t, *self.sun)
            hud_text(out, "BLACK HOLE · ~6 KM ACROSS", cx, cy + 62, int(L.hud_size * 0.40), "SemiBold", (255, 200, 140), s["marker"], 0.18)
            hud_text(out, "invisible to the eye", cx, cy + 62 + L.hud_size * 0.62, int(L.hud_size * 0.36), "Regular", (220, 228, 240), s["marker"] * 0.85, 0.10)
        if s["orbit"] > 0.01:
            cx, cy = self.cam_xy(t, *self.sun)
            hud_text(out, "SAME MASS · SAME ORBIT", cx, cy - (300 * 0.26 + 70), int(L.hud_size * 0.42), "SemiBold", (190, 215, 255), s["orbit"], 0.2)
            hud_text(out, "not to scale", cx, cy + 300 * 0.26 + 40, int(L.hud_size * 0.32), "Regular", (190, 205, 230), s["orbit"] * 0.8, 0.1)
        if s["inset"] > 0.6:
            cx, cy, r, a = self._inset_geom
            al = ramp(a, 0.6, 1.0)
            fs = int(L.hud_size * 0.36)
            hud_text(out, "TELESCOPE VIEW · 3′ FIELD · TIME-LAPSE", cx, cy - r - fs * 1.5, fs, "SemiBold", (230, 236, 245), al, 0.16)
            hud_text(out, "BLACK HOLE ENLARGED · EINSTEIN RING ≈ 1.4′", cx, cy + r + fs * 0.45, int(fs * 0.95), "SemiBold", (255, 196, 130), al, 0.10)
            hud_text(out, "NO DISK: NOTHING IS FALLING IN", cx, cy + r + fs * 1.75, int(fs * 0.85), "SemiBold", (215, 225, 240), al * 0.9, 0.12)
        # shot labels (small, honest)
        sh, t0 = s["shot"], s["t0"]; fs = int(L.hud_size * 0.40); top = L.safe_top + 40 if L.vertical else 70
        def lab(txt, x, y, a, col=(225, 232, 245), size=fs, wt="SemiBold", tr=0.18):
            if a > 0.01: hud_text(out, txt, x, y, size, wt, col, a, tr)
        fin = ramp(t, t0 + 0.1, t0 + 0.4)
        if sh == "sun": lab("THE SUN · SOLAR-TELESCOPE VIEW", W / 2, top, fin)
        if sh == "collapse":
            lab("WHAT REACHES US AT T + 8:20", W / 2, top, fin)
            lab("TIME-COMPRESSED ILLUSTRATION", W / 2, top + fs * 1.5, fin * 0.85, (255, 196, 130), int(fs * 0.85))
        if sh in ("orbit", "end") and hasattr(self, "_space_geom"):
            g = self._space_geom; bx, by = g["bh"]
            a_bh = fin if sh == "orbit" else ramp(t, t0 + 2.2, t0 + 2.8)
            lab("BLACK HOLE (ENLARGED)", bx, by + self.space_layout()["thE"] * 0.9 + 24, a_bh, (255, 200, 140), int(fs * 0.9))
            if sh == "orbit":
                lab("SAME MASS · SAME ORBIT", W / 2, top, fin, (195, 220, 255), int(fs * 1.15))
            lab("ILLUSTRATION · NOT TO SCALE · BRIGHTENED", W / 2, (L.safe_bot - 40) if L.vertical else H_ - 40, a_bh * 0.8, (190, 200, 220), int(fs * 0.75))
        if sh == "freeze":
            lab("EARTH WITH NO SUNLIGHT · BRIGHTENED", W / 2, top, fin, (205, 220, 240), int(fs * 0.9))
        # temperature counter
        show_temp = (t > T_COLD - 0.4) and t < T_CUT_END + 2.6
        if show_temp:
            a = ramp(t, T_COLD - 0.4, T_COLD + 0.1) * (1 - ramp(t, T_CUT_END + 2.0, T_CUT_END + 2.6))
            d = day_of(t); tc = temp_c(d); tf = tc * 9 / 5 + 32
            sign = "−" if tc < -0.5 else "+"
            hud_text(out, f"{sign}{abs(round(tc)):d}°C", W / 2, L.hud_y, int(L.hud_size * 1.1), "Bold", (225, 240, 255), a, 0.02, display=True)
            sf = "−" if tf < -0.5 else ""
            lab = f"DAY {int(d)}" if d >= 1 else "DAY 0"
            hud_text(out, f"EARTH AVERAGE · {lab} · {sf}{abs(round(tf))}°F", W / 2, L.hud_y + L.hud_size * 1.45, int(L.hud_size * 0.38), "SemiBold", (200, 215, 235), a * 0.9, 0.18)
        if t > T_LAST + 0.8:
            pass
        self.caps.L = L
        if cap_x != W / 2:
            saved = L.W; self._cap_draw_x(out, t, cap_x)
        else:
            self.caps.draw(out, t)

    def _cap_draw_x(self, out, t, cx):
        a = self.caps.active(t)
        if not a: return
        i, w, end = a
        from lib.text import word_layer
        rgba, _ = word_layer(w["cap"], self.L.cap_size, 640, scale=1.0)
        composite(out, rgba, cx, self.L.cap_y, min(1.0, (end - t) / 0.06))

    def cam_xy(self, t, x, y):
        """where a scene point lands after camera() (ignores the tiny handheld rotation)"""
        s = self.st(t); z = s["zoom"] * (1.02 + 0.004)
        from lib.post import handheld
        dx, dy, _ = handheld(t)
        sx, sy = self.sun
        return sx + (x - sx) * z + dx, sy + (y - sy) * z + dy


def run(vertical, stills=None):
    sc = Scene(vertical)
    tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); im = sc.frame(t)
            Image.fromarray((im * 255 + 0.5).astype(np.uint8)).save(os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=16)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0)


if __name__ == "__main__":
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    print(f"DUR {DUR}  T_NOW {T_NOW:.2f} T_OUT {T_OUT:.2f} T_ORB {T_ORB0:.2f} T_BH {T_BH:.2f} T_SC {T_SC0:.2f}-{T_SC1:.2f} T_COLD {T_COLD:.2f} T_WEEK {T_WEEK:.2f} T_YEAR {T_YEAR:.2f} T_END {T_END:.2f}")
    run(vert, st)
