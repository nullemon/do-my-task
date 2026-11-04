"""Plate handling + wave/foam/slide effects + vector drawing for the 06 compositor."""
import os, math
import numpy as np
from PIL import Image, ImageDraw
from common import *          # noqa
import world as Wd
from world import sst

EXPO = 2.3


class Plate:
    """A rendered camera: forest (before), strip (after) and data (world xyz + alpha) passes, plus derived maps."""
    def __init__(self, cam, strip=True, derive=True):
        self.cam_name = cam
        self.forest = np.load(os.path.join(PL, f"{cam}_forest.npy")).astype(np.float32)
        sp = os.path.join(PL, f"{cam}_strip.npy")
        self.strip = np.load(sp).astype(np.float32) if (strip and os.path.exists(sp)) else self.forest
        d = np.load(os.path.join(PL, f"{cam}_data.npy")).astype(np.float32)
        self.hp, self.wp = d.shape[:2]
        self.X = d[..., 0]; self.Y = d[..., 1]; self.Z = d[..., 2]; self.A = d[..., 3]
        self.cam = Cam(cam)
        self.sky = (self.A < 0.5)
        self.water = (~self.sky) & (self.Z < -2.0)
        self.land = (~self.sky) & (~self.water)
        if derive:
            self._derive()

    def _derive(self):
        xk = self.X / 1000.0; yk = self.Y / 1000.0
        z = np.where(self.land, self.Z, 0.0)
        idx = np.where(self.land)
        F = Wd.fields(xk[idx], yk[idx])
        R = Wd.runup(xk[idx], yk[idx]); wl = Wd.wet_limit(xk[idx], yk[idx])
        wet = np.zeros(self.X.shape, np.float32)
        zz = z[idx]
        wv = sst(-4, 6, R - zz) * (F["dw"] >= -0.02) * sst(0.03, 0.0, F["dw"] - wl) * (F["gm"] < 0.5)
        wet[idx] = wv
        self.wet = wet
        self.R = np.zeros_like(wet); self.R[idx] = R
        ta = np.full(self.X.shape, 1e6, np.float32)
        ta[idx] = Wd.arrival(xk[idx], yk[idx], zz)
        iw = np.where(self.water)
        ta[iw] = Wd.arrival(xk[iw], yk[iw], np.zeros(len(iw[0]), np.float32))
        xs_, ys_ = self.X / 1000.0, self.Y / 1000.0
        ta += (2.2 * Wd.noise(xs_, ys_, 0.025, 85) + 1.2 * Wd.noise(xs_, ys_, 0.008, 86)) * (~self.sky)
        self.Ta = ta
        self._after = None
        sm = np.zeros_like(wet); sm[idx] = Wd.slide_mask(xk[idx], yk[idx], zz); self.sm = sm
        # distance from camera (m) for depth tests
        c = self.cam.M[:3, 3]
        self.depth = np.where(self.sky, 1e9, np.sqrt((self.X - c[0]) ** 2 + (self.Y - c[1]) ** 2 + (self.Z - c[2]) ** 2)).astype(np.float32)

    def after(self, churn=0.6):
        """Static 'long after the wave' composite at plate resolution (trimline revealed, churned water)."""
        if self._after is None:
            w = self.wet[..., None]
            img = self.forest * (1 - w) + self.strip * w
            wat = self.water.astype(np.float32)[..., None] * churn
            xk = self.X / 1000.0; yk = self.Y / 1000.0
            stw = Wd.noise(xk * 3.0, yk * 0.8, 0.05, 83)
            fw = np.clip(1 - np.abs(stw + 0.5 * Wd.noise(xk, yk, 0.006, 84)) * 1.6, 0, 1) ** 2.5
            deep = np.array([0.008, 0.012, 0.017], np.float32)
            img = img * (1 - 0.8 * wat) + deep * 0.8 * wat + np.array([0.08, 0.09, 0.105], np.float32) * (wat * fw[..., None])
            self._after = img.astype(np.float32)
        return self._after

    def crop(self, arrs, z, cx, cy):
        cx, cy = clamp_center((self.hp, self.wp), z, cx, cy)
        out = zoom_crop_ch([np.ascontiguousarray(a, np.float32) for a in arrs], z, cx, cy)
        return [out[..., i] for i in range(out.shape[-1])], (cx, cy)


def crop3(img, z, cx, cy):
    return zoom_crop_ch([np.ascontiguousarray(img[..., c]) for c in range(3)], z, cx, cy)


def anim_noise(x, y, t, scale, seed, flow=(0.0, 0.0)):
    return Wd.noise(x + flow[0] * t, y + flow[1] * t, scale, seed)


