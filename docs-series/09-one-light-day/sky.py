"""Procedural deep-space sky: a structured Milky Way panorama (galactic equirect, built once with numpy FFT noise)
plus a star catalogue with a realistic magnitude distribution and blackbody colours. Rendered per frame through an
arbitrary camera rotation, so plates rendered in Blender (cam.json) get a consistent background."""
import os, math
import numpy as np
from lib import W, H, TEX, Acc, bilinear_wrap, blur

GAL_N = np.array([0.45, 0.35, 0.82]); GAL_N /= np.linalg.norm(GAL_N)        # galactic pole in world coords (as in voyager.py)
_c = np.cross(GAL_N, [0.0, 1.0, 0.0]); _c /= np.linalg.norm(_c)              # direction of the galactic centre (arbitrary)
G = np.stack([_c, np.cross(GAL_N, _c), GAL_N], 1)                            # columns: gal x (centre), y, z (pole) in world
MW_PATH = os.path.join(TEX, "milkyway.npy")
ST_PATH = os.path.join(TEX, "stars.npz")


def _noise(shape, beta, seed, aniso=1.0, kmin=1.5):
    h, w = shape
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None] * h * aniso; fx = np.fft.rfftfreq(w)[None, :] * w
    k = np.sqrt(fx * fx + fy * fy)
    amp = np.where(k < kmin, 0, (k + 1e-6) ** (-beta / 2))
    out = np.fft.irfft2(np.fft.rfft2(r.standard_normal((h, w)).astype(np.float32)) * amp, s=(h, w)).astype(np.float32)
    return (out - out.mean()) / out.std()


def make_milkyway(Nw=6144):
    Nh = Nw // 2
    l = (np.arange(Nw, dtype=np.float32) + 0.5) / Nw * 360 - 180          # galactic longitude, centre at 0
    b = 90 - (np.arange(Nh, dtype=np.float32) + 0.5) / Nh * 180
    L, B = np.meshgrid(l, b)
    n1 = _noise((Nh, Nw), 2.6, 1); n2 = _noise((Nh, Nw), 2.0, 2, aniso=2.2); n3 = _noise((Nh, Nw), 1.4, 3)
    n4 = _noise((Nh, Nw), 2.9, 4, aniso=2.8); n5 = _noise((Nh, Nw), 2.2, 5, aniso=1.6)
    warp = 2.5 * n1                                                         # degrees of latitude warp -> wavy band
    Bw = B + warp * np.exp(-(B / 30) ** 2)
    hgt = 4.5 + 5.5 * np.exp(-(L / 45) ** 2)
    Aint = 0.30 + 0.70 * np.exp(-(L / 70) ** 2) + 0.12 * np.exp(-((np.abs(L) - 180) / 40) ** 2)
    disk = Aint / np.cosh(Bw / hgt) ** 2 + 0.25 * Aint * np.exp(-np.abs(Bw) / 18)
    bulge = 1.6 * np.exp(-((L / 13) ** 2 + (Bw / 8.5) ** 2) ** 0.8)
    clouds = np.exp(0.55 * n2 + 0.25 * n3)                                 # patchy star clouds
    star = (disk * clouds + bulge * (0.8 + 0.2 * clouds)) ** 1.35
    # dust: ridged, filamentary, hugging the plane (the Great Rift), reddening what it covers
    ridg = 1 - np.abs(n4); ridg2 = 1 - np.abs(n5)
    tau = np.clip(ridg * 1.3 + 0.6 * ridg2 + 0.35 * n3 - 1.05, 0, None) * 8.0
    tau *= np.exp(-(Bw / 5.5) ** 2) * (0.55 + 0.45 * np.exp(-(L / 80) ** 2)) + 0.35 * np.exp(-((Bw - 6 - 0.04 * L) / 3.0) ** 2) * (np.abs(L) < 70)
    tau = blur(tau, 1.5)
    warm = np.exp(-(L / 50) ** 2) * np.exp(-(Bw / 14) ** 2)
    col = (1 - warm)[..., None] * np.array([0.72, 0.84, 1.10], np.float32) + warm[..., None] * np.array([1.18, 0.95, 0.66], np.float32)
    img = star[..., None] * col * np.exp(-tau[..., None] * np.array([0.88, 1.0, 1.2], np.float32))
    # unresolved-star grain
    g = np.random.default_rng(9).standard_normal((Nh, Nw)).astype(np.float32)
    img *= (1 + 0.08 * blur(g, 1.2) * 2.5)[..., None].clip(0.5, 2.0)
    # a few emission nebulae (pink) and blue reflection patches near the plane
    r = np.random.default_rng(12)
    for k in range(26):
        l0 = r.uniform(-180, 180); b0 = r.normal(0, 3.0); s0 = r.uniform(0.6, 2.2)
        d2 = (((L - l0 + 180) % 360 - 180) ** 2 + (B - b0) ** 2) / (s0 * s0)
        blob = np.exp(-d2) * np.clip(0.6 + 0.6 * n3, 0, 2) * r.uniform(0.05, 0.22)
        img += blob[..., None] * (np.array([1.0, 0.28, 0.42], np.float32) if r.random() < 0.7 else np.array([0.35, 0.5, 1.0], np.float32))
    # two faint satellite-galaxy smudges and a very faint isotropic floor
    for (l0, b0, s0, a0) in ((-80, -33, 3.0, 0.10), (-58, -44, 1.6, 0.07), (121, -21.5, 1.2, 0.05)):
        d2 = (((L - l0 + 180) % 360 - 180) ** 2 * math.cos(math.radians(b0)) ** 2 + (B - b0) ** 2) / (s0 * s0)
        img += (a0 * np.exp(-d2 ** 0.8) * (0.8 + 0.3 * n3))[..., None] * np.array([0.85, 0.9, 1.0], np.float32)
    img = np.maximum(img, 0) + 0.0015
    np.save(MW_PATH, img.astype(np.float16))
    return img


