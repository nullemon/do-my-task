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
from lib.sky import SkyCam, StarSky, day_sky, sun_disc, lens_flare, LensField
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
T_SC0 = LN["scope"]["start"] - 0.25
T_SC1 = LN["cold"]["start"] + 0.35
T_COLD = wt("cold", "COLD")
T_WEEK, T_YEAR = wt("cold", "−18°C"), wt("cold", "−73°C")
T_END = LN["end"]["start"]
T_LAST = LN["end"]["words"][-1]["t0"]

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
            self.sun = (650.0, 395.0); self.inset_c = (W / 2, 590.0); self.inset_r = 300
        else:
            self.sun = (1330.0, 215.0); self.inset_c = (1450.0, 420.0); self.inset_r = 290
        self.sun_r = self.f * 0.00465
        self.caps = Captions(self.L, WORDS, emphasis={"OUT", "BLACK", "NOON", "UNCHANGED", "6 KM", "−18°C", "−73°C", "SEE", "8 MIN", "AND 20 SEC", "TWILIGHT"})
        thetaE = 41.0
        self.thetaE = thetaE
        self.lens = LensField(half=230.0, res=0.15, n=260, seed=7, hero=[(-22.0, 0.0, 30.0, 9000.0), (95.0, -60.0, 10.0, 4200.0), (-40.0, 70.0, 8.0, 6000.0)],
                              galaxies=[(34.0, 2.6, 3.2, 0.6, 30.0, 0.16)])
        self.night_day = self.fg.night(1.0)
        self.day_fg = self.fg.day(1.0)

    # ----------------------------------------------------------------------------------------- state
    def st(self, t):
        s = {}
        s["sun"] = 1.0 if t < T_OUT else 0.0
        # camera exposure adaptation after the blackout: black, then the starlit scene fades up (eyes / auto-exposure)
        s["night"] = 0.0 if t < T_OUT else ease((t - T_OUT - 0.30) / 1.9) * (0.75 + 0.25 * ease((t - T_OUT - 2.2) / 2.5))
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
        s["inset"] = ramp(t, T_SC0, T_SC0 + 0.55) * (1 - ramp(t, T_SC1 - 0.35, T_SC1))
        s["orbit"] = ramp(t, T_ORB0, T_ORB0 + 0.5) * (1 - ramp(t, T_ORB1 - 0.4, T_ORB1))
        s["marker"] = ramp(t, T_BH - 0.4, T_BH) * (1 - ramp(t, T_SC0, T_SC0 + 0.3))
        return s

    # ----------------------------------------------------------------------------------------- frame
    def frame(self, t):
        L = self.L; W, H = L.W, L.H; s = self.st(t); fg = self.fg
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
        img = camera(img, t, s["zoom"], sx, sy, amp=1.0)
        if s["inset"] > 0: self.inset(img, t, s["inset"])
        img = bloom(img, 1.0 if s["sun"] > 0 else 0.6)
        out = tonemap(img, 1.1 if s["sun"] > 0 else 1.0)
        out = finish(out, t)
        self.overlay(out, t, s)
        return out

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
        """telescope view: point-lens lensing of background stars; grows out of the black hole's position"""
        R = self.inset_r; size = 2 * R
        u = (t - T_SC0) / (T_SC1 - T_SC0)
        off = (-60 + 120 * u, 2.0)                                    # relative drift (time-lapse)
        v = self.lens.view(size, 240.0, self.thetaE, off, seeing=0.9, ss=2) * 4.0
        yy, xx = np.mgrid[0:size, 0:size].astype(f32)
        d = np.sqrt((xx + 0.5 - R) ** 2 + (yy + 0.5 - R) ** 2) / R
        mask = smooth(1.0, 0.985, d)
        v = v * (1 - 0.35 * d[..., None] ** 4)                         # eyepiece vignette
        # reticle: thin cross with a gap, ticks; scale bar for the Einstein ring diameter
        ret = (((np.abs(xx - R) < 0.8) | (np.abs(yy - R) < 0.8)) & (d > 0.35) & (d < 0.97)).astype(f32) * 0.05
        ringE = np.clip(1 - np.abs(d * 120 - self.thetaE) / 0.35, 0, 1) * (np.sin(np.arctan2(yy - R, xx - R) * 36) > 0.2) * 0.06
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
        L = self.L; W = L.W
        cap_x = W / 2
        if not L.vertical and s["inset"] > 0.01: cap_x = 700
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
            hud_text(out, "TELESCOPE VIEW · 4′ FIELD · TIME-LAPSE", cx, cy - r - fs * 1.7, fs, "SemiBold", (230, 236, 245), al, 0.16)
            hud_text(out, "EINSTEIN RING ≈ 1.4′ · NO DISK: NOTHING FALLS IN", cx, cy + r + fs * 0.5, int(fs * 0.92), "SemiBold", (255, 196, 130), al, 0.10)
        # temperature counter
        if t > T_COLD - 0.4:
            a = ramp(t, T_COLD - 0.4, T_COLD + 0.1)
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
