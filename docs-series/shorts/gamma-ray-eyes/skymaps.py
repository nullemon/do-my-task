"""All-sky textures and the sky geometry for the locked park shot.
 - Maps: galactic plate carree textures from prep_maps.py (Haslam 408 MHz, Planck 857 / 100 GHz, Fermi-LAT 3FHL),
   stretched to 0..1 display values once.
 - SkyGeo: pinhole camera that matches lib.sky.SkyCam (level camera, horizon row hz, focal f px, facing azimuth az0);
   per frame the local-horizon -> galactic matrix from ephem.npz gives (l, b) for every sky pixel (half res).
 - Palettes: piecewise-linear LUTs in linear light (values > 1 are HDR and feed the bloom).
"""
import os, math
import numpy as np, cv2
from lib.core import f32
from scipy.ndimage import gaussian_filter

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S3-gamma-ray-eyes"


def _stretch(x, lo_p, hi_p):
    lo, hi = np.percentile(x, lo_p), np.percentile(x, hi_p)
    return np.clip((x - lo) / (hi - lo), 0, 1.25).astype(f32)


class Maps:
    def __init__(self):
        cache = os.path.join(SCR, "maps_disp.npz")
        if os.path.exists(cache):
            d = np.load(cache); self.__dict__.update({k: d[k] for k in d.files}); return
        d = np.load(os.path.join(SCR, "maps.npz"))
        self.radio = _stretch(np.log(d["radio"]), 1, 99.97)
        self.ir = _stretch(np.log(np.maximum(d["ir"], 0.3)), 3, 99.9)
        m = d["micro"]; med = np.median(m)
        self.cmb = np.tanh((np.clip(m - med, -2000, 2000)) / 210.0).astype(f32)            # anisotropy, -1..1
        gal = np.log1p(np.maximum(m - med - 260.0, 0) / 220.0)
        self.cmbgal = np.clip(gaussian_filter(gal, 1.2, mode="wrap") / np.percentile(gal, 99.9), 0, 1.3).astype(f32)
        c = d["gamma"].astype(np.float64)
        raw = c * 1.0
        gs = gaussian_filter(raw, 9.0, mode="wrap"); gf = gaussian_filter(raw, 1.4, mode="wrap")
        w = np.clip((gs - 0.35) / 1.4, 0, 1)                                               # sharp where photons are plentiful
        gam = gs * (1 - w) + np.maximum(gf, gs) * w
        self.gamma = _stretch(np.log(gam + 0.08), 2, 99.95)
        self.blz = d["blz"]
        np.savez(cache, radio=self.radio, ir=self.ir, cmb=self.cmb, cmbgal=self.cmbgal, gamma=self.gamma, blz=self.blz)


def lut(stops, n=1024):
    xs = np.array([s[0] for s in stops]); cs = np.array([s[1] for s in stops], np.float64)
    x = np.linspace(0, 1, n)
    return np.stack([np.interp(x, xs, cs[:, k]) for k in range(3)], 1).astype(f32)


def apply_lut(L, x):
    n = len(L)
    return L[np.clip((x * (n - 1)).astype(np.int32), 0, n - 1)]


PAL = {
    "radio": lut([(0.0, (0.012, 0.018, 0.090)), (0.22, (0.020, 0.070, 0.330)), (0.42, (0.000, 0.300, 0.620)),
                  (0.58, (0.030, 0.720, 0.560)), (0.72, (0.750, 0.900, 0.080)), (0.86, (1.900, 0.750, 0.060)),
                  (1.00, (5.000, 3.600, 2.300))]),
    "ir": lut([(0.0, (0.070, 0.012, 0.110)), (0.30, (0.300, 0.030, 0.260)), (0.52, (0.800, 0.070, 0.180)),
               (0.70, (1.500, 0.420, 0.060)), (0.86, (2.300, 1.400, 0.300)), (1.00, (5.000, 4.200, 3.000))]),
    "cmb": lut([(0.0, (0.010, 0.040, 0.500)), (0.28, (0.040, 0.330, 0.950)), (0.50, (1.000, 0.880, 0.620)),
                (0.72, (1.700, 0.520, 0.080)), (1.00, (1.900, 0.120, 0.030))]),
    "gamma": lut([(0.0, (0.030, 0.010, 0.085)), (0.30, (0.090, 0.025, 0.280)), (0.52, (0.320, 0.060, 0.700)),
                  (0.72, (1.000, 0.230, 1.300)), (0.88, (2.200, 1.100, 2.700)), (1.00, (5.500, 4.600, 6.000))]),
}


class SkyGeo:
    """camera rays at half resolution (ENU) and per-frame galactic lookup"""
    def __init__(self, W, H, hz, f, az0, eph):
        self.W, self.H, self.hz, self.f = W, H, hz, f
        a = math.radians(az0)
        self.fw = np.array([math.sin(a), math.cos(a), 0.0]); self.rt = np.array([math.cos(a), -math.sin(a), 0.0]); self.up = np.array([0, 0, 1.0])
        h, w = H // 2, W // 2
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64) * 2 + 0.5
        X = (xx - W / 2) / f; Z = (hz - yy) / f
        v = self.rt[None, None] * X[..., None] + self.fw[None, None] + self.up[None, None] * Z[..., None]
        self.v = (v / np.linalg.norm(v, axis=2, keepdims=True)).astype(f32)
        self.el = np.arcsin(np.clip(self.v[..., 2], -1, 1)).astype(f32)
        self.eph = eph; self.fps = float(eph["fps"])

    def at(self, t):
        """(M, sun, moon) interpolated at film time t"""
        x = t * self.fps; i = int(min(max(math.floor(x), 0), len(self.eph["M"]) - 2)); u = x - i
        M = self.eph["M"][i] * (1 - u) + self.eph["M"][i + 1] * u
        U, _, Vt = np.linalg.svd(M); M = U @ Vt
        def nv(k):
            v = self.eph[k][i] * (1 - u) + self.eph[k][i + 1] * u; return v / np.linalg.norm(v)
        return M, nv("sun"), nv("moon")

    def lookup(self, M):
        """texture coordinates (2048 x 1024 plate carree, galactic) for every half-res pixel"""
        g = self.v @ M.T.astype(f32)
        l = np.arctan2(g[..., 1], g[..., 0]); b = np.arcsin(np.clip(g[..., 2], -1, 1))
        mx = ((l / (2 * np.pi)) % 1.0 * 2048).astype(f32)
        my = ((0.5 - b / np.pi) * 1024 - 0.5).astype(f32)
        return mx, my

    @staticmethod
    def sample(tex, mx, my):
        return cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def project(self, v):
        """ENU unit vector -> full-res pixel (x, y), or None behind the camera"""
        z = float(v @ self.fw)
        if z <= 0.05: return None
        return self.W / 2 + self.f * float(v @ self.rt) / z, self.hz - self.f * float(v[2]) / z

    def gal_to_enu(self, M, l_deg, b_deg):
        l, b = np.radians(l_deg), np.radians(b_deg)
        g = np.stack([np.cos(b) * np.cos(l), np.cos(b) * np.sin(l), np.sin(b)], -1)
        return g @ M                                                   # M orthonormal: enu = M^T g

    def project_many(self, enu):
        z = enu @ self.fw
        x = self.W / 2 + self.f * (enu @ self.rt) / np.maximum(z, 1e-3)
        y = self.hz - self.f * enu[:, 2] / np.maximum(z, 1e-3)
        return x, y, z > 0.05