def make_stars(n=1000000, seed=21):
    r = np.random.default_rng(seed)
    nd = int(n * 0.72)
    # disk population: concentrated to the plane and (mildly) to the centre; halo population: isotropic
    bb = np.radians(np.clip(r.laplace(0, 7.5, nd) + 2.0 * np.sin(np.arange(nd) * 0.37), -89, 89))
    ll = np.radians(np.where(r.random(nd) < 0.45, r.normal(0, 55, nd), r.uniform(-180, 180, nd)))
    z = r.uniform(-1, 1, n - nd); ph = r.uniform(0, 2 * np.pi, n - nd)
    d = np.concatenate([np.stack([np.cos(bb) * np.cos(ll), np.cos(bb) * np.sin(ll), np.sin(bb)], 1),
                        np.stack([np.sqrt(1 - z * z) * np.cos(ph), np.sqrt(1 - z * z) * np.sin(ph), z], 1)])
    # magnitudes: N(<m) ~ 10^(0.48 m), from about -1 to 9.5
    lo, hi = 10 ** (0.48 * -1.2), 10 ** (0.48 * 11.3)
    m = np.log10(lo + r.random(n) * (hi - lo)) / 0.48
    flux = 10 ** (-0.4 * m)
    # colours from a temperature distribution (K, M, G, F, A, B ...)
    T = np.clip(np.exp(r.normal(math.log(5600), 0.33, n)), 2800, 26000)
    x = T / 100.0
    rr = np.where(x <= 66, 1.0, np.clip(1.2929 * (x - 60) ** -0.1332, 0, 1))
    gg = np.where(x <= 66, np.clip(0.3901 * np.log(x) - 0.6318, 0, 1), np.clip(1.1299 * (x - 60) ** -0.0755, 0, 1))
    bl = np.where(x >= 66, 1.0, np.clip(0.5432 * np.log(np.maximum(x - 10, 1.0)) - 1.1963, 0, 1))
    col = np.stack([rr, gg, bl], 1) ** 1.6
    col /= col.mean(1, keepdims=True)
    np.savez(ST_PATH, d=d.astype(np.float32), flux=flux.astype(np.float32), col=col.astype(np.float32))