def surge_layer(P, tau, z, cx, cy, foam_gain=1.0, cover_dur=9.0, drain=6.0, extra=None, band_gain=1.0):
    """Composite the before/after plates with the moving water for event time tau (s after impact).
    Returns linear RGB (H,W,3) plus helper maps."""
    chans = [P.forest[..., 0], P.forest[..., 1], P.forest[..., 2], P.strip[..., 0], P.strip[..., 1], P.strip[..., 2],
             P.X, P.Y, P.Z, P.Ta, P.wet, P.water.astype(np.float32), P.land.astype(np.float32)]
    if extra is not None:
        chans += extra
    C, (cx, cy) = P.crop(chans, z, cx, cy)
    fo = np.stack(C[0:3], -1); st = np.stack(C[3:6], -1)
    X, Y, Z, Ta, wet, wat, lnd = C[6:13]
    xk = X / 1000.0; yk = Y / 1000.0
    f = tau - Ta
    passed = wet * sst(0.0, 2.0, f)
    img = fo * (1 - passed[..., None]) + st * passed[..., None]
    # soaked ground right after the water drains: darker, then slowly back
    soak = passed * sst(cover_dur, cover_dur + drain, f) * (1 - sst(cover_dur + drain, cover_dur + drain + 40, f))
    img *= (1 - 0.35 * soak)[..., None]
    # moving whitewater on the land: dark turbulent water with flow-aligned foam streaks, bright at the front
    ang = np.arctan2(yk - Wd.IMPACT[1], xk - Wd.IMPACT[0]); rad = np.hypot(xk - Wd.IMPACT[0], yk - Wd.IMPACT[1])
    stk = 0.6 * Wd.noise(ang * 14.0, rad * 6.0 - 0.012 * tau, 0.05, 81) + 0.6 * Wd.noise(xk, yk - 0.002 * tau, 0.02, 87)
    n2 = Wd.noise(xk - 0.002 * tau, yk + 0.005 * tau, 0.012, 82)
    foam = np.clip(sst(0.1, 1.2, stk + 0.5 * n2), 0, 1)
    cover = wet * sst(-0.3, 0.4, f) * (1 - sst(cover_dur, cover_dur + drain, f))
    front = wet * np.exp(-((f - 0.4) / 0.9) ** 2)
    foam_col = np.array([0.36, 0.41, 0.48], np.float32)
    dark_w = np.array([0.022, 0.030, 0.040], np.float32)
    deep_w = np.array([0.008, 0.012, 0.017], np.float32)
    fm = np.clip(foam * 0.35 + front * (0.55 + 0.45 * foam), 0, 1) * foam_gain
    wcol = dark_w[None, None] * (1 - fm[..., None]) + foam_col[None, None] * fm[..., None]
    img = img * (1 - cover[..., None]) + wcol * cover[..., None]
    # water body: wave front band + churned water behind it
    fw = (tau - Ta) * wat
    band = wat * np.exp(-((fw - 0.8) / 2.5) ** 2) * band_gain
    churn_w = wat * sst(0, 2.0, fw) * (0.45 + 0.55 * np.exp(-np.maximum(fw, 0) / 120.0))
    stw = Wd.noise(xk * 3.0 + 0.004 * tau, yk * 0.8 - 0.004 * tau, 0.05, 83)
    foam_w = np.clip(1 - np.abs(stw + 0.5 * Wd.noise(xk, yk + 0.004 * tau, 0.006, 84)) * 1.6, 0, 1) ** 2.5
    img = img * (1 - 0.8 * churn_w[..., None]) + deep_w[None, None] * (0.8 * churn_w)[..., None]
    img += (foam_col * 0.22)[None, None] * (churn_w * foam_w)[..., None] * foam_gain
    img += (foam_col * 0.8)[None, None] * (band * (0.4 + 0.6 * foam_w))[..., None] * foam_gain
    # spray / mist above the climbing front (screen-space glow, offset upward)
    mist = down4(np.ascontiguousarray((front * (0.5 + 0.5 * foam) + band * 0.5).astype(np.float32)))
    mist = blur(mist, 6)
    mist = np.roll(mist, -3, axis=0)
    img += up4(mist)[..., None] * np.array([0.30, 0.34, 0.40], np.float32) * 0.6 * foam_gain
    return img, dict(X=X, Y=Y, Z=Z, wat=wat, lnd=lnd, f=f, wet=wet, extra=C[13:], cx=cx, cy=cy)


def finish(lin, exposure=EXPO, lift=0.0, sat=1.0, tint=(1, 1, 1)):
    lin = lin * np.asarray(tint, np.float32)
    if sat != 1.0:
        l = lin.mean(-1, keepdims=True); lin = l + (lin - l) * sat
    d = tonemap(lin, exposure)
    d = 0.6 * d + 0.4 * d * d * (3 - 2 * d)          # gentle S-curve for contrast
    if lift:
        d = d * (1 - lift) + lift
    return d


def shake(t, t0, t1, amp, seed=0):
    """2D camera shake offset (plate px) for an earthquake between t0 and t1."""
    if t < t0 or t > t1:
        return 0.0, 0.0
    e = ss(t0, t0 + 0.6, t) * (1 - ss(t1 - 3.0, t1, t))
    r = np.random.default_rng(seed + int(t * 24))
    return (amp * e * (math.sin(t * 37) * 0.6 + r.uniform(-0.4, 0.4)),
            amp * e * (math.sin(t * 29 + 1) * 0.6 + r.uniform(-0.4, 0.4)))


