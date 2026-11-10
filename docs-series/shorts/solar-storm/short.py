"""IF THE 1859 SOLAR STORM HIT TODAY — vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the user's city plate (C_city.png) for the whole Short; everything happens in the
sky and in the city lights.
  hook    dusk city; a white flare flashes from the Sun just below the horizon glow, chromatic beams fan out
  1859    second flare pulse (Carrington), "17.6 HOURS" counter, the sky darkens, a chromatic shock front sweeps the sky
  arrival the sky ERUPTS: folded green/crimson curtains with magenta fringes race overhead into a corona (aurora.py);
          the city is tinted green and red by the aurora light
  grid    blue-green transformer flashes along the skyline, windows die in block waves, street lamps pop (City is copied
          from ../milky-way-blackout/short.py); the auroras keep blazing over a dark city; phone / GPS readouts glitch out
  cost    trillions readout, the 2012 near miss
  end     the aurora fades, the lights flicker back on, the dusk sky returns (last frame ~ first frame: loops)
Built on docs-series/shorts/lib (read-only; nothing in lib/ is modified).
Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE, os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image, ImageDraw
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, lin_to_srgb, srgb_to_lin, fbm2
from lib.foreground import Foreground
from lib.sky import SkyCam, StarSky
from lib.text import Captions, hud_text, font
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from aurora import Aurora

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S6-solar-storm"
FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/C_city.png"
# street-lamp heads in SOURCE px of C_city.png (941x1672) (same as S2)
LAMPS_SRC = [(575, 1496), (703, 1449), (819, 1456), (470, 1386), (237, 1303)]
# a few lights that survive the blackout (battery / emergency lights), SOURCE px (from S2)
SURVIVE_SRC = [(547, 1592), (33, 1418), (264, 1404), (690, 1338)]
FPS = 30
LEAD, TAIL = 0.25, 2.0

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t0"]

T_FIRE = wt("hook", "FIRED") - 0.05            # the flare flashes from below the horizon
T_FLARE2 = wt("flare", "FLARE") - 0.05         # Carrington's white flare (second pulse)
T_CNT0, T_CNT1 = wt("flare", "17.6") - 0.1, wt("flare", "EARTH") + 0.2   # 17.6 h counter
T_HIT = wt("flare", "HIT")                     # shock front sweeps the sky
T_ERUPT = wt("erupt", "ERUPTED")               # aurora explodes overhead
T_GRID = wt("grid", "TODAY")
T_TRANS = wt("grid", "TRANSFORMERS")
T_OFF0 = T_TRANS + 0.25                        # first wave of windows dies
T_OFF1 = wt("grid", "DARK") + 0.25             # last wave
T_PH, T_GPS = wt("nosig", "PHONES"), wt("nosig", "GPS")
T_COST = LN["cost"]["start"]; T_2012 = wt("cost", "2012")
T_RET0 = wt("end", "MATTER")                   # lights come back
T_RET1 = DUR - 0.45
T_FADE0, T_FADE1 = LN["end"]["start"] - 0.2, DUR - 0.5     # aurora fades
LAMP_OFF = [T_OFF0 + 0.15 + k for k in (0.55, 0.30, 0.95, 0.75, 1.15)]
FLASH_T = [T_TRANS + 0.02, T_TRANS + 0.45, T_TRANS + 0.85, T_TRANS + 1.3, T_TRANS + 1.75]
FLASH_X = [0.30, 0.86, 0.55, 0.12, 0.70]
LAMP_ON = [T_RET0 + 0.2 + k for k in (0.5, 0.2, 0.7, 0.9, 1.1)]
SURGES = [T_ERUPT + 0.05, wt("aurora", "SPARKED"), wt("cost", "TRILLIONS"), wt("cost", "MISSED")]


# ------------------------------------------------------------------------------------------------- city lights
class City:
    """Copied from ../milky-way-blackout/short.py (S2), timings adapted.
    Light decomposition of the dusk photo: photo = D (all lights off) + window light + lamp light.
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
        n, lab, stats, cent = cv2.connectedComponentsWithStats(win, 8)
        near = gsum[np.clip(cent[:, 1].astype(int), 0, H - 1), np.clip(cent[:, 0].astype(int), 0, W - 1)]
        is_lamp = (near > 0.35) & (stats[:, cv2.CC_STAT_AREA] < 4000)
        is_lamp[0] = False
        winmask = (lab > 0) & ~is_lamp[lab]
        self.n = n
        Wm = cv2.GaussianBlur(cv2.dilate(winmask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(f32), (0, 0), 0.7)
        Wm = np.clip(Wm * 1.4, 0, 1) * a
        self.label = cv2.dilate((lab * winmask).astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32)
        u8 = (np.clip(sr, 0, 1) * 255 + 0.5).astype(np.uint8)
        im = cv2.inpaint(u8, cv2.dilate(winmask.astype(np.uint8), np.ones((5, 5), np.uint8)), 5, cv2.INPAINT_TELEA)
        dark_glass = srgb_to_lin(im.astype(f32) / 255) * np.array([0.30, 0.33, 0.40], f32)
        Yl = lum(P)[..., None]
        unlit_glow = Yl * 0.30 * np.array([0.85, 0.92, 1.10], f32)
        D = P * (1 - Wm[..., None]) + dark_glass * Wm[..., None]
        g3 = glow[..., None]
        D = D * (1 - g3) + np.minimum(D, unlit_glow) * g3
        heads = np.zeros((H, W), f32)
        for lx, ly in self.lamps:
            heads += np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * (7 * s) ** 2))
        heads = np.clip(heads * 1.5, 0, 1) * a
        D = D * (1 - heads[..., None]) + np.minimum(D, Yl * 0.15) * heads[..., None]
        self.D = D.astype(f32)
        self.Lw = (np.maximum(P - D, 0) * Wm[..., None] * (1 - g3)).astype(f32)
        self.Lg = (np.maximum(P - D, 0) * np.maximum(g3, heads[..., None])).astype(f32)
        # per-window switch-off time: grid outages sweep in block waves (far right -> near left), small jitter
        cx = cent[:, 0] / W; cy = (cent[:, 1] - fg.horizon) / H
        bx = np.floor(cent[:, 0] / (150 * s)); by = np.floor(cent[:, 1] / (110 * s))
        bkey = (bx * 37 + by * 101) % 7 / 7.0
        wave = np.clip(0.55 * (1 - cx) + 0.30 * np.clip(cy * 4, 0, 1) + 0.35 * bkey, 0, 1.2) / 1.2
        q = np.floor(wave * 4) / 4
        self.t_off = (T_OFF0 + q * (T_OFF1 - T_OFF0 - 0.25) + rng.uniform(0, 0.22, n)).astype(f32)
        self.t_on = (T_RET0 + 0.1 + (1 - q) * 0.9 + rng.uniform(0, 0.35, n)).astype(f32)
        self.ph = rng.uniform(0, 100, n).astype(f32)
        self.lamp_off, self.lamp_on = LAMP_OFF, LAMP_ON
        self.surv = np.zeros(n, bool)
        for px, py in [(x * s, y * s + oy) for x, y in SURVIVE_SRC]:
            d = (cent[1:, 0] - px) ** 2 + (cent[1:, 1] - py) ** 2
            i = 1 + int(np.argmin(d))
            if d[i - 1] < (40 * s) ** 2: self.surv[i] = True
        # night grade of the unlit city + a sky-facing rim (edges with open sky right above them)
        Yd = lum(D)[..., None]
        self.night = ((D * 0.30 + Yd * 0.70) * np.array([0.55, 0.72, 1.20], f32)).astype(f32)
        acc = np.zeros_like(a)
        for k in range(1, 9):
            sh = np.zeros_like(a); sh[k:] = a[:-k]
            acc += (1 - sh) * math.exp(-k / 2.5)
        self.rim = cv2.GaussianBlur(np.clip(acc * a, 0, 1), (0, 0), 0.6).astype(f32)
        # "up-facing" proxy for the aurora light: brighter towards the skyline, roofs and the near rooftop
        top = smooth(H, fg.horizon - 250 * s, yy)
        self.upf = np.clip(0.35 + 0.65 * top + 1.5 * self.rim, 0, 2.5).astype(f32)
        self.depth = smooth(fg.horizon + 260 * s, fg.horizon - 120 * s, yy).astype(f32)

    def on_window(self, t):
        on = np.ones(self.n, f32)
        if t > T_GRID + 0.6:                                               # brown-out flicker as the grid strains
            k = ramp(t, T_GRID + 0.6, T_TRANS)
            fl = 1 - k * (0.25 - 0.25 * np.sin(t * 61 + self.ph) * np.sin(t * 23 + self.ph * 2.3))
            pre = (t < self.t_off).astype(f32)
            u = (t - self.t_off) / 0.12
            on = pre * fl + (1 - pre) * np.clip(1 - u, 0, 1) * 0.6
            on += np.exp(-((t - self.t_off + 0.06) / 0.035) ** 2) * 1.6     # last-gasp flash
        if T_OFF0 < t < T_RET0 + 2.0:                                      # dim flickering emergency lights
            fl = (0.18 + 0.06 * np.sin(t * 9.0 + self.ph) + 0.05 * np.sin(t * 23.0 + self.ph * 3)) * ramp(t, T_OFF1 + 0.6, T_OFF1 + 1.6)
            on = np.where(self.surv, np.maximum(on, fl), on)
        if t > T_RET0:
            back = np.clip((t - self.t_on) / 0.10, 0, 1)
            back *= 0.80 + 0.20 * (np.sin(t * 90 + self.ph) > -0.6)
            on = np.maximum(on, back)
        on[0] = 0
        return on

    def on_lamp(self, t):
        out = []
        for i, (a, b) in enumerate(zip(self.lamp_off, self.lamp_on)):
            if t < a - 0.35: v = 1.0 if t < T_TRANS else 0.85 + 0.15 * math.sin(t * 70 + i)
            elif t < a: v = 0.5 + 0.5 * (math.sin(t * 120 + i * 3) > 0) * (0.6 + 0.4 * math.sin(t * 37))
            else: v = 0.0
            if t > a and t < a + 0.08: v = 3.0                               # pop
            if t > b: v = max(v, 0.15 + 0.85 * ease((t - b) / 1.2))
            out.append(v)
        return np.array(out + [0.0], f32)

    def ripple(self, t):
        """moving brightness bands from the curtains overhead"""
        x = self.fg.L.W
        if not hasattr(self, "_xx"): self._xx = np.arange(x, dtype=f32)[None, :] / x
        return (0.75 + 0.25 * np.sin(self._xx * 9.0 + t * 1.7) * np.sin(self._xx * 3.1 - t * 0.9)).astype(f32)

    def render(self, t, nightlvl, aur_col, hcol):
        """nightlvl 0 = dusk photo, 1 = deep night. aur_col: mean aurora radiance (tints the city)."""
        onw = self.on_window(t); onl = self.on_lamp(t)
        wmap = onw[self.label][..., None]
        lmap = onl[self.lamp_id][..., None]
        amb = self.D * (1 - nightlvl) + self.night * 0.075 * nightlvl
        img = amb + self.depth[..., None] * hcol * 0.25
        # aurora light: albedo (lights-off plate, normalised) x aurora colour, stronger on sky-facing surfaces
        alb = self.D / (lum(self.D)[..., None] * 3 + 0.02)
        img += alb * aur_col * self.upf[..., None] * self.ripple(t)[..., None] * 1.5
        img += self.Lw * wmap * 1.25 + self.Lg * lmap * 1.15
        return img.astype(f32)


