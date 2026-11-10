"""Shared basics for the vertical Shorts pipeline (numpy / cv2, linear-light HDR float32).
Run everything with /home/user/ttsenv/bin/python (numpy, scipy, soundfile, kokoro); cv2 + PIL come from COMMON/pylib.
"""
import os, sys, math
COMMON = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/shorts-common"
sys.path.insert(0, os.path.join(COMMON, "pylib"))
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np, cv2
cv2.setNumThreads(2)
f32 = np.float32
LIB = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(COMMON, "cache"); os.makedirs(CACHE, exist_ok=True)


def srgb_to_lin(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(f32)


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(f32)


def lum(x): return (x @ np.array([0.2126, 0.7152, 0.0722], f32)).astype(f32)
def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def ease(t): t = min(max(t, 0.0), 1.0); return t * t * (3 - 2 * t)
def ramp(t, a, b): return ease((t - a) / (b - a)) if b != a else float(t >= a)


def kf(t, keys):
    """piecewise smoothstep keyframes [(t, v), ...]; v scalar or tuple"""
    if t <= keys[0][0]: return keys[0][1]
    if t >= keys[-1][0]: return keys[-1][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u


def fbm2(shape, seed, beta=2.0, lo=0.0):
    """periodic spectral noise, mean 0 std 1"""
    h, w = shape; r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(h)[:, None] * h; fx = np.fft.rfftfreq(w)[None, :] * w
    f = np.sqrt(fx * fx + fy * fy); f[0, 0] = 1
    amp = f ** (-beta / 2.0); amp[0, 0] = 0
    if lo: amp[f < lo] = 0
    z = np.fft.irfft2(amp * np.exp(1j * r.uniform(0, 2 * np.pi, amp.shape)), s=(h, w))
    return ((z - z.mean()) / z.std()).astype(f32)


def noise1(t, seed, freq=1.0, octaves=3):
    """smooth 1-D value noise in about [-1, 1] (camera shake, flicker)"""
    v, a, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        x = t * freq * (2 ** o) + seed * 17.13 + o * 3.7
        i = math.floor(x); u = x - i; u = u * u * (3 - 2 * u)
        def h(n): return (math.sin(n * 127.1 + seed * 311.7 + o * 74.7) * 43758.5453) % 1.0 * 2 - 1
        v += a * (h(i) * (1 - u) + h(i + 1) * u); tot += a; a *= 0.5
    return v / tot


def bbcolor(T):
    """approximate linear RGB of a black body, normalised to max 1"""
    t = T / 100.0
    r = 255 if t <= 66 else 329.698727446 * (t - 60) ** -0.1332047592
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * (t - 60) ** -0.0755148492
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    c = np.clip(np.array([r, g, b]) / 255.0, 0, 1) ** 2.2
    return (c / c.max()).astype(f32)


def splat(img, fx, fy, rad, fn):
    """img[y, x] += fn(distance) (HxWx3 or HxW patch) within radius rad of (fx, fy)"""
    H, W = img.shape[:2]
    x0, x1 = max(0, int(fx - rad)), min(W, int(fx + rad) + 1); y0, y1 = max(0, int(fy - rad)), min(H, int(fy + rad) + 1)
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(f32)
    img[y0:y1, x0:x1] += fn(np.sqrt((xx + 0.5 - fx) ** 2 + (yy + 0.5 - fy) ** 2), xx + 0.5 - fx, yy + 0.5 - fy)


class Layout:
    """Output format. W x H frame; caption / HUD anchor rows; safe areas (top 12 %, bottom 20 % for vertical)."""
    def __init__(self, vertical=True):
        self.vertical = vertical
        if vertical:
            self.W, self.H = 1080, 1920
            self.cap_y = 1010; self.cap_size = 132; self.cap_maxw = 960
            self.hud_y = 1395; self.hud_size = 64
            self.safe_top, self.safe_bot = int(0.12 * 1920), int(0.80 * 1920)
        else:
            self.W, self.H = 1920, 1080
            self.cap_y = 560; self.cap_size = 112; self.cap_maxw = 1500
            self.hud_y = 850; self.hud_size = 52
            self.safe_top, self.safe_bot = 60, 1000
