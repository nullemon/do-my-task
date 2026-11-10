"""Storm aurora for a locked ground camera (linear HDR, numpy/cv2).

Geometry (physically inspired): auroral curtains are thin sheets that follow the geomagnetic field. Each sheet is a
folded curve at ~100 km altitude (the lower border) extruded upward along the field direction B for a few hundred km.
Seen from the ground, all field-aligned rays are parallel lines in 3-D, so in the image they converge on ONE vanishing
point V (the magnetic zenith): curtains passing overhead turn into a corona, rays radiating from V.

Emission along the field line (height h above the lower border):
  green 557.7 nm  O(1S)   sharp lower edge, bright, decays upward
  red   630.0 nm  O(1D)   high (≈ 200–400 km), broad: dominant in great storms (1859 was described as blood red)
  magenta fringe  N2 / N2+ just below the green edge in strong storms (fast electrons penetrate deeper)

Rendering trick: the image is resampled from a polar canvas centred on V (columns = angle, rows = distance from V),
because every ray is a radial line there. Sample points (curtain parameter s × height h) are projected with the camera,
splatted into the polar canvas with np.bincount, blurred along the rays, and remapped to the screen once per frame.
Overlapping folds and rays seen end-on brighten naturally (more emitting path along the line of sight).
"""
import math
import numpy as np, cv2
from lib.core import f32, fbm2, noise1, smooth

G_COL = np.array([0.10, 1.00, 0.30], f32)        # 557.7 nm (linear RGB, saturated)
R_COL = np.array([1.00, 0.035, 0.11], f32)       # 630 nm crimson
M_COL = np.array([0.95, 0.12, 0.85], f32)        # N2 magenta lower fringe


