"""IN 1994, PEOPLE CALLED 911 ABOUT A STRANGE CLOUD. IT WAS THE MILKY WAY. — vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the user's city plate (C_city.png) for the whole Short. Everything happens in the sky
and in the city lights: light-polluted orange dome -> the Northridge jolt -> windows and street lamps die block by block
-> the skyglow drains -> stars, then the Milky Way -> (end) the lights come back and the Milky Way drowns again (loops).
Built on docs-series/shorts/lib (read-only; nothing in lib/ is modified).
Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, lin_to_srgb, srgb_to_lin, fbm2
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from mw import milky_way

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S2-milky-way-blackout"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/C_city.png"
# street-lamp heads in SOURCE px of C_city.png (941x1672), found by eye on a 2x crop
LAMPS_SRC = [(575, 1496), (703, 1449), (819, 1456), (470, 1386), (237, 1303)]
# a few lights that survive the blackout (battery lanterns / a car), SOURCE px
SURVIVE_SRC = [(547, 1592), (33, 1418), (264, 1404), (690, 1338)]
FPS = 30
LEAD, TAIL = 0.25, 1.45

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]

T_HIT = wt("quake", "HIT")                 # the jolt lands on "hit"
T_SHAKE0, T_SHAKE1 = T_HIT - 0.12, T_HIT + 1.25
T_OFF0 = T_HIT + 0.55                      # first wave of windows dies
T_OFF1 = wt("dark", "DARK") + 0.15         # last wave
T_DRAIN0 = T_OFF1 - 0.10; T_DRAIN1 = T_DRAIN0 + 2.2      # skyglow drains away
T_STARS = LN["look"]["start"] - 0.15       # stars pop in
T_MW0 = wt("look", "UP") - 0.10; T_MW1 = T_MW0 + 3.2     # the Milky Way rises out of the dark
T_RET0 = wt("end", "RIGHT") - 0.25         # the lights come back
T_RET1 = DUR - 0.15
LAMP_OFF = [T_OFF0 + 0.15 + k for k in (0.55, 0.30, 0.95, 0.75, 1.15)]     # each street lamp dies with its block
LAMP_ON = [T_RET0 + 0.3 + k for k in (0.5, 0.2, 0.7, 0.9, 1.1)]


# ------------------------------------------------------------------------------------------------- city lights
class City:
    """Light decomposition of the dusk photo: photo = D (all lights off) + window light + lamp light.
    Windows are connected components of bright, warm, locally-peaked pixels; each switches off individually."""
    def __init__(self, fg, layout, seed=3):
        self.fg = fg; self.L = layout; W, H = layout.W, layout.H; s, oy = fg.s, fg.oy
        rng = np.random.default_rng(seed)
        P = fg.rgb; a = fg.a
        sr = lin_to_srgb(P); R, G, B = sr[..., 0], sr[..., 1], sr[..., 2]
        Y = 0.2126 * R + 0.7152 * G + 0.0722 * B
        Ym = cv2.GaussianBlur(Y * a, (0, 0), 4.0 * s) / np.maximum(cv2.GaussianBlur(a, (0, 0), 4.0 * s), 1e-3)
        warm = (R - B > 0.10) & (R > 0.40)
        peak = (Y - Ym > 0.045) | (Y > 0.62)
        win = (warm & peak & (a > 0.9)).astype(np.uint8)
        win = cv2.morphologyEx(win, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        self.lamps = [(x * s, y * s + oy) for x, y in LAMPS_SRC]
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        # lamp light on trees / road / walls: warm excess around each head, pool spread downward
        Gs = []
        for lx, ly in self.lamps:
            dy = yy - ly
            ry = np.where(dy > 0, 150 * s, 60 * s)
            Gs.append(np.exp(-((xx - lx) / (95 * s)) ** 2 - (dy / ry) ** 2))
        Gs = np.stack(Gs); gsum = Gs.sum(0)
        self.lamp_id = Gs.argmax(0).astype(np.int32)
        chroma = np.clip(((R - B) / np.maximum(R + G + B, 1e-3) - 0.08) / 0.25, 0, 1)
        glow = np.clip(gsum * 1.3, 0, 1) * chroma * a
        glow = cv2.GaussianBlur(glow, (0, 0), 1.2)
        # windows: soft mask; components (very large blobs = lamp-lit foliage near lamps -> lamp light instead)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(win, 8)
        near = gsum[np.clip(cent[:, 1].astype(int), 0, H - 1), np.clip(cent[:, 0].astype(int), 0, W - 1)]
        is_lamp = (near > 0.35) & (stats[:, cv2.CC_STAT_AREA] < 4000)
        is_lamp[0] = False
        winmask = (lab > 0) & ~is_lamp[lab]
        self.n = n; self.label = lab.astype(np.int32)
        Wm = cv2.GaussianBlur(cv2.dilate(winmask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(f32), (0, 0), 0.7)
        Wm = np.clip(Wm * 1.4, 0, 1) * a
        # label map dilated so the soft edge follows its window
        labd = cv2.dilate((lab * winmask).astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
        self.label = labd
        # "all lights off" plate: windows inpainted from the surrounding facade then darkened (unlit glass)
        u8 = (np.clip(sr, 0, 1) * 255 + 0.5).astype(np.uint8)
        im = cv2.inpaint(u8, cv2.dilate(winmask.astype(np.uint8), np.ones((5, 5), np.uint8)), 5, cv2.INPAINT_TELEA)
        dark_glass = srgb_to_lin(im.astype(f32) / 255) * np.array([0.30, 0.33, 0.40], f32)
        Yl = lum(P)[..., None]
        unlit_glow = Yl * 0.30 * np.array([0.85, 0.92, 1.10], f32)
        D = P * (1 - Wm[..., None]) + dark_glass * Wm[..., None]
        g3 = glow[..., None]
        D = D * (1 - g3) + np.minimum(D, unlit_glow) * g3
        # lamp heads: kill the bright cores outright
        heads = np.zeros((H, W), f32)
        for lx, ly in self.lamps:
            heads += np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * (7 * s) ** 2))
        heads = np.clip(heads * 1.5, 0, 1) * a
        D = D * (1 - heads[..., None]) + np.minimum(D, Yl * 0.15) * heads[..., None]
        self.D = D.astype(f32)
        self.Lw = (np.maximum(P - D, 0) * Wm[..., None] * (1 - g3)).astype(f32)
        self.Lg = (np.maximum(P - D, 0) * np.maximum(g3, heads[..., None])).astype(f32)
        self.Lg += (np.maximum(P - D, 0) * (1 - Wm[..., None]) * (1 - np.maximum(g3, heads[..., None]))).astype(f32) * 0  # rest: none
        # per-window switch-off time: grid outages sweep in block waves (far right -> near left), small jitter
        cx = cent[:, 0] / W; cy = (cent[:, 1] - fg.horizon) / H
        bx = np.floor(cent[:, 0] / (150 * s)); by = np.floor(cent[:, 1] / (110 * s))
        bkey = (bx * 37 + by * 101) % 7 / 7.0                                # block-coherent pseudo-random
        wave = np.clip(0.55 * (1 - cx) + 0.30 * np.clip(cy * 4, 0, 1) + 0.35 * bkey, 0, 1.2) / 1.2
        q = np.floor(wave * 4) / 4                                           # 4 waves
        self.t_off = (T_OFF0 + q * (T_OFF1 - T_OFF0 - 0.25) + rng.uniform(0, 0.22, n)).astype(f32)
        self.t_on = (T_RET0 + (1 - q) * 0.9 + rng.uniform(0, 0.35, n)).astype(f32)
        self.ph = rng.uniform(0, 100, n).astype(f32)
        # survivors: window components nearest to the given points keep a dim flickering light
        self.surv = np.zeros(n, bool)
        pts = [(x * s, y * s + oy) for x, y in SURVIVE_SRC]
        for px, py in pts:
            d = (cent[1:, 0] - px) ** 2 + (cent[1:, 1] - py) ** 2
            i = 1 + int(np.argmin(d))
            if d[i - 1] < (40 * s) ** 2: self.surv[i] = True
        self.surv[0] = False
        # lamp timing: each lamp dies with its block
        self.lamp_off, self.lamp_on = LAMP_OFF, LAMP_ON
        # night grade of the unlit city + a starlit rim on the edges facing the sky
        Yd = lum(D)[..., None]
        nd = (D * 0.22 + Yd * 0.78) * np.array([0.52, 0.72, 1.25], f32)
        er = cv2.erode(a, np.ones((1, 1), np.uint8))
        up = np.zeros_like(a); acc = np.zeros_like(a)
        for k in range(1, 9):                                               # how much sky is right above each pixel
            sh = np.zeros_like(a); sh[k:] = a[:-k]
            acc += (1 - sh) * math.exp(-k / 2.5)
        rim = np.clip(acc * a, 0, 1)
        rim = cv2.GaussianBlur(rim, (0, 0), 0.6)
        # distance-haze: far buildings (near the horizon line) pick up a touch of the sky colour
        depth = smooth(fg.horizon + 260 * s, fg.horizon - 120 * s, yy)
        self.night = nd.astype(f32); self.rim = rim.astype(f32); self.depth = depth.astype(f32)
        self.win_area = Wm

    def on_window(self, t):
        """per-component on level (0..1) incl. brown-out flicker during the quake and the return"""
        on = np.ones(self.n, f32)
        u = (t - self.t_off) / 0.12
        dying = np.clip(1 - u, 0, 1)
        if t > T_HIT - 0.1:                                                 # brown-out flicker while shaking
            fl = 0.75 + 0.25 * np.sin(t * 61 + self.ph) * np.sin(t * 23 + self.ph * 2.3)
            pre = (t < self.t_off).astype(f32)
            on = pre * fl + (1 - pre) * dying * 0.6
            # last-gasp flash right before death
            on += np.exp(-((t - self.t_off + 0.06) / 0.035) ** 2) * 0.6
        if t > T_RET0:
            back = np.clip((t - self.t_on) / 0.10, 0, 1)
            back *= 0.85 + 0.15 * (np.sin(t * 90 + self.ph) > -0.6)
            on = np.maximum(on, back)
        if T_OFF0 < t < T_RET0 + 2.0:
            fl = (0.20 + 0.06 * np.sin(t * 9.0 + self.ph) + 0.04 * np.sin(t * 23.0 + self.ph * 3)) * ramp(t, T_OFF1 + 1.2, T_OFF1 + 2.5)
            on = np.where(self.surv, np.maximum(on, fl), on)
        on[0] = 0
        return on

    def on_lamp(self, t):
        out = []
        for i, (a, b) in enumerate(zip(self.lamp_off, self.lamp_on)):
            if t < a - 0.35: v = 1.0 if t < T_HIT - 0.1 else 0.85 + 0.15 * math.sin(t * 70 + i)
            elif t < a: v = 0.5 + 0.5 * (math.sin(t * 120 + i * 3) > 0) * (0.6 + 0.4 * math.sin(t * 37))   # buzzing flicker
            else: v = 0.0
            if t > b:                                                        # sodium lamps warm up slowly (dim, then full)
                v = max(v, 0.15 + 0.85 * ease((t - b) / 1.6))
            out.append(v)
        return np.array(out + [0.0], f32)

    def render(self, t, glowlvl, nightlvl, sky_col_horizon):
        """glowlvl: 1 = light-polluted city ambient, 0 = starlight only. nightlvl: starlit fill level."""
        onw = self.on_window(t); onl = self.on_lamp(t)
        wmap = onw[self.label][..., None]
        lmap = onl[self.lamp_id][..., None]
        amb_before = self.D * np.array([0.62, 0.55, 0.50], f32) * 0.78           # under an orange sodium sky dome
        amb_after = self.night * nightlvl + self.rim[..., None] * np.array([0.004, 0.006, 0.011], f32) * nightlvl / 0.06
        g = glowlvl
        img = amb_before * g + amb_after * (1 - g)
        img += self.depth[..., None] * sky_col_horizon * 0.22                  # aerial perspective towards the horizon
        img += self.Lw * wmap * 1.25 + self.Lg * lmap * 1.15
        return img.astype(f32), onw, onl


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = Layout(vertical); W, H = self.L.W, self.L.H
        self.fg = Foreground(FG_PATH, self.L, hz_frac=0.60)
        self.hz = self.fg.horizon
        self.f = 1150.0 if vertical else 1000.0
        self.cam = SkyCam(W, H, self.hz, self.f)
        self.city = City(self.fg, self.L)
        self.stars = StarSky()
        self.caps = Captions(self.L, WORDS, emphasis={"1994", "SKY", "HIT", "DARK", "UP", "MILKY", "WAY", "NEVER", "80%", "YOU", "CLOUD"})
        # Milky Way placement: core low in the gap between the towers, band rising to the upper right
        if vertical:
            self.mw = dict(cx=2073, cy=704, rot=4.0); self.mw_core, self.mw_ang, self.mw_s = (430.0, 1330.0), 60.0, 1.0
        else:
            self.mw = dict(cx=2050, cy=1300, rot=-38.0); self.mw_core, self.mw_ang, self.mw_s = (760.0, 615.0), 40.0, 0.85
        self._prep_sky()

    def _prep_sky(self):
        """static parts of the sky (locked camera): Milky Way plate + faint stars, enhanced; light-pollution dome"""
        cam, W, H = self.cam, self.L.W, self.L.H
        el = cam.up(np.maximum(cam.el, 0))
        mw, self.mw_band = milky_way(W, H, self.mw_core, self.mw_ang, s=self.mw_s, seed=5, gain=3.2)
        ext = 1 - 0.80 * np.exp(-el / 0.06)
        self.mw_plate = (mw * ext[..., None]).astype(f32)
        # airglow: faint green 557.7 nm band ~10 deg up + red higher, with slow banded structure
        n = cv2.resize(fbm2((128, 256), 31, 2.6), (W, H), interpolation=cv2.INTER_CUBIC)
        band = np.exp(-((el - 0.17) / 0.10) ** 2) * (0.75 + 0.25 * n)
        self.airglow = (band[..., None] * np.array([0.0008, 0.0022, 0.0011], f32) + np.exp(-el / 0.35)[..., None] * np.array([0.0035, 0.0018, 0.0016], f32) * 0.6).astype(f32)
        self.night_bg = (np.exp(-el / 0.4)[..., None] * np.array([0.0010, 0.0016, 0.0032], f32) + np.array([0.0006, 0.0008, 0.0014], f32)).astype(f32)
        # light-polluted dome: sodium orange at the horizon -> murky brown-grey overhead, a little uneven
        n2 = cv2.resize(fbm2((64, 128), 33, 3.0), (W, H), interpolation=cv2.INTER_CUBIC)
        hz = np.exp(-el / 0.16); mid = np.exp(-el / 0.55)
        dome = hz[..., None] * np.array([0.30, 0.15, 0.055], f32) + mid[..., None] * np.array([0.042, 0.028, 0.020], f32) + np.array([0.011, 0.009, 0.009], f32)
        dome *= (1 + 0.06 * n2)[..., None]
        self.dome = dome.astype(f32)
        # residual glow from distant towns that kept power (a real blackout is never total)
        self.residual = (np.exp(-el / 0.06)[..., None] * np.array([0.020, 0.010, 0.004], f32)).astype(f32)
        self.sky_h_glow = np.array([0.30, 0.15, 0.06], f32)
        self.sky_h_night = np.array([0.006, 0.008, 0.012], f32)

    # ----------------------------------------------------------------------------------------------- levels
    def levels(self, t):
        g = 1 - ramp(t, T_DRAIN0, T_DRAIN1)                 # skyglow
        g = max(g, ramp(t, T_RET0 + 0.4, T_RET1))
        stars = ramp(t, T_STARS - 0.6, T_STARS + 1.0) * (1 - ramp(t, T_RET0 + 0.3, T_RET1 - 0.3) * 0.7)
        mw = ramp(t, T_MW0, T_MW1) * (1 - ramp(t, T_RET0 + 0.2, T_RET1 - 0.2))
        night = 0.026 * ramp(t, T_DRAIN0, T_DRAIN1 + 1.5) + 0.010
        return g, stars, mw, night

    def sky(self, t, g, st, mw):
        img = self.dome * g + self.residual * (1 - g) + self.night_bg * (1 - g)
        if mw > 0:
            img += (self.mw_plate * 1.0 + self.airglow) * mw * (1 - 0.92 * g)
        # bright stars, twinkling; under the dome only the brightest survive (they are drawn regardless, the dome hides them)
        stars = self.stars.render(self.cam, t, gain=1.0, twinkle=1.0, plate_gain=0.0, star_gain=1.0, **self.mw)
        sg = 0.35 + 0.65 * st
        img += stars * 0.55 * sg * (0.05 + 0.95 * (1 - g) ** 2)
        return img

    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        g, st, mw, night = self.levels(t)
        sky = self.sky(t, g, st, mw)
        hcol = self.sky_h_glow * g + self.sky_h_night * (1 - g)
        city, onw, onl = self.city.render(t, g, night, hcol)
        a = self.fg.a[..., None]
        img = sky * (1 - a) + city * a
        # earthquake jolt: the only camera motion in the film (tripod rattles), a few frames, decaying
        if T_SHAKE0 <= t < T_SHAKE1:
            u = (t - T_SHAKE0) / (T_SHAKE1 - T_SHAKE0)
            amp = (1 - u) ** 1.6 * min(1.0, u * 12) * (14 if L.vertical else 12)
            dx = amp * noise1(t, 91, 11.0, 2); dy = amp * 0.8 * noise1(t, 92, 13.0, 2)
            rot = amp * 0.03 * noise1(t, 93, 7.0, 2)
            M = cv2.getRotationMatrix2D((W / 2, H * 0.75), rot, 1.012)
            M[0, 2] += dx; M[1, 2] += dy
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # exposure: the camera opens up as the city dies (night adaptation), back down when the lights return
        ex = 1.0 + 1.6 * ramp(t, T_DRAIN0 + 0.3, T_DRAIN1 + 1.0) * (1 - ramp(t, T_RET0 + 0.3, T_RET1))
        img = bloom(img, 0.55 + 0.25 * g)
        out = tonemap(img, 1.05 * ex)
        out = self.grade(out, g)
        out = finish(out, t, grain=0.012 + 0.006 * (1 - g))
        self.overlay(out, t)
        return out

    def grade(self, out, g):
        """display-referred grade: sodium-orange before, cool blue night after"""
        warm = np.array([1.04, 0.98, 0.88], f32); cool = np.array([0.93, 0.98, 1.07], f32)
        out = out * (warm * g + cool * (1 - g))
        lift = np.array([0.006, 0.008, 0.016], f32) * (1 - g)
        return np.clip(out + lift * (1 - out), 0, 1)

    # ----------------------------------------------------------------------------------------------- text
    def overlay(self, out, t):
        L = self.L; W = L.W
        fs = int(L.hud_size * 0.42)
        top = L.safe_top + 50 if L.vertical else 70
        def lab(txt, y, a, col=(232, 236, 245), size=fs, wt="SemiBold", tr=0.16, x=None):
            if a > 0.01: hud_text(out, txt, W / 2 if x is None else x, y, size, wt, col, a, tr)
        q0, q1 = LN["quake"]["start"], LN["dark"]["end"]
        a = ramp(t, q0 + 0.1, q0 + 0.5) * (1 - ramp(t, q1, q1 + 0.4))
        lab("17 JAN 1994  ·  4:31 AM", top, a, (255, 205, 150), int(fs * 1.1))
        lab("NORTHRIDGE EARTHQUAKE  ·  M6.7", top + fs * 1.6, a * 0.9, (225, 230, 240), int(fs * 0.9))
        c0, c1 = LN["cloud"]["start"], LN["cloud"]["end"]
        a = ramp(t, c0 + 0.2, c0 + 0.6) * (1 - ramp(t, c1 + 0.1, c1 + 0.5))
        lab("AS RECOUNTED BY GRIFFITH OBSERVATORY", top, a * 0.9, (215, 225, 245), int(fs * 0.9))
        f0, f1 = LN["fact"]["start"], LN["end"]["start"]
        a = ramp(t, f0 + 0.2, f0 + 0.6) * (1 - ramp(t, f1 - 0.1, f1 + 0.3))
        lab("THE MILKY WAY IS HIDDEN FROM", top, a, (225, 232, 245), int(fs * 0.95))
        lab("NEARLY 80% OF NORTH AMERICANS", top + fs * 1.7, a, (255, 190, 110), int(fs * 1.15), "Bold")
        lab("MORE THAN 1/3 OF HUMANITY", top + fs * 3.5, a, (255, 190, 110), int(fs * 1.15), "Bold")
        lab("FALCHI ET AL., SCIENCE ADVANCES (2016)", top + fs * 5.3, a * 0.75, (190, 200, 220), int(fs * 0.72))
        self.caps.draw(out, t)


# ------------------------------------------------------------------------------------------------- run
def save(im, p):
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p)


def run(vertical, stills=None):
    sc = Scene(vertical); tag = "vert" if vertical else "wide"
    if stills:
        os.makedirs(os.path.join(SCR, "stills"), exist_ok=True)
        for t in stills:
            t0 = time.time(); save(sc.frame(t), os.path.join(SCR, "stills", f"{tag}_{t:05.2f}.png"))
            print(f"t={t:.2f} {time.time() - t0:.1f}s", flush=True)
        return
    n = int(round(DUR * FPS))
    enc = Encoder(os.path.join(SCR, f"video_{tag}.mp4"), sc.L.W, sc.L.H, FPS, crf=17)
    t0 = time.time()
    for i in range(n):
        enc.write(sc.frame(i / FPS))
        if i % 60 == 0: print(f"{tag} frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
    enc.close(); print("done", time.time() - t0, "DUR", DUR)


if __name__ == "__main__":
    vert = sys.argv[1] != "wide"
    st = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    run(vert, st)
