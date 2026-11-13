"""Photoreal lit Moon for "What If the Moon Got Closer?" (linear HDR, numpy / cv2).
Copied from ../other-moons/moons.py (itself from ../planets-as-moon/planets.py), reduced to the rocky-body path and
extended with:
  - a configurable Sun direction (gibbous phase, ~36 deg phase angle, lit from the lower right: the Sun is below the
    horizon behind the camera at blue hour)
  - earthshine on the night side (scaled with closeness, Earth's light on the Moon goes as 1/d^2)
  - `patch()` returns the rendered radiance + coverage instead of compositing (the Roche-limit break-up cuts it into
    fragments)
The disc is a true 3-D sphere seen by an orthographic ray per pixel, 2x supersampled in its bounding box, then
box-filtered down. The Solar System Scope 8k Moon map (CC BY 4.0, from NASA LRO data) is pre-filtered to the on-screen
scale (one Body per apparent size, so the small discs do not alias). Lommel-Seeliger photometry (flat-looking Moon).
Geometry: camera x right, y down, z forward (away from the viewer).
"""
import math, os
import numpy as np, cv2
from PIL import Image
from lib.core import f32, srgb_to_lin, fbm2, smooth

TEX = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common/dl/sss"
SUN = np.array([0.55, 0.22, -0.80]); SUN = SUN / np.linalg.norm(SUN)        # towards the Sun (camera frame)
PHASE_DEG = math.degrees(math.acos(-SUN[2]))
_tex_cache = {}


def load_lin(name, size=None):
    k = (name, size)
    if k not in _tex_cache:
        im = Image.open(os.path.join(TEX, name)).convert("RGB")
        a = np.asarray(im, f32) / 255.0
        if size and size[0] < a.shape[1]: a = cv2.resize(a, size, interpolation=cv2.INTER_AREA)
        _tex_cache[k] = srgb_to_lin(a)
    return _tex_cache[k]


def frame_of(pole):
    """rows = body axes (X, Y=north pole, Z) in camera coordinates"""
    Y = np.asarray(pole, float); Y = Y / np.linalg.norm(Y)
    v = np.array([0.0, 0.0, -1.0])
    X = np.cross(Y, v); X = X / np.linalg.norm(X); Z = np.cross(X, Y)
    return np.stack([X, Y, Z])


def pole_vec(roll_deg, tip_deg):
    """north pole: 'up' on screen rotated by roll (clockwise +), tipped towards the viewer by tip"""
    r, b = math.radians(roll_deg), math.radians(tip_deg)
    return np.array([math.sin(r) * math.cos(b), -math.cos(r) * math.cos(b), -math.sin(b)])


class Moon:
    def __init__(self, Rp, pole=pole_vec(-12, 4), lon0=0.0, surf=1.0, ss=2, max_tex=8192, seed=1):
        self.Rp, self.lon0, self.surf, self.ss = Rp, lon0, surf, ss
        self.M = frame_of(pole)
        want = int(min(2 * math.pi * Rp * ss * 1.3, max_tex)); want = max(want, 256)
        t = load_lin("8k_moon.jpg", (want, want // 2))
        self.tex = (t / max(float(t.mean()), 1e-4)).astype(f32)

    def patch(self, cx, cy, t, I=1.0, scale=1.0, es=0.0, es_col=(0.70, 0.82, 1.0), W=None, H=None):
        """-> (x0, x1, y0, y1, rad HxWx3, cov HxW) of the disc centred at (cx, cy); clipped to the frame if W/H given"""
        R = self.Rp * scale
        if R < 0.2: return None
        pad = R * 1.02 + 4
        x0, x1 = int(math.floor(cx - pad)), int(math.ceil(cx + pad))
        y0, y1 = int(math.floor(cy - pad)), int(math.ceil(cy + pad))
        if W is not None: x0, x1, y0, y1 = max(0, x0), min(W, x1), max(0, y0), min(H, y1)
        if x1 <= x0 or y1 <= y0: return None
        ss = self.ss if R > 1.5 else 4
        ys, xs = np.mgrid[0:(y1 - y0) * ss, 0:(x1 - x0) * ss].astype(f32)
        u = ((xs + 0.5) / ss + x0 - cx) / R; w = ((ys + 0.5) / ss + y0 - cy) / R
        rr2 = u * u + w * w
        cov = np.clip((1 - np.sqrt(rr2)) * R * ss + 0.5, 0, 1).astype(f32)          # analytic limb anti-aliasing
        z = -np.sqrt(np.clip(1 - rr2, 0, 1))
        n_cam = np.stack([u, w, z], -1)                                          # outward normal (camera frame)
        M = self.M.astype(f32)
        n_ = n_cam @ M.T                                                         # body frame
        lat = np.arcsin(np.clip(n_[..., 1], -1, 1)); lon = np.arctan2(n_[..., 0], n_[..., 2]) + self.lon0
        th, tw_ = self.tex.shape[:2]
        mx = ((lon / (2 * np.pi) + 0.5) % 1.0 * tw_).astype(f32); my = np.clip((0.5 - lat / np.pi) * th - 0.5, 0, th - 1).astype(f32)
        alb = cv2.remap(self.tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        mu = np.clip(-z, 0.0, 1.0)
        mu0 = n_cam @ SUN.astype(f32)
        m0 = np.maximum(mu0, 0)
        f = 2 * m0 / (m0 + np.maximum(mu, 0.02)) * smooth(-0.02, 0.06, mu0)         # Lommel-Seeliger, soft terminator
        col = alb * f[..., None] * self.surf
        if es > 0:                                                               # earthshine on the night side
            night = 1 - smooth(-0.04, 0.04, mu0)
            col = col + alb * (es * night * (0.35 + 0.65 * mu))[..., None] * np.array(es_col, f32)
        rad = col * cov[..., None]
        if ss > 1:
            sz = (x1 - x0, y1 - y0)
            rad = cv2.resize(rad, sz, interpolation=cv2.INTER_AREA); cov = cv2.resize(cov, sz, interpolation=cv2.INTER_AREA)
        return x0, x1, y0, y1, (rad * I).astype(f32), cov.astype(f32)

    def render(self, img, cx, cy, t, I=1.0, scale=1.0, es=0.0, ext=None):
        H, W = img.shape[:2]
        p = self.patch(cx, cy, t, I, scale, es, W=W, H=H)
        if p is None: return None
        x0, x1, y0, y1, rad, cov = p
        if ext is not None: rad = rad * ext[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - cov[..., None]) + rad
        return p


def night_mask(u, w):
    """for a disc point (u, w) in units of R (y down): > 0 on the night side"""
    z = -math.sqrt(max(1 - u * u - w * w, 0))
    return -(u * SUN[0] + w * SUN[1] + z * SUN[2])
