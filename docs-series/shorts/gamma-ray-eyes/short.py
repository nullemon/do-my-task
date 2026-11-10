"""IF YOUR EYES SAW GAMMA RAYS, THE MOON WOULD OUTSHINE THE SUN — vertical Short + 16:9 recomposition.
LOCKED CAMERA: one tripod frame of the park plate (A2_park.png) for the whole Short. The sky switches "eyes":
visible -> infrared -> radio -> microwave -> gamma -> visible (loops). Each switch is a colour wipe + whoosh.
Real all-sky data (skymaps.py / prep_maps.py) projected for a real place and time (ephem.py):
  infrared = Planck 857 GHz dust, radio = Haslam 408 MHz, microwave = Planck 100 GHz (CMB + Galaxy),
  gamma = Fermi-LAT 3FHL photons + 4FGL-DR4 blazars.
Built on docs-series/shorts/lib (read-only).
Usage (one heavy process at a time, under nice):
  /home/user/ttsenv/bin/python short.py vert|wide              full render -> SCR/video_<tag>.mp4
  /home/user/ttsenv/bin/python short.py vert|wide 1.0,9.5      stills -> SCR/stills/<tag>_<t>.png
"""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "audio")]
import lib.core  # noqa: F401  (pylib path for cv2 / PIL)
import numpy as np, cv2
from PIL import Image
from lib.core import f32, Layout, ramp, smooth, ease, noise1, splat, lum, lin_to_srgb, fbm2, kf
from lib.foreground import Foreground
from lib.sky import SkyCam, day_sky, sun_disc, lens_flare
from lib.text import Captions, hud_text, word_layer, composite
from lib.post import bloom, tonemap, finish, Encoder
from lib.audio import place
from skymaps import Maps, SkyGeo, PAL, apply_lut, SCR

FG_PATH = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/A2_park.png"
# SOURCE px of A2_park.png (941x1672), found on 3x crops: street-lamp heads + pole bases, house windows, house box
LAMPS_SRC = [(193, 1198, 1325), (666, 1207, 1322), (816, 1113, 1323)]
WINDOWS_SRC = [(683, 1277), (718, 1275), (778, 1277)]
HOUSE_SRC = (645, 1222, 812, 1300)
FPS = 30
LEAD, TAIL = 0.25, 1.30

PL = place(os.path.join(SCR, "vo", "words.json"), LEAD)
WORDS = [w for l in PL for w in l["words"]]
DUR = round(PL[-1]["end"] + TAIL, 2)
LN = {l["key"]: l for l in PL}
def wt(key, cap, n=0, end=False):
    ws = [w for w in LN[key]["words"] if w["cap"] == cap]; return ws[n]["t1" if end else "t0"]

# ---------------------------------------------------------------------------------------------- timeline
SW = {"ir": LN["ir"]["start"] - 0.14, "radio": LN["radio"]["start"] - 0.14, "micro": LN["micro"]["start"] - 0.14,
      "gamma": LN["gamma"]["start"] - 0.14, "vis2": LN["end"]["start"] - 0.20}
SEQ = [("vis", 0.0), ("ir", SW["ir"]), ("radio", SW["radio"]), ("micro", SW["micro"]), ("gamma", SW["gamma"]), ("vis", SW["vis2"])]
WIPE = 0.55
WIPE_END = 0.34
T_QUIET0, T_QUIET1 = wt("gamma", "SUN"), wt("gamma", "VANISHES", end=True)
T_CR0, T_HIT = wt("gamma", "COSMIC"), wt("gamma", "MOON")
T_BLAZE = wt("gamma", "BLAZES")
T_GRB = wt("fermi", "TELESCOPE") + 0.05
T_FACT0, T_FACT1 = LN["fermi"]["start"] + 0.1, LN["fermi"]["end"] + 0.45

MODE_COL = {"vis": (255, 246, 225), "ir": (255, 96, 170), "radio": (110, 232, 255), "micro": (255, 196, 96), "gamma": (205, 130, 255)}
LABEL = {"vis": ("VISIBLE LIGHT", "HUMAN EYES"), "ir": ("INFRARED EYES", "PLANCK · 350 µm DUST GLOW"),
         "radio": ("RADIO EYES", "408 MHz ALL-SKY SURVEY"), "micro": ("MICROWAVE EYES", "PLANCK · COSMIC MICROWAVE BACKGROUND"),
         "gamma": ("GAMMA-RAY EYES", "FERMI LAT ALL-SKY")}
EXPO = {"vis": 1.0, "ir": 1.0, "radio": 1.05, "micro": 1.0, "gamma": 0.95}
SAT = {"vis": 1.12, "ir": 1.25, "radio": 1.3, "micro": 1.25, "gamma": 1.3}