class Sky:
    def __init__(self):
        if not os.path.exists(MW_PATH): make_milkyway()
        if not os.path.exists(ST_PATH): make_stars()
        self.mw = np.load(MW_PATH).astype(np.float32)
        s = np.load(ST_PATH); self.d = s["d"] @ G.T.astype(np.float32)       # star directions in world coords
        self.flux = s["flux"]; self.col = s["col"]
        hh, ww = H // 2, W // 2
        self.px = (np.arange(ww, dtype=np.float32) + 0.5 - ww / 2)[None, :] * 2
        self.py = (np.arange(hh, dtype=np.float32) + 0.5 - hh / 2)[:, None] * 2
        k = np.zeros((21, 21), np.float32)
        for i in range(21):
            a = math.exp(-abs(i - 10) / 2.4); k[10, i] = max(k[10, i], a); k[i, 10] = max(k[i, 10], a)
        self.spike = k

    def render(self, R, fov_deg, mw_gain=1.0, star_gain=1.0, size=None):
        """R: 3x3 camera-to-world (columns = camera right, up, back; the camera looks along -Z). Returns linear RGB."""
        global W, H
        W0, H0 = W, H
        if size is not None: W, H = size
        try:
            return self._render(R, fov_deg, mw_gain, star_gain)
        finally:
            W, H = W0, H0

    def _render(self, R, fov_deg, mw_gain, star_gain):
        R = np.asarray(R, np.float32); f = (W / 2) / math.tan(math.radians(fov_deg) / 2)
        # Milky Way at half resolution
        hh, ww = H // 2, W // 2
        px = (np.arange(ww, dtype=np.float32) + 0.5 - ww / 2)[None, :] * 2; py = (np.arange(hh, dtype=np.float32) + 0.5 - hh / 2)[:, None] * 2
        dx = px; dy = -py; dz = -f
        wx = R[0, 0] * dx + R[0, 1] * dy + R[0, 2] * dz; wy = R[1, 0] * dx + R[1, 1] * dy + R[1, 2] * dz
        wz = R[2, 0] * dx + R[2, 1] * dy + R[2, 2] * dz
        gx = G[0, 0] * wx + G[1, 0] * wy + G[2, 0] * wz; gy = G[0, 1] * wx + G[1, 1] * wy + G[2, 1] * wz
        gz = G[0, 2] * wx + G[1, 2] * wy + G[2, 2] * wz
        nrm = np.sqrt(gx * gx + gy * gy + gz * gz)
        lon = np.arctan2(gy, gx); lat = np.arcsin(np.clip(gz / nrm, -1, 1))
        mh, mwd = self.mw.shape[:2]
        tx = (lon / (2 * np.pi) + 0.5) * mwd - 0.5; ty = (0.5 - lat / np.pi) * mh - 0.5
        ty = np.clip(ty, 0, mh - 1.001)
        half = bilinear_wrap(self.mw, tx, ty) * (0.075 * mw_gain)
        from PIL import Image
        lin = np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(half[..., c], np.float32), "F").resize((W, H), Image.BICUBIC)) for c in range(3)], -1)
        lin = np.maximum(lin, 0)
        # stars
        dc = self.d @ R                                                       # world -> camera (R^T applied to rows)
        vis = dc[:, 2] < -0.2
        sx = W / 2 + f * dc[vis, 0] / (-dc[vis, 2]); sy = H / 2 - f * dc[vis, 1] / (-dc[vis, 2])
        ok = (sx > -2) & (sx < W + 2) & (sy > -2) & (sy < H + 2)
        sx, sy = sx[ok], sy[ok]; fl = self.flux[vis][ok] * (150.0 * star_gain) * (f / 2000.0) ** 0.6; cl = self.col[vis][ok]
        acc = Acc(W, H)
        acc.add(sx, sy, fl, cl)
        big = fl > 1.5
        if big.any():                                                         # soft halo + tiny spikes for the brightest
            for ox, oy, wgt in ((-1, 0, .22), (1, 0, .22), (0, -1, .22), (0, 1, .22), (-2, 0, .06), (2, 0, .06), (0, -2, .06), (0, 2, .06),
                                (-1, -1, .1), (1, 1, .1), (-1, 1, .1), (1, -1, .1)):
                acc.add(sx[big] + ox, sy[big] + oy, fl[big] * wgt, cl[big])
        vb = fl > 12.0
        if vb.any():
            for k in range(3, 12):
                wgt = 0.05 * math.exp(-k / 3.5)
                for ox, oy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                    acc.add(sx[vb] + ox, sy[vb] + oy, fl[vb] * wgt, cl[vb])
        lin += acc.image()
        return lin


def look_R(az_deg, el_deg, roll_deg=0.0):
    """camera-to-world rotation looking towards (az, el) in world coords (z up)"""
    az, el, ro = math.radians(az_deg), math.radians(el_deg), math.radians(roll_deg)
    fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    up0 = np.array([0, 0, 1.0]); right = np.cross(fwd, up0); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    r2 = right * math.cos(ro) + up * math.sin(ro); u2 = -right * math.sin(ro) + up * math.cos(ro)
    return np.stack([r2, u2, -fwd], 1)


def yaw_pitch(R, yaw_deg, pitch_deg):
    """rotate camera about its own up / right axes"""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rp = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    return np.asarray(R) @ Ry @ Rp


def gal_dir(l_deg, b_deg):
    l, b = math.radians(l_deg), math.radians(b_deg)
    return G @ np.array([math.cos(b) * math.cos(l), math.cos(b) * math.sin(l), math.sin(b)])


def look_at_dir(d, roll_deg=0.0):
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    return look_R(math.degrees(math.atan2(d[1], d[0])), math.degrees(math.asin(d[2])), roll_deg)


if __name__ == "__main__":
    import time
    from lib import bloom, tonemap, to8, SCR
    from PIL import Image
    t0 = time.time(); s = Sky(); print("init", time.time() - t0)
    for i, (l, b, fov) in enumerate(((0, 5, 60), (40, 12, 45), (150, 30, 50), (-90, -50, 50))):
        t0 = time.time(); lin = s.render(look_at_dir(gal_dir(l, b), 20), fov); print("render", time.time() - t0)
        Image.fromarray(to8(tonemap(bloom(lin, 0.5, 12), 1.0))).save(os.path.join(SCR, "chk", f"sky_{i}.png"))