# ------------------------------------------------------------------ vector drawing (2x supersampled PIL)
def srgb(c):
    return np.asarray(c, np.float32) ** 2.2


class Vec:
    def __init__(self, ss=2):
        self.ss = ss
        self.im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def _p(self, pts):
        return [(float(x) * self.ss, float(y) * self.ss) for x, y in pts]

    def line(self, pts, col=(225, 230, 235), width=1.6, alpha=1.0):
        if alpha <= 0.003: return
        c = tuple(int(v) for v in col) + (int(255 * min(alpha, 1)),)
        self.d.line(self._p(pts), fill=c, width=max(1, int(round(width * self.ss))), joint="curve")

    def dashed(self, pts, col=(225, 230, 235), width=1.4, alpha=1.0, dash=10, gap=8):
        pts = np.asarray(pts, np.float64)
        seg = np.diff(pts, axis=0); L = np.hypot(seg[:, 0], seg[:, 1]); cum = np.concatenate([[0], np.cumsum(L)])
        s = 0.0
        while s < cum[-1]:
            e = min(s + dash, cum[-1])
            ss_ = np.linspace(s, e, 4)
            xs = np.interp(ss_, cum, pts[:, 0]); ys = np.interp(ss_, cum, pts[:, 1])
            self.line(list(zip(xs, ys)), col, width, alpha)
            s += dash + gap

    def poly(self, pts, fill=(225, 230, 235), alpha=1.0, outline=None, width=1.5):
        if alpha <= 0.003: return
        c = tuple(int(v) for v in fill) + (int(255 * min(alpha, 1)),)
        o = None if outline is None else tuple(int(v) for v in outline) + (int(255 * min(alpha, 1)),)
        self.d.polygon(self._p(pts), fill=c, outline=o, width=max(1, int(width * self.ss)) if o else 0)

    def circle(self, x, y, r, fill=None, outline=(225, 230, 235), alpha=1.0, width=1.5):
        if alpha <= 0.003: return
        s = self.ss
        f = None if fill is None else tuple(int(v) for v in fill) + (int(255 * alpha),)
        o = None if outline is None else tuple(int(v) for v in outline) + (int(255 * alpha),)
        self.d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=f, outline=o,
                       width=max(1, int(width * s)) if o else 0)

    def comp(self, disp):
        im = self.im.resize((W, H), Image.LANCZOS) if self.ss != 1 else self.im
        a = np.asarray(im, np.float32) / 255.0
        al = a[..., 3:4]
        rgb = a[..., :3] ** 2.2
        disp[:] = disp * (1 - al) + rgb * al
        return disp


# ------------------------------------------------------------------ silhouettes (true scale), metres
def eiffel(h=330.0):
    """Side silhouette of the Eiffel Tower: (outer polygon, arch polygon) in metres, x centred, y up."""
    ys = np.linspace(0, 300, 60)
    half = 62.0 * np.exp(-ys / 100.0) + 2.0
    right = list(zip(half, ys)); left = list(zip(-half[::-1], ys[::-1]))
    outer = right + [(1.6, 300), (0.6, 330), (-0.6, 330), (-1.6, 300)] + left
    # platforms
    arch = [(a * 45.0 * math.cos(math.radians(th)), 0 + 42 * math.sin(math.radians(th)) * (1 if a else 1))
            for a, th in [(1, t) for t in np.linspace(0, 180, 25)]]
    arch = [(45 * math.cos(math.radians(t)), 40 * math.sin(math.radians(t))) for t in np.linspace(0, 180, 25)]
    arch = [(46, 0)] + arch + [(-46, 0)]
    return outer, arch


def esb():
    """Empire State Building side silhouette (simplified setbacks), metres, total 443 m to the antenna tip."""
    prof = [(0, 65), (25, 65), (25, 50), (90, 50), (90, 31), (305, 31), (305, 25), (320, 25), (320, 17),
            (373, 17), (373, 9), (381, 9), (381, 5), (418, 3), (420, 1.2), (443, 0.4)]
    right = [(w, y) for y, w in prof]
    left = [(-w, y) for y, w in prof[::-1]]
    return right + left


def boat(len_m=13.0):
    """Small fishing troller silhouette (metres, origin at waterline centre)."""
    L = len_m
    hull = [(-0.5 * L, 1.6), (0.42 * L, 1.9), (0.5 * L, 2.3), (0.46 * L, 0.0), (-0.47 * L, 0.1)]
    cabin = [(-0.15 * L, 1.7), (-0.15 * L, 4.3), (0.12 * L, 4.3), (0.17 * L, 1.8)]
    mast = [(0.02 * L, 4.2), (0.04 * L, 4.2), (0.04 * L, 10.5), (0.02 * L, 10.5)]
    poles = [(0.03 * L, 9.8), (-0.45 * L, 6.5), (-0.44 * L, 6.3), (0.03 * L, 9.4)]
    return [hull, cabin, mast, poles]