# famous radio sources (galactic l, b, relative brightness) for the "radio galaxies and quasars" sparkle
RADIO_SRC = [("CAS A", 111.74, -2.13, 1.0), ("CYGNUS A", 76.19, 5.76, 1.0), ("CRAB", 184.56, -5.78, 0.7), ("VIRGO A", 283.78, 74.49, 0.6),
             ("CENTAURUS A", 309.52, 19.42, 0.8), ("3C 273", 289.95, 64.36, 0.5), ("FORNAX A", 240.16, -56.69, 0.5),
             ("PICTOR A", 251.60, -34.64, 0.5), ("HYDRA A", 242.93, 25.09, 0.45), ("HERCULES A", 23.0, 29.2, 0.45), ("SGR A", 359.94, -0.05, 0.9)]


def mode_at(t):
    """-> (current mode, previous mode or None, wipe progress 0..1)"""
    cur, prev, p = "vis", None, 1.0
    for i, (m, ts) in enumerate(SEQ):
        if t >= ts:
            cur = m; prev = SEQ[i - 1][0] if i > 0 else None
            dur = WIPE_END if i == len(SEQ) - 1 else WIPE
            p = (t - ts) / dur if i > 0 else 1.0
    if p >= 1.0: prev = None
    return cur, prev, min(max(p, 0.0), 1.0)


def rainbow(x):
    c = 0.5 + 0.5 * np.cos(2 * np.pi * (x[..., None] - np.array([0.0, 0.33, 0.67], f32)))
    return (c ** 2.2).astype(f32)