def palette(x):
    x = x[..., None] if np.ndim(x) else x
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


# ------------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = Layout(vertical); W, H = self.L.W, self.L.H
        self.fg = Foreground(FG_PATH, self.L, hz_frac=0.70)
        self.hz = self.fg.horizon
        self.f = 1150.0 if vertical else 1000.0
        self.cam = SkyCam(W, H, self.hz, self.f)
        self.city = City(self.fg, self.L)
        self.stars = StarSky()
        V = (0.53 * W, 0.20 * H) if vertical else (0.56 * W, 0.10 * H)
        self.aur = Aurora(W, H, self.hz, self.f, V)
        self.caps = Captions(self.L, WORDS, emphasis={"1859", "SUN", "STORM", "TODAY", "FLARE", "17.6", "EARTH", "ERUPTED",
                                                       "CARIBBEAN", "SPARKED", "TRANSFORMERS", "DARK", "MONTHS", "GPS", "PHONES",
                                                       "TRILLIONS", "2012", "NINE", "WHEN"})
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        self.xx, self.yy = xx, yy
        el = np.clip((self.hz - yy) / self.hz, 0, 1)
        self.el = el
        # the Sun sits just below the horizon, behind the skyline left of the tall tower
        self.P = (0.36 * W, self.hz + 0.03 * H)
        sx = np.exp(-((xx - self.P[0]) / (0.42 * W)) ** 2)
        # dusk sky (just after sunset): deep blue zenith, violet/pink band, orange glow at the horizon near the Sun
        self.dusk = (np.array([0.020, 0.040, 0.140], f32) * (1 - el[..., None] * 0.35)
                     + np.exp(-el / 0.22)[..., None] * np.array([0.10, 0.045, 0.11], f32)
                     + (np.exp(-el / 0.07) * (0.35 + 0.9 * sx))[..., None] * np.array([0.80, 0.26, 0.05], f32)).astype(f32)
        # night: deep blue, readable, brighter and a touch teal near the horizon (never black)
        self.nightsky = (np.exp(-el / 0.45)[..., None] * np.array([0.006, 0.012, 0.030], f32)
                         + np.array([0.004, 0.007, 0.022], f32)).astype(f32)
        self.h_dusk = np.array([0.30, 0.13, 0.06], f32); self.h_night = np.array([0.010, 0.016, 0.034], f32)
        # flare beams (half res)
        hh, hw = H // 2, W // 2
        y2, x2 = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.bdx, self.bdy = x2 - self.P[0], y2 - self.P[1]
        self.bd = np.sqrt(self.bdx ** 2 + self.bdy ** 2) + 1e-3; self.bphi = np.arctan2(self.bdy, self.bdx)
        r = np.random.default_rng(8)
        self.beamdef = [dict(a=-np.pi / 2 + (i - 3) * 0.36 + r.uniform(-0.1, 0.1), w=r.uniform(0.07, 0.13), I=r.uniform(0.8, 1.2),
                           hue=r.uniform(0, 1), ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(7)]
        sk = self.fg.skyline
        def hx(fx): x = int(fx * W); return (float(x), float(min(sk[max(0, x - 30):x + 30].min(), self.hz) + 4))
        self.flashes = [(tf, hx(fx), k) for tf, fx, k in zip(FLASH_T, FLASH_X, (1.0, 0.75, 0.95, 0.7, 0.85))]
        self.dist = np.sqrt((xx - self.P[0]) ** 2 + (yy - self.P[1]) ** 2)

    # ----------------------------------------------------------------------------------------------- levels
    def levels(self, t):
        """night (sky/city darkening), aurora level, oval progress (0 = on the horizon, 1 = overhead)"""
        night = ramp(t, T_FLARE2 - 0.5, T_HIT + 0.5) * (1 - ramp(t, T_RET0 - 0.3, DUR - 0.25))
        if t < T_ERUPT:
            lvl = 0.35 * ramp(t, T_CNT0 + 0.4, T_HIT) + 0.65 * ramp(t, T_ERUPT - 0.6, T_ERUPT + 0.1)
            prog = 0.30 * ramp(t, T_CNT0 + 0.4, T_HIT) + 0.70 * ramp(t, T_HIT, T_ERUPT + 0.25)
        else:
            lvl = 1.0; prog = 0.30 + 0.70 * ramp(t, T_HIT, T_ERUPT + 0.25)
        fade = 1 - ramp(t, T_FADE0, T_FADE1)
        lvl *= fade; prog = prog * (0.55 + 0.45 * fade)
        pulse = 1 + 0.22 * noise1(t, 3, 1.7, 3) + 0.08 * noise1(t, 4, 8.0, 1)
        pulse += sum(0.9 * math.exp(-((t - ts) / 0.18) ** 2) * (1 if t > ts else 1.0) for ts in SURGES)
        return night, lvl * pulse, prog

    def beam_layer(self, t, k):
        acc = np.zeros(self.bd.shape + (3,), f32)
        rad = (1 - np.exp(-self.bd / 40)) * (np.exp(-self.bd / 1300) * 0.9 + 0.1)
        for b in self.beamdef:
            a = b["a"] + 0.05 * math.sin(t * 0.7 * b["sp"] + b["ph"])
            dp = (self.bphi - a + np.pi) % (2 * np.pi) - np.pi
            w = b["w"] * (1 + 0.3 * math.sin(t * 1.1 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / w) ** 2 * 1.6)
            c = palette((b["hue"] + dp / w * 0.30) % 1.0) * 0.6 + np.array([1.0, 0.85, 0.6], f32) * 0.4
            acc += c * (g * b["I"])[..., None]
        out = acc * rad[..., None] * 0.5 * k
        return cv2.resize(out, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    def flare(self, t):
        """(beam level, core flash) for the hook flare and Carrington's flare"""
        b = 0.0; c = 0.0
        for t0, amp, dur in ((T_FIRE, 1.0, 3.2), (T_FLARE2, 0.75, 2.0)):
            u = t - t0
            if -0.1 < u < dur + 1.5:
                b = max(b, amp * min(1.0, max(u, 0) / 0.12) * math.exp(-max(u, 0) / dur))
                c += amp * (math.exp(-max(u, 0) / 0.25) * (u > 0) * 6 + math.exp(-max(u, 0) / 1.2) * (u > 0))
        return b, c

    def sky(self, t, night, lvl, prog):
        W, H = self.L.W, self.L.H
        img = self.dusk * (1 - night) + self.nightsky * night
        st = self.stars.render(self.cam, t, gain=1.0, twinkle=1.4, plate_gain=0.10, star_gain=1.0, cx=2073, cy=704, rot=4.0)
        img = img + st * (0.15 + 0.85 * night) * (1 - 0.5 * min(lvl, 1.0))
        b, c = self.flare(t)
        if b > 0.01: img = img + self.beam_layer(t, b)
        if c > 0.01:
            P = self.P
            splat(img, P[0], P[1], 2.2 * H, lambda d, dx, dy: ((np.exp(-d / 60) * 30 + np.exp(-d / 260) * 1.5 + np.exp(-d / 900) * 0.12) * c)[..., None]
                  * np.array([1.0, 0.92, 0.82], f32))
        # shock front: chromatic ring racing across the sky from the Sun's position
        u = t - T_HIT
        if -0.05 < u < 1.6:
            R = 2600 * max(u, 0) ** 0.7 / 1.6 ** 0.7 * 1.2; wdt = 30 + 90 * max(u, 0)
            for ch, off in ((0, 18), (1, 0), (2, -18)):
                img[..., ch] += np.exp(-((self.dist - R - off) / wdt) ** 2) * 1.2 * math.exp(-max(u, 0) / 0.8)
        aur, mean = self.aur.render(t, lvl, prog, storm=1.0, crown=1.0)
        img = img + aur
        if T_ERUPT - 0.05 < t < T_ERUPT + 1.0:                              # eruption flash
            img = img + 1.0 * math.exp(-(t - T_ERUPT + 0.05) / 0.16) * np.array([0.6, 1.0, 0.8], f32)
        return img, mean

    def flash(self, t):
        out = []
        for (tf, (x, y), k) in self.flashes:
            d = t - tf
            if -0.05 < d < 0.6:
                v = sum(a * math.exp(-((d - o) / w) ** 2) for o, a, w in ((0.0, 1.0, 0.045), (0.10, 0.6, 0.03), (0.22, 0.85, 0.05), (0.34, 0.3, 0.03)))
                out.append((x, y, v * k))
        return out

    def frame(self, t):
        L = self.L; W, H = L.W, L.H
        night, lvl, prog = self.levels(t)
        sky, amean = self.sky(t, night, lvl, prog)
        hcol = self.h_dusk * (1 - night) + self.h_night * night
        city = self.city.render(t, night, amean, hcol)
        fl = self.flash(t)
        if fl:
            col = np.array([0.35, 1.0, 0.85], f32)
            for (x, y, v) in fl:
                splat(sky, x, y, W * 1.4, lambda d, dx, dy, v=v: ((np.exp(-d / 18) * 60 + np.exp(-d / 130) * 3.0 + np.exp(-d / 600) * 0.35) * v)[..., None] * col)
            tot = sum(v for _, _, v in fl)
            city = city + self.city.D * col * 0.9 * tot
        b, c = self.flare(t)
        if c > 0.01:                                                       # flare light washes over the city
            city = city + self.city.D * np.array([1.0, 0.9, 0.8], f32) * 0.35 * c * self.city.upf[..., None]
        a = self.fg.a[..., None]
        img = sky * (1 - a) + city * a
        ex = 1.0 + 0.5 * night
        if T_TRANS < t < T_OFF1 + 0.2:                                       # brown-out flicker
            k = 0.5 + 0.5 * noise1(t, 77, 9.0, 2)
            ex *= 1.0 - 0.35 * (k > 0.72) * (noise1(t, 78, 23.0, 1) > 0)
        img = bloom(img, 0.7 + 0.5 * min(lvl, 1.2))
        out = tonemap(img, ex)
        out = self.grade(out, night)
        out = finish(out, t, grain=0.010, vignette=0.16)
        self.overlay(out, t)
        return out

    def grade(self, out, night):
        y = out.mean(2, keepdims=True)
        out = y + (out - y) * (1.12 + 0.25 * night)
        lift = np.array([0.006, 0.010, 0.022], f32) * night
        return np.clip(out + lift * (1 - out), 0, 1)

    # ----------------------------------------------------------------------------------------------- icons
    def icon(self, kind, size):
        """white line icon (phone with signal bars / GPS pin) with a red slash -> RGBA uint8"""
        S = size; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        lw = max(4, S // 18); wcol = (245, 248, 255, 255)
        if kind == "phone":
            d.rounded_rectangle((S * 0.30, S * 0.12, S * 0.70, S * 0.88), radius=S * 0.07, outline=wcol, width=lw)
            d.line((S * 0.44, S * 0.80, S * 0.56, S * 0.80), fill=wcol, width=lw)
            for i in range(4):
                x = S * (0.38 + i * 0.07); d.rectangle((x, S * (0.55 - i * 0.08), x + S * 0.04, S * 0.62), fill=(150, 160, 175, 255))
        else:
            cx, cy, r = S * 0.5, S * 0.40, S * 0.22
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=wcol, width=lw)
            d.polygon([(cx - r * 0.85, cy + r * 0.55), (cx + r * 0.85, cy + r * 0.55), (cx, S * 0.88)], outline=wcol, fill=None, width=lw)
            d.line((cx - r * 0.85, cy + r * 0.55, cx, S * 0.88), fill=wcol, width=lw)
            d.line((cx + r * 0.85, cy + r * 0.55, cx, S * 0.88), fill=wcol, width=lw)
            d.ellipse((cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35), fill=wcol)
        d.line((S * 0.15, S * 0.85, S * 0.85, S * 0.15), fill=(255, 60, 60, 255), width=int(lw * 1.4))
        return np.asarray(im)

    def glitch_icon(self, out, kind, cx, cy, size, t, t0, alpha):
        """composite an icon with RGB split, slice jitter and flicker (digital failure look)"""
        if alpha <= 0.01: return
        rgba = self.icon(kind, size).astype(f32) / 255
        age = t - t0
        g = 1.0 if age < 0.5 else 0.35
        rng = np.random.default_rng(int(t * 30) * 7 + (1 if kind == "phone" else 2))
        lay = rgba.copy()
        for _ in range(int(6 * g) + 1):                                    # horizontal slice offsets
            y0 = rng.integers(0, size - 8); h = rng.integers(3, max(4, size // 6)); dx = int(rng.normal(0, 14 * g))
            lay[y0:y0 + h] = np.roll(lay[y0:y0 + h], dx, axis=1)
        sh = int(6 + 10 * g * abs(math.sin(t * 37)))
        H, W = out.shape[:2]
        fl = alpha * (0.55 + 0.45 * (rng.uniform() > 0.18 * g))
        for ch, ox, tint in ((0, -sh, (1.0, 0.25, 0.3)), (2, sh, (0.3, 0.6, 1.0)), (1, 0, (1, 1, 1))):
            x0, y0 = int(cx - size / 2 + ox), int(cy - size / 2)
            xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + size), min(H, y0 + size)
            if xb <= xa or yb <= ya: continue
            src = lay[ya - y0:yb - y0, xa - x0:xb - x0]
            al = src[..., 3:] * fl * (0.55 if ch != 1 else 1.0)
            out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - al) + src[..., :3] * np.array(tint, f32) * al

    # ----------------------------------------------------------------------------------------------- text
    def overlay(self, out, t):
        L = self.L; W = L.W; V = L.vertical
        fs = int(L.hud_size * 0.42)
        top = L.safe_top + 40 if V else 60
        ly, by = (1145, 1240) if V else (712, 800)                        # label row, big readout row
        big = int(L.hud_size * (1.25 if V else 1.15))
        def lab(txt, y, a, col=(232, 236, 245), size=fs, wt="SemiBold", tr=0.16, x=None, disp=False):
            if a > 0.01: hud_text(out, txt, W / 2 if x is None else x, y, size, wt, col, a, tr, display=disp)
        def win(a0, a1, k=0.25): return ramp(t, a0, a0 + k) * (1 - ramp(t, a1 - k, a1))
        h0, h1 = LN["hook"]["start"], LN["flare"]["start"] + 0.2
        lab("THE CARRINGTON EVENT", top, win(h0 + 0.2, h1), (255, 214, 160), int(fs * 1.1), "Bold")
        lab("1–2 SEPTEMBER 1859", top + fs * 1.6, win(h0 + 0.3, h1) * 0.9, (225, 230, 240), int(fs * 0.9))
        f0 = LN["flare"]["start"]
        a = win(f0, T_CNT0 + 0.1)
        lab("1 SEP 1859  ·  WHITE-LIGHT SOLAR FLARE", ly, a, (255, 236, 200), fs, "Bold")
        lab("SEEN BY RICHARD CARRINGTON", ly + fs * 1.5, a * 0.85, (220, 228, 240), int(fs * 0.85))
        a = win(T_CNT0, LN["erupt"]["start"] + 0.3)
        if a > 0.01:
            hrs = 17.6 * ease((t - T_CNT0) / (T_CNT1 - T_CNT0)) if t < T_CNT1 else 17.6
            lab("SUN  →  EARTH", ly, a, (230, 238, 250), fs, "Bold")
            lab(f"{hrs:4.1f} HOURS", by, a, (255, 255, 255) if t < T_CNT1 else (255, 170, 70), big, "Black", 0.03, disp=True)
        a0 = LN["aurora"]["start"]
        for txt, s0, s1, col in (("AURORAS IN THE CARIBBEAN", a0, wt("aurora", "PEOPLE") - 0.05, (120, 255, 170)),
                                 ("NEWSPAPERS READ BY AURORA LIGHT", wt("aurora", "PEOPLE"), wt("aurora", "TELEGRAPHS") - 0.05, (255, 140, 170)),
                                 ("TELEGRAPHS SPARKED", wt("aurora", "TELEGRAPHS"), LN["aurora"]["end"] + 0.3, (170, 230, 255))):
            lab(txt, by, win(s0, s1, 0.18), col, int(big * (0.62 if V else 0.6) * min(1.0, 24 / len(txt))), "Black", 0.05, disp=True)
        lab("1859", ly, win(a0, LN["aurora"]["end"] + 0.3) * 0.9, (230, 236, 250), fs, "Bold")
        g0 = LN["grid"]["start"]
        lab("TODAY", ly, win(g0, LN["nosig"]["start"]), (255, 214, 160), fs, "Bold")
        lab("POWER GRID", by - big * 0.45, win(T_TRANS, LN["nosig"]["start"]), (235, 240, 250), int(fs * 0.9), "Bold")
        lab("FAILING", by + big * 0.25, win(T_TRANS, LN["nosig"]["start"]) * (0.6 + 0.4 * (math.sin(t * 25) > -0.3)), (255, 90, 80), int(big * 0.7), "Black", 0.08, disp=True)
        # phone / GPS readouts glitching out
        n0, n1 = T_PH - 0.1, T_COST + 0.25
        isz = 230 if V else 170
        ix = (W * 0.30, W * 0.70) if V else (W * 0.38, W * 0.62)
        self.glitch_icon(out, "phone", ix[0], by - 20, isz, t, T_PH, win(n0, n1, 0.1))
        self.glitch_icon(out, "gps", ix[1], by - 20, isz, t, T_GPS, win(T_GPS - 0.1, n1, 0.1))
        if t > n0:
            gl = 0.6 + 0.4 * (math.sin(t * 43) > -0.2)
            hud_text(out, "NO SIGNAL", ix[0], by + isz * 0.62, int(fs * 1.5), "Black", (255, 80, 80), win(n0 + 0.15, n1, 0.1) * gl, 0.12, display=True)
            hud_text(out, "GPS LOST", ix[1], by + isz * 0.62, int(fs * 1.5), "Black", (255, 80, 80), win(T_GPS + 0.05, n1, 0.1) * gl, 0.12, display=True)
        c0 = LN["cost"]["start"]
        a = win(c0, T_2012 - 0.1)
        lab("CARRINGTON-CLASS STORM, US COST", ly, a, (230, 236, 250), fs, "Bold")
        lab("$0.6–2.6 TRILLION", by, a, (255, 205, 90), int(big * 0.9), "Black", 0.03, disp=True)
        lab("LLOYD'S ESTIMATE (2013)", by + big * 0.75, a * 0.85, (210, 220, 235), int(fs * 0.8))
        a = win(T_2012 - 0.1, LN["cost"]["end"] + 0.35)
        lab("23 JULY 2012", ly, a, (230, 236, 250), fs, "Bold")
        lab("MISSED BY ~9 DAYS", by, a, (255, 120, 90), int(big * 0.8), "Black", 0.03, disp=True)
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