class Aurora:
    def __init__(self, W, H, hz, f, V, seed=11, NT=4096, NR=1024):
        self.W, self.H, self.hz, self.f = W, H, hz, f
        self.cx = W / 2.0
        self.V = V
        b = np.array([(V[0] - self.cx) / f, (hz - V[1]) / f, 1.0]); self.B = b / np.linalg.norm(b)
        self.NT, self.NR = NT, NR
        self.RMAX = math.hypot(max(V[0], W - V[0]), max(V[1], H - V[1])) * 1.02
        yy, xx = np.mgrid[0:H, 0:W].astype(f32)
        dx, dy = xx + 0.5 - V[0], yy + 0.5 - V[1]
        self.map_t = ((np.arctan2(dy, dx) % (2 * np.pi)) / (2 * np.pi) * NT).astype(f32)
        self.rpx = np.sqrt(dx * dx + dy * dy).astype(f32)
        self.map_r = (self.rpx / self.RMAX * NR).astype(f32)
        self.el = np.clip((hz - yy) / hz, 0, 1).astype(f32)
        r = np.random.default_rng(seed)
        self.tex = np.stack([fbm2((4, 8192), seed + k, 1.1)[0] for k in range(4)])          # 1-D ray textures
        self.tex = (self.tex - self.tex.min(1, keepdims=True)) / np.ptp(self.tex, 1, keepdims=True)
        # crown rays (angle) texture
        self.ctex = fbm2((2, NT), seed + 9, 1.5)[0]; self.ctex = (self.ctex - self.ctex.min()) / np.ptp(self.ctex)
        # curtains: final lower-border distance Z (km, forward), lateral half span, folds
        Zs = [38, 62, 92, 125, 175, 260, 400, 650]
        self.cur = []
        for k, Z in enumerate(Zs):
            span = Z * (0.5 * W / f) * 1.9 + 160
            self.cur.append(dict(Z=Z, span=span, ns=2600 if Z < 200 else 1800,
                                 A1=r.uniform(0.10, 0.22) * Z + 6, m1=r.uniform(0.6, 1.4), w1=r.uniform(0.15, 0.35) * r.choice([-1, 1]), p1=r.uniform(0, 6.3),
                                 A2=r.uniform(0.04, 0.08) * Z + 2, m2=r.uniform(2.5, 4.5), w2=r.uniform(0.9, 1.6) * r.choice([-1, 1]), p2=r.uniform(0, 6.3),
                                 F=r.uniform(0.08, 0.13) * span, n3=r.uniform(2.0, 3.5), w3=r.uniform(0.3, 0.7) * r.choice([-1, 1]), p3=r.uniform(0, 6.3),
                                 drift=r.uniform(-1.0, 1.0), off=r.uniform(0, 8192), I=r.uniform(0.8, 1.15) * (0.28 if Z < 80 else (1.35 if Z < 300 else 1.0)), tk=k % 4,
                                 hred=r.uniform(210, 270)))
        u = np.linspace(0, 1, 104, dtype=f32)
        self.h = (-14 + 420 * u ** 1.7).astype(f32)                                           # km above lower border
        self.dh = np.gradient(self.h).astype(f32)

    # ------------------------------------------------------------------------------------------------
    def _curtain(self, c, t, prog, acc, storm):
        NT, NR = self.NT, self.NR
        ns = c["ns"]
        s = np.linspace(-1, 1, ns, dtype=f32)
        Z0 = c["Z"] * math.exp((1 - prog) * 2.6)                         # oval expands from the horizon to overhead
        X = c["span"] * s + c["F"] * np.sin(2 * np.pi * c["n3"] * s + c["w3"] * t + c["p3"])
        Z = (Z0 + c["A1"] * np.sin(2 * np.pi * c["m1"] * s + c["w1"] * t + c["p1"]) * (Z0 / c["Z"]) ** 0.3
             + c["A2"] * np.sin(2 * np.pi * c["m2"] * s + c["w2"] * t + c["p2"]))
        Yb = 100.0 + 5.0 * np.sin(7.0 * s + 0.8 * t + c["p2"])
        # ray structure along the curtain: drifting fine rays * fast flicker * travelling surges
        tx = self.tex[c["tk"]]
        i1 = ((s * 1500 + c["off"] + c["drift"] * t * 90.0) % 8192).astype(np.int32)
        i2 = ((s * 700 + c["off"] * 0.5 - t * 260.0 * (1 if c["drift"] > 0 else -1)) % 8192).astype(np.int32)
        rays = (0.40 + 0.9 * tx[i1] ** 2.0) * (0.55 + 0.65 * tx[(i2 + 1000) % 8192])
        surge = 1 + 1.3 * np.exp(-(((s - (((t * 0.45 + c["p1"]) % 2.6) - 1.3)) / 0.10) ** 2))
        A = rays * surge * c["I"]
        # sample grid (s x h)
        h = self.h[None, :]
        Bx, By, Bz = self.B
        Px = X[:, None] + h * Bx; Py = Yb[:, None] + h * By; Pz = Z[:, None] + h * Bz
        ok = Pz > 2.0
        Pz = np.where(ok, Pz, 2.0)
        sx = self.cx + self.f * Px / Pz; sy = self.hz - self.f * Py / Pz
        dx, dy = sx - self.V[0], sy - self.V[1]
        rr = np.sqrt(dx * dx + dy * dy) / self.RMAX * NR
        th = (np.arctan2(dy, dx) % (2 * np.pi)) / (2 * np.pi) * NT
        # visible part of the curtain: below the horizon line it is hidden by the Earth / buildings anyway
        ok &= (rr < NR - 2) & (sy < self.hz + 40)
        # projected sample spacing (px): partial compensation, keeps end-on brightening but not runaway
        dr = np.abs(np.gradient(rr, axis=1)) * self.RMAX / NR
        dthpx = np.abs(np.gradient(np.unwrap(th / NT * 2 * np.pi, axis=0), axis=0)) * np.maximum(rr * self.RMAX / NR, 1.0)
        w = np.clip(dr, 0.25, 10) ** 0.75 * np.clip(dthpx, 0.25, 10) ** 0.55
        # emission profiles along the field line
        hh = self.h[None, :] + 0 * Yb[:, None]
        flame = 1 + 0.45 * np.sin(2 * np.pi * (hh / 70.0 - 1.6 * t) + s[:, None] * 9 + c["p1"])   # upward-running pulses
        g = smooth(-3.0, 3.5, hh) * (np.exp(-np.maximum(hh, 0) / 42.0) * flame + 0.9 * np.exp(-(np.maximum(hh, 0) / 7.0) ** 2))
        red = np.exp(-((hh - c["hred"]) / 100.0) ** 2) * 0.22 * smooth(60, 140, hh)
        mag = np.exp(-((hh + 3.0) / 6.0) ** 2) * smooth(-14, -8, hh) * storm
        base = (A[:, None] * w * ok).astype(f32)
        ir = np.clip(rr, 0, NR - 2); i0 = ir.astype(np.int32); fr = (ir - i0).astype(f32)
        it = th.astype(np.int32) % NT
        idx0 = (i0 * NT + it).ravel(); idx1 = idx0 + NT
        for k, e in enumerate((g, red, mag)):
            v = (base * e).ravel(); ff = fr.ravel()
            acc[k] += np.bincount(idx0, v * (1 - ff), minlength=NR * NT)[:NR * NT].reshape(NR, NT)
            acc[k] += np.bincount(idx1, v * ff, minlength=NR * NT)[:NR * NT].reshape(NR, NT)

    def _crown(self, t, acc, crown):
        """corona: rays radiating from the magnetic zenith (end-on view of the overhead curtains)"""
        NT, NR = self.NT, self.NR
        th = np.arange(NT, dtype=f32)
        a = self.ctex[((th * 1.0 + t * 26.0) % NT).astype(np.int32)]
        b = self.ctex[((th * 3.0 - t * 61.0 + 1500) % NT).astype(np.int32)]
        fl = self.ctex[((th * 0.5 + t * 140.0 + 700) % NT).astype(np.int32)]
        rays = (a ** 3 * 1.2 + b ** 4 * 0.9) * (0.5 + 0.8 * fl)
        rpx = (np.arange(NR, dtype=f32) + 0.5) * self.RMAX / NR
        sc = self.H / 1920.0 if self.H > self.W else self.H / 1080.0 * 0.8
        breathe = 1 + 0.12 * math.sin(t * 2.1)
        rg = 330 * sc * breathe
        gpro = smooth(30 * sc, 150 * sc, rpx) * np.exp(-np.maximum(rpx - rg, 0) / (260 * sc)) * smooth(rg * 2.8, rg * 1.2, rpx)
        rpro = np.exp(-rpx / (210 * sc)) * smooth(0, 60 * sc, rpx)
        mpro = np.exp(-((rpx - rg * 1.45) / (90 * sc)) ** 2)
        acc[0] += (gpro[:, None] * rays[None, :]) * 1.6 * crown
        acc[1] += (rpro[:, None] * (0.25 + rays[None, :])) * 1.1 * crown
        acc[2] += (mpro[:, None] * rays[None, :] ** 2) * 1.2 * crown

    def polar_blur(self, a, sig_px):
        """blur along the angle with a width that is constant in SCREEN pixels: rays stay soft near the zenith point
        instead of collapsing into hairline spokes (box filter x3 ~ Gaussian; wrap-around in angle)"""
        NT, NR = self.NT, self.NR
        out = np.empty_like(a)
        edges = np.unique(np.concatenate([[0], np.geomspace(4, NR, 14).astype(int)]))
        for i0, i1 in zip(edges[:-1], edges[1:]):
            m = 4; j0, j1 = max(0, i0 - m), min(NR, i1 + m)
            rc = (0.5 * (i0 + i1) + 0.5) * self.RMAX / NR
            sb = float(np.clip(sig_px * NT / (2 * np.pi * max(rc, 3.0)), 0.6, NT / 6))
            k = int(round(math.sqrt(4 * sb * sb + 1))) | 1
            if k <= 1: out[i0:i1] = a[i0:i1]; continue
            pad = 2 * k
            sub = np.concatenate([a[j0:j1, -pad:], a[j0:j1], a[j0:j1, :pad]], 1)
            for _ in range(3): sub = cv2.blur(sub, (k, 1), borderType=cv2.BORDER_REPLICATE)
            out[i0:i1] = sub[i0 - j0:i1 - j0, pad:pad + NT]
        return out

    def render(self, t, level, prog=1.0, storm=1.0, crown=1.0):
        """-> linear HDR (H, W, 3) aurora light, and its mean colour over the sky (for tinting the city)"""
        W, H = self.W, self.H
        if level <= 1e-3: return np.zeros((H, W, 3), f32), np.zeros(3, f32)
        acc = [np.zeros((self.NR, self.NT), np.float64) for _ in range(3)]
        for c in self.cur: self._curtain(c, t, prog, acc, storm)
        if crown > 0: self._crown(t, acc, 0.45 * crown * prog ** 3)
        out = np.zeros((H, W, 3), f32); tint = np.zeros(3, f32)
        for k, col in enumerate((G_COL, R_COL, M_COL)):
            a = acc[k].astype(f32)
            a = self.polar_blur(a, (2.2, 16.0, 3.0)[k])
            a = cv2.GaussianBlur(a, (0, 0), sigmaX=0.6, sigmaY=2.4) + cv2.GaussianBlur(a, (0, 0), sigmaX=4, sigmaY=16) * 0.35
            img = cv2.remap(a, self.map_t, self.map_r, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
            out += img[..., None] * col
            tint += float(img[: int(self.hz)].mean()) * col
        out *= 0.12 * level
        # diffuse storm glow: blood-red dome overhead, green band low, flickering
        fl = 1 + 0.18 * noise1(t, 5, 3.0, 2)
        redwash = (np.exp(-self.rpx / (0.55 * H)) * 0.55 + self.el * 0.35)[..., None] * R_COL * 0.020
        grn = np.exp(-((self.el - 0.10) / 0.10) ** 2)[..., None] * G_COL * 0.012 * prog
        out += (redwash * prog + grn) * level * fl
        y = out @ np.array([0.2126, 0.7152, 0.0722], f32)
        out = np.maximum(y[..., None] + (out - y[..., None]) * 1.35, 0)
        # light cast on the ground: the emission-weighted, fully saturated line colours (+ the diffuse glow)
        tint = tint * 0.12 * level + (R_COL * 0.020 * 0.5 * prog + G_COL * 0.012 * 0.3 * prog) * level
        return out, tint.astype(f32)