# ---------------------------------------------------------------------------------------------- scene
class Scene:
    def __init__(self, vertical=True):
        self.L = L = Layout(vertical); W, H = L.W, L.H
        self.fg = Foreground(FG_PATH, L, hz_frac=0.80)
        self.hz = self.fg.horizon
        self.f = 480.0 if vertical else 420.0
        self.eph = dict(np.load(os.path.join(SCR, "ephem.npz")))
        self.az0 = self._aim(630.0 if vertical else 1150.0)
        self.geo = SkyGeo(W, H, self.hz, self.f, self.az0, self.eph)
        self.cam = SkyCam(W, H, self.hz, self.f)
        self.maps = Maps()
        self.ah = cv2.resize(self.fg.a, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        self.sc = W / 1080 if vertical else 0.75                              # size scale for effects
        hh, hw = H // 2, W // 2
        yy, xx = np.mgrid[0:hh, 0:hw].astype(f32) * 2 + 1.0
        self.hxx, self.hyy = xx, yy
        self.eln = np.clip((self.hz - yy) / self.hz, 0, 1).astype(f32)
        self.shim = [cv2.resize(fbm2((96, 96), 61 + k, 2.2), (hw, hh), interpolation=cv2.INTER_CUBIC) for k in range(2)]
        self._prep_fg()
        caps_emph = {"GAMMA", "RAYS", "MOON", "OUTSHINE", "SUN", "INFRARED", "RADIO", "MICROWAVE", "BLAZES", "UNIVERSE", "SLICE", "VANISHES", "FERMI", "OUTSHINES", "DUST", "WARM"}
        self.caps = Captions(L, WORDS, emphasis=caps_emph)
        r = np.random.default_rng(7)
        n = 6
        self.beams = [dict(a=i * 2 * np.pi / n + r.uniform(-0.3, 0.3), w=r.uniform(0.16, 0.28), I=r.uniform(0.8, 1.2), hue=r.uniform(0, 1),
                           ph=r.uniform(0, 6.28), sp=r.uniform(0.6, 1.4)) for i in range(n)]
        # cosmic rays hitting the Moon: angle, start distance, arrival time
        nr = 34
        self.rays = [dict(a=r.uniform(0, 2 * np.pi), d0=r.uniform(650, 1100) * self.sc, ta=T_CR0 + 0.25 + (T_BLAZE + 0.05 - T_CR0 - 0.25) * (k / (nr - 1)) ** 0.8 + r.uniform(-0.05, 0.05),
                          fl=r.uniform(0.28, 0.42), hue=r.uniform(0.45, 0.85)) for k in range(nr)]
        self.grb = (0.84 * W, 0.17 * H) if vertical else (0.86 * W, 0.20 * H)
        self.rng_fixed = np.random.default_rng(3)
        mt = fbm2((256, 256), 71, 2.3) * 0.7 + fbm2((256, 256), 72, 1.4) * 0.3
        self.moon_tex = np.clip(mt * 0.5 + 0.5, 0, 1.3).astype(f32)

    def _aim(self, target_x):
        """camera azimuth that puts the Moon at target_x at t = 0"""
        m = self.eph["moon"][0]; best = None
        for a in np.arange(0, 360, 0.05):
            aa = math.radians(a); fw = np.array([math.sin(aa), math.cos(aa), 0]); rt = np.array([math.cos(aa), -math.sin(aa), 0])
            z = m @ fw
            if z <= 0.2: continue
            x = self.L.W / 2 + self.f * (m @ rt) / z
            if best is None or abs(x - target_x) < best[0]: best = (abs(x - target_x), a)
        return best[1]

    def up(self, a):
        return cv2.resize(a, (self.L.W, self.L.H), interpolation=cv2.INTER_LINEAR)

    # ------------------------------------------------------------------------------------------ foreground states
    def _prep_fg(self):
        fg = self.fg; W, H = self.L.W, self.L.H; s, oy = fg.s, fg.oy
        a = fg.a; rgb = fg.rgb; flat = fg.flat
        Y = (0.5 * lum(rgb) + 0.5 * lum(flat)).astype(f32)
        sr = lin_to_srgb(rgb)
        green = sr[..., 1] - np.maximum(sr[..., 0], sr[..., 2])
        leaf = (smooth(0.015, 0.09, green) * a).astype(f32)
        self.leaf = leaf
        # sky-facing rim (how much open sky is just above each pixel)
        acc = np.zeros_like(a)
        for k in range(1, 10):
            sh = np.zeros_like(a); sh[k:] = a[:-k]
            acc += (1 - sh) * math.exp(-k / 3.0)
        side = np.zeros_like(a)
        for k in range(1, 6):
            for dx in (-k, k):
                sh = np.roll(a, dx, 1); side += (1 - sh) * math.exp(-k / 2.0) * 0.5
        self.rim = cv2.GaussianBlur(np.clip((acc + side) * a, 0, 1), (0, 0), 0.8).astype(f32)
        yy = np.arange(H, dtype=f32)[:, None] * np.ones((1, W), f32)
        self.depth = smooth(self.hz + 140 * s, self.hz - 200 * s, yy).astype(f32) * a     # far things near the horizon
        # visible: the photo as shot
        self.fg_vis = rgb.astype(f32)
        # infrared: Wood effect (chlorophyll reflects near-IR: foliage and grass go white), everything else dim
        hf = np.clip(fg.hf, 0.5, 1.8)
        leafY = np.clip(0.20 + 2.6 * Y, 0, 1.1) * hf ** 0.8
        irY = Y * 0.55 * (1 - leaf) + leafY * leaf
        lc = np.array([1.00, 0.93, 0.98], f32); oc = np.array([0.60, 0.36, 0.40], f32)
        self.fg_ir = (irY[..., None] * (leaf[..., None] * lc + (1 - leaf[..., None]) * oc)).astype(f32)
        # stylised tints for radio / microwave / gamma: flattened luminance, mode tint, sky-coloured rim
        base = (Y * 0.85 + 0.15 * lum(rgb))[..., None]
        self.fg_tint = {
            "radio": (base * np.array([0.16, 0.42, 0.85], f32) + leaf[..., None] * base * np.array([0.0, 0.18, 0.10], f32)).astype(f32),
            "micro": (base * np.array([0.95, 0.46, 0.26], f32) + leaf[..., None] * base * np.array([0.10, 0.10, 0.0], f32)).astype(f32),
            "gamma": (base * np.array([0.42, 0.17, 0.85], f32) + leaf[..., None] * base * np.array([0.05, 0.0, 0.10], f32)).astype(f32),
        }
        self.rim_col = {"radio": np.array([0.35, 0.95, 1.0], f32), "micro": np.array([1.2, 0.85, 0.45], f32), "gamma": np.array([1.0, 0.45, 1.5], f32),
                        "ir": np.array([1.3, 0.40, 0.75], f32), "vis": np.array([0.0, 0.0, 0.0], f32)}
        self.lamps = [(x * s, y * s + oy, b * s + oy) for x, y, b in LAMPS_SRC]
        self.windows = [(x * s, y * s + oy) for x, y in WINDOWS_SRC]
        x0, y0, x1, y1 = HOUSE_SRC
        hm = np.zeros((H, W), f32)
        X0, X1, Y0, Y1 = int(x0 * s), int(x1 * s), int(y0 * s + oy), int(y1 * s + oy)
        if X1 > 0 and Y1 > 0 and X0 < W and Y0 < H:
            hm[max(Y0, 0):min(Y1, H), max(X0, 0):min(X1, W)] = 1.0
        hm = cv2.GaussianBlur(hm, (0, 0), 3.0 * s) * a * (1 - leaf)
        self.house = hm.astype(f32)

    def fg_state(self, mode, t):
        a = self.fg.a[..., None]
        if mode == "vis": return self.fg_vis
        if mode == "ir":
            warm = ramp(t, SW["ir"] + 0.25, SW["ir"] + 1.6)
            img = self.fg_ir + self.rim[..., None] * self.rim_col["ir"] * 0.10
            img = img + self.house[..., None] * np.array([1.6, 0.55, 0.12], f32) * 0.55 * warm * (0.9 + 0.1 * math.sin(t * 3.1))
            return img
        img = self.fg_tint[mode] * 0.75 + self.rim[..., None] * self.rim_col[mode] * 0.08
        img = img + self.depth[..., None] * self.rim_col[mode] * 0.035
        return img

    # ------------------------------------------------------------------------------------------ helpers
    def hglow(self, buf, x, y, prof, col, rad):
        """add prof(d_full_px) * col into the half-res buffer around full-res point (x, y)"""
        splat(buf, x / 2, y / 2, rad / 2, lambda d, dx, dy: (prof(d * 2))[..., None] * np.asarray(col, f32))

    def moon_shape(self, img, mp, sp, R, col, earth=0.0, soft=1.2, full=False):
        """crescent (or full disc) of radius R at full res; lit side faces the Sun direction on screen"""
        if mp is None: return
        ux, uy = (sp[0] - mp[0], sp[1] - mp[1]) if sp is not None else (1.0, 0.0)
        n = math.hypot(ux, uy) + 1e-6; ux, uy = ux / n, uy / n
        ce = math.cos(self.elong)
        col = np.asarray(col, f32)
        def fn(d, dx, dy):
            u = (dx * ux + dy * uy) / R; w = (-dx * uy + dy * ux) / R
            disc = smooth(R + soft, R - soft, d)
            if full: lit = np.ones_like(d)
            else: lit = smooth(-0.04, 0.04, u - ce * np.sqrt(np.clip(1 - w * w, 0, 1)))
            mare = 0.86 + 0.14 * np.sin(dx * 0.21 + 1.3) * np.sin(dy * 0.17 + 0.4)
            return (disc * (lit * mare + earth))[..., None] * col
        splat(img, mp[0], mp[1], R + 4, fn)

    # ------------------------------------------------------------------------------------------ skies
    def sky_vis(self, t, sp, mp):
        sx, sy = sp if sp else (self.L.W * 0.8, self.hz - 300)
        img = day_sky(self.cam, sx, sy, t, sun=1.0, cirrus=0.22)
        # big slow rainbow beams from the Sun (the reference look), only in the sky
        hb = np.zeros(self.hxx.shape + (3,), f32)
        dx = self.hxx - sx; dy = self.hyy - sy; d = np.sqrt(dx * dx + dy * dy) + 1e-3; phi = np.arctan2(dy, dx)
        rad = (1 - np.exp(-d / 30)) * (np.exp(-d / 1300) * 0.9 + 0.1)
        for b in self.beams:
            a = b["a"] + 0.05 * t * b["sp"]
            dp = (phi - a + np.pi) % (2 * np.pi) - np.pi
            w = b["w"] * (1 + 0.25 * math.sin(t * 0.9 * b["sp"] + b["ph"]))
            g = np.exp(-(dp / w) ** 2 * 1.6) * b["I"] * (0.75 + 0.25 * math.sin(t * 1.3 * b["sp"] + b["ph"]))
            hb += rainbow((b["hue"] + dp / w * 0.30) % 1.0) * g[..., None]
        img += self.up(hb * rad[..., None] * 0.34)
        self.moon_shape(img, mp, sp, 26 * self.sc, (0.62, 0.64, 0.70), earth=0.07)
        sun_disc(img, sx, sy, 10 * self.sc, 1.0)
        lens_flare(img, sx, sy, 0.7)
        return img

    def sky_ir(self, t, mx, my, sp, mp):
        k = 1.6 + 0.6 * math.sin(t * 0.9)
        sx = mx + self.shim[0] * k + 3.0 * np.sin(t * 2.1 + self.hyy[:, :1] * 0.02)
        syy = my + self.shim[1] * k
        v = self.geo.sample(self.maps.ir, sx.astype(f32), syy.astype(f32))
        v = np.clip(v * 1.05 + 0.05 * np.sin(t * 1.7 + self.hyy * 0.01), 0, 1.2)
        hb = apply_lut(PAL["ir"], v / 1.2) * 0.75
        # the air itself glows in thermal infrared, brightest near the horizon
        hb += (np.exp(-self.eln / 0.22)[..., None] * np.array([0.55, 0.12, 0.10], f32) + np.array([0.05, 0.01, 0.04], f32))
        if sp:
            self.hglow(hb, *sp, lambda d: np.exp(-d / (90 * self.sc)) * 1.6 + np.exp(-d / (320 * self.sc)) * 0.35, (1.0, 0.75, 0.40), 1200 * self.sc)
        if mp:
            self.hglow(hb, *mp, lambda d: np.exp(-d / (40 * self.sc)) * 0.45, (1.0, 0.55, 0.25), 300 * self.sc)
        img = self.up(hb)
        if sp:
            def fn(d, dx, dy): return (smooth(16 * self.sc + 1, 16 * self.sc - 1, d) * 40 + np.exp(-d / (14 * self.sc)) * 6)[..., None] * np.array([1.0, 0.85, 0.6], f32)
            splat(img, sp[0], sp[1], 200 * self.sc, fn)
        self.moon_shape(img, mp, sp, 26 * self.sc, (1.8, 0.75, 0.30), earth=0.15)
        return img

    def sources_layer(self, M, t, col, names=True, n_blz=120, gain=1.0):
        """twinkling compact sources (4FGL blazars + named radio sources) on a half-res layer"""
        lay = np.zeros(self.hxx.shape, f32)
        blz = self.maps.blz[:n_blz]
        enu = self.geo.gal_to_enu(M, blz[:, 0], blz[:, 1])
        x, y, ok = self.geo.project_many(enu)
        hh, hw = lay.shape
        for i in np.where(ok)[0]:
            xi, yi = int(x[i] / 2), int(y[i] / 2)
            if 1 <= xi < hw - 1 and 1 <= yi < hh - 1:
                tw = 0.6 + 0.4 * math.sin(t * (2.5 + (i % 7) * 0.6) + i * 1.7)
                lay[yi, xi] += (0.25 + 1.6 * float(blz[i, 2]) ** 0.5) * tw * gain
        lay = cv2.GaussianBlur(lay, (0, 0), 0.8) * 7 + cv2.GaussianBlur(lay, (0, 0), 3.0) * 6
        return lay[..., None] * np.asarray(col, f32)

    def sky_radio(self, t, M, mx, my, sp, mp):
        v = self.geo.sample(self.maps.radio, mx, my)
        # slow "breathing" pulse that travels along the band
        pulse = 1 + 0.06 * np.sin(t * 2.2 - (self.hxx + self.hyy) * 0.006)
        hb = apply_lut(PAL["radio"], np.clip(v * pulse, 0, 1.0)) * 0.95
        hb += self.sources_layer(M, t, (0.6, 1.0, 1.1), gain=0.9)
        # named radio sources: bright stars with expanding radio-wave rings
        for k, (name, l, b, br) in enumerate(RADIO_SRC):
            e = self.geo.gal_to_enu(M, np.array([l]), np.array([b]))[0]
            p = self.geo.project(e)
            if p is None or not (-50 < p[0] < self.L.W + 50 and -50 < p[1] < self.hz): continue
            ph = (t * 0.55 + k * 0.37) % 1.0
            rr = (30 + 260 * ph) * self.sc
            def prof(d, rr=rr, ph=ph, br=br):
                return (np.exp(-d / (9 * self.sc)) * 4.0 + np.exp(-((d - rr) / (6 * self.sc)) ** 2) * 0.35 * (1 - ph) ** 1.5) * br
            self.hglow(hb, p[0], p[1], prof, (0.7, 1.0, 1.0), 320 * self.sc)
        if sp:   # the radio Sun: a modest disc with a soft corona
            self.hglow(hb, *sp, lambda d: smooth(34 * self.sc, 26 * self.sc, d) * 1.4 + np.exp(-d / (40 * self.sc)) * 0.5, (1.0, 0.70, 0.30), 500 * self.sc)
        return self.up(hb)

    def sky_micro(self, t, M, mx, my, sp, mp):
        c = self.geo.sample(self.maps.cmb, mx, my); g = self.geo.sample(self.maps.cmbgal, mx, my)
        x = 0.5 + 0.5 * np.clip(c * 1.25, -1, 1)
        # the whole sky glows: a slow luminous swell rolling across it
        wave = 1 + 0.10 * np.sin(t * 1.8 - self.hyy * 0.008 + 0.4 * np.sin(self.hxx * 0.004 + t * 0.5))
        hb = apply_lut(PAL["cmb"], x) * (0.55 * wave)[..., None]
        hb += g[..., None] ** 1.3 * np.array([1.9, 1.6, 1.25], f32) * 1.1
        hb += np.exp(-self.eln / 0.3)[..., None] * np.array([0.10, 0.06, 0.03], f32)
        if sp:
            self.hglow(hb, *sp, lambda d: smooth(24 * self.sc, 18 * self.sc, d) * 2.5 + np.exp(-d / (30 * self.sc)) * 0.5, (1.0, 0.90, 0.75), 300 * self.sc)
        if mp:
            self.hglow(hb, *mp, lambda d: smooth(22 * self.sc, 16 * self.sc, d) * 0.35, (1.0, 0.85, 0.7), 60 * self.sc)
        return self.up(hb)

    def moon_level(self, t):
        hit = sum(math.exp(-((t - r["ta"]) / 0.06) ** 2) * 0.10 for r in self.rays)
        base = 0.65 + 0.25 * ramp(t, T_CR0, T_BLAZE) + 0.45 * ramp(t, T_BLAZE - 0.05, T_BLAZE + 0.5)
        flash = 2.2 * math.exp(-max(t - T_BLAZE, 0) / 0.35) * (t > T_BLAZE - 0.03)
        return base * (1 + 0.05 * math.sin(t * 5.0)) + hit + flash

    def sky_gamma(self, t, M, mx, my, sp, mp):
        sc = self.sc
        v = self.geo.sample(self.maps.gamma, mx, my)
        hb = apply_lut(PAL["gamma"], np.clip(v, 0, 1) ** 1.25) * 0.62
        hb += np.exp(-self.eln / 0.35)[..., None] * np.array([0.05, 0.01, 0.10], f32)
        # photon sparkle: individual gamma-ray "hits", more where the sky is brighter
        rng = np.random.default_rng(int(t * FPS) + 11)
        wgt = (np.clip(v, 0, 1) ** 4 * (1 - self.ah)).ravel(); wgt /= wgt.sum()
        idx = rng.choice(wgt.size, 140, p=wgt)
        lay = np.zeros(v.shape, f32); lay.ravel()[idx] += rng.uniform(0.5, 2.5, 140).astype(f32)
        lay = cv2.GaussianBlur(lay, (0, 0), 0.7) * 3 + cv2.GaussianBlur(lay, (0, 0), 2.5) * 2
        hb += lay[..., None] * np.array([0.9, 0.6, 1.3], f32)
        hb += self.sources_layer(M, t, (1.0, 0.65, 1.3), n_blz=160, gain=1.1)
        # the quiet Sun: almost dark (a faint violet rim)
        if sp:
            ks = 0.30 * (1 - 0.85 * ramp(t, T_QUIET0, T_QUIET1))
            self.hglow(hb, *sp, lambda d: smooth(30 * sc, 26 * sc, d) * (np.exp(-np.abs(d - 28 * sc) / (5 * sc)) * ks), (0.8, 0.5, 1.2), 80 * sc)
        # the Moon: a huge blazing orb (cosmic rays hitting the surface; no phases in gamma rays)
        ml = self.moon_level(t)
        R = (100 + 42 * ease(ramp(t, T_BLAZE - 0.1, T_BLAZE + 0.6))) * sc
        if mp:
            def halo(d, R=R, ml=ml):
                # centre-peaked bloom halo (no bright rim: the orb must read as a filled ball, not a ring)
                return (np.exp(-d / (0.55 * R)) * 0.8 + np.exp(-d / (190 * sc)) * 0.50
                        + np.exp(-d / (500 * sc)) * 0.05) * ml
            self.hglow(hb, *mp, halo, (0.85, 0.55, 1.35), 1500 * sc)
            # shock ring at the blaze
            u = (t - T_BLAZE) / 1.3
            if 0 < u < 1:
                rr = R + 700 * sc * ease(u) ** 0.7
                self.hglow(hb, *mp, lambda d: np.exp(-((d - rr) / (14 * sc)) ** 2) * 1.4 * (1 - u) ** 1.6, (1.0, 0.8, 1.3), rr + 60 * sc)
        # cosmic rays streaking in
        if T_CR0 < t < T_BLAZE + 0.4 and mp:
            cl = np.zeros(hb.shape, f32)
            for r in self.rays:
                u = (t - (r["ta"] - r["fl"])) / r["fl"]
                if not (0 <= u <= 1.0): continue
                dist = R + r["d0"] * (1 - u) ** 1.2
                ln = 160 * sc * (0.4 + 0.6 * (1 - u))
                ca, sa = math.cos(r["a"]), math.sin(r["a"])
                x0, y0 = (mp[0] + ca * dist) / 2, (mp[1] + sa * dist) / 2
                x1, y1 = (mp[0] + ca * (dist + ln)) / 2, (mp[1] + sa * (dist + ln)) / 2
                col = tuple(float(c) * 3.0 for c in rainbow(np.array(r["hue"], f32)))
                cv2.line(cl, (int(x0 * 8), int(y0 * 8)), (int(x1 * 8), int(y1 * 8)), (col[0] * 0.5 + 1.2, col[1] * 0.5 + 1.2, col[2] * 0.5 + 1.4), 2, cv2.LINE_AA, 3)
            hb += cv2.GaussianBlur(cl, (0, 0), 0.8) * 1.2 + cv2.GaussianBlur(cl, (0, 0), 4.0) * 1.5
        # a gamma-ray burst flashes in a far galaxy
        u = (t - T_GRB) / 1.6
        if -0.02 < u < 1:
            gx, gy = self.grb
            fl = math.exp(-max(u, 0) / 0.10) * 6 + math.exp(-max(u, 0) / 0.5) * 1.2
            self.hglow(hb, gx, gy, lambda d: np.exp(-d / (10 * sc)) * fl + np.exp(-d / (90 * sc)) * fl * 0.12, (0.95, 0.85, 1.25), 700 * sc)
            rr = 20 * sc + 520 * sc * ease(max(u, 0)) ** 0.6
            self.hglow(hb, gx, gy, lambda d: np.exp(-((d - rr) / (9 * sc)) ** 2) * 0.8 * (1 - u) ** 2, (0.7, 0.9, 1.4), rr + 40 * sc)
            hb += np.array([0.05, 0.03, 0.08], f32) * math.exp(-max(u, 0) / 0.12) * 2
        img = self.up(hb)
        if sp:   # dark disc: the quiet Sun barely glows
            ks = 1 - 0.8 * ramp(t, T_QUIET0, T_QUIET1)
            def dark(d, dx, dy): return smooth(29 * sc, 25 * sc, d)[..., None]
            x0, y0 = int(sp[0] - 32 * sc), int(sp[1] - 32 * sc)
            yy, xx = np.mgrid[0:int(64 * sc) + 1, 0:int(64 * sc) + 1].astype(f32)
            H, W = img.shape[:2]
            ya, xa = max(y0, 0), max(x0, 0); yb, xb = min(y0 + yy.shape[0], H), min(x0 + yy.shape[1], W)
            if yb > ya and xb > xa:
                d = np.sqrt((xx + x0 + 0.5 - sp[0]) ** 2 + (yy + y0 + 0.5 - sp[1]) ** 2)[ya - y0:yb - y0, xa - x0:xb - x0]
                m = smooth(29 * sc, 25 * sc, d)[..., None]
                img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - m * 0.85) + m * np.array([0.05, 0.02, 0.09], f32) * (0.6 + ks)
        if mp:   # orb body: a filled, fuzzy, mottled blazing Moon (like Fermi's gamma-ray Moon), gently pulsing
            tex = self.moon_tex; th, tw = tex.shape
            pulse = 1 + 0.07 * math.sin(t * 3.3) + 0.04 * math.sin(t * 7.1 + 1)
            def orb(d, dx, dy, R=R, ml=ml):
                q = d / R
                body = smooth(1.20, 0.55, q)                                    # soft, PSF-blurred edge
                u = ((dx / R * 0.5 + 0.5 + 0.03 * t) * (tw - 1)).astype(np.int32) % tw
                v = ((dy / R * 0.5 + 0.5 - 0.02 * t) * (th - 1)).astype(np.int32) % th
                n = tex[v, u]
                core = np.exp(-(q / 0.50) ** 2)
                mid = np.array([0.95, 0.36, 1.9], f32); hot = np.array([2.3, 1.8, 2.9], f32)
                val = body[..., None] * mid * (0.45 + 0.85 * n)[..., None] + core[..., None] * hot * 1.6 * (0.65 + 0.6 * n)[..., None]
                return val * ml * pulse
            splat(img, mp[0], mp[1], R * 1.3, orb)
            for r in self.rays:                                               # impact flashes on the limb
                du = t - r["ta"]
                if 0 <= du < 0.25:
                    hx, hy = mp[0] + math.cos(r["a"]) * R, mp[1] + math.sin(r["a"]) * R
                    k = math.exp(-du / 0.07) * 9
                    splat(img, hx, hy, 40 * sc, lambda d, dx, dy, k=k: (np.exp(-d / (5 * sc)) * k)[..., None] * np.array([1.0, 0.95, 1.2], f32))
        return img

    # ------------------------------------------------------------------------------------------ one mode
    def render_mode(self, mode, t, M, mx, my, sp, mp):
        L = self.L; a = self.fg.a[..., None]
        if mode == "vis": sky = self.sky_vis(t, sp, mp)
        elif mode == "ir": sky = self.sky_ir(t, mx, my, sp, mp)
        elif mode == "radio": sky = self.sky_radio(t, M, mx, my, sp, mp)
        elif mode == "micro": sky = self.sky_micro(t, M, mx, my, sp, mp)
        else: sky = self.sky_gamma(t, M, mx, my, sp, mp)
        fgi = self.fg_state(mode, t)
        img = sky * (1 - a) + fgi * a
        if mode == "ir":                                                       # warm things glow: lamps + windows
            warm = ramp(t, SW["ir"] + 0.25, SW["ir"] + 1.6)
            gl = np.zeros(self.hxx.shape + (3,), f32)
            for i, (lx, ly, by) in enumerate(self.lamps):
                fl = warm * (1 + 0.06 * noise1(t, 30 + i, 6.0))
                self.hglow(gl, lx, ly, lambda d, fl=fl: (np.exp(-d / (6 * self.sc)) * 6 + np.exp(-d / (28 * self.sc)) * 1.2 + np.exp(-d / (90 * self.sc)) * 0.25) * fl,
                           (1.0, 0.55, 0.18), 400 * self.sc)
            for (wx, wy) in self.windows:
                self.hglow(gl, wx, wy, lambda d: (np.exp(-d / (7 * self.sc)) * 2.0 + np.exp(-d / (30 * self.sc)) * 0.4) * warm, (1.0, 0.45, 0.12), 160 * self.sc)
            img = img + self.up(gl)
        if mode == "gamma" and mp:                                             # the Moon's violet light on the park
            ml = self.moon_level(t)
            img = img + a * self.rim[..., None] * np.array([0.5, 0.25, 0.8], f32) * 0.10 * ml
        img = bloom(img, {"vis": 0.6, "ir": 0.9, "radio": 1.0, "micro": 0.8, "gamma": 0.75}[mode])
        out = tonemap(img, EXPO[mode])
        y = out.mean(2, keepdims=True)
        out = np.clip(y + (out - y) * SAT[mode], 0, 1)
        return out

    def wipe(self, old, new, p, t, end=False):
        """diagonal colour wipe: new mode sweeps in from the upper left with a spectral leading edge"""
        W, H = self.L.W, self.L.H
        hh, hw = H // 2, W // 2
        s = (self.hxx * 0.80 + self.hyy * 0.60) / (W * 0.80 + H * 0.60)     # 0 top-left .. 1 bottom-right
        s = s + 0.015 * np.sin(self.hyy * 0.02 + t * 9) + 0.01 * np.sin(self.hxx * 0.03 - t * 7)
        front = -0.08 + 1.16 * ease(p) if not end else -0.08 + 1.16 * p
        m = smooth(front + 0.015, front - 0.015, s)
        e = np.exp(-((s - front) / 0.035) ** 2)
        col = rainbow(((s - front) / 0.035 * 0.22 + t * 0.7) % 1.0)
        m = self.up(m)[..., None]; e = self.up(e)[..., None]; col = self.up(col)
        out = old * (1 - m) + new * m
        out = out + e * (col * 0.9 + 0.35)
        # chromatic smear along the edge
        sh = int(10 * self.sc)
        if sh > 0:
            r = np.roll(out[..., 0], sh, 1); b = np.roll(out[..., 2], -sh, 1)
            out[..., 0] = out[..., 0] * (1 - e[..., 0]) + r * e[..., 0]; out[..., 2] = out[..., 2] * (1 - e[..., 0]) + b * e[..., 0]
        return np.clip(out, 0, 1)

    def chroma(self, out):
        W, H = self.L.W, self.L.H
        o = out.copy()
        for ch, k in ((0, 1.0018), (2, 0.9982)):
            M = np.float32([[k, 0, (1 - k) * W / 2], [0, k, (1 - k) * H / 2]])
            o[..., ch] = cv2.warpAffine(out[..., ch], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return o

    def frame(self, t):
        M, sun, moon = self.geo.at(t)
        self.elong = math.acos(max(-1.0, min(1.0, float(sun @ moon))))
        sp = self.geo.project(sun); mp = self.geo.project(moon)
        mx, my = self.geo.lookup(M)
        cur, prev, p = mode_at(t)
        out = self.render_mode(cur, t, M, mx, my, sp, mp)
        if prev is not None:
            old = self.render_mode(prev, t, M, mx, my, sp, mp)
            out = self.wipe(old, out, p, t, end=(SEQ[-1][1] <= t))
        # white-out flash on the snap back to daylight (and a softer pop on every switch)
        fl = 0.85 * math.exp(-max(t - SW["vis2"] - 0.10, 0) / 0.16) * (t > SW["vis2"] + 0.02)
        fl += sum(0.10 * math.exp(-max(t - SW[k] - 0.25, 0) / 0.10) * (t > SW[k] + 0.2) for k in ("ir", "radio", "micro"))
        fl += 0.22 * math.exp(-max(t - T_BLAZE, 0) / 0.12) * (t > T_BLAZE - 0.02)
        if fl > 0.003:
            out = out + (1 - out) * min(fl, 1.0) * np.array([1.0, 0.97, 1.0], f32)
        out = self.chroma(out)
        out = finish(out, t, grain=0.010, vignette=0.16)
        self.overlay(out, t)
        return out

    # ------------------------------------------------------------------------------------------ text
    def overlay(self, out, t):
        L = self.L; W = L.W
        top = (L.safe_top + 62) if L.vertical else 100
        cur, prev, p = mode_at(t)
        starts = {m: ts for m, ts in SEQ}
        t_in = 0.0 if (cur == "vis" and t < 1) else max(ts for m, ts in SEQ if ts <= t)
        age = t - t_in - (0.20 if t_in > 0 else 0.0)
        if age > -0.0:
            if cur == "vis" and t < SW["ir"]: a_ = ramp(t, 0.0, 0.25) * (1 - ramp(t, SW["ir"] - 0.25, SW["ir"]))
            else: a_ = ramp(age, 0, 0.12)
            if cur == "vis" and t >= SW["vis2"]: a_ = ramp(age, 0, 0.15)
            if cur == "gamma": a_ *= 1 - 0.75 * ramp(t, T_FACT0 - 0.2, T_FACT0 + 0.1)
            nxt = [ts for m, ts in SEQ if ts > t]
            if nxt: a_ *= 1 - ramp(t, nxt[0] - 0.12, nxt[0] + 0.05)
            pop = 1.0 + 0.22 * math.exp(-max(age, 0) / 0.07) if t_in > 0 else 1.0
            title, sub = LABEL[cur]
            size = (96 if L.vertical else 84) * pop
            if a_ > 0.01:
                rgba, _ = word_layer(title, size, 980 if L.vertical else 1300, fill=MODE_COL[cur])
                composite(out, rgba, W / 2, top, a_)
                hud_text(out, sub, W / 2, top + (78 if L.vertical else 66), int(L.hud_size * 0.42), "Bold", (240, 240, 248), a_ * 0.92, 0.14)
        # the Fermi fact card
        a = ramp(t, T_FACT0, T_FACT0 + 0.25) * (1 - ramp(t, T_FACT1 - 0.25, T_FACT1))
        if a > 0.01:
            y0 = (L.hud_y - 90) if L.vertical else 820
            hud_text(out, "NASA FERMI TELESCOPE", W / 2, y0, int(L.hud_size * 0.48), "Bold", (235, 225, 255), a, 0.18)
            rgba, _ = word_layer("MOON  >  SUN", (104 if L.vertical else 88), 980, fill=(214, 150, 255))
            composite(out, rgba, W / 2, y0 + (88 if L.vertical else 76), a)
            hud_text(out, "IN GAMMA RAYS ABOVE 31 MeV", W / 2, y0 + (175 if L.vertical else 150), int(L.hud_size * 0.48), "Bold", (235, 225, 255), a, 0.14)
        self.caps.draw(out, t)


# ---------------------------------------------------------------------------------------------- run
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
